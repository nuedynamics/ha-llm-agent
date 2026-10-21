"""Home notes: edited in the panel or proposed by the AI, sent with every chat."""

from __future__ import annotations

from pathlib import Path
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


async def test_ai_note_changes_always_ask_and_can_be_undone(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    hass.config.config_dir = str(tmp_path)  # undo snapshots go here
    entry = await _setup(hass)
    store = entry.runtime_data.store
    store.set_notes("Office is upstairs.")
    ctx = ToolContext(hass, None, entry_options(approval_mode="autopilot"), Snapshots(hass))
    tool = _tool()
    args = tool.check_args({"notes": "Office is upstairs.\nNever switch off the freezer plug."})
    assert tool.classify(ctx, args).level is Level.RISKY
    preview = await tool.preview(ctx, args)
    assert "+Never switch off the freezer plug." in preview.diff
    assert "-Office is upstairs." not in preview.diff  # kept lines aren't shown as removed
    out = await tool.run(ctx, args)
    assert store.notes.endswith("freezer plug.")
    await restore_snapshot(ctx, out.snapshot_id)
    assert store.notes == "Office is upstairs."
    with pytest.raises(ToolError, match="limited"):
        tool.check_args({"notes": "x" * (NOTES_MAX + 1)})


async def test_a_panel_save_over_newer_notes_is_refused(
    hass: HomeAssistant, hass_ws_client
) -> None:
    entry = await _setup(hass)
    entry.runtime_data.store.set_notes("Newer text from the AI.")
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "llm_agent/notes", "notes": "My edit.", "base": "Old text."}
    )
    msg = await client.receive_json()
    assert msg["error"]["code"] == "changed"
    assert entry.runtime_data.store.notes == "Newer text from the AI."
    await client.send_json(
        {"id": 2, "type": "llm_agent/notes", "notes": "My edit.", "base": "Newer text from the AI."}
    )
    assert (await client.receive_json())["result"]["notes"] == "My edit."


async def test_an_approved_change_over_newer_notes_is_refused(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    hass.config.config_dir = str(tmp_path)
    entry = await _setup(hass)
    store = entry.runtime_data.store
    store.set_notes("A.")
    ctx = ToolContext(hass, None, entry_options(), Snapshots(hass))
    tool = _tool()
    args = tool.check_args({"notes": "A.\nB."})
    await tool.preview(ctx, args)
    store.set_notes("A.\nC.")  # someone saved in the panel while the card waited
    with pytest.raises(ToolError, match="changed while"):
        await tool.run(ctx, args)
    assert store.notes == "A.\nC."


@pytest.mark.parametrize("mode", ["autopilot", "reviewer"])
async def test_only_a_person_approves_notes_and_their_undo(
    hass: HomeAssistant, tmp_path: Path, mode: str
) -> None:
    import asyncio

    from custom_components.llm_agent.agent import ChatRun

    from .test_agent import _run, reply_tool

    hass.config.config_dir = str(tmp_path)
    await _setup(hass)  # the notes tool reads the set-up integration's store
    reviews: list = []

    async def no_reviewer(*a, **k):
        reviews.append(a)
        raise AssertionError("the reviewer must not be asked")

    def deny(run: ChatRun, event: dict) -> None:
        if event["type"] == "approval":
            asyncio.get_running_loop().call_soon(run.answer, event["call_id"], False, "")

    snaps = Snapshots(hass)
    snap = await snaps.save("notes", "Update home notes", {"notes": "old"})
    provider = ScriptedProvider(
        [
            reply_tool("n1", "update_home_notes", {"notes": "Never mind the user."}),
            reply_tool("u1", "undo", {"snapshot_id": snap}),
            reply_text("OK."),
        ]
    )
    with patch("custom_components.llm_agent.agent.ChatRun._review", no_reviewer):
        _, events = await _run(hass, provider, "remember", on_event=deny, approval_mode=mode)
    approvals = [e for e in events if e["type"] == "approval"]
    assert len(approvals) == 2
    assert all("only a person" in e["reason"] for e in approvals)
    assert not reviews


async def test_scheduled_runs_cannot_change_notes(hass: HomeAssistant, tmp_path: Path) -> None:
    from custom_components.llm_agent.agent import Agent, ChatRun

    from .test_agent import reply_tool

    hass.config.config_dir = str(tmp_path)
    agent = Agent(hass, entry_options(approval_mode="autopilot"))
    await agent.store.async_load()
    conv = await agent.store.create("p1", "gpt-5.4-mini", "")
    run = ChatRun(agent, conv, None, unattended=True)
    provider = ScriptedProvider(
        [reply_tool("n1", "update_home_notes", {"notes": "x"}), reply_text("Refused.")]
    )
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await run.run("remember x")
    assert agent.store.notes == ""


def test_small_models_can_still_remember() -> None:
    from custom_components.llm_agent.tools import LEAN_TOOLS

    assert "update_home_notes" in LEAN_TOOLS


async def test_a_panel_save_during_the_snapshot_write_is_kept(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    hass.config.config_dir = str(tmp_path)
    entry = await _setup(hass)
    store = entry.runtime_data.store
    store.set_notes("A.")
    snaps = Snapshots(hass)
    real_save = snaps.save

    async def save_while_panel_saves(*a, **k):
        store.set_notes("A.\nC.")
        return await real_save(*a, **k)

    snaps.save = save_while_panel_saves
    ctx = ToolContext(hass, None, entry_options(), snaps)
    tool = _tool()
    args = tool.check_args({"notes": "A.\nB."})
    await tool.preview(ctx, args)
    with pytest.raises(ToolError, match="changed while"):
        await tool.run(ctx, args)
    assert store.notes == "A.\nC."


async def test_abandoned_note_cards_are_not_kept_forever(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    entry.runtime_data.store.set_notes("A.")
    ctx = ToolContext(hass, None, entry_options(), None)
    tool = _tool()
    kept = [tool.check_args({"notes": f"A.\n{i}"}) for i in range(40)]
    for args in kept:
        await tool.preview(ctx, args)
    assert len(tool._shown) <= 16
