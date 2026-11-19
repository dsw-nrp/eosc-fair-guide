# Design

## Context

See proposal.md, Why. `split_crate` in `scripts/build_crate.py` divides the crate into the core, which every view
loads, and the parts in `PART_SCRIPTS`, which views load when they first need them. A part carries whole entities
or property patches for core entities. Ledger clauses are core entities today; only their `guidance` is patched in
from the `standards` part, and the clauses of the external standards (CoreTrustSeal, CDIF, FDO, FRSM) move there
whole. `VIEW_PARTS` in `assets/js/app.js` lists the parts each view waits for: the catalogue, the checks and the
explorer load `standards`, a station loads it, and search preloads it before giving complete results.

## Goals / Non-Goals

**Goals:**

- Restore room in the first download for content, measured per language by the existing budget check.
- Keep every view's output identical once its parts have loaded.

**Non-Goals:**

- Changing the budget or how it is measured.
- Splitting `standards` into smaller parts, or deferring other kinds of record.

## Decisions

**Patch the clause's `text` from `standards`, beside its `guidance`.** A clause stays a core entity carrying its
identifier, source, principles, actor, kind, locator and status, so references, counts by principle, catalogue
filters and identifier search work before the part loads. Only `text`, the bilingual summary, moves, through the
same property-patch path that `guidance` already uses. Alternative considered: moving whole clause entities to
`standards` as the external standards' clauses are; rejected because station and explorer counts and the
catalogue's filters read clause records before any part has loaded.

**Find consumers by their reads, then prove them by the page checks.** The implementation lists every page-code
read of a clause's text (the catalogue's clause entries, `FG.clauseEntry` on stations and in the explorer,
questions that take their text from a clause, the search index) and confirms the view that does the read waits
for `standards`. A view that does not is added to its `VIEW_PARTS` entry rather than loading the part ad hoc. The
existing page sweep, with each view opened cold, is the evidence that nothing shows an empty requirement.

**Keep the graph equality check as the guard for completeness.** The language tests already assert that the core
with its parts equals the crate; they keep passing unchanged, which shows no clause text is lost.

## Risks / Trade-offs

- [A view shows a clause before `standards` arrives] → the new cold-start scenario and the page sweep cover the
  catalogue entry, a station's basis and the explorer; a missed consumer appears as an empty requirement there.
- [Search before the part loads misses clause text] → search already waits for `standards` before complete
  results; its cold-search test gains a clause-text query.
- [`standards` grows by the moved text] → it loads on views that already show requirements; its size is reported
  by the build as today.

## Migration Plan

One pull request changes the split and any `VIEW_PARTS` entry. Saved answers and published data are unaffected,
because the crate and the API do not change. Rollback is a revert. The held-back deposit-licence content then lands
in its own pull request on top.
