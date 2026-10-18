# Agent surfaces — 18 October 2026

- **When:** 2026-10-18
- **Impacted:** Approved native tooling continuation: authored rules/skill, vendor mirrors, mixed Codex reader,
  ownership/integrity checks, review facts and contributor documentation.
- **Request/approval:** Maintainer approved the reviewed delivery batch and continuation, then staged the delivered
  files. Native implementation follows the approved OpenSpec change; no remote operations were requested.
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** actual backend model id not exposed by the runtime
- **What:** Accepted the delivered receipt; migrated native content constraints without discarding their body;
  added native ownership sources, generator, receipt checks and guide-owned review facts.
- **Verification:** Settled `scripts/check_all.py` passes 29/29 checks in 166.0 seconds, including native
  generation, ownership, receipt integrity, public content, strict product OpenSpec, REUSE and browser checks.
  The unit run executes 387 tests with one Windows symlink-privilege skip; the other 14 native tooling
  regressions and 13 workflow tests pass. The real delivery merger and native generator preserve each other's
  actual Codex sections in an isolated copy. The original content-rule body is preserved.
  Full logs and reports are retained under `.cache/health-agent-surfaces-final/` and
  `.cache/agent-surfaces-check-all-final.log`; `.cache/agent-surfaces-final-receipt.json` summarizes coverage.
- **Delivery receipt:** The manifest verifies 129 complete files and eight delivered Codex sections. Dropped
  live/translation workflows have no remaining files; shared dependencies and the drafter remain. Hub inspection
  and planning now pass with no blockers, every bundle path identical and no same-name differences. During native
  editing the unstaged Codex region correctly triggered the dirty-overlap guard; the final staged state clears it.
- **Limits:** Hosted acceptance, publication, release and archive remain separately gated. Delivered assets remain
  read-only. Machine-local client context loading is not provisioned or inferred from file presence.
- **Close-out:** Local native tooling implementation was verified by the recorded run; the current review
  follow-up below requires its own fresh validation and approved delivery.

## Automation and tooling review follow-up

- **When:** 2026-10-18
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** actual backend model id not exposed by the runtime
- **What:** Implemented the approved PR review corrections and visible human tooling entrypoints.
- **Impacted:** Guide-owned ownership, correction loading, release-path policy, health publication,
  Copilot setup, native guidance, contribution documents and capability contracts.
- **Verification:** Focused ownership, correction, workflow, release and health tests pass. The publication
  probe loads/builds once rather than twice (1.043 s versus 1.342 s locally); this excludes the site build
  subprocess and hosted setup. The complete settled suite passes 29/29 in 177.6 seconds: 396 unit tests
  with one existing symlink-privilege skip, plus 67/67 browser cases with none skipped or pending.
  The initial 27/29 run is retained: formatting was corrected and the unchanged 60-ms concurrency fixture
  passed in isolation and the settled run; its timing sensitivity remains a stated limitation.
- **Close-out:** Local review follow-up complete. The separately approved upstream delivery was verified
  byte-for-byte and preserved the pre-apply index and native Codex region; native regeneration and receipt
  integrity pass. No staging, commit, push, posting, release or archive was performed by this session.
