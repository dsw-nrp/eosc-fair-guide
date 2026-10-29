# Spec Delta

## ADDED Requirements

### Requirement: Catalogue entries show everything their records carry

Every catalogue entry SHALL show each field its record carries, or the catalogue SHALL exclude that field with a
stated reason. A count SHALL NOT replace the items it counts, and a relation SHALL show on both of its ends. Each
entry SHALL lead to the dated content changes that produced or altered it, which the catalogue's list of changes
holds, so that no entry grows with each change.

#### Scenario: A content change names its people and tools

- **GIVEN** a reader opening a content change in the catalogue
- **WHEN** its entry is shown
- **THEN** it names the person responsible and each tool with its kind and version, an AI model appearing as a tool and never as an author
- **AND** it lists every requirement and source consulted and every item changed, grouped by kind, each linking to its entry, station or page

#### Scenario: A check question shows how it is answered

- **GIVEN** a reader opening a check question in the catalogue
- **WHEN** its entry is shown
- **THEN** it shows who puts it right, when it applies, whether "not applicable" is offered and which sources pre-fill it, with their limits

#### Scenario: A FIP profile shows its declarations

- **GIVEN** a reader opening a FIP profile in the catalogue
- **WHEN** its entry is shown
- **THEN** each declaration appears with its principle, its enabling resource and its status
- **AND** the table can be read across the entry's full width and on a page of its own
- **AND** that resource's entry lists the profile among those that declare it

#### Scenario: An entry leads to the changes that produced it

- **GIVEN** any catalogue entry covered by provenance
- **WHEN** its entry is shown
- **THEN** its corner counts the content changes that produced or altered it and leads to them in the catalogue, each
  dated and leading to the change's entry
- **AND** the entry itself does not list them

#### Scenario: A new field cannot hide

- **GIVEN** a record that gains a field its kind's entry neither shows nor excludes with a reason
- **WHEN** the checks run
- **THEN** they fail and name the kind and the field

### Requirement: Shared facts appear in the same place on every kind

Across kinds, an entry's byline SHALL name who made the work, and labelled rows SHALL name who operates, develops or
provides it. A work's own licence SHALL be a row; the licence of a quoted text SHALL sit beside the quote and be named
from the data. Dates SHALL sit in the details line, a status SHALL be one badge with icon, text and as-of date, and
qualified lists SHALL be rows. The catalogue's own labels SHALL NOT address the reader, since it is not read in a role.

#### Scenario: The same property in the same place

- **GIVEN** a reader comparing a large research infrastructure with a repository in the catalogue
- **WHEN** both entries are shown
- **THEN** each shows its host or operator as an Operated by row

#### Scenario: Two licences kept apart

- **GIVEN** a cited source with a licence and a glossary term that quotes a definition
- **WHEN** both entries are shown
- **THEN** the source shows a Licence row, and the term shows its definition's licence beside the definition, named as the data records it

#### Scenario: A question the self-check puts to the reader

- **GIVEN** a check question that the self-check's reader, the researcher, puts right
- **WHEN** its catalogue entry is shown
- **THEN** who puts it right is named by that role, as the Researcher lens names it, not as "you"

#### Scenario: Status reads without colour

- **GIVEN** a test's health and a FIP declaration's status
- **WHEN** they are shown
- **THEN** each carries an icon, a text and, where recorded, an as-of date
