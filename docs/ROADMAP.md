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
- Storage done right: the conversation cache is a small LRU (5 chats) that never drops a
  running chat; undo snapshots have a 50 MB budget, oldest pruned first.
- Compaction that doesn't fight prompt caching. Cached history is cheap (about a tenth of
  the price of fresh input), and every rewrite of old history forces a cache rebuild, so
  compaction is rare and batched:
  - it only starts once a chat reaches about 100k tokens;
  - it shortens only old tool results and tool arguments; your messages and the AI's
    replies are never cut;
  - the last 10 turns are never touched;
  - after a batch, the next one waits at least 10 more turns, so the cache is rebuilt at
    most once every 10 turns rather than on every turn.
- Undo is safe under races: one restore per snapshot, retryable if it fails part way.
- Bad tool arguments from the model come back as a clear error it can correct.
- Unit coverage reported in CI (81% at this release).

## Storage and caching plan

What is stored, and the limits that keep it small:

| Data | Where | Limit |
| --- | --- | --- |
| Conversation list | `.storage/llm_agent.conversations` | Titles and stats only |
| Each conversation | `.storage/llm_agent.conv.<id>` | Loaded on demand; 5 kept in memory |
| Undo snapshots | `/config/.llm_agent/snapshots/` | 50 MB, oldest pruned first |
| Audit log | `/config/.llm_agent/audit.jsonl` | Rotated to `audit.1.jsonl` at 2 MB |

