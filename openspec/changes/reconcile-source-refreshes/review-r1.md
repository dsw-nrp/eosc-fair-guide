# Runtime review dispositions

Review: [dsw-nrp/eosc-fair-guide#180, review 5905431297](https://github.com/dsw-nrp/eosc-fair-guide/pull/180#pullrequestreview-5905431297),
at `bc1495e33967beeb6dbc64bcb54e97e1137cfe54`. The maintainer supplied this review during authorized PR preparation.
Findings are being verified and repaired within the existing change; completion requires fresh evidence on the
published heads. Earlier local checks do not establish acceptance of these repairs.

Focused verification passes 62 Python tests and the bilingual browser suite. Fail-first probes detect the old
pre-fill race, a planted missing deferred API entry, the implicit-route retirement and interrupted favicon
publication/restart. The browser suite covers delayed, failed and retried data, preserved manual answers, a
superseded pending target, and owning-document iframe state. Both phone failure screenshots were inspected.
The runtime `breaking-change` label was applied and read back. Complete runtime acceptance passes all 36 checks
in 261.9 seconds. Required hosted checks subsequently passed on all six published implementation heads, as recorded below.

The combined reader at `649ca663e10b685d5e360d82de80e7055b52cdce` passes all 36 local checks in 230.9 seconds.
The runtime repair and forward merges are published on all six PRs; their original histories remain ancestors.
Each committed stage passes prerequisite-relative freshness, duplicates and the 300 KB bound. The combined
initial download is 307,003 bytes in Czech and 304,604 bytes in English, below 307,200. All four source datasets
retain exact native facts, source headers and unique genuine typed identifiers against their original PR heads.
Eight additional bilingual desktop/320 px screen/print viewports verify the retained re3data target and were
reviewed alongside the delayed/failed/Retry fixtures.

| Finding | Disposition |
| --- | --- |
| H1 parent/file-iframe storage assertion | Fix in the runtime PR: seed and verify the state in its owning document. |
| M1 maturity action before questions data | Fix in the runtime PR: retain the target, gate interpretation, and preserve neutral Retry. |
| M2 citation carriers still name footer | Fix the two READMEs, CFF message and Zenodo notes; retain attribution and licensing metadata. |
| M3 interrupted favicon publication | Stage/validate before replacement and preserve a recoverable verified backup; test interruption and restart. |
| M4 empty expected API lookup map | Compare against the complete published API projection and require nonempty coverage. |
| M5 missing counter-refusal release note | Add the required Unreleased line and runtime `breaking-change` label under the existing policy. |
| L1 mixed-version deferred parts | Initially advisory; the maintainer now approves a revision protocol inside this change, tracked in section 10 of the tasks and design. No issue has been filed. |
| L2 inconsistent implicit repository address | Fix in the runtime PR with shared route/address inference and a legacy-row regression. |
| L3 obsolete badge comment | Remove/rewrite the comment to match the shared favicon policy. |
| Existing arbitrary HTTPS host fetches | Promoted by the maintainer into the active public-destination policy; no network exploit was established by this review and no issue has been filed. |
| Existing cleartext intermediate redirects | Promoted into per-hop HTTPS enforcement in this change; no issue has been filed. |
| Existing unescaped positive manifest strings | Fix in the runtime PR alongside publication: consistent TOML-safe scalar serialization preserves the existing format. |
| Existing search-focus preloading | Keep advisory: current intentional deferral-to-intent behavior; no change or separate issue is proposed here. |
| Existing agent-derived organisation reservations | Promoted into complete shared identity reservations in section 10; the earlier address helper did not cover inferred agents. No issue has been filed. |

## Published implementation-head acceptance

| PR | Head | Required checks |
| --- | --- | --- |
| [dsw-nrp/eosc-fair-guide#180](https://github.com/dsw-nrp/eosc-fair-guide/pull/180) | `a958a80474a2560714e851317fd48d6032f29d76` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43615576712) |
| [dsw-nrp/eosc-fair-guide#178](https://github.com/dsw-nrp/eosc-fair-guide/pull/178) | `71db5da1fc23d4b4beb8c207dd6014f8a35e57d3` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43616140005) |
| [dsw-nrp/eosc-fair-guide#177](https://github.com/dsw-nrp/eosc-fair-guide/pull/177) | `6c7973b516e0999419018c65ec58252ee16a4e05` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43616139921) |
| [dsw-nrp/eosc-fair-guide#176](https://github.com/dsw-nrp/eosc-fair-guide/pull/176) | `f86cd32759d10304d5a8d2eb5321759cd277eb1f` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43616139853) |
| [dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168) | `ad8918dfe7e154c2c4f0b716cdf762caf10358ea` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43616139771) |
| [dsw-nrp/eosc-fair-guide#181](https://github.com/dsw-nrp/eosc-fair-guide/pull/181) | `649ca663e10b685d5e360d82de80e7055b52cdce` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43616130603) |

PR descriptions and heads were read back exactly; original source PR prose is preserved. The completion
record is the only subsequent reader change and receives its own required hosted checks before handoff.
No PR was merged or review thread resolved by the agent. Human content and technical acceptance remain required.
