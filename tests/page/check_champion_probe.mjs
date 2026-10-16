import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { summarize, reviewedCandidates, reviewedRecords } from "../../scripts/probe_champion.mjs";
const source = "https://tests.ostrails.eu";
assert.throws(() => reviewedCandidates([{ id: "a", endpoint: "https://other.example/tests/assess/test/a" }], source));
assert.throws(() => reviewedCandidates([{ id: "a", endpoint: source + "/tests/assess/test/a?url=https://other.example" }], source));
assert.throws(() => reviewedCandidates([{ id: "a", endpoint: source + "/tests/assess/test/b" }], source));
assert.throws(() => reviewedCandidates([{ id: "a", endpoint: source + "/tests/assess/test/a" }, { id: "a", endpoint: source + "/tests/assess/test/a" }], source));
assert.equal(reviewedCandidates([{ id: "a", endpoint: source + "/community-tests/assess/test/a" }], source).length, 1);
assert.throws(() => reviewedRecords([{ id: "same", identifier: "https://doi.org/10.1234/one" }, { id: "same", identifier: "https://hdl.handle.net/11234/two" }]), /duplicate reference/);
assert.throws(() => reviewedRecords([{ id: "a", identifier: "https://doi.org/10.1234/one?redirect=other" }]));
assert.throws(() => reviewedRecords([{ id: "a", identifier: "https://person:password@doi.org/10.1234/one" }]));
assert.equal(reviewedRecords([{ id: "a", identifier: "https://doi.org/10.1234/one" }, { id: "b", identifier: "https://hdl.handle.net/11234/two" }]).length, 2);
const results = summarize([{ test: "a", value: "pass" }, { test: "a", value: "fail" }, { test: "b", value: "pass" }, { test: "b", error: "CORS" }, { test: "c", error: "Timeout" }, { test: "d", value: "indeterminate" }]);
assert.deepEqual(results.map((entry) => entry.health), ["available", "degraded", "unavailable", "available"]);
assert.equal(results[3].definitive, 0, "a returned indeterminate verdict is distinguished from criterion evidence");
console.log("check_champion_probe: reviewed endpoint admission, stable identities and availability distinct from verdicts pass");

