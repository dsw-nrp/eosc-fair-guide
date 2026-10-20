# Tasks

## 1. Structured duplicate suggestions

- [x] 1.1 Extend the duplicate check's entry model so a reported group can carry a typed suggestion (entry, record, resolution, safe, file, table, field, value, reason) while the existing human-readable error text remains unchanged; verify with the existing duplicate-check unit tests and a new assertion on the PR 82 group.
- [x] 1.2 Implement the safe-suggestion rule: one curated entry and one registry record, an authoritative shared key, a missing link with no conflicting value, a known field placement, no accepted exception, and the record present in the content; verify safe and unsafe fixtures for re3data, FIP Dashboard and KNAV groups.
- [x] 1.3 Write the suggestion collection to `duplicates.json` under `CHECK_REPORT_DIR` when set and to `--report <path>` when requested; verify the file shape, format version and absence of writes in the default text-only run.
- [x] 1.4 Add the PR 82 regression fixture (a re3data record and a curated `datarepo`-like resource) and verify that applying the suggested `re3data` link in memory yields no duplicate error and one content entity.
- [x] 1.5 Document the suggestion shape and the safe/unsafe boundary in `docs/content-model.md` under the one-entry-per-thing rule; verify the documented example matches the emitted fixture.

## 2. Local safe fix

- [x] 2.1 Add `--fix` to the duplicate check to apply only `safe` suggestions in the working tree and print a unified diff; verify a safe fixture changes exactly the named field and an unsafe fixture writes nothing.
- [x] 2.2 Make `--fix` exit non-zero when no safe suggestion applies and print the remaining groups with their human-readable remedy; verify the exit code and output on an ambiguous fixture.
- [x] 2.3 Document the local fix workflow, including the requirement to add a provenance action naming the person, in `docs/content-model.md` or the maintainer documentation; verify the documented commands run as written.

## 3. Aggregate failure diagnostics and suggestion artifacts

- [x] 3.1 Change `check_ci.reconcile` to collect every failed lane result instead of raising on the first, with a bounded output tail per failure; verify a lane fixture with `content` and `duplicates` failures reports both.
- [x] 3.2 Copy the incoming lane `logs/` and `details/` into the health output before emitting a failure report; verify a failed aggregate's artifact contains the failing check log and detail file.
- [x] 3.3 Render every failed check and its bounded failure output in `check_health.markdown`, and copy `details/duplicates.json` into the review-suggestion artifact; verify the summary text and the artifact contents.
- [x] 3.4 Add tests for multiple failures, bounded output, missing lane logs and a passing run that remains unchanged; verify with the check-runner unit tests.
- [x] 3.5 Document the changed failure diagnostics and artifact contents in `docs/design.md`; verify the documented artifact names match the workflow.

## 4. Trusted PR comment suggestions

- [x] 4.1 Include the suggestion artifact in the `guide-review-*` upload and read it in the trusted comment publisher; verify the publisher receives it from a completed check run.
- [x] 4.2 Validate the artifact format, PR head, repository, suggestion count and size, and render a bounded "Suggested fixes" section with escaped text and a fenced diff; verify malformed, oversized and stale-head cases.
- [x] 4.3 Add publisher tests for the suggestion section, escaping, size bound and stale-head skip; verify no repository write occurs in the publisher.
- [x] 4.4 Document the comment section and its read-only boundary in `docs/design.md`; verify the PR check workflow remains read-only.

## 5. Maintainer `/fix-duplicates` command

- [x] 5.1 Add the separate trusted workflow and command parser for exactly `/fix-duplicates`, triggered only by `issue_comment` on pull requests; verify schedules and non-PR comments cannot invoke it.
- [x] 5.2 Reuse the current-permission check and verify the PR is open, same-repository, targets the default branch and has a non-default head; verify an unauthorised caller and a fork request change nothing.
- [x] 5.3 Read the PR head's `content/*.toml` as data and run the default-branch suggestion engine without executing PR code; verify a fixture PR yields the expected safe suggestion and an ambiguous group yields none.
- [x] 5.4 Resolve the commenter to an existing reviewed `[[person]]` through the GitHub identity and refuse when absent; verify no person is guessed and no provenance action is written for an unknown caller.
- [x] 5.5 Apply only safe suggestions, add one provenance action naming the commenter as agent and the command as instrument, and commit to the PR branch through the repository-scoped App without force-pushing or touching the default branch; verify the changed file, the action's results and the commit parent.
- [x] 5.6 Re-read the PR head before committing and abort with a comment when the target content changed; verify a simulated head race leaves the branch unchanged.
- [x] 5.7 Make the command idempotent and non-accepting: an existing link is a no-op, `content/duplicates.toml` is never edited, and the command never merges; verify each case with command tests.
- [x] 5.8 Document the command's trust model, App secrets, person requirement and rollback in `docs/design.md` and the maintainer documentation; verify the documented activation matches the default-branch workflow.

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
- [x] 8.7 Run strict OpenSpec validation and the full local checks, then reconcile the rolling usage entry with the repair evidence; retain the evidence in tests and the usage log without a standalone verification report.
- [x] 8.8 Register the command-generated provenance action before validation and include only that identifier-register change in the same repair commit; prove the complete registered-content path passes, existing and retired IDs remain unchanged, and unrelated missing IDs are not silently registered.
- [x] 8.9 Extract authored validation attachments from the same verified PR head alongside content without executing them; prove content-only extraction fails on missing attachments and the complete archived data validates before committing only the link, provenance and register.

## Workflow follow-up

- Archive the change after the project's review requirements and explicit approval are satisfied.
- Verify the archived specs retain the new requirements and that the workflow remains disabled or enabled as reviewed.
