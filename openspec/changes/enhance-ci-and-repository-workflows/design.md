# Design

## Context

The baseline is `main` at `660b1fe`, with no missing `origin/main` commits when planning started.
PR #102 contains the completed duplicate safety/actual PR #82 repair and archived specs, including
commit `c8f58bc`; it is not merged into this baseline. Integrate that reviewed dependency before applying
the dependent duplicate/collector work, without merging, reimplementing or archiving it through this plan.

The three consumed plans were unapplied: 15 changelog tasks, 24 maintenance tasks and 23 handoff tasks.
All 17 existing requirement blocks are retained in this delta. Their former task IDs are mapped below;
none becomes complete merely because it was consolidated. Original usage sessions remain historical
sections of one dated rolling entry. The old local active trees are retired only after coverage validation;
they are not archived as delivered changes. A local ignored recovery snapshot protects the source drafts.

On 20 October 2026 the complete open list contained 61 issues, all with zero comments. Relevant bodies
and acceptance criteria were read, not inferred from titles. The inventory is a dated planning snapshot;
refresh issue state/discussion before hosted migration or claiming closure. This design retains the
earlier G1-G5 findings, reproduction guidance and implementation dispositions.

| Evidence | Observation | Implementation consequence |
| --- | --- | --- |
| G1-G2, isolated reproduction | No unpublished-note gate; preparation drops curated notes | Shared parser/check plus real preparation-to-check regression |
| G3 / #84 | Workflow facts are scattered; no complete catalogue/drift check | One CI page and authoritative product inventory |
| G4, isolated reproduction | Missing lane hides an otherwise known content failure | Retain trusted known diagnostics while rejecting incomplete evidence |
| G5 and PR #102 regressions | Minimal fixtures missed producer/consumer, registered-ID and attachment boundaries | Test real handoffs and content; fake remote transport only |
| PR run 39442525611 | 465s elapsed, 129s before first job, 335s job-chain span, 726s summed job duration; site build 4s | Optimize setup/scheduling, not an expensive site-output cache |
| Same PR timing artifacts | Browser lane checks 186s/217s; CPU 127s; one case queues 33s for a slot | Benchmark budgets and case granularity with unchanged coverage |
| Deploy run 39224056433 | Full staging checks 568s; about 90 minutes between assembly and deployment | Separate check time from approval/queue wait; partition preparation |
| In-memory real source publisher | A human head introduced after ownership inspection is overwritten by `force: true` | Atomic expected-head update before more parallelism; no hosted loss is asserted |
| Bot issue evidence | Seven Champion candidates, fifteen link reports, one event and pagination #101 | Migrate communication and triage, not automatically edit content or adopt candidates |

### Reproducing G1, G2 and G4

The earlier investigation used isolated release and collector fixtures with the actual implementation
functions. These are baseline observations, not acceptance results for the planned repairs. Recreate
the probes in temporary fixture directories; the ignored investigation script is not required.

- **G1:** Copy the release-version test fixture from `tests/test_release_versions.py`, replace its
  changelog with a heading without `[Unreleased]`, and call `release_versions.check(root)` with no
  requested version. The baseline returned `[]`, demonstrating that the normal metadata check did
  not enforce an unpublished section.
- **G2:** Call `release_versions.changelog()` with an unpublished note such as `Explain the duplicate
  repair.`, one eligible merged PR and its commit in the selected history. Check both the note and
  generated PR link in the output. The baseline discarded the note while retaining the lineage link.
- **G4:** Use `tests/test_check_ci.py`'s `PartitionTests.fixture`, mark the CPU `content` result as
  failed, and remove the `browser-a/lane.json`. Invoke `check_ci.collect()` with source/build identity
  verification satisfied and capture the results passed to `check_all.emit_report`. The baseline
  returned 1 but emitted only `aggregate`, losing the known content failure from the summary. Retain
  the failure exit while requiring both diagnostics in the repair regression, also after integrating
  PR #102's valid multi-failure path.

## Goals / Non-Goals

