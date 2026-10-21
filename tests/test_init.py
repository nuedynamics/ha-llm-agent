"""Setup, panel registration and the admin-only WebSocket API."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.llm_agent.const import DOMAIN, PANEL_URL

from .conftest import entry_options
from .test_agent import ScriptedProvider, reply_text


async def _setup(hass: HomeAssistant, **opts: Any) -> MockConfigEntry:
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(
        domain=DOMAIN, data={"acknowledged_risks": True}, options=entry_options(**opts)
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_registers_admin_panel_and_assist_agent(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    panels = hass.data["frontend_panels"]
    assert PANEL_URL in panels
    assert panels[PANEL_URL].require_admin is True
    assert hass.states.async_entity_ids("conversation")
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert PANEL_URL not in hass.data["frontend_panels"]


async def test_ws_rejects_non_admin(hass: HomeAssistant, hass_ws_client, hass_admin_user) -> None:
    await _setup(hass)
    hass_admin_user.groups = []
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "llm_agent/conversations/list"})
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "unauthorized"


async def test_ws_chat_streams_and_persists(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "llm_agent/info"})
    info = await client.receive_json()
    assert info["result"]["providers"][0]["id"] == "p1"

    provider = ScriptedProvider([reply_text("Hello there")])
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await client.send_json_auto_id({"type": "llm_agent/chat", "text": "hi"})
        result = await client.receive_json()
        assert result["success"]
        conv_id = result["result"]["conversation_id"]
        events = []
        while True:
            msg = await client.receive_json()
            events.append(msg["event"])
            if msg["event"]["type"] == "done":
                break
    assert "".join(e.get("text", "") for e in events if e["type"] == "delta") == "Hello there"
    # subscribers get the chat's id as the first event
    assert events[0] == {"type": "conversation", "conversation_id": conv_id, "title": "New chat"}
    await client.send_json_auto_id({"type": "llm_agent/chat", "text": " \n "})
    assert not (await client.receive_json())["success"]

    await client.send_json_auto_id(
        {"type": "llm_agent/conversations/get", "conversation_id": conv_id}
    )
    conv = (await client.receive_json())["result"]
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]
    assert conv["messages"][0]["content"] == "hi"
    assert "raw" not in conv["messages"][1]

    await client.send_json_auto_id({"type": "llm_agent/conversations/list"})
    assert (await client.receive_json())["result"][0]["id"] == conv_id


async def test_diagnostics_redact_keys_and_omit_content(hass: HomeAssistant) -> None:
    from custom_components.llm_agent.diagnostics import async_get_config_entry_diagnostics

    entry = await _setup(
        hass, extra_prompt="my alarm code is zebra-4471", search_api_key="brave-secret-77"
    )
    agent = entry.runtime_data
    await agent.snapshots.audit(
        {"tool": "call_service", "args": "secret args", "risk": "low", "ok": False, "detail": "x"}
    )
    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = str(diag)
    assert "sk-" not in text and entry.options["providers"][0]["api_key"] not in text
    assert "zebra-4471" not in text and "secret args" not in text and "brave-secret-77" not in text
    assert diag["recent_actions"][-1] == {
        "time": diag["recent_actions"][-1]["time"],
        "tool": "call_service",
        "risk": "low",
        "ok": False,
    }


async def test_diagnostics_strip_credentials_from_provider_urls(hass: HomeAssistant) -> None:
    from custom_components.llm_agent.diagnostics import _redact_provider

    out = _redact_provider({"base_url": "http://bob:hunter2@proxy.lan:8080/v1", "api_key": "k"})
    assert out["base_url"] == "http://**REDACTED**@proxy.lan:8080/v1"
    assert "hunter2" not in str(out) and out["api_key"] != "k"
    assert _redact_provider({"base_url": "http://ollama:11434/v1"})["base_url"] == (
        "http://ollama:11434/v1"
    )


async def test_store_keeps_running_conversations_cached_and_deleted_ones_dead(
    hass: HomeAssistant,
) -> None:
    from custom_components.llm_agent.store import CACHE_SIZE, ConversationStore

    running: set[str] = set()
    store = ConversationStore(hass, busy=lambda cid: cid in running)
    await store.async_load()
    first = await store.create("p1", "m", "")
    running.add(first["id"])
    for _ in range(CACHE_SIZE + 3):
        await store.create("p1", "m", "")
    # still the same object, not a stale copy reloaded from disk
    assert await store.get(first["id"]) is first

    await store.delete(first["id"])
    first["messages"].append({"role": "user", "content": "late"})
    store.save(first)  # a cancelled run finishing after the delete
    assert await store.get(first["id"]) is None
    assert first["id"] not in [c["id"] for c in store.list()]


async def _chat_events(client) -> list[dict[str, Any]]:
    events = []
    while True:
        msg = await client.receive_json()
        events.append(msg["event"])
        if msg["event"]["type"] == "done":
            return events


async def test_ws_chat_sends_photos_for_that_turn_only(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    photo = {"media_type": "image/jpeg", "data": "/9j/4AAQ"}
    provider = ScriptedProvider([reply_text("A plug."), reply_text("Yes.")])
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await client.send_json_auto_id(
            {"type": "llm_agent/chat", "text": "what is this?", "images": [photo]}
        )
        result = await client.receive_json()
        assert result["success"]
        conv_id = result["result"]["conversation_id"]
        await _chat_events(client)
        await client.send_json_auto_id(
            {"type": "llm_agent/chat", "conversation_id": conv_id, "text": "is it smart?"}
        )
        assert (await client.receive_json())["success"]
        await _chat_events(client)
    assert provider.calls[0]["messages"][0]["images"] == [photo]
    later = provider.calls[1]["messages"][0]
    assert "images" not in later and "no longer attached" in later["content"]

    await client.send_json_auto_id(
        {"type": "llm_agent/conversations/get", "conversation_id": conv_id}
    )
    first = (await client.receive_json())["result"]["messages"][0]
    assert first == {"role": "user", "content": "what is this?", "photos": 1}


async def test_ws_chat_refuses_bad_photos(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    good = {"media_type": "image/png", "data": "iVBORw0KGgo="}
    for images in (
        [{"media_type": "image/svg+xml", "data": "QUJD"}],
        [{"media_type": "image/png", "data": "not base64!"}],
        [{"media_type": "image/png", "data": "iVBORw0KGgo=", "url": "http://x"}],
        [{"media_type": "image/png", "data": "/9j/4AAQ"}],  # a JPEG claiming to be a PNG
        [{"media_type": "image/png", "data": ""}],
        [good] * 4,
    ):
        await client.send_json_auto_id({"type": "llm_agent/chat", "text": "hi", "images": images})
        result = await client.receive_json()
        assert not result["success"], images[0]["media_type"]


def test_photo_size_is_checked() -> None:
    import probatio as vol
    import pytest

    from custom_components.llm_agent.websocket import _photo

    with pytest.raises(vol.Invalid, match="too large"):
        _photo({"media_type": "image/png", "data": "A" * 5_000_000})


def test_photo_checks_the_picture_type() -> None:
    from custom_components.llm_agent.websocket import _photo

    assert _photo({"media_type": "image/webp", "data": "UklGRgAAAABXRUJQ"})["data"]
    assert _photo({"media_type": "image/gif", "data": "R0lGODlh"})["data"]


def test_saved_conversations_never_hold_pictures() -> None:
    from custom_components.llm_agent.store import _without_images

    conv = {"id": "c", "messages": [{"role": "user", "content": "x", "images": [1], "photos": 1}]}
    saved = _without_images(conv)
    assert saved["messages"][0] == {"role": "user", "content": "x", "photos": 1}
    assert conv["messages"][0]["images"] == [1]  # the running turn keeps them
