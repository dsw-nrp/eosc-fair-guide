// Page checks for the FAIR Data Guide, run in Chromium with Playwright:
// - the page renders from a local file without any external request on load, console error or CSP violation;
// - every station renders in every lens and language, and so do the other views;
// - axe finds no WCAG 2.2 A or AA violation in any of those views;
// - the keyboard reaches the main controls, the page reflows at 320 px, and it works inside an iframe;
// - the self-check runs without network: modes, profiles, tiers, gaps on the path, snapshot pre-fill, a shared
//   link and the exports, with no score anywhere.
// Usage: python scripts/build_site.py && npm run check:page   (set PLAYWRIGHT_BROWSERS_PATH if the browser lives outside the default cache)

import { chromium } from "playwright";
import { AxeBuilder } from "@axe-core/playwright";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
// The built site (python scripts/build_site.py): the page, its data and the API, as they are published.
const site = resolve(root, "_site");
const pageUrl = pathToFileURL(resolve(site, "index.html")).href;
const crate = JSON.parse(readFileSync(resolve(site, "ro-crate-metadata.json"), "utf8"));
const graph = crate["@graph"];
const stations = graph.filter((e) => e["@type"] === "HowToSection").map((e) => e.identifier);
const lenses = graph.filter((e) => e["@type"] === "Audience" && e["@id"].startsWith("#lens-")).map((e) => e.audienceType);
/** The result so far must stay short and never scroll on its own. */
const panelFits = (page) =>
  page.evaluate(() => {
    const panel = document.querySelector(".check-summary");
    return panel && panel.scrollHeight <= panel.clientHeight + 1 && panel.getBoundingClientRect().height <= window.innerHeight * 0.6;
  });
const lensShown = (page, lens) => page.waitForFunction((expected) => {
  const current = document.querySelector('.lens-option[aria-current="true"]');
  return current && current.dataset.lens === expected;
}, lens);
const pages = graph.filter((e) => String(e["@id"]).startsWith("#page-") && e.identifier && !e.isPartOf).map((e) => e.identifier);
const principles = graph.filter((e) => String(e["@id"]).startsWith("https://w3id.org/fair/principles/terms/") && e.termCode).map((e) => e.termCode);
const checks = graph.filter((e) => e["@type"] === "Quiz").map((e) => ({ id: e.identifier, lens: [].concat(e.audience)[0]["@id"].replace("#lens-", "") }));
const failures = [];
const fail = (message) => failures.push(message);

const browser = await chromium.launch();
/** The independent sections of the checks, run at once; each opens its own browser context. */
const sections = [];

async function openPage(viewport) {
  const context = await browser.newContext({ viewport: viewport || { width: 1280, height: 900 } });
  const page = await context.newPage();
  const external = [];
  const problems = [];
  const state = { axeRunning: false };
  page.on("request", (request) => {
    const url = request.url();
    if (!url.startsWith("file:") && !url.startsWith("data:")) external.push(url);
  });
  page.on("console", (message) => {
    // axe fetches stylesheets to inspect them; the page's own CSP blocks that, which is the page working.
    if (message.type() === "error" && !state.axeRunning) problems.push("console: " + message.text());
  });
  page.on("pageerror", (error) => problems.push("page error: " + error.message));
  page.axeState = state;
  return { context, page, external, problems };
}

async function rendered(page) {
  await page.waitForFunction(() => { const h1 = document.querySelector("#main h1"); return h1 && h1.textContent.trim() && !document.body.textContent.includes("The guide is loading."); });
}

async function axe(page, label) {
  page.axeState.axeRunning = true;
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  page.axeState.axeRunning = false;
  for (const violation of result.violations) {
    fail(`${label}: axe ${violation.id} (${violation.impact}) on ${violation.nodes.length} node(s): ${violation.nodes[0].target.join(" ")}`);
  }
}

// Controls whose content is off centre, measured on what is drawn so that a stray margin or padding shows. In a
// control on one line every icon and line of text sits on the control's middle; in a control whose label wraps, an
// icon sits on the middle of the label's first line or of the whole label, never in between. A control that aligns
// its content to the start is measured against its label's first line, which may be taller than the label's own text. A control that sizes to its content or centres it has equal space
// left and right; one wider than its content and aligned to the start is left as it is. Runs in the page.
function misalignedControls() {
  // The range of a text node's visible characters: spaces around them take room but draw nothing. Defined here
  // because only this function reaches the page.
  const inkOf = (node) => {
    const text = node.textContent;
    const range = document.createRange();
    range.setStart(node, text.search(/\S/));
    range.setEnd(node, text.trimEnd().length);
    return range;
  };
  const tolerance = 1;
  const drawn = (rect) => rect.width > 0 && rect.height > 0;
  const textLines = (node) => [...inkOf(node).getClientRects()].filter(drawn);
  const firstLine = (node) => {
    if (node.nodeType === Node.TEXT_NODE) return textLines(node)[0] || null;
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, { acceptNode: (text) => (text.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP) });
    const text = walker.nextNode();
    return text ? textLines(text)[0] || null : null;
  };
  const middle = (rect) => (rect.top + rect.bottom) / 2;
  const found = [];
  for (const control of document.querySelectorAll("button, .button, .button-small, .lens-option")) {
    const box = control.getBoundingClientRect();
    const style = getComputedStyle(control);
    if (!drawn(box) || !style.display.includes("flex") || !style.flexDirection.startsWith("row") || control.closest(".visually-hidden")) continue;
    const parts = [];
    for (const node of control.childNodes) {
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
        const lines = textLines(node);
        if (lines.length) parts.push({ node, rect: lines[0], text: true, lines: lines.length });
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const part = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        if (part.position === "absolute" || part.display === "none" || !drawn(rect)) continue;
        const line = firstLine(node);
        parts.push({ node, rect, text: Boolean(line), line, lines: line ? Math.round(rect.height / line.height) : 0 });
      }
    }
    if (!parts.length) continue;
    const name = `${control.id ? "#" + control.id : "." + String(control.className).trim().split(/\s+/)[0]} "${control.textContent.trim().slice(0, 30) || control.getAttribute("aria-label") || control.title}"`;
    const top = box.top + parseFloat(style.borderTopWidth) + parseFloat(style.paddingTop);
    const bottom = box.bottom - parseFloat(style.borderBottomWidth) - parseFloat(style.paddingBottom);
    const wraps = parts.some((part) => part.lines > 1) || ["flex-start", "start", "baseline"].includes(style.alignItems);
    const label = parts.find((part) => part.text);
    const references = wraps && label ? [middle(label.line || label.rect), middle(label.rect)] : [(top + bottom) / 2];
    const off = parts.find((part) => (!wraps || !part.text) && references.every((reference) => Math.abs(middle(part.text ? part.line || part.rect : part.rect) - reference) > tolerance));
    if (off) {
      found.push(`${name}: ${off.text ? "its text" : "an icon"} is ${(middle(off.text ? off.line || off.rect : off.rect) - references[0]).toFixed(1)} px off the middle of ${wraps ? "its first line and of its label" : "the control"}`);
      continue;
    }
    const left = Math.min(...parts.map((part) => part.rect.left)) - box.left;
    const right = box.right - Math.max(...parts.map((part) => part.rect.right));
    const padding = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight) + parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth);
    const roomy = left + right - padding > tolerance;
    const centres = ["center", "space-around", "space-evenly"].includes(style.justifyContent);
    if (Math.abs(left - right) > tolerance && (centres || !roomy)) found.push(`${name} has ${left.toFixed(1)} px on the left and ${right.toFixed(1)} px on the right`);
  }
  return found;
}

// Things drawn over each other, or touching, without a deliberate decision. Marks are what the eye separates: a line
// of text, an icon or image, a form field, and a box (a component enclosed by a border on every side, or filled with
// rounded corners); full-width bands, table cells and one-sided separators are layout, not boxes. Two marks collide
// when neither holds the other and they intersect by more than a pixel; lines of text in one block are left to the
// font, an icon counts only against text on its own line, and a box may reach into the lines around it by up to three
// pixels. Two boxes touch when they sit side by side or one above the other less than two pixels apart, and an icon
// touches the text beside it the same way. A container marked data-joined makes its parts' contact deliberate. Only
// what is shown counts: a closed disclosure shows its summary alone, and a mark is cut to the boxes that clip it.
// Something may lie over a form field only within the field's padding, such as a clear button, never over its text.
// Runs in the page.
function collisions() {
  // The range of a text node's visible characters: spaces around them take room but draw nothing. Defined here
  // because only this function reaches the page.
  const inkOf = (node) => {
    const text = node.textContent;
    const range = document.createRange();
    range.setStart(node, text.search(/\S/));
    range.setEnd(node, text.trimEnd().length);
    return range;
  };
  const found = [];
  const drawn = (rect) => rect.width > 1 && rect.height > 1;
  const viewport = document.documentElement.clientWidth;
  const styles = new Map();
  const css = (element) => styles.get(element) || styles.set(element, getComputedStyle(element)).get(element);
  const clear = (color) => color === "transparent" || /rgba\([^)]*,\s*0\)$/.test(color);
  const enclosed = (style) => ["Top", "Right", "Bottom", "Left"].every((side) => parseFloat(style[`border${side}Width`]) > 0 && !clear(style[`border${side}Color`]));
  const filledRound = (style) => !clear(style.backgroundColor) && parseFloat(style.borderTopLeftRadius) > 0;
  const marks = [];
  const cut = (rect, clip) => {
    const left = Math.max(rect.left, clip.left);
    const top = Math.max(rect.top, clip.top);
    const right = Math.min(rect.right, clip.right);
    const bottom = Math.min(rect.bottom, clip.bottom);
    return { left, top, right, bottom, width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
  };
  const everywhere = { left: -Infinity, top: -Infinity, right: Infinity, bottom: Infinity };
  (function walk(element, block, clip) {
    const style = css(element);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0" || element.classList.contains("visually-hidden") || element.classList.contains("sprite") || ["SCRIPT", "STYLE", "TEMPLATE"].includes(element.tagName)) return;
    const own = style.display === "inline" || style.display === "contents" ? block : element;
    const rect = cut(element.getBoundingClientRect(), clip);
    const tag = element.tagName.toLowerCase();
    if (tag === "details" && !element.open) {
      const summary = element.querySelector(":scope > summary");
      if (summary) walk(summary, own, clip);
      return;
    }
    const clips = style.overflowX !== "visible" || style.overflowY !== "visible" || (style.position === "absolute" && style.clip !== "auto");
    const inner = clips ? cut(element.getBoundingClientRect(), clip) : clip;
    if (clips && !drawn(inner)) return;
    if (tag === "svg") {
      if (drawn(rect)) marks.push({ kind: "icon", node: element, rect, block: own === element ? block : own });
      return;
    }
    if (["img", "input", "select", "textarea"].includes(tag)) {
      if (drawn(rect)) marks.push({ kind: "box", node: element, rect, block });
      return;
    }
    if (drawn(rect) && rect.width < 0.9 * viewport && !style.display.startsWith("table") && (enclosed(style) || filledRound(style))) marks.push({ kind: "box", node: element, rect, block });
    for (const child of element.childNodes) {
      if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
        for (const line of inkOf(child).getClientRects()) {
          const shown = cut(line, inner);
          if (drawn(shown)) marks.push({ kind: "text", node: child, rect: shown, block: own });
        }
      } else if (child.nodeType === Node.ELEMENT_NODE) walk(child, own, inner);
    }
  })(document.body, document.body, everywhere);
  const element = (mark) => (mark.node.nodeType === Node.TEXT_NODE ? mark.node.parentElement : mark.node);
  const holds = (a, b) => a.node.contains(b.node) || b.node.contains(a.node);
  const joined = (a, b) => {
    let common = element(a);
    while (common && !common.contains(b.node)) common = common.parentElement;
    return Boolean(common && common.closest("[data-joined]"));
  };
  // Whether a mark reaches into a field's text area, the box inside its border and padding.
  const overField = (field, mark) => {
    const style = css(field.node);
    const box = field.node.getBoundingClientRect();
    const left = box.left + parseFloat(style.borderLeftWidth) + parseFloat(style.paddingLeft);
    const right = box.right - parseFloat(style.borderRightWidth) - parseFloat(style.paddingRight);
    return mark.rect.left < right - 1 && mark.rect.right > left + 1;
  };
  const describe = (mark) => {
    const text = (mark.node.textContent || "").trim().replace(/\s+/g, " ").slice(0, 24);
    const owner = element(mark);
    const label = owner.id ? "#" + owner.id : owner.classList.length ? "." + owner.classList[0] : owner.tagName.toLowerCase();
    return mark.kind === "text" ? `"${text}"` : `${mark.kind} ${label}${text ? ` "${text}"` : ""}`;
  };
  marks.sort((a, b) => a.rect.top - b.rect.top);
  for (let i = 0; i < marks.length; i += 1) {
    const a = marks[i];
    for (let j = i + 1; j < marks.length && marks[j].rect.top < a.rect.bottom + 2; j += 1) {
      const b = marks[j];
      if (holds(a, b)) continue;
      const across = Math.min(a.rect.right, b.rect.right) - Math.max(a.rect.left, b.rect.left);
      const down = Math.min(a.rect.bottom, b.rect.bottom) - Math.max(a.rect.top, b.rect.top);
      const sameBlock = a.block === b.block;
      const icon = a.kind === "icon" ? a : b.kind === "icon" ? b : null;
      const text = a.kind === "text" || b.kind === "text";
      if (across > 1 && down > 1) {
        if (a.kind === "text" && b.kind === "text" && sameBlock) continue;
        if (icon && sameBlock && down < icon.rect.height / 2) continue;
        if (text && (a.kind === "box" || b.kind === "box") && down <= 3) continue;
        const field = [a, b].find((mark) => ["INPUT", "TEXTAREA"].includes(mark.node.tagName));
        if (field && !overField(field, field === a ? b : a)) continue;
        if (!joined(a, b)) found.push(`${describe(a)} overlaps ${describe(b)}`);
        continue;
      }
      const sideBySide = down > Math.min(a.rect.height, b.rect.height) / 2 && across > -2;
      const stacked = across > Math.min(a.rect.width, b.rect.width) / 2 && down > -2;
      const boxes = a.kind === "box" && b.kind === "box";
      const iconBesideText = icon && text && sameBlock && sideBySide;
      if (((boxes && (sideBySide || stacked)) || iconBesideText) && !joined(a, b)) found.push(`${describe(a)} touches ${describe(b)}`);
    }
  }
  return found;
}

