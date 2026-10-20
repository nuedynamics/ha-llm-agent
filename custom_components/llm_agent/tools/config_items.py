"""Automations, scripts and scenes stored in the UI-managed YAML files.

These are the same files the Home Assistant UI editors write
(automations.yaml, scripts.yaml, scenes.yaml), so changes show up in the UI
and remain editable there.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util.yaml import load_yaml, parse_yaml

from ..approval import Risk
from . import Preview, Tool, ToolContext, ToolError, ToolOutput, obj
from .util import diff_text, read_text, to_yaml, write_text

KINDS = {
    # kind: (file, keyed_by_dict)
    "automation": ("automations.yaml", False),
    "script": ("scripts.yaml", True),
    "scene": ("scenes.yaml", False),
}
_LOCKS: dict[str, asyncio.Lock] = {}


def _lock(kind: str) -> asyncio.Lock:
    return _LOCKS.setdefault(kind, asyncio.Lock())


def _path(ctx: ToolContext, kind: str) -> Path:
    return Path(ctx.hass.config.path(KINDS[kind][0]))


async def _load(ctx: ToolContext, kind: str) -> Any:
    path = _path(ctx, kind)
    keyed = KINDS[kind][1]

    def _read() -> Any:
        if not path.exists():
            return {} if keyed else []
        data = load_yaml(str(path))
        if data is None:
            return {} if keyed else []
        return data

    try:
        data = await ctx.hass.async_add_executor_job(_read)
    except HomeAssistantError as err:
        raise ToolError(f"Cannot parse {path.name}: {err}") from err
    if (keyed and not isinstance(data, dict)) or (not keyed and not isinstance(data, list)):
        raise ToolError(f"{path.name} has an unexpected layout; edit it with the files tool")
    return data


def _find(data: Any, kind: str, item_id: str) -> Any:
    if KINDS[kind][1]:
        return data.get(item_id)
    for item in data:
        if isinstance(item, dict) and str(item.get("id")) == str(item_id):
            return item
    return None


def _resolve_id(ctx: ToolContext, kind: str, item_id: str) -> str:
    """Accept an entity_id (automation.x) and map it to the stored id."""
    if not item_id.startswith(f"{kind}."):
        return item_id
    entry = er.async_get(ctx.hass).async_get(item_id)
    if entry and entry.unique_id:
        return str(entry.unique_id)
    if kind == "script":
        return item_id.split(".", 1)[1]
    state = ctx.hass.states.get(item_id)
    if state and state.attributes.get("id"):
        return str(state.attributes["id"])
    return item_id


async def _validate(ctx: ToolContext, kind: str, item_id: str, config: dict[str, Any]) -> None:
    try:
        if kind == "automation":
            from homeassistant.components.automation.config import (
                async_validate_config_item,
            )

            await async_validate_config_item(ctx.hass, item_id, config)
        elif kind == "script":
            from homeassistant.components.script.config import (
                async_validate_config_item,
            )

            await async_validate_config_item(ctx.hass, item_id, config)
    except ImportError:
        return
    except Exception as err:
        raise ToolError(f"Invalid {kind} config: {err}") from err


def item_ids(data: Any, kind: str) -> set[str]:
    """Ids of the items in a loaded automations/scripts/scenes file."""
    if KINDS[kind][1]:
        return {str(k) for k in data} if isinstance(data, dict) else set()
    if isinstance(data, list):
        return {str(i["id"]) for i in data if isinstance(i, dict) and "id" in i}
    return set()


def ids_in_text(text: str | None, kind: str) -> set[str]:
    if not text:
        return set()
    try:
        return item_ids(parse_yaml(text), kind)
    except HomeAssistantError:
        return set()


def remove_orphans(hass: HomeAssistant, kind: str, removed: set[str]) -> None:
    """Drop registry entries for items that no longer exist, as the HA UI does."""
    registry = er.async_get(hass)
    for item_id in removed:
        if entity_id := registry.async_get_entity_id(kind, kind, item_id):
            registry.async_remove(entity_id)


def _entity_for(ctx: ToolContext, kind: str, item_id: str) -> str | None:
    if kind == "script":
        return f"script.{item_id}"
    return er.async_get(ctx.hass).async_get_entity_id(kind, kind, item_id)


class ListItems(Tool):
    def __init__(self) -> None:
        super().__init__(
            "list_config_items",
            "List UI-managed automations, scripts or scenes (id, alias, entity_id, state).",
            obj({"kind": {"type": "string", "enum": list(KINDS)}}, ["kind"]),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        kind = args["kind"]
        data = await _load(ctx, kind)
        items = (
            data.items()
            if KINDS[kind][1]
            else ((str(i.get("id")), i) for i in data if isinstance(i, dict))
        )
        out = []
        for item_id, item in items:
            entity_id = _entity_for(ctx, kind, item_id)
            state = ctx.hass.states.get(entity_id) if entity_id else None
            out.append(
                {
                    "id": item_id,
                    "alias": (item or {}).get("alias") or (item or {}).get("name"),
                    "entity_id": entity_id,
                    "state": state.state if state else None,
                }
            )
        return ToolOutput(out)


class GetItem(Tool):
    def __init__(self) -> None:
        super().__init__(
            "get_config_item",
            "Get the full config of an automation, script or scene by id or entity_id.",
            obj(
                {
                    "kind": {"type": "string", "enum": list(KINDS)},
                    "id": {"type": "string"},
                },
                ["kind", "id"],
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        kind = args["kind"]
        item_id = _resolve_id(ctx, kind, args["id"])
        item = _find(await _load(ctx, kind), kind, item_id)
        if item is None:
            raise ToolError(f"{kind} {item_id} not found in {KINDS[kind][0]}")
        return ToolOutput({"id": item_id, "config": item})


def _infer_kind(args: dict[str, Any]) -> dict[str, Any]:
    """Small models often put the kind under another name, or inside the config."""
    if args.get("kind") in KINDS:
        return args
    for key in ("domain", "type", "item_type"):
        if args.get(key) in KINDS:
            return {**args, "kind": args[key]}
    config = args.get("config")
    if isinstance(config, dict) and config.get("kind") in KINDS:
        rest = {k: v for k, v in config.items() if k != "kind"}
        return {**args, "kind": config["kind"], "config": rest}
    return args


class SaveItem(Tool):
    def __init__(self) -> None:
        super().__init__(
            "save_config_item",
            "Create or replace an automation, script or scene, then reload it. Pass the "
            "complete config (for automations: alias, description, triggers, conditions, "
            "actions, mode). Omit id to create a new one. Scripts need a slug id.",
            obj(
                {
                    "kind": {"type": "string", "enum": list(KINDS)},
                    "id": {"type": "string"},
                    "config": {"type": "object"},
                },
                ["kind", "config"],
            ),
        )

    def check_args(self, args: dict[str, Any]) -> dict[str, Any]:
        args = _infer_kind(args)
        args = super().check_args(args)
        config = args["config"]
        # Automations and scripts are named by 'alias'; 'name' is a common slip.
        if (
            args.get("kind") in ("automation", "script")
            and "name" in config
            and ("alias" not in config)
        ):
            config = {"alias": config["name"], **{k: v for k, v in config.items() if k != "name"}}
            args = {**args, "config": config}
        return args

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        return Risk.write()

    async def _plan(self, ctx: ToolContext, args: dict[str, Any]) -> tuple[str, Any, Any, str]:
        kind = args["kind"]
        keyed = KINDS[kind][1]
        item_id = args.get("id")
        if item_id:
            item_id = _resolve_id(ctx, kind, item_id)
        elif keyed:
            alias = str(args["config"].get("alias") or "script")
            item_id = (
                "".join(c if c.isalnum() else "_" for c in alias.lower()).strip("_") or "script"
            )
        else:
            item_id = str(int(time.time() * 1000))
        data = await _load(ctx, kind)
        old_item = _find(data, kind, item_id)
        config = dict(args["config"])
        config.pop("id", None)
        new_item = config if keyed else {"id": item_id, **config}
        return item_id, data, old_item, new_item

    async def preview(self, ctx: ToolContext, args: dict[str, Any]) -> Preview:
        item_id, _data, old_item, new_item = await self._plan(ctx, args)
        verb = "Update" if old_item is not None else "Create"
        return Preview(
            f"{verb} {args['kind']} {item_id}",
            diff_text(to_yaml(old_item), to_yaml(new_item), f"{args['kind']}/{item_id}"),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        kind = args["kind"]
        async with _lock(kind):
            item_id, data, old_item, new_item = await self._plan(ctx, args)
            await _validate(ctx, kind, item_id, new_item)
            path = _path(ctx, kind)
            old_text = await ctx.hass.async_add_executor_job(read_text, path)
            snap = await ctx.snapshots.save(
                "file",
                f"{'Update' if old_item is not None else 'Create'} {kind} {item_id}",
                {"path": path.name, "content": old_text},
            )
            if KINDS[kind][1]:
                data[item_id] = new_item
            elif old_item is not None:
                data[data.index(old_item)] = new_item
            else:
                data.append(new_item)
            await ctx.hass.async_add_executor_job(write_text, path, to_yaml(data))
        await ctx.hass.services.async_call(kind, "reload", {}, blocking=True)
        entity_id = _entity_for(ctx, kind, item_id)
        return ToolOutput(
            {"id": item_id, "entity_id": entity_id},
            f"Saved {kind} {item_id}",
            snapshot_id=snap,
        )


class DeleteItem(Tool):
    def __init__(self) -> None:
        super().__init__(
            "delete_config_item",
            "Delete an automation, script or scene, then reload.",
            obj(
                {
                    "kind": {"type": "string", "enum": list(KINDS)},
                    "id": {"type": "string"},
                },
                ["kind", "id"],
            ),
        )

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        return Risk.risky(f"deletes {args.get('kind')} {args.get('id')}")

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        kind = args["kind"]
        item_id = _resolve_id(ctx, kind, args["id"])
        async with _lock(kind):
            data = await _load(ctx, kind)
            item = _find(data, kind, item_id)
            if item is None:
                raise ToolError(f"{kind} {item_id} not found")
            path = _path(ctx, kind)
            old_text = await ctx.hass.async_add_executor_job(read_text, path)
            snap = await ctx.snapshots.save(
                "file",
                f"Delete {kind} {item_id}",
                {"path": path.name, "content": old_text},
            )
            if KINDS[kind][1]:
                del data[item_id]
            else:
                data.remove(item)
            await ctx.hass.async_add_executor_job(write_text, path, to_yaml(data))
        await ctx.hass.services.async_call(kind, "reload", {}, blocking=True)
        remove_orphans(ctx.hass, kind, {item_id})
        return ToolOutput({"ok": True}, f"Deleted {kind} {item_id}", snapshot_id=snap)


TOOLS: list[Tool] = [ListItems(), GetItem(), SaveItem(), DeleteItem()]
