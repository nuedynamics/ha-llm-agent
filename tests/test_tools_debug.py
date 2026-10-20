"""Debugging tools: traces, logbook and the log file."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.llm_agent.tools import ToolError
from custom_components.llm_agent.tools.debug import condense_trace, parse_log, redact

from .test_tools import _ctx, _tool

LOG = """\
2026-10-20 10:00:00.123 INFO (MainThread) [homeassistant.core] Starting
2026-10-20 10:00:01.000 WARNING (MainThread) [homeassistant.components.zha.core] Device \x1b[31mslow\x1b[0m
2026-10-20 10:00:02.000 ERROR (MainThread) [custom_components.hacs.base] Failed with api_key=abcdef123456 here
Traceback (most recent call last):
  File "x.py", line 1, in <module>
ValueError: boom
2026-10-20 10:00:03.000 ERROR (MainThread) [homeassistant.components.mqtt] Authorization: Bearer abcdefghijklmnop
"""


def test_log_is_parsed_and_secrets_masked() -> None:
    entries = parse_log(LOG)
    assert [e["level"] for e in entries] == ["INFO", "WARNING", "ERROR", "ERROR"]
    assert entries[1]["message"] == "Device slow"
    assert "ValueError: boom" in entries[2]["message"]
    assert "abcdef123456" not in entries[2]["message"] and "api_key=***" in entries[2]["message"]
    assert "abcdefghijklmnop" not in entries[3]["message"]
    assert redact('"password": "hunter22"') == '"password": "***"'


async def test_read_log_filters(hass: HomeAssistant, tmp_path: Path) -> None:
    hass.config.config_dir = str(tmp_path)
    (tmp_path / "home-assistant.log").write_text(LOG)
    tool = _tool("read_log")
    out = await tool.run(_ctx(hass), {})
    assert [e["level"] for e in out.data] == ["WARNING", "ERROR", "ERROR"]
    out = await tool.run(_ctx(hass), {"integration": "hacs", "level": "error"})
    assert len(out.data) == 1 and out.data[0]["logger"] == "custom_components.hacs.base"
    out = await tool.run(_ctx(hass), {"contains": "STARTING", "level": "info"})
    assert len(out.data) == 1
    out = await tool.run(_ctx(hass), {"level": "info", "limit": 2})
    assert out.data["matches"] == 4 and len(out.data["entries"]) == 2
    with pytest.raises(ToolError, match="not found"):
        await tool.run(_ctx(hass), {"previous_run": True})


TRACE = {
    "run_id": "r2",
    "state": "stopped",
    "script_execution": "failed_conditions",
    "timestamp": {"start": "2026-10-20T10:00:00", "finish": "2026-10-20T10:00:01"},
    "trigger": "state of binary_sensor.door",
    "trace": {
        "trigger/0": [{"changed_variables": {"trigger": {"big": 1}, "this": {}}}],
        "condition/0": [{"result": {"result": False, "entities": ["sun.sun"]}}],
    },
}


async def test_traces_list_and_detail(hass: HomeAssistant) -> None:
    hass.states.async_set("automation.door", "on", {"id": "1700"})
    runs = [
        {"run_id": "r1", "timestamp": {"start": "2026-10-20T09:00:00"}, "state": "stopped"},
        {"run_id": "r2", "timestamp": {"start": "2026-10-20T10:00:00"}, "state": "stopped"},
    ]
    ws = AsyncMock(side_effect=[runs[::-1], runs, TRACE])
    with patch("custom_components.llm_agent.tools.debug.ws_call", ws):
        listed = await _tool("get_traces").run(_ctx(hass), {"entity_id": "automation.door"})
        detail = await _tool("get_traces").run(
            _ctx(hass), {"entity_id": "automation.door", "run_id": "latest"}
        )
    assert [r["run_id"] for r in listed.data] == ["r1", "r2"]
    assert ws.call_args_list[0].args[2] == {"domain": "automation", "item_id": "1700"}
    assert ws.call_args_list[2].args[2]["run_id"] == "r2"
    assert detail.data["result"] == "failed_conditions"
    assert detail.data["steps"][1]["step"] == "condition/0"
    assert "variables" not in detail.data["steps"][0]  # trigger and this are left out


async def test_traces_need_an_automation_id(hass: HomeAssistant) -> None:
    hass.states.async_set("automation.yaml_only", "on", {})
    with pytest.raises(ToolError, match="no id"):
        await _tool("get_traces").run(_ctx(hass), {"entity_id": "automation.yaml_only"})


def test_long_traces_are_shortened() -> None:
    trace = dict(TRACE, trace={f"action/{i}": [{"result": {"x": "y" * 280}}] for i in range(80)})
    out = condense_trace(trace)
    assert len(out["steps"]) == 5 and out["steps"][2]["note"] == "steps omitted"


async def test_logbook_entries(hass: HomeAssistant) -> None:
    events = [
        {"when": 1760954400.0, "entity_id": "light.a", "state": "on", "context_user_id": "u1"},
        {"when": 1760954500.0, "entity_id": "light.a", "state": "off", "message": ""},
    ]
    ws = AsyncMock(return_value=events)
    with patch("custom_components.llm_agent.tools.debug.ws_call", ws):
        out = await _tool("get_logbook").run(_ctx(hass), {"entity_ids": "light.a", "limit": 1})
    assert ws.call_args.args[2]["entity_ids"] == ["light.a"]
    assert out.data["older_entries_left_out"] == 1
    assert out.data["entries"] == [
        {"when": out.data["entries"][0]["when"], "entity_id": "light.a", "state": "off"}
    ]
    assert out.data["entries"][0]["when"].startswith("2025-10-20")


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        ("login failed password=1234", "1234"),
        ("Authorization: Basic dXNlcjpwYXNz", "dXNlcjpwYXNz"),
        ("connecting to mqtt://bob:hunter2@broker:1883", "hunter2"),
        ("token: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.abcdefghijk", "eyJhbGciOiJIUzI1NiJ9"),
        ("headers {'x-api-key': 'k9'}", "k9"),
    ],
)
def test_more_credential_formats_are_masked(text: str, secret: str) -> None:
    assert secret not in redact(text)


def test_trace_variables_are_scrubbed() -> None:
    trace = dict(
        TRACE,
        error="auth failed for http://u:pw-77@host/",
        trace={"action/0": [{"changed_variables": {"api_key": "sk-live-9", "x": "ok"}}]},
    )
    text = str(condense_trace(trace))
    assert "sk-live-9" not in text and "pw-77" not in text and "ok" in text


def test_huge_trace_error_still_finishes() -> None:
    trace = dict(
        TRACE,
        error="e" * 13000,
        trace={f"action/{i}": [{"error": "x" * 3000}] for i in range(5)},
    )
    out = condense_trace(trace)
    assert len(str(out)) < 13000


def test_prefixed_names_and_quoted_values_are_masked() -> None:
    assert "brave-dummy-123456" not in redact("search_api_key=brave-dummy-123456")
    assert redact('password="hello world" next') == 'password="***" next'
