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
