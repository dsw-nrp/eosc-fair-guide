# Guide delivery

## Purpose

The FAIR Guide delivery capability and its observable acceptance contract.

## Requirements

### Requirement: Release-note configuration is ready for validation

The Guide SHALL provide `.github/release.yml` with English semantic categories, mappings for its feature
and bug labels, and a final catch-all retaining maintenance changes. Release-note report validation SHALL
support the explicitly selected recommended config without requiring propagation to a target checkout.
This configuration SHALL NOT replace the artifact-bound draft body or the release-preparation changelog.

#### Scenario: A maintainer prepares release notes locally

- **GIVEN** the Guide checkout and the delivered release-note tools
- **WHEN** the maintainer validates configuration only or prepares a report-only run
- **THEN** the actual config or explicitly selected report copy SHALL validate through the documented command
- **AND** report-only validation SHALL retain report language and working-companion checks

### Requirement: Repository carries best-practice files

The tool repository SHALL contain:

- a Czech `README.md` and an English operational `README_en.md`;
- MIT licensing for code and CC BY 4.0 for content, declared in a REUSE-compliant layout;
- `CITATION.cff`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` and `SECURITY.md`;
- an accessibility statement;
- `.editorconfig` and a `.gitattributes` that enforces LF line endings.

#### Scenario: Licence lint

- **GIVEN** any commit on the default branch
- **WHEN** the REUSE lint runs
- **THEN** every file has a declared licence and copyright

### Requirement: README language versions agree on repository facts

The Czech and English READMEs SHALL agree on current capabilities, repository contents, release practice
and validation commands. The English file SHALL remain the operational entry for agents.

#### Scenario: Documenting the check reports

- **GIVEN** the published dashboard and its validation commands
- **WHEN** either README is read
- **THEN** it describes the same report locations, navigation links and commands in its own language

### Requirement: Design documentation describes the current design

`docs/design.md` in the tool repository SHALL describe the current design by system area: purpose and scope,
architecture, content model, interface principles, self-check and evidence, connectors and evaluators, delivery
and automation. It SHALL state binding design decisions as principles with their reasons, and SHALL NOT narrate
review rounds, dated iterations or superseded choices; that history stays in version control and the planning
change.

#### Scenario: A contributor looks up why scores are absent

- **GIVEN** a contributor reading `docs/design.md`
- **WHEN** they look for how results are presented
- **THEN** the self-check section states that no combined score is shown and why, without a dated decision log or review-round account

### Requirement: Contributors can open a ready development environment

The repository SHALL provide a development container with the pinned Python and Node versions and the Playwright
browser with its system dependencies, in which the full check suite runs without further installation.

#### Scenario: Running the checks in the container

- **GIVEN** a contributor who opens the repository in its development container
- **WHEN** they run the documented check command
- **THEN** the checks run to completion without installing anything else

### Requirement: A missing build prerequisite fails with its remedy

When a package the build needs is absent, the build SHALL stop before writing any output and SHALL name the
missing package and the command that installs it. It SHALL NOT fetch a substitute from a CDN or publish a
placeholder in its place.

#### Scenario: Building a fresh clone without Node packages

- **GIVEN** a fresh clone in which `npm ci` has not run
- **WHEN** the site build runs
- **THEN** it stops before writing output, with a message naming `swagger-ui-dist` and `npm ci`

### Requirement: Minimal AI tooling with one editing skill

`AGENTS.md` SHALL be the runtime entry; `CLAUDE.md`, Copilot and mixed `CODEX.md` SHALL point to it.
`.agents/guide/` SHALL own native rules and a thin editing skill, with generated vendor readers and identical
skill copies in `.agents/skills/` and `.claude/skills/`. The skill SHALL route content, tone, accessibility,
paradata, validation and release execution to their maintained owners after the required planning boundary.

#### Scenario: Skill copies drift

- **GIVEN** a pull request that changes only one of the two skill copies
- **WHEN** the hygiene check runs
- **THEN** it fails and names both paths

### Requirement: Native ownership and delivered integrity are checked

`.agents/guide/surfaces.toml` SHALL classify owned, generated, delivered, tool-generated, runtime and mixed
surfaces, including guide-owned `.agents/reports/usage/` and `.agents/config/review_config.toml`. `check_all` SHALL
run native generation, ownership and delivery-integrity checks, failing on unclassified paths or missing, modified
or extra delivered content. Native generation SHALL preserve delivered Codex sections and the supplied preamble;
redelivery SHALL preserve native sections.

#### Scenario: A delivered rule is modified locally

- **GIVEN** the manifest records a delivered rule or Codex section
- **WHEN** it is modified and `check_all` runs
- **THEN** delivery integrity fails while ignoring separately declared owned and tool-generated paths

### Requirement: Runtime scratch hand-offs are neither owned nor delivered

The repository's runtime scratch area SHALL be a declared runtime path. Files there SHALL NOT be reported as unclassified managed files or as delivered content, and native generation SHALL NOT write into it.

#### Scenario: A tracked readme describes the runtime area

- **GIVEN** a tracked file in the declared runtime scratch area
- **WHEN** the ownership and delivery-integrity checks run
- **THEN** the file is classified as runtime and neither fails classification nor counts as delivered content

#### Scenario: A hand-off appears untracked

- **GIVEN** an untracked hand-off under the declared runtime scratch area
- **WHEN** the ownership checks run
- **THEN** it is classified as runtime and no finding is reported

### Requirement: Tooling documentation describes the current compatible set

`docs/agent-tooling.md` SHALL render its current bundle inventory from the delivery manifest, with an
authored task-to-tool matrix, vendor invocation, prerequisites, limits and read-only protection.
It SHALL describe each client's actual instructions, shared skills and tool-generated OpenSpec surfaces
without promising absent assets. The native editing skill and tooling document SHALL require the
OpenSpec lifecycle before implementation of a triggering change.

#### Scenario: A contributor chooses an editing workflow

- **GIVEN** the contributor reaches the native editing skill or tooling document
- **WHEN** their change triggers OpenSpec
- **THEN** both SHALL require the OpenSpec lifecycle before implementation

#### Scenario: A contributor checks workflow compatibility

- **GIVEN** the current curated bundle and guide review facts
- **WHEN** the tooling document describes the installed set
- **THEN** it SHALL record the four retained workflows, `aiscr-draft`, dropped live/translation workflows, unavailable `--sibling`, native `check_all` close-out and Git baseline mapping
- **AND** review facts SHALL declare no database and a deployment pipeline, public API and first-party frontend

### Requirement: Guide-owned usage and review facts

Usage logging SHALL adopt the delivered notability and runtime/backend fields under `.agents/reports/usage/`.
Guide-owned `.agents/config/review_config.toml` SHALL declare no database and the presence of a deployment
pipeline, public API and first-party frontend.

#### Scenario: Preparing an agent review

- **GIVEN** a significant review of the Guide
- **WHEN** the reviewer starts work
- **THEN** they read the guide-owned review facts and maintain a rolling usage entry

### Requirement: Content checks gate pull requests

Every pull request SHALL pass a structure check (RO-Crate validity and the guide's SHACL profile) and a
content-contract check (bilingual text, ledger citations, paradata coverage, dated statuses, HTTPS-only
links, allowlisted live hosts, no raw HTML in text) before merge.

#### Scenario: Unsafe content in a pull request

- **GIVEN** a pull request that puts a `javascript:` link into a resource
- **WHEN** the checks run
- **THEN** the content-contract check fails and names the resource

### Requirement: Page checks gate pull requests

Every pull request SHALL pass page-integrity, accessibility, link, diagram and hygiene checks before merge.
Broken internal links SHALL fail the check; broken external links SHALL produce a warning. A page whose compressed
download before any user action exceeds its budget SHALL produce a warning that names the size, the budget and the
largest parts.

#### Scenario: Page grows past its budget

- **GIVEN** a change after which the page, its scripts and its stylesheets download more than the budget, compressed
- **WHEN** the build runs
- **THEN** it warns with the size, the budget and the largest parts, and does not fail on the size alone

#### Scenario: Inline script added

- **GIVEN** a pull request that adds an inline event handler to the page
- **WHEN** the page-integrity check runs
- **THEN** it fails and names the element

### Requirement: Pull requests receive a reviewable summary

Each pull request SHALL receive a summary of the changed content and rendered previews at desktop and mobile
width.

#### Scenario: Text change preview

- **GIVEN** a pull request that changes advice text
- **WHEN** the checks complete
- **THEN** the pull request shows the changed items in Czech and English and links to the preview screenshots

### Requirement: Review comments use a separate trusted publisher

The review-comment workflow SHALL run after the PR checks, use only default-branch code and read
bounded review data without executing it. It SHALL verify the current PR head and source repository,
escape artifact text, and update only its own bot comment. Its only write permission SHALL be
`pull-requests: write`; the PR check workflow SHALL remain read-only.

#### Scenario: The PR advances before the summary is posted

- **GIVEN** a completed check run for an earlier commit
- **WHEN** the PR head no longer matches that run
- **THEN** the publisher skips the stale summary without changing the PR comment

### Requirement: Workflows are hardened

CI workflows for pull requests SHALL use the `pull_request` trigger, and the merge queue's `merge_group` trigger,
only, SHALL run with read-only repository permissions, SHALL pin third-party actions by commit SHA, and SHALL use
no secrets. Dependency and action updates SHALL be proposed automatically.

#### Scenario: Pull request from a fork

- **GIVEN** a pull request from a fork
- **WHEN** its checks run
- **THEN** they have read-only access and no secrets are available

#### Scenario: A merge group is checked

- **GIVEN** an approved pull request added to the merge queue
- **WHEN** the queue checks the merged result
- **THEN** the checks run with read-only access, no secrets and the same pinned actions as pull-request checks

### Requirement: Humans judge correctness and tone

CODEOWNERS SHALL name actual available maintainers responsible for technical integrity, compatibility and fit
with the Guide. Appropriate human collaborators SHALL review content correctness, source interpretation and tone.
Passing checks SHALL NOT replace human review. For the initial sole-maintainer alpha, PR delivery, required checks
and explicit maintainer acceptance SHALL be the enforceable gate. Mandatory content-owner approval SHALL be
enabled once a reviewer can approve the author's PR.

#### Scenario: Text change

- **GIVEN** a pull request that only changes advice text
- **WHEN** all checks pass
- **THEN** the available human-review gate remains required, and the alpha release candidate requires explicit maintainer acceptance

#### Scenario: Technical ownership and content expertise differ

- **WHEN** a content change is reviewed by its technical code owner
- **THEN** the owner checks integrity and fit, the appropriate human collaborators review content meaning, and enforced repository approvals still apply

### Requirement: Scheduled jobs never commit directly

Scheduled jobs SHALL deliver snapshot refreshes as pull requests and report link, status, live-service and
test-health observations in one maintenance digest. They SHALL watch the EOSC CZ pages the guide depends on (outputs,
service catalogue, training, Open Science III FAQ, minizáměry calls, acknowledgement and data steward pages) and list
added or updated items in the digest, ignoring navigation and pagination. They SHALL NOT commit to the default
branch or open work issues by themselves.

#### Scenario: Broken external link found

- **GIVEN** the weekly link check finds a persistently failing external link
- **WHEN** it completes
- **THEN** the digest lists the link, where it is used, the observed response and its persistence, and no separate issue is opened

#### Scenario: New EOSC CZ output

- **GIVEN** the EOSC CZ outputs page lists a document that was not there at the previous run
- **WHEN** the watch job runs
- **THEN** the digest lists the document with its address or anchor and its publication date when the page provides one, without inventing a date

#### Scenario: Pagination changes on a watched page

- **GIVEN** the training page adds a next-page link without adding a relevant item
- **WHEN** monitoring compares the page with its baseline
- **THEN** the navigation change creates no digest entry, comment or issue

### Requirement: Portable hosting

The guide SHALL work as a single page with no dependency on the host's content management system. It SHALL work
when embedded in an iframe and when opened as a local file, and it SHALL be publishable on GitHub Pages once the
repository is public. The site SHALL be built from the repository's sources with one documented command, which
also serves for opening it locally from a fresh clone.

#### Scenario: Embedded in an iframe

- **GIVEN** the page embedded in an iframe on another site
- **WHEN** a user navigates stations and lenses
- **THEN** the guide works fully, and shareable links open the same view in a new tab

### Requirement: Production publishes releases; staging follows the default branch

The production site SHALL be rebuilt and published only from a release tag. A merged pull request SHALL NOT change
production. A staging copy under `/next/` SHALL be rebuilt from every push to the default branch, in the same
deployment as production. Every HTML page of the staging copy SHALL carry a `noindex` robots directive and a visible
prerelease banner, and the copy SHALL be left out of the sitemap and linkset. Staging is unlisted, not private.

#### Scenario: A pull request is merged

- **GIVEN** a pull request merged into the default branch
- **WHEN** the deployment runs
- **THEN** `/next/` shows the merged change with the prerelease banner and `noindex`, and the production pages still serve the last release

#### Scenario: A release is tagged

- **GIVEN** a release tag created by the maintainer's dispatch
- **WHEN** the deployment runs
- **THEN** production serves that release's verified build, and `/next/` keeps serving the default branch

### Requirement: The guide can be embedded with a host snippet

The guide SHALL publish a host snippet and a documented message protocol through which an embedding page sizes
the frame to the guide's content and reflects the guide's current view in its own address, accepting messages only
from configured origins and using no third-party library. A host address shared from the embedding page SHALL
reopen the same view.

#### Scenario: Reading a long station in an embedded guide

- **GIVEN** the guide embedded on a host page with the snippet
- **WHEN** the reader opens a long station and shares the host page's address
- **THEN** the frame grows without an inner scroll bar, and the shared address opens the same station

### Requirement: OpenSpec-driven development in the repository

Before the first alpha, the tool repository SHALL carry pinned OpenSpec tooling, capability specs under
`openspec/specs/` and the sanitized planning artifacts. The change SHALL be archived under
`openspec/changes/archive/` after required implementation/delivery work is complete. CI SHALL validate
the OpenSpec tree on every pull request.

#### Scenario: Proposing a later change

- **GIVEN** a contributor who wants to change how the self-check works
- **WHEN** they install the development dependencies and create an OpenSpec change in the repository
- **THEN** the change validates against the repository's capability specs, and CI runs the same validation on their pull request

### Requirement: The editing skill decides when an OpenSpec change is needed

The editing skill SHALL route work that changes behaviour, a data or API contract, a stored format, CI or repository
governance through an OpenSpec change before implementation. It SHALL let typo, wording and formatting fixes,
behaviour-neutral dependency updates and source data refreshes proceed without one. It SHALL delegate to the
delivered planning and OpenSpec lifecycle before implementation and SHALL NOT implement first and maintain specs later.

#### Scenario: A content fix needs no change

- **GIVEN** a contributor who corrects a typo in a station's advice
- **WHEN** they follow the editing skill
- **THEN** the skill leads them straight to the content edit, its paradata and the checks, without an OpenSpec change

#### Scenario: A behaviour change needs a change

- **GIVEN** a contributor who wants the self-check to accept a new kind of identifier
- **WHEN** they follow the editing skill
- **THEN** the skill leads them to create an OpenSpec change first and to implement only after it is approved

### Requirement: No local or planning-environment details

Files and commit messages in the tool repository SHALL NOT contain local machine paths, user-specific setup, or
references to private planning systems. A hygiene check SHALL scan the repository's text files for
local path patterns, hub-internal names and unapproved unpublished working material. The approved model's
in-preparation citation SHALL remain subject to these local-path and private-material restrictions.

#### Scenario: Local path in a document

- **GIVEN** a pull request that adds a Windows path from a maintainer's machine to a document
- **WHEN** the hygiene check runs
- **THEN** it fails and names the file and line

### Requirement: The hygiene check names machine-specific scratch paths

The public-content hygiene check SHALL refuse an absolute, drive-qualified or rooted path to a local scratch layout, and SHALL NOT refuse the repository's own runtime scratch convention written as a repository-relative path. The other hygiene rules and the redacted `file:line: rule` findings SHALL remain unchanged.

#### Scenario: Delivered tooling documents the runtime scratch layout

- **GIVEN** a delivered library or skill that names the repository-relative scratch path
- **WHEN** the hygiene check runs
- **THEN** it reports nothing

#### Scenario: An absolute scratch path is planted

- **GIVEN** a document or test file containing a drive-qualified or rooted path to that layout
- **WHEN** the hygiene check runs
- **THEN** it fails and names the file, line and rule without quoting the path

### Requirement: Public move of the planning change

When the planning change moves into the public repository, only its proposal, design, specs and tasks SHALL move,
redacted of private workflows, local usage logs and workstation paths and unapproved unpublished working material. The approved
in-preparation conceptual-model citation MAY remain. The working
notes SHALL stay out: source transcriptions never move, and open questions move as issues.

#### Scenario: Moving the planning change

- **GIVEN** the planning change ready to move into the public repository
- **WHEN** the move is prepared
- **THEN** only the proposal, design, specs and tasks are copied, the redaction check passes on them, and no transcription or working note is part of the move

### Requirement: Open questions become issues

Before the first release is declared complete, every open question recorded during planning SHALL be filed as an
issue in the tool repository, with its context and a proposed owner.

#### Scenario: Release readiness

- **GIVEN** the first release candidate
- **WHEN** readiness is checked
- **THEN** each planning open question exists as a tool-repository issue, or is recorded as resolved

### Requirement: Contributors are recorded without effort

Human contributors SHALL use reviewed GitHub accounts/co-author trailers, known ORCIDs and citation opt-outs,
never e-mail addresses or invented IDs. Editorial agents SHALL be responsible for their actual actions;
PR authorship SHALL NOT assign every action to every author. AI assistants SHALL be instruments.
Automation accounts SHALL NOT become human authors or people in `CITATION.cff`.

#### Scenario: Contribution with an AI assistant

- **GIVEN** a pull request whose commits name an AI assistant as co-author
- **WHEN** its contributors are recorded
- **THEN** the responsible human is associated with the actual editorial actions, the assistant is an instrument, and only eligible human contributors appear in `CITATION.cff`

### Requirement: Missing contributor records come with their fix

A script SHALL prepare contributor records from a pull request's commits and reviewed identity mappings.
Missing known records SHALL produce a ready-made patch without pushing to contributor branches. Ambiguous
identities, unknown ORCID iDs and action responsibility SHALL require explicit resolution rather than fabrication.

#### Scenario: First contribution

- **GIVEN** a first-time contributor's pull request that changes a station and records no person, citation entry or provenance agent
- **WHEN** the pull-request checks run
- **THEN** they fail and offer the missing person entry, `CITATION.cff` entry and provenance agent as one change the contributor applies with one command

### Requirement: Contributor records stay consistent

Offline content checks SHALL keep human editorial agents and citation entries consistent, with matching known
ORCID iDs and explicit citation opt-outs. Automatic retrieval records SHALL retain source, date, software and run
identity separately from human editorial review; they SHALL NOT fabricate human responsibility for nightly jobs.
All action types SHALL remain compatible with the chosen crate profile.

#### Scenario: An agent missing from the citation file

- **GIVEN** a provenance action whose agent is not in `CITATION.cff` and has not declined being named
- **WHEN** the content checks run
- **THEN** they report the person missing from `CITATION.cff`

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

### Requirement: First official prerelease is the software example baseline

The app's software-practice worked example SHALL assess the first official prerelease. Development preparation
SHALL be distinguished from published evidence. Preservation identifiers and badges SHALL be stated only when
issued. Remaining work and its evidence SHALL live in issues or the relevant OpenSpec change. Public pages
SHALL explain stable practices without temporary development or future-assessment commentary.

#### Scenario: Private development checkout

- **GIVEN** the unpublished app in development
- **WHEN** a maintainer reviews the software-practice evidence map
- **THEN** existing build, licensing and citation evidence is shown, release and public preservation steps remain recorded for preparation, and no fabricated archive identifier or self-certification badge appears

### Requirement: Display translations load for the selected language

The first download SHALL load neutral structure and only the selected language's guide and interface
texts. Switching languages SHALL load the other display texts on demand while preserving answers.
Original source passages and published vocabulary labels SHALL retain their source languages.
The complete crate and API SHALL remain bilingual; exports requiring both languages SHALL load them
explicitly. A missing language file SHALL preserve the usable current view and offer retry.

#### Scenario: Switching an answered check

- **GIVEN** a Czech check with answers and the English translations not yet loaded
- **WHEN** the reader switches to English
- **THEN** English display texts load once and the same answers and evidence remain available

### Requirement: CI reports actual check-run health

The check runner SHALL produce JSON, a readable HTML dashboard and a CI summary that distinguish
passed, failed, blocked and unrun jobs, including a build failure. Content integrity and original-source
coverage SHALL be reported separately from live availability. Pull-request CI SHALL publish these
artifacts and its summary without credentials or repository write permissions and pin actions by commit.

#### Scenario: Build failure before verification

- **GIVEN** a build that fails before check jobs can run
- **WHEN** the runner emits its report
- **THEN** the dashboard preserves the build failure and marks dependent jobs blocked rather than claiming they passed

### Requirement: The published check dashboard is discoverable

The site SHALL publish the check dashboard with links from its footer and Data for machines. Report
links SHALL resolve within the published site. A fresh build SHALL show that no check run has completed;
completed results SHALL update the dashboard together with the REST snapshot.

#### Scenario: A reader opens the published report

- **GIVEN** either language version of the guide
- **WHEN** the reader follows its dashboard link
- **THEN** the dashboard opens and its guide, JSON report and summary links resolve within the site

### Requirement: The REST API publishes the health snapshot

The static REST API SHALL expose the same health result through a documented endpoint linked from
API metadata. Initial builds SHALL report no completed check run; a successful fresh build and run
SHALL publish actual outcomes. A failed build SHALL NOT overwrite an earlier site's health result.

#### Scenario: Checks complete after a fresh build

- **GIVEN** a fresh site whose health snapshot has no completed check run
- **WHEN** the check runner finishes
- **THEN** the REST endpoint publishes the same dated outcomes as the dashboard, including any failed or unrun jobs

#### Scenario: A later build fails

- **GIVEN** an earlier site with a published health snapshot
- **WHEN** the next build fails
- **THEN** its failure report remains available as a CI artifact and the earlier site's health endpoint is not overwritten

### Requirement: Build output locations cannot erase authored inputs

Site and standalone API builders SHALL validate resolved output locations before any deletion or mutation.
They SHALL reject the repository root, authored input directories, unsafe overlaps and symlink aliases to
protected inputs. Documented managed output directories SHALL remain usable.

#### Scenario: Authored assets selected as output

- **GIVEN** an output option resolving to the authored assets directory or its symlink alias
- **WHEN** a build is requested
- **THEN** it refuses before mutation and authored sentinel files remain intact

### Requirement: Source refresh proposals have a bounded trusted lifecycle

Each source SHALL have at most one active refresh PR; interdependent FIP collections SHALL be atomic.
Semantic no-ops SHALL create no PR or timestamp churn. Authorized refresh SHALL update a bot-owned proposal
from current main while preserving human edits. Rejected content SHALL NOT be reproposed unchanged
automatically. Refresh commands SHALL accept only reviewed source keys, never arbitrary shell, URLs or refs.

#### Scenario: Maintainer edits a proposed snapshot

- **GIVEN** an open source refresh PR whose branch contains human edits
- **WHEN** another automatic refresh runs
- **THEN** it leaves those edits intact and explains the need for explicit reconciliation

#### Scenario: The source data did not change

- **GIVEN** another successful retrieval of semantically identical source data
- **WHEN** publication is considered
- **THEN** no refresh PR is opened and the last successful observation is recorded independently of snapshot content

### Requirement: Refresh branches move only from the inspected head

`source-refresh.yml` publication SHALL change a refresh branch only while it still points at the head whose commits were inspected, and create an absent branch only while it is still absent, through one atomic comparison with that update; a branch that moved is kept and the run reports why.

#### Scenario: The branch moves after its commits were inspected

- **GIVEN** an open refresh branch whose commits were inspected as replaceable
- **WHEN** another writer advances the branch before the publisher replaces it
- **THEN** the atomic comparison refuses the update, the newer head is kept, and the run reports why

#### Scenario: The branch appears after it was read as absent

- **GIVEN** no refresh branch at the time publication read it
- **WHEN** another writer creates it before the publisher does
- **THEN** the creation is refused rather than replacing the new branch, and the run reports why

### Requirement: Source publication uses a narrowly scoped trusted App

Scheduled PR publication SHALL use the approved repository-scoped GitHub App through trusted code with only
the permissions needed for reserved branches and PRs. It SHALL NOT run untrusted PR code with that token,
push to the default branch or merge automatically. Refresh commands SHALL verify current caller permissions.

#### Scenario: An untrusted user requests refresh

- **GIVEN** a comment from an account without the required current repository permission
- **WHEN** the trusted refresh handler reads it
- **THEN** it does not publish or execute a refresh using App credentials

### Requirement: Refresh data is validated before replacement

Snapshot refreshes SHALL enforce response shape, completeness, bounded pagination and size, nonempty required
collections and reviewed removal thresholds before replacing existing data. Incomplete, empty or implausibly
reduced responses SHALL retain the last valid snapshot and produce attributable health diagnostics.

#### Scenario: A source returns an empty successful response

- **GIVEN** a nonempty reviewed snapshot and a response containing no required records
- **WHEN** the refresh runs
- **THEN** it keeps the snapshot unchanged and reports the rejected refresh without proposing header-only data

### Requirement: Health and source-watch reports remain actionable

Health reports SHALL separate content integrity, snapshot age, source availability and test verdicts.
Published observations SHALL have meaningful dashboard and API consumers for dates, revision, scope and status.
Persistent failures and relevant source changes SHALL appear in the maintenance digest once by stable key, without
transient-failure floods. A service failure SHALL NOT become a failed FAIR requirement. Live monitoring SHALL stay
separate from required deterministic PR checks.

#### Scenario: A test returns an indeterminate verdict

- **GIVEN** a completed live test with an indeterminate native result
- **WHEN** health is summarized
- **THEN** it is distinguishable from transport failure, a negative criterion result and a positive answer suggestion

#### Scenario: The runner receives an inconclusive response

- **GIVEN** a link request returns HTTP 403, HTTP 429 or a timeout
- **WHEN** the digest is rendered
- **THEN** it reports access denied, rate limited or temporarily unavailable without stating that the page is gone or that bot protection is confirmed

#### Scenario: A failure concerns imported content

- **GIVEN** the failing address comes from a reviewed upstream snapshot
- **WHEN** the finding is shown
- **THEN** it names the affected record and its source and points to the upstream or refresh correction route rather than to an edit of the snapshot

### Requirement: Routine content review has an explicit gate

Broad Czech/English text and link review SHALL cover the content as reworked after the maintainer's review rounds,
as a task of the planning change rather than a separately handed-off packet. Its record SHALL state coverage,
fixes and escalations. Routine polishing SHALL NOT rewrite original passages or assessment semantics. Required new
labels and targeted corrections MAY be completed during implementation.

#### Scenario: Implementation uncovers a missing translation

- **GIVEN** a new control missing its English label before the routine-review gate
- **WHEN** implementation validation runs
- **THEN** the required translation is fixed while the broad editorial review of the reworked content remains its own task

### Requirement: Landed review findings retain their disposition

All 26 confirmed findings in the landed PR #1 review at `63cf94d8` SHALL retain original IDs, receipts,
repair tasks and verification outcomes and SHALL be addressed before alpha. The separate first-run CI
provenance failure SHALL be corrected and regression-tested without weakening attribution. Verification
SHALL reuse the baseline and focus on repairs/new changes rather than repeat the deep review.

#### Scenario: A finding has no inline comment

- **GIVEN** L18 appears only in the review summary
- **WHEN** the repair ledger is checked
- **THEN** L18 still has its summary receipt, canonical diagram task and focused verification disposition

### Requirement: The complete prerelease bundle precedes release publication

Before tagging alpha, all decided implementable work, checks, issue transfer, repository preparation and
team hand-off SHALL be complete. External constraints and future work SHALL have issue dispositions;
implementable tasks SHALL NOT be silently deferred. Remote operations SHALL respect the delivery hold.
Pages, App, rules and workflow activation SHALL be verified in their actual trusted/default-branch context
after authorization. Archiving SHALL follow completion.

#### Scenario: Local workflow preparation is complete while remote delivery is held

- **GIVEN** locally verified workflow files and an active remote-delivery hold
- **WHEN** readiness is reported
- **THEN** local preparation is distinguished from pending remote activation, and neither publication nor active scheduled jobs are claimed

### Requirement: Deferred advice retains complete content and search

Initial transport SHALL keep structure and short advice within the unchanged configured budget, deferring detailed advice. Every supported language/part load order SHALL reconstruct the complete bilingual graph. The crate/API SHALL retain all content. Station routes and complete search SHALL wait for required advice. Language/load failures SHALL preserve a usable view, saved answers and retry, with local-file/iframe operation and no external request on load retained.

#### Scenario: Cold search needs deferred advice

- **GIVEN** a fresh browser whose detailed-advice language part has not loaded
- **WHEN** the reader searches for text present only in that advice while its download is delayed
- **THEN** complete results wait for the required part and include the matching advice rather than caching an incomplete index

#### Scenario: Advice language loading fails

- **GIVEN** a usable station and saved answers with the other language's advice not loaded
- **WHEN** switching languages fails to retrieve that part and the reader retries
- **THEN** the usable view and answers survive, retry loads the requested advice and the reconstructed graph retains both languages

### Requirement: Accessibility optimizations preserve audit outcomes and coverage

Optimized audits SHALL retain the pinned engine, shared WCAG policy, full context and required coverage. Reuse SHALL prove equivalent normalized rule/check/node outcomes, including deliberate violations and dynamic states. Frame/scoped audits SHALL retain the established adapter unless proven equivalent. Unproven cases SHALL fall back without suppressing rules, excluding navigation/frames or accepting incomplete results as passes.

#### Scenario: An optimization encounters an embedded frame

- **GIVEN** a page with a frame containing a deliberately inaccessible control
- **WHEN** the optimized check suite audits the page
- **THEN** frame coverage remains active through the established adapter and reports the violation

#### Scenario: A faster path disagrees with the reference

- **GIVEN** the same frame-free dynamic page state and policy audited through both implementations
- **WHEN** their normalized outcomes differ
- **THEN** equivalence is not accepted and that case retains the reference implementation with diagnostic evidence

### Requirement: CI partitions produce one complete attributable result

CI SHALL partition one verified build through one authoritative job/case inventory. Every lane SHALL verify checked source/build identity. Aggregate status, dashboard and API SHALL claim a complete pass only when all required work passes exactly once. Subsets SHALL stay partial; missing, duplicate, wrong-revision, failed, blocked or incomplete work, including setup failures, SHALL prevent a complete pass. Diagnostics and report/preview consumers SHALL remain usable.

#### Scenario: A browser partition does not finish

- **GIVEN** successful CPU and browser-lane reports but a missing required browser partition
- **WHEN** the aggregate runs after all lane outcomes
- **THEN** it reports the missing work and does not publish a complete passing required check or health result

#### Scenario: A partition has the wrong build or duplicate coverage

- **GIVEN** all lane artifacts are available but one has a different build identity or a repeated required case
- **WHEN** the collector reconciles the authoritative inventory
- **THEN** it rejects the aggregate with the identity or coverage discrepancy instead of relying on equal case totals

### Requirement: CI performance receipts preserve the coverage floor

Performance receipts SHALL distinguish elapsed time, queuing, active work and total runner cost with actual
coverage. Runtime targets SHALL NOT justify fewer cases, ignored initial failures or weaker validator profiles.

#### Scenario: A faster hosted candidate is measured

- **GIVEN** a previous full-run baseline and a partitioned candidate
- **WHEN** their performance is reported
- **THEN** revision/build identity, case coverage, elapsed time and runner cost accompany the result, and any initial failure remains recorded rather than counted as a successful retry

### Requirement: The footer shows the build's git identity

The footer SHALL show the Guide's version derived from the release tag, not from an authored copy, together with the
short commit the build was made from and a build date. A build not exactly at a release tag SHALL identify itself as
the unreleased `next` preview with the last tag, its distance ahead and its commit; a local build SHALL be
distinguishable from a published one.

#### Scenario: A tagged release

- **GIVEN** a build made from a release tag
- **WHEN** the footer is read
- **THEN** it shows the tag's version and the build's short commit

#### Scenario: The default branch is ahead of the last tag

- **GIVEN** a `/next/` build several commits after the last tag
- **WHEN** its footer is read
- **THEN** it is marked as the unreleased preview with the last tag, the number of commits ahead and its commit, and does not present itself as that tag

### Requirement: The build identity is carried by machine surfaces and checked

The same build identity SHALL agree across UI, health, crate and release manifest. Tag release SHALL accept
`release_status` as `testing` (default) or `production` and record it in an immutable annotated tag. A clean
exact-tag production build SHALL read that decision; local, dirty and preview builds SHALL use `testing`.
Documentation SHALL define the choices, notice behaviour and frozen-artifact semantics. CI SHALL reject
identity/revision mismatches.

#### Scenario: The approved production status is explicit

- **GIVEN** a clean exact-tag production build whose tag records `release_status=production`
- **WHEN** its verified artifact is produced
- **THEN** the UI, health, crate, manifest and image retain `production`, the testing notice is hidden, and retrying the tag workflow cannot relabel those bytes

#### Scenario: Missing or malformed tag status

- **GIVEN** a manually created tag without a status marker, or a tag with malformed or duplicate markers
- **WHEN** production is built
- **THEN** an unmarked tag defaults to `testing`, malformed or duplicate markers fail, and a repository variable cannot override the decision

#### Scenario: A release differs from the built page

- **GIVEN** a built page whose footer identity does not match the checked revision
- **WHEN** the checks run
- **THEN** they fail and name the page and the expected identity

#### Scenario: A preview build must not claim a release

- **GIVEN** a `/next/` build whose resolved status is `testing`
- **WHEN** its footer, health result and crate status are read
- **THEN** none of them claims a released Guide

### Requirement: Each release publishes a runnable container image

Each release SHALL publish a container image serving its verified, digest-checked site artifact unchanged, never
rebuilt from source. It SHALL be published to the GitHub container registry under its version, the tag without the
leading `v`. A moving `latest` SHALL name the newest approved release and a moving `stable` the newest approved
non-prerelease; neither SHALL move back. A deployed release SHALL receive its version tag and draft release even when
a newer one was approved meanwhile.

#### Scenario: Running a published release in a container

- **GIVEN** a reader with a container runtime
- **WHEN** they run the image for a release version
- **THEN** the guide is served locally and its footer shows the same version and commit as the release

#### Scenario: A prerelease is tagged

- **GIVEN** a prerelease tag such as `v1.0.0-alpha.5` that is the newest approved release
- **WHEN** its image is published
- **THEN** `latest` moves to it, `stable` does not, and the image carries the version `1.0.0-alpha.5` and no `v` tag

#### Scenario: A newer release is approved while an image is built

- **GIVEN** `v1.0.0-alpha.5` was deployed to Pages and `v1.0.0-alpha.6` was approved while the alpha.5 image was built
- **WHEN** the alpha.5 image is published
- **THEN** it carries `1.0.0-alpha.5` and its draft release is created, `latest` is not moved to it, and the summary names alpha.6 as the release that moves `latest`

#### Scenario: A release image published with its tag

- **GIVEN** the image of `v1.0.0-alpha.4`, published before version tags under `v1.0.0-alpha.4`
- **WHEN** a reader pulls `1.0.0-alpha.4`
- **THEN** they receive the same digest, and the `v1.0.0-alpha.4` tag still names it

### Requirement: A published image is signed, attested and reproducible

The image SHALL carry the build identity as OCI labels, be built reproducibly from the release date, and be published
with a vulnerability scan, an SBOM and a build-provenance attestation bound to its digest. The scan SHALL execute;
a failed scan operation SHALL stop publication, while vulnerability findings are advisory. The release SHALL record
the image reference and digest, and a check SHALL run the published image and confirm it serves the expected version
and commit.

#### Scenario: The image does not match the release

- **GIVEN** a published image whose served version or commit differs from its release
- **WHEN** the smoke check runs
- **THEN** it fails and reports the image digest and the mismatch

### Requirement: Native generation cannot overwrite another owner

Native generation SHALL reject any declared output overlapping an owned, tool-generated or runtime
path or any native source before writing an output. Existing reserved-path and alias protections
SHALL remain in force.

#### Scenario: A generated output targets an authored source

- **GIVEN** an output targets AGENTS, a native source, a tool-generated wrapper or a runtime path
- **WHEN** native generation validates the ownership map
- **THEN** it SHALL refuse before any write and leave every existing surface unchanged

### Requirement: Human tooling entrypoints are visible in contribution documents

`AGENTS.md` SHALL link `docs/agent-tooling.md`. Both `README.md` and `README_en.md` SHALL link it as
the human starting point near the beginning, and `CONTRIBUTING.md` SHALL do so in its introductory
section. The tooling document SHALL distinguish human onboarding from runtime `AGENTS.md`.

#### Scenario: A human opens a contribution entry document

- **GIVEN** either README language or CONTRIBUTING
- **WHEN** a contributor reads its introductory material
- **THEN** a labelled link SHALL lead to the human tooling guide and explain the runtime entry separately

### Requirement: Native usage logging follows delivered field owners

Native usage guidance SHALL refer to the delivered notability, runtime/backend and field owners rather
than define a competing field set. Guide usage entries SHALL use the owners' exact labels while keeping
the guide-owned usage location.

#### Scenario: A native log uses different field labels

- **GIVEN** a guide usage entry with labels that differ from the delivered field contract
- **WHEN** usage compliance is checked
- **THEN** it SHALL require the canonical labels and the native guidance SHALL point to their owner

### Requirement: Agent setup uses pinned repository dependencies

Copilot setup SHALL install the repository's locked dependencies and invoke the pinned local OpenSpec
CLI. It SHALL NOT install an unversioned global CLI. Setup SHALL retain read-only repository permissions
and nonpersisted checkout credentials, and regeneration checks SHALL detect a return to an unpinned route.

#### Scenario: Setup is regenerated with an unpinned install

- **GIVEN** a setup workflow installs OpenSpec without the repository lockfile pin
- **WHEN** workflow validation runs
- **THEN** it SHALL fail and identify the unpinned installation route

### Requirement: Release preparation validates the complete permitted file set

Release preparation SHALL obtain its expected file set from one shared structured owner, independent of
the emitted digest manifest. The publisher SHALL reject missing, extra, duplicate or noncanonical paths,
absolute paths, traversal and filesystem escapes before reading prepared files or making GitHub writes.
It SHALL bind each accepted file to its prepared digest and preserve reviewed retry recovery.

#### Scenario: A manifest selects an extra file with a matching digest

- **GIVEN** a manifest names a file outside the shared permitted set and supplies its correct digest
- **WHEN** the publisher validates the manifest
- **THEN** it SHALL refuse without reading that file or making a GitHub write

#### Scenario: An allowed path escapes through a filesystem link

- **GIVEN** an otherwise allowed relative path resolves outside the repository or aliases another path
- **WHEN** the publisher validates prepared paths
- **THEN** it SHALL refuse before reading prepared file bytes or making a GitHub write

### Requirement: Health publication reuses its content context

One publication run SHALL reuse its loaded content and constructed crate/graph across pending, final
and failure report emissions, including partitioned CI collection. Each emission SHALL retain its
current outcomes; reuse SHALL NOT suppress failure reporting or change API/dashboard semantics.

#### Scenario: A publication run emits several health snapshots

- **GIVEN** a successful build followed by pending, final and optional failure health publication
- **WHEN** the runner publishes those snapshots
- **THEN** it SHALL parse content and construct the publication crate once and report each actual outcome

### Requirement: Later review rounds retain summary-only observations

Later review rounds SHALL retain summary-only observations alongside inline findings, with a disposition,
owning repair location and verification or dispute evidence. Existing closures SHALL remain historical
receipts unless current evidence requires reopening them.

#### Scenario: A later review records an upstream source observation

- **GIVEN** a review summary identifies a defect faithfully copied from an upstream workflow
- **WHEN** the follow-up ledger is captured
- **THEN** it SHALL retain that observation, route correction to its authored source and require verified redelivery

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

### Requirement: Scheduled dependency updates group patch versions

Dependabot SHALL group patch- and minor-version updates for all dependencies within each configured ecosystem:
GitHub Actions, npm, pip and Docker. Major updates SHALL remain individual PRs. Grouping SHALL preserve the
configured directories, weekly schedules, the limit of 30 open version PRs and the existing security-update policy.

#### Scenario: Several patch updates are available

- **GIVEN** several dependencies in one configured ecosystem have patch- or minor-version updates
- **WHEN** Dependabot proposes scheduled version updates
- **THEN** those updates are eligible for one grouped PR for that ecosystem regardless of dependency name

#### Scenario: Minor and major versions are available

- **GIVEN** patch, minor and major updates are available for dependencies in a configured ecosystem
- **WHEN** Dependabot applies the grouping policy
- **THEN** patch and minor versions enter the group, and the major update stays outside it and remains eligible for its own PR

#### Scenario: Existing update settings are retained

- **GIVEN** the four configured ecosystems, their current directories, weekly schedules and limit of 30 open version PRs
- **WHEN** grouping is configured
- **THEN** each ecosystem retains those settings and the existing security-update policy

### Requirement: Aggregate checks report every failure with diagnostics

Required aggregate checks SHALL name every failed or partial check and include bounded diagnostics while preserving lane logs and details. Partial results SHALL fail even at native exit zero, locally as in CI, retaining their partial flag and original evidence. Required diagnostics SHALL precede optional suggestions; optional processing errors SHALL be reported without hiding diagnostics or changing the required-check outcome. The gate SHALL remain failing when required checks fail.

#### Scenario: Two checks fail in one lane

- **GIVEN** content and duplicates both fail in the CPU lane
- **WHEN** the collector reconciles the lane
- **THEN** the aggregate names both checks and includes their error text

#### Scenario: A lane fails before the collector publishes

- **GIVEN** a failed lane with logs and details
- **WHEN** the collector rejects the aggregate
- **THEN** the health artifact contains those logs and details

#### Scenario: A browser check leaves pending cases

- **GIVEN** a required browser result with exit code zero, partial coverage and pending or skipped cases
- **WHEN** the collector publishes the aggregate
- **THEN** the aggregate and check row are failed, its output is shown, and the partial evidence remains inspectable

#### Scenario: The local run meets a partial child

- **GIVEN** a local full run whose browser check exits zero with partial case coverage
- **WHEN** the local runner publishes its report and returns
- **THEN** that row and the run are failed, its output is shown, and the run exits non-zero

#### Scenario: A deliberate local subset completes

- **GIVEN** a local `--only` run whose selected checks all complete
- **WHEN** the run finishes
- **THEN** the unselected checks stay not run, the report remains partial, and the run exits zero

#### Scenario: Optional output cannot be written

- **GIVEN** reconciled check results and an unwritable optional suggestion destination
- **WHEN** optional publication fails
- **THEN** the required report and its original pass/fail outcome remain available and the optional error is reported

#### Scenario: A known failure accompanies missing lane evidence

- **GIVEN** the CPU lane reports a failed content check and a required browser lane report is missing or has the wrong identity
- **WHEN** the collector reconciles the lanes
- **THEN** the aggregate names the content failure and the missing or rejected lane, keeps their logs, never claims a complete run and admits no data from the rejected lane

#### Scenario: A newer push cancels a run

- **GIVEN** a run whose lanes a newer push cancels
- **WHEN** the run ends
- **THEN** the collector does not run, so no evidence failure is reported for lanes that never finished, and the required gate still reports no success for it

### Requirement: The trusted review comment surfaces suggested fixes

The trusted publisher SHALL show bounded exact suggestions and reasons as inert text, never apply them, and keep PR checks read-only. Only reconciled duplicate-lane evidence SHALL supply suggestions, retaining checked revision separately from the current PR head and rejecting stale heads or repositories. Invalid artifacts SHALL be filtered safely. Required evidence rejection SHALL publish no suggestions; upload SHALL admit only successfully generated current-run output.

#### Scenario: A duplicate suggestion is available
- **GIVEN** a completed check run with a safe duplicate suggestion
- **WHEN** the trusted publisher posts the review comment
- **THEN** the comment shows the exact file, table, field and value and does not edit the repository

#### Scenario: The PR head moved
- **GIVEN** suggestion data for an earlier head
- **WHEN** the publisher runs
- **THEN** it skips the stale comment

#### Scenario: Checks ran on the merge commit
- **GIVEN** a checked merge revision that differs from the PR source head
- **WHEN** the collector prepares suggestions for the trusted publisher
- **THEN** it retains both identities and the publisher admits suggestions for the current PR source head

#### Scenario: Wrong lane identity accompanies plausible suggestions

- **GIVEN** a lane with a stale source revision or wrong build identity and a valid-looking duplicates artifact
- **WHEN** the collector rejects the evidence
- **THEN** no suggestion from that run is published under the current PR head

#### Scenario: Required evidence is incomplete

- **GIVEN** a missing lane, duplicated job or invalid required script/case evidence
- **WHEN** aggregate reconciliation fails
- **THEN** the failure diagnostics are retained but no suggestions are published

#### Scenario: A valid duplicate failure produces suggestions

- **GIVEN** reconciled lanes with a failing duplicate check and safe suggestions from its owning lane
- **WHEN** the collector emits the failed aggregate
- **THEN** those suggestions remain available with the checked revision and current PR source head kept separate

#### Scenario: An unrelated directory carries suggestions

- **GIVEN** valid required lanes and an extra directory with a duplicates artifact
- **WHEN** the collector gathers suggestions
- **THEN** it ignores the extra artifact

#### Scenario: A suggestion field is an array or object

- **GIVEN** an otherwise recognizable artifact with a non-string file, table, field or identity value
- **WHEN** the collector validates it
- **THEN** it drops the malformed suggestion and continues emitting required diagnostics

#### Scenario: An earlier suggestions file exists

- **GIVEN** a previous suggestions output and a newly rejected aggregate
- **WHEN** the collector completes its failure path
- **THEN** the previous suggestions are removed, replaced by an empty payload, or excluded from the uploaded review artifact rather than republished

#### Scenario: Invalidating an earlier artifact fails

- **GIVEN** a previous suggestions file and an I/O failure when invalidating it
- **WHEN** the collector handles the optional error
- **THEN** the required report retains its outcome and the upload receives no suggestion path for that run

#### Scenario: A reason contains an external address or mention

- **WHEN** a reason containing a bare URL, Markdown link, image, mention or backtick is rendered
- **THEN** neither publication surface turns the reason into a clickable link, embedded image or notification

### Requirement: A maintainer can request a safe duplicate fix

A trusted fix command SHALL verify current writer access and apply only reviewed safe links on eligible same-repository PRs with requester provenance and changed-field reporting. It SHALL reject forks and schedules, never merge, write the default branch or accept duplicates. Bot diffs SHALL be bounded inert text; uncertain failures SHALL require branch inspection. Refresh SHALL preserve repairs and replace only complete, nonempty lists of the configured App's expected snapshot commits.

#### Scenario: An unauthorised caller requests the fix
- **GIVEN** a comment from an account without current write access
- **WHEN** the trusted handler reads it
- **THEN** it applies nothing and reports the refusal

#### Scenario: A safe suggestion is applied
- **GIVEN** a maintainer's fix request on a same-repository PR with one safe suggestion
- **WHEN** the handler completes
- **THEN** the branch has the link and a provenance action naming the maintainer, and the checks rerun

#### Scenario: The content has an identifier register
- **GIVEN** a safe suggestion against content with a populated identifier register
- **WHEN** the handler validates and commits the repair
- **THEN** the new provenance action is registered and committed with the link, existing and retired IDs remain unchanged, and unrelated unregistered entries still prevent the commit

#### Scenario: Content references authored attachments
- **GIVEN** a safe suggestion against content that references scripts, documentation and icons
- **WHEN** the handler validates the extracted PR data
- **THEN** it checks those attachments from the same verified head without executing PR code and commits only the repaired content, provenance and identifier register

#### Scenario: The group is ambiguous
- **GIVEN** a duplicate group without a safe suggestion
- **WHEN** the handler runs
- **THEN** it changes nothing and reports why human review is required

#### Scenario: The head moved before the handler's first read
- **GIVEN** content extracted from an earlier PR head
- **WHEN** the first validated PR head read differs from the recorded extraction SHA
- **THEN** the handler refuses before applying changes or creating a commit

#### Scenario: A refresh PR contains a duplicate repair by the same App

- **GIVEN** an open refresh PR with a snapshot commit followed by an App-authored duplicate repair
- **WHEN** newer changed source content is published
- **THEN** its link, provenance and registered identifier remain intact and the publisher explains the manual reconciliation

#### Scenario: The branch contains only recognized refresh commits

- **GIVEN** an open proposal whose commits all belong to the configured App and have the expected source-refresh message
- **WHEN** newer changed source content is published
- **THEN** the ordinary refresh update remains available

#### Scenario: Branch ownership is unknown

- **GIVEN** a missing bot identity, unavailable or empty commit inventory, different author, or unexpected message
- **WHEN** publication evaluates whether it may replace the branch
- **THEN** it preserves the branch and reports why automatic replacement was refused

#### Scenario: A repair diff contains a fence and is truncated

- **GIVEN** PR-authored diff context containing Markdown and fence delimiters and exceeding the comment budget
- **WHEN** the success comment is formatted
- **THEN** the diff stays inert inside a closed enclosure and the commit reference remains visible

#### Scenario: Posting the success comment fails after committing

- **GIVEN** the App successfully updates the PR branch and the following comment request fails
- **WHEN** the workflow reports the unexpected failure
- **THEN** it points to the run and asks the maintainer to check the branch state without claiming no change occurred

### Requirement: The unpublished changelog section is checked

`CHANGELOG.md` SHALL have exactly one top-level `[Unreleased]` section whose entries are meaningful when present.
Against the base revision, released sections SHALL stay byte-identical, except that a complete release transition
SHALL be accepted and the newest section of a version not yet tagged MAY gain generated lineage entries. Local and
PR checks SHALL report the exact structural problem and SHALL NOT edit the changelog.

#### Scenario: The section is missing or duplicated

- **WHEN** `[Unreleased]` is absent or appears twice
- **THEN** the check fails and names the structural problem and its fix

#### Scenario: The section holds only placeholders

- **WHEN** `[Unreleased]` contains only empty category headings or placeholder text
- **THEN** the check reports the missing meaningful entry
- **AND** an intentionally empty section after a release passes

#### Scenario: Published history is changed

- **WHEN** a PR changes an existing released section relative to its base
- **THEN** the check refuses the historical edit and directs the correction to `[Unreleased]`
- **AND** previously accepted historical section formats pass without conversion

#### Scenario: A release consumes the unpublished entries

- **WHEN** release preparation moves the unpublished entries into a new dated section and resets `[Unreleased]`
- **THEN** the check accepts the transition without requiring another unpublished entry
- **AND** a transition that loses entries or changes earlier releases is rejected

#### Scenario: A prepared release is completed before its tag

- **WHEN** a completion PR appends linked pull-request or commit entries to the newest section, whose version has no tag yet
- **THEN** the check accepts it
- **AND** any other change to that section, or an entry added once the version is tagged, is refused as a historical edit

### Requirement: Release preparation retains curated unpublished notes

Release preparation SHALL move the curated `[Unreleased]` body unchanged into the new dated section, followed by
the complete deduplicated PR and direct-commit lineage, and reset `[Unreleased]`. It SHALL refuse before writing
when the curated notes use a reserved lineage heading. Earlier released sections SHALL remain byte-identical.

#### Scenario: Curated notes and lineage are both available

- **WHEN** the maintainer prepares a release with curated notes and merged PRs or direct commits
- **THEN** the dated section contains the curated notes followed by the complete linked lineage
- **AND** PR titles do not replace the curated explanations

#### Scenario: There are no curated notes

- **WHEN** release preparation finds an empty `[Unreleased]` section and a nonempty release history
- **THEN** it keeps the existing PR-only, direct-only, mixed and first-release behaviour

#### Scenario: Curated notes use a reserved heading

- **WHEN** the curated notes contain a heading reserved for the generated lineage
- **THEN** preparation refuses before changing any file and names the conflicting heading

### Requirement: Release-note and planning hints are advisory

The trusted PR review comment SHALL state whether the PR adds an `[Unreleased]` line and SHALL add a planning hint
when behaviour, CI or governance paths change without a linked OpenSpec change. Hints SHALL be derived from the diff
and commits, SHALL NOT read PR body text as instructions and SHALL NOT fail checks. Dependency and source-refresh
PRs SHALL be shown as covered by the generated release lineage.

#### Scenario: A page change has no unpublished line

- **WHEN** a human PR changes reader-facing behaviour without an `[Unreleased]` line
- **THEN** the review comment says that its commit messages feed the release notes and that only a breaking change, a required step or a security fix needs a line, and the checks are unaffected

#### Scenario: A dependency update

- **WHEN** a Dependabot or source-refresh PR has no `[Unreleased]` entry
- **THEN** the review comment states that the generated release lineage covers it

#### Scenario: A workflow change without planning

- **WHEN** a PR changes workflow or script behaviour paths and neither adds nor references an OpenSpec change
- **THEN** the review comment names the touched paths and links the planning guidance, without failing the PR

### Requirement: Release bodies combine reviewed notes with the verification record

The release workflow SHALL draft each release body with a changelog link and one marked verification record. A
native helper SHALL compose the body from the publishable release-notes report and that record, keeping the record
byte for byte, SHALL show the composition first and SHALL write only that reviewed composition to an unpublished
draft.

#### Scenario: Reviewed notes are applied

- **GIVEN** a draft release with its verification record and a publishable release-notes report
- **WHEN** the maintainer reviews the composed body and applies it
- **THEN** the draft carries the notes without the report's title, followed by the unchanged verification record, and the helper confirms the stored body

#### Scenario: The inputs changed after review

- **WHEN** the notes or the release body differ from those of the reviewed composition
- **THEN** the helper writes nothing and asks for a new review

#### Scenario: An unsafe input

- **WHEN** the notes are the working companion, the body lacks a single marked record or the release is already published
- **THEN** the helper writes nothing and names the reason and the fix

### Requirement: Release notes come from durable history

Release notes and the changelog SHALL be drawn from commit messages, merged pull requests and issues, never from
pull-request descriptions alone. `[Unreleased]` SHALL hold a line only for a breaking change, a required step or a
security fix; the generated lineage covers every other change.

#### Scenario: A pull request description is edited after merge

- **WHEN** a merged pull request's description changes later
- **THEN** the changelog lineage and the source of the release notes stay the same, because they come from the squash commit, its kept commit messages and the issues

#### Scenario: An ordinary feature is merged

- **WHEN** a pull request adds a feature without breaking anything
- **THEN** it needs no `[Unreleased]` line, and the next release lists it through the generated lineage

### Requirement: New content under the existing model needs no OpenSpec change

Editing guidance SHALL treat a new content instance under the existing content model, such as an advice item,
question or resource, as content work with its usual sources, paradata and checks. It SHALL require an OpenSpec
change when the edit alters behaviour, assessment meaning, a stored format, CI or governance.

#### Scenario: A contributor adds advice

- **WHEN** a contributor adds an advice item that uses existing fields, lenses and levels
- **THEN** the guidance leads to the content edit, sources, paradata and checks without an OpenSpec change

#### Scenario: A contributor adds a content field

- **WHEN** a contributor needs a new field in the content model
- **THEN** the guidance leads to an OpenSpec change before implementation

### Requirement: Guide usage filenames carry their start date

Guide usage entries SHALL be named `usage-YYYY-MM-DD-<topic>.md` with a valid date equal to the entry's first `When`
date and SHALL carry the delivered canonical field labels. Later sessions of a rolling entry SHALL keep the
original filename. Violations SHALL name the file and the exact rename or missing label.

#### Scenario: A new entry has no date

- **WHEN** the offline checks find `usage-ci-workflows.md`
- **THEN** they fail and name the required `usage-YYYY-MM-DD-<topic>.md` form

#### Scenario: A rolling entry gains a later session

- **WHEN** an entry named for 2026-10-20 records a further session dated 2026-10-24
- **THEN** the check passes without a rename

#### Scenario: The filename date differs from the first session

- **WHEN** the filename date is not the first `When` date
- **THEN** the check fails and names the expected filename

### Requirement: Comment commands keep every accepted request

One trusted workflow SHALL read issue and PR comments, ignore non-commands before taking any concurrency slot and
queue accepted commands per affected resource. Each accepted command SHALL get an immediate acknowledgement and a
final outcome naming its run, result and next step, including waiting, refusal and queue overflow. Existing
command syntax and trust guards SHALL remain.

#### Scenario: An unrelated comment arrives while a command waits

- **GIVEN** a `/refresh re3data` command waiting behind a running refresh of the same source
- **WHEN** someone posts an ordinary comment on another PR
- **THEN** the waiting command still runs and reports its outcome

#### Scenario: Two maintainers request the same repair

- **WHEN** two `/fix-duplicates` commands arrive for one PR
- **THEN** they run one after the other, and the second reports either its own result or that nothing remains to repair

#### Scenario: The queue is full

- **WHEN** a command arrives and its resource queue is at capacity
- **THEN** the caller receives a refusal with retry guidance instead of a silent cancellation

#### Scenario: An unauthorised caller

- **WHEN** an account without current write access sends a privileged command
- **THEN** it is refused as before and no App credential is used

### Requirement: Contributors can ask which commands apply

`/help` SHALL answer in one bot-maintained comment per thread with the commands available there, whether the
caller may use each and why not, using the same eligibility rules as the commands themselves. A command that
closely resembles a known one SHALL receive a suggestion. Help SHALL write nothing except its comment and reaction.

#### Scenario: A maintainer asks on a PR with a safe suggestion

- **WHEN** a maintainer sends `/help` on a same-repository PR whose latest checks offer a safe duplicate repair
- **THEN** the help comment lists `/fix-duplicates` as available and states what it will change

#### Scenario: A command is unavailable

- **WHEN** `/help` is sent on a fork PR or by an account without write access
- **THEN** the help comment explains why each privileged command is unavailable and gives the local alternative

#### Scenario: Help is asked again

- **WHEN** `/help` is sent a second time in the same thread
- **THEN** the existing help comment is updated rather than a new one posted

#### Scenario: A command is mistyped

- **WHEN** a comment starts with `/fixduplicates`
- **THEN** the reply suggests `/fix-duplicates` and runs nothing

### Requirement: Fast feedback precedes the complete check

Pull requests SHALL receive a separate quick result from cheap offline checks while the complete partitioned checks
run. The quick result SHALL NOT replace or satisfy the required `checks` context, and every failure it reports
SHALL also appear in the complete result.

#### Scenario: A content error is pushed

- **WHEN** a PR introduces a content-contract error
- **THEN** the quick result fails first and names the item, and the required `checks` still run and fail on the same error

### Requirement: Check partitions are balanced without losing coverage

Lane assignment, case splits and unit-test shards SHALL be derived from measured timings. The authoritative
inventory SHALL still require every check, case and validator profile exactly once, and a failure in any lane, case
or shard SHALL fail the result. A speed claim SHALL come from paired runs at a fixed commit with unchanged coverage.

#### Scenario: Lanes are rebalanced

- **WHEN** checks move between lanes or a long script is split into cases
- **THEN** the collector still rejects a missing or duplicated check or case

#### Scenario: One unit-test shard fails

- **WHEN** a single test fails in one of several shards
- **THEN** the unit check fails, names the test and keeps the merged timing report

#### Scenario: A faster candidate skips work

- **WHEN** a candidate finishes sooner because a case or validator profile did not run
- **THEN** it is rejected as incomplete and no speed gain is recorded

### Requirement: Dependency caches speed up setup without becoming evidence

Dependency caches SHALL be keyed on the lockfile or requirements and a compatible runtime, SHALL fall back to a
cold install and SHALL report hit or miss. Lanes SHALL install only the tools their checks use. Cache contents SHALL
NOT replace current checks, store credentials or pass from PR runs into trusted runs.

#### Scenario: The lockfile changes or the cache is missing

- **WHEN** `package-lock.json` or `requirements-dev.txt` changes, or a restore fails
- **THEN** the lane installs from a compatible cache or cold and runs the same checks

### Requirement: The merge queue verifies the merged result

Merges into the default branch SHALL pass through a merge queue that runs the required `checks` on the merged
result, while each PR's own checks remain required before it can be queued. Human and bot PRs SHALL use the same
queue. The trusted review comment SHALL ignore merge-group runs. An administrator's direct merge SHALL remain
possible and SHALL receive full deployment checks.

#### Scenario: Two approved PRs are queued

- **WHEN** two approved PRs with passing checks enter the queue
- **THEN** each merges only after its merged result passes, and a failing entry leaves the queue with the reason

#### Scenario: A Dependabot PR is approved

- **WHEN** a maintainer approves a grouped dependency PR and adds it to the queue
- **THEN** it follows the same verification and merge path as a human PR

#### Scenario: An administrator merges directly

- **WHEN** an administrator bypasses the queue
- **THEN** the default-branch deployment runs the full checks because no queue result exists for that content

#### Scenario: The queue's checks complete

- **WHEN** a merge-group check run completes
- **THEN** the review-comment publisher skips it and changes no PR comment

### Requirement: Staging deploys reuse verified results and need no approval

A default-branch deployment SHALL reuse a successful merge-queue check result only when the deployed tree and build
inputs equal the checked ones and the result's health snapshot validates; otherwise it SHALL run the partitioned
checks. Deployments that only update staging SHALL need no manual approval. The run summary SHALL name the reused run
or the reason for the fallback.

#### Scenario: The merged content was verified in the queue

- **WHEN** the default-branch commit has the same tree and build inputs as a passing merge-group run
- **THEN** deployment builds the site, imports that run's validated health snapshot, updates `/next/` without approval and names the reused run

#### Scenario: No matching verified result exists

- **WHEN** the tree differs, no passing merge-group run exists or its snapshot fails validation
- **THEN** deployment runs the complete partitioned checks before publishing and states why

#### Scenario: Build inventories name different producing runs

- **WHEN** the fresh build differs from the queue build only in the three health files that adoption replaces
- **THEN** those differences do not prevent reuse, every other built file must match and the imported health snapshot still passes identity and schema validation

#### Scenario: Adoption fails while the summary is written successfully

- **WHEN** adoption rejects a result and the summary pipeline succeeds
- **THEN** deployment selects the complete partitioned checks and uploads no unchecked staging site as reused

### Requirement: Production promotion requires explicit approval

A deployment that would change the production site SHALL wait for approval in a dedicated protected environment
before publication. A deployment that only updates staging SHALL keep the last approved production bytes. Tag
release SHALL explain when the current default-branch commit has no successful deployment yet and which run to wait for.

#### Scenario: A release tag is pushed

- **WHEN** the tag's deployment is ready to publish new production bytes
- **THEN** it waits for a maintainer's approval and publishes production only after it

#### Scenario: The default branch advances while a tag waits

- **WHEN** a merge lands while a production promotion awaits approval
- **THEN** its deployment updates staging and keeps the last approved production bytes

#### Scenario: A tag is approved after the default branch moved on

- **WHEN** a waiting production promotion is approved after a newer default-branch commit was deployed
- **THEN** it publishes the approved production beside the latest checked staging site, and neither channel moves back

#### Scenario: Tagging an undeployed commit

- **WHEN** Tag release runs before the current default-branch commit has a successful deployment
- **THEN** it creates no tag and names the deployment run to wait for

### Requirement: Pages publication is serialized and never regresses a channel

Preparation SHALL be cancellable and separate from one serialized publication step. Before publishing, trusted code
SHALL recheck the current eligible production and staging identities and refuse or supersede stale output.
Approval waits SHALL NOT block independent preparation. A superseded run SHALL name its successor.

#### Scenario: An older run reaches publication after a newer one

- **WHEN** a run's staging commit is older than the staging commit already published
- **THEN** it publishes nothing and its summary names the newer run

#### Scenario: Preparation is cancelled

- **WHEN** a newer default-branch push cancels an older run's preparation
- **THEN** the published site is unchanged and the cancelled run names its successor

### Requirement: Repository settings have a reviewed expected state

`.github/repository.toml` SHALL describe the expected rulesets, merge queue, environments, labels and Project
configuration. A read-only audit SHALL report each difference with its UI path and an equivalent command, SHALL
report unreadable settings as unavailable rather than as matching, and SHALL apply only additive label and
Project-item fixes on explicit request.

#### Scenario: A setting drifts

- **WHEN** a ruleset, environment, Project view or built-in automation differs from the reviewed file
- **THEN** the audit names the setting, the expected and actual values, the UI path and an equivalent command

#### Scenario: An approved target waits for its task

- **WHEN** an approved target is not applied yet and another setting of the same ruleset or environment drifts
- **THEN** the audit lists the target as pending with its task and precondition, and the drift's command keeps the target at its live value

#### Scenario: A setting cannot be read

- **WHEN** the token in use cannot read a configured setting
- **THEN** the audit reports that setting as unavailable and names the access needed

#### Scenario: Fixes are requested

- **WHEN** a maintainer runs the audit with its fix option
- **THEN** it creates missing declared labels and adds missing Project items, and never deletes a label or changes a field value

### Requirement: Automation identities hold only the permissions they use

Each workflow job SHALL request only the token permissions it uses, and the GitHub App's registered permissions
SHALL match a reviewed list. App Project and organization Issue Types/Fields reads SHALL be audit-only and
read-only, with credentials routed per endpoint. Registration, installation acceptance and successful reads SHALL
be distinct evidence. Denied reads SHALL name the inaccessible part and actual cause without failing unrelated publication.

#### Scenario: The audit token is denied

- **WHEN** the audit job cannot read the configured Guide Project
- **THEN** the digest reports the inaccessible Project part and actual cause, names an owner action only when required, and the rest of the digest publishes

#### Scenario: A job requests an unlisted permission

- **WHEN** a workflow job requests a token permission that is not in the reviewed list for it
- **THEN** the offline workflow check fails and names the job and permission

#### Scenario: Organization reads need the accepted App scope

- **GIVEN** the registration advertises a read permission but installation acceptance or endpoint access is missing
- **WHEN** the audit reads organization issue types or fields
- **THEN** it uses the audit App credential, reports the specific unavailable read, retains readable repository/Project results and claims no success from registration alone

### Requirement: Labels are managed as reviewed configuration

Area and automation labels SHALL be declared in the reviewed settings file. Label synchronization SHALL create or
update declared labels and SHALL NOT delete a label; undeclared labels SHALL be listed for a human decision.

#### Scenario: A declared label is missing

- **WHEN** the audit runs with its fix option and `area:sources` does not exist
- **THEN** the label is created with its declared colour and description

#### Scenario: A label is not declared

- **WHEN** the repository has a label absent from the reviewed file
- **THEN** the audit lists it for a decision and does not delete it

### Requirement: Pull requests receive area labels from their changed paths

The trusted review publisher SHALL add the declared area labels that match a PR's changed paths, read from the
GitHub API, and the source-refresh publisher SHALL label its PRs. Automation SHALL only add labels and SHALL NOT
remove a label or re-add one that a person removed.

#### Scenario: A PR touches content and workflows

- **WHEN** a human PR changes `content/` and `.github/workflows/`
- **THEN** it receives `area:content` and `area:delivery`

#### Scenario: A person removes an automatic label

- **WHEN** a maintainer removes an area label the publisher added
- **THEN** later runs do not add it again

#### Scenario: A source refresh PR is opened

- **WHEN** the refresh publisher opens or updates its PR
- **THEN** the PR carries `source-refresh` and the matching area label

### Requirement: Issue templates follow the planned-issue shape

Issue templates SHALL be generated in Czech and English for bug, feature and task from the delivered
`aiscr-plan-issue` shape declarations, carrying its metadata table, sections and type block in one language, and
SHALL set the matching native issue type. A check SHALL fail when the templates differ from the current declarations.

#### Scenario: A reporter opens a template

- **WHEN** a reporter chooses the Czech bug template
- **THEN** the body contains the declared Czech metadata table, `Problém`, `Reprodukce`, `Rozsah`, `Akceptační kritéria` and `Otevřené otázky`, and the issue type is Bug

#### Scenario: The delivered shape changes

- **WHEN** a delivery update changes a declared heading
- **THEN** the offline check fails and names the regeneration command

### Requirement: Project consistency is audited with actionable fixes

A weekly read-only audit SHALL report open issues or PRs missing from Project #1, issues without a type, a body type
that differs from the native type, Ready issues lacking an area label, Priority, Effort or the planned-issue shape,
triage older than 14 days, Urgent issues without progress, state mismatches and automation or view drift, each with
a link or fix step.

#### Scenario: An open issue is missing from the Project

- **WHEN** an open issue is not a Project item
- **THEN** the audit lists it with the fix command

#### Scenario: A Ready issue is incomplete

- **WHEN** an issue in Ready has no Effort or lacks a planned-issue section
- **THEN** the audit lists the missing parts and links the issue

#### Scenario: Urgent work has not started

- **WHEN** an Urgent issue has stayed in Needs triage or Ready for more than three days
- **THEN** the digest lists it

#### Scenario: A built-in automation is switched off

- **WHEN** a Project automation expected to be on is disabled
- **THEN** the audit names it and the affected items

### Requirement: One maintenance digest is rebuilt from current state

Monitoring SHALL publish one open digest issue whose automation-owned body is rebuilt from current state on each
run. It SHALL comment only when findings appear, change, recover or expire, and a retry SHALL NOT repeat a comment.
Closing the digest SHALL start a successor that links its predecessor and carries all unresolved state and open
tasks. Two open digests SHALL stop publication with a warning.

#### Scenario: Only dates and counters advance

- **WHEN** a run finds no new, changed, recovered or expired finding
- **THEN** the digest body is refreshed and no comment is posted

#### Scenario: A publication is retried

- **WHEN** a run that already commented is retried
- **THEN** it recognizes its comment and posts no duplicate

#### Scenario: A maintainer closes the digest

- **WHEN** the next run finds no open digest
- **THEN** it opens a successor with all unresolved findings, limitations and open tasks, links both issues and moves open tasks to the successor
- **AND** closed tasks stay with the predecessor

#### Scenario: Two digests are open

- **WHEN** publication finds more than one open digest
- **THEN** it writes nothing and its summary names both issues and the fix

### Requirement: Maintainers promote findings into tasks

An observation SHALL become a task only when a person with write access creates it, for example from the digest's
prefilled task link. Automation SHALL attach such tasks to the digest while they are open, show them beside their
findings and keep closed tasks with their dispositions where they are. Recurrence SHALL ask for triage only on a material change and SHALL NOT reopen or recreate a task.

#### Scenario: A persistent failure is not triaged

- **WHEN** an unreviewed link fails across several runs
- **THEN** it stays in the digest's triage section and no task is created

#### Scenario: A maintainer tracks a finding

- **WHEN** a maintainer creates a task from the digest's link
- **THEN** the next run attaches it as a sub-issue of the digest and shows it beside the finding

#### Scenario: A closed task's finding continues

- **WHEN** a task was closed with a disposition and its finding persists unchanged
- **THEN** the digest shows the disposition and does not reopen the task
- **AND** a changed outcome returns the finding to triage

### Requirement: Monitoring coverage is bounded and explicit

Monitoring SHALL report eligible, attempted, deferred and invalid targets and distinguish unobserved targets from
successes. Selection SHALL give unchanged targets continuing coverage under the global request budget and a per-host
cap. Deferred targets SHALL keep their dated observation without new failures or recoveries.

#### Scenario: The inventory exceeds the request budget

- **GIVEN** 673 eligible URLs and a 600-request budget
- **WHEN** successive complete runs inspect the unchanged inventory
- **THEN** every URL is attempted within two runs and each report states its attempted and deferred counts

#### Scenario: A failing target is deferred

- **WHEN** a target with a persistent failure is outside this run's selection
- **THEN** the digest keeps its dated observation as unrefreshed without counting a new failure or a recovery

#### Scenario: One host throttles requests

- **WHEN** one host answers with rate limiting
- **THEN** its requests stop at the per-host cap and other hosts are still attempted

#### Scenario: Content no longer names a target

- **WHEN** a link, service, watched page or FAIR Champion test is removed from the content
- **THEN** the next run drops it from the state, with a page's baseline and unreviewed items, and the digest no longer lists it

### Requirement: Reviewed monitoring limitations retain their basis

A monitoring limitation SHALL name an exact finding and outcome, reason, evidence, reviewer, review date and
review-by date. Acknowledged observations SHALL stay visible and rechecked. A changed outcome, changed target or
passed deadline SHALL return the finding to triage. Wildcards, missing evidence and conflicting entries SHALL fail
validation.

#### Scenario: A reviewed denial recurs

- **WHEN** a URL with a current limitation for HTTP 403 answers 403 again
- **THEN** the digest shows it as a known limitation with fresh evidence and asks for nothing

#### Scenario: The basis changes or expires

- **WHEN** that URL answers 404, its address changes or the review-by date passes
- **THEN** the finding returns to triage

#### Scenario: An entry is too broad

- **WHEN** a limitation uses a wildcard, lacks evidence or conflicts with another entry
- **THEN** offline validation fails and names the entry

#### Scenario: A new denial needs review

- **WHEN** an unreviewed URL answers 403
- **THEN** the digest offers a ready-to-paste limitation entry for the maintainer to complete

### Requirement: Watch state survives between runs or its loss is explicit

Monitoring state SHALL persist between runs in durable run storage with a format version. Valid previous state
SHALL migrate; missing, expired or malformed state SHALL produce an explicit reset notice and SHALL NOT claim
streaks or recoveries. Human decisions SHALL NOT live only in this state.

#### Scenario: The previous state is available

- **WHEN** the previous successful run's state is valid
- **THEN** persistence streaks continue from it

#### Scenario: The previous state is missing

- **WHEN** no readable previous state exists
- **THEN** the digest shows a state-reset notice and reports no streak or recovery

#### Scenario: The state has the previous format

- **WHEN** the previous state uses the earlier format version
- **THEN** it is migrated and its baselines and streaks are kept

### Requirement: Digest entries stay readable in the issue

The digest SHALL show link findings that share a host and outcome as one entry giving the number of links and the
affected records. A section longer than its limit SHALL continue in a collapsed list in the issue body. The run
artifact SHALL hold raw observations only and SHALL NOT be the only place a finding a person must see appears.

#### Scenario: One host fails for many links

- **GIVEN** 17 links on one host time out in the same run
- **WHEN** the digest is rendered
- **THEN** it shows one triage entry for that host and outcome with the number of links and the affected records, instead of one entry per link

#### Scenario: A section exceeds its limit

- **WHEN** a section has more entries than its limit
- **THEN** the remaining entries appear in a collapsed list in the digest body, and the body stays within GitHub's limit

#### Scenario: A grouped finding is tracked or reviewed

- **WHEN** a maintainer tracks a grouped entry or records a limitation for one of its links
- **THEN** the task or limitation applies to the findings it names, as for single findings

### Requirement: Legacy health issues migrate into the digest

Before the digest replaces per-finding issues, a migration SHALL select every open legacy health issue by its label
and finding marker when it runs. Each issue's finding SHALL appear in the digest, no longer hold, be noise or carry the
maintainer's review in its closing comment; human discussion SHALL be summarised in the digest first. Issues SHALL
close only with an approved comment linking the digest. The per-finding publisher SHALL NOT run beside the digest.

#### Scenario: The issues are listed

- **WHEN** the maintainer lists the issues to migrate
- **THEN** every open `guide-health` issue with the legacy marker is listed with any human comment, and nothing is written

#### Scenario: Issues were opened after the migration was planned

- **GIVEN** the legacy publisher opened further issues after the migration was planned
- **WHEN** the issues are listed
- **THEN** those issues are listed with the rest

#### Scenario: The migration is applied

- **GIVEN** the first digest and an approved closing comment
- **WHEN** the listed issues are closed
- **THEN** each closes as not planned with that comment, and its finding is in the digest, no longer holds, is noise or is reviewed in that comment

### Requirement: The CI catalogue is generated from the workflow definitions

The CI documentation SHALL render each workflow's triggers, permissions, concurrency, artifacts and retention from
the workflow files, joined with a reviewed human entry for purpose, entry point, next actor and rerun route. A check
SHALL fail when a workflow, artifact or permission lacks its human entry or the rendered block is stale.

#### Scenario: A workflow is added without an entry

- **WHEN** a new workflow or uploaded artifact has no human entry
- **THEN** the offline check fails and names it

#### Scenario: A permission changes

- **WHEN** a workflow's permissions change and the catalogue block was not regenerated
- **THEN** the check fails and names the regeneration command

### Requirement: Every automated output ends with a next step

Every automated summary, comment, reply and report SHALL end with who acts next, the exact action, its
prerequisites or fallback and the evidence that shows completion. Successful outcomes SHALL say what review or checks
remain; partial, blocked and failed outcomes SHALL stay distinct and SHALL NOT claim success.

#### Scenario: A contributor receives a failed check

- **WHEN** a required check fails
- **THEN** the summary names the affected item, a local reproduction command and the evidence that confirms the fix

#### Scenario: A repair is applied

- **WHEN** `/fix-duplicates` commits a repair
- **THEN** the reply names the commit and the checks and review that remain

#### Scenario: A privileged route is unavailable

- **WHEN** a repair cannot run because of a fork, missing permission or unknown person
- **THEN** the reply gives the local or manual route and how to resolve the missing prerequisite

#### Scenario: A release product is ready

- **WHEN** CI prepares a release PR, deployment, image or draft release
- **THEN** its output names the exact revision or artifact and the separately authorized step that remains

#### Scenario: A renderer loses its next step

- **WHEN** a planted regression removes the action, fallback or completion evidence from a representative output
- **THEN** the renderer's test fails

### Requirement: A failed run names who acts

A workflow run SHALL fail only when a maintainer must act, and its summary SHALL state what happened, who acts and
the next step. A transient upstream failure that the next scheduled run retries SHALL be reported as a warning and
SHALL NOT fail the run. Information a person needs SHALL appear in a summary, reply or the digest, not only in an
artifact.

#### Scenario: A source cannot be downloaded

- **GIVEN** a scheduled refresh in which one source times out and another is proposed
- **WHEN** the run ends
- **THEN** it succeeds with a warning, its summary lists each source's outcome and links the proposed pull request

#### Scenario: A response is rejected

- **WHEN** validation rejects a source's new response or publication fails
- **THEN** the run fails and its summary names the source, the reason and the maintainer's next step

#### Scenario: A check cannot import what it needs

- **WHEN** a hosted job's checks import a module its setup does not install
- **THEN** an offline test fails before the change is merged and names the missing module

#### Scenario: A release dispatch runs on another branch

- **WHEN** Prepare release or Tag release is dispatched on a branch other than the default branch
- **THEN** the run fails in its first step, names the default branch to dispatch from and creates nothing

### Requirement: Scheduled refresh outcomes reach the digest

The digest SHALL list each source that the latest scheduled refresh did not refresh, with its outcome, date and run
link. When the refresh report cannot be read, the digest SHALL say that the refresh outcome is unknown and name the
run to check, and SHALL NOT present it as success.

#### Scenario: A source was not refreshed

- **GIVEN** the latest scheduled refresh could not retrieve one source
- **WHEN** the next watch publishes the digest
- **THEN** the digest lists that source as not refreshed, with its outcome and the run link

#### Scenario: The refresh report is unavailable

- **WHEN** the publisher cannot read the latest scheduled refresh report
- **THEN** the digest says the refresh outcome is unknown and names the run to check

### Requirement: Production publishes real crawler discovery files

The build SHALL emit a sitemap of only the Guide root and `api/index.html` at the actual production location,
using absolute, fragment-free URLs without invented dates. Crawler policy SHALL respect host-root robots scope;
a subpath file SHALL NOT be treated as origin control. Preview documents SHALL stay outside the sitemap and
remain crawlable with `noindex`. Assembly SHALL preserve verified production bytes.

#### Scenario: Production and preview are assembled

- **WHEN** the built production site is combined with a separately built preview
- **THEN** the sitemap uses the actual production origin/path, production bytes are unchanged, no preview/hash URL is advertised, and preview HTML is crawlable with `noindex`

#### Scenario: The base URL is overridden

- **WHEN** the build receives a different actual publication location before validation and packaging
- **THEN** absolute discovery URLs follow that location without predicting a future domain or patching a verified artifact

#### Scenario: The Guide is hosted below an origin root

- **WHEN** a project-hosted Guide cannot publish the origin-root `robots.txt`
- **THEN** documentation and checks report the effective hosting policy and do not claim that its project-subpath robots file controls crawlers

### Requirement: Release dispatches accept a leading v

Prepare release and Tag release SHALL accept the requested version with or without one leading `v` and
surrounding whitespace, and SHALL use the bare version in every file, branch, tag and message they produce. Any
other malformed value SHALL be refused with the accepted form shown.

#### Scenario: The maintainer types the tag form

- **GIVEN** the maintainer enters `v1.0.0-alpha.4`
- **WHEN** Prepare release runs
- **THEN** it prepares exactly the same files and branch as for `1.0.0-alpha.4`

#### Scenario: A malformed version

- **WHEN** a release dispatch receives `vv1.0.0` or `1.0`
- **THEN** it changes nothing and names the accepted form, for example `1.0.0-alpha.4` or `v1.0.0-alpha.4`

### Requirement: Release versions only increase

Prepare release and Tag release SHALL refuse a version whose precedence is not above every existing release tag,
name the newest tag and write nothing. They SHALL compare versions by SemVer precedence, as deployment does.

#### Scenario: A lower version is requested

- **GIVEN** the release tag `v1.1.0` exists
- **WHEN** the maintainer runs Prepare release or Tag release for `1.0.5`
- **THEN** no branch, pull request or tag is written, and the summary names `v1.1.0` and asks for a higher version

#### Scenario: Prerelease identifiers compare as numbers

- **GIVEN** the newest release tag is `v1.0.0-alpha.9`
- **WHEN** the maintainer prepares `1.0.0-alpha.10`
- **THEN** the version is accepted as newer

### Requirement: Tag release refuses an incomplete release changelog

Tag release SHALL create a tag only when the requested version's changelog section lists every merged pull request
and direct commit between the previous release tag and the commit to be tagged. Otherwise it SHALL create no tag,
name the missing changes and start release preparation for the same version.

#### Scenario: A change lands after the release PR merged

- **GIVEN** the release PR for `1.0.0-alpha.4` merged and one more PR merged afterwards
- **WHEN** the maintainer runs Tag release for `1.0.0-alpha.4`
- **THEN** no tag is created, and the summary names that PR, the completion it started and the next action: review and merge the completion PR, then run Tag release again

#### Scenario: The changelog is complete

- **WHEN** the requested section lists every change since the previous release tag
- **THEN** Tag release continues with its existing checks and creates the tag

### Requirement: Release preparation completes or replaces its own proposal

For an untagged version already on the default branch, Prepare release SHALL open a pull request that adds only
the missing changelog entries. It SHALL replace an open proposal of its own that nobody edited with one prepared
from the current default branch. An edited or closed proposal SHALL stay untouched, and the dispatch SHALL name
how to proceed.

#### Scenario: Completing a merged release

- **GIVEN** `1.0.0-alpha.4` metadata on the default branch, no tag, and one change missing from its changelog
- **WHEN** release preparation runs for that version
- **THEN** a pull request adds exactly that entry, leaving the version, dates and earlier entries unchanged

#### Scenario: Replacing an outdated unedited proposal

- **GIVEN** an open release pull request whose only commit is the automation's preparation, and a default branch that has moved on
- **WHEN** release preparation runs again for the same version
- **THEN** the proposal is prepared again from the current default branch and the pull request keeps its number

#### Scenario: A person edited the proposal

- **GIVEN** an open release pull request with a commit the preparation did not make
- **WHEN** release preparation runs again for the same version
- **THEN** it changes nothing and names the manual reconciliation route

### Requirement: A preview identical to the release says so

When the staging commit equals the commit of the published production release, every `/next/` page SHALL say that
the preview is identical to that release and link the production root, instead of announcing a next release. The
preview SHALL keep `noindex` and its own build identity.

#### Scenario: A release is tagged at the commit staging serves

- **GIVEN** `/next/` serves commit `161994f` and release `v1.0.0-alpha.3` is published from the same commit
- **WHEN** publication assembles both channels
- **THEN** each `/next/` page states in Czech and English that it is identical to `v1.0.0-alpha.3` and links the release, and production bytes stay unchanged

#### Scenario: The default branch moves on

- **WHEN** a later default-branch commit is published to staging
- **THEN** `/next/` again announces the next release

### Requirement: Each channel records when it is live

Publication SHALL record a successful `staging` deployment with the `/next/` address for the commit it published to
staging, and a `production` deployment with the root address for the release it published, each only after that
channel is live. A publication that publishes nothing SHALL record nothing. Release tags SHALL require a successful
`staging` deployment of their commit.

#### Scenario: A merge reaches staging

- **WHEN** publication makes a new default-branch commit live under `/next/`
- **THEN** the `staging` environment shows a successful deployment of that commit with the `/next/` address

#### Scenario: A release goes live

- **WHEN** publication makes an approved release live at the root
- **THEN** the `production` environment shows a successful deployment of that release with the root address, recorded after it went live

#### Scenario: Tagging a commit that never reached staging

- **WHEN** Tag release runs for a commit without a successful `staging` deployment
- **THEN** no tag is created and the summary names the run to wait for

### Requirement: Release notes are prepared in one invocation

A native release-notes skill SHALL, in one invocation, run the delivered release-notes workflow report-only from
the previous release tag, pre-releases included, to the requested tag, compose the body with the verification
record, ask once for approval of that body and apply it to the draft. Publishing the release SHALL remain a
separate maintainer act.

#### Scenario: The previous release is a pre-release

- **GIVEN** only pre-releases exist and `v1.0.0-alpha.3` is the previous tag
- **WHEN** the maintainer prepares the notes for `v1.0.0-alpha.4`
- **THEN** the notes cover exactly `v1.0.0-alpha.3..v1.0.0-alpha.4`

#### Scenario: The maintainer approves the body

- **WHEN** the composed body is approved
- **THEN** the draft carries it with the unchanged verification record, and the skill names publishing as the remaining step

#### Scenario: The maintainer declines

- **WHEN** the composed body is not approved
- **THEN** the draft release is unchanged

#### Scenario: A maintainer selects the Guide release-notes tool

- **WHEN** the maintainer opens the tooling task matrix or release-notes guidance
- **THEN** both lead to the native `fair-guide-release-notes` helper as the preferred Guide route, consistent with the generated inventory

### Requirement: Scheduled maintenance results are ready on Monday morning

Scheduled source refresh, dependency updates and health watch SHALL run in one weekly order in which each completes
by Monday 06:00 UTC, which is 08:00 in Prague or earlier, even when its scheduled start is delayed by six hours. The
monthly Champion remeasurement SHALL run within the first weekly health watch of each month.

#### Scenario: Scheduled starts are delayed

- **GIVEN** each scheduled start is delayed by six hours and each job uses its full timeout
- **WHEN** the schedule is checked offline
- **THEN** every job still completes before Monday 06:00 UTC

#### Scenario: The first week of a month

- **WHEN** the weekly health watch runs within the first seven days of a month
- **THEN** it also remeasures the Champion tests, and no separate monthly schedule exists

### Requirement: Manual health-watch runs select their parts

A manual health-watch run SHALL let the maintainer choose the settings and Project audit, the watch, or both. A run
limited to the audit SHALL open, edit or close no issue and SHALL change no digest. Scheduled runs SHALL run both
parts.

#### Scenario: Checking the audit on demand

- **WHEN** the maintainer runs health watch manually with only the audit selected
- **THEN** the audit runs with its Project token and reports in the run summary, and no issue or digest changes

#### Scenario: A scheduled run

- **WHEN** the weekly schedule starts health watch
- **THEN** both the watch and the audit run

### Requirement: Human documentation is organised by audience and type

Human documentation SHALL give Guide readers, contributors and maintainers one landing page each, and SHALL keep
each document to one type: how-to guide, reference, explanation or tutorial. Each document SHALL declare its type,
and an offline check SHALL fail on a missing or unknown declaration. Agent instructions and delivered or generated
documents are outside this structure.

#### Scenario: A maintainer looks for a task

- **WHEN** a maintainer opens the maintainer landing page
- **THEN** it lists each recurring maintainer task in one line with when it is needed and a link to its runbook

#### Scenario: A document lacks a type

- **WHEN** a human document has no type declaration or an unknown one
- **THEN** the offline check fails and names the document and the accepted types

### Requirement: Maintainer tasks have runbooks

Every recurring maintainer task SHALL have a how-to runbook under `docs/runbooks/` that opens with who
acts, how long it takes and why, followed by numbered steps naming where to act, what to do, the visible evidence of
completion and the next action on failure. A branching flow SHALL include an accessible diagram. One-time migration
procedures and issue-specific payloads SHALL live with their change, retaining evidence and approval gates.

#### Scenario: A step lacks its failure route

- **WHEN** a runbook step has no "If it fails" action
- **THEN** the offline check fails and names the runbook and the step

#### Scenario: Releasing from the runbook

- **GIVEN** the release runbook
- **WHEN** a maintainer follows it
- **THEN** each step names the exact place, the inputs and the visible evidence, and the Tag release refusal has a named next action

#### Scenario: A one-time migration is handed off

- **WHEN** legacy issues are migrated under a change-specific approval
- **THEN** the complete reviewed procedure and issue mapping live with that change, every observation and human discussion is retained, and recurring digest handling stays in its durable runbook

### Requirement: Documentation changes pass an independent review

Documentation SHALL pass structure/facts checks and an independent audience review. Moved text SHALL have a
complete section map. Long documents included in a full review SHALL receive section-by-section claim verification
against implementation, sources or current policy; sampled usability review SHALL NOT count as that verification.
A hand-off SHALL remain incomplete while its procedure has unresolved findings. Historical receipts SHALL retain their scope.

#### Scenario: A section disappears in a reshape

- **WHEN** a former section has no entry in the section map
- **THEN** the map check fails and names the section

#### Scenario: A document names a missing script

- **WHEN** a document refers to a repository path, script or workflow that does not exist
- **THEN** the facts check fails and names the reference

#### Scenario: The independent reader had to guess

- **WHEN** the reviewing agent reports a step it could not perform from the text alone
- **THEN** the documentation is fixed before the dependent hand-off is ticked

#### Scenario: An existing long document was only sampled

- **GIVEN** an earlier audience review sampled facts in a long design or content-model document
- **WHEN** complete factual verification is required
- **THEN** every section's claims receive located evidence or an owned disposition, and the sampled receipt is not presented as full verification

### Requirement: Issue threads can initiate source refresh

An authorized repository writer SHALL be able to request `/refresh <source>` from an ordinary issue or PR.
Eligibility, workflow selection, help and replies SHALL agree. Exact source keys, trusted default-branch code,
the shared queue and guarded branch replacement SHALL remain enforced. `/fix-duplicates` SHALL retain its
same-repository open-PR guards.

#### Scenario: A refresh starts before its proposal exists

- **GIVEN** a repository issue with no refresh PR and a caller with current write access
- **WHEN** the caller requests a reviewed source key
- **THEN** the trusted workflow creates or safely updates a refresh proposal and replies in the initiating issue with the result and proposal link

#### Scenario: An issue requests duplicate repair or an invalid refresh

- **WHEN** an issue comment requests `/fix-duplicates`, an unknown source or refresh without current write access
- **THEN** no repair or refresh mutation runs and help/refusal describes the actual eligibility

### Requirement: Publication addresses are resolved before verification

Absolute navigation/discovery metadata SHALL use the actual deployment location before validation and packaging.
Guide vocabulary/profile IRIs SHALL come from the reviewed namespace setting, never from the deployment location,
the live site or a release archive. Offline inputs SHALL be deterministic without network discovery or a guessed
future host. Publication SHALL preserve verified bytes and distinct channel links.

#### Scenario: Pages provides the deployed origin and path

- **WHEN** Pages configuration resolves the actual publication URL
- **THEN** navigation/discovery metadata uses that location before validation, semantic references use the reviewed namespace setting, and assembly preserves the resulting verified production bytes

#### Scenario: The same verified release is assembled with a preview

- **WHEN** publication combines an immutable production release with the preview channel
- **THEN** preview navigation uses its channel path without replacing production metadata or silently migrating content identities

### Requirement: Channels may differ in namespace until the next release

A preview whose reviewed namespace differs from published production's SHALL be published, and the deployment
summary SHALL state both namespaces and that the next release aligns them. Production SHALL change namespace only
through a release. Build evidence and reuse checks SHALL bind the namespace, profile and publication root. Existing
release bytes SHALL NOT be rewritten.

#### Scenario: The namespace setting changed before a release

- **GIVEN** published production still uses the legacy namespace
- **WHEN** a preview built with the new reviewed namespace is deployed
- **THEN** it is published beside unchanged production, and the deployment summary names both namespaces and the release that aligns them

#### Scenario: A release aligns the channels

- **WHEN** the next release is approved and published
- **THEN** production uses the reviewed namespace, and earlier archives keep their bytes and original contexts

#### Scenario: Sites were built for different publication roots

- **WHEN** production and preview were built for different publication roots
- **THEN** assembly refuses them and the summary names the deployment to rerun

#### Scenario: The Pages root changed after the sites were built

- **WHEN** the actual Pages root differs from the root stamped in the staging site being published
- **THEN** publication deploys nothing and its summary names the deployment to rerun

#### Scenario: Artifact declarations disagree with verified contents

- **WHEN** a recorded semantic identity disagrees with its crate/context/profile or required values cannot be established
- **THEN** publication and cross-namespace reuse are refused; an unstamped historical artifact is read from its verified contents rather than guessed from current configuration

#### Scenario: A result was checked for another namespace or publication root

- **WHEN** deployment compares a prior check result with a candidate using different semantic or publication inputs
- **THEN** the result is not reused and the candidate requires the full applicable checks

### Requirement: Durable documentation states current contracts

Durable documentation SHALL describe current contracts and stable procedures, excluding rollout narration,
change-task dependencies and completed follow-up instructions. Legitimate dated observations and conditional
instructions SHALL retain their context. References SHALL name and link the intended resource; an organization
Project SHALL use its explicit Project URL rather than an ambiguous conversation-style number.

#### Scenario: A migration finishes or a planned gate becomes active

- **WHEN** documentation is reconciled after implementation
- **THEN** durable instructions describe the resulting behavior, while change-specific history remains in its change record

#### Scenario: A dated measurement is still evidence

- **WHEN** contextual stale-prose checks encounter a dated measurement or a stable conditional recovery step
- **THEN** those valid statements remain, while a planted in-flight task reference is reported

### Requirement: Review procedures use the delivered review workflow

The review runbook SHALL recommend delivered `aiscr-review-pr`, explain local and PR scope/base selection,
finding disposition, fixes and re-review, and retain exact approval before posting externally. Local reviews SHALL
not post. Human review and merge decisions SHALL remain required. Guide documentation SHALL link the delivered
workflow instead of copying or modifying it.

#### Scenario: A contributor reviews staged work

- **WHEN** the contributor follows the runbook's local-review route
- **THEN** the selected local diff and baseline are explicit, findings are handled locally, and no PR comment is posted

#### Scenario: A PR review is ready to post

- **WHEN** findings and their dispositions have been prepared for a PR
- **THEN** the exact grouped posting payload awaits the delivered workflow's approval, and subsequent human approval/merge remains separate

### Requirement: AI contribution guidance remains generic and accountable

Both language introductions SHALL welcome AI-assisted contributions under human oversight and responsibility and
state that the repository supports such work. They SHALL refer to content paradata for actual instruments and
sources rather than freeze a vendor/model inventory. Operational usage logging SHALL remain separate.

#### Scenario: A contributor uses another AI instrument

- **WHEN** the instrument is truthfully recorded in the applicable provenance or usage record
- **THEN** the generic Czech and English contribution statements remain accurate without an inventory edit

### Requirement: Documentation diagrams describe executable workflows

Review, merge/publication, refresh and digest documentation SHALL use Mermaid diagrams where they aid orientation,
with accessible titles/descriptions and equivalent adjacent prose. Diagram transitions SHALL match actual workflow
dependencies, approvals, publication, refusal and retry routes. Successful rendering SHALL NOT alone establish
semantic correctness.

#### Scenario: A diagram skips a publication dependency

- **WHEN** a planted arrow leads directly from preparation to an outcome that requires publication
- **THEN** verification rejects that transition even if the diagram renders, whatever Mermaid link form the arrow uses

### Requirement: Applied release protections remain intact until a reviewed choice

The settings declaration and audit SHALL represent reviewed tag deployment and status-check gates. Existing live
protections SHALL NOT be removed to satisfy an obsolete planned target. Any replacement SHALL follow an explicit
maintainer choice and approval of its exact diff. Release acceptance SHALL prove successful staging and required
checks on the tagged commit before tag creation.

#### Scenario: Live protection is stronger than the older target

- **GIVEN** live tag protection requires two deployment environments and the Actions `checks` status
- **WHEN** the previous declaration names only one deployment
- **THEN** both live deployment gates remain until the retained target is chosen, and declaration/fixture repair does not silently remove a gate

#### Scenario: Staging or checks are missing on the release commit

- **WHEN** a release attempts tag creation through the queue or administrator fallback
- **THEN** missing successful staging or required checks prevent tag creation and name the unmet prerequisite

### Requirement: Queue tuning distinguishes build and merge controls

Queue documentation SHALL distinguish merge-group build concurrency from minimum/maximum merge-batch size and
batching wait. Tuning SHALL use observed waiting, runner demand and unchanged check coverage, followed by an explicit
maintainer choice. A suggested value SHALL NOT become an approved target, and a larger merge batch SHALL NOT be
described as combining CI builds.

#### Scenario: A larger merge batch is proposed

- **WHEN** a maintainer evaluates queue tuning
- **THEN** the evidence treats build and merge controls independently, existing values remain until a choice, and any hosted mutation requires its approved exact diff
