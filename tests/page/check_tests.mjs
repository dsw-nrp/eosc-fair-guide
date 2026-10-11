// Test identity is visible to readers and all local code/documentation attachments are real files.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { AxeBuilder } from "@axe-core/playwright";

const root = resolve(import.meta.dirname, "../..");
const site = resolve(root, process.env.FAIR_GUIDE_SITE || "_site");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const { chromium } = await import("playwright");
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();
const screenshots = resolve(root, ".cache/screenshots/tests");
mkdirSync(screenshots, { recursive: true });
const base = pathToFileURL(resolve(site, "index.html")).href;
const graph = JSON.parse(readFileSync(resolve(site, "ro-crate-metadata.json"), "utf8"))["@graph"];
const definitions = graph.filter((entry) => String(entry["@id"]).startsWith("#test-"));
const localDefinitions = definitions.filter((entry) => entry.identifier.startsWith("guide-"));
const questions = graph.filter((entry) => entry["@type"] === "Question");
function principlesOf(entity) {
  const about = Array.isArray(entity.about) ? entity.about : [entity.about];
  return [...new Set(about.map((reference) => graph.find((entry) => entry["@id"] === reference?.["@id"])?.termCode).filter(Boolean))];
}
const errors = [];
const requests = [];
let axeRunning = false;
page.on("pageerror", (error) => errors.push(error.message));
page.on("request", (request) => { if (!/^(?:file|data):/.test(request.url()) && !axeRunning) requests.push(request.url()); });

async function visit(hash) {
  if (page.url() === base + hash) return;
  const previous = await page.$("#main");
  await page.goto(base + hash);
  if (previous) await page.waitForFunction((node) => !node.isConnected, previous);
  await page.waitForSelector(".catalogue-results");
}

async function choose(selector) {
  const previous = await page.$("#main");
  await page.locator(selector).check();
  await page.waitForFunction((node) => !node.isConnected, previous);
}

async function checkFacets(lang) {
  for (const [kind, entities] of [["tests", definitions], ["questions", questions]]) {
    for (const code of ["F1", "F2", "F3", "A1", "A1.1", "A1.2", "I1", "I2", "I3", "R1", "R1.1", "R1.2", "R1.3"]) {
      await visit(`#/${lang}/K/catalogue/k!${kind}~p!${code}`);
      const expected = entities.filter((entry) => principlesOf(entry).includes(code)).length;
      const shown = await page.locator(".entry-card").count();
      assert.equal(shown, expected, `the existing ${code} principle filter covers all ${kind} groups`);
      assert(await page.locator(`[data-facet="principle"] input:checked`).count() === 1);
      assert.equal(await page.locator('[data-facet$="-fair"]').count(), 0, "FAIR mapping uses the shared principle facet");
    }
  }
  await visit(`#/${lang}/K/catalogue/questions/software.20`);
  assert.equal(await page.locator('[id="item-software.20"] .principle-tile').count(), 0, "a badge review is not forced into a FAIR principle");
  await visit(`#/${lang}/K/catalogue/questions/cdif.04`);
  for (const code of ["A1.2", "R1.1"]) assert.equal(await page.locator(`[id="item-cdif.04"] .principle-tile[href$="/explorer/${code}"]`).count(), 1, "question records show their existing principle tags");
  await visit(`#/${lang}/K/catalogue/k!tests~p!R1`);
  const main = await page.$("#main");
  await page.locator("#facet-kind-questions").check();
  await page.waitForFunction((node) => !node.isConnected, main);
  assert(await page.locator("#facet-principle-r1").isChecked(), "the shared principle selection survives switching kind");
  assert(page.url().includes("p!R1"));
  await visit(`#/${lang}/K/catalogue/k!tests`);
  assert.equal(await page.locator('[for="facet-tests-execution-browser"] .facet-count').textContent(), String(localDefinitions.length));
  assert.equal(await page.locator('[for="facet-tests-execution-service"] .facet-count').textContent(), String(definitions.length - localDefinitions.length));
  assert(await page.evaluate(() => {
    const kind = document.querySelector('[data-facet="kind"]');
    const execution = document.querySelector('[data-facet="tests-execution"]');
    return Boolean(execution?.closest(".facet-kind")) && Boolean(kind.compareDocumentPosition(execution) & Node.DOCUMENT_POSITION_FOLLOWING);
  }), "test facets stay inside the test section below Kind");
  await choose("#facet-tests-execution-browser");
  await choose("#facet-tests-check-software");
  const software = localDefinitions.filter((entry) => entry.isImplementationOf["@id"].startsWith("#item-software."));
  assert.equal(await page.locator(".entry-card").count(), software.length);
  assert(page.url().includes("f.execution!browser") && page.url().includes("f.check!software"), "facet selections are in the shareable URL");
  const saved = page.url();
  const restored = await context.newPage();
  await restored.goto(saved);
  await restored.waitForSelector("#facet-tests-execution-browser:checked");
  assert(await restored.locator("#facet-tests-check-software").isChecked());
  assert.equal(await restored.locator(".entry-card").count(), software.length);
  await restored.close();
  await visit(`#/${lang}/K/catalogue/k!tests~f.execution!service~f.thealth!degraded`);
  const degraded = definitions.filter((entry) => !entry.identifier.startsWith("guide-") && entry.healthStatus === "degraded");
  assert.equal(await page.locator(".entry-card").count(), degraded.length);
  assert.equal(await page.locator('.entry-card[id^="item-guide-"]').count(), 0, "recorded service status never includes local tests");
  await visit(`#/${lang}/K/catalogue/k!tests~o!name`);
  const previous = await page.$("#main");
  await page.locator("#catalogue-order").selectOption("check");
  await page.waitForFunction((node) => !node.isConnected, previous);
  const headings = await page.locator(".catalogue-group > h2").allTextContents();
  for (const id of new Set(localDefinitions.map((entry) => entry.isImplementationOf["@id"].slice(6).split(".")[0]))) {
    const check = graph.find((entry) => entry["@id"] === "#check-" + id);
    assert(headings.some((heading) => heading.includes(check.name.find((entry) => entry["@language"] === lang)["@value"])), "check ordering groups tests by the check they support");
  }
}

