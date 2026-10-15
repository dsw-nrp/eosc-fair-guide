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

Use `npm ci`, `npm run openspec:validate` and `python scripts/check_all.py`. Inspect desktop and phone states in
both languages, keyboard and iframe operation, failed/deferred loads, exports and saved-result support. Check
actual runtime identities and source preservation, rather than merely comparing duplicate generated maps.

## Delivery

The candidate and exact remote payload are reviewed together. An operator checklist covers reviewed PR merges
and privileged App/settings work; a deployed-candidate acceptance explicitly authorizes alpha tagging and
publication. Verify source commit, artifact digest, versions, dates, production, preview and release assets.
Archive after completed delivery under a fresh instruction; the installed capability specs remain in place.

See [the release hand-off](../../../docs/release-handoff.md) for dispositions, remaining gates and receipts.
