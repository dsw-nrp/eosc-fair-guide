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

### PR #113 review: multiline adoption conditions

- **When:** 2026-10-25
- **Agent / runtime:** Codex (API)
- **Model / backend:** GPT-6; exact backend model ID not exposed by the runtime.
- **What:** Confirmed review comment `discussion_r4369192866`: the conditional-pipeline regex skipped multiline
  conditions. Replaced it with a direct invariant requiring `pipefail` before the adoption command in every
  workflow step, independent of condition layout or an explicit shell.
- **Impacted:** `tests/test_workflows.py`, this rolling entry.
- **Verification:** The previous guard accepts the review's multiline reproduction. The replacement passes all
  29 workflow tests and 30 planted variants of single-line/multiline conditions, continued pipelines, explicit or
  omitted shells, and missing/before/after `pipefail`; every unsafe variant fails. Fresh native `check_all.py`
  passes 32 of 32 in 165.7 s, including the complete unit, browser, validator and final health API coverage.
- **Close-out:** Implementation remains in the approved `enhance-ci-and-repository-workflows` change; task 4.9
  still requires successful hosted reuse and release promotion.

### Post-merge deployment and alpha.3 release preparation

- **When:** 2026-10-25
- **Agent / runtime:** Codex (API)
- **Model / backend:** GPT-6; exact backend model ID not exposed by the runtime.
- **What:** Verified #113 merged as `ad5fc4b`. Its deployment selected full checks, correctly reporting no queue
  result for the administrator merge, and succeeded (run 40150326046, 5 min 13 s). Pages publication 40150667025
  succeeded. Live staging reports that revision with passed checks; production still reports `v1.0.0-alpha.2`
  at `8350edd`. Ran the previously approved Prepare release workflow for `1.0.0-alpha.3` on `main`;
  run 40150741799 opened release PR #114 at `0277060`, authored by `fair-guide-actions[bot]`.
- **Impacted:** GitHub release PR #114; task 4.9 evidence and this rolling entry.
- **Subagents used:** none.
- **MCP servers used:** GitHub.
- **Workflow context used:** `fair-guide-editor`, `openspec-apply-change`; existing approval for the hosted
  rehearsal in `enhance-ci-and-repository-workflows`. `gh` supplies run discovery and workflow dispatch, which
  the connected GitHub tools do not expose.
- **Verification:** Release preparation passed its metadata and generated-site version checks. The PR changes
  exactly the nine declared release files: six metadata owners, changelog, provenance and identifier register.
  All owning versions are `1.0.0-alpha.3`, dates are 2026-10-25, and the changelog retains the curated lines plus
  the 11 merged PRs and two direct commits in the 13-commit first-parent history. PR checks, including the
  required gate, passed in run 40150788749 at `0277060`. Fresh native close-out for this evidence update passed
  32 of 32 checks in 151.5 s, including all unit shards, browser groups, validators and final health API checks.
  The editor held the original environment's Ruff executable open during dependency alignment; restored the
  interrupted uninstall's package directories and used an isolated environment with the pinned
  `roc-validator==0.13.0` and `ruff==0.17.1` plus `npm ci` instead.
- **Close-out:** Task 4.9 remains open. PR #114 needs review and a queue merge; corrected hosted reuse and the
  approved release promotion still require their own observed outcomes. Evidence is kept on
  `agents/codex/alpha3-rehearsal`, separate from the generated release branch.

### Plan revision after the alpha.3 rehearsal

- **When:** 2026-10-25
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** Resumed after the previous Codex session ended on a credit limit while #114 was queued, and verified
  the hosted outcome: queue run 40153182976 passed and deployment 40153496770 reused it; Tag release 40154472734
  tagged `v1.0.0-alpha.3` at `161994f`; production was approved in run 40154498215; publication 40155190767 and
  release 40155239756 followed, leaving an unpublished draft. Explored the queue rejection 40151368869, the
  `/next/` label after tagging, environment naming, schedule delays and documentation shape, then revised the
  change's planning artifacts: decisions 16–23, eleven added delivery requirements, two modified knowledge-base
  requirements, task groups 8–10, integrated verification renumbered to group 11 with a final rehearsal (11.3),
  and decision notes on 4.9 and 5.8.
- **Impacted:** the change's proposal, design, tasks and both spec deltas, and this entry, on branch
  `agents/claude/ci-workflows-replan`. No implementation, workflow or repository setting changed.
- **Subagents used:** none.
- **MCP servers used:** none.
- **Workflow context used:** `openspec-explore`, `openspec-update-change`; `aiscr-planning-core` holds
  implementation until a fresh apply instruction for the revised plan.
- **Verification:** `npx openspec validate enhance-ci-and-repository-workflows --strict` reports the change valid;
  `npm run openspec:validate` passes 6 of 6; a read-only `audit_repository.py --section app` reports no drift;
  `python scripts/check_all.py` passes 32 of 32 in 142.2 s.
