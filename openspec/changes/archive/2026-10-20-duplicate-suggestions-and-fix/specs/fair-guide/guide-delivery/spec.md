# Spec Delta

## ADDED Requirements

### Requirement: Aggregate checks report every failure with diagnostics

Required aggregate checks SHALL name every failed or partial check and include bounded diagnostics while preserving lane logs and details. Partial results SHALL fail even at native exit zero, locally as in CI, retaining their partial flag and original evidence. Required diagnostics SHALL precede optional suggestions; optional processing errors SHALL be reported without hiding diagnostics or changing the required-check outcome. The gate SHALL remain failing when required checks fail.

#### Scenario: Two checks fail in one lane
- **GIVEN** content and duplicates both fail in the CPU lane
- **WHEN** the collector reconciles the lane
- **THEN** the aggregate names both checks and includes their error text

#### Scenario: A lane fails before the collector publishes
- **GIVEN** a failed lane with logs and details
- **WHEN** the collector rejects the aggregate
- **THEN** the health artifact contains those logs and details

#### Scenario: A browser check leaves pending cases

- **GIVEN** a required browser result with exit code zero, partial coverage and pending or skipped cases
- **WHEN** the collector publishes the aggregate
- **THEN** the aggregate and check row are failed, its output is shown, and the partial evidence remains inspectable

#### Scenario: The local run meets a partial child

- **GIVEN** a local full run whose browser check exits zero with partial case coverage
- **WHEN** the local runner publishes its report and returns
- **THEN** that row and the run are failed, its output is shown, and the run exits non-zero

#### Scenario: A deliberate local subset completes

- **GIVEN** a local `--only` run whose selected checks all complete
- **WHEN** the run finishes
- **THEN** the unselected checks stay not run, the report remains partial, and the run exits zero

#### Scenario: Optional output cannot be written

- **GIVEN** reconciled check results and an unwritable optional suggestion destination
- **WHEN** optional publication fails
- **THEN** the required report and its original pass/fail outcome remain available and the optional error is reported

### Requirement: The trusted review comment surfaces suggested fixes

The trusted publisher SHALL show bounded exact suggestions and reasons as inert text, never apply them, and keep PR checks read-only. Only reconciled duplicate-lane evidence SHALL supply suggestions, retaining checked revision separately from the current PR head and rejecting stale heads or repositories. Invalid artifacts SHALL be filtered safely. Required evidence rejection SHALL publish no suggestions; upload SHALL admit only successfully generated current-run output.

#### Scenario: A duplicate suggestion is available
- **GIVEN** a completed check run with a safe duplicate suggestion
- **WHEN** the trusted publisher posts the review comment
- **THEN** the comment shows the exact file, table, field and value and does not edit the repository

#### Scenario: The PR head moved
- **GIVEN** suggestion data for an earlier head
- **WHEN** the publisher runs
- **THEN** it skips the stale comment

#### Scenario: Checks ran on the merge commit
- **GIVEN** a checked merge revision that differs from the PR source head
- **WHEN** the collector prepares suggestions for the trusted publisher
- **THEN** it retains both identities and the publisher admits suggestions for the current PR source head

#### Scenario: Wrong lane identity accompanies plausible suggestions

- **GIVEN** a lane with a stale source revision or wrong build identity and a valid-looking duplicates artifact
- **WHEN** the collector rejects the evidence
- **THEN** no suggestion from that run is published under the current PR head

#### Scenario: Required evidence is incomplete

- **GIVEN** a missing lane, duplicated job or invalid required script/case evidence
- **WHEN** aggregate reconciliation fails
- **THEN** the failure diagnostics are retained but no suggestions are published

#### Scenario: A valid duplicate failure produces suggestions

- **GIVEN** reconciled lanes with a failing duplicate check and safe suggestions from its owning lane
- **WHEN** the collector emits the failed aggregate
- **THEN** those suggestions remain available with the checked revision and current PR source head kept separate

#### Scenario: An unrelated directory carries suggestions

- **GIVEN** valid required lanes and an extra directory with a duplicates artifact
- **WHEN** the collector gathers suggestions
- **THEN** it ignores the extra artifact

#### Scenario: A suggestion field is an array or object

- **GIVEN** an otherwise recognizable artifact with a non-string file, table, field or identity value
- **WHEN** the collector validates it
- **THEN** it drops the malformed suggestion and continues emitting required diagnostics

#### Scenario: An earlier suggestions file exists

- **GIVEN** a previous suggestions output and a newly rejected aggregate
- **WHEN** the collector completes its failure path
- **THEN** the previous suggestions are removed, replaced by an empty payload, or excluded from the uploaded review artifact rather than republished

