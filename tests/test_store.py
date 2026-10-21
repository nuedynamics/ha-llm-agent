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


async def test_old_chats_are_deleted_but_running_ones_kept(hass) -> None:
    import time

    from custom_components.llm_agent.store import ConversationStore

    running: set[str] = set()
    store = ConversationStore(hass, busy=lambda cid: cid in running)
    await store.async_load()
    old = await store.create("p1", "m", "")
    busy = await store.create("p1", "m", "")
    new = await store.create("p1", "m", "")
    for conv in (old, busy):
        store._index[conv["id"]]["updated"] = time.time() - 40 * 86400
    running.add(busy["id"])
    assert await store.delete_older_than(30) == 1
    ids = {c["id"] for c in store.list()}
    assert ids == {busy["id"], new["id"]}
    usage = await store.disk_usage()
    assert usage["chats"] == 2


async def test_spend_keeps_a_month_of_days(hass) -> None:
    from custom_components.llm_agent.store import ConversationStore

    store = ConversationStore(hass)
    await store.async_load()
    for day in range(1, 41):
        store.add_spend(f"2026-01-{day:02d}", 0.5)
    store.add_spend("2026-01-40", 0.25)
    store.add_spend("2026-01-40", 0)
    assert store.spent("2026-01-40") == 0.75
    assert store.spent("2026-01-01") == 0.0
    assert len(store._spend) == 31


async def test_flush_writes_pending_saves_and_deleted_chats_stay_deleted(
    hass: HomeAssistant,
) -> None:
    store = ConversationStore(hass)
    await store.async_load()
    store.set_notes("Saved just now.")
    conv = await store.create("p", "m", "ctx")
    await store.flush()
    fresh = ConversationStore(hass)
    await fresh.async_load()
    assert fresh.notes == "Saved just now."
    assert await fresh.get(conv["id"]) is not None
    await store.delete(conv["id"])
    assert await store.get(conv["id"]) is None
