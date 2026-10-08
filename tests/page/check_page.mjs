// Page checks for the FAIR data guide, run in Chromium with Playwright:
// - the page renders from a local file without any external request on load, console error or CSP violation;
// - every station renders in every lens and language, and so do the other views;
// - axe finds no WCAG 2.2 A or AA violation in any of those views;
// - the keyboard reaches the main controls, the page reflows at 320 px, and it works inside an iframe.
// Usage: npm run check:page   (set PLAYWRIGHT_BROWSERS_PATH if the browser lives outside the default cache)

import { chromium } from "playwright";
import { AxeBuilder } from "@axe-core/playwright";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const pageUrl = pathToFileURL(resolve(root, "index.html")).href;
const crate = JSON.parse(readFileSync(resolve(root, "ro-crate-metadata.json"), "utf8"));
const graph = crate["@graph"];
const stations = graph.filter((e) => e["@type"] === "HowToSection").map((e) => e.identifier);
const lenses = graph.filter((e) => e["@type"] === "Audience" && e["@id"].startsWith("#lens-")).map((e) => e.audienceType);
const pages = graph.filter((e) => String(e["@id"]).startsWith("#page-") && e.identifier).map((e) => e.identifier);
const principles = graph.filter((e) => String(e["@id"]).startsWith("https://w3id.org/fair/principles/terms/") && e.termCode).map((e) => e.termCode);
const failures = [];
const fail = (message) => failures.push(message);

const browser = await chromium.launch();

async function openPage(viewport) {
  const context = await browser.newContext({ viewport: viewport || { width: 1280, height: 900 } });
  const page = await context.newPage();
  const external = [];
  const problems = [];
  const state = { axeRunning: false };
  page.on("request", (request) => {
    const url = request.url();
    if (!url.startsWith("file:") && !url.startsWith("data:")) external.push(url);
  });
  page.on("console", (message) => {
    // axe fetches stylesheets to inspect them; the page's own CSP blocks that, which is the page working.
    if (message.type() === "error" && !state.axeRunning) problems.push("console: " + message.text());
  });
  page.on("pageerror", (error) => problems.push("page error: " + error.message));
  page.axeState = state;
  return { context, page, external, problems };
}

async function rendered(page) {
  await page.waitForFunction(() => { const h1 = document.querySelector("#main h1"); return h1 && h1.textContent.trim() && !document.body.textContent.includes("The guide is loading."); });
}

async function axe(page, label) {
  page.axeState.axeRunning = true;
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  page.axeState.axeRunning = false;
  for (const violation of result.violations) {
    fail(`${label}: axe ${violation.id} (${violation.impact}) on ${violation.nodes.length} node(s): ${violation.nodes[0].target.join(" ")}`);
  }
}

// 1. Load from a local file: no external request, no error.
{
  const { context, page, external, problems } = await openPage();
  await page.goto(pageUrl);
  await rendered(page);
  if (external.length) fail("requests on load: " + external.join(", "));
  for (const problem of problems) fail("load: " + problem);
  const heading = await page.textContent("#main h1");
  if (!heading.includes("Kde se právě nacházíte")) fail("first visit does not show the stage question: " + heading);
  await axe(page, "stage entry");

  // Keyboard: the skip link, lens picker, language switch and stage buttons are reachable with Tab.
  const reached = new Set();
  for (let i = 0; i < 25; i += 1) {
    await page.keyboard.press("Tab");
    reached.add(await page.evaluate(() => {
      const el = document.activeElement;
      return el ? (el.id || el.className || el.tagName) + ":" + (el.textContent || "").trim().slice(0, 20) : "";
    }));
  }
  const joined = [...reached].join(" | ");
  for (const expected of ["skip-link", "lens-select", "English", "Připravuji projekt"]) {
    if (!joined.includes(expected)) fail("keyboard does not reach: " + expected);
  }
  await context.close();
}

// 2. Every station in every lens and language, then the other views.
{
  const { context, page, external, problems } = await openPage();
  await page.goto(pageUrl);
  await rendered(page);
  const views = [];
  for (const lang of ["cs", "en"]) {
    for (const lens of lenses) for (const station of stations) views.push(`#/${lang}/${lens}/path/${station}`);
    for (const view of ["explorer", "resources", "repositories", "selfcheck"]) views.push(`#/${lang}/V/${view}`);
    for (const principle of principles.slice(0, 3)) views.push(`#/${lang}/K/explorer/${principle}`);
    for (const id of pages) views.push(`#/${lang}/V/page/${id}`);
  }
  for (const hash of views) {
    await page.evaluate((value) => { window.location.hash = value; }, hash);
    await page.waitForFunction((value) => window.location.hash === value && document.querySelector("#main h1"), hash);
    const headingText = (await page.textContent("#main h1")).trim();
    if (!headingText) fail(`${hash}: the main heading is empty`);
    const lang = await page.evaluate(() => document.documentElement.lang);
    if (lang !== hash.split("/")[1]) fail(`${hash}: html lang is ${lang}`);
    if (hash.includes("/path/")) {
      const now = await page.locator(".now").count();
      if (!now) fail(`${hash}: no L0 block`);
    }
    await axe(page, hash);
  }
  if (external.length) fail("requests while navigating: " + external.join(", "));
  for (const problem of problems) fail("navigation: " + problem);
  console.log(`checked ${views.length} views`);
  await context.close();
}

// 3. Reflow at 320 CSS pixels: no horizontal scrolling.
{
  const { context, page } = await openPage({ width: 320, height: 800 });
  for (const hash of ["#/cs/SR/path/publikace", "#/en/DS/resources", "#/cs/K/explorer/F1"]) {
    await page.goto(pageUrl + hash);
    await rendered(page);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (overflow > 1) fail(`${hash}: horizontal scroll of ${overflow}px at 320 px`);
  }
  await context.close();
}

// 4. Embedded in an iframe.
{
  const host = resolve(root, ".cache", "iframe-host.html");
  mkdirSync(dirname(host), { recursive: true });
  writeFileSync(host, `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Host</title></head><body><iframe title="FAIR guide" src="${pageUrl}#/cs/V/path/repozitar" style="width:100%;height:800px"></iframe></body></html>`);
  const { context, page } = await openPage();
  await page.goto(pathToFileURL(host).href);
  const frame = page.frameLocator("iframe");
  await frame.locator("#main h1").waitFor();
  const heading = await frame.locator("#main h1").textContent();
  if (!heading.includes("Repozitář")) fail("iframe: unexpected heading " + heading);
  await frame.getByRole("link", { name: /Další krok/ }).click();
  const next = await frame.locator("#main h1").textContent();
  if (!next.includes("Popis")) fail("iframe: navigation inside the frame failed: " + next);
  await context.close();
}

await browser.close();
if (failures.length) {
  console.error(failures.map((failure) => "FAIL " + failure).join("\n"));
  console.error(`${failures.length} problem(s)`);
  process.exit(1);
}
console.log("page checks passed");
