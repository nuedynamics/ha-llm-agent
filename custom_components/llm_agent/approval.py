"""Risk levels and the approval decision.

Every tool call is classified as READ, WRITE or RISKY by its tool. The approval
mode then decides whether the call runs straight away or waits for the admin.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from homeassistant.core import HomeAssistant

from .const import MODE_ASK_ALL, MODE_ASK_RISKY, MODE_AUTOPILOT


class Level(IntEnum):
    READ = 0
    WRITE = 1
    RISKY = 2


@dataclass(slots=True)
class Risk:
    level: Level
    reason: str = ""

    @classmethod
    def read(cls) -> Risk:
        return cls(Level.READ)

    @classmethod
    def write(cls, reason: str = "") -> Risk:
        return cls(Level.WRITE, reason)

    @classmethod
    def risky(cls, reason: str) -> Risk:
        return cls(Level.RISKY, reason)


def needs_approval(mode: str, risk: Risk) -> bool:
    if risk.level is Level.READ:
        return False
    if mode == MODE_ASK_ALL:
        return True
    if mode == MODE_AUTOPILOT:
        return False
    # MODE_ASK_RISKY and anything unknown fall back to the safe default.
    return risk.level is Level.RISKY or mode not in (MODE_ASK_RISKY,)


# Domains where any state-changing service is treated as risky.
RISKY_DOMAINS = {
    "lock": "controls a lock",
    "alarm_control_panel": "controls an alarm",
    "hassio": "Supervisor action",
    "backup": "backup action",
    "update": "installs an update",
    "homeassistant": "core Home Assistant action",
    "recorder": "changes recorded history",
    "valve": "opens or closes a valve",
    "siren": "controls a siren",
}

# Services that are harmless even in risky domains.
SAFE_SERVICES = {
    ("homeassistant", "update_entity"),
    ("homeassistant", "reload_core_config"),
    ("homeassistant", "reload_custom_templates"),
    ("homeassistant", "toggle"),
    ("homeassistant", "turn_on"),
    ("homeassistant", "turn_off"),
    ("update", "skip"),
    ("update", "clear_skipped"),
    ("alarm_control_panel", "alarm_arm_home"),
    ("alarm_control_panel", "alarm_arm_away"),
    ("alarm_control_panel", "alarm_arm_night"),
    ("lock", "lock"),
}

# Cover device classes that guard a way into the home.
ENTRY_COVER_CLASSES = {"garage", "gate", "door"}
DESTRUCTIVE_WORDS = ("delete", "remove", "purge", "clear", "wipe", "reset", "factory")


def classify_service(hass: HomeAssistant, domain: str, service: str, entity_ids: list[str]) -> Risk:
    if any(word in service for word in DESTRUCTIVE_WORDS):
        return Risk.risky(f"{domain}.{service} deletes or clears data")
    if domain == "homeassistant":
        # Generic turn_on/off/toggle can reach locks, alarms and entry covers.
        for entity_id in entity_ids:
            if entity_id.split(".", 1)[0] in ("lock", "alarm_control_panel", "valve"):
                return Risk.risky(f"affects {entity_id}")
            state = hass.states.get(entity_id)
            if (
                entity_id.startswith("cover.")
                and state
                and state.attributes.get("device_class") in ENTRY_COVER_CLASSES
            ):
                return Risk.risky(f"affects {entity_id}")
    if (domain, service) in SAFE_SERVICES:
        return Risk.write()
    if domain in RISKY_DOMAINS:
        return Risk.risky(f"{domain}.{service}: {RISKY_DOMAINS[domain]}")
    if domain == "cover" and service in (
        "open_cover",
        "toggle",
        "set_cover_position",
        "stop_cover",
    ):
        for entity_id in entity_ids:
            state = hass.states.get(entity_id)
            if state and state.attributes.get("device_class") in ENTRY_COVER_CLASSES:
                return Risk.risky(f"opens {entity_id} ({state.attributes['device_class']})")
    return Risk.write()


def summarize_args(args: dict[str, Any], limit: int = 600) -> str:
    import json

    text = json.dumps(args, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 1] + "…"
