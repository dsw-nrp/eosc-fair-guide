# Spec Delta

## ADDED Requirements

### Requirement: Content contributors are prepared into the archive record

Release preparation SHALL write `.zenodo.json` `contributors` from the Guide's `[guide] contributors` and
`[[person]]` records: the authored name, a bare ORCID iD when one is recorded and not opted out, the reviewed
organisation's structured ROR affiliation or its English name when it has no ROR, and the DataCite type
`DataCurator`.

#### Scenario: A reviewed contributor is prepared into the archive

- **GIVEN** a reviewed `[guide] contributors` person whose ORCID iD and organisation ROR are recorded
- **WHEN** release preparation writes the requested version and date
- **THEN** `.zenodo.json` carries that person under `contributors` with the bare ORCID iD, the structured ROR affiliation and the type `DataCurator`

#### Scenario: A contributor who declined an ORCID iD

- **GIVEN** a reviewed contributor with no ORCID iD listed
- **WHEN** release preparation writes the archive record
- **THEN** the contributor appears by name with no ORCID field, and no identifier is inferred or invented

### Requirement: Archive preparation leaves curated fields alone

The prepared archive record SHALL keep its curated notes, references, relations and funding text, SHALL change no
shared field other than the version, date and contributors it owns, and SHALL carry no `contributors` field when
the Guide lists none.

#### Scenario: The Guide lists no contributors

- **GIVEN** a Guide whose `[guide] contributors` list is empty
- **WHEN** release preparation writes the archive record
- **THEN** `.zenodo.json` carries no `contributors` field and the prepared file differs from the previous one only in its version and date

#### Scenario: Curated archive fields survive preparation

- **GIVEN** a record with curated notes, related identifiers, references and funding text
- **WHEN** preparation writes contributors alongside the version and date
- **THEN** every curated field keeps its value and the record remains valid under the offline import profile

### Requirement: Contributor credit is reconciled across the Guide and the archive

Citation checks SHALL reconcile `.zenodo.json` contributors with the Guide's `[guide] contributors` in identity,
ORCID iD, affiliation ROR IDs and DataCite type, and SHALL report each difference with its file and entry before
tagging. They SHALL keep requiring Zenodo creators to equal `CITATION.cff` software authors and SHALL NOT require
a `contributors` field in CFF, whose declared schema has none.

#### Scenario: A hand-edited contributor entry drifts

- **GIVEN** a `.zenodo.json` contributor whose name, ORCID iD, affiliation ROR ID or type differs from the reviewed person record
- **WHEN** the repository or release checks run
- **THEN** they fail and name the file and the contributor entry before any tag is created

#### Scenario: A contributor is missing from the archive

- **GIVEN** a Guide listing a person under `[guide] contributors` while `.zenodo.json` names no such contributor
- **WHEN** citation metadata are checked
- **THEN** the missing contributor is reported with the reviewed identity it should carry

#### Scenario: CFF stays a software authorship record

- **GIVEN** `.zenodo.json` that credits content contributors while `CITATION.cff` lists only software authors
- **WHEN** citation metadata are checked
- **THEN** the CFF document validates without a `contributors` field and the creators still match its authors in order
