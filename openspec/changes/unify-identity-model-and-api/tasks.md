# Tasks

Each group is one milestone and one pull request (design.md, *Migration Plan*). A group lands the tests and
documentation its own work needs, and closes with the full checks. Run unit tests with
`python -m unittest tests/<file>.py`, and named checks with `python scripts/check_all.py --only <name>`. A group is
complete only when `python scripts/check_all.py` passes in full.

## 1. Baseline

- [ ] 1.1 Rebase this branch on `main` once `polish-nkr-integration` has merged (or record that it will not). Rebuild,
  recount the figures in design.md *Context* (OpenAPI paths, page prefix literals, `sameAs` pairs, organisation
  families, repeated questions, advice items), and correct design.md where a figure changed. Verify: design.md cites
  the recount's date and commit.

## 2. Identity projection and kind vocabulary (M1)

- [ ] 2.1 Replace `KIND_CODES` and `TYPE_CODES` in `scripts/catalogue_identity.py` with the kind vocabulary and scope
  rule (design.md decision 2). Verify: `tests/test_catalogue_identity.py` covers every kind and scope, and fails on a
  classification segment and on an unknown kind.
- [ ] 2.2 Set `namespace = "https://w3id.org/eosc-cz/fair-guide/"` in `content/guide.toml`, and change
  `scripts/build_crate.py` so that:
  - every Guide thing gets `<ns>id/<address>` as its `@id`;
  - parts get fragments under their thing;
  - data entities stay relative;
  - `catalogueAddress`, redundant `termCode`, ID-only `name` and collision counters are dropped (decision 3).

  Verify: a unit test fails on any Guide thing with a fragment `@id`, any `name` equal to its identifier, or any
  identifier ending in a counter; `python scripts/check_all.py --only crate profile` passes.
- [ ] 2.3 Publish registry records as `dcat:CatalogRecord` with `foaf:primaryTopic` under their thing. Add FOAF to
  `ESTABLISHED_TERMS`, and let a thing founded by a record carry only its identity, name and address (decision 4).
  Verify: a unit test finds one Zenodo node with its KNAV and FIP Dashboard records attached, and one KNAV library
  organisation node.
- [ ] 2.4 Rework `scripts/check_duplicates.py` so that every record attaches to exactly one thing, with the new
  review key: same registrable host, or same normalised name and provider (decision 5). Verify: tests report the
  CESNET ownCloud pair for review, keep the safe `--fix` suggestions for authoritative keys, and keep accepted groups
  accepted.
- [ ] 2.5 Add `--renormalise` to `scripts/refresh_snapshots.py`: it rewrites `guideRoute` to the frozen kind and scope
  from the recorded snapshot, without a new observation. Verify: a unit test shows a second run changes nothing and
  `retrieved` dates are unchanged.
- [ ] 2.6 Write `openspec/changes/unify-identity-model-and-api/migration/migrate.py` (decision 17), covering prose
  references, register kind names and provenance result IDs, with a dry-run diff and its own unit test. Run it,
  `--renormalise` and one provenance action with `results = ["*"]`. Verify: a second run changes nothing, and
  `python scripts/check_all.py --only content duplicates` passes.
- [ ] 2.7 Enforce one reference syntax in `scripts/check_content.py`, so that a retired form fails with the address
  form named (decision 16). Verify: unit tests cover each retired form and a valid scoped address.
- [ ] 2.8 Rework the page scripts in `assets/js/`:
  - key the data by address and add `FG.kind`;
  - remove `catalogueKinds`, `FG.catalogueCode` and `FG.catalogueKind`;
  - route the catalogue by address and add the permanent `#/id/<address>` route;
  - use bare-ID anchors;
  - label the Guide's own IRI chip, with its strings in `content/ui.toml` in both languages (decision 15).

  Verify: a page test fails on any remaining entity fragment-prefix test, and `npm run check:page` covers `#/id/`
  for a resource, a station and an unknown address in both languages.
- [ ] 2.9 Move the routes and addresses that Python, page and API tests hard-code into one shared address helper
  per test language. Verify: a search for code addresses (`res/`, `step/`, `cl/` and others) in `tests/` finds none.
- [ ] 2.10 Update `docs/content-model.md` (*Identifiers*, *Crate mapping*, references) and `docs/design.md`, and the
  native rule `.agents/guide/rules/fair-guide-content.md`. Run `python scripts/generate_agent_surfaces.py`. Verify:
  `python scripts/check_all.py --only docs agent-generation agent-ownership` passes.
