"""Read state, history, templates; list and call services."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.service import async_get_all_descriptions
from homeassistant.helpers.template import Template
import homeassistant.util.dt as dt_util

from ..approval import Risk, classify_service
from . import Tool, ToolContext, ToolError, ToolOutput, list_arg, num_arg, obj, similar_entities

STATE_ATTR_SKIP = {
    "friendly_name",
    "icon",
    "entity_picture",
    "supported_features",
    "attribution",
}


def entity_area(hass, entity_id: str) -> str | None:
    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get(entity_id)
    if entry is None:
        return None
    if entry.area_id:
        return entry.area_id
    if entry.device_id:
        device = dr.async_get(hass).async_get(entry.device_id)
        if device:
            return device.area_id
    return None


def expand_target(hass, target: dict[str, Any] | None) -> list[str]:
    """Resolve a service target to entity ids (for risk checks and feedback)."""
    if not target:
        return []

    def as_list(value: Any) -> list[str]:
        if value is None:
            return []
        return [value] if isinstance(value, str) else list(value)

    ids = set(as_list(target.get("entity_id")))
    ent_reg = er.async_get(hass)
    devices = set(as_list(target.get("device_id")))
    areas = set(as_list(target.get("area_id")))
    if areas:
        dev_reg = dr.async_get(hass)
        devices |= {d.id for d in dev_reg.devices.values() if d.area_id in areas}
    if devices or areas:
        for entry in ent_reg.entities.values():
            if entry.device_id in devices or entry.area_id in areas:
                ids.add(entry.entity_id)
    return sorted(ids)


def compact_state(hass, state, attrs: bool = False) -> dict[str, Any]:
    item: dict[str, Any] = {
        "entity_id": state.entity_id,
        "name": state.name,
        "state": state.state,
    }
    if area := entity_area(hass, state.entity_id):
        item["area"] = area
    if attrs:
        item["attributes"] = {k: v for k, v in state.attributes.items() if k not in STATE_ATTR_SKIP}
        item["last_changed"] = state.last_changed.isoformat(timespec="seconds")
    return item


class SearchEntities(Tool):
    def __init__(self) -> None:
        super().__init__(
            "search_entities",
            "Find entities by text, domain and/or area. Returns entity_id, name, state "
            "and area. Use this before acting on devices whose ids you do not know.",
            obj(
                {
                    "query": {
                        "type": "string",
                        "description": "Text matched against id and name",
                    },
                    "domain": {"type": "string", "description": "e.g. light, sensor"},
                    "area": {"type": "string", "description": "Area id or name"},
                    "limit": {"type": "integer", "default": 40},
                }
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        hass = ctx.hass
        query = (args.get("query") or "").lower().strip()
        terms = query.split()
        domain = args.get("domain")
        area = (args.get("area") or "").lower().strip()
        area_ids: set[str] | None = None
        if area:
            area_ids = {
                a.id
                for a in ar.async_get(hass).async_list_areas()
                if a.id == area or a.name.lower() == area or area in a.name.lower()
            }
        limit = num_arg(args, "limit", 40, 1, 200)
        states = hass.states.async_all(domain) if domain else hass.states.async_all()
        results = []
        total = 0
        for state in states:
            if terms:
                hay = f"{state.entity_id} {state.name}".lower()
                if not all(t in hay for t in terms):
                    continue
            if area_ids is not None and entity_area(hass, state.entity_id) not in area_ids:
                continue
            total += 1
            if len(results) < limit:
                results.append(compact_state(hass, state))
        return ToolOutput({"total": total, "entities": results})


class GetEntities(Tool):
    def __init__(self) -> None:
        super().__init__(
            "get_entities",
            "Get full state and attributes for specific entities.",
            obj(
                {"entity_ids": {"type": "array", "items": {"type": "string"}}},
                ["entity_ids"],
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        out = []
        for entity_id in list_arg(args, "entity_ids")[:50]:
            state = ctx.hass.states.get(entity_id)
            out.append(
                compact_state(ctx.hass, state, attrs=True)
                if state
                else _not_found(ctx.hass, str(entity_id))
            )
        return ToolOutput(out)


class GetHistory(Tool):
    def __init__(self) -> None:
        super().__init__(
            "get_history",
            "State history for entities over the last N hours (downsampled).",
            obj(
                {
                    "entity_ids": {"type": "array", "items": {"type": "string"}},
                    "hours": {"type": "number", "default": 24},
                    "max_points": {"type": "integer", "default": 60},
                },
                ["entity_ids"],
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        try:
            from homeassistant.components.recorder import get_instance, history
        except ImportError as err:
            raise ToolError("Recorder is not available") from err
        hass = ctx.hass
        entity_ids = list_arg(args, "entity_ids")[:20]
        hours = num_arg(args, "hours", 24, 0.1, 24 * 30, float)
        max_points = num_arg(args, "max_points", 60, 2, 500)
        end = dt_util.utcnow()
        start = end - timedelta(hours=hours)
        data = await get_instance(hass).async_add_executor_job(
            lambda: history.get_significant_states(
                hass,
                start,
                end,
                entity_ids,
                include_start_time_state=True,
                significant_changes_only=True,
                minimal_response=True,
                no_attributes=True,
            )
        )
        out: dict[str, Any] = {}
        for entity_id, states in data.items():
            points = [
                (
                    (s.last_changed if hasattr(s, "last_changed") else s["last_changed"]),
                    (s.state if hasattr(s, "state") else s["state"]),
                )
                for s in states
            ]
            if len(points) > max_points:
                step = len(points) / max_points
                points = [points[int(i * step)] for i in range(max_points - 1)] + [points[-1]]
            out[entity_id] = [
                [
                    t.isoformat(timespec="minutes") if hasattr(t, "isoformat") else str(t),
                    v,
                ]
                for t, v in points
            ]
        return ToolOutput(out)


class RenderTemplate(Tool):
    def __init__(self) -> None:
        super().__init__(
            "render_template",
            "Render a Home Assistant Jinja template. Good for counting or aggregating "
            "states in one step, e.g. {{ states.light | selectattr('state','eq','on') | list | count }}.",
            obj({"template": {"type": "string"}}, ["template"]),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        try:
            result = Template(args["template"], ctx.hass).async_render(parse_result=False)
        except HomeAssistantError as err:
            raise ToolError(f"Template error: {err}") from err
        return ToolOutput(str(result))


class ListServices(Tool):
    def __init__(self) -> None:
        super().__init__(
            "list_services",
            "Without a domain: list domains and their service names. With a domain: "
            "service descriptions and fields.",
            obj({"domain": {"type": "string"}}),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        hass = ctx.hass
        domain = args.get("domain")
        if not domain:
            return ToolOutput(
                {d: sorted(s) for d, s in sorted(hass.services.async_services().items())}
            )
        descriptions = await async_get_all_descriptions(hass)
        services = descriptions.get(domain)
        if not services:
            raise ToolError(f"No services for domain {domain}")
        out = {}
        for name, desc in services.items():
            fields = {}
            for field_name, field in (desc.get("fields") or {}).items():
                if "fields" in field:  # collapsed section
                    for sub_name, sub in field["fields"].items():
                        fields[sub_name] = _field_brief(sub)
                else:
                    fields[field_name] = _field_brief(field)
            out[name] = {
                "description": (desc.get("description") or "")[:200],
                "fields": fields,
            }
            if desc.get("target"):
                out[name]["target"] = True
        return ToolOutput(out)


def _field_brief(field: dict[str, Any]) -> str:
    parts = []
    if field.get("required"):
        parts.append("required")
    selector = field.get("selector")
    if isinstance(selector, dict) and selector:
        parts.append(next(iter(selector)))
    if field.get("description"):
        parts.append(str(field["description"])[:100])
    return "; ".join(parts)


class CallService(Tool):
    def __init__(self) -> None:
        super().__init__(
            "call_service",
            "Call a Home Assistant service (action), e.g. light.turn_on. Returns the "
            "service response if any, and the new state of targeted entities.",
            obj(
                {
                    "domain": {"type": "string"},
                    "service": {"type": "string"},
                    "target": {
                        "type": "object",
                        "description": "entity_id / device_id / area_id / floor_id / label_id (string or list)",
                    },
                    "data": {"type": "object", "description": "Service data"},
                    "return_response": {"type": "boolean", "default": False},
                },
                ["domain", "service"],
            ),
        )

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        target = dict(args.get("target") or {})
        data = args.get("data") or {}
        if "entity_id" in data and "entity_id" not in target:
            target["entity_id"] = data["entity_id"]
        return classify_service(
            ctx.hass,
            args.get("domain", ""),
            args.get("service", ""),
            expand_target(ctx.hass, target),
        )

    def check_args(self, args: dict[str, Any]) -> dict[str, Any]:
        target = args.get("target")
        # A bare entity id (or list of them) is unambiguous: wrap it.
        if isinstance(target, str) and "{" not in target and "." in target:
            args = {**args, "target": {"entity_id": [t.strip() for t in target.split(",")]}}
        elif isinstance(target, list) and all(isinstance(t, str) for t in target):
            args = {**args, "target": {"entity_id": target}}
        return super().check_args(args)

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        hass = ctx.hass
        domain, service = args["domain"], args["service"]
        if not hass.services.has_service(domain, service):
            raise ToolError(f"Service {domain}.{service} does not exist")
        target = args.get("target") or None
        if target is not None and not isinstance(target, dict):
            raise ToolError('\'target\' must be an object such as {"entity_id": "light.kitchen"}')
        _check_entities(hass, domain, service, target)
        want_response = bool(args.get("return_response"))
        try:
            response = await hass.services.async_call(
                domain,
                service,
                dict(args.get("data") or {}),
                blocking=True,
                context=Context(user_id=ctx.user_id),
                target=target,
                return_response=want_response,
            )
        except (HomeAssistantError, ValueError) as err:
            raise ToolError(f"{domain}.{service} failed: {err}") from err
        result: dict[str, Any] = {"ok": True}
        if want_response:
            result["response"] = response
        affected = expand_target(hass, target)[:30]
        if affected:
            result["states"] = [
                compact_state(hass, s) for e in affected if (s := hass.states.get(e))
            ]
        return ToolOutput(result, summary=f"Called {domain}.{service}")


def _not_found(hass: Any, entity_id: str) -> dict[str, Any]:
    out: dict[str, Any] = {"entity_id": entity_id, "error": "not found"}
    if similar := similar_entities(hass, entity_id):
        out["similar"] = similar
    return out


def _check_entities(hass: Any, domain: str, service: str, target: dict[str, Any] | None) -> None:
    """Home Assistant silently ignores unknown entities and entities of another domain,
    which makes a failed call look like a success. Catch both here."""
    if not target or not target.get("entity_id"):
        return
    ids = target["entity_id"]
    ids = [ids] if isinstance(ids, str) else list(ids)
    if ids == ["all"]:
        return
    for entity_id in ids:
        if hass.states.get(entity_id) is None:
            similar = similar_entities(hass, str(entity_id))
            hint = f" Similar entities: {', '.join(similar)}." if similar else ""
            raise ToolError(
                f"Entity {entity_id} does not exist.{hint} Use search_entities to find the "
                "right entity id."
            )
    if domain != "homeassistant" and all(e.split(".", 1)[0] != domain for e in ids):
        other = ids[0].split(".", 1)[0]
        raise ToolError(
            f"{domain}.{service} does not act on {other} entities. "
            f"Use the {other} domain instead (for example {other}.{service}), "
            "or homeassistant.turn_on / turn_off."
        )


TOOLS: list[Tool] = [
    SearchEntities(),
    GetEntities(),
    GetHistory(),
    RenderTemplate(),
    ListServices(),
    CallService(),
]
