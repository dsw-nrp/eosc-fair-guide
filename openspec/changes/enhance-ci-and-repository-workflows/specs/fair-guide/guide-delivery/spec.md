# Spec Delta

## MODIFIED Requirements

### Requirement: Scheduled jobs never commit directly

Scheduled jobs SHALL deliver snapshot refreshes as pull requests and report monitoring observations in
one current health digest. They SHALL watch the EOSC CZ outputs, service catalogue, training, Open Science
III FAQ, minizáměry calls, acknowledgement and data steward pages and group relevant updates for
maintainer review, excluding navigation and pagination. Jobs SHALL NOT commit to the default
branch or create actionable sub-issues without maintainer triage.

#### Scenario: Broken external link found

- **GIVEN** the weekly link check finds a persistently failing external link
- **WHEN** it completes
- **THEN** it updates the current digest with the observed response, persistence, affected entries and evidence instead of opening a separate work issue automatically

#### Scenario: New EOSC CZ output

- **GIVEN** the EOSC CZ outputs page lists a document that was not there at the previous run
- **WHEN** the watch job runs
- **THEN** it groups the document in source updates to review, retaining its address or anchor and any available publication date without inventing one

#### Scenario: Pagination changes on a watched page

- **GIVEN** the training page adds a next-page link without adding a relevant source item
- **WHEN** monitoring compares the page with its baseline
- **THEN** the navigation change creates no candidate, notification or work issue

### Requirement: Health and source-watch reports remain actionable

Health reporting SHALL distinguish integrity, age, availability and verdicts and retain attributable
dates, revision and scope for existing dashboard/API consumers. Persistent observations and source updates
SHALL use stable finding keys in a digest without notification floods. Access denial or rate limiting
SHALL NOT establish a broken link; service failure SHALL NOT establish a failed FAIR requirement. Live
monitoring SHALL remain separate from deterministic PR gates.

#### Scenario: A test returns an indeterminate verdict

- **GIVEN** a completed live test with an indeterminate native result
- **WHEN** health is summarized
- **THEN** it is distinguishable from transport failure, a negative criterion result and a positive answer suggestion

#### Scenario: The runner receives an inconclusive response

- **GIVEN** a link request returns HTTP 403, HTTP 429 or a timeout
- **WHEN** the digest is rendered
- **THEN** it distinguishes access denied, rate limited and temporarily unavailable observations without asserting that the page is gone or that bot protection is confirmed

#### Scenario: A potential failure concerns imported content

- **GIVEN** the failing URL originates in a reviewed upstream snapshot
- **WHEN** the finding is shown
- **THEN** it names the affected resource and its source, supplies the relevant evidence and identifies the upstream or refresh correction route rather than directing an unsupported snapshot edit

## ADDED Requirements

### Requirement: Unpublished changelog entries follow a standing contribution policy

Contributors SHALL describe notable reader or maintainer changes in `[Unreleased]` using the settled PR
scope. A PR without such an entry SHALL give a concrete omission reason for review. Standing human and
agent instructions SHALL identify the same policy and explain release preparation and late findings.

#### Scenario: A notable change is ready for review

- **WHEN** a PR changes reader or maintainer behavior
- **THEN** its unpublished entry explains the resulting behavior under the applicable change category
- **AND** intermediate implementation batches are consolidated into the settled PR scope

#### Scenario: A change needs no release note

- **WHEN** a contributor considers a wording, test-only or routine maintenance change non-notable
- **THEN** the PR records a concrete omission reason for the reviewer instead of an invented release entry
- **AND** a bot author alone does not exempt a change

#### Scenario: A finding arrives after the original PR or release

- **WHEN** a new correction is made after the original work was merged or released
- **THEN** its notable effect is recorded for the next release in `[Unreleased]`
- **AND** the affected older version can be named without rewriting published history

### Requirement: Local and PR checks enforce the unpublished changelog contract

The shared check inventory SHALL validate one top-level `[Unreleased]` section and its non-placeholder
entries. Against a base revision it SHALL require a changed entry or concrete omission reason and reject
edits to existing released sections. A valid release transition SHALL be accepted. Checks SHALL read PR
declarations as data, fail with actionable diagnostics, and never edit the changelog themselves.

#### Scenario: A PR omits an entry and a reason

- **WHEN** changed content has neither an updated unpublished entry nor a concrete omission reason
- **THEN** local and PR verification fail and identify the entry or declaration needed

#### Scenario: A declaration is corrected

- **WHEN** the PR's omission reason is added or edited
- **THEN** the governing check can run against that current declaration without executing it as code

#### Scenario: The section is malformed or only a placeholder