try {
  for (const lang of ["cs", "en"]) {
    await page.setViewportSize({ width: 1280, height: 900 });
    await checkFacets(lang);
    // Check the crate and every generated record independently of pagination in the catalogue.
    assert.equal(definitions.length, 52);
    for (const test of definitions) {
      const automatic = test.identifier.startsWith("guide-");
      const anchor = automatic ? test.identifier : "fair-champion." + test.identifier;
      await visit(`#/${lang}/K/catalogue/tests/${anchor}`);
      await page.waitForSelector("#item-" + anchor.replaceAll(".", "\\."));
      const entry = page.locator("[id='item-" + anchor + "']");
      assert.equal(await entry.locator(".entry-title").textContent(), test.name.find((value) => value["@language"] === lang)["@value"]);
      if (automatic) assert.equal(await entry.locator(".entry-what").textContent(), lang === "cs" ? "test průvodce" : "guide test");
      assert.equal(await entry.locator(".card-details").textContent(), automatic ? lang === "cs" ? "v prohlížeči" : "in the browser" : lang === "cs" ? "externí služba" : "external service");
      assert(await entry.textContent().then((value) => value.includes(test.description.find((value) => value["@language"] === lang)["@value"])), "test purpose is readable in each language");
      assert.equal(await entry.locator(`a[href="${test.url}"]`).count(), 1, "test entry links actual implementation or execution endpoint");
      assert.equal(await entry.locator("code").count(), automatic ? 1 : 0, "local entry names its invoked function");
      assert(await entry.locator("a").filter({ hasText: lang === "cs" ? "Popis testu" : "Test documentation" }).count() > 0, "documentation is linked independently of execution");
      if (automatic) assert.equal(await entry.locator(`a[href="assets/js/tests/index.html#${test.identifier}${lang === "en" ? "-en" : ""}"]`).count(), 1, "documentation leads to this test's heading in the selected language");
      if (automatic) assert(await entry.locator("a[href*='/questions/']").count() > 0, "local test identifies the question it can prefill");
      for (const code of principlesOf(test)) assert.equal(await entry.locator(`.relations .principle-tile[href$="/explorer/${code}"]`).count(), 1, "test records show their existing FAIR tags");
    }
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(base + `#/${lang}/K/catalogue/tests/guide-software-14`);
      await page.waitForSelector("#item-guide-software-14");
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      axeRunning = true;
      const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
      axeRunning = false;
      assert.deepEqual(result.violations.map((violation) => violation.id), []);
      await page.locator("#item-guide-software-14").scrollIntoViewIfNeeded();
      await page.screenshot({ path: resolve(screenshots, `${lang}-software-14-${width}.png`) });
    }
  }
  const docBase = pathToFileURL(resolve(site, "assets/js/tests/index.html")).href;
  await page.goto(docBase);
  await page.waitForSelector("#object");
  assert.equal(await page.locator("[lang='en'] #english-title").count(), 1);
  for (const lang of ["cs", "en"]) for (const test of localDefinitions) {
    const anchor = test.identifier + (lang === "en" ? "-en" : "");
    const section = page.locator(`section[aria-labelledby="${anchor}"]`);
    assert.equal(await section.locator("h3 > code").textContent(), test.identifier, "each test ID appears in its own documentation heading");
    assert((await section.locator("h3").textContent()).includes(test.name.find((value) => value["@language"] === lang)["@value"]));
    assert((await section.textContent()).includes(test.description.find((value) => value["@language"] === lang)["@value"]));
    assert.equal(await section.locator(`a[href="../../../index.html#/${lang}/K/catalogue/questions/${test.isImplementationOf["@id"].slice(6)}"]`).count(), 1);
    assert.equal(await section.locator(`a[href="../../../api/tests/${test.identifier}.json"]`).count(), 1);
  }
  for (const [lang, id] of [["cs", "guide-cdif-04"], ["en", "guide-software-14"]]) for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(docBase + "#" + id + (lang === "en" ? "-en" : ""));
    const heading = page.locator("#" + id + (lang === "en" ? "-en" : ""));
    await heading.scrollIntoViewIfNeeded();
    assert(await heading.isVisible());
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await page.screenshot({ path: resolve(screenshots, `${lang}-documentation-${id}-${width}.png`) });
  }
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  axeRunning = true;
  const docs = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  axeRunning = false;
  assert.deepEqual(docs.violations.map((violation) => violation.id), []);
  assert.deepEqual(errors, []);
  assert.deepEqual(requests, [], "browsing test definitions makes no external request");
  console.log("check_tests: 52 bilingual catalogue identities, executable/doc links, local attachments and accessible layouts pass");
} finally {
  await browser.close();
}
