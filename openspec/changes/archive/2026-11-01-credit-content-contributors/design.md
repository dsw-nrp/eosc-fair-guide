# Design

## Context

See [proposal.md](proposal.md) — Why. The relevant current state:

- `content/guide.toml` owns `[guide] contributors` and the `[[person]]` records (name, ORCID iD, organisation IDs,
  `github`, `commitNames`, `orcidOptOut`); `check_content.py` validates every listed contributor against
  `[[person]]`, and `build_crate.py` already emits each contributor as `schema:contributor` on the Guide entity.
- `build_crate.build_credits()` builds the about page's roles table from the same file, but emits only the
  analysis authors, editor, review, tools and funding.
- `check_citation_metadata.py` requires `.zenodo.json` `creators` to equal `CITATION.cff` `authors` in order and
  validates each creator's structured ROR affiliations against `content/guide.toml`. It also accepts a Zenodo
  `contributors` array (DataCite types) and validates nothing in it.
- `CITATION.cff` declares `cff-version: 1.2.0`; that schema has `additionalProperties: false` and no
  `contributors` key, so a contributor entry there is rejected by the repository's own validator.
- `release_versions.prepare()` already writes `.zenodo.json` version and date, and refuses to write anything
  outside `.github/release-prepared-files.json`; `.zenodo.json` is in that permitted set.

## Goals / Non-Goals

**Goals:**

- One authored list, in `content/guide.toml`, produces both the about-page row and the archive mirror.
- The archive mirror is written by the existing release preparation, so the release owner edits no credit by hand
  and the prepared release pull request already owns the file.
- A hand edit to either side is reported before a tag is created.
- The credit split stays legible: analysis authors, compiler as editor, content contributors, software authors.

**Non-Goals:**

- Changing `CITATION.cff`, Zenodo creators, funding notes, references or relations.
- Naming contributors in the footer citation; it keeps naming the compiler as editor.
- A per-person DataCite type, a contributor editing interface, or any change to how provenance actions are authored.
- Any build-time dependency on `.zenodo.json` (see D1).

## Decisions

### D1. The Guide's list is authoritative; the archive record is generated

`build_crate.py` reads `[guide] contributors` for the page, and `release_versions.prepare()` reads the same list
and person records to write `.zenodo.json` `contributors`. The direction is Guide → archive, never archive → page.

Alternatives considered:

- **Build reads `.zenodo.json`.** Rejected. It makes a release artifact a build input, requires joining Zenodo
  names ("Berka, Karel") back to Guide person IDs by ORCID or by name to keep ORCID links and
  `schema:contributor` consistent, moves contributor validation out of the content checks, and needs a bilingual
  mapping for the English DataCite enums — more machinery than the page needs, and against invariant 3
  (content authored in `content/*.toml`).
- **Hand-mirrored list.** Rejected: two edits per person and no check that they agree; generation is the same
  amount of code and removes the drift.

### D2. A fixed DataCite type, `DataCurator`, for now

Content contribution is authoring and curation of the advice records, which fits `DataCurator`; `Editor` would
collide with the Guide's "editor = compiler" role in its citation, and `Other` says nothing. The enum never
reaches a reader: the about page shows a content label, not the DataCite term.

Alternative considered: a per-person `contributorRole` on `[[person]]`. Deferred — it is a new authored field for
a case that does not exist yet, and it would widen this change. When a contribution that is not content curation
(for example translation) is credited, its own change adds the field; the fixed type is the residual until then.

### D3. Contributors are written with the authored name and bare identifiers

Each entry carries `name` exactly as written in `[[person]].name`, the bare ORCID iD (`0000-…`) when recorded and
not opted out, and affiliations in the creator shape: `[{"id": "<ROR suffix>", "name": "<reviewed English name>"}]`
for organisations with a `ror`, otherwise the scalar `affiliation` with that name, never both.

No name inversion: Zenodo's `contributors[].name` is free text, and parsing "Karel Berka" into "Berka, Karel"
would guess at Czech name order and particles. The existing creators keep their curated "Family, Given" form; the
checker compares contributors exactly and creators as today.

An empty `[guide] contributors` list writes no `contributors` key, so the file differs only in version and date.

### D4. The page row comes from the crate, not from a second lookup

`build_credits()` gains one role entry, `contributors`, built from the same `[[person]]` entities the crate emits.
A person with an ORCID iD is linked to it; a person without one is plain text. `ui.toml` gains one bilingual label
for the row; the table keeps one visual treatment for every role, so the row is a label and a list, not a new
component. Nothing is fetched at runtime and no page script changes.

### D5. The checker owns reconciliation, preparation owns the write

`check_citation_metadata.py` compares every Zenodo contributor with its Guide person: name, ORCID iD, affiliation
ROR IDs (or scalar name), and type, reporting the file and entry. It keeps the creators == CFF authors rule and
keeps CFF valid without a contributors field, recording the asymmetry rather than working around it.

Alternatives considered: generate and trust. Rejected — a hand edit to `.zenodo.json` or a stale prepared branch
would otherwise reach Zenodo, and the repository's rule is that a check is the gate, not a convention.

### D6. Documentation and release mechanics

`docs/deployment.md` (Citation and Zenodo metadata) and `docs/content-model.md` (`guide.toml`) record the split and
the generation. The implementation lands in its own pull request; the release branch is never hand-edited. After
that merge, **Prepare release** is re-run for the untagged version, so the App-owned release pull request gains the
merged PR in its changelog and writes the contributor itself. `.github/release-prepared-files.json` needs no change.

## Risks / Trade-offs

- **A fixed `DataCurator` type mislabels a future non-curating contribution** → the enum is never shown on the
  page; a per-person type is added by its own change when such a contribution appears.
- **Name or affiliation text drifts between the Guide and Zenodo** → the checker compares the authored name, ORCID
  iD and ROR IDs exactly, and preparation writes from the same records.
- **A contributor's organisation has no ROR** → the scalar English affiliation is written and checked, never both
  forms for one person (the same rule as creators).
- **The about page table row grows long** → names are a list that wraps and reflows; the page check covers 320 px
  and the visual pass covers both languages.
- **The prepared release pull request cannot be re-prepared** → it is only ever written by the App; if it was
  hand-edited the dispatch refuses and the reconciliation is manual, as documented for releases.

## Migration Plan

No data migration and no stored-format change. Reverting the implementation pull request removes the page row and,
on the next preparation, the Zenodo contributors; the persons themselves are unchanged, so no identity is lost.

## Open Questions

- Which DataCite type a future translation or data-curation-only contribution should carry, and whether that
  needs a per-person field (deferred by D2; its own change answers it).
