// Maintainer-reported menu, disclosures, narrow source cards, licence table, scope wording and printed reports.
import assert from "node:assert/strict";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { assertNoBlankPages } from "./pdf_checks.mjs";
import { audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
const temporary = resolve(root, ".cache/browser-temp");
mkdirSync(temporary, { recursive: true });
process.env.TEMP = temporary;
process.env.TMP = temporary;
const { chromium } = await import("./browser.mjs");
const base = pathToFileURL(resolve(root, "_site/index.html")).href;
const shots = resolve(root, ".cache/screenshots/repairs");
mkdirSync(shots, { recursive: true });
const browser = await chromium.launch();
try {
  for (const lang of ["cs", "en"]) {
    for (const width of [320, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 1000 } });
      const page = await context.newPage();
      const errors = [], external = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("request", (request) => { if (/^https?:/.test(request.url())) external.push(request.url()); });
      const visit = async (route, selector) => {
        await page.goto(base + `#/${lang}/V/${route}`);
        await page.waitForSelector(selector);
      };
      const inspect = async (name) => {
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, name + " reflows");
        assert.deepEqual((await audit(page)).violations, [], name);
        await page.screenshot({ path: resolve(shots, `${lang}-${width}-${name}.png`) });
      };

      await visit("path/metadata", ".station-resources");
      const sources = page.locator(".station-resources .entry-card");
      assert(await sources.count());
      assert.equal(await page.locator(".station-resources .entry-head .id-chip").count(), await sources.count(), "every compact source card keeps its identifier chip");
      assert(await page.locator(".station-resources .entry-head .id-chip").evaluateAll((chips) => chips.every((chip) => chip.getAttribute("href")?.includes("/catalogue/"))), "source chips lead to their catalogue entries");
      assert(await page.locator(".station-resources .entry-head .id-chip").evaluateAll((chips) => chips.filter((chip) => chip.textContent.length < 20).every((chip) => chip.getBoundingClientRect().height < 2 * parseFloat(getComputedStyle(chip).lineHeight))), "short source IDs stay on one line");
      if (width === 320) assert.equal(await page.locator(".role-menu").evaluate((node) => getComputedStyle(node).backgroundColor), "rgba(0, 0, 0, 0)", "the role control has no white inset background");
      const menu = page.locator(width === 320 ? ".rail-mobile" : ".rail-desktop");
      if (width === 320) await menu.locator(":scope > summary").click();
      assert.equal(await menu.evaluate((node) => getComputedStyle(node).borderTopStyle), "solid");
      const current = menu.locator('a[aria-current="step"]');
      assert.equal(await current.count(), 1);
      assert.equal(await current.evaluate((node) => getComputedStyle(node).borderTopStyle), "solid");
      await inspect("menu");
      if (width === 320) await menu.locator(":scope > summary").click();
      const badge = page.locator(".station-resources .node-badge").first();
      assert(await page.locator(".station-resources .badge[data-status]").evaluateAll((nodes) =>
        nodes.length > 0 && nodes.every((node) => !["flex", "inline-flex"].includes(getComputedStyle(node).display))),
      "status text flows as a sentence, including narrow operational labels");
      if (await badge.count()) {
        assert.equal(await badge.evaluate((node) => [...node.childNodes].some((child) => child.nodeType === 3 && child.textContent.trim())), false,
          "node facts are complete phrases, not anonymous flex items");
        for (const link of await badge.locator("a").all()) {
          assert((await link.boundingBox()).width > 40, "the charter link must not become a column of letters");
        }
        await badge.scrollIntoViewIfNeeded();
        await inspect("sources");
      }

      await visit("catalogue/k!terms~f.lens!", ".term-definition");
      const definition = page.locator(".term-definition").first();
      assert.equal(await definition.evaluate((node) => node.open), false);
      assert.match(await definition.locator("summary").innerText(), /Heslář(?:i)? Open Science/, "glossary definitions identify their actual source");
      assert.equal(await definition.locator("summary").evaluate((node) => getComputedStyle(node).fontWeight), "400", "source definitions have normal weight");
      await definition.locator("summary").click();
      assert(await definition.locator(":scope > .content").isVisible());
      assert(await definition.locator(":scope > .content").evaluate((node) => parseFloat(getComputedStyle(node).paddingLeft) >= 8));
      await inspect("definition");

      await visit("page/licence-compatibility", ".compatibility-cell");
      assert.equal(await page.locator(".compatibility-cell").count(), 49);
      const cells = await page.locator(".compatibility-cell").evaluateAll((nodes) => nodes.map((node) => ({
        permitted: node.dataset.compatible, symbol: node.querySelector(".compatibility-icon").textContent,
        hidden: node.querySelector(".compatibility-icon").getAttribute("aria-hidden"), text: node.textContent,
        colour: getComputedStyle(node.querySelector(".compatibility-icon")).color,
      })));
      assert(cells.every((cell) => cell.hidden === "true" && cell.text.trim().split(/\s+/).length === 2));
      assert(cells.filter((cell) => cell.permitted === "true").every((cell) => cell.symbol === "✓"));
      assert(cells.filter((cell) => cell.permitted === "false").every((cell) => cell.symbol === "✗"));
      assert.notEqual(cells.find((cell) => cell.permitted === "true").colour, cells.find((cell) => cell.permitted === "false").colour);
      await inspect("licences");

      await page.goto(base + `#/${lang}/DS/path/plan`);
      await page.waitForSelector(".station-resources");
      await page.evaluate(() => { for (const node of document.querySelectorAll("details")) node.open = true; });
      const institutionLink = page.locator(`.station li a[href="#/${lang}/DS/check/institution"]`);
      assert.equal(await institutionLink.count(), 1, "the named institution check is a working prose link");
      await institutionLink.click();
      await page.waitForSelector(".check-evidence");
      assert.match(page.url(), /check\/institution/);
      await visit("check/institution/answers", ".tier-info");
      const scope = await page.locator(".tier-info").innerText();
      assert(scope.includes("9") && scope.includes("83") && scope.includes("Open Science III"));
      assert(!/zapojení|admission|FAIR analysis|Analýza FAIR/.test(scope), "institution scope does not describe NDI admission");
      await inspect("institution");

      await visit("check/dataset/evidence", "#mode-after");
      await page.locator("#mode-after").check();
      assert.equal(await page.locator("#evaluator-fair-checker").count(), 1, "FAIR-Checker supports published-dataset questions");
      assert.equal(await page.locator("#evaluator-f-uji").count(), 1, "F-UJI supports published-dataset questions");
      await visit("check/dataset/answers", "#answer-dataset-01-yes");
      await page.locator("#answer-dataset-01-yes").check();
      await page.locator("#answer-dataset-04-no").check();
      await page.locator("#answer-dataset-05-unknown").check();
      await visit("check/dataset/report", ".distribution-bar");
      await page.emulateMedia({ media: "print" });
      await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
      const segments = await page.locator(".distribution-bar > span").evaluateAll((nodes) => nodes.map((node) => ({
        colour: getComputedStyle(node).color, border: getComputedStyle(node).borderTopStyle,
        adjustment: getComputedStyle(node).printColorAdjust,
      })));
      assert(segments.length && segments.every((segment) => segment.colour === "rgb(0, 0, 0)" && segment.border === "solid" && segment.adjustment === "exact"),
        "every printed count stays visible when background printing is off");
      assert(await page.locator(".check-head h1").isVisible(), "the printed report names its check");
      assert.equal(await page.locator(".check-parts").isVisible(), false);
      assert.equal(await page.locator(".check-report details:not([open])").count(), 0);
      assert(await page.locator(".agreement-question .button-link").first().isVisible(), "question names print with evaluator answers");
      assert(await page.locator(".agreement-link").first().isVisible(), "reader answers print with evaluator answers");
      await page.screenshot({ path: resolve(shots, `${lang}-${width}-print.png`), fullPage: true });
      if (width === 1280) assertNoBlankPages(await page.pdf({ path: resolve(shots, `${lang}-report.pdf`), format: "A4", printBackground: false }));
      await page.evaluate(() => window.dispatchEvent(new Event("afterprint")));
      assert(await page.locator(".check-report details:not([open])").count(), "printing restores closed disclosures");
      assert.deepEqual(errors, []);
      assert.deepEqual(external, []);
      await context.close();
    }
  }
  console.log("check_repairs: bilingual desktop/phone menu, definitions, sources, licence marks, institution scope and background-free report printing pass");
} finally {
  await browser.close();
}
