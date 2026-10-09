// Page checks for the FAIR Data Guide, run in Chromium with Playwright:
// - the page renders from a local file without any external request on load, console error or CSP violation;
// - every station renders in every lens and language, and so do the other views;
// - axe finds no WCAG 2.2 A or AA violation in any of those views;
// - the keyboard reaches the main controls, the page reflows at 320 px, and it works inside an iframe;
// - the self-check runs without network: modes, profiles, tiers, gaps on the path, snapshot pre-fill, a shared
//   link and the exports, with no score anywhere.
// Usage: npm run check:page   (set PLAYWRIGHT_BROWSERS_PATH if the browser lives outside the default cache)

import { chromium } from "playwright";
import { AxeBuilder } from "@axe-core/playwright";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const pageUrl = pathToFileURL(resolve(root, "index.html")).href;
const crate = JSON.parse(readFileSync(resolve(root, "ro-crate-metadata.json"), "utf8"));
const graph = crate["@graph"];
const stations = graph.filter((e) => e["@type"] === "HowToSection").map((e) => e.identifier);
const lenses = graph.filter((e) => e["@type"] === "Audience" && e["@id"].startsWith("#lens-")).map((e) => e.audienceType);
/** The result so far must stay short and never scroll on its own. */
const panelFits = (page) =>
  page.evaluate(() => {
    const panel = document.querySelector(".check-summary");
    return panel && panel.scrollHeight <= panel.clientHeight + 1 && panel.getBoundingClientRect().height <= window.innerHeight * 0.6;
  });
const lensShown = (page, lens) => page.waitForFunction((expected) => {
  const current = document.querySelector('.lens-option[aria-current="true"]');
  return current && current.dataset.lens === expected;
}, lens);
const pages = graph.filter((e) => String(e["@id"]).startsWith("#page-") && e.identifier && !e.isPartOf).map((e) => e.identifier);
const principles = graph.filter((e) => String(e["@id"]).startsWith("https://w3id.org/fair/principles/terms/") && e.termCode).map((e) => e.termCode);
const checks = graph.filter((e) => e["@type"] === "Quiz").map((e) => ({ id: e.identifier, lens: [].concat(e.audience)[0]["@id"].replace("#lens-", "") }));
const failures = [];
const fail = (message) => failures.push(message);

const browser = await chromium.launch();

async function openPage(viewport) {
  const context = await browser.newContext({ viewport: viewport || { width: 1280, height: 900 } });
  const page = await context.newPage();
  const external = [];
  const problems = [];
  const state = { axeRunning: false };
  page.on("request", (request) => {
    const url = request.url();
    if (!url.startsWith("file:") && !url.startsWith("data:")) external.push(url);
  });
  page.on("console", (message) => {
    // axe fetches stylesheets to inspect them; the page's own CSP blocks that, which is the page working.
    if (message.type() === "error" && !state.axeRunning) problems.push("console: " + message.text());
  });
  page.on("pageerror", (error) => problems.push("page error: " + error.message));
  page.axeState = state;
  return { context, page, external, problems };
}

async function rendered(page) {
  await page.waitForFunction(() => { const h1 = document.querySelector("#main h1"); return h1 && h1.textContent.trim() && !document.body.textContent.includes("The guide is loading."); });
}

async function axe(page, label) {
  page.axeState.axeRunning = true;
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  page.axeState.axeRunning = false;
  for (const violation of result.violations) {
    fail(`${label}: axe ${violation.id} (${violation.impact}) on ${violation.nodes.length} node(s): ${violation.nodes[0].target.join(" ")}`);
  }
}

