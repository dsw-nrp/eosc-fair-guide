# Spec Delta

## MODIFIED Requirements

### Requirement: The REST API publishes the health snapshot

The static REST API SHALL expose the same health result through a documented endpoint linked from API metadata,
described under its own operations tag apart from the content kinds and never listed as content. Initial builds SHALL
report no completed check run; a successful fresh build and run SHALL publish actual outcomes. A failed build SHALL
NOT overwrite an earlier site's health result.

#### Scenario: Checks complete after a fresh build

- **GIVEN** a fresh site whose health snapshot has no completed check run
- **WHEN** the check runner finishes
- **THEN** the REST endpoint publishes the same dated outcomes as the dashboard, including any failed or unrun jobs

#### Scenario: A later build fails

- **GIVEN** an earlier site with a published health snapshot
- **WHEN** the next build fails
- **THEN** its failure report remains available as a CI artifact and the earlier site's health endpoint is not overwritten

#### Scenario: A consumer lists the content kinds

- **WHEN** a consumer reads the API metadata and the OpenAPI tags
- **THEN** the content kinds and the health endpoint are listed apart, and no content list contains health evidence

### Requirement: Production publishes real crawler discovery files

The build SHALL emit a sitemap of only the Guide root, `api/index.html` and every record's landing page at the
actual production location, using absolute, fragment-free URLs without invented dates. Crawler policy SHALL respect
host-root robots scope; a subpath file SHALL NOT be treated as origin control. Preview documents SHALL stay outside
the sitemap and remain crawlable with `noindex`. Assembly SHALL preserve verified production bytes.

#### Scenario: Production and preview are assembled

- **WHEN** the built production site is combined with a separately built preview
- **THEN** the sitemap uses the actual production origin/path and lists every record's landing page, production bytes are unchanged, no preview/hash URL is advertised, and preview HTML is crawlable with `noindex`

#### Scenario: The base URL is overridden

- **WHEN** the build receives a different actual publication location before validation and packaging
- **THEN** absolute discovery URLs follow that location without predicting a future domain or patching a verified artifact

#### Scenario: The Guide is hosted below an origin root

- **WHEN** a project-hosted Guide cannot publish the origin-root `robots.txt`
- **THEN** documentation and checks report the effective hosting policy and do not claim that its project-subpath robots file controls crawlers

## ADDED Requirements

### Requirement: The w3id redirect is maintained and watched

The Guide's w3id registration SHALL name at least two maintainers. A change to its redirect SHALL be made only through
a pull request to the registry, after a maintainer approves its exact content. The health watch SHALL probe the terms,
the profile and record IRIs as JSON and HTML, and report a failure in the maintenance digest once by stable key. A
runbook SHALL cover updating it.

#### Scenario: Someone else's change breaks the redirect

- **GIVEN** a published Guide whose record IRIs redirect correctly
- **WHEN** the weekly health watch finds that a record IRI no longer reaches its record
- **THEN** the digest reports the failing IRI and the redirect once, and links the runbook

#### Scenario: The Guide moves to a new host

- **GIVEN** an agreed new host for the Guide
- **WHEN** a maintainer follows the runbook
- **THEN** they prepare the redirect change, approve its exact content, submit it to the registry, and confirm with the probe that every probed IRI reaches the new host

### Requirement: A namespace switch is released only with a registered redirect

The release that first publishes production under a new namespace SHALL be prepared only after the registry has
merged the redirect that serves it. Once that release is published, the w3id probe SHALL confirm that the terms, the
profile and a record IRI resolve as JSON and HTML to it, and a failure SHALL be reported in the maintenance digest.

#### Scenario: The redirect is not merged yet

- **GIVEN** a preview built with the w3id namespace while the registry pull request is still open
- **WHEN** a maintainer prepares the next release
- **THEN** the release does not switch production to the new namespace, and its notes say what it waits for

#### Scenario: The release that switches

- **GIVEN** a registered redirect pointing at production
- **WHEN** the release that adopts the namespace is published and the probe runs
- **THEN** the probed terms, profile and record IRIs resolve to that release, or the digest reports the IRI that does not

### Requirement: Verified release artifacts remain reusable across schema transitions

Deployment and image tooling SHALL accept verified current and documented predecessor layouts without rewriting
verified bytes or requiring compatibility API documents. Both status-bearing nodes SHALL use only the status property
of the selected layout, with no per-node fallback. Missing, mixed, split or ambiguous layouts SHALL be rejected before
replacing output.

#### Scenario: Previous production beside a new preview

- **GIVEN** a verified predecessor archive with `api/health.json`, `creativeWorkStatus` and no generated 404
- **WHEN** it is assembled beside a preview built under API v1
- **THEN** assembly accepts the archive, preserves every production byte and publishes the preview without requiring
  the predecessor to gain new paths or pages

#### Scenario: An image retry uses the previous schema

- **GIVEN** that same verified predecessor archive selected for an image retry
- **WHEN** the candidate image is prepared and its health is verified
- **THEN** preparation reads the predecessor release status and the probe uses `api/health.json`, without rebuilding or
  rewriting the archive

#### Scenario: An ambiguous artifact is rejected

- **GIVEN** an archive carrying both health layouts, or neither recognized layout
- **WHEN** assembly or image preparation validates it
- **THEN** validation fails with the layout named and no output is replaced

#### Scenario: Mixed status generations are rejected

- **GIVEN** current health with only predecessor status properties, predecessor health with current status properties,
  or current and predecessor status properties split between `./` and `#guide-software`
- **WHEN** assembly or image preparation validates the archive
- **THEN** it rejects the mixed or split layout before replacing any managed output

### Requirement: Production identity derives from one crate decoding

Status validation, declaration verification and active publication identity SHALL consume one shared decoding of the
production crate rather than independently reparsing it. Verified bytes SHALL remain unchanged.

#### Scenario: Assembly reuses the production-crate identity

- **GIVEN** a verified current or predecessor archive whose statuses and declaration share its crate
- **WHEN** assembly validates the archive and compares its publication identity with the preview
- **THEN** those derivations share one crate decoding and production bytes remain unchanged

### Requirement: Release health responses bypass intermediary caches

Every health path supported for release images SHALL return `Cache-Control: no-store`. The candidate-image probe SHALL
verify that header together with the served identity.

#### Scenario: Both health layouts bypass intermediary caches

- **GIVEN** a current or documented predecessor artifact prepared into a candidate image
- **WHEN** its selected health path is requested through the container
- **THEN** the response carries `Cache-Control: no-store` and the probe verifies that header as well as the JSON identity