- **WHEN** `[Unreleased]` is absent, duplicated or populated only with empty headings or placeholders
- **THEN** verification reports the malformed structure or missing meaningful entry
- **AND** an intentionally empty section after release remains valid

#### Scenario: Published history is changed

- **WHEN** a PR changes an existing released section relative to its base
- **THEN** verification refuses the historical edit and directs the correction to the next release
- **AND** historical section formats that were already accepted are preserved without forced conversion

#### Scenario: A release consumes the unpublished entries

- **WHEN** valid release preparation moves the unpublished entries into its new dated section
- **THEN** verification accepts the transition without requiring another unpublished entry
- **AND** an incomplete transition that loses entries or changes earlier releases is rejected

### Requirement: Release preparation retains curated unpublished notes

Release preparation SHALL retain the curated unpublished body in the new dated release and reset
`[Unreleased]`. The complete deduplicated PR/direct-commit inventory SHALL remain discoverable alongside
those notes. Existing released sections and their accepted formatting SHALL remain byte-identical;
previously accepted unpublished prose SHALL not be silently discarded or require a migration.

#### Scenario: Curated notes and release lineage are both available

- **WHEN** the maintainer prepares a release with curated notes and eligible PRs or direct commits
- **THEN** the dated release retains the notes and the complete linked lineage inventory
- **AND** the generated inventory does not substitute PR titles for the curated explanations

#### Scenario: There are no curated unpublished notes

- **WHEN** release preparation finds an empty unpublished section and valid nonempty release history
- **THEN** it retains the existing supported PR-only, direct-only and first-release behavior

#### Scenario: Older prose or published sections already exist

- **WHEN** release preparation reads previously accepted free-form unpublished prose or older released headings
- **THEN** it preserves that prose and the historical release bytes without a bulk rewrite

### Requirement: Monitoring coverage is bounded and explicit

Monitoring SHALL disclose the eligible, attempted, deferred and invalid-target counts and distinguish
unobserved targets from successes. Bounded selection SHALL give unchanged eligible targets continuing
coverage rather than repeatedly selecting one fixed prefix. Deferred runs SHALL NOT manufacture
recovery or increment failure persistence for unattempted targets.

#### Scenario: The inventory exceeds the request budget

- **GIVEN** 673 eligible URLs and a 600-request run budget
- **WHEN** successive complete runs inspect the unchanged inventory
- **THEN** every URL is attempted within two runs and each report states its own attempted and deferred coverage

#### Scenario: A previously failing target is deferred

- **GIVEN** a target has a persistent failure and is outside this run's selection
- **WHEN** the next summary is produced
- **THEN** it retains the dated previous observation as unrefreshed without counting a new failure or recovery

### Requirement: Reviewed monitoring limitations retain their basis

A monitoring limitation SHALL identify an exact finding and outcome scope, reason, evidence, reviewer,
review date and review deadline. Acknowledged observations SHALL remain visible and be rechecked.
Expired decisions or changed targets/outcomes SHALL require renewed review without flooding issues.
Blanket host exemptions and converting acknowledged failures into passes SHALL be refused.

#### Scenario: A reviewed blocked request recurs

- **GIVEN** a current decision acknowledges HTTP 403 for one exact URL
- **WHEN** that response recurs
- **THEN** it remains a known monitoring limitation with fresh observation evidence and creates no duplicate work item or repeated unchanged notification

#### Scenario: The basis changes or expires

- **GIVEN** an acknowledged 403 becomes a 404, its target changes, or its review deadline passes
- **WHEN** the next applicable run reconciles decisions and observations
- **THEN** it presents the changed or expired decision for triage and no longer applies the old acknowledgement to the new condition

#### Scenario: A decision attempts a blanket exemption

- **GIVEN** a wildcard target, missing evidence or conflicting decisions for one finding scope
- **WHEN** configuration is validated locally or in PR checks
- **THEN** validation fails with an actionable diagnostic without suppressing observations

### Requirement: Maintainers control promotion into actionable work

An observation SHALL become an actionable sub-issue only through explicit maintainer triage. Promotion
SHALL retain the finding keys, evidence and parent relationship and reuse an existing task where
appropriate. Automation SHALL retain human dispositions, closed-task history and ownership; recurrence
SHALL request triage without silently reopening or recreating work.

#### Scenario: A persistent failure has not been triaged

- **GIVEN** a previously unreviewed link fails across several runs
- **WHEN** scheduled publication runs
- **THEN** it remains in the digest for triage and no actionable sub-issue is created

#### Scenario: A maintainer promotes related findings

