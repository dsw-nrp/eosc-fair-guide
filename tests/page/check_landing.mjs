// Static record landing pages are usable without JavaScript, at phone width and in print.
import assert from "node:assert/strict";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "./browser.mjs";
import { audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
const site = resolve(root, process.env.FAIR_GUIDE_SITE || "_site");
const shots = resolve(root, ".cache/screenshots/landing");
mkdirSync(shots, { recursive: true });
const browser = await chromium.launch();
const records = [
  { address: "resources/rdmkit", route: "/catalogue/resources/rdmkit", title: "RDMkit" },
  { address: "stations/plan", route: "/catalogue/stations/plan", title: "Plán" },
  { address: "repositories/zenodo", route: "/catalogue/repositories/zenodo", title: "Zenodo" },
  { address: "infrastructures/hl-lhc", route: "/catalogue/infrastructures/hl-lhc", title: "HL-LHC" },
];
const results = [];

for (const width of [1280, 390]) {
  for (const record of records) {
    const filename = resolve(site, "id", ...record.address.split("/")) + ".html";
    const url = pathToFileURL(filename).href;
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width, height: 1000 } });
    const page = await context.newPage();
    const requests = [];
    page.on("request", (request) => {
      if (/^https?:/i.test(request.url())) requests.push(request.url());
    });
    await page.goto(url);
    assert.equal(await page.locator(".landing-record[lang]").count(), 2, `${record.address}: both language blocks`);
    assert((await page.locator("#cs h1").textContent()).includes(record.title), `${record.address}: title without JavaScript`);
    const describedByCount = await page.locator('head link[rel="describedby"]').count();
    if (describedByCount !== 1) console.error(`heading mismatch: ${await page.locator("head").innerHTML()}`);
    assert.equal(describedByCount, 1, `${record.address}: API-describedby link`);
    assert.equal(await page.locator('head link[rel="describedby"]').getAttribute("type"), "application/ld+json", `${record.address}: describedby is JSON-LD`);
    assert.equal(await page.locator("script").count(), 0, `${record.address}: no script element`);
    assert.equal(await page.locator("body [onload]").count(), 0, `${record.address}: no load handler`);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${record.address}: no horizontal overflow at ${width}px`);
    const wide = await page.locator("a").evaluateAll((links) => links.filter((node) => node.getBoundingClientRect().right > innerWidth + 1).map((node) => node.href));
    assert.equal(wide.length, 0, `${record.address}: link beyond the phone viewport: ${wide.join(", ")}`);
    const auditPage = await browser.newPage();
    await auditPage.goto(url);
    const access = await audit(auditPage);
    assert.deepEqual(access.violations.map((entry) => entry.id), [], `${record.address}: accessibility at ${width}px`);
    await auditPage.close();
    assert.deepEqual(requests, [], `${record.address}: no HTTP request on load`);
    await page.screenshot({ path: resolve(shots, `${record.address.replace("/", "-")}-${width}.png`), fullPage: false });
    await page.emulateMedia({ media: "print" });
    assert(await page.locator("#en h1").isVisible(), `${record.address}: English content prints`);
    const pdf = await page.pdf({ printBackground: true, format: "A4" });
    assert(pdf.length > 1000, `${record.address}: printable PDF is not empty`);
    if (record.address === "stations/plan") {
      await page.screenshot({ path: resolve(shots, `stations-plan-${width}-print.png`), fullPage: false });
    }
    results.push({ address: record.address, width, select: [".landing-record[lang='cs']", ".landing-record[lang='en']"], pdfBytes: pdf.length });
    await context.close();
  }
}

for (const width of [1280, 390]) {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width, height: 1000 } });
  const actionPage = await context.newPage();
  await actionPage.goto(pathToFileURL(resolve(site, "id/pages/live-check.html")).href + "#quick-deep-action");
  assert(await actionPage.locator("#quick-deep-action").isVisible(), `nested quick-deep action is visible at ${width}px`);
  await actionPage.screenshot({ path: resolve(shots, `pages-live-check-action-${width}.png`), fullPage: false });
  await actionPage.emulateMedia({ media: "print" });
  assert(await actionPage.locator("#quick-deep-action").isVisible(), `nested action remains visible in print at ${width}px`);
  await context.close();
}

for (const record of records) {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const staticPage = await context.newPage();
  await staticPage.goto(pathToFileURL(resolve(site, "id", ...record.address.split("/")) + ".html").href);
  await staticPage.locator('nav[aria-label="Guide"] a').click();
  await staticPage.waitForURL((url) => url.hash === "#/id/" + record.address);
  const target = staticPage.url();
  await context.close();
  const page = await browser.newPage();
  const problem = [];
  page.on("pageerror", (error) => problem.push(error.message));
  // The native file:// link resolves without script; reopen the exact resulting URL with JavaScript to verify the view.
  await page.goto(target);
  try {
    await page.waitForFunction((expected) => location.hash.endsWith(expected), record.route, { timeout: 10000 });
  } catch (error) {
    console.error(`route ${record.address}: ${page.url()} — ${await page.locator("body").innerText()} — errors: ${problem.join("; ")}`);
    throw error;
  }
  await page.waitForSelector("#main h1");
  assert((await page.locator("#main").innerText()).includes(record.title), `${record.address}: the record content is visible`);
  await page.screenshot({ path: resolve(shots, `${record.address.replace("/", "-")}-catalogue.png`), fullPage: false });
  assert.deepEqual(problem, [], `${record.address}: Guide route has no JavaScript error`);
  await page.close();
}
console.log(`check_landing: both languages, no JavaScript, phone/desktop layouts and print pass for ${records.length} record types (${results.length} checks)`);
await browser.close();
