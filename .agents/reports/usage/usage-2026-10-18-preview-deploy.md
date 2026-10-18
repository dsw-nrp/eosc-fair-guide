# Preview deployment condition - 18 October 2026

- **When:** 2026-10-18
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** exact backend model id not exposed by the runtime
- **What:** Prepared the requested fix against `main` for the skipped Pages publication in run 39116471368.
  The deploy job explicitly tolerates a skipped optional production ancestor, requires successful assembly
  and respects cancellation. A workflow regression fails on the original missing condition.
- **Impacted:** `.github/workflows/deploy.yml` and `tests/test_workflows.py`; existing preview-delivery contract.
- **Close-out:** All 15 workflow tests pass after the regression failed on the original missing condition.
  Native full validation passes 29/29 in 200.2 seconds, including 397 unit tests with one existing Windows
  symlink-privilege skip. Logs and the final receipt are `.cache/preview-deploy-check-all.log` and
  `.cache/health-preview-deploy/`. No agent staging, commit, push, branch switch or hosted dispatch was
  performed; publication requires the maintainer's subsequent delivery and deployment run.
