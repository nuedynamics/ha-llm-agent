"""Camera snapshots, so a vision model can look ("is the garage door open?")."""

from __future__ import annotations

import base64
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from ..const import CONF_CAMERA_TOOLS, setting
from . import Tool, ToolContext, ToolError, ToolOutput, obj

SNAPSHOT_WIDTH = 1024
MAX_IMAGE_BYTES = 3_500_000  # providers cap images at about 5 MB once base64-encoded
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp", "image/gif")


class CameraSnapshot(Tool):
    def __init__(self) -> None:
        super().__init__(
            "camera_snapshot",
            "Take a still image from a camera entity and look at it. Only works with "
            "models that can see images. Describe only what is visible; say when the "
            "picture is too dark or unclear to tell.",
            obj(
                {"entity_id": {"type": "string", "description": "a camera.* entity"}}, ["entity_id"]
            ),
        )

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        entity_id = str(args["entity_id"]).strip()
        if not entity_id.startswith("camera."):
            raise ToolError("camera_snapshot needs a camera.* entity")
        state = ctx.hass.states.get(entity_id)
        if state is None:
            raise ToolError(f"{entity_id} does not exist")
        # Imported here: the camera integration loads only in homes with cameras.
        from homeassistant.components.camera import async_get_image

        try:
            image = await async_get_image(ctx.hass, entity_id, timeout=15, width=SNAPSHOT_WIDTH)
        except HomeAssistantError as err:
            raise ToolError(f"Could not get an image from {entity_id}: {err}") from None
        media_type = (image.content_type or "").split(";")[0].strip().lower()
        if media_type not in IMAGE_TYPES:
            raise ToolError(f"{entity_id} returned {media_type or 'no image'}, not a picture")
        if len(image.content) > MAX_IMAGE_BYTES:
            raise ToolError(f"The image from {entity_id} is too large to send")
        name = state.name or entity_id
        return ToolOutput(
            {"entity_id": entity_id, "name": name, "image": "attached below"},
            summary=f"Snapshot of {name}",
            images=[{"media_type": media_type, "data": base64.b64encode(image.content).decode()}],
        )


def camera_tools(options: dict[str, Any]) -> list[Tool]:
    return [CameraSnapshot()] if setting(options, CONF_CAMERA_TOOLS) else []
