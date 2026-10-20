"""Streaming adapters: SSE parsing, tool calls, usage and history conversion."""

from __future__ import annotations

import pytest

from custom_components.llm_agent.providers import ProviderConfig, ProviderError, base, make_provider
from custom_components.llm_agent.providers.anthropic import to_anthropic_messages
from custom_components.llm_agent.providers.base import Done, TextDelta, ToolCall, ToolSpec, Usage

from .conftest import FakeResponse, FakeSession, sse

TOOLS = [ToolSpec("get_entities", "Get entities", {"type": "object", "properties": {}})]


def _conf(kind: str) -> ProviderConfig:
    return ProviderConfig("p", kind, "x", "key", "http://stub.invalid", "m")


async def _collect(provider, messages=None):
    return [
        e
        async for e in provider.stream(
            model="m",
            system="sys",
            messages=messages or [{"role": "user", "content": "hi"}],
            tools=TOOLS,
        )
    ]


async def test_openai_stream_text_tool_and_usage() -> None:
    chunks = [
        {"choices": [{"delta": {"content": "Hel"}}]},
        {"choices": [{"delta": {"content": "lo"}}]},
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "c1",
                                "function": {"name": "get_entities", "arguments": '{"ids":'},
                            }
                        ]
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [{"index": 0, "function": {"arguments": ' ["light.a"]}'}}]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
        {
            "choices": [],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "prompt_tokens_details": {"cached_tokens": 40},
            },
        },
        "[DONE]",
    ]
    session = FakeSession([FakeResponse(200, sse(chunks))])
    events = await _collect(make_provider(session, _conf("openai")))
    text = "".join(e.text for e in events if isinstance(e, TextDelta))
    calls = [e for e in events if isinstance(e, ToolCall)]
    usage = next(e for e in events if isinstance(e, Usage))
    assert text == "Hello"
    assert calls[0].id == "c1" and calls[0].args == {"ids": ["light.a"]}
    assert (usage.input_tokens, usage.cache_read_tokens, usage.output_tokens) == (60, 40, 20)
    assert isinstance(events[-1], Done)
    body = session.requests[0]["json"]
    assert body["stream"] is True and body["tools"][0]["function"]["name"] == "get_entities"
    assert session.requests[0]["headers"]["authorization"] == "Bearer key"


async def test_anthropic_stream_preserves_raw_blocks() -> None:
    events = [
        {
            "type": "message_start",
            "message": {
                "usage": {"input_tokens": 10, "cache_read_input_tokens": 5, "output_tokens": 1}
            },
        },
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "thinking", "thinking": ""},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "thinking_delta", "thinking": "hmm"},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "signature_delta", "signature": "sig"},
        },
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
        {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "text_delta", "text": "On it"},
        },
        {"type": "content_block_stop", "index": 1},
        {
            "type": "content_block_start",
            "index": 2,
            "content_block": {"type": "tool_use", "id": "t1", "name": "get_entities", "input": {}},
        },
        {
            "type": "content_block_delta",
            "index": 2,
            "delta": {"type": "input_json_delta", "partial_json": '{"ids": ["a"]}'},
        },
        {"type": "content_block_stop", "index": 2},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "tool_use"},
            "usage": {"output_tokens": 30},
        },
        {"type": "message_stop"},
    ]
    session = FakeSession([FakeResponse(200, sse(events, named=True))])
    out = await _collect(make_provider(session, _conf("anthropic")))
    call = next(e for e in out if isinstance(e, ToolCall))
    done = out[-1]
    assert call.args == {"ids": ["a"]}
    assert isinstance(done, Done) and done.stop_reason == "tool_use"
    blocks = done.raw["anthropic"]
    assert [b["type"] for b in blocks] == ["thinking", "text", "tool_use"]
    assert blocks[0]["signature"] == "sig"
    usage = next(e for e in out if isinstance(e, Usage))
    assert (usage.input_tokens, usage.cache_read_tokens, usage.output_tokens) == (10, 5, 30)
    req = session.requests[0]
    assert req["url"] == "http://stub.invalid/v1/messages"
    assert req["json"]["tools"][-1]["cache_control"]["type"] == "ephemeral"


