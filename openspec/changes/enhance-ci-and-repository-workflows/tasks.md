# Tasks

All tasks are unapplied. Tasks depending on PR #102 require its reviewed implementation/spec baseline
first; do not merge that PR implicitly. Project #1 exists and personal access is verified; section 11
waits for organization-owner approval of App installation permissions and verification with the App identity
before any Project implementation/configuration. Independent CI work can proceed under its apply approval.
Section 12's hosted writes require concrete approval.
Neither permission-dependent nor hosted work becomes complete through local tests or consolidation.

## 1. Shared CI catalogue and policy owners

- [ ] 1.1 Build `.github/ci-products.toml` for all workflows, effective triggers/token/App permissions, writes, artifacts/retention, concurrency, generated ownership, consumers and handoff/test owners; verify complete coverage against actual workflow YAML, explicitly including setup/internal products and PR #102 when integrated.
- [ ] 1.2 Write `docs/ci.md` policy/usage with the six-field human handoff, exact `checks` context, full partition/reconciliation contract, generated setup ownership and local build/lane/collect/profile commands; verify executable examples and links from CONTRIBUTING, agent-tooling and deployment docs, preserving their procedural owners.
- [ ] 1.3 Add common-gate catalogue/drift and rendered-handoff tests; prove planted missing workflows, effective permission/trigger/artifact/concurrency mismatches and absent action/fallback/completion fields fail with specific remedies rather than passing on declarations alone.
- [ ] 1.4 Refresh the issue/PR dependency inventory and reconcile #84's original criteria with the design's expanded code scope; verify every listed issue retains its disposition, PR #102 remains an explicit dependency and any proposed remote amendment preserves original acceptance/metadata for later approval.

## 2. Unpublished notes and release preservation

- [ ] 2.1 Author `docs/changelog.md`, PR-template disposition and contribution/deployment links for notability, settled scope, categories, late findings and concrete omission reasons; verify normal/reason-only commands are discoverable and no blanket bot/path exemption is documented.
- [ ] 2.2 Implement the common changelog parser/check for one unpublished section, meaningful entries and preserved released blocks; prove missing/duplicate/placeholder sections and historical edits fail while empty post-release sections and accepted old formats remain valid.
- [ ] 2.3 Add base-aware note/reason checking once to the shared inventory and CPU lane, taking bounded event data or the documented local reason; verify local/partitioned rules and bases agree and injected declaration syntax is never executed or fetched.
- [ ] 2.4 Preserve the curated body byte-for-byte beside deduplicated PR/direct lineage in `release_versions.py`; prove planted note loss and reserved-heading conflicts fail before writes and legacy/empty/first/PR-only/direct-only/mixed releases retain historical bytes. Document curated versus generated ownership.
- [ ] 2.5 Recognize a complete release transition without another unpublished note; run actual prepared output through the checker and prove missing retained entries, stale release metadata or older-section rewrites are rejected.
- [ ] 2.6 Add truthful maintenance dispositions to trusted proposal templates and document rollout for existing bot PRs; verify identity alone cannot bypass the gate and a notable bot change still needs an entry or a concrete reviewed reason.

## 3. Proportionate contribution governance and usage checks

- [ ] 3.1 Update Guide-owned content/surface guidance and contributor examples for contract versus content-instance routing, changelog policy and the CI handoff owner; regenerate readers and verify ownership/delivery checks without modifying delivered tooling or rewriting original content/source meanings.
- [ ] 3.2 Implement shared local/PR disposition validation for declared OpenSpec-triggering work and the existing-contract route; prove ordinary advice/wording/refresh fixtures need no invented capability, declared contract changes require complete scoped artifacts, and diagnostics leave semantic classification to review.
- [ ] 3.3 Wire PR declarations as inert event data and declaration edits to fresh governing execution under the existing required `checks` context; prove missing-to-corrected declarations update correctly, no metadata-only path claims full coverage and current-head cancellation/trust invariants survive. Document the initial full-rerun cost and author-reviewed routing of PRs #39-#42.
- [ ] 3.4 Add the Guide usage filename/date/canonical-field check to the offline suite; plant undated, impossible-date and initial-date mismatch entries and verify exact remedies, while later rolling sessions retain their start-date filename. Document the delivered owner and keep content provenance separate.

