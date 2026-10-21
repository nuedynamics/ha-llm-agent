"""ChatGPT subscription adapter, checked against recorded-shape responses only.

Nothing here talks to OpenAI: the provider is experimental and never tried against a
real ChatGPT account in tests.
"""

from __future__ import annotations

import json

import pytest

from custom_components.llm_agent.providers import ProviderConfig, ProviderError, make_provider
from custom_components.llm_agent.providers.base import Done, TextDelta, ToolCall, ToolSpec, Usage
from custom_components.llm_agent.providers.chatgpt import to_responses_input

from .conftest import FakeResponse, FakeSession, sse

TOOLS = [ToolSpec("get_entities", "Get entities", {"type": "object", "properties": {}})]


async def _auth() -> tuple[str, str]:
    return "access-token", "acct-1"


def _conf(auth=_auth) -> ProviderConfig:
    return ProviderConfig(
        "c",
        "chatgpt",
        "ChatGPT",
        None,
        "https://chatgpt.invalid/backend-api/codex/",
        "gpt-5.5",
        auth=auth,
    )


async def _collect(session, messages=None, conf=None):
    provider = make_provider(session, conf or _conf())
    return [
        e
        async for e in provider.stream(
            model="gpt-5.5",
            system="sys",
            messages=messages or [{"role": "user", "content": "hi"}],
            tools=TOOLS,
            max_tokens=500,
        )
    ]


CALL = {
    "type": "function_call",
    "id": "fc_1",
    "call_id": "call_1",
    "name": "get_entities",
    "arguments": '{"domain": "light"}',
}
REASONING = {"type": "reasoning", "id": "rs_1", "summary": [], "encrypted_content": "enc"}
COMPLETED = {
    "type": "response.completed",
    "response": {
        "usage": {
            "input_tokens": 100,
            "input_tokens_details": {"cached_tokens": 30},
            "output_tokens": 12,
        }
    },
}


async def test_chatgpt_streams_text_calls_and_usage() -> None:
    events = [
        {"type": "response.created", "response": {}},
        {"type": "response.output_item.done", "item": REASONING},
        {"type": "response.output_text.delta", "delta": "Let me "},
        {"type": "response.output_text.delta", "delta": "look."},
        {
            "type": "response.output_item.done",
            "item": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Let me look."}],
            },
        },
        {"type": "response.output_item.done", "item": CALL},
        COMPLETED,
    ]
    session = FakeSession([FakeResponse(200, sse(events, named=True))])
    out = await _collect(session)
    assert [e.text for e in out if isinstance(e, TextDelta)] == ["Let me ", "look."]
    calls = [e for e in out if isinstance(e, ToolCall)]
    assert calls == [ToolCall("call_1", "get_entities", {"domain": "light"})]
    assert [e for e in out if isinstance(e, Usage)] == [Usage(70, 12, 30)]
    done = out[-1]
    assert isinstance(done, Done) and done.stop_reason == "tool_use"
    assert [i["type"] for i in done.raw["chatgpt"]] == ["reasoning", "message", "function_call"]

    req = session.requests[0]
    assert req["url"] == "https://chatgpt.invalid/backend-api/codex/responses"
    assert req["headers"]["authorization"] == "Bearer access-token"
    assert req["headers"]["chatgpt-account-id"] == "acct-1"
    body = req["json"]
    assert body["store"] is False and body["stream"] is True
    assert "max_output_tokens" not in body and "instructions" not in body
    assert body["include"] == ["reasoning.encrypted_content"]
    assert body["input"][0] == {
        "type": "message",
        "role": "developer",
        "content": [{"type": "input_text", "text": "sys"}],
    }
    assert body["tools"][0]["type"] == "function" and body["tools"][0]["name"] == "get_entities"


def test_history_replays_raw_items_and_converts_the_rest() -> None:
    img = {"media_type": "image/jpeg", "data": "AAA"}
    messages = [
        {"role": "user", "content": "look", "images": [img]},
        {"role": "assistant", "content": "x", "tool_calls": [], "raw": {"chatgpt": [REASONING]}},
        {
            "role": "assistant",
            "content": "Checking.",
            "tool_calls": [{"id": "toolu_1", "name": "get_entities", "args": {"a": 1}}],
            "raw": {"anthropic": [{"type": "text", "text": "ignored"}]},
        },
        {
            "role": "tool",
            "tool_call_id": "toolu_1",
            "name": "get_entities",
            "content": "[]",
            "images": [img],
        },
    ]
    out = to_responses_input("", messages)
    assert out[0]["content"][0] == {
        "type": "input_image",
        "image_url": "data:image/jpeg;base64,AAA",
    }
    assert out[1] == REASONING
    assert out[2]["role"] == "assistant"
    assert out[2]["content"] == [{"type": "output_text", "text": "Checking."}]
    assert out[3] == {
        "type": "function_call",
        "call_id": "toolu_1",
        "name": "get_entities",
        "arguments": json.dumps({"a": 1}),
    }
    assert out[4] == {"type": "function_call_output", "call_id": "toolu_1", "output": "[]"}
    assert out[5]["role"] == "user" and out[5]["content"][0]["type"] == "input_image"


