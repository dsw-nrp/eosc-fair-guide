# Proposal

## Why

Pull request 82, an automated re3data refresh, added `r3d100014970` (the NRP Data Catch-all Repository) without linking the existing curated `datarepo` resource. Two checks failed, but the required aggregate reported only `content: failed or partial result`; the `duplicates` failure and both exact diagnoses were buried in a lane artifact. The remedy was a one-line link in `content/resources.toml`, but neither the refresh workflow nor the PR comment said where to put it.

The duplicate rule is correct and must stay a gate. The maintenance cost is in diagnosis and safe repair: agents and contributors must discover the field, the file and the identity link by hand, and the CI result hides the second failure. A narrow, explicit suggestion path removes that friction without letting automation decide that two records are the same thing.

## What Changes

- `check_duplicates` emits a structured, machine-readable suggestion beside its current human-readable error for groups it can resolve unambiguously: a curated entry and one registry record sharing an authoritative key, a known link field, no existing conflicting link.
- The required `checks` job reports every failed check with a bounded output tail, not only the first one, and copies lane logs and details into the health artifact on failure so the summary and artifact agree.
- The trusted PR comment adds a "Suggested fixes" section with a fenced patch and the reason. The PR check workflow stays read-only and never edits content.
- A local `--fix` mode applies only `safe` suggestions, prints the diff, and leaves the commit and provenance action to the person running it.
- A maintainer-triggered `/fix-duplicates` command on a same-repository PR applies only `safe` suggestions, records the commenting maintainer as the provenance agent, commits to the PR branch through the trusted App, and lets the checks rerun. It never runs on schedules, never runs for untrusted forks, and never auto-accepts a duplicate in `content/duplicates.toml`.
- `refresh_snapshots` passes the Guide-owned identifiers already used in `content/` as reserved IDs, so a new snapshot row cannot silently mint an identifier owned by another entry.
- Regression tests cover the PR 82 case (a new re3data record matching a curated resource), ambiguous groups that must not be auto-fixed, aggregate multi-failure reporting and the reserved-ID guard.

Excluded: automatic curated-content edits on schedules or ordinary PRs, auto-accepting lookalike records, changing the duplicate rule itself, and any new provider or registry integration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-knowledge-base`: the one-entry-per-thing check gains structured, unambiguous link suggestions and an explicit safe-fix boundary while retaining the existing failure and accepted-group rules.
- `fair-guide/guide-delivery`: CI reports all failed checks with actionable output, the trusted comment surfaces suggestions, and a maintainer-authorised fix command has a narrow trust and provenance model.

## Impact

- `scripts/check_duplicates.py`: structured suggestion records and `--fix` mode.
- `scripts/check_content.py`: shared report or suggestion plumbing if required.
- `scripts/check_ci.py`: aggregate all failures, preserve lane diagnostics, expose suggestions to consumers.
- `scripts/check_health.py`: summary rendering of failures and suggestions.
- `scripts/refresh_snapshots.py` and `scripts/catalogue_identity.py`: reserved IDs and regression behaviour.
- `.github/workflows/checks.yml`: summary and artifact changes only; read-only remains.
- `.github/workflows/pr-summary.yml`, `.github/scripts/comment-summary.cjs`: trusted suggestion comment.
- A maintainer-only fix workflow or an extension of the existing trusted publisher, with the repository-scoped App and current-permission checks.
- Tests under `tests/`; `docs/design.md` and `docs/content-model.md` where the suggestion and fix boundaries are described.
- No generated site output, API schema change or browser behaviour change.
