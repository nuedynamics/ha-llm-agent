"""Integration tools run real config-entry flows without external services."""

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryDisabler, ConfigEntryState
import probatio
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

from custom_components.llm_agent.approval import Level
from custom_components.llm_agent.tools import ToolError

from .test_tools import _ctx, _tool


class LocalFlow(config_entries.ConfigFlow):
    """An entirely in-process integration with a required name field."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=probatio.Schema({probatio.Required("name"): str}), errors={}
        )


@pytest.fixture
def local_integration(hass):
    events = []

    async def setup_entry(hass, entry):
        events.append(("setup", entry.entry_id))
        return True

    async def unload_entry(hass, entry):
        events.append(("unload", entry.entry_id))
        return True

    mock_integration(
        hass,
        MockModule(
            "test",
            async_setup_entry=setup_entry,
            async_unload_entry=unload_entry,
            partial_manifest={"config_flow": True},
        ),
    )
    mock_platform(hass, "test.config_flow")
    with mock_config_flow("test", LocalFlow):
        yield events


async def test_integrations_lists_entries_and_filters_domain(hass, local_integration):
    entry = MockConfigEntry(domain="test", title="Local", disabled_by=ConfigEntryDisabler.USER)
    entry.add_to_hass(hass)
    other = MockConfigEntry(domain="other", title="Other")
    other.add_to_hass(hass)
    tool = _tool("integrations")
    all_entries = await tool.run(_ctx(hass), {"action": "list"})
    assert {item["entry_id"] for item in all_entries.data["entries"]} == {
        entry.entry_id,
        other.entry_id,
    }
    out = await tool.run(_ctx(hass), {"action": "list", "domain": "test"})
    assert out.data == {
        "entries": [
            {
                "entry_id": entry.entry_id,
                "domain": "test",
                "title": "Local",
                "state": "not_loaded",
                "disabled": True,
            }
        ],
        "in_progress": [],
    }


async def test_integrations_starts_flow_and_lists_progress(hass, local_integration):
    tool = _tool("integrations")
    started = await tool.run(_ctx(hass), {"action": "start_flow", "domain": "test"})
    assert started.summary == "Started test setup"
    assert started.data["type"] == "form"
    assert started.data["handler"] == "test"
    assert started.data["step_id"] == "user"
    assert started.data["errors"] == {}
    assert started.data["data_schema"] == [{"name": "name", "required": True, "type": "string"}]
    listed = await tool.run(_ctx(hass), {"action": "list", "domain": "test"})
    assert listed.data["in_progress"] == [
        {"flow_id": started.data["flow_id"], "handler": "test", "step_id": "user", "source": "user"}
    ]
    assert (await tool.run(_ctx(hass), {"action": "list", "domain": "other"})).data[
        "in_progress"
    ] == []


async def test_integrations_continues_flow_and_creates_entry(hass, local_integration):
    tool = _tool("integrations")
    started = await tool.run(_ctx(hass), {"action": "start_flow", "domain": "test"})
    out = await tool.run(
        _ctx(hass),
        {
            "action": "continue_flow",
            "flow_id": started.data["flow_id"],
            "user_input": {"name": "Local Sensor"},
        },
    )
    await hass.async_block_till_done()
    assert out.data["type"] == "create_entry"
    assert out.data["title"] == "Local Sensor"
    entry = hass.config_entries.async_get_entry(out.data["entry_id"])
    assert entry is not None and entry.data == {"name": "Local Sensor"}
    assert "data" not in out.data and "result" not in out.data
    assert (await tool.run(_ctx(hass), {"action": "list"})).data["in_progress"] == []


async def test_integrations_aborts_flow(hass, local_integration):
    tool = _tool("integrations")
    started = await tool.run(_ctx(hass), {"action": "start_flow", "domain": "test"})
    out = await tool.run(_ctx(hass), {"action": "abort_flow", "flow_id": started.data["flow_id"]})
    assert out.data == {"ok": True}
    assert hass.config_entries.flow.async_progress() == []


async def test_integrations_reloads_entry(hass, local_integration):
    entry = MockConfigEntry(domain="test", title="Local")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    out = await _tool("integrations").run(
        _ctx(hass), {"action": "reload", "entry_id": entry.entry_id}
    )
    assert out.data == {"ok": True}
    assert out.summary == "Reloaded Local"
    assert local_integration == [
        ("setup", entry.entry_id),
        ("unload", entry.entry_id),
        ("setup", entry.entry_id),
    ]
    assert entry.state is ConfigEntryState.LOADED


async def test_integrations_removes_entry_without_optional_backup(hass, local_integration):
    entry = MockConfigEntry(domain="test", title="Local")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    out = await _tool("integrations").run(
        _ctx(hass, backup_before_risky=False), {"action": "remove", "entry_id": entry.entry_id}
    )
    assert out.data == {"ok": True, "backup": ""}
    assert out.summary == "Removed Local"
    assert hass.config_entries.async_get_entry(entry.entry_id) is None
    assert local_integration[-1] == ("unload", entry.entry_id)


async def test_integrations_requires_domain_to_start_flow(hass):
    with pytest.raises(ToolError, match="domain is required"):
        await _tool("integrations").run(_ctx(hass), {"action": "start_flow"})


@pytest.mark.parametrize("action", ["continue_flow", "abort_flow"])
async def test_integrations_rejects_unknown_flow(hass, action):
    with pytest.raises(ToolError, match="Unknown or finished flow_id"):
        await _tool("integrations").run(_ctx(hass), {"action": action, "flow_id": "missing"})


@pytest.mark.parametrize("action", ["reload", "remove"])
async def test_integrations_rejects_missing_entry(hass, action):
    with pytest.raises(ToolError, match="Config entry missing not found"):
        await _tool("integrations").run(_ctx(hass), {"action": action, "entry_id": "missing"})


async def test_integrations_rejects_unknown_action(hass, local_integration):
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    with pytest.raises(ToolError, match="Unknown action invalid"):
        await _tool("integrations").run(
            _ctx(hass), {"action": "invalid", "entry_id": entry.entry_id}
        )


async def test_integrations_reports_invalid_flow_input(hass, local_integration):
    tool = _tool("integrations")
    started = await tool.run(_ctx(hass), {"action": "start_flow", "domain": "test"})
    with pytest.raises(ToolError, match="Invalid input"):
        await tool.run(
            _ctx(hass),
            {
                "action": "continue_flow",
                "flow_id": started.data["flow_id"],
                "user_input": {"name": 123},
            },
        )


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("list", Level.READ),
        ("start_flow", Level.RISKY),
        ("continue_flow", Level.RISKY),
        ("abort_flow", Level.WRITE),
        ("reload", Level.WRITE),
        ("remove", Level.RISKY),
    ],
)
def test_integrations_classifies_action_risk(hass, action, expected):
    risk = _tool("integrations").classify(_ctx(hass), {"action": action, "entry_id": "local"})
    assert risk.level is expected
    if action == "remove":
        assert risk.reason == "removes integration entry local"
