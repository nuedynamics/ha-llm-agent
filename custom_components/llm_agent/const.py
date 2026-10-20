"""Constants for LLM Agent."""

from __future__ import annotations

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

MODE_ASK_ALL = "ask_all"
MODE_ASK_RISKY = "ask_risky"
MODE_AUTOPILOT = "autopilot"
APPROVAL_MODES = [MODE_ASK_ALL, MODE_ASK_RISKY, MODE_AUTOPILOT]

DEFAULT_OPTIONS = {
    CONF_APPROVAL_MODE: MODE_ASK_RISKY,
    CONF_ALLOW_SHELL: False,
    CONF_PROTECT_SENSITIVE: True,
    CONF_BLOCK_INVALID_RESTART: True,
    CONF_BACKUP_BEFORE_RISKY: True,
    CONF_MAX_STEPS: 25,
    CONF_PRICE_OVERRIDES: {},
    CONF_EXTRA_PROMPT: "",
    CONF_DAILY_CAP: 0.0,
}

APPROVAL_TIMEOUT = 600  # seconds
MAX_TOOL_RESULT_CHARS = 16000
OLD_TOOL_RESULT_CHARS = 1500  # tool results from earlier turns are shortened to this
MAX_CONVERSATIONS = 200
SNAPSHOT_KEEP = 50

DATA_DIR = ".llm_agent"  # inside the HA config dir
