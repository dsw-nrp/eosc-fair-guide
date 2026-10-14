// Shared safe rendering on the built page: addresses as the browser reads them, event attributes and data merges.
// Each unsafe address is first shown to be unsafe when set raw, so the case is one a browser would actually follow.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const root = resolve(import.meta.dirname, "../..");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const { chromium } = await import("playwright");
const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
await page.route(/^https?:/, (route) => route.abort());
const base = pathToFileURL(resolve(root, "_site/index.html")).href;
await page.goto(base + "#/en/V/path/start");
await page.waitForSelector("#main h1");

const addresses = await page.evaluate(() => {
  const FG = window.FairGuide;
  const unsafe = [
    "javascript:alert(1)", "JaVaScRiPt:alert(1)", "java\tscript:alert(1)", "java\nscript:alert(1)", "java\rscript:alert(1)",
    "\u0001javascript:alert(1)", " \u0000 javascript:alert(1)", "javascript:alert(1)\u001f", "\u0019data:text/html,x",
    "data:text/html,<b>x</b>", "vbscript:msgbox(1)", "//evil.example/x", "/\\evil.example/x", "\\\\evil.example/x",
    "\t//evil.example/x", "http://evil.example/",
  ];
  const raw = (value) => {
    const link = document.createElement("a");
    link.setAttribute("href", value);
    return { protocol: link.protocol, host: link.host };
  };
  const followed = (value) => {
    const { protocol, host } = raw(value);
    return ["javascript:", "data:", "vbscript:", "http:"].includes(protocol) || host === "evil.example";
  };
  return {
    unsafe: unsafe.map((value) => ({ value, followed: followed(value), safe: FG.safeHref(value),
      link: FG.h("a", { href: value }).hasAttribute("href"), image: FG.h("img", { src: value }).hasAttribute("src") })),
    kept: ["https://example.org/a?b=1#c", " https://example.org/a ", "#/en/V/path/start", "assets/img/eosc-cz-logo.svg",
      "mailto:info@eosc.cz", "../api/meta.json", "http://doi.org/10.1234/x"].map((value) => [value, FG.safeHref(value)]),
  };
});
for (const entry of addresses.unsafe) {
  assert(entry.followed, `test case is not unsafe when set raw: ${JSON.stringify(entry.value)}`);
  assert.equal(entry.safe, null, `safeHref admits ${JSON.stringify(entry.value)}`);
  assert(!entry.link && !entry.image, `an element links ${JSON.stringify(entry.value)}`);
}
assert.deepEqual(addresses.kept, [
  ["https://example.org/a?b=1#c", "https://example.org/a?b=1#c"],
  [" https://example.org/a ", "https://example.org/a"],
  ["#/en/V/path/start", "#/en/V/path/start"],
  ["assets/img/eosc-cz-logo.svg", "assets/img/eosc-cz-logo.svg"],
  ["mailto:info@eosc.cz", "mailto:info@eosc.cz"],
  ["../api/meta.json", "../api/meta.json"],
  ["http://doi.org/10.1234/x", "https://doi.org/10.1234/x"],
]);

const attributes = await page.evaluate(() => {
  const FG = window.FairGuide;
  window.inlineRan = 0;
  window.listenerRan = 0;
  const hostile = FG.h("button", { onclick: "window.inlineRan = 1", ONMOUSEOVER: "window.inlineRan = 2", onFocus: 42,
    onauxclick: true, onkeyup: { handleEvent() { window.inlineRan = 3; } }, srcdoc: "<p>x</p>" }, "Hostile");
  const frame = FG.h("iframe", { srcdoc: "<script>window.parent.inlineRan = 4</script>", title: "frame" });
  const ordinary = FG.h("button", { onclick: () => { window.listenerRan += 1; }, class: "button", "aria-label": "Label",
    hidden: true, "data-key": "k", title: "Title" }, "Ordinary");
  document.body.append(hostile, frame, ordinary);
  hostile.click();
  hostile.dispatchEvent(new MouseEvent("mouseover"));
  hostile.dispatchEvent(new KeyboardEvent("keyup"));
  ordinary.click();
  const names = (element) => [...element.attributes].map((attribute) => attribute.name);
  const result = { hostile: names(hostile), frame: names(frame), ordinary: names(ordinary), inlineRan: window.inlineRan,
    listenerRan: window.listenerRan, label: ordinary.textContent };
  hostile.remove(); frame.remove(); ordinary.remove();
  return result;
});
assert.deepEqual(attributes.hostile, [], "a non-function event value or an inline document becomes an attribute");
assert.deepEqual(attributes.frame, ["title"]);
assert.equal(attributes.inlineRan, 0, "inline code ran");
assert.equal(attributes.listenerRan, 1, "a function listener does not run");
assert.deepEqual(attributes.ordinary.sort(), ["aria-label", "class", "data-key", "hidden", "title"]);
assert.equal(attributes.label, "Ordinary");

