# Spec Delta

## MODIFIED Requirements

### Requirement: Results carry their format and version

The JSON-LD export and the Markdown summary SHALL declare the result format and its version and the guide's version.
Format revision 4 SHALL record a reader's answer as a quality measurement of its question's persistent IRI and SHALL
name each automated test by its persistent IRI; revisions 1 to 3 SHALL still load. Loading SHALL tell apart a file the
guide did not make, a damaged file, a file in a newer format and a file for an unknown check, each with its own
message. Questions the current guide does not know SHALL be skipped with a note.

#### Scenario: A file from an older guide

- **GIVEN** a saved result that includes a question the current guide no longer has
- **WHEN** a user loads it
- **THEN** the preview opens with the other answers and says how many questions were left out

#### Scenario: A result names its questions and tests persistently

- **GIVEN** a dataset check exported by the current guide, with a reader's answer and a FAIR-Checker result
- **WHEN** a tool reads them
- **THEN** the answer is a quality measurement of the question's persistent IRI, the FAIR-Checker result names its test's persistent IRI, and both resolve wherever the Guide is hosted

#### Scenario: A revision 3 file after the address change

- **GIVEN** a result saved in revision 3, whose test references name `api/tests/<question>.json` at the address it was served from
- **WHEN** a user loads it into the current guide
- **THEN** it loads with its answers and evidence, and its test references are read as references to the same questions
