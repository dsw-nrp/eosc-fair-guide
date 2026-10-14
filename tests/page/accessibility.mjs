// The guide's one accessibility policy for every page check: WCAG 2.0, 2.1 and 2.2 at levels A and AA, as axe-core
// tags its rules (AGENTS.md, invariant 9). Every check audits through this module; check_accessibility.mjs proves
// that the tags enable rules at each level and that no check carries a list of its own.
import { AxeBuilder } from "@axe-core/playwright";

export const WCAG_TAGS = Object.freeze(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]);

/** Run the policy on the page, or on the part of it a selector names. */
export function audit(page, include) {
  const builder = new AxeBuilder({ page }).withTags([...WCAG_TAGS]);
  return (include ? builder.include(include) : builder).analyze();
}
