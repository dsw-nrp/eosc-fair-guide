// Page checks for the FAIR Data Guide, run in Chromium with Playwright:
// - the page renders from a local file without any external request on load, console error or CSP violation;
// - every station renders in every lens and language, and so do the other views;
// - axe finds no WCAG 2.2 A or AA violation in any of those views;
// - the keyboard reaches the main controls, the page reflows at 320 px, and it works inside an iframe;
// - the self-check runs without network: modes, profiles, tiers, gaps on the path, snapshot pre-fill, a shared
//   link and the exports, with no score anywhere;
// - every landing shortcut and station action that stays in the guide reaches what it names;
// - a control that cannot act yet is inactive with a visible reason, and becomes active once it can.
// Usage: python scripts/build_site.py && npm run check:page   (set PLAYWRIGHT_BROWSERS_PATH if the browser lives outside the default cache)

import { chromium, recordFailure, runCases } from "./browser.mjs";
import { mapLimit } from "../../scripts/browser_env.mjs";
import { rendered, navigationRendered, gotoView, searchReady } from "./navigation.mjs";
import { audit } from "./accessibility.mjs";
import { compactControlProblems } from "./compact_controls.mjs";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
// The built site (python scripts/build_site.py): the page, its data and the API, as they are published.
const site = resolve(root, "_site");
const pageUrl = pathToFileURL(resolve(site, "index.html")).href;
const crate = JSON.parse(readFileSync(resolve(site, "ro-crate-metadata.json"), "utf8"));
const graph = crate["@graph"];
// The full crate is independent of the browser's deferred loading. Keep explicit address assertions below,
// and use the published identity to locate the same entry in checks of its other behaviour.
const sourceAnchors = new Map();
for (const entity of graph.filter((e) => e.catalogueAddress)) {
  const anchor = entity.catalogueAddress.split("/").slice(1).join("/");
  for (const reference of [].concat(entity.alternateIdentifier || [])) {
    const source = graph.find((node) => node["@id"] === reference["@id"]);
    if (source?.propertyID && source.value) sourceAnchors.set(source.propertyID + "." + source.value, anchor);
  }
  for (const reference of [].concat(entity.sameAs || [])) {
    const match = reference["@id"]?.match(/re3data\.org\/repository\/(r3d\d+)$|fip-dashboard\.dmp\.eosc\.cz\/resources\/([^/]+)$/);
    if (match) sourceAnchors.set((match[1] ? "re3data." : "fip-dashboard.") + (match[1] || match[2]), anchor);
  }

  for (const token of [entity.identifier, entity["@id"].replace(/^#(resource|repository|term|knav)-/, ""), entity["@id"].startsWith("#repository-r3d") && "re3data." + entity.identifier, entity["@id"].startsWith("#fer-") && "fip-dashboard." + entity.identifier, entity.termCode && "t.ntk." + entity.termCode].flat().filter(Boolean)) {
    sourceAnchors.set(String(token), anchor);
  }
}
const publishedUi = JSON.parse(readFileSync(resolve(site, "assets/data/ui.js"), "utf8").match(/^window\.FairGuideData\.ui = (.*);$/m)[1]);
const entryAnchor = (id) => sourceAnchors.get(String(id)) || id;
const cataloguePath = (kind, id) => {
  const prefix = Object.keys(publishedUi.config.catalogueKinds).find((code) => publishedUi.config.catalogueKinds[code] === kind) || kind;
  const source = graph.find((entity) => entity.identifier === id || entity["@id"] === "#knav-" + String(id).replace(/^knav\./, ""));
  const equivalent = [].concat(source?.sameAs || []).map((ref) => graph.find((entity) => entity["@id"] === ref["@id"])).find((entity) => entity?.catalogueAddress);
  const entity = graph.find((entity) => entity.catalogueAddress?.startsWith(prefix + "/") && (entity.identifier === id || entity.catalogueAddress.split("/").slice(1).join("/") === entryAnchor(id))) || equivalent;
  return "/catalogue/" + (entity?.catalogueAddress || prefix + "/" + entryAnchor(id));
};

// The interface strings' structure, to tell a raw string key on the page from ordinary text.
const uiStrings = JSON.parse(readFileSync(resolve(site, "assets/data/ui.js"), "utf8").match(/^window\.FairGuideData\.ui = (.*);$/m)[1]).ui;
const isUiKey = (token) => token.split(".").reduce((node, part) => (node && typeof node === "object" ? node[part] : undefined), uiStrings) !== undefined;
const stations =graph.filter((e) => e["@type"] === "HowToSection").map((e) => e.identifier);
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
const principles = graph.filter((e) => String(e["@id"]).startsWith("#principle-") && e.termCode).map((e) => e.termCode);
const checks = graph.filter((e) => e["@type"] === "Quiz").map((e) => ({ id: e.identifier, lens: [].concat(e.audience)[0]["@id"].replace("#lens-", "") }));
const failures = [];
// The question numbers a list of gaps or tasks shows: a question shows by its number inside its check.
const numbersIn = (list) => list.locator(".item-id").allTextContents();
const fail = (message) => { failures.push(message); recordFailure(message); };
/** A followed link marks its entry for about a second and a half and then lets the mark go, so a wait started after
    the click can miss it on a loaded machine and report a defect that is not there. Record the mark in the page as
    the browser applies it, before the click, and assert the recorded fact once the click has settled. */
async function watchJump(page, entryId) {
  entryId = entryAnchor(entryId);
  await page.evaluate((id) => {
    window.__jumpMarked = false;
    const seen = (node) => {
      if (!node || typeof node.id !== "string") return;
      const candidates = node.id === "item-" + id ? [node] : node.querySelectorAll('[id="item-' + CSS.escape(id) + '"]');
      for (const element of candidates) if (element.classList.contains("jumped")) window.__jumpMarked = true;
    };
    const observer = new MutationObserver((records) => {
      for (const record of records) {
        if (record.type === "attributes") seen(record.target);
        else for (const node of record.addedNodes) if (node.nodeType === 1) seen(node);
      }
    });
    observer.observe(document.getElementById("app") || document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["class"] });
  }, entryId);
}

const browser = await chromium.launch();
/** The independent sections of the checks, run at once; each opens its own browser context. */
const sections = [];

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

async function axe(page, label) {
  page.axeState.axeRunning = true;
  const result = await audit(page);
  page.axeState.axeRunning = false;
  for (const violation of result.violations) {
    fail(`${label}: axe ${violation.id} (${violation.impact}) on ${violation.nodes.length} node(s): ${violation.nodes[0].target.join(" ")}`);
  }
}

import { misalignedControls, collisions } from "./layout.mjs";

// 1. Load from a local file: no external request, no error.
sections.push(["page", async () => {
  const { context, page, external, problems } = await openPage();
  await gotoView(page, pageUrl);
  await rendered(page);
  if (external.length) fail("requests on load: " + external.join(", "));
  for (const problem of problems) fail("load: " + problem);
  const heading = await page.textContent("#main h1");
  if (!heading.includes("Průvodce FAIR daty")) fail("first visit does not open the landing: " + heading);
  // The page icon is the EOSC CZ symbol, as the FIP Dashboard uses it, served from the page's own files.
  for (const rel of ["icon", "apple-touch-icon"]) {
    const href = await page.locator(`head link[rel="${rel}"]`).getAttribute("href");
    if (!href || /^[a-z]+:/i.test(href) || !existsSync(resolve(root, href))) fail(`page icon: the ${rel} link is missing or not a file of the page: ${href}`);
  }
  if (!(await page.locator("#search-input").count())) fail("landing: no search box");
  // The life-cycle journey: the path's stages in order, each opening its first step and naming its steps, the check
  // within reuse; before any step was read, no stage is marked.
  const staged = graph.filter((e) => e["@type"] === "HowToSection" && e.lifecycleStage);
  const pathStages = [...new Set(staged.map((e) => e.lifecycleStage["@id"]))];
  if (!(await page.locator("#journey-title").textContent()).includes("Životní cyklus výzkumných dat")) fail("landing: no life-cycle journey");
  if ((await page.locator(".journey-stages > li").count()) !== pathStages.length) fail(`landing: the journey does not show the ${pathStages.length} stages`);
  if ((await page.locator(".journey-stages .journey-steps a").count()) !== staged.length) fail("landing: the journey's stages do not name all their steps");
  if ((await page.locator(".journey-stage").first().getAttribute("href")) !== "#/cs/V/path/plan") fail("landing: the first stage does not open the first step");
  if ((await page.locator(".journey-stages > li", { hasText: "Uchovávání dat" }).locator(".journey-stage").getAttribute("href")) !== "#/cs/V/path/repository") fail("landing: the preservation stage does not open the repository step");
  if (staged.length !== stations.length) fail("landing: a step stands outside the life cycle");
  if (!(await page.locator(".journey-stages > li", { hasText: "Opakované užití dat" }).locator('a[href="#/cs/V/path/assessment"]').count())) fail("landing: the check is not in the reuse stage");
  // The ring draws the same stages in the same order and closes: the last stage leads back to the first.
  const ring = await page.locator(".journey-ring .ring-stage").evaluateAll((groups) => groups.map((group) => [group.dataset.stage, group.dataset.next]));
  const listed = await page.locator(".journey-stages > li .journey-stage strong").allTextContents();
  if (ring.length !== pathStages.length || ring.length !== listed.length) fail(`landing: the ring has ${ring.length} stages, the list ${listed.length}`);
  if (ring.some(([, next], index) => next !== ring[(index + 1) % ring.length][0])) fail("landing: the ring does not lead from each stage to the next and from reuse back to planning");
  if (ring.length && (ring[0][0] !== "plan" || ring[ring.length - 1][0] !== "reuse")) fail("landing: the ring does not run from planning to reuse");
  if ((await page.locator(".journey-ring svg").getAttribute("aria-hidden")) !== "true") fail("landing: the ring is not hidden from assistive technology beside its list");
  if (await page.locator(".ring-last").count()) fail("landing: a first visit marks a stage on the ring");
  if (await page.locator(".journey-last").count()) fail("landing: a first visit marks a stage as last read");
  if (!(await page.locator(".tasks .task").count())) fail("landing: no task shortcuts");
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
      await gotoView(view, pageUrl + hash);
      await view.waitForSelector(".catalogue-layout");
    };
    await open("#/cs/V/catalogue/k!resources");
    const items = await menu();
    if (!items.includes("Katalog") || items.includes("Zdroje") || items.includes("Repozitáře")) fail("catalogue: the menu does not hold one catalogue item in place of the finders: " + items.join(", "));
    if ((await current()) !== "Katalog" || (await kinds()) !== "resources") fail("catalogue: the resources address does not select the resources: " + (await kinds()));
    await open("#repositories");
    if ((await kinds()) !== "repositories") fail("catalogue: an in-page link to the repositories does not select them");
    for (const [old, kind] of [["sources", "resources"], ["clauses", "clauses"], ["questions", "questions"], ["terms", "terms"], ["fips", "fips"], ["tests", "tests"], ["lifecycle", "lifecycle"], ["actions", "actions"]]) {
      await open("#/cs/V/catalogue/" + old);
      if ((await kinds()) !== kind) fail(`catalogue: the address for ${old} does not select ${kind}`);
      if (!(await view.locator(".catalogue-results .card").count())) fail(`catalogue: ${kind} list nothing`);
    }
    if ((await view.locator('[data-facet="kind"] input[type="radio"]').count()) !== 11) fail("catalogue: the kind is not a single choice among eleven");
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
    // Chips show the short local ID; their link retains the complete canonical address.
    for (const kind of ["terms", "fips", "tests", "repositories"]) {
      await open("#/cs/V/catalogue/k!" + kind);
      const chips = await view.locator(".catalogue-results .card .entry-head .id-chip").evaluateAll((links) => links.map((link) => [link.textContent, link.getAttribute("href")]));
      if (!chips.length || chips.some(([id, href]) => id.includes("/") || id.length > 32 || !href.endsWith("/" + id))) fail(`catalogue: ${kind} chips do not show their compact local ID`);
    }

    // Resources and cited sources as one kind, marked by how the guide uses them.
    await open("#/cs/V/catalogue/resources");
    // Where the guide uses an entry is one row, stations by icon and name, then checks; its details (publisher,
    // language, version, date) are one quiet line, not badges.
    const analysisCard = view.locator(".card", { hasText: "Analýza a návrh postupů" }).first();
    const analysis = await analysisCard.textContent();
    const used = analysisCard.locator(".relations dd").nth(0);
    if (!(await analysisCard.locator(".entry-head").textContent()).includes("podklad obsahu") || !(await used.locator("a.holder-link", { hasText: "Plán" }).count()) || !analysis.includes("Zralost FAIR repozitáře")) fail("catalogue: the analysis is not marked as a basis with the stations and checks that cite it");
    if ((await analysisCard.locator(".relations dt", { hasText: "V Průvodci" }).count()) !== 1 || !(await analysisCard.locator(".card-details").textContent()).includes("verze 1.2") || (await analysisCard.locator(".badge", { hasText: "verze" }).count())) fail("catalogue: the analysis card does not keep where it is used in one row and its details out of the badges");
    // A kind's own facets list their values by number of records, most first.
    const counts = await view.locator('[data-facet="resources-use"] .facet-count').allTextContents();
    if (counts.join(",") !== counts.map(Number).sort((a, b) => b - a).join(",")) fail("catalogue: a kind's facet is not ordered by number of records: " + counts.join(","));
    const both = await view.locator(".card", { hasText: "AI jako služba (CERIT)" }).first().textContent();
    if (!both.includes("doporučuje Průvodce") || !both.includes("podklad obsahu")) fail("catalogue: a resource that is also cited is not marked with both uses");

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
    // The chosen kind's own filter holds for no other kind: the others count none and say why.
    await view.locator("#facet-clauses-ckind-recommendation").check();
    await view.waitForFunction(() => location.hash.includes("f.ckind!recommendation"));
    const otherKind = view.locator('[data-facet="kind"] li', { hasText: "Zdroje" });
    if ((await otherKind.locator(".facet-count").textContent()) !== "0" || !(await view.locator('[data-facet="kind"] > .facet-note').textContent()).includes("platí jen pro druh Požadavky")) fail("catalogue: another kind is counted under a filter of the chosen kind, or the picker does not say why");
    await view.locator("#facet-clauses-ckind-recommendation").uncheck();
    await view.waitForFunction(() => !location.hash.includes("f.ckind!recommendation"));
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
    // Typing with pauses renders the list again after each pause; the field keeps the text in order, its spaces, and
    // the caret where it was, also when editing in the middle.
    const typed = async (keys) => {
      for (const key of keys) {
        await view.keyboard.press(key);
        await view.waitForTimeout(400);
      }
      return view.evaluate(() => ({ id: document.activeElement.id, value: document.activeElement.value, caret: document.activeElement.selectionStart }));
    };
    await view.locator("#catalogue-search").fill("");
    await view.locator("#catalogue-search").focus();
    let field = await typed([..."open sci"].map((char) => (char === " " ? "Space" : char)));
    if (field.id !== "catalogue-search" || field.value !== "open sci" || field.caret !== 8) fail("catalogue: typing with pauses does not keep the text, its space and the caret: " + JSON.stringify(field));
    field = await typed(["ArrowLeft", "ArrowLeft", "ArrowLeft", "x"]);
    if (field.value !== "open xsci" || field.caret !== 6) fail("catalogue: editing the search in the middle loses the caret: " + JSON.stringify(field));
    await view.locator("#catalogue-search").fill("");
    await view.waitForFunction(() => !location.hash.includes("q!"));

    // In English, titles and badges carry no Czech outside an original title marked as Czech, and a work the guide
    // only cites shows its original title with the translation in brackets; in Czech the original stands alone.
    await open("#/en/V/catalogue/resources");
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
    await open("#/cs/V/catalogue/resources");
    if ((await surveyTitle()).includes("[")) fail("catalogue: in Czech a Czech work shows a translation: " + (await surveyTitle()));

    // No shared facet shows only zeros: a kind whose entries carry no station or principle shows no such facet or
    // order; FIP profiles take principles from their declarations, content changes the places of what they changed.
    for (const kind of ["resources", "repositories", "infrastructures", "clauses", "questions", "terms", "fips", "tests", "actions"]) {
      await open("#/cs/V/catalogue/" + kind);
      const empty = await view.evaluate(() =>
        ["station", "principle"].filter((name) => {
          const group = document.querySelector(`[data-facet="${name}"]`);
          return group && ![...group.querySelectorAll(".facet-count")].some((node) => Number(node.textContent) > 0);
        })
      );
      if (empty.length) fail(`catalogue: ${kind} shows a facet with only zeros: ${empty.join(", ")}`);
    }
    await open("#/cs/V/catalogue/fips");
    if (!(await view.locator('[data-facet="principle"]').count()) || (await view.locator('[data-facet="station"]').count())) fail("catalogue: FIP profiles do not filter by principle alone");
    await open("#/cs/V/catalogue/actions");
    if (!(await view.locator('[data-facet="station"]').count())) fail("catalogue: content changes do not filter by the stations they changed");

    // Finders: resources order by type, status or the date their status was checked, oldest first, and keep their
    // orientation tags; repositories order by data source and link each source to its record; while NKR lists no
    // repository, sample records built from re3data facts show on request, labelled as samples.
    await open("#/cs/V/catalogue/resources");
    const groupNames = async () => (await view.locator(".catalogue-group > h2").allTextContents()).map((name) => name.split(" · ")[0]);
    const orderBy = async (order) => {
      await view.locator("#catalogue-order").selectOption(order);
      await view.waitForFunction((value) => location.hash.includes("o!" + value), order);
      return groupNames();
    };
    const checkedGroups = await orderBy("checked");
    const checkedDates = checkedGroups.filter((name) => name.startsWith("Ověřeno")).map((name) => name.replace("Ověřeno ", "").split(". ").reverse().map((part) => part.padStart(2, "0")).join(""));
    if (!checkedDates.length || checkedDates.some((date, index) => index && date < checkedDates[index - 1]) || checkedGroups[checkedGroups.length - 1] !== "Bez data ověření") fail("finders: ordering by the date checked does not put the oldest first: " + checkedGroups.join(" | "));
    if (!(await view.locator(".catalogue-results .card .relations .audience svg.icon").count()) || !(await view.locator(".catalogue-results .card .relations .principle-tile").count())) fail("finders: resource cards lack their audiences (icon and name) and principle tiles");
    const typeGroups = await orderBy("type");
    if (new Set(typeGroups).size !== typeGroups.length) fail("finders: a type shows as two groups: " + typeGroups.join(" | "));
    const moreTypes = view.locator('[data-facet="resources-type"] button');
    if (await moreTypes.count()) await moreTypes.first().click();
    const typeValues = await view.locator('[data-facet="resources-type"] .facet-label').allTextContents();
    if (new Set(typeValues).size !== typeValues.length) fail("finders: the type facet offers one type twice: " + typeValues.join(" | "));
    // One vocabulary of types for resources, cited sources and FIP Dashboard records, written as categories are.
    if (typeValues.some((value) => /^\p{Lu}/u.test(value) && !/^\p{Lu}{2,}/u.test(value)) || typeValues.length > 15) fail("finders: the types are not one vocabulary in lower case: " + typeValues.join(" | "));
    const statusGroups = await orderBy("status");
    if (statusGroups[0] !== "provozní" || statusGroups[statusGroups.length - 1] !== "Bez stavu") fail("finders: statuses are not in their own order: " + statusGroups.join(" | "));
    await open("#/cs/V/catalogue/repositories");
    if ((await orderBy("rsource"))[0] !== "výběr Průvodce") fail("finders: ordering repositories by data source does not start with the guide's selection");
    if (!(await view.locator('.relations a[href^="https://www.re3data.org/repository/r3d"]').count())) fail("finders: a repository's re3data source does not link to its record");
    // NKR records arrive in the reviewed snapshot; an empty snapshot says so without offering an on-demand load.
    // A snapshot record joins the repository it describes or is listed alone.
    const repositoryCount = () => view.evaluate(() => window.FairGuide.repositoryEntries().length);
    const repositoriesBefore = await repositoryCount();
    if (await view.locator("#nkr-load").count()) fail("finders: the reviewed NKR snapshot still offers an on-demand load");
    if (!(await view.locator("#nkr-status").textContent()).includes("NKR zatím žádný repozitář neuvádí") || !(await view.locator('#nkr-status a[href^="https://"]').count())) fail("finders: an empty NKR snapshot does not say so with a link to NKR");
    if ((await repositoryCount()) !== repositoriesBefore) fail("finders: an empty NKR result changes the repositories");
    if (await view.locator(".nkr-sample, #nkr-samples").count()) fail("finders: records NKR does not have are shown in its place");
    // Joining matched and unmatched NKR records now happens at build time, covered by
    // test_annotations_and_nkr_records_join_the_catalogue_at_build_time in tests/test_scripts.py.

    // Content from the EOSC CZ website: each step's training is a line among the help routes, not a resource card;
    // the identifier callout leads with scripted verification; the About page links the introductory courses; the
    // repository finder lists the added general-purpose and domain repositories.
    for (const [step, count] of [["collect", 2], ["process", 1], ["analyse", 1]]) {
      await gotoView(view, pageUrl + "#/cs/V/path/" + step);
      await view.waitForFunction((id) => location.hash.endsWith("/" + id) && document.querySelector("#main h1"), step);
      const trainings = view.locator(".station-help .training");
      if ((await trainings.locator("a").count()) !== count || !(await trainings.textContent()).trim().startsWith("Školení k tomuto kroku")) fail(`training: the ${step} step does not list its ${count} training(s) in one line`);
    }
    if (await view.locator('.cards .card a[href*="eosc.cz/skoleni/"]').count()) fail("training: a training shows as a resource card as well");
    await gotoView(view, pageUrl + "#/cs/V/path/metadata");
    await view.waitForSelector("#main h1");
    await view.locator(".callout-verify-identifiers summary").click();
    const steps = await view.locator(".callout-verify-identifiers ol li").allTextContents();
    if (!steps[0].includes("Ověřit identifikátory") || !steps[1].includes("skript")) fail("identifier callout: it does not lead with the helper and a script: " + steps.slice(0, 2).join(" | "));
    await gotoView(view, pageUrl + "#/cs/V/page/about");
    /* A hash change keeps the previous view until the about page's parts arrive; wait for the link itself. */
    const courses = await view.waitForSelector('a.text-ref[href$="/catalogue/res/course/training-overview"]', { timeout: 10000 }).catch(() => null);
    if (!courses) fail("about: the introductory courses are not linked");
    await open("#/cs/V/catalogue/repositories");
    for (const name of ["Dryad", "Harvard Dataverse", "Molecular Biophysics Database (MBDB)"]) {
      if (!(await view.locator(".catalogue-results .card h3", { hasText: name }).count())) fail("repositories: " + name + " is not listed");
    }

    // Exports: every view but a single check offers printing under it, and its content as data where it has a record
    // in the API; the whole crate is on the page for machines. The catalogue saves the filtered list it shows as CSV
    // and as data, a station saves itself as Markdown, and printing opens closed sections.
    const exportIds = async () => view.evaluate(() => [...document.querySelectorAll(".export-bar .export-actions > *")].map((node) => node.id).join(","));
    const exportData = async () => view.evaluate(() => (document.getElementById("export-data") || {}).getAttribute?.("href") || "");
    for (const [hash, expected, record] of [
      ["#/cs/V/path/start", "export-print"],
      ["#/cs/V/explorer", "export-print"],
      ["#/cs/V/page/about", "export-print"],
      ["#/cs/V/tools", "export-print"],
      ["#/cs/V/check", "export-data,export-print", "api/checks.json"],
      ["#/cs/V/explorer/R1.1", "export-data,export-print", "api/pr/R1.1.json"],
      ["#/cs/V/path/licence", "export-markdown,export-data,export-print", "api/step/licence.json"],
    ]) {
      await gotoView(view, pageUrl + hash);
      await view.waitForSelector("#main h1");
      if ((await exportIds()) !== expected) fail(`exports: ${hash} offers ${await exportIds()} instead of ${expected}`);
      if (record && ((await exportData()) !== record || !existsSync(resolve(root, "_site", record)))) fail(`exports: ${hash} does not offer its record ${record} as data, or it is not built`);
    }
    await gotoView(view, pageUrl + "#/cs/V/path/licence");
    await view.waitForSelector("#main h1");
    if (!(await view.locator('a[href="#/cs/V/catalogue/k!actions~s!licence"]').count())) fail("paradata: the station does not lead to its changes in the catalogue");
    await gotoView(view, pageUrl + "#/cs/V/check/dataset");
    await view.waitForSelector("#main h1");
    if (await view.locator(".export-bar").count()) fail("exports: a single check shows the shared export bar beside its own exports");
    await gotoView(view, pageUrl + "#/cs/DS/check/institution/report");
    await view.waitForSelector("#export-data");
    if ((await view.locator("#export-data").getAttribute("href")) !== "api/check/institution.json") fail("exports: a single check does not offer its benchmark record as data");
    const saved = async (id) => {
      const [download] = await Promise.all([view.waitForEvent("download"), view.locator("#export-" + id).click()]);
      return { name: download.suggestedFilename(), text: readFileSync(await download.path(), "utf8") };
    };
    await open("#/en/V/catalogue/k!resources~s!licence");
    const listed = await found();
    const csv = await saved("csv");
    const csvRows = csv.text.replace(/^\ufeff/, "").trim().split("\r\n");
    if (!csvRows[0].includes("Record in the API")) fail("exports: the CSV does not carry each entry's record");
    if (!/^fair-guide-catalogue-resources-\d{4}-\d{2}-\d{2}\.csv$/.test(csv.name) || !csvRows[0].startsWith("Identifier,Name,") || !csvRows[0].includes("Address") || !csvRows[0].includes("Status")) fail("exports: the CSV is not named or headed as expected: " + csv.name + " " + csvRows[0]);
    if (csvRows.length - 1 !== listed || !csvRows.slice(1).every((row) => row.includes("https://"))) fail(`exports: the CSV does not hold exactly the ${listed} filtered entries with their addresses (${csvRows.length - 1} rows)`);
    const json = JSON.parse((await saved("json")).text);
    // The list as data has the shape of the API's lists; each entry names its record at the page's address, which for a
    // local file is the configured one and maps onto the built site.
    const configured = await view.evaluate(() => window.FairGuide.config.pageUrl);
    const inBuilt = (id) => String(id).startsWith(configured) && existsSync(resolve(root, "_site", String(id).slice(configured.length)));
    if (json["@type"] !== "ItemList" || json.numberOfItems !== listed || json.itemListElement.length !== listed || !String(json["@id"]).includes("s!licence") || !String(json["@context"]).endsWith("api/context.jsonld")) fail("exports: the list as data is not an ItemList of the filtered entries naming its filters");
    if (!json.itemListElement.every((item) => item.identifier && item.name && inBuilt(item["@id"]))) fail("exports: an entry of the list as data does not name its record in the API");
    await gotoView(view, pageUrl + "#/en/DS/path/licence");
    await view.waitForSelector("#main h1");
    const markdown = await saved("markdown");
    if (!markdown.name.startsWith("fair-guide-station-licence-DS-en-") || !markdown.text.startsWith("# Licence and access") || !markdown.text.includes("\n## How to do it\n") || !markdown.text.includes("#/en/DS/path/licence")) fail("exports: the station's Markdown lacks its title, levels or address: " + markdown.name);
    if (/\n\n\n/.test(markdown.text)) fail("exports: the station's Markdown has empty runs of lines");
    if (!markdown.text.includes("\n  What to check: ") || !markdown.text.includes("\n  ```text\n") || !markdown.text.includes("Always verify what AI produces.")) fail("exports: the station's Markdown lacks an AI tip's check, prompt or reminder");
    // Copying a prompt: the button says it copied, or, where the clipboard is refused, the prompt is selected.
    await view.evaluate(() => { document.querySelector('#main details[data-key="ai"]').open = true; });
    const prompt = view.locator("#main .ai-prompt").first();
    await prompt.locator("button").click();
    await view.waitForTimeout(100);
    const copied = await prompt.evaluate((block) => ({ label: block.querySelector(".copy-label").textContent, selected: window.getSelection().toString().trim(), text: block.querySelector("pre").textContent.trim() }));
    if (copied.label !== "Copied" && copied.selected !== copied.text) fail(`exports: copying a prompt neither copies nor selects it (${copied.label})`);
    const closed = await view.locator("#main details:not([open])").count();
    await view.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
    if (!closed || (await view.locator("#main details:not([open])").count())) fail("exports: printing does not open the closed sections");
    await view.evaluate(() => window.dispatchEvent(new Event("afterprint")));
    if ((await view.locator("#main details:not([open])").count()) !== closed) fail("exports: the sections opened for printing do not close again");

    // Links from text: a step that names DataCite links the name to its catalogue entry, quietly, and the crate
    // records DataCite as mentioned by the step, with no markup in the text.
    await gotoView(view, pageUrl + "#/cs/V/path/findability");
    await view.waitForSelector("#main h1");
    await view.locator('details[data-key="L1"] > summary').click();
    const named = view.locator('details[data-key="L1"] a.text-ref', { hasText: "DataCite" }).first();
    if (!(await named.count()) || !(await named.getAttribute("href")).endsWith("/catalogue/res/srv/datacite")) fail("text links: DataCite in a step does not link to its catalogue entry");
    const quiet = await named.evaluate((link) => getComputedStyle(link).color === getComputedStyle(link.parentElement).color && getComputedStyle(link).textDecorationStyle === "dotted");
    if (!quiet) fail("text links: a link in text does not keep the text's colour with a dotted underline");
    const step = crate["@graph"].find((entity) => entity["@id"] === "#advice-findability.04-step-3");
    if (!step || JSON.stringify(step.text).includes("[[") || !JSON.stringify(step.mentions).includes("#resource-datacite")) fail("text links: the crate does not record DataCite as mentioned by the step with clean text");
    if (JSON.stringify(crate).includes("[[")) fail("text links: reference markup reached the crate");
    await watchJump(view, "datacite");
    await named.click();
    await view.waitForSelector("[id=\"item-srv/datacite\"]");
    await view.waitForFunction(() => window.__jumpMarked === true, null, { timeout: 30000 });

    await gotoView(view, pageUrl + "#/cs/V/page/machines");
    await view.waitForSelector("#main h1");
    // The page sits in the header: its button is marked while it is open, no main-menu item is, and the header also
    // links the source repository.
    if (await view.locator('.main-nav [aria-current="page"]').count()) fail("machines: a main-menu item is marked although the page sits in the header");
    if ((await view.locator('.site-header a.header-page[aria-current="page"]').textContent()).trim() !== "Data pro stroje") fail("machines: the header's button is not marked while the page is open");
    if (!(await view.locator('.site-header a.header-repository[href^="https://github.com/"]').count())) fail("header: the source repository is not linked");
    if (!(await view.locator('.machine-tasks a[href="ro-crate-metadata.json"]').count())) fail("machines: the page does not offer the knowledge base");
    // A data steward who wants one record finds its address pattern and a working example, and how the guide itself
    // uses the same means: its signposts, read from the same list as the head and the linkset.
    const example = await view.locator(".machine-tasks a[href$='pr/R1.1.json']").getAttribute("href");
    if (!example || !existsSync(resolve(root, "_site", example)) || !(await view.locator(".machine-tasks code", { hasText: "<id>.json" }).count())) fail("machines: the task table does not show a record's pattern and a working example");
    // The page offers every machine-facing surface the Guide publishes, one row each with its description, so
    // nothing important is missing (crate, profile, vocabulary, record, service, health, tests, harvest,
    // requirements, result, list).
    const taskRows = await view.locator(".machine-tasks tbody tr").count();
    if (taskRows !== 11) fail("machines: the task table offers " + taskRows + " surfaces, expected 11 (crate, profile, vocabulary, record, service, health, tests, harvest, requirements, result, list)");
    const shown = await view.locator(".signposts tbody tr").evaluateAll((rows) => rows.map((row) => row.querySelector("code").textContent + " " + row.querySelector("td a").getAttribute("href")).sort());
    const head = await view.locator("head link[rel]").evaluateAll((links) => links.filter((link) => !["stylesheet", "icon", "apple-touch-icon"].includes(link.rel)).map((link) => link.getAttribute("rel") + " " + link.getAttribute("href")).sort());
    if (shown.join("|") !== head.join("|")) fail("machines: the signposts the page shows differ from the head's: " + shown.join(", ") + " vs " + head.join(", "));
    const linkset = JSON.parse(readFileSync(resolve(site, "linkset.json"), "utf8")).linkset[0];
    const listed2 = Object.entries(linkset).filter(([rel]) => rel !== "anchor").flatMap(([rel, targets]) => targets.map((target) => rel + " " + target.href));
    if (linkset.anchor !== "./" || listed2.sort().join("|") !== head.filter((link) => !link.startsWith("linkset ")).join("|")) fail("signposting: the linkset does not list the head's links, anchored at the site");
    // The standards the knowledge base follows are linked: RO-Crate and Process Run Crate to their catalogue entries,
    // the guide's profile to its landing page at its own address, which the build writes so the identifier resolves.
    const practice = view.locator("#practice");
    for (const id of ["ro-crate", "process-run-crate"]) {
      if (!(await practice.locator(`a.text-ref[href$="${cataloguePath("resources", id)}"]`).count())) fail(`machines: the practice section does not link ${id} to its catalogue entry`);
    }
    const profileHref = await practice.locator('a.text-ref[href^="profile/"]').getAttribute("href");
    if (!profileHref || !existsSync(resolve(site, profileHref, "index.html"))) fail("machines: the guide's profile is not linked to its landing page: " + profileHref);
    for (const rel of ["describedby", "service-desc", "service-doc", "license", "type", "author", "linkset"]) {
      if (!head.some((link) => link.startsWith(rel + " "))) fail("signposting: the head has no " + rel + " link");
    }
    if (!(await view.locator('head link[rel="describedby"][href="ro-crate-metadata.json"]').count())) fail("machines: the head does not carry the describedby link");
    // The API (built into _site/ by scripts/build_site.py): typed links in the head lead to its description and its
    // documentation, and the page lists every collection as an accessible counterpart of the documentation.
    const inSite = (href) => Boolean(href) && !/^[a-z]+:/i.test(href) && existsSync(resolve(site, href.endsWith("/") ? href + "index.html" : href));
    for (const rel of ["service-desc", "service-doc"]) {
      const href = await view.locator(`head link[rel="${rel}"]`).getAttribute("href");
      if (!inSite(href)) fail(`machines: the ${rel} link does not lead to the built API: ${href}`);
    }
    const endpoints = await view.locator(".endpoints tbody td:first-of-type a").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    const expectedEndpoints = await view.evaluate(() => {
      const api = window.FairGuide.config.api;
      return [...api.collections.map((collection) => api.files.record.replace("{record}", collection)), api.files.meta, api.files.context, api.files.health];
    });
    if (endpoints.slice().sort().join("|") !== expectedEndpoints.sort().join("|") || !endpoints.every(inSite)) fail("machines: the endpoint list does not name every collection of the built API: " + endpoints.join(" "));
    // The crate's HTML preview is the guide page: opened as the preview it shows the machine-readable data, not the
    // path landing, so a reader following the crate's preview link sees the crate, not an unrelated view.
    await view.goto(new URL("ro-crate-preview.html", pageUrl).href);
    await view.waitForSelector("#main h1");
    if ((await view.locator("#main h1").textContent()).trim() !== "Data pro stroje" || !(await view.locator(".machine-tasks").count())) fail("machines: the crate preview does not open the machine-readable data");
    // The vocabulary page anchors every term, so its IRI (<address>terms#<term>) opens its own row, and lists them all.
    const turtle = readFileSync(resolve(site, "terms/fair-guide.ttl"), "utf8");
    const termCount = (turtle.match(/ a rdf:Property ;/g) || []).length;
    await view.goto(new URL("terms/index.html", pageUrl).href);
    await view.waitForSelector("main .detail-entry");
    const anchors = await view.locator("main .detail-entry[id]").evaluateAll((rows) => rows.map((row) => row.id));
    if (!termCount || anchors.length !== termCount) fail(`vocabulary: the page anchors ${anchors.length} terms, the Turtle defines ${termCount}`);
    if (!anchors.includes("guidance")) fail("vocabulary: a term is not anchored by its own id");
    // Every catalogue entry links to its record in the API; the NKR samples are illustrations, not entries.
    for (const kind of ["resources", "repositories", "infrastructures", "clauses", "questions", "terms", "fips", "tests", "actions"]) {
      await gotoView(view, pageUrl + "#/cs/V/catalogue/" + kind);
      await view.waitForFunction((id) => { const radio = document.getElementById(id); return radio && radio.checked && document.querySelector(".catalogue .card"); }, "facet-kind-" + kind);
      const unlinked = await view.locator(".catalogue .card").evaluateAll((cards) => cards.filter((card) => !card.querySelector(".json-link")).map((card) => card.id || card.textContent.trim().slice(0, 40)));
      const records = await view.locator(".catalogue .card .json-link").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
      if (unlinked.length || !records.every(inSite)) fail(`catalogue: ${kind} entries without a record in the API, or a link that leads nowhere: ${unlinked.join(", ")}`);
      const corner = await view.locator(".catalogue .card .json-link").first().evaluate((link) => {
        const box = link.getBoundingClientRect();
        const card = link.closest(".card").getBoundingClientRect();
        return box.top - card.top < 40 && card.right - box.right < 40;
      });
      if (!corner) fail(`catalogue: the ${kind} record link does not sit in the card's top right corner`);
      // One card for every kind: its own identifier in the head, and its relations under fixed labels in one order.
      const order = ["Principy", "Pro koho", "Provozovatel", "Vyvinuli", "Provozuje", "Národní uzel", "Členství v ERIC", "Profil FIP komunity", "Vychází z", "V Průvodci", "Identifikátory", "Vrstvy implementace", "Návaznosti"];
      const cards = await view.locator(".catalogue .card").evaluateAll((all) =>
        all.map((card) => ({ id: card.id, chip: (card.querySelector(".entry-head .id-chip") || {}).textContent, labels: [...card.querySelectorAll(".relations dt")].map((dt) => dt.textContent) }))
      );
      const wrong = cards.filter((card) => card.chip !== card.id.split("/").at(-1).replace(/^item-/, "") || card.labels.some((label, index) => !order.includes(label) || (index && order.indexOf(label) <= order.indexOf(card.labels[index - 1]))));
      if (wrong.length) fail(`catalogue: ${kind} cards without their own identifier in the head, or with relations out of order: ` + wrong.slice(0, 3).map((card) => card.id + " " + card.labels.join("/")).join("; "));
    }
    // An entry shows the persistent identifiers it has, named by scheme, and none it lacks; the stations and checks
    // an entry names carry their icons.
    const pidsOf = async (hash, anchor) => {
      await gotoView(view, pageUrl + hash);
      await view.waitForSelector(`[id="item-${entryAnchor(anchor)}"]`);
      return view.locator(`[id="item-${entryAnchor(anchor)}"]`).evaluate((card) => ({
        pids: [...card.querySelectorAll(".pid-chip")].map((link) => [link.querySelector(".pid-scheme")?.textContent, link.getAttribute("href"), link.textContent.replace(link.querySelector(".pid-scheme")?.textContent || "", "").replace(/\s*\(.*\)$/, "").trim()]),
        plainIcons: [...card.querySelectorAll(".relations a.holder-link")].filter((link) => !link.querySelector("svg.icon")).length,
        holders: card.querySelectorAll(".relations a.holder-link").length,
      }));
    };
    const roCrate = await pidsOf("#/cs/DS/catalogue/k!resources~q!crate", "ro-crate");
    if (!roCrate.pids.some(([scheme, href, text]) => scheme === "DOI" && href === "https://doi.org/10.5281/zenodo.13751027" && text === href)) fail("catalogue: RO-Crate does not show its DOI in full: " + JSON.stringify(roCrate.pids));
    if (!roCrate.holders || roCrate.plainIcons) fail("catalogue: a station an entry names lacks its icon");
    const zenodo = await pidsOf("#/cs/V/catalogue/k!repositories~q!zenodo", "zenodo");
    if (!zenodo.pids.some(([scheme, href]) => scheme === "re3data" && href.endsWith("/r3d100010468"))) fail("catalogue: Zenodo does not show its re3data identifier: " + JSON.stringify(zenodo.pids));
    // One real-world thing is one entry: Zenodo's FIP Dashboard record is shown with the curated repository, not on
    // its own, and the borrowed identifiers of its records lead to it from either kind.
    if (!zenodo.pids.some(([, href]) => href.endsWith("/resources/zenodo"))) fail("catalogue: Zenodo does not show its FIP Dashboard record: " + JSON.stringify(zenodo.pids));
    await gotoView(view, pageUrl + "#/cs/V/catalogue/k!resources~q!zenodo");
    await view.waitForSelector(".catalogue-results");
    if (await view.locator('[id="item-gen/zenodo"]').count()) fail("catalogue: Zenodo's FIP Dashboard record is listed apart from the repository");
    await gotoView(view, pageUrl + "#/cs/V/catalogue/repo/gen/zenodo");
    await view.waitForSelector('[id="item-gen/zenodo"]');
    if ((await view.locator(".catalogue-results .card").count()) !== 1) fail("catalogue: Zenodo does not have one canonical entry");
    // Source records enrich the one canonical entry; external IDs remain metadata.
    for (const lang of ["cs", "en"]) {
      await gotoView(view, pageUrl + `#/${lang}/V/catalogue/k!resources`);
      await view.waitForSelector(".catalogue-results");
      const kindPosition = await view.locator('[data-facet="kind"]').evaluate((facet) => [...facet.parentElement.children].indexOf(facet));
      await view.locator("#facet-kind-repositories").check();
      await view.waitForFunction(() => location.hash.includes("k!repositories"));
      await view.waitForSelector(".catalogue-results");
      if ((await view.locator('[data-facet="kind"]').evaluate((facet) => [...facet.parentElement.children].indexOf(facet))) !== kindPosition) fail(`catalogue: switching to repositories changes the kind picker's position (${lang})`);
      const purposeInSection = await view.locator('[data-facet="repositories-rfunction"]').evaluate((facet) => {
        const kind = document.querySelector('[data-facet="kind"]');
        const section = facet.closest(".facet-kind");
        return kind && section && section.querySelector(".facet-kind-name") && !!(kind.compareDocumentPosition(facet) & Node.DOCUMENT_POSITION_FOLLOWING) && section.querySelector("fieldset") === facet;
      });
      if (!purposeInSection) fail("repositories and registries: task choices are outside the family section or reorder the kind picker");
      for (const id of ["nma", "fairsharing", "fip-dashboard.nusl", "fip-dashboard.nrp-invenio", "re3data.r3d100014032", "re3data.r3d100010386"]) {
        if ((await view.locator(`[id="item-${entryAnchor(id)}"]`).count()) !== 1) fail(`catalogue: ${id} is not listed once among repositories and registries (${lang})`);
      }
      for (const id of ["asep-arl", "clarin-dspace"]) {
        if (await view.locator(`[id="item-fip-dashboard.${id}"]`).count()) fail(`catalogue: ${id} is listed apart from its reviewed re3data match`);
      }
      for (const target of ["nma", "fairsharing", "re3data.r3d100014032", "re3data.r3d100010386"]) {
        await gotoView(view, pageUrl + `#/${lang}/V${cataloguePath("repositories", target)}`);
        await view.waitForSelector(`[id="item-${entryAnchor(target)}"]`);
        if ((await view.locator(".catalogue-results .card").count()) !== 1) fail(`catalogue: ${target} does not open its single joined entry`);
      }
      await gotoView(view, pageUrl + `#/${lang}/V/path/repository`);
      await view.waitForSelector(".now-actions");
      const chooser = view.locator('.now-actions a[href*="f.rfunction"]');
      if (!(await chooser.count())) fail("repository chooser: no function filter on the action");
      else await chooser.first().click();
      await view.waitForSelector(".catalogue-results");
      for (const id of ["zenodo", "mbdb", "re3data.r3d100014032"]) {
        if (!(await view.locator(`[id="item-${entryAnchor(id)}"]`).count())) fail(`repository chooser: data destination ${id} is missing`);
      }
      for (const id of ["nma", "fairsharing", "fip-dashboard.nusl"]) {
        if (await view.locator(`[id="item-${entryAnchor(id)}"]`).count()) fail(`repository chooser: ${id} is presented as a data deposit destination`);
      }
      await gotoView(view, pageUrl + `#/${lang}/V/catalogue/k!repositories~f.rfunction!%23rfunction-deposit-publications`);
      await view.waitForSelector(".catalogue-results");
      for (const id of ["zenodo", "re3data.r3d100014032", "fip-dashboard.nusl"]) {
        if (!(await view.locator(`[id="item-${entryAnchor(id)}"]`).count())) fail(`publication filter: ${id} is missing`);
      }
      if (await view.locator('[id="item-dom/mbdb"]').count()) fail("publication filter: a data-only repository is included");
      if (!(await view.locator(".kind-intro .notice").count())) fail("repositories and registries: the dashboard's demo disclaimer is missing");
    }
    const datacite = await pidsOf("#/cs/V/catalogue/k!resources~q!DataCite", "datacite");
    if (!datacite.pids.some(([scheme, href, text]) => scheme === "Nanopublikace" && href.startsWith("https://purl.org/np/") && text.startsWith("http://purl.org/np/"))) fail("catalogue: a nanopublication IRI is not shown as it is and linked over HTTPS: " + JSON.stringify(datacite.pids));
    const clause = await pidsOf("#/cs/V/catalogue/k!clauses~q!A.F1.N1", "A.F1.N1");
    if (clause.pids.length) fail("catalogue: a requirement shows a persistent identifier it does not have");
    // The accessibility statement names the API documentation as exempt and points to the accessible list.
    await gotoView(view, pageUrl + "#/cs/V/page/accessibility");
    await view.waitForSelector("#main h1");
    const exemption = view.locator("#main section", { hasText: "Swagger UI" });
    if (!(await exemption.count()) || !(await exemption.locator('a[href="#/cs/V/page/machines"]').count())) fail("accessibility: the statement does not name the API documentation and point to the endpoint list");
    // A block of "- " lines in page text is a list: the AI page's practice for agents, with its link kept.
    await gotoView(view, pageUrl + "#/en/V/page/ai");
    await view.waitForSelector("#main h1");
    const agentPractice = view.locator("#main section", { hasText: "When an AI agent does the work" }).locator("ul.text-list");
    if ((await agentPractice.locator("li").count()) < 8 || (await agentPractice.innerText()).includes("- ") || !(await agentPractice.locator("a.text-ref").count())) fail("ai page: the practice for agents is not a list of items with its link");
    // Each practice opens with its lead in bold, and the practice follows the rules directly.
    if ((await agentPractice.locator("li > strong:first-child").count()) !== (await agentPractice.locator("li").count())) fail("ai page: a practice for agents lacks its bold lead");
    const headings = await view.locator("#main article > section > h2").allTextContents();
    if (headings.indexOf("When an AI agent does the work") !== headings.indexOf("Three rules") + 1) fail("ai page: the practice for agents does not follow the rules: " + headings.join(" | "));
    const gathered = await view.evaluate(() => {
      const FG = window.FairGuide;
      const all = FG.stations().flatMap((station) => FG.refs(station, "itemListElement").filter((item) => item.adviceKind === "ai"));
      const forOne = all.filter((item) => FG.refIds(item, "audience").length < FG.lenses().length).length;
      const shown = [...document.querySelectorAll(".ai-station-tips .ai-tip")];
      return { all: all.length, forOne, shown: shown.length, tagged: shown.filter((tip) => tip.querySelector(".orientation .lens-tag")).length, prompts: shown.filter((tip) => tip.querySelector(".ai-prompt pre")).length };
    });
    if (!gathered.all || gathered.shown !== gathered.all || gathered.prompts !== gathered.all || gathered.tagged !== gathered.forOne) fail("ai page: the stations' AI tips are not all gathered with their prompts, or a tip for one view lacks its icon: " + JSON.stringify(gathered));
    const chat = view.locator('[id="cerit"] .section-action a');
    if (!(await chat.count()) || !(await chat.getAttribute("href")).startsWith("https://chat.ai.e-infra.cz") || (await chat.getAttribute("target")) !== "_blank") fail("ai page: the CERIT section does not lead to the e-INFRA CZ AI chat");
    // The start loads only its selected core language; About adds pages and its linked model records.
    const fresh = await context.newPage();
    await gotoView(fresh, pageUrl);
    await rendered(fresh);
    const startLanguage = await fresh.evaluate(() => window.FairGuide.state.lang);
    const atStart = await fresh.locator('script[src*="data/kb-"]').evaluateAll((scripts) => scripts.map((script) => script.getAttribute("src")));
    await navigationRendered(fresh, () => fresh.evaluate((lang) => { window.location.hash = `#/${lang}/V/page/about`; }, startLanguage));
    await fresh.waitForSelector('[id="why"]');
    const forPage = await fresh.locator('script[src*="data/kb-"]').evaluateAll((scripts) => scripts.map((script) => script.getAttribute("src")));
    if (atStart.join() !== `assets/data/kb-${startLanguage}.js` ||
        forPage.slice().sort().join() !== [`assets/data/kb-${startLanguage}.js`, "assets/data/kb-pages.js", `assets/data/kb-pages-${startLanguage}.js`, "assets/data/kb-model.js", `assets/data/kb-model-${startLanguage}.js`].sort().join()) {
      fail(`parts: the start loads ${atStart.join(", ")}; a page loads ${forPage.join(", ")}`);
    }
    await fresh.close();
    // The About page links the analysis the guide is built on, where it first names it.
    await gotoView(view, pageUrl + "#/cs/V/page/about");
    await view.waitForSelector("#main h1");
    const basis = view.locator("#main section").first().locator("a.text-ref", { hasText: "Analýzy a návrhu postupů" });
    if (!(await basis.count())) fail("about: the analysis the guide is built on is not linked where the page first names it");
    // CoreTrustSeal: one question per requirement in three blocks, each with the requirement's guidance as published;
    // a question with no FAIR principle has no empty row of tags.
    await navigationRendered(view, () => view.goto(pageUrl + "#/cs/SR/check/coretrustseal/answers"));
    const cts = await view.evaluate(() => {
      const items = [...document.querySelectorAll("#main fieldset")].filter((field) => /^\d\d\b/.test(field.querySelector("legend")?.textContent.trim() || ""));
      const guidance = [...document.querySelectorAll("#main details.item-basis details.clause-guidance .content")];
      const first = items.find((field) => field.querySelector("legend").textContent.trim().startsWith("01"));
      return { items: items.length, guidance: guidance.length, english: guidance.every((node) => node.lang === "en"), emptyTags: first ? first.querySelectorAll(".badges").length : -1 };
    });
    const ctsBlocks = await view.locator("#main .check-block > h2, #main section h2").allTextContents();
    if (cts.items !== 16 || cts.guidance !== 16 || !cts.english || cts.emptyTags !== 0) fail("coretrustseal: not sixteen questions each with English guidance, or an empty row of tags: " + JSON.stringify(cts));
    if (!["Organizační infrastruktura", "Správa digitálních objektů", "Informační technologie a bezpečnost"].every((name) => ctsBlocks.some((heading) => heading.includes(name)))) fail("coretrustseal: the questions are not in the three CoreTrustSeal areas: " + ctsBlocks.join(" | "));
    // A principle links the CoreTrustSeal requirements it relates to, and an analysis clause links the numbers it
    // names to the requirement they are about (the analysis's "R14", reuse, is R13 in the 2026-2028 edition).
    await gotoView(view, pageUrl + "#/cs/V/explorer/F2");
    await view.waitForSelector("#main h1");
    const ctsLinks = await view.locator('#main a[href*="catalogue/cl/CTS."]').evaluateAll((links) => links.map((link) => [link.textContent.trim(), decodeURIComponent(link.getAttribute("href"))]));
    if (!ctsLinks.some(([text, href]) => text.startsWith("R13") && href.endsWith("/CTS.R13"))) fail("explorer: F2 does not link its CoreTrustSeal requirements: " + JSON.stringify(ctsLinks));
    if (!ctsLinks.some(([text, href]) => text === "R14" && href.endsWith("/CTS.R13"))) fail("explorer: the analysis's R14 (reuse) does not lead to requirement R13: " + JSON.stringify(ctsLinks));
    // CDIF: the principle links its profiles, and the analysis's 2023 name "Discovery" leads to the Core profile.
    const cdifLinks = await view.locator('#main a[href*="catalogue/cl/CDIF."]').evaluateAll((links) => links.map((link) => [link.textContent.trim(), decodeURIComponent(link.getAttribute("href")).split("/").pop()]));
    if (!cdifLinks.some(([text, id]) => text === "Core" && id === "CDIF.Core") || !cdifLinks.some(([text, id]) => text === "Discovery" && id === "CDIF.Core")) fail("explorer: F2 does not link its CDIF profiles by meaning: " + JSON.stringify(cdifLinks));
    // The CDIF check: what the standard requires first, then the recommended elements, metadata management and the
    // profiles; the first tier is named for the standard, not for NRP or the analysis.
    await navigationRendered(view, () => view.goto(pageUrl + "#/cs/SR/check/cdif/answers"));
    const cdifQuestions = () => view.evaluate(() => [...document.querySelectorAll("#main fieldset legend")].filter((legend) => /^\d\d\b/.test(legend.textContent.trim())).length);
    const basicCount = await cdifQuestions();
    const tierSentence = await view.locator("#main .tier-info").innerText();
    await view.locator('label[for="extended-toggle"]').click();
    await view.waitForFunction(() => [...document.querySelectorAll("#main fieldset legend")].filter((legend) => /^\d\d\b/.test(legend.textContent.trim())).length > 9);
    const extendedCount = await cdifQuestions();
    if (basicCount !== 9 || extendedCount !== 35 || !tierSentence.startsWith("Povinné podle standardu (9")) fail(`cdif: ${basicCount} basic and ${extendedCount} extended questions, tier sentence "${tierSentence.slice(0, 60)}"`);
    await view.locator('label[for="extended-toggle"]').click();
    await view.close();
  }

  // Requirement identifiers resolve to the catalogue: a cited requirement shows its text, then its identifier as a chip
  // that leads to the catalogue entry, which is brought into view and marked, also when opened directly; the
  // catalogue lists the requirements by source, with a kind filter, and the check questions with their basis.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await gotoView(view, pageUrl + "#/cs/V/path/licence");
    await view.waitForSelector(".station");
    // The next step and one related tool, the second a quieter button.
    const nowActions = await view.locator(".now .now-actions a").evaluateAll((links) => links.map((link) => link.className));
    if (nowActions.length !== 2 || !nowActions[0].includes("button-primary") || !nowActions[1].includes("button-related")) fail("station: the next step is not followed by one quieter related tool: " + nowActions.join(" | "));
    // The accepted order: the key point under the title, then what to do now and the glossary terms before the
    // disclosures; callouts before the sources; then the resources, help and the pager. The reasons go straight to
    // what the advice rests on.
    const order = await view.locator(".station > *").evaluateAll((parts) => parts.map((part) => part.className || (part.dataset && part.dataset.key) || part.tagName.toLowerCase()));
    const expected = ["station-header", "key-point", "now", "station-terms", "L1", "L2", "ai", "callout", "L3", "provenance-line", "station-resources", "station-help", "pager"];
    const at = expected.map((name) => order.findIndex((part) => String(part).split(" ").includes(name)));
    if (at.some((index) => index < 0) || at.some((index, n) => n && index <= at[n - 1])) fail("station: the parts are not in the accepted order: " + order.join(" | "));
    if (!(await view.locator(".station > .key-point").textContent()).includes("Hlavní myšlenka")) fail("station: the key point is not set apart under the title");
    await view.locator('details[data-key="L1"] > summary').click();
    await view.locator('details[data-key="L2"] > summary').click();
    if (await view.locator('details[data-key="L2"] h3').count()) fail("station: Proč carries headings of its own (the principles, or what the advice rests on)");
    const entries = await view.locator('details[data-key="L2"] ul.clauses > li').count();
    const chips = await view.locator('details[data-key="L2"] ul.clauses > li a.id-chip').count();
    if (!entries || chips < entries - 1) fail(`ids: the cited requirements do not carry linked identifiers (${chips} of ${entries})`);
    if (await view.locator('details[data-key="L2"] ul.clauses > li > .clause-text .id-chip').count()) fail("ids: an identifier leads the requirement's text instead of following it");
    // A requirement shows one way wherever it is cited: its identifier once, its source by short name leading to the
    // source's catalogue entry. The station's terms lead to their catalogue entries, as terms in its text do.
    const cited = await view.locator('details[data-key="L2"] ul.clauses > li').evaluateAll((items) =>
      items.map((item) => ({ id: (item.querySelector(".id-chip") || {}).textContent, bold: (item.querySelector(".clause-title strong") || {}).textContent, source: item.querySelector("a.source-link") }))
    );
    if (cited.some((item) => item.id && item.bold === item.id)) fail("ids: a requirement shows its identifier twice under Proč");
    const analysisLink = view.locator('details[data-key="L2"] a.source-link', { hasText: "Analýza FAIR pro NRP/NDI" }).first();
    if (!(await analysisLink.count()) || !(await analysisLink.getAttribute("href")).endsWith("/catalogue/res/pub/analyza-fair-1.2")) fail("ids: a requirement's source is not named by its short name, leading to its catalogue entry");
    const termHrefs = await view.locator(".station-terms a.chip").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    if (!termHrefs.length || termHrefs.some((href) => !href.includes("/catalogue/term/") || href.includes("ntk."))) fail("ids: the station's terms do not lead to their catalogue entries: " + termHrefs.join(" "));
    // The explorer names a principle's relations in the catalogue's rows, and its requirements without doubled
    // identifiers.
    await gotoView(view, pageUrl + "#/cs/V/explorer/R1.1");
    await view.waitForSelector(".principle-relations");
    const relationLabels = await view.locator(".principle-relations dt").allTextContents();
    if (relationLabels.join("|") !== "FIP Dashboard|CoreTrustSeal|CDIF") fail("explorer: R1.1's relations are not the FIP Dashboard, CoreTrustSeal and CDIF rows: " + relationLabels.join("|"));
    if (await view.locator("ul.clauses > li").evaluateAll((items) => items.some((item) => (item.querySelector(".clause-title strong") || {}).textContent === (item.querySelector(".id-chip") || {}).textContent))) fail("explorer: a requirement shows its identifier twice");
    // An audience shows by icon and name.
    await gotoView(view, pageUrl + "#/cs/V/page/ai");
    /* The page's text arrives with its part; wait for the orientation itself rather than the first heading. */
    await view.waitForSelector(".orientation .lens-tag");
    const audienceNames = await view.locator(".orientation .lens-tag").allInnerTexts();
    if (!audienceNames.length || audienceNames.some((name) => !name.trim())) fail("ai page: an audience shows by icon alone");
    await gotoView(view, pageUrl + "#/cs/V/path/licence");
    await view.waitForSelector(".station");
    /* The station remembers that Proč was open; a click would close it. */
    if (!(await view.locator('details[data-key="L2"]').evaluate((details) => details.open))) await view.locator('details[data-key="L2"] > summary').click();
    const chip = view.locator('details[data-key="L2"] ul.clauses a.id-chip').first();
    const id = (await chip.textContent()).trim().replace(/^clauses\//, "");
    await watchJump(view, id);
    await chip.click();
    await view.waitForSelector(".catalogue-layout");
    await view.waitForFunction((expected) => document.activeElement && document.activeElement.id === "item-" + expected, id);
    if (!(await view.evaluate(() => window.__jumpMarked === true))) fail("ids: the catalogue entry is not marked when the identifier is followed");
    if (!(await view.locator("#facet-kind-clauses").isChecked())) fail("ids: the identifier does not select the requirements");
    await view.goto("about:blank");
    await gotoView(view, pageUrl + "#/cs/V/catalogue/cl/A.F1.N1");
    await view.waitForSelector('[id="item-A.F1.N1"]');
    const box = await view.locator('[id="item-A.F1.N1"]').boundingBox();
    if (!box || box.y < 0 || box.y > 900) fail("ids: a directly opened link to a requirement does not bring it into view");
    // A link to one entry shows that entry alone, says so, and leads to the whole kind.
    if ((await view.locator(".clause-card").count()) !== 1 || !(await view.locator(".single-entry").count())) fail("ids: a link to one requirement does not show it alone with a notice");
    await view.locator(".single-entry a").click();
    await view.waitForFunction(() => document.querySelectorAll(".clause-card").length > 1);
    const all = Number((await view.locator(".catalogue-count").textContent()).match(/\d+/)[0]);
    await view.locator("#facet-clauses-ckind-recommendation").check();
    await view.waitForFunction(() => location.hash.includes("f.ckind!recommendation"));
    const recommendations = Number((await view.locator(".catalogue-count").textContent()).match(/\d+/)[0]);
    if (!(recommendations > 0 && recommendations < all)) fail("ids: the kind filter does not narrow the requirements");
    await gotoView(view, pageUrl + "#/cs/V/catalogue/q/maturity.18");
    await view.waitForSelector('[id="item-maturity.18"]');
    if (!(await view.locator('[id="item-maturity.18"] a.id-chip').count())) fail("ids: a check question does not link the requirements it rests on");
    await view.close();
  }

  // Every page sits under a menu item: the tools view lists the helpers and the AI page, and its item stays current
  // on each of them; the about item covers the about page and the accessibility statement.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const current = async () => (await view.locator('.main-nav [aria-current="page"]').textContent()).trim();
    await gotoView(view, pageUrl + "#/cs/V/tools");
    await view.waitForSelector(".tool-cards");
    if ((await current()) !== "Nástroje a postupy") fail("tools: the menu does not mark the tools item on the tools view");
    const tools = await view.locator(".tool-card h3 a").evaluateAll((links) => links.map((link) => link.getAttribute("href").split("/").pop()));
    if (tools.join(",") !== "live-check,identifiers,citation,model,ai,software,notebooks,provenance,fdo,licence-compatibility") fail("tools: the tools view does not list interactive tools before guidance: " + tools.join(","));
    if ((await view.locator(".tool-group").count()) !== 2) fail("tools: interactive tools and guidance are not separate groups");
    if ((await view.locator(".tool-coming").count()) !== 0) fail("tools: implemented helpers are still marked as in preparation");
    for (const [id, item] of [["identifiers", "Nástroje a postupy"], ["ai", "Nástroje a postupy"], ["live-check", "Nástroje a postupy"], ["citation", "Nástroje a postupy"], ["about", "O Průvodci"], ["accessibility", "O Průvodci"]]) {
      await gotoView(view, pageUrl + "#/cs/V/page/" + id);
      // A hash change keeps the previous view's heading until the new view renders: wait for the route, not a heading.
      await view.waitForFunction((page) => location.hash.endsWith("/page/" + page) && document.querySelector(`#main [data-page="${page}"], #main h1`), id);
      await view.waitForFunction((expected) => document.querySelector('.main-nav [aria-current="page"]')?.textContent.trim() === expected, item, { timeout: 5000 }).catch(() => {});
      if ((await current()) !== item) fail(`page ${id}: the menu does not mark ${item}`);
    }
    await view.close();
  }

  // FAIRsharing records join repositories at build time and appear as identifier chips with a catalogue source.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await gotoView(view, pageUrl + "#/cs/V/catalogue/repo/dom/csda");
    await view.waitForSelector(".catalogue-results .entry-card");
    if (await view.locator("#fairsharing-load").count()) fail("repositories: FAIRsharing still offers an on-demand load");
    const card = view.locator(".catalogue-results .entry-card");
    const record = card.locator('.pid-chip[href="https://doi.org/10.25504/FAIRsharing.f4bfb1"]');
    if (!(await record.count()) || !(await record.locator(".pid-scheme").textContent()).includes("FAIRsharing")) fail("repositories: the snapshot's FAIRsharing record is not an identifier chip on its repository");
    if (!(await card.locator('.relations a[href$="/catalogue/repo/reg/fairsharing"]').count())) fail("repositories: the FAIRsharing source does not lead to its catalogue entry");
    await view.close();
  }

  // Visual rules from the visual pass: cards keep even padding; the explorer shows an overview before a principle is
  // chosen; a helper page says when its helper is not there yet; on a phone the language switch shares the logo's row.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await gotoView(view, pageUrl + "#/cs/V/catalogue/k!resources");
    await view.waitForSelector(".cards .card");
    const gap = await view.locator(".cards .card").first().evaluate((card) => {
      const last = card.lastElementChild.getBoundingClientRect();
      const box = card.getBoundingClientRect();
      return { bottom: Math.round(box.bottom - last.bottom), top: Math.round(card.firstElementChild.getBoundingClientRect().top - box.top) };
    });
    if (Math.abs(gap.bottom - gap.top) > 4) fail("cards: the space below the content differs from the space above it: " + JSON.stringify(gap));
    await gotoView(view, pageUrl + "#/cs/V/explorer");
    await view.waitForSelector("#main h1");
    const rows = await view.locator(".explorer-overview tbody tr").count();
    const caption = await view.locator(".explorer-overview caption").textContent().catch(() => "");
    if (rows !== 4 || !/^\d+ požadav/.test(caption)) fail("explorer: no overview of the requirements before a principle is chosen: " + caption);
    for (const [id, expected] of [["identifiers", false], ["citation", false], ["live-check", false], ["about", false]]) {
      await gotoView(view, pageUrl + "#/cs/V/page/" + id);
      await view.waitForSelector("#main h1");
      const coming = await view.locator(".helper-coming").count();
      if (Boolean(coming) !== expected) fail(`page ${id}: the note that the helper is coming is ${coming ? "shown" : "missing"}`);
    }
    await view.setViewportSize({ width: 390, height: 800 });
    await gotoView(view, pageUrl + "#/cs/V/page/about");
    await view.waitForSelector("#main h1");
    const logo = await view.locator(".brand > a").first().boundingBox();
    const language = await view.locator(".site-header .header-lang").boundingBox();
    if (language.y > logo.y + logo.height) fail("header: on a phone the language switch takes a row of its own");
    await view.close();
  }

  // Keyboard: the skip link, lens picker, language switch, search and the journey's stages are reachable with Tab.
  const reached = new Set();
  for (let i = 0; i < 30; i += 1) {
    await page.keyboard.press("Tab");
    reached.add(await page.evaluate(() => {
      const el = document.activeElement;
      return el ? (el.id || el.className || el.tagName) + ":" + (el.textContent || "").trim().slice(0, 40) : "";
    }));
  }
  const joined = [...reached].join(" | ");
  for (const expected of ["skip-link", "lens-option", "English", "search-input", "journey-stage:1Plánování"]) {
    if (!joined.includes(expected)) fail("keyboard does not reach: " + expected);
  }

  // Universal search: terms are found locally while typing, in both languages and without diacritics, and hand
  // over to the catalogue; identifiers are routed by what they denote once the search is confirmed, the guide's own
  // identifiers while typing; nothing is sent while searching.
  const typeQuery = async (text) => {
    await page.fill("#search-input", "");
    await page.locator("#search-input").pressSequentially(text);
    await searchReady(page, text);
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
  if (!(await page.locator("#search-results .result-primary").getAttribute("href")).endsWith("/catalogue/cl/A.F1.N1")) fail("search: a requirement identifier does not lead to its catalogue entry while typing");
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
  if (!(await page.locator("#search-results .result-primary").getAttribute("href")).endsWith("/citation/10.1038%2Fsdata.2016.18")) fail("search: the citation handoff loses the DOI");
  if (!said.includes("Jde o publikaci") || !(await primary()).includes("Vytvořit citaci")) fail("search: a Crossref DOI does not lead to the citation: " + said);

  // A re3data identifier opens the maturity check filled in from the snapshot.
  await page.evaluate(() => { window.FairGuide.live.findFairsharing = async () => []; });
  await search("r3d100010386");
  await page.locator("#search-results .result-primary").click();
  await page.waitForFunction(() => location.hash.endsWith("/check/maturity") && document.getElementById("prefill-status") && document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await page.locator(".target-card").textContent()).includes("LINDAT")) fail("search: the maturity check from a re3data identifier does not say which repository it is");
  await gotoView(page, pageUrl);
  await rendered(page);

  // Task shortcuts change with the lens, chosen in the band under the main menu.
  if ((await page.locator(".lens-band .lens-option").count()) !== 4) fail("lens band: four options are not shown on the landing");
  if ((await page.locator('.lens-option[aria-current="true"]').getAttribute("data-lens")) !== "V") fail("lens band: the current lens is not marked");
  if ((await page.locator('.lens-option[data-lens="SR"]').getAttribute("href")) !== "#/cs/SR/path/start") fail("lens band: an option is not a shareable link");
  await page.locator('.lens-option[data-lens="SR"]').click();
  await lensShown(page, "SR");
  if (!(await page.locator(".tasks").textContent()).includes("podmínky NRP")) fail("landing: the repository administrator's tasks are missing");
  await context.close();
}]);

