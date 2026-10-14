// Optional evaluators and shared answer ownership: FAIR-Checker's twelve metrics run from the browser against an
// inert fixture service, local F-UJI reports (historical 3.5.0 and current 4.0.1 fixtures), reviewed mappings,
// late results, retries, removal, exports and the probe scenarios of the evidence hierarchy, in both languages, at
// full and phone width, with the keyboard and in print.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const { chromium } = await import("playwright");
const fixture = (name) => readFileSync(resolve(root, "tests/fixtures/providers", name), "utf8");
const fuji350 = fixture("fuji-3.5.0.json");
const fuji401 = fixture("fuji-4.0.1.json");
const fairChecker = JSON.parse(fixture("fair-checker.json"));
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
const page = await context.newPage();
const base = pathToFileURL(resolve(root, "_site/index.html")).href;
const problems = [];
const external = [];
let axeRunning = false;
page.on("pageerror", (error) => problems.push(error.message));
page.on("console", (message) => { if (message.type() === "error" && !axeRunning) problems.push(message.text()); });
page.on("request", (request) => { if (!/^(?:file|data|blob):/.test(request.url()) && !axeRunning) external.push(request.url()); });
page.on("dialog", (dialog) => dialog.accept());
const screenshots = resolve(root, ".cache/screenshots/providers");
mkdirSync(screenshots, { recursive: true });
const TARGET = "https://doi.org/10.1234/example";

async function open(lang, id = "dataset", lens = "V") {
  /* A hash change keeps the previous view until the new one is drawn; wait for it to be replaced. */
  const previous = await page.$("#main");
  const hash = `#/${lang}/${lens}/check/${id}`;
  const changed = !page.url().endsWith(hash);
  await page.goto(base + hash);
  if (previous && changed) await page.waitForFunction((node) => !node.isConnected, previous).catch(() => {});
  if (!changed) await page.evaluate(() => window.FairGuide.rerender());
  await page.waitForSelector(id === "dataset" ? "#mode-after" : `#item-${id}-01`);
  if (id === "dataset") {
    await page.locator("#mode-after").check();
    await page.waitForFunction(() => (window.FairGuide.state.answers.dataset || {}).mode === "after");
  }
  await page.waitForSelector("#prefill-pid");
}
/** Go to one part of the open check (evidence, answers or report) and wait until it is drawn. */
async function part(name) {
  const [prefix] = page.url().match(/#\/[a-z]{2}\/[A-Z]+\/check\/[a-z-]+/) || [];
  const hash = prefix + "/" + name;
  if (!page.url().endsWith(hash)) {
    const previous = await page.$("#main");
    await page.evaluate((target) => { window.location.hash = target; }, hash);
    if (previous) await page.waitForFunction((node) => !node.isConnected, previous).catch(() => {});
  }
  await page.waitForSelector(`.check-parts [aria-current="step"][href$="/${name}"]`);
}
async function checkAccess(label) {
  axeRunning = true;
  const result = await audit(page);
  axeRunning = false;
  assert.deepEqual(result.violations.map((entry) => entry.id), [], label + ": accessibility");
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), label + ": no horizontal overflow");
}
const reset = () => page.evaluate(() => { const FG = window.FairGuide; FG.clearStoredData(); FG.saveState(); });
const setTarget = (target = TARGET) => page.evaluate((value) => {
  const FG = window.FairGuide, st = FG.state.answers.dataset;
  st.pid = FG.live.parsePid(value).value; st.target = value; st.extended = true; FG.saveState(); FG.rerender();
}, target);
const item = (id) => page.evaluate((key) => window.FairGuide.state.answers.dataset.items[key] || null, id);
async function mockService(failing = []) {
  await page.evaluate(([service, failed]) => {
    const FG = window.FairGuide;
    window.providerCalls = [];
    window.providerFail = failed;
    FG.live.fetchText = async (connector, path) => {
      window.providerCalls.push(connector + " " + path);
      if (window.providerGate) await window.providerGate;
      if (path === "swagger.json") return { text: JSON.stringify(service.swagger) };
      const metric = decodeURIComponent(path.match(/metric_([^?]+)/)[1]);
      if (window.providerFail.includes(metric)) throw Object.assign(new Error("FAIR-Checker REST API: HTTP 502"), { code: "http-error" });
      return { text: JSON.stringify(service.responses[metric]) };
    };
  }, [fairChecker, failing]);
}
async function load(text, name = "report.json") {
  await page.locator("#provider-import-fuji").setInputFiles({ name, mimeType: "application/json", buffer: Buffer.from(text) });
  await page.waitForSelector(".import-preview");
}
const statusText = () => page.locator("#prefill-status").textContent();

