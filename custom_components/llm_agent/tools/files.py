"""Read and edit files in the Home Assistant config directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.yaml import Input
import yaml

from ..approval import Risk
from . import Preview, Tool, ToolContext, ToolError, ToolOutput, num_arg, obj
from .util import FILE_LOCK, diff_text, read_text, text_hash, write_text

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
SENSITIVE_PREFIXES = (".cloud/", ".ssh/", ".llm_agent/")  # .llm_agent: undo snapshots
SENSITIVE_SUFFIXES = (".pem", ".key", ".db", ".db-wal", ".db-shm")


class _AnyTagLoader(yaml.SafeLoader):
    """Syntax check only: HA tags (!include, !secret, !env_var, !input...) are accepted
    but never resolved, so checking a file can't read another file or the environment."""


_AnyTagLoader.add_multi_constructor("!", lambda loader, suffix, node: None)
# Blueprint inputs keep HA's own (inert) form, so HA's check for undeclared inputs runs.
_AnyTagLoader.add_constructor(
    "!input", lambda loader, node: Input(str(loader.construct_scalar(node)))
)


def check_syntax(rel: str, text: str) -> None:
    """Refuse a file that HA could not load, before it is written.

    YAML must parse; blueprints must also pass HA's blueprint schema; python_scripts
    must compile (they are never run here). Blocking: call it in an executor. Errors
    only quote the text being checked."""
    try:
        _check(rel, text)
    except ToolError:
        raise
    except Exception as err:
        raise ToolError(f"Not saved: {rel} could not be checked ({type(err).__name__})") from err


def _check(rel: str, text: str) -> None:
    lower = rel.lower()
    if lower.endswith((".yaml", ".yml")):
        try:
            data = yaml.load(text, Loader=_AnyTagLoader)
        except yaml.YAMLError as err:
            raise ToolError(f"Not saved: {rel} is not valid YAML: {err}") from err
        if lower.startswith("blueprints/"):
            _check_blueprint(rel, data)
    elif lower.startswith("python_scripts/") and lower.endswith(".py"):
        try:
            compile(text, rel, "exec")
        except (SyntaxError, ValueError) as err:
            raise ToolError(f"Not saved: {rel} has a Python syntax error: {err}") from err


def _check_blueprint(rel: str, data: Any) -> None:
    from homeassistant.components.blueprint.models import Blueprint
    from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA

    if not isinstance(data, dict):
        raise ToolError(f"Not saved: {rel} is not a blueprint")
    parts = rel.split("/")
    domain = parts[1] if len(parts) > 2 else None
    try:
        Blueprint(data, path=rel, expected_domain=domain, schema=BLUEPRINT_SCHEMA)
    except (HomeAssistantError, ValueError) as err:
        raise ToolError(f"Not saved: {rel} is not a valid blueprint: {err}") from err


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
        # Only the file name carries that suffix; a folder called x.corrupt.1 is a folder.
        head, _, name = rel.rpartition("/")
        name = name.split(".corrupt.", 1)[0]
        base = f"{head}/{name}" if head else name
        return any(
            path in SENSITIVE_NAMES
            or path.rsplit("/", 1)[-1] == "secrets.yaml"  # HA reads one per directory
            or path.startswith(SENSITIVE_PREFIXES)
            or path.endswith(SENSITIVE_SUFFIXES)
            for path in (rel, base)
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
        offset = num_arg(args, "offset", 0, 0, 10**9)
        limit = num_arg(args, "limit", 400, 1, 4000)
        found = await ctx.hass.async_add_executor_job(_read_lines, path, offset, limit)
        if found is None:
            raise ToolError(f"{rel} does not exist")
        chunk, total = found
        out: dict[str, Any] = {"path": rel, "total_lines": total, "offset": offset}
        if total is None:
            out["note"] = "File too big to count its lines"
        return ToolOutput({**out, "content": chunk})


MAX_SCAN_BYTES = 64 * 1024 * 1024


def _read_lines(path: Path, offset: int, limit: int) -> tuple[str, int | None] | None:
    """Lines offset..offset+limit, streamed so a huge log isn't loaded whole. The line
    count stops at MAX_SCAN_BYTES (then None). Blocking: run in an executor."""
    picked: list[str] = []
    size = scanned = count = 0
    try:
        with path.open(encoding="utf-8", errors="replace", newline=None) as handle:
            for count, line in enumerate(handle, 1):
                scanned += len(line)
                if offset < count <= offset + limit and size < MAX_READ_CHARS:
                    picked.append(line.rstrip("\n"))
                    size += len(line)
                elif count > offset + limit and scanned > MAX_SCAN_BYTES:
                    return "\n".join(picked)[:MAX_READ_CHARS], None
    except FileNotFoundError:
        return None
    return "\n".join(picked)[:MAX_READ_CHARS], count


class WriteFile(Tool):
    def __init__(self) -> None:
        super().__init__(
            "write_file",
            "Change a file in the config dir. Either give 'content' (whole new file) or "
            "'old'/'new' to replace one exact, unique snippet (preferred for small edits). "
            "YAML is checked before saving, blueprints (blueprints/<automation|script>/...) "
            "against HA's blueprint schema, and python_scripts/*.py for syntax. After "
            "editing YAML, run check_config before restarting.",
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
        await ctx.hass.async_add_executor_job(check_syntax, rel, new_text)
        return path, rel, old_text, new_text

    async def preview(self, ctx: ToolContext, args: dict[str, Any]) -> Preview:
        _path, rel, old_text, new_text = await self._plan(ctx, args)
        verb = "Edit" if old_text is not None else "Create"
        return Preview(f"{verb} {rel}", diff_text(old_text, new_text, rel))

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        async with FILE_LOCK:
            path, rel, old_text, new_text = await self._plan(ctx, args)
            snap = await ctx.snapshots.save(
                "file",
                f"Edit {rel}",
                {"path": rel, "content": old_text, "after": text_hash(new_text)},
            )
            await ctx.hass.async_add_executor_job(write_text, path, new_text)
        return ToolOutput({"ok": True, "path": rel}, f"Wrote {rel}", snapshot_id=snap)


TOOLS: list[Tool] = [ListFiles(), ReadFile(), WriteFile()]