- **GIVEN** a maintainer chooses an existing or new issue to address related observations
- **WHEN** that decision is recorded and the issue is attached as a sub-issue
- **THEN** subsequent publication links those observations to that same task while preserving its assignee, priority, discussion and acceptance criteria

#### Scenario: A human closes work while observations continue

- **GIVEN** a promoted task is closed with a recorded disposition
- **WHEN** its finding persists or later recurs
- **THEN** the digest preserves the decision and requests renewed triage only for a material change, without reopening the task or creating a replacement automatically

### Requirement: Digest publication preserves discussion and limits comments

The digest SHALL keep current evidence in automation-owned description sections and preserve human
content elsewhere. Comments SHALL summarize meaningful changes rather than each observation. Only
verified automation-owned summaries incorporated into a published replacement SHALL be minimized as
outdated; human discussion and decision comments SHALL remain untouched.

#### Scenario: Only dates and persistence counters advance

- **GIVEN** no new finding, changed outcome, recovery or review decision is needed
- **WHEN** the publisher refreshes the digest
- **THEN** it updates observation metadata without posting a new comment

#### Scenario: A summary is replaced

- **GIVEN** an older automation-owned summary is fully incorporated into a newer verified summary
- **WHEN** comment cleanup runs
- **THEN** it can minimize that old summary without deleting it or minimizing human discussion, retained decisions or the current summary

#### Scenario: Publication is retried or interrupted

- **GIVEN** a previous attempt published a summary but its receipt write failed
- **WHEN** the same run is retried
- **THEN** it recognizes the existing publication and avoids a duplicate comment, and it never minimizes an old summary before a replacement is verified

### Requirement: Digest retirement preserves open work and decisions

The current digest SHALL support reviewed retirement with a linked successor. Rollover SHALL carry
unresolved observations, acknowledgements and task references without recreating tasks or treating
supersession as recovery. It SHALL preserve the previous discussion and be recoverable after partial
failure. A report's age alone SHALL NOT silently discard pending work.

#### Scenario: An overloaded digest is retired

- **GIVEN** maintainer approval to rotate the current digest with unresolved findings and open sub-issues
- **WHEN** retirement completes
- **THEN** the successor includes current state and open-task links, both reports link to each other, and the predecessor closes explicitly as superseded without changing child-task states or identities

#### Scenario: Rotation is interrupted

- **GIVEN** the successor exists but one handoff step failed
- **WHEN** rotation is retried
- **THEN** it resumes the same handoff without creating another successor, losing decisions or leaving normal publication to update two active reports

### Requirement: Repository management uses one permission-gated Project

One Guide-wide Project SHALL organize issues and PRs with concise status, area and priority views,
including maintenance hierarchy. Project implementation and setup SHALL wait for confirmed organization
permissions. Native automation SHALL be preferred where sufficient; later Project access failure SHALL
leave observation, digest publication and maintainer triage usable with an explicit synchronization warning.

#### Scenario: Organization permission remains pending

- **GIVEN** Project plans exist but organization permissions have not been confirmed
- **WHEN** implementation scope is selected
- **THEN** Project code, configuration, setup and backlog import remain unimplemented and unchecked, and a repository Projects-enabled flag alone does not discharge the gate

#### Scenario: The Project becomes available

- **GIVEN** confirmed organization permissions and an approved Project setup
- **WHEN** the Guide backlog is onboarded
- **THEN** existing issues and PRs are imported without duplication or changing their titles, labels, assignees, states or scopes, and raw monitoring observations do not become individual Project cards

#### Scenario: Project access fails after activation

- **GIVEN** a previously activated Project becomes unavailable
- **WHEN** scheduled monitoring publishes current evidence
- **THEN** digest and triage operations remain usable, the Project synchronization failure stays visible, and a later retry reconciles missing entries without duplicate tasks

### Requirement: Every CI product has an actionable human handoff

Every CI product SHALL provide or link a human handoff stating its outcome, significance, affected scope and revision, eligible next actor, exact next action, prerequisites, fallback and completion evidence. Machine artifacts SHALL have a discoverable human entrypoint. Completed work requiring no action SHALL say so; skipped, blocked, partial and failed outcomes SHALL remain distinct.

#### Scenario: A contributor receives a failed check summary
- **WHEN** CI reports a failed check to a contributor unfamiliar with its implementation
- **THEN** the handoff identifies the affected item, gives an executable reproduction or repair step with prerequisites, and explains what evidence confirms completion

#### Scenario: A raw artifact contains the detailed findings
- **WHEN** CI publishes machine data or bounded details outside the main summary
- **THEN** its human entrypoint explains the result and next step, links the attributable evidence and discloses omitted scope

