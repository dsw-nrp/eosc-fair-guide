# Design

## Context

See `proposal.md` for the motivation. The baseline is `main` at `f0c09f9`. PR #102 is part of it and already
delivers atomic refresh-branch updates, complete provenance for the remote `/fix-duplicates` command and
reporting of every failed check. This change builds on those and does not repeat them.

The live state was read on 23–24 October 2026:

| Evidence | Observation | Consequence |
| --- | --- | --- |
| PR run 40022072478 | 6 min 20 s. Build 20 s; CPU lane 18 s setup + 119 s checks; browser-a 45 s + 187 s; browser-b 60 s + 226 s (critical path); collector 41 s | Shorten the critical lane and setup, not the build |
| Same run, lane evidence | Two browser slots per lane. Case `en/320` waited 62 s for a slot. Long single scripts: accessibility 67 s, sources 65 s, model 63 s; final cases at 1280 px about 60 s | More balanced lanes and case splits |
| Same run, unit timings | 470 tests, 105 s, run one after another; slowest test 7.8 s | Parallel shards |
| CPU lane | Three `rocrate-validator` profiles of about 110 s each overlap the unit tests | Measure alternatives |
| Deployment | Staging runs the full `check_all.py` (568 s in run 39224056433). Every deployment, staging included, waits for a named reviewer. On 23 October three merges cancelled two pending deployments | Reuse verified results; approve production only |
| Main ruleset | Squash only, branches must be up to date, code-owner review, required `checks`; administrators may bypass | A merge queue replaces the up-to-date rule |
| Comment workflows | `fix-duplicates.yml` and `source-refresh.yml` both start on every comment; workflow-level concurrency is taken before the job filter, and a new pending run cancels the waiting one | One filter-first command workflow |
| Health watch | 24 open per-finding issues; state in `actions/cache`, which drops entries unused for seven days, on a weekly schedule; only the first 600 of 673 URLs are checked | Digest, durable state, fair selection |
| Project #1 | 70 items; Status Needs triage, Ready, In progress, Review, Done; seven views; native automations with auto-close off and auto-archive on. Priority and Effort are organization issue fields that exist only on typed issues; 2 of 61 open issues are typed; no `area:*` labels exist yet | Audit, labels, typed templates, backfill |
| App registration | `fair-guide-actions` lists `organization_projects: write` and several permissions no workflow requests; installation acceptance is not readable with the maintainer's current token | Reviewed permission list; read-only audit |
| Issue shape | The delivered `aiscr-plan-issue` engine declares the issue shape and exposes `section_status()` and `readiness()` | Templates and audit reuse it |

The first hosted release rehearsal, on 25 October 2026, added this evidence:

| Evidence | Observation | Consequence |
| --- | --- | --- |
| #114 queue run 40153182976, deployment 40153496770 | Staging adopted the queue result in 26 s with no fallback; Tag release 40154472734 tagged `161994f`; the production build took 10 min 16 s and was approved in run 40154498215; publication and the draft release followed | The repaired reuse path works |
| Queue run 40151368869 | `guide` was rejected: the release action ended at 01:28:10 UTC and the base `7b3fa74` was committed at 01:36:37; re-preparation (`d6bd75f`) also added `7b3fa74` to the changelog | Freshness from history (16); release currency at Tag release (17) |
| `/next/` after tagging | Footer `v1.0.0-alpha.2+15 · 161994f` while production serves `v1.0.0-alpha.3` from the same commit | Release notice (19) |
| Environments | `github-pages` publishes both channels; the `production` record appeared at approval (02:37:46), before the bytes went live (02:38:45) | Channel records (20) |
| Schedules | Source refresh started at 10:52 for 05:17, health watch at 09:36 for 04:41; Dependabot uses its defaults | Monday-morning schedule (22) |
| Documentation | `docs/deployment.md`: 2,714 words, no numbered steps; `docs/maintenance.md`: none either; sentences up to 60–132 words | Documentation in one wave (23) |

Two baseline defects remain and are reproduced as follows. These describe the current behaviour, not the result
of this change's repairs.

- **G2, curated notes lost:** call `release_versions.changelog()` with an `[Unreleased]` note and one eligible
  merged PR. The output keeps the PR link and drops the note. `CHANGELOG.md` currently holds one Added and eight
  Fixed curated bullets that the next preparation would drop.
- **G4, known failure hidden:** use the fixture from `PartitionTests.fixture` in `tests/test_check_ci.py`, mark
  the CPU `content` result failed and delete `browser-a/lane.json`. `check_ci.collect()` returns 1 but the report
  contains only `aggregate`, because `reconcile()` raises on the missing lane after collecting the failure.

## Goals / Non-Goals

**Goals:**

- Simple operations stay simple: merge with one click, release with two dispatches and one approval, triage from
  one view, repair with one command.
- Machines check structure and consistency; people judge notability, semantics and priority.
- Every automated output says what happens next, and every setting has a reviewed expected state.
- Faster checks with exactly the same coverage.

**Non-Goals:**

- No bot writes to the Project and no bot administration rights.
- No PR-body parsing for policy decisions.
- No combined or skipped coverage to reach a time target, and no hard wall-clock gate.
- No new runtime dependency or service.

## Decisions

### 1. Waves and their order

