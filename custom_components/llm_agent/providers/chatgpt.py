"""ChatGPT subscription adapter (experimental): the Responses API on the ChatGPT backend.

Uses the endpoint and request shape of OpenAI's open-source Codex CLI with a ChatGPT
sign-in, so usage counts against the person's ChatGPT plan rather than an API key.
OpenAI does not document this endpoint for other apps; it may change or stop working.
Tested with recorded responses only.
"""

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

# Output item types we replay on the next request; anything else is dropped.
_REPLAY = frozenset({"message", "reasoning", "function_call"})


def _obj(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _count(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    return value if isinstance(value, int) and value > 0 else 0


def _image(img: dict[str, str]) -> dict[str, Any]:
    return {"type": "input_image", "image_url": f"data:{img['media_type']};base64,{img['data']}"}


def _user(text: str, images: list[dict[str, str]] | None) -> dict[str, Any]:
    content = [_image(img) for img in images or []]
    content.append({"type": "input_text", "text": text or " "})
    return {"type": "message", "role": "user", "content": content}


def to_responses_input(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if system:
        out.append(
            {
                "type": "message",
                "role": "developer",
                "content": [{"type": "input_text", "text": system}],
            }
        )
    for msg in messages:
        role = msg["role"]
        if role == "user":
            out.append(_user(msg["content"], msg.get("images")))
        elif role == "assistant":
            raw = (msg.get("raw") or {}).get("chatgpt")
            if raw:
                # Replay what the API returned, encrypted reasoning included.
                out.extend(dict(item) for item in raw)
                continue
            if msg.get("content"):
                out.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": msg["content"]}],
                    }
                )
            for call in msg.get("tool_calls") or []:
                out.append(
                    {
                        "type": "function_call",
                        "call_id": call["id"],
                        "name": call["name"],
                        "arguments": json.dumps(call["args"]),
                    }
                )
        elif role == "tool":
            out.append(
                {
                    "type": "function_call_output",
                    "call_id": msg.get("tool_call_id") or "",
                    "output": msg["content"],
                }
            )
            if msg.get("images"):
                # Tool output is text only; photos follow as a user message.
                out.append(_user("(image from the tool call above)", msg["images"]))
    return out


def _usage(data: dict[str, Any]) -> Usage:
    cached = _count(_obj(data.get("input_tokens_details")), "cached_tokens")
    return Usage(
        input_tokens=max(0, _count(data, "input_tokens") - cached),
        output_tokens=_count(data, "output_tokens"),
        cache_read_tokens=cached,
    )


def _error(data: dict[str, Any]) -> str:
    err = _obj(_obj(data.get("response")).get("error")) or _obj(data.get("error"))
    msg = err.get("message") or data.get("message") or "the service returned an error"
    return f"ChatGPT: {str(msg)[:500]}"


class ChatGPTProvider(Provider):
    async def stream(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec],
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        if self.config.auth is None:
            raise ProviderError("ChatGPT: not signed in")
        token, account = await self.config.auth()
        # The ChatGPT backend takes no output limit (max_tokens is ignored) and no
        # separate instructions field: the system prompt goes in as a developer message.
        body: dict[str, Any] = {
            "model": model,
            "input": to_responses_input(system, messages),
            "tools": [
                {
                    "type": "function",
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters or {"type": "object", "properties": {}},
                    "strict": False,
                }
                for t in tools
            ],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "store": False,
            "stream": True,
            "include": ["reasoning.encrypted_content"],
        }
        headers = {
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "accept": "text/event-stream",
        }
        if account:
            headers["chatgpt-account-id"] = account
        url = f"{self.config.base_url.rstrip('/')}/responses"
        usage = Usage()
        stop_reason: str | None = None
        items: list[dict[str, Any]] = []
        calls: list[ToolCall] = []
        finished = False
        try:
            async with open_stream(
                self._session,
                url,
                body,
                headers,
                "ChatGPT",
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
                    kind = payload.get("type")
                    if kind == "response.output_text.delta":
                        if isinstance(delta := payload.get("delta"), str) and delta:
                            yield TextDelta(delta)
                    elif kind == "response.refusal.delta":
                        stop_reason = "refusal"
                        if isinstance(delta := payload.get("delta"), str) and delta:
                            yield TextDelta(delta)  # the model's explanation
                    elif kind == "response.output_item.done":
                        item = _obj(payload.get("item"))
                        if not isinstance(item.get("type"), str) or item["type"] not in _REPLAY:
                            continue
                        items.append(dict(item))
                        if item["type"] == "function_call":
                            args = item.get("arguments")
                            calls.append(
                                ToolCall(
                                    str(item.get("call_id") or item.get("id") or ""),
                                    str(item.get("name") or ""),
                                    parse_args(args if isinstance(args, str) else "{}"),
                                )
                            )
                        elif item["type"] == "message":
                            content = item.get("content")
                            for part in content if isinstance(content, list) else []:
                                if _obj(part).get("type") == "refusal":
                                    stop_reason = "refusal"
                    elif kind in ("response.completed", "response.incomplete"):
                        response = _obj(payload.get("response"))
                        usage = _usage(_obj(response.get("usage")))
                        finished = True
                        if kind == "response.incomplete":
                            reason = _obj(response.get("incomplete_details")).get("reason")
                            stop_reason = "refusal" if reason == "content_filter" else "max_tokens"
                        elif stop_reason is None:
                            stop_reason = "tool_use" if calls else "end_turn"
                    elif kind in ("response.failed", "error"):
                        raise ProviderError(_error(payload))
        except aiohttp.ClientError as err:
            raise ProviderError(f"ChatGPT connection error: {err}") from err
        if not finished:
            # Never act on, or keep, a reply that stopped before it said it was done.
            raise ProviderError("ChatGPT: the reply stopped before it was complete. Try again.")
        if stop_reason == "refusal":
            # A refused reply never runs tools, and isn't replayed with calls left open.
            calls = []
            items = [i for i in items if i["type"] != "function_call"]
        for call in calls:
            if stop_reason == "max_tokens":
                call.args = {"_truncated": True}
            yield call
        yield usage
        yield Done(stop_reason, raw={"chatgpt": items} if items else None)
