# Evaluator mapping review runbook

- **When:** 2026-11-17
- **Agent / runtime:** Claude Code
- **Model / backend:** claude-fable-5-2
- **What:** Give the external-evaluator mappings an owner role, a six-month review cadence and review triggers, as
  issue 14 of `dsw-nrp/eosc-fair-guide` asks; the issue records who holds the role. A maintainer runbook linked from
  the maintainer landing page, the
  recorded decision that FAIR-Checker's reviewed identity stays its API version, and a browser test showing that a
  changed mapping changes only the suggestion. The review date lives in the runbook; no content field is added.
- **Impacted:** `docs/runbooks/review-evaluator-mappings.md` (new), `docs/ci.md`, `docs/design.md`, a comment in
  `content/live.toml`, `tests/page/check_providers.mjs` and this usage entry. No record, mapping, stored format or
  runtime behaviour changes.
- **Close-out:** `python scripts/check_docs.py` passes 38 documents and `npm run check:providers` passes with the new
  assertion. All 36 repository checks pass in 258.3 seconds; this entry was written afterwards and the documentation
  and agent-surface ownership checks were run again. No push or pull request is made before the maintainer approves
  the diff and the pull-request text.
