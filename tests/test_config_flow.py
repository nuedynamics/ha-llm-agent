"""Config and options flows."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.llm_agent.const import DOMAIN

from .conftest import entry_options

VALIDATE = "custom_components.llm_agent.config_flow.validate_provider"


async def test_user_flow_requires_ack_and_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"type": "anthropic", "acknowledged_risks": False}
    )
    assert result["errors"] == {"acknowledged_risks": "must_acknowledge"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"type": "anthropic", "acknowledged_risks": True}
    )
    assert result["step_id"] == "provider"
    with (
        patch(VALIDATE, return_value=None),
        patch("custom_components.llm_agent.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Claude",
                "api_key": "k",
                "base_url": "https://api.anthropic.com",
                "default_model": "claude-sonnet-5-5",
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    provider = result["options"]["providers"][0]
    assert provider["type"] == "anthropic" and provider["api_key"] == "k"
    assert result["options"]["approval_mode"] == "ask_risky"
    assert result["options"]["allow_shell"] is False


async def test_bad_key_shows_error(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"type": "openai", "acknowledged_risks": True}
    )
    with patch(VALIDATE, return_value="invalid_auth"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "OpenAI",
                "api_key": "bad",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-5.4",
            },
        )
    assert result["errors"] == {"base": "invalid_auth"}


async def test_options_shell_needs_confirmation(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=entry_options())
    entry.add_to_hass(hass)
    with patch("custom_components.llm_agent.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.MENU
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "settings"}
        )
        settings = {
            "approval_mode": "ask_risky",
            "backup_before_risky": True,
            "protect_sensitive": True,
            "block_invalid_restart": False,
            "allow_shell": True,
            "max_steps": 30,
        }
        result = await hass.config_entries.options.async_configure(result["flow_id"], settings)
        assert result["step_id"] == "confirm_shell"
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"confirm": False}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["allow_shell"] is False
    assert entry.options["block_invalid_restart"] is False
    assert entry.options["max_steps"] == 30
    assert entry.options["providers"][0]["id"] == "p1"


async def test_options_edit_provider_keeps_key_when_blank(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=entry_options())
    entry.add_to_hass(hass)
    with (
        patch("custom_components.llm_agent.async_setup_entry", return_value=True),
        patch(VALIDATE, return_value=None),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "edit_provider"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"provider": "p1"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"name": "Renamed", "base_url": "http://stub.invalid/v1", "default_model": "gpt-5.4"},
        )
    provider = entry.options["providers"][0]
    assert provider["name"] == "Renamed" and provider["api_key"] == "sk-test"
    assert provider["default_model"] == "gpt-5.4"
