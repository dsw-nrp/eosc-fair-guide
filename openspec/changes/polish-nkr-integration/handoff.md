# NKR integration evidence and hand-off

## Reference harvest

Baseline: [dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168),
head `774b241890fdfb31be6ec111c0db9e415b998c5c`, checked out independently
under `.cache/pr168-baseline`. The public five-record fixture lives in
`tests/fixtures/nkr/`; its README describes the contact sanitization and exclusions.

## Baseline unit failures

`python -m unittest discover -s tests` reproduces eight NKR failures in
`test_publication_location.PublicationLocationTests.test_two_origins_two_prefixes_with_real_expanded_graphs_and_profile_validation`:
the four publication locations in that test, each with an independent semantic
namespace and with the publication location as namespace. Each fails the
`Repository link` profile constraint on `#repository-srhtp4ek` (CzBIRD).
The exact `(location, semantic)` subcase names are:

| Location | Semantic namespace |
| --- | --- |
| `https://one.example/` | `https://namespace.example/` |
| `https://one.example/` | `https://one.example/` |
| `https://one.example/a/guide/` | `https://namespace.example/` |
| `https://one.example/a/guide/` | `https://one.example/a/guide/` |
| `https://two.example/` | `https://namespace.example/` |
| `https://two.example/` | `https://two.example/` |
| `https://two.example/a/guide/` | `https://namespace.example/` |
| `https://two.example/a/guide/` | `https://two.example/a/guide/` |

All eight are covered by D1 (reviewed handle join) and D5 (conditional repository
link). D7 also prevents the opaque `srhtp4ek` identity on the next harvest.

The initial isolated run lacked Swagger UI and a built site; both prerequisites
were supplied before the repeat. The sandbox additionally refused temporary
fixture directories, Git test repositories and a test implementation attachment.
Those errors are environmental findings, separate from the eight NKR failures.
The native rerun completed 713 tests in 153.255 seconds with nine failures and
one skip. Eight are the subcases above. The additional failure is
`test_health.HealthTests.test_custom_test_record_catches_missing_or_escaping_attachments`:
it hard-codes `../eosc-fair-guide/assets/js/assess.js`, which resolves within the
normal checkout but outside an isolated checkout named `pr168-baseline`.
This is a baseline test portability finding, unrelated to NKR; no product change
is needed for it. Full output is retained in `.cache/pr168-baseline/.cache/pr168-unit-native.log`.

## Maintainer follow-up

