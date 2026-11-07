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
  KB and English is 296.9 KB, below the 300 KB budget. `gh pr checks 172` is green on the earlier head; no CI run
  covers the uncommitted head used for this entry yet. Live checks were not run.
- **Close-out:** the local M2 work is complete (49 of 71 tracked tasks). Task 3.22 is not checked off until CI
  verifies a commit containing it; that requires separately authorised staging, commit and push. M3 (API v1 and
  graph access) is the next implementation milestone.
