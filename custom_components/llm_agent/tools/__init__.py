"""Tool framework: every tool declares a JSON schema, a risk classifier and a runner."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import json
from typing import Any, ClassVar

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ..approval import Risk
from ..providers.base import ToolSpec
from ..snapshots import Snapshots


class ToolError(HomeAssistantError):
    """A tool failed in a way the model should see and can correct."""


MAX_PARSE = 200_000


def _types(schema: dict[str, Any]) -> set[str]:
    t = schema.get("type")
    return set(t) if isinstance(t, list) else {t} if t else set()


def _parse_text(text: str) -> Any:
    """Parse JSON, or a Python-style literal (single quotes, True/None), which small
    models often produce. Literals only: nothing is evaluated."""
    if len(text) > MAX_PARSE:
        raise ValueError("too long")
    try:
        return json.loads(text)
    except ValueError:
        pass
    stripped = text.strip()
    try:
        return ast.literal_eval(stripped)
    except ValueError, SyntaxError:
        # An unquoted list of ids, e.g. [light.a, light.b]
        inner = stripped[1:-1]
        if stripped[:1] == "[" and stripped[-1:] == "]" and not set(inner) & set("[]{}:"):
            return [p.strip().strip("'\"") for p in inner.split(",") if p.strip()]
        closed = _close_brackets(stripped)
        if closed is None:
            raise
    try:
        return json.loads(closed)
    except ValueError:
        return ast.literal_eval(closed)


def _close_brackets(text: str) -> str | None:
    """Small models sometimes stop before the last closing brackets. Add the missing
    closers if that is the only problem: quotes balanced and no mismatched brackets."""
    pairs = {"{": "}", "[": "]"}
    stack: list[str] = []
    quote = ""
    escaped = False
    for ch in text:
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
        elif ch in pairs:
            stack.append(pairs[ch])
        elif ch in "}]" and (not stack or stack.pop() != ch):
            return None
    if quote or not stack or text[:1] not in pairs:
        return None
    return text + "".join(reversed(stack))


def _coerce(key: str, value: Any, schema: dict[str, Any]) -> Any:
    types = _types(schema)
    if not types or ("string" in types and isinstance(value, str)):
        return value
    if isinstance(value, str) and types & {"object", "array"}:
        try:
            parsed = _parse_text(value)
        except ValueError, SyntaxError, MemoryError, RecursionError:
            if "array" in types:
                return [value]  # a single item where a list was expected
            raise ToolError(
                f"'{key}' must be a JSON object, but got text that is not valid JSON. "
                "Send it as an object, not a string."
            ) from None
        value = parsed
    if isinstance(value, str) and "boolean" in types:
        # "False" as text would otherwise count as true.
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off", ""}:
            return False
        raise ToolError(f"'{key}' must be true or false, got {value!r}")
    if isinstance(value, str) and types & {"integer", "number"}:
        try:
            return int(value) if "integer" in types else float(value)
        except ValueError:
            raise ToolError(f"'{key}' must be a number, got {value!r}") from None
    if "object" in types and not isinstance(value, dict) and "array" not in types:
        raise ToolError(f"'{key}' must be an object, got {type(value).__name__}")
    if "array" in types and not isinstance(value, list) and "object" not in types:
        return [value]
    return value


def similar_entities(hass: HomeAssistant, wanted: str, limit: int = 5) -> list[str]:
    """Existing entity ids that look like what the model asked for."""
    domain, _, rest = wanted.lower().rpartition(".")
    key = rest.replace("_", " ")
    scored = []
    for state in hass.states.async_all():
        name = str(state.attributes.get("friendly_name") or "").lower()
        score = max(
            SequenceMatcher(None, key, state.object_id.replace("_", " ")).ratio(),
            SequenceMatcher(None, key, name).ratio() if name else 0.0,
        )
        obj = state.object_id.replace("_", " ")
        if len(key) >= 3 and (key in obj or key in name):
            score = max(score, 0.8)  # "e2e" → "e2e switch"
        if score < 0.5:
            continue
        # Same domain ranks first: the model usually gets the domain right.
        rank = score + (0.15 if domain and state.domain == domain else 0.0)
        scored.append((rank, state.entity_id))
    scored.sort(reverse=True)
    return [e for _rank, e in scored[:limit]]


def num_arg(
    args: dict[str, Any], key: str, default: float, low: float, high: float, cast: Any = int
) -> Any:
    """A numeric argument clamped to [low, high]; bad input becomes a ToolError."""
    value = args.get(key)
    try:
        number = cast(default if value is None or value == "" else value)
    except TypeError, ValueError:
        raise ToolError(f"{key} must be a number, got {value!r}") from None
    return max(cast(low), min(number, cast(high)))


def list_arg(args: dict[str, Any], key: str) -> list[Any]:
    """A list argument; null means empty and a single string becomes a one-item list."""
    value = args.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        raise ToolError(f"{key} must be a list")
    return value


@dataclass(slots=True)
class ToolContext:
    hass: HomeAssistant
    user_id: str | None
    options: dict[str, Any]
    snapshots: Snapshots


@dataclass(slots=True)
class ToolOutput:
    data: Any
    summary: str = ""
    snapshot_id: str | None = None
    # Pictures for vision models: {"media_type": "image/jpeg", "data": base64 text}
    images: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class Preview:
    """Shown on the approval card."""

    summary: str
    diff: str | None = None


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})
    # Results come from outside the home (web pages, search). After one, the chat asks
    # before every change.
    untrusted: ClassVar[bool] = False

    def spec(self) -> ToolSpec:
        return ToolSpec(self.name, self.description, self.parameters)

    def check_args(self, args: dict[str, Any]) -> dict[str, Any]:
        """Check the top-level arguments against the schema, repairing what models
        commonly get wrong (objects and lists sent as text, numbers as strings)."""
        props = self.parameters.get("properties", {})
        out = dict(args)
        for key in self.parameters.get("required", []):
            if out.get(key) is None:
                raise ToolError(f"Missing required argument '{key}'")
        for key, value in args.items():
            if key in props and value is not None:
                out[key] = _coerce(key, value, props[key])
        return out

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        return Risk.read()

    def review_keys(self, ctx: ToolContext, args: dict[str, Any]) -> list[str]:
        """Names matched against the always-ask list: the tool, and tool:action."""
        keys = [self.name]
        if isinstance(args.get("action"), str):
            keys.append(f"{self.name}:{args['action']}")
        return keys

    async def preview(self, ctx: ToolContext, args: dict[str, Any]) -> Preview | None:
        return None

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        raise NotImplementedError


def obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def build_tools(options: dict[str, Any]) -> list[Tool]:
    from . import (
        camera,
        config_items,
        dashboards,
        debug,
        files,
        integrations,
        reference,
        registry,
        states,
        system,
        web,
        websocket,
    )
    from .shell import ShellTool

    tools: list[Tool] = [
        *states.TOOLS,
        *registry.TOOLS,
        *config_items.TOOLS,
        *dashboards.TOOLS,
        *integrations.TOOLS,
        *files.TOOLS,
        *system.TOOLS,
        *websocket.TOOLS,
        *reference.TOOLS,
        *debug.TOOLS,
        *web.web_tools(options),
        *camera.camera_tools(options),
    ]
    if options.get("allow_shell"):
        tools.append(ShellTool())
    return tools
