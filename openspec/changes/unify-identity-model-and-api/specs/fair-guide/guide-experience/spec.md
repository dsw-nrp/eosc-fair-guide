# Spec Delta

## MODIFIED Requirements

### Requirement: The machine-readable side is visible

A page for machines SHALL teach machine-actionability by example, for data stewards first. It SHALL start from what a
reader wants to do and lead to the matching data (the whole knowledge base, one record, a query, an integration,
discovery by harvesters, a saved check result). It SHALL show how the guide applies its own advice, and SHALL explain
and link the crate, the RDF distribution with its query recipes, the API with its documentation and every endpoint,
the IRI pattern, the profile and the licence.

#### Scenario: A data steward wants one record

- **GIVEN** a data steward on the page for machines who wants the data about one principle
- **WHEN** they read what the page offers
- **THEN** they find the record's persistent IRI pattern and API address pattern, a working example, and how the guide itself uses the same means

#### Scenario: A data steward wants to ask a question of the whole graph

- **GIVEN** a data steward who wants the advice for one lens across all stations
- **WHEN** they read what the page offers for queries
- **THEN** they find the RDF distribution, the profile that defines what they may query and a recipe that answers that question

### Requirement: The guide signposts itself

The guide's HTML head SHALL carry FAIR Signposting links: the crate and the RDF distribution (`describedby`), the API
description (`service-desc`), the API documentation (`service-doc`), the licence (`license`), the type of what the
page presents (`type`), the editors (`author`), the guide's persistent identifier (`cite-as`) once it has one, and a
linkset (`linkset`) listing the same links. Every link SHALL be relative to the site, so the guide can move.

#### Scenario: Harvester discovers the API

- **GIVEN** a harvester that reads the guide's home page
- **WHEN** it inspects the typed links in the HTML head, or the linkset they point to
- **THEN** it finds the crate, the RDF distribution, the OpenAPI description, the API documentation and the licence

### Requirement: Identifiers are routed by what they denote

An identifier SHALL be placed without any request where its form or the knowledge base tells what it denotes: a
re3data record or NKR record leads to the repository maturity check, a nanopublication or FIP profile to the FIP
check, a ROR ID to the institution check, an ORCID iD to the identifier helper, and a Guide IRI or address to its
catalogue entry. A generic DOI or Handle SHALL offer one lookup that says what it is before the fitting check.

#### Scenario: A repository's DOI

- **GIVEN** a user who pastes the DOI of a re3data record
- **WHEN** they press Enter
- **THEN** the first result offers the repository maturity check filled in from re3data, not the dataset check

#### Scenario: A Guide IRI

- **GIVEN** a user who pastes `https://w3id.org/eosc-cz/fair-guide/id/stations/licence`
- **WHEN** they press Enter
- **THEN** the first result opens the catalogue entry of the licence station, without any request

### Requirement: Identifiers appear as chips

Wherever the Guide shows an identifier, whether its own ID, a persistent identifier, a record address or a metric or
test ID, it SHALL show it as a chip rather than a bare link. A persistent identifier SHALL keep its scheme and be
shown in full; a chip for an entry of the catalogue SHALL lead to it. A record's own persistent IRI SHALL be labelled
as the record's identifier, distinct from the identifiers of other registries.

#### Scenario: A repository with records in several registries

- **GIVEN** a repository with a re3data record, a FAIRsharing record and a FIP Dashboard record
- **WHEN** its catalogue entry is shown
- **THEN** each record is a chip naming its scheme, and its sources lead to those registries' catalogue entries

#### Scenario: A record's own IRI

- **GIVEN** the catalogue entry of DMP.eosc.cz
- **WHEN** it is shown
- **THEN** its ID chip reads `dmp-eosc`, and a separate chip labelled as the Guide's identifier shows its full persistent IRI

## ADDED Requirements

### Requirement: Catalogue routes follow record addresses

A catalogue entry's route SHALL be its address, `#/<lang>/catalogue/<kind>/<id>`, with the same kind word as the
address, the API and catalogue filters. The page SHALL keep a permanent route, `#/id/<address>`, that opens the
catalogue entry an address names, including for stations and checks, in the reader's language. An unknown address
SHALL say that no entry has it.

#### Scenario: Opening a record from its IRI

- **GIVEN** a reader whose browser was redirected from a station's persistent IRI to `#/id/stations/licence`
- **WHEN** the page opens
- **THEN** it shows the catalogue entry of the licence station in the reader's language, with a link to the station on the path

#### Scenario: An address no entry has

- **WHEN** a reader opens `#/id/resources/no-such-entry`
- **THEN** the page says that no catalogue entry has that address and offers the catalogue search
