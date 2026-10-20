# ha-llm-agent: architecture (draft for owner approval, 2026-10-20)

An AI-provider-agnostic Home Assistant custom integration (HACS) that adds an
admin-only sidebar chat. The agent can control devices and edit Home Assistant
itself (dashboards, automations, scripts, scenes, helpers, integrations, files,
restart, HACS, optional shell). Apache-2.0. Repo: github.com/nuedynamics/ha-llm-agent.
Integration domain: `llm_agent`. Minimum HA: 2026.10.

## 1. Repo layout

```
custom_components/llm_agent/
  manifest.json        no pip requirements (uses HA's aiohttp session)
  __init__.py          setup: register panel, static path, WS commands, LLM provider entries
  config_flow.py       provider entry (provider, API key, base URL, default model) +
                       required "I understand the risks" checkbox; options flow
  const.py
  providers/           base.py (interface), anthropic.py, openai_compat.py
                       (OpenAI, OpenRouter, Ollama /v1), models.py (static model
                       list + static prices; free-text model allowed)
  agent.py             turn loop: provider stream -> tool calls -> approval -> results
  approval.py          risk classifier + approval modes
  tools/               states.py, services.py, registry.py, automations.py
                       (also scripts, scenes), dashboards.py, helpers.py,
                       integrations.py, files.py, system.py, hacs.py, shell.py
  snapshots.py         undo copies and full-backup hook
  store.py             conversations, audit log
  conversation.py      Assist conversation entity (voice)
  websocket.py         admin-only WS API for the panel
  www/agent-panel.js   built frontend (committed; HACS installs from the repo)
frontend/              Lit + TypeScript source, Vite build
tests/                 pytest-homeassistant-custom-component, fake provider
.github/workflows/     CI (GitHub-hosted runners only)
LICENSE NOTICE README.md DISCLAIMER.md hacs.json
```

## 2. Providers

One small interface: `stream(messages, tools, model, options) -> async iterator`
of `TextDelta | ToolCall | Usage | Done`. Two adapters cover all four providers:
- **Anthropic** Messages API with SSE streaming and tool use.
- **OpenAI-compatible** Chat Completions with SSE streaming and tool calls.
  OpenAI, OpenRouter and Ollama (`/v1`) only differ by base URL and auth header.

Raw HTTP through HA's shared aiohttp session, with no SDK dependencies. That
avoids conflicts with the SDK versions HA core pins (anthropic, openai, ollama).
Each provider config entry stores its API key in HA's standard config-entry
storage. The key is never sent to the browser and is redacted from logs and
diagnostics.

Models: `models.py` holds a static default list per provider with input and
output prices per million tokens. The model picker offers these as suggestions
and accepts any typed model id. A model with no known price shows tokens only.
Prices can be overridden in options.

## 3. Agent loop (panel)

1. The user sends a message. The loop builds the prompt: a system prompt, a
   compact home summary (areas, domains, counts; full entity detail only through
   tools), the history and the tool schemas.
2. Provider deltas stream to the browser over a WS subscription.
3. For each tool call, the risk classifier returns `safe` or `risky`. The
   approval mode decides whether to run it or pause:
   - **ask_all**: pause on every write.
   - **ask_risky** (default): pause on risky calls.
   - **autopilot**: never pause, except that shell still requires its own
     enable switch.

   A pause sends an approval card to the panel: a plain-language summary, the
   arguments, and a diff for YAML, dashboard and file edits. Approve or deny
   resumes the loop. Deny returns "user denied" to the model. The loop stops at
   a timeout (10 min) or when the user cancels.
4. Tool results go back to the model. The loop repeats until a final answer,
   with a step cap (default 25 tool calls per turn).
5. Usage totals are stored for each conversation: tokens and a $ estimate.

The panel loop owns its own state rather than HA's ChatLog. ChatLog runs tool
calls automatically as they stream, which conflicts with pausing for approval.

## 4. Voice / Assist

`conversation.py` registers one conversation entity per provider entry. It uses
HA's standard ChatLog flow with HA's built-in **Assist** LLM API: exposed
entities, intents and scripts. Voice can therefore control devices and answer
questions, but cannot edit config. This matches the owner's decision and needs
no approval UI.

## 5. Tools (panel only)

| Group | Tools | Risky when |
|---|---|---|
| states | search entities, get state/attributes, history, logbook | never (read) |
| services | call any service | lock/unlock, alarm, garage/gate/door covers, `homeassistant.*`, delete-style services |
| registry | list/rename/assign areas, devices, entities; enable/disable | delete/remove |
| automations / scripts / scenes | list, get, create/update, delete, run, reload | delete; always snapshot before write |
| dashboards | list, get config, create, save config, delete | delete; snapshot before save |
| helpers | create/update/delete input_* and other helpers | delete |
| integrations | list entries, start/continue config flow, reload, remove | remove |
| files | list/read/write inside `/config` only | every write; snapshot first |
| system | check_config, reload domain, restart, read error log | restart (always runs check_config first and refuses if invalid) |
| hacs | search, install, update (only if HACS is installed) | install/update; full backup first |
| shell | run a command with a timeout, cwd `/config` | always; tool exists only when enabled in options (warning shown) |

