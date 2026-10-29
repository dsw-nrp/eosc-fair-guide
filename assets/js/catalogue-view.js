/* Catalogue of the FAIR Data Guide: one list of everything in the knowledge base, narrowed by facets with counts.
   Kind is a single choice that shows every kind with its count; search, station and principle apply across kinds
   and stay when the kind changes; a facet that belongs to one kind is labelled with it. The reader chooses the ordering, groups follow it, and the
   whole state is part of the address, so a filtered list is a link. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);
  const { audiences, basedOnRow, citationDetails, citations, code, declaredInRow, developerRow, entryCard, entryLink, field, icons, inGuide, licenceRow, operatorRow, resourceCard, serviceOf, slug, snapshotItem, sourceLink, stationsOf, tiles, typeOf, uses, writeState } = FG.catalogueParts;

  const KINDS = ["resources", "repositories", "infrastructures", "clauses", "questions", "terms", "fips", "tests", "lifecycle", "model", "actions"];

  /* What each kind's entry shows of its record, and what it leaves out with the reason (design D8). The catalogue's
     completeness test fails when a record carries a field its kind neither shows nor excludes, and when a shown field
     with a value draws nothing; a card marks what it draws with `data-field`. */
  const NOT_SHOWN = {
    "@id": "the record's own address, which the entry's API link leads to",
    "@type": "the record's type, which the entry's kind and what-line name",
    catalogueAddress: "the entry's address, which its ID chip shows",
    identifier: "the entry's local ID, which its ID chip shows",
    alternateIdentifier: "a source system's key for joining an imported record; persistent identifiers show under Identifiers",
  };
  const SHOWN = ["implementationLayers", "implementationSeams"];
  const SCHEMA_SUBTYPE = "a schema.org or FIP class for machine readers; the entry's type names what it is";
  const ORDER = "orders the entry within its group; the list follows that order";
  const FIELDS = {
    resources: {
      shown: ["about", "alternateName", "audience", "author", "catalogueType", "creditText", "dateModified", "datePublished", "description", "discipline", "guideType", "inLanguage", "isBasedOn", "license", "lifecycleStage", "mentions", "name", "nodeMembership", "operatedBy", "operatedBySource", "operatorSource", "preparationStatus", "provider", "publisher", "rdmkitRecord", "resourceType", "review", "sameAs", "sdDatePublished", "serviceStatus", "spatialCoverage", "statusAsOf", "trainingSearch", "url", "version"],
      excluded: { additionalType: SCHEMA_SUBTYPE },
    },
    repositories: {
      shown: ["abbreviation", "about", "alternateName", "attributedTo", "audience", "catalogueType", "description", "developerSource", "guideType", "inLanguage", "isBasedOn", "keywords", "mentions", "name", "nodeMembership", "operatedBy", "operatedBySource", "operatorSource", "provider", "publisher", "rdmkitRecord", "repositoryFunction", "repositoryKind", "resourceType", "review", "sameAs", "sdDatePublished", "serviceStatus", "spatialCoverage", "statusAsOf", "trainingSearch", "url"],
      excluded: { additionalType: SCHEMA_SUBTYPE },
    },
    infrastructures: {
      shown: ["abbreviation", "esfriStatus", "infrastructureCharacter", "infrastructurePhase", "isBasedOn", "memberOf", "name", "nationalNodeOf", "operates", "publisher", "researchField", "roadmapLocator", "roadmapSince", "sameAs", "subjectOf", "url"],
      excluded: {},
    },
    clauses: {
      shown: ["about", "audience", "citation", "clauseKind", "creativeWorkStatus", "guidance", "isPartOf", "mentions", "name", "note", "sourceLocator", "supersededBy", "text"],
      excluded: {},
      /* Values that draw nothing on purpose: a reader sees only a superseded requirement marked. */
      defaults: { creativeWorkStatus: { values: ["current", "refresh"], reason: "a current requirement shows no badge, and a refresh is an editorial task; only a superseded one is marked" } },
    },
    questions: {
      shown: ["about", "additionalProperty", "allowsNotApplicable", "appliesTo", "assessmentContext", "block", "championEvidenceOnly", "citation", "description", "fixAt", "fixedBy", "isPartOf", "lookup", "mentions", "name", "note", "prefillLevel", "providedByNrpFor", "text", "tier"],
      excluded: { position: ORDER },
    },
    terms: {
      shown: ["description", "license", "name", "subjectOf", "url"],
      excluded: { inDefinedTermSet: "every term belongs to Heslář, which the entry's what-line names", termCode: "the term's number in Heslář, whose page the title links" },
    },
    fips: {
      shown: ["abstract", "alternateName", "author", "creativeWorkStatus", "dateModified", "hasPart", "isBasedOn", "keywords", "name", "review", "sameAs", "url", "version"],
      excluded: { additionalType: SCHEMA_SUBTYPE },
    },
    tests: {
      shown: ["about", "additionalProperty", "alternateName", "citation", "description", "hasPart", "healthStatus", "isImplementationOf", "isPartOf", "name", "reviewedVersion", "statusAsOf", "subjectOf", "url"],
      excluded: { additionalType: SCHEMA_SUBTYPE },
    },
    lifecycle: {
      shown: ["citation", "description", "descriptionTranslation", "inDefinedTermSet", "license", "name", "nameTranslation", "note", "quotedDefinition"],
      excluded: { position: ORDER, termCode: "the stage's code in its model, which its ID carries" },
    },
    model: {
      shown: ["carrier", "citation", "description", "hasPart", "maintainers", "modelKind", "name", "recipient", "sender", "transfer"],
      excluded: { inDefinedTermSet: "every term belongs to the implementation model, which the entry's what-line names", position: ORDER, termCode: "the term's code, which its ID carries" },
    },
    actions: {
      shown: ["agent", "description", "endTime", "instrument", "name", "object", "result"],
      excluded: { actionStatus: "every recorded change is completed, so the status distinguishes nothing" },
    },
  };
  /* Records with an address but no list of their own: each has its own view, or shows inside another entry. */
  const OUTSIDE_LISTS = {
    check: "a check is the self-check's own view",
    step: "a station is the path's own view",
    pr: "a principle is the principle explorer's own view",
    org: "an organisation shows where an entry names it, and on the About page",
  };
  /* Records of a listed kind that are not entries themselves, by type: each shows inside the entries named. */
  const WITHIN = {
    lifecycle: { DefinedTermSet: "a life-cycle model shows in the what-line of each of its stages", CreativeWork: "a correspondence shows in the Corresponds to row of both its stages" },
    model: { DefinedTermSet: "the implementation model is its own page", CreativeWork: "an implementation example shows inside the seam it illustrates" },
  };
  FG.catalogueFields = { kinds: FIELDS, notShown: NOT_SHOWN, shown: SHOWN, outside: OUTSIDE_LISTS, within: WITHIN };
  const sourceKey = (source, id) => source + "." + id;
  /* Values shown before "more"; the path's steps always show in full. */
  const SHOWN_VALUES = 9;
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
        titleFields: "name url",
        details: [field("discipline", FG.list(tool.discipline).map((value) => FG.t("catalogue.discipline." + value)).join(", ") || null)],
        body: [
          h("p", { lang: "en", "data-field": "description" }, FG.text(tool.description)),
          /* The description is the catalogue's own text, under the catalogue's licence. */
          FG.quoteLicence(tool.license, "license"),
          tool.url ? null : h("p", { class: "small" }, FG.t("catalogue.knavHttp") + " ", FG.external(catalogue.url, FG.t("catalogue.use.knav"))),
          steps.length ? h("p", { class: "small", "data-field": "lifecycleStage" }, h("span", { class: "entry-what" }, FG.t("catalogue.knavSteps") + ": "),
            steps.map((stage, index) => [index ? ", " : null, h("a", { href: FG.entryHref(stage) }, FG.span(stage.name))])) : null,
        ],
        relations: { basedOn: [source ? FG.sourceLink(source) : null, FG.refs(tool, "isBasedOn").map(snapshotItem)], inGuide: inGuide(holders) },
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
            what: [field("guideType", FG.termName(typeOf(source)))].concat(uses(used)),
            title: url ? FG.external(url, FG.nameNodes(source)) : FG.nameNodes(source),
            titleFields: "name url",
            /* Who wrote the work: its credit line, or its authors by name. */
            byline: source.creditText || FG.refs(source, "author").map((person) => FG.text(person.name)).join(", ") || null,
            bylineFields: "creditText author",
            details: citationDetails(source),
            relations: { license: licenceRow(source), inGuide: inGuide(citedBy), identifiers: FG.identifierItems(source) },
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
            what: [field("guideType", FG.termName(typeOf(fer)))].concat(uses(used)),
            title: FG.external(fer.url || FG.refIds(fer, "sameAs")[0], fer.name),
            titleFields: "name url",
            /* What kind of FAIR-enabling resource it is and where it applies, as the FIP Dashboard records them. */
            details: [
              field("alternateName", fer.alternateName ? FG.text(fer.alternateName) : null),
              field("catalogueType", FG.id(fer.catalogueType) ? FG.t("catalogue.fairDataType", { type: FG.termName(FG.id(fer.catalogueType)) }) : null),
              field("spatialCoverage", fer.spatialCoverage ? FG.t("catalogue.spatial." + fer.spatialCoverage) : null),
            ],
            body: fer.description ? h("p", { "data-field": "description" }, FG.span(fer.description)) : null,
            states: FG.verificationBadges(fer),
            relations: {
              principles: tiles(FG.principlesOf(fer)),
              providedBy: FG.refs(fer, "provider").map((party) => (party.url ? FG.external(party.url, FG.abbreviatedName(party, FG.state.lang)) : h("span", null, FG.abbreviatedName(party, FG.state.lang)))),
              declaredIn: declaredInRow(fer),
              basedOn: FG.refs(fer, "isBasedOn").map(snapshotItem),
              identifiers: FG.identifierItems(fer),
            },
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
      const researchField = FG.id(infra.researchField);
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
        text: [FG.nameForms(infra), FG.partyName(infra, "publisher"), nodes.map((ri) => ri.name).join(" "), erics.map((eric) => eric.name).join(" ")].join(" "),
        stations: [],
        principles: [],
        order: FG.fold(infra.abbreviation || FG.text(infra.name)),
        facets: { field: researchField ? [researchField] : [], riphase: phase ? [phase] : [], esfri: FG.refIds(infra, "esfriStatus") },
        render: () =>
          entryCard({ kind: "infrastructures",
            id: infra.identifier,
            entity: infra,
            service: { identifier: "infrastructure-" + infra.identifier },
            what: [field("researchField", researchField ? categoryLabel(researchField) : null), field("infrastructurePhase", phase ? categoryLabel(phase) : null)],
            title: infra.url ? FG.external(infra.url, name) : name,
            titleFields: "name abbreviation url",
            /* The host is who operates the infrastructure, in the Operated by row as for every kind (design D8). */
            details: [otherName(infra), field("roadmapSince", FG.t("infrastructure.since", { year: infra.roadmapSince })), field("infrastructureCharacter", character ? categoryLabel(character) : null)],
            states: FG.refIds(infra, "esfriStatus").map((id) => h("span", { class: "badge", "data-field": "esfriStatus" }, FG.termName(id))),
            fields: { basedOn: "isBasedOn roadmapLocator" },
            relations: {
              operatedBy: operatorRow(infra),
              operates: FG.refs(infra, "operates").map(entryLink),
              identifiers: FG.identifierItems(infra),
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
        render: () => {
          /* A repository the FIP Dashboard lists is described there by its enabling-resource record; one that is such a
             record itself carries those facts on its own entry. */
          const fer = record && record.fer ? record.fer : String(repository["@id"]).startsWith("#fer-") ? repository : null;
          const languages = FG.list(repository.inLanguage).map(String);
          return entryCard({ kind: "repositories",
            id: anchor,
            entity: repository,
            service: { identifier: repository["@id"].replace(/^#(resource|repository)-/, ""), name: repository.name, url: repository.url },
            what: [field("repositoryFunction", functions.map(FG.termName).join(" · ") || null),
              field("repositoryKind", FG.id(repository.repositoryKind) ? FG.termName(FG.id(repository.repositoryKind)) : null),
              field("resourceType guideType", typeOf(repository) ? FG.termName(typeOf(repository)) : null)].concat(uses(used)),
            title: FG.external(repository.url, FG.abbreviatedName(repository, FG.state.lang)),
            titleFields: "name abbreviation url",
            /* The name in the other language stays on the entry (D-173). */
            details: [
              field("alternateName", repository.alternateName && !repository.abbreviation ? FG.text(repository.alternateName) : null),
              otherName(repository),
              field("keywords", FG.subjectsOf(repository).join(", ") || null),
              field("inLanguage", languages.length ? FG.t("resource.languages", { languages: languages.join(", ") }) : null),
              field("catalogueType", FG.id(repository.catalogueType) ? FG.t("catalogue.fairDataType", { type: FG.termName(FG.id(repository.catalogueType)) }) : null),
              field("spatialCoverage", repository.spatialCoverage ? FG.t("catalogue.spatial." + repository.spatialCoverage) : null),
              field("sdDatePublished", repository.sdDatePublished ? FG.t("catalogue.accessed", { date: FG.formatDate(repository.sdDatePublished) }) : null),
            ],
            body: [repository.description ? h("p", { "data-field": "description mentions" }, FG.linkedSpan(repository, "description")) : null, dataciteBlock(repository, anchor)],
            states: [FG.statusBadge(repository), FG.nodeBadge(repository), fer ? FG.verificationBadges(fer) : null],
            fields: { basedOn: "isBasedOn rdmkitRecord trainingSearch" },
            relations: {
              principles: fer ? tiles(FG.principlesOf(fer)) : [],
              operatedBy: operatorRow(repository),
              developedBy: developerRow(repository),
              providedBy: FG.refs(repository, "provider").map((party) => (party.url ? FG.external(party.url, FG.abbreviatedName(party, FG.state.lang)) : h("span", null, FG.abbreviatedName(party, FG.state.lang)))),
              declaredIn: declaredInRow(fer),
              basedOn: [FG.repositorySourceLinks(repository), repository.rdmkitRecord ? FG.external(repository.rdmkitRecord, "RDMkit") : null, repository.trainingSearch ? FG.external(repository.trainingSearch, FG.t("catalogue.trainingSearch")) : null],
              audience: audiences(FG.refIds(repository, "audience")),
              inGuide: inGuide(holders),
              identifiers: FG.identifierItems(repository),
            },
          });
        },
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
            what: clause.clauseKind ? field("clauseKind", FG.t("catalogue.clauseKind." + clause.clauseKind)) : null,
            title: FG.clauseTitle(clause) ? FG.span(FG.clauseTitle(clause)) : null,
            body: [h("p", { "data-field": "text mentions" }, FG.linkedSpan(clause)), FG.guidance(clause)],
            states: status === "superseded" ? field("creativeWorkStatus", FG.clauseStatus(status)) : null,
            /* What has changed since the source was published, with the requirements that say so. */
            notes: clause.note
              ? h("p", { class: "small clause-note" }, h("span", { "data-field": "note" }, FG.span(clause.note)),
                  FG.refs(clause, "citation").length ? h("span", { "data-field": "citation" }, " (", FG.refs(clause, "citation").map((item, index) => [index ? ", " : null, FG.recordLink(item)]), ")") : null)
              : null,
            fields: { basedOn: "isPartOf sourceLocator" },
            relations: {
              principles: tiles(FG.principlesOf(clause)),
              audience: audience ? h("span", { class: "audience" }, FG.category(FG.termName(audience))) : null,
              /* The works behind a requirement without a note follow its source; with a note they support the note. */
              basedOn: source ? [sourceLink(source), clause.sourceLocator ? h("span", { class: "muted" }, " · " + clause.sourceLocator) : null,
                !clause.note && FG.refs(clause, "citation").length ? h("span", { "data-field": "citation" }, "; ", FG.refs(clause, "citation").map((item, index) => [index ? ", " : null, FG.recordLink(item)])) : null] : null,
              replacedBy: FG.refs(clause, "supersededBy").map(FG.recordLink),
              replaces: (FG.reverseRelations().replaces.get(clause["@id"]) || []).map(FG.recordLink),
              inGuide: inGuide(holders),
            },
          }),
      };
    });
  }

  /** Where a question's suggested answer comes from: the records and fields the self-check reads, the FAIR Champion
      tests, the Guide's own tests and the evaluators' criteria mapped to it, each with how much it covers. */
  function prefillSources(item) {
    const own = FG.refs(item, "additionalProperty")
      .filter((property) => String(property.propertyID).startsWith("prefill:"))
      .flatMap((property) => {
        const source = String(property.propertyID).slice("prefill:".length);
        if (source === "champion") {
          return FG.list(property.value).map((value) => {
            const test = FG.sourceEntity("fair-champion", String(value), "#test-");
            return [FG.t("catalogue.prefill.champion") + ": ", test ? FG.recordLink(test) : h("code", null, String(value))];
          });
        }
        return [[FG.t("catalogue.prefill." + source), typeof property.value === "string" ? [" · ", h("code", null, property.value)] : null]];
      });
    const reverse = (FG.reverseRelations().prefilledBy.get(item["@id"]) || []).map(({ entity, coverage }) => [
      FG.recordLink(entity),
      coverage ? h("span", { class: "muted" }, " · " + FG.t("catalogue.coverage." + coverage)) : null,
    ]);
    const limits = [item.prefillLevel === "partly" ? FG.t("catalogue.prefillPartly") : null, item.championEvidenceOnly ? FG.t("catalogue.championOnly") : null].filter(Boolean);
    const items = own.concat(reverse);
    if (!items.length && !limits.length) return [];
    return [FG.relationGroups([{ items, render: (entry) => entry }]), limits.length ? h("p", { class: "small muted" }, limits.join(" · ")) : null];
  }

  /** When a question applies: the check modes and NRP profiles it is asked in, and whether "not applicable" is
      offered. */
  function appliesRow(item) {
    const refs = FG.refIds(item, "appliesTo");
    const modes = refs.filter((id) => id.startsWith("#mode-")).map((id) => FG.t("catalogue.mode." + id.replace("#mode-", "")));
    const profiles = refs.filter((id) => id.startsWith("#profile-")).map(FG.termName);
    return [
      h("span", null, modes.length || profiles.length ? modes.concat(profiles).join(", ") : FG.t("catalogue.appliesAlways")),
      h("span", { class: "muted" }, " · " + FG.t(item.allowsNotApplicable ? "catalogue.notApplicableOffered" : "catalogue.notApplicableNot")),
    ];
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
                what: FG.id(item.tier) ? field("tier", FG.category(FG.id(item.tier) === "#tier-basic" ? FG.t("catalogue.tierBasic") : FG.termName(FG.id(item.tier)))) : null,
                body: [
                  h("p", { "data-field": "text mentions" }, FG.linkedSpan(item)),
                  item.description ? h("div", { class: "small muted question-explanation", "data-field": "description" }, FG.linkedParagraphs(item, "description")) : null,
                  item.assessmentContext ? h("p", { class: "small", "data-field": "assessmentContext" }, FG.t("selfcheck.question.context") + ". " + FG.t("selfcheck.question.contextHint")) : null,
                  item.lookup ? h("p", { class: "small", "data-field": "lookup" }, FG.t("catalogue.lookup") + ": ", FG.external(FG.id(item.lookup), FG.id(item.lookup))) : null,
                  item.note ? h("p", { class: "small", "data-field": "note" }, FG.span(item.note)) : null,
                ],
                fields: { basedOn: "citation", inGuide: "isPartOf fixAt" },
                relations: {
                  principles: tiles(FG.principlesOf(item)),
                  fixedBy: FG.refIds(item, "fixedBy").length ? [FG.refIds(item, "fixedBy").map(FG.termName).join(", "), item.fixAt ? [h("span", { class: "muted" }, " · "), h("a", { href: FG.href("path", station) }, FG.span(FG.get(item.fixAt).name))] : null] : [],
                  applies: appliesRow(item),
                  group: FG.id(item.block) ? FG.span(FG.get(FG.id(item.block))?.name || FG.id(item.block)) : [],
                  nrpProfile: FG.refIds(item, "providedByNrpFor").map(FG.termName).join(", ") || [],
                  prefilledFrom: prefillSources(item),
                  basedOn: clauses.map((clause) => FG.idChip(clause)),
                  mentions: FG.refs(item, "mentions").map(FG.recordLink),
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
            titleFields: "name url",
            details: en,
            detailsLang: "en",
            /* Definitions retain the source's language; no English translation is invented. */
            body: [
              term.description ? h("details", { class: "term-definition", open: Boolean(FG.parseHash(window.location.hash).extra), "data-field": "description" },
                h("summary", null, FG.t("catalogue.termDefinition")), h("div", { class: "content" }, FG.paragraphs(term.description))) : null,
              FG.refs(term, "subjectOf").filter((clause) => clause.guidance).map((clause) => h("details", { "data-field": "subjectOf" },
                h("summary", null, FG.t("catalogue.originalDefinition", { source: FG.shortText(FG.get(clause.isPartOf)) })),
                h("div", { class: "content" }, h("p", null, FG.sourceLink(FG.get(clause.isPartOf)), clause.sourceLocator ? " · " + clause.sourceLocator : ""),
                  h("blockquote", null, FG.paragraphs(clause.guidance))))),
              /* The definition is Heslář's text, under the licence its record names (design D8). */
              FG.quoteLicence(term.license, "license"),
            ],
            relations: { inGuide: inGuide(at), identifiers: FG.identifierItems(term) },
          }),
      };
    });
  }

  /** A FIP profile's declarations in principle order, with a summary by status. */
  function declarationsOf(fip) {
    const declarations = FG.refs(fip, "hasPart").slice().sort((a, b) => FG.principleOrder(FG.principlesOf(a)[0] || {}, FG.principlesOf(b)[0] || {}));
    const counts = new Map();
    for (const declaration of declarations) counts.set(declaration.creativeWorkStatus, (counts.get(declaration.creativeWorkStatus) || 0) + 1);
    const summary = FG.t("catalogue.declarations", { n: declarations.length }) + ": " + [...counts].map(([status, n]) => FG.t("catalogue.declarationCount." + status, { n })).join(", ");
    return { declarations, summary };
  }

  /** The declarations as a table of principle, enabling resource (leading to its entry), status and note. */
  function declarationsTable(declarations) {
    const columns = ["principle", "resource", "status", "note"];
    return h("div", { class: "text-table-scroll", role: "region", tabindex: "0", "aria-label": FG.t("catalogue.relation.declarations") },
      h("table", { class: "text-table declarations-table" },
        h("thead", null, h("tr", null, columns.map((column) => h("th", { scope: "col" }, FG.t("catalogue.declarationColumn." + column))))),
        h("tbody", null, declarations.map((declaration) => h("tr", null,
          h("td", null, FG.principlesOf(declaration).map((principle) => FG.principleTile(principle))),
          h("td", null, FG.refs(declaration, "mentions").map((fer, index) => [index ? ", " : null, FG.recordLink(fer)])),
          h("td", null, FG.declarationBadge(declaration.creativeWorkStatus)),
          h("td", null, declaration.description ? FG.span(declaration.description) : null))))));
  }

  /** A FIP profile's declarations on its card: across the card's width, folded behind the summary and built when a
      reader first opens them, with the way to the same table on a page of its own. */
  function declarationsRow(fip, anchor) {
    const { declarations, summary } = declarationsOf(fip);
    if (!declarations.length) return [];
    let built = false;
    const label = FG.t("catalogue.declarationsFull");
    /* The box's header carries the way to the full page, beside the summary rather than inside it, so opening the box
       and following the link stay two separate controls. */
    return h("div", { class: "relation-group fold-box" },
      h("details", { class: "relation-fold declarations", ontoggle: (event) => {
        if (!event.target.open || built) return;
        built = true;
        event.target.append(declarationsTable(declarations));
      } }, h("summary", null, summary)),
      FG.external(FG.catalogueHref("fips", anchor + "/" + DECLARATIONS_PAGE), [FG.icon("fullPage"), h("span", { class: "visually-hidden" }, label)], { class: "fold-action", title: label }));
  }

  /* The last part of a FIP profile's address that shows its declarations on a page of their own. */
  const DECLARATIONS_PAGE = "declarations";

  /** A FIP profile's declarations on a page of their own, at the page's full width, for reading the whole table. */
  function declarationsPage(entry) {
    const { declarations, summary } = declarationsOf(entry.entity);
    return h("div", { class: "catalogue catalogue-table-page" },
      FG.heading(1, null, FG.t("catalogue.declarationsOf", { name: FG.text(entry.entity.name) })),
      h("p", { class: "small" }, h("a", { href: FG.entryHref(entry.entity) }, FG.t("catalogue.backToEntry")), " · " + summary),
      declarationsTable(declarations));
  }

  function fipEntries() {
    return FG.refs(FG.get("#fips"), "hasPart").map((fip) => {
      const url = FG.refIds(fip, "sameAs")[0] || fip.url;
      const community = FG.get(FG.id(fip.author));
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
            titleFields: "name sameAs",
            /* The community that authored the profile, leading to the address the profile names for it. */
            byline: community ? (fip.url ? FG.external(fip.url, FG.abbreviatedName(community, FG.state.lang)) : FG.abbreviatedName(community, FG.state.lang)) : null,
            bylineFields: "author url",
            details: [
              field("alternateName", fip.alternateName),
              field("creativeWorkStatus", fip.creativeWorkStatus ? FG.t("catalogue.fipStatus." + fip.creativeWorkStatus) : null),
              field("version", fip.version ? FG.t("catalogue.version", { version: fip.version }) : null),
              field("dateModified", fip.dateModified ? FG.t("catalogue.modified", { date: FG.formatDate(String(fip.dateModified).slice(0, 10)) }) : null),
              field("keywords", FG.subjectsOf(fip).join(", ") || null),
            ],
            body: fip.abstract ? h("p", { "data-field": "abstract" }, FG.span(fip.abstract)) : null,
            states: FG.verificationBadges(fip),
            fields: { basedOn: "isBasedOn" },
            relations: {
              declarations: declarationsRow(fip, FG.config.api.records[fip["@id"]].split("/").slice(1).join("/")),
              basedOn: FG.refs(fip, "isBasedOn").map(snapshotItem),
              identifiers: FG.pidItems(fip),
            },
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
              what: field("isPartOf", FG.t("catalogue.what.criterion", { provider: provider.name })),
              details: FG.t("catalogue.testExecution." + execution),
              title: [FG.span(criterion.alternateName), " ", h("span", { class: "id-chip id-chip-static" }, criterion.identifier)],
              titleFields: "alternateName",
              body: [h("p", { class: "small muted", lang: "en", "data-field": "name" }, FG.text(criterion.name)),
                h("p", { class: "small" }, criterion.url ? h("span", { "data-field": "url" }, FG.external(criterion.url, FG.t(execution === "service" ? "selfcheck.evidence.endpoint" : "catalogue.criterionForm"))) : null,
                  documentation.map((url) => [" · ", h("span", { "data-field": "subjectOf" }, FG.external(url, FG.t("selfcheck.evidence.documentation")))])),
                FG.list(criterion.reviewedVersion).length ? h("p", { class: "small", "data-field": "reviewedVersion" }, FG.t("catalogue.reviewedVersion") + ": " + FG.list(criterion.reviewedVersion).join("; ")) : null,
                linked.length ? null : h("p", { class: "small muted" }, FG.t("catalogue.unmapped"))],
              relations: {
                principles: tiles(principles),
                /* The questions the criterion's result suggests an answer to, each with how much of it it covers. */
                covers: FG.relationGroups([{ items: linked, render: ({ mapping, item }) => [FG.idChip(item), h("span", { class: "muted" }, " · " + FG.t("catalogue.coverage." + mapping.mappingCoverage)), mapping.description ? [": ", FG.span(mapping.description)] : null] }]),
                inGuide: inGuide(checks.map((id) => FG.get("#check-" + id))),
                identifiers: FG.identifierItems(criterion),
              },
            }),
        };
      });
  }

  /* A test's health by its icon, beside its text. */
  const HEALTH_ICON = { available: "●", degraded: "◐", unavailable: "○" };

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
              body: [test.description ? h("div", { "data-field": "description" }, FG.paragraphs(test.description)) : null,
                h("p", { class: "small" }, h("span", { "data-field": FG.refIds(test, "hasPart").includes(test.url) ? "url hasPart" : "url" }, FG.external(test.url, FG.t(local ? "selfcheck.evidence.code" : "selfcheck.evidence.endpoint"))),
                  /* The files the Guide's own test runs from, as the crate lists them. */
                  /* The other files the Guide's own test runs with; its code file is the link before them. */
                  FG.refIds(test, "hasPart").filter((path) => path !== test.url).length
                    ? h("span", { "data-field": "hasPart" }, " · " + FG.t("catalogue.testFiles") + ": ", FG.refIds(test, "hasPart").filter((path) => path !== test.url).map((path, index) => [index ? ", " : null, h("a", { href: path }, path)]))
                    : null),
                documentation.length ? h("p", { class: "small", "data-field": "subjectOf" }, documentation.map((url, index) => [index ? " · " : null, FG.external(FG.testDocumentationHref(url, test), FG.t("selfcheck.evidence.documentation") + (documentation.length > 1 ? " " + (index + 1) : ""))])) : null,
                entryPoint ? h("p", { class: "small", "data-field": "additionalProperty" }, h("code", null, entryPoint.value)) : null],
              states: health ? FG.stateBadge({ icon: HEALTH_ICON[health], text: FG.t("catalogue.health." + health), asOf: test.statusAsOf, attrs: { "data-health": String(health) }, field: "healthStatus statusAsOf" }) : null,
              fields: { basedOn: "citation", prefills: "isImplementationOf" },
              relations: {
                principles: tiles(principles),
                prefills: FG.relationGroups([{ items: linkedQuestions, render: (item) => [FG.idChip(item), " ", FG.linkedSpan(item)] }]),
                basedOn: FG.refs(test, "citation").map(FG.recordLink),
                inGuide: inGuide(checks.map((id) => FG.get("#check-" + id))),
                identifiers: FG.identifierItems(test),
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

  /** The person responsible for a change, with a link to their ORCID iD unless they declined to show one. */
  function agentByline(action) {
    const person = FG.get(FG.id(action.agent));
    if (!person) return null;
    const orcid = FG.pids(person).find((pid) => pid.scheme === "orcid");
    return [FG.span(person.name), orcid ? [" · ", FG.external(orcid.iri, FG.t("pid.orcid"))] : null];
  }

  /** A tool used in a change: its name, what kind of tool it is (software or an AI model) and its recorded version, so
      an AI model shows as a tool and never as an author. */
  function toolItem(instrument) {
    const name = instrument.url ? FG.external(instrument.url, FG.text(instrument.name)) : FG.span(instrument.name);
    const qualifiers = [instrument.applicationCategory ? FG.t("catalogue.instrumentKind." + instrument.applicationCategory) : null, instrument.version ? FG.t("catalogue.version", { version: instrument.version }) : null].filter(Boolean);
    return [name, qualifiers.length ? h("span", { class: "muted" }, " · " + qualifiers.join(" · ")) : null];
  }

  /** A content change: when and what kind, who made it and with which tools, what was done, what it consulted and
      every item it changed, each leading to its entry, station or page (design D8). */
  function actionEntries(reach) {
    return FG.graph
      .filter((entity) => String(entity["@id"]).startsWith("#action-"))
      .map((action) => {
        const created = /^Create/.test(String(FG.list(action["@type"])[0]));
        const consulted = FG.refs(action, "object");
        const changed = FG.refs(action, "result");
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
          /* A change is found by its person and tools as well as by what it did. */
          text: [FG.text(action.name), FG.text(action.description), FG.text((FG.get(FG.id(action.agent)) || {}).name), FG.refs(action, "instrument").map((tool) => FG.text(tool.name)).join(" ")].join(" "),
          stations: [...new Set(reached.flatMap((place) => [...place.stations]))],
          principles: [...new Set(reached.flatMap((place) => [...place.principles]))],
          facets: { change: [created ? "created" : "updated"], record: FG.refIds(action, "result") },
          render: () =>
            entryCard({ kind: "actions",
              id,
              entity: action,
              class: "change",
              what: FG.t(created ? "catalogue.created" : "catalogue.updated"),
              title: FG.text(action.name),
              titleLang: "en",
              byline: agentByline(action),
              bylineFields: "agent",
              details: [field("endTime", FG.formatDate(String(action.endTime || "").slice(0, 10))), consulted.length ? FG.t("catalogue.consultedCount", { n: consulted.length }) : null, FG.t("catalogue.changedItems", { n: changed.length })],
              body: action.description ? h("p", { class: "small", lang: "en", "data-field": "description" }, FG.text(action.description)) : null,
              relations: {
                /* A change's few tools always show: an AI model among them is never behind a fold. */
                tools: FG.relationGroups([{ items: FG.refs(action, "instrument"), render: toolItem, fold: false }]),
                consulted: FG.relationGroups(FG.recordGroups(consulted)),
                changed: FG.relationGroups(FG.recordGroups(changed)),
              },
            }),
        };
      });
  }

  let entriesCache = null;
  function allEntries() {
    if (entriesCache && entriesCache.revision === FG.dataRevision && entriesCache.graph === FG.graph &&
        entriesCache.size === FG.graph.length && entriesCache.lang === FG.state.lang) return entriesCache.entries;
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
    entriesCache = { revision: FG.dataRevision, graph: FG.graph, size: FG.graph.length, lang: FG.state.lang, entries: grouped };
    return grouped;
  }
  /* Every list entry by kind, for the completeness test. */
  FG.catalogueEntries = allEntries;

  function modelEntries() {
    return FG.modelTerms().map((term) => ({
      kind: "model", entity: term, name: FG.text(term.name),
      text: [term.identifier, FG.bothLanguages(term.name), FG.bothLanguages(term.description)].join(" "),
      export: { text: FG.text(term.description) }, stations: [], principles: [],
      order: String(term.position || 0).padStart(3, "0"), facets: { modelKind: [term.modelKind] },
      render: () => entryCard({ kind: "model", id: term.identifier, entity: term, what: field("modelKind", FG.t("model.kind." + term.modelKind)),
        title: FG.span(term.name), body: [h("div", { "data-field": "description" }, FG.paragraphs(term.description)), FG.modelDetail(term),
          h("p", { class: "small" }, h("a", { href: FG.modelFilterHref("resources", term) }, FG.t("model.related")), " · ",
            h("a", { href: FG.href("page", "model") }, FG.t("model.overview")))],
        fields: { basedOn: "citation" },
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
          what: [field("inDefinedTermSet", FG.shortText(modelSource(model))), FG.t("lifecycle.stage")],
          title: FG.span(stage.name),
          details: translated ? field("nameTranslation", FG.t("lifecycle.translatedName")) : null,
          body: [
            shown ? h("blockquote", { class: "stage-definition", lang: shown["@language"], "data-field": "description" }, shown["@value"]) : null,
            /* A path stage's Czech definition is the Průvodce's translation; the Czech source's own wording follows it. */
            shown && FG.list(stage.descriptionTranslation).includes(shown["@language"])
              ? h("p", { class: "small muted", "data-field": "descriptionTranslation" }, FG.t("lifecycle.translationOf", { source: FG.shortText(modelSource(model)) }))
              : null,
            stage.quotedDefinition
              ? [h("blockquote", { class: "stage-definition stage-quote", lang: FG.list(stage.quotedDefinition)[0]["@language"], "data-field": "quotedDefinition" }, FG.list(stage.quotedDefinition)[0]["@value"]),
                h("p", { class: "small muted" }, FG.t("lifecycle.quoteOf") + " ", FG.sourceLink(FG.refs(stage, "citation").slice(-1)[0]))]
              : null,
            stage.note ? h("p", { class: "small", lang: FG.list(stage.note)[0]["@language"], "data-field": "note" }, FG.list(stage.note)[0]["@value"]) : null,
            /* The definition is the model's own text, under the licence its record names (design D8). */
            FG.quoteLicence(stage.license, "license"),
          ],
          fields: { basedOn: "citation" },
          relations: {
            correspondsTo: correspondences(stage["@id"]).length ? h("ul", { class: "relation-group crosswalk relation-list" }, correspondences(stage["@id"]).map((item) => correspondenceItem(item, stage["@id"]))) : [],
            basedOn: FG.refs(stage, "citation").map(FG.sourceLink),
            inGuide: inGuide(holders),
          },
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
    for (const facet of (KIND_FACETS[entry.kind] || []).filter((item) => !item.hidden)) row[facet.key] = (entry.facets[facet.key] || []).map(facet.label);
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
    const facets = (KIND_FACETS[kind] || []).filter((facet) => !facet.hidden).map((facet) => facet.key);
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
    actions: [
      { key: "change", values: () => ["created", "updated"], label: (value) => FG.t("catalogue." + value) },
      /* An entry's corner link narrows the changes to those of that record; it shows as a filter, not as a facet. */
      { key: "record", hidden: true, label: (id) => (FG.get(id) ? FG.get(id).identifier || FG.nameText(FG.get(id)) : id) },
    ],
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
        FG.live.nkrNote()
      );
    }
    return h(
      "div",
      { class: "kind-intro" },
      h("p", { class: "small" }, intro),
      kind === "fips" || kind === "resources" || kind === "repositories" ? FG.dashboardNotice() : null
    );
  }

  FG.views.catalogue = function (route) {
    route = { ...route, arg: FG.catalogueKind(route.arg) };
    const state = readState(route);
    const entries = allEntries();
    if (route.arg === "fips" && String(route.extra || "").endsWith("/" + DECLARATIONS_PAGE)) {
      const anchor = route.extra.slice(0, -("/" + DECLARATIONS_PAGE).length);
      const entry = entries.fips.find((item) => item.anchor === anchor);
      if (entry) return declarationsPage(entry);
    }
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
          ownFacets.filter((facet) => !facet.hidden).map((facet) => kindFacet(own, facet))
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
    const results = groups.map((group) => {
      const cards = group.entries.map((entry) => {
        const node = entry.render();
        if (node.id && used.has(node.id)) node.removeAttribute("id");
        else used.add(node.id);
        return node;
      });
      return h(
        "section",
        { class: "catalogue-group", id: group.anchor || null },
        group.label && !single.length ? h("h2", { tabindex: group.anchor ? "-1" : null }, group.label, h("span", { class: "muted group-count" }, " · " + FG.t("catalogue.entries", { n: group.entries.length }))) : null,
        h("ul", { class: "cards" }, cards)
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
