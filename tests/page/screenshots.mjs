// Screenshots of the FAIR data guide at desktop and mobile width, for pull-request previews.
// Usage: node tests/page/screenshots.mjs <output-directory> [hash ...]

import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const pageUrl = pathToFileURL(resolve(root, "index.html")).href;
const [outDir = resolve(root, ".cache", "screenshots"), ...hashes] = process.argv.slice(2);
const views = hashes.length ? hashes : ["", "#/cs/V/path/repozitar", "#/en/SR/path/publikace", "#/cs/V/resources"];
const widths = { desktop: { width: 1366, height: 1000 }, mobile: { width: 390, height: 1200 } };

mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
for (const [device, viewport] of Object.entries(widths)) {
  for (const hash of views) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    await page.goto(pageUrl + hash);
    await page.waitForFunction(() => {
      const heading = document.querySelector("#main h1");
      return heading && heading.textContent.trim();
    });
    const name = (hash.replace(/^#\//, "").replace(/\//g, "-") || "start") + `-${device}.png`;
    await page.screenshot({ path: resolve(outDir, name), fullPage: false });
    console.log(name);
    await context.close();
  }
}
await browser.close();