The nine waves in the proposal map to the task groups: wave 1 to group 1, wave 2 to group 2, wave 3 to groups 3
and 4, wave 4 to group 5, wave 5 to group 6, wave 6 to group 7, wave 7 to group 8, wave 8 to group 9 and wave 9 to
group 10. Group 11 verifies the whole change. Correctness lands first because the next release would otherwise
lose notes. The settings audit (group 3) precedes the setting changes it verifies. Labels and templates precede
the digest because "Track as task" uses them. Group 8 may land before groups 6 and 7, because the next release uses
it; group 9 is independent; group 10 lands after groups 6–9, so the documentation describes their final behaviour
once.

Alternative rejected: one large PR. It would be too big to review and would delay the urgent correctness fixes.

### 2. Changelog from durable history; reviewed release bodies

`scripts/check_changelog.py` joins the offline inventory and the CPU lane. It checks one `[Unreleased]` section,
meaningful entries, unchanged released sections against the base and a complete release transition. It reads no
PR body text. `release_versions.py` reuses its parser: the `[Unreleased]` lines move unchanged into the new dated
section, followed by the generated "Merged pull requests" and "Direct commits" lists. Lines that use those
reserved headings are refused before any write.

`CHANGELOG.md` is permanent, so it stays mechanical. The generated lineage is the record. `[Unreleased]` holds a
single line only for a breaking change, a step people have to take or a security fix. Detail lives in commit
messages: they are durable, and squash merges keep every branch commit's message in the default branch (the
repository's `COMMIT_MESSAGES` squash setting). Pull-request descriptions are not a source, because review
workflows edit them and their shape varies.

The reader-facing account of a release belongs in its GitHub release body. The release workflow drafts the body
with a link to the release's changelog section and one marked verification record (commit, archive digest, image,
release status). At release time a maintainer runs the delivered `/aiscr-write-release-notes` in its report-only
mode. It reads merged PRs, commit messages and issue threads and groups them by `.github/release.yml`. The native
`scripts/release_body.py` then composes the body from the publishable report and the verification record, kept byte
for byte. It shows the result, and only `--apply` writes that reviewed composition to an unpublished draft. The
skill's own body update would replace the record, so it stays off; the skill itself is unchanged. Decision 21 joins
both steps in one native skill.

The trusted review comment shows an advisory line derived from the diff: "unpublished line added", "covered by the
generated lineage" for Dependabot and refresh PRs, or "commit messages feed the release notes; add a line only
for a breaking change, a required step or a security fix". `docs/changelog.md` documents this.

Alternatives rejected: a required note-or-reason gate read from the PR body. It reruns the full six-minute checks on
every body edit, needs bot exemptions and turns untrusted text into a policy input. Changelog fragment files were
also rejected; they add files without preventing the reproduced loss. Curated prose for every notable change was
tried and dropped: it duplicated the commit history and froze verbose text into every release. Release notes
built from PR descriptions were rejected because those descriptions are edited after merge.

### 3. Known failures survive incomplete evidence

`reconcile()` keeps the results of admitted lanes when a later lane is missing, unreadable or has the wrong
identity. The collector emits those known failures together with the evidence diagnostic and stays failed.
Rejected lanes contribute nothing, and optional suggestions stay unpublished as today.

### 4. Local duplicate repair matches the remote command

Local `--fix` writes the link, one provenance action and its identifier registration, then rechecks content and
duplicates with the existing atomic rollback. The responsible person comes from `--person`, or else from the single
reviewed person whose `github` or `commitNames` entry in `content/guide.toml` matches `git config user.name` or the
GitHub account. Unknown or ambiguous identities write nothing. The output states how the person was resolved, so a
wrong local Git identity is visible in the diff before commit. The provenance-writing code is shared with
`fix_duplicates.py`, so both routes produce the same records.

Alternative rejected: requiring `--person` always. It adds a step for every known contributor and gains nothing,
because the reviewed mapping already exists and the diff is reviewed.

### 5. One command workflow with `/help`

`commands.yml` is the only `issue_comment` workflow. A `parse` job runs default-branch code with no write
permission and no concurrency group, and it only starts for a comment that begins with `/`. It checks the syntax
against a registry (`/help`, `/fix-duplicates`, `/refresh <source>`). An `acknowledge` job checks the context and
the caller's current permission. Each command then runs in a job with job-level concurrency keyed to the resource
it changes and `queue: max`: `fix-duplicates-<pr>` per pull request, and one `source-refresh` group for every
refresh, because sources read each other's snapshots. GitHub allows up to 100 pending runs this way, and
`queue: max` cannot be combined with `cancel-in-progress`. `fix-duplicates.yml` becomes a called workflow, and
`source-refresh.yml` keeps its schedule and dispatch triggers and becomes callable too. Their trust guards do not change.

Accepted commands get an `eyes` reaction at once. They end with a `rocket` reaction, or with `confused` and a reply
naming the run, the result and the next step whenever nothing else explains the result; the handlers' own replies
also name their run. A command that must wait names the earlier run holding its resource, found through the run
title `Comment on #<n>`; a cancelled run, including a full queue, is answered with retry guidance.
`/help` maintains one marked comment per thread. It lists the applicable commands and the caller's eligibility from
the same eligibility functions the commands use, and offers "did you mean" for near-miss commands. Anyone may ask
for help; it only edits its own comment.

Alternatives rejected: one workflow per command with workflow-level groups (the current race) and a bot service
(no backend).

### 6. Faster checks with unchanged coverage

- **Quick feedback.** A `quick` job in `checks.yml` runs the cheap offline checks (content, duplicates, changelog,
  ruff, format, public-content, openspec, agent generation) next to the build. It is not required. Its failures
  also appear in the full `checks` result.
