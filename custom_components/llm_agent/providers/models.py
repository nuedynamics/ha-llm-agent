"""Static model suggestions and prices (USD per million tokens).

These are suggestions only: any model id can be typed in the panel. Prices are
estimates for the cost display and can be overridden in the integration options.
Update this table in a release when providers change their line-up.
"""

from __future__ import annotations

from typing import Any

# provider type -> default base URL
DEFAULT_BASE_URLS: dict[str, str] = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://homeassistant.local:11434/v1",
}

PROVIDER_NAMES: dict[str, str] = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "openrouter": "OpenRouter",
    "ollama": "Ollama",
}

# (model id, label, input $/M, output $/M, cache-read $/M or None)
_MODELS: dict[str, list[tuple[str, str, float | None, float | None, float | None]]] = {
    "anthropic": [
        ("claude-sonnet-5-5", "Claude Sonnet 5.5", 2.0, 10.0, 0.2),
        ("claude-opus-5-5", "Claude Opus 5.5", 4.0, 20.0, 0.4),
        ("claude-haiku-5-5", "Claude Haiku 5.5", 0.1, 0.5, 0.01),
        ("claude-fable-5-1", "Claude Fable 5.1", 10.0, 50.0, 1.0),
    ],
    "openai": [
        ("gpt-5.5", "GPT-5.5", 5.0, 30.0, 0.5),
        ("gpt-5.4", "GPT-5.4", 2.5, 15.0, 0.25),
        ("gpt-5.4-mini", "GPT-5.4 mini", 0.75, 4.5, 0.075),
        ("gpt-5.4-nano", "GPT-5.4 nano", 0.2, 1.25, 0.02),
    ],
    "openrouter": [
        ("openrouter/auto", "Auto router", None, None, None),
        ("anthropic/claude-sonnet-5.5", "Claude Sonnet 5.5", 2.0, 10.0, 0.2),
        ("openai/gpt-5.4-mini", "GPT-5.4 mini", 0.75, 4.5, 0.075),
        ("google/gemini-2.5-flash", "Gemini 2.5 Flash", None, None, None),
    ],
    "ollama": [
        ("llama3.1:8b", "Llama 3.1 8B (local)", 0.0, 0.0, 0.0),
        ("granite3.3:8b", "Granite 3.3 8B (local)", 0.0, 0.0, 0.0),
        ("gpt-oss:20b", "gpt-oss 20B (local)", 0.0, 0.0, 0.0),
    ],
}


def suggestions(provider_type: str) -> list[dict[str, Any]]:
    return [
        {"id": m, "label": label, "input": i, "output": o, "cache_read": c}
        for m, label, i, o, c in _MODELS.get(provider_type, [])
    ]


def default_model(provider_type: str) -> str:
    models = _MODELS.get(provider_type) or [("", "", None, None, None)]
    return models[0][0]


def price_for(
    provider_type: str, model: str, overrides: dict[str, Any] | None = None
) -> tuple[float, float, float] | None:
    """Return (input, output, cache_read) $/M for a model, or None if unknown."""
    if overrides and model in overrides:
        o = overrides[model]
        try:
            inp, out = float(o["input"]), float(o["output"])
            return inp, out, float(o.get("cache_read", inp))
        except KeyError, TypeError, ValueError:
            pass
    for m, _label, i, o, c in _MODELS.get(provider_type, []):
        if m == model and i is not None and o is not None:
            return i, o, c if c is not None else i
    if provider_type == "ollama":
        return 0.0, 0.0, 0.0
    return None


def estimate_cost(
    price: tuple[float, float, float] | None,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float | None:
    if price is None:
        return None
    inp, out, cached = price
    # Anthropic reports cache reads/writes separately from input_tokens; cache
    # writes bill at 1.25x input. OpenAI-style providers include cached tokens
    # in input_tokens, which callers normalise before calling this.
    total = (
        input_tokens * inp
        + output_tokens * out
        + cache_read_tokens * cached
        + cache_write_tokens * inp * 1.25
    )
    return total / 1_000_000