// 2. Every station in every lens and language, then the other views.
for (let shard = 0; shard < 4; shard++) sections.push([`views:${shard + 1}`, async () => {
  const views = [];
  for (const lang of ["cs", "en"]) {
    // Station states belong to station_matrix.mjs, executed by the final-candidate sweep.
    for (const view of ["explorer", "catalogue", "tools", "selfcheck"]) views.push(`#/${lang}/V/${view}`);
    for (const tab of ["sources", "terms", "fips", "tests", "lifecycle", "life/rdm/reuse", "k!resources~f.use!knav", "res/tool/archaeological-information-system", "actions"]) views.push(`#/${lang}/V/catalogue/${tab}`);
    for (const check of checks) views.push(`#/${lang}/${check.lens}/check/${check.id}`);
    for (const principle of principles.slice(0, 3)) views.push(`#/${lang}/K/explorer/${principle}`);
    for (const id of pages) views.push(`#/${lang}/V/page/${id}`);
  }
  // This section owns one worker; nested work must not multiply the shared browser budget.
  const assigned = views.filter((_, index) => index % 4 === shard);
  await checkViews(assigned);
  console.log(`checked ${assigned.length} views (shard ${shard + 1}/4 of ${views.length})`);
}]);

/** Open the guide in one page and check each view in turn. */
async function checkViews(views) {
  const { context, page, external, problems } = await openPage();
  await gotoView(page, pageUrl);
  await rendered(page);
  for (const hash of views) {
    await page.evaluate((value) => { document.getElementById("main").dataset.previousView = "true"; window.location.hash = value; }, hash);
    await page.waitForFunction((value) => window.location.hash === value && document.querySelector("#main h1") && !document.getElementById("main").dataset.previousView, hash);
    const headingText = (await page.textContent("#main h1")).trim();
    if (!headingText) fail(`${hash}: the main heading is empty`);
    const lang = await page.evaluate(() => document.documentElement.lang);
    if (lang !== hash.split("/")[1]) fail(`${hash}: html lang is ${lang}`);
    await axe(page, hash);
    // The page shell holds elements only; a view part that is absent leaves no stray text.
    if (await page.evaluate(() => [...document.getElementById("app").childNodes].some((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim()))) fail(`${hash}: stray text in the page shell`);
    // No value reaches the page unformatted.
    const shown = await page.locator("#app").innerText();
    if (/\[object Object\]|\bundefined\b/.test(shown)) fail(`${hash}: an unformatted value is shown`);
    // No interface string is shown as its key, as when a language lacks it.
    const rawKeys = (shown.match(/\b[a-z][a-zA-Z]*(?:\.[a-zA-Z][\w-]*)+\b/g) || []).filter(isUiKey);
    if (rawKeys.length) fail(`${hash}: interface keys shown instead of text: ${[...new Set(rawKeys)].slice(0, 5).join(", ")}`);
    // No link leads back to the start because its address was refused.
    if (await page.locator('#app a[href="#"]').count()) fail(`${hash}: a link that leads nowhere (href="#")`);
    // Every external link opens in a new tab.
    const sameTab = await page.evaluate(() => [...document.querySelectorAll('a[href^="http"]')].filter((link) => link.target !== "_blank" || !/noopener/.test(link.rel)).map((link) => link.href));
    if (sameTab.length) fail(`${hash}: external links that do not open in a new tab: ${[...new Set(sameTab)].slice(0, 5).join(", ")}`);
    // Alignment and spacing: icons and text in every control sit centred, and nothing collides or touches unless the
    // markup says it is meant to (data-joined).
    const misaligned = await page.evaluate(misalignedControls);
    if (misaligned.length) fail(`${hash}: misaligned controls: ${[...new Set(misaligned)].slice(0, 4).join("; ")}`);
    const collided = await page.evaluate(collisions);
    if (collided.length) fail(`${hash}: collisions: ${[...new Set(collided)].slice(0, 4).join("; ")}`);
  }
  if (external.length) fail("requests while navigating: " + external.join(", "));
  for (const problem of problems) fail("navigation: " + problem);
  await context.close();
}

// 3. Reflow at 320 CSS pixels: no horizontal scrolling, and the main views keep their alignment and spacing.
sections.push(["reflow", async () => {
  const { context, page } = await openPage({ width: 320, height: 800 });
  const narrow = ["#/cs/V/path/start", "#/cs/SR/path/publication", "#/en/DS/catalogue/k!resources", "#/cs/V/catalogue/clauses", "#/cs/K/explorer/F1", "#/cs/V/selfcheck", "#/cs/V/check/dataset", "#/cs/V/tools", "#/cs/V/page/machines", "#/en/V/page/about"];
  for (const hash of narrow) {
    await gotoView(page, pageUrl + hash);
    await rendered(page);
    // A station's AI block, opened, so its prompts and copy buttons are measured too.
    await page.evaluate(() => document.querySelectorAll('#main details[data-key="ai"]').forEach((block) => { block.open = true; }));
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (overflow > 1) fail(`${hash}: horizontal scroll of ${overflow}px at 320 px`);
    const misaligned = await page.evaluate(misalignedControls);
    if (misaligned.length) fail(`${hash} at 320 px: misaligned controls: ${[...new Set(misaligned)].slice(0, 4).join("; ")}`);
    const collided = await page.evaluate(collisions);
    if (collided.length) fail(`${hash} at 320 px: collisions: ${[...new Set(collided)].slice(0, 4).join("; ")}`);
  }
  await context.close();
}]);

// 4. Embedded in an iframe.
sections.push(["iframe", async () => {
  const host = resolve(root, ".cache", "iframe-host.html");
  mkdirSync(dirname(host), { recursive: true });
  writeFileSync(host, `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Host</title></head><body><iframe title="FAIR guide" src="${pageUrl}#/cs/V/path/repository" style="width:100%;height:800px"></iframe></body></html>`);
  const { context, page } = await openPage();
  await page.goto(pathToFileURL(host).href);
  const frame = page.frameLocator("iframe");
  await frame.locator("#main h1").waitFor();
  const heading = await frame.locator("#main h1").textContent();
  if (!heading.includes("Výběr repozitáře")) fail("iframe: unexpected heading " + heading);
  await frame.getByRole("link", { name: /Další krok/ }).click();
  try {
    await frame.locator("#main h1", { hasText: "Popis" }).waitFor({ timeout: 5000 });
  } catch (error) {
    fail("iframe: navigation inside the frame failed: " + (await frame.locator("#main h1").textContent()));
  }
  await context.close();
}]);

// 5. Self-check without network: modes and profiles, answers, tiers, gaps on the path, the FIP Dashboard
//    snapshot pre-fill, a shared link and the exports. Nothing may leave the browser.
sections.push(["self-check", async () => {
  const { context, page, external, problems } = await openPage();
  const go = async (hash) => {
    await navigationRendered(page, () => page.evaluate((value) => window.FairGuide.navigate(value), hash));
  };
  const checked = (id) => page.locator("#" + id).isChecked();
  await gotoView(page, pageUrl);
  await rendered(page);

  // A check reads as three parts, each with its own address; the check's own address opens the evidence, and the
  // parts are marked as the reader moves through them (guide-self-check, "A check reads as evidence, answers and
  // report").
  const part = (name) => go("#/cs/V/check/dataset/" + name);
  /* Any check's part, in a role: the evidence, the answers or the report. */
  const at = (lens, check, name) => go(`#/cs/${lens}/check/${check}/${name}`);
  const currentPart = () => page.locator('.check-parts [aria-current="step"]').textContent();
  // Dataset check: the mode comes first, the first view shows the Minimum items only.
  await go("#/cs/V/check/dataset");
  if (!(await currentPart()).includes("Podklady")) fail("dataset check: the check does not open at its evidence part");
  if (!(await page.locator(".notice", { hasText: "Nejdřív odpovězte" }).count())) fail("dataset check: no prompt to choose the mode first");
  await page.locator("#mode-after").check();
  await page.locator(".part-next a").click();
  await page.waitForFunction(() => location.hash.endsWith("/check/dataset/answers") && document.querySelector(".question-card"));
  if (!(await currentPart()).includes("Odpovědi")) fail("dataset check: the answers part is not marked as current");
  if (await page.locator("#item-dataset-06").count()) fail("dataset check: a Recommended item shows in the first view");
  if (/Krok \d/.test(await page.locator(".item-group h2").first().textContent())) fail("dataset check: group headings imitate the path's step numbering");
  if (!(await page.locator("#item-dataset-04").count())) fail("dataset check: Minimum item dataset.04 is missing after publication");
  if (await page.locator("#item-dataset-15").count()) fail("dataset check: a before-publication item shows after publication");
  await page.locator("#answer-dataset-04-no").check();
  await page.locator("#answer-dataset-05-unknown").check();
  await page.locator("#answer-dataset-01-yes").check();
  // Compact question cards: the criterion, principles, answers and one evidence line in view; the explanation,
  // tests, responsibility, path step and sources in one closed disclosure (guide-self-check, "Question cards are
  // compact").
  {
    const card = page.locator("#item-dataset-04");
    if (!(await card.locator(".principle-tile").count()) || !(await card.locator(".origin").isVisible())) fail("dataset check: a question card lacks its principles or its evidence line");
    if ((await card.locator(".question-details").count()) !== 1 || (await card.locator(".question-details").getAttribute("open")) !== null) fail("dataset check: a question card's details are not one closed disclosure");
    if (await card.locator(".fix-at").isVisible()) fail("dataset check: who fixes a question and its path step show outside its details");
  }
  // Each state has its own colour, solid when the reader answered, and Yes and Don't know differ clearly in hue.
  {
    const colour = (value) => page.locator(`#item-dataset-04 .option[data-value="${value}"]`).evaluate((option) => getComputedStyle(option).getPropertyValue("--state").trim());
    const hues = await Promise.all(["yes", "partly", "no", "unknown"].map(colour));
    if (new Set(hues).size !== 4) fail("dataset check: answer states share a colour: " + hues.join(" "));
    const filled = await page.locator('#item-dataset-04 .option[data-value="no"]').evaluate((option) => getComputedStyle(option).backgroundColor);
    if (filled === "rgba(0, 0, 0, 0)" || filled === "rgb(255, 255, 255)") fail("dataset check: the reader's own answer is not filled with its state's colour");
  }
  await part("report");
  if (!(await currentPart()).includes("Zpráva")) fail("dataset check: the report part is not marked as current");
  const gaps = await page.locator(".gaps").first().textContent();
  if (!(await numbersIn(page.locator(".gaps").first())).includes("04") || !gaps.includes("Licence") || !gaps.includes("správce repozitáře")) fail("dataset check: the dataset.04 gap lacks where to fix it or who fixes it: " + gaps);
  const gapLink = await page.locator(".gaps a", { hasText: "Licence" }).first().getAttribute("href");
  if (gapLink !== "#/cs/V/path/licence") fail("dataset check: the gap links to " + gapLink);
  const tasks = await page.locator(".gaps").nth(1).textContent();
  if (!(await numbersIn(page.locator(".gaps").nth(1))).includes("05") || !tasks.includes("data steward")) fail("dataset check: the don't-know task does not say whom to ask: " + tasks);
  if (!(await page.locator(".gaps").nth(1).locator('a[href^="https://nma.eosc.cz"]').count())) fail("dataset check: the don't-know task has no NMA search link");
  const resultText = await page.locator("#results").textContent();
  if (/%|skóre|score/i.test(resultText.replace("nesčítá odpovědi do skóre", ""))) fail("dataset check: the result shows a score or percentage");
  // The report: per-principle distributions as solid segments named in text, the gaps grouped by who fixes them.
  {
    const segments = await page.locator("#results .principle-distribution .distribution-bar > span").evaluateAll((all) => all.map((segment) => [segment.dataset.state, getComputedStyle(segment).backgroundColor]));
    if (!segments.length || segments.some(([, colour]) => /rgba\(0, 0, 0, 0\)/.test(colour))) fail("dataset check: the report's distributions are not solid segments");
    const named = await page.locator("#results .principle-distribution .distribution-text").first().textContent();
    if (!/chybí|splněno|nevíte/.test(named)) fail("dataset check: a distribution is not named in text: " + named);
    if (!(await page.locator("#results .gap-group h4").first().textContent()).includes("správce repozitáře")) fail("dataset check: the gaps are not grouped by who fixes them");
  }
  await axe(page, "dataset check report");
  await part("answers");
  await axe(page, "dataset check answered");
  await page.locator('label[for="extended-toggle"]').click();
  if (!(await page.locator("#item-dataset-06").count())) fail("dataset check: the extended check does not show Recommended items");
  if (!(await page.locator("#extended-toggle").isChecked()) || (await page.locator("#extended-toggle").getAttribute("role")) !== "switch") fail("dataset check: the extended check is not an on/off switch that shows its state");
  if (!(await panelFits(page))) fail("dataset check: the result so far scrolls or is too tall in the extended check: " + await page.locator(".check-summary").evaluate((panel) => JSON.stringify({ height: panel.getBoundingClientRect().height, scroll: panel.scrollHeight, client: panel.clientHeight, viewport: innerHeight })));
  if (!(await checked("answer-dataset-04-no"))) fail("dataset check: opening the extended check lost an answer");
  await page.locator('label[for="extended-toggle"]').click();

  // The first view says what its tier means; items are grouped by FAIR principle, can be grouped by path step, and
  // each names the step where it is addressed.
  const tierInfo = await page.locator(".tier-info").textContent();
  if (!tierInfo.includes("Minimum (") || !tierInfo.includes("Národní datové infrastruktury")) fail("dataset check: the first view does not explain its tier: " + tierInfo);
  const minimumCount = (tierInfo.match(/Minimum \((\d+) /) || [])[1];
  if (!(await page.locator(".item-group h2").first().textContent()).includes("Dohledatelnost")) fail("dataset check: items are not grouped by FAIR principle by default");
  if (!(await page.locator('#item-dataset-04 .fix-at a.step-link[href$="/path/licence"]').count())) fail("dataset check: an item names its step without a link to it");
  if (!(await page.locator("#item-dataset-04 .fix-at").textContent()).includes("Licence")) fail("dataset check: an item does not name the step where it is addressed");
  // The summary mirrors the questions: one chip per question in view, in the list's groups.
  const listed = await page.locator(".items fieldset.item").evaluateAll((items) => items.map((item) => item.id.replace("item-dataset-", "")));
  const chips = await page.locator(".summary-chip").evaluateAll((buttons) => buttons.map((button) => button.textContent.match(/\d{2}/)[0]));
  if (listed.join(" ") !== chips.join(" ")) fail(`dataset check: the summary does not mirror the questions (${chips.join(" ")} vs ${listed.join(" ")})`);
  if ((await page.locator(".summary-group .distribution").count()) !== (await page.locator(".summary-group").count())) fail("dataset check: the running result has no distribution per group");
  await page.locator("#grouping-steps").check();
  const stepHeading = page.locator(".item-group h2").first();
  if ((await stepHeading.locator("svg").count()) !== 1 || /Krok \d/.test(await stepHeading.textContent())) fail("dataset check: grouping by path step does not show the step's icon and name");
  const stepGroups = await page.locator(".item-group").count();
  if ((await page.locator(".summary-group").count()) !== stepGroups) fail("dataset check: the summary does not follow the grouping by path step");
  if ((await page.locator(".summary-group-label .group-icon").count()) !== (await page.locator(".summary-group").count())) fail("dataset check: path steps in the summary lack their icons");
  await part("report");
  if (!(await page.locator("#results .result-progress").first().textContent()).endsWith("z " + minimumCount)) fail("dataset check: the result counts items the first view does not show");
  if ((await page.locator(".result-group").count()) !== stepGroups) fail("dataset check: the full result does not follow the grouping by path step");
  await part("answers");
  await page.locator("#grouping-principles").check();

  // At the top of the answers the summary's box starts level with the first box of the questions.
  await page.evaluate(() => window.scrollTo(0, 0));
  const firstBox = await page.locator(".check-main .items > *").first().boundingBox();
  const summaryBox = await page.locator(".check-summary").boundingBox();
  if (Math.abs(firstBox.y - summaryBox.y) > 2) fail(`dataset check: the summary starts ${Math.round(summaryBox.y - firstBox.y)}px off the first box`);

  // The result stands beside the questions and shows the licence gap at once; it can be collapsed, and the choice
  // survives a reload.
  const mainBox = await page.locator(".check-main").boundingBox();
  const resultBox = await page.locator(".check-summary").boundingBox();
  if (!(resultBox.x > mainBox.x + mainBox.width / 2)) fail("dataset check: the result is not beside the questions");
  await page.locator("#item-dataset-04").scrollIntoViewIfNeeded();
  const gapCell = page.locator('.summary-chip[data-state="gap"]', { hasText: /(^|\s)04(\s|$)/ });
  const gapBox = await gapCell.boundingBox();
  if (!gapBox || gapBox.y < 0 || gapBox.y + gapBox.height > (await page.evaluate(() => window.innerHeight))) fail("dataset check: the R1.1 gap is not in view beside the item");
  // On a wide screen the check's controls sit in the summary, at hand while scrolling.
  if (!(await page.locator(".check-summary #extended-toggle").count()) || !(await page.locator(".check-summary #grouping-steps").count())) fail("dataset check: the extended switch and the grouping are not in the summary on a wide screen");
  // The chips and counts of the result so far lead to the items and to the full result.
  await gapCell.click();
  if (!(await page.evaluate(() => document.activeElement.closest("#item-dataset-04")))) fail("dataset check: a principle chip does not lead to its item");
  if ((await page.locator('.summary-count[data-kind="gaps"]').getAttribute("href")) !== "#/cs/V/check/dataset/report") fail("dataset check: the gap count does not lead to the report");
  // Saved answers outside the short scope remain stored and return when the reader extends the check.
  await page.locator('label[for="extended-toggle"]').click();
  await page.locator("#answer-dataset-08-no").check();
  await page.locator('label[for="extended-toggle"]').click();
  if (await page.locator(".summary-chip", { hasText: /(^|\s)08(\s|$)/ }).count()) fail("dataset check: a saved answer outside the short scope still appears in its summary");
  await page.locator('label[for="extended-toggle"]').click();
  if (!(await checked("answer-dataset-08-no"))) fail("dataset check: changing scope lost the saved answer outside it");
  await page.locator('label[for="extended-toggle"]').click();
  // The collapse control stays exactly where it was.
  await page.locator("#item-dataset-04").scrollIntoViewIfNeeded();
  await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
  const toggleBefore = await page.locator("#result-toggle").boundingBox();
  if (!(await page.evaluate(({ x, y }) => document.elementFromPoint(x, y)?.closest("#result-toggle"), { x: toggleBefore.x + toggleBefore.width / 2, y: toggleBefore.y + toggleBefore.height / 2 }))) fail("dataset check: the sticky collapse control is covered by another element");
  // Click where the reader sees the sticky control; locator.click may scroll it back to its flow position first.
  await page.mouse.click(toggleBefore.x + toggleBefore.width / 2, toggleBefore.y + toggleBefore.height / 2);
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
    st.items["dataset.02"] = {
      value: "yes",
      origin: "prefill",
      prefill: { source: "resolver", date: "2026-10-08", value: "yes", notes: [], list: [], fields: [{ path: "url", values: ["https://repo.example/record/1"], more: 0 }], record: "https://repo.example/record/1" },
    };
    FG.saveState();
    FG.rerender();
  });
  // The question's evidence line names the source, its date and the record; its details hold every field found.
  const evidence = await page.locator("#origin-dataset-02").textContent();
  if (!evidence.includes("8. 10. 2026") || !evidence.includes("záznam")) fail("dataset check: the evidence line beside dataset.02 is incomplete: " + evidence);
  if (!(await page.locator('#origin-dataset-02 a[href="https://repo.example/record/1"]').count())) fail("dataset check: the evidence does not link to its record");
  const details = await page.locator("#item-dataset-02 .question-details").textContent();
  if (!details.includes("url") || !details.includes("https://repo.example/record/1")) fail("dataset check: the question's details lack the fields found: " + details);
  // Withdrawing an answer the reader changed restores the suggestion, attributed to its source, and leaves the other
  // answers as they were (guide-self-check, "Each answer can be withdrawn").
  await page.locator("#answer-dataset-02-no").check();
  if (!(await page.locator("#withdraw-dataset-02").count())) fail("dataset check: a changed answer offers no way to withdraw it");
  await page.locator("#withdraw-dataset-02").click();
  await page.waitForFunction(() => document.getElementById("answer-dataset-02-yes") && document.getElementById("answer-dataset-02-yes").checked);
  if ((await page.locator("#item-dataset-02").getAttribute("data-origin")) !== "suggestion" || !(await page.locator("#origin-dataset-02").textContent()).includes("resolver")) fail("dataset check: withdrawing does not restore the suggestion with its source");
  if (!(await checked("answer-dataset-04-no")) || !(await checked("answer-dataset-01-yes"))) fail("dataset check: withdrawing one answer changed others");
  if (await page.locator("#withdraw-dataset-02").count()) fail("dataset check: a suggestion offers to withdraw itself");
  await page.locator("#answer-dataset-01-no").check();
  await page.locator("#withdraw-dataset-01").click();
  await page.waitForSelector("#answer-dataset-01-yes");
  if (await page.locator('input[name="answer-dataset-01"]:checked').count()) fail("dataset check: withdrawing an answer without a suggestion does not leave it open");
  await page.locator("#answer-dataset-01-yes").check();
  // A resolved identifier says what it is, under the field in the evidence part and in the report.
  await part("evidence");
  const card = await page.locator(".target-card").textContent();
  if (!card.includes("Sample dataset") || !card.includes("Zenodo") || !card.includes("2026")) fail("dataset check: the resolved identifier does not say what it is: " + card);
  await part("report");
  if (!(await page.locator(".result-headline").textContent()).includes("Kontrolujete: Sample dataset")) fail("dataset check: the result does not name what is checked");
  await page.locator("#export-format-md").check();
  await page.locator(".export-preview summary").click();
  await page.waitForFunction(() => document.getElementById("export-preview-text").value.length > 0);
  const doiSummary = await page.locator("#export-preview-text").inputValue();
  if (!doiSummary.includes("url: https://repo.example/record/1")) fail("dataset check: the Markdown summary lacks the evidence");
  await page.locator("#export-format-jsonld").check();
  if (!(await page.locator("#export-preview-text").inputValue()).includes('"guideState"')) fail("dataset check: the preview does not follow the chosen format");
  await page.locator(".export-preview summary").click();
  await page.locator("#export-format-md").check();
  // Your answers read as a list: the answer beside each question, and the evidence under it.
  const answerRow = await page.locator(".answers-list .answer-row").filter({ has: page.locator(".item-id", { hasText: /^02$/ }) }).textContent();
  if (!answerRow.includes("Ano") || !answerRow.includes("https://repo.example/record/1") || !answerRow.includes("záznam")) fail("dataset check: the answers list lacks the answer or its evidence: " + answerRow);
  // The summary loads back with the DOI in its field, what it is, and the evidence.
  {
    const saved = resolve(root, ".cache", "doi-summary.md");
    writeFileSync(saved, doiSummary);
    await page.evaluate(() => {
      window.FairGuide.state.answers.dataset = { mode: "before", items: {} };
      window.FairGuide.saveState();
      window.FairGuide.rerender();
    });
    await part("evidence");
    await page.locator("#load-file").setInputFiles(saved);
    await page.waitForSelector(".notice.shared");
    await page.getByRole("button", { name: "Použít odpovědi ze souboru" }).click();
    // Adopted answers open at the answers part.
    await page.waitForFunction(() => location.hash.endsWith("/check/dataset/answers") && document.getElementById("origin-dataset-02"));
    if (!(await page.locator("#item-dataset-02 .question-details").textContent()).includes("https://repo.example/record/1")) fail("load: the evidence behind dataset.02 is lost after loading the summary");
    await part("evidence");
    if ((await page.locator("#prefill-pid").inputValue()) !== "10.5281/zenodo.1") fail("load: the DOI is not back in its field after loading the summary");
    const restoredCard = page.locator(".target-card");
    if (!(await restoredCard.count()) || !(await restoredCard.textContent()).includes("Sample dataset")) fail("load: what the DOI is does not show after loading the summary");
  }
  await page.locator("#prefill-pid-clear").click();
  if (await page.locator("#prefill-pid").inputValue()) fail("dataset check: clearing did not empty the identifier field");
  if (await page.locator(".target-card").count()) fail("dataset check: clearing the identifier kept its description");
  await part("answers");
  if (await page.locator('input[name="answer-dataset-02"]:checked').count()) fail("dataset check: clearing the identifier kept the answer it pre-filled");
  if (!(await checked("answer-dataset-01-yes")) || !(await checked("answer-dataset-04-no"))) fail("dataset check: clearing the identifier removed the user's own answers");

  // The path marks the stations with open items.
  await go("#/cs/V/path/licence");
  if (!(await page.locator('.rail-desktop a[href="#/cs/V/path/licence"] .rail-mark[data-state="gap"]').count())) fail("path: the licence station has no gap mark");
  const tileOrder = await page.locator(".station-header .principle-tile").evaluateAll((tiles) => tiles.map((tile) => tile.textContent.trim().split(" ")[0]));
  if (tileOrder.join(" ") !== "A1.2 R1.1") fail("path: the station's principles are not in F, A, I, R order: " + tileOrder.join(" "));
  const legend = page.locator(".rail-desktop .rail-legend a");
  if (!(await legend.count()) || (await legend.getAttribute("href")) !== "#/cs/V/selfcheck") fail("path: the self-check marks have no visible legend linking to the self-check");

  // The rail lists the steps under the life-cycle stages and marks the stage of the step being read, in words too;
  // no stage is ever chosen.
  const stageGroups = page.locator(".rail-desktop .rail-stage");
  if ((await stageGroups.count()) < 7) fail("path: the rail does not list the life-cycle stages");
  if (await page.locator(".rail .rail-step .number").count()) fail("path: rail steps repeat the stage numbering");
  if (!(await page.locator(".rail .rail-stage-number").count())) fail("path: removing step numbers also removed stage numbers");
  const currentStage = page.locator(".rail-desktop .current-stage");
  if ((await currentStage.count()) !== 1 || !(await currentStage.locator(".rail-stage-name").textContent()).includes("Sdílení dat")) fail("path: the licence step's stage is not marked as current");
  if ((await currentStage.locator("li a").count()) !== 4) fail("path: the sharing stage does not hold its four steps");
  if (!(await currentStage.locator(".visually-hidden").count())) fail("path: the current stage is marked only visually");
  if (await page.locator(".stage-switch, .stage-card").count()) fail("path: a stage choice is still offered");

  // The menu's path item opens the station the visitor was last at; the home item opens the path's start, with a
  // line to resume where they were.
  if ((await page.locator(".main-nav a", { hasText: "Cesta k FAIR" }).getAttribute("href")) !== "#/cs/V/path/licence") fail("menu: the path item does not open the last station");
  if ((await page.locator('.main-nav a[aria-current="page"]').textContent()) !== "Cesta k FAIR") fail("menu: the path item is not marked on a station");
  await page.locator(".main-nav a", { hasText: "Úvod" }).click();
  try {
    await page.waitForFunction(() => window.location.hash === "#/cs/V/path/start" && document.querySelector("#journey-title"), null, { timeout: 5000 });
  } catch (error) {
    fail("menu: the home item does not open the path's start");
  }
  if ((await page.locator('.main-nav a[aria-current="page"]').textContent()) !== "Úvod") fail("menu: the home item is not marked on the landing");
  if (!(await page.locator(".resume a").textContent()).includes("Licence")) fail("path: no resume line for the last station");
  if ((await page.locator(".ring-last").getAttribute("data-stage")) !== "share") fail("landing: the ring does not mark the stage last read");
  const lastRead = await page.locator(".journey-last").allTextContents();
  if (lastRead.length !== 1 || !lastRead[0].includes("Sdílení dat") || !lastRead[0].includes("Naposledy jste četli")) fail("landing: the stage last read is not marked in words: " + lastRead.join(" | "));

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
    await gotoView(view, pageUrl + "#/cs/V/path/licence");
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
  const guideCitation = await page.locator(".site-footer p", { hasText: "Jak citovat Průvodce" }).textContent();
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
  for (const hash of ["#/cs/V/explorer", "#/cs/V/catalogue/k!repositories", "#/cs/V/catalogue/k!resources", "#/cs/V/page/about"]) {
    await go(hash);
    if (await page.locator(".lens-band").count()) fail("lens band: shown where the lens changes nothing: " + hash);
  }
  await go("#/cs/V/selfcheck");
  if (!(await page.locator(".lens-band").count())) fail("lens band: missing on the self-check overview");
  const cornerOffsets = await page.locator(".check-card").evaluateAll((cards) => cards.map((card) => { const box = card.getBoundingClientRect(); const button = card.querySelector(".check-card-action a").getBoundingClientRect(); return Math.round(box.bottom - button.bottom) + "/" + Math.round(box.right - button.right); }));
  if (new Set(cornerOffsets).size !== 1) fail("overview: the check cards' buttons are not in the same corner: " + cornerOffsets.join(" "));
  // In the catalogue the lens is a facet of the resources that starts empty, whatever the reader's lens; chosen, it
  // narrows what the guide recommends and leaves cited works in.
  await go("#/cs/V/catalogue/k!resources");
  const shownNow = async () => Number(((await page.locator(".catalogue-count").textContent()).match(/\d+/) || [0])[0]);
  if (await page.locator('input[id^="facet-resources-lens-"]:checked').count()) fail("finder: the lens facet starts with a lens chosen");
  const allLenses = await shownNow();
  await page.locator("#facet-resources-lens-ds").check();
  await page.waitForFunction(() => location.hash.includes("f.lens!DS"));
  if ((await shownNow()) >= allLenses) fail("finder: the lens facet does not filter the resources");
  if (!(await page.locator(".card", { hasText: "Analýza a návrh postupů" }).count())) fail("finder: the lens hides a cited work, which has no audience");

  // A shared link opens as a preview in a browser without the answers, and can be adopted.
  await part("report");
  await page.locator("#share-create").click();
  const shared = await page.locator("#share-url").inputValue();
  if (!shared.includes("/check/dataset/a2.after.none.") || !shared.includes(".04n") || !shared.includes(".05k")) fail("share link: unexpected payload " + shared);
  if (shared.startsWith("file:")) fail("share link: names a local file instead of the published page");
  {
    const other = await browser.newContext();
    const view = await other.newPage();
    await gotoView(view, pageUrl + shared.slice(shared.indexOf("#")));
    await view.waitForSelector(".notice.shared");
    if (!(await numbersIn(view.locator(".gaps").first())).includes("04")) fail("share link: the preview does not show the dataset.04 gap");
    await view.getByRole("button", { name: "Použít odpovědi z odkazu" }).click();
    await view.waitForSelector("#answer-dataset-04-no");
    if (!(await view.locator("#answer-dataset-04-no").isChecked())) fail("share link: adopting the answers did not store them");
    await gotoView(view, pageUrl + "#/cs/V/check/dataset/a2.after._.99q");
    await view.waitForSelector(".notice");
    if (!(await view.locator(".notice", { hasText: "nepodařilo přečíst" }).count())) fail("share link: an invalid link is not reported");
    await other.close();
  }

  // Gate check: the core-system profile marks monitoring and central logging as provided by NRP.
  await at("SR", "gate", "evidence");
  await page.locator("#profile-core-system").check();
  await at("SR", "gate", "answers");
  for (const id of ["gate-09", "gate-10"]) {
    if (await page.locator(`#answer-${id}-yes`).count()) fail(`gate check: ${id} asks for an answer although NRP provides it`);
    if (!/zajišťuje NRP/i.test(await page.locator(`#item-${entryAnchor(id)}`).textContent())) fail(`gate check: ${id} is not marked as provided by NRP`);
  }
  if (await page.locator("#item-gate-18").count()) fail("gate check: gate.18 shows for the core-system profile");
  // NKR lists no repository yet, so a record is put in place of the NKR snapshot the page carries.
  await at("SR", "gate", "evidence");
  await page.evaluate(() => {
    window.FairGuide.config.nkr = { retrieved: "2026-10-14", records: [{ id: "test/1", content: { repositoryName: "Test repository", pidType: ["DOI"], oaipmhEndpoint: ["https://repo.example/oai"] } }] };
    window.FairGuide.rerender();
  });
  await page.locator("#prefill-nkr-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await page.locator('.evidence-card[data-source="nkr"] #prefill-status').count())) fail("gate check: the NKR run does not report in the NKR card");
  await page.evaluate(() => { delete window.FairGuide.config.nkr; });
  await at("SR", "gate", "answers");
  for (const id of ["gate-01", "gate-07"]) {
    if (!(await checked(`answer-${id}-yes`))) fail(`gate check: ${id} is not pre-filled yes from an NKR record listing DOI`);
    if (!(await page.locator(`#origin-${id}`).textContent()).includes("NKR")) fail(`gate check: ${id} does not name NKR as its source`);
  }
  if (!(await checked("answer-gate-08-partly"))) fail("gate check: gate.08 exceeds its pre-fill level");
  if (await page.locator('input[name="answer-gate-06"]:checked').count()) fail("gate check: gate.06 is pre-filled although the record does not state it");
  await axe(page, "gate check");

  // Maturity and institution checks run end to end; the institution check has no Minimum items and shows them all.
  // The maturity check fills in from the re3data snapshot and says which repository it is; a repository outside
  // the snapshot is explained rather than guessed. FAIRsharing's record comes from its snapshot (D-185).
  await at("SR", "maturity", "answers");
  await page.locator('label[for="extended-toggle"]').click();
  const fromRe3data = async (input) => {
    await at("SR", "maturity", "evidence");
    if (await page.locator("#prefill-re3data-clear").isEnabled()) await page.locator("#prefill-re3data-clear").click();
    await page.fill("#prefill-re3data", input);
    await page.locator("#prefill-re3data-run").click();
    await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  };
  await fromRe3data("https://www.re3data.org/repository/r3d100010386");
  if (!(await page.locator('.evidence-card[data-source="re3data"] .target-card').textContent()).includes("LINDAT")) fail("maturity check: the re3data record does not say which repository it is, in the re3data card");
  if (!(await page.locator('.evidence-card[data-source="re3data"] #prefill-status').count())) fail("maturity check: the re3data run does not report in the re3data card");
  await at("SR", "maturity", "answers");
  if (!(await checked("answer-maturity-18-partly")) || !(await page.locator("#origin-maturity-18").textContent()).includes("re3data")) fail("maturity check: maturity.18 is not partly met from re3data alone");
  if (!(await checked("answer-maturity-01-yes")) || !(await checked("answer-maturity-19-yes"))) fail("maturity check: re3data facts do not fill in maturity.01 and maturity.19");
  if (!(await page.locator("#item-maturity-05 .question-details").textContent()).includes("OAI-PMH")) fail("maturity check: maturity.05 does not retain the OAI-PMH evidence from re3data in its details");
  // A repository whose FAIRsharing record the snapshot holds completes maturity.18 and links the record.
  await fromRe3data("r3d100010484");
  await at("SR", "maturity", "answers");
  if (!(await checked("answer-maturity-18-yes"))) fail("maturity check: a FAIRsharing record in the snapshot does not complete maturity.18");
  if (!(await page.locator('#origin-maturity-18 a[href="https://doi.org/10.25504/FAIRsharing.f4bfb1"]').count())) fail("maturity check: maturity.18 does not link to the FAIRsharing record");
  // Without the FAIRsharing snapshot, maturity.18 stays open with a note, and the re3data answers stand.
  await page.evaluate(() => {
    const FG = window.FairGuide, get = FG.get;
    FG.get = (id) => (id === "#snapshot-fairsharing" ? undefined : get(id));
    window.restoreGet = () => { FG.get = get; };
  });
  await fromRe3data("r3d100010386");
  await page.evaluate(() => window.restoreGet());
  await at("SR", "maturity", "answers");
  if ((await page.locator('input[name="answer-maturity-18"]:checked').count()) || !(await page.locator("#origin-maturity-18").textContent()).includes("nepodařilo ověřit")) fail("maturity check: without the FAIRsharing snapshot maturity.18 is not left open with a note");
  if (!(await checked("answer-maturity-01-yes"))) fail("maturity check: without the FAIRsharing snapshot the re3data answers stopped");
  await at("SR", "maturity", "evidence");
  await page.fill("#prefill-re3data", "r3d999999999");
  await page.locator("#prefill-re3data-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("není ve snímku"));
  await page.locator("#prefill-re3data-clear").click();
  // While NKR lists no repository, the check says to use the re3data record instead and offers no sample records,
  // which only the catalogue shows.
  if (!(await page.locator("#nkr-status").textContent()).includes("re3data níže") || (await page.locator("#nkr-samples").count()) || (await page.locator("#nkr-load").count())) fail("maturity check: an empty NKR does not point to the re3data record, offers sample records the check cannot use, or offers to load NKR");
  // FAIR Champion over a sample of records (replaced here). Each question shows the tests that can answer it and runs
  // them alone; an identifier that does not resolve is not tested. One record passes, one fails and one gives no
  // result. A narrower retention test covers only part of the tombstone question, so it suggests Partly (D-168).
  // Running all tests shows a bar in the sample's card, the coverage is stated, and a retry runs only the tests
  // without a result.
  await at("SR", "maturity", "answers");
  if (!(await page.locator("#item-maturity-11 .question-details").evaluate((node) => node.open))) await page.locator("#item-maturity-11 .question-details > summary").click();
  const line = page.locator("#tests-maturity-11");
  if (!(await line.locator('a[href$="/catalogue/test/fc/fc_metadata_persistence"]').count()) || !(await line.textContent()).includes("po zadání vzorku") || (await page.locator(".champion-tests").count())) fail("maturity check: a question does not show its test and that a sample comes first, or the tests are listed apart from their questions");
  await page.evaluate(() => {
    const live = window.FairGuide.live;
    window.championCalls = [];
    live.resolvePid = async (pid) => ({ found: !pid.value.endsWith("/gone"), url: "https://repo.example/" + pid.value });
    live.championTest = async (test, record) => {
      window.championCalls.push(test + " " + record);
      if (window.championGate) await window.championGate;
      if (record.endsWith("/none")) throw new Error("no verdict");
      return { value: record.endsWith("/bad") ? "fail" : "pass", log: "" };
    };
  });
  await at("SR", "maturity", "evidence");
  await page.fill("#prefill-champion", "10.1234/good\n10.1234/bad\n10.1234/none\n10.1234/gone");
  await at("SR", "maturity", "answers");
  if (!(await page.locator("#item-maturity-11 .question-details").evaluate((node) => node.open))) await page.locator("#item-maturity-11 .question-details > summary").click();
  await page.locator("#test-run-maturity-11").click();
  await page.waitForFunction(() => FairGuide.state.answers.maturity.items["maturity.11"]?.observations?.some((entry) => entry.source === "champion"));
  const oneQuestion = await page.evaluate(() => window.championCalls);
  if (oneQuestion.length !== 3 || oneQuestion.some((call) => !call.startsWith("fc_metadata_persistence https://doi.org/") || call.includes("gone"))) fail("maturity check: one question's run did not test only its test on the resolved records, as resolver addresses: " + oneQuestion.join(", "));
  if (!(await checked("answer-maturity-11-partly")) || !(await line.textContent()).includes("1 z 2") || !(await page.locator("#origin-maturity-11").textContent()).includes("FAIR Champion")) fail("maturity check: a narrower test met on part of the sample does not suggest Partly, or loses its coverage at its test line");
  if (!(await page.locator("#prefill-status").textContent()).includes("10.1234/gone")) fail("maturity check: the record that does not resolve is not reported");
  await page.evaluate(() => { window.championCalls = []; window.championGate = new Promise((resolve) => { window.openChampion = resolve; }); });
  await at("SR", "maturity", "evidence");
  await page.locator("#prefill-champion-run").click();
  await page.waitForSelector("#prefill-progress:not([hidden])");
  if (!(await page.locator('.evidence-card[data-source="sample"] #prefill-progress').count())) fail("maturity check: the run's progress is not in the sample's card, beside its control");
  if (!(await page.locator("#prefill-progress").textContent()).includes("z 28 testů")) fail("maturity check: running all tests does not show the progress of the remaining tests and the retry");
  await at("SR", "maturity", "answers");
  if (!(await page.locator("#tests-maturity-06 .test-state").textContent()).includes("běží")) fail("maturity check: a question's line does not say its test is running");
  await page.evaluate(() => window.openChampion());
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  await at("SR", "maturity", "evidence");
  if (await page.locator("#prefill-progress:not([hidden])").count()) fail("maturity check: the progress bar stays after the tests");
  const championStatus = await page.locator("#prefill-status").textContent();
  if (!championStatus.includes("20 z 30 testů")) fail("maturity check: the coverage is not reported: " + championStatus);
  if (!(await page.locator("#prefill-champion-run").textContent()).includes("(10)")) fail("maturity check: no retry of the ten tests without a result");
  await page.evaluate(() => { window.championGate = null; window.championCalls = []; window.FairGuide.live.championTest = async (test, record) => (window.championCalls.push(record), { value: "pass", log: "" }); });
  await page.locator("#prefill-champion-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("30 z 30"));
  if (await page.evaluate(() => window.championCalls.length !== 10 || window.championCalls.some((record) => !record.endsWith("/none")))) fail("maturity check: the retry ran tests that had a result");
  if (await page.locator("#prefill-champion-run").count()) fail("maturity check: a run stays offered after every test has a result");
  await at("SR", "maturity", "answers");
  if (!(await page.locator("#tests-maturity-11").textContent()).includes("2 z 3")) fail("maturity check: the retried results are not counted");
  await at("SR", "maturity", "evidence");
  await page.fill("#prefill-champion", "a b c d e f");
  /* A sample over five records cannot be tested: the run waits, and the sample's reason says how many it takes. */
  const oversized = await page.locator("#prefill-champion-run").evaluate((button) => ({ disabled: button.disabled, reason: (document.getElementById(button.getAttribute("aria-describedby") || "") || {}).textContent || "" }));
  if (!oversized.disabled || !oversized.reason.includes("jeden až 5")) fail("maturity check: a sample over five records can be tested, or the run does not say why it waits");
  await at("SR", "maturity", "answers");
  await page.locator("#answer-maturity-02-no").check();
  await at("SR", "maturity", "report");
  if (!(await numbersIn(page.locator(".gaps").first())).includes("02")) fail("maturity check: the maturity.02 gap is missing");
  await at("DS", "institution", "answers");
  if (!(await page.locator("#item-institution-01").count())) fail("institution check: no item shows in the first view");
  await page.locator("#answer-institution-01-unknown").check();
  await at("DS", "institution", "report");
  if (!(await numbersIn(page.locator(".gaps").first())).includes("01")) fail("institution check: the don't-know task is missing");
  // A check in blocks reports its state by block, every question once (D-185).
  if (!(await page.locator("#results-blocks").count()) || !(await page.locator("#results .block-distribution").count())) fail("institution check: the report does not give the state by block");
  await at("DS", "institution", "answers");
  // The basic institution check is the strategy, which the Open Science III call requires, and the research act's
  // obligations; the extended check adds the action plan, the policy and the national infrastructure. Blocks replace
  // the grouping switch; a gap cites the call's minimum (and for the policy the EOSC CZ manual) and links to the
  // step where it is fixed.
  const basicBlocks = await page.locator(".item-group > h2").allTextContents();
  if (basicBlocks.length !== 2 || !basicBlocks[0].includes("zákona o výzkumu") || !basicBlocks[1].includes("Strategie") || (await page.locator(".grouping").count())) fail("institution check: the basic check is not the research act's obligations and the strategy, or the grouping switch shows: " + basicBlocks.join(" | "));
  if ((await page.locator(".item-group > h2 svg.group-icon").count()) !== 2 || (await page.locator(".check-summary svg.group-icon").count()) < 2) fail("institution check: blocks are not marked by their icons in the list and the summary");
  if (!(await page.locator(".item-group .group-description", { hasText: "§ 83" }).count())) fail("institution check: the obligations block does not say where they come from");
  await page.locator("#answer-institution-08-no").check();
  await at("DS", "institution", "report");
  const peopleGap = page.locator(".gaps .action-card").filter({ has: page.locator(".item-id", { hasText: /^08$/ }) }).first();
  if (!(await peopleGap.locator('.id-chip[href$="/catalogue/cl/OS3-RULES.04"]').count())) fail("institution check: the strategy's human-resources gap does not cite the call's minimum");
  await at("DS", "institution", "answers");
  await page.locator('label[for="extended-toggle"]').click();
  const allBlocks = await page.locator(".item-group > h2").allTextContents();
  if (allBlocks.length !== 5 || !allBlocks[3].includes("Politika")) fail("institution check: the extended check does not add the action plan, policy and infrastructure blocks: " + allBlocks.join(" | "));
  await page.locator("#answer-institution-18-no").check();
  await at("DS", "institution", "report");
  const retentionGap = page.locator(".gaps .action-card").filter({ has: page.locator(".item-id", { hasText: /^18$/ }) }).first();
  const cites = async (id) => retentionGap.locator(`.id-chip[href$="/catalogue/cl/${id}"]`).count();
  if (!(await cites("OS3-RULES.14")) || !(await cites("POLICY-MANUAL.04")) || !(await retentionGap.locator('a[href$="/path/repository"]').count())) fail("institution check: the retention gap does not cite the call and the manual or link to the repository step");

  // FIP check: the dashboard snapshot pre-fills answers with their source; a principle without a declaration stays
  // open with a note; a change by the user stays marked.
  await at("K", "fip", "answers");
  await page.locator('label[for="extended-toggle"]').click();
  await at("K", "fip", "evidence");
  await page.locator("#prefill-fip").selectOption("nusl-grey");
  await page.locator("#prefill-fip-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  await at("K", "fip", "answers");
  const open = await page.evaluate(() => [...document.querySelectorAll("fieldset.item")].filter((item) => !item.querySelector("input:checked") && item.textContent.includes("nic nedeklaruje")).map((item) => item.id));
  if (!open.length) fail("FIP check: no item stays open with a note for a principle without a declaration");
  await at("K", "fip", "evidence");
  await page.locator("#prefill-fip").selectOption("ndi-baseline");
  await page.locator("#prefill-fip-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  await at("K", "fip", "answers");
  if (!(await checked("answer-fip-01-yes"))) fail("FIP check: fip.01 is not pre-filled from the snapshot");
  if (!(await panelFits(page))) fail("FIP check: the result so far scrolls or is too tall after pre-fill: " + await page.locator(".check-summary").evaluate((panel) => JSON.stringify({ height: panel.getBoundingClientRect().height, scroll: panel.scrollHeight, client: panel.clientHeight, viewport: innerHeight })));
  if (!(await page.locator("#origin-fip-01").textContent()).includes("FIP Dashboard (snímek)")) fail("FIP check: fip.01 does not name its source");
  await page.locator("#answer-fip-01-partly").check();
  if ((await page.locator("#origin-fip-01 .source-chip[data-origin]").getAttribute("data-origin")) !== "changed") fail("FIP check: a changed pre-filled answer is not marked");
  await axe(page, "FIP check pre-filled");

  // Loading a saved result is a way to start: offered at the top of every check, also before the mode is chosen,
  // and not repeated among the saving controls.
  for (const [hash, label] of [["#/cs/V/check/dataset", "before the mode"], ["#/cs/SR/check/maturity", "with public records"], ["#/cs/DS/check/institution", "without public records"]]) {
    const view = await browser.newPage();
    await gotoView(view, pageUrl + hash);
    await view.waitForSelector("#main h1");
    if (!(await view.locator(".prefill #load-file").count())) fail(`start (${label}): loading a saved result is not offered at the top of the check`);
    if (await view.locator(".export #load-file, .export .load-file").count()) fail(`start (${label}): loading is repeated among the saving controls`);
    await view.close();
  }

  // Exports: Markdown and an FTR result set in an RO-Crate, naming the published page and the assessed profile.
  await at("K", "fip", "report");
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
  const k01 = results.find((result) => result["@id"] === "#result-fip.01") || {};
  if (!String(k01["ftr:log"]).includes("Doklad") || !k01["prov:used"]) fail("export: the fip.01 result does not record its evidence: " + JSON.stringify(k01));
  if (!md.includes("Deklarované")) fail("export: the Markdown summary does not carry the evidence behind the answers");
  if (JSON.stringify(exported).includes("file:")) fail("export: the JSON-LD names a local file");
  // A result names the test it came from: the question's manual test in the guide's API, which implements the
  // question's metric. From a local file the page names the configured address, which maps onto the built site.
  const configured = await page.evaluate(() => window.FairGuide.config.pageUrl);
  const testRef = String((k01["ftr:outputFromTest"] || {})["@id"] || "");
  const testFile = testRef.startsWith(configured) ? resolve(root, "_site", testRef.slice(configured.length)) : null;
  const testRecord = testFile && existsSync(testFile) ? JSON.parse(readFileSync(testFile, "utf8")) : null;
    if (!testRecord || ![].concat(testRecord["@type"]).includes("Test") || testRecord.isImplementationOf !== "../q/fip.01.json") fail("export: the fip.01 result does not name its test in the guide's API: " + testRef);

  // Local data: each check says where the answers are kept, and how it works.
  await at("K", "fip", "evidence");
  const note = await page.locator(".local-data").textContent();
  if (!note.includes("zůstávají jen v tomto prohlížeči") || !note.includes("Co odchází")) fail("local data: the statement or its explanation is missing on the check");
  if (!/<!-- fair-guide-result v2 guide=\S+: fip a2\./.test(md)) fail("export: the Markdown summary does not carry the answers with the format and guide versions");
  if (!/<!-- fair-guide-state\n[A-Za-z0-9+/=\n]+\n-->/.test(md)) fail("export: the Markdown summary does not carry the state for loading back");
  const state = JSON.parse(exportedGraph.find((entity) => entity.guideState).guideState);
  if (state.format !== "eosc-fair-guide-result" || state.v !== 2 || !state.guideVersion) fail("export: the JSON-LD does not declare its format and the guide's version");
  if (state.fip !== "ndi-baseline" || !state.targetInfo) fail("export: the JSON-LD does not carry the chosen profile and what it is");

  // A saved result loads in another browser as a preview, keeps its evidence, and is adopted only on request; a
  // file the guide did not make is refused.
  {
    const other = await browser.newContext();
    const view = await other.newPage();
    await gotoView(view, pageUrl + "#/cs/K/selfcheck");
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
    await tryLoad(variant("damaged.jsonld", (data) => { data.items["fip.01"].value = "maybe"; }), "poškozený", "load: a damaged file is not reported as damaged");
    await tryLoad(variant("newer.jsonld", (data) => { data.v = 4; data.guideVersion = "9.0.0"; }), "novější verze", "load: a file from a newer format is not reported");
    /* Revision 3 is assessments; a revision 2 file that claims them is damaged rather than silently partial. */
    await tryLoad(variant("claimed.jsonld", (data) => { data.assessments = [{ id: "f-uji:sha256-00", provider: "f-uji" }]; }), "poškozený", "load: a revision 2 file with assessments is not reported as damaged");
    await view.locator("#load-file-overview").setInputFiles(variant("unknown-item.jsonld", (data) => { data.items["fip.99"] = { value: "yes", origin: "user", prefill: null }; }));
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("vynechali: 1")) fail("load: a question this version does not know is not skipped with a note");
    await gotoView(view, pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await view.locator("#load-file-overview").setInputFiles(await ldDownload.path());
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("ze souboru")) fail("load: a JSON-LD file does not open as a preview");
    if (await view.evaluate(() => Object.keys(window.FairGuide.state.answers).length)) fail("load: the preview changed the stored answers");
    await view.getByRole("button", { name: "Použít odpovědi ze souboru" }).click();
    await view.waitForSelector("#answer-fip-01-partly");
    if (!(await view.locator("#answer-fip-01-partly").isChecked())) fail("load: the adopted answers are not the file's answers");
    const loaded = await view.locator("#origin-fip-01").textContent();
    if (!loaded.includes("Převzato ze sdíleného výsledku") || !loaded.includes("se liší od návrhu")) fail("load: the adopted fip.01 lost its evidence or is mislabelled: " + loaded);
    const restored = async (format) => {
      await gotoView(view, pageUrl + "#/cs/K/check/fip/evidence");
      await view.waitForSelector("#prefill-fip");
      if ((await view.locator("#prefill-fip").inputValue()) !== "ndi-baseline") fail(`load (${format}): the profile chosen for pre-fill is not restored`);
      if (!(await view.locator(".target-card").count())) fail(`load (${format}): what the identifier is does not show after loading`);
    };
    await restored("JSON-LD");
    await gotoView(view, pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await view.locator("#load-file-overview").setInputFiles(await mdDownload.path());
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("ze souboru")) fail("load: a Markdown summary does not open as a preview");
    await view.getByRole("button", { name: "Použít odpovědi ze souboru" }).click();
    await view.waitForSelector("#answer-fip-01-partly");
    const fromMarkdown = await view.locator("#origin-fip-01").textContent();
    if (!fromMarkdown.includes("se liší od návrhu")) fail("load (Markdown): the adopted fip.01 lost its evidence: " + fromMarkdown);
    await restored("Markdown");
    // A summary from before the state was carried still loads its answers.
    const older = resolve(root, ".cache", "older-summary.md");
    writeFileSync(older, md.replace(/<!-- fair-guide-state[\s\S]*?-->\n?/, ""));
    await gotoView(view, pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await view.locator("#load-file-overview").setInputFiles(older);
    await view.waitForSelector(".notice.shared");
    const broken = resolve(root, ".cache", "broken-state.md");
    writeFileSync(broken, md.replace(/(<!-- fair-guide-state\n)[A-Za-z0-9]{8}/, "$1@@@@@@@@"));
    await gotoView(view, pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await tryLoad(broken, "poškozený", "load: a summary with a damaged state is not reported as damaged");
    await other.close();
  }

  // Reflow of a check at 320 CSS pixels.
  await page.setViewportSize({ width: 320, height: 800 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 1) fail(`FIP check: horizontal scroll of ${overflow}px at 320 px`);

  // Deleting everything lives on the About page, which the footer links to, and on each check; the self-check
  // overview links there. It leaves nothing the guide stored, and the checks start empty.
  await go("#/cs/K/selfcheck");
  if ((await page.locator(".local-data").count()) || !(await page.locator('a[href$="/page/about/privacy"]', { hasText: "smazat" }).count())) fail("local data: the self-check overview does not link to the About page in place of the note");
  if (!(await page.locator('footer a[href$="/page/about/privacy"]').count())) fail("local data: the footer does not link to the data in this browser");
  await go("#/cs/K/page/about/privacy");
  if (!(await page.locator("#privacy .local-data").count())) fail("local data: the About page's privacy section does not show the note");
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
}]);

// 6. Funded output in the dataset check: the programme question appears after publication with no programme
//    picked; the minizáměr shows the requirements both programmes share and Open Science III adds its own; a
//    DataCite record without the data steward's ORCID iD gives a gap that says the dataset would not meet the
//    programme's requirement. Its own context, so the pre-filled answers stay out of the other self-check flows.
sections.push(["funded output", async () => {
  const { context, page, external, problems } = await openPage();
  const checked = (id) => page.locator("#" + id).isChecked();
  const part = (name) => navigationRendered(page, () => page.evaluate((target) => { window.location.hash = target; }, "#/cs/V/check/dataset/" + name));
  await gotoView(page, pageUrl + "#/cs/V/check/dataset");
  await rendered(page);
  await page.waitForSelector("#mode-after");
  const programmeItems = graph.filter((e) => e["@type"] === "Question" && [].concat(e.appliesTo || []).some((ref) => String(ref["@id"]).startsWith("#profile-"))).map((e) => e.identifier.replace(".", "-"));
  const outputItems = async () => (await page.locator("fieldset.item").evaluateAll((items) => items.map((item) => item.id.replace("item-", "")))).filter((id) => programmeItems.includes(id)).sort().join(",");
  await page.locator("#mode-before").check();
  if (await page.locator('input[name="profile"]').count()) fail("dataset check: the programme question shows before publication");
  await page.locator("#mode-after").check();
  if ((await page.locator('input[name="profile"]:checked').getAttribute("value")) !== "none" || (await outputItems())) fail("dataset check: the check does not start without a programme and without programme items");
  await page.locator('input[name="profile"][value="minizamer"]').check();
  await part("answers");
  await page.locator('label[for="extended-toggle"]').click();
  if ((await outputItems()) !== "dataset-20,dataset-21,dataset-22,dataset-23") fail("dataset check: the minizáměr programme does not show just the shared requirements: " + (await outputItems()));
  await part("evidence");
  await page.locator('input[name="profile"][value="os3"]').check();
  await part("answers");
  if ((await outputItems()) !== "dataset-20,dataset-21,dataset-22,dataset-23,dataset-24,dataset-25,dataset-26,dataset-27,dataset-28") fail("dataset check: Open Science III does not add its own requirements");
  await page.evaluate(() => {
    const live = window.FairGuide.live;
    live.resolvePid = async () => ({ found: true, url: "https://zenodo.org/records/1", title: "Test" });
    live.datacite = async () => ({ doi: "10.5281/zenodo.1", titles: [{ title: "Test" }], creators: [{ name: "Nováková, Jana", nameIdentifiers: [{ nameIdentifier: "https://orcid.org/0000-0002-1825-0097", nameIdentifierScheme: "ORCID" }] }], contributors: [] });
    live.discoverObject = async (input) => ({ input, pid: live.parsePid(input), date: "2026-10-11T12:00:00Z", supported: true,
      resolved: await live.resolvePid(), datacite: await live.datacite(), representations: [], diagnostics: [], coverage: {} });
  });
  await part("evidence");
  await page.fill("#prefill-steward", "0000-0001-5109-3700");
  await page.locator("#prefill-steward").dispatchEvent("change");
  await page.fill("#prefill-pid", "10.5281/zenodo.1");
  await page.locator("#prefill-pid-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status") && document.getElementById("prefill-status").textContent.includes("Hotovo"));
  await part("answers");
  if (!(await checked("answer-dataset-27-no"))) fail("dataset check: a record without the data steward's ORCID iD does not answer no");
  await part("report");
  const stewardGap = page.locator(".gaps .action-card").filter({ has: page.locator(".item-id", { hasText: /^27$/ }) }).first();
  if (!(await stewardGap.textContent()).includes("nesplnila požadavek programu na výstup (Open Science III") || !(await stewardGap.locator('.id-chip[href$="/catalogue/cl/OS3-RULES.24"]').count())) fail("dataset check: the data steward gap does not say the output requirement is not met, or does not cite the call's rules");
  // A gap's basis names its source the way every citation does: by short name, leading to the catalogue; a
  // question's basis opens under the same label.
  if (!(await stewardGap.locator('a.source-link[href$="/catalogue/res/doc/os3-rules"]').textContent()).includes("Pravidla výzvy Open Science III")) fail("dataset check: the gap does not name the call's rules by their short name, leading to the catalogue");
  await part("answers");
  if (!(await page.locator("#item-dataset-27 details.item-basis > summary").textContent()).startsWith("Vychází z (")) fail("dataset check: a question's basis does not open under the label every view uses");
  // FAIR Champion on the dataset, as a second action after the lookup: each question shows its tests and runs them
  // alone, the lookup result runs them all, and no test runs on an identifier that does not resolve. Four outcomes:
  // a pass answers yes, a fail no, an indeterminate verdict or no result leaves the answer to the quick check; the
  // coverage is stated and a retry runs only the tests without a result. The extended view shows every question.
  await page.waitForSelector("#tests-dataset-07", { state: "attached" });
  if (!(await page.locator('#tests-dataset-07 [data-health="degraded"]').count())) fail("dataset check: a degraded test is not marked at its question");
  await page.evaluate(() => {
    const live = window.FairGuide.live;
    window.championCalls = [];
    live.resolvePid = async () => ({ found: false });
    live.championTest = async (test, record) => {
      window.championCalls.push(test + " " + record);
      const verdicts = { fc_data_identifier_in_metadata: "pass", fc_metadata_includes_license: "fail", fc_unique_identifier: "pass", test_FM_F1_M_IdentPersistent: "indeterminate", community_data_cited_in_pub: "fail" };
      if (!verdicts[test]) throw new Error("no verdict");
      return { value: verdicts[test], log: "log of " + test };
    };
  });
  await page.locator("#item-dataset-03 .question-details > summary").click();
  await page.locator("#test-run-dataset-03").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("nepodařilo přeložit"));
  if (await page.evaluate(() => window.championCalls.length)) fail("dataset check: FAIR Champion was called for an identifier that does not resolve");
  await page.evaluate(() => { window.FairGuide.live.resolvePid = async () => ({ found: true, url: "https://zenodo.org/records/1", title: "Test" }); });
  await page.locator("#test-run-dataset-03").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if ((await page.evaluate(() => window.championCalls.join(","))) !== "fc_data_identifier_in_metadata https://doi.org/10.5281/zenodo.1") fail("dataset check: one question's run did not test only its test, on the DOI as its resolver address");
  if (!(await checked("answer-dataset-03-yes")) || !(await page.locator("#tests-dataset-03").textContent()).includes("splněno")) fail("dataset check: a passed test does not answer dataset.03 yes and show on its line");
  await part("evidence");
  if (!(await page.locator(".champion-all").textContent()).includes("6 otázek")) fail("dataset check: the evidence part does not offer the tests of six questions");
  await page.locator("#prefill-champion-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("5 z 7 testů"));
  await part("answers");
  if ((await page.evaluate(() => window.championCalls.filter((call) => call.startsWith("fc_data_identifier_in_metadata")).length)) !== 1 || (await page.evaluate(() => window.championCalls.length)) !== 7) fail("dataset check: running all tests ran again a test that had a result");
  if (!(await checked("answer-dataset-04-no")) || !(await page.locator("#tests-dataset-04").textContent()).includes("nesplněno")) fail("dataset check: a failed test does not answer dataset.04 no");
  if (!(await checked("answer-dataset-02-yes")) || !(await page.locator("#origin-dataset-02").textContent()).includes("resolver")) fail("dataset check: an indeterminate test replaced the quick check's answer to dataset.02");
  if (!(await page.locator("#test-run-dataset-09").textContent()).includes("Zopakovat")) fail("dataset check: no retry of a test without a result at its question");
  await page.evaluate(() => { window.championCalls = []; window.FairGuide.live.championTest = async (test, record) => (window.championCalls.push(test), { value: "pass", log: "" }); });
  await part("evidence");
  if (!(await page.locator("#prefill-champion-run").textContent()).includes("(2)")) fail("dataset check: no retry of the two tests without a result in the evidence part");
  await page.locator("#prefill-champion-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("7 z 7 testů"));
  if (await page.evaluate(() => window.championCalls.sort().join(",") !== "community_metadata_includes_author_affiliation,fc_metadata_outward_links")) fail("dataset check: the retry ran tests that had a result");
  if (external.length) fail("funded output: requests without a lookup: " + external.join(", "));
  for (const problem of problems) fail("funded output: " + problem);
  console.log("checked the funded-output profile");
  await context.close();
}]);

sections.push(["research practice", async () => {
  const { context, page, external, problems } = await openPage();
  for (const lang of ["cs", "en"]) {
    for (const [id, basic, total] of [["software", 8, 20], ["fdo", 6, 34]]) {
      await page.evaluate(() => {
        if (window.FairGuide && window.FairGuide.state) {
          window.FairGuide.state.answers = {};
          window.FairGuide.saveState();
        }
      });
      await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/check/${id}/answers`));
      await page.waitForSelector(`#item-${entryAnchor(id)}-01`);
      const count = () => page.locator(`.item[id^="item-${entryAnchor(id)}-"]`).count();
      if ((await count()) !== basic) fail(`${id} (${lang}): the first view does not have ${basic} advisory questions`);
      if ((await page.locator(".tier-info").textContent()).includes("Minimum")) fail(`${id}: uses the NDI minimum tier`);
      await page.locator(`#answer-${id}-01-unknown`).check();
      await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/check/${id}/report`));
      if (!(await page.locator("#results .gaps").textContent()).trim()) fail(`${id}: uncertainty has no follow-up`);
      await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/check/${id}/answers`));
      await page.locator('label[for="extended-toggle"]').click();
      if ((await count()) !== total) fail(`${id} (${lang}): the extended check does not have ${total} questions`);
      if (id === "fdo" && ((await page.locator(".item-context").count()) !== 3 || (await page.locator("fieldset.item").count()) !== 31)) fail(`fdo (${lang}): source definitions create extra answerable obligations`);
      if (!(await page.locator(`#answer-${id}-01-unknown`).isChecked())) fail(`${id}: disclosure loses an answer`);
      const roundTrip = await page.evaluate((id) => {
        const fg = window.FairGuide;
        const check = fg.get("#check-" + id);
        const state = fg.state.answers[id];
        const saved = fg.selfcheck.portableState(check, state);
        const read = fg.selfcheck.readPortable(saved);
        const crate = fg.selfcheck.ftrCrate(check, state);
        return { read: Boolean(read.check && read.state), saved: saved.check, results: crate["@graph"].filter((node) => [].concat(node["@type"]).includes("TestResult")).length };
      }, id);
      if (!roundTrip.read || roundTrip.saved !== id || !roundTrip.results) fail(`${id}: export/import contract failed: ${JSON.stringify(roundTrip)}`);
      await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/check/${id}/report`));
      const overview = await page.locator(".result-headline").innerText();
      if (/%|celkové skóre|overall score/i.test(overview.replace(/žádné celkové skóre|no overall score/gi, ""))) fail(`${id}: result shows an overall score`);
    }
    for (const id of ["software", "notebooks", "provenance", "fdo"]) {
      await gotoView(page, pageUrl + `#/${lang}/V/page/${id}`);
      await page.waitForSelector("#main #start");
      const details = page.locator("#main article > details");
      if (!(await details.count()) || await details.first().getAttribute("open")) fail(`${id}: deeper guidance is not disclosed on request`);
      await details.first().locator("summary").click();
      if ((await details.first().getAttribute("open")) === null) fail(`${id}: deeper guidance does not open`);
      for (const width of [390, 1280]) {
        await page.setViewportSize({ width, height: 900 });
        const padding = await details.first().evaluate((box) => {
          const frame = box.getBoundingClientRect();
          const summary = box.querySelector("summary").getBoundingClientRect();
          const content = box.querySelector(".content");
          const first = content && content.firstElementChild;
          if (!first) return false;
          const text = first.getBoundingClientRect();
          return text.left - frame.left >= 8 && frame.right - text.right >= 8 && text.top - summary.bottom >= 8;
        });
        if (!padding) fail(`${id} (${lang}, ${width}px): expanded guidance touches its frame or summary`);
      }
    }
  }
  await gotoView(page, pageUrl + "#/en/V/check/software/answers");
  await page.waitForSelector("#item-software-01");
  await page.locator("#answer-software-01-no").check();
  await gotoView(page, pageUrl + "#/en/V/path/publication");
  await page.waitForFunction(() => window.FairGuide.partsLoaded.has("questions"));
  if (!(await page.locator('.rail-desktop a[href="#/en/V/path/publication"] .rail-mark[data-state="gap"]').count())) fail("software: saved gap is lost after reloading the path");
  if (external.length) fail("research practice: external requests without a lookup: " + external.join(", "));
  for (const problem of problems) fail("research practice: " + problem);
  await context.close();
}]);

sections.push(["research station links", async () => {
  const { context, page, problems } = await openPage();
  for (const lang of ["cs", "en"]) {
    for (const lens of ["V", "DS", "SR", "K"]) {
      for (const id of ["software", "notebooks", "provenance", "fdo"]) {
        await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/${lens}/page/${id}`));
        await page.waitForSelector("#main #start");
        const missing = await page.evaluate(({ id, lang, lens }) => {
          const fg = window.FairGuide;
          const targets = fg.refs(fg.get("#page-" + id), "hasPart")
            .flatMap((section) => fg.config.textLinks[section["@id"]] || [])
            .filter((link) => link.ref.startsWith("#station-"))
            .map((link) => `#/${lang}/${lens}/path/${fg.get(link.ref).identifier}`);
          const actual = [...document.querySelectorAll("#main a.text-ref")].map((link) => link.getAttribute("href"));
          return targets.filter((target) => !actual.includes(target));
        }, { id, lang, lens });
        if (missing.length) fail(`${id} (${lang}, ${lens}): station references do not open the path: ${missing.join(", ")}`);
        if (id === "software" && await page.locator(`#main a[href="#/${lang}/${lens}/path/licence"]`).count()) {
          await page.locator(`#main a[href="#/${lang}/${lens}/path/licence"]`).click();
          await page.waitForSelector(".now-actions");
          if (await page.evaluate(() => !location.hash.includes("/path/licence"))) fail(`software (${lang}, ${lens}): licence link did not open the station`);
        }
      }
    }
  }
  for (const problem of problems) fail("research station links: " + problem);
  await context.close();
}]);

sections.push(["published health and documentation links", async () => {
  const { context, page, external, problems } = await openPage();
  const health = JSON.parse(readFileSync(resolve(site, "api/health.json"), "utf8"));
  const documents = ["health/index.html", "ro-crate-preview.html", "profile/0.1/index.html", "profile/fair-guide/profile.ttl", "terms/index.html", "terms/fair-guide.ttl", "assets/js/tests/index.html"];
  for (const lang of ["cs", "en"]) {
    await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/K/page/machines`));
    const footerLink = page.locator('footer a[href="health/index.html"]');
    if (await footerLink.count() !== 1 || await footerLink.getAttribute("hreflang") !== "en") fail(`${lang}: health dashboard is not linked from the footer with its language`);
    for (const document of documents) {
      if (!(await page.locator(`#main .machine-tasks a[href^="${document}"]`).count())) fail(`${lang}: Data for machines does not link ${document}`);
      if (!existsSync(resolve(site, document))) fail(`${lang}: documentation target is missing: ${document}`);
    }
    await footerLink.click();
    await page.waitForSelector("main h1");
    const text = await page.locator("main").innerText();
    if (!text.includes("Status: " + health.run.status)) fail("health: dashboard and API show different run outcomes");
    if (health.generated_at && !text.includes(health.generated_at)) fail("health: dashboard and API have different timestamps");
    if (!health.generated_at && !text.includes("No completed check run")) fail("health: a plain build claims a completed run");
    for (const href of await page.locator("nav a").evaluateAll((links) => links.map((link) => link.getAttribute("href")))) {
      if (!existsSync(fileURLToPath(new URL(href, page.url())))) fail("health: a published report link is broken: " + href);
    }
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) fail(`health: dashboard overflows at ${width}px`);
      await axe(page, `health dashboard ${lang} ${width}px`);
    }
  }
  if (external.length) fail("health links: opening the dashboard made external requests: " + external.join(", "));
  for (const problem of problems) fail("health links: " + problem);
  await context.close();
}]);

