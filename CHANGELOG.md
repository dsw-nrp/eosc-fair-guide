# Changelog

All notable changes to this guide are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). A release updates the version and date here, in
`CITATION.cff` and in the crate's publication metadata together.

## [Unreleased]

### Added

- Exact duplicate-link suggestions in check artifacts and trusted PR comments, with an explicit local
  `--fix` and maintainer `/fix-duplicates` command that records provenance, registers its ID and guards the PR head;
  repaired refresh pull requests remain protected for manual reconciliation.
- A changelog check in local and pull-request runs: exactly one `[Unreleased]` section with real entries,
  unchanged published releases and complete release transitions (`docs/changelog.md` explains the policy).
- `/help` on any pull request lists the comment commands that apply there and whether you may use them, and a
  mistyped command gets a "did you mean" answer.

### Changed

- All comment commands run through one workflow. An accepted command is acknowledged at once, waits its turn
  behind an earlier run for the same resource and ends with a reaction or a reply naming its run.
- Local `check_duplicates.py --fix` now writes the provenance action and its identifier registration along with
  the safe links, for the reviewed person matched from `git config user.name` or named with `--person`. Without a
  reviewed person it changes nothing.

### Fixed

- Release preparation keeps the curated `[Unreleased]` notes in the new release ahead of the generated list of
  merged pull requests and direct commits, instead of discarding them.
- A missing or invalid CI lane no longer hides failures that the other lanes reported; both are shown, and the
  check still fails.
- An ordinary comment can no longer cancel a waiting `/refresh` or `/fix-duplicates` command.
- Include the dated re3data snapshot from PR #82 and link the NRP Data Catch-all Repository to
  `r3d100014970`, keeping its curated resource and imported record as one repository entity.
- Report every failed or incomplete required check with bounded diagnostics, retain lane logs and details,
  and publish suggestions only from validated evidence without allowing optional output errors to hide failures.
- Refuse competing duplicate owners and invalid link placements, replace local repair files atomically with
  rollback on handled failures, preserve existing TOML keys, and reserve active and retired identifiers during refresh.
- Keep authored Markdown inert in bot reasons and repair diffs, retain commit references within comment bounds,
  and explain uncertain branch state after a command failure. PR heads remain distinct from checked merge revisions.
- Replace a refresh branch only through an atomic comparison with the head whose commits were inspected, and create
  an absent one only while it stays absent, so a branch that moves or appears mid-run keeps its newer head.
- Fail a partial check in the local `check_all.py` job row and exit code as the aggregate does, while a deliberate
  `--only` subset whose selected checks complete stays partial and exits zero.
- Classify the runtime scratch area as a runtime path and narrow the scratch hygiene rule to machine-specific
  locations, so delivered tooling that documents the repository's own layout no longer fails every pull request.
- Refresh the tooling inventory from the delivery manifest and re-verify the merged `datarepo` link, so the
  generation and content checks pass after integrating the default branch.

## [1.0.0-alpha.2] - 2026-10-19

Since v1.0.0-alpha.1.

### Merged pull requests

