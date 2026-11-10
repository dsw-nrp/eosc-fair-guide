# Design

## Context

See proposal.md, *Why*, for the problem. The figures in this design were measured on a build of `1ec02bd`
(`polish-nkr-integration`) and on the published `1.0.0-alpha.5`. That change merged as `07a1d4a`
([dsw-nrp/eosc-fair-guide#170](https://github.com/dsw-nrp/eosc-fair-guide/pull/170)) after two more review rounds.
Content is unchanged between the two commits, and `main` holds no NKR snapshot yet.

**Recount (task 1.1, 2026-11-06, builds of `07a1d4a` and `1ec02bd` with one script).** No figure changed with the
rebase: both builds give the same counts.

- **The build:** 1,522 OpenAPI paths, two of them templated (the published `1.0.0-alpha.5` has 1,521).
- **The page:** 213 fragment-prefix literals in 10 scripts.
- **The graph:**
  - 17 `sameAs` pairs between Guide nodes;
  - organisations in five `@id` families (`org`, `fd-org`, `infrastructure`, `european-ri`, `eric`);
  - 272 advice items, 214 questions and 52 authored steps.
- **Counted differently from before:**
  - **Names:** 930 entities have a `name` equal to their identifier in some language (first counted as 925).
  - **Restating questions:** 71 questions publish a cited clause's text as their own. The 16 CoreTrustSeal
    questions already take it from their `requirement` clause (`build_crate.py`, `item.setdefault("statement", ...)`).
    The other 55 hold a copy, two of them differing only by reference markup or punctuation. 51 of the 55 copy their
    `requirement` clause, and four (`gate.01`, `gate.08`, `gate.10`, `maturity.14`) copy a clause they cite only in
    `sources`.

**Graph-model review (2026-11-07, build of `d016c1d`).** After M2, the published graph was read against every
vocabulary it refers to: schema.org, DCTERMS, DCAT, FOAF, SKOS, DQV, PROV-O, FTR, ADMS 2.00 (which the W3C namespace
serves), SIO, the FIP ontology, PROF and the FAIR principles terms. The review ran an RDFS closure, schema.org's
domain and range lists, the vocabularies' disjointness axioms, a comparison of every Guide property's declaration with
its values, and a mutation that removes each required property from a real node. Python's OpenSSL on the
maintainer's machine first rejected the valid certificates of SEMIC and Nanodash, which serve ADMS and the FIP terms;
both loaded through a current CA bundle with verification on. ADMS, PROF and the FAIR principles terms showed no
failure, and no node falls in two disjoint classes. Decisions 4, 6, 8, 13, 14 and 20 to 23 answer the findings:

- **RC1, declarations the data contradicts.** Under RDFS reasoning, 24 nodes become organisations (memberships
  through `nodeMilestone`; services and repositories through `nodeMembership`), 14 registry records become
  repositories (`repositoryKind`), and the Node, memberships, layers, seams and life-cycle stages become creative
  works. The ranges of `block`, `infrastructureCharacter`, `nodeMembership`, `rdmkitRecord` and `trainingSearch` do not
  match their values; `assessmentContext` specialises `dcterms:description` but holds a boolean; `disclosureLevel`
  specialises `schema:position` but holds terms; `guideSources`, `guideState` and `acceptsDeposits` are declared and
  unused in the content graph (the first two are carried by exported results, the third by NKR records). The RO-Crate
  validator applies this reasoning, which is why profile 0.2 needed an exemption
  for memberships.
- **RC2, strings for classes and terms.** 582 `additionalType` values, which RO-Crate's context reads as text: the
  FTR test type, FIP classes, cited datasets and software, tools and helper pages, two of them in schema.org's
  `https` form, which no other schema.org term in the crate uses. Clause kinds, mapping bases,
  evaluator mapping coverage and model kinds are strings. IRIs are strings in the source, licence, RDMkit and
  training fields, and three source fields collapse onto one property.
- **RC3, records typed as their thing.** The 20 FIP Dashboard organisation records are typed as organisations, and
  record typing differs by registry. FIP Dashboard records also carry the FIP class of the thing they describe, such
  as `fip:Metadata-schema`, or `fip:Registry` on five repository records, which would type the record as its thing
  once classes are types.
- **RC4, schema.org outside its domains.** The Node's `member`, clause `audience` (actor terms are not audiences),
  `isBasedOn` on organisations and infrastructures, `license`, `citation` and `position` on terms, and crate-local
  lists that hold organisations.
- **RC5, facts stated twice.** 377 terms are named by their set and by themselves; inverse pairs are stated both
  ways; `hasPart` and `isPartOf` have no rule.
- **RC6, shapes that cannot fail.** Five shapes select nodes by the property they require. A clause, a resource or a
  repository that loses its kind-defining property leaves its shape and passes.
- **RC7, a class whose definition does not hold.** FTR defines a test as a service, an API with code that implements
  a metric (a subclass of `dcat:DataService` and `prov:Agent`); the 214 manual tests are a person answering a
  question, and the 42 local tests are browser code without an API.
- **RC8, a term at an IRI its vocabulary does not define.** The crate's 256 links from a test to the question it
  implements, the profile's test shape and the crate context use `https://semanticscience.org/resource/SIO_000233`.
  SIO defines only `http://semanticscience.org/resource/SIO_000233`. The `https` form comes from the FTR ontology,
  which marks it `rdfs:isDefinedBy` SIO, so the scheme is FTR's error. The FAIR Champion test records at
  `tests.ostrails.eu` use SIO's `http` IRI, so neither a SIO consumer nor a consumer of real FTR records finds the
  Guide's links.

**Implementation review (2026-11-08, head `623b5f7`).** Eighteen verified findings cover incomplete identity and
fragment publication, mixed-version release and migration failures, and smaller integration, performance and retired-code
issues. The independent coverage checks exposed a shared weakness in the existing tests: several expected sets came from
the same filtered projection as the implementation, so omitted records stayed invisible. Decision 24 records the release
layout transition; decisions 11, 17 and 19 now include the corresponding independent guards. CORR-002 is pre-existing
and is not assigned to this change.

**Follow-up implementation review (2026-11-09, head `e9c8a14`).** Ten new findings cover deferred station references,
search failure recovery, a literal saved-result template used as an href, mixed release-schema acceptance, missing
health cache protection and smaller landing, performance and retired-code issues. The review independently confirmed
all 18 earlier repairs and left CORR-002 unchanged in provenance and scope. The additional routing decision makes the
bare Guide URL open the existing path start for every reader instead of depending on stored station history.

The approach is bound by these constraints:

- **Static hosting.** GitHub Pages serves files only and ignores query strings. Anything that filters or shapes a
  response has to be a file, or has to run in the consumer's engine. Review facts stay as they are: no database, no
  backend.
- **Standard-library build.** The generator and content checks use only the Python standard library
  (`requirements-dev.txt`). rdflib and pyshacl are already test dependencies.
- **RO-Crate addressing.** Data entities (files) are resolved relative to the crate root. The crate therefore cannot
  set `@base` to the w3id namespace, and Guide things need absolute IRIs in the crate.
- **The page.** It runs from files and in an iframe without any request on load, and it reads the crate through
  generated data scripts. It finds and classifies entities through 213 fragment-prefix literals in 10 scripts.
- **Pre-release freedom.** Before Guide `1.0.0`, identifiers, addresses and the published contract may change in
  place without compatibility routes (*The first release establishes the route baseline*, as modified here). No
  name, form or register category is kept for compatibility alone.
- **Durable prose.** Code, tests, content, styles, CI and durable documents cite no part of any change, this one or an
  earlier one. They explain a rule in their own words and name no design decision, task or migration step, in any
  form a change has used: `D-172`, `design D8`, `(decision 28)`, `(design: group 21)` or `(task 4.1)`. This change's
  artifacts stay under `openspec/changes/`, and knowledge of the old forms lives only in its `migration/` folder.

## Goals / Non-Goals

**Goals:**

- One identity projection, from the Guide-owned ID to the address, shared by the IRI, API path, page route, prose
  reference, page data key and export.
- One graph model, published three ways: the crate, N-Triples and the API, with no translation layer between them.
- A graph that says what its data is: declarations that hold, classes as types, each fact stated once and shapes
  that a node cannot escape.
- A contract that consumers can test against (profile, OpenAPI, recipes), with a deprecation rule from `1.0.0`.
- External IRIs that survive a host move with one redirect change.

**Non-Goals:**

- A query runtime of any kind (B and C in the exploration), SQL or tabular distributions, and an in-browser query
  console.
- Changing what any advice, question or requirement says, except the 55 statements merged into their clauses.
- Re-shaping the page beyond addressing, the predictable bare-URL landing, identifier chips, credited sources, the
  repository family's name, the `#/id/` entry route, the record landing pages (decision 19) and the machines page's
  outline (decision 15).

## Decisions

### 1. Namespace and IRI grammar

The namespace is `https://w3id.org/eosc-cz/fair-guide/`, set as `namespace` in `content/guide.toml`:

```
<ns>terms#<term>                 Guide vocabulary (classes and properties)
<ns>profile/<version>            RO-Crate profile, its shapes and recipes
<ns>id/<kind>/<id>               a thing
<ns>id/<kind>/<scope>/<id>       a thing whose scope is part of its identity
<ns>id/<kind>/<id>#<part>        a part of a thing: a registry record (#knav), a FIP declaration, an advice step
```

- **No API version or file extension in an IRI.** Only the redirect knows where the current representation lives.
- **Records get 303 redirects, documents 302.** A record IRI names a thing, not a document, so it redirects with
  303. `terms` and `profile` redirect with 302, so that a host move is never cached as permanent.
- **Alternatives rejected:**
  - IRIs relative to wherever the crate is read (today): they differ between preview and production.
  - The Pages namespace (I2): it ties every IRI to the GitHub host, and the namespace has already moved once, from
    `fair.eosc.cz`.
  - A path without `id/`: it would mix record IRIs with `terms` and `profile`.

### 2. Kind vocabulary

Kinds are plural English words. The words below are what `catalogue_identity.py`, `issued_ids` and the API share.

| Today | Kind | Scope | Classification moved into data |
|---|---|---|---|
| `pr/` | `principles` | | |
| `step/` | `stations` | | |
| `check/` | `checks` | | |
| `q/` | `questions` | | |
| (fragment only) | `advice` | | advice kind (direction, tip), lens, level |
| `test/fc/`, `test/fcx/`, `test/f-uji/`, `test/guide/` | `tests` | `fair-champion`, `fair-checker`, `f-uji`, `guide` | |
| `res/<type>/` | `resources` | | resource type; cited and recommended as roles |
| `repo/<kind>/` | `repositories` | | repository kind. Registries (`repo/reg/nkr`) become `resources` |
| `cl/` | `clauses` | | |
| `term/` | `glossary` | | |
| `org/` and the Dashboard organisations | `organizations` | | |
| `ri/<domain>/`, ERICs, European RIs | `infrastructures` | | research domain, ESFRI status |
| `fip/` | `fips` | | |
| `act/` | `actions` | | |
| `model/layers-seams` | `models` | | |
| `model/layer/`, `model/seam/`, `model/ex/` | `layers`, `seams`, `model-examples` | | |
| `life/rdmkit`, `life/maldreth`, `life/knav-tools` | `lifecycles` | | |
| `life/rdm/`, `life/mld/`, `life/knav/` (stages) | `lifecycles` | the model's own ID: `rdmkit`, `maldreth`, `knav-tools` | |
| `life/crosswalk`, `life/xw/` | `crosswalks` | the crosswalk's ID, for its mappings | |
| (no address) | `pages`, `callouts` | | |
| controlled term sets (tiers, levels, lenses, statuses…) | `vocabularies` | the set's ID | |

- **`glossary`, not `terms`.** This avoids a second meaning of "terms" next to the vocabulary namespace `terms#`.
  `advice` and `glossary` are collective nouns; the rule is one plain English word, plural where the word has one.
- **Sources stay a role.** The catalogue already shows resources and cited sources as one kind marked by use, and
  addresses already share `res/`. `sources.toml` and `resources.toml` remain two authoring files; both mint
  `resources/<id>`, and one ID space keeps them unique.
- **NKR types are repository kinds.** `NKR_KIND` in `catalogue_identity.py` maps NKR's type (disciplinary,
  institutional, generic) to the repository kind only. The refresh mints `repositories/<id>` for a new NKR record
  instead of today's `repo/<subtype>` (`preserve_snapshot`), so *Catalogue slugs use meaningful local names* loses
  its `repo/dom` route.
- **Alternatives rejected:**
  - Short codes: opaque, and several of them already disagree with the model (`step`, `q`, `cl`).
  - Singular words: they would add a third form next to the plural kind names that filter state, lists and
    `KIND_CODES` keys already use.

### 3. One identity projection, in the crate and on the page

- **The crate.** Every Guide thing gets its absolute IRI as `@id`. Its Guide ID appears once, as `identifier`;
  source IDs stay typed `PropertyValue`s in `identifier`. The separate `catalogueAddress` (`dcterms:identifier`),
  `termCode` (except for vocabulary terms, where it is the code) and any `name` that only repeats the ID are dropped.
- **The page.** Its data scripts key every entity by its address (`resources/dmp-eosc`), and the build keeps the IRI
  beside it. The page asks `FG.kind(entity)` instead of testing fragment prefixes. `FG.catalogueKinds`,
  `FG.catalogueCode` and `FG.catalogueKind` go away, because route, filter and API use the same word.
- **Alternatives rejected:**
  - Keep fragment `@id`s and add the IRI in `sameAs`: graph identity stays unstable, and `schema:sameAs` merges
    nothing.
  - Use full IRIs as page keys: longer data scripts for no gain inside a page that knows its own namespace.
- **Failure handling.** The build refuses an entity without an address, two entities with one address, and an
  address whose kind is not in the vocabulary. The content check names the source file and entry.

### 4. Registry records are records about one thing (R1)

- **The record node.** A registry record becomes a `dcat:CatalogRecord` with `foaf:primaryTopic` naming the thing.
  It sits at the thing's IRI plus `#<scheme>`: `#knav`, `#fip-dashboard`, `#fip-dashboard-organization`, `#nkr`,
  `#re3data`, `#fairsharing` or `#datacite` (for example `.../repositories/zenodo#knav`). The FIP Dashboard keeps two
  collections, so its organisation records take a fragment of their own: an organisation and its eponymous service
  are one node, which can hold both the Dashboard's resource and organisation records (`resources/datacite`). It
  carries the registry's own name, description, licence,
  retrieval date and source identifier, and it is part of its snapshot. FOAF joins the established vocabularies in
  `ESTABLISHED_TERMS`, for this one property.
- **One typing for records.** Every record is a `dcat:CatalogRecord` and a `schema:CreativeWork`, whatever the
  registry describes, and never carries the class of its thing, so a class query counts things and not records
  (RC3). A FIP Dashboard organisation record is therefore no `schema:Organization`. A classification the registry
  gives its thing, such as a Dashboard record's FIP class or an NKR record's repository kind, is the record's
  `dcterms:type`; the thing's own types come from the Guide's classification (open question 12).
- **Every registry is treated alike.** re3data's repository rows and the FAIRsharing and DataCite annotations become
  records as the KNAV, FIP Dashboard and NKR rows do, instead of merging into the thing. A FAIRsharing record carries
  its DOI and name, a DataCite record its repository ID; the thing keeps the DOI in `sameAs`.
- **The thing rests on its records.** Each record names its thing with `foaf:primaryTopic`, and the thing does not
  name its records again (open question 4, decision 22). A curated thing's `isBasedOn` names the Guide's selection,
  and each record names its snapshot. A consumer reads which catalogues supplied a thing from the records that name
  it, and the page credits them from the same statements (decision 15).
- **A snapshot holds its records.** The KNAV catalogue's and the FIP Dashboard's record lists are their snapshots:
  each snapshot lists its records in `hasPart` (open question 7) and is `about` the catalogue's own resource
  (`resources/knav-dm-tools-catalogue`, `resources/fip-dashboard`). The crate-local lists `#knav-tools` and `#fers`
  go, so the catalogue is not a second node beside its own entry.
- **A thing only a registry knows** is founded by its record. The thing node carries its identity, its name, its
  address and the facts lists filter on: kind, status with its date, functions and `acceptsDeposits`. The
  descriptive text stays on the record, with its attribution. An NKR repository with no web address is such a
  thing: it is listed with its status and kept out of the data-repository chooser
  (*A repository not yet public is listed with its NKR record*).
- **Precedence is resolved onto the thing.** Where a registry's facts take precedence, as NKR's name, kind, dated
  status, keywords and web address do (*NKR records are shown as found*), the build writes the winning values on the
  thing, so the API and the page read one set of facts. The record keeps the registry's own values. This replaces
  the `_nkr` overrides in `build_repositories`, which write NKR's values into the entity and keep the originals only
  in the snapshot. A fact the curated entry states wins; NKR wins for its fields; any other fact comes from the first
  registry that states it, in the order re3data, FIP Dashboard, KNAV, FAIRsharing, DataCite.
- **Named agents are things.** A publisher, operator, developer or author named in content resolves to the one thing
  the Guide describes under exactly that name, in any language and of any kind: an organisation, an infrastructure,
  a repository or a resource. "Charles University" is `organizations/cuni`, and "Zenodo" as a publisher is
  `repositories/zenodo`, so an organisation and its eponymous service are one node. Only a name no thing has mints an
  organisation. Where two things share the name, the content names the agent by its address, and the build refuses
  an ambiguous name.
- **Organisation records attach by a reviewed key.** A FIP Dashboard organisation record attaches to a thing only
  through its ROR or a reviewed handle, never through its name: `fipDashboard` on a curated organisation or
  infrastructure row, and `fipDashboardOrganization` on a resource row, whose `fipDashboard` names the Dashboard's
  resource record. A record that names no thing founds one; the duplicate check reports one whose name a described
  thing shares, for review.
- **External record pages stay in `sameAs`.** The thing keeps `sameAs` to a registry's own page, such as
  `https://repo.cz/objects/<handle>` for NKR, as records name their FIP Dashboard counterparts (proposal,
  *Interoperability by identity*). Chips and the not-yet-public exception read that link. The profile's `Repository`
  shape and the API's `Repository` schema keep the exception: an HTTPS `url`, or a planned or in-development status
  with an NKR page in `sameAs`. Only their status test follows decisions 6 and 11.
- **The page** shows one entry per thing, with each registry's record as an attributed section, as it does today for
  sources.
- **Alternatives rejected:**
  - Peer nodes with `sameAs` (R0): consumers have to merge them, and counts come out doubled.
  - `schema:about`: too weak, since a record can be about several topics.
  - Merging records into the thing (R2): it loses per-source attribution, which the content rules require.

### 5. Duplicate check attaches records

- **Its job** changes from "curated versus registry" to "every record attaches to exactly one thing".
- **Build joins** keep the reviewed keys `build_repositories` uses today (archived `polish-nkr-integration`,
  decision D1). An address alone joins only an NKR record; curated and FIP Dashboard entries never join by address
  alone. Two NKR records that reach one thing stay rejected, by the build and by the check.
- **Shared keys** (address, DOI, registry IDs, ROR) still report a duplicate. The authoritative ones
  (`AUTHORITATIVE_KEYS`) propose the reviewed link as the safe `--fix` suggestion. Neither joins anything on its own.
- **A new review key** catches the ownCloud case: the same registrable domain with a distinctive name word in
  common, or the same normalised name with the same provider, between a record and a thing. A plain domain match is
  not enough: many unrelated services share `github.com` or `cesnet.cz`. A review is listed in the report and the
  output; it never fails the check, never proposes a fix and never joins, since a similar name or host must not join
  records (*NKR records are shown as found*).
- **Names shared across kinds.** Two described things of one exact name, such as an infrastructure and the
  repository it operates, are reported unless an accepted group says why they are two.
- **Accepted groups** in `content/duplicates.toml` keep their reasons.

### 6. Controlled vocabularies and statuses

- **Every controlled term** is a `DefinedTerm` in exactly one `DefinedTermSet`: membership via `inDefinedTermSet`
  only, its code as `termCode`, a bilingual name. This covers tiers, levels, actors, modes, profiles, resource types,
  repository kinds, statuses, glossary terms, principles, layers and life-cycle stages. Lenses and clause actors keep
  `Audience` as a second type, because `audience` requires it (open question 6).
- **Stated once.** A term names its set with `inDefinedTermSet`; a set does not list its terms again with
  `hasDefinedTerm` (RC5).
- **No controlled value is a string.** Clause kinds, mapping bases, evaluator mapping coverage and model kinds become
  terms of their own schemes, as statuses did (RC2). Evaluator mapping coverage (whole, partial) stays a scheme of its
  own beside pre-fill coverage, whose terms include champion evidence only. A list a registry publishes, such as
  KNAV's discipline groups and the FIP Dashboard's scopes, becomes a scheme attributed to that registry, so its
  records refer to terms in the registry's own words.
- **SKOS alignment** is stated once, in the vocabulary document (`terms/fair-guide.ttl`): `schema:DefinedTerm`
  `rdfs:subClassOf skos:Concept`, and `schema:inDefinedTermSet` `rdfs:subPropertyOf skos:inScheme`. The 106
  per-instance `skos:` types and memberships go away.
- **Every status** refers to a term of its own scheme, through a property that specialises `adms:status`:
  - clause status (current, refresh, superseded);
  - service status (the five levels, with `statusAsOf`);
  - ESFRI status;
  - the Guide's testing status;
  - health status;
  - preparation status.

  `creativeWorkStatus` strings go away, so `planned` exists once, in the service-status scheme.
- **NKR's own status** stays in its snapshot. Its record and its thing carry the service-status term that
  `scripts/nkr_contract.py` maps it to, dated by the retrieval date. The difference between NKR's two pilot states
  reaches the graph only as `acceptsDeposits = false`.
- **Alternatives rejected:**
  - SKOS only: the crate is schema.org-based, and RO-Crate tooling expects `DefinedTerm`.
  - Both on every instance (today): every membership is stated twice.

### 7. Advice, steps and actions

- **Advice items** (272) get the Guide class `fg:AdviceItem`, the IRI of today's SHACL shape. Its broader term is
  `schema:CreativeWork`, with the reason recorded: schema.org's HowTo types describe steps of a procedure, not
  advice addressed by lens and level.
- **Their kind** (direction or tip) becomes `adviceKind`, a term in the advice-kind scheme.
- **Steps** (52) stay `HowToDirection` parts at `#step-<n>` under their advice item's IRI. **Actions** (77) stay
  `potentialAction` parts at `#action`, with `#action-2` for an advice item's second action.

### 8. FTR in the graph

- **Types.** A check is `Quiz` and `ftr:Benchmark`; a question is `Question` and `ftr:Metric`.
- **No manual tests.** FTR defines a test as a "Service, formed by an API and associated piece of code that
  implements a Metric", a subclass of `dcat:DataService` and `prov:Agent`. A person answering a question in the
  self-check is no such service, so the graph holds no manual tests and `tests/self-check/` is not a scope (RC7). The
  214 manual tests that M2 generated leave the crate and the API.
- **A reader's answer** is a `dqv:QualityMeasurement` of its question: `ftr:Metric` specialises `dqv:Metric`, so the
  answer is `dqv:isMeasurementOf` the question, `dqv:computedOn` the assessed target, with the answer as its
  `dqv:value`. It lives in the saved result, never in the published graph (decision 14).
- **Automated tests.** FAIR Champion tests and FAIR-Checker criteria are each invoked through an API endpoint of
  their own, so each is an `ftr:Test` implementing its metric. F-UJI's criteria arrive in imported reports and are
  F-UJI's `ftr:Metric`s; their results stay evidence read as F-UJI presents it. A FAIR Champion test implements the
  metric its own FTR record at FAIR Champion names (for example `fair-metrics/general/FM_F1_M_IdentPersistent`), which
  the content records with the test; FAIR-Checker publishes no metric IRIs, so its criteria name none (maintainer
  decision, 2026-11-07). Neither implements a Guide question: pre-filling an answer is evidence, not implementation. The page export already reads them
  this way (`providers.js`). The Guide's local tests run as browser code without an API, which FTR's definition does
  not cover: they carry no FTR type, implement their question through SIO's link, and their results stay evidence
  (open question 11).
- **One class for the kind.** Every record of the `tests` kind is an `fg:AssessmentCriterion`, whatever its FTR type,
  so one class selects the kind; its FTR type, where one applies, stands beside it, as `Audience` stands beside a
  lens's term type (open question 13). Its reason for a Guide class: FTR splits criteria into metrics and tests by how
  a provider exposes them, while the Guide lists every provider's criterion as one kind.
- **Relations.** The graph states the FTR relations (`ftr:hasBenchmark`, `dqv:inDimension`, SIO implementation links)
  and drops the schema.org duplicates for the same relation. Only the question names its check; the check does not
  list its questions again with `ftr:hasAssociatedMetric`, which FTR declares as the inverse (open question 8).
- **The API** uses these names as they are, so `RENAMED`, `DROPPED` and `FTR_TYPES` disappear from
  `build_api.py`.
- **Local tests.** A local test's three entities (record, documentation file and entry point) remain. The entry
  point is the test's executable reference, and the profile documents it.
- **Alternatives rejected:** keeping the manual tests as `ftr:Test` with the stretch recorded, which makes them data
  services and agents to any reasoner that knows FTR; a Guide class for them, under which an answer is neither an FTR
  nor a DQV result.

### 9. Pre-fill mappings

`#item-*-prefill-*` `PropertyValue`s become one node per mapping, typed `fg:PrefillMapping`:
- `fg:prefillSource` names the source or service entity;
- `fg:prefillField` names the field read (`doi`);
- `fg:prefillCoverage` names a term (whole, partly, champion evidence only).

The API publishes them on the question record. `prefillLevel` and `championEvidenceOnly` fold into the coverage term.

### 10. Questions that restate their clause

- **Authoring.** A question names its text's clause with `requirement`, the existing field the 16 CoreTrustSeal
  questions already use. A question with a `requirement` and no `statement` takes that clause's text, and the clause
  becomes its first source (`build_crate.py`, documented under `checks/<id>.toml`). The migration:
  - the 51 questions that copy their `requirement` clause drop their `statement`;
  - `gate.01`, `gate.08`, `gate.10` and `maturity.14` gain `requirement` for the clause they copy and drop theirs;
  - their other cited clauses stay in `sources`, which covers the three that cite more than one.
- **Output.** The build writes the clause's text as the question's `text` in every output, linking the clause as its
  basis. Readers and FTR consumers see a text, and the sources hold it once.
- **The content check** rejects a `statement` identical to the text of a cited clause in either language, once
  reference markup and final punctuation are ignored, and names the question and the clause.
- **`maturity.14`** takes `A.I3.R2`'s text. Its ORCID and ROR references move into that clause.
- **Alternative rejected:** a new `statementClause` field. It would restate what `requirement` already means.

### 11. API v1

```
api/v1/index.json                     what the API offers, with links to every list, vocabulary and operation
api/v1/<kind>.json                    list: id, address, IRI, label and the kind's filter fields
api/v1/<kind>/<id>.json               record
api/v1/<kind>/<scope>/<id>.json       scoped record
api/v1/vocabularies/<set>.json        a term set with its terms, referenced by records
api/v1/health.json                    health snapshot, tag "operations", linked from index.json, not a content kind
api/v1/context.jsonld                 JSON-LD context
api/tests/<question>.json             saved-result revisions 1-3 only (decision 14)
openapi.json                          one list and one record operation per kind
```

**Filter fields** come from one table in `build_api.py`, which the schemas and the documentation also read:

| Kind | Filter fields |
|---|---|
| advice | station, lens, level, kind, principles |
| questions | check, tier, principles, modes, profiles, fixAt, owner, pre-fill sources |
| resources | resource type, roles, lenses, stations, status, `asOf` |
| repositories | repository kind, status, accepts deposits, registry IDs |
| clauses | source, principles, clause kind, actor, status |
| tests | scope (provider), metric, principles |
| principles, stations, checks, others | their position and a summary label |

- **Every issued address is published.** One enumeration covers organizations and infrastructures created by registry
  joins, named agents and the roadmap just as it covers curated entries; no curated-ID filter narrows it. An independent
  test derives the expected API record and landing-page set from the crate's issued IRIs rather than from that
  enumeration itself.
- **Filter metadata is truthful.** A collection advertises a default filter field only where its summaries supply it;
  the OpenAPI enum comes from the same decision. This prevents position and term-position fields becoming documented
  filters when no summary can supply them.
- **Build work is bounded by the graph, not repeated per record.** The registry-record index is constructed once per API
  instance. Schema options repeated by object identity are removed before the existing structural JSON deduplication,
  preserving semantic equality and byte-identical generated files. Tests assert both call counts and unchanged output.
- **Generated HTML stays out of sources.** The generated-output guard covers the root `404.html` and every
  `id/<address>.html`, with negative fixtures at the repository root and at a nested record path.
- **`acceptsDeposits`** is `false` or absent. Absence means unknown, never acceptance (*Repository and registry
  functions*), so no list entry carries `true`, and the schema and the documentation say so.
- **Records** refer to vocabulary terms by address, with the term set published once, instead of embedding them;
  today `pr/R1.1` repeats one lens description 67 times.
- **Parts** are given in full in their thing's record under their fragment: an advice item's steps and actions, a
  FIP's declarations, and a thing's registry records (`#knav`, `#nkr`, `#re3data` and the others), so a thing only a
  registry knows still reads with its registry's description and attribution.
- **Schemas** are typed, with enums from the term sets. The OpenAPI document describes a scoped kind's `{scope}` as
  an enum and `{id}` with a pattern and examples.
- **Removed:**
  - the 16 role-named lists (`sources`, `metrics` and the rest);
  - the per-record operations;
  - the old `api/<code>/...` tree, removed without compatibility documents because it is unreleased.
- **The health snapshot** moves to `api/v1/health.json`. `docker/nginx.conf` moves its `no-store` rule with it.
- **Endpoint documentation shows a real target.** The machines page keeps the saved-result support template
  `api/tests/{id}.json` as text while its link opens a concrete emitted question-support document. Its OpenAPI coverage
  is compared through the operation/template, and each emitted href is checked directly rather than made valid only
  inside the test.

### 12. RDF distribution

- **The writer.** The build writes `knowledge-graph.nt` beside the crate, with a small standard-library writer. It
  expands the build's own graph using the term map the build already owns (the crate's inline context plus the
  RO-Crate terms it uses, from a pinned local copy of the RO-Crate 1.2 context).
