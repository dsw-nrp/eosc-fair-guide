# Guide delivery

## Purpose

The FAIR Guide delivery capability and its observable acceptance contract.

## Requirements

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

`AGENTS.md` SHALL be the single agent guide. `CLAUDE.md` and the GitHub Copilot instructions SHALL only point
to it. One editing skill SHALL exist in `.agents/skills/`, with an identical copy in `.claude/skills/`. The
skill SHALL cover:

- first, whether work needs an OpenSpec change;
- the content model and how to add or change advice, checks and resources;
- the tone and accessibility rules;
- the paradata obligation;
- the validation commands and release steps.

#### Scenario: Skill copies drift

- **GIVEN** a pull request that changes only one of the two skill copies
- **WHEN** the hygiene check runs
- **THEN** it fails and names both paths

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
behaviour-neutral dependency updates and source data refreshes proceed without one.

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

A release SHALL keep the Guide, `CITATION.cff`, npm manifest and lockfile, `pyproject.toml`, crate metadata and
release tag consistent. One script SHALL own the version and the release dates in all of them; prose SHALL NOT
restate the version. The first official prerelease tag SHALL be `v1.0.0-alpha.1`. Each release SHALL attach the
verified built site from its source commit as an asset; deployment SHALL publish that same checked artifact
without rebuilding away its recorded health outcomes.

#### Scenario: Version mismatch

- **GIVEN** a release pull request in which `CITATION.cff` and the crate carry different versions
- **WHEN** the hygiene check runs
- **THEN** it fails and names the mismatching files

### Requirement: Releases are prepared and tagged by dispatch

A prepare-release dispatch SHALL write the version, the dates and a changelog of the pull requests merged since the
last tag into a release pull request; one release MAY collect many pull requests. The tag SHALL be created only by
a separate dispatch after the release pull request is merged, never automatically.

#### Scenario: Preparing a release from several merged pull requests

- **GIVEN** three pull requests merged since the last tag
- **WHEN** the maintainer runs the prepare-release dispatch for `1.0.0-alpha.2`
- **THEN** a release pull request sets that version and today's release date in every owning file and lists the three pull requests in the changelog, and no tag exists until the maintainer runs the tag dispatch after merging it

### Requirement: First official prerelease is the software example baseline

The app's software-practice worked example SHALL assess the first official prerelease. Development-stage
preparation SHALL be distinguished from published release evidence. Public preservation identifiers and
OpenSSF badges SHALL be stated only when actually issued. Remaining preparation steps SHALL be recorded
with their evidence in maintainer documentation. Public pages SHALL explain stable practices without
temporary development or future-assessment commentary.

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
