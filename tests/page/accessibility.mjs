// The guide's one accessibility policy for every page check: WCAG 2.0, 2.1 and 2.2 at levels A and AA, as axe-core
// tags its rules (AGENTS.md, invariant 9). Every check audits through this module; check_accessibility.mjs proves
// that the tags enable rules at each level and that no check carries a list of its own.
import { AxeBuilder } from "@axe-core/playwright";
import axe from "axe-core";
import { isDeepStrictEqual } from "node:util";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

export const WCAG_TAGS = Object.freeze(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]);

/** Run the policy on the page, or on the part of it a selector names. */
export function referenceAudit(page, include) {
  const builder = new AxeBuilder({ page }).withTags([...WCAG_TAGS]);
  return (include ? builder.include(include) : builder).analyze();
}

/** Compare semantic outcomes, excluding only run metadata (URL, date and elapsed time). */
export function auditOutcomes(result) {
  const checks = (values) => values.map(({ id, impact, message, data, relatedNodes }) => ({
    id, impact, message, data, relatedNodes: relatedNodes?.map(({ html, target }) => ({ html, target })),
  })).sort((a, b) => a.id.localeCompare(b.id));
  const outcomes = Object.fromEntries(["violations", "incomplete", "passes", "inapplicable"].map((key) => [key,
    result[key].map(({ id, impact, tags, nodes }) => ({ id, impact, tags: [...tags].sort(), nodes: nodes.map((node) => ({
      html: node.html, target: node.target, impact: node.impact,
      any: checks(node.any), all: checks(node.all), none: checks(node.none),
    })).sort((a, b) => JSON.stringify(a.target).localeCompare(JSON.stringify(b.target))) })).sort((a, b) => a.id.localeCompare(b.id)),
  ]));
  // The reference adapter serializes partial results through JSON, omitting undefined diagnostic fields.
  return JSON.parse(JSON.stringify(outcomes));
}

/** Reuse setup only within a frame-free document; navigation discards the engine naturally. */
export async function audit(page, include) {
  // Viewport media-query listeners can replace the view on the next frame. Audit the completed layout.
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
  });
  const mode = process.env.CHECK_AXE_MODE || "reuse";
  if (!["reuse", "reference", "compare"].includes(mode)) throw new Error("Unknown CHECK_AXE_MODE: " + mode);
  const hasFrames = async () => page.frames().length !== 1 || await page.locator("iframe, frame").count() !== 0;
  if (include || mode === "reference" || await hasFrames()) return referenceAudit(page, include);
  if (!await page.evaluate((version) => window.axe?.version === version, axe.version)) await page.evaluate(axe.source);
  const result = await page.evaluate((tags) => window.axe.run(document, { runOnly: { type: "tag", values: tags } }), [...WCAG_TAGS]);
  // A frame may have appeared during the audit; its coverage belongs to the established adapter.
  if (await hasFrames()) return referenceAudit(page, include);
  if (mode === "compare") {
    const reference = await referenceAudit(page);
    if (!isDeepStrictEqual(auditOutcomes(result), auditOutcomes(reference))) {
      const directory = resolve(import.meta.dirname, '../../.cache/axe-parity');
      mkdirSync(directory, { recursive: true });
      writeFileSync(resolve(directory, `${process.pid}.json`), JSON.stringify({ url: page.url(), actual: auditOutcomes(result), reference: auditOutcomes(reference) }, null, 2));
      throw new Error("Reused axe outcomes differ from the reference: " + page.url());
    }
  }
  return result;
}
