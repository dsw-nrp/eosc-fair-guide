// The shared accessibility policy enables the WCAG rules it intends, and every page check uses it.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { WCAG_TAGS, audit } from "./accessibility.mjs";

const root = resolve(import.meta.dirname, "../..");
const { chromium } = await import("./browser.mjs");

// No check keeps a tag list of its own: divergent lists silently check different criteria on different views.
const here = resolve(root, "tests/page");
for (const name of readdirSync(here).filter((file) => file.endsWith(".mjs") && !["accessibility.mjs", "check_accessibility.mjs"].includes(file))) {
  const text = readFileSync(resolve(here, name), "utf8");
  assert(!/withTags\(|new AxeBuilder/.test(text), `${name} audits outside the shared policy`);
}

// A fixture with one known failure per level: each must be reported, so the level's rules are actually enabled.
const fixture = `<!doctype html><html><head><title>Policy fixture</title>
<meta name="viewport" content="width=device-width, user-scalable=no"></head><body><main>
<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">
<p style="color:#bbbbbb;background:#ffffff">Low contrast text</p>
<label>Name <input type="text" autocomplete="nonsense-value"></label>
<p><button style="width:8px;height:8px;padding:0;border:0"></button><button style="width:8px;height:8px;padding:0;border:0;margin:0">x</button></p>
</main></body></html>`;
const expected = {
  "image-alt": "wcag2a",
  "html-has-lang": "wcag2a",
  "color-contrast": "wcag2aa",
  "meta-viewport": "wcag2aa",
  "autocomplete-valid": "wcag21aa",
  "target-size": "wcag22aa",
};
const browser = await chromium.launch();
try {
  const page = await (await browser.newContext()).newPage();
  await page.route("https://policy.example/", (route) => route.fulfill({ contentType: "text/html", body: fixture }));
  await page.goto("https://policy.example/");
  const result = await audit(page);
  const reported = new Map(result.violations.map((violation) => [violation.id, violation.tags]));
  for (const [rule, tag] of Object.entries(expected)) {
    assert(reported.has(rule), `the policy did not report ${rule} (${tag})`);
    assert(reported.get(rule).includes(tag), `${rule} is not tagged ${tag}`);
  }
  // Every policy tag enables rules in this axe version; a WCAG 2.2 level A tag would be added once axe has rules for it.
  const counts = await page.evaluate((tags) => Object.fromEntries([...tags, "wcag22a"].map((tag) => [tag, window.axe.getRules([tag]).length])), [...WCAG_TAGS]);
  for (const tag of WCAG_TAGS) assert(counts[tag] > 0, `${tag} enables no rule`);
  assert.equal(counts.wcag22a, 0, "axe now has WCAG 2.2 level A rules; add wcag22a to the policy");
  console.log(`check_accessibility: one policy (${WCAG_TAGS.join(", ")}) in every check; ${Object.keys(expected).length} known failures across levels reported`);
} finally {
  await browser.close();
}
