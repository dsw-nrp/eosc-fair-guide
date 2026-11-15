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
