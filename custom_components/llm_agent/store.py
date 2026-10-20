"""Conversation storage: a small index plus one HA Store file per conversation.

Writes are debounced, so a streaming turn costs one disk write, not hundreds.
"""

from __future__ import annotations

import secrets
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, MAX_CONVERSATIONS

VERSION = 1
SAVE_DELAY = 2


class ConversationStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._index_store: Store[dict[str, Any]] = Store(hass, VERSION, f"{DOMAIN}.conversations")
        self._index: dict[str, dict[str, Any]] = {}
        self._cache: dict[str, dict[str, Any]] = {}
        self._stores: dict[str, Store[dict[str, Any]]] = {}

    async def async_load(self) -> None:
        data = await self._index_store.async_load() or {}
        self._index = data.get("conversations", {})

    def _conv_store(self, conv_id: str) -> Store[dict[str, Any]]:
        if conv_id not in self._stores:
            self._stores[conv_id] = Store(self.hass, VERSION, f"{DOMAIN}.conv.{conv_id}")
        return self._stores[conv_id]

    def _save_index(self) -> None:
        self._index_store.async_delay_save(lambda: {"conversations": self._index}, SAVE_DELAY)

    def list(self) -> list[dict[str, Any]]:
        return sorted(self._index.values(), key=lambda c: c.get("updated", 0), reverse=True)

    async def get(self, conv_id: str) -> dict[str, Any] | None:
        if conv_id in self._cache:
            return self._cache[conv_id]
        if conv_id not in self._index:
            return None
        data = await self._conv_store(conv_id).async_load()
        if data is None:
            return None
        self._cache[conv_id] = data
        # keep the in-memory cache small; conversations reload from disk on demand
        if len(self._cache) > 5:
            for old in list(self._cache)[:-5]:
                if old != conv_id:
                    self._cache.pop(old, None)
        return data

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
        conv["updated"] = time.time()
        self._index[conv["id"]] = self._summary(conv)
        self._conv_store(conv["id"]).async_delay_save(lambda: conv, SAVE_DELAY)
        self._save_index()

    async def rename(self, conv_id: str, title: str) -> None:
        conv = await self.get(conv_id)
        if conv is not None:
            conv["title"] = title[:120]
            self.save(conv)

    async def delete(self, conv_id: str) -> None:
        self._index.pop(conv_id, None)
        self._cache.pop(conv_id, None)
        await self._conv_store(conv_id).async_remove()
        self._stores.pop(conv_id, None)
        self._save_index()

    async def _prune(self) -> None:
        if len(self._index) <= MAX_CONVERSATIONS:
            return
        for conv in self.list()[MAX_CONVERSATIONS:]:
            await self.delete(conv["id"])
