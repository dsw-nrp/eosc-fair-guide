// Source/criterion boundaries: no browser or remote service is needed for these pure mappings.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { runInNewContext } from "node:vm";

const root = resolve(import.meta.dirname, "../..");
const FG = { config: { discovery: { schemaVocabulary: "https://schema.org/", codeMetaVocabulary: "https://codemeta.github.io/terms/",
  codeMetaContexts: ["https://doi.org/10.5063/schema/codemeta-2.0"], conformsTo: "http://purl.org/dc/terms/conformsTo" },
  connectors: [{ id: "doi", origin: "https://doi.org" }, { id: "handle", origin: "https://hdl.handle.net" }] },
  list: (value) => value == null ? [] : Array.isArray(value) ? value : [value], selfcheck: {},
  unsafeKey: (name) => ["__proto__", "constructor", "prototype"].includes(name) };
for (const script of ["assets/js/live.js", "assets/js/assess.js", "assets/js/discovery.js", "assets/js/tests/object.js", "assets/js/tests/software.js"])
  runInNewContext(readFileSync(resolve(root, script), "utf8"), { window: { FairGuide: FG }, URL });
const registered = Object.keys(FG.selfcheck.localTests).sort();
const declared = [...readFileSync(resolve(root, "content/live.toml"), "utf8").matchAll(/^id = "(guide-[^"]+)"$/gm)].map((match) => match[1]).sort();
assert.deepEqual(registered, declared, "every executed local criterion has one declared test identity");
const pid = { type: "doi", value: "10.1234/example" };
const landing = "https://archive.example/record/one";
const representation = (data, extra = {}) => ({ source: "landing", url: landing, identity: "matched", format: "application/ld+json", data, profiles: [], ...extra });
const discovery = (representations, extra = {}) => ({ input: pid.value, pid, date: "2026-10-11T12:00:00Z", resolved: { found: true, url: landing, values: [{ type: "URL", value: landing }] }, representations, ...extra });
const assess = (id, result, sample) => FG.selfcheck.assessObject({ identifier: id }, result, sample);
const get = (observations, id) => observations.find((observation) => observation.id === id);

const ordinary = discovery([representation({ "@context": "https://schema.org", identifier: "https://doi.org/" + pid.value,
  name: "A title", description: "A short abstract", license: "https://creativecommons.org/licenses/by/4.0/",
  distribution: { contentUrl: "https://archive.example/files/data.csv" } })]);
assert.equal(get(assess("dataset", ordinary), "dataset.04").value, "yes");
assert.equal(get(assess("dataset", ordinary), "dataset.06").value, "partly", "description fragments do not complete a compound criterion");
const cdif = assess("cdif", ordinary);
assert.equal(get(cdif, "cdif.03").value, "yes");
assert.equal(get(cdif, "cdif.03").testId, "guide-cdif-03");
assert.equal(FG.selfcheck.localTests["guide-cdif-03"](cdif).length, 1, "the declared entry point selects only its criterion");
assert(FG.selfcheck.localTests["guide-cdif-04"](cdif).every((entry) => entry.id === "cdif.04"));
assert.equal(get(cdif, "cdif.04").value, "partly", "a licence does not establish every access/right condition");
assert.equal(get(cdif, "cdif.10").value, "partly");
assert(!get(cdif, "cdif.27"), "Schema.org JSON-LD is not CDIF profile conformance");
assert(!get(cdif, "cdif.05"), "a generic JSON-LD context is not a declared CDIF profile");
assert(!get(assess("fdo", ordinary), "fdo.27"), "a generic type is not an FDO type");
assert.equal(get(assess("fdo", ordinary), "fdo.02").value, "partly", "typed resolver values do not validate a PID profile");
assert(!get(assess("fdo", ordinary), "fdo.12"), "preservation needs evidence beyond a live record");
assert(!get(assess("dataset", discovery([], { pid: null, input: landing })), "dataset.01"), "landing reachability is not a persistent identifier");

