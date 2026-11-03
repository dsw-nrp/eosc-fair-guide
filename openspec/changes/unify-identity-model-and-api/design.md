# Design

## Context

See proposal.md, *Why*, for the problem. The figures in this design were measured on a build of `1ec02bd`
(`polish-nkr-integration`, not yet merged) and on the published `1.0.0-alpha.5`. Implementation rebases on `main`
once that change merges and recounts them. The approach is bound by these constraints:

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
  place without compatibility routes (*The first release establishes the route baseline*, as modified here).

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
- Changing what any advice, question or requirement says, except the 71 statements merged into their clauses.
- Re-shaping the page beyond addressing, the identifier chip and the `#/id/` route.

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
  It sits at the thing's IRI plus `#<scheme>` (for example `.../repositories/zenodo#knav`). It carries the
  registry's own name, description, licence, retrieval date and source identifier, and it is part of its snapshot.
  FOAF joins the established vocabularies in `ESTABLISHED_TERMS`, for this one property.
- **A thing only a registry knows** is founded by its record. The thing node carries only its identity, its name and
  its address; the descriptive text stays on the record, with its attribution.
- **The page** shows one entry per thing, with each registry's record as an attributed section, as it does today for
  sources.
- **Alternatives rejected:**
  - Peer nodes with `sameAs` (R0): consumers have to merge them, and counts come out doubled.
  - `schema:about`: too weak, since a record can be about several topics.
  - Merging records into the thing (R2): it loses per-source attribution, which the content rules require.

### 5. Duplicate check attaches records

- **Its job** changes from "curated versus registry" to "every record attaches to exactly one thing".
- **Authoritative keys** (address, DOI, registry IDs, ROR) still attach a record automatically, and that link remains
  the safe `--fix` suggestion.
- **A new review key** catches the ownCloud case: the same registrable host, or the same normalised name with the
  same provider, between a record and a thing. It reports for review and never fixes automatically.
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
- **Alternatives rejected:**
  - SKOS only: the crate is schema.org-based, and RO-Crate tooling expects `DefinedTerm`.
  - Both on every instance (today): every membership is stated twice.

### 7. Advice, steps and actions

- **Advice items** (272) get the Guide class `fg:AdviceItem`, the IRI of today's SHACL shape. Its broader term is
  `schema:CreativeWork`, with the reason recorded: schema.org's HowTo types describe steps of a procedure, not
  advice addressed by lens and level.
- **Their kind** (direction or tip) becomes `adviceKind`, a term in the advice-kind scheme.
- **Steps** (52) stay `HowToDirection` parts at `#step-<n>` under their advice item's IRI. **Actions** (77) stay
  `potentialAction` parts at `#action`.

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

- **Authoring.** A question names its text's clause with `statementClause = "<clause id>"` instead of `statement`.
  It must be one of the question's `sources`; this is needed because 3 of the 71 cite more than one clause.
- **Output.** The build writes the clause's text as the question's `text` in every output, linking the clause as its
  basis. Readers and FTR consumers see a text, and the sources hold it once.
- **The content check** rejects a `statement` identical to the text of a cited clause in either language.
- **`maturity.14`** takes `A.I3.R2`'s text. Its ORCID and ROR references move into that clause.

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

- **Records** refer to vocabulary terms by address, with the term set published once, instead of embedding them;
  today `pr/R1.1` repeats one lens description 67 times.
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
  - Catalogue routes are `#/<lang>/catalogue/<kind>/<id>`, with `<scope>/` where needed.
  - `#/id/<address>` opens the catalogue entry, stations and checks included, in the saved language or else Czech.
  - An unknown address says so and offers search.
- **Identifier input.** Search and the identifier input accept a Guide IRI or an address.
- **Chips.** An ID chip still shows the record ID; its title names the full address. `FG.pids` labels the record's
  own w3id IRI as the Guide's identifier ("Identifikátor Průvodce" / "Guide identifier"), apart from external PIDs.
- **Anchors** for glossary terms and repositories become the bare ID.
- **Accessibility.** The new chip is a native link with a visible label and focus. It carries text, not colour
  alone, and wraps at slashes on narrow screens as PID chips already do.

### 16. One reference syntax

