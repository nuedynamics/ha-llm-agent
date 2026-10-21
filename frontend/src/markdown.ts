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
  // Nothing in a reply may load by itself: a URL could carry home data out without an
  // approval. HTML only (no SVG/MathML), no media, no resource attributes; links need a click.
  const html = DOMPurify.sanitize(marked.parse(text) as string, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: [
      "style", "form", "input", "button", "iframe", "img", "image", "video", "audio",
      "source", "picture", "track", "object", "embed", "link", "meta", "base", "svg", "math",
    ],
    FORBID_ATTR: ["style", "src", "srcset", "poster", "background", "ping", "xlink:href", "formaction"],
  });
  if (final) {
    if (cache.size > 300) cache.clear();
    cache.set(text, html);
  }
  return html;
}
