/* Universal search of the FAIR data guide. An identifier is routed to the tool that handles it; any other text is
   searched in the guide's own knowledge base, ignoring diacritics and covering both languages. Searching sends
   nothing anywhere: a service is called only when the user picks an identifier result. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);
  const S = (FG.search = FG.search || {});
  const SHOWN = 3;
  const KINDS = ["station", "check", "principle", "resource", "repository", "term", "page", "clause"];
  const ORCID = /^(?:https?:\/\/orcid\.org\/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$/i;
  const ROR = /^(?:https?:\/\/ror\.org\/)?(0[a-hj-km-np-tv-z0-9]{6}\d{2})$/i;
  const URL = /^https:\/\/\S+$/i;
  let index = null;

  const fold = (value) =>
    String(value || "")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase();
  const bothLanguages = (value) => FG.textOf(value, "cs").text + " " + FG.textOf(value, "en").text;

  /** Every searchable entity with its title, the text it is found by, and where it leads. */
  function buildIndex() {
    const entries = [];
    const add = (kind, title, extra, target) => entries.push({ kind, title, target, key: fold(bothLanguages(title)), extra: fold(extra) });
    for (const station of FG.stations()) {
      const advice = FG.refs(station, "itemListElement").map((item) => bothLanguages(item.text)).join(" ");
      add("station", station.name, bothLanguages(station.headline) + " " + advice, { href: FG.href("path", station.identifier) });
    }
    for (const check of FG.ofType("Quiz")) add("check", check.name, bothLanguages(check.description), { href: FG.href("check", check.identifier) });
    for (const principle of FG.principles()) {
      add("principle", [principle.termCode, FG.text(principle.name)].join(" "), bothLanguages(principle.name) + " " + bothLanguages(principle.description), {
        href: FG.href("explorer", principle.termCode),
      });
    }
    for (const entity of FG.graph) {
      const id = String(entity["@id"]);
      if (id.startsWith("#resource-") && entity.name) add("resource", entity.name, bothLanguages(entity.description), { href: FG.href("resources", entity.identifier) });
      else if (id.startsWith("#repository-") && entity.name) add("repository", entity.name, FG.list(entity.keywords).map((word) => bothLanguages(word)).join(" "), { href: FG.href("repositories") });
      else if (id.startsWith("#term-") && entity.name && entity.url) add("term", entity.name, "", { url: entity.url });
      else if (id.startsWith("#page-") && entity.identifier && entity.headline) add("page", entity.headline, "", { href: FG.href("page", entity.identifier) });
      else if (id.startsWith("#clause-") && entity.text) {
        const principle = FG.refs(entity, "about")[0];
        add("clause", entity.identifier + " " + FG.text(entity.text).slice(0, 90), bothLanguages(entity.text), {
          href: principle ? FG.href("explorer", principle.termCode) : FG.href("explorer"),
        });
      }
    }
    return entries;
  }

  /** What the query is: an identifier for a tool, or text for the knowledge base. */
  S.classify = function (query) {
    const value = String(query || "").trim();
    if (!value) return { type: "empty" };
    const pid = FG.live && FG.live.parsePid(value);
    if (pid) return { type: pid.type, value: pid.value };
    let match = value.match(ORCID);
    if (match) return { type: "orcid", value: match[1].toUpperCase() };
    match = value.match(ROR);
    if (match) return { type: "ror", value: match[1].toLowerCase() };
    if (URL.test(value)) return { type: "url", value };
    return { type: "text", value };
  };

  /** Matches in the knowledge base, grouped by kind; every word of the query must occur. */
  S.find = function (query) {
    index = index || buildIndex();
    const words = fold(query).split(/\s+/).filter(Boolean);
    if (!words.length) return [];
    const phrase = words.join(" ");
    const scored = [];
    for (const entry of index) {
      const haystack = entry.key + " " + entry.extra;
      if (!words.every((word) => haystack.includes(word))) continue;
      let score = 1;
      if (words.every((word) => entry.key.includes(word))) score = 2;
      if (entry.key.startsWith(phrase) || entry.key.includes(" " + phrase)) score = 3;
      scored.push({ entry, score });
    }
    scored.sort((a, b) => b.score - a.score || KINDS.indexOf(a.entry.kind) - KINDS.indexOf(b.entry.kind));
    return KINDS.map((kind) => ({ kind, items: scored.filter((item) => item.entry.kind === kind).map((item) => item.entry) })).filter((group) => group.items.length);
  };

  function resultLink(target, label, icon, primary) {
    const children = [FG.icon ? FG.icon(icon) : null, h("span", null, label)];
    if (target.url) return FG.external(target.url, children, { class: "result" + (primary ? " result-primary" : "") });
    if (target.onclick) return h("button", { type: "button", class: "result" + (primary ? " result-primary" : ""), onclick: target.onclick }, children);
    return h("a", { class: "result" + (primary ? " result-primary" : ""), href: target.href }, children);
  }

  function identifierResults(found) {
    const actions = [];
    if (found.type === "doi" || found.type === "handle") {
      actions.push(resultLink({ onclick: () => FG.selfcheck.startWithPid(found.value) }, FG.t("search.checkDataset", { pid: found.value }), "check", true));
      if (found.type === "doi") actions.push(resultLink({ href: FG.href("page", "citation") }, FG.t("search.cite"), "cite"));
      actions.push(resultLink({ url: FG.config.links.nmaSearch + "?q=" + encodeURIComponent('"' + found.value + '"') }, FG.t("search.nma"), "search"));
    } else if (found.type === "orcid" || found.type === "ror") {
      actions.push(resultLink({ href: FG.href("page", "identifiers") }, FG.t("search.verify", { id: found.value }), "identifier", true));
    } else if (found.type === "url") {
      actions.push(resultLink({ href: FG.href("page", "live-check") }, FG.t("search.checkUrl"), "check", true));
    }
    return [h("ul", { class: "results-list" }, actions.map((action) => h("li", null, action))), h("p", { class: "small muted" }, FG.t("search.notSent"))];
  }

  function textResults(query) {
    const groups = S.find(query);
    if (!groups.length) return [h("p", null, FG.t("search.none"))];
    const icons = { station: "now", check: "check", principle: "why", resource: "sources", repository: "sources", term: "info", page: "info", clause: "sources" };
    return [
      groups.map((group) => {
        const item = (entry, position) => h("li", null, resultLink(entry.target, FG.text(entry.title) || String(entry.title), icons[group.kind], position === 0 && group === groups[0]));
        const list = h("ul", { class: "results-list" }, group.items.slice(0, SHOWN).map(item));
        const more =
          group.items.length > SHOWN
            ? h(
                "button",
                {
                  type: "button",
                  class: "button-link small",
                  onclick: (event) => {
                    list.replaceChildren(...group.items.map(item));
                    event.currentTarget.remove();
                    list.children[SHOWN].firstChild.focus();
                  },
                },
                FG.t("search.more", { n: group.items.length })
              )
            : null;
        return [h("h3", null, FG.t("search.kind." + group.kind)), list, more];
      }),
      h("p", { class: "small muted" }, FG.t("search.localOnly")),
    ];
  }

  /** The search form with its results; results appear when the search is confirmed. */
  S.form = function () {
    const input = h("input", { id: "search-input", type: "search", autocomplete: "off", spellcheck: "false", placeholder: FG.t("search.placeholder") });
    const results = h("div", { id: "search-results", class: "search-results" });
    const status = h("p", { class: "visually-hidden", role: "status" });
    const run = (event) => {
      event.preventDefault();
      const found = S.classify(input.value);
      if (found.type === "empty") {
        results.replaceChildren();
        status.textContent = "";
        return;
      }
      const content = found.type === "text" ? textResults(found.value) : identifierResults(found);
      results.replaceChildren(...content.flat(Infinity).filter(Boolean));
      status.textContent = FG.t("search.done");
    };
    return h(
      "form",
      { class: "search", role: "search", onsubmit: run },
      h("label", { for: "search-input" }, FG.t("search.label")),
      h("div", { class: "search-row" }, input, h("button", { type: "submit", class: "button button-primary" }, FG.icon ? FG.icon("search") : null, FG.t("search.button"))),
      status,
      results
    );
  };
})();
