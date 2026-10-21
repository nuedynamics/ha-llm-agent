"""Tools from MCP servers set up with Home Assistant's Model Context Protocol integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
import probatio as vol
import pytest

from custom_components.llm_agent.agent import ChatRun
from custom_components.llm_agent.approval import Level
from custom_components.llm_agent.tools import ToolError
from custom_components.llm_agent.tools.mcp import MAX_TOOLS, McpTool, async_mcp_tools

from .test_agent import ScriptedProvider, _run, reply_text, reply_tool


class RemoteTool(llm.Tool):
    def __init__(self, name: str, reply: Any = None, error: bool = False) -> None:
        self.name = name
        self.description = f"{name} from the test server. " + "x" * 2000
        self.parameters = vol.Schema({vol.Required("query"): str})
        self.reply = {"answer": "42"} if reply is None else reply
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def async_call(self, hass, tool_input, llm_context):
        self.calls.append(tool_input.tool_args)
        return llm.ToolResult(self.reply, error=self.error)


@dataclass(kw_only=True)
class FakeServerApi(llm.API):
    tools: list[llm.Tool] = field(default_factory=list)

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        return llm.APIInstance(self, "", llm_context, tools=self.tools)


def _server(hass: HomeAssistant, slug: str, *tools: llm.Tool, name: str = "Test server"):
    return llm.async_register_api(
        hass, FakeServerApi(hass=hass, id=f"mcp-{slug}", name=name, tools=list(tools))
    )


async def test_off_by_default_and_only_mcp_servers_are_offered(hass: HomeAssistant) -> None:
    _server(hass, "notes", RemoteTool("search"))
    llm.async_register_api(hass, FakeServerApi(hass=hass, id="other", name="Other", tools=[]))
    assert await async_mcp_tools(hass, {}, None) == []
    tools = await async_mcp_tools(hass, {"mcp_tools": True}, None)
    assert [t.name for t in tools] == ["mcp_notes_search"]
    tool = tools[0]
    assert isinstance(tool, McpTool) and tool.untrusted
    assert "outside Home Assistant" in tool.description
    assert len(tool.description) < 800  # the server's own text is cut short
    assert tool.parameters["properties"]["query"]["type"] == "string"


async def test_names_are_safe_unique_and_the_count_is_capped(hass: HomeAssistant) -> None:
    _server(hass, "a.b", RemoteTool("do it!"), RemoteTool("do it?"))
    many = [RemoteTool(f"t{i}") for i in range(MAX_TOOLS + 5)]
    for tool in many:
        tool.description = "short"
    _server(hass, "big", *many)
    tools = await async_mcp_tools(hass, {"mcp_tools": True}, None)
    names = [t.name for t in tools]
    assert names[:2] == ["mcp_a_b_do_it_", "mcp_a_b_do_it__2"]
    assert len(names) == len(set(names)) == MAX_TOOLS


async def test_calls_are_risky_checked_and_marked_untrusted(hass: HomeAssistant) -> None:
    remote = RemoteTool("search")
    _server(hass, "notes", remote)
    (tool,) = await async_mcp_tools(hass, {"mcp_tools": True}, None)
    assert tool.classify(None, {"query": "x"}).level is Level.RISKY
    with pytest.raises(ToolError, match="Invalid arguments"):
        tool.check_args({"query": 5, "other": 1})
    ctx = type("Ctx", (), {"hass": hass, "user_id": None})()
    out = await tool.run(ctx, tool.check_args({"query": "x"}))
    assert remote.calls == [{"query": "x"}]
    assert "Untrusted" in out.data["note"] and "42" in out.data["result"]
    preview = await tool.preview(ctx, {"query": "x"})
    assert "Test server" in preview.summary and '"x"' in preview.summary


async def test_server_errors_come_back_as_tool_errors(hass: HomeAssistant) -> None:
    _server(hass, "bad", RemoteTool("search", reply={"error": "nope"}, error=True))
    (tool,) = await async_mcp_tools(hass, {"mcp_tools": True}, None)
    ctx = type("Ctx", (), {"hass": hass, "user_id": None})()
    with pytest.raises(ToolError, match="nope"):
        await tool.run(ctx, {"query": "x"})


async def test_a_call_asks_first_and_taints_the_chat(hass: HomeAssistant) -> None:
    remote = RemoteTool("search")
    _server(hass, "notes", remote)
    provider = ScriptedProvider(
        [reply_tool("m1", "mcp_notes_search", {"query": "x"}), reply_text("It said 42.")]
    )

    def approve(run: ChatRun, event: dict[str, Any]) -> None:
        if event["type"] == "approval":
            asyncio.get_running_loop().call_soon(run.answer, event["call_id"], True, "")

    conv, events = await _run(hass, provider, "ask the server", on_event=approve, mcp_tools=True)
    assert [e["type"] for e in events].count("approval") == 1
    assert remote.calls == [{"query": "x"}]
    assert conv["untrusted"] is True
    offered = [t.name for t in provider.calls[0]["tools"]]
    assert "mcp_notes_search" in offered


async def test_unattended_autopilot_runs_never_reach_the_server(hass: HomeAssistant) -> None:
    from unittest.mock import patch

    from custom_components.llm_agent.agent import Agent

    from .conftest import entry_options

    remote = RemoteTool("search")
    _server(hass, "notes", remote)
    agent = Agent(hass, entry_options(mcp_tools=True, approval_mode="autopilot"))
    await agent.store.async_load()
    conv = await agent.store.create("p1", "gpt-5.4-mini", "")
    run = ChatRun(agent, conv, None, unattended=True)
    provider = ScriptedProvider(
        [reply_tool("m1", "mcp_notes_search", {"query": "x"}), reply_text("Refused.")]
    )
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await run.run("ask the server")
    assert remote.calls == []


async def test_offering_mcp_tools_marks_the_chat_and_automations_get_none(
    hass: HomeAssistant,
) -> None:
    from unittest.mock import patch

    from custom_components.llm_agent.agent import Agent

    from .conftest import entry_options

    _server(hass, "notes", RemoteTool("search"))
    provider = ScriptedProvider([reply_text("Hi.")])
    conv, _ = await _run(hass, provider, "hello", mcp_tools=True)
    assert conv["untrusted"] is True  # the servers' own text was in the tool list

    agent = Agent(hass, entry_options(mcp_tools=True, approval_mode="autopilot"))
    await agent.store.async_load()
    conv = await agent.store.create("p1", "gpt-5.4-mini", "")
    run = ChatRun(agent, conv, None, unattended=True)
    provider = ScriptedProvider([reply_text("Hi.")])
    with patch("custom_components.llm_agent.agent.make_provider", return_value=provider):
        await run.run("hello")
    assert not any(t.name.startswith("mcp_") for t in provider.calls[0]["tools"])
    assert not conv.get("untrusted")


async def test_huge_schemas_are_left_out(hass: HomeAssistant) -> None:
    big = RemoteTool("big")
    big.parameters = vol.Schema({vol.Required("q", description="x" * 100_000): str})
    _server(hass, "s", big, RemoteTool("small"))
    tools = await async_mcp_tools(hass, {"mcp_tools": True}, None)
    assert [t.name for t in tools] == ["mcp_s_small"]
