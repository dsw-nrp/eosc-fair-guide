// Deterministic browser fixtures for shared discovery and public software connectors. No service is called.
// Run directly without a site build: node tests/page/check_discovery.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const { chromium } = await import("playwright");
// The connector tables use only JSON-compatible TOML scalars and arrays. Read the committed configuration
// without a site build or another interpreter; fail if a relevant field gains an unsupported value shape.
const sections = readFileSync(resolve(root, "content/live.toml"), "utf8").split(/(?=^\[)/m);
function table(section) {
  const result = {};
  for (const line of section.split(/\r?\n/).slice(1)) {
    if (!line.trim() || line.trim().startsWith("#")) continue;
    const pair = line.match(/^(\w+)\s*=\s*(.+)$/);
    assert(pair, "unexpected connector configuration field: " + line);
    result[pair[1]] = JSON.parse(pair[2]);
  }
  return result;
}
const config = {
  connectors: sections.filter((section) => section.startsWith("[[connector]]")).map(table),
  discovery: table(sections.find((section) => section.startsWith("[discovery]"))),
  software: table(sections.find((section) => section.startsWith("[software]"))),
};
// Fictitious reviewed origins exercise exactly the same declarative discovery path; no provider adapter
// participates in these fixtures. Every actual network request is blocked by the browser route below.
config.connectors.push({ id: "fixture-object-a", name: "Reviewed fixture A", origin: "https://archive-a.example" },
  { id: "fixture-object-b", name: "Reviewed fixture B", origin: "https://archive-b.example" });
config.discovery.connectors = ["fixture-object-a", "fixture-object-b"];
const code = readFileSync(resolve(root, "assets/js/live.js"), "utf8");
const discoveryCode = readFileSync(resolve(root, "assets/js/discovery.js"), "utf8");
const browser = await chromium.launch();
const page = await browser.newPage();
const external = [];
let moduleLoads = 0;
await page.route("**/*", async (route) => {
  if (route.request().url().endsWith("/assets/js/discovery.js")) {
    moduleLoads += 1;
    await route.fulfill({ contentType: "text/javascript", body: discoveryCode });
  } else if (route.request().url().endsWith("/fixture.html")) {
    await route.fulfill({ contentType: "text/html", body: "<!doctype html><title>Discovery fixtures</title>" });
  } else { external.push(route.request().url()); await route.abort(); }
});
try {
  await page.goto("https://guide.example/fixture.html");
  await page.evaluate((configuration) => {
    window.requests = [];
    window.FairGuide = { config: configuration, list: (value) => value == null ? [] : Array.isArray(value) ? value : [value] };
    window.fetch = async () => { throw new Error("unexpected request on load"); };
  }, config);
  await page.addScriptTag({ content: code });
  assert.equal(await page.evaluate(() => window.requests.length), 0, "connector evaluation starts no request");
  assert.equal(moduleLoads, 0, "discovery code stays deferred until a user action");

  async function fixture(routes, overrides = {}) {
    await page.evaluate(({ routes, overrides, configuration }) => {
      window.FairGuide.config = structuredClone(configuration);
      for (const key of ["discovery", "software"]) Object.assign(window.FairGuide.config[key], overrides[key] || {});
      window.requests = [];
      window.executedRepositoryCode = false;
      window.fetch = async (url, options) => {
        window.requests.push({ url: String(url), method: options.method, credentials: options.credentials,
          redirect: options.redirect, referrerPolicy: options.referrerPolicy, accept: options.headers.Accept });
        const route = routes[String(url)];
        if (!route) throw new Error("no fixture for " + url);
        if (route.error) throw new TypeError(route.error);
        const response = new Response(route.text ?? JSON.stringify(route.data), { status: route.status || 200,
          headers: { "content-type": route.type || "application/json", ...(route.headers || {}) } });
        if (route.redirectUrl) Object.defineProperty(response, "url", { value: route.redirectUrl });
        return response;
      };
    }, { routes, overrides, configuration: config });
  }
  const discover = (input) => page.evaluate((value) => window.FairGuide.live.discoverObject(value), input);
  const software = (input, ref) => page.evaluate(({ input, ref }) => window.FairGuide.live.softwareRepository(input, { ref }), { input, ref });
  const calls = () => page.evaluate(() => window.requests);
  const doi = "10.1234/target";
  const resolver = "https://doi.org/api/handles/10.1234/target";
  const datacite = "https://api.datacite.org/dois/10.1234%2Ftarget";
  const landing = "https://archive-a.example/object/42";
  const metadataApi = "https://archive-a.example/metadata/record.jsonld";
  const registry = { doi, url: landing, titles: [{ title: "Target" }], schemaVersion: "DataCite Metadata Schema 4.6" };
  const initial = {
    [resolver]: { data: { responseCode: 1, values: [{ type: "URL", data: { value: landing, format: "string" } },
      { type: "FDO_TEST_TYPE", data: { value: { registeredType: "fixture-only" }, format: "fixture" }, index: 2 }] } },
    [datacite]: { data: { data: { attributes: registry } } },
  };

  await fixture({});
  const concurrent = await Promise.all([discover("urn:nbn:cz:example"), software("https://institution.example/group/tool")]);
  let result = concurrent[0];
  assert.equal(moduleLoads, 1, "concurrent user actions load the local connector code once");
  assert.equal(result.supported, false);
  assert.equal(result.diagnostics[0].code, "unsupported-pid");
  assert.equal((await calls()).length, 0, "unsupported managed PID keeps manual assessment without a request");

  const profile = "https://profiles.example/declared";
  const context = { "@vocab": "https://schema.org/", conformsTo: { "@id": "http://purl.org/dc/terms/conformsTo", "@type": "@id" } };
  const outcomes = [];
  for (const origin of ["https://archive-a.example", "https://archive-b.example"]) {
    const subject = origin + "/object/42";
    const linked = origin + "/metadata/target.jsonld";
    const wrong = origin + "/metadata/another.jsonld";
    const linkset = origin + "/metadata/links";
    const unlinkedApi = origin + "/metadata/record.jsonld";
    await fixture({ ...initial,
      [resolver]: { data: { responseCode: 1, values: [{ type: "URL", data: { value: subject, format: "string" } },
        { type: "FDO_TEST_TYPE", data: { value: { registeredType: "fixture-only" }, format: "fixture" } }] } },
      [datacite]: { data: { data: { attributes: { ...registry, url: subject } } } },
      [subject]: { type: "text/html", text: `<title>Target</title><img src="https://unreviewed.example/image"><iframe src="https://unreviewed.example/frame"></iframe>
        <script>window.executedRepositoryCode = true</script><link rel="describedby" href="${wrong}" type="application/ld+json">
        <link rel="profile" href="${profile}"><script type="application/ld+json">${JSON.stringify({ "@context": context, "@graph": [{ "@id": subject, identifier: doi, "@type": "Dataset", name: "Target JSON-LD" }] })}</script>`,
        headers: { link: `<${linkset}>; rel="linkset"; type="application/linkset+json", <https://unreviewed.example/meta>; rel="describedby"; type="application/json"` } },
      [wrong]: { type: "application/ld+json", data: { "@context": context, "@id": subject, identifier: "10.1234/another", name: "Wrong object" } },
      [linkset]: { type: "application/linkset+json", data: { linkset: [{ anchor: subject, describedby: [{ href: linked, type: "application/ld+json" }], profile: [{ href: profile }] }] } },
      [linked]: { type: "application/ld+json", data: { "@context": context, "@graph": [
        { identifier: { propertyID: "DOI", value: doi }, name: "Linked target", conformsTo: profile },
        { "@context": { "@vocab": "https://other.example/vocabulary/" }, "@id": subject, name: "Different vocabulary", conformsTo: profile },
        { "@context": null, "@id": subject, name: "Reset context" },
      ] } },
      [unlinkedApi]: { type: "application/ld+json", data: { identifier: doi, name: "Undeclared API record" } },
    });
    result = await discover(doi);
    assert(result.representations.some((entry) => entry.format === "text/html"));
    assert(result.representations.some((entry) => entry.data.name === "Target JSON-LD"));
    const linkedRepresentation = result.representations.find((entry) => entry.data.name === "Linked target");
    assert(linkedRepresentation);
    assert.deepEqual(linkedRepresentation.data["@context"], context, "selected graph nodes inherit their enclosing JSON-LD context");
    assert.deepEqual(linkedRepresentation.declarations, [{ predicate: "conformsTo", value: profile }], "profile declarations retain their raw predicate separately from validation");
    assert.deepEqual(result.representations.find((entry) => entry.data.name === "Different vocabulary").data["@context"], { "@vocab": "https://other.example/vocabulary/" }, "a node's own vocabulary remains distinct");
    assert.equal(result.representations.find((entry) => entry.data.name === "Reset context").data["@context"], null, "explicit null resets rather than inherits JSON-LD context");
    assert(!result.representations.some((entry) => entry.data.name === "Wrong object"), "a conflicting DOI overrides a matching landing URL");
    assert(result.diagnostics.some((entry) => entry.code === "identity-mismatched" && entry.url === wrong));
    assert(result.diagnostics.some((entry) => entry.code === "unsupported-origin" && entry.url.includes("unreviewed")));
    assert(result.observations.some((entry) => entry.kind === "declared-profile" && entry.value === profile));
    assert(!result.observations.some((entry) => /conform|fdo-type/i.test(entry.kind)), "JSON-LD, schema version, labels and profile declarations are not conformance");
    assert(result.representations.filter((entry) => entry.source !== "datacite").every((entry) => entry.source === "landing"));
    assert.deepEqual(result.resolved.values[1].value, { registeredType: "fixture-only" }, "typed PID values are retained without reinterpreting them");
    assert(result.observations.some((entry) => entry.kind === "pid-record" && entry.source === "pid-record"));
    assert.equal(await page.evaluate(() => window.executedRepositoryCode), false, "external HTML stays inert");
    assert.equal(external.length, 0, "parsing external HTML never requests images or frames");
    assert(!(await calls()).some((entry) => entry.url === unlinkedApi), "API paths are never guessed from a hostname or record path");
    assert(!(await calls()).some((entry) => entry.url.includes("schema.org")), "remote JSON-LD contexts are preserved without fetching them");
    outcomes.push(result.representations.map((entry) => [entry.source, entry.format, entry.data.name || entry.data.title || "registry"]));
  }
  assert.deepEqual(outcomes[0], outcomes[1], "equivalent declared representations produce equivalent discovery on two unrelated reviewed origins");

  await fixture({ ...initial, [landing]: { type: "text/html", text: `<script type="application/ld+json">${JSON.stringify({ "@context": { "@vocab": "https://schema.org/", identifier: "https://other.example/label" }, identifier: doi, name: "Unverified subject" })}</script>` } });
  result = await discover(doi);
  assert(!result.representations.some((entry) => entry.data.name === "Unverified subject"), "an overridden compact identifier cannot establish metadata identity");
  assert(result.diagnostics.some((entry) => entry.code === "identity-unverified"));

  const rawLinked = "https://archive-a.example/metadata/raw.jsonld";
  await fixture({
    [landing]: { type: "text/html", text: `<title>Raw URL target</title><link rel="describedby" href="${rawLinked}" type="application/ld+json">` },
    [rawLinked]: { type: "application/ld+json", data: { "@context": context, "@id": landing, identifier: doi, name: "Raw linked target", conformsTo: profile } },
  });
  result = await discover(landing);
  assert.equal(result.supported, true);
  assert.equal(result.pid, null);
  assert.equal(result.resolved.found, true);
  assert.equal(result.resolved.url, landing);
  assert.equal(result.resolved.title, "Raw URL target");
  assert.equal(result.datacite, null);
  assert(result.representations.some((entry) => entry.data.name === "Raw linked target" && entry.subject === landing));
  assert(!(await calls()).some((entry) => [resolver, datacite].includes(entry.url)), "raw landing URLs skip resolver and registry requests");
  const textLinks = "https://archive-a.example/metadata/linkset.txt";
  await fixture({ ...initial,
    [landing]: { type: "text/html", text: `<title>Standard metadata</title>
      <a rel="linkset" href="/metadata/linkset.txt">Metadata links</a>
      <div itemscope itemtype="https://schema.org/Dataset" itemid="${landing}" itemref="dates">
        <meta itemprop="identifier" content="${doi}"><h1 itemprop="name">Microdata target</h1>
        <a itemprop="license" href="https://licences.example/cc-by">Licence</a>
        <div itemprop="distribution" itemscope itemtype="https://schema.org/DataDownload"><a itemprop="contentUrl" href="/data/table.csv">Download</a></div>
        <div itemscope itemtype="https://schema.org/Organization"><span itemprop="name">Unrelated nested organisation</span></div>
      </div><div id="dates"><time itemprop="datePublished" datetime="2026-01-02">January</time></div>
      <div itemscope itemtype="https://schema.org/Dataset"><meta itemprop="identifier" content="10.1234/wrong"><span itemprop="name">Wrong microdata object</span></div>
      <div typeof="schema:Dataset">Uninterpreted RDFa</div>` },
    [textLinks]: { type: "application/linkset", text: `<${rawLinked}>; rel="describedby"; anchor="${landing}"; type="application/ld+json"` },
    [rawLinked]: { type: "application/ld+json", data: { "@context": "https://schema.org", "@id": "../object/42", name: "Relative identity" } },
  });
  result = await discover(doi);
  const micro = result.representations.find((entry) => entry.format === "text/html;profile=microdata" && entry.data.name?.includes("Microdata target"));
  assert(micro, "Schema.org microdata is inspected independently of the repository provider");
  assert.deepEqual(micro.data.datePublished, ["2026-01-02"], "itemref properties use their machine-readable values");
  assert.deepEqual(micro.data.distribution[0].contentUrl, ["https://archive-a.example/data/table.csv"], "nested distribution URLs resolve against the document");
  assert.deepEqual(micro.data.name, ["Microdata target"], "nested item properties cannot leak into the outer subject");
  assert(!result.representations.some((entry) => entry.data.name?.includes("Wrong microdata object")), "other objects' microdata is rejected");
  assert(result.representations.some((entry) => entry.data.name === "Relative identity"), "text linksets and relative JSON-LD identities are supported");
  assert(result.diagnostics.some((entry) => entry.code === "unsupported-format" && entry.message.includes("RDFa")), "uninterpreted standard markup is disclosed, never reported absent");
  assert.equal(external.length, 0, "microdata parsing makes no embedded-resource request");
  await fixture({ [landing]: { error: "CORS fixture" } });
  result = await discover(landing);
  assert.equal(result.supported, true);
  assert.equal(result.resolved, null, "URL syntax alone is never a successful resolution observation");
  assert(result.diagnostics.some((entry) => entry.code === "unavailable" && entry.url === landing));
  await fixture({});
  result = await discover("https://unreviewed.example/object/42");
  assert.equal(result.resolved, null);
  assert(result.diagnostics.some((entry) => entry.code === "unsupported-origin"));
  assert.equal((await calls()).length, 0, "raw URLs retain the reviewed-origin boundary");

  const linked = "https://archive-a.example/metadata/target.jsonld";
  await fixture({ ...initial, [landing]: { error: "Failed to fetch (CORS fixture)" },
    [datacite]: { data: { data: { attributes: { ...registry, relatedIdentifiers: [{ relationType: "HasMetadata", relatedIdentifierType: "URL", relatedIdentifier: metadataApi }] } } } },
    [metadataApi]: { type: "application/ld+json", data: { "@context": "https://schema.org", identifier: doi, name: "Declared API record" },
      headers: { link: `<${linked}>; rel="describedby"; type="application/ld+json"` } },
    [linked]: { type: "application/ld+json", data: { "@context": "https://schema.org", identifier: doi, name: "API linked target" } },
  });
  result = await discover(doi);
  assert(result.diagnostics.some((entry) => entry.code === "unavailable" && entry.url === landing));
  assert(result.representations.some((entry) => entry.source === "landing" && entry.url === metadataApi));
  assert(result.representations.some((entry) => entry.data.name === "API linked target"), "explicit metadata relations and readable Link headers supply generic discovery routes");
  assert(!(await calls()).some((entry) => entry.url.includes("ostrails")), "quick discovery never starts FAIR Champion");
  await fixture({ ...initial, [landing]: { error: "Failed to fetch (CORS fixture)" },
    [metadataApi]: { type: "application/ld+json", data: { identifier: doi, name: "Undeclared API record" } },
  });
  result = await discover(doi);
  assert(!result.representations.some((entry) => entry.source === "landing"), "unreadable landing without a declared route remains unverified");
  assert(!(await calls()).some((entry) => entry.url === metadataApi), "CORS never triggers a guessed endpoint or named adapter");

  const unsupported = "https://institution.example/record/1";
  await fixture({ ...initial, [resolver]: { data: { responseCode: 1, values: [{ type: "URL", data: { value: unsupported } }] } } });
  result = await discover(doi);
  assert(result.diagnostics.some((entry) => entry.code === "unsupported-origin" && entry.url === unsupported));
  assert(!(await calls()).some((entry) => entry.url.startsWith(unsupported)), "no arbitrary landing host is fetched");

  await fixture({ ...initial, [landing]: { type: "text/html", text: "x".repeat(1024) } }, { discovery: { maxBytes: 600 } });
  result = await discover(doi);
  assert(result.diagnostics.some((entry) => entry.code === "size-limit" && entry.url === landing), "streamed response is byte-bounded without Content-Length");
  await fixture(initial, { discovery: { maxRequests: 1 } });
  result = await discover(doi);
  assert.equal((await calls()).length, 1, "discovery request cap applies across all sources");
  assert(result.diagnostics.some((entry) => entry.code === "request-limit"));

  const sha = "a".repeat(40), blob = "b".repeat(40), nextSha = "c".repeat(40);
  const github = "https://api.github.com/repos/example/tool";
  const gitlab = "https://gitlab.com/api/v4/projects/example%2Fgroup%2Ftool";
  const encode = (text) => Buffer.from(text).toString("base64");
  const malicious = "window.executedRepositoryCode = true; require('child_process').exec('danger')";
  const githubRoutes = {
    [github]: { data: { private: false, full_name: "example/tool", name: "tool", default_branch: "main", license: { spdx_id: "MIT" } } },
    [github + "/commits/main"]: { data: { sha, commit: { committer: { date: "2026-10-10T12:00:00Z" } } } },
    [github + "/git/trees/" + sha + "?recursive=1"]: { data: { truncated: false, tree: [
      { path: "README.md", type: "blob", mode: "100644", sha: blob, size: 10 },
      { path: "setup.py", type: "blob", mode: "100644", sha: blob, size: malicious.length },
      { path: "download.sh", type: "blob", mode: "100755", sha: blob, size: 10 },
      { path: "tests/test_tool.py", type: "blob", mode: "100644", sha: blob, size: 10 },
      { path: "LICENSE", type: "blob", mode: "120000", sha: blob, size: 10 },
    ] } },
    [github + "/contents/README.md?ref=" + sha]: { data: { path: "README.md", type: "file", sha: blob, size: 10, encoding: "base64", content: encode("# Tool") } },
    [github + "/contents/setup.py?ref=" + sha]: { data: { path: "setup.py", type: "file", sha: blob, size: malicious.length, encoding: "base64", content: encode(malicious) } },
    [github + "/contents/tests/test_tool.py?ref=" + sha]: { data: { path: "tests/test_tool.py", type: "file", sha: blob, size: 10, encoding: "base64", content: encode("assert True") } },
  };
  await fixture(githubRoutes);
  result = await software("https://github.com/example/tool");
  assert.equal(result.commit, sha);
  assert.equal(result.release, null, "default branch is development state, not a release");
  assert.equal(result.files.length, 3);
  assert.equal(result.files.find((entry) => entry.path === "setup.py").text, malicious, "selected build definition remains inert text");
  assert(!result.files.some((entry) => ["download.sh", "LICENSE"].includes(entry.path)), "arbitrary executable scripts and symlinks are not read");
  assert((await calls()).filter((entry) => entry.url.includes("/contents/")).every((entry) => entry.url.endsWith("?ref=" + sha)), "all files use the immutable commit");
  assert(result.files.every((entry) => entry.url.includes(sha) && entry.commit === sha));
  assert.equal(await page.evaluate(() => window.executedRepositoryCode), false);
  assert.equal(result.coverage.listingComplete, true);

  const release = { tag_name: "v1", name: "Version 1", html_url: "https://github.com/example/tool/releases/tag/v1", published_at: "2026-10-01T00:00:00Z" };
  await fixture({ ...githubRoutes, [github + "/commits/v1"]: githubRoutes[github + "/commits/main"],
    [github + "/releases/tags/v1"]: { data: release }, [github + "/commits/refs%2Ftags%2Fv1"]: { data: { sha } } });
  result = await software("https://github.com/example/tool/releases/tag/v1");
  assert.equal(result.release.tag, "v1", "an actual selected release is identified at this commit");
  await fixture({ ...githubRoutes, [github + "/commits/v1"]: githubRoutes[github + "/commits/main"],
    [github + "/releases/tags/v1"]: { data: release }, [github + "/commits/refs%2Ftags%2Fv1"]: { data: { sha: nextSha } } });
  result = await software("https://github.com/example/tool", "v1");
  assert.equal(result.release, null);
  assert(result.diagnostics.some((entry) => entry.code === "release-commit-mismatch"));

  await fixture({});
  result = await software("https://gitlab.institution.example/group/tool");
  assert.equal(result.supported, false);
  assert.equal(result.diagnostics[0].code, "unsupported-host");
  assert.equal((await calls()).length, 0);
  result = await software("https://token@github.com/example/tool");
  assert.equal(result.supported, false, "credential URLs are excluded");

  const gitlabRoutes = {
    [gitlab + "?license=true"]: { data: { visibility: "public", path_with_namespace: "example/group/tool", name: "tool", default_branch: "main" } },
    [gitlab + "/repository/commits/main"]: { data: { id: sha, committed_date: "2026-10-10T12:00:00Z" } },
    [gitlab + "/repository/tree?recursive=true&per_page=100&page=1&ref=" + sha]: { data: [{ path: "CITATION.cff", type: "blob", mode: "100644", id: blob }] },
    [gitlab + "/repository/files/CITATION.cff?ref=" + sha]: { data: { file_path: "CITATION.cff", commit_id: sha, encoding: "base64", size: 10, content: encode("title: Tool") } },
  };
  await fixture(gitlabRoutes);
  result = await software("https://gitlab.com/example/group/tool");
  assert.equal(result.commit, sha);
  assert.equal(result.files[0].path, "CITATION.cff");
  assert.equal(result.files[0].text, "title: Tool");
  await fixture({ ...gitlabRoutes, [gitlab + "/repository/files/CITATION.cff?ref=" + sha]: { ...gitlabRoutes[gitlab + "/repository/files/CITATION.cff?ref=" + sha], data: { ...gitlabRoutes[gitlab + "/repository/files/CITATION.cff?ref=" + sha].data, commit_id: nextSha } } });
  result = await software("https://gitlab.com/example/group/tool");
  assert.equal(result.files.length, 0, "mixed-commit GitLab response is excluded");
  assert(result.diagnostics.some((entry) => entry.code === "identity-mismatched"));

  await fixture({ ...githubRoutes, [github + "/git/trees/" + sha + "?recursive=1"]: { status: 403, headers: { "x-ratelimit-remaining": "0" }, data: { message: "limit" } } });
  result = await software("https://github.com/example/tool");
  assert.equal(result.commit, sha, "earlier commit evidence survives a rate limit");
  assert(result.diagnostics.some((entry) => entry.code === "rate-limit"));
  assert.equal(result.coverage.listingComplete, false);
  await fixture(githubRoutes, { software: { maxRequests: 2 } });
  result = await software("https://github.com/example/tool");
  assert.equal((await calls()).length, 2);
  assert(result.diagnostics.some((entry) => entry.code === "request-limit"));
  await fixture(githubRoutes, { software: { maxFiles: 1 } });
  result = await software("https://github.com/example/tool");
  assert.equal(result.files.length, 1);
  assert(result.diagnostics.some((entry) => entry.code === "file-count-limit"));
  const absentCore = Object.fromEntries(["CITATION.cff", "codemeta.json", "LICENSE", "package.json", "pyproject.toml", "requirements.txt", "Makefile", ".gitlab-ci.yml"]
    .map((path) => [github + "/contents/" + path + "?ref=" + sha, { status: 404, data: { message: "exact path absent" } }]));
  await fixture({ ...githubRoutes, ...absentCore,
    [github + "/git/trees/" + sha + "?recursive=1"]: { data: { ...githubRoutes[github + "/git/trees/" + sha + "?recursive=1"].data, truncated: true } } });
  result = await software("https://github.com/example/tool");
  assert(result.diagnostics.some((entry) => entry.code === "pagination"));
  assert(result.diagnostics.some((entry) => entry.code === "path-not-found"));
  assert.equal(result.coverage.listingComplete, false);
  assert(result.files.some((entry) => entry.path === "README.md"), "truncated inspection keeps attributable files");
  assert((await calls()).filter((entry) => entry.url.includes("/contents/")).every((entry) => entry.url.endsWith("?ref=" + sha)));
  await fixture({ ...gitlabRoutes,
    [gitlab + "/repository/tree?recursive=true&per_page=100&page=1&ref=" + sha]: { ...gitlabRoutes[gitlab + "/repository/tree?recursive=true&per_page=100&page=1&ref=" + sha], headers: { "x-next-page": "2" } } });
  result = await software("https://gitlab.com/example/group/tool");
  assert(result.diagnostics.some((entry) => entry.code === "pagination"));
  assert.equal(result.coverage.listingComplete, false);
  assert(!(await calls()).some((entry) => entry.url.includes("page=2")), "no unbounded tree crawl follows pagination");
  await fixture({ ...githubRoutes, [github + "/git/trees/" + sha + "?recursive=1"]: { data: { tree: [{ path: "README.md", type: "blob", mode: "100644", sha: blob, size: 100000 }] } } });
  result = await software("https://github.com/example/tool");
  assert(result.diagnostics.some((entry) => entry.code === "size-limit"));
  assert(!(await calls()).some((entry) => entry.url.includes("/contents/")), "oversized file is skipped before a file request");
  await fixture({ ...githubRoutes, [github]: { ...githubRoutes[github], redirectUrl: "https://unreviewed.example/repo" } });
  result = await software("https://github.com/example/tool");
  assert(result.diagnostics.some((entry) => entry.code === "unreadable-response"));

  await fixture(githubRoutes);
  await software("https://github.com/example/tool");
  assert((await calls()).every((entry) => entry.method === "GET" && entry.credentials === "omit" && entry.redirect === "error" && entry.referrerPolicy === "no-referrer"), "every bounded request is anonymous, read-only and refuses redirects");
  assert.equal(external.length, 0);
  assert.equal(moduleLoads, 1);
  console.log("PASS public discovery and software repository fixtures");
} finally {
  await browser.close();
}