async def test_cut_off_stream_never_runs_its_tool_calls() -> None:
    events = [{"type": "response.output_item.done", "item": CALL}]
    session = FakeSession([FakeResponse(200, sse(events))])
    with pytest.raises(ProviderError, match="stopped before"):
        await _collect(session)


async def test_failed_response_raises_its_message() -> None:
    events = [{"type": "response.failed", "response": {"error": {"message": "usage limit"}}}]
    session = FakeSession([FakeResponse(200, sse(events))])
    with pytest.raises(ProviderError, match="usage limit"):
        await _collect(session)


async def test_incomplete_response_marks_calls_truncated() -> None:
    events = [
        {"type": "response.output_item.done", "item": CALL},
        {
            "type": "response.incomplete",
            "response": {"incomplete_details": {"reason": "max_output_tokens"}, "usage": {}},
        },
    ]
    out = await _collect(FakeSession([FakeResponse(200, sse(events))]))
    calls = [e for e in out if isinstance(e, ToolCall)]
    assert calls[0].args == {"_truncated": True}
    assert out[-1].stop_reason == "max_tokens"


async def test_malformed_events_are_skipped() -> None:
    events = [
        "not json",
        "[1, 2]",
        {"type": "response.output_item.done", "item": "nope"},
        {"type": "response.output_item.done", "item": {"type": "web_search_call"}},
        {"type": "response.output_text.delta", "delta": 5},
        {"type": "response.completed", "response": {"usage": {"input_tokens": "many"}}},
    ]
    out = await _collect(FakeSession([FakeResponse(200, sse(events))]))
    assert [e for e in out if isinstance(e, Usage)] == [Usage()]
    assert out[-1] == Done("end_turn", raw=None)


async def test_not_signed_in_raises() -> None:
    with pytest.raises(ProviderError, match="not signed in"):
        await _collect(FakeSession([]), conf=_conf(auth=None))


async def test_a_filtered_reply_never_runs_its_tool_calls() -> None:
    events = [
        {"type": "response.output_item.done", "item": CALL},
        {
            "type": "response.incomplete",
            "response": {"incomplete_details": {"reason": "content_filter"}},
        },
    ]
    out = await _collect(FakeSession([FakeResponse(200, sse(events))]))
    assert not [e for e in out if isinstance(e, ToolCall)]
    assert out[-1].stop_reason == "refusal" and out[-1].raw is None


@pytest.mark.parametrize("item", [{"type": []}, {"type": "message", "content": 42}])
async def test_odd_output_items_are_skipped(item) -> None:
    events = [{"type": "response.output_item.done", "item": item}, COMPLETED]
    out = await _collect(FakeSession([FakeResponse(200, sse(events))]))
    assert out[-1].stop_reason == "end_turn"


async def test_a_refusal_explanation_is_shown() -> None:
    events = [{"type": "response.refusal.delta", "delta": "I can't help with that."}, COMPLETED]
    out = await _collect(FakeSession([FakeResponse(200, sse(events))]))
    assert "".join(e.text for e in out if isinstance(e, TextDelta)) == "I can't help with that."
    assert out[-1].stop_reason == "refusal"


async def test_malformed_output_items_are_not_kept_for_the_next_request() -> None:
    invalid = {"type": "message", "role": "assistant", "content": 42}
    bad_call = {"type": "function_call", "call_id": 7, "name": "get_entities", "arguments": "{}"}
    events = [
        {"type": "response.output_item.done", "item": invalid},
        {"type": "response.output_item.done", "item": bad_call},
        COMPLETED,
    ]
    out = await _collect(FakeSession([FakeResponse(200, sse(events))]))
    assert not [e for e in out if isinstance(e, ToolCall)]
    replay = to_responses_input("", [{"role": "assistant", "content": "", "raw": out[-1].raw}])
    assert invalid not in replay and bad_call not in replay
