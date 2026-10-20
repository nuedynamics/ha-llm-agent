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
  Mention,
  Prefs,
  ModelSuggestion,
  ProviderInfo,
  ReviewVerdict,
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
  @state() private query = "";
  @state() private hits: ConvSummary[] | null = null;
  private searchTimer?: number;
  @state() private convId: string | null = null;
  @state() private chatTitle = "New chat";
  @state() private items: Item[] = [];
  @state() private usage: Usage = EMPTY_USAGE;
  @state() private running = false;
  @state() private editing = false;
  @state() private providerId = "";
  @state() private model = "";
  /** Models fetched from each provider, loaded the first time the model box is used. */
  @state() private fetched: Record<string, ModelSuggestion[]> = {};
  @state() private showList = false;
  @state() private loadError = "";
  @state() private mentions: Mention[] = [];
  @state() private prefs: Prefs = loadPrefs();
  @state() private showPrefs = false;
  @state() private mentionIndex = 0;
  private mentionStart = -1;

  @query("textarea") private input?: HTMLTextAreaElement;
  @query(".messages") private scroller?: HTMLElement;

  private unsub?: () => Promise<void>;
  private started = false;
  private stickToBottom = true;
  private renderTimer?: number;

  private get ws() {
    return this.hass!.connection;
  }

  private applyPrefs(): void {
    const p = this.prefs;
    if (p.theme === "auto") this.removeAttribute("data-theme");
    else this.setAttribute("data-theme", p.theme);
    if (p.size === "normal") this.removeAttribute("data-size");
    else this.setAttribute("data-size", p.size);
    this.toggleAttribute("data-compact", p.compact);
  }

  private setPref<K extends keyof Prefs>(key: K, value: Prefs[K]): void {
    this.prefs = { ...this.prefs, [key]: value };
    savePrefs(this.prefs);
    this.applyPrefs();
  }

  /** Make the current provider and model this user's default for new chats (or clear it). */
  private async setMyDefault(clear = false): Promise<void> {
    const res = await this.ws.sendMessagePromise<{
      my_default: Info["my_default"];
    }>({
      type: "llm_agent/my_default",
      provider_id: clear ? null : this.providerId,
      model: clear ? "" : this.model,
    });
    if (this.info) this.info = { ...this.info, my_default: res.my_default };
  }

  /** Provider and model for a new chat: the user's own default if it still exists. */
  private startModel(): void {
    const mine = this.info?.my_default;
    const p =
      (mine && this.info?.providers.find((x) => x.id === mine.provider_id)) ||
      this.info?.providers[0];
    if (!p) return;
    this.providerId = p.id;
    this.model =
      mine && mine.provider_id === p.id && mine.model
        ? mine.model
        : p.default_model;
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
    this.applyPrefs();
    if (!this.providerId) this.startModel();
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
    this.startModel();
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
    if (conv.stopped && conv.stopped_text)
      this.items.push({
        kind: "notice",
        text: conv.stopped_text,
        stop: conv.stopped,
      });
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
  private async send(retry?: string, overCap = false): Promise<void> {
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
          over_cap: overCap || undefined,
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
      case "review_start":
        this.patchTool(e.call_id, { reviewing: true });
        return;
      case "review":
        this.patchTool(e.call_id, {
          reviewing: false,
          review: { decision: e.decision, reason: e.reason, model: e.model },
        });
        return;
      case "tool_result":
        this.patchTool(e.call_id, {
          ...(e.review ? { review: e.review } : {}),
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
        this.push({ kind: "notice", text: e.text, stop: e.stop });
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

  private modelError = "";
  private loadingModels = new Set<string>();

  private async loadModels(): Promise<void> {
    const id = this.providerId;
    if (!id || id in this.fetched || this.loadingModels.has(id)) return;
    this.loadingModels.add(id);
    try {
      const res = await this.ws.sendMessagePromise<{
        models: ModelSuggestion[];
        error: string | null;
      }>({ type: "llm_agent/models", provider_id: id });
      this.modelError = res.error ?? "";
      this.fetched = { ...this.fetched, [id]: res.models };
    } catch {
      // keep the built-in suggestions; try again next time
    } finally {
      this.loadingModels.delete(id);
    }
  }

  /** Pick up after a reply that was cut off, stopped, or hit the tool limit. */
  private continueTurn(overCap = false): void {
    this.input!.value = "Continue.";
    void this.send(undefined, overCap);
  }

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
    if (this.mentions.length && !ev.isComposing) {
      const n = this.mentions.length;
      if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
        ev.preventDefault();
        this.mentionIndex =
          (this.mentionIndex + (ev.key === "ArrowDown" ? 1 : n - 1)) % n;
        return;
      }
      if (ev.key === "Enter" || ev.key === "Tab") {
        ev.preventDefault();
        this.pickMention(this.mentions[this.mentionIndex]);
        return;
      }
      if (ev.key === "Escape") {
        ev.preventDefault();
        this.mentions = [];
        return;
      }
    }
    if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) {
      const modifier = ev.ctrlKey || ev.metaKey;
      if (this.prefs.send === "ctrl" && !modifier) return; // plain Enter is a new line
      ev.preventDefault();
      void this.send();
    }
  }

  private onInput(): void {
    this.autosize();
    this.updateMentions();
  }

  /** Show `@` suggestions for the word being typed at the cursor. */
  private updateMentions(): void {
    const ta = this.input;
    const hass = this.hass;
    if (!ta || !hass) return;
    const before = ta.value.slice(0, ta.selectionStart ?? ta.value.length);
    const m = /(^|\s)@([^\s@]*)$/.exec(before);
    if (!m) {
      this.mentions = [];
      return;
    }
    this.mentionStart = before.length - m[2].length - 1;
    this.mentions = findMentions(hass, m[2]);
    this.mentionIndex = 0;
  }

  private pickMention(item: Mention): void {
    const ta = this.input!;
    const end = ta.selectionStart ?? ta.value.length;
    const value = ta.value;
    ta.value =
      value.slice(0, this.mentionStart) + item.insert + " " + value.slice(end);
    const pos = this.mentionStart + item.insert.length + 1;
    ta.setSelectionRange(pos, pos);
    this.mentions = [];
    ta.focus();
    this.autosize();
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
    const listOpen = this.narrow ? this.showList : this.prefs.listOpen;
    const lastUser = this.convId ? this.lastUserIndex() : -1;
    return html`
      <div
        class="layout ${this.narrow ? "narrow" : ""}"
        @click=${this.closePrefsOutside}
        @keydown=${(e: KeyboardEvent) => {
          if (e.key === "Escape" && this.showPrefs) this.showPrefs = false;
        }}
      >
        ${listOpen ? this.renderList() : nothing}
        <main>
          <header>
            <ha-menu-button
              .hass=${this.hass}
              .narrow=${this.narrow}
            ></ha-menu-button>
            <button
              class="icon"
              title=${listOpen ? "Hide chats" : "Show chats"}
              aria-label="Conversations"
              aria-expanded=${listOpen}
              @click=${() =>
                this.narrow
                  ? (this.showList = !this.showList)
                  : this.setPref("listOpen", !this.prefs.listOpen)}
            >
              <ha-icon
                icon=${this.narrow ? "mdi:forum-outline" : "mdi:dock-left"}
              ></ha-icon>
            </button>
            <div class="title">${this.chatTitle}</div>
            ${
              this.items.length
                ? html`<button
                    class="icon"
                    title="Download this chat as Markdown"
                    aria-label="Export"
                    @click=${this.exportChat}
                  >
                    <ha-icon icon="mdi:tray-arrow-down"></ha-icon>
                  </button>`
                : nothing
            }
            ${
              listOpen
                ? nothing
                : html`<button
                    class="icon"
                    title="New chat"
                    aria-label="New chat"
                    @click=${this.newChat}
                  >
                    <ha-icon icon="mdi:square-edit-outline"></ha-icon>
                  </button>`
            }
            <button
              class="icon gear"
              title="Panel settings"
              aria-label="Panel settings"
              aria-expanded=${this.showPrefs}
              @click=${() => (this.showPrefs = !this.showPrefs)}
            >
              <ha-icon icon="mdi:cog-outline"></ha-icon>
            </button>
            ${this.showPrefs ? this.renderPrefs() : nothing}
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
                  item.kind !== "user" &&
                    item.kind !== "notice" &&
                    (idx === 0 || this.items[idx - 1].kind === "user"),
                ),
            )}
          </div>
          ${this.renderComposer()}
        </main>
      </div>
    `;
  }

  private onSearch(ev: Event): void {
    this.query = (ev.target as HTMLInputElement).value;
    clearTimeout(this.searchTimer);
    if (!this.query.trim()) {
      this.hits = null;
      return;
    }
    this.searchTimer = window.setTimeout(async () => {
      const query = this.query;
      const res = await this.ws.sendMessagePromise<{
        conversations: ConvSummary[];
      }>({ type: "llm_agent/conversations/search", query });
      if (query === this.query) this.hits = res.conversations;
    }, 300);
  }

  private exportChat(): void {
    const md = toMarkdown(this.chatTitle, this.items);
    const url = URL.createObjectURL(new Blob([md], { type: "text/markdown" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slug(this.chatTitle) || "chat"}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  private renderList(): TemplateResult {
    const list = this.hits ?? this.convs;
    return html`<nav>
      <div class="nav-head">
        <span class="brand"
          ><span class="brand-mark"
            ><ha-icon icon="mdi:robot-happy-outline"></ha-icon></span
          >LLM Agent</span
        >
        <button
          class="icon"
          title="New chat"
          aria-label="New chat"
          @click=${this.newChat}
        >
          <ha-icon icon="mdi:square-edit-outline"></ha-icon>
        </button>
      </div>
      <label class="search">
        <ha-icon icon="mdi:magnify"></ha-icon>
        <input
          type="search"
          placeholder="Search chats"
          aria-label="Search chats"
          .value=${this.query}
          @input=${this.onSearch}
        />
      </label>
      <div class="convs">
        ${
          this.hits && !this.hits.length
            ? html`<div class="nav-empty">No chats match.</div>`
            : nothing
        }
        ${!this.hits && !this.convs.length ? html`<div class="nav-empty">No chats yet.</div>` : nothing}
        ${groupByDay(list, !!this.hits).map(
          ([label, convs]) => html`
            ${label ? html`<div class="group">${label}</div>` : nothing}
            ${convs.map(
              (c) =>
                html`<div
                  class="conv ${c.id === this.convId ? "active" : ""}"
                  @click=${() => this.open(c.id)}
                >
                  <span class="conv-title"
                    >${c.title}${
                      c.snippet && c.snippet !== c.title
                        ? html`<small class="snippet">${c.snippet}</small>`
                        : nothing
                    }</span
                  >
                  <button
                    class="icon del"
                    title="Delete"
                    aria-label="Delete chat"
                    @click=${(e: Event) => this.removeConv(c.id, e)}
                  >
                    <ha-icon icon="mdi:trash-can-outline"></ha-icon>
                  </button>
                </div>`,
            )}
          `,
        )}
      </div>
    </nav>`;
  }

  /** Close the panel settings popover on a click anywhere outside it. */
  private closePrefsOutside(ev: Event): void {
    if (!this.showPrefs) return;
    const inside = ev
      .composedPath()
      .some(
        (el) =>
          el instanceof HTMLElement &&
          (el.classList.contains("prefs") || el.classList.contains("gear")),
      );
    if (!inside) this.showPrefs = false;
  }

  private renderPrefs(): TemplateResult {
    const p = this.prefs;
    const pick = <K extends keyof Prefs>(
      key: K,
      label: string,
      options: [Prefs[K], string][],
    ) =>
      html`<label
        >${label}
        <select
          @change=${(e: Event) =>
            this.setPref(
              key,
              (e.target as HTMLSelectElement).value as Prefs[K],
            )}
        >
          ${options.map(
            ([value, text]) =>
              html`<option value=${String(value)} ?selected=${p[key] === value}>
                ${text}
              </option>`,
          )}
        </select></label
      >`;
    const check = (key: "compact" | "toolsOpen" | "showUsage", label: string) =>
      html`<label class="check"
        ><input
          type="checkbox"
          .checked=${p[key]}
          @change=${(e: Event) => this.setPref(key, (e.target as HTMLInputElement).checked)}
        />${label}</label
      >`;
    const mine = this.info?.my_default;
    const mineName = mine
      ? `${this.info?.providers.find((x) => x.id === mine.provider_id)?.name ?? "?"} · ${mine.model || "provider default"}`
      : "";
    return html`<div class="prefs" role="dialog" aria-label="Panel settings">
      ${pick("theme", "Theme", [
        ["auto", "Follow Home Assistant"],
        ["light", "Light"],
        ["dark", "Dark"],
      ])}
      ${pick("size", "Text size", [
        ["small", "Small"],
        ["normal", "Normal"],
        ["large", "Large"],
      ])}
      ${pick("send", "Send with", [
        ["enter", "Enter"],
        ["ctrl", "Ctrl+Enter"],
      ])}
      ${check("compact", "Compact layout")}
      ${check("toolsOpen", "Expand tool cards")}
      ${check("showUsage", "Show token use and cost")}
      <div class="mine">
        <div>
          My default for new chats:
          ${mine ? mineName : "the provider's default"}
        </div>
        <button class="small" @click=${() => this.setMyDefault()}>
          Use the current model
        </button>
        ${
          mine
            ? html`<button
                class="small ghost"
                @click=${() => this.setMyDefault(true)}
              >
                Clear
              </button>`
            : nothing
        }
      </div>
      <div class="hint">
        These settings are kept in this browser. Agent settings are under
        Settings → Devices &amp; services → LLM Agent → Configure.
      </div>
    </div>`;
  }

  private renderWelcome(): TemplateResult {
    const tips = [
      "Turn off all the lights downstairs",
      "Make a dashboard for the living room",
      "Create an automation: porch light on at sunset, off at 11pm",
      "Why did the hallway sensor go unavailable yesterday?",
    ];
    const icons = [
      "mdi:lightbulb-group-outline",
      "mdi:view-dashboard-outline",
      "mdi:robot-outline",
      "mdi:stethoscope",
    ];
    const name = this.hass?.user?.name?.split(" ")[0];
    return html`<div class="welcome">
      <div class="logo"><ha-icon icon="mdi:robot-happy-outline"></ha-icon></div>
      <h2>${greeting()}${name ? `, ${name}` : ""}</h2>
      <p>
        I can control devices, answer questions about your home, and build
        automations, scenes, scripts and dashboards.
      </p>
      <span class="mode-chip"
        ><ha-icon icon="mdi:shield-check-outline"></ha-icon
        >${capitalize(modeName(this.info?.approval_mode))}</span
      >
      <div class="tips">
        ${tips.map(
          (t, i) =>
            html`<button
              class="tip"
              @click=${() => {
                this.input!.value = t;
                this.input!.focus();
                this.autosize();
              }}
            >
              <ha-icon icon=${icons[i % icons.length]}></ha-icon>
              <span>${t}</span>
            </button>`,
        )}
      </div>
    </div>`;
  }

  private renderItem(
    item: Item,
    last: boolean,
    lastUser = false,
    replyStart = false,
  ): TemplateResult | typeof nothing {
    const avatar = replyStart
      ? html`<div class="avatar" aria-hidden="true">
          <ha-icon icon="mdi:robot-happy-outline"></ha-icon>
        </div>`
      : nothing;
    switch (item.kind) {
      case "user":
        return html`<div class="row user">
          ${
            lastUser && !this.running
              ? html`<div class="msg-actions">
                  <button
                    class="icon"
                    title="Edit"
                    aria-label="Edit"
                    @click=${() => this.editLast(item.text)}
                  >
                    <ha-icon icon="mdi:pencil-outline"></ha-icon>
                  </button>
                  <button
                    class="icon"
                    title="Retry"
                    aria-label="Retry"
                    @click=${() => this.send(item.text)}
                  >
                    <ha-icon icon="mdi:refresh"></ha-icon>
                  </button>
                </div>`
              : nothing
          }
          <div class="msg user">${item.text}</div>
        </div>`;
      case "assistant":
        if (!item.text) {
          return last && this.running
            ? html`<div class="row reply">
                ${avatar}
                <div class="msg assistant typing">
                  <span></span><span></span><span></span>
                </div>
              </div>`
            : nothing;
        }
        return html`<div class="row reply">
          ${avatar}
          <div class="msg assistant md">
            ${unsafeHTML(renderMarkdown(item.text, !(last && this.running)))}
          </div>
        </div>`;
      case "notice":
        return html`<div class="notice ${item.error ? "error" : ""}">
          ${item.text}
          ${
            last && !this.running && item.stop && CONTINUABLE.has(item.stop)
              ? html`<button
                  class="small"
                  @click=${() => this.continueTurn(item.stop === "spend_cap")}
                >
                  ${item.stop === "spend_cap" ? "Continue anyway" : "Continue"}
                </button>`
              : nothing
          }
        </div>`;
      case "tool":
        return html`<div class="row reply">
          ${avatar}${this.renderTool(item)}
        </div>`;
    }
  }

  private renderTool(item: Extract<Item, { kind: "tool" }>): TemplateResult {
    const approval = item.approval;
    const status = {
      running: html`<span class="spinner" aria-label="Running"></span>`,
      ok: html`<ha-icon
        class="st ok"
        icon="mdi:check-circle"
        aria-label="Done"
      ></ha-icon>`,
      error: html`<ha-icon
        class="st error"
        icon="mdi:alert-circle"
        aria-label="Failed"
      ></ha-icon>`,
      waiting: html`<span class="tag wait">Waiting for you</span>`,
    }[item.status];
    return html`<div
      class="tool ${item.status} ${approval?.risky ? "risky" : ""}"
    >
      ${
        approval
          ? html`<div class="approval-head">
              <ha-icon
                icon=${approval.risky ? "mdi:shield-alert-outline" : "mdi:hand-back-right-outline"}
              ></ha-icon>
              <span
                >Needs your
                approval${approval.reason ? html`<span class="why"> · ${approval.reason}</span>` : nothing}</span
              >
            </div>`
          : nothing
      }
      <details ?open=${!!approval || this.prefs.toolsOpen}>
        <summary>
          <span class="tool-icon"
            ><ha-icon icon=${toolIcon(item.name)}></ha-icon
          ></span>
          <span class="tool-name">${toolLabel(item.name)}</span>
          <span class="tool-summary"
            >${approval?.summary ?? item.summary ?? argsLine(item.args)}</span
          >
          ${item.undone ? html`<span class="tag">undone</span>` : nothing}
          ${reviewTag(item.review, item.reviewing)}
          ${status}
          ${
            item.snapshotId && !item.undone && item.status === "ok"
              ? html`<button
                  class="ghost small undo"
                  title="Undo this change"
                  @click=${(e: Event) => {
                    e.preventDefault();
                    e.stopPropagation();
                    void this.undo(item);
                  }}
                >
                  Undo
                </button>`
              : nothing
          }
          <ha-icon class="chev" icon="mdi:chevron-down"></ha-icon>
        </summary>
        ${
          item.review
            ? html`<div class="review-note ${item.review.decision}">
                <ha-icon icon="mdi:shield-check-outline"></ha-icon>
                <span
                  ><b>Reviewer${item.review.model ? ` (${item.review.model})` : ""}:</b>
                  ${item.review.reason || REVIEW_WORDS[item.review.decision]}</span
                >
              </div>`
            : nothing
        }
        ${approval?.diff ? html`<pre class="diff">${diffLines(approval.diff)}</pre>` : nothing}
        ${!approval ? html`<pre class="args">${JSON.stringify(item.args, null, 2)}</pre>` : nothing}
        ${item.preview && !approval ? html`<pre class="result">${item.preview}</pre>` : nothing}
      </details>
      ${
        approval
          ? html`<div class="approval">
              <input
                id="note-${item.id}"
                placeholder="Optional note for the AI"
              />
              <button
                class="ghost danger-text"
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
          @input=${this.onInput}
          @blur=${() =>
            // close the list unless focus came back (a pick by mouse refocuses the box)
            setTimeout(() => {
              if ((this.renderRoot as ShadowRoot).activeElement !== this.input)
                this.mentions = [];
            }, 150)}
        ></textarea>
        ${
          this.mentions.length
            ? html`<ul class="mentions" role="listbox">
                ${this.mentions.map(
                  (m, i) =>
                    html`<li
                      role="option"
                      aria-selected=${i === this.mentionIndex}
                      class=${i === this.mentionIndex ? "active" : ""}
                      @mousedown=${(e: Event) => {
                        e.preventDefault();
                        this.pickMention(m);
                      }}
                    >
                      <span class="kind">${m.kind}</span>
                      <span class="label">${m.label}</span>
                      <span class="detail">${m.detail}</span>
                    </li>`,
                )}
              </ul>`
            : nothing
        }
        <div class="toolbar">
          <label
            class="model-pill"
            title=${this.modelError || "Provider and model"}
          >
            <ha-icon icon="mdi:creation-outline"></ha-icon>
            <select
              aria-label="Provider"
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
            <span class="sep">/</span>
            <input
              class="model"
              aria-label="Model"
              list=${listId}
              .value=${this.model}
              ?disabled=${this.running}
              @change=${(e: Event) => (this.model = (e.target as HTMLInputElement).value.trim())}
              @focus=${this.loadModels}
            />
            <datalist id=${listId}>
              ${(this.fetched[this.providerId] ?? p?.models)?.map(
                (m) => html`<option value=${m.id}>${m.label}</option>`,
              )}
            </datalist>
          </label>
          <span class="spacer"></span>
          ${
            this.running
              ? html`<button
                  class="send stop"
                  title="Stop"
                  aria-label="Stop"
                  @click=${this.stop}
                >
                  <ha-icon icon="mdi:stop"></ha-icon>
                </button>`
              : html`<button
                  class="send"
                  title="Send"
                  aria-label="Send"
                  @click=${() => this.send()}
                >
                  <ha-icon icon="mdi:arrow-up"></ha-icon>
                </button>`
          }
        </div>
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
        <span
          class="usage"
          ?hidden=${!this.prefs.showUsage}
          title="Tokens in / out (cached). Cost is an estimate."
        >
          ${fmtTokens(this.usage.input + this.usage.cache_read + this.usage.cache_write)}
          in · ${fmtTokens(this.usage.output)} out
          ${this.usage.cache_read ? html` · ${fmtTokens(this.usage.cache_read)} cached` : nothing}
          ·
          ${this.usage.cost == null ? "cost n/a" : `~$${this.usage.cost.toFixed(this.usage.cost < 1 ? 4 : 2)}`}
          ${
            this.usage.review
              ? html` · reviewer ${fmtTokens(this.usage.review.input + this.usage.review.output)}
                  tokens,
                  ${this.usage.review.cost == null ? "cost n/a" : `~$${this.usage.review.cost.toFixed(4)}`}`
              : nothing
          }
        </span>
      </div>
    </footer>`;
  }
}

// ---- helpers ----------------------------------------------------------------

const PREFS_KEY = "llm-agent-prefs";
const DEFAULT_PREFS: Prefs = {
  theme: "auto",
  size: "normal",
  compact: false,
  toolsOpen: false,
  showUsage: true,
  send: "enter",
  listOpen: true,
};

function loadPrefs(): Prefs {
  try {
    const saved = JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}");
    return {
      ...DEFAULT_PREFS,
      ...(typeof saved === "object" && saved ? saved : {}),
    };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

function savePrefs(p: Prefs): void {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(p));
  } catch {
    // private mode or storage full: the setting lasts until the page reloads
  }
}

const MAX_MENTIONS = 8;

/** Entities, areas and devices whose id or name contains `q`, best matches first.
 * Inserting exact ids saves the model a search and avoids picking the wrong device. */
export function findMentions(hass: Hass, q: string): Mention[] {
  const needle = q.toLowerCase();
  const scored: [number, Mention][] = [];
  const add = (m: Mention, id: string) => {
    const name = m.label.toLowerCase();
    const key = id.toLowerCase();
    let score: number;
    if (!needle) score = 3;
    else if (name.startsWith(needle) || key.startsWith(needle)) score = 0;
    else if (name.includes(needle) || key.includes(needle)) score = 1;
    else return;
    scored.push([score, m]);
  };
  for (const a of Object.values(hass.areas ?? {})) {
    add(
      {
        kind: "area",
        label: a.name,
        insert: `area_id:${a.area_id}`,
        detail: a.area_id,
      },
      a.area_id,
    );
  }
  for (const d of Object.values(hass.devices ?? {})) {
    const name = d.name_by_user || d.name;
    if (!name) continue;
    add(
      {
        kind: "device",
        label: name,
        insert: `device_id:${d.id} (${name})`,
        detail: "device",
      },
      name,
    );
  }
  for (const st of Object.values(hass.states ?? {})) {
    const name = st.attributes.friendly_name || st.entity_id;
    add(
      {
        kind: "entity",
        label: name,
        insert: st.entity_id,
        detail: st.entity_id,
      },
      st.entity_id,
    );
  }
  scored.sort((x, y) => x[0] - y[0] || x[1].label.localeCompare(y[1].label));
  return scored.slice(0, MAX_MENTIONS).map(([, m]) => m);
}

/** A chat as Markdown: messages, and each tool call with its result. */
export function toMarkdown(title: string, items: Item[]): string {
  const out = [`# ${title}`, ""];
  for (const item of items) {
    if (item.kind === "user") out.push(`**You:** ${item.text}`, "");
    else if (item.kind === "assistant" && item.text) out.push(item.text, "");
    else if (item.kind === "notice") out.push(`> ${item.text}`, "");
    else if (item.kind === "tool") {
      const mark =
        item.status === "ok" ? "✓" : item.status === "error" ? "✗" : "…";
      out.push(
        `- ${mark} \`${item.name}\`${item.summary ? `: ${item.summary}` : ""}`,
        "",
      );
    }
  }
  return out.join("\n");
}

function slug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 50);
}

const CONTINUABLE = new Set(["length", "tool_limit", "cancelled", "spend_cap"]);

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
        review: m.review ?? undefined,
      });
    }
  }
  return items;
}