- **The check.** A test proves that the triples equal rdflib's parse of the crate (graph isomorphism).
- **Signposting.** The linkset and HTML head add it as `describedby` with type `application/n-triples`.
- **Alternative rejected:** rdflib or a JSON-LD processor at build time, which would break the standard-library build
  rule.

### 13. Query contract and recipes

- **Selecting a kind.** Every kind has a class or a term set that selects it, or a recorded reason. Pages and
  callouts carry a reason: they are the Guide's own text, reached by IRI. Crosswalk correspondences get a class (a
  Guide class where no established class carries a basis and a source), and their basis becomes a term. The `tests`
  kind is selected by `fg:AssessmentCriterion` (decision 8). A check fails on a kind with neither a selector nor a
  reason (RC6).
- **A Guide class where kinds share one** (maintainer decision, 2026-11-07). Most kinds share their established class
  with another kind, so each such kind gets a Guide class beside it, specialising that class: `fg:Clause`,
  `fg:Resource`, `fg:Repository` (also a `schema:DataCatalog`), `fg:ResearchInfrastructure`, `fg:LifecycleModel`,
  `fg:Crosswalk` and `fg:StageCorrespondence`, `fg:TermSet` for the Guide's vocabularies, and `fg:AssessmentCriterion`.
  Actions are also `prov:Activity`. A kind of terms is selected by its set: glossary, principles, a life-cycle
  model's stages and a vocabulary's terms; layers, seams and model examples by their model-kind term. Organisations
  are the `schema:Organization`s that are not research infrastructures. Pages, callouts and the one conceptual model
  carry a reason: the Guide's own text and model, reached by IRI. Rejected: classification terms alone, which leave
  114 resources and three repositories without a term and give the shapes nothing to select by class; and reasons
  wherever a class is shared, which leaves RC6 open.
