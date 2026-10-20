// Browser test of the LLM Agent panel against a real HA and the stub model.
// Usage: node panel.mjs <ha-url> <tokens-json-file> <config-dir> [screenshot-dir]
import { readFileSync, existsSync } from "node:fs";
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
await page.getByText("What should I do?").waitFor();

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
if (!(await panel.locator("pre.diff").innerText()).includes("+hello from the e2e test")) fail("diff missing");
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

// 4. history survives a reload
await page.reload();
await panel.locator(".conv").first().click();
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

if (errors.length) fail(`page errors: ${errors.join("; ")}`);
await browser.close();
console.log("E2E PASS");
