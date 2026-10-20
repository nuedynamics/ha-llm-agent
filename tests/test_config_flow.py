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
            "safety": {
                "backup_before_risky": True,
                "protect_sensitive": True,
                "block_invalid_restart": False,
                "allow_shell": True,
            },
            "cost": {"daily_spend_cap": 0, "max_steps": 30, "max_reply_tokens": 16000},
            "context": {
                "compact_at_tokens": 100000,
                "keep_turns": 10,
                "include_home_summary": True,
            },
            "storage": {
                "chats_in_memory": 5,
                "max_chats": 200,
                "auto_delete_days": 0,
                "undo_size_mb": 50,
                "undo_keep": 50,
                "undo_max_age_days": 0,
                "audit_size_mb": 2,
            },
            "connection": {"request_timeout": 300, "retries": 3},
            "debugging": {"log_prompts": False},
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


async def test_options_storage_shows_usage_and_cleans_up(hass: HomeAssistant) -> None:
    from custom_components.llm_agent.agent import Agent

    entry = MockConfigEntry(domain=DOMAIN, data={}, options=entry_options())
    entry.add_to_hass(hass)
    agent = Agent(hass, entry_options())
    await agent.store.async_load()
    await agent.snapshots.save("file", "x", {"path": "a.yaml", "content": "a: 1"})
    hass.data[DOMAIN] = agent
    with patch("custom_components.llm_agent.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "storage"}
        )
        assert result["step_id"] == "storage"
        assert result["description_placeholders"]["snapshots"] == "1"
        assert result["description_placeholders"]["spent_today"] == "$0.00"
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"delete_older_days": 0, "clear_undo": True}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert (await agent.snapshots.disk_usage())["snapshots"] == 0
    hass.data.pop(DOMAIN)


async def test_settings_are_stored_flat_and_clamped(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=entry_options())
    entry.add_to_hass(hass)
    with patch("custom_components.llm_agent.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "settings"}
        )
        # every section is in the form, with the defaults filled in
        names = [str(k) for k in result["data_schema"].schema]
        assert {"safety", "cost", "context", "storage", "connection", "debugging"} <= set(names)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "approval_mode": "ask_all",
                "safety": {
                    "backup_before_risky": True,
                    "protect_sensitive": True,
                    "block_invalid_restart": True,
                    "allow_shell": False,
                },
                "cost": {"daily_spend_cap": 2.5, "max_steps": 40, "max_reply_tokens": 8192},
                "context": {"compact_at_tokens": 0, "keep_turns": 6, "include_home_summary": False},
                "storage": {
                    "chats_in_memory": 3,
                    "max_chats": 100,
                    "auto_delete_days": 30,
                    "undo_size_mb": 20,
                    "undo_keep": 30,
                    "undo_max_age_days": 14,
                    "audit_size_mb": 5,
                },
                "connection": {"request_timeout": 600, "retries": 1},
                "debugging": {"log_prompts": True},
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    opts = entry.options
    assert "cost" not in opts and opts["max_steps"] == 40 and opts["daily_spend_cap"] == 2.5
    assert opts["compact_at_tokens"] == 0 and opts["include_home_summary"] is False
    assert opts["auto_delete_days"] == 30 and isinstance(opts["auto_delete_days"], int)
    assert opts["request_timeout"] == 600 and opts["log_prompts"] is True


async def test_sections_left_out_keep_their_values(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=entry_options(max_chats=77))
    entry.add_to_hass(hass)
    with patch("custom_components.llm_agent.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "settings"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "approval_mode": "ask_risky",
                "cost": {"price_overrides": {"m": {"input": 1, "output": 2}}},
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["max_chats"] == 77
    assert entry.options["price_overrides"] == {"m": {"input": 1, "output": 2}}
    assert entry.options["max_steps"] == 25
