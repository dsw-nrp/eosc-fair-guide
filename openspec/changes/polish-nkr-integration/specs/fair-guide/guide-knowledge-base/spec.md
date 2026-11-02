## MODIFIED Requirements

### Requirement: Repository names are harvested and reviewed

The re3data snapshot SHALL keep the names re3data tags as Czech beside the English name and the abbreviations.
Curated entries SHALL correct or complete Czech names and abbreviations from the repository's own site, and the
curated form SHALL take precedence, except for a repository NKR lists: its NKR name (Czech from the repository name,
English from the English alternative name, otherwise the repository name) SHALL take precedence, and a curated
abbreviation SHALL still apply.

#### Scenario: re3data lacks the Czech name

- **GIVEN** re3data lists "CSDA" as an English additional name and no Czech name for the Czech Social Science Data Archive
- **WHEN** the catalogue is built
- **THEN** the curated entry supplies "Český sociálněvědní datový archiv" and "ČSDA", and "CSDA" remains the English abbreviation

#### Scenario: NKR names a repository in both languages

- **GIVEN** an NKR record named "Repozitář herbářových sbírek" with the English alternative name "Herbarium Collections Repository"
- **WHEN** the catalogue is built
- **THEN** Czech readers see the Czech name and English readers the English name

### Requirement: Catalogue slugs use meaningful local names

Catalogue ID slugs SHALL omit grammatical particles and prefer official abbreviations or specific source URL words. Generic registry/resolver and interface paths SHALL NOT determine a slug. When neither yields a useful name, the Guide SHALL assign concise meaningful name words without truncating a word. These are one-time local assignments; refresh SHALL preserve them.

#### Scenario: A source URL changes after local assignment

- **WHEN** a record receives a local slug from an abbreviation or source URL
- **THEN** later source changes preserve the assigned slug and cannot change the Guide identity

#### Scenario: An NKR record page does not name a repository

- **GIVEN** a new NKR record whose record page is `https://repo.cz/objects/20.500.14818/jgu5fyqf` and whose own address is `https://herbarium.biodiversity.cz`
- **WHEN** the snapshot is refreshed
- **THEN** the record's slug comes from the repository's own address or name, such as `herbarium`, never from the NKR handle
- **AND** its address is routed by its NKR type, for a disciplinary repository under `repo/dom`

## ADDED Requirements

### Requirement: NKR statuses map onto the dated vocabulary

A repository NKR lists SHALL take its status from NKR, mapped onto the five-level vocabulary and dated by the
snapshot's retrieval date: intended as planned; development and test as in development; both pilot states as pilot;
production as operational. A decommissioned record SHALL NOT be listed, and NKR's release date SHALL NOT be used.

#### Scenario: Statuses from one snapshot

- **GIVEN** an NKR snapshot retrieved on 2026-11-01 with records in production, pilot accepting data and development
- **WHEN** the catalogue is built
- **THEN** they are shown as operational, pilot and in development, each as of 1 November 2026

#### Scenario: A decommissioned record

- **GIVEN** an NKR record with status decommissioned whose address matches a curated entry
- **WHEN** the catalogue is built
- **THEN** no entry is added for the record, the curated entry keeps its own status, and the health report names the record for maintainer review

### Requirement: The NKR snapshot keeps only fields its record can carry

The NKR snapshot SHALL keep the reviewed fields that NKR's published Repository schema defines, including status and
alternative names, and SHALL record only whether a contact exists, never the address. A field a check pre-fills from
NKR that the schema does not define SHALL be named in the refresh report and not requested.

#### Scenario: A pre-filled field the record no longer carries

- **GIVEN** a check that pre-fills `pidType` from NKR and an NKR Repository schema without `pidType`
- **WHEN** the NKR snapshot is refreshed
- **THEN** the snapshot's field list omits `pidType` and the refresh report names it as not carried by the record

#### Scenario: The administrator role from a contact

- **GIVEN** an NKR record with a main contact
- **WHEN** a repository administrator fills the gate check from that record
- **THEN** the administrator-role item is answered from NKR and no contact address appears in the snapshot, the page or the export

### Requirement: The duplicate check covers NKR records

The duplicate check SHALL read NKR snapshot records and treat an NKR handle and an NKR record's exact normalised
address as keys that join it to one entry. An NKR record whose keys name two different entries SHALL be reported.

#### Scenario: A harvest that repeats curated repositories

- **GIVEN** NKR records for repositories that the curated selection and the re3data snapshot already list at the same addresses
- **WHEN** the duplicate check runs
- **THEN** each record joins its entry and no duplicate is reported

#### Scenario: Two entries claim one NKR record

- **GIVEN** two curated entries that name the same NKR handle
- **WHEN** the duplicate check runs
- **THEN** it fails and names both entries and the handle

### Requirement: A repository link may be its NKR record only while it is not public

The repository record in the API and the knowledge-base profile SHALL require an HTTPS address, except for a repository
whose status is planned or in development and which links an NKR record. The API description SHALL state that
exception.

#### Scenario: Validating a repository in development

- **GIVEN** a built site with a repository in development that has no address and links its NKR record
- **WHEN** the API and profile checks run
- **THEN** both accept it

#### Scenario: An operational repository without an address

- **GIVEN** a built site with an operational repository that has no address
- **WHEN** the API and profile checks run
- **THEN** both reject it and name the repository
