# Tasks

## 1. Reference fixture and baseline

- [x] 1.1 Add a test fixture of the five public NKR records as of 2026-11-01 (search results plus `nkr-schema.json` from `https://repo.cz/schemas/Repository`), with every `mainContact` value replaced by a synthetic address, and verify no real contact address is committed (an e-mail pattern search over the fixture finds only `example.org` addresses)
- [x] 1.2 Check out the head of [dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168) locally, run `python -m unittest discover -s tests`, and record the names of all eight unit failures in this change's hand-off notes; verify each one is attributed to a design decision (D1–D9) or listed as a new finding before group 2 starts

## 2. Snapshot refresh (D6, D7)

- [x] 2.1 Move the NKR type mapping into `scripts/catalogue_identity.py`, add NKR's host to the registry hosts `identity_seed` skips, and route new NKR records by type in `preserve_snapshot`; verify with a unit test that the fixture yields `herbarium` under `repo/dom` and that no NKR ID equals its handle suffix
- [x] 2.2 Make `refresh_snapshots.nkr` read the Repository schema, keep the identity fields plus the `prefill.nkr` paths the schema defines, report the others in the outcome, and keep `status` and `additionalNames`; verify with unit tests that `pidType` is reported and absent from `fields`, and that a missing schema rejects the refresh without writing
- [x] 2.3 Reject a refresh with a record that is not decommissioned, has no address or reviewed handle joining an addressed entry, and is not planned or in development; verify with a unit test naming the record in the rejection reason and leaving the previous snapshot unchanged
- [x] 2.4 Update `docs/content-model.md` (NKR snapshot fields, schema-derived field list, contact presence) and `docs/runbooks/refresh-a-source.md` if its NKR step changes; verify with `python scripts/check_docs.py`

## 3. Catalogue identity and precedence (D1, D2, D3)

- [x] 3.1 Replace the single merge key in `build_repositories` with a union of keys (existing keys, NKR handle, NKR address lookup), and refuse an NKR record whose keys reach two components; verify with a unit test over the fixture that gives three automatic joins, one join through `nkr` on a curated entry, one new entry and one refused ambiguous record. Cover FIP-only address joins with identity and source credits retained, and reject ambiguous joins involving FIP-only entries without automatically joining other sources by address.
- [x] 3.2 Apply NKR's non-empty name (Czech and English), kind, status, as-of date, keywords and address after merging, and keep every other property's first-value rule; verify with unit tests for the CzBIRD case (name, in development, curated address and operator kept) and for a resource entity (`datarepo`) taking NKR's name
- [x] 3.3 Map NKR statuses to the five-level vocabulary dated by `retrieved`, exclude decommissioned records, and report them with any entry they reach; verify with unit tests over all seven NKR statuses and the decommissioned report
- [x] 3.4 Give `nkr_config` the `mainContact` presence from `mainContactPresent`, and show "present" without an address in the self-check evidence; verify with a page test that gate.13 is answered from NKR and that the export contains no address
- [x] 3.5 Update `docs/content-model.md` (merge keys, NKR precedence, status mapping) and the repository-discovery paragraph of `docs/design.md`; verify with `python scripts/check_docs.py`

## 4. Not-yet-public repositories and deposit availability (D4, D5)

- [x] 4.1 Add the Guide vocabulary term for deposit availability, set it false at build for planned, in development, prospective or NKR `pilot - not accepting data`, and leave the deposit facet value out of the index for such entities; verify with a page test that the data-repository chooser omits a fixture repository in development while the repositories family lists it with its function
- [x] 4.2 Allow a repository entity without `url` only when planned or in development with an NKR `sameAs`: relax the profile shape with `sh:or` and the API `Repository` schema with an `if`/`then` and a description; verify that `rocrate-validator ... -p fair-guide-0.1` and `npm run check:api` accept the fixture repository in development and reject an operational one without an address
- [x] 4.3 Show the bilingual "no public address yet" line on such a card and keep its title opening the entry, with the NKR record as its external link; add the strings to `content/ui.toml` in Czech and English, and verify with a page check at 320 px and desktop in both languages
- [x] 4.4 Apply the abbreviation display rule where the displayed name is composed; verify with a page test that "Molecular Biophysics Database - MBDB" is not followed by "(MBDB)" and that "Český sociálněvědní datový archiv (ČSDA)" is unchanged

