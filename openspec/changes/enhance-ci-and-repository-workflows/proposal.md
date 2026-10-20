# Proposal

## Why

Alpha maintenance produces too many notifications, incomplete repair handoffs and avoidable CI work,
while contribution and release policies lack consistent enforcement. A multiuser repository needs one
delivery contract connecting reliable checks, efficient execution, safe concurrent writes and human-owned work.

## What Changes

- Consume `unreleased-changelog-policy`, `consolidate-maintenance-reporting` and
  `actionable-ci-repair-bundles` into this single unapplied change, retaining their requirements,
  acceptance coverage and usage history. The design maps every former task and the inspected issue backlog.
- Deliver one CI policy/catalogue and product inventory, drift checks, actionable human handoffs for every
  CI product, complete duplicate repair bundles, and diagnostics that retain known failures when other
  lane evidence is missing. Reuse PR #102's reviewed duplicate repair after integrating that dependency.
- Enforce settled `[Unreleased]` notes or concrete reviewed omission reasons; preserve curated notes and
  full PR/direct-commit lineage through release preparation. Add proportionate OpenSpec routing and dated
  usage-file checks through Guide-owned rules, without editing delivered tooling.
- Replace per-observation issue floods with one current digest, exact reviewed monitoring limitations,
  maintainer-controlled sub-issues, bounded meaningful comments and resumable retirement. Migrate the 24
  current bot notifications without losing unresolved work, human discussion or original evidence.
- Measure cold/warm setup, queueing, active checks and runner cost; add npm/pip package caching, unify
  concurrency budgets, reuse the verified-build partition approach for deployment, and tune slow cases
  only with measured full-coverage results. Browser caching and extra shards require demonstrated benefit.
- Define cancellation/queue policy by intent and shared resource: current PR results may supersede old
  ones; explicit operations receive a terminal outcome. Separate cancellable preparation from serialized
  publication, and protect source-refresh branch updates with an atomic expected-head condition.
- Include issue #83's real production `robots.txt` and `sitemap.xml`, with configured-origin checks,
  explicit document scope, production byte preservation and preview exclusion. Fulfil #84's original
  documentation/drift criteria alongside these explicitly planned code changes.
- Reuse [Guide Project #1](https://github.com/orgs/dsw-nrp/projects/1) with native lifecycle support and
  reviewed backlog import. Personal access is verified. **Project implementation, configuration and import
  wait for the organization owner to approve the required App installation permissions and for actual
  organization-Project access to be verified using `fair-guide-actions`.**
- **BREAKING:** local duplicate `--fix` requires an explicit reviewed `--person` and applies a complete
  link/provenance/registration repair; missing identity writes nothing. Existing exact trusted command
  syntax remains supported. CI artifact/watch format changes retain explicit migration and legacy handoffs.

Scope is repository delivery and management. It excludes editorial expansion, FAIR/evaluator semantics,
new crate/profile versions, DNS adoption, external registrations, mandatory live-network PR checks,
automatic issue promotion/merging and a public-health API redesign. Issue migration, Project setup,
hosted dispatch, ruleset changes, publication and archive still need their applicable concrete approvals.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-delivery`: checked CI policy and handoffs, changelog/governance gates, efficient
  attributable execution, intent-aware concurrency, safe publication, digest/Project management and
  real production crawler files.
- `fair-guide/guide-knowledge-base`: complete duplicate repair preparation/application and dated-status
  reporting through the digest, preserving human responsibility and authored content integrity.

## Impact

`scripts/check_all.py`, `check_ci.py`, `check_health.py`, `check_duplicates.py`, `fix_duplicates.py`,
new shared repair/changelog/contribution-policy helpers, `release_versions.py`, `watch_sources.py`,
site generation/assembly, browser scheduling and timing helpers; `.github/workflows/`, trusted publishers,
the PR template, one `.github/ci-products.toml`, and `.github/health-watch.toml`. Tests extend existing
workflow, publisher, release, content and browser coverage with CI-document/handoff/governance checks.
Standing docs are `docs/ci.md`, `docs/maintenance.md`, `docs/changelog.md`, current design/deployment/content
procedures and contribution entrypoints. Native agent changes originate under `.agents/guide/` and regenerate.

This plan is based on `main` at `660b1fe` and the live issue inventory read on 20 October 2026. PR #102
remains an explicit implementation dependency, not a merged baseline. No new dependency, browser feature
or historical-release rewrite is intended. Acceptance requires planted regressions, real producer/consumer
and registered-content paths, full deterministic coverage, measured hosted performance and separately
recorded human/permission-dependent outcomes. Local mocks cannot discharge hosted activation.