const merged = await page.evaluate(() => {
  const FG = window.FairGuide;
  const patch = JSON.parse('{"__proto__":{"polluted":"yes"},"constructor":{"prototype":{"polluted":"yes"}},' +
    '"prototype":{"polluted":"yes"},"name":{"en":"New"},"list":[null,"b"],"nested":{"__proto__":{"polluted":"yes"},"keep":"v"}}');
  const target = { name: { cs: "Původní" }, list: ["a0", "a1"], nested: {} };
  FG.mergeData(target, patch);
  return { polluted: ({}).polluted, functionPolluted: (function () {}).polluted,
    prototypes: [target, target.nested].every((value) => Object.getPrototypeOf(value) === Object.prototype),
    own: ["constructor", "prototype"].filter((key) => Object.hasOwn(target, key)),
    name: target.name, list: target.list, keep: target.nested.keep,
    shared: ["__proto__", "constructor", "prototype", "name"].map(FG.unsafeKey) };
});
assert.equal(merged.polluted, undefined, "a merge reached Object.prototype");
assert.equal(merged.functionPolluted, undefined, "a merge reached a constructor's prototype");
assert(merged.prototypes, "a merge replaced an object's prototype");
assert.deepEqual(merged.own, []);
assert.deepEqual(merged.name, { cs: "Původní", en: "New" });
assert.deepEqual(merged.list, ["a0", "b"]);
assert.equal(merged.keep, "v");
assert.deepEqual(merged.shared, [true, true, true, false]);
// The page applies language patches with the expected results the generator's reference implementation also meets.
const fixtureText = readFileSync(resolve(root, "tests/fixtures/language-patch.json"), "utf8");
const patches = JSON.parse(fixtureText).cases;
// The text is parsed inside the page, so prototype keys arrive as the own keys a downloaded patch would carry.
const applied = await page.evaluate((text) => JSON.parse(text).cases.map((entry) => {
  window.FairGuide.mergeData(entry.target, entry.patch);
  return JSON.stringify(entry.target);
}), fixtureText);
assert.equal(await page.evaluate(() => ({}).polluted), undefined);
patches.forEach((entry, index) => assert.deepEqual(JSON.parse(applied[index]), entry.expected, entry.name));

// Printing opens every closed disclosure once and afterwards closes exactly those again; one handler pair does it.
const printHandlers = readdirSync(resolve(root, "assets/js")).filter((name) => name.endsWith(".js"))
  .map((name) => (readFileSync(resolve(root, "assets/js", name), "utf8").match(/addEventListener\("beforeprint"/g) || []).length);
assert.equal(printHandlers.reduce((sum, count) => sum + count, 0), 1, "one beforeprint handler");
await page.evaluate(() => { location.hash = "#/en/V/path/plan"; });
await page.waitForSelector("#main .station details");
const printed = await page.evaluate(() => {
  const all = [...document.querySelectorAll("details")];
  all[0].open = true; // a disclosure the reader opened stays open after printing
  const before = all.map((element) => element.open);
  window.dispatchEvent(new Event("beforeprint"));
  const during = all.every((element) => element.open);
  window.dispatchEvent(new Event("afterprint"));
  return { count: all.length, before, during, after: all.map((element) => element.open) };
});
assert(printed.count > 1 && printed.before.includes(false), "the station has closed disclosures to print");
assert(printed.during, "a closed disclosure stays closed while printing");
assert.deepEqual(printed.after, printed.before, "printing does not restore the disclosure state");

// Ordinary rendering through the real language merge stays intact in both languages.
for (const lang of ["cs", "en"]) {
  await page.evaluate((value) => { location.hash = `#/${value}/V/path/start`; }, lang);
  await page.waitForFunction((value) => document.documentElement.lang === value && document.querySelector("#main h1"), lang);
  assert(await page.locator("#main a[href]").count(), `no links render in ${lang}`);
}
assert.deepEqual(errors, []);
await browser.close();
console.log("check_safety: browser-interpreted addresses, event attributes, inline documents and prototype keys are refused; ordinary rendering passes");
