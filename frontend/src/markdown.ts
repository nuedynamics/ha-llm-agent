import DOMPurify from "dompurify";
import { Marked } from "marked";

const marked = new Marked({ gfm: true, breaks: true, async: false });

// Links from model output open in a new tab and never get the panel's opener.
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A") {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer");
  }
});

const cache = new Map<string, string>();

/** Markdown -> sanitized HTML. Finished messages are cached; streaming text is not. */
export function renderMarkdown(text: string, final = true): string {
  if (final) {
    const hit = cache.get(text);
    if (hit !== undefined) return hit;
  }
  const html = DOMPurify.sanitize(marked.parse(text) as string, {
    FORBID_TAGS: ["style", "form", "input", "button", "iframe", "img"],
    FORBID_ATTR: ["style"],
  });
  if (final) {
    if (cache.size > 300) cache.clear();
    cache.set(text, html);
  }
  return html;
}
