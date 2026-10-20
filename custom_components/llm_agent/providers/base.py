"""Provider-neutral types and the streaming interface shared by all adapters.

Messages use one small neutral shape so the agent loop never deals with
provider-specific formats:

    {"role": "user", "content": str}
    {"role": "assistant", "content": str, "tool_calls": [ToolCall-as-dict, ...]}
    {"role": "tool", "tool_call_id": str, "name": str, "content": str}
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class ProviderError(Exception):
    """Raised when a provider returns an error or an unusable stream."""


@dataclass(slots=True)
class TextDelta:
    text: str


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "args": self.args}


@dataclass(slots=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(slots=True)
class Done:
    stop_reason: str | None = None
    # Provider-native assistant content to replay verbatim on the next request.
    raw: dict[str, Any] | None = None


StreamEvent = TextDelta | ToolCall | Usage | Done


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderConfig:
    id: str
    type: str
    name: str
    api_key: str | None
    base_url: str
    default_model: str


class Provider:
    """Base adapter. Subclasses implement `stream`."""

    def __init__(self, session: aiohttp.ClientSession, config: ProviderConfig) -> None:
        self._session = session
        self.config = config

    async def stream(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec],
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


async def iter_sse(
    resp: aiohttp.ClientResponse,
) -> AsyncIterator[tuple[str | None, str]]:
    """Yield (event, data) pairs from a server-sent-events response.

    Reads line by line so memory stays flat no matter how long the reply is.
    """
    event: str | None = None
    data_lines: list[str] = []
    async for raw in resp.content:
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if not line:
            if data_lines:
                yield event, "\n".join(data_lines)
            event, data_lines = None, []
            continue
        if line.startswith(":"):
            continue
        name, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if name == "event":
            event = value
        elif name == "data":
            data_lines.append(value)
    if data_lines:
        yield event, "\n".join(data_lines)


async def raise_for_status(resp: aiohttp.ClientResponse, provider: str) -> None:
    if resp.status < 400:
        return
    try:
        body = await resp.text()
    except aiohttp.ClientError:
        body = ""
    detail = body[:500]
    try:
        parsed = json.loads(body)
        err = parsed.get("error", parsed)
        if isinstance(err, dict):
            detail = str(err.get("message") or err)[:500]
    except ValueError, AttributeError:
        pass
    raise ProviderError(f"{provider} HTTP {resp.status}: {detail}")


def parse_args(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        return {"_invalid_json": raw[:2000]}
    return value if isinstance(value, dict) else {"value": value}
