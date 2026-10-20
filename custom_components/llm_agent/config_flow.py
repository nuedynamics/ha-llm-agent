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
from homeassistant.data_entry_flow import section
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
from homeassistant.util import dt as dt_util
import probatio as vol

from .const import (
    APPROVAL_MODES,
    CONF_ACK,
    CONF_ALLOW_SHELL,
    CONF_ALWAYS_ASK,
    CONF_APPROVAL_MODE,
    CONF_AUDIT_MB,
    CONF_AUTO_DELETE_DAYS,
    CONF_BACKUP_BEFORE_RISKY,
    CONF_BLOCK_INVALID_RESTART,
    CONF_CACHE_CHATS,
    CONF_COMPACT_AT,
    CONF_DAILY_CAP,
    CONF_EXTRA_PROMPT,
    CONF_HOME_SUMMARY,
    CONF_KEEP_TURNS,
    CONF_LOG_PROMPTS,
    CONF_MAX_CHATS,
    CONF_MAX_REPLY_TOKENS,
    CONF_MAX_STEPS,
    CONF_PRICE_OVERRIDES,
    CONF_PROTECT_SENSITIVE,
    CONF_PROVIDERS,
    CONF_RETRIES,
    CONF_REVIEWER_MODEL,
    CONF_REVIEWER_PROVIDER,
    CONF_SEARCH_BACKEND,
    CONF_SEARCH_KEY,
    CONF_SEARXNG_URL,
    CONF_TIMEOUT,
    CONF_UNDO_DAYS,
    CONF_UNDO_KEEP,
    CONF_UNDO_MB,
    CONF_WEB_ALLOW_LAN,
    CONF_WEB_TOOLS,
    DEFAULT_OPTIONS,
    DOMAIN,
    NAME,
    RANGES,
    SAME_PROVIDER,
    SEARCH_BACKENDS,
    setting,
)
from .providers.models import (
    DEFAULT_BASE_URLS,
    PRICES_CHECKED,
    PROVIDER_NAMES,
    default_model,
    models_request,
    suggestions,
)
from .tools.web import search_backend

TYPE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[SelectOptionDict(value=k, label=v) for k, v in PROVIDER_NAMES.items()],
        mode=SelectSelectorMode.LIST,
    )
)


def _size(n: int) -> str:
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / 1024 / 1024:.1f} MB"


def _number(key: str, step: float = 1, unit: str | None = None) -> NumberSelector:
    lo, hi = RANGES[key]
    config = NumberSelectorConfig(min=lo, max=hi, step=step, mode=NumberSelectorMode.BOX)
    if unit:
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


# section -> (collapsed, keys). The common settings stay open at the top.
SECTIONS: dict[str, tuple[bool, list[str]]] = {
    "safety": (
        False,
        [
            CONF_BACKUP_BEFORE_RISKY,
            CONF_PROTECT_SENSITIVE,
            CONF_BLOCK_INVALID_RESTART,
            CONF_ALLOW_SHELL,
        ],
    ),
    "cost": (False, [CONF_DAILY_CAP, CONF_MAX_STEPS, CONF_MAX_REPLY_TOKENS, CONF_PRICE_OVERRIDES]),
    "context": (True, [CONF_COMPACT_AT, CONF_KEEP_TURNS, CONF_HOME_SUMMARY]),
    "storage": (
        True,
        [
            CONF_CACHE_CHATS,
            CONF_MAX_CHATS,
            CONF_AUTO_DELETE_DAYS,
            CONF_UNDO_MB,
            CONF_UNDO_KEEP,
            CONF_UNDO_DAYS,
            CONF_AUDIT_MB,
        ],
    ),
    "connection": (True, [CONF_TIMEOUT, CONF_RETRIES]),
    "reviewer": (True, [CONF_REVIEWER_PROVIDER, CONF_REVIEWER_MODEL, CONF_ALWAYS_ASK]),
    "web": (
        True,
        [
            CONF_WEB_TOOLS,
            CONF_WEB_ALLOW_LAN,
            CONF_SEARCH_BACKEND,
            CONF_SEARXNG_URL,
            CONF_SEARCH_KEY,
        ],
    ),
    "debugging": (True, [CONF_LOG_PROMPTS]),
}

_UNITS = {
    CONF_DAILY_CAP: (0.5, "USD"),
    CONF_MAX_REPLY_TOKENS: (256, "tokens"),
    CONF_COMPACT_AT: (1000, "tokens"),
    CONF_AUTO_DELETE_DAYS: (1, "days"),
    CONF_UNDO_MB: (1, "MB"),
    CONF_UNDO_DAYS: (1, "days"),
    CONF_AUDIT_MB: (1, "MB"),
    CONF_TIMEOUT: (10, "s"),
}


