<!-- type: reference -->
# Production and preview deployment

Use the [release runbook](runbooks/release.md) to publish a version, [merge](runbooks/merge.md) for ordinary delivery,
and [maintainer tasks](ci.md) for other operations. This reference defines the channel and artifact contracts.

Production is the verified artifact of the newest approved release tag that its own deployment has published; the
preview (`/next/`, staging) is the newest checked default-branch commit. A default-branch push builds `/next/`, reusing the merge queue's result for the
same commit or running the partitioned checks, and preserves every production byte. A new release tag builds and
checks its source once, packages the exact output and waits for a maintainer's approval before those bytes are
published. Each Pages deployment replaces the whole combined tree. Pull-request and merge-queue checks remain
read-only and do not deploy.

Before the first verified release, the root states that no release is published and links to the preview. It does not serve
unreleased Guide content as production. With an existing release, failure to retrieve or verify its artifact
stops deployment; there is no substitution from the default branch.

The deployment resolves immutable source commits first. Both sites record the commit actually checked through
`FAIR_GUIDE_CHECK_REVISION`. The release archive is checked against its tag/version, source commit, digest and
passed health report. Unsafe archive members, input/output overlaps and path collisions are refused before
replacing the managed assembly.

Release assets are the durable production source. While a new tag's draft release has not yet been created,
the commit-labelled Actions artifact of the tag deployment whose production and approval jobs succeeded is the
fallback. Artifact expiry or incomplete release assets without that fallback cause a failed deployment and leave
the existing published site in place. A failed or unapproved newer tag does not supersede the previous verified
production source or block updates to `/next/`. Retrying an already verified tag reuses its artifact rather than
rebuilding production, and needs no second approval.

## Merge queue, staging and production

A pull request into `main` enters the merge queue after its own `checks` pass and the configured reviews
are satisfied. The queue runs `checks.yml` on the merged result (`merge_group`) and
merges only when it passes; human, Dependabot and refresh pull requests take the same path. Queue runs build the
`preview` channel, the bytes staging deploys.

**Staging.** A default-branch deployment builds the staging site and looks for the successful merge-queue run of
the same commit. When that run's source files and build inputs equal the fresh build's, the deployment imports its
validated health snapshot instead of checking again. Otherwise it runs the [partitioned
checks](../.github/workflows/partitioned-checks.yml), and the run summary says why: a direct merge, a run that
failed or expired, or a build on another day. Staging needs no approval.

**Production.** A tag run checks and packages its source, then its `approve-production` job waits in the
`production` environment for a maintainer when those bytes are new. The default branch keeps deploying meanwhile,
with the last approved production. Tag release needs a successful deployment of the current default-branch commit,
which the tag ruleset also requires, and otherwise names the run to wait for.

**Publication.** The deployment run (`deploy.yml`) only prepares. After each successful one, the separate
[publish workflow](../.github/workflows/publish.yml) runs trusted default-branch code, one publication at a time
(`pages-publish`), so cancelling a deployment run never interrupts a Pages deployment. A newer push cancels the
older run's preparation, and the cancelled run names its successor. Each publication resolves what to publish when
it starts:

- the newest approved release, from its release assets or the run that approved it;
- after a default-branch deployment, that run's own staging site while its commit is still the head; an older run
  publishes nothing and names the run for the head;
- after a tag deployment, the head's checked staging site beside the new production. While the head's own
  deployment is still preparing, the tag publishes nothing, and the head's publication then includes the release.

GitHub records each Pages deployment against the default-branch head when the publication started; a publication
therefore deploys only that commit's staging site. It decides in a job without an environment, so a publication
that deploys nothing leaves no record. Once the site is live, the publication also records each channel: a
successful `staging` deployment of the staging commit with the `/next/` address and, for a release it published, a
`production` deployment of the tag with the root address. Publishing the same site again records nothing new.
Tag protection requires successful `github-pages` and `staging` deployments and the `checks` status from GitHub
Actions on the commit to tag. Tag release also verifies its `staging` record, so only a staged commit is released.
`staging`, like `github-pages`, admits only `main`, and the record counts only when
GitHub resolves it to the published commit; Tag release also requires that a run of the publication workflow wrote
it. The `production` environment's approval job creates no record of its own. Only a publication
after a successful deployment waits for its turn; a newer one replaces an older waiting one and publishes at least
as much, since every publication resolves the newest approved release. To publish again, run **Deploy the verified
site** on the default branch rather than rerunning an older deployment run, whose rerun would cancel newer
preparation and then find its commit superseded. A release tag deploys only from its push: the dispatch refuses a
tag, and a failed tag deployment is retried by rerunning that run. No publication moves
either channel back, and a retry publishes the same identities again. The release workflow drafts a release, and
publishes its image, only after a publication has deployed that release to Pages.

