"""Risk levels and the approval decision.

Every tool call is classified as READ, WRITE or RISKY by its tool. The approval
mode then decides whether the call runs straight away or waits for the admin.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import fnmatch
import re
from typing import Any

from homeassistant.core import HomeAssistant

from .const import MODE_ASK_ALL, MODE_ASK_RISKY, MODE_AUTOPILOT, MODE_REVIEWER


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
    # MODE_ASK_RISKY and anything unknown fall back to the safe default. In reviewer
    # mode the same risky calls need approval; the reviewer gives it, or a person does.
    return risk.level is Level.RISKY or mode not in (MODE_ASK_RISKY, MODE_REVIEWER)


def parse_patterns(text: str | None) -> list[str]:
    """Comma- or newline-separated patterns, lower-cased, blanks dropped."""
    return [p.strip().lower() for p in re.split(r"[,\n]", text or "") if p.strip()]


def always_asks(patterns: list[str], keys: list[str]) -> str | None:
    """The first key that matches an always-ask pattern, or None."""
    for key in keys:
        for pattern in patterns:
            if fnmatch.fnmatchcase(key.lower(), pattern):
                return key
    return None


RULE_VERBS = {"allow": "allow", "ask": "ask", "deny": "deny", "never": "deny"}


@dataclass(frozen=True, slots=True)
class Rule:
    verb: str  # allow, ask or deny
    pattern: str
    members_only: bool = False


def parse_rules(text: str | None) -> tuple[list[Rule], list[str]]:
    """Approval rules, one per line: `[members] allow|ask|deny pattern, pattern`.
    "always" before the verb and "never" for deny are accepted. Returns the rules and
    the lines that could not be read."""
    rules: list[Rule] = []
    bad: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        words = line.lower().split(None, 1)
        members = words[0] in ("members", "members:")
        if members:
            words = words[1].split(None, 1) if len(words) > 1 else []
        if words and words[0] == "always":
            words = words[1].split(None, 1) if len(words) > 1 else []
        verb = RULE_VERBS.get(words[0]) if words else None
        patterns = parse_patterns(words[1]) if verb and len(words) > 1 else []
        if not patterns:
            bad.append(raw.strip())
            continue
        rules.extend(Rule(verb, p, members) for p in patterns)
    return rules, bad


def match_rule(rules: list[Rule], groups: list[list[str]], member: bool) -> Rule | None:
    """The rule that decides a call, or None. `groups` holds the names of each thing the
    call acts on (for a service call: each entity with its domain.service). Deny wins
    over ask, and ask over allow, when any name matches. Allow needs every group
    matched by an allow rule, so "allow light.*" never lets a call that also reaches a
    lock through. Rules marked members only apply in household members' chats."""
    rules = [r for r in rules if member or not r.members_only]

    def hits(rule: Rule, keys: list[str]) -> bool:
        return any(fnmatch.fnmatchcase(k.lower(), rule.pattern) for k in keys)

    flat = [k for group in groups for k in group]
    for verb in ("deny", "ask"):
        if found := next((r for r in rules if r.verb == verb and hits(r, flat)), None):
            return found
    allows = [r for r in rules if r.verb == "allow"]
    picked: Rule | None = None
    for group in groups:
        rule = next((r for r in allows if hits(r, group)), None)
        if rule is None:
            return None
        picked = picked or rule
    return picked


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
    # HA lowercases domain, service and entity ids, so OPEN_COVER is open_cover.
    domain, service = str(domain).strip().lower(), str(service).strip().lower()
    entity_ids = [str(e).strip().lower() for e in entity_ids]
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
        # a gate or garage door that tilts opens that way too
        "open_cover_tilt",
        "toggle_cover_tilt",
        "set_cover_tilt_position",
        "stop_cover_tilt",
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