def _field(key: str, opts: dict[str, Any]) -> tuple[Any, Any]:
    if key == CONF_REVIEWER_PROVIDER:
        choices = [SelectOptionDict(value=SAME_PROVIDER, label="Same as the chat")] + [
            SelectOptionDict(value=p["id"], label=p.get("name") or p["type"])
            for p in opts.get("providers", [])
        ]
        current = opts.get(key) or SAME_PROVIDER
        if current not in [c["value"] for c in choices]:
            current = SAME_PROVIDER
        return vol.Required(key, default=current), SelectSelector(
            SelectSelectorConfig(options=choices, mode=SelectSelectorMode.DROPDOWN)
        )
    if key in (CONF_REVIEWER_MODEL, CONF_ALWAYS_ASK):
        return vol.Optional(key, description={"suggested_value": opts.get(key)}), TextSelector(
            TextSelectorConfig(multiline=key == CONF_ALWAYS_ASK)
        )
    if key == CONF_SEARCH_BACKEND:
        return vol.Required(key, default=search_backend(opts)), SelectSelector(
            SelectSelectorConfig(
                options=SEARCH_BACKENDS,
                translation_key=CONF_SEARCH_BACKEND,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
    if key in (CONF_SEARXNG_URL, CONF_SEARCH_KEY):
        kind = TextSelectorType.URL if key == CONF_SEARXNG_URL else TextSelectorType.PASSWORD
        return vol.Optional(key, description={"suggested_value": opts.get(key)}), TextSelector(
            TextSelectorConfig(type=kind)
        )
    if key == CONF_PRICE_OVERRIDES:
        return vol.Optional(key, description={"suggested_value": opts.get(key)}), ObjectSelector()
    if key in RANGES:
        step, unit = _UNITS.get(key, (1, None))
        return vol.Required(key, default=setting(opts, key)), _number(key, step, unit)
    return vol.Required(key, default=bool(opts.get(key, DEFAULT_OPTIONS.get(key)))), (
        BooleanSelector()
    )


def _settings_schema(opts: dict[str, Any]) -> vol.Schema:
    fields: dict[Any, Any] = {
        vol.Required(CONF_APPROVAL_MODE, default=opts[CONF_APPROVAL_MODE]): SelectSelector(
            SelectSelectorConfig(
                options=APPROVAL_MODES,
                translation_key=CONF_APPROVAL_MODE,
                mode=SelectSelectorMode.LIST,
            )
        ),
        vol.Optional(
            CONF_EXTRA_PROMPT, description={"suggested_value": opts.get(CONF_EXTRA_PROMPT)}
        ): TextSelector(TextSelectorConfig(multiline=True)),
    }
    for name, (collapsed, keys) in SECTIONS.items():
        inner = dict(_field(k, opts) for k in keys)
        # A section left out of the answer keeps its current values.
        fields[vol.Optional(name)] = section(vol.Schema(inner), {"collapsed": collapsed})
    return vol.Schema(fields)


def _flatten(user_input: dict[str, Any]) -> dict[str, Any]:
    """Sections come back as nested dicts; options are stored flat."""
    flat: dict[str, Any] = {}
    for key, value in user_input.items():
        if key in SECTIONS and isinstance(value, dict):
            flat.update(value)
        else:
            flat[key] = value
    return flat


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
            vol.Optional(
                "context_window",
                description={"suggested_value": cur.get("context_window")},
            ): NumberSelector(
                NumberSelectorConfig(
                    min=2048, max=2_000_000, step=1024, mode=NumberSelectorMode.BOX
                )
            ),
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
    if user_input.get("context_window"):
        provider["context_window"] = int(user_input["context_window"])
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
        menu = ["settings", "storage", "add_provider"]
        if self._providers:
            menu += ["edit_provider", "remove_provider"]
        return self.async_show_menu(step_id="init", menu_options=menu)

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        opts = self._options
        if user_input is not None:
            flat = _flatten(user_input)
            for key, value in list(flat.items()):
                if key in RANGES:
                    flat[key] = setting({key: value}, key)
            flat.setdefault(CONF_EXTRA_PROMPT, "")
            flat.setdefault(CONF_PRICE_OVERRIDES, {})
            if "reviewer" in user_input:
                flat.setdefault(CONF_REVIEWER_MODEL, "")
                flat.setdefault(CONF_ALWAYS_ASK, "")
            if "web" in user_input:  # an emptied text box comes back missing
                flat.setdefault(CONF_SEARXNG_URL, "")
                flat.setdefault(CONF_SEARCH_KEY, "")
            if flat.get(CONF_ALLOW_SHELL) and not opts.get(CONF_ALLOW_SHELL):
                self._pending = flat
                return await self.async_step_confirm_shell()
            return self._save(**flat)
        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(opts),
            description_placeholders={"prices_checked": PRICES_CHECKED},
        )

    async def async_step_storage(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show what the integration stores and offer to clean it up."""
        agent = self.hass.data.get(DOMAIN)
        if agent is None:
            return self.async_abort(reason="not_loaded")
        if user_input is not None:
            days = int(user_input.get("delete_older_days") or 0)
            if days > 0:
                await agent.store.delete_older_than(days)
            if user_input.get("clear_undo"):
                await agent.snapshots.clear()
            return self._save()
        chats = await agent.store.disk_usage()
        snaps = await agent.snapshots.disk_usage()
        today = agent.store.spent(dt_util.now().strftime("%Y-%m-%d"))
        return self.async_show_form(
            step_id="storage",
            data_schema=vol.Schema(
                {
                    vol.Required("delete_older_days", default=0): NumberSelector(
                        NumberSelectorConfig(
                            min=0,
                            max=3650,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="days",
                        )
                    ),
                    vol.Required("clear_undo", default=False): BooleanSelector(),
                }
            ),
            description_placeholders={
                "chats": str(chats["chats"]),
                "chat_size": _size(chats["bytes"]),
                "snapshots": str(snaps["snapshots"]),
                "snapshot_size": _size(snaps["snapshot_bytes"]),
                "audit_size": _size(snaps["audit_bytes"]),
                "spent_today": f"${today:.2f}",
            },
        )

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
