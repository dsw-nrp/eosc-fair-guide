# Duplicate suggestions and fix

- **When:** 2026-10-20
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** exact backend model id not exposed by the runtime
- **What:** Verified the change, then implemented the user-authorized repairs for all five findings and
  the actual PR 82 duplicate failure. Extended the existing OpenSpec artifacts before implementation.
- **Impacted:** Duplicate suggestion/fix scripts, CI head identity and workflows, reserved identifiers,
  regression tests, the dated PR 82 re3data snapshot and curated link, registered provenance, maintainer
  documentation and changelog. Verification evidence is retained in regression tests and this usage entry.
- **Close-out:** Earlier repair pass: 41 OpenSpec tasks complete. Focused regressions pass 56 tests; strict OpenSpec validation
  passes 6/6; the final full local run passes 30/30 in 169.8 seconds, including 439 unit tests with one
  existing Windows skip. Reproduced PR 82's
  duplicate and conflicting-entity-ID failures, then verified the linked content passes both checks and
  builds one repository entity. Inspected the card in Czech and English on desktop, phone and print.
  Both ownership checks pass. The standalone verification report was removed at the maintainer's request.
  Hosted activation remains deferred under task 7.4. Existing staging was preserved;
  no commits, remote comments, pushes or archive were performed.

## Kilo session (exploration, capture and initial implementation)

- **When:** 2026-10-20
- **Agent / runtime:** Kilo (VS Code extension)
- **Model / backend:** e-infra-cz/deepseek-v4.1-flash-thinking
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** `openspec-explore`, `openspec-propose`, `openspec-apply-change`; delivered
  `aiscr-planning-core`, `aiscr-quality-first-execution`, `aiscr-usage-logging` and `aiscr-model-logging`
  rules; `npx openspec` for the pinned CLI.
- **What:** Investigated PR 82's duplicate and conflicting-entity-ID CI failure, captured the
  `duplicate-suggestions-and-fix` change, and implemented its initial scoped pass: structured duplicate
  suggestions and local `--fix`, aggregate failure diagnostics, trusted review-comment suggestions, the
  maintainer `/fix-duplicates` workflow and handler, reserved snapshot identifiers, documentation and tests.
  Recorded the working `npx openspec` invocation in `AGENTS.md` after the bare `openspec` command was
  refused by the agent allowlist.
- **Impacted:** `AGENTS.md`, `CONTRIBUTING.md`, `docs/content-model.md`, `docs/design.md`,
  `content/guide.toml`; `scripts/check_duplicates.py`, `scripts/check_ci.py`, `scripts/check_health.py`,
  `scripts/refresh_snapshots.py`, `scripts/fix_duplicates.py`; `.github/scripts/comment-summary.cjs`,
  `.github/workflows/checks.yml`, `.github/workflows/fix-duplicates.yml`; the change artifacts under
  `openspec/changes/duplicate-suggestions-and-fix/`; `tests/page/check_pr_comment.mjs`,
  `tests/test_check_ci.py`, `tests/test_health.py`, `tests/test_scripts.py`, `tests/test_workflows.py`;
  this usage entry.
- **Verification:** During this pass, `python scripts/check_all.py` passed 30/30 after the comment-length
  fixes; `npx openspec validate --all --strict` passed 6/6; `npx openspec --version`, `context --json`,
  `status` and `validate` were exercised; Ruff lint/format, the PR-comment Node test and the focused Python
  suites passed. The handler, publisher and workflow contracts are covered by local/fake tests. Hosted
  `/fix-duplicates` activation was not exercised; later final repairs and the 41-task close-out are recorded
  in the session entry above.
- **Corrections:** After maintainer feedback, replaced the bare `openspec` guidance with `npx openspec`
  (and the `npm run -s openspec:cli -- …` fallback) in `AGENTS.md`; added GitHub comment-length bounds for
  the `/fix-duplicates` success comment and the trusted review comment; and accepted option 2 to defer hosted
  activation to release preparation.
