"""Shared fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
import json
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest

from custom_components.llm_agent.const import DEFAULT_OPTIONS, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components/ in every test."""


@pytest.fixture(autouse=True)
async def core_setup(hass: HomeAssistant) -> None:
    """conversation needs the core integration (exposed entities) first."""
    assert await async_setup_component(hass, "homeassistant", {})


PROVIDER = {
    "id": "p1",
    "type": "openai",
    "name": "Test",
    "api_key": "sk-test",
    "base_url": "http://stub.invalid/v1",
    "default_model": "gpt-5.4-mini",
}


def entry_options(**changes: Any) -> dict[str, Any]:
    return {**DEFAULT_OPTIONS, "providers": [dict(PROVIDER)], **changes}


class FakeContent:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self._gen()

    async def _gen(self) -> AsyncIterator[bytes]:
        for line in self._lines:
            yield line


class FakeResponse:
    def __init__(self, status: int, lines: list[bytes], body: str = "") -> None:
        self.status = status
        self.content = FakeContent(lines)
        self._body = body

    async def text(self) -> str:
        return self._body

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None


class FakeSession:
    """Records requests and replays canned SSE responses in order."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.requests.append({"url": url, **kwargs})
        return self.responses.pop(0)


def sse(events: list[dict[str, Any] | str], named: bool = False) -> list[bytes]:
    lines: list[bytes] = []
    for ev in events:
        if isinstance(ev, str):
            lines.append(f"data: {ev}\n".encode())
        else:
            if named:
                lines.append(f"event: {ev['type']}\n".encode())
            lines.append(f"data: {json.dumps(ev)}\n".encode())
        lines.append(b"\n")
    return lines


__all__ = ["DOMAIN", "PROVIDER", "FakeResponse", "FakeSession", "entry_options", "sse"]