// Every landing shortcut and station action that stays in the guide, in every lens and language, reaches what it
// names: a named catalogue entry opens alone, a topic opens the catalogue narrowed to it with entries, and no link
// opens the catalogue's bare default list of resources.
sections.push(["targets", async () => {
  await mapLimit(["cs", "en"], async (lang) => {
    const { context, page, problems } = await openPage();
    await gotoView(page, pageUrl);
    await rendered(page);
    const visit = (hash) => navigationRendered(page, () => page.evaluate((target) => { window.location.hash = target; }, hash));
    /* A link to the view already open would not navigate; leave it first. */
    const go = async (hash) => {
      if ((await page.evaluate(() => window.location.hash)) === hash) await visit(`#/${lang}/V/explorer`);
      await visit(hash);
    };
    const inGuide = (list) => list.filter(([href]) => href && href.startsWith("#/"));
    const links = new Map();
    for (const lens of lenses) {
      await go(`#/${lang}/${lens}/path/start`);
      const tasks = inGuide(await page.locator(".tasks a.task").evaluateAll((all) => all.map((a) => [a.getAttribute("href"), a.textContent.trim()])));
      if (!tasks.length) fail(`targets: the ${lang}/${lens} landing has no shortcut within the guide`);
      for (const [href, label] of tasks) links.set(href, `${lang}/${lens} shortcut "${label}"`);
      for (const station of stations) {
        await go(`#/${lang}/${lens}/path/${station}`);
        const actions = inGuide(await page.locator(".now-actions a").evaluateAll((all) => all.map((a) => [a.getAttribute("href"), a.textContent.trim()])));
        for (const [href, label] of actions) if (!links.has(href)) links.set(href, `${lang}/${lens} ${station} action "${label}"`);
      }
    }
    for (const [href, where] of links) {
      await go(href);
      const parts = (await page.evaluate(() => window.location.hash)).slice(2).split("/").map(decodeURIComponent);
      if (parts[2] !== "catalogue") continue;
      const cards = await page.locator(".catalogue-results .entry-card").count();
      if (parts[4]) {
        if (cards !== 1) fail(`targets: ${where} names entry ${parts[4]} but shows ${cards} entries`);
      } else if (/^(k!)?resources$/.test(parts[3] || "")) {
        fail(`targets: ${where} opens the bare list of resources (${href})`);
      } else if (!cards) {
        fail(`targets: ${where} opens an empty list (${href})`);
      }
    }
    for (const problem of problems) fail(`targets ${lang}: ${problem}`);
    await context.close();
  }, 1);
}]);

