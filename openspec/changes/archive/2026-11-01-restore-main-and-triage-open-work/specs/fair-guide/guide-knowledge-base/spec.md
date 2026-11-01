# Spec Delta

## MODIFIED Requirements

### Requirement: Every statement traces to a published source

Every advice item and every check SHALL cite at least one entry of the clause ledger. Each ledger entry SHALL
point to a published source: the FAIR analysis, the NRP conditions, the NRP documentation, or a published
paper, dataset or web page. A ledger entry SHALL cite the published work that originally states it; a work that
relays, summarises or links another published work SHALL be cited only for what it adds itself. Unpublished working
material SHALL NOT supply assessment requirements.

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

## ADDED Requirements

### Requirement: A quoted passage records its source's licence as a reviewed licence

A quoted passage SHALL carry the licence its source records, recorded as the one canonical address of a known licence
or mark, one on the reviewed lists that the content check keeps: the six Creative Commons families (BY, BY-SA, BY-ND,
BY-NC, BY-NC-SA, BY-NC-ND) and its public-domain tools (CC0, the Public Domain Mark), GNU paths, OSI pages and SPDX
entries; a licence on none of them, another Creative Commons licence included, SHALL be added to its list through
review before a source records it.

#### Scenario: A source records its licence as text

- **GIVEN** a source or a resource citation whose `license` is not the canonical address of a licence or mark at
  Creative Commons, GNU, OSI or SPDX
- **WHEN** the content checks run
- **THEN** the check fails and names the source or the resource citation, so the value cannot lift the bound unseen

#### Scenario: A source records a licence the Guide has not reviewed

- **GIVEN** a source whose `license` is the canonical SPDX address of a licence on none of the reviewed lists, or a
  Creative Commons licence outside the reviewed families, such as Sampling 1.0
- **WHEN** the content checks run
- **THEN** the check fails, and its message names the lists, with the six Creative Commons families (BY, BY-SA,
  BY-ND, BY-NC, BY-NC-SA, BY-NC-ND) and the two public-domain tools (CC0, the Public Domain Mark), and says that the
  licence is added to its list through review

### Requirement: A licence keeps one canonical address

A Creative Commons address SHALL name a version Creative Commons published, with a port only before 4.0, and BY-NC-ND
1.0 as `by-nd-nc/1.0/`; a licence OSI publishes SHALL be recorded at OSI by its lowercase slug, and an SPDX entry only
for a licence OSI does not publish. The check's message SHALL state these forms.

#### Scenario: A source records another address of the same licence

- **GIVEN** a source whose `license` is a Creative Commons licence's deed or legal-code page, or its address without
  the trailing slash
- **WHEN** the content checks run
- **THEN** the check fails, and its message gives the canonical form as an example, so one licence keeps one address

#### Scenario: A source records an unpublished version, a later port or a second address

- **GIVEN** a source whose `license` names a Creative Commons version that was never published (`by/9.9/`), a port of
  4.0 (`by/4.0/cz/`), BY-NC-ND 1.0 as `by-nc-nd/1.0/`, or the SPDX entry of a licence OSI publishes
- **WHEN** the content checks run
- **THEN** the check fails, and its message states the published versions, that a port is accepted only before 4.0,
  that BY-NC-ND 1.0 is `by-nd-nc/1.0/`, and that a licence OSI publishes is recorded at OSI by its lowercase slug

### Requirement: Quotes from a source without a licence stay within the right of quotation

A passage quoted from a source that records no licence SHALL stay within the right of quotation: at most 200 words
per clause, attributed by its source and locator, with no licence claimed for it. A source outside copyright SHALL
record the Public Domain Mark, and its passages are not bounded.

#### Scenario: A clause quotes a page that records no licence

- **GIVEN** a clause whose source records no licence
- **WHEN** its guidance quotes more than 200 words
- **THEN** the content checks fail and name the clause
- **AND** a quote of up to 200 words with its source and locator passes, as does a longer passage from a source
  that records the Public Domain Mark
- **AND** a quote from it without a locator fails
