// Every check prints basic and extended reports without empty trailing PDF pages; evaluator inputs follow mappings.
import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { assertNoBlankPages } from "./pdf_checks.mjs";
import { printMatrix } from "./print_matrix.mjs";
import { readFileSync } from "node:fs";

const root = resolve(import.meta.dirname, "../..");
const temporary = resolve(root, ".cache/browser-temp");
mkdirSync(temporary, { recursive: true });
process.env.TEMP = temporary; process.env.TMP = temporary;
const { chromium } = await import("./browser.mjs");
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const file = pathToFileURL(resolve(root, "_site/index.html")).href;
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
const cases = [];
const matrix = printMatrix(JSON.parse(readFileSync(resolve(root, '_site/ro-crate-metadata.json'), 'utf8'))['@graph']);
try {
  await page.goto(file + "#/en/V/check/dataset/evidence");
  await page.waitForSelector("#mode-after");
  for (const { lang, check, mode, extended, key, grouping } of matrix) {
      await page.goto(file + `#/${lang}/V/check/${check}/evidence`);
      await page.waitForFunction((check) => document.querySelector(".check-head h1") && window.FairGuide.state.answers[check], check);
        await page.evaluate(({check, mode, grouping}) => {
          const FG = window.FairGuide;
          const entry = FG.get("#check-" + check);
          FG.state.answers[check] = { mode, profile: FG.refs(FG.get("#profiles-" + check), "hasDefinedTerm")[0]?.termCode,
            items: Object.fromEntries(FG.refs(entry, "hasPart").map((item) => [item.identifier, { value: "yes" }])) };
          if (grouping) FG.state.checkGroupings[check] = grouping;
          else delete FG.state.checkGroupings[check];
          FG.rerender();
        }, {check, mode, grouping});
        const mapped = check === "dataset" && mode === "after";
        assert.equal(await page.locator("#evaluator-fair-checker").count(), mapped ? 1 : 0, `${check}/${mode}: FAIR-Checker has reviewed question coverage`);
        assert.equal(await page.locator("#evaluator-f-uji").count(), mapped ? 1 : 0, `${check}/${mode}: F-UJI has reviewed question coverage`);
          await page.evaluate(({check, extended}) => { window.FairGuide.state.answers[check].extended = extended; }, {check, extended});
          await page.goto(file + `#/${lang}/V/check/${check}/report`);
          await page.waitForSelector("#results");
          if (grouping) assert.equal(await page.locator('#results-steps').count(), 1, 'the selected path breakdown prints');
          const pdf = await page.pdf({ format: "A4", printBackground: false });
          let pages;
          try { pages = assertNoBlankPages(pdf); }
          catch (error) {
            writeFileSync(resolve(root, ".cache/print-failure.pdf"), pdf);
            throw new Error(`${lang}/${check}/${mode}/${extended}: ${error.message}`, { cause: error });
          }
          cases.push({ key, pages, status: 'passed' });
          await page.goto(file + `#/${lang}/V/check/${check}/evidence`);
          await page.waitForSelector(".check-evidence");
  }
  assert.deepEqual(errors, []);
  console.log(`check_print: ${cases.length} bilingual check/mode/scope PDFs contain text on every page; evaluator inputs follow reviewed question coverage`);
} finally {
  const directory = resolve(root, '.cache/screenshots/final');
  mkdirSync(directory, { recursive: true });
  writeFileSync(resolve(directory, 'print-coverage.json'), JSON.stringify({ planned: matrix.map((item) => item.key), executed: cases,
    skipped: matrix.filter((item) => !cases.some((done) => done.key === item.key)).map((item) => item.key) }, null, 2) + '\n');
  await browser.close();
}
