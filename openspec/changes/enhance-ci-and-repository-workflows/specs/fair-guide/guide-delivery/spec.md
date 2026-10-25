# Spec Delta

## MODIFIED Requirements

### Requirement: Workflows are hardened

CI workflows for pull requests SHALL use the `pull_request` trigger, and the merge queue's `merge_group` trigger,
only, SHALL run with read-only repository permissions, SHALL pin third-party actions by commit SHA, and SHALL use
no secrets. Dependency and action updates SHALL be proposed automatically.

#### Scenario: Pull request from a fork

- **GIVEN** a pull request from a fork
- **WHEN** its checks run
- **THEN** they have read-only access and no secrets are available

#### Scenario: A merge group is checked

- **GIVEN** an approved pull request added to the merge queue
- **WHEN** the queue checks the merged result
- **THEN** the checks run with read-only access, no secrets and the same pinned actions as pull-request checks

### Requirement: Scheduled jobs never commit directly

Scheduled jobs SHALL deliver snapshot refreshes as pull requests and report link, status, live-service and
test-health observations in one maintenance digest. They SHALL watch the EOSC CZ pages the guide depends on (outputs,
service catalogue, training, Open Science III FAQ, minizáměry calls, acknowledgement and data steward pages) and list
added or updated items in the digest, ignoring navigation and pagination. They SHALL NOT commit to the default
branch or open work issues by themselves.

#### Scenario: Broken external link found

- **GIVEN** the weekly link check finds a persistently failing external link
- **WHEN** it completes
- **THEN** the digest lists the link, where it is used, the observed response and its persistence, and no separate issue is opened

#### Scenario: New EOSC CZ output

- **GIVEN** the EOSC CZ outputs page lists a document that was not there at the previous run
- **WHEN** the watch job runs
- **THEN** the digest lists the document with its address or anchor and its publication date when the page provides one, without inventing a date

#### Scenario: Pagination changes on a watched page

- **GIVEN** the training page adds a next-page link without adding a relevant item
- **WHEN** monitoring compares the page with its baseline
- **THEN** the navigation change creates no digest entry, comment or issue

### Requirement: Health and source-watch reports remain actionable

Health reporting SHALL separate content integrity, snapshot age, source availability and test verdicts.
Published observations SHALL have meaningful dashboard and API consumers for their dates, revision, scope and
status. Persistent failures and relevant source changes SHALL appear in the maintenance digest by stable keys
without duplicates or transient-failure floods. A service failure SHALL NOT become a failed FAIR requirement. Live
monitoring SHALL remain separate from mandatory deterministic PR checks.

#### Scenario: A test returns an indeterminate verdict

- **GIVEN** a completed live test with an indeterminate native result
- **WHEN** health is summarized
- **THEN** it is distinguishable from transport failure, a negative criterion result and a positive answer suggestion

#### Scenario: The runner receives an inconclusive response

- **GIVEN** a link request returns HTTP 403, HTTP 429 or a timeout
- **WHEN** the digest is rendered
- **THEN** it reports access denied, rate limited or temporarily unavailable without stating that the page is gone or that bot protection is confirmed

#### Scenario: A failure concerns imported content

- **GIVEN** the failing address comes from a reviewed upstream snapshot
- **WHEN** the finding is shown
- **THEN** it names the affected record and its source and points to the upstream or refresh correction route rather than to an edit of the snapshot

### Requirement: Scheduled dependency updates group patch versions

Dependabot SHALL group patch- and minor-version updates for all dependencies within each configured ecosystem:
GitHub Actions, npm, pip and Docker. Major updates SHALL remain individual PRs. Grouping SHALL preserve the
configured directories, weekly schedules, the limit of 30 open version PRs and the existing security-update policy.

#### Scenario: Several patch updates are available

- **GIVEN** several dependencies in one configured ecosystem have patch- or minor-version updates
- **WHEN** Dependabot proposes scheduled version updates
- **THEN** those updates are eligible for one grouped PR for that ecosystem regardless of dependency name

#### Scenario: Minor and major versions are available

- **GIVEN** patch, minor and major updates are available for dependencies in a configured ecosystem
- **WHEN** Dependabot applies the grouping policy
- **THEN** patch and minor versions enter the group, and the major update stays outside it and remains eligible for its own PR

#### Scenario: Existing update settings are retained

- **GIVEN** the four configured ecosystems, their current directories, weekly schedules and limit of 30 open version PRs
- **WHEN** grouping is configured
- **THEN** each ecosystem retains those settings and the existing security-update policy

### Requirement: Aggregate checks report every failure with diagnostics

Required aggregate checks SHALL name every failed or partial check and include bounded diagnostics while preserving lane logs and details. Partial results SHALL fail even at native exit zero, locally as in CI, retaining their partial flag and original evidence. Required diagnostics SHALL precede optional suggestions; optional processing errors SHALL be reported without hiding diagnostics or changing the required-check outcome. The gate SHALL remain failing when required checks fail.

#### Scenario: Two checks fail in one lane

- **GIVEN** content and duplicates both fail in the CPU lane
- **WHEN** the collector reconciles the lane
- **THEN** the aggregate names both checks and includes their error text

#### Scenario: A lane fails before the collector publishes

- **GIVEN** a failed lane with logs and details
- **WHEN** the collector rejects the aggregate
- **THEN** the health artifact contains those logs and details

#### Scenario: A browser check leaves pending cases

