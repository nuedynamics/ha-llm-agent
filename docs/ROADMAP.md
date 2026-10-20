# Roadmap

Guiding rule: every feature has to earn its place. It should be cheap to run on a Raspberry
Pi, add nothing to Home Assistant's startup when idle, and stay simple to use. We are not
trying to be a general chatbot. The goal is the best way to run and build a Home Assistant
setup by talking to it.

## 0.1.1: Works on real setups (hardening)

- Real-model test: an end-to-end run against a local model (Llama 3.1 8B in Ollama), plus
  a manual check with each paid provider.
- Retry with backoff on rate limits and overloads (HTTP 429, 5xx, Anthropic 529), honouring
  `retry-after`, before any text streams.
- Clear error messages in the panel for a bad key, an unknown model, running out of
  credit, and timeouts.
- Diagnostics download (Settings → Devices & services → LLM Agent → Download diagnostics),
  with keys redacted, for bug reports.
- Integration icon in the integration's `brand/` folder (HA 2026.10 serves it directly).
- Narrow and mobile layout checked in the companion app, with a screenshot in e2e.
- Issue templates: bug report (asks for the diagnostics file) and feature request.
- No Chinese models in defaults, docs or testing (owner decision).

## 0.1.2: Daily-use polish

- `@` autocomplete for entities, areas and devices in the composer, which sends exact ids
  and saves tokens.
- Edit and resend the last message; regenerate the last reply.
- Copy buttons on code blocks; export a conversation as Markdown.
- Search conversations by title and text.
- Daily spend cap (optional): stop and ask once the estimated cost for the day passes a
  set amount.
- Verified price table for OpenAI and OpenRouter, with the source date shown in settings.

## 0.2.0: Sees and debugs the home

- **"Why didn't my automation run?"**: tools that read automation traces and the logbook,
  so the AI can explain a failure and propose a fix.
- **Log reader**: filtered `home-assistant.log` lookups (errors for one integration since
  the last restart) instead of dumping the whole file.
- **Template tester**: render Jinja templates live before saving them.
- **Building in HA, beyond automations**: blueprints (create from an automation and
  use them), YAML packages, template sensors and helpers, and small `python_script`s,
  each validated before saving and undoable like every other edit.
- **Camera snapshots and image upload** for models that support vision ("is the garage
  door open?", "what is this device?").
- **Dashboard preview**: render a proposed dashboard view inside the approval card before
  applying it.

## 0.3.0: Remembers and works in the background

- **Home notes**: a small, user-editable memory ("the office is upstairs", "never touch the
  freezer plug") added to the system prompt and cached.
- **Scheduled prompts**: "every Sunday evening, check for unavailable devices and low
  batteries and send me a summary", using HA's own scheduler.
- **MCP client**: connect to external MCP servers as extra tools, behind the same
  approval rules.

## 0.4.0: Safe for the whole household

- **Non-admin mode**: household members get a control-and-questions chat limited to the
  entities exposed to Assist. No config or file tools, and no approval bypass.
- Per-user conversation history and per-user spend caps.
- Per-tool approval rules ("always allow lights, always ask for locks").

## 1.0: Default HACS listing

- Listed in the default HACS store (needs a stable release history and the brand icon).
- Translations (start with the languages HA users request most).
- Documentation site with recipes: energy dashboard, presence automations, "migrate my
  YAML to the UI".
- Stable tool and settings contract, with upgrade notes for each release.

## Not planned

- A general web-browsing assistant, or a coding assistant for projects outside Home
  Assistant. Building things *in* Home Assistant is the core of the product (see 0.2.0).
- Hosting or reselling model access. You always bring your own key or local model.
- Cloud sync of conversations.
