# Spec Delta

## MODIFIED Requirements

### Requirement: Static read-only API

The guide SHALL publish a read-only API without a backend under a versioned path (`api/v1/`): for each kind, a list
whose entries carry the fields a client filters on, and one record per entity at its address. Advice SHALL be a kind
of its own. Responses SHALL carry language maps and a JSON-LD context and SHALL refer to shared vocabulary terms
rather than repeat them. An OpenAPI 3.1 document with a relative server address SHALL describe one templated
operation per kind and response.

#### Scenario: A consumer reads a principle

- **GIVEN** a service that requests the R1.1 principle from the guide's API
- **WHEN** it reads the response
- **THEN** it receives the principle with its advice per lens, the stations that address it and the check items that test it, as JSON with a JSON-LD context

#### Scenario: A consumer filters one list

- **GIVEN** a service that needs the researcher advice at the licence station at level L0
- **WHEN** it fetches the advice list once
- **THEN** every entry carries its station, lens, level, principles and text, so the service filters the list without fetching any record

#### Scenario: The description names templates

- **WHEN** a developer opens the OpenAPI description
- **THEN** each kind has one list and one record operation with a path parameter, every published record file matches one described template, and no operation names a single record

### Requirement: Content addressed relative to the site

API files SHALL link the guide's own records and each other relative to the referring file, never by the site's
address. An entity's identity SHALL be its persistent IRI under the Guide namespace. Saved results SHALL name tests
by persistent IRI; other outbound links SHALL use the page's serving address. Runtime links SHALL use the Guide
window's location and channel path, not an iframe parent's. Offline use SHALL keep references usable without
exposing filesystem paths.

#### Scenario: The guide moves

- **GIVEN** the guide published at a new address
- **WHEN** a consumer follows a link in an API record, or the test IRI in a result exported before the move
- **THEN** it reaches the record at the new address, without the guide being rebuilt for it

#### Scenario: The Guide is embedded at a repository subpath

- **GIVEN** the Guide runs in an iframe under a different origin or path from its parent
- **WHEN** a reader opens an API reference or share link
- **THEN** the link follows the Guide's current origin and channel path, not the parent or a predicted public hostname

#### Scenario: The Guide is opened from a local file

- **WHEN** a reader navigates or exports references from `file://`
- **THEN** local/relative behavior remains usable, no filesystem path is represented as a public identifier, and no external request is made on load

### Requirement: Checks published as FTR definitions

Each check SHALL be an FTR benchmark in the knowledge graph and the API, its questions FTR metrics, and each question's
manual test an FTR test with its own persistent IRI (`tests/self-check/<question>`). The API SHALL use the graph's
types and property names without renaming them, so that the test references in an exported result set resolve to
the same definitions in both.

#### Scenario: Exported result resolves

- **GIVEN** a self-check result set exported from the guide
- **WHEN** a tool follows a result's test reference
- **THEN** it reaches the item's FTR test definition in the published API

#### Scenario: The graph carries the FTR definitions

- **WHEN** a consumer queries the published graph for FTR tests
- **THEN** it finds every manual test and every curated automated test, each linked to the metric it implements and that metric to its benchmark

### Requirement: One entry per real-world thing

Curated content SHALL describe each real-world thing once, in one entry that carries every role it plays, and a
content identifier SHALL name exactly one entity. Two curated entries SHALL NOT share a web address or a DOI. The
graph SHALL hold one node per thing; a registry's record about it SHALL be a record attached to that node, never a
peer node. The content checks SHALL enforce these rules and SHALL report entries that nothing uses.

#### Scenario: A duplicate in a pull request

- **GIVEN** an editor who adds a source with the address of an existing resource
- **WHEN** the content checks run
- **THEN** they fail and name both entries

#### Scenario: A repository listed by two registries

- **GIVEN** Zenodo, which the guide curates and which KNAV and the FIP Dashboard also list
- **WHEN** the graph is built
- **THEN** it holds one Zenodo node with one persistent IRI, and the KNAV and FIP Dashboard records are attached to it as records about it

