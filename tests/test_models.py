"""Model lists fetched from the provider: filtering, merging with suggestions, caching."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.llm_agent.agent import Agent
from custom_components.llm_agent.providers.models import merge_models, parse_models, suggestions

from .conftest import entry_options
from .test_init import _setup

URL = "http://stub.invalid/v1/models"


def test_only_chat_and_tool_models_are_listed() -> None:
    openai = {"data": [{"id": "gpt-x"}, {"id": "text-embedding-3"}, {"id": "whisper-1"}]}
    assert parse_models("openai", openai) == ["gpt-x"]
    router = {
        "data": [
            {"id": "a/tools", "supported_parameters": ["tools", "temperature"]},
            {"id": "b/no-tools", "supported_parameters": ["temperature"]},
        ]
    }
    assert parse_models("openrouter", router) == ["a/tools"]
    assert parse_models("ollama", {"oops": 1}) == []


def test_merge_keeps_labels_drops_retired_suggestions() -> None:
    known = suggestions("openai")
    assert merge_models("openai", None) == known
    first = known[0]["id"]
    merged = merge_models("openai", [first, "brand-new"])
    assert merged[0] == known[0]  # still labelled
    assert merged[1] == {"id": "brand-new", "label": "brand-new"}
    assert len(merged) == 2  # suggestions the provider no longer offers are dropped


async def test_agent_fetches_once_and_falls_back(hass: HomeAssistant, aioclient_mock) -> None:
    agent = Agent(hass, entry_options())
    aioclient_mock.get(URL, json={"data": [{"id": "gpt-x"}]})
    models, error = await agent.models("p1")
    assert error is None and [m["id"] for m in models] == ["gpt-x"]
    await agent.models("p1")
    assert aioclient_mock.call_count == 1  # cached
    # Failure with nothing cached: the built-in suggestions and a reason.
    agent._model_cache.clear()
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=401)
    models, error = await agent.models("p1")
    assert models == suggestions("openai") and "HTTP 401" in error
    headers = aioclient_mock.mock_calls[0][3]
    assert headers["Authorization"] == "Bearer sk-test"


async def test_ws_models(hass: HomeAssistant, hass_ws_client, aioclient_mock) -> None:
    await _setup(hass)
    aioclient_mock.get(URL, json={"data": [{"id": "gpt-x"}]})
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "llm_agent/models", "provider_id": "p1"})
    msg = await client.receive_json()
    assert msg["success"] and msg["result"]["models"] == [{"id": "gpt-x", "label": "gpt-x"}]


def test_openrouter_prices_come_from_its_model_list() -> None:
    from custom_components.llm_agent.providers.models import parse_prices, price_for

    body = {
        "data": [
            {
                "id": "a/model",
                "pricing": {
                    "prompt": "0.000001",
                    "completion": "0.000004",
                    "input_cache_read": "0.0000001",
                },
            },
            {"id": "openrouter/auto", "pricing": {"prompt": "-1", "completion": "-1"}},
            {"id": "b/no-price"},
        ]
    }
    live = parse_prices("openrouter", body)
    assert live == {"a/model": (1.0, 4.0, 0.1)}
    assert price_for("openrouter", "a/model", None, live) == (1.0, 4.0, 0.1)
    # your own override still wins
    assert price_for("openrouter", "a/model", {"a/model": {"input": 2, "output": 3}}, live) == (
        2.0,
        3.0,
        2.0,
    )
    assert parse_prices("openai", body) == {}


def test_anthropic_cache_read_prices_match_the_published_table() -> None:
    from custom_components.llm_agent.providers.models import price_for

    assert price_for("anthropic", "claude-haiku-5-5") == (0.1, 0.5, 0.01)
    assert price_for("anthropic", "claude-sonnet-5-5") == (2.0, 10.0, 0.1)
    assert price_for("anthropic", "claude-opus-5-5") == (4.0, 20.0, 0.2)
    assert price_for("anthropic", "claude-fable-5-1") == (10.0, 50.0, 0.25)