## 4. Complete duplicate repair bundles

- [ ] 4.1 After the reviewed PR #102 baseline is present, add shared read-only repair preparation for safe links, provenance draft, registration intent, deferred actor/time/action ID and source fingerprints; verify a real original-duplicate fixture contains every obligation with unchanged authored bytes, and document the emitted shape.
- [ ] 4.2 Carry the bounded versioned bundle from the real duplicate producer through the collector with distinct source head/checked revision; prove stale, conflicting, existing-key, accepted-exception, unsupported-version, path and size/count cases cannot become applicable repairs.
- [ ] 4.3 Share truthful provenance finalization and scoped registration across application routes; test reviewed/unknown identity, nonretired action IDs, explicitly selected compatible prior actions and preservation of unrelated provenance, sources, instruments and all issued/retired IDs.
- [ ] 4.4 Route local `--fix --person` through isolated materialization, real registered-content/duplicate/exact-base validation and transactional replacement; prove missing identity/registration/attachments, unrelated errors, concurrent local edits and injected write failures preserve original authored bytes, while a valid result contains exactly the required complete repair.
- [ ] 4.5 Route trusted `/fix-duplicates` through the same finalization while retaining caller permissions, App scope, fork/default-branch exclusions and initial/final head guards; fake remote transport only and verify one complete content/provenance/register commit or no commit on refusal.
- [ ] 4.6 Update command help, CONTRIBUTING and content-model guidance for preview, explicit person/optional action selection, reviewed identity registration, full diff inspection, rerun and rollback; execute the documented fixture commands and verify idempotence and the nonzero local no-change contract.

## 5. Human handoffs and incomplete-evidence diagnostics

- [ ] 5.1 Render actual collector bundles in the existing bounded PR comment, including provenance/registration drafts, deferred fields, eligible command, local fallback and completion evidence; verify legacy data is explicitly incomplete and reserve handoff space ahead of long tables while retaining escaping and bot-owned update tests.
- [ ] 5.2 Give duplicate success/refusal paths concrete continuation for unknown person, forks, missing App/access, changed head, remaining errors and already-completed work; verify rendered instructions distinguish a completed commit from pending checks/review and expose no secrets.
- [ ] 5.3 Retain attributable known failures alongside missing/unreadable/wrong-identity lane diagnostics and copied logs/details; prove planted simultaneous content failure plus absent/invalid lane reports both without accepting rejected evidence or claiming a pass. Include actionable health/setup/missing-report fallbacks and document current design.
- [ ] 5.4 Apply the handoff contract to source-refresh and current/new monitoring entrypoints, including unchanged/rejected/human-edited/partial outcomes; exercise real producer/publisher output and plant missing reconciliation or completion instructions. Link CI and maintenance procedures without adding per-finding notifications.
- [ ] 5.5 Apply the contract to prepare/tag, deploy, image and draft-release outputs with exact source/artifact identity, prerequisites, recovery and separately authorized continuation; verify actual producer/consumer fixtures reject missing review/publication steps and update the owning deployment procedure.

## 6. Honest bounded monitoring and reviewed limitations

- [ ] 6.1 Add `.github/health-watch.toml` policy/limitation parsing with exact key/target/outcome, evidence, reviewer and review/deadline fields; prove wildcard, missing-evidence, conflicting and invalid-date entries fail offline, and document the distinct configuration versus issue/prose-link owners.
- [ ] 6.2 Separate suspected missing, denied, rate-limited, timeout and other unavailable outcomes, retaining HTTP/method/source evidence; verify 403/429 never establish disappearance, changed target/outcome or expiration requires triage, recovery preserves historical decisions and no live finding becomes a FAIR verdict.
- [ ] 6.3 Implement fair bounded selection and a per-host cap under the global request budget with bounded Retry-After handling; verify all unchanged 673/600 targets are reached within two complete runs, deferred targets do not recover/accrue streaks and per-host throttling cannot starve other hosts. Document explicit coverage/reset semantics.
- [ ] 6.4 Add source-specific extraction and pending-candidate fixtures; prove #101 pagination/cosmetic navigation produces no finding while real events/documents and unchanged unresolved Champion candidates persist. Document human triage, imported-record correction routes and source-date limits in `docs/maintenance.md`.

