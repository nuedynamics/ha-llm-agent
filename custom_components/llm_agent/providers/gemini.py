"""Google Gemini API adapter (native generateContent over SSE).

Unverified: written against Google's published API and tested with recorded
responses only, not against the live service.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
import json
from typing import Any
import uuid

import aiohttp

from .base import (
    Done,
    Provider,
    ProviderError,
    StreamEvent,
    TextDelta,
    ToolCall,
    ToolSpec,
    Usage,
    iter_sse,
    open_stream,
)

# Gemini 3 wants the thought signature of each function call sent back with it. Calls
# made by another provider (or dropped by compaction) have none; Google documents this
# value for that case.
NO_SIGNATURE = "skip_thought_signature_validator"

MADE_UP_ID = "gem_"  # prefix for ids we make up when Gemini gives a call none

_REFUSALS = frozenset(
    {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"}
)


def _inline(img: dict[str, str]) -> dict[str, Any]:
    return {"inlineData": {"mimeType": img["media_type"], "data": img["data"]}}


def _add(out: list[dict[str, Any]], role: str, parts: list[dict[str, Any]]) -> None:
    """Gemini wants user and model turns to alternate, so same-role turns are merged."""
    if out and out[-1]["role"] == role:
        out[-1]["parts"].extend(parts)
    else:
        out.append({"role": role, "parts": parts})


def to_gemini_contents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = msg["role"]
        if role == "user":
            parts = [_inline(img) for img in msg.get("images") or []]
            parts.append({"text": msg["content"] or " "})
            _add(out, "user", parts)
        elif role == "assistant":
            raw = (msg.get("raw") or {}).get("gemini")
            if raw:
                # Replay exactly what the API returned, thought signatures included.
                _add(out, "model", [dict(p) for p in raw])
                continue
            parts = []
            if msg.get("content"):
                parts.append({"text": msg["content"]})
            for call in msg.get("tool_calls") or []:
                parts.append(
                    {
                        "functionCall": {"name": call["name"], "args": call["args"]},
                        "thoughtSignature": NO_SIGNATURE,
                    }
                )
            _add(out, "model", parts or [{"text": " "}])
        elif role == "tool":
            key = "error" if msg.get("is_error") else "output"
            reply: dict[str, Any] = {
                "name": msg.get("name") or "tool",
                "response": {key: msg["content"]},
            }
            call_id = msg.get("tool_call_id") or ""
            if call_id and not call_id.startswith(MADE_UP_ID):
                reply["id"] = call_id  # the id Gemini gave the call
            parts = [{"functionResponse": reply}]
            parts += [_inline(img) for img in msg.get("images") or []]
            _add(out, "user", parts)
    return out


def _plain_text(part: dict[str, Any]) -> bool:
    return set(part) == {"text"} and isinstance(part["text"], str)


def _obj(value: Any) -> dict[str, Any]:
    """The value if it is a JSON object, else an empty one (malformed replies)."""
    return value if isinstance(value, dict) else {}


def _count(meta: dict[str, Any], key: str) -> int:
    value = meta.get(key)
    return value if isinstance(value, int) and value > 0 else 0


def _usage(meta: dict[str, Any]) -> Usage:
    cached = _count(meta, "cachedContentTokenCount")
    # Thinking tokens bill as output. Input excludes cache reads, as for Anthropic.
    out = _count(meta, "candidatesTokenCount") + _count(meta, "thoughtsTokenCount")
    return Usage(
        input_tokens=max(0, _count(meta, "promptTokenCount") - cached),
        output_tokens=out,
        cache_read_tokens=cached,
    )


class GeminiProvider(Provider):
    async def stream(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec],
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        body: dict[str, Any] = {
            "contents": to_gemini_contents(messages),
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            body["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "parametersJsonSchema": t.parameters or {"type": "object"},
                        }
                        for t in tools
                    ]
                }
            ]
        headers = {"x-goog-api-key": self.config.api_key or "", "content-type": "application/json"}
        name = model.removeprefix("models/")
        url = (
            f"{self.config.base_url.rstrip('/')}/v1beta/models/{name}:streamGenerateContent?alt=sse"
        )
        usage = Usage()
        stop_reason: str | None = None
        parts: list[dict[str, Any]] = []
        calls: list[ToolCall] = []
        finished = False
        try:
            async with open_stream(
                self._session,
                url,
                body,
                headers,
                "Gemini",
                self.config.timeout,
                self.config.retries,
            ) as resp:
                async for _event, data in iter_sse(resp):
                    try:
                        payload = json.loads(data)
                    except ValueError:
                        continue
                    if not isinstance(payload, dict):
                        continue
                    if err := payload.get("error"):
                        msg = _obj(err).get("message") or "the service returned an error"
                        raise ProviderError(f"Gemini: {str(msg)[:500]}")
                    if meta := _obj(payload.get("usageMetadata")):
                        usage = _usage(meta)  # cumulative; the last one counts
                    if _obj(payload.get("promptFeedback")).get("blockReason"):
                        stop_reason, finished = "refusal", True
                    candidates = payload.get("candidates")
                    for cand in (candidates if isinstance(candidates, list) else [])[:1]:
                        cand = _obj(cand)
                        found = _obj(cand.get("content")).get("parts")
                        for part in found if isinstance(found, list) else []:
                            if not isinstance(part, dict):
                                continue
                            if "functionCall" in part:
                                fc = _obj(part["functionCall"])
                                args = fc.get("args")
                                calls.append(
                                    ToolCall(
                                        str(fc.get("id") or f"{MADE_UP_ID}{uuid.uuid4().hex[:12]}"),
                                        str(fc.get("name", "")),
                                        args if isinstance(args, dict) else {},
                                    )
                                )
                                parts.append(dict(part))
                                continue
                            text = part.get("text")
                            if isinstance(text, str) and text and not part.get("thought"):
                                yield TextDelta(text)
                            if parts and _plain_text(part) and _plain_text(parts[-1]):
                                parts[-1] = {"text": parts[-1]["text"] + text}
                            else:
                                parts.append(dict(part))
                        reason = cand.get("finishReason")
                        if reason is not None and not isinstance(reason, str):
                            raise ProviderError("Gemini: the reply was not in the expected form.")
                        if reason:
                            finished = True
                        if reason == "MAX_TOKENS":
                            stop_reason = "max_tokens"
                        elif reason in _REFUSALS:
                            stop_reason = "refusal"
                        elif reason and stop_reason is None:
                            stop_reason = "tool_use" if calls else "end_turn"
        except aiohttp.ClientError as err:
            raise ProviderError(f"Gemini connection error: {err}") from err
        if calls and not finished:
            # The stream stopped without saying it was done: never act on a cut-off reply.
            raise ProviderError("Gemini: the reply stopped before it was complete. Try again.")
        for call in calls:
            if stop_reason == "max_tokens":
                call.args = {"_truncated": True}
            yield call
        yield usage
        yield Done(stop_reason, raw={"gemini": parts} if parts else None)
