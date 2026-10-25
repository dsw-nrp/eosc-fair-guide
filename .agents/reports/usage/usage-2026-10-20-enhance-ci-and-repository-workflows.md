# Enhanced CI and repository workflows

- **When:** 2026-10-20
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** exact backend model id not exposed by the runtime
- **What:** Prepared the initial plan for the `enhance-ci-and-repository-workflows` OpenSpec change.
- **Impacted:** The change's proposal, two capability deltas, design and tasks; this usage entry.
- **Close-out:** Planning artifacts complete and strictly valid; no implementation, push, issue write, Project
  setup or hosted dispatch.

## Claude Code session (re-plan after the PR #102 merge)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** `openspec-explore` (the maintainer confirmed the capture explicitly); delivered
  `aiscr-planning-core`, `aiscr-quality-first-execution`, `aiscr-usage-logging` and `aiscr-model-logging` rules;
  pinned `npx openspec` CLI; read-only `gh` API queries and GitHub documentation pages.
- **What:** Re-oriented the change on current `main` (`f0c09f9`, including PR #102) and removed the legacy of the
  consumed drafts. Rewrote the proposal, design, both delta specs and tasks around six waves: correctness,
  faster checks, merge queue and deployment approvals with a settings audit, Project and intake, the
  maintenance digest, and self-explaining CI with crawler files. Grounded them in measured run timings, the
  live rulesets, environments, Project #1 configuration, App registration and the delivered `aiscr-plan-issue`
  shape.
- **Impacted:** `openspec/changes/enhance-ci-and-repository-workflows/` (all five artifacts); this usage entry,
  trimmed of the consumed-draft history at the maintainer's request.
- **Corrections:** The maintainer required PR checks to stay before `main` with a merge queue, the Dependabot
  limit to stay at 30, and no security-update group (security updates are off on purpose). The maintainer chose
  labels for Area, Markdown issue templates consistent with `aiscr-plan-issue`, Low/Medium/High Effort, a manual
  Review status, and allowed Urgent items in the public digest. Performance work targets check duration, not
  only run frequency.
- **Verification:** strict OpenSpec validation of the change and of all items passes (6/6); public-content,
  agent-surface ownership, sibling-delivery and whitespace checks report no findings.
- **Close-out:** Planning only; 59 tasks unchecked. No code, workflow, setting, issue, Project or remote change was
  made, and nothing was committed or pushed. App installation acceptance of `organization_projects` remains
  unverified with the maintainer's token.

## Claude Code session (apply group 1: nothing gets lost)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** `openspec-apply-change` after the maintainer's explicit apply instruction; the delivered
  planning, quality-first and usage-logging rules; pinned `npx openspec` CLI.
- **What:** Implemented tasks 1.1–1.10:
  - the changelog check, with release preparation keeping curated notes (G2);
  - known failures kept beside missing or invalid lane evidence (G4);
  - complete local duplicate repair through the shared `duplicate_repairs.py`, with reviewed-person resolution;
  - one filter-first comment-command workflow with queued resources, visible outcomes and `/help`;
  - one budget owner for local and CI runners.

  Corrected the design wording to the implemented single refresh queue and the GitHub reactions used.
- **Impacted:**
  - New: `scripts/check_changelog.py`, `scripts/duplicate_repairs.py`, `.github/workflows/commands.yml`,
    `.github/scripts/commands.cjs`, `docs/changelog.md`.
  - Changed: `release_versions.py`, `check_ci.py`, `check_all.py`, `check_duplicates.py`, `fix_duplicates.py`,
    `check_groups.json`, `fix-duplicates.yml`, `source-refresh.yml`, `source-publisher.cjs`, `comment-summary.cjs`,
    CONTRIBUTING, `docs/design.md`, `docs/content-model.md`, `docs/deployment.md`, `CHANGELOG.md`.
  - Tests: new `tests/test_changelog.py` and `tests/page/check_commands.mjs`; changed `test_release_versions.py`,
    `test_check_ci.py`, `test_duplicate_review.py`, `test_scripts.py`, `test_workflows.py`, `test_check_runner.py`,
    `check_source_publisher.mjs`.
  - Planning: `design.md` and `tasks.md` of the change.
- **Verification:**
  - G2 and G4 were reproduced against the `HEAD` code (the note dropped; only the aggregate was reported) and are
    fixed in the working tree.
  - Strict OpenSpec validation passes.
  - The full `check_all.py` passed 30 of 31; `versions` refused a restated Guide version in `docs/changelog.md`.
    After that fix, the affected `versions`, `changelog`, `public-content` and `reuse` checks pass 4 of 4.
  - `git diff --check` reports nothing.
- **Close-out:** 10 of 59 tasks complete; group 2 onwards remain.
  - `commands.yml`, `queue: max` and the reusable-workflow calls run only from the default branch, so they are
    unverified until hosted use after merge.
  - The OpenSpec wrapper refresh to 1.14.3, already staged by someone else, was left untouched.
  - Nothing was committed or pushed.

## Claude Code session (apply group 2 and the release-notes follow-up)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** `openspec-apply-change` invoked by the maintainer for this change; the delivered planning,
  quality-first and usage-logging rules; the delivered `aiscr-write-release-notes` skill, read but not run; pinned
  `npx openspec` CLI; `gh` queries and artifact downloads; three approved reruns each of the baseline run
  40022072478 and the candidate run 40085436997; the approved push of draft PR #107, stacked on #103.
- **What:**
  - Group 2:
    - `scripts/ci_timings.py`, with a trimmed fixture of run 40022072478 and the three-rerun baseline in
      `docs/ci.md`.
    - Case reports record script-level browser-slot waits.
    - The non-required `quick` job.
    - Unit tests in measured, deterministic shards, each with a private report directory.
    - Four browser lanes from the timing suggestion, with longest-first final-candidate cases, and a unit-test
      lane of its own after candidate run 40084136770 showed the shards slowing the validators.
    - npm and pip caches keyed on the lockfiles; browser lanes skip the Python validators, and the collector drops
      its unused browser path.
  - Group 1 follow-up (tasks 1.11 and 1.12): `CHANGELOG.md` keeps the generated lineage plus single lines for
    breaking changes, required steps and security fixes, and detail lives in commit messages. Draft release bodies
    carry a changelog link and a marked verification record, and `scripts/release_body.py` composes reviewed
    `/aiscr-write-release-notes` reports with that record.
- **Impacted:**
  - New: `scripts/ci_timings.py`, `scripts/unit_shards.json`, `scripts/release_body.py`, `docs/ci.md`,
    `tests/test_ci_timings.py`, `tests/test_release_body.py`, `tests/fixtures/ci-timings/40022072478-1/`.
  - Changed: `scripts/check_ci.py`, `scripts/profile_checks.py`, `scripts/check_policy.json`,
    `.github/workflows/checks.yml`, `.github/scripts/release-artifact.cjs`, `.agents/guide/surfaces.toml`, `.gitignore`, `tests/page/browser.mjs`,
    `tests/page/check_final_candidate.mjs`, `tests/page/check_release.mjs`, CONTRIBUTING, `docs/design.md`,
    `docs/changelog.md`, `docs/deployment.md`, `CHANGELOG.md`.
  - Tests: `test_check_ci.py`, `test_check_runner.py`, `test_workflows.py`, `runtime.test.mjs`.
  - Planning: the change's proposal, design, `guide-delivery` delta and tasks (1.11, 1.12, 2.1, 2.2, 2.4 and 2.5
    checked, then 2.7 and 2.8; 2.5, 3.1 and 7.4 reworded).
  - Commits `6848835`, `2534902` and `ae2e813` on `agents/claude/ci-faster-checks`, draft PR #107.