#### Scenario: CI did not complete its required work
- **WHEN** a producer is blocked or its evidence is partial or unavailable
- **THEN** the fallback handoff states what remains unverified, who can retry or investigate, and the next step without claiming success

#### Scenario: A release product is ready for human review
- **WHEN** CI prepares a release PR, deployment, image or draft release
- **THEN** its handoff names the exact revision or artifact, remaining review and separately authorized continuation, and evidence needed to finish without implying publication approval

### Requirement: Repair suggestions explain eligibility and completion

A CI repair suggestion SHALL distinguish the prepared draft from an applied change, show all related required edits and deferred inputs, and give the exact supported application and verification routes. An unavailable privileged route SHALL identify its prerequisite and a local or manual alternative. It SHALL NOT imply an unregistered action, guessed person or link-only patch completes the repair.

#### Scenario: A maintainer can use the duplicate command
- **WHEN** a safe duplicate repair is offered for a same-repository PR
- **THEN** the summary shows the link, provenance draft and registration intent, explains the current-write-access and reviewed-person requirements for `/fix-duplicates`, and states how to inspect its commit and rerun checks

#### Scenario: The PR is a fork or the caller is unknown
- **WHEN** the privileged repair route is unavailable because of PR origin, permissions, missing person mapping or App configuration
- **THEN** the handoff explains the limitation and an explicit local or manual completion route, including how to resolve the missing reviewed identity without inventing one

#### Scenario: The head advanced
- **WHEN** a repair draft or requested application no longer matches the PR head
- **THEN** no stale repair is published as current and the refusal or run summary explains how to obtain a fresh result

### Requirement: CI product handoff coverage is enforced

The repository SHALL maintain one CI product-to-handoff inventory covering its workflows, human entrypoints, producer/consumer boundaries and verification owners. Local and PR checks SHALL reject uncovered products and missing required handoff fields. Rendered-output tests SHALL prove actionable failure and completion paths; declarations alone SHALL NOT establish that the handoff works.

#### Scenario: A workflow publishes an uncatalogued product
- **WHEN** a workflow adds an artifact, proposal, report or publication output without a mapped human handoff
- **THEN** the common check fails and identifies the product and the required inventory or handoff update

#### Scenario: A renderer loses the next step
- **WHEN** a planted regression removes an action, prerequisite fallback or completion instruction from a representative rendered output
- **THEN** the relevant contract test fails even if the inventory still declares that field present

#### Scenario: An internal workflow produces no standalone user product
- **WHEN** a setup workflow or reusable internal stage is catalogued
- **THEN** it explicitly maps to its consuming human entrypoint or states that it produces no standalone product, with a checked reason rather than a silent exclusion

### Requirement: The CI catalogue matches effective workflow behavior

The CI policy SHALL catalogue every workflow's triggers, purpose, effective token and App permissions, write effects, artifacts, retention, concurrency and generated ownership. It SHALL document exact local reproduction and distinguish the required job context from the workflow name. Drift checks SHALL reject missing workflows and mismatched structured facts while release procedures retain their existing owner.

#### Scenario: A workflow or effective permission changes
- **WHEN** a workflow is added or its trigger, permission, artifact or concurrency policy changes without the matching catalogue update
- **THEN** the offline drift check fails with the affected workflow and correction route, including generated setup workflows

### Requirement: Incomplete CI evidence retains known failure diagnostics

When lane evidence is absent, unreadable or invalid, collection SHALL retain attributable known check failures alongside the evidence-integrity diagnostics and preserved logs. It SHALL identify incomplete coverage, remain nonpassing and provide a concrete retry or investigation handoff. Rejected identity or coverage data SHALL NOT become accepted evidence merely to improve diagnostics.

#### Scenario: A known check fails and another lane is absent
- **WHEN** the CPU content check fails and a required browser lane is missing
- **THEN** the summary reports both the content failure and missing lane, links retained details and never claims complete execution

### Requirement: Dependency caches accelerate installation without becoming verification evidence

Dependency caching SHALL use dependency inputs and compatible platform/runtime identity, retain cold-install fallback and disclose hit/miss/setup timing. Cache contents SHALL NOT replace current source/build checks, store credentials or cross the existing PR-to-privileged trust boundary. Restored test outcomes or generated sites SHALL NOT substitute for required current verification.

#### Scenario: A cache is missing or incompatible
- **WHEN** the lockfile, relevant requirements, runtime or platform changes, or restoration fails
- **THEN** installation uses the compatible cache or cold path and the same required checks still run with truthful timing

### Requirement: Execution tuning preserves complete attributable coverage