Writes are batched (HA's delayed save), so a streaming reply does not write to disk for
every token. Provider prompt caching (Anthropic cache breakpoints, OpenAI automatic prefix
caching) is kept effective by keeping the system prompt and tool list stable and putting
the current time in the user message.

Planned:

- 0.1.2 (done): storage use shown in **Configure → Storage and spend**, with "delete chats
  older than N days" and "clear undo history". 0.1.3: optional auto-delete of old chats.
- The home summary (areas, entity counts) is captured when a chat starts and stays fixed
  for that chat, so it never breaks the cache mid-conversation. 0.2.0: offer a refresh
  when areas or devices change during a long chat.

## 0.1.2: Daily-use polish (released)

**Built-in Home Assistant know-how** (first, because the real-model checks show models
fail on HA's YAML shape, not on reasoning):

- A small reference pack shipped inside the integration (about 50 KB of Markdown, written
  for this project under Apache-2.0): automation triggers, conditions and actions;
  scripts and scenes; service-call targets; templates; dashboard views and the common
  cards; helpers. Each page has a short worked example and the mistakes models make.
- An index of the pack (a page tree with one line per page, about 1k tokens) sits in the
  system prompt, so it is cached. A `read_reference` tool loads only the page the model
  needs.
- Version-exact facts still come from your own Home Assistant: services and their fields
  (`list_services`), entities and their supported features, and the config check.
- Fallback when the pack doesn't cover it: fetch the integration's page from
  home-assistant.io, then web search (see 0.2.0). We link to the official docs rather
  than copy them; their license is not Apache-2.0.

- `@` autocomplete for entities, areas and devices in the composer, which sends exact ids
  and saves tokens.
- Edit and resend the last message; regenerate the last reply.
- Copy buttons on code blocks; export a conversation as Markdown.
- Search conversations by title and text.
- Daily spend cap (optional): stop and ask once the estimated cost for the day passes a
  set amount.
- Verified price table for Anthropic and OpenAI, with the source date shown in settings;
  OpenRouter prices read live from its model list; Claude Haiku's higher price for prompts
  over 100k tokens.
- Model list fetched from the provider (with a cached fallback) instead of a fixed list.
- Panel shows why a turn stopped (tool limit, cut off, cancelled) with a one-click continue.

## 0.1.3: Settings people actually tweak (released)

Home Assistant users like to tune things. Every setting gets a sensible default, a range
that can't break anything, and a one-line explanation. Settings are grouped into
collapsible sections in **Configure → Settings** so the common ones stay on top.

- **Chats and storage:**
  - chats kept in memory (default 5);
  - auto-delete chats older than N days (default off);
  - maximum number of saved chats;
  - undo history size (default 50 MB) and age;
  - audit log size.
- **Context and cost:**
  - when to compact long chats (default 100k tokens), or turn compaction off;
  - set from the model's context window automatically, so a small local model with an
    8k–32k context compacts early enough to keep working;
  - how many recent turns are never shortened (default 10);
  - maximum reply length;
  - include the home summary in the prompt (on/off, for privacy and cost);
  - request timeout and number of retries.
- **Panel:**
  - theme: follow Home Assistant (default), light or dark;
  - text size and compact layout;
  - tool cards collapsed or expanded;
  - show or hide token use and cost;
  - send with Enter or with Ctrl+Enter.
- **Per user:** default provider and model, so each admin can pick their own.
- **Debugging:** log full prompts and replies (off by default, with a warning that the log
  then contains conversation text).

These are stored in the integration's options, so they survive updates and show up in
diagnostics. Panel-only preferences (theme, text size) are kept per browser.

Shipped as planned. The context window is set per provider (the add-provider form has
an optional "context window" field), and compaction then starts at half of it.

## 0.2.0: Sees and debugs the home (released)

- **"Why didn't my automation run?"**: `get_traces` reads automation and script traces
  (trigger, each condition and action with its result or error), and `get_logbook` reads
  the logbook, so the AI can explain a failure and propose a fix.
- **Log reader**: `read_log` filters `home-assistant.log` (or the log from before the last
  restart) by level, integration and text. Credentials in log lines are masked.
- **Template tester**: `render_template` takes stand-in variables (`trigger`, script
  variables), can treat undefined names as errors, reports warnings, and says which
  entities the template listens to.
- **Web research**:
  - `web_fetch` reads HTML and text pages up to 3 MB, in parts, with headings and links
    kept. The Home Assistant integration docs are the first place it looks.
  - `web_search` through a self-hosted SearXNG or a Brave Search API key, offered only
    when one is set up.
  - **Safety:**
    - Web content is marked untrusted. Once a chat has read any, every change in that
      chat asks you, whatever the approval mode (Autopilot included).
    - Private, loopback and link-local addresses are blocked by default. The check runs
      when the address is resolved and again on every redirect, so a public name that
      points at your LAN is blocked too.
    - Only text is downloaded, nothing is executed, and web tools can be turned off.
- Moved to the backlog: the provider's own web search (Anthropic, OpenAI), PDF reading,
  saved docs in `/config/llm_agent/docs/`, and other search APIs such as Tavily.

## 0.2.1: Reviewer approval mode (released)

Shipped as planned below, plus:
- **Free web search, on by default**: the Home Assistant forum, Home Assistant's GitHub
  issues and Wikipedia (in the HA language), with no key or account. SearXNG and Brave
  Search remain for whole-web search; search can be turned off.
- The raw WebSocket tool's `call_service` now follows the same risk rules as the
  `call_service` tool, and `execute_script` counts as risky.
- The reviewer reviews what "Ask before risky actions" would ask about; everyday changes
  still run straight away. Its spend counts towards the daily cap.
- Risk checks resolve `entity_id: all`, floors, labels and targets inside service data.
- Backlog: running a saved script or automation (`script.turn_on`, `automation.trigger`)
  counts as an everyday change even when its actions are risky. Classify by the actions
  it contains.

- **Reviewer approval mode**: a fourth approval mode where a second model, usually a
  cheaper one, approves or denies actions instead of you.
  - You pick the reviewer's provider and model in settings. It can be a small paid model
    or a local Ollama model.
  - For each action that would normally ask you, the reviewer sees:
    - your original request;
    - the action and its arguments, with the diff for edits;
    - the reason the action counts as risky.
  - It answers approve, deny (the reason goes back to the main model), or "ask the
    human", which falls back to the normal approval card.
  - It fails closed: if the reviewer errors, times out or gives an unclear answer, you
    are asked.
  - Some actions always come to you, whatever the reviewer says. By default these are
    unlocking, opening doors and gates, disarming alarms, removing integrations and
    shell commands, and the list is editable.
  - The reviewer can't change the action, only approve or deny it. Its decision and
    reason show on the tool card and go in the audit log.
  - It sees no tool output, so instructions hidden in device names or files can't talk
    it into approving.
  - Reviewer token use and cost are shown separately in the chat.

## 0.2.2: Sees (released)

For models that can see images:

- **Camera snapshots**: the `camera_snapshot` tool looks at a camera ("is the garage
  door open?"). On by default; **Safety → Camera snapshots** turns it off.
- **Photo upload**: attach or paste up to three photos to a message ("what is this
  device?"). The panel shrinks them to at most 1568 pixels a side and re-encodes them as
  JPEG, which also removes metadata such as where the photo was taken.
- Pictures go to the provider with that turn only and aren't stored; the chat history
  notes that a photo was sent.

## 0.2.3: Builds more of the home

- **`llm_agent.ask` action**: automations and scripts send a prompt and get the reply back.
  Nobody can approve there, so actions that need approval are refused.
- **Long-term statistics**: a `get_statistics` tool for energy and sensor trends over
  months, from HA's recorder statistics.
- **Google Gemini**: a native provider (marked unverified until someone tries it with a
  real key).
- **Quick-start buttons**: example requests on the empty chat screen.
- **Building in HA, beyond automations**: blueprints (create from an automation and
  use them), YAML packages, template sensors and helpers, and small `python_script`s,
  each validated before saving and undoable like every other edit.
- **Dashboard preview**: render a proposed dashboard view inside the approval card before
  applying it.
- **Small local models**: a lean tool set (about 800 tokens instead of 3,000) for models
  with a context window of 16,384 tokens or less, and for Ollama with none set (done).
- **Size check in CI**: fail if the panel bundle grows past 60 kB gzipped (done).

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
- Translations and accessibility basics (see Languages and Accessibility in the backlog).
- Documentation site with recipes: energy dashboard, presence automations, "migrate my
  YAML to the UI".
- Stable tool and settings contract, with upgrade notes for each release.

## Backlog

- **Home health check:** unavailable devices, low batteries, Repairs issues, broken
  integrations, and automations that refer to entities that don't exist.
- **Approve from your phone:** approval requests as an actionable mobile notification.
- **Energy questions:** "why was my energy use high last week?" from HA's energy data.
- **Charts in the chat:** "graph the bedroom temperature this week", drawn inline.
- **Cheap and strong models together:** a cheap model for quick control, a stronger one
  for building.
- **Automation clean-up:** find automations that duplicate or fight each other, or never
  run.
- **ESPHome help:** write and check ESPHome device configs.
- **Explain my setup:** a readable write-up of the home that doubles as documentation.
- **Shareable recipes:** export an automation or dashboard idea for others to import.
- **Web research extras:** the provider's own web search, PDF reading, saved docs, more
  search APIs (from 0.2.0).
- **Languages:**
  - the panel and settings translated (HA's translation files plus a panel string table),
    starting with the languages HA users request most;
  - replies in the user's Home Assistant language by default, with a per-user override;
  - dates, numbers and currency in the user's locale;
  - right-to-left layout for Arabic and Hebrew.
- **Accessibility:**
  - full keyboard use: shortcuts for new chat, search, stop and approve or deny, plus a
    visible focus ring everywhere;
  - screen reader support: labels on every icon button, live-region announcements for
    streaming replies and approval requests, and tool cards that read as one unit;
  - contrast checked against WCAG AA in light, dark and HA themes, a high-contrast option,
    and no information carried by colour alone (status icons also have text);
  - respects reduced motion (no spinners or slide-ins), and text size up to 200% without
    breaking the layout;
  - voice in the panel: dictate a message and have replies read aloud through HA's
    speech-to-text and text-to-speech.
- **Model qualification:** a pass-rate table per model (local and hosted) from repeated
  live checks, shown in the README. Until then the supported target is Claude Haiku, and
  the release live check runs against it. Local models are best effort for control and
  questions.

## Not planned

- A coding assistant for projects outside Home Assistant. Building things *in* Home
  Assistant is the core of the product (see 0.2.0). Web research is in scope when it
  serves the home (see 0.2.0).
- Hosting or reselling model access. You always bring your own key or local model.
- Cloud sync of conversations.
