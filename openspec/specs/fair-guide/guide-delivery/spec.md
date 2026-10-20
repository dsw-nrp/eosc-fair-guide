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

`.agents/guide/surfaces.toml` SHALL classify owned, generated, delivered, tool-generated and mixed surfaces,
including guide-owned `.agents/reports/usage/` and `.agents/config/review_config.toml`. `check_all` SHALL run
native generation, ownership and delivery-integrity checks, failing on unclassified paths or missing, modified
or extra delivered content. Native generation SHALL preserve delivered Codex sections and the supplied preamble;
redelivery SHALL preserve native sections.

#### Scenario: A delivered rule is modified locally

- **GIVEN** the manifest records a delivered rule or Codex section
- **WHEN** it is modified and `check_all` runs
- **THEN** delivery integrity fails while ignoring separately declared owned and tool-generated paths

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

CI workflows for pull requests SHALL use the `pull_request` trigger only, SHALL run with read-only repository
permissions, SHALL pin third-party actions by commit SHA, and SHALL use no secrets. Dependency and action
updates SHALL be proposed automatically.

#### Scenario: Pull request from a fork

- **GIVEN** a pull request from a fork
- **WHEN** its checks run
- **THEN** they have read-only access and no secrets are available

### Requirement: Humans judge correctness and tone

Code owners SHALL identify actual available maintainers for text, design, the content model and CI. Passing
checks SHALL NOT replace human review of correctness and tone. For the initial sole-maintainer alpha,
PR delivery, required checks and explicit maintainer acceptance SHALL be the enforceable gate. Mandatory
content-owner approval SHALL be enabled when a reviewer able to approve the author's PR is available.

#### Scenario: Text change

- **GIVEN** a pull request that only changes advice text
- **WHEN** all checks pass
- **THEN** the available human-review gate remains required, and the alpha release candidate requires explicit maintainer acceptance

### Requirement: Scheduled jobs never commit directly

Scheduled jobs SHALL deliver snapshot refreshes as pull requests, and SHALL report link, status, live-service
and test-health problems as issues. They SHALL also watch the EOSC CZ pages the guide depends on (the outputs
page, the service catalogue, the training pages, the Open Science III FAQ, the minizáměry calls, the
acknowledgement page and the data steward pages) and open an issue when an item is added or updated. They SHALL
NOT commit to the default branch.

#### Scenario: Broken external link found

- **GIVEN** the weekly link check finds a broken external link
- **WHEN** it completes
- **THEN** it opens or updates an issue that lists the link and where it is used

#### Scenario: New EOSC CZ output

- **GIVEN** the EOSC CZ outputs page lists a document that was not there at the previous run
- **WHEN** the watch job runs
- **THEN** it opens an issue that names the document, its anchor and its publication date

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

Health reporting SHALL separate content integrity, snapshot age, source availability and test verdicts.
Published observations SHALL have meaningful dashboard and API consumers for their dates, revision, scope and
status. Persistent failures and relevant source changes SHALL update issues by stable keys without duplicates
or transient-failure floods. A service failure SHALL NOT become a failed FAIR requirement. Live monitoring
SHALL remain separate from mandatory deterministic PR checks.

#### Scenario: A test returns an indeterminate verdict

- **GIVEN** a completed live test with an indeterminate native result
- **WHEN** health is summarized
- **THEN** it is distinguishable from transport failure, a negative criterion result and a positive answer suggestion

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

Each release SHALL publish a container image that serves that release's verified site artifact unchanged, assembled
from the digest-checked artifact rather than rebuilt from source. It SHALL be published to the GitHub container
registry and carry the release tag, a moving `latest` on every release and a moving `stable` on every non-prerelease.

#### Scenario: Running a published release in a container

- **GIVEN** a reader with a container runtime
- **WHEN** they run the image for a release tag
- **THEN** the guide is served locally and its footer shows the same version and commit as the release

#### Scenario: A prerelease is tagged

- **GIVEN** a prerelease tag such as `v1.0.0-alpha.1`
- **WHEN** its image is published
- **THEN** `latest` moves to it, `stable` does not, and the image carries that release's tag

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

Dependabot SHALL group patch-version updates for all dependencies within each configured ecosystem:
GitHub Actions, npm, pip and Docker. Minor and major updates SHALL remain eligible for individual PRs.
Grouping SHALL preserve the configured directories, weekly schedules and open-version-PR limits.

#### Scenario: Several patch updates are available

- **GIVEN** several dependencies in one configured ecosystem have patch-version updates
- **WHEN** Dependabot proposes scheduled version updates
- **THEN** those patch updates are eligible for one grouped PR for that ecosystem regardless of dependency name

#### Scenario: Minor and major versions are available

- **GIVEN** patch, minor and major updates are available for dependencies in a configured ecosystem
- **WHEN** Dependabot applies the grouping policy
- **THEN** only patch versions enter the group and minor and major updates remain eligible for individual PRs

#### Scenario: Existing update settings are retained

- **GIVEN** the four configured ecosystems, their current directories, weekly schedules and limit of 30 open version PRs
- **WHEN** patch grouping is configured
- **THEN** each ecosystem retains those settings and the existing security-update policy
