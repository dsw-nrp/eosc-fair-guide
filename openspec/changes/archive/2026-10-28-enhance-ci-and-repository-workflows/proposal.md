# Proposal

## Why

Maintaining the Guide costs too many clicks, waits and notifications, and some paths lose information. The next
release preparation would silently drop the curated `[Unreleased]` notes. A missing CI lane hides failures that
were already known. Any comment can cancel a waiting `/refresh` command. PR checks take about six minutes, each
merge needs a branch update, a rerun and a deployment approval, and monitoring keeps one issue per finding
(24 open today). Contributors, maintainers and bots need fast feedback, simple merges, quiet monitoring and a
Project that stays consistent without manual bookkeeping.

The first hosted release rehearsal, on 25 October 2026, worked but exposed more problems. A content PR fails in the
queue whenever anything lands on `main` after its provenance action ended, and the only way past is a less truthful
end time. A release PR prepared before `main` moved would ship an incomplete changelog without any warning, and once
the queue rejects it no maintainer route re-prepares it. After tagging, `/next/` names the previous tag for the very
commit production now serves. The `github-pages` environment reads like staging but publishes both channels.
Scheduled jobs start about five hours late at unrelated hours. The maintainer documentation mixes steps, guarantees
and mechanism, so a person cannot find the next action quickly.

## What Changes

