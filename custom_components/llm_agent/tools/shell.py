"""Shell commands (off unless the admin enables them in options)."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
from typing import Any

from ..approval import Risk
from . import Tool, ToolContext, ToolError, ToolOutput, num_arg, obj

MAX_OUTPUT = 20000
HALF = MAX_OUTPUT // 2  # bytes kept from the start and from the end


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
            start_new_session=True,  # its own process group, so stopping it stops children
        )
        head, tail = bytearray(), bytearray()
        total = 0

        async def drain() -> None:
            # Keep the first and last bytes only: a noisy command can't fill HA's memory.
            nonlocal total
            assert proc.stdout is not None
            while chunk := await proc.stdout.read(65536):
                total += len(chunk)
                room = HALF - len(head)
                if room > 0:
                    head.extend(chunk[:room])
                    chunk = chunk[room:]
                tail.extend(chunk)
                del tail[:-HALF]
            await proc.wait()

        try:
            await asyncio.wait_for(drain(), timeout)
        except TimeoutError:
            await _stop(proc)
            raise ToolError(f"Command timed out after {timeout}s") from None
        except BaseException:
            await _stop(proc)  # Stop pressed: the command doesn't keep running
            raise
        text = head.decode("utf-8", "replace")
        if total > len(head) + len(tail):
            text += "\n… (truncated) …\n"
        text += tail.decode("utf-8", "replace")
        return ToolOutput({"exit_code": proc.returncode, "output": text})


async def _stop(proc: asyncio.subprocess.Process) -> None:
    """Kill the command and everything it started (never HA's own group)."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        if os.getpgid(proc.pid) != os.getpgrp():
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    with contextlib.suppress(Exception):
        await asyncio.shield(asyncio.wait_for(proc.wait(), 5))
