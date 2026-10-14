/* Catalogue helpers every view uses: addresses of catalogue entries and filtered lists, identifiers, source and
   clause links, and the one card every entry is drawn as (station resources use it too). The catalogue view
   itself is assets/js/catalogue-view.js, which the page loads when the catalogue first opens. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);
  /* ---------------------------------------------------------------- shared helpers */

  /** The link to an entity's JSON record in the guide's API; nothing until the API is published. */
  /** The address of the catalogue showing one kind, or one entry of it. */
  FG.catalogueHref = (kind, item) => FG.href("catalogue", kind) + (item ? "/" + encodeURIComponent(item) : "");

  /* A record the guide takes from another registry is identified by that registry's own catalogue entry and the
     registry's identifier for it (re3data.r3d100013576, fip-dashboard.ndi-baseline), so a borrowed identifier always
     says whose it is; a vocabulary's term also says it is a term: t.<keeper>.<ID> (t.ntk.87 for Heslář, which NTK
     keeps). The guide's own entries keep their own identifiers (docs/content-model.md, Identifiers). */
  FG.borrowedId = (registry, id) => registry + "." + id;
  FG.termAnchor = (term) => FG.borrowedId("t.ntk", term.termCode);
  FG.repositoryAnchor = (repository) => {
    if (String(repository["@id"] || "").startsWith("#fer-")) return FG.borrowedId("fip-dashboard", repository.identifier);
    const own = String(repository["@id"] || "").replace(/^#(repository|resource)-/, "");
    if (FG.refIds(repository, "isBasedOn").includes("#snapshot-re3data")) return FG.borrowedId("re3data", own);
    /* A repository only NKR lists keeps NKR's identifier for it. */
    const nkr = FG.refIds(repository, "sameAs").map((iri) => (iri.match(/^https:\/\/repo\.cz\/objects\/(.+)$/) || [])[1]).find(Boolean);
    if (own.startsWith("nkr-") && nkr) return FG.borrowedId("nkr", nkr);
    return own || FG.borrowedId("nkr", slug(FG.text(repository.name)));
  };

  /** The catalogue searched for a query within one kind, as the landing's search links to it. */
  FG.catalogueSearchHref = (query, kind) => writeState({ kinds: [kind || "resources"], stations: [], principles: [], q: query, order: "", f: {} });


  /** An identifier as a small chip that leads to its entry in the catalogue. */
  FG.idChip = function (kind, id) {
    return h("a", { class: "id-chip", href: FG.catalogueHref(kind, id), title: FG.t("catalogue.openEntry", { id }) }, id);
  };

  /** A source's short name: a cited resource's own name, or a source's short name when it has one. */
  FG.shortName = (source) => FG.span(String(source["@id"]).startsWith("#resource-") ? source.name : source.alternateName || source.name);

  /** A source's short name as plain text, for lists and filters. */
  FG.shortText = (source) => FG.text(String(source["@id"]).startsWith("#resource-") ? source.name : source.alternateName || source.name);

  /** A category's name as the catalogue lists categories: in lower case, unless it starts with an acronym. */
  FG.category = (name) => {
    const text = String(name || "");
    return /^\p{Lu}{2,}/u.test(text) ? text : text.charAt(0).toLocaleLowerCase(FG.state.lang) + text.slice(1);
  };

  /** A work an entry rests on, by its short name, leading to its own entry in the catalogue. */
  FG.sourceLink = (source) => h("a", { class: "source-link", href: FG.catalogueHref("resources", source.identifier) }, FG.shortName(source));

  /** Warn when a published statement has been superseded. Refresh is an editorial status. */
  FG.clauseStatus = (status) =>
    status === "superseded" ? h("span", { class: "badge", "data-clause-status": status }, FG.t("explorer.superseded")) : null;

  /** A requirement's guidance, as its source publishes it, behind a disclosure. */
  FG.guidance = function (clause) {
    if (!clause.guidance) return null;
    const literal = FG.list(clause.guidance).find((value) => value && value["@language"]);
    const source = FG.get(clause.isPartOf);
    const language = (literal && literal["@language"]) || clause.guidanceLanguage || "en";
    return h("details", { class: "clause-guidance" }, h("summary", null, FG.t("catalogue.guidance")),
      h("div", { class: "content", lang: language },
        source ? [h("p", { class: "small muted", lang: FG.state.lang }, FG.sourceLink(source), source.version && !FG.text(source.name).endsWith(" " + source.version) ? " · " + source.version : null),
          source.creditText ? h("p", { class: "small muted", lang: FG.state.lang }, source.creditText) : null,
          source.license ? h("p", { class: "small muted", lang: FG.state.lang }, FG.external(FG.id(source.license) || source.license, FG.t("catalogue.originalLicense"))) : null] : null,
        FG.paragraphs(clause.guidance)));
  };

  /** A requirement's title, when it has one besides its identifier. */
  FG.clauseTitle = (clause) => (clause.name && FG.text(clause.name) !== clause.identifier ? clause.name : null);

  /** A compact catalogue entry, reused in principles, path reasons and question sources. */
  FG.clauseEntry = function (clause) {
    const source = FG.get(clause.isPartOf);
    const status = clause.creativeWorkStatus;
    const isClause = String(clause["@id"]).startsWith("#clause-");
    const title = FG.clauseTitle(clause);
    return h(
      "li",
      { class: "clause" },
      h(
        "p",
        { class: "entry-head clause-meta" },
        isClause ? FG.idChip("clauses", clause.identifier) : null,
        clause.clauseKind ? h("span", { class: "entry-what" }, FG.t("catalogue.clauseKind." + clause.clauseKind)) : null,
        FG.clauseStatus(status)
      ),
      title && clause.text ? h("p", { class: "entry-title clause-title" }, h("strong", null, FG.span(title))) : null,
      h("p", { class: "clause-text" }, FG.linkedSpan(clause, clause.text ? "text" : "name")),
      status && status !== "current" && clause.note ? h("p", { class: "small clause-note" }, FG.span(clause.note)) : null,
      source ? h("p", { class: "clause-source small" }, h("span", { class: "entry-what" }, FG.t("catalogue.relation.basedOn") + ": "), FG.sourceLink(source)) : null,
      FG.guidance(clause)
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

  /* The relations a card may show, in this order, each under one label and icon wherever it appears. */
  const RELATIONS = ["principles", "audience", "operatedBy", "developedBy", "operates", "nationalNodeOf", "memberOf", "fips", "basedOn", "inGuide", "identifiers"];
  /* The resource types that are tools or services, whose entries carry a service badge. */
  const SERVICE_TYPES = ["#rtype-service", "#rtype-tool", "#rtype-registry"];

  /** The mark of an entry's kind: the kind's icon on the kind's colour, named for screen readers. */
  /** A service's badge, when the entity is a tool or a service. */
  const serviceOf = (entity) => (SERVICE_TYPES.includes(typeOf(entity)) ? entity : null);

  /** An entry as a card, the same for every kind: its own identifier with what it is and how the guide uses it;
      its title; one quiet line of details; its text; badges for its state only; then its relations, one row each,
      in a fixed order, each drawn one way everywhere. */
  function entryCard(spec) {
    const kind = spec.kind || null;
    const what = FG.list(spec.what).filter(Boolean);
    const details = FG.list(spec.details).filter(Boolean);
    const states = [spec.states].flat(Infinity).filter(Boolean);
    const rows = spec.compact ? [] : RELATIONS.map((key) => [key, [spec.relations && spec.relations[key]].flat(Infinity).filter(Boolean)]).filter(([, items]) => items.length);
    return h(
      "li",
      { class: ["card", "entry-card", kind ? "kind-" + kind : null, spec.compact ? "entry-compact" : null].concat(spec.class || []).filter(Boolean).join(" "), id: "item-" + spec.id, "data-kind": kind, tabindex: "-1" },
      /* The kind shows in the card's top strip and the kind facet, and its icon stands before the title wherever the
         entry has no favicon of its own (D-185). */
      h("p", { class: "entry-head" }, spec.compact ? null : h("span", { class: "id-chip id-chip-static" }, spec.id), what.length ? h("span", { class: "entry-what" }, what.join(" · ")) : null, spec.compact ? null : FG.apiLink(spec.entity)),
      spec.title
        ? h("h3", { class: "entry-title", lang: spec.titleLang || null }, spec.service ? FG.serviceBadge(spec.service.identifier, spec.service.url, kind || "resources") : kind ? FG.kindBadge(kind) : null, h("span", null, spec.title))
        : null,
      spec.byline ? h("p", { class: "small entry-byline" }, spec.byline) : null,
      details.length ? h("p", { class: "small muted card-details", lang: spec.detailsLang || null }, details.join(" · ")) : null,
      spec.body,
      states.length ? h("div", { class: "badges" }, states) : null,
      spec.notes,
      spec.compact ? h("p", { class: "small entry-more" }, h("a", { href: FG.catalogueHref(kind, spec.id) }, FG.t("catalogue.whole.entry"))) : null,
      !spec.compact && (rows.length || FG.modelRows(spec.entity).length)
        ? h(
            "dl",
            { class: "relations" },
            rows.map(([key, items]) => [FG.relationTerm(key), h("dd", { class: key === "identifiers" ? "pid-line" : null }, items)]),
            FG.modelRows(spec.entity)
          )
        : null
    );
  }

  const tiles = (principles) => principles.map((principle) => FG.principleTile(principle));

  /** A link to an entry's own place in the catalogue: a repository under its anchor, an infrastructure or a resource
      under its identifier. */
  const entryLink = (entity) => {
    if (!entity) return null;
    const id = String(entity["@id"]);
    const name = entity.abbreviation ? FG.abbreviatedName(entity, FG.state.lang) : FG.text(entity.name);
    if (id.startsWith("#infrastructure-")) return h("a", { href: FG.catalogueHref("infrastructures", entity.identifier) }, name);
    if (entity["@type"] === "DataCatalog" || id.startsWith("#repository-")) return h("a", { href: FG.catalogueHref("repositories", FG.repositoryAnchor(entity)) }, name);
    return h("a", { href: FG.catalogueHref("resources", entity.identifier) }, name);
  };

  /** Who operates an entry, as its sources state it: the operator its own page names and the large research
      infrastructure that operates it, each with the source that says so (D-172, D-174). */
  const operatorRow = (entity) => [
    entity.operatorName ? h("span", null, FG.text(entity.operatorName), entity.operatorSource ? [" (", FG.external(entity.operatorSource, FG.t("infrastructure.operatorSource")), ")"] : null) : null,
    FG.get(FG.id(entity.operatedBy))
      ? h("span", null, entryLink(FG.get(FG.id(entity.operatedBy))), entity.operatedBySource ? [" (", FG.external(entity.operatedBySource, FG.t("infrastructure.operatorSource")), ")"] : null)
      : null,
  ].filter(Boolean);

  /** Who developed an entry, where its sources name its developers rather than an operator (D-174). */
  const developerRow = (entity) =>
    entity.developerName ? [h("span", null, FG.text(entity.developerName), entity.developerSource ? [" (", FG.external(entity.developerSource, FG.t("infrastructure.operatorSource")), ")"] : null)] : [];
  /** The audiences an entry is for, by icon and name. */
  const audiences = (lensIds) =>
    lensIds
      .map(FG.get)
      .filter(Boolean)
      .map((lens) => h("span", { class: "audience" }, FG.icon((icons().lens || {})[lens.audienceType]), FG.text(lens.name)));
  const sourceLink = (source) => FG.sourceLink(source);

  /* ---------------------------------------------------------------- entries of each kind */

  /* Resources, cited sources and FIP Dashboard records share the guide's resource types: a source's or a record's
     type comes from the crosswalk in the content. */
  const typeOf = (entity) => FG.id(entity.resourceType || entity.guideType) || null;

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
      entity.preparationStatus === "in-preparation" ? FG.t("model.inPreparation") : null,
      date,
    ];
  }

  const uses = (list) => list.map((use) => FG.t("catalogue.use." + use));

  function resourceCard(resource, record, used, holders, compact) {
    return entryCard({
      kind: "resources",
      compact,
      id: resource.identifier,
      entity: resource,
      service: serviceOf(resource),
      what: [FG.termName(FG.id(resource.resourceType))].concat(uses(used)),
      title: FG.external(resource.url, FG.nameNodes(resource)),
      details: citationDetails(resource),
      body: resource.description ? h("p", null, FG.span(resource.description)) : null,
      states: [FG.statusBadge(resource), FG.nodeBadge(resource), record ? FG.verificationBadges(record.fer) : null],
      relations: {
        principles: record && record.fer ? tiles(FG.principlesOf(record.fer)) : [],
        audience: audiences(FG.refIds(resource, "audience")),
        operatedBy: operatorRow(resource),
        basedOn: [
          resource.rdmkitRecord ? FG.external(resource.rdmkitRecord, "RDMkit") : null,
          resource.trainingSearch ? FG.external(resource.trainingSearch, FG.t("catalogue.trainingSearch")) : null,
        ],
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
  /** A resource's card wherever the guide shows it; at a station, without that station among where it is used, and
      compact: what it is, its name, its text and its state, with the way to its whole entry in the catalogue. */
  FG.resourceCard = function (resource, except, compact) {
    const record = FG.dashboardRecord(resource);
    const recommended = FG.stations().filter((station) => FG.refIds(station, "mentions").includes(resource["@id"]));
    const holders = recommended.concat(citedSources().get(resource["@id"]) || []).filter((holder) => holder.identifier !== except);
    const cited = FG.refIds(FG.get("#sources"), "hasPart").includes(resource["@id"]);
    const used = [recommended.length ? "recommended" : null, cited ? "cited" : null, record ? "dashboard" : null].filter(Boolean);
    return resourceCard(resource, record, used, holders, compact);
  };


  const encodePart = (value) => encodeURIComponent(value).replace(/[~!_]/g, (char) => "%" + char.charCodeAt(0).toString(16).toUpperCase());

  /** The catalogue showing one kind narrowed to some stations, such as the changes to a station. */
  FG.catalogueFilterHref = (kind, stations) => writeState({ kinds: [kind], stations, principles: [], q: "", order: "", f: {} });
  FG.repositoryFinderHref = () => writeState({ kinds: ["repositories"], stations: [], principles: [], q: "", order: "", f: { rfunction: ["#rfunction-deposit-data"] } });
  FG.modelFilterHref = (kind, term) => writeState({ kinds: [kind], stations: [], principles: [], layers: term.modelKind === "layer" ? [term["@id"]] : [], seams: term.modelKind === "seam" ? [term["@id"]] : [], q: "", order: "", f: {} });

  /* A topic named in content (`#resources?type=standard,vocabulary`, `#resources?station=assessment`): the content's
     facet name and the prefix its values take as entities; `station` narrows the shared station dimension. The
     content check accepts the same facets and values. */
  const TOPIC_FACETS = { resources: { type: ["type", "#rtype-"] }, repositories: { function: ["rfunction", "#rfunction-"] } };

  /** The catalogue state for a kind narrowed to a topic, for the reader's lens. */
  FG.catalogueTopic = function (kind, query) {
    const f = {};
    let stations = [];
    for (const part of query.split("&")) {
      const [name, values = ""] = part.split("=");
      const list = values.split(",").filter(Boolean);
      const facet = (TOPIC_FACETS[kind] || {})[name];
      if (name === "station") stations = list;
      else if (facet) f[facet[0]] = list.map((value) => facet[1] + value);
    }
    f.lens = [FG.state.lens];
    return stateArg({ kinds: [kind], stations, principles: [], q: "", order: "", f });
  };

  function writeState(state) {
    return FG.href("catalogue", stateArg(state));
  }

  function stateArg(state) {
    const fields = ["k!" + state.kinds.map(encodePart).join("_")];
    if (state.stations.length) fields.push("s!" + state.stations.map(encodePart).join("_"));
    if (state.principles.length) fields.push("p!" + state.principles.map(encodePart).join("_"));
    if (state.layers?.length) fields.push("l!" + state.layers.map(encodePart).join("_"));
    if (state.seams?.length) fields.push("n!" + state.seams.map(encodePart).join("_"));
    if (state.q) fields.push("q!" + encodePart(state.q));
    if (state.order) fields.push("o!" + state.order);
    for (const [key, list] of Object.entries(state.f)) fields.push("f." + key + "!" + list.map(encodePart).join("_"));
    return fields.join("~");
  }


  /* What the catalogue view builds on, for assets/js/catalogue-view.js. */
  FG.catalogueParts = { audiences, citationDetails, citations, code, developerRow, entryCard, entryLink, icons, inGuide, operatorRow, resourceCard, serviceOf, slug, sourceLink, stationsOf, tiles, typeOf, uses, writeState };
})();
