# Tasks

## 1. Structured duplicate suggestions

- [x] 1.1 Extend the duplicate check's entry model so a reported group can carry a typed suggestion (entry, record, resolution, safe, file, table, field, value, reason) while the existing human-readable error text remains unchanged; verify with the existing duplicate-check unit tests and a new assertion on the PR 82 group.
- [x] 1.2 Implement one curated entry plus one present registry record, an authoritative key, missing link, exact reviewed placement, no accepted exception and unique ownership across the catalogue/proposals; verify re3data, FIP Dashboard and KNAV fixtures, existing/competing owners, cross-registry identity and deduplication.
- [x] 1.3 Write the suggestion collection to `duplicates.json` under `CHECK_REPORT_DIR` when set and to `--report <path>` when requested; verify the file shape, format version and absence of writes in the default text-only run.
- [x] 1.4 Add the PR 82 regression fixture (a re3data record and a curated `datarepo`-like resource) and verify that applying the suggested `re3data` link in memory yields no duplicate error and one content entity.
- [x] 1.5 Document the suggestion shape and the safe/unsafe boundary in `docs/content-model.md` under the one-entry-per-thing rule; verify the documented example matches the emitted fixture.

## 2. Local safe fix

- [x] 2.1 Apply only safe local links through validated atomic replacements with original-byte rollback and concurrent-target checks; register replacement bytes before cleanup without a discovery read, and verify application/recheck/cleanup failures, explicit restoration errors, and the exact successful diff, success message and provenance reminder, including planted missing-output regressions.
- [x] 2.2 Make `--fix` exit non-zero when no safe suggestion applies and print the remaining groups with their human-readable remedy; verify the exit code and output on an ambiguous fixture.
- [x] 2.3 Document the local fix workflow, requester provenance, handled-failure rollback and per-file rather than multi-file crash atomicity; verify the documented commands and failure guidance match the tested behavior.

## 3. Aggregate failure diagnostics and suggestion artifacts

- [x] 3.1 Collect every failed or partial required result with bounded output, normalize zero-exit partial rows into aggregate failures while retaining native lane evidence, and verify console/health agreement for multiple failures and pending/skipped cases.
- [x] 3.2 Copy the incoming lane `logs/` and `details/` into the health output before emitting a failure report; verify a failed aggregate's artifact contains the failing check log and detail file.
- [x] 3.3 Render every failed check and bounded output before optional suggestion processing, admit suggestions only from the reconciled duplicate lane, and keep PR head distinct from checked revision; verify wrong identity/build, missing/duplicate/incomplete evidence and extra directories cannot publish suggestions.
- [x] 3.4 Test multiple failures, bounded output, missing logs, malformed arrays/objects, optional read/write/append errors and preserved passing/failing outcomes; verify malformed suggestions are filtered safely and required reports remain available.
- [x] 3.5 Document the changed failure diagnostics and artifact contents in `docs/design.md`; verify the documented artifact names match the workflow.

## 4. Trusted PR comment suggestions

- [x] 4.1 Upload review suggestions only through a collector suggestions_path output emitted after successful current-run generation and summary publication; verify stale-file invalidation failure emits no upload path while valid duplicate failures remain actionable and the trusted publisher reads the artifact.
- [x] 4.2 Validate artifact format, PR head/repository, count/size and exact placement combinations; render bounded fenced patches and inert reasons, and verify malformed/oversized/stale cases plus Python/Node placement parity.
- [x] 4.3 Test suggestion rendering, escaping, bare URLs/images/mentions/backticks, comment bounds and stale-head omission; prove the publisher remains read-only and planted output regressions are detected.
- [x] 4.4 Document the comment section and its read-only boundary in `docs/design.md`; verify the PR check workflow remains read-only.

## 5. Maintainer `/fix-duplicates` command

- [x] 5.1 Add the separate trusted workflow and command parser for exactly `/fix-duplicates`, triggered only by `issue_comment` on pull requests; verify schedules and non-PR comments cannot invoke it.
- [x] 5.2 Reuse the current-permission check and verify the PR is open, same-repository, targets the default branch and has a non-default head; verify an unauthorised caller and a fork request change nothing.
- [x] 5.3 Read the PR head's content and authored validation attachments as data without executing PR code, using the shared accepted-group loader; verify safe and ambiguous fixtures plus both handler loading/validation paths.
- [x] 5.4 Resolve the commenter to an existing reviewed `[[person]]` through the GitHub identity and refuse when absent; verify no person is guessed and no provenance action is written for an unknown caller.
- [x] 5.5 Apply safe links with registered requester provenance and commit only the reviewed changes through the App without force/default-branch writes; verify parent/files/results, inert fenced diffs and diagnostics, embedded delimiters, truncation and retained commit references.
- [x] 5.6 Re-read the PR head before committing and abort with a comment when the target content changed; verify a simulated head race leaves the branch unchanged.
- [x] 5.7 Make the command idempotent and non-accepting: an existing link is a no-op, `content/duplicates.toml` is never edited, and the command never merges; verify each case with command tests.
- [x] 5.8 Document the command trust model, App secrets, person mapping, rollback and uncertain post-commit failure guidance; verify default-branch activation and a successful commit followed by a failed success comment requests branch inspection without claiming no change.

