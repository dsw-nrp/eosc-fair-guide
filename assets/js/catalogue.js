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
  /** The address of the catalogue showing one kind, or one entry of it. */
  FG.catalogueHref = (kind, item) => FG.href("catalogue", kind) + (item ? "/" + encodeURIComponent(item) : "");

  /** The catalogue searched for a query within one kind, as the landing's search links to it. */
  FG.catalogueSearchHref = (query, kind) => writeState({ kinds: [kind || "resources"], stations: [], principles: [], q: query, order: "", f: {} });


  /** An identifier as a small chip that leads to its entry in the catalogue. */
  FG.idChip = function (kind, id) {
    return h("a", { class: "id-chip", href: FG.catalogueHref(kind, id), title: FG.t("catalogue.openEntry", { id }) }, id);
  };

  /** A source's short name: a cited resource's own name, or a source's short name when it has one. */
  FG.shortName = (source) => FG.span(String(source["@id"]).startsWith("#resource-") ? source.name : source.alternateName || source.name);

  /** A work an entry rests on, by its short name, leading to its own entry in the catalogue. */
  FG.sourceLink = (source) => h("a", { class: "source-link", href: FG.catalogueHref("resources", source.identifier) }, FG.shortName(source));

  /** That a statement needs refreshing or was superseded, as a badge. */
  FG.clauseStatus = (status) =>
    status && status !== "current" ? h("span", { class: "badge", "data-clause-status": status }, FG.t(status === "superseded" ? "explorer.superseded" : "explorer.refresh")) : null;

  /** A requirement's guidance, as its source publishes it, behind a disclosure. */
  FG.guidance = (clause) =>
    clause.guidance
      ? h("details", { class: "clause-guidance" }, h("summary", null, FG.t("catalogue.guidance")), h("div", { class: "content", lang: "en" }, FG.paragraphs(clause.guidance)))
      : null;

  /** A requirement's title, when it has one besides its identifier. */
  FG.clauseTitle = (clause) => (clause.name && FG.text(clause.name) !== clause.identifier ? clause.name : null);

  /** A requirement or finding as the guide shows it wherever it cites one, the same in a station, the explorer and a
      question: its title when it has one besides its identifier, its text, then its identifier leading to the
      catalogue, its source by short name, and once that it needs refreshing or was superseded, with the note. */
  FG.clauseEntry = function (clause) {
    const source = FG.get(clause.isPartOf);
    const status = clause.creativeWorkStatus;
    const isClause = String(clause["@id"]).startsWith("#clause-");
    const title = FG.clauseTitle(clause);
    return h(
      "li",
      { class: "clause" },
      h("p", { class: "clause-text" }, title && clause.text ? [h("strong", null, FG.span(title)), " "] : null, FG.linkedSpan(clause, clause.text ? "text" : "name")),
      FG.guidance(clause),
      h(
        "p",
        { class: "clause-meta small" },
        isClause ? FG.idChip("clauses", clause.identifier) : null,
        source ? [isClause ? " · " : null, FG.sourceLink(source)] : null,
        FG.clauseStatus(status) ? [" ", FG.clauseStatus(status)] : null
      ),
      status && status !== "current" && clause.note ? h("p", { class: "small clause-note" }, FG.span(clause.note)) : null
    );
  };

  const code = (iri) => String(FG.id(iri) || iri || "").split("/").pop();
  const slug = (value) => FG.fold(value).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const icons = () => (FG.config && FG.config.icons) || {};

  /** A station or a check, as a link with its icon and name, as the path menu and the checks show them. */
  function holderLink(holder) {
    return holder.position
      ? h("a", { class: "holder-link", href: FG.href("path", holder.identifier) }, FG.icon((icons().station || {})[holder.identifier]), FG.span(holder.name))
      : h("a", { class: "holder-link", href: FG.href("check", holder.identifier) }, FG.icon((icons().check || {})[holder.identifier]), FG.span(holder.name));
  }

  /** Where the guide uses an entry: its stations in path order, then its checks, each once. */
  function inGuide(holders) {
    const unique = [...new Set(holders.filter(Boolean))];
    return unique
      .filter((holder) => holder.position)
      .sort((a, b) => Number(a.position) - Number(b.position))
      .concat(unique.filter((holder) => !holder.position))
      .map(holderLink);
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

  /* ---------------------------------------------------------------- one card for every kind */

  /* The relations a card may show, in this order, each under one label wherever it appears. */
  const RELATIONS = ["principles", "audience", "basedOn", "inGuide", "identifiers"];

  /** An entry as a card, the same for every kind: its own identifier with what it is and how the guide uses it;
      its title; one quiet line of details; its text; badges for its state only; then its relations, one row each,
      in a fixed order, each drawn one way everywhere. */
  function entryCard(spec) {
    const what = FG.list(spec.what).filter(Boolean);
    const details = FG.list(spec.details).filter(Boolean);
    const states = [spec.states].flat(Infinity).filter(Boolean);
    const rows = RELATIONS.map((key) => [key, [spec.relations && spec.relations[key]].flat(Infinity).filter(Boolean)]).filter(([, items]) => items.length);
    return h(
      "li",
      { class: ["card", "entry-card"].concat(spec.class || []).join(" "), id: "item-" + spec.id, tabindex: "-1" },
      h("p", { class: "entry-head" }, h("span", { class: "id-chip id-chip-static" }, spec.id), what.length ? h("span", { class: "entry-what" }, what.join(" · ")) : null, FG.apiLink(spec.entity)),
      spec.title ? h("h3", { class: "entry-title", lang: spec.titleLang || null }, spec.title) : null,
      spec.byline ? h("p", { class: "small entry-byline" }, spec.byline) : null,
      details.length ? h("p", { class: "small muted card-details", lang: spec.detailsLang || null }, details.join(" · ")) : null,
      spec.body,
      states.length ? h("div", { class: "badges" }, states) : null,
      spec.notes,
      rows.length
        ? h(
            "dl",
            { class: "relations" },
            rows.map(([key, items]) => [h("dt", null, FG.t("catalogue.relation." + key)), h("dd", { class: key === "identifiers" ? "pid-line" : null }, items)])
          )
        : null
    );
  }

  const tiles = (principles) => principles.map((principle) => FG.principleTile(principle));
  /** The audiences an entry is for, by icon and name. */
  const audiences = (lensIds) =>
    lensIds
      .map(FG.get)
      .filter(Boolean)
      .map((lens) => h("span", { class: "audience" }, FG.icon((icons().lens || {})[lens.audienceType]), FG.text(lens.name)));
  const sourceLink = (source) => FG.sourceLink(source);

  /* ---------------------------------------------------------------- entries of each kind */

  /* Citation forms that are also resource types read as one type: a cited document is a document. */
  const FORM_AS_TYPE = { DigitalDocument: "#rtype-document", CreativeWork: "#rtype-standard" };

  function sourceForm(source) {
    const extra = FG.list(source.additionalType).map(String);
    if (extra.some((type) => /Dataset$/.test(type))) return "Dataset";
    if (extra.some((type) => /SoftwareSourceCode$/.test(type))) return "SoftwareSourceCode";
    return String(FG.list(source["@type"])[0]);
  }

  /** How a cited work is cited, for the card's line of details: publisher, language, version and date. */
  function citationDetails(entity) {
    const publisher = FG.get(entity.publisher);
    const languages = FG.list(entity.inLanguage).map(String);
    const date = entity.datePublished
      ? FG.t("catalogue.published", { date: String(entity.datePublished).length === 10 ? FG.formatDate(entity.datePublished) : String(entity.datePublished) })
      : entity.sdDatePublished
        ? FG.t("catalogue.accessed", { date: FG.formatDate(entity.sdDatePublished) })
        : null;
    return [
      publisher ? FG.text(publisher.alternateName || publisher.name) : null,
      languages.length ? FG.t("resource.languages", { languages: languages.join(", ") }) : null,
      entity.version ? FG.t("catalogue.version", { version: entity.version }) : null,
      date,
    ];
  }

  const uses = (list) => list.map((use) => FG.t("catalogue.use." + use));

  function resourceCard(resource, record, used, holders) {
    return entryCard({
      id: resource.identifier,
      entity: resource,
      what: [FG.termName(FG.id(resource.resourceType))].concat(uses(used)),
      title: FG.external(resource.url, FG.nameNodes(resource)),
      details: citationDetails(resource),
      body: resource.description ? h("p", null, FG.span(resource.description)) : null,
      states: [FG.statusBadge(resource), record ? FG.verificationBadges(record.fer) : null],
      relations: {
        principles: record && record.fer ? tiles(FG.principlesOf(record.fer)) : [],
        audience: audiences(FG.refIds(resource, "audience")),
        inGuide: inGuide(holders),
        identifiers: FG.pidItems(resource).concat(record ? [FG.pidItem("dashboard", record.url)] : []),
      },
    });
  }

  /* Where sources are cited, worked out once for the parts of the knowledge base loaded so far. */
  let citedCache = null;
  const citedSources = () => {
    if (!citedCache || citedCache.parts !== FG.partsLoaded.size) citedCache = { parts: FG.partsLoaded.size, bySource: citations().bySource };
    return citedCache.bySource;
  };

  /** A resource's card wherever the guide shows it; at a station, without that station among where it is used. */
  FG.resourceCard = function (resource, except) {
    const record = FG.dashboardRecord(resource);
    const recommended = FG.stations().filter((station) => FG.refIds(station, "mentions").includes(resource["@id"]));
    const holders = recommended.concat(citedSources().get(resource["@id"]) || []).filter((holder) => holder.identifier !== except);
    const cited = FG.refIds(FG.get("#sources"), "hasPart").includes(resource["@id"]);
    const used = [recommended.length ? "recommended" : null, cited ? "cited" : null, record ? "dashboard" : null].filter(Boolean);
    return resourceCard(resource, record, used, holders);
  };

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
      const used = [recommended.length ? "recommended" : null, citedSet.has(resource["@id"]) ? "cited" : null, record ? "dashboard" : null].filter(Boolean);
      entries.push({
        kind: "resources",
        anchor: resource.identifier,
        entity: resource,
        name: FG.text(resource.name),
        export: { url: resource.url, text: FG.text(resource.description) },
        checked: resource.statusAsOf ? String(resource.statusAsOf).slice(0, 10) : "",
        text: [FG.bothLanguages(resource.name), FG.bothLanguages(resource.description), resource.alternateName].join(" "),
        stations: [...new Set(stationsOf(recommended).concat(stationsOf(citedBy)))],
        principles: record && record.fer ? FG.refs(record.fer, "about").map(code) : [],
        facets: {
          use: used,
          type: [FG.id(resource.resourceType)],
          status: FG.id(resource.serviceStatus) ? [FG.id(resource.serviceStatus)] : [],
          language: FG.list(resource.inLanguage).map(String),
          lens: FG.refIds(resource, "audience").map((id) => id.replace("#lens-", "")),
        },
        render: () => resourceCard(resource, record, used, recommended.concat(citedBy)),
      });
    }
    for (const source of FG.refs(FG.get("#sources"), "hasPart").filter((entity) => !entity.resourceType)) {
      const citedBy = cited.get(source["@id"]) || [];
      const url = source.url || (String(source["@id"]).startsWith("https://") ? source["@id"] : null);
      entries.push({
        kind: "resources",
        anchor: source.identifier,
        entity: source,
        name: FG.text(source.name),
        export: { url },
        text: [FG.text(source.name), source.creditText, FG.text((FG.get(source.publisher) || {}).name)].join(" "),
        stations: stationsOf(citedBy),
        principles: [],
        facets: { use: ["cited"], type: [FORM_AS_TYPE[sourceForm(source)] || "form:" + sourceForm(source)], status: [], language: FG.list(source.inLanguage).map(String), lens: [] },
        render: () =>
          entryCard({
            id: source.identifier,
            entity: source,
            what: [FG.t("catalogue.sourceType." + sourceForm(source))].concat(uses(["cited"])),
            title: url ? FG.external(url, FG.nameNodes(source)) : FG.nameNodes(source),
            byline: source.creditText || null,
            details: citationDetails(source),
            relations: { inGuide: inGuide(citedBy), identifiers: FG.pidItems(source) },
          }),
      });
    }
    for (const fer of FG.refs(FG.get("#fers"), "hasPart").filter((entity) => !linkedFers.has(entity["@id"]))) {
      entries.push({
        kind: "resources",
        anchor: "fer-" + fer.identifier,
        entity: fer,
        name: FG.text(fer.name),
        export: { url: fer.url, text: FG.text(fer.description) },
        text: [FG.text(fer.name), FG.bothLanguages(fer.description)].join(" "),
        stations: [],
        principles: FG.refs(fer, "about").map(code),
        facets: { use: ["dashboard"], type: ["fer:" + FG.id(fer.catalogueType)], status: [], language: [], lens: [] },
        render: () =>
          entryCard({
            id: "fer-" + fer.identifier,
            entity: fer,
            what: [FG.termName(FG.id(fer.catalogueType))].concat(uses(["dashboard"])),
            title: FG.external(FG.refIds(fer, "sameAs")[0] || fer.url, fer.name),
            body: fer.description ? h("p", null, FG.span(fer.description)) : null,
            states: FG.verificationBadges(fer),
            relations: { principles: tiles(FG.principlesOf(fer)), identifiers: FG.pidItems(fer) },
          }),
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
        entity: repository,
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
        render: () =>
          entryCard({
            id: anchor,
            entity: repository,
            what: FG.id(repository.repositoryKind) ? FG.termName(FG.id(repository.repositoryKind)) : null,
            title: FG.external(repository.url, FG.text(repository.name)),
            details: FG.subjectsOf(repository).join(", "),
            states: FG.statusBadge(repository),
            relations: { basedOn: FG.repositorySourceLinks(repository), identifiers: FG.pidItems(repository) },
          }),
      };
    });
  }

  function clauseEntries(used) {
    return FG.refs(FG.get("#ledger"), "hasPart").map((clause, index) => {
      const holders = used.get(clause["@id"]) || [];
      const status = clause.creativeWorkStatus || "current";
      const audience = FG.id(clause.audience);
      const source = FG.get(clause.isPartOf);
      return {
        kind: "clauses",
        anchor: clause.identifier,
        entity: clause,
        name: clause.identifier,
        export: { text: FG.text(clause.text) },
        text: [clause.identifier, FG.bothLanguages(clause.name), FG.bothLanguages(clause.text)].join(" "),
        stations: stationsOf(holders),
        principles: FG.principlesOf(clause).map((principle) => principle.termCode),
        order: String(index).padStart(4, "0"),
        group: { source: FG.id(clause.isPartOf) },
        facets: { ckind: clause.clauseKind ? [clause.clauseKind] : [], csource: [FG.id(clause.isPartOf)], actor: audience ? [audience] : [], cstatus: [status] },
        render: () =>
          entryCard({
            id: clause.identifier,
            entity: clause,
            class: "clause-card",
            what: clause.clauseKind ? FG.t("catalogue.clauseKind." + clause.clauseKind) : null,
            title: FG.clauseTitle(clause) ? FG.span(FG.clauseTitle(clause)) : null,
            body: [h("p", null, FG.linkedSpan(clause)), FG.guidance(clause)],
            states: FG.clauseStatus(status),
            notes: status !== "current" && clause.note ? h("p", { class: "small clause-note" }, FG.span(clause.note)) : null,
            relations: {
              principles: tiles(FG.principlesOf(clause)),
              audience: audience ? h("span", { class: "audience" }, FG.termName(audience)) : null,
              basedOn: source ? sourceLink(source) : null,
              inGuide: inGuide(holders),
            },
          }),
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
            entity: item,
            name: item.identifier,
            export: { text: FG.text(item.text) },
            text: [item.identifier, FG.bothLanguages(item.text)].join(" "),
            stations: station ? [station] : [],
            principles: FG.principlesOf(item).map((principle) => principle.termCode),
            order: String(checkIndex).padStart(2, "0") + ":" + String(item.position || 0).padStart(4, "0"),
            group: { check: check.identifier },
            facets: { check: [check.identifier], tier: FG.id(item.tier) ? [FG.id(item.tier)] : [] },
            render: () =>
              entryCard({
                id: item.identifier,
                entity: item,
                what: FG.id(item.tier) ? FG.termName(FG.id(item.tier)) : null,
                body: h("p", null, FG.linkedSpan(item)),
                relations: {
                  principles: tiles(FG.principlesOf(item)),
                  basedOn: clauses.map((clause) => FG.idChip("clauses", clause.identifier)),
                  /* A question is asked in its check and listed at the station where it is put right. */
                  inGuide: inGuide([check, FG.get(item.fixAt)]),
                },
              }),
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
        entity: term,
        name: cs.replace(/^[[(]+/, ""),
        export: { name: FG.text(term.name), url: term.url },
        nameEn: en.replace(/^[[(]+/, ""),
        text: cs + " " + en,
        stations: stationsOf(at),
        principles: [],
        facets: {},
        render: () =>
          entryCard({
            id: String(term.termCode),
            entity: term,
            class: "term-card",
            what: FG.t("catalogue.what.term"),
            title: FG.external(term.url, cs),
            titleLang: "cs",
            details: en,
            detailsLang: "en",
            relations: { inGuide: inGuide(at), identifiers: FG.pidItems(term) },
          }),
      };
    });
  }

  function fipEntries() {
    return FG.refs(FG.get("#fips"), "hasPart").map((fip) => {
      const url = FG.refIds(fip, "sameAs")[0] || fip.url;
      return {
        kind: "fips",
        anchor: fip.identifier,
        entity: fip,
        name: FG.text(fip.name),
        export: { url },
        text: [FG.bothLanguages(fip.name), fip.alternateName, FG.bothLanguages(fip.abstract)].join(" "),
        stations: [],
        principles: [...new Set(FG.refs(fip, "hasPart").flatMap((declaration) => FG.principlesOf(declaration).map((principle) => principle.termCode)))],
        facets: {},
        render: () =>
          entryCard({
            id: fip.identifier,
            entity: fip,
            what: FG.t("catalogue.what.fip"),
            title: url ? FG.external(url, FG.text(fip.name)) : FG.span(fip.name),
            details: [
              fip.alternateName,
              fip.version ? FG.t("catalogue.version", { version: fip.version }) : null,
              fip.dateModified ? FG.formatDate(String(fip.dateModified).slice(0, 10)) : null,
              FG.t("catalogue.declarations", { n: FG.refs(fip, "hasPart").length }),
            ],
            body: fip.abstract ? h("p", null, FG.span(fip.abstract)) : null,
            states: FG.verificationBadges(fip),
            relations: { identifiers: FG.pidItems(fip) },
          }),
      };
    });
  }

  /** The questions each FAIR Champion test pre-fills, by test identifier. */
  function testQuestions() {
    const byTest = new Map();
    for (const check of FG.ofType("Quiz")) {
      for (const item of FG.refs(check, "hasPart").sort(FG.byPosition)) {
        for (const entry of FG.refs(item, "additionalProperty").filter((property) => property.propertyID === "prefill:champion")) {
          for (const test of FG.list(entry.value).map(String)) byTest.set(test, (byTest.get(test) || []).concat(item));
        }
      }
    }
    return byTest;
  }

  function testEntries() {
    const questions = testQuestions();
    return FG.graph
      .filter((entity) => String(entity["@id"]).startsWith("#test-"))
      .map((test) => {
        const principle = FG.principles().find((entry) => entry.termCode === code(test.about));
        const health = FG.id(test.healthStatus) || test.healthStatus;
        return {
          kind: "tests",
          anchor: test.identifier,
          entity: test,
          name: FG.text(test.name),
          export: { url: FG.refIds(test, "sameAs")[0] || test.url },
          text: [FG.bothLanguages(test.name), test.identifier].join(" "),
          stations: [],
          principles: principle ? [principle.termCode] : [],
          facets: {},
          render: () =>
            entryCard({
              id: test.identifier,
              entity: test,
              what: FG.t("catalogue.what.test"),
              title: FG.external(test.url, FG.text(test.name)),
              states: health
                ? h("span", { class: "badge", "data-health": String(health) }, FG.t("catalogue.health." + health), test.statusAsOf ? h("span", { class: "muted" }, " · " + FG.t("status.asOf", { date: FG.formatDate(test.statusAsOf) })) : null)
                : null,
              relations: {
                principles: principle ? tiles([principle]) : [],
                inGuide: (questions.get(test.identifier) || []).map((item) => FG.idChip("questions", item.identifier)),
                identifiers: FG.pidItems(test),
              },
            }),
        };
      });
  }

  /** Where each entity a content change can produce sits: its stations and principles, from the advice of each
      station and from the entries of the other kinds. */
  function reachOf(kinds) {
    const reach = new Map();
    const add = (id, stations, principles) => {
      const known = reach.get(id) || { stations: new Set(), principles: new Set() };
      for (const station of stations) known.stations.add(station);
      for (const principle of principles) known.principles.add(principle);
      reach.set(id, known);
    };
    for (const station of FG.stations()) {
      for (const item of FG.refs(station, "itemListElement")) {
        const principles = FG.refs(item, "citation").flatMap((clause) => FG.principlesOf(clause).map((principle) => principle.termCode));
        for (const part of [item].concat(FG.refs(item, "hasPart"))) add(part["@id"], [station.identifier], principles);
      }
    }
    for (const entry of kinds.clauses) add("#clause-" + entry.anchor, entry.stations, entry.principles);
    for (const entry of kinds.questions) add("#item-" + entry.anchor, entry.stations, entry.principles);
    for (const entry of kinds.resources) add("#resource-" + entry.anchor, entry.stations, entry.principles);
    return reach;
  }

  /** A content change: when, what kind, what was done and on what it drew; who and with which tool stays in the
      paradata, so the catalogue repeats no names. */
  function actionEntries(reach) {
    const cited = new Set(FG.refIds(FG.get("#sources"), "hasPart"));
    return FG.graph
      .filter((entity) => String(entity["@id"]).startsWith("#action-"))
      .map((action) => {
        const created = /^Create/.test(String(FG.list(action["@type"])[0]));
        const sources = FG.refs(action, "object").filter((entity) => cited.has(entity["@id"]));
        const id = String(action["@id"]).replace(/^#action-/, "");
        /* A change sits where the items it produced sit. */
        const reached = FG.refIds(action, "result").map((result) => reach.get(result)).filter(Boolean);
        return {
          kind: "actions",
          anchor: id,
          entity: action,
          name: FG.text(action.name),
          export: { text: FG.text(action.description) },
          date: String(action.endTime || ""),
          text: [FG.text(action.name), FG.text(action.description)].join(" "),
          stations: [...new Set(reached.flatMap((place) => [...place.stations]))],
          principles: [...new Set(reached.flatMap((place) => [...place.principles]))],
          facets: { change: [created ? "created" : "updated"] },
          render: () =>
            entryCard({
              id,
              entity: action,
              class: "change",
              what: FG.t(created ? "catalogue.created" : "catalogue.updated"),
              title: FG.text(action.name),
              titleLang: "en",
              details: [FG.formatDate(String(action.endTime || "").slice(0, 10)), FG.t("catalogue.changedItems", { n: FG.refIds(action, "result").length })],
              body: action.description ? h("p", { class: "small", lang: "en" }, FG.text(action.description)) : null,
              relations: { basedOn: sources.map(sourceLink) },
            }),
        };
      });
  }

  function allEntries() {
    const { bySource, byClause } = citations();
    const kinds = {
      resources: resourceEntries(bySource),
      repositories: repositoryEntries(),
      clauses: clauseEntries(byClause),
      questions: questionEntries(),
      terms: termEntries(),
      fips: fipEntries(),
      tests: testEntries(),
    };
    kinds.actions = actionEntries(reachOf(kinds));
    return kinds;
  }

  /* ---------------------------------------------------------------- exports */

  /** One entry as a row of an exported list, in the reader's language. */
  function exportRow(entry) {
    const out = entry.export || {};
    const row = { id: entry.anchor, name: out.name || entry.name, text: out.text || "", url: out.url || "", date: String(entry.date || "").slice(0, 10) };
    for (const facet of KIND_FACETS[entry.kind] || []) row[facet.key] = (entry.facets[facet.key] || []).map(facet.label);
    row.stations = entry.stations.map((id) => FG.text((FG.get("#station-" + id) || {}).name));
    row.principles = entry.principles;
    row.entry = FG.pageAddress() + FG.catalogueHref(entry.kind, entry.anchor);
    const record = FG.recordHref(entry.entity);
    if (record) row.record = FG.siteAddress() + record;
    return row;
  }

  /** The columns of a kind's list: the fields its entries fill, its facets, where the guide uses them, the link. */
  function exportColumns(kind, rows) {
    const facets = (KIND_FACETS[kind] || []).map((facet) => facet.key);
    const filled = ["id", "name", "text", "url", "date"].filter((key) => rows.some((row) => row[key]));
    return filled.concat(facets, ["stations", "principles", "entry"], rows.some((row) => row.record) ? ["record"] : []).map((key) => ({ key, label: facets.includes(key) ? FG.t("catalogue.facet." + key) : FG.t("export.column." + key) }));
  }

  /** The list the catalogue shows, in the order shown and with the filters that made it: as CSV, and as data in the
      shape of the API's lists, each entry with its record at the address the page is served from. */
  function offerListExports(kind, groups) {
    const entries = [...new Set(groups.flatMap((group) => group.entries))];
    const rows = entries.map(exportRow);
    const parts = ["catalogue", kind];
    const columns = exportColumns(kind, rows);
    const site = FG.siteAddress();
    const summary = (entry) => {
      const entity = entry.entity || {};
      const record = FG.recordHref(entity);
      const label = entity.text !== undefined && entity.name === entity.identifier ? "text" : "name";
      return { "@id": record ? site + record : FG.pageAddress() + FG.catalogueHref(entry.kind, entry.anchor), "@type": entity["@type"], identifier: entry.anchor, [label]: FG.languageMap(entity[label]) || entry.name };
    };
    const payload = () => ({
      "@context": site + FG.config.api.files.context,
      "@id": FG.pageAddress() + window.location.hash,
      "@type": "ItemList",
      name: FG.t("app.title") + " · " + FG.t("catalogue.tab." + kind),
      dateCreated: FG.today(),
      version: FG.root.version,
      license: FG.id(FG.root.license),
      isBasedOn: site + "ro-crate-metadata.json",
      numberOfItems: entries.length,
      itemListElement: entries.map(summary),
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

  /** The catalogue showing one kind narrowed to some stations, such as the changes to a station. */
  FG.catalogueFilterHref = (kind, stations) => writeState({ kinds: [kind], stations, principles: [], q: "", order: "", f: {} });

  function writeState(state) {
    const fields = ["k!" + state.kinds.map(encodePart).join("_")];
    if (state.stations.length) fields.push("s!" + state.stations.map(encodePart).join("_"));
    if (state.principles.length) fields.push("p!" + state.principles.map(encodePart).join("_"));
    if (state.q) fields.push("q!" + encodePart(state.q));
    if (state.order) fields.push("o!" + state.order);
    for (const [key, list] of Object.entries(state.f)) fields.push("f." + key + "!" + list.map(encodePart).join("_"));
    return FG.href("catalogue", fields.join("~"));
  }

  /** The values chosen for a facet; the lens facet, like every other, starts with none. */
  const chosenValues = (state, route, key) => state.f[key] || [];

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
    resources: ["name", "type", "status", "checked"],
    repositories: ["guided", "name", "rsource"],
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
    /* A facet's values as groups in their own order (statuses, data sources); entries without a value come last. */
    const byFacet = (key, ranked, emptyLabel) => {
      const facet = (KIND_FACETS[entries.length ? entries[0].kind : ""] || []).find((item) => item.key === key);
      return grouped((entry) => (entry.facets[key] || [])[0] || "", (value) => (value ? facet.label(value) : emptyLabel), rankIn(ranked));
    };
    if (order === "type") {
      /* Types group by their name: a cited document and a resource of the type document read as one group. */
      const facet = KIND_FACETS.resources.find((item) => item.key === "type");
      const labelOf = (entry) => ((entry.facets.type || [])[0] ? facet.label(entry.facets.type[0]) : "");
      const labels = [...new Set(entries.map(labelOf))].sort((a, b) => FG.fold(a).localeCompare(FG.fold(b), "cs"));
      return grouped(labelOf, (label) => label, rankIn(labels));
    }
    if (order === "status") return byFacet("status", FG.refIds(FG.get("#statuses"), "hasDefinedTerm"), FG.t("catalogue.withoutStatus"));
    if (order === "rsource") return byFacet("rsource", ["#repositories-curated", "#snapshot-re3data", "nkr", "fairsharing"], "");
    if (order === "checked") {
      /* The status checked longest ago first, so stale entries surface. */
      return grouped(
        (entry) => entry.checked || "",
        (key) => (key ? FG.t("catalogue.checkedOn", { date: FG.formatDate(key) }) : FG.t("catalogue.notChecked")),
        (key) => (key ? Number(key.replace(/-/g, "")) : Infinity)
      );
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
  function kindPicker(selected, counts, noteOf, onPick, footnote) {
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
      ),
      footnote ? h("p", { class: "facet-note small muted" }, footnote) : null
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
        nkr.status || fairsharing.status ? h("div", { class: "filter-status" }, nkr.status, fairsharing.status) : null,
        nkr.samples ? FG.nkrSamples() : null
      );
    }
    return h(
      "div",
      { class: "kind-intro" },
      h("p", { class: "small" }, intro),
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
    /* A link to one entry shows that entry alone, with the way to the whole kind; an anchor no entry has shows the
       kind with a note. */
    const single = route.extra ? inKinds.filter((entry) => entry.anchor === route.extra) : [];
    const visible = single.length ? single : inKinds.filter((entry) => passesShared(entry, state) && passesKind(entry, state, route));
    /* A shared dimension the chosen kind has no values for shows no facet and no order, unless a filter on it is
       active, so that it can be cleared where it was set. */
    const carries = (dimension) => entries[kind].some((entry) => entry[dimension].length);
    const showStations = carries("stations") || state.stations.length > 0;
    const showPrinciples = carries("principles") || state.principles.length > 0;
    const orders = ordersFor(kind).filter((name) => (name !== "station" || carries("stations")) && (name !== "principle" || carries("principles")));
    const order = orders.includes(state.order) ? state.order : orders[0];

    /* Counts: kinds under every filter; a shared facet under every other filter; a kind's facet within that kind.
       The chosen kind's own filters cannot hold for another kind, so another kind counts none while one is chosen,
       as it does for a station or principle it lacks; choosing it drops them. The lens, kept across kinds, is not one. */
    const ownFilters = (KIND_FACETS[kind] || []).filter((facet) => !facet.passThrough && chosenValues(state, route, facet.key).length);
    const kindCounts = new Map(
      KINDS.map((other) => [other, other !== kind && ownFilters.length ? 0 : entries[other].filter((entry) => passesShared(entry, state) && passesKind(entry, state, route)).length])
    );
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
      if (other !== kind && ownFilters.length) return null;
      if (!count && state.stations.length && lacks(other, "stations")) return FG.t("catalogue.noStation");
      if (!count && state.principles.length && lacks(other, "principles")) return FG.t("catalogue.noPrinciple");
      return null;
    };

    const draft = FG.catalogueDraft;
    const search = h(
      "div",
      { class: "facet-search" },
      h("label", { for: "catalogue-search" }, FG.t("catalogue.search")),
      /* The list follows the trimmed query; the field keeps what was typed, spaces included, and the caret where
         it was, since every change renders the view again. */
      h("input", {
        type: "search",
        id: "catalogue-search",
        value: draft && draft.value.trim() === state.q ? draft.value : state.q,
        "data-caret": draft && draft.value.trim() === state.q ? draft.start + "," + draft.end : null,
        oninput: (event) => {
          clearTimeout(FG.catalogueTyping);
          const input = event.target;
          FG.catalogueTyping = setTimeout(() => {
            FG.catalogueDraft = { value: input.value, start: input.selectionStart, end: input.selectionEnd };
            go(Object.assign({}, state, { q: input.value.trim() }), "#catalogue-search");
          }, 300);
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
      kindPicker(
        kind,
        kindCounts,
        kindNote,
        (other, focus) => go(Object.assign({}, state, { kinds: [other], order: "", f: state.f.lens ? { lens: state.f.lens } : {} }), focus),
        ownFilters.length ? FG.t("catalogue.noKindFilter", { facets: ownFilters.map((facet) => FG.t("catalogue.facet." + facet.key).toLowerCase()).join(", "), kind: FG.t("catalogue.tab." + kind) }) : null
      ),
      showStations
        ? facetGroup("station", FG.t("catalogue.facet.station"), FG.stations().map((station) => station.identifier), state.stations, sharedCounts("stations", "station"), stationLabel, (id, focus) =>
            go(Object.assign({}, state, { stations: toggle(state.stations, id) }), focus)
          )
        : null,
      showPrinciples
        ? facetGroup("principle", FG.t("catalogue.facet.principle"), rankedPrinciples(), state.principles, sharedCounts("principles", "principle"), principleLabel, (value, focus) =>
            go(Object.assign({}, state, { principles: toggle(state.principles, value) }), focus)
          )
        : null,
      selected.map((own) => {
        const ownFacets = KIND_FACETS[own] || [];
        if (!ownFacets.length) return null;
        return h(
          "div",
          { class: "facet-kind" },
          h("p", { class: "facet-kind-name" }, FG.t("catalogue.tab." + own)),
          ownFacets.map((facet) => {
            const counts = kindFacetCounts(own, facet.key);
            /* By number of records, most first; equal counts keep the facet's own order (alphabetical where it has
               none). Kind, station and principle keep the guide's order. */
            const natural = facet.values ? facet.values() : [...counts.keys()].sort((a, b) => FG.fold(facet.label(a)).localeCompare(FG.fold(facet.label(b)), "cs"));
            const values = natural.slice().sort((a, b) => (counts.get(b) || 0) - (counts.get(a) || 0));
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
      const all = expanded.has(group.key) || group.entries.length <= PAGE;
      const cards = (all ? group.entries : group.entries.slice(0, PAGE)).map((entry) => {
        const node = entry.render();
        if (node.id && used.has(node.id)) node.removeAttribute("id");
        else used.add(node.id);
        return node;
      });
      return h(
        "section",
        { class: "catalogue-group" },
        group.label && !single.length ? h("h2", null, group.label, h("span", { class: "muted group-count" }, " · " + FG.t("catalogue.entries", { n: group.entries.length }))) : null,
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
    if (route.extra) {
      const whole = h("a", { href: FG.catalogueHref(kind), class: "single-all" }, FG.t("catalogue.showAll", { kind: FG.t("catalogue.tab." + kind), n: entries[kind].length }));
      const note = h("p", { class: "single-entry small" }, FG.t(single.length ? "catalogue.single" : "catalogue.singleMissing", { id: route.extra }), " ", whole);
      /* One entry keeps only the notice its record needs: the FIP Dashboard disclaimer for a dashboard record. */
      const dashboard = single.length && (kind === "fips" || FG.list(single[0].facets.use).includes("dashboard"));
      results.unshift(note, single.length ? (dashboard ? FG.dashboardNotice() : null) : kindIntro(kind));
    } else results.unshift(kindIntro(kind));

    return h(
      "div",
      { class: "wrap catalogue" },
      FG.heading(1, null, FG.t("catalogue.title")),
      h("p", { class: "lead" }, FG.t("catalogue.intro.all")),
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
