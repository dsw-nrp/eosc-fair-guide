// A mixed static deployment never changes accepted data or the reader's answers and offers usable recovery.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "./browser.mjs";

const site = resolve(import.meta.dirname, "../../_site");
const file = pathToFileURL(resolve(site, "index.html")).href;
const artifacts = resolve(import.meta.dirname, "../../.cache/revision-visuals");
mkdirSync(artifacts, { recursive: true });
const revision = readFileSync(resolve(site, "assets/data/kb.js"), "utf8").match(/FairGuideData\.revision = "([^"]+)"/)[1];
const browser = await chromium.launch();

async function presentation(page, frame, name, initial = false) {
  const error = frame.locator(".data-load-error");
  const bounds = await error.boundingBox();
  assert(bounds.y >= 0 && bounds.y + bounds.height <= page.viewportSize().height, "recovery stays in the viewport");
  assert.equal(await error.locator('[lang="cs"]').count(), initial ? 2 : 3);
  assert.equal(await error.locator('[lang="en"]').count(), initial ? 2 : 3);
  const boxes = await error.locator("button").evaluateAll((buttons) => buttons.map((button) => {
    const r = button.getBoundingClientRect(); return { x: r.x, y: r.y, right: r.right, bottom: r.bottom, height: r.height };
  }));
  assert(boxes.every((box) => box.height >= 44), "recovery actions retain touch targets");
  assert.equal(boxes.length, initial ? 1 : 2, "startup offers only Reload; deferred failure also offers Retry");
  if (!initial) assert(boxes[1].x - boxes[0].right >= 4 || boxes[1].y - boxes[0].bottom >= 4, "recovery actions keep a gap");
  assert(await frame.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "recovery reflows");
  await page.screenshot({ path: resolve(artifacts, name + ".png") });
  if (name.includes("http") && name.endsWith("320")) {
    await page.emulateMedia({ media: "print" });
    await page.screenshot({ path: resolve(artifacts, name + "-print.png") });
    await page.emulateMedia({ media: "screen" });
  }
}

