# Proposal

## Why

Maintaining the Guide costs too many clicks, waits and notifications, and some paths lose information. The next
release preparation would silently drop the curated `[Unreleased]` notes. A missing CI lane hides failures that
were already known. Any comment can cancel a waiting `/refresh` command. PR checks take about six minutes, each
merge needs a branch update, a rerun and a deployment approval, and monitoring keeps one issue per finding
(24 open today). Contributors, maintainers and bots need fast feedback, simple merges, quiet monitoring and a
Project that stays consistent without manual bookkeeping.

## What Changes

The change lands in six waves. Each wave is one reviewed pull request and is useful on its own.

1. **Nothing gets lost.** A changelog check protects `[Unreleased]` and published history, and release
   preparation keeps the unpublished lines beside the generated PR/commit list. Detail stays in durable commit
   messages, and release bodies combine reviewed notes with the verification record. The CI collector keeps known
   failures when lane evidence is missing. Local duplicate repair writes the same complete link, provenance
   and registration as the remote command. One comment-command workflow keeps every accepted request,
   answers with a visible outcome and adds `/help`.
2. **Faster checks.** A quick feedback job reports cheap checks in about a minute. Lanes are balanced from
   measured timings, long browser scripts become cases, unit tests run in parallel shards and lanes install
   only what they need with npm/pip caches. Coverage stays complete; acceptance uses paired timing runs.
3. **Simple merge and deploy.** A merge queue verifies the merged result, while PR checks stay required. Deploy
   reuses the queue's result for identical content or runs the partitioned checks. Staging needs no approval;
   production promotion keeps an explicit approval. Dependabot groups patch and minor updates and keeps its
   limit of 30. A reviewed `.github/repository.toml` describes the expected settings, and a read-only audit
   reports drift with exact fix steps.
4. **Consistent Project and intake.** Area is a reviewed set of labels, also applied to PRs from changed paths.
   Czech and English issue templates are generated from the delivered `aiscr-plan-issue` shape. A weekly
   read-only audit checks Project #1 (types, Ready definition, automation and view drift) and reports
   actionable fixes. Native Project automations remain the only Project writers.
5. **Quiet monitoring.** One digest issue is rebuilt from current state on every run and comments only on
   meaningful change. Maintainers promote findings with a "Track as task" link. Limitations have a reviewed
   basis and deadline. URL coverage rotates fairly, and state survives in run artifacts. The 24 legacy bot
   issues migrate into the digest after approval.
6. **Self-explaining CI.** `docs/ci.md` carries a catalogue generated from the workflow files and a maintainer
   cheat sheet. Every automated output ends with a next step. PR comments give advisory release-note and
   planning hints. A usage-filename check is added. Production publishes real `robots.txt` and `sitemap.xml`
   (#83); #84's CI documentation is delivered.

- **BREAKING:** health observations move from one issue per finding to one digest; consumers of the
  `guide-health` per-finding issues must follow the digest.
- **BREAKING:** local `check_duplicates.py --fix` refuses to write when no reviewed responsible person can be
  resolved, instead of applying the link with a provenance reminder.

Scope is repository delivery and maintenance. Excluded: editorial content, FAIR interpretation and evaluator
semantics, crate/profile versions (#25), canonical address and DNS (#15, #32), external registrations (#80),
Dependabot security updates (deliberately off), automatic merging or promotion of work, bot writes to the
Project, and a public API redesign. Reusing expensive check results by input digest is a separately approved
follow-up.

Validation: strict OpenSpec validation and `python scripts/check_all.py`; planted regressions for every new
check and renderer; real producer/consumer paths with fake remote transport only; paired before/after timing
reruns with unchanged coverage. Ruleset/environment changes, the backfill, the digest migration and hosted
rehearsals each need their own approval of the exact content and are recorded separately from local evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-delivery`: changelog and release-note handling, failure diagnostics, comment commands and
  `/help`, check speed, merge queue and deployment approvals, settings audit, labels, issue templates, Project
  audit, digest monitoring, CI documentation and handoffs, crawler files.
- `fair-guide/guide-knowledge-base`: dated statuses reported in the digest; local duplicate repair records
  complete provenance for a resolved reviewed person.

## Impact

- Scripts: `check_changelog.py`, `release_versions.py`, `release_body.py`, `check_ci.py`, `check_all.py`, `profile_checks.py`,
  `check_duplicates.py`, `fix_duplicates.py`, `watch_sources.py`, `build_site.py`/`assemble_pages.py`, and new
  `ci_timings.py`, `audit_repository.py`, `generate_issue_templates.py`, usage and CI-catalogue checks.
- Workflows: new `commands.yml`; changes to `checks.yml`, `pr-summary.yml`, `deploy.yml`, `health-watch.yml`,
  `source-refresh.yml`, `fix-duplicates.yml`, `tag-release.yml`; trusted scripts under `.github/scripts/`;
  `.github/dependabot.yml`, the PR template, `.github/ISSUE_TEMPLATE/`, `.github/repository.toml`,
  `.github/health-watch.toml`.
- Docs: `docs/ci.md`, `docs/maintenance.md`, `docs/changelog.md`, `docs/deployment.md`, CONTRIBUTING,
  content-model guidance; native rules under `.agents/guide/` with regenerated mirrors.
- GitHub settings (human-applied after approval): main and tag rulesets, `github-pages` and new `production`
  environments, labels, Project #1 views and automations, App installation permissions.
- Baseline: `main` at `f0c09f9`, which includes PR #102. Live repository, Project and run data read on
  23–24 October 2026. No new runtime dependency is intended.
