# Spec Delta

## ADDED Requirements

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
