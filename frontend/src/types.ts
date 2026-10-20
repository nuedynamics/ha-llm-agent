export interface HassConnection {
  sendMessagePromise<T = unknown>(msg: Record<string, unknown>): Promise<T>;
  subscribeMessage<T = unknown>(
    callback: (event: T) => void,
    msg: Record<string, unknown>,
  ): Promise<() => Promise<void>>;
}

export interface Hass {
  connection: HassConnection;
  user?: { is_admin: boolean; name: string };
  themes?: { darkMode?: boolean };
  locale?: { language: string };
  states?: Record<string, { entity_id: string; attributes: { friendly_name?: string } }>;
  areas?: Record<string, { area_id: string; name: string }>;
  devices?: Record<string, { id: string; name?: string | null; name_by_user?: string | null }>;
}

/** One `@` autocomplete suggestion: what is shown and what goes into the message. */
export interface Mention {
  kind: "entity" | "area" | "device";
  label: string;
  insert: string;
  detail: string;
}

export interface ModelSuggestion {
  id: string;
  label: string;
  input?: number | null;
  output?: number | null;
}

export interface ProviderInfo {
  id: string;
  type: string;
  name: string;
  type_name: string;
  default_model: string;
  models: ModelSuggestion[];
}

export interface Info {
  version: string;
  approval_mode: string;
  providers: ProviderInfo[];
  running: string[];
  my_default?: { provider_id: string; model: string } | null;
}

/** Panel preferences, kept per browser. */
export interface Prefs {
  theme: "auto" | "light" | "dark";
  size: "small" | "normal" | "large";
  compact: boolean;
  toolsOpen: boolean;
  showUsage: boolean;
  send: "enter" | "ctrl";
  listOpen: boolean;
}

export interface Usage {
  input: number;
  output: number;
  cache_read: number;
  cache_write: number;
  cost: number | null;
  review?: { input: number; output: number; cost: number | null };
}

export interface ReviewVerdict {
  decision: "approve" | "deny" | "ask";
  reason: string;
  model: string;
}

export interface ConvSummary {
  id: string;
  title: string;
  updated: number;
  model: string;
  provider_id: string;
  cost: number | null;
  snippet?: string;
}

export interface ToolCallInfo {
  id: string;
  name: string;
  args: Record<string, unknown>;
}

/** One rendered item in the chat. */
export type Item =
  | { kind: "user"; text: string }
  | { kind: "assistant"; text: string }
  | {
      kind: "tool";
      id: string;
      name: string;
      args: Record<string, unknown>;
      status: "running" | "ok" | "error" | "waiting";
      summary?: string;
      preview?: string;
      snapshotId?: string | null;
      undone?: boolean;
      approval?: Approval;
      review?: ReviewVerdict;
      reviewing?: boolean;
    }
  | { kind: "notice"; text: string; error?: boolean; stop?: string };

export interface Approval {
  summary: string;
  reason: string;
  risky: boolean;
  diff: string | null;
}

export interface Conversation {
  id: string;
  title: string;
  provider_id: string;
  model: string;
  usage: Usage;
  stopped?: string | null;
  stopped_text?: string | null;
  messages: StoredMessage[];
}

export type StoredMessage =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; tool_calls: ToolCallInfo[] }
  | {
      role: "tool";
      tool_call_id: string;
      name: string;
      ok: boolean;
      summary: string;
      snapshot_id: string | null;
      undone?: boolean;
      decision: string | null;
      review?: ReviewVerdict | null;
      preview: string;
    };

export type ChatEvent =
  | { type: "delta"; text: string }
  | {
      type: "tool_start";
      call_id: string;
      name: string;
      args: Record<string, unknown>;
    }
  | {
      type: "approval";
      call_id: string;
      name: string;
      risky: boolean;
      reason: string;
      summary: string;
      diff: string | null;
      args: Record<string, unknown>;
    }
  | {
      type: "tool_result";
      call_id: string;
      ok: boolean;
      summary: string;
      snapshot_id: string | null;
      preview: string;
      review?: ReviewVerdict | null;
    }
  | { type: "review_start"; call_id: string; model: string }
  | ({ type: "review"; call_id: string } & ReviewVerdict)
  | { type: "usage"; usage: Usage }
  | { type: "notice"; text: string; stop?: string }
  | { type: "error"; message: string }
  | { type: "done"; usage: Usage };
