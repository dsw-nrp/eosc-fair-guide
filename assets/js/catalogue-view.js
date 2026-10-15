/* Catalogue of the FAIR Data Guide: one list of everything in the knowledge base, narrowed by facets with counts.
   Kind is a single choice that shows every kind with its count; search, station and principle apply across kinds
   and stay when the kind changes; a facet that belongs to one kind is labelled with it. The reader chooses the ordering, groups follow it, and the
   whole state is part of the address, so a filtered list is a link. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);
  const { audiences, citationDetails, citations, code, developerRow, entryCard, entryLink, icons, inGuide, operatorRow, resourceCard, serviceOf, slug, sourceLink, stationsOf, tiles, typeOf, uses, writeState } = FG.catalogueParts;

  const KINDS = ["resources", "repositories", "infrastructures", "clauses", "questions", "terms", "fips", "tests", "lifecycle", "model", "actions"];
  const PAGE = 20;
  const sourceKey = (source, id) => source + "." + id;
  /* Values shown before "more"; the path's steps always show in full. */
  const SHOWN_VALUES = 9;
  const expanded = new Set();
  const openFacets = new Set();

  /** The KNAV catalogue's tools, and the tool each entry of the guide stands for (its record's `sameAs`). */
  function knavIndex() {
    const tools = FG.refs(FG.get("#knav-tools"), "hasPart");
    const standing = new Map(tools.filter((tool) => tool.sameAs).map((tool) => [FG.id(tool.sameAs), tool]));
    return { tools, standing };
  }

  /** The guide's steps a catalogue tool belongs to: its catalogue steps, through the crosswalk, to the path's stages. */
  function knavStations(tool) {
    const stages = FG.refIds(tool, "lifecycleStage");
    const pathStages = stages.flatMap((stage) => correspondences(stage).flatMap((item) => FG.refIds(item, "about"))).filter((id) => !stages.includes(id));
    return FG.stations().filter((station) => pathStages.includes(FG.id(station.lifecycleStage)));
  }

  /** A KNAV catalogue tool no entry of the guide stands for, as the catalogue describes it. */
  function knavEntry(tool) {
    const anchor = sourceKey("knav", tool.identifier);
    const holders = knavStations(tool);
    const catalogue = FG.get("#knav-tools");
    const source = FG.get("#source-knav-dm-tools-catalogue");
    const steps = FG.refs(tool, "lifecycleStage");
    return {
      kind: "resources", entity: tool, name: tool.name,
      export: { url: tool.url || "", text: FG.text(tool.description) },
      text: [tool.name, FG.text(tool.description)].join(" "),
      stations: holders.map((station) => station.identifier), principles: [],
      facets: { use: ["knav"], type: ["#rtype-tool"], status: [], language: ["en"], lens: [], discipline: FG.list(tool.discipline) },
      render: () => entryCard({ kind: "resources",
        id: anchor, entity: tool, service: { identifier: anchor, name: tool.name, url: tool.url },
        what: [FG.termName("#rtype-tool")].concat(uses(["knav"])),
        /* The guide links only over HTTPS; a tool the catalogue lists by a plain-HTTP address leads to the catalogue. */
        title: tool.url ? FG.external(tool.url, tool.name) : h("span", null, tool.name),
        details: FG.list(tool.discipline).map((value) => FG.t("catalogue.discipline." + value)),
        body: [
          h("p", { lang: "en" }, FG.text(tool.description)),
          tool.url ? null : h("p", { class: "small" }, FG.t("catalogue.knavHttp") + " ", FG.external(catalogue.url, FG.t("catalogue.use.knav"))),
          steps.length ? h("p", { class: "small" }, h("span", { class: "entry-what" }, FG.t("catalogue.knavSteps") + ": "),
            steps.map((stage, index) => [index ? ", " : null, h("a", { href: FG.entryHref(stage) }, FG.span(stage.name))])) : null,
          tool.license ? h("p", { class: "small muted" }, FG.external(FG.id(tool.license) || tool.license, FG.t("catalogue.originalLicense"))) : null,
        ],
        relations: { basedOn: source ? [FG.sourceLink(source)] : [], inGuide: inGuide(holders) },
      }),
    };
  }

  /** Resources and cited sources as one kind, each marked by how the guide uses it, with the FIP Dashboard's
      resources and the KNAV catalogue's tools folded in. */
  function resourceEntries(cited) {
    const knav = knavIndex();
    const entries = [];
    const recommendedAt = new Map();
    for (const station of FG.stations()) for (const id of FG.refIds(station, "mentions")) recommendedAt.set(id, (recommendedAt.get(id) || []).concat(station));
    const citedSet = new Set(FG.refIds(FG.get("#sources"), "hasPart"));
    const linkedFers = new Set();
    const repositoryIds = new Set(FG.refIds(FG.get("#repositories"), "hasPart"));
    for (const repository of FG.refs(FG.get("#repositories"), "hasPart")) {
      const record = FG.dashboardRecord(repository);
      if (record && record.fer) linkedFers.add(record.fer["@id"]);
    }
    const resources = FG.graph.filter((entity) => entity.resourceType && String(entity["@id"]).startsWith("#resource-"));
    for (const resource of resources) {
      const record = FG.dashboardRecord(resource);
      if (record && record.fer) linkedFers.add(record.fer["@id"]);
      if (repositoryIds.has(resource["@id"])) continue;
      const recommended = recommendedAt.get(resource["@id"]) || [];
      const citedBy = cited.get(resource["@id"]) || [];
      const tool = knav.standing.get(resource["@id"]);
      const used = [recommended.length ? "recommended" : null, citedSet.has(resource["@id"]) ? "cited" : null, record ? "dashboard" : null, tool ? "knav" : null].filter(Boolean);
      entries.push({
        kind: "resources",
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
          discipline: tool ? FG.list(tool.discipline) : [],
          node: nodeRole(resource),
        },
        render: () => resourceCard(resource, record, used, recommended.concat(citedBy)),
      });
    }
    for (const source of FG.refs(FG.get("#sources"), "hasPart").filter((entity) => !entity.resourceType)) {
      const citedBy = cited.get(source["@id"]) || [];
      const url = source.url || (String(source["@id"]).startsWith("https://") ? source["@id"] : null);
      const tool = knav.standing.get(source["@id"]);
      const used = ["cited"].concat(tool ? ["knav"] : []);
      entries.push({
        kind: "resources",
        entity: source,
        name: FG.text(source.name),
        export: { url },
        text: [FG.text(source.name), source.creditText, FG.text((FG.get(source.publisher) || {}).name)].join(" "),
        stations: stationsOf(citedBy),
        principles: [],
        facets: { use: used, type: [typeOf(source)].filter(Boolean), status: [], language: FG.list(source.inLanguage).map(String), lens: [], discipline: tool ? FG.list(tool.discipline) : [] },
        render: () =>
          entryCard({ kind: "resources",
            id: source.identifier,
            entity: source,
            service: serviceOf(source),
            what: [FG.termName(typeOf(source))].concat(uses(used)),
            title: url ? FG.external(url, FG.nameNodes(source)) : FG.nameNodes(source),
            byline: source.creditText || null,
            details: citationDetails(source),
            relations: { inGuide: inGuide(citedBy), identifiers: FG.pidItems(source) },
          }),
      });
    }
    for (const fer of FG.refs(FG.get("#fers"), "hasPart").filter((entity) => !linkedFers.has(entity["@id"]) && !repositoryIds.has(entity["@id"]))) {
      const tool = knav.standing.get(fer["@id"]);
      const used = ["dashboard"].concat(tool ? ["knav"] : []);
      entries.push({
        kind: "resources",
        entity: fer,
        name: FG.text(fer.name),
        export: { url: fer.url, text: FG.text(fer.description) },
        text: [FG.text(fer.name), FG.bothLanguages(fer.description)].join(" "),
        stations: [],
        principles: FG.refs(fer, "about").map(code),
        facets: { use: used, type: [typeOf(fer)].filter(Boolean), status: [], language: [], lens: [], discipline: tool ? FG.list(tool.discipline) : [] },
        render: () =>
          entryCard({ kind: "resources",
            id: sourceKey("fip-dashboard", fer.identifier),
            entity: fer,
            service: serviceOf(fer) ? { identifier: sourceKey("fip-dashboard", fer.identifier), name: fer.name, url: fer.url } : null,
            what: [FG.termName(typeOf(fer))].concat(uses(used)),
            title: FG.external(FG.refIds(fer, "sameAs")[0] || fer.url, fer.name),
            body: fer.description ? h("p", null, FG.span(fer.description)) : null,
            states: FG.verificationBadges(fer),
            relations: { principles: tiles(FG.principlesOf(fer)), identifiers: FG.pidItems(fer) },
          }),
      });
    }
    for (const tool of knav.tools.filter((item) => !item.sameAs)) entries.push(knavEntry(tool));
    return entries;
  }

  /** What an entry is in the EOSC CZ Node, as a facet value: its role there, or none (D-172). */
  const nodeRole = (entity) => {
    const membership = FG.get(FG.id(entity.nodeMembership));
    return membership ? [FG.id(membership.roleName)] : [];
  };

  /** The large research infrastructures of the national roadmap (D-174): names in the reader's language with the
      acronym, the facts the roadmap states with where it states them, and three relations kept apart: the European
      infrastructures each is the Czech node of, its ERIC memberships, and the entries it operates. */
  function infrastructureEntries() {
    return FG.refs(FG.get("#infrastructures"), "hasPart").map((infra) => {
      const field = FG.id(infra.researchField);
      const phase = FG.id(infra.infrastructurePhase);
      const character = FG.id(infra.infrastructureCharacter);
      const nodes = FG.refs(infra, "nationalNodeOf");
      const erics = FG.refs(infra, "memberOf");
      const name = FG.abbreviatedName(infra, FG.state.lang);
      return {
        kind: "infrastructures",
        entity: infra,
        name,
        export: { url: infra.url },
        text: [FG.nameForms(infra), infra.hostingInstitution, nodes.map((ri) => ri.name).join(" "), erics.map((eric) => eric.name).join(" ")].join(" "),
        stations: [],
        principles: [],
        order: FG.fold(infra.abbreviation || FG.text(infra.name)),
        facets: { field: field ? [field] : [], riphase: phase ? [phase] : [], esfri: FG.refIds(infra, "esfriStatus") },
        render: () =>
          entryCard({ kind: "infrastructures",
            id: infra.identifier,
            entity: infra,
            service: { identifier: "infrastructure-" + infra.identifier },
            what: [field, phase].filter(Boolean).map(categoryLabel),
            title: infra.url ? FG.external(infra.url, name) : name,
            details: [otherName(infra), FG.t("infrastructure.host", { host: infra.hostingInstitution }), FG.t("infrastructure.since", { year: infra.roadmapSince }), character ? categoryLabel(character) : null],
            states: FG.refIds(infra, "esfriStatus").map((id) => h("span", { class: "badge" }, FG.termName(id))),
            relations: {
              operates: FG.refs(infra, "operates").map(entryLink),
              identifiers: FG.pidItems(infra),
              nationalNodeOf: nodes.map((ri) => h("span", null, ri.name + (FG.id(ri.esfriStatus) ? " (" + FG.termName(FG.id(ri.esfriStatus)) + ")" : ""))),
              fips: FG.id(infra.subjectOf) ? [h("a", { href: FG.entryHref(FG.get(infra.subjectOf)) }, FG.text((FG.get(FG.id(infra.subjectOf)) || {}).name) || FG.id(infra.subjectOf).replace("#fip-", ""))] : [],
              memberOf: erics.map((eric) => h("span", null, eric.czechMembershipSince === "expected" ? FG.t("infrastructure.ericExpected", { name: eric.name }) : FG.t("infrastructure.ericSince", { name: eric.name, year: eric.czechMembershipSince }))),
              basedOn: FG.refs(infra, "isBasedOn").map((source, index) => h("span", null, sourceLink(source), index === 0 && infra.roadmapLocator ? " · " + infra.roadmapLocator : null)),
            },
          }),
      };
    });
  }

  /** An entry's name in the other language, where it differs (D-173). */
  const otherName = (entity) => (FG.otherLanguageName(entity) || {}).text || null;

  function repositoryEntries(cited) {
    const citedSet = new Set(FG.refIds(FG.get("#sources"), "hasPart"));
    const knav = knavIndex();
    return FG.repositoryEntries().map((repository) => {
      const anchor = FG.repositoryAnchor(repository);
      const kindIndex = FG.repositoryKindOrder.indexOf(FG.id(repository.repositoryKind));
      const record = FG.dashboardRecord(repository);
      const recommended = FG.stations().filter((station) => FG.refIds(station, "mentions").includes(repository["@id"]));
      const citedBy = cited.get(repository["@id"]) || [];
      const holders = recommended.concat(citedBy);
      const functions = FG.refIds(repository, "repositoryFunction");
      const tool = knav.standing.get(repository["@id"]);
      const used = [recommended.length ? "recommended" : null, citedSet.has(repository["@id"]) ? "cited" : null, record ? "dashboard" : null, tool ? "knav" : null].filter(Boolean);
      return {
        kind: "repositories",
        anchor,
        entity: repository,
        name: FG.abbreviatedName(repository, FG.state.lang),
        export: { url: repository.url, text: FG.text(repository.description) },
        text: [FG.nameForms(repository), FG.bothLanguages(repository.description), FG.bothLanguages(repository.keywords)].join(" "),
        stations: [...new Set(stationsOf(holders).concat(functions.includes("#rfunction-deposit-data") ? ["repository"] : []))],
        principles: record && record.fer ? FG.refs(record.fer, "about").map(code) : [],
        order: (kindIndex < 0 ? FG.repositoryKindOrder.length : kindIndex) + ":" + FG.fold(FG.text(repository.name)),
        facets: {
          rfunction: functions,
          rkind: FG.id(repository.repositoryKind) ? [FG.id(repository.repositoryKind)] : [],
          rsource: FG.refIds(repository, "isBasedOn"),
          use: used,
          status: FG.id(repository.serviceStatus) ? [FG.id(repository.serviceStatus)] : [],
          language: FG.list(repository.inLanguage).map(String),
          lens: FG.refIds(repository, "audience").map((id) => id.replace("#lens-", "")),
          node: nodeRole(repository),
        },
        render: () =>
          entryCard({ kind: "repositories",
            id: anchor,
            entity: repository,
            service: { identifier: repository["@id"].replace(/^#(resource|repository)-/, ""), name: repository.name, url: repository.url },
            what: functions.map(FG.termName).concat(FG.id(repository.repositoryKind) ? [FG.termName(FG.id(repository.repositoryKind))] : [], uses(used)),
            title: FG.external(repository.url, FG.abbreviatedName(repository, FG.state.lang)),
            /* The name in the other language stays on the entry (D-173). */
            details: [otherName(repository), FG.subjectsOf(repository).join(", ")].filter(Boolean),
            body: [repository.description ? h("p", null, FG.span(repository.description)) : null, dataciteBlock(repository, anchor)],
            states: [FG.statusBadge(repository), FG.nodeBadge(repository), record ? FG.verificationBadges(record.fer) : null],
            relations: {
              principles: record && record.fer ? tiles(FG.principlesOf(record.fer)) : [],
              operatedBy: operatorRow(repository),
              developedBy: developerRow(repository),
              basedOn: FG.repositorySourceLinks(repository),
              audience: audiences(FG.refIds(repository, "audience")),
              inGuide: inGuide(holders),
              identifiers: FG.pidItems(repository).concat(record ? [FG.pidItem("dashboard", record.url)] : []),
            },
          }),
      };
    });
  }

  /* What DataCite reported about each repository a reader asked about during this visit, by entry. */
  const dataciteReads = new Map();
  const number = FG.formatNumber;
  /** The leading counts of one DataCite facet, each as its title with the count in brackets. */
  const leading = (list) => list.slice(0, 4).map((entry) => entry.title + " (" + number(entry.count) + ")").join(" · ");

  /** A repository's DataCite record, read on the reader's request: what DataCite reports about its DOIs, with the date
      it was read, and links to its DataCite Commons page and its Metadata Dashboard. */
  function dataciteBlock(repository, anchor) {
    /* Offered only where DataCite holds the repository: the guide names its DataCite repository, or the DataCite
       snapshot found it by the repository's re3data record. */
    const route = FG.live.dataciteRoute(repository);
    if (!route || !route.id) return null;
    const read = dataciteReads.get(anchor) || { state: "idle" };
    const button = "datacite-load-" + slug(anchor);
    const load = async () => {
      dataciteReads.set(anchor, { state: "loading" });
      FG.rerender(button);
      try {
        const found = await FG.live.dataciteRepository(route);
        const counts = found ? await FG.live.dataciteCounts(found.id) : null;
        dataciteReads.set(anchor, found ? { state: "done", found, counts, date: FG.today() } : { state: "absent" });
      } catch (error) {
        dataciteReads.set(anchor, { state: "failed" });
      }
      FG.rerender("datacite-" + slug(anchor));
    };
    const t = (key, params) => FG.t("catalogue.datacite." + key, params);
    if (read.state !== "done") {
      return h(
        "div",
        { class: "datacite-read", id: "datacite-" + slug(anchor), tabindex: "-1" },
        h("button", { type: "button", class: "button-small", id: button, onclick: load, disabled: read.state === "loading" || null }, t("load")),
        read.state === "idle" ? null : h("p", { class: "small", role: "status" }, t(read.state))
      );
    }
    const { found, counts } = read;
    const links = FG.config.links;
    return h(
      "section",
      { class: "datacite-read", id: "datacite-" + slug(anchor), tabindex: "-1", "aria-label": t("title") },
      h("p", { class: "small" }, h("strong", null, t("read", { date: FG.formatDate(read.date) })), " · ", t("as", { name: found.name, id: found.id })),
      h(
        "dl",
        { class: "datacite-facts small" },
        h("dt", null, t("total")), h("dd", null, number(counts.total)),
        counts.resourceTypes.length ? [h("dt", null, t("types")), h("dd", null, leading(counts.resourceTypes))] : null,
        counts.licenses.length ? [h("dt", null, t("licenses")), h("dd", null, leading(counts.licenses))] : null,
        counts.schemaVersions.length ? [h("dt", null, t("schemas")), h("dd", null, leading(counts.schemaVersions))] : null
      ),
      h("p", { class: "small" }, FG.external(links.dataciteRepository + found.id, t("commons")), " · ", FG.external(links.dataciteMetadata + found.id, t("metadata")))
    );
  }

  function clauseEntries(used) {
    return FG.refs(FG.get("#ledger"), "hasPart").map((clause, index) => {
      const holders = used.get(clause["@id"]) || [];
      const status = clause.creativeWorkStatus || "current";
      const audience = FG.id(clause.audience);
      const source = FG.get(clause.isPartOf);
      return {
        kind: "clauses",
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
          entryCard({ kind: "clauses",
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
              audience: audience ? h("span", { class: "audience" }, FG.category(FG.termName(audience))) : null,
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
              entryCard({ kind: "questions",
                id: item.identifier,
                entity: item,
                what: FG.id(item.tier) ? FG.category(FG.termName(FG.id(item.tier))) : null,
                body: h("p", null, FG.linkedSpan(item)),
                relations: {
                  principles: tiles(FG.principlesOf(item)),
                  basedOn: clauses.map((clause) => FG.idChip(clause)),
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
        entity: term,
        name: cs.replace(/^[[(]+/, ""),
        export: { name: FG.text(term.name), url: term.url, text: FG.text(term.description), license: term.license },
        nameEn: en.replace(/^[[(]+/, ""),
        text: cs + " " + en + " " + FG.bothLanguages(term.description),
        stations: stationsOf(at),
        principles: [],
        facets: {},
        render: () =>
          entryCard({ kind: "terms",
            id: FG.termAnchor(term),
            entity: term,
            class: "term-card",
            what: FG.t("catalogue.what.term"),
            title: FG.external(term.url, cs),
            titleLang: "cs",
            details: en,
            detailsLang: "en",
            /* Definitions retain the source's language; no English translation is invented. */
            body: [
              term.description ? h("details", { class: "term-definition", open: Boolean(FG.parseHash(window.location.hash).extra) },
                h("summary", null, FG.t("catalogue.originalDefinition")), FG.paragraphs(term.description)) : null,
              FG.refs(term, "subjectOf").filter((clause) => clause.guidance).map((clause) => h("details", null,
                h("summary", null, FG.t("catalogue.originalDefinition")),
                h("div", { class: "content" }, h("p", null, FG.sourceLink(FG.get(clause.isPartOf)), clause.sourceLocator ? " · " + clause.sourceLocator : ""),
                  h("blockquote", null, FG.paragraphs(clause.guidance))))),
              h("p", { class: "small muted term-attribution" }, FG.external(term.url, FG.t("catalogue.termDefinition")),
                term.license ? [" · ", FG.external(term.license, "CC BY 4.0")] : null),
            ],
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
        entity: fip,
        name: FG.text(fip.name),
        export: { url },
        text: [FG.bothLanguages(fip.name), fip.alternateName, FG.bothLanguages(fip.abstract)].join(" "),
        stations: [],
        principles: [...new Set(FG.refs(fip, "hasPart").flatMap((declaration) => FG.principlesOf(declaration).map((principle) => principle.termCode)))],
        facets: {},
        render: () =>
          entryCard({ kind: "fips",
            id: sourceKey("fip-dashboard", fip.identifier),
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

  /** The questions each registered test pre-fills, by test identifier. */
  function testQuestions() {
    const byTest = new Map();
    for (const check of FG.ofType("Quiz")) {
      for (const item of FG.refs(check, "hasPart").sort(FG.byPosition)) {
        for (const entry of FG.refs(item, "additionalProperty").filter((property) => property.propertyID === "prefill:champion")) {
          for (const test of FG.list(entry.value).map(String)) byTest.set(test, (byTest.get(test) || []).concat(item));
        }
      }
    }
    for (const test of FG.refs(FG.get("#tests"), "hasPart")) {
      const item = FG.get(test.isImplementationOf);
      if (item) byTest.set(test.identifier, [item]);
    }
    return byTest;
  }

  /** External evaluators' native criteria: the provider's own identifier and wording, the guide's reading, the
      reviewed versions, and the questions each relates to with its coverage. Unmapped criteria stay listed. */
  function criterionEntries() {
    const providers = FG.list((FG.config.providers || {}).list);
    return FG.graph
      .filter((entity) => String(entity["@id"]).startsWith("#criterion-") && entity.identifier && !entity.mappingCoverage)
      .map((criterion) => {
        const provider = providers.find((entry) => criterion["@id"] === "#criterion-" + entry.id + "-" + criterion.identifier) || { id: "", name: FG.text((FG.get(criterion.isPartOf) || {}).name), mode: "service" };
        const mappings = FG.refs(criterion, "hasPart");
        const linked = mappings.map((mapping) => ({ mapping, item: FG.get(mapping.about) })).filter((entry) => entry.item);
        const checks = [...new Set(linked.map(({ item }) => String(item.identifier).split(".")[0]))];
        const stations = [...new Set(linked.map(({ item }) => String(FG.id(item.fixAt) || "").replace("#station-", "")).filter(Boolean))];
        const principles = FG.principlesOf(criterion);
        const execution = provider.mode === "import" ? "import" : "service";
        const documentation = FG.list(criterion.subjectOf).map(FG.id).filter(Boolean);
        const anchor = sourceKey(provider.id, criterion.identifier);
        return {
          kind: "tests",
          anchor,
          entity: criterion,
          name: FG.text(criterion.alternateName) || FG.text(criterion.name),
          export: { url: criterion.url, text: FG.text(criterion.name) },
          text: [FG.bothLanguages(criterion.alternateName), FG.text(criterion.name), criterion.identifier, provider.name].join(" "),
          stations,
          principles: principles.map((principle) => principle.termCode),
          group: { check: checks[0] || "" },
          facets: { execution: [execution], check: checks, thealth: [] },
          render: () =>
            entryCard({ kind: "tests",
              id: anchor,
              entity: criterion,
              what: FG.t("catalogue.what.criterion", { provider: provider.name }),
              details: FG.t("catalogue.testExecution." + execution),
              title: [FG.span(criterion.alternateName), " ", h("span", { class: "id-chip id-chip-static" }, criterion.identifier)],
              body: [h("p", { class: "small muted", lang: "en" }, FG.text(criterion.name)),
                h("p", { class: "small" }, criterion.url ? FG.external(criterion.url, FG.t(execution === "service" ? "selfcheck.evidence.endpoint" : "catalogue.criterionForm")) : null,
                  documentation.map((url) => [" · ", FG.external(url, FG.t("selfcheck.evidence.documentation"))])),
                FG.list(criterion.reviewedVersion).length ? h("p", { class: "small" }, FG.t("catalogue.reviewedVersion") + ": " + FG.list(criterion.reviewedVersion).join("; ")) : null,
                linked.length
                  ? h("ul", { class: "small" }, linked.map(({ mapping, item }) => h("li", null, FG.idChip(item), " ", FG.t("catalogue.coverage." + mapping.mappingCoverage), mapping.description ? [": ", FG.span(mapping.description)] : null)))
                  : h("p", { class: "small muted" }, FG.t("catalogue.unmapped"))],
              relations: {
                principles: tiles(principles),
                inGuide: inGuide(checks.map((id) => FG.get("#check-" + id))),
                identifiers: FG.pidItems(criterion),
              },
            }),
        };
      });
  }

  function testEntries() {
    const questions = testQuestions();
    return FG.graph
      .filter((entity) => String(entity["@id"]).startsWith("#test-"))
      .map((test) => {
        const principles = FG.principlesOf(test);
        const local = String(test.identifier).startsWith("guide-");
        const anchor = local ? test.identifier : sourceKey("fair-champion", test.identifier);
        const health = FG.id(test.healthStatus) || test.healthStatus;
        const documentation = FG.list(test.subjectOf).map((entry) => {
          const entity = FG.get(entry);
          return entity && entity.url || FG.id(entry);
        }).filter(Boolean);
        const entryPoint = FG.refs(test, "additionalProperty").find((entry) => entry.propertyID === "entryPoint");
        const linkedQuestions = questions.get(local ? test.identifier : FG.sourceIdentifier(test, "fair-champion")) || [];
        const checks = [...new Set(linkedQuestions.map((item) => String(item.identifier).split(".")[0]))];
        const stations = [...new Set(linkedQuestions.map((item) => String(FG.id(item.fixAt) || "").replace("#station-", "")).filter(Boolean))];
        return {
          kind: "tests",
          anchor,
          entity: test,
          name: FG.text(test.name),
          export: { url: FG.refIds(test, "sameAs")[0] || test.url, text: FG.text(test.description) },
          text: [FG.bothLanguages(test.name), FG.bothLanguages(test.description), test.identifier].join(" "),
          stations,
          principles: principles.map((principle) => principle.termCode),
          group: { check: checks[0] || "" },
          facets: { execution: [local ? "browser" : "service"], check: checks, thealth: health ? [String(health)] : [] },
          render: () =>
            entryCard({ kind: "tests",
              id: anchor,
              entity: test,
              what: FG.t(local ? "catalogue.what.localTest" : "catalogue.what.test"),
              details: FG.t("catalogue.testExecution." + (local ? "browser" : "service")),
              title: FG.span(test.name),
              body: [test.description ? FG.paragraphs(test.description) : null,
                h("p", { class: "small" }, FG.external(test.url, FG.t(local ? "selfcheck.evidence.code" : "selfcheck.evidence.endpoint"))),
                documentation.length ? h("p", { class: "small" }, documentation.map((url, index) => [index ? " · " : null, FG.external(FG.testDocumentationHref(url, test), FG.t("selfcheck.evidence.documentation") + (documentation.length > 1 ? " " + (index + 1) : ""))])) : null,
                entryPoint ? h("p", { class: "small" }, h("code", null, entryPoint.value)) : null],
              states: health
                ? h("span", { class: "badge", "data-health": String(health) }, FG.t("catalogue.health." + health), test.statusAsOf ? h("span", { class: "muted" }, " · " + FG.t("status.asOf", { date: FG.formatDate(test.statusAsOf) })) : null)
                : null,
              relations: {
                principles: tiles(principles),
                inGuide: inGuide(checks.map((id) => FG.get("#check-" + id))).concat(linkedQuestions.map((item) => FG.idChip(item))),
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
    for (const entry of kinds.clauses) add(FG.id(entry.entity), entry.stations, entry.principles);
    for (const entry of kinds.questions) add(FG.id(entry.entity), entry.stations, entry.principles);
    for (const entry of kinds.resources) add(FG.id(entry.entity), entry.stations, entry.principles);
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
            entryCard({ kind: "actions",
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
      repositories: repositoryEntries(bySource),
      infrastructures: infrastructureEntries(),
      clauses: clauseEntries(byClause),
      questions: questionEntries(),
      terms: termEntries(),
      fips: fipEntries(),
      tests: testEntries().concat(criterionEntries()),
      lifecycle: lifecycleEntries(),
      model: modelEntries(),
    };
    kinds.actions = actionEntries(reachOf(kinds));
    for (const entry of Object.values(kinds).flat()) {
      const address = FG.config.api.records[FG.id(entry.entity)];
      if (!address) throw new Error("Catalogue entry has no build-issued address: " + FG.id(entry.entity));
      entry.kind = FG.catalogueKind(address.split("/")[0]);
      entry.anchor = address.split("/").slice(1).join("/");
      entry.text = [entry.text, entry.anchor, entry.entity["@id"], ...FG.list(entry.entity.identifier), ...FG.refs(entry.entity, "alternateIdentifier").map((item) => item.value)].join(" ");
      entry.layers = FG.refIds(entry.entity, "implementationLayers");
      entry.seams = FG.refIds(entry.entity, "implementationSeams");
    }
    const grouped = Object.fromEntries(KINDS.map((kind) => [kind, []]));
    for (const entry of Object.values(kinds).flat()) grouped[entry.kind].push(entry);
    return grouped;
  }

  function modelEntries() {
    return FG.modelTerms().map((term) => ({
      kind: "model", entity: term, name: FG.text(term.name),
      text: [term.identifier, FG.bothLanguages(term.name), FG.bothLanguages(term.description)].join(" "),
      export: { text: FG.text(term.description) }, stations: [], principles: [],
      order: String(term.position || 0).padStart(3, "0"), facets: { modelKind: [term.modelKind] },
      render: () => entryCard({ kind: "model", id: term.identifier, entity: term, what: FG.t("model.kind." + term.modelKind),
        title: FG.span(term.name), body: [FG.paragraphs(term.description), FG.modelDetail(term),
          h("p", { class: "small" }, h("a", { href: FG.modelFilterHref("resources", term) }, FG.t("model.related")), " · ",
            h("a", { href: FG.href("page", "model") }, FG.t("model.overview")))],
        relations: { basedOn: FG.refs(term, "citation").map(FG.sourceLink) }
      })
    }));
  }

  /* The life-cycle models in order, and the path's stage of a station (`lifecycleStage`). */
  const lifecycleModels = () => FG.graph.filter((entity) => /^#lifecycle-/.test(entity["@id"]) && entity["@type"] === "DefinedTermSet").sort(FG.byPosition);
  const modelSource = (model) => FG.refs(model, "citation")[0];
  const correspondences = (stageId) => FG.refs(FG.get("#lifecycle-crosswalk"), "hasPart").filter((item) => FG.refIds(item, "about").includes(stageId));

  /* Each basis of a correspondence by its icon, beside its name. */
  const BASIS_ICONS = { published: "met", reviewed: "search", unconfirmed: "unknown" };

  /** A stage's correspondence as one line: the other model's stage, the basis, its source and why. */
  function correspondenceItem(item, stageId) {
    const other = FG.refs(item, "about").find((stage) => stage["@id"] !== stageId);
    const model = other && FG.get(FG.id(other.inDefinedTermSet));
    const source = FG.refs(item, "citation")[0];
    return h("li", { "data-basis": item.mappingBasis },
      h("a", { href: FG.entryHref(other) }, model ? FG.shortText(modelSource(model)) + ": " : "", FG.span(other.name)),
      " ", h("span", { class: "badge", "data-basis": item.mappingBasis }, FG.icon(BASIS_ICONS[item.mappingBasis]), FG.t("lifecycle.basis." + item.mappingBasis)),
      source ? [" · ", FG.sourceLink(source)] : null,
      item.description ? h("span", { class: "small muted" }, " · ", FG.span(item.description)) : null);
  }

  function lifecycleEntries() {
    const stations = FG.stations();
    return lifecycleModels().flatMap((model) => FG.refs(model, "hasDefinedTerm").map((stage) => {
      /* A path stage holds its stations; another model's stage reaches them through the path stages it matches. */
      const pathStages = model["@id"] === FG.id(FG.get("#path").isBasedOn) ? [stage["@id"]] : correspondences(stage["@id"]).flatMap((item) => FG.refIds(item, "about")).filter((id) => id !== stage["@id"]);
      const holders = stations.filter((station) => pathStages.includes(FG.id(station.lifecycleStage)));
      const translated = FG.list(stage.nameTranslation).includes(FG.state.lang);
      const definition = FG.list(stage.description).filter((value) => value && value["@value"]);
      const shown = definition.find((value) => value["@language"] === FG.state.lang) || definition[0];
      return {
        kind: "lifecycle", entity: stage, name: FG.text(stage.name),
        text: [stage.identifier, FG.bothLanguages(stage.name), definition.map((value) => value["@value"]).join(" ")].join(" "),
        export: { text: shown ? shown["@value"] : "" }, stations: holders.map((station) => station.identifier), principles: [],
        order: String(model.position).padStart(2, "0") + String(stage.position).padStart(3, "0"), facets: { lcmodel: [model.identifier] },
        render: () => entryCard({ kind: "lifecycle",
          id: stage.identifier, entity: stage,
          what: [FG.shortText(modelSource(model)), FG.t("lifecycle.stage")],
          title: FG.span(stage.name),
          details: translated ? FG.t("lifecycle.translatedName") : null,
          body: [
            shown ? h("blockquote", { class: "stage-definition", lang: shown["@language"] }, shown["@value"]) : null,
            /* A path stage's Czech definition is the Průvodce's translation; the Czech source's own wording follows it. */
            shown && FG.list(stage.descriptionTranslation).includes(shown["@language"])
              ? h("p", { class: "small muted" }, FG.t("lifecycle.translationOf", { source: FG.shortText(modelSource(model)) }))
              : null,
            stage.quotedDefinition
              ? [h("blockquote", { class: "stage-definition stage-quote", lang: FG.list(stage.quotedDefinition)[0]["@language"] }, FG.list(stage.quotedDefinition)[0]["@value"]),
                h("p", { class: "small muted" }, FG.t("lifecycle.quoteOf") + " ", FG.sourceLink(FG.refs(stage, "citation").slice(-1)[0]))]
              : null,
            stage.note ? h("p", { class: "small", lang: FG.list(stage.note)[0]["@language"] }, FG.list(stage.note)[0]["@value"]) : null,
            FG.list(stage.license).map((license) => h("p", { class: "small muted" }, FG.external(FG.id(license) || license, FG.t("catalogue.originalLicense")))),
            correspondences(stage["@id"]).length
              ? [h("p", { class: "entry-what" }, FG.t("lifecycle.correspondsTo")), h("ul", { class: "crosswalk small" }, correspondences(stage["@id"]).map((item) => correspondenceItem(item, stage["@id"])))]
              : null,
          ],
          relations: { basedOn: FG.refs(stage, "citation").map(FG.sourceLink), inGuide: inGuide(holders) },
        }),
      };
    }));
  }

  /* ---------------------------------------------------------------- exports */

  /** One entry as a row of an exported list, in the reader's language. */
  function exportRow(entry) {
    const out = entry.export || {};
    const row = { id: FG.config.api.records[FG.id(entry.entity)], name: out.name || entry.name, text: out.text || "", url: out.url || "", date: String(entry.date || "").slice(0, 10) };
    if (out.license) row.license = out.license;
    for (const facet of KIND_FACETS[entry.kind] || []) row[facet.key] = (entry.facets[facet.key] || []).map(facet.label);
    row.stations = entry.stations.map((id) => FG.text((FG.get("#station-" + id) || {}).name));
    row.principles = entry.principles;
    row.implementationLayers = entry.layers;
    row.implementationSeams = entry.seams;
    row.entry = FG.pageAddress() + FG.catalogueHref(entry.kind, entry.anchor);
    const record = FG.recordHref(entry.entity);
    if (record) row.record = FG.siteAddress() + record;
    return row;
  }

  /** The columns of a kind's list: the fields its entries fill, its facets, where the guide uses them, the link. */
  function exportColumns(kind, rows) {
    const facets = (KIND_FACETS[kind] || []).map((facet) => facet.key);
    const filled = ["id", "name", "text", "url", "date", "license"].filter((key) => rows.some((row) => row[key]));
    return filled.concat(facets, ["stations", "principles", "implementationLayers", "implementationSeams", "entry"], rows.some((row) => row.record) ? ["record"] : []).map((key) => ({ key, label: facets.includes(key) ? FG.t("catalogue.facet." + key) : FG.t("export.column." + key) }));
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
      return { "@id": record ? site + record : FG.pageAddress() + FG.catalogueHref(entry.kind, entry.anchor), "@type": entity["@type"], identifier: FG.config.api.records[FG.id(entity)], [label]: FG.languageMap(entity[label]) || entry.name,
        ...(entry.kind === "terms" && entity.description ? { description: FG.languageMap(entity.description), url: entity.url, license: entity.license } : {}),
        implementationLayers: entry.layers.map((id) => ({ "@id": site + "ro-crate-metadata.json" + id })),
        implementationSeams: entry.seams.map((id) => ({ "@id": site + "ro-crate-metadata.json" + id })) };
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
    /* An empty list has nothing to save; its exports wait, saying why. */
    const empty = rows.length ? null : FG.t("export.emptyList");
    FG.offerExport({ id: "csv", label: FG.t("export.csv", { n: rows.length }), unavailable: empty, run: () => FG.download(FG.exportName(parts, "csv"), FG.csv(columns, rows), "text/csv") });
    const saveJson = async () => {
      try {
        await FG.completeLanguages();
        FG.download(FG.exportName(parts, "json"), JSON.stringify(payload(), null, 2) + "\n", "application/json");
      } catch (error) { FG.dataLoadError(error, saveJson); }
    };
    FG.offerExport({ id: "json", label: FG.t("export.json", { n: rows.length }), unavailable: empty, run: saveJson });
  }

  /* ---------------------------------------------------------------- facets of one kind */

  /* The KNAV catalogue's discipline groups, in the order of its filter. */
  const KNAV_DISCIPLINES = ["all", "biology-chemistry", "physics-materials", "computer-information", "astronomy", "social-sciences-humanities", "earth-sciences"];
  const termLabel = (id) => FG.termName(id) || id;
  /* Every kind's categories read the same: in lower case, unless a name starts with an acronym. */
  const categoryLabel = (id) => FG.category(termLabel(id));
  const KIND_FACETS = {
    resources: [
      { key: "use", values: () => ["recommended", "cited", "dashboard", "knav"], label: (value) => FG.t("catalogue.use." + value) },
      { key: "type", label: categoryLabel },
      { key: "status", label: categoryLabel },
      { key: "language", values: () => ["cs", "en"], label: (value) => FG.t("catalogue.language." + value) },
      /* The lens narrows what the guide recommends; a cited work or a dashboard record has no audience and stays. */
      { key: "lens", values: () => FG.lenses().map((lens) => lens.audienceType), label: (value) => FG.category(FG.text((FG.lenses().find((lens) => lens.audienceType === value) || {}).name)), passThrough: true },
      { key: "discipline", values: () => KNAV_DISCIPLINES, label: (value) => FG.t("catalogue.discipline." + value) },
      { key: "node", values: () => FG.refIds(FG.get("#node-roles"), "hasDefinedTerm"), label: categoryLabel },
    ],
    repositories: [
      { key: "rfunction", values: () => FG.refIds(FG.get("#repository-functions"), "hasDefinedTerm"), label: categoryLabel },
      { key: "rkind", values: () => FG.repositoryKindOrder, label: categoryLabel },
      { key: "rsource", label: (value) => FG.repositorySource(value) },
      { key: "use", values: () => ["recommended", "cited", "dashboard", "knav"], label: (value) => FG.t("catalogue.use." + value) },
      { key: "status", label: categoryLabel },
      { key: "language", values: () => ["cs", "en"], label: (value) => FG.t("catalogue.language." + value) },
      { key: "lens", values: () => FG.lenses().map((lens) => lens.audienceType), label: (value) => FG.category(FG.text((FG.lenses().find((lens) => lens.audienceType === value) || {}).name)), passThrough: true },
      { key: "node", values: () => FG.refIds(FG.get("#node-roles"), "hasDefinedTerm"), label: categoryLabel },
    ],
    infrastructures: [
      { key: "field", values: () => FG.refIds(FG.get("#research-fields"), "hasDefinedTerm"), label: categoryLabel },
      { key: "riphase", values: () => FG.refIds(FG.get("#ri-phases"), "hasDefinedTerm"), label: categoryLabel },
      { key: "esfri", values: () => FG.refIds(FG.get("#esfri-statuses"), "hasDefinedTerm"), label: (value) => FG.termName(value) },
    ],
    clauses: [
      { key: "ckind", values: () => ["requirement", "recommendation", "fulfilment", "statement"], label: (value) => FG.t("catalogue.clauseKind." + value) },
      { key: "csource", label: (value) => (FG.get(value) ? FG.shortText(FG.get(value)) : value) },
      { key: "actor", label: categoryLabel },
      { key: "cstatus", values: () => ["current", "refresh", "superseded"], label: (value) => FG.t("catalogue.clauseStatus." + value) },
    ],
    questions: [
      { key: "check", values: () => FG.ofType("Quiz").map((check) => check.identifier), label: (value) => FG.text((FG.get("#check-" + value) || {}).name) },
      { key: "tier", label: categoryLabel },
    ],
    tests: [
      { key: "execution", values: () => ["browser", "service", "import"], label: (value) => FG.t("catalogue.testExecution." + value) },
      { key: "check", values: () => FG.ofType("Quiz").map((check) => check.identifier), label: (value) => FG.text((FG.get("#check-" + value) || {}).name) },
      { key: "thealth", label: (value) => FG.t("catalogue.health." + value), note: "catalogue.testHealthNote" },
    ],
    lifecycle: [{ key: "lcmodel", values: () => lifecycleModels().map((model) => model.identifier), label: (value) => FG.shortText(modelSource(FG.get("#lifecycle-" + value))) }],
    model: [{ key: "modelKind", values: () => ["layer", "seam"], label: (value) => FG.t("model.kind." + value) }],
    actions: [{ key: "change", values: () => ["created", "updated"], label: (value) => FG.t("catalogue." + value) }],
  };

  /* ---------------------------------------------------------------- the state in the address */

  /** `k!resources_clauses~s!licence~p!R1.1~q!licence~o!name~f.use!cited`; a bare kind (an older tab address) selects
      that kind alone. */
  function readState(route) {
    const state = { kinds: [], stations: [], principles: [], layers: [], seams: [], q: "", order: "", f: {} };
    const arg = String(route.arg || "");
    if (KINDS.includes(arg)) {
      state.kinds = [arg];
      return state;
    }
    for (const field of arg.split("~")) {
      const [key, value = ""] = field.split("!");
      const list = value ? value.split("_").map(decodeURIComponent) : [];
      if (key === "k") state.kinds = list.filter((kind) => KINDS.includes(kind));
      else if (key === "s") state.stations = list;
      else if (key === "p") state.principles = list;
      else if (key === "l") state.layers = list;
      else if (key === "n") state.seams = list;
      else if (key === "q") state.q = decodeURIComponent(value);
      else if (key === "o") state.order = value;
      else if (key.startsWith("f.")) state.f[key.slice(2)] = list;
    }
    state.kinds = state.kinds.length ? state.kinds.slice(0, 1) : ["resources"];
    return state;
  }

  /** The values chosen for a facet; the lens facet, like every other, starts with none. */
  const chosenValues = (state, route, key) => state.f[key] || [];

  /** A model definition belongs in its own facet without asserting a self-association in the knowledge base. */
  function sharedValues(entry, dimension) {
    const ownKind = dimension === "layers" ? "layer" : dimension === "seams" ? "seam" : "";
    return entry.kind === "model" && entry.entity.modelKind === ownKind
      ? [...entry[dimension], entry.entity["@id"]] : entry[dimension];
  }

  function passesShared(entry, state, skip) {
    if (state.q && !FG.fold(state.q).split(/\s+/).every((word) => FG.fold(entry.text).includes(word))) return false;
    if (skip !== "station" && state.stations.length && !entry.stations.some((station) => state.stations.includes(station))) return false;
    if (skip !== "principle" && state.principles.length && !entry.principles.some((principle) => state.principles.includes(principle))) return false;
    for (const key of ["layers", "seams"]) if (skip !== key && state[key]?.length && !sharedValues(entry, key).some((id) => state[key].includes(id))) return false;
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
    infrastructures: ["field", "name"],
    clauses: ["source", "principle", "station"],
    questions: ["check", "principle", "station"],
    terms: ["name", "nameEn"],
    fips: ["name"],
    tests: ["check", "principle", "name"],
    lifecycle: ["guided", "name"],
    model: ["guided", "name"],
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
    if (order === "field") return byFacet("field", FG.refIds(FG.get("#research-fields"), "hasDefinedTerm"), "");
    if (order === "rsource") return byFacet("rsource", ["#repositories-curated", "#snapshot-re3data", "#snapshot-nkr", "#snapshot-fairsharing", "#snapshot-datacite", "#snapshot-fip-dashboard"], "");
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
    /* Terms by name read as an index: one group per initial letter in the language's alphabet, so Č follows C and
       Ch follows H in Czech; anything that does not start with a letter gathers under "#". */
    if ((order === "name" || order === "nameEn") && entries.length && entries.every((entry) => entry.kind === "terms")) {
      const lang = order === "nameEn" ? "en" : "cs";
      const collator = new Intl.Collator(lang, { sensitivity: "base" });
      const nameOf = (entry) => (order === "nameEn" ? entry.nameEn || entry.name : entry.name);
      const letterOf = (entry) => {
        const name = String(nameOf(entry)).trim();
        if (lang === "cs" && /^ch/i.test(name)) return "Ch";
        return /^\p{L}/u.test(name) ? name.charAt(0).toLocaleUpperCase(lang) : "#";
      };
      const groups = new Map();
      for (const entry of entries) groups.set(letterOf(entry), (groups.get(letterOf(entry)) || []).concat(entry));
      const letters = [...groups.keys()].sort((a, b) => (a === "#" ? 1 : b === "#" ? -1 : lang === "cs" && (a === "Ch" || b === "Ch") ? chRank(a, b, collator) : collator.compare(a, b)));
      return letters.map((letter) => ({ key: "letter-" + letter, letter, anchor: "letter-" + encodeURIComponent(letter), label: letter, entries: groups.get(letter).sort((a, b) => collator.compare(nameOf(a), nameOf(b))) }));
    }
    const sorted = entries.slice();
    if (order === "guided") sorted.sort(withinKind);
    else if (order === "newest") sorted.sort((a, b) => String(b.date).localeCompare(String(a.date)));
    else if (order === "oldest") sorted.sort((a, b) => String(a.date).localeCompare(String(b.date)));
    else if (order === "nameEn") sorted.sort((a, b) => FG.fold(a.nameEn || a.name).localeCompare(FG.fold(b.nameEn || b.name), "en"));
    else sorted.sort(byName);
    return [{ key: "all", label: null, entries: sorted }];
  }

  /* In Czech, Ch is a letter of its own between H and I. */
  const chRank = (a, b, collator) => {
    const place = (letter) => (letter === "Ch" ? ["H", 1] : [letter, 0]);
    const [left, leftAfter] = place(a);
    const [right, rightAfter] = place(b);
    return collator.compare(left, right) || leftAfter - rightAfter;
  };

  /** The letters of an index as a row of jumps, each moving to its group. */
  function letterIndex(groups) {
    const jump = (group) => {
      if (!expanded.has(group.key)) { expanded.add(group.key); FG.focusAfterRender = false; FG.render(); }
      const section = document.getElementById(group.anchor);
      if (!section) return;
      section.scrollIntoView({ block: "start" });
      const heading = section.querySelector("h2");
      if (heading) heading.focus({ preventScroll: true });
    };
    return h(
      "nav",
      { class: "letter-index", "aria-label": FG.t("catalogue.letters") },
      h("ul", null, groups.map((group) => h("li", null, h("button", { type: "button", class: "letter-jump", "aria-label": FG.t("catalogue.toLetter", { letter: group.letter }), onclick: () => jump(group) }, group.letter))))
    );
  }

  /* ---------------------------------------------------------------- the view */

  /** A facet as a group of checkboxes with counts; values past the first few open on request. */
  function facetGroup(name, legend, values, chosen, counts, labelOf, onToggle) {
    const open = openFacets.has(name);
    const shown = open || name === "station" ? values : values.filter((value, index) => index < SHOWN_VALUES || chosen.includes(value));
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
            h(
              "label",
              { for: id, class: "kind-" + kind },
              h("span", { class: "kind-mark", "aria-hidden": "true" }, FG.icon((icons().kind || {})[kind])),
              h("span", { class: "facet-label" }, FG.t("catalogue.tab." + kind)),
              h("span", { class: "facet-count" }, String(count))
            ),
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
      /* NKR, FAIRsharing and DataCite come with the page, refreshed by a scheduled workflow; nothing is loaded here. */
      const all = FG.repositoryEntries();
      const recorded = all.filter((repository) => FG.refIds(repository, "isBasedOn").includes("#snapshot-fairsharing")).length;
      const snapshot = FG.get("#snapshot-fairsharing");
      return h(
        "div",
        { class: "kind-intro" },
        h("p", { class: "small" }, intro),
        FG.dashboardNotice(),
        snapshot ? h("p", { class: "small" }, FG.t("repositories.fairsharingNote", { n: recorded, total: all.length, date: FG.formatDate(snapshot.dateCreated) })) : null,
        FG.live.nkrNote(),
        nodeNote()
      );
    }
    return h(
      "div",
      { class: "kind-intro" },
      h("p", { class: "small" }, intro),
      kind === "fips" || kind === "resources" || kind === "repositories" ? FG.dashboardNotice() : null,
      kind === "resources" || kind === "infrastructures" ? nodeNote() : null
    );
  }

  /** What the EOSC CZ Node is, where its badges show: a candidate node of the EOSC Federation since its approval,
      with the announcement that says so (D-172). */
  function nodeNote() {
    const node = FG.get("#eosc-cz-node");
    if (!node || !node.nodeStateSince) return null;
    const sources = FG.refs(node, "isBasedOn");
    const source = sources[1] || sources[0];
    return h("p", { class: "small" }, FG.t("node.candidate", { date: FG.formatDate(node.nodeStateSince) }), source ? [" ", sourceLink(source)] : null);
  }

  FG.views.catalogue = function (route) {
    route = { ...route, arg: FG.catalogueKind(route.arg) };
    const state = readState(route);
    const entries = allEntries();
    // API-backed catalogue records outside the faceted lists (for example an organisation or the model itself)
    // remain directly addressable from prose, with the same record address and shared entry card.
    if (route.extra && !Object.values(entries).flat().some((entry) => entry.kind + "/" + entry.anchor === route.arg + "/" + route.extra)) {
      const record = Object.entries(FG.config.api.records).find(([, address]) => address === FG.catalogueCode(route.arg) + "/" + route.extra);
      const entity = record && FG.get(record[0]);
      if (entity) return h("div", { class: "catalogue wrap" }, FG.heading(1, null, FG.t("catalogue.title")),
        h("p", { class: "single-entry small" }, FG.t("catalogue.single", { id: route.extra })),
        h("ul", { class: "catalogue-results cards" }, entryCard({ kind: route.arg, id: route.extra, entity,
          title: entity.url ? FG.external(entity.url, FG.span(entity.name || entity.headline || entity.identifier)) : FG.span(entity.name || entity.headline || entity.identifier),
          body: [FG.paragraphs(entity.description || entity.text), FG.modelDetail(entity)],
          relations: { basedOn: FG.refs(entity, "citation").map(FG.sourceLink) }
        })));
    }
    const go = (next, focus) => FG.replaceInPlace(writeState(next), focus);
    const toggle = (list, value) => (list.includes(value) ? list.filter((item) => item !== value) : list.concat(value));

    /* A link to one entry shows its kind unfiltered, so the entry is there. */
    if (route.extra) Object.assign(state, { stations: [], principles: [], layers: [], seams: [], q: "", f: { lens: [] } });

    const kind = state.kinds[0];
    const selected = [kind];
    const inKinds = entries[kind];
    /* A link to one entry shows that entry alone, with the way to the whole kind; an anchor no entry has shows the
       kind with a note. */
    const single = route.extra ? inKinds.filter((entry) => entry.anchor === route.extra) : [];
    const visible = single.length ? single : inKinds.filter((entry) => passesShared(entry, state) && passesKind(entry, state, route));
    /* A shared dimension the chosen kind has no values for shows no facet and no order, unless a filter on it is
       active, so that it can be cleared where it was set. */
    const carries = (dimension) => entries[kind].some((entry) => sharedValues(entry, dimension).length);
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
    const lacks = (kind, dimension) => !entries[kind].some((entry) => sharedValues(entry, dimension).length);
    const sharedCounts = (dimension, skip) => {
      const counts = new Map();
      for (const entry of inKinds.filter((item) => passesShared(item, state, skip) && passesKind(item, state, route))) {
        for (const value of new Set(sharedValues(entry, dimension))) counts.set(value, (counts.get(value) || 0) + 1);
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
    const kindFacet = (own, facet) => {
      const counts = kindFacetCounts(own, facet.key);
      const natural = facet.values ? facet.values() : [...counts.keys()].sort((a, b) => FG.fold(facet.label(a)).localeCompare(FG.fold(facet.label(b)), "cs"));
      const values = natural.slice().sort((a, b) => (counts.get(b) || 0) - (counts.get(a) || 0));
      const chosen = chosenValues(state, route, facet.key);
      const group = facetGroup(own + "-" + facet.key, FG.t("catalogue.facet." + facet.key), values, chosen, counts, facet.label, (value, focus) =>
        go(Object.assign({}, state, { f: Object.assign({}, state.f, { [facet.key]: toggle(chosen, value) }) }), focus)
      );
      return [group, facet.note ? h("p", { class: "facet-note small muted" }, FG.t(facet.note)) : null];
    };
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
      ["layers", "seams"].map((dimension) => carries(dimension) || state[dimension].length ? facetGroup(dimension, FG.t("catalogue.facet." + dimension),
        FG.modelTerms(dimension === "layers" ? "layer" : "seam").map((term) => term["@id"]), state[dimension], sharedCounts(dimension, dimension),
        (id) => FG.text(FG.get(id)?.name) || id, (id, focus) => go(Object.assign({}, state, { [dimension]: toggle(state[dimension], id) }), focus)) : null),
      selected.map((own) => {
        const ownFacets = KIND_FACETS[own] || [];
        if (!ownFacets.length) return null;
        return h(
          "div",
          { class: "facet-kind" },
          h("p", { class: "facet-kind-name" }, FG.t("catalogue.tab." + own)),
          ownFacets.map((facet) => kindFacet(own, facet))
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
    for (const dimension of ["layers", "seams"]) for (const id of state[dimension]) chip(FG.text(FG.get(id)?.name) || id, Object.assign({}, state, { [dimension]: state[dimension].filter((value) => value !== id) }));
    for (const facet of KIND_FACETS[kind] || []) {
      const chosen = chosenValues(state, route, facet.key);
      for (const value of chosen) chip(FG.t("catalogue.facet." + facet.key) + ": " + facet.label(value), Object.assign({}, state, { f: Object.assign({}, state.f, { [facet.key]: chosen.filter((item) => item !== value) }) }));
    }

    const groups = groupsFor(order, visible);
    offerListExports(kind, groups);
    const used = new Set();
    let remaining = PAGE;
    const results = groups.map((group) => {
      const shown = expanded.has(group.key) ? group.entries : group.entries.slice(0, remaining);
      remaining = Math.max(0, remaining - shown.length);
      const all = shown.length === group.entries.length;
      const cards = shown.map((entry) => {
        const node = entry.render();
        if (node.id && used.has(node.id)) node.removeAttribute("id");
        else used.add(node.id);
        return node;
      });
      return h(
        "section",
        { class: "catalogue-group", id: group.anchor || null },
        group.label && !single.length ? h("h2", { tabindex: group.anchor ? "-1" : null }, group.label, h("span", { class: "muted group-count" }, " · " + FG.t("catalogue.entries", { n: group.entries.length }))) : null,
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
              FG.t("catalogue.more", { n: group.entries.length - shown.length })
            )
      );
    });
    if (route.extra) {
      const whole = h("a", { href: FG.catalogueHref(kind), class: "single-all" }, FG.t("catalogue.showAll", { kind: FG.t("catalogue.tab." + kind), n: entries[kind].length }));
      const note = h("p", { class: "single-entry small" }, FG.t(single.length ? "catalogue.single" : "catalogue.singleMissing", { id: route.extra }), " ", whole);
      /* One entry keeps only the notice its record needs: the FIP Dashboard disclaimer for a dashboard record. */
      const dashboard = single.length && (kind === "fips" || FG.list(single[0].facets.use).includes("dashboard"));
      results.unshift(note, single.length ? (dashboard ? FG.dashboardNotice() : null) : kindIntro(kind));
    } else results.unshift(kindIntro(kind), groups.some((group) => group.letter) && groups.length > 1 ? letterIndex(groups) : null);

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
                h("button", { type: "button", class: "button-link small", onclick: () => go({ kinds: selected, stations: [], principles: [], layers: [], seams: [], q: "", order: state.order, f: { lens: [] } }, "#catalogue-search") }, FG.t("catalogue.clear"))
              )
            : null,
          results
        )
      )
    );
  };
})();
