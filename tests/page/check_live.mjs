// Live checks for the FAIR Data Guide's self-check, run in Chromium with Playwright against the real services:
// - a real DOI pre-fills the dataset check from DataCite and the DOI resolver;
// - a real Handle pre-fills from the Handle resolver;
// - an identifier that does not exist leaves the items open with a note;
// - a published FIP nanopublication pre-fills the FIP check;
// - every request goes to an allowlisted connector, and only after a click.
// These checks need the network and depend on outside services, so they are not part of the pull-request gate.
// Usage: npm run check:live   (set PLAYWRIGHT_BROWSERS_PATH if the browser lives outside the default cache)

import { chromium } from "playwright";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const pageUrl = pathToFileURL(resolve(root, "index.html")).href;
const config = JSON.parse(readFileSync(resolve(root, "index.html"), "utf8").match(/<script type="application\/json" id="ui">(.*?)<\/script>/s)[1]).config;
const origins = config.connectors.map((connector) => connector.origin);
const SAMPLE = {
  doi: "10.5281/zenodo.21726258",
  handle: "11234/1-5787",
  missing: "10.5281/zenodo.1000000000000",
  fip: "RAhoyQ_s4N_K_yuZ6jeolF5L8u2y75dcISHS8UJ-MZ5fM",
};
const failures = [];
const fail = (message) => failures.push(message);

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();
const requests = [];
page.on("request", (request) => {
  const url = request.url();
  if (!url.startsWith("file:") && !url.startsWith("data:") && !url.startsWith("blob:")) requests.push(url);
});

async function open(hash) {
  await page.goto(pageUrl + hash);
  await page.waitForSelector("#main h1");
}

async function prefill(button) {
  await page.locator(button).click();
  await page.waitForFunction(() => {
    const status = document.getElementById("prefill-status");
    return status && status.textContent && !status.textContent.includes("Načítám");
  }, null, { timeout: 60000 });
  return page.locator("#prefill-status").textContent();
}

const answer = (id) => page.evaluate((item) => {
  const input = document.querySelector(`input[name="answer-${item}"]:checked`);
  return input ? input.value : null;
}, id);

// Dataset check from a DOI.
await open("#/cs/V/check/dataset");
await page.locator("#mode-after").check();
if (requests.length) fail("requests before any lookup: " + requests.join(", "));
await page.locator("#extended-toggle").click();
await page.locator("#prefill-pid").fill("https://doi.org/" + SAMPLE.doi);
let status = await prefill("#prefill-pid-run");
console.log("DOI:", status);
if ((await answer("D01")) !== "yes") fail("DOI: D01 is not pre-filled yes");
if ((await answer("D02")) !== "yes") fail("DOI: D02 is not pre-filled yes");
if (!(await page.locator("#origin-D02").textContent()).includes("zenodo.org")) fail("DOI: D02 does not show where the DOI leads");
if ((await answer("D04")) !== "yes") fail("DOI: D04 (licence URI) is not pre-filled yes");
if (!(await page.locator("#origin-D04").textContent()).includes("DataCite")) fail("DOI: D04 does not name DataCite");
if ((await answer("D11")) === "yes") fail("DOI: D11 exceeds its pre-fill level");

// Dataset check from a Handle: only the resolver answers.
await page.locator("#prefill-pid").fill(SAMPLE.handle);
status = await prefill("#prefill-pid-run");
console.log("Handle:", status);
if (!(await page.locator("#origin-D02").textContent()).includes("lindat")) fail("Handle: D02 does not show where the Handle leads");

// An identifier that does not exist.
await page.evaluate(() => { localStorage.clear(); });
await page.goto("about:blank");
await open("#/cs/V/check/dataset");
await page.locator("#mode-after").check();
await page.locator("#prefill-pid").fill(SAMPLE.missing);
status = await prefill("#prefill-pid-run");
console.log("Missing:", status);
if (await answer("D01")) fail("missing identifier: D01 was pre-filled");
if (!(await page.locator("#origin-D01").textContent()).includes("nepodařilo")) fail("missing identifier: D01 has no note");
if (!status.includes("nezná")) fail("missing identifier: DataCite not reported as not knowing it");

// FIP check from a published nanopublication.
await open("#/cs/K/check/fip");
await page.locator("#extended-toggle").click();
await page.locator("#prefill-nanopub").fill("https://w3id.org/np/" + SAMPLE.fip);
status = await prefill("#prefill-nanopub-run");
console.log("Nanopublication:", status);
const answered = await page.evaluate(() => document.querySelectorAll('fieldset.item input:checked').length);
if (!answered) fail("nanopublication: no FIP item was pre-filled");
const origin = await page.locator(".source-chip").first().textContent();
if (!origin.includes("nanopublikace")) fail("nanopublication: the source is not named: " + origin);
if (!(await page.locator(".origin a").count())) fail("nanopublication: declared resources are not listed");

for (const url of requests) {
  if (!origins.some((allowed) => url.startsWith(allowed + "/"))) fail("request outside the connector allowlist: " + url);
}

await browser.close();
if (failures.length) {
  console.error(failures.map((failure) => "FAIL " + failure).join("\n"));
  console.error(`${failures.length} problem(s)`);
  process.exit(1);
}
console.log(`live checks passed (${requests.length} requests, all to allowlisted services)`);
