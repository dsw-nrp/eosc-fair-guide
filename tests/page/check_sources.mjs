// Original passages survive deferred loading in every question and remain readable in the principle explorer.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const { chromium } = await import("playwright");
const graph = JSON.parse(readFileSync(resolve(root, "_site/ro-crate-metadata.json"), "utf8"))["@graph"];
const checks = graph.filter((entity) => entity["@type"] === "Quiz");
const principles = graph.filter((entity) => String(entity["@id"]).startsWith("#principle-") && entity.termCode);
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();
const base = pathToFileURL(resolve(root, "_site/index.html")).href;
const screenshots = resolve(root, ".cache/screenshots/sources");
mkdirSync(screenshots, { recursive: true });
const problems = [];
const external = [];
let axeRunning = false;
page.on("pageerror", (error) => problems.push(error.message));
page.on("request", (request) => { if (!/^(?:file|data):/.test(request.url()) && !axeRunning) external.push(request.url()); });

async function visit(hash) {
  const previous = await page.$("#main");
  await page.goto(base + hash);
  if (previous) await page.waitForFunction((node) => !node.isConnected, previous);
  await page.waitForSelector("#main h1");
}

async function resize(width) {
  const previous = await page.$("#main");
  const rerenders = await page.evaluate((width) => Boolean(document.querySelector(".check-view")) && matchMedia("(min-width: 60rem)").matches !== (width >= 960), width);
  await page.setViewportSize({ width, height: 900 });
  if (rerenders) await page.waitForFunction((node) => !node.isConnected, previous);
}