- [x] 5.9 Preserve repaired refresh PRs by requiring a complete nonempty inventory of expected App-authored snapshot commits before replacement; verify same-App repairs, human/other/unknown authors, unexpected messages and missing/failed inventories produce no branch/tree/commit writes and explain manual reconciliation, while ordinary refreshes still update.

## 6. Reserved snapshot identifiers

- [x] 6.1 Gather the primary identifiers and `retiredIds` of the authored collections other than the snapshot being replaced and pass them as `reserved` to `preserve_snapshot`; verify a new row whose derived ID collides with a curated entry receives a non-colliding ID.
- [x] 6.2 Reject a snapshot replacement when a new identifier collision cannot be resolved by the existing identity join; verify the rejection reason and that the previous snapshot is unchanged.
- [x] 6.3 Add regression tests for reserved IDs, retired IDs and existing snapshot IDs; verify the existing refresh tests still pass.
- [x] 6.4 Document the reserved-ID rule in `docs/content-model.md` under snapshot refresh; verify the documented behaviour matches the generated snapshot.

## 7. Integration verification

- [x] 7.1 Run `npm run openspec:validate` and verify the change validates without warnings that affect the contract.
- [x] 7.2 Run `python scripts/check_all.py` and verify the content checks, unit tests, crate/profile checks and agent-surface checks pass.
- [x] 7.3 Run the duplicate check and `--fix` against a temporary branch containing the PR 82 fixture, then verify the linked resource passes `check_duplicates` and `check_content`.
- [x] 7.4 Exercise the trusted comment and `/fix-duplicates` workflows against a same-repository test PR; verify the comment is read-only and the command's commit is reviewable, reversible and provenance-bearing. Local/fake verification is accepted; hosted activation is deferred to release preparation by explicit maintainer decision.
- [x] 7.5 Confirm the new workflow is inert until merged to the default branch and that the schedule path cannot reach the fix command.

## 8. Verification repairs and the actual PR 82 content

- [x] 8.1 Bind extracted PR content to its archived SHA, refuse an initial or final head mismatch, and prove the pre-read race cannot commit stale files.
- [x] 8.2 Carry the PR head separately from the checked merge revision in suggestion artifacts and prove collector output renders in the publisher when those SHAs differ.
- [x] 8.3 Reject competing suggestions for one target field and existing keys, validate proposed TOML before writing, and prove refused fixes preserve the original bytes.
- [x] 8.4 Reserve central-register retired identifiers alongside snapshot retiredIds and prove a refresh cannot reuse either kind.
- [x] 8.5 Make local --fix return nonzero whenever no safe change was applied, including a clean no-op, and cover the exit contract.
- [x] 8.6 Include PR 82's dated re3data snapshot and the curated datarepo link with registered provenance; reproduce the original failure and verify the repaired content builds one repository entity.
- [x] 8.7 Run strict OpenSpec validation and complete local checks, reconcile the combined task ledger and original rolling usage entry, retain failure-before/success-after evidence in tests and usage without a standalone report, and keep hosted activation explicitly deferred under task 7.4.
- [x] 8.8 Register the command-generated provenance action before validation and include only that identifier-register change in the same repair commit; prove the complete registered-content path passes, existing and retired IDs remain unchanged, and unrelated missing IDs are not silently registered.
- [x] 8.9 Extract authored validation attachments from the same verified PR head alongside content without executing them; prove content-only extraction fails on missing attachments and the complete archived data validates before committing only the link, provenance and register.
- [x] 8.10 Replace a refresh branch through one atomic ref update that compares the head read before the commit inventory, and create an absent branch only while it stays absent; prove a branch that moves or appears mid-run keeps its newer head with an explained result.
- [x] 8.11 Fail a partial child result in the local runner's job row and exit code as the CI aggregate does, while an explicit `--only` subset whose selected checks all complete keeps its partial report and exits zero; prove both in the runner tests.

## Workflow follow-up

- Retain this original archive after the maintainer-authorized consolidation of PR #102's review fixes.
- Keep the two main capability specs aligned with the six combined delta requirements and preserve the hosted activation boundary in task 7.4.
- Commit, push, review replies, merge and release remain separately authorized actions.