- **Limits / hand-off:** Hosted workflow activation, App-token execution and a real same-repository test PR
  were not exercised. Task 7.4 is recorded as accepted local/fake verification under option 2.
- **Close-out:** The initial pass was left uncommitted on `agents/kilo/duplicate-suggestions-and-fix`; no
  commit, push, pull request, merge, remote comment or archive was performed. The change and final
  verification were continued in the session above.

## Action registration and extracted-content validation repair

- **When:** 2026-10-20
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** exact backend model id not exposed by the runtime
- **What:** Registered the command-generated provenance action before validation and included the register
  update in the repair commit payload. The complete real-content regression also exposed missing authored
  attachments in the workflow archive; extraction now includes those files as data from the same head.
  Removed the standalone verification report as requested, retaining the earlier usage sessions.
- **Impacted:** Duplicate handler/workflow, registered-content and producer/consumer regressions,
  contribution/design/changelog guidance, existing OpenSpec artifacts and this usage entry.
- **Close-out:** Both strengthened happy-path tests failed before the registration repair; the real-content
  workflow regression failed before adding the validation attachments. All 11 command tests and the workflow
  contract test now pass, including preservation of existing/retired IDs and refusal of unrelated missing
  IDs. Strict OpenSpec validation passes 8/8; the full suite passes 30/30 in 168.8 seconds, including 441
  unit tests with one existing Windows skip. All 43 tasks are complete under the existing local/hosted
  distinction in task 7.4. The scoped repair is staged with the previous work; separate planning drafts
  remain unstaged. Corrected the three session-created usage filenames to include their 2026-10-20
  start date while retaining their session contents and staging scope. No commit, push or hosted mutation performed.

## Approved spec sync and archival

- **When:** 2026-10-20
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** exact backend model id not exposed by the runtime
- **What:** Following explicit maintainer approval, synced all six completed requirements into the two
  existing main capabilities and archived the completed change before preparing its implementation commit.
- **Impacted:** Main delivery and knowledge-base specs; the six unchanged planning files moved to
  `openspec/changes/archive/2026-10-20-duplicate-suggestions-and-fix/`; this usage entry.
- **Close-out:** All four artifacts and 43 tasks complete. Verified all archived file hashes, every synced
  requirement and scenario, preservation of both original main-spec byte prefixes, and canonical spec
  structure. Strict validation passes 7/7 after archival; ownership and delivered-integrity checks pass.
  Runtime verification remains the full 30/30 run recorded above. Hosted activation remains deferred
  under task 7.4. Separate planning drafts remain outside the implementation commit; no push authorized.


## PR #102 review, verification and consolidation

- **When:** 2026-10-20
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** exact backend model id not exposed by the runtime
- **What:** Implemented all eleven PR #102 review findings after approved apply: unique ownership and exact
  placement parity, atomic rollback, validated CI evidence and partial failures, protected refresh PRs,
  inert bot output and accurate post-commit failure guidance. Subsequent verification found two I/O gaps;
  explicit follow-up authorization covered rollback registration before cleanup and current-run upload
  admission. Strengthened success assertions cover the diff and complete provenance reminder.
- **Impacted:** Duplicate checker/handler, CI collector/upload workflow, trusted publishers, regression tests,
  maintainer documentation, settled changelog and this original OpenSpec change. The maintainer requested
  one change and one usage record: review scope is integrated into the existing archive sections, six
  requirement blocks and task ledger, with matching main specs; the redundant records are removed.
