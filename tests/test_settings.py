"""0.1.3 settings reach the parts they control."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant

from custom_components.llm_agent.agent import Agent, ChatRun
from custom_components.llm_agent.const import setting

from .conftest import PROVIDER, entry_options
from .test_agent import ScriptedProvider, reply_text
from .test_init import _setup


def test_numbers_are_clamped_to_safe_ranges() -> None:
    assert setting({"max_steps": 10_000}, "max_steps") == 200
    assert setting({"keep_turns": 0}, "keep_turns") == 2
    assert setting({"retries": "nonsense"}, "retries") == 3
    assert setting({}, "compact_at_tokens") == 100_000


async def test_limits_reach_the_stores_and_providers(hass: HomeAssistant) -> None:
    provider = {**PROVIDER, "context_window": 8192}
    agent = Agent(
        hass,
        entry_options(
            providers=[provider],
            chats_in_memory=2,
            max_chats=20,
            undo_size_mb=10,
            undo_keep=7,
            undo_max_age_days=3,
            audit_size_mb=4,
            request_timeout=900,
            retries=0,
        ),
    )
    assert agent.store.cache_size == 2 and agent.store.max_chats == 20
    assert agent.snapshots.max_bytes == 10 * 1024 * 1024 and agent.snapshots.keep == 7
    assert agent.snapshots.max_age_days == 3
    assert agent.snapshots.audit_max_bytes == 4 * 1024 * 1024
    pconf = agent.providers()[0]
    assert (pconf.timeout, pconf.retries, pconf.context_window) == (900, 0, 8192)


async def _one_turn(hass: HomeAssistant, **opts: Any) -> tuple[ScriptedProvider, Agent]:
    provider = ScriptedProvider([reply_text("Done.")])
    agent = Agent(hass, entry_options(**opts))
    await agent.store.async_load()
    conv = await agent.store.create("p1", "gpt-5.4-mini", "ctx")
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await ChatRun(agent, conv, None).run("hello")
    return provider, agent


async def test_reply_length_and_compaction_settings_are_used(hass: HomeAssistant) -> None:
    with patch("custom_components.llm_agent.agent.compact_history", return_value=False) as compact:
        provider, _agent = await _one_turn(
            hass,
            providers=[{**PROVIDER, "context_window": 8192}],
            max_reply_tokens=4096,
            keep_turns=4,
        )
    assert provider.calls[0]["max_tokens"] == 4096
    # a small context window lowers the threshold to half the window
    assert compact.call_args.args[1:] == (4096, 4)

    with patch("custom_components.llm_agent.agent.compact_history") as compact:
        await _one_turn(hass, compact_at_tokens=0)
    compact.assert_not_called()


async def test_prompt_log_only_when_turned_on(hass: HomeAssistant, caplog) -> None:
    name = "custom_components.llm_agent.agent.prompts"
    await _one_turn(hass)
    assert not [r for r in caplog.records if r.name == name]
    caplog.clear()
    await _one_turn(hass, log_prompts=True)
    logged = [r.getMessage() for r in caplog.records if r.name == name]
    assert any("system prompt" in m for m in logged)
    assert any("hello" in m for m in logged) and any("Done." in m for m in logged)
    logging.getLogger(name).setLevel(logging.NOTSET)


async def test_home_summary_can_be_left_out(hass: HomeAssistant, hass_ws_client) -> None:
    entry = await _setup(hass, include_home_summary=False)
    agent = entry.runtime_data
    provider = ScriptedProvider([reply_text("Hi.")])
    client = await hass_ws_client(hass)
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await client.send_json({"id": 1, "type": "llm_agent/chat", "text": "hello"})
        msg = await client.receive_json()
        assert msg["success"]
        while (await client.receive_json())["event"]["type"] != "done":
            pass
    conv = await agent.store.get(msg["result"]["conversation_id"])
    assert conv["context"] == ""
    assert "Home:" not in provider.calls[0]["system"]


async def test_each_user_can_set_a_default_model(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "llm_agent/my_default", "provider_id": "p1", "model": "gpt-5.5"}
    )
    assert (await client.receive_json())["result"]["my_default"] == {
        "provider_id": "p1",
        "model": "gpt-5.5",
    }
    await client.send_json({"id": 2, "type": "llm_agent/info"})
    assert (await client.receive_json())["result"]["my_default"]["model"] == "gpt-5.5"
    await client.send_json({"id": 3, "type": "llm_agent/my_default", "provider_id": "nope"})
    assert not (await client.receive_json())["success"]
    await client.send_json({"id": 4, "type": "llm_agent/my_default", "provider_id": None})
    assert (await client.receive_json())["result"]["my_default"] is None
