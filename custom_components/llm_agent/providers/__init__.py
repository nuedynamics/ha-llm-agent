"""Provider adapters."""

from __future__ import annotations

import aiohttp

from .anthropic import AnthropicProvider
from .base import Provider, ProviderConfig, ProviderError
from .openai_compat import OpenAICompatProvider

__all__ = ["Provider", "ProviderConfig", "ProviderError", "make_provider"]


def make_provider(session: aiohttp.ClientSession, config: ProviderConfig) -> Provider:
    if config.type == "anthropic":
        return AnthropicProvider(session, config)
    return OpenAICompatProvider(session, config)
