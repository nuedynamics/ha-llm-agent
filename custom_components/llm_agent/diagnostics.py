"""Diagnostics download for bug reports.

Keys and the custom prompt are redacted. Conversation text and tool arguments are left
out, because they can describe the home in detail. Recent actions are listed by tool name
and outcome only.
"""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant

from .const import CONF_EXTRA_PROMPT, CONF_PROVIDERS, DOMAIN

TO_REDACT = {"api_key", CONF_EXTRA_PROMPT}
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
        out.append(
            {k: e.get(k) for k in ("time", "tool", "risk", "decision", "ok") if k in e}
            | ({"error": str(e["detail"])[:200]} if not e.get("ok") and e.get("detail") else {})
        )
    return out


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    agent = entry.runtime_data
    options = async_redact_data(dict(entry.options), TO_REDACT)
    options[CONF_PROVIDERS] = [
        async_redact_data(p, TO_REDACT) for p in entry.options.get(CONF_PROVIDERS, [])
    ]
    return {
        "version": hass.data.get(f"{DOMAIN}_version"),
        "home_assistant": HA_VERSION,
        "options": options,
        "conversations": len(agent.store.list()),
        "running": len(agent.runs),
        "recent_actions": await hass.async_add_executor_job(
            _recent_actions, agent.snapshots.root / "audit.jsonl"
        ),
    }