- [ ] 2.11 Add the `[Unreleased]` breaking lines to `CHANGELOG.md` for addresses, routes, the reference syntax and
  the namespace. Verify: `python scripts/check_all.py --only changelog` passes.
- [ ] 2.12 Inspect the catalogue, a record of each kind and the identifier input in Czech and English, at phone width
  and in print. Then run `python scripts/check_all.py`. Verify: the full run passes, and the M1 pull request is open
  for human review.

## 3. One graph model (M2)

- [ ] 3.1 Model every controlled term as a `DefinedTerm` in one `DefinedTermSet`, with membership stated once.
  Publish the SKOS alignment once in `terms/fair-guide.ttl`, and update `GUIDE_TERMS` with shapes or reasons
  (decision 6). Verify: a unit test finds no `skos:inScheme` on any instance and finds the alignment axioms in the
  vocabulary document; `python scripts/check_all.py --only content` passes.
- [ ] 3.2 Make every status a term of its scheme, through properties that specialise `adms:status`, and remove
  `creativeWorkStatus` strings. Verify: a unit test finds no status literal, and the stale-status test in
  `tests/test_health.py` still reports an expired `asOf`.
- [ ] 3.3 Give advice items the class `fg:AdviceItem` and an `adviceKind` term, with steps and actions as parts
  (decision 7). Verify: the profile shape targets the class, pyshacl passes, and a unit test counts every authored
  advice item once.
- [ ] 3.4 Type checks and questions as FTR benchmarks and metrics. Generate the manual tests at `tests/self-check/`,
  state the FTR relations and drop their schema.org duplicates (decision 8). Verify: a unit test finds one manual test
  per question and every FTR relation; `npm run check:assessment` passes.
- [ ] 3.5 Publish pre-fill mappings as `fg:PrefillMapping` and read them on the page (decision 9). Verify: a unit test
  finds `dataset.01`'s DataCite mapping with field and coverage; the catalogue scenario *A check question shows how it
  is answered* passes in `npm run check:page`.
- [ ] 3.6 Add `statementClause` to the check content model and make the content check reject copied statements. Make
  the build write the clause text, migrate the 71 questions, and move `maturity.14`'s references into `A.I3.R2`
  (decision 10). Verify:
  - unit tests cover the field, the rejection and the build output;
  - `content/checks/` holds no statement identical to a cited clause;
  - the affected questions read the same in both languages.
- [ ] 3.7 Move the profile to `0.2`, with shapes for every kind's class, catalogue records, term sets, the FTR types
  and pre-fill mappings. Verify: `python scripts/check_all.py --only crate profile` passes.
- [ ] 3.8 Update `docs/content-model.md` (*Term classification*, *Statuses*, `checks/<id>.toml`) and `docs/design.md`.
  Verify: `python scripts/check_all.py --only docs` passes.
- [ ] 3.9 Run `python scripts/check_all.py`. Verify: the full run passes, and the M2 pull request is open for human
  review.

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
- [ ] 4.2 Describe the API with one list and one record operation per kind, typed schemas and term-set enums. Change
  `tests/api/check_api.mjs` to match every file to exactly one template and to reject per-record operations. Verify:
  `npm run check:api` passes, and the Swagger page lists one tag per kind.
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
  - the RDF distribution;
  - the recipes;
  - API v1;
  - the table mapping Guide kinds to FIP Dashboard collections (F1).

  Verify: `npm run check:page` passes for the machines page in both languages, at phone width and in print.
- [ ] 4.8 Write saved results as format revision 4, with persistent test IRIs, and load revisions 1–3 with their
  `api/tests/` references (decision 14). Verify: `npm run check:assessment` loads a fixture of each revision and
  exports revision 4 with IRIs.
- [ ] 4.9 Update `docs/content-model.md` (*Static API*), `docs/design.md`, `docs/ci-reference.md` and the README
  endpoint mentions, and add the `[Unreleased]` breaking lines for API v1 and result revision 4. Verify:
  `python scripts/check_all.py --only docs changelog` passes.
- [ ] 4.10 Run `python scripts/check_all.py`. Verify: the full run passes, and the M3 pull request is open for human
  review.

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
  current profile and one record IRI per kind as JSON and HTML. Verify: unit tests with recorded responses cover a
  correct redirect, a wrong target and a 500; a manual `--live` run passes.
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