#### Scenario: Invalidating an earlier artifact fails

- **GIVEN** a previous suggestions file and an I/O failure when invalidating it
- **WHEN** the collector handles the optional error
- **THEN** the required report retains its outcome and the upload receives no suggestion path for that run

#### Scenario: A reason contains an external address or mention

- **WHEN** a reason containing a bare URL, Markdown link, image, mention or backtick is rendered
- **THEN** neither publication surface turns the reason into a clickable link, embedded image or notification

### Requirement: A maintainer can request a safe duplicate fix

A trusted fix command SHALL verify current writer access and apply only reviewed safe links on eligible same-repository PRs with requester provenance and changed-field reporting. It SHALL reject forks and schedules, never merge, write the default branch or accept duplicates. Bot diffs SHALL be bounded inert text; uncertain failures SHALL require branch inspection. Refresh SHALL preserve repairs and replace only complete, nonempty lists of the configured App's expected snapshot commits.

#### Scenario: An unauthorised caller requests the fix
- **GIVEN** a comment from an account without current write access
- **WHEN** the trusted handler reads it
- **THEN** it applies nothing and reports the refusal

#### Scenario: A safe suggestion is applied
- **GIVEN** a maintainer's fix request on a same-repository PR with one safe suggestion
- **WHEN** the handler completes
- **THEN** the branch has the link and a provenance action naming the maintainer, and the checks rerun

#### Scenario: The content has an identifier register
- **GIVEN** a safe suggestion against content with a populated identifier register
- **WHEN** the handler validates and commits the repair
- **THEN** the new provenance action is registered and committed with the link, existing and retired IDs remain unchanged, and unrelated unregistered entries still prevent the commit

#### Scenario: Content references authored attachments
- **GIVEN** a safe suggestion against content that references scripts, documentation and icons
- **WHEN** the handler validates the extracted PR data
- **THEN** it checks those attachments from the same verified head without executing PR code and commits only the repaired content, provenance and identifier register

#### Scenario: The group is ambiguous
- **GIVEN** a duplicate group without a safe suggestion
- **WHEN** the handler runs
- **THEN** it changes nothing and reports why human review is required

#### Scenario: The head moved before the handler's first read
- **GIVEN** content extracted from an earlier PR head
- **WHEN** the first validated PR head read differs from the recorded extraction SHA
- **THEN** the handler refuses before applying changes or creating a commit

#### Scenario: A refresh PR contains a duplicate repair by the same App

- **GIVEN** an open refresh PR with a snapshot commit followed by an App-authored duplicate repair
- **WHEN** newer changed source content is published
- **THEN** its link, provenance and registered identifier remain intact and the publisher explains the manual reconciliation

#### Scenario: The branch contains only recognized refresh commits

- **GIVEN** an open proposal whose commits all belong to the configured App and have the expected source-refresh message
- **WHEN** newer changed source content is published
- **THEN** the ordinary refresh update remains available

#### Scenario: Branch ownership is unknown

- **GIVEN** a missing bot identity, unavailable or empty commit inventory, different author, or unexpected message
- **WHEN** publication evaluates whether it may replace the branch
- **THEN** it preserves the branch and reports why automatic replacement was refused

#### Scenario: A repair diff contains a fence and is truncated

- **GIVEN** PR-authored diff context containing Markdown and fence delimiters and exceeding the comment budget
- **WHEN** the success comment is formatted
- **THEN** the diff stays inert inside a closed enclosure and the commit reference remains visible

#### Scenario: Posting the success comment fails after committing

- **GIVEN** the App successfully updates the PR branch and the following comment request fails
- **WHEN** the workflow reports the unexpected failure
- **THEN** it points to the run and asks the maintainer to check the branch state without claiming no change occurred

### Requirement: Refresh branches move only from the inspected head

`source-refresh.yml` publication SHALL change a refresh branch only while it still points at the head whose commits were inspected, and create an absent branch only while it is still absent, through one atomic comparison with that update; a branch that moved is kept and the run reports why.

#### Scenario: The branch moves after its commits were inspected

- **GIVEN** an open refresh branch whose commits were inspected as replaceable
- **WHEN** another writer advances the branch before the publisher replaces it
- **THEN** the atomic comparison refuses the update, the newer head is kept, and the run reports why

#### Scenario: The branch appears after it was read as absent

- **GIVEN** no refresh branch at the time publication read it
- **WHEN** another writer creates it before the publisher does
- **THEN** the creation is refused rather than replacing the new branch, and the run reports why
