"""Config check, reloads, restart, logs and undo."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from homeassistant.helpers.check_config import async_check_ha_config_file

from ..approval import Risk
from . import Tool, ToolContext, ToolError, ToolOutput, obj
from .config_items import ids_in_text, remove_orphans
from .util import read_text, remove_file, write_text
from .websocket import ws_call

RELOADABLE_FILES = {
    "automations.yaml": "automation",
    "scripts.yaml": "script",
    "scenes.yaml": "scene",
}


async def check_config(ctx: ToolContext) -> dict[str, Any]:
    result = await async_check_ha_config_file(ctx.hass)
    return {
        "valid": not result.errors,
        "errors": [{"domain": e.domain, "message": e.message[:500]} for e in result.errors[:20]],
        "warnings": [
            {"domain": w.domain, "message": w.message[:300]} for w in result.warnings[:20]
        ],
    }


class SystemTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            "system",
            "check_config: validate configuration. reload: reload a domain's YAML (domain, or "
            "'all'). restart: restart Home Assistant (runs check_config first). logs: recent "
            "errors and warnings from the system log.",
            obj(
                {
                    "action": {
                        "type": "string",
                        "enum": ["check_config", "reload", "restart", "logs"],
                    },
                    "domain": {"type": "string"},
                },
                ["action"],
            ),
        )

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        action = args.get("action")
        if action in ("check_config", "logs"):
            return Risk.read()
        if action == "restart":
            return Risk.risky("restarts Home Assistant")
        return Risk.write()

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        hass = ctx.hass
        action = args["action"]
        if action == "check_config":
            return ToolOutput(await check_config(ctx))
        if action == "logs":
            entries = await ws_call(ctx, "system_log/list") or []
            return ToolOutput(
                [
                    {
                        "level": e.get("level"),
                        "source": (e.get("source") or [None])[0],
                        "message": " | ".join(e.get("message") or [])[:400],
                        "count": e.get("count"),
                    }
                    for e in entries[:30]
                ]
            )
        if action == "reload":
            domain = args.get("domain") or "all"
            if domain == "all":
                await hass.services.async_call("homeassistant", "reload_all", {}, blocking=True)
            elif hass.services.has_service(domain, "reload"):
                await hass.services.async_call(domain, "reload", {}, blocking=True)
            else:
                raise ToolError(f"{domain} has no reload action; it may need a restart")
            return ToolOutput({"ok": True}, f"Reloaded {domain}")
        if action == "restart":
            result = await check_config(ctx)
            if not result["valid"] and ctx.options.get("block_invalid_restart", True):
                raise ToolError(
                    "Configuration is invalid, restart refused: "
                    + "; ".join(e["message"] for e in result["errors"][:5])
                )

            # Restart shortly after the tool returns so the reply and history are saved.
            async def _later() -> None:
                await asyncio.sleep(3)
                await hass.services.async_call("homeassistant", "restart", {})

            hass.async_create_background_task(_later(), "llm_agent_restart")
            return ToolOutput(
                {"ok": True, "config_valid": result["valid"]},
                "Restarting Home Assistant in 3 seconds",
            )
        raise ToolError(f"Unknown action {action}")


class UndoTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            "undo",
            "List recent change snapshots, or restore one (by snapshot_id) to undo a change "
            "made by this agent.",
            obj({"snapshot_id": {"type": "string"}}),
        )

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        return Risk.write("restores a previous version") if args.get("snapshot_id") else Risk.read()

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        snap_id = args.get("snapshot_id")
        if not snap_id:
            return ToolOutput(await ctx.snapshots.list())
        return ToolOutput(*await restore_snapshot(ctx, snap_id))


async def restore_snapshot(ctx: ToolContext, snap_id: str) -> tuple[dict[str, Any], str]:
    snap = await ctx.snapshots.load(snap_id)
    if snap is None:
        raise ToolError(f"Snapshot {snap_id} not found")
    if snap.get("undone"):
        raise ToolError("This change was already undone")
    result = await _restore(ctx, snap)
    await ctx.snapshots.mark_undone(snap_id)
    return result


async def _restore(ctx: ToolContext, snap: dict[str, Any]) -> tuple[dict[str, Any], str]:
    hass = ctx.hass
    if snap["kind"] == "file":
        root = Path(hass.config.path())
        path = Path(snap["path"])
        path = path if path.is_absolute() else root / path
        content = snap.get("content")
        domain = RELOADABLE_FILES.get(path.name) if path.parent == root else None
        before: set[str] = set()
        if domain:
            before = ids_in_text(await hass.async_add_executor_job(read_text, path), domain)
        if content is None:
            await hass.async_add_executor_job(remove_file, path)
        else:
            await hass.async_add_executor_job(write_text, path, content)
        if domain:
            await hass.services.async_call(domain, "reload", {}, blocking=True)
            remove_orphans(hass, domain, before - ids_in_text(content, domain))
        verb = "Removed" if content is None else "Restored"
        return {"ok": True, "restored": snap["path"]}, f"{verb} {snap['path']}"
    if snap["kind"] == "lovelace":
        url_path = snap.get("url_path")
        if snap.get("created"):
            dashboards = await ws_call(ctx, "lovelace/dashboards/list") or []
            match = next((d for d in dashboards if d.get("url_path") == url_path), None)
            if match:
                await ws_call(ctx, "lovelace/dashboards/delete", {"dashboard_id": match["id"]})
            return {"ok": True}, f"Removed dashboard {url_path}"
        if meta := snap.get("deleted_meta"):
            payload = {
                k: meta[k]
                for k in (
                    "url_path",
                    "title",
                    "icon",
                    "show_in_sidebar",
                    "require_admin",
                )
                if meta.get(k) is not None
            }
            await ws_call(ctx, "lovelace/dashboards/create", payload)
        if snap.get("config") is None:
            await ws_call(ctx, "lovelace/config/delete", {"url_path": url_path})
        else:
            await ws_call(
                ctx,
                "lovelace/config/save",
                {"url_path": url_path, "config": snap["config"]},
            )
        return {"ok": True}, f"Restored dashboard {url_path or 'default'}"
    raise ToolError(f"Unknown snapshot kind {snap['kind']}")


TOOLS: list[Tool] = [SystemTool(), UndoTool()]