- **Classes are types.** Every class is an `@type`, never an `additionalType` string, which RO-Crate's context reads
  as text (RC2): the FTR types, the FIP classes, cited datasets and software, tools and helper pages. Each is written
  at the IRI its vocabulary defines (decision 23), so the helper pages' `https://schema.org/WebApplication` becomes
  `http://schema.org/WebApplication`, the form RO-Crate's context uses for every schema.org term. A cited dataset is a
  `dcat:Dataset`, and cited software, a tool and the Guide's own source code are `dcmitype:Software` (maintainer
  decision, 2026-11-07): as types, RO-Crate 1.2 reads `schema:Dataset` as a data entity the crate holds,
  `schema:SoftwareSourceCode` as a script that must be a file, and `schema:SoftwareApplication` as software with a
  known version, none of which a cited work is.
- **Shapes target classes.** A shape selects its nodes by class and requires the properties that define the kind,
  so a node that loses one fails rather than leaving the shape. A test removes each required property from a real
  node and expects a violation (RC6).
- **The profile** moves to `0.2`. Its shapes cover:
  - every kind's class and required properties;
  - `fg:AdviceItem`;
  - `dcat:CatalogRecord`;
  - term-set membership;
  - the FTR types;
  - `fg:PrefillMapping`.
- **Recipes** are SPARQL files published with the profile at `profile/<version>/recipes/<name>.rq`, each with a
  Czech and English description and an expected-result fixture in `tests/fixtures/recipes/`. The first set:
  - advice for a lens at a station;
  - questions of a check by tier;
  - resources for a principle;
  - registry records of a thing;
  - tests implementing a metric;
  - the clauses a question cites.
