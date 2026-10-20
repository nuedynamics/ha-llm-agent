"""Areas, devices and entity registry edits."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

from ..approval import Risk
from . import Tool, ToolContext, ToolError, ToolOutput, obj


class ListAreas(Tool):
    def __init__(self) -> None:
        super().__init__(
            "list_areas",
            "List areas (id, name, floor) with device and entity counts.",
            obj({}),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        hass = ctx.hass
        dev_counts: dict[str | None, int] = {}
        for device in dr.async_get(hass).devices.values():
            dev_counts[device.area_id] = dev_counts.get(device.area_id, 0) + 1
        return ToolOutput(
            [
                {
                    "id": a.id,
                    "name": a.name,
                    "floor": a.floor_id,
                    "devices": dev_counts.get(a.id, 0),
                }
                for a in ar.async_get(hass).async_list_areas()
            ]
        )


class ListDevices(Tool):
    def __init__(self) -> None:
        super().__init__(
            "list_devices",
            "List devices, optionally filtered by area or text. Includes the device's entity ids.",
            obj(
                {
                    "area": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                }
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        hass = ctx.hass
        area = args.get("area")
        query = (args.get("query") or "").lower()
        limit = max(1, min(int(args.get("limit") or 50), 300))
        ent_reg = er.async_get(hass)
        out = []
        for device in dr.async_get(hass).devices.values():
            if area and device.area_id != area:
                continue
            name = device.name_by_user or device.name or ""
            if query and query not in f"{name} {device.manufacturer} {device.model}".lower():
                continue
            out.append(
                {
                    "id": device.id,
                    "name": name,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "area": device.area_id,
                    "disabled": device.disabled_by is not None,
                    "entities": [
                        e.entity_id for e in er.async_entries_for_device(ent_reg, device.id)
                    ],
                }
            )
            if len(out) >= limit:
                break
        return ToolOutput(out)


class UpdateRegistry(Tool):
    def __init__(self) -> None:
        super().__init__(
            "update_registry",
            "Create/update/delete areas; rename, move or disable devices; rename, move, "
            "re-id, hide, disable or remove entities. 'changes' keys: area: name, icon, "
            "floor_id. device: name, area_id, disabled. entity: name, icon, area_id, "
            "new_entity_id, disabled, hidden.",
            obj(
                {
                    "kind": {"type": "string", "enum": ["area", "device", "entity"]},
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "delete"],
                    },
                    "id": {
                        "type": "string",
                        "description": "area_id, device_id or entity_id",
                    },
                    "changes": {"type": "object"},
                },
                ["kind", "action"],
            ),
        )

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        if args.get("action") == "delete":
            return Risk.risky(f"deletes {args.get('kind')} {args.get('id')}")
        return Risk.write()

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        hass = ctx.hass
        kind, action = args["kind"], args["action"]
        item_id = args.get("id")
        changes = dict(args.get("changes") or {})
        try:
            if kind == "area":
                reg = ar.async_get(hass)
                if action == "create":
                    area = reg.async_create(
                        changes.get("name") or item_id or "New area",
                        icon=changes.get("icon"),
                        floor_id=changes.get("floor_id"),
                    )
                    return ToolOutput({"area_id": area.id}, f"Created area {area.name}")
                if not item_id or reg.async_get_area(item_id) is None:
                    raise ToolError(f"Area {item_id} not found")
                if action == "delete":
                    reg.async_delete(item_id)
                    return ToolOutput({"ok": True}, f"Deleted area {item_id}")
                kwargs = {k: changes[k] for k in ("name", "icon", "floor_id") if k in changes}
                reg.async_update(item_id, **kwargs)
                return ToolOutput({"ok": True}, f"Updated area {item_id}")

            if kind == "device":
                reg = dr.async_get(hass)
                if action != "update":
                    raise ToolError(
                        "Devices can only be updated here; remove them via their integration"
                    )
                if not item_id or reg.async_get(item_id) is None:
                    raise ToolError(f"Device {item_id} not found")
                kwargs: dict[str, Any] = {}
                if "name" in changes:
                    kwargs["name_by_user"] = changes["name"]
                if "area_id" in changes:
                    kwargs["area_id"] = changes["area_id"]
                if "disabled" in changes:
                    kwargs["disabled_by"] = (
                        dr.DeviceEntryDisabler.USER if changes["disabled"] else None
                    )
                reg.async_update_device(item_id, **kwargs)
                return ToolOutput({"ok": True}, f"Updated device {item_id}")

            reg = er.async_get(hass)
            if not item_id or reg.async_get(item_id) is None:
                raise ToolError(f"Entity {item_id} is not in the entity registry")
            if action == "delete":
                reg.async_remove(item_id)
                return ToolOutput({"ok": True}, f"Removed {item_id} from the registry")
            if action == "create":
                raise ToolError("Entities are created by integrations or helpers, not here")
            kwargs = {
                k: changes[k] for k in ("name", "icon", "area_id", "new_entity_id") if k in changes
            }
            if "disabled" in changes:
                kwargs["disabled_by"] = (
                    er.RegistryEntryDisabler.USER if changes["disabled"] else None
                )
            if "hidden" in changes:
                kwargs["hidden_by"] = er.RegistryEntryHider.USER if changes["hidden"] else None
            entry = reg.async_update_entity(item_id, **kwargs)
            return ToolOutput({"entity_id": entry.entity_id}, f"Updated {entry.entity_id}")
        except (ValueError, KeyError) as err:
            raise ToolError(str(err)) from err


TOOLS: list[Tool] = [ListAreas(), ListDevices(), UpdateRegistry()]
