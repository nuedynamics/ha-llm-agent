"""Diagnostics download for bug reports.

Keys and the custom prompt are redacted. Conversation text and tool arguments are left
out, because they can describe the home in detail. Recent actions are listed by tool name
and outcome only, and credentials in provider URLs are removed.
"""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant

from .const import CONF_EXTRA_PROMPT, CONF_PROVIDERS, CONF_SEARCH_KEY, CONF_SEARXNG_URL, DOMAIN

TO_REDACT = {"api_key", CONF_EXTRA_PROMPT, CONF_SEARCH_KEY, CONF_SEARXNG_URL}
RECENT_ACTIONS = 20


def _recent_actions(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open(encoding="utf-8") as fh:
            lines = deque(fh, maxlen=RECENT_ACTIONS)
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        # Error details can quote tool arguments, so only the outcome is reported.
        out.append({k: e.get(k) for k in ("time", "tool", "risk", "decision", "ok") if k in e})
    return out


def _redact_provider(provider: dict[str, Any]) -> dict[str, Any]:
    out = async_redact_data(provider, TO_REDACT)
    if url := out.get("base_url"):
        # scheme, host and port only: a gateway may carry its token in the path or query
        parts = urlsplit(url)
        host = parts.hostname or ""
        if parts.port:
            host += f":{parts.port}"
        user = "**REDACTED**@" if parts.username or parts.password else ""
        # short path parts such as /v1 or /api stay; long ones may be tokens
        path = "/".join(seg if len(seg) <= 12 else "**REDACTED**" for seg in parts.path.split("/"))
        query = "**REDACTED**" if parts.query else ""
        out["base_url"] = urlunsplit((parts.scheme, user + host, path, query, ""))
    return out


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    agent = getattr(entry, "runtime_data", None)
    options = async_redact_data(dict(entry.options), TO_REDACT)
    options[CONF_PROVIDERS] = [_redact_provider(p) for p in entry.options.get(CONF_PROVIDERS, [])]
    out: dict[str, Any] = {
        "version": hass.data.get(f"{DOMAIN}_version"),
        "home_assistant": HA_VERSION,
        "options": options,
    }
    if agent is None:  # setup didn't finish; the settings still help
        return {**out, "loaded": False}
    return {
        **out,
        "conversations": len(agent.store.list()),
        "running": len(agent.runs),
        "recent_actions": await hass.async_add_executor_job(
            _recent_actions, agent.snapshots.root / "audit.jsonl"
        ),
    }
