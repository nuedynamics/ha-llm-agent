"""Tools that change configuration, and undo."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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
    assert "warning" not in out.data
    assert hass.states.get("automation.porch_light_at_sunset") is not None

    undo = _tool("undo")
    await undo.run(ctx, {"snapshot_id": out.snapshot_id})
    await hass.async_block_till_done()
    assert (config_dir / "automations.yaml").read_text() == "[]\n"
    assert hass.states.get("automation.porch_light_at_sunset") is None


async def test_saved_but_not_loaded_automation_is_flagged(
    hass: HomeAssistant, config_dir: Path
) -> None:
    # configuration.yaml without 'automation: !include automations.yaml': the file is
    # written, but nothing loads it. Say so instead of reporting a working automation.
    assert await async_setup_component(hass, "automation", {"automation": []})
    args = {
        "kind": "automation",
        "config": {"alias": "Never loads", "triggers": [], "actions": []},
    }
    with patch("custom_components.llm_agent.tools.config_items._entity_for", return_value=None):
        out = await _tool("save_config_item").run(_ctx(hass), args)
    assert out.data["entity_id"] is None
    assert "automation: !include automations.yaml" in out.data["warning"]
    assert "not loaded" in out.summary


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


# Mistakes a small local model (Llama 3.1 8B) made in the real-model check.


def test_objects_sent_as_text_are_repaired() -> None:
    save = _tool("save_config_item")
    python_style = "{'alias': 'Night off', 'triggers': [{'trigger': 'time', 'at': '23:00'}]}"
    args = save.check_args({"kind": "automation", "id": "night_off", "config": python_style})
    assert args["config"]["triggers"][0]["at"] == "23:00"
    json_style = '{"alias": "Night off"}'
    assert save.check_args({"kind": "automation", "config": json_style})["config"] == {
        "alias": "Night off"
    }
    with pytest.raises(ToolError, match="must be a JSON object"):
        save.check_args({"kind": "automation", "config": "{'alias': 'cut off"})
    with pytest.raises(ToolError, match="Missing required argument 'config'"):
        save.check_args({"kind": "automation"})


def test_lists_and_numbers_sent_as_text_are_repaired() -> None:
    get = _tool("get_entities")
    assert get.check_args({"entity_ids": "['light.a', 'light.b']"})["entity_ids"] == [
        "light.a",
        "light.b",
    ]
    assert get.check_args({"entity_ids": "light.a"})["entity_ids"] == ["light.a"]


async def test_unknown_entity_is_refused_with_suggestions(hass: HomeAssistant) -> None:
    hass.states.async_set("input_boolean.e2e_switch", "off", {"friendly_name": "E2E switch"})
    call = _tool("call_service")
    hass.services.async_register("switch", "turn_on", lambda _call: None)
    with pytest.raises(ToolError, match=r"does not exist.*input_boolean\.e2e_switch"):
        await call.run(
            _ctx(hass),
            {"domain": "switch", "service": "turn_on", "target": {"entity_id": "switch.e2e"}},
        )
    out = await _tool("get_entities").run(_ctx(hass), {"entity_ids": ["switch.e2e"]})
    assert out.data[0]["similar"][0] == "input_boolean.e2e_switch"


async def test_service_on_wrong_domain_is_refused(hass: HomeAssistant) -> None:
    hass.states.async_set("input_boolean.e2e_switch", "off")
    hass.services.async_register("switch", "turn_on", lambda _call: None)
    with pytest.raises(ToolError, match="Use the input_boolean domain"):
        await _tool("call_service").run(
            _ctx(hass),
            {
                "domain": "switch",
                "service": "turn_on",
                "target": {"entity_id": "input_boolean.e2e_switch"},
            },
        )


def test_dashboard_config_must_be_a_dashboard_and_main_one_asks() -> None:
    save = _tool("save_dashboard")
    with pytest.raises(ToolError, match="must be a JSON object"):  # cut off mid-string
        save.check_args({"config": "{'views': [{'cards': [{'entity': 'switch.e"})
    # Cut off only before the closing brackets: repaired.
    fixed = save.check_args({"config": "{'views': [{'cards': [{'entity': 'switch.e2e'}"})
    assert fixed["config"]["views"][0]["cards"] == [{"entity": "switch.e2e"}]
    with pytest.raises(ToolError, match="'views' list"):
        save.check_args({"config": {"cards": []}})
    ok = save.check_args({"config": {"views": [{"cards": []}]}})
    assert save.classify(None, ok).level is Level.RISKY  # replaces the main dashboard
    assert save.classify(None, {**ok, "url_path": "e2e-test"}).level is Level.WRITE


def test_booleans_and_bare_targets_sent_as_text_are_repaired() -> None:
    call = _tool("call_service")
    args = call.check_args(
        {
            "domain": "input_boolean",
            "service": "turn_on",
            "target": "input_boolean.a, input_boolean.b",
            "data": "{}",
            "return_response": "False",
        }
    )
    assert args["target"] == {"entity_id": ["input_boolean.a", "input_boolean.b"]}
    assert args["data"] == {} and args["return_response"] is False
    with pytest.raises(ToolError, match="true or false"):
        call.check_args({"domain": "a", "service": "b", "return_response": "maybe"})
    # target: "entity_id" with the real id in data: moved into target, where it is checked.
    args = call.check_args(
        {
            "domain": "light",
            "service": "turn_on",
            "target": "entity_id",
            "data": {"entity_id": "light.a", "brightness": 10},
        }
    )
    assert args["target"] == {"entity_id": "light.a"} and args["data"] == {"brightness": 10}
    assert "target" not in call.check_args({"domain": "a", "service": "b", "target": "entity_id"})


def test_unquoted_lists_and_automation_name_are_repaired() -> None:
    assert _tool("get_entities").check_args({"entity_ids": "[light.a, light.b]"})["entity_ids"] == [
        "light.a",
        "light.b",
    ]
    args = _tool("save_config_item").check_args(
        {"kind": "automation", "config": {"name": "Night off", "triggers": []}}
    )
    assert args["config"] == {"alias": "Night off", "triggers": []}


def test_config_cut_off_before_closing_brackets_is_repaired() -> None:
    tool = _tool("save_config_item")
    cut = "{'alias': 'Night', 'actions': [{'action': 'switch.turn_off', 'target': {'entity_id': 'switch.a'}}]"
    assert tool.check_args({"kind": "automation", "config": cut})["config"]["alias"] == "Night"
    # Only missing closers are added; mismatched brackets or open quotes stay errors.
    for bad in ("{'a': [1}", "{'a': 'open"):
        with pytest.raises(ToolError):
            tool.check_args({"kind": "automation", "config": bad})


def test_automation_kind_is_found_where_small_models_put_it() -> None:
    tool = _tool("save_config_item")
    assert (
        tool.check_args({"domain": "automation", "config": {"alias": "A"}})["kind"] == "automation"
    )
    args = tool.check_args({"config": {"kind": "script", "alias": "S"}})
    assert args["kind"] == "script" and args["config"] == {"alias": "S"}
    with pytest.raises(ToolError, match="kind"):
        tool.check_args({"domain": "light", "config": {}})


@pytest.mark.parametrize(
    ("path", "content", "match"),
    [
        ("packages/x.yaml", "a: [1, 2\n", "not valid YAML"),
        ("blueprints/automation/me/x.yaml", "blueprint:\n  name: X\n", "not a valid blueprint"),
        ("blueprints/script/me/x.yaml", "- 1\n", "not a blueprint"),
        ("python_scripts/x.py", "if True\n  pass\n", "syntax error"),
    ],
)
async def test_write_file_refuses_files_ha_could_not_load(
    hass: HomeAssistant, path: str, content: str, match: str
) -> None:
    with pytest.raises(ToolError, match=match):
        await _tool("write_file").preview(_ctx(hass), {"path": path, "content": content})


async def test_write_file_accepts_ha_tags_without_resolving_them(hass: HomeAssistant) -> None:
    content = "homeassistant:\n  packages: !include_dir_named packages\nkey: !secret k\n"
    preview = await _tool("write_file").preview(
        _ctx(hass), {"path": "configuration.yaml", "content": content}
    )
    assert "packages" in preview.diff