**Break glass.** An administrator can merge directly, bypassing the queue, to repair a broken queue or required
check. Say why in the pull request. That commit has no queue result, so its deployment runs the full checks.

## Publication location and Guide namespace

Each deployable build resolves the actual Pages location from the Pages API before its checks and sets
`FAIR_GUIDE_BASE_URL`; `baseUrl` in `content/guide.toml` names the same HTTPS site for local and offline builds.
No build predicts a future hostname or looks one up over the network. The location gives the page's recorded
address, the sitemap and, at an origin root, `robots.txt`. At runtime, navigation, API references, shared links
and exported test references follow the Guide window's own address, including its channel path. From a local file
they use the recorded HTTPS location or stay relative when none is recorded, and never publish a filesystem path.

The Guide's own terms (`<namespace>terms#`) and RO-Crate profile (`<namespace>profile/<profileVersion>`) come from
`namespace` in `content/guide.toml`. It is a reviewed setting that does not follow the publication location, so
moving the site renames no term, and no deployment reads it from the live site or a release archive. Changing it
renames every Guide term: it is a breaking change made through a reviewed pull request and noted in the changelog.
Content from before the setting existed used its own `baseUrl`. Pull-request checks build for the resolved location,
or `baseUrl` when Pages cannot be read, and deploy nothing.

Packaging stamps the release manifest with `publication_url` and `semantic` (`vocabulary_base`, `profile`), read
from the archive's own crate and page configuration. Assembly verifies a stamp against the archive's contents; an
older archive without one is read from its verified crate, never from the current configuration. Assembly refuses a
stamped release built for another publication root than the preview. Merge-queue reuse compares every built file,
so a result checked for another namespace or root is not reused.

Between a namespace change and the next release, the preview names the new terms while production keeps those of
its release. Assembly accepts that pair, the publication summary names both namespaces, and the next release aligns
them. The first release with the Pages-root namespace follows releases that named `https://fair.eosc.cz/`. Earlier
archives keep their bytes and original contexts, so consumers read each artifact's own context and profile. No
alias, redirect or `sameAs` relates old and new term IRIs, and no custom domain is adopted.

Immediately before the Pages deployment, publication compares the actual Pages location with the root the staging
site was built for. A location that changed after the build deploys nothing, leaves the published sites in place
and names the deployment to rerun.

## Settings and rollback

The [audit runbook](runbooks/audit-settings.md) owns approved application of one settings diff; the
[rollback runbook](runbooks/rollback-a-setting.md) owns rollback. The table records preconditions and rollback values.

| Step | Precondition | Rollback |
| --- | --- | --- |
| Turn the merge queue on | `checks.yml` runs on `merge_group` on `main` | Remove the merge-queue rule |
| Switch off "require branches to be up to date" | The merge queue is on | Switch it on |
| Create `production` with its reviewer, for release tags only | None | Delete it and re-add the reviewer to `github-pages` |
| Remove the reviewer from `github-pages` and limit it to `main` | The `approve-production` job is on `main` | Re-add the reviewer and the `v*.*.*` tag rule |
| Create `staging` without reviewers, limited to `main` | Publication's channel records are on `main` | Delete it; Tag release then refuses until it exists again |
| Require both deployment gates and `checks` for release tags | A publication has recorded a successful `staging` deployment and the commit passed `checks` | Restore the reviewed previous policy only after approval of the exact recovery diff; preserve live gates while diagnosing |

## Preview behaviour

Every HTML page below `/next/`, including API, profile, health and local-test documentation, carries `noindex`
and a visible bilingual prerelease notice. Tag release tags a commit the preview already serves, built before the
tag existed, so while the preview and the published release share a commit the notice says that the preview is
identical to that release and links it; the preview's own footer keeps the identity it was built with. Staging is
unlisted, not private. The build writes `sitemap.xml` at the publication location, listing only the Guide root and
`api/index.html` as absolute, fragment-free URLs without modification dates. Hash views and the two languages are
not separate indexable pages, and adopting a custom domain is a separate decision.

