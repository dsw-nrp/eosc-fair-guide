// Deterministically hold deferred parts: navigation/search must not inspect the old view or an incomplete index.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { extname, resolve, sep } from "node:path";
import { chromium } from "./browser.mjs";
import { gotoView, searchReady } from "./navigation.mjs";

const site = resolve(import.meta.dirname, "../../_site"), origin = "http://guide.test";
const browser = await chromium.launch();
const context = await browser.newContext();
const mime = { ".js": "text/javascript", ".html": "text/html", ".css": "text/css", ".svg": "image/svg+xml", ".json": "application/json" };
await context.route(origin + "/**", async (route) => {
  const pathname = new URL(route.request().url()).pathname;
  const path = resolve(site, "." + (pathname === "/" ? "/index.html" : pathname));
  assert(path.startsWith(site + sep));
  try { await route.fulfill({ body: readFileSync(path), contentType: mime[extname(path)] || "application/octet-stream" }); }
  catch { await route.fulfill({ status: 404, body: "Missing fixture" }); }
});

async function hold(page, pattern) {
  const entered = Promise.withResolvers(), release = Promise.withResolvers();
  await page.route(pattern, async (route) => {
    entered.resolve();
    await release.promise;
    await route.fallback();
  });
  return { entered: entered.promise, release: () => release.resolve() };
}

try {
  const page = await context.newPage();
  await gotoView(page, origin + "/#/cs/V/path/start");
  const about = await hold(page, "**/kb-pages-cs.js");
  let settled = false;
  const navigation = gotoView(page, origin + "/#/cs/V/page/about").then(() => { settled = true; });
  await about.entered;
  assert((await page.locator("#main h1").textContent()).includes("FAIR"), "old heading remains while parts load");
  assert.equal(settled, false, "an existing heading cannot settle navigation");
  about.release();
  await navigation;
  assert(await page.locator("#why").count(), "About's own content arrived");
  await gotoView(page, origin + "/#/cs/V/page/about"); // same address must complete without a hashchange

  const english = await hold(page, "**/kb-pages-en.js");
  settled = false;
  const language = gotoView(page, origin + "/#/en/V/page/about").then(() => { settled = true; });
  await english.entered;
  assert.equal(settled, false);
  english.release();
  await language;
  assert.equal(await page.locator("html").getAttribute("lang"), "en");
  await gotoView(page, origin + "/#/en/V/page/accessibility");
  assert((await page.locator("#main").textContent()).includes("Swagger UI"));

  const fresh = await context.newPage();
  await gotoView(fresh, origin + "/#/cs/V/path/start");
  const standards = await hold(fresh, "**/kb-standards-cs.js");
  await fresh.locator("#search-input").fill("licence");
  await standards.entered;
  assert.equal(await fresh.locator("#search-input").inputValue(), "licence");
  settled = false;
  const search = searchReady(fresh, "licence").then(() => { settled = true; });
  await fresh.evaluate(() => document.querySelector("#search-input").value);
  assert.equal(settled, false, "a rendered query does not establish a fully loaded index");
  standards.release();
  await search;
  assert((await fresh.locator("#search-results").textContent()).includes("R1.1"));
  console.log("check_navigation: delayed About/language/search parts, same-route navigation and accessibility content pass");
} finally { await browser.close(); }
