"""Home notes: edited in the panel or proposed by the AI, sent with every chat."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.llm_agent.approval import Level
from custom_components.llm_agent.const import NOTES_MAX
from custom_components.llm_agent.snapshots import Snapshots
from custom_components.llm_agent.tools import ToolContext, ToolError, build_tools
from custom_components.llm_agent.tools.system import restore_snapshot

from .conftest import entry_options
from .test_agent import ScriptedProvider, reply_text
from .test_init import _setup


def _tool():
    return next(t for t in build_tools(entry_options()) if t.name == "update_home_notes")


async def test_panel_saves_notes_and_every_chat_sees_them(
    hass: HomeAssistant, hass_ws_client
) -> None:
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "llm_agent/notes", "notes": " Office is upstairs. "})
    assert (await client.receive_json())["result"]["notes"] == "Office is upstairs."
    await client.send_json({"id": 2, "type": "llm_agent/info"})
    info = (await client.receive_json())["result"]
    assert info["notes"] == "Office is upstairs." and info["notes_max"] == NOTES_MAX
    await client.send_json({"id": 3, "type": "llm_agent/notes", "notes": "x" * (NOTES_MAX + 1)})
    assert not (await client.receive_json())["success"]

    provider = ScriptedProvider([reply_text("Hi.")])
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await client.send_json({"id": 4, "type": "llm_agent/chat", "text": "hello"})
        assert (await client.receive_json())["success"]
        while (await client.receive_json())["event"]["type"] != "done":
            pass
    assert "Home notes" in provider.calls[0]["system"]
    assert "Office is upstairs." in provider.calls[0]["system"]
    assert entry.runtime_data.store.notes == "Office is upstairs."


async def test_ai_note_changes_always_ask_and_can_be_undone(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    store = entry.runtime_data.store
    store.set_notes("Office is upstairs.")
    ctx = ToolContext(hass, None, entry_options(approval_mode="autopilot"), Snapshots(hass))
    tool = _tool()
    args = tool.check_args({"notes": "Office is upstairs.\nNever switch off the freezer plug."})
    assert tool.classify(ctx, args).level is Level.RISKY
    preview = await tool.preview(ctx, args)
    assert "+Never switch off the freezer plug." in preview.diff
    out = await tool.run(ctx, args)
    assert store.notes.endswith("freezer plug.")
    await restore_snapshot(ctx, out.snapshot_id)
    assert store.notes == "Office is upstairs."
    with pytest.raises(ToolError, match="limited"):
        tool.check_args({"notes": "x" * (NOTES_MAX + 1)})