async def test_anthropic_truncated_tool_input_is_flagged() -> None:
    events = [
        {"type": "message_start", "message": {"usage": {}}},
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "tool_use", "id": "t1", "name": "get_entities", "input": {}},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "input_json_delta", "partial_json": '{"ids": ['},
        },
        {"type": "content_block_stop", "index": 0},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "max_tokens"},
            "usage": {"output_tokens": 5},
        },
    ]
    session = FakeSession([FakeResponse(200, sse(events))])
    out = await _collect(make_provider(session, _conf("anthropic")))
    call = next(e for e in out if isinstance(e, ToolCall))
    assert call.args.get("_truncated") or "_invalid_json" in call.args


async def test_http_error_raises_provider_error() -> None:
    session = FakeSession([FakeResponse(401, [], '{"error": {"message": "bad key"}}')])
    with pytest.raises(ProviderError, match=r"API key was rejected.*bad key"):
        await _collect(make_provider(session, _conf("openai")))
    assert len(session.requests) == 1


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []

    async def fake_sleep(delay: float) -> None:
        slept.append(delay)

    monkeypatch.setattr(base.asyncio, "sleep", fake_sleep)
    return slept


@pytest.mark.parametrize("kind", ["openai", "anthropic"])
async def test_transient_errors_are_retried_before_streaming(
    kind: str, no_sleep: list[float]
) -> None:
    ok = (
        sse([{"choices": [{"delta": {"content": "hello"}}]}, "[DONE]"])
        if kind == "openai"
        else sse(
            [
                {"type": "message_start", "message": {"usage": {}}},
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": "hello"},
                },
                {"type": "content_block_stop", "index": 0},
                {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {}},
            ]
        )
    )
    busy = FakeResponse(429, [], "slow down", headers={"retry-after": "120"})
    overloaded = FakeResponse(529, [], "overloaded")
    session = FakeSession([busy, overloaded, FakeResponse(200, ok)])
    out = await _collect(make_provider(session, _conf(kind)))
    assert "".join(e.text for e in out if isinstance(e, TextDelta)) == "hello"
    assert len(session.requests) == 3
    # retry-after is honoured but capped; otherwise the fixed backoff applies.
    assert no_sleep == [base.MAX_RETRY_AFTER, base.RETRY_DELAYS[1]]
    assert busy.released and overloaded.released


async def test_retries_give_up_with_a_clear_error(no_sleep: list[float]) -> None:
    session = FakeSession([FakeResponse(503, [], "down") for _ in range(4)])
    with pytest.raises(ProviderError, match="server error"):
        await _collect(make_provider(session, _conf("openai")))
    assert len(session.requests) == 4


def test_anthropic_history_replays_raw_and_merges_tool_results() -> None:
    raw = [
        {"type": "thinking", "thinking": "x", "signature": "s"},
        {"type": "tool_use", "id": "t1", "name": "n", "input": {}},
    ]
    msgs = to_anthropic_messages(
        [
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "t1", "name": "n", "args": {}}],
                "raw": {"anthropic": raw},
            },
            {"role": "tool", "tool_call_id": "t1", "name": "n", "content": "ok"},
        ]
    )
    assert msgs[1]["content"] == raw
    assert msgs[2]["role"] == "user" and msgs[2]["content"][0]["type"] == "tool_result"


def test_tool_call_written_as_text_is_recovered() -> None:
    from custom_components.llm_agent.providers.base import ToolSpec
    from custom_components.llm_agent.providers.openai_compat import text_tool_call

    tools = [ToolSpec("call_service", "", {"type": "object", "properties": {}})]
    text = 'Let me do that. {"name": "call_service", "parameters": {"domain": "light"}} ok'
    call = text_tool_call(text, tools)
    assert call is not None and call.name == "call_service" and call.args == {"domain": "light"}
    assert text_tool_call('{"name": "rm_rf", "parameters": {}}', tools) is None  # unknown tool
    assert text_tool_call("Here is some YAML: {a: 1}", tools) is None
