# Tasks

Each group is one milestone; the whole change is one pull request,
[dsw-nrp/eosc-fair-guide#172](https://github.com/dsw-nrp/eosc-fair-guide/pull/172) (design.md, *Migration Plan*).
A group lands the tests and documentation its own work needs, and closes with the full checks. Run unit tests with
`python -m unittest tests/<file>.py`, and named checks with `python scripts/check_all.py --only <name>`. A group is
complete only when `python scripts/check_all.py` passes in full, and the pull request merges only when it passes on
its head in CI.

## 1. Baseline

- [x] 1.1 Rebase this branch on `main` once `polish-nkr-integration` has merged (or record that it will not). Rebuild,
  recount the figures in design.md *Context* (OpenAPI paths, page prefix literals, `sameAs` pairs, organisation
  families, repeated questions, advice items), and correct design.md where a figure changed. Verify: design.md cites
  the recount's date and commit.

## 2. Identity projection and kind vocabulary (M1)

- [x] 2.1 Replace `KIND_CODES` and `TYPE_CODES` in `scripts/catalogue_identity.py` with the kind vocabulary and scope
  rule, including the NKR branch of `preserve_snapshot`, which then mints `repositories` and leaves NKR's type to the
  repository kind through `NKR_KIND` (design.md decision 2). Verify: `tests/test_catalogue_identity.py` covers every
  kind and scope, fails on a classification segment and on an unknown kind, and gives a new disciplinary NKR record
  `repositories/<id>`.
- [x] 2.2 Set `namespace = "https://w3id.org/eosc-cz/fair-guide/"` in `content/guide.toml`, and change
  `scripts/build_crate.py` so that:
  - every Guide thing gets `<ns>id/<address>` as its `@id`;
  - parts get fragments under their thing;
  - data entities stay relative;
  - `catalogueAddress`, redundant `termCode`, ID-only `name` and collision counters are dropped (decision 3).

  Verify: a unit test fails on any Guide thing with a fragment `@id`, any `name` equal to its identifier, or any
  identifier ending in a counter; `python scripts/check_all.py --only crate profile` passes.
- [x] 2.3 Publish registry records as `dcat:CatalogRecord` with `foaf:primaryTopic` under their thing. Add FOAF to
  `ESTABLISHED_TERMS`. Resolve NKR's precedence onto the thing in place of the `_nkr` overrides, keep NKR's values on
  its record, and let a thing founded by a record carry its identity, name, address and filter facts (decision 4).
  Verify:
  - a unit test finds one Zenodo node with its KNAV and FIP Dashboard records attached, and one KNAV library
    organisation node;
  - with the NKR fixture (`tests/fixtures/nkr/`), one Czech-BioImaging node carries NKR's name and status and its
    `#nkr` record, and the herbarium repository is founded by its NKR record;
  - with Czech-BioImaging's curated handle removed, its address-free record founds a thing in development, without
    a web address and with `acceptsDeposits = false`.
- [x] 2.4 Rework `scripts/check_duplicates.py` so that every record attaches to exactly one thing, with the new
  review key: same registrable host, or same normalised name and provider (decision 5). Verify: tests report the
  CESNET ownCloud pair for review, keep the safe `--fix` suggestions for authoritative keys, and keep accepted groups
  accepted.
- [x] 2.5 Add `--renormalise` to `scripts/refresh_snapshots.py`: it rewrites `guideRoute` to the frozen kind and scope
  from the recorded snapshot, without a new observation, for every snapshot that carries it, NKR's included
  (decision 17). Verify: a unit test rewrites an NKR record's `repo/dom` route, a second run changes nothing, and
  `retrieved` dates are unchanged.
- [x] 2.6 Write `openspec/changes/unify-identity-model-and-api/migration/migrate.py` (decision 17), covering prose
  references, register kind names and provenance result IDs, with a dry-run diff and its own unit test. Run it,
  `--renormalise` and one provenance action with `results = ["*"]`. Verify: a second run changes nothing, and
  `python scripts/check_all.py --only content duplicates` passes.
- [x] 2.7 Enforce one reference syntax in `scripts/check_content.py`, so that a retired form fails with the address
  form named (decision 16). Verify: unit tests cover each retired form and a valid scoped address.
- [x] 2.8 Rework the page scripts in `assets/js/`:
  - key the data by address and add `FG.kind`;
  - remove `catalogueKinds`, `FG.catalogueCode` and `FG.catalogueKind`;
  - route the catalogue by address under the lens, `#/<lang>/<lens>/catalogue/<kind>/<id>`;
  - add the `#/id/<address>` entry route, which applies the saved language and lens, or else Czech with the `V`
    lens, and replaces itself with the full route;
  - use bare-ID anchors;
  - label the Guide's own IRI chip, with its strings in `content/ui.toml` in both languages (decision 15).

  Verify:
  - a page test fails on any remaining entity fragment-prefix test;
  - `npm run check:page` covers `#/id/` for a resource, a station and an unknown address in both languages, and
    opens it with a saved data-steward lens;
  - a shared `DS` catalogue link opens with that lens, and an embedded Guide asked for `#/id/` publishes the full
    route to its host.
- [x] 2.9 Move the routes and addresses that Python, page and API tests hard-code into one shared address helper
  per test language, including `tests/test_nkr_integration.py` and the `catalogue/repo/...` routes in
  `tests/page/check_page.mjs`. Verify: a search for code addresses (`res/`, `step/`, `cl/` and others) in `tests/`
  finds none.
- [x] 2.10 Update `docs/content-model.md` (*Identifiers*, *Crate mapping*, references) and `docs/design.md`, and the
  native rule `.agents/guide/rules/fair-guide-content.md`. Run `python scripts/generate_agent_surfaces.py`. Verify:
  `python scripts/check_all.py --only docs agent-generation agent-ownership` passes.
- [x] 2.11 Add the `[Unreleased]` breaking lines to `CHANGELOG.md` for addresses, routes, the reference syntax and
  the namespace. Verify: `python scripts/check_all.py --only changelog` passes.
- [x] 2.12 Validate the content's `baseUrl` also when `FAIR_GUIDE_BASE_URL` gives the build its publication
  location. Verify: `tests/test_scripts.py`'s HTTPS test passes with the variable set, as in CI, and without it.
- [x] 2.13 Publish re3data's repository rows and the FAIRsharing and DataCite annotations as `#re3data`,
  `#fairsharing` and `#datacite` records, with the winning values on the thing in the documented order, a repository
  only re3data knows founded by its record, and every thing naming its records in `isBasedOn` (decision 4). Verify:
  unit tests find `datarepo`'s `#re3data` record keeping re3data's values, a `#fairsharing` record with the DOI in
  the thing's `sameAs`, a `#datacite` record, and every registry record named by its thing; `npm run check:page`
  passes.
- [x] 2.14 Let a snapshot hold its records: list the KNAV and FIP Dashboard records in their snapshots' `hasPart`,
  each snapshot `about` its catalogue's resource, and drop `#knav-tools` and `#fers` (decision 4). Verify: a unit test
  finds no crate-local registry list and every record in its snapshot; `npm run check:page` passes.
- [x] 2.15 Resolve named agents to the one thing of that exact name, in any language and of any kind; accept an
  address in an agent field; refuse an ambiguous name; attach FIP Dashboard organisation records, under
  `#fip-dashboard-organization`, only by ROR or a reviewed handle (`fipDashboard` on an organisation or
  infrastructure row, `fipDashboardOrganization` on a resource row), added for today's name matches; report
  name-only matches for review (decisions 4 and 5). Verify: unit tests find no two described things of one exact
  name outside an accepted group, "Charles University" resolving to `organizations/cuni`, the publisher "Zenodo"
  resolving to `repositories/zenodo`, DataCite holding both of its FIP Dashboard records, and a name-only
  organisation record listed for review.
- [x] 2.16 Name records by address in the fields that can name several kinds: provenance `objects`, model association
  targets and the worked example's steps, through `migrate.py` (decision 16). Verify: a second migration run changes
  nothing, and the content check rejects a bare ID in each field with the address form named.
- [x] 2.17 Key the identifier register by record kind, with each value the address without the kind (vocabularies,
  callouts with their items, stations with the model contexts, models, layers, seams, model examples, life cycles,
  crosswalks, tests with their scope, and sources within resources), through `migrate.py`, `issued_ids` and
  `scripts/register_ids.py` (decision 17). Verify: a unit test finds every register key in the kind vocabulary, and
  `python scripts/check_all.py --only content` passes.
- [x] 2.18 Resolve result prefixes to records and to parts only where the pattern names one, record the Guide as the
  crate result of an action whose result is `*`, and drop the `identity-migration` instrument (decision 17). Verify:
  unit tests cover both prefix forms and the `*` action; the catalogue entry of `actions/2026-11-06-identity-migration`
  names the Guide only.
- [x] 2.19 Move every form older than this change out of `scripts/` and `tests/`: the route table, the word forms,
  the code prefixes, `refresh_snapshots.py --renormalise --routes` and their tests go into `migration/`, and the
  content check names the record whose ID ends an unknown reference (decisions 16 and 17). Verify: a search of
  `scripts/` and `tests/` for code addresses and word forms finds none, and `migration/test_migrate.py` passes.
- [x] 2.20 Rework the page's identifiers and sources: identifier chips without labels, every catalogue entry showing
  its own IRI, "Vychází z" / "Based on" from the entry's `isBasedOn` with each catalogue's snapshot date, and the
  repository family named "Repozitáře" / "Repositories", with unused strings removed from `content/ui.toml`
  (decision 15). Verify: `npm run check:page` covers the three scenarios of *An entry credits the catalogues that
  supplied it* and an IRI chip in an entry of every kind, in both languages.
- [x] 2.21 Replace `[[profile|...]]` with a reference to the machines page's section that presents the profile, so
  only records and kinds remain as targets (decision 16). Verify: the content check refuses a target that is neither
  a record nor a kind.
- [x] 2.22 Remove every citation of this change from code, tests, content and durable documents (the design's
  decisions, its tasks and its migration), and add a check that fails on one (design.md, *Context*). Verify: the check
  fails on a planted citation and passes on the tree.
- [x] 2.23 Update `docs/content-model.md`, `docs/design.md`, the native content rule (regenerated) and
  `CHANGELOG.md` for tasks 2.13 to 2.22. Verify: `python scripts/check_all.py --only docs agent-generation
  agent-ownership changelog` passes.
- [x] 2.24 Inspect the catalogue, a record of each kind and the identifier input in Czech and English, at phone width
  and in print. Then run `python scripts/check_all.py`. Verify: the full run passes locally, and CI passes on the pull
  request's head.
- [x] 2.25 Give every page section in `content/pages.toml` a reviewed `id`, through `migrate.py`, and make
  `scripts/check_content.py` refuse a section without one. The section's `id` is its fragment wherever the section is
  named: in the crate, in the page's list of folded sections and in references (decision 15). Verify: a unit test
  finds no page section whose fragment is its position, the content check rejects a section without an `id`, and a
  second migration run changes nothing.
- [x] 2.26 Reorder the machines page in `content/pages.toml`: the introduction, *Co hledáte* (`tasks`), the worked
  example (`model-example`), the Guide's practice (`practice`), then the API endpoints (`endpoints`) (decision 15).
  Verify: `npm run check:page` finds that order in Czech and English, and every section keeps its IRI.
- [x] 2.27 Rewrite every citation of a change in its own words, in every form a change has used: the D-numbers
  (`D-172`), `design Dn`, `(decision N)`, `(design: group N)` and `(task N.N)`. Widen the check from 2.22
  (`change_citations` in `scripts/check_docs.py`) to all these forms, to the `.github` workflows, scripts and
  `repository.toml`, and to `assets/css/` (design.md, *Context*). Tests that plant a citation build it from fragments.
  The repository audit's `task` field stays, since naming the step that applies a pending setting is its job.
  Verify: the check fails on each planted form and passes on the tree.

## 3. One graph model (M2)

- [x] 3.1 Model every controlled term as a `DefinedTerm` in one `DefinedTermSet`, with membership stated once.
  Publish the SKOS alignment once in `terms/fair-guide.ttl`, and update `GUIDE_TERMS` with shapes or reasons
  (decision 6). Verify: a unit test finds no `skos:inScheme` on any instance and finds the alignment axioms in the
  vocabulary document; `python scripts/check_all.py --only content` passes.
- [x] 3.2 Make every status a term of its scheme, through properties that specialise `adms:status`, and remove
  `creativeWorkStatus` strings. Verify: a unit test finds no status literal, and the stale-status test in
  `tests/test_health.py` still reports an expired `asOf`.
- [x] 3.3 Give advice items the class `fg:AdviceItem` and an `adviceKind` term, with steps and actions as parts
  (decision 7). Verify: the profile shape targets the class, pyshacl passes, and a unit test counts every authored
  advice item once.
- [x] 3.4 Type checks and questions as FTR benchmarks and metrics. Generate the manual tests at `tests/self-check/`,
  state the FTR relations and drop their schema.org duplicates (decision 8). Verify: a unit test finds one manual test
  per question and every FTR relation; `npm run check:assessment` passes.
- [x] 3.5 Publish pre-fill mappings as `fg:PrefillMapping` and read them on the page (decision 9). Verify: a unit test
  finds `dataset.01`'s DataCite mapping with field and coverage; the catalogue scenario *A check question shows how it
  is answered* passes in `npm run check:page`.
- [x] 3.6 Make the content check reject copied statements. Migrate the 55 questions through `requirement`: the 51 that
  copy their `requirement` clause drop `statement`, and `gate.01`, `gate.08`, `gate.10` and `maturity.14` gain
  `requirement` and drop theirs. Move `maturity.14`'s references into `A.I3.R2` (decision 10). Verify:
  - unit tests cover the rejection and the build output for a question without a `statement`;
  - `content/checks/` holds no statement identical to a cited clause;
  - the affected questions read the same in both languages.
- [x] 3.7 Move the profile to `0.2`, with shapes for every kind's class, catalogue records, term sets, the FTR types
  and pre-fill mappings. Keep the `Repository` shape's not-yet-public exception (an HTTPS address, or planned or in
  development with an NKR page in `sameAs`), with its status test on the decision-6 term (decision 4). Verify:
  `python scripts/check_all.py --only crate profile` passes, and the profile accepts an address-free NKR repository
  in development and rejects an operational one.
