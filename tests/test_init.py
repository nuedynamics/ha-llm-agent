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

    entry = await _setup(hass, extra_prompt="my alarm code is 1234")
    agent = entry.runtime_data
    await agent.snapshots.audit(
        {"tool": "call_service", "args": "secret args", "risk": "low", "ok": False, "detail": "x"}
    )
    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = str(diag)
    assert "sk-" not in text and entry.options["providers"][0]["api_key"] not in text
    assert "1234" not in text and "secret args" not in text
    assert diag["recent_actions"][-1] == {
        "time": diag["recent_actions"][-1]["time"],
        "tool": "call_service",
        "risk": "low",
        "ok": False,
        "error": "x",
    }