### Requirement: Prose references name catalogue entries

A prose reference SHALL name a published catalogue entry by its address, `[[<kind>/<id>|phrase]]`, or a kind's
catalogue list by the kind word. A content field that can name records of several kinds SHALL name a record by its
address too. Targets SHALL derive from the same identity projection as IRIs, API records and routes. The content
checks SHALL reject any other reference and name the record whose ID it ends with, where one has it.

#### Scenario: A catalogue tool named in a step

- **GIVEN** a step whose text names a tool the KNAV catalogue lists and no guide entry stands for
- **WHEN** the step is shown
- **THEN** the reference is one the content checks accept, and it links to that tool's catalogue entry

#### Scenario: A reference without a kind

- **GIVEN** an advice text that references a station as `[[licence|...]]`
- **WHEN** the content checks run
- **THEN** they fail, name the item and give the address form `[[stations/licence|...]]`

#### Scenario: A field that names records of several kinds

- **GIVEN** a model association whose target is the question `dataset.01`
- **WHEN** the content checks run
- **THEN** they accept the target `questions/dataset.01` and reject the bare `dataset.01`, naming the address form

#### Scenario: The Guide's profile named in prose

- **GIVEN** a text that names the Guide's profile
- **WHEN** the page is shown
- **THEN** the reference names the section of the machines page that presents the profile, and no reference names a target that is neither a record nor a kind

### Requirement: Catalogue addresses are guide-issued

Each catalogue record SHALL own a locally stored identifier and one address, `<kind>/<id>`, emitted once by the build
for IRIs, API, routes, references and exports. The kind SHALL be a plural English word from one vocabulary. A scope
segment, `<kind>/<scope>/<id>`, SHALL appear only where it is part of the identity; a classification SHALL NOT be part
of an address. Chips SHALL show the record ID. Complete addresses SHALL NOT be duplicated in a per-record register.

#### Scenario: A repository the guide takes from re3data

- **GIVEN** a repository re3data lists and the guide does not curate
- **WHEN** the catalogue and the API are built
- **THEN** its record carries a Guide-owned identifier and address, its re3data identifier remains external
  metadata/search input, and a changed source identifier does not silently reissue the Guide identity

#### Scenario: Classification changes after issue

- **GIVEN** a released entry whose resource type changes
- **WHEN** its classification is updated
- **THEN** its address remains unchanged, because the type is not part of it, and its current classification remains accurately described

#### Scenario: A scope that is part of the identity

- **GIVEN** the stage `plan` in two life-cycle models
- **WHEN** their addresses are built
- **THEN** they are `lifecycles/rdmkit/plan` and `lifecycles/maldreth/plan`, each scope named by its model's own identifier

### Requirement: Catalogue slugs use meaningful local names

Catalogue ID slugs SHALL omit grammatical particles and prefer official abbreviations or specific source URL words.
Generic registry/resolver and interface paths SHALL NOT determine a slug. When neither yields a useful name, the Guide
SHALL assign concise meaningful name words without truncating a word. These are one-time local assignments; refresh
SHALL preserve them.

#### Scenario: A source URL changes after local assignment

- **WHEN** a record receives a local slug from an abbreviation or source URL
- **THEN** later source changes preserve the assigned slug and cannot change the Guide identity

#### Scenario: An NKR record page does not name a repository

- **GIVEN** a new NKR record whose record page is `https://repo.cz/objects/20.500.14818/jgu5fyqf` and whose own address is `https://herbarium.biodiversity.cz`
- **WHEN** the snapshot is refreshed
- **THEN** the record's slug comes from the repository's own address or name, such as `herbarium`, never from the NKR handle
- **AND** its address is `repositories/herbarium`, and its NKR type sets its repository kind, never a segment of the address

### Requirement: Records have one primary identity

