"""Read and edit files in the Home Assistant config directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..approval import Risk
from . import Preview, Tool, ToolContext, ToolError, ToolOutput, num_arg, obj
from .util import diff_text, read_text, write_text

MAX_READ_CHARS = 60000
SENSITIVE_NAMES = {
    "secrets.yaml",
    ".storage/auth",
    ".storage/auth_provider.homeassistant",
    ".storage/core.config_entries",
    ".storage/application_credentials",
    ".storage/cloud",
    ".storage/http",
    ".storage/onboarding",
    ".storage/llm_agent.chatgpt_auth",  # ChatGPT sign-in tokens
}
SENSITIVE_PREFIXES = (".cloud/", ".ssh/")
SENSITIVE_SUFFIXES = (".pem", ".key", ".db", ".db-wal", ".db-shm")


class FileAccess:
    def __init__(self, ctx: ToolContext) -> None:
        self.root = Path(ctx.hass.config.path()).resolve()
        self.protect = ctx.options.get("protect_sensitive", True)

    def resolve(self, raw: str) -> tuple[Path, str]:
        raw = (raw or "").strip() or "."
        path = Path(raw)
        if not path.is_absolute():
            path = self.root / path
        path = path.resolve()
        try:
            rel = path.relative_to(self.root).as_posix()
        except ValueError:
            if self.protect:
                raise ToolError(
                    "Only files inside the config directory are allowed. An admin can turn off "
                    "'Protect sensitive data' in the LLM Agent options to lift this."
                ) from None
            return path, str(path)
        if self.protect and self.is_sensitive(rel):
            raise ToolError(
                f"{rel} holds credentials or databases and is protected. Use !secret references "
                "instead of reading secrets. An admin can turn off 'Protect sensitive data'."
            )
        return path, rel

    @staticmethod
    def is_sensitive(rel: str) -> bool:
        # HA keeps an unreadable storage file as <name>.corrupt.<time>: same contents.
        base = rel.split(".corrupt.", 1)[0]
        return (
            base in SENSITIVE_NAMES
            or rel.startswith(SENSITIVE_PREFIXES)
            or rel.endswith(SENSITIVE_SUFFIXES)
        )


class ListFiles(Tool):
    def __init__(self) -> None:
        super().__init__(
            "list_files",
            "List a directory under the HA config dir (default: the config dir itself).",
            obj({"path": {"type": "string", "default": "."}}),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        path, rel = FileAccess(ctx).resolve(args.get("path") or ".")

        def _list() -> list[dict[str, Any]]:
            if not path.is_dir():
                raise ToolError(f"{rel} is not a directory")
            out = []
            for child in sorted(path.iterdir())[:500]:
                try:
                    stat = child.stat()
                except OSError:
                    continue
                out.append(
                    {
                        "name": child.name + ("/" if child.is_dir() else ""),
                        "size": stat.st_size if child.is_file() else None,
                    }
                )
            return out

        return ToolOutput(await ctx.hass.async_add_executor_job(_list))


class ReadFile(Tool):
    def __init__(self) -> None:
        super().__init__(
            "read_file",
            "Read a text file in the config dir. Use offset/limit (lines) for big files.",
            obj(
                {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "default": 0},
                    "limit": {"type": "integer", "default": 400},
                },
                ["path"],
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        path, rel = FileAccess(ctx).resolve(args["path"])
        text = await ctx.hass.async_add_executor_job(read_text, path)
        if text is None:
            raise ToolError(f"{rel} does not exist")
        lines = text.splitlines()
        offset = num_arg(args, "offset", 0, 0, 10**9)
        limit = num_arg(args, "limit", 400, 1, 4000)
        chunk = "\n".join(lines[offset : offset + limit])[:MAX_READ_CHARS]
        return ToolOutput(
            {"path": rel, "total_lines": len(lines), "offset": offset, "content": chunk}
        )


class WriteFile(Tool):
    def __init__(self) -> None:
        super().__init__(
            "write_file",
            "Change a file in the config dir. Either give 'content' (whole new file) or "
            "'old'/'new' to replace one exact, unique snippet (preferred for small edits). "
            "After editing YAML, run check_config before restarting.",
            obj(
                {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
                ["path"],
            ),
        )

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        return Risk.risky(f"edits file {args.get('path')}")

    async def _plan(
        self, ctx: ToolContext, args: dict[str, Any]
    ) -> tuple[Path, str, str | None, str]:
        path, rel = FileAccess(ctx).resolve(args["path"])
        old_text = await ctx.hass.async_add_executor_job(read_text, path)
        if args.get("old") is not None:
            if old_text is None:
                raise ToolError(f"{rel} does not exist")
            count = old_text.count(args["old"])
            if count != 1:
                raise ToolError(f"'old' snippet found {count} times in {rel}; it must be unique")
            new_text = old_text.replace(args["old"], args.get("new") or "", 1)
        elif args.get("content") is not None:
            new_text = args["content"]
        else:
            raise ToolError("Give 'content' or 'old'/'new'")
        return path, rel, old_text, new_text

    async def preview(self, ctx: ToolContext, args: dict[str, Any]) -> Preview:
        _path, rel, old_text, new_text = await self._plan(ctx, args)
        verb = "Edit" if old_text is not None else "Create"
        return Preview(f"{verb} {rel}", diff_text(old_text, new_text, rel))

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        path, rel, old_text, new_text = await self._plan(ctx, args)
        snap = await ctx.snapshots.save("file", f"Edit {rel}", {"path": rel, "content": old_text})
        await ctx.hass.async_add_executor_job(write_text, path, new_text)
        return ToolOutput({"ok": True, "path": rel}, f"Wrote {rel}", snapshot_id=snap)


TOOLS: list[Tool] = [ListFiles(), ReadFile(), WriteFile()]
