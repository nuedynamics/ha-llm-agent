"""Approve from your phone: an actionable notification through the Home Assistant app.

The household picks one notify action (notify.mobile_app_<phone>). An approval goes to
that phone when nobody has the chat open, when it has waited a minute in the panel, when
an automation's request needs it, or when a household member's chat needs an admin. The
notification has Approve and Deny buttons. Each one carries a random token that only that
notification knows, and a press only counts when it comes from an admin's phone.
"""

from __future__ import annotations

from collections.abc import Callable
import contextlib
import logging
import secrets
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback

from .const import CONF_APPROVAL_PHONE

_LOGGER = logging.getLogger(__name__)

EVENT = "mobile_app_notification_action"
APPROVE = "LLM_AGENT_APPROVE_"
DENY = "LLM_AGENT_DENY_"
MAX_TEXT = 300


def phone_service(options: dict[str, Any]) -> str | None:
    """The notify action's name without "notify.", or None when no phone is set."""
    name = str(options.get(CONF_APPROVAL_PHONE) or "").strip()
    if name.startswith("notify."):
        name = name[len("notify.") :]
    return name or None


class PhoneApprovals:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        # token -> callback(approved) for each approval waiting on the phone
        self._waiting: dict[str, Callable[[bool], bool]] = {}
        self._unsub = hass.bus.async_listen(EVENT, self._on_action)

    def close(self) -> None:
        self._unsub()
        self._waiting.clear()

    async def send(
        self,
        options: dict[str, Any],
        title: str,
        text: str,
        answer: Callable[[bool], bool],
    ) -> str | None:
        """Send the notification. Returns its token, or None when no phone is set or the
        notify action failed."""
        service = phone_service(options)
        if not service or not self.hass.services.has_service("notify", service):
            return None
        token = secrets.token_urlsafe(16)
        self._waiting[token] = answer
        message = text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "…"
        try:
            await self.hass.services.async_call(
                "notify",
                service,
                {
                    "title": title[:80],
                    "message": message,
                    "data": {
                        "tag": f"llm_agent_{token}",
                        "actions": [
                            {"action": APPROVE + token, "title": "Approve"},
                            {"action": DENY + token, "title": "Deny"},
                        ],
                    },
                },
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001 - the panel can still answer
            _LOGGER.warning("Could not send the approval to %s: %s", service, err)
            self._waiting.pop(token, None)
            return None
        return token

    async def done(self, options: dict[str, Any], token: str | None) -> None:
        """Forget the token and clear the notification once the approval is answered."""
        if token is None or self._waiting.pop(token, None) is None:
            return
        service = phone_service(options)
        if not service or not self.hass.services.has_service("notify", service):
            return
        with contextlib.suppress(Exception):  # only tidying up the phone
            await self.hass.services.async_call(
                "notify",
                service,
                {"message": "clear_notification", "data": {"tag": f"llm_agent_{token}"}},
                blocking=False,
            )

    @callback
    def _on_action(self, event: Event) -> None:
        action = str(event.data.get("action") or "")
        for prefix, approved in ((APPROVE, True), (DENY, False)):
            if action.startswith(prefix):
                token = action[len(prefix) :]
                if token in self._waiting:
                    self.hass.async_create_task(self._press(event, token, approved))
                return

    async def _press(self, event: Event, token: str, approved: bool) -> None:
        user_id = event.context.user_id
        user = await self.hass.auth.async_get_user(user_id) if user_id else None
        if user is None or not user.is_admin or not user.is_active:
            _LOGGER.warning("Ignored an approval press from a phone that isn't an admin's")
            return
        answer = self._waiting.pop(token, None)
        if answer is not None:
            answer(approved)
