"""WebSocket API used by the panel. Every command requires an admin user.

The panel route itself is not access-controlled by Home Assistant, so these checks are
the real security boundary.
"""

from __future__ import annotations

import base64
import binascii
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
import probatio as vol

from .agent import STOP_TEXT, Agent, ChatRun, Emit, home_context, rewind_last_turn
from .const import CONF_APPROVAL_MODE, CONF_HOME_SUMMARY, DOMAIN, setting
from .providers.models import PROVIDER_NAMES, suggestions
from .tools import ToolContext, ToolError
from .tools.camera import IMAGE_TYPES, MAX_IMAGE_BYTES
from .tools.system import AlreadyUndone, restore_snapshot

VERSION_KEY = "version"


def _agent(hass: HomeAssistant) -> Agent | None:
    return hass.data.get(DOMAIN)


@callback
def async_register(hass: HomeAssistant) -> None:
    for handler in (
        ws_info,
        ws_my_default,
        ws_models,
        ws_list,
        ws_search,
        ws_get,
        ws_delete,
        ws_rename,
        ws_chat,
        ws_attach,
        ws_approve,
        ws_cancel,
        ws_undo,
    ):
        websocket_api.async_register_command(hass, handler)


def _not_ready(connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    connection.send_error(msg["id"], "not_ready", "LLM Agent is not set up")


@websocket_api.websocket_command({vol.Required("type"): "llm_agent/info"})
@websocket_api.require_admin
@callback
def ws_info(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    agent = _agent(hass)
    if agent is None:
        return _not_ready(connection, msg)
    connection.send_result(
        msg["id"],
        {
            "version": hass.data.get(f"{DOMAIN}_{VERSION_KEY}"),
            "approval_mode": agent.options.get(CONF_APPROVAL_MODE),
            "providers": [
                {
                    "id": p.id,
                    "type": p.type,
                    "name": p.name,
                    "type_name": PROVIDER_NAMES.get(p.type, p.type),
                    "default_model": p.default_model,
                    "models": suggestions(p.type),
                }
                for p in agent.providers()
            ],
            "running": list(agent.runs),
            "my_default": agent.store.user_default(connection.user.id),
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "llm_agent/my_default",
        # null clears it, so new chats use the provider's default again
        vol.Required("provider_id"): vol.Any(str, None),
        vol.Optional("model", default=""): vol.All(str, vol.Length(max=200)),
    }
)
@websocket_api.require_admin
@callback
def ws_my_default(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Set the current user's default provider and model for new chats."""
    agent = _agent(hass)
    if agent is None:
        return _not_ready(connection, msg)
    provider_id = msg["provider_id"]
    if provider_id and provider_id not in {p.id for p in agent.providers()}:
        connection.send_error(msg["id"], "not_found", "Unknown provider")
        return
    agent.store.set_user_default(connection.user.id, provider_id, msg["model"].strip())
    connection.send_result(msg["id"], {"my_default": agent.store.user_default(connection.user.id)})


@websocket_api.websocket_command(
    {vol.Required("type"): "llm_agent/models", vol.Required("provider_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_models(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    agent = _agent(hass)
    if agent is None:
        return _not_ready(connection, msg)
    models, error = await agent.models(msg["provider_id"])
    connection.send_result(msg["id"], {"models": models, "error": error})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "llm_agent/conversations/search",
        vol.Required("query"): vol.All(str, vol.Length(max=200)),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_search(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    agent = _agent(hass)
    if agent is None:
        return _not_ready(connection, msg)
    connection.send_result(msg["id"], {"conversations": await agent.store.search(msg["query"])})


@websocket_api.websocket_command({vol.Required("type"): "llm_agent/conversations/list"})
@websocket_api.require_admin
@callback
def ws_list(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    agent = _agent(hass)
    if agent is None:
        return _not_ready(connection, msg)
    connection.send_result(msg["id"], agent.store.list())


@websocket_api.websocket_command(
    {
        vol.Required("type"): "llm_agent/conversations/get",
        vol.Required("conversation_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_get(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    agent = _agent(hass)
    if agent is None:
        return _not_ready(connection, msg)
    conv = await agent.store.get(msg["conversation_id"])
    if conv is None:
        connection.send_error(msg["id"], "not_found", "Conversation not found")
        return
    connection.send_result(msg["id"], _public(conv))


def _public(conv: dict[str, Any]) -> dict[str, Any]:
    """Conversation as the panel needs it: no raw provider blocks or context."""
    messages = []
    for m in conv["messages"]:
        if m["role"] == "user":
            item = {"role": "user", "content": m.get("display", m["content"])}
            if m.get("photos"):
                item["photos"] = m["photos"]
            messages.append(item)
        elif m["role"] == "assistant":
            messages.append(
                {
                    "role": "assistant",
                    "content": m.get("content", ""),
                    "tool_calls": m.get("tool_calls", []),
                }
            )
        else:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": m["tool_call_id"],
                    "name": m["name"],
                    "ok": not m.get("is_error"),
                    "summary": m.get("summary", ""),
                    "snapshot_id": m.get("snapshot_id"),
                    "undone": m.get("undone", False),
                    "decision": m.get("decision"),
                    "review": m.get("review"),
                    "preview": m["content"][:1500],
                }
            )
    return {
        "id": conv["id"],
        "title": conv["title"],
        "provider_id": conv["provider_id"],
        "model": conv["model"],
        "usage": conv["usage"],
        "stopped": conv.get("stopped"),
        "stopped_text": STOP_TEXT.get(conv.get("stopped") or ""),
        "messages": messages,
    }


@websocket_api.websocket_command(
    {
        vol.Required("type"): "llm_agent/conversations/delete",
        vol.Required("conversation_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    agent = _agent(hass)
    if agent is None:
        return _not_ready(connection, msg)
    if (run := agent.runs.get(msg["conversation_id"])) and run.task:
        run.task.cancel()
    await agent.store.delete(msg["conversation_id"])
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "llm_agent/conversations/rename",
        vol.Required("conversation_id"): str,
        vol.Required("title"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_rename(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    agent = _agent(hass)
    if agent is None:
        return _not_ready(connection, msg)
    await agent.store.rename(msg["conversation_id"], msg["title"])
    connection.send_result(msg["id"])


MAX_PHOTOS = 3


def _photo(value: Any) -> dict[str, str]:
    """A photo from the panel: a known picture type, valid base64, not too large."""
    if not isinstance(value, dict) or set(value) != {"media_type", "data"}:
        raise vol.Invalid("a photo needs media_type and data")
    if value["media_type"] not in IMAGE_TYPES:
        raise vol.Invalid("photos must be JPEG, PNG, WebP or GIF")
    data = value["data"]
    if not isinstance(data, str) or len(data) > MAX_IMAGE_BYTES * 4 // 3 + 4:
        raise vol.Invalid("the photo is too large")
    try:
        base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as err:
        raise vol.Invalid("the photo is not valid base64") from err
    return {"media_type": value["media_type"], "data": data}


@websocket_api.websocket_command(
    {
        vol.Required("type"): "llm_agent/chat",
        vol.Optional("conversation_id"): vol.Any(str, None),
        vol.Required("text"): vol.All(str, vol.Length(min=1, max=100000)),
        vol.Optional("provider_id"): str,
        vol.Optional("model"): str,
        # Replace the last user message (edit and resend, or retry with the same text).
        vol.Optional("rewind", default=False): bool,
        # Run this one turn even though today's spend is past the daily cap.
        vol.Optional("over_cap", default=False): bool,
        # Photos for this message, for models that can see images.
        vol.Optional("images", default=list): vol.All([_photo], vol.Length(max=MAX_PHOTOS)),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_chat(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Start a turn. Streams events on this subscription until a 'done' event."""
    agent = _agent(hass)
    if agent is None:
        return _not_ready(connection, msg)
    conv = None
    if msg.get("conversation_id"):
        conv = await agent.store.get(msg["conversation_id"])
    try:
        pconf = agent.provider_config(msg.get("provider_id") or (conv or {}).get("provider_id"))
    except ToolError as err:
        connection.send_error(msg["id"], "no_provider", str(err))
        return
    if conv is None:
        context = home_context(hass) if setting(agent.options, CONF_HOME_SUMMARY) else ""
        conv = await agent.store.create(pconf.id, msg.get("model") or pconf.default_model, context)
    elif conv["id"] not in agent.runs:
        if conv["provider_id"] != pconf.id:
            conv["provider_id"] = pconf.id
            conv["model"] = pconf.default_model
        if msg.get("model"):
            conv["model"] = msg["model"]
    if conv["id"] in agent.runs:
        connection.send_error(msg["id"], "busy", "This conversation is already running")
        return

    note = rewind_last_turn(conv) if msg["rewind"] else ""
    run = ChatRun(agent, conv, connection.user.id)
    agent.runs[conv["id"]] = run
    run.listeners.add(_listen(connection, msg["id"], run))

    async def _run() -> None:
        try:
            await run.run(msg["text"], note, over_cap=msg["over_cap"], images=msg["images"])
        finally:
            agent.runs.pop(conv["id"], None)

    connection.send_result(msg["id"], {"conversation_id": conv["id"], "title": conv["title"]})
    run.task = hass.async_create_background_task(_run(), f"llm_agent_chat_{conv['id']}")


def _listen(connection: websocket_api.ActiveConnection, msg_id: int, run: ChatRun) -> Emit:
    """Stream a run's events on this subscription. Closing the panel only ends the
    stream; the turn continues and can be re-attached with llm_agent/attach."""

    def listener(event: dict[str, Any]) -> None:
        connection.send_message(websocket_api.event_message(msg_id, event))

    @callback
    def _unsub() -> None:
        run.listeners.discard(listener)

    connection.subscriptions[msg_id] = _unsub
    return listener


@websocket_api.websocket_command(
    {vol.Required("type"): "llm_agent/attach", vol.Required("conversation_id"): str}
)
@websocket_api.require_admin
@callback
def ws_attach(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Re-attach to a running turn (after reopening the panel)."""
    agent = _agent(hass)
    run = agent.runs.get(msg["conversation_id"]) if agent else None
    if run is None:
        connection.send_error(msg["id"], "not_running", "This conversation is not running")
        return
    connection.send_result(msg["id"])
    run.attach(_listen(connection, msg["id"], run))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "llm_agent/approve",
        vol.Required("conversation_id"): str,
        vol.Required("call_id"): str,
        vol.Required("approved"): bool,
        vol.Optional("note", default=""): str,
    }
)
@websocket_api.require_admin
@callback
def ws_approve(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    agent = _agent(hass)
    run = agent.runs.get(msg["conversation_id"]) if agent else None
    if run is None or not run.answer(msg["call_id"], msg["approved"], msg["note"][:500]):
        connection.send_error(msg["id"], "not_found", "No pending approval with that id")
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): "llm_agent/cancel", vol.Required("conversation_id"): str}
)
@websocket_api.require_admin
@callback
def ws_cancel(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    agent = _agent(hass)
    run = agent.runs.get(msg["conversation_id"]) if agent else None
    if run is not None and run.task is not None:
        run.task.cancel()
    connection.send_result(msg["id"])


async def _mark_message_undone(agent: Any, msg: dict[str, Any]) -> None:
    """Remember the undo on the tool message, so the panel shows it after a reload."""
    if (conv_id := msg.get("conversation_id")) and (conv := await agent.store.get(conv_id)):
        for m in conv["messages"]:
            if m.get("role") == "tool" and m.get("snapshot_id") == msg["snapshot_id"]:
                m["undone"] = True
                agent.store.save(conv)
                break


@websocket_api.websocket_command(
    {
        vol.Required("type"): "llm_agent/undo",
        vol.Required("snapshot_id"): str,
        vol.Optional("conversation_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_undo(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    agent = _agent(hass)
    if agent is None:
        return _not_ready(connection, msg)
    ctx = ToolContext(hass, connection.user.id, agent.options, agent.snapshots)
    try:
        _data, summary = await restore_snapshot(ctx, msg["snapshot_id"])
    except AlreadyUndone:
        # Undone earlier (perhaps by the assistant): show it as undone, restore nothing.
        await _mark_message_undone(agent, msg)
        connection.send_result(msg["id"], {"summary": "Already undone"})
        return
    except ToolError as err:
        connection.send_error(msg["id"], "undo_failed", str(err))
        return
    await _mark_message_undone(agent, msg)
    await agent.snapshots.audit(
        {
            "user": connection.user.id,
            "tool": "undo",
            "args": msg["snapshot_id"],
            "ok": True,
            "detail": summary,
        }
    )
    connection.send_result(msg["id"], {"summary": summary})
