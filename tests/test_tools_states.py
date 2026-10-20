"""State tools exercised against Home Assistant states, registries and recorder."""

from datetime import timedelta

from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from homeassistant.helpers.service import async_set_service_schema
import homeassistant.util.dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.llm_agent.approval import Level
from custom_components.llm_agent.tools import ToolError

from .test_tools import _ctx, _tool


@pytest.fixture
def mock_recorder_before_hass(recorder_db_url):
    """Prepare the recorder database before the autouse core setup creates hass."""


@pytest.fixture
def room(hass):
    area = ar.async_get(hass).async_create("Living Room")
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("test", "lamp")}, name="Lamp"
    )
    dr.async_get(hass).async_update_device(device.id, area_id=area.id)
    entity = er.async_get(hass).async_get_or_create(
        "light", "test", "lamp", suggested_object_id="lamp", device_id=device.id
    )
    hass.states.async_set(
        entity.entity_id,
        "on",
        {"friendly_name": "Reading Lamp", "brightness": 120, "icon": "mdi:lamp"},
    )
    hass.states.async_set("sensor.temperature", "21")
    return area, device, entity


async def test_search_entities_filters_text_domain_area_and_limits_results(hass, room):
    area, _, entity = room
    hass.states.async_set("light.other", "off", {"friendly_name": "Other Lamp"})
    tool = _tool("search_entities")
    out = await tool.run(_ctx(hass), {"query": "reading lamp", "domain": "light", "area": "living"})
    assert out.data == {
        "total": 1,
        "entities": [
            {"entity_id": entity.entity_id, "name": "Reading Lamp", "state": "on", "area": area.id}
        ],
    }
    out = await tool.run(_ctx(hass), {"domain": "light", "limit": 1})
    assert out.data["total"] == 2
    assert len(out.data["entities"]) == 1
    assert (await tool.run(_ctx(hass), {"area": "nonexistent"})).data == {
        "total": 0,
        "entities": [],
    }


async def test_search_entities_rejects_invalid_limit(hass):
    with pytest.raises(ToolError, match="limit"):
        await _tool("search_entities").run(_ctx(hass), {"limit": "invalid"})


async def test_get_entities_returns_attributes_area_and_missing_entity(hass, room):
    area, _, entity = room
    out = await _tool("get_entities").run(
        _ctx(hass), {"entity_ids": [entity.entity_id, "light.missing"]}
    )
    state = out.data[0]
    assert state == {
        "entity_id": entity.entity_id,
        "name": "Reading Lamp",
        "state": "on",
        "area": area.id,
        "attributes": {"brightness": 120},
        "last_changed": hass.states.get(entity.entity_id).last_changed.isoformat(
            timespec="seconds"
        ),
    }
    assert out.data[1] == {"entity_id": "light.missing", "error": "not found"}


async def test_get_entities_limits_rows(hass):
    out = await _tool("get_entities").run(
        _ctx(hass), {"entity_ids": [f"sensor.test_{i}" for i in range(55)]}
    )
    assert len(out.data) == 50
    assert out.data[-1] == {"entity_id": "sensor.test_49", "error": "not found"}


async def test_get_entities_treats_null_as_empty_and_rejects_non_lists(hass):
    out = await _tool("get_entities").run(_ctx(hass), {"entity_ids": None})
    assert not out.data
    with pytest.raises(ToolError, match="entity_ids"):
        await _tool("get_entities").run(_ctx(hass), {"entity_ids": 5})


async def test_get_history_limits_rows_and_keeps_last_state(hass, recorder_mock, freezer):
    start = dt_util.utcnow()
    for i in range(6):
        freezer.move_to(start + timedelta(minutes=i))
        hass.states.async_set("sensor.temperature", str(i))
        await async_wait_recording_done(hass)
    freezer.move_to(start + timedelta(minutes=7))
    out = await _tool("get_history").run(
        _ctx(hass), {"entity_ids": ["sensor.temperature"], "hours": 1, "max_points": 3}
    )
    assert list(out.data) == ["sensor.temperature"]
    points = out.data["sensor.temperature"]
    assert len(points) == 3
    assert [point[1] for point in points] == ["0", "2", "5"]
    assert dt_util.parse_datetime(points[-1][0]) == start + timedelta(minutes=5)


async def test_get_history_rejects_invalid_hours(hass):
    with pytest.raises(ToolError, match="hours"):
        await _tool("get_history").run(
            _ctx(hass), {"entity_ids": ["sensor.temperature"], "hours": "invalid"}
        )


async def test_render_template_reads_real_states(hass):
    hass.states.async_set("sensor.temperature", "21")
    out = await _tool("render_template").run(
        _ctx(hass), {"template": "Temperature: {{ states('sensor.temperature') }}"}
    )
    assert out.data == {"result": "Temperature: 21", "updates_on": ["sensor.temperature"]}
    assert (await _tool("render_template").run(_ctx(hass), {"template": "{{ 1 + 1 }}"})).data == "2"


async def test_render_template_reports_syntax_error(hass):
    with pytest.raises(ToolError, match="Template error"):
        await _tool("render_template").run(_ctx(hass), {"template": "{{ invalid"})


