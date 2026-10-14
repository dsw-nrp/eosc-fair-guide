// Citation helper contracts: identity and style fidelity, partial failure, privacy, reset and plain-text outputs.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const { chromium } = await import("playwright");
const browser = await chromium.launch();
const context = await browser.newContext({ acceptDownloads: true });
await context.addInitScript(() => Object.defineProperty(navigator, "clipboard", { value: { writeText: async () => { throw Error("denied"); } } }));
const page = await context.newPage();
const base = pathToFileURL(resolve(root, "_site/index.html")).href;
const shots = resolve(root, ".cache/screenshots/citation");
mkdirSync(shots, { recursive: true });
let mode = "ok", release, active = 0, peak = 0;
const calls = [];
const origins = new Set(JSON.parse(readFileSync(resolve(root, "_site/assets/data/ui.js"), "utf8").match(/^window\.FairGuideData\.ui = (.*);$/m)[1]).config.connectors.map((entry) => entry.origin));
await page.route(/^https?:/, async (route) => {
  const url = new URL(route.request().url());
  assert(origins.has(url.origin), "requests stay on reviewed origins");
  assert.equal(route.request().headers().cookie, undefined);
  assert.equal(route.request().headers().authorization, undefined);
  assert.equal(route.request().headers().referer, undefined);
  calls.push(url.href); active++; peak = Math.max(peak, active);
  try {
    const doi = url.searchParams.get("doi") || decodeURIComponent(url.pathname.match(/(?:ra|dois|works)\/(.+?)(?:\/transform\/|$)/)?.[1] || url.pathname.split("/").slice(3).join("/"));
    const agency = doi.includes("crossref") ? "Crossref" : "DataCite";
    let body, status = 200, type = "application/json";
    if (url.origin === "https://doi.org") body = [{ RA: mode === "unsupported" ? "Other" : agency, ...(mode === "missing" ? { status: "DOI does not exist" } : {}) }];
    else if (url.origin === "https://api.datacite.org" || (url.origin === "https://api.crossref.org" && !url.pathname.includes("/transform/"))) {
      if (mode === "delayed") await new Promise((resolve) => { release = resolve; });
      const recordDoi = mode === "mismatch" ? "10.1234/another" : doi;
      body = agency === "DataCite" ? { data: { attributes: { doi: recordDoi, titles: [{ title: "Dataset <img src='https://evil.example/title'>" }] } } }
        : { message: { DOI: recordDoi, title: ["Crossref article"] } };
    } else if (url.pathname === "/styles") {
      if (mode === "stylesBlocked") { await route.abort(); return; }
      // The real published list is about 96 KB, larger than a single citation representation.
      body = mode === "styleMissing" ? ["apa"] : ["apa", "iso690-author-date-cs", ...Array.from({ length: 5000 }, (_, n) => "published-style-" + n)];
    } else if (url.pathname === "/format") {
      if (mode === "formatterBlocked") { await route.abort(); return; }
      type = mode === "html" ? "text/html" : "text/plain";
      body = url.searchParams.get("style") === "apa" ? `Author. (2026). APA <img src='https://evil.example/citation'>. https://doi.org/${doi}`
        : `AUTOR. Česká citace. 2026. Dostupné z: https://doi.org/${doi}`;
    } else if (url.pathname.includes("x-bibtex")) {
      type = "application/x-bibtex";
      body = `@article{entry, title={A record}, doi={${mode === "badBib" ? "10.1234/wrong" : doi}}}`;
    } else if (url.pathname.includes("x-research-info-systems")) {
      type = "application/x-research-info-systems";
      if (mode === "rateLimit") status = 429;
      body = `TY  - DATA\nTI  - A record\nDO  - ${mode === "badRis" ? "10.1234/wrong" : doi}\nER  -\n`;
    } else throw Error("Unexpected citation request: " + url.href);
    await route.fulfill({ status, contentType: type, headers: { "access-control-allow-origin": "*" }, body: typeof body === "string" ? body : JSON.stringify(body) });
  } finally { active--; }
});
const visit = async (hash = "#/en/V/page/citation/10.1234%2Fdatacite") => {
  await page.goto(base + hash);
  await page.waitForSelector("#citation-doi");
};
const generate = async (doi = "10.1234/datacite") => {
  await page.locator("#citation-doi").fill(doi);
  await page.locator('.citation-helper button[type="submit"]').click();
  await page.waitForFunction(() => !document.querySelector('.citation-helper button[type="submit"]').disabled);
};
try {
  await visit();
  assert.equal(await page.locator("#citation-doi").inputValue(), "10.1234/datacite");
  assert.equal(calls.length, 0, "route seeding does not contact services");
  await page.locator("#citation-doi").fill("10.1234/edited");
  await page.evaluate(() => { location.hash = "#/en/V/path/start"; });
  await page.waitForSelector("#search-input");
  await page.evaluate(() => { location.hash = "#/en/V/page/citation/10.1234%2Fdatacite"; });
  await page.waitForSelector("#citation-doi");
  assert.equal(await page.locator("#citation-doi").inputValue(), "10.1234/datacite", "a repeated handoff replaces an edited draft");
  await generate("not a DOI");
  assert.equal(calls.length, 0, "invalid input stays local");
  for (const doi of ["10.1234/datacite", "10.1234/crossref"]) {
    await generate("https://doi.org/" + doi);
    assert.equal(await page.locator(".citation-format pre").count(), 4);
    assert((await page.locator("#citation-bibtex").textContent()).includes(doi));
    assert.equal(await page.locator(".citation-helper img").count(), 0, "untrusted markup is text");
    assert.equal(await page.locator(".citation-format a").count(), 4, "every output links to its service representation");
  }
  await page.locator(".citation-format").first().locator("button").first().click();
  assert.equal(await page.evaluate(() => getSelection().toString()), await page.locator("#citation-apa").textContent(), "clipboard denial selects the complete text");
  const downloading = page.waitForEvent("download");
  await page.locator(".citation-format").nth(2).locator("button").nth(1).click();
  const download = await downloading;
  assert(download.suggestedFilename().endsWith(".bib"));
  assert.equal(readFileSync(await download.path(), "utf8"), await page.locator("#citation-bibtex").textContent());
  for (const failure of ["styleMissing", "stylesBlocked", "formatterBlocked", "html", "badBib", "badRis", "rateLimit"]) {
    mode = failure; await generate();
    const expected = ["stylesBlocked", "formatterBlocked", "html"].includes(failure) ? 2 : 3;
    assert.equal(await page.locator(".citation-format pre").count(), expected, "independent failure: " + failure);
    if (failure === "styleMissing") assert(!calls.slice(-5).some((url) => url.includes("style=iso690")), "an absent style is never requested");
  }
  for (const failure of ["missing", "unsupported", "mismatch"]) {
    mode = failure; const before = calls.length; await generate();
    assert.equal(await page.locator(".citation-format").count(), 0);
    assert(!calls.slice(before).some((url) => /format|transform|crosscite/.test(url)), "no citation generated from unsupported or different records");
  }
  mode = "delayed";
  await page.locator("#citation-doi").fill("10.1234/datacite");
  await page.locator('.citation-helper button[type="submit"]').click();
  while (!release) await new Promise((resolve) => setTimeout(resolve, 20));
  await page.locator(".citation-helper .field-clear").click();
  release();
  await page.waitForTimeout(250);
  assert.equal(await page.locator("#citation-doi").inputValue(), "");
  assert.equal(await page.locator(".citation-format").count(), 0, "late response cannot restore cleared results");
  mode = "ok";
  await generate();
  const kept = await page.locator("#citation-apa").textContent(), beforeSwitch = calls.length;
  await page.evaluate(() => { location.hash = "#/cs/V/page/citation"; });
  await page.waitForFunction(() => document.documentElement.lang === "cs");
  assert.equal(await page.locator("#citation-apa").textContent(), kept, "language switching retains outputs");
  assert.equal(calls.length, beforeSwitch, "language switching makes no external request");
  for (const lang of ["cs", "en"]) {
    await visit(`#/${lang}/V/page/citation`); await generate();
    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await page.waitForSelector(".citation-format");
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "citation reflows at " + width);
      const a11y = await audit(page);
      assert.deepEqual(a11y.violations, []);
      await page.screenshot({ path: resolve(shots, `${lang}-citation-${width}.png`), fullPage: true });
    }
  }
  assert(peak <= 4, "citation requests remain bounded");
  assert(!calls.some((url) => url.includes("evil.example")), "external markup never triggers a request");
  console.log("check_citation: DataCite/Crossref, identity/style fidelity, independent failures, plain text, copy/download, privacy/reset and bilingual accessibility pass");
} finally { await browser.close(); }