- **Corrections:** The maintainer corrected the claim that `/next/` served alpha.3: its footer showed
  `v1.0.0-alpha.2+15`, built before the tag, which became decision 19. The maintainer also counted #114 as 4.9's
  human path, confirmed the App installation for 5.8, chose a one-wave documentation reshape over gradual change,
  and deferred a human documentation review in favour of an independent agent reader.
- **Close-out:** Planning revision only. Implementation of groups 6–11 and the evidence for 4.9 and 5.8 await
  approval of the revised plan.

### Group 8: release flow repairs and the 4.9 close-out

- **When:** 2026-10-25
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** Under the maintainer's apply instruction, closed 4.9 with the rehearsal evidence and implemented tasks
  8.1–8.6 on `agents/claude/ci-workflows-replan`: paradata freshness from history; release dispatches accepting a
  leading `v`; Tag release refusing a changelog that misses changes and calling Prepare release to complete it;
  completion and guarded replacement of release proposals; the `/next/` notice when it equals the release; and
  `staging`/`production` records once each channel is live. Implementation corrected the plan in two places, both
  recorded in design 17 and the changelog requirement: the reroute is a reusable-workflow call, and an untagged
  release section may gain lineage entries. A background security review of `e4d25cb` found that `staging` lacked
  the branch policy of `github-pages`; `0e0eba3` restores it and makes Tag release require a record written by
  publication. Dispatched health watch run 40190490225 for 5.8's evidence: its audit job read the App token but
  reported Project #1 unavailable and the merge settings as drift.
- **Impacted:** `scripts/check_content.py`, `check_changelog.py`, `release_version.py`, `release_versions.py`,
  `assemble_pages.py`; `.github/scripts/prepare-release.cjs`, `release-version.cjs`, `deployment.cjs`; workflows
  `prepare-release.yml`, `tag-release.yml`, `publish.yml`, `deploy.yml`; `.github/repository.toml` (staging, the
  tag ruleset target as pending, tokens); `assets/css/staging.css`; `docs/content-model.md`, `docs/deployment.md`;
  the native content rule with regenerated mirrors; tests; this change's artifacts.
- **Subagents used:** none.
- **MCP servers used:** none.
- **Workflow context used:** `openspec-apply-change`, `fair-guide-editor`; `aiscr-planning-core` for the apply
  boundary and the plan corrections.
- **Verification:** `python scripts/check_all.py` passes 32 of 32 in 147.5 s at `0e0eba3`; strict OpenSpec
  validation passes. Planted regressions are caught for the freshness rule (four tests fail on the old rule),
  `v`-stripping in both runtimes, the release self-exclusion, the lineage-only changelog rule, the unedited-proposal
  check, the lineage gate on tagging, the release notice, repeated channel records, the tag gate's environment, the
  publication provenance check and the moved-branch handling. A read-only audit of environments and rulesets reports
  exactly the two pending 8.7 targets and no drift.
- **Close-out:** 8.7 follows the merge of this group; 8.8 waits for the delivered release-notes tooling. 5.8 stays
  open: run 40190490225 shows that the audit queries Project #1's workflows, which the App's read permission does
  not cover, so the whole Project section fails with a misleading owner step, and that it reports settings the
  job's token cannot see as drift. A repair is proposed as a new task for approval.

### Audit repair, schedule, delivery refresh and the maintenance digest

