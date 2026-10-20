# Spec Delta

## ADDED Requirements

### Requirement: Aggregate checks report every failure with diagnostics
When required checks fail, the aggregate SHALL name every failed check, not only the first, and SHALL include a bounded tail of each failure's output in the CI summary. The collector SHALL preserve the lane logs and details in the uploaded health artifact on failure. A failed aggregate SHALL remain a failure; this requirement changes diagnostics, not the gate.

#### Scenario: Two checks fail in one lane
- **GIVEN** content and duplicates both fail in the CPU lane
- **WHEN** the collector reconciles the lane
- **THEN** the aggregate names both checks and includes their error text

#### Scenario: A lane fails before the collector publishes
- **GIVEN** a failed lane with logs and details
- **WHEN** the collector rejects the aggregate
- **THEN** the health artifact contains those logs and details

### Requirement: The trusted review comment surfaces suggested fixes
The review-comment publisher SHALL read bounded suggestion data from the check artifacts and SHALL add a "Suggested fixes" section to its own comment. It SHALL escape the text, state the reason, keep the PR check workflow read-only, and skip a stale head. It SHALL NOT apply the suggestion.

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

### Requirement: A maintainer can request a safe duplicate fix
A trusted command SHALL allow a maintainer with current write access to apply only safe duplicate suggestions on a same-repository pull request. It SHALL verify the caller, reject forks and schedules, apply only the reviewed safe suggestions, add a provenance action naming the caller, commit to the PR branch with the repository-scoped App, and report the changed fields. It SHALL NOT merge, push to the default branch, or accept a duplicate.

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
