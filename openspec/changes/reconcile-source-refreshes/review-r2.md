# Second runtime review dispositions

Review: [dsw-nrp/eosc-fair-guide#180, review 5906482392](https://github.com/dsw-nrp/eosc-fair-guide/pull/180#pullrequestreview-5906482392),
at `a958a80474a2560714e851317fd48d6032f29d76`. The maintainer supplied the review during authorized PR preparation.
It confirms the previous blocking repairs. This round retains the declared Python floor and bounds cleanup to
generated staging state under the existing recovery contract; no dependency or stored-format change is required.

| Finding or observation | Disposition |
| --- | --- |
| N1 abandoned stages after a hard stop | Fix in the runtime PR: guarded cleanup during recovery, retaining verified assets and unrelated entries. |
| N2 Python 3.12-only `Path.is_junction` | Fix in the runtime PR: use Python 3.11-compatible link/reparse metadata and verify on a real 3.11 interpreter. |
| Existing missing/empty-set `--check` success | Advisory follow-up: absence/bootstrap validation semantics need a separate explicit decision. No issue has been filed. |
| Existing unvalidated host in work filename | Advisory follow-up with input/fetch policy; this round does not claim to repair it. No issue has been filed. |
| Prior deferred-part revision gate | Retains its separate planning disposition; no protocol is added here. |

Both failures were reproduced before the fix: stale stages remained after recovery and real Python 3.11.15
raised `AttributeError` at `Path.is_junction`. The 28-test favicon suite now passes on Python 3.11.15 and 3.14.7.
It verifies abandoned-directory cleanup both with and without backup recovery, exact retained asset bytes,
unrelated directories/files, rejected symlink/reparse metadata, inspection failure and older publication faults.
The interpreter is isolated under the ignored repository cache; PATH, registry and the declared floor are unchanged.

The integrated reader at `3107c3011f9274fea13812d7f4bf8e4c89fb0e0b` passes all 36 local checks in 208.8 seconds.
All six prepared/published stages pass prerequisite-relative freshness, duplicate and size checks. The reader's
initial download is 307,001 bytes in Czech and 304,602 bytes in English, below 307,200. Native source facts,
headers and unique typed identifiers still match the original four PRs exactly. No browser content or asset
acquisition changed; the existing visual evidence remains applicable.

Required hosted checks pass on all six implementation heads below. PR descriptions and heads are read back
exactly; original source prose and all published ancestry remain preserved.

## Published implementation-head acceptance

| PR | Head | Required checks |
| --- | --- | --- |
| [dsw-nrp/eosc-fair-guide#180](https://github.com/dsw-nrp/eosc-fair-guide/pull/180) | `dcad578976028c56a2af12b1ec4edd029147ddbc` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43629916682) |
| [dsw-nrp/eosc-fair-guide#178](https://github.com/dsw-nrp/eosc-fair-guide/pull/178) | `8c2f7a2f1649901e3f7b750c672a925c72ebf92e` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43630224349) |
| [dsw-nrp/eosc-fair-guide#177](https://github.com/dsw-nrp/eosc-fair-guide/pull/177) | `eaa2a70120a5182920499f49dd3d5c31065d717c` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43630223896) |
| [dsw-nrp/eosc-fair-guide#176](https://github.com/dsw-nrp/eosc-fair-guide/pull/176) | `7148ea52d76602edf99d6e7d05a7b04790235a65` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43630223805) |
| [dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168) | `b5c77f689f497d0756f97282f8cf70a18a07b68c` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43630222967) |
| [dsw-nrp/eosc-fair-guide#181](https://github.com/dsw-nrp/eosc-fair-guide/pull/181) | `3107c3011f9274fea13812d7f4bf8e4c89fb0e0b` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43630218000) |

The subsequent reader completion record changes only validation notes and task status; its own required
hosted checks are verified before handoff. No PR is merged, review thread resolved, issue closed, spec synced
or change archived by this work. Human review remains required.
