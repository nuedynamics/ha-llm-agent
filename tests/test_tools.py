"""Tools that change configuration, and undo."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest

from custom_components.llm_agent.approval import Level
from custom_components.llm_agent.snapshots import Snapshots
from custom_components.llm_agent.tools import ToolContext, ToolError, build_tools
from custom_components.llm_agent.tools.files import FileAccess
from custom_components.llm_agent.tools.websocket import WebSocketTool, classify_ws

from .conftest import entry_options


@pytest.fixture
def config_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    hass.config.config_dir = str(tmp_path)
    (tmp_path / "configuration.yaml").write_text(
        "automation: !include automations.yaml\nscript: !include scripts.yaml\n"
    )
    (tmp_path / "automations.yaml").write_text("[]\n")
    (tmp_path / "scripts.yaml").write_text("{}\n")
    (tmp_path / "secrets.yaml").write_text("pw: hunter2\n")
    return tmp_path


def _ctx(hass: HomeAssistant, user_id: str | None = None, **opts) -> ToolContext:
    return ToolContext(hass, user_id, entry_options(**opts), Snapshots(hass))


def _tool(name: str, **opts):
    return next(t for t in build_tools(entry_options(**opts)) if t.name == name)


async def test_save_automation_then_undo(hass: HomeAssistant, config_dir: Path) -> None:
    assert await async_setup_component(hass, "automation", {"automation": []})
    ctx = _ctx(hass)
    save = _tool("save_config_item")
    args = {
        "kind": "automation",
        "config": {
            "alias": "Porch light at sunset",
            "triggers": [{"trigger": "sun", "event": "sunset"}],
            "actions": [{"action": "light.turn_on", "target": {"entity_id": "light.porch"}}],
        },
    }
    preview = await save.preview(ctx, args)
    assert "Create automation" in preview.summary and "Porch light" in preview.diff
    out = await save.run(ctx, args)
    await hass.async_block_till_done()
    text = (config_dir / "automations.yaml").read_text()
    assert "Porch light at sunset" in text
    assert out.data["entity_id"] == "automation.porch_light_at_sunset"
    assert hass.states.get("automation.porch_light_at_sunset") is not None

    undo = _tool("undo")
    await undo.run(ctx, {"snapshot_id": out.snapshot_id})
    await hass.async_block_till_done()
    assert (config_dir / "automations.yaml").read_text() == "[]\n"
    assert hass.states.get("automation.porch_light_at_sunset") is None


async def test_invalid_automation_is_rejected_without_writing(
    hass: HomeAssistant, config_dir: Path
) -> None:
    assert await async_setup_component(hass, "automation", {"automation": []})
    save = _tool("save_config_item")
    with pytest.raises(ToolError):
        await save.run(
            _ctx(hass),
            {"kind": "automation", "config": {"alias": "bad", "triggers": [{"trigger": "nope"}]}},
        )
    assert (config_dir / "automations.yaml").read_text() == "[]\n"


async def test_file_protection(hass: HomeAssistant, config_dir: Path) -> None:
    access = FileAccess(_ctx(hass))
    with pytest.raises(ToolError):
        access.resolve("secrets.yaml")
    with pytest.raises(ToolError):
        access.resolve("../etc/passwd")
    with pytest.raises(ToolError):
        access.resolve(".storage/auth")
    _path, rel = access.resolve("configuration.yaml")
    assert rel == "configuration.yaml"
    # an admin can lift the protection
    FileAccess(_ctx(hass, protect_sensitive=False)).resolve("secrets.yaml")


async def test_write_file_edit_and_undo(hass: HomeAssistant, config_dir: Path) -> None:
    ctx = _ctx(hass)
    write = _tool("write_file")
    assert write.classify(ctx, {"path": "configuration.yaml"}).level is Level.RISKY
    args = {
        "path": "configuration.yaml",
        "old": "script: !include scripts.yaml",
        "new": "script: !include scripts.yaml\nlogger:",
    }
    preview = await write.preview(ctx, args)
    assert "+logger:" in preview.diff
    out = await write.run(ctx, args)
    assert "logger:" in (config_dir / "configuration.yaml").read_text()
    with pytest.raises(ToolError, match="found 0 times"):
        await write.run(ctx, {"path": "configuration.yaml", "old": "missing", "new": "x"})
    await _tool("undo").run(ctx, {"snapshot_id": out.snapshot_id})
    assert "logger:" not in (config_dir / "configuration.yaml").read_text()
    # A second undo would overwrite anything changed since, so it is refused.
    with pytest.raises(ToolError, match="already undone"):
        await _tool("undo").run(ctx, {"snapshot_id": out.snapshot_id})


async def test_dashboard_create_save_and_undo(
    hass: HomeAssistant, config_dir: Path, hass_admin_user
) -> None:
    assert await async_setup_component(hass, "lovelace", {})
    ctx = _ctx(hass, hass_admin_user.id)
    save = _tool("save_dashboard")
    cfg = {"views": [{"title": "Home", "cards": [{"type": "entities", "entities": ["light.a"]}]}]}
    out = await save.run(ctx, {"url_path": "agent-test", "config": cfg, "title": "Agent test"})
    assert out.data["created"] is True
    got = await _tool("get_dashboard").run(ctx, {"url_path": "agent-test"})
    assert got.data["config"]["views"][0]["title"] == "Home"
    await _tool("undo").run(ctx, {"snapshot_id": out.snapshot_id})
    listed = await _tool("list_dashboards").run(ctx, {})
    assert "agent-test" not in str(listed.data)


async def test_dashboard_needs_admin_user(hass: HomeAssistant, config_dir: Path) -> None:
    assert await async_setup_component(hass, "lovelace", {})
    with pytest.raises(ToolError, match="admin"):
        await _tool("list_dashboards").run(_ctx(hass, None), {})


def test_classify_ws() -> None:
    assert classify_ws("lovelace/dashboards/list").level is Level.READ
    assert classify_ws("config_entries/delete").level is Level.RISKY
    assert classify_ws("hacs/repository/download").level is Level.RISKY


async def test_sensitive_ws_commands_blocked(hass: HomeAssistant, hass_admin_user) -> None:
    tool = WebSocketTool()
    with pytest.raises(ToolError):
        await tool.run(
            _ctx(hass, hass_admin_user.id),
            {
                "command": "auth/long_lived_access_token",
                "payload": {"client_name": "x", "lifespan": 1},
            },
        )


async def test_shell_only_when_enabled(hass: HomeAssistant, config_dir: Path) -> None:
    assert "shell" not in {t.name for t in build_tools(entry_options())}
    shell = _tool("shell", allow_shell=True)
    out = await shell.run(_ctx(hass, allow_shell=True), {"command": "echo hi"})
    assert out.data == {"exit_code": 0, "output": "hi\n"}
    with pytest.raises(ToolError):
        await shell.run(_ctx(hass), {"command": "echo hi"})


async def test_snapshots_stay_within_size_budget(
    hass: HomeAssistant, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.llm_agent import snapshots

    monkeypatch.setattr(snapshots, "SNAPSHOT_MAX_BYTES", 5000)
    snaps = snapshots.Snapshots(hass)
    ids = [await snaps.save("file", f"s{i}", {"content": "x" * 2000}) for i in range(5)]
    kept = {p.stem for p in snaps.dir.glob("*.json")}
    assert ids[-1] in kept and len(kept) == 2
    # a single snapshot larger than the budget is still kept, so the newest edit can be undone
    big = await snaps.save("file", "big", {"content": "x" * 10000})
    assert {p.stem for p in snaps.dir.glob("*.json")} == {big}


async def test_concurrent_undos_restore_once(hass: HomeAssistant, config_dir: Path) -> None:
    import asyncio

    ctx = _ctx(hass)
    args = {"path": "configuration.yaml", "old": "script: !include scripts.yaml", "new": "x: 1"}
    out = await _tool("write_file").run(ctx, args)
    results = await asyncio.gather(
        *(_tool("undo").run(ctx, {"snapshot_id": out.snapshot_id}) for _ in range(2)),
        return_exceptions=True,
    )
    assert sum(isinstance(r, ToolError) for r in results) == 1


async def test_failed_restore_can_be_retried(hass: HomeAssistant, config_dir: Path) -> None:
    from unittest.mock import patch

    ctx = _ctx(hass)
    args = {"path": "configuration.yaml", "old": "script: !include scripts.yaml", "new": "x: 1"}
    out = await _tool("write_file").run(ctx, args)
    with (
        patch("custom_components.llm_agent.tools.system.write_text", side_effect=OSError("disk")),
        pytest.raises(OSError),
    ):
        await _tool("undo").run(ctx, {"snapshot_id": out.snapshot_id})
    await _tool("undo").run(ctx, {"snapshot_id": out.snapshot_id})  # not marked undone
    assert "script: !include scripts.yaml" in (config_dir / "configuration.yaml").read_text()
