"""The llm_agent.ask action: ask the agent from an automation or script."""

from __future__ import annotations

import asyncio

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
import probatio as vol

from .agent import ChatRun, home_context
from .const import CONF_HOME_SUMMARY, DOMAIN, setting

ASK_TIMEOUT = 300  # seconds; an automation should not hang on a slow model

ASK_SCHEMA = vol.Schema(
    {
        vol.Required("prompt"): vol.All(str, vol.Length(min=1, max=20000)),
        vol.Optional("provider"): str,
        vol.Optional("model"): str,
        vol.Optional("conversation_id"): str,
        vol.Optional("title"): vol.All(str, vol.Length(min=1, max=120)),
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    async def ask(call: ServiceCall) -> ServiceResponse:
        agent = hass.data.get(DOMAIN)
        if agent is None:
            raise ServiceValidationError("LLM Agent is not set up")
        user_id = call.context.user_id
        if user_id:  # a person calling it (automations run without a user)
            user = await hass.auth.async_get_user(user_id)
            if user is None or not user.is_admin:
                raise Unauthorized(context=call.context)
        conv = None
        if call.data.get("conversation_id"):
            conv = await agent.store.get(call.data["conversation_id"])
            # A person continues their own chats (and unowned ones, as an admin); an
            # automation continues only the unowned chats that actions start.
            if conv is None or conv.get("user_id") not in (None, user_id):
                raise ServiceValidationError("No conversation with that id")
        providers = agent.providers()
        if not providers:
            raise ServiceValidationError("No AI provider is configured")
        if wanted := call.data.get("provider"):
            pconf = next((p for p in providers if wanted in (p.id, p.name)), None)
            if pconf is None:
                raise ServiceValidationError(f"No provider named {wanted}")
        else:
            pconf = agent.provider_config((conv or {}).get("provider_id"))
        if conv is not None and conv["id"] in agent.runs:
            raise ServiceValidationError("That conversation is already running")
        if conv is None:
            context = home_context(hass) if setting(agent.options, CONF_HOME_SUMMARY) else ""
            conv = await agent.store.create(pconf.id, pconf.default_model, context, user_id)
            conv["source"] = "action"
            if call.data.get("title"):
                conv["title"] = call.data["title"]
        elif conv.get("provider_id") != pconf.id:
            conv["provider_id"] = pconf.id
            conv["model"] = pconf.default_model  # the old model belongs to the old provider
        if call.data.get("model"):
            conv["model"] = call.data["model"]

        run = ChatRun(agent, conv, user_id, unattended=True)
        errors: list[str] = []
        run.listeners.add(lambda e: errors.append(e["message"]) if e["type"] == "error" else None)
        start = len(conv["messages"])
        agent.runs[conv["id"]] = run

        async def _run() -> None:
            try:
                await run.run(call.data["prompt"])
            finally:
                # Only once the turn has really ended, so no second turn can overlap it.
                if agent.runs.get(conv["id"]) is run:
                    agent.runs.pop(conv["id"], None)

        run.task = hass.async_create_task(_run(), "llm_agent_ask")
        try:
            async with asyncio.timeout(ASK_TIMEOUT):
                await asyncio.shield(run.task)
        except TimeoutError as err:
            run.task.cancel()
            raise HomeAssistantError(f"No answer within {ASK_TIMEOUT} seconds") from err
        except asyncio.CancelledError:
            run.task.cancel()  # the automation was stopped: stop the agent too
            raise
        except Exception as err:
            raise HomeAssistantError(f"The request failed: {err}") from err
        if run.task.cancelled():
            raise HomeAssistantError("The request was stopped")
        if errors:
            raise HomeAssistantError(errors[-1])
        reply = "\n\n".join(
            m["content"]
            for m in conv["messages"][start:]
            if m["role"] == "assistant" and m.get("content")
        )
        return {"response": reply, "conversation_id": conv["id"]}

    hass.services.async_register(
        DOMAIN, "ask", ask, schema=ASK_SCHEMA, supports_response=SupportsResponse.ONLY
    )
