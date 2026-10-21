"""The tools of a household member's chat: see and control the devices exposed to Assist.

Members are Home Assistant users who are not admins. Their chat can answer questions about
and control only the entities the household exposed to Assist (Settings > Voice
assistants > Expose), the same set a voice assistant sees. It has no settings, files,
automations, notes or web tools.
"""

from __future__ import annotations

import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar

from ..approval import Risk, classify_service
from . import Tool, ToolContext, ToolError, ToolOutput, list_arg, num_arg, obj
from .states import TARGET_KEYS, CallService, GetHistory, compact_state, entity_area

ASSISTANT = "conversation"
MAX_ENTITIES = 30
_ON_OFF = {"turn_on", "turn_off", "toggle"}
# The everyday services a member's chat may call, by domain, always on the entities it
# names. Anything else (homeassistant.*, script.<name>, media_player.join, ...) can
# reach entities the chat can't see, so it isn't offered.
MEMBER_SERVICES: dict[str, set[str]] = {
    "light": _ON_OFF,
    "switch": _ON_OFF,
    "input_boolean": _ON_OFF,
    "fan": _ON_OFF
    | {
        "set_percentage",
        "oscillate",
        "set_direction",
        "set_preset_mode",
        "increase_speed",
        "decrease_speed",
    },
    "cover": {
        "open_cover",
        "close_cover",
        "stop_cover",
        "set_cover_position",
        "toggle",
        "open_cover_tilt",
        "close_cover_tilt",
        "set_cover_tilt_position",
    },
    "lock": {"lock", "unlock", "open"},
    "climate": {
        "turn_on",
        "turn_off",
        "set_temperature",
        "set_hvac_mode",
        "set_preset_mode",
        "set_fan_mode",
        "set_humidity",
        "set_swing_mode",
    },
    "humidifier": _ON_OFF | {"set_humidity", "set_mode"},
    "water_heater": {"turn_on", "turn_off", "set_temperature", "set_operation_mode"},
    "media_player": {
        "turn_on",
        "turn_off",
        "toggle",
        "media_play",
        "media_pause",
        "media_play_pause",
        "media_stop",
        "media_next_track",
        "media_previous_track",
        "volume_set",
        "volume_up",
        "volume_down",
        "volume_mute",
        "select_source",
        "shuffle_set",
        "repeat_set",
    },
    "scene": {"turn_on"},
    "script": _ON_OFF,
    "vacuum": {"start", "pause", "stop", "return_to_base", "locate"},
    "lawn_mower": {"start_mowing", "pause", "dock"},
    "valve": {"open_valve", "close_valve", "stop_valve", "set_valve_position"},
    "alarm_control_panel": {
        "alarm_arm_home",
        "alarm_arm_away",
        "alarm_arm_night",
        "alarm_arm_vacation",
        "alarm_disarm",
    },
    "button": {"press"},
    "input_button": {"press"},
    "number": {"set_value"},
    "input_number": {"set_value"},
    "select": {"select_option"},
    "input_select": {"select_option"},
    "siren": _ON_OFF,
}
_ENTITY_ID = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+$")


def exposed(hass: HomeAssistant, entity_id: str) -> bool:
    """Exposed to Assist. Anything unexpected counts as not exposed."""
    try:
        from homeassistant.components.homeassistant.exposed_entities import (
            async_should_expose,
        )

        return hass.states.get(entity_id) is not None and async_should_expose(
            hass, ASSISTANT, entity_id
        )
    except Exception:  # noqa: BLE001 - fail closed
        return False


def visible(ctx: ToolContext, entity_id: str) -> bool:
    """Exposed to Assist and not denied by the household's rules."""
    return exposed(ctx.hass, entity_id) and not (ctx.hidden and ctx.hidden(entity_id))


def _exposed_ids(ctx: ToolContext, args: dict[str, Any], key: str) -> list[str]:
    ids = [str(e).strip().lower() for e in list_arg(args, key)][:MAX_ENTITIES]
    hidden = [e for e in ids if not visible(ctx, e)]
    if hidden:
        raise ToolError(
            f"{', '.join(hidden)} is not one of the devices this chat can use. Use "
            "home_entities to see which ones it can."
        )
    return ids