## 7. One digest, durable triage and resumable retirement

- [ ] 7.1 Version observer/publisher evidence together and publish one discoverable digest with bounded managed sections and human text preserved; verify valid v1 state migration, unknown/malformed reset, exact bot/issue ownership, concurrent/ambiguous body refusal and unchanged public health/API semantics.
- [ ] 7.2 Add semantic transition receipts, coalesced meaningful comments and publication-aware cache persistence; prove timestamp/counter-only runs do not comment and remote-success/cache-failure retries recover without duplicates. Verify watch publication/checkpoint serialization and document artifact-retention limits.
- [ ] 7.3 Pin the current bot summary where supported and minimize only incorporated older bot summaries after replacement verification; prove human/decision/current comments and spoofed markers survive, failures cannot hide evidence and missing cleanup capability gives a visible warning. Document proposed retention defaults.
- [ ] 7.4 Support native maintainer creation/adoption of sub-issues with exact findings/evidence and authorized decision receipts; verify schedules never promote work, one task can cover multiple findings, closed dispositions are retained, current authority is checked on acceptance and missing rationale never implies reopening or duplicate work.
- [ ] 7.5 Add explicit expected-digest rotation and deterministic successor recovery; test interruption at each publication/link/closure step, retained unresolved findings/limitations/open-task references and unchanged child identity/state. Document quarterly review and the configurable 100-comment overload hint, with supersession distinct from recovery.

## 8. Intent-aware queues and safe concurrent writes

- [ ] 8.1 Repair the reproduced source-refresh race with an atomic expected-reviewed-head condition at branch update; inject a human push after ownership inspection and prove the human head survives, no blind force update succeeds and retries are idempotent. Document the conflict/reconciliation route and retain bot-ownership/no-default-branch-write protections.
- [ ] 8.2 Define and implement workflow resource/intent keys and bounded request queues while retaining per-PR latest-head cancellation and release preparation/tag mutual exclusion; test three overlapping explicit requests, duplicate requests, queue overflow and unrelated events, proving accepted intent receives an inspectable terminal outcome.
- [ ] 8.3 Coordinate refresh/repair writers by actual target resource and preserve dependent source/FIP atomicity; test competing automation and human edits on the same branch, independent sources and late head changes. Verify non-PR/unauthorized events cannot consume a valid command's resource queue and document ownership boundaries.
- [ ] 8.4 Separate cancellable preparation from serialized combined-Pages/image promotion and recheck current eligible artifact/channel identity at publication; test older output waiting for approval, newer preview/production arrival, cancellation and retry without channel regression or mutable release identity.
- [ ] 8.5 Document queue order/capacity, waiting/approval/supersession and recovery in the CI catalogue and actual handoffs; verify planted missing successor/retry information fails and no workflow-level lock holds independent preparation solely for a publication approval wait.

## 9. Measured caching and execution performance

- [ ] 9.1 Add compatible npm and pip package caches to PR and normal trusted deployment setup, explicitly keying the actual lock/requirements inputs; test changed inputs, cold/missing/failed restore and default-branch reuse boundaries, record hit/miss/install timings and document why installation/current checks still run.
- [ ] 9.2 Make local and partitioned CI consume one execution-budget owner with explicit overrides and retained cross-process browser limits; verify environment/CLI/policy precedence, bounded independent processes and complete case receipts, and document runnable budget comparisons.
- [ ] 9.3 Partition deployment verification through the existing verified-build inventory, preserving distinct tag/preview contexts and release-artifact reuse; prove missing/duplicate/wrong-source/build/case evidence still fails, then compare equal-coverage baseline/candidate hosted runs and document actual setup/active/approval/runner costs.
- [ ] 9.4 Use existing unit/script/case profiles to reduce repeated setup or long slot ownership where measured, benchmarking bounded worker/case alternatives; prove initial failures, isolation, traces/screenshots, all cases and three validator profiles remain. Record repeated fixed-context cold/warm comparisons; retain browser caching, images or more shards only if measured benefit justifies restore/setup and runner/queue cost.

## 10. Production crawler artifacts

