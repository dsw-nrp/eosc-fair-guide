# Defer clause text from the first download

- **When:** 2026-11-18
- **Agent / runtime:** Claude Code
- **Model / backend:** claude-opus-5-5
- **What:** Plan the OpenSpec change `defer-clause-text`: ledger clause summaries move from the page's first
  download to the `standards` part, which already carries their guidance, so content work fits the 300 KB budget
  again. The held-back NRP deposit-licence manual content (`dsw-nrp/eosc-fair-guide` issue 140) depends on it.
  Planning artifacts only; implementation awaits approval.
- **Impacted:** `openspec/changes/defer-clause-text/` (proposal, delta spec for `fair-guide/guide-delivery`, design,
  tasks) and this usage entry.
- **Close-out:** `openspec validate defer-clause-text --strict` and `npm run openspec:validate` pass. A read-only
  prototype on `main` measured the first download's headroom at 471 → 27,366 bytes (Czech) and 2,906 → 29,451
  bytes (English) with clause text deferred.
