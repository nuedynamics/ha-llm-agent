"""Run Home Assistant WebSocket commands internally as the chatting admin.

This gives the agent the same reach as the HA frontend (helpers, registries,
dashboards, energy, backups, HACS, ...) without a tool per feature.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.http import WebSocketAdapter
from homeassistant.helpers.json import json_dumps

from ..approval import Risk
from . import Tool, ToolContext, ToolError, ToolOutput, obj
from .states import CallService

_LOGGER = logging.getLogger(__name__)
WS_TIMEOUT = 120

READ_SUFFIXES = (
    "/list",
    "/get",
    "/info",
    "/search",
    "/details",
    "/status",
    "/config",
    "/schema",
)
READ_EXACT = {
    "get_states",
    "get_config",
    "get_services",
    "get_panels",
    "render_template",
    "ping",
}
RISKY_WORDS = ("delete", "remove", "restore", "uninstall", "reset", "wipe", "purge")
RISKY_PREFIXES = (
    "hacs/repository/download",
    "hacs/repository/remove",
    "hassio/",
    "supervisor/",
    "backup/restore",
    "config/auth",
    "auth/",
    "person/",
    "config_entries/",
    "update/",
    "homeassistant/",
)
# Never runnable through the agent while sensitive-data protection is on.
SENSITIVE = (
    "auth/long_lived_access_token",
    "auth/refresh_tokens",
    "auth/sign_path",
    "config/auth_provider",
    "application_credentials/",
    "cloud/",
)


def classify_ws(command: str) -> Risk:
    if command in READ_EXACT or command.endswith(READ_SUFFIXES):
        return Risk.read()
    if any(w in command for w in RISKY_WORDS) or command.startswith(RISKY_PREFIXES):
        return Risk.risky(f"{command} can remove data or change system settings")
    return Risk.write()


async def ws_call(ctx: ToolContext, command: str, payload: dict[str, Any] | None = None) -> Any:
    """Run one WebSocket command and return its result (or raise ToolError)."""
    hass = ctx.hass
    if command.startswith("llm_agent/"):
        raise ToolError("The agent cannot call its own commands")
    if "subscribe" in command:
        raise ToolError(
            "Subscription commands are not supported; use the matching list/get command"
        )
    user = await hass.auth.async_get_user(ctx.user_id) if ctx.user_id else None
    if user is None or not user.is_admin:
        raise ToolError("WebSocket commands need an admin user")

    loop = asyncio.get_running_loop()
    result: asyncio.Future[Any] = loop.create_future()

    def send_message(message: Any) -> None:
        if result.done():
            return
        if isinstance(message, (bytes, str)):
            message = json.loads(message)
        else:
            # Round-trip through HA's encoder so json_fragment and datetimes resolve.
            message = json.loads(json_dumps(message))
        if message.get("type") == "result":
            result.set_result(message)

    conn = ActiveConnection(
        WebSocketAdapter(_LOGGER, {"connid": "llm_agent"}),
        hass,
        send_message,
        user,
        None,
        "llm_agent",
    )
    conn.async_handle({**(payload or {}), "id": 1, "type": command})
    try:
        message = await asyncio.wait_for(result, WS_TIMEOUT)
    except TimeoutError as err:
        raise ToolError(f"{command} timed out") from err
    finally:
        conn.async_handle_close()
    if not message.get("success"):
        error = message.get("error") or {}
        raise ToolError(f"{command} failed: {error.get('code')}: {error.get('message')}")
    return message.get("result")


class WebSocketTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            "ha_websocket",
            "Run any Home Assistant WebSocket API command as the current admin, exactly "
            "as the HA frontend does. Use it for things without a dedicated tool, e.g. "
            "helpers (input_boolean/create, input_number/update, timer/delete, "
            "counter/list), floors and labels (config/floor_registry/*, "
            "config/label_registry/*), lovelace/resources, energy/get_prefs, "
            "backup/info, backup/generate, hacs/repositories/list, "
            "hacs/repository/download (needs repository id), system_health/info, "
            "repairs/list_issues. 'payload' holds the command fields (not id/type).",
            obj(
                {
                    "command": {
                        "type": "string",
                        "description": "The WebSocket message type",
                    },
                    "payload": {"type": "object"},
                },
                ["command"],
            ),
        )

    def _as_service(self, args: dict[str, Any]) -> dict[str, Any] | None:
        """A WebSocket call_service, in call_service tool form, so it gets the same rules."""
        if str(args.get("command", "")) != "call_service":
            return None
        payload = args.get("payload") or {}
        return {
            "domain": str(payload.get("domain", "")),
            "service": str(payload.get("service", "")),
            "target": payload.get("target") or {},
            "data": payload.get("service_data") or {},
        }

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        command = str(args.get("command", ""))
        if command == "execute_script":
            return Risk.risky("runs a script sequence directly, which can call any service")
        if (service := self._as_service(args)) is not None:
            return SERVICE_TOOL.classify(ctx, service)
        return classify_ws(command)

    def review_keys(self, ctx: ToolContext, args: dict[str, Any]) -> list[str]:
        keys = [self.name, f"{self.name}:{args.get('command', '')}"]
        if (service := self._as_service(args)) is not None:
            keys += SERVICE_TOOL.review_keys(ctx, service)
        return keys

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        command = str(args["command"])
        if ctx.options.get("protect_sensitive", True) and command.startswith(SENSITIVE):
            raise ToolError(
                f"{command} is blocked because it exposes credentials. An admin can turn off "
                "'Protect sensitive data' in the LLM Agent options to allow it."
            )
        if command.startswith("hacs/repository/download") and ctx.options.get(
            "backup_before_risky", True
        ):
            from ..snapshots import full_backup

            note = await full_backup(ctx.hass, f"HACS download {args.get('payload')}")
        else:
            note = ""
        data = await ws_call(ctx, command, args.get("payload") or {})
        return ToolOutput(data, summary=note or f"Ran {command}")


TOOLS: list[Tool] = [WebSocketTool()]
SERVICE_TOOL = CallService()
