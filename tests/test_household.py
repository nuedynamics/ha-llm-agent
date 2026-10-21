"""Household chat for non-admin users, approval rules, per-member caps and phone approvals."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
from homeassistant.core import Context, HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.llm_agent.agent import Agent, ChatRun
from custom_components.llm_agent.approval import match_rule, parse_rules
from custom_components.llm_agent.const import PANEL_URL
from custom_components.llm_agent.phone import APPROVE, DENY, EVENT
from custom_components.llm_agent.store import Viewer
from custom_components.llm_agent.tools import ToolContext, ToolError
from custom_components.llm_agent.tools.household import HomeControl, HomeEntities

from .conftest import entry_options
from .test_agent import ScriptedProvider, reply_text, reply_tool
from .test_init import _setup


def _tool_results(conv: dict[str, Any]) -> list[dict[str, Any]]:
    return [m for m in conv["messages"] if m["role"] == "tool"]


async def _chat(
    hass: HomeAssistant,
    replies: list[list[Any]],
    *,
    member: bool = False,
    unattended: bool = False,
    user_id: str | None = None,
    on_event=None,
    **opts: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]], ScriptedProvider, Agent]:
    agent = Agent(hass, entry_options(**opts))
    await agent.store.async_load()
    conv = await agent.store.create("p1", "gpt-5.4-mini", "", user_id)
    run = ChatRun(agent, conv, user_id, unattended=unattended, member=member)
    events: list[dict[str, Any]] = []

    def listener(event: dict[str, Any]) -> None:
        events.append(event)
        if on_event:
            on_event(run, event)

    run.listeners.add(listener)
    provider = ScriptedProvider(replies)
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await run.run("go")
    return conv, events, provider, agent


def _approve_all(run: ChatRun, event: dict[str, Any]) -> None:
    if event["type"] == "approval":
        asyncio.get_running_loop().call_soon(run.answer, event["call_id"], True, "")


# Rules


def test_rules_parse_verbs_scopes_and_bad_lines() -> None:
    rules, bad = parse_rules(
        "allow light.*, switch.*\nalways ask lock.*\nmembers deny cover.garage\n"
        "never shell  # comment\nmaybe light.*\nallow\n\n# only a comment"
    )
    assert [(r.verb, r.pattern, r.members_only) for r in rules] == [
        ("allow", "light.*", False),
        ("allow", "switch.*", False),
        ("ask", "lock.*", False),
        ("deny", "cover.garage", True),
        ("deny", "shell", False),
    ]
    assert bad == ["maybe light.*", "allow"]


def test_strictest_rule_wins_and_allow_must_cover_every_target() -> None:
    rules, _ = parse_rules("allow light.*\nask lock.*\nmembers deny light.attic")
    light = ["call_service", "light.turn_on", "light.turn_on", "light.kitchen"]
    lock = ["call_service", "homeassistant.turn_off", "lock.turn_off", "lock.front"]
    assert match_rule(rules, [light], False).verb == "allow"
    # one call reaching a light and a lock is not allowed by "allow light.*"
    assert match_rule(rules, [light, lock], False).verb == "ask"
    other = ["call_service", "homeassistant.turn_off", "switch.turn_off", "switch.fan"]
    assert match_rule(rules, [light, other], False) is None
    attic = ["call_service", "light.turn_on", "light.turn_on", "light.attic"]
    assert match_rule(rules, [attic], False).verb == "allow"
    assert match_rule(rules, [attic], True).verb == "deny"


async def test_allow_rule_skips_asking_even_in_ask_everything_mode(hass: HomeAssistant) -> None:
    calls = async_mock_service(hass, "light", "turn_on")
    hass.states.async_set("light.kitchen", "off")
    args = {"domain": "light", "service": "turn_on", "target": {"entity_id": "light.kitchen"}}
    _conv, events, _, _ = await _chat(
        hass,
        [reply_tool("c1", "call_service", args), reply_text("Done.")],
        approval_mode="ask_all",
        approval_rules="allow light.*",
    )
    assert not [e for e in events if e["type"] == "approval"]
    assert len(calls) == 1


async def test_ask_rule_asks_even_in_autopilot_and_deny_refuses(hass: HomeAssistant) -> None:
    async_mock_service(hass, "switch", "turn_on")
    hass.states.async_set("switch.fan", "off")
    args = {"domain": "switch", "service": "turn_on", "target": {"entity_id": "switch.fan"}}
    conv, events, _, _ = await _chat(
        hass,
        [reply_tool("c1", "call_service", args), reply_text("Done.")],
        on_event=_approve_all,
        approval_mode="autopilot",
        approval_rules="ask switch.fan",
    )
    (approval,) = [e for e in events if e["type"] == "approval"]
    assert "your rules ask for switch.fan" in approval["reason"]

    calls = async_mock_service(hass, "light", "turn_on")
    hass.states.async_set("light.kitchen", "off")
    args = {"domain": "light", "service": "turn_on", "target": {"entity_id": "light.kitchen"}}
    conv, events, _, _ = await _chat(
        hass,
        [reply_tool("c1", "call_service", args), reply_text("No.")],
        approval_mode="autopilot",
        approval_rules="deny light.kitchen",
    )
    assert not calls
    assert _tool_results(conv)[0]["summary"] == "Not allowed by your rules"


async def test_deny_rule_also_stops_reads(hass: HomeAssistant) -> None:
    conv, _, _, _ = await _chat(
        hass,
        [reply_tool("c1", "get_history", {"entity_ids": ["sensor.x"]}), reply_text("No.")],
        approval_rules="deny get_history",
    )
    assert _tool_results(conv)[0]["is_error"]


async def test_allow_rule_never_skips_asking_after_web_content(hass: HomeAssistant) -> None:
    async_mock_service(hass, "light", "turn_on")
    hass.states.async_set("light.kitchen", "off")
    args = {"domain": "light", "service": "turn_on", "target": {"entity_id": "light.kitchen"}}
    agent = Agent(hass, entry_options(approval_rules="allow light.*"))
    await agent.store.async_load()
    conv = await agent.store.create("p1", "gpt-5.4-mini", "")
    conv["untrusted"] = True
    run = ChatRun(agent, conv, None)
    seen: list[dict[str, Any]] = []
    run.listeners.add(lambda e: (seen.append(e), _approve_all(run, e)))
    provider = ScriptedProvider([reply_tool("c1", "call_service", args), reply_text("Done.")])
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await run.run("go")
    assert [e for e in seen if e["type"] == "approval"]


# Member tools


def _ctx(hass: HomeAssistant) -> ToolContext:
    return ToolContext(hass, None, {}, None)


async def test_members_see_only_entities_exposed_to_assist(hass: HomeAssistant) -> None:
    hass.states.async_set("light.kitchen", "on")
    hass.states.async_set("light.secret", "off")
    async_expose_entity(hass, "conversation", "light.kitchen", True)
    async_expose_entity(hass, "conversation", "light.secret", False)
    out = await HomeEntities().run(_ctx(hass), {"domain": "light"})
    assert [e["entity_id"] for e in out.data["entities"]] == ["light.kitchen"]
    with pytest.raises(ToolError, match="not one of the devices"):
        await HomeEntities().run(_ctx(hass), {"entity_ids": ["light.secret"]})


async def test_member_control_is_limited_to_exposed_entities_by_id(hass: HomeAssistant) -> None:
    calls = async_mock_service(hass, "light", "turn_on")
    async_mock_service(hass, "homeassistant", "restart")
    hass.states.async_set("light.kitchen", "off")
    hass.states.async_set("light.secret", "off")
    async_expose_entity(hass, "conversation", "light.kitchen", True)
    async_expose_entity(hass, "conversation", "light.secret", False)
    tool = HomeControl()
    ctx = _ctx(hass)
    ok = tool.check_args({"domain": "light", "service": "turn_on", "entity_ids": "light.kitchen"})
    tool.classify(ctx, ok)
    await tool.run(ctx, ok)
    assert len(calls) == 1
    hidden = tool.check_args(
        {"domain": "light", "service": "turn_on", "entity_ids": ["light.secret"]}
    )
    with pytest.raises(ToolError):
        tool.classify(ctx, hidden)
    with pytest.raises(ToolError, match="entity_ids"):
        tool.check_args(
            {
                "domain": "light",
                "service": "turn_on",
                "entity_ids": ["light.kitchen"],
                "data": {"area_id": "upstairs"},
            }
        )
    restart = tool.check_args(
        {"domain": "homeassistant", "service": "restart", "entity_ids": ["light.kitchen"]}
    )
    with pytest.raises(ToolError, match="can't use"):
        tool.classify(ctx, restart)
    wrong = tool.check_args(
        {"domain": "switch", "service": "turn_on", "entity_ids": ["light.kitchen"]}
    )
    with pytest.raises(ToolError, match="only acts on"):
        tool.classify(ctx, wrong)


async def test_member_chat_gets_only_member_tools_and_no_admin_context(
    hass: HomeAssistant,
) -> None:
    _, _, provider, _ = await _chat(hass, [reply_text("Hi.")], member=True, user_id="kid")
    names = {t.name for t in provider.calls[0]["tools"]}
    assert names == {"home_entities", "home_history", "home_control"}
    assert "admin access" not in provider.calls[0]["system"]
    assert "Reference pages" not in provider.calls[0]["system"]


async def test_member_chat_asks_in_autopilot_and_risky_needs_an_admin(
    hass: HomeAssistant,
) -> None:
    calls = async_mock_service(hass, "lock", "unlock")
    hass.states.async_set("lock.front", "locked")
    async_expose_entity(hass, "conversation", "lock.front", True)
    args = {"domain": "lock", "service": "unlock", "entity_ids": ["lock.front"]}
    conv, events, _, _ = await _chat(
        hass,
        [reply_tool("c1", "home_control", args), reply_text("Can't.")],
        member=True,
        user_id="kid",
        approval_mode="autopilot",
    )
    assert not calls
    assert not [e for e in events if e["type"] == "approval"]
    assert _tool_results(conv)[0]["summary"] == "Needs an admin"

    switch_calls = async_mock_service(hass, "switch", "turn_on")
    hass.states.async_set("switch.fan", "off")
    async_expose_entity(hass, "conversation", "switch.fan", True)
    args = {"domain": "switch", "service": "turn_on", "entity_ids": ["switch.fan"]}
    conv, events, _, _ = await _chat(
        hass,
        [reply_tool("c1", "home_control", args), reply_text("Done.")],
        member=True,
        user_id="kid",
        on_event=_approve_all,
        approval_mode="ask_all",
    )
    (approval,) = [e for e in events if e["type"] == "approval"]
    assert not approval["phone_only"]  # an everyday change: the member approves it
    assert len(switch_calls) == 1


async def test_member_cap_stops_the_member_and_cannot_be_overridden(
    hass: HomeAssistant,
) -> None:
    agent = Agent(hass, entry_options(member_daily_cap=0.1))
    await agent.store.async_load()
    with patch.object(type(agent.store), "user_spent", return_value=0.5):
        conv = await agent.store.create("p1", "gpt-5.4-mini", "", "kid")
        run = ChatRun(agent, conv, "kid", member=True)
        provider = ScriptedProvider([reply_text("Hi.")])
        with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
            await run.run("go", over_cap=True)
    assert not provider.calls
    assert conv["stopped"] == "member_cap"


def test_spend_is_counted_per_user_for_today() -> None:
    from custom_components.llm_agent.store import ConversationStore

    store = ConversationStore.__new__(ConversationStore)
    store._spend, store._user_spend = {}, {}
    store._save_index = lambda: None
    store.add_spend("2026-10-20", 0.2, "kid")
    store.add_spend("2026-10-21", 0.1, "kid")
    store.add_spend("2026-10-21", 0.3, None)
    assert store.user_spent("kid", "2026-10-21") == 0.1
    assert store.user_spent("kid", "2026-10-20") == 0.0
    assert store.spent("2026-10-21") == pytest.approx(0.4)


def test_viewers_see_their_own_chats_and_admins_the_unowned_ones() -> None:
    mine, theirs, old = {"user_id": "a"}, {"user_id": "b"}, {}
    admin, member = Viewer("a", True), Viewer("b", False)
    assert admin.sees(mine) and not admin.sees(theirs) and admin.sees(old)
    assert member.sees(theirs) and not member.sees(mine) and not member.sees(old)


# Phone approvals


async def _phone_run(hass: HomeAssistant, press_as) -> tuple[dict[str, Any], list, list]:
    notified = async_mock_service(hass, "notify", "mobile_app_pixel")
    unlocks = async_mock_service(hass, "lock", "unlock")
    hass.states.async_set("lock.front", "locked")
    agent = Agent(hass, entry_options(approval_phone="notify.mobile_app_pixel"))
    await agent.store.async_load()
    conv = await agent.store.create("p1", "gpt-5.4-mini", "")
    run = ChatRun(agent, conv, None, unattended=True)
    args = {"domain": "lock", "service": "unlock", "target": {"entity_id": "lock.front"}}
    provider = ScriptedProvider([reply_tool("c1", "call_service", args), reply_text("Ok.")])
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        task = hass.async_create_task(run.run("unlock"))
        for _ in range(100):
            if notified:
                break
            await asyncio.sleep(0.01)
        assert notified, "the approval was not sent to the phone"
        actions = notified[0].data["data"]["actions"]
        assert actions[0]["action"].startswith(APPROVE) and actions[1]["action"].startswith(DENY)
        assert run.phone_only == {"c1"}
        await press_as(actions[0]["action"])
        if not task.done():
            run.answer("c1", False, "test over")
        await task
    agent.phone.close()
    return conv, notified, unlocks


async def test_an_automation_waits_for_the_phone_and_an_admin_press_approves(
    hass: HomeAssistant, hass_admin_user
) -> None:
    async def press(action: str) -> None:
        hass.bus.async_fire(EVENT, {"action": action}, context=Context(user_id=hass_admin_user.id))
        await hass.async_block_till_done()

    conv, _notified, unlocks = await _phone_run(hass, press)
    assert len(unlocks) == 1
    assert _tool_results(conv)[0]["decision"] == "approved"


async def test_a_press_from_a_non_admin_phone_is_ignored(
    hass: HomeAssistant, hass_read_only_user
) -> None:
    async def press(action: str) -> None:
        hass.bus.async_fire(
            EVENT, {"action": action}, context=Context(user_id=hass_read_only_user.id)
        )
        hass.bus.async_fire(EVENT, {"action": action + "x"})  # a guessed token
        # the turn is still waiting for an answer, so don't wait for every task
        for _ in range(5):
            await asyncio.sleep(0.01)

    conv, _, unlocks = await _phone_run(hass, press)
    assert not unlocks
    assert _tool_results(conv)[0]["decision"] == "denied"


# WebSocket access


async def test_household_members_get_their_own_limited_chat(
    hass: HomeAssistant, hass_ws_client, hass_admin_user, hass_read_only_user
) -> None:
    entry = await _setup(hass, household_chat=True)
    assert hass.data["frontend_panels"][PANEL_URL].require_admin is False
    agent = entry.runtime_data
    agent.store.set_notes("the safe code is in the drawer")
    admin_conv = await agent.store.create("p1", "gpt-5.4-mini", "", hass_admin_user.id)
    old_conv = await agent.store.create("p1", "gpt-5.4-mini", "")

    member = await hass_ws_client(hass, access_token=await _token(hass, hass_read_only_user))
    await member.send_json_auto_id({"type": "llm_agent/info"})
    info = (await member.receive_json())["result"]
    assert info["is_admin"] is False and info["notes"] == ""

    for blocked in (
        {"type": "llm_agent/notes", "notes": "x"},
        {"type": "llm_agent/models", "provider_id": "p1"},
        {"type": "llm_agent/my_default", "provider_id": None},
        {"type": "llm_agent/undo", "snapshot_id": "x"},
    ):
        await member.send_json_auto_id(blocked)
        assert (await member.receive_json())["error"]["code"] == "unauthorized"

    for conv_id in (admin_conv["id"], old_conv["id"]):
        await member.send_json_auto_id(
            {"type": "llm_agent/conversations/get", "conversation_id": conv_id}
        )
        assert (await member.receive_json())["error"]["code"] == "not_found"
        await member.send_json_auto_id(
            {"type": "llm_agent/conversations/delete", "conversation_id": conv_id}
        )
        assert not (await member.receive_json())["success"]
        await member.send_json_auto_id(
            {"type": "llm_agent/chat", "conversation_id": conv_id, "text": "hi"}
        )
        assert (await member.receive_json())["error"]["code"] == "not_found"

    provider = ScriptedProvider([reply_text("Hello")])
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await member.send_json_auto_id(
            {"type": "llm_agent/chat", "text": "hi", "model": "expensive-model"}
        )
        conv_id = (await member.receive_json())["result"]["conversation_id"]
        while (await member.receive_json())["event"]["type"] != "done":
            pass
    assert provider.calls[0]["model"] == "gpt-5.4-mini"  # members can't pick the model
    await member.send_json_auto_id({"type": "llm_agent/conversations/list"})
    assert [c["id"] for c in (await member.receive_json())["result"]] == [conv_id]

    admin = await hass_ws_client(hass)
    await admin.send_json_auto_id({"type": "llm_agent/conversations/list"})
    ids = {c["id"] for c in (await admin.receive_json())["result"]}
    assert ids == {admin_conv["id"], old_conv["id"]}  # not the member's chat


async def test_household_off_keeps_members_out(
    hass: HomeAssistant, hass_ws_client, hass_read_only_user
) -> None:
    await _setup(hass)
    member = await hass_ws_client(hass, access_token=await _token(hass, hass_read_only_user))
    await member.send_json_auto_id({"type": "llm_agent/info"})
    assert (await member.receive_json())["error"]["code"] == "unauthorized"


async def _token(hass: HomeAssistant, user) -> str:
    refresh = await hass.auth.async_create_refresh_token(user, "https://example.com/")
    return hass.auth.async_create_access_token(refresh)
