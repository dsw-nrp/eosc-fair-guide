# Local acceptance and remaining hand-offs

Updated: 2026-10-25. Owner of the hosted steps below: the repository maintainer, David Novák.
Implementation remains on `agents/claude/ci-workflows-replan`, draft PR #116. Local acceptance is not delivery to
the default branch or evidence that a hosted workflow has exercised the new code.

## Issues and release notes

| Item | Verified state and disposition |
| --- | --- |
| [#83](https://github.com/dsw-nrp/eosc-fair-guide/issues/83) | Read back open on 25 October. Task 7.7 implements crawler files, configured-base generation and assembly preservation. The change is locally verified; issue closure awaits reviewed delivery and publication evidence |
| [#84](https://github.com/dsw-nrp/eosc-fair-guide/issues/84) | Read back open on 25 October. Tasks 7.1/7.2 and group 10 deliver the maintainer landing page, generated catalogue, reproduction, timings and runbooks. The approved change supersedes the issue's older lane names, per-finding monitoring and procedure location; the required context is `checks`. Closure awaits reviewed delivery |
| #59–#65 and #85–#101 | No migration is claimed or performed. Their observation/discussion refresh, exact mapping, first digest, approval and read-back remain task 6.10; the independently reviewed migration runbook is ready |
| `[Unreleased]` | One breaking-change line tells consumers to follow the Maintenance digest. Ordinary documentation and checker changes use commit history; published release sections are unchanged |

Issue states and bodies were read without posting, closing or editing them. No speculative issue closure or
release-note publication is included in local acceptance.

## Explicit owned deferrals

| Task | Completed locally | Remaining step and precondition |
| --- | --- | --- |
| 5.8/5.9 | Audit repair, fixtures and planted regressions; the owner confirmed installation acceptance in the earlier session | After #116 reaches the default branch, the maintainer runs **Live health and source watch** with `parts: audit` and records that Project #1 fields, views and items are read while genuinely unreadable sections stay unavailable |
| 6.10 | Digest implementation and independently reviewed migration runbook | After default-branch delivery, refresh all original threads; show the exact mapping, first digest and closure payloads for approval; publish and close only after approval, then reread |
| 6.11 | Digest runbook and maintenance reference pass structure checks and the independent maintainer review | Verify its steps against the published new digest after delivery/migration; no published digest is simulated as evidence |
| 8.7 | The maintainer created the `staging` environment; channel-record implementation and offline fixtures are complete | After a real successful `staging` record exists, verify API-created deployment acceptance, approve the exact tag-ruleset diff, switch `github-pages` to `staging` and audit again. Rollback restores `github-pages` |
| 8.8 | Native helper, mirrors and ownership/delivery checks; previous-prerelease tag selection | Exercise against the next actual draft release, stop before apply and show the body and `prev..tag` range. No draft exists in the recovered session; published releases are not used as substitutes |
| 11.3 | Release and recovery runbooks pass the independent maintainer review | Obtain separate hosted-rehearsal approval, follow the release runbook alone, merge an intervening PR and record queue acceptance, refusal/re-preparation, preview notice, channel records and timings |

These tasks remain unchecked. A separately approved rehearsal or settings/migration write is not implied by the
instruction to continue implementation. Archive still requires verified completion and fresh explicit approval.


## Final local verification

The full native close-out passed 36/36 checks in 150.0 seconds, including the 656 discovered unit tests (one
platform skip), browser/API checks, accessible diagrams and the three crate profiles. Strict OpenSpec validation,
generation, ownership and delivered integrity pass. The task tracker is 71/78 complete; the seven tasks listed
above remain open for the stated hosted evidence and approvals. The local documentation receipt is
`documentation-review.md`.