A crawler applies only the `robots.txt` at its origin's root. The Guide is published at the project path
`https://dsw-nrp.github.io/eosc-fair-guide/` (26 October 2026), whose origin root this repository does not publish,
so the build writes no `robots.txt` there: a file below the project path would control nothing. The sitemap
is then found when submitted to a search engine's webmaster tools, not through robots. When the Guide is hosted at
an origin root, the build writes `robots.txt` allowing all paths and naming the sitemap; assembly refuses a release
whose robots policy would stop crawlers reading the preview's `noindex`. Preview pages stay crawlable so that
`noindex` keeps them out of search results. The current choice is to index the GitHub Pages site.

Production's crawler files and linkset stay byte for byte as released and gain no preview entries; the preview gets
no copy of either crawler file. The preview retains shared knowledge-base identifiers and its existing discovery
data; its OpenAPI server is relative to its own description so API requests use `/next/`.

`scripts/assemble_pages.py` adds these deployment-only changes after both inputs pass. It does not rebuild,
fetch, tag or publish. Production is never transformed. A new deployment can update the preview without
replacing production with new default-branch content.

## Release artifact and activation

The release workflow runs after a successful publication using trusted default-branch code. It confirms the
completed run's repository, workflow path and event, reads the publication's record of the release it deployed,
checks that the tag has not moved, and downloads the approved deployment run's exact release artifact. A
publication that deployed nothing or no release, or a release that already has its assets, drafts nothing. Digest,
version and passed health are checked before drafting the release. The archive attached to the draft is the
production site that was deployed.
An interrupted upload resumes on the existing draft and uploads only missing assets, after confirming existing
assets have exactly the same bytes. A complete existing release is unchanged. Conflicting assets or missing
assets on a published release are refused; human changes are not overwritten or deleted.

Activation requires delivery to the default branch, Pages configuration and maintainer authorization.
Local fixture checks do not establish remote activation. Creating a tag and publishing a release remain explicit
maintainer actions; track activation state and outstanding operator work in issues or an OpenSpec change.

GitHub's [workflow-run documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)
describes the completed-run trigger and its security boundary.

## Release status

Choose `release_status` in the **Tag release** (`tag-release.yml`) manual workflow alongside the merged version.
It is a required choice with default `testing` and these case-sensitive values:

| Value | Meaning | Published behaviour |
| --- | --- | --- |
| `testing` | Evaluation or editorial testing; the default workflow choice. | The bilingual testing notice is visible. |
| `production` | The responsible maintainer has approved the Guide for public use. | The testing notice is hidden on the clean tagged production build. |

The dispatch rejects missing or unrecognized values; `released` is not supported. Selecting `production`
requires the responsible maintainer's approval. Record that approval in the release issue or OpenSpec change.

The workflow creates an annotated tag with `Fair-Guide-Release-Status: testing` or
`Fair-Guide-Release-Status: production` and never moves an existing tag. Deployment selects that exact tag through
`FAIR_GUIDE_RELEASE_TAG`, verifies its commit and reads its annotation, with full tag history and
`FAIR_GUIDE_BUILD_CHANNEL=production`. No repository status variable is used. An unmarked manual/lightweight tag
defaults to `testing`; malformed or duplicate status markers fail the build.

Local, dirty and `/next/` builds always resolve to `testing`, even at a tag annotated `production`.
The build freezes the resolved value in UI configuration, health and
RO-Crate `creativeWorkStatus`; the manifest and image reuse it. Build channel (`release`, `next`, `local`)
describes source identity and is separate from release status (`testing`, `production`).

Existing tags, verified artifacts and images retain their recorded status; retries reuse their exact bytes.
A status change requires a new version and tag selected through **Tag release**, followed by a newly checked
artifact. It never relabels an existing release or changes a moving repository setting.

## Local assembly check

The [assembly how-to](how-to/verify-assembly.md) owns setup, fixture commands, checked inputs and local inspection.
Assembly accepts an already checked preview and an optional verified production archive; it never publishes.

## Release preparation and tagging

**Prepare release** (`prepare-release.yml`) accepts a SemVer version such as
`X.Y.Z` or `X.Y.Z-alpha.N`; both release dispatches also accept the tag form `vX.Y.Z-alpha.N` and use the bare version.
Release tags use `vX.Y.Z`, with an optional SemVer prerelease suffix.
The standard-library owner `scripts/release_versions.py` writes the Guide's version and `datePublished`, the
root `CITATION.cff` version and `date-released`, `.zenodo.json` version and `publication_date`, `package.json` and
both `package-lock.json` root versions, and the Python project version. The build derives the crate and API values from
the Guide; generated files are never patched.
The citation's referenced works retain their original versions and dates. No release status or testing notice
changes automatically.

