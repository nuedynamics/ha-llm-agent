// Browser test of the LLM Agent panel against a real HA and the stub model.
// Usage: node panel.mjs <ha-url> <tokens-json-file> <config-dir> [screenshot-dir]
import { readFileSync, existsSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { deflateSync, crc32 } from "node:zlib";
import { chromium } from "playwright";

const [ha, tokenFile, configDir, shots = "/tmp"] = process.argv.slice(2);
const tokens = JSON.parse(readFileSync(tokenFile, "utf8"));
let page;
const fail = async (msg) => {
  console.error("FAIL:", msg);
  if (page) await page.screenshot({ path: `${shots}/llm-agent-failure.png` }).catch(() => {});
  process.exit(1);
};
process.on("unhandledRejection", (err) => fail(String(err)));
process.on("uncaughtException", (err) => fail(String(err)));

async function state(entityId) {
  const r = await fetch(`${ha}/api/states/${entityId}`, {
    headers: { authorization: `Bearer ${tokens.access_token}` },
  });
  return (await r.json()).state;
}

const browser = await chromium.launch(
  process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
);
page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
page.on("dialog", (d) => d.accept());
await page.addInitScript((t) => localStorage.setItem("hassTokens", JSON.stringify(t)), tokens);

await page.goto(`${ha}/llm-agent`);
const panel = page.locator("llm-agent-panel");
const box = panel.locator("textarea");
await box.waitFor({ timeout: 60000 });
await panel.locator(".welcome h2").waitFor();

// 1. device control runs without approval in the default mode
await box.fill("please switch on the test switch");
await box.press("Enter");
await page.getByText("Done, the test switch is on.").waitFor({ timeout: 30000 });
if ((await state("input_boolean.e2e_switch")) !== "on") fail("switch did not turn on");
if (!(await panel.locator(".usage").innerText()).includes("~$")) fail("no cost estimate shown");
await page.screenshot({ path: `${shots}/llm-agent-1-control.png` });

// 2. a risky change waits for approval and shows a diff
await box.fill("write file please");
await box.press("Enter");
const approve = panel.getByRole("button", { name: "Approve" });
await approve.waitFor({ timeout: 30000 });
const diffText = await panel.locator("pre.diff").innerText();
if (!diffText.includes("+hello from the e2e test")) fail("diff missing");
if (!/\n\+hello from the e2e test/.test(diffText)) fail("diff lines are not on separate lines");
await page.screenshot({ path: `${shots}/llm-agent-2-approval.png` });
if (existsSync(`${configDir}/e2e_note.txt`)) fail("file written before approval");
await approve.click();
await page.getByText("I wrote").waitFor({ timeout: 30000 });
if (!existsSync(`${configDir}/e2e_note.txt`)) fail("file not written after approval");

// 3. undo removes it again
await panel.getByRole("button", { name: "Undo" }).click();
await panel.getByText(/Undone:/).waitFor({ timeout: 15000 });
if (existsSync(`${configDir}/e2e_note.txt`)) fail("undo did not remove the file");
await page.screenshot({ path: `${shots}/llm-agent-3-undo.png` });

// 4. history survives a reload, and the panel reopens the last chat by itself
await page.reload();
await page.getByText("Done, the test switch is on.").waitFor({ timeout: 15000 });
if (!(await panel.locator(".tag", { hasText: "undone" }).count())) fail("undone state lost on reload");
if (await panel.getByRole("button", { name: "Undo" }).count()) fail("Undo offered again after reload");

// 5. phone layout: the chat fills the screen and the conversation list opens on demand
await page.setViewportSize({ width: 390, height: 844 });
await page.reload();
await box.waitFor({ timeout: 30000 });
await panel.getByRole("button", { name: "Conversations" }).click();
await panel.locator(".conv").first().click();
await page.getByText("Done, the test switch is on.").waitFor({ timeout: 15000 });
const composer = await panel.locator(".composer").boundingBox();
if (!composer || composer.x < 0 || composer.x + composer.width > 390 || composer.y + composer.height > 844)
  fail(`composer is off screen on a phone: ${JSON.stringify(composer)}`);
await page.screenshot({ path: `${shots}/llm-agent-4-phone.png` });

// 6. retry replaces the last turn instead of adding another one
await page.setViewportSize({ width: 1280, height: 800 });
await panel.getByRole("button", { name: "Retry" }).click();
await panel.getByRole("button", { name: "Deny" }).waitFor({ timeout: 15000 });
if ((await panel.locator(".msg.user", { hasText: "write file please" }).count()) !== 1)
  fail("retry duplicated the user message");
if (await panel.locator(".tag", { hasText: "undone" }).count()) fail("retry kept the old attempt");
await panel.getByRole("button", { name: "Deny" }).click();
await panel.getByRole("button", { name: "Retry" }).waitFor({ timeout: 15000 });
await page.screenshot({ path: `${shots}/llm-agent-5-retry.png` });

// 7. a cut-off reply says why and offers Continue, also after reopening the chat
await panel.getByRole("button", { name: "New chat" }).first().click();
await box.fill("tell me a long story");
await box.press("Enter");
const cont = panel.getByRole("button", { name: "Continue" });
await cont.waitFor({ timeout: 15000 });
if (!(await panel.getByText("cut off at the length limit").count())) fail("no cut-off notice");
await panel.locator(".conv", { hasText: "tell me a long story" }).click();
await cont.waitFor({ timeout: 15000 });
await cont.click();
await page.getByText("Hello from the stub model.").waitFor({ timeout: 15000 });
if (await cont.count()) fail("Continue stayed after continuing");

// 8. the model list comes from the provider when the model box is first used
await panel.locator("input.model").focus();
await panel.locator('datalist option[value="stub-model"]').waitFor({ state: "attached", timeout: 15000 });

// 9. typing @ suggests entities and inserts the exact entity id
await box.fill("");
await box.pressSequentially("turn on @e2e_sw");
const option = panel.locator("ul.mentions li", { hasText: "input_boolean.e2e_switch" });
await option.waitFor({ timeout: 10000 });
await page.screenshot({ path: `${shots}/llm-agent-6-mention.png` });
await box.press("Enter");
const typed = await box.inputValue();
if (typed !== "turn on input_boolean.e2e_switch ") fail(`mention not inserted: ${JSON.stringify(typed)}`);
if (await panel.locator("ul.mentions").count()) fail("suggestions stayed open after picking");

// 10. panel settings: dark theme sticks after a reload; Ctrl+Enter mode keeps Enter as a new line
await panel.getByRole("button", { name: "Panel settings" }).click();
await panel.getByLabel("Theme").selectOption("dark");
await panel.getByLabel("Send with").selectOption("ctrl");
await page.waitForTimeout(400); // let the popover and colour transitions finish
await page.screenshot({ path: `${shots}/llm-agent-7-settings.png` });
const host = page.locator("llm-agent-panel");
if ((await host.getAttribute("data-theme")) !== "dark") fail("dark theme not applied");
await page.reload();
await box.waitFor({ timeout: 30000 });
if ((await host.getAttribute("data-theme")) !== "dark") fail("theme not kept after reload");
await box.fill("line one");
await box.press("Enter");
if ((await box.inputValue()) !== "line one\n") fail("Enter sent the message in Ctrl+Enter mode");
await panel.getByRole("button", { name: "Panel settings" }).click();
await panel.getByLabel("Send with").selectOption("enter");
// the welcome screen in both explicit themes (screenshots only)
await box.fill("");
await panel.getByRole("button", { name: "New chat" }).first().click();
for (const theme of ["dark", "light"]) {
  if (!(await panel.locator(".prefs").count()))
    await panel.getByRole("button", { name: "Panel settings" }).click();
  await panel.getByLabel("Theme").selectOption(theme);
  await panel.locator(".messages").click({ position: { x: 20, y: 300 } }); // outside the popover
  if (await panel.locator(".prefs").count()) fail("panel settings stayed open after an outside click");
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${shots}/llm-agent-8-welcome-${theme}.png` });
}
await panel.getByRole("button", { name: "Panel settings" }).click();
await panel.getByLabel("Theme").selectOption("auto");
await box.press("Escape");

// 11. a photo goes with the message, shows in the chat, and is noted (not kept) after reopening
await panel.getByRole("button", { name: "New chat" }).first().click();
await panel.getByLabel("Add a photo").setInputFiles(`${configDir}/camera.png`);
await panel.locator(".attached img").waitFor({ timeout: 10000 });
await box.fill("what is in this photo");
await box.press("Enter");
await page.getByText("I can see 1 photo.").waitFor({ timeout: 15000 });
if (!(await panel.locator(".msg.user .photos img").count())) fail("sent photo not shown");
if (await panel.locator(".attached img").count()) fail("photo stayed in the composer after sending");
await page.screenshot({ path: `${shots}/llm-agent-9-photo.png` });
await panel.getByRole("button", { name: "New chat" }).first().click();
await panel.locator(".conv", { hasText: "what is in this photo" }).click();
await panel.getByText("1 photo (not kept)").waitFor({ timeout: 15000 });
await panel.getByRole("button", { name: "Retry" }).click();
await panel.getByText("Attach them again").waitFor({ timeout: 10000 });
if (!(await panel.getByText("I can see 1 photo.").count())) fail("retry without the photo replaced the answer");
await panel.locator(".editing button", { hasText: "Cancel" }).click();

// 12. draft photos don't follow you into another chat
await panel.getByLabel("Add a photo").setInputFiles(`${configDir}/camera.png`);
await panel.locator(".attached img").waitFor({ timeout: 10000 });
await panel.getByRole("button", { name: "New chat" }).first().click();
if (await panel.locator(".attached img").count()) fail("draft photo followed into a new chat");

// 13. three large, noisy photos still fit in one message (HA closes the socket over 4 MiB)
const noisy = noisyPng(2000, 1500);
const files = [1, 2, 3].map((i) => ({ name: `noise${i}.png`, mimeType: "image/png", buffer: noisy }));
await panel.getByLabel("Add a photo").setInputFiles(files);
for (let i = 0; (await panel.locator(".attached img").count()) < 3; i++) {
  if (i > 60) fail("noisy photos were not attached");
  await page.waitForTimeout(500);
}
await box.fill("three noisy photos");
await box.press("Enter");
await page.getByText("I can see 3 photo.").waitFor({ timeout: 30000 });

// 14. a proposed dashboard can be previewed before approving, without outside addresses
await panel.getByRole("button", { name: "New chat" }).first().click();
const outside = [];
page.on("request", (r) => r.url().includes(".invalid") && outside.push(r.url()));
await box.fill("make a new dashboard");
await box.press("Enter");
await panel.getByRole("button", { name: "Preview the dashboard" }).click({ timeout: 30000 });
await panel.locator("llm-dashboard-preview").getByText("E2E preview").waitFor({ timeout: 15000 });
await panel.locator("llm-dashboard-preview").getByText("E2E stack").waitFor({ timeout: 15000 });
if (!(await panel.getByText("7 cards not shown").count())) fail("unsafe cards were not held back");
await page.waitForTimeout(1000);
if (outside.length) fail(`preview fetched outside addresses: ${outside.join(", ")}`);
await page.screenshot({ path: `${shots}/llm-agent-6-dashboard-preview.png` });
await panel.getByRole("button", { name: "Deny" }).click();
await page.getByText("OK, I did not do that.").waitFor({ timeout: 15000 });

// 15. home notes are edited in the panel and kept
await panel.getByRole("button", { name: "Home notes" }).click();
await panel.locator(".prefs.notes textarea").fill("The office is upstairs.");
await panel.locator(".prefs.notes").getByRole("button", { name: "Save" }).click();
await panel.getByText("Saved.").waitFor({ timeout: 10000 });
await page.screenshot({ path: `${shots}/llm-agent-7-home-notes.png` });
await page.reload();
await panel.getByRole("button", { name: "Home notes" }).click({ timeout: 30000 });
const kept = await panel.locator(".prefs.notes textarea").inputValue();
if (kept !== "The office is upstairs.") fail(`home notes not kept: ${kept}`);

if (errors.length) fail(`page errors: ${errors.join("; ")}`);
await browser.close();
console.log("E2E PASS");

/** An uncompressible RGB PNG: the worst case for photo size. */
function noisyPng(w, h) {
  const row = w * 3 + 1;
  const raw = randomBytes(row * h);
  for (let y = 0; y < h; y++) raw[y * row] = 0;
  const chunk = (type, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const body = Buffer.concat([Buffer.from(type), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(body) >>> 0);
    return Buffer.concat([len, body, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr.set([8, 2, 0, 0, 0], 8);
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw)),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}
