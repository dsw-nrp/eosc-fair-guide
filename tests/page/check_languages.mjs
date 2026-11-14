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
const questionPart = JSON.parse(readFileSync(resolve(site, "assets/data/kb-questions.js"), "utf8").match(/^window\.FairGuideData\.parts\["questions"\] = (.*);$/m)[1]);
const expectedNkr = questionPart.config.nkr;
const initialGraph = JSON.parse(readFileSync(resolve(site, "assets/data/kb.js"), "utf8").match(/^window\.FairGuideData\.kb = (.*);$/m)[1])["@graph"];
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

async function failedTextSearch({ holdInspection = false } = {}) {
  const context = await browser.newContext(), page = await context.newPage();
  const observed = watched(page);
  let fail = true, hold = false, release, requested;
  const gate = new Promise((resolve) => { release = resolve; });
  const asked = new Promise((resolve) => { requested = resolve; });
  let releaseInspection, requestedInspection;
  const inspectionGate = new Promise((resolve) => { releaseInspection = resolve; });
  const inspectionAsked = new Promise((resolve) => { requestedInspection = resolve; });
  await context.route("https://guide-search.test/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (holdInspection && pathname === "/assets/js/inspection.js") { requestedInspection(); await inspectionGate; }
    if (pathname === "/assets/data/kb-standards-cs.js") {
      if (fail) return route.abort("failed");
      if (hold) { requested(); await gate; }
    }
    await route.fulfill({ body: readFileSync(resolve(site, "." + pathname)),
      contentType: pathname.endsWith(".js") ? "text/javascript" : pathname.endsWith(".css") ? "text/css" : pathname.endsWith(".svg") ? "image/svg+xml" : "text/html" });
  });
  await page.goto("https://guide-search.test/index.html#/cs/V/path/start");
  await rendered(page, "cs", "#search-input");
  await page.fill("#search-input", "licence");
  await page.locator("form.search").evaluate((form) => form.requestSubmit());
  await page.locator(".data-load-error").waitFor();
  return { context, page, observed, release, releaseInspection, inspectionAsked, async recover(wait = false) {
    fail = false; hold = wait;
    await page.locator(".data-load-error button").click();
    if (wait) await asked;
  } };
}

