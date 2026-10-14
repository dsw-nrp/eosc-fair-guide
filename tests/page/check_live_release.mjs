// Opt-in live verification for release acceptance. No fixtures, credentials or
// report imports: two citation lookups and one complete FAIR-Checker assessment.
import assert from 'node:assert/strict';
import {mkdirSync, writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
const root = resolve(import.meta.dirname, '../..');
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, '.cache/ms-playwright');
const base = pathToFileURL(resolve(root, '_site/index.html')).href;
const browser = await chromium.launch();
const context = await browser.newContext({viewport: {width: 1280, height: 900}});
const page = await context.newPage();
const receipt = {checked: new Date().toISOString(), citations: [], assessment: null, errors: []};
const requests = [];
page.on('request', request => {if (/^https?:/.test(request.url())) requests.push(request.url());});
try {
  for (const doi of ['10.71495/5dv6-v116', '10.1038/sdata.2016.18']) {
    try {
      const before = requests.length;
      await page.goto(base + '#/cs/V/page/citation/' + encodeURIComponent(doi));
      await page.waitForSelector('#citation-doi');
      assert.equal(requests.length, before, 'citation entry sends no request');
      await page.locator('.citation-helper button[type="submit"]').click();
      await page.waitForFunction(() => !document.querySelector('.citation-helper button[type="submit"]').disabled,
        null, {timeout: 60000});
      const formats = await page.locator('.citation-format pre').count();
      let distinctStyle = false;
      if (formats === 4) distinctStyle = await page.locator('#citation-apa').textContent() !== await page.locator('#citation-iso690').textContent();
      receipt.citations.push({doi, formats, distinctStyle});
      console.log(`Citation ${doi}: ${formats}/4 formats, distinct APA/Czech ISO: ${distinctStyle}`);
      assert.equal(formats, 4, 'all four formats must be available');
      assert(distinctStyle, 'Czech ISO must not fall back to APA');
    } catch (error) {receipt.errors.push(`Citation ${doi}: ${error.message}`);}
  }
  try {
    // Confirm the public subject's type without storing personal metadata.
    const doi = '10.5281/zenodo.21726258';
    const response = await context.request.get('https://api.datacite.org/dois/' + doi);
    assert.equal(response.status(), 200, 'the real dataset record is available');
    const record = (await response.json()).data.attributes;
    assert.equal(record.types.resourceTypeGeneral, 'Dataset', 'assessment target is a real dataset');
    const target = 'https://doi.org/' + doi;
    const before = requests.length;
    await page.goto(base + '#/en/V/check/dataset');
    await page.waitForSelector('#mode-after');
    await page.locator('#mode-after').check();
    await page.waitForSelector('#provider-run-fair-checker');
    await page.evaluate(value => {
      const FG = window.FairGuide, state = FG.state.answers.dataset;
      state.pid = FG.live.parsePid(value).value; state.target = value; FG.saveState(); FG.rerender();
    }, target);
    await page.waitForSelector('#provider-run-fair-checker:not([disabled])');
    assert.equal(requests.length, before, 'target entry sends no request');
    await page.locator('#provider-run-fair-checker').click();
    await page.waitForSelector('#provider-attached-fair-checker', {timeout: 240000});
    const assessment = await page.evaluate(() => {
      const saved = window.FairGuide.state.answers.dataset.assessments[0];
      return {target: saved.target, versions: saved.versions, reviewed: saved.reviewed,
        metrics: saved.results.map(result => ({id: result.id, score: result.score?.value, error: result.error || null}))};
    });
    receipt.assessment = assessment;
    assert.equal(assessment.target, target);
    assert.equal(assessment.metrics.length, 12, 'every metric is retained');
    assert.equal(new Set(assessment.metrics.map(metric => metric.id)).size, 12);
    assert(assessment.metrics.every(metric => !metric.error && Number.isInteger(metric.score)), 'all twelve metrics must have a native result');
    console.log(`FAIR-Checker: ${assessment.metrics.length}/12 native results, API ${assessment.versions.api}, reviewed ${assessment.reviewed}`);
  } catch (error) {receipt.errors.push('FAIR-Checker: ' + error.message);}
  const allowed = await page.evaluate(() => window.FairGuide.config.connectors.map(connector => connector.origin));
  assert(requests.every(url => allowed.some(origin => url.startsWith(origin + '/'))), 'every browser request uses an enrolled connector');
} catch (error) {receipt.errors.push(error.message);}
finally {
  const directory = resolve(root, '.cache/live-release');
  mkdirSync(directory, {recursive: true});
  writeFileSync(resolve(directory, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
  await browser.close();
}
if (receipt.errors.length) {console.error(receipt.errors.join('\n')); process.exitCode = 1;}
else console.log(`Live release checks passed (${requests.length} explicit browser requests).`);