- **When:** 2026-10-25
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** Continued the apply phase on `agents/claude/ci-workflows-replan` (draft PR #116). 5.9: the weekly audit
  reads Project #1's workflows in their own query and reports what its token cannot see as unavailable, not drift.
  9.1–9.2: the weekly jobs finish by Monday morning in Prague, and a manual health-watch run chooses its parts.
  7.8 follow-up: the PR summary skips a cancelled checks run. The native delivery reader accepts the format 2
  receipt, and the refreshed `aiscr-*` delivery (55cc0a0) is applied unchanged. Group 6 (6.1–6.9): the live watch
  classifies outcomes, selects the least recently attempted links under host caps and `Retry-After`, keeps
  versioned state, validates reviewed limitations offline and ignores pagination; one maintenance digest is rebuilt
  in place, comments only on change, rotates by closing and adopts keyed tasks from people with write access. The
  watch job is now read-only; a separate publish job is the only writer, and the state artifact is read only from
  this workflow's default-branch runs. `health-issues.cjs` is removed.
- **Impacted:** `scripts/audit_repository.py`, `watch_sources.py`, `agent_surfaces.py`, `check_all.py`,
  `check_ci.py`, `check_groups.json`; `.github/scripts/health-digest.cjs` (replaces `health-issues.cjs`),
  `.github/health-watch.toml`; workflows `health-watch.yml`, `source-refresh.yml`, `pr-summary.yml`;
  `.github/repository.toml` (tokens, label paths, staging recorded); the delivered `aiscr-*` surfaces, the
  manifest and the delivered sections of `CODEX.md`; `README.md`, `README_en.md`, `docs/design.md`,
  `docs/maintenance.md`; tests and fixtures; this change's tasks.
- **Subagents used:** none.
- **MCP servers used:** none.
- **Workflow context used:** `openspec-apply-change`, `fair-guide-editor`; `aiscr-planning-core` for the apply
  boundary.
- **Corrections:** The maintainer reported that the review comment workflow failed on cancelled checks runs, a
  regression from the 7.8 collector change; the comment job now skips a cancelled run.
- **Verification:** `python scripts/check_all.py` passed 31 of 33; the two failures were one over-long test line,
  fixed during the run, after which `ruff`, `format`, `unit` and `helpers` pass 4 of 4 on the final tree. Strict
  OpenSpec validation passes. Planted regressions are caught for the publisher's run condition, the state choice
  after a refused publication, and the branch and fork filters of the previous-state lookup; an offline
  observe-and-render chain produces the reset notice and the "audit did not run" section.
- **Close-out:** 58 of 78 tasks are done. The digest workflow first runs hosted after merge, with 5.8/5.9's
  audit-only run and 8.7's ruleset switch. 6.10 (legacy issue migration) and 6.11 (digest runbook) follow, then
  groups 7 and 10, 8.8 and group 11.

### Documentation wave and independent reader review

- **When:** 2026-10-25
- **Agent / runtime:** Codex
- **Model / backend:** GPT-6; exact backend model identifier not exposed by the runtime.
- **What:** Resumed Claude's approved apply scope on `agents/claude/ci-workflows-replan`. Completed the human
  documentation reshape: three audience entry routes, task runbooks, contributor how-tos, retained detailed
  references and a 148-section map. Registered the documentation check in local, CPU and quick inventories;
  added planted regressions for structure, filenames, links, empty steps and missing repeated sections. Updated
  native content/contract examples and documentation/changelog rules, then regenerated the vendor mirrors.
  Three fresh audience readers found and rechecked repairs for discoverability, embedding configuration, advisory
  wording, local repair identity/recovery, deployment retries, review fallback and reference/procedure separation.
- **Impacted:** Both READMEs, CONTRIBUTING, human docs and new how-tos/runbooks; `scripts/check_docs.py`,
  `check_all.py`, `check_ci.py`, `ci_catalogue.py`; the authored CI catalogue; native rules and generated mirrors;
  tests; the change's section map, review receipt, hand-off status and tasks; the single digest migration line in
  `[Unreleased]`. Delivered files and delivered CODEX sections retain their receipt integrity.
- **Subagents used:** `default` agents `docs_reader_review`, `docs_contributor_review`, `docs_maintainer_review`,
  each without the writing conversation; all final passes returned `NO_FINDINGS`.
- **MCP servers used:** GitHub (read-only issue #83/#84 reconciliation and PR recovery).
- **Workflow context used:** `openspec-apply-change`, `fair-guide-editor`; approved design decision 23 and tasks
  7.2, 7.5 and 10.1-10.4. No new implementation scope or hosted write approval was inferred.
- **Verification:** The documentation check and section map pass for 37 documents and 148 former sections;
  15 documentation tests, 8 catalogue tests and 35 workflow tests pass. Native generation, ownership and
  sibling-delivery checks pass. The first integrated run passed 35/36 checks: the unit suite caught introductory
  tooling links and source-name coverage lost from the READMEs. Those contracts were restored without weakening
  their tests; 20 tooling tests (one platform skip), 5 source-registry tests and the reader re-review pass.
  A further planted directory typo is caught by the documentation checker. The corrected full close-out passed 36/36 checks in 150.0 seconds, including all browser/API groups, accessible
  diagrams and the three crate profiles. All 656 discovered unit tests are accounted for, with one platform skip.
  The tracker is 71/78 complete; the seven hosted/approval-dependent tasks remain open.
- **Corrections:** Independent readers caught missing or inaccessible information rather than accepting the
  structure check alone. Their eight finding groups and repairs are in the change's `documentation-review.md`.
- **Close-out:** Documentation is locally accepted by all three audiences. Hosted audit, first-digest verification,
  legacy migration, tag-ruleset switch, draft-helper exercise and release rehearsal remain owned deferrals in
  `handoff-status.md`; their tasks stay unchecked. No issue state, setting, release or archive was changed.


### Follow-up planning capture

- **When:** 2026-10-26
- **Agent / runtime:** Codex
- **Model / backend:** GPT-6; exact backend model identifier not exposed by the runtime.
- **What:** Used the maintainer's explicit task-capture instruction to extend the existing
  `enhance-ci-and-repository-workflows` plan coherently across proposal, design, both capability deltas and tasks.
  Added 22 tasks covering serving-location addresses and effective indexing, issue-origin refresh, narrowly
  scoped organization audit reads, settings decisions, complete durable-documentation verification and renewed
  integrated acceptance. Reconciled remaining hand-offs with already applied owner actions and the delivered
  native release helper; retained all previous task states and historical receipts.
- **Impacted:** Only the five existing OpenSpec planning artifacts and this rolling usage entry. The staged
  implementation, prior review receipts, durable docs and delivered assets were not edited by this capture.
- **Subagents used:** none during this planning capture.
- **MCP servers used:** none during this planning capture; dated read-only observations from the preceding
  exploration are retained as such in the design.
- **Workflow context used:** `openspec-update-change` for the approved planning capture following
  `openspec-explore`; `fair-guide-editor` and delivered planning/usage rules for repository boundaries.
- **Verification:** Strict change validation and `npm run openspec:validate` pass (6/6 items). Public-content
  checks report no findings and all 10 usage entries pass before this append. Direct integrity checks confirm
  exactly 22 new unchecked tasks, all 78 earlier task states unchanged, 71/100 complete, retained baseline
  scenario names and ADDED requirement descriptions within 500 characters. `git diff --check` passes; the staged
  index matches its pre-capture SHA256. Final usage/public-content checks follow this append. Implementation
  tests were not rerun for planning-only edits; the 25 October full-suite receipt remains historical evidence.
- **Corrections:** The maintainer chose indexing the current GitHub Pages address and clarified that all
  Guide-owned addresses should follow the actual serving location rather than a strictly predicted base URL.
  The plan covers runtime links, API/export consumers and semantic/static publication metadata together,
  preserving logical IDs, exact external IRIs, offline/iframe use, shared channel identities and verified bytes.
- **Close-out:** Planning capture only: 71/100 tasks complete, 29 remaining including seven prior hosted/approval
  gates. Tag-deployment selection and queue tuning remain explicit decisions with current protections and values
  retained. Implementation resumes through approved apply. No staging, commit, push, remote mutation, release,
  archival or memory update was performed.


### Authorized checkpoint commit and apply resumption

- **When:** 2026-10-26
- **Agent / runtime:** Codex
- **Model / backend:** GPT-6; exact backend model identifier not exposed by the runtime.
- **What:** Prepared the maintainer-requested local checkpoint of the accumulated documentation wave,
  follow-up plan and owner-ordered upstream tooling delivery, before resuming approved apply of the same change.
- **Impacted:** Existing staged work, including delivery source `79abd13a2bda8ad6d83de4001bd283c6b087d6dc`;
  no delivered copy was edited by this session. The existing branch is retained.
- **Subagents used:** none at this checkpoint.
- **MCP servers used:** none at this checkpoint.
- **Workflow context used:** `openspec-apply-change`, `fair-guide-editor` and delivered planning/usage rules;
  the fresh explicit user instruction authorizes implementation of the captured follow-up after the commit.
- **Verification:** Strict OpenSpec validation passes 6/6 and staged whitespace checks pass. Ownership has no
  findings. Native generation reports seven stale outputs after the delivery and authored rule changes. The
  local delivery checker reports one entry-section hash mismatch because the new stamp is inside the SPDX
  prologue; removing only that receipt line yields the manifest's exact section hash. Both compatibility findings
  are recorded for repair in the Guide-owned consumer and native regeneration after the checkpoint; this is not
  a claim that the current implementation has passed fresh full acceptance.
- **Corrections:** The maintainer confirmed the upstream bundle was delivered on their order and explicitly
  requested a local commit followed by apply. The delivered layer remains read-only.
- **Close-out:** Checkpoint scope is concrete and staged; 71/100 tasks remain complete. Commit is local only.
  Resume implementation with compatibility repair and the pending approved tasks; hosted settings, migration,
  publication and archival retain their separate gates.


### Approved follow-up implementation and remaining namespace decision

- **When:** 2026-10-26
- **Agent / runtime:** Codex
- **Model / backend:** GPT-6; exact backend model identifier not exposed by the runtime.
- **What:** Created the authorized local checkpoint `1a5287f5adbc083ce95728212388e5527dc54261`, then resumed
  approved apply of `enhance-ci-and-repository-workflows`. Repaired Guide-owned receipt compatibility without
  editing the delivered bundle; implemented issue-origin refresh and scoped organization audit reads; reconciled
  the chosen tag and queue declarations; completed the bounded documentation follow-ups and workflow diagrams.
- **Impacted:** Guide-owned scripts/tests, refresh/audit and draft publication-input workflows, settings
  declarations, runtime location handling, content metadata/paradata, durable docs, native mirrors and the
  existing OpenSpec evidence records. The delivery manifest and delivered sections remain unchanged after
  the checkpoint. Serving-location edits remain a draft pending the explicit namespace-transition decision.
- **Subagents used:** `aiscr_analyse_integration` at `/root/review_runbook_reader`, read-only independent
  procedure checks for review roles/runbook, complete migration relocation and workflow-diagram semantics.
- **MCP servers used:** GitHub, read-only primary action/runner/context sources; no external posting.
- **Workflow context used:** `openspec-apply-change`, `fair-guide-editor`, native content/surfaces rules and
  delivered planning, usage/model logging and review-reader contracts. The review skill was inspected as a
  documentation authority; no formal PR review or grouped posting was invoked.
- **Verification:** OpenSpec reports 82/100 tasks complete. Targeted suites pass: 21 native-surface tests
  (one platform skip), 40 audit tests, 36 workflow tests, eight catalogue tests and 25 documentation tests.
  Real parser-to-refresh-reply fixtures cover issues and PRs; planted PR-only and organization-routing
  regressions are caught. Documentation checks cover all 37 documents and the section map; actual offline
  JSON-LD expansion and wrong-prefix/alias/scheme controls pass. All 20 Mermaid diagrams and six approved
  SVG adaptations render; four false publication shortcuts are rejected. The independent bounded readers
  returned NO_FINDINGS. Inspected bilingual About screen/print screenshots at desktop and phone widths;
  content/freshness checks pass. The runtime location matrix passes eight origin/prefix/filename iframe
  cases, actual JSON/FTR exports and offline fallbacks. A native full unit run found six integration
  failures; corrected the unclear mapping example, regenerated catalogue and outdated read-only workflow
  assertions, then reran all three affected suites successfully. Fresh native complete acceptance passes
  36/36 checks in 143.0 s, including 671 unit tests (one platform skip), all browser/API groups, all three
  crate profiles, strict OpenSpec and native generation/ownership/delivery. The earlier 25 October receipt
  is not reused as proof for this tree. Final usage/public-content/docs/OpenSpec checks follow these
  evidence-only updates; group 15 remains open for its unmet full claim/address/hosted acceptance criteria.
- **Corrections:** The maintainer explicitly retained both `github-pages` and `staging` deployment gates
  plus Actions `checks`, and selected the live maximum merge batch of ten. Read-only ruleset/App audit
  reports zero findings. A fresh production read exposed an unhandled namespace transition: production
  still defines the legacy fair.eosc.cz vocabulary/profile. Task 12.1 is reopened; affected implementation
  is paused for the choice of coordinated release cutover or temporary semantic-namespace retention.
- **Close-out:** Eleven follow-up tasks are complete; 18 tasks remain, including the six address/discovery
  tasks, complete long-document verification/final audience review, renewed acceptance and earlier hosted
  hand-offs. This is local implementation evidence. No push, second commit, hosted setting/issue mutation,
  dispatch, publication, release, archival or memory update was performed.


### Coordinated next-release namespace cutover planning decision

- **When:** 2026-10-26
- **Agent / runtime:** Codex
- **Model / backend:** GPT-6; exact backend model identifier not exposed by the runtime.
- **What:** Recorded the maintainer's selection of a coordinated production/preview namespace cutover at the next
  release. Reconciled the existing proposal, design decision 28, both capability deltas and tasks with that choice;
  updated the existing address inventory and hand-off record. Added unchecked task 12.7 and expanded transition,
  refusal/retry and namespace-aware artifact/reuse acceptance. The plan identifies the absolute-IRI compatibility
  change for settled release notes without changing the current changelog or implementing the transition.
- **Impacted:** Five existing planning artifacts, the existing address inventory/hand-off records and this rolling
  usage entry. No new planning artifact was created. Ordinary previews retain published production semantics until
  the verified next-release/current-head-preview pair can be deployed together; prior archives keep their bytes.
- **Subagents used:** none during this planning revision.
- **MCP servers used:** none during this planning revision.
- **Workflow context used:** `openspec-update-change` and `fair-guide-editor`; selected repo-local root and
  spec-driven schema were confirmed through the CLI. The maintainer's explicit direction authorizes this planning
  revision, while implementation continues through apply and release execution retains its separate approval.
- **Verification:** Strict change and all-spec validation pass (6/6 items). The diagram run passes 21 Mermaid
  diagrams and six approved SVG adaptations. New/revised requirement descriptions remain within 500 characters.
  Direct fingerprints confirm all 878 implementation/source files outside planning and usage are unchanged, and
  the index remains unstaged. CLI progress is 82/101: one new unchecked task, no implementation completion inferred.
  Public-content and whitespace checks pass; final planning/usage checks follow this append. The prior 36/36 native
  suite remains evidence for the unchanged implementation draft, not acceptance of this newly planned cutover.
- **Corrections:** The maintainer chose coordinated next-release cutover, resolving the pending direction question.
  This selects planning scope only, not a release version, tag, promotion or publication approval. The current
  address implementation draft still needs reconciliation and acceptance under the revised plan.
- **Close-out:** Planning revised coherently. No implementation edits, commit, push, hosted mutation, dispatch,
  release, publication, archival or memory update. Remaining work is 19 unchecked tasks through the apply and
  separately approved hosted/human hand-offs; the previous 82/100 receipt retains its historical scope.

### Interrupted cutover implementation (recovered record)

- **When:** 2026-10-26
- **Agent / runtime:** Codex
- **Model / backend:** GPT-6; exact backend model identifier not exposed by the runtime.
- **What:** Continued apply after the planning decision. Drafted most of the coordinated namespace cutover
  (separate publication and semantic inputs, paired release/preview publication, manifest stamps and assembly
  refusal) and started three complete documentation readers. The session stopped mid-edit at 20:33 UTC when its
  workspace credits were exhausted; it wrote no usage entry, left no contributor receipt and ticked no task.
- **Impacted:** Uncommitted publication scripts, workflows, tests and documentation, later reviewed and repaired by
  the resumed apply below. Nothing was committed, pushed, dispatched or published.
- **Subagents used:** `/root/reader_claims`, `/root/contributor_claims` and `/root/maintainer_claims`.
- **MCP servers used:** none in this continuation; its GitHub reads all precede the planning entry above.
- **Workflow context used:** `openspec-apply-change` and `fair-guide-editor`. Recorded afterwards by the resumed
  apply from the Codex session logs, because the interrupted session could not close out.
- **Verification:** None completed in the session. Its draft was not accepted as found: the resumed apply
  verified it and repaired three defects (see `address-inventory.md`, local acceptance matrix).
- **Close-out:** Interrupted; superseded by the resumed apply entry below.

### Resumed cutover apply and contributor documentation review

- **When:** 2026-10-26
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** Reviewed the interrupted Codex draft and its session logs, repaired it and completed tasks 12.2-12.7.
  The repairs: the pre-deployment recheck no longer fails every overtaken ordinary publication (it checks the head
  only for a paired release), fixtures no longer substitute the newest approved release for the live one, and the
  paired preview reads the default head after approval in a new `pair-head` job. Recovered and resolved the
  interrupted readers' 23 first-pass findings, then ran a fresh contributor reader and repaired its 12 findings,
  including stale documentation links in comment-command and duplicate-repair messages.
- **Impacted:** `deploy.yml`, `publish.yml` and `checks.yml`; the deployment, publication-location, health-digest and
  command scripts; reviewed token and catalogue declarations; publication, workflow, docs and command tests; the
  duplicate-repair messages; deployment, design, content-model, release, assembly and contributor documentation;
  the change's address inventory, documentation review, hand-off status and tasks.
- **Subagents used:** general-purpose documentation readers: the contributor reader (complete receipt) and a Guide
  reader that stopped at the runtime's session limit without a receipt.
- **MCP servers used:** none.
- **Workflow context used:** `openspec-apply-change` and `fair-guide-editor`, with the delivered planning, review
  conduct and usage/model logging rules.
- **Verification:** Fresh native acceptance passed 36/36 checks in 204.6 s, including 683 unit tests. Planted
  head-recheck, stale-placeholder and removed-anchor regressions fail their checks. Strict OpenSpec validation
  passes (6/6) and the documentation check passes for all 37 documents.
- **Close-out:** Interrupted at the runtime's session limit with the tracker at 89/101. Nothing committed, pushed,
  dispatched or published; continued by the Kilo session below.

### Final audience passes and renewed acceptance

- **When:** 2026-10-27
- **Agent / runtime:** Kilo (VS Code extension)
- **Model / backend:** anthropic/claude-opus-5-5
- **What:** Resumed the apply from the interrupted Claude Code transcript. Ran fresh Guide-reader and maintainer
  readers (the earlier Guide reader had no receipt) and repaired their nine findings after confirming each against
  code. The repairs: build prerequisites and FRSM-13 evidence, citing the Guide, Czech titles, App credential types,
  the partitioned-checks callers, how waiting runs are described, a hand-off for a reused merge-queue result, and the
  emergency-merge label step. Completed tasks 14.1, 14.9, 15.1 and 15.2 (93/101).
- **Impacted:** both READMEs; software-practice, design, CI reference and emergency-merge documentation; the CI
  catalogue source and generator; the crate's `runtimePlatform`; the merge-queue adoption output in
  `scripts/check_ci.py`; the catalogue and adoption tests; and the change's documentation review, section map,
  hand-off status and tasks.
- **Subagents used:** `general` (two read-only documentation readers: Guide readers and maintainers).
- **MCP servers used:** none.
- **Workflow context used:** `openspec-apply-change` and `fair-guide-editor`, with the delivered planning, review
  conduct, quality-first and usage/model logging rules. Issue states were read with `gh issue view` only.
- **Verification:** `python scripts/check_all.py` passes 36/36 checks in 203.2 s, including 684 unit tests.
  Strict OpenSpec passes 6/6, and generation, ownership and delivery report zero findings. The section-map check
  passes for 37 documents. The old reuse summary and the old catalogue wording each fail their new tests when
  planted, and both files were restored byte for byte.
- **Corrections:** A shell command was refused under the user's global Kilo allowlist (`Push-Location` is not
  listed); the user asked for the permissions to be checked, and later commands stay within it. An emergency-merge
  fix that would have sent maintainers to the audit's `--fix` write directly was narrowed to the approval-gated
  settings-audit runbook before checks ran.
- **Close-out:** Local acceptance is complete. The eight remaining tasks are hosted or human hand-offs with separate
  approvals. Nothing committed, pushed, dispatched, published or archived, and no issue was changed.

### Status review, finishing capture and group 16 apply

- **When:** 2026-10-27 to 2026-10-28
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** In explore mode, reviewed the change's status against the remote events of 25–27 October: the red
  scheduled refresh with its reasons only in an artifact, 18 issues opened by the legacy watch (17 for one host), and
  #116's hosted failures. Evaluated the namespace pair machinery. At the maintainer's direction, captured the
  finishing scope (S1 now, a persistent namespace deferred to an issue, hand-offs finished through use, group 16)
  in the change artifacts. Then applied 16.2–16.7:
  - a reviewed `namespace` replaces the live-production lookup and the paired publication, with documentation;
  - digest host grouping and collapsed overflow;
  - scheduled refresh summaries that fail only when a maintainer acts, and refresh outcomes in the digest;
  - separate audit App tokens;
  - the language-markup rule wording.
  16.1's quick-job install and its import-derived test are in place, awaiting the hosted run.
- **Impacted:** `checks.yml`, `deploy.yml`, `partitioned-checks.yml`, `publish.yml`, `health-watch.yml` and
  `source-refresh.yml`; `publication-location.cjs` (reduced), `deployment.cjs`, `release-artifact.cjs`,
  `health-digest.cjs` and `source-publisher.cjs`; `build_crate.py`, `publication_location.py`, `assemble_pages.py`,
  `audit_repository.py`, `watch_sources.py` and `check_docs.py`, with `publication_inputs.py` removed;
  `content/guide.toml`; the reviewed token list and CI catalogue (regenerated reference); the native content rule
  and its generated mirrors and `CODEX.md` region; deployment, design, content-model, maintenance, assembly,
  release, digest and refresh documentation; `CHANGELOG.md`; the affected Python and JavaScript tests; and the
  change's proposal, design, specs, tasks, migration record, hand-off status and address inventory.
- **Subagents used:** none.
- **MCP servers used:** none.
- **Workflow context used:** `openspec-explore` (status review and capture) and `openspec-apply-change`, with the
  delivered planning, quality-first, review-conduct and usage/model logging rules and the native content and
  surface rules. Remote state was read with `gh` only.
- **Verification:** each task's planted regressions failed and the restored files passed:
  - a quick check importing an uninstalled module;
  - one token refusal blocking both reads;
  - the namespace following the environment;
  - different publication roots accepted;
  - host grouping disabled;
  - overflow sent back to the artifact;
  - a retried source failing the run;
  - render ignoring the refresh.

  The first full run failed one unit test that encoded the old "one setting moves everything" contract; it was
  rewritten for the reviewed namespace and passes. On the final tree `python scripts/check_all.py` passes 36/36 checks
  in 159.3 s. Strict OpenSpec passes 6/6, and generation, ownership and delivery report zero findings.
- **Corrections:** The maintainer redirected the namespace design from the implemented coordinated pair to a reviewed
  setting (S1), and the remaining hand-offs from deferral to completion through use. A `git rm --cached` of
  `scripts/publication_inputs.py` unstaged that file before it was deleted, which had not been announced in
  advance. A shell heredoc that could start the Windows Python stub was stopped and replaced by an editor change.
- **Close-out:** Local tasks 16.2–16.7 and 16.9 are complete (100/113). 16.1 waits for #116's hosted `quick` run;
  16.8 (two issues) and 16.10–16.12 need their approvals. Nothing committed, pushed, dispatched, published or
  archived, and no issue was changed.

### Review capture: #116 findings and release-flow observations

- **When:** 2026-10-28
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** In explore mode, checked the AIS CR review approval view of #116 at `2ccc0a6` against the head. All
  seven findings and all four pre-existing observations hold. Finding 5 holds, but its stated mechanism and
  `overwrite: true` fix do not: the same job uploads `github-pages` before deploying. The documented
  default-branch deployment is the retry route. Two observations go further than the review says: a lower tag
  cannot be deleted and would shift the next release's lineage base, and the image recheck skips the superseded
  release's draft. At the maintainer's direction, captured tasks 16.13-16.24 in the change. Pre-existing [2] came into
  scope with the decision that a release published to Pages always keeps its image tag and draft (decision 30).
- **Impacted:** the change's `tasks.md` (16.13-16.24 and the 16.10 precondition), `design.md` (decision 30 and
  decisions 8, 11, 12, 28 and 29) and the `guide-delivery` delta spec (the container image requirement, a
  version-ordering requirement and six scenarios), and this entry. The review hand-off was not changed.
