"""Gemini adapter, checked against recorded-shape responses (no live service)."""

from __future__ import annotations

from custom_components.llm_agent.providers import ProviderConfig, make_provider
from custom_components.llm_agent.providers.base import Done, TextDelta, ToolCall, ToolSpec, Usage
from custom_components.llm_agent.providers.gemini import NO_SIGNATURE, to_gemini_contents
from custom_components.llm_agent.providers.models import merge_models, models_request, parse_models

from .conftest import FakeResponse, FakeSession, sse

TOOLS = [ToolSpec("get_entities", "Get entities", {"type": "object", "properties": {}})]


def _conf() -> ProviderConfig:
    return ProviderConfig("g", "gemini", "Gemini", "gkey", "https://gem.invalid/", "m")


async def _collect(session, messages=None, tools=TOOLS):
    provider = make_provider(session, _conf())
    return [
        e
        async for e in provider.stream(
            model="gemini-3-flash-preview",
            system="sys",
            messages=messages or [{"role": "user", "content": "hi"}],
            tools=tools,
            max_tokens=500,
        )
    ]


def _chunk(parts, finish=None, usage=None):
    cand = {"content": {"role": "model", "parts": parts}}
    if finish:
        cand["finishReason"] = finish
    out = {"candidates": [cand]}
    if usage:
        out["usageMetadata"] = usage
    return out


async def test_gemini_streams_text_calls_usage_and_keeps_signatures() -> None:
    events = [
        _chunk([{"text": "Let me "}]),
        _chunk([{"text": "look."}]),
        _chunk(
            [
                {"text": "thinking", "thought": True},
                {
                    "functionCall": {"name": "get_entities", "args": {"domain": "light"}},
                    "thoughtSignature": "sig1",
                },
            ],
            finish="STOP",
            usage={
                "promptTokenCount": 100,
                "cachedContentTokenCount": 40,
                "candidatesTokenCount": 20,
                "thoughtsTokenCount": 5,
            },
        ),
    ]
    session = FakeSession([FakeResponse(200, sse(events))])
    out = await _collect(session)
    assert "".join(e.text for e in out if isinstance(e, TextDelta)) == "Let me look."
    call = next(e for e in out if isinstance(e, ToolCall))
    assert call.name == "get_entities" and call.args == {"domain": "light"}
    assert call.id.startswith("gem_")
    usage = next(e for e in out if isinstance(e, Usage))
    assert (usage.input_tokens, usage.cache_read_tokens, usage.output_tokens) == (60, 40, 25)
    done = out[-1]
    assert isinstance(done, Done) and done.stop_reason == "tool_use"
    raw = done.raw["gemini"]
    assert raw[0] == {"text": "Let me look."}  # streamed text is joined
    assert raw[-1]["thoughtSignature"] == "sig1"

    req = session.requests[0]
    assert req["url"] == (
        "https://gem.invalid/v1beta/models/gemini-3-flash-preview:streamGenerateContent?alt=sse"
    )
    assert req["headers"]["x-goog-api-key"] == "gkey"
    body = req["json"]
    assert body["systemInstruction"] == {"parts": [{"text": "sys"}]}
    assert body["generationConfig"] == {"maxOutputTokens": 500}
    decl = body["tools"][0]["functionDeclarations"][0]
    assert decl["name"] == "get_entities" and "parametersJsonSchema" in decl


async def test_gemini_without_tools_sends_none_and_maps_stops() -> None:
    session = FakeSession(
        [
            FakeResponse(200, sse([_chunk([{"text": "cut"}], finish="MAX_TOKENS")])),
            FakeResponse(200, sse([_chunk([], finish="SAFETY")])),
            FakeResponse(200, sse([{"promptFeedback": {"blockReason": "SAFETY"}}])),
        ]
    )
    first = await _collect(session, tools=[])
    assert "tools" not in session.requests[0]["json"]
    assert first[-1].stop_reason == "max_tokens"
    assert (await _collect(session))[-1].stop_reason == "refusal"
    assert (await _collect(session))[-1].stop_reason == "refusal"


def test_gemini_history_replays_raw_merges_turns_and_answers_calls() -> None:
    img = {"media_type": "image/png", "data": "QUJD"}
    messages = [
        {"role": "user", "content": "what is this?", "images": [img]},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "c1", "name": "a", "args": {}}],
            "raw": {
                "gemini": [{"functionCall": {"id": "c1", "name": "a"}, "thoughtSignature": "s"}]
            },
        },
        {"role": "tool", "tool_call_id": "c1", "name": "a", "content": "ok", "images": [img]},
        # A call from another provider: no raw, so no real signature.
        {
            "role": "assistant",
            "content": "hm",
            "tool_calls": [{"id": "gem_x", "name": "b", "args": {"q": 1}}],
        },
        {"role": "tool", "tool_call_id": "gem_x", "name": "b", "content": "bad", "is_error": True},
        {"role": "user", "content": "thanks"},
    ]
    out = to_gemini_contents(messages)
    assert [c["role"] for c in out] == ["user", "model", "user", "model", "user"]
    assert out[0]["parts"][0] == {"inlineData": {"mimeType": "image/png", "data": "QUJD"}}
    assert out[1]["parts"][0]["thoughtSignature"] == "s"
    reply = out[2]["parts"][0]["functionResponse"]
    assert reply == {"name": "a", "response": {"output": "ok"}, "id": "c1"}
    assert "inlineData" in out[2]["parts"][1]
    assert out[3]["parts"][1]["thoughtSignature"] == NO_SIGNATURE
    last = out[4]["parts"]
    assert last[0]["functionResponse"] == {"name": "b", "response": {"error": "bad"}}
    assert last[1] == {"text": "thanks"}


def test_gemini_model_list() -> None:
    url, headers = models_request("gemini", "https://gem.invalid", "gkey")
    assert url.startswith("https://gem.invalid/v1beta/models") and headers == {
        "x-goog-api-key": "gkey"
    }
    body = {
        "models": [
            {
                "name": "models/gemini-3-flash-preview",
                "supportedGenerationMethods": ["generateContent"],
            },
            {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
            {"name": "models/gemini-new", "supportedGenerationMethods": ["generateContent"]},
        ]
    }
    ids = parse_models("gemini", body)
    assert ids == ["gemini-3-flash-preview", "gemini-new"]
    merged = merge_models("gemini", ids)
    assert merged[0]["label"] == "Gemini 3 Flash (preview)"


async def test_gemini_survives_malformed_chunks() -> None:
    events = [
        {"candidates": [None]},
        {"candidates": "x", "usageMetadata": {"promptTokenCount": "many"}},
        _chunk([{"functionCall": "oops"}, {"text": 5}, "junk"]),
        {"error": "plain"},
    ]
    session = FakeSession([FakeResponse(200, sse(events))])
    import pytest

    from custom_components.llm_agent.providers import ProviderError

    with pytest.raises(ProviderError, match="Gemini: the service returned an error"):
        await _collect(session)


async def test_gemini_never_acts_on_a_cut_off_stream() -> None:
    import pytest

    from custom_components.llm_agent.providers import ProviderError

    cut = [_chunk([{"functionCall": {"name": "get_entities", "args": {}}}])]  # no finishReason
    session = FakeSession([FakeResponse(200, sse(cut))])
    with pytest.raises(ProviderError, match="stopped before"):
        await _collect(session)
