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
in 261.9 seconds. Hosted verification remains pending on the repaired heads.

| Finding | Disposition |
| --- | --- |
| H1 parent/file-iframe storage assertion | Fix in the runtime PR: seed and verify the state in its owning document. |
| M1 maturity action before questions data | Fix in the runtime PR: retain the target, gate interpretation, and preserve neutral Retry. |
| M2 citation carriers still name footer | Fix the two READMEs, CFF message and Zenodo notes; retain attribution and licensing metadata. |
| M3 interrupted favicon publication | Stage/validate before replacement and preserve a recoverable verified backup; test interruption and restart. |
| M4 empty expected API lookup map | Compare against the complete published API projection and require nonempty coverage. |
| M5 missing counter-refusal release note | Add the required Unreleased line and runtime `breaking-change` label under the existing policy. |
| L1 mixed-version deferred parts | Advisory, track separately: a revision protocol changes the delivery contract and needs its own planning decision. No issue has been filed. |
| L2 inconsistent implicit repository address | Fix in the runtime PR with shared route/address inference and a legacy-row regression. |
| L3 obsolete badge comment | Remove/rewrite the comment to match the shared favicon policy. |
| Existing arbitrary HTTPS host fetches | Advisory, track separately: network-target policy is broader security work; no network exploit was established in this review and no issue has been filed. |
| Existing cleartext intermediate redirects | Advisory, track separately with the fetch-policy decision; no issue has been filed. |
| Existing unescaped positive manifest strings | Fix in the runtime PR alongside publication: consistent TOML-safe scalar serialization preserves the existing format. |
| Existing search-focus preloading | Keep advisory: current intentional deferral-to-intent behavior; no change or separate issue is proposed here. |
| Existing agent-derived organisation reservations | Advisory, track separately: the address helper repair does not claim to cover inferred agent identities; no issue has been filed. |