- Archive initial OpenSpec change ([#67](https://github.com/dsw-nrp/eosc-fair-guide/pull/67))
- Allow direct-main releases and maintain Zenodo metadata ([#68](https://github.com/dsw-nrp/eosc-fair-guide/pull/68))
- chore\(deps\): Bump actions/upload-artifact from 4.6.2 to 7.0.2 ([#78](https://github.com/dsw-nrp/eosc-fair-guide/pull/78))
- chore\(deps\): Bump actions/github-script from 7.1.0 to 9.0.0 ([#77](https://github.com/dsw-nrp/eosc-fair-guide/pull/77))
- chore\(deps\): Bump actions/checkout from 4.3.1 to 7.0.1 ([#76](https://github.com/dsw-nrp/eosc-fair-guide/pull/76))
- chore\(deps\): Bump actions/create-github-app-token from 3.2.0 to 3.3.0 ([#75](https://github.com/dsw-nrp/eosc-fair-guide/pull/75))
- chore\(deps\): Bump actions/download-artifact from 4.3.0 to 8.0.2 ([#74](https://github.com/dsw-nrp/eosc-fair-guide/pull/74))
- chore\(deps\): Bump actions/setup-node from 4.4.0 to 7.1.0 ([#73](https://github.com/dsw-nrp/eosc-fair-guide/pull/73))
- chore\(deps-dev\): Bump @axe-core/playwright from 4.13.0 to 4.14.0 ([#72](https://github.com/dsw-nrp/eosc-fair-guide/pull/72))
- chore\(deps-dev\): Bump swagger-ui-dist from 5.33.2 to 5.33.3 in the patch-updates group ([#71](https://github.com/dsw-nrp/eosc-fair-guide/pull/71))
- chore\(deps-dev\): Bump ruff from 0.17.0 to 0.17.1 in the patch-updates group ([#69](https://github.com/dsw-nrp/eosc-fair-guide/pull/69))

### Direct commits

- fix: keep the release context repository-aware ([6d15974](https://github.com/dsw-nrp/eosc-fair-guide/commit/6d15974f1215103e5140c7957277e58ab60bbc50))
- Fix licence in CITATION file ([ceb5f79](https://github.com/dsw-nrp/eosc-fair-guide/commit/ceb5f79008a26a86dd1bc150d226b7b45bb91c2b))

## [1.0.0-alpha.1] - 2026-10-18

### Merged pull requests

Since the beginning of the repository.

- v1.0.0-alpha.1 ([#1](https://github.com/dsw-nrp/eosc-fair-guide/pull/1))
- chore\(deps\): Bump github/codeql-action/upload-sarif from 4.35.0 to 4.39.0 ([#54](https://github.com/dsw-nrp/eosc-fair-guide/pull/54))
- chore\(deps-dev\): Bump swagger-ui-dist from 5.33.0 to 5.33.2 ([#53](https://github.com/dsw-nrp/eosc-fair-guide/pull/53))
- chore\(deps-dev\): Bump mermaid from 11.16.1 to 12.2.0 ([#52](https://github.com/dsw-nrp/eosc-fair-guide/pull/52))
- chore\(deps\): Bump actions/attest-build-provenance from 8beda2b7ed98355c0e97c0a63bec38ae472e66c4 to 4d101475d8b20a2381f78447822ac1eab6504dd8 ([#51](https://github.com/dsw-nrp/eosc-fair-guide/pull/51))
- chore\(deps\): Bump actions/setup-python from 5.6.0 to 7.0.0 ([#49](https://github.com/dsw-nrp/eosc-fair-guide/pull/49))
- chore\(deps-dev\): Bump @fission-ai/openspec from 1.14.1 to 1.14.2 ([#48](https://github.com/dsw-nrp/eosc-fair-guide/pull/48))
- chore\(deps\): Bump actions/cache/save from 4.3.0 to 6.1.0 ([#47](https://github.com/dsw-nrp/eosc-fair-guide/pull/47))
- chore\(deps-dev\): Bump ruff from 0.16.6 to 0.17.0 ([#46](https://github.com/dsw-nrp/eosc-fair-guide/pull/46))
- chore\(deps\): Bump actions/cache/restore from 4.3.0 to 6.1.0 ([#45](https://github.com/dsw-nrp/eosc-fair-guide/pull/45))
- chore\(deps\): Bump nginxinc/nginx-unprivileged from \`826d597\` to \`378d0c3\` in /docker ([#44](https://github.com/dsw-nrp/eosc-fair-guide/pull/44))
- chore\(deps-dev\): Bump playwright from 1.63.0 to 1.64.1 ([#50](https://github.com/dsw-nrp/eosc-fair-guide/pull/50))
- Refresh the re3data snapshot ([#56](https://github.com/dsw-nrp/eosc-fair-guide/pull/56))
- Refresh the fip-dashboard snapshot ([#57](https://github.com/dsw-nrp/eosc-fair-guide/pull/57))
- Refresh the knav-tools snapshot ([#58](https://github.com/dsw-nrp/eosc-fair-guide/pull/58))
- Refresh the heslar snapshot ([#55](https://github.com/dsw-nrp/eosc-fair-guide/pull/55))