PR and deployment verification SHALL use one authoritative check/case inventory and configurable execution budgets. Performance acceptance SHALL compare a fixed revision and build context with equal coverage, separating setup, queueing, active work, approval wait and summed runner time. Changes to partitions, workers or case granularity SHALL retain every required case, failure artifact and validator profile.

#### Scenario: A faster deployment partition is proposed
- **WHEN** a candidate completes sooner than the baseline
- **THEN** its receipt reports cold/warm cache state, environment, budgets, coverage and runner time, retaining initial failures and refusing a speed claim derived from skipped work or unlike build contexts

### Requirement: Workflow concurrency distinguishes supersession from explicit requests

Concurrency policy SHALL distinguish replaceable current-result work from accepted explicit operations and shared mutable resources. Superseded checks/previews SHALL identify their successor; accepted maintainer operations SHALL complete, refuse or explicitly supersede without silently losing pending intent. Queue capacity, resource scope and recovery SHALL be documented; serialization SHALL NOT imply dispatch-order guarantees.

#### Scenario: Three explicit requests overlap
- **WHEN** one operation is active and two more valid maintainer requests arrive for the same resource
- **THEN** each accepted request retains an inspectable outcome or explicit supersession, including queue overflow or changed prerequisites

#### Scenario: Different PRs receive new commits
- **WHEN** a newer source head supersedes a run on one PR
- **THEN** it cancels obsolete work for that PR while independent PR verification remains eligible to execute

### Requirement: Preparation and publication have separate concurrency boundaries

Cancellable artifact preparation SHALL be separated from serialized publication to a shared destination. Before publishing combined Pages output or moving image aliases, trusted code SHALL verify current eligible source/channel identity and refuse stale promotion. Approval waits SHALL be reported separately and SHALL NOT unnecessarily serialize independent preparation. Release artifacts SHALL retain immutable identity.

#### Scenario: An older prepared deployment waits for approval
- **WHEN** newer eligible production or preview state exists before the older output publishes
- **THEN** publication reconciles current eligible artifacts or refuses the stale promotion, without reverting either channel or treating the approval wait as check execution

### Requirement: Automated branch updates preserve concurrent human work

An automated update to an existing branch SHALL enforce the expected reviewed head atomically at the write, preserve intervening human commits and report a concrete reconciliation route on conflict. Workflow serialization or a preliminary human-edit check alone SHALL NOT establish exclusive ownership. Retries SHALL be idempotent and never silently force away concurrent work.

#### Scenario: A person pushes after the publisher checks branch ownership
- **WHEN** a refresh publisher prepares a replacement and the branch advances before its update
- **THEN** the update is rejected, the human head remains intact and the handoff identifies the conflicting branch and review/retry route

### Requirement: Contribution governance is proportionate and checked

Contribution policy SHALL distinguish changes to behavior/contracts/governance from content instances, wording and behavior-neutral refreshes under existing contracts. Required planning references and explicit non-contract dispositions SHALL be checked locally and in PRs, with human review owning semantic classification. Ordinary content edits SHALL retain bilingual/source/paradata checks without mandatory per-edit OpenSpec churn.

#### Scenario: A contributor adds advice under the established model
- **WHEN** the edit preserves behavior, assessment meaning and the stored content contract
- **THEN** the contributor can declare the existing-contract route, supply normal sources/paradata and pass without inventing a capability requirement for that advice

#### Scenario: A CI or assessment contract changes
- **WHEN** the PR declares a triggering contract change
- **THEN** its complete scoped planning artifacts are required before apply and the gate reports missing planning rather than treating a green content check as approval

### Requirement: Guide usage filenames follow their delivered date convention

Guide-owned usage checks SHALL require a valid date and change/topic in each usage filename, consistent with the entry's initial date and the delivered field owners. Rolling later sessions SHALL retain the original filename date. Violations SHALL name the file and exact rename/remediation, without changing delivered rules or conflating agent usage with content provenance.

#### Scenario: A new usage entry has no filename date
- **WHEN** local or PR governance validation inspects the entry
- **THEN** it fails with the required dated filename form while allowing later dated sessions in the same rolling entry

### Requirement: Production publishes real crawler discovery files

The site build SHALL emit valid production robots and sitemap files from the configured base URL. The sitemap SHALL contain only explicitly selected real production documents with absolute fragment-free addresses. Assembly SHALL preserve production copies byte-identically, exclude preview documents from the sitemap and retain preview noindex. Tests SHALL validate the actual generated files, including base-URL overrides.

#### Scenario: Production and preview are assembled
- **WHEN** the real built production artifact is combined with a separately built preview
- **THEN** crawler files exist, use the configured production origin/path, retain their production bytes and advertise no preview or hash-route document