for (const context of [{ "@vocab": "https://schema.org/", license: "https://other.example/rights" }, ["https://schema.org", null], ["https://schema.org", "https://unknown.example/context"]]) {
  assert(!get(assess("dataset", discovery([representation({ "@context": context, license: "https://example.org/licence" })])), "dataset.04"), "term overrides/reset/unknown contexts must stay unmapped");
}
assert(!get(assess("cdif", discovery([representation({ "@context": "https://schema.org", distribution: { "@context": { contentUrl: "https://other.example/foo" }, contentUrl: "https://example.org/file" } })])), "cdif.03"), "nested context overrides are respected");
assert(!get(assess("dataset", discovery([representation({ "https://schema.org/license": "https://example.org/licence" }, { identity: "mismatched" })])), "dataset.04"));
const profiles = assess("cdif", discovery([representation({ "@context": "https://schema.org", identifier: "https://doi.org/" + pid.value }, { profiles: ["https://example.org/profile/v1"] })]));
assert.equal(get(profiles, "cdif.05").value, "yes", "explicit declaration can answer the declaration question");
assert(!get(profiles, "cdif.27"), "the declaration does not validate that profile");
assert(assess("maturity", ordinary, true).every((entry) => entry.value !== "yes" && entry.subject === "https://doi.org/" + pid.value), "sample evidence retains its subject and cannot establish repository-wide compliance");

const software = { supported: true, provider: "github", url: "https://github.com/team/research", commit: "a".repeat(40), date: "2026-10-11T12:00:00Z",
  metadata: { name: "Research", visibility: "public" }, files: [], coverage: { readFiles: 0, selectedFiles: 0 } };
const file = (path, kind, text) => ({ path, kind, text, url: software.url + "/blob/" + software.commit + "/" + path });
const sw = (files, extra = {}) => FG.selfcheck.assessSoftware({ identifier: "software" }, { ...software, files, ...extra });
assert.equal(get(sw([]), "software.09").value, "yes");
assert.equal(get(sw([]), "software.09").testId, "guide-software-09");
const relative = assess("cdif", discovery([representation({ "@context": "https://schema.org", license: "../licence", distribution: { contentUrl: "files/data.csv" } })]));
assert.equal(get(relative, "cdif.03").fields[0].values[0], "https://archive.example/record/files/data.csv");
assert.equal(get(relative, "cdif.04").fields[0].values[0], "https://archive.example/licence");
const microdata = assess("cdif", discovery([representation({ "@context": "https://schema.org", name: ["Dataset"], license: ["../licence"], distribution: [{ contentUrl: ["files/data.csv", "files/description.txt"] }] }, { format: "text/html;profile=microdata" })]));
assert.equal(get(microdata, "cdif.03").value, "yes");
assert.deepEqual(Array.from(get(microdata, "cdif.03").fields[0].values), ["https://archive.example/record/files/data.csv", "https://archive.example/record/files/description.txt"]);
assert.equal(get(sw([]), "software.03").value, "partly", "one commit does not prove every release is identified");
assert(!get(sw([file("package.json", "dependency-build", '{"name":"package"}')]), "software.13"), "a manifest filename is not a dependency declaration");
assert.equal(get(sw([file("package.json", "dependency-build", '{"dependencies":{"library":"1.0"}}')]), "software.13").value, "partly");
assert.equal(get(sw([file("LICENSE", "licence", "MIT licence content")]), "software.15").value, "partly", "one licence cannot cover all bundled components automatically");
assert(!get(sw([file("test/check.js", "test-definition", 'throw new Error("unrelated file");')]), "software.14"), "a test-directory filename alone is not a test definition");
assert.equal(get(sw([file("test/check.js", "test-definition", 'test("example", () => assert(true));')]), "software.14").value, "partly");
assert(!get(sw([file("CITATION.cff", "citation", 'authors:\n  - name: Research team\npreferred-citation:\n  type: article\n  doi: 10.1234/paper\n  authors:\n    - family-names: Paper-author\n')]), "software.07"), "a preferred-citation DOI describes a different object");
const codemeta = (identifier) => file("codemeta.json", "software-metadata", JSON.stringify({ "@context": "https://doi.org/10.5063/schema/codemeta-2.0", "@type": "SoftwareSourceCode", codeRepository: software.url, identifier }));
assert(!get(sw([codemeta("not-an-identifier")]), "software.07"));
assert.equal(get(sw([codemeta("https://doi.org/10.1234/software")]), "software.07").value, "partly", "a declared PID target has not been checked");
assert(!get(sw([file("codemeta.json", "software-metadata", JSON.stringify({ "@context": ["https://schema.org", { SoftwareSourceCode: "https://other.example/Type" }], "@type": "SoftwareSourceCode", codeRepository: software.url, identifier: software.url }))]), "software.07"), "a remapped type cannot establish the software metadata subject");
assert(!get(sw([file("codemeta.json", "software-metadata", JSON.stringify({ "@context": "https://schema.org", "@type": "SoftwareSourceCode", codeRepository: "https://github.com/another/project", identifier: software.url }))]), "software.07"));
assert.equal(sw([], { commit: null }).length, 0, "an unresolved ref cannot produce immutable-commit evidence");