**Goals:** one approval/task boundary for repository delivery; shared policy and verification owners;
reliable complete repair handoffs; low-noise monitoring; measured performance; explicit queue semantics;
safe concurrent human/automation work; permission-gated repository-wide Project management.

**Non-goals:** changing FAIR interpretation, evaluator mappings or original sources; accepting all
candidate tests; a new public API format; a backend; DNS or external-account changes; blanket link
exceptions; automatic merging; a runtime/framework migration; replacing published release history.

## Decisions

### 1. Own workflow facts and human continuation together

`docs/ci.md` owns CI policy and usage. `.github/ci-products.toml` supplies one structured catalogue for
workflow triggers, effective workflow/job/token/App permissions, write effects, artifact names/retention,
concurrency, generated ownership, product consumers and human handoff/test owners. Document the workflow
display name separately from required job context `checks`. YAML drift tests compare structured facts
exactly; human prose is checked for discoverability and reviewed for meaning. Include generated Copilot
setup without hand-editing its generated output. Link from CONTRIBUTING, agent-tooling and deployment docs.

Every CI product maps to an existing human entrypoint with outcome/significance, affected scope/revision,
next actor, exact action, prerequisites/fallback and completion evidence. Raw JSON, SBOMs, screenshots and
internal outputs link to that entrypoint; no bespoke handoff fields are added to public formats. Cover PR
summary/health/preview, duplicate commands, refresh proposals, watch reports, preparation/tagging, deployment,
images and draft releases. A successful repair still states what review/checks remain. Missing artifacts,
unavailable automation, queueing, supersession, refusal and partial results have concrete continuation.
Reserve comment space for the next step before tables; keep escaping, size bounds and bot-owned updates.

Use `tests/test_ci_docs.py` for the shared catalogue and `tests/test_ci_handoffs.py` plus existing renderer
tests for actual output. Plant omissions: missing workflow/permission, missing next action/fallback and
completion text must fail. A matching catalogue alone is insufficient evidence of a useful handoff.
Keep `docs/deployment.md` as procedural owner, `docs/maintenance.md` for triage and `docs/changelog.md`
for notes; the CI page links rather than duplicates those procedures.

Alternative rejected: separate catalogues for documentation, artifacts and handoffs. They would recreate
the ownership drift this consolidation is intended to remove.

### 2. Enforce contribution policy without inventing semantic certainty

Native content/surface rules distinguish contract changes from instances authored under an established
contract. Adding advice or a routine snapshot does not need an OpenSpec change solely because it adds
content; altered assessment meaning, behavior, formats, CI or governance does. Preserve bilingual text,
sources, issued IDs and provenance on both routes. Give contributors examples from ordinary content,
new fields, assessment logic, dependencies and workflow changes. The Guide-owned PR template records
the route and reason/reference; a lightweight local/PR check verifies the declaration and complete
referenced artifacts for a declared contract change. Reviewers judge semantics; path heuristics cannot
prove the declaration true. Missing planning cannot be repaired by inventing specs after implementation.

Use one shared contribution-policy helper, without patching delivered skills or broadening their policy.
Review the existing content PRs #39-#42 with their authors under these examples; do not rewrite their
plans or discard work automatically. Add a Guide-owned usage checker to the normal offline gate:
`usage-YYYY-MM-DD-<topic>.md`, valid date matching the initial `When`, canonical delivered field labels.
Later sessions retain the original filename date. Agent usage and content paradata remain separate.

PR declaration/body edits must refresh their governing result without letting metadata-only evidence
stand in for source/build verification. The initial bounded implementation retains required context
`checks` and reruns the full workflow on declaration edits. This correctness-first cost must be measured;
introducing a separate required metadata gate or reusing old success attestations is excluded from this
iteration unless separately replanned with its ruleset/identity implications. Do not silently change
branch protection to accommodate the checker.

### 3. Preserve authored release explanations through the whole release path

