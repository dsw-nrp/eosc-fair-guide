# Changelog

All notable changes to this guide are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). A release updates the version and date here, in
`CITATION.cff` and in the crate's publication metadata together.

## [Unreleased]

### Changed

- Breaking: maintenance observations move to one **Maintenance digest**; follow it instead of the per-finding `guide-health` issues.
- Breaking: the Guide's own term and RO-Crate profile IRIs move from `https://fair.eosc.cz/` to the reviewed
  `namespace` in `content/guide.toml`, now `https://dsw-nrp.github.io/eosc-fair-guide/terms#` and `…/profile/0.1`.
  The preview carries them from this change, production from the next release. Record IDs and external IRIs are
  unchanged and earlier archives keep their IRIs; read each artifact's own context and profile.

## [1.0.0-alpha.3] - 2026-10-25

### Changed

- Breaking: local `check_duplicates.py --fix` changes nothing unless a reviewed person is named with `--person` or
  matched from `git config user.name`.
- Pull requests into `main` merge through the merge queue (**Merge when ready**), and a new release's production
  site is published only after a maintainer approves it in the `production` environment.

Since v1.0.0-alpha.2.

### Merged pull requests

- Badges added to README and DOI to citation files ([#81](https://github.com/dsw-nrp/eosc-fair-guide/pull/81))
- Make duplicate repairs actionable and safe ([#102](https://github.com/dsw-nrp/eosc-fair-guide/pull/102))
- chore\(deps-dev\): Bump swagger-ui-dist from 5.33.3 to 5.34.0 ([#106](https://github.com/dsw-nrp/eosc-fair-guide/pull/106))
- chore\(deps-dev\): Bump @fission-ai/openspec from 1.14.2 to 1.14.3 in the patch-updates group across 1 directory ([#105](https://github.com/dsw-nrp/eosc-fair-guide/pull/105))
- chore\(deps\): Bump nginxinc/nginx-unprivileged from \`378d0c3\` to \`b5047b9\` in /docker ([#104](https://github.com/dsw-nrp/eosc-fair-guide/pull/104))
- docs\(openspec\): consolidate CI and repository workflow plans ([#103](https://github.com/dsw-nrp/eosc-fair-guide/pull/103))
- Merge queue checks, staging reuse and approval-gated production \(group 4\) ([#109](https://github.com/dsw-nrp/eosc-fair-guide/pull/109))
- Record the applied merge queue and production approval \(task 4.8\) ([#112](https://github.com/dsw-nrp/eosc-fair-guide/pull/112))
- chore\(deps-dev\): Bump roc-validator from 0.12.2 to 0.13.0 in the minor-and-patch group ([#110](https://github.com/dsw-nrp/eosc-fair-guide/pull/110))
- chore\(deps\): Bump the minor-and-patch group with 2 updates ([#111](https://github.com/dsw-nrp/eosc-fair-guide/pull/111))
- feat\(intake\): area labels, issue templates and Project checks \(group 5\) ([#113](https://github.com/dsw-nrp/eosc-fair-guide/pull/113))

### Direct commits

- feat\(agent-tooling\): split workflow runs into visible hand-off and bulk dirs ([a38f70f](https://github.com/dsw-nrp/eosc-fair-guide/commit/a38f70f785818f7bc1cacba3b45eddabdeacf7bb))
- chore\(deps-dev\): update DOMPurify, undici and fast-uri for security advisories ([e19757b](https://github.com/dsw-nrp/eosc-fair-guide/commit/e19757b55c79370d488d2897b4df6200bc431c38))
- docs\(rehearsal\): record post-merge deployment and alpha.3 preparation ([7b3fa74](https://github.com/dsw-nrp/eosc-fair-guide/commit/7b3fa743f0afe526c9cd8067ec734702f432ea22))

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

