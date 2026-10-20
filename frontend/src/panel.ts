import {
  LitElement,
  html,
  nothing,
  type PropertyValues,
  type TemplateResult,
} from "lit";
import { property, query, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { repeat } from "lit/directives/repeat.js";
import { renderMarkdown } from "./markdown";
import { styles } from "./styles";
import type {
  ChatEvent,
  Conversation,
  ConvSummary,
  Hass,
  Info,
  Item,
  ProviderInfo,
  StoredMessage,
  Usage,
} from "./types";

const EMPTY_USAGE: Usage = {
  input: 0,
  output: 0,
  cache_read: 0,
  cache_write: 0,
  cost: 0,
};

class LlmAgentPanel extends LitElement {
  static styles = styles;

  @property({ attribute: false }) hass?: Hass;
  @property({ type: Boolean }) narrow = false;

  @state() private info?: Info;
  @state() private convs: ConvSummary[] = [];
  @state() private convId: string | null = null;
  @state() private chatTitle = "New chat";
  @state() private items: Item[] = [];
  @state() private usage: Usage = EMPTY_USAGE;
  @state() private running = false;
  @state() private editing = false;
  @state() private providerId = "";
  @state() private model = "";
  @state() private showList = false;
  @state() private loadError = "";

  @query("textarea") private input?: HTMLTextAreaElement;
  @query(".messages") private scroller?: HTMLElement;

  private unsub?: () => Promise<void>;
  private started = false;
  private stickToBottom = true;
  private renderTimer?: number;

  private get ws() {
    return this.hass!.connection;
  }

  protected updated(changed: PropertyValues): void {
    if (changed.has("hass") && this.hass && !this.started) {
      this.started = true;
      void this.init();
    }
    if (this.stickToBottom && this.scroller) {
      this.scroller.scrollTop = this.scroller.scrollHeight;
    }
    this.addCopyButtons();
  }

  /** Copy buttons on code blocks in finished replies (the model's YAML is often pasted). */
  private addCopyButtons(): void {
    if (!this.scroller) return;
    for (const pre of this.scroller.querySelectorAll<HTMLPreElement>(
      ".md pre:not([data-copy])",
    )) {
      pre.dataset.copy = "1";
      const btn = document.createElement("button");
      btn.className = "copy small ghost";
      btn.textContent = "Copy";
      btn.addEventListener("click", async () => {
        const code = pre.querySelector("code") ?? pre;
        try {
          await navigator.clipboard.writeText(code.textContent ?? "");
          btn.textContent = "Copied";
        } catch {
          btn.textContent = "Copy failed";
        }
        setTimeout(() => (btn.textContent = "Copy"), 1500);
      });
      pre.prepend(btn);
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    void this.detach();
    this.started = false;
  }

  private async init(): Promise<void> {
    try {
      this.info = await this.ws.sendMessagePromise<Info>({
        type: "llm_agent/info",
      });
    } catch (err) {
      this.loadError = (err as { message?: string }).message ?? String(err);
      return;
    }
    const first = this.info.providers[0];
    if (first && !this.providerId) {
      this.providerId = first.id;
      this.model = first.default_model;
    }
    await this.refreshList();
    if (this.convId) await this.open(this.convId);
  }

  private async refreshList(): Promise<void> {
    this.convs = await this.ws.sendMessagePromise<ConvSummary[]>({
      type: "llm_agent/conversations/list",
    });
  }

  private get provider(): ProviderInfo | undefined {
    return this.info?.providers.find((p) => p.id === this.providerId);
  }

  // ---- conversations -------------------------------------------------------

  private async detach(): Promise<void> {
    const unsub = this.unsub;
    this.unsub = undefined;
    if (unsub) {
      try {
        await unsub();
      } catch {
        /* socket already closed */
      }
    }
  }

  private newChat(): void {
    this.editing = false;
    void this.detach();
    this.convId = null;
    this.chatTitle = "New chat";
    this.items = [];
    this.usage = EMPTY_USAGE;
    this.running = false;
    this.showList = false;
    const p = this.provider ?? this.info?.providers[0];
    if (p) this.model = p.default_model;
    this.input?.focus();
  }

  private async open(id: string): Promise<void> {
    await this.detach();
    this.showList = false;
    this.editing = false;
    const conv = await this.ws.sendMessagePromise<Conversation>({
      type: "llm_agent/conversations/get",
      conversation_id: id,
    });
    this.convId = conv.id;
    this.chatTitle = conv.title;
    this.usage = conv.usage;
    this.providerId = conv.provider_id;
    this.model = conv.model;
    this.items = toItems(conv.messages);
    this.running = false;
    this.stickToBottom = true;
    const info = await this.ws.sendMessagePromise<Info>({
      type: "llm_agent/info",
    });
    if (info.running.includes(id)) {
      this.running = true;
      this.items = [...this.items, { kind: "assistant", text: "" }];
      this.unsub = await this.ws.subscribeMessage<ChatEvent>(
        (e) => this.onEvent(e),
        {
          type: "llm_agent/attach",
          conversation_id: id,
        },
      );
    }
  }

  private async removeConv(id: string, ev: Event): Promise<void> {
    ev.stopPropagation();
    if (!confirm("Delete this conversation?")) return;
    await this.ws.sendMessagePromise({
      type: "llm_agent/conversations/delete",
      conversation_id: id,
    });
    if (id === this.convId) this.newChat();
    await this.refreshList();
  }

  // ---- sending -------------------------------------------------------------

  private lastUserIndex(): number {
    for (let i = this.items.length - 1; i >= 0; i--) {
      if (this.items[i].kind === "user") return i;
    }
    return -1;
  }

  /** Send the composer text, or `retry` to run the last message again. Editing or retrying
   * replaces the last message and its reply in the saved conversation. */
  private async send(retry?: string): Promise<void> {
    const rewind = retry !== undefined || this.editing;
    const text = retry ?? this.input?.value.trim();
    if (!text || this.running) return;
    if (retry === undefined) {
      this.input!.value = "";
      this.autosize();
    }
    this.editing = false;
    const lastUser = this.lastUserIndex();
    const kept =
      rewind && lastUser >= 0 ? this.items.slice(0, lastUser) : this.items;
    this.items = [
      ...kept,
      { kind: "user", text },
      { kind: "assistant", text: "" },
    ];
    this.running = true;
    this.stickToBottom = true;
    try {
      let first = true;
      this.unsub = await this.ws.subscribeMessage<
        ChatEvent | { conversation_id: string }
      >(
        (e) => {
          if (first && "conversation_id" in e) return;
          first = false;
          this.onEvent(e as ChatEvent);
        },
        {
          type: "llm_agent/chat",
          text,
          conversation_id: this.convId,
          provider_id: this.providerId || undefined,
          model: this.model || undefined,
          rewind: rewind || undefined,
        },
      );
    } catch (err) {
      this.running = false;
      this.push({ kind: "notice", text: errText(err), error: true });
      return;
    }
    if (!this.convId) {
      await this.refreshList();
      this.convId = this.convs[0]?.id ?? null;
      this.chatTitle = this.convs[0]?.title ?? text.slice(0, 60);
    }
  }

  private onEvent(e: ChatEvent): void {
    switch (e.type) {
      case "delta": {
        const last = this.items[this.items.length - 1];
        if (last?.kind === "assistant") {
          last.text += e.text;
        } else {
          this.items.push({ kind: "assistant", text: e.text });
        }
        this.scheduleRender();
        return;
      }
      case "tool_start":
        this.push({
          kind: "tool",
          id: e.call_id,
          name: e.name,
          args: e.args,
          status: "running",
        });
        return;
      case "approval":
        this.patchTool(
          e.call_id,
          {
            status: "waiting",
            approval: {
              summary: e.summary,
              reason: e.reason,
              risky: e.risky,
              diff: e.diff,
            },
          },
          {
            kind: "tool",
            id: e.call_id,
            name: e.name,
            args: e.args,
            status: "waiting",
          },
        );
        return;
      case "tool_result":
        this.patchTool(e.call_id, {
          status: e.ok ? "ok" : "error",
          summary: e.summary,
          preview: e.preview,
          snapshotId: e.snapshot_id,
          approval: undefined,
        });
        // the model writes its next text after the tools
        this.push({ kind: "assistant", text: "" });
        return;
      case "usage":
        this.usage = e.usage;
        return;
      case "notice":
        this.push({ kind: "notice", text: e.text });
        return;
      case "error":
        this.push({ kind: "notice", text: e.message, error: true });
        return;
      case "done":
        this.usage = e.usage;
        this.running = false;
        this.items = this.items.filter(
          (i) => !(i.kind === "assistant" && !i.text),
        );
        void this.detach();
        void this.refreshList().then(() => {
          this.chatTitle =
            this.convs.find((c) => c.id === this.convId)?.title ??
            this.chatTitle;
        });
        return;
    }
  }

  private scheduleRender(): void {
    // Streaming tokens re-render at most ~12 times a second.
    if (this.renderTimer !== undefined) return;
    this.renderTimer = window.setTimeout(() => {
      this.renderTimer = undefined;
      this.requestUpdate();
    }, 80);
  }

  private push(item: Item): void {
    const items = this.items.filter(
      (i) => !(i.kind === "assistant" && !i.text),
    );
    this.items = [...items, item];
  }

  private patchTool(
    id: string,
    patch: Partial<Extract<Item, { kind: "tool" }>>,
    fallback?: Item,
  ): void {
    let found = false;
    this.items = this.items.map((i) => {
      if (i.kind === "tool" && i.id === id) {
        found = true;
        return { ...i, ...patch };
      }
      return i;
    });
    if (!found && fallback)
      this.push({ ...(fallback as object), ...patch } as Item);
  }

  private async answer(id: string, approved: boolean): Promise<void> {
    const note =
      (
        this.renderRoot.querySelector(
          `#note-${CSS.escape(id)}`,
        ) as HTMLInputElement | null
      )?.value ?? "";
    this.patchTool(id, { status: "running", approval: undefined });
    try {
      await this.ws.sendMessagePromise({
        type: "llm_agent/approve",
        conversation_id: this.convId,
        call_id: id,
        approved,
        note,
      });
    } catch (err) {
      this.push({ kind: "notice", text: errText(err), error: true });
    }
  }

  private async undo(item: Extract<Item, { kind: "tool" }>): Promise<void> {
    if (!item.snapshotId || !confirm(`Undo "${item.summary || item.name}"?`))
      return;
    try {
      const res = await this.ws.sendMessagePromise<{ summary: string }>({
        type: "llm_agent/undo",
        snapshot_id: item.snapshotId,
        ...(this.convId ? { conversation_id: this.convId } : {}),
      });
      this.patchTool(item.id, { undone: true });
      this.push({ kind: "notice", text: `Undone: ${res.summary}` });
    } catch (err) {
      this.push({ kind: "notice", text: errText(err), error: true });
    }
  }

  private async stop(): Promise<void> {
    if (this.convId) {
      await this.ws.sendMessagePromise({
        type: "llm_agent/cancel",
        conversation_id: this.convId,
      });
    }
  }

  // ---- input ---------------------------------------------------------------

  private editLast(text: string): void {
    this.editing = true;
    this.input!.value = text;
    this.autosize();
    this.input!.focus();
  }

  private cancelEdit(): void {
    this.editing = false;
    this.input!.value = "";
    this.autosize();
  }

  private onKey(ev: KeyboardEvent): void {
    if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) {
      ev.preventDefault();
      void this.send();
    }
  }

  private autosize(): void {
    const ta = this.input;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 240)}px`;
  }

  private onScroll(): void {
    const el = this.scroller;
    if (el)
      this.stickToBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  }

  private pickProvider(ev: Event): void {
    this.providerId = (ev.target as HTMLSelectElement).value;
    this.model = this.provider?.default_model ?? "";
  }

  // ---- render --------------------------------------------------------------

  protected render(): TemplateResult {
    if (this.loadError) {
      return html`<div class="empty">
        LLM Agent could not load: ${this.loadError}
      </div>`;
    }
    if (this.info && !this.info.providers.length) {
      return html`<div class="empty">
        No AI provider is configured. Add one under Settings → Devices &amp;
        services → LLM Agent → Configure.
      </div>`;
    }
    const listOpen = !this.narrow || this.showList;
    const lastUser = this.convId ? this.lastUserIndex() : -1;
    return html`
      <div class="layout ${this.narrow ? "narrow" : ""}">
        ${listOpen ? this.renderList() : nothing}
        <main>
          <header>
            <ha-menu-button
              .hass=${this.hass}
              .narrow=${this.narrow}
            ></ha-menu-button>
            ${
              this.narrow
                ? html`<button
                    class="icon"
                    title="Conversations"
                    aria-label="Conversations"
                    @click=${() => (this.showList = !this.showList)}
                  >
                    <ha-icon icon="mdi:forum-outline"></ha-icon>
                  </button>`
                : nothing
            }
            <div class="title">${this.chatTitle}</div>
            <button class="ghost" @click=${this.newChat}>New chat</button>
          </header>
          <div class="messages" @scroll=${this.onScroll}>
            ${this.items.length ? nothing : this.renderWelcome()}
            ${repeat(
              this.items,
              (_i, idx) => idx,
              (item, idx) =>
                this.renderItem(
                  item,
                  idx === this.items.length - 1,
                  idx === lastUser,
                ),
            )}
          </div>
          ${this.renderComposer()}
        </main>
      </div>
    `;
  }

  private renderList(): TemplateResult {
    return html`<nav>
      <button class="primary wide" @click=${this.newChat}>+ New chat</button>
      <div class="convs">
        ${this.convs.map(
          (c) =>
            html`<div
              class="conv ${c.id === this.convId ? "active" : ""}"
              @click=${() => this.open(c.id)}
            >
              <span class="conv-title">${c.title}</span>
              <button
                class="icon small"
                title="Delete"
                @click=${(e: Event) => this.removeConv(c.id, e)}
              >
                ✕
              </button>
            </div>`,
        )}
      </div>
    </nav>`;
  }

  private renderWelcome(): TemplateResult {
    const tips = [
      "Turn off all the lights downstairs",
      "Make a dashboard for the living room",
      "Create an automation: porch light on at sunset, off at 11pm",
      "Why did the hallway sensor go unavailable yesterday?",
    ];
    return html`<div class="welcome">
      <h2>What should I do?</h2>
      <p>
        I can control devices, answer questions about your home, and build
        automations, scenes, scripts and dashboards. Mode:
        <b>${modeName(this.info?.approval_mode)}</b>.
      </p>
      <div class="tips">
        ${tips.map(
          (t) =>
            html`<button
              class="tip"
              @click=${() => {
                this.input!.value = t;
                this.input!.focus();
              }}
            >
              ${t}
            </button>`,
        )}
      </div>
    </div>`;
  }

  private renderItem(
    item: Item,
    last: boolean,
    lastUser = false,
  ): TemplateResult | typeof nothing {
    switch (item.kind) {
      case "user":
        return html`<div class="msg user">${item.text}</div>
          ${
            lastUser && !this.running
              ? html`<div class="msg-actions">
                  <button
                    class="small ghost"
                    @click=${() => this.editLast(item.text)}
                  >
                    Edit
                  </button>
                  <button
                    class="small ghost"
                    @click=${() => this.send(item.text)}
                  >
                    Retry
                  </button>
                </div>`
              : nothing
          }`;
      case "assistant":
        if (!item.text) {
          return last && this.running
            ? html`<div class="msg assistant typing">
                <span></span><span></span><span></span>
              </div>`
            : nothing;
        }
        return html`<div class="msg assistant md">
          ${unsafeHTML(renderMarkdown(item.text, !(last && this.running)))}
        </div>`;
      case "notice":
        return html`<div class="notice ${item.error ? "error" : ""}">
          ${item.text}
        </div>`;
      case "tool":
        return this.renderTool(item);
    }
  }

  private renderTool(item: Extract<Item, { kind: "tool" }>): TemplateResult {
    const icon = { running: "⋯", ok: "✓", error: "!", waiting: "?" }[
      item.status
    ];
    const approval = item.approval;
    return html`<div
      class="tool ${item.status} ${approval?.risky ? "risky" : ""}"
    >
      <details ?open=${!!approval}>
        <summary>
          <span class="badge">${icon}</span>
          <span class="tool-name">${toolLabel(item.name)}</span>
          <span class="tool-summary"
            >${approval?.summary ?? item.summary ?? argsLine(item.args)}</span
          >
          ${item.undone ? html`<span class="tag">undone</span>` : nothing}
        </summary>
        ${approval?.diff ? html`<pre class="diff">${diffLines(approval.diff)}</pre>` : nothing}
        ${!approval ? html`<pre class="args">${JSON.stringify(item.args, null, 2)}</pre>` : nothing}
        ${item.preview && !approval ? html`<pre class="result">${item.preview}</pre>` : nothing}
      </details>
      ${
        approval
          ? html`<div class="approval">
              <div class="reason">
                ${approval.risky ? "⚠ " : ""}Needs your
                approval${approval.reason ? `: ${approval.reason}` : ""}
              </div>
              <input
                id="note-${item.id}"
                placeholder="Optional note for the AI"
              />
              <button
                class="danger"
                @click=${() => this.answer(item.id, false)}
              >
                Deny
              </button>
              <button
                class="primary"
                @click=${() => this.answer(item.id, true)}
              >
                Approve
              </button>
            </div>`
          : nothing
      }
      ${
        item.snapshotId && !item.undone && item.status === "ok"
          ? html`<button
              class="ghost small undo"
              @click=${() => this.undo(item)}
            >
              Undo
            </button>`
          : nothing
      }
    </div>`;
  }

  private renderComposer(): TemplateResult {
    const p = this.provider;
    const listId = "models";
    return html`<footer>
      <div class="composer">
        <textarea
          rows="1"
          placeholder="Ask or tell me to do something…"
          @keydown=${this.onKey}
          @input=${this.autosize}
        ></textarea>
        ${
          this.running
            ? html`<button class="danger" @click=${this.stop}>Stop</button>`
            : html`<button class="primary" @click=${() => this.send()}>
                Send
              </button>`
        }
      </div>
      <div class="meta">
        ${
          this.editing
            ? html`<span class="editing"
                >Editing your last message
                <button class="small ghost" @click=${this.cancelEdit}>
                  Cancel
                </button></span
              >`
            : nothing
        }
        <select
          @change=${this.pickProvider}
          .value=${this.providerId}
          ?disabled=${this.running}
        >
          ${this.info?.providers.map(
            (prov) =>
              html`<option
                value=${prov.id}
                ?selected=${prov.id === this.providerId}
              >
                ${prov.name}
              </option>`,
          )}
        </select>
        <input
          class="model"
          list=${listId}
          .value=${this.model}
          ?disabled=${this.running}
          @change=${(e: Event) => (this.model = (e.target as HTMLInputElement).value.trim())}
          title="Model id (pick or type)"
        />
        <datalist id=${listId}>
          ${p?.models.map((m) => html`<option value=${m.id}>${m.label}</option>`)}
        </datalist>
        <span
          class="usage"
          title="Tokens in / out (cached). Cost is an estimate."
        >
          ${fmtTokens(this.usage.input + this.usage.cache_read + this.usage.cache_write)}
          in · ${fmtTokens(this.usage.output)} out
          ${this.usage.cache_read ? html` · ${fmtTokens(this.usage.cache_read)} cached` : nothing}
          ·
          ${this.usage.cost == null ? "cost n/a" : `~$${this.usage.cost.toFixed(this.usage.cost < 1 ? 4 : 2)}`}
        </span>
      </div>
    </footer>`;
  }
}

// ---- helpers ----------------------------------------------------------------

function toItems(messages: StoredMessage[]): Item[] {
  const items: Item[] = [];
  const calls = new Map<
    string,
    { name: string; args: Record<string, unknown> }
  >();
  for (const m of messages) {
    if (m.role === "user") items.push({ kind: "user", text: m.content });
    else if (m.role === "assistant") {
      if (m.content) items.push({ kind: "assistant", text: m.content });
      for (const c of m.tool_calls)
        calls.set(c.id, { name: c.name, args: c.args });
    } else {
      const call = calls.get(m.tool_call_id);
      items.push({
        kind: "tool",
        id: m.tool_call_id,
        name: m.name,
        args: call?.args ?? {},
        status: m.ok ? "ok" : "error",
        summary: m.summary || (m.decision === "denied" ? "Denied" : ""),
        preview: m.preview,
        snapshotId: m.snapshot_id,
        undone: m.undone,
      });
    }
  }
  return items;
}

function diffLines(diff: string): TemplateResult[] {
  return diff.split("\n").map((line) => {
    const cls =
      line.startsWith("+") && !line.startsWith("+++")
        ? "add"
        : line.startsWith("-") && !line.startsWith("---")
          ? "del"
          : line.startsWith("@@")
            ? "hunk"
            : "";
    return html`<span class=${cls}>${line} </span>`;
  });
}

function toolLabel(name: string): string {
  return name.replace(/_/g, " ");
}

function argsLine(args: Record<string, unknown>): string {
  const s = Object.entries(args)
    .filter(([k]) => !k.startsWith("_"))
    .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(" ");
  return s.length > 120 ? `${s.slice(0, 117)}…` : s;
}

function fmtTokens(n: number): string {
  return n >= 1_000_000
    ? `${(n / 1_000_000).toFixed(1)}M`
    : n >= 1000
      ? `${(n / 1000).toFixed(1)}k`
      : String(n);
}

function modeName(mode?: string): string {
  return (
    {
      ask_all: "ask before every change",
      ask_risky: "ask before risky actions",
      autopilot: "autopilot",
    }[mode ?? ""] ?? ""
  );
}

function errText(err: unknown): string {
  return (err as { message?: string }).message ?? String(err);
}

if (!customElements.get("llm-agent-panel")) {
  customElements.define("llm-agent-panel", LlmAgentPanel);
}