Keep one `[Unreleased]` section in `CHANGELOG.md`; use existing semantic categories where needed and
consolidate intermediate batches to settled PR outcomes. A concrete reviewer-visible omission reason
is acceptable for non-notable work, without bot/path/documentation/dependency blanket exemptions.
Local reproduction uses `CHANGELOG_NO_ENTRY_REASON`; CI reads the PR body as bounded inert event data.
Never interpolate declarations into shell, fetch their links or write them into notes automatically.

`scripts/check_changelog.py` owns parsing/base comparison in the common inventory and CPU lane. It checks
one unpublished section, meaningful entries when present, historical blocks and a changed entry or reason.
An empty section after a release is valid. The checker cannot decide editorial notability. Preserve accepted
historical section formats and legacy unpublished prose without bulk conversion.

Reuse that parser in `release_versions.py`: move the curated body byte-for-byte into the new dated release,
then append complete deduplicated PR/direct-commit lineage. Reset unpublished notes; preserve earlier
released sections byte-for-byte. A valid transition needs no self-referential new note. Reject conflicting
reserved inventory headings before writing. Keep empty-note, first-release, PR-only, direct-only and mixed
history behavior. Trusted proposal templates state their actual omission disposition; identity alone is
not permission to omit notes. Document activation for already-open PRs and late findings after release.

Alternative rejected: fragment files or requiring any changelog diff. Neither prevents the reproduced
loss and both encourage unrelated edits rather than meaningful notes.

### 4. Prepare complete repairs and retain useful failure evidence

After PR #102 is integrated, share `scripts/duplicate_repairs.py` between reporting and explicit local/
trusted application. Prepare a bounded versioned data bundle: source repository/head and checked merge
revision, fingerprints of relevant inputs, authoritative safe links, consulted source/result IDs,
instrument/name/description, deferred person/action ID/completion time and registration intent.
CI displays a draft; it does not claim the action happened or insert unfinished actions into authored TOML.

At explicit application, recompute with trusted code from current verified input; resolve a reviewed person,
choose a free nonretired action ID, record actual completion time and materialize links, provenance and only
their required registration. Existing actions are extended only by explicit compatible selection, preserving
their instruments/sources. Otherwise retain a separately attributable scoped repair action. Unknown people
get an exact identity-review route, not fabricated authorship. The local command is
`python scripts/check_duplicates.py --fix --person <reviewed-person-id>`; missing identity writes nothing.
The exact `/fix-duplicates` syntax and permission/fork/App/default-branch trust guards remain unchanged.

Prepare in isolation, run real duplicate/content/exact-base freshness validation with registered real content
and authored attachments, then check source/head preconditions before publication. Local multiple-file
replacement must roll back on write failure and preserve unrelated edits. Never register unrelated IDs,
modify accepted duplicate groups or execute instructions from CI artifacts. A complete remote repair is
one branch commit. Preserve the nonzero local no-change exit. Transitional readers accept known legacy
field-only data with an explicitly incomplete/manual handoff before new producers depend on the bundle.

For G4, preserve bounded attributable failures and copied logs/details before rejecting missing, unreadable
or invalid lanes. Keep malformed/wrong-identity records separate from accepted evidence. The gate remains
failed/partial; useful diagnostics do not excuse incomplete coverage. Plant combined known-failure plus
missing/invalid-lane cases, and pass actual producer output through collector, renderer and application.

### 5. Treat observations, review decisions and tasks as separate durable facts

`.github/health-watch.toml` owns request/report policy and exact reviewed monitoring limitations. Each
limitation records finding key, target/outcome scope, reason, evidence, reviewer, review date and deadline.
Reject wildcards, missing evidence, invalid dates and conflicting scopes. A changed URL, 403 becoming 404
or expired decision reopens triage, not a replacement issue. Acknowledged failures stay visible and rechecked.
`content/link-reviews.toml` remains the separate semantic prose-reference mechanism.

Keep HTTP/method/target evidence. Distinguish suspected missing (404/410), access denial, rate limiting and
temporary unavailability; a 403/429 does not prove a broken page or bot protection. Imported entries identify
their source and correction/refresh route. Live monitoring never becomes a mandatory network PR gate or
a failed FAIR requirement. Retain current dashboard/API contracts.

