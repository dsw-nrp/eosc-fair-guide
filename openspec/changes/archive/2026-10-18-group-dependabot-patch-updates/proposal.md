# Proposal

## Why

The maintainer wants patch dependency updates reviewed together instead of as one pull request per dependency.
The current Dependabot configuration monitors four ecosystems but defines no update groups.

## What Changes

- Group patch-version updates for every dependency within each of GitHub Actions, npm, pip and Docker.
- Keep minor and major updates eligible for individual pull requests.
- Preserve the existing directories, weekly schedules and maintainer-selected limit of 30 open version PRs.
- Leave security-update policy, dependency versions, release behavior and application content unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-delivery`: define patch-only grouping for scheduled dependency update proposals.

## Impact

Implementation changes `.github/dependabot.yml` and records this change's usage. No runtime, API, content or
dependency version changes are needed. Use the existing topic checkout and preserve its staged release fixes.
Validate the parsed grouping rules and existing workflow tests, strict OpenSpec and native close-out.
Actual grouped pull-request creation can be observed only after delivery and a hosted Dependabot run.
