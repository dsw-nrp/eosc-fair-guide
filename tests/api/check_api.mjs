// API checks for the FAIR Data Guide, on the site that scripts/build_site.py writes into _site/:
// - the OpenAPI description is valid OpenAPI 3.1, with a relative server address;
// - every API file matches the schema of the path it is served at, and every file is documented;
// - every link in a record leads to a file of the API (and a fragment to a part given in that file), and every
//   identifier in the crate names an entity the crate has;
// - the documentation page has its own content security policy and no inline script; served over HTTP, it shows
//   the description, "Try it out" on the principles list returns the list, and no request leaves the site.
// The documentation page is a third-party tool exempt from the accessibility check (the accessibility statement
// names it), so axe does not run here.
// Usage: python scripts/build_site.py && npm run check:api
import { createServer } from "node:http";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, extname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import SwaggerParser from "@apidevtools/swagger-parser";
import Ajv2020 from "ajv/dist/2020.js";
import { chromium } from "playwright";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const siteArgument = process.argv.indexOf("--site");
const site = siteArgument >= 0 ? resolve(process.argv[siteArgument + 1]) : join(root, "_site");
const healthOnly = process.argv.includes("--health-only");
const failures = [];
const fail = (message) => failures.push(message);
const read = (path) => JSON.parse(readFileSync(path, "utf8"));
const posix = (path) => path.split(sep).join("/");

if (!existsSync(join(site, "openapi.json"))) {
  console.error("FAIL no API in _site/; run python scripts/build_site.py first");
  process.exit(1);
}
const openapi = read(join(site, "openapi.json"));
const crate = read(join(site, "ro-crate-metadata.json"));
const crateIds = new Set(crate["@graph"].map((entity) => entity["@id"]));
// The address the API was built for, read from the crate's own vocabulary (<address>terms#), which no file of the
// API may name.
const sitePrefix = Object.values(crate["@context"][1]).find((iri) => String(iri).includes("terms#")).split("terms#")[0];
const files = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path);
    else if ([".json", ".jsonld"].includes(extname(name))) files.push(posix(relative(site, path)));
  }
})(join(site, "api"));
if (healthOnly) {
  files.splice(0, files.length, "api/health.json", "api/meta.json");
}

// 1. The description is valid OpenAPI 3.1 and names its server relative to itself.
try {
  await SwaggerParser.validate(structuredClone(openapi));
} catch (error) {
  fail("openapi.json: " + error.message.split("\n").slice(0, 3).join(" "));
}
if (openapi.openapi !== "3.1.0") fail("openapi.json: not OpenAPI 3.1.0 but " + openapi.openapi);
if (!openapi.servers || openapi.servers.some((server) => /^[a-z]+:/i.test(server.url))) fail("openapi.json: a server address is not relative");

// 2. Every file matches the schema of its path, and every documented record exists.
const ajv = new Ajv2020({ strict: false, allErrors: true });
const definitions = JSON.parse(JSON.stringify(openapi.components.schemas).replaceAll("#/components/schemas/", "#/$defs/"));
ajv.addSchema({ $id: "api", $defs: definitions });
const routes = Object.entries(openapi.paths).map(([template, item]) => {
  const parameter = (item.get.parameters || [])[0];
  const pattern = new RegExp("^" + template.slice(1).replace(/[.]/g, "\\.").replace(/\{[^}]+\}/, "([^/]+)") + "$");
  const media = Object.values(item.get.responses["200"].content)[0];
  return { template, pattern, schema: media.schema.$ref.split("/").pop(), values: parameter ? parameter.schema.enum : null };
});
for (const file of files) {
  const route = routes.find((candidate) => candidate.pattern.test(file));
  if (!route) {
    fail(`${file}: no path of the description serves it`);
    continue;
  }
  const validate = ajv.getSchema("api#/$defs/" + route.schema);
  if (!validate(read(join(site, file)))) {
    fail(`${file}: does not match ${route.schema}: ` + validate.errors.slice(0, 3).map((error) => `${error.instancePath || "/"} ${error.message}`).join("; "));
  }
}
for (const route of routes.filter((candidate) => candidate.values && !healthOnly)) {
  for (const value of route.values) {
    const file = route.template.slice(1).replace(/\{[^}]+\}/, value);
    if (!existsSync(join(site, file))) fail(`${route.template}: the documented record ${value} has no file`);
  }
}

