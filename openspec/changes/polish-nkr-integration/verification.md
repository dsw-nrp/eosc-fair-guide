# Verification Report: polish-nkr-integration

Date: 2026-11-05. Workflow: `openspec-verify-change`, schema `spec-driven`.
Scope: implementation at `1ec02bd` plus the review and authorized verification-warning repairs, compared
with base `b8569d3`. The initial verification was report-only; the subsequent explicit "fix both" request
authorized tasks 10.1-10.3 through `openspec-apply-change`. Existing staged content was preserved.

## Summary

| Dimension | Status |
| --- | --- |
| Completeness | 29/29 tracked tasks checked; implementation found for all 12 delta requirements |
| Correctness | 12 requirements and 32 scenarios examined; both reported edge cases repaired and covered |
| Coherence | Nine design decisions traced; D3 and D6 warning repairs verified; code patterns consistent |

There are seven ADDED and five MODIFIED requirements, with no REMOVED or RENAMED entries.
All six applicable checks ran: Task Completion, Spec Coverage, Requirement Implementation Mapping,
Scenario Coverage, Design Adherence and Code Pattern Consistency. No checks were skipped.

## Issues by priority

### CRITICAL

None.

### WARNING

None outstanding. Both warnings from the initial verification are resolved below.

### SUGGESTION

None.

## Resolved warnings

1. **Guide compatibility after an upstream schema type change — resolved.**

   Before repair, changing `additionalNames` to a schema-valid string replaced the snapshot and caused
   `AttributeError: 'str' object has no attribute 'get'` in the build. Kept identity values now also match
   `NKR_FIELD_SHAPES` in `scripts/nkr_contract.py`, checked before writing by `refresh_snapshots.py:609`.
   Field selection still follows the fetched schema and dynamic pre-fill roots.

   `test_changed_schema_cannot_admit_shapes_the_guide_cannot_consume` reproduces five incompatible schema
   and value combinations: string alternative names, arrays of string names, array-valued nested names,
   numeric Czech keywords and a string English keyword field. Each rejects with the record/field named
   and leaves the previous snapshot byte-identical. The original isolated probe now reports `rejected`,
   `snapshot_changed: false` and no build error.

2. **Retirement identity through raw source addresses — resolved.**

   Before repair, a decommissioned record at `https://digiarchiv.aiscr.cz/` yielded `Entries reached: none`
   because AMCR's final URL is `https://amcr-info.aiscr.cz/`. The graph now retains its repository key lookup
   as build-only metadata (`build_crate.py:1686`). Build and health reporting share `nkr_match_keys`;
   retirement reporting names every reached entity without merging the retired record.

   Regression tests cover both AMCR addresses, multiple entries at one address and a reviewed re3data
   key. The existing handle-based retirement coverage still passes. AMCR's entity remains unchanged and
   the retired record is never listed. The original isolated probe now names `#repository-amcr`.

## Requirement and scenario coverage

| Delta requirement | Scenarios | Implementation and test evidence |
| --- | ---: | --- |
| Resource and repository finder | 5 | `build_crate.build_repositories`; reference harvest, raw/annotated addresses, FIP-only joins and both ambiguity tests in `tests/test_nkr_integration.py`; finder/browser checks |
| Repository and registry functions | 3 | `catalogue-view.js` retains displayed functions and filters the deposit facet; FIP publication-deposit regression; catalogue and NKR page checks |
| NKR records are shown as found | 5 | Multi-key merge and final NKR property overrides; name/empty-address tests; empty snapshot injection and abbreviation assertions in `tests/page/check_page.mjs` |
| A repository not yet public is listed with its NKR record | 2 | Conditional API/profile link contract; address-free card and bilingual text; profile negative controls, refresh rejection test and NKR browser section |
| Repository names are harvested and reviewed | 2 | `repository_entity`, `nkr_repositories`; Czech re3data naming checks in `tests/test_scripts.py`; bilingual herbarium and CzBIRD fixture assertions |
| Catalogue slugs use meaningful local names | 2 | `catalogue_identity.identity_seed` and `preserve_snapshot`; registry-host exclusion, NKR kind routes, readable fixture IDs and existing identity-preservation tests |
| NKR statuses map onto the dated vocabulary | 3 | Shared mapping; all seven statuses; mapped-retirement filters and raw/annotated/multiple-address/re3data retirement reporting tests |
| The NKR snapshot keeps only fields its record can carry | 2 | `nkr_fields`, schema property selection and unavailable-field notes; contact reduced to presence; refresh tests, publisher note test and gate/export browser assertions |
| NKR refresh rejects unrepresentable values before writing | 3 | Upstream and Guide type/enum/nested checks, HTTPS URLs and retryable transport errors; invalid-value, schema-change and snapshot-preservation tests |
| Curated NKR handles resolve to snapshot records | 1 | `check_content.check_repositories`; valid/mistyped handles in repository and resource-repository placements |
| The duplicate check covers NKR records | 2 | NKR entries and link keys; raw/annotation addresses; conflicting curated owners, multi-entry and multiple-NKR ambiguity regressions; Python/Node placement parity |
| A repository link may be its NKR record only while it is not public | 2 | `build_api.schemas`, `profile/fair-guide/must/1_content.ttl`; schema and SHACL positive/negative controls |

