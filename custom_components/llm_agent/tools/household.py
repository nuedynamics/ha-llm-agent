"""The tools of a household member's chat: see and control the devices exposed to Assist.

Members are Home Assistant users who are not admins. Their chat can answer questions about
and control only the entities the household exposed to Assist (Settings > Voice
assistants > Expose), the same set a voice assistant sees. It has no settings, files,
automations, notes or web tools.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar

from ..approval import Risk, classify_service
from . import Tool, ToolContext, ToolError, ToolOutput, list_arg, num_arg, obj
from .states import TARGET_KEYS, CallService, GetHistory, compact_state, entity_area

ASSISTANT = "conversation"
MAX_ENTITIES = 30
# homeassistant.* services a member may use on exposed entities; every other one is
# a whole-home action
GENERIC_SERVICES = {"turn_on", "turn_off", "toggle"}


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


def _exposed_ids(hass: HomeAssistant, args: dict[str, Any], key: str) -> list[str]:
    ids = [str(e) for e in list_arg(args, key)][:MAX_ENTITIES]
    hidden = [e for e in ids if not exposed(hass, e)]
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
            ids = _exposed_ids(hass, args, "entity_ids")
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
            if not exposed(hass, state.entity_id):
                continue
            if terms and not all(t in f"{state.entity_id} {state.name}".lower() for t in terms):
                continue
            if area_ids is not None and entity_area(hass, state.entity_id) not in area_ids:
                continue
            total += 1
            if len(found) < limit:
                found.append(compact_state(hass, state))
        return ToolOutput({"total": total, "entities": found})


class HomeHistory(GetHistory):
    def __init__(self) -> None:
        super().__init__()
        self.name = "home_history"
        self.description = "State history of devices this chat can see, over the last N hours."

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        _exposed_ids(ctx.hass, args, "entity_ids")
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
            ids = [i.strip() for i in ids.split(",") if i.strip()]
        if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
            raise ToolError("entity_ids must list the entities to control")
        data = args.get("data") or {}
        if not isinstance(data, dict):
            raise ToolError("data must be an object")
        if any(k in data for k in TARGET_KEYS):
            raise ToolError("Name the entities in entity_ids, not in data")
        return {
            "domain": str(args["domain"]),
            "service": str(args["service"]),
            "target": {"entity_id": ids[:MAX_ENTITIES]},
            "data": data,
        }

    def _check(self, hass: HomeAssistant, args: dict[str, Any]) -> list[str]:
        domain, service = args["domain"], args["service"]
        ids = _exposed_ids(hass, {"ids": args["target"]["entity_id"]}, "ids")
        if domain == "homeassistant":
            if service not in GENERIC_SERVICES:
                raise ToolError(f"This chat can't use homeassistant.{service}")
        elif any(e.split(".", 1)[0] != domain for e in ids):
            raise ToolError(f"{domain}.{service} only acts on {domain} entities")
        return ids

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        # Checked here, before anything asks for approval, and again when it runs.
        ids = self._check(ctx.hass, args)
        return classify_service(ctx.hass, args["domain"], args["service"], ids)

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        self._check(ctx.hass, args)
        return await super().run(ctx, {**args, "return_response": False})


def member_tools() -> list[Tool]:
    return [HomeEntities(), HomeHistory(), HomeControl()]
