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
        (
            "blueprints/automation/me/x.yaml",
            "blueprint:\n  name: X\n  domain: automation\nactions: !input undeclared\n",
            "undeclared",
        ),
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


async def test_blueprint_check_never_reads_other_files_or_the_environment(
    hass: HomeAssistant, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (config_dir / "secrets.yaml").write_text("pw: PROTECTED_VALUE\n")
    monkeypatch.setenv("HLA_TEST_VALUE", "ENVIRONMENT_VALUE")
    for name in (f"!include {config_dir / 'secrets.yaml'}", "!env_var HLA_TEST_VALUE"):
        content = f"blueprint:\n  name: {name}\n  domain: automation\n"
        with pytest.raises(ToolError) as err:
            await _tool("write_file").preview(
                _ctx(hass), {"path": "blueprints/automation/me/x.yaml", "content": content}
            )
        assert "PROTECTED_VALUE" not in str(err.value)
        assert "ENVIRONMENT_VALUE" not in str(err.value)


@pytest.mark.parametrize(
    "content", ["date: 2026-13-40\n", "x: " + "[" * 2000 + "0" + "]" * 2000 + "\n"]
)
async def test_hostile_yaml_is_refused_not_crashed(hass: HomeAssistant, content: str) -> None:
    with pytest.raises(ToolError, match="Not saved"):
        await _tool("write_file").preview(
            _ctx(hass), {"path": "packages/x.yaml", "content": content}
        )


async def test_file_checks_run_in_the_executor(hass: HomeAssistant) -> None:
    from custom_components.llm_agent.tools.files import check_syntax

    jobs: list[object] = []
    real = hass.async_add_executor_job

    def spy(target, *args):
        jobs.append(target)
        return real(target, *args)

    with patch.object(hass, "async_add_executor_job", side_effect=spy):
        await _tool("write_file").preview(
            _ctx(hass), {"path": "packages/x.yaml", "content": "a: 1\n"}
        )
    assert check_syntax in jobs


def test_ws_risky_prefix_and_words_beat_a_read_suffix() -> None:
    assert classify_ws("config/auth/list").level is Level.RISKY
    assert classify_ws("system_log/clear").level is Level.RISKY
    assert classify_ws("get_states").level is Level.READ


async def test_execute_script_needs_a_person_whatever_the_rules(hass) -> None:
    tool = WebSocketTool()
    assert await tool.needs_person(None, {"command": "execute_script", "payload": {}})
    assert not await tool.needs_person(None, {"command": "lovelace/dashboards/list"})


def test_ws_reads_under_risky_prefixes_stay_reads() -> None:
    assert classify_ws("config_entries/get").level is Level.READ
    assert classify_ws("auth/current_user").level is Level.RISKY


async def test_rules_see_the_members_of_a_scene(hass: HomeAssistant) -> None:
    from custom_components.llm_agent.approval import match_rule, parse_rules
    from custom_components.llm_agent.tools.states import CallService

    hass.states.async_set("scene.leave", "scening", {"entity_id": ["light.hall", "lock.front"]})
    tool = CallService()
    args = {"domain": "scene", "service": "turn_on", "target": {"entity_id": ["scene.leave"]}}
    rules = parse_rules("allow scene.*\ndeny lock.*")[0]
    rule = match_rule(rules, tool.rule_groups(ToolContext(hass, None, {}, None), args), False)
    assert rule is not None and rule.verb == "deny"


async def test_secrets_files_in_subfolders_are_protected(
    hass: HomeAssistant, config_dir: Path
) -> None:
    (config_dir / "packages").mkdir()
    (config_dir / "packages" / "secrets.yaml").write_text("pw: NESTED\n")
    access = FileAccess(_ctx(hass))
    for rel in ("packages/secrets.yaml", "packages/secrets.yaml.corrupt.1", ".llm_agent/x.json"):
        with pytest.raises(ToolError):
            access.resolve(rel)


async def test_config_items_never_resolve_includes_and_keep_tags(
    hass: HomeAssistant, config_dir: Path
) -> None:
    assert await async_setup_component(hass, "script", {})
    (config_dir / "secrets.yaml").write_text("pw: hunter2\nwifi: hunter2\n")
    (config_dir / "scripts.yaml").write_text(
        "leak:\n  sequence: !include secrets.yaml\nother:\n  alias: !secret wifi\n  sequence: []\n"
    )
    ctx = _ctx(hass)
    out = await _tool("get_config_item").run(ctx, {"kind": "script", "id": "leak"})
    assert "hunter2" not in str(out.data)
    assert out.data["config"]["sequence"] == "!include secrets.yaml"
    with patch("custom_components.llm_agent.tools.config_items._validate"):
        await _tool("save_config_item").run(
            ctx, {"kind": "script", "id": "new", "config": {"alias": "New", "sequence": []}}
        )
    text = (config_dir / "scripts.yaml").read_text()
    assert "sequence: !include secrets.yaml" in text and "alias: !secret wifi" in text
    assert "hunter2" not in text


async def test_config_items_refuse_a_symlink_to_a_protected_file(
    hass: HomeAssistant, config_dir: Path
) -> None:
    (config_dir / "scripts.yaml").unlink()
    (config_dir / "scripts.yaml").symlink_to(config_dir / "secrets.yaml")
    with pytest.raises(ToolError):
        await _tool("list_config_items").run(_ctx(hass), {"kind": "script"})


async def test_a_forged_snapshot_cannot_restore_a_protected_file(
    hass: HomeAssistant, config_dir: Path
) -> None:
    ctx = _ctx(hass)
    with pytest.raises(ToolError):
        await _tool("write_file").run(
            ctx, {"path": ".llm_agent/snapshots/forged.json", "content": "{}"}
        )
    ctx.snapshots.dir.mkdir(parents=True, exist_ok=True)
    (ctx.snapshots.dir / "forged.json").write_text(
        '{"id":"forged","kind":"file","label":"x","path":"secrets.yaml","content":"pw: CHANGED\\n"}'
    )
    with pytest.raises(ToolError):
        await _tool("undo").run(ctx, {"snapshot_id": "forged"})
    assert (config_dir / "secrets.yaml").read_text() == "pw: hunter2\n"


@pytest.mark.parametrize(
    ("actions", "level"),
    [
        ([{"action": "light.turn_on", "target": {"entity_id": "light.porch"}}], Level.WRITE),
        ([{"action": "lock.unlock", "target": {"entity_id": "lock.front_door"}}], Level.RISKY),
        ([{"if": [], "then": [{"service": "alarm_control_panel.alarm_disarm"}]}], Level.RISKY),
        ([{"action": "{{ states('input_text.cmd') }}"}], Level.RISKY),
        ([{"action": "homeassistant.turn_on", "target": {"entity_id": "{{ x }}"}}], Level.RISKY),
        ([{"device_id": "abc", "domain": "lock", "type": "unlock"}], Level.RISKY),
    ],
)
async def test_saving_an_automation_is_as_risky_as_its_actions(
    hass: HomeAssistant, actions: list, level: Level
) -> None:
    args = {
        "kind": "automation",
        "config": {
            "alias": "x",
            "triggers": [{"trigger": "event", "event_data": {"action": "UNLOCK"}}],
            "actions": actions,
        },
    }
    assert _tool("save_config_item").classify(_ctx(hass), args).level is level


async def test_a_new_script_never_replaces_one_with_the_same_name(
    hass: HomeAssistant, config_dir: Path
) -> None:
    (config_dir / "scripts.yaml").write_text("evening_lights:\n  alias: Old\n  sequence: []\n")
    save = _tool("save_config_item")
    plan = await save._plan(_ctx(hass), {"kind": "script", "config": {"alias": "Evening lights"}})
    assert plan[0] == "evening_lights_2" and plan[2] is None
    plan = await save._plan(_ctx(hass), {"kind": "script", "config": {"alias": "Café lights"}})
    assert plan[0] == "cafe_lights"


async def test_an_invalid_scene_is_not_saved(hass: HomeAssistant, config_dir: Path) -> None:
    (config_dir / "scenes.yaml").write_text("- id: evening\n  name: Evening\n  entities: {}\n")
    with pytest.raises(ToolError, match="name"):
        await _tool("save_config_item").run(
            _ctx(hass),
            {"kind": "scene", "id": "evening", "config": {"entities": {"light.k": "on"}}},
        )
    assert "name: Evening" in (config_dir / "scenes.yaml").read_text()


async def test_items_without_an_id_cannot_be_picked(hass: HomeAssistant, config_dir: Path) -> None:
    (config_dir / "scenes.yaml").write_text(
        "- name: First\n  entities: {light.a: 'on'}\n- name: Second\n  entities: {light.b: 'on'}\n"
    )
    ctx = _ctx(hass)
    listed = await _tool("list_config_items").run(ctx, {"kind": "scene"})
    assert [i["id"] for i in listed.data] == [None, None]
    with pytest.raises(ToolError):
        await _tool("get_config_item").run(ctx, {"kind": "scene", "id": "None"})


async def test_undoing_an_older_change_never_erases_a_later_one(
    hass: HomeAssistant, config_dir: Path
) -> None:
    ctx = _ctx(hass)
    write = _tool("write_file")
    first = await write.run(ctx, {"path": "notes.txt", "content": "first"})
    second = await write.run(ctx, {"path": "notes.txt", "content": "second"})
    undo = _tool("undo")
    with pytest.raises(ToolError, match="changed since"):
        await undo.run(ctx, {"snapshot_id": first.snapshot_id})
    assert (config_dir / "notes.txt").read_text() == "second"
    await undo.run(ctx, {"snapshot_id": second.snapshot_id})
    await undo.run(ctx, {"snapshot_id": first.snapshot_id})
    assert not (config_dir / "notes.txt").exists()


async def test_concurrent_file_edits_both_land(hass: HomeAssistant, config_dir: Path) -> None:
    import asyncio

    (config_dir / "two.yaml").write_text("one: 0\ntwo: 0\n")
    ctx = _ctx(hass)
    write = _tool("write_file")
    await asyncio.gather(
        write.run(ctx, {"path": "two.yaml", "old": "one: 0", "new": "one: 1"}),
        write.run(ctx, {"path": "two.yaml", "old": "two: 0", "new": "two: 1"}),
    )
    assert (config_dir / "two.yaml").read_text() == "one: 1\ntwo: 1\n"


async def test_read_file_returns_only_the_lines_asked_for(
    hass: HomeAssistant, config_dir: Path
) -> None:
    (config_dir / "big.log").write_text("".join(f"line {i}\n" for i in range(1000)))
    out = await _tool("read_file").run(_ctx(hass), {"path": "big.log", "offset": 10, "limit": 2})
    assert out.data["content"] == "line 10\nline 11" and out.data["total_lines"] == 1000


async def test_shell_timeout_stops_the_whole_command(hass: HomeAssistant, config_dir: Path) -> None:
    import asyncio

    shell = _tool("shell", allow_shell=True)
    ctx = _ctx(hass, allow_shell=True)
    with pytest.raises(ToolError, match="timed out"):
        await shell.run(ctx, {"command": "(sleep 2; touch late.txt) & wait", "timeout": 1})
    await asyncio.sleep(1.5)
    assert not (config_dir / "late.txt").exists()
    out = await shell.run(ctx, {"command": "head -c 100000 /dev/zero | tr '\\\\0' x"})
    assert len(out.data["output"]) < 21000 and "truncated" in out.data["output"]
