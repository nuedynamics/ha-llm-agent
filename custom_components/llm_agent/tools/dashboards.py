"""Lovelace dashboards: list, read, create/save with diff and undo, delete."""

from __future__ import annotations

from typing import Any

from ..approval import Risk
from . import Preview, Tool, ToolContext, ToolError, ToolOutput, obj
from .util import diff_text, to_yaml
from .websocket import ws_call


async def _dashboards(ctx: ToolContext) -> list[dict[str, Any]]:
    return await ws_call(ctx, "lovelace/dashboards/list") or []


async def _get_config(ctx: ToolContext, url_path: str | None) -> dict[str, Any] | None:
    try:
        return await ws_call(ctx, "lovelace/config", {"url_path": url_path})
    except ToolError as err:
        if "config_not_found" in str(err):
            return None
        raise


class ListDashboards(Tool):
    def __init__(self) -> None:
        super().__init__(
            "list_dashboards",
            "List dashboards (url_path, title, mode). The default dashboard has url_path null.",
            obj({}),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        items = [{"url_path": None, "title": "Overview (default)"}]
        for d in await _dashboards(ctx):
            items.append(
                {
                    "id": d.get("id"),
                    "url_path": d.get("url_path"),
                    "title": d.get("title"),
                    "mode": d.get("mode"),
                    "show_in_sidebar": d.get("show_in_sidebar"),
                }
            )
        return ToolOutput(items)


class GetDashboard(Tool):
    def __init__(self) -> None:
        super().__init__(
            "get_dashboard",
            "Get a dashboard's full config (views, cards). null/omitted url_path = default.",
            obj({"url_path": {"type": ["string", "null"]}}),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        config = await _get_config(ctx, args.get("url_path"))
        if config is None:
            return ToolOutput(
                {
                    "config": None,
                    "note": "Auto-generated dashboard; saving a config takes it over",
                }
            )
        return ToolOutput({"config": config})


class SaveDashboard(Tool):
    def __init__(self) -> None:
        super().__init__(
            "save_dashboard",
            "Save a full dashboard config (replaces it). To create a NEW dashboard, give a "
            "new url_path containing a hyphen (e.g. 'energy-view') and a title. Omitting "
            "url_path replaces the user's main (default) dashboard. Use get_dashboard first "
            "when editing.",
            obj(
                {
                    "url_path": {"type": ["string", "null"]},
                    "config": {
                        "type": "object",
                        "description": '{"views": [{"title": ..., "cards": [...]}]}',
                    },
                    "title": {"type": "string"},
                    "icon": {"type": "string"},
                    "show_in_sidebar": {"type": "boolean", "default": True},
                    "require_admin": {"type": "boolean", "default": False},
                },
                ["config"],
            ),
        )

    def check_args(self, args: dict[str, Any]) -> dict[str, Any]:
        args = super().check_args(args)
        config = args["config"]
        views, strategy = config.get("views"), config.get("strategy")
        if not (isinstance(views, list) and all(isinstance(v, dict) for v in views)) and not (
            isinstance(strategy, dict)
        ):
            raise ToolError(
                "config must be a dashboard: an object with a 'views' list, e.g. "
                '{"views": [{"title": "Home", "cards": [{"type": "entities", '
                '"entities": ["light.kitchen"]}]}]}'
            )
        return args

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        if not args.get("url_path"):
            return Risk.risky("replaces your main dashboard")
        return Risk.write()

    async def preview(self, ctx: ToolContext, args: dict[str, Any]) -> Preview:
        url_path = args.get("url_path")
        old = await _get_config(ctx, url_path)
        name = url_path or "default"
        return Preview(
            f"Save dashboard {name}"
            + ("" if old is not None else " (new or taking over auto-generated)"),
            diff_text(to_yaml(old), to_yaml(args["config"]), f"dashboard/{name}"),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        url_path = args.get("url_path")
        created = False
        if url_path:
            existing = {d.get("url_path") for d in await _dashboards(ctx)}
            if url_path not in existing:
                if "-" not in url_path:
                    raise ToolError("New dashboard url_path must contain a hyphen")
                payload = {
                    "url_path": url_path,
                    "title": args.get("title") or url_path.replace("-", " ").title(),
                    "show_in_sidebar": args.get("show_in_sidebar", True),
                    "require_admin": args.get("require_admin", False),
                }
                if args.get("icon"):
                    payload["icon"] = args["icon"]
                await ws_call(ctx, "lovelace/dashboards/create", payload)
                created = True
        old = None if created else await _get_config(ctx, url_path)
        snap = await ctx.snapshots.save(
            "lovelace",
            f"{'Create' if created else 'Save'} dashboard {url_path or 'default'}",
            {"url_path": url_path, "config": old, "created": created},
        )
        await ws_call(
            ctx,
            "lovelace/config/save",
            {"url_path": url_path, "config": args["config"]},
        )
        return ToolOutput(
            {"ok": True, "url_path": url_path, "created": created},
            f"{'Created' if created else 'Saved'} dashboard {url_path or 'default'}",
            snapshot_id=snap,
        )


class DeleteDashboard(Tool):
    def __init__(self) -> None:
        super().__init__(
            "delete_dashboard",
            "Delete a dashboard by url_path.",
            obj({"url_path": {"type": "string"}}, ["url_path"]),
        )

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        return Risk.risky(f"deletes dashboard {args.get('url_path')}")

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        url_path = args["url_path"]
        match = next((d for d in await _dashboards(ctx) if d.get("url_path") == url_path), None)
        if match is None:
            raise ToolError(f"Dashboard {url_path} not found")
        old = await _get_config(ctx, url_path)
        snap = await ctx.snapshots.save(
            "lovelace",
            f"Delete dashboard {url_path}",
            {"url_path": url_path, "config": old, "deleted_meta": match},
        )
        await ws_call(ctx, "lovelace/dashboards/delete", {"dashboard_id": match["id"]})
        return ToolOutput({"ok": True}, f"Deleted dashboard {url_path}", snapshot_id=snap)


TOOLS: list[Tool] = [
    ListDashboards(),
    GetDashboard(),
    SaveDashboard(),
    DeleteDashboard(),
]
