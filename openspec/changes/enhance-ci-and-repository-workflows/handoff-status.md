# Local acceptance and remaining hand-offs

## Finishing decisions, 28 October 2026

The maintainer decided to finish this change within days of the merge rather than keep hosted hand-offs open.
Group 16 in `tasks.md` holds the new work and the dated decisions on each remaining task. Nothing was pushed,
dispatched, posted, closed or archived by this capture.

| Remaining scope | Outcome after the merge |
| --- | --- |
| 13.3, 5.8, 5.9 | One audit-only run on merge day. If the organization owner has not yet accepted the Issue Types/Fields reads (the maintainer's token cannot tell), they are recorded as unavailable and the tasks close on the Project read |
| 6.10, 6.11 | Migration of every open `guide-health` issue by label and marker (43 on 28 October, none with a human comment), then the digest runbook checked against the digest it publishes |
| 8.7 | `staging` record from the first default-branch deployment; pre-tag checks on the alpha.4 tag through the route actually used |
| 11.3, 8.8 | The alpha.4 release, following the release runbook, aligns production with the reviewed namespace and exercises the release-notes helper on its draft |
| Human documentation review | Dropped; the maintainer's walk-through of the runbooks in use replaces it (16.11) |

Observed on the remote between 25 and 27 October: Source refresh run 40313332538 failed for heslar and nkr and
proposed re3data as #117, with the reasons only in its report artifact. Legacy watch run 40485129785 ended green
after opening #118–#135, 17 of them for the unreachable `heslar.openscience.cz`. #116's last hosted run, on
`1a5287f`, failed on drifted generated mirrors (passing in the working tree) and on the quick job's missing PyYAML.

## Follow-up implementation, 26 October 2026

Owner of remaining hosted/human steps: repository maintainer David Novák. The requested checkpoint is local
commit `1a5287f5adbc083ce95728212388e5527dc54261`; subsequent implementation remains uncommitted on the same
branch. Nothing was pushed, dispatched, published, closed or archived by this continuation.

The planning decision below added unchecked task 12.7 (82/101). A Codex continuation then implemented most of the
coordinated cutover and launched the complete documentation readers, but stopped mid-edit when its workspace ran out
of credits; its contributor receipt was never written. The resumed apply (Claude Code) reviewed and repaired that
draft and completed group 12 (89/101), then stopped at its runtime's session limit during the documentation review.
A Kilo continuation completed the final audience passes and renewed acceptance, so the tracker is 93/101. Completed
follow-ups are 12.1-12.7, 13.1, 13.2, 13.4, 13.5, 14.1-14.9, 15.1 and 15.2. Evidence lives in
`address-inventory.md`, `settings-evidence.md` and `documentation-review.md`; the earlier close-out below retains
its historical scope.

Every remaining task is a hosted or human hand-off: 5.8, 5.9, 6.10, 6.11, 8.7, 8.8, 11.3 and 13.3. None of them
can be closed with local evidence, and this record authorises none of them.

| Outstanding scope | Current boundary and next evidence |
| --- | --- |
| Hosted cutover (11.3) | Group 12 is accepted locally (`address-inventory.md`). The first paired release publication, actual Pages API behaviour, hosted discovery and search-engine uptake need the separately approved rehearsal and release. No release, custom-domain adoption or DNS change is authorized |
| 13.3 and 5.8/5.9 | Local credential routing and explicit Organization Issue Types/Fields read requests are tested. Installation acceptance for those new reads, actual token issuance and readable Issue Types/Fields/Project endpoints still need default-branch audit-only evidence. Previously confirmed Project acceptance is not requested again |
| 8.7 | The maintainer selected both `github-pages` and `staging`, plus Actions `checks`; the fresh ruleset audit matches. Retain them. Successful staging deployment records and pre-tag checks on the release commit still require hosted proof. No replacement of either deployment gate is planned; any later settings mutation needs its exact approved diff |
| 6.10/6.11 | The complete one-time procedure now lives in `legacy-health-migration.md` and passes independent relocation review. Refresh all original threads, prepare exact mapping/digest/closure payloads and obtain their approval before migration. Recurring runbook acceptance still needs the actual published digest |
| 8.8/11.3 | The native release helper and procedures are locally checked. Its actual-draft exercise and the hosted rehearsal remain separately approved steps; rehearsal must cover coordinated namespace cutover and pair refusal/retry, issue-origin refresh, actual-location discovery and scoped audit reads as well as the existing release scenarios |
| 14.1/14.9 and 15.1/15.2 | Complete locally on 27 October. Three fresh audience readers checked all 37 documents (843 claims; 25 findings repaired, 59 owned deferrals) in `documentation-review.md`. The native suite passes 36/36 checks in 203.2 s with 684 unit tests, strict OpenSpec 6/6 and zero generation, ownership or delivery findings. The issue and changelog reconciliation follows below. Ordinary human content review of the pull request remains required |

### Issues and change notes, read back 27 October 2026

| Item | Verified state and disposition |
| --- | --- |
| [#83](https://github.com/dsw-nrp/eosc-fair-guide/issues/83) | Open, unchanged since 25 October. Groups 7 and 12 now cover it: a sitemap from the verified production location, and a crawler policy that writes `robots.txt` only at an origin root and keeps preview `noindex` pages crawlable. The issue's original expectation of a project-subpath robots file is superseded, because such a file controls nothing. Closure needs reviewed delivery and the first publication's evidence |
| [#84](https://github.com/dsw-nrp/eosc-fair-guide/issues/84) | Open, unchanged since 25 October. The maintainer landing page, generated catalogue and runbooks are now complete, and the maintainer reader verified them in full. Closure needs reviewed delivery |
| [#15](https://github.com/dsw-nrp/eosc-fair-guide/issues/15), [#32](https://github.com/dsw-nrp/eosc-fair-guide/issues/32) | Open, unchanged since 25 October, and excluded from this change. The Guide follows its actual Pages location, so no custom domain, DNS change, alias or redirect is adopted or inferred. The legacy `https://fair.eosc.cz/` IRIs in released archives are kept |
| `[Unreleased]` | Two breaking lines: the Maintenance digest, and the Guide's term and profile IRIs moving to the actual publication root, with earlier archives keeping theirs and consumers reading each artifact's own context and profile. `check_changelog` passes within the full suite |

Remaining gates, each needing its own approval: the hosted audit for 13.3 and 5.8/5.9; the digest migration and
published-digest check (6.10/6.11); staging records and pre-tag checks (8.7); the real draft exercise (8.8); and
the rehearsal (11.3). The rehearsal covers the coordinated cutover with pair refusal and retry, actual-location
discovery, issue-origin refresh and scoped audit reads. Decisions 13.4 and 13.5 are recorded and keep the live
settings. No issue was posted, edited or closed in this reconciliation.

The selected queue target is two concurrent builds, maximum ten/minimum one merges and zero batching wait.
The read-only settings audit matches; no remote setting was changed. The former target below to replace
`github-pages` with `staging` is superseded by the maintainer's explicit decision in 13.4; it is retained only
as part of the dated 25 October receipt. The earlier proposed migration runbook location is likewise superseded
by the complete change-owned procedure.

## Historical local receipt, 25 October 2026

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
