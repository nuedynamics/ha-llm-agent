"""OpenAI-compatible Chat Completions adapter (OpenAI, OpenRouter, Ollama, others)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from difflib import get_close_matches
import json
import logging
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

_LOGGER = logging.getLogger(__name__)


def _data_url(img: dict[str, str]) -> str:
    return f"data:{img['media_type']};base64,{img['data']}"


def to_openai_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    pending: list[dict[str, str]] = []

    def flush() -> None:
        if pending:
            parts: list[dict[str, Any]] = [
                {"type": "text", "text": "Pictures from the tool results above:"}
            ]
            parts += [
                {
                    "type": "image_url",
                    "image_url": {"url": _data_url(i)},
                }
                for i in pending
            ]
            out.append({"role": "user", "content": parts})
            pending.clear()

    for msg in messages:
        role = msg["role"]
        if role != "tool":
            flush()
        if role == "user":
            if msg.get("images"):
                out.append(
                    {
                        "role": "user",
                        "content": [
                            *(
                                {"type": "image_url", "image_url": {"url": _data_url(i)}}
                                for i in msg["images"]
                            ),
                            {"type": "text", "text": msg["content"]},
                        ],
                    }
                )
            else:
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
            # Chat Completions tool messages are text only, so pictures follow the
            # tool results as a user message.
            pending.extend(msg.get("images") or [])
    flush()
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
        # OpenAI's newer models take only max_completion_tokens; the compatible servers
        # (Ollama, OpenRouter) read max_tokens.
        body["max_completion_tokens" if self.config.type == "openai" else "max_tokens"] = max_tokens
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
        text_parts: list[str] = []
        ended = False
        try:
            async with open_stream(
                self._session,
                url,
                body,
                headers,
                self.config.name,
                self.config.timeout,
                self.config.retries,
            ) as resp:
                async for _event, data in iter_sse(resp):
                    if data.strip() == "[DONE]":
                        ended = True
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
                            text_parts.append(text)
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

        if not ended and finish is None:
            # the connection closed mid-reply; never act on half a reply
            raise ProviderError(f"{self.config.name}: the reply ended early. Try again.")
        if finish == "content_filter":
            yield usage
            yield Done("refusal")
            return
        named = [calls[i] for i in sorted(calls) if calls[i]["name"]]
        for idx, entry in enumerate(named):
            args = parse_args(entry["args"])
            if finish == "length":
                args = {"_truncated": True}  # cut off; the agent answers with an error
            yield ToolCall(entry["id"] or f"call_{idx}", entry["name"], args)
        if (
            not named
            and tools
            and finish != "length"
            and (call := text_tool_call("".join(text_parts), tools))
        ):
            _LOGGER.debug("%s: recovered a tool call written as text", self.config.name)
            yield call
            finish = "tool_calls"
        yield usage
        yield Done(finish)


def text_tool_call(text: str, tools: list[ToolSpec]) -> ToolCall | None:
    """Some local models (Llama 3.1 on Ollama, for one) sometimes write a tool call as JSON
    instead of making it. Recover {"name": <known tool>, "parameters": {...}}, but only
    when that JSON is the whole reply: JSON inside an explanation is an example."""
    if len(text) > 20_000:
        return None
    body = text.strip()
    if body.startswith("<|python_tag|>"):
        body = body[len("<|python_tag|>") :].strip()
    if body.startswith("```") and body.endswith("```"):
        body = body[3:-3].strip()
        if body[:4].lower() == "json":
            body = body[4:].strip()
    if not body.startswith("{"):
        return None
    try:
        obj, end = json.JSONDecoder().raw_decode(body)
    except ValueError:
        return None
    if body[end:].strip() or not isinstance(obj, dict):
        return None
    names = {t.name for t in tools}
    name = obj.get("name")
    if isinstance(name, str) and name not in names:
        # A near miss such as get_entity for get_entities.
        close = get_close_matches(name, names, n=1, cutoff=0.8)
        name = close[0] if close else None
    if not name:
        return None
    args = obj.get("parameters", obj.get("arguments", {}))
    if isinstance(args, str):
        args = parse_args(args)
    return ToolCall("text_call_0", name, args) if isinstance(args, dict) else None