The workflow retrieves every page of closed pull requests for the default branch. The script finds the nearest
reachable release tag and selects merged PRs whose merge commits belong to that tag-to-HEAD ancestry (all HEAD
ancestry for the first release). It also collects every page of GitHub PR associations for first-parent commits
in that history. Notes list merged PRs once and include linked, escaped subjects for direct commits; merge,
squash and rebase PR commits are not listed again as direct changes. The curated `[Unreleased]` notes lead the
new release section unchanged, and `[Unreleased]` is left empty; notes that are malformed or use a reserved
lineage heading stop preparation before any write ([changelog policy](changelog.md)). Earlier release sections are preserved.
Unmerged PRs and changes outside this history are excluded. Commit-only and mixed releases are supported;
an empty Git history or failed/incomplete collection is refused. A release can collect several merged PRs.

Preparation records the dispatcher using a reviewed `person.github` identity and the deterministic script as
instrument. Add a new dispatcher's reviewed identity and citation credit through an ordinary content PR first.
The preparation timestamp and release date come from the workflow run's start in UTC, so retrying that run
produces the same proposed bytes. The dispatch opens `release/<version>` with just the owning metadata,
changelog, provenance and identifier register. A retry can finish opening a PR after branch creation was
interrupted. An outdated proposal is prepared again from the current default branch, keeping its PR, only while
the release App made every commit on it; an edited proposal is left for reconciliation by hand, and a proposal
closed without merging is never reopened. When the default branch already carries the requested version untagged,
the dispatch completes that release instead: its PR adds only the changelog entries for changes that landed since
the preparation, leaving the version, dates and earlier entries unchanged.

The default path is to review and merge that release PR, then run **Tag release** (`tag-release.yml`) on the
current default-branch commit with the same version. A maintainer may also use valid release metadata committed
directly to the default branch through an explicitly authorized process. The dispatch checks all owning versions
and dates, citation/Zenodo metadata and exactly one nonempty changelog section for the requested version with
the matching date. No release PR or merge-commit ancestry is required. The section must also list every merged PR
and direct commit since the previous tag, leaving out the release's own `release/<version>` PRs. When changes landed
after preparation, Tag release creates no tag, names them in its summary and calls Prepare release, which opens the
completion PR; merge it and run Tag release again. The final branch-head check rejects a stale source. The dispatch creates `v<version>` once and never moves an existing tag. Tag creation starts the
checked production build; publishing the resulting draft release is still a separate maintainer act. The native `fair-guide-release-notes` skill composes reviewed notes with the draft's marked verification record
and asks once before applying. The [release runbook](runbooks/release.md) owns its invocation and publication;
the [release-notes how-to](how-to/release-notes.md) owns the manual fallback.

Historical recovery is limited to an unchanged original release whose failed-deployment tag was removed before
an artifact was published. The [historical tag recovery runbook](runbooks/recover-a-release-tag.md) owns approval,
identity checks and the one-time annotated tag. The normal dispatch selects the current default-branch commit;
it never selects a historical target. Branch advancement alone causes no refusal if the requested-release checks
still pass. An existing tag never moves; corrected metadata requires a new version.

`.github/release.yml` groups GitHub-generated notes into Breaking changes (`breaking-change`, reserved
for breaking PRs), Features (`enhancement`), Bug fixes (`bug`) and Other (all remaining PRs). It keeps
dependency and bot changes visible. Check this configuration with
`python .agents/scripts/validate_release_yml.py --root . --skip-reports` using Python with PyYAML.
This config does not replace Prepare release's complete PR/direct-commit changelog or the artifact-bound draft body.
For curated notes, follow the release-notes skill and validate its recommended report copy as instructed;
publishing notes still needs separate approval.