// 3. Links lead somewhere: relative paths to API files (and their fragments to parts given there), the crate's
//    identifiers to its entities. Link-valued properties are the ones the context types as links.
const context = read(join(site, "api/context.jsonld"))["@context"];
const linkKeys = new Set(["@id", ...Object.entries(context).filter(([, definition]) => definition && (definition["@type"] === "@id" || definition["@reverse"])).map(([key]) => key)]);
linkKeys.add("api_record"); // Ordinary health JSON links to existing records; it does not use a JSON-LD context.
const partsOf = new Map();
const partIds = (path) => {
  if (!partsOf.has(path)) {
    const ids = new Set();
    if (extname(path) === ".html") {
      for (const match of readFileSync(join(site, path), "utf8").matchAll(/\bid=["']([^"']+)["']/g)) ids.add("#" + match[1]);
    } else (function collect(value) {
      if (Array.isArray(value)) value.forEach(collect);
      else if (value && typeof value === "object") {
        if (typeof value["@id"] === "string" && value["@id"].startsWith("#")) ids.add(value["@id"]);
        Object.values(value).forEach(collect);
      }
    })(read(join(site, path)));
    partsOf.set(path, ids);
  }
  return partsOf.get(path);
};
let links = 0;
for (const file of files.filter((name) => name.endsWith(".json"))) {
  const check = (link) => {
    links += 1;
    if (/^[a-z]+:/i.test(link)) {
      // Nothing of the guide's own is named by an address: the site may move.
      if (link.startsWith(sitePrefix)) fail(`${file}: ${link} names the guide by its address instead of a relative path`);
      return;
    }
    const [path, fragment] = link.split("#");
    const target = path ? posix(join(dirname(file), path)) : file;
    if (target === "ro-crate-metadata.json") {
      /* A topic target (`#resources?station=assessment`) names its list; the content check checks the topic. */
      if (fragment && !crateIds.has("#" + fragment.split("?")[0])) fail(`${file}: ${link} names no entity of the crate`);
      return;
    }
    if (target === "." || target === "./") return; // the guide's page, with a route in the fragment
    if (!existsSync(join(site, target))) fail(`${file}: the link ${link} leads to no file`);
    else if (fragment && !partIds(target).has("#" + fragment)) fail(`${file}: the link ${link} names no part of ${target}`);
  };
  (function walk(value, key) {
    if (Array.isArray(value)) return value.forEach((item) => walk(item, key));
    if (value && typeof value === "object") return Object.entries(value).forEach(([inner, item]) => walk(item, inner));
    if (typeof value === "string" && (linkKeys.has(key) || key === "@context")) check(value);
  })(read(join(site, file)), null);
}

// The health snapshot is ordinary JSON and retains the scope of every claim. A fresh build must not
// masquerade as a completed check run; final check_all publication is checked again with --health-only.
const health = read(join(site, "api/health.json"));
if (health["@context"]) fail("api/health.json: ordinary check evidence must not claim a JSON-LD context");
if (!read(join(site, "api/meta.json")).hasPart.includes("health.json")) fail("api/meta.json: no link to the health snapshot");
if (health.live_availability.status !== "unchecked") fail("api/health.json: an offline inventory claims live availability");
if (health.run.status === "not_run" && (health.generated_at !== null || health.run.jobs.length)) fail("api/health.json: a build inventory claims completed checks");
if (health.run.status !== "not_run" && (typeof health.generated_at !== "string" || !Number.isFinite(Date.parse(health.generated_at)))) fail("api/health.json: completed run has no actual report timestamp");
if (health.run.status === "passed" && health.run.jobs.some((job) => ["failed", "blocked"].includes(job.status))) fail("api/health.json: a passed run includes a failed or blocked check");
if (new Set(health.run.jobs.map((job) => job.name)).size !== health.run.jobs.length) fail("api/health.json: duplicate check-run identities");
let failedItems = 0;
for (const group of health.integrity) {
  const failed = group.items.filter((item) => item.status === "failed").length;
  const passed = group.items.filter((item) => item.status === "passed").length;
  failedItems += failed;
  if (group.count !== group.items.length || group.failed !== failed || group.passed !== passed) fail(`api/health.json: inconsistent integrity counts for ${group.type}`);
}
if (health.integrity_failed !== failedItems) fail("api/health.json: inconsistent total integrity failures");
for (const kind of ["clauses", "questions", "advice"]) {
  const counts = health.original_coverage.counts[kind];
  if (!counts) continue; // An unreadable-content diagnostic makes no coverage claim.
  const items = health.original_coverage[kind];
  const withOriginal = items.filter((item) => kind === "clauses" ? item.has_original : item.originals.length > 0).length;
  if (counts.total !== items.length || counts.with_original !== withOriginal) fail(`api/health.json: inconsistent original-coverage counts for ${kind}`);
  if (kind !== "clauses") {
    for (const item of items) {
      const actual = item.originals.length ? item.missing_originals.length ? "partial" : "complete" : item.reviewed_basis ? "reviewed_source_links" : "no_original";
      if (item.status !== actual) fail(`api/health.json: inaccurate original-coverage status for ${item.id}`);
      if (new Set([...item.originals, ...item.missing_originals]).size !== item.citations.length) fail(`api/health.json: lost citation coverage for ${item.id}`);
    }
  }
}

