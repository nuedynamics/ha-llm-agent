"""Home notes: a short, household-approved memory added to every chat."""

from __future__ import annotations

from typing import Any

from ..approval import Risk
from ..const import DOMAIN, NOTES_MAX
from . import Preview, Tool, ToolContext, ToolError, ToolOutput, obj
from .util import diff_text


def _store(ctx: ToolContext) -> Any:
    agent = ctx.hass.data.get(DOMAIN)
    if agent is None:
        raise ToolError("LLM Agent is not set up")
    return agent.store


class UpdateHomeNotes(Tool):
    def __init__(self) -> None:
        super().__init__(
            "update_home_notes",
            "Replace the home notes: short lasting facts and rules every chat sees (they are "
            "already in your instructions). Give the complete new text, one note per line, "
            f"keeping the existing notes you still want. At most {NOTES_MAX} characters. "
            "Never store secrets.",
            obj({"notes": {"type": "string"}}, ["notes"]),
        )
        # Notes shown on recent approval cards, to refuse a save over newer notes.
        # Denied or abandoned cards never reach run(), so only the latest few are kept.
        self._shown: dict[int, str] = {}

    def check_args(self, args: dict[str, Any]) -> dict[str, Any]:
        args = super().check_args(args)
        if not isinstance(args.get("notes"), str):
            raise ToolError("notes must be text")
        if len(args["notes"].strip()) > NOTES_MAX:
            raise ToolError(f"Home notes are limited to {NOTES_MAX} characters; shorten them")
        return args

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        return Risk.risky("changes what the AI remembers in every chat")

    async def needs_person(self, ctx: ToolContext, args: dict[str, Any]) -> bool:
        # Notes steer every later chat, so a person always sees what is remembered.
        return True

    async def preview(self, ctx: ToolContext, args: dict[str, Any]) -> Preview:
        old = _store(ctx).notes
        self._shown[id(args)] = old
        while len(self._shown) > 64:
            self._shown.pop(next(iter(self._shown)))
        new = args["notes"].strip()
        # Line-terminated, so an unchanged last line isn't shown as removed and re-added.
        return Preview(
            "Update home notes",
            diff_text(old + "\n" if old else "", new + "\n" if new else "", "home notes"),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        store = _store(ctx)
        changed = ToolError(
            "The home notes changed while this was waiting for approval. Read the new "
            "notes in your instructions next turn and propose the change again."
        )
        if id(args) not in self._shown:
            # no record of what the person was shown: don't guess it was today's notes
            raise changed
        old = self._shown.pop(id(args))
        if store.notes != old:
            raise changed
        snap = await ctx.snapshots.save("notes", "Update home notes", {"notes": old})
        if store.notes != old:  # saved in the panel while the snapshot was written
            raise changed
        store.set_notes(args["notes"])
        return ToolOutput(
            {"ok": True, "notes": store.notes}, "Updated home notes", snapshot_id=snap
        )


TOOLS: list[Tool] = [UpdateHomeNotes()]
