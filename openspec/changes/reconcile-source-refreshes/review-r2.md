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

Complete integrated acceptance and published-head verification remain pending for this round. Earlier passing
heads are historical evidence and do not establish acceptance of the new repair.