- **Measured partitions.** `scripts/ci_timings.py <run-id>` reads job and step timings and lane evidence (queue,
  setup, active time, slot waits). It suggests a lane assignment by longest-first packing. The assignment stays in
  its single committed owner and changes only through review. Expected outcome: three or four browser lanes of
  about 150 s each instead of two lanes of up to 226 s.
- **Case splits.** Browser scripts whose time excluding browser-slot waits exceeds about 45 s become named cases
  through the existing case mechanism, so slots fill evenly, and cases start longest first. The inventory still
  requires each case once. Case reports record a script's slot wait. Measured on 24 October 2026, accessibility,
  sources, model and citation took 3.7–13.9 s alone but 37–68 s in run 40022072478: their CI time was slot
  waiting, which separate lanes remove and splitting would not. No script currently qualifies.
- **Unit shards.** `profile_checks.py` runs deterministic shards in parallel processes, locally and in CI, and
  merges one timing report. Tests already use temporary fixtures. A shuffled-order run guards against hidden
  shared state.
- **Setup.** `setup-python` and `setup-node` use their pip and npm caches, keyed on `requirements-dev.txt` and
  `package-lock.json`. Browser lanes skip the Python validator stack when the lane runner needs only the standard
  library; the apply task verifies the import graph first. The collector drops installs it does not use.
- **Experiments kept only when measured.** One validator process for the three profiles, or keeping validators off
  the unit-shard cores. A Playwright browser cache, where restore plus system dependencies may cost as much as
  today's install. Outcome on 24 October 2026: the unit shards moved to a lane of their own, which took the CPU lane
  off the critical path. A single validator process and a browser cache were not adopted. The validators no longer
  set the elapsed time, and the browser download is 7.5 s of a 17.5 s install, a saving smaller than the reruns'
  own 7 s spread.
- **Acceptance.** Three reruns of a fixed PR commit before and after, reported by `ci_timings.py`: elapsed time,
  critical path, queue, setup and summed job time, with full case and validator coverage. Goals: full checks
  around 4–4.5 min and quick feedback around 1–1.5 min. Public-repository minutes are free; the real constraint is
  the organization's concurrent-job limit, which the receipt also reports.

Alternatives rejected: path-based skipping of browser lanes (it weakens the "every PR" checks). Caching built sites
or test results is deferred to the separately approved input-digest experiment.

### 7. Merge queue with PR checks kept

```mermaid
flowchart LR
  accTitle: Pull request to staging with a merge queue
  accDescr: PR checks run first; the queue re-checks the merged result; deployment reuses that result for an identical tree, otherwise runs full checks; staging needs no approval while production waits for approval.
  pr["PR checks: quick + full"] --> review["Code-owner review"]
  review --> queue["Merge queue: checks on merged result"]
  queue --> main["Squash onto main"]
  main --> reuse{"Same tree and build inputs as a passing queue run?"}
  reuse -- yes --> stage["Build site, import health, publish /next/"]
  reuse -- no --> full["Partitioned checks"] --> stage
  tag["Release tag"] --> approve["Production approval"] --> publish["Serialized Pages publication"]
  stage --> publish
```

The main ruleset gains a merge-queue rule: squash method, all entries green, up to three PRs per group, at most two
groups building, no minimum wait and a 30-minute check timeout. The up-to-date requirement is switched off because
the queue verifies the merged result. PR checks stay required before a PR can be queued, so contributors keep their
feedback, and Dependabot, refresh and human PRs follow the same path. `checks.yml` handles `merge_group`: it uses
the merge-group base, skips the quick job and the PR-only review-data steps and keeps read-only permissions.
Merge-group runs build the `preview` channel that staging deploys, so the bytes they verify are the staging bytes;
PR runs keep the local channel. `pr-summary.yml` ignores merge-group runs. Administrator bypass stays as the
documented break-glass route. Its commits simply do not match a queue result, so deployment runs the full checks.

The build, lane and collector jobs become one reusable workflow, called by PR, merge-group and
deployment-fallback checks, so the inventory and evidence rules are identical everywhere. A check run is named
after its job, so `checks.yml` keeps a top-level `checks` job that passes only when the reusable workflow passed;
the required context keeps its name.

### 8. Deployment: reuse, approval only for production, serialized publication

For a default-branch push, deployment builds the staging site in the `preview` channel, which takes seconds. It
then looks for a successful merge-group `checks` run of the same commit whose source files and build inputs equal
the fresh build's; the queue's tested commit becomes the default-branch commit. If one is found, it imports that
run's health snapshot after validating the identity fields and the health API schema, and names the run in the
summary. The build comparison excludes exactly the three files replaced by health publication (`api/health.json`,
`health/index.html`, `health/summary.md`), whose initial inventory names the producing run. Every other built file
must match. The adoption step preserves the Python exit status through its summary pipeline, so a rejected result
always selects full checks. Any unmatched or invalid result runs the reusable partitioned checks and states why.
The trust is the same as today: the code
that produced the reused result is the code being deployed, and a PR run never contributes to a deployment.

Approval moves from the `github-pages` environment to a new `production` environment with required reviewers. An
`approve-production` job runs only when a tag run built production bytes that no earlier run verified. A tag is
approved once its release assets are complete, its deployment run succeeded, or that run's production and approval
jobs succeeded, so staging never promotes an unapproved tag. Workflow concurrency is per ref: branch runs cancel
superseded preparation, tag runs are never cancelled by branch runs, and a cancelled run names its successor. Tag
runs prepare no staging site.

