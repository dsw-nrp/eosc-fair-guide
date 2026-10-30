# Spec Delta

## MODIFIED Requirements

### Requirement: Every statement traces to a published source

Every advice item and every check SHALL cite at least one entry of the clause ledger. Each ledger entry SHALL
point to a published source: the FAIR analysis, the NRP conditions, the NRP documentation, or a published
paper, dataset or web page. A ledger entry SHALL cite the published work that originally states it; a work that
relays, summarises or links another published work SHALL be cited only for what it adds itself. A quoted passage
SHALL carry the licence its source records, recorded as the one canonical address of that licence or mark at
Creative Commons, GNU, OSI or SPDX. A passage quoted
from a source that records no licence SHALL stay within the right of quotation: at most 200 words per clause,
attributed by its source and locator, with no licence claimed for it. A source outside copyright SHALL record the
Public Domain Mark, and its passages are not bounded. Unpublished working material SHALL NOT supply assessment
requirements.

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

#### Scenario: A clause quotes a page that records no licence

- **GIVEN** a clause whose source records no licence
- **WHEN** its guidance quotes more than 200 words
- **THEN** the content checks fail and name the clause
- **AND** a quote of up to 200 words with its source and locator passes, as does a longer passage from a source
  that records the Public Domain Mark
- **AND** a quote from it without a locator fails

#### Scenario: A source records its licence as text

- **GIVEN** a source or a resource citation whose `license` is not the canonical address of a licence or mark at
  Creative Commons, GNU, OSI or SPDX
- **WHEN** the content checks run
- **THEN** the check fails and names the source or the resource citation, so the value cannot lift the bound unseen

#### Scenario: A source records another address of the same licence

- **GIVEN** a source whose `license` is a Creative Commons licence's deed or legal-code page, or its address without
  the trailing slash
- **WHEN** the content checks run
- **THEN** the check fails, and its message gives the canonical form as an example, so one licence keeps one address
