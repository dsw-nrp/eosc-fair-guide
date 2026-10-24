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
