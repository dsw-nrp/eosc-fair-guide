# Defer clause text from the first download

- **When:** 2026-11-18
- **Agent / runtime:** Claude Code
- **Model / backend:** claude-opus-5-5
- **What:** Plan and implement the OpenSpec change `defer-clause-text`: ledger clause summaries move from the page's
  first download to the `standards` part, which already carries their guidance, so content work fits the 300 KB
  budget again; the clause records stay in the first download. The held-back NRP deposit-licence manual content
  (`dsw-nrp/eosc-fair-guide` issue 140) depends on it. Every page read of clause text was traced to a view that
  already waits for `standards`, so no view's parts changed.
- **Impacted:** `openspec/changes/defer-clause-text/` (proposal, delta spec for `fair-guide/guide-delivery`, design,
  tasks), `scripts/build_crate.py`, `tests/test_languages.py`, `tests/page/check_languages.mjs` and this usage entry.
- **Close-out:** Eight of nine tasks are done; 3.4 is the maintainer's review and merge. The first download's
  headroom is 27,370 bytes (Czech) and 29,454 bytes (English), from 471 and 2,906 on `main`. The new unit test fails
  on `main`'s split; the cold-start page check fails, rather than hangs, when the explorer or a station stops waiting
  for `standards`; cold search finds a clause by a word only its text holds, in both languages. With the held-back
  deposit-licence content applied as a patch, the language tests, including the budget, and the content check
  pass. `npm run openspec:validate` passes 7 of 7 and all 36 repository checks pass in 233.8 seconds; this entry was
  written afterwards and the documentation and agent-surface ownership checks were run again.
