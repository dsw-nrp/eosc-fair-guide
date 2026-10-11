// Shared question states, conservative suggestions and bounded portable evidence, with inert public fixtures.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { AxeBuilder } from "@axe-core/playwright";

const root = resolve(import.meta.dirname, "../..");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const { chromium } = await import("playwright");
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();
const base = pathToFileURL(resolve(root, "_site/index.html")).href;
const problems = [];
const external = [];
let axeRunning = false;
page.on("pageerror", (error) => problems.push(error.message));
page.on("console", (message) => { if (message.type() === "error" && !axeRunning) problems.push(message.text()); });
page.on("request", (request) => { if (!/^(?:file|data):/.test(request.url()) && !axeRunning) external.push(request.url()); });
const screenshots = resolve(root, ".cache/screenshots/questions");
mkdirSync(screenshots, { recursive: true });
async function open(lang, id, lens = "V") {
  await page.goto(base + `#/${lang}/${lens}/check/${id}`);
  await page.waitForSelector(id === "dataset" ? "#mode-after" : `#item-${id}-01`);
  if (id === "dataset") await page.locator("#mode-after").check();
}
async function checkAccess() {
  axeRunning = true;
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  axeRunning = false;
  assert.deepEqual(result.violations.map((entry) => entry.id), []);
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "no horizontal overflow");
}
async function checkGroupIcons() {
  for (const [groups, icons] of [[".item-group", ".item-group > h2 svg.group-icon"], [".summary-group", ".summary-group-label svg.group-icon"], [".result-group", ".result-group > h3 svg.group-icon"]]) {
    const count = await page.locator(groups).count();
    assert(count > 0); assert.equal(await page.locator(icons).count(), count, "every section has an icon in the questions and both result views");
  }
}
try {
  for (const lang of ["cs", "en"]) {
    await page.evaluate(() => { if (window.FairGuide) { window.FairGuide.state.answers = {}; window.FairGuide.saveState(); } });
    await open(lang, "software");
    assert.equal(await page.locator(".prefill-row #prefill-software").count(), 1);
    assert.equal(await page.locator('#item-software-04 [data-local-test="guide-software-04"] a[href="assets/js/tests/software.js"]').count(), 1, "local test source is visible beside the question");
    assert.equal(await page.locator('#item-software-04 [data-local-test="guide-software-04"] a[href^="assets/js/tests/index.html"]').count(), 1, "local test documentation is visible beside the question");
    assert((await page.locator("#item-software-01 .question-relations").textContent()).includes(lang === "cs" ? "Odpovědnost" : "Responsibility"));
    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await checkAccess();
      await page.screenshot({ path: resolve(screenshots, `${lang}-software-empty-${width}.png`), fullPage: true });
    }
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.evaluate(() => {
      const FG = window.FairGuide;
      FG.live.softwareRepository = async () => ({ supported: true, provider: "github", repository: "team/research", url: "https://github.com/team/research", ref: "main", commit: "a".repeat(40), date: "2026-10-11T12:00:00Z",
        metadata: { name: "Research software", visibility: "public", description: "A useful research program" }, files: [{ path: "package.json", kind: "dependency-build", text: '{"dependencies":{"library":"1.0"}}', url: "https://github.com/team/research/blob/" + "a".repeat(40) + "/package.json" }], diagnostics: [], coverage: { readFiles: 1, selectedFiles: 1 } });
    });
    await page.fill("#prefill-software", "https://github.com/team/research");
    await page.click("#prefill-software-run");
    await page.waitForSelector("#origin-software-04");
    assert(await page.locator("#answer-software-04-partly").isChecked());
    await page.locator('label[for="extended-toggle"]').click();
    await checkGroupIcons();
    assert(await page.locator("#answer-software-09-yes").isChecked());
    await page.locator("#answer-software-04-no").check();
    await page.click("#prefill-software-run");
    await page.waitForFunction(() => !document.getElementById("prefill-status").textContent.includes("Načítám") && !document.getElementById("prefill-status").textContent.includes("Loading"));
    assert(await page.locator("#answer-software-04-no").isChecked(), "a refresh cannot replace the authored answer");
    const roundTrip = await page.evaluate(() => {
      const FG = window.FairGuide, SC = FG.selfcheck, check = FG.get("#check-software"), st = FG.state.answers.software;
      const saved = SC.portableState(check, st), loaded = SC.readPortable(saved);
      const old = structuredClone(saved); old.v = 1; delete old.inspection; delete old.champion; for (const entry of Object.values(old.items)) delete entry.observations;
      return { v: saved.v, manual: loaded.state.items["software.04"].origin, value: loaded.state.items["software.04"].value,
        commit: loaded.state.targetInfo.commit, observations: loaded.state.items["software.04"].observations.length,
        legacy: SC.readPortable(old).error || null, newer: SC.readPortable({ ...saved, v: 3 }).error,
        bytes: new TextEncoder().encode(JSON.stringify(SC.ftrCrate(check, st))).length };
    });
    assert.equal(roundTrip.v, 2); assert.equal(roundTrip.manual, "user"); assert.equal(roundTrip.value, "no");
    assert.equal(roundTrip.commit, "a".repeat(40)); assert(roundTrip.observations > 0); assert.equal(roundTrip.legacy, null); assert.equal(roundTrip.newer, "newer"); assert(roundTrip.bytes < 2 * 1024 * 1024);
    await page.locator("#item-software-04 .evidence-details > summary").click();
    const longValue = "Complete retained evidence\n".repeat(650);
    await page.evaluate((value) => {
      const FG = window.FairGuide, SC = FG.selfcheck;
      const saved = SC.portableState(FG.get("#check-software"), FG.state.answers.software);
      const entry = saved.items["software.04"];
      entry.observations[0].fields = [{ path: "description", values: [value] }];
      entry.prefill = entry.observations[0];
      FG.state.answers.software = SC.readPortable(saved).state; FG.saveState(); FG.rerender();
    }, longValue);
    await page.waitForSelector("#item-software-04 .evidence-details");
    await page.locator("#item-software-04 .evidence-details > summary").click();
    const retained = page.locator("#item-software-04 .evidence-value").first();
    assert.equal(await retained.textContent(), longValue, "a normal bounded source value is preserved in full beyond the old 2000-character cut");
    assert(await retained.evaluate((node) => node.scrollHeight > node.clientHeight && getComputedStyle(node).overflowY === "auto"), "complete long values scroll inside their container");
    await retained.focus();
    await page.keyboard.press("End");
    for (const width of [1280, 390]) {
      const oldMain = await page.$("#main");
      const wide = page.viewportSize().width >= 960;
      await page.setViewportSize({ width, height: 900 });
      if (wide !== (width >= 960)) await page.waitForFunction((node) => !node.isConnected, oldMain);
      const details = page.locator("#item-software-04 .evidence-details");
      if (!await details.evaluate((node) => node.open)) await details.locator(":scope > summary").click();
      assert.equal(await retained.textContent(), longValue);
      await retained.evaluate((node) => { node.scrollTop = 0; });
      await checkAccess();
      await page.screenshot({ path: resolve(screenshots, `${lang}-software-edited-${width}.png`), fullPage: true });
      await page.locator("#item-software-04").screenshot({ path: resolve(screenshots, `${lang}-software-question-${width}.png`) });
    }
    await open(lang, "cdif", "K");
    await page.evaluate(() => {
      const FG = window.FairGuide;
      FG.live.discoverObject = async (input) => ({ input, pid: FG.live.parsePid(input), supported: true, date: "2026-10-11T12:00:00Z", resolved: { found: true, url: "https://archive.example/one", values: [{ type: "URL", value: "https://archive.example/one" }] }, datacite: null, diagnostics: [{ code: "unavailable", source: "landing", url: "https://archive.example/other", message: "Browser access unavailable" }], coverage: {},
        representations: [{ source: "landing", url: "https://archive.example/one", identity: "matched", format: "application/ld+json", profiles: [], data: { "@context": "https://schema.org", identifier: "https://doi.org/10.1234/example", name: "Dataset title", license: "https://creativecommons.org/licenses/by/4.0/" } }] });
    });
    await page.fill("#prefill-pid", "10.1234/example"); await page.click("#prefill-pid-run");
    await page.waitForSelector("#origin-cdif-02");
    assert(await page.locator("#answer-cdif-02-partly").isChecked());
    assert.equal(await page.locator("#item-cdif-04 input:checked").count(), 1);
    await page.locator('label[for="extended-toggle"]').click();
    assert.equal(await page.locator("#item-cdif-27 input:checked").count(), 0, "no profile-conformance answer from Schema.org");
    await page.locator("#item-cdif-04 .evidence-details > summary").click();
    assert((await page.locator("#origin-cdif-04").textContent()).includes("CC BY 4.0"));
    assert((await page.locator("#origin-cdif-04 .content").textContent()).includes("https://creativecommons.org/licenses/by/4.0/"), "display shortening preserves full retained URI");
    await page.locator(".inspection-details > summary").click();
    await checkAccess();
    await page.screenshot({ path: resolve(screenshots, `${lang}-cdif-partial-390.png`), fullPage: true });
    await page.locator("#item-cdif-04").screenshot({ path: resolve(screenshots, `${lang}-cdif-evidence.png`) });
    await open(lang, "fdo");
    await page.evaluate(() => { const FG = window.FairGuide; FG.state.answers.fdo.items["fdo.09"] = { value: "yes", origin: "user" }; FG.saveState(); });
    await page.locator('label[for="extended-toggle"]').click();
    assert.equal(await page.locator("fieldset.item").count(), 31); assert.equal(await page.locator(".item-context").count(), 3);
    await checkGroupIcons();
    assert.equal(await page.locator("#item-fdo-09 input").count(), 0);
    assert.equal(await page.locator("#item-fdo-09 .historical-answer").count(), 1);
    await page.locator("#item-fdo-09 details.item-basis > summary").click();
    await page.locator("#item-fdo-09 .clause-guidance > summary").click();
    assert.equal(await page.locator("#item-fdo-09 .clause-guidance > .content").getAttribute("lang"), "en");
    await page.locator("#item-fdo-09").screenshot({ path: resolve(screenshots, `${lang}-fdo-source.png`) });
    await page.fill("#prefill-pid", "urn:example:managed-object");
    await page.evaluate(() => { window.FairGuide.live.discoverObject = async (input) => ({ input, supported: false, date: "2026-10-11T12:00:00Z", diagnostics: [{ code: "unsupported-pid", message: "Manual assessment remains available" }], coverage: {}, representations: [] }); });
    await page.click("#prefill-pid-run");
    await page.waitForFunction(() => document.querySelector(".inspection-details"));
    assert.equal(await page.locator("#prefill-pid").inputValue(), "urn:example:managed-object");
    assert.equal(await page.locator("#answer-fdo-01-no:checked").count(), 0);
    await checkAccess();
    await page.screenshot({ path: resolve(screenshots, `${lang}-fdo-context-390.png`), fullPage: true });
  }
  await open("en", "maturity", "SR");
  await page.evaluate(() => {
    const FG = window.FairGuide; const records = Array.from({ length: 5 }, (_, index) => "https://archive.example/object/" + index);
    const verdicts = Object.fromEntries(records.map((record, index) => ["fc_structured_metadata " + record, { value: index === 4 ? null : "pass", log: "Original observation " + index + " <script>inert</script>", error: index === 4 ? "Request unavailable" : undefined }]));
    FG.state.answers.maturity = { items: {}, extended: true, sample: records.join("\n"), champion: { input: records.join("\n"), records, verdicts, date: "2026-10-11" } }; FG.saveState(); FG.rerender();
  });
  await page.waitForSelector("#tests-maturity-03 .test-records");
  await page.locator("#tests-maturity-03 .test-records > summary").click();
  assert.equal(await page.locator("#tests-maturity-03 .probe-record").count(), 5);
  assert((await page.locator("#tests-maturity-03").textContent()).includes("Request unavailable"));
  const probes = await page.evaluate(() => {
    const FG = window.FairGuide, SC = FG.selfcheck, check = FG.get("#check-maturity"), st = FG.state.answers.maturity;
    const portable = SC.portableState(check, st), loaded = SC.readPortable(portable);
    return { restored: Object.keys(loaded.state.champion.verdicts).length,
      members: SC.ftrCrate(check, st)["@graph"].filter((entry) => entry["ftr:outputFromTest"] && entry["@id"].startsWith("#result-fc_structured_metadata")).map((entry) => ({ target: entry["ftr:assessmentTarget"]["@id"], log: entry["ftr:log"] })) };
  });
  assert.equal(probes.restored, 5); assert.equal(probes.members.length, 4);
  assert.equal(await page.locator('#tests-maturity-03 .test-invocation a[href*="/assess/test/fc_structured_metadata"]').count(), 1, "question shows the actual external POST endpoint");
  assert(await page.locator('#tests-maturity-03 .test-invocation a').count() >= 2, "question links external test documentation too");
  assert(probes.members.every((entry, index) => entry.target.endsWith("/" + index) && entry.log.includes("observation " + index)));
  const bounded = await page.evaluate(() => {
    const FG = window.FairGuide, SC = FG.selfcheck, check = FG.get("#check-maturity"), st = structuredClone(FG.state.answers.maturity);
    for (const item of FG.refs(check, "hasPart")) {
      const observations = Array.from({ length: 8 }, (_, index) => ({ source: "landing", date: "2026-10-11", value: "partly", notes: [], list: [], record: "https://archive.example/" + index,
        subject: "https://archive.example/" + index, representation: "application/ld+json", fields: [{ path: "description", values: ["長".repeat(2000)] }] }));
      st.items[item.identifier] = { value: "no", origin: "user", observations, prefill: observations[7] };
    }
    for (const entry of Object.values(st.champion.verdicts)) entry.log = "長".repeat(5000);
    const saved = SC.portableState(check, st), ftr = SC.ftrCrate(check, st);
    return { bytes: new TextEncoder().encode(JSON.stringify(ftr)).length, restored: SC.readPortable(saved).error || null,
      shortened: Object.values(saved.items).some((entry) => entry.prefill.truncated), original: st.items[FG.refs(check, "hasPart")[0].identifier].observations.length,
      answers: Object.values(saved.items).every((entry) => entry.value === "no" && entry.origin === "user") };
  });
  assert(bounded.bytes < 2 * 1024 * 1024, "a large multibyte evidence export remains loadable within the file limit");
  assert.equal(bounded.restored, null); assert.equal(bounded.shortened, true); assert.equal(bounded.original, 8); assert.equal(bounded.answers, true);
  await page.locator("#tests-maturity-03 .probe-log > summary").first().click();
  assert.equal(await page.locator("#tests-maturity-03 .probe-log script").count(), 0, "probe output remains inert text");
  await page.screenshot({ path: resolve(screenshots, "en-repository-probe-390.png"), fullPage: true });
  await page.locator("#item-maturity-03").screenshot({ path: resolve(screenshots, "en-repository-probe-question.png") });
  assert.deepEqual(external, [], "no public request without an explicit real-service fixture");
  assert.deepEqual(problems, []);
  console.log("check_questions: bilingual question states, source context, software/PID suggestions, manual edits, v1/v2 import and five-record logs pass");
} finally { await browser.close(); }
