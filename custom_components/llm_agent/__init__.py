"""LLM Agent: an AI chat panel that can operate Home Assistant."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from . import websocket
from .agent import Agent
from .chatgpt_auth import get_auth
from .const import (
    CONF_AUTO_DELETE_DAYS,
    DEFAULT_OPTIONS,
    DOMAIN,
    NAME,
    PANEL_ELEMENT,
    PANEL_URL,
    STATIC_URL,
    setting,
)
from .services import async_setup_services

PLATFORMS = [Platform.CONVERSATION]
_REGISTERED = f"{DOMAIN}_registered"

type LLMAgentConfigEntry = ConfigEntry[Agent]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register actions once; they work while a config entry is loaded."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LLMAgentConfigEntry) -> bool:
    options = {**DEFAULT_OPTIONS, **entry.options}
    agent = Agent(hass, options)
    await agent.store.async_load()
    entry.runtime_data = agent
    hass.data[DOMAIN] = agent

    integration = await async_get_integration(hass, DOMAIN)
    version = str(integration.version)
    hass.data[f"{DOMAIN}_version"] = version

    # Static files and WS commands cannot be unregistered, so register them once.
    if not hass.data.get(_REGISTERED):
        www = Path(__file__).parent / "www"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(www), cache_headers=True)]
        )
        websocket.async_register(hass)
        hass.data[_REGISTERED] = True

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title=NAME,
        sidebar_icon="mdi:robot-outline",
        # the version query busts the browser cache after an update
        module_url=f"{STATIC_URL}/{PANEL_ELEMENT}.js?v={version}",
        embed_iframe=False,
        require_admin=True,
    )

    async def _auto_delete(_now: object = None) -> None:
        days = setting(options, CONF_AUTO_DELETE_DAYS)
        if days:
            await agent.store.delete_older_than(days)

    await _auto_delete()
    entry.async_on_unload(async_track_time_interval(hass, _auto_delete, timedelta(hours=6)))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: LLMAgentConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: LLMAgentConfigEntry) -> bool:
    agent = entry.runtime_data
    for run in list(agent.runs.values()):
        if run.task:
            run.task.cancel()
    frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.pop(DOMAIN, None)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: LLMAgentConfigEntry) -> None:
    """Removing the integration deletes stored ChatGPT sign-ins."""
    await get_auth(hass).clear()
