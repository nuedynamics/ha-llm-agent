"""The llm_agent.ask action."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError, Unauthorized
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.llm_agent.const import DOMAIN

from .test_agent import ScriptedProvider, reply_text, reply_tool
from .test_init import _setup


async def _ask(hass: HomeAssistant, scripted, context=None, **data):
    with patch("custom_components.llm_agent.agent.make_provider", return_value=scripted):
        return await hass.services.async_call(
            DOMAIN, "ask", data, blocking=True, return_response=True, context=context
        )


async def test_ask_returns_the_reply_and_can_continue(hass: HomeAssistant) -> None:
    await _setup(hass)
    provider = ScriptedProvider([reply_text("No windows are open."), reply_text("Still none.")])
    first = await _ask(hass, provider, prompt="any windows open?")
    assert first["response"] == "No windows are open."
    again = await _ask(hass, provider, prompt="and now?", conversation_id=first["conversation_id"])
    assert again == {"response": "Still none.", "conversation_id": first["conversation_id"]}
    assert len(provider.calls[1]["messages"]) == 3  # the earlier turn came along


async def test_ask_refuses_actions_that_need_approval(hass: HomeAssistant) -> None:
    await _setup(hass, approval_mode="ask_all")
    calls = async_mock_service(hass, "light", "turn_on")
    hass.states.async_set("light.kitchen", "off")
    provider = ScriptedProvider(
        [
            reply_tool(
                "c1",
                "call_service",
                {"domain": "light", "service": "turn_on", "target": {"entity_id": "light.kitchen"}},
            ),
            reply_text("I couldn't; please turn it on from the panel."),
        ]
    )
    out = await _ask(hass, provider, prompt="turn on the kitchen light")
    assert calls == []
    assert "panel" in out["response"]
    tool_msg = provider.calls[1]["messages"][-1]
    assert tool_msg["is_error"] and "Nobody can approve" in tool_msg["content"]


async def test_ask_runs_everyday_actions_in_ask_risky_mode(hass: HomeAssistant) -> None:
    await _setup(hass)
    calls = async_mock_service(hass, "light", "turn_on")
    hass.states.async_set("light.kitchen", "off")
    provider = ScriptedProvider(
        [
            reply_tool(
                "c1",
                "call_service",
                {"domain": "light", "service": "turn_on", "target": {"entity_id": "light.kitchen"}},
            ),
            reply_text("Done."),
        ]
    )
    await _ask(hass, provider, prompt="turn on the kitchen light")
    assert len(calls) == 1


async def test_ask_checks_the_caller_and_provider(hass: HomeAssistant, hass_read_only_user) -> None:
    await _setup(hass)
    with pytest.raises(Unauthorized):
        await _ask(hass, ScriptedProvider([]), Context(user_id=hass_read_only_user.id), prompt="hi")
    with pytest.raises(ServiceValidationError, match="No provider named"):
        await _ask(hass, ScriptedProvider([]), prompt="hi", provider="Nope")
    with pytest.raises(ServiceValidationError, match="No conversation"):
        await _ask(hass, ScriptedProvider([]), prompt="hi", conversation_id="missing")
