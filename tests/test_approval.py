"""Risk classification and approval modes."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.llm_agent.approval import Level, Risk, classify_service, needs_approval


async def test_classify_service(hass: HomeAssistant) -> None:
    hass.states.async_set("cover.garage", "closed", {"device_class": "garage"})
    hass.states.async_set("cover.blind", "closed", {"device_class": "blind"})
    hass.states.async_set("lock.front", "locked")
    assert classify_service(hass, "light", "turn_on", ["light.a"]).level is Level.WRITE
    assert classify_service(hass, "lock", "unlock", ["lock.front"]).level is Level.RISKY
    assert classify_service(hass, "lock", "lock", ["lock.front"]).level is Level.WRITE
    assert classify_service(hass, "cover", "open_cover", ["cover.garage"]).level is Level.RISKY
    assert classify_service(hass, "cover", "open_cover", ["cover.blind"]).level is Level.WRITE
    assert classify_service(hass, "homeassistant", "turn_off", ["lock.front"]).level is Level.RISKY
    assert classify_service(hass, "homeassistant", "restart", []).level is Level.RISKY


def test_needs_approval_modes() -> None:
    assert needs_approval("ask_all", Risk.write())
    assert not needs_approval("ask_all", Risk.read())
    assert not needs_approval("ask_risky", Risk.write())
    assert needs_approval("ask_risky", Risk.risky("x"))
    assert not needs_approval("autopilot", Risk.risky("x"))


async def test_services_that_run_code_or_scripts_are_risky(hass: HomeAssistant) -> None:
    for domain, service in [
        ("script", "turn_on"),
        ("script", "front_door_open"),
        ("automation", "trigger"),
        ("shell_command", "anything"),
        ("python_script", "x"),
        ("pyscript", "x"),
        ("command_line", "x"),
        ("rest_command", "x"),
        ("mqtt", "publish"),
        ("scene", "apply"),
        ("scene", "create"),
    ]:
        assert classify_service(hass, domain, service, []).level is Level.RISKY, domain
    for entity in ("script.unlock_all", "automation.away"):
        assert classify_service(hass, "homeassistant", "turn_on", [entity]).level is Level.RISKY


async def test_a_scene_is_judged_by_the_devices_it_sets(hass: HomeAssistant) -> None:
    hass.states.async_set("scene.movie", "scening", {"entity_id": ["light.tv"]})
    hass.states.async_set("scene.leave", "scening", {"entity_id": ["light.hall", "lock.front"]})
    hass.states.async_set("scene.odd", "scening", {})
    assert classify_service(hass, "scene", "turn_on", ["scene.movie"]).level is Level.WRITE
    assert classify_service(hass, "scene", "turn_on", ["scene.leave"]).level is Level.RISKY
    assert classify_service(hass, "scene", "turn_on", ["scene.odd"]).level is Level.RISKY
    assert classify_service(hass, "homeassistant", "turn_on", ["scene.leave"]).level is Level.RISKY


async def test_a_group_is_judged_by_its_members(hass: HomeAssistant) -> None:
    hass.states.async_set("cover.garage", "closed", {"device_class": "garage"})
    hass.states.async_set("cover.all", "closed", {"entity_id": ["cover.blind", "cover.garage"]})
    hass.states.async_set("group.night", "off", {"entity_id": ["group.inner"]})
    hass.states.async_set("group.inner", "off", {"entity_id": ["script.unlock"]})
    assert classify_service(hass, "cover", "open_cover", ["cover.all"]).level is Level.RISKY
    assert classify_service(hass, "homeassistant", "turn_on", ["group.night"]).level is Level.RISKY


async def test_refreshing_a_script_is_not_running_it(hass: HomeAssistant) -> None:
    risk = classify_service(hass, "homeassistant", "update_entity", ["script.unlock"])
    assert risk.level is Level.WRITE


async def test_a_parent_device_target_reaches_its_child_devices(hass: HomeAssistant) -> None:
    from homeassistant.helpers import device_registry as dr, entity_registry as er
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.llm_agent.tools.states import expand_target

    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    devices = dr.async_get(hass)
    hub = devices.async_get_or_create(config_entry_id=entry.entry_id, identifiers={("t", "hub")})
    door = devices.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("t", "door")}, via_device_id=hub.id
    )
    er.async_get(hass).async_get_or_create(
        "cover", "test", "garage", device_id=door.id, suggested_object_id="garage"
    )
    assert "cover.garage" in expand_target(hass, {"device_id": hub.id}, "cover")
