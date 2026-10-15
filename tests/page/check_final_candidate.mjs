// Final identity, potential coverage, phone navigation and complete catalogues with original definitions.
import assert from "node:assert/strict";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const { chromium } = await import("playwright");
const file = pathToFileURL(resolve(root, "_site/index.html")).href;
const screenshots = resolve(root, ".cache/screenshots/final");
mkdirSync(screenshots, { recursive: true });
const graph = JSON.parse(readFileSync(resolve(root, "_site/ro-crate-metadata.json"), "utf8"))["@graph"];
const browser = await chromium.launch();
try {
  for (const lang of ["cs", "en"]) {
    await Promise.all([320, 390, 1280].map(async (width) => {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      const page = await context.newPage();
      const errors = [], external = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("request", (request) => { if (/^https?:/.test(request.url())) external.push(request.url()); });
      await page.goto(file + `#/${lang}/V/path/licence`);
      await page.waitForSelector(".station h1");
      assert((await page.title()).includes(lang === "cs" ? "Licence" : "Licence"));
      if (width < 640) {
        assert(!(await page.locator(".navigation-menu").evaluate((menu) => menu.open)));
        assert(!(await page.locator(".role-menu").evaluate((menu) => menu.open)));
        assert((await page.locator(".station h1").boundingBox()).y < 600, "mobile navigation must leave room for the task");
        await page.locator(".role-menu > summary").click();
        await page.locator('.lens-option[data-lens="DS"]').click();
        await page.waitForFunction(() => window.FairGuide.state.lens === "DS");
        assert(await page.locator(".role-menu > summary").evaluate((summary) => summary === document.activeElement),
          "changing a phone role keeps focus on its visible control");
      }
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      assert.deepEqual((await audit(page)).violations, []);
      await page.screenshot({ path: resolve(screenshots, `${lang}-path-${width}.png`) });

      for (const [check, expected] of [["software", 6], ["cdif", 9], ["fdo", 2]]) {
        await page.goto(file + `#/${lang}/V/check/${check}/evidence`);
        await page.waitForSelector('.evidence-card[data-source="' + (check === "software" ? "software" : "pid") + '"]');
        const facts = await page.locator(".evidence-card").first().locator("dl").innerText();
        assert.match(facts, new RegExp("\\b" + expected + "\\b"), `${check} describes registered potential coverage`);
        assert.equal(await page.locator('.evidence-card[data-source="evaluators"]').count(), 0,
          `${check} offers no external evaluator without a reviewed question mapping`);
        assert.equal(await page.evaluate(() => Object.keys(window.FairGuide.state.answers).some((id) =>
          Object.keys(window.FairGuide.state.answers[id].items || {}).length)), false, "showing capability never answers questions");
      }

      await page.goto(file + `#/${lang}/V/catalogue/term`);
      await page.waitForSelector(".letter-index");
      assert.equal(await page.locator(".catalogue-group .entry-card").count(),
        graph.filter((entity) => entity.catalogueAddress?.startsWith("term/")).length, "every glossary term is present immediately");
      assert.equal(await page.locator(".catalogue-more").count(), 0, "the catalogue needs no Show more click");
      assert.equal(await page.locator(".term-definition[open]").count(), 0);
      await page.locator(".letter-index button").last().click();
      const last = page.locator(".catalogue-group").last();
      assert(await last.locator(".entry-card").count(), "choosing a letter reaches its existing entries");
      const definition = last.locator(".term-definition").first();
      if (await definition.count()) {
        await definition.locator("summary").click();
        assert(await definition.evaluate((element) => element.open));
      }
      assert.deepEqual((await audit(page)).violations, []);
      await page.screenshot({ path: resolve(screenshots, `${lang}-terms-${width}.png`) });

      await page.goto(file + `#/${lang}/V/catalogue/res/tool/github`);
      await page.waitForSelector("[id='item-tool/github']");
      assert.equal(await page.locator(".entry-card").count(), 1);
      const chip = page.locator(".entry-head .id-chip");
      assert.equal(await chip.innerText(), "github");
      assert((await chip.getAttribute("title")).includes("res/tool/github"));
      assert((await page.title()).toLowerCase().includes("github"));
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      assert.deepEqual((await audit(page)).violations, []);
      assert.deepEqual(errors, []);
      assert.deepEqual(external, []);
      for (const lens of ["V", "DS", "SR", "K"]) {
        for (const station of graph.filter((entity) => entity["@type"] === "HowToSection")) {
          await page.evaluate(() => { document.querySelector("#main").dataset.previousView = "true"; });
          await page.goto(file + `#/${lang}/${lens}/path/${station.identifier}`);
          await page.waitForFunction(() => !document.querySelector("#main")?.dataset.previousView && document.querySelector(".station h1"));
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false,
            `${lang}/${lens}/${station.identifier} reflows at ${width}px`);
          assert.deepEqual((await audit(page)).violations, [], `${lang}/${lens}/${station.identifier} at ${width}px`);
        }
      }
      assert.deepEqual(errors, []);
      assert.deepEqual(external, []);
      await context.close();
    }));
  }
  assert(!existsSync(resolve(root, "_site/api/resources/knav.github.json")), "no unreleased compatibility API document");
  assert(graph.every((entry) => !entry.catalogueAddress || entry.catalogueAddress.split("/").at(-1).length <= 32));
  console.log("check_final_candidate: compact identity, coverage, mobile menus, complete catalogues, originals and all 264 step/role/language/width accessibility states pass");
} finally {
  await browser.close();
}
