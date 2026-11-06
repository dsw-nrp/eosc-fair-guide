# Verification Report: polish-nkr-integration

Date: 2026-11-05. Workflow: `openspec-verify-change`, schema `spec-driven`.
Scope: implementation at `f898fde` plus the second PR review repairs, compared with base `b8569d3`.
The initial verification was report-only; later explicit repair requests authorized tasks 10 and 11 through
`openspec-apply-change`. This report keeps the earlier dispositions and adds the second review below.

## Summary

| Dimension | Status |
| --- | --- |
| Completeness | 34/34 tracked tasks checked; all 13 delta requirements mapped |
| Correctness | 13 requirements and 35 scenarios examined; five second-review findings repaired |
| Coherence | Nine decisions traced; incoming NKR keys align with its reviewed schema; availability has one owner |

There are eight ADDED and five MODIFIED requirements, with no REMOVED or RENAMED entries.
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

   Regression tests cover both AMCR addresses and multiple entries at one address. Handle-based retirement
   coverage also passes. The earlier direct re3data retirement test injected a relationship absent from the
   reviewed Repository schema; second-review task 11.1 removes that dormant path and its synthetic coverage
   claim. AMCR's entity remains unchanged and the retired record is never listed.

## Second PR review dispositions

The review of `f898fde` confirmed all nine original findings were resolved and raised five new Low findings.
Their local repairs are:

| Finding | Disposition and evidence |
| --- | --- |
| NKR annotation overlay replaces source facts | NKR rows bypass `[[record]]` overlays; regressions keep their original names and addresses when joining AMCR or MBDB, and both build and duplicate checks agree. |
| Incoming re3data join is dormant under the reviewed schema | Removed `nkr_re3data`, the live-record parser property, the re3data match key and synthetic retirement branch. A refresh test proves `relatedRegistry` is omitted and the normalized NKR record has no re3data key. Incoming NKR joins use reviewed handles and exact addresses; curated re3data joins remain separate. |
| Expanded contact evidence is not pinned | The page check opens both `.question-details` and `.evidence-details`, then asserts a visible `uveden`/`present` value. Removing the field context from the generated inspection script fails the Czech assertion; restoring it passes. |
| Untrusted diagnostic labels reach logs and summaries | Labels lose terminal/control characters and Unicode line separators, collapse whitespace, are bounded and escaped. The publisher independently sanitizes reasons in both summary tables and PR bodies. Python/Node adversarial cases cover hostile IDs/names, markup and long text. |
| Deposit availability has two producers | Only the final entity loop derives the property, using `NON_DEPOSIT_STATUSES` after overrides and NKR's retained pilot-refusal fact. Curated repository/resource cases cover all five Guide statuses. Removing `planned` from the shared set makes the curated-status test fail. |

The direct-record annotation probe intentionally supplies a legacy extra relationship to prove it contributes
no identity or annotation facts; it is not evidence of a currently harvested re3data join. Both current-schema
refresh and the supported build/duplicate paths are covered independently.

The review's two older, explicitly non-verdict observations (kind-map drift and the placement parity test's
fixed domain) remain advisory; this repair does not claim they were fixed or file an issue for them.

## Requirement and scenario coverage

| Delta requirement | Scenarios | Implementation and test evidence |
| --- | ---: | --- |
| Resource and repository finder | 5 | `build_crate.build_repositories`; reference harvest, raw/annotated addresses, FIP-only joins and both ambiguity tests in `tests/test_nkr_integration.py`; finder/browser checks |
| Repository and registry functions | 3 | `catalogue-view.js` retains displayed functions and filters the deposit facet; FIP publication-deposit regression; catalogue and NKR page checks |
| NKR records are shown as found | 6 | Supported handle/address joins, annotation-overlay exclusion and final NKR property overrides; name/empty-address tests; empty snapshot injection and abbreviation assertions |
| A repository not yet public is listed with its NKR record | 2 | Conditional API/profile link contract; address-free card and bilingual text; profile negative controls, refresh rejection test and NKR browser section |
| Repository names are harvested and reviewed | 2 | `repository_entity`, `nkr_repositories`; Czech re3data naming checks in `tests/test_scripts.py`; bilingual herbarium and CzBIRD fixture assertions |
| Catalogue slugs use meaningful local names | 2 | `catalogue_identity.identity_seed` and `preserve_snapshot`; registry-host exclusion, NKR kind routes, readable fixture IDs and existing identity-preservation tests |
| NKR statuses map onto the dated vocabulary | 3 | Shared mapping; all seven statuses; mapped-retirement filters and raw/annotated/multiple-address retirement reporting tests |
| The NKR snapshot keeps only fields its record can carry | 3 | Schema selection/unavailable-field notes; omitted unsupported relationships; contact presence, expanded bilingual evidence and export assertions |
| NKR refresh rejects unrepresentable values before writing | 3 | Upstream and Guide type/enum/nested checks, HTTPS URLs and retryable transport errors; invalid-value, schema-change and snapshot-preservation tests |
| Curated NKR handles resolve to snapshot records | 1 | `check_content.check_repositories`; valid/mistyped handles in repository and resource-repository placements |
| Source diagnostics are bounded literal text | 1 | Hostile-label refresh test and summary/PR-body publisher tests; old snapshot bytes preserved |
| The duplicate check covers NKR records | 2 | NKR entries and link keys; raw/annotation addresses; conflicting curated owners, multi-entry and multiple-NKR ambiguity regressions; Python/Node placement parity |
| A repository link may be its NKR record only while it is not public | 2 | `build_api.schemas`, `profile/fair-guide/must/1_content.ttl`; schema and SHACL positive/negative controls |

