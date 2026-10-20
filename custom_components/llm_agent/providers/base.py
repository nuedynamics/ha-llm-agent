"""Provider-neutral types and the streaming interface shared by all adapters.

Messages use one small neutral shape so the agent loop never deals with
provider-specific formats:

    {"role": "user", "content": str}
    {"role": "assistant", "content": str, "tool_calls": [ToolCall-as-dict, ...]}
    {"role": "tool", "tool_call_id": str, "name": str, "content": str}
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
    timeout: float = 300.0  # seconds without data before giving up
    retries: int = 3
    context_window: int | None = None  # tokens, when the user set it for the provider


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


# Statuses worth retrying: timeouts, conflicts, rate limits, server errors and overloads.
RETRY_STATUSES = frozenset({408, 409, 429, 500, 502, 503, 504, 529})
RETRY_DELAYS = (1.0, 3.0, 8.0, 15.0, 30.0, 30.0)
MAX_RETRY_AFTER = 30.0

_HINTS = {
    401: "the API key was rejected. Check it under Configure → Edit provider.",
    402: "the account is out of credit.",
    403: "the API key is not allowed to use this model or endpoint.",
    404: "the model or endpoint was not found. Check the model id and base URL.",
    413: "the request is too large for this model.",
    429: "rate limited. Try again shortly.",
    529: "the provider is overloaded. Try again shortly.",
}


def _retry_after(resp: aiohttp.ClientResponse, default: float) -> float:
    try:
        value = float(resp.headers.get("retry-after", ""))
    except ValueError:
        return default
    return max(0.0, min(value, MAX_RETRY_AFTER))


@asynccontextmanager
async def open_stream(
    session: aiohttp.ClientSession,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    provider: str,
    read_timeout: float = 300.0,
    retries: int = 3,
) -> AsyncIterator[aiohttp.ClientResponse]:
    """POST a streaming request, retrying transient failures before any output arrives.

    Once a response with a success status is handed to the caller there are no more
    retries, so streamed text is never duplicated.
    """
    delays = RETRY_DELAYS[: max(0, retries)]
    attempt = 0
    while True:
        try:
            resp = await session.post(
                url,
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=read_timeout),
            )
        except (aiohttp.ClientConnectionError, TimeoutError) as err:
            if attempt >= len(delays):
                raise ProviderError(f"{provider} connection error: {err}") from err
            delay = delays[attempt]
            _LOGGER.debug("%s connection error (%s), retrying in %.0fs", provider, err, delay)
        else:
            if resp.status in RETRY_STATUSES and attempt < len(delays):
                delay = _retry_after(resp, delays[attempt])
                _LOGGER.debug("%s HTTP %s, retrying in %.0fs", provider, resp.status, delay)
                resp.release()
            else:
                try:
                    await raise_for_status(resp, provider)
                    yield resp
                finally:
                    resp.release()
                return
        attempt += 1
        await asyncio.sleep(delay)


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
    hint = _HINTS.get(resp.status) or (
        "the provider had a server error. Try again shortly." if resp.status >= 500 else ""
    )
    prefix = f"{provider}: {hint} " if hint else f"{provider}: "
    raise ProviderError(f"{prefix}(HTTP {resp.status}: {detail})")


def parse_args(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        return {"_invalid_json": raw[:2000]}
    return value if isinstance(value, dict) else {"value": value}
