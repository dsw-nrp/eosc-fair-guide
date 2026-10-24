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