const root = resolve(import.meta.dirname, "../..");
const graph = JSON.parse(readFileSync(resolve(root, "_site/ro-crate-metadata.json"), "utf8"))["@graph"];
for (const id of ["dataset.01", "dataset.13", "maturity.01", "maturity.05", "maturity.11"]) {
  assert.equal(graph.find((entry) => entry.identifier === id)?.championEvidenceOnly, true, "evidence-only policy travels with the question");
}
const { chromium } = await import("./browser.mjs");
const browser = await chromium.launch();
const page = await browser.newPage();
const requests = [], errors = [];
page.on("request", (request) => { if (!/^(file|data):/.test(request.url())) requests.push(request.url()); });
page.on("pageerror", (error) => errors.push(error.message));
async function visit(lang, check) {
  await page.goto(pathToFileURL(resolve(root, "_site/index.html")).href + `#/${lang}/${check === "dataset" ? "V" : "SR"}/check/${check}`);
  await page.waitForSelector(check === "dataset" ? "#mode-after" : "#prefill-champion");
  await page.evaluate((id) => { FairGuide.state.answers[id] = { items: {}, extended: true }; FairGuide.saveState(); FairGuide.rerender(); }, check);
  if (check === "dataset") await page.check("#mode-after");
  await page.evaluate(() => {
    const live = FairGuide.live;
    live.resolvePid = async () => ({ found: true, url: "https://archive.example/record" });
    live.discoverObject = async (input) => ({ input, pid: live.parsePid(input), supported: true, date: "2026-10-11", resolved: { found: true, url: "https://archive.example/record" }, representations: [], diagnostics: [], coverage: {} });
    live.championTest = async (id) => ({ value: id === "community_data_cited_in_pub" ? "fail" : "pass", log: "Narrow source observation" });
  });
}
// A check's evidence (where the sample or identifier is entered) and its question cards are separate parts.
async function part(name) {
  const [prefix] = page.url().match(/#\/[a-z]{2}\/[A-Z]+\/check\/[a-z-]+/);
  await page.evaluate((hash) => { window.location.hash = hash; }, prefix + "/" + name);
  await page.waitForSelector(`.check-parts [aria-current="step"][href$="/${name}"]`);
}
async function run(id) {
  const details = page.locator(`#item-${id.replaceAll(".", "-")} .question-details`);
  if (!(await details.evaluate((node) => node.open))) await details.locator(":scope > summary").click();
  await page.click("#test-run-" + id.replaceAll(".", "-"));
  await page.waitForFunction((id) => FairGuide.state.answers[id.split(".")[0]]?.items[id]?.observations?.some((entry) => entry.source === "champion"), id);
}
try {
  for (const lang of ["cs", "en"]) {
    await visit(lang, "maturity");
    await page.fill("#prefill-champion", "10.1234/record");
    await part("answers");
    await page.check("#answer-maturity-05-no");
    await run("maturity.05");
    assert(await page.locator("#answer-maturity-05-no").isChecked(), "protocol pass cannot replace a manual answer about OAI-PMH/NKR");
    await run("maturity.11");
    // The retention test covers only part of the tombstone question, so its pass suggests Partly, never Yes (D-168).
    assert.deepEqual(await page.locator("#item-maturity-11 input:checked").evaluateAll((inputs) => inputs.map((input) => input.value)), ["partly"], "a narrower persistence test suggests only Partly");
    const evidence = await page.evaluate(() => {
      const SC = FairGuide.selfcheck, check = FairGuide.get("#check-maturity");
      const loaded = SC.readPortable(SC.portableState(check, FairGuide.state.answers.maturity));
      return loaded.state.items["maturity.11"];
    });
    // A loaded suggestion is "shared"; only the reader's own answer loads as "user".
    assert.deepEqual([evidence.value, evidence.origin], ["partly", "shared"], "export/import keeps a suggestion apart from the reader's own answer");
    const observed = evidence.observations.find((entry) => entry.source === "champion");
    assert.equal(observed.value, "partly", "export/import retains the partial suggestion");
    assert(observed.notes.some((note) => note.key === "selfcheck.note.partialCoverage"), "export/import retains the partial-coverage basis");
    assert.equal(await page.locator('#tests-maturity-11 .test-list > .test-row > .test-invocation > a[href="https://tests.ostrails.eu/tests/assess/test/fc_metadata_persistence"]').count(), 1, "the invocation identity stays accessible");
    assert.equal(await page.locator("#tests-maturity-02").count(), 0, "an identifier-scheme test does not answer landing-page continuity");
    // A run saved under the earlier evidence-only rule follows the current one on the next visit (D-184).
    await page.evaluate(() => {
      const entry = FairGuide.state.answers.maturity.items["maturity.11"];
      for (const seen of [entry.prefill, ...entry.observations]) if (seen.source === "champion") { seen.value = null; seen.notes = []; }
      delete entry.value; delete entry.origin;
      FairGuide.saveState();
    });
    await page.reload();
    await part("answers");
    await page.waitForSelector("#item-maturity-11");
    assert.deepEqual(await page.locator("#item-maturity-11 input:checked").evaluateAll((inputs) => inputs.map((input) => input.value)), ["partly"], "a saved FAIR Champion run is applied again under the current rule");

    await visit(lang, "dataset");
    await page.fill("#prefill-pid", "10.1234/record");
    await page.click("#prefill-pid-run");
    await page.waitForFunction(() => /Hotovo|Done/.test(document.querySelector("#prefill-status").textContent));
    await part("answers");
    await run("dataset.13");
    // A citation index that finds nothing suggests No, marked as partial coverage: the citation may lie outside it (D-168).
    assert.deepEqual(await page.locator("#item-dataset-13 input:checked").evaluateAll((inputs) => inputs.map((input) => input.value)), ["no"], "citation-index absence suggests No");
    assert(await page.evaluate(() => FairGuide.state.answers.dataset.items["dataset.13"].prefill.notes.some((note) => note.key === "selfcheck.note.partialCoverage")), "citation-index absence is marked as partial coverage");
    assert.equal(await page.evaluate(() => FairGuide.state.answers.dataset.champion.verdicts["community_data_cited_in_pub https://doi.org/10.1234/record"].value), "fail", "retain the actual external verdict");
    assert.equal(await page.locator("#tests-dataset-02").count(), 0);
    assert(await page.locator("#answer-dataset-02-yes").isChecked(), "landing resolution uses the actual resolver observation");
  }
  assert.deepEqual(requests, [], "no network request on entry or when mocked observations are used");
  assert.deepEqual(errors, []);
  console.log("check_champion_probe: bilingual scope safeguards, manual answers, source verdicts, corrected mappings and portable evidence pass");
} finally { await browser.close(); }
