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
import { has, type Key, loadLanguage, t } from "./i18n";
import { renderMarkdown } from "./markdown";
import "./preview";
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
  Photo,
} from "./types";

// Arguments a preview diff shows in full (same list as the server's phone text).
const DIFF_ARGS = new Set(["config", "content", "old", "new", "notes"]);

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
  @state() private previews = new Set<string>();
  @state() private hits: ConvSummary[] | null = null;
  private searchTimer?: number;
  @state() private convId: string | null = null;
  @state() private chatTitle = "New chat";
  @state() private items: Item[] = [];
  @state() private usage: Usage = EMPTY_USAGE;
  @state() private running = false;
  /** Read out by screen readers: replies finished, approvals waiting, errors. */
  @state() private announce = "";
  @state() private editing = false;
  /** Photos waiting to go with the next message. */
  @state() private photos: Photo[] = [];
  /** Bumped whenever the draft photos are cleared, so a photo still being encoded
   * then is thrown away instead of reappearing. */
  private photoGen = 0;
  @state() private providerId = "";
  @state() private model = "";
  /** Models fetched from each provider, loaded the first time the model box is used. */
  @state() private fetched: Record<string, ModelSuggestion[]> = {};
  @state() private showList = false;
  @state() private loadError = "";
  @state() private mentions: Mention[] = [];
  @state() private prefs: Prefs = loadPrefs();
  @state() private showPrefs = false;
  @state() private showNotes = false;
  @state() private notesDraft = "";
  private notesBase = "";
  @state() private notesStatus = "";
  @state() private mentionIndex = 0;
  private mentionStart = -1;

  @query(".composer textarea") private input?: HTMLTextAreaElement;
  @query(".messages") private scroller?: HTMLElement;

  private gen = 0;
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
    } else if (changed.has("hass") && this.hass) {
      const old = (changed.get("hass") as Hass | undefined)?.locale?.language;
      const now = this.hass.locale?.language;
      if (old !== now)
        void loadLanguage(now).then((c) => {
          if (c) this.requestUpdate();
        });
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
      btn.textContent = t("copy");
      btn.addEventListener("click", async () => {
        const code = pre.querySelector("code") ?? pre;
        try {
          await navigator.clipboard.writeText(code.textContent ?? "");
          btn.textContent = t("copied");
        } catch {
          btn.textContent = t("copy_failed");
        }
        setTimeout(() => (btn.textContent = t("copy")), 1500);
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
    if (await loadLanguage(this.hass?.locale?.language))
      this.requestUpdate();
    try {
      this.info = await this.ws.sendMessagePromise<Info>({
        type: "llm_agent/info",
      });
      this.loadError = "";
    } catch (err) {
      this.loadError = (err as { message?: string }).message ?? String(err);
      return;
    }
    this.applyPrefs();
    if (!this.providerId) this.startModel();
    await this.refreshList();
    // Coming back to the panel reopens the chat that was open last time.
    const last = this.convId ?? lastConv();
    if (last && this.convs.some((c) => c.id === last)) {
      try {
        await this.open(last);
      } catch {
        rememberConv(null);
      }
    }
  }

  private async refreshList(): Promise<void> {
    this.convs = await this.ws.sendMessagePromise<ConvSummary[]>({
      type: "llm_agent/conversations/list",
    });
  }

  /** A household member (not an admin): a simpler panel, the server enforces the limits. */
  private get member(): boolean {
    return this.info?.is_admin === false;
  }

  private get provider(): ProviderInfo | undefined {
    return this.info?.providers.find((p) => p.id === this.providerId);
  }

  // ---- conversations -------------------------------------------------------

  private async detach(): Promise<void> {
    this.gen++; // anything still on its way for the old view is dropped
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

  private clearPhotos(): void {
    this.photos = [];
    this.photoGen++;
  }

  private newChat(): void {
    this.editing = false;
    this.clearPhotos();
    void this.detach();
    this.convId = null;
    rememberConv(null);
    this.chatTitle = "New chat";
    this.items = [];
    this.usage = EMPTY_USAGE;
    this.running = false;
    this.showList = false;
    this.startModel();
    this.input?.focus();
  }

  private async open(id: string, retried = false): Promise<void> {
    await this.detach();
    const gen = this.gen;
    this.showList = false;
    this.editing = false;
    this.clearPhotos();
    const conv = await this.ws.sendMessagePromise<Conversation>({
      type: "llm_agent/conversations/get",
      conversation_id: id,
    });
    if (gen !== this.gen) return; // another chat was opened meanwhile
    this.convId = conv.id;
    rememberConv(conv.id);
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
    if (gen !== this.gen || !info.running.includes(id)) return;
    this.running = true;
    this.items = [...this.items, { kind: "assistant", text: "" }];
    let unsub: () => Promise<void>;
    try {
      unsub = await this.ws.subscribeMessage<ChatEvent>(
        (e) => {
          if (gen === this.gen) this.onEvent(e);
        },
        { type: "llm_agent/attach", conversation_id: id },
      );
    } catch {
      // it finished between reading the chat and attaching: read it again
      if (gen === this.gen && !retried) await this.open(id, true);
      else if (gen === this.gen) this.running = false;
      return;
    }
    this.keepOrDrop(gen, unsub);
  }

  /** Install a subscription only if its view is still current; otherwise end it. */
  private keepOrDrop(gen: number, unsub: () => Promise<void>): void {
    if (gen === this.gen) this.unsub = unsub;
    else void unsub().catch(() => undefined);
  }

  /** The call's arguments, in full: what Approve runs must be visible. A diff already
   * shows content, so those arguments are left out next to one. */
  private renderArgs(args: Record<string, unknown> | undefined, hasDiff: boolean) {
    const shown = Object.fromEntries(
      Object.entries(args ?? {}).filter(([k]) => !(hasDiff && DIFF_ARGS.has(k))),
    );
    if (!Object.keys(shown).length) return nothing;
    return html`<pre class="args">${JSON.stringify(shown, null, 2)}</pre>`;
  }

  private async removeConv(id: string, ev: Event): Promise<void> {
    ev.stopPropagation();
    if (!confirm(t("confirm_delete"))) return;
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
    const lastUser = this.lastUserIndex();
    const prev = this.items[lastUser];
    const photos =
      retry !== undefined
        ? (prev?.kind === "user" && prev.images) || []
        : this.photos;
    let text = retry ?? this.input?.value.trim();
    if (!text && photos.length) text = "(photo)";
    if (!text || this.running) return;
    if (retry !== undefined && prev?.kind === "user" && prev.photos && !prev.images) {
      // its photos weren't kept: let the person attach them again rather than
      // silently replacing the answer with one that never saw them
      this.editLast(prev.text, undefined, prev.photos);
      return;
    }
    // to put back if the server refuses the message
    const before = {
      items: this.items,
      draft: this.input?.value ?? "",
      photos: this.photos,
      editing: this.editing,
    };
    if (retry === undefined) {
      this.input!.value = "";
      this.clearPhotos();
      this.autosize();
    }
    this.editing = false;
    const kept =
      rewind && lastUser >= 0 ? this.items.slice(0, lastUser) : this.items;
    this.items = [
      ...kept,
      { kind: "user", text, images: photos.length ? photos : undefined },
      { kind: "assistant", text: "" },
    ];
    this.running = true;
    this.announce = "";
    this.stickToBottom = true;
    const gen = this.gen;
    try {
      const unsub = await this.ws.subscribeMessage<
        ChatEvent | { type: "conversation"; conversation_id: string; title: string }
      >(
        (e) => {
          if (gen !== this.gen) return;
          if (e.type === "conversation") {
            // the chat's real id, never guessed from the list (another tab may add one)
            if (!this.convId) {
              this.convId = e.conversation_id;
              this.chatTitle = e.title || text.slice(0, 60);
              rememberConv(this.convId);
            }
            return;
          }
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
          language: this.hass?.locale?.language || undefined,
          images: photos.length
            ? photos.map(({ media_type, data }) => ({ media_type, data }))
            : undefined,
        },
        // a reconnect must never send the message again
        { resubscribe: false },
      );
      this.keepOrDrop(gen, unsub);
    } catch (err) {
      this.running = false;
      if (gen === this.gen) {
        this.items = before.items;
        this.editing = before.editing;
        if (retry === undefined && this.input) {
          this.input.value = before.draft;
          this.photos = before.photos;
          this.autosize();
        }
      }
      this.push({ kind: "notice", text: errText(err), error: true });
      return;
    }
    await this.refreshList();
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
              phoneOnly: e.phone_only,
              phone: e.phone,
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
        this.announce = e.phone_only
          ? t("announce_phone")
          : t("announce_approval");
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
          ...(e.image?.startsWith("data:image/") ? { image: e.image } : {}),
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
        this.announce = t("announce_error");
        return;
      case "done":
        this.usage = e.usage;
        this.running = false;
        // The log region reads the reply itself; this only marks the end.
        this.announce = t("announce_done");
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
    const card = this.items.find((i) => i.kind === "tool" && i.id === id) as
      | Extract<Item, { kind: "tool" }>
      | undefined;
    const prior = card ? { status: card.status, approval: card.approval } : undefined;
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
      if (prior) this.patchTool(id, prior); // show the buttons again
      this.push({ kind: "notice", text: errText(err), error: true });
    }
  }

  private async undo(item: Extract<Item, { kind: "tool" }>): Promise<void> {
    if (!item.snapshotId || !confirm(t("confirm_undo", { name: item.summary || item.name })))
      return;
    try {
      const res = await this.ws.sendMessagePromise<{ summary: string }>({
        type: "llm_agent/undo",
        snapshot_id: item.snapshotId,
        ...(this.convId ? { conversation_id: this.convId } : {}),
      });
      this.patchTool(item.id, { undone: true });
      this.push({ kind: "notice", text: t("undone_notice", { summary: res.summary }) });
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
    this.input!.value = t("continue_message");
    void this.send(undefined, overCap);
  }

  private editLast(text: string, images?: Photo[], kept?: number): void {
    this.editing = true;
    this.clearPhotos();
    this.photos = images ?? [];
    if (kept && !images) this.photosNotKept();
    this.input!.value = text;
    this.autosize();
    this.input!.focus();
  }

  private cancelEdit(): void {
    this.editing = false;
    this.clearPhotos();
    this.input!.value = "";
    this.autosize();
  }

  private async onPick(ev: Event): Promise<void> {
    const input = ev.target as HTMLInputElement;
    await this.addPhotos([...(input.files ?? [])]);
    input.value = "";
  }

  private async onPaste(ev: ClipboardEvent): Promise<void> {
    const files = [...(ev.clipboardData?.files ?? [])].filter((f) =>
      f.type.startsWith("image/"),
    );
    if (!files.length) return;
    ev.preventDefault();
    await this.addPhotos(files);
  }

  private photosNotKept(): void {
    this.push({
      kind: "notice",
      text: t("photos_not_kept"),
    });
  }

  private async addPhotos(files: File[]): Promise<void> {
    const gen = this.photoGen;
    for (const file of files) {
      if (this.photos.length >= MAX_PHOTOS) break;
      try {
        const photo = await shrinkPhoto(file);
        // cleared, sent or switched chats while encoding: drop it
        if (gen !== this.photoGen || this.photos.length >= MAX_PHOTOS) return;
        this.photos = [...this.photos, photo];
      } catch {
        this.push({
          kind: "notice",
          text: t("photo_unreadable", { name: file.name || t("that_picture") }),
          error: true,
        });
      }
    }
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
    if (ev.key === "Escape" && this.running && !ev.isComposing) {
      ev.preventDefault();
      void this.stop();
      return;
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
      return html`<div class="empty">${t("load_error", { error: this.loadError })}</div>`;
    }
    if (this.info && !this.info.providers.length) {
      return html`<div class="empty">${t("no_provider")}</div>`;
    }
    const listOpen = this.narrow ? this.showList : this.prefs.listOpen;
    const lastUser = this.convId ? this.lastUserIndex() : -1;
    return html`
      <div
        class="layout ${this.narrow ? "narrow" : ""}"
        @click=${this.closePrefsOutside}
        @keydown=${(e: KeyboardEvent) => {
          if (e.key === "Escape") {
            this.showPrefs = false;
            this.showNotes = false;
          }
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
              title=${listOpen ? t("hide_chats") : t("show_chats")}
              aria-label=${t("conversations")}
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
            <div class="title">${chatName(this.chatTitle)}</div>
            ${
              this.items.length
                ? html`<button
                    class="icon"
                    title=${t("export_title")}
                    aria-label=${t("export")}
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
                    title=${t("new_chat")}
                    aria-label=${t("new_chat")}
                    @click=${this.newChat}
                  >
                    <ha-icon icon="mdi:square-edit-outline"></ha-icon>
                  </button>`
            }
            ${
              this.member
                ? nothing
                : html`<button
                    class="icon gear"
                    title=${t("home_notes")}
                    aria-label=${t("home_notes")}
                    aria-expanded=${this.showNotes}
                    @click=${this.toggleNotes}
                  >
                    <ha-icon icon="mdi:notebook-outline"></ha-icon>
                  </button>`
            }
            ${this.showNotes && !this.member ? this.renderNotes() : nothing}
            <button
              class="icon gear"
              title=${t("panel_settings")}
              aria-label=${t("panel_settings")}
              aria-expanded=${this.showPrefs}
              @click=${() => {
                this.showPrefs = !this.showPrefs;
                this.showNotes = false;
              }}
            >
              <ha-icon icon="mdi:cog-outline"></ha-icon>
            </button>
            ${this.showPrefs ? this.renderPrefs() : nothing}
          </header>
          <div class="sr-only" role="status" aria-live="polite">${this.announce}</div>
          <div class="messages" role="log" aria-label=${t("conversation")} @scroll=${this.onScroll}>
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
          title=${t("new_chat")}
          aria-label=${t("new_chat")}
          @click=${this.newChat}
        >
          <ha-icon icon="mdi:square-edit-outline"></ha-icon>
        </button>
      </div>
      <label class="search">
        <ha-icon icon="mdi:magnify"></ha-icon>
        <input
          type="search"
          placeholder=${t("search_chats")}
          aria-label=${t("search_chats")}
          .value=${this.query}
          @input=${this.onSearch}
        />
      </label>
      <div class="convs">
        ${
          this.hits && !this.hits.length
            ? html`<div class="nav-empty">${t("no_matches")}</div>`
            : nothing
        }
        ${!this.hits && !this.convs.length ? html`<div class="nav-empty">${t("no_chats")}</div>` : nothing}
        ${groupByDay(list, !!this.hits).map(
          ([label, convs]) => html`
            ${label ? html`<div class="group">${t(label)}</div>` : nothing}
            ${convs.map(
              (c) =>
                html`<div
                  class="conv ${c.id === this.convId ? "active" : ""}"
                  @click=${() => this.open(c.id)}
                >
                  <span class="conv-title"
                    >${
                      c.source === "action"
                        ? html`<ha-icon
                            class="auto"
                            icon="mdi:robot-outline"
                            title=${t("started_by_automation")}
                          ></ha-icon>`
                        : nothing
                    }${chatName(c.title)}${
                      c.snippet && c.snippet !== c.title
                        ? html`<small class="snippet">${c.snippet}</small>`
                        : nothing
                    }</span
                  >
                  <button
                    class="icon del"
                    title=${t("delete")}
                    aria-label=${t("delete_chat")}
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

  /** Close the panel settings and home notes popovers on a click anywhere outside them. */
  private closePrefsOutside(ev: Event): void {
    if (!this.showPrefs && !this.showNotes) return;
    const inside = ev
      .composedPath()
      .some(
        (el) =>
          el instanceof HTMLElement &&
          (el.classList.contains("prefs") || el.classList.contains("gear")),
      );
    if (!inside) {
      this.showPrefs = false;
      this.showNotes = false;
    }
  }

  private async toggleNotes(): Promise<void> {
    this.showNotes = !this.showNotes;
    this.showPrefs = false;
    if (!this.showNotes) return;
    this.notesDraft = this.info?.notes ?? "";
    this.notesBase = this.notesDraft;
    this.notesStatus = "";
    try {
      // The AI or another window may have changed them since the panel loaded.
      const info = await this.ws.sendMessagePromise<Info>({ type: "llm_agent/info" });
      this.info = info;
      if (this.showNotes && this.notesDraft === this.notesBase) {
        this.notesDraft = info.notes ?? "";
        this.notesBase = this.notesDraft;
      }
    } catch {
      /* keep what was loaded */
    }
  }

  private async saveNotes(): Promise<void> {
    const sent = this.notesDraft;
    try {
      const res = await this.ws.sendMessagePromise<{ notes: string }>({
        type: "llm_agent/notes",
        notes: sent,
        base: this.notesBase,
      });
      if (this.info) this.info = { ...this.info, notes: res.notes };
      if (this.notesDraft === sent) this.notesDraft = res.notes; // keep newer typing
      this.notesBase = res.notes;
      this.notesStatus = t("saved");
    } catch (err) {
      this.notesStatus = (err as { message?: string }).message || t("could_not_save");
    }
  }

  private renderNotes(): TemplateResult {
    const max = this.info?.notes_max ?? 2000;
    const left = max - this.notesDraft.trim().length;
    return html`<div class="prefs notes" role="dialog" aria-label=${t("home_notes")}>
      <strong>${t("home_notes")}</strong>
      <textarea
        rows="8"
        maxlength=${max + 200}
        placeholder=${t("notes_placeholder")}
        .value=${this.notesDraft}
        @input=${(e: Event) => {
          this.notesDraft = (e.target as HTMLTextAreaElement).value;
          this.notesStatus = "";
        }}
      ></textarea>
      <div class="mine">
        <button class="small" ?disabled=${left < 0} @click=${this.saveNotes}>${t("save")}</button>
        <span class=${left < 0 ? "over" : "hint"}>${t("characters_left", { count: left })}</span>
        ${this.notesStatus ? html`<span class="hint">${this.notesStatus}</span>` : nothing}
      </div>
      <div class="hint">${t("notes_hint")}</div>
    </div>`;
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
      ? `${this.info?.providers.find((x) => x.id === mine.provider_id)?.name ?? "?"} · ${mine.model || t("model_provider_default")}`
      : "";
    return html`<div class="prefs" role="dialog" aria-label=${t("panel_settings")}>
      ${pick("theme", t("theme"), [
        ["auto", t("theme_auto")],
        ["light", t("theme_light")],
        ["dark", t("theme_dark")],
      ])}
      ${pick("size", t("text_size"), [
        ["small", t("size_small")],
        ["normal", t("size_normal")],
        ["large", t("size_large")],
      ])}
      ${pick("send", t("send_with"), [
        ["enter", "Enter"],
        ["ctrl", "Ctrl+Enter"],
      ])}
      ${check("compact", t("compact_layout"))}
      ${check("toolsOpen", t("expand_tools"))}
      ${check("showUsage", t("show_usage"))}
      ${
        this.member
          ? nothing
          : html`<div class="mine">
        <div>${t("my_default", { model: mine ? mineName : t("provider_default") })}</div>
        <button class="small" @click=${() => this.setMyDefault()}>
          ${t("use_current_model")}
        </button>
        ${
          mine
            ? html`<button
                class="small ghost"
                @click=${() => this.setMyDefault(true)}
              >
                ${t("clear")}
              </button>`
            : nothing
        }
      </div>`
      }
      <div class="hint">
        ${t("prefs_hint")}${this.member ? "" : ` ${t("prefs_hint_admin")}`}
      </div>
    </div>`;
  }

  private renderWelcome(): TemplateResult {
    const tips = welcomeTips(this.hass, this.member);
    const name = this.hass?.user?.name?.split(" ")[0];
    return html`<div class="welcome">
      <div class="logo"><ha-icon icon="mdi:robot-happy-outline"></ha-icon></div>
      <h2>${name ? t("greeting_name", { greeting: greeting(), name }) : greeting()}</h2>
      ${
        this.member
          ? html`<p>${t("welcome_member")}</p>`
          : html`<p>${t("welcome_admin")}</p>
              <span class="mode-chip"
                ><ha-icon icon="mdi:shield-check-outline"></ha-icon
                >${modeName(this.info?.approval_mode)}</span
              >`
      }
      <div class="tips">
        ${tips.map(
          (tip) =>
            html`<button
              class="tip"
              @click=${() => {
                this.input!.value = tip.text;
                this.input!.focus();
                this.autosize();
              }}
            >
              <ha-icon icon=${tip.icon}></ha-icon>
              <span>${tip.text}</span>
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
                    title=${t("edit")}
                    aria-label=${t("edit")}
                    @click=${() => this.editLast(item.text, item.images, item.photos)}
                  >
                    <ha-icon icon="mdi:pencil-outline"></ha-icon>
                  </button>
                  <button
                    class="icon"
                    title=${t("retry")}
                    aria-label=${t("retry")}
                    @click=${() => this.send(item.text)}
                  >
                    <ha-icon icon="mdi:refresh"></ha-icon>
                  </button>
                </div>`
              : nothing
          }
          <div class="msg user">${this.renderPhotos(item)}${item.text}</div>
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
                  ${item.stop === "spend_cap" ? t("continue_anyway") : t("continue")}
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

  private renderPreview(item: Extract<Item, { kind: "tool" }>): TemplateResult {
    const config = item.args?.config;
    if (!config || typeof config !== "object") return html``;
    const open = this.previews.has(item.id);
    return html`<div class="preview">
      <button
        class="ghost small"
        @click=${() => {
          const next = new Set(this.previews);
          if (open) next.delete(item.id);
          else next.add(item.id);
          this.previews = next;
        }}
      >
        <ha-icon icon=${open ? "mdi:eye-off-outline" : "mdi:eye-outline"}></ha-icon>
        ${open ? t("hide_preview") : t("preview_dashboard")}
      </button>
      ${
        open
          ? html`<llm-dashboard-preview .hass=${this.hass} .config=${config}></llm-dashboard-preview>`
          : nothing
      }
    </div>`;
  }

  /** When each notes card appeared; its Save button waits a moment so it isn't clicked by habit. */
  private noteCardSince = new Map<string, number>();

  /** A suggested change to the home notes: its own look and words, unlike an action approval. */
  private renderNoteSuggestion(item: Extract<Item, { kind: "tool" }>): TemplateResult {
    const lines = (item.approval?.diff ?? "").replace(/\n+$/, "").split("\n");
    const added = lines.filter((l) => l.startsWith("+") && !l.startsWith("+++")).map((l) => l.slice(1));
    const removed = lines.filter((l) => l.startsWith("-") && !l.startsWith("---")).map((l) => l.slice(1));
    let since = this.noteCardSince.get(item.id);
    if (since === undefined) {
      since = Date.now();
      this.noteCardSince.set(item.id, since);
      setTimeout(() => this.requestUpdate(), NOTE_ARM_MS + 50);
    }
    const armed = Date.now() - since >= NOTE_ARM_MS;
    return html`<div class="note-suggestion" role="group" aria-label=${t("suggested_note")}>
      <div class="note-head">
        <ha-icon icon="mdi:notebook-edit-outline"></ha-icon>
        <div>
          <strong>${t("note_question")}</strong>
          <small>${t("note_explain")}</small>
        </div>
      </div>
      ${added.filter((l) => l.trim()).length
        ? html`<ul class="note-lines add">
            ${added.filter((l) => l.trim()).map((l) => html`<li>${l}</li>`)}
          </ul>`
        : nothing}
      ${removed.filter((l) => l.trim()).length
        ? html`<div class="note-label">${t("forget")}</div>
            <ul class="note-lines del">
              ${removed.filter((l) => l.trim()).map((l) => html`<li>${l}</li>`)}
            </ul>`
        : nothing}
      <div class="note-actions">
        <button class="ghost" @click=${() => this.answer(item.id, false)}>
          ${t("note_no")}
        </button>
        <button
          class="note-save"
          ?disabled=${!armed}
          title=${armed ? t("note_save_title") : t("read_it_first")}
          @click=${() => this.answer(item.id, true)}
        >
          ${t("save_to_notes")}
        </button>
      </div>
    </div>`;
  }

  private renderTool(item: Extract<Item, { kind: "tool" }>): TemplateResult {
    const approval = item.approval;
    if (approval && !approval.phoneOnly && item.name === "update_home_notes") return this.renderNoteSuggestion(item);
    const status = {
      running: html`<span class="spinner" aria-label=${t("running")}></span>`,
      ok: html`<ha-icon
        class="st ok"
        icon="mdi:check-circle"
        aria-label=${t("done")}
      ></ha-icon>`,
      error: html`<ha-icon
        class="st error"
        icon="mdi:alert-circle"
        aria-label=${t("failed")}
      ></ha-icon>`,
      waiting: html`<span class="tag wait">${t("waiting_for_you")}</span>`,
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
                >${t("needs_approval")}${approval.reason ? html`<span class="why"> · ${approval.reason}</span>` : nothing}</span
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
          ${item.undone ? html`<span class="tag">${t("undone")}</span>` : nothing}
          ${reviewTag(item.review, item.reviewing)}
          ${status}
          ${
            item.snapshotId && !item.undone && item.status === "ok" && !this.member
              ? html`<button
                  class="ghost small undo"
                  title=${t("undo_title")}
                  @click=${(e: Event) => {
                    e.preventDefault();
                    e.stopPropagation();
                    void this.undo(item);
                  }}
                >
                  ${t("undo")}
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
                  ><b>${item.review.model ? t("reviewer_model", { model: item.review.model }) : t("reviewer")}:</b>
                  ${item.review.reason || t(REVIEW_WORDS[item.review.decision])}</span
                >
              </div>`
            : nothing
        }
        ${approval?.diff ? html`<pre class="diff">${diffLines(approval.diff)}</pre>` : nothing}
        ${approval && item.name === "save_dashboard" ? this.renderPreview(item) : nothing}
        ${this.renderArgs(item.args, Boolean(approval?.diff))}
        ${item.preview && !approval ? html`<pre class="result">${item.preview}</pre>` : nothing}
      </details>
        ${
          item.image
            ? html`<img class="snapshot" src=${item.image} alt=${t("camera_snapshot")} />`
            : nothing
        }
      ${
        approval?.phoneOnly
          ? html`<div class="approval phone-wait">
              <ha-icon icon="mdi:cellphone-message"></ha-icon>
              ${t("phone_wait")}
            </div>`
          : approval
          ? html`<div class="approval">
              <input
                id="note-${item.id}"
                placeholder=${t("approval_note")}
                aria-label=${t("approval_note")}
              />
              <button
                class="ghost danger-text"
                @click=${() => this.answer(item.id, false)}
              >
                ${t("deny")}
              </button>
              <button
                class="primary"
                @click=${() => this.answer(item.id, true)}
              >
                ${t("approve")}
              </button>
            </div>`
          : nothing
      }
    </div>`;
  }

  /** Photos on a sent message. The bubble keeps whitespace, so this adds none. */
  private renderPhotos(item: Item): TemplateResult | typeof nothing {
    if (item.kind !== "user") return nothing;
    if (item.images?.length)
      return html`<div class="photos">${item.images.map((p) => html`<img src=${p.url} alt=${t("your_photo")} />`)}</div>`;
    if (item.photos)
      return html`<div class="photo-note"><ha-icon icon="mdi:image-outline"></ha-icon>${photoCount(item.photos)} ${t("not_kept")}</div>`;
    return nothing;
  }

  private renderComposer(): TemplateResult {
    const p = this.provider;
    const listId = "models";
    return html`<footer>
      <div class="composer">
        <textarea
          rows="1"
          placeholder=${t("composer_placeholder")}
          @keydown=${this.onKey}
          @input=${this.onInput}
          @paste=${this.onPaste}
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
        ${
          this.photos.length
            ? html`<div class="attached">
                ${this.photos.map(
                  (p, i) =>
                    html`<span class="thumb">
                      <img src=${p.url} alt=${t("photo_to_send")} />
                      <button
                        class="icon"
                        title=${t("remove_photo")}
                        aria-label=${t("remove_photo")}
                        @click=${() =>
                          (this.photos = this.photos.filter((_, j) => j !== i))}
                      >
                        <ha-icon icon="mdi:close"></ha-icon>
                      </button>
                    </span>`,
                )}
              </div>`
            : nothing
        }
        <div class="toolbar">
          <label
            class="attach icon"
            title=${t("add_photo_title")}
            ?hidden=${this.photos.length >= MAX_PHOTOS}
          >
            <ha-icon icon="mdi:image-plus-outline"></ha-icon>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              multiple
              aria-label=${t("add_photo")}
              ?disabled=${this.running}
              @change=${this.onPick}
            />
          </label>
          ${
            this.member
              ? nothing
              : html`<label
            class="model-pill"
            title=${this.modelError || t("provider_and_model")}
          >
            <ha-icon icon="mdi:creation-outline"></ha-icon>
            <select
              aria-label=${t("provider")}
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
              aria-label=${t("model")}
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
          </label>`
          }
          <span class="spacer"></span>
          ${
            this.running
              ? html`<button
                  class="send stop"
                  title=${t("stop")}
                  aria-label=${t("stop")}
                  @click=${this.stop}
                >
                  <ha-icon icon="mdi:stop"></ha-icon>
                </button>`
              : html`<button
                  class="send"
                  title=${t("send")}
                  aria-label=${t("send")}
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
                >${t("editing_last")}
                <button class="small ghost" @click=${this.cancelEdit}>
                  ${t("cancel")}
                </button></span
              >`
            : nothing
        }
        <span
          class="usage"
          ?hidden=${!this.prefs.showUsage}
          title=${t("usage_title")}
        >
          ${t("usage_line", {
            input: fmtTokens(this.usage.input + this.usage.cache_read + this.usage.cache_write),
            output: fmtTokens(this.usage.output),
          })}
          ${this.usage.cache_read ? ` · ${t("usage_cached", { count: fmtTokens(this.usage.cache_read) })}` : nothing}
          ·
          ${this.usage.cost == null ? t("cost_na") : `~$${this.usage.cost.toFixed(this.usage.cost < 1 ? 4 : 2)}`}
          ${
            this.usage.review
              ? ` · ${t("reviewer_usage", {
                  tokens: fmtTokens(this.usage.review.input + this.usage.review.output),
                  cost: this.usage.review.cost == null ? t("cost_na") : `~$${this.usage.review.cost.toFixed(4)}`,
                })}`
              : nothing
          }
        </span>
      </div>
    </footer>`;
  }
}

// ---- helpers ----------------------------------------------------------------

const PREFS_KEY = "llm-agent-prefs";
const LAST_CONV_KEY = "llm-agent-last-chat";

function lastConv(): string | null {
  try {
    return localStorage.getItem(LAST_CONV_KEY);
  } catch {
    return null;
  }
}

function rememberConv(id: string | null): void {
  try {
    if (id) localStorage.setItem(LAST_CONV_KEY, id);
    else localStorage.removeItem(LAST_CONV_KEY);
  } catch {
    // private mode: the panel opens on a new chat next time
  }
}
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
const NOTE_ARM_MS = 1500;

/** Starter requests for the empty chat, using this home's own area names. */
export function welcomeTips(hass: any, member = false): { text: string; icon: string }[] {
  const areas = Object.values(hass?.areas ?? {})
    .map((a: any) => String(a.name ?? ""))
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b));
  const room = areas[0] ?? t("living_room");
  const energy = Object.values(hass?.states ?? {}).some(
    (s: any) => s.attributes?.device_class === "energy",
  );
  if (member)
    return [
      { text: t("tip_lights", { room }), icon: "mdi:lightbulb-group-outline" },
      { text: t("tip_anything_on"), icon: "mdi:power" },
      { text: t("tip_temperature"), icon: "mdi:thermometer" },
    ];
  return [
    { text: t("tip_lights", { room }), icon: "mdi:lightbulb-group-outline" },
    { text: t("tip_dashboard_room", { room }), icon: "mdi:view-dashboard-outline" },
    {
      text: t("tip_dashboard_all"),
      icon: "mdi:view-dashboard-edit-outline",
    },
    {
      text: t("tip_automation"),
      icon: "mdi:robot-outline",
    },
    energy
      ? { text: t("tip_energy"), icon: "mdi:lightning-bolt-outline" }
      : { text: t("tip_unavailable"), icon: "mdi:stethoscope" },
    { text: t("tip_batteries"), icon: "mdi:battery-alert-variant-outline" },
  ];
}

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
  const out = [`# ${chatName(title)}`, ""];
  for (const item of items) {
    if (item.kind === "user") {
      const n = item.images?.length || item.photos || 0;
      const note = n ? ` _(${photoCount(n)})_` : "";
      out.push(`**${t("you")}:** ${item.text}${note}`, "");
    }
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
    if (m.role === "user")
      items.push({ kind: "user", text: m.content, photos: m.photos });
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
        summary: m.summary || (m.decision === "denied" ? t("denied") : ""),
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
  approve: "reviewer_approved",
  deny: "reviewer_denied",
  ask: "reviewer_unsure",
} as const;

function reviewTag(
  review: ReviewVerdict | undefined,
  reviewing: boolean | undefined,
): TemplateResult | typeof nothing {
  if (reviewing && !review) return html`<span class="tag wait">${t("reviewing")}</span>`;
  if (!review) return nothing;
  return html`<span class="tag review ${review.decision}" title=${review.reason}
    >${t(REVIEW_WORDS[review.decision] ?? "reviewer")}</span
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
  if (name === "camera_snapshot") return "mdi:cctv";
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

/** The server names a chat "New chat" until its first message gives it a title. */
function chatName(title: string): string {
  return title === "New chat" ? t("new_chat") : title;
}

function photoCount(n: number): string {
  return n === 1 ? t("one_photo") : t("n_photos", { count: n });
}

function greeting(): string {
  const h = new Date().getHours();
  return t(
    h < 5
      ? "greeting_evening"
      : h < 12
        ? "greeting_morning"
        : h < 18
          ? "greeting_afternoon"
          : "greeting_evening",
  );
}

/** Chats grouped by when they were last used; search results stay in one group. */
function groupByDay(
  list: ConvSummary[],
  flat: boolean,
): [Key | "", ConvSummary[]][] {
  if (flat) return [["", list]];
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const today = start.getTime() / 1000;
  const bounds: [Key, number][] = [
    ["today", today],
    ["yesterday", today - 86400],
    ["previous_7", today - 7 * 86400],
    ["previous_30", today - 30 * 86400],
    ["older", -Infinity],
  ];
  const groups: [Key | "", ConvSummary[]][] = [];
  for (const c of list) {
    const label = bounds.find(([, t]) => c.updated >= t)![0];
    const g = groups.find(([l]) => l === label);
    if (g) g[1].push(c);
    else groups.push([label, [c]]);
  }
  return groups;
}

/** A built-in tool's name in the user's language; MCP and unknown tools as they are. */
function toolLabel(name: string): string {
  const key = `tool_${name}`;
  return has(key) ? t(key) : name.replace(/_/g, " ");
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
  const key = (
    {
      ask_all: "mode_ask_all",
      ask_risky: "mode_ask_risky",
      reviewer: "mode_reviewer",
      autopilot: "mode_autopilot",
      read_only: "mode_read_only",
    } as Record<string, Key>
  )[mode ?? ""];
  return key ? t(key) : "";
}

function errText(err: unknown): string {
  return (err as { message?: string }).message ?? String(err);
}

if (!customElements.get("llm-agent-panel")) {
  customElements.define("llm-agent-panel", LlmAgentPanel);
}

const MAX_PHOTOS = 3;
const PHOTO_SIDE = 1568; // larger pictures cost more tokens without helping the model
// Base64 characters per photo: three of them plus the text stay well under Home
// Assistant's 4 MiB WebSocket message limit, even for noisy pictures.
const PHOTO_BUDGET = 1_000_000;

/** Re-encode a picture as a JPEG of at most PHOTO_SIDE pixels a side. This keeps the
 * message well under Home Assistant's WebSocket limit and drops metadata such as the
 * location the photo was taken. */
async function shrinkPhoto(file: File): Promise<Photo> {
  const bitmap = await createImageBitmap(file);
  try {
    let side = Math.min(PHOTO_SIDE, Math.max(bitmap.width, bitmap.height));
    for (;;) {
      for (const quality of [0.85, 0.7, 0.55]) {
        const url = encodeJpeg(bitmap, side, quality);
        const data = url.slice(url.indexOf(",") + 1);
        if (data.length <= PHOTO_BUDGET) return { media_type: "image/jpeg", data, url };
      }
      if (side <= 256) throw new Error("photo too detailed to send");
      side = Math.round(side * 0.75);
    }
  } finally {
    bitmap.close();
  }
}

function encodeJpeg(bitmap: ImageBitmap, side: number, quality: number): string {
  const scale = Math.min(1, side / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#fff"; // transparent areas would turn black in a JPEG
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", quality);
}
