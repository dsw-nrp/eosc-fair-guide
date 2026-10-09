/* Catalogue of the FAIR Data Guide: one list of everything in the knowledge base, narrowed by facets with counts.
   Kind is a single choice that shows every kind with its count; search, station and principle apply across kinds
   and stay when the kind changes; a facet that belongs to one kind is labelled with it. The reader chooses the ordering, groups follow it, and the
   whole state is part of the address, so a filtered list is a link. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);
  const KINDS = ["resources", "repositories", "clauses", "questions", "terms", "fips", "tests", "actions"];
  /* Older addresses named the kinds as tabs; cited sources are now part of the resources. */
  const ALIASES = { sources: "resources" };
  const PAGE = 50;
  /* Values shown before "more"; the nine stations always show in full. */
  const SHOWN_VALUES = 9;
  const expanded = new Set();
  const openFacets = new Set();

  /* ---------------------------------------------------------------- shared helpers */

  /** The link to an entity's JSON record in the guide's API; nothing until the API is published. */
  FG.apiLink = function (collection, id) {
    const api = FG.config.api;
    if (!api || !api.base || !id) return null;
    return h("a", { class: "json-link", href: api.base + collection + "/" + encodeURIComponent(id) + ".json", type: "application/json" }, "JSON");
  };

  /** The address of the catalogue showing one kind, or one entry of it. */
  FG.catalogueHref = (kind, item) => FG.href("catalogue", kind) + (item ? "/" + encodeURIComponent(item) : "");

  /** The catalogue searched for a query within one kind, as the landing's search links to it. */
  FG.catalogueSearchHref = (query, kind) => writeState({ kinds: [kind || "resources"], stations: [], principles: [], q: query, order: "", f: {} });


  /** An identifier as a small chip that leads to its entry in the catalogue. */
  FG.idChip = function (kind, id) {
    return h("a", { class: "id-chip", href: FG.catalogueHref(kind, id), title: FG.t("catalogue.openEntry", { id }) }, id);
  };

  /** A requirement or finding as the guide shows it wherever it cites one: the text first, then its identifier,
      leading to the catalogue, and its source; a note when the statement needs refreshing or was superseded. */
  FG.clauseEntry = function (clause) {
    const source = FG.get(clause.isPartOf);
    const status = clause.creativeWorkStatus;
    const isClause = String(clause["@id"]).startsWith("#clause-");
    return h(
      "li",
      { class: "clause" },
      h("p", { class: "clause-text" }, FG.span(clause.text || clause.name)),
      h(
        "p",
        { class: "clause-meta small" },
        isClause ? FG.idChip("clauses", clause.identifier) : null,
        source ? [isClause ? " · " : null, source.url ? FG.external(source.url, FG.nameNodes(source)) : FG.nameNodes(source)] : null
      ),
      status && status !== "current" && clause.note
        ? h("p", { class: "small clause-note" }, h("strong", null, FG.t(status === "superseded" ? "explorer.superseded" : "explorer.refresh") + ": "), FG.span(clause.note))
        : null
    );
  };

  const joined = (links) => links.flatMap((link, index) => (index ? [", ", link] : [link]));
  const code = (iri) => String(FG.id(iri) || iri || "").split("/").pop();
  const slug = (value) => FG.fold(value).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  /** A station or a check, as a short link. */
  function holderLink(holder) {
    return holder.position
      ? h("a", { href: FG.href("path", holder.identifier) }, holder.position + " · ", FG.span(holder.name))
      : h("a", { href: FG.href("check", holder.identifier) }, FG.span(holder.name));
  }

  /** Where each clause and each source is cited: the stations and checks whose items cite the clause. */
  function citations() {
    const bySource = new Map();
    const byClause = new Map();
    const note = (map, key, holder) => {
      const list = map.get(key) || [];
      if (!list.includes(holder)) list.push(holder);
      map.set(key, list);
    };
    const holders = FG.stations()
      .map((station) => [station, FG.refs(station, "itemListElement")])
      .concat(FG.ofType("Quiz").map((check) => [check, FG.refs(check, "hasPart")]));
    for (const [holder, items] of holders) {
      for (const item of items) {
        for (const clause of FG.refs(item, "citation")) {
          note(byClause, clause["@id"], holder);
          if (FG.id(clause.isPartOf)) note(bySource, FG.id(clause.isPartOf), holder);
        }
      }
    }
    return { bySource, byClause };
  }

  const stationsOf = (holders) => holders.filter((holder) => holder.position).map((station) => station.identifier);

  /* ---------------------------------------------------------------- entries of each kind */

  function sourceForm(source) {
    const extra = FG.list(source.additionalType).map(String);
    if (extra.some((type) => /Dataset$/.test(type))) return "Dataset";
    if (extra.some((type) => /SoftwareSourceCode$/.test(type))) return "SoftwareSourceCode";
    return String(FG.list(source["@type"])[0]);
  }

  /** How a cited work is cited: publisher, version and date, as badges. */
  function citationBadges(entity) {
    const publisher = FG.get(entity.publisher);
    const date = entity.datePublished
      ? FG.t("catalogue.published", { date: String(entity.datePublished).length === 10 ? FG.formatDate(entity.datePublished) : String(entity.datePublished) })
      : entity.sdDatePublished
        ? FG.t("catalogue.accessed", { date: FG.formatDate(entity.sdDatePublished) })
        : null;
    return [
      publisher ? h("span", { class: "badge" }, FG.text(publisher.alternateName || publisher.name)) : null,
      entity.version ? h("span", { class: "badge" }, FG.t("catalogue.version", { version: entity.version })) : null,
      date ? h("span", { class: "badge" }, date) : null,
    ];
  }

  const useMark = (use) => h("span", { class: "badge use-mark", "data-use": use }, FG.t("catalogue.use." + use));

  /** Resources and cited sources as one kind, each marked by how the guide uses it, with the FIP Dashboard's
      resources folded in. */
  function resourceEntries(cited) {
    const entries = [];
    const recommendedAt = new Map();
    for (const station of FG.stations()) for (const id of FG.refIds(station, "mentions")) recommendedAt.set(id, (recommendedAt.get(id) || []).concat(station));
    const citedSet = new Set(FG.refIds(FG.get("#sources"), "hasPart"));
    const linkedFers = new Set();
    const resources = FG.graph.filter((entity) => entity.resourceType && String(entity["@id"]).startsWith("#resource-"));
    for (const resource of resources) {
      const record = FG.dashboardRecord(resource);
      if (record && record.fer) linkedFers.add(record.fer["@id"]);
      const recommended = recommendedAt.get(resource["@id"]) || [];
      const citedBy = cited.get(resource["@id"]) || [];
      const uses = [recommended.length ? "recommended" : null, citedSet.has(resource["@id"]) ? "cited" : null, record ? "dashboard" : null].filter(Boolean);
      entries.push({
        kind: "resources",
        anchor: resource.identifier,
        name: FG.text(resource.name),
        export: { url: resource.url, text: FG.text(resource.description) },
        text: [FG.bothLanguages(resource.name), FG.bothLanguages(resource.description), resource.alternateName].join(" "),
        stations: [...new Set(stationsOf(recommended).concat(stationsOf(citedBy)))],
        principles: record && record.fer ? FG.refs(record.fer, "about").map(code) : [],
        facets: {
          use: uses,
          type: [FG.id(resource.resourceType)],
          status: FG.id(resource.serviceStatus) ? [FG.id(resource.serviceStatus)] : [],
          language: FG.list(resource.inLanguage).map(String),
          lens: FG.refIds(resource, "audience").map((id) => id.replace("#lens-", "")),
        },
        render: () =>
          FG.resourceCard(resource, {
            badges: [uses.map(useMark), citationBadges(resource), FG.apiLink("resources", resource.identifier)],
            after: [
              recommended.length ? h("p", { class: "small cited-by" }, FG.t("catalogue.recommendedAt") + ": ", joined(recommended.map(holderLink))) : null,
              citedBy.length ? h("p", { class: "small cited-by" }, FG.t("catalogue.citedBy") + ": ", joined(citedBy.map(holderLink))) : null,
            ],
          }),
      });
    }
    for (const source of FG.refs(FG.get("#sources"), "hasPart").filter((entity) => !entity.resourceType)) {
      const citedBy = cited.get(source["@id"]) || [];
      const url = source.url || (String(source["@id"]).startsWith("https://") ? source["@id"] : null);
      const name = FG.nameNodes(source);
      entries.push({
        kind: "resources",
        anchor: source.identifier,
        name: FG.text(source.name),
        export: { url },
        text: [FG.text(source.name), source.creditText, FG.text((FG.get(source.publisher) || {}).name)].join(" "),
        stations: stationsOf(citedBy),
        principles: [],
        facets: { use: ["cited"], type: ["form:" + sourceForm(source)], status: [], language: FG.list(source.inLanguage).map(String), lens: [] },
        render: () =>
          h(
            "li",
            { class: "card", id: "item-" + source.identifier, tabindex: "-1" },
            h("h3", null, url ? FG.external(url, name) : name),
            source.creditText ? h("p", { class: "small" }, source.creditText) : null,
            h("div", { class: "badges" }, h("span", { class: "badge" }, FG.t("catalogue.sourceType." + sourceForm(source))), useMark("cited"), citationBadges(source), FG.apiLink("resources", source.identifier)),
            citedBy.length ? h("p", { class: "small cited-by" }, FG.t("catalogue.citedBy") + ": ", joined(citedBy.map(holderLink))) : null
          ),
      });
    }
    for (const fer of FG.refs(FG.get("#fers"), "hasPart").filter((entity) => !linkedFers.has(entity["@id"]))) {
      entries.push({
        kind: "resources",
        anchor: "fer-" + fer.identifier,
        name: FG.text(fer.name),
        export: { url: fer.url, text: FG.text(fer.description) },
        text: [FG.text(fer.name), FG.bothLanguages(fer.description)].join(" "),
        stations: [],
        principles: FG.refs(fer, "about").map(code),
        facets: { use: ["dashboard"], type: ["fer:" + FG.id(fer.catalogueType)], status: [], language: [], lens: [] },
        render: () => FG.ferCard(fer, { badges: [useMark("dashboard"), FG.apiLink("fers", fer.identifier)] }),
      });
    }
    return entries;
  }

  function repositoryEntries() {
    return FG.repositoryEntries().map((repository) => {
      const anchor = repository["@id"] ? String(repository["@id"]).replace(/^#(repository|resource)-/, "") : "nkr-" + slug(FG.text(repository.name));
      const kindIndex = FG.repositoryKindOrder.indexOf(FG.id(repository.repositoryKind));
      return {
        kind: "repositories",
        anchor,
        name: FG.text(repository.name),
        export: { url: repository.url },
        text: [FG.text(repository.name), FG.list(repository.keywords).map((word) => (typeof word === "string" ? word : word["@value"])).join(" ")].join(" "),
        stations: ["repozitar"],
        principles: [],
        order: (kindIndex < 0 ? FG.repositoryKindOrder.length : kindIndex) + ":" + FG.fold(FG.text(repository.name)),
        facets: {
          rkind: FG.id(repository.repositoryKind) ? [FG.id(repository.repositoryKind)] : [],
          rsource: FG.refIds(repository, "isBasedOn").concat(repository.nkr ? ["nkr"] : [], repository.fairsharing ? ["fairsharing"] : []),
        },
        render: () => FG.repositoryCard(repository, "item-" + anchor),
      };
    });
  }

  function sourceLine(clause) {
    const source = FG.get(clause.isPartOf);
    if (!source) return null;
    return h("p", { class: "small cited-by" }, FG.t("catalogue.source") + ": ", h("a", { href: FG.catalogueHref("resources", source.identifier) }, FG.nameNodes(source)));
  }

  function clauseEntries(used) {
    return FG.refs(FG.get("#ledger"), "hasPart").map((clause, index) => {
      const holders = used.get(clause["@id"]) || [];
      const status = clause.creativeWorkStatus || "current";
      const audience = FG.id(clause.audience);
      return {
        kind: "clauses",
        anchor: clause.identifier,
        name: clause.identifier,
        export: { text: FG.text(clause.text) },
        text: [clause.identifier, FG.bothLanguages(clause.text)].join(" "),
        stations: stationsOf(holders),
        principles: FG.principlesOf(clause).map((principle) => principle.termCode),
        order: String(index).padStart(4, "0"),
        group: { source: FG.id(clause.isPartOf) },
        facets: { ckind: clause.clauseKind ? [clause.clauseKind] : [], csource: [FG.id(clause.isPartOf)], actor: audience ? [audience] : [], cstatus: [status] },
        render: () =>
          h(
            "li",
            { class: "card clause-card", id: "item-" + clause.identifier, tabindex: "-1" },
            h("p", { class: "clause-head" }, h("span", { class: "id-chip id-chip-static" }, clause.identifier), clause.clauseKind ? h("span", { class: "badge" }, FG.t("catalogue.clauseKind." + clause.clauseKind)) : null),
            h("p", null, FG.span(clause.text)),
            h(
              "div",
              { class: "badges" },
              FG.principlesOf(clause).map((principle) => FG.principleTile(principle)),
              audience ? h("span", { class: "badge" }, FG.termName(audience)) : null,
              status !== "current" ? h("span", { class: "badge", "data-clause-status": status }, FG.t(status === "superseded" ? "explorer.superseded" : "explorer.refresh")) : null,
              FG.apiLink("clauses", clause.identifier)
            ),
            status !== "current" && clause.note ? h("p", { class: "small clause-note" }, FG.span(clause.note)) : null,
            sourceLine(clause),
            holders.length ? h("p", { class: "small cited-by" }, FG.t("catalogue.usedIn") + ": ", joined(holders.map(holderLink))) : null
          ),
      };
    });
  }

  function questionEntries() {
    return FG.ofType("Quiz").flatMap((check, checkIndex) =>
      FG.refs(check, "hasPart")
        .sort(FG.byPosition)
        .map((item) => {
          const clauses = FG.refs(item, "citation").filter((clause) => String(clause["@id"]).startsWith("#clause-"));
          const station = String(FG.id(item.fixAt) || "").replace("#station-", "");
          return {
            kind: "questions",
            anchor: item.identifier,
            name: item.identifier,
            export: { text: FG.text(item.text) },
            text: [item.identifier, FG.bothLanguages(item.text)].join(" "),
            stations: station ? [station] : [],
            principles: FG.principlesOf(item).map((principle) => principle.termCode),
            order: String(checkIndex).padStart(2, "0") + ":" + String(item.position || 0).padStart(4, "0"),
            group: { check: check.identifier },
            facets: { check: [check.identifier], tier: FG.id(item.tier) ? [FG.id(item.tier)] : [] },
            render: () =>
              h(
                "li",
                { class: "card", id: "item-" + item.identifier, tabindex: "-1" },
                h("p", { class: "clause-head" }, h("span", { class: "id-chip id-chip-static" }, item.identifier), item.tier ? h("span", { class: "badge" }, FG.termName(FG.id(item.tier))) : null),
                h("p", null, FG.span(item.text)),
                h("div", { class: "badges" }, FG.principlesOf(item).map((principle) => FG.principleTile(principle)), FG.apiLink("questions", item.identifier)),
                h("p", { class: "small cited-by" }, FG.t("catalogue.inCheck") + ": ", h("a", { href: FG.href("check", check.identifier) }, FG.span(check.name))),
                clauses.length ? h("p", { class: "small cited-by" }, FG.t("catalogue.basedOn") + ": ", joined(clauses.map((clause) => FG.idChip("clauses", clause.identifier)))) : null
              ),
          };
        })
    );
  }

  function termEntries() {
    const stations = new Map();
    for (const station of FG.stations()) for (const id of FG.refIds(station, "mentions")) stations.set(id, (stations.get(id) || []).concat(station));
    return FG.refs(FG.get("#glossary"), "hasDefinedTerm").map((term) => {
      const at = stations.get(term["@id"]) || [];
      const cs = FG.textOf(term.name, "cs").text;
      const en = FG.textOf(term.name, "en").text;
      return {
        kind: "terms",
        anchor: String(term.termCode),
        name: cs.replace(/^[[(]+/, ""),
        export: { name: FG.text(term.name), url: term.url },
        nameEn: en.replace(/^[[(]+/, ""),
        text: cs + " " + en,
        stations: stationsOf(at),
        principles: [],
        facets: {},
        render: () =>
          h(
            "li",
            { class: "card term-card", id: "item-" + term.termCode, tabindex: "-1" },
            h("h3", { lang: "cs" }, FG.external(term.url, cs)),
            h("p", { class: "small", lang: "en" }, en),
            at.length ? h("p", { class: "small cited-by" }, FG.t("catalogue.onPath") + ": ", joined(at.map(holderLink))) : null
          ),
      };
    });
  }

  function fipEntries() {
    return FG.refs(FG.get("#fips"), "hasPart").map((fip) => {
      const url = FG.refIds(fip, "sameAs")[0] || fip.url;
      const details = [fip.alternateName, fip.version ? FG.t("catalogue.version", { version: fip.version }) : null, fip.dateModified ? FG.formatDate(String(fip.dateModified).slice(0, 10)) : null].filter(Boolean);
      return {
        kind: "fips",
        anchor: fip.identifier,
        name: FG.text(fip.name),
        export: { url },
        text: [FG.bothLanguages(fip.name), fip.alternateName, FG.bothLanguages(fip.abstract)].join(" "),
        stations: [],
        principles: [],
        facets: {},
        render: () =>
          h(
            "li",
            { class: "card", id: "item-" + fip.identifier, tabindex: "-1" },
            h("h3", null, url ? FG.external(url, FG.text(fip.name)) : FG.span(fip.name)),
            details.length ? h("p", { class: "small muted" }, details.join(" · ")) : null,
            fip.abstract ? h("p", null, FG.span(fip.abstract)) : null,
            h("div", { class: "badges" }, h("span", { class: "badge" }, FG.t("catalogue.declarations", { n: FG.refs(fip, "hasPart").length })), FG.verificationBadges(fip), FG.apiLink("fips", fip.identifier))
          ),
      };
    });
  }

  function testEntries() {
    return FG.graph
      .filter((entity) => String(entity["@id"]).startsWith("#test-"))
      .map((test) => {
        const principle = FG.principles().find((entry) => entry.termCode === code(test.about));
        const health = FG.id(test.healthStatus) || test.healthStatus;
        return {
          kind: "tests",
          anchor: test.identifier,
          name: FG.text(test.name),
          export: { url: FG.refIds(test, "sameAs")[0] || test.url },
          text: [FG.bothLanguages(test.name), test.identifier].join(" "),
          stations: [],
          principles: principle ? [principle.termCode] : [],
          facets: {},
          render: () =>
            h(
              "li",
              { class: "card", id: "item-" + test.identifier, tabindex: "-1" },
              h("h3", null, FG.external(test.url, FG.text(test.name))),
              h(
                "div",
                { class: "badges" },
                principle ? FG.principleTile(principle) : null,
                health ? h("span", { class: "badge", "data-health": String(health) }, FG.t("catalogue.health." + health), test.statusAsOf ? h("span", { class: "muted" }, " · " + FG.t("status.asOf", { date: FG.formatDate(test.statusAsOf) })) : null) : null,
                h("span", { class: "badge code" }, test.identifier),
                FG.apiLink("tests", test.identifier)
              )
            ),
        };
      });
  }

  /** A content change: when, what kind, what was done and on what it drew; who and with which tool stays in the
      paradata, so the catalogue repeats no names. */
  function actionEntries() {
    const cited = new Set(FG.refIds(FG.get("#sources"), "hasPart"));
    return FG.graph
      .filter((entity) => String(entity["@id"]).startsWith("#action-"))
      .map((action) => {
        const created = /^Create/.test(String(FG.list(action["@type"])[0]));
        const sources = FG.refs(action, "object").filter((entity) => cited.has(entity["@id"]));
        const id = String(action["@id"]).replace(/^#action-/, "");
        return {
          kind: "actions",
          anchor: id,
          name: FG.text(action.name),
          export: { text: FG.text(action.description) },
          date: String(action.endTime || ""),
          text: [FG.text(action.name), FG.text(action.description)].join(" "),
          stations: [],
          principles: [],
          facets: { change: [created ? "created" : "updated"] },
          render: () =>
            h(
              "li",
              { class: "card change", id: "item-" + id, tabindex: "-1" },
              h("p", { class: "change-head small" }, h("time", { datetime: String(action.endTime || "") }, FG.formatDate(String(action.endTime || "").slice(0, 10))), " · ", FG.t(created ? "catalogue.created" : "catalogue.updated")),
              h("h3", { lang: "en" }, FG.text(action.name)),
              action.description ? h("p", { class: "small", lang: "en" }, FG.text(action.description)) : null,
              h(
                "p",
                { class: "small muted" },
                FG.t("catalogue.changedItems", { n: FG.refIds(action, "result").length }),
                sources.length ? [" · ", FG.t("catalogue.drewOn") + ": ", joined(sources.map((source) => h("span", null, FG.nameNodes(source))))] : null,
                " ",
                FG.apiLink("actions", id)
              )
            ),
        };
      });
  }

  function allEntries() {
    const { bySource, byClause } = citations();
    return {
      resources: resourceEntries(bySource),
      repositories: repositoryEntries(),
      clauses: clauseEntries(byClause),
      questions: questionEntries(),
      terms: termEntries(),
      fips: fipEntries(),
      tests: testEntries(),
      actions: actionEntries(),
    };
  }

  /* ---------------------------------------------------------------- exports */

  /** One entry as a row of an exported list, in the reader's language. */
  function exportRow(entry) {
    const out = entry.export || {};
    const row = { id: entry.anchor, name: out.name || entry.name, text: out.text || "", url: out.url || "", date: String(entry.date || "").slice(0, 10) };
    for (const facet of KIND_FACETS[entry.kind] || []) row[facet.key] = (entry.facets[facet.key] || []).map(facet.label);
    row.stations = entry.stations.map((id) => FG.text((FG.get("#station-" + id) || {}).name));
    row.principles = entry.principles;
    row.entry = (FG.config.pageUrl || "") + FG.catalogueHref(entry.kind, entry.anchor);
    return row;
  }

  /** The columns of a kind's list: the fields its entries fill, its facets, where the guide uses them, the link. */
  function exportColumns(kind, rows) {
    const facets = (KIND_FACETS[kind] || []).map((facet) => facet.key);
    const filled = ["id", "name", "text", "url", "date"].filter((key) => rows.some((row) => row[key]));
    return filled.concat(facets, ["stations", "principles", "entry"]).map((key) => ({ key, label: facets.includes(key) ? FG.t("catalogue.facet." + key) : FG.t("export.column." + key) }));
  }

  /** The list the catalogue shows, as CSV and JSON, in the order shown and with the filters that made it. */
  function offerListExports(kind, groups) {
    const rows = [...new Set(groups.flatMap((group) => group.entries))].map(exportRow);
    const parts = ["catalogue", kind];
    const columns = exportColumns(kind, rows);
    const payload = () => ({
      title: FG.t("app.title") + " · " + FG.t("catalogue.tab." + kind),
      url: (FG.config.pageUrl || "") + window.location.hash,
      exported: FG.today(),
      language: FG.state.lang,
      version: FG.root.version,
      license: FG.id(FG.root.license),
      columns: Object.fromEntries(columns.map((column) => [column.key, column.label])),
      count: rows.length,
      items: rows,
    });
    FG.offerExport({ id: "csv", label: FG.t("export.csv", { n: rows.length }), run: () => FG.download(FG.exportName(parts, "csv"), FG.csv(columns, rows), "text/csv") });
    FG.offerExport({ id: "json", label: FG.t("export.json", { n: rows.length }), run: () => FG.download(FG.exportName(parts, "json"), JSON.stringify(payload(), null, 2) + "\n", "application/json") });
  }

  /* ---------------------------------------------------------------- facets of one kind */

  const termLabel = (id) => FG.termName(id) || id;
  const KIND_FACETS = {
    resources: [
      { key: "use", values: () => ["recommended", "cited", "dashboard"], label: (value) => FG.t("catalogue.use." + value) },
      { key: "type", label: (value) => (value.startsWith("form:") ? FG.t("catalogue.sourceType." + value.slice(5)) : value.startsWith("fer:") ? termLabel(value.slice(4)) : termLabel(value)) },
      { key: "status", label: termLabel },
      { key: "language", values: () => ["cs", "en"], label: (value) => FG.t("catalogue.language." + value) },
      /* The lens narrows what the guide recommends; a cited work or a dashboard record has no audience and stays. */
      { key: "lens", values: () => FG.lenses().map((lens) => lens.audienceType), label: (value) => FG.text((FG.lenses().find((lens) => lens.audienceType === value) || {}).name), passThrough: true },
    ],
    repositories: [
      { key: "rkind", values: () => FG.repositoryKindOrder, label: termLabel },
      { key: "rsource", label: (value) => (value === "nkr" ? "NKR" : value === "fairsharing" ? "FAIRsharing" : FG.repositorySource(value)) },
    ],
    clauses: [
      { key: "ckind", values: () => ["requirement", "recommendation", "fulfilment", "statement"], label: (value) => FG.t("catalogue.clauseKind." + value) },
      { key: "csource", label: (value) => FG.text((FG.get(value) || {}).name) || value },
      { key: "actor", label: termLabel },
      { key: "cstatus", values: () => ["current", "refresh", "superseded"], label: (value) => FG.t("catalogue.clauseStatus." + value) },
    ],
    questions: [
      { key: "check", values: () => FG.ofType("Quiz").map((check) => check.identifier), label: (value) => FG.text((FG.get("#check-" + value) || {}).name) },
      { key: "tier", label: termLabel },
    ],
    actions: [{ key: "change", values: () => ["created", "updated"], label: (value) => FG.t("catalogue." + value) }],
  };

  /* ---------------------------------------------------------------- the state in the address */

  /** `k!resources_clauses~s!licence~p!R1.1~q!licence~o!name~f.use!cited`; a bare kind (an older tab address) selects
      that kind alone. */
  function readState(route) {
    const state = { kinds: [], stations: [], principles: [], q: "", order: "", f: {} };
    const arg = String(route.arg || "");
    if (KINDS.includes(arg) || ALIASES[arg]) {
      state.kinds = [ALIASES[arg] || arg];
      return state;
    }
    for (const field of arg.split("~")) {
      const [key, value = ""] = field.split("!");
      const list = value ? value.split("_").map(decodeURIComponent) : [];
      if (key === "k") state.kinds = list.filter((kind) => KINDS.includes(kind));
      else if (key === "s") state.stations = list;
      else if (key === "p") state.principles = list;
      else if (key === "q") state.q = decodeURIComponent(value);
      else if (key === "o") state.order = value;
      else if (key.startsWith("f.")) state.f[key.slice(2)] = list;
    }
    state.kinds = state.kinds.length ? state.kinds.slice(0, 1) : ["resources"];
    return state;
  }

  const encodePart = (value) => encodeURIComponent(value).replace(/[~!_]/g, (char) => "%" + char.charCodeAt(0).toString(16).toUpperCase());

  function writeState(state) {
    const fields = ["k!" + state.kinds.map(encodePart).join("_")];
    if (state.stations.length) fields.push("s!" + state.stations.map(encodePart).join("_"));
    if (state.principles.length) fields.push("p!" + state.principles.map(encodePart).join("_"));
    if (state.q) fields.push("q!" + encodePart(state.q));
    if (state.order) fields.push("o!" + state.order);
    for (const [key, list] of Object.entries(state.f)) fields.push("f." + key + "!" + list.map(encodePart).join("_"));
    return FG.href("catalogue", fields.join("~"));
  }

  /** The lens filter starts from the reader's lens until they choose otherwise. */
  const chosenValues = (state, route, key) => (key === "lens" && state.f.lens === undefined ? [route.lens] : state.f[key] || []);

  function passesShared(entry, state, skip) {
    if (state.q && !FG.fold(entry.text).includes(FG.fold(state.q))) return false;
    if (skip !== "station" && state.stations.length && !entry.stations.some((station) => state.stations.includes(station))) return false;
    if (skip !== "principle" && state.principles.length && !entry.principles.some((principle) => state.principles.includes(principle))) return false;
    return true;
  }

  function passesKind(entry, state, route, skip) {
    for (const facet of KIND_FACETS[entry.kind] || []) {
      if (facet.key === skip) continue;
      const chosen = chosenValues(state, route, facet.key);
      if (!chosen.length) continue;
      const values = entry.facets[facet.key] || [];
      if (facet.passThrough && !values.length) continue;
      if (!values.some((value) => chosen.includes(value))) return false;
    }
    return true;
  }

  /* ---------------------------------------------------------------- ordering and groups */

  const ORDERS_FOR = {
    resources: ["name"],
    repositories: ["guided", "name"],
    clauses: ["source", "principle", "station"],
    questions: ["check", "principle", "station"],
    terms: ["name", "nameEn"],
    fips: ["name"],
    tests: ["principle", "name"],
    actions: ["newest", "oldest"],
  };

  const ordersFor = (kind) => [...new Set(ORDERS_FOR[kind].concat(["name", "station", "principle"]))];

  const rankedPrinciples = () => FG.principles().slice().sort(FG.principleOrder).map((principle) => principle.termCode);
  const byName = (a, b) => FG.fold(a.name).localeCompare(FG.fold(b.name), "cs");
  const withinKind = (a, b) => (a.order !== undefined && b.order !== undefined ? String(a.order).localeCompare(String(b.order)) : 0) || byName(a, b);

  /** Groups for an ordering: a key, a heading and the entries, in the order of the groups. */
  function groupsFor(order, entries) {
    const stations = FG.stations().map((station) => station.identifier);
    const principles = rankedPrinciples();
    const grouped = (keyOf, labelOf, rankOf) => {
      const groups = new Map();
      for (const entry of entries) {
        const key = keyOf(entry);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(entry);
      }
      return [...groups.entries()].sort(([a], [b]) => rankOf(a) - rankOf(b)).map(([key, list]) => ({ key, label: labelOf(key), entries: list.sort(withinKind) }));
    };
    const rankIn = (list) => (key) => (key && list.includes(key) ? list.indexOf(key) : list.length);
    if (order === "station") {
      return grouped(
        (entry) => entry.stations.slice().sort((a, b) => stations.indexOf(a) - stations.indexOf(b))[0] || "",
        (key) => {
          const station = FG.get("#station-" + key);
          return station ? station.position + " · " + FG.text(station.name) : FG.t("catalogue.withoutStation");
        },
        rankIn(stations)
      );
    }
    if (order === "principle") {
      return grouped(
        (entry) => entry.principles.slice().sort((a, b) => principles.indexOf(a) - principles.indexOf(b))[0] || "",
        (key) => {
          const principle = FG.principles().find((entry) => entry.termCode === key);
          return principle ? key + " " + FG.text(principle.name) : FG.t("catalogue.withoutPrinciple");
        },
        rankIn(principles)
      );
    }
    if (order === "source") {
      const analysis = FG.id(FG.refs(FG.root, "isBasedOn")[0]);
      const names = new Map(entries.map((entry) => [entry.group.source, FG.text((FG.get(entry.group.source) || {}).name)]));
      const ranked = [...names.keys()].sort((a, b) => (a === analysis ? -1 : b === analysis ? 1 : FG.fold(names.get(a)).localeCompare(FG.fold(names.get(b)), "cs")));
      return grouped((entry) => entry.group.source, (key) => names.get(key) || key, rankIn(ranked));
    }
    if (order === "check") {
      const checks = FG.ofType("Quiz").map((check) => check.identifier);
      return grouped((entry) => entry.group.check, (key) => FG.text((FG.get("#check-" + key) || {}).name), rankIn(checks));
    }
    const sorted = entries.slice();
    if (order === "guided") sorted.sort(withinKind);
    else if (order === "newest") sorted.sort((a, b) => String(b.date).localeCompare(String(a.date)));
    else if (order === "oldest") sorted.sort((a, b) => String(a.date).localeCompare(String(b.date)));
    else if (order === "nameEn") sorted.sort((a, b) => FG.fold(a.nameEn || a.name).localeCompare(FG.fold(b.nameEn || b.name), "en"));
    else sorted.sort(byName);
    return [{ key: "all", label: null, entries: sorted }];
  }

  /* ---------------------------------------------------------------- the view */

  /** A facet as a group of checkboxes with counts; values past the first few open on request. */
  function facetGroup(name, legend, values, chosen, counts, labelOf, onToggle) {
    const open = openFacets.has(name);
    const shown = open ? values : values.filter((value, index) => index < SHOWN_VALUES || chosen.includes(value));
    return h(
      "fieldset",
      { class: "facet", "data-facet": name },
      h("legend", null, legend),
      h(
        "ul",
        null,
        shown.map((value) => {
          const id = "facet-" + name + "-" + slug(value);
          const count = counts.get(value) || 0;
          const checked = chosen.includes(value);
          return h(
            "li",
            { class: count || checked ? null : "facet-empty" },
            h("input", { type: "checkbox", id, checked, onchange: () => onToggle(value, "#" + CSS.escape(id)) }),
            h("label", { for: id }, h("span", { class: "facet-label" }, labelOf(value)), h("span", { class: "facet-count" }, String(count)))
          );
        })
      ),
      values.length > shown.length || open
        ? h(
            "button",
            {
              type: "button",
              class: "button-link small",
              onclick: () => {
                if (open) openFacets.delete(name);
                else openFacets.add(name);
                FG.rerender();
              },
            },
            open ? FG.t("catalogue.fewerValues") : FG.t("catalogue.moreValues", { n: values.length - shown.length })
          )
        : null
    );
  }

  /** The kind as a single choice, each with its count under the other filters and, where it shows none because it
      lacks a chosen dimension, the reason. */
  function kindPicker(selected, counts, noteOf, onPick) {
    return h(
      "fieldset",
      { class: "facet facet-kinds", "data-facet": "kind" },
      h("legend", null, FG.t("catalogue.facet.kind")),
      h(
        "ul",
        null,
        KINDS.map((kind) => {
          const id = "facet-kind-" + kind;
          const count = counts.get(kind) || 0;
          const note = noteOf(kind, count);
          return h(
            "li",
            { class: count || kind === selected ? null : "facet-empty" },
            h("input", { type: "radio", name: "catalogue-kind", id, checked: kind === selected, onchange: () => onPick(kind, "#" + id) }),
            h("label", { for: id }, h("span", { class: "facet-label" }, FG.t("catalogue.tab." + kind)), h("span", { class: "facet-count" }, String(count))),
            note ? h("span", { class: "facet-note small muted" }, note) : null
          );
        })
      )
    );
  }

  /** What a kind is, and for repositories the live sources, shown where its entries start. */
  function kindIntro(kind) {
    const intro = kind === "repositories" ? FG.t("repositories.intro") : FG.t("catalogue.intro." + kind);
    if (kind === "repositories") {
      const lookup = FG.repositoryEntries().map((repository) => ({ identifiers: repository.identifier, url: repository.url }));
      const nkr = FG.live.nkrControls();
      const fairsharing = FG.live.fairsharingControls(lookup);
      return h(
        "div",
        { class: "kind-intro" },
        h("p", { class: "small" }, intro),
        h("div", { class: "filter-actions" }, nkr.button, fairsharing.button),
        nkr.status || fairsharing.status ? h("div", { class: "filter-status" }, nkr.status, fairsharing.status) : null
      );
    }
    return h(
      "div",
      { class: "kind-intro" },
      h("p", { class: "small" }, intro, kind === "actions" ? [" ", h("a", { href: FG.href("page", "machines") }, FG.t("catalogue.machinesLink"))] : null),
      kind === "fips" || kind === "resources" ? FG.dashboardNotice() : null
    );
  }

  FG.views.catalogue = function (route) {
    const state = readState(route);
    const entries = allEntries();
    const go = (next, focus) => FG.replaceInPlace(writeState(next), focus);
    const toggle = (list, value) => (list.includes(value) ? list.filter((item) => item !== value) : list.concat(value));

    /* A link to one entry shows its kind unfiltered, so the entry is there. */
    if (route.extra) Object.assign(state, { stations: [], principles: [], q: "", f: { lens: [] } });

    const kind = state.kinds[0];
    const selected = [kind];
    const inKinds = entries[kind];
    const visible = inKinds.filter((entry) => passesShared(entry, state) && passesKind(entry, state, route));
    const orders = ordersFor(kind);
    const order = orders.includes(state.order) ? state.order : orders[0];

    /* Counts: kinds under every filter; a shared facet under every other filter; a kind's facet within that kind. */
    const kindCounts = new Map(KINDS.map((kind) => [kind, entries[kind].filter((entry) => passesShared(entry, state) && passesKind(entry, state, route)).length]));
    const lacks = (kind, dimension) => !entries[kind].some((entry) => entry[dimension].length);
    const sharedCounts = (dimension, skip) => {
      const counts = new Map();
      for (const entry of inKinds.filter((item) => passesShared(item, state, skip) && passesKind(item, state, route))) {
        for (const value of new Set(entry[dimension])) counts.set(value, (counts.get(value) || 0) + 1);
      }
      return counts;
    };
    const kindFacetCounts = (kind, key) => {
      const counts = new Map();
      for (const entry of entries[kind].filter((item) => passesShared(item, state) && passesKind(item, state, route, key))) {
        for (const value of new Set(entry.facets[key] || [])) counts.set(value, (counts.get(value) || 0) + 1);
      }
      return counts;
    };
    const kindNote = (other, count) => {
      if (!count && state.stations.length && lacks(other, "stations")) return FG.t("catalogue.noStation");
      if (!count && state.principles.length && lacks(other, "principles")) return FG.t("catalogue.noPrinciple");
      return null;
    };

    const search = h(
      "div",
      { class: "facet-search" },
      h("label", { for: "catalogue-search" }, FG.t("catalogue.search")),
      h("input", {
        type: "search",
        id: "catalogue-search",
        value: state.q,
        oninput: (event) => {
          clearTimeout(FG.catalogueTyping);
          const value = event.target.value;
          FG.catalogueTyping = setTimeout(() => go(Object.assign({}, state, { q: value.trim() }), "#catalogue-search"), 300);
        },
      })
    );
    const stationLabel = (id) => {
      const station = FG.get("#station-" + id);
      return station ? station.position + " · " + FG.text(station.name) : id;
    };
    const principleLabel = (value) => value + " " + FG.text((FG.principles().find((entry) => entry.termCode === value) || {}).name);
    const facets = [
      search,
      /* Changing the kind keeps search, station, principle and lens, and drops the previous kind's own facets. */
      kindPicker(kind, kindCounts, kindNote, (other, focus) => go(Object.assign({}, state, { kinds: [other], order: "", f: state.f.lens === undefined ? {} : { lens: state.f.lens } }), focus)),
      facetGroup("station", FG.t("catalogue.facet.station"), FG.stations().map((station) => station.identifier), state.stations, sharedCounts("stations", "station"), stationLabel, (id, focus) =>
        go(Object.assign({}, state, { stations: toggle(state.stations, id) }), focus)
      ),
      facetGroup("principle", FG.t("catalogue.facet.principle"), rankedPrinciples(), state.principles, sharedCounts("principles", "principle"), principleLabel, (value, focus) =>
        go(Object.assign({}, state, { principles: toggle(state.principles, value) }), focus)
      ),
      selected.map((own) => {
        const ownFacets = KIND_FACETS[own] || [];
        if (!ownFacets.length) return null;
        return h(
          "div",
          { class: "facet-kind" },
          h("p", { class: "facet-kind-name" }, FG.t("catalogue.tab." + own)),
          ownFacets.map((facet) => {
            const counts = kindFacetCounts(own, facet.key);
            const values = facet.values ? facet.values() : [...counts.keys()].sort((a, b) => FG.fold(facet.label(a)).localeCompare(FG.fold(facet.label(b)), "cs"));
            const chosen = chosenValues(state, route, facet.key);
            return facetGroup(own + "-" + facet.key, FG.t("catalogue.facet." + facet.key), values, chosen, counts, facet.label, (value, focus) =>
              go(Object.assign({}, state, { f: Object.assign({}, state.f, { [facet.key]: toggle(chosen, value) }) }), focus)
            );
          })
        );
      }),
    ];

    /* Active filters as chips that remove themselves. */
    const chips = [];
    const chip = (label, next) =>
      chips.push(
        h("li", null, h("button", { type: "button", class: "filter-chip", "aria-label": FG.t("catalogue.remove", { label }), onclick: () => go(next, "#catalogue-search") }, label, h("span", { "aria-hidden": "true" }, " ×")))
      );
    if (state.q) chip("„" + state.q + "“", Object.assign({}, state, { q: "" }));
    for (const id of state.stations) chip(stationLabel(id), Object.assign({}, state, { stations: state.stations.filter((item) => item !== id) }));
    for (const value of state.principles) chip(principleLabel(value), Object.assign({}, state, { principles: state.principles.filter((item) => item !== value) }));
    for (const facet of KIND_FACETS[kind] || []) {
      const chosen = chosenValues(state, route, facet.key);
      for (const value of chosen) chip(FG.t("catalogue.facet." + facet.key) + ": " + facet.label(value), Object.assign({}, state, { f: Object.assign({}, state.f, { [facet.key]: chosen.filter((item) => item !== value) }) }));
    }

    const groups = groupsFor(order, visible);
    offerListExports(kind, groups);
    const used = new Set();
    const results = groups.map((group) => {
      /* A link to one entry shows the whole group it is in, so the entry is there to land on. */
      const all = expanded.has(group.key) || group.entries.length <= PAGE || (route.extra && group.entries.some((entry) => entry.anchor === route.extra));
      const cards = (all ? group.entries : group.entries.slice(0, PAGE)).map((entry) => {
        const node = entry.render();
        if (node.id && used.has(node.id)) node.removeAttribute("id");
        else used.add(node.id);
        return node;
      });
      return h(
        "section",
        { class: "catalogue-group" },
        group.label ? h("h2", null, group.label, h("span", { class: "muted group-count" }, " · " + FG.t("catalogue.entries", { n: group.entries.length }))) : null,
        h("ul", { class: "cards" }, cards),
        all
          ? null
          : h(
              "button",
              {
                type: "button",
                class: "button-small catalogue-more",
                onclick: () => {
                  expanded.add(group.key);
                  FG.rerender();
                },
              },
              FG.t("catalogue.more", { n: group.entries.length - PAGE })
            )
      );
    });
    results.unshift(kindIntro(kind));

    return h(
      "div",
      { class: "wrap catalogue" },
      FG.heading(1, null, FG.t("catalogue.title")),
      h("p", { class: "lead" }, FG.t("catalogue.intro.all"), " ", h("a", { href: FG.href("page", "machines") }, FG.t("catalogue.machinesLink"))),
      h(
        "div",
        { class: "catalogue-layout" },
        h(
          "details",
          /* Open beside the results on wide screens; on a phone closed until opened, so the results come first. */
          { class: "catalogue-facets", open: (FG.catalogueFacetsOpen ?? window.matchMedia("(min-width: 60rem)").matches) ? true : null, ontoggle: (event) => (FG.catalogueFacetsOpen = event.target.open) },
          h("summary", null, FG.t("catalogue.filters"), chips.length ? h("span", { class: "facet-count" }, String(chips.length)) : null),
          h("div", { class: "facet-panel" }, facets)
        ),
        h(
          "div",
          { class: "catalogue-results" },
          h(
            "div",
            { class: "catalogue-toolbar" },
            h("p", { role: "status", class: "catalogue-count" }, FG.t("finder.count", { n: visible.length })),
            h(
              "label",
              { class: "catalogue-order" },
              FG.t("catalogue.order"),
              h(
                "select",
                { id: "catalogue-order", onchange: (event) => go(Object.assign({}, state, { order: event.target.value }), "#catalogue-order") },
                orders.map((value) => h("option", { value, selected: value === order }, FG.t("catalogue.orderBy." + value)))
              )
            )
          ),
          chips.length
            ? h(
                "div",
                { class: "active-filters" },
                h("ul", { "aria-label": FG.t("catalogue.active") }, chips),
                h("button", { type: "button", class: "button-link small", onclick: () => go({ kinds: selected, stations: [], principles: [], q: "", order: state.order, f: { lens: [] } }, "#catalogue-search") }, FG.t("catalogue.clear"))
              )
            : null,
          results
        )
      )
    );
  };
})();
