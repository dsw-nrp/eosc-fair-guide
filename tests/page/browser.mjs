// Shared browser lifecycle, bounded case execution and failure evidence for all Node browser checks.
import { root, mapLimit, workerCount, browserSourceDigest } from "../../scripts/browser_env.mjs";
import { acquireSlot } from "../../scripts/browser_slots.mjs";
import { AsyncLocalStorage } from "node:async_hooks";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, readdirSync, writeFileSync, rmSync } from "node:fs";
import { resolve, sep } from "node:path";
const { chromium: engine } = await import("playwright");
const reportStart = performance.now();

const storage = new AsyncLocalStorage();
const scriptName = (process.argv[1] || "browser-fixture").split(/[\\/]/).at(-1);
const reportFile = resolve(process.env.CHECK_CASE_REPORT || resolve(root, ".cache/check-details", scriptName + ".json"));
const artifactRoot = reportFile + ".artifacts";
const sourceDigest = browserSourceDigest();
let revision = process.env.GITHUB_SHA || "unknown";
try { revision = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim(); } catch { /* Report missing identity honestly. */ }
const script = { name: scriptName, contexts: new Set(), failed: false, problems: [], artifacts: [] };
const cases = [];
let planned = [], selected = [], count = 0;

function saveReport() {
  mkdirSync(resolve(reportFile, ".."), { recursive: true });
  const skipped = planned.filter((name) => !selected.includes(name));
  const pending = selected.filter((name) => !cases.some((item) => item.name === name));
  writeFileSync(reportFile, JSON.stringify({ revision, source_digest: sourceDigest, node: process.version, platform: process.platform,
    workers: workerCount(), trace_snapshots: process.env.CHECK_TRACE_SNAPSHOTS === "1",
    seconds: (performance.now() - reportStart) / 1000, attempt: 1, retries: [],
    status: script.failed || cases.some((item) => item.status === "failed") ? "failed" : skipped.length || pending.length ? "partial" : "passed",
    planned, executed: cases, skipped, pending, script: { name: script.name, problems: script.problems, artifacts: script.artifacts } }, null, 2) + "\n");
}

async function capture(context, scope) {
  if (context.__captured) return;
  context.__captured = true;
  const directory = resolve(artifactRoot, `${String(++count).padStart(3, "0")}-${scope.name.replace(/[^\w-]/g, "_")}`);
  mkdirSync(directory, { recursive: true });
  const pages = [];
  for (const [index, page] of context.pages().entries()) {
    const snapshot = { url: page.url(), requested: page.__requested, errors: page.__errors || [] };
    try {
      snapshot.heading = await page.locator("#main h1, h1").first().textContent({ timeout: 1000 });
    } catch { snapshot.heading = null; }
    try { await page.screenshot({ path: resolve(directory, `page-${index}.png`), timeout: 5000 }); }
    catch (error) { snapshot.screenshot_error = error.message; }
    try { writeFileSync(resolve(directory, `page-${index}.html`), await page.content()); }
    catch (error) { snapshot.dom_error = error.message; }
    pages.push(snapshot);
  }
  try { await context.tracing.stop({ path: resolve(directory, "trace.zip") }); }
  catch (error) { scope.problems.push(`trace: ${error.message}`); }
  writeFileSync(resolve(directory, "state.json"), JSON.stringify({ revision, case: scope.name, pages }, null, 2) + "\n");
  scope.artifacts.push(directory);
}

