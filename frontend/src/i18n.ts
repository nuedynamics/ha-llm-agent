// The panel's words. English is built in; other languages are small JSON files served
// next to the bundle and fetched once, so the bundle doesn't grow with each language.
import en from "../../custom_components/llm_agent/www/i18n/en.json";

export type Key = keyof typeof en;

/** Languages with a translation file in www/i18n, by Home Assistant language code. */
export const LANGUAGES = [
  "de",
  "es",
  "fr",
  "it",
  "nl",
  "pl",
  "pt-BR",
  "sv",
  "zh-Hans",
  "zh-Hant",
] as const;

let table: Partial<Record<Key, string>> = {};
let loaded = "en";

/** The text for `key` in the loaded language (English when missing), with `{name}`
 * placeholders filled in. */
export function t(key: Key, vars?: Record<string, string | number>): string {
  const text = table[key] ?? en[key];
  return vars ? text.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? String(vars[name]) : m)) : text;
}

/** True when the English table has `key`, e.g. a label for a built-in tool. */
export function has(key: string): key is Key {
  return key in en;
}

/** The file for a Home Assistant language code: an exact match, then a file for the
 * same base language (pt uses pt-BR), else English. */
export function pickLanguage(code: string | undefined): string {
  if (!code) return "en";
  const exact = LANGUAGES.find((l) => l.toLowerCase() === code.toLowerCase());
  if (exact) return exact;
  const base = code.split("-")[0].toLowerCase();
  return LANGUAGES.find((l) => l.split("-")[0].toLowerCase() === base) ?? "en";
}

/** Load the panel's words for a Home Assistant language. True when the table changed. */
export async function loadLanguage(code: string | undefined): Promise<boolean> {
  const lang = pickLanguage(code);
  if (lang === loaded) return false;
  if (lang === "en") {
    table = {};
    loaded = "en";
    return true;
  }
  try {
    // next to the bundle, with its ?v=<version> so an upgrade isn't served stale words
    const here = new URL(import.meta.url);
    const res = await fetch(new URL(`i18n/${lang}.json${here.search}`, here));
    if (!res.ok) return false;
    const data = (await res.json()) as Record<string, unknown>;
    const next: Partial<Record<Key, string>> = {};
    for (const key of Object.keys(en) as Key[]) {
      if (typeof data[key] === "string") next[key] = data[key] as string;
    }
    table = next;
    loaded = lang;
    return true;
  } catch {
    return false; // stay in English
  }
}