- **Verification:**
  - The timing tool reproduces the reference run's critical path: build, browser-b lane, collector; 6 min 19 s.
    The reruns took 346, 347 and 262 s.
  - A planted unknown clause fails both `check_ci.py quick` and the CPU lane with the same `advice:plan.01` error.
  - The 511 unit tests run exactly once in 1, 4 and shuffled shards (99.6 s in one process, 29.3 s in four, locally).
    A planted failure in any shard, or a dead shard, fails the check.
  - Local `CI=true` simulations of build, lanes and collector pass 31 of 31 with five and with six lanes.
  - Candidate run 40085436997 passed in all four attempts with 33 checks, 68 of 68 cases and identical validator
    output. Its reruns' median elapsed time is 274 s against the baseline's 346 s; quick feedback takes 19–27 s.
    pip missed in the branch's first run and hit in every candidate attempt. The collector artifacts keep
    their names and inventories. The receipt is in `docs/ci.md`.
  - The release-body tests cover the byte-exact record, review-before-apply and every refusal; `check_release.mjs`
    passes with the marked record.
  - Strict OpenSpec validation passes. The full `check_all.py` passes 31 of 31, and `git diff --check` reports
    nothing.
- **Corrections:**
  - The maintainer chose to reword 2.5 to time excluding slot waits.
  - The maintainer chose a mechanical changelog with single lines for breaking changes, required steps and security
    fixes only.
  - Detail is drawn from commit messages, not pull-request descriptions, which review workflows edit.
  - The release-body helper was requested now.
  - Finding: unit tests overwrote the CPU lane's `duplicates.json`, from which pull-request repair suggestions are
    read. Fixed by private shard report directories.
  - Finding: a rerun removes earlier attempts' artifacts, so attempts 2 and 3 keep job timings only.
