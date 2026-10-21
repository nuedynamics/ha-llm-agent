"""Household members' limits hold against the ways around them."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
from homeassistant.core import Context, HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.llm_agent.agent import Agent, ChatRun
from custom_components.llm_agent.approval import Level, classify_service, match_rule, parse_rules
from custom_components.llm_agent.phone import APPROVE, DENY, EVENT, PhoneApprovals
from custom_components.llm_agent.tools import ToolContext, ToolError
from custom_components.llm_agent.tools.household import HomeControl, HomeEntities
from custom_components.llm_agent.tools.states import CallService
from custom_components.llm_agent.tools.websocket import WebSocketTool

from .conftest import entry_options
from .test_agent import ScriptedProvider, reply_text, reply_tool
from .test_household import _approve_all, _chat, _tool_results


def _ctx(hass: HomeAssistant, hidden=None) -> ToolContext:
    return ToolContext(hass, None, {}, None, hidden)


def _expose(hass: HomeAssistant, entity_id: str, state: str = "off", **attrs: Any) -> None:
    hass.states.async_set(entity_id, state, attrs)
    async_expose_entity(hass, "conversation", entity_id, True)


async def test_member_control_offers_only_everyday_services(hass: HomeAssistant) -> None:
    _expose(hass, "script.goodnight")
    hass.states.async_set("script.hidden", "off")
    _expose(hass, "media_player.kitchen", "idle")
    hass.states.async_set("media_player.office", "idle")
    async_expose_entity(hass, "conversation", "media_player.office", False)
    tool, ctx = HomeControl(), _ctx(hass)
    # script.<name> runs that script, whatever entity the call names
    decoy = tool.check_args(
        {"domain": "script", "service": "hidden", "entity_ids": ["script.goodnight"]}
    )
    with pytest.raises(ToolError, match=r"can.t use script\.hidden"):
        tool.classify(ctx, decoy)
    join = tool.check_args(
        {
            "domain": "media_player",
            "service": "join",
            "entity_ids": ["media_player.kitchen"],
            "data": {"group_members": ["media_player.office"]},
        }
    )
    with pytest.raises(ToolError, match=r"can.t use media_player\.join"):
        tool.classify(ctx, join)
    sneaky = tool.check_args(
        {
            "domain": "media_player",
            "service": "select_source",
            "entity_ids": ["media_player.kitchen"],
            "data": {"source": "media_player.office"},
        }
    )
    with pytest.raises(ToolError, match=r"media_player\.office"):
        tool.classify(ctx, sneaky)


async def test_service_names_are_compared_the_way_ha_reads_them(hass: HomeAssistant) -> None:
    _expose(hass, "cover.garage", "closed", device_class="garage")
    tool = HomeControl()
    args = tool.check_args(
        {"domain": "Cover", "service": "OPEN_COVER", "entity_ids": ["COVER.GARAGE"]}
    )
    assert args["service"] == "open_cover"
    assert tool.classify(_ctx(hass), args).level is Level.RISKY
    assert classify_service(hass, "cover", "OPEN_COVER", ["cover.garage"]).level is Level.RISKY
    # "a, b" is how HA reads a comma-joined target
    both = {
        "domain": "cover",
        "service": "open_cover",
        "target": {"entity_id": "cover.blind, cover.garage"},
    }
    assert CallService().classify(_ctx(hass), both).level is Level.RISKY


async def test_allowing_one_cover_never_allows_another_in_the_same_websocket_call(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set("cover.blind", "closed")
    hass.states.async_set("cover.garage", "closed", {"device_class": "garage"})
    rules, _ = parse_rules("allow cover.blind")
    args = {
        "command": "call_service",
        "payload": {
            "domain": "cover",
            "service": "open_cover",
            "target": {"entity_id": ["cover.blind", "cover.garage"]},
        },
    }
    groups = WebSocketTool().rule_groups(_ctx(hass), args)
    assert len(groups) == 2
    assert match_rule(rules, groups, False) is None


async def test_member_chat_gets_no_home_notes(hass: HomeAssistant) -> None:
    agent = Agent(hass, entry_options())
    await agent.store.async_load()
    agent.store.set_notes("The safe code is 1234")
    conv = await agent.store.create("p1", "gpt-5.4-mini", "", "kid")
    run = ChatRun(agent, conv, "kid", member=True)
    provider = ScriptedProvider([reply_text("Hi.")])
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await run.run("go")
    assert "1234" not in provider.calls[0]["system"]


async def test_an_allow_rule_never_lets_a_member_skip_the_admin(hass: HomeAssistant) -> None:
    calls = async_mock_service(hass, "lock", "unlock")
    _expose(hass, "lock.front", "locked")
    args = {"domain": "lock", "service": "unlock", "entity_ids": ["lock.front"]}
    conv, _, _, _ = await _chat(
        hass,
        [reply_tool("c1", "home_control", args), reply_text("Can't.")],
        member=True,
        user_id="kid",
        approval_rules="allow lock.*",
    )
    assert not calls
    assert _tool_results(conv)[0]["summary"] == "Needs an admin"


async def test_an_ask_rule_asks_for_reads_too(hass: HomeAssistant) -> None:
    _expose(hass, "light.kitchen")
    _, events, _, _ = await _chat(
        hass,
        [reply_tool("c1", "home_entities", {}), reply_text("Ok.")],
        member=True,
        user_id="kid",
        on_event=_approve_all,
        approval_rules="ask home_entities",
    )
    assert [e for e in events if e["type"] == "approval"]


async def test_a_deny_rule_hides_the_entity_from_a_member(hass: HomeAssistant) -> None:
    _expose(hass, "sensor.private", "1")
    _expose(hass, "sensor.public", "2")
    hidden = lambda e: e == "sensor.private"  # noqa: E731
    out = await HomeEntities().run(_ctx(hass, hidden), {"domain": "sensor"})
    assert [e["entity_id"] for e in out.data["entities"]] == ["sensor.public"]
    with pytest.raises(ToolError):
        await HomeEntities().run(_ctx(hass, hidden), {"entity_ids": ["sensor.private"]})
    conv, _, _, _ = await _chat(
        hass,
        [reply_tool("c1", "home_entities", {"domain": "sensor"}), reply_text("Ok.")],
        member=True,
        user_id="kid",
        approval_rules="deny sensor.private",
    )
    assert "sensor.private" not in str(_tool_results(conv)[0]["content"])


async def test_an_action_whose_targets_change_while_waiting_is_not_run(
    hass: HomeAssistant,
) -> None:
    calls = async_mock_service(hass, "cover", "open_cover")
    hass.states.async_set("cover.blind", "closed")
    args = {"domain": "cover", "service": "open_cover", "target": {"entity_id": "all"}}

    def approve_after_adding(run: ChatRun, event: dict[str, Any]) -> None:
        if event["type"] == "approval":
            hass.states.async_set("cover.garage", "closed", {"device_class": "garage"})
            asyncio.get_running_loop().call_soon(run.answer, event["call_id"], True, "")

    conv, _, _, _ = await _chat(
        hass,
        [reply_tool("c1", "call_service", args), reply_text("Ok.")],
        on_event=approve_after_adding,
        approval_mode="ask_all",
    )
    assert not calls
    assert _tool_results(conv)[0]["summary"] == "Not run: its targets changed"


async def test_one_persons_chats_never_push_out_anothers(hass: HomeAssistant) -> None:
    agent = Agent(hass, entry_options())
    await agent.store.async_load()
    agent.store.max_chats = 2
    mine = await agent.store.create("p1", "m", "", "admin")
    for _ in range(3):
        await agent.store.create("p1", "m", "", "kid")
    ids = {c["id"] for c in agent.store.list()}
    assert mine["id"] in ids
    assert len([c for c in agent.store.list() if c.get("user_id") == "kid"]) == 2


async def test_phone_tokens_end_with_their_approval(hass: HomeAssistant, hass_admin_user) -> None:
    notified = async_mock_service(hass, "notify", "mobile_app_pixel")
    options = {"approval_phone": "notify.mobile_app_pixel"}
    phone = PhoneApprovals(hass)
    answers: list[bool] = []

    def answer(ok: bool) -> bool:
        answers.append(ok)
        return True

    def press(action: str) -> None:
        hass.bus.async_fire(EVENT, {"action": action}, context=Context(user_id=hass_admin_user.id))

    # a change too long for the phone can only be denied there
    token = await phone.send(options, "t", "x", answer, can_approve=False)
    assert [a["action"] for a in notified[-1].data["data"]["actions"]] == [DENY + token]
    press(APPROVE + token)
    await hass.async_block_till_done()
    assert answers == []
    press(DENY + token)
    await hass.async_block_till_done()
    assert answers == [False]
    # answered on the phone: done() still clears the notification
    await phone.done(options, token)
    await hass.async_block_till_done()
    assert notified[-1].data["message"] == "clear_notification"
    press(DENY + token)
    await hass.async_block_till_done()
    assert answers == [False]
    phone.close()
