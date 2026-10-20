# Design

## Context

See [proposal.md](proposal.md). `.github/dependabot.yml` has one entry each for GitHub Actions, npm, pip and
Docker. The maintainer has already raised each open-PR limit to 30; preserve that edit and the staged release work.

## Goals / Non-Goals

Group patch updates without restricting which dependency names can receive them. Keep this configuration-only
change separate from the release change and from package installation troubleshooting.

## Decisions

Use an explicit `patch-updates` group in every ecosystem entry, with `applies-to: version-updates`,
`patterns: ["*"]` and `update-types: ["patch"]`. This includes every dependency type and leaves nonmatching
minor and major versions eligible for separate PRs. Group within each ecosystem; no cross-ecosystem bundle
or security-update grouping is requested. The definitions follow the
[GitHub Dependabot groups reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#groups).

Keep the existing directories, weekly schedules and limits verbatim. Add no dependency, workflow, runtime or
user-interface change. Validate parsed YAML and existing workflow tests; no new test framework is needed.

## Risks / Trade-offs

- A wildcard without the patch filter could combine broader updates: inspect both properties in all four entries.
- Local checks cannot demonstrate hosted PR creation: report the configuration as locally validated and inspect
  the next scheduled Dependabot run after delivery.

## Migration Plan

Apply the four group blocks in the current topic checkout. Validate workflow contracts, strict OpenSpec and the
full native check suite, then update this change's usage entry. Delivery and archive remain separate actions.
To roll back, remove only the four group blocks, preserving the maintainer's other update settings.
