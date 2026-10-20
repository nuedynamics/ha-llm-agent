"""Registry tools use the real area, device and entity registries."""

from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.llm_agent.approval import Level
from custom_components.llm_agent.tools import ToolError

from .test_tools import _ctx, _tool


@pytest.fixture
def registered(hass):
    area = ar.async_get(hass).async_create("Kitchen")
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("test", "lamp")},
        name="Lamp",
        manufacturer="Example",
        model="LED",
    )
    dr.async_get(hass).async_update_device(device.id, area_id=area.id)
    entity = er.async_get(hass).async_get_or_create("light", "test", "lamp", device_id=device.id)
    return area, device, entity


async def test_list_areas_includes_empty_areas_and_device_counts(hass, registered):
    area, _, _ = registered
    empty = ar.async_get(hass).async_create("Empty")
    out = await _tool("list_areas").run(_ctx(hass), {})
    assert out.data == [
        {"id": area.id, "name": "Kitchen", "floor": None, "devices": 1},
        {"id": empty.id, "name": "Empty", "floor": None, "devices": 0},
    ]


async def test_list_devices_returns_metadata_and_entities(hass, registered):
    area, device, entity = registered
    out = await _tool("list_devices").run(_ctx(hass), {"area": area.id, "query": "example"})
    assert out.data == [
        {
            "id": device.id,
            "name": "Lamp",
            "manufacturer": "Example",
            "model": "LED",
            "area": area.id,
            "disabled": False,
            "entities": [entity.entity_id],
        }
    ]
    assert (await _tool("list_devices").run(_ctx(hass), {"area": "missing"})).data == []
    assert (await _tool("list_devices").run(_ctx(hass), {"query": "missing"})).data == []


async def test_list_devices_honors_user_name_and_limit(hass, registered):
    _, device, _ = registered
    dr.async_get(hass).async_update_device(device.id, name_by_user="Desk Lamp")
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("test", "other")}, name="Other"
    )
    out = await _tool("list_devices").run(_ctx(hass), {"limit": 1})
    assert len(out.data) == 1
    assert out.data[0]["name"] == "Desk Lamp"


async def test_list_devices_rejects_invalid_limit(hass):
    with pytest.raises(ToolError, match="limit"):
        await _tool("list_devices").run(_ctx(hass), {"limit": "invalid"})


async def test_update_registry_creates_updates_and_deletes_area(hass):
    tool = _tool("update_registry")
    ctx = _ctx(hass)
    created = await tool.run(
        ctx, {"kind": "area", "action": "create", "changes": {"name": "Office", "icon": "mdi:desk"}}
    )
    assert set(created.data) == {"area_id"}
    area_id = created.data["area_id"]
    assert ar.async_get(hass).async_get_area(area_id).name == "Office"
    assert created.summary == "Created area Office"
    updated = await tool.run(
        ctx,
        {
            "kind": "area",
            "action": "update",
            "id": area_id,
            "changes": {"name": "Study", "icon": "mdi:book"},
        },
    )
    assert updated.data == {"ok": True}
    area = ar.async_get(hass).async_get_area(area_id)
    assert (area.name, area.icon) == ("Study", "mdi:book")
    deleted = await tool.run(ctx, {"kind": "area", "action": "delete", "id": area_id})
    assert deleted.data == {"ok": True}
    assert ar.async_get(hass).async_get_area(area_id) is None


async def test_update_registry_moves_renames_and_disables_device(hass, registered):
    _, device, _ = registered
    area = ar.async_get(hass).async_create("Office")
    tool = _tool("update_registry")
    args = {
        "kind": "device",
        "action": "update",
        "id": device.id,
        "changes": {"name": "Desk Light", "area_id": area.id, "disabled": True},
    }
    out = await tool.run(_ctx(hass), args)
    assert out.data == {"ok": True}
    updated = dr.async_get(hass).async_get(device.id)
    assert (updated.name_by_user, updated.area_id, updated.disabled_by) == (
        "Desk Light",
        area.id,
        dr.DeviceEntryDisabler.USER,
    )
    args["changes"] = {"disabled": False}
    await tool.run(_ctx(hass), args)
    assert dr.async_get(hass).async_get(device.id).disabled_by is None


async def test_update_registry_changes_entity_metadata_and_id(hass, registered):
    area, _, entity = registered
    tool = _tool("update_registry")
    out = await tool.run(
        _ctx(hass),
        {
            "kind": "entity",
            "action": "update",
            "id": entity.entity_id,
            "changes": {
                "name": "Desk Light",
                "icon": "mdi:desk",
                "area_id": area.id,
                "new_entity_id": "light.desk",
                "disabled": True,
                "hidden": True,
            },
        },
    )
    assert out.data == {"entity_id": "light.desk"}
    assert out.summary == "Updated light.desk"
    updated = er.async_get(hass).async_get("light.desk")
    assert (updated.name, updated.icon, updated.area_id) == ("Desk Light", "mdi:desk", area.id)
    assert updated.disabled_by is er.RegistryEntryDisabler.USER
    assert updated.hidden_by is er.RegistryEntryHider.USER
    await tool.run(
        _ctx(hass),
        {
            "kind": "entity",
            "action": "update",
            "id": "light.desk",
            "changes": {"disabled": False, "hidden": False},
        },
    )
    updated = er.async_get(hass).async_get("light.desk")
    assert updated.disabled_by is None and updated.hidden_by is None
    removed = await tool.run(_ctx(hass), {"kind": "entity", "action": "delete", "id": "light.desk"})
    assert removed.data == {"ok": True}
    assert er.async_get(hass).async_get("light.desk") is None


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        ("area", "Area missing not found"),
        ("device", "Device missing not found"),
        ("entity", "Entity missing is not in the entity registry"),
    ],
)
async def test_update_registry_rejects_missing_item(hass, kind, message):
    with pytest.raises(ToolError, match=message):
        await _tool("update_registry").run(
            _ctx(hass), {"kind": kind, "action": "update", "id": "missing"}
        )


async def test_update_registry_rejects_device_deletion(hass, registered):
    _, device, _ = registered
    with pytest.raises(ToolError, match="Devices can only be updated"):
        await _tool("update_registry").run(
            _ctx(hass), {"kind": "device", "action": "delete", "id": device.id}
        )
    assert dr.async_get(hass).async_get(device.id) is not None


async def test_update_registry_rejects_entity_creation(hass, registered):
    _, _, entity = registered
    with pytest.raises(ToolError, match="Entities are created by integrations or helpers"):
        await _tool("update_registry").run(
            _ctx(hass), {"kind": "entity", "action": "create", "id": entity.entity_id}
        )


async def test_update_registry_wraps_invalid_entity_id(hass, registered):
    _, _, entity = registered
    with pytest.raises(ToolError, match=r"[Ii]nvalid"):
        await _tool("update_registry").run(
            _ctx(hass),
            {
                "kind": "entity",
                "action": "update",
                "id": entity.entity_id,
                "changes": {"new_entity_id": "not an entity id"},
            },
        )


@pytest.mark.parametrize(
    ("action", "expected"),
    [("create", Level.WRITE), ("update", Level.WRITE), ("delete", Level.RISKY)],
)
def test_update_registry_classifies_mutation_risk(hass, action, expected):
    risk = _tool("update_registry").classify(
        _ctx(hass), {"kind": "area", "action": action, "id": "office"}
    )
    assert risk.level is expected
    if action == "delete":
        assert risk.reason == "deletes area office"
