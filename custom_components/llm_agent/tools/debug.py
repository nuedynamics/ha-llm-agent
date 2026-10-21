"""Debugging the home: automation and script traces, the logbook, and the HA log file."""

from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
import re
from typing import Any

from homeassistant.util import dt as dt_util

from . import Tool, ToolContext, ToolError, ToolOutput, list_arg, num_arg, obj
from .websocket import ws_call

MAX_TRACE_CHARS = 12_000
LOG_TAIL_BYTES = 4 * 1024 * 1024
MAX_ENTRY_CHARS = 2_000

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_LOG_LINE = re.compile(
    r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)?) (DEBUG|INFO|WARNING|ERROR|CRITICAL) "
    r"\(([^)]*)\) \[([^\]]+)\] ?(.*)$"
)
_LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}
# Values that look like credentials are masked before log or trace text reaches the model.
_SECRET_NAME = r"(?:access_token|refresh_token|api_key|apikey|api-key|password|passwd|pwd|token|secret|client_secret|private_key|authorization|auth|x-api-key|cookie)"
_SECRETS = re.compile(
    rf"(?i)({_SECRET_NAME}[\"']?\s*[:=]\s*)"
    r"(\"[^\"]*(?:\"|$)|'[^']*(?:'|$)|(?:bearer\s+|basic\s+)?[^\s\"',;&}\]]+)"
)


def _mask_value(m: re.Match[str]) -> str:
    value = m.group(2)
    quote = value[0] if value[:1] in ("'", '"') else ""
    return f"{m.group(1)}{quote}***{quote}"


_AUTH_SCHEME = re.compile(r"(?i)\b(bearer|basic|digest)(\s+)([a-z0-9._~+/=\-]{4,})")
_URL_CREDS = re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*://)[^/\s:@]+:[^/\s@]*@")
_JWT = re.compile(r"\beyJ[a-zA-Z0-9_\-]{8,}\.[a-zA-Z0-9_\-]{8,}\.[a-zA-Z0-9_\-]{8,}")
_SECRET_KEY = re.compile(rf"(?i){_SECRET_NAME}")


def redact(text: str) -> str:
    text = _URL_CREDS.sub(r"\1***:***@", text)
    text = _AUTH_SCHEME.sub(r"\1\2***", text)
    text = _SECRETS.sub(_mask_value, text)
    return _JWT.sub("***", text)