All 32 declared scenario conditions have implementation/test evidence. The two additional scenarios now
cover the combinations exposed by the initial verification warnings.

## Task evidence

| Tasks | Evidence |
| --- | --- |
| 1.1–1.2 | Sanitized five-record fixture and privacy test; baseline failure names and D1/D5 attribution in `handoff.md`; retained baseline unit log exists locally |
| 2.1–2.4 | Shared kind routing, schema selection and refresh tests; unavailable-field publisher assertion; content-model and refresh-runbook updates |
| 3.1–3.5 | Multi-key/FIP/ambiguity regressions; NKR precedence and all-status tests; contact pre-fill/export browser coverage; design/content-model updates |
| 4.1–4.4 | Deposit-facet exclusion, profile/API exceptions, bilingual address-free card and abbreviation cases |
| 5.1–6.1 | Duplicate/link/placement parity tests; empty/populated browser assertions; earlier planted duplicate failure recorded in `handoff.md` |
| 7.1 | Reviewed CzBIRD handle, registered provenance action and fresh content/freshness checks |
| 8.1–8.3 | Populated fixture integration and visual evidence retained in `handoff.md`; fresh full native acceptance below |
| 9.1-9.5 | Eight additional NKR tests plus browser cases, shared status mapping, corrected rollback sequence and fresh checks |
| 10.1-10.3 | Three new NKR tests covering both warning repairs; original probes repeated successfully; complete native acceptance and updated records |

Task 9.2 and revised D6 explicitly distinguish transport failure from malformed schema content; that later
decision clarifies task 2.2's older wording about an unreadable schema.

## Design and pattern review

- D1: reviewed keys, raw/annotation addresses, separate FIP-only components and ambiguity rejection are present.
- D2: final non-empty NKR property precedence and Unicode token abbreviation suppression are present.
- D3: mapped/dated statuses and exclusion are present; retirement reporting uses the build's identity lookup.
- D4: deposit availability is derived without removing the entry's functions.
- D5: API, profile and UI agree on planned/development address-free repositories linked to NKR.
- D6: upstream and Guide field-shape validation, privacy reduction and retry classification are present;
  incompatible schema/value changes reject before snapshot replacement.
- D7: registry record URLs do not seed NKR IDs; type-based routes and existing local identity preservation remain.
- D8: duplicate checks cover NKR links, automatic exact-address joins and ambiguous components.
- D9: empty-NKR states are injected and restored independently of the harvested content.

The NKR contract module uses the standard library and serves refresh/build/check paths. The change follows
the existing graph/text-node rendering, bilingual strings, source provenance and generated-output boundaries.
No significant naming, dependency or code-pattern deviation was found.

## Fresh validation

- `.venv/Scripts/python.exe scripts/check_all.py`: **36/36 passed in 172.9 seconds**, including **738 unit tests**
  in four successful shards, the complete browser checks, API/profile checks, docs and ownership/integrity checks.
- Strict OpenSpec validation within that run: **6/6 passed**.
- Focused NKR suite: **25 tests passed**. The new regressions failed before repair, then passed.
- Original isolated probes now confirm both repairs. Source and current evidence are local under
  `.cache/verify_nkr_contract.py` and `.cache/nkr-verification-probes.json`; the before-repair evidence is
  retained in `.cache/nkr-verification-probes-before-repair.json`.
- Complete acceptance logs and reports are under `.cache/health/`. The earlier same-session populated fixture
  API/profile and bilingual desktop/phone/print evidence is recorded separately in `handoff.md`.

This report assesses the local implementation. It does not record a merge, a real scheduled-source refresh,
hosted publication, a commit, spec synchronization or archival. The existing maintainer follow-up remains in
`tasks.md` and `handoff.md`.

## Final assessment

**All checks passed. Ready for archive** as an advisory implementation assessment. No critical issues,
warnings, suggestions or skipped checks remain in this report. Archival remains a separate action.