- **Subagents used:** none.
- **MCP servers used:** none.
- **Workflow context used:** `openspec-explore` and `openspec-update-change`, with the delivered planning,
  quality-first, review-conduct and usage/model logging rules. Remote state was read with `gh` only. Two web
  searches covered artifact-name behaviour on re-runs.
- **Verification:** `openspec validate enhance-ci-and-repository-workflows --strict` passes. The tracker reads
  101/125.
- **Close-out:** Planning capture only. Implementation of 16.13-16.24 waits for approval of the apply phase.
  Nothing committed, pushed, dispatched, published or archived, and no issue or review was changed.

### Review repairs apply (16.13-16.26)

- **When:** 2026-10-28
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** Applied the review capture after the maintainer's apply approval. The maintainer added 16.25 during the
  run, and after the report 16.26 (the production-approval retry) and the review repairs in the proposal's finishing
  scope.
  - **Watch and digest:** watch pages and Champion core tests that content no longer names leave the state; a
    limitation with a current task names it instead of claiming a change; only open tasks are adopted.
  - **Documentation check:** the publication-order check refuses every Mermaid link form other than a named `-->`.
  - **Dependencies:** `rdflib` and `pyshacl` are pinned.
  - **Publication:** hand-offs, the production-approval summary and the catalogue's retry route name the documented
    deployment dispatch. The last root check compares live Pages with the root stamped in the staging site, and the
    resolve job lost its unused `pages: read`.
  - **Release flow (decision 30):** the production job runs only for tags; a superseded published release keeps
    its image tag and draft, and only the aliases follow precedence; release dispatches fail visibly on another
    branch; versions must increase.
  - **Local checks:** the public-content check skips untracked files in the runtime paths declared in
    `.agents/guide/surfaces.toml`, such as run hand-offs, which stay visible to Git.
