# Defer clause text from the first download

- **When:** 2026-11-18
- **Agent / runtime:** Claude Code
- **Model / backend:** claude-opus-5-5
- **What:** Plan and implement the OpenSpec change `defer-clause-text`: ledger clause summaries move from the page's
  first download to the `standards` part, which already carries their guidance, so content work fits the 300 KB
  budget again; the clause records stay in the first download. The held-back NRP deposit-licence manual content
  (`dsw-nrp/eosc-fair-guide` issue 140) depends on it. Every page read of clause text was traced to a view that
  already waits for `standards`, so no view's parts changed.
- **Impacted:** `openspec/changes/archive/2026-11-18-defer-clause-text/` (proposal, delta spec for
  `fair-guide/guide-delivery`, design, tasks), `openspec/specs/fair-guide/guide-delivery/spec.md`,
  `scripts/build_crate.py`, `tests/test_languages.py`, `tests/page/check_languages.mjs` and this usage entry.
- **Close-out:** The change was archived on 2026-11-18 at
  `openspec/changes/archive/2026-11-18-defer-clause-text/`; PR
  [#191](https://github.com/dsw-nrp/eosc-fair-guide/pull/191) remains an open draft. The first download's
  headroom is 27,370 bytes (Czech) and 29,454 bytes (English), from 471 and 2,906 on `main`. The new unit test fails
  on `main`'s split; the cold-start page check fails, rather than hangs, when the explorer or a station stops waiting
  for `standards`; cold search finds a clause by a word only its text holds, in both languages. With the held-back
  deposit-licence content applied as a patch, the language tests, including the budget, and the content check
  pass. `npm run openspec:validate` passes 7 of 7 and all 36 repository checks pass in 233.8 seconds; the strict
  validation also passes after the delta was split and synced.
- **Corrections:** The operator directed archiving despite the draft, unmerged PR and the uncommitted task 3.4
  change. Verification then found the 687-character MODIFIED requirement would fail the main-spec 500-character
  limit; with operator approval the delta was split into a new ADDED "Deferred requirement text retains complete
  content and search" requirement plus the unchanged MODIFIED requirement, the main spec was synced, and the
  change archived.
