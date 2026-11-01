# Tasks

## 1. About page credit row

- [x] 1.1 Add the `contributors` role to `build_credits()` in `scripts/build_crate.py`, linking each person to their ORCID iD and omitting the row when the list is empty; verify `python -m unittest tests.test_scripts` covers a fixture with an ORCID, one without, and an empty list.
- [x] 1.2 Add the bilingual row label to `[credits]` in `content/ui.toml` and mention content contributors beside the editor and analysis authors in the credits introduction in `content/pages.toml`; verify `python scripts/check_content.py` accepts both texts and the two languages say the same thing.
- [x] 1.3 Extend `tests/page/check_page.mjs` to assert the contributors row, its ORCID links, its reflow at 320 px and that the footer citation still names only the editor; verify `npm run check:page` fails on a planted missing row before it passes on the real build.
- [x] 1.4 Run the visual pass on the about page in Czech and English at phone and desktop widths and review the row for wrapping, spacing and wording; verify the captured screenshots show no collision or misalignment and record what was reviewed. Recorded: `.cache/screenshots-about/` holds the Czech and English about page at 1280 and 390 px, with the contributors row visible in both languages; the maintainer reviewed the captures on 2026-11-01 and accepted the row's wrapping, spacing and wording without a change.

## 2. Archive record written by release preparation

- [x] 2.1 Teach `release_versions.prepare()` to write `.zenodo.json` `contributors` from `[guide] contributors` and the person records (authored name, bare ORCID iD, structured ROR affiliations, type `DataCurator`, no key when the list is empty); verify `python -m unittest tests.test_release_versions` covers a prepared contributor, a contributor without an ORCID iD, an empty list, and untouched curated notes, references and relations.
- [x] 2.2 Share the affiliation shaping with the creator path and write the scalar English affiliation only when the reviewed organisation has no ROR, never both forms; verify a unit test covers the scalar fallback and rejects the mixed form.
- [x] 2.3 Confirm `.github/release-prepared-files.json` still matches what preparation writes; verify the permitted-set assertion passes in `tests/test_release_versions.py` and `python scripts/release_versions.py prepare` refuses a path outside the policy.

## 3. Reconciliation in the citation checks

- [x] 3.1 Compare every `.zenodo.json` contributor with the Guide's reviewed person in `scripts/check_citation_metadata.py` (name, ORCID iD, affiliation ROR IDs or scalar name, DataCite type) and report the file and entry; verify `python -m unittest tests.test_citation_metadata` covers a name, ORCID, affiliation and type drift, and a contributor missing from the archive.
- [x] 3.2 Keep the creators == `CITATION.cff` authors rule and leave CFF without a `contributors` field; verify a fixture with contributors only in `.zenodo.json` passes the CFF schema and the order check, and `python scripts/check_citation_metadata.py` is green on the repository.
- [x] 3.3 Update the offline profile fixtures only as far as the new contributor rules need; verify `python -m unittest tests.test_citation_metadata -v` reports no skipped fixture.

## 4. Documentation and provenance

- [x] 4.1 Record the credit split and the generation direction in `docs/deployment.md` (Citation and Zenodo metadata) and the `guide.toml` row in `docs/content-model.md`; verify `python scripts/check_docs.py` accepts the declarations, links and named files.
- [x] 4.2 Add one provenance action for this change naming the responsible person, the instruments used, the consulted sources and the changed items, and register its identifier; verify `python scripts/register_ids.py` then `python scripts/check_content.py --base origin/main` reports no unregistered or uncovered item.
- [x] 4.3 Keep `CHANGELOG.md` untouched, since the change is neither breaking nor a required step nor a security fix; verify `python scripts/check_all.py` still reports the changelog checks green.

## 5. Integration

- [x] 5.1 Verify `npx openspec validate credit-content-contributors --strict` and `npm run openspec:validate` accept the change and every delta requirement has its scenario.
- [x] 5.2 Verify `python scripts/check_all.py` and `npm run check:page` pass on the built site, including the release-path fixtures `node tests/page/check_prepare_release.mjs` and `python -m unittest tests.test_workflows`.
- [x] 5.3 Inspect the built about page and, in the prepared release pull request, `.zenodo.json`: Karel Berka appears with his ORCID iD in the contributors row and as a `DataCurator` contributor, and neither record presents him as a software author.

## Workflow follow-up

- Merge the implementation pull request into `main` through the normal review and queue.
- Re-run **Prepare release** for the untagged version, never hand-editing the release branch, and confirm the App-owned pull request now lists the merged PR and carries the contributor.
- Tag release, publish and archive remain separate maintainer actions.
- Archive this change once the merged result and the prepared archive record are verified.
