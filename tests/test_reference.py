"""The built-in reference pages: every page is indexed, and every example is valid config
for the Home Assistant version under test, so the pages can't drift from HA."""

from __future__ import annotations

import json
import re

from homeassistant.core import HomeAssistant
import pytest
import yaml

from custom_components.llm_agent.tools import ToolError
from custom_components.llm_agent.tools.config_items import _validate
from custom_components.llm_agent.tools.reference import ORDER, _read_pages, async_index, summary

from .test_tools import _ctx, _tool

PAGES = _read_pages()
START = [{"trigger": "homeassistant", "event": "start"}]


def _blocks(page: str, lang: str) -> list[str]:
    return re.findall(rf"```{lang}\n(.*?)```", PAGES[page], re.S)


def test_every_page_is_indexed_with_a_summary() -> None:
    assert list(PAGES) == list(ORDER)
    for name, text in PAGES.items():
        assert text.startswith("# ") and summary(text), name


async def test_index_lists_every_page(hass: HomeAssistant) -> None:
    index = await async_index(hass)
    assert all(f"- {name}: " in index for name in ORDER)
    assert len(index) < 2500  # it is in every system prompt


async def test_read_reference_returns_a_page(hass: HomeAssistant) -> None:
    tool = _tool("read_reference")
    out = await tool.run(_ctx(hass), {"page": "triggers.md"})
    assert out.data.startswith("# Triggers")
    with pytest.raises(ToolError, match="Pages: automations"):
        await tool.run(_ctx(hass), {"page": "nope"})


@pytest.mark.parametrize(
    ("page", "wrap"),
    [
        ("automations", lambda c: c),
        ("triggers", lambda c: {"triggers": c["triggers"], "actions": []}),
        ("conditions", lambda c: {"triggers": START, **c, "actions": []}),
        ("actions", lambda c: {"triggers": START, **c}),
    ],
)
async def test_automation_examples_are_valid(hass: HomeAssistant, page, wrap) -> None:
    blocks = _blocks(page, "yaml")
    assert blocks
    for block in blocks:
        await _validate(_ctx(hass), "automation", "example", wrap(yaml.safe_load(block)))


async def test_script_example_is_valid(hass: HomeAssistant) -> None:
    script = yaml.safe_load(_blocks("scripts-scenes", "yaml")[0])
    await _validate(_ctx(hass), "script", "bedtime", script)


async def test_mistakes_called_out_are_really_rejected(hass: HomeAssistant) -> None:
    # The pages warn about these; make sure HA still rejects them.
    for bad in (
        {"triggers": [{"trigger": "time", "at": "23:00:00", "days": ["mon"]}], "actions": []},
        {"triggers": START, "actions": [{"platform": "homeassistant", "action": "light.turn_on"}]},
    ):
        with pytest.raises(ToolError):
            await _validate(_ctx(hass), "automation", "bad", bad)


def test_dashboard_examples_pass_the_dashboard_check() -> None:
    save = _tool("save_dashboard")
    for block in _blocks("dashboards", "json"):
        save.check_args({"config": json.loads(block), "url_path": "living-room"})


def test_service_call_example_is_well_formed() -> None:
    args = json.loads(_blocks("targets", "json")[0])
    assert _tool("call_service").check_args(args)["target"] == {"entity_id": ["light.kitchen"]}


async def test_blueprint_example_saves_and_an_automation_can_use_it(hass: HomeAssistant) -> None:
    from homeassistant.setup import async_setup_component

    from custom_components.llm_agent.tools.files import check_syntax

    rel = "blueprints/automation/llm_agent/motion_light.yaml"
    text = _blocks("blueprints", "yaml")[0]
    check_syntax(rel, text)
    path = hass.config.path(rel)

    def _write() -> None:
        import os

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    await hass.async_add_executor_job(_write)
    assert await async_setup_component(hass, "automation", {})
    usage = json.loads(_blocks("blueprints", "json")[0])
    await _validate(_ctx(hass), "automation", "example", usage)


def test_package_python_and_template_helper_examples_are_well_formed() -> None:
    from custom_components.llm_agent.tools.files import check_syntax

    for block in _blocks("packages", "yaml"):
        check_syntax("packages/example.yaml", block)
    check_syntax("python_scripts/example.py", _blocks("packages", "python")[0])
    form = json.loads(_blocks("helpers", "json")[-1])
    assert form["state"].startswith("{{")