class HomeEntities(Tool):
    def __init__(self) -> None:
        super().__init__(
            "home_entities",
            "The devices and sensors this chat can see and control, with their state and "
            "area. Filter by text, domain or area, or pass entity_ids for full details.",
            obj(
                {
                    "query": {"type": "string", "description": "Text matched against id and name"},
                    "domain": {"type": "string", "description": "e.g. light, sensor"},
                    "area": {"type": "string", "description": "Area id or name"},
                    "entity_ids": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "default": 40},
                }
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        hass = ctx.hass
        if args.get("entity_ids"):
            ids = _exposed_ids(ctx, args, "entity_ids")
            return ToolOutput(
                [compact_state(hass, s, attrs=True) for e in ids if (s := hass.states.get(e))]
            )
        terms = (args.get("query") or "").lower().split()
        domain = args.get("domain")
        area = (args.get("area") or "").lower().strip()
        area_ids = None
        if area:
            area_ids = {
                a.id
                for a in ar.async_get(hass).async_list_areas()
                if a.id == area or area in a.name.lower()
            }
        limit = num_arg(args, "limit", 40, 1, 200)
        found: list[dict[str, Any]] = []
        total = 0
        for state in hass.states.async_all(domain) if domain else hass.states.async_all():
            if not visible(ctx, state.entity_id):
                continue
            if terms and not all(t in f"{state.entity_id} {state.name}".lower() for t in terms):
                continue
            if area_ids is not None and entity_area(hass, state.entity_id) not in area_ids:
                continue
            total += 1
            if len(found) < limit:
                found.append(compact_state(hass, state))
        return ToolOutput({"total": total, "entities": found})

    def rule_groups(self, ctx: ToolContext, args: dict[str, Any]) -> list[list[str]]:
        return _per_entity(self.name, args)


def _per_entity(name: str, args: dict[str, Any]) -> list[list[str]]:
    """One rule group per named entity, so "deny sensor.x" matches a read of it."""
    ids = [str(e).strip().lower() for e in list_arg(args, "entity_ids")]
    return [[name, e] for e in ids] or [[name]]


class HomeHistory(GetHistory):
    def __init__(self) -> None:
        super().__init__()
        self.name = "home_history"
        self.description = "State history of devices this chat can see, over the last N hours."

    def rule_groups(self, ctx: ToolContext, args: dict[str, Any]) -> list[list[str]]:
        return _per_entity(self.name, args)

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        _exposed_ids(ctx, args, "entity_ids")
        return await super().run(ctx, args)


class HomeControl(CallService):
    """call_service limited to exposed entities named by id."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "home_control"
        self.description = (
            "Control devices this chat can use: domain.service on entity ids, e.g. "
            "light.turn_on with data {brightness_pct: 50}."
        )
        self.parameters = obj(
            {
                "domain": {"type": "string"},
                "service": {"type": "string"},
                "entity_ids": {"type": "array", "items": {"type": "string"}},
                "data": {"type": "object", "description": "Service data"},
            },
            ["domain", "service", "entity_ids"],
        )

    def check_args(self, args: dict[str, Any]) -> dict[str, Any]:
        args = Tool.check_args(self, args)
        ids = args.get("entity_ids")
        if isinstance(ids, str):
            ids = ids.split(",")
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
            raise ToolError("entity_ids must list the entities to control")
        # HA reads ids and service names case-insensitively, so compare them that way.
        ids = [i.strip().lower() for i in ids if i.strip()]
        if not ids:
            raise ToolError("entity_ids must list the entities to control")
        data = args.get("data") or {}
        if not isinstance(data, dict):
            raise ToolError("data must be an object")
        if any(k in data for k in TARGET_KEYS):
            raise ToolError("Name the entities in entity_ids, not in data")
        return {
            "domain": str(args["domain"]).strip().lower(),
            "service": str(args["service"]).strip().lower(),
            "target": {"entity_id": ids[:MAX_ENTITIES]},
            "data": data,
        }

    def _check(self, ctx: ToolContext, args: dict[str, Any]) -> list[str]:
        domain, service = args["domain"], args["service"]
        if service not in MEMBER_SERVICES.get(domain, ()):
            raise ToolError(
                f"This chat can't use {domain}.{service}. It can use everyday controls "
                "such as turn_on, turn_off, set_temperature or media_play on its devices."
            )
        ids = _exposed_ids(ctx, {"ids": args["target"]["entity_id"]}, "ids")
        if any(e.split(".", 1)[0] != domain for e in ids):
            raise ToolError(f"{domain}.{service} only acts on {domain} entities")
        if domain == "script" and args.get("data"):
            # Script variables can name any entity; a member runs scripts as they are.
            raise ToolError("This chat runs scripts without data")
        hidden = sorted(
            v
            for v in _strings(args.get("data"))
            if _ENTITY_ID.match(v.strip().lower()) and not visible(ctx, v.strip().lower())
        )
        if hidden:
            raise ToolError(f"The data names {', '.join(hidden)}, which this chat can't use")
        return ids

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        # Checked here, before anything asks for approval, and again when it runs.
        ids = self._check(ctx, args)
        return classify_service(ctx.hass, args["domain"], args["service"], ids)

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        self._check(ctx, args)
        return await super().run(ctx, {**args, "return_response": False})


def _strings(value: Any) -> list[str]:
    """Every string inside service data."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in [*value.keys(), *value.values()] for s in _strings(v)]
    if isinstance(value, (list, tuple)):
        return [s for v in value for s in _strings(v)]
    return []


def member_tools() -> list[Tool]:
    return [HomeEntities(), HomeHistory(), HomeControl()]