The deployment run only prepares. Assembly and Pages publication run in a separate workflow, `publish.yml`,
started by every successful deployment run (`workflow_run`), so cancelling preparation can never interrupt a Pages
deployment. Each run that follows a successful deployment is the critical section (the workflow-level group
`pages-publish`; any other run gets a group of its own, and a newer waiting publication replaces an older waiting one,
publishing at least as much) and resolves the identities to publish when it starts. It decides in a job without an
environment, and only a publication that deploys enters `github-pages`, so no deployment record names a commit that
was not published. Production is the newest approved tag, fetched from its release assets or from the run that
approved it. GitHub records the Pages deployment against the default-branch head when the publication started, and
the tag ruleset and Tag release read that record, so a publication deploys only that commit's staging site. After a
default-branch deployment, publication takes that run's own checked staging site while its commit is still the
head; otherwise it publishes nothing and names the run for the head. After a tag deployment, it takes the head's
checked staging site beside the new production, so a tag approved after the branch moved on is still promoted;
while the head's own deployment is still preparing, it publishes nothing and the head's publication includes the
release. Neither channel moves back, and publishing the same identities again changes nothing. `github-pages`
accepts only the default branch. Release drafting and the image follow a publication that deployed the release, and
Tag release checks for a successful `github-pages` deployment of the current default-branch commit, as the tag
ruleset does, and otherwise names the run to wait for. Decision 20 moves that requirement to the `staging` record.

Alternatives rejected:

- Keeping one approval for all deployments. It makes every merge a two-person, two-step operation without protecting
  anything that the code-owner review does not already protect.
- Publishing nothing whenever a run's staging commit is stale. A tag approved after the branch moved on would stay
  unpromoted until some later deployment.
- Publishing inside the deployment run. Cancelling a superseded run would then cancel a Pages deployment already in
  progress.
- Cancelling only the preparation jobs through job-level groups. These cancel in order of arrival rather than run
  age, so an older run's late job could cancel a newer run's.

### 9. Settings as a reviewed expected state

`.github/repository.toml` records the main and tag rulesets including the merge-queue parameters, the
`github-pages` and `production` environments, the labels and their path rules, the Project's fields, options,
views and built-in automations, and the App's expected registration permissions. `scripts/audit_repository.py`
reads the live state and prints, for each difference, the setting, the expected and actual values, the UI path and
an equivalent `gh api` command. Settings it cannot read are "unavailable", never "matching". `--fix` is limited to
creating or updating declared labels and adding missing Project items with the operator's own token. No bot holds
administration rights; people apply setting changes, and the next audit confirms them.

The same script runs locally, by manual dispatch and weekly. The weekly run feeds the digest's "Project and
settings" section. A capability table in `docs/maintenance.md` records which token can read which section.

Alternatives rejected: a settings-sync bot with administration permission (too much power) and prose-only
checklists (they drift silently).

### 10. Project, labels and intake

The Project's native automations remain its only writers. Area is a label, because Project views can filter by
labels but cannot group by them:

| Label | Covers |
| --- | --- |
| `area:content` | advice, questions, glossary, model texts |
| `area:sources` | snapshots, refresh, registry data, ledger sources |
| `area:interface` | UI, accessibility, language, print |
| `area:evaluation` | live checks, evaluators, self-check |
| `area:delivery` | CI, release, deployment, tooling, dependencies |
| `area:maintenance` | the health digest and the tasks it spawns |
| `source-refresh` | PRs opened by the refresh publisher |

The trusted review publisher lists the PR's files through the GitHub API and maps paths to area labels with the
rules from `repository.toml`, using a standard-library Python helper. It only adds labels. It does not re-add a
label that the timeline shows a person removed. The refresh publisher adds `source-refresh`.

Status meanings: **Needs triage** is set by the item-added automation (PRs also receive it; the Triage view shows
issues only). **Ready** means triaged. **In progress** is set when a PR is linked. **Review** is set by hand when
the linked PR is ready for review. **Done** is set by closing or merging, and auto-archive applies after 14 days.
PRs are followed in the "PR - authored" and "PR - automated" views regardless of Status.

**Definition of Ready:** an Issue Type (Bug, Feature or Task), at least one `area:*` label, Priority and Effort
(Low, Medium or High), and a body that the delivered `readiness()` accepts. Priority and Effort are organization
issue fields available only on typed issues, which is why the type comes first.

`scripts/generate_issue_templates.py` imports the delivered shape constants and writes Czech and English Bug,
Feature and Task Markdown templates. Each template has the metadata table, `Problém`/`Problem`, the type block,
`Rozsah`/`Scope`, `Akceptační kritéria`/`Acceptance criteria` and `Otevřené otázky`/`Open questions`, plus guidance
comments that repeat the engine's rules. It omits the workflow-owned marker, reporter region and disclosure, and
sets the native issue type in front matter. `config.yml` keeps blank issues and links Discussions and the docs.
`--check` joins the offline suite. Markdown templates were chosen over issue forms because forms render every field
as a `###` heading and cannot produce the metadata table.

The Project audit reports:

- open issues or PRs missing from the Project;
- issues without a type, or a body `Typ`/`Type` row that differs from the native type;
- Ready issues failing the definition above;
- Needs triage older than 14 days;
- Urgent issues in Needs triage or Ready for more than three days;
- closed items not Done, or open items in Done;
- drift in automations and views.

