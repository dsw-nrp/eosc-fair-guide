// Browser smoke checks of an assembled production/preview tree. Health receipts are synthetic fixtures;
// this is not a release or a claim that an uncommitted source has passed release verification.
import assert from "node:assert/strict";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync } from "node:fs";
import { createServer } from "node:http";
import { extname, resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { audit } from "./accessibility.mjs";
import { installGuards } from "./guards.mjs";

const root = resolve(import.meta.dirname, "../..");
const cache = resolve(root, ".cache");
mkdirSync(cache, { recursive: true });
const fixture = mkdtempSync(resolve(cache, "deployment-fixture-"));
assert(realpathSync(fixture).startsWith(realpathSync(cache) + sep));
const stage = resolve(fixture, "staging");
const production = resolve(fixture, "production");
const output = resolve(fixture, "pages");
cpSync(resolve(root, "_site"), stage, { recursive: true });
cpSync(resolve(root, "_site"), production, { recursive: true });
const python = existsSync(resolve(root, ".venv/Scripts/python.exe")) && process.platform === "win32"
  ? resolve(root, ".venv/Scripts/python.exe") : "python";
const prepared = spawnSync(python, ["-c", `
import json,sys
from pathlib import Path
sys.path.insert(0, 'scripts')
import assemble_pages, package_site
stage,prod,out=map(Path,sys.argv[1:])
for site,sha in [(stage,'b'*40),(prod,'a'*40)]:
    path=site/'api/health.json'
    report=json.loads(path.read_text(encoding='utf-8'))
    config_path=site/'assets/data/ui.js'
    prefix='window.FairGuideData.ui = '
    text=config_path.read_text(encoding='utf-8')
    config=json.loads(next(line for line in text.splitlines() if line.startswith(prefix))[len(prefix):].removesuffix(';'))
    config['config']['build']['commit']=sha[:7]
    config_path.write_text('\\n'.join(prefix+json.dumps(config)+';' if line.startswith(prefix) else line for line in text.splitlines())+'\\n',encoding='utf-8')
    report['build']=config['config']['build']
    report.update(revision=sha,generated_at='2026-10-14T12:00:00Z')
    report['run']['status']='passed'
    path.write_text(json.dumps(report),encoding='utf-8')
artifact=out.parent/'release'
manifest=package_site.package(prod,'a'*40,artifact)
assemble_pages.assemble(stage,'b'*40,out,production=artifact,production_tag='v'+manifest['version'],production_commit='a'*40)
`, stage, production, output], { cwd: root, encoding: "utf8" });
assert.equal(prepared.status, 0, prepared.stderr || prepared.stdout);
const mime = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png" };
const server = createServer((request, response) => {
  const name = decodeURIComponent(new URL(request.url, "http://localhost").pathname).replace(/\/$/, "/index.html");
  const path = resolve(output, "." + name);
  if (!path.startsWith(output + sep)) { response.writeHead(403).end(); return; }
  try { response.writeHead(200, { "Content-Type": mime[extname(path)] || "application/octet-stream" }).end(readFileSync(path)); }
  catch { response.writeHead(404).end(); }
});
await new Promise((done) => server.listen(0, "127.0.0.1", done));
const origin = `http://127.0.0.1:${server.address().port}`;
const { chromium } = await import("./browser.mjs");
const browser = await chromium.launch();
const page = await (await browser.newContext()).newPage();
const {problems, external} = installGuards(page, {
  allowed: (url) => url.startsWith(origin + "/") || /^(data|blob):/.test(url),
});
const screenshots = resolve(cache, "screenshots/deployment");
mkdirSync(screenshots, { recursive: true });
try {
  await page.goto(origin + "/#/cs/DS/path/start");
  await page.waitForSelector(".journey-steps");
  assert.equal(await page.locator(".staging-notice").count(), 0, "production has no preview overlay");
  for (const width of [1280, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    for (const lang of ["cs", "en"]) {
      await page.goto(origin + `/next/#/${lang}/DS/path/start`);
      await page.waitForSelector(".journey-steps");
      assert.equal(await page.locator('meta[name="robots"]').getAttribute("content"), "noindex");
      assert(await page.locator(".staging-notice").isVisible());
      await page.locator('.journey-steps a[href$="/plan"]').click();
      await page.waitForSelector('#main details[data-key="L1"]');
      await page.locator('#main details[data-key="L1"] > summary').click();
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${lang}/${width}: reflow`);
      const access = await audit(page);
      assert.deepEqual(access.violations.map((entry) => entry.id), [], `${lang}/${width}: preview accessibility`);
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({ path: resolve(screenshots, `${lang}-${width}.png`) });
    }
  }
  await page.goto(origin + "/next/api/");
  const description = JSON.parse(readFileSync(resolve(output, "next/openapi.json"), "utf8"));
  const operation = description.paths["/api/health.json"].get;
  const selector = `#operations-${operation.tags[0]}-${operation.operationId}`;
  await page.waitForSelector(selector);
  assert(await page.locator(".staging-notice").isVisible(), "standalone API documentation has the notice");
  await page.locator(selector + " .opblock-summary").first().click();
  await page.locator(selector + " .try-out__btn").click();
  const requested = page.waitForResponse(origin + "/next/api/health.json");
  await page.locator(selector + " .execute").click();
  const response = await requested;
  assert.equal((await response.json()).revision, "b".repeat(40), "Swagger reads the preview's API, not production");
  assert.equal(response.status(), 200);
  assert.deepEqual(external, [], "assembly starts no external requests");
  assert.deepEqual(problems, [], "assembled views have no script errors");
  console.log("check_deployment: assembled Guide navigation, both languages/widths, noindex/notice, axe, reflow and preview Swagger requests pass");
} finally {
  await browser.close();
  await new Promise((done) => server.close(done));
  // Only this owned fixture below the repository cache is removed.
  assert(realpathSync(fixture).startsWith(realpathSync(cache) + sep));
  rmSync(fixture, { recursive: true, force: true });
}