- **GIVEN** a required browser result with exit code zero, partial coverage and pending or skipped cases
- **WHEN** the collector publishes the aggregate
- **THEN** the aggregate and check row are failed, its output is shown, and the partial evidence remains inspectable

#### Scenario: The local run meets a partial child

- **GIVEN** a local full run whose browser check exits zero with partial case coverage
- **WHEN** the local runner publishes its report and returns
- **THEN** that row and the run are failed, its output is shown, and the run exits non-zero

#### Scenario: A deliberate local subset completes

- **GIVEN** a local `--only` run whose selected checks all complete
- **WHEN** the run finishes
- **THEN** the unselected checks stay not run, the report remains partial, and the run exits zero

#### Scenario: Optional output cannot be written

- **GIVEN** reconciled check results and an unwritable optional suggestion destination
- **WHEN** optional publication fails
- **THEN** the required report and its original pass/fail outcome remain available and the optional error is reported

#### Scenario: A known failure accompanies missing lane evidence

- **GIVEN** the CPU lane reports a failed content check and a required browser lane report is missing or has the wrong identity
- **WHEN** the collector reconciles the lanes
- **THEN** the aggregate names the content failure and the missing or rejected lane, keeps their logs, never claims a complete run and admits no data from the rejected lane

#### Scenario: A newer push cancels a run

- **GIVEN** a run whose lanes a newer push cancels
- **WHEN** the run ends
- **THEN** the collector does not run, so no evidence failure is reported for lanes that never finished, and the required gate still reports no success for it

## ADDED Requirements

### Requirement: The unpublished changelog section is checked

`CHANGELOG.md` SHALL have exactly one top-level `[Unreleased]` section whose entries are meaningful when present.
Against the base revision, released sections SHALL stay byte-identical, except that a complete release transition
SHALL be accepted. Local and PR checks SHALL report the exact structural problem and SHALL NOT edit the changelog.

#### Scenario: The section is missing or duplicated

- **WHEN** `[Unreleased]` is absent or appears twice
- **THEN** the check fails and names the structural problem and its fix

#### Scenario: The section holds only placeholders

- **WHEN** `[Unreleased]` contains only empty category headings or placeholder text
- **THEN** the check reports the missing meaningful entry
- **AND** an intentionally empty section after a release passes

#### Scenario: Published history is changed

- **WHEN** a PR changes an existing released section relative to its base
- **THEN** the check refuses the historical edit and directs the correction to `[Unreleased]`
- **AND** previously accepted historical section formats pass without conversion

#### Scenario: A release consumes the unpublished entries

- **WHEN** release preparation moves the unpublished entries into a new dated section and resets `[Unreleased]`
- **THEN** the check accepts the transition without requiring another unpublished entry
- **AND** a transition that loses entries or changes earlier releases is rejected

### Requirement: Release preparation retains curated unpublished notes

Release preparation SHALL move the curated `[Unreleased]` body unchanged into the new dated section, followed by
the complete deduplicated PR and direct-commit lineage, and reset `[Unreleased]`. It SHALL refuse before writing
when the curated notes use a reserved lineage heading. Earlier released sections SHALL remain byte-identical.

#### Scenario: Curated notes and lineage are both available

- **WHEN** the maintainer prepares a release with curated notes and merged PRs or direct commits
- **THEN** the dated section contains the curated notes followed by the complete linked lineage
- **AND** PR titles do not replace the curated explanations

#### Scenario: There are no curated notes

- **WHEN** release preparation finds an empty `[Unreleased]` section and a nonempty release history
- **THEN** it keeps the existing PR-only, direct-only, mixed and first-release behaviour

#### Scenario: Curated notes use a reserved heading

- **WHEN** the curated notes contain a heading reserved for the generated lineage
- **THEN** preparation refuses before changing any file and names the conflicting heading

### Requirement: Release-note and planning hints are advisory

The trusted PR review comment SHALL state whether the PR adds an `[Unreleased]` line and SHALL add a planning hint
when behaviour, CI or governance paths change without a linked OpenSpec change. Hints SHALL be derived from the diff
and commits, SHALL NOT read PR body text as instructions and SHALL NOT fail checks. Dependency and source-refresh
PRs SHALL be shown as covered by the generated release lineage.

#### Scenario: A page change has no unpublished line

- **WHEN** a human PR changes reader-facing behaviour without an `[Unreleased]` line
- **THEN** the review comment says that its commit messages feed the release notes and that only a breaking change, a required step or a security fix needs a line, and the checks are unaffected

#### Scenario: A dependency update

- **WHEN** a Dependabot or source-refresh PR has no `[Unreleased]` entry
- **THEN** the review comment states that the generated release lineage covers it

#### Scenario: A workflow change without planning

- **WHEN** a PR changes workflow or script behaviour paths and neither adds nor references an OpenSpec change
- **THEN** the review comment names the touched paths and links the planning guidance, without failing the PR

### Requirement: Release bodies combine reviewed notes with the verification record

The release workflow SHALL draft each release body with a changelog link and one marked verification record. A
native helper SHALL compose the body from the publishable release-notes report and that record, keeping the record
byte for byte, SHALL show the composition first and SHALL write only that reviewed composition to an unpublished
draft.

#### Scenario: Reviewed notes are applied

- **GIVEN** a draft release with its verification record and a publishable release-notes report
- **WHEN** the maintainer reviews the composed body and applies it
- **THEN** the draft carries the notes without the report's title, followed by the unchanged verification record, and the helper confirms the stored body

