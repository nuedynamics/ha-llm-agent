"""Shared helpers for tools: YAML I/O, diffs, atomic writes."""

from __future__ import annotations

import contextlib
import difflib
import os
from pathlib import Path
from typing import Any

from homeassistant.util.file import write_utf8_file_atomic
from homeassistant.util.yaml import dump

MAX_DIFF_CHARS = 12000


def diff_text(old: str | None, new: str | None, name: str) -> str:
    lines = difflib.unified_diff(
        (old or "").splitlines(keepends=True),
        (new or "").splitlines(keepends=True),
        fromfile=f"a/{name}",
        tofile=f"b/{name}",
        n=2,
    )
    text = "".join(lines)
    if len(text) > MAX_DIFF_CHARS:
        text = text[:MAX_DIFF_CHARS] + "\n… (diff truncated)\n"
    return text or "(no changes)"


def to_yaml(value: Any) -> str:
    return dump(value) if value is not None else ""


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_utf8_file_atomic(str(path), content)


def remove_file(path: Path) -> None:
    with contextlib.suppress(FileNotFoundError):
        os.remove(path)
