// Diagram checks for the FAIR Data Guide: every Mermaid diagram in the repository's Markdown files (and any
// diagrams/*.mmd source) renders with the pinned Mermaid in Chromium, and carries an accessible title and description
// (accTitle, accDescr). Approved authored SVG adaptations retain accessible alternatives and are copied exactly.
// Usage: npm run check:diagrams   (set PLAYWRIGHT_BROWSERS_PATH if the browser lives outside the default cache)

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const mermaidScript = createRequire(import.meta.url).resolve("mermaid/dist/mermaid.min.js");

/** Diagrams with the file and line they start at: fenced blocks in tracked Markdown files and whole .mmd files. */
function diagrams() {
  const tracked = execFileSync("git", ["ls-files", "--", "*.md", "*.mmd"], { cwd: root, encoding: "utf8" }).split("\n").filter(Boolean);
  const authored = existsSync(resolve(root, "diagrams")) ? readdirSync(resolve(root, "diagrams")).filter((file) => file.endsWith(".mmd")).map((file) => "diagrams/" + file) : [];
  const files = [...new Set(tracked.concat(authored))];
  const found = [];
  for (const file of files) {
    const text = readFileSync(resolve(root, file), "utf8");
    if (file.endsWith(".mmd")) {
      found.push({ where: file, text });
      continue;
    }
    const lines = text.split("\n");
    for (let index = 0; index < lines.length; index += 1) {
      if (lines[index].trim() !== "```mermaid") continue;
      const end = lines.findIndex((line, position) => position > index && line.trim() === "```");
      if (end < 0) {
        found.push({ where: `${file}:${index + 1}`, text: "", unclosed: true });
        break;
      }
      found.push({ where: `${file}:${index + 1}`, text: lines.slice(index + 1, end).join("\n") });
      index = end;
    }
  }
  return found;
}

const failures = [];
const all = diagrams();
/* The content model has one maintained entity-relationship diagram (docs/content-model.md); other documents link it. */
const models = all.filter((diagram) => /^\s*erDiagram\b/.test(diagram.text));
if (models.length !== 1 || !models[0].where.startsWith("docs/content-model.md")) failures.push(`the content-model diagram must be defined once, in docs/content-model.md: ${models.map((diagram) => diagram.where).join(", ") || "none"}`);
const browser = await chromium.launch();
const page = await browser.newPage();
await page.setContent("<!doctype html><html><body></body></html>");
await page.addScriptTag({ path: mermaidScript });
await page.evaluate(() => window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict" }));
for (const [index, diagram] of all.entries()) {
  if (diagram.unclosed) {
    failures.push(`${diagram.where}: the Mermaid block is not closed`);
    continue;
  }
  if (!/^\s*accTitle\s*:/m.test(diagram.text) || !/^\s*accDescr\s*[:{]/m.test(diagram.text)) {
    failures.push(`${diagram.where}: the diagram has no accTitle and accDescr`);
  }
  const result = await page.evaluate(
    async ([id, text]) => {
      try {
        const { svg } = await window.mermaid.render(id, text);
        return { ok: svg.includes("<svg") };
      } catch (error) {
        return { ok: false, error: String((error && error.message) || error).split("\n").slice(0, 3).join(" ") };
      }
    },
    ["diagram-" + index, diagram.text]
  );
  if (!result.ok) failures.push(`${diagram.where}: does not render: ${result.error || "no SVG"}`);
  if (diagram.where.endsWith(".mmd")) {
    const output = resolve(root, "_site/assets/diagrams", diagram.where.split("/").pop().replace(/\.mmd$/, ".svg"));
    if (!existsSync(output)) failures.push(`${diagram.where}: built SVG is missing`);
    else {
      const valid = await page.evaluate((svg) => {
        const document = new DOMParser().parseFromString(svg, "image/svg+xml");
        return !document.querySelector("parsererror") && Boolean(document.querySelector("svg[viewBox] title")) && Boolean(document.querySelector("svg desc"));
      }, readFileSync(output, "utf8"));
      if (!valid) failures.push(`${diagram.where}: built SVG is not standalone XML with an accessible title and description`);
    }
  }
}
const svgDirectory = resolve(root, "assets/diagrams");
const authoredSvgs = existsSync(svgDirectory) ? readdirSync(svgDirectory).filter((file) => file.endsWith(".svg")) : [];
for (const name of authoredSvgs) {
  const source = readFileSync(resolve(svgDirectory, name), "utf8");
  const built = resolve(root, "_site/assets/diagrams", name);
  if (!existsSync(built) || readFileSync(built, "utf8") !== source) failures.push(`${name}: the build did not preserve the approved SVG`);
  const valid = await page.evaluate(([text, name]) => {
    const doc = new DOMParser().parseFromString(text, "image/svg+xml");
    const svg = doc.querySelector("svg");
    return !doc.querySelector("parsererror") && svg?.hasAttribute("viewBox") && svg.getAttribute("role") === "img" &&
      svg.getAttribute("lang") === name.match(/-(cs|en)\.svg$/)?.[1] && Boolean(doc.querySelector("title")?.textContent) &&
      Boolean(doc.querySelector("desc")?.textContent) && !doc.querySelector("script, foreignObject, image, a") &&
      (!name.startsWith("metadata-architecture") || Boolean(doc.querySelector("[stroke-dasharray]")));
  }, [source, name]);
  if (!valid) failures.push(`${name}: invalid or inaccessible authored SVG, or lost planned-arrow distinction`);
}
await browser.close();

if (failures.length) {
  console.error(failures.map((failure) => "FAIL " + failure).join("\n"));
  console.error(`${failures.length} problem(s) in ${all.length} diagrams`);
  process.exit(1);
}
console.log(`diagram checks passed (${all.length} Mermaid diagrams, ${authoredSvgs.length} approved SVG adaptations)`);
