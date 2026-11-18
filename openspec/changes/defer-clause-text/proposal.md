# Proposal

## Why

The page's first download is at its 300 KB budget: on `main` on 18 November 2026 the Czech page had 471 bytes of
headroom, and the English page 2,906. Every ledger clause's summary text loads up front, although only views that
already load the `standards` part show it. Content work is now blocked: the NRP deposit-licence manual's two
clauses and one advice item (issue 140 of `dsw-nrp/eosc-fair-guide`) add about 690 bytes to the Czech download and
fail the budget test.

## What Changes

- The text of every ledger clause moves from the first download to the `standards` part, which already carries
  the clauses' quoted guidance. The clause records themselves (identifier, source, principles, actor, kind,
  locator, status) stay in the first download, so references, counts and filters keep working.
- Views and search that show clause text wait for the `standards` part, as they already do for guidance; any that
  does not yet load it is added to the parts it waits for.
- A prototype on `main` measured the effect: the Czech first download gains about 26.9 KB of headroom (471 →
  27,366 bytes) and the English one about 26.5 KB (2,906 → 29,451 bytes).

Exclusions: the budget itself, the crate, the API and the published graph are unchanged; no content changes here.

Validation: the budget test passes with the held-back deposit-licence content applied; the page checks show clause
text wherever they did before, in both languages and from a cold start; the existing check that the core and the
parts together equal the crate keeps passing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-delivery`: "Deferred advice retains complete content and search" also defers ledger clause
  texts from the initial transport, with a scenario for a view that shows a clause before the part has loaded.

## Impact

- Code: the crate split in `scripts/build_crate.py`; the parts each view waits for in `assets/js/app.js`, if a
  consumer is found that does not load `standards` yet.
- Tests: `tests/test_languages.py` (budget and graph reconstruction), the page checks in `tests/page/`.
- Follow-up unblocked: the deposit-licence manual content on branch `agents/claude/deposit-licence-manual`.
