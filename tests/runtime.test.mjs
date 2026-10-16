import assert from "node:assert/strict";
import { test, mock } from "node:test";
import { resolve } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, mkdirSync, readFileSync, writeFileSync, unlinkSync, rmdirSync } from "node:fs";
import { browserEnvironment, root, mapLimit, workerCount, checkDefaults } from "../scripts/browser_env.mjs";
import { slotIsAbandoned } from "../scripts/browser_slots.mjs";

test("a released or reassigned slot is not abandoned when its former owner exits", () => {
  for (const reassigned of [false, true]) {
    const slot = mkdtempSync(resolve(root, ".cache/runtime-owner-race-"));
    writeFileSync(resolve(slot, "owner"), "123456789");
    const probe = mock.method(process, "kill", () => {
      // Reproduce the exact interleaving: read old owner, release/reassign, old process exits.
      unlinkSync(resolve(slot, "owner")); rmdirSync(slot);
      if (reassigned) { mkdirSync(slot); writeFileSync(resolve(slot, "owner"), String(process.pid)); }
      throw Object.assign(new Error("former owner exited"), { code: "ESRCH" });
    });
    try { assert.equal(slotIsAbandoned(slot), false, `reassigned=${reassigned}`); }
    finally { probe.mock.restore(); }
  }
  const slot = mkdtempSync(resolve(root, ".cache/runtime-dead-owner-"));
  writeFileSync(resolve(slot, "owner"), "123456789");
  const probe = mock.method(process, "kill", () => {
    throw Object.assign(new Error("dead owner"), { code: "ESRCH" });
  });
  try { assert.equal(slotIsAbandoned(slot), true, "a genuinely abandoned slot still fails closed"); }
  finally { probe.mock.restore(); }
});

test("local and CI budgets share one policy and leave explicit budgets intact", () => {
  const policy = JSON.parse(readFileSync(resolve(root, "scripts/check_policy.json"), "utf8"));
  assert.deepEqual(checkDefaults({}, 16), { profile: "local", ...policy.local });
  assert.deepEqual(checkDefaults({ CI: "true" }, 16), { profile: "ci", ...policy.ci });
  for (const CI of ["", "0", "false", "FALSE"]) assert.equal(checkDefaults({ CI }, 16).profile, "local");
  assert.deepEqual(checkDefaults({}, 1), { profile: "local", jobs: 1, browser_workers: 1 });
  assert.equal(workerCount("8"), 8);
});

test("installer and checks share the repository default and preserve explicit overrides", () => {
  assert.equal(browserEnvironment({}).PLAYWRIGHT_BROWSERS_PATH, resolve(root, ".cache/ms-playwright"));
  for (const value of ["/opt/ms-playwright", "0", "D:\\shared\\browsers"]) {
    assert.equal(browserEnvironment({ PLAYWRIGHT_BROWSERS_PATH: value }).PLAYWRIGHT_BROWSERS_PATH, value);
  }
  assert.equal(browserEnvironment({ EXAMPLE: "preserved" }).EXAMPLE, "preserved");
});

test("bounded work preserves results and never exceeds the selected budget", async () => {
  let active = 0, maximum = 0;
  const result = await mapLimit([0, 1, 2, 3, 4, 5], async (value) => {
    maximum = Math.max(maximum, ++active);
    await new Promise((done) => setImmediate(done));
    active--;
    return value * 2;
  }, 2);
  assert.equal(maximum, 2);
  assert.deepEqual(result, [0, 2, 4, 6, 8, 10]);
  assert.deepEqual(await mapLimit([], () => assert.fail()), []);
});

test("bad budgets fail rather than silently running an empty suite", () => {
  for (const value of ["0", "-1", "no", "1.5", ""]) assert.throws(() => workerCount(value));
  assert.equal(workerCount("2"), 2);
});

