/* Catalogue helpers every view uses: addresses of catalogue entries and filtered lists, identifiers, source and
   clause links, and the one card every entry is drawn as (station resources use it too). The catalogue view
   itself is assets/js/catalogue-view.js, which the page loads when the catalogue first opens. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);
  /* ---------------------------------------------------------------- shared helpers */

  /** Compact route codes are emitted from the build vocabulary; UI category names remain readable. */
  FG.catalogueKind = (code) => FG.config.catalogueKinds[code] || code;
  FG.catalogueCode = (kind) => Object.keys(FG.config.catalogueKinds).find((code) => FG.config.catalogueKinds[code] === kind) || kind;
  FG.catalogueHref = (kind, item) => FG.href("catalogue") + "/" + [FG.catalogueCode(kind), ...(item ? item.split("/") : [])].map(encodeURIComponent).join("/");
  FG.entryHref = (entity) => {
    const address = FG.config.api.records[FG.id(entity)];
    return address ? FG.href("catalogue") + "/" + address.split("/").map(encodeURIComponent).join("/") : null;
  };
  FG.termAnchor = (term) => FG.config.api.records[FG.id(term)]?.split("/").slice(1).join("/");
  FG.repositoryAnchor = (repository) => FG.config.api.records[FG.id(repository)]?.split("/").slice(1).join("/");

  /** The catalogue searched for a query within one kind, as the landing's search links to it. */
  FG.catalogueSearchHref = (query, kind) => writeState({ kinds: [kind || "resources"], stations: [], principles: [], q: query, order: "", f: {} });


  /** An identifier as a small chip that leads to its entry in the catalogue. */
  FG.idChip = function (entity) {
    const address = FG.config.api.records[FG.id(entity)];
    const id = address?.split("/").at(-1) || entity?.identifier || "";
    return h(address ? "a" : "span", { class: "id-chip", href: address ? FG.entryHref(entity) : null,
      title: address ? FG.t("catalogue.openEntry", { id: address }) : null }, id);
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
  FG.sourceLink = (source) => h("a", { class: "source-link", href: FG.entryHref(source) }, FG.shortName(source));

  /** What the EOSC CZ Node is, as the About page states it: the node's own state since its date, with the source
      that states it (D-172). */
  FG.nodeNote = function () {
    const node = FG.get("#eosc-cz-node");
    if (!node || !node.nodeStateSince) return null;
    const sources = FG.refs(node, "isBasedOn");
    const source = sources[1] || sources[0];
    return h("p", { class: "small" }, FG.t("node." + node.nodeState, { date: FG.formatDate(node.nodeStateSince) }), source ? [" ", FG.sourceLink(source)] : null);
  };

  /** Warn when a published statement has been superseded. Refresh is an editorial status. */
  FG.clauseStatus = (status) =>
    status === "superseded" ? h("span", { class: "badge", "data-clause-status": status }, FG.t("explorer.superseded")) : null;

  /** A requirement's guidance, as its source publishes it, behind a disclosure. */
  FG.guidance = function (clause) {
    if (!clause.guidance) return null;
    const literal = FG.list(clause.guidance).find((value) => value && value["@language"]);
    const source = FG.get(clause.isPartOf);
    const language = (literal && literal["@language"]) || clause.guidanceLanguage || "en";
    return h("details", { class: "clause-guidance", "data-field": "guidance" }, h("summary", null, FG.t("catalogue.guidance")),
      h("div", { class: "content", lang: language },
        source ? [h("p", { class: "small muted", lang: FG.state.lang }, FG.sourceLink(source), source.version && !FG.text(source.name).endsWith(" " + source.version) ? " · " + source.version : null),
          source.creditText ? h("p", { class: "small muted", lang: FG.state.lang }, source.creditText) : null,
          /* The quoted guidance is under its source's licence, named from the data beside the quote (design D8). */
          source.license ? h("div", { lang: FG.state.lang }, FG.quoteLicence(source.license)) : null] : null,
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
        isClause ? FG.idChip(clause) : null,
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

  const code = (entity) => String((FG.get(entity) || entity || {}).termCode || "");
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

  /* The relations a card may show, in this order, each under one label and icon wherever it appears: what the entry
     is about and for, how it is used, who made, runs or provides it, its licence, what it rests on and replaces, and
     where it is used and changed. */
  const RELATIONS = ["principles", "audience", "fixedBy", "applies", "group", "nrpProfile", "prefilledFrom", "prefills", "covers", "correspondsTo", "declarations", "declaredIn", "madeBy", "tools", "operatedBy", "developedBy", "providedBy", "operates", "nationalNodeOf", "memberOf", "fips", "license", "basedOn", "replacedBy", "replaces", "consulted", "changed", "mentions", "inGuide", "identifiers"];
  /* The record fields each row draws, unless a card names its own: the catalogue's completeness test reads them from
     the row's `data-field` (design D8). */
  const ROW_FIELDS = {
    principles: "about",
    audience: "audience",
    fixedBy: "fixedBy",
    applies: "appliesTo allowsNotApplicable",
    group: "block",
    nrpProfile: "providedByNrpFor",
    prefilledFrom: "additionalProperty prefillLevel championEvidenceOnly",
    covers: "hasPart",
    declarations: "hasPart",
    madeBy: "agent",
    tools: "instrument",
    operatedBy: "publisher operatedBy operatorSource operatedBySource",
    developedBy: "attributedTo developerSource",
    providedBy: "provider",
    operates: "operates",
    nationalNodeOf: "nationalNodeOf",
    memberOf: "memberOf",
    fips: "subjectOf",
    license: "license",
    basedOn: "isBasedOn",
    replacedBy: "supersededBy",
    consulted: "object",
    changed: "result",
    mentions: "mentions",
    identifiers: "sameAs",
  };

  /** The labels of a card's rows in their fixed order, model rows last, as the page tests compare them. */
  FG.catalogueRowOrder = () => RELATIONS.concat(["implementationLayers", "implementationSeams"]).map((key) => FG.t("catalogue.relation." + key));

  /** A part of a card that draws record fields, marked with their names for the completeness test. */
  const field = (names, node) => (node ? h("span", { "data-field": names }, node) : null);

  /* ---------------------------------------------------------------- shared conventions (design D8) */

  /** A licence named from the data: an SPDX record by its identifier, a Creative Commons or GNU licence by its code
      and version from its address, and any other licence by its address. */
  FG.licenceName = function (value) {
    const id = FG.id(value) || String(value || "");
    const entity = FG.get(id);
    if (entity && entity.identifier) return /^CC/.test(entity.identifier) ? String(entity.identifier).replace(/-/g, " ") : String(entity.identifier);
    let url;
    try {
      url = new URL(id);
    } catch (error) {
      return id;
    }
    const parts = url.pathname.split("/").filter(Boolean);
    const host = url.hostname.replace(/^www\./, "");
    if (host === "creativecommons.org" && parts[0] === "licenses") return ["CC", String(parts[1] || "").toUpperCase(), parts[2]].filter(Boolean).join(" ");
    if (host === "creativecommons.org" && parts[0] === "publicdomain") return [parts[1] === "zero" ? "CC0" : "Public Domain Mark", parts[2]].filter(Boolean).join(" ");
    const gnu = host === "gnu.org" && String(parts.at(-1) || "").match(/^(a|l)?gpl-([\d.]+?)(?:\.html|-only|-or-later)?$/i);
    if (gnu) return "GNU " + (gnu[1] || "").toUpperCase() + "GPL " + gnu[2];
    if (host === "spdx.org" || host === "opensource.org") return parts.at(-1);
    return host + url.pathname.replace(/\/$/, "");
  };

  /** A licence as a link to its text, named from the data. */
  FG.licenceLink = (value) => FG.external(FG.id(value) || String(value), FG.licenceName(value));

  /** The licence of a quoted text, as one quiet line beside the quote; `names` are the record fields it draws. */
  FG.quoteLicence = (value, names) =>
    value ? h("p", { class: "small muted quote-licence", "data-field": names || null }, FG.t("catalogue.quoteLicence") + ": ", FG.list(value).map((item, index) => [index ? ", " : null, FG.licenceLink(item)])) : null;

  /* Relations read from their other end, worked out once for the knowledge base as loaded (design D8): the changes
     that produced or altered each record, the questions each test or criterion pre-fills, the FIP declarations that
     name each enabling resource, the requirements each one replaces, and the station or page of every part of the
     Guide that has no catalogue entry of its own. */
  let reverseCache = null;
  FG.reverseRelations = function () {
    if (reverseCache && reverseCache.revision === FG.dataRevision && reverseCache.graph === FG.graph && reverseCache.size === FG.graph.length) return reverseCache;
    const add = (map, key, value) => map.set(key, (map.get(key) || []).concat(value));
    const changes = new Map();
    for (const action of FG.graph.filter((entity) => String(entity["@id"]).startsWith("#action-")).sort((a, b) => String(b.endTime || "").localeCompare(String(a.endTime || "")))) {
      for (const id of FG.refIds(action, "result")) add(changes, id, action);
    }
    const prefills = new Map();
    for (const check of FG.ofType("Quiz")) {
      for (const item of FG.refs(check, "hasPart").sort(FG.byPosition)) {
        for (const entry of FG.refs(item, "additionalProperty").filter((property) => property.propertyID === "prefill:champion")) {
          for (const test of FG.list(entry.value).map(String)) add(prefills, "champion:" + test, { item });
        }
      }
    }
    /* The Guide's own tests and the external evaluators' criteria, read from the question's end. */
    const prefilledBy = new Map();
    for (const test of FG.graph.filter((entity) => String(entity["@id"]).startsWith("#test-") && entity.isImplementationOf)) {
      add(prefills, test["@id"], { item: FG.get(test.isImplementationOf) });
      add(prefilledBy, FG.id(test.isImplementationOf), { entity: test });
    }
    for (const criterion of FG.graph.filter((entity) => String(entity["@id"]).startsWith("#criterion-") && entity.hasPart)) {
      for (const mapping of FG.refs(criterion, "hasPart")) {
        if (!FG.get(mapping.about)) continue;
        add(prefills, criterion["@id"], { item: FG.get(mapping.about), coverage: mapping.mappingCoverage, note: mapping.description });
        add(prefilledBy, FG.id(mapping.about), { entity: criterion, coverage: mapping.mappingCoverage });
      }
    }
    const declaredIn = new Map();
    for (const fip of FG.refs(FG.get("#fips"), "hasPart")) for (const declaration of FG.refs(fip, "hasPart")) for (const id of FG.refIds(declaration, "mentions")) add(declaredIn, id, { fip, declaration });
    /* An enabling resource the Guide also lists as a resource or repository has that entry, not one of its own. */
    const standsFor = new Map();
    for (const entity of FG.graph.filter((item) => FG.config.api.records[item["@id"]] && FG.refIds(item, "sameAs").length)) {
      const record = FG.dashboardRecord(entity);
      if (record && record.fer && !standsFor.has(record.fer["@id"])) standsFor.set(record.fer["@id"], entity);
    }
    const replaces = new Map();
    for (const clause of FG.refs(FG.get("#ledger"), "hasPart")) for (const id of FG.refIds(clause, "supersededBy")) add(replaces, id, clause);
    const places = new Map();
    const placeAll = (place, refs) => {
      for (const ref of refs) {
        if (places.has(ref["@id"])) continue;
        places.set(ref["@id"], place);
        placeAll(place, FG.refs(ref, "hasPart"));
      }
    };
    for (const station of FG.stations()) placeAll({ view: "path", arg: station.identifier, entity: station }, FG.refs(station, "itemListElement").concat(FG.refs(station, "hasPart")));
    for (const entity of FG.graph.filter((item) => FG.id(item.isPartOf) && !places.has(item["@id"]))) {
      let parent = FG.get(FG.id(entity.isPartOf));
      for (let depth = 0; parent && depth < 4; depth += 1) {
        const id = String(parent["@id"]);
        if (id.startsWith("#station-")) {
          places.set(entity["@id"], { view: "path", arg: parent.identifier, entity: parent });
          break;
        }
        if (id.startsWith("#page-") && !FG.id(parent.isPartOf)) {
          places.set(entity["@id"], { view: "page", arg: parent.identifier, entity: parent });
          break;
        }
        if (places.has(id)) {
          places.set(entity["@id"], places.get(id));
          break;
        }
        parent = FG.get(FG.id(parent.isPartOf));
      }
    }
    reverseCache = { revision: FG.dataRevision, graph: FG.graph, size: FG.graph.length, changes, prefills, prefilledBy, declaredIn, standsFor, replaces, places };
    return reverseCache;
  };

  /** A record as a link: to its catalogue entry, or for a part of the Guide without one, to its station or page. */
  FG.recordLink = function (entity) {
    if (!entity) return null;
    const standing = FG.reverseRelations().standsFor.get(entity["@id"]);
    if (!FG.entryHref(entity) && standing) return FG.recordLink(standing);
    const href = FG.entryHref(entity);
    const isRequirement = String(entity["@id"]).startsWith("#clause-") || String(entity["@id"]).startsWith("#item-");
    const label = isRequirement || !entity.name ? entity.identifier || FG.text(entity.name) || String(entity["@id"]) : FG.nameText(entity);
    if (href) return h("a", { href }, label);
    if (entity["@id"] === "./") return h("a", { href: FG.href("page", "about") }, FG.text(entity.name));
    const place = FG.reverseRelations().places.get(entity["@id"]);
    if (place) return h("span", null, entity.identifier || FG.text(entity.name), " · ", h("a", { href: FG.href(place.view, place.arg) }, FG.span(place.entity.name || place.entity.headline)));
    return h("span", null, entity.identifier || FG.text(entity.name) || String(entity["@id"]));
  };

  /** What kind of record something is, for grouping a change's records: its catalogue kind, or the part of the Guide
      it belongs to. */
  FG.recordGroup = function (entity) {
    const address = FG.config.api.records[FG.id(entity)];
    if (address) return FG.catalogueKind(address.split("/")[0]);
    const id = String(entity["@id"]);
    if (id === "./") return "guide";
    return ["advice", "callout", "page", "model-context"].find((prefix) => id.startsWith("#" + prefix + "-")) || "other";
  };

  /** A list of records grouped as FG.recordGroup groups them, in the catalogue's order of kinds. */
  FG.recordGroups = function (records) {
    const order = Object.values(FG.config.catalogueKinds).concat(["advice", "callout", "model-context", "page", "guide", "other"]);
    const groups = new Map();
    for (const record of records.filter(Boolean)) groups.set(FG.recordGroup(record), (groups.get(FG.recordGroup(record)) || []).concat(record));
    return [...groups.entries()]
      .sort(([a], [b]) => order.indexOf(a) - order.indexOf(b))
      .map(([group, items]) => {
        /* A catalogue kind is named as its tab names it; the other parts of the Guide by their own group name. */
        const tab = FG.t("catalogue.tab." + group);
        return { label: tab !== "catalogue.tab." + group ? tab : FG.t("catalogue.recordGroup." + group), items, render: FG.recordLink };
      });
  };

  /** The catalogue's content changes narrowed to those that produced or altered a record. */
  FG.changesHref = (entity) => writeState({ kinds: ["actions"], stations: [], principles: [], q: "", order: "", f: { record: [FG.id(entity)] } });

  /** An entry's links in its top corner: the changes that produced or altered it, as a count that leads to them in
      the catalogue, and its record as data. A record's changes stay in the catalogue's list of changes, so no entry
      grows with each one (design D8). */
  const entryLinks = (entity) => {
    const count = (FG.reverseRelations().changes.get(FG.id(entity)) || []).length;
    const changes = count
      ? h("a", { class: "changes-link", href: FG.changesHref(entity), title: FG.t("catalogue.changesOf", { n: count }), "aria-label": FG.t("catalogue.changesOf", { n: count }) }, FG.icon("changes"), h("span", { "aria-hidden": "true" }, String(count)))
      : null;
    const record = FG.apiLink(entity);
    return changes || record ? h("span", { class: "entry-links" }, changes, record) : null;
  };

  /** Every identifier an entry is recorded with: its persistent identifiers by scheme, then any other address it is
      the same as (its FIP Dashboard record among them), each once. */
  FG.identifierItems = function (entity) {
    const pids = FG.pids(entity);
    const shown = new Set(pids.map((pid) => pid.iri));
    const others = FG.refIds(entity, "sameAs")
      .filter((iri) => /^https:\/\//.test(iri) && !shown.has(iri) && !/^https:\/\/(dx\.)?doi\.org\/10\.17616\//i.test(iri))
      .map((iri) => FG.pidItem(iri.startsWith(FG.DASHBOARD) ? "dashboard" : "address", iri));
    return pids.map((pid) => FG.pidItem(pid.scheme, pid.iri)).concat(others);
  };

  /* A FIP declaration's status by its icon, beside its text. */
  const DECLARATION_ICON = { "in-use": "●", planned: "○", "under-consideration": "◌", "to-be-replaced": "◔" };
  FG.declarationBadge = (status) => FG.stateBadge({ icon: DECLARATION_ICON[status], text: FG.t("catalogue.declarationStatus." + status), attrs: { "data-declaration": status } });

  /** The FIP profiles that declare an enabling resource, each with the principles and the status it is declared for. */
  const declaredInRow = (fer) => {
    const list = (fer && FG.reverseRelations().declaredIn.get(fer["@id"])) || [];
    return list.length
      ? FG.relationGroups([{ items: list, render: ({ fip, declaration }) => [
          h("a", { href: FG.entryHref(fip) }, FG.text(fip.alternateName) || FG.text(fip.name)),
          h("span", { class: "muted" }, " · " + FG.principlesOf(declaration).map((principle) => principle.termCode).join(", ") + " "),
          FG.declarationBadge(declaration.creativeWorkStatus),
        ] }])
      : [];
  };

  /** A snapshot an entry's facts come from, by name with the date it was taken. */
  const snapshotItem = (snapshot) =>
    h("span", null, snapshot.url ? FG.external(snapshot.url, FG.repositorySource(snapshot["@id"])) : FG.repositorySource(snapshot["@id"]), snapshot.dateCreated ? h("span", { class: "muted" }, " · " + FG.t("catalogue.snapshotOf", { date: FG.formatDate(snapshot.dateCreated) })) : null);

  /* Rows that take the card's full width under their label: a table needs more than the row's column. */
  const WIDE_ROWS = ["declarations"];

  /* A group longer than this folds behind its count and is built when a reader first opens it. */
  const FOLD_AFTER = 8;

  /** A relation's items in groups by kind, as one row: each group named with its count, folded when long and built
      only when first opened, so a long list costs nothing until it is asked for. `groups` are { label, items,
      render, fold }; a single group without a label lists its items directly, and `fold: false` keeps a short
      list open however long it is. */
  FG.relationGroups = function (groups) {
    const shown = groups.filter((group) => group.items.length);
    const list = (group) => h("ul", { class: "relation-list" }, group.items.map((item) => h("li", null, group.render(item))));
    return shown.map((group) => {
      const label = group.label ? group.label + " (" + FG.formatNumber(group.items.length) + ")" : null;
      if (group.items.length <= FOLD_AFTER || group.fold === false) return h("div", { class: "relation-group" }, label ? h("p", { class: "relation-group-label" }, label) : null, list(group));
      let built = false;
      return h(
        "details",
        { class: "relation-group relation-fold", ontoggle: (event) => {
          if (!event.target.open || built) return;
          built = true;
          event.target.append(list(group));
        } },
        h("summary", null, label || FG.t("catalogue.itemCount", { n: group.items.length }))
      );
    });
  };
  /* The resource types that are tools or services, whose entries carry a service badge. */
  const SERVICE_TYPES = ["#rtype-service", "#rtype-tool", "#rtype-registry"];

  /** A service's badge, when the entity is a tool or a service. */
  const serviceOf = (entity) => (SERVICE_TYPES.includes(typeOf(entity)) ? entity : null);

  /** An entry as a card, the same for every kind: its own identifier with what it is and how the guide uses it;
      its title; one quiet line of details; its text; badges for its state only; then its relations, one row each,
      in a fixed order, each drawn one way everywhere. */
  function entryCard(spec) {
    const address = FG.config.api.records[FG.id(spec.entity)];
    if (address) spec = { ...spec, kind: FG.catalogueKind(address.split("/")[0]), id: address.split("/").slice(1).join("/") };
    const kind = spec.kind || null;
    const what = FG.list(spec.what).filter(Boolean);
    const details = FG.list(spec.details).filter(Boolean);
    const states = [spec.states].flat(Infinity).filter(Boolean);
    const relations = spec.relations || {};
    const rows = spec.compact ? [] : RELATIONS.map((key) => [key, [relations[key]].flat(Infinity).filter(Boolean)]).filter(([, items]) => items.length);
    const rowFields = (key) => (spec.fields && key in spec.fields ? spec.fields[key] : ROW_FIELDS[key]) || null;
    return h(
      "li",
      { class: ["card", "entry-card", kind ? "kind-" + kind : null, spec.compact ? "entry-compact" : null].concat(spec.class || []).filter(Boolean).join(" "), id: "item-" + spec.id, "data-kind": kind, tabindex: "-1" },
      /* The kind shows in the card's top strip and the kind facet, and its icon stands before the title wherever the
         entry has no favicon of its own (D-185). */
      h("p", { class: "entry-head" }, FG.idChip(spec.entity), what.length ? h("span", { class: "entry-what" }, what.map((item, index) => [index ? " · " : null, item])) : null, spec.compact ? null : entryLinks(spec.entity)),
      spec.title
        ? h("h3", { class: "entry-title", lang: spec.titleLang || null, "data-field": spec.titleFields || "name" }, spec.service ? FG.serviceBadge(spec.service.identifier, spec.service.url, kind || "resources") : kind && icons().kind?.[kind] ? FG.kindBadge(kind) : null, h("span", null, spec.title))
        : null,
      spec.byline ? h("p", { class: "small entry-byline", "data-field": spec.bylineFields || null }, spec.byline) : null,
      details.length ? h("p", { class: "small muted card-details", lang: spec.detailsLang || null }, details.map((item, index) => [index ? " · " : null, item])) : null,
      spec.body,
      states.length ? h("div", { class: "badges" }, states) : null,
      spec.notes,
      spec.compact ? h("p", { class: "small entry-more" }, h("a", { href: FG.entryHref(spec.entity) }, FG.t("catalogue.whole.entry"))) : null,
      !spec.compact && (rows.length || FG.modelRows(spec.entity).length)
        ? h(
            "dl",
            { class: "relations" },
            rows.map(([key, items]) => [FG.relationTerm(key), h("dd", { class: [key === "identifiers" ? "pid-line" : null, WIDE_ROWS.includes(key) ? "relation-wide" : null].filter(Boolean).join(" ") || null, "data-field": rowFields(key) }, items)]),
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
    if (id.startsWith("#infrastructure-")) return h("a", { href: FG.entryHref(entity) }, name);
    if (entity["@type"] === "DataCatalog" || id.startsWith("#repository-")) return h("a", { href: FG.entryHref(entity) }, name);
    return h("a", { href: FG.entryHref(entity) }, name);
  };

  /** Who operates an entry, as its sources state it: the operator its own page names and the large research
      infrastructure that operates it, each with the source that says so (D-172, D-174). */
  const operatorRow = (entity) => [
    FG.partyName(entity, "publisher") ? h("span", null, FG.partyName(entity, "publisher"), entity.operatorSource ? [" (", FG.external(entity.operatorSource, FG.t("infrastructure.operatorSource")), ")"] : null) : null,
    FG.get(FG.id(entity.operatedBy))
      ? h("span", null, entryLink(FG.get(FG.id(entity.operatedBy))), entity.operatedBySource ? [" (", FG.external(entity.operatedBySource, FG.t("infrastructure.operatorSource")), ")"] : null)
      : null,
  ].filter(Boolean);

  /** Who developed an entry, where its sources name its developers rather than an operator (D-174). */
  const developerRow = (entity) =>
    FG.partyName(entity, "attributedTo") ? [h("span", null, FG.partyName(entity, "attributedTo"), entity.developerSource ? [" (", FG.external(entity.developerSource, FG.t("infrastructure.operatorSource")), ")"] : null)] : [];
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
    const date = (key, value) => (value ? FG.t(key, { date: String(value).length === 10 ? FG.formatDate(value) : String(value) }) : null);
    const short = entity.alternateName && FG.text(entity.alternateName) !== FG.text(entity.name) ? FG.text(entity.alternateName) : null;
    return [
      field("alternateName", short),
      field("publisher", publisher ? FG.text(publisher.alternateName || publisher.name) : null),
      field("inLanguage", languages.length ? FG.t("resource.languages", { languages: languages.join(", ") }) : null),
      field("version", entity.version ? FG.t("catalogue.version", { version: entity.version }) : null),
      field("preparationStatus", entity.preparationStatus === "in-preparation" ? FG.t("model.inPreparation") : null),
      field("datePublished", date("catalogue.published", entity.datePublished)),
      field("dateModified", date("catalogue.modified", entity.dateModified)),
      field("sdDatePublished", date("catalogue.accessed", entity.sdDatePublished)),
    ];
  }

  /** What an entry rests on: the snapshots its facts come from, and the RDMkit and training records that list it. */
  const basedOnRow = (entity) => [
    FG.refs(entity, "isBasedOn").filter((source) => String(source["@id"]).startsWith("#snapshot-")).map(snapshotItem),
    entity.rdmkitRecord ? FG.external(entity.rdmkitRecord, "RDMkit") : null,
    entity.trainingSearch ? FG.external(entity.trainingSearch, FG.t("catalogue.trainingSearch")) : null,
  ];

  /** A work's own licences as a row, each named from the data. */
  const licenceRow = (entity) => FG.list(entity.license).map((licence, index) => [index ? ", " : null, FG.licenceLink(licence)]);

  const uses = (list) => list.map((use) => FG.t("catalogue.use." + use));

  function resourceCard(resource, record, used, holders, compact) {
    return entryCard({
      kind: "resources",
      compact,
      id: resource.identifier,
      entity: resource,
      service: serviceOf(resource),
      what: [field("resourceType", FG.termName(FG.id(resource.resourceType)))].concat(uses(used)),
      title: FG.external(resource.url, FG.nameNodes(resource)),
      titleFields: "name url",
      byline: resource.creditText || null,
      bylineFields: "creditText",
      details: citationDetails(resource),
      body: resource.description ? h("p", { "data-field": "description mentions" }, FG.linkedSpan(resource, "description")) : null,
      states: [FG.statusBadge(resource), FG.nodeBadge(resource), record ? FG.verificationBadges(record.fer) : null],
      fields: { basedOn: "isBasedOn rdmkitRecord trainingSearch" },
      relations: {
        principles: record && record.fer ? tiles(FG.principlesOf(record.fer)) : [],
        audience: audiences(FG.refIds(resource, "audience")),
        operatedBy: operatorRow(resource),
        declaredIn: record ? declaredInRow(record.fer) : [],
        license: licenceRow(resource),
        basedOn: basedOnRow(resource),
        inGuide: inGuide(holders),
        identifiers: FG.identifierItems(resource),
      },
    });
  }

  /* Where sources are cited, worked out once for the parts of the knowledge base loaded so far. */
  let citedCache = null;
  const citedSources = () => {
    if (!citedCache || citedCache.revision !== FG.dataRevision || citedCache.graph !== FG.graph)
      citedCache = { revision: FG.dataRevision, graph: FG.graph, bySource: citations().bySource };
    return citedCache.bySource;
  };

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
  FG.catalogueParts = { audiences, basedOnRow, citationDetails, citations, code, declaredInRow, developerRow, entryCard, entryLink, field, icons, inGuide, licenceRow, operatorRow, resourceCard, serviceOf, slug, snapshotItem, sourceLink, stationsOf, tiles, typeOf, uses, writeState };
})();
