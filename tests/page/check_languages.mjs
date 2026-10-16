// Selected-language downloads, local-file switching, exact data reconstruction and a failed local file retry.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const root = resolve(import.meta.dirname, "../..");
const site = resolve(root, process.argv[2] || "_site");
const file = pathToFileURL(resolve(site, "index.html")).href;
const crate = JSON.parse(readFileSync(resolve(site, "ro-crate-metadata.json"), "utf8"));
const { chromium } = await import("./browser.mjs");
const browser = await chromium.launch();

async function rendered(page, lang, id) {
  await page.waitForFunction(({ lang, id }) => document.documentElement.lang === lang &&
    window.FairGuide?.state.lang === lang && Boolean(document.querySelector(id)), { lang, id });
}
function watched(page) {
  const requests = [], errors = [];
  page.on("request", (request) => requests.push(request.url()));
  page.on("pageerror", (error) => errors.push(error.message));
  return { requests, errors };
}
function languageFiles(requests, lang) {
  return requests.filter((url) => new RegExp(`/assets/data/kb(?:-[a-z]+)?-${lang}\\.js$`).test(url));
}

try {
  for (const initial of ["cs", "en"]) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const observed = watched(page);
    const other = initial === "cs" ? "en" : "cs";
    await page.goto(file + `#/${initial}/K/check/software/answers`);
    await rendered(page, initial, "#item-software-04");
    assert.equal(languageFiles(observed.requests, other).length, 0, "the other display language is not downloaded initially");
    assert.equal(languageFiles(observed.requests, initial).length, 5, "one core and four required part translations, including model relations");
    assert.equal(await page.evaluate((lang) => window.FairGuide.ui.app.title[lang], other), "", "unloaded UI values stay absent");
    assert(await page.evaluate((lang) => window.FairGuide.get("#station-plan").name.some((value) => value["@language"] === lang && !value["@value"]), other));
    if (initial === "cs") assert(await page.evaluate(() => window.FairGuide.bothLanguages(window.FairGuide.get("#station-findability").name).includes("findability")), "folded aliases preserve a genuinely unloaded English title");
    await page.locator("#answer-software-04-no").check();
    const saved = await page.evaluate(() => JSON.stringify(window.FairGuide.state.answers.software));
    const originalIds = await page.evaluate(() => [...window.FairGuide.byId.keys()].sort());
    await page.getByRole("link", { name: other === "en" ? "English" : "Česky", exact: true }).click();
    await rendered(page, other, "#item-software-04");
    assert(await page.locator("#answer-software-04-no").isChecked(), "language switching keeps the authored answer");
    assert.equal(await page.evaluate(() => JSON.stringify(window.FairGuide.state.answers.software)), saved);
    assert.deepEqual(await page.evaluate(() => [...window.FairGuide.byId.keys()].sort()), originalIds, "switching adds no duplicate entities");
    assert.equal(languageFiles(observed.requests, other).length, 5);
    await page.getByRole("link", { name: initial === "en" ? "English" : "Česky", exact: true }).click();
    await rendered(page, initial, "#item-software-04");
    assert.equal(languageFiles(observed.requests, initial).length, 5, "switching back uses the existing values");
    assert.deepEqual(observed.errors, []);
    assert(observed.requests.every((url) => /^(?:file|data):/.test(url)), "local-file navigation sends no external request");

    // A catalogue JSON export deliberately loads the complete language maps; CSV remains in the current language.
    await page.evaluate((lang) => { window.location.hash = `#/${lang}/K/catalogue/k!resources`; }, initial);
    await rendered(page, initial, "#catalogue-search");
    const exported = await page.evaluate(async () => {
      const FG = window.FairGuide;
      let result;
      const download = FG.download;
      FG.download = (_name, text) => { result = JSON.parse(text); };
      try { await FG.exports.find((entry) => entry.id === "json").run(); }
      finally { FG.download = download; }
      return result;
    });
    const labelled = exported.itemListElement.filter((entry) => entry.name && typeof entry.name === "object");
    assert(labelled.length > 0);
    assert(labelled.every((entry) => entry.name.cs && entry.name.en), "JSON summaries retain both API-style label languages");
    assert.equal(await page.evaluate(() => window.FairGuide.state.lang), initial, "exporting does not switch the view");

    // Every deferred part and both languages together preserve the exact full source graph.
    const reconstructed = await page.evaluate(async () => {
      const FG = window.FairGuide;
      await Promise.all(Object.keys(FG.config.parts).map((part) => FG.loadPart(part)));
      await FG.completeLanguages();
      return Object.fromEntries(FG.graph.map((entity) => [entity["@id"], entity]));
    });
    assert.deepEqual(reconstructed, Object.fromEntries(crate["@graph"].map((entity) => [entity["@id"], entity])));
    await context.close();
  }

  const savedContext = await browser.newContext();
  const savedPage = await savedContext.newPage();
  const savedObserved = watched(savedPage);
  await savedContext.addInitScript(() => localStorage.setItem("eosc-fair-guide", JSON.stringify({ lang: "en", lens: "V" })));
  await savedPage.goto(file);
  await rendered(savedPage, "en", "#search-input");
  assert.equal(languageFiles(savedObserved.requests, "cs").length, 0, "a saved language is selected before the first download");
  assert.equal(languageFiles(savedObserved.requests, "en").length, 1);
  await savedContext.close();

  // Public static hosts work like file://. A missing translation leaves the current view readable and retryable.
  const context = await browser.newContext();
  const page = await context.newPage();
  const observed = watched(page);
  const origin = "https://guide.example";
  let blockEnglish = true;
  await context.route(origin + "/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (blockEnglish && pathname === "/assets/data/kb-en.js") return route.abort("failed");
    const path = resolve(site, "." + pathname);
    assert(path.startsWith(site + "/") || path.startsWith(site + "\\"));
    const type = path.endsWith(".js") ? "text/javascript" : path.endsWith(".css") ? "text/css" : path.endsWith(".svg") ? "image/svg+xml" : "text/html";
    await route.fulfill({ body: readFileSync(path), contentType: type });
  });
  await page.goto(origin + "/index.html#/cs/V/path");
  await rendered(page, "cs", "#search-input");
  assert.equal(languageFiles(observed.requests, "en").length, 0);
  const search = async (text) => {
    await page.fill("#search-input", text);
    await page.waitForFunction((query) => document.querySelector("#search-results")?.dataset.query === query, text);
    return page.locator("#search-results").textContent();
  };
  assert(!(await search("authentication")).includes("Nic nenalezeno"), "English terms match while only Czech display text is loaded");
  assert.equal(languageFiles(observed.requests, "en").length, 0, "cross-language search needs no other display translation");
  await page.getByRole("link", { name: "English", exact: true }).click();
  await page.waitForSelector(".data-load-error");
  assert.equal(await page.evaluate(() => window.FairGuide.state.lang), "cs");
  assert(await page.locator("#search-input").isVisible(), "failed switch keeps the previous working view");
  blockEnglish = false;
  await page.locator(".data-load-error button").click();
  await rendered(page, "en", "#search-input");
  assert.equal(await page.locator(".data-load-error").count(), 0);
  assert.equal(observed.requests.filter((url) => url.endsWith("/assets/data/kb-en.js")).length, 2, "retry actually reloads the failed local file");
  assert.deepEqual(observed.errors, []);
  assert(observed.requests.every((url) => url.startsWith(origin + "/") || url.startsWith("data:")), "static-host browsing requests only its own assets");
  await context.close();
  console.log("language checks: selected downloads, both directions, exact graph, bilingual exports/search and failed-file retry passed");
} finally {
  await browser.close();
}
