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
    return set(part) == {"text"}


def _usage(meta: dict[str, Any]) -> Usage:
    cached = meta.get("cachedContentTokenCount", 0) or 0
    prompt = meta.get("promptTokenCount", 0) or 0
    # Thinking tokens bill as output. Input excludes cache reads, as for Anthropic.
    out = (meta.get("candidatesTokenCount", 0) or 0) + (meta.get("thoughtsTokenCount", 0) or 0)
    return Usage(input_tokens=max(0, prompt - cached), output_tokens=out, cache_read_tokens=cached)


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
                        msg = err.get("message") if isinstance(err, dict) else err
                        raise ProviderError(f"Gemini: {msg}")
                    if meta := payload.get("usageMetadata"):
                        usage = _usage(meta)  # cumulative; the last one counts
                    if (payload.get("promptFeedback") or {}).get("blockReason"):
                        stop_reason = "refusal"
                    for cand in (payload.get("candidates") or [])[:1]:
                        for part in (cand.get("content") or {}).get("parts") or []:
                            if not isinstance(part, dict):
                                continue
                            if "functionCall" in part:
                                fc = part["functionCall"] or {}
                                args = fc.get("args")
                                calls.append(
                                    ToolCall(
                                        fc.get("id") or f"{MADE_UP_ID}{uuid.uuid4().hex[:12]}",
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
                                parts[-1] = {"text": parts[-1]["text"] + (text or "")}
                            else:
                                parts.append(dict(part))
                        reason = cand.get("finishReason")
                        if reason == "MAX_TOKENS":
                            stop_reason = "max_tokens"
                        elif reason in _REFUSALS:
                            stop_reason = "refusal"
                        elif reason and stop_reason is None:
                            stop_reason = "tool_use" if calls else "end_turn"
        except aiohttp.ClientError as err:
            raise ProviderError(f"Gemini connection error: {err}") from err
        for call in calls:
            if stop_reason == "max_tokens":
                call.args = {"_truncated": True}
            yield call
        yield usage
        yield Done(stop_reason, raw={"gemini": parts} if parts else None)
