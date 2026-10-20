"""Real-model check: chat over the WebSocket API and verify what actually changed in HA.

Runs inside the HA container (which has aiohttp). Every approval request is approved.
Usage: python3 live_check.py <access-token>
"""

from __future__ import annotations

import asyncio
import json
import sys
import time

import aiohttp

WS = "ws://127.0.0.1:8123/api/websocket"
TURN_TIMEOUT = 300


class Client:
    def __init__(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        self.ws = ws
        self.next_id = 1

    async def send(self, payload: dict) -> int:
        msg_id = self.next_id
        self.next_id += 1
        await self.ws.send_json({"id": msg_id, **payload})
        return msg_id

    async def call(self, payload: dict) -> dict:
        msg_id = await self.send(payload)
        while True:
            msg = await self.ws.receive_json()
            if msg.get("id") == msg_id and msg["type"] == "result":
                if not msg["success"]:
                    raise RuntimeError(msg["error"])
                return msg["result"]

    async def chat(self, text: str, conv_id: str | None) -> tuple[str, str, list[str]]:
        """Run one turn, approving everything. Returns (conversation id, reply, tools used)."""
        msg_id = await self.send(
            {"type": "llm_agent/chat", "text": text, "conversation_id": conv_id}
        )
        reply, tools = "", []
        self.reviews: list[dict] = []
        self.asked = 0
        self.usage: dict = {}
        deadline = time.monotonic() + TURN_TIMEOUT
        while time.monotonic() < deadline:
            msg = await asyncio.wait_for(self.ws.receive_json(), TURN_TIMEOUT)
            if msg.get("id") != msg_id:
                continue
            if msg["type"] == "result":
                if not msg["success"]:
                    raise RuntimeError(msg["error"])
                conv_id = msg["result"]["conversation_id"]
                continue
            ev = msg["event"]
            if ev["type"] == "delta":
                reply += ev["text"]
            elif ev["type"] == "tool_start":
                tools.append(ev["name"])
                print(f"     call {ev['name']} {json.dumps(ev['args'])[:600]}")
            elif ev["type"] == "tool_result":
                mark = "ok " if ev["ok"] else "ERR"
                print(f"       {mark} {ev['preview'][:300]!r}")
            elif ev["type"] == "review":
                self.reviews.append(ev)
                print(f"       reviewer {ev['decision']}: {ev['reason']!r}")
            elif ev["type"] == "approval":
                self.asked += 1
                await self.send(
                    {
                        "type": "llm_agent/approve",
                        "conversation_id": conv_id,
                        "call_id": ev["call_id"],
                        "approved": True,
                    }
                )
            elif ev["type"] == "error":
                raise RuntimeError(ev["message"])
            elif ev["type"] == "done":
                self.usage = ev.get("usage") or {}
                return conv_id, reply, tools
        raise TimeoutError(text)


async def state(client: Client, entity_id: str) -> dict | None:
    states = await client.call({"type": "get_states"})
    return next((s for s in states if s["entity_id"] == entity_id), None)


async def set_options(session: aiohttp.ClientSession, token: str, **changes) -> None:
    """Change integration settings through the options flow, as a person would."""
    base = WS.replace("ws://", "http://").rsplit("/api/", 1)[0]
    head = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{base}/api/config/config_entries/entry", headers=head) as resp:
        entry = next(e for e in await resp.json() if e["domain"] == "llm_agent")
    flow_url = f"{base}/api/config/config_entries/options/flow"
    async with session.post(flow_url, json={"handler": entry["entry_id"]}, headers=head) as resp:
        flow = await resp.json()
    url = f"{flow_url}/{flow['flow_id']}"
    async with session.post(url, json={"next_step_id": "settings"}, headers=head) as resp:
        await resp.json()
    async with session.post(url, json=changes, headers=head) as resp:
        done = await resp.json()
    if done.get("type") != "create_entry":
        raise RuntimeError(f"options flow failed: {done}")
    await asyncio.sleep(2)  # the entry reloads


async def main(token: str) -> int:
    results: list[tuple[str, bool, str]] = []
    async with aiohttp.ClientSession() as session, session.ws_connect(WS) as ws:
        await ws.receive_json()
        await ws.send_json({"type": "auth", "access_token": token})
        assert (await ws.receive_json())["type"] == "auth_ok"
        c = Client(ws)

        async def scenario(name: str, prompt: str, check, conv: str | None = None):
            started = time.monotonic()
            try:
                conv, reply, tools = await c.chat(prompt, conv)
                ok, why = await check(reply)
            except Exception as err:  # noqa: BLE001 - report every failure
                ok, why, tools, reply = False, repr(err), [], ""
            took = time.monotonic() - started
            results.append((name, ok, why))
            print(f"{'PASS' if ok else 'FAIL'} {name} ({took:.0f}s) tools={tools}")
            print(f"     reply: {reply.strip()[:300]!r}")
            if not ok:
                print(f"     why: {why}")
            return conv

        async def switch_on(_reply):
            s = await state(c, "input_boolean.e2e_switch")
            return (s and s["state"] == "on"), f"state={s and s['state']}"

        async def says_on(reply):
            return " on" in f" {reply.lower()}", "reply should say it is on"

        async def automation_made(_reply):
            states = await c.call({"type": "get_states"})
            autos = [s for s in states if s["entity_id"].startswith("automation.")]
            names = [s["attributes"].get("friendly_name", "") for s in autos]
            return any("night" in n.lower() for n in names), f"automations={names}"

        async def dashboard_made(_reply):
            boards = await c.call({"type": "lovelace/dashboards/list"})
            urls = [b["url_path"] for b in boards]
            return any("e2e" in u for u in urls), f"dashboards={urls}"

        conv = await scenario("control", "Turn on the E2E switch, please.", switch_on)
        await scenario("question", "Is the E2E switch on or off right now?", says_on, conv)
        await scenario(
            "automation",
            "Create an automation called 'E2E night off' that turns off the E2E switch "
            "every day at 23:00.",
            automation_made,
        )
        await scenario(
            "dashboard",
            "Create a new dashboard called 'E2E Test' with one entities card that shows "
            "the E2E switch.",
            dashboard_made,
        )

        async def scenario_tools(name, prompt, want, words):
            async def check(reply):
                missing = [w for w in words if w not in reply.lower()]
                return not missing, f"reply lacks {missing}"

            started = time.monotonic()
            try:
                _, reply, tools = await c.chat(prompt, None)
                ok, why = await check(reply)
                if want not in tools:
                    ok, why = False, f"{want} not used"
            except Exception as err:  # noqa: BLE001
                ok, why, tools, reply = False, repr(err), [], ""
            results.append((name, ok, why))
            print(
                f"{'PASS' if ok else 'FAIL'} {name} ({time.monotonic() - started:.0f}s) tools={tools}"
            )
            print(f"     reply: {reply.strip()[:300]!r}")
            if not ok:
                print(f"     why: {why}")

        await scenario_tools(
            "debug",
            "Has the automation 'E2E night off' run yet? Check its traces.",
            "get_traces",
            [],
        )
        await scenario_tools(
            "docs",
            "Look up the Home Assistant docs page for the input_boolean integration and tell "
            "me what the 'initial' option does.",
            "web_fetch",
            ["initial"],
        )
        await scenario_tools(
            "search",
            "Search the web for how people fix Zigbee devices that keep going unavailable in "
            "Home Assistant, and list two suggestions with their links.",
            "web_search",
            ["http"],
        )

        # Reviewer mode: a second model decides risky actions the person asked for.
        await set_options(session, token, approval_mode="reviewer")

        async def dashboard_gone(_reply):
            boards = await c.call({"type": "lovelace/dashboards/list"})
            urls = [b["url_path"] for b in boards]
            approved = [r for r in c.reviews if r["decision"] == "approve"]
            cost = (c.usage.get("review") or {}).get("cost")
            if any("e2e" in u for u in urls):
                return False, f"dashboard still there: {urls}"
            if not approved or c.asked:
                return False, f"reviews={c.reviews} asked={c.asked}"
            return cost is not None, f"reviewer cost={cost}"

        await scenario(
            "reviewer", "Delete the 'E2E Test' dashboard, I don't need it.", dashboard_gone
        )
        await set_options(session, token, approval_mode="ask_risky")
    failed = [r for r in results if not r[1]]
    print(json.dumps({"passed": len(results) - len(failed), "failed": len(failed)}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1])))
