# Proposal

## Why

Karel Berka authored and edited a substantial part of the Guide's advice (four merged pull requests, recorded as
co-author and as the agent of four provenance actions), and the Guide already credits him through
`[guide] contributors` in `content/guide.toml`, the crate's `schema:contributor` and his reviewed ORCID and
affiliation. None of that reaches a reader: the about page's "Who contributed" table has no contributors row
(`build_credits` emits analysis, editor, review, tools and funding), and the archived Zenodo record names only
the software author. The contributor policy deliberately keeps `CITATION.cff` to software authors
(`docs/design.md`, and the CFF 1.2.0 schema rejects `contributors` outright), yet `.zenodo.json` does support
data contributors — so the archive can credit them and the citation file cannot. Today that asymmetry is
unused and undocumented, and content credit is visible only inside per-item paradata.

## What Changes

- The about page's roles table gains one row for content contributors, painted from the crate's
  `[guide] contributors` Person entities, with each name linked to its reviewed ORCID iD, in Czech and English.
  The existing roles (analysis authors, editor, editorial review, tools, funding) keep their wording.
- Release preparation writes `.zenodo.json` `contributors` from the reviewed `[guide] contributors` and
  `[[person]]` records: the person's name, bare ORCID iD, reviewed structured affiliation ROR IDs, and the
  DataCite contributor type `DataCurator`. Version and date behaviour is unchanged, and the release owner still
  edits no credit by hand.
- `check_citation_metadata.py` reconciles Zenodo contributors with the Guide's contributors (identity,
  ORCID, affiliation ROR IDs, type) and keeps the existing rule that Zenodo creators equal CFF software authors.
  A drift is reported before tagging.
- `docs/deployment.md` and `docs/content-model.md` record that CFF owns software authorship, Zenodo additionally
  carries content contributors, and the Guide's `contributors` list is the single authored source for both the
  about page and the archive mirror.
- Karel Berka becomes the first credited contributor through his existing reviewed person record; no new
  person, ORCID or affiliation is introduced.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-experience`: the requirement *Credit for content and compilation* gains content
  contributors as a named role on the about page, still distinct from the compiler-as-editor citation.
- `fair-guide/guide-delivery`: *Zenodo metadata preserves shared credit and curated archive fields* gains the
  prepared contributors mirror, and *Citation checks validate CFF and the effective Zenodo import format* gains
  the reconciliation rule between the Guide's contributors and Zenodo contributors.

## Impact

- `content/guide.toml` — no shape change; the existing `contributors` list and person records are the source.
- `content/ui.toml` — one bilingual label for the new credits row; `content/pages.toml` — the credits
  introduction mentions contributors alongside the editor and analysis authors.
- `scripts/build_crate.py` — `build_credits` emits the contributors row (with ORCID links) for the page.
- `scripts/release_versions.py` — preparation writes `.zenodo.json` contributors from the reviewed list.
- `scripts/check_citation_metadata.py` — contributor reconciliation in the offline checker and its Zenodo profile.
- `.zenodo.json` — a `contributors` array for the first credited content contributor.
- `docs/deployment.md`, `docs/content-model.md` — the credit split and the single authored source.
- Tests: `tests/test_citation_metadata.py`, `tests/test_release_versions.py`, `tests/test_content.py` (credits
  building), the page checks for the new row and its reflow; a visual pass of the about page in both languages.
- `content/provenance.toml` — one provenance action for this change; no `CHANGELOG.md` `[Unreleased]` line,
  because the change is neither breaking, a required step nor a security fix.
- Excluded: any change to `CITATION.cff`, creators, funding notes, curated Zenodo references or relations; a
  per-contributor DataCite type (a fixed `DataCurator` is recorded as a residual until a contribution that is
  not content curation appears); hand edits to the prepared release branch.