Replace the fixed first-600 selection with fair bounded selection/cursor or least-recent attempt policy.
At 673 eligible URLs and budget 600, unchanged targets receive coverage within two complete runs. Report
eligible/attempted/deferred/invalid counts. Unattempted targets retain dated unrefreshed evidence and cannot
gain failure streaks or recover. State loss is explicit. Add a per-host request cap under the global budget
and bounded Retry-After-aware handling; measure it rather than claiming it explains historical 429s.

Use reviewed extraction for watched pages; pagination such as #101 is not a source update. Preserve useful
documents/events, source dates when available and unresolved Champion candidates until maintainer review,
including unchanged subsequent runs. No automatic candidate adoption or content changes follow.

### 6. Publish one digest with recoverable human triage and retirement

Keep the observer/publisher split and version their internal evidence/plan together. Preserve valid v1
baselines/streaks; unknown or malformed state produces a truthful reset/error. Cache accelerates observation
history and coverage but does not own human decisions. Store reviewed limitations in configuration and
work/dispositions in native issue hierarchy and authorized decision-comment references.

The current digest has stable report-family/generation markers, bounded managed sections and separate
human text. Verify repository/bot/issue ownership and markers, reread before writes, preserve unmanaged
content and metadata and refuse ambiguous/concurrent managed edits. Semantic transition receipts exclude
volatile timestamps/counters: one meaningful coalesced comment per run, none for unchanged observations.
Recover remote success after failed cache/receipt persistence; save state after a verified publication
checkpoint. Never minimize an older summary until its replacement is verified.

Proposed defaults: current and two previous bot summaries visible; minimize only incorporated older bot
summaries as outdated, never human/decision/current comments. Pin when supported. Missing cleanup permission
is a visible warning, not a publication failure. Hiding old comments cannot undo notifications already sent.

Maintainers create/adopt sub-issues through native GitHub UI, with exact finding/evidence and an attributable
triage reference; no repository PR is required just to promote work. Verify current decision authority on
acceptance and retain historical receipts if roles later change. Reuse tasks covering several findings,
look up all task states, preserve ownership/acceptance criteria and retain closed dispositions. Missing
closure rationale becomes a question; recurrence never silently reopens or recreates a task.

Quarterly review and a configurable 100-comment overload hint prompt explicit trusted rotation. Identify
the expected predecessor; discover the deterministic successor; publish/verify carried unresolved evidence,
limitations and task links; link both reports; close the predecessor as superseded. Retry partial steps
without duplicate successors or two active digests. Children keep original identity, parent history and
state; the successor links open work. Publication and rotation share the health-state writer lock.

### 7. Scope concurrency to intent and the resource being mutated

| Work/resource | Policy |
| --- | --- |
| PR checks and current review summaries | Latest valid head/attempt may replace older work per PR/source; independent PRs remain independent |
| Preview artifact preparation | Latest source can supersede obsolete preparation; cancellation cannot interrupt an irreversible publish |
| Explicit refresh/fix/prepare/tag/rotation requests | Preserve accepted requests with a bounded queue or explicit duplicate/supersession/refusal; never silently lose intent |
| Pages combined production/preview and image aliases | Single serialized promotion per destination, current eligible identities checked at the write |
| Watch publication/cache checkpoint | One writer, resumable remote receipt, no parallel digest/rotation mutation |
| Source branches | Serialize automation by the actual source/branch resource and enforce an atomic reviewed-head guard against human/other workflow pushes |

GitHub's default one-pending concurrency slot replaces earlier pending runs even with
`cancel-in-progress: false`. Use supported `queue: max` where explicit intent requires preservation;
document its finite capacity and the queue-order rather than dispatch-order semantics. Validate event
eligibility before acquiring a resource queue; unrelated comments or non-release completions must not
displace valid operations. Keep release-preparation/tagging mutual exclusion and serialize moving image
aliases. Do not weaken App scope, defaults, fork restrictions, action pins or no-auto-merge rules.