test("separate Node processes share the same browser-case limit", async () => {
  for (const budget of [1, 2]) {
    const directory = mkdtempSync(resolve(root, ".cache/runtime-slots-"));
    const source = `import {acquireSlot} from './scripts/browser_slots.mjs';
      const release=await acquireSlot();
      const start=performance.timeOrigin+performance.now();
      await new Promise(done=>setTimeout(done,60));
      const end=performance.timeOrigin+performance.now();
      release(); console.log(JSON.stringify({start,end}));`;
    const intervals = await Promise.all(Array.from({length: 3}, () => new Promise((done, reject) => {
      const child = spawn(process.execPath, ["--input-type=module", "-e", source], {
        cwd: root, env: {...process.env, CHECK_BROWSER_SLOT_DIR: directory, CHECK_BROWSER_WORKERS: String(budget)},
      });
      let output = "", errors = "";
      child.stdout.on("data", (data) => { output += data; });
      child.stderr.on("data", (data) => { errors += data; });
      child.on("error", reject);
      child.on("close", (code) => {
        if (code) reject(new Error(errors)); else done(JSON.parse(output));
      });
    })));
    const events = intervals.flatMap(({start,end}) => [[start,1],[end,-1]]).sort((a,b) => a[0]-b[0] || a[1]-b[1]);
    let active = 0, maximum = 0;
    for (const [,delta] of events) { active += delta; maximum = Math.max(maximum, active); }
    assert.equal(maximum, budget);
  }
});

test("case reports retain skipped and aborted work and reject unknown selections", () => {
  mkdirSync(resolve(root, ".cache"), { recursive: true });
  const directory = mkdtempSync(resolve(root, ".cache/runtime-policy-"));
  function run(name, source) {
    const path = resolve(directory, name + ".json");
    const result = spawnSync(process.execPath, ["--input-type=module", "-e", source], {
      cwd: root, env: { ...process.env, CHECK_CASE_REPORT: path }, encoding: "utf8",
    });
    assert(!result.error, String(result.error));
    return { result, report: JSON.parse(readFileSync(path, "utf8")) };
  }
  const partial = run("partial", `import {runCases} from './tests/page/browser.mjs';
    await runCases([['one',async()=>{}],['two',async()=>{}]],['one']);`);
  assert.equal(partial.result.status, 0);
  assert.equal(partial.report.status, "partial");
  assert.deepEqual(partial.report.skipped, ["two"]);
  const aborted = run("aborted", `import {runCases} from './tests/page/browser.mjs';
    await runCases([['one',async()=>{throw new Error('deliberate')}],['two',async()=>{}]]);`);
  assert.equal(aborted.report.status, "failed");
  assert.equal(aborted.report.executed.find((item) => item.name === "one").aborted, true);
  assert.equal(aborted.report.executed.find((item) => item.name === "two").status, "passed");
  const unknown = run("unknown", `import {runCases} from './tests/page/browser.mjs';
    await runCases([['one',async()=>{}]],['misspelled']);`);
  assert.equal(unknown.result.status, 1);
  assert.equal(unknown.report.status, "failed");
});

test("a failed browser assertion retains the requested route, heading, errors, screenshot and trace", () => {
  const directory = mkdtempSync(resolve(root, ".cache/runtime-artifact-"));
  const path = resolve(directory, "failure.json");
  const result = spawnSync(process.execPath, ["--input-type=module", "-e", `
    import {chromium} from './tests/page/browser.mjs';
    const browser=await chromium.launch();
    try {
      const page=await browser.newPage();
      await page.goto('data:text/html,<h1>Deliberate fixture</h1>');
      await page.evaluate(()=>console.error('fixture error'));
      throw new Error('deliberate assertion failure');
    } finally {await browser.close();}`], {
    cwd: root, env: { ...process.env, CHECK_CASE_REPORT: path }, encoding: "utf8",
  });
  assert.equal(result.status, 1, result.stderr);
  const report = JSON.parse(readFileSync(path, "utf8"));
  assert.equal(report.status, "failed");
  const artifacts = report.script.artifacts[0];
  assert(artifacts, result.stderr);
  const state = JSON.parse(readFileSync(resolve(artifacts, "state.json"), "utf8"));
  assert.equal(state.pages[0].heading, "Deliberate fixture");
  assert(state.pages[0].requested.startsWith("data:"));
  assert(state.pages[0].errors.includes("fixture error"));
  for (const name of ["page-0.png", "page-0.html", "trace.zip"]) assert(existsSync(resolve(artifacts, name)));
});
