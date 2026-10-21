"""Read-only mode looks but never changes anything."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.llm_agent.approval import Level, Risk, needs_approval

from .test_agent import ScriptedProvider, _run, reply_text, reply_tool


def _unlock() -> list:
    return reply_tool(
        "c1",
        "call_service",
        {"domain": "lock", "service": "unlock", "target": {"entity_id": "lock.front"}},
    )


async def test_read_only_refuses_changes_even_when_a_rule_allows_them(
    hass: HomeAssistant,
) -> None:
    calls = async_mock_service(hass, "lock", "unlock")
    hass.states.async_set("lock.front", "locked")
    provider = ScriptedProvider([_unlock(), reply_text("I can't.")])
    conv, events = await _run(
        hass, provider, "unlock", approval_mode="read_only", approval_rules="allow lock.*"
    )
    assert calls == []
    assert not any(e["type"] == "approval" for e in events)
    tool = next(m for m in conv["messages"] if m["role"] == "tool")
    assert "Read-only mode is on" in str(tool["content"])
    assert "Read-only mode is on" in provider.calls[0]["system"]


async def test_read_only_still_answers_questions(hass: HomeAssistant) -> None:
    hass.states.async_set("light.kitchen", "on")
    provider = ScriptedProvider(
        [reply_tool("c1", "get_entities", {"entity_ids": ["light.kitchen"]}), reply_text("On.")]
    )
    conv, _ = await _run(hass, provider, "is the kitchen light on?", approval_mode="read_only")
    tool = next(m for m in conv["messages"] if m["role"] == "tool")
    assert "Read-only" not in str(tool["content"])
    assert "light.kitchen" in str(tool["content"])


def test_read_only_never_counts_a_change_as_approved() -> None:
    assert needs_approval("read_only", Risk(Level.WRITE))
    assert not needs_approval("read_only", Risk.read())
