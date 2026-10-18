# Spec Delta

## MODIFIED Requirements

### Requirement: Releases are versioned consistently

A release SHALL keep the Guide, `CITATION.cff`, `.zenodo.json`, npm manifest and lockfile, `pyproject.toml`, crate
metadata and release tag consistent. One script SHALL own their version and release dates;
prose SHALL NOT restate the version. The first official prerelease tag SHALL be `v1.0.0-alpha.1`. Each release
SHALL attach the verified built site from its source commit as an asset; deployment SHALL publish that same
checked artifact without rebuilding away its recorded health outcomes.

#### Scenario: Version mismatch

- **GIVEN** a release pull request in which `CITATION.cff` and the crate carry different versions
- **WHEN** the hygiene check runs
- **THEN** it fails and names the mismatching files

#### Scenario: Zenodo metadata still describes the previous release

- **GIVEN** the Guide and CFF have a new release version or date while `.zenodo.json` retains the previous values
- **WHEN** release validation runs through either the PR or direct-commit route
- **THEN** it fails and names the stale Zenodo fields before tagging

### Requirement: Releases are prepared and tagged by dispatch

A prepare-release dispatch SHALL write the version, dates and a changelog of merged PRs and direct default-branch
commits since the last reachable release tag into a release PR by default. A separate maintainer dispatch SHALL
create the tag from valid committed release metadata on the current default branch, whether that metadata arrived
through a release PR or direct commits. Preparation and default-branch pushes SHALL NOT automatically create tags.

#### Scenario: Preparing a release from several merged pull requests

- **GIVEN** three pull requests merged since the last tag
- **WHEN** the maintainer runs the prepare-release dispatch for `1.0.0-alpha.2`
- **THEN** a release pull request sets that version and today's release date in every owning file and lists the three pull requests in the changelog, and no tag exists until the maintainer runs the tag dispatch after merging it

#### Scenario: Preparing a release containing only direct commits

- **GIVEN** direct default-branch commits and no merged PRs since the last release tag
- **WHEN** the maintainer runs Prepare release with a new version
- **THEN** it opens the normal release PR with consistent metadata and linked commit summaries instead of refusing because the PR list is empty

#### Scenario: Tagging metadata committed directly to the default branch

- **GIVEN** the current default-branch commit contains consistent metadata and a nonempty dated changelog section for the requested version, without a merged release PR
- **WHEN** the maintainer runs Tag release with that version and a valid release status
- **THEN** the workflow creates the annotated release tag at that exact commit without requiring PR ancestry
- **AND** successful verified deployment feeds the existing image and draft-release chain, with publication remaining a separate maintainer action

### Requirement: An unchanged release may be re-issued by a direct annotated tag

Tag release SHALL select the current default-branch commit, never a historical target. After the branch advances,
an unchanged release MAY be re-issued manually at its original release merge commit only if no released artifact was
published for the removed tag. Its annotated tag SHALL carry the release-status marker and never move an existing
tag. Deployment and release SHALL use that commit's verified build.

#### Scenario: Re-issuing an unchanged release after a repair

- **GIVEN** a merged release pull request at a known commit, its tag removed after a failed deployment before any released artifact was published, and a repair merged to the default branch
- **WHEN** the maintainer manually recreates the annotated tag for that original release merge commit
- **THEN** the tag names that historical commit and carries the same status marker, and deployment and the draft release follow from that commit's verified build

#### Scenario: Dispatching after a repair with valid committed metadata

- **GIVEN** the default branch has advanced beyond the original release merge commit and its current head passes all requested-release checks with no existing requested tag
- **WHEN** the maintainer runs Tag release
- **THEN** the dispatch tags that current head, including the repair, rather than selecting the historical merge commit or refusing solely because the branch advanced

## ADDED Requirements

### Requirement: Release changelogs cover PRs and direct commits without duplication

Release preparation SHALL include merged PRs and direct default-branch commits in the selected release history,
using all history for the first release. Each PR SHALL appear once; commits represented by that PR SHALL NOT also
appear as direct changes. Direct entries SHALL contain escaped subjects and repository commit links. Output SHALL
be deterministic, preserve prior release sections and refuse a genuinely empty history or incomplete collection.

#### Scenario: A release mixes direct commits and different merge methods

- **GIVEN** ordinary, squash and rebase PR merges plus direct commits in the release history
- **WHEN** the maintainer prepares the release
- **THEN** each merged PR appears once, direct commits appear with their subjects and commit links, and commits belonging to those PRs are not repeated as direct changes
- **AND** prior release sections retain their existing bytes

#### Scenario: A direct commit is outside the release history

- **GIVEN** a previous reachable release tag, commits before that tag and commits on an unmerged branch
- **WHEN** the release changelog is generated
- **THEN** those earlier and unrelated commits are excluded

#### Scenario: The first release contains only direct commits

- **GIVEN** a repository with direct default-branch history and no reachable release tag
- **WHEN** release preparation runs
- **THEN** it derives nonempty linked notes from that history without requiring a PR or an earlier tag

#### Scenario: The release history is empty

- **GIVEN** the selected source commit is the previous release tag's commit and there are no new changes
- **WHEN** release preparation runs for a new version
- **THEN** it refuses before changing metadata or opening a release PR