try {
  // A direct station visit needs its originals without a preceding visit to a check or catalogue.
  await page.goto(base + "#/cs/V/path/licence");
  await page.waitForSelector('.station details[data-key="L2"] .clause-guidance', { state: "attached" });
  for (const lang of ["cs", "en"]) {
    const seen = new Set();
    const withoutOriginal = new Set();
    for (const check of checks) {
      const id = check.identifier;
      await visit(`#/${lang}/V/check/${id}/answers`);
      await page.waitForFunction(() => window.FairGuide?.partsLoaded.has("questions") && window.FairGuide.partsLoaded.has("standards"));
      const combinations = await page.evaluate((id) => {
        const FG = window.FairGuide;
        const codes = (prefix) => FG.refs(FG.get(prefix + id), "hasDefinedTerm").map((term) => term.termCode);
        return { modes: codes("#modes-").length ? codes("#modes-") : [null], profiles: codes("#profiles-").length ? codes("#profiles-") : [null] };
      }, id);
      for (const mode of combinations.modes) for (const profile of combinations.profiles) {
        await page.evaluate(({ id, mode, profile }) => {
          const FG = window.FairGuide;
          FG.state.answers[id] = { items: {}, extended: true, mode, profile };
          FG.saveState(); FG.rerender();
        }, { id, mode, profile });
        await page.waitForSelector(`#main .item[id^="item-${id}-"]`);
        const result = await page.evaluate((id) => {
          const FG = window.FairGuide;
          const errors = [], seen = [], missing = [];
          for (const row of document.querySelectorAll(`#main .item[id^="item-${id}-"]`)) {
            const identifier = id + "." + row.id.split("-").pop();
            seen.push(identifier);
            const clauses = FG.refs(FG.get("#item-" + identifier), "citation").filter((clause) => clause.guidance);
            const originals = [...row.querySelectorAll(".clause-guidance")];
            if (!clauses.length) missing.push(identifier);
            if (originals.length !== clauses.length) errors.push(identifier + ": original count differs");
            for (let index = 0; index < clauses.length; index++) {
              const clause = clauses[index], original = originals[index], source = FG.get(clause.isPartOf);
              const body = original?.querySelector(":scope > .content");
              if (!body || body.lang !== clause.guidance["@language"]) errors.push(identifier + ": original language lost");
              if (original?.open) errors.push(identifier + ": original unexpectedly expanded");
              if (source.creditText && !body?.textContent.includes(source.creditText)) errors.push(identifier + ": source attribution lost");
              if (source.license && !body?.querySelector(`a[href="${FG.id(source.license) || source.license}"]`)) errors.push(identifier + ": reuse link lost");
              if (!body?.querySelector(".source-link")) errors.push(identifier + ": source link lost");
            }
          }
          return { errors, seen, missing };
        }, id);
        assert.deepEqual(result.errors, [], `${lang}, ${id}, ${mode}, ${profile}`);
        result.seen.forEach((identifier) => seen.add(identifier));
        result.missing.forEach((identifier) => withoutOriginal.add(identifier));
      }
    }
    const expected = graph.filter((entity) => entity["@type"] === "Question").map((entity) => entity.identifier);
    assert.deepEqual([...seen].sort(), expected.sort(), "every question rendered, including profile and mode variants");
    assert.deepEqual([...withoutOriginal].sort(), ["institution.24", "maturity.18"]);

    for (const [id, number] of [["institution", "02"], ["dataset", "27"], ["software", "20"]]) {
      await visit(`#/${lang}/V/check/${id}/answers`);
      if (id === "dataset") await page.evaluate(() => {
        const FG = window.FairGuide; FG.state.answers.dataset.mode = "after"; FG.state.answers.dataset.profile = "os3"; FG.rerender();
      });
      const row = page.locator(`#item-${id}-${number}`);
      for (const width of [1280, 390]) {
        await resize(width);
        /* The sources sit in the question card's details, which open first. */
        const card = row.locator(".question-details");
        if (!(await card.evaluate((node) => node.open))) await card.locator(":scope > summary").click();
        const basis = row.locator(".item-basis");
        if (!(await basis.evaluate((node) => node.open))) await basis.locator(":scope > summary").click();
        const original = row.locator(".clause-guidance").first();
        if (!(await original.evaluate((node) => node.open))) await original.locator(":scope > summary").click();
        await row.screenshot({ path: resolve(screenshots, `${lang}-${id}-${number}-${width}.png`) });
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      }
    }

    for (const principle of principles) {
      await visit(`#/${lang}/V/explorer/${principle.termCode}`);
      await page.waitForSelector(".principle-detail");
      assert.equal(await page.locator('[data-clause-status="refresh"]').count(), 0);
      for (const width of [1280, 320]) {
        await page.setViewportSize({ width, height: 900 });
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${lang} ${principle.termCode}: reflow`);
      }
    }
    await visit(`#/${lang}/V/explorer/F1`);
    const refresh = page.locator(".clause", { has: page.locator('a.id-chip[href$="/A.F1.N3"]') });
    assert.equal(await refresh.locator(".clause-note").count(), 1, "keep the explanation about newer source context");
    await visit(`#/${lang}/V/explorer/R1.1`);
    assert(await page.locator('[data-clause-status="superseded"]').count(), "readers still see superseded-source warnings");
    const original = page.locator(".principle-requirements .clause-guidance").first();
    await original.locator(":scope > summary").click();
    assert(await original.locator(":scope > .content > p").evaluateAll((paragraphs) => paragraphs.every((p) => parseFloat(getComputedStyle(p).marginBottom) > 0)), "original paragraphs retain spacing");
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await original.scrollIntoViewIfNeeded();
      await page.screenshot({ path: resolve(screenshots, `${lang}-principle-original-${width}.png`) });
      axeRunning = true;
      const access = await audit(page);
      axeRunning = false;
      assert.deepEqual(access.violations, [], "expanded principles remain accessible");
    }
    await visit(`#/${lang}/V/catalogue/cl/A.F1.N3`);
    await page.waitForSelector("#item-A\\.F1\\.N3");
    assert.equal(await page.locator('[data-clause-status="refresh"]').count(), 0);
    assert.equal(await page.locator("#item-A\\.F1\\.N3 .clause-note").count(), 1);

    for (const lens of ["V", "DS", "SR", "K"]) {
      await visit(`#/${lang}/${lens}/path/licence`);
      const why = page.locator('details[data-key="L2"]');
      if (!(await why.evaluate((node) => node.open))) await why.locator(":scope > summary").click();
      assert(await why.locator(".clause > .entry-head + .clause-text, .clause > .entry-head + .clause-title").count(), "Proč uses the same compact catalogue hierarchy");
      for (const width of [1280, 390]) {
        await page.setViewportSize({ width, height: 900 });
        await why.scrollIntoViewIfNeeded();
        await page.screenshot({ path: resolve(screenshots, `${lang}-why-${lens}-${width}.png`) });
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      }
    }
  }
  assert.deepEqual(problems, []);
  assert.deepEqual(external, [], "source and principle browsing makes no external requests");
  console.log("check_sources: originals in every applicable question, lazy attribution, all bilingual principles, update notes, accessibility and reflow pass");
} finally { await browser.close(); }
