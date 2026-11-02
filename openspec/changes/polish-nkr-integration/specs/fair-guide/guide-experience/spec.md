## MODIFIED Requirements

### Requirement: Resource and repository finder

The guide SHALL let users filter resources by station, lens, type, status and language. Repositories and registries
SHALL form one catalogue family regardless of whether their records come from the guide's selection, the FIP
Dashboard, re3data, NKR or FAIRsharing, without duplicates.

#### Scenario: Repository listed in two sources

- **GIVEN** a repository present in both NKR and the re3data snapshot
- **WHEN** the finder lists repositories
- **THEN** the repository appears once, with both sources credited, each as a link to its record

#### Scenario: Records joined through different keys

- **GIVEN** a curated entry that names a re3data record, and an NKR record that names no re3data record but has the same normalised address as the curated entry
- **WHEN** the finder lists repositories
- **THEN** the repository appears once, crediting the curated selection, re3data and NKR, each as a link to its record

#### Scenario: NKR matches a repository listed only by the FIP Dashboard

- **GIVEN** an existing FIP Dashboard repository with no curated or re3data entry, and an NKR record at its exact normalised address
- **WHEN** the finder lists repositories
- **THEN** one entry retains the FIP repository's local identity, functions and verification evidence, takes NKR's non-empty authoritative facts, and credits both source records

#### Scenario: NKR handle and FIP address reach different entries

- **GIVEN** an NKR record whose handle is named by one curated entry and whose address names a different FIP Dashboard-only entry
- **WHEN** the catalogue is built and the duplicate check runs
- **THEN** both reject the ambiguous join and name the NKR record and both entries

#### Scenario: An address that names two entries

- **GIVEN** an NKR record whose normalised address is the address of two different catalogue entries
- **WHEN** the content checks run
- **THEN** they fail, name the NKR record and both entries, and the build joins the record to neither

### Requirement: Repository and registry functions

A function facet SHALL distinguish data and publication deposit from finding metadata, standards, repositories
or support. An entry MAY have several functions. The data-repository chooser SHALL open data deposit, ordered by
domain, institutional and general-purpose repositories, and SHALL leave out repositories that do not accept data yet.
Source, recommendation and verification SHALL remain separate facts; inclusion SHALL NOT imply NRP or EOSC CZ
qualification.

#### Scenario: Dashboard repository and registry

- **GIVEN** repositories and registries imported from the FIP Dashboard alongside other sources
- **WHEN** the user opens the repositories and registries family
- **THEN** every such thing is available there by meaning, with its functions and source records
- **AND** the data-deposit filter excludes metadata directories and standards registries that do not accept data deposits

#### Scenario: Reviewed cross-registry identity

- **GIVEN** reviewed evidence that differently named records in re3data and the FIP Dashboard describe one thing
- **WHEN** the catalogue lists that thing
- **THEN** one entry carries both records, each borrowed identifier still opens it, and source claims retain their provenance
- **AND** a similar name or hostname alone does not merge records

#### Scenario: A repository that does not accept data yet

- **GIVEN** a data repository whose status is planned or in development, or whose NKR record says it is a pilot not accepting data
- **WHEN** a reader opens the data-repository chooser
- **THEN** the repository is not offered there
- **AND** it remains listed in the repositories and registries family with its status and its data-deposit function

### Requirement: NKR records are shown as found

The scheduled source workflow SHALL bring NKR's repository records into a snapshot. Each record SHALL join the
catalogue entry that shares its re3data record, its NKR handle or its exact normalised address, or become an entry of
its own when none matches; a similar name or host alone SHALL NOT join it. A record with no address SHALL join only an
entry that names its NKR handle. For a repository NKR lists, the names, kind, status, keywords and address NKR states
SHALL take precedence over other sources; a value NKR leaves empty SHALL NOT remove another source's value. When NKR
lists no repository, the finder and the repository check SHALL say so with a link to NKR, and SHALL NOT show sample or
simulated records.

#### Scenario: NKR lists no repository

- **GIVEN** NKR lists no repository, so there is no NKR snapshot
- **WHEN** a reader opens the repository catalogue
- **THEN** the guide states that NKR lists no repository yet, with a link to NKR, and offers nothing to load

#### Scenario: NKR's facts take precedence

- **GIVEN** a curated repository entry with status pilot and a Czech name of its own, joined to an NKR record with status development and the name "CzBIRD"
- **WHEN** a reader opens the entry in either language
- **THEN** it is named CzBIRD and shown as in development, dated by the NKR snapshot, with NKR credited
- **AND** the curated functions, operator and abbreviation remain

#### Scenario: NKR leaves the address empty

- **GIVEN** a curated entry with a working address, joined through its reviewed NKR handle to an NKR record whose address is empty
- **WHEN** the catalogue is built
- **THEN** the entry keeps the curated address and still links to its NKR record

#### Scenario: A record without an address and without a reviewed handle

- **GIVEN** an NKR record with an empty address that no entry names by its NKR handle
- **WHEN** the catalogue is built
- **THEN** the record does not join an entry with a similar name, and is listed as its own entry

#### Scenario: An abbreviation already in the name

- **GIVEN** an entry with the abbreviation "MBDB" whose NKR name is "Molecular Biophysics Database - MBDB"
- **WHEN** the entry's name is shown
- **THEN** the abbreviation is not added to it a second time

## ADDED Requirements

### Requirement: A repository not yet public is listed with its NKR record

An NKR repository with no address that joins no entry SHALL be listed with its status and its NKR record as its only
link, and SHALL say in both languages that it has no public address yet. Only a repository whose status is planned or
in development SHALL be listed without an address of its own.

#### Scenario: A repository in development

- **GIVEN** an NKR record with status development, an empty address and no matching entry
- **WHEN** a reader opens the repository catalogue
- **THEN** the repository is listed as in development, its name opens its entry, the entry links to the NKR record and states that the repository has no public address yet
- **AND** the data-repository chooser does not offer it

#### Scenario: An operational repository without an address

- **GIVEN** an NKR record with status production and an empty address that joins no entry
- **WHEN** the snapshot is refreshed
- **THEN** the refresh rejects the snapshot with a reason naming the record, and the previous snapshot stays unchanged