#### Scenario: Change collection fails or includes Markdown syntax

- **GIVEN** change collection requires several pages or a commit subject contains Markdown syntax
- **WHEN** release preparation collects and renders that history
- **THEN** every required page must be retrieved, collection failure stops preparation, and subjects render as escaped text

### Requirement: Direct-commit tagging preserves release validation

Tag release SHALL validate the selected current default-branch commit, the requested version against all owning
metadata, consistent release dates, a matching nonempty dated changelog section, and the explicit release status
before creating a tag. It SHALL reject existing tags without moving them. Failure SHALL create no tag ref.
PR-based preparation, permitted-file validation and reviewed retry recovery SHALL remain supported.

#### Scenario: Release metadata or notes do not match the requested version

- **GIVEN** a version disagreement, inconsistent dates, or a missing, empty or differently dated changelog section for the requested version
- **WHEN** Tag release runs
- **THEN** it explains the disagreement and creates no tag ref

#### Scenario: The default branch moves after source selection

- **GIVEN** Tag release selected a commit and the default branch advances before the final branch check
- **WHEN** the workflow checks its selected source before tag creation
- **THEN** it refuses and asks the maintainer to rerun against the current default-branch commit

#### Scenario: A tag already exists or a dispatch is invalid

- **GIVEN** an existing requested tag, a non-default-branch invocation, or an invalid version or release status
- **WHEN** Tag release runs
- **THEN** it refuses without creating or moving a tag ref or changing an existing tag's release status

#### Scenario: Existing PR preparation is retried

- **GIVEN** preparation created its normal release branch but opening the PR was interrupted
- **WHEN** the same dispatch is retried
- **THEN** existing permitted-file, digest and branch-content checks still allow safe recovery and reject edited or outdated proposals

### Requirement: Zenodo metadata preserves shared credit and curated archive fields

Release preparation SHALL maintain `.zenodo.json` with the shared software citation fields, version and date
consistent with their owning metadata. It SHALL preserve reviewed structured affiliations, references,
relations, funding acknowledgements and other curated Zenodo-specific fields. Report authors and licenses
SHALL remain attached to the cited report rather than becoming software authorship or licensing.

#### Scenario: Preparing another release preserves the archive description

- **GIVEN** reviewed software credit, two ROR affiliations and curated Zenodo notes, references and relations
- **WHEN** release preparation updates the version and date
- **THEN** shared software citation metadata stays consistent, both affiliations and curated fields survive, and the proposed files include `.zenodo.json` within the permitted digest-checked set

#### Scenario: Software credits change

- **GIVEN** a reviewed change to a software author's identity or ORCID, title, abstract, keywords or software license
- **WHEN** citation metadata are maintained and checked
- **THEN** the corresponding Zenodo fields are updated or a mismatch is reported before release
- **AND** authors listed only in the FAIR-analysis reference are not silently added as software creators

### Requirement: Citation checks validate CFF and the effective Zenodo import format

Repository checks, release preparation and tag validation SHALL validate CFF schema correctness and the supported
Zenodo import shape, as well as cross-file consistency. Validation SHALL distinguish the supported importer
from an outdated schema, retain valid structured ROR affiliations and reject unsupported license shapes in
the metadata Zenodo will consume. Failure SHALL prevent delivery of prepared metadata or creation of a tag.

#### Scenario: The CFF document is invalid

- **GIVEN** malformed CFF or a value invalid under its declared schema
- **WHEN** the repository or release checks run
- **THEN** validation fails with the relevant file and field instead of relying only on version/date matching

#### Scenario: Zenodo's effective license value is a list

- **GIVEN** `.zenodo.json` contains an array of software and content licenses where the importer expects a supported single license value
- **WHEN** release metadata validation runs
- **THEN** it rejects that import shape before preparation is published or a tag is created, while retaining the separate file-level licensing explanation

#### Scenario: The legacy schema is narrower than the supported importer

- **GIVEN** otherwise valid Zenodo metadata containing a release version and structured ROR affiliations
- **WHEN** the documented offline compatibility checks run
- **THEN** those supported fields pass even if the older linked schema omits them, without disabling validation of unrelated invalid fields

### Requirement: Published release documentation exposes the concept DOI

After the corrected release is successfully archived in Zenodo and a concept DOI is issued, both README language
versions SHALL display its badge linked to that all-versions DOI. The link SHALL resolve to the release series.
Before issuance, documentation SHALL NOT invent a DOI or claim successful archiving. Version-specific citation
identifiers SHALL remain distinct from the concept DOI.

#### Scenario: Zenodo successfully archives the corrected release

- **GIVEN** the release is published and its Zenodo record exposes the issued concept DOI
- **WHEN** the post-release documentation follow-up runs
- **THEN** both READMEs gain the badge for that actual concept DOI and its destination is verified

#### Scenario: Archiving fails or the DOI has not been issued

- **GIVEN** a failed or pending Zenodo archive with no issued concept DOI
- **WHEN** release readiness or the README follow-up is reported
- **THEN** the pending archive/badge work stays explicit and no placeholder is presented as an issued DOI
