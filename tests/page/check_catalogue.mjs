// The catalogue hides nothing (design D8): every field a catalogue entry's record carries is shown by its kind or
// excluded with a reason, and every shown field with a value draws visible text in the entry's card.
import { mkdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { audit } from "./accessibility.mjs";
import { installGuards } from "./guards.mjs";

const root = resolve(import.meta.dirname, "../..");
const site = resolve(root, process.env.FAIR_GUIDE_SITE || "_site");
const temporary = resolve(root, ".cache/browser-temp");
mkdirSync(temporary, { recursive: true });
process.env.TEMP = temporary;
process.env.TMP = temporary;
const { chromium } = await import("./browser.mjs");
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();
const { state, problems: errors } = installGuards(page, { allowed: (url) => /^(?:file|data):/.test(url) });
const base = pathToFileURL(resolve(site, "index.html")).href;

await page.goto(base + "#/cs/V/catalogue/k!resources");
await page.waitForSelector(".catalogue-layout");

const problems = await page.evaluate(() => {
  const FG = window.FairGuide;
  const { kinds, notShown, shown, outside, within } = FG.catalogueFields;
  const entries = FG.catalogueEntries();
  const found = new Map();
  const note = (kind, field, problem, id) => {
    const key = kind + ": " + field + " " + problem;
    found.set(key, (found.get(key) || []).concat(id));
  };
  /* A value counts when it says something: false does, an empty list does not. */
  const present = (value) => value !== null && value !== undefined && value !== "" && !(Array.isArray(value) && !value.length);
  const listed = new Set();
  for (const [kind, list] of Object.entries(entries)) {
    const declared = kinds[kind];
    if (!declared) {
      note(kind, "*", "is a kind without declared fields", "");
      continue;
    }
    for (const entry of list) {
      const entity = entry.entity;
      listed.add(entity["@id"]);
      const card = entry.render();
      for (const [field, value] of Object.entries(entity)) {
        const isShown = shown.includes(field) || declared.shown.includes(field);
        if (!isShown && !(field in notShown) && !(field in declared.excluded)) note(kind, field, "is neither shown nor excluded with a reason", entity["@id"]);
        else if (isShown && present(value)) {
          /* A name that only repeats the entry's ID is what its ID chip shows; a declared default draws nothing. */
          if (field === "name" && FG.text(value) === entity.identifier) continue;
          if ((declared.defaults || {})[field]?.values.includes(value)) continue;
          const marked = [...card.querySelectorAll("[data-field]")].filter((node) => node.dataset.field.split(" ").includes(field));
          if (!marked.some((node) => node.textContent.trim())) note(kind, field, "is shown by the kind but its card draws nothing", entity["@id"]);
        }
      }
    }
  }
  /* Every addressed record is a list entry, or the catalogue says where else it shows. */
  const kindOf = (code) => FG.catalogueKind(code);
  for (const entity of FG.graph.filter((item) => item.catalogueAddress && !listed.has(item["@id"]))) {
    const code = entity.catalogueAddress.split("/")[0];
    const types = [].concat(entity["@type"]);
    if (outside[code] || types.some((type) => (within[kindOf(code)] || {})[type])) continue;
    note(kindOf(code), "(record)", "has an address but is neither listed nor shown inside another entry", entity["@id"]);
  }
  return [...found.entries()].map(([key, ids]) => key + " (" + ids.length + ": " + ids.slice(0, 3).join(", ") + (ids.length > 3 ? ", …" : "") + ")").sort();
});

// The entries design D8 names, read as a reader sees them: the facts each kind gains, both ends of each relation, and
// a folded list that opens by keyboard and is built only then.
const graph = JSON.parse(readFileSync(resolve(site, "ro-crate-metadata.json"), "utf8"))["@graph"];
const byId = new Map(graph.map((entity) => [entity["@id"], entity]));
const list = (value) => [].concat(value ?? []);
const fail = (message) => problems.push(message);
/* Shows one entry and waits for its own card, not the card the previous view left. */
const show = async (hash) => {
  const anchor = decodeURIComponent(hash.split("/catalogue/")[1]).split("/").slice(1).join("/");
  await page.goto(base + hash);
  await page.waitForSelector(`.catalogue-results [id="item-${anchor}"]`);
  return page.locator(`.catalogue-results [id="item-${anchor}"]`).first();
};
const open = (id, lang = "cs") => show(`#/${lang}/V/catalogue/${byId.get(id).catalogueAddress}`);
const row = async (card, label) => {
  const term = card.locator(".relations dt", { hasText: label });
  return (await term.count()) ? term.first().evaluate((node) => node.nextElementSibling.textContent) : "";
};
/* Opens every folded list on the card, which builds it, and waits until it is built. */
const unfold = (card) => card.evaluate(async (node) => {
  for (const fold of node.querySelectorAll("details")) fold.open = true;
  await new Promise((done) => setTimeout(done, 50));
});
const items = (card, field) => card.locator(`dd[data-field="${field}"] li`).count();

for (const [id, consulted, changed] of [["#action-2026-10-16-initial-state", 143, 1374], ["#action-2026-10-18-station-dedup", 25, 18]]) {
  const action = byId.get(id);
  const card = await open(id);
  const person = byId.get(action.agent["@id"]).name;
  if (!(await card.locator(".entry-byline").textContent()).includes(person)) fail(`catalogue: ${id} does not name ${person} in its byline`);
  if ((await items(card, "instrument")) !== list(action.instrument).length || !(await row(card, "Nástroje")).includes("model AI")) fail(`catalogue: ${id} does not list each tool with its kind`);
  const summary = card.locator('dd[data-field="result"] details > summary').first();
  if (await summary.count()) {
    const before = await items(card, "result");
    await summary.focus();
    await page.keyboard.press("Enter");
    await page.waitForTimeout(50);
    if (!(await summary.evaluate((node) => node.parentElement.open)) || (await items(card, "result")) <= before) fail(`catalogue: ${id} does not open and build a folded list by keyboard`);
  }
  await unfold(card);
  if ((await items(card, "object")) !== consulted || (await items(card, "result")) !== changed) fail(`catalogue: ${id} does not list its ${consulted} consulted and ${changed} changed records`);
  const unresolved = await card.evaluate((node) => {
    const addresses = new Set(Object.values(window.FairGuide.config.api.records));
    return [...node.querySelectorAll('dd[data-field="object"] a, dd[data-field="result"] a')]
      .map((link) => decodeURIComponent(link.getAttribute("href") || ""))
      .filter((href) => href.includes("/catalogue/") && !addresses.has(href.split("/catalogue/")[1]));
  });
  if (unresolved.length) fail(`catalogue: ${id} links records the catalogue does not have: ${unresolved.slice(0, 3).join(", ")}`);
}
if (!(await row(await open("#action-2026-10-16-initial-state", "en"), "Tools")).includes("AI model")) fail("catalogue: the English change does not name an AI model as a tool");
{
  // A page of the Guide that a change altered leads to that page, named by its heading rather than its ID. The Guide
  // record links to the About page too, so the heading is looked for among every such link, in whatever group order.
  const card = await open("#action-2026-10-26-workflow-follow-up", "en");
  await unfold(card);
  const about = await card.locator('dd[data-field="result"] a[href$="/page/about"]').allTextContents();
  if (!about.map((text) => text.trim()).includes("About the Guide")) fail("catalogue: a change does not link the About page by its heading: " + about.join(", "));
}
{
  // A context question says what it is in the self-check's words, not by an interface key.
  const context = await (await open("#item-fdo.09", "en")).locator('[data-field="assessmentContext"]').textContent();
  if (!context.startsWith("Original source context.") || context.includes("catalogue.")) fail("catalogue: fdo.09 does not say it is source context: " + context);
}

{
  const card = await open("#item-dataset.01");
  if (!(await row(card, "Kdo to napraví")).includes("správce repozitáře")) fail("catalogue: dataset.01 does not say who puts it right");
  if (!/po zveřejnění.*netýká se/.test(await row(card, "Kdy se ptá"))) fail("catalogue: dataset.01 does not say when it applies and whether “not applicable” is offered");
  const prefill = await row(card, "Předvyplňuje se z");
  const localTest = list(byId.get("#test-guide-dataset-01").name).find((value) => value["@language"] === "cs")?.["@value"];
  if (!["DataCite", "FAIR Champion", localTest, "jen z podkladů FAIR Champion"].every((text) => prefill.includes(text))) fail("catalogue: dataset.01 does not list its pre-fill sources with their limits: " + prefill);
  // An entry's changes stay in the catalogue's list of changes: the entry's corner counts them and leads there.
  const changes = card.locator(".entry-links .changes-link");
  if (!(await changes.count()) || (await card.locator(".relations dt", { hasText: "Změny" }).count())) fail("catalogue: dataset.01 does not lead to its changes from its corner, or lists them in the entry");
  else {
    await page.goto(base + (await changes.getAttribute("href")));
    await page.waitForSelector(".catalogue-results .change");
    const listed = await page.locator(".catalogue-results").textContent();
    const chip = await page.locator(".active-filters").textContent();
    if (!listed.includes("Initial public Guide state") || !chip.includes("dataset.01") || (await page.locator('[data-facet="actions-record"]').count())) fail("catalogue: dataset.01's changes are not the catalogue's changes narrowed to it, with a filter that can be removed");
  }
  // The catalogue is not read in a role: it names the self-check's "you" by its role, the researcher.
  const fixer = await row(await open("#item-dataset.15"), "Kdo to napraví");
  if (!fixer.includes("výzkumník") || /(?<!\p{L})vy(?!\p{L})/u.test(fixer)) fail("catalogue: a question addresses the reader in its Who puts it right row: " + fixer);
  const cdif = await open("#item-cdif.01");
  if (!(await row(cdif, "Skupina")).trim()) fail("catalogue: cdif.01 does not show its group");
}

{
  const card = await open("#fip-csda");
  const summary = await card.locator('dd[data-field="hasPart"] summary').textContent();
  if (!summary.includes("18 deklarací: 17 se používá, 1 plánovaná")) fail("catalogue: the ČSDA profile does not summarise its declarations by status: " + summary);
  if (await card.locator(".declarations-table").count()) fail("catalogue: the declarations table is built before it is opened");
  await unfold(card);
  if ((await card.locator(".declarations-table tbody tr").count()) !== 18) fail("catalogue: the ČSDA profile does not list its 18 declarations");
  if (!(await card.locator('dd.relation-wide[data-field="hasPart"]').count())) fail("catalogue: the declarations do not take the card's full width");
  if (await card.locator('dd[data-field="hasPart"] summary a').count() || !(await card.locator('dd[data-field="hasPart"] .fold-box > a.fold-action[target="_blank"]').count())) fail("catalogue: the full-page link is not an action in the declarations box's header");
  const fullPage = await card.locator('dd[data-field="hasPart"] a[target="_blank"]').getAttribute("href");
  const planned = await card.locator('.declarations-table tr:has([data-declaration="planned"]) td:nth-child(2) a').first().getAttribute("href");
  await page.goto(base + fullPage);
  await page.waitForSelector(".catalogue-table-page .declarations-table");
  if ((await page.locator(".catalogue-table-page .declarations-table tbody tr").count()) !== 18 || (await page.locator(".catalogue-facets").count())) fail("catalogue: the ČSDA declarations do not open on a page of their own");
  if (!(await row(await show(planned), "Deklarováno v")).includes("ČSDA")) fail("catalogue: the resource ČSDA plans does not list the profile under Declared in");
}

{
  const source = graph.find((entity) => String(entity["@id"]).startsWith("#source-") && String(entity.license || "").includes("creativecommons.org/licenses/by/4.0"));
  if (!(await row(await open(source["@id"]), "Licence")).includes("CC BY 4.0")) fail(`catalogue: ${source["@id"]} does not show its licence as a row named from the data`);
  const term = graph.find((entity) => String(entity["@id"]).startsWith("#term-"));
  if (!(await (await open(term["@id"])).locator(".quote-licence").textContent()).includes("CC BY 4.0")) fail("catalogue: a term does not name its definition's licence beside it");
  const infrastructure = await open("#infrastructure-elixir-cz");
  if (!(await row(infrastructure, "Provozovatel")).trim()) fail("catalogue: an infrastructure does not show its host as Operated by");
  const healthy = graph.find((entity) => entity.healthStatus && entity.statusAsOf);
  const badge = (await open(healthy["@id"])).locator("[data-health]");
  if (!(await badge.locator('[aria-hidden="true"]').count()) || !/ověřeno/.test(await badge.textContent())) fail("catalogue: a test's health is not one badge with icon, text and as-of date");
  const criterion = graph.find((entity) => String(entity["@id"]).startsWith("#criterion-") && list(entity.hasPart).length);
  const criterionCard = await open(criterion["@id"]);
  await unfold(criterionCard);
  if ((await items(criterionCard, "hasPart")) !== list(criterion.hasPart).length) fail("catalogue: a criterion's mappings are not its Covers row");
  if (!(await (await open("#lifecycle-rdmkit.plan")).locator(".relations dt", { hasText: "Odpovídá" }).count())) fail("catalogue: a life-cycle stage does not show what it corresponds to as a row");
}

{
  if (!(await row(await open("#test-guide-dataset-01"), "Předvyplňuje")).includes("dataset.01")) fail("catalogue: a local test does not list the question it pre-fills");
  if (!(await row(await open("#clause-A.R1.1.N2"), "Nahrazeno")).includes("DSW-NRP.01")) fail("catalogue: a superseded requirement does not name what replaced it");
  const replaces = await row(await open("#clause-DSW-NRP.01"), "Nahrazuje");
  if (!replaces.includes("A.R1.1.N2") || !replaces.includes("A.K2.2.2")) fail("catalogue: a requirement does not list the requirements it replaces");
}

for (const id of ["#action-2026-10-18-station-dedup", "#fip-csda"]) {
  await unfold(await open(id));
  state.axeRunning = true;
  const result = await audit(page);
  state.axeRunning = false;
  for (const violation of result.violations) fail(`catalogue: ${id} accessibility: ${violation.id} at ${violation.nodes.map((node) => node.target).join(", ")}`);
}

await browser.close();
const failures = problems.concat(errors.map((error) => "page error: " + error));
for (const problem of failures) console.log("catalogue: " + problem);
if (failures.length) process.exitCode = 1;
else console.log("catalogue: every record field is shown or excluded with a reason");
