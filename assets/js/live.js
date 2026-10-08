/* Live connectors of the FAIR data guide. Every call starts from a user action, goes only to a host on the
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
    const url = found
      ? FG.list(data.values)
          .filter((value) => value && value.type === "URL")
          .map((value) => value.data && value.data.value)
          .find(Boolean)
      : null;
    return { found, url: url ? String(url) : null };
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

  live.nkrButton = function () {
    const status = {
      loading: FG.t("repositories.nkrLoading"),
      done: live.nkr.records.length ? null : FG.t("repositories.nkrEmpty"),
      failed: FG.t("repositories.nkrFailed", { url: FG.config.links.nkr }),
    }[live.nkr.state];
    return FG.h(
      "div",
      null,
      FG.h("button", { type: "button", id: "nkr-load", onclick: live.loadNkr, disabled: live.nkr.state === "loading" }, FG.t("repositories.nkrLoad")),
      status ? FG.h("p", { role: "status", class: "small" }, status) : null
    );
  };
})();
