# LLM Agent for Home Assistant

A chat panel in your Home Assistant sidebar where an AI model does things for you: switch
devices, answer questions about your home, and build automations, scenes, scripts,
dashboards and helpers. It works with Anthropic, OpenAI, OpenRouter or a local Ollama
server, using your own API key and the model you pick.

> **Read [DISCLAIMER.md](DISCLAIMER.md) first.** The AI acts with administrator rights. It can
> make mistakes, and provider charges are yours.

## What it can do

- **Control devices**: "turn off everything downstairs", "set the thermostat to 20".
- **Answer questions** from states and history: "when did the back door last open?"
- **Automations, scripts and scenes**: created in the same files the HA editor uses, so you
  can open and edit them in the UI afterwards.
- **Dashboards**: create a dashboard or edit an existing one.
- **Areas, devices and entities**: rename them, assign areas, enable or disable them.
- **Integrations**: start and answer config flows, reload or remove integrations, and install
  from HACS (after your approval).
- **Config files**: read and edit YAML, check the configuration, reload and restart.
- **Undo**: every change it makes to a file or dashboard can be undone from the chat.
- **Assist**: each provider also shows up as an Assist conversation agent for voice and text.
  Assist uses Home Assistant's built-in tools (device control and questions only, on the
  entities you expose).

## Safety settings

All of these are under **Settings → Devices & services → LLM Agent → Configure → Settings**.

| Setting | Default | What it does |
| --- | --- | --- |
| Approval mode | Ask before risky actions | `Ask before every change`, `Ask before risky actions` or `Autopilot` (never asks). |
| Back up before risky actions | On | A full backup before HACS installs and integration removal. |
| Protect sensitive data | On | Blocks reading `secrets.yaml`, auth and credential storage, databases and files outside `/config`, and token-issuing commands. |
| Refuse restart when configuration is invalid | On | Restart only after a passing config check. |
| Allow shell commands | Off | Lets the AI run commands in the HA container. Asks you to confirm when you turn it on. |
| Tool calls per message | 25 | Stops runaway loops. |

Risky actions include unlocking locks, opening garage doors and gates, disarming alarms,
editing files, deleting things, installing or removing integrations, and restarting. In
the default mode each one shows you a summary and, for edits, a diff before it runs.

The panel and all of its API calls are restricted to administrator accounts.

## Install

Requires Home Assistant 2026.10 or newer.

1. In HACS, open the menu → **Custom repositories**, add
   `https://github.com/nuedynamics/ha-llm-agent` with type **Integration**.
2. Install **LLM Agent** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration → LLM Agent**, accept the risk
   notice, then choose a provider and enter your API key and default model.
4. Open **LLM Agent** in the sidebar.

To add more providers or change models later, use **Configure** on the integration. You can
also type any model id in the panel.

### Providers

| Provider | Base URL | Notes |
| --- | --- | --- |
| Anthropic | `https://api.anthropic.com` | Prompt caching is used to keep costs down. |
| OpenAI | `https://api.openai.com/v1` | |
| OpenRouter | `https://openrouter.ai/api/v1` | Any OpenRouter model id. |
| Ollama | `http://<host>:11434/v1` | Local and free. Pick a model that supports tool calling. |

Token counts and an estimated cost are shown under the chat. The built-in price table is a
best-effort estimate; you can override prices per model in the settings.

## Privacy

Messages, plus the information about your home that the AI looks up to answer, are sent to
the provider you choose. Nothing is sent anywhere else. Conversations are stored in your
Home Assistant `.storage` folder; snapshots for undo and an audit log of actions are in
`/config/.llm_agent/`.

## Development

```
pip install pytest-homeassistant-custom-component ruff
pytest && ruff check .
cd frontend && npm ci && npm run build     # rebuilds custom_components/llm_agent/www/
e2e/run.sh                                  # real HA container + stub model + Chromium
```

The built panel bundle is committed so HACS installs work without a build step. CI checks
that it matches the source.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
