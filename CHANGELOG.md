# Changelog

All notable changes to this guide are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). A release updates the version and date here, in
`CITATION.cff` and in the crate's publication metadata together.

## [Unreleased]

- Breaking: source refreshes now refuse unresolved identity collisions within one kind and scope instead of
  allocating numbered identifiers; review the identity match or supply a reviewed descriptive identifier before retrying.

- Breaking: repository API records may omit `url` while planned or in development when they link an NKR record.
- Breaking: every record is addressed `<kind>/<id>` in plain kind words (`resources/github`, `stations/licence`),
  or `<kind>/<scope>/<id>` where scope belongs to its identity, instead of the code addresses
  (`res/tool/github`, `step/licence`); API record files, catalogue routes and `guideRoute` values follow, and the
  catalogue's groups are `glossary`, `lifecycles` and `models`.
- Breaking: every record's `@id` is its IRI under the namespace `https://w3id.org/eosc-cz/fair-guide/`
  (`…/id/stations/licence`), not a crate fragment; the crate drops `catalogueAddress`.
- Breaking: a registry's record of a thing is a `dcat:CatalogRecord` and `schema:CreativeWork` under it
  (`#re3data`, `#fip-dashboard`, `#knav`, `#nkr`, `#fairsharing`, `#datacite`) naming the thing by
  `foaf:primaryTopic`; the thing does not list those records again. The record rests on its snapshot, which lists it;
  a curated work rests on the Guide's selection, and an organisation or infrastructure names its published sources
  with `dcterms:source`. A thing only registries know keeps its identity, name, address and filter facts, and its
  description stays on the record. A registry is a resource and is no longer in `#repositories`. A named agent is the
  one thing of that name, and a FIP Dashboard organisation record joins a thing only by a reviewed handle or ROR, as
  `#fip-dashboard-organization`.
- Breaking: references in text are `[[<kind>/<id>|phrase]]`, with a part as `<address>#<fragment>` and a kind word
  for its list; the Guide's profile is `[[pages/machines#tasks|…]]`, and anything else is refused.
- Breaking: provenance `objects`, model association `target` and the worked example's `steps` name records by
  address; a result `*` records the Guide as an action's result; `content/identifiers.toml` lists each identifier
  under the kind of its record, as the address without the kind (`vocabularies = ["lenses/V", …]`).
- Breaking: every controlled term is a `schema:DefinedTerm` in one term set, named only by the term with
  `schema:inDefinedTermSet` and ordered by `guide:termPosition`; the set does not list terms again with
  `schema:hasDefinedTerm`, and no instance carries `skos:` types or `skos:inScheme`. Every status is a term of its
  scheme: `creativeWorkStatus` gives way to `clauseStatus`, `fipStatus`, `declarationStatus` and `releaseStatus`,
  `healthStatus`, `preparationStatus` and `nodeState` name terms instead of strings.
- Breaking: an advice item is a `guide:AdviceItem` with an `adviceKind` term, not a `HowToTip` or `HowToDirection`;
  a check is also an `ftr:Benchmark`, a question an `ftr:Metric` naming its check by `ftr:hasBenchmark` and its
  principles by `dqv:inDimension`, while the check does not repeat its questions. Only criteria exposed through an
  API are `ftr:Test`; F-UJI criteria are `ftr:Metric`, and local assessment criteria carry no FTR type. The manual
  `tests/self-check/` records are gone, and `api/tests/<question>.json` only supports saved results in revisions 1–3.
- Breaking: a question's pre-fill is a `guide:PrefillMapping` part (`prefillSource`, `prefillField`,
  `prefillCoverage`) instead of `additionalProperty` values, `prefillLevel` and `championEvidenceOnly`.
- Breaking: relations are stated in one documented direction, classes are `@type`s rather than
  `additionalType` strings, and schema.org properties stay within their pinned domain and range declarations;
  vocabulary declarations are checked against the built graph and its pinned vocabularies.
- Breaking: quoted glossary and life-cycle definitions move from terms to `schema:CreativeWork` fragments linked
  with `dcterms:hasPart`, carrying their text, licence and citation; a second Czech life-cycle source has its own
  fragment linked by `guide:quotedDefinition`. A local criterion calls its browser function by `guide:entryPoint`.
- Breaking: the EOSC CZ Node is `resources/eosc-cz-node`, a `schema:Service` provided by e-INFRA CZ, and onboarded
  entries are `dcat:Relationship` parts linked from the Node by `dcat:qualifiedRelation`, not schema.org members;
  the NRP Data Catch-all Repository is a `service`, not a `registry`.