The digest is public and may list Urgent items (confirmed by the maintainer). It shows no other Project field
values. Anything else that could disclose Project-only content is asked about before it is added. The checks that
read the Project's own Status (Ready, triage age, state mismatches) therefore appear in the digest as counts, and
the Project's views show the items; missing items, types and Urgent work are linked.

The weekly audit job reads the repository with its `GITHUB_TOKEN` (`actions: read`, `issues: read`) and only
Project #1 with the App token, as the audit's token table recorded. If that token cannot see the issues behind the
Project's items, the items are reported unavailable rather than missing or in order. The repository's logs and
artifacts are public and the Project is not, so the job publishes only the redacted section; the full report, which
names Project-only values, stays with a maintainer's local run.

The backfill assigns the Issue Type and area label of every open issue from a reviewed mapping file kept with this
change. It is applied with the audit's dry run first, after which people triage in the Triage view. Because GitHub
creates an unknown label when one is added to an issue, the backfill adds labels only once the declared labels
exist.

A template-born issue is not Ready by itself: `readiness()` requires the workflow-owned marker, reporter context and
disclosure, which `/aiscr-plan-issue` adds when a maintainer shapes it. A filled template therefore lacks only the
reporter context in `section_status()`.

### 11. One digest rebuilt from state

```mermaid
flowchart LR
  accTitle: Monitoring digest and task promotion
  accDescr: The watch job produces state and a digest plan; the publisher rebuilds the single digest body, comments only on meaningful change, adopts maintainer-created tasks as sub-issues and starts a successor when the digest is closed.
  watch["Watch run: links, pages, statuses, candidates, audit"] --> state["Versioned state (run artifact)"]
  state --> digest["Digest body rebuilt from state"]
  digest --> comment{"New, changed, recovered or expired?"}
  comment -- yes --> post["One comment with run marker"]
  digest --> track["Track as task link"]
  track --> task["Maintainer creates task"]
  task --> adopt["Attached as sub-issue, shown beside finding"]
  closed["Maintainer closes digest"] --> successor["Next run opens successor and moves open tasks"]
```

`health-issues.cjs` is replaced by a digest publisher. It finds the single open issue with the `guide-health`
label and the digest marker that was created by the workflow identity. If none exists, it creates one; if there
are two, it writes nothing and warns. The body is entirely automation-owned and says so, while discussion happens
in comments. Its sections are: needs triage, tracked, known limitations, source updates to review, candidates to
review, stale statuses, coverage, and Project and settings. Overflow is collapsed into counts with an artifact
link, so the body stays within GitHub's limit. A comment is posted only when the set of new, changed, recovered or
expired findings is nonempty. It carries the run ID, so a retry finds it instead of repeating it. Pinning is best
effort with a visible warning. Rotation is the maintainer closing the digest: the next run opens a successor,
posts the forward link on the predecessor and moves open sub-issues. Each step can be rerun until it is complete.

A finding's "Track as task" link opens a new issue prefilled with the Task shape, the finding key marker and
`area:maintenance`. The publisher adopts an open issue that carries a known key and was created by an account
with write access, attaching it as a sub-issue of the digest with `GITHUB_TOKEN` and `issues: write`. The native
auto-add-sub-issues automation then places it in the Project. A closed task keeps its disposition. Only a changed
outcome returns its finding to triage.

### 12. Watch inputs, coverage and state

Outcomes are classified as broken (404/410), denied (401/403), rate limited (429) or unavailable (timeout, 5xx,
DNS), keeping the method, status and evidence. Selection is least recently attempted first under the global budget,
with a per-host cap and bounded `Retry-After` handling, and reports eligible, attempted, deferred and invalid
counts. State is a versioned JSON file uploaded as a run artifact with 90-day retention and downloaded from the
previous successful run. Version 1 state is migrated. Missing or malformed state produces a reset notice.

`.github/health-watch.toml` holds reviewed limitations: exact key, outcome, reason, evidence, reviewer (person ID),
review date and review-by date. These entries are validated offline. For new denials and rate limits, the digest
offers a ready-to-paste entry. `content/link-reviews.toml` stays the separate mechanism for prose references.
Watched-page extraction ignores pagination and navigation such as #101. Champion candidates stay listed until a
maintainer decides, without automatic adoption.

