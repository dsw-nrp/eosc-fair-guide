# Proposal

## Why

Prepare release currently refuses a release containing only direct commits to `main`, as demonstrated by
[run 39135668252](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/39135668252). Tag release also requires
the current commit to be the merge commit of a release PR, blocking otherwise valid committed release metadata.
The maintainer also reports a rejected Zenodo release. Build on the existing software-license correction and
deployment repair while adding reviewed archive metadata and release-time validation.

## What Changes

- Keep release preparation through a PR as the default, including for releases whose source changes were
  committed directly to `main`.
- Generate release changelogs from merged PRs and direct default-branch commits since the previous reachable
  release tag, with commit links and no duplicate entries for changes already represented by a PR.
- Permit the manual tag dispatch to tag the current default-branch commit when its committed version,
  release dates and changelog are valid, without requiring release-PR ancestry.
- Reconcile the historical recovery contract: the dispatch selects the current head, while re-issuing an
  unchanged historical release remains a manual operation at its original release merge commit.
- Preserve the existing repository-context repair and MIT software-license correction, including their
  regression coverage. Deliver this change through a normal commit and PR with the published history intact.
- Adopt the staged `CITATION.cff` additions and `.zenodo.json`; keep their shared software citation metadata,
  version and dates consistent, retain the structured ROR affiliations and curated Zenodo-specific fields,
  and validate both CFF correctness and Zenodo-import compatibility before tagging.
- Keep explicit version and release-status selection, empty-release refusal, immutable annotated tags and
  the existing verified deployment, container and draft-release chain.
- After the corrected release is successfully archived by Zenodo, add its real concept-DOI badge to both
  README languages. Keep exact-version citation identifiers distinct from that all-versions DOI.
- Add regression fixtures for commit-only and mixed histories, direct metadata commits, and existing refusal
  and recovery behavior. Document the default PR flow and the direct-commit alternative.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-delivery`: accept direct commits as release input and tag targets, maintain valid CFF
  and Zenodo metadata through the release lifecycle, and expose the issued concept DOI after archiving,
  while retaining the PR default, manual dispatches and repaired deployment behavior.

## Impact

Implementation affects `scripts/release_versions.py`, `.github/scripts/prepare-release.cjs`, their workflow
steps and tests, `.github/release-prepared-files.json`, `CITATION.cff`, `.zenodo.json`, `docs/deployment.md`,
`CONTRIBUTING.md`, and guide-owned release guidance. Both READMEs describe the PR default and authorized
maintainer direct-commit exception; they receive the badge only after an actual DOI is issued. The existing
deployment repair, published commits, archive and release tag stay in place.

No new application runtime dependency or public data/API change is needed. Use the existing pinned check
tools for metadata validation and declare the checker's direct `jsonschema` dependency compatibly with
`cffconvert`. No automatic direct push of prepared metadata, release on every push,
automatic draft publication, automatic protection relaxation or tag movement is proposed.

Validate with real Git-history fixtures and mocked GitHub delivery fixtures, strict OpenSpec validation,
the repository's Python lint and full native close-out. Add fixtures for stale Zenodo metadata, preserved
custom fields and Zenodo's single-license import constraint. Verify the normal commit diff retains the existing
repairs and reviewed metadata. PR delivery, tagging, release publication and Zenodo acceptance remain separate
operator hand-offs; planning and offline tests do not establish them.