// Discovery's identity, the object readers and CodeMeta reading share one bounded context resolver.
const doi = "https://doi.org/" + pid.value;
const identity = (data) => FG.live.identityMatch(data, pid, landing, false, landing);
const readers = (data) => [identity(data), Boolean(get(assess("cdif", discovery([representation(data)])), "cdif.01"))];
const shared = [
  [{ "@context": "https://schema.org", identifier: doi }, ["matched", true]],
  [{ "@context": "https://doi.org/10.5063/schema/codemeta-2.0", identifier: doi }, ["matched", true]],
  [{ "@context": { s: "https://schema.org/" }, "s:identifier": doi }, ["matched", true]],
  [{ "@context": { id: "https://schema.org/identifier", ident: "id" }, ident: doi }, ["matched", true]],
  [{ "http://schema.org/identifier": doi }, ["matched", true]],
  [{ "@context": ["https://schema.org", "https://unknown.example/context"], identifier: doi }, ["unverified", false]],
  [{ "@context": ["https://schema.org", null], identifier: doi }, ["unverified", false]],
  [{ "@context": ["https://schema.org", { identifier: "https://other.example/id" }], identifier: doi }, ["unverified", false]],
  [{ "@context": ["https://schema.org", { identifier: { "@reverse": "https://schema.org/identifier" } }], identifier: doi }, ["unverified", false]],
  [{ "@context": { a: "b", b: "a" }, a: doi }, ["unverified", false]],
  [{ "@context": Array(17).fill("https://schema.org"), identifier: doi }, ["unverified", false]],
  [JSON.parse(`{"@context": {"__proto__": {"identifier": "https://schema.org/identifier"}}, "identifier": "${doi}"}`), ["unverified", false]],
  [{ "@context": "https://schema.org", identifier: "https://doi.org/10.1234/another" }, ["mismatched", true]],
];
for (const [data, expected] of shared) assert.deepEqual(readers(data), expected, JSON.stringify(data["@context"] ?? Object.keys(data)));
assert.equal(({}).identifier, undefined, "a context cannot reach Object.prototype");
for (const [data] of shared) assert.deepEqual(Array.from(FG.jsonLd.propertyValues(data, "identifier")).slice(0, 1), [FG.jsonLd.property(data, "identifier")].filter(Boolean),
  "assessment reads the first value identity reads");
const curie = (extra) => file("codemeta.json", "software-metadata", JSON.stringify({ "@context": ["https://doi.org/10.5063/schema/codemeta-2.0", { s: "https://schema.org/" }],
  "@type": "SoftwareSourceCode", "s:codeRepository": software.url, ...extra }));
assert.equal(get(sw([curie({ identifier: "https://doi.org/10.1234/software", developmentStatus: "active" })]), "software.05").value, "partly", "CodeMeta terms stay known beside a prefix");
assert.equal(get(sw([curie({ identifier: "https://doi.org/10.1234/software" })]), "software.07").value, "partly");
assert(!get(sw([file("codemeta.json", "software-metadata", JSON.stringify({ "@context": "https://unknown.example/context", "@type": "SoftwareSourceCode", codeRepository: software.url, identifier: software.url }))]), "software.07"), "an unknown context identifies no software subject");
assert(!get(sw([]), "software.18"), "repository inspection does not execute examples");
assert(!get(sw([]), "software.19"), "a source repository is not archival preservation");
console.log("check_assess: conservative object/software mappings and adversarial context fixtures pass");
