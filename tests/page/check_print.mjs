// Every check prints basic and extended reports without empty trailing PDF pages; evaluator inputs follow mappings.
import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { assertNoBlankPages } from "./pdf_checks.mjs";

const root = resolve(import.meta.dirname, "../..");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const temporary = resolve(root, ".cache/browser-temp");
mkdirSync(temporary, { recursive: true });
process.env.TEMP = temporary; process.env.TMP = temporary;
const { chromium } = await import("playwright");
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const file = pathToFileURL(resolve(root, "_site/index.html")).href;
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
const cases = [];
try {
  await page.goto(file + "#/en/V/check/dataset/evidence");
  await page.waitForSelector("#mode-after");
  const checks = await page.evaluate(() => window.FairGuide.ofType("Quiz").map((check) => check.identifier));
  for (const lang of ["cs", "en"]) {
    for (const check of checks) {
      await page.goto(file + `#/${lang}/V/check/${check}/evidence`);
      await page.waitForFunction((check) => document.querySelector(".check-head h1") && window.FairGuide.state.answers[check], check);
      const modes = await page.evaluate((id) => window.FairGuide.refs(window.FairGuide.get("#modes-" + id), "hasDefinedTerm").map((mode) => mode.termCode), check);
      for (const mode of modes.length ? modes : [null]) {
        await page.evaluate(({check, mode}) => {
          const FG = window.FairGuide;
          const entry = FG.get("#check-" + check);
          FG.state.answers[check] = { mode, profile: FG.refs(FG.get("#profiles-" + check), "hasDefinedTerm")[0]?.termCode,
            items: Object.fromEntries(FG.refs(entry, "hasPart").map((item) => [item.identifier, { value: "yes" }])) };
          FG.rerender();
        }, {check, mode});
        const mapped = check === "dataset" && mode === "after";
        assert.equal(await page.locator("#evaluator-fair-checker").count(), mapped ? 1 : 0, `${check}/${mode}: FAIR-Checker has reviewed question coverage`);
        assert.equal(await page.locator("#evaluator-f-uji").count(), mapped ? 1 : 0, `${check}/${mode}: F-UJI has reviewed question coverage`);
        for (const extended of [false, true]) {
          await page.evaluate(({check, extended}) => { window.FairGuide.state.answers[check].extended = extended; }, {check, extended});
          await page.goto(file + `#/${lang}/V/check/${check}/report`);
          await page.waitForSelector("#results");
          const pdf = await page.pdf({ format: "A4", printBackground: false });
          let pages;
          try { pages = assertNoBlankPages(pdf); }
          catch (error) {
            writeFileSync(resolve(root, ".cache/print-failure.pdf"), pdf);
            throw new Error(`${lang}/${check}/${mode}/${extended}: ${error.message}`, { cause: error });
          }
          cases.push(`${lang}/${check}/${mode || "default"}/${extended ? "extended" : "basic"}: ${pages}`);
          await page.goto(file + `#/${lang}/V/check/${check}/evidence`);
          await page.waitForSelector(".check-evidence");
        }
      }
    }
  }
  assert.deepEqual(errors, []);
  console.log(`check_print: ${cases.length} bilingual check/mode/scope PDFs contain text on every page; evaluator inputs follow reviewed question coverage`);
} finally { await browser.close(); }
