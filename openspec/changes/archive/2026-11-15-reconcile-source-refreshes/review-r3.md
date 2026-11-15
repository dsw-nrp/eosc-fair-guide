# Third runtime review dispositions

Review: [dsw-nrp/eosc-fair-guide#180, review 5908126039](https://github.com/dsw-nrp/eosc-fair-guide/pull/180#pullrequestreview-5908126039),
at `ba434b4e084e471312396276877a881de96f35be`. The maintainer supplied it during the already-authorized repair and
publication workflow. These repairs complete the existing revision and favicon contracts in section 11.

| Finding | Disposition |
| --- | --- |
| F1 nested modules omitted from revision | Repair recursive consumer coverage, hashing relative paths and bytes; reproduce nested-only changes. |
| F2 equally stale initial pair accepted | Bind both initial payloads to the generated document expectation before graph/UI/config acceptance. |
| F3 query-bearing script URL malformed | Share one query/fragment-safe URL helper across all four existing loaders. |
| F4 ineffective startup Retry | Offer Reload alone at startup; preserve refetching Retry for deferred registrations. |
| F5 shared CGNAT refusal | Add an explicit policy guard and independent test as hardening; no demonstrated floor bypass. |
| F6 unreachable `jpeg` extension | Remove the unused spelling; detected JPEG images already use `jpg`. |
| Other maintenance clients use ordinary `urlopen` | Retain the explicitly approved favicon-only scope; no new issue is implied or filed. |

The version claim in F5 is not established: [CPython v3.11.0](https://github.com/python/cpython/blob/v3.11.0/Lib/ipaddress.py#L1236-L1239)
already excludes its shared-address network in `IPv4Address.is_global`, with that network defined as
`100.64.0.0/10`. The explicit guard still makes the local policy independent of this predicate.

All nine preceding findings are confirmed fixed by the new review. Their historical evidence remains in
`review-r1.md` and `review-r2.md`. No reply, thread resolution, issue closure, merge, spec sync or archive is
performed as part of this remediation. Current verification and publication evidence will be recorded below.

Fail-first probes reproduce F1-F4. F5 is tested with a controlled global-classification override, including both
range boundaries, mapped addresses and adjacent public controls; it is not presented as a real interpreter bypass.
The corrected suites pass 66 tests on Python 3.11.15 and 21 Node runtime tests. Real browser requests exercise
all four URL-helper callers with preserved query values and a single revision. Initial equal-stale pairs and
missing expectations stop acceptance; Reload alone restores the Guide with saved answers. Deferred Retry and
input retention remain covered in both languages, files/HTTP/iframes, desktop/320 px and print. The current
matrix produces 42 recovery captures, including visually inspected new startup states. Full integrated and
hosted acceptance remain pending.

Complete integrated local acceptance subsequently passes all 36 native checks in 255.8 seconds with the four
prepared source refreshes and reader integration present. Strict OpenSpec validation passes 7/7. Original
source fields, headers and unique typed identifiers remain exact. Initial Czech/English payloads remain below
307,200 bytes. The implementation is carried forward through all six local branches; publication and required
checks on their actual remote heads are the remaining delivery task.

## Published implementation-head acceptance

All six findings are addressed in the runtime and carried through the four source PRs and reader integration.
Required hosted checks pass on every implementation head below; source facts and published ancestry remain intact.

| PR | Implementation head | Required checks |
| --- | --- | --- |
| [dsw-nrp/eosc-fair-guide#180](https://github.com/dsw-nrp/eosc-fair-guide/pull/180) | `5e048b79e40f1bce1f0354b658920ce257053e88` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43662872191) |
| [dsw-nrp/eosc-fair-guide#181](https://github.com/dsw-nrp/eosc-fair-guide/pull/181) | `b7748c852aaaabd7d7af6a867fc1415b68798e35` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43662871461) |
| [dsw-nrp/eosc-fair-guide#178](https://github.com/dsw-nrp/eosc-fair-guide/pull/178) | `19afa59c8a64ffeb1027436fda4f37bd4fa8e3ab` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43662876934) |
| [dsw-nrp/eosc-fair-guide#177](https://github.com/dsw-nrp/eosc-fair-guide/pull/177) | `b72d563de148878bf84a91843997287c19884356` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43662876626) |
| [dsw-nrp/eosc-fair-guide#176](https://github.com/dsw-nrp/eosc-fair-guide/pull/176) | `44ea914c89de73de52fbe44527910afeec493ea4` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43662877574) |
| [dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168) | `963e26e087c722d4817dff7d6b0edb66662e1dee` | [passed](https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/43662876788) |

The following record-only completion commit receives its own required checks before final handoff. Human review
and the existing merge order remain required; no review thread is replied to or resolved, issue closed, PR merged,
spec synced, change archived or release published by this work.