// 1. Load from a local file: no external request, no error.
sections.push(["page", async () => {
  const { context, page, external, problems } = await openPage();
  await page.goto(pageUrl);
  await rendered(page);
  if (external.length) fail("requests on load: " + external.join(", "));
  for (const problem of problems) fail("load: " + problem);
  const heading = await page.textContent("#main h1");
  if (!heading.includes("Průvodce FAIR daty")) fail("first visit does not open the landing: " + heading);
  // The page icon is the EOSC CZ symbol, as the FIP Dashboard uses it, served from the page's own files.
  for (const rel of ["icon", "apple-touch-icon"]) {
    const href = await page.locator(`head link[rel="${rel}"]`).getAttribute("href");
    if (!href || /^[a-z]+:/i.test(href) || !existsSync(resolve(root, href))) fail(`page icon: the ${rel} link is missing or not a file of the page: ${href}`);
  }
  if (!(await page.locator("#search-input").count())) fail("landing: no search box");
  if (!(await page.locator("#stage-question").textContent()).includes("Kde se právě nacházíte")) fail("landing: no stage question");
  if ((await page.locator(".stage-card").count()) !== 4) fail("landing: the four stage cards are missing");
  if (!(await page.locator(".stage-card").first().textContent()).includes("Krok 1")) fail("landing: the stage cards do not name the steps they cover");
  if (await page.locator(".stage-current").count()) fail("landing: a first visit marks a current stage");
  if (!(await page.locator(".tasks .task").count())) fail("landing: no task shortcuts");
  const stageWeights = await page.locator(".stage-card").first().evaluate((card) => [getComputedStyle(card.querySelector("strong")).fontWeight, getComputedStyle(card.querySelector(".small")).fontWeight]);
  if (Number(stageWeights[1]) >= Number(stageWeights[0]) || Number(stageWeights[1]) > 400) fail("landing: a stage card's description is as bold as its title: " + stageWeights.join("/"));
  await axe(page, "landing");

  // The catalogue: one menu item over one list narrowed by facets with counts. Kind is a single choice, and older
  // addresses select their kind; every kind lists its entries; resources and cited sources
  // are one kind marked by usage; a facet keeps focus and puts the state in the address, which opens the same list;
  // station and principle apply across kinds and say when a kind lacks them; the reader orders the list and groups
  // follow; changes name no people; the page for machines links the knowledge base.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const menu = async () => view.locator(".main-nav a").evaluateAll((links) => links.map((link) => link.textContent.trim()));
    const current = async () => (await view.locator('.main-nav [aria-current="page"]').textContent()).trim();
    const kinds = async () => view.locator('[data-facet="kind"] input:checked').evaluateAll((boxes) => boxes.map((box) => box.id.replace("facet-kind-", "")).join(","));
    const found = async () => Number(((await view.locator(".catalogue-count").textContent()).match(/\d+/) || [0])[0]);
    const open = async (hash) => {
      await view.goto(pageUrl + hash);
      await view.waitForSelector(".catalogue-layout");
    };
    await open("#/cs/V/resources");
    const items = await menu();
    if (!items.includes("Katalog") || items.includes("Zdroje") || items.includes("Repozitáře")) fail("catalogue: the menu does not hold one catalogue item in place of the finders: " + items.join(", "));
    if ((await current()) !== "Katalog" || (await kinds()) !== "resources") fail("catalogue: the resources address does not select the resources: " + (await kinds()));
    await open("#repositories");
    if ((await kinds()) !== "repositories") fail("catalogue: an in-page link to the repositories does not select them");
    for (const [old, kind] of [["sources", "resources"], ["clauses", "clauses"], ["questions", "questions"], ["terms", "terms"], ["fips", "fips"], ["tests", "tests"], ["actions", "actions"]]) {
      await open("#/cs/V/catalogue/" + old);
      if ((await kinds()) !== kind) fail(`catalogue: the address for ${old} does not select ${kind}`);
      if (!(await view.locator(".catalogue-results .card").count())) fail(`catalogue: ${kind} list nothing`);
    }
    if ((await view.locator('[data-facet="kind"] input[type="radio"]').count()) !== 8) fail("catalogue: the kind is not a single choice among eight");
    const toolbarGap = await view.evaluate(() => {
      const bar = document.querySelector(".catalogue-toolbar");
      return bar.nextElementSibling.getBoundingClientRect().top - bar.getBoundingClientRect().bottom;
    });
    if (toolbarGap < 8) fail(`catalogue: the ordering control touches the content below it (${toolbarGap}px)`);
    const changes = await view.locator(".catalogue-results").textContent();
    if (/Novák|Claude/.test(changes)) fail("catalogue: the content changes name people or tools");
    const drewOn = await view.locator(".change", { hasText: "FAIRsharing" }).first().textContent();
    if ((drewOn.match(/FAIRsharing/g) || []).length > 4) fail("catalogue: a change lists one source more than once: " + drewOn);
    await open("#/cs/V/catalogue/terms");
    if (!(await view.locator(".term-card h3").first().textContent()).match(/^[^[(]/)) fail("catalogue: the glossary does not sort past leading brackets");

    // Resources and cited sources as one kind, marked by how the guide uses them.
    await open("#/cs/V/catalogue/resources");
    // Where the guide uses an entry is one row, stations by icon and name, then checks; its details (publisher,
    // language, version, date) are one quiet line, not badges.
    const analysisCard = view.locator(".card", { hasText: "Analýza a návrh postupů" }).first();
    const analysis = await analysisCard.textContent();
    const used = analysisCard.locator(".relations dd").nth(0);
    if (!(await analysisCard.locator(".entry-head").textContent()).includes("podklad obsahu") || !(await used.locator("a.holder-link", { hasText: "Plán" }).count()) || !analysis.includes("Zralost FAIR repozitáře")) fail("catalogue: the analysis is not marked as a basis with the stations and checks that cite it");
    if ((await analysisCard.locator(".relations dt", { hasText: "V průvodci" }).count()) !== 1 || !(await analysisCard.locator(".card-details").textContent()).includes("verze 1.2") || (await analysisCard.locator(".badge", { hasText: "verze" }).count())) fail("catalogue: the analysis card does not keep where it is used in one row and its details out of the badges");
    // A kind's own facets list their values by number of records, most first.
    const counts = await view.locator('[data-facet="resources-use"] .facet-count').allTextContents();
    if (counts.join(",") !== counts.map(Number).sort((a, b) => b - a).join(",")) fail("catalogue: a kind's facet is not ordered by number of records: " + counts.join(","));
    const both = await view.locator(".card", { hasText: "AI jako služba (CERIT)" }).first().textContent();
    if (!both.includes("doporučuje průvodce") || !both.includes("podklad obsahu")) fail("catalogue: a resource that is also cited is not marked with both uses");

    // Facets: a choice keeps focus and goes into the address; the kind replaces the previous one; counts follow.
    await view.locator("#facet-kind-clauses").check();
    await view.waitForFunction(() => location.hash.includes("k!clauses"));
    if ((await view.evaluate(() => document.activeElement && document.activeElement.id)) !== "facet-kind-clauses") fail("catalogue: the kind picker does not keep focus");
    if ((await kinds()) !== "clauses" || (await view.locator(".clause-card").count()) !== (await view.locator(".catalogue-results .card").count())) fail("catalogue: choosing a kind does not replace the previous one");
    const before = await found();
    await view.locator("#facet-station-licence").check();
    await view.waitForFunction(() => location.hash.includes("s!licence"));
    if (!((await found()) > 0 && (await found()) < before)) fail("catalogue: the station facet does not narrow the list");
    if (!(await view.locator('[data-facet="kind"] li', { hasText: "Profily FIP" }).textContent()).includes("nemají zastávku")) fail("catalogue: a kind without stations does not say why it shows none");
    // The chosen kind's own filter holds for no other kind: the others count none and say why.
    await view.locator("#facet-clauses-ckind-recommendation").check();
    await view.waitForFunction(() => location.hash.includes("f.ckind!recommendation"));
    const otherKind = view.locator('[data-facet="kind"] li', { hasText: "Zdroje" });
    if ((await otherKind.locator(".facet-count").textContent()) !== "0" || !(await view.locator('[data-facet="kind"] > .facet-note').textContent()).includes("platí jen pro druh Požadavky")) fail("catalogue: another kind is counted under a filter of the chosen kind, or the picker does not say why");
    await view.locator("#facet-clauses-ckind-recommendation").uncheck();
    await view.waitForFunction(() => !location.hash.includes("f.ckind!recommendation"));
    await view.locator("#catalogue-order").selectOption("principle");
    await view.waitForFunction(() => location.hash.includes("o!principle"));
    if (!(await view.locator(".catalogue-group > h2").count())) fail("catalogue: ordering by principle does not group the list");
    const address = await view.evaluate(() => location.hash);
    const count = await found();
    await view.goto("about:blank");
    await open(address);
    if ((await found()) !== count || (await kinds()) !== "clauses") fail("catalogue: the address does not reopen the same list");
    await view.locator("#facet-kind-resources").check();
    await view.waitForFunction(() => location.hash.includes("k!resources"));
    if (!(await view.evaluate(() => location.hash.includes("s!licence")))) fail("catalogue: changing the kind drops the station");
    await view.locator("#facet-kind-clauses").check();
    await view.waitForFunction(() => location.hash.includes("k!clauses"));
    await view.locator("#catalogue-search").fill("licence");
    await view.waitForFunction(() => location.hash.includes("q!licence"));
    if (!((await found()) > 0 && (await found()) < count)) fail("catalogue: the search does not narrow the list");
    await view.locator(".active-filters .button-link").click();
    await view.waitForFunction(() => !location.hash.includes("s!licence") && !location.hash.includes("q!"));
    // Typing with pauses renders the list again after each pause; the field keeps the text in order, its spaces, and
    // the caret where it was, also when editing in the middle.
    const typed = async (keys) => {
      for (const key of keys) {
        await view.keyboard.press(key);
        await view.waitForTimeout(400);
      }
      return view.evaluate(() => ({ id: document.activeElement.id, value: document.activeElement.value, caret: document.activeElement.selectionStart }));
    };
    await view.locator("#catalogue-search").fill("");
    await view.locator("#catalogue-search").focus();
    let field = await typed([..."open sci"].map((char) => (char === " " ? "Space" : char)));
    if (field.id !== "catalogue-search" || field.value !== "open sci" || field.caret !== 8) fail("catalogue: typing with pauses does not keep the text, its space and the caret: " + JSON.stringify(field));
    field = await typed(["ArrowLeft", "ArrowLeft", "ArrowLeft", "x"]);
    if (field.value !== "open xsci" || field.caret !== 6) fail("catalogue: editing the search in the middle loses the caret: " + JSON.stringify(field));
    await view.locator("#catalogue-search").fill("");
    await view.waitForFunction(() => !location.hash.includes("q!"));

    // In English, titles and badges carry no Czech outside an original title marked as Czech, and a work the guide
    // only cites shows its original title with the translation in brackets; in Czech the original stands alone.
    const openAll = async (hash) => {
      await open(hash);
      while (await view.locator(".catalogue-more").count()) await view.locator(".catalogue-more").first().click();
    };
    await openAll("#/en/V/catalogue/resources");
    const czechOutside = await view.evaluate(() => {
      const czech = /[ěščřžůťďňáéíóúý]/i;
      const found = [];
      for (const holder of document.querySelectorAll(".catalogue-results .card h3, .catalogue-results .card .badge")) {
        const walker = document.createTreeWalker(holder, NodeFilter.SHOW_TEXT);
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
          if (czech.test(node.textContent) && node.parentElement.closest("[lang]").getAttribute("lang") !== "cs") found.push(node.textContent.trim());
        }
      }
      return found;
    });
    if (czechOutside.length) fail("catalogue: Czech names in English titles or badges: " + czechOutside.slice(0, 5).join(" | "));
    const surveyTitle = async () => (await view.locator(".card h3", { hasText: "Stav správy výzkumných dat" }).first().textContent()).trim();
    if (!(await surveyTitle()).includes("[State of research data management in the Czech Republic 2025]")) fail("catalogue: a cited Czech work does not show its translated title in English: " + (await surveyTitle()));
    await openAll("#/cs/V/catalogue/resources");
    if ((await surveyTitle()).includes("[")) fail("catalogue: in Czech a Czech work shows a translation: " + (await surveyTitle()));

    // No shared facet shows only zeros: a kind whose entries carry no station or principle shows no such facet or
    // order; FIP profiles take principles from their declarations, content changes the places of what they changed.
    for (const kind of ["resources", "repositories", "clauses", "questions", "terms", "fips", "tests", "actions"]) {
      await open("#/cs/V/catalogue/" + kind);
      const empty = await view.evaluate(() =>
        ["station", "principle"].filter((name) => {
          const group = document.querySelector(`[data-facet="${name}"]`);
          return group && ![...group.querySelectorAll(".facet-count")].some((node) => Number(node.textContent) > 0);
        })
      );
      if (empty.length) fail(`catalogue: ${kind} shows a facet with only zeros: ${empty.join(", ")}`);
    }
    await open("#/cs/V/catalogue/fips");
    if (!(await view.locator('[data-facet="principle"]').count()) || (await view.locator('[data-facet="station"]').count())) fail("catalogue: FIP profiles do not filter by principle alone");
    await open("#/cs/V/catalogue/actions");
    if (!(await view.locator('[data-facet="station"]').count())) fail("catalogue: content changes do not filter by the stations they changed");

    // Finders: resources order by type, status or the date their status was checked, oldest first, and keep their
    // orientation tags; repositories order by data source and link each source to its record; while NKR lists no
    // repository, sample records built from re3data facts show on request, labelled as samples.
    await open("#/cs/V/catalogue/resources");
    const groupNames = async () => (await view.locator(".catalogue-group > h2").allTextContents()).map((name) => name.split(" · ")[0]);
    const orderBy = async (order) => {
      await view.locator("#catalogue-order").selectOption(order);
      await view.waitForFunction((value) => location.hash.includes("o!" + value), order);
      return groupNames();
    };
    const checkedGroups = await orderBy("checked");
    const checkedDates = checkedGroups.filter((name) => name.startsWith("Ověřeno")).map((name) => name.replace("Ověřeno ", "").split(". ").reverse().map((part) => part.padStart(2, "0")).join(""));
    if (!checkedDates.length || checkedDates.some((date, index) => index && date < checkedDates[index - 1]) || checkedGroups[checkedGroups.length - 1] !== "Bez data ověření") fail("finders: ordering by the date checked does not put the oldest first: " + checkedGroups.join(" | "));
    if (!(await view.locator(".catalogue-results .card .relations .audience svg.icon").count()) || !(await view.locator(".catalogue-results .card .relations .principle-tile").count())) fail("finders: resource cards lack their audiences (icon and name) and principle tiles");
    const typeGroups = await orderBy("type");
    if (new Set(typeGroups).size !== typeGroups.length) fail("finders: a type shows as two groups: " + typeGroups.join(" | "));
    const moreTypes = view.locator('[data-facet="resources-type"] button');
    if (await moreTypes.count()) await moreTypes.first().click();
    const typeValues = await view.locator('[data-facet="resources-type"] .facet-label').allTextContents();
    if (new Set(typeValues).size !== typeValues.length) fail("finders: the type facet offers one type twice: " + typeValues.join(" | "));
    // One vocabulary of types for resources, cited sources and FIP Dashboard records, written as categories are.
    if (typeValues.some((value) => /^\p{Lu}/u.test(value) && !/^\p{Lu}{2,}/u.test(value)) || typeValues.length > 15) fail("finders: the types are not one vocabulary in lower case: " + typeValues.join(" | "));
    const statusGroups = await orderBy("status");
    if (statusGroups[0] !== "provozní" || statusGroups[statusGroups.length - 1] !== "Bez stavu") fail("finders: statuses are not in their own order: " + statusGroups.join(" | "));
    await open("#/cs/V/catalogue/repositories");
    if ((await orderBy("rsource"))[0] !== "výběr průvodce") fail("finders: ordering repositories by data source does not start with the guide's selection");
    if (!(await view.locator('.relations a[href^="https://www.re3data.org/repository/r3d"]').count())) fail("finders: a repository's re3data source does not link to its record");
    await view.evaluate(() => { window.FairGuide.live.fetchJson = async () => ({ results: [] }); });
    if (await view.locator("#nkr-samples").count()) fail("finders: sample NKR records are offered before NKR was asked");
    await view.locator("#nkr-load").click();
    await view.waitForSelector("#nkr-samples");
    if (await view.locator(".nkr-sample").count()) fail("finders: sample NKR records show without being asked for");
    await view.locator("#nkr-samples").click();
    await view.waitForSelector(".nkr-sample");
    if ((await view.locator(".nkr-sample").count()) !== 3 || (await view.locator(".nkr-sample .sample-label").count()) !== 3) fail("finders: three sample records are not each labelled as samples");
    if (!(await view.locator(".nkr-samples .notice").textContent()).includes("ne záznamy NKR")) fail("finders: the samples do not say they are not NKR records");
    const lindat = await view.locator(".nkr-sample", { hasText: "LINDAT" }).textContent();
    if (!lindat.includes("OAI-PMH") || !lindat.includes("neuvedeno")) fail("finders: a sample record does not show re3data's values and what re3data does not state");
    if ((await view.evaluate(() => document.activeElement && document.activeElement.id)) !== "nkr-samples") fail("finders: showing the samples moves focus away from the control");

    // Content from the EOSC CZ website: each step's training is a line among the help routes, not a resource card;
    // the identifier callout leads with scripted verification; the About page links the introductory courses; the
    // repository finder lists the added general-purpose and domain repositories.
    await view.goto(pageUrl + "#/cs/V/path/prace");
    await view.waitForSelector("#main h1");
    const training = view.locator("li.training");
    if ((await training.locator("a").count()) !== 3 || !(await training.textContent()).startsWith("Školení k tomuto kroku")) fail("training: the Práce step does not list its three trainings in one line");
    if (await view.locator('.cards .card a[href*="eosc.cz/skoleni/"]').count()) fail("training: a training shows as a resource card as well");
    await view.goto(pageUrl + "#/cs/V/path/popis");
    await view.waitForSelector("#main h1");
    await view.locator(".callout-verify-identifiers summary").click();
    const steps = await view.locator(".callout-verify-identifiers ol li").allTextContents();
    if (!steps[0].includes("Ověřit identifikátory") || !steps[1].includes("skript")) fail("identifier callout: it does not lead with the helper and a script: " + steps.slice(0, 2).join(" | "));
    await view.goto(pageUrl + "#/cs/V/page/about");
    await view.waitForSelector("#main h1");
    if (!(await view.locator('a.text-ref[href$="/catalogue/resources/training-overview"]').count())) fail("about: the introductory courses are not linked");
    await open("#/cs/V/catalogue/repositories");
    for (const name of ["Dryad", "Harvard Dataverse", "Molecular Biophysics Database (MBDB)"]) {
      if (!(await view.locator(".catalogue-results .card h3", { hasText: name }).count())) fail("repositories: " + name + " is not listed");
    }

    // Exports: every view but a single check offers printing under it, and its content as data where it has a record
    // in the API; the whole crate is on the page for machines. The catalogue saves the filtered list it shows as CSV
    // and as data, a station saves itself as Markdown, and printing opens closed sections.
    const exportIds = async () => view.evaluate(() => [...document.querySelectorAll(".export-bar .export-actions > *")].map((node) => node.id).join(","));
    const exportData = async () => view.evaluate(() => (document.getElementById("export-data") || {}).getAttribute?.("href") || "");
    for (const [hash, expected, record] of [
      ["#/cs/V/path/start", "export-print"],
      ["#/cs/V/explorer", "export-print"],
      ["#/cs/V/page/about", "export-print"],
      ["#/cs/V/tools", "export-print"],
      ["#/cs/V/check", "export-data,export-print", "api/checks.json"],
      ["#/cs/V/explorer/R1.1", "export-data,export-print", "api/principles/R1.1.json"],
      ["#/cs/V/path/licence", "export-markdown,export-data,export-print", "api/stations/licence.json"],
    ]) {
      await view.goto(pageUrl + hash);
      await view.waitForSelector("#main h1");
      if ((await exportIds()) !== expected) fail(`exports: ${hash} offers ${await exportIds()} instead of ${expected}`);
      if (record && ((await exportData()) !== record || !existsSync(resolve(root, "_site", record)))) fail(`exports: ${hash} does not offer its record ${record} as data, or it is not built`);
    }
    await view.goto(pageUrl + "#/cs/V/path/licence");
    await view.waitForSelector("#main h1");
    if (!(await view.locator('a[href="#/cs/V/catalogue/k!actions~s!licence"]').count())) fail("paradata: the station does not lead to its changes in the catalogue");
    await view.goto(pageUrl + "#/cs/V/check/dataset");
    await view.waitForSelector("#main h1");
    if (await view.locator(".export-bar").count()) fail("exports: a single check shows the shared export bar beside its own exports");
    await view.goto(pageUrl + "#/cs/DS/check/institution");
    await view.waitForSelector("#export-data");
    if ((await view.locator("#export-data").getAttribute("href")) !== "api/checks/institution.json") fail("exports: a single check does not offer its benchmark record as data");
    const saved = async (id) => {
      const [download] = await Promise.all([view.waitForEvent("download"), view.locator("#export-" + id).click()]);
      return { name: download.suggestedFilename(), text: readFileSync(await download.path(), "utf8") };
    };
    await open("#/en/V/catalogue/k!resources~s!licence");
    const listed = await found();
    const csv = await saved("csv");
    const csvRows = csv.text.replace(/^\ufeff/, "").trim().split("\r\n");
    if (!csvRows[0].includes("Record in the API")) fail("exports: the CSV does not carry each entry's record");
    if (!/^fair-guide-catalogue-resources-\d{4}-\d{2}-\d{2}\.csv$/.test(csv.name) || !csvRows[0].startsWith("Identifier,Name,") || !csvRows[0].includes("Address") || !csvRows[0].includes("Status")) fail("exports: the CSV is not named or headed as expected: " + csv.name + " " + csvRows[0]);
    if (csvRows.length - 1 !== listed || !csvRows.slice(1).every((row) => row.includes("https://"))) fail(`exports: the CSV does not hold exactly the ${listed} filtered entries with their addresses (${csvRows.length - 1} rows)`);
    const json = JSON.parse((await saved("json")).text);
    // The list as data has the shape of the API's lists; each entry names its record at the page's address, which for a
    // local file is the configured one and maps onto the built site.
    const configured = await view.evaluate(() => window.FairGuide.config.pageUrl);
    const inBuilt = (id) => String(id).startsWith(configured) && existsSync(resolve(root, "_site", String(id).slice(configured.length)));
    if (json["@type"] !== "ItemList" || json.numberOfItems !== listed || json.itemListElement.length !== listed || !String(json["@id"]).includes("s!licence") || !String(json["@context"]).endsWith("api/context.jsonld")) fail("exports: the list as data is not an ItemList of the filtered entries naming its filters");
    if (!json.itemListElement.every((item) => item.identifier && item.name && inBuilt(item["@id"]))) fail("exports: an entry of the list as data does not name its record in the API");
    await view.goto(pageUrl + "#/en/DS/path/licence");
    await view.waitForSelector("#main h1");
    const markdown = await saved("markdown");
    if (!markdown.name.startsWith("fair-guide-station-licence-DS-en-") || !markdown.text.startsWith("# Licence and access") || !markdown.text.includes("\n## How to do it\n") || !markdown.text.includes("#/en/DS/path/licence")) fail("exports: the station's Markdown lacks its title, levels or address: " + markdown.name);
    if (/\n\n\n/.test(markdown.text)) fail("exports: the station's Markdown has empty runs of lines");
    if (!markdown.text.includes("\n  What to check: ") || !markdown.text.includes("\n  ```text\n") || !markdown.text.includes("Always verify what AI produces.")) fail("exports: the station's Markdown lacks an AI tip's check, prompt or reminder");
    // Copying a prompt: the button says it copied, or, where the clipboard is refused, the prompt is selected.
    await view.evaluate(() => { document.querySelector('#main details[data-key="ai"]').open = true; });
    const prompt = view.locator("#main .ai-prompt").first();
    await prompt.locator("button").click();
    await view.waitForTimeout(100);
    const copied = await prompt.evaluate((block) => ({ label: block.querySelector(".copy-label").textContent, selected: window.getSelection().toString().trim(), text: block.querySelector("pre").textContent.trim() }));
    if (copied.label !== "Copied" && copied.selected !== copied.text) fail(`exports: copying a prompt neither copies nor selects it (${copied.label})`);
    const closed = await view.locator("#main details:not([open])").count();
    await view.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
    if (!closed || (await view.locator("#main details:not([open])").count())) fail("exports: printing does not open the closed sections");
    await view.evaluate(() => window.dispatchEvent(new Event("afterprint")));
    if ((await view.locator("#main details:not([open])").count()) !== closed) fail("exports: the sections opened for printing do not close again");

    // Links from text: a step that names DataCite links the name to its catalogue entry, quietly, and the crate
    // records DataCite as mentioned by the step, with no markup in the text.
    await view.goto(pageUrl + "#/cs/V/path/dohledatelnost");
    await view.waitForSelector("#main h1");
    await view.locator('details[data-key="L1"] > summary').click();
    const named = view.locator('details[data-key="L1"] a.text-ref', { hasText: "DataCite" }).first();
    if (!(await named.count()) || !(await named.getAttribute("href")).endsWith("/catalogue/resources/datacite")) fail("text links: DataCite in a step does not link to its catalogue entry");
    const quiet = await named.evaluate((link) => getComputedStyle(link).color === getComputedStyle(link.parentElement).color && getComputedStyle(link).textDecorationStyle === "dotted");
    if (!quiet) fail("text links: a link in text does not keep the text's colour with a dotted underline");
    const step = crate["@graph"].find((entity) => entity["@id"] === "#advice-dohledatelnost.V.L1.2-step-3");
    if (!step || JSON.stringify(step.text).includes("[[") || !JSON.stringify(step.mentions).includes("#resource-datacite")) fail("text links: the crate does not record DataCite as mentioned by the step with clean text");
    if (JSON.stringify(crate).includes("[[")) fail("text links: reference markup reached the crate");
    await named.click();
    await view.waitForSelector("#item-datacite.jumped");

    await view.goto(pageUrl + "#/cs/V/page/machines");
    await view.waitForSelector("#main h1");
    // The page sits in the header: its button is marked while it is open, no main-menu item is, and the header also
    // links the source repository.
    if (await view.locator('.main-nav [aria-current="page"]').count()) fail("machines: a main-menu item is marked although the page sits in the header");
    if ((await view.locator('.site-header a.header-page[aria-current="page"]').textContent()).trim() !== "Data pro stroje") fail("machines: the header's button is not marked while the page is open");
    if (!(await view.locator('.site-header a.header-repository[href^="https://github.com/"]').count())) fail("header: the source repository is not linked");
    if (!(await view.locator('.machine-tasks a[href="ro-crate-metadata.json"]').count())) fail("machines: the page does not offer the knowledge base");
    // A data steward who wants one record finds its address pattern and a working example, and how the guide itself
    // uses the same means: its signposts, read from the same list as the head and the linkset.
    const example = await view.locator(".machine-tasks a[href$='principles/R1.1.json']").getAttribute("href");
    if (!example || !existsSync(resolve(root, "_site", example)) || !(await view.locator(".machine-tasks code", { hasText: "<id>.json" }).count())) fail("machines: the task table does not show a record's pattern and a working example");
    const shown = await view.locator(".signposts tbody tr").evaluateAll((rows) => rows.map((row) => row.querySelector("code").textContent + " " + row.querySelector("td a").getAttribute("href")).sort());
    const head = await view.locator("head link[rel]").evaluateAll((links) => links.filter((link) => !["stylesheet", "icon", "apple-touch-icon"].includes(link.rel)).map((link) => link.getAttribute("rel") + " " + link.getAttribute("href")).sort());
    if (shown.join("|") !== head.join("|")) fail("machines: the signposts the page shows differ from the head's: " + shown.join(", ") + " vs " + head.join(", "));
    const linkset = JSON.parse(readFileSync(resolve(site, "linkset.json"), "utf8")).linkset[0];
    const listed2 = Object.entries(linkset).filter(([rel]) => rel !== "anchor").flatMap(([rel, targets]) => targets.map((target) => rel + " " + target.href));
    if (linkset.anchor !== "./" || listed2.sort().join("|") !== head.filter((link) => !link.startsWith("linkset ")).join("|")) fail("signposting: the linkset does not list the head's links, anchored at the site");
    // The standards the knowledge base follows are linked: RO-Crate and Process Run Crate to their catalogue entries,
    // the guide's profile to its landing page at its own address, which the build writes so the identifier resolves.
    const practice = view.locator("#practice");
    for (const id of ["ro-crate", "process-run-crate"]) {
      if (!(await practice.locator(`a.text-ref[href$="/catalogue/resources/${id}"]`).count())) fail(`machines: the practice section does not link ${id} to its catalogue entry`);
    }
    const profileHref = await practice.locator('a.text-ref[href^="profile/"]').getAttribute("href");
    if (!profileHref || !existsSync(resolve(site, profileHref, "index.html"))) fail("machines: the guide's profile is not linked to its landing page: " + profileHref);
    for (const rel of ["describedby", "service-desc", "service-doc", "license", "type", "author", "linkset"]) {
      if (!head.some((link) => link.startsWith(rel + " "))) fail("signposting: the head has no " + rel + " link");
    }
    if (!(await view.locator('head link[rel="describedby"][href="ro-crate-metadata.json"]').count())) fail("machines: the head does not carry the describedby link");
    // The API (built into _site/ by scripts/build_site.py): typed links in the head lead to its description and its
    // documentation, and the page lists every collection as an accessible counterpart of the documentation.
    const inSite = (href) => Boolean(href) && !/^[a-z]+:/i.test(href) && existsSync(resolve(site, href.endsWith("/") ? href + "index.html" : href));
    for (const rel of ["service-desc", "service-doc"]) {
      const href = await view.locator(`head link[rel="${rel}"]`).getAttribute("href");
      if (!inSite(href)) fail(`machines: the ${rel} link does not lead to the built API: ${href}`);
    }
    const endpoints = await view.locator(".endpoints tbody td:first-of-type a").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    const collections = await view.evaluate(() => window.FairGuide.config.api.collections.length);
    if (endpoints.length !== collections + 2 || !endpoints.every(inSite)) fail("machines: the endpoint list does not name every collection of the built API: " + endpoints.join(" "));
    // Every catalogue entry links to its record in the API; the NKR samples are illustrations, not entries.
    for (const kind of ["resources", "repositories", "clauses", "questions", "terms", "fips", "tests", "actions"]) {
      await view.goto(pageUrl + "#/cs/V/catalogue/" + kind);
      await view.waitForFunction((id) => { const radio = document.getElementById(id); return radio && radio.checked && document.querySelector(".catalogue .card"); }, "facet-kind-" + kind);
      const unlinked = await view.locator(".catalogue .card:not(.nkr-sample)").evaluateAll((cards) => cards.filter((card) => !card.querySelector(".json-link")).map((card) => card.id || card.textContent.trim().slice(0, 40)));
      const records = await view.locator(".catalogue .card .json-link").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
      if (unlinked.length || !records.every(inSite)) fail(`catalogue: ${kind} entries without a record in the API, or a link that leads nowhere: ${unlinked.join(", ")}`);
      const corner = await view.locator(".catalogue .card .json-link").first().evaluate((link) => {
        const box = link.getBoundingClientRect();
        const card = link.closest(".card").getBoundingClientRect();
        return box.top - card.top < 40 && card.right - box.right < 40;
      });
      if (!corner) fail(`catalogue: the ${kind} record link does not sit in the card's top right corner`);
      // One card for every kind: its own identifier in the head, and its relations under fixed labels in one order.
      const order = ["Principy", "Pro koho", "Vychází z", "V průvodci", "Identifikátory"];
      const cards = await view.locator(".catalogue .card:not(.nkr-sample)").evaluateAll((all) =>
        all.map((card) => ({ id: card.id, chip: (card.querySelector(".entry-head .id-chip-static") || {}).textContent, labels: [...card.querySelectorAll(".relations dt")].map((dt) => dt.textContent) }))
      );
      const wrong = cards.filter((card) => "item-" + card.chip !== card.id || card.labels.some((label, index) => !order.includes(label) || (index && order.indexOf(label) <= order.indexOf(card.labels[index - 1]))));
      if (wrong.length) fail(`catalogue: ${kind} cards without their own identifier in the head, or with relations out of order: ` + wrong.slice(0, 3).map((card) => card.id + " " + card.labels.join("/")).join("; "));
    }
    // An entry shows the persistent identifiers it has, named by scheme, and none it lacks; the stations and checks
    // an entry names carry their icons.
    const pidsOf = async (hash, anchor) => {
      await view.goto(pageUrl + hash);
      await view.waitForSelector(`[id="item-${anchor}"]`);
      return view.locator(`[id="item-${anchor}"]`).evaluate((card) => ({
        pids: [...card.querySelectorAll(".pid-line a")].map((link) => [link.previousElementSibling.textContent, link.getAttribute("href"), link.textContent.replace(/\s*\(.*\)$/, "")]),
        plainIcons: [...card.querySelectorAll(".relations a.holder-link")].filter((link) => !link.querySelector("svg.icon")).length,
        holders: card.querySelectorAll(".relations a.holder-link").length,
      }));
    };
    const roCrate = await pidsOf("#/cs/DS/catalogue/k!resources~q!crate", "ro-crate");
    if (!roCrate.pids.some(([scheme, href, text]) => scheme === "DOI" && href === "https://doi.org/10.5281/zenodo.13751027" && text === href)) fail("catalogue: RO-Crate does not show its DOI in full: " + JSON.stringify(roCrate.pids));
    if (!roCrate.holders || roCrate.plainIcons) fail("catalogue: a station an entry names lacks its icon");
    const zenodo = await pidsOf("#/cs/V/catalogue/k!repositories~q!zenodo", "zenodo");
    if (!zenodo.pids.some(([scheme, href]) => scheme === "re3data" && href.endsWith("/r3d100010468"))) fail("catalogue: Zenodo does not show its re3data identifier: " + JSON.stringify(zenodo.pids));
    const datacite = await pidsOf("#/cs/V/catalogue/k!resources~q!DataCite", "datacite");
    if (!datacite.pids.some(([scheme, href, text]) => scheme === "Nanopublikace" && href.startsWith("https://purl.org/np/") && text.startsWith("http://purl.org/np/"))) fail("catalogue: a nanopublication IRI is not shown as it is and linked over HTTPS: " + JSON.stringify(datacite.pids));
    const clause = await pidsOf("#/cs/V/catalogue/k!clauses~q!A.F1.N1", "A.F1.N1");
    if (clause.pids.length) fail("catalogue: a requirement shows a persistent identifier it does not have");
    // The accessibility statement names the API documentation as exempt and points to the accessible list.
    await view.goto(pageUrl + "#/cs/V/page/accessibility");
    await view.waitForSelector("#main h1");
    const exemption = view.locator("#main section", { hasText: "Swagger UI" });
    if (!(await exemption.count()) || !(await exemption.locator('a[href="#/cs/V/page/machines"]').count())) fail("accessibility: the statement does not name the API documentation and point to the endpoint list");
    // A block of "- " lines in page text is a list: the AI page's practice for agents, with its link kept.
    await view.goto(pageUrl + "#/en/V/page/ai");
    await view.waitForSelector("#main h1");
    const agentPractice = view.locator("#main section", { hasText: "When an AI agent does the work" }).locator("ul.text-list");
    if ((await agentPractice.locator("li").count()) < 8 || (await agentPractice.innerText()).includes("- ") || !(await agentPractice.locator("a.text-ref").count())) fail("ai page: the practice for agents is not a list of items with its link");
    // Each practice opens with its lead in bold, and the practice follows the rules directly.
    if ((await agentPractice.locator("li > strong:first-child").count()) !== (await agentPractice.locator("li").count())) fail("ai page: a practice for agents lacks its bold lead");
    const headings = await view.locator("#main article > section > h2").allTextContents();
    if (headings.indexOf("When an AI agent does the work") !== headings.indexOf("Three rules") + 1) fail("ai page: the practice for agents does not follow the rules: " + headings.join(" | "));
    const gathered = await view.evaluate(() => {
      const FG = window.FairGuide;
      const all = FG.stations().flatMap((station) => FG.refs(station, "itemListElement").filter((item) => item.adviceKind === "ai"));
      const forOne = all.filter((item) => FG.refIds(item, "audience").length < FG.lenses().length).length;
      const shown = [...document.querySelectorAll(".ai-station-tips .ai-tip")];
      return { all: all.length, forOne, shown: shown.length, tagged: shown.filter((tip) => tip.querySelector(".orientation .lens-tag")).length, prompts: shown.filter((tip) => tip.querySelector(".ai-prompt pre")).length };
    });
    if (!gathered.all || gathered.shown !== gathered.all || gathered.prompts !== gathered.all || gathered.tagged !== gathered.forOne) fail("ai page: the stations' AI tips are not all gathered with their prompts, or a tip for one view lacks its icon: " + JSON.stringify(gathered));
    const chat = view.locator('[id="cerit"] .section-action a');
    if (!(await chat.count()) || !(await chat.getAttribute("href")).startsWith("https://chat.ai.e-infra.cz") || (await chat.getAttribute("target")) !== "_blank") fail("ai page: the CERIT section does not lead to the e-INFRA CZ AI chat");
    // Parts of the knowledge base load only when a view needs them: none at the start, the pages' text for a page.
    const fresh = await context.newPage();
    await fresh.goto(pageUrl);
    await rendered(fresh);
    const atStart = await fresh.locator('script[src*="data/kb-"]').count();
    await fresh.evaluate(() => { window.location.hash = "#/cs/V/page/about"; });
    await fresh.waitForSelector('[id="why"]');
    const forPage = await fresh.locator('script[src*="data/kb-"]').evaluateAll((scripts) => scripts.map((script) => script.getAttribute("src")));
    if (atStart || forPage.join() !== "assets/data/kb-pages.js") fail(`parts: the start loads ${atStart} part(s), a page loads ${forPage.join(", ")}`);
    await fresh.close();
    // The About page links the analysis the guide is built on, where it first names it.
    await view.goto(pageUrl + "#/cs/V/page/about");
    await view.waitForSelector("#main h1");
    const basis = view.locator("#main section").first().locator("a.text-ref", { hasText: "Analýzy a návrhu postupů" });
    if (!(await basis.count())) fail("about: the analysis the guide is built on is not linked where the page first names it");
    // CoreTrustSeal: one question per requirement in three blocks, each with the requirement's guidance as published;
    // a question with no FAIR principle has no empty row of tags.
    await view.goto(pageUrl + "#/cs/SR/check/coretrustseal");
    await view.waitForSelector("#main h1");
    const cts = await view.evaluate(() => {
      const items = [...document.querySelectorAll("#main fieldset")].filter((field) => /^C\d\d\b/.test(field.querySelector("legend")?.textContent.trim() || ""));
      const guidance = [...document.querySelectorAll("#main details.item-basis details.clause-guidance .content")];
      const first = items.find((field) => field.querySelector("legend").textContent.trim().startsWith("C01"));
      return { items: items.length, guidance: guidance.length, english: guidance.every((node) => node.lang === "en"), emptyTags: first ? first.querySelectorAll(".badges").length : -1 };
    });
    const ctsBlocks = await view.locator("#main .check-block > h2, #main section h2").allTextContents();
    if (cts.items !== 16 || cts.guidance !== 16 || !cts.english || cts.emptyTags !== 0) fail("coretrustseal: not sixteen questions each with English guidance, or an empty row of tags: " + JSON.stringify(cts));
    if (!["Organizační infrastruktura", "Správa digitálních objektů", "Informační technologie a bezpečnost"].every((name) => ctsBlocks.some((heading) => heading.includes(name)))) fail("coretrustseal: the questions are not in the three CoreTrustSeal areas: " + ctsBlocks.join(" | "));
    // A principle links the CoreTrustSeal requirements it relates to, and an analysis clause links the numbers it
    // names to the requirement they are about (the analysis's "R14", reuse, is R13 in the 2026-2028 edition).
    await view.goto(pageUrl + "#/cs/V/explorer/F2");
    await view.waitForSelector("#main h1");
    const ctsLinks = await view.locator('#main a[href*="catalogue/clauses/CTS."]').evaluateAll((links) => links.map((link) => [link.textContent.trim(), decodeURIComponent(link.getAttribute("href"))]));
    if (!ctsLinks.some(([text, href]) => text.startsWith("R13") && href.endsWith("/CTS.R13"))) fail("explorer: F2 does not link its CoreTrustSeal requirements: " + JSON.stringify(ctsLinks));
    if (!ctsLinks.some(([text, href]) => text === "R14" && href.endsWith("/CTS.R13"))) fail("explorer: the analysis's R14 (reuse) does not lead to requirement R13: " + JSON.stringify(ctsLinks));
    // CDIF: the principle links its profiles, and the analysis's 2023 name "Discovery" leads to the Core profile.
    const cdifLinks = await view.locator('#main a[href*="catalogue/clauses/CDIF."]').evaluateAll((links) => links.map((link) => [link.textContent.trim(), decodeURIComponent(link.getAttribute("href")).split("/").pop()]));
    if (!cdifLinks.some(([text, id]) => text === "Core" && id === "CDIF.Core") || !cdifLinks.some(([text, id]) => text === "Discovery" && id === "CDIF.Core")) fail("explorer: F2 does not link its CDIF profiles by meaning: " + JSON.stringify(cdifLinks));
    // The CDIF check: what the standard requires first, then the recommended elements, metadata management and the
    // profiles; the first tier is named for the standard, not for NRP or the analysis.
    await view.goto(pageUrl + "#/cs/SR/check/cdif");
    await view.waitForSelector("#main h1");
    const cdifQuestions = () => view.evaluate(() => [...document.querySelectorAll("#main fieldset legend")].filter((legend) => /^M\d\d\b/.test(legend.textContent.trim())).length);
    const basicCount = await cdifQuestions();
    const tierSentence = await view.locator("#main .tier-info").innerText();
    await view.locator('label[for="extended-toggle"]').click();
    await view.waitForFunction(() => [...document.querySelectorAll("#main fieldset legend")].filter((legend) => /^M\d\d\b/.test(legend.textContent.trim())).length > 9);
    const extendedCount = await cdifQuestions();
    if (basicCount !== 9 || extendedCount !== 35 || !tierSentence.startsWith("Povinné podle standardu (9")) fail(`cdif: ${basicCount} basic and ${extendedCount} extended questions, tier sentence "${tierSentence.slice(0, 60)}"`);
    await view.locator('label[for="extended-toggle"]').click();
    await view.close();
  }

  // Requirement identifiers resolve to the catalogue: a cited requirement shows its text, then its identifier as a chip
  // that leads to the catalogue entry, which is brought into view and marked, also when opened directly; the
  // catalogue lists the requirements by source, with a kind filter, and the check questions with their basis.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await view.goto(pageUrl + "#/cs/V/path/licence");
    await view.waitForSelector(".station");
    // The next step and one related tool, the second a quieter button.
    const nowActions = await view.locator(".now .now-actions a").evaluateAll((links) => links.map((link) => link.className));
    if (nowActions.length !== 2 || !nowActions[0].includes("button-primary") || !nowActions[1].includes("button-related")) fail("station: the next step is not followed by one quieter related tool: " + nowActions.join(" | "));
    // The how-to opens with the station's key point; the reasons go straight to what the advice rests on.
    await view.locator('details[data-key="L1"] summary').click();
    if (!(await view.locator('details[data-key="L1"] .content > .key-point:first-child').textContent()).includes("Hlavní myšlenka")) fail("station: the how-to does not open with the station's key point");
    await view.locator('details[data-key="L2"] summary').click();
    if (await view.locator('details[data-key="L2"] h3', { hasText: "Principy" }).count()) fail("station: Proč repeats the principles the header shows");
    const entries = await view.locator('details[data-key="L2"] ul.clauses > li').count();
    const chips = await view.locator('details[data-key="L2"] ul.clauses > li a.id-chip').count();
    if (!entries || chips < entries - 1) fail(`ids: the cited requirements do not carry linked identifiers (${chips} of ${entries})`);
    if (await view.locator('details[data-key="L2"] ul.clauses > li > .clause-text .id-chip').count()) fail("ids: an identifier leads the requirement's text instead of following it");
    // A requirement shows one way wherever it is cited: its identifier once, its source by short name leading to the
    // source's catalogue entry. The station's terms lead to their catalogue entries, as terms in its text do.
    const cited = await view.locator('details[data-key="L2"] ul.clauses > li').evaluateAll((items) =>
      items.map((item) => ({ id: (item.querySelector(".id-chip") || {}).textContent, bold: (item.querySelector(".clause-text strong") || {}).textContent, source: item.querySelector("a.source-link") }))
    );
    if (cited.some((item) => item.id && item.bold === item.id)) fail("ids: a requirement shows its identifier twice under Proč");
    const analysisLink = view.locator('details[data-key="L2"] a.source-link', { hasText: "Analýza FAIR pro NRP/NDI" }).first();
    if (!(await analysisLink.count()) || !(await analysisLink.getAttribute("href")).endsWith("/catalogue/resources/analyza-fair-1.2")) fail("ids: a requirement's source is not named by its short name, leading to its catalogue entry");
    const termHrefs = await view.locator(".station-terms a.chip").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    if (!termHrefs.length || termHrefs.some((href) => !href.includes("/catalogue/terms/"))) fail("ids: the station's terms do not lead to their catalogue entries: " + termHrefs.join(" "));
    // The explorer names a principle's relations in the catalogue's rows, and its requirements without doubled
    // identifiers.
    await view.goto(pageUrl + "#/cs/V/explorer/R1.1");
    await view.waitForSelector(".principle-relations");
    const relationLabels = await view.locator(".principle-relations dt").allTextContents();
    if (relationLabels.join("|") !== "FIP Dashboard|CoreTrustSeal|CDIF") fail("explorer: R1.1's relations are not the FIP Dashboard, CoreTrustSeal and CDIF rows: " + relationLabels.join("|"));
    if (await view.locator("ul.clauses > li").evaluateAll((items) => items.some((item) => (item.querySelector(".clause-text strong") || {}).textContent === (item.querySelector(".id-chip") || {}).textContent))) fail("explorer: a requirement shows its identifier twice");
    // An audience shows by icon and name.
    await view.goto(pageUrl + "#/cs/V/page/ai");
    await view.waitForSelector("#main h1");
    const audienceNames = await view.locator(".orientation .lens-tag").allInnerTexts();
    if (!audienceNames.length || audienceNames.some((name) => !name.trim())) fail("ai page: an audience shows by icon alone");
    await view.goto(pageUrl + "#/cs/V/path/licence");
    await view.waitForSelector(".station");
    /* The station remembers that Proč was open; a click would close it. */
    if (!(await view.locator('details[data-key="L2"]').evaluate((details) => details.open))) await view.locator('details[data-key="L2"] summary').click();
    const chip = view.locator('details[data-key="L2"] ul.clauses a.id-chip').first();
    const id = (await chip.textContent()).trim();
    await chip.click();
    await view.waitForSelector(".catalogue-layout");
    await view.waitForFunction((expected) => document.activeElement && document.activeElement.id === "item-" + expected, id);
    if (!(await view.evaluate(() => document.activeElement.classList.contains("jumped")))) fail("ids: the catalogue entry is not marked when the identifier is followed");
    if (!(await view.locator("#facet-kind-clauses").isChecked())) fail("ids: the identifier does not select the requirements");
    await view.goto("about:blank");
    await view.goto(pageUrl + "#/cs/V/catalogue/clauses/A.F1.N1");
    await view.waitForSelector('[id="item-A.F1.N1"]');
    const box = await view.locator('[id="item-A.F1.N1"]').boundingBox();
    if (!box || box.y < 0 || box.y > 900) fail("ids: a directly opened link to a requirement does not bring it into view");
    // A link to one entry shows that entry alone, says so, and leads to the whole kind.
    if ((await view.locator(".clause-card").count()) !== 1 || !(await view.locator(".single-entry").count())) fail("ids: a link to one requirement does not show it alone with a notice");
    await view.locator(".single-entry a").click();
    await view.waitForFunction(() => document.querySelectorAll(".clause-card").length > 1);
    const all = await view.locator(".clause-card").count();
    await view.locator("#facet-clauses-ckind-recommendation").check();
    await view.waitForFunction(() => location.hash.includes("f.ckind!recommendation"));
    const recommendations = await view.locator(".clause-card").count();
    if (!(recommendations > 0 && recommendations < all)) fail("ids: the kind filter does not narrow the requirements");
    await view.goto(pageUrl + "#/cs/V/catalogue/questions/S18");
    await view.waitForSelector("#item-S18");
    if (!(await view.locator("#item-S18 a.id-chip").count())) fail("ids: a check question does not link the requirements it rests on");
    await view.close();
  }

  // Every page sits under a menu item: the tools view lists the helpers and the AI page, and its item stays current
  // on each of them; the about item covers the about page and the accessibility statement.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const current = async () => (await view.locator('.main-nav [aria-current="page"]').textContent()).trim();
    await view.goto(pageUrl + "#/cs/V/tools");
    await view.waitForSelector(".tool-cards");
    if ((await current()) !== "Nástroje") fail("tools: the menu does not mark the tools item on the tools view");
    const tools = await view.locator(".tool-card h2 a").evaluateAll((links) => links.map((link) => link.getAttribute("href").split("/").pop()));
    if (tools.join(",") !== "live-check,identifiers,citation,ai") fail("tools: the tools view does not list the tool pages in order: " + tools.join(","));
    if ((await view.locator(".tool-coming").count()) !== 3) fail("tools: the helpers in preparation are not marked as such");
    for (const [id, item] of [["identifiers", "Nástroje"], ["ai", "Nástroje"], ["live-check", "Nástroje"], ["citation", "Nástroje"], ["about", "O průvodci"], ["accessibility", "O průvodci"]]) {
      await view.goto(pageUrl + "#/cs/V/page/" + id);
      await view.waitForSelector("#main h1");
      if ((await current()) !== item) fail(`page ${id}: the menu does not mark ${item}`);
    }
    await view.close();
  }

  // Repositories: FAIRsharing records are loaded on request, link from each repository they describe, and the
  // repository names FAIRsharing among its sources.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await view.goto(pageUrl + "#/cs/V/repositories");
    await view.waitForSelector("#fairsharing-load");
    if (await view.locator(".fairsharing-record").count()) fail("repositories: FAIRsharing records show before they are loaded");
    const asked = await view.evaluate(async () => {
      const seen = [];
      window.FairGuide.live.findFairsharing = async (repositories) => {
        seen.push(...repositories);
        return [{ doi: "10.25504/FAIRsharing.f4bfb1", name: "Czech Social Science Data Archive", re3data: "r3d100010484", addresses: [] }];
      };
      document.getElementById("fairsharing-load").click();
      await new Promise((done) => setTimeout(done, 300));
      return seen.filter((repository) => (repository.identifiers || []).length).length;
    });
    if (!asked) fail("repositories: the FAIRsharing lookup is not given the repositories' re3data records");
    const card = view.locator(".card", { has: view.locator(".fairsharing-record") });
    if ((await card.count()) !== 1 || !(await card.textContent()).includes("FAIRsharing")) fail("repositories: the FAIRsharing record does not show on its repository");
    if ((await card.locator(".fairsharing-record").getAttribute("href")) !== "https://doi.org/10.25504/FAIRsharing.f4bfb1") fail("repositories: the FAIRsharing link does not lead to the record's DOI");
    if (!(await view.locator("#fairsharing-status").textContent()).includes("1 z")) fail("repositories: the FAIRsharing status does not say how many were found");
    const buttons = await view.locator(".filter-actions button").evaluateAll((all) => all.map((button) => Math.round(button.getBoundingClientRect().top)));
    if (new Set(buttons).size !== 1) fail("repositories: the live-source buttons are not aligned: " + buttons.join(", "));
    await view.close();
  }

  // Visual rules from the visual pass: cards keep even padding; the explorer shows an overview before a principle is
  // chosen; a helper page says when its helper is not there yet; on a phone the language switch shares the logo's row.
  {
    const view = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await view.goto(pageUrl + "#/cs/V/resources");
    await view.waitForSelector(".cards .card");
    const gap = await view.locator(".cards .card").first().evaluate((card) => {
      const last = card.lastElementChild.getBoundingClientRect();
      const box = card.getBoundingClientRect();
      return { bottom: Math.round(box.bottom - last.bottom), top: Math.round(card.firstElementChild.getBoundingClientRect().top - box.top) };
    });
    if (Math.abs(gap.bottom - gap.top) > 4) fail("cards: the space below the content differs from the space above it: " + JSON.stringify(gap));
    await view.goto(pageUrl + "#/cs/V/explorer");
    await view.waitForSelector("#main h1");
    const rows = await view.locator(".explorer-overview tbody tr").count();
    const caption = await view.locator(".explorer-overview caption").textContent().catch(() => "");
    if (rows !== 4 || !/^\d+ požadav/.test(caption)) fail("explorer: no overview of the requirements before a principle is chosen: " + caption);
    for (const [id, expected] of [["identifiers", true], ["citation", true], ["live-check", true], ["about", false]]) {
      await view.goto(pageUrl + "#/cs/V/page/" + id);
      await view.waitForSelector("#main h1");
      const coming = await view.locator(".helper-coming").count();
      if (Boolean(coming) !== expected) fail(`page ${id}: the note that the helper is coming is ${coming ? "shown" : "missing"}`);
    }
    await view.setViewportSize({ width: 390, height: 800 });
    await view.goto(pageUrl + "#/cs/V/page/about");
    await view.waitForSelector("#main h1");
    const logo = await view.locator(".brand > a").first().boundingBox();
    const language = await view.locator(".site-header .header-lang").boundingBox();
    if (language.y > logo.y + logo.height) fail("header: on a phone the language switch takes a row of its own");
    await view.close();
  }

  // Keyboard: the skip link, lens picker, language switch, search and stage cards are reachable with Tab.
  const reached = new Set();
  for (let i = 0; i < 30; i += 1) {
    await page.keyboard.press("Tab");
    reached.add(await page.evaluate(() => {
      const el = document.activeElement;
      return el ? (el.id || el.className || el.tagName) + ":" + (el.textContent || "").trim().slice(0, 40) : "";
    }));
  }
  const joined = [...reached].join(" | ");
  for (const expected of ["skip-link", "lens-option", "English", "search-input", "Připravuji projekt"]) {
    if (!joined.includes(expected)) fail("keyboard does not reach: " + expected);
  }

  // Universal search: terms are found locally while typing, in both languages and without diacritics, and hand
  // over to the catalogue; identifiers are routed by what they denote once the search is confirmed, the guide's own
  // identifiers while typing; nothing is sent while searching.
  const typeQuery = async (text) => {
    await page.fill("#search-input", "");
    await page.locator("#search-input").pressSequentially(text);
    await page.waitForFunction((query) => document.querySelector("#search-results").dataset.query === query, text);
    return page.locator("#search-results").textContent();
  };
  const search = async (text) => {
    await page.fill("#search-input", text);
    await page.locator("#search-input").press("Enter");
    await page.waitForFunction((query) => document.querySelector("#search-results").dataset.confirmed === "true" && document.querySelector("#search-results").dataset.query === query, text);
    return page.locator("#search-results").textContent();
  };
  let found = await typeQuery("licence");
  if (!found.includes("Licence a přístup") || !found.includes("R1.1")) fail("search: 'licence' does not find the licence step and R1.1: " + found.slice(0, 200));
  const firstGroup = page.locator("#search-results .results-list").first();
  if ((await firstGroup.locator("li").count()) !== 3) fail("search: a long result group is not shortened to three");
  await page.locator("#search-results .button-link").first().click();
  if ((await firstGroup.locator("li").count()) <= 3) fail("search: 'show all' does not reveal the rest of the group");
  if (!(await page.evaluate(() => document.activeElement.closest(".results-list li:nth-child(4)")))) fail("search: focus does not move to the first revealed result");
  found = await typeQuery("pristup");
  if (!found.includes("Licence a přístup")) fail("search: matching does not ignore diacritics");
  found = await typeQuery("persistent identifier");
  if (found.includes("Nic nenalezeno")) fail("search: English words are not searched");
  found = await typeQuery("https://doi.org/10.5281/zenodo.21726258");
  if (!found.includes("Stiskněte Enter") || (await page.locator("#search-results .result").count())) fail("search: a typed DOI does not wait for Enter: " + found.slice(0, 200));
  found = await search("https://doi.org/10.5281/zenodo.21726258");
  const primary = async () => (await page.locator("#search-results .result-primary").textContent()).trim();
  if (!(await primary()).includes("Zjistit, co to je") || !found.includes("Zkontrolovat datovou sadu")) fail("search: a DOI does not offer to find out what it is, with the dataset check beside it");
  found = await search("0000-0001-6592-6291");
  if (!found.includes("Ověřit identifikátor")) fail("search: an ORCID iD is not routed to the identifier helper");
  found = await search("r3d100010386");
  if (!(await primary()).includes("Zkontrolovat zralost repozitáře")) fail("search: a re3data identifier is not routed to the maturity check: " + found.slice(0, 200));
  found = await search("https://ror.org/04wxdxa47");
  if (!(await primary()).includes("Instituce a správa dat") || !found.includes("Ověřit identifikátor")) fail("search: a ROR ID is not routed to the institution check, with verification beside it");
  found = await typeQuery("A.F1.N1");
  if (!(await page.locator("#search-results .result-primary").getAttribute("href")).endsWith("/catalogue/clauses/A.F1.N1")) fail("search: a requirement identifier does not lead to its catalogue entry while typing");
  found = await typeQuery("licence");
  if (!(await page.locator(".catalogue-handoff a").getAttribute("href")).includes("q!licence")) fail("search: text results do not hand over to the catalogue");
  // The language changes in place; the search then shows titles in English and links into the English guide.
  await page.evaluate(() => { location.hash = "#/en/V/path/start"; });
  await page.waitForFunction(() => document.documentElement.lang === "en" && document.querySelector("#search-input"));
  found = await typeQuery("autho");
  if (!found.includes("Authentication and authorisation") || /Ověřování|umožní/.test(found)) fail("search: after switching to English the results keep Czech titles: " + found.slice(0, 200));
  if (!(await page.locator("#search-results a.result").first().getAttribute("href")).startsWith("#/en/")) fail("search: after switching to English the results link into the Czech guide");
  await page.evaluate(() => { location.hash = "#/cs/V/path/start"; });
  await page.waitForFunction(() => document.documentElement.lang === "cs" && document.querySelector("#search-input"));
  await axe(page, "landing with search results");
  if (external.length) fail("search: requests while searching: " + external.join(", "));

  // Finding out what a DOI is: the registration agency and, for DataCite, the type (both replaced here) lead to
  // the dataset check or to the citation, and say where the answer came from.
  await page.evaluate(() => {
    const live = window.FairGuide.live;
    live.doiAgency = async (doi) => (doi.startsWith("10.1038/") ? "Crossref" : "DataCite");
    live.datacite = async () => ({ types: { resourceTypeGeneral: "Dataset" }, titles: [{ title: "Test data" }], publisher: { name: "Zenodo" }, publicationYear: 2026 });
  });
  const findOut = async (pid) => {
    await search(pid);
    await page.locator("#search-results .result-primary").click();
    await page.waitForFunction(() => document.querySelector("#search-results .search-basis strong"));
    return page.locator("#search-results .search-basis").textContent();
  };
  let said = await findOut("10.5281/zenodo.21726258");
  if (!said.includes("Jde o datovou sadu") || !said.includes("DataCite") || !(await primary()).includes("Zkontrolovat datovou sadu")) fail("search: a DataCite dataset does not lead to the dataset check: " + said);
  if (!(await page.evaluate(() => document.activeElement && document.activeElement.classList.contains("result-primary")))) fail("search: focus does not move to the route found");
  if (!(await page.locator("#search-results").textContent()).includes("Dotázali jsme se: doi.org, DataCite")) fail("search: after a lookup the note does not say which services were asked");
  said = await findOut("10.1038/sdata.2016.18");
  if (!said.includes("Jde o publikaci") || !(await primary()).includes("Vytvořit citaci")) fail("search: a Crossref DOI does not lead to the citation: " + said);

  // A re3data identifier opens the maturity check filled in from the snapshot.
  await page.evaluate(() => { window.FairGuide.live.findFairsharing = async () => []; });
  await search("r3d100010386");
  await page.locator("#search-results .result-primary").click();
  await page.waitForFunction(() => location.hash.endsWith("/check/maturity") && document.getElementById("prefill-status") && document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await page.locator(".target-card").textContent()).includes("LINDAT")) fail("search: the maturity check from a re3data identifier does not say which repository it is");
  await page.goto(pageUrl);
  await rendered(page);

  // Task shortcuts change with the lens, chosen in the band under the main menu.
  if ((await page.locator(".lens-band .lens-option").count()) !== 4) fail("lens band: four options are not shown on the landing");
  if ((await page.locator('.lens-option[aria-current="true"]').getAttribute("data-lens")) !== "V") fail("lens band: the current lens is not marked");
  if ((await page.locator('.lens-option[data-lens="SR"]').getAttribute("href")) !== "#/cs/SR/path/start") fail("lens band: an option is not a shareable link");
  await page.locator('.lens-option[data-lens="SR"]').click();
  await lensShown(page, "SR");
  if (!(await page.locator(".tasks").textContent()).includes("Podmínky NRP")) fail("landing: the repository administrator's tasks are missing");
  await context.close();
}]);

