/* Live connectors of the FAIR data guide. Every call starts from a user action, goes only to a host on the
   allowlist in the page configuration (content/live.toml), times out, and treats the response as data. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const live = (FG.live = FG.live || {});
  const NKR_KIND = { disciplinary: "#rkind-domain", institutional: "#rkind-institutional", generic: "#rkind-general" };

  function connector(id) {
    const found = FG.config.connectors.find((item) => item.id === id);
    if (!found) throw new Error("unknown connector " + id);
    return found;
  }

  /** Fetch JSON from an allowlisted connector; rejects on timeout, HTTP errors and non-JSON answers. */
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
      if (!response.ok) throw new Error(target.name + ": HTTP " + response.status);
      return await response.json();
    } finally {
      clearTimeout(timer);
    }
  };

  /* ---------------------------------------------------------------- NKR */

  live.nkr = { state: "idle", records: [] };

  function nkrRecord(content) {
    const registries = FG.list(content.relatedRegistry);
    const re3data = registries
      .map((entry) => String(entry.relatedRegistryUrl || ""))
      .map((url) => (url.match(/r3d\d+/) || [])[0])
      .find(Boolean);
    return {
      name: String(content.repositoryName || ""),
      url: String(content.mainUrl || ""),
      kind: NKR_KIND[content.type] || null,
      keywords: FG.list(FG.state.lang === "cs" ? content.keywordCz : content.keywordEn).map(String),
      re3data: re3data || null,
    };
  }

  live.loadNkr = async function () {
    live.nkr.state = "loading";
    FG.render();
    try {
      const data = await live.fetchJson("nkr", "search?query=type:Repository&pageSize=200");
      live.nkr.records = FG.list(data.results).map((result) => nkrRecord(result.content || {})).filter((record) => record.name);
      live.nkr.state = "done";
    } catch (error) {
      live.nkr.state = "failed";
    }
    FG.render();
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
      FG.h("button", { type: "button", onclick: live.loadNkr, disabled: live.nkr.state === "loading" }, FG.t("repositories.nkrLoad")),
      status ? FG.h("p", { role: "status", class: "small" }, status) : null
    );
  };
})();
