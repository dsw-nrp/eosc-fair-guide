## ADDED Requirements

### Requirement: Knowledge base is an RO-Crate

The guide's content SHALL be published as an RO-Crate 1.2 metadata file, and the guide page SHALL be that
crate's HTML preview. The same crate SHALL be available both as a standalone `ro-crate-metadata.json` and
as a generated classic script the page loads, so the page works without fetching any file. Credit SHALL be recorded so that the guide's
compiler holds an editor role, and the FAIR analysis the content builds on is a source entity with its authors.

#### Scenario: Harvester reads the crate

- **GIVEN** a published release of the guide
- **WHEN** a harvester requests `ro-crate-metadata.json`
- **THEN** it receives a valid RO-Crate 1.2 graph that contains the stations, advice items, checks, resources and provenance actions

#### Scenario: Page opened as a local file

- **GIVEN** the page file is opened from disk without network access
- **WHEN** the page loads
- **THEN** all content renders from the crate script delivered with the page, and only the live checks report that they are unavailable

### Requirement: Content is authored in source files and generated

Content SHALL be authored in TOML source files. A generator that uses only the Python standard library SHALL
produce the crate, the page's data scripts, the crate preview and the API files. Generated files SHALL NOT be
committed: pull requests carry authored files only, and the site is built from them in the pull-request checks
and at deployment. Reviewed snapshots of external sources are authored input and stay committed.

#### Scenario: Edited source

- **GIVEN** a pull request that changes a TOML source file
- **WHEN** the checks run
- **THEN** they build the site from the sources, validate the built crate, API and page, and fail with the reason if the build or a validation fails

#### Scenario: Generated file in a pull request

- **GIVEN** a pull request that adds a built crate or API file to the repository
- **WHEN** the hygiene check runs
- **THEN** it fails and names the generated file

### Requirement: Names have an English form

Every name readers see SHALL have an English form. A name that is not language-neutral, such as an
organisation's Czech name or the title of a Czech work, SHALL carry both languages, and a publisher that is a
curated organisation SHALL be cited by its identifier. A work the guide only cites SHALL show, in a language other
than its own, its original title followed by the translation in brackets. The content checks SHALL refuse a plain
Czech name.

#### Scenario: Czech organisation in the English guide

- **GIVEN** a resource published by an organisation with a Czech name
- **WHEN** the guide is shown in English
- **THEN** the resource names the organisation in English, and a content entry with only the Czech name fails the content checks

### Requirement: Published identifiers are reused

FAIR principle records SHALL keep published w3id IRIs alongside their Guide-owned identity; a resource SHALL
link its published FER IRI or FAIRsharing DOI. Entities SHALL use an established vocabulary before a
guide-specific term. An identifier SHALL be one typed `identifier` value. A guide-specific term SHALL declare
its broader term or a recorded reason, its domain and range, and a definition in a vocabulary document at the
guide's address.

#### Scenario: Resource with a published FER

- **GIVEN** a resource such as DataCite that has a published FER nanopublication
- **WHEN** the crate is generated
- **THEN** the resource entity carries that FER IRI as an equivalent identifier

#### Scenario: A fact an established term expresses

- **GIVEN** a fact the guide records that an established vocabulary term already expresses
- **WHEN** the crate is generated
- **THEN** the entity uses the established term, and no guide-specific term is introduced for it

#### Scenario: Identifier typed by its issuing scheme

- **GIVEN** a repository the guide curates that a registry also lists
- **WHEN** the crate is generated
- **THEN** the record carries its Guide identity and the registry identifier as separate `identifier` values,
  each naming the scheme that issued it

#### Scenario: Guide-specific term without a declaration

- **GIVEN** a guide-specific term proposed with neither a broader established term nor a recorded reason
- **WHEN** the content checks run
- **THEN** the check fails and names the term

#### Scenario: Consumer dereferences a guide term

