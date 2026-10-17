/* Live connectors of the FAIR Data Guide. Every call starts from a user action, goes only to a host on the
   allowlist in the page configuration (content/live.toml), times out, and treats the response as data. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const live = (FG.live = FG.live || {});
  const NKR_KIND = { disciplinary: "#rkind-domain", institutional: "#rkind-institutional", generic: "#rkind-general" };
  const NANOPUB_CODE = /(?:^|[^A-Za-z0-9_-])(RA[A-Za-z0-9_-]{43})(?![A-Za-z0-9_-])/;

  /** The allowlisted connector with this ID; every connector call, including reviewed discovery, looks it up here. */
  function connector(id) {
    const found = FG.config.connectors.find((item) => item.id === id);
    if (!found) throw new Error("unknown connector " + id);
    return found;
  }

  live.connector = connector;
  live.origin = (id) => connector(id).origin;

  /** Whether the service's API admits the guide's origin; a service that does not is used through its snapshot. */
  live.available = (id) => connector(id).browserAccess !== false;

  /** One byte-counting reader for JSON connectors and reviewed discovery, including chunked responses. */
  live.responseText = async function (response, maxBytes) {
    if (!Number.isSafeInteger(maxBytes) || maxBytes <= 0) throw new Error("response byte limit must be a positive integer");
    const tooLarge = () => Object.assign(new Error("response exceeds byte limit"), { code: "size-limit" });
    if (Number(response.headers.get("content-length")) > maxBytes) {
      if (response.body) await response.body.cancel();
      throw tooLarge();
    }
    if (!response.body?.getReader) {
      const text = await response.text();
      if (new TextEncoder().encode(text).byteLength > maxBytes) throw tooLarge();
      return text;
    }
    const reader = response.body.getReader(), decoder = new TextDecoder();
    let bytes = 0, text = "";
    try {
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        bytes += chunk.value.byteLength;
        if (bytes > maxBytes) { await reader.cancel(); throw tooLarge(); }
        text += decoder.decode(chunk.value, { stream: true });
      }
      return text + decoder.decode();
    } finally { reader.releaseLock(); }
  };

  /** Fetch JSON from an allowlisted connector; rejects on timeout, HTTP errors and non-JSON answers. With
      `allowNotFound`, a 404 answer gives null instead of an error. */
  live.fetchJson = async function (connectorId, path, options = {}) {
    const maxBytes = options.maxBytes ?? 4 * 1024 * 1024;
    if (!Number.isSafeInteger(maxBytes) || maxBytes <= 0) throw new Error("response byte limit must be a positive integer");
    const target = connector(connectorId);
    const url = new URL(path, target.origin + "/");
    if (url.origin !== target.origin) throw new Error("refusing a URL outside " + target.origin);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), ((options && options.timeoutSeconds) || 20) * 1000);
    try {
      const response = await fetch(url.href, {
        method: (options && options.method) || "GET",
        headers: Object.assign({ Accept: options.accept || "application/json" }, options.headers || {}),
        body: options && options.body,
        signal: controller.signal,
        credentials: "omit",
        referrerPolicy: "no-referrer",
      });
      if (response.status === 404 && options && options.allowNotFound) return null;
      if (!response.ok) throw new Error(target.name + ": HTTP " + response.status);
      return JSON.parse(await live.responseText(response, maxBytes));
    } finally {
      clearTimeout(timer);
    }
  };

  /* Keep reviewed discovery off the initial download. A local classic script also works from file://. Discovery
     reads JSON-LD with the shared field readers (assess.js), so they load first unless a check already loaded them. */
  let discoveryLoad;
  const loadLocalScript = (path) => new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = path;
    script.onload = resolve;
    script.onerror = () => reject(new Error("The Guide could not load its discovery connector."));
    document.head.append(script);
  });
  function loadDiscovery() {
    if (!discoveryLoad) {
      discoveryLoad = (FG.jsonLd ? Promise.resolve() : loadLocalScript(FG.config.discovery.assessmentScript))
        .then(() => loadLocalScript(FG.config.discovery.script))
        .catch((error) => { discoveryLoad = null; throw error; });
    }
    return discoveryLoad;
  }
  live.discoverObject = async (...args) => { await loadDiscovery(); return live.discoverObject(...args); };
  live.softwareRepository = async (...args) => { await loadDiscovery(); return live.softwareRepository(...args); };
  /** Read a bounded public representation without credentials or redirects, through reviewed discovery. */
  live.fetchText = async (...args) => { await loadDiscovery(); return live.readPublic(...args); };

  /* ---------------------------------------------------------------- identifiers */

  /** Recognise a DOI or a Handle, also when it is written as a resolver link or with a doi:/hdl: prefix. */
  live.parsePid = function (input) {
    let value = String(input || "").trim();
    value = value.replace(/^(?:doi|hdl):\s*/i, "");
    value = value.replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "").replace(/^https?:\/\/hdl\.handle\.net\//i, "");
    try {
      value = decodeURIComponent(value);
    } catch (error) {
      /* Keep the identifier as typed. */
    }
    if (/^10\.\d{4,9}\/\S+$/.test(value)) return { type: "doi", value };
    if (/^\d[\w.-]*\/\S+$/.test(value)) return { type: "handle", value };
    return null;
  };

  /** The resolver link of a parsed identifier. */
  live.pidUrl = (pid) => live.origin(pid.type === "doi" ? "doi" : "handle") + "/" + pid.value;

  /* ORCID iDs, ROR IDs and re3data records are recognised here alone, so search, the identifier helper, the checks
     and the connectors accept the same forms: the bare identifier, or its registry address with or without the scheme,
     "www." and a closing slash. Recognition reads the form; the identifier helper verifies ORCID and ROR checksums. */
  const ORCID_FORM = /^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/;
  const ROR_FORM = /^0[a-hj-km-np-tv-z0-9]{6}\d{2}$/;
  const RE3DATA_FORM = /^r3d\d{9}$/;
  const registryValue = (input, address) =>
    String(input || "").trim().replace(address, "").replace(/[?#].*$/, "").replace(/\/$/, "");

  /** An ORCID iD in its canonical form (upper-case check character), or null. */
  live.parseOrcid = (input) => {
    const value = registryValue(input, /^(?:https?:\/\/)?(?:www\.)?orcid\.org\//i).toUpperCase();
    return ORCID_FORM.test(value) ? value : null;
  };

  /** A ROR ID in its canonical lower-case form, or null. */
  live.parseRor = (input) => {
    const value = registryValue(input, /^(?:https?:\/\/)?(?:www\.)?ror\.org\//i).toLowerCase();
    return ROR_FORM.test(value) ? value : null;
  };

  /** A re3data record identifier (r3d…) written bare or as its re3data address, or null. A re3data DOI names the same
      record only through its resolver: live.re3dataRecord follows it. */
  live.parseRe3data = (input) => {
    const value = registryValue(input, /^(?:https?:\/\/)?(?:www\.)?re3data\.org\/repository\//i).toLowerCase();
    return RE3DATA_FORM.test(value) ? value : null;
  };

  /** Whether a parsed identifier is a DOI that re3data registers for its records (prefix 10.17616). */
  live.isRe3dataDoi = (pid) => Boolean(pid && pid.type === "doi" && /^10\.17616\//.test(pid.value));

  /** The re3data record an input names: an r3d identifier or address directly, or a DOI or Handle whose resolver
      target is a re3data record. Null when it names none or the resolver cannot be asked. */
  live.re3dataRecord = async function (input) {
    const direct = live.parseRe3data(input);
    if (direct) return direct;
    const pid = live.parsePid(input);
    if (!pid) return null;
    try {
      const resolved = await live.resolvePid(pid);
      return live.parseRe3data((resolved && resolved.url) || "");
    } catch (error) {
      return null;
    }
  };

  /** Ask the DOI or Handle resolver whether the identifier exists and where it leads. */
  live.resolvePid = async function (pid, options) {
    const path = "api/handles/" + pid.value.split("/").map(encodeURIComponent).join("/");
    const data = await live.fetchJson(pid.type === "doi" ? "doi" : "handle", path, Object.assign({ allowNotFound: true }, options || {}));
    const found = Boolean(data && data.responseCode === 1);
    const valueOf = (type) =>
      found
        ? FG.list(data.values)
            .filter((value) => value && value.type === type)
            .map((value) => value.data && value.data.value)
            .find((value) => typeof value === "string" && value)
        : null;
    return { found, url: valueOf("URL") || null, title: valueOf("TITLE") || null,
      values: found ? FG.list(data.values).map((value) => ({ type: String(value.type || ""), value: value.data && value.data.value,
        format: value.data && value.data.format, index: value.index })) : [] };
  };

  /** The registration agency of a DOI (DataCite, Crossref, ...), or null when doi.org does not know the DOI. */
  live.doiAgency = async function (doi, options) {
    const data = await live.fetchJson("doi", "ra/" + String(doi).split("/").map(encodeURIComponent).join("/"), options);
    const agency = FG.list(data)[0] || {};
    return agency.RA && !/does not exist|invalid/i.test(String(agency.status || "")) ? String(agency.RA) : null;
  };

  /** The public name behind an ORCID iD, or null when ORCID does not know it. */
  live.orcidName = async function (orcid) {
    const data = await live.fetchJson("orcid", "v3.0/" + encodeURIComponent(orcid) + "/person", { allowNotFound: true });
    if (!data) return null;
    const name = data.name || {};
    const credit = name["credit-name"] && name["credit-name"].value;
    const given = name["given-names"] && name["given-names"].value;
    const family = name["family-name"] && name["family-name"].value;
    return String(credit || [given, family].filter(Boolean).join(" ") || orcid);
  };

  /** The display name of a ROR organisation, or null when ROR does not know it. */
  live.rorName = async function (id) {
    const data = await live.fetchJson("ror", "v2/organizations/" + encodeURIComponent(id), { allowNotFound: true });
    if (!data) return null;
    const names = FG.list(data.names);
    const display = names.find((name) => FG.list(name && name.types).includes("ror_display")) || names[0] || {};
    return String(display.value || id);
  };

  /** DataCite metadata of a DOI, or null when DataCite does not hold it. */
  live.datacite = async function (doi, options) {
    const data = await live.fetchJson("datacite", "dois/" + encodeURIComponent(doi), Object.assign({ allowNotFound: true }, options || {}));
    return data && data.data ? data.data.attributes || {} : null;
  };

  /** Crossref metadata of a DOI, or null when Crossref does not hold it. */
  live.crossref = async function (doi) {
    const data = await live.fetchJson("crossref", "works/" + encodeURIComponent(doi), { allowNotFound: true });
    return data && data.status === "ok" && data.message ? data.message : null;
  };

  /* ---------------------------------------------------------------- FAIR Implementation Profiles */

  /** The trusty URI code of a nanopublication in a code or an address, or null. */
  live.nanopubCode = function (input) {
    const match = String(input || "").match(NANOPUB_CODE);
    return match ? match[1] : null;
  };

  /** A nanopublication IRI as an HTTPS link; purl.org serves its http IRIs over HTTPS as well. */
  live.httpsIri = function (iri) {
    const value = String(iri || "").replace(/^http:(\/\/purl\.org\/)/, "https:$1");
    return value.startsWith("https:") ? value : null;
  };

  live.fipIri = (code) => FG.config.nanopub.fipIri[0].split("{code}").join(code);

  /** Declarations of a published FIP nanopublication: question, relation and declared resource. */
  live.fipDeclarations = async function (code) {
    const config = FG.config.nanopub;
    const iris = config.fipIri.map((form) => "<" + form.split("{code}").join(code) + ">").join(" ");
    const query = config.query.split("{fips}").join(iris);
    const data = await live.fetchJson("nanopub", config.path + "?query=" + encodeURIComponent(query), {
      headers: { Accept: "application/sparql-results+json" },
    });
    const value = (binding) => (binding && binding.value != null ? String(binding.value) : "");
    return FG.list(data && data.results && data.results.bindings).map((row) => ({
      fip: value(row.fip),
      question: value(row.q).split("FIP-Question-").pop(),
      relation: value(row.rel).split("/").pop(),
      fer: value(row.fer),
      label: value(row.ferLabel) || null,
    }));
  };

  /** Current profiles and resources from the FIP Dashboard API, in the shape of the snapshot. */
  live.dashboard = async function () {
    const [fips, resources] = await Promise.all([live.fetchJson("fip-dashboard", "api/fips"), live.fetchJson("fip-dashboard", "api/resources")]);
    return { fips: FG.list(fips), resources: FG.list(resources) };
  };

  /* ---------------------------------------------------------------- FAIR Champion and service status */

  /** Run one FAIR Champion test on an identifier; resolves to the verdict and the test's log. Any failure to get a
      verdict (HTTP error, timeout, an answer without a result) rejects, and the caller reports "no result". */
  live.championInvocation = function (testId, identifier) {
    const champion = FG.config.champion;
    const endpoint = new URL(champion.endpoint);
    const path = endpoint.pathname.replace(/\/$/, "") + "/" + encodeURIComponent(testId);
    const test = typeof FG.get === "function" ? FG.get("#test-" + testId) : null;
    return { url: test && test.url || new URL(path, endpoint.origin).href, method: "POST", body: { resource_identifier: identifier } };
  };

  live.championTest = async function (testId, identifier) {
    const invocation = live.championInvocation(testId, identifier);
    const data = await live.fetchJson("champion", new URL(invocation.url).pathname, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/ld+json, application/json" },
      body: JSON.stringify(invocation.body),
      timeoutSeconds: FG.config.champion.timeoutSeconds,
    });
    return live.championResult(data);
  };

  /** Decode the same published result contract in the page and the scheduled browser health probe. */
  live.championResult = function (data) {
    const graph = FG.list(data && (data["@graph"] || data));
    const result = graph.find((entity) => entity && FG.list(entity["@type"]).some((type) => /TestResult$/.test(String(type))));
    const vocab = FG.config.vocab;
    const literal = (value) => String((value && typeof value === "object" ? value["@value"] : value) || "");
    const value = result ? literal(result["prov:value"] || result[vocab.prov + "value"]).toLowerCase() : "";
    if (!["pass", "fail", "indeterminate"].includes(value)) throw new Error("no verdict");
    return { value, log: literal(result["ftr:log"] || result[vocab.ftr + "log"]) };
  };

  /** Current state of the DMP.eosc.cz components from its status page. */
  live.dmpStatus = async function () {
    const data = await live.fetchJson("dmp-status", FG.config.dmpStatus.path);
    return FG.list(data)
      .filter((entry) => entry && entry.name)
      .map((entry) => ({ name: String(entry.name), status: String(entry.status || "") }));
  };

  /* ---------------------------------------------------------------- NKR */

  /* NKR's repositories come with the page, from the snapshot a scheduled workflow refreshes, as do FAIRsharing's
     records and DataCite's repositories (scripts/refresh_snapshots.py); none is asked for on demand. While NKR lists
     no repository there is no snapshot, and nothing stands in for one. */
  function nkrRecord(record) {
    const content = (record && record.content) || {};
    const registries = FG.list(content.relatedRegistry);
    const re3data = registries.map((entry) => live.parseRe3data(entry && entry.relatedRegistryUrl)).find(Boolean);
    return {
      id: record && record.sourceId ? String(record.sourceId) : null,
      name: String(content.repositoryName || ""),
      url: String(content.mainUrl || ""),
      kind: NKR_KIND[content.type] || null,
      keywords: FG.list(FG.state.lang === "cs" ? content.keywordCz : content.keywordEn).map(String),
      re3data: re3data || null,
      content,
    };
  }

  /** The repositories NKR lists, as of the snapshot. */
  live.nkrRecords = () => FG.list(FG.config.nkr && FG.config.nkr.records).map(nkrRecord).filter((record) => record.name);

  /** Where NKR could help but lists no repository yet, a note saying so with a link to NKR; the caller's `empty`
      says what to do instead. Nothing once NKR lists repositories, since they then join the guide's lists. */
  live.nkrNote = function (options) {
    if (live.nkrRecords().length) return null;
    const own = options && options.empty;
    return FG.h("p", { id: "nkr-status", class: "small" }, own || FG.t("repositories.nkrEmpty"), " ", FG.external(FG.config.links.nkr, FG.t("repositories.nkrOpen")));
  };

  /* ---------------------------------------------------------------- DataCite repositories */

  /* A DataCite repository ID (a DataCite client): `<member>.<repository>` in lower case. */
  const DATACITE_REPOSITORY = /^[a-z0-9]+\.[a-z0-9][a-z0-9.-]*$/;
  const enc = encodeURIComponent;

  /** Where the guide finds an entry's repository in DataCite: the ID the maintainer reviewed, or the DOI of the
      entry's re3data record, by which DataCite records the repository it describes. Null when there is neither. */
  live.dataciteRoute = function (entity) {
    if (!entity) return null;
    const typed = FG.refs(entity, "alternateIdentifier").find((item) => item && item.propertyID === "datacite");
    const id = String((typed && typed.value) || entity.datacite || "");
    if (DATACITE_REPOSITORY.test(id)) return { id };
    const doi = FG.refIds(entity, "sameAs").concat(entity.doi ? ["https://doi.org/" + entity.doi] : [])
      .map((value) => live.parsePid(value)).find((pid) => pid && live.isRe3dataDoi(pid));
    return doi ? { re3dataDoi: doi.value } : null;
  };

  /** The repository DataCite records for a route, as { id, name, url }, or null when DataCite has none. */
  live.dataciteRepository = async function (route) {
    if (!route) return null;
    const data = route.id
      ? await live.fetchJson("datacite", "clients/" + enc(route.id), { allowNotFound: true })
      : await live.fetchJson("datacite", "clients?re3data-id=" + enc(route.re3dataDoi));
    const found = route.id ? data && data.data : FG.list(data && data.data).length === 1 ? data.data[0] : null;
    if (!found || !DATACITE_REPOSITORY.test(String(found.id || ""))) return null;
    const attributes = found.attributes || {};
    return { id: found.id, name: typeof attributes.name === "string" ? attributes.name : found.id };
  };

  /** What DataCite reports about a repository's DOIs: their number, and counts by resource type, licence and metadata
      schema version, largest first. */
  live.dataciteCounts = async function (repositoryId) {
    const data = await live.fetchJson("datacite", "dois?client-id=" + enc(repositoryId) + "&page%5Bsize%5D=0&disable-facets=false");
    const meta = (data && data.meta) || {};
    const counts = (list) => FG.list(list)
      .filter((entry) => entry && typeof entry.id === "string" && typeof entry.title === "string" && Number.isInteger(entry.count))
      .map((entry) => ({ id: entry.id, title: entry.title, count: entry.count }))
      .sort((a, b) => b.count - a.count);
    return { total: Number.isInteger(meta.total) ? meta.total : 0, resourceTypes: counts(meta.resourceTypes), licenses: counts(meta.licenses),
      schemaVersions: counts(meta.schemaVersions) };
  };

  /** Records drawn at random from all a repository's DOIs, of every type it publishes, each with its title and type
      (D-185). A record that is part of another (a file Dataverse registers within its dataset) is left out, so the
      sample holds what the repository publishes. */
  live.dataciteSample = async function (repositoryId, size) {
    const data = await live.fetchJson("datacite", "dois?client-id=" + enc(repositoryId) +
      "&query=" + enc("-relatedIdentifiers.relationType:IsPartOf") + "&random=true&page%5Bsize%5D=" + size + "&fields%5Bdois%5D=doi%2Ctitles%2Ctypes");
    return FG.list(data && data.data).map((record) => {
      const pid = live.parsePid(String((record && record.id) || ""));
      const attributes = (record && record.attributes) || {};
      const title = FG.list(attributes.titles).map((entry) => entry && entry.title).find((value) => typeof value === "string" && value.trim());
      const type = String((attributes.types || {}).resourceTypeGeneral || "").slice(0, 60);
      return pid && pid.type === "doi" ? { doi: pid.value.toLowerCase(), title: title ? title.trim().slice(0, 300) : "", type } : null;
    }).filter(Boolean);
  };
})();