async def test_list_services_returns_names_and_field_descriptions(hass):
    async_mock_service(hass, "llm_agent", "test_action")
    async_set_service_schema(
        hass,
        "llm_agent",
        "test_action",
        {
            "description": "A local test service",
            "target": {"entity": [{"domain": "light"}]},
            "fields": {
                "brightness": {
                    "required": True,
                    "selector": {"number": {}},
                    "description": "Brightness",
                },
                "advanced": {"fields": {"transition": {"selector": {"number": {}}}}},
            },
        },
    )
    tool = _tool("list_services")
    out = await tool.run(_ctx(hass), {})
    assert out.data["llm_agent"] == ["test_action"]
    details = await tool.run(_ctx(hass), {"domain": "llm_agent"})
    assert details.data == {
        "test_action": {
            "description": "A local test service",
            "fields": {"brightness": "required; number; Brightness", "transition": "number"},
            "target": True,
        }
    }


async def test_list_services_rejects_unknown_domain(hass):
    with pytest.raises(ToolError, match="No services for domain nonexistent"):
        await _tool("list_services").run(_ctx(hass), {"domain": "nonexistent"})


async def test_call_service_passes_target_data_user_and_returns_states(hass, room, hass_admin_user):
    area, _, entity = room
    calls = async_mock_service(hass, "light", "turn_on")
    out = await _tool("call_service").run(
        _ctx(hass, hass_admin_user.id),
        {
            "domain": "light",
            "service": "turn_on",
            "target": {"area_id": area.id},
            "data": {"brightness": 200},
        },
    )
    assert len(calls) == 1
    assert calls[0].data == {"area_id": area.id, "brightness": 200}
    assert calls[0].context.user_id == hass_admin_user.id
    assert out.data == {
        "ok": True,
        "states": [
            {"entity_id": entity.entity_id, "name": "Reading Lamp", "state": "on", "area": area.id}
        ],
    }
    assert out.summary == "Called light.turn_on"


async def test_call_service_returns_response(hass):
    async def respond(call):
        return {"answer": 42}

    hass.services.async_register("test", "answer", respond, supports_response=SupportsResponse.ONLY)
    out = await _tool("call_service").run(
        _ctx(hass), {"domain": "test", "service": "answer", "return_response": True}
    )
    assert out.data == {"ok": True, "response": {"answer": 42}}


async def test_call_service_rejects_missing_service(hass):
    with pytest.raises(ToolError, match=r"Service light\.nonexistent does not exist"):
        await _tool("call_service").run(_ctx(hass), {"domain": "light", "service": "nonexistent"})


async def test_call_service_reports_service_failure(hass):
    async def fail(call):
        raise HomeAssistantError("Cannot turn on")

    hass.services.async_register("light", "turn_on", fail)
    with pytest.raises(ToolError, match=r"light\.turn_on failed: Cannot turn on"):
        await _tool("call_service").run(_ctx(hass), {"domain": "light", "service": "turn_on"})


@pytest.mark.parametrize(
    ("domain", "service", "expected"),
    [
        ("light", "turn_on", Level.WRITE),
        ("lock", "unlock", Level.RISKY),
        ("lock", "lock", Level.WRITE),
    ],
)
def test_call_service_classifies_domain_risk(hass, domain, service, expected):
    assert (
        _tool("call_service").classify(_ctx(hass), {"domain": domain, "service": service}).level
        is expected
    )


@pytest.mark.parametrize("target_kind", ["entity_id", "device_id", "area_id", "data"])
def test_call_service_classifies_expanded_targets(hass, room, target_kind):
    area, device, _ = room
    entity = er.async_get(hass).async_get_or_create("lock", "test", "door", device_id=device.id)
    args = {"domain": "homeassistant", "service": "turn_off"}
    if target_kind == "data":
        args["data"] = {"entity_id": entity.entity_id}
    else:
        args["target"] = {
            target_kind: {
                "entity_id": entity.entity_id,
                "device_id": device.id,
                "area_id": area.id,
            }[target_kind]
        }
    assert _tool("call_service").classify(_ctx(hass), args).level is Level.RISKY


async def test_render_template_takes_variables_and_reports_what_it_listens_to(hass):
    hass.states.async_set("sensor.temperature", "21")
    out = await _tool("render_template").run(
        _ctx(hass),
        {
            "template": "{{ trigger.to_state }} {{ states('sensor.temperature') | int + 1 }}",
            "variables": {"trigger": {"to_state": "on"}},
        },
    )
    assert out.data["result"] == "on 22"
    assert out.data["updates_on"] == ["sensor.temperature"]


async def test_render_template_strict_catches_typos(hass):
    tool = _tool("render_template")
    loose = await tool.run(_ctx(hass), {"template": "{{ tempreature }}"})
    assert loose.data == {"result": "", "warnings": ["'tempreature' is undefined"]}
    with pytest.raises(ToolError, match="tempreature"):
        await tool.run(_ctx(hass), {"template": "{{ tempreature }}", "strict": True})
