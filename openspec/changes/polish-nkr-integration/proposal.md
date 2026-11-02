# Proposal

## Why

The first real NKR harvest ([dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168), 2026-11-01, five records) proved the refresh but failed the API, profile, unit and page checks and would have listed three repositories twice. The catalogue joins an NKR record only by re3data ID or by its own address, NKR records no longer carry `relatedRegistry`, and the duplicate check does not read snapshot `record` rows, so ArchaeoVault, the Data Catch-all Repository and CzBIRD each gained a second entry; CzBIRD, which NKR lists without an address, became an entry with no link. The snapshot would also mint opaque identifiers (`9lloktrg`, `jgu5fyqf`) from NKR record pages that later refreshes would preserve, so the integration must be corrected before any NKR snapshot merges.

NKR has meanwhile split its record: `Repository` (<https://repo.cz/schemas/Repository>) keeps identity and description, and the operational fields moved to `RepositoryPlus`, which has no public records yet. Reading `RepositoryPlus` is separate work tracked in [dsw-nrp/eosc-fair-guide#169](https://github.com/dsw-nrp/eosc-fair-guide/issues/169); this change only stops expecting those fields from `Repository`.

## What Changes

- **Catalogue identity.** A repository entry is one thing when any of its keys match: re3data ID, NKR handle, or exact normalised address. An NKR record with a matching address joins automatically; a record without an address joins only through a reviewed `nkr` handle on a curated entry (the field `docs/content-model.md` already defines but the merge key ignores). A similar name or host alone still merges nothing.
- **NKR is the authority for the facts it publishes.** For a repository NKR lists, its name (Czech from `repositoryName`, English from `additionalNames`), kind, status with its as-of date, keywords and address take precedence over curated and other registry values. An empty NKR value states nothing and never removes a curated value, so a known working instance address stays. Guide-owned facts (functions, operator, developer, DataCite repository, abbreviation, recommendation) are unaffected. An abbreviation is not appended to a name that already ends with it.
- **NKR status maps onto the five-level vocabulary.** `intended` → planned; `development`, `test` → in development; `pilot - not accepting data`, `pilot - accepting data` → pilot; `production` → operational; a `decomissioned` record is not listed. NKR's placeholder `releaseDate` is not used as a date.
- **A not-yet-public repository can be listed.** An NKR record with no address that joins no entry is listed with its status and its NKR record as its only link; repository listings that offer a place to deposit data now do not offer it. The repository link requirement in the profile and API schema is relaxed for exactly this case: status planned or in development, with an NKR record link.
- **Snapshot refresh.** The NKR snapshot keeps `status` and `additionalNames`, keeps only fields the `Repository` record can carry, and records the presence of a contact so the administrator-role question can be answered from it. New NKR identifiers are seeded from the repository's own address or name, never from the NKR record page, and routed by kind (`repo/dom`, `repo/inst`, `repo/gen`).
- **Checks.** The duplicate check reads NKR snapshot records and treats an NKR handle as a linking key. Page checks stop assuming that NKR is empty; the empty state is tested by putting an empty NKR configuration in place, as the pre-fill test already does with a record.
- **Content.** The curated `czech-bioimaging` entry gains its reviewed NKR handle `20.500.14818/srhtp4ek` with evidence and paradata.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-experience`: *Resource and repository finder* and *NKR records are shown as found* — multi-key joining, NKR as the authority for its published facts, and listing a not-yet-public NKR repository without an address.
- `fair-guide/guide-knowledge-base`: NKR status in the dated five-level vocabulary; repository names where NKR is authoritative; NKR identifiers seeded from the repository, not the record page; the duplicate check covering NKR records; the conditional repository link in the API schema and profile.

## Impact

- **Code:** `scripts/build_crate.py` (`repository_key`, `build_repositories`, `nkr_repositories`, `nkr_config`), `scripts/refresh_snapshots.py` (`nkr`, `nkr_fields`), `scripts/catalogue_identity.py` (`identity_seed`, NKR routes), `scripts/check_duplicates.py`, `assets/js/live.js` and `assets/js/catalogue-view.js` where status and links are rendered.
- **Contracts:** `profile/fair-guide/must/1_content.ttl` (*Repository link*), the API `Repository` schema, `docs/content-model.md` (NKR snapshot fields, merge precedence).
- **Content:** `content/repositories.toml` (`czech-bioimaging`), `content/provenance.toml`, `content/identifiers.toml` for new entries.
- **Tests:** `tests/test_scripts.py` (NKR refresh and catalogue join), `tests/page/check_page.mjs` (NKR empty state and pre-fill), API and profile fixtures.
- **Hand-off:** [dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168) is closed unmerged once this change lands; the next scheduled refresh proposes a clean snapshot that a maintainer reviews.

### Exclusions

- Reading `RepositoryPlus`, mapping its Wikidata PID types and re-reviewing `NKR-SCHEMA.01` and the `prefill.nkr` lists: [dsw-nrp/eosc-fair-guide#169](https://github.com/dsw-nrp/eosc-fair-guide/issues/169).
- NKR descriptions, which NKR publishes without a licence.
- Joining NKR records to `[[record]]` annotations by a reviewed `nkr` key: added only when a re3data-only entry needs it.

### Validation

`npm run openspec:validate`; `python -m unittest discover -s tests` with fixtures from the five real records (three automatic joins, one reviewed join, one new entry, one record without an address that joins nothing); `python scripts/check_duplicates.py`; the API and profile checks on a build that includes those fixtures; `python scripts/check_all.py` at close-out; a visual pass of the repository catalogue and the gate check in both languages at desktop and phone widths.