Every normalized catalogue record SHALL store one Guide-owned primary `id`; source identifiers SHALL use typed
`alternateIds` with source scheme and value. In the graph a record SHALL have one persistent IRI from its address,
carry its Guide identifier once and source identifiers as typed values. No other property SHALL restate it, a name
SHALL NOT repeat it, and no identifier SHALL encode a type or collision counter.

#### Scenario: An imported record is normalized

- **WHEN** the Guide imports a record with a real source identifier
- **THEN** `id` holds the Guide assignment, `alternateIds` retains the genuine typed source identifier, and no `guideId` or obsolete own-ID alternate remains

#### Scenario: A requirement without a title

- **GIVEN** the clause `A.R1.1.N1`, which has a text but no title of its own
- **WHEN** the graph is built
- **THEN** its node carries the identifier once and its text, and no name that repeats the identifier

#### Scenario: Two records whose source IDs collide

- **GIVEN** a FIP Dashboard organisation whose source ID equals a curated organisation's ID
- **WHEN** the graph is built
- **THEN** the Dashboard record attaches to the organisation it describes, or is rejected for review, and no identifier gains a counter suffix

### Requirement: The first release establishes the route baseline

Before the first official release (Guide `1.0.0`), identifiers, addresses, IRIs, API paths, the profile and the
query recipes MAY change in place. Compatibility routes, historical alias tables and duplicate API documents SHALL
NOT be retained for unreleased addresses. Genuine external identifiers SHALL remain usable as metadata and search
inputs. Separately required saved-result format support SHALL be preserved.

#### Scenario: An unreleased catalogue route changes

- **GIVEN** an unreleased address replaced by the final address
- **WHEN** the product is built
- **THEN** its callers and tests use the address and no old-route compatibility document is emitted

#### Scenario: Saved results from an alpha release

- **GIVEN** a result saved in format revision 3, which names its tests under `api/tests/<question>.json`
- **WHEN** the product is built after the address change
- **THEN** those test references still resolve, because saved-result support is preserved separately

### Requirement: Guide vocabulary IRIs come from a reviewed namespace

Guide-owned term, profile and record IRIs SHALL derive from the namespace declared in the Guide's reviewed
configuration, `https://w3id.org/eosc-cz/fair-guide/`, independent of where the Guide is served. Changing it SHALL be
a reviewed breaking change recorded in the changelog. Logical IDs and exact external IRIs SHALL remain unchanged; prior
artifacts SHALL retain their bytes and original contexts, without invented aliases or redirects.

#### Scenario: A different origin or repository prefix is deployed

- **WHEN** the Guide is built for another origin or path with the same namespace setting
- **THEN** navigation and discovery follow that location, expanded JSON-LD, record IRIs and profile references keep the declared namespace, and logical content IDs and exact external IRIs retain their identity

#### Scenario: The namespace setting changes

- **WHEN** a reviewed change sets a new namespace
- **THEN** every Guide term, the profile and every record IRI move to it together, no logical identifier changes, and the changelog names the break

#### Scenario: Publication combines production and preview

- **WHEN** verified production content is assembled beside a preview
- **THEN** channel links remain distinct without silently rewriting shared content identity or already verified production metadata

#### Scenario: A historical artifact is read after the namespace changed

- **WHEN** a consumer reads an older release archive or its original context
- **THEN** its bytes and legacy term/profile names are unchanged; no alias, redirect or external-IRI normalization is inferred

## ADDED Requirements

### Requirement: Persistent IRIs resolve through a registered redirect

The namespace SHALL be registered with w3id. Its redirect SHALL send `terms` and `profile/<version>` to the published
vocabulary and profile, and `id/<address>` to the API record when JSON is requested and otherwise to the record's
landing page. No redirect target SHALL carry a fragment, so the fragment of a part's IRI survives the redirect. IRIs
SHALL carry no API version. A host move or a new API major version SHALL change only the redirect, never an IRI.

#### Scenario: A machine dereferences a record IRI

- **WHEN** a client requests `https://w3id.org/eosc-cz/fair-guide/id/resources/dmp-eosc` asking for JSON
- **THEN** it is redirected to that record in the current API version

#### Scenario: A person opens a record IRI

