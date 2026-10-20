"""The agent loop: tool execution, approvals, limits and cancellation."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.llm_agent.agent import Agent, ChatRun
from custom_components.llm_agent.providers.base import Done, TextDelta, ToolCall, Usage

from .conftest import entry_options


class ScriptedProvider:
    """Returns one scripted reply per model call and records what it was sent."""

    def __init__(self, replies: list[list[Any]]) -> None:
        self.replies = replies
        self.calls: list[dict[str, Any]] = []

    async def stream(self, **kwargs: Any):
        self.calls.append(kwargs)
        for event in self.replies.pop(0):
            yield event


def reply_text(text: str) -> list[Any]:
    return [TextDelta(text), Usage(100, 10), Done("end_turn")]


def reply_tool(call_id: str, name: str, args: dict[str, Any]) -> list[Any]:
    return [ToolCall(call_id, name, args), Usage(200, 20), Done("tool_use")]


async def _run(hass: HomeAssistant, provider: ScriptedProvider, text: str, on_event=None, **opts):
    agent = Agent(hass, entry_options(**opts))
    await agent.store.async_load()
    conv = await agent.store.create("p1", "gpt-5.4-mini", "ctx")
    run = ChatRun(agent, conv, None)
    events: list[dict[str, Any]] = []

    def listener(event: dict[str, Any]) -> None:
        events.append(event)
        if on_event:
            on_event(run, event)

    run.listeners.add(listener)
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await run.run(text)
    return conv, events


async def test_turn_runs_tool_and_records_usage(hass: HomeAssistant) -> None:
    calls: list[ServiceCall] = async_mock_service(hass, "light", "turn_on")
    hass.states.async_set("light.kitchen", "off")
    provider = ScriptedProvider(
        [
            reply_tool(
                "c1",
                "call_service",
                {"domain": "light", "service": "turn_on", "target": {"entity_id": "light.kitchen"}},
            ),
            reply_text("Done, the kitchen light is on."),
        ]
    )
    conv, events = await _run(hass, provider, "turn on the kitchen light")
    assert len(calls) == 1
    roles = [m["role"] for m in conv["messages"]]
    assert roles == ["user", "assistant", "tool", "assistant"]
    assert conv["messages"][2]["is_error"] is False
    assert conv["title"] == "turn on the kitchen light"
    assert conv["usage"]["input"] == 300 and conv["usage"]["output"] == 30
    assert conv["usage"]["cost"] is not None and conv["usage"]["cost"] > 0
    assert events[-1]["type"] == "done"
    # second model call received the tool result
    assert provider.calls[1]["messages"][-1]["role"] == "tool"
    # the user message carries the time, the system prompt does not
    assert provider.calls[0]["messages"][0]["content"].startswith("[")


async def test_risky_call_waits_for_approval_and_denial_is_reported(hass: HomeAssistant) -> None:
    calls = async_mock_service(hass, "lock", "unlock")
    hass.states.async_set("lock.front", "locked")
    provider = ScriptedProvider(
        [
            reply_tool(
                "c1",
                "call_service",
                {"domain": "lock", "service": "unlock", "target": {"entity_id": "lock.front"}},
            ),
            reply_text("OK, I left it locked."),
        ]
    )

    def deny(run: ChatRun, event: dict[str, Any]) -> None:
        if event["type"] == "approval":
            asyncio.get_running_loop().call_soon(run.answer, event["call_id"], False, "not now")

    conv, events = await _run(hass, provider, "unlock the door", on_event=deny)
    assert not calls
    assert any(e["type"] == "approval" and e["risky"] for e in events)
    tool_msg = conv["messages"][2]
    assert (
        tool_msg["is_error"]
        and "denied" in tool_msg["content"]
        and "not now" in tool_msg["content"]
    )


async def test_approved_call_runs(hass: HomeAssistant) -> None:
    calls = async_mock_service(hass, "lock", "unlock")
    hass.states.async_set("lock.front", "locked")
    provider = ScriptedProvider(
        [
            reply_tool(
                "c1",
                "call_service",
                {"domain": "lock", "service": "unlock", "target": {"entity_id": "lock.front"}},
            ),
            reply_text("Unlocked."),
        ]
    )

    def approve(run: ChatRun, event: dict[str, Any]) -> None:
        if event["type"] == "approval":
            asyncio.get_running_loop().call_soon(run.answer, event["call_id"], True, "")

    conv, _ = await _run(hass, provider, "unlock the door", on_event=approve)
    assert len(calls) == 1
    assert conv["messages"][2]["decision"] == "approved"


async def test_autopilot_skips_approval(hass: HomeAssistant) -> None:
    calls = async_mock_service(hass, "lock", "unlock")
    hass.states.async_set("lock.front", "locked")
    provider = ScriptedProvider(
        [
            reply_tool(
                "c1",
                "call_service",
                {"domain": "lock", "service": "unlock", "target": {"entity_id": "lock.front"}},
            ),
            reply_text("Unlocked."),
        ]
    )
    _, events = await _run(hass, provider, "unlock", approval_mode="autopilot")
    assert len(calls) == 1
    assert not any(e["type"] == "approval" for e in events)


async def test_unknown_tool_and_bad_args_return_errors(hass: HomeAssistant) -> None:
    provider = ScriptedProvider(
        [
            [
                ToolCall("a", "get_entity", {}),
                ToolCall("b", "get_entities", {"_invalid_json": "{"}),
                Done("tool_use"),
            ],
            reply_text("Sorry."),
        ]
    )
    conv, _ = await _run(hass, provider, "x")
    tool_msgs = [m for m in conv["messages"] if m["role"] == "tool"]
    assert [m["is_error"] for m in tool_msgs] == [True, True]
    assert "Unknown tool get_entity. Did you mean get_entities?" in tool_msgs[0]["content"]


async def test_step_limit_stops_the_loop(hass: HomeAssistant) -> None:
    hass.states.async_set("light.a", "on")
    replies = [reply_tool(f"c{i}", "get_entities", {"entity_ids": ["light.a"]}) for i in range(20)]
    provider = ScriptedProvider(replies)
    conv, events = await _run(hass, provider, "loop", max_steps=2)
    tool_msgs = [m for m in conv["messages"] if m["role"] == "tool"]
    assert tool_msgs[0]["is_error"] is False
    assert any("limit" in m["content"] for m in tool_msgs)
    assert len(provider.calls) < 20
    assert events[-1]["type"] == "done"
    # The panel learns why the turn stopped, so it can offer to continue.
    assert conv["stopped"] == "tool_limit"
    assert any(e.get("stop") == "tool_limit" for e in events)


async def test_cancel_fills_missing_tool_results(hass: HomeAssistant) -> None:
    provider = ScriptedProvider(
        [
            reply_tool(
                "c1",
                "call_service",
                {"domain": "lock", "service": "unlock", "target": {"entity_id": "lock.front"}},
            )
        ]
    )
    agent = Agent(hass, entry_options())
    await agent.store.async_load()
    conv = await agent.store.create("p1", "m", "ctx")
    run = ChatRun(agent, conv, None)
    seen = asyncio.Event()
    run.listeners.add(lambda e: seen.set() if e["type"] == "approval" else None)
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        task = asyncio.ensure_future(run.run("unlock"))
        await seen.wait()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    assert conv["messages"][-1]["role"] == "tool"
    assert conv["messages"][-1]["tool_call_id"] == "c1"
    assert conv["messages"][-1]["is_error"]
    assert conv["stopped"] == "cancelled"


async def test_cut_off_reply_is_reported_and_cleared_by_the_next_message(hass) -> None:
    provider = ScriptedProvider([[TextDelta("Half a"), Done("max_tokens")], reply_text("Rest.")])
    agent = Agent(hass, entry_options())
    await agent.store.async_load()
    conv = await agent.store.create("p1", "m", "ctx")
    events: list[dict[str, Any]] = []
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        run = ChatRun(agent, conv, None)
        run.listeners.add(events.append)
        await run.run("write a lot")
        assert conv["stopped"] == "length"
        assert any(e.get("stop") == "length" and "cut off" in e["text"] for e in events)
        await ChatRun(agent, conv, None).run("Continue.")
    assert "stopped" not in conv


def test_rewind_drops_last_turn_and_reports_actions() -> None:
    from custom_components.llm_agent.agent import rewind_last_turn

    conv = {
        "messages": [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "turn on the lamp"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1"}]},
            {"role": "tool", "name": "call_service", "summary": "Called light.turn_on"},
            {"role": "tool", "name": "get_state", "summary": "x", "is_error": True},
            {"role": "assistant", "content": "Done"},
        ]
    }
    note = rewind_last_turn(conv)
    assert [m["content"] for m in conv["messages"]] == ["first", "ok"]
    assert "Called light.turn_on" in note and "get_state" not in note
    # nothing done in the dropped turn -> no note
    assert rewind_last_turn(conv) == ""
    assert conv["messages"] == []


def test_compaction_is_rare_batched_and_keeps_recent_turns(monkeypatch) -> None:
    from custom_components.llm_agent import agent as agent_mod

    keep = agent_mod.KEEP_TURNS
    big = "y" * 8_000  # ~2k tokens per tool result, ~4k per turn

    def turn(n: int) -> list[dict]:
        return [
            {"role": "user", "content": f"q{n}"},
            {
                "role": "assistant",
                "content": "",
                "raw": {"anthropic": [{"type": "thinking"}]},
                "tool_calls": [{"id": f"c{n}", "name": "write_file", "args": {"new": big}}],
            },
            {"role": "tool", "tool_call_id": f"c{n}", "name": "write_file", "content": big},
            {"role": "assistant", "content": f"a{n}"},
        ]

    conv: dict = {"messages": []}
    # Below the token threshold nothing is touched, however many turns there are.
    for n in range(keep + 1):
        conv["messages"] += turn(n)
    assert not agent_mod.compact_history(conv)

    while agent_mod._history_chars(conv["messages"]) < (
        agent_mod.COMPACT_AT_TOKENS * agent_mod.CHARS_PER_TOKEN
    ):
        conv["messages"] += turn(len(conv["messages"]))
    assert agent_mod.compact_history(conv)
    msgs = conv["messages"]
    old, recent = msgs[: -4 * keep], msgs[-4 * keep :]
    assert all(len(m["content"]) < 500 for m in old if m["role"] == "tool")
    assert not any("raw" in m for m in old)
    assert all(m["content"] == big for m in recent if m["role"] == "tool")  # last turns intact
    assert all(
        m["content"].startswith("a") for m in old if m["role"] == "assistant" and m["content"]
    )

    # Compaction shrinks the history, so it stays under the threshold for a long while.
    assert agent_mod._history_chars(msgs) < agent_mod.COMPACT_AT_TOKENS * agent_mod.CHARS_PER_TOKEN

    # Even when a chat stays over the threshold, the prefix stays stable (the cache keeps
    # hitting) until KEEP_TURNS more turns have passed.
    monkeypatch.setattr(agent_mod, "COMPACT_AT_TOKENS", 1)
    for n in range(keep - 1):
        conv["messages"] += turn(1000 + n)
        snapshot = [dict(m) for m in conv["messages"]]
        assert not agent_mod.compact_history(conv)
        assert conv["messages"] == snapshot
    conv["messages"] += turn(2000)
    assert agent_mod.compact_history(conv)  # next batch


async def test_unexpected_error_is_reported_not_swallowed(hass, caplog) -> None:
    from custom_components.llm_agent.agent import Agent, ChatRun

    from .conftest import entry_options

    class Broken:
        async def stream(self, **_kw):
            raise RuntimeError("boom")
            yield  # pragma: no cover

    agent = Agent(hass, entry_options())
    await agent.store.async_load()
    conv = await agent.store.create("p1", "m", "")
    run = ChatRun(agent, conv, "user")
    events: list[dict] = []
    run.listeners.add(events.append)
    with patch("custom_components.llm_agent.agent.make_provider", return_value=Broken()):
        await run.run("hi")
    errors = [e for e in events if e["type"] == "error"]
    assert errors and "RuntimeError: boom" in errors[0]["message"]
    assert events[-1]["type"] == "done"
    assert "Unexpected error" in caplog.text