## 5. Duplicate check (D8)

- [x] 5.1 Add NKR snapshot records to `check_duplicates.entries` with `nkr` and address keys, make `nkr` an authoritative and link key, and add its placement on `[[repository]]` and `[resource.repository]`; verify with unit tests that the reference harvest reports nothing, that two curated entries naming one handle fail with both names, and that the Node-validator parity test passes

## 6. Page checks (D9)

- [x] 6.1 Rewrite the empty-NKR assertions in `tests/page/check_page.mjs` (finder and maturity check) to inject an empty NKR configuration and restore it, and add a populated-state assertion; verify by planting a regression (an NKR record listed twice) and seeing `npm run check:page` fail, then pass without it

## 7. Content and paradata

- [x] 7.1 Add `nkr = "20.500.14818/srhtp4ek"` to the curated `czech-bioimaging` entry in `content/repositories.toml`, and extend or add the provenance action in `content/provenance.toml` naming the NKR record as consulted, with the model as an instrument; verify with `python scripts/check_content.py --base origin/main` and `python scripts/check_duplicates.py`

## 8. Integration

- [x] 8.1 Build with the fixture snapshot in a temporary content copy and run the API, profile, unit and page checks against it; verify all pass, and that the five records produce exactly one new repository entry
- [x] 8.2 Run `npm run openspec:validate` and `python scripts/check_all.py` on the branch and record both results in the usage-log entry
- [x] 8.3 Do the visual pass of the repository catalogue, a joined NKR entry, the fixture entry in development and the gate check pre-filled from NKR, in Czech and English at desktop and phone widths; record screenshots in the pull-request review artifacts and fix what the pass finds

## 9. Review repairs

- [x] 9.1 Align raw and annotated address keys in build and duplicate checks, and reject two NKR records reaching one component; reproduce both failures and verify regression tests.
- [x] 9.2 Share the reviewed status mapping, validate every kept NKR field against the fetched schema before writing, and keep schema transport failures retryable; verify rejection and snapshot preservation with malformed records and schema drift.
- [x] 9.3 Keep address-free records that join an addressed curated repository or resource through a reviewed handle, and validate curated handles against an available snapshot; verify valid and mistyped handles in both placements.
- [x] 9.4 Restore abbreviation suppression anywhere a complete token occurs, retaining the MBDB suffix case; demonstrate the regression in browser checks and inspect affected cards in both languages at phone and desktop widths.
- [x] 9.5 Correct rollback order, reconcile contract documentation, and run OpenSpec validation plus the complete local check suite; record evidence in the hand-off and rolling usage entry.

## 10. Verification warning repairs

- [x] 10.1 Validate kept NKR identity values against the Guide's consumed shapes as well as the fetched schema; reproduce schema changes to alternative names and keywords and verify rejection without replacing the previous snapshot.
- [x] 10.2 Reuse the build's repository identity lookup for retirement reporting, including raw and annotated addresses and reviewed keys; reproduce the AMCR omission and verify every reached entry is named without changing its status or listing the retired record.
- [x] 10.3 Run strict OpenSpec validation and complete native acceptance; update the verification report, hand-off and rolling usage record with both warning dispositions.

## Workflow follow-up

- A maintainer closes [dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168) unmerged after this change merges, and dispatches the `nkr` source refresh.
- The maintainer reviews the new snapshot pull request, registers its identifiers with `scripts/register_ids.py` and decides how to report the CzBIRD keyword typo to NKR.
- Archive the change after review and the refresh pull request are settled.