// Controls that cannot act yet wait: in each empty check, helper and filtered-out list, every control that needs an
// identifier, records, text or an answer is inactive and names a visible reason; given what it needs, it acts.
sections.push(["inactive", async () => {
  const { context, page, problems } = await openPage();
  await gotoView(page, pageUrl);
  await rendered(page);
  const go = (hash) => navigationRendered(page, () => page.evaluate((target) => { window.location.hash = target; }, hash));
  const state = (selector) => page.locator(selector).first().evaluate((element) => {
    const ids = (element.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
    const reason = ids.map((id) => document.getElementById(id)).filter((item) => item && !item.hidden && item.offsetParent !== null).map((item) => item.textContent.trim()).join(" | ");
    return { disabled: element.disabled, reason };
  });
  const waits = async (selector, where) => {
    if (!(await page.locator(selector).count())) return;
    const { disabled, reason } = await state(selector);
    if (!disabled) fail(`inactive: ${where}: ${selector} is active but cannot act yet`);
    else if (!reason) fail(`inactive: ${where}: ${selector} is inactive without a visible reason`);
  };
  const acts = async (selector, where) => {
    const { disabled } = await state(selector);
    if (disabled) fail(`inactive: ${where}: ${selector} stays inactive once it can act`);
  };
  const NEEDS = ["pid", "re3data", "nanopub", "software"].flatMap((key) => [`#prefill-${key}-run`, `#prefill-${key}-clear`])
    .concat(["#prefill-sample-run", "#prefill-champion-run", "#export-download", "#export-copy", "#share-create", "#answers-clear"]);
  for (const check of checks) {
    await go(`#/cs/${check.lens}/check/${check.id}`);
    await page.waitForSelector(".check-parts");
    for (const selector of NEEDS) await waits(selector, `empty ${check.id} check`);
  }
  // Given what they need, they act: an identifier, a sample, an answer.
  await go("#/cs/SR/check/maturity");
  await page.fill("#prefill-re3data", "r3d100010386");
  await acts("#prefill-re3data-run", "maturity with a re3data identifier");
  await acts("#prefill-re3data-clear", "maturity with a re3data identifier");
  await page.fill("#prefill-champion", "https://doi.org/10.5281/zenodo.1\nhttps://doi.org/10.5281/zenodo.2");
  await acts("#prefill-sample-run", "maturity with a sample");
  await acts("#prefill-champion-run", "maturity with a sample");
  await go("#/cs/SR/check/maturity/answers");
  await page.locator('input[name="answer-maturity-01"]').first().check();
  await go("#/cs/SR/check/maturity/report");
  for (const selector of ["#export-download", "#export-copy", "#share-create", "#answers-clear"]) await acts(selector, "maturity with an answer");
  await page.evaluate(() => { localStorage.clear(); });
  // The helpers and the landing search wait for text; a list filtered to nothing has nothing to save.
  await go("#/cs/V/page/identifiers");
  await waits(".identifier-helper button[type=submit]", "empty identifier helper");
  await waits(".identifier-helper .field-clear", "empty identifier helper");
  await page.fill("#identifier-text", "10.5281/zenodo.1");
  await acts(".identifier-helper button[type=submit]", "identifier helper with text");
  await go("#/cs/V/page/citation");
  await waits(".citation-helper button[type=submit]", "empty citation helper");
  await waits(".citation-helper .field-clear", "empty citation helper");
  await page.fill("#citation-doi", "10.5281/zenodo.1");
  await acts(".citation-helper button[type=submit]", "citation helper with a DOI");
  await go("#/cs/V/catalogue/k!resources~q!zzzqqqxxx");
  await waits("#export-csv", "an empty list");
  await waits("#export-json", "an empty list");
  await go("#/cs/V/path/start");
  await waits(".search button[type=submit]", "the empty landing search");
  for (const problem of problems) fail("inactive: " + problem);
  await context.close();
}]);

// The life-cycle models in the catalogue: every stage is listed, and the path's reuse stage shows its definition as
// published and each correspondence with its basis and source, the unconfirmed one marked (guide-knowledge-base,
// "Life-cycle models and their crosswalk are records"). A name the guide translated says so.
sections.push(["life cycle", async () => {
  const stageCount = graph.filter((e) => /^#lifecycle-[^.]+\./.test(e["@id"])).length;
  const citing = graph.filter((e) => e["@type"] === "HowToSection" && e.lifecycleStage && e.lifecycleStage["@id"] === "#lifecycle-rdmkit.reuse").map((e) => e.identifier);
  if (!stageCount || !citing.length) fail("life cycle: the crate has no life-cycle stages or no station in the reuse stage");
  await mapLimit(["cs", "en"], async (lang) => {
    const { context, page, problems } = await openPage();
    await gotoView(page, pageUrl);
    await rendered(page);
    const visit = (hash) => navigationRendered(page, () => page.evaluate((target) => { window.location.hash = target; }, hash));
    const card = page.locator(".catalogue-results .entry-card");
    await visit(`#/${lang}/K/catalogue/lifecycle`);
    if ((await card.count()) !== stageCount) fail(`life cycle ${lang}: the list shows ${await card.count()} stages, the crate has ${stageCount}`);
    await visit(`#/${lang}/K/catalogue/life/rdm/reuse`);
    if ((await card.count()) !== 1) fail(`life cycle ${lang}: the reuse stage's entry is not shown alone`);
    // Both languages state the same definition: RDMkit's own in English, the Guide's marked translation in Czech; KNAV's
    // Czech wording follows as a quotation that keeps its stage label.
    if ((await card.locator(".stage-definition").first().getAttribute("lang")) !== lang) fail(`life cycle ${lang}: the definition is not given in ${lang}`);
    const translated = (await card.textContent()).includes(lang === "cs" ? "Překlad Průvodce z RDMkit" : "Translated by the Guide");
    if (translated !== (lang === "cs")) fail(`life cycle ${lang}: the Guide's translation is ${translated ? "claimed for the source's text" : "not marked"}`);
    const quote = card.locator(".stage-quote");
    if ((await quote.count()) !== 1 || !(await quote.textContent()).startsWith("Opakované užití dat: ") || (await quote.getAttribute("lang")) !== "cs") fail(`life cycle ${lang}: KNAV's Czech definition is not quoted with its stage label`);
    if (await card.locator(".card-details").count()) fail(`life cycle ${lang}: the published RDMkit/KNAV name is marked as translated`);
    const rows = await card.locator(".crosswalk li").evaluateAll((all) => all.map((li) => ({
      basis: li.dataset.basis, target: decodeURIComponent(li.querySelector("a").getAttribute("href")), sources: li.querySelectorAll(".source-link").length,
    })));
    const row = (stage) => {
      const entity = graph.find((entry) => entry["@id"] === "#lifecycle-" + stage);
      return rows.find((item) => item.target.endsWith("/" + entity?.catalogueAddress));
    };
    for (const [stage, basis] of Object.entries({ "maldreth.access": "unconfirmed", "maldreth.transform": "reviewed", "knav-tools.reusing": "reviewed" })) {
      if (!row(stage)) fail(`life cycle ${lang}: the reuse stage does not list ${stage}`);
      else if (row(stage).basis !== basis) fail(`life cycle ${lang}: ${stage} is marked ${row(stage).basis}, not ${basis}`);
    }
    if (row("maldreth.access") && !row("maldreth.access").sources) fail(`life cycle ${lang}: the unconfirmed correspondence names no source`);
    const sources = await card.locator(".relations .source-link").count();
    if (sources < 2) fail(`life cycle ${lang}: the stage cites ${sources} source(s); RDMkit and KNAV expected`);
    const steps = await card.locator(".relations .holder-link").evaluateAll((all) => all.map((a) => a.getAttribute("href")));
    for (const station of citing) if (!steps.some((href) => href.endsWith("/path/" + station))) fail(`life cycle ${lang}: the stage does not lead to its step ${station}`);
    await visit(`#/${lang}/K/catalogue/life/mld/access`);
    const marked = await card.locator(".card-details").count();
    if ((lang === "cs") !== (marked === 1)) fail(`life cycle ${lang}: the guide's translated name is ${marked ? "" : "not "}marked`);
    for (const problem of problems) fail(`life cycle ${lang}: ${problem}`);
    await context.close();
  }, 1);
}]);

// A stage chosen and stored by an earlier version of the guide is ignored: the path's start shows the journey with no
// stage marked, and the next save drops the stored choice.
sections.push(["stored stage", async () => {
  const { context, page, problems } = await openPage();
  await gotoView(page, pageUrl);
  await rendered(page);
  await page.evaluate(() => localStorage.setItem("eosc-fair-guide", JSON.stringify({ lang: "cs", lens: "V", started: true, entryStation: "repository" })));
  await gotoView(page, pageUrl + "#/cs/V/path");
  await page.reload();
  await rendered(page);
  if (!(await page.locator("#journey-title").count())) fail("stored stage: the path does not open its start for a visitor who has read no step");
  if (await page.locator(".journey-last").count()) fail("stored stage: an older stored stage marks the journey");
  await navigationRendered(page, () => page.evaluate(() => { window.location.hash = "#/cs/V/path/plan"; }));
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem("eosc-fair-guide")));
  if ("started" in stored || "entryStation" in stored) fail("stored stage: the stored choice survives a save");
  if (stored.lastStation !== "plan") fail("stored stage: reading a step is not remembered");
  for (const problem of problems) fail(`stored stage: ${problem}`);
  await context.close();
}]);

