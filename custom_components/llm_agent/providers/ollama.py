"""Ollama adapter on Ollama's own chat API (/api/chat).

The OpenAI-compatible endpoint ignores keep_alive and num_ctx and lets thinking models
think. On local hardware that costs minutes per reply: the model unloads after every
request (when the server keeps nothing loaded), its context size is picked per request
(a different size reloads it), and hidden thinking comes before every step. The native
API takes all three per request.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
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
    open_stream,
    parse_args,
)
from .openai_compat import text_tool_call

_LOGGER = logging.getLogger(__name__)


def native_base(base_url: str) -> str:
    """The server address without the OpenAI-compatible /v1 suffix."""
    base = base_url.rstrip("/")
    return base.removesuffix("/v1")


def to_ollama_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    pending: list[str] = []

    def flush() -> None:
        if pending:
            out.append(
                {
                    "role": "user",
                    "content": "Pictures from the tool results above:",
                    "images": list(pending),
                }
            )
            pending.clear()

    for msg in messages:
        role = msg["role"]
        if role != "tool":
            flush()
        if role == "user":
            item: dict[str, Any] = {"role": "user", "content": msg["content"]}
            if msg.get("images"):
                item["images"] = [i["data"] for i in msg["images"]]
            out.append(item)
        elif role == "assistant":
            item = {"role": "assistant", "content": msg.get("content") or ""}
            if calls := msg.get("tool_calls") or []:
                item["tool_calls"] = [
                    {"function": {"name": c["name"], "arguments": c["args"]}} for c in calls
                ]
            out.append(item)
        elif role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_name": msg.get("name", ""),
                    "content": msg["content"],
                }
            )
            pending.extend(i["data"] for i in msg.get("images") or [])
    flush()
    return out


def think_value(reasoning: str | None, model: str) -> bool | str | None:
    """Ollama's think field: off, on, or a level for the models that take one."""
    if not reasoning:
        return None
    if reasoning == "none":
        return False
    if "gpt-oss" in model:
        return reasoning
    return True


class OllamaProvider(Provider):
    async def stream(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec],
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        options: dict[str, Any] = {"num_predict": max_tokens}
        if self.config.context_window:
            options["num_ctx"] = self.config.context_window
        body: dict[str, Any] = {
            "model": model,
            "messages": to_ollama_messages(system, messages),
            "stream": True,
            "options": options,
        }
        if (think := think_value(self.config.reasoning, model)) is not None:
            body["think"] = think
        if self.config.keep_alive is not None:
            body["keep_alive"] = f"{self.config.keep_alive}m"
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
        url = native_base(self.config.base_url) + "/api/chat"

        usage = Usage()
        finish: str | None = None
        calls: list[dict[str, Any]] = []
        text_parts: list[str] = []
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
                async for raw in resp.content:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except ValueError:
                        continue
                    if "error" in payload:
                        raise ProviderError(f"{self.config.name}: {payload['error']}")
                    message = payload.get("message") or {}
                    if text := message.get("content"):
                        text_parts.append(text)
                        yield TextDelta(text)
                    for tc in message.get("tool_calls") or []:
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            args = fn.get("arguments")
                            calls.append(
                                {
                                    "id": tc.get("id") or "",
                                    "name": fn["name"],
                                    "args": args
                                    if isinstance(args, dict)
                                    else parse_args(args or ""),
                                }
                            )
                    if payload.get("done"):
                        finish = payload.get("done_reason") or "stop"
                        usage.input_tokens = payload.get("prompt_eval_count", 0) or 0
                        usage.output_tokens = payload.get("eval_count", 0) or 0
                        break
        except aiohttp.ClientError as err:
            raise ProviderError(f"{self.config.name} connection error: {err}") from err

        if finish is None:
            # the connection closed mid-reply; never act on half a reply
            raise ProviderError(f"{self.config.name}: the reply ended early. Try again.")
        for idx, entry in enumerate(calls):
            args = {"_truncated": True} if finish == "length" else entry["args"]
            yield ToolCall(entry["id"] or f"call_{idx}", entry["name"], args)
        if calls:
            finish = "tool_calls" if finish != "length" else finish
        elif tools and finish != "length" and (call := text_tool_call("".join(text_parts), tools)):
            _LOGGER.debug("%s: recovered a tool call written as text", self.config.name)
            yield call
            finish = "tool_calls"
        yield usage
        yield Done(finish)
