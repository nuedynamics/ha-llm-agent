"""Integrations: list config entries, run config flows, reload and remove entries."""

from __future__ import annotations

from typing import Any

from homeassistant import data_entry_flow
from homeassistant.helpers import config_validation as cv
import probatio

from ..approval import Risk
from ..snapshots import full_backup
from . import Tool, ToolContext, ToolError, ToolOutput, obj

ACTIONS = ["list", "start_flow", "continue_flow", "abort_flow", "reload", "remove"]


def _flow_json(result: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "type",
        "flow_id",
        "handler",
        "step_id",
        "errors",
        "description_placeholders",
        "reason",
        "title",
        "menu_options",
        "progress_action",
        "url",
    )
    out = {k: result[k] for k in keep if k in result and result[k] is not None}
    out["type"] = str(result.get("type"))
    if (schema := result.get("data_schema")) is not None:
        try:
            out["data_schema"] = probatio.to_field_list(
                schema, custom_serializer=cv.custom_serializer
            )
        except TypeError, ValueError:
            out["data_schema"] = "unserializable schema"
    if result.get("type") is data_entry_flow.FlowResultType.CREATE_ENTRY and result.get("result"):
        entry = result["result"]
        out["entry_id"] = getattr(entry, "entry_id", None)
    return out


class IntegrationsTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            "integrations",
            "Manage integrations. list: config entries (optionally for a domain). "
            "start_flow: begin adding an integration (domain), returns the form to fill. "
            "continue_flow: submit user_input for flow_id. abort_flow. reload/remove: by entry_id. "
            "Discovered devices show up as flows in list (in_progress).",
            obj(
                {
                    "action": {"type": "string", "enum": ACTIONS},
                    "domain": {"type": "string"},
                    "flow_id": {"type": "string"},
                    "entry_id": {"type": "string"},
                    "user_input": {"type": "object"},
                },
                ["action"],
            ),
        )

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        action = args.get("action")
        if action == "list":
            return Risk.read()
        if action == "remove":
            return Risk.risky(f"removes integration entry {args.get('entry_id')}")
        if action == "start_flow" or action == "continue_flow":
            return Risk.risky("adds or changes an integration")
        return Risk.write()

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        hass = ctx.hass
        entries = hass.config_entries
        action = args["action"]
        try:
            if action == "list":
                domain = args.get("domain")
                items = [
                    {
                        "entry_id": e.entry_id,
                        "domain": e.domain,
                        "title": e.title,
                        "state": str(e.state.value),
                        "disabled": e.disabled_by is not None,
                    }
                    for e in entries.async_entries(domain)
                ]
                flows = [
                    {
                        "flow_id": f["flow_id"],
                        "handler": f["handler"],
                        "step_id": f.get("step_id"),
                        "source": f.get("context", {}).get("source"),
                    }
                    for f in entries.flow.async_progress()
                    if not domain or f["handler"] == domain
                ]
                return ToolOutput({"entries": items, "in_progress": flows})
            if action == "start_flow":
                if not args.get("domain"):
                    raise ToolError("domain is required")
                result = await entries.flow.async_init(
                    args["domain"],
                    context={"source": "user", "show_advanced_options": True},
                )
                return ToolOutput(_flow_json(result), f"Started {args['domain']} setup")
            if action == "continue_flow":
                result = await entries.flow.async_configure(
                    args["flow_id"], args.get("user_input") or {}
                )
                return ToolOutput(_flow_json(result))
            if action == "abort_flow":
                entries.flow.async_abort(args["flow_id"])
                return ToolOutput({"ok": True})
            entry_id = args.get("entry_id") or ""
            entry = entries.async_get_entry(entry_id)
            if entry is None:
                raise ToolError(f"Config entry {entry_id} not found")
            if action == "reload":
                ok = await entries.async_reload(entry_id)
                return ToolOutput({"ok": ok}, f"Reloaded {entry.title}")
            if action == "remove":
                note = ""
                if ctx.options.get("backup_before_risky", True):
                    note = await full_backup(hass, f"remove integration {entry.title}")
                await entries.async_remove(entry_id)
                return ToolOutput({"ok": True, "backup": note}, f"Removed {entry.title}")
        except data_entry_flow.UnknownFlow as err:
            raise ToolError("Unknown or finished flow_id") from err
        except data_entry_flow.UnknownHandler as err:
            raise ToolError(f"No integration named {args.get('domain')}") from err
        except probatio.Invalid as err:
            raise ToolError(f"Invalid input: {err}") from err
        raise ToolError(f"Unknown action {action}")


TOOLS: list[Tool] = [IntegrationsTool()]
