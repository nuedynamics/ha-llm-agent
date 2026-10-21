"""Conversation storage: a small index plus one HA Store file per conversation.

Writes are debounced, so a streaming turn costs one disk write, not hundreds.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import secrets
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, MAX_CONVERSATIONS, NOTES_MAX

VERSION = 1
SAVE_DELAY = 2
CACHE_SIZE = 5
SPEND_DAYS = 31  # daily spend totals kept for the cap and the settings page


class ConversationStore:
    def __init__(
        self, hass: HomeAssistant, busy: Callable[[str], bool] = lambda _id: False
    ) -> None:
        """`busy(conv_id)` tells the store a conversation is in use by a running turn; such
        conversations stay cached so everyone edits the same object."""
        self.hass = hass
        self._busy = busy
        self._index_store: Store[dict[str, Any]] = Store(hass, VERSION, f"{DOMAIN}.conversations")
        self._index: dict[str, dict[str, Any]] = {}
        self._cache: dict[str, dict[str, Any]] = {}
        self._stores: dict[str, Store[dict[str, Any]]] = {}
        # estimated spend per local day, "YYYY-MM-DD" -> USD
        self._spend: dict[str, float] = {}
        # user id -> {"provider_id", "model"}: each admin's default for new chats
        self._prefs: dict[str, dict[str, str]] = {}
        # Home notes: facts and rules the household wants every chat to know
        self._notes = ""
        self.cache_size = CACHE_SIZE
        self.max_chats = MAX_CONVERSATIONS

    async def async_load(self) -> None:
        data = await self._index_store.async_load() or {}
        self._index = data.get("conversations", {})
        self._spend = data.get("spend", {})
        self._prefs = data.get("prefs", {})
        notes = data.get("notes", "")
        self._notes = notes if isinstance(notes, str) else ""

    def user_default(self, user_id: str) -> dict[str, str] | None:
        return self._prefs.get(user_id)

    def set_user_default(self, user_id: str, provider_id: str | None, model: str) -> None:
        if provider_id:
            self._prefs[user_id] = {"provider_id": provider_id, "model": model}
        else:
            self._prefs.pop(user_id, None)
        self._save_index()

    @property
    def notes(self) -> str:
        return self._notes

    def set_notes(self, text: str) -> None:
        self._notes = text.strip()[:NOTES_MAX]
        self._save_index()

    def add_spend(self, day: str, cost: float) -> None:
        if cost <= 0:
            return
        self._spend[day] = round(self._spend.get(day, 0.0) + cost, 6)
        for old in sorted(self._spend)[:-SPEND_DAYS]:
            self._spend.pop(old)
        self._save_index()

    def spent(self, day: str) -> float:
        return self._spend.get(day, 0.0)

    def _conv_store(self, conv_id: str) -> Store[dict[str, Any]]:
        if conv_id not in self._stores:
            self._stores[conv_id] = Store(self.hass, VERSION, f"{DOMAIN}.conv.{conv_id}")
        return self._stores[conv_id]

    def _save_index(self) -> None:
        self._index_store.async_delay_save(
            lambda: {
                "conversations": self._index,
                "spend": self._spend,
                "prefs": self._prefs,
                "notes": self._notes,
            },
            SAVE_DELAY,
        )

    def list(self) -> list[dict[str, Any]]:
        return sorted(self._index.values(), key=lambda c: c.get("updated", 0), reverse=True)

    async def search(self, query: str, limit: int = 30) -> list[dict[str, Any]]:
        """Chats whose title or messages contain `query` (case-insensitive), newest first,
        each with a short snippet. Reads chats from disk one at a time without caching
        them, so memory stays flat."""
        needle = query.strip().lower()
        if not needle:
            return []
        found: list[dict[str, Any]] = []
        for summary in self.list():
            if len(found) >= limit:
                break
            conv_id = summary["id"]
            conv = self._cache.get(conv_id) or await self._conv_store(conv_id).async_load()
            snippet = _snippet(summary.get("title", ""), needle)
            for msg in (conv or {}).get("messages", []):
                if snippet or msg.get("role") not in ("user", "assistant"):
                    continue
                snippet = _snippet(str(msg.get("display") or msg.get("content") or ""), needle)
            if snippet:
                found.append({**summary, "snippet": snippet})
        return found

    async def get(self, conv_id: str) -> dict[str, Any] | None:
        if conv_id in self._cache:
            self._cache[conv_id] = self._cache.pop(conv_id)  # most recently used last
            return self._cache[conv_id]
        if conv_id not in self._index:
            return None
        data = await self._conv_store(conv_id).async_load()
        if data is None:
            return None
        if conv_id in self._cache:  # loaded concurrently; keep the first object
            return self._cache[conv_id]
        self._cache[conv_id] = data
        self._evict()
        return data

    def _evict(self) -> None:
        """Keep a few conversations in memory; the rest reload from disk on demand."""
        excess = len(self._cache) - self.cache_size
        for old in list(self._cache):
            if excess <= 0:
                break
            if not self._busy(old):
                self._cache.pop(old)
                excess -= 1

    async def create(self, provider_id: str, model: str, context: str) -> dict[str, Any]:
        conv_id = time.strftime("%Y%m%d%H%M%S") + secrets.token_hex(3)
        now = time.time()
        conv = {
            "id": conv_id,
            "title": "New chat",
            "created": now,
            "updated": now,
            "provider_id": provider_id,
            "model": model,
            "context": context,
            "messages": [],
            "usage": {
                "input": 0,
                "output": 0,
                "cache_read": 0,
                "cache_write": 0,
                "cost": 0.0,
            },
        }
        self._cache[conv_id] = conv
        self._evict()
        self._index[conv_id] = self._summary(conv)
        await self._prune()
        self.save(conv)
        return conv

    @staticmethod
    def _summary(conv: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": conv["id"],
            "title": conv["title"],
            "updated": conv["updated"],
            "model": conv["model"],
            "provider_id": conv["provider_id"],
            "cost": conv["usage"].get("cost"),
        }

    def save(self, conv: dict[str, Any]) -> None:
        """Save soon. Pictures are never written, even when a save lands mid-turn."""
        if conv.get("deleted"):  # a cancelled turn finishing after delete must not revive it
            return
        conv["updated"] = time.time()
        self._index[conv["id"]] = self._summary(conv)
        self._conv_store(conv["id"]).async_delay_save(lambda: _without_images(conv), SAVE_DELAY)
        self._save_index()

    async def rename(self, conv_id: str, title: str) -> None:
        conv = await self.get(conv_id)
        if conv is not None:
            conv["title"] = title[:120]
            self.save(conv)

    async def delete(self, conv_id: str) -> None:
        self._index.pop(conv_id, None)
        if (conv := self._cache.pop(conv_id, None)) is not None:
            conv["deleted"] = True
        await self._conv_store(conv_id).async_remove()
        self._stores.pop(conv_id, None)
        self._save_index()

    async def _prune(self) -> None:
        if len(self._index) <= self.max_chats:
            return
        for conv in self.list()[self.max_chats :]:
            if not self._busy(conv["id"]):
                await self.delete(conv["id"])

    async def delete_older_than(self, days: float) -> int:
        """Delete chats not updated in `days` days (running chats are kept). Returns the count."""
        cutoff = time.time() - days * 86400
        old = [c["id"] for c in self.list() if c.get("updated", 0) < cutoff]
        removed = 0
        for conv_id in old:
            if not self._busy(conv_id):
                await self.delete(conv_id)
                removed += 1
        return removed

    async def disk_usage(self) -> dict[str, int]:
        """Number of saved chats and the bytes their files take."""
        storage = Path(self.hass.config.path(".storage"))

        def _size() -> int:
            return sum(f.stat().st_size for f in storage.glob(f"{DOMAIN}.conv.*") if f.is_file())

        return {"chats": len(self._index), "bytes": await self.hass.async_add_executor_job(_size)}


def _snippet(text: str, needle: str, width: int = 60) -> str:
    at = text.lower().find(needle)
    if at < 0:
        return ""
    start = max(0, at - width)
    end = min(len(text), at + len(needle) + width)
    return (
        ("…" if start else "")
        + " ".join(text[start:end].split())
        + ("…" if end < len(text) else "")
    )


def _without_images(conv: dict[str, Any]) -> dict[str, Any]:
    """The conversation as stored: photos and snapshots are sent for one turn only."""
    if not any("images" in m for m in conv["messages"]):
        return conv
    messages = [
        {k: v for k, v in m.items() if k != "images"} if "images" in m else m
        for m in conv["messages"]
    ]
    return {**conv, "messages": messages}