The original scope has nine logical waves. Earlier waves landed separately; the maintainer consolidated the
remaining work on `agents/claude/ci-workflows-replan` (draft PR #116). The follow-up below extends that same change.

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
   read-only audit checks the [EOSC CZ FAIR Guide Project](https://github.com/orgs/dsw-nrp/projects/1)
   (types, Ready definition, automation and view drift) and reports
   actionable fixes. Native Project automations remain the only Project writers.
5. **Quiet monitoring.** One digest issue is rebuilt from current state on every run and comments only on
   meaningful change. Maintainers promote findings with a "Track as task" link. Limitations have a reviewed
   basis and deadline. URL coverage rotates fairly, and state survives in run artifacts. The 24 legacy bot
   issues migrate into the digest after approval.
6. **Self-explaining CI.** `docs/ci.md` carries a catalogue generated from the workflow files and a maintainer
   cheat sheet. Every automated output ends with a next step. PR comments give advisory release-note and
   planning hints. A usage-filename check is added. Production publishes an actual-location sitemap and an
   effective hosting-aware crawler policy (#83); #84's CI documentation receives complete acceptance below.
7. **Release flow repairs.** Paradata freshness is decided from history, so a moving `main` no longer fails a
   correct PR and `endTime` keeps meaning when the work finished. Tag release refuses a version whose changelog
   misses changes since the previous tag and starts Prepare release to complete it; preparation can complete an
   untagged version and replace its own unedited outdated proposal. Both dispatches accept a leading `v`. A
   `/next/` identical to the release says so. `staging` and `production` deployment records show when each channel
   is live; `github-pages` stays the publishing mechanism. One native skill prepares and applies release notes.
8. **Predictable schedule.** Scheduled refresh, dependency updates and health watch finish by Monday morning in
   Prague despite GitHub's start delays. Manual health-watch runs can select the audit, the watch or both.
9. **Documentation people can use.** All human documentation is reshaped in one wave by Diátaxis type, with one
   landing page per audience and maintainer runbooks whose steps say where, what, done when and if it fails. A
   section map, facts and structure checks and an independent agent reader review the wave. A final hosted
   rehearsal follows the new release runbook.

- **BREAKING:** health observations move from one issue per finding to one digest; consumers of the
  `guide-health` per-finding issues must follow the digest.
- **BREAKING:** local `check_duplicates.py --fix` refuses to write when no reviewed responsible person can be
  resolved, instead of applying the link with a provenance reminder.
- **BREAKING:** absolute Guide vocabulary/profile IRIs move from the legacy namespace to the reviewed namespace
  setting, now the current Pages root. The preview carries them from the merge of this change, production from the
  next release. Historical artifacts keep their original contexts; consumers use the context/profile belonging to
  the artifact they read. Logical record IDs and exact external IRIs are unchanged.

Scope is repository delivery and maintenance. Excluded: editorial content, FAIR interpretation and evaluator
semantics, crate/profile versions (#25), custom-domain adoption and DNS (#15, #32), external registrations (#80),
Dependabot security updates (deliberately off), automatic merging or promotion of work, bot writes to the
Project, and a public API redesign. Reusing expensive check results by input digest is a separately approved
follow-up. Also excluded: editing the delivered `aiscr-write-release-notes` (its upstream maintainer changes its
invocation policy), `AGENTS.md` and other delivered or generated surfaces in the documentation wave, and moving the
release lineage out of `CHANGELOG.md`.

### Follow-up scope confirmed on 26 October 2026

The maintainer's documentation read found gaps beyond the structural reshape and sampled reader checks.
This same change adds serving-location addresses and discovery, issue-based refresh, the newly requested
organization read permissions, settings reconciliation and complete documentation review. It does not create
a separate remediation change. The completed tasks and the 25 October validation remain historical receipts;
they do not establish acceptance of this extension.

- **Serving location is authoritative for navigation and discovery.** Index the current GitHub Pages site.
  Guide-owned links and discovery metadata follow the actual serving origin and site path, not a predicted
  hostname. Relative references preserve portability; static files needing absolute URLs use the actual deployment
  URL before validation and packaging. Preserve logical Guide IDs, external vocabulary/source IRIs, file and iframe
  operation, shared production/preview identities and immutable release bytes. Record the compatibility
  disposition of existing absolute IRIs before changing their generation. Vocabulary and profile IRIs come from a
  reviewed namespace setting instead (revised on 28 October, below). No existing release artifact is rewritten.
- **Discovery reflects effective hosting controls.** Correct sitemap locations and preview indexing; do not
  describe a project-subdirectory robots file as the host-root policy or block discovery of `noindex`. The existing
  root/API sitemap scope remains; separate indexable station/language pages are not implicitly added.
- **Commands and audits meet their users where they work.** Allow authorized `/refresh <source>` from ordinary
  issue threads as well as pull requests. Keep duplicate repair PR-only. After installation acceptance, request
  and route the App's Issue Types/Issue Fields read permissions only where the audit needs them.
- **Durable documentation is complete and current.** Review the whole human set, including every section of the
  long design and content reference, against its maintained sources and implementation. Qualify reused vocabulary
  terms, distinguish technical owners from content reviewers, use named Project links, make AI participation
  guidance generic, expose the native release helper and add a review runbook and accurate workflow diagrams.
  One-time migration instructions and rollout evidence stay with this change.
- **Applied settings and recommendations stay distinct.** Reconcile the observed tag gates and status check,
  retaining both deployment gates and `checks`, as explicitly chosen during apply. Explain and evaluate queue build
  concurrency separately from merge batching; the maintainer also selected the existing live batch of ten while
  keeping two builds, minimum one and no wait. The local declaration follows those choices; no remote write is inferred.

The current-host address work is in scope even though adoption of `fair.eosc.cz` and DNS changes remain
with #15/#32. These planning updates authorize no implementation, remote writes, release or archive.

### Finishing scope confirmed on 28 October 2026

The maintainer wants this change finished rather than left open behind hosted hand-offs. The releases so far are
alphas and the repository is still being set up, so the remaining proof comes from ordinary use within days of the
merge. A check that cannot be made within this change is dropped explicitly rather than deferred.

- **A reviewed namespace setting replaces the coordinated pair.** `content/guide.toml` declares the
  vocabulary/profile namespace, set to the current Pages root. Deployments no longer read live production to choose
  it, and publication no longer pairs a release with a current-head preview. Until the next release the preview's
  namespace differs from production's, and the deployment summary says so instead of refusing. A persistent
  `w3id.org` namespace moves to a new issue.
- **Failures name who acts.** A red run means a person must act, and its summary says what to do. A source that
  cannot be downloaded is a warning; a rejected one stays a failure. Both reach the digest. Nothing a person needs
  exists only in an artifact. The audit asks for the accepted Project read separately from the new organization
  reads, so a pending acceptance hides only what it covers.
- **The digest stays short.** Link findings that share a host and outcome form one entry, and a section's
  overflow stays in the issue body.
- **Hand-offs finish through use.** The audit, the digest migration and the alpha.4 release, which doubles as the
  rehearsal, follow the merge, each through its runbook. The maintainer's walk-through of those runbooks replaces
  the separate human documentation review. The migration selects every open `guide-health` issue by label and
  marker, including those opened since it was planned.
- **Small corrections.** The quick job installs what its checks import. The native content rule stops requiring
  inline language markup that does not exist. A possibly stale source title goes to the content team as an issue.
- **Review repairs before the merge.** The review of #116 found seven defects in the new automation and four older
  gaps in the release flow; all are fixed in the same pull request. The watch retires targets that content no
  longer names, the digest moves only open tasks, and the documentation check reads every Mermaid link form.
  Retry hand-offs name routes that work. A release published to Pages always keeps its image tag and draft, and
  only `latest` and `stable` follow precedence. Release versions must increase, and a release dispatch on another
  branch fails visibly (decision 30). Untracked run hand-offs in the declared runtime area, which stay visible to
  Git, no longer fail the public-content check.
- **Release images carry the version.** From the next release an image is tagged with the version, the git tag
  without its `v` (`1.0.0-alpha.5`); the images of alpha.1 to alpha.4 gain that tag beside their `v` tags
  (decision 31, from the alpha.4 release review).

Validation: strict OpenSpec validation and `python scripts/check_all.py`; planted regressions for every new
check and renderer; real producer/consumer paths with fake remote transport only; paired before/after timing
reruns with unchanged coverage. Ruleset/environment changes, the backfill, the digest migration and hosted
rehearsals each need their own approval of the exact content and are recorded separately from local evidence.
The documentation wave passes its section map, facts and structure checks and an independent agent review, and a
final hosted rehearsal follows the release runbook.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-delivery`: changelog and release-note handling, failure diagnostics, comment commands and
  `/help`, check speed, merge queue and deployment approvals, settings audit, labels, issue templates, Project
  audit, digest monitoring, CI documentation and handoffs, crawler files; release currency and re-preparation,
  version input, the `/next/` release notice, channel deployment records, one-invocation release notes, the weekly
  schedule and manual health-watch parts, documentation types, runbooks and their review.
  The follow-up adds issue-thread refresh, scoped organization audit reads, applied tag-policy reconciliation,
  current-host discovery and complete durable-documentation acceptance. The finishing scope adds failure
  hand-offs that name who acts, scheduled refresh outcomes in the digest and host-grouped digest entries, and
  replaces the namespace pair check with channels that may differ in namespace until the next release. The review
  repairs add increasing release versions and image aliases that never move back while every published release
  keeps its tag and draft. Release images are tagged with the version, without the git tag's `v`.
- `fair-guide/guide-knowledge-base`: dated statuses reported in the digest; local duplicate repair records
  complete provenance for a resolved reviewed person; paradata freshness decided from history in every comparison
  context, including the merge queue.
  The follow-up requires namespace-qualified mapping documentation without renaming logical record identities or
  external terms, and the finishing scope takes Guide vocabulary/profile IRIs from a reviewed namespace setting.

## Impact

- Scripts: `check_changelog.py`, `release_versions.py`, `release_body.py`, `check_ci.py`, `check_all.py`, `profile_checks.py`,
  `check_duplicates.py`, `fix_duplicates.py`, `watch_sources.py`, `build_site.py`/`assemble_pages.py`, and new
  `ci_timings.py`, `audit_repository.py`, `generate_issue_templates.py`, usage and CI-catalogue checks.
- Workflows: new `commands.yml`; changes to `checks.yml`, `pr-summary.yml`, `deploy.yml`, `health-watch.yml`,
  `source-refresh.yml`, `fix-duplicates.yml`, `tag-release.yml`; trusted scripts under `.github/scripts/`;
  `.github/dependabot.yml`, the PR template, `.github/ISSUE_TEMPLATE/`, `.github/repository.toml`,
  `.github/health-watch.toml`.
- Release flow and schedule: `check_content.py`, `assemble_pages.py`, `release_version.py`, `release_versions.py`,
  `.github/scripts/prepare-release.cjs` and `release-version.cjs`, `prepare-release.yml`, `tag-release.yml`,
  `publish.yml`, `source-refresh.yml`, `.github/dependabot.yml`; new `scripts/check_docs.py`.
- Docs: every human document (both READMEs, CONTRIBUTING, `docs/**`) reshaped by type, new `docs/runbooks/`, and a
  reviewed section map kept with this change; native rules and the new `fair-guide-release-notes` skill under
  `.agents/guide/` with regenerated mirrors.
- GitHub settings (human-applied after approval): main and tag rulesets, channel environments, labels, Guide
  Project views and automations, and App installation permissions. The already applied tag gates need target
  reconciliation and hosted evidence, not another instruction to add `staging`.
- Upstream dependency: the invocation-policy change for delivered `aiscr-write-release-notes` has arrived and the
  native helper exists locally; its real draft exercise remains open in 8.8.
- Baseline: `main` at `f0c09f9`, which includes PR #102. Live repository, Project and run data read on
  23–24 October 2026. No new runtime dependency is intended.
- Follow-up impact: runtime address/export consumers, JSON-LD contexts, vocabulary/profile generation,
  deployment URL inputs, discovery output, refresh eligibility and replies, audit token routing and its reviewed
  declarations, native documentation guidance and all affected human docs. Live observations and owner reports
  of 26 October are recorded in design decisions 24-27; the existing staged implementation is not changed by capture.
  Decision 28, revised on 28 October, keeps the namespace in artifact/reuse identity but takes it from a reviewed
  setting; the live-production lookup and the pair check are removed. Finishing impact (decision 29 and group 16):
  the quick job's install, the audit's App tokens, the scheduled refresh summary, the digest renderer and
  publisher, `assemble_pages.py`, the deployment scripts, the native content rule and the affected runbooks.
  Review repairs (decision 30, 16.13-16.26): the watch and digest publisher, `check_docs.py`,
  `check_public_content.py`, the release, publication and image workflows and their scripts, and the RDF test pins.
  Version image tags (decision 31, 16.32-16.33): `publish-image.yml`, its workflow test, `docs/deployment.md`, the
  changelog and a one-time maintainer alias of the four earlier images.
