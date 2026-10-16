# Initial alpha design and hand-off

## Context

The implemented system and its reasons are maintained in [the product design](../../../docs/design.md) and
[the content model](../../../docs/content-model.md). Those documents, the installed capability specs and source
code are sufficient grounding for team work from this repository.

## Decisions

- Static and portable: one source model serves local files, embedded use, hosted pages and machine-readable data.
- Guide identity is locally owned. Every normalized record has one primary `id`; imported records retain genuine typed `alternateIds`.
  The primary and frozen routing prefix remain independent
  of source IDs, names or URLs. External identities remain record metadata; ambiguous refresh joins require review.
- Catalogue addresses are emitted once; short kind/type codes do not replace readable UI categories.
- Before the first release, obsolete routes and alias tables are removed without compatibility copies.
- Advisory linking proposes specific, contextual edits and never changes prose or quotation text automatically.
- Potential test coverage, observed evidence and reader answers remain distinct.
- The final review covers architecture/data, bilingual text/source fidelity, UX/GUI/design and code hygiene.

## Validation

The browser-check continuation synchronizes hash navigation with the completed view and waits for the
search index's language parts. Installation and all browser entry points share the repository cache default
and respect an explicit browser-path override. Check groups retain per-script/case timings, explicit partial
coverage and failure screenshots, traces, route/heading/error records. A shared cross-process browser budget
prevents outer groups and inner pools from multiplying concurrency. The station matrix preserves all closed
and expanded guidance states while reusing navigation; the complete deterministic PR gate remains required.
Use measured scope/environment/revision receipts for optimization claims and keep live-service observations
separate. No publication, repository setting or remote operation follows automatically from local checks.

Use `npm ci`, `npm run openspec:validate` and `python scripts/check_all.py`. Inspect desktop and phone states in
both languages, keyboard and iframe operation, failed/deferred loads, exports and saved-result support. Check
actual runtime identities and source preservation, rather than merely comparing duplicate generated maps.

## Delivery

The candidate and exact remote payload are reviewed together. An operator checklist covers reviewed PR merges
and privileged App/settings work; a deployed-candidate acceptance explicitly authorizes alpha tagging and
publication. Verify source commit, artifact digest, versions, dates, production, preview and release assets.
Archive after completed delivery under a fresh instruction; the installed capability specs remain in place.

Posted follow-ups are maintained in the [repository issues](https://github.com/dsw-nrp/eosc-fair-guide/issues).
The temporary issue/release handoff documents were deliberately retired; delivery work uses issue receipts
and an explicitly reviewed payload rather than recreating a second draft queue.

## Browser-check verification receipt (16 October 2026)

The complete product suite passes 26/26 groups in 338.3 seconds on Windows with Node 24.19.0, Python 3.14
and the shared two-worker budget, including 328 Python tests, six runtime regressions, all 352 station states
and 40 bilingual PDF fixtures. Three fresh delayed-navigation/search regressions pass on their first attempts.
Case reports contain no missing, pending or skipped cases in the complete run; selected benchmark scopes remain
explicitly partial. Failure evidence retention is tested with a deliberately failing child process.

Representative trace trials take 28.55s with full DOM snapshots and 23.62s with action traces; identical view
shards take 57.07s with one worker and 37.19s with two. These paired trials share one source digest and built
input. They do not establish a hosted CI speedup: the full fixed-budget local run takes longer than the
199.5-second pre-change run on this higher-core workstation. All three validator checks remain in the gate;
hosted runtime and billed runner-minute effects remain unmeasured. Full trace snapshots remain opt-in via
`CHECK_TRACE_SNAPSHOTS=1`; default failures retain the action trace, PNG and HTML captures.

## Full-run scheduling correction (16 October 2026)

Local and CI defaults now share `scripts/check_policy.json`: four outer jobs in both profiles, four browser
slots locally and two in CI, with defaults capped by reported CPUs. CLI browser budgets override
`CHECK_BROWSER_WORKERS`, then the selected profile; npm/direct Node use the same policy. Each successful
build records actual profile/resources/budgets and built-input hashes in the health artifact's `execution.json`.

The declared complete-run comparison used four outer jobs and browser budgets 4/8/2, sequentially, with one
source identity and identical build hashes and required coverage. All passed 26/26 groups in 242.3/236.6/338.8s.
Four slots are selected: eight saves only 2.4% overall and increases CPU-heavy unit/validator contention.

The declared default repeat exposed a slot-owner liveness race and was stopped, preserving its failed runtime
log. A worker could release/reassign its slot and exit between the PID read and process probe. The allocator
now rechecks that the same dead owner remains recorded. A deterministic regression fails before the fix and
passes after it for both released/reassigned slots; genuinely abandoned slots still fail closed.

The corrected normal command, without concurrency flags, passes 26/26 groups in 236.7s, including 329 Python
tests, eight runtime tests, every required browser case, all 352 station states and 40 bilingual PDF fixtures.
Its built-input hashes and required coverage match the three controls; its source identity records the race
fix separately. Successful runs leave no slot owners or waiting tickets. These are first complete attempts
for each source/configuration; the failed intermediate repeat is retained rather than counted as success.

The selected local default is about 30% faster than the two-slot control, and remains about 19% slower than
the historical 199.5s unrestricted baseline. Hosted CI performance and billed minutes remain unmeasured.
The measurements justify retaining a simple four-slot local profile; no scheduler rewrite or extra CI lanes
were introduced. Ordinary verification runs the complete suite once. Failure traces/PNG/HTML and all profile
validators remain in the gate.