- [x] 3.8 Update `docs/content-model.md` (*Term classification*, *Statuses*, `checks/<id>.toml`) and `docs/design.md`.
  Verify: `python scripts/check_all.py --only docs` passes.
- [x] 3.9 Run `python scripts/check_all.py`. Verify: the full run passes locally, and CI passes on the pull request's
  head.

Tasks 3.10 to 3.22 answer the graph-model review of 2026-11-07 (design.md, *Context*). M2 closes again with 3.22,
before any M3 task starts.

- [x] 3.10 Update the native rule `.agents/guide/rules/fair-guide-content.md` for questions as open question 1 settles,
  then run `python scripts/generate_agent_surfaces.py`. Verify:
  `python scripts/check_all.py --only docs agent-generation agent-ownership` passes, and the vendor mirrors carry the
  new text.
- [x] 3.11 **Hand-off (maintainer):** answer open questions 1 to 12 in design.md, and record each answer in its decision
  (4, 8, 20, 21 or 22). Verify: design.md's *Open Questions* lists no question without an answer.
- [x] 3.12 Pin every vocabulary the graph refers to and write each term at the IRI its vocabulary defines
  (decision 23):
  - keep a copy of each vocabulary (schema.org, DCTERMS, DCAT, FOAF, SKOS, DQV, PROV-O, FTR, ADMS, SIO, the FIP
    ontology, PROF, the FAIR principles terms) under `tests/fixtures/`, each with its source, retrieval date and
    licence;
  - add a check that reads only those copies and fails on a namespace without one and on a term its vocabulary does
    not define at the IRI used;
  - write SIO's `http://semanticscience.org/resource/SIO_000233` in the crate context, the profile's test shape, the
    API, `docs/content-model.md` and the tests, and the helper pages' class in schema.org's `http` form.

  Verify: the check fails on a planted `https` schema.org class and on an unpinned namespace, and passes on the tree;
  a unit test finds every implementation link under SIO's `http` IRI and none under `https`;
  `python scripts/check_all.py --only crate profile` passes.
