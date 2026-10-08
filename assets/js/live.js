/* Live connectors of the FAIR Data Guide. Every call starts from a user action, goes only to a host on the
   allowlist in the page configuration (content/live.toml), times out, and treats the response as data. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const live = (FG.live = FG.live || {});
  const NKR_KIND = { disciplinary: "#rkind-domain", institutional: "#rkind-institutional", generic: "#rkind-general" };
  const NANOPUB_CODE = /(?:^|[^A-Za-z0-9_-])(RA[A-Za-z0-9_-]{43})(?![A-Za-z0-9_-])/;

  function connector(id) {
    const found = FG.config.connectors.find((item) => item.id === id);
    if (!found) throw new Error("unknown connector " + id);
    return found;
  }

  live.origin = (id) => connector(id).origin;

  /** Whether the service's API admits the guide's origin; a service that does not is used through its snapshot. */
  live.available = (id) => connector(id).browserAccess !== false;

  /** Fetch JSON from an allowlisted connector; rejects on timeout, HTTP errors and non-JSON answers. With
      `allowNotFound`, a 404 answer gives null instead of an error. */
  live.fetchJson = async function (connectorId, path, options) {
    const target = connector(connectorId);
    const url = new URL(path, target.origin + "/");
    if (url.origin !== target.origin) throw new Error("refusing a URL outside " + target.origin);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), ((options && options.timeoutSeconds) || 20) * 1000);
    try {
      const response = await fetch(url.href, {
        method: (options && options.method) || "GET",
        headers: Object.assign({ Accept: "application/json" }, (options && options.headers) || {}),
        body: options && options.body,
        signal: controller.signal,
        credentials: "omit",
        referrerPolicy: "no-referrer",
      });
      if (response.status === 404 && options && options.allowNotFound) return null;
      if (!response.ok) throw new Error(target.name + ": HTTP " + response.status);
      return await response.json();
    } finally {
      clearTimeout(timer);
    }
  };

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

  /** Ask the DOI or Handle resolver whether the identifier exists and where it leads. */
  live.resolvePid = async function (pid) {
    const path = "api/handles/" + pid.value.split("/").map(encodeURIComponent).join("/");
    const data = await live.fetchJson(pid.type === "doi" ? "doi" : "handle", path, { allowNotFound: true });
    const found = Boolean(data && data.responseCode === 1);
    const valueOf = (type) =>
      found
        ? FG.list(data.values)
            .filter((value) => value && value.type === type)
            .map((value) => value.data && value.data.value)
            .find((value) => typeof value === "string" && value)
        : null;
    return { found, url: valueOf("URL") || null, title: valueOf("TITLE") || null };
  };

  /** The registration agency of a DOI (DataCite, Crossref, ...), or null when doi.org does not know the DOI. */
  live.doiAgency = async function (doi) {
    const data = await live.fetchJson("doi", "ra/" + String(doi).split("/").map(encodeURIComponent).join("/"));
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
  live.datacite = async function (doi) {
    const data = await live.fetchJson("datacite", "dois/" + encodeURIComponent(doi), { allowNotFound: true });
    return data && data.data ? data.data.attributes || {} : null;
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
  live.championTest = async function (testId, identifier) {
    const champion = FG.config.champion;
    const endpoint = new URL(champion.endpoint);
    const data = await live.fetchJson("champion", endpoint.pathname.replace(/\/$/, "") + "/" + encodeURIComponent(testId), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/ld+json, application/json" },
      body: JSON.stringify({ resource_identifier: identifier }),
      timeoutSeconds: champion.timeoutSeconds,
    });
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

  /* ---------------------------------------------------------------- FAIRsharing */

  /* FAIRsharing's API needs a login, but every FAIRsharing record has a DataCite DOI whose metadata lists the
     described resource's addresses, including its re3data record, so a DataCite search finds the records. */
  live.fairsharing = { state: "idle", records: [], asked: 0 };

  /** An address without its scheme, "www." and trailing slashes, for matching. */
  live.bareUrl = (url) =>
    String(url || "")
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\//, "")
      .replace(/^www\./, "")
      .replace(/\/+$/, "");

  function fairsharingRecord(entry) {
    const attributes = (entry && entry.attributes) || {};
    const first = (list, key) => FG.list(list).map((item) => item && item[key]).find((value) => typeof value === "string" && value) || "";
    const related = FG.list(attributes.relatedIdentifiers)
      .map((item) => String((item && item.relatedIdentifier) || ""))
      .filter(Boolean);
    return {
      doi: String((entry && entry.id) || attributes.doi || ""),
      name: first(attributes.titles, "title").replace(/^FAIRsharing record for:\s*/i, ""),
      re3data: related.map((value) => (value.match(/r3d\d{9}/i) || [""])[0].toLowerCase()).find(Boolean) || null,
      addresses: related.map(live.bareUrl),
    };
  }

  /** FAIRsharing records of the given repositories ({ identifiers, url }), found by their re3data records and
      addresses in DataCite searches of at most 30 terms each. */
  live.findFairsharing = async function (repositories) {
    const terms = new Set();
    for (const repository of repositories) {
      for (const id of FG.list(repository.identifiers)) if (/^r3d\d{9}$/i.test(id)) terms.add(FG.config.links.re3dataRecord + id.toLowerCase());
      const url = String(repository.url || "");
      if (/^https?:\/\//.test(url) && !url.includes('"')) {
        terms.add(url);
        terms.add(url.endsWith("/") ? url.replace(/\/+$/, "") : url + "/");
      }
    }
    const all = [...terms];
    const batches = [];
    for (let start = 0; start < all.length; start += 30) batches.push(all.slice(start, start + 30));
    const prefix = FG.config.fairsharing.prefix;
    const answers = await Promise.all(
      batches.map((batch) =>
        live.fetchJson(
          "datacite",
          "dois?query=" + encodeURIComponent("relatedIdentifiers.relatedIdentifier:(" + batch.map((term) => '"' + term + '"').join(" OR ") + ")") + "&prefix=" + encodeURIComponent(prefix) + "&page[size]=100"
        )
      )
    );
    const records = new Map();
    for (const answer of answers) for (const entry of FG.list(answer && answer.data)) {
      const found = fairsharingRecord(entry);
      if (found.doi && found.name) records.set(found.doi.toLowerCase(), found);
    }
    return [...records.values()];
  };

  /** The FAIRsharing record of a repository among those found, by its re3data record or its address. */
  live.fairsharingOf = function (repository, records) {
    const ids = FG.list(repository.identifiers).map((id) => String(id).toLowerCase());
    const address = live.bareUrl(repository.url);
    return (records || live.fairsharing.records).find((record) => (record.re3data && ids.includes(record.re3data)) || (address && record.addresses.includes(address))) || null;
  };

  live.loadFairsharing = async function (repositories) {
    live.fairsharing.state = "loading";
    live.fairsharing.asked = repositories.length;
    FG.rerender("fairsharing-load");
    try {
      live.fairsharing.records = await live.findFairsharing(repositories);
      live.fairsharing.state = "done";
    } catch (error) {
      live.fairsharing.state = "failed";
    }
    FG.rerender("fairsharing-load");
  };

  /** The FAIRsharing button and its status line, placed apart by the caller. */
  live.fairsharingControls = function (repositories) {
    const found = repositories.filter((repository) => live.fairsharingOf(repository)).length;
    const status = {
      loading: FG.t("repositories.fairsharingLoading"),
      done: FG.t("repositories.fairsharingFound", { n: found, total: repositories.length }),
      failed: FG.t("repositories.fairsharingFailed", { url: FG.config.links.fairsharing }),
    }[live.fairsharing.state];
    return {
      button: FG.h("button", { type: "button", id: "fairsharing-load", onclick: () => live.loadFairsharing(repositories), disabled: live.fairsharing.state === "loading" }, FG.t("repositories.fairsharingLoad")),
      status: status ? FG.h("p", { id: "fairsharing-status", role: "status", class: "small" }, status) : null,
    };
  };

  /* ---------------------------------------------------------------- NKR */

  live.nkr = { state: "idle", records: [] };

  function nkrRecord(result) {
    const content = (result && result.content) || {};
    const registries = FG.list(content.relatedRegistry);
    const re3data = registries
      .map((entry) => String((entry && entry.relatedRegistryUrl) || ""))
      .map((url) => (url.match(/r3d\d+/) || [])[0])
      .find(Boolean);
    return {
      id: result && result.id ? String(result.id) : null,
      name: String(content.repositoryName || ""),
      url: String(content.mainUrl || ""),
      kind: NKR_KIND[content.type] || null,
      keywords: FG.list(FG.state.lang === "cs" ? content.keywordCz : content.keywordEn).map(String),
      re3data: re3data || null,
      content,
    };
  }

  live.loadNkr = async function () {
    live.nkr.state = "loading";
    FG.rerender("nkr-load");
    try {
      const data = await live.fetchJson("nkr", "search?query=type:Repository&pageSize=200");
      live.nkr.records = FG.list(data.results).map(nkrRecord).filter((record) => record.name);
      live.nkr.state = "done";
    } catch (error) {
      live.nkr.state = "failed";
    }
    FG.rerender("nkr-load");
  };

  /** The NKR button and its status line, placed apart by the caller. */
  live.nkrControls = function () {
    const status = {
      loading: FG.t("repositories.nkrLoading"),
      done: live.nkr.records.length ? null : FG.t("repositories.nkrEmpty"),
      failed: FG.t("repositories.nkrFailed", { url: FG.config.links.nkr }),
    }[live.nkr.state];
    return {
      button: FG.h("button", { type: "button", id: "nkr-load", onclick: live.loadNkr, disabled: live.nkr.state === "loading" }, FG.t("repositories.nkrLoad")),
      status: status ? FG.h("p", { id: "nkr-status", role: "status", class: "small" }, status) : null,
    };
  };

  live.nkrButton = function () {
    const controls = live.nkrControls();
    return FG.h("div", null, controls.button, controls.status);
  };
})();
