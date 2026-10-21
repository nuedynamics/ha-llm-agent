"""Shared helpers for tools: YAML I/O, diffs, atomic writes."""

from __future__ import annotations

import asyncio
import contextlib
import difflib
import hashlib
import os
from pathlib import Path
import re
from typing import Any

from annotatedyaml.dumper import FastestAvailableSafeDumper
from homeassistant.util.file import write_utf8_file_atomic
import yaml

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


# One lock for every change to a config file (file edits, config items, undo), so two
# chats can't both read the old file and each write over the other's change.
FILE_LOCK = asyncio.Lock()


def text_hash(text: str | None) -> str | None:
    return None if text is None else hashlib.sha256(text.encode()).hexdigest()


class Tagged(str):
    """An HA tag kept as written (``!secret wifi``, ``!include x.yaml``): never resolved,
    so reading a file can't pull in another file, a secret or the environment, and
    saving writes the tag back unchanged."""

    tag: str
    raw: str

    def __new__(cls, tag: str, raw: str) -> Tagged:
        text = super().__new__(cls, f"{tag} {raw}")
        text.tag, text.raw = tag, raw
        return text


class InertLoader(yaml.SafeLoader):
    """SafeLoader that keeps HA's tags (scalars only) as Tagged values."""


def _tagged(loader: InertLoader, suffix: str, node: yaml.Node) -> Tagged:
    if not isinstance(node, yaml.ScalarNode):
        raise yaml.constructor.ConstructorError(
            None, None, f"!{suffix} on a list or map is not supported here", node.start_mark
        )
    return Tagged(f"!{suffix}", str(loader.construct_scalar(node)))


InertLoader.add_multi_constructor("!", _tagged)


def load_inert(text: str) -> Any:
    return yaml.load(text, Loader=InertLoader)


# HA's YAML tags. A config read as JSON shows them as "!secret wifi"; saving turns such
# strings back into tags, so a read-then-save round trip doesn't quote them.
_TAG_TEXT = re.compile(r"^(!(?:secret|env_var|input|include|include_dir_[a-z_]+))\s+(\S.*)$")


def retag(value: Any) -> Any:
    if isinstance(value, Tagged):
        return value
    if isinstance(value, str):
        m = _TAG_TEXT.match(value)
        return Tagged(m.group(1), m.group(2)) if m else value
    if isinstance(value, dict):
        return {k: retag(v) for k, v in value.items()}
    if isinstance(value, list):
        return [retag(v) for v in value]
    return value


class _Dumper(FastestAvailableSafeDumper):  # type: ignore[misc,valid-type]
    pass


_Dumper.add_representer(Tagged, lambda dumper, data: dumper.represent_scalar(data.tag, data.raw))


def to_yaml(value: Any) -> str:
    if value is None:
        return ""
    return yaml.dump(
        value, default_flow_style=False, allow_unicode=True, sort_keys=False, Dumper=_Dumper
    ).replace(": null\n", ":\n")


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
