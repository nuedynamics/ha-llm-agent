"""ChatGPT sign-in and token refresh, with recorded-shape responses only (no OpenAI)."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.llm_agent import chatgpt_auth
from custom_components.llm_agent.chatgpt_auth import (
    CLIENT_ID,
    REDIRECT_URI,
    SIGN_IN_AGAIN,
    DeviceLogin,
    finish_login,
    get_auth,
    start_login,
    tokens_from,
)
from custom_components.llm_agent.providers import ProviderError


def _jwt(claims: dict[str, Any]) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"e30.{payload}.sig"


def _tokens(exp: float, account: str = "acct-1", refresh: str | None = "r1") -> dict[str, Any]:
    body = {
        "access_token": _jwt({"exp": exp}),
        "id_token": _jwt({"https://api.openai.com/auth": {"chatgpt_account_id": account}}),
    }
    if refresh:
        body["refresh_token"] = refresh
    return body


class JSONResponse:
    def __init__(self, status: int, body: Any = None) -> None:
        self.status = status
        self._body = body

    async def json(self, content_type: str | None = None) -> Any:
        return self._body

    async def __aenter__(self) -> JSONResponse:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None


class JSONSession:
    def __init__(self, responses: list[JSONResponse]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> JSONResponse:
        self.requests.append({"url": url, **kwargs})
        return self.responses.pop(0)


def test_tokens_keep_account_expiry_and_old_refresh_token() -> None:
    tokens = tokens_from(_tokens(1234.0))
    assert tokens["account_id"] == "acct-1" and tokens["expires_at"] == 1234.0
    assert tokens["refresh_token"] == "r1"
    # A refresh that leaves out the refresh and id tokens keeps the old ones.
    again = tokens_from({"access_token": _jwt({"exp": 9999})}, tokens)
    assert again["refresh_token"] == "r1" and again["account_id"] == "acct-1"
    with pytest.raises(ProviderError):
        tokens_from({"error": "x"})


async def test_start_login_reads_the_code_and_interval() -> None:
    session = JSONSession(
        [JSONResponse(200, {"device_auth_id": "d1", "usercode": "ABCD-1234", "interval": "7"})]
    )
    login = await start_login(session)
    assert login == DeviceLogin("d1", "ABCD-1234", 7.0)
    assert session.requests[0]["json"] == {"client_id": CLIENT_ID}
    with pytest.raises(ProviderError):
        await start_login(JSONSession([JSONResponse(200, ["unexpected"])]))
    with pytest.raises(ProviderError):
        await start_login(JSONSession([JSONResponse(500)]))


async def test_finish_login_waits_for_the_code_then_exchanges_it() -> None:
    session = JSONSession(
        [
            JSONResponse(403),
            JSONResponse(404),
            JSONResponse(200, {"authorization_code": "ac", "code_verifier": "cv"}),
            JSONResponse(200, _tokens(time.time() + 3600)),
        ]
    )
    with patch.object(chatgpt_auth.asyncio, "sleep", return_value=None):
        tokens = await finish_login(session, DeviceLogin("d1", "CODE", 1.0))
    assert tokens["account_id"] == "acct-1"
    exchange = session.requests[-1]
    assert exchange["url"].endswith("/oauth/token")
    assert exchange["data"] == {
        "grant_type": "authorization_code",
        "code": "ac",
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": "cv",
    }


async def test_finish_login_gives_up_when_the_code_expires() -> None:
    session = JSONSession([JSONResponse(403)])
    with pytest.raises(ProviderError, match="expired"):
        await finish_login(session, DeviceLogin("d1", "CODE", 5.0), give_up_after=1.0)


async def test_access_refreshes_once_and_saves_the_new_refresh_token(
    hass: HomeAssistant,
) -> None:
    auth = get_auth(hass)
    await auth.save("p1", tokens_from(_tokens(time.time() + 60)))  # about to expire
    session = JSONSession([JSONResponse(200, _tokens(time.time() + 3600, refresh="r2"))])
    with patch.object(chatgpt_auth, "async_get_clientsession", return_value=session):
        results = await asyncio.gather(auth.access("p1"), auth.access("p1"))
    assert len(session.requests) == 1  # the second caller used the refreshed token
    assert session.requests[0]["json"] == {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": "r1",
    }
    assert results[0] == results[1] and results[0][1] == "acct-1"
    assert (await auth._load())["p1"]["refresh_token"] == "r2"


async def test_refused_refresh_asks_to_sign_in_again(hass: HomeAssistant) -> None:
    auth = get_auth(hass)
    await auth.save("p1", tokens_from(_tokens(time.time() - 10)))
    session = JSONSession([JSONResponse(401, {"error": "refresh_token_reused"})])
    with (
        patch.object(chatgpt_auth, "async_get_clientsession", return_value=session),
        pytest.raises(ProviderError) as err,
    ):
        await auth.access("p1")
    assert str(err.value) == SIGN_IN_AGAIN
    with pytest.raises(ProviderError, match="sign in again"):
        await auth.access("missing")


async def test_remove_and_clear_drop_stored_sign_ins(hass: HomeAssistant) -> None:
    auth = get_auth(hass)
    await auth.save("p1", tokens_from(_tokens(time.time() + 3600)))
    await auth.remove("p1")
    with pytest.raises(ProviderError):
        await auth.access("p1")
    await auth.save("p2", tokens_from(_tokens(time.time() + 3600)))
    await auth.clear()
    assert await auth._load() == {}


def test_the_ai_cannot_read_the_stored_sign_in() -> None:
    from custom_components.llm_agent.tools.files import FileAccess

    assert FileAccess.is_sensitive(f".storage/{chatgpt_auth._STORE_KEY}")
