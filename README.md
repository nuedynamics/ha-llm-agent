# LLM Agent for Home Assistant

[![CI](https://github.com/nuedynamics/ha-llm-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/nuedynamics/ha-llm-agent/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/nuedynamics/ha-llm-agent)](https://github.com/nuedynamics/ha-llm-agent/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

A chat panel in your Home Assistant sidebar where an AI model does the work for you. It
switches devices, answers questions about your home, and builds automations, scripts,
scenes, dashboards and helpers. Bring your own model: Anthropic, OpenAI, OpenRouter, or a
free local model on Ollama.

![The LLM Agent panel creating an automation](docs/images/automation.png)

> **Read [DISCLAIMER.md](DISCLAIMER.md) first.** The AI acts with administrator rights. It can
> make mistakes, and provider charges are yours. Risky actions ask for your approval by
> default, and every file or dashboard change can be undone.

**Contents:** [Install](#install) · [What it can do](#what-it-can-do) ·
[Safety](#safety-and-approvals) · [Providers](#providers-and-cost) ·
[Limitations](#limitations) · [Privacy](#privacy-and-storage) ·
[Troubleshooting](#troubleshooting) · [Testing](#how-it-is-tested) · [Roadmap](#roadmap)

## Install

Requires Home Assistant **2026.10** or newer and an administrator account.

### Recommended: HACS, one click

If you have [HACS](https://hacs.xyz), click this button. It opens HACS on your own Home
Assistant with this repository filled in:

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nuedynamics&repository=ha-llm-agent&category=integration)

1. Click **Download**, then restart Home Assistant.
2. Add the integration with this button, or from **Settings → Devices & services → Add
   integration → LLM Agent**:

   [![Open your Home Assistant instance and start setting up LLM Agent.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=llm_agent)

3. Accept the risk notice, choose a provider, and enter your API key and default model.
4. Open **LLM Agent** in the sidebar.

HACS tells you when an update is available.

### HACS, by hand

Use this if the button doesn't reach your Home Assistant.

1. HACS → ⋮ menu → **Custom repositories**.
2. Add `https://github.com/nuedynamics/ha-llm-agent` with type **Integration**.
3. Find **LLM Agent**, click **Download**, and restart Home Assistant.
4. **Settings → Devices & services → Add integration → LLM Agent**.

### Manual, without HACS

1. Download `llm_agent.zip` from the [latest release](https://github.com/nuedynamics/ha-llm-agent/releases/latest).
2. Unzip it into `/config/custom_components/llm_agent/` (that folder should then contain
   `manifest.json`).
3. Restart Home Assistant and add the integration as above.

To update, repeat these steps. There is no build step; the panel ships pre-built.

> HACS treats LLM Agent as a custom repository because it isn't in the default HACS store
> yet. A default store listing is planned for 1.0 (see the [roadmap](docs/ROADMAP.md)).

## What it can do

| Ask for | What happens |
| --- | --- |
| "Turn off everything downstairs", "set the thermostat to 20" | Calls the right services on the right entities. |
| "When did the back door last open?" | Reads states and history, then answers. |
| "Turn the porch light on at sunset and off at 23:00" | Writes an automation into `automations.yaml`, validates it and reloads. You can open it in the HA editor afterwards. |
| "Make a script for the bedtime routine" | Scripts and scenes, handled the same way as automations. |
| "Make a dashboard for the living room" | Creates or edits a dashboard. |
| "Put the new Zigbee sensors in the right rooms" | Renames areas, devices and entities, and enables or disables them. |
| "Set up the Met.no weather integration" | Starts and answers config flows, reloads or removes integrations, and installs from HACS. |
| "Add `logger:` to configuration.yaml and restart" | Reads and edits YAML, checks the configuration, then reloads or restarts. |
| "Undo that" | Puts the file or dashboard back the way it was. |

It also adds an **Assist conversation agent** for each provider, so you can use the same
model with voice and text Assist. Assist uses Home Assistant's own tools, so there it can
only control, and answer questions about, the entities you expose to Assist.

In the panel:

- Replies stream as they are written. Each tool call shows as a card you can expand.
- File edits and deletions show a diff and wait for approval. Changes to files,
  automations and dashboards get an **Undo** button.
- You can **Edit** or **Retry** your last message, and **Copy** any code block.
- Conversations are saved, so you can return to any of them.
- Each chat shows its token use and an estimated cost.
- It works on phones and in the companion app.

| Approval with a diff | Undo | Phone |
| --- | --- | --- |
| ![Approval card showing a diff](docs/images/approval.png) | ![A change being undone](docs/images/undo.png) | ![Panel on a phone](docs/images/phone.png) |

## Safety and approvals

All settings are under **Settings → Devices & services → LLM Agent → Configure → Settings**.

| Setting | Default | What it does |
| --- | --- | --- |
| Approval mode | Ask before risky actions | `Ask before every change`, `Ask before risky actions`, or `Autopilot` (never asks). |
| Back up before risky actions | On | Takes a full HA backup before HACS installs and integration removal. |
| Protect sensitive data | On | Blocks reading `secrets.yaml`, auth and credential storage, databases, and files outside `/config`. Also blocks commands that issue tokens. |
| Refuse restart when configuration is invalid | On | Restarts only after a passing config check. |
| Allow shell commands | **Off** | Lets the AI run commands in the HA container. Asks you to confirm when you turn it on. |
| Tool calls per message | 25 | Stops runaway loops. |

Risky actions include:

- unlocking locks, and opening garage doors and gates;
- disarming alarms;
- editing files and deleting things;
- installing or removing integrations;
- restarting.

In the default mode, everyday changes such as switching lights or saving an automation run
straight away, and you can undo the automation.

The panel and all of its API calls are limited to administrator accounts. Every action is
written to an audit log.

## Providers and cost

| Provider | Base URL | Notes |
| --- | --- | --- |
| Anthropic | `https://api.anthropic.com` | Prompt caching cuts the cost of long chats. |
| OpenAI | `https://api.openai.com/v1` | Automatic prompt caching. |
| OpenRouter | `https://openrouter.ai/api/v1` | Takes any OpenRouter model id. |
| Ollama | `http://<host>:11434/v1` | Local and free. Use a model with tool calling, for example `llama3.1:8b`. |

You can add several providers, switch between them per chat, or type any model id.

Rate limits and overloads are retried with backoff. Errors give the cause ("the API key was
rejected", "out of credit", "model not found") rather than a bare HTTP code.

The cost shown is an estimate from a built-in price table, and you can override prices per
model in the settings. Your provider's bill is the real number.

## Limitations

- **It can be wrong.** Small local models in particular can pick the wrong entity, or
  write an automation that doesn't do what you meant. Keep approvals on for anything that
  matters, and read the diff.
- **Admins only.** There is no household or non-admin mode yet (planned for 0.4).
- **Undo covers files and dashboards only.** Device actions (on/off) and registry changes
  (renames, areas) can't be undone, so ask it to change them back. Integration removal and
  HACS installs are covered by the automatic backup instead.
- **No images yet.** It can't look at camera snapshots or photos (planned for 0.2).
- **No automation debugging yet.** It can't read automation traces or the log to explain
  why something didn't run (planned for 0.2).
- **No long-term memory.** Each chat starts fresh apart from a short summary of your home.
- **Ollama models need tool calling.** A model without it can chat but can't act.
- **Not in the default HACS store yet** (see [Install](#install)).

## Privacy and storage

Your messages, and whatever the AI looks up to answer them, go to the provider you chose.
Nothing goes anywhere else, and there is no telemetry.

| Data | Where | Limit |
| --- | --- | --- |
| Conversations | `/config/.storage/llm_agent.*` | Loaded on demand; 5 kept in memory |
| Undo snapshots | `/config/.llm_agent/snapshots/` | 50 MB, oldest removed first |
| Audit log | `/config/.llm_agent/audit.jsonl` | Rotated at 2 MB |

Delete a conversation from the list to remove it.

Removing the integration leaves these files in place. If you want them gone, delete
`/config/.llm_agent/` and the `llm_agent.*` files in `/config/.storage/` by hand.

## Troubleshooting

**Error messages.** Provider errors show up in the chat with the cause and the HTTP status,
for example: `Anthropic: the API key was rejected (HTTP 401: ...)`.

**Debug logging.** Turn on **Enable debug logging** on the integration's page, or add this
to `configuration.yaml` and restart:

```yaml
logger:
  logs:
    custom_components.llm_agent: debug
```

With debug logging on, each model request logs its duration, stop reason, token counts and
cache hits, plus the outcome of every tool call.

**Diagnostics.** Go to Settings → Devices & services → LLM Agent → ⋮ → **Download
diagnostics**.

- It includes your settings and the last 20 actions, by tool name and outcome only.
- It leaves out API keys, credentials in URLs, your custom prompt, and all conversation
  text.

**Reporting a bug.** [Open an issue](https://github.com/nuedynamics/ha-llm-agent/issues/new/choose)
and attach the diagnostics file.

## How it is tested

Every push runs these checks on GitHub-hosted CI:

| Check | What it covers |
| --- | --- |
| Unit tests (101, **81% line coverage**) | The agent loop, approvals, and every tool against a real in-process Home Assistant. Also providers (streaming, retries, errors), storage, undo races, diagnostics redaction, and the Assist agent. Each CI run's summary has per-file coverage. |
| End-to-end browser test | A real Home Assistant container with a stub model and headless Chromium. It covers device control, approval with a diff, undo, reload and history, the phone layout, and edit and retry. |
| hassfest and HACS validation | Home Assistant's and HACS's own checks for integrations. |
| Panel build check | Confirms the committed panel bundle matches the source. |
| CodeQL | Static security analysis of the Python and TypeScript code. |

Before each release, a **real-model check** (`LIVE_MODEL=llama3.1:8b e2e/run.sh`) runs
against a local Llama 3.1 8B on Ollama. It:

1. turns a switch on;
2. asks about the switch's state;
3. creates an automation;
4. creates a dashboard.

After each step it checks that the change really happened in Home Assistant.

## Development

```sh
pip install -r requirements-test.txt
pytest --cov=custom_components/llm_agent && ruff check .
cd frontend && npm ci && npm run build   # rebuilds custom_components/llm_agent/www/
e2e/run.sh                                # real HA container + stub model + Chromium
```

[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains how the pieces fit together.

## Roadmap

The full plan is in [docs/ROADMAP.md](docs/ROADMAP.md). In short:

- **0.1.x, hardening and daily polish:**
  - `@` autocomplete for entities;
  - search and export;
  - a daily spend cap;
  - storage controls.
- **0.2, debugging the home:**
  - automation traces and a log reader;
  - a template tester;
  - camera snapshots;
  - blueprints, packages and template sensors.
- **0.3:** home notes (memory), scheduled prompts, and MCP servers as extra tools.
- **0.4:** a safe mode for household members, per-user history, and per-tool rules.
- **1.0:** a default HACS store listing, translations, and a docs site.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
