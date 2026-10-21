"""Static model suggestions and prices (USD per million tokens).

These are suggestions only: any model id can be typed in the panel. Prices are
estimates for the cost display and can be overridden in the integration options.
Update this table, and PRICES_CHECKED, in a release when providers change prices.
Sources: platform.claude.com/docs/en/about-claude/pricing and
developers.openai.com/api/docs/pricing and ai.google.dev/gemini-api/docs/pricing (standard
tier; Gemini 3.8 Flash at its list price, not the price that ends 2026-12-31). OpenRouter prices come live from
its model list, so they are always current.
"""

from __future__ import annotations

from typing import Any

# provider type -> default base URL
DEFAULT_BASE_URLS: dict[str, str] = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://homeassistant.local:11434/v1",
    "gemini": "https://generativelanguage.googleapis.com",
    "chatgpt": "https://chatgpt.com/backend-api/codex",
}

PROVIDER_NAMES: dict[str, str] = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "openrouter": "OpenRouter",
    "ollama": "Ollama",
    "gemini": "Google Gemini (unverified)",
    "chatgpt": "ChatGPT subscription (experimental)",
}

PRICES_CHECKED = "2026-10-20"

# (model id, label, input $/M, output $/M, cache-read $/M or None)
_MODELS: dict[str, list[tuple[str, str, float | None, float | None, float | None]]] = {
    "anthropic": [
        ("claude-sonnet-5-5", "Claude Sonnet 5.5", 2.0, 10.0, 0.1),
        ("claude-opus-5-5", "Claude Opus 5.5", 4.0, 20.0, 0.2),
        ("claude-haiku-5-5", "Claude Haiku 5.5", 0.1, 0.5, 0.01),
        ("claude-fable-5-1", "Claude Fable 5.1", 10.0, 50.0, 0.25),
    ],
    "openai": [
        ("gpt-5.5", "GPT-5.5", 5.0, 30.0, 0.5),
        ("gpt-5.4", "GPT-5.4", 2.5, 15.0, 0.25),
        ("gpt-5.4-mini", "GPT-5.4 mini", 0.75, 4.5, 0.075),
        ("gpt-5.4-nano", "GPT-5.4 nano", 0.2, 1.25, 0.02),
    ],
    "openrouter": [
        ("openrouter/auto", "Auto router", None, None, None),
        ("anthropic/claude-sonnet-5.5", "Claude Sonnet 5.5", 2.0, 10.0, 0.1),
        ("openai/gpt-5.4-mini", "GPT-5.4 mini", 0.75, 4.5, 0.075),
        ("google/gemini-2.5-flash", "Gemini 2.5 Flash", None, None, None),
    ],
    "ollama": [
        ("llama3.1:8b", "Llama 3.1 8B (local)", 0.0, 0.0, 0.0),
        ("granite3.3:8b", "Granite 3.3 8B (local)", 0.0, 0.0, 0.0),
        ("gpt-oss:20b", "gpt-oss 20B (local)", 0.0, 0.0, 0.0),
    ],
    "gemini": [
        ("gemini-3-flash-preview", "Gemini 3 Flash (preview)", 0.5, 3.0, 0.05),
        ("gemini-3.1-pro-preview", "Gemini 3.1 Pro (preview)", 2.0, 12.0, 0.2),
        ("gemini-3.8-flash", "Gemini 3.8 Flash", 1.5, 7.5, 0.15),
    ],
    # Covered by the ChatGPT plan, so no per-token cost is shown.
    "chatgpt": [
        ("gpt-5.5", "GPT-5.5", 0.0, 0.0, 0.0),
        ("gpt-5.4", "GPT-5.4", 0.0, 0.0, 0.0),
        ("gpt-5.4-mini", "GPT-5.4 mini", 0.0, 0.0, 0.0),
    ],
}


# Models that bill more once one request's prompt passes a size:
# model -> (prompt tokens, (input, output, cache-read) $/M above that size).
LONG_PROMPT_PRICES: dict[str, tuple[int, tuple[float, float, float]]] = {
    "claude-haiku-5-5": (100_000, (0.5, 2.5, 0.05)),
    "gemini-3.1-pro-preview": (200_000, (4.0, 18.0, 0.4)),
}

Price = tuple[float, float, float]


