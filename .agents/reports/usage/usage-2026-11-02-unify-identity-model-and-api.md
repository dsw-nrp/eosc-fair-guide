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

- **When:** 2026-11-06 (+01:00)
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none (GitHub was reached through the `gh` CLI)
- **Workflow context used:** `openspec-explore` on the maintainer's review of
  [dsw-nrp/eosc-fair-guide#172](https://github.com/dsw-nrp/eosc-fair-guide/pull/172), then
  `openspec-apply-change unify-identity-model-and-api`; delivered `aiscr-planning-core`,
  `aiscr-quality-first-execution`, `aiscr-usage-logging` and `aiscr-model-logging` rules; the native
  `fair-guide-content` and `fair-guide-surfaces` rules; `scripts/generate_agent_surfaces.py`; the change's own
  `migration/migrate.py`; local Playwright checks; `gh pr checks` and `gh run view` for the PR's CI.
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
- **Impacted:** `assets/` (`js/core.js`, `js/views.js`, `js/catalogue.js`, `js/catalogue-view.js`,
  `css/app.css`), `content/` (`guide.toml`, `identifiers.toml`, `model.toml`, `pages.toml`, `provenance.toml`,
  `ui.toml`), `scripts/` (`build_crate.py`, `catalogue_identity.py`, `check_content.py`, `check_docs.py`,
  `check_duplicates.py`, `duplicate_repairs.py`, `refresh_snapshots.py`), `tests/`, `docs/` (`content-model.md`,
  `design.md`), `CHANGELOG.md`, `.agents/guide/rules/fair-guide-content.md` and its generated mirrors and
  `CODEX.md` region, `openspec/changes/unify-identity-model-and-api/` (all artifacts, `migration/`); this entry.
- **Verification:** `python scripts/check_all.py` passes 36 of 36 checks on `cc12724`; the live checks were not
  run. `migration/test_migrate.py` passes 10 of 10, including the guard that no script, test or page script names
  an earlier form, and a second migration run changes nothing. `npx openspec validate
  unify-identity-model-and-api --strict` passes. The unit lane passes locally with CI's `FAIR_GUIDE_BASE_URL`.
- **Close-out:** 23 of 55 tasks are complete. Task 2.15 (named agents) waits for a maintainer decision: an
  organisation and its eponymous service are one node, and four of them (DataCite, FAIRsharing, ORCID, Creative
  Commons) would hold two FIP Dashboard records under one fragment. Task 2.24 needs CI on the PR's head; nothing
  is pushed yet.
- **Corrections:** the maintainer's review asked to drop the migration instrument, to keep change-specific
  references out of durable prose, to keep one pull request, to name register entries by kind instead of keeping
  names for share links, and to credit every catalogue that supplied an entry.