#### Scenario: The inputs changed after review

- **WHEN** the notes or the release body differ from those of the reviewed composition
- **THEN** the helper writes nothing and asks for a new review

#### Scenario: An unsafe input

- **WHEN** the notes are the working companion, the body lacks a single marked record or the release is already published
- **THEN** the helper writes nothing and names the reason and the fix

### Requirement: Release notes come from durable history

Release notes and the changelog SHALL be drawn from commit messages, merged pull requests and issues, never from
pull-request descriptions alone. `[Unreleased]` SHALL hold a line only for a breaking change, a required step or a
security fix; the generated lineage covers every other change.

#### Scenario: A pull request description is edited after merge

- **WHEN** a merged pull request's description changes later
- **THEN** the changelog lineage and the source of the release notes stay the same, because they come from the squash commit, its kept commit messages and the issues

#### Scenario: An ordinary feature is merged

- **WHEN** a pull request adds a feature without breaking anything
- **THEN** it needs no `[Unreleased]` line, and the next release lists it through the generated lineage

### Requirement: New content under the existing model needs no OpenSpec change

Editing guidance SHALL treat a new content instance under the existing content model, such as an advice item,
question or resource, as content work with its usual sources, paradata and checks. It SHALL require an OpenSpec
change when the edit alters behaviour, assessment meaning, a stored format, CI or governance.

#### Scenario: A contributor adds advice

- **WHEN** a contributor adds an advice item that uses existing fields, lenses and levels
- **THEN** the guidance leads to the content edit, sources, paradata and checks without an OpenSpec change

#### Scenario: A contributor adds a content field

- **WHEN** a contributor needs a new field in the content model
- **THEN** the guidance leads to an OpenSpec change before implementation

### Requirement: Guide usage filenames carry their start date

Guide usage entries SHALL be named `usage-YYYY-MM-DD-<topic>.md` with a valid date equal to the entry's first `When`
date and SHALL carry the delivered canonical field labels. Later sessions of a rolling entry SHALL keep the
original filename. Violations SHALL name the file and the exact rename or missing label.

#### Scenario: A new entry has no date

- **WHEN** the offline checks find `usage-ci-workflows.md`
- **THEN** they fail and name the required `usage-YYYY-MM-DD-<topic>.md` form

#### Scenario: A rolling entry gains a later session

- **WHEN** an entry named for 2026-10-20 records a further session dated 2026-10-24
- **THEN** the check passes without a rename

#### Scenario: The filename date differs from the first session

- **WHEN** the filename date is not the first `When` date
- **THEN** the check fails and names the expected filename

### Requirement: Comment commands keep every accepted request

One trusted workflow SHALL read issue and PR comments, ignore non-commands before taking any concurrency slot and
queue accepted commands per affected resource. Each accepted command SHALL get an immediate acknowledgement and a
final outcome naming its run, result and next step, including waiting, refusal and queue overflow. Existing
command syntax and trust guards SHALL remain.

#### Scenario: An unrelated comment arrives while a command waits

- **GIVEN** a `/refresh re3data` command waiting behind a running refresh of the same source
- **WHEN** someone posts an ordinary comment on another PR
- **THEN** the waiting command still runs and reports its outcome

#### Scenario: Two maintainers request the same repair

- **WHEN** two `/fix-duplicates` commands arrive for one PR
- **THEN** they run one after the other, and the second reports either its own result or that nothing remains to repair

#### Scenario: The queue is full

- **WHEN** a command arrives and its resource queue is at capacity
- **THEN** the caller receives a refusal with retry guidance instead of a silent cancellation

#### Scenario: An unauthorised caller

- **WHEN** an account without current write access sends a privileged command
- **THEN** it is refused as before and no App credential is used

### Requirement: Contributors can ask which commands apply

`/help` SHALL answer in one bot-maintained comment per thread with the commands available there, whether the
caller may use each and why not, using the same eligibility rules as the commands themselves. A command that
closely resembles a known one SHALL receive a suggestion. Help SHALL write nothing except its comment and reaction.

#### Scenario: A maintainer asks on a PR with a safe suggestion

- **WHEN** a maintainer sends `/help` on a same-repository PR whose latest checks offer a safe duplicate repair
- **THEN** the help comment lists `/fix-duplicates` as available and states what it will change

#### Scenario: A command is unavailable

- **WHEN** `/help` is sent on a fork PR or by an account without write access
- **THEN** the help comment explains why each privileged command is unavailable and gives the local alternative

#### Scenario: Help is asked again

- **WHEN** `/help` is sent a second time in the same thread
- **THEN** the existing help comment is updated rather than a new one posted

#### Scenario: A command is mistyped

- **WHEN** a comment starts with `/fixduplicates`
- **THEN** the reply suggests `/fix-duplicates` and runs nothing

### Requirement: Fast feedback precedes the complete check

Pull requests SHALL receive a separate quick result from cheap offline checks while the complete partitioned checks
run. The quick result SHALL NOT replace or satisfy the required `checks` context, and every failure it reports
SHALL also appear in the complete result.

#### Scenario: A content error is pushed

- **WHEN** a PR introduces a content-contract error
- **THEN** the quick result fails first and names the item, and the required `checks` still run and fail on the same error

### Requirement: Check partitions are balanced without losing coverage