- [x] 3.13 Make the vocabulary's declarations hold for the graph (decision 20), reading the pinned vocabularies:
  - state domains and ranges as open question 2 settles, and correct the ones the review found;
  - `assessmentContext` stops specialising `dcterms:description`, and `disclosureLevel` stops specialising
    `schema:position`;
  - keep `guideSources` and `guideState`, which exported results carry, and count the export's terms as used;
  - add a check over the built graph that fails on a use outside a declaration and on an unused term;
  - remove the membership exemption from the organisation shape in `profile/fair-guide/must/2_model.ttl`.

  Verify:
  - the check fails on a planted wrong domain, range, datatype and specialised range, and passes on the tree;
  - an RDFS closure of the crate with the vocabulary adds no class to a Guide node beyond its asserted classes'
    superclasses;
  - `python scripts/check_all.py --only crate profile` passes.
- [x] 3.14 Type every registry record as `dcat:CatalogRecord` and `schema:CreativeWork`, never with its thing's class,
  and state a FIP Dashboard record's FIP class as open question 12 settles (decision 4). Verify: a unit test finds
  every record with exactly those two classes, and selecting `schema:Organization` or a FIP class returns no record;
  `npm run check:page` passes.
- [x] 3.15 Select every kind by its class (decision 13):
  - write every class as `@type`, never as an `additionalType` string: the FIP classes, cited datasets and software,
    tools and helper pages;
  - type crosswalk correspondences by a class, with their basis a term;
  - add term sets for clause kinds, mapping bases, evaluator mapping coverage and model kinds to `content/guide.toml`,
    and schemes for the lists a registry publishes (KNAV's discipline groups, the FIP Dashboard's scopes);
  - give each kind that shares its class a Guide class (decision 13);
  - add a check that every kind has a class, a term set or a recorded reason.

  Verify: the check fails on a planted kind without one; a unit test finds no `additionalType` value that names a
  class and no controlled value as a string; `python scripts/check_all.py --only content crate profile` and
  `npm run check:page` pass.