- **Close-out:** 19 of 61 tasks complete.
  - 2.3 waits for the changed-lockfile evidence of the first Dependabot PR after this lands, as agreed.
  - 2.6 kept the unit lane. With the maintainer's agreement, a single validator process and a Playwright browser
    cache were not adopted: the validators are off the critical path, and downloads take about 7.5 s of a 17.5 s
    install.

## Claude Code session (apply group 3: repository settings audit)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** `openspec-apply-change` continued at the maintainer's request; the delivered planning,
  quality-first and usage-logging rules; read-only `gh` REST and GraphQL queries of the repository, Project #1,
  the organization's issue types and fields and the App registration; GitHub's permission reference.
- **What:** Tasks 3.1–3.4.
  - `.github/repository.toml` holds the reviewed settings, rulesets with the merge-queue target, environments,
    labels, Project #1 configuration, issue types and fields, App permissions and per-job token requests. The
    approved but unapplied targets are `[[pending]]` entries with their current values.
  - `scripts/audit_repository.py` is read only, names the UI path and an equivalent command for each finding,
    reports unreadable parts as unavailable, and limits `--fix` to declared labels and Project items.
  - An offline token-permission test and the capability table in `docs/maintenance.md`.
- **Impacted:**
  - New: `.github/repository.toml`, `scripts/audit_repository.py`, `docs/maintenance.md`,
    `tests/test_audit_repository.py`, `tests/fixtures/repository-audit.json`.
  - Changed: `tests/test_workflows.py`, CONTRIBUTING, the change's design (open questions answered) and tasks
    (3.1–3.4 checked), this entry.
- **Verification:**
  - A real read-only audit with the maintainer's token finds no drift and four pending targets, all task 4.8. One
    declared label (`breaking-change`) is missing, and the organization issue fields are unavailable.
  - Fixture tests cover planted drift in every section, unreadable sections, hidden bypass actors, reached
    targets, the `--fix` write boundary (a planted deleting fix fails) and schema rejection.
  - A planted extra token permission fails and names the job.
  - The full `check_all.py` passes 31 of 31, and `git diff --check` reports nothing.
- **Corrections:**
  - The maintainer kept the App's current registration as the reviewed state. The design and task 5.8 no
    longer trim it; each job's App token still requests only what that job uses.
- **Findings:**
  - The App registration already reads `organization_projects: read`, not write as planned.
  - `.github/release.yml` and the changelog policy use a `breaking-change` label that did not exist.
  - Bypass actors are hidden from tokens without write access to a ruleset.
- **Close-out:** 23 of 61 tasks complete. With the maintainer's approval, `--fix` created the `breaking-change`
  label; draft PR stacked on #107.

## Claude Code session (review of PR #103)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** The local AIS CR review approval view of PR #103 at `7cf1d36` (nine findings, not
  posted); the delivered quality-first rule for incoming review feedback; a read-only live audit of the rulesets
  and environments.