// 2. Every station in every lens and language, then the other views.
sections.push(["views", async () => {
  const views = [];
  for (const lang of ["cs", "en"]) {
    for (const lens of lenses) for (const station of stations) views.push(`#/${lang}/${lens}/path/${station}`);
    for (const view of ["explorer", "resources", "repositories", "tools", "selfcheck"]) views.push(`#/${lang}/V/${view}`);
    for (const tab of ["sources", "terms", "fips", "tests", "actions"]) views.push(`#/${lang}/V/catalogue/${tab}`);
    for (const check of checks) views.push(`#/${lang}/${check.lens}/check/${check.id}`);
    for (const principle of principles.slice(0, 3)) views.push(`#/${lang}/K/explorer/${principle}`);
    for (const id of pages) views.push(`#/${lang}/V/page/${id}`);
  }
  // Several pages at once, each taking every fourth view in order.
  const PAGES = 4;
  await Promise.all(Array.from({ length: PAGES }, (_, part) => checkViews(views.filter((_, index) => index % PAGES === part))));
  console.log(`checked ${views.length} views`);
}]);

/** Open the guide in one page and check each view in turn. */
async function checkViews(views) {
  const { context, page, external, problems } = await openPage();
  await page.goto(pageUrl);
  await rendered(page);
  for (const hash of views) {
    await page.evaluate((value) => { window.location.hash = value; }, hash);
    await page.waitForFunction((value) => window.location.hash === value && document.querySelector("#main h1"), hash);
    const headingText = (await page.textContent("#main h1")).trim();
    if (!headingText) fail(`${hash}: the main heading is empty`);
    const lang = await page.evaluate(() => document.documentElement.lang);
    if (lang !== hash.split("/")[1]) fail(`${hash}: html lang is ${lang}`);
    if (hash.includes("/path/")) {
      const now = await page.locator(".now").count();
      if (!now) fail(`${hash}: no L0 block`);
      // Every station offers AI tips, each with what to check, a prompt and its copy button. Opened once in a page, the
      // block stays open in the views that follow, so the alignment and spacing checks below measure it.
      const tips = await page.evaluate(() => {
        const block = document.querySelector('#main details[data-key="ai"]');
        if (!block) return null;
        block.open = true;
        return [...block.querySelectorAll(".ai-tip")].map((tip) => Boolean(tip.querySelector("p > strong") && tip.querySelector(".ai-prompt pre")?.textContent.trim() && tip.querySelector(".ai-prompt button .copy-label")));
      });
      if (!tips || !tips.length || !tips.every(Boolean)) fail(`${hash}: no AI tip, or one without what to check, a prompt and its copy button`);
    }
    await axe(page, hash);
    // The page shell holds elements only; a view part that is absent leaves no stray text.
    if (await page.evaluate(() => [...document.getElementById("app").childNodes].some((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim()))) fail(`${hash}: stray text in the page shell`);
    // No value reaches the page unformatted.
    if (/\[object Object\]|\bundefined\b/.test(await page.locator("#app").innerText())) fail(`${hash}: an unformatted value is shown`);
    // No link leads back to the start because its address was refused.
    if (await page.locator('#app a[href="#"]').count()) fail(`${hash}: a link that leads nowhere (href="#")`);
    // Every external link opens in a new tab.
    const sameTab = await page.evaluate(() => [...document.querySelectorAll('a[href^="http"]')].filter((link) => link.target !== "_blank" || !/noopener/.test(link.rel)).map((link) => link.href));
    if (sameTab.length) fail(`${hash}: external links that do not open in a new tab: ${[...new Set(sameTab)].slice(0, 5).join(", ")}`);
    // Alignment and spacing: icons and text in every control sit centred, and nothing collides or touches unless the
    // markup says it is meant to (data-joined).
    const misaligned = await page.evaluate(misalignedControls);
    if (misaligned.length) fail(`${hash}: misaligned controls: ${[...new Set(misaligned)].slice(0, 4).join("; ")}`);
    const collided = await page.evaluate(collisions);
    if (collided.length) fail(`${hash}: collisions: ${[...new Set(collided)].slice(0, 4).join("; ")}`);
  }
  if (external.length) fail("requests while navigating: " + external.join(", "));
  for (const problem of problems) fail("navigation: " + problem);
  await context.close();
}

// 3. Reflow at 320 CSS pixels: no horizontal scrolling, and the main views keep their alignment and spacing.
sections.push(["reflow", async () => {
  const { context, page } = await openPage({ width: 320, height: 800 });
  const narrow = ["#/cs/V/path/start", "#/cs/SR/path/publikace", "#/en/DS/resources", "#/cs/V/catalogue/clauses", "#/cs/K/explorer/F1", "#/cs/V/selfcheck", "#/cs/V/check/dataset", "#/cs/V/tools", "#/cs/V/page/machines", "#/en/V/page/about"];
  for (const hash of narrow) {
    await page.goto(pageUrl + hash);
    await rendered(page);
    // A station's AI block, opened, so its prompts and copy buttons are measured too.
    await page.evaluate(() => document.querySelectorAll('#main details[data-key="ai"]').forEach((block) => { block.open = true; }));
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (overflow > 1) fail(`${hash}: horizontal scroll of ${overflow}px at 320 px`);
    const misaligned = await page.evaluate(misalignedControls);
    if (misaligned.length) fail(`${hash} at 320 px: misaligned controls: ${[...new Set(misaligned)].slice(0, 4).join("; ")}`);
    const collided = await page.evaluate(collisions);
    if (collided.length) fail(`${hash} at 320 px: collisions: ${[...new Set(collided)].slice(0, 4).join("; ")}`);
  }
  await context.close();
}]);

// 4. Embedded in an iframe.
sections.push(["iframe", async () => {
  const host = resolve(root, ".cache", "iframe-host.html");
  mkdirSync(dirname(host), { recursive: true });
  writeFileSync(host, `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Host</title></head><body><iframe title="FAIR guide" src="${pageUrl}#/cs/V/path/repozitar" style="width:100%;height:800px"></iframe></body></html>`);
  const { context, page } = await openPage();
  await page.goto(pathToFileURL(host).href);
  const frame = page.frameLocator("iframe");
  await frame.locator("#main h1").waitFor();
  const heading = await frame.locator("#main h1").textContent();
  if (!heading.includes("Výběr repozitáře")) fail("iframe: unexpected heading " + heading);
  await frame.getByRole("link", { name: /Další krok/ }).click();
  try {
    await frame.locator("#main h1", { hasText: "Popis" }).waitFor({ timeout: 5000 });
  } catch (error) {
    fail("iframe: navigation inside the frame failed: " + (await frame.locator("#main h1").textContent()));
  }
  await context.close();
}]);

// 5. Self-check without network: modes and profiles, answers, tiers, gaps on the path, the FIP Dashboard
//    snapshot pre-fill, a shared link and the exports. Nothing may leave the browser.
sections.push(["self-check", async () => {
  const { context, page, external, problems } = await openPage();
  const go = async (hash) => {
    await page.evaluate((value) => { window.location.hash = value; }, hash);
    await page.waitForFunction((value) => window.location.hash === value && document.querySelector("#main h1"), hash);
  };
  const checked = (id) => page.locator("#" + id).isChecked();
  await page.goto(pageUrl);
  await rendered(page);

  // Dataset check: the mode comes first, the first view shows the Minimum items only.
  await go("#/cs/V/check/dataset");
  if (!(await page.locator(".notice", { hasText: "Nejdřív odpovězte" }).count())) fail("dataset check: no prompt to choose the mode first");
  await page.locator("#mode-after").check();
  if (await page.locator("#item-D06").count()) fail("dataset check: a Recommended item shows in the first view");
  if (/Krok \d/.test(await page.locator(".item-group h2").first().textContent())) fail("dataset check: group headings imitate the path's step numbering");
  if (!(await page.locator("#item-D04").count())) fail("dataset check: Minimum item D04 is missing after publication");
  if (await page.locator("#item-P01").count()) fail("dataset check: a before-publication item shows after publication");
  await page.locator("#answer-D04-no").check();
  await page.locator("#answer-D05-unknown").check();
  await page.locator("#answer-D01-yes").check();
  const gaps = await page.locator(".gaps").first().textContent();
  if (!gaps.includes("D04") || !gaps.includes("Licence") || !gaps.includes("správce repozitáře")) fail("dataset check: the D04 gap lacks where to fix it or who fixes it: " + gaps);
  const gapLink = await page.locator(".gaps a", { hasText: "Licence" }).first().getAttribute("href");
  if (gapLink !== "#/cs/V/path/licence") fail("dataset check: the gap links to " + gapLink);
  const tasks = await page.locator(".gaps").nth(1).textContent();
  if (!tasks.includes("D05") || !tasks.includes("data steward")) fail("dataset check: the don't-know task does not say whom to ask: " + tasks);
  if (!(await page.locator(".gaps").nth(1).locator('a[href^="https://nma.eosc.cz"]').count())) fail("dataset check: the don't-know task has no NMA search link");
  const resultText = await page.locator("#results").textContent();
  if (/%|skóre|score/i.test(resultText)) fail("dataset check: the result shows a score or percentage");
  await axe(page, "dataset check answered");
  await page.locator('label[for="extended-toggle"]').click();
  if (!(await page.locator("#item-D06").count())) fail("dataset check: the extended check does not show Recommended items");
  if (!(await page.locator("#extended-toggle").isChecked()) || (await page.locator("#extended-toggle").getAttribute("role")) !== "switch") fail("dataset check: the extended check is not an on/off switch that shows its state");
  if (!(await panelFits(page))) fail("dataset check: the result so far scrolls or is too tall in the extended check");
  if (!(await checked("answer-D04-no"))) fail("dataset check: opening the extended check lost an answer");
  await page.locator('label[for="extended-toggle"]').click();

  // The first view says what its tier means; items are grouped by FAIR principle, can be grouped by path step, and
  // each names the step where it is addressed.
  const tierInfo = await page.locator(".tier-info").textContent();
  if (!tierInfo.includes("Minimum (") || !tierInfo.includes("Národní datové infrastruktury")) fail("dataset check: the first view does not explain its tier: " + tierInfo);
  const minimumCount = (tierInfo.match(/Minimum \((\d+) /) || [])[1];
  if (!(await page.locator("#results p").first().textContent()).endsWith("z " + minimumCount)) fail("dataset check: the result counts items the first view does not show");
  if (!(await page.locator(".item-group h2").first().textContent()).includes("Dohledatelnost")) fail("dataset check: items are not grouped by FAIR principle by default");
  if (!(await page.locator('#item-D04 .fix-at a.step-link[href$="/path/licence"]').count())) fail("dataset check: an item names its step without a link to it");
  if (!(await page.locator("#item-D04 .fix-at").textContent()).includes("Licence")) fail("dataset check: an item does not name the step where it is addressed");
  // The summary mirrors the questions: one chip per question in view, in the list's groups.
  const listed = await page.locator(".items fieldset.item").evaluateAll((items) => items.map((item) => item.id.replace("item-", "")));
  const chips = await page.locator(".summary-chip").evaluateAll((buttons) => buttons.map((button) => button.textContent.match(/[A-Z]\d{2}/)[0]));
  if (listed.join(" ") !== chips.join(" ")) fail(`dataset check: the summary does not mirror the questions (${chips.join(" ")} vs ${listed.join(" ")})`);
  await page.locator("#grouping-steps").check();
  const stepHeading = page.locator(".item-group h2").first();
  if ((await stepHeading.locator("svg").count()) !== 1 || /Krok \d/.test(await stepHeading.textContent())) fail("dataset check: grouping by path step does not show the step's icon and name");
  if ((await page.locator(".summary-group").count()) !== (await page.locator(".item-group").count())) fail("dataset check: the summary does not follow the grouping by path step");
  if ((await page.locator(".result-group").count()) !== (await page.locator(".item-group").count())) fail("dataset check: the full result does not follow the grouping by path step");
  if ((await page.locator(".summary-group-label .group-icon").count()) !== (await page.locator(".summary-group").count())) fail("dataset check: path steps in the summary lack their icons");
  await page.locator("#grouping-principles").check();

  // At the top of the page the summary's box starts level with the first box of the questions.
  await page.evaluate(() => window.scrollTo(0, 0));
  const firstBox = await page.locator(".check-main .choice").first().boundingBox();
  const summaryBox = await page.locator(".check-summary").boundingBox();
  if (Math.abs(firstBox.y - summaryBox.y) > 2) fail(`dataset check: the summary starts ${Math.round(summaryBox.y - firstBox.y)}px off the first box`);
  /* A legend drawn on the border would put the visible top line below the box's top edge. */
  const legendInside = await page.locator(".check-main .choice").first().evaluate((box) => box.querySelector("legend").getBoundingClientRect().top > box.getBoundingClientRect().top + 1);
  if (!legendInside) fail("dataset check: the first box's visible top line is not level with the summary");

  // The result stands beside the questions and shows the licence gap at once; it can be collapsed, and the choice
  // survives a reload.
  const mainBox = await page.locator(".check-main").boundingBox();
  const resultBox = await page.locator(".check-summary").boundingBox();
  if (!(resultBox.x > mainBox.x + mainBox.width / 2)) fail("dataset check: the result is not beside the questions");
  await page.locator("#item-D04").scrollIntoViewIfNeeded();
  const gapCell = page.locator('.summary-chip[data-state="gap"]', { hasText: "D04" });
  const gapBox = await gapCell.boundingBox();
  if (!gapBox || gapBox.y < 0 || gapBox.y + gapBox.height > (await page.evaluate(() => window.innerHeight))) fail("dataset check: the R1.1 gap is not in view beside the item");
  // On a wide screen the check's controls sit in the summary, at hand while scrolling.
  if (!(await page.locator(".check-summary #extended-toggle").count()) || !(await page.locator(".check-summary #grouping-steps").count())) fail("dataset check: the extended switch and the grouping are not in the summary on a wide screen");
  // The chips and counts of the result so far lead to the items and to the full result.
  await gapCell.click();
  if (!(await page.evaluate(() => document.activeElement.closest("#item-D04")))) fail("dataset check: a principle chip does not lead to its item");
  await page.locator('.summary-count[data-kind="gaps"]').click();
  if (!(await page.evaluate(() => document.activeElement.id === "results-gaps"))) fail("dataset check: the gap count does not lead to the gaps in the full result");
  // A chip whose item the short view hides opens the extended view and lands on the item.
  await page.locator('label[for="extended-toggle"]').click();
  await page.locator("#answer-D08-no").check();
  await page.locator('label[for="extended-toggle"]').click();
  await page.locator(".summary-chip", { hasText: "D08" }).click();
  if (!(await page.locator("#extended-toggle").isChecked()) || !(await page.evaluate(() => document.activeElement.closest("#item-D08")))) fail("dataset check: a chip for a hidden item does not open the extended view at the item");
  await page.locator('label[for="extended-toggle"]').click();
  // The collapse control stays exactly where it was.
  await page.locator("#item-D04").scrollIntoViewIfNeeded();
  const toggleBefore = await page.locator("#result-toggle").boundingBox();
  await page.locator("#result-toggle").click();
  if (!(await page.locator("#result-body").isHidden())) fail("dataset check: the result panel does not collapse");
  const toggleAfter = await page.locator("#result-toggle").boundingBox();
  if (!(await page.locator(".check-main #extended-toggle").count())) fail("dataset check: with the summary collapsed, the controls are not above the questions");
  if (Math.abs(toggleBefore.x - toggleAfter.x) > 1 || Math.abs(toggleBefore.y - toggleAfter.y) > 1) fail("dataset check: the collapse control moves when the panel collapses");
  if ((await page.locator("#result-toggle").boundingBox()).width > 48) fail("dataset check: the collapse control is not a small icon");
  await page.reload();
  await page.waitForSelector("#result-toggle");
  if (!(await page.locator("#result-body").isHidden())) fail("dataset check: the collapsed result panel is not remembered");
  else await page.locator("#result-toggle").click();
  if (!(await page.locator("#result-body").isVisible())) fail("dataset check: the result panel does not open again");

  // Evidence beside the criterion: the field and value found, the source, the date and a link to the record; the
  // same evidence is in the Markdown summary. Clearing the identifier removes what it pre-filled and keeps the
  // user's own answers.
  await page.evaluate(() => {
    const FG = window.FairGuide;
    const st = FG.state.answers.dataset;
    st.pid = "10.5281/zenodo.1";
    st.target = "https://doi.org/10.5281/zenodo.1";
    st.targetInfo = { name: "Sample dataset", creators: "Novak, D. a kol.", publisher: "Zenodo", year: "2026", kind: "Dataset" };
    st.items.D02 = {
      value: "yes",
      origin: "prefill",
      prefill: { source: "resolver", date: "2026-10-08", value: "yes", notes: [], list: [], fields: [{ path: "url", values: ["https://repo.example/record/1"], more: 0 }], record: "https://repo.example/record/1" },
    };
    FG.saveState();
    FG.rerender();
  });
  // A resolved identifier says what it is, under the field and in the result.
  const card = await page.locator(".target-card").textContent();
  if (!card.includes("Sample dataset") || !card.includes("Zenodo") || !card.includes("2026")) fail("dataset check: the resolved identifier does not say what it is: " + card);
  if (!(await page.locator(".result-headline").textContent()).includes("Kontrolujete: Sample dataset")) fail("dataset check: the result does not name what is checked");
  const evidence = await page.locator("#origin-D02").textContent();
  if (!evidence.includes("url") || !evidence.includes("https://repo.example/record/1") || !evidence.includes("8. 10. 2026")) fail("dataset check: the evidence beside D02 is incomplete: " + evidence);
  if ((await page.locator("#origin-D02 a").getAttribute("href")) !== "https://repo.example/record/1") fail("dataset check: the evidence does not link to its record");
  await page.locator("#export-format-md").check();
  await page.locator(".export-preview summary").click();
  await page.waitForFunction(() => document.getElementById("export-preview-text").value.length > 0);
  const doiSummary = await page.locator("#export-preview-text").inputValue();
  if (!doiSummary.includes("url = https://repo.example/record/1")) fail("dataset check: the Markdown summary lacks the evidence");
  await page.locator("#export-format-jsonld").check();
  if (!(await page.locator("#export-preview-text").inputValue()).includes('"guideState"')) fail("dataset check: the preview does not follow the chosen format");
  await page.locator(".export-preview summary").click();
  await page.locator("#export-format-md").check();
  // Your answers read as a list: the answer beside each question, and the evidence under it.
  const answerRow = await page.locator(".answers-list .answer-row").filter({ hasText: "D02" }).textContent();
  if (!answerRow.includes("Ano") || !answerRow.includes("url = https://repo.example/record/1") || !answerRow.includes("záznam")) fail("dataset check: the answers list lacks the answer or its evidence: " + answerRow);
  // The summary loads back with the DOI in its field, what it is, and the evidence.
  {
    const saved = resolve(root, ".cache", "doi-summary.md");
    writeFileSync(saved, doiSummary);
    await page.evaluate(() => {
      window.FairGuide.state.answers.dataset = { mode: "before", items: {} };
      window.FairGuide.saveState();
      window.FairGuide.rerender();
    });
    await page.locator("#load-file").setInputFiles(saved);
    await page.waitForSelector(".notice.shared");
    await page.getByRole("button", { name: "Použít odpovědi ze souboru" }).click();
    await page.waitForSelector("#prefill-pid");
    if ((await page.locator("#prefill-pid").inputValue()) !== "10.5281/zenodo.1") fail("load: the DOI is not back in its field after loading the summary");
    const restoredCard = page.locator(".target-card");
    if (!(await restoredCard.count()) || !(await restoredCard.textContent()).includes("Sample dataset")) fail("load: what the DOI is does not show after loading the summary");
    if (!(await page.locator("#origin-D02").textContent()).includes("https://repo.example/record/1")) fail("load: the evidence behind D02 is lost after loading the summary");
  }
  await page.locator("#prefill-pid-clear").click();
  if (await page.locator('input[name="answer-D02"]:checked').count()) fail("dataset check: clearing the identifier kept the answer it pre-filled");
  if (!(await checked("answer-D01-yes")) || !(await checked("answer-D04-no"))) fail("dataset check: clearing the identifier removed the user's own answers");
  if (await page.locator("#prefill-pid").inputValue()) fail("dataset check: clearing did not empty the identifier field");
  if (await page.locator(".target-card").count()) fail("dataset check: clearing the identifier kept its description");

  // The path marks the stations with open items.
  await go("#/cs/V/path/licence");
  if (!(await page.locator('.rail-desktop a[href="#/cs/V/path/licence"] .gap-mark').count())) fail("path: the licence station has no gap mark");
  const tileOrder = await page.locator(".station-header .principle-tile").evaluateAll((tiles) => tiles.map((tile) => tile.textContent.trim().split(" ")[0]));
  if (tileOrder.join(" ") !== "A1.2 R1.1") fail("path: the station's principles are not in F, A, I, R order: " + tileOrder.join(" "));
  const legend = page.locator(".rail-desktop .rail-legend a");
  if (!(await legend.count()) || (await legend.getAttribute("href")) !== "#/cs/V/selfcheck") fail("path: the self-check marks have no visible legend linking to the self-check");

  // Until the visitor chooses a stage, no stage is shown as chosen, on the path or on the landing.
  if (!(await page.locator(".stage-switch summary").textContent()).includes("zatím nevybraná")) fail("path: the stage switch claims a stage before one was chosen");
  await go("#/cs/V/path/start");
  if (await page.locator(".stage-current").count()) fail("landing: a stage is marked although none was chosen");

  // The stage can be changed on the path itself; the choice opens the stage's first station.
  await go("#/cs/V/path/licence");
  await page.locator(".stage-switch summary").click();
  await page.locator(".stage-switch button", { hasText: "Chci data zveřejnit" }).click();
  try {
    await page.waitForFunction(() => window.location.hash === "#/cs/V/path/repozitar" && document.querySelector(".stage-switch summary").textContent.includes("Chci data zveřejnit"), null, { timeout: 5000 });
  } catch (error) {
    fail("path: choosing a stage does not open its first station and show the choice");
  }
  if ((await page.locator('.stage-switch button[aria-pressed="true"]').count()) !== 1) fail("path: the chosen stage is not pressed in the stage switch");
  await go("#/cs/V/path/licence");

  // The menu's path item opens the station the visitor was last at; the home item opens the path's start, with a
  // line to resume where they were.
  if ((await page.locator(".main-nav a", { hasText: "Cesta k FAIR" }).getAttribute("href")) !== "#/cs/V/path/licence") fail("menu: the path item does not open the last station");
  if ((await page.locator('.main-nav a[aria-current="page"]').textContent()) !== "Cesta k FAIR") fail("menu: the path item is not marked on a station");
  await page.locator(".main-nav a", { hasText: "Úvod" }).click();
  try {
    await page.waitForFunction(() => window.location.hash === "#/cs/V/path/start" && document.querySelector("#stage-question") && document.querySelector("#stage-question").textContent.includes("Kde se právě nacházíte"), null, { timeout: 5000 });
  } catch (error) {
    fail("menu: the home item does not open the stage question");
  }
  if ((await page.locator('.main-nav a[aria-current="page"]').textContent()) !== "Úvod") fail("menu: the home item is not marked on the landing");
  if (!(await page.locator(".resume a").textContent()).includes("Licence")) fail("path: no resume line for the last station");
  const current = await page.locator(".stage-current").allTextContents();
  if (current.length !== 1 || !current[0].includes("Kroky 3–6") || !current[0].includes("Vybráno ")) fail("landing: the chosen stage is not marked with the last visit: " + current.join(" | "));

  // Switching the lens keeps open levels and the scroll position.
  await go("#/cs/V/path/licence");
  await page.locator(".station details summary").first().click();
  await page.evaluate(() => window.scrollTo(0, 400));
  const before = await page.evaluate(() => window.scrollY);
  // Click where the option is, as a user does: Playwright's locator click scrolls a sticky element to its place in
  // the flow first, which a real click does not.
  const option = await page.locator('.lens-option[data-lens="SR"]').boundingBox();
  await page.mouse.click(option.x + option.width / 2, option.y + option.height / 2);
  await lensShown(page, "SR");
  if ((await page.evaluate(() => window.location.hash)) !== "#/cs/SR/path/licence") fail("lens switch: the station changed");
  if ((await page.evaluate(() => document.activeElement.dataset.lens)) !== "SR") fail("lens switch: focus does not stay on the chosen lens");
  if (!(await page.locator(".station details[open]").count())) fail("lens switch: the open level closed");
  const after = await page.evaluate(() => window.scrollY);
  if (Math.abs(after - before) > 40) fail(`lens switch: the page scrolled from ${before} to ${after}`);

  // A station reads how, why, AI, then sources; its glossary terms come before the callouts and the resources; a
  // callout stays closed until the reader opens it.
  {
    const view = await browser.newPage();
    await view.goto(pageUrl + "#/cs/V/path/licence");
    await view.waitForSelector(".station");
    const keys = await view.locator(".station > details").evaluateAll((all) => all.map((part) => part.dataset.key));
    if (keys.join(",") !== "L1,L2,ai,L3") fail("station: the parts are not in the order how, why, AI, sources: " + keys.join(","));
    const at = await view.evaluate(() => {
      const parts = [...document.querySelector(".station").children];
      const index = (selector) => parts.findIndex((part) => part.matches(selector));
      return { terms: index(".station-terms"), callout: index(".callout"), resources: index("section:has(.cards)") };
    });
    if (!(at.terms >= 0 && at.terms < at.callout && at.callout < at.resources)) fail("station: the glossary terms are not above the callouts and resources: " + JSON.stringify(at));
    if (await view.locator(".callout details[open]").count()) fail("station: a callout is open before the reader opens it");
    await view.locator(".callout summary").first().click();
    if (!(await view.locator(".callout details[open] ol li").count())) fail("station: an opened callout shows no advice");
    await view.close();
  }

  // Credit: the station line names sources, not people, and opens the full detail; the footer credits the analysis
  // authors and cites the guide with its compiler as editor; the roles are listed on the about page.
  const provenance = await page.locator(".provenance-line").textContent();
  if (!provenance.includes("Analýzy FAIR") || /Novák|Trtíková/.test(provenance)) fail("station: the provenance line is not a sources-only line: " + provenance);
  await page.locator(".provenance-line button").click();
  if (!(await page.locator('details[data-key="L3"][open]').count())) fail("station: the provenance line does not open the sources and paradata");
  const history = await page.locator('details[data-key="L3"]').textContent();
  if (/Novák|Claude/.test(history) || !/obsah (vytvořen|upraven)/.test(history)) fail("station: the change history names people or tools, or lists no dated change");
  const basis = await page.locator(".site-footer p", { hasText: "Obsah vychází z" }).textContent();
  if (!basis.includes("Trtíková, I.") || !basis.includes("Čížek, T.") || !basis.includes("verze 1.2") || !basis.includes("doi.org/10.71495/5dv6-v116")) fail("footer: the analysis is not cited with its authors: " + basis);
  const guideCitation = await page.locator(".site-footer p", { hasText: "Jak citovat průvodce" }).textContent();
  if (!guideCitation.includes("Novák, D. (ed.)") || !guideCitation.includes("[software]")) fail("footer: the guide is not cited as software with its editor: " + guideCitation);
  await page.locator(".site-footer a", { hasText: "Kdo se podílel" }).click();
  await page.waitForFunction(() => document.activeElement && document.activeElement.id === "credits");
  const roles = await page.locator(".credits tbody th").allTextContents();
  if (roles.length !== 5 || !roles[0].includes("Autoři obsahového základu") || !roles[1].includes("editor")) fail("about: the roles table is incomplete: " + roles.join(" | "));
  if (!(await page.locator('.credits a[href="https://orcid.org/0000-0001-6491-2947"]').count())) fail("about: the analysis authors do not link their ORCID iDs");
  await go("#/cs/SR/path/licence");

  // The header logo leads to the EOSC CZ home page; the title opens the path's start.
  if ((await page.locator(".brand a").first().getAttribute("href")) !== "https://www.eosc.cz/") fail("header: the EOSC CZ logo does not link to its home page");
  if ((await page.locator(".brand-title").getAttribute("href")) !== "#/cs/SR/path/start") fail("header: the title does not open the path's start");
  if ((await page.locator(".brand img").boundingBox()).height < 40) fail("header: the EOSC CZ logo is too small to read");

  // Each logo of the funding logolink links to its owner, over the part of the image it covers.
  const logoLinks = await page.locator(".logolink .logolink-part").evaluateAll((links) => links.map((link) => [link.getAttribute("href"), link.textContent.trim()]));
  const logoHosts = logoLinks.map(([href]) => new URL(href).host).join(" ");
  if (logoHosts !== "opjak.cz msmt.gov.cz www.eosc.cz" || logoLinks.some(([, name]) => !name)) fail("footer: the logolink parts do not link to their owners: " + JSON.stringify(logoLinks));
  const logoArea = await page.locator(".logolink").boundingBox();
  if ((await page.locator(".logolink-funding").boundingBox()).height < 90) fail("footer: the logolink is too small to read");
  for (const box of await page.locator(".logolink .logolink-part").evaluateAll((links) => links.map((link) => link.getBoundingClientRect().toJSON()))) {
    if (box.width < 40 || box.left < logoArea.x - 1 || box.right > logoArea.x + logoArea.width + 1) fail("footer: a logolink part lies outside the image");
  }

  // The lens band appears only where the lens changes what is shown; in the resource finder it is the lens filter.
  for (const hash of ["#/cs/V/explorer", "#/cs/V/repositories", "#/cs/V/resources", "#/cs/V/page/about", "#/cs/V/check/dataset"]) {
    await go(hash);
    if (await page.locator(".lens-band").count()) fail("lens band: shown where the lens changes nothing: " + hash);
  }
  await go("#/cs/V/selfcheck");
  if (!(await page.locator(".lens-band").count())) fail("lens band: missing on the self-check overview");
  const cornerOffsets = await page.locator(".check-card").evaluateAll((cards) => cards.map((card) => { const box = card.getBoundingClientRect(); const button = card.querySelector(".check-card-action a").getBoundingClientRect(); return Math.round(box.bottom - button.bottom) + "/" + Math.round(box.right - button.right); }));
  if (new Set(cornerOffsets).size !== 1) fail("overview: the check cards' buttons are not in the same corner: " + cornerOffsets.join(" "));
  // In the catalogue the lens is a facet of the resources that starts empty, whatever the reader's lens; chosen, it
  // narrows what the guide recommends and leaves cited works in.
  await go("#/cs/V/resources");
  const shownNow = async () => Number(((await page.locator(".catalogue-count").textContent()).match(/\d+/) || [0])[0]);
  if (await page.locator('input[id^="facet-resources-lens-"]:checked').count()) fail("finder: the lens facet starts with a lens chosen");
  const allLenses = await shownNow();
  await page.locator("#facet-resources-lens-ds").check();
  await page.waitForFunction(() => location.hash.includes("f.lens!DS"));
  if ((await shownNow()) >= allLenses) fail("finder: the lens facet does not filter the resources");
  if (!(await page.locator(".card", { hasText: "Analýza a návrh postupů" }).count())) fail("finder: the lens hides a cited work, which has no audience");

  // A shared link opens as a preview in a browser without the answers, and can be adopted.
  await go("#/cs/V/check/dataset");
  await page.locator("#share-create").click();
  const shared = await page.locator("#share-url").inputValue();
  if (!shared.includes("/check/dataset/a1.after.none.") || !shared.includes("D04n") || !shared.includes("D05k")) fail("share link: unexpected payload " + shared);
  if (shared.startsWith("file:")) fail("share link: names a local file instead of the published page");
  {
    const other = await browser.newContext();
    const view = await other.newPage();
    await view.goto(pageUrl + shared.slice(shared.indexOf("#")));
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".gaps").first().textContent()).includes("D04")) fail("share link: the preview does not show the D04 gap");
    await view.getByRole("button", { name: "Použít odpovědi z odkazu" }).click();
    await view.waitForSelector("#answer-D04-no");
    if (!(await view.locator("#answer-D04-no").isChecked())) fail("share link: adopting the answers did not store them");
    await view.goto(pageUrl + "#/cs/V/check/dataset/a1.after._.Z99q");
    await view.waitForSelector(".notice");
    if (!(await view.locator(".notice", { hasText: "nepodařilo přečíst" }).count())) fail("share link: an invalid link is not reported");
    await other.close();
  }

  // Gate check: the core-system profile marks monitoring and central logging as provided by NRP.
  await go("#/cs/SR/check/gate");
  await page.locator("#profile-a").check();
  for (const id of ["G09", "G10"]) {
    if (await page.locator(`#answer-${id}-yes`).count()) fail(`gate check: ${id} asks for an answer although NRP provides it`);
    if (!/zajišťuje NRP/i.test(await page.locator(`#item-${id}`).textContent())) fail(`gate check: ${id} is not marked as provided by NRP`);
  }
  if (await page.locator("#item-G18").count()) fail("gate check: G18 shows for the core-system profile");
  // NKR lists no repository yet, so a record is put in place of the loaded list to test the mapping.
  await page.evaluate(() => {
    window.FairGuide.live.nkr = { state: "done", records: [{ id: "test/1", name: "Test repository", content: { pidType: ["DOI"], oaipmhEndpoint: ["https://repo.example/oai"] } }] };
    window.FairGuide.rerender();
  });
  await page.locator("#prefill-nkr-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  for (const id of ["G01", "G07"]) {
    if (!(await checked(`answer-${id}-yes`))) fail(`gate check: ${id} is not pre-filled yes from an NKR record listing DOI`);
    if (!(await page.locator(`#origin-${id}`).textContent()).includes("NKR")) fail(`gate check: ${id} does not name NKR as its source`);
  }
  if (!(await checked("answer-G08-partly"))) fail("gate check: G08 exceeds its pre-fill level");
  if (await page.locator('input[name="answer-G06"]:checked').count()) fail("gate check: G06 is pre-filled although the record does not state it");
  await axe(page, "gate check");

  // Maturity and institution checks run end to end; the institution check has no Minimum items and shows them all.
  await go("#/cs/SR/check/maturity");
  // The maturity check fills in from the re3data snapshot and says which repository it is; a repository outside
  // the snapshot is explained rather than guessed.
  await page.locator('label[for="extended-toggle"]').click();
  // The FAIRsharing lookup goes to DataCite; here it is replaced, as every request is in these checks.
  await page.evaluate(() => { window.FairGuide.live.findFairsharing = async () => []; });
  await page.fill("#prefill-re3data", "https://www.re3data.org/repository/r3d100010386");
  await page.locator("#prefill-re3data-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await checked("answer-S18-partly")) || !(await page.locator("#origin-S18").textContent()).includes("re3data")) fail("maturity check: S18 is not partly met from re3data alone");
  if (!(await checked("answer-S01-yes")) || !(await checked("answer-S19-yes"))) fail("maturity check: re3data facts do not fill in S01 and S19");
  if (!(await page.locator(".target-card").textContent()).includes("LINDAT")) fail("maturity check: the re3data record does not say which repository it is");
  if (!(await page.locator("#origin-S05").textContent()).includes("OAI-PMH")) fail("maturity check: S05 does not show the OAI-PMH evidence from re3data");
  // A failed FAIRsharing lookup leaves S18 open with a note; a record found answers it and links to the record.
  await page.locator("#prefill-re3data-clear").click();
  await page.evaluate(() => { window.FairGuide.live.findFairsharing = async () => { throw new Error("offline"); }; });
  await page.fill("#prefill-re3data", "r3d100010386");
  await page.locator("#prefill-re3data-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if ((await page.locator('input[name="answer-S18"]:checked').count()) || !(await page.locator("#origin-S18").textContent()).includes("nepodařilo ověřit")) fail("maturity check: a failed FAIRsharing lookup does not leave S18 open with a note");
  if (!(await checked("answer-S01-yes"))) fail("maturity check: a failed FAIRsharing lookup stopped the re3data answers");
  await page.evaluate(() => { window.FairGuide.live.findFairsharing = async () => [{ doi: "10.25504/FAIRsharing.test", name: "LINDAT", re3data: "r3d100010386", addresses: [] }]; });
  await page.locator("#prefill-re3data-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await checked("answer-S18-yes"))) fail("maturity check: a FAIRsharing record does not complete S18");
  if (!(await page.locator('#origin-S18 a[href="https://doi.org/10.25504/FAIRsharing.test"]').count())) fail("maturity check: S18 does not link to the FAIRsharing record");
  await page.fill("#prefill-re3data", "r3d999999999");
  await page.locator("#prefill-re3data-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("není ve snímku"));
  await page.locator("#prefill-re3data-clear").click();
  // While NKR lists no repository, the check says to use the re3data record instead and offers no sample records,
  // which only the catalogue shows.
  await page.evaluate(() => {
    window.FairGuide.live.nkr = { state: "done", records: [], samples: false };
    window.FairGuide.rerender();
  });
  if (!(await page.locator("#nkr-status").textContent()).includes("re3data níže") || (await page.locator("#nkr-samples").count())) fail("maturity check: an empty NKR does not point to the re3data record, or offers sample records the check cannot use");
  // FAIR Champion over a sample of records (replaced here). Each question shows the tests that can answer it and runs
  // them alone; an identifier that does not resolve is not tested. One record passes, one fails and one gives no
  // result, so a question resting on one test is partly met by the two records with a result. Running all tests
  // shows a bar, the coverage is stated, and a retry runs only the tests without a result.
  const line = page.locator("#tests-S02");
  if (!(await line.locator('a[href$="/catalogue/tests/fc_metadata_identifier_persistence"]').count()) || !(await line.textContent()).includes("po zadání vzorku") || (await page.locator(".champion-tests").count())) fail("maturity check: a question does not show its test and that a sample comes first, or the tests are listed apart from their questions");
  await page.evaluate(() => {
    const live = window.FairGuide.live;
    window.championCalls = [];
    live.resolvePid = async (pid) => ({ found: !pid.value.endsWith("/gone"), url: "https://repo.example/" + pid.value });
    live.championTest = async (test, record) => {
      window.championCalls.push(test + " " + record);
      if (window.championGate) await window.championGate;
      if (record.endsWith("/none")) throw new Error("no verdict");
      return { value: record.endsWith("/bad") ? "fail" : "pass", log: "" };
    };
  });
  await page.fill("#prefill-champion", "10.1234/good\n10.1234/bad\n10.1234/none\n10.1234/gone");
  await page.locator("#test-run-S02").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  const oneQuestion = await page.evaluate(() => window.championCalls);
  if (oneQuestion.length !== 3 || oneQuestion.some((call) => !call.startsWith("fc_metadata_identifier_persistence https://doi.org/") || call.includes("gone"))) fail("maturity check: one question's run did not test only its test on the resolved records, as resolver addresses: " + oneQuestion.join(", "));
  if (!(await checked("answer-S02-partly")) || !(await line.textContent()).includes("1 z 2") || !(await page.locator("#origin-S02").textContent()).includes("FAIR Champion")) fail("maturity check: a sample with one passing and one failing record does not partly meet S02, with the count on its test line");
  if (!(await page.locator("#prefill-status").textContent()).includes("10.1234/gone")) fail("maturity check: the record that does not resolve is not reported");
  await page.evaluate(() => { window.championCalls = []; window.championGate = new Promise((resolve) => { window.openChampion = resolve; }); });
  await page.locator("#prefill-champion-run").click();
  await page.waitForSelector("#prefill-progress:not([hidden])");
  if (!(await page.locator("#prefill-progress").textContent()).includes("z 19 testů") || !(await page.locator("#tests-S06 .test-state").textContent()).includes("běží")) fail("maturity check: running all tests does not show the progress of the remaining tests and S02's retry, or a question's line does not say its test is running");
  await page.evaluate(() => window.openChampion());
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (await page.locator("#prefill-progress:not([hidden])").count()) fail("maturity check: the progress bar stays after the tests");
  const championStatus = await page.locator("#prefill-status").textContent();
  if (!championStatus.includes("14 z 21 testů")) fail("maturity check: the coverage is not reported: " + championStatus);
  if (!(await page.locator("#prefill-champion-run").textContent()).includes("(7)")) fail("maturity check: no retry of the seven tests without a result");
  await page.evaluate(() => { window.championGate = null; window.championCalls = []; window.FairGuide.live.championTest = async (test, record) => (window.championCalls.push(record), { value: "pass", log: "" }); });
  await page.locator("#prefill-champion-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("21 z 21"));
  if (await page.evaluate(() => window.championCalls.length !== 7 || window.championCalls.some((record) => !record.endsWith("/none")))) fail("maturity check: the retry ran tests that had a result");
  if (!(await page.locator("#tests-S02").textContent()).includes("2 z 3") || (await page.locator("#prefill-champion-run").count())) fail("maturity check: the retried results are not counted, or a run stays offered");
  await page.fill("#prefill-champion", "a b c d e f");
  await page.locator("#prefill-champion-run").click();
  if (!(await page.locator("#prefill-status").textContent()).includes("jeden až 5")) fail("maturity check: a sample over five records is accepted");
  await page.locator("#answer-S02-no").check();
  if (!(await page.locator(".gaps").first().textContent()).includes("S02")) fail("maturity check: the S02 gap is missing");
  await go("#/cs/DS/check/institution");
  if (!(await page.locator("#item-I01").count())) fail("institution check: no item shows in the first view");
  await page.locator("#answer-I01-unknown").check();
  if (!(await page.locator(".gaps").first().textContent()).includes("I01")) fail("institution check: the don't-know task is missing");
  // The basic institution check is the strategy, which the Open Science III call requires, and the research act's
  // obligations; the extended check adds the action plan, the policy and the national infrastructure. Blocks replace
  // the grouping switch; a gap cites the call's minimum (and for the policy the EOSC CZ manual) and links to the
  // step where it is fixed.
  const basicBlocks = await page.locator(".item-group > h2").allTextContents();
  if (basicBlocks.length !== 2 || !basicBlocks[0].includes("zákona o výzkumu") || !basicBlocks[1].includes("Strategie") || (await page.locator(".grouping").count())) fail("institution check: the basic check is not the research act's obligations and the strategy, or the grouping switch shows: " + basicBlocks.join(" | "));
  if ((await page.locator(".item-group > h2 svg.group-icon").count()) !== 2 || (await page.locator(".check-summary svg.group-icon").count()) < 2) fail("institution check: blocks are not marked by their icons in the list and the summary");
  if (!(await page.locator(".item-group .group-description", { hasText: "§ 83" }).count())) fail("institution check: the obligations block does not say where they come from");
  await page.locator("#answer-I08-no").check();
  const peopleGap = page.locator(".gaps .action-card", { hasText: "I08" }).first();
  if (!(await peopleGap.locator('.id-chip[href$="/catalogue/clauses/E.OS3-RULES.S3"]').count())) fail("institution check: the strategy's human-resources gap does not cite the call's minimum");
  await page.locator('label[for="extended-toggle"]').click();
  const allBlocks = await page.locator(".item-group > h2").allTextContents();
  if (allBlocks.length !== 5 || !allBlocks[3].includes("Politika")) fail("institution check: the extended check does not add the action plan, policy and infrastructure blocks: " + allBlocks.join(" | "));
  await page.locator("#answer-I18-no").check();
  const retentionGap = page.locator(".gaps .action-card", { hasText: "I18" }).first();
  const cites = async (id) => retentionGap.locator(`.id-chip[href$="/catalogue/clauses/${id}"]`).count();
  if (!(await cites("E.OS3-RULES.P3")) || !(await cites("E.POLICY-MANUAL.RETENTION")) || !(await retentionGap.locator('a[href$="/path/repozitar"]').count())) fail("institution check: the retention gap does not cite the call and the manual or link to the repository step");

  // FIP check: the dashboard snapshot pre-fills answers with their source; a principle without a declaration stays
  // open with a note; a change by the user stays marked.
  await go("#/cs/K/check/fip");
  await page.locator('label[for="extended-toggle"]').click();
  await page.locator("#prefill-fip").selectOption("nusl-grey");
  await page.locator("#prefill-fip-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  const open = await page.evaluate(() => [...document.querySelectorAll("fieldset.item")].filter((item) => !item.querySelector("input:checked") && item.textContent.includes("nic nedeklaruje")).map((item) => item.id));
  if (!open.length) fail("FIP check: no item stays open with a note for a principle without a declaration");
  await page.locator("#prefill-fip").selectOption("ndi-baseline");
  await page.locator("#prefill-fip-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await checked("answer-K01-yes"))) fail("FIP check: K01 is not pre-filled from the snapshot");
  if (!(await panelFits(page))) fail("FIP check: the result so far scrolls or is too tall after pre-fill");
  if (!(await page.locator("#origin-K01").textContent()).includes("FIP Dashboard (snímek)")) fail("FIP check: K01 does not name its source");
  await page.locator("#answer-K01-partly").check();
  if ((await page.locator("#origin-K01 .source-chip").getAttribute("data-origin")) !== "changed") fail("FIP check: a changed pre-filled answer is not marked");
  await axe(page, "FIP check pre-filled");

  // Loading a saved result is a way to start: offered at the top of every check, also before the mode is chosen,
  // and not repeated among the saving controls.
  for (const [hash, label] of [["#/cs/V/check/dataset", "before the mode"], ["#/cs/SR/check/maturity", "with public records"], ["#/cs/DS/check/institution", "without public records"]]) {
    const view = await browser.newPage();
    await view.goto(pageUrl + hash);
    await view.waitForSelector("#main h1");
    if (!(await view.locator(".prefill #load-file").count())) fail(`start (${label}): loading a saved result is not offered at the top of the check`);
    if (await view.locator(".export #load-file, .export .load-file").count()) fail(`start (${label}): loading is repeated among the saving controls`);
    await view.close();
  }

  // Exports: Markdown and an FTR result set in an RO-Crate, naming the published page and the assessed profile.
  await page.locator("#export-format-md").check();
  const [mdDownload] = await Promise.all([page.waitForEvent("download"), page.locator("#export-download").click()]);
  const md = readFileSync(await mdDownload.path(), "utf8");
  if (!md.startsWith("# Úplnost FIP") || md.includes("file:")) fail("export: unexpected Markdown summary");
  await page.locator("#export-format-jsonld").check();
  const [ldDownload] = await Promise.all([page.waitForEvent("download"), page.locator("#export-download").click()]);
  const exported = JSON.parse(readFileSync(await ldDownload.path(), "utf8"));
  const exportedGraph = exported["@graph"];
  const typed = (type) => (entity) => [].concat(entity["@type"]).includes(type);
  const set = exportedGraph.find(typed("TestResultSet"));
  const results = exportedGraph.filter(typed("TestResult"));
  if (!set || set["prov:hadMember"].length !== results.length || !results.length) fail("export: the result set does not hold the results");
  if (!set || !String((set["ftr:assessmentTarget"] || {})["@id"]).includes("/profiles/ndi-baseline")) fail("export: the assessment target is not the chosen profile");
  if (results.some((result) => !["pass", "fail", "indeterminate"].includes(result["prov:value"]))) fail("export: a result has an unexpected value");
  const k01 = results.find((result) => result["@id"] === "#result-K01") || {};
  if (!String(k01["ftr:log"]).includes("Doklad") || !k01["prov:used"]) fail("export: the K01 result does not record its evidence: " + JSON.stringify(k01));
  if (!md.includes("Deklarované")) fail("export: the Markdown summary does not carry the evidence behind the answers");
  if (JSON.stringify(exported).includes("file:")) fail("export: the JSON-LD names a local file");
  // A result names the test it came from: the question's manual test in the guide's API, which implements the
  // question's metric. From a local file the page names the configured address, which maps onto the built site.
  const configured = await page.evaluate(() => window.FairGuide.config.pageUrl);
  const testRef = String((k01["ftr:outputFromTest"] || {})["@id"] || "");
  const testFile = testRef.startsWith(configured) ? resolve(root, "_site", testRef.slice(configured.length)) : null;
  const testRecord = testFile && existsSync(testFile) ? JSON.parse(readFileSync(testFile, "utf8")) : null;
  if (!testRecord || ![].concat(testRecord["@type"]).includes("Test") || testRecord.isImplementationOf !== "../metrics/K01.json") fail("export: the K01 result does not name its test in the guide's API: " + testRef);

  // Local data: each check says where the answers are kept, and how it works.
  const note = await page.locator(".local-data").textContent();
  if (!note.includes("zůstávají jen v tomto prohlížeči") || !note.includes("Co odchází")) fail("local data: the statement or its explanation is missing on the check");
  if (!/<!-- fair-guide-result v1 guide=\S+: fip a1\./.test(md)) fail("export: the Markdown summary does not carry the answers with the format and guide versions");
  if (!/<!-- fair-guide-state\n[A-Za-z0-9+/=\n]+\n-->/.test(md)) fail("export: the Markdown summary does not carry the state for loading back");
  const state = JSON.parse(exportedGraph.find((entity) => entity.guideState).guideState);
  if (state.format !== "eosc-fair-guide-result" || state.v !== 1 || !state.guideVersion) fail("export: the JSON-LD does not declare its format and the guide's version");
  if (state.fip !== "ndi-baseline" || !state.targetInfo) fail("export: the JSON-LD does not carry the chosen profile and what it is");

  // A saved result loads in another browser as a preview, keeps its evidence, and is adopted only on request; a
  // file the guide did not make is refused.
  {
    const other = await browser.newContext();
    const view = await other.newPage();
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    const foreign = resolve(root, ".cache", "not-a-result.md");
    writeFileSync(foreign, "# Notes\n\nNothing from the guide.\n");
    await view.locator("#load-file-overview").setInputFiles(foreign);
    await view.waitForFunction(() => document.getElementById("load-file-overview-status").textContent.includes("nevytvořil"));
    // A damaged file, a file from a newer format and a file with a question this version does not know.
    const variant = (name, change) => {
      const copy = JSON.parse(JSON.stringify(exported));
      const holder = copy["@graph"].find((entity) => entity.guideState);
      const data = JSON.parse(holder.guideState);
      change(data);
      holder.guideState = JSON.stringify(data);
      const path = resolve(root, ".cache", name);
      writeFileSync(path, JSON.stringify(copy));
      return path;
    };
    const tryLoad = async (path, expected, message) => {
      await view.locator("#load-file-overview").setInputFiles(path);
      try {
        await view.waitForFunction((text) => document.getElementById("load-file-overview-status").textContent.includes(text), expected, { timeout: 3000 });
      } catch (error) {
        fail(message + ": " + (await view.locator("#load-file-overview-status").textContent()));
      }
    };
    await tryLoad(variant("damaged.jsonld", (data) => { data.items.K01.value = "maybe"; }), "poškozený", "load: a damaged file is not reported as damaged");
    await tryLoad(variant("newer.jsonld", (data) => { data.v = 2; data.guideVersion = "9.0.0"; }), "novější verze", "load: a file from a newer format is not reported");
    await view.locator("#load-file-overview").setInputFiles(variant("unknown-item.jsonld", (data) => { data.items.K99 = { value: "yes", origin: "user", prefill: null }; }));
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("vynechali: 1")) fail("load: a question this version does not know is not skipped with a note");
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await view.locator("#load-file-overview").setInputFiles(await ldDownload.path());
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("ze souboru")) fail("load: a JSON-LD file does not open as a preview");
    if (await view.evaluate(() => Object.keys(window.FairGuide.state.answers).length)) fail("load: the preview changed the stored answers");
    await view.getByRole("button", { name: "Použít odpovědi ze souboru" }).click();
    await view.waitForSelector("#answer-K01-partly");
    if (!(await view.locator("#answer-K01-partly").isChecked())) fail("load: the adopted answers are not the file's answers");
    const loaded = await view.locator("#origin-K01").textContent();
    if (!loaded.includes("Převzato ze sdíleného výsledku") || !loaded.includes("liší se od návrhu")) fail("load: the adopted K01 lost its evidence or is mislabelled: " + loaded);
    const restored = async (format) => {
      if ((await view.locator("#prefill-fip").inputValue()) !== "ndi-baseline") fail(`load (${format}): the profile chosen for pre-fill is not restored`);
      if (!(await view.locator(".target-card").count())) fail(`load (${format}): what the identifier is does not show after loading`);
    };
    await restored("JSON-LD");
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await view.locator("#load-file-overview").setInputFiles(await mdDownload.path());
    await view.waitForSelector(".notice.shared");
    if (!(await view.locator(".notice.shared").textContent()).includes("ze souboru")) fail("load: a Markdown summary does not open as a preview");
    await view.getByRole("button", { name: "Použít odpovědi ze souboru" }).click();
    await view.waitForSelector("#answer-K01-partly");
    const fromMarkdown = await view.locator("#origin-K01").textContent();
    if (!fromMarkdown.includes("liší se od návrhu")) fail("load (Markdown): the adopted K01 lost its evidence: " + fromMarkdown);
    await restored("Markdown");
    // A summary from before the state was carried still loads its answers.
    const older = resolve(root, ".cache", "older-summary.md");
    writeFileSync(older, md.replace(/<!-- fair-guide-state[\s\S]*?-->\n?/, ""));
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await view.locator("#load-file-overview").setInputFiles(older);
    await view.waitForSelector(".notice.shared");
    const broken = resolve(root, ".cache", "broken-state.md");
    writeFileSync(broken, md.replace(/(<!-- fair-guide-state\n)[A-Za-z0-9]{8}/, "$1@@@@@@@@"));
    await view.goto(pageUrl + "#/cs/K/selfcheck");
    await view.waitForSelector("#load-file-overview");
    await tryLoad(broken, "poškozený", "load: a summary with a damaged state is not reported as damaged");
    await other.close();
  }

  // Reflow of a check at 320 CSS pixels.
  await page.setViewportSize({ width: 320, height: 800 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 1) fail(`FIP check: horizontal scroll of ${overflow}px at 320 px`);

  // Deleting everything lives on the About page, which the footer links to, and on each check; the self-check
  // overview links there. It leaves nothing the guide stored, and the checks start empty.
  await go("#/cs/K/selfcheck");
  if ((await page.locator(".local-data").count()) || !(await page.locator('a[href$="/page/about/privacy"]', { hasText: "smazat" }).count())) fail("local data: the self-check overview does not link to the About page in place of the note");
  if (!(await page.locator('footer a[href$="/page/about/privacy"]').count())) fail("local data: the footer does not link to the data in this browser");
  await go("#/cs/K/page/about/privacy");
  if (!(await page.locator("#privacy .local-data").count())) fail("local data: the About page's privacy section does not show the note");
  if (!(await page.locator("#local-data-delete").isVisible())) fail("local data: the delete control is not visible without opening anything");
  page.once("dialog", (dialog) => dialog.accept());
  await page.locator("#local-data-delete").click();
  await page.waitForFunction(() => document.getElementById("local-data-status").textContent.includes("smazané"));
  if (await page.evaluate(() => window.localStorage.getItem("eosc-fair-guide"))) fail("local data: something remains in the browser after deleting everything");
  await go("#/cs/V/check/dataset");
  if (!(await page.locator(".notice", { hasText: "Nejdřív odpovězte" }).count())) fail("local data: the dataset check kept its answers after deleting everything");
  if (await page.evaluate(() => window.localStorage.getItem("eosc-fair-guide"))) fail("local data: browsing after deletion stored something without a user action");

  if (external.length) fail("self-check: requests without a lookup: " + external.join(", "));
  for (const problem of problems) fail("self-check: " + problem);
  console.log("checked the self-check flows");
  await context.close();
}]);

// 6. Funded output in the dataset check: the programme question appears after publication with no programme
//    picked; the minizáměr shows the requirements both programmes share and Open Science III adds its own; a
//    DataCite record without the data steward's ORCID iD gives a gap that says the dataset would not meet the
//    programme's requirement. Its own context, so the pre-filled answers stay out of the other self-check flows.
sections.push(["funded output", async () => {
  const { context, page, external, problems } = await openPage();
  const checked = (id) => page.locator("#" + id).isChecked();
  await page.goto(pageUrl + "#/cs/V/check/dataset");
  await rendered(page);
  await page.waitForSelector("#mode-after");
  const outputItems = async () => page.locator("fieldset.item").evaluateAll((items) => items.map((item) => item.id.replace("item-", "")).filter((id) => id.startsWith("O")).sort().join(","));
  await page.locator("#mode-before").check();
  if (await page.locator('input[name="profile"]').count()) fail("dataset check: the programme question shows before publication");
  await page.locator("#mode-after").check();
  if ((await page.locator('input[name="profile"]:checked').getAttribute("value")) !== "none" || (await outputItems())) fail("dataset check: the check does not start without a programme and without programme items");
  await page.locator('input[name="profile"][value="minizamer"]').check();
  if ((await outputItems()) !== "O01,O02,O03,O04") fail("dataset check: the minizáměr programme does not show just the shared requirements: " + (await outputItems()));
  await page.locator('input[name="profile"][value="os3"]').check();
  if ((await outputItems()) !== "O01,O02,O03,O04,O05,O06,O07,O08,O09") fail("dataset check: Open Science III does not add its own requirements");
  await page.evaluate(() => {
    const live = window.FairGuide.live;
    live.resolvePid = async () => ({ found: true, url: "https://zenodo.org/records/1", title: "Test" });
    live.datacite = async () => ({ doi: "10.5281/zenodo.1", titles: [{ title: "Test" }], creators: [{ name: "Nováková, Jana", nameIdentifiers: [{ nameIdentifier: "https://orcid.org/0000-0002-1825-0097", nameIdentifierScheme: "ORCID" }] }], contributors: [] });
  });
  await page.fill("#prefill-steward", "0000-0001-5109-3700");
  await page.locator("#prefill-steward").dispatchEvent("change");
  await page.fill("#prefill-pid", "10.5281/zenodo.1");
  await page.locator("#prefill-pid-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status") && document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if (!(await checked("answer-O08-no"))) fail("dataset check: a record without the data steward's ORCID iD does not answer no");
  const stewardGap = page.locator(".gaps .action-card", { hasText: "O08" }).first();
  if (!(await stewardGap.textContent()).includes("nesplnila požadavek programu na výstup (Open Science III") || !(await stewardGap.locator('.id-chip[href$="/catalogue/clauses/E.OS3-RULES.D-STEWARD"]').count())) fail("dataset check: the data steward gap does not say the output requirement is not met, or does not cite the call's rules");
  // A gap's basis names its source the way every citation does: by short name, leading to the catalogue; a
  // question's basis opens under the same label.
  if (!(await stewardGap.locator('a.source-link[href$="/catalogue/resources/os3-rules"]').textContent()).includes("Pravidla výzvy Open Science III")) fail("dataset check: the gap does not name the call's rules by their short name, leading to the catalogue");
  if (!(await page.locator("#item-O08 details.item-basis summary").textContent()).startsWith("Vychází z (")) fail("dataset check: a question's basis does not open under the label every view uses");
  // FAIR Champion on the dataset, as a second action after the lookup: each question shows its tests and runs them
  // alone, the lookup result runs them all, and no test runs on an identifier that does not resolve. Four outcomes:
  // a pass answers yes, a fail no, an indeterminate verdict or no result leaves the answer to the quick check; the
  // coverage is stated and a retry runs only the tests without a result. The extended view shows every question.
  await page.locator('label[for="extended-toggle"]').click();
  await page.waitForSelector("#tests-D07");
  if (!(await page.locator(".champion-all").textContent()).includes("5 otázek") || !(await page.locator('#tests-D07 [data-health="degraded"]').count())) fail("dataset check: the lookup result does not offer the tests of five questions, or a degraded test is not marked at its question");
  await page.evaluate(() => {
    const live = window.FairGuide.live;
    window.championCalls = [];
    live.resolvePid = async () => ({ found: false });
    live.championTest = async (test, record) => {
      window.championCalls.push(test + " " + record);
      const verdicts = { fc_data_identifier_in_metadata: "pass", fc_metadata_includes_license: "fail", fc_metadata_identifier_persistence: "indeterminate" };
      if (!verdicts[test]) throw new Error("no verdict");
      return { value: verdicts[test], log: "log of " + test };
    };
  });
  await page.locator("#test-run-D03").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("nepodařilo přeložit"));
  if (await page.evaluate(() => window.championCalls.length)) fail("dataset check: FAIR Champion was called for an identifier that does not resolve");
  await page.evaluate(() => { window.FairGuide.live.resolvePid = async () => ({ found: true, url: "https://zenodo.org/records/1", title: "Test" }); });
  await page.locator("#test-run-D03").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("Hotovo"));
  if ((await page.evaluate(() => window.championCalls.join(","))) !== "fc_data_identifier_in_metadata https://doi.org/10.5281/zenodo.1") fail("dataset check: one question's run did not test only its test, on the DOI as its resolver address");
  if (!(await checked("answer-D03-yes")) || !(await page.locator("#tests-D03").textContent()).includes("splněno")) fail("dataset check: a passed test does not answer D03 yes and show on its line");
  await page.locator("#prefill-champion-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("3 z 5 testů"));
  if ((await page.evaluate(() => window.championCalls.filter((call) => call.startsWith("fc_data_identifier_in_metadata")).length)) !== 1 || (await page.evaluate(() => window.championCalls.length)) !== 5) fail("dataset check: running all tests ran again a test that had a result");
  if (!(await checked("answer-D04-no")) || !(await page.locator("#tests-D04").textContent()).includes("nesplněno")) fail("dataset check: a failed test does not answer D04 no");
  if (!(await checked("answer-D02-yes")) || !(await page.locator("#origin-D02").textContent()).includes("resolver")) fail("dataset check: an indeterminate test replaced the quick check's answer to D02");
  if (!(await page.locator("#prefill-champion-run").textContent()).includes("(2)") || !(await page.locator("#test-run-D09").textContent()).includes("Zopakovat")) fail("dataset check: no retry of the two tests without a result, overall or at their questions");
  await page.evaluate(() => { window.championCalls = []; window.FairGuide.live.championTest = async (test, record) => (window.championCalls.push(test), { value: "pass", log: "" }); });
  await page.locator("#prefill-champion-run").click();
  await page.waitForFunction(() => document.getElementById("prefill-status").textContent.includes("5 z 5 testů"));
  if (await page.evaluate(() => window.championCalls.sort().join(",") !== "community_metadata_includes_author_affiliation,fc_metadata_outward_links")) fail("dataset check: the retry ran tests that had a result");
  if (external.length) fail("funded output: requests without a lookup: " + external.join(", "));
  for (const problem of problems) fail("funded output: " + problem);
  console.log("checked the funded-output profile");
  await context.close();
}]);

// Every section at once; one that throws fails on its own and the others still report.
const timings = [];
await Promise.all(
  sections.map(async ([name, run]) => {
    const start = Date.now();
    try {
      await run();
    } catch (error) {
      fail(`${name}: stopped: ${String(error.message).split("\n")[0]}`);
    }
    timings.push(`${name} ${((Date.now() - start) / 1000).toFixed(1)}s`);
  })
);
console.log("sections: " + timings.join(", "));

await browser.close();
if (failures.length) {
  console.error(failures.map((failure) => "FAIL " + failure).join("\n"));
  console.error(`${failures.length} problem(s)`);
  process.exit(1);
}
console.log("page checks passed");
