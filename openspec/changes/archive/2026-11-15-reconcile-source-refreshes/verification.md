# Verification Report: reconcile-source-refreshes

Verified on 2026-11-15 using `openspec-verify-change`, against commit `58e54f6bd097f4517ce49e6e32d941d88fb059b8` on
`agents/codex/reconcile-source-refreshes`. Planning is repo-local, schema `spec-driven`.
The CLI-selected proposal, all three delta specs, design and complete task file were read. No tracked artifact
is unavailable or intentionally skipped. The apply state is context, not the basis for the verdict below.

Archival reference maintenance (2026-11-16): source paths within this change now name their archive location.
The verification date, verified commit and historical line references remain unchanged. R11 explicitly identifies
its local manual-probe receipt; the unrelated committed page-check citation has been removed. These reference
corrections do not represent a new execution of the original verification.

## Summary

| Dimension | Status |
| --- | --- |
| Completeness | 51/51 tasks complete; implementation evidence found for 17/17 ADDED or MODIFIED requirements. |
| Correctness | 17/17 requirements mapped; all 50 scenarios have implementation and test/probe evidence. |
| Coherence | Design decisions and project code patterns followed; no contradictions found. |

There are no REMOVED or RENAMED requirements. Removal/rename baseline checks are not applicable. No applicable
verification check is skipped or marked not verified. Scenario evidence includes a fresh direct browser probe
for contextual glossary navigation; this is distinguished from committed regression tests below.

## Checks and evidence

- Fresh strict validation: `npm run openspec:validate`, 7/7 items passed.
- Fresh focused Python verification: 153 tests passed on Python 3.14, spanning identity allocation, inferred
  reservations, semantic record distinctions, favicon integrity/public HTTPS, language partitioning, named agents
  and NKR reconciliation. No skipped tests, failures or errors.
- Fresh Node verification: all 21 runtime tests passed, including independent UI/document revision mismatch,
  transactional part acceptance, corrected Retry, query/fragment preservation and single-flight reuse.
- Fresh contextual browser probe: FIP and FER links on About each open the intended glossary entry in Czech and
  English at 320 px, with no external requests or page errors (four navigation cases).
- Fresh source fidelity: eight comparisons against the four original PR commits pass. Native fields, snapshot
  headers/retrieval dates and genuine unique typed source identifiers are exact outside Guide-owned metadata.
- Complete native acceptance on this exact commit is retained from the conflict-repair run: 36/36 checks passed
  in 232.9 seconds against main `38bb9be94465e9bdd0a753eee1e6d72e752aa92e`. The stored health report records
  all 36 required jobs plus the build as passed. It covers browser, API/profile, accessibility, reconstruction,
  source freshness, REUSE, formatting and documentation checks. This verification reuses that exact-head result.