- [x] 3.16 Make the profile's shapes select by class and require what defines each kind: the clause, resource,
  repository, model and test shapes (decision 13). Verify: a test removes each required property from a real node of
  every shape and gets a violation, including the five shapes the review found inert and the three a node could
  leave; pyshacl and the RO-Crate validator pass on the tree.
- [x] 3.17 Remove the manual tests and the `tests/self-check/` scope from the crate, the API and the kind vocabulary
  (decision 8). Type every record of the `tests` kind as `fg:AssessmentCriterion`, with FAIR Champion tests and
  FAIR-Checker criteria also `ftr:Test`, F-UJI criteria also `ftr:Metric`, and the local tests without an FTR type
  (open questions 11 and 13). Keep generating `api/tests/<question>.json` for revisions 1–3 (decision 14). Verify: unit
  tests find no manual test, every record of the kind an assessment criterion, every FAIR Champion test implementing
  the metric its FTR record names and no FAIR-Checker criterion naming one (FAIR-Checker publishes none; decision 8),
  every F-UJI criterion a metric and no local test with an FTR type; `npm run check:assessment` passes.
- [x] 3.18 State each relation in one direction and use schema.org within its domains (decision 22), as open
  questions 4 to 10 settle:
  - term-set membership by the term only;
  - one direction per relation per kind, recorded in `docs/content-model.md`;
  - the link between a thing and its registry records, and the sources of organisations and infrastructures;
  - clause actors, quoted definitions' licence and citation, and the crate-local lists;
  - distinct source properties with IRI values, and IRI references for RDMkit records, training searches and
    licences;
  - a check of every schema.org use against the pinned schema.org copy (3.12).

  Verify: the schema.org check fails on a planted use outside a domain and a range, and passes on the tree; a unit
  test finds no relation stated in both directions and no set that lists its terms; `npm run check:page` passes.