After this change merges, a maintainer closes the original refresh PR unmerged,
dispatches the NKR refresh, reviews the joins and readable identifiers, and
registers the new identifiers. The CzBIRD keyword typo remains a source-side
review decision. RepositoryPlus integration remains separate work in
[dsw-nrp/eosc-fair-guide#169](https://github.com/dsw-nrp/eosc-fair-guide/issues/169).

## Local implementation evidence

- The sanitized five-record harvest is refreshed into a temporary content copy.
  Its normal build produces three address joins, one reviewed handle join and exactly
  one new repository. A separate build omits the reviewed handle to exercise the
  address-free CzBIRD entry in development; it adds two entries, as expected.
- Both builds pass the API validator and all 60 required Guide profile checks.
  Unit negative controls reject an operational address-free repository and one
  without an NKR record. API negative controls also reject an insecure address.
- The complete populated-fixture page suite passes, including the embedding and
  catalogue completeness checks. An intentional duplicate in generated output
  failed with `NKR test/development is listed 2 times`; rebuilding removed it.
- The first aggregate pass completed all 36 checks in 195.6 seconds, including the
  full 723-test unit suite. The final default aggregate after the contact evidence
  wording fix passed all 36 checks in 165.2 seconds, again including 723 unit tests.
  OpenSpec validation passed all six items. Final reports are in `.cache/health/`.
- The visual pass covers the catalogue, joined CzBIRD and MBDB entries, the
  address-free entry and NKR gate pre-fill in both languages at 1366 and 320 px,
  including collapsed/expanded evidence and print. The raw contact-field label
  found during review now has a bilingual label. A regression check preserves an
  unrelated source title `present` while localizing contact presence.
  Prepared review images and their manifest are in `.cache/screenshots-nkr/`;
  these local artifacts have not been uploaded. No contact address is present.

No NKR snapshot is added to authored content. A real NKR harvest still enters
through the separately reviewed source-refresh pull request after merge.

## Verification repair: NKR joins to FIP-only repositories

OpenSpec verification exposed that FIP-only repositories entered the catalogue
after NKR's address lookup. An NKR record at CESNET Invenio's address therefore
produced two entries while the duplicate checker passed. Combining CzBIRD's
reviewed handle with the FIP-only NUSL address also passed the build despite the
duplicate checker rejecting its ambiguous keys.

Task 3.1 was reopened for the repair. Three new regression tests failed before
the implementation changed, then passed after registering FIP-only entries as
separate components before the NKR merge. Their existing local IDs, functions,
verification evidence and source links are retained, and an NKR join credits
both snapshots. The full NKR test module passes 14 tests, including a separate
check that a joined publication repository does not gain a data-deposit function.
The original five-record fixture still adds exactly one repository.

A temporary populated build adding an NKR record at CESNET Invenio's address
passes API validation (1,736 files) and all 60 required Guide profile checks.
Browser probes confirm one entry at its existing route, both source links,
retained verification evidence and exclusion from data deposit when NKR says
it is not accepting data, in Czech and English at 1366 and 320 px. The viewport
screenshots and manifest are local artifacts under `.cache/screenshots-nkr-fip/`.
The rolling usage entry records the final default aggregate result.

## Review repairs, 2026-11-05

All nine findings from [dsw-nrp/eosc-fair-guide#170](https://github.com/dsw-nrp/eosc-fair-guide/pull/170)
are repaired locally:

| Finding | Repair and regression evidence |
| --- | --- |
| Raw snapshot and annotation addresses disagree | Build and duplicate checks index both. NKR records at either AMCR address join the existing AMCR entity and retain NKR address precedence. |
| Status vocabulary can drift silently | `scripts/nkr_contract.py` owns the reviewed mapping. Every refreshed status must match the fetched schema enum and the mapping. Retirement filters in the build, pre-fill, duplicate check and health inventory use the mapped result; a synthetic corrected spelling exercises all four. |
| Address-free reviewed joins are rejected | Refresh reads reviewed handles from repositories and resource repositories. A pilot without an address is accepted when its reviewed entry supplies an address; the unjoined pilot still rejects. |
| Curated NKR handles are unchecked | Content validation reports the entry and unknown handle in either placement when an NKR snapshot exists. Before the first snapshot there is no harvested record to compare. |
| Prefix and internal abbreviations repeat | Unicode token boundaries suppress existing abbreviations anywhere in a name, with literal regex escaping. Browser checks cover COMPASS, CzechNanoLab, an internal token, symbolic abbreviations, and substrings that still need an abbreviation. MBDB and ČSDA retain their intended display. |
| Invalid kept values are written | Schema types, enums and nested required fields are checked before writing; non-empty addresses require absolute HTTPS URLs. Invalid addresses, alternative names and keyword arrays leave the old snapshot byte-identical and name the record and field. Contact content remains reduced to presence only. |
| Two NKR records mix facts in one component | Build and duplicate checks reject the ambiguity with both handles, for a new component and an existing repository. |
| Schema transport failures require maintainer action | Retrieval errors retain the retryable `failed` outcome; malformed schemas remain `rejected`. Both preserve the snapshot. |
| Rollback order blocks its own checks | The migration plan removes the NKR snapshot first or reverts both changes together, and explicitly validates against a tree containing the merged snapshot. |

The initial Python regressions and the focused browser check reproduced the failures before the repairs.
The NKR module now has 22 tests. The complete default acceptance run passes 36/36 checks in 189.7 seconds,
including all 735 unit tests; strict OpenSpec validation passes all six items. Reports are in `.cache/health/`.
The focused NKR browser section also passes after retaining the address-free card's accessibility audit
alongside the new abbreviation assertions.

A refreshed five-record fixture still adds exactly one repository, passes API validation (1,736 files) and
all 60 required Guide profile checks. Viewport screenshots cover COMPASS, CzechNanoLab, MBDB and ČSDA in
Czech and English at 1366 and 320 px, with desktop print views. The baseline and populated-fixture artifacts
are local under `.cache/screenshots-nkr-review/` and `.cache/screenshots-nkr-review-fixture/`.

A sandboxed unit rerun encountered Windows temporary-directory permissions; the native acceptance run
passed, and its seven empty scratch directories were removed. No authored snapshot, commit, push, review
thread resolution, archive or hosted operation is part of this repair.

## Authorized verification warning repairs, 2026-11-05

The subsequent OpenSpec verification found two additional edge cases. After the explicit "fix both" request,
tasks 10.1-10.3 repair both within this change:

- Kept identity values satisfy the fetched schema and the Guide's consumed shapes in `scripts/nkr_contract.py`.
  Five schema/value drift cases now reject before replacement and preserve the previous snapshot exactly.
- The graph retains the build's repository identity lookup as runtime metadata. Retirement reporting uses the
  same NKR match keys and names all entries reached through raw/annotated addresses or reviewed keys, without
  changing their facts or listing the retired record. The lookup is not serialized into the crate or API.

The new regression cases failed before the repair. All 25 NKR tests now pass, and both original verification
probes confirm the fixes: incompatible alternative names return `rejected` without changing the snapshot,
and the retired raw-address AMCR probe names `#repository-amcr`. Before/after evidence is retained locally
under `.cache/nkr-verification-probes-before-repair.json` and `.cache/nkr-verification-probes.json`.

Final native acceptance passes 36/36 checks in 172.9 seconds, including 738 unit tests. Strict OpenSpec
validation passes all six items. The verification report now records both warnings as resolved and covers
29 tracked tasks, 12 requirements and 32 scenarios. Existing staged content was preserved; no commit, push,
archive, source-refresh dispatch or hosted operation was performed.

## Second PR review repairs, 2026-11-05

The review at `f898fde` confirmed the nine original threads were repaired and raised five new Low findings.
All five are addressed by tasks 11.1-11.5:

- NKR rows bypass re3data annotation overlays and use their original names and addresses. The reviewed schema
  has no `relatedRegistry`, so the dormant incoming re3data parser, match key and synthetic retirement branch
  were removed. Refresh omission and supported handle/address build/duplicate paths have explicit tests.
- The browser check opens both disclosure levels for gate.13 and checks the visible contact value in both
  languages. A planted removal of the field context from generated `inspection.js` failed the Czech assertion;
  restoring the file passed. Expanded views were inspected at desktop and 320 px in both languages.
- Source-controlled diagnostic labels are flattened, stripped of terminal/control characters and Unicode
  separators, bounded and escaped. The publisher repeats protection for summary tables and PR bodies.
  Adversarial Python/Node cases preserve the old snapshot and cannot create active markup or extra rows.
- Deposit availability has one producer after status overrides. `NON_DEPOSIT_STATUSES` owns the Guide rule,
  and NKR's pilot refusal stays source data until then. Curated repository/resource cases cover all five
  statuses; removing `planned` from the shared set makes the new curated-status regression fail.

The focused NKR module passes 29 tests. The full initial run passed 35/36 checks with one formatting failure;
after formatting, final native acceptance passes 36/36 checks in 170.5 seconds, including 742 unit tests.
Strict OpenSpec validation passes all six items. Diagnostic protection has a curated security changelog note.
The verification report now covers 34 tasks, 13 requirements and 35 scenarios, with all five new findings
resolved. The two older non-verdict observations remain advisory, as reported by the reviewer.

The negative-control logs and positive localization log are under `.cache/nkr-round2-*`; expanded-evidence
screenshots and manifest are under `.cache/screenshots-nkr-round2/`. No implementation source was left with
a planted regression. Changes remain local and uncommitted; no push, thread resolution, archive or hosted
operation was performed.
