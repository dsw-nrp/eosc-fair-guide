# Credit content contributors

## Kilo Code session (explore, plan and apply)

- **When:** 2026-11-01 (+01:00)
- **Agent / runtime:** Kilo Code (VS Code extension)
- **Model / backend:** deepseek-v4.1-flash-thinking (e-infra-cz)
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** `openspec-explore` (the maintainer confirmed the capture of the change and its artifacts),
  `openspec-apply-change`; delivered `aiscr-planning-core`, `aiscr-quality-first-execution`, `aiscr-usage-logging`,
  `aiscr-model-logging` and `aiscr-openspec-posture` rules; the native `fair-guide-content` and `fair-guide-surfaces`
  rules; pinned `npx openspec` CLI; `gh` reads of PR 165; Playwright page checks and screenshots of the built Guide.
- **What:**
  - Captured the change `credit-content-contributors` after exploring how Karel Berka's content credit is recorded:
    `[guide] contributors`, four provenance actions and the crate's `schema:contributor`, but no reader-facing row
    and no archive entry. Established that CFF 1.2.0 rejects a `contributors` field (validated against the schema in
    use) and that `.zenodo.json` accepts DataCite contributor types.
  - Implemented the change on `agents/kilo/credit-content-contributors`, branched from `origin/main`; the checkout
    stood on the App-owned `release/1.0.0-alpha.5` branch, where a hand commit would break the prepared-file policy,
    so no work was done there.
  - About page: `build_credits()` emits a content-contributors row from `[guide] contributors` with ORCID links and
    omits it when empty; `ui.toml` gains the bilingual label and the credits introduction names the role.
  - Release preparation writes `.zenodo.json` `contributors` from the same reviewed records (authored name, bare
    ORCID iD, structured ROR affiliation or the English name alone, type `DataCurator`), and omits the key when the
    list is empty; the affiliation shaping is shared with the creator validation.
  - `check_citation_metadata.py` reconciles contributors with the Guide and keeps Zenodo creators equal to CFF
    software authors; CFF stays unchanged.
  - Tests: the credits row (ORCID, name-only, empty), the page assertions (row, ORCID links, citation excludes the
    contributor, reflow at 320 px with a planted regression), the preparation writer (contributor, name-only, scalar
    affiliation, empty list, curated fields preserved) and the reconciliation drifts (name, ORCID, affiliation, type,
    missing, unknown).
  - Documented the split and the generation in `docs/deployment.md` and `docs/content-model.md`; added one provenance
    action and registered its identifier. `CHANGELOG.md` stays untouched.
  - Committed on `agents/kilo/credit-content-contributors` and opened as
    [dsw-nrp/eosc-fair-guide#166](https://github.com/dsw-nrp/eosc-fair-guide/pull/166).
- **Impacted:** `.zenodo.json`; `content/identifiers.toml`; `content/pages.toml`; `content/provenance.toml`;
  `content/ui.toml`; `docs/content-model.md`; `docs/deployment.md`; `scripts/build_crate.py`;
  `scripts/check_citation_metadata.py`; `scripts/release_versions.py`; `tests/page/check_page.mjs`;
  `tests/test_citation_metadata.py`; `tests/test_release_versions.py`; `tests/test_scripts.py`;
  `openspec/specs/fair-guide/guide-delivery/spec.md`; `openspec/specs/fair-guide/guide-experience/spec.md`;
  `openspec/changes/archive/2026-11-01-credit-content-contributors/`.
- **Verification:** `python scripts/check_all.py` reports 36 of 36 checks; `npm run check:page` fails on a planted
  missing row and passes on the real build; `npx openspec validate credit-content-contributors --strict` and
  `npm run openspec:validate` pass; `node tests/page/check_prepare_release.mjs` and
  `python -m unittest tests.test_workflows` pass; `python scripts/check_docs.py` reports 37 documents;
  `python scripts/check_citation_metadata.py` is green; the built `ui.js` credits and `.zenodo.json` were inspected.
  The visual pass over the about page in both languages at desktop and phone widths is captured under
  `.cache/screenshots-about/` and was reviewed and accepted by the maintainer on 2026-11-01 (task 1.4 records it).
  After the verification pass, `tests.test_release_versions` gained the contributor with no ORCID iD (the declined-iD
  scenario), `tests/page/check_page.mjs` checks the Czech about page at 320 px as well, and the contributor
  reconciliation matches by ORCID iD before falling back to the name, so a name drift and a duplicate entry are
  reported separately (`tests.test_citation_metadata` covers both).
- **Close-out:** all tracked tasks are complete. The main specs were synced (1 MODIFIED and 3 ADDED requirements,
  verified verbatim against the delta) and the change is archived as
  `openspec/changes/archive/2026-11-01-credit-content-contributors/`; `openspec archive` confirmed no further spec
  changes. Merge the branch, then re-run Prepare release for the untagged version instead of editing the release
  branch.
- **Corrections:** the maintainer first proposed deriving the about-page credits from `.zenodo.json` and folding the
  work into PR 165; the session showed the build-input and source-of-truth cost and the prepared-file policy, and the
  maintainer accepted Guide-first generation at release preparation in its own change. The maintainer then proposed
  listing all FAIR-analysis authors as contributors by default; after the credit-separation evidence the maintainer
  kept the basis credit separate, and those authors enter the list only when they contribute directly. The verification
  pass reported the visual pass as unrecorded; the maintainer confirmed it was done, so task 1.4 now records it, and
  the verification warnings and suggestions were fixed: an ORCID-less contributor test, the Czech 320 px reflow case
  and ORCID-first contributor matching with a duplicate-entry diagnostic.

## Review-fix session (2026-11-01)

- **When:** 2026-11-01 (+01:00)
- **Agent / runtime:** Kilo Code (VS Code extension)
- **Model / backend:** `deepseek-v4.1-flash-thinking` (e-infra-cz), exposed by the runtime
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** `aiscr-review-pr` (review of PR 166, findings not posted), delivered
  `aiscr-review-conduct`, `aiscr-planning-core`, `aiscr-quality-first-execution` and `aiscr-model-logging` rules, the
  native `fair-guide-content` and `fair-guide-surfaces` rules, `python scripts/check_all.py` job inventory and the
  Playwright page checks.
- **What:**
  - Reviewed PR 166 without posting the findings, then fixed the three Low observations the review reported.
  - `reviewed_affiliations()` keeps every reviewed organisation for a person with any ROR affiliation: an
    organisation without a ROR enters the structured list as a name-only entry, and the scalar `affiliation` stays
    the form only when no organisation carries a ROR. This makes the writer match the synced requirement that an
    organisation without a ROR be written by its English name.
  - `docs/deployment.md` now states that a pull request adding someone to `[guide] contributors` also mirrors the
    entry into `.zenodo.json`, because `check_citation_metadata.py` runs in the pull-request checks and before
    preparation.
  - This entry no longer says that no commit, push or pull request was made; it names the branch and PR 166.
  - Added the mixed-affiliation preparation test.
- **Impacted:** `.agents/reports/usage/usage-2026-11-01-credit-content-contributors.md`; `docs/deployment.md`;
  `scripts/release_versions.py`; `tests/test_release_versions.py`.
- **Verification:** `python -m unittest tests.test_release_versions tests.test_citation_metadata tests.test_scripts`
  passes, `python scripts/check_citation_metadata.py` is green, and `python scripts/check_content.py --base origin/main`,
  `python scripts/check_docs.py` and `python scripts/check_usage.py` pass.
- **Close-out:** the review run directories are retained because no review was posted; the fixes are committed on the
  pull-request branch and the summary is prepared for the description.