Fix the demonstrated refresh race before any increased writer parallelism: inspect the exact branch head
and commits, then update only if that head still matches atomically. A final reread followed by a blind
force update remains unsafe. An explicit expected-value Git lease is one suitable mechanism. On conflict,
preserve the human head and give reconciliation/retry instructions. Coordinate refresh and duplicate repair
on the same branch; separate workflow names alone provide no cross-writer protection. Preserve interdependent
FIP collections atomically and re3data-dependent source ordering when considering narrower locks.

Separate long preparation/check jobs from the publication critical section. Approval waits must not block
independent preparation. Pages still has one destination: independently publishing production and preview
can regress the combined site. At promotion, reconcile the newest eligible digest-checked production and
selected preview or refuse stale output; preserve channel/release status and published bytes. Explicit tag
requests can conclude as superseded/refused when a newer eligible release exists; preservation is a request
outcome guarantee, not a promise to promote every historical tag. Report queued/waiting/cancelled/superseded
states with successor/run links and a completion path. Add overlap, late-arrival, interruption and burst tests.

### 8. Measure performance without trading away coverage or throughput

Use `scripts/check_policy.json` as the single local/CI budget owner; remove duplicated CLI defaults while
retaining explicit overrides and shared cross-process browser slots. Benchmark current 4 outer/2 browser
budgets against smaller outer pools and limited alternatives on equivalent hosted runners. Split long
independent cases when it reduces slot monopolization; preserve planned/executed case identities and failure
screenshots/traces. Schedule heavy validators/unit work so browser execution does not compete with all of
them on the same runner. Partition deployment through the existing verified-build inventory, keeping tag
and preview build contexts distinct and the one-artifact release trust chain intact.

Enable npm package caching keyed from `package-lock.json` and pip download/wheel caching with an explicit
`requirements-dev.txt` dependency path and compatible runtime/platform. Populate reusable default-branch
caches through trusted normal runs; PR-local caches alone do not warm sibling PRs. Always retain installation,
cold fallback and current tests. Do not cache broad site outputs or test-pass results as a substitute for
verification. Treat watch-state persistence separately from dependency caches and retain PR/privileged trust
boundaries. Browser caching/prebuilt images are opt-in experiments only: restore/pull and uncached Linux
dependencies may cost as much as the current 18-20s installation. Do not add an image-maintenance service.

Read existing unit/script/case timings before optimizing; target repeat setup/fixture work without sharing
mutable test state. Accept changes only after paired fixed-revision/context cold and warm hosted comparisons,
with at least repeated runs to distinguish a cache win from runner variation. Report queue/setup/test/upload/
approval time, source/build identity, runner resources, budgets, initial failures, full inventory and summed
job duration (not billing). No arbitrary speed claim or hard wall-clock gate follows from the unlike PR/deploy
examples above. More shards must improve measured latency without unacceptable runner-time/queue growth;
organization capacity is not established by this repository's timings.

### 9. Deliver actual production crawler files for #83

Generate from the configured base URL, including `FAIR_GUIDE_BASE_URL` overrides; use a standard XML writer
and canonical same-origin absolute locations without fragments. Initial sitemap scope is the Guide root
and `api/index.html`. Health, profile/vocabulary documents and local-test documentation keep their existing
discovery links and are deliberately not advertised in this initial sitemap. Do not invent SPA route URLs,
per-language duplicates or modification dates.

Root `robots.txt` allows production crawling, points to the absolute sitemap and disallows the configured
preview path. Preview HTML noindex remains primary. Preview copies of discovery files must not advertise
preview documents; assembly preserves the production files byte-for-byte. Validate the real build and final
assembled tree for file presence, XML, origin/path overrides, selected real documents, no hash locations and
no preview sitemap entries. This repairs delivery output, not DNS or approval of a canonical address.
Reconcile public machine-facing claims and record any required content provenance rather than editing
the reviewed snapshot sources.