- **What:** Each of the nine findings was confirmed against the code before it was fixed.
  - High: the audit's command bodies keep every other pending target at its live value, so an unrelated fix
    cannot enable the merge queue before `merge_group` exists. The pending entries and task 4.8 name the
    preconditions (4.1 for the queue, 4.4 for removing the `github-pages` reviewer), and the spec has a scenario.
  - Medium:
    - Undeclared live rule parameters are reported as drift.
    - The reviewed state declares three live pull-request parameters and the GitHub Actions integration of the
      required check.
    - The `/fix-duplicates` admission rule in Python (`admitted()`) and in `commands.cjs` is bound by a parity
      test.
  - Low:
    - `/refresh` reports when publication stopped part-way.
    - The lineage headings and the `Suggested fixes` heading come from their producers.
    - A section-level UI path no longer ends in a blank name.
    - Printed commands are quoted with `shlex`.
- **Impacted:** `.github/repository.toml`, `.github/scripts/{commands,comment-summary,source-publisher}.cjs`,
  `.github/workflows/source-refresh.yml`, `scripts/{audit_repository,check_changelog,fix_duplicates,release_versions}.py`,
  `docs/maintenance.md`, the change's spec delta and task 4.8, `tests/test_{audit_repository,duplicate_review}.py`,
  `tests/page/check_{commands,source_publisher}.mjs`, this entry.
- **Verification:**
  - The focused tests pass. With each fix turned off in turn, its new test fails: holding pending targets, the
    section path, the Python admission guard.
  - A read-only live audit of the rulesets and environments finds 0 drift with the new parameter check, and the
    same four pending targets.
  - `openspec validate --strict` passes.
  - `check_all.py`: 30 of 31 checks pass. `public-content` flags only the review tool's untracked local scratch
    files under `.agents/local_scratch/`; the same rule over all 609 tracked files finds nothing.
- **Findings:** The public-content scan reads untracked files, including the delivered review tooling's runtime
  scratch output, which records an absolute workstation path.
- **Close-out:** 23 of 61 tasks complete; no task changed state.

### Review round 2 (`a7358ef`)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** Four new findings, all reproduced before they were fixed:
  - A missing environment crashed the audit, and a pending entry above the finding's setting kept a stale live
    value. Pending targets are now held unless the finding is at or below them. A target whose ruleset, rule or
    environment does not exist live keeps its recorded current value, so a recreated `github-pages` keeps its
    reviewer.
  - `_keys()` reported a missing required key but let validation continue, so 17 table/key pairs raised
    `KeyError`, not only `project.owner`. It now stops checking that table.
  - A kept team reviewer stays a team in a fix body.
- **Impacted:** `scripts/audit_repository.py`, `tests/test_audit_repository.py`, `docs/maintenance.md`, this entry.
- **Verification:** The four new tests fail on `a7358ef` and pass now. The read-only live audit and
  `--check-config` are unchanged: 0 drift, 4 pending.
- **Close-out:** 23 of 61 tasks complete.

## Claude Code session (apply group 4: merge queue and deployment)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** `openspec-apply-change` continued after #103 merged; the delivered planning and
  quality-first rules; read-only `gh` queries of Project #1 views and the repository settings.
- **What:** Tasks 4.1–4.7.
  - One reusable workflow (`partitioned-checks.yml`) holds the build, lanes and collector. Pull requests, merge
    groups and the deployment fallback call it, and the top-level `checks` job keeps the required context.
  - `checks.yml` runs on `merge_group`, with the queue base, the `preview` channel and no review data.
  - A staging deployment imports a passing merge-queue run's health snapshot (`check_ci.py adopt`) when the commit,
    source files and build inputs match. Otherwise it runs the partitioned checks and says why.
  - An `approve-production` job (environment `production`) waits only for new production bytes. Concurrency is per
    ref.
  - One serialized `publish` job resolves the newest checked staging site and the newest approved release when it
    starts. A cancelled run names its successor.
  - Tag release names the deployment run to wait for, and Dependabot groups minor and patch updates.
  - Deployment and contributor docs updated. The renamed Project views are declared.
- **Impacted:**
  - Workflows and config: `.github/workflows/{checks,partitioned-checks,deploy,tag-release}.yml`,
    `.github/dependabot.yml`, `.github/repository.toml`.
  - Scripts: `.github/scripts/{deployment,release-artifact,prepare-release}.cjs`, `scripts/check_ci.py`,
    `scripts/check_groups.json`.
  - Tests: `tests/test_{workflows,check_ci,audit_repository}.py`,
    `tests/page/check_{publication,release,prepare_release}.mjs`, `tests/fixtures/repository-audit.json`.
  - Docs: `docs/deployment.md`, `docs/design.md`, CONTRIBUTING.
  - OpenSpec: the change's design (decisions 7 and 8), the spec delta (late-approval scenario) and tasks 4.1–4.7.
  - This entry.