if (healthOnly) {
  if (failures.length) {
    console.error(failures.map((failure) => "FAIL " + failure).join("\n"));
    process.exit(1);
  }
  console.log(`Health API checks passed (${health.run.status} run snapshot, ${links} record links)`);
  process.exit(0);
}

// 4. The documentation page: its own policy, no inline script, and over HTTP it works within the site.
const docsPage = readFileSync(join(site, "api/index.html"), "utf8");
if (!/<meta http-equiv="Content-Security-Policy" content="[^"]*connect-src 'self'/.test(docsPage)) fail("api/index.html: no content security policy that keeps requests on the site");
if (/<script(?![^>]*\bsrc=)[^>]*>/.test(docsPage)) fail("api/index.html: an inline script");
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".jsonld": "application/ld+json", ".svg": "image/svg+xml", ".png": "image/png" };
const server = createServer((request, response) => {
  const path = decodeURIComponent(new URL(request.url, "http://localhost").pathname).replace(/\/$/, "/index.html");
  const candidate = join(site, path);
  const file = candidate.startsWith(site + sep) && existsSync(candidate) && statSync(candidate).isFile() ? candidate : null;
  if (!file) {
    response.writeHead(404).end();
    return;
  }
  response.writeHead(200, { "Content-Type": types[extname(file)] || "application/octet-stream" }).end(readFileSync(file));
});
await new Promise((ready) => server.listen(0, "127.0.0.1", ready));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch();
const page = await browser.newPage();
const outside = [];
const problems = [];
page.on("request", (request) => {
  if (!request.url().startsWith(origin) && !request.url().startsWith("data:")) outside.push(request.url());
});
page.on("console", (message) => {
  if (message.type() === "error") problems.push(message.text());
});
page.on("pageerror", (error) => problems.push(error.message));
await page.goto(origin + "/api/");
await page.waitForSelector("#operations-principles-listPrinciples", { timeout: 30000 });
if (!(await page.locator(".info .title").textContent()).includes(openapi.info.title)) fail("documentation page: the title of the description does not show");
await page.locator("#operations-principles-listPrinciples .opblock-summary").first().click();
await page.locator("#operations-principles-listPrinciples .try-out__btn").click();
await page.locator("#operations-principles-listPrinciples .execute").click();
await page.waitForSelector("#operations-principles-listPrinciples .live-responses-table tr.response .response-col_status", { timeout: 30000 });
const status = (await page.locator("#operations-principles-listPrinciples .live-responses-table tr.response .response-col_status").first().textContent()).trim();
const body = await page.locator("#operations-principles-listPrinciples .live-responses-table tr.response .response-col_description").first().textContent();
if (status !== "200" || !body.includes("R1.1")) fail(`documentation page: trying the principles list returned ${status} without R1.1`);
if (outside.length) fail("documentation page: requests left the site: " + outside.join(", "));
for (const problem of problems) fail("documentation page: " + problem);
await browser.close();
server.close();

if (failures.length) {
  console.error(failures.map((failure) => "FAIL " + failure).join("\n"));
  console.error(`${failures.length} problem(s)`);
  process.exit(1);
}
console.log(`API checks passed (${files.length} files, ${links} links, the documentation page)`);