- Breaking: the Guide's profile is `0.2`, with shapes for the graph model.
- Breaking: API v1 replaces role-named collections, code paths and per-record operations with `api/v1/index.json`
  and one typed list plus unscoped or scoped record template per kind. Compact references share vocabulary-set
  documents, list entries carry identity and filter fields, health is `api/v1/health.json` under `operations`, and
  the old tree is not generated.
- Breaking: saved results use format revision 4: a reader's answer is a `dqv:QualityMeasurement` of its question's
  persistent IRI, with `dqv:computedOn` and `dqv:value`, rather than an FTR test of a synthetic question-test address.
  Automated evidence names actual test IRIs. Revisions 1–3 still load, and their `api/tests/<question>.json`
  support documents describe and link the question without presenting a test.
- Required step: a question that asks what a cited clause says names it as its `requirement` and states no
  `statement`; the content check refuses a statement that copies a cited clause.
- Security: render source-controlled refresh diagnostics as bounded literal text in logs, reports and workflow summaries.

## [1.0.0-alpha.5] - 2026-11-01

### Changed

- Breaking: release container images are tagged with the version, without the git tag's `v`
  (`ghcr.io/dsw-nrp/eosc-fair-guide:<version>`); the images of `1.0.0-alpha.1` to `1.0.0-alpha.4` carry it beside
  their `v` tags.

Since v1.0.0-alpha.4.

### Merged pull requests

- Tag release images with the version and finish the CI change ([#143](https://github.com/dsw-nrp/eosc-fair-guide/pull/143))
- fix\(agent-tooling\): regenerate the inventory after the AIS CR redelivery ([#144](https://github.com/dsw-nrp/eosc-fair-guide/pull/144))
- chore\(deps-dev\): Bump ruff from 0.17.1 to 0.17.2 in the minor-and-patch group ([#138](https://github.com/dsw-nrp/eosc-fair-guide/pull/138))
- chore\(deps\): Bump the minor-and-patch group with 2 updates ([#139](https://github.com/dsw-nrp/eosc-fair-guide/pull/139))
- Refresh the re3data snapshot ([#117](https://github.com/dsw-nrp/eosc-fair-guide/pull/117))
- content: streamline stations and merge duplicate advice \(\#35\) ([#145](https://github.com/dsw-nrp/eosc-fair-guide/pull/145))
- Restore main and triage open work: watch, audit and digest fixes ([#146](https://github.com/dsw-nrp/eosc-fair-guide/pull/146))
- content: add consent, data appraisal and team continuity advice \(\#36\) ([#147](https://github.com/dsw-nrp/eosc-fair-guide/pull/147))
- feat\(catalogue\): show every field a catalogue entry carries ([#149](https://github.com/dsw-nrp/eosc-fair-guide/pull/149))
- content: add folder, format, synthetic sample and packaging advice \(\#37\) ([#151](https://github.com/dsw-nrp/eosc-fair-guide/pull/151))
- content: add sample identifier, patent and post-publication error advice \(\#38\) ([#161](https://github.com/dsw-nrp/eosc-fair-guide/pull/161))
- feat\(content\): cite the original source and bound quotes without a licence ([#148](https://github.com/dsw-nrp/eosc-fair-guide/pull/148))
- chore: close out and archive restore-main-and-triage-open-work ([#164](https://github.com/dsw-nrp/eosc-fair-guide/pull/164))
- feat\(credit\): show content contributors on the about page and in Zenodo ([#166](https://github.com/dsw-nrp/eosc-fair-guide/pull/166))

### Direct commits

- Update AIS CR delivered tools ([b3474e5](https://github.com/dsw-nrp/eosc-fair-guide/commit/b3474e50b4e5403c7630dbe7be71d5036c529701))

## [1.0.0-alpha.4] - 2026-10-28

### Changed

- Breaking: maintenance observations move to one **Maintenance digest**; follow it instead of the per-finding `guide-health` issues.
- Breaking: the Guide's own term and RO-Crate profile IRIs move from `https://fair.eosc.cz/` to the reviewed
  `namespace` in `content/guide.toml`, now `https://dsw-nrp.github.io/eosc-fair-guide/terms#` and `…/profile/0.1`.
  The preview carries them from this change, production from the next release. Record IDs and external IRIs are
  unchanged and earlier archives keep their IRIs; read each artifact's own context and profile.

Since v1.0.0-alpha.3.

### Merged pull requests

- CI workflows and docs refactor ([#116](https://github.com/dsw-nrp/eosc-fair-guide/pull/116))
- Finish the merge-day hand-offs and name release versions by their form ([#141](https://github.com/dsw-nrp/eosc-fair-guide/pull/141))


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