- **WHEN** a browser opens the same IRI
- **THEN** it is redirected to the landing page of DMP.eosc.cz, which links to its catalogue entry in the Guide

#### Scenario: A person opens a part's IRI

- **WHEN** a browser opens `https://w3id.org/eosc-cz/fair-guide/id/repositories/zenodo#knav`
- **THEN** it reaches Zenodo's landing page at the section of its KNAV record

#### Scenario: The Guide moves to another host

- **GIVEN** the redirect updated for a new host
- **WHEN** a consumer dereferences an IRI issued before the move
- **THEN** it reaches the same record at the new host, and no IRI changed

### Requirement: Registry records describe one thing

A record a registry publishes (KNAV, FIP Dashboard, NKR, re3data, FAIRsharing, DataCite) SHALL be a catalogue record
about exactly one thing, scoped under it by the registry's scheme. It SHALL keep the registry's wording, licence and
retrieval date. The thing SHALL rest on its records. A record that matches no curated entry SHALL found a thing of
its own. The duplicate check SHALL report a record that could attach to more than one thing.

#### Scenario: A registry describes a curated service

- **GIVEN** the KNAV record for Zenodo, the curated repository Zenodo and their shared re3data identifier
- **WHEN** the graph is built
- **THEN** the KNAV record is `.../id/repositories/zenodo#knav`, it is about the Zenodo node, and its description keeps KNAV's wording and licence

#### Scenario: Two records for one service under different addresses

- **GIVEN** a curated service and a KNAV record that name the same provider and service, one by its documentation page and one by its service address
- **WHEN** the duplicate check runs
- **THEN** it reports the pair for review instead of publishing two things

#### Scenario: A repository re3data describes

- **GIVEN** a curated repository that re3data and FAIRsharing also describe
- **WHEN** the graph is built
- **THEN** it holds one node with `#re3data` and `#fairsharing` records under it, each keeping its registry's values, and the node names both records among what it rests on

### Requirement: Named agents resolve to one thing

An organisation, publisher, operator, developer or author named in content SHALL resolve to the one thing the Guide
describes under exactly that name, in any language and of any kind, and SHALL be a new organisation only where no
thing has the name. A name that two things share SHALL be refused unless the content names the agent by address. A
registry's organisation record SHALL attach to a thing only by a reviewed key, never by its name.

#### Scenario: A publisher that is a described service

- **GIVEN** a source whose publisher is named "Zenodo", and the curated repository Zenodo
- **WHEN** the graph is built
- **THEN** the source's publisher is the Zenodo repository node, and no separate organisation named Zenodo exists

#### Scenario: An organisation named in its other language

- **GIVEN** an operator named "Charles University" and the curated organisation whose names are "Univerzita Karlova" and "Charles University"
- **WHEN** the graph is built
- **THEN** the operator is that organisation

#### Scenario: An organisation and its eponymous service

- **GIVEN** the curated resource DataCite, with the FIP Dashboard's resource record and a reviewed handle of its organisation record
- **WHEN** the graph is built
- **THEN** one node holds both, as `#fip-dashboard` and `#fip-dashboard-organization`, and no separate organisation named DataCite exists

#### Scenario: A registry's organisation record with a known name

- **GIVEN** a FIP Dashboard organisation record named like a described infrastructure, with no ROR and no reviewed handle
- **WHEN** the graph is built and the duplicate check runs
- **THEN** the record is not attached by its name, and the duplicate check lists the pair for review

### Requirement: Provenance names items by their addresses

A provenance action SHALL name what it consulted and what it produced or changed by address or address prefix. A
prefix SHALL match records, and a part of a record only where the prefix names one. An action that covers every item
(`*`) SHALL record the Guide itself as its result, while the freshness check SHALL read it as covering every item.

#### Scenario: A structural change

- **GIVEN** a provenance action with the result `*` that renamed every record's identity
- **WHEN** its catalogue entry is shown
- **THEN** it names the Guide as what it changed, and no record lists it among its own changes

