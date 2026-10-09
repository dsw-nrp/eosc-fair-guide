// Live checks for the FAIR Data Guide's self-check, run in Chromium with Playwright against the real services:
// - a real DOI pre-fills the dataset check from DataCite and the DOI resolver;
// - a real Handle pre-fills from the Handle resolver;
// - an identifier that does not exist leaves the items open with a note;
// - a published FIP nanopublication pre-fills the FIP check;
// - FAIRsharing records are found through DataCite for the repositories page and the maturity check;
// - the landing's search finds out what a DOI is from its registration agency and DataCite;
// - every request goes to an allowlisted connector, and only after a click.
// These checks need the network and depend on outside services, so they are not part of the pull-request gate.
// Usage: python scripts/build_site.py && npm run check:live   (set PLAYWRIGHT_BROWSERS_PATH if the browser lives outside the default cache)

import { chromium } from "playwright";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const site = resolve(root, "_site"); // the built site (python scripts/build_site.py)
const pageUrl = pathToFileURL(resolve(site, "index.html")).href;
const config = JSON.parse(readFileSync(resolve(site, "assets/data/ui.js"), "utf8").match(/^window\.FairGuideData\.ui = (.*);$/m)[1]).config;
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
await page.locator('label[for="extended-toggle"]').click();
await page.locator("#prefill-pid").fill("https://doi.org/" + SAMPLE.doi);
let status = await prefill("#prefill-pid-run");
console.log("DOI:", status);
if ((await answer("D01")) !== "yes") fail("DOI: D01 is not pre-filled yes");
if ((await answer("D02")) !== "yes") fail("DOI: D02 is not pre-filled yes");
if (!(await page.locator("#origin-D02").textContent()).includes("zenodo.org")) fail("DOI: D02 does not show where the DOI leads");
if (!(await page.locator(".target-card").textContent()).includes("FAIR assessment")) fail("DOI: the resolved DOI does not show its title");
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
await page.locator('label[for="extended-toggle"]').click();
await page.locator("#prefill-nanopub").fill("https://w3id.org/np/" + SAMPLE.fip);
status = await prefill("#prefill-nanopub-run");
console.log("Nanopublication:", status);
const answered = await page.evaluate(() => document.querySelectorAll('fieldset.item input:checked').length);
if (!answered) fail("nanopublication: no FIP item was pre-filled");
const origin = await page.locator(".source-chip").first().textContent();
if (!origin.includes("nanopublikace")) fail("nanopublication: the source is not named: " + origin);
if (!(await page.locator(".origin a").count())) fail("nanopublication: declared resources are not listed");

// FAIRsharing records through DataCite: the repositories page and the maturity check's registration question.
await open("#/cs/V/repositories");
await page.locator("#fairsharing-load").click();
await page.waitForFunction(() => {
  const status = document.getElementById("fairsharing-status");
  return status && !status.textContent.includes("Hledám");
}, null, { timeout: 60000 });
const fairsharingStatus = await page.locator("#fairsharing-status").textContent();
console.log("FAIRsharing:", fairsharingStatus);
const csda = page.locator(".card", { hasText: "Czech Social Science Data Archive" });
if (!(await csda.locator(".fairsharing-record").count())) fail("FAIRsharing: the ČSDA record was not found: " + fairsharingStatus);
await open("#/cs/SR/check/maturity");
await page.locator('label[for="extended-toggle"]').click();
await page.locator("#prefill-re3data").fill("r3d100010484");
status = await prefill("#prefill-re3data-run");
console.log("re3data and FAIRsharing:", status);
if ((await answer("S18")) !== "yes") fail("FAIRsharing: S18 is not answered yes for ČSDA");

// What a DOI is: a Zenodo DOI is a DataCite output, a journal article's DOI a Crossref publication.
async function findOut(pid) {
  await open("#/cs/V/path/start");
  await page.fill("#search-input", pid);
  await page.locator("#search-input").press("Enter");
  await page.locator("#search-results .result-primary").click();
  await page.waitForFunction(() => {
    const said = document.querySelector("#search-results .search-basis");
    return said && !said.closest(".identifier-results").textContent.includes("Zjišťujeme");
  }, null, { timeout: 60000 });
  return page.locator("#search-results .search-basis").textContent();
}
let said = await findOut(SAMPLE.doi);
console.log("What is the Zenodo DOI:", said);
if (!said.includes("Jde o") || !said.includes("DataCite")) fail("lookup: the Zenodo DOI is not placed through DataCite: " + said);
said = await findOut("10.1038/sdata.2016.18");
console.log("What is the article DOI:", said);
if (!said.includes("Jde o publikaci") || !said.includes("Crossref")) fail("lookup: the article DOI is not placed as a Crossref publication: " + said);

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
