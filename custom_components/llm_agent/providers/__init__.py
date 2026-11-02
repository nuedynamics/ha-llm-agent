"""Provider adapters."""

from __future__ import annotations

import aiohttp

from .anthropic import AnthropicProvider
from .base import Provider, ProviderConfig, ProviderError
from .chatgpt import ChatGPTProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openai_compat import OpenAICompatProvider

__all__ = ["Provider", "ProviderConfig", "ProviderError", "make_provider"]


def make_provider(session: aiohttp.ClientSession, config: ProviderConfig) -> Provider:
    if config.type == "anthropic":
        return AnthropicProvider(session, config)
    if config.type == "chatgpt":
        return ChatGPTProvider(session, config)
    if config.type == "gemini":
        return GeminiProvider(session, config)
    if config.type == "ollama":
        return OllamaProvider(session, config)
    return OpenAICompatProvider(session, config)
