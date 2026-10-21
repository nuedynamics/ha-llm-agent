"""Sign in with a ChatGPT subscription (experimental).

Uses the same device-code sign-in as OpenAI's open-source Codex CLI: Home Assistant
shows a code, the person enters it at auth.openai.com, and we receive tokens for the
ChatGPT backend. OpenAI does not document this for other apps, so it may stop working.

Tokens live in their own storage file, not in the integration options: refreshed tokens
must be saved each time (a refresh token works once), and saving options reloads the
integration.
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
import json
import logging
import time
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .providers.base import ProviderError

_LOGGER = logging.getLogger(__name__)

ISSUER = "https://auth.openai.com"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"  # the Codex CLI's public client id
VERIFY_URL = f"{ISSUER}/codex/device"
REDIRECT_URI = f"{ISSUER}/deviceauth/callback"
LOGIN_TIMEOUT = 15 * 60
REFRESH_EARLY = 5 * 60  # refresh when the access token has less than this left
TIMEOUT = aiohttp.ClientTimeout(total=30)
_STORE_KEY = f"{DOMAIN}.chatgpt_auth"
_DATA_KEY = f"{DOMAIN}_chatgpt_auth"
SIGN_IN_AGAIN = (
    "ChatGPT: sign in again. Open Configure → Edit provider, choose this provider and "
    "tick “Sign in again”."
)


@dataclass(slots=True)
class DeviceLogin:
    device_auth_id: str
    user_code: str
    interval: float


def _claims(jwt: str) -> dict[str, Any]:
    """The payload of a JWT, unverified: it came straight from OpenAI over TLS and is
    only read for the account id and expiry."""
    try:
        payload = jwt.split(".")[1]
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except IndexError, ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def tokens_from(body: Any, old: dict[str, Any] | None = None) -> dict[str, Any]:
    """The parts of a token response we keep. A refresh may omit the refresh token or
    id token; then the old ones stay."""
    if not isinstance(body, dict) or not isinstance(body.get("access_token"), str):
        raise ProviderError("ChatGPT: the sign-in service gave no access token")
    old = old or {}
    access = body["access_token"]
    id_claims = _claims(body["id_token"]) if isinstance(body.get("id_token"), str) else {}
    auth = id_claims.get("https://api.openai.com/auth")
    account = (auth or {}).get("chatgpt_account_id") if isinstance(auth, dict) else None
    exp = _claims(access).get("exp")
    return {
        "access_token": access,
        "refresh_token": body.get("refresh_token") or old.get("refresh_token") or "",
        "account_id": account or old.get("account_id") or "",
        "expires_at": float(exp) if isinstance(exp, (int, float)) else time.time() + 3600,
    }


async def start_login(session: aiohttp.ClientSession) -> DeviceLogin:
    url = f"{ISSUER}/api/accounts/deviceauth/usercode"
    try:
        async with session.post(url, json={"client_id": CLIENT_ID}, timeout=TIMEOUT) as resp:
            if resp.status >= 400:
                raise ProviderError(f"ChatGPT: could not start sign-in (HTTP {resp.status})")
            body = await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise ProviderError(f"ChatGPT: could not start sign-in ({type(err).__name__})") from err
    if not isinstance(body, dict):
        raise ProviderError("ChatGPT: the sign-in service gave no code")
    code = body.get("user_code") or body.get("usercode")
    if not isinstance(code, str) or not isinstance(body.get("device_auth_id"), str):
        raise ProviderError("ChatGPT: the sign-in service gave no code")
    try:
        interval = min(max(float(body.get("interval") or 5), 1.0), 30.0)
    except TypeError, ValueError:
        interval = 5.0
    return DeviceLogin(body["device_auth_id"], code, interval)


async def finish_login(
    session: aiohttp.ClientSession, login: DeviceLogin, give_up_after: float = LOGIN_TIMEOUT
) -> dict[str, Any]:
    """Wait until the person has entered the code, then fetch the tokens."""
    url = f"{ISSUER}/api/accounts/deviceauth/token"
    deadline = time.monotonic() + give_up_after
    body: Any = None
    while True:
        try:
            async with session.post(
                url,
                json={"device_auth_id": login.device_auth_id, "user_code": login.user_code},
                timeout=TIMEOUT,
            ) as resp:
                if resp.status < 400:
                    body = await resp.json(content_type=None)
                    break
                if resp.status not in (403, 404):  # 403/404 mean "not entered yet"
                    raise ProviderError(f"ChatGPT: sign-in failed (HTTP {resp.status})")
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            _LOGGER.debug("ChatGPT sign-in poll failed: %s", type(err).__name__)
        if time.monotonic() + login.interval > deadline:
            raise ProviderError("ChatGPT: the code expired before it was entered")
        await asyncio.sleep(login.interval)
    if not isinstance(body, dict) or not all(
        isinstance(body.get(k), str) for k in ("authorization_code", "code_verifier")
    ):
        raise ProviderError("ChatGPT: the sign-in service gave an unexpected answer")
    form = {
        "grant_type": "authorization_code",
        "code": body["authorization_code"],
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": body["code_verifier"],
    }
    return tokens_from(await _token_request(session, data=form))


async def _token_request(session: aiohttp.ClientSession, **kwargs: Any) -> Any:
    try:
        async with session.post(f"{ISSUER}/oauth/token", timeout=TIMEOUT, **kwargs) as resp:
            if resp.status in (400, 401):
                raise ProviderError(SIGN_IN_AGAIN)
            if resp.status >= 400:
                raise ProviderError(f"ChatGPT: the sign-in service failed (HTTP {resp.status})")
            return await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        # Never include the response: it may echo credentials.
        raise ProviderError(
            f"ChatGPT: could not reach the sign-in service ({type(err).__name__})"
        ) from err


class ChatGPTAuth:
    """Stored tokens for every ChatGPT provider, refreshed one at a time."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, 1, _STORE_KEY, private=True)
        self._data: dict[str, Any] | None = None
        self._locks: dict[str, asyncio.Lock] = {}

    async def _load(self) -> dict[str, Any]:
        if self._data is None:
            self._data = await self._store.async_load() or {}
        return self._data

    async def save(self, provider_id: str, tokens: dict[str, Any]) -> None:
        data = await self._load()
        data[provider_id] = tokens
        await self._store.async_save(data)

    async def remove(self, provider_id: str) -> None:
        data = await self._load()
        if data.pop(provider_id, None) is not None:
            await self._store.async_save(data)

    async def clear(self) -> None:
        """Delete every stored sign-in (the integration is being removed)."""
        self._data = {}
        await self._store.async_remove()

    async def access(self, provider_id: str) -> tuple[str, str]:
        """(access token, account id), refreshed first if it is about to expire."""
        async with self._locks.setdefault(provider_id, asyncio.Lock()):
            data = await self._load()
            tokens = data.get(provider_id)
            if not tokens:
                raise ProviderError(SIGN_IN_AGAIN)
            if tokens["expires_at"] - time.time() < REFRESH_EARLY:
                if not tokens.get("refresh_token"):
                    raise ProviderError(SIGN_IN_AGAIN)
                body = await _token_request(
                    async_get_clientsession(self.hass),
                    json={
                        "client_id": CLIENT_ID,
                        "grant_type": "refresh_token",
                        "refresh_token": tokens["refresh_token"],
                    },
                )
                tokens = tokens_from(body, tokens)
                await self.save(provider_id, tokens)
            return tokens["access_token"], tokens["account_id"]


def get_auth(hass: HomeAssistant) -> ChatGPTAuth:
    if (auth := hass.data.get(_DATA_KEY)) is None:
        auth = hass.data[_DATA_KEY] = ChatGPTAuth(hass)
    return auth