try {
  for (const lang of ["cs", "en"]) for (const width of [1280, 320]) for (const mode of ["http", "file", "iframe"]) {
    const context = await browser.newContext({ viewport: { width, height: 900 } }), page = await context.newPage();
    const requests = [], errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    let stale = true;
    const target = `/assets/data/kb-questions-${lang}.js`;
    await context.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (!url.pathname.includes("/assets/") && url.protocol === "file:") return route.continue();
      const path = url.pathname.slice(url.pathname.indexOf("/assets/"));
      const relative = path.startsWith("/assets/") ? path : url.pathname;
      requests.push({ path: relative, version: url.searchParams.get("v"), protocol: url.protocol });
      const source = readFileSync(resolve(site, "." + relative));
      const body = stale && relative === target ? source.toString().replaceAll(revision, "older-build") : source;
      await route.fulfill({ body, contentType: relative.endsWith(".js") ? "text/javascript" : relative.endsWith(".css") ? "text/css" : relative.endsWith(".svg") ? "image/svg+xml" : "text/html" });
    });
    const base = mode === "http" ? "https://guide-revision.test/index.html" : file;
    await page.goto(base + `#/${lang}/K/path/start`);
    let frame = page;
    if (mode === "iframe") {
      await page.setContent(`<iframe title="Guide" width="${width - 20}" height="850" src="${file}#/${lang}/K/path/start"></iframe>`);
      frame = page.frames().find((candidate) => candidate !== page.mainFrame());
    }
    await frame.locator("#search-input").waitFor();
    // Focus already preloads the search data; this text must survive the later questions failure.
    await frame.locator("#search-input").fill("keep my input");
    await frame.evaluate(({ lang }) => {
      const FG = window.FairGuide;
      FG.state.answers.gate = { profile: "independent", items: { "gate.13": { value: "no", origin: "user" } } };
      FG.saveState(); FG.navigate(`#/${lang}/K/check/gate/evidence`);
    }, { lang });
    await frame.locator(".data-load-error").waitFor();
    assert.equal(await frame.locator("#search-input").inputValue(), "keep my input");
    assert.equal(await frame.evaluate(() => window.FairGuide.partsLoaded.has("questions")), false);
    assert.equal(await frame.evaluate(() => window.FairGuide.config.providers), undefined);
    assert.equal(await frame.evaluate(() => window.FairGuide.state.answers.gate.items["gate.13"].value), "no");
    await presentation(page, frame, `${lang}-${mode}-${width}`);
    stale = false;
    await frame.locator(".data-load-error button").first().click();
    await frame.locator(".check-evidence").waitFor();
    assert.equal(await frame.locator(".data-load-error").count(), 0);
    assert.equal(await frame.evaluate(() => window.FairGuide.state.answers.gate.items["gate.13"].value), "no");
    assert(await frame.evaluate(() => Boolean(window.FairGuide.config.providers.list.length && window.FairGuide.config.champion.endpoint)));
    assert.equal(requests.filter((request) => request.path === target).length, 2);
    assert(requests.filter((request) => request.path.endsWith(".js")).every((request) => request.version === revision));
    if (mode !== "http") assert(requests.every((request) => request.protocol === "file:"));
    assert.deepEqual(errors, []);
    await context.close();
  }
  // Exercise all four loaders with real configured query-bearing module paths, without contacting a service.
  for (const lang of ["cs", "en"]) {
    const context = await browser.newContext(), page = await context.newPage(), scripts = [], errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await context.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.origin !== "https://guide-script-query.test") return route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
      if (url.pathname.endsWith(".js")) scripts.push(url);
      let body = readFileSync(resolve(site, "." + url.pathname));
      if (url.pathname.startsWith("/assets/data/")) body = body.toString().replace(/(assets\/(?:js|data)\/[^"?]+\.js)(?=")/g, "$1?fixture=a%3Fb");
      await route.fulfill({ body, contentType: url.pathname.endsWith(".js") ? "text/javascript" : url.pathname.endsWith(".css") ? "text/css" : "text/html" });
    });
    await page.goto(`https://guide-script-query.test/index.html#/${lang}/V/check/software/evidence`);
    await page.locator("#prefill-software").fill("https://github.com/example/repository");
    await page.locator("#prefill-software-run").click();
    await page.waitForFunction(() => Boolean(window.FairGuide.live && window.FairGuide.selfcheck.assessSoftware));
    await page.waitForFunction(() => [...document.scripts].some((script) => script.src.includes("/assets/js/discovery.js")));
    await page.waitForFunction(() => !document.querySelector("#prefill-software-run").disabled);
    for (const module of ["selfcheck.js", "inspection.js", "assess.js", "tests/object.js", "tests/software.js", "discovery.js"]) {
      const found = scripts.filter((url) => url.pathname === "/assets/js/" + module);
      assert.equal(found.length, 1, module + " loads once");
      assert.equal(found[0].searchParams.get("fixture"), "a?b", module + " retains its query");
      assert.deepEqual(found[0].searchParams.getAll("v"), [revision], module + " has one current revision");
    }
    assert.deepEqual(errors, []);
    await context.close();
  }
  for (const mode of ["http", "file", "iframe"]) for (const failure of (mode === "http" ? ["stale", "stale-pair", "absent", "absent-document"] : ["stale-pair"])) for (const lang of ["cs", "en"]) for (const width of (mode === "http" ? [1280, 320] : [320])) {
    const context = await browser.newContext({ viewport: { width, height: 900 } }), page = await context.newPage();
    let stale = true;
    await context.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.includes("/assets/") ? url.pathname.slice(url.pathname.indexOf("/assets/")) : "/index.html";
      let body = readFileSync(resolve(site, "." + path));
      if (stale && failure.startsWith("stale") && path === "/assets/data/kb.js") body = body.toString().replaceAll(revision, "older-build");
      if (stale && failure === "stale-pair" && path === "/assets/data/ui.js") body = body.toString().replaceAll(revision, "older-build");
      if (stale && failure === "absent" && ["/assets/data/kb.js", "/assets/data/ui.js"].includes(path)) body = "/* initial data absent */";
      if (stale && failure === "absent-document" && path === "/index.html") body = body.toString().replace(/ data-revision="[^"]+"/, "");
      await route.fulfill({ body, contentType: path.endsWith(".js") ? "text/javascript" : path.endsWith(".css") ? "text/css" : "text/html" });
    });
    await page.addInitScript(() => {
      if (!sessionStorage.getItem("revision-fixture-seeded")) {
        localStorage.setItem("eosc-fair-guide", JSON.stringify({ answers: { fixture: { retained: true } } }));
        sessionStorage.setItem("revision-fixture-seeded", "true");
      }
    });
    const base = mode === "http" ? "https://guide-initial.test/index.html" : file;
    await page.goto(`${base}#/${lang}/K/path/start`);
    let frame = page;
    if (mode === "iframe") {
      await page.setContent(`<iframe title="Guide" width="${width - 20}" height="850" src="${file}#/${lang}/K/path/start"></iframe>`);
      frame = page.frames().find((candidate) => candidate !== page.mainFrame());
    }
    await frame.locator(".data-load-error").waitFor();
    assert.equal(await frame.evaluate(() => window.FairGuide.graph), undefined);
    assert.equal(await frame.locator("#main > p").count(), 0, "initial failure retires the loading message");
    assert(await frame.evaluate(() => JSON.parse(localStorage.getItem("eosc-fair-guide")).answers.fixture.retained));
    await presentation(page, frame, `${lang}-initial-${failure}-${mode}-${width}`, true);
    stale = false;
    await frame.locator(".data-load-error button").click();
    await frame.locator("#search-input").waitFor();
    assert.equal(await frame.evaluate(() => window.FairGuide.state.answers.fixture.retained), true);
    await context.close();
  }
  console.log("revision checks: transactional acceptance, Retry/Reload, saved answers/input, file/HTTP/iframe and bilingual reflow passed");
} finally { await browser.close(); }
