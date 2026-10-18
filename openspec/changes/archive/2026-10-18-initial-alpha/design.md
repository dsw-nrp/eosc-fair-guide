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

The automation and tooling review follow-up protects authored/runtime paths from native generation, uses
locked Copilot dependencies, validates exactly-once snapshot corrections through the shared content error
contract, and validates release-file selection against one shared structured policy before reads or writes.
Health publication reuses one content/crate context while retaining each snapshot's actual outcomes. The
tooling guide is the visible human entrypoint from both README languages and CONTRIBUTING. Delivered
workflow corrections arrive through approved upstream delivery; native sources retain separate ownership.
The local build marker remains a repeat-build guard; the pinned Pages archive excludes hidden files by
default. Hosted artifact inspection and publication remain separately authorized acceptance work.

The candidate and exact remote payload are reviewed together. An operator checklist covers reviewed PR merges
and privileged App/settings work; a deployed-candidate acceptance explicitly authorizes alpha tagging and
publication. Verify source commit, artifact digest, versions, dates, production, preview and release assets.
Archive after completed delivery under a fresh instruction; the installed capability specs remain in place.

Posted follow-ups are maintained in the [repository issues](https://github.com/dsw-nrp/eosc-fair-guide/issues).
The temporary issue/release handoff documents were deliberately retired; delivery work uses issue receipts
and an explicitly reviewed payload rather than recreating a second draft queue.

