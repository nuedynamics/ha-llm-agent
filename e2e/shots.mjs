// README screenshots: opens each stored conversation in the panel and captures it.
// Usage: node shots.mjs <ha-url> <tokens-json-file> <out-dir>
// Run against a HA that live_check.py has already populated (LIVE_MODEL=... KEEP=1 run.sh).
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

const [ha, tokenFile, out] = process.argv.slice(2);
const tokens = JSON.parse(readFileSync(tokenFile, "utf8"));
const browser = await chromium.launch(
  process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
);

async function open(viewport) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 2 });
  await page.addInitScript((t) => localStorage.setItem("hassTokens", JSON.stringify(t)), tokens);
  await page.goto(`${ha}/llm-agent`);
  await page.locator("llm-agent-panel textarea").waitFor({ timeout: 60000 });
  return page;
}

const page = await open({ width: 1280, height: 800 });
const panel = page.locator("llm-agent-panel");
await page.screenshot({ path: `${out}/welcome.png` });
const convs = panel.locator(".conv");
const n = await convs.count();
for (let i = 0; i < n; i++) {
  await convs.nth(i).click();
  await page.waitForTimeout(800);
  const title = (await convs.nth(i).innerText()).trim().toLowerCase();
  const slug = title.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40);
  // Expand the cards that changed something (they have Undo), so the change shows;
  // lookups stay folded.
  for (const s of await panel.locator(".tool summary", { hasText: "Undo" }).all()) await s.click();
  await page.waitForTimeout(300);
  await panel.locator(".messages").evaluate((el) => el.scrollTo(0, 0));
  await page.waitForTimeout(200);
  await page.screenshot({ path: `${out}/conv-${i}-${slug}.png` });
}

const phone = await open({ width: 390, height: 844 });
await phone.screenshot({ path: `${out}/phone.png` });
await browser.close();
console.log(`${n} conversations captured in ${out}`);