// The KNAV tools catalogue in the catalogue: a tool no entry stands for is listed once under its catalogue identifier,
// with its steps, disciplines and licence, and reaches the guide's steps through the crosswalk; an entry that is a
// catalogue tool is listed once, marked, and opens from the tool's identifier; a plain-HTTP address is not linked.
sections.push(["knav catalogue", async () => {
  const tools = graph.filter((e) => /^#knav-/.test(e["@id"]) && e["@id"] !== "#knav-tools");
  const unlinked = tools.filter((e) => !e.sameAs);
  if (!tools.length || tools.length === unlinked.length) fail("knav catalogue: the crate has no tools, or none an entry stands for");
  const { context, page, problems } = await openPage();
  await gotoView(page, pageUrl);
  await rendered(page);
  const visit = (hash) => navigationRendered(page, () => page.evaluate((target) => { window.location.hash = target; }, hash));
  const cards = page.locator(".catalogue-results .entry-card");
  // The catalogue's view code is not part of the first download; it loads when the catalogue first opens.
  const viewCode = () => page.locator('script[src$="assets/js/catalogue-view.js"]').count();
  if (await viewCode()) fail("knav catalogue: the catalogue view's code loads before the catalogue opens");
  /* Each tool is one entry: among the resources, or among the repositories and registries when one stands for it. */
  const listed = [];
  for (const kind of ["resources", "repositories"]) {
    await visit(`#/cs/K/catalogue/k!${kind}~f.use!knav`);
    listed.push(...(await cards.evaluateAll((all) => all.map((card) => card.id.replace(/^item-/, "")))));
  }
  if ((await viewCode()) !== 1) fail("knav catalogue: opening the catalogue did not load its view code once");
  const borrowed = listed.filter((id) => unlinked.some((tool) => tool.catalogueAddress.split("/").slice(1).join("/") === id));
  if (borrowed.length !== unlinked.length) fail(`knav catalogue: ${borrowed.length} tools listed under their own identifier, ${unlinked.length} expected`);
  if (listed.length !== tools.length) fail(`knav catalogue: the KNAV use lists ${listed.length} entries for ${tools.length} tools`);
  await visit("#/cs/K/catalogue/res/tool/ais-cr");
  const card = cards.first();
  if (!(await card.locator('a[href*="/catalogue/life/knav/reusing"]').count())) fail("knav catalogue: a tool does not lead to its catalogue step");
  if (!(await card.locator('.relations a.holder-link[href$="/path/citation"]').count())) fail("knav catalogue: a reusing tool does not reach the citation step");
  if ((await card.locator(".card-details").textContent()).trim() === "") fail("knav catalogue: a tool shows no discipline");
  if (!(await card.locator('a[href^="https://www.gnu.org/licenses/gpl-3.0"]').count())) fail("knav catalogue: a tool does not show the catalogue's licence");
  await visit("#/cs/K/catalogue/k!resources~s!citation~f.use!knav~f.discipline!social-sciences-humanities");
  if (!(await page.locator("[id=\"item-tool/ais-cr\"]").count())) fail("knav catalogue: the station and discipline filters miss a matching tool");
  await visit("#/cs/K/catalogue/res/tool/kadi4mat");
  if ((await cards.count()) !== 1 || (await cards.first().getAttribute("id")) !== "item-tool/kadi4mat") fail("knav catalogue: a tool an entry stands for does not open that entry");
  if (!(await cards.first().textContent()).includes("v katalogu nástrojů KNAV")) fail("knav catalogue: the entry that is a catalogue tool is not marked");
  await visit("#/cs/K/catalogue/res/tool/eduroam");
  if (await cards.first().locator('a[href^="http:"]').count()) fail("knav catalogue: a plain-HTTP address is linked");
  if (!(await cards.first().locator('a[href^="https://openscience.lib.cas.cz/"]').count())) fail("knav catalogue: a plain-HTTP tool does not lead to the catalogue");
  for (const problem of problems) fail(`knav catalogue: ${problem}`);
  await context.close();
}]);

// One visual system for catalogue entries (guide-experience, "Catalogue entries share one visual system"): every
// entry carries its kind's mark and colour, the kind facet shows the same marks, each kind has its own icon and
// colour, labelled rows carry one icon per label in one order, and a tool or service carries the same badge in the
// catalogue and among a step's resources, while a standard carries none.
sections.push(["visual system", async () => {
  const kinds = ["resources", "repositories", "infrastructures", "clauses", "questions", "terms", "fips", "tests", "lifecycle", "model", "actions"];
  const ROW_ORDER = ["Principy", "Pro koho", "Provozovatel", "Vyvinuli", "Provozuje", "Národní uzel", "Členství v ERIC", "Profil FIP komunity", "Vychází z", "V Průvodci", "Identifikátory", "Vrstvy implementace", "Návaznosti"];
  const { context, page, problems } = await openPage();
  await gotoView(page, pageUrl);
  await rendered(page);
  const visit = (hash) => navigationRendered(page, () => page.evaluate((target) => { window.location.hash = target; }, hash));
  const marks = new Map();
  const rowIcons = new Map();
  for (const kind of kinds) {
    await visit(`#/cs/K/catalogue/k!${kind}`);
    const seen = await page.locator(".catalogue-results .entry-card").evaluateAll((cards) =>
      cards.slice(0, 12).map((card) => {
        return {
          id: card.id,
          kind: card.dataset.kind,
          marked: Boolean(card.querySelector(".entry-head .kind-mark")),
          strip: getComputedStyle(card).borderTopColor,
          rows: [...card.querySelectorAll(":scope > .relations:not(.model-detail) > dt")].map((dt) => dt.textContent.trim()),
          labelled: [...card.querySelectorAll(".relations > dt")].map((dt) => ({ text: dt.textContent.trim(), icon: dt.querySelector("use") ? dt.querySelector("use").getAttribute("href") : null })),
        };
      })
    );
    if (!seen.length) fail(`visual system: no ${kind} entries to compare`);
    for (const card of seen) {
      if (card.kind !== kind) fail(`visual system: ${card.id} in ${kind} is marked as ${card.kind}`);
      // The kind shows in the facet and as the card's top strip; a card carries no kind mark of its own (D-185).
      if (card.marked) fail(`visual system: ${card.id} repeats its kind's mark`);
      if ((marks.get(kind) || card.strip) !== card.strip) fail(`visual system: ${kind} entries carry different strips`);
      marks.set(kind, card.strip);
      const order = card.rows.map((row) => ROW_ORDER.indexOf(row));
      if (order.includes(-1) || order.some((index, at) => at && index <= order[at - 1])) fail(`visual system: ${card.id}'s rows are not in the fixed order: ${card.rows.join(", ")}`);
      for (const row of card.labelled) {
        if (!row.icon) fail(`visual system: ${card.id}'s row "${row.text}" has no icon`);
        if ((rowIcons.get(row.text) || row.icon) !== row.icon) fail(`visual system: the row "${row.text}" carries different icons`);
        rowIcons.set(row.text, row.icon);
      }
    }
  }
  if (new Set(marks.values()).size !== kinds.length) fail("visual system: two kinds share a colour");
  const facet = await page.locator(".facet-kinds li label").evaluateAll((labels) => labels.map((label) => [label.getAttribute("for"), label.querySelector(".kind-mark use")?.getAttribute("href"), getComputedStyle(label.querySelector(".kind-mark")).backgroundColor]));
  const kindIcons = new Map();
  for (const [id, icon, colour] of facet) {
    const kind = id.replace("facet-kind-", "");
    if (!icon) fail(`visual system: the kind facet shows no icon for ${kind}`);
    kindIcons.set(kind, icon);
    if (marks.get(kind) !== colour) fail(`visual system: the kind facet colours ${kind} (${colour}) differently from its entries' strip (${marks.get(kind)})`);
  }
  if (new Set(kindIcons.values()).size !== kinds.length) fail("visual system: two kinds share an icon");

  // A service's badge: the same favicon, or the same kind icon and colour, at a step and in the catalogue; its own
  // favicon wherever the page has one, and loaded from the page's own files; a tool on a code-hosting platform shows
  // its kind's icon, never a two-letter monogram; none on a standard (D-183, D-185).
  const badge = (card) => card.locator(".entry-title > .service-badge").evaluateAll((nodes) => nodes.map((node) =>
    [node.dataset.service, node.textContent.trim(), (node.querySelector("use") || { getAttribute: () => "" }).getAttribute("href"), getComputedStyle(node).backgroundColor, (node.querySelector("img") || {}).src || ""].join(" ")));
  const favicons = new Set(JSON.parse(readFileSync(resolve(site, "assets/data/ui.js"), "utf8").match(/^window\.FairGuideData\.ui = (.*);$/m)[1]).config.favicons.hosts);
  await visit("#/cs/K/catalogue/repo/reg/nkr");
  const nkrBadge = page.locator(".catalogue-results .entry-card .entry-title > .service-badge img");
  if (!favicons.has("repo.cz") || !(await nkrBadge.count()) || !(await nkrBadge.getAttribute("src")).endsWith("assets/favicons/repo.cz.png")) fail("visual system: NKR does not show its own favicon");
  else if (!(await nkrBadge.evaluate((image) => image.complete && image.naturalWidth === 48))) fail("visual system: NKR's favicon does not load from the page's files");
  await visit("#/cs/K/catalogue/res/tool/qualianon");
  if (await page.locator(".catalogue-results .entry-card .entry-title > .service-badge img").count()) fail("visual system: a tool on GitHub shows GitHub's favicon as its own");
  const placeholder = page.locator(".catalogue-results .entry-card .entry-title > .service-placeholder");
  if (!(await placeholder.count()) || (await placeholder.locator("use").getAttribute("href")) !== kindIcons.get("resources") || (await placeholder.textContent()).trim())
    fail("visual system: a tool without a favicon does not show the resources kind's icon in place of one");
  await visit("#/cs/K/catalogue/repo/dom/benchmark-energy-geometry");
  if (await page.locator(".catalogue-results .entry-card .entry-title > .service-badge img").count()) fail("visual system: a repository linked by its re3data record shows re3data's favicon as its own");
  await visit("#/cs/V/path/repository");
  const badged = page.locator("#main .station .entry-card").filter({ has: page.locator(".entry-title > .service-badge") });
  if (!(await badged.count())) fail("visual system: no service at the repository step carries a badge");
  else {
    const service = (await badged.first().getAttribute("id")).replace(/^item-/, "");
    const atStep = await badge(badged.first());
    const address = graph.find((entity) => entity.catalogueAddress?.split("/").slice(1).join("/") === service)?.catalogueAddress;
    if (!address) throw new Error(`no published address for ${service}`);
    await visit(`#/cs/K/catalogue/${address}`);
    const inCatalogue = await badge(page.locator(".catalogue-results .entry-card").first());
    if (atStep.length !== 1 || atStep[0] !== inCatalogue[0]) fail(`visual system: ${service}'s badge differs between the step (${atStep}) and the catalogue (${inCatalogue})`);
  }
  await visit("#/cs/K/catalogue/res/tool/fair-checker");
  if ((await badge(page.locator(".catalogue-results .entry-card").first()))[0]?.split(" ")[0] !== "fair-checker") fail("visual system: the evaluator's catalogue entry is not badged under the key the self-check uses");
  const standard = graph.find((r) => r.resourceType?.["@id"] === "#rtype-standard" && r.identifier);
  await visit(`#/cs/K/catalogue/${standard.catalogueAddress}`);
  // A standard is no service: it shows its kind's icon before its title, not a service's badge (D-185).
  {
    const card = page.locator(".catalogue-results .entry-card").first();
    if ((await card.locator(".entry-title > .service-badge[data-service]").count()) || (await card.locator(".entry-title > .service-placeholder use").getAttribute("href")) !== kindIcons.get("resources")) fail(`visual system: the standard ${standard.identifier} does not show its kind's icon, or carries a service's badge`);
  }
  for (const problem of problems) fail(`visual system: ${problem}`);
  await context.close();
}]);

// The glossary carries licensed original descriptions, and phrases in them find the term in both search views.
sections.push(["glossary definitions", async () => {
  const { context, page, problems, external } = await openPage();
  await gotoView(page, pageUrl);
  await rendered(page);
  const visit = (hash) => navigationRendered(page, () => page.evaluate((target) => { window.location.hash = target; }, hash));
  const terms = graph.filter((node) => node.inDefinedTermSet?.["@id"] === "#glossary");
  const description = (term) => [].concat(term.description || []).find((value) => value["@language"] === "cs")?.["@value"];
  const described = terms.filter(description);
  if (described.length !== terms.length) fail("glossary: the reviewed snapshot lost a source definition");
  const term = described.find((entry) => description(entry).length > 200);
  const phrase = description(term).split(/\s+/).slice(8, 12).join(" ");
  const anchor = term.catalogueAddress.split("/").slice(1).join("/");
  for (const language of ["cs", "en"]) {
    await visit(`#/${language}/V/catalogue/k!terms`);
    const cards = page.locator(".catalogue-results .term-card");
    if ((await cards.locator(".term-definition").count()) !== (await cards.count())) fail(`glossary ${language}: descriptions are missing from term cards`);
    if ((await cards.locator('.term-attribution a[href="https://creativecommons.org/licenses/by/4.0/"]').count()) !== (await cards.count())) fail(`glossary ${language}: licence attribution is missing`);
    await visit(`#/${language}/V/catalogue/k!terms~q!${encodeURIComponent(phrase)}`);
    const card = page.locator(`[id="item-${entryAnchor(anchor)}"]`);
    if (!(await card.count())) fail(`glossary ${language}: a definition-only phrase does not find its term`);
    else {
      await card.locator(".term-definition summary").click();
      if (!(await card.locator(".term-definition").innerText()).replace(/\s+/g, " ").includes(phrase)) fail(`glossary ${language}: the source description is not retained`);
      if (await card.locator(".term-definition script, .term-definition img").count()) fail("glossary: source markup was executed");
      if (!(await card.locator(`[href="${term.url}"]`).count())) fail("glossary: the source term is not linked");
    }
    const found = await page.evaluate((phrase) => window.FairGuide.search.find(phrase).find((group) => group.kind === "term")?.items.map((item) => item.target.href) || [], phrase);
    if (!found.some((href) => href.endsWith("/term/" + anchor))) fail(`glossary ${language}: general search does not index definitions`);
    for (const format of ["csv", "json"]) {
      const [download] = await Promise.all([page.waitForEvent("download"), page.locator("#export-" + format).click()]);
      const output = readFileSync(await download.path(), "utf8");
      const definitionText = format === "json" ? JSON.parse(output).itemListElement.find((entry) => entry.identifier === term.catalogueAddress)?.description?.cs || "" : output;
      if (!definitionText.replace(/\s+/g, " ").includes(phrase)) fail(`glossary ${language}: ${format} export lost the definition`);
      if (!output.includes(term.url) || !output.includes("https://creativecommons.org/licenses/by/4.0/")) fail(`glossary ${language}: ${format} export lost attribution`);
    }
    await page.setViewportSize({ width: 320, height: 900 });
    await axe(page, "glossary definitions " + language);
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) fail(`glossary ${language}: description overflows at phone width`);
    await page.setViewportSize({ width: 1280, height: 900 });
  }
  if (external.length) fail("glossary: external requests without a user lookup: " + external.join(", "));
  for (const problem of problems) fail(`glossary: ${problem}`);
  await context.close();
}]);