try {
  /* ------------------------------------------------ the shared record, read locally */
  await open("en");
  const read = await page.evaluate(async ([older, current]) => {
    const P = window.FairGuide.providers;
    const a = await P.readFuji(older, { name: "older.json" });
    const b = await P.readFuji(current, { name: "current.json" });
    const unknown = JSON.parse(older); unknown.metric_specification = "https://doi.org/10.5281/zenodo.9999999";
    const c = await P.readFuji(JSON.stringify(unknown), { name: "unknown.json" });
    const metric = (read, id) => read.assessment.results.find((result) => result.id === id);
    const broken = JSON.parse(older); broken.results[3].metric_identifier = "not a metric";
    const errors = {
      tooLarge: (await P.readFuji(" ".repeat(P.settings().maxImportBytes + 1))).error,
      notJson: (await P.readFuji("{ not json")).error,
      foreign: (await P.readFuji(JSON.stringify({ name: "something else" }))).error,
      guideResult: (await P.readFuji(JSON.stringify({ format: "eosc-fair-guide-result", v: 2 }))).error,
      broken: (await P.readFuji(JSON.stringify(broken))).error,
    };
    const service = P.provider("fair-checker");
    let refused = null;
    try { P.readFairChecker("A11", JSON.stringify({ score: "7" }), service); } catch (error) { refused = error.code; }
    return {
      reviewed: [a.assessment.reviewed, b.assessment.reviewed, c.assessment.reviewed],
      versions: [P.versionText(a.assessment), P.versionText(b.assessment)],
      counts: [a.assessment.results.length, b.assessment.results.length],
      ids: [a.assessment.id, b.assessment.id].map((id) => id.slice(0, 13)),
      persistent: metric(a, "FsF-F1-02MD"), vocabularies: metric(a, "FsF-I2-01M"),
      readings: {
        persistent: P.reading(metric(a, "FsF-F1-02MD"), P.provider("f-uji")),
        initial: P.reading({ id: "x", verdict: "pass", maturity: 1 }, P.provider("f-uji")),
        none: P.reading(metric(b, "FsF-F3-01M"), P.provider("f-uji")),
        checker: [2, 1, 0].map((value) => P.reading({ id: "x", score: { value, max: 2 } }, service)),
        differs: P.statusDiffers(metric(a, "FsF-F1-02MD")),
        outcome: P.outcome(metric(a, "FsF-F1-02MD"), P.provider("f-uji")),
      },
      harvest: a.assessment.harvest, sameTarget: P.sameTarget("https://doi.org/10.1234/EXAMPLE", "doi:10.1234/example"),
      errors, refused,
      echo: P.readFairChecker("F2A", JSON.stringify({ metric: "F1A", score: "1" }), service),
      mappings: { service: P.mappings(service).map((row) => row.coverage), fuji: P.mappings(P.provider("f-uji")).filter((row) => row.coverage === "whole").map((row) => row.metric + " " + row.question) },
    };
  }, [fuji350, fuji401]);
  assert.deepEqual(read.reviewed, [true, true, false], "both reviewed specifications map; an unknown specification never borrows a mapping");
  assert(read.versions[0].includes("3.5.0") && read.versions[0].includes("metrics_v0.8") && read.versions[1].includes("4.0.1") && read.versions[1].includes("0.8"));
  assert.deepEqual(read.counts, [17, 17]);
  assert.deepEqual(read.ids, ["f-uji:sha256-", "f-uji:sha256-"]);
  // F-UJI's own client shows a metric as passed at its level from level 1, whatever the report's test status; the
  // status stays recorded as native and is shown where it differs. Subtests show passed or unknown by their status.
  assert.equal(read.persistent.native, "fail"); assert.equal(read.persistent.verdict, "pass", "F-UJI shows level 3 as passed");
  assert.deepEqual(read.persistent.score, { earned: 1, total: 1 }); assert.equal(read.persistent.maturity, 3);
  assert.equal(read.persistent.subtests.length, 4);
  assert.equal(read.persistent.subtests.filter((test) => test.native === "fail" && test.verdict === "indeterminate" && test.score.total === 0).length, 2, "unscored failing subtests show F-UJI's unknown");
  assert.equal(read.vocabularies.native, "fail"); assert.equal(read.vocabularies.verdict, "pass");
  assert.deepEqual(read.readings, {
    persistent: "met", initial: "partly", none: "open", checker: ["met", "partly", "failed"], differs: true,
    outcome: "FAIR level 3 of 3 (advanced) · the service's 1 of 1 points",
  }, "results read as each provider presents them");
  assert.equal(read.harvest[0].licence.length, 2, "licence statements stay with the source that gave them");
  assert.equal(read.sameTarget, true);
  assert.deepEqual(read.errors, { tooLarge: "tooLarge", notJson: "notJson", foreign: "foreign", guideResult: "guideResult", broken: "broken" });
  assert.equal(read.refused, "unexpected-response");
  assert.equal(read.echo.echoed, "F1A", "a response naming another metric keeps the requested identity and records the difference");
  assert(read.mappings.service.every((coverage) => coverage === "partial"), "FAIR-Checker metrics only add evidence");
  assert.deepEqual(read.mappings.fuji.sort(), ["FsF-A1-01M dataset.10", "FsF-F1-02MD dataset.01"]);
  // FAIR-Checker scoring 0 everywhere usually read no metadata at all, so it decides nothing; one 0 among other
  // scores is that metric's No. Numbers are written as the page's language writes them.
  const guard = await page.evaluate(() => {
    const P = window.FairGuide.providers, FG = window.FairGuide;
    const item = FG.get("#item-dataset.01");
    const rows = [{ metric: "F1A", coverage: "partial" }];
    const service = P.provider("fair-checker");
    const assessment = (scores) => ({ provider: "fair-checker", reviewed: true, target: "https://doi.org/10.1234/example",
      results: Object.entries(scores).map(([id, score]) => P.readFairChecker(id, JSON.stringify({ metric: id, score }), service)) });
    const blank = P.evidence(item, rows, assessment({ F1A: 0, F1B: 0, A11: 0 }));
    const one = P.evidence(item, rows, assessment({ F1A: 0, F1B: 2, A11: 1 }));
    const lang = FG.state.lang;
    FG.state.lang = "cs";
    const czech = FG.formatNumber(0.5); // P.outcome writes every number through it
    FG.state.lang = lang;
    return { blank: [blank.value, blank.notes.map((note) => note.key)], one: one.value, czech };
  });
  assert.equal(guard.blank[0], null, "a FAIR-Checker assessment that scored 0 everywhere suggests nothing");
  assert(guard.blank[1].includes("selfcheck.note.providerBlank"), "and it says why");
  assert.equal(guard.one, "no", "one metric's 0 among other scores still suggests No through a partial mapping");
  assert(guard.czech.includes("0,5"), "Czech pages write the points with a decimal comma: " + guard.czech);

  for (const lang of ["cs", "en"]) {
    await reset();
    await open(lang);
    /* ------------------------------------------------ explicit choices; nothing runs on entry */
    await mockService();
    assert.equal(await page.locator(".evaluators").count(), 1);
    assert(await page.locator("#provider-run-fair-checker").isDisabled(), "no identifier, no run");
    assert.equal(await page.locator('.evaluators a[href="https://www.f-uji.net/?action=test"]').count(), 1, "F-UJI is a public form link without a prefilled identifier");
    assert.equal(await page.locator('.evaluators a[href="https://fair-checker.france-bioinformatique.fr/check"]').count(), 1);
    await setTarget();
    await page.waitForSelector("#evaluator-target");
    assert.equal(await page.locator("#evaluator-target").textContent(), TARGET, "the identifier sent is shown before any choice");
    assert((await page.locator("#evaluator-fair-checker").textContent()).includes("fair-checker.france-bioinformatique.fr"), "the service and its host are named");
    for (const id of ["fair-checker", "f-uji"]) assert.equal(await page.locator(`#evaluator-${id} .evaluator-name > .service-badge[data-service="${id}"] + span strong`).count(), 1, "each evaluator's name follows its service badge");
    assert.deepEqual(await page.evaluate(() => window.providerCalls), [], "entering, typing and preview send nothing");
    await page.locator(".evaluators .flow-details > summary").click();
    assert.equal(await page.locator('.evaluators .flow[data-flow="evidence"] .flow-step').count(), 5);
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await checkAccess(`${lang} choices ${width}`);
      await page.locator(".evaluators").screenshot({ path: resolve(screenshots, `${lang}-choices-${width}.png`) });
    }
    await page.setViewportSize({ width: 1280, height: 900 });

    /* ------------------------------------------------ manual answers survive every provider event */
    await part("answers");
    await page.locator("#answer-dataset-10-no").check();
    await page.locator("#answer-dataset-04-no").check();
    await part("evidence");

    /* ------------------------------------------------ a late result never attaches to another target */
    await page.evaluate(() => { window.providerGate = new Promise((resolve) => { window.releaseGate = resolve; }); });
    await page.locator("#provider-run-fair-checker").click();
    await page.waitForFunction(() => window.providerCalls.length > 0);
    assert(await page.locator("#provider-run-fair-checker").isDisabled(), "a running assessment cannot be started twice");
    assert.equal(await page.locator("#provider-progress").count(), 1, "a running assessment shows its progress");
    await page.evaluate(() => { window.FairGuide.live.discoverObject = async (input) => ({ input, supported: false, date: "2026-10-12T00:00:00Z", diagnostics: [], coverage: {}, representations: [] }); });
    await page.fill("#prefill-pid", "10.1234/other");
    await page.click("#prefill-pid-run");
    await page.waitForFunction(() => window.FairGuide.state.answers.dataset.target.endsWith("/other"));
    await page.evaluate(() => { window.providerGate = null; window.releaseGate(); });
    await page.waitForTimeout(1000);
    assert.equal(await page.evaluate(() => (window.FairGuide.state.answers.dataset.assessments || []).length), 0, "late results for an earlier target are discarded");
    assert.deepEqual(await page.evaluate(() => window.providerCalls), ["fair-checker swagger.json"], "a run left behind by another target sends no metric request");
    assert.equal((await item("dataset.10")).value, "no");

    /* ------------------------------------------------ twelve metrics, unavailable ones retried alone */
    await setTarget();
    await mockService(["I2", "R13", "A11"]);
    await page.locator("#provider-run-fair-checker").click();
    await page.waitForSelector("#provider-attached-fair-checker");
    await part("report");
    await page.waitForSelector("#provider-overview-0");
    assert.equal(await page.locator('#assessment-title-0 > .service-badge[data-service="fair-checker"]').count(), 1, "the assessment names its evaluator beside its badge");
    const run = await page.evaluate(() => {
      const assessment = window.FairGuide.state.answers.dataset.assessments[0];
      return { results: assessment.results.length, errors: assessment.results.filter((result) => result.error).map((result) => result.id).sort(), api: assessment.versions.api, reviewed: assessment.reviewed, calls: window.providerCalls.length };
    });
    assert.deepEqual(run, { results: 12, errors: ["A11", "I2", "R13"], api: "1.0", reviewed: true, calls: 13 });
    assert.equal(await page.locator("#provider-overview-0 .criterion").count(), 12, "every native metric is listed, results or not");
    assert((await page.locator('#provider-overview-0 .criterion[data-verdict="none"]').count()) === 3);
    assert((await page.locator("#provider-overview-0").textContent()).includes(lang === "cs" ? "Bez mapování" : "Not mapped"), "unmapped metrics stay inspectable");
    assert.equal((await item("dataset.10")).value, "no", "a provider result never replaces the reader's answer");
    await part("answers");
    assert.equal(await page.locator("#origin-dataset-10 .source-chip[data-origin]").getAttribute("data-origin"), "confirmed", "the reader's No stays theirs, and FAIR-Checker's 0 confirms it");
    await part("report");
    // FAIR-Checker's scores read as it colours them; every mapping is partial, so 2 and 1 suggest Partly and 0 No.
    assert.deepEqual(await page.evaluate(() => Object.fromEntries(Object.entries(window.FairGuide.state.answers.dataset.items).filter(([, entry]) => entry.origin === "prefill").map(([key, entry]) => [key, entry.value]))),
      { "dataset.01": "partly", "dataset.08": "partly", "dataset.09": "no" }, "partial mappings suggest Partly when met and No when not; the reader's answers stay");
    assert(await page.evaluate(() => window.FairGuide.state.answers.dataset.items["dataset.04"].observations.some((seen) => seen.source === "fair-checker" && seen.value === "partly")), "a partial suggestion stays beside the reader's answer");
    await page.evaluate(() => { window.providerCalls = []; window.providerFail = []; });
    await page.locator("#provider-retry-0").click();
    await page.waitForFunction(() => window.FairGuide.state.answers.dataset.assessments[0].results.every((result) => !result.error));
    assert.deepEqual(await page.evaluate(() => window.providerCalls.map((call) => call.split(" ")[1].match(/metric_(\w+)/)[1]).sort()), ["A11", "I2", "R13"], "the retry asks only for the unresolved metrics");
    assert.equal(await page.evaluate(() => window.FairGuide.state.answers.dataset.assessments.length), 1, "a retry completes the same assessment");
    await page.locator("#provider-overview-0 .criterion").first().locator(".evidence-details > summary").click();
    assert.equal(await page.locator("#provider-overview-0 .provider-text b").count(), 0, "provider text stays inert");

    /* ------------------------------------------------ F-UJI: preview, attach, mappings, ownership */
    await part("evidence");
    await load(fuji350, "fuji-3.5.0.json");
    const preview = await page.locator(".import-preview").textContent();
    for (const expected of ["10.1234/example", "3.5.0", "metrics_v0.8", "zenodo.6461229", "f0c1a2b3c4d5e6f7", "17"]) assert(preview.includes(expected), "the preview shows " + expected);
    assert.equal(await page.evaluate(() => (window.FairGuide.state.answers.dataset.assessments || []).length), 1, "a preview attaches nothing");
    await checkAccess(`${lang} preview`);
    await page.locator("#provider-import-attach").click();
    await page.waitForSelector("#provider-attached-f-uji");
    await part("report");
    await page.waitForSelector("#provider-overview-1");
    const persistent = await item("dataset.01");
    assert.equal(persistent.value, "yes", "a metric F-UJI shows as passed at level 3 suggests Yes through a whole mapping, whatever its test status");
    assert(persistent.observations.some((seen) => seen.source === "f-uji" && seen.value === "yes" && !seen.notes.some((note) => note.key === "selfcheck.note.providerFail")));
    assert.equal(persistent.prefill.source, "f-uji", "evidence about the whole question outranks FAIR-Checker's earlier partial suggestion");
    /* A saved assessment follows the current reading on the next visit: an observation stored under an earlier
       reading is replaced once, and only that assessment's own. */
    await page.evaluate(() => {
      const entry = window.FairGuide.state.answers.dataset.items["dataset.01"];
      entry.observations.find((seen) => seen.source === "f-uji").value = "no";
      entry.prefill.value = "no"; entry.value = "no";
      window.FairGuide.saveState();
    });
    await page.reload();
    await page.waitForSelector("#main h1");
    await part("report");
    await page.waitForSelector("#provider-overview-1");
    const reread = await item("dataset.01");
    assert.equal(reread.observations.find((seen) => seen.source === "f-uji").value, "yes", "a saved assessment is read again under the current reading on the next visit");
    assert.equal(reread.value, "yes", "and its suggestion follows");
    assert((await page.locator("#provider-overview-1").textContent()).includes(lang === "cs" ? "test_status" : "test_status"), "the report's own status is shown where it differs");
    assert.equal((await item("dataset.10")).value, "no", "a whole-mapping pass leaves the reader's No unchanged");
    assert.equal((await item("dataset.10")).origin, "user");
    const licence = await item("dataset.04");
    assert.equal(licence.value, "no"); assert(licence.observations.filter((seen) => ["fair-checker", "f-uji"].includes(seen.source)).every((seen) => seen.value === "partly"), "partial coverage suggests Partly beside the reader's No");
    assert((await page.locator("#provider-overview-1").textContent()).includes(lang === "cs" ? "Průvodce tyto stránky sám nečetl" : "the Guide did not read these pages itself"), "harvested evidence is attributed to F-UJI");
    /* Without the reader's answer, a reattached report (after removing the old copy) suggests Yes. */
    await page.evaluate(() => { const st = window.FairGuide.state.answers.dataset; delete st.items["dataset.10"]; window.FairGuide.saveState(); window.FairGuide.rerender(); });
    await page.locator("#provider-remove-1").click();
    await page.waitForFunction(() => window.FairGuide.state.answers.dataset.assessments.length === 1);
    await part("evidence");
    await load(fuji350, "fuji-3.5.0.json");
    await page.locator("#provider-import-attach").click();
    await page.waitForFunction(() => window.FairGuide.state.answers.dataset.assessments.length === 2);
    assert.equal((await item("dataset.10")).value, "yes", "a reviewed whole mapping at F-UJI's top level suggests Yes");
    assert.equal((await item("dataset.10")).origin, "prefill");

    /* duplicate, historical, mismatched and unknown-version reports */
    await load(fuji350, "again.json");
    assert(await page.locator("#provider-import-attach").isDisabled(), "a duplicate report is not attached twice");
    await page.locator("#provider-import-discard").click();
    const other = JSON.parse(fuji350); other.request.object_identifier = "https://doi.org/10.1234/elsewhere";
    await load(JSON.stringify(other), "elsewhere.json");
    assert(await page.locator("#provider-import-attach").isDisabled(), "a report about another object is not attached");
    assert((await page.locator(".import-preview").textContent()).includes("10.1234/elsewhere"));
    await page.locator("#provider-import-discard").click();
    const unknown = JSON.parse(fuji401); unknown.metric_specification = "https://doi.org/10.5281/zenodo.9999999"; unknown.software_version = "9.0.0";
    unknown.results[4].maturity = 0;
    const unknownLevel = unknown.results.filter((result) => result.maturity === 0).length;
    await load(JSON.stringify(unknown), "unknown.json");
    assert((await page.locator(".import-preview").textContent()).includes("9.0.0"));
    await page.locator("#provider-import-attach").click();
    await page.waitForFunction(() => window.FairGuide.state.answers.dataset.assessments.length === 3);
    await part("report");
    await page.waitForSelector("#provider-overview-2");
    assert.equal(await page.locator('#provider-overview-2 .badge[data-reviewed="false"]').count(), 1);
    assert.equal(await page.locator("#provider-overview-2 .criterion").count(), 17, "an unmapped version keeps its complete native results");
    assert.equal(await page.locator('#provider-overview-2 .criterion[data-verdict="indeterminate"]').count(), unknownLevel, "a metric at level 0 shows F-UJI's unknown, not a failure");
    assert.equal(await page.locator('#provider-overview-2 .criterion[data-verdict="fail"]').count(), 0, "F-UJI shows no metric as failed");
    assert.equal((await item("dataset.10")).value, "yes", "an unknown version changes no answer");

    /* removal withdraws only what the assessment contributed */
    await page.locator("#provider-remove-1").click();
    await page.waitForFunction(() => window.FairGuide.state.answers.dataset.assessments.length === 2);
    const afterRemoval = await item("dataset.10");
    assert(!afterRemoval || afterRemoval.value !== "yes", "a suggestion that rested on the removed report goes");
    assert.equal((await item("dataset.04")).value, "no", "the reader's answers stay");

    /* ------------------------------------------------ exports and the lossless evidence */
    await part("evidence");
    await load(fuji350, "fuji-3.5.0.json");
    await page.locator("#provider-import-attach").click();
    await page.waitForFunction(() => window.FairGuide.state.answers.dataset.assessments.length === 3);
    await part("report");
    await page.waitForSelector("#provider-overview-2");
    const saved = await page.evaluate(() => {
      const FG = window.FairGuide, SC = FG.selfcheck, check = FG.get("#check-dataset"), st = FG.state.answers.dataset;
      const portable = SC.portableState(check, st);
      return { v: portable.v, assessments: portable.assessments.length, logs: portable.assessments.some((entry) => entry.results.some((result) => result.log)),
        restored: SC.readPortable(portable).state.assessments.length, members: SC.ftrCrate(check, st)["@graph"].filter((entity) => String(entity["@id"]).startsWith("#provider-") && [].concat(entity["@type"]).includes("TestResult")).length };
    });
    assert.deepEqual(saved, { v: 3, assessments: 3, logs: false, restored: 3, members: 12 + 17 + 17 });
    await page.locator("#export-format-md").check();
    await page.locator(".export-preview summary").click();
    await page.waitForFunction(() => document.getElementById("export-preview-text").value.length > 0);
    const markdown = await page.locator("#export-preview-text").inputValue();
    assert(markdown.includes("FsF-F1-02MD") && markdown.includes("R13") && markdown.includes("fair-guide-result v3"));
    await page.locator(".export-preview summary").click();
    const [evidence] = await Promise.all([page.waitForEvent("download"), page.locator("#export-evidence").click()]);
    const complete = readFileSync(await evidence.path(), "utf8");
    const holder = JSON.parse(complete)["@graph"].find((entity) => entity.guideSources);
    assert(Object.values(JSON.parse(holder.guideSources)).includes(fuji350), "the complete evidence keeps the original report byte for byte");
    const [original] = await Promise.all([page.waitForEvent("download"), page.locator("#provider-download-2").click()]);
    assert.equal(readFileSync(await original.path(), "utf8"), fuji350, "the original report downloads unchanged");
    /* The complete evidence loads back, with its original report, in a browser that never saw it. */
    await page.evaluate(() => { window.FairGuide.clearStoredData(); window.FairGuide.saveState(); });
    await page.goto(base + `#/${lang}/V/selfcheck`);
    await page.waitForSelector("#load-file-overview");
    await page.locator("#load-file-overview").setInputFiles({ name: "evidence.jsonld", mimeType: "application/ld+json", buffer: Buffer.from(complete) });
    await page.waitForSelector(".notice.shared");
    assert.equal(await page.locator("#provider-overview-2").count(), 1, "the preview shows the loaded assessments");
    assert.equal(await page.locator("[id^='provider-remove'], [id^='provider-retry']").count(), 0, "a preview offers no control over the reader's own answers");
    await page.locator(".notice.shared .button-primary").click();
    await page.waitForSelector(`.check-parts [aria-current="step"][href$="/answers"]`);
    await part("report");
    await page.waitForSelector("#provider-overview-2");
    assert.equal(await page.evaluate((text) => Object.values(window.localStorage).includes(text), fuji350), true, "the restored report is kept in this browser");

    /* ------------------------------------------------ phone, print and keyboard */
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      /* Crossing the wide-layout width draws the view again. */
      await page.waitForTimeout(100);
      await page.waitForSelector("#results-assessments");
      await page.evaluate(() => document.getElementById("results-assessments").scrollIntoView());
      await checkAccess(`${lang} overview ${width}`);
      await page.screenshot({ path: resolve(screenshots, `${lang}-overview-${width}.png`), fullPage: true });
      await page.locator("#provider-overview-2").screenshot({ path: resolve(screenshots, `${lang}-assessment-${width}.png`) });
      await part("answers");
      await page.locator("#item-dataset-10").screenshot({ path: resolve(screenshots, `${lang}-question-${width}.png`) });
      await part("report");
    }
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.emulateMedia({ media: "print" });
    assert(await page.locator("#provider-overview-2").isVisible(), "the overview prints");
    assert(await page.locator("#provider-overview-2 .criterion-questions button").first().isVisible(), "question references print");
    await page.emulateMedia({ media: "screen" });
    await page.locator("#provider-download-0").focus();
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate(() => document.activeElement.id), "provider-remove-0", "the overview's controls follow in keyboard order");
  }

  /* ------------------------------------------------ untrusted files, storage limits and stale previews */
  await reset();
  await open("cs");
  await setTarget();
  /* Logs stay in the retained report, not in the saved answers; the overview still reads them. */
  await load(fuji350, "fuji-3.5.0.json");
  await page.locator("#provider-import-attach").click();
  await page.waitForSelector("#provider-attached-f-uji");
  await part("report");
  await page.waitForSelector("#provider-overview-0");
  assert.equal(await page.evaluate(() => JSON.stringify(window.FairGuide.state.answers.dataset.assessments).includes("test_debug") || window.FairGuide.state.answers.dataset.assessments[0].results.some((result) => result.log)), false, "native logs are not copied into the saved answers");
  await page.locator("#provider-overview-0 .criterion").nth(1).locator(".evidence-details > summary").click();
  assert((await page.locator("#provider-overview-0 .criterion").nth(1).textContent()).includes("Found persistence identifier scheme"), "the native log is read from the retained report");
  /* A full browser storage gives way to the answers: reports are dropped from storage and kept for the visit. */
  const quota = await page.evaluate(() => {
    const FG = window.FairGuide, original = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key, value) {
      if (key === "eosc-fair-guide" && Object.keys(window.localStorage).some((name) => name.startsWith("eosc-fair-guide:source:"))) throw new DOMException("full", "QuotaExceededError");
      return original.call(this, key, value);
    };
    FG.state.answers.dataset.items["dataset.05"] = { value: "yes", origin: "user" };
    const saved = FG.saveState();
    const sources = Object.keys(window.localStorage).filter((name) => name.startsWith("eosc-fair-guide:source:")).length;
    Storage.prototype.setItem = function () { throw new DOMException("full", "QuotaExceededError"); };
    const refused = FG.saveState();
    const full = FG.storageFull;
    FG.rerender();
    const shown = Boolean(document.getElementById("local-data-full"));
    Storage.prototype.setItem = original;
    return { saved, sources, refused, answers: JSON.parse(window.localStorage.getItem("eosc-fair-guide")).answers.dataset.items["dataset.05"].value, full, shown };
  });
  assert.deepEqual(quota, { saved: true, sources: 0, refused: false, answers: "yes", full: true, shown: true }, "answers are saved before retained reports, and a refusal is shown");
  assert((await page.locator("#provider-overview-0").textContent()).includes("do zavření stránky"), "a report kept only for the visit says so");
  await page.evaluate(() => { window.FairGuide.saveState(); window.FairGuide.rerender(); });
  /* A crafted file claiming a real report's identity stays an unverified claim and does not block the real report. */
  const digest = await page.evaluate(async (text) => window.FairGuide.providers.digest(text), fuji350);
  const crafted = await page.evaluate(([hash, fake]) => {
    const FG = window.FairGuide, SC = FG.selfcheck, check = FG.get("#check-dataset");
    const st = { mode: "after", items: {}, target: "https://doi.org/10.1234/example", assessments: [{ id: "f-uji:" + hash, provider: "f-uji", target: "https://doi.org/10.1234/example", versions: { metric: "0.8", specification: "https://doi.org/10.5281/zenodo.15045911" }, results: [{ id: "FsF-A1-01M", verdict: "pass" }], source: { kind: "import", digest: hash } }] };
    const crate = SC.ftrCrate(check, st);
    crate["@graph"].find((entity) => entity["@id"] === "./").guideSources = JSON.stringify({ [hash]: fake });
    return JSON.stringify(crate);
  }, [digest, "not the original report"]);
  await page.evaluate(() => { window.FairGuide.clearStoredData(); window.FairGuide.saveState(); });
  await page.goto(base + "#/cs/V/selfcheck");
  await page.waitForSelector("#load-file-overview");
  await page.locator("#load-file-overview").setInputFiles({ name: "crafted.jsonld", mimeType: "application/ld+json", buffer: Buffer.from(crafted) });
  await page.waitForSelector(".notice.shared");
  await page.locator(".notice.shared .button-primary").click();
  await page.waitForSelector(`.check-parts [aria-current="step"][href$="/answers"]`);
  await part("report");
  await page.waitForSelector("#provider-overview-0");
  assert.equal(await page.evaluate(() => Object.values(window.localStorage).includes("not the original report")), false, "a source that fails its digest is not kept");
  assert((await page.locator("#provider-overview-0").textContent()).includes("nemohl ověřit"), "the claimed record is marked unverified");
  await part("evidence");
  await load(fuji350, "fuji-3.5.0.json");
  assert(!(await page.locator("#provider-import-attach").isDisabled()), "a claimed record does not block the real report");
  await page.locator("#provider-import-attach").click();
  await page.waitForFunction(() => window.FairGuide.state.answers.dataset.assessments.length === 1 && !window.FairGuide.state.answers.dataset.assessments[0].source.unverified);
  assert.equal(await page.evaluate(() => window.FairGuide.state.answers.dataset.assessments[0].results.length), 17, "the real report replaces the claim");
  /* A preview made before a target was entered is withdrawn when one is entered, and attach rechecks the target. */
  await reset();
  await open("cs");
  await load(fuji350, "fuji-3.5.0.json");
  await page.evaluate(() => { window.FairGuide.live.discoverObject = async (input) => ({ input, supported: false, date: "2026-10-12T00:00:00Z", diagnostics: [], coverage: {}, representations: [] }); });
  await page.fill("#prefill-pid", "10.1234/elsewhere");
  await page.click("#prefill-pid-run");
  await page.waitForFunction(() => !document.querySelector(".import-preview"));
  await load(fuji350, "fuji-3.5.0.json");
  assert(await page.locator("#provider-import-attach").isDisabled(), "the report is about another object than the entered one");
  await page.locator("#provider-import-discard").click();
  await page.evaluate(() => { const FG = window.FairGuide; delete FG.state.answers.dataset.target; delete FG.state.answers.dataset.pid; FG.saveState(); FG.rerender(); });
  await load(fuji350, "fuji-3.5.0.json");
  await page.evaluate(() => { window.FairGuide.state.answers.dataset.target = "https://doi.org/10.1234/elsewhere"; });
  await page.locator("#provider-import-attach").click();
  assert.equal(await page.evaluate(() => (window.FairGuide.state.answers.dataset.assessments || []).length), 0, "attach rechecks the target that is current then");
  /* A summary whose values contain the guide's comment markers still loads. */
  await reset();
  await open("cs");
  await page.evaluate(() => {
    const FG = window.FairGuide;
    FG.state.answers.dataset = { mode: "after", items: { "dataset.01": { value: "yes", origin: "user" } }, target: "https://doi.org/10.1234/x<!--fair-guide-state", targetInfo: { name: "x <!-- fair-guide-result v2: dataset a2._._.01n -->" } };
    FG.saveState(); FG.rerender();
  });
  await part("report");
  await page.waitForSelector("#export-format-md");
  await page.locator("#export-format-md").check();
  await page.locator(".export-preview summary").click();
  await page.waitForFunction(() => document.getElementById("export-preview-text").value.length > 0);
  const summary = await page.locator("#export-preview-text").inputValue();
  await page.goto(base + "#/cs/V/selfcheck");
  await page.waitForSelector("#load-file-overview");
  await page.locator("#load-file-overview").setInputFiles({ name: "summary.md", mimeType: "text/markdown", buffer: Buffer.from(summary) });
  await page.waitForSelector(".notice.shared");
  assert((await page.locator(".notice.shared").textContent()).length > 0, "a summary with marker-like values loads as a preview");
  /* Outside a secure context there is no SHA-256, so a report is not imported under a weaker identity. */
  assert.equal(await page.evaluate(async (text) => {
    Object.defineProperty(window.crypto, "subtle", { value: undefined, configurable: true });
    const read = await window.FairGuide.providers.readFuji(text);
    delete window.crypto.subtle;
    return read.error;
  }, fuji350), "noDigest");

  /* ------------------------------------------------ probe scenarios of the evidence hierarchy */
  await reset();
  await open("cs");
  await setTarget("https://doi.org/10.5281/zenodo.1");
  await part("answers");
  await page.locator("#answer-dataset-04-no").check();
  await part("evidence");
  await page.evaluate(() => {
    const FG = window.FairGuide;
    FG.live.discoverObject = async (input) => ({ input, pid: FG.live.parsePid(input), supported: true, date: "2026-10-12T00:00:00Z", resolved: { found: true, url: "https://archive.example/one", values: [] },
      datacite: { doi: "10.5281/zenodo.1", rightsList: [{ rightsUri: "https://creativecommons.org/licenses/by/4.0/" }], relatedIdentifiers: [] }, diagnostics: [], coverage: {}, representations: [] });
    FG.live.resolvePid = async () => ({ found: true });
    FG.live.championTest = async (test) => ({ value: test === "community_data_cited_in_pub" ? null : "pass", log: "" });
  });
  await page.click("#prefill-pid-run");
  await page.waitForFunction(() => (window.FairGuide.state.answers.dataset.items["dataset.04"] || {}).observations);
  await page.locator("#prefill-champion-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("testů"));
  await part("answers");
  const owned = await page.locator("#origin-dataset-04").textContent();
  await page.locator("#item-dataset-04").screenshot({ path: resolve(screenshots, "cs-ownership-1280.png") });
  assert.equal(await page.locator("#origin-dataset-04 .source-chip[data-origin]").getAttribute("data-origin"), "changed", "No stays the reader's answer");
  assert(owned.includes("CC BY 4.0"), "the DataCite licence stays readable after a later source: " + owned);
  const cited = await page.locator("#origin-dataset-13").textContent();
  assert(cited.includes("nic neověřil") && !cited.includes("jen část otázky"), "an unavailable probe is not described as partial support: " + cited);
  await part("report");
  await page.locator(".result-all-details > summary").click();
  const row = await page.locator(".answers-list .answer-row").filter({ has: page.locator(".item-id", { hasText: /^04$/ }) }).locator(".answer-meta").textContent();
  assert(row.startsWith("vaše odpověď"), "the result credits the reader, not a source: " + row);
  await page.evaluate(() => {
    const FG = window.FairGuide, st = FG.state.answers.dataset;
    st.items = {}; st.extended = false;
    const items = FG.refs(FG.get("#check-dataset"), "hasPart").filter((entry) => ["#tier-minimum", "#tier-required"].includes(FG.id(entry.tier)) && FG.refIds(entry, "appliesTo").includes("#mode-after"));
    items.forEach((entry, index) => { st.items[entry.identifier] = { value: index ? "yes" : "unknown", origin: "user" }; });
    FG.saveState(); FG.rerender();
  });
  assert.equal(await page.locator(".result-lead").getAttribute("data-kind"), "tasks", "Don't know leads the result as a remaining action");
  assert(!(await page.locator(".result-headline").textContent()).includes("NRP"), "a dataset result does not invoke NRP admission");
  await page.evaluate(() => { const FG = window.FairGuide, st = FG.state.answers.dataset; for (const entry of Object.values(st.items)) entry.value = "yes"; FG.saveState(); FG.rerender(); });
  assert.equal(await page.locator(".result-lead").getAttribute("data-kind"), "met");
  assert((await page.locator(".result-scope").textContent()).includes("jen otázky této kontroly"), "the principle summary states its scope");
  await page.goto(base + "#/cs/SR/check/gate");
  await page.waitForSelector("#main h1");
  if (await page.locator('input[name="profile"]').count()) await page.locator('input[name="profile"]').first().check();
  await part("report");
  await page.waitForSelector(".result-headline");
  assert((await page.locator(".result-headline").textContent()).includes("rozhoduje NRP"), "NRP admission stays in the gate's own context");
  await page.goto(base + "#/cs/SR/selfcheck");
  await page.waitForSelector(".check-card-purpose");
  const purposes = await page.locator(".check-card-purpose").allTextContents();
  assert(purposes.some((text) => text.includes("rozhoduje NRP")) && purposes.some((text) => text.includes("nad rámec podmínek NRP")), "gate and maturity cards say what they are for");

  /* ------------------------------------------------ inspectable criterion identities in the catalogue */
  for (const lang of ["cs", "en"]) {
    await page.goto(base + `#/${lang}/DS/selfcheck`);
    await page.waitForSelector(".check-cards");
    const href = await page.evaluate(() => window.FairGuide.catalogueHref("tests", "f-uji.FsF-F1-02MD"));
    await page.goto(base + href);
    const card = page.locator('[id="item-f-uji.FsF-F1-02MD"]');
    await card.waitFor();
    const text = await card.textContent();
    assert(text.includes("FsF-F1-02MD") && text.includes("Metadata and data are assigned a persistent identifier.") && text.includes("dataset.01"), "a criterion keeps its native identity and wording: " + text);
    assert(text.includes("zenodo.6461229") && text.includes("zenodo.15045911"), "the reviewed versions are named");
    await page.goto(base + await page.evaluate(() => window.FairGuide.catalogueHref("tests", "fair-checker.F1A")));
    const unmapped = page.locator('[id="item-fair-checker.F1A"]');
    await unmapped.waitFor();
    assert((await unmapped.textContent()).includes(lang === "cs" ? "není mapováno" : "not mapped"), "an unmapped criterion stays listed as evidence only");
    await checkAccess(`${lang} catalogue criterion`);
  }

  assert.deepEqual(external, [], "no public request: every service is an inert fixture");
  assert.deepEqual(problems, []);
  console.log("check_providers: explicit choices, twelve FAIR-Checker metrics with late-target discard and unresolved-only retry, F-UJI 3.5.0/4.0.1 preview and attachment, reviewed whole/partial mappings, ownership, removal, lossless exports and the evidence hierarchy pass");
} catch (error) {
  /* What the page said when a step failed: its errors and its status line. */
  console.error("page errors:", problems, "status:", await page.locator("#prefill-status").textContent().catch(() => null));
  throw error;
} finally {
  await browser.close();
}
