"""Undo snapshots, full backups before risky actions, and the audit log."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import secrets
import time
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DATA_DIR, SNAPSHOT_KEEP

_LOGGER = logging.getLogger(__name__)

AUDIT_MAX_BYTES = 2 * 1024 * 1024


class Snapshots:
    """Stores the previous version of anything the agent changes.

    Kinds:
      file      -> {"path": relative path, "content": str | None (None = did not exist)}
      lovelace  -> {"url_path": str | None, "config": dict | None}
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.root = Path(hass.config.path(DATA_DIR))
        self.dir = self.root / "snapshots"

    def _ensure_dirs(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)

    async def save(self, kind: str, label: str, data: dict[str, Any]) -> str:
        snap_id = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        record = {
            "id": snap_id,
            "kind": kind,
            "label": label,
            "time": time.time(),
            **data,
        }

        def _write() -> None:
            self._ensure_dirs()
            tmp = self.dir / f"{snap_id}.json.tmp"
            tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.dir / f"{snap_id}.json")
            files = sorted(self.dir.glob("*.json"))
            for old in files[:-SNAPSHOT_KEEP]:
                old.unlink(missing_ok=True)

        await self.hass.async_add_executor_job(_write)
        return snap_id

    async def load(self, snap_id: str) -> dict[str, Any] | None:
        if not snap_id or "/" in snap_id or ".." in snap_id:
            return None
        path = self.dir / f"{snap_id}.json"

        def _read() -> dict[str, Any] | None:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except OSError, ValueError:
                return None

        return await self.hass.async_add_executor_job(_read)

    async def list(self, limit: int = 20) -> list[dict[str, Any]]:
        def _list() -> list[dict[str, Any]]:
            if not self.dir.exists():
                return []
            out = []
            for path in sorted(self.dir.glob("*.json"), reverse=True)[:limit]:
                try:
                    rec = json.loads(path.read_text(encoding="utf-8"))
                except OSError, ValueError:
                    continue
                out.append(
                    {
                        "id": rec["id"],
                        "kind": rec["kind"],
                        "label": rec.get("label", ""),
                    }
                )
            return out

        return await self.hass.async_add_executor_job(_list)

    async def audit(self, entry: dict[str, Any]) -> None:
        line = json.dumps({"time": time.time(), **entry}, ensure_ascii=False, default=str)
        path = self.root / "audit.jsonl"

        def _append() -> None:
            self.root.mkdir(parents=True, exist_ok=True)
            try:
                if path.stat().st_size > AUDIT_MAX_BYTES:
                    os.replace(path, self.root / "audit.1.jsonl")
            except FileNotFoundError:
                pass
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

        try:
            await self.hass.async_add_executor_job(_append)
        except OSError as err:  # never let auditing break a tool call
            _LOGGER.warning("Could not write audit log: %s", err)


async def full_backup(hass: HomeAssistant, reason: str) -> str:
    """Create a full HA backup if the backup integration offers a service for it."""
    for service in ("create_automatic", "create"):
        if hass.services.has_service("backup", service):
            await hass.services.async_call("backup", service, {}, blocking=True)
            return f"Full backup created before: {reason}"
    if hass.services.has_service("hassio", "backup_full"):
        await hass.services.async_call(
            "hassio",
            "backup_full",
            {"name": f"LLM Agent: {reason}"[:60]},
            blocking=True,
        )
        return f"Full backup created before: {reason}"
    return "No backup service available; continued without a full backup"