Safety limits are settings (owner 2026-10-20: "idk if we want the limits so hard").
They default to on and apply in every approval mode, including autopilot:
- **Protect sensitive data** (on): file tools refuse paths outside `/config` and
  credential stores (`secrets.yaml`, `.storage/auth*`, `.storage/core.config_entries`,
  keys, databases); token-issuing WS commands are blocked.
- **Refuse restart when configuration is invalid** (on).
- **Back up before risky actions** (on): HACS installs and integration removal.
- **Allow shell commands** (off): turning it on needs a second confirmation step.
- **Tool calls per message** (25): after the limit the model is told to stop and summarize.

## 6. Undo and backups

- Before any write to YAML, dashboards or files, the previous content is copied to
  `/config/.llm_agent/snapshots/<timestamp>/`. The last 50 are kept. The panel shows
  an Undo button on each change card. The model can also undo through a tool.
- Before HACS installs and integration removals, the agent makes a full HA backup
  through the backup integration. This is configurable.
- An audit log (`/config/.llm_agent/audit.jsonl`, rotated) records every tool
  call: time, user, tool, risk, approval decision, result status. Secrets are
  never logged.

## 7. Security model

- The panel is registered `require_admin`. Every WS command also checks admin,
  because hiding the panel does not block access to the page by itself.
- API keys stay on the server. The frontend sees only provider names and models.
- Prompt injection (device names, file content or web data steering the model) is
  mitigated by approvals and the safety settings above, and is called out in the disclaimer.
- No telemetry. The only outbound calls go to the configured provider URLs.

## 7a. Efficiency (owner 2026-10-20: "efficient. Well made.")

People run HA on Raspberry Pis, so the integration does real work cheaply rather than
doing less:
- No polling anywhere. The panel streams over the existing HA WebSocket; nothing runs
  while no chat is active. No background tasks at idle.
- No Python requirements: raw aiohttp on HA's shared client session, so installs pull
  nothing and cannot conflict with core pins.
- Conversations: one small index plus one store file per conversation, debounced
  writes (one disk write per turn, not per token), at most 5 kept in memory.
- Streaming text re-renders at most ~12 times a second; finished messages cache their
  rendered markdown.
- History: compact tool results (capped at creation), recorder queries with
  minimal_response/no_attributes and downsampling.
- Token cost: stable cached system prompt and tools (Anthropic prompt caching), the
  home summary computed once per conversation, the time in the user message.
- The panel bundle (~40 kB gzipped) loads only when the panel is opened.

## 8. Frontend

Lit + TypeScript, built by Vite into one ES module (`www/agent-panel.js`, about
60 KB target). Small dependencies only: `lit`, `marked` and `dompurify` for safe
Markdown rendering.

Features:
- conversation list (new, rename, delete)
- streaming chat with a Stop button
- collapsible tool-call cards
- approval cards with diff and Undo
- model picker per conversation (suggestions plus free text)
- token and $ footer
- a settings link

Image attachments are deferred to 0.2.

## 9. Legal

- Apache-2.0 LICENSE and NOTICE. Apache-2.0 has the same warranty and
  liability disclaimers as MIT, and adds patent and contribution terms.
- DISCLAIMER.md and the README state:
  - use at your own risk
  - the AI can make mistakes and can control physical devices
  - not affiliated with or endorsed by Home Assistant or Nabu Casa
  - provider charges are the user's responsibility
- The config flow cannot finish until the admin ticks the risk acknowledgement.
- This is not legal advice. Get counsel if the project is ever sold.

## 10. CI (free, GitHub-hosted runners only; never the self-hosted runner)

- `ci.yml` on every push and PR:
  - ruff
  - pytest with pytest-homeassistant-custom-component pinned to the target HA
  - hassfest
  - HACS validate (brands check ignored until a brands PR lands)
  - frontend typecheck and build, failing if the committed `www/agent-panel.js` is stale
- `e2e.yml`: starts a real HA container in Actions, onboards it, installs the
  integration, points it at a stub OpenAI-compatible SSE server, and drives the
  panel with Playwright. It covers chat, a tool call, an approval and an undo.
- CodeQL default setup, Dependabot, and secret scanning (all free for public repos).
- `release.yml`: on a tag, attaches a zip and creates the GitHub release that HACS reads.

## 11. Delivery order (0.1.0)

1. Skeleton: manifest, config flow, providers, fake-provider tests, CI green.
2. Panel chat with streaming and history; read-only tools.
3. Service calls, approval modes and risk classifier.
4. Automations, scripts, scenes, dashboards and helpers, with snapshots and Undo.
5. Integrations, files, system (check_config and restart), HACS, shell.
6. Assist conversation entity.
7. e2e in Actions, README and disclaimer, release v0.1.0.
   Afterwards: HACS default-store submission (needs a home-assistant/brands PR).