Lane assignment, case splits and unit-test shards SHALL be derived from measured timings. The authoritative
inventory SHALL still require every check, case and validator profile exactly once, and a failure in any lane, case
or shard SHALL fail the result. A speed claim SHALL come from paired runs at a fixed commit with unchanged coverage.

#### Scenario: Lanes are rebalanced

- **WHEN** checks move between lanes or a long script is split into cases
- **THEN** the collector still rejects a missing or duplicated check or case

#### Scenario: One unit-test shard fails

- **WHEN** a single test fails in one of several shards
- **THEN** the unit check fails, names the test and keeps the merged timing report

#### Scenario: A faster candidate skips work

- **WHEN** a candidate finishes sooner because a case or validator profile did not run
- **THEN** it is rejected as incomplete and no speed gain is recorded

### Requirement: Dependency caches speed up setup without becoming evidence

Dependency caches SHALL be keyed on the lockfile or requirements and a compatible runtime, SHALL fall back to a
cold install and SHALL report hit or miss. Lanes SHALL install only the tools their checks use. Cache contents SHALL
NOT replace current checks, store credentials or pass from PR runs into trusted runs.

#### Scenario: The lockfile changes or the cache is missing

- **WHEN** `package-lock.json` or `requirements-dev.txt` changes, or a restore fails
- **THEN** the lane installs from a compatible cache or cold and runs the same checks

### Requirement: The merge queue verifies the merged result

Merges into the default branch SHALL pass through a merge queue that runs the required `checks` on the merged
result, while each PR's own checks remain required before it can be queued. Human and bot PRs SHALL use the same
queue. The trusted review comment SHALL ignore merge-group runs. An administrator's direct merge SHALL remain
possible and SHALL receive full deployment checks.

#### Scenario: Two approved PRs are queued

- **WHEN** two approved PRs with passing checks enter the queue
- **THEN** each merges only after its merged result passes, and a failing entry leaves the queue with the reason

#### Scenario: A Dependabot PR is approved

- **WHEN** a maintainer approves a grouped dependency PR and adds it to the queue
- **THEN** it follows the same verification and merge path as a human PR

#### Scenario: An administrator merges directly

- **WHEN** an administrator bypasses the queue
- **THEN** the default-branch deployment runs the full checks because no queue result exists for that content

#### Scenario: The queue's checks complete

- **WHEN** a merge-group check run completes
- **THEN** the review-comment publisher skips it and changes no PR comment

### Requirement: Staging deploys reuse verified results and need no approval

A default-branch deployment SHALL reuse a successful merge-queue check result only when the deployed tree and build
inputs equal the checked ones and the result's health snapshot validates; otherwise it SHALL run the partitioned
checks. Deployments that only update staging SHALL need no manual approval. The run summary SHALL name the reused run
or the reason for the fallback.

#### Scenario: The merged content was verified in the queue

- **WHEN** the default-branch commit has the same tree and build inputs as a passing merge-group run
- **THEN** deployment builds the site, imports that run's validated health snapshot, updates `/next/` without approval and names the reused run

#### Scenario: No matching verified result exists

- **WHEN** the tree differs, no passing merge-group run exists or its snapshot fails validation
- **THEN** deployment runs the complete partitioned checks before publishing and states why

#### Scenario: Build inventories name different producing runs

- **WHEN** the fresh build differs from the queue build only in the three health files that adoption replaces
- **THEN** those differences do not prevent reuse, every other built file must match and the imported health snapshot still passes identity and schema validation

#### Scenario: Adoption fails while the summary is written successfully

- **WHEN** adoption rejects a result and the summary pipeline succeeds
- **THEN** deployment selects the complete partitioned checks and uploads no unchecked staging site as reused

### Requirement: Production promotion requires explicit approval

A deployment that would change the production site SHALL wait for approval in a dedicated protected environment
before publication. A deployment that only updates staging SHALL keep the last approved production bytes. Tag
release SHALL explain when the current default-branch commit has no successful deployment yet and which run to wait for.

#### Scenario: A release tag is pushed

- **WHEN** the tag's deployment is ready to publish new production bytes
- **THEN** it waits for a maintainer's approval and publishes production only after it

#### Scenario: The default branch advances while a tag waits

- **WHEN** a merge lands while a production promotion awaits approval
- **THEN** its deployment updates staging and keeps the last approved production bytes

#### Scenario: A tag is approved after the default branch moved on

- **WHEN** a waiting production promotion is approved after a newer default-branch commit was deployed
- **THEN** it publishes the approved production with that commit's checked staging site, and neither channel moves back

#### Scenario: Tagging an undeployed commit

- **WHEN** Tag release runs before the current default-branch commit has a successful deployment
- **THEN** it creates no tag and names the deployment run to wait for

### Requirement: Pages publication is serialized and never regresses a channel

Preparation SHALL be cancellable and separate from one serialized publication step. Before publishing, trusted code
SHALL recheck the current eligible production and staging identities and refuse or supersede stale output.
Approval waits SHALL NOT block independent preparation. A superseded run SHALL name its successor.

#### Scenario: An older run reaches publication after a newer one

- **WHEN** a run's staging commit is older than the staging commit already published
- **THEN** it publishes nothing and its summary names the newer run

#### Scenario: Preparation is cancelled

- **WHEN** a newer default-branch push cancels an older run's preparation
- **THEN** the published site is unchanged and the cancelled run names its successor