- **Impacted:** `watch_sources.py`, `check_docs.py`, `assemble_pages.py` and `check_public_content.py`; `deployment.cjs`,
  `health-digest.cjs`, `release-artifact.cjs`, `release-version.cjs` and `prepare-release.cjs`; `deploy.yml`,
  `publish.yml`, `publish-image.yml`, `tag-release.yml` and `prepare-release.yml`; `.github/ci-catalogue.toml`,
  `.github/repository.toml` and `requirements-dev.txt`; `docs/deployment.md` and the regenerated
  `docs/ci-reference.md`; the affected Python and JavaScript tests; the change's proposal and tasks; this entry.
- **Subagents used:** none.
- **MCP servers used:** none.
- **Workflow context used:** `openspec-apply-change`, with the delivered planning, quality-first and usage/model
  logging rules and the native content and surface rules.
- **Verification:** each task's planted regression failed and the restored code passed:
  - prunes disabled;
  - the old limitation branch;
  - the old `-->` filter, which let eight link forms through;
  - a re-run hand-off, in publication and in the approval summary;
  - the resolve-time root comparison;
  - adoption without the open filter, which re-parented closed tasks 8 and 9;
  - the old production condition;
  - throwing on supersession;
  - the job-level dispatch condition;
  - a disabled version check;
  - an unfiltered public-content scan.

  The new pins were installed into a fresh environment from `requirements-dev.txt`.
