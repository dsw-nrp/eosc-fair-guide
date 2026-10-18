// The model organises guidance through explicit mappings, without changing source criteria or implying coverage.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";
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
const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
const page = await context.newPage();
const base = pathToFileURL(resolve(site, "index.html")).href;
const graph = JSON.parse(readFileSync(resolve(site, "ro-crate-metadata.json"), "utf8"))["@graph"];
const terms = graph.filter((entry) => ["layer", "seam"].includes(entry.modelKind));
const refs = (entry, property) => [].concat(entry?.[property] || []).map((reference) => reference["@id"]);
const get = (id) => graph.find((entry) => entry["@id"] === id);
const questionEntries = graph.filter((entry) => entry["@type"] === "Question");
const {state, problems: errors, external} = installGuards(page, {
  allowed: (url) => /^(?:file|data):/.test(url),
});
const screenshots = resolve(root, ".cache/screenshots/model");
mkdirSync(screenshots, { recursive: true });

async function visit(hash, selector = "#main h1") {
  const previous = await page.$("#main");
  await page.goto(base + hash);
  if (previous) await page.waitForFunction((node) => !node.isConnected, previous);
  await page.waitForSelector(selector);
}
async function choose(selector) {
  const previous = await page.$("#main");
  await page.locator(selector).check();
  await page.waitForFunction((node) => !node.isConnected, previous);
}
async function accessible() {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "the model reflows");
  state.axeRunning = true;
  const result = await audit(page);
  state.axeRunning = false;
  assert.deepEqual(result.violations.map((violation) => ({ id: violation.id, targets: violation.nodes.map((node) => node.target) })), []);
}
async function download(selector) {
  const waiting = page.waitForEvent("download");
  await page.locator(selector).click();
  return readFileSync(await (await waiting).path(), "utf8");
}
async function expectedQuestions(seams, layers = []) {
  const expected = questionEntries.filter((item) => (!seams.length || refs(item, "implementationSeams").some((id) => seams.includes(id))) &&
    (!layers.length || refs(item, "implementationLayers").some((id) => layers.includes(id))));
  assert.equal(await page.locator(".entry-card").count(), expected.length, "AND between model dimensions, OR within one dimension");
  for (const item of expected) assert.equal(await page.locator(`[id="item-${item.identifier}"] .model-tag`).count(), refs(item, "implementationLayers").length + refs(item, "implementationSeams").length, "associations are visible in the record");
}

