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
- **Durable prose.** Code, tests, content and durable documents cite no part of this change. They explain a rule in
  their own words and name no design decision, task or migration step; this change's artifacts stay under
  `openspec/changes/`, and knowledge of the old forms lives only in its `migration/` folder.

## Goals / Non-Goals

**Goals:**

- One identity projection, from the Guide-owned ID to the address, shared by the IRI, API path, page route, prose
  reference, page data key and export.
- One graph model, published three ways: the crate, N-Triples and the API, with no translation layer between them.
- A contract that consumers can test against (profile, OpenAPI, recipes), with a deprecation rule from `1.0.0`.
- External IRIs that survive a host move with one redirect change.

**Non-Goals:**

- A query runtime of any kind (B and C in the exploration), SQL or tabular distributions, and an in-browser query
  console.
- Changing what any advice, question or requirement says, except the 55 statements merged into their clauses.
- Re-shaping the page beyond addressing, identifier chips, credited sources, the repository family's name, the
  `#/id/` entry route and the record landing pages (decision 19).

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
| (API only) | `tests` | `self-check` (the manual test of each question) | |
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
  It sits at the thing's IRI plus `#<scheme>`: `#knav`, `#fip-dashboard`, `#nkr`, `#re3data`, `#fairsharing` or
  `#datacite` (for example `.../repositories/zenodo#knav`). It carries the registry's own name, description, licence,
  retrieval date and source identifier, and it is part of its snapshot. FOAF joins the established vocabularies in
  `ESTABLISHED_TERMS`, for this one property.
- **Every registry is treated alike.** re3data's repository rows and the FAIRsharing and DataCite annotations become
  records as the KNAV, FIP Dashboard and NKR rows do, instead of merging into the thing. A FAIRsharing record carries
  its DOI and name, a DataCite record its repository ID; the thing keeps the DOI in `sameAs`.
- **The thing rests on its records.** Every thing names each of its registry records in `isBasedOn`, beside the
  Guide's curated list where it is curated, and each record names its snapshot. A consumer reads from the graph
  which catalogues supplied a thing, and the page credits them from the same statements (decision 15).
- **A snapshot holds its records.** The KNAV catalogue's and the FIP Dashboard's record lists are their snapshots:
  each snapshot lists its records in `hasPart` and is `about` the catalogue's own resource
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
  through its ROR or a reviewed `fipDashboard` handle on the curated organisation, infrastructure or resource row,
  never through its name. A record that names no thing founds one; the duplicate check reports one whose name a
  described thing shares, for review.
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
  repository kinds, statuses, glossary terms, principles, layers and life-cycle stages. Lenses keep `Audience` as a
  second type, because `audience` requires it.
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
- **Manual tests.** Each question's manual test is an `ftr:Test` at `tests/self-check/<question>`, generated by the
  build into the crate (214 today).
- **Relations.** The graph states the FTR relations (`ftr:hasAssociatedMetric`, `ftr:hasBenchmark`,
  `dqv:inDimension`, SIO implementation links) and drops the schema.org duplicates for the same relation.
- **The API** uses these names as they are, so `RENAMED`, `DROPPED` and `FTR_TYPES` disappear from
  `build_api.py`.
- **Local tests.** A local test's three entities (record, documentation file and entry point) remain. The entry
  point is the test's executable reference, and the profile documents it.

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

### 12. RDF distribution

- **The writer.** The build writes `knowledge-graph.nt` beside the crate, with a small standard-library writer. It
  expands the build's own graph using the term map the build already owns (the crate's inline context plus the
  RO-Crate terms it uses, from a pinned local copy of the RO-Crate 1.2 context).
- **The check.** A test proves that the triples equal rdflib's parse of the crate (graph isomorphism).
- **Signposting.** The linkset and HTML head add it as `describedby` with type `application/n-triples`.
- **Alternative rejected:** rdflib or a JSON-LD processor at build time, which would break the standard-library build
  rule.

### 13. Query contract and recipes

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

- **Revision 4.** Results name tests by IRI: `<ns>id/tests/self-check/<question>`, or the automated test's own IRI.
- **Older revisions.** Revisions 1–3 still load. The loader already keys answers by question ID, and it reads their
  `api/tests/<question>.json` references as the same question's test.
