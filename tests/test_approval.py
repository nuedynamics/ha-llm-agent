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