const REVIEW_WORDS = {
  approve: "Reviewer approved",
  deny: "Reviewer denied",
  ask: "Reviewer unsure, asking you",
} as const;

function reviewTag(
  review: ReviewVerdict | undefined,
  reviewing: boolean | undefined,
): TemplateResult | typeof nothing {
  if (reviewing && !review) return html`<span class="tag wait">Reviewing…</span>`;
  if (!review) return nothing;
  return html`<span class="tag review ${review.decision}" title=${review.reason}
    >${REVIEW_WORDS[review.decision] ?? "Reviewer"}</span
  >`;
}

function diffLines(diff: string): TemplateResult[] {
  return diff
    .replace(/\n+$/, "")
    .split("\n")
    .map((line) => {
      const cls =
        line.startsWith("+") && !line.startsWith("+++")
          ? "add"
          : line.startsWith("-") && !line.startsWith("---")
            ? "del"
            : line.startsWith("@@")
              ? "hunk"
              : "";
      return html`<span class=${cls}>${line || " "}</span>`;
    });
}

function toolIcon(name: string): string {
  if (name === "shell") return "mdi:console";
  if (name === "call_service") return "mdi:play-circle-outline";
  if (name === "undo") return "mdi:undo";
  if (name === "system") return "mdi:cog-outline";
  if (name === "ha_websocket") return "mdi:api";
  if (name === "integrations") return "mdi:puzzle-outline";
  if (name === "read_reference") return "mdi:book-open-variant";
  if (name === "render_template") return "mdi:code-braces";
  if (name === "get_history") return "mdi:chart-timeline-variant";
  if (name === "web_fetch") return "mdi:web";
  if (name === "web_search") return "mdi:magnify";
  if (name === "get_traces") return "mdi:transit-connection-variant";
  if (name === "get_logbook") return "mdi:history";
  if (name === "read_log") return "mdi:text-box-search-outline";
  if (name.includes("dashboard")) return "mdi:view-dashboard-outline";
  if (name.includes("config_item")) return "mdi:robot-outline";
  if (name.includes("file")) return "mdi:file-document-outline";
  if (
    name.includes("area") ||
    name.includes("device") ||
    name.includes("registry")
  )
    return "mdi:devices";
  if (name.includes("entit") || name.includes("service"))
    return "mdi:format-list-bulleted";
  return "mdi:wrench-outline";
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function greeting(): string {
  const h = new Date().getHours();
  return h < 5
    ? "Good evening"
    : h < 12
      ? "Good morning"
      : h < 18
        ? "Good afternoon"
        : "Good evening";
}

/** Chats grouped by when they were last used; search results stay in one group. */
function groupByDay(
  list: ConvSummary[],
  flat: boolean,
): [string, ConvSummary[]][] {
  if (flat) return [["", list]];
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const today = start.getTime() / 1000;
  const bounds: [string, number][] = [
    ["Today", today],
    ["Yesterday", today - 86400],
    ["Previous 7 days", today - 7 * 86400],
    ["Previous 30 days", today - 30 * 86400],
    ["Older", -Infinity],
  ];
  const groups: [string, ConvSummary[]][] = [];
  for (const c of list) {
    const label = bounds.find(([, t]) => c.updated >= t)![0];
    const g = groups.find(([l]) => l === label);
    if (g) g[1].push(c);
    else groups.push([label, [c]]);
  }
  return groups;
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
      reviewer: "reviewer decides risky actions",
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
