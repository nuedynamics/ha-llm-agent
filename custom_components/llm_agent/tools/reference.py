"""Built-in Home Assistant reference pages, for models that don't know HA's YAML shapes.

The pages live in ../reference/*.md. Each starts with '# Title' and a '> summary' line;
the summaries form a short index in the system prompt (cached with it), and the model
loads a page on demand with read_reference.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from . import Tool, ToolContext, ToolError, ToolOutput, obj

REFERENCE_DIR = Path(__file__).parent.parent / "reference"
# Index order: the page to read first comes first.
ORDER = (
    "automations",
    "triggers",
    "conditions",
    "actions",
    "targets",
    "templates",
    "scripts-scenes",
    "dashboards",
    "helpers",
)

_pages: dict[str, str] | None = None


def _read_pages() -> dict[str, str]:
    found = {p.stem: p.read_text(encoding="utf-8") for p in REFERENCE_DIR.glob("*.md")}
    return {name: found[name] for name in (*ORDER, *sorted(found)) if name in found}


async def async_pages(hass: HomeAssistant) -> dict[str, str]:
    """Read the pages once (in the executor) and keep them; they are about 15 KB."""
    global _pages
    if _pages is None:
        _pages = await hass.async_add_executor_job(_read_pages)
    return _pages


def summary(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("> "):
            return line[2:].strip()
    return ""


async def async_index(hass: HomeAssistant) -> str:
    pages = await async_pages(hass)
    lines = [f"- {name}: {summary(text)}" for name, text in pages.items()]
    return (
        "Reference pages (read with read_reference before writing automations, scripts, "
        "scenes, dashboards, templates or helpers; they show the exact YAML shape):\n"
        + "\n".join(lines)
    )


class ReadReference(Tool):
    def __init__(self) -> None:
        super().__init__(
            "read_reference",
            "Read a built-in Home Assistant reference page (see the list in your "
            "instructions), with examples of the exact config shape.",
            obj({"page": {"type": "string", "enum": list(ORDER)}}, ["page"]),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        pages = await async_pages(ctx.hass)
        name = str(args["page"]).strip().lower().removesuffix(".md")
        if name not in pages:
            raise ToolError(f"No reference page {name!r}. Pages: {', '.join(pages)}")
        return ToolOutput(pages[name], summary=f"Read the {name} reference")


TOOLS: list[Tool] = [ReadReference()]
