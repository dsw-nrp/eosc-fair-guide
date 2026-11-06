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