- **Prose** references are `[[<kind>/<id>|phrase]]` only, with the scope inside the address where there is one.
- **Retired forms:** `term:<id>`, `station:`, `clause:`, `page:`, `infrastructure:` and the code addresses. The
  content check rejects them and names the address form.
- **Documentation.** The native content rule in `.agents/guide/` and `docs/content-model.md` document the one
  syntax, and the vendor mirrors are regenerated.

### 17. Content migration

- **The script.** One standard-library script, `openspec/changes/unify-identity-model-and-api/migration/migrate.py`,
  owned by this change. It is idempotent, has a dry-run that prints the diff, and writes:
  - prose references: about 260 address forms plus the word forms;
  - `content/identifiers.toml` kind names (`requirements` becomes `clauses`, and the rest follow the kind table);
  - provenance `results` (`test:`, `provider:`, `infrastructure:` and other prefixes become addresses);
  - the 71 `statementClause` merges.
- **Snapshots** are generated files, so their `guideRoute` (219 records plus the glossary) is rewritten by a new
  `refresh_snapshots.py --renormalise` mode. It rereads the recorded snapshot without a new observation and keeps
  `retrieved`. `guideRoute` keeps its meaning, the frozen kind (and scope), so a later reclassification still cannot
  move an identity.
- **Paradata.** One provenance action, `<date>-unify-identity-model-and-api`, with `results = ["*"]` covers the
  freshness check. Its agent is the responsible maintainer; its instruments are the migration script and the AI model
  used; it is described as a structural migration. Content credit gains no person.

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
RewriteRule ^id/(.+)$ https://dsw-nrp.github.io/eosc-fair-guide/#/id/$1 [R=303,NE,L]
```

- **Coupling.** The rules depend only on three site paths: `terms/`, `profile/` and `api/v1/`, plus the permanent
  `#/id/` route. A host move ([dsw-nrp/eosc-fair-guide#32](https://github.com/dsw-nrp/eosc-fair-guide/issues/32)) or
  an API major version needs a registry pull request, and the new runbook `docs/runbooks/update-the-w3id-redirect.md`
  covers both.
- **Testing.** The rules are tested with the registry's own checker (`tools/check/` and `.w3id-check.yaml`) before
  submission, and with the probe after merge.
- **Watching.** The health watch probes, weekly, `terms` (HTML and Turtle), the current `profile`, and one record IRI
  per kind as JSON and HTML. A failure is reported in the digest under the key `w3id:<iri>`.

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
- [Hash-route redirects lose the language preference and depend on `NE` handling] → `#/id/` takes the saved language
  or Czech, and the probe checks the HTML route.
- [A third-party SKOS alignment in our vocabulary document could be read as overreach] → It is stated as
  subclass/subproperty axioms in the Guide's own document, never as equivalence, and the document says so.
- [Dropping `name` where it repeats the identifier removes a label some tools display] → The `identifier` and the
  text remain. Every kind's label field is declared in the API table, and the profile documents it.
- [The page rewrite (213 prefix literals) can regress views quietly] → `FG.kind` comes with a test that fails on any
  remaining prefix test. The full browser suite runs in both languages, at phone width and in print.
- [Saved results from alpha releases point at the old host path] → `api/tests/<question>.json` keeps being generated
  at the same relative path, and the loader maps them.
- [The design's counts come from an unmerged branch] → Recount after rebasing; tasks verify counts against the actual
  build.

## Migration Plan

```
 M1 identity        kind words, w3id namespace, one identity projection, R1 records, migration script,
                    page addressing and #/id/, one reference syntax, duplicate-attach check
      |
 M2 model           vocabulary and status model, advice class, FTR in graph, pre-fill mappings,
                    question text from clauses, profile 0.2
      |
 M3 access          API v1, OpenAPI templates, health under operations, N-Triples, recipes and their CI,
                    machines page, saved-result revision 4
      |
 M4 w3id + release  EOSC CZ consent, approved submission, registry merge, probe and runbook,
                    the release that switches production
```

- **Pull requests.** Each milestone is one pull request (M1 may split into generator and migration commits), merged
  with the full checks. The preview carries the w3id namespace from M1, while production keeps its namespace until
  M4's release, through the existing channel handling.
- **Rollback.** Before the release, a milestone reverts by reverting its pull request; no published artifact changes.
  After the switching release, rollback is a new release: earlier archives keep their bytes and contexts, and the
  redirect can point at any host.