- **Close-out:** Initial review repair passed 114 focused tests and 30/30 checks in 167.3 seconds with 465
  unit tests; verification then passed 115 focused tests and reproduced the two I/O gaps. Both fixes passed
  118 focused tests and the final 30/30 suite in 192.6 seconds, including 468 unit tests with one existing
  skip. The success-assertion follow-up passed all 27 regression-file tests and rejected planted missing
  diff/reminder output. Strict validation, Ruff, hygiene and ownership checks passed; native generation
  changed zero files. Evidence remains in `.cache/health-harden-duplicate-repair-review/` and
  `.cache/health-harden-duplicate-repair-review-final/`. Temporary sandbox artifacts were cleaned up.
  All eleven findings and both later verification warnings are resolved; the combined ledger has 44
  completed tasks. Consolidation validation passes all five main specs and four archived task ledgers;
  direct strict validation of this archive's proposal and deltas has zero findings. All 44 scenario bodies
  are preserved, main/archive blocks match and unrelated requirements are unchanged. Hygiene, ownership,
  delivery integrity, REUSE and diff checks pass; runtime tests were not repeated for this record-only edit.
  Consolidation changes records/specs only and preserves original attribution, App
  constraints and the separately deferred hosted activation in task 7.4. No implementation edit, staging,
  commit, push, remote review write, merge or release is part of this consolidation.

## Kilo session: atomic refresh branch and local partial parity

- **When:** 2026-10-21
- **Agent / runtime:** Kilo (VS Code extension)
- **Model / backend:** e-infra-cz/deepseek-v4.1-flash-thinking
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** continued the interrupted Codex session from its local rollout transcript; the native
  `fair-guide-editor` routing, the delivered `aiscr-planning-core`, `aiscr-quality-first-execution`,
  `aiscr-usage-logging` and `aiscr-model-logging` rules, and `npm run -s openspec:validate` for the pinned CLI.
- **What:** Fixed the two review findings the interrupted session had left unresolved, with direct edits as the
  maintainer requested. `source-publisher.cjs` now reads the refresh branch head before the commit inventory and
  moves the branch through one atomic GraphQL `updateRefs` call whose `beforeOid` is that head (all zeros for an
  absent branch); a branch that moved or appeared is kept and reported as `moved` instead of being force-replaced.
  `check_all.py` now treats a partial child as a failure in its job row, health report and exit code exactly as the
  CI aggregate does, while an explicit `--only` subset whose selected checks complete stays partial and exits zero.
- **Impacted:** `.github/scripts/source-publisher.cjs`, `scripts/check_all.py`, `tests/page/check_source_publisher.mjs`,
  `tests/test_check_runner.py`, `docs/design.md`, `CHANGELOG.md`, the delivery spec and the archived change's
  delta and task ledger (new requirement "Refresh branches move only from the inspected head" plus the local-runner
  scenarios and tasks 8.10–8.11), and this usage entry.
- **Verification:** `node tests/page/check_source_publisher.mjs` passes the new assertions that the creation
  compares with the all-zero oid, that an update replaces exactly the inspected head, that a planted branch move
  keeps the newer head with no pull update or comment, and that a missing repository identity is refused. Focused
  Python suites pass: 49 runner/script/health tests, 27 duplicate-review tests and 13 CI tests. Strict OpenSpec
  validation passes 5/5, and Ruff lint and format pass. `python scripts/check_all.py --report-dir
  .cache/health-review-fixes-final` returns 25 of 30 in 166.7 seconds with `unit` and `helpers` (including the
  publisher check) passing.
  The five failures are not caused by these edits: `content` reports `datarepo` changed since the merge base
  `a38f70f` (committed 2026-10-21T00:32:35+02:00, after this pull request's provenance action, so the merged main
  requires a fresher paradata action); `agent-generation` and `public-content` report drift in files that are
  identical to `origin/main` and unchanged by this branch; `agent-ownership` and `sibling-delivery` flag the
  untracked Codex runtime scratch area in the workspace.
- **Close-out:** No commit, push, merge, remote write or release was performed. Hosted behaviour was not exercised:
  the App token path uses the documented `updateRefs`/`RefUpdate` contract against a local fake. Remaining items for
  the maintainer: decide whether the merged branch carries a fresh `datarepo` provenance action, resolve the
  `a38f70f` surface drift (`docs/agent-tooling.md` and the delivered skill text) on main, and treat or ignore the
  untracked Codex runtime scratch area outside the ownership map.
