// One owner of the exhaustive station states. Closed and expanded guidance are different coverage states.
import assert from "node:assert/strict";
import { audit } from "./accessibility.mjs";
import { misalignedControls, collisions } from "./layout.mjs";

export function stationMatrix(graph) {
  const cases = [];
  const stations = graph.filter((entry) => entry["@type"] === "HowToSection");
  for (const lang of ["cs", "en"]) for (const width of [320, 390, 1280]) {
    for (const lens of ["V", "DS", "SR", "K"]) for (const station of stations) {
      for (const state of width === 1280 ? ["closed", "ai-open"] : ["closed"]) {
        const hash = `#/${lang}/${lens}/path/${station.identifier}`;
        cases.push({ key: `${hash}/${width}/${state}`, lang, width, lens, hash, state });
      }
    }
  }
  return cases;
}

export async function checkStation(page, item, uiStrings) {
  if (item.state === "closed") {
    // Reset persisted disclosure state explicitly: the matrix describes the state it actually audits.
    await page.evaluate(() => document.querySelectorAll('#main details[data-key="ai"]').forEach((node) => { node.open = false; }));
  } else {
    const tips = await page.evaluate(() => {
      const block = document.querySelector('#main details[data-key="ai"]');
      if (!block) return [];
      block.open = true;
      return [...block.querySelectorAll(".ai-tip")].map((tip) => Boolean(tip.querySelector("p > strong") &&
        tip.querySelector(".ai-prompt pre")?.textContent.trim() && tip.querySelector(".ai-prompt button .copy-label")));
    });
    assert(tips.length && tips.every(Boolean), `${item.key}: complete AI tips`);
  }
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${item.key}: reflow`);
  assert.deepEqual((await audit(page)).violations, [], item.key);
  // Former desktop page-sweep assertions belong to the expanded state, where every visible control is measured.
  if (item.state !== "ai-open") return;
  assert((await page.locator("#main h1").textContent()).trim(), `${item.key}: heading`);
  assert.equal(await page.evaluate(() => document.documentElement.lang), item.lang);
  assert(await page.locator(".now").count(), `${item.key}: L0`);
  assert.equal(await page.evaluate(() => [...document.getElementById("app").childNodes]
    .some((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim())), false, `${item.key}: shell`);
  const shown = await page.locator("#app").innerText();
  assert(!/\[object Object\]|\bundefined\b/.test(shown), `${item.key}: unformatted value`);
  const keys = (shown.match(/\b[a-z][a-zA-Z]*(?:\.[a-zA-Z][\w-]*)+\b/g) || [])
    .filter((token) => token.split(".").reduce((node, part) => node && typeof node === "object" ? node[part] : undefined, uiStrings) !== undefined);
  assert.deepEqual(keys, [], `${item.key}: raw UI keys`);
  assert.equal(await page.locator('#app a[href="#"]').count(), 0, `${item.key}: refused links`);
  assert.deepEqual(await page.evaluate(() => [...document.querySelectorAll('a[href^="http"]')]
    .filter((link) => link.target !== "_blank" || !/noopener/.test(link.rel)).map((link) => link.href)), [], `${item.key}: external targets`);
  assert.deepEqual(await page.evaluate(misalignedControls), [], `${item.key}: alignment`);
  assert.deepEqual(await page.evaluate(collisions), [], `${item.key}: collisions`);
}
