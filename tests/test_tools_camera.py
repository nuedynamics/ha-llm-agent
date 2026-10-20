"""Camera snapshots for vision models, and pictures in provider requests."""

from __future__ import annotations

import base64
from unittest.mock import patch

from homeassistant.components.camera import Image
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.llm_agent.agent import _drop_images, _provider_view
from custom_components.llm_agent.providers.anthropic import to_anthropic_messages
from custom_components.llm_agent.providers.openai_compat import to_openai_messages
from custom_components.llm_agent.tools import ToolError, build_tools
from custom_components.llm_agent.tools.camera import CameraSnapshot

from .conftest import entry_options
from .test_tools import _ctx

JPEG = b"\xff\xd8\xff\xe0fakejpeg"
GET = "homeassistant.components.camera.async_get_image"


async def test_snapshot_attaches_the_picture(hass: HomeAssistant) -> None:
    hass.states.async_set("camera.garage", "idle", {"friendly_name": "Garage"})
    with patch(GET, return_value=Image("image/jpeg", JPEG)) as get:
        out = await CameraSnapshot().run(_ctx(hass), {"entity_id": "camera.garage"})
    assert get.call_args.kwargs["width"] == 1024
    assert out.images == [{"media_type": "image/jpeg", "data": base64.b64encode(JPEG).decode()}]
    assert out.summary == "Snapshot of Garage"


@pytest.mark.parametrize(
    ("entity_id", "image", "error"),
    [
        ("light.kitchen", None, "camera"),
        ("camera.missing", None, "does not exist"),
        ("camera.garage", Image("text/html", b"<html>"), "not a picture"),
        ("camera.garage", Image("image/jpeg", b"x" * 3_600_000), "too large"),
    ],
)
async def test_snapshot_refuses_bad_input(hass: HomeAssistant, entity_id, image, error) -> None:
    hass.states.async_set("camera.garage", "idle")
    with patch(GET, return_value=image), pytest.raises(ToolError, match=error):
        await CameraSnapshot().run(_ctx(hass), {"entity_id": entity_id})


async def test_snapshot_camera_error(hass: HomeAssistant) -> None:
    hass.states.async_set("camera.garage", "idle")
    with (
        patch(GET, side_effect=HomeAssistantError("offline")),
        pytest.raises(ToolError, match="offline"),
    ):
        await CameraSnapshot().run(_ctx(hass), {"entity_id": "camera.garage"})


def test_camera_tool_follows_the_setting() -> None:
    assert "camera_snapshot" in {t.name for t in build_tools(entry_options())}
    assert "camera_snapshot" not in {t.name for t in build_tools(entry_options(camera_tools=False))}


IMG = {"media_type": "image/jpeg", "data": "QUJD"}
HISTORY = [
    {"role": "user", "content": "is the garage open?"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": "c1", "name": "camera_snapshot", "args": {}}],
    },
    {
        "role": "tool",
        "tool_call_id": "c1",
        "name": "camera_snapshot",
        "content": "{}",
        "images": [IMG],
    },
]


def test_anthropic_puts_the_picture_in_the_tool_result() -> None:
    msgs = to_anthropic_messages([_provider_view(m) for m in HISTORY])
    block = msgs[-1]["content"][-1]
    assert block["type"] == "tool_result"
    assert block["content"][1]["source"] == {
        "type": "base64",
        "media_type": "image/jpeg",
        "data": "QUJD",
    }


def test_openai_sends_the_picture_after_the_tool_results() -> None:
    msgs = to_openai_messages("sys", [_provider_view(m) for m in HISTORY])
    assert msgs[-2]["role"] == "tool"
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"][1]["image_url"]["url"] == "data:image/jpeg;base64,QUJD"


def test_pictures_are_dropped_after_the_turn() -> None:
    history = [dict(m) for m in HISTORY]
    _drop_images(history)
    assert "images" not in history[-1] and "no longer attached" in history[-1]["content"]


PHOTO_TURN = [{"role": "user", "content": "what is this?", "images": [IMG], "photos": 1}]


def test_anthropic_puts_uploaded_photos_before_the_text() -> None:
    msgs = to_anthropic_messages([_provider_view(m) for m in PHOTO_TURN])
    blocks = msgs[0]["content"]
    assert blocks[0]["type"] == "image" and blocks[0]["source"]["data"] == "QUJD"
    assert blocks[-1]["type"] == "text" and blocks[-1]["text"] == "what is this?"


def test_openai_sends_uploaded_photos_as_image_parts() -> None:
    msgs = to_openai_messages("sys", [_provider_view(m) for m in PHOTO_TURN])
    parts = msgs[-1]["content"]
    assert parts[0]["image_url"]["url"] == "data:image/jpeg;base64,QUJD"
    assert parts[-1] == {"type": "text", "text": "what is this?"}


def test_provider_view_keeps_display_keys_out() -> None:
    view = _provider_view({**PHOTO_TURN[0], "display": "what is this?"})
    assert set(view) == {"role", "content", "images"}


def test_prompt_log_counts_pictures_instead_of_writing_them() -> None:
    from custom_components.llm_agent.agent import _loggable

    logged = _loggable(PHOTO_TURN[0])
    assert logged["images"] == "(1 picture(s) not logged)"
    assert "QUJD" not in str(logged)
