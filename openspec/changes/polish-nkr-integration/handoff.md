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