### 10. Reuse Project #1 after automation access is proved

On 20 October 2026, [Project #1: EOSC CZ FAIR Guide](https://github.com/orgs/dsw-nrp/projects/1)
was verified as an open, private organization Project linked to `dsw-nrp/eosc-fair-guide`. It had no items,
one unfiltered board view named `View 1`, Status values Todo / In Progress / Done, and native Parent issue
and Sub-issues progress fields. Area, Priority and the additional planned views were absent. Personal CLI
access now works and GitHub reports `viewerCanUpdate: true`; this does not prove App-token access.

The repository's `SOURCE_REFRESH_CLIENT_ID` matches `fair-guide-actions`. Its registration exposes write
permissions for Contents, Issues, Pull requests and repository Projects, but the inspected API response
does not list `organization_projects`. Repository Projects permission does not cover this organization
Project. Organization permissions > Projects must allow read/write, and the organization owner must approve
the changed installation permissions. Installation grants were not independently readable with the personal
credential; registration metadata is not proof of installed permissions. The user confirmed that the owner
dependency remains pending. Do not broaden the personal CLI token merely to inspect installation settings.

Reuse this existing Project and preserve its private visibility and repository link. The Guide-wide Project
covers content, interface, maintenance, delivery and tooling. Proposed fields are Status, Area and Priority;
views are Overview, Ready, Maintenance and Release preparation, with
native parent/sub-issue progress. Prefer native auto-add/status/archive workflows and explicit reviewed
backfill of existing issues and active PRs. Import is idempotent, preserves metadata/human field values and
creates no card for each raw observation. Completed-item archival does not close issues.

Project implementation, configuration, setup/import and any adapter stay unchecked until owner approval,
actual automation-identity access and concrete setup approval are recorded. After owner approval, first
verify that a fresh installation token can read this exact Project and its fields; verify necessary writes
only within the approved setup/import scope. The existing jobs explicitly request narrower token permissions;
retain those limits and request organization-Project access only for the job that needs it, using the current
repository scope. Repository Projects-enabled and personal access are insufficient; the repository
`GITHUB_TOKEN` and App registration alone do not establish organization-Project automation access.
Add a narrow adapter only for a demonstrated native gap. Later access loss yields a visible synchronization
warning; issue triage/digest publication continue, and recovery reconciles missing entries without duplication.

### 11. Reconcile issues without silently expanding or closing them

| Issues read | Disposition within this change |
| --- | --- |
| #84 | Fully consume its original CI page, all workflow/artifact facts, exact drift comparison, generated ownership, local reproduction and cross-links. Its documentation-only non-goals remain historical issue scope; this approved plan separately proposes code repairs. Prepare a reviewed issue amendment/link before claiming that issue accepted the wider scope. |
| #83 | Fully include production crawler generation, real-build/assembly tests, configured origin, explicit document scope and documentation/paradata. |
| #59-#65 | Migrate seven Champion candidate notifications to retained digest triage; no candidate selection or assessment semantics are approved here. |
| #85-#99 | Migrate fifteen link observations to digest/known-limit review or retain existing actionable tasks after human triage; no bulk false-positive declaration or unsupported snapshot edit. |
| #100, #101 | Retain the potentially relevant event for review; fix pagination extraction and disposition #101 as noise only in the approved migration. |
| #6 | Contribute bounded CI test/handoff gap evidence and positive/negative regressions; full criterion/source/evidence-to-answer/FAIR semantic audit remains open. |
| #25; PR #70 | Keep current validated crate/profile/dependency compatibility; future upgrade-readiness decision and the incompatible jsonschema proposal are separate. No version adoption or closure claimed. |
| #80 | External best-practices registration remains a human-owned follow-up; this work may supply evidence links but does not register, certify or display a badge. |
| #15, #32 | Canonical-address/DNS/hosting decisions remain external dependencies. #83 uses the existing configurable base and does not assert adoption or hosted resolution. |
| #14 | Mapping maintenance ownership/semantics stay with the named reviewer and content lead; the Project can track it without implementing it. |
| #5, #7-#13, #16-#24, #26-#31, #33, #35-#38, #43 | Retain independent content, source, service, UI, licensing and editorial issues; Project backfill can include them without absorbing their implementation. |

This table partitions all 61 open issues in the inspected snapshot exactly once. The complete live issue
inventory and thread must be refreshed before any migration. Reuse original issue numbers, assignees,
labels, milestones, discussions and acceptance scope. No remote issue update/closure, comment hiding or
Project operation is authorized by creating this plan. An absorbed notification closes as absorbed or
superseded with a verified successor link, never as recovered. Content remediation, when warranted, follows
its own source/paradata checks and human triage.

### 12. Former tasks have explicit integrated owners

Ranges refer to original task IDs, not completion. The combined delta preserves the source requirement
blocks; this mapping prevents task-level obligations from vanishing when the three active drafts retire.

| Consumed plan | Former tasks | Integrated tasks |
| --- | --- | --- |
| `unreleased-changelog-policy` | 1.1-1.2 | 2.1 |
| `unreleased-changelog-policy` | 1.3 | 3.1 |
| `unreleased-changelog-policy` | 2.1 | 2.2 |
| `unreleased-changelog-policy` | 2.2, 4.1 | 2.3 |
| `unreleased-changelog-policy` | 2.3 | 2.5 |
| `unreleased-changelog-policy` | 3.1-3.3 | 2.4 |
| `unreleased-changelog-policy` | 4.2 | 3.3 |
| `unreleased-changelog-policy` | 4.3 | 2.6 |
| `unreleased-changelog-policy` | 5.1 | 13.1 |
| `unreleased-changelog-policy` | 5.2 | 13.2 |
| `unreleased-changelog-policy` | 5.3 | 13.3 |
| `consolidate-maintenance-reporting` | 1.1 | 6.1 |
| `consolidate-maintenance-reporting` | 1.2, 2.1 | 6.2 |
| `consolidate-maintenance-reporting` | 1.3, 2.3 | 6.4 |
| `consolidate-maintenance-reporting` | 2.2 | 6.3 |
| `consolidate-maintenance-reporting` | 2.4, 3.1 | 7.1 |
| `consolidate-maintenance-reporting` | 3.2, 3.4 | 7.2 |
| `consolidate-maintenance-reporting` | 3.3 | 7.3 |
| `consolidate-maintenance-reporting` | 4.1-4.2 | 7.4 |
| `consolidate-maintenance-reporting` | 5.1-5.2 | 7.5 |
| `consolidate-maintenance-reporting` | 6.1-6.4 | 11.1-11.4 |
| `consolidate-maintenance-reporting` | 7.1-7.3 | 12.1-12.3 |
| `consolidate-maintenance-reporting` | 8.1 | 13.1 |
| `consolidate-maintenance-reporting` | 8.2 | 13.2-13.3 |
| `actionable-ci-repair-bundles` | 1.1 | 1.2 |
| `actionable-ci-repair-bundles` | 1.2 | 1.1 |
| `actionable-ci-repair-bundles` | 1.3 | 1.3 |
| `actionable-ci-repair-bundles` | 2.1, 2.3 | 4.1 |
| `actionable-ci-repair-bundles` | 2.2 | 4.2 |
| `actionable-ci-repair-bundles` | 3.1 | 4.3 |
| `actionable-ci-repair-bundles` | 3.2-3.3 | 4.4 |
| `actionable-ci-repair-bundles` | 3.4 | 4.5 |
| `actionable-ci-repair-bundles` | 3.5 | 4.6 |
| `actionable-ci-repair-bundles` | 4.1, 4.4 | 5.1 |
| `actionable-ci-repair-bundles` | 4.2 | 5.2 |
| `actionable-ci-repair-bundles` | 4.3 | 5.3 |
| `actionable-ci-repair-bundles` | 5.1-5.2 | 5.4 |
| `actionable-ci-repair-bundles` | 5.3 | 5.5 |
| `actionable-ci-repair-bundles` | 5.4 | 1.4, 3.4 |
| `actionable-ci-repair-bundles` | 6.1 | 13.1 |
| `actionable-ci-repair-bundles` | 6.2 | 13.3 |
| `actionable-ci-repair-bundles` | 6.3 | 12.4 |
| `actionable-ci-repair-bundles` | 6.4 | 12.3, 13.2 |

## Risks / Trade-offs

- Scope could become a repository rewrite -> the issue disposition table and capability deltas are the
  boundary; reject unrelated content/assessment work and retain explicit acceptance milestones.
- More parallel work could increase queues or expose stale writes -> atomic branch guards and publication
  identity precede concurrency expansion; report both latency and summed runner time.
- New governance could recreate friction -> normal content has an explicit non-contract route; declarations
  and diagnostics explain remedies, while people judge notability and semantics.
- Cache/state or API writes can fail partway -> cold fallbacks, trusted remote receipts, single writers,
  conflict refusals and interruption/retry tests; no cached human decision becomes authoritative.
- Metadata edits initially rerun a full gate -> accept and measure that bounded cost before designing a
  separate required context; do not manufacture source verification from body-only checks.
- Organization-owner approval of App installation permissions and hosted activation may lag local work ->
  keep those tasks visibly incomplete; verified personal access does not discharge the automation gate. Avoid
  claiming complete delivery or archival until their actual acceptance or approved rescoping.

## Migration Plan

1. Verify the three source requirement/task mappings and issue dispositions, then retire only their
   unapplied local trees. Preserve historical usage sessions; do not archive them as completed work.
2. After explicit apply approval, integrate the PR #102 dependency for affected work and implement policy,
   shared validation and producer/consumer tests in the existing trust architecture. Land tolerant readers
   before new bundle/watch producers; migrate valid baseline state explicitly.
3. Repair concurrent branch updates before increasing parallelism. Introduce caches and partitioned
   preparation with measured unchanged coverage. Activate declaration triggers with actionable transition
   guidance for existing PRs. Add real crawler files and verify actual build/assembly.
4. Prepare the exact first digest and a refreshed issue-by-issue dry run. Obtain concrete hosted approval,
   publish/migrate, test receipt/retry/rotation behavior, then activate unattended publication. Do not resume
   the old per-finding publisher in parallel. Reuse Project #1 as a separate milestone after owner approval
   and verification with the App identity. This dependency holds Project work, not independent approved CI work.
5. Record local results, hosted performance/activation and human outcomes separately. Roll back through
   reviewed reverts or disable the affected publisher while retaining evidence and human state; preserve
   completed authored repairs, notes and immutable releases. Archive only after verified completion and
   explicit approval, with reviewed spec sync.

## References

- [CI catalogue issue #84](https://github.com/dsw-nrp/eosc-fair-guide/issues/84) and [crawler files #83](https://github.com/dsw-nrp/eosc-fair-guide/issues/83).
- [Duplicate repair dependency PR #102](https://github.com/dsw-nrp/eosc-fair-guide/pull/102).
- [Existing Guide Project #1](https://github.com/orgs/dsw-nrp/projects/1) and [fair-guide-actions registration](https://api.github.com/apps/fair-guide-actions).
- [Measured PR run](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/39442525611) and [deployment run](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/39224056433).
- [GitHub concurrency and queues](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).
- [Git expected-value leases](https://git-scm.com/docs/git-push) and [cache scope](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching).
- [npm caching](https://github.com/actions/setup-node#caching-global-packages-data), [pip caching](https://github.com/actions/setup-python#caching-packages-dependencies) and [Playwright cache guidance](https://playwright.dev/docs/ci#caching-browsers).
- [Project automation permissions](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/automating-projects-using-actions) and [auto-add/backfill](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/adding-items-automatically).
- [Installation approval and explicit token permissions](https://github.com/actions/create-github-app-token#how-it-works).