- **Corrections:** The maintainer added 16.25 after the local suite failed on the review hand-off. Its first
  version gitignored `.agents/local_scratch/`; the maintainer pointed to that directory's README, which keeps
  hand-offs visible in `git status`, and reverted `.gitignore`. The check now skips only untracked files in the
  declared runtime paths. Finding 5's
  review mechanism was replaced by the documented deployment retry before implementation. The project `.venv`
  keeps Ruff 0.17.0 because the editor holds `ruff.exe`, so lint ran with the pinned 0.17.1 from a fresh
  environment.
- **Close-out:** `python scripts/check_all.py` passes 36/36 checks with the #116 review hand-off present,
  including `public-content`, the unit shards, browser groups, crate profiles, OpenSpec, generation, ownership and
  delivery. It passed after 16.25, after 16.26 and the proposal update, and again on the final tree after 16.25
  was reworked to keep the scratch area visible.
  Tasks 16.13-16.26 are complete (115/127). 16.1 waits for #116's hosted `quick` run; 16.10-16.12 and the
  earlier hand-offs need their approvals. Nothing committed, pushed, dispatched, published or archived, and no
  issue or review was changed.

### Delta spec sync

- **When:** 2026-10-28
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** At the maintainer's request (`openspec-sync-specs`), merged the change's two delta specs into the main
  specs while the change stays active. In `guide-delivery`, 7 modified requirements were replaced in place and 55
  added ones appended (126 requirements). In `guide-knowledge-base`, 5 were replaced and 3 added (55). No modified
  requirement dropped a main-spec scenario, and there were no removals or renames.
  Strict validation then rejected four modified requirements longer than 500 characters. Their text was
  tightened in the delta without changing a requirement, and the specs were synced again:
  - Humans judge correctness and tone;
  - Health and source-watch reports remain actionable;
  - Each release publishes a runnable container image;
  - Content addressed relative to the site, whose moved-address rationale stays in its "The guide moves" scenario.
- **Impacted:** `openspec/specs/fair-guide/guide-delivery/spec.md`, `openspec/specs/fair-guide/guide-knowledge-base/spec.md`,
  the change's two delta specs, and this entry.
- **Workflow context used:** `openspec-sync-specs`, with a scratch merge script.
- **Verification:**
  - A round trip of the unchanged main specs was byte-identical, and a second merge changed nothing.
  - Every synced block equals its delta; titles, Purpose and all other requirements are unchanged.
  - `npm run openspec:validate` (all items, strict) passes 6/6 with no warnings.
- **Close-out:** main specs synced; the change stays active until its remaining hand-offs and archive approval.
  Nothing committed or archived.
