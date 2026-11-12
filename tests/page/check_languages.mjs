// Selected-language downloads, local-file switching, exact data reconstruction and a failed local file retry.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { iri, siteNamespace } from "./addresses.mjs";

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
    assert(await page.evaluate((lang) => window.FairGuide.get("stations/plan").name.some((value) => value["@language"] === lang && !value["@value"]), other));
    if (initial === "cs") assert(await page.evaluate(() => window.FairGuide.bothLanguages(window.FairGuide.get("stations/findability").name).includes("findability")), "folded aliases preserve a genuinely unloaded English title");
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
    // The page names records by their addresses, relative to the namespace (build_crate.relative_ids).
    const base = iri("", siteNamespace(site));
    const relative = (value) => Array.isArray(value) ? value.map(relative) : value && typeof value === "object"
      ? Object.fromEntries(Object.entries(value).map(([name, item]) => [name, name === "@id" && typeof item === "string" && item.startsWith(base) ? item.slice(base.length) : relative(item)]))
      : value;
    assert.deepEqual(reconstructed, Object.fromEntries(crate["@graph"].map((entity) => relative(entity)).map((entity) => [entity["@id"], entity])));
    await context.close();
  }

  const savedContext = await browser.newContext();
  const savedPage = await savedContext.newPage();
  const savedObserved = watched(savedPage);
  await savedContext.addInitScript(() => localStorage.setItem("eosc-fair-guide", JSON.stringify({ lang: "en", lens: "V" })));
  await savedPage.goto(file);
  await rendered(savedPage, "en", "#search-input");
  assert.equal(languageFiles(savedObserved.requests, "cs").length, 0, "a saved language is selected before the first download");
  assert.equal(languageFiles(savedObserved.requests, "en").length, 1, savedObserved.requests.join(" | "));
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
  // Advice search waits for its language patch, and a failed advice translation remains retryable.
  const delayed = await browser.newContext();
  const delayedPage = await delayed.newPage();
  let releaseAdvice, noticeAdvice;
  const gate = new Promise((resolve) => { releaseAdvice = resolve; });
  const requested = new Promise((resolve) => { noticeAdvice = resolve; });
  let failAdviceEnglish = true;
  await delayed.route(origin + '/**', async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === '/assets/data/kb-advice-en.js' && failAdviceEnglish) return route.abort('failed');
    let body = readFileSync(resolve(site, '.' + pathname));
    if (pathname === '/assets/data/kb-advice-cs.js') {
      let injected = false;
      body = body.toString().replace(/"@value":\s*"/, (match) => { if (injected) return match; injected = true; return match + 'deferredadviceprobe '; });
      assert(injected, 'the probe belongs to a deferred advice text');
      noticeAdvice(); await gate;
    }
    await route.fulfill({ body, contentType: pathname.endsWith('.js') ? 'text/javascript' : pathname.endsWith('.css') ? 'text/css' : 'text/html' });
  });
  await delayedPage.goto(origin + '/index.html#/cs/V/path/start');
  await rendered(delayedPage, 'cs', '#search-input');
  assert.equal(await delayedPage.evaluate(() => window.FairGuide.partsLoaded.has('advice')), false);
  await delayedPage.evaluate(() => {
    const FG = window.FairGuide, invalidate = FG.invalidateData;
    window.partInvalidations = 0;
    FG.invalidateData = () => { window.partInvalidations += 1; invalidate(); };
  });
  await delayedPage.fill('#search-input', 'deferredadviceprobe');
  await requested;
  await delayedPage.locator('form.search').evaluate((form) => form.requestSubmit());
  assert.notEqual(await delayedPage.locator('#search-results').getAttribute('data-query'), 'deferredadviceprobe', 'unloaded advice does not produce a complete empty result');
  releaseAdvice();
  await delayedPage.waitForFunction(() => document.querySelector('#search-results')?.dataset.query === 'deferredadviceprobe');
  assert(await delayedPage.locator('#search-results a[href*="/path/"]').count(), 'the deferred advice is in the completed index');
  assert.equal(await delayedPage.evaluate(() => window.partInvalidations), 8, 'overlapping focus and submission merge and invalidate each part/language operation once');
  const repeated = await delayedPage.evaluate(async () => {
    const FG = window.FairGuide, find = FG.search.find;
    let calls = 0;
    FG.search.find = (...args) => { calls += 1; return find(...args); };
    try {
      const input = document.querySelector('#search-input');
      input.dispatchEvent(new Event('focus', { bubbles: false }));
      document.querySelector('form.search').requestSubmit();
      await new Promise((done) => setTimeout(done, 0));
      return calls;
    } finally { FG.search.find = find; }
  });
  assert.equal(repeated, 0, 'identical query, confirmation and data revision do not evaluate results again');
  await delayedPage.getByRole('link', { name: 'English', exact: true }).click();
  await delayedPage.locator('.data-load-error').waitFor();
  assert.equal(await delayedPage.evaluate(() => window.FairGuide.state.lang), 'cs');
  failAdviceEnglish = false;
  await delayedPage.locator('.data-load-error button').click();
  await rendered(delayedPage, 'en', '#search-input');
  assert(await delayedPage.evaluate(() => window.FairGuide.partHasLanguage('advice', 'en')));
  await delayed.close();

  // A failed text-search part offers a working retry, while identifier routing remains available independently.
  const failure = await browser.newContext();
  const failedPage = await failure.newPage();
  const failedObserved = watched(failedPage);
  let failStandards = true;
  await failure.route(origin + "/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (failStandards && pathname === "/assets/data/kb-standards-cs.js") return route.abort("failed");
    const path = resolve(site, "." + pathname);
    const type = pathname.endsWith(".js") ? "text/javascript" : pathname.endsWith(".css") ? "text/css" : pathname.endsWith(".svg") ? "image/svg+xml" : "text/html";
    await route.fulfill({ body: readFileSync(path), contentType: type });
  });
  await failedPage.goto(origin + "/index.html#/cs/V/path/start");
  await rendered(failedPage, "cs", "#search-input");
  await failedPage.fill("#search-input", "10.5281/zenodo.21726258");
  await failedPage.locator("form.search").evaluate((form) => form.requestSubmit());
  await failedPage.waitForFunction(() => document.querySelector("#search-results")?.dataset.confirmed === "true" && document.querySelector("#search-results")?.dataset.query === "10.5281/zenodo.21726258");
  assert(await failedPage.locator("#search-results .result-primary").count(), "an identifier route does not wait for unrelated text-index parts");
  await failedPage.fill("#search-input", "licence");
  await failedPage.locator("form.search").evaluate((form) => form.requestSubmit());
  await failedPage.locator(".data-load-error").waitFor();
  failStandards = false;
  await failedPage.locator(".data-load-error button").click();
  await failedPage.waitForFunction(() => document.querySelector("#search-results")?.dataset.confirmed === "true" && document.querySelector("#search-results")?.dataset.query === "licence");
  assert(await failedPage.locator('#search-results a[href$="/path/licence"]').count(), "search retry renders the recovered text results");
  assert.equal(await failedPage.locator(".data-load-error").count(), 0);
  assert.deepEqual(failedObserved.errors, []);
  await failure.close();

  // A FIP-only failure cannot confirm an incomplete index. Recovery follows the pending query to the replacement form.
  const fipFailure = await browser.newContext();
  const fipPage = await fipFailure.newPage();
  const fipObserved = watched(fipPage);
  const fipQuery = "ArchaeoVault";
  let failFips = true;
  let holdFipsRetry = false;
  let releaseFipsRetry, announceFipsRetry;
  const fipRetryGate = new Promise((resolve) => { releaseFipsRetry = resolve; });
  const fipRetryRequested = new Promise((resolve) => { announceFipsRetry = resolve; });
  await fipFailure.route(origin + "/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/assets/data/kb-fips-cs.js") {
      if (failFips) return route.abort("failed");
      if (holdFipsRetry) {
        announceFipsRetry();
        await fipRetryGate;
      }
    }
    const path = resolve(site, "." + pathname);
    const type = pathname.endsWith(".js") ? "text/javascript" : pathname.endsWith(".css") ? "text/css" : pathname.endsWith(".svg") ? "image/svg+xml" : "text/html";
    await route.fulfill({ body: readFileSync(path), contentType: type });
  });
  await fipPage.goto(origin + "/index.html#/cs/V/path/start");
  await rendered(fipPage, "cs", "#search-input");
  await fipPage.fill("#search-input", fipQuery);
  await fipPage.locator("form.search").evaluate((form) => form.requestSubmit());
  await fipPage.locator(".data-load-error").waitFor();
  assert(await fipPage.evaluate(() => ["standards", "questions", "advice"].every((part) => window.FairGuide.partHasLanguage(part, "cs"))));
  assert.equal(await fipPage.evaluate(() => window.FairGuide.partHasLanguage("fips", "cs")), false);
  assert.notEqual(await fipPage.locator("#search-results").getAttribute("data-query"), fipQuery, "a missing FIP part never produces confirmed empty or partial results");
  assert.notEqual(await fipPage.locator("#search-results").getAttribute("data-confirmed"), "true");
  failFips = false;
  holdFipsRetry = true;
  await fipPage.locator(".data-load-error button").click();
  await fipRetryRequested;
  await fipPage.evaluate(() => { location.hash = "#/cs/DS/path/start"; });
  await rendered(fipPage, "cs", "#search-input");
  releaseFipsRetry();
  await fipPage.waitForFunction((query) => {
    const results = document.querySelector("#search-results");
    return results?.isConnected && results.dataset.confirmed === "true" && results.dataset.query === query;
  }, fipQuery);
  assert.equal(await fipPage.evaluate(() => window.FairGuide.state.lens), "DS");
  assert.equal(await fipPage.locator("#search-input").inputValue(), fipQuery, "retry restores the pending query when no newer query was entered");
  const fipLinks = await fipPage.locator("#search-results a").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
  assert(fipLinks.some((href) => (href || "").includes("/catalogue/repositories/archaeovault")), "successful retry includes the FIP-supplied match: " + fipLinks.join(" | "));
  assert.equal(await fipPage.locator(".data-load-error").count(), 0);
  assert.deepEqual(fipObserved.errors, []);
  await fipFailure.close();

  // A later query entered after navigation wins over completion of an older retry.
  const navigationFailure = await browser.newContext();
  const navigationPage = await navigationFailure.newPage();
  const navigationObserved = watched(navigationPage);
  let failNavigationStandards = true;
  let holdNavigationRetry = false;
  let releaseNavigationRetry, announceNavigationRetry;
  const navigationRetryGate = new Promise((resolve) => { releaseNavigationRetry = resolve; });
  const navigationRetryRequested = new Promise((resolve) => { announceNavigationRetry = resolve; });
  await navigationFailure.route(origin + "/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/assets/data/kb-standards-cs.js") {
      if (failNavigationStandards) return route.abort("failed");
      if (holdNavigationRetry) {
        announceNavigationRetry();
        await navigationRetryGate;
      }
    }
    const path = resolve(site, "." + pathname);
    const type = pathname.endsWith(".js") ? "text/javascript" : pathname.endsWith(".css") ? "text/css" : pathname.endsWith(".svg") ? "image/svg+xml" : "text/html";
    await route.fulfill({ body: readFileSync(path), contentType: type });
  });
  await navigationPage.goto(origin + "/index.html#/cs/V/path/start");
  await rendered(navigationPage, "cs", "#search-input");
  await navigationPage.fill("#search-input", fipQuery);
  await navigationPage.locator("form.search").evaluate((form) => form.requestSubmit());
  await navigationPage.locator(".data-load-error").waitFor();
  failNavigationStandards = false;
  holdNavigationRetry = true;
  await navigationPage.locator(".data-load-error button").click();
  await navigationRetryRequested;
  await navigationPage.evaluate(() => { location.hash = "#/cs/DS/path/start"; });
  await rendered(navigationPage, "cs", "#search-input");
  await navigationPage.fill("#search-input", "licence");
  releaseNavigationRetry();
  await navigationPage.waitForFunction(() => {
    const results = document.querySelector("#search-results");
    return results?.isConnected && results.dataset.confirmed === "true" && results.dataset.query === "licence";
  });
  assert.equal(await navigationPage.locator("#search-input").inputValue(), "licence", "an older retry does not replace newer reader input");
  assert(await navigationPage.locator('#search-results a[href$="/path/licence"]').count(), "the live form renders the newer query");
  assert.equal(await navigationPage.locator(".data-load-error").count(), 0);
  assert.deepEqual(navigationObserved.errors, []);
  await navigationFailure.close();

  // A clear entered after navigation is a newer revision, not an untouched field waiting for the old query.
  const clearFailure = await browser.newContext();
  const clearPage = await clearFailure.newPage();
  const clearObserved = watched(clearPage);
  let failClearStandards = true, holdClearRetry = false;
  let releaseClearRetry, announceClearRetry;
  const clearRetryGate = new Promise((resolve) => { releaseClearRetry = resolve; });
  const clearRetryRequested = new Promise((resolve) => { announceClearRetry = resolve; });
  await clearFailure.route(origin + "/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/assets/data/kb-standards-cs.js") {
      if (failClearStandards) return route.abort("failed");
      if (holdClearRetry) { announceClearRetry(); await clearRetryGate; }
    }
    const path = resolve(site, "." + pathname);
    const type = pathname.endsWith(".js") ? "text/javascript" : pathname.endsWith(".css") ? "text/css" : pathname.endsWith(".svg") ? "image/svg+xml" : "text/html";
    await route.fulfill({ body: readFileSync(path), contentType: type });
  });
  await clearPage.goto(origin + "/index.html#/cs/V/path/start");
  await rendered(clearPage, "cs", "#search-input");
  await clearPage.fill("#search-input", "licence");
  await clearPage.locator("form.search").evaluate((form) => form.requestSubmit());
  await clearPage.locator(".data-load-error").waitFor();
  failClearStandards = false;
  holdClearRetry = true;
  await clearPage.locator(".data-load-error button").click();
  await clearRetryRequested;
  await clearPage.evaluate(() => { location.hash = "#/cs/DS/path/start"; });
  await rendered(clearPage, "cs", "#search-input");
  await clearPage.fill("#search-input", "replacement");
  await clearPage.fill("#search-input", "");
  releaseClearRetry();
  await clearPage.waitForFunction(() => document.querySelector("#search-results")?.dataset.confirmed === "true");
  assert.equal(await clearPage.locator("#search-input").inputValue(), "", "an older retry does not replace a deliberate clear");
  assert.equal(await clearPage.locator("#search-results").getAttribute("data-query"), "", "an old query is not restored or submitted after a deliberate clear");
  assert.deepEqual(clearObserved.errors, []);
  await clearFailure.close();

  // A retry that finishes while the next language is loading must follow the route, not the still-connected old form.
  const languageFailure = await browser.newContext();
  const languagePage = await languageFailure.newPage();
  const languageObserved = watched(languagePage);
  let failLanguageStandards = true, holdLanguageRetry = false;
  let releaseLanguageRetry, announceLanguageRetry, releaseEnglish, announceEnglish;
  const languageRetryGate = new Promise((resolve) => { releaseLanguageRetry = resolve; });
  const languageRetryRequested = new Promise((resolve) => { announceLanguageRetry = resolve; });
  const englishGate = new Promise((resolve) => { releaseEnglish = resolve; });
  const englishRequested = new Promise((resolve) => { announceEnglish = resolve; });
  await languageFailure.route(origin + "/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/assets/data/kb-standards-cs.js") {
      if (failLanguageStandards) return route.abort("failed");
      if (holdLanguageRetry) { announceLanguageRetry(); await languageRetryGate; }
    }
    if (pathname === "/assets/data/kb-en.js") { announceEnglish(); await englishGate; }
    const path = resolve(site, "." + pathname);
    const type = pathname.endsWith(".js") ? "text/javascript" : pathname.endsWith(".css") ? "text/css" : pathname.endsWith(".svg") ? "image/svg+xml" : "text/html";
    await route.fulfill({ body: readFileSync(path), contentType: type });
  });
  await languagePage.goto(origin + "/index.html#/cs/V/path/start");
  await rendered(languagePage, "cs", "#search-input");
  await languagePage.fill("#search-input", "licence");
  await languagePage.locator("form.search").evaluate((form) => form.requestSubmit());
  await languagePage.locator(".data-load-error").waitFor();
  failLanguageStandards = false;
  holdLanguageRetry = true;
  await languagePage.locator(".data-load-error button").click();
  await languageRetryRequested;
  await languagePage.getByRole("link", { name: "English", exact: true }).click();
  await englishRequested;
  releaseLanguageRetry();
  await languagePage.waitForTimeout(0);
  assert.notEqual(await languagePage.locator("#search-results").getAttribute("data-confirmed"), "true", "an outgoing Czech form does not accept the completed retry");
  releaseEnglish();
  await rendered(languagePage, "en", "#search-input");
  await languagePage.waitForFunction(() => document.querySelector("#search-results")?.dataset.confirmed === "true" && document.querySelector("#search-results")?.dataset.query === "licence");
  assert.equal(await languagePage.locator("#search-input").inputValue(), "licence", "the current English form receives the pending query");
  assert(await languagePage.locator('#search-results a[href$="/path/licence"]').count(), "the current English form receives the recovered results");
  assert.equal(await languagePage.locator(".data-load-error").count(), 0);
  assert.deepEqual(languageObserved.errors, []);
  await languageFailure.close();

  // The latest classification wins: a failed part for obsolete text cannot suppress a newer identifier.
  const identifierFailure = await browser.newContext();
  const identifierPage = await identifierFailure.newPage();
  const identifierDOI = "10.5281/zenodo.21726258";
  const identifierObserved = watched(identifierPage);
  let releaseTextPart, announceTextPart;
  const textPartGate = new Promise((resolve) => { releaseTextPart = resolve; });
  const textPartRequested = new Promise((resolve) => { announceTextPart = resolve; });
  await identifierFailure.route(origin + "/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/assets/data/kb-standards-cs.js") { announceTextPart(); await textPartGate; return route.abort("failed"); }
    const path = resolve(site, "." + pathname);
    const type = pathname.endsWith(".js") ? "text/javascript" : pathname.endsWith(".css") ? "text/css" : pathname.endsWith(".svg") ? "image/svg+xml" : "text/html";
    await route.fulfill({ body: readFileSync(path), contentType: type });
  });
  await identifierPage.goto(origin + "/index.html#/cs/V/path/start");
  await rendered(identifierPage, "cs", "#search-input");
  await identifierPage.fill("#search-input", "licence");
  await textPartRequested;
  await identifierPage.locator("form.search").evaluate((form) => form.requestSubmit());
  await identifierPage.fill("#search-input", identifierDOI);
  releaseTextPart();
  await identifierPage.waitForFunction((query) => {
    const results = document.querySelector("#search-results");
    return results?.dataset.confirmed === "true" && results.dataset.query === query;
  }, identifierDOI);
  assert(await identifierPage.locator("#search-results .result-primary").count(), "the newer identifier renders without a second submission");
  assert.equal(await identifierPage.locator(".data-load-error").count(), 0, "the obsolete text-part failure is not an identifier error");
  assert.deepEqual(identifierObserved.errors, []);
  await identifierFailure.close();

  console.log("language checks: selected downloads, both directions, exact graph, bilingual exports/search and failed-file retry passed");
} finally {
  await browser.close();
}
