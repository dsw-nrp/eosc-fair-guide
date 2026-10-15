// Published checksum vectors and browser checks of identifier extraction, privacy and honest lookup outcomes.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { runInNewContext } from "node:vm";
import { audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const { chromium } = await import("playwright");
const config = { api: { records: {} }, helpers: { maxCharacters: 100000, maxItems: 40 }, links: { fipDashboard: "https://fip-dashboard.dmp.eosc.cz/", nkr: "https://nkr.example/" } };
const FG = { config, list: (value) => value == null ? [] : Array.isArray(value) ? value : [value], graph: [], get: () => null, refs: () => [] };
for (const script of ["live.js", "helpers.js", "search.js"]) runInNewContext(readFileSync(resolve(root, "assets/js", script), "utf8"), { window: { FairGuide: FG }, URL });
const H = FG.helpers;
const plain = (value) => JSON.parse(JSON.stringify(value)); // values from the script context, compared by content
// One owner recognises ORCID iDs and re3data records; search, the identifier helper and the checks agree with it.
const orcids = [["0000-0002-1825-0097", "0000-0002-1825-0097"], ["https://orcid.org/0000-0002-1825-0097", "0000-0002-1825-0097"],
  ["http://orcid.org/0000-0002-1825-0097/", "0000-0002-1825-0097"], ["orcid.org/0000-0002-1694-233x", "0000-0002-1694-233X"],
  ["https://www.orcid.org/0000-0002-1694-233X", "0000-0002-1694-233X"]];
for (const [input, canonical] of orcids) {
  assert.equal(FG.live.parseOrcid(input), canonical, input);
  assert.deepEqual(plain(FG.search.classify(input)), { type: "orcid", value: canonical }, "search: " + input);
  assert.deepEqual(plain(H.extract(input).items.map((item) => [item.type, item.value])), [["orcid", canonical]], "helper: " + input);
}
for (const input of ["0000-0002-1825-00970", "00000002-1825-0097", "x0000-0002-1825-0097", "https://orcid.org.evil.example/0000-0002-1825-0097",
  "https://evil.example/orcid.org/0000-0002-1825-0097", "https://orcid.org/0000-0002-1825-0097/works", "0000-0002-1825-009"]) {
  assert.equal(FG.live.parseOrcid(input), null, input);
  assert.notEqual(FG.search.classify(input).type, "orcid", "search: " + input);
  assert(!H.extract(input).items.some((item) => item.type === "orcid"), "helper: " + input);
}
const records = [["r3d100010468", "r3d100010468"], ["R3D100010468", "r3d100010468"], ["https://www.re3data.org/repository/r3d100010468", "r3d100010468"],
  ["re3data.org/repository/r3d100010468/", "r3d100010468"], ["http://re3data.org/repository/r3d100010468?view=1", "r3d100010468"]];
const resolvePid = FG.live.resolvePid;
FG.live.resolvePid = async (pid) => {
  if (pid.value.includes("unreachable")) throw Error("resolver unavailable");
  return { found: true, url: pid.value.startsWith("10.17616/") ? "https://www.re3data.org/repository/r3d100010468" : "https://evil.example/repository/r3d100010468" };
};
for (const [input, canonical] of records) {
  assert.equal(FG.live.parseRe3data(input), canonical, input);
  assert.deepEqual(plain(FG.search.classify(input)), { type: "re3data", value: canonical }, "search: " + input);
  assert.equal(await FG.live.re3dataRecord(input), canonical, "check: " + input);
}
for (const input of ["r3d10001046", "r3d1000104680", "xr3d100010468", "see r3d100010468", "https://evil.example/repository/r3d100010468",
  "https://www.re3data.org/search?query=r3d100010468", "10.1234/elsewhere", "10.17616/unreachable"]) {
  assert.equal(FG.live.parseRe3data(input), null, input);
  assert.equal(await FG.live.re3dataRecord(input), null, "check: " + input);
}
assert.deepEqual(plain(FG.search.classify("10.17616/R3D1D0")), { type: "re3data", value: "10.17616/R3D1D0" }, "a re3data DOI routes to the maturity check");
assert.equal(await FG.live.re3dataRecord("https://doi.org/10.17616/R3D1D0"), "r3d100010468", "the check follows a re3data DOI to its record");
assert.notEqual(FG.search.classify("xr3d100010468").type, "re3data");
FG.live.resolvePid = resolvePid;
// Reviewed discovery looks connectors up through the live owner rather than its own copy.
const ownConnector = FG.live.connector, looked = [];
FG.live.connector = (id) => { looked.push(id); throw Error("looked up by the shared owner"); };
runInNewContext(readFileSync(resolve(root, "assets/js/discovery.js"), "utf8"), { window: { FairGuide: FG }, URL });
await assert.rejects(FG.live.readPublic("datacite", "dois/x", { maxBytes: 10 }), /looked up by the shared owner/);
assert.deepEqual(plain(looked), ["datacite"]);
FG.live.connector = ownConnector;
// Examples published in ORCID's identifier documentation and the ROR identifier-pattern documentation.
for (const id of ["0000-0002-1825-0097", "0000-0001-5109-3700", "0000-0002-1694-233X"]) assert(H.validOrcid(id));
for (const id of ["02mhbdp94", "000000098"]) assert(H.validRor(id));
assert(!H.validOrcid("0000-0002-1825-0098"));
assert(!H.validOrcid("0000000218250097"));
assert(!H.validRor("02mhbdp93"));
assert(!H.validRor("02mibdp94"));
for (let n = 0; n < 15; n++) {
  const digits = "0000000218250097".split("");
  digits[n] = String((Number(digits[n]) + 1) % 10);
  assert(!H.validOrcid(digits.join("").match(/.{4}/g).join("-")), "single-digit transcription errors are caught");
}
const extracted = H.extract('ORCID https://orcid.org/0000-0002-1694-233x. ROR 02mhbdp94; doi:10.1234/a(b). https://doi.org/10.1234/A%28b%29 hdl:11234/1-456, 0000-0002-1825-0098');
assert.equal(extracted.items.length, 5);
assert.equal(extracted.items[2].value, "10.1234/a(b)");
assert.equal(extracted.items[4].checksum, false);
assert.equal(H.extract("https://orcid.org.evil.example/0000-0002-1825-0097 /0000-0002-1825-0097 0000-0002-1825-00970").items.length, 0);
assert.equal(H.extract("https://archive.example/11234/1-456").items.length, 0, "arbitrary URLs are not sent to a resolver");
assert.equal(H.extract("hdl:11234/A hdl:11234/a").items.length, 2, "explicit Handle suffix case is retained");
assert.equal(H.extract("Date 2026/10, fraction 1/2, path 11234/filename, version 4.2/readme.").items.length, 0, "unlabelled numeric paths and fractions are not guessed to be Handles");
assert.equal(H.extract("https://doi.org/10.1234/a%252Fb").items[0].value, "10.1234/a%2Fb", "resolver paths decode exactly once");
assert.equal(H.extract("https://doi.org/10.1234/a/").items[0].value, "10.1234/a/", "significant PID suffix slashes remain");
assert(H.extract("x".repeat(100001)).textLimit);
const many = Array.from({ length: 41 }, (_, n) => "10.1234/record-" + n).join(" ");
assert.equal(H.extract(many).items.length, 40);
assert(H.extract(many).itemLimit);
let called = 0;
FG.live.orcidName = async () => { called++; return "Someone else"; };
assert.equal((await H.resolveIdentifier(extracted.items[4])).status, "invalid");
assert.equal(called, 0, "invalid checksums never reach a connector");
FG.live.rorName = async () => { throw Error("service unavailable"); };
assert.equal((await H.resolveIdentifier({ type: "ror", value: "02mhbdp94" })).status, "unavailable");
FG.live.resolvePid = async () => ({ found: true, url: "https://archive.example/record" });
FG.live.datacite = async () => { throw Error("metadata unavailable"); };
FG.live.crossref = async () => null;
const partial = await H.resolveIdentifier({ type: "doi", value: "10.1234/record" });
assert.equal(partial.status, "found", "missing metadata do not undo successful resolution");
assert.equal(partial.title, null);
assert(partial.metadataUnavailable);
FG.live.datacite = async () => ({ doi: "10.1234/other", titles: [{ title: "Wrong DataCite title" }] });
FG.live.crossref = async () => ({ DOI: "10.1234/other", title: ["Wrong Crossref title"] });
assert.equal((await H.resolveIdentifier({ type: "doi", value: "10.1234/record" })).title, null, "titles from different DOI records are not attributed to the requested object");

const browser = await chromium.launch();
const context = await browser.newContext();
const page = await context.newPage();
const base = pathToFileURL(resolve(root, "_site/index.html")).href;
const screenshots = resolve(root, ".cache/screenshots/helpers");
mkdirSync(screenshots, { recursive: true });
const external = [], local = [];
let active = 0, peak = 0, rorAttempts = 0, releaseDiscarded;
page.on("request", (request) => { if (request.url().startsWith("file:")) local.push(request.url()); });
await page.route(/^https?:/, async (route) => {
  const url = route.request().url();
  external.push(url);
  active++; peak = Math.max(peak, active);
  try {
    await new Promise((done) => setTimeout(done, 30));
    if (url.includes("/api/handles/") && url.includes("discarded")) await new Promise((done) => { releaseDiscarded = done; });
    let body, status = 200;
    if (url.startsWith("https://pub.orcid.org/")) body = { name: { "credit-name": { value: "A different researcher" } } };
    else if (url.startsWith("https://api.ror.org/")) {
      rorAttempts++;
      if (rorAttempts === 1) { status = 503; body = { error: "temporary" }; }
      else { status = 404; body = { error: "missing" }; }
    } else if (url.includes("/api/handles/")) body = { responseCode: url.includes("missing") ? 100 : 1,
      values: [{ type: "URL", data: { value: "https://archive.example/record" } }, ...(url.includes("11234") ? [{ type: "TITLE", data: { value: "Handle record title" } }] : [])] };
    else if (url.startsWith("https://api.datacite.org/")) {
      const doi = decodeURIComponent(new URL(url).pathname.slice("/dois/".length));
      if (doi.includes("crossref")) { status = 404; body = {}; }
      else body = { data: { attributes: { doi, titles: [{ title: '<img src="https://evil.example/payload">A dataset title' }] } } };
    } else if (url.startsWith("https://api.crossref.org/")) body = { status: "ok", message: { DOI: decodeURIComponent(new URL(url).pathname.slice("/works/".length)), title: ["Crossref article title"] } };
    else throw Error("unexpected external request: " + url);
    await route.fulfill({ status, headers: { "access-control-allow-origin": "*" }, contentType: "application/json", body: JSON.stringify(body) });
  } finally { active--; }
});
async function visit(hash) {
  await page.goto(base + hash);
  await page.waitForFunction(() => window.FairGuide && window.FairGuide.parseHash(location.hash).view === "page" ? Boolean(document.querySelector(".identifier-helper")) : Boolean(document.querySelector("#search-input")));
}
try {
  await visit("#/cs/V/path/start");
  assert(!local.some((url) => url.endsWith("helpers.js")), "helper code is absent from the initial download");
  await page.locator("#search-input").fill("0000-0002-1825-0097");
  await page.locator("#search-input").press("Enter");
  await page.locator('#search-results a[href*="/page/identifiers/"]').click();
  await page.waitForSelector("#identifier-text");
  assert.equal(await page.locator("#identifier-text").inputValue(), "0000-0002-1825-0097", "search hands over the selected identifier");
  assert.equal(external.length, 0);
  await page.locator("#identifier-text").fill("Private context: 0000-0002-1825-0097 0000-0002-1825-0098 02mhbdp94 10.1234/one hdl:11234/1-456 10.1234/missing 10.9876/crossref");
  await page.locator('.identifier-helper button[type="submit"]').click();
  assert.equal(await page.locator(".identifier-list > li").count(), 7);
  assert.equal(external.length, 0, "scanning pasted text sends nothing");
  assert(!(await page.evaluate(() => JSON.stringify(localStorage))).includes("Private context"), "pasted text is not saved");
  const offline = await audit(page);
  assert.deepEqual(offline.violations, []);
  await page.locator('.identifier-helper button', { hasText: "Načíst nalezené záznamy" }).click();
  await page.waitForFunction(() => !document.querySelector('.identifier-list > li[data-status="running"], .identifier-list > li[data-status="queued"]'));
  const rows = page.locator(".identifier-list > li");
  assert((await rows.nth(0).innerText()).includes("A different researcher"));
  assert(await rows.nth(1).locator("button").isDisabled());
  assert((await rows.nth(2).innerText()).includes("neznamená to"));
  assert((await rows.nth(3).innerText()).includes("<img"));
  assert.equal(await rows.nth(3).locator("img").count(), 0, "external titles remain inert text");
  assert((await rows.nth(4).innerText()).includes("Handle record title"));
  assert((await rows.nth(5).innerText()).includes("nerozpoznala"));
  assert((await rows.nth(6).innerText()).includes("Crossref article title"));
  assert(!external.some((url) => url.includes("Private") || url.includes("0098") || url.includes("evil.example")));
  assert(peak <= 4, "all lookups share a four-request ceiling");
  await rows.nth(2).locator("button").click();
  await page.waitForFunction(() => document.querySelectorAll(".identifier-list > li")[2].textContent.includes("nerozpoznala"));
  assert.equal(rorAttempts, 2, "service failures retry only after an explicit click");
  await page.locator('.identifier-helper .field-clear').click();
  assert.equal(await page.locator("#identifier-text").inputValue(), "");
  assert.equal(await page.locator(".identifier-list > li").count(), 0);
  assert.equal(await page.locator("#identifier-summary").innerText(), "");
  assert.equal(await page.evaluate(() => location.hash), "#/cs/V/page/identifiers", "reset removes the seeded identifier from the URL");
  await page.evaluate(() => {
    const H = window.FairGuide.helpers, resolve = H.resolveIdentifier;
    H.resolveIdentifier = (...args) => resolve(...args).finally(() => { window.discardedLookupCompleted = true; });
  });
  await page.locator("#identifier-text").fill("10.1234/discarded");
  await page.locator('.identifier-helper button[type="submit"]').click();
  await page.locator('.identifier-list button').click();
  for (let attempt = 0; !releaseDiscarded && attempt < 100; attempt++) await new Promise((done) => setTimeout(done, 10));
  assert(releaseDiscarded, "the reset is exercised while a lookup is pending");
  await page.locator('.identifier-helper .field-clear').click();
  releaseDiscarded();
  await page.waitForFunction(() => window.discardedLookupCompleted);
  assert.equal(await page.locator(".identifier-list > li").count(), 0, "discarded responses do not restore cleared results");
  assert.equal(await page.locator("#identifier-summary").innerText(), "");
  for (const lang of ["cs", "en"]) {
    await visit(`#/${lang}/V/page/identifiers`);
    await page.locator("#identifier-text").fill("0000-0002-1825-0097 0000-0002-1825-0098 10.1234/one");
    await page.locator('.identifier-helper button[type="submit"]').click();
    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await page.locator(".identifier-list").scrollIntoViewIfNeeded();
      await page.screenshot({ path: resolve(screenshots, `${lang}-identifier-local-${width}.png`) });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    }
    await page.locator('.identifier-helper .buttons button[type="button"]').click();
    await page.waitForFunction(() => !document.querySelector('.identifier-list > li[data-status="running"], .identifier-list > li[data-status="queued"]'));
    const access = await audit(page);
    assert.deepEqual(access.violations, []);
    await page.screenshot({ path: resolve(screenshots, `${lang}-identifier-resolved-320.png`) });
  }
  console.log("check_helpers: published checksum vectors, extraction limits, search handoff, local privacy, bounded lookups, failure/retry, safe titles and bilingual accessibility/reflow pass");
} finally { await browser.close(); }