### Requirement: Repository settings have a reviewed expected state

`.github/repository.toml` SHALL describe the expected rulesets, merge queue, environments, labels and Project
configuration. A read-only audit SHALL report each difference with its UI path and an equivalent command, SHALL
report unreadable settings as unavailable rather than as matching, and SHALL apply only additive label and
Project-item fixes on explicit request.

#### Scenario: A setting drifts

- **WHEN** a ruleset, environment, Project view or built-in automation differs from the reviewed file
- **THEN** the audit names the setting, the expected and actual values, the UI path and an equivalent command

#### Scenario: An approved target waits for its task

- **WHEN** an approved target is not applied yet and another setting of the same ruleset or environment drifts
- **THEN** the audit lists the target as pending with its task and precondition, and the drift's command keeps the target at its live value

#### Scenario: A setting cannot be read

- **WHEN** the token in use cannot read a configured setting
- **THEN** the audit reports that setting as unavailable and names the access needed

#### Scenario: Fixes are requested

- **WHEN** a maintainer runs the audit with its fix option
- **THEN** it creates missing declared labels and adds missing Project items, and never deletes a label or changes a field value

### Requirement: Automation identities hold only the permissions they use

Each workflow job SHALL request only the token permissions it uses, and the GitHub App's registered permissions
SHALL match a reviewed list. Project access SHALL be read-only and limited to the audit job. A denied or missing
permission SHALL produce a visible unavailable report naming the owner action, without failing unrelated publication.

#### Scenario: The audit token is denied

- **WHEN** the audit job cannot read Project #1
- **THEN** the digest reports the Project audit as unavailable with the owner's step, and the rest of the digest publishes

#### Scenario: A job requests an unlisted permission

- **WHEN** a workflow job requests a token permission that is not in the reviewed list for it
- **THEN** the offline workflow check fails and names the job and permission

### Requirement: Labels are managed as reviewed configuration

Area and automation labels SHALL be declared in the reviewed settings file. Label synchronization SHALL create or
update declared labels and SHALL NOT delete a label; undeclared labels SHALL be listed for a human decision.

#### Scenario: A declared label is missing

- **WHEN** the audit runs with its fix option and `area:sources` does not exist
- **THEN** the label is created with its declared colour and description

#### Scenario: A label is not declared

- **WHEN** the repository has a label absent from the reviewed file
- **THEN** the audit lists it for a decision and does not delete it

### Requirement: Pull requests receive area labels from their changed paths

The trusted review publisher SHALL add the declared area labels that match a PR's changed paths, read from the
GitHub API, and the source-refresh publisher SHALL label its PRs. Automation SHALL only add labels and SHALL NOT
remove a label or re-add one that a person removed.

#### Scenario: A PR touches content and workflows

- **WHEN** a human PR changes `content/` and `.github/workflows/`
- **THEN** it receives `area:content` and `area:delivery`

#### Scenario: A person removes an automatic label

- **WHEN** a maintainer removes an area label the publisher added
- **THEN** later runs do not add it again

#### Scenario: A source refresh PR is opened

- **WHEN** the refresh publisher opens or updates its PR
- **THEN** the PR carries `source-refresh` and the matching area label

### Requirement: Issue templates follow the planned-issue shape

Issue templates SHALL be generated in Czech and English for bug, feature and task from the delivered
`aiscr-plan-issue` shape declarations, carrying its metadata table, sections and type block in one language, and
SHALL set the matching native issue type. A check SHALL fail when the templates differ from the current declarations.

#### Scenario: A reporter opens a template

- **WHEN** a reporter chooses the Czech bug template
- **THEN** the body contains the declared Czech metadata table, `Problém`, `Reprodukce`, `Rozsah`, `Akceptační kritéria` and `Otevřené otázky`, and the issue type is Bug

#### Scenario: The delivered shape changes

- **WHEN** a delivery update changes a declared heading
- **THEN** the offline check fails and names the regeneration command

### Requirement: Project consistency is audited with actionable fixes

A weekly read-only audit SHALL report open issues or PRs missing from Project #1, issues without a type, a body type
that differs from the native type, Ready issues lacking an area label, Priority, Effort or the planned-issue shape,
triage older than 14 days, Urgent issues without progress, state mismatches and automation or view drift, each with
a link or fix step.

#### Scenario: An open issue is missing from the Project

- **WHEN** an open issue is not a Project item
- **THEN** the audit lists it with the fix command

#### Scenario: A Ready issue is incomplete

- **WHEN** an issue in Ready has no Effort or lacks a planned-issue section
- **THEN** the audit lists the missing parts and links the issue

#### Scenario: Urgent work has not started

- **WHEN** an Urgent issue has stayed in Needs triage or Ready for more than three days
- **THEN** the digest lists it

#### Scenario: A built-in automation is switched off

- **WHEN** a Project automation expected to be on is disabled
- **THEN** the audit names it and the affected items

### Requirement: One maintenance digest is rebuilt from current state

Monitoring SHALL publish one open digest issue whose automation-owned body is rebuilt from current state on each
run. It SHALL comment only when findings appear, change, recover or expire, and a retry SHALL NOT repeat a comment.
Closing the digest SHALL start a successor that links its predecessor and carries all unresolved state and open
tasks. Two open digests SHALL stop publication with a warning.

#### Scenario: Only dates and counters advance

