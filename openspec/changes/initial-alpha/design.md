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

## Reader corrections, payload headroom and effective CI

### Context and evidence (16 October 2026)

This continuation is task group 4, before human delivery in section 2. It supersedes the earlier scheduling
conclusion only where the hosted evidence below supports it; earlier verification receipts remain historical.
The maintainer approved planning capture, not implementation. The group includes the public-content/history
audit and initial-state provenance consolidation as release prerequisites.

The catalogue's letter boxes align, but their glyphs sit 2.34-6.77 px left of centre in the observed layouts:
the shared inline-flex button rule lacks horizontal centring. The About credits table inherits 1.2rem/19.2px
from a dangling `.credits,` before the profile-heading selector instead of the shared small table style.
Running-summary group SVGs are deliberately decorative; the list has a group name but the isolated mark has
no title. The icon helper accepts a class, not a title, so its wrapper must carry the translated title.

The report's overview has FAIR and native-block distributions, but no path-step distribution. Its detailed
answers use a separate grouping helper, which prefers blocks and otherwise follows the Answers choice.
Existing tests verify detailed groups without verifying the selected report overview. This explains why a
dataset can show path-grouped answers while its overview still shows FAIR; FIP, gate and maturity share the gap.

Current source measures 300.55 KiB Czech and 297.97 KiB English before interaction against the 300 KiB budget.
An in-memory transport-partition probe moving 232 L1-L3 text/description fields estimates 284.18/281.89 KiB,
before the new loader/configuration overhead. This is a candidate measurement, not implemented output.

Hosted run [38935902112](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/38935902112), at
`c6c4d6448d83a5d392e236fb42ade4ab9caf042e`, passes 26/26 groups in 673.1 seconds, with about 61 seconds
of installation. Recorded resources are four CPUs, four outer jobs and two shared browser slots. Group times
overlap and include queuing: page 631.3s, final 482.3s, helpers 425.6s, assessment 359.3s, profile 198.6s and
unit 154.4s. One iframe case spends 126.16s waiting and 0.53s active; a reflow case spends 56.96/1.87s.
These are evidence of contention and coarse slot occupancy, not permission to remove the cases.

The pinned axe Playwright adapter injects axe for each audit and creates a blank finishing page. A frame-free
station probe compares the original audit with direct reuse of the same 4.13.0 engine and WCAG tags: closed
804/339ms, expanded 673/292ms, and a planted unnamed-button failure 676/345ms. Normalized rule/node outcomes
match across violations, incomplete, passes and inapplicable results; both catch the planted failure. These
three local states establish a promising direction, not complete parity or a hosted speedup.

### Decisions and alternatives

1. **One grouping choice across Answers and Report.** Both views expose the switch. Dataset offers FAIR/path;
   other checks offer native blocks, FAIR and path wherever mapped. The same selected grouping controls the
   question list, running summary, report distributions and detailed answers; existing simultaneous report
   breakdowns become alternatives. Retain a compatible choice between views, with native blocks the default
   where present and FAIR otherwise. Native frameworks, criterion identities and answer meaning remain intact.
   An independent report preference or an always-added path section would leave contradictory presentation.
   Keep the switch reachable with collapsed summaries and on phones, without duplicate control IDs. Shared
   previews and print use the same presentation. Group labels have translated names and icon titles.
2. **Keep counting semantics explicit.** Path/block groupings cover the selected questions once, retaining an
   Other group for missing mappings. FAIR overview distributions retain their intentional multi-area counting,
   overlap explanation and count of questions without a FAIR principle. Question lists and chip navigation
   retain one occurrence per question. Scope, NRP-provided items, evidence, answer ownership and extended-mode
   behaviour are independent of presentation. No grouping introduces an overall score or an export format bump.
3. **Defer advice details through existing property patches.** Retain core structure and L0 text, move L1-L3
   text/description into a classic-script part, and load it for station rendering and complete search indexing.
   Keep the crate/API bilingual and unchanged in meaning. Check reconstruction across language/part load orders,
   file/iframe access, cold links, failed loads and retry. Search readiness must include this part, extending
   the repaired partial-index guard. Aim near 285 KiB while keeping the 300 KiB ceiling; report actual overhead.
   Raising the budget or shaving only the 0.55 KiB excess gives no useful headroom. Removing catalogue identity
   mappings risks routing/search, and moving arbitrary view-code tails crosses hidden runtime dependencies.
4. **Reduce repeated audit setup with a guarded fast path.** Reuse a pinned axe engine only for frame-free
   whole-document cases after paired parity checks with the same full-document context and policy. Compare
   normalized rule/check/node outcomes, including seeded failures, dynamic navigation and expanded guidance.
   Retain the original adapter for documents with frames and scoped audits; unknown cases or a mismatch fall
   back. Do not enable legacy mode globally, omit navigation from audits or reduce the station/state matrix.
5. **Separate CPU and browser workloads in CI.** One checked build feeds a CPU/unit/all-profile lane and two
   balanced browser partitions from one maintained inventory. Every lane verifies actual checked source and
   build hashes. Distinguish the checked merge revision from the PR head used for review publishing. Preserve
   read-only untrusted-PR checks, pinned actions, the required aggregate status and health/API/preview consumers.
   The collector runs on failures and rejects missing, duplicate, wrong-revision, blocked or incomplete work;
   passing lane subsets cannot independently claim complete health. Keep the ordinary local full-run command.
   More workers on the same four CPUs retains contention; separate runners trade shorter elapsed time for
   setup/artifact overhead and potentially more runner minutes. Measure both before claiming efficiency.

### Execution, risks and verification

Implement only after fresh apply approval, in this order: UI corrections and focused visual/regression checks;
advice transport and reconstruction/search checks; paired audit proof and collector failure tests; the public-content/provenance audit;
then one complete settled local suite. Prepare one hosted acceptance against the recorded 673.1-second baseline
after separate remote authorization. A roughly five-minute verification target is an aim, not a result or a
reason to retry failures into success. Stop on failure, diagnose from retained evidence and rerun only what a
repair invalidates before final acceptance. Do not repeat the 4/8/2 concurrency experiment.

Keep all required jobs/cases, 352 closed/expanded station states, 40 PDF fixtures, three validator profiles,
source-preservation and deterministic checks, adding the targeted UI/load/collector regressions. Verify Czech
and English at desktop/phone widths, empty/partial/saved check states, selected report overviews, unmapped
questions, shared previews, print and keyboard focus. Reconcile coverage IDs rather than just totals.

The public-content/provenance audit remains a release prerequisite: audit current source and local commit messages without printing
sensitive matches, preserve attributable evidence of historical exposure, prepare local fixes and require a
fresh order for any history rewrite. Replace granular provenance with the initial-state action under the
existing one-action-per-PR default, preserving truthful people, instruments, sources and produced-entity
coverage; align the requirement, content-model documentation and both editing-skill copies during apply.

Planning capture changes only this active change. Installed capability specs, runtime, workflows, content and
skill copies are updated during separately approved implementation. Validate the OpenSpec tree and public-copy
privacy, retain a source/build/coverage receipt and leave publication and archive under their existing gates.
