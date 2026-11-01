# Spec Delta

## MODIFIED Requirements

### Requirement: Credit for content and compilation

Credit SHALL separate the content's basis from the guide's compilation. The footer SHALL credit the authors of the
FAIR analysis the content builds on and SHALL give the guide's own citation as software, naming its compiler as
editor. The about page SHALL list: authors of the analysis, compilation and development, editorial review,
content contributors, AI tools and funding. Each station SHALL show its sources and provenance as one short line
without person names, linking to the full detail.

#### Scenario: Who wrote the content

- **GIVEN** any view
- **WHEN** a user reads the footer
- **THEN** it credits the authors of the FAIR analysis as the basis of the content and gives the guide's citation with its compiler as editor, so no single person appears as the author of everything

#### Scenario: Roles on the about page

- **GIVEN** a user who follows "Who contributed" in the footer
- **WHEN** the about page opens at its roles
- **THEN** a table names the authors of the analysis with their ORCID iDs, the editor, the editorial review, the content contributors with an ORCID link where one is recorded, the tools used and the funding

#### Scenario: A content contributor is not a software author

- **GIVEN** a person credited as a content contributor
- **WHEN** a reader compares the about page with the guide's citation and with `CITATION.cff`
- **THEN** the person appears in the content-contributors row and not as the guide's editor or as a software author, and a contributor without an ORCID iD appears by name only
