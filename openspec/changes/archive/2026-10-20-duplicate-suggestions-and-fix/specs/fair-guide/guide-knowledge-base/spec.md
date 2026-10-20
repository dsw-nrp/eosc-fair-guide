# Spec Delta

## ADDED Requirements

### Requirement: Duplicate groups carry an exact, unambiguous suggestion
When the duplicate check reports a group it can resolve without editorial judgement, it SHALL also provide a machine-readable suggestion naming the curated entry, file, table, field and value, and SHALL keep the existing human-readable error. It SHALL mark a suggestion safe only when exactly one curated entry and one registry record share an authoritative key, the curated entry lacks the link, the field placement is known, and no accepted exception applies.

#### Scenario: A new re3data record matches a curated resource
- **GIVEN** a re3data snapshot record and a curated resource sharing an address, with no re3data link on the resource
- **WHEN** the duplicate check runs
- **THEN** the error names both entries and the suggestion names `content/resources.toml`, the `resource.repository` table and `re3data = "<record>"`

#### Scenario: A lookalike is not suggested as a fix
- **GIVEN** two curated entries that share only a name, or two registry records that share an address
- **WHEN** the duplicate check runs
- **THEN** it reports the group without marking any suggestion safe

### Requirement: Safe duplicate suggestions are applied only by explicit human action
A safe suggestion SHALL NOT be applied by scheduled jobs or ordinary pull-request checks. A local fix mode and a maintainer-triggered command MAY apply it, SHALL print or report the exact change, and SHALL require a provenance action naming the person who requested the fix. The duplicate rule and the accepted-group file SHALL NOT be changed automatically.

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
