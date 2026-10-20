"""Conversation search: titles and message text, from memory or disk, with snippets."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.llm_agent.store import ConversationStore


async def test_search_finds_titles_and_messages_with_snippets(hass: HomeAssistant) -> None:
    store = ConversationStore(hass)
    await store.async_load()
    a = await store.create("p1", "m", "")
    a["title"] = "Porch light schedule"
    a["messages"] = [{"role": "user", "content": "[t] hi", "display": "hi"}]
    store.save(a)
    b = await store.create("p1", "m", "")
    b["messages"] = [
        {"role": "user", "content": "[t] x", "display": "Why does the GARAGE door open at night?"},
        {"role": "tool", "content": "porch secret tool output"},
    ]
    store.save(b)
    store._cache.clear()  # force reads from the stores, not memory

    hits = await store.search("porch")
    assert [h["id"] for h in hits] == [a["id"]]  # tool output is not searched
    assert hits[0]["snippet"] == "Porch light schedule"
    hits = await store.search("garage")
    assert [h["id"] for h in hits] == [b["id"]] and "GARAGE door" in hits[0]["snippet"]
    assert await store.search("  ") == []
    assert not store._cache  # searching does not fill the memory cache
