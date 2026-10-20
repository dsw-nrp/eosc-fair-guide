# Spec Delta

## MODIFIED Requirements

### Requirement: Native ownership and delivered integrity are checked

`.agents/guide/surfaces.toml` SHALL classify owned, generated, delivered, tool-generated, runtime and mixed surfaces, including guide-owned `.agents/reports/usage/`, `.agents/config/review_config.toml` and the repository's runtime scratch area. `check_all` SHALL run native generation, ownership and delivery-integrity checks, failing on unclassified paths or missing, modified or extra delivered content. Native generation SHALL preserve delivered Codex sections and the supplied preamble; redelivery SHALL preserve native sections.

#### Scenario: A delivered rule is modified locally

- **GIVEN** the manifest records a delivered rule or Codex section
- **WHEN** it is modified and `check_all` runs
- **THEN** delivery integrity fails while ignoring separately declared owned and tool-generated paths

#### Scenario: A runtime hand-off is present

- **GIVEN** a tracked or untracked file under the declared runtime scratch area
- **WHEN** the ownership and delivery-integrity checks run
- **THEN** the file is classified as runtime and neither fails classification nor counts as delivered content

### Requirement: No local or planning-environment details

Files and commit messages in the tool repository SHALL NOT contain local machine paths, user-specific setup, or references to private planning systems. A hygiene check SHALL scan the repository's text files for machine-specific path patterns, hub-internal names and unapproved unpublished working material, and SHALL NOT refuse the repository's own runtime scratch convention written as a repository-relative path. The approved model's in-preparation citation SHALL remain subject to these local-path and private-material restrictions.

#### Scenario: Local path in a document

- **GIVEN** a pull request that adds a Windows path from a maintainer's machine to a document
- **WHEN** the hygiene check runs
- **THEN** it fails and names the file and line

#### Scenario: Delivered tooling documents the runtime scratch layout

- **GIVEN** a delivered library or skill that names the repository-relative scratch path
- **WHEN** the hygiene check runs
- **THEN** it reports nothing, while an absolute machine-specific path to that layout still fails and names the file and line