- [ ] 10.1 Generate `robots.txt` and XML `sitemap.xml` from configured base/origin/path, advertising the root and `api/index.html` only, with preview disallow and no hash routes/invented dates; verify real build outputs for normal and overridden bases and actual advertised files.
- [ ] 10.2 Preserve production crawler bytes during real production/preview assembly, retain preview HTML noindex and prevent preview sitemap advertisements; plant missing/malformed/wrong-origin/preview-entry failures in actual build/deployment tests rather than synthetic files alone.
- [ ] 10.3 Reconcile current delivery/design/deployment and public machine-facing claims, adding any required registered paradata; verify the documented sitemap scope, excluded documents and separate DNS/adoption ownership match the output and #83 acceptance.

## 11. Existing Guide Project #1: organization-owner dependency

- [ ] 11.1 After the organization owner approves the required installation permissions, verify `fair-guide-actions` has organization Projects read/write and can read Project #1 and its fields using a fresh installation token; registration currently lists repository Projects write but no organization Projects permission. Present the concrete setup/import scope and leave 11.2-11.4 unchecked until automation access and setup approval are recorded. Verified personal access alone does not discharge this task.
- [ ] 11.2 After permission and setup approval, reuse `https://github.com/orgs/dsw-nrp/projects/1`, preserving its private visibility, repository link and native hierarchy; reconcile existing Status and `View 1` with the approved Status/Area/Priority fields and Overview/Ready/Maintenance/Release preparation views, verify live configuration and ownership and document its use without per-observation cards. Keep existing workflow tokens narrow and request organization-Project access only for the job that needs it.
- [ ] 11.3 Configure native lifecycle automation and execute a reviewed backlog/active-PR import; verify idempotent retries, preserved titles/labels/milestones/assignees/states/scopes and human field values, and that completed-item archival never closes issues.
- [ ] 11.4 Add a narrow trusted adapter only for a demonstrated native lifecycle gap; verify later Project denial leaves digest and triage usable with a synchronization warning, and recovery fills missing entries without duplication or implicit App permission expansion.

## 12. Controlled hosted rollout and human acceptance

- [ ] 12.1 Refresh every legacy health issue's full thread/state and prepare an issue-by-issue migration preview; verify #59-#65 and #85-#101 each maps to retained actionable work or a digest observation/noise disposition with original evidence and metadata, and refresh the broader 61-issue disposition table without treating it as a closure list.
- [ ] 12.2 Obtain approval of the exact first digest and migration/amendment payloads before hosted writes, then apply and reread them; verify absorbed notifications link to the digest and close as absorbed/superseded, retained tasks preserve identity/state and #83/#84 closure claims match delivered acceptance only.
- [ ] 12.3 Perform separately approved default-branch hosted activation/retry/rotation and same-repository repair exercises with real bot/App behavior; verify permissions, complete repair commits, stale/unknown-person refusals, receipts and state recovery before unattended operation, recording Project acceptance separately and obtaining explicit owned deferral for any unexercised hosted gate.
- [ ] 12.4 Walk through failure, blocked privileged repair, queued/superseded operation and successful completion as a contributor without session context; verify the actual rendered instructions alone suffice to continue, and record remaining human decisions rather than counting local fixtures as human acceptance.

## 13. Integrated verification and close-out

- [ ] 13.1 Pass real build/lane/collector/renderer/repair, release-preparation/checker and observer/publisher data through their complete consumers with fake remote transport only; verify planted missing registration/attachments, invalid lane evidence, partial writes, lost cache and human races fail without weakening accepted behavior.
- [ ] 13.2 Reconcile the integrated task/issue dispositions, settled full-scope changelog and dated rolling usage entry with local, hosted/performance and human evidence; verify every retained source obligation has an outcome and pending Project/hosted work remains explicit rather than complete by consolidation.
- [ ] 13.3 Run strict OpenSpec validation, native generation/ownership/delivery checks and `python scripts/check_all.py`; verify the full original deterministic coverage plus new gates pass and performance receipts retain the same case/validator floor. Report unresolved permission/external constraints before any completion/archive claim.

## Workflow follow-up

- Begin implementation only after a fresh apply instruction for this combined change.
- Keep commits/pushes, remote issue payloads/migration, rulesets, Project setup, hosted dispatch, release publication and archive within their separately authorized scopes.
- Archive only after verified completion and explicit approval, synchronizing reviewed deltas first; the retired source drafts are superseded plans, not completed archived deliveries.
