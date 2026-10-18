# Swagger deployment-check navigation wait - 18 October 2026

- **When:** 2026-10-18
- **Agent / runtime:** Kilo Code
- **Model / backend:** e-infra-cz/deepseek-v4.1-flash-thinking
- **What:** Repaired the deployment check after Playwright 1.64.1. Main-push run 39118444930 passed
  28/29 checks but timed out at `tests/page/check_deployment.mjs:95`: the Swagger Execute click
  completed, then the run waited for a scheduled navigation that never cleared. An isolated 1.64.1
  diagnostic passes locally, and the check already waits for the API response separately, so the
  click now uses `noWaitAfter: true` instead of waiting for that unrelated navigation.
- **Impacted:** `tests/page/check_deployment.mjs`; the deployment check contract is unchanged.
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** change `eosc-fair-guide`; `fair-guide-editor` conventions
- **Verification:** The hosted failure was read from run 39118444930's staging log; the local 1.63
  reproduction passes at `.cache/failure-39118444930-repro.log`, and the isolated 1.64.1 diagnostic
  is `.cache/investigation-39118444930/new-runtime.log`. The focused deployment check passes three
  consecutive runs with 1.64.1 at 15.79, 15.22 and 15.20 seconds. The complete suite passes 29/29 in
  185.3 seconds with the health receipt under `.cache/health/`.
- **Close-out:** Hosted verification remains pending delivery and a new deployment run. No staging,
  commit, push, branch switch, workflow dispatch, release or archive was performed.