All 35 declared scenario conditions have implementation/test evidence, including the second review's
annotation, unsupported-field and diagnostic cases.

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
| 11.1-11.5 | Four new NKR tests, publisher sink cases, expanded evidence assertions, two planted regressions, bilingual desktop/phone screenshots and complete native acceptance |

Task 9.2 and revised D6 explicitly distinguish transport failure from malformed schema content; that later
decision clarifies task 2.2's older wording about an unreadable schema.

## Design and pattern review

- D1: supported NKR handle/address keys, raw/annotation addresses, separate FIP-only components and ambiguity rejection are present; NKR receives no annotation overlay.
- D2: final non-empty NKR property precedence and Unicode token abbreviation suppression are present.
- D3: mapped/dated statuses and exclusion are present; retirement reporting uses the build's identity lookup.
- D4: one final producer derives deposit availability from the applied Guide status and NKR-only source fact.
- D5: API, profile and UI agree on planned/development address-free repositories linked to NKR.
- D6: upstream and Guide field-shape validation, privacy reduction and retry classification are present;
  incompatible schema/value changes reject before replacement; operator diagnostics are bounded literal text.
- D7: registry record URLs do not seed NKR IDs; type-based routes and existing local identity preservation remain.
- D8: duplicate checks cover NKR links, automatic exact-address joins and ambiguous components.
- D9: empty-NKR states are injected and restored independently of the harvested content.

The NKR contract module uses the standard library and serves refresh/build/check paths. The change follows
the existing graph/text-node rendering, bilingual strings, source provenance and generated-output boundaries.
No significant naming, dependency or code-pattern deviation was found.

## Fresh validation

- `.venv/Scripts/python.exe scripts/check_all.py`: **36/36 passed in 170.5 seconds**, including **742 unit tests**
  in four successful shards, the complete browser checks, API/profile checks, docs and ownership/integrity checks.
- Strict OpenSpec validation within that run: **6/6 passed**.
- Focused NKR suite: **29 tests passed**. Annotation, unsupported-field and diagnostic regressions failed
  before repair, then passed. The publisher's hostile summary/PR-body cases pass too.
- Planted controls: removing `inspection.js` field context fails the expanded Czech evidence assertion;
  restoring the generated script passes. Removing `planned` from the shared availability set fails the
  curated-status test. Logs are under `.cache/nkr-round2-*-negative.log` and the positive localization log.
- Expanded contact evidence was visually inspected in Czech/English at 1366 and 320 px. Screenshots and their
  manifest are local under `.cache/screenshots-nkr-round2/`. No contact address is present.
- Original isolated probes now confirm both repairs. Source and current evidence are local under
  `.cache/verify_nkr_contract.py` and `.cache/nkr-verification-probes.json`; the before-repair evidence is
  retained in `.cache/nkr-verification-probes-before-repair.json`.
- Complete acceptance logs and reports are under `.cache/health/`. The earlier same-session populated fixture
  API/profile and bilingual desktop/phone/print evidence is recorded separately in `handoff.md`.

This report assesses the local implementation. It does not record a merge, a real scheduled-source refresh,
hosted publication, a commit, spec synchronization or archival. The existing maintainer follow-up remains in
`tasks.md` and `handoff.md`.

## Final assessment

All five new review findings are repaired and complete local acceptance passes. The first run passed 35/36
checks because one line needed formatting; after correction, the final run passed 36/36. No active findings
from this review remain; its two older non-verdict advisories are recorded above. Archival remains separate.
