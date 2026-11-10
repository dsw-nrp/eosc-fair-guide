# Unify identity, model and API

## Claude Code session (explore and capture)

- **When:** 2026-11-02 to 2026-11-03 (+01:00)
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none (GitHub was reached through the `gh` CLI)
- **Workflow context used:** `openspec-explore` (the maintainer asked for the full change to be built after the
  exploration), `aiscr-plan-issue` for the `v1.0.0` follow-up issue; delivered `aiscr-planning-core`,
  `aiscr-quality-first-execution`, `aiscr-openspec-posture`, `aiscr-usage-logging` and `aiscr-model-logging` rules;
  the native `fair-guide-content` and `fair-guide-surfaces` rules; the pinned `npx openspec` CLI; `gh` reads of
  issues #25, #32, #33 and #136, the `perma-id/w3id.org` registry layout and the FIP Dashboard OpenAPI description;
  read-only probes of the built crate (rdflib parse and one SPARQL query) and of the published API.
- **What:**
  - Evaluated the published static API (1,521 literal OpenAPI paths, two templated) and traced the cause to two
    unaligned partitionings: role-named lists and kind/type-coded record addresses.
  - Profiled the crate's data model and found duplicated identities, peer registry nodes, unlinked duplicates,
    several identity forms per entity, two models (crate and API), three vocabulary and seven status modellings,
    and 71 questions that restate their clause.
  - Agreed with the maintainer on: option A for the API, F1 for FIP Dashboard naming, D2 for graph access, I3 and
    R1 for identity, plural word kinds, the namespace `https://w3id.org/eosc-cz/fair-guide/` with maintainers
    `motyc` and `MarekSuchanek`, merging the repeated questions, `#/id/` opening the catalogue entry, and nothing
    permanent before `1.0.0`.
  - Captured the OpenSpec change `unify-identity-model-and-api` with its proposal, four spec deltas
    (knowledge base, experience, delivery, self-check), design and tasks, on the branch
    `agents/claude/unify-identity-model-and-api`, created from `origin/main` after `git fetch`.
  - Shaped the `v1.0.0` follow-up issue through `aiscr-plan-issue`. After the maintainer approved its digest, posted
    it as [dsw-nrp/eosc-fair-guide#171](https://github.com/dsw-nrp/eosc-fair-guide/issues/171), with the confirmed
    triage: milestone `v1.0.0`, label `area:delivery`, Priority Medium, Effort Low, Project #1 status Ready. The
    change now links it, and the run's hand-off directory was cleaned up.
- **Impacted:** `openspec/changes/unify-identity-model-and-api/` (`.openspec.yaml`, `proposal.md`, `design.md`,
  `tasks.md`, `specs/fair-guide/guide-knowledge-base/spec.md`, `specs/fair-guide/guide-experience/spec.md`,
  `specs/fair-guide/guide-delivery/spec.md`, `specs/fair-guide/guide-self-check/spec.md`);
  `.agents/reports/usage/usage-2026-11-02-unify-identity-model-and-api.md`. Runtime scratch only:
  `.agents/local_scratch/aiscr-plan-issue/v1-contract-versions/`.
- **Verification:** `npx openspec validate unify-identity-model-and-api --strict` and `npm run openspec:validate`
  pass (6 of 6); `github_issues.py verify-composition` reports no findings for the issue draft.
  `python scripts/check_all.py` passed 34 of 36 checks. `usage-entries` and `unit` failed on this entry's file name,
  which has to carry its first `When` date. After the rename,
  `python scripts/check_all.py --only usage-entries unit` passes 2 of 2. The live checks were not run.
- **Close-out:** planning is complete; no task is started. Implementation waits for an explicit
  `/openspec-apply-change unify-identity-model-and-api`. Task 1.1 rebases on `main` after `polish-nkr-integration`
  and recounts the design's figures.
- **Corrections:** the maintainer clarified that
  [dsw-nrp/eosc-fair-guide#136](https://github.com/dsw-nrp/eosc-fair-guide/issues/136) is folded into the change
  entirely, including the w3id submission, not only the record-ID part. The change therefore carries #136's acceptance
  criteria, the EOSC CZ consent, the approval-gated registry pull request, the probe and runbook, and the release
  gate.

## Claude Code session (rebase reconciliation and M1)

- **When:** 2026-11-06 (+01:00)
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none (GitHub was reached through the `gh` CLI)
- **Workflow context used:** `openspec-explore` after the rebase on
  [dsw-nrp/eosc-fair-guide#170](https://github.com/dsw-nrp/eosc-fair-guide/pull/170), then
  `openspec-apply-change`; delivered `aiscr-planning-core`, `aiscr-quality-first-execution`, `aiscr-usage-logging`
  and `aiscr-model-logging` rules; the native `fair-guide-content` and `fair-guide-surfaces` rules; the pinned
  OpenSpec CLI; `gh` reads of PRs #168, #170 and #172 and issue #169.
- **What:**
  - Reconciled the change with the merged NKR integration: NKR types become repository kinds, NKR's precedence is
    resolved onto the thing while its record keeps NKR's values, a thing founded by a record carries the facts lists
    filter on, external record pages stay in `sameAs`, build joins stay as reviewed, NKR's native status stays in its
    snapshot, `acceptsDeposits` is false or unknown, and `--renormalise` covers the NKR snapshot. The delta now
    modifies *Catalogue slugs use meaningful local names*, whose `repo/dom` route contradicted the change.
  - With the maintainer, replaced the hash route as the browser target of record IRIs by static record landing
    pages (decision 19), kept the lens in every route, and made `#/id/` the lens-free entry route that applies the
    reader's saved language and lens. The sitemap requirement now lists the landing pages.
  - Task 1.1: built `07a1d4a` and `1ec02bd` and recounted with one script. No figure changed with the rebase;
    names repeating their identifier are 930, and 55 questions copy their clause (16 more already take it through
    `requirement`). With the maintainer, decision 10 now reuses `requirement` instead of a new `statementClause`.
- **Impacted:** `openspec/changes/unify-identity-model-and-api/` (`proposal.md`, `design.md`, `tasks.md`, and the
  knowledge-base, experience and delivery spec deltas);
  `.agents/reports/usage/usage-2026-11-02-unify-identity-model-and-api.md`.
- **Verification:** `npx openspec validate unify-identity-model-and-api --strict` passes after each artifact edit.
- **Close-out:** task 1.1 is complete (1 of 43). M1 (tasks 2.1 to 2.12) continues on this branch, which carries
  the plan and M1 in [dsw-nrp/eosc-fair-guide#172](https://github.com/dsw-nrp/eosc-fair-guide/pull/172).
- **Corrections:** the maintainer rejected dropping the lens from catalogue routes as a regression, and chose
  landing pages over the `#/id/` redirect target.

## Claude Code session (M1 implementation)

- **When:** 2026-11-06 (+01:00)
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** `openspec-apply-change unify-identity-model-and-api`; delivered
  `aiscr-planning-core`, `aiscr-quality-first-execution`, `aiscr-usage-logging` and `aiscr-model-logging` rules;
  the native `fair-guide-content` and `fair-guide-surfaces` rules; `scripts/generate_agent_surfaces.py`; the
  change's own `migration/migrate.py` and `scripts/refresh_snapshots.py --renormalise`; local Playwright checks.
- **What:** M1 tasks 2.1 to 2.11 in local commits `63728eb`, `42c9864`, `96a3d42`, `251971d` and `6e0b660`:
  - kind-word addresses and routes, the identity projection to w3id IRIs, page data keyed by address;
  - the catalogue routed by kind under the lens, the `#/id/<address>` entry route (also for an embedding host),
    a labelled Guide-identifier chip and a single entry for every record;
  - provenance results and the identifier register named by address and kind, through the migration script;
  - registry records as `dcat:CatalogRecord` parts with `foaf:primaryTopic`, things founded by their records,
    NKR's precedence on the thing, and the duplicate check's review key;
  - tests on shared address helpers (`tests/addresses.py`, `tests/page/addresses.mjs`), a guard against fragment
    prefixes in page scripts, and the docs, native rule, mirrors and changelog.
- **Impacted:** `assets/js/`, `assets/css/`, `content/` (routes, references, results, register, identifiers,
  `ui.toml`, `icons.toml`), `scripts/` (`build_crate.py`, `build_api.py`, `check_content.py`, `check_duplicates.py`,
  `check_health.py`, `check_docs.py`, `duplicate_repairs.py`, `catalogue_identity.py`, `refresh_snapshots.py`),
  `profile/fair-guide/must/1_content.ttl`, `tests/`, `docs/`, `CHANGELOG.md`, `.agents/guide/rules/` and its
  generated mirrors, `openspec/changes/unify-identity-model-and-api/` (`tasks.md`, `migration/`); this entry.
- **Verification:** `python scripts/check_all.py` passes 36 of 36 checks on `6e0b660` with this entry
  (767 unit tests, the page, final-candidate, model, helpers, assessment, api and diagram browser groups among
  them); the live checks were not run. `npx openspec validate unify-identity-model-and-api --strict` passes. The
  catalogue, a record of each kind and the identifier input were inspected in Czech and English at 390 and 1280
  pixels and in print.
- **Close-out:** M1 tasks 2.1 to 2.11 are complete (12 of 43). Task 2.12 waits only for the M1 pull request:
  nothing is pushed and PR #172 is unchanged until the maintainer approves the push.

## Claude Code session (M1 review follow-up)

- **When:** 2026-11-06 to 2026-11-07 (+01:00)
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none (GitHub was reached through the `gh` CLI)
- **Workflow context used:** `openspec-explore` on the maintainer's review of
  [dsw-nrp/eosc-fair-guide#172](https://github.com/dsw-nrp/eosc-fair-guide/pull/172), then
  `openspec-apply-change unify-identity-model-and-api`; delivered `aiscr-planning-core`,
  `aiscr-quality-first-execution`, `aiscr-usage-logging` and `aiscr-model-logging` rules; the native
  `fair-guide-content` and `fair-guide-surfaces` rules; `scripts/generate_agent_surfaces.py`; the change's own
  `migration/migrate.py`; local Playwright checks and inspection screenshots; `gh pr view`, `gh pr checks` and
  `gh run view` for the PR's CI; `git push` of the branch after the maintainer approved it.
- **What:**
  - Folded the review into the change (`05e6bed`): every registry alike, named agents, registries as resources,
    unlabelled chips and credited sources, address fields, a kind-keyed register, no compatibility names, no
    change citations in durable prose, and one pull request for the whole change; new M1 tasks 2.12 to 2.24.
  - Tasks 2.12 to 2.14 and 2.16 to 2.23 in `a0608ed` to `cc12724`:
    - the content's `baseUrl` validated when `FAIR_GUIDE_BASE_URL` is set, the CI unit failure on the PR;
    - `#re3data`, `#fairsharing` and `#datacite` records; every thing rests on its records and, where curated,
      on the Guide's selection; snapshots hold their records and `#knav-tools` and `#fers` are gone;
    - provenance objects, association targets and the worked example's steps by address; the register keyed by
      record kind; a `*` result names the Guide; the `identity-migration` instrument dropped;
    - the route translation, renormalisation and retired word forms moved into `migration/`, with a guard;
      `[[profile|...]]` became `[[pages/machines#tasks|...]]`;
    - unlabelled identifier chips, every entry's IRI first, "Vychází z" from the records with snapshot dates,
      registries among the resources and the family "Repozitáře" / "Repositories";
    - citations of the change removed from code and tests, with a check in `check_docs.py`; docs, the native
      rule and its mirrors, and the changelog.
  - Task 2.15 in `4ec293f`, after the maintainer chose a fragment of its own for the FIP Dashboard's
    organisation records: named agents resolve to the one thing of that name; organisation records join only by
    ROR or a reviewed handle, as `#fip-dashboard-organization`; eLTER RI's KNAV record joins its infrastructure;
    the duplicate check reports shared names outside a `[[distinct]]` group (CNC, CSDA, DSW). The design,
    the knowledge-base delta and task 2.15 record the decision.
  - Task 2.24 in `e9088f2`: inspected the catalogue, records of nine kinds and the identifier page in Czech and
    English at 390 and 1280 pixels and in print; fixed the credited catalogues running together and chips
    printing their address twice; the migration's action now describes the whole pull request.
- **Impacted:** `assets/` (`js/core.js`, `js/views.js`, `js/catalogue.js`, `js/catalogue-view.js`,
  `css/app.css`), `content/` (`guide.toml`, `identifiers.toml`, `model.toml`, `pages.toml`, `provenance.toml`,
  `ui.toml`, `infrastructures.toml`, `resources.toml`, `duplicates.toml`), `scripts/` (`build_crate.py`,
  `catalogue_identity.py`, `check_content.py`, `check_docs.py`,
  `check_duplicates.py`, `duplicate_repairs.py`, `refresh_snapshots.py`), `tests/`, `docs/` (`content-model.md`,
  `design.md`), `CHANGELOG.md`, `.agents/guide/rules/fair-guide-content.md` and its generated mirrors and
  `CODEX.md` region, `openspec/changes/unify-identity-model-and-api/` (all artifacts, `migration/`); this entry.
- **Verification:** `python scripts/check_all.py` passes 36 of 36 checks on `e9088f2`; the live checks were not
  run. CI passes in full on the PR's head `4ec293f` (and on `06bacfe` before it). `migration/test_migrate.py`
  passes 10 of 10, including the guard that no script, test or page script names an earlier form, and a second
  migration run changes nothing. `npx openspec validate unify-identity-model-and-api --strict` passes. The
  inspection found no page error and no horizontal overflow in 48 views.
- **Close-out:** M1 is complete (25 of 55 tasks); its last commits are pushed to the PR, whose head CI checks.
  M2 (tasks 3.1 to 3.9) is next.
- **Corrections:** the maintainer's review asked to drop the migration instrument, to keep change-specific
  references out of durable prose, to keep one pull request, to name register entries by kind instead of keeping
  names for share links, and to credit every catalogue that supplied an entry.

## Kilo session (page sections, machines page, citation cleanup)

- **When:** 2026-11-07 (+01:00)
- **Agent / runtime:** Kilo Code (VS Code extension)
- **Model / backend:** anthropic/claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** continued the Claude Code session recorded in the runtime scratch area: its
  `openspec-explore` decisions on the machines page and earlier change citations, then the approved planning
  edits and `openspec-apply-change unify-identity-model-and-api`; delivered `aiscr-planning-core`,
  `aiscr-quality-first-execution`, `aiscr-usage-logging` and `aiscr-model-logging` rules; the native
  `fair-guide-content` and `fair-guide-surfaces` rules; the change's own `migration/migrate.py`; the integrated
  browser for the machines page.
- **What:**
  - Planning: tasks 2.25 to 2.27, the *Durable prose* constraint widened to any change, decision 15's page sections
    and machines page outline, the proposal's page and impact points, and a knowledge-base scenario for reordered
    sections.
  - Task 2.25: sixteen page sections took reviewed ids through `migrate.py` and `ids.toml`; the build keys and
    names every section by its id, the content check refuses a section without one or with a number, and the
    page always anchors a section by its id.
  - Task 2.26: the machines page runs intro, *Co hledáte*, the worked example, the Guide's practice, then the
    endpoints; the page check asserts that order in the crate and in both languages, and failed on a planted
    reorder. The migration's provenance action names the work and Kilo Code among its instruments.
  - Task 2.27: 122 citations of earlier changes (D-numbers, design and decision numbers, design groupings, task
    numbers) rewritten in their own words; `change_citations` covers every form, the `.github` workflows, scripts
    and `repository.toml`, and the CSS, with each planted form tested from fragments.
- **Impacted:** `assets/` (`js/catalogue.js`, `js/catalogue-view.js`, `js/core.js`, `js/live.js`,
  `js/providers.js`, `js/search.js`, `js/selfcheck.js`, `js/views.js`, `css/app.css`), `content/` (`pages.toml`,
  `provenance.toml`, and comments in `eosc-node.toml`, `guide.toml`, `icons.toml`, `infrastructures.toml`,
  `live.toml`, `repositories.toml`, `resources.toml`, `ui.toml`), `scripts/` (`assemble_pages.py`,
  `build_crate.py`, `check_content.py`, `check_docs.py`, `refresh_snapshots.py`, `vendor_favicons.py`,
  `watch_sources.py`), `tests/`, `.github/` (`repository.toml`, six workflows, four scripts), `docs/`
  (`content-model.md`, `design.md`), `openspec/changes/unify-identity-model-and-api/` (proposal, design, tasks,
  the knowledge-base delta, `migration/`); this entry.
- **Verification:** `python scripts/check_all.py` passes 36 of 36 checks on the uncommitted tree; the live checks
  were not run. `migration/test_migrate.py` passes 11 of 11, and a second migration run changes nothing.
  `npm run openspec:validate` passes. The machines page was viewed in the integrated browser at desktop width;
  the phone-width reflow is covered by the page check, not by a screenshot.
- **Close-out:** M1 is complete again with tasks 2.25 to 2.27 (28 of 58 tasks). The planning edits are committed
  locally as `4addbb7`, and the implementation with this entry in the commit after it. Nothing is pushed; PR #172
  and its CI are unchanged.
- **Corrections:** the runtime's permission rules refused `git add`, and the session stopped before committing the
  implementation. The maintainer staged the work and asked the session to read the allowlist more carefully and
  carry on; the session committed what the maintainer staged.

## Kilo session, continued (M2 graph model)

- **When:** 2026-11-07 (+01:00)
- **Agent / runtime:** Kilo Code (VS Code extension)
- **Model / backend:** anthropic/claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none (GitHub was reached through the `gh` CLI)
- **Workflow context used:** `openspec-apply-change unify-identity-model-and-api` after the maintainer approved the
  push and asked to continue; the delivered `aiscr-planning-core`, `aiscr-quality-first-execution`,
  `aiscr-usage-logging` and `aiscr-model-logging` rules; the native `fair-guide-content` rule; the change's
  `migration/migrate.py`; `gh pr checks` for the PR's CI; pyshacl and the RO-Crate validator for profile 0.2.
- **What:**
  - Pushed `354be6c` (tasks 2.25 to 2.27); CI passed in full on it.
  - Task 3.1: every controlled term a `DefinedTerm` in one set, lenses included; the SKOS reading stated once as
    axioms in the vocabulary document.
  - Task 3.2: every status a term of its scheme through an `adms:status` specialisation: requirement, FIP,
    declaration, health, preparation, release and node state beside service and ESFRI status.
  - Task 3.3: advice items as `guide:AdviceItem` with an advice-kind term; steps and actions stay parts.
  - Task 3.4: checks as FTR benchmarks and questions as FTR metrics with their FTR relations, and each question's
    manual test in the crate at `tests/self-check/<question>`; the API no longer renames anything.
  - Task 3.5: pre-fill as typed `guide:PrefillMapping` parts with a coverage term, read by the page. The print
    check's PDF helper now reads a stream by its declared length, which a final carriage return had broken.
  - Task 3.6: the content check refuses a statement that copies a cited clause; 55 questions take their clause's
    text, four through a reviewed table that also moves two copies' references into their clauses.
  - Task 3.7: profile 0.2 with graph-model shapes, each proved by a planted violation in a new unit test; one shape
    was inert until it targeted FIPs by type.
  - Task 3.8: the content model, the design, the changelog and the docs check.
- **Impacted (M2):** `assets/js/` (`catalogue.js`, `catalogue-view.js`, `core.js`, `inspection.js`,
  `providers.js`, `selfcheck.js`, `views.js`), `content/` (`guide.toml`, `ledger.toml`, `checks/fdo.toml`,
  `checks/gate.toml`, `checks/maturity.toml`, `checks/software.toml`, `provenance.toml`), `profile/fair-guide/`
  (`profile.ttl`, `must/1_content.ttl`, `must/2_model.ttl`), `scripts/` (`build_api.py`, `build_crate.py`,
  `check_all.py`, `check_content.py`, `check_docs.py`, `image_release.py`, `release_versions.py`), `tests/` (with
  `test_profile_model.py`), `docs/` (`content-model.md`, `design.md`, `deployment.md`), `AGENTS.md` (the profile
  version in the validator command), `CHANGELOG.md`, `openspec/changes/unify-identity-model-and-api/` (`tasks.md`,
  `migration/`); this entry.
- **Verification (M2):** the narrowest checks ran after each task; `python scripts/check_all.py` passes 36 of 36 on
  the final tree with this entry; the live checks were not run. `migration/test_migrate.py` passes 12 of 12, and a
  second migration run changes nothing. `tests/test_profile_model.py` refuses a planted violation of every new
  shape, and the RO-Crate validator applies them.
- **Close-out (M2):** M2 is complete (37 of 58 tasks) and pushed to the PR; task 3.9 holds once CI passes on its
  head. Pages, callouts, crosswalks and evaluator
  tests share `schema:CreativeWork` with other kinds, so profile 0.2 has no shape that targets them; the content
  check keeps covering them. The native content rule in `.agents/guide/` still tells question authors to write a
  statement; it is a governed surface outside this milestone's tasks, so it is left for an approved edit.

## Kilo session, continued (M2 graph-model review and close-out)

- **When:** 2026-11-07 (+01:00)
- **Agent / runtime:** Kilo Code (VS Code extension)
- **Model / backend:** e-infra-cz/kimi-k3.1-pro
- **Subagents used:** none
- **MCP servers used:** none (GitHub was reached through the `gh` CLI)
- **Workflow context used:** continued the Claude Code session's `openspec-apply-change unify-identity-model-and-api`
  from its own resume file; delivered `aiscr-planning-core`, `aiscr-quality-first-execution`, `aiscr-usage-logging`
  and `aiscr-model-logging` rules; the native `fair-guide-editor` and `openspec-apply-change` workflows; the pinned
  `npx openspec` CLI; offline rdflib, pyshacl and the repository's Playwright suites; `gh pr checks` for CI.
- **What:**
  - Completed the native question-text rule and the maintainer's graph-model decisions. Pinned the used vocabularies
    and their licences as offline fixtures, checked every used term at its declared IRI, and tested each Guide
    declaration against the graph and class hierarchies.
  - Selected every kind by its class or term set, asserted rather than inferred kinds, made all registry records
    `dcat:CatalogRecord` plus `schema:CreativeWork`, removed manual FTR tests, and selected criteria by
    `guide:AssessmentCriterion`. Profile shapes now fail planted removals of required fields instead of letting a
    node escape its shape.
  - Stated each relation once: terms name their sets, principles are dimensions and questions name checks, records
    name their topics, snapshots hold records, and no thing duplicates its records. Models, lifecycle definitions,
    glossary definitions and test entry points use valid properties and classes; sources and documents use IRI
    references. An author/provider's organisational role stays distinct from its service record.
  - Moved quoted definitions to creative works under their terms, linked with `dcterms:hasPart` and, for a second
    Czech definition, `guide:quotedDefinition`. Their exact wording, licences and citations remain available to the
    page, search, exports and deferred reconstruction. Model terms and organisations use `dcterms:source` where
    schema.org is too restrictive.
  - Modelled the EOSC CZ Node as `resources/eosc-cz-node`, a service provided by e-INFRA CZ, with qualified DCAT
    relationships and their role, milestone, date and charter. Reclassified the NRP Data Catch-all Repository as a
    service. Registered the new source and Node and the EOSC Federation Handbook with its DOI and licence.
  - Corrected API source alternatives and record fragments, embedded registry records through reverse
    `foaf:primaryTopic`, and avoided treating ordinary health source IDs as links. Deferred definitions and
    instruments so the initial Czech payload returns below 300 KB with complete reconstruction.
  - Documented the resulting model in `docs/content-model.md` and `docs/design.md`, corrected the unreleased
    changelog, and made the worker-limit regression deterministic by coordinating acquisitions rather than relying
    on process startup timing.
- **Impacted:** `content/` (`eosc-node.toml`, `sources.toml`, `identifiers.toml`, `guide.toml`, `resources.toml`,
  `stations/05-repository.toml`, `provenance.toml`, `ui.toml`), `scripts/` (`build_crate.py`, `build_api.py`,
  `check_content.py`, `check_docs.py`, `check_duplicates.py`), `assets/js/` (catalogue, core, search, inspection and
  view scripts), `profile/fair-guide/`, `tests/` (offline vocabularies, graph, API, page and runtime contracts),
  `docs/` (`content-model.md`, `design.md`), `CHANGELOG.md`, `.agents/guide/rules/fair-guide-content.md` and its
  generated mirrors, `openspec/changes/unify-identity-model-and-api/` (proposal, design, tasks and spec deltas), and
  this entry. The local Claude session file remains runtime scratch under `.agents/local_scratch/cld/`.
- **Verification:** `python scripts/check_all.py` passes all 36 checks on the final tree. The offline vocabulary,
  graph and profile regressions, full browser suite, API's 1,735 files and 38,592 links, and both publication and
  worker-coordination suites pass. `npm run openspec:validate` passes 6 of 6. The initial Czech payload is 299.3
  KB and English is 296.9 KB, below the 300 KB budget. `gh pr checks 172` passes in full on `abe4289`, including
  all lanes and the final collector. Live checks were not run.
- **Close-out:** M2 is complete (50 of 71 tracked tasks) on `abe4289`, committed and pushed with local and CI
  verification. M3 (API v1 and graph access) is the next implementation milestone.

## Kilo session, continued (M3 API v1, health and graph access)

- **When:** 2026-11-08 (+01:00)
- **Agent / runtime:** Kilo Code (VS Code extension)
- **Model / backend:** e-infra-cz/kimi-k3.1-pro
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** continued the approved `openspec-apply-change` implementation of
  `unify-identity-model-and-api`; delivered `aiscr-planning-core`, `aiscr-quality-first-execution`,
  `aiscr-usage-logging` and `aiscr-model-logging` rules; native guide content/surface constraints; the pinned
  `npx openspec` CLI; offline API, Playwright and health checks.
- **What:**
  - Task 4.1: `api/v1/index.json`, one list and record templates per real kind, nested scope paths, an advice
    collection, compact vocabulary references and index-linked health. Only `api/tests/<question>.json` supports
    the older saved-result documents; the old API role routes are not emitted.
  - Task 4.2: OpenAPI 3.1 templates for unscoped/scoped records, typed response/list-summary shapes, vocabulary
    term-code enums and the NKR planned/in-development address exception. Every JSON file matches one template;
    no per-record operation survives. Normalised array/object inference avoids overlapping alternatives.
  - Task 4.3: health consumers, dashboards, deployment/release fixtures, image probing and nginx `no-store` moved
    to `api/v1/health.json`, under the OpenAPI `operations` tag.
- **Impacted:** `scripts/build_api.py`, `scripts/build_crate.py`, `scripts/check_health.py`,
  `scripts/package_site.py`, `scripts/release_versions.py`, `tests/api/check_api.mjs`, `tests/test_scripts.py`,
  `tests/addresses.py`, `tests/page/addresses.mjs`, health/deployment/release/page-check fixtures,
  `docker/nginx.conf`, `.github/workflows/publish-image.yml`, the change's `tasks.md`; this entry.
- **Verification:** `tests.test_scripts.ApiTests` passes 9 tests. `python scripts/build_site.py` and
  `npm run check:api` pass: 2,067 files and 42,409 links, with the NKR positive/negative probes and Swagger.
  `python scripts/check_all.py --only health health-api` passes 2 of 2. These narrow green results do not replace
  M3 close-out. A whole Python-suite attempt exceeded five minutes and showed consumer failures before their
  migration; it was not treated as a pass. Initial downloads currently exceed the 300 KB budget at 301 KB.
- **Close-out:** Tasks 4.1 to 4.3 are complete (53 of 71); no new commit or push was made. No CI result is claimed
  for this working tree. Task 4.4 (an offline N-Triples distribution isomorphic to the crate) is next.

## Kilo session, continued (M3 RDF, recipes, machine docs and result revision 4)

- **When:** 2026-11-08 (+01:00)
- **Agent / runtime:** Kilo Code (VS Code extension)
- **Model / backend:** e-infra-cz/kimi-k3.1-pro
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** approved `openspec-apply-change`; offline standard-library JSON-LD expansion and
  serialization, rdflib graph comparison, Playwright rendering and result loading; native bilingual content and
  provenance rules; the change's API, recipe and saved-result contracts.
- **What:**
  - Task 4.4: `scripts/knowledge_graph.py` writes deterministic N-Triples from the crate through a pinned local
    RO-Crate 1.2 context, with no network request. `tests/test_knowledge_graph.py` checks isomorphism with rdflib.
  - Task 4.5: the distribution is linkset and HTML-head `describedby`, with an `application/n-triples` type and
    deployment verification.
  - Task 4.6: six bilingual SPARQL recipes publish through `profile_recipes()` under the active profile version;
    `tests/test_recipes.py` compares actual nonempty results and graph-mutation results against these fixtures,
    rejecting only unused or renamed relationships.
  - Task 4.7: bilingual machine text and endpoint labels cover API v1, address/IRI patterns, scoped records,
    vocabulary references, the four FIP equivalents, N-Triples and recipes. Local file links are generated
    controls, not unsupported Markdown. Phone and desktop screenshots were inspected; the full page suite passes.
  - Task 4.8: saved results are revision 4. Reader answers use `dqv:QualityMeasurement`, `isMeasurementOf`,
    `computedOn` and `value`; they no longer fabricate a test at `api/tests/<question>`. Automated evidence names
    actual Guide test IRIs. Revisions 1–3 load through explicit allow-listing and new fixture tests.
- **Impacted:** `scripts/knowledge_graph.py`, recipe sources under `profile/fair-guide/recipes/`,
  `scripts/build_crate.py`, `scripts/build_api.py`, `assets/js/views.js`, `assets/js/catalogue.js`,
  `assets/js/catalogue-view.js`, `assets/js/selfcheck.js`, `assets/js/providers.js`,
  `content/pages.toml`, `content/ui.toml`, `content/provenance.toml`, offline graph, recipe and result fixtures,
  API, page, model, assessment and deployment checks, the change's `tasks.md`; this entry.
- **Verification:** `python -m unittest tests.test_knowledge_graph tests.test_recipes` passes (3 and 2 methods);
  recipe expected results pass and each recipe fails after its relation is renamed in an RDF graph copy.
  `npm run check:deployment` passes. `npm run check:page` passes in full, as do `check_embed`, `check_catalogue`,
  `check_questions`, `check_providers` and `check_assessment` with revisions 1–3 loading and revision 4 exports.
  No live evaluator was called. The build still warns that the initial Czech payload is over 300 KB (about 303),
  so the budget has not been closed by these narrower completions.
- **Close-out:** Tasks 4.4 to 4.8 are complete (58 of 71). Work remains uncommitted; no push or new CI result is
  claimed. Documentation/changelog is next, followed by static record pages and the full M3 gate.
- **Corrections:** a directory-creation shell command and an inline browser-inspection command were rejected by
  runtime policy. Required directories/files used the dedicated write tool; visual inspection used the repository's
  screenshot workflow. Repeated nested-wrapping errors in the endpoint view were corrected by decomposing rows and
  named elements, validated by `node --check` and the browser suite. The full-suite checkpoint then exposed old API
  fixtures and an undefined release-identity comparison; all of the Python inventory passed in the final gate after
  their focused repairs. The shared-slot test now waits for the configured number of acquisitions before measuring,
  so Windows process startup does not turn a successful budget test into a false failure.
- **What (M3 close-out):**
  - Tasks 4.9–4.10: documented API v1, RDF and revision 4; produced bilingual static landing pages with persistent
    IRIs, API record links, status/dates, related records, part anchors and valid head metadata in the existing
    stylesheets. They work without JavaScript, including from `file://`, through the Guide's entry route.
  - Task 4.11: supplied the bilingual `404.html`, nginx handling, production sitemap entries and preview exclusions;
    release assembly retains the root 404 without falsely requiring it for a preview-only release-less deployment.
  - Deferred the machine endpoint renderer and API text until that view needs them. Embedded/script/lib queries,
    results and record links use the same v1/address projection; health, release, image and CI consumers were checked
    against it. Integrated the landing browser cases into the page checks and typed schema/link coverage.
- **Impacted (M3 close-out):** `scripts/build_api.py`, `scripts/build_crate.py`, `scripts/landing_pages.py`,
  `scripts/build_site.py`, `scripts/assemble_pages.py`, `scripts/release_versions.py`, `scripts/knowledge_graph.py`,
  `assets/js/`, `content/pages.toml`, `content/ui.toml`, `content/provenance.toml`, `docs/`, both READMEs,
  `CHANGELOG.md`, `AGENTS.md`, `docker/nginx.conf`, deployment workflows, static recipe/result fixtures and `tests/`;
  this usage entry and the change's `tasks.md`. No runtime scratch was added to the tracked file set.
- **Verification (M3 close-out):** `python scripts/check_all.py` passes **36 of 36** checks (the Python inventory is
  865 tests with one skip), including crate/profile/schema validation, full page, landing, deployment, assessment,
  API and runtime checks. `npm run openspec:validate` passes 6 of 6. `ruff check scripts tests` and
  `ruff format --check scripts tests` pass. The fresh build emits no initial-payload budget warning. Landing pages
  were checked in both languages at desktop/phone widths, in print, with JavaScript disabled and through local-file
  Guide routes. No live service tests were run. No claim of CI on the new M3 work is made yet.
- **Close-out (M3 close-out):** tasks 4.1–4.11 are complete (61 of 71). The local half of 4.12 passes on this exact
  source tree except for the provenance/diagnostic bookkeeping added subsequently, which is rechecked separately.
  Task 4.12 remains open pending the separately approved commit/push and CI on that PR head. No w3id, release,
  namespace-consent or other M4 action has begun.
- **Verification (M3 CI):** the separately approved commit `3bedc50` was pushed to
  [dsw-nrp/eosc-fair-guide#172](https://github.com/dsw-nrp/eosc-fair-guide/pull/172). The
  [workflow run](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/42472866854) completed successfully with
  head SHA `3bedc5022acd0e67b3e07de3b2ab33b705ae3ee3`; quick checks, build, all six lanes and the final collector
  passed.
- **Close-out (M3 complete):** tasks 4.1–4.12 are complete (**62 of 71**), with local and CI verification on the
  pushed commit. M4 begins with its separately gated EOSC CZ consent and exact-content registry approval; neither has
  started, and no live service requests or release action were made here.

## M3 review remediation (2026-11-09)

- **When:** 2026-11-09, local implementation session.
- **Agent / runtime:** Kilo.
- **Model / backend:** `e-infra-cz/kimi-k3.1-pro`.
- **What:** Addressed all 18 verified findings from the PR review through OpenSpec tasks 4.13–4.18. Accepted predecessor and
  current release layouts independently, made migration retries safe from mixed checkpoints, published every issued
  identity, guarded generated HTML, aligned list filters, cached the registry index and deduplicated schemas, completed
  nested static targets and deep-404 assets, and corrected profile, local-test and accessible machine documentation.
  The interactive visual pass then exposed removal of curated annex assumptions and an `undefined` roadmap-year branch,
  which is now conditional.
- **Impacted:** `scripts/assemble_pages.py`, `scripts/image_release.py`, `scripts/build_crate.py`, `scripts/build_api.py`,
  `scripts/landing_pages.py`, `openspec/changes/unify-identity-model-and-api/migration/`, `content/ui.toml`,
  `content/provenance.toml`, `profile/fair-guide/must/2_model.ttl`, `assets/js/catalogue-view.js`,
  `assets/js/machines.js`, `assets/js/tests/index.html`, `.github/workflows/publish-image.yml`, the OpenSpec planning
  artifacts, focused unit/browser/deployment tests and this usage entry.
- **Workflow context used:** approved OpenSpec change `unify-identity-model-and-api`, M3 review remediation 4.13–4.19.
- **Verification:** mixed-layout release unit tests, migration boundary interruption tests, 206 script tests, profile and
  helper suites, 2,170 API files with 42,921 links, catalogue completeness, and complete page/deployment suites.
  `python scripts/check_all.py` passes **36 of 36** checks and `npm run openspec:validate` passes **6 of 6**.
  Both language paths fit the initial-payload budget: Czech is 299.9 KB and English 297.6 KB compressed, versus 300 KB.
  Visual review covered HL-LHC, nested quick-deep action and nested 404 at desktop and phone widths and in print.
- **Close-out:** tasks 4.13–4.19 are complete (69 of 78), with local **36 of 36** checks passing and every CI lane green
  in [workflow run 42576972665](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/42576972665). The next work is
  M4's separately gated EOSC CZ consent and exact-content registry approval; neither has started here.

## Kilo session, continued (review R2 and predictable bare URL)

- **When:** 2026-11-10 (+00:00).
- **Agent / runtime:** Kilo Code (VS Code extension).
- **Model / backend:** e-infra-cz/kimi-k3.1-pro.
- **Subagents used:** none.
- **MCP servers used:** none (the pull-request review was read through the `gh` CLI).
- **Workflow context used:** `openspec-explore`, then the separately approved `openspec-apply-change` and native
  `fair-guide-editor` routes; the native content/surface rules; the pinned `npx openspec` CLI; repository unit and
  browser suites; local Docker for real health-header probes.
- **What:**
  - Captured the second review's ten findings and the chosen route contract, then completed tasks 4.20–4.25. The bare
    Guide URL now selects `path/start` for every reader, including those with saved station history; the Path menu,
    resume action, explicit station-free path and crate-preview exception retain their prior behavior.
  - Retained only text-referenced infrastructure addresses in the initial record map. Search now classifies before
    preloading, so identifiers remain routeable when unrelated parts fail, while text-search failure displays the
    shared retry and recovers without losing results.
  - Saved-result documentation now links a concrete support document beside its displayed URI template. Infrastructure
    cards share one reverse `operatedBy` index. Landing pages derive status fields from declared ADMS properties, show
    HL-LHC's `landmark` without inventing a date, and drop the obsolete walker/wrapper/configuration alternatives.
  - Added one release-layout gate: the health layout selects the status property for both status-bearing nodes, with
    current/predecessor/missing/mixed/split/dual refusal before replacement. Both health paths use `no-store`, and the
    image workflow verifies the header. Genuine current and predecessor containers passed direct header and identity
    probes.
- **Impacted:** `assets/js/` (app, core, search, machines, catalogue-view), `scripts/` (`build_crate.py`,
  `landing_pages.py`, `assemble_pages.py`, `image_release.py`), `docker/nginx.conf`,
  `.github/workflows/publish-image.yml`, release/publication fixtures and focused browser/Python tests, `docs/design.md`,
  `content/provenance.toml`, the five planning/specification artifacts named in the approved capture, and this usage
  entry. Fixture preparers wrote only ignored caches and the containers used for the probes. No branch, remote issue or
  release was changed.
- **Verification:** focused station-reference and bare-route cases, complete language and safety suites, 22 landing and
  language tests, 25 assembly/image layout tests and 41 workflow tests all pass. Both real containers returned
  `Cache-Control: no-store` with correct identities. Visual review covered both languages, desktop/phone widths, print,
  station references, independent identifiers, Search failure/retry, saved-result row, infrastructure card and HL-LHC.
  `npm run openspec:validate` passes **6 of 6**, and `python scripts/check_all.py` passes **36 of 36**. Ruff lint and
  format pass on the final code. These checks do not establish behavior on a new CI head.
- **Close-out:** tasks 4.20–4.25 are complete (**75 of 85**). Task 4.26 remains open only for separately authorized
  commit/push and CI on the resulting PR head. The next implementation dependency is then M4's human EOSC CZ consent;
  it has not started and was not purported to be complete in this session.
- **Corrections:** the maintainer selected the existing lifecycle `path/start` for every bare-URL visit, rather than the
  initially discussed last-station or first-station variants. The final scenarios explicitly cover both fresh and
  returning readers.
