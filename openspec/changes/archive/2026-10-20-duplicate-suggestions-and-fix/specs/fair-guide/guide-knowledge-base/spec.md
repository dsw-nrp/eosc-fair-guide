# Spec Delta

## ADDED Requirements

### Requirement: Duplicate groups carry an exact, unambiguous suggestion

The duplicate check SHALL retain existing human-readable errors and emit exact machine-readable links naming the curated entry, record, file, table, field and value. A safe link SHALL require one curated entry and one present registry record sharing an authoritative key, a missing link, a reviewed placement, no accepted exception and unique ownership across all entries and suggestions. Python consumers SHALL share exact placements, with independent Node-validator parity.

#### Scenario: A new re3data record matches a curated resource
- **GIVEN** a re3data snapshot record and a curated resource sharing an address, with no re3data link on the resource
- **WHEN** the duplicate check runs
- **THEN** the error names both entries and the suggestion names `content/resources.toml`, the `resource.repository` table and `re3data = "<record>"`

#### Scenario: A lookalike is not suggested as a fix
- **GIVEN** two curated entries that share only a name, or two registry records that share an address
- **WHEN** the duplicate check runs
- **THEN** it reports the group without marking any suggestion safe

#### Scenario: A registry record already has an owner

- **GIVEN** curated A links registry record R and curated B shares an authoritative key with R
- **WHEN** the duplicate check considers adding the same registry link to B
- **THEN** it reports the duplicate without suggesting that B safely acquire R

#### Scenario: Two unlinked curated entries compete for one record

- **GIVEN** different authoritative keys independently match two curated entries to one registry record
- **WHEN** the complete suggestion set is checked
- **THEN** neither assignment is marked safe and applying fixes changes neither entry

#### Scenario: Individually allowed values form an invalid placement

- **GIVEN** a suggestion contains a known file, table and field but their combination is not valid for its entry kind
- **WHEN** a producer or consumer validates it
- **THEN** it is not emitted, published or applied as a safe suggestion

#### Scenario: An artifact validator drifts

- **WHEN** the Node artifact validator accepts a placement the Python contract rejects, or rejects an allowed placement
- **THEN** the parity check fails and identifies the disagreement

### Requirement: Safe duplicate suggestions are applied only by explicit human action

Safe suggestions SHALL require explicit human action and provenance naming the requester; schedules and ordinary PR checks SHALL NOT apply them. Local repair SHALL validate TOML, replace each target atomically, restore original bytes on handled application or recheck failure, and report the exact diff and provenance reminder only after success. Failure or no-op SHALL return nonzero. The duplicate rule and accepted groups SHALL NOT change automatically.

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

- **WHEN** all safe links are applied and the duplicate recheck passes
- **THEN** the command prints the applied working-tree diff and the provenance reminder and returns zero

### Requirement: New snapshot identifiers are reserved across the Guide
A snapshot refresh SHALL NOT assign a new record identifier that is already used by another Guide entry, and SHALL preserve existing local identifiers across refresh as before. A collision that cannot be resolved by an existing identity join SHALL be rejected for review rather than written.

#### Scenario: A new record would reuse a curated identifier
- **GIVEN** a new snapshot record whose derived local identifier is already owned by a curated entry
- **WHEN** the snapshot is generated
- **THEN** the refresh uses a non-colliding identifier or rejects the replacement with a reviewable reason

#### Scenario: A new record would reuse a retired identifier
- **GIVEN** a derived identifier retired in the central register or a snapshot's retiredIds
- **WHEN** a snapshot is refreshed
- **THEN** the identifier remains reserved and is not assigned to the new record