- [x] 3.19 Make the EOSC CZ Node a platform (decision 21):
  - move it to `resources/eosc-cz-node` as a `schema:Service` operated through `schema:provider`, with its state as
    open question 3 settles, and update the register;
  - record onboarding as `dcat:qualifiedRelation` parts typed `dcat:Relationship`, with `dcterms:relation`,
    `dcat:hadRole`, milestone, date checked, charter and locator;
  - drop `fg:nodeMembership`, and read the badge and the facet from the Node's relations;
  - cite the EOSC Federation Handbook 2.0 (doi:10.5281/zenodo.18454649) in `content/sources.toml`, with paradata.

  Verify:
  - a unit test finds MBDB's relation with its role, milestone, date and source, and no `schema:member` on the Node;
  - under RDFS reasoning, no relation, service or repository is an organisation;
  - `npm run check:page` covers a service's and a repository's badge and the node facet in Czech and English.
- [x] 3.20 Give the NRP Data Catch-all Repository (`content/resources.toml`, `datarepo`) a classification other than
  `registry`, with paradata. Verify: no repository carries the registry type, and
  `python scripts/check_all.py --only content duplicates` passes.
- [x] 3.21 Update `docs/content-model.md` (crate mapping, classes, the Node, records, statuses, kinds, relation
  directions and the pinned vocabularies), `docs/design.md` and `CHANGELOG.md` for tasks 3.10 to 3.20. Verify:
  `python scripts/check_all.py --only docs changelog` passes.