- **Verification:**
  - Workflow, check and audit unit tests pass. Each of six mutations of the publication rules fails
    `check_publication.mjs`.
  - Real data: a `preview` `check_all.py` passed 31 of 31, a fresh staging build adopted its report and published
    a passed snapshot naming the commit, and a changed build input was refused with its reason.
  - The full `check_all.py` passes 31 of 31, and `openspec validate --strict` passes.
- **Corrections:** The maintainer chose option 1 for a tag approved after the default branch moved on:
  publication takes the newest checked bytes of each channel from the run that checked them.
- **Findings:**
  - A check run is named after its job, so moving `checks` into a reusable workflow would have broken the
    required context.
  - Pull-request builds use the `local` channel, so only `preview` merge-queue builds can match staging.
- **Close-out:** 30 of 61 tasks complete. Not yet observed on GitHub: the merge queue, `queue: max`, a
  `cancelled()` job after a concurrency cancellation, and whether the queue's tested commit becomes the default-branch
  commit (task 4.9's rehearsal checks them).

### Review of PR #109 (`97b2d65`) and the separate publish workflow

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** Two findings were confirmed and fixed.
  - Medium: the workflow-level cancellation could also cancel a running `publish` job. The maintainer chose
    option C: publication moves to `publish.yml`, started by each successful deployment run, so cancelling
    preparation never interrupts a Pages deployment.
  - The publication binds to the triggering deployment run (`completedDeployment`). It deploys only the staging
    site of the commit its Pages record names, the default-branch head when it started. A tag publishes once the
    head's staging site is checked; until then the head's publication includes it.
  - Release drafting follows a publication that deployed the release, through the `pages-identity` record and
    `publishedRelease`. Tag release reads the `github-pages` deployment records that the tag ruleset reads.
  - Low: the unused `verifiedRun` was removed.
- **Settings:** The maintainer created `production` and removed the `github-pages` reviewer and its tag rule. The
  two satisfied `[[pending]]` entries were removed, `github-pages` is declared `main`-only, and the fixture's
  environments were re-recorded from the live state.
- **Impacted:**
  - Workflows: `.github/workflows/{deploy,publish,release,tag-release}.yml`.
  - Scripts: `.github/scripts/{deployment,release-artifact,prepare-release}.cjs`.
  - Config: `.github/repository.toml`.
  - Tests: `tests/test_{workflows,audit_repository}.py`, `tests/page/check_{publication,release,prepare_release}.mjs`,
    `tests/fixtures/repository-audit.json`.
  - Docs and plan: `docs/deployment.md`, the change's design decision 8 and its spec scenario, this entry.
- **Verification:**
  - Each of ten mutations of the publication, release and tagging rules fails a JavaScript check.
  - The Python and JavaScript tests pass.
  - The live audit of rulesets and environments shows 0 drift and 2 pending.
- **Corrections:** Option C was the maintainer's choice over the recommended per-ref queue.

### Review of PR #109, round 2 (`5cedca9`)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** One Medium finding, confirmed. A publication that deployed nothing still recorded a successful
  `github-pages` environment deployment, which the tag ruleset and Tag release accept.
  - `publish.yml` now decides in a `resolve` job without an environment, and only a deploying `publish` job enters
    `github-pages`. A workflow-level `pages-publish` group keeps deciding and deploying together.
  - `productionSource()` names where approved bytes are without downloading them, and `reuse()` and
    `publishedRelease()` build on it.
- **Impacted:** `.github/workflows/publish.yml`, `.github/scripts/{deployment,release-artifact}.cjs`,
  `.github/repository.toml`, `tests/test_workflows.py`, `tests/page/check_publication.mjs`, `docs/deployment.md`,
  the change's design decision 8, this entry.
- **Verification:** The workflow, audit and check tests and the publication, release and dispatch checks pass, and
  `openspec validate --strict` passes.

### Review of PR #109, round 3 (`8bf9260`)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** One Medium finding, confirmed: a publish run after a cancelled or failed deployment entered the
  workflow-level group and could replace a waiting publication.
  - Only a run that follows a successful deployment enters `pages-publish`; any other run gets a group of its own.
  - A publication after a superseded tag's deployment now publishes the newest approved release rather than nothing,
    so a real run that replaces a waiting one loses nothing.
  - The reviewer's job-level lock on `publish` alone was not used: it would let one run's decision and another's
    deployment interleave and move staging back.
- **Impacted:** `.github/workflows/publish.yml`, `.github/scripts/deployment.cjs`, `tests/test_workflows.py`,
  `tests/page/check_publication.mjs`, `docs/deployment.md`, the change's design decision 8, this entry.
- **Verification:** The Python tests (69) and the publication check pass.

### Review of PR #109, round 4 (`10b0982`)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** One Medium finding, confirmed. A manual (`workflow_dispatch`) deployment run on a release tag was
  admitted, but approval, publication and release drafting follow only a tag's push run. Before this change, release
  drafting also ignored manual tag runs.
  - `sources()` refuses a tag dispatch and names the rerun of the push run as the retry.
  - `completedDeployment()` admits a tag's push run only. The deployment docs say so.
- **Impacted:** `.github/scripts/{release-artifact,deployment}.cjs`, `tests/page/check_{release,publication}.mjs`,
  `docs/deployment.md`, this entry.
- **Verification:** The publication, release and dispatch checks pass.

## Claude Code session (after #109: settings of task 4.8)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** read-only `gh` queries of the post-merge runs, the deployment records and the live
  rulesets; the read-only settings audit.
- **What:**
  - The first hosted run of the new deployment path on `eac8b24` worked.
    - The deployment ran the partitioned checks and named the reason: no merge-queue run, as after a direct merge.
    - `publish.yml` resolved and published, the `github-pages` record names `eac8b24`, and `/next/` reports a passed
      health snapshot for it.
    - The release workflow drafted nothing, because `v1.0.0-alpha.2` already has its assets.
  - The maintainer applied task 4.8's settings, partly out of the task's order. The task records the deviation.
    - The environment steps came together at about 15:59 UTC, before #109 merged at 19:32: `production` was created,
      and the reviewer and tag rule left `github-pages`. The tag rule went back at about 16:01. Until 17:29 at the
      latest, when `github-pages` was `main`-only again, a tag pushed would have published without approval. No tag
      was pushed, and no Pages deployment ran between 14:58 and 19:37.
    - The ruleset steps (merge queue on, "up to date" off) came together after #109 merged.
    - Audits: environments and rulesets at 15:59 (the tag rule missing); environments at 16:01 (0 drift); a read of
      the `github-pages` branch rules at 17:29 (`main` only); rulesets at 19:38 (both steps pending); and the full
      audit at 19:51 (0 drift).
  - The two satisfied `[[pending]]` entries are removed, and the fixture's main ruleset is re-recorded from the live
    state. Tests reproduce the waiting state through `pending_queue()`. Task 4.8 is checked off.
  - `CHANGELOG.md` gains the required-step line for the merge queue and production approval.
- **Impacted:** `.github/repository.toml`, `tests/fixtures/repository-audit.json`, `tests/test_audit_repository.py`,
  `CHANGELOG.md`, the change's tasks, this entry.
- **Verification:**
  - The full read-only audit shows 0 drift and 0 pending; organization issue fields stay unavailable to this token.
  - The audit and workflow tests pass (47).
- **Close-out:** 31 of 61 tasks complete. Task 4.9, the hosted rehearsal, needs separate approval. The first grouped
  Dependabot PR also gives task 2.3's changed-lockfile evidence.

### Review of PR #112 (`7658e3f`)

- **When:** 2026-10-24
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** One Low finding, confirmed. Task 4.8 was checked off while this entry recorded steps applied out of order
  and no audit after each step.
  - Task 4.8 stays checked, with the deviation recorded beneath it: the window, the evidence that nothing deployed,
    and where the audits are listed.
  - The settings bullets above now give the times, the evidence and each audit.
- **Impacted:** the change's tasks, this entry.
- **Verification:** GitHub's `github-pages` deployments, the deployment runs and the remote tags show no deployment
  between 14:58 and 19:37 UTC and no tag after `v1.0.0-alpha.2`. The audit times come from the session transcript.
  OpenSpec validation passes, and the task count is unchanged.

## Claude Code session (after #112, the queue rehearsal and group 5: Project and intake)

- **When:** 2026-10-25
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** `openspec-apply-change` continued for group 5; the delivered planning, quality-first and
  usage-logging rules; the delivered `aiscr-plan-issue` engine, read and imported but not changed; read-only `gh`
  queries of runs, artifacts, Project #1, open issues and Dependabot alerts.
- **What:**
  - After #112 (administrator merge as `01fc802`), the newer push cancelled the older deployment run and named its
    successor. `01fc802` ran the fallback checks, published, and `/next/` reports it. The cancelled run's collector
    failed inside it: folded into the change as task 7.8 with a spec scenario, by the maintainer's decision.
  - Task 4.9, approved by the maintainer: the human-PR part is deferred (recorded beside the task), and the release
    rehearsal uses `1.0.0-alpha.3` with status `testing`. The grouped Dependabot PRs #110 and #111 wait for approval.
  - Task 2.3 evidence: #110 changed `requirements-dev.txt`, so its pip key changed and both Python lanes missed and
    reinstalled. #112's second run hit the cache. Both runs list the same checks per lane and pass 31 of 31. The
    npm half waits for a pull-request run on the new lockfile.
  - Group 5 (tasks 5.2–5.5 and 5.7):
    - Area and `source-refresh` labels with reviewed path rules, applied by `scripts/area_labels.py`.
    - Add-only labelling in the review and refresh publishers through `labels.cjs`; a removed label stays removed.
    - Czech and English issue templates generated from the delivered shape, with `--check` in the offline and quick
      suites.
    - Project item checks in the audit, the digest's public "Project and settings" section, and the reviewed backfill
      mode.
    - The weekly audit job in `health-watch.yml`, which uses the App token for Project #1 only.
    - The triage guide in `docs/maintenance.md`.
  - Task 5.6: the backfill mapping is drafted for review; nothing is applied.
- **Impacted:** `.github/repository.toml`, `.github/workflows/{pr-summary,health-watch}.yml`,
  `.github/scripts/{labels,source-publisher}.cjs`, `.github/ISSUE_TEMPLATE/`,
  `scripts/{area_labels,plan_issue_shape,generate_issue_templates,audit_repository,check_all,check_ci}.py`,
  `scripts/check_groups.json`, `tests/test_{audit_repository,issue_templates,workflows}.py`,
  `tests/page/check_{labels,source_publisher}.mjs`, `tests/fixtures/repository-audit.json`, `docs/maintenance.md`, the
  change's design, spec delta, tasks and `backfill.toml`, this entry.
- **Verification:**
  - A read-only run of the extended audit on live data: 59 open issues without an Issue Type, nothing else.
  - The dry run of the draft backfill: 120 changes, applied by nothing.
  - 20 planted defects each fail a check: one per rule, publisher guard, workflow condition and guide reference.
- **Corrections:**
  - The first draft read the whole audit with the App token.
    From group 3, `docs/maintenance.md` records that the repository sections use `GITHUB_TOKEN` and the App token
    reads only Project #1. The job and the audit follow it, and the audit reports hidden items as unavailable.
  - A security review of the local commit found that the weekly job uploaded the full JSON report and printed the
    full report to its log. Both are public in this repository, and they named Project-only values. The job now
    publishes only the redacted section, and its workflow test guards that.
- **Close-out:** `check_all.py` passes 32 of 32, including the new `issue-templates` check. Strict OpenSpec validation
  passes. 36 of 62 tasks are complete. Task 5.1 waits for `--fix` to create the declared labels, 5.6 for the
  mapping's approval and application, and 5.8 for the organization owner.

### Review of PR #113 (`7b2d5d8`)

- **When:** 2026-10-25
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** Two Low findings, both confirmed, and one pre-existing observation, now reachable.
  - The publishers could make GitHub create an undeclared label with its default colour. They now add only labels
    that exist and name the ones they skip; the next run adds those once `--fix` has created them.
  - The cancellation scenario described a collector change that was not in the PR. The collector now runs unless
    the run was cancelled (task 7.8). The required gate keeps `always()`, because a skipped required check counts
    as passing. The text now promises no collector failure, not a run without any failed job.
  - An empty organization issue-types list was read as drift. The weekly job's token may receive exactly that, so
    the list is now unavailable, as for issue fields.
  - Task 2.3 is complete. pip: #110 changed `requirements-dev.txt`, missed and reinstalled with the same per-lane
    checks as #112's warm run. npm: the key moved from `…78ce8c` to `…7a4652` with `package-lock.json`. #113's
    first run missed and saved it (run 40142786024), and every job of the next run hit it, passing 32 of 32
    (run 40143003658).
- **Impacted:** `.github/scripts/{labels,source-publisher}.cjs`, `.github/workflows/partitioned-checks.yml`,
  `scripts/audit_repository.py`, `tests/test_{audit_repository,workflows}.py`,
  `tests/page/check_{labels,source_publisher}.mjs`, the change's design, spec delta and tasks, this entry.
- **Verification:** Each new guard fails a check when broken (four planted defects).

### Labels and backfill applied (tasks 5.1 and 5.6)

- **When:** 2026-10-25
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** With the maintainer's approval of the suggested steps:
  - `audit_repository.py --section labels --fix` created the six `area:*` labels and `source-refresh` with their
    reviewed metadata (`breaking-change` already existed).
  - The backfill was compared once more and then applied: 59 Issue Types and 61 area labels, with no unmapped or
    closed issue.
  - The test fixture's labels, Project items and open issues are re-recorded from that state.
  - The permission system refused approving and queuing #110 and #111 under the maintainer's account. That step is
    the maintainer's.
- **Impacted:** live labels and issue types and labels of the 61 open issues (GitHub); `tests/fixtures/repository-audit.json`,
  `tests/test_audit_repository.py`, the change's tasks, this entry.
- **Verification:**
  - The full read-only audit shows 0 drift, 0 missing, 0 undeclared and 0 attention. Only organization issue fields
    stay unavailable.
  - All 61 open issues have a type and an area label.
  - By their filters, the views hold 26 automated and 22 authored pull requests and 24 `area:maintenance` issues.
- **Close-out:** 40 of 62 tasks complete; 5.8 waits for the organization owner and 4.9 for the queue approvals.

### Merge-queue rehearsal: adoption and fallback repairs

- **When:** 2026-10-25
- **Agent / runtime:** Codex (API)
- **Model / backend:** GPT-6; exact backend model ID not exposed by the runtime.
- **What:** Continued the approved Claude session. The maintainer queued #110 and #111; both merged, and the
  final tested commit was `d1ef695`. Deployment run 40147547699 rejected the queue evidence because the initial
  health inventory names its producing run. Its summary pipeline nevertheless returned success through `tee`,
  skipping full checks. Publication run 40147592421 refused the unchecked site before Pages deployment.
  Adoption now compares every built file except the three health files it replaces, retains snapshot identity
  and API validation, and preserves the adoption exit status through the pipeline.
- **Impacted:** `scripts/check_ci.py`, `.github/workflows/deploy.yml`, `tests/test_{check_ci,workflows}.py`, the
  change's design, delivery spec delta and task 4.9 evidence, this rolling entry.
- **Subagents used:** none.
- **MCP servers used:** GitHub.
- **Workflow context used:** `fair-guide-editor`, `openspec-apply-change`; change
  `enhance-ci-and-repository-workflows`, with the existing implementation and hosted-rehearsal approvals.
- **Verification:** 54 focused deployment/workflow tests pass, including a real health publication proving that
  precisely the excluded files are replaced. The actual Bash script selects reuse only for successful adoption,
  selects full checks for a failed adoption or missing run, and reproduces false reuse when `pipefail` is removed.
  Four planted regressions are detected: comparing the run-specific snapshot, ignoring all built files, excluding
  an extra unchanged file, and removing `pipefail`. The saved queue and local builds of `d1ef695` contain 1,956
  files apiece and differ only in the three replaced health files. Fresh native `check_all.py` passes 32 of 32
  checks in 152.8 s, including all unit shards, browser groups, validators and final health API validation;
  strict change validation, Ruff and diff checks pass.
- **Close-out:** 40 of 62 tasks remain complete. Hosted reuse after the repair, release preparation and promotion
  remain pending; the unsuccessful rehearsal is not acceptance evidence for task 4.9.