The legacy migration has two phases. First, a dry run maps every open `guide-health` issue (#59–#65, #85–#101) to
a digest entry, a retained task or a noise disposition, after refreshing each thread. Second, after approval of
that mapping and of the exact first digest body, one run publishes the digest, comments and closes the absorbed
issues as "not planned" with the digest link. The per-finding publisher is removed in the same PR, so the two
publishers never run in parallel.

### 13. Self-explaining CI

The workflow catalogue block in `docs/ci.md` is generated from the YAML: triggers, permissions at each level,
concurrency, uploaded artifacts and retention. A small reviewed TOML file adds purpose, human entry point, next
actor and rerun route per workflow and artifact. `--check` fails on a missing entry or a stale block; generated
Copilot setup is included. The page opens with a cheat sheet: merge, release, refresh a source, fix a duplicate,
handle the digest and rerun a check. It also documents commands, `/help`, local reproduction (`check_all.py`, the
`check_ci.py` build/lane/collect steps, `ci_timings.py`) and the required context name `checks` as distinct from
the workflow name. CONTRIBUTING, `docs/agent-tooling.md` and `docs/deployment.md` link to it and keep their own
procedures. Decision 23 makes the cheat sheet the maintainer landing page: one line per task, linking its runbook.

All renderers share a "Next / If blocked / Done when" block: Python for the check summary and collector, JavaScript
for the trusted publishers. Representative output tests fail when an element is removed. The PR template asks for a
planning link and reminds authors that commit messages feed the release notes, in plain words; nothing parses it.

A run that a newer push cancels must not report an evidence failure for lanes that never finished. The evidence
collector therefore runs unless the run was cancelled (it still collects after a failed lane), while the required
`checks` gate keeps `always()` and fails such a run: a skipped required check would count as passing, so a cancelled
merge group must never report one. The first hosted
cancellation, on 24 October 2026, showed the collector failing inside a cancelled deployment run.

### 14. Crawler files (#83)

The build writes `robots.txt` and `sitemap.xml` from the configured base URL, including `FAIR_GUIDE_BASE_URL`
overrides, with a standard XML writer. The sitemap lists the Guide root and `api/index.html`, with no fragments,
per-language duplicates or invented dates. `robots.txt` points to the absolute sitemap and disallows the preview
path. Assembly preserves the production files byte-for-byte, and preview copies never advertise preview
documents. Tests use the real build and assembled tree. DNS and canonical-address adoption stay with #15 and #32.

### 15. Permissions

The App's registration stays as it is: on 24 October 2026 the maintainer chose to keep its current permissions,
which already include `organization_projects: read` for the audit. `.github/repository.toml` records them as the
reviewed list, and the public App endpoint lets the audit detect drift from it. Every App token request names only
the permissions its job uses, so no job holds the whole registration. An offline workflow test compares each job's
requested permissions with the reviewed list and checks that the registration covers them.

### 16. Paradata freshness from history

Freshness compared a covering action's `endTime` with the comparison base's commit time. That rule dates from the
first commit, when every PR was up to date with its base. With the merge queue and "up to date" off, the base moves
under a waiting PR: any content PR fails in the queue once anything lands on `main` after its action ended, while
its PR checks stayed green. The only remedy was a later `endTime`, which makes published paradata less true.

Freshness now reads history instead of the clock. An item that changed since the comparison base is covered by an
action that is absent at the base, or whose `endTime` is later than the same action's `endTime` at the base. The
second clause keeps the rule that extending an action means updating its end time, without comparing it with
anyone else's commit. `scripts/contributors.py` already finds actions added since the base by identifier; the
content check reads the base's actions the same way. Local, PR and merge-queue runs apply one rule. In a merge group
with several entries, each entry's items are covered by that entry's own new action.

Alternatives rejected: documenting "merge nothing during a release" (a conduct rule, and it covers release PRs
only); comparing against the PR's own fork point in the queue (a third comparison context); re-dating actions
automatically (it falsifies the record).

### 17. Release currency at Tag release

The time rule also did useful work by accident: alpha.3's forced re-preparation added `7b3fa74` to its changelog,
which would otherwise have shipped without it. Decision 16 removes that accident, so currency gets its own check.
Tag release is the right place: it is the last point before bytes freeze, and it tags the current default-branch
head, so changes can land after the release PR merged as well as before. Tag release compares the requested
section's lineage with the merged PRs and direct commits from the previous release tag to the commit it would tag,
using release preparation's own collection. The release's own proposal branch (`release/<version>`) is left out,
because a release never lists its own preparation. On a gap it creates no tag, names the missing changes and calls
Prepare release for the same version as a reusable workflow, so the maintainer who ran Tag release stays the
recorded actor: a dispatch would need `actions: write`, which the App lacks, and a `GITHUB_TOKEN` dispatch would run
as `github-actions[bot]`, which preparation refuses. Both workflows hold the `release-preparation` concurrency group
at job level, because a caller and its called workflow holding the same workflow-level group deadlock. The
maintainer then receives a PR to approve, not a puzzle. The changelog check lets the newest section gain generated
lineage entries only while its version has no tag.

Prepare release gains two routes. For an untagged version already on the default branch, it opens a completion PR
that adds only the missing lineage entries, extending the release's provenance action where the release-file
policy requires it. For an open proposal of its own whose every commit is the App's verified preparation, it
prepares again from the current head and updates that branch, so the PR keeps its number; source refresh already
replaces App-authored branches this way. An edited or closed proposal is never touched, and the dispatch names
the manual route. Together with decision 16 this removes two gaps the rehearsal found: there was no maintainer
route after a queue rejection, and "merge nothing during a release" was an unenforced rule. A repair that lands
after the release PR, which the existing re-issue requirement lets Tag release include, is one such change:
completion lists it before the tag, so the head then passes every requested-release check.

Alternatives considered: generating the lineage into the release body at draft time would be complete by
construction, but it reverses the complete-changelog decision (decision 2). Checking currency in the merge queue
misses changes that land between the merge and the tag.

### 18. Version input

Both dispatches strip surrounding whitespace and one leading `v` before the shared acceptance
(`release-version.cjs`, `release_version.py` and their shared fixtures), so a maintainer can type the tag form.
Every later use sees the bare version.

### 19. `/next/` when it equals the release

Tag release always tags a commit that staging already serves, so after every release `/next/` names the previous
tag plus a count for the commit production now serves, until the next push. Assembly already writes the preview
notice into every `/next/` page. When publication's staging commit equals the production release commit, assembly
writes a bilingual notice that the preview is identical to that release, with a link to the root, instead of
"Preview of the next release". The build identity stays as built: rewriting it would patch generated output, and the
notice removes the contradiction. A redirect was rejected: it would break `/next/` deep links and API paths and
would need a script or meta refresh.

### 20. Channel records: staging and production

`github-pages` is not a staging environment: its single publication job deploys the whole tree, production root
included. `production` is the approval gate, and its record appears at approval, before the bytes are live. Neither
says "this channel is live at this address". Renaming `github-pages` would mislabel it, and GitHub recommends
keeping that name for Pages.

After a publication that deploys, `publish.yml` records a `staging` deployment of the staging commit with the
`/next/` address and, when it published a release, a `production` deployment of the release with the root address.
A publication that deploys nothing records nothing. `github-pages` stays the publishing mechanism. The approval job
keeps `production` as its gate; where GitHub lets a job use an environment without creating a deployment, the gate
creates none, so `production` lists only live releases. Tag release and the tag ruleset require a successful
`staging` deployment, which says what is meant: tag only what was staged. `repository.toml` declares `staging`, and
the ruleset changes only after a publication created the first `staging` record (task 8.7).

The first open fact is verified: since GitHub's March 2026 update, a job's `environment` accepts `deployment: false`,
which keeps required reviewers but creates no deployment, so the approval job uses it. The second, whether a tag
ruleset's required deployments accept deployments created through the API, is verified in task 8.7 before the
ruleset changes; until then the ruleset keeps `github-pages` and Tag release alone checks `staging`. `staging` keeps
the `main` branch policy of `github-pages`: without it, anyone holding `deployments: write`, including a workflow on a
pull-request branch, could create a successful record for an unreviewed commit, and the ruleset would then admit a
tag on it with only the production approval left in the way. Records therefore name the branch `main` and count
only when GitHub resolves them to the published commit; a record that resolves to a newer commit is left inactive.
Because the ruleset sees only that a successful record exists, Tag release also requires that a `publish.yml` run
on the default branch wrote it. Production records name the tag, which its `tag v*.*.*` policy admits.

### 21. One-invocation release notes

A native skill, `fair-guide-release-notes`, runs the whole route. It resolves the tag and the previous release tag,
including pre-releases, because the delivered workflow's default baseline skips them. It runs
`/aiscr-write-release-notes` report-only in English with those answers fixed, composes with `release_body.py`,
asks once for approval, applies and reads the body back. Publishing stays a separate click. The skill is
user-invoked only, because it writes to GitHub. It depends on the delivered skill allowing model invocation, which
its upstream maintainer changes; the delivered copy is not patched here. Until then the documented two-command route
stays. Release-notes reports remain git-ignored, so the release body is the durable record.

### 22. A predictable weekly schedule

The schedule works backwards from Monday 08:00 in Prague: every scheduled job completes by Monday 06:00 UTC even
with a six-hour start delay and its full timeout. Source refresh runs first, then Dependabot, with day, time and
`Europe/Prague` set for each ecosystem, then health watch, so the digest reflects the week. The monthly Champion
remeasurement runs inside the first weekly health watch of a month instead of on its own cron. An offline test
computes the bound from the workflow and Dependabot files.

Manual health-watch runs choose the audit, the watch or both. An audit-only run writes nothing to issues or the
digest, so either part can be tested on demand, and 5.8's evidence can come from such a run.

### 23. Documentation in one wave

The documentation mixes three readers in one text: the person doing a task, the reviewer checking guarantees and
the implementer. It follows Diátaxis instead. Guide readers (both READMEs), contributors (CONTRIBUTING) and
maintainers (`docs/ci.md`'s cheat sheet) each have one landing page. Each document has one type: how-to guide,
reference, explanation, or a tutorial once a real newcomer need appears. A document declares its type in an HTML
comment on its first line, which `scripts/check_docs.py` reads.

Maintainer tasks become runbooks under `docs/runbooks/`. A runbook opens with who acts, how long it takes and why,
in two sentences at most. Numbered steps then give **Where**, **Do**, **Done when** and **If it fails**, using the
same words as the automated outputs' "Next / If blocked / Done when" blocks (decision 13). A branching flow gets a
Mermaid diagram with `accTitle` and `accDescr`. The runbook owns the steps; reference and explanation link to it
and do not repeat them.

The reshape is one wave, not gradual. Diátaxis recommends small steps for human writers; an agent can rewrite the
whole set coherently, and the constraint becomes review. The review package:

- a section map, kept with this change, that gives every former section its new home or a removal reason, and a
  check that no former heading is unaccounted for;
- a facts check that every repository path, script, workflow and npm script a document names exists;
- the structure check above;
- an independent reader per audience: a fresh agent, not a fork of the writing session, that reads only the
  documents and their links, checks type fit and whether each step can be performed from the text alone, and
  samples moved facts against the map. It returns located findings or `NO_FINDINGS`, and the author fixes them.

A human review step was considered and deferred: real use will refine the documents. `AGENTS.md` and delivered or
generated surfaces are excluded; their owners govern them. The documentation rules join the native surface rule
(task 7.5), so later edits keep the shape.

### Issue dispositions (refreshed 24 October 2026)

| Issues | Disposition |
| --- | --- |
| #83 | Delivered by group 7 |
| #84 | Its CI page, workflow and artifact facts, drift check, generated-setup ownership, local reproduction and cross-links are delivered by groups 2 and 7. The code repairs are this change's own scope |
| #59–#65 | Migrated to the digest's candidates section; no candidate selection is approved here |
| #85–#99 | Migrated to digest findings; triaged after migration |
| #100 | Migrated as a source update to review |
| #101 | Closed as noise after the pagination fix, within the approved migration |
| #6 | Receives CI test and handoff evidence; stays open |
| #5–#33, #35–#38, #43, #80 | Unaffected; typed, labelled and triaged through the backfill. #14, #15, #25 and #32 stay external or separate decisions |
| PRs #39–#42, #70 | Unaffected; labelled and tracked in the Project |

## Risks / Trade-offs

- **Queue and PR checks double the runs per PR** → lanes become faster first (wave 2), and the queue builds at most
  two groups. Reuse of PR results inside the queue is part of the separately approved input-digest experiment.
- **The concurrent-job limit could queue runs** → `ci_timings.py` reports queue time, and the lane count is
  chosen from it.
- **Deployment reuse could import a forged snapshot** → only from merge-group runs with an identical tree and
  build inputs, with identity and schema validation. PR runs are never used. When in doubt, the full checks run.
- **A wrong setting could be applied** → each change is shown as the audit's expected-versus-actual diff before it
  is applied, then confirmed by a fresh audit. Each step has a recorded rollback.
- **Branch-run cancellation could leave a commit undeployed when a tag is requested** → Tag release names the run
  to wait for. The latest commit is always deployed by the latest run.
- **Issue-field values may not be readable with the App token** → those checks report "unavailable" and the
  rest of the audit still runs. The local audit with a maintainer token covers them.
- **The digest body could exceed limits** → bounded sections with counts and artifact links.
- **Removing the per-finding issues loses their notifications** → the digest comments on meaningful change, and
  people watch one issue instead of 24.
- **Local Git identity could be wrong** → the person is printed and visible in the diff; `--person` overrides it.
- **History-based freshness could accept an old action reused without new work** → an action counts only when it
  is new since the base or its `endTime` moved later.
- **Tag release's automatic re-preparation could surprise** → it only opens or updates a PR, never merges or tags,
  and its summary names the PR and the next action.
- **API-created deployment records might not satisfy the tag ruleset** → verified before the ruleset changes; until
  then the ruleset keeps `github-pages`.
- **A one-wave documentation reshape could drop or change a fact** → the section map, the facts check and the
  independent reader's sampling of moved facts.
- **The release-notes skill depends on an upstream change** → until it arrives, the documented two-command route
  stays.

## Migration Plan

1. Land groups 1 and 2 as normal PRs, with no settings changes.
2. Land the settings audit and record the live state (group 3). Land the merge-queue-ready workflows (group 4 code)
   while the old rules are still active; `merge_group` is unused until the queue is enabled.
3. After approval of the audit's exact expected-versus-actual diff, apply settings one at a time, rerunning the
   audit after each:
   - **Enable the merge queue.** Rollback: remove the rule.
   - **Switch off "up to date".** Rollback: switch it on.
   - **Create the `production` environment with reviewers and tag-only deployment.** Rollback: remove it and
     re-add the reviewer to `github-pages`.
   - **Remove the reviewer from `github-pages`.** Rollback: re-add it.

   A separately approved hosted rehearsal then merges one human PR and one grouped Dependabot PR and promotes one
   release.
4. Land labels, templates and the Project audit (group 5). After approval of the mapping, apply the backfill.
   The organization owner confirms the App installation and trims its registration.
5. Land the digest with its migration (group 6). Run the dry run, approve the payloads, publish and reread.
6. Land the CI documentation, handoffs, hints, usage check and crawler files (group 7).
7. Land the release flow repairs (group 8), possibly before groups 6 and 7. After a publication has created a
   successful `staging` record and decision 20's two facts are verified, apply the tag ruleset's required
   deployment change after approval of the audit diff. Rollback: restore `github-pages` as the required deployment.
8. Land the schedule (group 9). Rollback: restore the previous cron entries and Dependabot defaults.
9. Land the documentation wave (group 10) after its review package passes.
10. A separately approved final rehearsal follows the release runbook (task 11.3).

Rollback for code is a reviewed revert. The digest publisher can be disabled while its state artifacts and
human comments remain. Completed repairs, notes and published releases are never rewritten.

## Open Questions

These can be answered during apply without changing the specs or the task breakdown:

- Which API path and App permission read organization issue-field values (Priority, Effort)? Answered on
  24 October 2026: `GET /orgs/{org}/issue-fields` needs the organization's Issue Fields read permission, and one
  issue's values come from `GET /repos/{repo}/issues/{number}/issue-field-values` with Issues read. The maintainer
  token received an empty list, so the audit reports the fields as unavailable until an owner confirms them.
- Do Markdown issue templates apply their `type` front matter? If not, triage sets the type and the audit lists
  untyped issues.
- Can prefilled new-issue links preset labels for all reporters? Adoption relies only on the finding key, so
  either answer works.
- Can `GITHUB_TOKEN` read rulesets and environments? Answered on 24 October 2026: rulesets need only Metadata
  read, but their bypass actors appear only with write access to the ruleset, and environments need Actions read.
  `docs/maintenance.md` records the capability table.
- Do the validator and Playwright-cache experiments pay off? Answered on 24 October 2026: neither was adopted
  (see the experiments in decision 6).
- Can a job use the `production` environment as an approval gate without creating a deployment record? Answered on
  25 October 2026: yes, with `deployment: false` (GitHub's March 2026 update); required reviewers still apply.
- Do a tag ruleset's required deployments accept deployments created through the API? If not, the ruleset keeps
  `github-pages` and Tag release alone checks `staging`.