def suggestions(provider_type: str) -> list[dict[str, Any]]:
    return [
        {"id": m, "label": label, "input": i, "output": o, "cache_read": c}
        for m, label, i, o, c in _MODELS.get(provider_type, [])
    ]


def default_model(provider_type: str) -> str:
    models = _MODELS.get(provider_type) or [("", "", None, None, None)]
    return models[0][0]


def price_for(
    provider_type: str,
    model: str,
    overrides: dict[str, Any] | None = None,
    live: dict[str, Price] | None = None,
) -> Price | None:
    """Return (input, output, cache_read) $/M for a model, or None if unknown.
    Your overrides win, then prices the provider published (OpenRouter), then our table."""
    if overrides and model in overrides:
        o = overrides[model]
        try:
            inp, out = float(o["input"]), float(o["output"])
            return inp, out, float(o.get("cache_read", inp))
        except KeyError, TypeError, ValueError:
            pass
    if live and model in live:
        return live[model]
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


# OpenAI's list includes embedding, audio and image models that can't chat.
_NOT_CHAT = (
    "embedding",
    "tts",
    "whisper",
    "dall-e",
    "audio",
    "realtime",
    "transcribe",
    "image",
    "moderation",
    "search",
    "davinci",
    "babbage",
    "sora",
)


def models_request(
    provider_type: str, base_url: str, api_key: str | None
) -> tuple[str, dict[str, str]]:
    """URL and headers for the provider's model list (also used to check credentials)."""
    base = base_url.rstrip("/")
    if provider_type == "anthropic":
        return f"{base}/v1/models?limit=100", {
            "x-api-key": api_key or "",
            "anthropic-version": "2023-06-01",
        }
    if provider_type == "gemini":
        return f"{base}/v1beta/models?pageSize=1000", {"x-goog-api-key": api_key or ""}
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    return f"{base}/models", headers


def parse_models(provider_type: str, body: Any) -> list[str]:
    """Model ids from a /models response that can chat and call tools, where we can tell."""
    if provider_type == "gemini":
        return _gemini_models(body)
    items = body.get("data") if isinstance(body, dict) else None
    if not isinstance(items, list):
        return []
    ids = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        model_id = item["id"]
        if provider_type == "openai" and any(w in model_id for w in _NOT_CHAT):
            continue
        params = item.get("supported_parameters")
        if provider_type == "openrouter" and isinstance(params, list) and "tools" not in params:
            continue
        ids.append(model_id)
    return ids


def _gemini_models(body: Any) -> list[str]:
    items = body.get("models") if isinstance(body, dict) else None
    ids = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        methods = item.get("supportedGenerationMethods")
        if isinstance(methods, list) and "generateContent" not in methods:
            continue
        model_id = item["name"].removeprefix("models/")
        if any(w in model_id for w in ("embedding", "tts", "image", "audio", "live", "aqa")):
            continue
        ids.append(model_id)
    return ids


def parse_prices(provider_type: str, body: Any) -> dict[str, Price]:
    """Per-model prices from an OpenRouter /models response ($ per token, as strings)."""
    if provider_type != "openrouter" or not isinstance(body, dict):
        return {}
    prices: dict[str, Price] = {}
    for item in body.get("data") or []:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        pricing = item.get("pricing")
        if not isinstance(pricing, dict):
            continue
        try:
            inp = float(pricing["prompt"]) * 1_000_000
            out = float(pricing["completion"]) * 1_000_000
            cached = float(pricing.get("input_cache_read") or pricing["prompt"]) * 1_000_000
        except KeyError, TypeError, ValueError:
            continue
        if min(inp, out, cached) < 0:  # OpenRouter uses -1 for "varies" (auto router)
            continue
        prices[item["id"]] = (round(inp, 6), round(out, 6), round(cached, 6))
    return prices


def merge_models(provider_type: str, fetched: list[str] | None) -> list[dict[str, Any]]:
    """Our labelled suggestions that the provider still offers, then everything else it
    offers. Without a fetched list, the suggestions alone."""
    known = suggestions(provider_type)
    if not fetched:
        return known
    offered = set(fetched)
    merged = [m for m in known if m["id"] in offered]
    seen = {m["id"] for m in merged}
    merged += [{"id": m, "label": m} for m in sorted(offered - seen)]
    return merged