def scrub(value: Any, depth: int = 0) -> Any:
    """Mask credentials anywhere in a nested value: keys that name a secret lose their
    value, and every string goes through redact()."""
    if depth > 20:
        return "…"
    if isinstance(value, dict):
        return {
            k: "***" if isinstance(k, str) and _SECRET_KEY.search(k) else scrub(v, depth + 1)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [scrub(v, depth + 1) for v in value]
    if isinstance(value, str):
        return redact(value)
    return value


def _short(value: Any, limit: int = 300) -> Any:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + "…"


def _item_id(ctx: ToolContext, domain: str, target: str) -> str:
    """Trace item id: an automation's `id` attribute, a script's object id."""
    target = target.strip()
    if "." not in target:
        target = f"{domain}.{target}"
    state = ctx.hass.states.get(target)
    if domain == "script":
        return target.split(".", 1)[1]
    if state is None:
        raise ToolError(f"No automation {target}. Use search_entities to find it.")
    item = state.attributes.get("id")
    if not item:
        raise ToolError(
            f"{target} has no id (it is defined in YAML without 'id:'), so it has no traces."
        )
    return str(item)


def condense_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """The useful part of a trace: what triggered, which conditions passed, each step's
    result or error, and the final state."""
    steps = []
    for path, entries in (trace.get("trace") or {}).items():
        for entry in entries:
            step: dict[str, Any] = {"step": path}
            if entry.get("error"):
                step["error"] = _short(scrub(entry["error"]), 500)
            result = entry.get("result")
            if result:
                step["result"] = _short(scrub(result))
            changed = entry.get("changed_variables")
            if changed:
                # trigger and context are large and already summarised elsewhere
                kept = {k: v for k, v in changed.items() if k not in ("trigger", "context", "this")}
                if kept:
                    step["variables"] = _short(scrub(kept))
            steps.append(step)
    out = {
        "run_id": trace.get("run_id"),
        "started": trace.get("timestamp", {}).get("start"),
        "finished": trace.get("timestamp", {}).get("finish"),
        "state": trace.get("state"),
        "result": trace.get("script_execution"),
        "error": _short(trace["error"], 1000) if trace.get("error") else None,
        "trigger": _short(trace.get("trigger"), 500) if trace.get("trigger") else None,
        "steps": steps,
    }
    out = scrub(out)
    if len(json.dumps(out, default=str)) > MAX_TRACE_CHARS and len(out["steps"]) > 4:
        out["steps"] = [
            *out["steps"][:2],
            {"step": "…", "note": "steps omitted"},
            *out["steps"][-2:],
        ]
    if len(json.dumps(out, default=str)) > MAX_TRACE_CHARS:
        out["steps"] = [
            {"step": "…", "note": f"{len(steps)} steps omitted; the trace is too large"}
        ]
    return out


class Traces(Tool):
    def __init__(self) -> None:
        super().__init__(
            "get_traces",
            "Recent runs of an automation or script, to explain why it did or did not do "
            "something. Without run_id: the last runs (when, how it ended, errors). With "
            "run_id ('latest' for the newest): the trigger, each condition and action step "
            "with its result or error.",
            obj(
                {
                    "entity_id": {
                        "type": "string",
                        "description": "automation.x or script.x",
                    },
                    "run_id": {"type": "string"},
                },
                ["entity_id"],
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        entity_id = str(args["entity_id"])
        domain = "script" if entity_id.startswith("script.") else "automation"
        item_id = _item_id(ctx, domain, entity_id)
        runs = await ws_call(ctx, "trace/list", {"domain": domain, "item_id": item_id}) or []
        runs = sorted(runs, key=lambda r: (r.get("timestamp") or {}).get("start") or "")
        run_id = args.get("run_id")
        if not run_id:
            if not runs:
                return ToolOutput(
                    f"No stored runs for {entity_id}. It has not run since Home Assistant "
                    "started, or tracing is off (stored_traces: 0)."
                )
            return ToolOutput(
                scrub(
                    [
                        {
                            "run_id": r.get("run_id"),
                            "started": (r.get("timestamp") or {}).get("start"),
                            "state": r.get("state"),
                            "result": r.get("script_execution"),
                            "last_step": r.get("last_step"),
                            "error": r.get("error"),
                            "trigger": r.get("trigger"),
                        }
                        for r in runs[-10:]
                    ]
                ),
                summary=f"{len(runs)} runs of {entity_id}",
            )
        if run_id == "latest":
            if not runs:
                raise ToolError(f"No stored runs for {entity_id}")
            run_id = runs[-1]["run_id"]
        trace = await ws_call(
            ctx, "trace/get", {"domain": domain, "item_id": item_id, "run_id": str(run_id)}
        )
        return ToolOutput(condense_trace(trace or {}), summary=f"Trace {run_id} of {entity_id}")


class Logbook(Tool):
    def __init__(self) -> None:
        super().__init__(
            "get_logbook",
            "Logbook entries (state changes, automations triggered, who did what) for the "
            "last hours, optionally for some entities. Oldest first.",
            obj(
                {
                    "entity_ids": {"type": "array", "items": {"type": "string"}},
                    "hours": {"type": "number", "description": "default 24, max 168"},
                    "limit": {"type": "integer", "description": "default 100, max 300"},
                }
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        hours = num_arg(args, "hours", 24, 0.1, 168, float)
        limit = num_arg(args, "limit", 100, 1, 300)
        end = dt_util.utcnow()
        payload: dict[str, Any] = {
            "start_time": (end - timedelta(hours=hours)).isoformat(),
            "end_time": end.isoformat(),
        }
        if entity_ids := list_arg(args, "entity_ids"):
            payload["entity_ids"] = [str(e) for e in entity_ids]
        events = await ws_call(ctx, "logbook/get_events", payload) or []
        out = []
        for event in events[-limit:]:
            when = event.get("when")
            if isinstance(when, (int, float)):
                when = dt_util.as_local(dt_util.utc_from_timestamp(when)).isoformat(
                    timespec="seconds"
                )
            row = {
                "when": when,
                "entity_id": event.get("entity_id"),
                "name": event.get("name"),
                "state": event.get("state"),
                "message": redact(event["message"]) if event.get("message") else None,
                "by": event.get("context_entity_id")
                or event.get("context_event_type")
                or event.get("context_user_id"),
            }
            out.append({k: v for k, v in row.items() if v not in (None, "")})
        skipped = max(0, len(events) - limit)
        return ToolOutput(
            {"entries": out, "older_entries_left_out": skipped} if skipped else out,
            summary=f"{len(out)} logbook entries",
        )


def parse_log(text: str) -> list[dict[str, Any]]:
    """Split HA log text into entries; continuation lines (tracebacks) join the entry above."""
    entries: list[dict[str, Any]] = []
    for raw in text.splitlines():
        line = _ANSI.sub("", raw)
        m = _LOG_LINE.match(line)
        if m:
            entries.append(
                {
                    "time": m.group(1),
                    "level": m.group(2),
                    "logger": m.group(4),
                    "message": m.group(5),
                }
            )
        elif entries and line.strip():
            msg = entries[-1]["message"]
            if len(msg) < MAX_ENTRY_CHARS:
                entries[-1]["message"] = msg + "\n" + line
    for entry in entries:
        # mask first: a cut can drop the quote that marks where a secret ends
        entry["message"] = redact(entry["message"])[:MAX_ENTRY_CHARS]
    return entries


def _matches_integration(logger: str, name: str) -> bool:
    name = name.strip().lower()
    logger = logger.lower()
    return (
        logger == name
        or f"components.{name}" in logger
        or logger.startswith(f"custom_components.{name}")
        or logger.startswith(f"{name}.")
    )


def _read_tail(path: Path) -> str | None:
    try:
        with path.open("rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - LOG_TAIL_BYTES))
            data = fh.read()
    except FileNotFoundError:
        return None
    text = data.decode("utf-8", "replace")
    if len(data) == LOG_TAIL_BYTES:
        text = text.split("\n", 1)[-1]  # drop the partial first line
    return text


class ReadLog(Tool):
    def __init__(self) -> None:
        super().__init__(
            "read_log",
            "Search home-assistant.log: entries at or above a level, optionally for one "
            "integration or containing some text, newest last. previous_run reads the log "
            "from before the last restart. Credentials in log lines are masked.",
            obj(
                {
                    "integration": {
                        "type": "string",
                        "description": "domain or logger, e.g. zha or homeassistant.core",
                    },
                    "level": {
                        "type": "string",
                        "enum": ["debug", "info", "warning", "error"],
                        "description": "minimum level, default warning",
                    },
                    "contains": {"type": "string"},
                    "previous_run": {"type": "boolean"},
                    "limit": {"type": "integer", "description": "default 40, max 200"},
                }
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        name = "home-assistant.log.1" if args.get("previous_run") else "home-assistant.log"
        path = Path(ctx.hass.config.path(name))
        text = await ctx.hass.async_add_executor_job(_read_tail, path)
        if text is None:
            raise ToolError(
                f"{name} was not found. Home Assistant may log to the console only; use "
                "system logs for recent errors instead."
            )
        level = _LEVELS.get(str(args.get("level") or "warning").lower(), 30)
        integration = args.get("integration")
        needle = str(args.get("contains") or "").lower()
        limit = num_arg(args, "limit", 40, 1, 200)
        entries = [
            e
            for e in await ctx.hass.async_add_executor_job(parse_log, text)
            if _LEVELS[e["level"].lower()] >= level
            and (not integration or _matches_integration(e["logger"], str(integration)))
            and (not needle or needle in e["message"].lower() or needle in e["logger"].lower())
        ]
        shown = entries[-limit:]
        return ToolOutput(
            {"matches": len(entries), "entries": shown}
            if len(entries) > limit
            else shown or f"No matching entries in {name}.",
            summary=f"{len(entries)} log entries",
        )


TOOLS: list[Tool] = [Traces(), Logbook(), ReadLog()]