- [x] 3.22 Run `python scripts/check_all.py`. Verify: the full run passes locally, and CI passes on the pull request's
  head.

## 4. API v1 and graph access (M3)

- [x] 4.1 Rebuild `scripts/build_api.py` on the `api/v1/` layout (decision 11):
  - `index.json`;
  - lists from one filter-field table;
  - records that refer to vocabularies;
  - the advice collection;
  - `health.json` under the operations tag;
  - `api/tests/<question>.json` kept for saved results;
  - the old tree removed.

  Verify: unit tests in `tests/test_scripts.py` find every kind's list and records, the filter fields of each list
  entry, and no API file outside `api/v1/`, `api/tests/` and the documentation page.
- [x] 4.2 Describe the API with one list and one record operation per kind, typed schemas and term-set enums. Keep the
  `Repository` schema's not-yet-public exception with a referenced status term, and describe `acceptsDeposits` as
  `false` or absent (decisions 4 and 11). Change `tests/api/check_api.mjs` to match every file to exactly one template
  and to reject per-record operations. Verify: `npm run check:api` passes, its NKR probe accepts a repository in
  development without an address and rejects an operational one, and the Swagger page lists one tag per kind.
- [x] 4.3 Move the health snapshot's consumers and `docker/nginx.conf`'s `no-store` rule to `api/v1/health.json`.
  Verify: `python scripts/check_all.py --only health health-api` passes.
- [x] 4.4 Write `knowledge-graph.nt` with a standard-library writer and a pinned local RO-Crate 1.2 context
  (decision 12). Verify: a unit test proves it isomorphic to rdflib's parse of the crate, and the build makes no
  network request.
- [x] 4.5 Add the N-Triples distribution to the linkset and the HTML head as `describedby`. Verify:
  `npm run check:deployment` and the signposting test find it.
- [x] 4.6 Publish the six recipes with bilingual descriptions under `profile/0.2/recipes/`, with expected-result
  fixtures in `tests/fixtures/recipes/` and a unit test that runs each one (decision 13). Verify: the test passes,
  and fails on a copy of the graph with a renamed property.
- [x] 4.7 Update the machines page and the API documentation page:
  - the IRI and address patterns;
  - the record landing pages and what their typed links point to;
  - the RDF distribution;
  - the recipes;
  - API v1;
  - the table mapping Guide kinds to FIP Dashboard collections (F1);
  - the practice section's paragraph on addresses, which still says the permanent address is to be settled.

  Verify: `npm run check:page` passes for the machines page in both languages, at phone width and in print.
- [x] 4.8 Write saved results as format revision 4, with each reader's answer a `dqv:QualityMeasurement` of its
  question's persistent IRI and automated evidence naming its test's persistent IRI, and load revisions 1–3 with their
  `api/tests/` references (decision 14). Verify: `npm run check:assessment` loads a fixture of each revision and
  exports revision 4 with question and test IRIs.
