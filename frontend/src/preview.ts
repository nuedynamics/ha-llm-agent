// Renders a proposed dashboard with Home Assistant's own cards, before it is saved.
// Only built-in cards that draw the home's entities are rendered. Anything that could
// load an address chosen by the proposal or run code (add-on cards, templates, pictures,
// markdown, maps, web pages, style overrides) is listed as not shown, so a proposal
// can't make the browser fetch or run anything before it is approved.
import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { property, state } from "lit/decorators.js";

type Card = Record<string, unknown>;
interface View {
  title?: string;
  path?: string;
  cards?: Card[];
  sections?: { cards?: Card[] }[];
}
interface CardHelpers {
  createCardElement(config: Card): HTMLElement & { hass?: unknown };
}
declare global {
  interface Window {
    loadCardHelpers?: () => Promise<CardHelpers>;
  }
}

// Built-in cards that draw entities only. Stacks are checked card by card.
const SAFE_CARDS = new Set([
  "alarm-panel",
  "button",
  "calendar",
  "entities",
  "entity",
  "gauge",
  "glance",
  "heading",
  "history-graph",
  "humidifier",
  "light",
  "logbook",
  "sensor",
  "statistic",
  "statistics-graph",
  "thermostat",
  "tile",
  "todo-list",
]);
const STACKS = new Set(["horizontal-stack", "vertical-stack", "grid"]);
const SAFE_ROWS = new Set(["section", "divider"]);
// Text that could point somewhere or be evaluated: addresses, CSS url(), templates
// (Jinja and add-on JavaScript), HTML and add-on element names.
const UNSAFE_TEXT = /\/\/|url\s*\(|\{\{|\{%|\[\[\[|<|custom:|javascript:|data:/i;
const UNSAFE_KEYS = new Set(["card_mod", "style", "image", "image_entity", "camera_image"]);

function safeValue(value: unknown, depth = 0): boolean {
  if (depth > 20) return false;
  if (typeof value === "string") return !UNSAFE_TEXT.test(value);
  if (Array.isArray(value)) return value.every((v) => safeValue(v, depth + 1));
  if (value && typeof value === "object") {
    return Object.entries(value).every(
      ([k, v]) => !UNSAFE_KEYS.has(k) && !UNSAFE_TEXT.test(k) && safeValue(v, depth + 1),
    );
  }
  return true;
}

export function viewCards(view: View): Card[] {
  const cards = [...(view.cards ?? [])];
  for (const section of view.sections ?? []) cards.push(...(section.cards ?? []));
  return cards.filter((c) => c && typeof c === "object");
}

// Home Assistant defines loadCardHelpers once its dashboard code has loaded. When the
// panel is opened directly, that hasn't happened yet, so ask the frontend's own panel
// resolver to load the dashboard panel (nothing is shown or navigated).
async function cardHelpers(): Promise<CardHelpers | undefined> {
  if (!window.loadCardHelpers) {
    try {
      type Resolver = HTMLElement & {
        hass?: unknown;
        _updateRoutes?: () => void;
        routerOptions?: { routes?: Record<string, { load?: () => Promise<unknown> }> };
      };
      const resolver = document.createElement("partial-panel-resolver") as Resolver;
      resolver.hass = { panels: [{ url_path: "llm-preview", component_name: "lovelace" }] };
      resolver._updateRoutes?.();
      await resolver.routerOptions?.routes?.["llm-preview"]?.load?.();
    } catch {
      // fall through: the preview reports that it isn't available
    }
  }
  for (let i = 0; i < 50 && !window.loadCardHelpers; i++) {
    await new Promise((r) => setTimeout(r, 100));
  }
  return window.loadCardHelpers?.();
}

export function previewable(card: Card, depth = 0): boolean {
  if (!card || typeof card !== "object" || depth > 5) return false;
  const type = card.type;
  if (typeof type !== "string") return false;
  if (STACKS.has(type)) {
    const { cards, ...rest } = card;
    return (
      Array.isArray(cards) &&
      cards.every((c) => previewable(c as Card, depth + 1)) &&
      safeValue(rest)
    );
  }
  if (!SAFE_CARDS.has(type)) return false;
  const rows = card.entities;
  if (
    Array.isArray(rows) &&
    !rows.every(
      (r) =>
        typeof r === "string" ||
        (r && typeof r === "object" && (!("type" in r) || SAFE_ROWS.has(String(r.type)))),
    )
  ) {
    return false;
  }
  return safeValue(card);
}

class DashboardPreview extends LitElement {
  @property({ attribute: false }) hass?: unknown;
  @property({ attribute: false }) config?: { views?: View[] };
  @state() private view = 0;
  @state() private error = "";
  private cards: (HTMLElement & { hass?: unknown })[] = [];
  private skipped = 0;

  private get views(): View[] {
    return Array.isArray(this.config?.views) ? this.config!.views : [];
  }

  protected async willUpdate(changed: PropertyValues): Promise<void> {
    if (changed.has("config") || changed.has("view")) await this.build();
    for (const card of this.cards) card.hass = this.hass;
  }

  private async build(): Promise<void> {
    this.cards = [];
    this.skipped = 0;
    const view = this.views[this.view];
    if (!view) return;
    try {
      const helpers = await cardHelpers();
      if (!helpers) throw new Error("card helpers aren't available");
      for (const config of viewCards(view).slice(0, 40)) {
        if (!previewable(config)) {
          this.skipped++;
          continue;
        }
        const el = helpers.createCardElement(config);
        el.hass = this.hass;
        this.cards.push(el);
      }
      this.error = "";
    } catch (err) {
      this.error = `Preview unavailable: ${(err as Error).message}`;
    }
    this.requestUpdate();
  }

  protected render() {
    if (!this.views.length) return html`<p class="note">This dashboard has no views.</p>`;
    return html`
      ${
        this.views.length > 1
          ? html`<div class="tabs">
              ${this.views.map(
                (v, i) =>
                  html`<button
                    class=${i === this.view ? "on" : ""}
                    @click=${() => (this.view = i)}
                  >
                    ${v.title || v.path || `View ${i + 1}`}
                  </button>`,
              )}
            </div>`
          : nothing
      }
      ${this.error ? html`<p class="note">${this.error}</p>` : nothing}
      <div class="grid" inert>${this.cards}</div>
      ${
        this.skipped
          ? html`<p class="note">
              ${
                this.skipped > 1
                  ? `${this.skipped} cards not shown: the preview only draws Home Assistant's own entity cards.`
                  : "1 card not shown: the preview only draws Home Assistant's own entity cards."
              }
            </p>`
          : nothing
      }
    `;
  }

  static styles = css`
    :host {
      display: block;
      padding: 8px 0;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 8px;
      pointer-events: none; /* a preview, not a remote control */
    }
    .tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-bottom: 8px;
    }
    .tabs button {
      font: inherit;
      border: 1px solid var(--divider-color);
      background: none;
      color: inherit;
      border-radius: 12px;
      padding: 2px 10px;
      cursor: pointer;
    }
    .tabs button.on {
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
      border-color: var(--primary-color);
    }
    .note {
      color: var(--secondary-text-color);
      font-size: 0.9em;
      margin: 6px 0;
    }
  `;
}

if (!customElements.get("llm-dashboard-preview")) {
  customElements.define("llm-dashboard-preview", DashboardPreview);
}
