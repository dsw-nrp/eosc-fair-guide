# Tasks

## 1. Split

- [x] 1.1 In `split_crate` (`scripts/build_crate.py`), patch each core ledger clause's `text` from the `standards`
  part beside its `guidance`, keeping its other properties in the core; verify the language tests' graph equality
  check passes and a generated `kb-cs.js` holds no clause text.
- [x] 1.2 Extend `tests/test_languages.py` so it asserts that no clause in the core carries `text` and that each
  clause's text is in the `standards` part in both languages; verify the test fails on `main`'s split and passes
  with 1.1.

## 2. Consumers

- [x] 2.1 List every page-code read of a clause's text and the view or flow that does it; record the list in the
  pull request and confirm each waits for `standards`, adding it to `VIEW_PARTS` in `assets/js/app.js` where it
  does not; verify `npm run check:page` passes.
- [x] 2.2 Add a page check that opens a clause's catalogue entry, a station whose basis cites clauses, and a
  principle in the explorer from a cold start with `standards` delayed, in both languages, and finds the clause
  text drawn after it arrives; verify it fails when the view is removed from waiting for `standards` and passes
  with it.
- [x] 2.3 Add a cold-search case for text that appears only in a clause's summary; verify complete results include
  the clause.

## 3. Budget and integration

- [x] 3.1 Run the budget measurement on the branch and record each language's headroom in the pull request; verify
  both are at least 25 KB.
- [x] 3.2 Apply the held-back content of `agents/claude/deposit-licence-manual` to a scratch copy of the branch and
  run `python -m unittest tests.test_languages`; verify the budget test passes, then discard the scratch copy.
- [x] 3.3 Run `npm run openspec:validate` and `python scripts/check_all.py`; verify all checks pass.
- [ ] 3.4 **Hand-off (maintainer):** review and merge the pull request.

## Workflow follow-up

- Rebase `agents/claude/deposit-licence-manual` on the merged change and open its pull request.
- Archive the change after merge, syncing its delta into `openspec/specs/fair-guide/guide-delivery/spec.md`.
