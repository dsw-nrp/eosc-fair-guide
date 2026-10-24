# Spec Delta

## MODIFIED Requirements

### Requirement: Statuses are dated

Every status of a service or resource SHALL use the five-level vocabulary (operational, pilot, in
development, planned, prospective) and SHALL carry an as-of date. A status older than the configured freshness
threshold SHALL be reported.

#### Scenario: Stale status

- **GIVEN** a resource whose status as-of date is older than the freshness threshold
- **WHEN** the scheduled health job runs
- **THEN** the maintenance digest lists the resource and its last verified date for maintainer triage

### Requirement: Safe duplicate suggestions are applied only by explicit human action

Safe suggestions SHALL require explicit human action and provenance naming the requester; schedules and ordinary PR checks SHALL NOT apply them. Local repair SHALL validate TOML, replace each target atomically, restore original bytes on handled application or recheck failure, and after success report the exact diff including its provenance action and identifier registration. Failure or no-op SHALL return nonzero. The duplicate rule and accepted groups SHALL NOT change automatically.

#### Scenario: Scheduled refresh meets a duplicate

- **GIVEN** a scheduled source refresh adds a record that duplicates a curated entry
- **WHEN** the refresh completes
- **THEN** the snapshot proposal is unchanged by automation and the suggestion is reported for human action

#### Scenario: Authoritative matches compete for the same field

- **GIVEN** two registry records match one curated entry through different authoritative keys
- **WHEN** the duplicate check proposes links to the same target field
- **THEN** it marks neither competing value safe and no fix changes that field

#### Scenario: A target key already exists

- **GIVEN** a target table already contains the suggested field, even with an empty value
- **WHEN** a fix is considered
- **THEN** no duplicate key is inserted and the original file remains valid TOML

#### Scenario: No local safe change applies

- **GIVEN** content with no applicable safe suggestion
- **WHEN** the local fix command runs
- **THEN** it leaves the content unchanged and returns nonzero

#### Scenario: A maintainer applies the fix

- **GIVEN** a maintainer requests the fix on a same-repository pull request
- **WHEN** the safe suggestion is applied
- **THEN** the change is committed to that branch with a provenance action naming the maintainer, and the checks rerun

#### Scenario: A replacement fails

- **GIVEN** a safe link and a failure while writing its temporary replacement or replacing its target
- **WHEN** the local repair handles the error
- **THEN** the original target bytes are preserved, temporary files are cleaned up and the command reports failure

#### Scenario: Rechecking the completed repair fails

- **GIVEN** one or more files were changed by local duplicate repair
- **WHEN** content loading fails or duplicate errors remain during the final recheck
- **THEN** every changed target is restored to its original bytes and the command returns nonzero

#### Scenario: A later target fails after an earlier target changed

- **GIVEN** multiple safe links affect different files
- **WHEN** applying a later link raises an error
- **THEN** the earlier changes are also restored and no applied-success message is printed

#### Scenario: Cleanup fails after a target was replaced

- **GIVEN** a target was replaced successfully and the following temporary-file cleanup raises an error
- **WHEN** the local repair handles the error
- **THEN** the replaced target is already tracked for rollback and its original bytes are restored without a post-write discovery read

#### Scenario: A valid local repair completes

- **WHEN** all safe links are applied and the content and duplicate rechecks pass, including the identifier register
- **THEN** the command prints the applied working-tree diff, which contains the links, one provenance action naming the responsible person and that action's registration, and returns zero

## ADDED Requirements

### Requirement: Local duplicate repair resolves a reviewed responsible person

Local repair SHALL record as responsible the reviewed person given with `--person` or, without it, the single
reviewed person whose GitHub account or commit name matches the local Git identity. An unknown or ambiguous identity
SHALL write nothing, return nonzero and name both the `--person` option and the identity-review procedure. Repair
SHALL never invent a person.

#### Scenario: The local Git identity is reviewed

- **GIVEN** a local Git user name listed in one person's reviewed `commitNames`
- **WHEN** the contributor runs the local fix without `--person`
- **THEN** the provenance action names that person and the output says how the person was resolved

#### Scenario: A person is named explicitly

- **WHEN** the contributor runs the local fix with `--person` and a reviewed person ID
- **THEN** that person is recorded regardless of the local Git identity

#### Scenario: The identity is unknown or ambiguous

- **WHEN** the local Git identity matches no reviewed person or more than one
- **THEN** the command writes nothing, returns nonzero and names the `--person` option and the procedure for adding a reviewed identity