try {
  // A cold landing action cannot interpret a delayed or unavailable registry as an absent record.
  for (const lang of ["cs", "en"]) for (const unavailable of [false, true]) {
    const context = await browser.newContext({ viewport: { width: unavailable ? 390 : 1280, height: 850 } });
    const page = await context.newPage(), observed = watched(page);
    let release, announce, fail = unavailable;
    const gate = new Promise((done) => { release = done; });
    const asked = new Promise((done) => { announce = done; });
    await context.route("https://prefill-loading.test/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname === "/assets/data/kb-questions.js") {
        announce(); await gate;
        if (fail) return route.abort("failed");
      }
      await route.fulfill({ body: readFileSync(resolve(site, "." + pathname)),
        contentType: pathname.endsWith(".js") ? "text/javascript" : pathname.endsWith(".css") ? "text/css" : pathname.endsWith(".svg") ? "image/svg+xml" : "text/html" });
    });
    await page.goto(`https://prefill-loading.test/index.html#/${lang}/SR/path/start`);
    await rendered(page, lang, "#search-input");
    await page.evaluate(() => {
      const FG = window.FairGuide, translate = FG.t;
      window.missingRegistryReads = 0;
      FG.t = (key, ...args) => { if (key === "selfcheck.prefill.re3dataMissing") window.missingRegistryReads += 1; return translate(key, ...args); };
      FG.state.answers.maturity = { items: { "maturity.01": { value: "no", origin: "user" } } };
      FG.saveState();
    });
    let id = Object.keys(questionPart.config.re3data)[0];
    assert(id, "the corpus supplies a known re3data record");
    await page.fill("#search-input", id);
    await page.locator("form.search").evaluate((form) => form.requestSubmit());
    await page.locator("#search-results button.result-primary").click();
    await asked;
    await page.waitForFunction(() => location.hash.includes("/check/maturity") && window.FairGuide.state.answers.maturity.re3data);
    await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
    assert.equal(await page.evaluate(() => window.missingRegistryReads), 0, "pending data cannot report a missing record");
    assert.equal(await page.evaluate(() => window.FairGuide.config.re3data), undefined);
    assert.equal(await page.evaluate(() => window.FairGuide.state.answers.maturity.items["maturity.01"].value), "no");
    if (unavailable) {
      release();
      await page.locator(".data-load-error").waitFor();
      assert.equal(await page.evaluate(() => window.missingRegistryReads), 0, "unavailable data cannot report a missing record");
      assert.equal(await page.evaluate(() => window.FairGuide.state.answers.maturity.re3data), id);
      await page.screenshot({ path: resolve(root, `.cache/screenshots/languages/prefill-unavailable-${lang}.png`) });
      fail = false;
      await page.locator(".data-load-error button").click();
      await rendered(page, lang, ".check-parts");
    } else {
      id = Object.keys(questionPart.config.re3data)[1];
      assert(id, "a second target exercises a superseded pending pre-fill");
      await page.evaluate((id) => window.FairGuide.selfcheck.startWithRe3data(id), id);
      release();
      await page.waitForFunction((id) => window.FairGuide.state.answers.maturity.target?.endsWith(id), id);
      assert(await page.evaluate(() => Object.values(window.FairGuide.state.answers.maturity.items).some((row) => row.prefill)), "the selected snapshot supplies pre-fill evidence after loading");
    }
    assert.equal(await page.evaluate(() => window.FairGuide.state.answers.maturity.re3data), id);
    assert.equal(await page.evaluate(() => window.FairGuide.state.answers.maturity.items["maturity.01"].value), "no");
    assert.equal(await page.evaluate(() => window.missingRegistryReads), 0);
    assert.equal(await page.locator(".data-load-error").count(), 0);
    await page.evaluate((lang) => { location.hash = `#/${lang}/SR/check/maturity/evidence`; }, lang);
    await rendered(page, lang, "#prefill-re3data");
    assert.equal(await page.locator("#prefill-re3data").inputValue(), id, "the recovered evidence control retains the chosen target");
    await page.screenshot({ path: resolve(root, `.cache/screenshots/languages/prefill-recovered-${lang}-${unavailable}.png`) });
    assert.deepEqual(observed.errors, []);
    await context.close();
  }

  const base = iri("", siteNamespace(site));
  const keywordProbe = crate["@graph"].filter((row) => row["@id"].startsWith(base + "repositories/") && !row["@id"].includes("#"))
    .flatMap((row) => [].concat(row.keywords || []).flatMap((value) => String(value["@value"] || value).match(/[\p{L}]{7,}/gu) || [])
      .filter((word) => !JSON.stringify(initialGraph.find((entry) => entry["@id"] === row["@id"].slice(base.length)) || {}).toLowerCase().includes(word.toLowerCase()))
      .map((query) => ({ query, address: row["@id"].slice(base.length) })))[0];
  assert(keywordProbe, "the corpus supplies a primary-repository keyword absent from its initial record");
  for (const lang of ["cs", "en"]) {
    const context = await browser.newContext(), page = await context.newPage();
    await page.goto(file + `#/${lang}/K/path/start`);
    await rendered(page, lang, "#search-input");
    assert.equal(await page.evaluate(() => window.FairGuide.partHasLanguage("fips", window.FairGuide.state.lang)), false);
    await page.fill("#search-input", keywordProbe.query);
    await page.locator("form.search").evaluate((form) => form.requestSubmit());
    await page.waitForFunction(() => document.querySelector("#search-results")?.dataset.confirmed === "true");
    const links = await page.locator("#search-results a").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("href")));
    assert(links.some((href) => href.includes("/catalogue/" + keywordProbe.address)), "cold search includes the deferred repository keyword: " + JSON.stringify(keywordProbe));
    await context.close();
  }

  // Registry pre-fill is absent at landing, then complete before cold checks render, in files and iframes.
  for (const lang of ["cs", "en"]) {
    for (const embedded of [false, true]) {
      const context = await browser.newContext(), page = await context.newPage(), observed = watched(page);
      await context.addInitScript((lang) => {
        if (!localStorage.getItem("eosc-fair-guide")) localStorage.setItem("eosc-fair-guide", JSON.stringify({ lang, lens: "K" }));
      }, lang);
      await page.goto(file + `#/${lang}/K/path/start`);
      let view = page;
      if (embedded) {
        await page.setContent(`<iframe title="Guide" src="${file}#/${lang}/K/path/start"></iframe>`);
        view = page.frames().find((frame) => frame !== page.mainFrame());
      }
      await rendered(view, lang, "#search-input");
      assert.equal(await view.evaluate(() => window.FairGuide.config.nkr), undefined);
      assert.equal(await view.evaluate(() => window.FairGuide.config.re3data), undefined);
      // Each document owns its saved answers; a file iframe need not share its parent's storage area.
      await view.evaluate(() => {
        const FG = window.FairGuide;
        FG.state.answers.gate = { profile: "independent", items: { "gate.13": { value: "no", origin: "user" } } };
        FG.saveState();
      });
      const route = file + `#/${lang}/K/check/gate/evidence`;
      await view.goto(route);
      await rendered(view, lang, ".check-evidence");
      assert.deepEqual(await view.evaluate(() => window.FairGuide.config.nkr), expectedNkr);
      assert(await view.evaluate(() => Object.keys(window.FairGuide.config.re3data).length > 0));
      assert.equal(await view.evaluate(() => window.FairGuide.state.answers.gate.items["gate.13"].value), "no");
      if (expectedNkr?.records.length) {
        assert.equal(await view.locator("#prefill-nkr option").count(), expectedNkr.records.length);
        assert.equal(await view.locator("#nkr-status").count(), 0, "loading cannot masquerade as an empty source");
      }
      assert(observed.requests.every((url) => /^(?:file|data):/.test(url)));
      assert.deepEqual(observed.errors, []);
      await context.close();
    }
  }

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
    const find = FG.search.find, results = document.querySelector("#search-results"), replace = results.replaceChildren.bind(results);
    window.searchEvaluations = 0; window.resultReplacements = 0;
    FG.search.find = (...args) => { window.searchEvaluations += 1; return find(...args); };
    results.replaceChildren = (...args) => { window.resultReplacements += 1; return replace(...args); };
  });
  await delayedPage.fill('#search-input', 'deferredadviceprobe');
  await requested;
  await delayedPage.locator('form.search').evaluate((form) => form.requestSubmit());
  assert.notEqual(await delayedPage.locator('#search-results').getAttribute('data-query'), 'deferredadviceprobe', 'unloaded advice does not produce a complete empty result');
  releaseAdvice();
  await delayedPage.waitForFunction(() => document.querySelector('#search-results')?.dataset.query === 'deferredadviceprobe' && document.querySelector('#search-results')?.dataset.confirmed === 'true');
  assert(await delayedPage.locator('#search-results a[href*="/path/"]').count(), 'the deferred advice is in the completed index');
  assert.equal(await delayedPage.evaluate(() => window.partInvalidations), 8, 'overlapping focus and submission merge and invalidate each part/language operation once');
  assert.equal(await delayedPage.evaluate(() => window.searchEvaluations), 1, "cold focus and confirmation score the settled query once");
  assert.equal(await delayedPage.evaluate(() => window.resultReplacements), 1, "cold confirmation replaces results once");
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
  assert.equal(await delayedPage.evaluate(() => window.resultReplacements), 1, "warm identical confirmation leaves the result tree intact");
  await delayedPage.fill("#search-input", "licence");
  await delayedPage.locator("form.search").evaluate((form) => form.requestSubmit());
  assert.equal(await delayedPage.evaluate(() => window.searchEvaluations), 2, "new input is evaluated");
  await delayedPage.evaluate(() => { window.FairGuide.invalidateData(); document.querySelector("form.search").requestSubmit(); });
  assert.equal(await delayedPage.evaluate(() => window.searchEvaluations), 3, "a new data revision is evaluated");
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

  // Completing a retry on a view without Search retains its query for the next eligible form.
  const formless = await failedTextSearch();
  await formless.recover(true);
  await formless.page.evaluate(() => { location.hash = "#/cs/V/check/dataset"; });
  formless.release();
  await formless.page.waitForFunction(() => !document.querySelector("#main form.search") && document.querySelector("#main h1"));
  await formless.page.evaluate(() => { location.hash = "#/cs/DS/path/start"; });
  await formless.page.waitForFunction(() => document.querySelector("#main form.search")?.dataset.route === location.hash);
  assert.equal(await formless.page.locator("#search-input").inputValue(), "licence", "a formless detour does not discard the pending query");
  await formless.page.waitForFunction(() => document.querySelector("#search-results")?.dataset.confirmed === "true");
  await formless.page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
  assert.equal(await formless.page.locator("#search-input").inputValue(), "licence", "recovered results remain on the settled current form");
  assert(await formless.page.locator('#search-results a[href$="/path/licence"]').count());
  assert.deepEqual(formless.observed.errors, []);
  await formless.context.close();

  // An outgoing check's late controls cannot rerender the landing and erase its recovered query.
  const outgoingCheck = await failedTextSearch({ holdInspection: true });
  await outgoingCheck.recover(true);
  await outgoingCheck.page.evaluate(() => { location.hash = "#/cs/V/check/dataset"; });
  outgoingCheck.release();
  await outgoingCheck.inspectionAsked;
  await outgoingCheck.page.evaluate(() => { location.hash = "#/cs/DS/path/start"; });
  await outgoingCheck.page.waitForFunction(() => document.querySelector("#main form.search")?.dataset.route === location.hash && document.querySelector("#search-results")?.dataset.confirmed === "true");
  outgoingCheck.releaseInspection();
  await outgoingCheck.page.waitForFunction(() => typeof window.FairGuide.selfcheck?.providersFactory === "function");
  await outgoingCheck.page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
  assert.equal(await outgoingCheck.page.locator("#search-input").inputValue(), "licence", "outgoing controls cannot erase recovered input");
  assert.equal(await outgoingCheck.page.locator("#search-results").getAttribute("data-query"), "licence");
  assert.deepEqual(outgoingCheck.observed.errors, []);
  await outgoingCheck.context.close();

  // A newer submission retires an older retry even when its load finishes after another navigation.
  const superseded = await failedTextSearch();
  await superseded.recover(true);
  await superseded.page.evaluate(() => { location.hash = "#/cs/DS/path/start"; });
  await superseded.page.waitForFunction(() => document.querySelector("#main form.search")?.dataset.route === location.hash);
  await superseded.page.fill("#search-input", identifierDOI);
  await superseded.page.locator("form.search").evaluate((form) => form.requestSubmit());
  await superseded.page.waitForFunction(() => document.querySelector("#search-results")?.dataset.query === "10.5281/zenodo.21726258");
  await superseded.page.evaluate(() => { location.hash = "#/cs/V/check/dataset"; });
  superseded.release();
  await superseded.page.waitForFunction(() => !document.querySelector("#main form.search"));
  await superseded.page.evaluate(() => { location.hash = "#/cs/K/path/start"; });
  await superseded.page.waitForFunction(() => document.querySelector("#main form.search")?.dataset.route === location.hash);
  assert.equal(await superseded.page.locator("#search-input").inputValue(), "", "the older retry cannot restore its superseded query");
  assert.deepEqual(superseded.observed.errors, []);
  await superseded.context.close();

  // Once a text error is visible, successful identifier submission retires both its alert and stale retry callback.
  const successful = await failedTextSearch();
  await successful.page.evaluate(() => { window.obsoleteSearchRetry = document.querySelector(".data-load-error button"); });
  await successful.page.fill("#search-input", identifierDOI);
  await successful.page.locator("form.search").evaluate((form) => form.requestSubmit());
  await successful.page.waitForFunction(() => document.querySelector("#search-results")?.dataset.confirmed === "true");
  assert.equal(await successful.page.locator(".data-load-error").count(), 0, "a successful DOI retires the visible text error");
  assert(await successful.page.locator("#search-results .result-primary").count());
  const staleRetryCalls = await successful.page.evaluate(async () => {
    const FG = window.FairGuide, load = FG.loadPart; let calls = 0;
    FG.loadPart = (...args) => { calls += 1; return load(...args); };
    try { window.obsoleteSearchRetry.click(); await new Promise((done) => setTimeout(done, 0)); return calls; }
    finally { FG.loadPart = load; }
  });
  assert.equal(staleRetryCalls, 0, "a retired retry cannot execute against unrelated current input");
  await successful.context.close();

  const clearedFailure = await failedTextSearch();
  await clearedFailure.page.fill("#search-input", "");
  assert.equal(await clearedFailure.page.locator(".data-load-error").count(), 0, "a deliberate clear retires the visible text error without submission");
  assert.equal(await clearedFailure.page.locator("#search-results").getAttribute("data-query"), "");
  assert(await clearedFailure.page.locator("form.search button[type=submit]").isDisabled());
  await clearedFailure.context.close();

  const unrelatedFailure = await failedTextSearch();
  await unrelatedFailure.page.evaluate(() => {
    window.unrelatedRetries = 0;
    window.FairGuide.dataLoadError(new Error("unrelated view failure"), () => { window.unrelatedRetries += 1; });
  });
  await unrelatedFailure.page.fill("#search-input", "");
  assert.equal(await unrelatedFailure.page.locator(".data-load-error").count(), 1, "clearing Search cannot conceal another view's failure");
  await unrelatedFailure.page.fill("#search-input", identifierDOI);
  await unrelatedFailure.page.locator("form.search").evaluate((form) => form.requestSubmit());
  assert.equal(await unrelatedFailure.page.locator(".data-load-error").count(), 1, "successful Search cannot conceal another view's failure");
  await unrelatedFailure.page.locator(".data-load-error button").click();
  assert.equal(await unrelatedFailure.page.evaluate(() => window.unrelatedRetries), 1);
  await unrelatedFailure.context.close();

  // A script can download successfully but omit its payload. Retry must refetch the corrected local file.
  for (const missing of ["neutral", "translation", "language", "questions", "question-translation"]) {
    const context = await browser.newContext(), page = await context.newPage(), observed = watched(page);
    const registry = missing === "questions" || missing === "question-translation";
    const target = { neutral: "/assets/data/kb-standards.js", translation: "/assets/data/kb-standards-cs.js", language: "/assets/data/kb-en.js", questions: "/assets/data/kb-questions.js", "question-translation": "/assets/data/kb-questions-cs.js" }[missing];
    const requests = [];
    let omit = true;
    await context.route("https://guide-registration.test/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      requests.push(pathname);
      await route.fulfill({ body: omit && pathname === target ? "/* payload intentionally absent */" : readFileSync(resolve(site, "." + pathname)),
        contentType: pathname.endsWith(".js") ? "text/javascript" : pathname.endsWith(".css") ? "text/css" : pathname.endsWith(".svg") ? "image/svg+xml" : "text/html" });
    });
    await page.goto("https://guide-registration.test/index.html#/cs/V/" + (missing === "language" ? "check/software/answers" : "path/start"));
    let saved;
    if (missing === "language") {
      await rendered(page, "cs", "#answer-software-04-no");
      await page.locator("#answer-software-04-no").check();
      saved = await page.evaluate(() => JSON.stringify(window.FairGuide.state.answers.software));
      await page.getByRole("link", { name: "English", exact: true }).click();
    } else if (registry) {
      await rendered(page, "cs", "#search-input");
      await page.evaluate(() => {
        const FG = window.FairGuide;
        FG.state.answers.gate = { profile: "independent", items: { "gate.13": { value: "no", origin: "user" } } };
        FG.saveState(); location.hash = "#/cs/K/check/gate/evidence";
      });
    } else {
      await rendered(page, "cs", "#search-input");
      await page.fill("#search-input", "licence");
      await page.locator("form.search").evaluate((form) => form.requestSubmit());
    }
    await page.locator(".data-load-error").waitFor();
    const failedRequests = requests.filter((path) => path === target).length;
    assert(failedRequests >= 1);
    if (registry) {
      assert.equal(await page.locator("#nkr-status").count(), 0, "an unregistered source cannot report an empty registry");
      assert.equal(await page.evaluate(() => window.FairGuide.state.answers.gate.items["gate.13"].value), "no");
    }
    if (missing === "language") {
      assert(await page.locator("#answer-software-04-no").isChecked(), "failed registration preserves the usable view and answers");
    } else {
      if (!registry) assert.notEqual(await page.locator("#search-results").getAttribute("data-confirmed"), "true", "missing registration cannot confirm incomplete search");
    }
    omit = false;
    await page.locator(".data-load-error button").click();
    if (missing === "language") {
      await rendered(page, "en", "#answer-software-04-no");
      assert.equal(await page.evaluate(() => JSON.stringify(window.FairGuide.state.answers.software)), saved);
      assert(await page.locator("#answer-software-04-no").isChecked());
    } else if (registry) {
      await rendered(page, "cs", ".check-evidence");
      assert.deepEqual(await page.evaluate(() => window.FairGuide.config.nkr), expectedNkr);
      assert.equal(await page.evaluate(() => window.FairGuide.state.answers.gate.items["gate.13"].value), "no");
    } else {
      await page.waitForFunction(() => document.querySelector("#search-results")?.dataset.confirmed === "true");
      assert(await page.locator('#search-results a[href$="/path/licence"]').count());
      assert.equal(requests.filter((path) => path === (missing === "neutral" ? "/assets/data/kb-standards-cs.js" : "/assets/data/kb-standards.js")).length, 1, "accepted companion data is reused");
    }
    assert.equal(requests.filter((path) => path === target).length, failedRequests + 1, "Retry requests the previously unregistered script again");
    assert(await page.evaluate(() => new Set(window.FairGuide.graph.map((entity) => entity["@id"])).size === window.FairGuide.graph.length));
    assert.equal(await page.locator(".data-load-error").count(), 0);
    assert.deepEqual(observed.errors, []);
    await context.close();
  }

  console.log("language checks: selected downloads, both directions, exact graph, bilingual exports/search and failed-file retry passed");
} finally {
  await browser.close();
}
