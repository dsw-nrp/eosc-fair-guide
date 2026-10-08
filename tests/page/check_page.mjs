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
  await axe(page, "landing");

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

  // Universal search: terms are found locally while typing, in both languages and without diacritics; identifiers
  // are routed to their tool once the search is confirmed, and nothing is sent while searching.
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
  if (!(await page.locator("#search-results .result-primary").textContent()).includes("Zkontrolovat datovou sadu")) fail("search: a DOI is not routed to the dataset check");
  found = await search("0000-0001-6592-6291");
  if (!found.includes("Ověřit identifikátor")) fail("search: an ORCID iD is not routed to the identifier helper");
  await axe(page, "landing with search results");
  if (external.length) fail("search: requests while searching: " + external.join(", "));

  // Task shortcuts change with the lens, chosen in the band under the main menu.
  if ((await page.locator(".lens-band .lens-option").count()) !== 4) fail("lens band: four options are not shown on the landing");
  if ((await page.locator('.lens-option[aria-current="true"]').getAttribute("data-lens")) !== "V") fail("lens band: the current lens is not marked");
  if ((await page.locator('.lens-option[data-lens="SR"]').getAttribute("href")) !== "#/cs/SR/path/start") fail("lens band: an option is not a shareable link");
  await page.locator('.lens-option[data-lens="SR"]').click();
  await lensShown(page, "SR");
  if (!(await page.locator(".tasks").textContent()).includes("Brána NRP")) fail("landing: the repository administrator's tasks are missing");
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
    for (const view of ["explorer", "resources", "repositories", "selfcheck"]) views.push(`#/${lang}/V/${view}`);
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
  await page.locator("#extended-toggle").click();
  if (!(await page.locator("#item-D06").count())) fail("dataset check: the extended check does not show Recommended items");
  if (!(await checked("answer-D04-no"))) fail("dataset check: opening the extended check lost an answer");
  await page.locator("#extended-toggle").click();

  // The first view says what its tier means; items are grouped by FAIR principle, can be grouped by path step, and
  // each names the step where it is addressed.
  const tierInfo = await page.locator(".tier-info").textContent();
  if (!tierInfo.includes("Minimum (") || !tierInfo.includes("Národní datové infrastruktury")) fail("dataset check: the first view does not explain its tier: " + tierInfo);
  const minimumCount = (tierInfo.match(/Minimum \((\d+)\)/) || [])[1];
  if (!(await page.locator("#results p").first().textContent()).endsWith("z " + minimumCount)) fail("dataset check: the result counts items the first view does not show");
  if (!(await page.locator(".item-group h2").first().textContent()).includes("Dohledatelnost")) fail("dataset check: items are not grouped by FAIR principle by default");
  if (!(await page.locator("#item-D04 .fix-at").textContent()).includes("Licence")) fail("dataset check: an item does not name the step where it is addressed");
  await page.locator("#grouping-steps").check();
  if (!(await page.locator(".item-group h2").first().textContent()).includes("Řeší se v kroku")) fail("dataset check: grouping by path step does not work");
  await page.locator("#grouping-principles").check();

  // The result stands beside the questions and shows the licence gap at once; it can be collapsed, and the choice
  // survives a reload.
  const mainBox = await page.locator(".check-main").boundingBox();
  const resultBox = await page.locator(".check-result").boundingBox();
  if (!(resultBox.x > mainBox.x + mainBox.width / 2)) fail("dataset check: the result is not beside the questions");
  await page.locator("#item-D04").scrollIntoViewIfNeeded();
  const gapCell = page.locator('.principle-cell[data-state="gap"]', { hasText: "R1.1" });
  const gapBox = await gapCell.boundingBox();
  if (!gapBox || gapBox.y < 0 || gapBox.y + gapBox.height > (await page.evaluate(() => window.innerHeight))) fail("dataset check: the R1.1 gap is not in view beside the item");
  await page.locator("#result-toggle").click();
  if (!(await page.locator("#result-body").isHidden())) fail("dataset check: the result panel does not collapse");
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
    st.items.D02 = {
      value: "yes",
      origin: "prefill",
      prefill: { source: "resolver", date: "2026-10-08", value: "yes", notes: [], list: [], fields: [{ path: "url", values: ["https://repo.example/record/1"], more: 0 }], record: "https://repo.example/record/1" },
    };
    FG.saveState();
    FG.rerender();
  });
  const evidence = await page.locator("#origin-D02").textContent();
  if (!evidence.includes("url") || !evidence.includes("https://repo.example/record/1") || !evidence.includes("8. 10. 2026")) fail("dataset check: the evidence beside D02 is incomplete: " + evidence);
  if ((await page.locator("#origin-D02 a").getAttribute("href")) !== "https://repo.example/record/1") fail("dataset check: the evidence does not link to its record");
  await page.getByRole("button", { name: "Shrnutí v Markdownu" }).click();
  if (!(await page.locator("#markdown-text").inputValue()).includes("url = https://repo.example/record/1")) fail("dataset check: the Markdown summary lacks the evidence");
  await page.locator("#prefill-pid-clear").click();
  if (await page.locator('input[name="answer-D02"]:checked').count()) fail("dataset check: clearing the identifier kept the answer it pre-filled");
  if (!(await checked("answer-D01-yes")) || !(await checked("answer-D04-no"))) fail("dataset check: clearing the identifier removed the user's own answers");
  if (await page.locator("#prefill-pid").inputValue()) fail("dataset check: clearing did not empty the identifier field");

  // The path marks the stations with open items.
  await go("#/cs/V/path/licence");
  if (!(await page.locator('.rail-desktop a[href="#/cs/V/path/licence"] .gap-mark').count())) fail("path: the licence station has no gap mark");
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

  // Credit: the station line names sources, not people, and opens the full detail; the footer credits the analysis
  // authors and cites the guide with its compiler as editor; the roles are listed on the about page.
  const provenance = await page.locator(".provenance-line").textContent();
  if (!provenance.includes("Analýzy FAIR") || /Novák|Trtíková/.test(provenance)) fail("station: the provenance line is not a sources-only line: " + provenance);
  await page.locator(".provenance-line button").click();
  if (!(await page.locator('details[data-key="L3"][open]').count())) fail("station: the provenance line does not open the sources and paradata");
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
  for (const hash of ["#/cs/V/explorer", "#/cs/V/repositories", "#/cs/V/page/about", "#/cs/V/check/dataset"]) {
    await go(hash);
    if (await page.locator(".lens-band").count()) fail("lens band: shown where the lens changes nothing: " + hash);
  }
  await go("#/cs/V/selfcheck");
  if (!(await page.locator(".lens-band").count())) fail("lens band: missing on the self-check overview");
  await go("#/cs/V/resources");
  if (await page.locator('.filters select[name="lens"]').count()) fail("finder: a second lens filter is shown beside the band");
  const researcherCount = await page.locator(".cards").first().locator("> li").count();
  await page.locator('.lens-option[data-lens="DS"]').click();
  await lensShown(page, "DS");
  if ((await page.locator(".cards").first().locator("> li").count()) === researcherCount) fail("finder: the lens band does not filter the resources");

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
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Předvyplněno"));
  for (const id of ["G01", "G07"]) {
    if (!(await checked(`answer-${id}-yes`))) fail(`gate check: ${id} is not pre-filled yes from an NKR record listing DOI`);
    if (!(await page.locator(`#origin-${id}`).textContent()).includes("NKR")) fail(`gate check: ${id} does not name NKR as its source`);
  }
  if (!(await checked("answer-G08-partly"))) fail("gate check: G08 exceeds its pre-fill level");
  if (await page.locator('input[name="answer-G06"]:checked').count()) fail("gate check: G06 is pre-filled although the record does not state it");
  await axe(page, "gate check");

  // Maturity and institution checks run end to end; the institution check has no Minimum items and shows them all.
  await go("#/cs/SR/check/maturity");
  await page.locator("#answer-S02-no").check();
  if (!(await page.locator(".gaps").first().textContent()).includes("S02")) fail("maturity check: the S02 gap is missing");
  await go("#/cs/DS/check/institution");
  if (!(await page.locator("#item-I01").count())) fail("institution check: no item shows in the first view");
  await page.locator("#answer-I01-unknown").check();
  if (!(await page.locator(".gaps").first().textContent()).includes("I01")) fail("institution check: the don't-know task is missing");

  // FIP check: the dashboard snapshot pre-fills answers with their source; a principle without a declaration stays
  // open with a note; a change by the user stays marked.
  await go("#/cs/K/check/fip");
  await page.locator("#extended-toggle").click();
  await page.locator("#prefill-fip").selectOption("nusl-grey");
  await page.locator("#prefill-fip-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Předvyplněno"));
  const open = await page.evaluate(() => [...document.querySelectorAll("fieldset.item")].filter((item) => !item.querySelector("input:checked") && item.textContent.includes("nic nedeklaruje")).map((item) => item.id));
  if (!open.length) fail("FIP check: no item stays open with a note for a principle without a declaration");
  await page.locator("#prefill-fip").selectOption("ndi-baseline");
  await page.locator("#prefill-fip-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Předvyplněno"));
  if (!(await checked("answer-K01-yes"))) fail("FIP check: K01 is not pre-filled from the snapshot");
  if (!(await page.locator("#origin-K01").textContent()).includes("FIP Dashboard (snímek)")) fail("FIP check: K01 does not name its source");
  await page.locator("#answer-K01-partly").check();
  if ((await page.locator("#origin-K01 .source-chip").getAttribute("data-origin")) !== "changed") fail("FIP check: a changed pre-filled answer is not marked");
  await axe(page, "FIP check pre-filled");

  // Exports: Markdown and an FTR result set in an RO-Crate, naming the published page and the assessed profile.
  const [mdDownload] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Stáhnout shrnutí (.md)" }).click()]);
  const md = readFileSync(await mdDownload.path(), "utf8");
  if (!md.startsWith("# Úplnost FIP") || md.includes("file:")) fail("export: unexpected Markdown summary");
  const [ldDownload] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: /Stáhnout výsledek jako JSON-LD/ }).click()]);
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
  if (!md.includes("Doklad")) fail("export: the Markdown summary has no evidence column");
  if (JSON.stringify(exported).includes("file:")) fail("export: the JSON-LD names a local file");

  // Local data: each check says where the answers are kept, and how it works.
  const note = await page.locator(".local-data").textContent();
  if (!note.includes("zůstávají jen v tomto prohlížeči") || !note.includes("Co odchází")) fail("local data: the statement or its explanation is missing on the check");
  if (!md.includes("<!-- fair-guide-result: fip a1.")) fail("export: the Markdown summary does not carry the answers");

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
    await view.locator("#load-file-overview").setInputFiles(await ldDownload.path());
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("ze souboru")) fail("load: a JSON-LD file does not open as a preview");
    if (await view.evaluate(() => Object.keys(window.FairGuide.state.answers).length)) fail("load: the preview changed the stored answers");
    await view.getByRole("button", { name: "Použít odpovědi ze souboru" }).click();
    await view.waitForSelector("#answer-K01-partly");
    if (!(await view.locator("#answer-K01-partly").isChecked())) fail("load: the adopted answers are not the file's answers");
    const loaded = await view.locator("#origin-K01").textContent();
    if (!loaded.includes("Převzato ze sdíleného výsledku") || !loaded.includes("liší se od návrhu")) fail("load: the adopted K01 lost its evidence or is mislabelled: " + loaded);
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await view.locator("#load-file-overview").setInputFiles(await mdDownload.path());
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("ze souboru")) fail("load: a Markdown summary does not open as a preview");
    await other.close();
  }

  // Reflow of a check at 320 CSS pixels.
  await page.setViewportSize({ width: 320, height: 800 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 1) fail(`FIP check: horizontal scroll of ${overflow}px at 320 px`);

  // Deleting everything leaves nothing the guide stored, and the checks start empty.
  await go("#/cs/K/selfcheck");
  await page.locator(".local-data summary").click();
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