// 1. Load from a local file: no external request, no error.
{
  const { context, page, external, problems } = await openPage();
  await page.goto(pageUrl);
  await rendered(page);
  if (external.length) fail("requests on load: " + external.join(", "));
  for (const problem of problems) fail("load: " + problem);
  const heading = await page.textContent("#main h1");
  if (!heading.includes("Průvodce FAIR daty")) fail("first visit does not open the landing: " + heading);
  if (!(await page.locator("#search-input").count())) fail("landing: no search box");
  if (!(await page.locator("#stage-question").textContent()).includes("Kde se právě nacházíte")) fail("landing: no stage question");
  if ((await page.locator(".stage-card").count()) !== 4) fail("landing: the four stage cards are missing");
  if (!(await page.locator(".stage-card").first().textContent()).includes("Krok 1")) fail("landing: the stage cards do not name the steps they cover");
  if (await page.locator(".stage-current").count()) fail("landing: a first visit marks a current stage");
  if (!(await page.locator(".tasks .task").count())) fail("landing: no task shortcuts");
  const stageWeights = await page.locator(".stage-card").first().evaluate((card) => [getComputedStyle(card.querySelector("strong")).fontWeight, getComputedStyle(card.querySelector(".small")).fontWeight]);
  if (Number(stageWeights[1]) >= Number(stageWeights[0]) || Number(stageWeights[1]) > 400) fail("landing: a stage card's description is as bold as its title: " + stageWeights.join("/"));
  await axe(page, "landing");

  // The catalogue: one menu item over one list narrowed by facets with counts. Kind is a single choice, and older
  // addresses select their kind; every kind lists its entries; resources and cited sources
  // are one kind marked by usage; a facet keeps focus and puts the state in the address, which opens the same list;
  // station and principle apply across kinds and say when a kind lacks them; the reader orders the list and groups
  // follow; changes name no people; the page for machines links the knowledge base.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const menu = async () => view.locator(".main-nav a").evaluateAll((links) => links.map((link) => link.textContent.trim()));
    const current = async () => (await view.locator('.main-nav [aria-current="page"]').textContent()).trim();
    const kinds = async () => view.locator('[data-facet="kind"] input:checked').evaluateAll((boxes) => boxes.map((box) => box.id.replace("facet-kind-", "")).join(","));
    const found = async () => Number(((await view.locator(".catalogue-count").textContent()).match(/\d+/) || [0])[0]);
    const open = async (hash) => {
      await view.goto(pageUrl + hash);
      await view.waitForSelector(".catalogue-layout");
    };
    await open("#/cs/V/resources");
    const items = await menu();
    if (!items.includes("Katalog") || items.includes("Zdroje") || items.includes("Repozitáře")) fail("catalogue: the menu does not hold one catalogue item in place of the finders: " + items.join(", "));
    if ((await current()) !== "Katalog" || (await kinds()) !== "resources") fail("catalogue: the resources address does not select the resources: " + (await kinds()));
    await open("#repositories");
    if ((await kinds()) !== "repositories") fail("catalogue: an in-page link to the repositories does not select them");
    for (const [old, kind] of [["sources", "resources"], ["clauses", "clauses"], ["questions", "questions"], ["terms", "terms"], ["fips", "fips"], ["tests", "tests"], ["actions", "actions"]]) {
      await open("#/cs/V/catalogue/" + old);
      if ((await kinds()) !== kind) fail(`catalogue: the address for ${old} does not select ${kind}`);
      if (!(await view.locator(".catalogue-results .card").count())) fail(`catalogue: ${kind} list nothing`);
    }
    if ((await view.locator('[data-facet="kind"] input[type="radio"]').count()) !== 8) fail("catalogue: the kind is not a single choice among eight");
    const toolbarGap = await view.evaluate(() => {
      const bar = document.querySelector(".catalogue-toolbar");
      return bar.nextElementSibling.getBoundingClientRect().top - bar.getBoundingClientRect().bottom;
    });
    if (toolbarGap < 8) fail(`catalogue: the ordering control touches the content below it (${toolbarGap}px)`);
    const changes = await view.locator(".catalogue-results").textContent();
    if (/Novák|Claude/.test(changes)) fail("catalogue: the content changes name people or tools");
    const drewOn = await view.locator(".change", { hasText: "FAIRsharing" }).first().textContent();
    if ((drewOn.match(/FAIRsharing/g) || []).length > 4) fail("catalogue: a change lists one source more than once: " + drewOn);
    await open("#/cs/V/catalogue/terms");
    if (!(await view.locator(".term-card h3").first().textContent()).match(/^[^[(]/)) fail("catalogue: the glossary does not sort past leading brackets");

    // Resources and cited sources as one kind, marked by how the guide uses them.
    await open("#/cs/V/catalogue/resources");
    const analysis = await view.locator(".card", { hasText: "Analýza a návrh postupů" }).first().textContent();
    if (!analysis.includes("podklad obsahu") || !analysis.includes("1 · Plán") || !analysis.includes("Zralost FAIR repozitáře")) fail("catalogue: the analysis is not marked as a basis with the stations and checks that cite it");
    const both = await view.locator(".card", { hasText: "AI jako služba (CERIT)" }).first().textContent();
    if (!both.includes("doporučuje průvodce") || !both.includes("podklad obsahu")) fail("catalogue: a resource that is also cited is not marked with both uses");

    // Facets: a choice keeps focus and goes into the address; the kind replaces the previous one; counts follow.
    await view.locator("#facet-kind-clauses").check();
    await view.waitForFunction(() => location.hash.includes("k!clauses"));
    if ((await view.evaluate(() => document.activeElement && document.activeElement.id)) !== "facet-kind-clauses") fail("catalogue: the kind picker does not keep focus");
    if ((await kinds()) !== "clauses" || (await view.locator(".clause-card").count()) !== (await view.locator(".catalogue-results .card").count())) fail("catalogue: choosing a kind does not replace the previous one");
    const before = await found();
    await view.locator("#facet-station-licence").check();
    await view.waitForFunction(() => location.hash.includes("s!licence"));
    if (!((await found()) > 0 && (await found()) < before)) fail("catalogue: the station facet does not narrow the list");
    if (!(await view.locator('[data-facet="kind"] li', { hasText: "Profily FIP" }).textContent()).includes("nemají zastávku")) fail("catalogue: a kind without stations does not say why it shows none");
    await view.locator("#catalogue-order").selectOption("principle");
    await view.waitForFunction(() => location.hash.includes("o!principle"));
    if (!(await view.locator(".catalogue-group > h2").count())) fail("catalogue: ordering by principle does not group the list");
    const address = await view.evaluate(() => location.hash);
    const count = await found();
    await view.goto("about:blank");
    await open(address);
    if ((await found()) !== count || (await kinds()) !== "clauses") fail("catalogue: the address does not reopen the same list");
    await view.locator("#facet-kind-resources").check();
    await view.waitForFunction(() => location.hash.includes("k!resources"));
    if (!(await view.evaluate(() => location.hash.includes("s!licence")))) fail("catalogue: changing the kind drops the station");
    await view.locator("#facet-kind-clauses").check();
    await view.waitForFunction(() => location.hash.includes("k!clauses"));
    await view.locator("#catalogue-search").fill("licence");
    await view.waitForFunction(() => location.hash.includes("q!licence"));
    if (!((await found()) > 0 && (await found()) < count)) fail("catalogue: the search does not narrow the list");
    await view.locator(".active-filters .button-link").click();
    await view.waitForFunction(() => !location.hash.includes("s!licence") && !location.hash.includes("q!"));

    // In English, titles and badges carry no Czech outside an original title marked as Czech, and a work the guide
    // only cites shows its original title with the translation in brackets; in Czech the original stands alone.
    const openAll = async (hash) => {
      await open(hash);
      while (await view.locator(".catalogue-more").count()) await view.locator(".catalogue-more").first().click();
    };
    await openAll("#/en/V/catalogue/resources");
    const czechOutside = await view.evaluate(() => {
      const czech = /[ěščřžůťďňáéíóúý]/i;
      const found = [];
      for (const holder of document.querySelectorAll(".catalogue-results .card h3, .catalogue-results .card .badge")) {
        const walker = document.createTreeWalker(holder, NodeFilter.SHOW_TEXT);
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
          if (czech.test(node.textContent) && node.parentElement.closest("[lang]").getAttribute("lang") !== "cs") found.push(node.textContent.trim());
        }
      }
      return found;
    });
    if (czechOutside.length) fail("catalogue: Czech names in English titles or badges: " + czechOutside.slice(0, 5).join(" | "));
    const surveyTitle = async () => (await view.locator(".card h3", { hasText: "Stav správy výzkumných dat" }).first().textContent()).trim();
    if (!(await surveyTitle()).includes("[State of research data management in the Czech Republic 2025]")) fail("catalogue: a cited Czech work does not show its translated title in English: " + (await surveyTitle()));
    await openAll("#/cs/V/catalogue/resources");
    if ((await surveyTitle()).includes("[")) fail("catalogue: in Czech a Czech work shows a translation: " + (await surveyTitle()));

    // Exports: every view but a single check offers printing and the whole crate under it; the catalogue saves the
    // filtered list it shows as CSV and JSON, a station saves itself as Markdown, and printing opens closed sections.
    const exportIds = async () => view.evaluate(() => [...document.querySelectorAll(".export-bar .export-actions > *")].map((node) => node.id).join(","));
    for (const hash of ["#/cs/V/path/start", "#/cs/V/explorer", "#/cs/V/page/about", "#/cs/V/tools", "#/cs/V/check"]) {
      await view.goto(pageUrl + hash);
      await view.waitForSelector("#main h1");
      if ((await exportIds()) !== "export-print,export-crate") fail(`exports: ${hash} does not offer printing and the crate: ${await exportIds()}`);
    }
    await view.goto(pageUrl + "#/cs/V/check/dataset");
    await view.waitForSelector("#main h1");
    if (await view.locator(".export-bar").count()) fail("exports: a single check shows the shared export bar beside its own exports");
    const saved = async (id) => {
      const [download] = await Promise.all([view.waitForEvent("download"), view.locator("#export-" + id).click()]);
      return { name: download.suggestedFilename(), text: readFileSync(await download.path(), "utf8") };
    };
    await open("#/en/V/catalogue/k!resources~s!licence");
    const listed = await found();
    const csv = await saved("csv");
    const csvRows = csv.text.replace(/^\ufeff/, "").trim().split("\r\n");
    if (!/^fair-guide-catalogue-resources-\d{4}-\d{2}-\d{2}\.csv$/.test(csv.name) || !csvRows[0].startsWith("Identifier,Name,") || !csvRows[0].includes("Address") || !csvRows[0].includes("Status")) fail("exports: the CSV is not named or headed as expected: " + csv.name + " " + csvRows[0]);
    if (csvRows.length - 1 !== listed || !csvRows.slice(1).every((row) => row.includes("https://"))) fail(`exports: the CSV does not hold exactly the ${listed} filtered entries with their addresses (${csvRows.length - 1} rows)`);
    const json = JSON.parse((await saved("json")).text);
    if (json.count !== listed || json.items.length !== listed || !json.url.includes("s!licence") || !json.items.every((item) => item.entry.includes("/catalogue/resources/"))) fail("exports: the JSON list does not match the filtered list or name its filters");
    await view.goto(pageUrl + "#/en/DS/path/licence");
    await view.waitForSelector("#main h1");
    const markdown = await saved("markdown");
    if (!markdown.name.startsWith("fair-guide-station-licence-DS-en-") || !markdown.text.startsWith("# Licence and access") || !markdown.text.includes("\n## How to do it\n") || !markdown.text.includes("#/en/DS/path/licence")) fail("exports: the station's Markdown lacks its title, levels or address: " + markdown.name);
    if (/\n\n\n/.test(markdown.text)) fail("exports: the station's Markdown has empty runs of lines");
    const closed = await view.locator("#main details:not([open])").count();
    await view.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
    if (!closed || (await view.locator("#main details:not([open])").count())) fail("exports: printing does not open the closed sections");
    await view.evaluate(() => window.dispatchEvent(new Event("afterprint")));
    if ((await view.locator("#main details:not([open])").count()) !== closed) fail("exports: the sections opened for printing do not close again");

    await view.goto(pageUrl + "#/cs/V/page/machines");
    await view.waitForSelector("#main h1");
    if ((await current()) !== "Katalog") fail("machines: the page does not sit under the catalogue");
    if (!(await view.locator('.machine-links a[href="ro-crate-metadata.json"]').count())) fail("machines: the page does not link the knowledge base");
    if (!(await view.locator('head link[rel="describedby"][href="ro-crate-metadata.json"]').count())) fail("machines: the head does not carry the describedby link");
    await view.close();
  }

  // Requirement identifiers resolve to the catalogue: a cited requirement shows its text, then its identifier as a chip
  // that leads to the catalogue entry, which is brought into view and marked, also when opened directly; the
  // catalogue lists the requirements by source, with a kind filter, and the check questions with their basis.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await view.goto(pageUrl + "#/cs/V/path/licence");
    await view.waitForSelector(".station");
    await view.locator('details[data-key="L2"] summary').click();
    const entries = await view.locator('details[data-key="L2"] ul.clauses > li').count();
    const chips = await view.locator('details[data-key="L2"] ul.clauses > li a.id-chip').count();
    if (!entries || chips < entries - 1) fail(`ids: the cited requirements do not carry linked identifiers (${chips} of ${entries})`);
    if (await view.locator('details[data-key="L2"] ul.clauses > li > .clause-text .id-chip').count()) fail("ids: an identifier leads the requirement's text instead of following it");
    const chip = view.locator('details[data-key="L2"] ul.clauses a.id-chip').first();
    const id = (await chip.textContent()).trim();
    await chip.click();
    await view.waitForSelector(".catalogue-layout");
    await view.waitForFunction((expected) => document.activeElement && document.activeElement.id === "item-" + expected, id);
    if (!(await view.evaluate(() => document.activeElement.classList.contains("jumped")))) fail("ids: the catalogue entry is not marked when the identifier is followed");
    if (!(await view.locator("#facet-kind-clauses").isChecked())) fail("ids: the identifier does not select the requirements");
    await view.goto("about:blank");
    await view.goto(pageUrl + "#/cs/V/catalogue/clauses/A.F1.N1");
    await view.waitForSelector('[id="item-A.F1.N1"]');
    const box = await view.locator('[id="item-A.F1.N1"]').boundingBox();
    if (!box || box.y < 0 || box.y > 900) fail("ids: a directly opened link to a requirement does not bring it into view");
    const all = await view.locator(".clause-card").count();
    await view.locator("#facet-clauses-ckind-recommendation").check();
    await view.waitForFunction(() => location.hash.includes("f.ckind!recommendation"));
    const recommendations = await view.locator(".clause-card").count();
    if (!(recommendations > 0 && recommendations < all)) fail("ids: the kind filter does not narrow the requirements");
    await view.goto(pageUrl + "#/cs/V/catalogue/questions/S18");
    await view.waitForSelector("#item-S18");
    if (!(await view.locator("#item-S18 a.id-chip").count())) fail("ids: a check question does not link the requirements it rests on");
    await view.close();
  }

  // Every page sits under a menu item: the tools view lists the helpers and the AI page, and its item stays current
  // on each of them; the about item covers the about page and the accessibility statement.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const current = async () => (await view.locator('.main-nav [aria-current="page"]').textContent()).trim();
    await view.goto(pageUrl + "#/cs/V/tools");
    await view.waitForSelector(".tool-cards");
    if ((await current()) !== "Nástroje") fail("tools: the menu does not mark the tools item on the tools view");
    const tools = await view.locator(".tool-card h2 a").evaluateAll((links) => links.map((link) => link.getAttribute("href").split("/").pop()));
    if (tools.join(",") !== "live-check,identifiers,citation,ai") fail("tools: the tools view does not list the tool pages in order: " + tools.join(","));
    if ((await view.locator(".tool-coming").count()) !== 3) fail("tools: the helpers in preparation are not marked as such");
    for (const [id, item] of [["identifiers", "Nástroje"], ["ai", "Nástroje"], ["live-check", "Nástroje"], ["citation", "Nástroje"], ["about", "O průvodci"], ["accessibility", "O průvodci"]]) {
      await view.goto(pageUrl + "#/cs/V/page/" + id);
      await view.waitForSelector("#main h1");
      if ((await current()) !== item) fail(`page ${id}: the menu does not mark ${item}`);
    }
    await view.close();
  }

  // Repositories: FAIRsharing records are loaded on request, link from each repository they describe, and the
  // repository names FAIRsharing among its sources.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await view.goto(pageUrl + "#/cs/V/repositories");
    await view.waitForSelector("#fairsharing-load");
    if (await view.locator(".fairsharing-record").count()) fail("repositories: FAIRsharing records show before they are loaded");
    const asked = await view.evaluate(async () => {
      const seen = [];
      window.FairGuide.live.findFairsharing = async (repositories) => {
        seen.push(...repositories);
        return [{ doi: "10.25504/FAIRsharing.f4bfb1", name: "Czech Social Science Data Archive", re3data: "r3d100010484", addresses: [] }];
      };
      document.getElementById("fairsharing-load").click();
      await new Promise((done) => setTimeout(done, 300));
      return seen.filter((repository) => (repository.identifiers || []).length).length;
    });
    if (!asked) fail("repositories: the FAIRsharing lookup is not given the repositories' re3data records");
    const card = view.locator(".card", { has: view.locator(".fairsharing-record") });
    if ((await card.count()) !== 1 || !(await card.textContent()).includes("FAIRsharing")) fail("repositories: the FAIRsharing record does not show on its repository");
    if ((await card.locator(".fairsharing-record").getAttribute("href")) !== "https://doi.org/10.25504/FAIRsharing.f4bfb1") fail("repositories: the FAIRsharing link does not lead to the record's DOI");
    if (!(await view.locator("#fairsharing-status").textContent()).includes("1 z")) fail("repositories: the FAIRsharing status does not say how many were found");
    const buttons = await view.locator(".filter-actions button").evaluateAll((all) => all.map((button) => Math.round(button.getBoundingClientRect().top)));
    if (new Set(buttons).size !== 1) fail("repositories: the live-source buttons are not aligned: " + buttons.join(", "));
    await view.close();
  }

  // Visual rules from the visual pass: cards keep even padding; the explorer shows an overview before a principle is
  // chosen; a helper page says when its helper is not there yet; on a phone the language switch shares the logo's row.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await view.goto(pageUrl + "#/cs/V/resources");
    await view.waitForSelector(".cards .card");
    const gap = await view.locator(".cards .card").first().evaluate((card) => {
      const last = card.lastElementChild.getBoundingClientRect();
      const box = card.getBoundingClientRect();
      return { bottom: Math.round(box.bottom - last.bottom), top: Math.round(card.firstElementChild.getBoundingClientRect().top - box.top) };
    });
    if (Math.abs(gap.bottom - gap.top) > 4) fail("cards: the space below the content differs from the space above it: " + JSON.stringify(gap));
    await view.goto(pageUrl + "#/cs/V/explorer");
    await view.waitForSelector("#main h1");
    const rows = await view.locator(".explorer-overview tbody tr").count();
    const caption = await view.locator(".explorer-overview caption").textContent().catch(() => "");
    if (rows !== 4 || !/^\d+ požadav/.test(caption)) fail("explorer: no overview of the requirements before a principle is chosen: " + caption);
    for (const [id, expected] of [["identifiers", true], ["citation", true], ["live-check", true], ["about", false]]) {
      await view.goto(pageUrl + "#/cs/V/page/" + id);
      await view.waitForSelector("#main h1");
      const coming = await view.locator(".helper-coming").count();
      if (Boolean(coming) !== expected) fail(`page ${id}: the note that the helper is coming is ${coming ? "shown" : "missing"}`);
    }
    await view.setViewportSize({ width: 390, height: 800 });
    await view.goto(pageUrl + "#/cs/V/page/about");
    await view.waitForSelector("#main h1");
    const logo = await view.locator(".brand > a").first().boundingBox();
    const language = await view.locator(".site-header .controls .button").boundingBox();
    if (language.y > logo.y + logo.height) fail("header: on a phone the language switch takes a row of its own");
    await view.close();
  }

  // Keyboard: the skip link, lens picker, language switch, search and stage cards are reachable with Tab.
  const reached = new Set();
  for (let i = 0; i < 30; i += 1) {
    await page.keyboard.press("Tab");
    reached.add(await page.evaluate(() => {
      const el = document.activeElement;
      return el ? (el.id || el.className || el.tagName) + ":" + (el.textContent || "").trim().slice(0, 40) : "";
    }));
  }
  const joined = [...reached].join(" | ");
  for (const expected of ["skip-link", "lens-option", "English", "search-input", "Připravuji projekt"]) {
    if (!joined.includes(expected)) fail("keyboard does not reach: " + expected);
  }

  // Universal search: terms are found locally while typing, in both languages and without diacritics, and hand
  // over to the catalogue; identifiers are routed by what they denote once the search is confirmed, the guide's own
  // identifiers while typing; nothing is sent while searching.
  const typeQuery = async (text) => {
    await page.fill("#search-input", "");
    await page.locator("#search-input").pressSequentially(text);
    await page.waitForFunction((query) => document.querySelector("#search-results").dataset.query === query, text);
    return page.locator("#search-results").textContent();
  };
  const search = async (text) => {
    await page.fill("#search-input", text);
    await page.locator("#search-input").press("Enter");
    await page.waitForFunction((query) => document.querySelector("#search-results").dataset.confirmed === "true" && document.querySelector("#search-results").dataset.query === query, text);
    return page.locator("#search-results").textContent();
  };
  let found = await typeQuery("licence");
  if (!found.includes("Licence a přístup") || !found.includes("R1.1")) fail("search: 'licence' does not find the licence step and R1.1: " + found.slice(0, 200));
  const firstGroup = page.locator("#search-results .results-list").first();
  if ((await firstGroup.locator("li").count()) !== 3) fail("search: a long result group is not shortened to three");
  await page.locator("#search-results .button-link").first().click();
  if ((await firstGroup.locator("li").count()) <= 3) fail("search: 'show all' does not reveal the rest of the group");
  if (!(await page.evaluate(() => document.activeElement.closest(".results-list li:nth-child(4)")))) fail("search: focus does not move to the first revealed result");
  found = await typeQuery("pristup");
  if (!found.includes("Licence a přístup")) fail("search: matching does not ignore diacritics");
  found = await typeQuery("persistent identifier");
  if (found.includes("Nic nenalezeno")) fail("search: English words are not searched");
  found = await typeQuery("https://doi.org/10.5281/zenodo.21726258");
  if (!found.includes("Stiskněte Enter") || (await page.locator("#search-results .result").count())) fail("search: a typed DOI does not wait for Enter: " + found.slice(0, 200));
  found = await search("https://doi.org/10.5281/zenodo.21726258");
  const primary = async () => (await page.locator("#search-results .result-primary").textContent()).trim();
  if (!(await primary()).includes("Zjistit, co to je") || !found.includes("Zkontrolovat datovou sadu")) fail("search: a DOI does not offer to find out what it is, with the dataset check beside it");
  found = await search("0000-0001-6592-6291");
  if (!found.includes("Ověřit identifikátor")) fail("search: an ORCID iD is not routed to the identifier helper");
  found = await search("r3d100010386");
  if (!(await primary()).includes("Zkontrolovat zralost repozitáře")) fail("search: a re3data identifier is not routed to the maturity check: " + found.slice(0, 200));
  found = await search("https://ror.org/04wxdxa47");
  if (!(await primary()).includes("Instituce a správa dat") || !found.includes("Ověřit identifikátor")) fail("search: a ROR ID is not routed to the institution check, with verification beside it");
  found = await typeQuery("A.F1.N1");
  if (!(await page.locator("#search-results .result-primary").getAttribute("href")).endsWith("/catalogue/clauses/A.F1.N1")) fail("search: a requirement identifier does not lead to its catalogue entry while typing");
  found = await typeQuery("licence");
  if (!(await page.locator(".catalogue-handoff a").getAttribute("href")).includes("q!licence")) fail("search: text results do not hand over to the catalogue");
  // The language changes in place; the search then shows titles in English and links into the English guide.
  await page.evaluate(() => { location.hash = "#/en/V/path/start"; });
  await page.waitForFunction(() => document.documentElement.lang === "en" && document.querySelector("#search-input"));
  found = await typeQuery("autho");
  if (!found.includes("Authentication and authorisation") || /Ověřování|umožní/.test(found)) fail("search: after switching to English the results keep Czech titles: " + found.slice(0, 200));
  if (!(await page.locator("#search-results a.result").first().getAttribute("href")).startsWith("#/en/")) fail("search: after switching to English the results link into the Czech guide");
  await page.evaluate(() => { location.hash = "#/cs/V/path/start"; });
  await page.waitForFunction(() => document.documentElement.lang === "cs" && document.querySelector("#search-input"));
  await axe(page, "landing with search results");
  if (external.length) fail("search: requests while searching: " + external.join(", "));

  // Finding out what a DOI is: the registration agency and, for DataCite, the type (both replaced here) lead to
  // the dataset check or to the citation, and say where the answer came from.
  await page.evaluate(() => {
    const live = window.FairGuide.live;
    live.doiAgency = async (doi) => (doi.startsWith("10.1038/") ? "Crossref" : "DataCite");
    live.datacite = async () => ({ types: { resourceTypeGeneral: "Dataset" }, titles: [{ title: "Test data" }], publisher: { name: "Zenodo" }, publicationYear: 2026 });
  });
  const findOut = async (pid) => {
    await search(pid);
    await page.locator("#search-results .result-primary").click();
    await page.waitForFunction(() => document.querySelector("#search-results .search-basis strong"));
    return page.locator("#search-results .search-basis").textContent();
  };
  let said = await findOut("10.5281/zenodo.21726258");
  if (!said.includes("Jde o datovou sadu") || !said.includes("DataCite") || !(await primary()).includes("Zkontrolovat datovou sadu")) fail("search: a DataCite dataset does not lead to the dataset check: " + said);
  if (!(await page.evaluate(() => document.activeElement && document.activeElement.classList.contains("result-primary")))) fail("search: focus does not move to the route found");
  if (!(await page.locator("#search-results").textContent()).includes("Dotázali jsme se: doi.org, DataCite")) fail("search: after a lookup the note does not say which services were asked");
  said = await findOut("10.1038/sdata.2016.18");
  if (!said.includes("Jde o publikaci") || !(await primary()).includes("Vytvořit citaci")) fail("search: a Crossref DOI does not lead to the citation: " + said);

  // A re3data identifier opens the maturity check filled in from the snapshot.
  await page.evaluate(() => { window.FairGuide.live.findFairsharing = async () => []; });
  await search("r3d100010386");
  await page.locator("#search-results .result-primary").click();
  await page.waitForFunction(() => location.hash.endsWith("/check/maturity") && document.getElementById("prefill-status") && document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await page.locator(".target-card").textContent()).includes("LINDAT")) fail("search: the maturity check from a re3data identifier does not say which repository it is");
  await page.goto(pageUrl);
  await rendered(page);

  // Task shortcuts change with the lens, chosen in the band under the main menu.
  if ((await page.locator(".lens-band .lens-option").count()) !== 4) fail("lens band: four options are not shown on the landing");
  if ((await page.locator('.lens-option[aria-current="true"]').getAttribute("data-lens")) !== "V") fail("lens band: the current lens is not marked");
  if ((await page.locator('.lens-option[data-lens="SR"]').getAttribute("href")) !== "#/cs/SR/path/start") fail("lens band: an option is not a shareable link");
  await page.locator('.lens-option[data-lens="SR"]').click();
  await lensShown(page, "SR");
  if (!(await page.locator(".tasks").textContent()).includes("Podmínky NRP")) fail("landing: the repository administrator's tasks are missing");
  await context.close();
}

