"""Tool framework: every tool declares a JSON schema, a risk classifier and a runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ..approval import Risk
from ..providers.base import ToolSpec
from ..snapshots import Snapshots


class ToolError(HomeAssistantError):
    """A tool failed in a way the model should see and can correct."""


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

    def spec(self) -> ToolSpec:
        return ToolSpec(self.name, self.description, self.parameters)

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        return Risk.read()

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
        config_items,
        dashboards,
        files,
        integrations,
        registry,
        states,
        system,
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
    ]
    if options.get("allow_shell"):
        tools.append(ShellTool())
    return tools
