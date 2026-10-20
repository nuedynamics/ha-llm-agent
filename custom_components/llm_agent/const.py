"""Constants for LLM Agent."""

from __future__ import annotations

from typing import Any

DOMAIN = "llm_agent"
NAME = "LLM Agent"

PANEL_URL = "llm-agent"
PANEL_ELEMENT = "llm-agent-panel"
STATIC_URL = "/llm_agent_static"

# options keys
CONF_PROVIDERS = "providers"
CONF_APPROVAL_MODE = "approval_mode"
CONF_ALLOW_SHELL = "allow_shell"
CONF_PROTECT_SENSITIVE = "protect_sensitive"
CONF_BLOCK_INVALID_RESTART = "block_invalid_restart"
CONF_BACKUP_BEFORE_RISKY = "backup_before_risky"
CONF_MAX_STEPS = "max_steps"
CONF_PRICE_OVERRIDES = "price_overrides"
CONF_EXTRA_PROMPT = "extra_prompt"
CONF_ACK = "acknowledged_risks"
CONF_DAILY_CAP = "daily_spend_cap"  # USD per day, 0 = no cap
# 0.1.3 settings. Each has a default here and a safe range in the options form.
CONF_MAX_REPLY_TOKENS = "max_reply_tokens"
CONF_COMPACT_AT = "compact_at_tokens"  # 0 = never compact
CONF_KEEP_TURNS = "keep_turns"
CONF_HOME_SUMMARY = "include_home_summary"
CONF_CACHE_CHATS = "chats_in_memory"
CONF_MAX_CHATS = "max_chats"
CONF_AUTO_DELETE_DAYS = "auto_delete_days"  # 0 = keep
CONF_UNDO_MB = "undo_size_mb"
CONF_UNDO_KEEP = "undo_keep"
CONF_UNDO_DAYS = "undo_max_age_days"  # 0 = no age limit
CONF_AUDIT_MB = "audit_size_mb"
CONF_TIMEOUT = "request_timeout"  # seconds without data from the provider
CONF_RETRIES = "retries"
CONF_LOG_PROMPTS = "log_prompts"
# 0.2.0 web research
CONF_WEB_TOOLS = "web_tools"
CONF_CAMERA_TOOLS = "camera_tools"  # 0.2.2: camera snapshots for vision models
CONF_WEB_ALLOW_LAN = "web_allow_lan"
CONF_SEARCH_BACKEND = "search_backend"  # free, searxng, brave or off ("none" = free)
CONF_SEARXNG_URL = "searxng_url"
CONF_SEARCH_KEY = "search_api_key"
SEARCH_BACKENDS = ["free", "searxng", "brave", "off"]

MODE_ASK_ALL = "ask_all"
MODE_ASK_RISKY = "ask_risky"
MODE_AUTOPILOT = "autopilot"
MODE_REVIEWER = "reviewer"
APPROVAL_MODES = [MODE_ASK_ALL, MODE_ASK_RISKY, MODE_REVIEWER, MODE_AUTOPILOT]
# 0.2.1 reviewer approval mode
CONF_REVIEWER_PROVIDER = "reviewer_provider"  # provider id, or SAME_PROVIDER
SAME_PROVIDER = "chat"
CONF_REVIEWER_MODEL = "reviewer_model"  # empty = that provider's default model
CONF_ALWAYS_ASK = "always_ask"  # patterns that always come to a person
DEFAULT_ALWAYS_ASK = (
    "lock.*, cover.*, alarm_control_panel.alarm_disarm, integrations:remove, shell, "
    "ha_websocket:execute_script, write_file"
)

DEFAULT_OPTIONS = {
    CONF_APPROVAL_MODE: MODE_ASK_RISKY,
    CONF_REVIEWER_PROVIDER: SAME_PROVIDER,
    CONF_REVIEWER_MODEL: "",
    CONF_ALWAYS_ASK: DEFAULT_ALWAYS_ASK,
    CONF_ALLOW_SHELL: False,
    CONF_PROTECT_SENSITIVE: True,
    CONF_BLOCK_INVALID_RESTART: True,
    CONF_BACKUP_BEFORE_RISKY: True,
    CONF_MAX_STEPS: 25,
    CONF_PRICE_OVERRIDES: {},
    CONF_EXTRA_PROMPT: "",
    CONF_DAILY_CAP: 0.0,
    CONF_MAX_REPLY_TOKENS: 16000,
    CONF_COMPACT_AT: 100_000,
    CONF_KEEP_TURNS: 10,
    CONF_HOME_SUMMARY: True,
    CONF_CACHE_CHATS: 5,
    CONF_MAX_CHATS: 200,
    CONF_AUTO_DELETE_DAYS: 0,
    CONF_UNDO_MB: 50,
    CONF_UNDO_KEEP: 50,
    CONF_UNDO_DAYS: 0,
    CONF_AUDIT_MB: 2,
    CONF_TIMEOUT: 300,
    CONF_RETRIES: 3,
    CONF_LOG_PROMPTS: False,
    CONF_WEB_TOOLS: True,
    CONF_CAMERA_TOOLS: True,
    CONF_WEB_ALLOW_LAN: False,
    CONF_SEARCH_BACKEND: "free",
    CONF_SEARXNG_URL: "",
    CONF_SEARCH_KEY: "",
}

# (min, max) for every number setting, so a bad value can never break anything.
# Values outside are clamped wherever they are read.
RANGES: dict[str, tuple[float, float]] = {
    CONF_MAX_STEPS: (1, 200),
    CONF_DAILY_CAP: (0, 1000),
    CONF_MAX_REPLY_TOKENS: (1024, 128_000),
    CONF_COMPACT_AT: (0, 1_000_000),
    CONF_KEEP_TURNS: (2, 50),
    CONF_CACHE_CHATS: (1, 50),
    CONF_MAX_CHATS: (10, 5000),
    CONF_AUTO_DELETE_DAYS: (0, 3650),
    CONF_UNDO_MB: (5, 2000),
    CONF_UNDO_KEEP: (5, 1000),
    CONF_UNDO_DAYS: (0, 3650),
    CONF_AUDIT_MB: (1, 100),
    CONF_TIMEOUT: (30, 1800),
    CONF_RETRIES: (0, 6),
}


def setting(options: dict, key: str) -> Any:
    """An option's value, falling back to the default and clamped to its range."""
    value = options.get(key, DEFAULT_OPTIONS.get(key))
    if key not in RANGES:
        return value
    lo, hi = RANGES[key]
    try:
        num = float(value)
    except TypeError, ValueError:
        num = float(DEFAULT_OPTIONS[key])
    num = min(max(num, lo), hi)
    return int(num) if isinstance(DEFAULT_OPTIONS[key], int) else num


APPROVAL_TIMEOUT = 600  # seconds
MAX_TOOL_RESULT_CHARS = 16000
OLD_TOOL_RESULT_CHARS = 1500  # tool results from earlier turns are shortened to this
MAX_CONVERSATIONS = 200
SNAPSHOT_KEEP = 50

DATA_DIR = ".llm_agent"  # inside the HA config dir