- **GIVEN** the published guide address
- **WHEN** a consumer dereferences one of the guide's own term IRIs
- **THEN** it receives the vocabulary document that defines that term

### Requirement: Every statement traces to a published source

Every advice item and every check SHALL cite at least one entry of the clause ledger. Each ledger entry SHALL
point to a published source: the FAIR analysis, the NRP conditions, the NRP documentation, or a published
paper, dataset or web page. Unpublished working material SHALL NOT supply assessment requirements.

#### Scenario: Advice without a source

- **GIVEN** a pull request that adds an advice item with no ledger citation
- **WHEN** the content checks run
- **THEN** the check fails and names the item

#### Scenario: Citation of an unknown source

- **GIVEN** an advice item that cites an identifier missing from the ledger
- **WHEN** the content checks run
- **THEN** the check fails and names the unknown identifier

### Requirement: The analysis is covered without loss

Every clause of the FAIR analysis' principle table SHALL be reachable in the principle explorer under its
principle. The path MAY present a curated selection, provided the explorer keeps every clause.

#### Scenario: Clause missing from the explorer

- **GIVEN** a ledger clause from the principle table
- **WHEN** it is not reachable under its principle in the explorer
- **THEN** the content checks fail and name the clause

### Requirement: Content changes record paradata

A pull request SHALL record one Process Run Crate provenance action by default: the person (ORCID where available), every instrument it used (including the AI tool/model), the consulted sources, the entities it produced or changed and the end time, with coverage naming every item it changed; a finer action per batch MAY replace it where a change genuinely needs its own. AI SHALL be an instrument. Provenance coverage SHALL include exactly the kinds compared against the PR merge base.

#### Scenario: Changed advice without a newer action

- **GIVEN** a pull request that changes an advice item's text
- **WHEN** no provenance action newer than the previous release covers that item
- **THEN** the content checks fail and name the item

#### Scenario: A page changes without a newer action

- **GIVEN** a pull request that changes a page's text
- **WHEN** no provenance action newer than the previous release covers that page
- **THEN** the content checks fail and name the page

#### Scenario: A pull request records one action

- **GIVEN** a pull request that changes several content items
- **WHEN** one provenance action covers every item the pull request changed
- **THEN** the content checks pass, and the action names every person and instrument the change used

### Requirement: Statuses are dated

Every status of a service or resource SHALL use the five-level vocabulary (operational, pilot, in
development, planned, prospective) and SHALL carry an as-of date. A status older than the configured freshness
threshold SHALL be reported.

#### Scenario: Stale status

- **GIVEN** a resource whose status as-of date is older than the freshness threshold
- **WHEN** the scheduled health job runs
- **THEN** it opens an issue that names the resource and its last verified date

### Requirement: Content is bilingual

Every user-facing text SHALL exist in Czech and English as language-tagged values.

#### Scenario: Missing translation

- **GIVEN** an advice item with Czech text only
- **WHEN** the content checks run
- **THEN** the check fails and names the item and the missing language

### Requirement: Non-browser sources enter as reviewed snapshots