- **Old test paths.** The build keeps generating `api/tests/<question>.json`, as the manual-test documents that
  saved files name. This is the separate saved-result support the route-baseline requirement keeps; no other old path
  survives.

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
- **Chips.** An ID chip still shows the record ID; its title names the full address. Every catalogue entry, of every
  kind and in the list as well as alone, shows its own persistent IRI first among its identifiers. No identifier chip
  carries a label: an identifier is shown in full, and its address already says what issued it ("Identifikátor
  Průvodce", "re3data" or "FAIRsharing" would only repeat it).
- **Credited sources.** An entry's "Vychází z" / "Based on" row reads its `isBasedOn` (decision 4): the Guide's
  selection where the entry is curated, and the catalogue of each registry record under it, each leading to that
  catalogue's own entry with its snapshot's date. A registry that only identifies the thing, without a record (an NKR
  handle before NKR's first snapshot), is shown among the identifiers and not credited as a source.
- **The repository family** is "Repozitáře" / "Repositories": registries are resources (decision 2), so a registry
  is listed and filtered with the resources.
- **Anchors** for glossary terms and repositories become the bare ID.
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
  that writes the API records. It is static and bilingual: Czech first, each language marked with `lang`, as the
  page's `noscript` text already is. It needs no JavaScript and makes no request beyond its own stylesheet.
- **Content.** A fixed set of fields taken from the API record it signposts:
  - name, text and kind, the Guide-identifier chip and external identifiers;
  - status with its date, where the kind has one;
  - one section per part, anchored by the part's fragment (`#knav`, `#step-2`, `#action`), with each registry
    record's attribution and licence;
  - links to related records' landing pages.
- **Signposting.** The head carries `cite-as` (the record's IRI), `describedby` (its API record, typed
  `application/ld+json`), `type`, `license` and `collection` (the Guide). The Guide root keeps its own links.
- **Into the Guide.** "Otevřít v Průvodci" / "Open in the Guide" links to `<root>index.html#/id/<address>` with an
  explicit `index.html`, so it works from `file://` too; the route applies the reader's language and lens (decision
  15).
- **Unknown addresses.** The build writes a bilingual `404.html` that says no catalogue entry has the address and
  links to the catalogue search. Pages serves it for any missing path; `docker/nginx.conf` adds
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

## Risks / Trade-offs

- [The migration touches almost every content file, and review cannot read it line by line] → It is one idempotent
  script with a dry-run. The reviewer checks the script, its tests and a sampled diff per kind. The build refuses
  dangling or ambiguous addresses.
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
- [About as many small HTML files as API records enlarge the site] → They are static and short; task 1.1's recount
  gives the number, and the release size is checked in the M3 pull request.
- [A third-party SKOS alignment in our vocabulary document could be read as overreach] → It is stated as
  subclass/subproperty axioms in the Guide's own document, never as equivalence, and the document says so.
- [Dropping `name` where it repeats the identifier removes a label some tools display] → The `identifier` and the
  text remain. Every kind's label field is declared in the API table, and the profile documents it.
- [The page rewrite (213 prefix literals) can regress views quietly] → `FG.kind` comes with a test that fails on any
  remaining prefix test. The full browser suite runs in both languages, at phone width and in print.
- [Saved results from alpha releases point at the old host path] → `api/tests/<question>.json` keeps being generated
  at the same relative path, and the loader maps them.
- [The build figures were measured on `1ec02bd`, before its last review rounds] → Task 1.1 recounted both builds
  with one script and found no change (*Context*). Later tasks verify their counts against the actual build.
- [A named agent that resolves to a service makes a resource or repository the `publisher` of a work, where a reader
  of schema.org expects an organisation] → One node per name is what the catalogue shows anyway, and the profile
  allows any described thing as an agent. A name that should mean the organisation and not the service names the
  organisation's address in the content.
- [Two kinds of thing legitimately share a name, such as the Czech National Corpus infrastructure and its corpus
  repository] → The build refuses the ambiguous agent name, the content names the agent by address, and an accepted
  group records why the two are separate.
- [A founded thing moves its description to its record, so a consumer reading only the thing's node finds less] →
  The record is under the thing's IRI, the thing names it in `isBasedOn`, and the API record of the thing carries
  its records (decision 11).

## Migration Plan

```
 M1 identity        kind words, w3id namespace, one identity projection, R1 records, migration script,
                    page addressing and #/id/, one reference syntax, duplicate-attach check
      |
 M2 model           vocabulary and status model, advice class, FTR in graph, pre-fill mappings,
                    question text from clauses, profile 0.2
      |
 M3 access          API v1, OpenAPI templates, health under operations, N-Triples, recipes and their CI,
                    record landing pages, 404 page and sitemap, machines page, saved-result revision 4
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
