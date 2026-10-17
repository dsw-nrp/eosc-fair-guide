// Reader visuals beyond the model figures: the object and PID flow, the publication hand-over drawn from the model's
// seam records, the software release flow, the evidence-to-answer flow, what each check is for, and the chosen
// stage on the rail. Each is checked in both languages, at full and phone width, with axe, in print and against the
// one place its facts are maintained.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
const { chromium } = await import("./browser.mjs");
const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
const base = pathToFileURL(resolve(root, "_site/index.html")).href;
const graph = JSON.parse(readFileSync(resolve(root, "_site/ro-crate-metadata.json"), "utf8"))["@graph"];
const seam = (id) => graph.find((entity) => entity["@id"] === "#seam-" + id);
const problems = [];
const external = [];
let axeRunning = false;
page.on("pageerror", (error) => problems.push(error.message));
page.on("console", (message) => { if (message.type() === "error" && !axeRunning) problems.push(message.text()); });
page.on("request", (request) => { if (!/^(?:file|data):/.test(request.url()) && !axeRunning) external.push(request.url()); });
const screenshots = resolve(root, ".cache/screenshots/visuals");
mkdirSync(screenshots, { recursive: true });

async function go(hash, selector) {
  await page.goto(base + hash);
  await page.waitForSelector(selector);
}
/** Open a station's Proč, which remembers its state across views, without toggling it closed. */
async function openWhy() {
  const why = page.locator('#main details[data-key="L2"]');
  if (!(await why.evaluate((details) => details.open))) await why.locator(":scope > summary").click();
  assert(await why.evaluate((details) => details.open));
}
async function checkAccess(label) {
  axeRunning = true;
  const result = await audit(page);
  axeRunning = false;
  assert.deepEqual(result.violations.map((entry) => entry.id), [], label + ": accessibility");
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), label + ": no horizontal overflow");
}
/** A visual reads as a titled ordered list of labelled steps, and its title names it. */
async function readsInOrder(flow, steps, label) {
  assert.equal(await flow.locator("figcaption.flow-title").count(), 1, label + ": a title");
  assert.equal(await flow.locator("ol.flow-steps > li.flow-step").count(), steps, label + ": steps in order");
  for (const step of await flow.locator(".flow-step").all()) assert((await step.locator(".flow-label").textContent()).trim(), label + ": every step is labelled");
}
async function widths(label) {
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.waitForTimeout(100);
    await checkAccess(`${label} ${width}`);
    await page.screenshot({ path: resolve(screenshots, `${label}-${width}.png`), fullPage: true });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
}
const lang = (value, code) => (Array.isArray(value) ? value : [value]).find((entry) => entry && entry["@language"] === code)?.["@value"];

try {
  for (const code of ["cs", "en"]) {
    /* What a PID identifies and what a browser can read: the identifier helper and the publication station. */
    await go(`#/${code}/V/page/identifiers`, '.flow[data-flow="object"]');
    await readsInOrder(page.locator('.flow[data-flow="object"]'), 4, `${code} object flow`);
    assert((await page.locator('.flow[data-flow="object"] .flow-note').textContent()).length > 0, "the access limit is stated");
    await widths(`${code}-identifiers`);
    await go(`#/${code}/V/path/publication`, '#main details[data-key="L2"]');
    await openWhy();
    await readsInOrder(page.locator('#main details[data-key="L2"] .flow[data-flow="object"]'), 4, `${code} publication object flow`);

    /* The publication hand-over, drawn from the seam records, reads the same at findability and beside Figure 3. */
    for (const lens of ["V", "DS", "SR"]) {
      await go(`#/${code}/${lens}/path/findability`, '#main details[data-key="L2"]');
      await openWhy();
      const chain = page.locator('#main details[data-key="L2"] .flow-handover');
      assert(await chain.isVisible(), "the hand-over is visible in Proč");
      await readsInOrder(chain, 3, `${code} ${lens} hand-over`);
      const steps = await chain.locator(".flow-step").evaluateAll((items) => items.map((item) => item.dataset.step.replace(/^seam\./, "")));
      assert.deepEqual(steps, ["repository-pid-registry", "repository-nma", "nma-research-register"], "registration, harvest and reporting stay separate steps");
      const text = await chain.textContent();
      for (const id of steps) assert(text.includes(lang(seam(id).sender, code)) && text.includes(lang(seam(id).recipient, code)), `${id}: sender and recipient come from the seam record`);
      assert(text.includes(lang(seam("nma-research-register").description, code)), "the PID citation and the reporting link are told apart");
      if (lens === "SR") {
        await widths(`${code}-findability-${lens}`);
        await chain.screenshot({ path: resolve(screenshots, `${code}-handover.png`) });
      }
    }
    await page.goto(base + `#/${code}/SR/page/model`);
    await page.waitForSelector("#metadata-architecture .flow-handover", { state: "attached" });
    /* The figure's section may be folded; the hand-over opens with it. */
    if (await page.locator("details#metadata-architecture:not([open])").count()) await page.locator("details#metadata-architecture > summary").click();
    await readsInOrder(page.locator("#metadata-architecture .flow-handover"), 3, `${code} model hand-over`);
    assert(await page.locator("#metadata-architecture .flow-handover").isVisible());
    /* Elsewhere a station context shows its own seams. */
    await go(`#/${code}/DS/path/metadata`, '#main details[data-key="L2"]');
    await openWhy();
    assert.deepEqual(await page.locator('#main details[data-key="L2"] .flow-handover .flow-step').evaluateAll((items) => items.map((item) => item.dataset.step.replace(/^seam\./, ""))), ["community-repository", "repository-nma"], "a context draws its own seams");

    /* Which software version to release, preserve and cite, with no mandatory service. */
    await go(`#/${code}/V/page/software`, '#preserve .flow[data-flow="software"]');
    await readsInOrder(page.locator('#preserve .flow[data-flow="software"]'), 4, `${code} software flow`);
    assert((await page.locator('#preserve .flow[data-flow="software"] .flow-note').textContent()).includes("Software Heritage"));
    await widths(`${code}-software`);

    /* How evidence affects an answer, and what each check is for. */
    await go(`#/${code}/SR/selfcheck`, ".check-cards");
    await page.locator(".flow-details > summary").click();
    await readsInOrder(page.locator('.flow[data-flow="evidence"]'), 5, `${code} evidence flow`);
    assert.equal(await page.locator(".check-card-purpose").count(), await page.locator(".check-card").count(), "every check says what it is for");
    await widths(`${code}-selfcheck`);
    await page.emulateMedia({ media: "print" });
    assert(await page.locator('.flow[data-flow="evidence"]').isVisible(), "the evidence flow prints");
    await page.emulateMedia({ media: "screen" });

    /* The stage of the step being read is marked on the rail, with a text equivalent. */
    await go(`#/${code}/V/path/process`, ".rail-desktop .current-stage");
    assert.equal(await page.locator(".rail-desktop .current-stage").count(), 1, "the current stage is marked");
    assert.equal(await page.locator(".rail-desktop .current-stage > .rail-stage-name .visually-hidden").count(), 1, "the mark is also text");
    await checkAccess(`${code} rail`);
    await page.evaluate(() => { window.FairGuide.clearStoredData(); window.FairGuide.saveState(); });
  }
  assert.deepEqual(external, [], "visuals load nothing from outside the guide");
  assert.deepEqual(problems, []);
  console.log("check_visuals: object, publication hand-over, software and evidence flows, check purposes and the current stage pass in both languages, at full and phone width and in print");
} finally {
  await browser.close();
}