#### Scenario: Advice of one station

- **GIVEN** an action with the result `advice/plan.*`
- **WHEN** the graph is built
- **THEN** its results are the plan station's advice items, without their steps or actions

### Requirement: Controlled vocabularies have one model

Every controlled-vocabulary term, including tiers, levels, lenses, actors, modes, resource types, statuses, glossary
terms, principles, layers and life-cycle stages, SHALL be a defined term in exactly one term set, with its membership
stated once. The vocabulary document SHALL publish once how these terms align with SKOS. A status SHALL refer to a term
of its scheme, never a free string.

#### Scenario: A consumer lists a scheme's terms

- **WHEN** a consumer queries the graph for the terms of the service-status scheme
- **THEN** it finds each term once, through one membership property, with its code and bilingual name

#### Scenario: A requirement under review

- **GIVEN** a clause whose status is that it needs a refresh
- **WHEN** the graph is built
- **THEN** its status refers to the refresh term of the clause-status scheme, not to a string

### Requirement: Advice items share one class

Every advice item SHALL carry one class that identifies it as advice, whatever its kind. Its kind, lens, level and
station SHALL be properties, so a consumer selects all advice by its class and narrows it by those properties.

#### Scenario: All advice for one lens

- **WHEN** a consumer queries the graph for advice items addressed to data stewards
- **THEN** it selects them by the advice class and the lens, without relying on an identifier's form

### Requirement: Pre-fill mappings are typed statements

A question's pre-fill mapping SHALL be a typed statement naming the source that can answer it, the field read and the
level of coverage. The graph and the API SHALL both publish it.

#### Scenario: A question DataCite can pre-fill

- **GIVEN** the question `dataset.01`, which DataCite metadata can answer from the DOI
- **WHEN** a consumer reads the question in the graph or the API
- **THEN** it finds a pre-fill statement naming the DataCite source, the field `doi` and its coverage, not an untyped name-value pair

### Requirement: A question that restates its clause takes its text

A question whose statement is the same as one of its cited clauses SHALL take its text from that clause and SHALL NOT
hold a copy. Its own fields stay on the question. A question keeps its own statement only when it addresses another
actor, covers part of the clause, or must be phrased to be answerable. The content checks SHALL reject a statement
identical to one of its clauses.

#### Scenario: A CoreTrustSeal question

- **GIVEN** the question `coretrustseal.01`, whose wording is that of the requirement `CTS.R01`
- **WHEN** the question is shown, exported or published
- **THEN** its text is the clause's text in both languages, and the sources hold it once, in the ledger

#### Scenario: A copied statement in a pull request

- **GIVEN** an editor who adds a question whose statement repeats a clause it cites
- **WHEN** the content checks run
- **THEN** they fail, name the question and the clause, and point to taking the text from the clause

### Requirement: The knowledge graph is published as RDF

The build SHALL publish the knowledge graph as N-Triples next to the crate, with every IRI absolute and no remote
context needed to read it. It SHALL hold the same triples a JSON-LD processor obtains from the crate.

#### Scenario: Loading the graph offline

- **GIVEN** a consumer without network access and the published N-Triples file
- **WHEN** it loads the file into an RDF store
- **THEN** it loads without fetching any context, and its triples equal those of the crate

### Requirement: Graph queries have a tested contract

The classes, properties and shapes a consumer may query SHALL be published as the versioned RO-Crate profile, with
documented SPARQL recipes for common questions. CI SHALL run every recipe against the built graph with its expected
results. Before Guide `1.0.0` the contract MAY change in place; from `1.0.0` a change SHALL follow the published
deprecation rule.

#### Scenario: A recipe breaks

- **GIVEN** a pull request that renames a property a recipe uses
- **WHEN** the checks run
- **THEN** the recipe check fails and names the recipe

#### Scenario: A consumer starts from a recipe

- **GIVEN** a data steward who wants the researcher advice at one station
- **WHEN** they run the documented recipe against the published graph
- **THEN** it returns those advice items with their levels, in the language they select
