// DataCite in the repository finder and the maturity check, run in Chromium against the built site with every
// DataCite response replaced by a fixture and every other external request refused:
// - a finder entry offers DataCite only where the reviewed snapshot identifies its repository, reads current
//   figures on request, and states their retrieval date and links to DataCite's own pages;
// - an entry the DataCite snapshot does not list offers no lookup;
// - the maturity check draws a random sample of the repository's records from DataCite only once the repository is
//   known, lists the records with their titles before any test runs, replaces one record at a time and keeps the
//   sample field editable by hand.
// Usage: python scripts/build_site.py && node tests/page/check_datacite.mjs

import assert from "node:assert/strict";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
const { chromium } = await import("./browser.mjs");
const base = pathToFileURL(resolve(root, "_site/index.html")).href;

/* DataCite's repositories by ID and by re3data DOI; LINDAT's re3data DOI finds none. */
const REPOSITORIES = { "gesis.csda": "Czech Social Science Data Archive", "cern.zenodo": "Zenodo" };
const BY_RE3DATA = { "10.17616/R35P6H": "gesis.csda" };
const COUNTS = {
  total: 7634,
  resourceTypes: [{ id: "dataset", title: "Dataset", count: 7630 }, { id: "text", title: "Text", count: 2 }],
  licenses: [{ id: "cc-by-4.0", title: "CC-BY-4.0", count: 19 }],
  schemaVersions: [{ id: "4", title: "Schema 4", count: 7633 }],
};
const record = (n) => ({ id: `10.14473/fixture${n}`, type: "dois", attributes: { doi: `10.14473/fixture${n}`, titles: [{ title: n === 2 ? '<img src="https://evil.example/x">Survey 2' : `Survey ${n}` }] } });
let draws = 0;

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
const page = await context.newPage();
const requests = [];
const problems = [];
/* axe fetches stylesheets to inspect them; the page's own CSP blocks that, which is the page working. */
let auditing = false;
const accessible = async (label) => {
  auditing = true;
  try {
    assert.deepEqual((await audit(page)).violations, [], label);
  } finally {
    auditing = false;
  }
};
page.on("pageerror", (error) => problems.push(error.message));
page.on("console", (message) => { if (message.type() === "error" && !auditing) problems.push(message.text()); });
await page.route(/^https?:/, async (route) => {
  const url = new URL(route.request().url());
  requests.push(url.href);
  if (url.origin !== "https://api.datacite.org") { problems.push("unexpected request: " + url.href); return route.abort(); }
  let body = { data: [], meta: { total: 0 } };
  let status = 200;
  const client = url.searchParams.get("client-id");
  if (url.pathname.startsWith("/clients/")) {
    const id = decodeURIComponent(url.pathname.slice("/clients/".length));
    if (REPOSITORIES[id]) body = { data: { id, type: "clients", attributes: { name: REPOSITORIES[id] } } };
    else status = 404;
  } else if (url.pathname === "/clients") {
    const id = BY_RE3DATA[url.searchParams.get("re3data-id")];
    body = { data: id ? [{ id, type: "clients", attributes: { name: REPOSITORIES[id] } }] : [], meta: { total: id ? 1 : 0 } };
  } else if (url.pathname === "/dois" && client && url.searchParams.get("disable-facets") === "false") {
    body = { data: [], meta: COUNTS };
  } else if (url.pathname === "/dois" && client && url.searchParams.get("random") === "true") {
    assert.equal(url.searchParams.get("resource-type-id"), null, "a sample includes every record type the repository registers");
    assert.equal(url.searchParams.get("query"), "-relatedIdentifiers.relationType:IsPartOf", "records that are part of another are left out");
    draws += 1;
    /* The first draw gives records 1–5; each later draw gives one record already in the sample and a new one. */
    body = { data: draws === 1 ? [1, 2, 3, 4, 5].map(record) : [record(1), record(5 + draws)], meta: { total: 2078 } };
  }
  await route.fulfill({ status, headers: { "access-control-allow-origin": "*" }, contentType: "application/json", body: JSON.stringify(body) });
});

async function visit(hash, selector) {
  await page.goto(base + hash);
  await page.waitForSelector(selector, { timeout: 20000 });
}

