"""OpenAI-compatible Chat Completions adapter (OpenAI, OpenRouter, Ollama, others)."""

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
    open_stream,
    parse_args,
)


def to_openai_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for msg in messages:
        role = msg["role"]
        if role == "user":
            out.append({"role": "user", "content": msg["content"]})
        elif role == "assistant":
            item: dict[str, Any] = {
                "role": "assistant",
                "content": msg.get("content") or None,
            }
            calls = msg.get("tool_calls") or []
            if calls:
                item["tool_calls"] = [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {
                            "name": c["name"],
                            "arguments": json.dumps(c["args"]),
                        },
                    }
                    for c in calls
                ]
            elif item["content"] is None:
                item["content"] = ""
            out.append(item)
        elif role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": msg["tool_call_id"],
                    "content": msg["content"],
                }
            )
    return out


class OpenAICompatProvider(Provider):
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
            "model": model,
            "messages": to_openai_messages(system, messages),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
        headers = {"content-type": "application/json"}
        if self.config.api_key:
            headers["authorization"] = f"Bearer {self.config.api_key}"
        if self.config.type == "openrouter":
            headers["x-title"] = "LLM Agent for Home Assistant"
            headers["http-referer"] = "https://github.com/nuedynamics/ha-llm-agent"
        url = self.config.base_url.rstrip("/") + "/chat/completions"

        usage = Usage()
        finish: str | None = None
        calls: dict[int, dict[str, Any]] = {}
        try:
            async with open_stream(self._session, url, body, headers, self.config.name) as resp:
                async for _event, data in iter_sse(resp):
                    if data.strip() == "[DONE]":
                        break
                    try:
                        payload = json.loads(data)
                    except ValueError:
                        continue
                    if "error" in payload:
                        err = payload["error"]
                        raise ProviderError(
                            f"{self.config.name}: {err.get('message') if isinstance(err, dict) else err}"
                        )
                    if u := payload.get("usage"):
                        details = u.get("prompt_tokens_details") or {}
                        cached = details.get("cached_tokens", 0) or 0
                        # Normalise to Anthropic semantics: input excludes cache reads.
                        usage.input_tokens = max(0, (u.get("prompt_tokens", 0) or 0) - cached)
                        usage.output_tokens = u.get("completion_tokens", 0) or 0
                        usage.cache_read_tokens = cached
                    for choice in payload.get("choices") or []:
                        delta = choice.get("delta") or {}
                        if text := delta.get("content"):
                            yield TextDelta(text)
                        for tc in delta.get("tool_calls") or []:
                            idx = tc.get("index", 0)
                            entry = calls.setdefault(idx, {"id": "", "name": "", "args": ""})
                            if tc.get("id"):
                                entry["id"] = tc["id"]
                            fn = tc.get("function") or {}
                            if fn.get("name"):
                                entry["name"] += fn["name"]
                            if fn.get("arguments"):
                                entry["args"] += fn["arguments"]
                        if choice.get("finish_reason"):
                            finish = choice["finish_reason"]
        except aiohttp.ClientError as err:
            raise ProviderError(f"{self.config.name} connection error: {err}") from err

        for idx in sorted(calls):
            entry = calls[idx]
            if not entry["name"]:
                continue
            yield ToolCall(entry["id"] or f"call_{idx}", entry["name"], parse_args(entry["args"]))
        yield usage
        yield Done(finish)
