# Tasks

## 1. Preserve existing repairs and prepare the normal change

- [x] 1.1 Verify the repository-context repair from `6d15974f1215103e5140c7957277e58ab60bbc50` and license correction from `ceb5f79008a26a86dd1bc150d226b7b45bb91c2b` remain in the published main ancestry. Keep the current branch, published commits, initial-alpha archive and release tag intact.
- [x] 1.2 Preserve the reviewed CFF/Zenodo additions and existing repair behavior; verify `node tests/page/check_release.mjs` passes and `python -m unittest discover -s tests -p test_workflows.py` retains repository-getter regression coverage.
- [x] 1.3 Remove the abandoned local history candidates and their recovery refs/scratch exports, reconcile the change artifacts with ordinary PR delivery, and prepare the scoped normal-commit diff without committing or pushing. Verify existing main/topic/tag refs and unrelated staged content are preserved.

## 2. Collect and render the complete release history

- [x] 2.1 Extend `scripts/release_versions.py` with a read-only, SHA-bound history export and deterministic first-parent commit records alongside the existing full-ancestry PR scope. Add real Git fixtures in `tests/test_release_versions.py`; verify previous-tag, first-release, off-branch and empty-history cases with `python -m unittest discover -s tests -p test_release_versions.py`.
- [x] 2.2 Extend `.github/scripts/prepare-release.cjs` collection with complete paginated commit-to-PR associations and separate structured association data; move Python setup/history export before collection in `prepare-release.yml`. Verify complete pagination, source binding, read failures and no remote writes during collection through `node tests/page/check_prepare_release.mjs` and `python -m unittest discover -s tests -p test_workflows.py`.
- [x] 2.3 Render merged PRs and uncovered direct commits in the Python changelog owner, validating association completeness and escaping subjects before mutation. Add commit-only, mixed ordinary/squash/rebase, duplicate-title, malformed-input, empty-history and preserved-old-section fixtures; verify the focused Python and JS release fixtures pass and the original empty-PR regression is accepted.
- [x] 2.4 Update preparation descriptions, PR-body wording and provenance instrument text to describe the complete release history; document commit-only and mixed inputs in `docs/deployment.md` and `CONTRIBUTING.md`. Verify the documented default still opens a release PR and no workflow gains a direct push or automatic tag path.

## 3. Maintain and validate CFF and Zenodo metadata

- [x] 3.1 Enroll `.zenodo.json` in `.github/release-prepared-files.json` and extend the Python release owner to update its version/publication date before manifest emission. Update Python and JS fixtures that hard-code the old file sets; verify the exact expanded permitted set, digests, refusal-before-write behavior and preserved unrelated Zenodo fields in the focused release tests.
- [x] 3.2 Add the read-only `scripts/check_citation_metadata.py` and matching `tests/test_citation_metadata.py`, using the pinned check dependencies. Validate CFF, the documented importer-compatible Zenodo profile, shared citation identities/fields and version/date agreement. Verify supported structured ROR affiliations pass, stale or malformed values and unsupported license arrays fail, report credits stay separate, and curated fields survive preparation with `python -m unittest discover -s tests -p test_citation_metadata.py` and the release-version fixtures.
- [x] 3.3 Register the checker once in `scripts/check_all.py` for local and CPU-lane execution; install the pinned metadata-check tools and invoke it in Prepare release and Tag release before delivery or tag creation. Add workflow/inventory regression fixtures; verify failing metadata blocks mutation and the checker appears exactly once in local/CI coverage with the relevant workflow and CI tests.
- [x] 3.4 Document field ownership, supported structured affiliations, the outdated-schema discrepancy, the reported Zenodo failure's evidence limit, and local validation commands in `docs/deployment.md` and contribution guidance. Verify documented commands run and make a clear distinction between generic CFF validity, importer compatibility and actual remote archive acceptance.

## 4. Tag committed metadata independently of PR ancestry

- [x] 4.1 Add requested-release validation to `scripts/release_versions.py` for consistent owning versions/dates and exactly one matching, nonempty dated changelog section, retaining ordinary metadata-check behavior. Verify missing, duplicate, empty and mismatched sections fail, valid direct metadata passes, and rejection precedes writes in `tests/test_release_versions.py`.
- [x] 4.2 Pass the requested version to that validation before write credentials in `tag-release.yml`; replace release-PR ancestry gating in `.github/scripts/prepare-release.cjs` with the shared content-validation flow. Update version/step descriptions and keep the final default-branch check, explicit status and immutable annotated tag. Verify PR and direct-commit success, stale/non-default refs, version/status errors, Zenodo validation failure and existing-tag refusal in `node tests/page/check_prepare_release.mjs` and `tests/test_workflows.py`.
- [x] 4.3 Document both tagging routes, their checks and the post-release concept-DOI badge hand-off in `docs/deployment.md` and `CONTRIBUTING.md`; reconcile PR-default wording with authorized maintainer direct commits. Update `.agents/guide/rules/fair-guide-surfaces.md` and regenerate its outputs with `python scripts/generate_agent_surfaces.py`. Verify native ownership/delivery checks pass, historical recovery and separate publication remain documented, and no unissued DOI or placeholder badge is added to either README.

## 5. Validate the integrated release change

- [x] 5.1 Run the focused citation-metadata, release-version and workflow Python tests plus `node tests/page/check_prepare_release.mjs` and `node tests/page/check_release.mjs`; verify the original failures and new stale-metadata cases are detected against the prior behavior, while context preservation, permitted-file/digest and interrupted-PR recovery fixtures pass with the implementation.
- [x] 5.2 Run the repository's Python lint, CFF/Zenodo checker and `npm run openspec:validate`, then `python scripts/check_all.py` for full native close-out. Record actual coverage, the scoped commit diff and environmental limitations in the existing change records; verify offline fixtures create no real tag, release or default-branch commit.

## 6. Address PR 68 review 5564997969

- [x] 6.1 Reconcile the durable unchanged-release recovery requirement, its delta and design with current-head dispatch selection and manual-only historical recovery; clarify `docs/deployment.md`. Verify strict OpenSpec validation and the existing immutable-tag, current-head and stale-source JavaScript fixtures.
- [x] 6.2 Pin the citation checker's direct dependency to `jsonschema==3.2.0`, compatible with `cffconvert==2.0.0`. Verify the installed check environment satisfies both declarations, the offline citation checker and its focused tests pass, and dependency metadata are consistent.
- [x] 6.3 Reconcile both README contribution sections with PR-default delivery and explicitly authorized maintainer direct commits under the same release checks. Keep agent permissions and branch protection intact; check bilingual equivalence, contribution guidance and whitespace.

## Workflow follow-up

- Present the normal commit diff for delivery through the existing PR workflow. Preserve published main history and the existing repairs; committing and pushing require their own direct order.
- After approved delivery, verify the changed workflows on the default branch and confirm the Zenodo integration is enabled. The maintainer separately authorizes preparation of the next version, tagging and release publication; inspect the actual Zenodo archive outcome. A failed archive remains pending and does not justify moving the old tag.
- After Zenodo successfully archives the corrected new release, retrieve the actual concept DOI and add its badge/link to both `README.md` and `README_en.md` through the normal reviewed documentation route. Verify the badge and all-versions destination; preserve exact-version DOI distinctions and do not insert placeholders before issuance.
- Verify implementation against this change before requesting archive; archive requires fresh authorization and must not be inferred from completed planning or tasks.
