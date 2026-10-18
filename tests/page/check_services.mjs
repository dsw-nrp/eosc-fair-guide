// Block each enrolled service at the network boundary and exercise its recovery in the real UI.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { resolve, extname, sep } from "node:path";
import { pathToFileURL } from "node:url";
const root = resolve(import.meta.dirname, "../..");
const { chromium } = await import("./browser.mjs");
const site = resolve(root, "_site");
const config = JSON.parse(readFileSync(resolve(site, "assets/data/ui.js"), "utf8").match(/^window\.FairGuideData\.ui = (.*);$/m)[1]).config;
const origins = new Map(config.connectors.map((entry) => [entry.id, entry.origin]));
const server = createServer((request, response) => {
  const path = resolve(site, "." + new URL(request.url, "http://localhost").pathname);
  if (!path.startsWith(site + sep)) { response.writeHead(403).end(); return; }
  try {
    response.setHeader("Content-Type", ({ ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml" })[extname(path)] || "application/octet-stream");
    response.end(readFileSync(path));
  } catch { response.writeHead(404).end(); }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const http = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch();
let blocked, attempted = [], errors = [];
const page = await browser.newPage();
page.on("pageerror", (error) => errors.push(error.message));
await page.route(/^https?:/, async (route) => {
  const url = new URL(route.request().url());
  if (url.origin === http) return route.continue();
  assert([...origins.values()].includes(url.origin), "unexpected external origin: " + url.origin);
  attempted.push(url.href);
  if (url.origin === blocked) return route.abort();
  let data, status = 200, type = "application/json";
  const doi = decodeURIComponent(url.pathname.match(/(?:ra|dois|works)\/(.+?)(?:\/transform\/|$)/)?.[1] || url.searchParams.get("doi") || "10.1234/record");
  if (url.pathname.includes("/ra/")) data = [{ RA: doi.includes("crossref") ? "Crossref" : "DataCite" }];
  else if (url.pathname.includes("/api/handles/")) data = { responseCode: 1, values: [{ type: "URL", data: { value: "https://zenodo.org/records/123" } }] };
  else if (url.origin === origins.get("datacite")) {
    if (doi.includes("crossref")) { status = 404; data = {}; }
    else data = { data: { attributes: { doi, titles: [{ title: "Dataset" }], types: { resourceTypeGeneral: "Dataset" } } } };
  } else if (url.origin === origins.get("crossref")) {
    if (doi.includes("crossref")) data = { status: "ok", message: { DOI: doi, title: ["Article"] } };
    else { status = 404; data = {}; }
  }
  else if (url.origin === origins.get("doi-citation")) {
    if (url.pathname === "/styles") data = ["apa", "iso690-author-date-cs"];
    else { type = "text/plain"; data = "Author. Citation. https://doi.org/" + doi; }
  } else if (url.origin === origins.get("datacite-content")) {
    const value = decodeURIComponent(url.pathname.split("/").slice(3).join("/"));
    if (url.pathname.includes("x-bibtex")) { type = "application/x-bibtex"; data = `@article{entry, doi={${value}}}`; }
    else { type = "application/x-research-info-systems"; data = `TY  - DATA\nDO  - ${value}\nER  -\n`; }
  } else if (url.origin === origins.get("public-object")) { type = "text/html"; data = "<html><title>Dataset</title></html>"; }
  else { status = 404; data = {}; }
  await route.fulfill({ status, contentType: type, headers: { "access-control-allow-origin": "*" }, body: typeof data === "string" ? data : JSON.stringify(data) });
});
const visit = async (base, lang, view) => {
  assert.deepEqual(errors, []);
  attempted = []; errors = [];
  await page.goto(base + `#/${lang}/V/${view}`);
  await page.waitForSelector("#main h1");
  if (view.startsWith("page/")) await page.waitForSelector(view.includes("citation") ? "#citation-doi" : "#identifier-text");
  else if (view.startsWith("check/")) await page.waitForSelector(".prefill");
  if (view === "check/dataset") await page.check("#mode-after");
  assert.equal(attempted.length, 0, "no external request on entry: " + view);
};
// A check's evidence (its pre-fill sources) and its answers are separate parts; answers persist across them.
const part = async (name) => {
  const [prefix] = page.url().match(/#\/[a-z]{2}\/[A-Z]+\/check\/[a-z-]+/);
  await page.evaluate((hash) => { window.location.hash = hash; }, prefix + "/" + name);
  await page.waitForSelector(`.check-parts [aria-current="step"][href$="/${name}"]`);
  if (name === "answers") await page.waitForSelector("#main .item");
};
const done = () => page.waitForFunction(() => {
  const text = document.querySelector("#prefill-status")?.textContent;
  return text && !/Načítám|Loading/.test(text);
});
try {
  for (const base of [pathToFileURL(resolve(site, "index.html")).href, http + "/index.html"]) {
    for (const lang of ["cs", "en"]) {
      for (const [connector, value] of [["doi", "10.1234/record"], ["handle", "hdl:11234/1-record"], ["orcid", "0000-0002-1825-0097"], ["ror", "02mhbdp94"], ["datacite", "10.1234/record"], ["crossref", "10.1234/crossref"]]) {
        blocked = origins.get(connector); await visit(base, lang, "page/identifiers");
        await page.fill("#identifier-text", value); await page.click('.identifier-helper button[type="submit"]');
        await page.click(".identifier-list button");
        await page.waitForFunction(() => !document.querySelector('.identifier-list [data-status="running"], .identifier-list > li[data-status="running"]'));
        const text = await page.locator(".identifier-list").innerText();
        assert(/nepodařilo|not be retrieved|není.*dostupn|unavailable|No name or title/.test(text), connector + ": " + text);
        assert(attempted.some((url) => url.startsWith(blocked + "/")), connector + " was exercised");
      }
      for (const [connector, value, count] of [["doi", "10.1234/record", 0], ["datacite", "10.1234/record", 0], ["crossref", "10.1234/crossref", 0], ["doi-citation", "10.1234/record", 2], ["datacite-content", "10.1234/record", 2]]) {
        blocked = origins.get(connector); await visit(base, lang, "page/citation");
        await page.fill("#citation-doi", value); await page.click('.citation-helper button[type="submit"]');
        await page.waitForFunction(() => !document.querySelector('.citation-helper button[type="submit"]').disabled);
        assert.equal(await page.locator(".citation-format pre").count(), count, "citation partial coverage: " + connector);
        assert(attempted.some((url) => url.startsWith(blocked + "/")));
      }
      for (const [connector, repo] of [["github-api", "https://github.com/example/tool"], ["gitlab-public", "https://gitlab.com/example/tool"]]) {
        blocked = origins.get(connector); await visit(base, lang, "check/software");
        await part("answers"); await page.check("#answer-software-01-yes"); await part("evidence");
        await page.fill("#prefill-software", repo); await page.click("#prefill-software-run"); await done();
        assert(await page.locator("#prefill-software-run").isEnabled());
        assert(/nepodařilo|could not|unavailable|nedostupn/i.test(await page.locator("#prefill-status").textContent()));
        assert(attempted.some((url) => url.startsWith(blocked + "/")));
        await part("answers");
        assert(await page.locator("#answer-software-01-yes").isChecked(), "manual answer survives " + connector);
      }
      // NKR enters as a reviewed snapshot: the repository check offers no on-demand load and asks NKR for nothing.
      blocked = origins.get("nkr"); await visit(base, lang, "check/maturity");
      assert.equal(await page.locator("#nkr-load").count(), 0, "the NKR snapshot offers no on-demand load");
      blocked = origins.get("nanopub"); await visit(base, lang, "check/fip");
      await page.fill("#prefill-nanopub", "RAhoyQ_s4N_K_yuZ6jeolF5L8u2y75dcISHS8UJ-MZ5fM");
      await page.click("#prefill-nanopub-run"); await done();
      assert(attempted.some((url) => url.startsWith(blocked + "/")));
      await part("answers");
      assert.equal(await page.locator(".item input[value='no']:checked").count(), 0);
      blocked = origins.get("fip-dashboard"); await visit(base, lang, "check/fip");
      await page.evaluate(() => { FairGuide.config.connectors.find((entry) => entry.id === "fip-dashboard").browserAccess = true; });
      await page.selectOption("#prefill-fip", "ndi-baseline"); await page.click("#prefill-fip-run"); await done();
      assert(attempted.some((url) => url.startsWith(blocked + "/")));
      await part("answers");
      assert(/snímek|snapshot/.test(await page.locator("#origin-fip-01").textContent()), "failed live Dashboard retains correctly attributed snapshot");
      blocked = origins.get("public-object"); await visit(base, lang, "check/fdo");
      await page.fill("#prefill-pid", "10.1234/record"); await page.click("#prefill-pid-run"); await done();
      assert(attempted.some((url) => url.startsWith(blocked + "/")), "landing fetch attempted");
      await part("answers");
      assert.equal(await page.locator(".item input[value='no']:checked").count(), 0, "unreadable landing page is not a failed requirement");
      blocked = origins.get("champion"); await visit(base, lang, "check/dataset");
      await page.fill("#prefill-pid", "10.1234/record"); await page.click("#prefill-pid-run"); await done();
      await page.click("#prefill-champion-run");
      await page.waitForFunction(() => Object.keys(FairGuide.state.answers.dataset?.champion?.verdicts || {}).length > 0);
      await page.waitForFunction(() => /tests gave a result|Výsledek dalo/.test(document.querySelector("#prefill-status").textContent));
      assert(attempted.some((url) => url.startsWith(blocked + "/")));
      await part("answers");
      assert.equal(await page.locator(".item input[value='no']:checked").count(), 0, "blocked Champion produces no failed answers");
      blocked = origins.get("dmp-status");
      const rejected = await page.evaluate(async () => { try { await FairGuide.live.dmpStatus(); return false; } catch { return true; } });
      assert(rejected, "non-UI status connector rejects failure without changing displayed content");
      const cspRefused = await page.evaluate(async () => { try { await fetch("https://outside.example/unreviewed"); return false; } catch { return true; } });
      assert(cspRefused, "standalone CSP refuses an unenrolled host before a network request");
      assert.deepEqual(errors, []);
    }
  }
  console.log("check_services: every enrolled host blocked, standalone/file and CS/EN recovery, manual answers, partial citation and accurate snapshot fallback pass");
} finally { await browser.close(); await new Promise((resolve) => server.close(resolve)); }
