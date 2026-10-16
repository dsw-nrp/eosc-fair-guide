// Local embedding: exact origins/windows, bounded messages, content height and shareable host routes.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { resolve, sep } from "node:path";
import { audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
const site = resolve(root, "_site");
const { chromium } = await import("./browser.mjs");
const mime = { ".js": "text/javascript", ".css": "text/css", ".html": "text/html", ".svg": "image/svg+xml", ".json": "application/json" };
let hostOrigin;
let guideOrigin;
function serve(request, response) {
  const address = new URL(request.url, "http://localhost");
  if (address.pathname === "/host") {
    response.setHeader("Content-Type", "text/html");
    response.end(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Local embed test</title></head><body style="margin:0"><h1>Host</h1>
      <iframe id="guide" title="FAIR Guide" src="${guideOrigin}/#/cs/DS/path/start" style="width:100%;height:800px;border:0"></iframe>
      <script src="${guideOrigin}/assets/js/embed.js" data-guide-frame="guide" defer></script></body></html>`);
    return;
  }
  const path = resolve(site, "." + decodeURIComponent(address.pathname === "/" ? "/index.html" : address.pathname));
  if (!path.startsWith(site + sep)) { response.writeHead(403).end(); return; }
  try {
    let body = readFileSync(path);
    if (path.endsWith("index.html")) body = Buffer.from(body.toString().replace('data-parent-origins="self ', `data-parent-origins="${hostOrigin} self `));
    response.setHeader("Content-Type", mime[path.slice(path.lastIndexOf("."))] || "application/octet-stream");
    response.end(body);
  } catch { response.writeHead(404).end(); }
}
async function start() {
  const server = createServer(serve);
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  return { server, origin: `http://127.0.0.1:${server.address().port}` };
}
const guideServer = await start();
guideOrigin = guideServer.origin;
const hostServer = await start();
hostOrigin = hostServer.origin;
const foreign = await start();
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();
const problems = [];
page.on("pageerror", (error) => problems.push(error.message));
const frame = () => page.frames().find((entry) => entry.url().startsWith(guideOrigin + "/"));
const hostView = () => new URL(page.url()).searchParams.get("fair-guide-view");
async function mirrored(view) {
  await page.waitForFunction((expected) => new URL(location.href).searchParams.get("fair-guide-view") === expected, view);
}
async function fits() {
  await page.waitForFunction(() => parseInt(document.getElementById("guide").style.height, 10) !== 800);
  await frame().waitForFunction(() => document.documentElement.scrollHeight <= innerHeight + 2);
}
async function navigate(view) {
  await frame().evaluate((value) => window.FairGuide.navigate(value), view);
  await mirrored(view);
  await fits();
}
try {
  const initial = "#/cs/DS/path/licence";
  await page.goto(hostOrigin + "/host?keep=yes&fair-guide-view=" + encodeURIComponent(initial) + "#host-anchor");
  await page.frameLocator("#guide").locator('#main details[data-key="L1"]').waitFor();
  await fits();
  assert.equal(await frame().evaluate(() => location.hash), initial, "a shared host address opens the saved station");
  assert.equal(new URL(page.url()).searchParams.get("keep"), "yes");
  assert.equal(new URL(page.url()).hash, "#host-anchor");
  const before = await page.locator("#guide").evaluate((node) => node.getBoundingClientRect().height);
  await frame().locator('#main details[data-key="L1"] > summary').click();
  await page.waitForFunction((height) => parseInt(document.getElementById("guide").style.height, 10) > height, before);
  await fits();
  const expanded = await page.locator("#guide").evaluate((node) => node.getBoundingClientRect().height);
  await frame().locator('#main details[data-key="L1"] > summary').click();
  await page.waitForFunction((height) => parseInt(document.getElementById("guide").style.height, 10) < height, expanded);
  await fits();
  for (const width of [1280, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    for (const view of ["#/en/SR/path/metadata", "#/cs/K/path/start", "#/cs/DS/check/dataset/report"]) {
      await navigate(view);
      await frame().waitForFunction(() => document.querySelector("#main h1") && !document.querySelector(".data-load-error"));
      assert(await frame().evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${width}: frame reflow`);
    }
  }
  const shared = page.url();
  await page.reload();
  await page.frameLocator("#guide").locator('.check-parts [aria-current="step"][href$="/report"]').waitFor();
  await fits();
  assert.equal(page.url(), shared, "reload preserves the host URL");
  const previous = "#/en/DS/path/plan";
  await page.evaluate((view) => {
    const url = new URL(location.href); url.searchParams.set("fair-guide-view", view);
    history.pushState(null, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, previous);
  await frame().waitForFunction((view) => location.hash === view, previous);
  await page.goBack();
  await frame().waitForFunction(() => location.hash.endsWith("/check/dataset/report"));
  await fits();
  const result = await audit(page);
  assert.deepEqual(result.violations.map((entry) => entry.id), [], "embedded view accessibility");

  // Valid shape from a different sending window is rejected even on the admitted Guide origin.
  const current = hostView();
  await page.evaluate((origin) => {
    const other = document.createElement("iframe"); other.id = "other"; other.src = origin + "/"; document.body.append(other);
  }, guideOrigin);
  await page.frameLocator("#other").locator("#main h1").waitFor();
  await page.frames().find((entry) => entry !== frame() && entry.url() === guideOrigin + "/").evaluate((origin) => parent.postMessage({ type: "fair-guide:state", version: 1, height: 999, view: "#/en/V/path/plan" }, origin), hostOrigin);
  await page.waitForTimeout(100);
  assert.equal(hostView(), current, "another iframe cannot impersonate the selected frame");
  await page.locator("#other").evaluate((node) => node.remove());
  for (const data of [
    { type: "fair-guide:state", version: 2, height: 999, view: "#/en/V/path/plan" },
    { type: "fair-guide:state", version: 1, height: -1, view: "#/en/V/path/plan" },
    { type: "fair-guide:state", version: 1, height: 999, view: "javascript:alert(1)" },
  ]) {
    await frame().evaluate(([message, origin]) => parent.postMessage(message, origin), [data, hostOrigin]);
    await page.waitForTimeout(50);
    assert.equal(hostView(), current, "invalid state has no effect");
  }
  // An unconfigured parent origin cannot handshake or read any state, despite loading the host snippet.
  await page.goto(foreign.origin + "/host?fair-guide-view=" + encodeURIComponent(initial));
  await page.frameLocator("#guide").locator('#main details[data-key="L1"]').waitFor();
  await frame().evaluate(() => window.FairGuide.navigate("#/en/V/path/plan"));
  await frame().locator('#main details[data-key="L1"]').waitFor();
  await page.waitForTimeout(150);
  assert.equal(hostView(), initial, "foreign parent receives no view updates");
  assert.equal(await page.locator("#guide").evaluate((node) => node.style.height), "800px", "foreign parent receives no height updates");
  assert.deepEqual(problems, [], "no page errors");
  console.log("check_embed: cross-origin local host, share/reload, resize/shrink, languages/roles, accessibility and rejected messages passed");
} finally {
  await browser.close();
  await Promise.all([guideServer, hostServer, foreign].map(({ server }) => new Promise((done) => server.close(done))));
}
