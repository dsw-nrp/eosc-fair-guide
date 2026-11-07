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
- [ ] 3.9 Run `python scripts/check_all.py`. Verify: the full run passes locally, and CI passes on the pull request's
  head.

## 4. API v1 and graph access (M3)

- [ ] 4.1 Rebuild `scripts/build_api.py` on the `api/v1/` layout (decision 11):
  - `index.json`;
  - lists from one filter-field table;
  - records that refer to vocabularies;
  - the advice collection;
  - `health.json` under the operations tag;
  - `api/tests/<question>.json` kept for saved results;
  - the old tree removed.

  Verify: unit tests in `tests/test_scripts.py` find every kind's list and records, the filter fields of each list
  entry, and no API file outside `api/v1/`, `api/tests/` and the documentation page.
- [ ] 4.2 Describe the API with one list and one record operation per kind, typed schemas and term-set enums. Keep the
  `Repository` schema's not-yet-public exception with a referenced status term, and describe `acceptsDeposits` as
  `false` or absent (decisions 4 and 11). Change `tests/api/check_api.mjs` to match every file to exactly one template
  and to reject per-record operations. Verify: `npm run check:api` passes, its NKR probe accepts a repository in
  development without an address and rejects an operational one, and the Swagger page lists one tag per kind.
- [ ] 4.3 Move the health snapshot's consumers and `docker/nginx.conf`'s `no-store` rule to `api/v1/health.json`.
  Verify: `python scripts/check_all.py --only health health-api` passes.
- [ ] 4.4 Write `knowledge-graph.nt` with a standard-library writer and a pinned local RO-Crate 1.2 context
  (decision 12). Verify: a unit test proves it isomorphic to rdflib's parse of the crate, and the build makes no
  network request.
- [ ] 4.5 Add the N-Triples distribution to the linkset and the HTML head as `describedby`. Verify:
  `npm run check:deployment` and the signposting test find it.
- [ ] 4.6 Publish the six recipes with bilingual descriptions under `profile/0.2/recipes/`, with expected-result
  fixtures in `tests/fixtures/recipes/` and a unit test that runs each one (decision 13). Verify: the test passes,
  and fails on a copy of the graph with a renamed property.
- [ ] 4.7 Update the machines page and the API documentation page:
  - the IRI and address patterns;
  - the record landing pages and what their typed links point to;
  - the RDF distribution;
  - the recipes;
  - API v1;
  - the table mapping Guide kinds to FIP Dashboard collections (F1);
  - the practice section's paragraph on addresses, which still says the permanent address is to be settled.

  Verify: `npm run check:page` passes for the machines page in both languages, at phone width and in print.
- [ ] 4.8 Write saved results as format revision 4, with persistent test IRIs, and load revisions 1–3 with their
  `api/tests/` references (decision 14). Verify: `npm run check:assessment` loads a fixture of each revision and
  exports revision 4 with IRIs.
- [ ] 4.9 Update `docs/content-model.md` (*Static API*), `docs/design.md`, `docs/ci-reference.md` and the README
  endpoint mentions, and add the `[Unreleased]` breaking lines for API v1 and result revision 4. Verify:
  `python scripts/check_all.py --only docs changelog` passes.
- [ ] 4.10 Write a landing page, `id/<address>.html`, for every issued address (decision 19): the fixed field set
  from the API record, both languages with `lang`, an anchored section per part, the typed links and the link into
  the Guide through `index.html#/id/<address>`. Verify:
  - a unit test finds one page per address, an anchor for every part fragment, and `cite-as` and `describedby`
    naming the record's IRI and API record;
  - a test compares each page's fields with its API record;
  - `npm run check:page` reads a resource's, a station's and a repository's page without JavaScript in both
    languages, at phone width and in print, and follows the link into the Guide from `file://`.
- [ ] 4.11 Write the bilingual `404.html` with an absolute link to the catalogue search, add
  `error_page 404 /404.html` to `docker/nginx.conf`, and list the landing pages in the production sitemap
  (`build_crate.py`). Verify:
  - a unit test finds every landing page in the production sitemap and none in a preview build, and finds the
    `error_page` rule in `docker/nginx.conf`;
  - `npm run check:deployment`, whose server answers a missing path as Pages does, gets status 404 and the page for
    an unknown address.
- [ ] 4.12 Run `python scripts/check_all.py`. Verify: the full run passes locally, and CI passes on the pull request's
  head.

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