- **CI** runs every recipe with rdflib against `knowledge-graph.nt` and compares sorted rows.
- **Deprecation rule (effective from Guide `1.0.0`).** A change that removes or changes the meaning of a class,
  property, shape, recipe, API field or path is first marked deprecated, in the profile and OpenAPI
  (`deprecated: true`) and in the changelog. It stays for at least one minor release and is removed only in the next
  major. Additions may arrive in any minor. Until `1.0.0`, changes are made in place.
  [dsw-nrp/eosc-fair-guide#171](https://github.com/dsw-nrp/eosc-fair-guide/issues/171) confirms the rule and moves
  the versions to production values.

### 14. Saved results

- **Revision 4.** A reader's answer is a `dqv:QualityMeasurement` of its question's IRI, `<ns>id/questions/<question>`,
  computed on the assessed target (decision 8). Automated evidence names its test's own IRI, or the F-UJI metric it
  reports on.
- **Older revisions.** Revisions 1–3 still load. The loader already keys answers by question ID, and it reads their
  `api/tests/<question>.json` references as references to the same question.
- **Old test paths.** The build keeps generating `api/tests/<question>.json`, as the documents that saved files of
  revisions 1–3 name, each describing and linking its question. Such a document is no longer a test and no list or
  question names it. This is the separate saved-result support the
  route-baseline requirement keeps; no other old path survives.

### 15. Page addressing and display

- **Routes.**
  - Catalogue routes are `#/<lang>/<lens>/catalogue/<kind>/<id>`, with `<scope>/` where needed. They keep the lens
    like every other view: the catalogue filters by it, and embedding protocol v1 accepts only views that name one,
    so the protocol stays unchanged.
  - `#/id/<address>` is the one route without reader state. It is the landing page's link into the Guide (decision
    19), not a redirect target. It opens the catalogue entry, stations and checks included, in the saved language
    and lens, or else in Czech with the `V` lens. It replaces itself with the full route before the view is shown or
    published to an embedding page.
  - An unknown address says so and offers search.