try {
  /* ------------------------------------------------ the repository finder */
  await visit("#/cs/K/catalogue/repo/dom/csda", ".catalogue-results .entry-card");
  /* Long enough for a lookup the page started by itself to have gone out. */
  await page.waitForTimeout(500);
  assert.equal(requests.length, 0, "opening an entry asks DataCite nothing");
  await page.locator(".datacite-read button").click();
  await page.waitForSelector("section.datacite-read");
  /* Czech groups thousands with a no-break space. */
  const facts = (await page.locator("section.datacite-read").innerText()).replace(/ /g, " ");
  for (const expected of ["Podle DataCite, načteno", "gesis.csda", "Registrovaná DOI", "7 634", "Dataset (7 630)", "CC-BY-4.0 (19)", "Schema 4 (7 633)"]) {
    assert(facts.includes(expected), `the finder's DataCite facts lack "${expected}": ${facts}`);
  }
  assert(facts.includes(new Date().getDate() + ". " + (new Date().getMonth() + 1) + ". " + new Date().getFullYear()), "the facts carry the date they were read");
  assert.equal(await page.locator('section.datacite-read a[href="https://commons.datacite.org/repositories/gesis.csda"]').count(), 1, "the entry links its DataCite Commons page");
  assert.equal(await page.locator('section.datacite-read a[href="https://metadata.datacite.org/gesis.csda"]').count(), 1, "the entry links its Metadata Dashboard");
  assert.deepEqual(requests.map((url) => new URL(url).pathname), ["/clients/gesis.csda", "/dois"], "the snapshot's reviewed DataCite ID is used, then its DOIs are counted");
  assert.equal(await page.locator('.relations a[href*="10.17616"]').count(), 0, "the re3data record's DOI is not shown as the repository's own identifier");
  await accessible("the finder's DataCite facts are accessible");

  requests.length = 0;
  await visit("#/en/K/catalogue/repo/gen/zenodo", ".catalogue-results .entry-card .datacite-read button");
  await page.locator(".datacite-read button").click();
  await page.waitForSelector("section.datacite-read");
  assert.equal(new URL(requests[0]).pathname, "/clients/cern.zenodo", "a reviewed DataCite ID is asked for directly");
  assert((await page.locator("section.datacite-read").innerText()).includes("According to DataCite, read on"));

  await visit("#/cs/K/catalogue/repo/dom/lindat-clariah-cz", ".catalogue-results .entry-card");
  assert.equal(await page.locator(".datacite-read").count(), 0, "an entry absent from the DataCite snapshot offers no lookup");

  await visit("#/cs/K/catalogue/repo/inst/eli-eric-open-data", ".catalogue-results .entry-card");
  assert.equal(await page.locator(".datacite-read").count(), 0, "an entry with no way to DataCite offers no DataCite lookup");

  /* ------------------------------------------------ the maturity check's sample */
  requests.length = 0;
  await visit("#/cs/SR/check/maturity", "#main h1");
  await page.waitForSelector("#prefill-datacite-sample");
  assert(await page.locator("#prefill-datacite-sample").isDisabled(), "no repository, no draw");
  const reason = page.locator("#prefill-datacite-sample + .control-reason");
  assert(await reason.isVisible() && (await reason.textContent()).includes("re3data"), "the inactive draw says what it waits for");
  await page.evaluate(() => { window.FairGuide.live.findFairsharing = async () => []; });
  await page.fill("#prefill-re3data", "r3d100010484");
  await page.locator("#prefill-re3data-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  requests.length = 0;
  await page.locator("#prefill-datacite-sample").click();
  await page.waitForSelector(".datacite-sample li");
  assert.equal(await page.locator(".datacite-sample li").count(), 5);
  assert.equal(await page.locator("#prefill-champion").inputValue(), [1, 2, 3, 4, 5].map((n) => `10.14473/fixture${n}`).join("\n"), "the drawn DOIs fill the sample field");
  const listed = await page.locator("#datacite-sample").innerText();
  assert(listed.includes("Survey 1") && listed.includes("Testy zatím neběžely") && listed.includes("Czech Social Science Data Archive"), listed);
  assert.equal(await page.locator('#datacite-sample img').count(), 0, "a title is text, never markup");
  assert(requests.every((url) => url.startsWith("https://api.datacite.org/")), "drawing a sample runs no test: " + requests.join(", "));

  await page.locator(".datacite-sample li").nth(2).getByRole("button").click();
  await page.waitForFunction(() => document.getElementById("prefill-champion").value.includes("fixture7"));
  assert.equal((await page.locator("#prefill-champion").inputValue()).split("\n")[2], "10.14473/fixture7", "a replaced record keeps its place");
  assert(!(await page.locator("#prefill-champion").inputValue()).includes("fixture3"));
  assert.equal(await page.evaluate(() => document.activeElement.id), "datacite-replace-10-14473-fixture7", "focus moves to the new record");

  await page.fill("#prefill-champion", "10.14473/fixture1\n10.14473/fixture7\n10.5555/typed");
  await page.locator("#prefill-champion").dispatchEvent("input");
  await page.locator("#prefill-datacite-sample").focus();
  await page.evaluate(() => window.FairGuide.rerender());
  await page.waitForSelector(".datacite-sample li");
  assert.equal(await page.locator(".datacite-sample li").count(), 2, "records removed by hand leave the list; typed ones stay in the field");
  await accessible("the drawn sample is accessible");
  assert(requests.every((url) => url.startsWith("https://api.datacite.org/")), "only DataCite was asked: " + requests.join(", "));
  assert.deepEqual(problems, []);
  console.log("check_datacite: finder facts on request with date and links, absent and routeless entries, sample drawn after the repository is known, listed before any test, replaced in place, editable by hand: pass");
} finally {
  await browser.close();
}