Data from sources that a browser cannot query (for example re3data, Heslář, the FIP Dashboard while its API
refuses the guide's origin, the KNAV and RDMkit tool lists, NMA facets and test-service health) SHALL enter the
crate only as dated snapshots delivered by pull request. A snapshot SHALL credit its source and link back to it.
Text such as glossary definitions SHALL be copied only where the source's licence permits; otherwise only labels
and links are kept.

#### Scenario: Scheduled refresh

- **GIVEN** the scheduled refresh job finds changed re3data entries
- **WHEN** it completes
- **THEN** it opens a pull request with the updated snapshot and its retrieval date, and commits nothing directly

### Requirement: Snapshots keep their source's licence

A snapshot whose source licence differs from the guide's content licence SHALL declare the source's licence on its
file and on its entities in the crate, and SHALL NOT be relicensed as guide content.

#### Scenario: A snapshot under another licence

- **GIVEN** the KNAV tools catalogue, whose repository is licensed GPL-3.0
- **WHEN** its snapshot enters the crate
- **THEN** the snapshot file and its tool entities declare GPL-3.0 and credit KNAV, and the guide's own content licence is not applied to them

### Requirement: Czech repositories include reviewed Czech-hosted ones

The re3data snapshot SHALL combine the repositories re3data lists for the Czech Republic with a reviewed list of
Czech-hosted repositories that re3data does not tag with that country.

#### Scenario: A Czech-hosted repository without the country tag

- **GIVEN** the ELI ERIC Open Data Repository, hosted in the Czech Republic but not tagged with it in re3data
- **WHEN** the re3data snapshot is refreshed
- **THEN** it includes that repository from the reviewed list, with its re3data record and retrieval date

### Requirement: Repository names are harvested and reviewed

The re3data snapshot SHALL keep the names re3data tags as Czech beside the English name and the abbreviations.
Curated entries SHALL correct or complete Czech names and abbreviations from the repository's own site, and the
curated form SHALL take precedence.

#### Scenario: re3data lacks the Czech name

- **GIVEN** re3data lists "CSDA" as an English additional name and no Czech name for the Czech Social Science Data Archive
- **WHEN** the catalogue is built
- **THEN** the curated entry supplies "Český sociálněvědní datový archiv" and "ČSDA", and "CSDA" remains the English abbreviation

### Requirement: Catalogue entries keep their qualification and status

FAIR-enabling resources and FIPs taken from the FIP Dashboard SHALL keep the dashboard's identifier, its
verification level (verified, self-declared, under review), the verifier and the verification date, and FIPs
SHALL keep their status and declarations. While the dashboard's own metadata carries a disclaimer about its data,
the snapshot SHALL keep that disclaimer and the guide SHALL show it.

#### Scenario: Sample data in the catalogue

- **GIVEN** a dashboard snapshot whose metadata includes a disclaimer that its profiles are sample data
- **WHEN** a user opens a FIP taken from that snapshot
- **THEN** the guide shows the disclaimer next to the profile, and the notice disappears after a snapshot without the disclaimer is merged

### Requirement: Static read-only API

The guide SHALL publish a read-only API without a backend: JSON files for each collection and each entity
(principles, stations, checks, resources, repositories, clauses, sources and glossary terms), generated at
deployment and described by an OpenAPI 3.1 document with a relative server address. Responses SHALL carry language
maps and a JSON-LD context. Paths SHALL follow the FIP Dashboard API's naming where both describe the same thing.

#### Scenario: A consumer reads a principle

- **GIVEN** a service that requests the R1.1 principle from the guide's API
- **WHEN** it reads the response
- **THEN** it receives the principle with its advice per lens, the stations that address it and the check items that test it, as JSON with a JSON-LD context

### Requirement: Content addressed relative to the site

The API's files SHALL name the guide's own entities and each other by references relative to the file that names
them, never by the site's address, so the guide works unchanged when it moves to another address. Links that leave
the page, such as the test references in an exported result, SHALL take the address the page is served from.

#### Scenario: The guide moves

- **GIVEN** the guide published at a new address
- **WHEN** a consumer follows a link in an API record, or the test reference in a result exported there
- **THEN** it reaches the record at the new address, without the guide being rebuilt for it

### Requirement: Checks published as FTR definitions

Each check SHALL be published in the API as an FTR benchmark, with its items as metrics and manual tests, so that
the test references in an exported self-check result set resolve.

#### Scenario: Exported result resolves

- **GIVEN** a self-check result set exported from the guide
- **WHEN** a tool follows a result's test reference
- **THEN** it reaches the item's FTR test definition in the published API

### Requirement: Interactive API documentation

Interactive documentation of the API SHALL be served from a separate page built from a pinned Swagger UI package
copied in at deployment, with its own content security policy; the guide's own page keeps its stricter policy.

#### Scenario: Trying an endpoint

- **GIVEN** a developer on the API documentation page
- **WHEN** they try the principles endpoint
- **THEN** the page fetches the JSON from the same site and shows it, and no request leaves the site

### Requirement: One entry per real-world thing

Curated content SHALL describe each real-world thing once, in one entry that carries every role it plays, and a
content identifier SHALL name exactly one entity. Two curated entries SHALL NOT share a web address or a DOI. A
curated entry that matches a snapshot record SHALL link to it instead of repeating it. The content checks SHALL
enforce these rules and SHALL report entries that nothing uses.

#### Scenario: A duplicate in a pull request

- **GIVEN** an editor who adds a source with the address of an existing resource
- **WHEN** the content checks run
- **THEN** they fail and name both entries

### Requirement: Research practice sources retain their scope

Software assessment principles SHALL retain identities distinct from data FAIR principles. Software sources
SHALL identify FAIR4RS, FAIR-IMPACT FRSM, CODE, Software Heritage and OpenSSF Best Practices with their
respective roles and versions. Authored summaries SHALL link to original requirements without presenting
them as NRP conditions.

#### Scenario: Code archive and software assessment

- **GIVEN** software guidance that uses Software Heritage and OpenSSF
- **WHEN** the sources are read in the catalogue
- **THEN** preservation, precise archival references and voluntary self-certification are distinguished from FAIR4RS/FRSM assessment

### Requirement: Software and content are described separately

The guide SHALL describe its software as a machine-readable entity linked to the knowledge-base dataset,
with version, repository, author, licence, citation and build/dependency documentation. AI contributions
SHALL name the tools actually used and keep people as responsible agents.

#### Scenario: Integrator inspects the guide's own metadata

- **GIVEN** the generated crate
- **WHEN** the integrator follows the worked software example
- **THEN** software and content dataset have separate identities, appropriate licences and an explicit relationship

### Requirement: National development and FDO specification status are explicit

The FDO specification SHALL be labelled version 3.0, Proposed Recommendation. OSII notebook and provenance
outputs SHALL carry dated development or planning status. The feasibility study SHALL NOT serve as evidence
of an operational national endpoint.

#### Scenario: Planned national notebook instance

- **GIVEN** an OSII output described in the feasibility study
- **WHEN** it is listed in the guide
- **THEN** its dated project status is explicit and no operational endpoint is inferred

### Requirement: Suitable original descriptions accompany check criteria

Across all checks, a criterion with a fitting published passage that permits reuse SHALL make that
original description available through its source clause. The passage SHALL retain its wording,
original language, attribution and precise source version. Guide explanations, paraphrases and
translations SHALL be distinguishable from the original. A criterion without a suitable reusable
passage SHALL retain source links without an invented original description.

#### Scenario: A Czech requirement accompanies an English question

- **GIVEN** a question based on a reusable Czech requirement
- **WHEN** the reader opens its basis in the English guide
- **THEN** the original is identified as Czech with its source and version, and any English translation is labelled separately

#### Scenario: A question synthesises several sources

- **GIVEN** no single passage expresses the whole criterion
- **WHEN** its original descriptions are prepared
- **THEN** fitting excerpts are attributed separately or the source links are retained, without presenting an invented combined passage as an original requirement

### Requirement: Question revisions preserve issued identities

Question and source-clause revisions SHALL preserve issued identifiers and published source labels. An
identifier is issued once it appears in an official release. Retired issued questions or issued questions that
become contextual entries SHALL retain traceable identifier history; their identifiers SHALL NOT be reused for
another criterion. Before the first official release, identifiers MAY change in place; the register then lists
only the current set.

#### Scenario: Restructuring before the first release

- **GIVEN** the unreleased guide in which the work station is split into three steps
- **WHEN** the register and the content checks run
- **THEN** the register lists the new step and advice identifiers only, and no retirement entry is required for the former ones

#### Scenario: A source description is not an obligation

- **GIVEN** an issued FDO question based on descriptive context
- **WHEN** review corrects its assessment treatment
- **THEN** the original source label and issued question identity remain traceable without assigning that identity to an unrelated obligation

### Requirement: Local automated criteria are inspectable test records

Every local automated criterion SHALL have a stable issued identifier, bilingual description of its
observations and limits, a named callable implementation and links to the question it supports.
The catalogue and API SHALL expose these Test records. Executable source and documentation SHALL be
attached files in the RO-Crate. Shared algorithm files MAY implement multiple named criteria.

#### Scenario: Inspecting a local software test

- **GIVEN** a software question with a local prefill rule
- **WHEN** the reader inspects its test record
- **THEN** the record identifies the criterion, its source code and documentation and the limited evidence it derives, without claiming external certification or successful execution of the inspected software

### Requirement: Original coverage is inventoried across content kinds

A deterministic maintainer check SHALL inventory original passages for all clauses, questions and
station advice, retaining the exact missing citations and source associations. Partial citation coverage
SHALL remain distinct from complete coverage. Only explicitly reviewed omissions SHALL be labelled
deliberate; absent passages SHALL NOT imply reuse permission, a missing FAIR requirement or an invented
exemption.

#### Scenario: Advice cites a service summary without an original

- **GIVEN** a station advice item whose cited clause has no original passage
- **WHEN** the inventory runs
- **THEN** it reports the item, missing clause and published source for review without inventing a requirement quotation or labelling the advice a failed FAIR criterion

### Requirement: Layers and seams have shared model records

The knowledge base SHALL publish six functional layers and twelve responsibility-boundary connections,
including within-layer transfers, with bilingual descriptions and stable identities. Connections SHALL describe
transferred information, sender/recipient functions, carrier and maintenance actors. Reviewed item associations
SHALL be shared by the page, crate and API, preserving existing FAIR categories, framework groups and identities.

#### Scenario: An editor associates a harvesting question

- **GIVEN** a question specifically addressing repository-to-NMA harvesting
- **WHEN** its reviewed model association is generated
- **THEN** the question, catalogue and API resolve the same connection record and unknown model references fail validation

### Requirement: The conceptual manuscript has a narrow citation exception

The approved Layers-and-Seams manuscript MAY be cited as in preparation solely for its conceptual model and
attributed examples. It SHALL NOT supply assessment obligations or establish current service status. Its
citation SHALL preserve authentic authorship and title without invented publication metadata.

#### Scenario: A conceptual model cites its manuscript

- **GIVEN** the approved manuscript in preparation
- **WHEN** its model and examples are published in the guide
- **THEN** the citation identifies its preparation status and assessment requirements retain published sources

### Requirement: Model associations preserve evidence and responsibility scope

A model association SHALL indicate relevance, not implementation success or conformance. Implementation
statuses SHALL retain their scope, source and observation date independently of component status. Actors who
implement or maintain a transfer SHALL NOT be presented as formally assigned accountable owners without
evidence. Associations inherited by tests SHALL respect their actual documented coverage.

#### Scenario: A pilot catalogue has a planned planning integration

- **GIVEN** a pilot catalogue and a planning integration documented only as planned
- **WHEN** their connection is described
- **THEN** the two scopes remain distinguishable and neither the catalogue's existence nor a successful probe establishes that the planning integration works

### Requirement: Provider criteria and mappings have inspectable identities

Provider/metric records SHALL retain native IDs, criterion/source versions, documentation and applicable
GUI/invocation links. They SHALL reuse existing FAIR facets and distinguish whole/partial/unmapped coverage.
Mappings SHALL name the reviewed provider/metric version, Guide question and coverage conditions.
Source wording/force SHALL NOT become a normalized verdict or invented original description.

#### Scenario: A metric version changes

- **GIVEN** a provider report using a version newer than the reviewed mapping
- **WHEN** its catalogue association is considered
- **THEN** the native identity and documentation remain available while automatic suggestions wait for version-specific review

### Requirement: Provider observations retain their original assessment

Shared assessment records SHALL retain provider, target/subject/representation, supplied versions, assessment
and retrieval dates, native outcomes/subtests/diagnostics and original source links or report. Questions SHALL
reference those records rather than copy divergent versions of the same assessment. Unknown native fields
SHALL remain preserved within accepted size/safety limits. Normalized references SHALL NOT discard or rewrite
native evidence.

#### Scenario: Two questions refer to one imported assessment

- **GIVEN** one accepted F-UJI report relevant to two questions
- **WHEN** the result is exported
- **THEN** both questions reference one complete attributable assessment rather than independently truncated copies

### Requirement: Provenance coverage agrees with changed-item fingerprints

Every authored entity kind included in freshness comparison SHALL have truthful provenance coverage,
including organizations. Local and exact-base PR comparison SHALL enforce the same coverage contract.
Automatic source retrieval SHALL record source/time/software/run separately from human editorial review.
Human authorship and citation entries SHALL NOT be inferred from an automation account or indiscriminately
assigned to every action in a pull request.

#### Scenario: An organization changes without covering provenance

- **GIVEN** a changed organization included in the base-comparison fingerprints
- **WHEN** content validation runs locally or on the pull request
- **THEN** it requires a truthful covering action in both contexts and does not silently exempt the kind

### Requirement: Life-cycle models and their crosswalk are records

The RDMkit and MaLDReTH research data life cycles and the KNAV tools catalogue's steps SHALL be records in the
knowledge base, each stage with its published name, definition, source and licence. Each path step SHALL link the
stages it corresponds to in each model. Each correspondence SHALL state whether a source publishes it or the guide
reviewed it, and unconfirmed ones SHALL be marked. The crosswalk SHALL appear in the catalogue, the API and the crate.

#### Scenario: Reading the crosswalk for the reuse stage

- **GIVEN** the catalogue record of the path's reuse stage
- **WHEN** a reader opens it
- **THEN** it shows RDMkit Reuse as the published basis, MaLDReTH Access and Transform with the source of each correspondence and any unconfirmed mark, and the KNAV Reusing step as the guide's reviewed mapping

### Requirement: Stage definitions read the same in both languages

For the path's stages, Czech readers SHALL see the guide's Czech translation of the source's definition, marked as a
translation, so that both languages state the same definition. A Czech source's own definition SHALL remain as a
second, attributed quote that keeps its stage label so that it reads as a sentence. Other models' definitions SHALL
stay in their source's language.

#### Scenario: Reading the planning stage in Czech

- **GIVEN** a Czech reader opening the planning stage in the catalogue
- **WHEN** the entry is shown
- **THEN** it shows the translation of RDMkit's definition marked as the guide's translation, and below it KNAV's quote beginning "Plánování:" with its source

### Requirement: Catalogues of tools and repositories are linked

The guide SHALL link the SSH Open Marketplace at the steps and lenses it serves, OpenDOAR as a repository
directory, and Infra Finder for those who choose research infrastructure. A catalogue SHALL be harvested only where
it offers an open API and terms that permit reuse.

#### Scenario: Looking for social-science tools

- **GIVEN** a researcher in the social sciences and humanities on the analysis step
- **WHEN** the step's resources are shown
- **THEN** the SSH Open Marketplace is among them, and OpenDOAR appears with the repository directories in the catalogue

### Requirement: DataCite informs repository details

The guide SHALL use DataCite's open services where they describe a repository: its DataCite repository record and
DOI counts in the repository finder, and its registered records as the source of samples for the maturity check.
Each fact SHALL name DataCite as its source and the date it was read.

#### Scenario: A repository that registers DataCite DOIs

- **GIVEN** a repository in the finder that registers DOIs with DataCite
- **WHEN** a reader opens its entry
- **THEN** the entry links its DataCite record and states what DataCite reports, with the date it was read

### Requirement: RDMkit is reused beyond its life cycle

The guide SHALL reuse RDMkit beyond its life-cycle stages: its task pages SHALL be cited or linked from the steps
and advice they inform; its role pages from the matching lenses; its domain pages from the community lens where a
domain matches; and its training references and FAIR Cookbook recipes as resources where they fit a step. Where
Czech law or national services differ from RDMkit's international guidance, the guide SHALL state the national
position and its source.

#### Scenario: RDMkit advice that differs under Czech law

- **GIVEN** the licence step, where RDMkit suggests CC0 to waive all rights
- **WHEN** a researcher reads the advice on databases and public domain
- **THEN** the guide links the RDMkit licensing page and states, citing the NRP copyright and licences FAQ, that Czech law reads CC0 as the broadest licence because authors' rights cannot be waived

### Requirement: RDMkit tool records join the catalogue

RDMkit tool and resource records SHALL be joined to existing catalogue entries through their bio.tools,
FAIRsharing and TeSS identifiers and addresses, under the one-entry-per-thing rule. Further RDMkit tools SHALL be
imported selectively, for the steps they serve, within the initial-download budget.

#### Scenario: A tool listed by RDMkit and the guide

- **GIVEN** eLabFTW, which RDMkit and the guide both list
- **WHEN** the catalogue is built
- **THEN** one eLabFTW entry links its RDMkit record, and no second entry is created

### Requirement: EOSC CZ Node membership is recorded with its state

The EOSC CZ Node SHALL be a record with its operator and candidate status. Each member entry SHALL carry its role,
state, any planned milestone, the date checked and the source. Membership SHALL be curated from the node's
published charter and announcements until a machine-readable node catalogue exists.

#### Scenario: A repository planned for integration

- **GIVEN** MBDB, listed in the node charter for integration by month 6
- **WHEN** the crate and the API are built
- **THEN** MBDB's record carries the node membership with that milestone, the date checked and the charter as its source

### Requirement: Large research infrastructures keep distinct relations

Large research infrastructures of the national roadmap SHALL be records with acronyms, Czech and English names,
host institution, field, life-cycle phase and ESFRI status, cited by roadmap annex. National-node status, ERIC
membership, operating a catalogue entry and EOSC CZ Node membership SHALL be separate relations. An operator
relation SHALL be recorded only where a source states it.

#### Scenario: A national node that operates a repository

- **GIVEN** CSDA/ESS-CZ
- **WHEN** its record is shown
- **THEN** it is the Czech national node of CESSDA and ESS according to Annex 7 and operates the ČSDA repository, while ČSDA's node badge comes from the node charter

#### Scenario: A repository without a stated operator infrastructure

- **GIVEN** MBDB, whose sources name its developers but no operating infrastructure
- **WHEN** the catalogue is built
- **THEN** MBDB's record names its developers and no infrastructure operator

### Requirement: Prose references name catalogue entries

A prose reference SHALL resolve to any allowed published catalogue entry by its compact Guide address. Its targets SHALL derive from the same identity projection as API records and routes, with a short collection allow-list. Current authored short forms for resources/sources, pages, stations, clauses, infrastructure and model records SHALL remain available; synthetic source-route aliases SHALL NOT be required.

#### Scenario: A catalogue tool named in a step

- **GIVEN** a step whose text names a tool the KNAV catalogue lists and no guide entry stands for
- **WHEN** the step is shown
- **THEN** the reference is one the content checks accept, and it links to that tool's catalogue entry

### Requirement: Catalogue addresses are guide-issued

Each catalogue record SHALL own a locally stored identifier and one compact address,
`<kind-code>/<type-code>/<id>`, emitted once by the build for API, routes, references and exports. Chips SHALL show
the compact record ID. Kind/type codes SHALL use one vocabulary; unneeded type SHALL be omitted. Complete computed
addresses SHALL NOT be duplicated in a parallel per-record register.

#### Scenario: A repository the guide takes from re3data

- **GIVEN** a repository re3data lists and the guide does not curate
- **WHEN** the catalogue and the API are built
- **THEN** its record carries a Guide-owned identifier and compact address, its re3data identifier remains external
  metadata/search input, and a changed source identifier does not silently reissue the Guide identity

#### Scenario: Classification changes after issue

- **GIVEN** a released entry whose resource type changes
- **WHEN** its classification is updated
- **THEN** its issued address remains unchanged and its current classification remains accurately described

### Requirement: Catalogue slugs use meaningful local names

Catalogue ID slugs SHALL omit grammatical particles and prefer official abbreviations or specific source URL words. Generic registry/resolver and interface paths SHALL NOT determine a slug. When neither yields a useful name, the Guide SHALL assign concise meaningful name words without truncating a word. These are one-time local assignments; refresh SHALL preserve them.

#### Scenario: A source URL changes after local assignment

- **WHEN** a record receives a local slug from an abbreviation or source URL
- **THEN** later source changes preserve the assigned slug and cannot change the Guide identity

### Requirement: Records have one primary identity

Every normalized catalogue record SHALL store one Guide-owned primary `id`. Genuine source identifiers SHALL
use typed `alternateIds` with source scheme and value; obsolete local IDs SHALL NOT become source alternates.
Graph and API identities SHALL use the primary; external joins SHALL use explicit source identities.
The build SHALL reject competing primary fields and missing or malformed source identifiers.

#### Scenario: An imported record is normalized

- **WHEN** the Guide imports a record with a real source identifier
- **THEN** `id` holds the Guide assignment, `alternateIds` retains the genuine typed source identifier, and no `guideId` or obsolete own-ID alternate remains

### Requirement: Imported identities survive source refresh

Released addresses SHALL survive title, classification and external source ID/URL changes. Imported records SHALL
preserve their locally owned Guide identifier across refresh; ambiguous identity changes SHALL require review.
External identifiers, authoritative IRIs and landing URLs SHALL remain metadata with their actual roles; `sameAs`
SHALL denote equivalent identity rather than a general citation.

#### Scenario: An upstream record changes its identifier

- **GIVEN** an imported record with a stored Guide ID and reviewed external identity
- **WHEN** refresh reconciles a changed upstream ID through an unambiguous exact external identity
- **THEN** the Guide ID and address remain unchanged and an ambiguous join requires review

### Requirement: The first release establishes the route baseline

Before the first official release, identifiers MAY change in place. Compatibility routes, historical alias tables
and duplicate API documents SHALL NOT be retained for unreleased addresses. Genuine external identifiers SHALL
remain usable as metadata and search inputs. Separately required saved-result format support SHALL be preserved.

#### Scenario: An unreleased catalogue route changes

- **GIVEN** an unreleased address replaced by the final compact address
- **WHEN** the product is built
- **THEN** its callers and tests use the compact address and no old-route compatibility document is emitted

### Requirement: Reviewed missing-link decisions remain scoped and visible

The health report SHALL separate unresolved link suggestions from reviewed unlinked mentions and stale decisions. Each decision SHALL name an exact field, target, text fingerprint, review date and reason, without wildcards. Changed text or targets SHALL reopen review; new occurrences SHALL remain eligible. Invalid or duplicate decisions SHALL fail health integrity without exempting prose broadly.

#### Scenario: Reviewed text changes

- **GIVEN** an exact dated decision to leave a mention unlinked
- **WHEN** its field text or proposed target changes
- **THEN** the current suggestion is unresolved again and the previous decision is reported as stale

#### Scenario: A new occurrence of a reviewed term

- **GIVEN** a decision scoped to one occurrence of a term
- **WHEN** the term occurs in a new field
- **THEN** that occurrence is eligible for a suggestion and the older decision does not hide it