- **Identifier input.** Search and the identifier input accept a Guide IRI or an address.
- **The bare Guide URL is predictable.** An empty hash selects the existing `#/<lang>/<lens>/path/start` landing,
  independently of stored station history. The Path menu and resume action still use the last-read station; an
  explicit route without a station keeps its existing behaviour, and `ro-crate-preview.html` keeps its machines
  exception. Only the default changes, not the landing or station views.
- **Deferred data cannot break synchronous references.** Infrastructure addresses named by the build's text links stay
  in the initial record map; only the remaining infrastructure addresses wait for `fips` or `api`. The set is derived
  from the references rather than maintained as another ID list. Station tests exercise the references before `fips`
  has loaded.
- **Search fails openly and independently.** Classification happens before text-index preloading, so a recognised
  identifier needs no unrelated part. A failed text-search part exposes the shared visible alert and retry action;
  retry resubmits after recovery. A planted failure test also proves that an identifier route still renders.
- **Infrastructure relations are indexed once.** A reverse `operatedBy` map is built with the infrastructure entries
  and reused by their cards, rather than scanning the whole graph for every card on every render. Unchanged filters
  continue to reuse the existing catalogue derivation cache.
- **Chips.** An ID chip still shows the record ID; its title names the full address. Every catalogue entry, of every
  kind and in the list as well as alone, shows its own persistent IRI first among its identifiers. No identifier chip
  carries a label: an identifier is shown in full, and its address already says what issued it ("Identifikátor
  Průvodce", "re3data" or "FAIRsharing" would only repeat it).
- **Credited sources.** An entry's "Vychází z" / "Based on" row reads the Guide's selection from its `isBasedOn`
  where the entry is curated, and the catalogue of each registry record that names it (decision 4), each leading to that
  catalogue's own entry with its snapshot's date. A registry that only identifies the thing, without a record (an NKR
  handle before NKR's first snapshot), is shown among the identifiers and not credited as a source.
- **The repository family** is "Repozitáře" / "Repositories": registries are resources (decision 2), so a registry
  is listed and filtered with the resources.
- **Anchors** for glossary terms and repositories become the bare ID.
- **Page sections.** A page section's fragment is its reviewed `id` (`pages/machines#tasks`), never its position, and
  the content check refuses a section without one. Reordering a page then moves no IRI, reference or shared link;
  today 16 of the 47 sections have no `id`, so their fragment is their place on the page.
- **The machines page's outline** follows what a reader wants: what the page offers, *Co hledáte* / *What you are
  looking for*, the worked example from a requirement to a usable finding, how the Guide applies its own advice, and
  then the API endpoints. Today it opens with the worked example and only then says what the page is. Task 4.7 adds
  the IRI and address patterns, the landing pages, the RDF distribution, the recipes and API v1 within this outline
  rather than reordering it.
- **Accessibility.** An identifier chip is a native link with a visible focus. It carries text, not colour alone, and
  wraps at slashes on narrow screens.

### 16. One reference syntax

- **Prose** references are `[[<kind>/<id>|phrase]]`, with the scope inside the address where there is one, and a
  part as `<address>#<fragment>`. A kind word alone names that kind's catalogue list, as `[[infrastructures|...]]`
  does; it is the rule, not an exception. The one reference to the Guide's profile names the section of the machines
  page that presents it, `[[pages/machines#tasks|...]]`, so no target outside the records and kinds remains.
- **Fields that can name several kinds** name a record by its address too: provenance `results` and `objects`, a
  model association's `target`, the worked example's `steps`, and an agent field where a name is ambiguous
  (decision 4). A field whose name fixes the kind, such as `fixAt`, `stations` or `sources`, keeps the bare ID.
- **An unknown reference** names no record and no kind. The content check refuses it and names the one record whose
  ID equals the reference's last segment, where there is one (`[[licence|...]]` gives `[[stations/licence|...]]`).
  It knows no earlier form; the migration owns those (decision 17).
- **Documentation.** The native content rule in `.agents/guide/` and `docs/content-model.md` document the one
  syntax, and the vendor mirrors are regenerated.

### 17. Content migration

- **The script.** One standard-library script, `openspec/changes/unify-identity-model-and-api/migration/migrate.py`,
  owned by this change. It is idempotent, has a dry-run that prints the diff, and writes:
  - prose references: about 260 address forms plus the word forms;
  - the identifier register (below);
  - provenance `results` and `objects`, model association targets and the worked example's steps, as addresses
    that name the same published items;
  - the 55 statement merges through `requirement` (decision 10).
- **Retry is safe from mixed states.** Reassignment and dependent renames accept a file only in a recognized old or new
  state, so a completed rename cannot be applied a second time after interruption leaves old and new files together.
  Every changed file is written to a same-directory temporary file and replaced atomically. Fault injection at each
  write boundary proves that retry completes byte-for-byte like an uninterrupted run; the existing second-run test is
  not sufficient evidence of this.
- **The register** keys every issued ID by its record kind, and its value is the address without the kind:
  `vocabularies` holds `lenses/V`, `modes-dataset/before` and `profiles-gate/core-system`; `callouts` holds
  `sensitive-data` and its items as parts, `sensitive-data#steward`; `stations` holds the model contexts as
  `plan#context-V`; `models`, `layers`, `seams` and `model-examples` split today's `model`; `lifecycles` and
  `crosswalks` split `lifecycle`; `tests` carries the scope, `guide/guide-dataset-01`; sources share `resources`,
  one ID space. No category is kept for its old name; share links carry a mode's or profile's code, which this does
  not change.
- **Snapshots** are generated files, so their `guideRoute` (219 records plus the glossary when measured) is rewritten
  by the migration's renormalisation, which rereads the recorded snapshot without a new observation and keeps
  `retrieved`. `guideRoute` keeps its meaning, the frozen kind (and scope), so a later reclassification still cannot
  move an identity. A harvest proposed before this change and merged after it is renormalised with the same script.
- **The migration owns the old forms.** The route table, the word forms, the code prefixes and the renormalisation
  live in `migration/` with their tests (`migration/test_migrate.py`). `scripts/` and `tests/` know only the current
  forms: the content check has no table of retired forms (decision 16), and `refresh_snapshots.py` has no route
  translation.
- **Results name records.** A result is an address or an address prefix. A prefix (`advice/plan.*`) matches records;
  it matches a part only when the pattern names one (`callouts/sensitive-data#*`). An action whose result is `*`
  changed the Guide as a whole: the crate records the Guide itself as its result, and the freshness check reads `*`
  as covering every item. A record's list of changes therefore never fills with one structural migration.
- **Paradata.** One provenance action, `2026-11-06-identity-migration`, with `results = ["*"]` covers the freshness
  check. Its agent is the responsible maintainer; its instruments are the AI tools used, and no migration script is
  an instrument; it is described as a structural migration. Content credit gains no person.

### 18. The w3id registration

- **Location.** The pull request to `perma-id/w3id.org` adds `ids/eosc-cz/`:
  - a `README.md` naming EOSC CZ as the owner and `motyc` and `MarekSuchanek` as maintainers until EOSC CZ names
    others;
  - an `.htaccess` that sends the root to `https://www.eosc.cz/`;
  - `ids/eosc-cz/fair-guide/` with its own `README.md` and `.htaccess`.
- **Rule outline** (the exact text is shown for approval before submission):

```
RewriteEngine on
RewriteRule ^$ https://dsw-nrp.github.io/eosc-fair-guide/ [R=302,L]
RewriteCond %{HTTP_ACCEPT} text/turtle
RewriteRule ^terms/?$ https://dsw-nrp.github.io/eosc-fair-guide/terms/fair-guide.ttl [R=302,L]
RewriteRule ^terms/?$ https://dsw-nrp.github.io/eosc-fair-guide/terms/ [R=302,L]
RewriteRule ^profile/(.+)$ https://dsw-nrp.github.io/eosc-fair-guide/profile/$1 [R=302,L]
RewriteCond %{HTTP_ACCEPT} application/(ld\+)?json
RewriteRule ^id/(.+)$ https://dsw-nrp.github.io/eosc-fair-guide/api/v1/$1.json [R=303,L]
RewriteRule ^id/(.+)$ https://dsw-nrp.github.io/eosc-fair-guide/id/$1.html [R=303,L]
```

- **No fragment in a target.** A redirect whose `Location` carries a fragment replaces the one requested (RFC 9110,
  section 10.2.2). The targets carry none, so a part IRI such as `.../id/repositories/zenodo#knav` reaches the
  landing page at that part.
- **Coupling.** The rules depend only on four site paths: `terms/`, `profile/`, `api/v1/` and `id/`. A host move
  ([dsw-nrp/eosc-fair-guide#32](https://github.com/dsw-nrp/eosc-fair-guide/issues/32)) or an API major version needs
  a registry pull request, and the new runbook `docs/runbooks/update-the-w3id-redirect.md` covers both.
- **Testing.** The rules are tested with the registry's own checker (`tools/check/` and `.w3id-check.yaml`) before
  submission, and with the probe after merge.
- **Watching.** The health watch probes, weekly, `terms` (HTML and Turtle), the current `profile`, and one record IRI
  per kind as JSON and HTML. A failure is reported in the digest under the key `w3id:<iri>`.

### 19. Record landing pages

- **One document per address.** The build writes `id/<address>.html` for every address it issues, in the same loop
  that writes the API records. It is static and bilingual from the builder's shared language configuration, Czech first,
  each language marked with `lang`, as the page's `noscript` text already is. It needs no JavaScript and makes no
  request beyond its own stylesheet.
- **Content.** A fixed set of fields taken from the API record it signposts:
  - name, text and kind, the Guide-identifier chip and external identifiers;
  - status with its date, where the kind has one;
  - one section per issued part, anchored by the part's fragment (`#knav`, `#step-2`, `#action`), with each registry
    record's attribution and licence;
  - links to related records' landing pages.
- **Statuses share one declaration.** Landing-page status properties come from the shared properties that specialise
  `adms:status`, including `infrastructurePhase` and `esfriStatus`; a second manually filtered list cannot silently
  omit a new status kind. HL-LHC proves that `landmark` occupies the Status field. A date appears only when the API
  record actually supplies one; no observation date is invented for an undated record.
- **Every nested fragment exists.** One recursive walker indexes and renders direct and nested parts, including nested
  actions and vocabulary members. An independent test compares every fragment the API issues with exactly one static
  target, instead of looking only at direct record parts. Ineffective secondary language and description settings go.
- **Signposting.** The head carries `cite-as` (the record's IRI), `describedby` (its API record, typed
  `application/ld+json`), `type`, `license` and `collection` (the Guide). The Guide root keeps its own links. Compact
  classes expand through the established class-prefix mappings, so `prov:Activity` becomes
  `http://www.w3.org/ns/prov#Activity`, never a fabricated schema.org IRI; the other compact types follow the same
  mappings.
- **Into the Guide.** "Otevřít v Průvodci" / "Open in the Guide" links to `<root>index.html#/id/<address>` with an
  explicit `index.html`, so it works from `file://` too; the route applies the reader's language and lens (decision
  15).
- **Unknown addresses.** The build writes a bilingual `404.html` that says no catalogue entry has the address and
  links to the catalogue search. Stylesheets resolve from the validated publication path, including a project subpath,
  rather than below the missing record's URL. A nested missing-address check requires the 404 status, bilingual text and
  successful loading of both stylesheets. Pages serves it for any missing path; `docker/nginx.conf` adds
  `error_page 404 /404.html`.
- **Discovery.** The production sitemap lists every landing page with an absolute, fragment-free URL. Preview pages
  under `next/` get `noindex` and the preview notice from assembly, like every preview page, and stay out of it.
- **Alternatives rejected:**
  - A hash route as the browser target (as first planned): it drops part fragments, gives crawlers one page, and
    allows only one HTML head, so no record can carry its own signposting.
  - Path routes with the History API: GitHub Pages has no rewrites and its `404.html` fallback answers with status
    404, and `file://` cannot reload a deep path.
  - Pre-rendering the whole app per record: every record would repeat the application shell, and the app's
    relative paths assume the site root.

### 20. The vocabulary's declarations hold for the graph

- **The rule.** Every domain and range that the vocabulary document and the crate publish holds for every use in the
  built graph, including the range of an established property a Guide term specialises. A reasoner therefore adds no
  class that a node does not have. A term the graph does not use is not declared (RC1).
- **Corrections known now:**
  - the domains of `nodeMembership`, `nodeMilestone`, `statusAsOf`, `operatedBy`, `repositoryKind`, `modelKind`,
    `implementationLayers`, `nameTranslation`, `descriptionTranslation`, `quotedDefinition` and `note`;
  - the ranges of `block`, `infrastructureCharacter`, `nodeMembership`, `rdmkitRecord` and `trainingSearch`;
  - `assessmentContext`, a flag that marks a question as context rather than an answerable criterion, no longer
    specialises `dcterms:description`;
  - `disclosureLevel`, whose values are terms, no longer specialises `schema:position`;
  - `guideSources` and `guideState` stay, because every exported result carries them under the Guide's IRIs and the
    loader reads them back; `acceptsDeposits` stays, because NKR records produce it. The check counts the terms the
    build hands the page for its exports as used, and `acceptsDeposits` in the graph built from the NKR fixture
    (maintainer decision, 2026-11-07: the review had read the two export terms as unused).
- **The check.** A test reads the built graph with the Guide's vocabulary and fails on a use whose subject, value or
  datatype a declaration does not admit, on a use outside the range of the specialised established property, and on
  an unused term. Planted wrong uses prove each branch.
- **How declarations are stated.** They stay `rdfs:domain` and `rdfs:range`, and each is made true (open question 2).
  A domain or range names the most specific class that every use has, read through the class hierarchies of the
  pinned vocabularies (decision 23); where only `schema:Thing` would cover every use, the declaration is omitted
  rather than made vacuous.
- **The membership exemption** in profile 0.2's organisation shape goes, because no declaration types a membership as
  an organisation any more.
- **Alternative rejected:** keeping the declarations and exempting their effects in shapes, which treats each
  symptom and leaves every reasoning consumer with the wrong classes.

### 21. The EOSC CZ Node is a platform

- **What a Node is.** The EOSC Federation Handbook 2.0 (EOSC Association, 2026-01-30, doi:10.5281/zenodo.18454649,
  CC BY 4.0) defines it: "An EOSC Node is a collection of services and data sources operated as a platform by a
  national, regional, thematic, or European organisation (or consortium)". Nodes "onboard" resources. The 2024 draft
  had called a Node an organisation, with a separate Node Host as the legal entity; the Guide follows the current
  edition, which `content/sources.toml` cites.
- **The Node in the graph** is a `schema:Service` at `resources/eosc-cz-node`, of resource type `service`, operated by
  e-INFRA CZ through `schema:provider`. It carries `nodeState`, its state in the federation, with its date, and no
  five-level service status; the resource shape accepts a node state in place of a service status (open question 3).
- **Onboarding** is a DCAT qualified relation, one part of the Node per onboarded entry:

```
resources/eosc-cz-node
  dcat:qualifiedRelation --> <part>  (dcat:Relationship)
      dcterms:relation --> the onboarded service or repository
      dcat:hadRole     --> a term of the node-role scheme (service, repository, incubator)
      fg:nodeMilestone, fg:statusAsOf, schema:citation (the charter), dcterms:references (the locator)
```

  DCAT 3 defines `dcat:Relationship` as "an association class for attaching additional information to a relationship
  between DCAT Resources", and `dcat:hadRole` as "the function of an entity or agent with respect to another entity
  or resource". As in DCAT's Example 54, the role is the related entry's function for the Node. `dcat:Role`
  specialises `skos:Concept`, so the node-role terms fit the SKOS alignment of decision 6.
- **Read from the Node's side.** `fg:nodeMembership` goes, so the relation is stated once. The page reads the Node's
  relations through its reverse relations for the badge and the facet; an entry's API record still shows its
  membership, and task 4.1's table may list the node role as a filter field.
- **The address** moves from `organizations/eosc-cz-node` to `resources/eosc-cz-node` before `1.0.0`, in place, with
  the register.
- **Accessibility.** The badge keeps its text, icon and source link; only where it reads its data changes.
- **Alternatives rejected:**
  - Keeping the Node an organisation: it contradicts the current Handbook, and DCAT's domain would make that
    organisation a `dcat:Resource` and a `prov:Entity`.
  - `schema:member` with a role: its range is an organisation or a person, never a service.
  - schema.org's `makesOffer` and `itemOffered`: commerce semantics, with no place for a role.
  - A Guide class for memberships: an established class exists.

### 22. Each fact once, and schema.org within its domains

- **One direction.** For each kind, a relation and its inverse are stated in one documented direction only, never
  both for the same pair (RC5). The content model records the direction, and a check finds a pair stated both ways.
- **schema.org within its domains.** A schema.org property is used only on a subject one of its published domain
  classes admits, with a value its range admits; elsewhere a property whose definition fits replaces it (RC4). A
  check compares the built graph with the pinned vocabularies of decision 23.
- **IRIs as references.** A value that names a web resource is an IRI reference, except where schema.org's own `URL`
  datatype is text, as in `url`. The three source fields become distinct properties, each specialising
  `dcterms:source` with IRI values.
- **The particular choices** (open questions 4 to 10):
  - a record names its thing, and the thing does not name its records (decision 4);
  - organisations and infrastructures name their published sources with `dcterms:source`, which has no domain; the
    operator, operated-by and developer sources are its subproperties;
  - clause actors are typed `Audience` (decision 6);
  - snapshots keep `hasPart` for their records;
  - a question names its check and a check does not list its questions (decision 8); `hasPart` and `isPartOf` have
    one direction per kind, recorded in the content model;
  - a quoted definition is a `#definition` part of its term, carrying the quoted text, its licence and its citation;
    the term keeps its name;
  - the crate-local lists go, except any a page view still reads, which the content model then names.

### 23. Every term is the IRI its vocabulary defines

- **The rule.** Every class and property the graph uses from an established vocabulary is the IRI that vocabulary
  defines, in its scheme. The link from a test to the question it implements becomes SIO's own
  `http://semanticscience.org/resource/SIO_000233`, in the crate context, the profile's test shape, the API, the
  documentation and the tests (RC8). SIO places it under "is attribute of" and then "is related to", whose domain and
  range are SIO's top class, so the change adds no class a node does not have.
- **Pinned vocabularies.** A copy of every vocabulary the graph refers to is kept with the tests, as the RO-Crate
  context already is: schema.org, DCTERMS, DCAT, FOAF, SKOS, DQV, PROV-O, FTR, ADMS, SIO, the FIP ontology, PROF and
  the FAIR principles terms. Each copy records its source, retrieval date and licence. The checks of decisions 20, 22
  and this decision read these copies, so no check depends on the network or on a machine's certificate store.
- **The check.** It fails on a namespace the graph refers to that has no pinned copy, and on a term its vocabulary
  does not define at the IRI used. A planted `https` schema.org class and an unpinned namespace prove both branches.
  Refreshing a copy is a reviewed update that reruns the checks.
- **FTR's own scheme error** can be reported to the FTR maintainers. That is an outward action, drafted and approved
  separately; this change does not depend on it.
- **Alternative rejected:** following FTR's `https` form. It matches one ontology file's error, while SIO and the
  FTR records published by FAIR Champion use the `http` form.

### 24. Verified artifacts across schema transitions

- **One recognized layout at a time.** Current artifacts carry `api/v1/health.json`, `releaseStatus` and the generated
  bilingual 404. Documented predecessor artifacts carry `api/health.json` and `creativeWorkStatus`, and need no 404.
  Assembly and image preparation accept either layout, preserve the verified bytes and reject a mixed or missing
  layout before replacing output. A current 404 is required only for the current layout.
- **Health and status select together.** One shared gate derives the accepted status property from the selected health
  layout and requires it on both `./` and `#guide-software`. Neither node may fall back independently to the other
  generation's property. Current health with legacy status, predecessor health with current status, and a split crate
  are all mixed layouts, not compatibility cases.
- **Every health response is fresh.** The image's nginx template applies `Cache-Control: no-store` to both
  `/api/v1/health.json` and `/api/health.json`. The candidate container's probe checks that header along with the
  served revision and build identity, so a body-only smoke check cannot conceal a stale intermediary response.
- **The artifact supplies its own contract.** Release identity reads the status field found in that layout, and the
  candidate image probes the health path found in the archive instead of assuming API v1. These are readers of
  already verified artifacts, not compatibility API documents, so the route-baseline rule is unchanged.
- **Independent old/new evidence.** Tests supply genuine current-shape and predecessor-shape archives through Pages
  assembly, image preparation and health verification, including the previous health path and no-404 case. A full
  current, predecessor, missing, mixed and split-node matrix proves rejection before managed output is replaced. No
  live release establishes this compatibility.
- **Alternative rejected:** invoking historical tooling for each old artifact. That adds another checkout and trust
  boundary and makes an ordinary retry more complex without improving byte preservation.

## Risks / Trade-offs

- [The migration touches almost every content file, and interruption can leave a mixed checkout] → It is one
  state-aware, idempotent script with a dry-run and atomic replacement per changed file. Fault injection covers every
  write boundary and retry; the reviewer also checks the script and a sampled diff per kind. The build refuses dangling
  or ambiguous addresses.
- [The w3id merge is in other people's hands, and EOSC CZ must agree to the `eosc-cz` folder] → Ask EOSC CZ first,
  together with #32's address question. Production keeps its namespace until the redirect is merged (spec: *A
  namespace switch is released only with a registered redirect*), so the release waits rather than shipping IRIs
  that don't resolve.
- [Between the registry merge and the release, record IRIs redirect to production paths that only the release
  creates] → Nobody depends on the new IRIs before the release. The probe reports the gap until then, and the release
  closes it.
- [A record is rendered twice, by the landing page and by the app, and the two can drift] → The landing page renders
  only its fixed field set from the API record it signposts, and a test compares the two.
- [Pages serves one `404.html` for the whole site, preview included, and production's bytes come from the release]
  → The page names no channel. It is served at any depth, so it links to the catalogue search by an absolute
  address from the build's publication location, never relative to itself.
- [Complete identity enumeration adds records the initial API projection omitted] → Independent graph-to-document
  coverage tests prove that every issued address exists without deriving the expected set from that same projection;
  the normal page-payload budget, both-language views and release size are checked again.
- [A third-party SKOS alignment in our vocabulary document could be read as overreach] → It is stated as
  subclass/subproperty axioms in the Guide's own document, never as equivalence, and the document says so.
- [Dropping `name` where it repeats the identifier removes a label some tools display] → The `identifier` and the
  text remain. Every kind's label field is declared in the API table, and the profile documents it.
- [The page rewrite (213 prefix literals) can regress views quietly] → `FG.kind` comes with a test that fails on any
  remaining prefix test. The full browser suite runs in both languages, at phone width and in print.
- [Saved results from alpha releases point at the old host path] → `api/tests/<question>.json` keeps being generated
  at the same relative path, and the loader maps them.
- [The default branch changes while previous production still uses the predecessor layout] → Assembly and image
  preparation recognize current and predecessor artifacts independently, reject ambiguous layouts before output, and
  test both through their own health and status evidence. Verified production bytes are never rewritten.
- [The build figures were measured on `1ec02bd`, before its last review rounds] → Task 1.1 recounted both builds
  with one script and found no change (*Context*). Later tasks verify their counts against the actual build.
- [A named agent that resolves to a service makes a resource or repository the `publisher` of a work, where a reader
  of schema.org expects an organisation] → One node per name is what the catalogue shows anyway, and the profile
  allows any described thing as an agent. A name that should mean the organisation and not the service names the
  organisation's address in the content.
- [Two kinds of thing legitimately share a name, such as the Czech National Corpus infrastructure and its corpus
  repository] → The build refuses the ambiguous agent name, the content names the agent by address, and an accepted
  group records why the two are separate.
- [Dropping the manual tests removes 214 IRIs that the preview published after M2] → No release names them. Saved
  files of revisions 1–3 name `api/tests/<question>.json`, which stays, and revision 4 names the question.
- [A consumer that relied on inference from the vocabulary's domains gets fewer classes] → Every class a node has is
  asserted; only the wrong inferences disappear.
- [The Node's address moves after M1 issued it] → It is unreleased. The content check refuses a reference to the old
  address and names the record (decision 16), and the register moves with it.
- [The pinned vocabularies age] → They are reviewed fixtures like the RO-Crate context; a refresh is a reviewed
  update, and the check names any term a copy lacks.
- [Switching SIO's IRI breaks a consumer that followed the FTR ontology file's `https` form] → Nothing released uses
  it, and the FTR records FAIR Champion publishes use SIO's `http` IRI.
- [The review's fixes reopen a milestone that had closed] → They land before M3 writes any schema or recipe, so no
  API schema or recipe is written twice; M2 closes again with its own full checks.
- [A founded thing moves its description to its record, so a consumer reading only the thing's node finds less] →
  The record is under the thing's IRI and names the thing with `foaf:primaryTopic`; the API record of the thing
  carries its records in full under their fragments (decision 11).

## Migration Plan

```
 M1 identity        kind words, w3id namespace, one identity projection, R1 records, migration script,
                    page addressing and #/id/, one reference syntax, duplicate-attach check
      |
 M2 model           vocabulary and status model, advice class, FTR in graph, pre-fill mappings,
                    question text from clauses, profile 0.2; then the review's fixes: declarations
                    that hold, kinds by class, records typed once, each fact once, answers as DQV
                    measurements, the EOSC CZ Node as a platform
      |
 M3 access          API v1, OpenAPI templates, health under operations, N-Triples, recipes and their CI,
                    record landing pages, 404 page and sitemap, machines page, saved-result revision 4;
                    complete issued records, nested fragment guards, compatible release readers and safe retries
      |
 M4 w3id + release  EOSC CZ consent, approved submission, registry merge, probe and runbook,
                    the release that switches production
```

- **One pull request.** The whole change is one pull request,
  [dsw-nrp/eosc-fair-guide#172](https://github.com/dsw-nrp/eosc-fair-guide/pull/172); the milestones are groups of
  commits in it. It merges only when `python scripts/check_all.py` passes in full on its head, so `main` never holds
  a partial identity model. The preview carries the w3id namespace from M1, while production keeps its namespace
  until M4's release, through the existing channel handling.
- **Rollback.** Before the release, the change reverts by reverting its pull request; no published artifact changes.
  After the switching release, rollback is a new release: earlier archives keep their bytes and contexts, and the
  redirect can point at any host.

## Open Questions

Raised by the graph-model review. The maintainer answered all of them on 2026-11-07 (task 3.11); each answer is
recorded in the decision named.

1. **How the native content rule asks for a question's text.** Answer: as `docs/content-model.md` does. Name the
   clause with `requirement`, and write a `statement` only where the question names another actor, covers part of
   the clause or must be reworded to be answerable (task 3.10).
2. **How the vocabulary states domains and ranges.** Answer: `rdfs:domain` and `rdfs:range`, each made true and
   checked against the class hierarchies of the pinned vocabularies; a declaration only `schema:Thing` would satisfy
   is omitted (decision 20). Not chosen: schema.org's non-inferential `domainIncludes` and `rangeIncludes`.
3. **The Node's status.** Answer: its node state only, with its date; the resource shape accepts a node state in
   place of a service status (decision 21). Not chosen: a five-level service status beside it.
4. **How a thing names its registry records.** Answer: on the record's side only, with `foaf:primaryTopic`; the
   thing does not name its records, and the page and the API read them from the records (decisions 4 and 15). The
   requirement *Registry records describe one thing* says so.
5. **The published sources of organisations and infrastructures.** Answer: `dcterms:source`, with the operator,
   operated-by and developer sources as its subproperties, all with IRI values (decision 22).
6. **Clause actors as audiences.** Answer: actor terms are also typed `Audience` (decision 6).
7. **Snapshots' records.** Answer: `hasPart` stays (decision 4).
8. **The direction of `hasPart`/`isPartOf` and of the FTR pair.** Answer: one direction per kind, recorded in the
   content model; a question names its check with `ftr:hasBenchmark`, and the check does not list its questions
   (decisions 8 and 22).
9. **The licence and citation of a quoted definition.** Answer: a `#definition` part of the term carries the quoted
   text, its licence and its citation (decision 22).
10. **Crate-local lists.** Answer: removed, except any a page view still reads (decision 22).
11. **The Guide's local tests.** Answer: no FTR type; they implement their question through SIO's link, and their
    results stay evidence (decision 8).
12. **A registry's classification of a thing.** Answer: the record's `dcterms:type`, such as a FIP Dashboard record's
    FIP class or an NKR record's repository kind; the thing's types come from the Guide's classification
    (decision 4).
13. **How the `tests` kind is selected**, found while recording these answers: it holds FTR tests, F-UJI's FTR
    metrics (the class questions also have) and local tests without an FTR type. Answer: every record of the kind is
    an `fg:AssessmentCriterion`, with its FTR type beside it where one applies (decisions 8 and 13). Not chosen:
    reading F-UJI's criteria as tests, or recording a reason for selecting the kind by IRI.