- **WHEN** a run finds no new, changed, recovered or expired finding
- **THEN** the digest body is refreshed and no comment is posted

#### Scenario: A publication is retried

- **WHEN** a run that already commented is retried
- **THEN** it recognizes its comment and posts no duplicate

#### Scenario: A maintainer closes the digest

- **WHEN** the next run finds no open digest
- **THEN** it opens a successor with all unresolved findings, limitations and open tasks, links both issues and moves open tasks to the successor

#### Scenario: Two digests are open

- **WHEN** publication finds more than one open digest
- **THEN** it writes nothing and its summary names both issues and the fix

### Requirement: Maintainers promote findings into tasks

An observation SHALL become a task only when a person with write access creates it, for example from the digest's
prefilled task link. Automation SHALL attach such tasks to the digest, show them beside their findings and keep
closed dispositions. Recurrence SHALL ask for triage only on a material change and SHALL NOT reopen or recreate a task.

#### Scenario: A persistent failure is not triaged

- **WHEN** an unreviewed link fails across several runs
- **THEN** it stays in the digest's triage section and no task is created

#### Scenario: A maintainer tracks a finding

- **WHEN** a maintainer creates a task from the digest's link
- **THEN** the next run attaches it as a sub-issue of the digest and shows it beside the finding

#### Scenario: A closed task's finding continues

- **WHEN** a task was closed with a disposition and its finding persists unchanged
- **THEN** the digest shows the disposition and does not reopen the task
- **AND** a changed outcome returns the finding to triage

### Requirement: Monitoring coverage is bounded and explicit

Monitoring SHALL report eligible, attempted, deferred and invalid targets and distinguish unobserved targets from
successes. Selection SHALL give unchanged targets continuing coverage under the global request budget and a per-host
cap. Deferred targets SHALL keep their dated observation without new failures or recoveries.

#### Scenario: The inventory exceeds the request budget

- **GIVEN** 673 eligible URLs and a 600-request budget
- **WHEN** successive complete runs inspect the unchanged inventory
- **THEN** every URL is attempted within two runs and each report states its attempted and deferred counts

#### Scenario: A failing target is deferred

- **WHEN** a target with a persistent failure is outside this run's selection
- **THEN** the digest keeps its dated observation as unrefreshed without counting a new failure or a recovery

#### Scenario: One host throttles requests

- **WHEN** one host answers with rate limiting
- **THEN** its requests stop at the per-host cap and other hosts are still attempted

### Requirement: Reviewed monitoring limitations retain their basis

A monitoring limitation SHALL name an exact finding and outcome, reason, evidence, reviewer, review date and
review-by date. Acknowledged observations SHALL stay visible and rechecked. A changed outcome, changed target or
passed deadline SHALL return the finding to triage. Wildcards, missing evidence and conflicting entries SHALL fail
validation.

#### Scenario: A reviewed denial recurs

- **WHEN** a URL with a current limitation for HTTP 403 answers 403 again
- **THEN** the digest shows it as a known limitation with fresh evidence and asks for nothing

#### Scenario: The basis changes or expires

- **WHEN** that URL answers 404, its address changes or the review-by date passes
- **THEN** the finding returns to triage

#### Scenario: An entry is too broad

- **WHEN** a limitation uses a wildcard, lacks evidence or conflicts with another entry
- **THEN** offline validation fails and names the entry

#### Scenario: A new denial needs review

- **WHEN** an unreviewed URL answers 403
- **THEN** the digest offers a ready-to-paste limitation entry for the maintainer to complete

### Requirement: Watch state survives between runs or its loss is explicit

Monitoring state SHALL persist between runs in durable run storage with a format version. Valid previous state
SHALL migrate; missing, expired or malformed state SHALL produce an explicit reset notice and SHALL NOT claim
streaks or recoveries. Human decisions SHALL NOT live only in this state.

#### Scenario: The previous state is available

- **WHEN** the previous successful run's state is valid
- **THEN** persistence streaks continue from it

#### Scenario: The previous state is missing

- **WHEN** no readable previous state exists
- **THEN** the digest shows a state-reset notice and reports no streak or recovery

#### Scenario: The state has the previous format

- **WHEN** the previous state uses the earlier format version
- **THEN** it is migrated and its baselines and streaks are kept

### Requirement: Legacy health issues migrate into the digest

Before the digest replaces per-finding issues, an approved issue-by-issue migration SHALL map each open legacy health
issue to a digest entry, a retained task or a noise disposition, preserving its evidence and discussion. Absorbed
issues SHALL close with a link to the digest. The per-finding publisher SHALL NOT run in parallel with the digest.

#### Scenario: The migration is previewed

- **WHEN** the migration preview runs
- **THEN** it lists every open `guide-health` issue with its target disposition and writes nothing

#### Scenario: The approved migration is applied

- **WHEN** the approved migration runs
- **THEN** absorbed issues are closed with a link to the digest entry, retained tasks keep their number and state, and every original observation appears in the digest

### Requirement: The CI catalogue is generated from the workflow definitions

The CI documentation SHALL render each workflow's triggers, permissions, concurrency, artifacts and retention from
the workflow files, joined with a reviewed human entry for purpose, entry point, next actor and rerun route. A check
SHALL fail when a workflow, artifact or permission lacks its human entry or the rendered block is stale.

#### Scenario: A workflow is added without an entry

- **WHEN** a new workflow or uploaded artifact has no human entry
- **THEN** the offline check fails and names it

