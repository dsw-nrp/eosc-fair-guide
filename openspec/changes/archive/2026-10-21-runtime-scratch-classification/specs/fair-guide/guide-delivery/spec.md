# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Native ownership and delivered integrity are checked

`.agents/guide/surfaces.toml` SHALL classify owned, generated, delivered, tool-generated, runtime and mixed surfaces, including guide-owned `.agents/reports/usage/` and `.agents/config/review_config.toml`. `check_all` SHALL run native generation, ownership and delivery-integrity checks, failing on unclassified paths or missing, modified or extra delivered content. Native generation SHALL preserve delivered Codex sections and the supplied preamble; redelivery SHALL preserve native sections.

#### Scenario: A delivered rule is modified locally

- **GIVEN** the manifest records a delivered rule or Codex section
- **WHEN** it is modified and `check_all` runs
- **THEN** delivery integrity fails while ignoring separately declared owned and tool-generated paths