- Required hosted `checks` passed on this exact head:
  [Guide checks and health report](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43766677126).
  [dsw-nrp/eosc-fair-guide#181](https://github.com/dsw-nrp/eosc-fair-guide/pull/181) remains open and conflict-free;
  historical cohort publications and head read-backs are retained.
- Initial downloads remain 307,123 gzip bytes in Czech and 304,722 in English, below 307,200 in each language.
- The Python 3.11 focused checks and real favicon acquisition from implementation remain historical evidence;
  they were not rerun or presented as new acquisitions during verification. The current source, assets and
  consumer code retain the reviewed implementation.
- Retained desktop/320 px, Czech/English, screen/print and HTTP/file/iframe visual evidence was inspected and
  representative images sampled again: CLARIN's expanded source disclosure, About credits and startup Reload.
  No visual defect was found. This report does not count historical captures as freshly generated screenshots.

Evidence receipts are under `.cache/reconcile-source-refreshes/openspec-verification/` and
`.cache/reconcile-source-refreshes/pr181-main-reconciliation/`. These are local diagnostic receipts; this
maintained report preserves the findings independently of cache retention. The implementation was not edited.

## Task completion

The authoritative apply response reports task tracking configured, 51 readable descriptions, 51 complete and
zero remaining. No unavailable tracking files are reported. Completion was cross-checked against these groups:

| Tasks | Count | Evidence |
| --- | ---: | --- |
| 1.1–1.6 Identity/source reconciliation | 6 | R15–R17; exact source comparisons; identity-review.md dispositions. |
| 2.1–2.2 Registry classification | 2 | R17, before/after FAIRsharing/NMA graph regression. |
| 3.1–3.3 About/footer credit | 3 | R12, keyboard/credit/print checks and unchanged attribution semantics. |
| 4.1–4.5 Favicon eligibility/outcomes | 5 | R01–R08/R13; actual manifest, integrity and coverage; retained acquisition/visual evidence. |
| 5.1–5.3 Deferred detail and size | 3 | R14/R09; exact bilingual reconstruction, budget and cold-load browser matrix. |
| 6.1–6.3 Integrated delivery | 3 | Exact-head full local/hosted acceptance, source/patch receipts and separately reviewed PR stack. |
| 7.1–7.3 Glossary integration | 3 | R11; ten placement/omission decisions, eight contextual terms, bilingual references and reader action. |
| 8.1–8.7 First review remediation | 7 | Deferred entry actions, atomic publication, legacy route inference, citation carriers and review-r1.md. |
| 9.1–9.4 Second review remediation | 4 | Owned stage recovery, Python floor evidence and review-r2.md. |
| 10.1–10.9 Consolidated observations | 9 | Inferred agents, explicit set integrity, contained paths, pinned HTTPS and transactional revisions. |
| 11.1–11.6 Third review remediation | 6 | Recursive consumer revisions, independent document expectation, four URL-helper consumers, Reload and CGNAT tests. |

Runtime/source prerequisites subsequently landed through human squash merges. The conflict repair at this
verified head preserves the reviewed reader tree, adds main ancestry and removes an automatically duplicated
test method. The independent reader provenance action remains available and passes freshness against main.

## Requirement implementation mapping

### R01: Favicon integrity requires an explicit asset set

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-delivery/spec.md:3` (ADDED Requirements).

Implementation: `scripts/vendor_favicons.py:643`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| The recorded asset directory disappears | `tests/test_favicons.py:188` | Covered |
| A deliberate prune records no remaining icons | `tests/test_favicons.py:188` | Covered |

### R02: Favicon work files stay inside their owned directory

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-delivery/spec.md:21` (ADDED Requirements).

Implementation: `scripts/vendor_favicons.py:477`, `scripts/vendor_favicons.py:548`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| A fixture host contains Windows path separators | `tests/test_favicons.py:205` | Covered |

### R03: Favicon acquisition reaches only validated public HTTPS destinations

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-delivery/spec.md:33` (ADDED Requirements).

Implementation: `scripts/public_https.py:79`, `scripts/public_https.py:106`, `scripts/public_https.py:167`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| A public name resolves to public and private addresses | `tests/test_public_https.py:97` | Covered |
| An HTTPS response redirects through HTTP | `tests/test_public_https.py:207` | Covered |
| Shared CGNAT space is classified as global by a host interpreter | `tests/test_public_https.py:29` | Covered |

### R04: Favicon connections pin validated public addresses

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-delivery/spec.md:55` (ADDED Requirements).

Implementation: `scripts/public_https.py:118`, `scripts/public_https.py:144`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| DNS changes after validation | `tests/test_public_https.py:126`, `tests/test_public_https.py:140`, `tests/test_public_https.py:153` | Covered |

### R05: Favicon publication preserves a recoverable verified set

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-delivery/spec.md:66` (ADDED Requirements).

Implementation: `scripts/vendor_favicons.py:513`, `scripts/vendor_favicons.py:493`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| Publication stops between directory replacements | `tests/test_favicons.py:330`, `tests/test_favicons.py:317` | Covered |
| A hard stop leaves an abandoned stage | `tests/test_favicons.py:237`, `tests/test_favicons.py:261` | Covered |

### R06: Favicon acquisition has dated outcomes

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-delivery/spec.md:87` (ADDED Requirements).

Implementation: `scripts/vendor_favicons.py:548`, `scripts/vendor_favicons.py:397`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| A host has no usable favicon | `tests/test_favicons.py:582` | Covered |
| A host cannot be reached | `tests/test_favicons.py:582` | Covered |
| A usable image is acquired | `tests/test_favicons.py:582`, `tests/test_favicons.py:451` | Covered |

### R07: Failed favicon refresh preserves verified assets

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-delivery/spec.md:115` (ADDED Requirements).

Implementation: `scripts/vendor_favicons.py:430`, `scripts/vendor_favicons.py:548`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| A previously available site times out | `tests/test_favicons.py:542` | Covered |
| Only infrastructure marks are refreshed | `tests/test_favicons.py:486` | Covered |

### R08: Favicon validation reports integrity and coverage honestly

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-delivery/spec.md:135` (ADDED Requirements).

Implementation: `scripts/vendor_favicons.py:643`, `scripts/vendor_favicons.py:734`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| An observation is malformed | `tests/test_favicons.py:612` | Covered |
| Content adds a host that has never been collected | `tests/test_favicons.py:612` | Covered |
| Collection still has failed attempts | `tests/test_favicons.py:582`, `tests/test_favicons.py:612` | Covered |

### R09: Browser data belongs to one compatible build revision

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-experience/spec.md:3` (ADDED Requirements).

Implementation: `scripts/build_crate.py:5422`, `assets/js/core.js:18`, `assets/js/core.js:143`, `assets/js/core.js:89`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| A cached part comes from another build | `tests/runtime.test.mjs:66`, `tests/page/check_revisions.mjs:150` | Covered |
| Retry receives corrected matching data | `tests/runtime.test.mjs:72`, `tests/page/check_revisions.mjs:150` | Covered |
| The initial files belong to different builds | `tests/runtime.test.mjs:90`, `tests/page/check_revisions.mjs:141` | Covered |
| Both initial data files are equally stale | `tests/runtime.test.mjs:12`, `tests/page/check_revisions.mjs:121` | Covered |
| A nested consumer module changes | `tests/test_languages.py:33` | Covered |
| A script path already contains a query and fragment | `tests/runtime.test.mjs:23`, `tests/page/check_revisions.mjs:108` | Covered |

### R10: Entry actions wait for their deferred evidence

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-experience/spec.md:48` (ADDED Requirements).

Implementation: `assets/js/selfcheck.js:729`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| A maturity action starts while questions data is delayed | `tests/page/check_languages.mjs:64` | Covered |

### R11: Explain terms where they help the reader

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-experience/spec.md:61` (ADDED Requirements).

Implementation: `content/pages.toml:47`, `content/stations/01-plan.toml:243`, `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/identity-review.md:60`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| A community records its implementation choices | Manual browser probe, local receipt only: `.cache/reconcile-source-refreshes/openspec-verification/glossary-probe.mjs:18` (four Czech/English navigations at 320 px; no committed glossary-link test) | Covered by manual probe |

### R12: Credit for content and compilation

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-experience/spec.md:76` (MODIFIED Requirements).

Implementation: `assets/js/views.js:1407`, `assets/js/views.js:1467`, `assets/js/views.js:397`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| Who wrote the content | `tests/page/check_page.mjs:3097` | Covered |
| Roles on the about page | `tests/page/check_page.mjs:3109`, `tests/page/check_page.mjs:1489` | Covered |
| A content contributor is not a software author | `tests/page/check_page.mjs:1486`, `tests/page/check_page.mjs:1491` | Covered |

### R13: Own-site favicons cover eligible resource kinds consistently

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-experience/spec.md:108` (ADDED Requirements).

Implementation: `scripts/build_crate.py:643`, `scripts/vendor_favicons.py:130`, `assets/js/catalogue.js:404`, `assets/js/core.js:319`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| CoreTrustSeal has a usable favicon | `tests/test_favicons.py:371`, `tests/page/check_page.mjs:2500` | Covered |
| A document is identified through a resolver or shared platform | `tests/test_favicons.py:49` | Covered |
| An eligible site has no usable mark | `tests/test_favicons.py:582`, `tests/page/check_page.mjs:2493` | Covered |
| NKR alone supplies a repository's site | `tests/test_favicons.py:371` | Covered |
| A repository has only its NKR record address | `tests/test_favicons.py:422` | Covered |

### R14: Registry detail loads when its reader task needs it

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-experience/spec.md:148` (ADDED Requirements).

Implementation: `scripts/build_crate.py:5395`, `scripts/build_crate.py:5118`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| First visit with populated NKR data | `tests/test_languages.py:131`, `tests/test_languages.py:348` | Covered |
| Direct repository check from a local file | `tests/page/check_languages.mjs:148` | Covered |
| Search needs a deferred keyword | `tests/page/check_languages.mjs:144` | Covered |
| The required local data fails to register | `tests/page/check_languages.mjs:722`, `tests/page/check_languages.mjs:436` | Covered |

### R15: New snapshot identifiers are reserved across the Guide

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-knowledge-base/spec.md:3` (MODIFIED Requirements).

Implementation: `scripts/catalogue_identity.py:186`, `scripts/catalogue_identity.py:365`, `scripts/refresh_snapshots.py:923`, `scripts/refresh_snapshots.py:981`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| A new record would reuse a curated identifier | `tests/test_scripts.py:1987`, `tests/test_scripts.py:1996` | Covered |
| A new record would reuse a retired identifier | `tests/test_scripts.py:2011`, `tests/test_catalogue_identity.py:164` | Covered |
| A glossary term shares a word with software | `tests/test_catalogue_identity.py:155`, `tests/test_registry_records.py:266` | Covered |
| A glossary term shares a word with a page | `tests/test_catalogue_identity.py:155`, `tests/test_registry_records.py:266` | Covered |
| KNAV describes the existing re3data resource | `tests/test_catalogue_identity.py:168`, `tests/test_registry_records.py:266` | Covered |
| NKR describes the existing DataRepo repository | `tests/test_registry_records.py:266` | Covered |
| A source match is ambiguous | `tests/test_catalogue_identity.py:168`, `tests/test_scripts.py:1973` | Covered |
| An identifier contains a genuine published version | `tests/test_catalogue_identity.py:155`, `tests/test_catalogue_identity.py:56` | Covered |
| An established source row joins a curated thing | `tests/test_catalogue_identity.py:56` | Covered |
| Similar labels describe different things | `tests/test_registry_records.py:34`, `tests/test_registry_records.py:45`, `tests/test_registry_records.py:56`, `tests/test_registry_records.py:65` | Covered |
| A reviewed software classification differs from a native repository label | `tests/test_registry_records.py:45`, `tests/page/check_page.mjs:3069` | Covered |

### R16: Refresh reserves inferred organisation addresses

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-knowledge-base/spec.md:87` (ADDED Requirements).

Implementation: `scripts/build_crate.py:2345`, `scripts/refresh_snapshots.py:923`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| An incoming organisation competes with an inferred agent | `tests/test_inferred_reservations.py:17`, `tests/test_inferred_reservations.py:33`, `tests/test_inferred_reservations.py:39` | Covered |

### R17: Dashboard registry classification survives source reclassification

Spec: `openspec/changes/archive/2026-11-15-reconcile-source-refreshes/specs/fair-guide/guide-knowledge-base/spec.md:101` (ADDED Requirements).

Implementation: `scripts/build_crate.py:2454`, `scripts/build_crate.py:2646`.

| Scenario | Test/probe evidence | Result |
| --- | --- | --- |
| FAIRsharing and NMA become registries in the Dashboard | `tests/test_registry_records.py:94` | Covered |

## Design adherence and code patterns

- Kind/scope/address reservations and reviewed joins precede allocation. Exact source handles remain typed;
  unresolved collisions fail before replacement, and meaningful published digits are not banned. The Git,
  provenance, re3data and DataRepo cases retain one thing per intended identity with source records underneath.
- Specific licences, licence overviews/publishers, software/deployments and identifier mechanisms/providers stay
  distinct. CLARIN's imported instance wording and verification remain attributed source claims, without a
  software-level certification or deposit capability. Native descriptions are not silently rewritten.
- Registry ontology classification stays on catalogue records. The before/after test checks types, identities,
  reviews and deposit meaning as well as the visible label.
- Existing questions/fips/api parts retain complete data while initial payloads stay within budget. The four
  script loaders share FG.scriptUrl. Initial data matches the document, deferred acceptance waits for both
  contributions, Retry refetches only rejected data and startup offers actionable Reload.
- Both citations use existing renderers on About. All six credit roles, ORCID behavior, version/licence/funding
  and the editor/source-author distinction remain; footer navigation opens the credits with keyboard focus.
- Favicon eligibility comes from one validated resource-type policy. Collection uses reconciled winning sites,
  including NKR-only records; shared-platform addresses retain the fallback. Observations use the existing
  generated manifest and do not add maintenance arrays to initial browser data.
- Favicon publication stages/verifies a complete set and preserves recoverable previous assets. Work paths are
  contained before image writes; cleanup rejects links/reparse points using Python-3.11-compatible inspection.
  Public-only HTTPS validates all answers/hops, pins numeric connections/peers, keeps TLS verification and
  excludes proxies. Other source-refresh transports retain their approved separate scope.
- Authored TOML, generated output boundaries, standard-library Python and the FG classic-script namespace remain
  consistent with the repository. No new dependency, backend, saved-answer format or external load request is introduced.

## External limits and separate hand-offs

The verified offline favicon manifest reports 258 eligible identities and 213 usable assets. Latest attempts
are 178 acquired, 24 completed negative observations and 56 failed attempts, with zero unattempted identities
and 55 exclusions. Available assets overlap unsuccessful later attempts; these are not disjoint populations.
The 56 failures are dated unresolved external observations, not proof that icons do not exist. They do not
violate the requirement to retain assets and report failures honestly, and this verification does not declare
[dsw-nrp/eosc-fair-guide#150](https://github.com/dsw-nrp/eosc-fair-guide/issues/150) closed or every external host
currently reachable.

Human source/content acceptance, technical approval, PR merge, issue closure, spec sync, archival and release
remain separately governed actions. None is performed or newly authorized by this report. These hand-offs are
tracked separately from this implementation-verification result.

## Issues by priority

- **CRITICAL:** None.
- **WARNING:** None.
- **SUGGESTION:** None.

## Final assessment

All checks passed. Ready for archive. This is the advisory implementation-verification verdict; running the
archive workflow, including its own checks and explicit approval, remains a separate action.
