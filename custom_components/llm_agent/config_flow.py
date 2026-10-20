"""Config and options flows: risk acknowledgement, providers and settings."""

from __future__ import annotations

import secrets
from typing import Any

import aiohttp
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    ObjectSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import probatio as vol

from .const import (
    APPROVAL_MODES,
    CONF_ACK,
    CONF_ALLOW_SHELL,
    CONF_APPROVAL_MODE,
    CONF_BACKUP_BEFORE_RISKY,
    CONF_BLOCK_INVALID_RESTART,
    CONF_EXTRA_PROMPT,
    CONF_MAX_STEPS,
    CONF_PRICE_OVERRIDES,
    CONF_PROTECT_SENSITIVE,
    CONF_PROVIDERS,
    DEFAULT_OPTIONS,
    DOMAIN,
    NAME,
)
from .providers.models import (
    DEFAULT_BASE_URLS,
    PROVIDER_NAMES,
    default_model,
    models_request,
    suggestions,
)

TYPE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[SelectOptionDict(value=k, label=v) for k, v in PROVIDER_NAMES.items()],
        mode=SelectSelectorMode.LIST,
    )
)


def _model_selector(provider_type: str) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=m["id"], label=m["label"])
                for m in suggestions(provider_type)
            ],
            custom_value=True,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _provider_schema(provider_type: str, current: dict[str, Any] | None = None) -> vol.Schema:
    cur = current or {}
    key_required = provider_type != "ollama"
    key_marker = vol.Required if key_required and not cur else vol.Optional
    return vol.Schema(
        {
            vol.Required("name", default=cur.get("name", PROVIDER_NAMES[provider_type])): str,
            key_marker("api_key"): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Required(
                "base_url",
                default=cur.get("base_url", DEFAULT_BASE_URLS[provider_type]),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
            vol.Required(
                "default_model",
                default=cur.get("default_model", default_model(provider_type)),
            ): _model_selector(provider_type),
        }
    )


async def validate_provider(hass: HomeAssistant, provider: dict[str, Any]) -> str | None:
    """Return an error key, or None if the provider answered."""
    session = async_get_clientsession(hass)
    url, headers = models_request(provider["type"], provider["base_url"], provider.get("api_key"))
    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status in (401, 403):
                return "invalid_auth"
            if resp.status >= 500:
                return "cannot_connect"
    except aiohttp.ClientError, TimeoutError:
        return "cannot_connect"
    return None


def _new_provider(
    provider_type: str, user_input: dict[str, Any], old: dict[str, Any] | None = None
) -> dict[str, Any]:
    provider = {
        "id": (old or {}).get("id") or secrets.token_hex(4),
        "type": provider_type,
        "name": user_input["name"].strip() or PROVIDER_NAMES[provider_type],
        "api_key": user_input.get("api_key") or (old or {}).get("api_key") or "",
        "base_url": user_input["base_url"].strip(),
        "default_model": str(user_input["default_model"]).strip(),
    }
    return provider


class LLMAgentConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._type = "anthropic"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_ACK):
                errors[CONF_ACK] = "must_acknowledge"
            else:
                self._type = user_input["type"]
                return await self.async_step_provider()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("type", default=self._type): TYPE_SELECTOR,
                    vol.Required(CONF_ACK, default=False): BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            provider = _new_provider(self._type, user_input)
            if error := await validate_provider(self.hass, provider):
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=NAME,
                    data={CONF_ACK: True},
                    options={**DEFAULT_OPTIONS, CONF_PROVIDERS: [provider]},
                )
        return self.async_show_form(
            step_id="provider",
            data_schema=_provider_schema(self._type),
            errors=errors,
            description_placeholders={"provider": PROVIDER_NAMES[self._type]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LLMAgentOptionsFlow()


class LLMAgentOptionsFlow(OptionsFlow):
    def __init__(self) -> None:
        self._type = "anthropic"
        self._editing: dict[str, Any] | None = None

    @property
    def _options(self) -> dict[str, Any]:
        return {**DEFAULT_OPTIONS, **self.config_entry.options}

    @property
    def _providers(self) -> list[dict[str, Any]]:
        return list(self._options.get(CONF_PROVIDERS, []))

    def _save(self, **changes: Any) -> ConfigFlowResult:
        return self.async_create_entry(data={**self._options, **changes})

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        menu = ["settings", "add_provider"]
        if self._providers:
            menu += ["edit_provider", "remove_provider"]
        return self.async_show_menu(step_id="init", menu_options=menu)

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        opts = self._options
        if user_input is not None:
            user_input[CONF_MAX_STEPS] = int(user_input[CONF_MAX_STEPS])
            user_input.setdefault(CONF_EXTRA_PROMPT, "")
            user_input.setdefault(CONF_PRICE_OVERRIDES, {})
            if user_input[CONF_ALLOW_SHELL] and not opts.get(CONF_ALLOW_SHELL):
                self._pending = user_input
                return await self.async_step_confirm_shell()
            return self._save(**user_input)
        schema = vol.Schema(
            {
                vol.Required(CONF_APPROVAL_MODE, default=opts[CONF_APPROVAL_MODE]): SelectSelector(
                    SelectSelectorConfig(
                        options=APPROVAL_MODES,
                        translation_key=CONF_APPROVAL_MODE,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_BACKUP_BEFORE_RISKY, default=opts[CONF_BACKUP_BEFORE_RISKY]
                ): BooleanSelector(),
                vol.Required(
                    CONF_PROTECT_SENSITIVE, default=opts[CONF_PROTECT_SENSITIVE]
                ): BooleanSelector(),
                vol.Required(
                    CONF_BLOCK_INVALID_RESTART, default=opts[CONF_BLOCK_INVALID_RESTART]
                ): BooleanSelector(),
                vol.Required(CONF_ALLOW_SHELL, default=opts[CONF_ALLOW_SHELL]): BooleanSelector(),
                vol.Required(CONF_MAX_STEPS, default=opts[CONF_MAX_STEPS]): NumberSelector(
                    NumberSelectorConfig(min=1, max=200, step=1, mode=NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_EXTRA_PROMPT,
                    description={"suggested_value": opts.get(CONF_EXTRA_PROMPT)},
                ): TextSelector(TextSelectorConfig(multiline=True)),
                vol.Optional(
                    CONF_PRICE_OVERRIDES,
                    description={"suggested_value": opts.get(CONF_PRICE_OVERRIDES)},
                ): ObjectSelector(),
            }
        )
        return self.async_show_form(step_id="settings", data_schema=schema)

    async def async_step_confirm_shell(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            pending = self._pending
            if not user_input.get("confirm"):
                pending[CONF_ALLOW_SHELL] = False
            return self._save(**pending)
        return self.async_show_form(
            step_id="confirm_shell",
            data_schema=vol.Schema({vol.Required("confirm", default=False): BooleanSelector()}),
        )

    async def async_step_add_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._type = user_input["type"]
            self._editing = None
            return await self.async_step_provider()
        return self.async_show_form(
            step_id="add_provider",
            data_schema=vol.Schema({vol.Required("type", default=self._type): TYPE_SELECTOR}),
        )

    def _provider_choice(self) -> SelectSelector:
        return SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(
                        value=p["id"],
                        label=f"{p['name']} ({PROVIDER_NAMES.get(p['type'], p['type'])})",
                    )
                    for p in self._providers
                ],
                mode=SelectSelectorMode.LIST,
            )
        )

    async def async_step_edit_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._editing = next(p for p in self._providers if p["id"] == user_input["provider"])
            self._type = self._editing["type"]
            return await self.async_step_provider()
        return self.async_show_form(
            step_id="edit_provider",
            data_schema=vol.Schema({vol.Required("provider"): self._provider_choice()}),
        )

    async def async_step_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            provider = _new_provider(self._type, user_input, self._editing)
            if error := await validate_provider(self.hass, provider):
                errors["base"] = error
            else:
                providers = [p for p in self._providers if p["id"] != provider["id"]]
                if self._editing:
                    index = next(
                        i for i, p in enumerate(self._providers) if p["id"] == provider["id"]
                    )
                    providers.insert(index, provider)
                else:
                    providers.append(provider)
                return self._save(**{CONF_PROVIDERS: providers})
        return self.async_show_form(
            step_id="provider",
            data_schema=_provider_schema(self._type, self._editing),
            errors=errors,
            description_placeholders={"provider": PROVIDER_NAMES[self._type]},
        )

    async def async_step_remove_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            providers = [p for p in self._providers if p["id"] != user_input["provider"]]
            return self._save(**{CONF_PROVIDERS: providers})
        return self.async_show_form(
            step_id="remove_provider",
            data_schema=vol.Schema({vol.Required("provider"): self._provider_choice()}),
        )
