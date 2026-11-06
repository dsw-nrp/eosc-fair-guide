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
shown in full, without a label that repeats what the identifier states; a chip for an entry of the catalogue SHALL
lead to it. Every catalogue entry SHALL show its own persistent IRI first among its identifiers.

#### Scenario: A repository with records in several registries

- **GIVEN** a repository with a re3data record, a FAIRsharing record and a FIP Dashboard record
- **WHEN** its catalogue entry is shown
- **THEN** each identifier is a chip that shows it in full and carries no label, and its sources lead to those registries' catalogue entries

#### Scenario: A record's own IRI

- **GIVEN** the catalogue entry of DMP.eosc.cz
- **WHEN** it is shown
- **THEN** its ID chip reads `dmp-eosc`, and its first identifier chip shows its full persistent IRI without a label

#### Scenario: Every kind shows its IRI

- **GIVEN** the catalogue entries of a question, a requirement, a life-cycle stage, a model layer and a content change
- **WHEN** each is shown
- **THEN** each shows its own persistent IRI among its identifiers

### Requirement: Resource and repository finder

The guide SHALL let users filter resources by station, lens, type, status and language. Repositories SHALL form one
catalogue family regardless of whether their records come from the guide's selection, the FIP Dashboard, re3data,
NKR or FAIRsharing, without duplicates. A registry SHALL be a resource, listed and filtered with the resources.

#### Scenario: Repository listed in two sources

- **GIVEN** a repository present in both NKR and the re3data snapshot
- **WHEN** the finder lists repositories
- **THEN** the repository appears once, with both sources credited, each as a link to its record

#### Scenario: Records joined through different keys

- **GIVEN** a curated entry that names a re3data record, and an NKR record that names no re3data record but has the same normalised address as the curated entry
- **WHEN** the finder lists repositories
- **THEN** the repository appears once, crediting the curated selection, re3data and NKR, each as a link to its record

#### Scenario: NKR matches a repository listed only by the FIP Dashboard

- **GIVEN** an existing FIP Dashboard repository with no curated or re3data entry, and an NKR record at its exact normalised address
- **WHEN** the finder lists repositories
- **THEN** one entry retains the FIP repository's local identity, functions and verification evidence, takes NKR's non-empty authoritative facts, and credits both source records

#### Scenario: NKR handle and FIP address reach different entries

- **GIVEN** an NKR record whose handle is named by one curated entry and whose address names a different FIP Dashboard-only entry
- **WHEN** the catalogue is built and the duplicate check runs
- **THEN** both reject the ambiguous join and name the NKR record and both entries

#### Scenario: An address that names two entries

- **GIVEN** an NKR record whose normalised address is the address of two different catalogue entries
- **WHEN** the content checks run
- **THEN** they fail, name the NKR record and both entries, and the build joins the record to neither

#### Scenario: A registry among the resources

- **GIVEN** NKR, a registry the guide curates with the data-repository function of finding repositories
- **WHEN** a reader opens the catalogue
- **THEN** NKR is listed once, among the resources, with its functions shown, and not in the repositories family

### Requirement: Repository and registry functions

A function facet SHALL distinguish data and publication deposit from finding metadata, standards, repositories
or support. An entry MAY have several functions. The data-repository chooser SHALL open data deposit, ordered by
domain, institutional and general-purpose repositories, and SHALL leave out repositories that do not accept data yet.
Source, recommendation and verification SHALL remain separate facts; inclusion SHALL NOT imply NRP or EOSC CZ
qualification.

#### Scenario: Dashboard repository and registry

- **GIVEN** repositories and registries imported from the FIP Dashboard alongside other sources
- **WHEN** the user opens the repositories family and the resources
- **THEN** every such thing is available by meaning, a repository among the repositories and a registry among the resources, each with its functions and source records
- **AND** the data-deposit filter excludes metadata directories and standards registries that do not accept data deposits

#### Scenario: Reviewed cross-registry identity

- **GIVEN** reviewed evidence that differently named records in re3data and the FIP Dashboard describe one thing
- **WHEN** the catalogue lists that thing
- **THEN** one entry carries both records, each borrowed identifier still opens it, and source claims retain their provenance
- **AND** a similar name or hostname alone does not merge records

#### Scenario: A repository that does not accept data yet

- **GIVEN** a data repository whose status is planned or in development, or whose NKR record says it is a pilot not accepting data
- **WHEN** a reader opens the data-repository chooser
- **THEN** the repository is not offered there
- **AND** it remains listed in the repositories family with its status and its data-deposit function

### Requirement: Kind-specific facets remain inside their family

The repository function facet SHALL appear under the Repositories heading. Changing the selected family SHALL NOT
move the shared Kind facet.

#### Scenario: Reader switches catalogue families

- **GIVEN** a reader switching from resources to repositories
- **WHEN** the repository function choices appear
- **THEN** they appear inside that family section and the Kind facet retains its shared position

## ADDED Requirements

### Requirement: An entry credits the catalogues that supplied it

A catalogue entry's sources SHALL name the Guide's selection where the entry is curated and the catalogue of every
registry record the entry holds, each leading to that catalogue's entry with the date of its snapshot. A registry
that only identifies the entry, without a record the Guide holds, SHALL appear among the identifiers and SHALL NOT be
credited as a source.

#### Scenario: A repository several catalogues supply

- **GIVEN** Zenodo, which the guide curates and which the KNAV catalogue and the FIP Dashboard also record
- **WHEN** its catalogue entry is shown
- **THEN** its sources name the guide's selection, the KNAV catalogue and the FIP Dashboard, each leading to that catalogue's entry with its snapshot date

#### Scenario: A curated resource a registry also records

- **GIVEN** a curated resource with a KNAV record and no other registry record
- **WHEN** its catalogue entry is shown
- **THEN** its sources name the guide's selection and the KNAV catalogue

#### Scenario: A registry that only identifies the entry

- **GIVEN** a curated repository that names its NKR handle while no NKR snapshot holds its record
- **WHEN** its catalogue entry is shown
- **THEN** the NKR record page appears among its identifiers, and NKR is not among its sources

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