// The answers step counts answers as they are given, and the result so far stays beside the questions on a wide
// screen and follows them on a phone.
sections.push(["check parts", async () => {
  const { context, page, problems } = await openPage();
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await gotoView(page, pageUrl + "#/en/SR/check/maturity/answers");
    await rendered(page);
    await page.evaluate(() => { window.FairGuide.clearStoredData(); window.FairGuide.rerender(); });
    await page.waitForSelector("#main .item");
    const note = page.locator("#parts-answers-note");
    const before = await note.textContent();
    await page.locator('#main .item input[type="radio"][value="yes"]').first().check();
    const after = await note.textContent();
    if (!/^0 /.test(before) || !/^1 /.test(after)) fail(`check parts (${width}px): the answers step does not count an answer as it is given: ${before} → ${after}`);
    const place = await page.evaluate(() => {
      const panel = document.querySelector(".check-summary").getBoundingClientRect();
      const main = document.querySelector(".check-main").getBoundingClientRect();
      return { shown: panel.height > 0, beside: panel.left >= main.right, after: panel.top >= main.bottom };
    });
    if (!place.shown) fail(`check parts (${width}px): the result so far is not shown`);
    else if (width > 900 ? !place.beside : !place.after) fail(`check parts (${width}px): the result so far is not ${width > 900 ? "beside" : "after"} the questions`);
  }
  // Crossing the wide-screen width (turning a tablet, zooming) re-renders the check and keeps the focus.
  await page.locator('#main .item input[type="radio"][value="yes"]').first().focus();
  const focused = await page.evaluate(() => document.activeElement.id);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.waitForFunction(() => document.querySelector(".check-summary .summary-controls"));
  if ((await page.evaluate(() => document.activeElement.id)) !== focused) fail("check parts: crossing the wide-screen width loses the focus");
  // Withdrawing by keyboard reaches the count, the result so far and the export like any other change of answer.
  const first = await page.locator("#main .item").first().getAttribute("id");
  const id = first.replace("item-", "");
  await page.locator("#withdraw-" + id).press("Enter");
  await page.waitForFunction((key) => !document.getElementById("withdraw-" + key), id);
  if (!/^0 /.test(await page.locator("#parts-answers-note").textContent())) fail("check parts: withdrawing an answer does not reach the answers step's count");
  if (await page.locator(`input[name="answer-${id}"]:checked`).count()) fail("check parts: a withdrawn answer without a suggestion stays chosen");
  if (!/Answered 0 of \d/.test(await page.locator(".check-summary").innerText())) fail("check parts: the result so far still counts a withdrawn answer");
  if (!(await page.evaluate((key) => document.activeElement && document.activeElement.name === "answer-" + key, id))) fail("check parts: withdrawing by keyboard does not return the focus to the question's answers");
  const exported = await page.evaluate(() => { const SC = window.FairGuide.selfcheck; return JSON.stringify(SC.portableState(window.FairGuide.get("#check-maturity"), window.FairGuide.state.answers.maturity)); });
  if (exported.includes('"value":"yes"')) fail("check parts: the export still carries a withdrawn answer");
  // An evaluator's work carries its badge beside its name: FAIR Champion's tests in a question's details, and its
  // column in the report's table of answers and evaluators.
  await page.evaluate(() => { window.FairGuide.state.answers.maturity = { items: {}, extended: true }; window.FairGuide.saveState(); window.FairGuide.rerender(); });
  const testHead = page.locator("#tests-maturity-11 .test-label");
  if (!(await testHead.locator(".service-badge").count()) || !(await testHead.textContent()).includes("FAIR Champion")) fail("check parts: FAIR Champion's tests do not carry its badge and name");
  await page.locator('#main .item input[type="radio"][value="no"]').first().check();
  await page.evaluate(() => { window.location.hash = "#/en/SR/check/maturity/report"; });
  await page.waitForSelector('.check-parts [aria-current="step"][href$="/report"]');
  const column = page.locator("th .evaluator-name", { hasText: "FAIR Champion" });
  if (!(await column.count()) || !(await column.first().locator(".service-badge").count())) fail("check parts: the report's evaluator column does not carry FAIR Champion's badge and name");
  for (const problem of problems) fail(`check parts: ${problem}`);
  await context.close();
}]);

