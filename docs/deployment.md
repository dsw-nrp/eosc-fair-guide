# Production and preview deployment

Production is the most recent successfully deployed release tag's verified artifact. A default-branch push builds `/next/` and reuses
that artifact, preserving every production byte. A new release tag builds and checks its source once, packages
the exact output and assembles it with a checked default-branch preview. The Pages deployment replaces the whole
combined tree. Pull-request checks remain read-only and do not deploy.

Before the first verified release, the root states that no release is published and links to the preview. It does not serve
unreleased Guide content as production. With an existing release, failure to retrieve or verify its artifact
stops deployment; there is no substitution from the default branch.

The deployment resolves immutable source commits first. Both sites record the commit actually checked through
`FAIR_GUIDE_CHECK_REVISION`; a tag-triggered workflow can check a different default-branch commit for its preview.
The release archive is checked against its tag/version, source commit, digest and passed health report. Unsafe
archive members, input/output overlaps and path collisions are refused before replacing the managed assembly.

Release assets are the durable production source. While a new tag's draft release has not yet been created,
the successful tag deployment's commit-labelled Actions artifact is the fallback. Artifact expiry or incomplete
release assets without that fallback cause a failed deployment and leave the existing published site in place.
A failed attempt to deploy a newer tag does not supersede the previous verified production source or block
updates to `/next/`. Retrying an already verified tag reuses its artifact rather than rebuilding production.

## Preview behaviour

Every HTML page below `/next/`, including API, profile, health and local-test documentation, carries `noindex`
and a visible bilingual prerelease notice. Staging is unlisted, not private. Production's sitemap and linkset
remain unchanged and do not gain preview entries. The preview retains shared knowledge-base identifiers and
its existing discovery data; its OpenAPI server is relative to its own description so API requests use `/next/`.

`scripts/assemble_pages.py` adds these deployment-only changes after both inputs pass. It does not rebuild,
fetch, tag or publish. Production is never transformed. A new deployment can update the preview without
replacing production with new default-branch content.

## Release artifact and activation

The release workflow runs after a successful tag deployment using trusted default-branch code. It confirms
the completed run's repository, workflow path, event, tag and commit, checks that the tag has not moved, and
downloads that run's exact release artifact. Digest, version and passed health are checked before drafting the
release. The archive attached to the draft is the production site that was deployed.
An interrupted upload resumes on the existing draft and uploads only missing assets, after confirming existing
assets have exactly the same bytes. A complete existing release is unchanged. Conflicting assets or missing
assets on a published release are refused; human changes are not overwritten or deleted.

The prepared workflows are inactive until delivered to the default branch, Pages is configured and the
maintainer authorizes deployment. Local fixture checks do not establish remote activation. Creating a tag and
publishing a release remain explicit maintainer actions.

GitHub's [workflow-run documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)
describes the completed-run trigger and its security boundary.

## Local assembly check

Run `python -m unittest discover -s tests -p test_assemble_pages.py` and
`node tests/page/check_release.mjs`, then `npm run check:deployment` for the real browser and Swagger request.
The fixtures cover production preservation, all preview HTML pages,
first-tag absence, source selection, durable byte reuse and refused malformed/mismatched artifacts.

To assemble already checked inputs without publishing:

```bash
python scripts/assemble_pages.py --staging _site --staging-commit <checked-preview-sha> --production .cache/release --production-tag <release-tag> --production-commit <checked-release-sha> --out .cache/pages
```

Omit the three `--production*` arguments to exercise the state before the first release. The preview must have
a completed passing health report naming its supplied commit. The production directory holds `manifest.json`,
the release archive and its checksum. Open `.cache/pages/index.html` or serve that directory locally to inspect
both the production root and `/next/`; this command does not change `_site/`.

## Release preparation and tagging

Run **Prepare release** (`prepare-release.yml`) on the default branch with a SemVer version without `v`.
The standard-library owner `scripts/release_versions.py` writes the Guide's version and `datePublished`, the
root `CITATION.cff` version and `date-released`, npm's manifest and both lockfile root versions, and the Python
project version. The build derives the crate and API values from the Guide; generated files are never patched.
The citation's referenced works retain their original versions and dates. No release status or testing notice
changes automatically.

The workflow retrieves every page of closed pull requests for the default branch. The script finds the nearest
reachable release tag and selects merged PRs whose merge commits belong to that tag-to-HEAD ancestry (all HEAD
ancestry for the first release). It writes the complete PR list into the release's changelog section, preserving
earlier released sections. Unmerged PRs and changes outside this history are excluded; an empty list is refused.
This includes squash and rebase merges through GitHub's recorded `merge_commit_sha`. Direct commits have no PR
entry and should be reviewed before preparation. A release can collect several merged PRs.

Preparation records the dispatcher using a reviewed `person.github` identity and the deterministic script as
instrument. Add a new dispatcher's reviewed identity and citation credit through an ordinary content PR first.
The preparation timestamp and release date come from the workflow run's start in UTC, so retrying that run
produces the same proposed bytes. The dispatch opens `release/<version>` with just the owning metadata,
changelog, provenance and identifier register. It refuses an edited or outdated release branch and never moves
it or reopens a closed proposal. A retry can finish opening a PR after branch creation was interrupted.

Review and merge that release PR, then run **Tag release** (`tag-release.yml`) on its current default-branch
merge commit with the same version. It checks the metadata and the merged PR, creates `v<version>` once and never
moves an existing tag. If further commits landed after the release merge, reconcile the release through review
before tagging; the dispatch refuses to tag those different bytes. Tag creation starts the checked production
build described above; publishing the resulting draft release is still a separate maintainer act.

Both dispatches use the existing repository-scoped App (`SOURCE_REFRESH_CLIENT_ID` and
`SOURCE_REFRESH_APP_PRIVATE_KEY`), with Contents and Pull requests read/write at installation and narrower tokens
per job. The App's PR and tag events trigger normal checks and deployment. GitHub documents this distinction
in [workflow triggering](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
Default-branch-only jobs and checkout credentials disabled keep the App token out of PR execution. These
prepared workflows have not been activated or dispatched remotely.

`python scripts/release_versions.py check --site _site` checks all versions and dates, the built crate and
documentation that restates the Guide version. `check_all.py` runs it with the other deterministic checks.
Run `python -m unittest discover -s tests -p test_release_versions.py` and
`node tests/page/check_prepare_release.mjs` for offline metadata, history, identity and delivery fixtures.

For the opt-in acceptance probes, run `npm run check:live-release`. It requests the four citation formats for
one DataCite and one Crossref DOI, verifies that Czech ISO differs from APA, then runs the Guide's twelve
FAIR-Checker metrics against a public dataset after confirming its DataCite type. It uses real browser requests
and saves a compact receipt in `.cache/live-release/receipt.json`. Missing native results fail this probe;
they do not become failed FAIR criteria. The general `check:live` suite covers additional services separately.
