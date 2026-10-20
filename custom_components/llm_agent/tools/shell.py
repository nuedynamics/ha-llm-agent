"""Shell commands (off unless the admin enables them in options)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from ..approval import Risk
from . import Tool, ToolContext, ToolError, ToolOutput, num_arg, obj

MAX_OUTPUT = 20000


class ShellTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            "shell",
            "Run a shell command inside the Home Assistant container (cwd = config dir). "
            "Output is truncated. Prefer dedicated tools when one exists.",
            obj(
                {
                    "command": {"type": "string"},
                    "timeout": {
                        "type": "integer",
                        "default": 60,
                        "description": "seconds, max 600",
                    },
                },
                ["command"],
            ),
        )

    def classify(self, ctx: ToolContext, args: dict[str, Any]) -> Risk:
        return Risk.risky("runs a shell command")

    async def run(self, ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
        if not ctx.options.get("allow_shell"):
            raise ToolError("Shell access is turned off in the LLM Agent options")
        timeout = num_arg(args, "timeout", 60, 1, 600)
        env = {k: v for k, v in os.environ.items() if "TOKEN" not in k and "KEY" not in k}
        proc = await asyncio.create_subprocess_shell(
            args["command"],
            cwd=ctx.hass.config.path(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            stdin=asyncio.subprocess.DEVNULL,
            env=env,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise ToolError(f"Command timed out after {timeout}s") from None
        text = out.decode("utf-8", "replace")
        if len(text) > MAX_OUTPUT:
            text = text[: MAX_OUTPUT // 2] + "\n… (truncated) …\n" + text[-MAX_OUTPUT // 2 :]
        return ToolOutput({"exit_code": proc.returncode, "output": text})