#### Scenario: A permission changes

- **WHEN** a workflow's permissions change and the catalogue block was not regenerated
- **THEN** the check fails and names the regeneration command

### Requirement: Every automated output ends with a next step

Every automated summary, comment, reply and report SHALL end with who acts next, the exact action, its
prerequisites or fallback and the evidence that shows completion. Successful outcomes SHALL say what review or checks
remain; partial, blocked and failed outcomes SHALL stay distinct and SHALL NOT claim success.

#### Scenario: A contributor receives a failed check

- **WHEN** a required check fails
- **THEN** the summary names the affected item, a local reproduction command and the evidence that confirms the fix

#### Scenario: A repair is applied

- **WHEN** `/fix-duplicates` commits a repair
- **THEN** the reply names the commit and the checks and review that remain

#### Scenario: A privileged route is unavailable

- **WHEN** a repair cannot run because of a fork, missing permission or unknown person
- **THEN** the reply gives the local or manual route and how to resolve the missing prerequisite

#### Scenario: A release product is ready

- **WHEN** CI prepares a release PR, deployment, image or draft release
- **THEN** its output names the exact revision or artifact and the separately authorized step that remains

#### Scenario: A renderer loses its next step

- **WHEN** a planted regression removes the action, fallback or completion evidence from a representative output
- **THEN** the renderer's test fails

### Requirement: Production publishes real crawler discovery files

The site build SHALL emit valid production `robots.txt` and `sitemap.xml` from the configured base URL. The sitemap
SHALL list only the Guide root and `api/index.html` with absolute, fragment-free addresses. Assembly SHALL preserve
the production files byte-identically, keep preview documents out of the sitemap and retain preview `noindex`.

#### Scenario: Production and preview are assembled

- **WHEN** the built production site is combined with a separately built preview
- **THEN** both files exist, use the configured production origin and path, keep their production bytes and advertise no preview or hash-route address

#### Scenario: The base URL is overridden

- **WHEN** the build runs with a different configured base URL
- **THEN** the robots and sitemap addresses follow that base

### Requirement: Release dispatches accept a leading v

Prepare release and Tag release SHALL accept the requested version with or without one leading `v` and
surrounding whitespace, and SHALL use the bare version in every file, branch, tag and message they produce. Any
other malformed value SHALL be refused with the accepted form shown.

#### Scenario: The maintainer types the tag form

- **GIVEN** the maintainer enters `v1.0.0-alpha.4`
- **WHEN** Prepare release runs
- **THEN** it prepares exactly the same files and branch as for `1.0.0-alpha.4`

#### Scenario: A malformed version

- **WHEN** a release dispatch receives `vv1.0.0` or `1.0`
- **THEN** it changes nothing and names the accepted form, for example `1.0.0-alpha.4` or `v1.0.0-alpha.4`

### Requirement: Tag release refuses an incomplete release changelog

Tag release SHALL create a tag only when the requested version's changelog section lists every merged pull request
and direct commit between the previous release tag and the commit to be tagged. Otherwise it SHALL create no tag,
name the missing changes and start release preparation for the same version.

#### Scenario: A change lands after the release PR merged

- **GIVEN** the release PR for `1.0.0-alpha.4` merged and one more PR merged afterwards
- **WHEN** the maintainer runs Tag release for `1.0.0-alpha.4`
- **THEN** no tag is created, and the summary names that PR, the completion it started and the next action: review and merge the completion PR, then run Tag release again

#### Scenario: The changelog is complete

- **WHEN** the requested section lists every change since the previous release tag
- **THEN** Tag release continues with its existing checks and creates the tag

### Requirement: Release preparation completes or replaces its own proposal

For an untagged version already on the default branch, Prepare release SHALL open a pull request that adds only
the missing changelog entries. It SHALL replace an open proposal of its own that nobody edited with one prepared
from the current default branch. An edited or closed proposal SHALL stay untouched, and the dispatch SHALL name
how to proceed.

#### Scenario: Completing a merged release

- **GIVEN** `1.0.0-alpha.4` metadata on the default branch, no tag, and one change missing from its changelog
- **WHEN** release preparation runs for that version
- **THEN** a pull request adds exactly that entry, leaving the version, dates and earlier entries unchanged

#### Scenario: Replacing an outdated unedited proposal

- **GIVEN** an open release pull request whose only commit is the automation's preparation, and a default branch that has moved on
- **WHEN** release preparation runs again for the same version
- **THEN** the proposal is prepared again from the current default branch and the pull request keeps its number

#### Scenario: A person edited the proposal

- **GIVEN** an open release pull request with a commit the preparation did not make
- **WHEN** release preparation runs again for the same version
- **THEN** it changes nothing and names the manual reconciliation route

### Requirement: A preview identical to the release says so

When the staging commit equals the commit of the published production release, every `/next/` page SHALL say that
the preview is identical to that release and link the production root, instead of announcing a next release. The
preview SHALL keep `noindex` and its own build identity.

#### Scenario: A release is tagged at the commit staging serves

- **GIVEN** `/next/` serves commit `161994f` and release `v1.0.0-alpha.3` is published from the same commit
- **WHEN** publication assembles both channels
- **THEN** each `/next/` page states in Czech and English that it is identical to `v1.0.0-alpha.3` and links the release, and production bytes stay unchanged

#### Scenario: The default branch moves on

