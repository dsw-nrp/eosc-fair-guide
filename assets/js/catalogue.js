/* Catalogue of the FAIR Data Guide: one view with a tab for each kind of entity in the knowledge base. The resource
   and repository finders are two of its tabs (views.js); the others list cited sources, glossary terms, FIP
   profiles, FAIR tests and content changes. Each item links to its record in the guide's API once it is published. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);
  const TABS = ["resources", "repositories", "sources", "terms", "fips", "tests", "actions"];
  const queries = {};
  FG.tabs = FG.tabs || {};

  /** The link to an entity's JSON record in the guide's API; nothing until the API is published. */
  FG.apiLink = function (collection, id) {
    const api = FG.config.api;
    if (!api || !api.base || !id) return null;
    return h("a", { class: "json-link", href: api.base + collection + "/" + encodeURIComponent(id) + ".json", type: "application/json" }, "JSON");
  };

  /** The address of a catalogue tab, or of one item in it. */
  FG.catalogueHref = (tab, item) => FG.href("catalogue", tab) + (item ? "/" + encodeURIComponent(item) : "");

  const matches = (tab, ...texts) => !queries[tab] || FG.fold(texts.join(" ")).includes(FG.fold(queries[tab]));

  /** A search field that narrows the tab's list as it is typed. */
  function searchBox(tab, build) {
    return h(
      "div",
      { class: "filters" },
      h(
        "label",
        null,
        FG.t("catalogue.search"),
        h("input", {
          type: "search",
          id: "catalogue-search",
          value: queries[tab] || "",
          oninput: (event) => {
            queries[tab] = event.target.value;
            FG.renderList("catalogue-list", build);
          },
        })
      )
    );
  }

  /** A list with its count, rebuilt in place by the search field. */
  function listed(items, render, wrapper) {
    return h("div", null, h("p", { role: "status" }, FG.t("finder.count", { n: items.length })), wrapper(items.map(render)));
  }

  const cards = (children) => h("ul", { class: "cards" }, children);

  /** A station or a check, as a short link. */
  function holderLink(holder) {
    return holder.position
      ? h("a", { href: FG.href("path", holder.identifier) }, holder.position + " · ", FG.span(holder.name))
      : h("a", { href: FG.href("check", holder.identifier) }, FG.span(holder.name));
  }

  const joined = (links) => links.flatMap((link, index) => (index ? [", ", link] : [link]));

  /* ---------------------------------------------------------------- cited sources */

  /** Where each source is cited: the stations and checks whose items cite one of its clauses. */
  function citedBy() {
    const map = new Map();
    const holders = FG.stations()
      .map((station) => [station, FG.refs(station, "itemListElement")])
      .concat(FG.ofType("Quiz").map((check) => [check, FG.refs(check, "hasPart")]));
    for (const [holder, items] of holders) {
      for (const item of items) {
        for (const clause of FG.refs(item, "citation")) {
          const source = FG.id(clause.isPartOf);
          if (!source) continue;
          const list = map.get(source) || [];
          if (!list.includes(holder)) list.push(holder);
          map.set(source, list);
        }
      }
    }
    return map;
  }

  function sourceKind(source) {
    const extra = FG.list(source.additionalType).map(String);
    if (extra.some((type) => /Dataset$/.test(type))) return "Dataset";
    if (extra.some((type) => /SoftwareSourceCode$/.test(type))) return "SoftwareSourceCode";
    return String(FG.list(source["@type"])[0]);
  }

  function sourceCard(source, cited) {
    const publisher = FG.get(source.publisher);
    const url = source.url || (String(source["@id"]).startsWith("https://") ? source["@id"] : null);
    const name = h("span", { lang: source.inLanguage || null }, FG.text(source.name));
    const date = source.datePublished
      ? FG.t("catalogue.published", { date: String(source.datePublished).length === 10 ? FG.formatDate(source.datePublished) : String(source.datePublished) })
      : source.sdDatePublished
        ? FG.t("catalogue.accessed", { date: FG.formatDate(source.sdDatePublished) })
        : null;
    return h(
      "li",
      { class: "card", id: "item-" + source.identifier },
      h("h3", null, url ? FG.external(url, name) : name),
      source.creditText ? h("p", { class: "small" }, source.creditText) : null,
      h(
        "div",
        { class: "badges" },
        h("span", { class: "badge" }, FG.t("catalogue.sourceType." + sourceKind(source))),
        publisher ? h("span", { class: "badge" }, FG.text(publisher.alternateName || publisher.name)) : null,
        source.version ? h("span", { class: "badge" }, FG.t("catalogue.version", { version: source.version })) : null,
        date ? h("span", { class: "badge" }, date) : null,
        FG.apiLink("sources", source.identifier)
      ),
      cited.length ? h("p", { class: "small cited-by" }, FG.t("catalogue.citedBy") + ": ", joined(cited.map(holderLink))) : null
    );
  }

  FG.tabs.sources = function () {
    const sources = FG.refs(FG.get("#sources"), "hasPart").sort((a, b) => FG.text(a.name).localeCompare(FG.text(b.name)));
    const cited = citedBy();
    const build = () =>
      listed(
        sources.filter((source) => matches("sources", FG.text(source.name), source.creditText, FG.text((FG.get(source.publisher) || {}).name))),
        (source) => sourceCard(source, cited.get(source["@id"]) || []),
        cards
      );
    return [h("h2", null, FG.t("catalogue.tab.sources")), h("p", null, FG.t("catalogue.intro.sources")), searchBox("sources", build), h("div", { id: "catalogue-list" }, build())];
  };

  /* ---------------------------------------------------------------- glossary terms */

  FG.tabs.terms = function () {
    const glossary = FG.get("#glossary");
    /* Alphabetical in Czech, ignoring a leading bracket such as "[čistě] Open Access časopis". */
    const sortKey = (term) => FG.textOf(term.name, "cs").text.replace(/^[[(]+/, "");
    const terms = FG.refs(glossary, "hasDefinedTerm").sort((a, b) => sortKey(a).localeCompare(sortKey(b), "cs"));
    const stations = new Map();
    for (const station of FG.stations()) for (const id of FG.refIds(station, "mentions")) stations.set(id, (stations.get(id) || []).concat(station));
    const row = (term) =>
      h(
        "tr",
        { id: "item-" + term.termCode },
        h("th", { scope: "row", lang: "cs" }, FG.external(term.url, FG.textOf(term.name, "cs").text)),
        h("td", { lang: "en" }, FG.textOf(term.name, "en").text),
        h("td", null, joined((stations.get(term["@id"]) || []).map(holderLink)))
      );
    const table = (rows) =>
      h(
        "table",
        { class: "catalogue-table" },
        h("thead", null, h("tr", null, h("th", { scope: "col" }, FG.t("catalogue.term")), h("th", { scope: "col" }, FG.t("catalogue.termEn")), h("th", { scope: "col" }, FG.t("catalogue.onPath")))),
        h("tbody", null, rows)
      );
    const build = () => listed(terms.filter((term) => matches("terms", FG.bothLanguages(term.name))), row, table);
    return [
      h("h2", null, FG.t("catalogue.tab.terms")),
      h("p", null, FG.t("catalogue.intro.terms"), " ", glossary ? FG.external(glossary.url, FG.text(glossary.name)) : null, glossary && glossary.dateCreated ? " · " + FG.t("finder.snapshot", { date: FG.formatDate(glossary.dateCreated) }) : null),
      searchBox("terms", build),
      h("div", { id: "catalogue-list" }, build()),
    ];
  };

  /* ---------------------------------------------------------------- FIP profiles */

  function fipCard(fip) {
    const url = FG.refIds(fip, "sameAs")[0] || fip.url;
    const details = [fip.alternateName, fip.version ? FG.t("catalogue.version", { version: fip.version }) : null, fip.dateModified ? FG.formatDate(String(fip.dateModified).slice(0, 10)) : null].filter(Boolean);
    return h(
      "li",
      { class: "card", id: "item-" + fip.identifier },
      h("h3", null, url ? FG.external(url, FG.text(fip.name)) : FG.span(fip.name)),
      details.length ? h("p", { class: "small muted" }, details.join(" · ")) : null,
      fip.abstract ? h("p", null, FG.span(fip.abstract)) : null,
      h("div", { class: "badges" }, h("span", { class: "badge" }, FG.t("catalogue.declarations", { n: FG.refs(fip, "hasPart").length })), FG.verificationBadges(fip), FG.apiLink("fips", fip.identifier))
    );
  }

  FG.tabs.fips = function () {
    const fips = FG.refs(FG.get("#fips"), "hasPart");
    const build = () => listed(fips.filter((fip) => matches("fips", FG.bothLanguages(fip.name), fip.alternateName, FG.bothLanguages(fip.abstract))), fipCard, cards);
    return [h("h2", null, FG.t("catalogue.tab.fips")), h("p", null, FG.t("catalogue.intro.fips")), FG.dashboardNotice(), searchBox("fips", build), h("div", { id: "catalogue-list" }, build())];
  };

  /* ---------------------------------------------------------------- FAIR tests */

  function testCard(test) {
    const code = String(FG.id(test.about) || "").split("/").pop();
    const principle = FG.principles().find((entry) => entry.termCode === code);
    const health = FG.id(test.healthStatus) || test.healthStatus;
    return h(
      "li",
      { class: "card", id: "item-" + test.identifier },
      h("h3", null, FG.external(test.url, FG.text(test.name))),
      h(
        "div",
        { class: "badges" },
        principle ? FG.principleTile(principle) : null,
        health ? h("span", { class: "badge", "data-health": String(health) }, FG.t("catalogue.health." + health), test.statusAsOf ? h("span", { class: "muted" }, " · " + FG.t("status.asOf", { date: FG.formatDate(test.statusAsOf) })) : null) : null,
        h("span", { class: "badge code" }, test.identifier),
        FG.apiLink("tests", test.identifier)
      )
    );
  }

  FG.tabs.tests = function () {
    const tests = FG.graph.filter((entity) => String(entity["@id"]).startsWith("#test-"));
    const build = () => listed(tests.filter((test) => matches("tests", FG.bothLanguages(test.name), test.identifier)), testCard, cards);
    return [h("h2", null, FG.t("catalogue.tab.tests")), h("p", null, FG.t("catalogue.intro.tests")), searchBox("tests", build), h("div", { id: "catalogue-list" }, build())];
  };

  /* ---------------------------------------------------------------- content changes */

  /** A content change: when, what kind, what was done and on what it drew; who and with which tool stays in the
      paradata, so the catalogue repeats no names. */
  function actionItem(action, cited) {
    const created = /^Create/.test(String(FG.list(action["@type"])[0]));
    const sources = FG.refs(action, "object").filter((entity) => cited.has(entity["@id"]));
    const results = FG.refIds(action, "result").length;
    return h(
      "li",
      { class: "change", id: "item-" + String(action["@id"]).replace(/^#action-/, "") },
      h("p", { class: "change-head" }, h("time", { datetime: String(action.endTime || "") }, FG.formatDate(String(action.endTime || "").slice(0, 10))), " · ", FG.t(created ? "catalogue.created" : "catalogue.updated"), " · ", h("strong", { lang: "en" }, FG.text(action.name))),
      action.description ? h("p", { class: "small", lang: "en" }, FG.text(action.description)) : null,
      h(
        "p",
        { class: "small muted" },
        FG.t("catalogue.changedItems", { n: results }),
        sources.length ? [" · ", FG.t("catalogue.drewOn") + ": ", joined(sources.map((source) => h("span", { lang: source.inLanguage || null }, FG.text(source.name))))] : null,
        " ",
        FG.apiLink("actions", String(action["@id"]).replace(/^#action-/, ""))
      )
    );
  }

  FG.tabs.actions = function () {
    const actions = FG.graph.filter((entity) => String(entity["@id"]).startsWith("#action-")).sort((a, b) => String(b.endTime || "").localeCompare(String(a.endTime || "")));
    const cited = new Set(FG.refIds(FG.get("#sources"), "hasPart"));
    const build = () =>
      listed(
        actions.filter((action) => matches("actions", FG.text(action.name), FG.text(action.description))),
        (action) => actionItem(action, cited),
        (items) => h("ol", { class: "changes" }, items)
      );
    return [
      h("h2", null, FG.t("catalogue.tab.actions")),
      h("p", null, FG.t("catalogue.intro.actions"), " ", h("a", { href: FG.href("page", "machines") }, FG.t("catalogue.machinesLink"))),
      searchBox("actions", build),
      h("div", { id: "catalogue-list" }, build()),
    ];
  };

  /* ---------------------------------------------------------------- the view */

  function tabBar(current) {
    return h(
      "nav",
      { class: "catalogue-tabs", "aria-label": FG.t("catalogue.tabs") },
      h(
        "ul",
        null,
        TABS.map((tab) => {
          const href = FG.catalogueHref(tab);
          const open = (event) => {
            if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            FG.navigateInPlace(href, `.catalogue-tabs a[data-tab="${tab}"]`);
          };
          return h("li", null, h("a", { href, "data-tab": tab, "aria-current": tab === current ? "page" : null, onclick: open }, FG.t("catalogue.tab." + tab)));
        })
      )
    );
  }

  FG.views.catalogue = function (route) {
    const tab = TABS.includes(route.arg) ? route.arg : "resources";
    return h(
      "div",
      { class: "wrap catalogue" },
      FG.heading(1, null, FG.t("catalogue.title")),
      h("p", { class: "lead" }, FG.t("catalogue.intro.all"), " ", h("a", { href: FG.href("page", "machines") }, FG.t("catalogue.machinesLink"))),
      tabBar(tab),
      h("section", { class: "catalogue-tab", "aria-label": FG.t("catalogue.tab." + tab) }, FG.tabs[tab](route))
    );
  };
})();
