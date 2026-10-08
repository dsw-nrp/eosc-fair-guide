/* Universal search of the FAIR Data Guide. Text is searched in the guide's own knowledge base as it is typed,
   ignoring diacritics and covering both languages. An identifier is routed by what it denotes: its form places
   most identifiers, the knowledge base places the guide's own identifiers and addresses it lists, and for a DOI or
   Handle one explicit lookup says what it is. Searching sends nothing anywhere: a service is called only when the
   user picks an identifier result. Text results hand over to the catalogue. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);
  const S = (FG.search = FG.search || {});
  const SHOWN = 3;
  const MIN_TYPED = 2;
  const TYPING_DELAY = 200;
  const STATUS_DELAY = 800;
  const ID_NAMES = { doi: "DOI", handle: "Handle", orcid: "ORCID iD", ror: "ROR ID", url: "URL" };
  const KINDS = ["station", "check", "principle", "resource", "repository", "term", "page", "clause"];
  /* Identifiers placed by the knowledge base alone: their routes send nothing, so they answer while typing. */
  const LOCAL = ["guide", "known"];
  const ORCID = /^(?:https?:\/\/orcid\.org\/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$/i;
  const ROR = /^(?:https?:\/\/ror\.org\/)?(0[a-hj-km-np-tv-z0-9]{6}\d{2})$/i;
  const URL = /^https:\/\/\S+$/i;
  const R3D = /^(?:https?:\/\/(?:www\.)?re3data\.org\/repository\/)?(r3d\d{9})\/?$/i;
  const NANOPUB = /^RA[A-Za-z0-9_-]{43}$|\/np\/RA/;
  /* DataCite's general resource types, by what the guide can do with them. */
  const DATA = ["Dataset", "Collection", "Image", "Audiovisual", "Sound", "Model", "PhysicalObject", "InteractiveResource"];
  const SOFTWARE = ["Software", "ComputationalNotebook", "Workflow"];
  const TEXT = ["Text", "JournalArticle", "Book", "BookChapter", "ConferencePaper", "ConferenceProceeding", "Preprint", "Report", "Dissertation", "Journal", "PeerReview", "Standard"];
  let index = null;

  const fold = FG.fold;
  const bothLanguages = FG.bothLanguages;

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
      if (id.startsWith("#resource-") && entity.name) add("resource", entity.name, bothLanguages(entity.description), { href: FG.catalogueHref("resources", entity.identifier) });
      else if (id.startsWith("#repository-") && entity.name) add("repository", entity.name, FG.list(entity.keywords).map((word) => bothLanguages(word)).join(" "), { href: FG.catalogueHref("repositories", id.replace(/^#repository-/, "")) });
      else if (id.startsWith("#term-") && entity.name && entity.termCode) add("term", entity.name, "", { href: FG.catalogueHref("terms", entity.termCode) });
      else if (id.startsWith("#page-") && entity.identifier && entity.headline) add("page", entity.headline, "", { href: FG.href("page", entity.identifier) });
      else if (id.startsWith("#clause-") && entity.text) {
        const principle = FG.principlesOf(entity)[0];
        add("clause", entity.identifier + " " + FG.text(entity.text).slice(0, 90), bothLanguages(entity.text), { href: FG.catalogueHref("clauses", entity.identifier) });
      }
    }
    return entries;
  }

  /** What the query is: an identifier for a tool, or text for the knowledge base. */
  const bare = (url) => String(url || "").toLowerCase().replace(/^https?:\/\/(www\.)?/, "").replace(/\/+$/, "");

  /** An identifier of the guide's own: a requirement (A.F1.N1) or a check question (S18). */
  function guideEntry(value) {
    if (!/^[A-Za-z][\w.-]{1,40}$/.test(value)) return null;
    const clause = FG.get("#clause-" + value) || FG.get("#clause-" + value.toUpperCase());
    if (clause) return { type: "guide", kind: "clauses", value: clause.identifier };
    const item = FG.get("#item-" + value.toUpperCase());
    if (item && item.identifier) return { type: "guide", kind: "questions", value: item.identifier };
    return null;
  }

  /** An address of something the catalogue lists: a resource or a repository. */
  function knownByUrl(value) {
    const address = bare(value);
    const resource = FG.graph.find((entity) => entity.resourceType && String(entity["@id"]).startsWith("#resource-") && bare(entity.url) === address);
    if (resource) return { type: "known", value, kind: "resources", anchor: resource.identifier, name: FG.text(resource.name) };
    const repository = FG.refs(FG.get("#repositories"), "hasPart").find((entity) => bare(entity.url) === address);
    if (repository) {
      const r3d = FG.refIds(repository, "sameAs").concat(FG.list(repository.identifier)).map((id) => (String(id).match(/r3d\d{9}/i) || [])[0]).find(Boolean);
      return { type: "known", value, kind: "repositories", anchor: String(repository["@id"]).replace(/^#(repository|resource)-/, ""), name: FG.text(repository.name), r3d };
    }
    return null;
  }

  S.classify = function (query) {
    const value = String(query || "").trim();
    if (!value) return { type: "empty" };
    const guide = guideEntry(value);
    if (guide) return guide;
    let match = value.match(R3D);
    if (match) return { type: "re3data", value: match[1].toLowerCase() };
    if (FG.live && NANOPUB.test(value) && FG.live.nanopubCode(value)) return { type: "nanopub", value: FG.live.nanopubCode(value) };
    const profiles = FG.config.links.fipDashboard + "profiles/";
    if (value.startsWith(profiles)) return { type: "fipProfile", value: value.slice(profiles.length).replace(/[/?#].*$/, ""), url: value };
    if (value.startsWith(FG.config.links.nkr + "objects/")) return { type: "nkr", value };
    const pid = FG.live && FG.live.parsePid(value);
    if (pid && pid.type === "doi" && /^10\.17616\//.test(pid.value)) return { type: "re3data", value: pid.value };
    if (pid) return { type: pid.type, value: pid.value };
    match = value.match(ORCID);
    if (match) return { type: "orcid", value: match[1].toUpperCase() };
    match = value.match(ROR);
    if (match) return { type: "ror", value: match[1].toLowerCase() };
    if (URL.test(value)) return knownByUrl(value) || { type: "url", value };
    return { type: "text", value };
  };

  const idName = (type) => ID_NAMES[type] || FG.t("search.idName." + type);

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

  const datasetCheck = (pid, primary) => resultLink({ onclick: () => FG.selfcheck.startWithPid(pid) }, FG.t("search.checkDataset", { pid }), "check", primary);
  const cite = (primary) => resultLink({ href: FG.href("page", "citation") }, FG.t("search.cite"), "cite", primary);
  const nma = (pid) => resultLink({ url: FG.config.links.nmaSearch + "?q=" + encodeURIComponent('"' + pid + '"') }, FG.t("search.nma"), "search");
  const verify = (id, primary) => resultLink({ href: FG.href("page", "identifiers") }, FG.t("search.verify", { id }), "identifier", primary);
  /* A re3data DOI that does not lead to a record still opens the check, to be filled in by hand. */
  const maturity = (value, primary) =>
    resultLink({ onclick: async () => (await FG.selfcheck.startWithRe3data(value)) || FG.navigate(FG.href("check", "maturity")) }, FG.t("search.maturityRe3data"), "check", primary);
  const list = (actions) => h("ul", { class: "results-list" }, actions.filter(Boolean).map((action) => h("li", null, action)));
  const basis = (key, params) => h("p", { class: "small muted search-basis" }, FG.t("search.basis." + key, params || {}));

  /** What can be done with an identifier placed by its form or by the knowledge base, without any request. */
  function routes(found, box) {
    const findOut = resultLink({ onclick: () => lookUp(found, box) }, FG.t("search.findOut"), "identifier", true);
    switch (found.type) {
      case "doi":
        return [basis("form", { type: idName(found.type) }), list([findOut, datasetCheck(found.value, false), cite(false), nma(found.value), verify(found.value, false)])];
      case "handle":
        return [basis("form", { type: idName(found.type) }), list([findOut, datasetCheck(found.value, false), nma(found.value)])];
      case "re3data":
        return [basis("form", { type: idName(found.type) }), list([maturity(found.value, true), /^r3d/.test(found.value) ? resultLink({ url: FG.config.links.re3dataRecord + found.value }, FG.t("search.open.re3data"), "external") : null])];
      case "nanopub":
        return [basis("form", { type: idName(found.type) }), list([resultLink({ onclick: () => FG.selfcheck.startWithNanopub(found.value) }, FG.t("search.fipNanopub"), "check", true)])];
      case "fipProfile":
        return [basis("form", { type: idName(found.type) }), list([resultLink({ onclick: () => FG.selfcheck.startWithFip(found.value) || FG.navigate(FG.href("check", "fip")) }, FG.t("search.fipProfile"), "check", true), resultLink({ url: found.url }, FG.t("search.open.fipProfile"), "external")])];
      case "nkr":
        return [basis("form", { type: idName(found.type) }), list([resultLink({ href: FG.href("check", "maturity") }, FG.t("search.maturity"), "check", true), resultLink({ url: found.value }, FG.t("search.open.nkr"), "external")])];
      case "orcid":
        return [basis("form", { type: idName(found.type) }), list([verify(found.value, true)])];
      case "ror":
        return [basis("form", { type: idName(found.type) }), list([resultLink({ href: FG.href("check", "institution") }, FG.t("search.institution"), "check", true), verify(found.value, false)])];
      case "guide":
        return [basis("guide"), list([resultLink({ href: FG.catalogueHref(found.kind, found.value) }, FG.t("search.openEntry", { id: found.value }), "sources", true)])];
      case "known":
        return [basis("catalogue"), list([resultLink({ href: FG.catalogueHref(found.kind, found.anchor) }, FG.t("search.inCatalogue", { name: found.name }), "sources", true), found.r3d ? maturity(found.r3d, false) : null])];
      default:
        return [basis("form", { type: idName(found.type) }), list([resultLink({ href: FG.href("page", "live-check") }, FG.t("search.checkUrl"), "check", true)])];
    }
  }

  /** One explicit lookup that says what a DOI or Handle is: its registration agency and, for DataCite, its type. */
  async function whatIs(found, asked) {
    try {
      if (found.type === "handle") {
        asked.push("Handle.net");
        const resolved = await FG.live.resolvePid({ type: "handle", value: found.value });
        return resolved.found ? { kind: "handle", title: resolved.title, by: "Handle.net" } : { kind: "unknown" };
      }
      asked.push("doi.org");
      const agency = await FG.live.doiAgency(found.value);
      if (!agency) return { kind: "unknown" };
      if (agency !== "DataCite") return { kind: "publication", by: agency };
      asked.push("DataCite");
      const attributes = await FG.live.datacite(found.value);
      if (!attributes) return { kind: "unknown", by: agency };
      const general = String((attributes.types || {}).resourceTypeGeneral || "");
      const title = FG.list(attributes.titles).map((entry) => entry && entry.title).find(Boolean) || "";
      const publisher = attributes.publisher && typeof attributes.publisher === "object" ? attributes.publisher.name : attributes.publisher;
      const details = { title: title.replace(/^FAIRsharing record for:\s*/i, ""), publisher, year: attributes.publicationYear, by: "DataCite" };
      if (/^10\.25504\//.test(found.value)) {
        const r3d = FG.list(attributes.relatedIdentifiers).map((entry) => (String((entry && entry.relatedIdentifier) || "").match(/r3d\d{9}/i) || [])[0]).find(Boolean);
        return Object.assign(details, { kind: r3d ? "repository" : "fairsharing", r3d: r3d && r3d.toLowerCase() });
      }
      const kind = DATA.includes(general) ? "dataset" : SOFTWARE.includes(general) ? "software" : TEXT.includes(general) ? "publication" : "other";
      return Object.assign(details, { kind, general });
    } catch (error) {
      return { kind: "failed" };
    }
  }

  async function lookUp(found, box) {
    box.replaceChildren(h("p", { class: "small", role: "status" }, FG.t("search.findingOut")));
    const asked = [];
    const result = await whatIs(found, asked);
    const sent = box.nextElementSibling;
    if (sent && asked.length) sent.textContent = FG.t("search.asked", { sources: asked.join(", ") });
    const what = [result.title, result.publisher, result.year].filter(Boolean).join(" · ");
    const said = ["unknown", "failed"].includes(result.kind)
      ? h("p", { class: "search-basis", role: "status" }, FG.t("search.lookup." + result.kind))
      : h("p", { class: "search-basis", role: "status" }, h("strong", null, FG.t("search.is", { kind: FG.t("search.what." + result.kind) })), what ? " " + what : null, result.by ? h("span", { class: "muted" }, " (" + FG.t("search.by", { source: result.by }) + ")") : null);
    const note = (key) => h("p", { class: "small" }, FG.t("search.note." + key));
    const actions = {
      dataset: [list([datasetCheck(found.value, true), cite(false), nma(found.value)])],
      software: [note("software"), list([datasetCheck(found.value, true), cite(false)])],
      publication: [note("publication"), list([cite(true), datasetCheck(found.value, false)])],
      repository: [list([maturity(result.r3d, true)])],
      fairsharing: [list([resultLink({ url: FG.live.pidUrl({ type: "doi", value: found.value }) }, FG.t("search.open.fairsharing"), "external", true), resultLink({ href: FG.href("check", "maturity") }, FG.t("search.maturity"), "check")])],
      handle: [list([datasetCheck(found.value, true), nma(found.value)])],
      other: [list([datasetCheck(found.value, true), cite(false), verify(found.value, false)])],
      unknown: [list([verify(found.value, true)])],
      failed: [list([resultLink({ onclick: () => lookUp(found, box) }, FG.t("search.findOut"), "identifier", true), datasetCheck(found.value, false)])],
    }[result.kind];
    box.replaceChildren(said, ...actions.flat(Infinity).filter(Boolean));
    const first = box.querySelector(".result");
    if (first) first.focus();
  }

  function identifierResults(found) {
    const box = h("div", { class: "identifier-results" });
    box.replaceChildren(...routes(found, box).flat(Infinity).filter(Boolean));
    return [box, h("p", { class: "small muted" }, FG.t(LOCAL.includes(found.type) ? "search.localOnly" : "search.notSent"))];
  }

  /** The catalogue as the full results page: the same query, in the kind with the first results. */
  function handOff(query, groups) {
    const kinds = { resource: "resources", repository: "repositories", term: "terms", clause: "clauses" };
    const first = groups.find((group) => kinds[group.kind]);
    return h("p", { class: "catalogue-handoff" }, h("a", { href: FG.catalogueSearchHref(query, first ? kinds[first.kind] : "resources") }, FG.t("search.inCatalogueAll", { q: query })));
  }

  function textResults(query) {
    const groups = S.find(query);
    if (!groups.length) return [h("p", null, FG.t("search.none")), handOff(query, groups)];
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
      handOff(query, groups),
      h("p", { class: "small muted" }, FG.t("search.localOnly")),
    ];
  }

  /** A recognised identifier while it is being typed: its routes lead to outside services, so they wait for Enter. */
  function identifierHint(found) {
    return [h("p", { class: "search-hint" }, FG.icon ? FG.icon("identifier") : null, h("span", null, FG.t("search.identifierHint", { type: idName(found.type) })))];
  }

  /** The search form with its results: the guide's own content is searched while typing; the routes for an
      identifier that lead to outside services appear when the search is confirmed with Enter or the button. */
  S.form = function () {
    const input = h("input", { id: "search-input", type: "search", autocomplete: "off", spellcheck: "false", placeholder: FG.t("search.placeholder") });
    const results = h("div", { id: "search-results", class: "search-results" });
    const status = h("p", { class: "visually-hidden", role: "status" });
    let typingTimer = null;
    let statusTimer = null;
    const show = (confirmed) => {
      const value = input.value;
      const found = S.classify(value);
      let content = [];
      let message = "";
      if (found.type === "text" && (confirmed || found.value.length >= MIN_TYPED)) {
        content = textResults(found.value);
        const count = S.find(found.value).reduce((sum, group) => sum + group.items.length, 0);
        message = count ? FG.t("search.found", { n: count }) : FG.t("search.none");
      } else if (found.type !== "text" && found.type !== "empty") {
        const ready = confirmed || LOCAL.includes(found.type);
        content = ready ? identifierResults(found) : identifierHint(found);
        message = ready ? FG.t("search.done") : FG.t("search.identifierHint", { type: idName(found.type) });
      }
      results.replaceChildren(...content.flat(Infinity).filter(Boolean));
      results.dataset.query = value;
      results.dataset.confirmed = String(confirmed);
      clearTimeout(statusTimer);
      if (confirmed) status.textContent = message;
      else statusTimer = setTimeout(() => (status.textContent = message), STATUS_DELAY);
    };
    const typed = () => {
      clearTimeout(typingTimer);
      typingTimer = setTimeout(() => show(false), TYPING_DELAY);
    };
    const run = (event) => {
      event.preventDefault();
      clearTimeout(typingTimer);
      show(true);
    };
    input.addEventListener("input", typed);
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