// Names in the reader's language with their abbreviations (guide-experience, "Names appear in the reader's language
// with their abbreviations"): a Czech reader finds the Czech Social Science Data Archive by "CSDA" and by "ČSDA", it
// reads with its Czech abbreviation, and the English form stays on the entry; an English page the other way round.
sections.push(["repository names", async () => {
  const { context, page, problems } = await openPage();
  const cards = async (lang, query) => {
    await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/catalogue/k!repositories~q!${encodeURIComponent(query)}`));
    await page.waitForSelector("#main .entry-card");
    return page.$$eval("#main .entry-card", (els) => els.map((card) => [card.querySelector(".entry-title").textContent, card.querySelector(".card-details")?.textContent || ""]));
  };
  for (const query of ["CSDA", "ČSDA"]) {
    const found = (await cards("cs", query)).find(([title]) => title.includes("Český sociálněvědní datový archiv (ČSDA)"));
    if (!found) fail(`repository names: "${query}" does not find "Český sociálněvědní datový archiv (ČSDA)" on a Czech page`);
    else if (!found[1].includes("Czech Social Science Data Archive (CSDA)")) fail("repository names: the English form is not on the Czech entry");
  }
  const english = (await cards("en", "ČSDA")).find(([title]) => title.includes("Czech Social Science Data Archive (CSDA)"));
  if (!english || !english[1].includes("Český sociálněvědní datový archiv (ČSDA)")) fail("repository names: the English entry does not read with its abbreviation and keep the Czech form");
  for (const problem of problems) fail(`repository names: ${problem}`);
  await context.close();
}]);

// The EOSC CZ Node and the large research infrastructures (guide-knowledge-base, "EOSC CZ Node membership is recorded
// with its state", "Large research infrastructures keep distinct relations"; guide-experience, "EOSC CZ Node
// membership is visible"): ČSDA carries the node badge with its planned milestone, the date checked and the charter,
// and is operated by CSDA/ESS-CZ, which is the Czech node of CESSDA and ESS and operates ČSDA; MBDB names its
// developers and no operator; the node facet narrows the repositories to the node's; a node service carries the
// badge among a step's resources too.
sections.push(["node and infrastructures", async () => {
  const { context, page, problems } = await openPage();
  const visit = (hash) => navigationRendered(page, () => page.goto(pageUrl + hash));
  const card = (text) => page.locator("#main .entry-card", { hasText: text }).first();
  const rows = (entry) => entry.locator(".relations").evaluate((list) => Object.fromEntries([...list.querySelectorAll(":scope > dt")].map((dt) => [dt.textContent.trim(), dt.nextElementSibling.textContent.replace(/\s+/g, " ").trim()])));
  await visit("#/cs/K/catalogue/k!repositories~q!CSDA");
  await page.waitForSelector("#main .entry-card");
  const csda = card("Český sociálněvědní datový archiv (ČSDA)");
  const badge = (await csda.locator(".node-badge").count()) ? await csda.locator(".node-badge").textContent() : "";
  if (!/EOSC CZ Node · zapojení plánováno do M12 · ověřeno/.test(badge) || !(await csda.locator('.node-badge a[href*="EOSC_CZ_National_Node_Charter"]').count())) fail("node: ČSDA does not carry the node badge with its milestone, date and charter: " + badge);
  if (!((await rows(csda))["Provozovatel"] || "").includes("CSDA/ESS-CZ")) fail("node: ČSDA does not name CSDA/ESS-CZ as its operator");
  for (const lang of ["cs", "en"]) {
    await visit(`#/${lang}/K/catalogue/ri/ssh/csda-ess-cz`);
    const labels = await page.locator("#catalogue-order option").allTextContents();
    if (labels.some((label) => label.startsWith("catalogue.orderBy."))) fail(`infrastructures: untranslated ${lang} ordering: ${labels.join(", ")}`);
  }
  await visit("#/cs/K/catalogue/ri/ssh/csda-ess-cz");
  await page.waitForSelector("#main .entry-card");
  const infra = await rows(card("CSDA/ESS-CZ"));
  if (!/CESSDA ERIC/.test(infra["Národní uzel"] || "") || !/ESS ERIC/.test(infra["Národní uzel"] || "")) fail("infrastructures: CSDA/ESS-CZ is not the node of CESSDA and ESS: " + JSON.stringify(infra));
  if (!(infra["Provozuje"] || "").includes("ČSDA")) fail("infrastructures: CSDA/ESS-CZ does not operate ČSDA");
  if (!/Annex 7|Annex 1/.test(infra["Vychází z"] || "") && !/Cestovní mapa/.test(infra["Vychází z"] || "")) fail("infrastructures: CSDA/ESS-CZ does not cite the roadmap");
  await visit("#/cs/K/catalogue/repo/dom/mbdb");
  await page.waitForSelector("#main .entry-card");
  const mbdb = await rows(card("MBDB"));
  if (!/Biotechnologický ústav AV ČR a CESNET/.test(mbdb["Vyvinuli"] || "") || mbdb["Provozovatel"]) fail("infrastructures: MBDB does not name its developers without an operator: " + JSON.stringify(mbdb));
  await visit("#/cs/K/catalogue/k!repositories~f.node!" + encodeURIComponent("#noderole-repository"));
  await page.waitForSelector("#main .entry-card");
  const members = await page.locator("#main .catalogue-results .entry-card").count();
  const badges = await page.locator("#main .catalogue-results .entry-card .node-badge").count();
  // Seven of the charter's eight repositories are catalogue repositories; the RECETOX libraries are reference data.
  if (members !== 7 || badges !== members) fail(`node: the node facet does not narrow the repositories to the node's seven (${members} entries, ${badges} badges)`);
  await visit("#/cs/V/path/analyse");
  await page.waitForSelector(".station-resources");
  if (!(await page.locator(".station-resources .entry-card", { hasText: "Galaxy" }).locator(".node-badge").count())) fail("node: Galaxy carries no node badge among the analysis step's resources");
  for (const problem of problems) fail(`node and infrastructures: ${problem}`);
  await context.close();
}]);