// 2. Every station in every lens and language, then the other views.
{
  const { context, page, external, problems } = await openPage();
  await page.goto(pageUrl);
  await rendered(page);
  const views = [];
  for (const lang of ["cs", "en"]) {
    for (const lens of lenses) for (const station of stations) views.push(`#/${lang}/${lens}/path/${station}`);
    for (const view of ["explorer", "resources", "repositories", "tools", "selfcheck"]) views.push(`#/${lang}/V/${view}`);
    for (const tab of ["sources", "terms", "fips", "tests", "actions"]) views.push(`#/${lang}/V/catalogue/${tab}`);
    for (const check of checks) views.push(`#/${lang}/${check.lens}/check/${check.id}`);
    for (const principle of principles.slice(0, 3)) views.push(`#/${lang}/K/explorer/${principle}`);
    for (const id of pages) views.push(`#/${lang}/V/page/${id}`);
  }
  for (const hash of views) {
    await page.evaluate((value) => { window.location.hash = value; }, hash);
    await page.waitForFunction((value) => window.location.hash === value && document.querySelector("#main h1"), hash);
    const headingText = (await page.textContent("#main h1")).trim();
    if (!headingText) fail(`${hash}: the main heading is empty`);
    const lang = await page.evaluate(() => document.documentElement.lang);
    if (lang !== hash.split("/")[1]) fail(`${hash}: html lang is ${lang}`);
    if (hash.includes("/path/")) {
      const now = await page.locator(".now").count();
      if (!now) fail(`${hash}: no L0 block`);
    }
    await axe(page, hash);
    // The page shell holds elements only; a view part that is absent leaves no stray text.
    if (await page.evaluate(() => [...document.getElementById("app").childNodes].some((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim()))) fail(`${hash}: stray text in the page shell`);
    // No value reaches the page unformatted.
    if (/\[object Object\]|\bundefined\b/.test(await page.locator("#app").innerText())) fail(`${hash}: an unformatted value is shown`);
    // Every external link opens in a new tab.
    const sameTab = await page.evaluate(() => [...document.querySelectorAll('a[href^="http"]')].filter((link) => link.target !== "_blank" || !/noopener/.test(link.rel)).map((link) => link.href));
    if (sameTab.length) fail(`${hash}: external links that do not open in a new tab: ${[...new Set(sameTab)].slice(0, 5).join(", ")}`);
  }
  if (external.length) fail("requests while navigating: " + external.join(", "));
  for (const problem of problems) fail("navigation: " + problem);
  console.log(`checked ${views.length} views`);
  await context.close();
}

// 3. Reflow at 320 CSS pixels: no horizontal scrolling.
{
  const { context, page } = await openPage({ width: 320, height: 800 });
  for (const hash of ["#/cs/SR/path/publikace", "#/en/DS/resources", "#/cs/K/explorer/F1"]) {
    await page.goto(pageUrl + hash);
    await rendered(page);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (overflow > 1) fail(`${hash}: horizontal scroll of ${overflow}px at 320 px`);
  }
  await context.close();
}

// 4. Embedded in an iframe.
{
  const host = resolve(root, ".cache", "iframe-host.html");
  mkdirSync(dirname(host), { recursive: true });
  writeFileSync(host, `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Host</title></head><body><iframe title="FAIR guide" src="${pageUrl}#/cs/V/path/repozitar" style="width:100%;height:800px"></iframe></body></html>`);
  const { context, page } = await openPage();
  await page.goto(pathToFileURL(host).href);
  const frame = page.frameLocator("iframe");
  await frame.locator("#main h1").waitFor();
  const heading = await frame.locator("#main h1").textContent();
  if (!heading.includes("Repozitář")) fail("iframe: unexpected heading " + heading);
  await frame.getByRole("link", { name: /Další krok/ }).click();
  try {
    await frame.locator("#main h1", { hasText: "Popis" }).waitFor({ timeout: 5000 });
  } catch (error) {
    fail("iframe: navigation inside the frame failed: " + (await frame.locator("#main h1").textContent()));
  }
  await context.close();
}

// 5. Self-check without network: modes and profiles, answers, tiers, gaps on the path, the FIP Dashboard
//    snapshot pre-fill, a shared link and the exports. Nothing may leave the browser.
{
  const { context, page, external, problems } = await openPage();
  const go = async (hash) => {
    await page.evaluate((value) => { window.location.hash = value; }, hash);
    await page.waitForFunction((value) => window.location.hash === value && document.querySelector("#main h1"), hash);
  };
  const checked = (id) => page.locator("#" + id).isChecked();
  await page.goto(pageUrl);
  await rendered(page);

  // Dataset check: the mode comes first, the first view shows the Minimum items only.
  await go("#/cs/V/check/dataset");
  if (!(await page.locator(".notice", { hasText: "Nejdřív odpovězte" }).count())) fail("dataset check: no prompt to choose the mode first");
  await page.locator("#mode-after").check();
  if (await page.locator("#item-D06").count()) fail("dataset check: a Recommended item shows in the first view");
  if (/Krok \d/.test(await page.locator(".item-group h2").first().textContent())) fail("dataset check: group headings imitate the path's step numbering");
  if (!(await page.locator("#item-D04").count())) fail("dataset check: Minimum item D04 is missing after publication");
  if (await page.locator("#item-P01").count()) fail("dataset check: a before-publication item shows after publication");
  await page.locator("#answer-D04-no").check();
  await page.locator("#answer-D05-unknown").check();
  await page.locator("#answer-D01-yes").check();
  const gaps = await page.locator(".gaps").first().textContent();
  if (!gaps.includes("D04") || !gaps.includes("Licence") || !gaps.includes("správce repozitáře")) fail("dataset check: the D04 gap lacks where to fix it or who fixes it: " + gaps);
  const gapLink = await page.locator(".gaps a", { hasText: "Licence" }).first().getAttribute("href");
  if (gapLink !== "#/cs/V/path/licence") fail("dataset check: the gap links to " + gapLink);
  const tasks = await page.locator(".gaps").nth(1).textContent();
  if (!tasks.includes("D05") || !tasks.includes("data steward")) fail("dataset check: the don't-know task does not say whom to ask: " + tasks);
  if (!(await page.locator(".gaps").nth(1).locator('a[href^="https://nma.eosc.cz"]').count())) fail("dataset check: the don't-know task has no NMA search link");
  const resultText = await page.locator("#results").textContent();
  if (/%|skóre|score/i.test(resultText)) fail("dataset check: the result shows a score or percentage");
  await axe(page, "dataset check answered");
  await page.locator('label[for="extended-toggle"]').click();
  if (!(await page.locator("#item-D06").count())) fail("dataset check: the extended check does not show Recommended items");
  if (!(await page.locator("#extended-toggle").isChecked()) || (await page.locator("#extended-toggle").getAttribute("role")) !== "switch") fail("dataset check: the extended check is not an on/off switch that shows its state");
  if (!(await panelFits(page))) fail("dataset check: the result so far scrolls or is too tall in the extended check");
  if (!(await checked("answer-D04-no"))) fail("dataset check: opening the extended check lost an answer");
  await page.locator('label[for="extended-toggle"]').click();

  // The first view says what its tier means; items are grouped by FAIR principle, can be grouped by path step, and
  // each names the step where it is addressed.
  const tierInfo = await page.locator(".tier-info").textContent();
  if (!tierInfo.includes("Minimum (") || !tierInfo.includes("Národní datové infrastruktury")) fail("dataset check: the first view does not explain its tier: " + tierInfo);
  const minimumCount = (tierInfo.match(/Minimum \((\d+) /) || [])[1];
  if (!(await page.locator("#results p").first().textContent()).endsWith("z " + minimumCount)) fail("dataset check: the result counts items the first view does not show");
  if (!(await page.locator(".item-group h2").first().textContent()).includes("Dohledatelnost")) fail("dataset check: items are not grouped by FAIR principle by default");
  if (!(await page.locator("#item-D04 .fix-at").textContent()).includes("Licence")) fail("dataset check: an item does not name the step where it is addressed");
  // The summary mirrors the questions: one chip per question in view, in the list's groups.
  const listed = await page.locator(".items fieldset.item").evaluateAll((items) => items.map((item) => item.id.replace("item-", "")));
  const chips = await page.locator(".summary-chip").evaluateAll((buttons) => buttons.map((button) => button.textContent.match(/[A-Z]\d{2}/)[0]));
  if (listed.join(" ") !== chips.join(" ")) fail(`dataset check: the summary does not mirror the questions (${chips.join(" ")} vs ${listed.join(" ")})`);
  await page.locator("#grouping-steps").check();
  const stepHeading = page.locator(".item-group h2").first();
  if ((await stepHeading.locator("svg").count()) !== 1 || /Krok \d/.test(await stepHeading.textContent())) fail("dataset check: grouping by path step does not show the step's icon and name");
  if ((await page.locator(".summary-group").count()) !== (await page.locator(".item-group").count())) fail("dataset check: the summary does not follow the grouping by path step");
  if ((await page.locator(".result-group").count()) !== (await page.locator(".item-group").count())) fail("dataset check: the full result does not follow the grouping by path step");
  if ((await page.locator(".summary-group-label .group-icon").count()) !== (await page.locator(".summary-group").count())) fail("dataset check: path steps in the summary lack their icons");
  await page.locator("#grouping-principles").check();

  // At the top of the page the summary's box starts level with the first box of the questions.
  await page.evaluate(() => window.scrollTo(0, 0));
  const firstBox = await page.locator(".check-main .choice").first().boundingBox();
  const summaryBox = await page.locator(".check-summary").boundingBox();
  if (Math.abs(firstBox.y - summaryBox.y) > 2) fail(`dataset check: the summary starts ${Math.round(summaryBox.y - firstBox.y)}px off the first box`);
  /* A legend drawn on the border would put the visible top line below the box's top edge. */
  const legendInside = await page.locator(".check-main .choice").first().evaluate((box) => box.querySelector("legend").getBoundingClientRect().top > box.getBoundingClientRect().top + 1);
  if (!legendInside) fail("dataset check: the first box's visible top line is not level with the summary");

  // The result stands beside the questions and shows the licence gap at once; it can be collapsed, and the choice
  // survives a reload.
  const mainBox = await page.locator(".check-main").boundingBox();
  const resultBox = await page.locator(".check-summary").boundingBox();
  if (!(resultBox.x > mainBox.x + mainBox.width / 2)) fail("dataset check: the result is not beside the questions");
  await page.locator("#item-D04").scrollIntoViewIfNeeded();
  const gapCell = page.locator('.summary-chip[data-state="gap"]', { hasText: "D04" });
  const gapBox = await gapCell.boundingBox();
  if (!gapBox || gapBox.y < 0 || gapBox.y + gapBox.height > (await page.evaluate(() => window.innerHeight))) fail("dataset check: the R1.1 gap is not in view beside the item");
  // On a wide screen the check's controls sit in the summary, at hand while scrolling.
  if (!(await page.locator(".check-summary #extended-toggle").count()) || !(await page.locator(".check-summary #grouping-steps").count())) fail("dataset check: the extended switch and the grouping are not in the summary on a wide screen");
  // The chips and counts of the result so far lead to the items and to the full result.
  await gapCell.click();
  if (!(await page.evaluate(() => document.activeElement.closest("#item-D04")))) fail("dataset check: a principle chip does not lead to its item");
  await page.locator('.summary-count[data-kind="gaps"]').click();
  if (!(await page.evaluate(() => document.activeElement.id === "results-gaps"))) fail("dataset check: the gap count does not lead to the gaps in the full result");
  // A chip whose item the short view hides opens the extended view and lands on the item.
  await page.locator('label[for="extended-toggle"]').click();
  await page.locator("#answer-D08-no").check();
  await page.locator('label[for="extended-toggle"]').click();
  await page.locator(".summary-chip", { hasText: "D08" }).click();
  if (!(await page.locator("#extended-toggle").isChecked()) || !(await page.evaluate(() => document.activeElement.closest("#item-D08")))) fail("dataset check: a chip for a hidden item does not open the extended view at the item");
  await page.locator('label[for="extended-toggle"]').click();
  // The collapse control stays exactly where it was.
  await page.locator("#item-D04").scrollIntoViewIfNeeded();
  const toggleBefore = await page.locator("#result-toggle").boundingBox();
  await page.locator("#result-toggle").click();
  if (!(await page.locator("#result-body").isHidden())) fail("dataset check: the result panel does not collapse");
  const toggleAfter = await page.locator("#result-toggle").boundingBox();
  if (!(await page.locator(".check-main #extended-toggle").count())) fail("dataset check: with the summary collapsed, the controls are not above the questions");
  if (Math.abs(toggleBefore.x - toggleAfter.x) > 1 || Math.abs(toggleBefore.y - toggleAfter.y) > 1) fail("dataset check: the collapse control moves when the panel collapses");
  if ((await page.locator("#result-toggle").boundingBox()).width > 48) fail("dataset check: the collapse control is not a small icon");
  await page.reload();
  await page.waitForSelector("#result-toggle");
  if (!(await page.locator("#result-body").isHidden())) fail("dataset check: the collapsed result panel is not remembered");
  else await page.locator("#result-toggle").click();
  if (!(await page.locator("#result-body").isVisible())) fail("dataset check: the result panel does not open again");

  // Evidence beside the criterion: the field and value found, the source, the date and a link to the record; the
  // same evidence is in the Markdown summary. Clearing the identifier removes what it pre-filled and keeps the
  // user's own answers.
  await page.evaluate(() => {
    const FG = window.FairGuide;
    const st = FG.state.answers.dataset;
    st.pid = "10.5281/zenodo.1";
    st.target = "https://doi.org/10.5281/zenodo.1";
    st.targetInfo = { name: "Sample dataset", creators: "Novak, D. a kol.", publisher: "Zenodo", year: "2026", kind: "Dataset" };
    st.items.D02 = {
      value: "yes",
      origin: "prefill",
      prefill: { source: "resolver", date: "2026-10-08", value: "yes", notes: [], list: [], fields: [{ path: "url", values: ["https://repo.example/record/1"], more: 0 }], record: "https://repo.example/record/1" },
    };
    FG.saveState();
    FG.rerender();
  });
  // A resolved identifier says what it is, under the field and in the result.
  const card = await page.locator(".target-card").textContent();
  if (!card.includes("Sample dataset") || !card.includes("Zenodo") || !card.includes("2026")) fail("dataset check: the resolved identifier does not say what it is: " + card);
  if (!(await page.locator(".result-headline").textContent()).includes("Kontrolujete: Sample dataset")) fail("dataset check: the result does not name what is checked");
  const evidence = await page.locator("#origin-D02").textContent();
  if (!evidence.includes("url") || !evidence.includes("https://repo.example/record/1") || !evidence.includes("8. 10. 2026")) fail("dataset check: the evidence beside D02 is incomplete: " + evidence);
  if ((await page.locator("#origin-D02 a").getAttribute("href")) !== "https://repo.example/record/1") fail("dataset check: the evidence does not link to its record");
  await page.locator("#export-format-md").check();
  await page.locator(".export-preview summary").click();
  await page.waitForFunction(() => document.getElementById("export-preview-text").value.length > 0);
  const doiSummary = await page.locator("#export-preview-text").inputValue();
  if (!doiSummary.includes("url = https://repo.example/record/1")) fail("dataset check: the Markdown summary lacks the evidence");
  await page.locator("#export-format-jsonld").check();
  if (!(await page.locator("#export-preview-text").inputValue()).includes('"guideState"')) fail("dataset check: the preview does not follow the chosen format");
  await page.locator(".export-preview summary").click();
  await page.locator("#export-format-md").check();
  // Your answers read as a list: the answer beside each question, and the evidence under it.
  const answerRow = await page.locator(".answers-list .answer-row").filter({ hasText: "D02" }).textContent();
  if (!answerRow.includes("Ano") || !answerRow.includes("url = https://repo.example/record/1") || !answerRow.includes("záznam")) fail("dataset check: the answers list lacks the answer or its evidence: " + answerRow);
  // The summary loads back with the DOI in its field, what it is, and the evidence.
  {
    const saved = resolve(root, ".cache", "doi-summary.md");
    writeFileSync(saved, doiSummary);
    await page.evaluate(() => {
      window.FairGuide.state.answers.dataset = { mode: "before", items: {} };
      window.FairGuide.saveState();
      window.FairGuide.rerender();
    });
    await page.locator("#load-file").setInputFiles(saved);
    await page.waitForSelector(".notice.shared");
    await page.getByRole("button", { name: "Použít odpovědi ze souboru" }).click();
    await page.waitForSelector("#prefill-pid");
    if ((await page.locator("#prefill-pid").inputValue()) !== "10.5281/zenodo.1") fail("load: the DOI is not back in its field after loading the summary");
    const restoredCard = page.locator(".target-card");
    if (!(await restoredCard.count()) || !(await restoredCard.textContent()).includes("Sample dataset")) fail("load: what the DOI is does not show after loading the summary");
    if (!(await page.locator("#origin-D02").textContent()).includes("https://repo.example/record/1")) fail("load: the evidence behind D02 is lost after loading the summary");
  }
  await page.locator("#prefill-pid-clear").click();
  if (await page.locator('input[name="answer-D02"]:checked').count()) fail("dataset check: clearing the identifier kept the answer it pre-filled");
  if (!(await checked("answer-D01-yes")) || !(await checked("answer-D04-no"))) fail("dataset check: clearing the identifier removed the user's own answers");
  if (await page.locator("#prefill-pid").inputValue()) fail("dataset check: clearing did not empty the identifier field");
  if (await page.locator(".target-card").count()) fail("dataset check: clearing the identifier kept its description");

  // The path marks the stations with open items.
  await go("#/cs/V/path/licence");
  if (!(await page.locator('.rail-desktop a[href="#/cs/V/path/licence"] .gap-mark').count())) fail("path: the licence station has no gap mark");
  const tileOrder = await page.locator(".station-header .principle-tile").evaluateAll((tiles) => tiles.map((tile) => tile.textContent.trim().split(" ")[0]));
  if (tileOrder.join(" ") !== "A1.2 R1.1") fail("path: the station's principles are not in F, A, I, R order: " + tileOrder.join(" "));
  const legend = page.locator(".rail-desktop .rail-legend a");
  if (!(await legend.count()) || (await legend.getAttribute("href")) !== "#/cs/V/selfcheck") fail("path: the self-check marks have no visible legend linking to the self-check");

  // Until the visitor chooses a stage, no stage is shown as chosen, on the path or on the landing.
  if (!(await page.locator(".stage-switch summary").textContent()).includes("zatím nevybraná")) fail("path: the stage switch claims a stage before one was chosen");
  await go("#/cs/V/path/start");
  if (await page.locator(".stage-current").count()) fail("landing: a stage is marked although none was chosen");

  // The stage can be changed on the path itself; the choice opens the stage's first station.
  await go("#/cs/V/path/licence");
  await page.locator(".stage-switch summary").click();
  await page.locator(".stage-switch button", { hasText: "Chci data zveřejnit" }).click();
  try {
    await page.waitForFunction(() => window.location.hash === "#/cs/V/path/repozitar" && document.querySelector(".stage-switch summary").textContent.includes("Chci data zveřejnit"), null, { timeout: 5000 });
  } catch (error) {
    fail("path: choosing a stage does not open its first station and show the choice");
  }
  if ((await page.locator('.stage-switch button[aria-pressed="true"]').count()) !== 1) fail("path: the chosen stage is not pressed in the stage switch");
  await go("#/cs/V/path/licence");

  // The menu's path item opens the station the visitor was last at; the home item opens the path's start, with a
  // line to resume where they were.
  if ((await page.locator(".main-nav a", { hasText: "Cesta k FAIR" }).getAttribute("href")) !== "#/cs/V/path/licence") fail("menu: the path item does not open the last station");
  if ((await page.locator('.main-nav a[aria-current="page"]').textContent()) !== "Cesta k FAIR") fail("menu: the path item is not marked on a station");
  await page.locator(".main-nav a", { hasText: "Úvod" }).click();
  try {
    await page.waitForFunction(() => window.location.hash === "#/cs/V/path/start" && document.querySelector("#stage-question") && document.querySelector("#stage-question").textContent.includes("Kde se právě nacházíte"), null, { timeout: 5000 });
  } catch (error) {
    fail("menu: the home item does not open the stage question");
  }
  if ((await page.locator('.main-nav a[aria-current="page"]').textContent()) !== "Úvod") fail("menu: the home item is not marked on the landing");
  if (!(await page.locator(".resume a").textContent()).includes("Licence")) fail("path: no resume line for the last station");
  const current = await page.locator(".stage-current").allTextContents();
  if (current.length !== 1 || !current[0].includes("Kroky 3–6") || !current[0].includes("Vybráno ")) fail("landing: the chosen stage is not marked with the last visit: " + current.join(" | "));

  // Switching the lens keeps open levels and the scroll position.
  await go("#/cs/V/path/licence");
  await page.locator(".station details summary").first().click();
  await page.evaluate(() => window.scrollTo(0, 400));
  const before = await page.evaluate(() => window.scrollY);
  // Click where the option is, as a user does: Playwright's locator click scrolls a sticky element to its place in
  // the flow first, which a real click does not.
  const option = await page.locator('.lens-option[data-lens="SR"]').boundingBox();
  await page.mouse.click(option.x + option.width / 2, option.y + option.height / 2);
  await lensShown(page, "SR");
  if ((await page.evaluate(() => window.location.hash)) !== "#/cs/SR/path/licence") fail("lens switch: the station changed");
  if ((await page.evaluate(() => document.activeElement.dataset.lens)) !== "SR") fail("lens switch: focus does not stay on the chosen lens");
  if (!(await page.locator(".station details[open]").count())) fail("lens switch: the open level closed");
  const after = await page.evaluate(() => window.scrollY);
  if (Math.abs(after - before) > 40) fail(`lens switch: the page scrolled from ${before} to ${after}`);

  // A station reads how, why, AI, then sources; its glossary terms come before the callouts and the resources; a
  // callout stays closed until the reader opens it.
  {
    const view = await browser.newPage();
    await view.goto(pageUrl + "#/cs/V/path/licence");
    await view.waitForSelector(".station");
    const keys = await view.locator(".station > details").evaluateAll((all) => all.map((part) => part.dataset.key));
    if (keys.join(",") !== "L1,L2,ai,L3") fail("station: the parts are not in the order how, why, AI, sources: " + keys.join(","));
    const at = await view.evaluate(() => {
      const parts = [...document.querySelector(".station").children];
      const index = (selector) => parts.findIndex((part) => part.matches(selector));
      return { terms: index(".station-terms"), callout: index(".callout"), resources: index("section:has(.cards)") };
    });
    if (!(at.terms >= 0 && at.terms < at.callout && at.callout < at.resources)) fail("station: the glossary terms are not above the callouts and resources: " + JSON.stringify(at));
    if (await view.locator(".callout details[open]").count()) fail("station: a callout is open before the reader opens it");
    await view.locator(".callout summary").first().click();
    if (!(await view.locator(".callout details[open] ol li").count())) fail("station: an opened callout shows no advice");
    await view.close();
  }

  // Credit: the station line names sources, not people, and opens the full detail; the footer credits the analysis
  // authors and cites the guide with its compiler as editor; the roles are listed on the about page.
  const provenance = await page.locator(".provenance-line").textContent();
  if (!provenance.includes("Analýzy FAIR") || /Novák|Trtíková/.test(provenance)) fail("station: the provenance line is not a sources-only line: " + provenance);
  await page.locator(".provenance-line button").click();
  if (!(await page.locator('details[data-key="L3"][open]').count())) fail("station: the provenance line does not open the sources and paradata");
  const history = await page.locator('details[data-key="L3"]').textContent();
  if (/Novák|Claude/.test(history) || !/obsah (vytvořen|upraven)/.test(history)) fail("station: the change history names people or tools, or lists no dated change");
  const basis = await page.locator(".site-footer p", { hasText: "Obsah vychází z" }).textContent();
  if (!basis.includes("Trtíková, I.") || !basis.includes("Čížek, T.") || !basis.includes("verze 1.2") || !basis.includes("doi.org/10.71495/5dv6-v116")) fail("footer: the analysis is not cited with its authors: " + basis);
  const guideCitation = await page.locator(".site-footer p", { hasText: "Jak citovat průvodce" }).textContent();
  if (!guideCitation.includes("Novák, D. (ed.)") || !guideCitation.includes("[software]")) fail("footer: the guide is not cited as software with its editor: " + guideCitation);
  await page.locator(".site-footer a", { hasText: "Kdo se podílel" }).click();
  await page.waitForFunction(() => document.activeElement && document.activeElement.id === "credits");
  const roles = await page.locator(".credits tbody th").allTextContents();
  if (roles.length !== 5 || !roles[0].includes("Autoři obsahového základu") || !roles[1].includes("editor")) fail("about: the roles table is incomplete: " + roles.join(" | "));
  if (!(await page.locator('.credits a[href="https://orcid.org/0000-0001-6491-2947"]').count())) fail("about: the analysis authors do not link their ORCID iDs");
  await go("#/cs/SR/path/licence");

  // The header logo leads to the EOSC CZ home page; the title opens the path's start.
  if ((await page.locator(".brand a").first().getAttribute("href")) !== "https://www.eosc.cz/") fail("header: the EOSC CZ logo does not link to its home page");
  if ((await page.locator(".brand-title").getAttribute("href")) !== "#/cs/SR/path/start") fail("header: the title does not open the path's start");
  if ((await page.locator(".brand img").boundingBox()).height < 40) fail("header: the EOSC CZ logo is too small to read");

  // Each logo of the funding logolink links to its owner, over the part of the image it covers.
  const logoLinks = await page.locator(".logolink .logolink-part").evaluateAll((links) => links.map((link) => [link.getAttribute("href"), link.textContent.trim()]));
  const logoHosts = logoLinks.map(([href]) => new URL(href).host).join(" ");
  if (logoHosts !== "opjak.cz msmt.gov.cz www.eosc.cz" || logoLinks.some(([, name]) => !name)) fail("footer: the logolink parts do not link to their owners: " + JSON.stringify(logoLinks));
  const logoArea = await page.locator(".logolink").boundingBox();
  if ((await page.locator(".logolink-funding").boundingBox()).height < 90) fail("footer: the logolink is too small to read");
  for (const box of await page.locator(".logolink .logolink-part").evaluateAll((links) => links.map((link) => link.getBoundingClientRect().toJSON()))) {
    if (box.width < 40 || box.left < logoArea.x - 1 || box.right > logoArea.x + logoArea.width + 1) fail("footer: a logolink part lies outside the image");
  }

  // The lens band appears only where the lens changes what is shown; in the resource finder it is the lens filter.
  for (const hash of ["#/cs/V/explorer", "#/cs/V/repositories", "#/cs/V/resources", "#/cs/V/page/about", "#/cs/V/check/dataset"]) {
    await go(hash);
    if (await page.locator(".lens-band").count()) fail("lens band: shown where the lens changes nothing: " + hash);
  }
  await go("#/cs/V/selfcheck");
  if (!(await page.locator(".lens-band").count())) fail("lens band: missing on the self-check overview");
  const cornerOffsets = await page.locator(".check-card").evaluateAll((cards) => cards.map((card) => { const box = card.getBoundingClientRect(); const button = card.querySelector(".check-card-action a").getBoundingClientRect(); return Math.round(box.bottom - button.bottom) + "/" + Math.round(box.right - button.right); }));
  if (new Set(cornerOffsets).size !== 1) fail("overview: the check cards' buttons are not in the same corner: " + cornerOffsets.join(" "));
  // In the catalogue the lens is a facet of the resources, starting from the reader's lens; it narrows what the
  // guide recommends and leaves cited works in.
  await go("#/cs/V/resources");
  const shownNow = async () => Number(((await page.locator(".catalogue-count").textContent()).match(/\d+/) || [0])[0]);
  if (!(await page.locator("#facet-resources-lens-v").isChecked())) fail("finder: the lens facet does not start from the reader's lens");
  const researcherCount = await shownNow();
  await page.locator("#facet-resources-lens-v").uncheck();
  await page.waitForFunction(() => location.hash.includes("f.lens!"));
  const allLenses = await shownNow();
  if (allLenses < researcherCount) fail("finder: all lenses do not show at least the researcher's resources");
  await page.locator("#facet-resources-lens-ds").check();
  await page.waitForFunction(() => location.hash.includes("f.lens!DS"));
  if ((await shownNow()) === researcherCount && researcherCount === allLenses) fail("finder: the lens facet does not filter the resources");
  if (!(await page.locator(".card", { hasText: "Analýza a návrh postupů" }).count())) fail("finder: the lens hides a cited work, which has no audience");

  // A shared link opens as a preview in a browser without the answers, and can be adopted.
  await go("#/cs/V/check/dataset");
  await page.locator("#share-create").click();
  const shared = await page.locator("#share-url").inputValue();
  if (!shared.includes("/check/dataset/a1.after._.") || !shared.includes("D04n") || !shared.includes("D05k")) fail("share link: unexpected payload " + shared);
  if (shared.startsWith("file:")) fail("share link: names a local file instead of the published page");
  {
    const other = await browser.newContext();
    const view = await other.newPage();
    await view.goto(pageUrl + shared.slice(shared.indexOf("#")));
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".gaps").first().textContent()).includes("D04")) fail("share link: the preview does not show the D04 gap");
    await view.getByRole("button", { name: "Použít odpovědi z odkazu" }).click();
    await view.waitForSelector("#answer-D04-no");
    if (!(await view.locator("#answer-D04-no").isChecked())) fail("share link: adopting the answers did not store them");
    await view.goto(pageUrl + "#/cs/V/check/dataset/a1.after._.Z99q");
    await view.waitForSelector(".notice");
    if (!(await view.locator(".notice", { hasText: "nepodařilo přečíst" }).count())) fail("share link: an invalid link is not reported");
    await other.close();
  }

  // Gate check: the core-system profile marks monitoring and central logging as provided by NRP.
  await go("#/cs/SR/check/gate");
  await page.locator("#profile-a").check();
  for (const id of ["G09", "G10"]) {
    if (await page.locator(`#answer-${id}-yes`).count()) fail(`gate check: ${id} asks for an answer although NRP provides it`);
    if (!/zajišťuje NRP/i.test(await page.locator(`#item-${id}`).textContent())) fail(`gate check: ${id} is not marked as provided by NRP`);
  }
  if (await page.locator("#item-G18").count()) fail("gate check: G18 shows for the core-system profile");
  // NKR lists no repository yet, so a record is put in place of the loaded list to test the mapping.
  await page.evaluate(() => {
    window.FairGuide.live.nkr = { state: "done", records: [{ id: "test/1", name: "Test repository", content: { pidType: ["DOI"], oaipmhEndpoint: ["https://repo.example/oai"] } }] };
    window.FairGuide.rerender();
  });
  await page.locator("#prefill-nkr-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  for (const id of ["G01", "G07"]) {
    if (!(await checked(`answer-${id}-yes`))) fail(`gate check: ${id} is not pre-filled yes from an NKR record listing DOI`);
    if (!(await page.locator(`#origin-${id}`).textContent()).includes("NKR")) fail(`gate check: ${id} does not name NKR as its source`);
  }
  if (!(await checked("answer-G08-partly"))) fail("gate check: G08 exceeds its pre-fill level");
  if (await page.locator('input[name="answer-G06"]:checked').count()) fail("gate check: G06 is pre-filled although the record does not state it");
  await axe(page, "gate check");

  // Maturity and institution checks run end to end; the institution check has no Minimum items and shows them all.
  await go("#/cs/SR/check/maturity");
  // The maturity check fills in from the re3data snapshot and says which repository it is; a repository outside
  // the snapshot is explained rather than guessed.
  await page.locator('label[for="extended-toggle"]').click();
  // The FAIRsharing lookup goes to DataCite; here it is replaced, as every request is in these checks.
  await page.evaluate(() => { window.FairGuide.live.findFairsharing = async () => []; });
  await page.fill("#prefill-re3data", "https://www.re3data.org/repository/r3d100010386");
  await page.locator("#prefill-re3data-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await checked("answer-S18-partly")) || !(await page.locator("#origin-S18").textContent()).includes("re3data")) fail("maturity check: S18 is not partly met from re3data alone");
  if (!(await checked("answer-S01-yes")) || !(await checked("answer-S19-yes"))) fail("maturity check: re3data facts do not fill in S01 and S19");
  if (!(await page.locator(".target-card").textContent()).includes("LINDAT")) fail("maturity check: the re3data record does not say which repository it is");
  if (!(await page.locator("#origin-S05").textContent()).includes("OAI-PMH")) fail("maturity check: S05 does not show the OAI-PMH evidence from re3data");
  // A failed FAIRsharing lookup leaves S18 open with a note; a record found answers it and links to the record.
  await page.locator("#prefill-re3data-clear").click();
  await page.evaluate(() => { window.FairGuide.live.findFairsharing = async () => { throw new Error("offline"); }; });
  await page.fill("#prefill-re3data", "r3d100010386");
  await page.locator("#prefill-re3data-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if ((await page.locator('input[name="answer-S18"]:checked').count()) || !(await page.locator("#origin-S18").textContent()).includes("nepodařilo ověřit")) fail("maturity check: a failed FAIRsharing lookup does not leave S18 open with a note");
  if (!(await checked("answer-S01-yes"))) fail("maturity check: a failed FAIRsharing lookup stopped the re3data answers");
  await page.evaluate(() => { window.FairGuide.live.findFairsharing = async () => [{ doi: "10.25504/FAIRsharing.test", name: "LINDAT", re3data: "r3d100010386", addresses: [] }]; });
  await page.locator("#prefill-re3data-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await checked("answer-S18-yes"))) fail("maturity check: a FAIRsharing record does not complete S18");
  if (!(await page.locator('#origin-S18 a[href="https://doi.org/10.25504/FAIRsharing.test"]').count())) fail("maturity check: S18 does not link to the FAIRsharing record");
  await page.fill("#prefill-re3data", "r3d999999999");
  await page.locator("#prefill-re3data-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("není ve snímku"));
  await page.locator("#prefill-re3data-clear").click();
  await page.locator("#answer-S02-no").check();
  if (!(await page.locator(".gaps").first().textContent()).includes("S02")) fail("maturity check: the S02 gap is missing");
  await go("#/cs/DS/check/institution");
  if (!(await page.locator("#item-I01").count())) fail("institution check: no item shows in the first view");
  await page.locator("#answer-I01-unknown").check();
  if (!(await page.locator(".gaps").first().textContent()).includes("I01")) fail("institution check: the don't-know task is missing");

  // FIP check: the dashboard snapshot pre-fills answers with their source; a principle without a declaration stays
  // open with a note; a change by the user stays marked.
  await go("#/cs/K/check/fip");
  await page.locator('label[for="extended-toggle"]').click();
  await page.locator("#prefill-fip").selectOption("nusl-grey");
  await page.locator("#prefill-fip-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  const open = await page.evaluate(() => [...document.querySelectorAll("fieldset.item")].filter((item) => !item.querySelector("input:checked") && item.textContent.includes("nic nedeklaruje")).map((item) => item.id));
  if (!open.length) fail("FIP check: no item stays open with a note for a principle without a declaration");
  await page.locator("#prefill-fip").selectOption("ndi-baseline");
  await page.locator("#prefill-fip-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await checked("answer-K01-yes"))) fail("FIP check: K01 is not pre-filled from the snapshot");
  if (!(await panelFits(page))) fail("FIP check: the result so far scrolls or is too tall after pre-fill");
  if (!(await page.locator("#origin-K01").textContent()).includes("FIP Dashboard (snímek)")) fail("FIP check: K01 does not name its source");
  await page.locator("#answer-K01-partly").check();
  if ((await page.locator("#origin-K01 .source-chip").getAttribute("data-origin")) !== "changed") fail("FIP check: a changed pre-filled answer is not marked");
  await axe(page, "FIP check pre-filled");

  // Loading a saved result is a way to start: offered at the top of every check, also before the mode is chosen,
  // and not repeated among the saving controls.
  for (const [hash, label] of [["#/cs/V/check/dataset", "before the mode"], ["#/cs/SR/check/maturity", "with public records"], ["#/cs/DS/check/institution", "without public records"]]) {
    const view = await browser.newPage();
    await view.goto(pageUrl + hash);
    await view.waitForSelector("#main h1");
    if (!(await view.locator(".prefill #load-file").count())) fail(`start (${label}): loading a saved result is not offered at the top of the check`);
    if (await view.locator(".export #load-file, .export .load-file").count()) fail(`start (${label}): loading is repeated among the saving controls`);
    await view.close();
  }

  // Exports: Markdown and an FTR result set in an RO-Crate, naming the published page and the assessed profile.
  await page.locator("#export-format-md").check();
  const [mdDownload] = await Promise.all([page.waitForEvent("download"), page.locator("#export-download").click()]);
  const md = readFileSync(await mdDownload.path(), "utf8");
  if (!md.startsWith("# Úplnost FIP") || md.includes("file:")) fail("export: unexpected Markdown summary");
  await page.locator("#export-format-jsonld").check();
  const [ldDownload] = await Promise.all([page.waitForEvent("download"), page.locator("#export-download").click()]);
  const exported = JSON.parse(readFileSync(await ldDownload.path(), "utf8"));
  const exportedGraph = exported["@graph"];
  const typed = (type) => (entity) => [].concat(entity["@type"]).includes(type);
  const set = exportedGraph.find(typed("TestResultSet"));
  const results = exportedGraph.filter(typed("TestResult"));
  if (!set || set["prov:hadMember"].length !== results.length || !results.length) fail("export: the result set does not hold the results");
  if (!set || !String((set["ftr:assessmentTarget"] || {})["@id"]).includes("/profiles/ndi-baseline")) fail("export: the assessment target is not the chosen profile");
  if (results.some((result) => !["pass", "fail", "indeterminate"].includes(result["prov:value"]))) fail("export: a result has an unexpected value");
  const k01 = results.find((result) => result["@id"] === "#result-K01") || {};
  if (!String(k01["ftr:log"]).includes("Doklad") || !k01["prov:used"]) fail("export: the K01 result does not record its evidence: " + JSON.stringify(k01));
  if (!md.includes("Deklarované")) fail("export: the Markdown summary does not carry the evidence behind the answers");
  if (JSON.stringify(exported).includes("file:")) fail("export: the JSON-LD names a local file");

  // Local data: each check says where the answers are kept, and how it works.
  const note = await page.locator(".local-data").textContent();
  if (!note.includes("zůstávají jen v tomto prohlížeči") || !note.includes("Co odchází")) fail("local data: the statement or its explanation is missing on the check");
  if (!/<!-- fair-guide-result v1 guide=\S+: fip a1\./.test(md)) fail("export: the Markdown summary does not carry the answers with the format and guide versions");
  if (!/<!-- fair-guide-state\n[A-Za-z0-9+/=\n]+\n-->/.test(md)) fail("export: the Markdown summary does not carry the state for loading back");
  const state = JSON.parse(exportedGraph.find((entity) => entity.guideState).guideState);
  if (state.format !== "eosc-fair-guide-result" || state.v !== 1 || !state.guideVersion) fail("export: the JSON-LD does not declare its format and the guide's version");
  if (state.fip !== "ndi-baseline" || !state.targetInfo) fail("export: the JSON-LD does not carry the chosen profile and what it is");

  // A saved result loads in another browser as a preview, keeps its evidence, and is adopted only on request; a
  // file the guide did not make is refused.
  {
    const other = await browser.newContext();
    const view = await other.newPage();
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    const foreign = resolve(root, ".cache", "not-a-result.md");
    writeFileSync(foreign, "# Notes\n\nNothing from the guide.\n");
    await view.locator("#load-file-overview").setInputFiles(foreign);
    await view.waitForFunction(() => document.getElementById("load-file-overview-status").textContent.includes("nevytvořil"));
    // A damaged file, a file from a newer format and a file with a question this version does not know.
    const variant = (name, change) => {
      const copy = JSON.parse(JSON.stringify(exported));
      const holder = copy["@graph"].find((entity) => entity.guideState);
      const data = JSON.parse(holder.guideState);
      change(data);
      holder.guideState = JSON.stringify(data);
      const path = resolve(root, ".cache", name);
      writeFileSync(path, JSON.stringify(copy));
      return path;
    };
    const tryLoad = async (path, expected, message) => {
      await view.locator("#load-file-overview").setInputFiles(path);
      try {
        await view.waitForFunction((text) => document.getElementById("load-file-overview-status").textContent.includes(text), expected, { timeout: 3000 });
      } catch (error) {
        fail(message + ": " + (await view.locator("#load-file-overview-status").textContent()));
      }
    };
    await tryLoad(variant("damaged.jsonld", (data) => { data.items.K01.value = "maybe"; }), "poškozený", "load: a damaged file is not reported as damaged");
    await tryLoad(variant("newer.jsonld", (data) => { data.v = 2; data.guideVersion = "9.0.0"; }), "novější verze", "load: a file from a newer format is not reported");
    await view.locator("#load-file-overview").setInputFiles(variant("unknown-item.jsonld", (data) => { data.items.K99 = { value: "yes", origin: "user", prefill: null }; }));
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("vynechali: 1")) fail("load: a question this version does not know is not skipped with a note");
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await view.locator("#load-file-overview").setInputFiles(await ldDownload.path());
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("ze souboru")) fail("load: a JSON-LD file does not open as a preview");
    if (await view.evaluate(() => Object.keys(window.FairGuide.state.answers).length)) fail("load: the preview changed the stored answers");
    await view.getByRole("button", { name: "Použít odpovědi ze souboru" }).click();
    await view.waitForSelector("#answer-K01-partly");
    if (!(await view.locator("#answer-K01-partly").isChecked())) fail("load: the adopted answers are not the file's answers");
    const loaded = await view.locator("#origin-K01").textContent();
    if (!loaded.includes("Převzato ze sdíleného výsledku") || !loaded.includes("liší se od návrhu")) fail("load: the adopted K01 lost its evidence or is mislabelled: " + loaded);
    const restored = async (format) => {
      if ((await view.locator("#prefill-fip").inputValue()) !== "ndi-baseline") fail(`load (${format}): the profile chosen for pre-fill is not restored`);
      if (!(await view.locator(".target-card").count())) fail(`load (${format}): what the identifier is does not show after loading`);
    };
    await restored("JSON-LD");
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await view.locator("#load-file-overview").setInputFiles(await mdDownload.path());
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("ze souboru")) fail("load: a Markdown summary does not open as a preview");
    await view.getByRole("button", { name: "Použít odpovědi ze souboru" }).click();
    await view.waitForSelector("#answer-K01-partly");
    const fromMarkdown = await view.locator("#origin-K01").textContent();
    if (!fromMarkdown.includes("liší se od návrhu")) fail("load (Markdown): the adopted K01 lost its evidence: " + fromMarkdown);
    await restored("Markdown");
    // A summary from before the state was carried still loads its answers.
    const older = resolve(root, ".cache", "older-summary.md");
    writeFileSync(older, md.replace(/<!-- fair-guide-state[\s\S]*?-->\n?/, ""));
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await view.locator("#load-file-overview").setInputFiles(older);
    await view.waitForSelector(".notice.shared");
    const broken = resolve(root, ".cache", "broken-state.md");
    writeFileSync(broken, md.replace(/(<!-- fair-guide-state\n)[A-Za-z0-9]{8}/, "$1@@@@@@@@"));
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await tryLoad(broken, "poškozený", "load: a summary with a damaged state is not reported as damaged");
    await other.close();
  }

  // Reflow of a check at 320 CSS pixels.
  await page.setViewportSize({ width: 320, height: 800 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 1) fail(`FIP check: horizontal scroll of ${overflow}px at 320 px`);

  // Deleting everything leaves nothing the guide stored, and the checks start empty.
  await go("#/cs/K/selfcheck");
  if (!(await page.locator("#local-data-delete").isVisible())) fail("local data: the delete control is not visible without opening anything");
  page.once("dialog", (dialog) => dialog.accept());
  await page.locator("#local-data-delete").click();
  await page.waitForFunction(() => document.getElementById("local-data-status").textContent.includes("smazané"));
  if (await page.evaluate(() => window.localStorage.getItem("eosc-fair-guide"))) fail("local data: something remains in the browser after deleting everything");
  await go("#/cs/V/check/dataset");
  if (!(await page.locator(".notice", { hasText: "Nejdřív odpovězte" }).count())) fail("local data: the dataset check kept its answers after deleting everything");
  if (await page.evaluate(() => window.localStorage.getItem("eosc-fair-guide"))) fail("local data: browsing after deletion stored something without a user action");

  if (external.length) fail("self-check: requests without a lookup: " + external.join(", "));
  for (const problem of problems) fail("self-check: " + problem);
  console.log("checked the self-check flows");
  await context.close();
}

await browser.close();
if (failures.length) {
  console.error(failures.map((failure) => "FAIL " + failure).join("\n"));
  console.error(`${failures.length} problem(s)`);
  process.exit(1);
}
console.log("page checks passed");
