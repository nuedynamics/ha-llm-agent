"""Onboard a fresh HA instance and add LLM Agent pointed at the stub. Stdlib only.

Prints the token JSON (for the browser test) on success.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HA = sys.argv[1]  # e.g. http://127.0.0.1:18123
STUB = sys.argv[2]  # e.g. http://127.0.0.1:18080/v1
CLIENT = HA + "/"


def call(method: str, path: str, data=None, token: str | None = None, form: bool = False):
    headers = {}
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers["content-type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            headers["content-type"] = "application/json"
    if token:
        headers["authorization"] = f"Bearer {token}"
    req = urllib.request.Request(HA + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


for _ in range(180):
    try:
        call("GET", "/api/onboarding")
        break
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        time.sleep(1)
else:
    sys.exit("HA did not start")

code = call(
    "POST",
    "/api/onboarding/users",
    {
        "client_id": CLIENT,
        "name": "E2E",
        "username": "e2e",
        "password": "e2e-pass-123",
        "language": "en",
    },
)["auth_code"]
tokens = call(
    "POST",
    "/auth/token",
    {"grant_type": "authorization_code", "code": code, "client_id": CLIENT},
    form=True,
)
tok = tokens["access_token"]
call("POST", "/api/onboarding/core_config", {}, tok)
call("POST", "/api/onboarding/analytics", {}, tok)
call("POST", "/api/onboarding/integration", {"client_id": CLIENT, "redirect_uri": CLIENT}, tok)

flow = call("POST", "/api/config/config_entries/flow", {"handler": "llm_agent"}, tok)
flow = call(
    "POST",
    f"/api/config/config_entries/flow/{flow['flow_id']}",
    {"type": os.environ.get("LLM_TYPE", "openai"), "acknowledged_risks": True},
    tok,
)
flow = call(
    "POST",
    f"/api/config/config_entries/flow/{flow['flow_id']}",
    {
        "name": os.environ.get("LLM_NAME", "Stub"),
        "api_key": os.environ.get("LLM_KEY", "sk-stub"),
        "base_url": STUB,
        "default_model": os.environ.get("LLM_MODEL", "stub-model"),
    },
    tok,
)
if flow.get("type") != "create_entry":
    sys.exit(f"config flow failed: {flow}")

# Price the stub model through the options flow so the cost estimate path is exercised.
opt = call(
    "POST", "/api/config/config_entries/options/flow", {"handler": flow["result"]["entry_id"]}, tok
)
opt = call(
    "POST",
    f"/api/config/config_entries/options/flow/{opt['flow_id']}",
    {"next_step_id": "settings"},
    tok,
)
opt = call(
    "POST",
    f"/api/config/config_entries/options/flow/{opt['flow_id']}",
    {"price_overrides": {"stub-model": {"input": 1.0, "output": 2.0}}},
    tok,
)
if opt.get("type") != "create_entry":
    sys.exit(f"options flow failed: {opt}")
# Wait for startup to finish, so "Home Assistant is starting" toasts are gone.
for _ in range(120):
    if call("GET", "/api/config", token=tok).get("state") == "RUNNING":
        break
    time.sleep(1)
print(
    json.dumps(
        {
            **tokens,
            "hassUrl": HA,
            "clientId": CLIENT,
            "expires": int(time.time() * 1000) + tokens["expires_in"] * 1000,
        }
    )
)