- **WHEN** a later default-branch commit is published to staging
- **THEN** `/next/` again announces the next release

### Requirement: Each channel records when it is live

Publication SHALL record a successful `staging` deployment with the `/next/` address for the commit it published to
staging, and a `production` deployment with the root address for the release it published, each only after that
channel is live. A publication that publishes nothing SHALL record nothing. Release tags SHALL require a successful
`staging` deployment of their commit.

#### Scenario: A merge reaches staging

- **WHEN** publication makes a new default-branch commit live under `/next/`
- **THEN** the `staging` environment shows a successful deployment of that commit with the `/next/` address

#### Scenario: A release goes live

- **WHEN** publication makes an approved release live at the root
- **THEN** the `production` environment shows a successful deployment of that release with the root address, recorded after it went live

#### Scenario: Tagging a commit that never reached staging

- **WHEN** Tag release runs for a commit without a successful `staging` deployment
- **THEN** no tag is created and the summary names the run to wait for

### Requirement: Release notes are prepared in one invocation

A native release-notes skill SHALL, in one invocation, run the delivered release-notes workflow report-only from
the previous release tag, pre-releases included, to the requested tag, compose the body with the verification
record, ask once for approval of that body and apply it to the draft. Publishing the release SHALL remain a
separate maintainer act.

#### Scenario: The previous release is a pre-release

- **GIVEN** only pre-releases exist and `v1.0.0-alpha.3` is the previous tag
- **WHEN** the maintainer prepares the notes for `v1.0.0-alpha.4`
- **THEN** the notes cover exactly `v1.0.0-alpha.3..v1.0.0-alpha.4`

#### Scenario: The maintainer approves the body

- **WHEN** the composed body is approved
- **THEN** the draft carries it with the unchanged verification record, and the skill names publishing as the remaining step

#### Scenario: The maintainer declines

- **WHEN** the composed body is not approved
- **THEN** the draft release is unchanged

### Requirement: Scheduled maintenance results are ready on Monday morning

Scheduled source refresh, dependency updates and health watch SHALL run in one weekly order in which each completes
by Monday 06:00 UTC, which is 08:00 in Prague or earlier, even when its scheduled start is delayed by six hours. The
monthly Champion remeasurement SHALL run within the first weekly health watch of each month.

#### Scenario: Scheduled starts are delayed

- **GIVEN** each scheduled start is delayed by six hours and each job uses its full timeout
- **WHEN** the schedule is checked offline
- **THEN** every job still completes before Monday 06:00 UTC

#### Scenario: The first week of a month

- **WHEN** the weekly health watch runs within the first seven days of a month
- **THEN** it also remeasures the Champion tests, and no separate monthly schedule exists

### Requirement: Manual health-watch runs select their parts

A manual health-watch run SHALL let the maintainer choose the settings and Project audit, the watch, or both. A run
limited to the audit SHALL open, edit or close no issue and SHALL change no digest. Scheduled runs SHALL run both
parts.

#### Scenario: Checking the audit on demand

- **WHEN** the maintainer runs health watch manually with only the audit selected
- **THEN** the audit runs with its Project token and reports in the run summary, and no issue or digest changes

#### Scenario: A scheduled run

- **WHEN** the weekly schedule starts health watch
- **THEN** both the watch and the audit run

### Requirement: Human documentation is organised by audience and type

Human documentation SHALL give Guide readers, contributors and maintainers one landing page each, and SHALL keep
each document to one type: how-to guide, reference, explanation or tutorial. Each document SHALL declare its type,
and an offline check SHALL fail on a missing or unknown declaration. Agent instructions and delivered or generated
documents are outside this structure.

#### Scenario: A maintainer looks for a task

- **WHEN** a maintainer opens the maintainer landing page
- **THEN** it lists each maintainer task in one line with when it is needed and a link to its runbook

#### Scenario: A document lacks a type

- **WHEN** a human document has no type declaration or an unknown one
- **THEN** the offline check fails and names the document and the accepted types

### Requirement: Maintainer tasks have runbooks

Every recurring or handed-off maintainer task SHALL have a how-to runbook under `docs/runbooks/` that opens with who
acts, how long it takes and why, followed by numbered steps naming where to act, what to do, the visible evidence of
completion and the next action on failure. A branching flow SHALL include a diagram with an accessible title and
description.

#### Scenario: A step lacks its failure route

- **WHEN** a runbook step has no "If it fails" action
- **THEN** the offline check fails and names the runbook and the step

#### Scenario: Releasing from the runbook

- **GIVEN** the release runbook
- **WHEN** a maintainer follows it
- **THEN** each step names the exact place, the inputs and the visible evidence, and the Tag release refusal has a named next action

### Requirement: Documentation changes pass an independent review

A documentation change SHALL pass the structure and facts checks and a review by an agent that did not write it and
reads only the documentation. A change that moves text SHALL carry a section map accounting for every former
section. A hand-off SHALL NOT be complete while the runbook it relies on has unresolved findings.

#### Scenario: A section disappears in a reshape

- **WHEN** a former section has no entry in the section map
- **THEN** the map check fails and names the section

#### Scenario: A document names a missing script

- **WHEN** a document refers to a repository path, script or workflow that does not exist
- **THEN** the facts check fails and names the reference

#### Scenario: The independent reader had to guess

- **WHEN** the reviewing agent reports a step it could not perform from the text alone
- **THEN** the documentation is fixed before the dependent hand-off is ticked
