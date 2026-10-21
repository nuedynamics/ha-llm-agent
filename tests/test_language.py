"""Replies follow the user's language."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant

from custom_components.llm_agent.agent import Agent, ChatRun

from .conftest import entry_options
from .test_agent import ScriptedProvider, reply_text


async def _system(hass: HomeAssistant, language: str | None) -> str:
    agent = Agent(hass, entry_options())
    await agent.store.async_load()
    conv = await agent.store.create("p1", "gpt-5.4-mini", "")
    run = ChatRun(agent, conv, None)
    provider = ScriptedProvider([reply_text("Hallo.")])
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await run.run("go", language=language)
    return provider.calls[0]["system"]


async def test_reply_language_uses_the_panel_language(hass: HomeAssistant) -> None:
    hass.config.language = "en"
    system = await _system(hass, "de")
    assert "language is de" in system
    assert "Reply in the language the user writes in" in system


async def test_reply_language_falls_back_to_home_language(hass: HomeAssistant) -> None:
    hass.config.language = "nl"
    assert "language is nl" in await _system(hass, None)
