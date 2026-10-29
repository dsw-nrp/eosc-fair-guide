# Spec Delta

## MODIFIED Requirements

### Requirement: Every statement traces to a published source

Every advice item and every check SHALL cite at least one entry of the clause ledger. Each ledger entry SHALL
point to a published source: the FAIR analysis, the NRP conditions, the NRP documentation, or a published
paper, dataset or web page. A ledger entry SHALL cite the published work that originally states it; a work that
relays, summarises or links another published work SHALL be cited only for what it adds itself. Unpublished
working material SHALL NOT supply assessment requirements.

#### Scenario: Advice without a source

- **GIVEN** a pull request that adds an advice item with no ledger citation
- **WHEN** the content checks run
- **THEN** the check fails and names the item

#### Scenario: Citation of an unknown source

- **GIVEN** an advice item that cites an identifier missing from the ledger
- **WHEN** the content checks run
- **THEN** the check fails and names the unknown identifier

#### Scenario: A page relays a published checklist

- **GIVEN** a web page that summarises a published checklist and links to it
- **WHEN** a clause records the checklist's recommendation
- **THEN** the clause cites the checklist, with its DOI where it has one, and quotes the checklist's wording
- **AND** the page is cited only for a statement of its own
