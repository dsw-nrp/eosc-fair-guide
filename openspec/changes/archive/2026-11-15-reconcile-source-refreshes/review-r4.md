# Fourth runtime review dispositions

Review: [dsw-nrp/eosc-fair-guide#180, review 5910050172](https://github.com/dsw-nrp/eosc-fair-guide/pull/180#pullrequestreview-5910050172),
at `5e048b79e40f1bce1f0354b658920ce257053e88`. It confirms all fifteen preceding findings are fixed.

| Item | Disposition |
| --- | --- |
| R1 UI-to-document guard lacks an isolated regression | Add document-current / KB-current / UI-stale to the existing runtime test, asserting rejection before graph, UI or configuration acceptance. Prove it detects removal of the UI guard. |
| Digest comment overstates independence from metadata | Correct the comment to describe generated data and build metadata plus consumer code. Keep the approved per-build behavior. |

This is test coverage and comment correction under the existing revision contract. It changes no application
behavior, stored format or API and requires no new specification delta. Existing source/identity decisions,
the 300 KB bound and publication/merge boundaries remain in effect. Verification evidence is kept in the rolling
usage entry and current PR/handoff records. No review reply, thread resolution, issue closure, merge, spec sync,
archive or release is authorized by this work.

The new case reports `Missing expected exception` when the UI guard is removed from an isolated in-memory copy
of `core.js`. The production file is left byte-for-byte unchanged. With the guard present, all 21 Node runtime
tests pass, including rejection before graph/UI/config acceptance. The digest comment now acknowledges build
metadata. Complete integrated native acceptance passes all 36 checks on the combined reader head. Exact-head
hosted acceptance is required before handoff and is recorded separately in the delivery evidence.