- [x] 4.9 Update `docs/content-model.md` (*Static API*), `docs/design.md`, `docs/ci-reference.md` and the README
  endpoint mentions, and add the `[Unreleased]` breaking lines for API v1 and result revision 4. Verify:
  `python scripts/check_all.py --only docs changelog` passes.
- [x] 4.10 Write a landing page, `id/<address>.html`, for every issued address (decision 19): the fixed field set
  from the API record, both languages with `lang`, an anchored section per part, the typed links and the link into
  the Guide through `index.html#/id/<address>`. Verify:
  - a unit test finds one page per address, an anchor for every part fragment, and `cite-as` and `describedby`
    naming the record's IRI and API record;
  - a test compares each page's fields with its API record;
  - `npm run check:page` reads a resource's, a station's and a repository's page without JavaScript in both
    languages, at phone width and in print, and follows the link into the Guide from `file://`.
- [x] 4.11 Write the bilingual `404.html` with an absolute link to the catalogue search, add
  `error_page 404 /404.html` to `docker/nginx.conf`, and list the landing pages in the production sitemap
  (`build_crate.py`). Verify:
  - a unit test finds every landing page in the production sitemap and none in a preview build, and finds the
    `error_page` rule in `docker/nginx.conf`;
  - `npm run check:deployment`, whose server answers a missing path as Pages does, gets status 404 and the page for
    an unknown address.
- [x] 4.12 Run `python scripts/check_all.py`. Verify: the full run passes locally, and CI passes on the pull request's
  head.

Tasks 4.13 to 4.19 answer the 2026-11-08 implementation review. All 18 findings have a repair and regression proof;
CORR-002 stays out of scope because the shared provider-form identity predates this change.

- [x] 4.13 Keep verified current and documented predecessor artifacts reusable through assembly and image retries
  (DEPLOY-001 and DEPLOY-002). Recognize `api/v1/health.json` with `releaseStatus` and the generated 404 separately from
  `api/health.json` with `creativeWorkStatus` and no 404, require exactly one layout, preserve verified bytes and reject
  ambiguous or missing layouts before replacing output. Propagate the selected health path into the candidate image's
  probe. Verify: genuine old-shape and new-shape archives pass through Pages assembly, image preparation and health
  verification, and an ambiguous artifact fails before output replacement.
- [x] 4.14 Make the content migration retry safe from mixed old/new checkouts (DEPLOY-003). Accept reassignment and
  dependent renames only in recognized old or new states, write every changed TOML file through a same-directory
  temporary file and replace it atomically. Verify: fault injection at each write boundary leaves only complete old or
  new bytes, and a retry completes byte-for-byte like the uninterrupted migration; the repeated rename cannot collapse
  accepted duplicate identities.
- [x] 4.15 Publish every issued identity and guard every generated HTML output (CORR-001 and INT-004). Remove the
  curated organization/infrastructure ID filters from `api_records()` and extend `is_generated()` to root `404.html`
  and `id/**/*.html`. Verify: an independent crate-IRI-to-document check finds one list entry, API record and landing
  page for every issued address, including `infrastructures/hl-lhc` and `infrastructures/ctao`; staged root and nested
  generated HTML files fail the repository content check, while authored HTML remains accepted.
- [x] 4.16 Align list filter metadata and remove repeated API build work (INT-001, PERF-001 and PERF-002). Advertise
  only default filter fields supplied by summaries and derive the OpenAPI enum from the same decision; construct the
  registry-record index once per `Api` instance; deduplicate repeated schema-object identities before structural JSON
  deduplication. Verify: generic tests cover every default-field kind, call counts show one registry-index build and
  fewer serializations, and generated JSON/OpenAPI files are byte-identical.
- [x] 4.17 Complete static landing pages and deep-404 handling (INT-002, INT-003, INT-005, DEAD-002 and DEAD-003).
  Expand compact class IRIs through established prefix mappings; use one recursive walker for part indexing and
  rendering, including nested actions and vocabulary members; derive 404 stylesheet paths from the validated
  publication path; use shared `LANGS` and delete the unused description label. Verify: tests find exactly one anchor per
  issued fragment, `prov:Activity` expands to `http://www.w3.org/ns/prov#Activity`, a nested action and vocabulary term
  have static targets, and a nested missing address returns bilingual 404 text with both stylesheets loaded successfully.