async function instrument(context, scope) {
  scope.contexts.add(context);
  // Action traces stay cheap during exhaustive sweeps; capture screenshots and DOM only at failure.
  await context.tracing.start({ screenshots: false, snapshots: process.env.CHECK_TRACE_SNAPSHOTS === "1" });
  context.on("page", (page) => {
    page.__errors = [];
    page.on("console", (message) => { if (message.type() === "error") page.__errors.push(message.text()); });
    page.on("pageerror", (error) => page.__errors.push(error.message));
    const goto = page.goto.bind(page);
    page.goto = (url, ...args) => { page.__requested = String(url); return goto(url, ...args); };
  });
  const close = context.close.bind(context);
  context.close = async (...args) => {
    // A top-level assertion may unwind through finally before the error reaches Node. Retain that context's
    // evidence provisionally, and discard it only at a successful process exit. Named cases know their verdict.
    if (scope === script || scope.failed) await capture(context, scope);
    else await context.tracing.stop();
    scope.contexts.delete(context);
    return close(...args);
  };
  return context;
}

async function lease(scope) {
  scope.lease ||= acquireSlot();
  await scope.lease;
}

async function release(scope) {
  if (!scope.lease) return;
  try { (await scope.lease)(); } catch { /* Acquisition failure remains the original case failure. */ }
  scope.lease = null;
}

export const chromium = {
  async launch(...args) {
    const browser = await engine.launch(...args);
    const newContext = browser.newContext.bind(browser), close = browser.close.bind(browser);
    browser.newContext = async (...args) => {
      const scope = storage.getStore() || script;
      await lease(scope);
      return instrument(await newContext(...args), scope);
    };
    // Browser.newPage's implicit context otherwise bypasses the instrumented public factory.
    browser.newPage = async (options) => (await browser.newContext(options)).newPage();
    browser.close = async (...args) => {
      for (const context of browser.contexts()) await context.close();
      await release(script);
      return close(...args);
    };
    return browser;
  },
};

export function recordFailure(message) {
  const scope = storage.getStore() || script;
  scope.failed = true;
  scope.problems.push(message);
}

export async function runCases(entries, only = []) {
  planned = entries.map(([name]) => name);
  const matches = (name, choice) => name === choice || name.startsWith(choice + ":");
  const unknown = only.filter((choice) => !planned.some((name) => matches(name, choice)));
  if (unknown.length) throw new Error(`Unknown browser case(s): ${unknown.join(", ")}`);
  selected = planned.filter((name) => !only.length || only.some((choice) => matches(name, choice)));
  await mapLimit(entries.filter(([name]) => selected.includes(name)), async ([name, run]) => {
    const scope = { name, contexts: new Set(), failed: false, problems: [], artifacts: [] };
    const start = performance.now();
    await storage.run(scope, async () => {
      try {
        await lease(scope);
        scope.queueSeconds = (performance.now() - start) / 1000;
        await run();
      }
      catch (error) { scope.aborted = true; recordFailure(error.stack || String(error)); }
      finally {
        for (const context of [...scope.contexts]) await context.close();
        await release(scope);
      }
    });
    cases.push({ name, status: scope.failed ? "failed" : "passed", seconds: (performance.now() - start) / 1000,
      queue_seconds: scope.queueSeconds || 0, aborted: scope.aborted || false,
      problems: scope.problems, artifacts: scope.artifacts });
    saveReport();
  });
  return cases;
}

process.on("uncaughtException", async (error) => {
  script.failed = true;
  script.problems.push(error.stack || String(error));
  console.error(error);
  for (const context of [...script.contexts]) {
    try { await context.close(); } catch { /* The original error remains the failure. */ }
  }
  saveReport();
  process.exit(1);
});
process.on("exit", (code) => {
  if (code) script.failed = true;
  if (!planned.length) { planned = [script.name]; selected = [...planned]; }
  if (!cases.length) cases.push({ name: script.name, status: code ? "failed" : "passed", attempt: 1 });
  if (!code && !script.failed && !cases.some((item) => item.status === "failed")) {
    for (const directory of script.artifacts) {
      if (!resolve(directory).startsWith(resolve(artifactRoot) + sep)) throw new Error("Artifact cleanup escaped its root");
      rmSync(directory, { recursive: true, force: true });
    }
    script.artifacts = [];
  }
  saveReport();
});