Both dispatches use the existing repository-scoped App (`SOURCE_REFRESH_CLIENT_ID` and
`SOURCE_REFRESH_APP_PRIVATE_KEY`), with Contents and Pull requests read/write at installation and narrower tokens
per job. The App's PR and tag events trigger normal checks and deployment. GitHub documents this distinction
in [workflow triggering](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
Default-branch-only jobs and checkout credentials disabled keep the App token out of PR execution. These
workflows require activation through the approved deployment procedure.

`python scripts/release_versions.py check --site _site` checks all versions and dates, the built crate and
documentation that restates the Guide version. `check_all.py` runs it with the other deterministic checks.
Run `python -m unittest discover -s tests -p test_release_versions.py` and
`node tests/page/check_prepare_release.mjs` for offline metadata, history, identity and delivery fixtures.

## Citation and Zenodo metadata

Install the pinned `requirements-dev.txt` and run `python scripts/check_citation_metadata.py`. This read-only
check runs in local `check_all` and the CPU CI lane, and both release dispatches run it before delivery or
tagging. CFF is validated against its declared schema; the Zenodo import profile and shared citation fields
are checked separately. `python scripts/release_versions.py check --version <version>` additionally requires
matching committed release metadata and dated, nonempty notes for that requested version.

The Guide owns release version/date, and CFF owns software authors, ORCIDs, title, abstract, keywords and license.
Zenodo uses the equivalent values, including bare ORCIDs and the lowercase MIT license identifier. Its description
is the CFF abstract, optionally followed by the guide/source links. Other shared-field changes need a matching
Zenodo edit; the checker reports drift. Structured creator affiliations retain their reviewed ROR IDs and names
from `content/guide.toml`. Do not also set a scalar `affiliation`, which overrides structured affiliations in
Zenodo's importer. The release owner changes only version/date in `.zenodo.json`, preserving curated references,
relations, funding/licensing notes and other supported archive fields. The permitted-file policy and emitted
digests include the Zenodo file. Cited-report authors and licensing remain attached to that report; file-level
licensing remains in `REUSE.toml`.

[Zenodo selects `.zenodo.json` exclusively](https://help.zenodo.org/docs/github/describe-software/) when both files
exist. Its [linked legacy schema](https://developers.zenodo.org/#github) omits `version` and structured affiliations,
although the [reviewed importer](https://github.com/zenodo/zenodo-rdm/blob/1fab575d6b7eea09e5ebef5329ee366efbddc802/site/zenodo_rdm/legacy/deserializers/metadata.py)
supports both. The repository's offline profile explicitly accepts those fields and rejects unsupported shapes;
it does not fetch a changing schema during checks or claim remote vocabulary/archival acceptance.

Keep regression coverage for both general CFF validity and Zenodo's import subset: a CFF license list can be
valid CFF while the pinned importer accepts a string or dictionary, but not a list. This repository's check uses
the narrower SPDX-string profile. Run
`python -m unittest discover -s tests -p test_citation_metadata.py` for those fixtures.

For an approved release, verify the Zenodo integration and its actual archive result. Keep the concept DOI
badge/link in both `README.md` and `README_en.md` aligned with the issued record and verify the destination.
The [concept DOI covers all versions](https://support.zenodo.org/help/en-gb/25-citations/234-how-to-share-or-cite-a-zenodo-record);
retain version-specific DOI distinctions for reproducible citations. Do not add placeholder badges, guess a DOI
or claim successful archiving while the record is pending or failed. The GitHub integration does not support
[DOI pre-reservation](https://support.zenodo.org/help/en-gb/24-github-integration/73-can-i-pre-reserved-a-doi-before-a-github-release).

## Live release probes

For the opt-in acceptance probes, run `npm run check:live-release`. It requests the four citation formats for
one DataCite and one Crossref DOI, verifies that Czech ISO differs from APA, then runs the Guide's twelve
FAIR-Checker metrics against a public dataset after confirming its DataCite type. It uses real browser requests
and saves a compact receipt in `.cache/live-release/receipt.json`. Missing native results fail this probe;
they do not become failed FAIR criteria. The general `check:live` suite covers additional services separately.

## Release container image

Every tagged release also publishes a container image to the GitHub container registry, assembled from that
release's verified site artifact — never rebuilt from source — so a reader can run the published page locally with
`docker run --rm -p 8080:8080 ghcr.io/dsw-nrp/eosc-fair-guide:latest`. It always carries the release tag. The
moving `latest` names the newest approved release and `stable` the newest approved non-prerelease; neither moves
back. When a newer release is approved while an older one's image is built, the older image keeps only its own tag,
its draft release is still created, and its summary names the release whose own run moves the aliases. It is signed
(cosign, keyless) and attested against its digest and scanned with Trivy; a failed scan operation blocks
publication, while vulnerability findings are advisory. The release notes record that digest. Its
`nginx-unprivileged` base is digest-pinned and the `docker` Dependabot entry keeps it current.

The production site and draft release receive the same verified bytes.