try {
  assert.equal(terms.filter((entry) => entry.modelKind === "layer").length, 6);
  assert.equal(terms.filter((entry) => entry.modelKind === "seam").length, 12);
  assert(terms.every((entry) => !entry.serviceStatus && !entry.statusAsOf), "a generic connection definition does not claim implementation status");
  assert.equal(graph.filter((entry) => entry.modelKind === "example").length, 3);
  // Fresh entry must resolve every step without borrowing data from an earlier catalogue or check visit.
  for (const lang of ["cs", "en"]) for (const destination of ["model", "machines"]) {
    const fresh = await browser.newContext();
    try {
      const direct = await fresh.newPage();
      await direct.goto(base + `#/${lang}/K/page/${destination}`);
      await direct.waitForSelector(".model-worked-example");
      const example = direct.locator(".model-worked-example");
      assert.equal(await example.locator("ol > li").count(), 4, "direct page entry resolves all four example records");
      const test = graph.find((entry) => entry.identifier === "guide-dataset-01");
      const label = test.name.find((value) => value["@language"] === lang)["@value"];
      assert((await example.locator('li:has(a[href*="/test/"])').textContent()).includes(label), "the test step shows its human-readable title beside its ID");
    } finally { await fresh.close(); }
  }
  for (const lang of ["cs", "en"]) {
    await page.evaluate(() => { if (window.FairGuide) { window.FairGuide.state.answers = {}; window.FairGuide.saveState(); } });
    await page.setViewportSize({ width: 1280, height: 900 });
    await visit(`#/${lang}/K/tools`, ".tool-cards");
    const modelIcon = await page.locator('.tool-card:has(a[href$="/page/model"]) svg use').getAttribute("href");
    assert(modelIcon && (await page.locator('.tool-card svg use').evaluateAll((icons) => icons.map((icon) => icon.getAttribute("href")))).filter((icon) => icon === modelIcon).length === 1, "the model has its own distinct tool icon");
    await visit(`#/${lang}/K/catalogue/k!model`, ".catalogue-results");
    assert.equal(await page.locator(".entry-card").count(), 18);
    assert.equal(await page.locator('[data-facet="seams"]').count(), 1, "model records expose the shared connection facet");
    assert.equal(await page.locator('[for="facet-seams-seam-repository-nma"] .facet-count').textContent(), "1", "the connection definition counts itself without a self-association");
    const infrastructureCount = terms.filter((entry) => entry["@id"] === "#layer-infrastructure" || refs(entry, "implementationLayers").includes("#layer-infrastructure")).length;
    assert.equal(await page.locator('[for="facet-layers-layer-infrastructure"] .facet-count').textContent(), String(infrastructureCount), "layer counts include the layer definition and its connections");
    await choose("#facet-seams-seam-repository-nma");
    assert.deepEqual(await page.locator(".entry-card").evaluateAll((cards) => cards.map((card) => card.id)), ["item-seam/repository-nma"]);
    const modelExport = JSON.parse(await download("#export-json"));
    assert.deepEqual(modelExport.itemListElement[0].implementationSeams, [], "identity filtering does not invent a self-association in exported records");
    for (const kind of ["resources", "repositories", "clauses", "questions", "terms", "fips", "tests", "model", "actions"]) {
      await visit(`#/${lang}/K/catalogue/k!${kind}`, ".catalogue-results");
      const anchor = (await page.locator(".entry-card").first().getAttribute("id")).replace(/^item-/, "");
      await visit(`#/${lang}/K/catalogue/k!${kind}~q!${encodeURIComponent(anchor.toUpperCase())}`, ".catalogue-results");
      assert.equal(await page.locator(`[id="item-${anchor}"]`).count(), 1, `the ${kind} catalogue finds its displayed ID case-insensitively`);
    }
    await visit(`#/${lang}/K/catalogue/k!model`, ".catalogue-results");
    // The model's icon marks its kind in the facet; entries carry the kind's colour, not its icon (D-185).
    assert.equal(await page.locator(`.facet-kinds label[for="facet-kind-model"] use[href="${modelIcon}"]`).count(), 1, "the kind facet marks model records with its icon");
    assert.equal(await page.locator(".entry-card .entry-head .kind-mark").count(), 0, "model records do not repeat the kind's icon");
    await choose("#facet-model-modelKind-layer");
    assert.equal(await page.locator(".entry-card").count(), 6);
    await visit(`#/${lang}/K/catalogue/k!questions~n!%23seam-repository-nma`, ".catalogue-results");
    await expectedQuestions(["#seam-repository-nma"]);
    assert(await page.evaluate(() => {
      const kind = document.querySelector('[data-facet="kind"]');
      const layers = document.querySelector('[data-facet="layers"]');
      const seams = document.querySelector('[data-facet="seams"]');
      const own = document.querySelector(".facet-kind");
      return [layers, seams].every((facet) => Boolean(kind.compareDocumentPosition(facet) & Node.DOCUMENT_POSITION_FOLLOWING) &&
        Boolean(facet.compareDocumentPosition(own) & Node.DOCUMENT_POSITION_FOLLOWING));
    }), "Kind stays above shared model filters; type-specific filters remain below them");
    const independentCount = questionEntries.filter((item) => refs(item, "implementationSeams").includes("#seam-community-repository")).length;
    assert.equal(await page.locator('[for="facet-seams-seam-community-repository"] .facet-count').textContent(), String(independentCount), "connection counts exclude their own selection");
    await choose("#facet-seams-seam-community-repository");
    await expectedQuestions(["#seam-repository-nma", "#seam-community-repository"]);
    await choose("#facet-layers-layer-community");
    await expectedQuestions(["#seam-repository-nma", "#seam-community-repository"], ["#layer-community"]);
    await choose("#facet-kind-tests");
    assert.equal(await page.locator('[data-facet="seams"] input:checked').count(), 2, "connection selection survives a kind switch");
    assert.equal(await page.locator('[data-facet="layers"] input:checked').count(), 1, "layer selection survives a kind switch");
    assert(page.url().includes("n!") && page.url().includes("l!"));
    await choose("#facet-kind-questions");
    await expectedQuestions(["#seam-repository-nma", "#seam-community-repository"], ["#layer-community"]);
    const saved = page.url();
    await page.reload();
    await page.waitForSelector('[data-facet="seams"] input:checked');
    assert.equal(page.url(), saved, "the route reopens the same filters");
    const json = JSON.parse(await download("#export-json"));
    assert(json.itemListElement.every((item) => item.implementationLayers.length && item.implementationSeams.length), "JSON export retains the associations");
    const csv = await download("#export-csv");
    assert(csv.includes("#seam-community-repository") && csv.includes("#layer-community"), "CSV retains stable model references");
    await visit(`#/${lang}/K/catalogue/k!questions~n!%23seam-repository-nma`, ".catalogue-results");
    // Plant a blind propagation defect: an unrelated question is wrongly classified by a broadly cited source.
    const unrelated = questionEntries.find((item) => !refs(item, "implementationSeams").includes("#seam-repository-nma"));
    await page.evaluate((id) => { const FG = window.FairGuide; const item = FG.get(id); window.modelSavedRefs = item.implementationSeams;
      item.implementationSeams = [{ "@id": "#seam-repository-nma" }]; FG.invalidateData(); FG.render(); }, unrelated["@id"]);
    await assert.rejects(() => expectedQuestions(["#seam-repository-nma"]), "the regression check rejects blind propagation");
    await page.evaluate((id) => { const FG = window.FairGuide; FG.get(id).implementationSeams = window.modelSavedRefs; FG.invalidateData(); FG.render(); }, unrelated["@id"]);
    await expectedQuestions(["#seam-repository-nma"]);
    await visit(`#/${lang}/K/catalogue/model/seam/repository-nma`, ".entry-card");
    assert.equal(await page.locator(".entry-card").count(), 1, "a direct definition link clears unrelated filters");
    assert.equal(await page.locator('.model-tag[href$="/model/layer/infrastructure"]').count(), 1, "within-layer transfer is represented explicitly");
    await visit(`#/${lang}/K/catalogue/res/pub/layers-seams-manuscript`, ".entry-card");
    assert((await page.locator(".entry-card .card-details").textContent()).includes(lang === "cs" ? "v přípravě" : "in preparation"), "the unpublished conceptual source is labelled in its own record");
    await visit(`#/${lang}/K/page/model`, "#model-seam");
    assert.equal(await page.locator(".model-layers > li").count(), 6);
    assert.equal(await page.locator("#model-seam option").count(), 12);
    await page.locator(".implementation-model .model-diagram img").scrollIntoViewIfNeeded();
    await page.waitForFunction(() => { const image = document.querySelector(".model-diagram img"); return image?.complete && image.naturalWidth > 0; });
    assert.equal(await page.locator(".model-diagram").count(), 3, "the guide reuses all three approved manuscript figures");
    for (const section of ["national-mapping", "metadata-architecture"]) {
      await page.locator(`#${section} summary`).click();
      const figure = page.locator(`#${section} .model-diagram`);
      await figure.locator("img").scrollIntoViewIfNeeded();
      await figure.locator("img").evaluate((image) => image.decode());
      assert.equal(await figure.locator('a[target="_blank"]').count(), 1, "detailed figures can be opened at full size");
      assert((await page.locator(`#${section}`).textContent()).includes("2026"), "national diagrams retain the mapping date");
    }
    await page.locator("#model-seam").selectOption("repository-catalogue-planning");
    await page.locator(".model-examples summary").click();
    assert.equal(await page.locator(".model-example").count(), 2, "catalogue publication and reuse in planning retain distinct scopes");
    assert.equal(await page.locator('.model-example [data-status="pilot"]').count(), 1);
    assert.equal(await page.locator('.model-example [data-status="planned"]').count(), 1);
    assert((await page.locator(".model-examples").textContent()).includes("2026-09"), "month precision from the manuscript is preserved");
    assert((await page.locator(".model-examples").textContent()).includes(lang === "cs" ? "stav v mapování" : "mapping status"), "reported mapping status is not presented as a live check");
    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await accessible();
      await page.screenshot({ path: resolve(screenshots, `${lang}-overview-${width}.png`), fullPage: true });
      await page.locator("#model-connection").scrollIntoViewIfNeeded();
      await page.screenshot({ path: resolve(screenshots, `${lang}-connection-${width}.png`) });
    }
    await page.setViewportSize({ width: 1280, height: 900 });
    for (const lens of ["V", "DS", "SR", "K"]) {
      await visit(`#/${lang}/${lens}/path/metadata`, 'details[data-key="L2"]');
      await page.locator('details[data-key="L2"]').evaluate((element) => { element.open = true; });
      const expected = graph.filter((entry) => String(entry["@id"]).startsWith("#model-context-") && refs(entry, "isPartOf").includes("#station-metadata") && refs(entry, "audience").includes("#lens-" + lens));
      assert.equal(await page.locator(".model-context").count(), expected.length);
      for (const entry of expected) assert((await page.locator(".model-context").textContent()).includes(entry.text.find((value) => value["@language"] === lang)["@value"]), "Proč uses the specific role context");
      const markdown = await download("#export-markdown");
      for (const entry of expected) assert(markdown.includes(entry.text.find((value) => value["@language"] === lang)["@value"]), "station Markdown retains the role explanation");
    }
    await visit(`#/${lang}/K/page/machines`, ".model-worked-example");
    const example = page.locator(".model-worked-example");
    assert.equal(await example.locator("ol > li").count(), 4, "the worked example follows the actual four-record chain");
    for (const family of ["cl", "q", "test", "act"]) assert.equal(await example.locator(`ol a[href*="/catalogue/${family}/"]`).count(), 1, "each example step opens the correct record family");
    /* The check's parts: the questions are answered on one, the hand-overs and exports are in the report, and a
       saved result is loaded among the evidence. */
    const checkPart = (name, selector) => visit(`#/${lang}/SR/check/maturity/${name}`, selector);
    await checkPart("answers", "#item-maturity-01");
    await page.locator('label[for="extended-toggle"]').click();
    await page.waitForSelector("#item-maturity-09");
    assert(await page.locator("#item-maturity-09 .model-tag").count() > 0, "question detail shows its connections");
    await page.locator("#answer-maturity-09-unknown").check();
    await checkPart("report", ".result-handover");
    await page.locator(".result-handover summary").first().click();
    assert((await page.locator(".result-handover").first().textContent()).includes(lang === "cs" ? "není uložen" : "No automatically"), "manual uncertainty does not fabricate evidence");
    const result = await page.evaluate(() => { const FG = window.FairGuide; return FG.selfcheck.ftrCrate(FG.get("#check-maturity"), FG.state.answers.maturity); });
    const member = result["@graph"].find((entry) => entry["@id"] === "#result-maturity.09");
    assert(member.implementationSeams.some((reference) => reference["@id"].endsWith("#seam-community-repository")), "JSON-LD results retain the source question's mappings");
    assert.equal(member["prov:value"], "indeterminate", "an unanswered connection is not declared broken");
    await page.locator("#export-format-jsonld").check();
    const exported = await download("#export-download");
    await checkPart("evidence", "#load-file");
    await page.locator("#load-file").setInputFiles({ name: "model-result.jsonld", mimeType: "application/ld+json", buffer: Buffer.from(exported) });
    await page.waitForSelector(".notice.shared");
    assert(await page.locator(".result-handover .model-tag").count() > 0, "a saved result preview restores connections from the current question records");
    await page.locator(".notice.shared button.button-primary").click();
    await page.waitForSelector("#item-maturity-09");
    assert(await page.locator("#answer-maturity-09-unknown").isChecked(), "loading a mapped result retains its answer");
    assert(await page.locator("#item-maturity-09 .model-tag").count() > 0);
    const old = await page.evaluate(() => { const FG = window.FairGuide; const data = FG.selfcheck.portableState(FG.get("#check-maturity"), FG.state.answers.maturity); data.v = 1;
      for (const item of Object.values(data.items)) delete item.observations;
      return FG.selfcheck.readPortable(data); });
    assert(!old.error && old.state.items["maturity.09"].value === "unknown", "older saved states need no new model fields");
    await page.evaluate(() => { const FG = window.FairGuide; const st = FG.state.answers.maturity; st.target = "10.1234/example"; st.targetInfo = { name: "Named record" }; FG.saveState(); });
    await checkPart("report", ".result-handover");
    assert.equal(await page.locator('.result-handover:first-of-type a.pid-chip[href="https://doi.org/10.1234/example"]').count(), 1, "a bare DOI gets its resolver link, as an identifier chip, in the hand-over");
    assert((await page.locator(".result-handover").first().textContent()).includes("Named record"), "retained target description is shown");
    const questionText = get("#item-maturity.09").text.find((value) => value["@language"] === lang)["@value"];
    assert((await page.locator(".result-handover").first().textContent()).includes(questionText), "the hand-over retains the full criterion");
    for (const width of [1280, 390, 320]) {
      const previous = await page.$("#main");
      const wasWide = await page.evaluate(() => matchMedia("(min-width: 60rem)").matches);
      await page.setViewportSize({ width, height: 900 });
      const isWide = await page.evaluate(() => matchMedia("(min-width: 60rem)").matches);
      if (wasWide !== isWide) await page.waitForFunction((node) => !node.isConnected, previous);
      await checkPart("answers", "#item-maturity-09");
      await page.locator("#item-maturity-09").scrollIntoViewIfNeeded();
      await accessible();
      await page.screenshot({ path: resolve(screenshots, `${lang}-question-${width}.png`) });
      await checkPart("report", ".result-handover");
      await page.locator(".result-handover").first().evaluate((element) => { element.open = true; });
      await page.locator(".result-handover").first().scrollIntoViewIfNeeded();
      await page.screenshot({ path: resolve(screenshots, `${lang}-handover-${width}.png`) });
    }
    await page.setViewportSize({ width: 1280, height: 900 });
    await visit(`#/${lang}/K/check/fip`, "#prefill-fip");
    await page.evaluate(() => { window.FairGuide.live.available = () => false; });
    await page.locator("#prefill-fip").selectOption("ndi-baseline");
    await page.locator("#prefill-fip-run").click();
    await page.waitForFunction(() => window.FairGuide.state.answers.fip?.items?.["fip.02"]?.value);
    await visit(`#/${lang}/K/check/fip/answers`, "#answer-fip-02-partly");
    assert(await page.locator("#answer-fip-02-partly").isChecked(), "selecting an F2 resource does not establish all profile attributes");
    assert.equal(get("#item-fip.02").prefillLevel, "partly");
    await page.locator("#answer-fip-02-yes").check();
    assert(await page.locator("#answer-fip-02-yes").isChecked(), "the informed user can supply complete evidence");
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(external, [], "model navigation and local exports send nothing outside the browser");
  console.log("check_model: model records, scoped mappings, persistent facets, bilingual role contexts, exports, handovers and accessible diagrams pass");
} finally {
  await browser.close();
}
