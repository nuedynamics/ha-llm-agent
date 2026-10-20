"""Anthropic Messages API adapter (raw HTTP + SSE, prompt caching on)."""

from __future__ import annotations

from collections.abc import AsyncIterator
import json
from typing import Any

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
    parse_args,
    raise_for_status,
)

API_VERSION = "2023-06-01"
CACHE = {"type": "ephemeral"}


def to_anthropic_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert neutral messages to Anthropic content blocks.

    Consecutive tool results are merged into one user turn, as the API requires.
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = msg["role"]
        if role == "user":
            blocks: list[dict[str, Any]] = [{"type": "text", "text": msg["content"] or " "}]
            if out and out[-1]["role"] == "user":
                out[-1]["content"].extend(blocks)
            else:
                out.append({"role": "user", "content": blocks})
        elif role == "assistant":
            raw = msg.get("raw", {}).get("anthropic")
            if raw:
                # Replay exactly what the API returned (thinking blocks included).
                out.append({"role": "assistant", "content": [dict(b) for b in raw]})
                continue
            blocks = []
            if msg.get("content"):
                blocks.append({"type": "text", "text": msg["content"]})
            for call in msg.get("tool_calls") or []:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call["args"],
                    }
                )
            if not blocks:
                blocks.append({"type": "text", "text": " "})
            out.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": msg["tool_call_id"],
                "content": msg["content"],
            }
            if msg.get("is_error"):
                block["is_error"] = True
            if out and out[-1]["role"] == "user":
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
    # Cache everything up to the newest turn so follow-up requests reuse it.
    if out:
        last = out[-1]["content"][-1]
        last["cache_control"] = CACHE
    return out


class AnthropicProvider(Provider):
    async def stream(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec],
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        tool_defs = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
                "eager_input_streaming": True,
            }
            for t in tools
        ]
        if tool_defs:
            tool_defs[-1]["cache_control"] = CACHE
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": [{"type": "text", "text": system, "cache_control": CACHE}],
            "messages": to_anthropic_messages(messages),
            "stream": True,
        }
        if tool_defs:
            body["tools"] = tool_defs
        headers = {
            "x-api-key": self.config.api_key or "",
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }
        url = self.config.base_url.rstrip("/") + "/v1/messages"
        usage = Usage()
        stop_reason: str | None = None
        # index -> block being assembled; tool_use input arrives as partial JSON
        blocks: dict[int, dict[str, Any]] = {}
        partial: dict[int, str] = {}
        try:
            async with self._session.post(
                url,
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=None, sock_read=300),
            ) as resp:
                await raise_for_status(resp, "Anthropic")
                async for event, data in iter_sse(resp):
                    try:
                        payload = json.loads(data)
                    except ValueError:
                        continue
                    kind = payload.get("type", event)
                    if kind == "message_start":
                        u = payload.get("message", {}).get("usage", {})
                        usage.input_tokens = u.get("input_tokens", 0)
                        usage.cache_read_tokens = u.get("cache_read_input_tokens", 0) or 0
                        usage.cache_write_tokens = u.get("cache_creation_input_tokens", 0) or 0
                        usage.output_tokens = u.get("output_tokens", 0)
                    elif kind == "content_block_start":
                        idx = payload["index"]
                        blocks[idx] = dict(payload.get("content_block", {}))
                        if blocks[idx].get("type") == "tool_use":
                            partial[idx] = ""
                    elif kind == "content_block_delta":
                        idx = payload["index"]
                        delta = payload.get("delta", {})
                        block = blocks.get(idx)
                        dtype = delta.get("type")
                        if block is None:
                            continue
                        if dtype == "text_delta":
                            text = delta.get("text", "")
                            block["text"] = block.get("text", "") + text
                            yield TextDelta(text)
                        elif dtype == "input_json_delta":
                            partial[idx] = partial.get(idx, "") + delta.get("partial_json", "")
                        elif dtype == "thinking_delta":
                            block["thinking"] = block.get("thinking", "") + delta.get(
                                "thinking", ""
                            )
                        elif dtype == "signature_delta":
                            block["signature"] = block.get("signature", "") + delta.get(
                                "signature", ""
                            )
                        elif dtype == "citations_delta":
                            block.setdefault("citations", []).append(delta.get("citation"))
                    elif kind == "content_block_stop":
                        idx = payload.get("index")
                        block = blocks.get(idx)
                        if block is not None and block.get("type") == "tool_use":
                            block["input"] = parse_args(partial.pop(idx, ""))
                    elif kind == "message_delta":
                        stop_reason = payload.get("delta", {}).get("stop_reason") or stop_reason
                        out = payload.get("usage", {}).get("output_tokens")
                        if out is not None:
                            usage.output_tokens = out
                    elif kind == "error":
                        err = payload.get("error", {})
                        raise ProviderError(f"Anthropic: {err.get('message') or err}")
        except aiohttp.ClientError as err:
            raise ProviderError(f"Anthropic connection error: {err}") from err
        ordered = [blocks[i] for i in sorted(blocks)]
        for block in ordered:
            if block.get("type") == "tool_use":
                args = block.get("input") or {}
                if stop_reason == "max_tokens":
                    # Input was cut off; the agent answers it with an error result.
                    args = {"_truncated": True}
                yield ToolCall(block["id"], block["name"], args)
        yield usage
        yield Done(stop_reason, raw={"anthropic": ordered})