// Hiding path badges is a local display preference; it never changes answers or step navigation.
sections.push(["rail check visibility", async () => {
  const { context, page, problems } = await openPage();
  await gotoView(page, pageUrl + "#/cs/SR/check/maturity/answers");
  await rendered(page);
  await page.locator('input[type="radio"][value="no"]').first().check();
  const visit = (hash) => navigationRendered(page, () => page.evaluate((target) => { window.location.hash = target; }, hash));
  await visit("#/cs/SR/path/plan");
  const answers = await page.evaluate(() => JSON.stringify(window.FairGuide.state.answers));
  const desktop = page.locator("#rail-show-checks-desktop");
  if (!(await desktop.isChecked()) || !(await page.locator(".rail-desktop .rail-marks").first().isVisible())) fail("rail visibility: check badges are not shown by default");
  await desktop.focus();
  await page.keyboard.press("Space");
  if (await page.locator(".rail-desktop .rail-marks:visible").count()) fail("rail visibility: keyboard toggle did not hide badges");
  if ((await page.evaluate(() => document.activeElement.id)) !== "rail-show-checks-desktop") fail("rail visibility: toggling lost keyboard focus");
  await page.reload();
  await rendered(page);
  if ((await desktop.isChecked()) || (await page.locator(".rail-desktop .rail-marks:visible").count())) fail("rail visibility: hidden badges return after reload");
  await visit("#/en/SR/path/plan");
  if ((await desktop.isChecked()) || (await page.locator(".rail-desktop .rail-marks:visible").count())) fail("rail visibility: language change resets the preference");
  if ((await page.locator('.rail-desktop a[aria-current="step"]').count()) !== 1) fail("rail visibility: current-step navigation was hidden");
  await page.setViewportSize({ width: 390, height: 900 });
  await page.locator(".rail-mobile > summary").click();
  const mobile = page.locator("#rail-show-checks-mobile");
  if (await mobile.isChecked()) fail("rail visibility: phone and desktop disagree");
  await mobile.focus();
  await page.keyboard.press("Space");
  if (!(await page.locator(".rail-mobile .rail-marks").first().isVisible()) || !(await desktop.isChecked())) fail("rail visibility: phone toggle did not restore badges in both menus");
  if (!(await page.locator(".rail-mobile").evaluate((menu) => menu.open))) fail("rail visibility: toggling closed the phone menu");
  if ((await page.evaluate(() => JSON.stringify(window.FairGuide.state.answers))) !== answers) fail("rail visibility: toggling changed saved answers");
  await mobile.uncheck();
  await page.evaluate(() => { window.FairGuide.clearStoredData(); window.FairGuide.rerender(); });
  if (!(await mobile.isChecked()) || (await page.evaluate(() => window.FairGuide.storage.read().hideCheckBadges))) fail("rail visibility: deleting local data did not reset the preference");
  for (const problem of problems) fail(`rail visibility: ${problem}`);
  await context.close();
}]);

// Kind radios share the middle line of the icon, label and count, including wrapped labels.
sections.push(["facet alignment", async () => {
  const { context, page, problems } = await openPage();
  await gotoView(page, pageUrl);
  await rendered(page);
  for (const language of ["cs", "en"]) {
    await navigationRendered(page, () => page.evaluate((code) => { window.location.hash = `#/${code}/V/catalogue/k!questions`; }, language));
    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      const facets = page.locator(".catalogue-facets");
      if (!(await facets.evaluate((node) => node.open))) await facets.locator(":scope > summary").click();
      const offsets = await page.locator(".facet-kinds li").evaluateAll((rows) => rows.map((row) => {
        const centre = (node) => { const box = node.getBoundingClientRect(); return box.top + box.height / 2; };
        const radio = row.querySelector("input");
        const label = row.querySelector("label");
        return {
          id: radio.id,
          offsets: [radio, label.querySelector(".kind-mark"), label.querySelector(".facet-count")].map((node) => Math.abs(centre(node) - centre(label))),
        };
      }));
      for (const row of offsets) if (row.offsets.some((offset) => offset > 1))
        fail(`facet alignment: ${language} ${width}px ${row.id} has centre offsets ${row.offsets.join(", ")}`);
    }
  }
  for (const problem of problems) fail(`facet alignment: ${problem}`);
  await context.close();
}]);

// Catalogues the guide links (guide-knowledge-base, "Catalogues of tools and repositories are linked"): a researcher
// on the analysis step finds the SSH Open Marketplace among its resources, OpenDOAR is listed with the repository
// directories, and the KNAV catalogue's record of the Marketplace opens the Guide's entry.
sections.push(["linked catalogues", async () => {
  const { context, page, problems } = await openPage();
  await gotoView(page, pageUrl);
  await rendered(page);
  const visit = (hash) => navigationRendered(page, () => page.evaluate((target) => { window.location.hash = target; }, hash));
  await visit("#/cs/V/path/analyse");
  if (!(await page.locator('#main .station [id="item-reg/ssh-open-marketplace"]').count())) fail("linked catalogues: the analysis step does not recommend the SSH Open Marketplace to researchers");
  await visit("#/cs/K/catalogue/repo/reg/opendoar");
  const card = page.locator(".catalogue-results .entry-card");
  if ((await card.count()) !== 1 || !(await card.first().locator(".entry-what").textContent()).includes("Hledat repozitáře")) fail("linked catalogues: OpenDOAR is not listed with the repository directories");
  await visit("#/cs/K/catalogue/repo/reg/ssh-open-marketplace");
  if ((await card.first().getAttribute("id")) !== "item-reg/ssh-open-marketplace") fail("linked catalogues: the KNAV record of the Marketplace does not open the Guide's entry");
  for (const problem of problems) fail(`linked catalogues: ${problem}`);
  await context.close();
}]);

sections.push(["Licence compatibility", async () => {
  const { context, page, problems } = await openPage({ width: 320, height: 900 });
  // Independent transcription of the published NRP v1.0 table, p. 14, in its printed column order.
  const names = ["BY", "BY-SA", "BY-NC", "BY-ND", "BY-NC-SA", "BY-NC-ND", "CC0"];
  const expected = ["1110101", "1100001", "1010101", "0000000", "1010101", "0000000", "1110101"];
  for (const lang of ["cs", "en"]) {
    await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/page/licence-compatibility`));
    const table = page.locator("#main .text-table");
    const actual = await table.locator("tbody tr").evaluateAll((rows) => rows.map((row) => [...row.querySelectorAll("td")].map((cell) => {
      const text = cell.cloneNode(true);
      text.querySelectorAll('[aria-hidden="true"]').forEach((icon) => icon.remove());
      return ["ano", "yes"].includes(text.textContent.trim()) ? "1" : "0";
    }).join("")));
    if (actual.join(",") !== expected.join(",")) fail(`licence matrix: ${lang} differs from NRP`);
    if (await table.locator('th[scope="row"]').count() !== names.length || await table.locator('th[scope="col"]').count() !== names.length + 1) fail("licence matrix: missing native row/column headers");
    if (await page.locator('#main select').count()) fail("licence matrix: a selector replaced the flat guidance table");
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) fail("licence table: horizontal page overflow at 320px");
    await axe(page, `licence table ${lang}`);
    await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/tools`));
    if (!await page.locator('.tool-group[aria-labelledby="tools-guidance"] a[href$="/page/licence-compatibility"]').count()) fail("licence table: missing from Guides");
    await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/catalogue/term/public-licence`));
    const quote = page.locator("#main blockquote");
    if (!await quote.count() || !(await quote.first().textContent()).includes("standardizovan")) fail(`original definitions: missing public-licence source text in ${lang}`);
    if (!await page.locator('#main details a[href$="/res/guide/copyright-licences"]').count()) fail(`original definitions: missing NRP attribution in ${lang}`);
  }
  for (const problem of problems) fail(`licence compatibility: ${problem}`);
  await context.close();
}]);

sections.push(["Read steps and situations", async () => {
  const { context, page, problems } = await openPage();
  const visit = (hash) => navigationRendered(page, () => page.goto(pageUrl + hash));
  for (const lang of ["cs", "en"]) for (const lens of ["V", "DS", "SR", "K"]) {
    await visit(`#/${lang}/${lens}/path/start`);
    const shortcuts = page.locator(".tasks a");
    if (await shortcuts.count() !== 4) fail(`shortcuts: expected four situations for ${lang}/${lens}`);
    const hrefs = await shortcuts.evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    if (hrefs.some((href) => !href.includes("/path/"))) fail(`shortcuts: a ${lang}/${lens} situation bypasses its step`);
    /* A visit marks nothing: the read mark is the reader's own, and every step offers the control (D-190). */
    if (await page.locator(".journey-steps [data-read][data-state='read']").count()) fail(`read steps: ${lang}/${lens} marked a step without the reader`);
    if (await page.locator(".journey-steps [data-read]").count() !== 11) fail(`read steps: ${lang}/${lens} does not offer a read control on every step`);
    for (const width of [1280, 320]) {
      await page.setViewportSize({ width, height: 900 });
      for (const problem of await compactControlProblems(page)) fail(`read steps: ${lang}/${lens}/${width}: ${problem}`);
    }
    await page.setViewportSize({ width: 1280, height: 900 });
  }
  await visit("#/cs/V/path/plan");
  if (!await page.locator('#main a[href="https://dmp.eosc.cz/"]').count()) fail("shortcuts: planning has no DMP next action");
  await visit("#/cs/V/path/licence");
  for (const problem of await compactControlProblems(page)) fail(`read steps rail: ${problem}`);
  /* The reader marks two steps by hand; nothing marks itself, and the mark is theirs to take off again. */
  await page.locator('.rail-desktop [data-read="plan"]').click();
  await page.locator('.rail-desktop [data-read="licence"]').click();
  for (const id of ["plan", "licence"]) if (!await page.locator(`.rail-desktop [data-read="${id}"][data-state="read"]`).count()) fail(`read steps: missing rail mark ${id}`);
  await page.reload();
  await page.waitForSelector("#main h1");
  await visit("#/en/DS/path/start");
  if (await page.locator(".journey-steps [data-read][data-state='read']").count() !== 2) fail("read steps: marks did not survive reload and language/role change");
  await page.locator('.journey-steps [data-read="plan"]').click();
  if (await page.locator('[data-read="plan"][data-state="read"]').count()) fail("read steps: a mark cannot be taken off");
  if (await page.locator('[data-read="licence"][data-state="read"]').count() !== 1) fail("read steps: taking one mark off changed another");
  await page.evaluate(() => window.FairGuide.clearStoredData());
  await visit("#/cs/DS/path/start");
  await page.reload();
  await page.waitForSelector("#main h1");
  if (await page.locator("[data-read][data-state='read']").count()) fail("read steps: clear-local-data retained marks");
  for (const problem of problems) fail(`read steps: ${problem}`);
  await context.close();
}]);

sections.push(["RDMkit reuse", async () => {
  const { context, page, problems } = await openPage();
  for (const lang of ["cs", "en"]) {
    await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/catalogue/res/tool/elabftw`));
    const entries = page.locator("#main .catalogue-results .entry-card");
    if (await entries.count() !== 1) fail(`RDMkit: eLabFTW has duplicate ${lang} entries`);
    if (!await entries.locator('a[href="https://rdmkit.elixir-europe.org/all_tools_and_resources#elabftw"]').count()) fail(`RDMkit: missing ${lang} tool record`);
    if (!await entries.locator('a[href*="tess.elixir-europe.org/search?"]').count()) fail(`RDMkit: missing ${lang} training search`);
    await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/path/plan`));
    if (!await page.locator('#main a[href$="/rdmkit-researcher"]').count()) fail(`RDMkit: researcher role missing at ${lang} planning`);
    await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/K/path/metadata`));
    if (!await page.locator('#main a[href$="/cookbook-dictionary"]').count()) fail(`RDMkit: dictionary recipe missing at ${lang} metadata`);
  }
  for (const problem of problems) fail(`RDMkit reuse: ${problem}`);
  await context.close();
}]);

sections.push(["Workflow guidance", async () => {
  const { context, page, problems } = await openPage();
  for (const lang of ["cs", "en"]) for (const lens of ["V", "DS", "SR", "K"]) {
    await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/${lens}/path/analyse`));
    const resource = { V: "conda-environments", DS: "conda-environments", SR: "workflow-ro-crate", K: "workflow-ro-crate" }[lens];
    if (!await page.locator(`.steps a[href$="${cataloguePath("resources", resource)}"]`).count()) fail(`workflows: missing ${lang}/${lens} analysis guidance`);
    if (!await page.locator('#main a[href$="/page/software"]').count()) fail(`workflows: missing ${lang}/${lens} software-page link`);
  }
  for (const lang of ["cs", "en"]) {
    await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/V/page/software`));
    const workflows = page.locator("#workflows");
    for (const id of ["conda", "workflow-ro-crate", "workflowhub", "galaxy-cz", "jupyterhub-cerit", "lexis"]) {
      const kind = id === "workflowhub" ? "repositories" : "resources";
      if (!await workflows.locator(`a[href$="${cataloguePath(kind, id)}"]`).count()) fail(`workflows: missing ${lang} ${id}`);
    }
  }
  for (const problem of problems) fail(`workflow guidance: ${problem}`);
  await context.close();
}]);

sections.push(["Infrastructure marks", async () => {
  const { context, page, problems } = await openPage();
  const records = graph.filter((entity) => entity["@id"].startsWith("#infrastructure-") && entity.identifier);
  const marks = JSON.parse(readFileSync(resolve(site, "assets/data/ui.js"), "utf8").match(/^window\.FairGuideData\.ui = (.*);$/m)[1]).config.favicons.marks;
  for (const lang of ["cs", "en"]) for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const record of records) {
      await navigationRendered(page, () => page.goto(pageUrl + `#/${lang}/K/catalogue/${record.catalogueAddress}`));
      const image = page.locator(".catalogue-results .entry-title .service-favicon img");
      const expected = marks["infrastructure-" + record.identifier];
      if (expected) {
        if (await image.count()) { await image.scrollIntoViewIfNeeded(); await image.evaluate((i) => i.decode()); }
        if (!await image.count() || !await image.evaluate((i) => i.complete && i.naturalWidth === 48)) fail(`infrastructure marks: ${record.identifier} does not load ${expected}`);
      } else if (await image.count()) fail(`infrastructure marks: ${record.identifier} inherited a portal or institutional favicon`);
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) fail(`infrastructure marks: ${lang} ${width}px ${record.identifier} overflows`);
    }
  }
  for (const problem of problems) fail(`infrastructure marks: ${problem}`);
  await context.close();
}]);

sections.push(["catalogue text reference", async () => {
  const { context, page, problems } = await openPage();
  await gotoView(page, pageUrl + "#/en/V/path/plan");
  await rendered(page);
  // A borrowed tool need not have loaded yet: referenceHref reads the build's emitted address.
  await page.evaluate(() => {
    const FG = window.FairGuide;
    const owner = { "@id": "#text-reference-check", text: "Use GitHub for collaboration." };
    FG.config.textLinks[owner["@id"]] = [{ ref: "#knav-github", en: "GitHub" }];
    const paragraph = FG.h("p", { id: "catalogue-reference-check" }, FG.linkedSpan(owner));
    document.querySelector("#main").append(paragraph);
  });
  const link = page.locator("#catalogue-reference-check a.text-ref");
  if ((await link.getAttribute("href")) !== "#/en/V/catalogue/res/tool/github") fail("catalogue text reference: the tool does not use its issued address");
  await navigationRendered(page, () => link.click());
  const cards = page.locator(".catalogue-results .entry-card");
  if ((await cards.count()) !== 1 || (await cards.first().getAttribute("id")) !== "item-tool/github") fail("catalogue text reference: following a tool name does not reach its entry alone");
  const term = graph.find((entity) => entity["@id"] === "#term-public-licence");
  await navigationRendered(page, () => page.goto(pageUrl + "#/en/V/catalogue/" + term.catalogueAddress));
  if ((await cards.count()) !== 1) fail("catalogue text reference: a canonical term does not open one entry");
  for (const entity of [graph.find((e) => e.catalogueAddress?.startsWith("org/")), graph.find((e) => e["@id"] === "#implementation-model")]) {
    await navigationRendered(page, () => page.goto(pageUrl + "#/en/V/catalogue/" + entity.catalogueAddress));
    if ((await cards.count()) !== 1) fail("catalogue text reference: a published record outside the facets has no direct entry");
    if ((await cards.first().locator(".entry-head .id-chip").textContent()) !== entity.catalogueAddress.split("/").at(-1)) fail("catalogue text reference: a direct record shows a second address");
    if ((await cards.first().locator(".entry-title").textContent()).includes("[object Object]")) fail("catalogue text reference: a language value is rendered as an object");
    await axe(page, "direct catalogue record " + entity.catalogueAddress);
  }
  for (const problem of problems) fail(`catalogue text reference: ${problem}`);
  await context.close();
}]);

// Named sections retain individual verdicts, timings and failure artifacts; selected runs remain partial.
const only = (process.env.CHECK_PAGE_SECTIONS || "").split(",").map((name) => name.trim()).filter(Boolean);
const results = await runCases(sections, only);
for (const result of results.filter((item) => item.status === "failed")) {
  for (const problem of result.problems) if (!failures.includes(problem)) failures.push(`${result.name}: ${problem}`);
}
console.log("sections: " + results.map((item) => `${item.name} ${item.seconds.toFixed(1)}s`).join(", "));
await browser.close();
if (failures.length) {
  console.error(failures.map((failure) => "FAIL " + failure).join("\n"));
  console.error(`${failures.length} problem(s)`);
  process.exitCode = 1;
} else console.log(only.length ? "selected page checks passed (partial coverage)" : "page checks passed");