- [x] 4.18 Correct profile and machine documentation contracts and remove retired residue (CORR-003, REF-INT-001,
  INT-006, DEAD-001 and DEAD-004). Require one declaration status with a planted status-free profile test; update both
  local-test documentation languages to `api/v1/tests/guide/<id>.json` and `api/v1/tests.json`; add the retained
  `/api/tests/{id}.json` operation to the accessible endpoint table and compare that surface with OpenAPI; delete the
  `#entry-localtest-` and Guide `operates` mappings. Verify: focused profile, local-test, endpoint and source searches
  pass, and every advertised endpoint and documented local-test link resolves to an emitted record.
- [ ] 4.19 Reconcile this change's evidence and close review remediation. Update the existing provenance action and
  rolling usage entry with the actual work and verification, without moving times merely to satisfy checks. Inspect all
  affected views in both languages, at desktop and phone widths and in print, including a newly enumerated organization,
  nested action anchors and nested 404 styling. Run `npm run openspec:validate` and `python scripts/check_all.py`.
  Verify: every review scenario and the complete local run pass and, after separately authorized commit/push, CI passes
  on the pull request's resulting head.

## 5. w3id registration and release (M4)

- [ ] 5.1 **Hand-off (maintainer):** obtain EOSC CZ's agreement to the `ids/eosc-cz/` folder, together with
  [dsw-nrp/eosc-fair-guide#32](https://github.com/dsw-nrp/eosc-fair-guide/issues/32)'s address question. Verify: the
  agreement and its date are recorded in
  [dsw-nrp/eosc-fair-guide#136](https://github.com/dsw-nrp/eosc-fair-guide/issues/136).
- [ ] 5.2 Draft `ids/eosc-cz/README.md`, `ids/eosc-cz/.htaccess`, `ids/eosc-cz/fair-guide/README.md`,
  `ids/eosc-cz/fair-guide/.htaccess` and the pull-request body in this change's `w3id/` folder (decision 18).
  Maintainers are `motyc` and `MarekSuchanek`. Verify: the registry's own checker passes on the drafts.
- [ ] 5.3 **Hand-off (maintainer approval):** present the exact files and pull-request body. Verify: the approval of
  that content is recorded in #136 before anything is sent.
- [ ] 5.4 Submit the approved files to `perma-id/w3id.org` from a fork, linking #136. Verify: the pull-request URL is
  recorded in #136, and the registry's automated checks pass.
- [ ] 5.5 **Hand-off (w3id maintainers):** the registry merges the pull request. Verify: `terms` and `profile/0.2`
  redirect as designed.
- [ ] 5.6 Add the w3id probe to the health watch, with the digest key `w3id:<iri>`, for `terms` (HTML and Turtle), the
  current profile and one record IRI per kind as JSON and HTML. The HTML probe requires a `Location` without a
  fragment that reaches the record's landing page. Verify: unit tests with recorded responses cover a correct
  redirect, a wrong target, a target with a fragment and a 500; a manual `--live` run passes.
- [ ] 5.7 Write `docs/runbooks/update-the-w3id-redirect.md` for a host move and an API major version. Verify:
  `python scripts/check_all.py --only docs` passes the runbook structure.
- [ ] 5.8 **Hand-off (maintainer):** prepare and tag the release that switches production to the w3id namespace,
  following `docs/runbooks/release.md`, only after 5.5. Verify: after publication, the probe shows the terms, the
  profile and the record IRIs resolving to the release, and #136 is closed.

## 6. Integration

- [ ] 6.1 After 5.8, run `npm run openspec:validate`, `python scripts/check_all.py` and
  `python scripts/check_all.py --live` against `main`. Verify: all pass, and a reader dereferences one IRI of each
  kind from outside the site, as JSON and in a browser.

## Workflow follow-up

- [dsw-nrp/eosc-fair-guide#171](https://github.com/dsw-nrp/eosc-fair-guide/issues/171), in the `v1.0.0` milestone,
  moves the profile, API and contract versions to their production values and confirms the deprecation rule.
- Archive this change once 6.1 passes and the project's review requirements are satisfied.
