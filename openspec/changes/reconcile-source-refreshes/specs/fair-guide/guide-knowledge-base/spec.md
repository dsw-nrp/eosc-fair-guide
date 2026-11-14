## MODIFIED Requirements

### Requirement: New snapshot identifiers are reserved across the Guide

Refresh SHALL reserve identities by their issued kind, scope and identifier. A reviewed source match SHALL attach
to its existing thing. Distinct kinds MAY use the same local word. Unresolved collisions within one kind/scope
SHALL be rejected for review without allocating a counter suffix. Existing identities and retired reservations
SHALL survive refresh; source IDs SHALL retain their issuing schemes and values.

#### Scenario: A new record would reuse a curated identifier

- **GIVEN** a new snapshot record whose derived local identifier is already owned by a curated entry
- **WHEN** the snapshot is generated
- **THEN** a reviewed identity match attaches the source record to that entry without a second thing or counter ID
- **AND** a different or unresolved thing in the same kind/scope requires a reviewed descriptive ID or is rejected

#### Scenario: A new record would reuse a retired identifier

- **GIVEN** an identity retired in the central register or a snapshot's retirement metadata
- **WHEN** a snapshot is refreshed
- **THEN** that identity remains reserved and is not assigned to a different thing
- **AND** an unqualified legacy retirement is retained conservatively rather than guessed into another kind

#### Scenario: A glossary term shares a word with software

- **GIVEN** the Git software resource and a newly imported Heslář term for Git
- **WHEN** their Guide identities are reconciled
- **THEN** `resources/git` and `glossary/git` remain distinct records of their respective kinds
- **AND** the term retains its Heslář source ID without becoming `git-2`

#### Scenario: A glossary term shares a word with a page

- **GIVEN** `pages/provenance` and a newly imported Heslář term for provenance
- **WHEN** the term receives its Guide identity
- **THEN** it uses `glossary/provenance` without changing the page or allocating `provenance-2`

#### Scenario: KNAV describes the existing re3data resource

- **GIVEN** the reviewed KNAV link on the curated re3data resource and the KNAV row whose source ID is `re3data`
- **WHEN** the refreshed graph and API are built
- **THEN** one `resources/re3data` thing has its KNAV record at `resources/re3data#knav`
- **AND** no `resources/re3data-2` thing or Guide collision-counter identifier is introduced

#### Scenario: NKR describes the existing DataRepo repository

- **GIVEN** an NKR record whose reviewed handle or exact normalized address joins the existing DataRepo repository
- **WHEN** the refreshed graph and API are built
- **THEN** one `repositories/datarepo` thing has its NKR record at `repositories/datarepo#nkr`
- **AND** the input identity and emitted source metadata do not introduce a `datarepo-2` Guide identity

#### Scenario: A source match is ambiguous

- **GIVEN** a source record whose reviewed identity keys reach two different things
- **WHEN** refresh or the build reconciles its identity
- **THEN** it reports the source record and conflicting things, creates neither a new numbered thing nor a guessed join,
  and preserves the previous snapshot bytes on refresh rejection

#### Scenario: An identifier contains a genuine published version

- **GIVEN** a reviewed identifier whose digits express a source's actual version rather than collision allocation
- **WHEN** identity validation runs
- **THEN** it retains that meaningful identifier and does not reject it merely for ending in digits

#### Scenario: An established source row joins a curated thing

- **GIVEN** a source row with an established precise local key and a reviewed join to a curated thing
- **WHEN** refresh carries the row forward
- **THEN** it preserves the row's local key and genuine source handle while projection attaches its record to the thing
- **AND** a canonical thing's more general name does not replace a versioned licence key such as `cc-by-4-0`

#### Scenario: Similar labels describe different things

- **GIVEN** a specific licence and a licence overview, or repository software and a deployed repository
- **WHEN** their identities and source observations are reconciled
- **THEN** their records describe separate things and a shared publisher, name or implementation does not join them
- **AND** verification scoped to a deployed instance stays on its source record and does not certify the software

#### Scenario: A reviewed software classification differs from a native repository label

- **GIVEN** a curated software entry and a linked Dashboard record whose native type is `repository`
- **WHEN** catalogue and API data are generated
- **THEN** the software retains its reviewed Guide type and is not listed as a deposit repository
- **AND** the source record retains its native classification, wording and verification as source claims

## ADDED Requirements

### Requirement: Refresh reserves inferred organisation addresses

Source refresh SHALL reserve the existing addresses of organisations inferred from named publishers, operators,
developers and infrastructure hosts, using the build's shared identity resolution. The identity-only projection
SHALL not require complete page or assessment content. A colliding unjoined source organisation SHALL be refused
for review before snapshot replacement, without numeric counters or implicit source joins by name.

#### Scenario: An incoming organisation competes with an inferred agent

- **GIVEN** an existing inferred organisation at `organizations/carpentries`
- **WHEN** a new unjoined source row would allocate that address
- **THEN** refresh refuses the collision with a reviewable diagnostic and preserves the prior snapshot
- **AND** the full and identity-only projections agree on the existing organisation addresses

### Requirement: Dashboard registry classification survives source reclassification

A FIP Dashboard record classified as `registry` SHALL retain its native catalogue type and the reviewed FIP
Registry classification on the source record. Reclassification SHALL NOT move its described thing's identity,
type the source record as that thing, or imply deposit capability or verification not supported by the source.

#### Scenario: FAIRsharing and NMA become registries in the Dashboard

- **GIVEN** the refreshed FAIRsharing and NMA records change their Dashboard type from `repository` to `registry`
- **WHEN** their crate, API and catalogue records are generated
- **THEN** both keep their existing thing identities and native source classification
- **AND** their Dashboard source records retain the FIP Registry classification as catalogue records
- **AND** the records are not themselves classified as repository or service entities
