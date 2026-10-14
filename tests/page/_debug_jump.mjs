// TEMPORARY diagnostic for the failing page check at check_page.mjs:627.
import { chromium } from "playwright";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const site = resolve("_site");
const pageUrl = pathToFileURL(resolve(site, "index.html")).href;

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();
page.on("pageerror", (error) => console.log("PAGEERROR:", error.message));

await page.goto(pageUrl + "#/cs/V/path/findability");
await page.waitForSelector("#main h1");
await page.locator('details[data-key="L1"] > summary').click();
const named = page.locator('details[data-key="L1"] a.text-ref', { hasText: "DataCite" }).first();

for (const rate of [1, 6, 12, 20]) {
  const client = await context.newCDPSession(page);
  await client.send("Emulation.setCPUThrottlingRate", { rate });
  await page.goto(pageUrl + "#/cs/V/path/findability");
  await page.waitForSelector("#main h1");
  const link = page.locator('details[data-key="L1"] a.text-ref', { hasText: "DataCite" }).first();
  const started = Date.now();
  await link.click();
  const clickMs = Date.now() - started;
  let outcome;
  try {
    await page.waitForSelector("#item-datacite.jumped", { timeout: 20000 });
    outcome = "caught";
  } catch (error) {
    outcome = "MISSED";
  }
  console.log(`throttle x${rate}: click ${clickMs}ms -> ${outcome}`);
  await client.detach();
}
await browser.close();
