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

A catalogue entry's route SHALL be its address under the reader's language and lens,
`#/<lang>/<lens>/catalogue/<kind>/<id>`, with the same kind word as the address, the API and catalogue filters. A
route SHALL open with the lens it names.

#### Scenario: A shared catalogue link keeps its lens

- **GIVEN** the link `#/en/DS/catalogue/resources/dmp-eosc`, shared by a data steward
- **WHEN** a reader whose saved lens is the researcher's opens it
- **THEN** the entry opens with the data-steward lens the link names

### Requirement: One entry route applies the reader's settings

The page SHALL keep one route without reader state, `#/id/<address>`. It SHALL open the catalogue entry an address
names, stations and checks included, in the reader's saved language and lens, or else in Czech with the researcher
lens, and SHALL replace itself with the full route. An unknown address SHALL say that no entry has it.

#### Scenario: Opening a record from its landing page

- **GIVEN** a reader whose saved lens is the data steward's, on the landing page of the licence station
- **WHEN** they follow its link into the Guide, `#/id/stations/licence`
- **THEN** the page shows the catalogue entry of the licence station in their language with the data-steward lens, with a link to the station on the path
- **AND** the page's address becomes `#/<lang>/DS/catalogue/stations/licence`

#### Scenario: An embedded Guide opens a record

- **GIVEN** a Guide embedded in a host page and asked to open `#/id/resources/dmp-eosc`
- **WHEN** it publishes its view to the host page
- **THEN** the host receives the full route with language and lens, in the form the embedding protocol accepts

#### Scenario: An address no entry has

- **WHEN** a reader opens `#/id/resources/no-such-entry`
- **THEN** the page says that no catalogue entry has that address and offers the catalogue search

### Requirement: Every record has a landing page

Every address the build issues SHALL have a static landing page, `id/<address>.html`, readable without JavaScript.
It SHALL present the record in both languages, each marked with its language, with one section per part anchored by
the part's fragment, and SHALL link into the Guide through `#/id/<address>`. A request for an address no record has
SHALL be answered as not found, with a bilingual page that offers the catalogue search.

#### Scenario: A reader without scripts

- **GIVEN** a browser with JavaScript turned off
- **WHEN** it opens the landing page of DMP.eosc.cz
- **THEN** the reader sees the record's name and text in Czech and English, each marked with its language

#### Scenario: A landing page opened at a part

- **WHEN** a reader opens Zenodo's landing page with the fragment `#knav`
- **THEN** it shows the section of Zenodo's KNAV record, with KNAV's wording, licence and retrieval date

#### Scenario: A landing page opened from a local copy

- **GIVEN** the built site opened from `file://`
- **WHEN** a reader opens a landing page and follows its link into the Guide
- **THEN** the Guide opens that entry, and no external request is made

#### Scenario: An address no record has

- **WHEN** a browser requests the landing page of an address the build has not issued
- **THEN** the response is not found, and its page says so in both languages and links to the catalogue search

### Requirement: Landing pages signpost their record

A landing page's head SHALL carry FAIR Signposting links for its record: its persistent IRI (`cite-as`), its API
record (`describedby`), its type (`type`), its licence (`license`) and the Guide as its collection (`collection`).

#### Scenario: A harvester follows a record's typed links

- **GIVEN** a harvester that does not run JavaScript
- **WHEN** it reads the head of DMP.eosc.cz's landing page
- **THEN** it finds the record's persistent IRI as `cite-as` and its API record as `describedby`, without fetching the Guide page
