# Guide experience

## Purpose

The FAIR Guide experience capability and its observable acceptance contract.

## Requirements

### Requirement: Model records connect catalogue content by function and transfer

The catalogue SHALL expose model records in its established presentation and offer shared implementation-layer
and connection facets with existing count, OR/AND and shareable-route behaviour. Selected shared facets SHALL
survive kind changes, Kind SHALL retain its position, and associated records SHALL visibly show quiet linked
model relations. Model details SHALL offer related filtered content; exports SHALL retain these associations.

#### Scenario: Following repository-to-NMA content across kinds

- **GIVEN** a reader selecting the repository-to-NMA connection
- **WHEN** they switch from resources to questions and tests
- **THEN** the connection filter remains, counts reflect matching records and each record retains its own coverage rather than implying that NMA presence, endpoint existence and harvesting are equivalent

### Requirement: Model definitions participate in shared facets

The shared facets SHALL include each layer or connection definition by its own identity without adding a
self-association to the knowledge base or exported records.

#### Scenario: Selecting a connection in the model catalogue

- **GIVEN** a reader viewing model records
- **WHEN** they select a connection in the shared connection facet
- **THEN** its definition appears with an accurate count, and exports retain actual associations without an invented self-link

### Requirement: The model explains existing work in context

A bilingual model overview SHALL explain six functional layers, within/across-layer transfers and feedback
with an accessible diagram and equivalent prose. Selected station/lens explanations SHALL appear in Proč and
reuse model records; practical corrections SHALL be integrated into existing L1 steps. Model descriptions SHALL
load on demand, preserving file, iframe, language and initial-download behaviour.

#### Scenario: A community explains metadata requirements

- **GIVEN** a reader using the community lens at metadata
- **WHEN** they open Proč
- **THEN** the explanation distinguishes community profiles/schemas, repository configuration and the shared discovery record, links the relevant model connection and preserves the published source requirements below it

### Requirement: The guide demonstrates its own information transfers

Data for machines and the model overview SHALL link actual source, question, test and revision records as a
worked example. The example SHALL distinguish recorded revision provenance from an executed assessment and
explain the selected test's actual scope. All four records SHALL resolve independently of prior navigation,
and an identified test step SHALL show its readable title alongside the issued identifier.

#### Scenario: A reader follows the identifier example

- **GIVEN** the guide's identifier requirement, question, local test and revision
- **WHEN** the reader follows the worked example
- **THEN** each record resolves and PID resolution is distinguished from long-term availability

#### Scenario: Opening the example without visiting the catalogue first

- **GIVEN** a fresh session in either language
- **WHEN** the reader opens the model overview or Data for machines directly
- **THEN** all four linked steps appear, including the question and the test's readable title

### Requirement: Test definitions are easy to locate

The test catalogue SHALL offer execution location, supported check and dated external service-status
facets. Local tests SHALL have no fabricated service status. Local test documentation SHALL show each
issued identifier and label in a heading in both languages, and links SHALL open the selected language.

#### Scenario: Finding a local software test

- **GIVEN** a reader browsing test definitions
- **WHEN** the reader selects browser execution and the software check
- **THEN** the catalogue shows the matching local tests and each documentation link opens its identified heading in the reader's language

### Requirement: Tests and questions reuse FAIR principle filters

Tests and check questions SHALL reuse the established FAIR principles and the shared catalogue
principle filter. Local tests SHALL inherit their question's principle links in the catalogue,
documentation, crate and API. Records SHALL display those links using the existing principle tiles.
No FAIR category, vocabulary, mapping property or separate facet SHALL be added. Framework-specific
source identifiers and existing inherited mappings SHALL remain intact. Unsupported links SHALL
remain absent.

#### Scenario: Software-specific FAIR4RS topics

- **GIVEN** a software criterion based on a published FRSM metric
- **WHEN** its topic classification is displayed
- **THEN** its source identifier remains intact and applicable links use existing FAIR principles without renaming a software-specific requirement as a data requirement

### Requirement: The path follows the research data life cycle

The path SHALL follow the seven stages of the RDMkit research data life cycle in order, named in Czech as on the
KNAV Open Science Department's life-cycle page. The sharing stage SHALL hold the metadata, licence, publication and
findability steps; the reuse stage SHALL hold the citation and assessment steps, since assessing data is a form of
reuse; every other stage SHALL hold one step, and no step SHALL stand outside the cycle.

#### Scenario: The path in order

- **GIVEN** any lens and language
- **WHEN** the rail is shown
- **THEN** it lists the seven stages in RDMkit order with their Czech or English names, four steps under sharing, citation and assessment under reuse, and one step under each other stage

### Requirement: The reader's stage is derived, never chosen

The stage a reader is in SHALL be derived from the step being read; the guide SHALL NOT ask the reader to choose a
stage and SHALL NOT store one. Earlier steps SHALL stay visible and reachable. The path's start SHALL stay reachable
from the main menu, and a returning visitor SHALL resume the step they last read with one action.

#### Scenario: Reading a sharing step

- **GIVEN** a reader on the licence step
- **WHEN** the path is shown
- **THEN** the rail lists the seven stages with sharing marked as the current stage and its four steps beneath it, and no stage choice is offered

#### Scenario: Returning visitor opens the path's start

- **GIVEN** a visitor whose last step was processing
- **WHEN** they choose the home item in the main menu
- **THEN** the life-cycle journey marks processing as the stage last read, and one action resumes that step

### Requirement: Home and path in the main menu

The main menu SHALL offer the landing as its own first item, and a separate path item that opens the station the
visitor was last at, or the first station on a first visit. Each item SHALL be marked as current only on its own
view: the home item on the landing, the path item on a station.

#### Scenario: Returning visitor resumes from the menu

- **GIVEN** a visitor whose last station was the licence station
- **WHEN** they choose the path item in the main menu
- **THEN** the licence station opens and the path item is marked as current

### Requirement: Role lenses on the same path

The guide SHALL offer four lenses: researcher, data steward, repository administrator or curator, and
community/FIP. Switching the lens SHALL change the content shown for the current station without leaving it, and
SHALL keep the disclosure levels the user opened and the scroll position, so that roles can be compared.

#### Scenario: Switching lens

- **GIVEN** a user reading the publication station in the researcher lens
- **WHEN** they switch to the repository administrator lens
- **THEN** the same station shows the repository administrator's content, and the position on the path is kept

#### Scenario: Comparing lenses with details open

- **GIVEN** a user who opened levels L1 and L2 on a station
- **WHEN** they switch the lens
- **THEN** levels L1 and L2 stay open for the new lens's content, and the page does not jump to the top

### Requirement: Lens switch placement

The lens switch SHALL be an always-visible band of four options, each with an icon and a text label, under the
main menu, not a drop-down. Each option SHALL be a link, so a lens can be shared. The band SHALL appear only on
views where the lens changes what is shown (the path and the self-check overview) and SHALL be hidden elsewhere. In
the catalogue the lens SHALL be one of the resource filters, starting from the reader's lens.

#### Scenario: Lens without effect

- **GIVEN** a user in the principle explorer or the repository finder
- **WHEN** the view is shown
- **THEN** no lens switch is shown, because the lens changes nothing there

### Requirement: Detail on demand

Each station SHALL first show the key point for the lens, then level L0: one sentence with at most two actions,
then the Heslář terms the station uses. Levels L1 (steps), L2 (why: principles and requirements) and the AI advice
SHALL follow in that order and open only on request; the shared callouts SHALL follow them, and L3 (sources and
provenance) SHALL come after the callouts. Disclosure SHALL use native, keyboard-operable elements.

#### Scenario: Default view

- **GIVEN** any station in any lens
- **WHEN** it is first shown
- **THEN** the key point, the L0 sentence with its actions and the Heslář terms are visible, and the L1, L2, AI, callout and L3 controls are closed, with the callouts placed before L3

### Requirement: L2 notes read as prose

Authored L2 notes SHALL read as short prose within the explanation, with a service status as a quiet status note,
not as a bulleted list.

#### Scenario: A single status note in L2

- **GIVEN** a station whose only authored L2 note states that a service is in pilot operation
- **WHEN** a reader opens L2
- **THEN** the note reads as a short status sentence within the explanation, not as a one-item bulleted list

### Requirement: No dead ends

Every station SHALL end with one concrete next action and SHALL offer a route to human help, such as the
institution's data steward or NRP support.

#### Scenario: User is unsure

- **GIVEN** a user on any station
- **WHEN** they look for help
- **THEN** a help link to a data steward or NRP support is visible on that station

### Requirement: Shareable views

The current language, lens and station SHALL be expressible as a link that reopens the same view, so that a
data steward can send a researcher directly to the relevant step.

#### Scenario: Data steward shares a station

- **GIVEN** a data steward viewing the description station in the researcher lens in Czech
- **WHEN** they copy the page link and a researcher opens it
- **THEN** the researcher sees the same station, lens and language

### Requirement: Principle explorer

The guide SHALL provide a view per FAIR principle that lists every ledger clause for that principle, grouped
by actor (NRP, repository, FIP), with its links to CoreTrustSeal requirements and CDIF profiles. Principles SHALL
be chosen from a vertical menu grouped by F, A, I and R, laid out like the path's station rail.

#### Scenario: Explorer completeness

- **GIVEN** the principle R1.1
- **WHEN** the user opens it in the explorer
- **THEN** every ledger clause attributed to R1.1 is listed with its source

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

### Requirement: Reader's meaning and task guide the interface

Every view's navigation, labels, grouping and defaults SHALL follow what the reader wants to do and what an entry
means. Understanding the interface SHALL NOT require knowledge of source files, registries or implementation.
Source and verification detail SHALL support decisions without determining where the reader finds the thing.

#### Scenario: Finding an imported service by its purpose

- **GIVEN** a reader who knows what a service does but not which registry supplies its record
- **WHEN** they browse or follow a task shortcut
- **THEN** the service appears under the relevant meaning and function with a clear label
- **AND** the reader can inspect its sources and verification without needing them to find it

### Requirement: Finder sorting and orientation

Users SHALL sort resources by name, type, status or the date the status was checked, and repositories
by name, kind or source. Items SHALL carry orientation tags (principle tiles, lens icons), and every data source an
item names SHALL be a live link to the record it came from.

#### Scenario: Sorting by status date

- **GIVEN** a user in the resource finder
- **WHEN** they sort by the date the status was checked
- **THEN** the resources whose status was checked longest ago come first, each still showing its tags and source links

### Requirement: NKR records are shown as found

The scheduled workflow SHALL bring NKR records into a snapshot. Each SHALL join by its reviewed handle or exact
normalised address, or stand alone; similar names or hosts SHALL NOT join. An address-free record SHALL join only
through its handle. NKR's non-empty names, kind, status, keywords and address SHALL take precedence; empty values SHALL
NOT remove other sources' values. When NKR lists no repository, the finder and repository check SHALL link to NKR, not
show sample/simulated records.

#### Scenario: NKR lists no repository

- **GIVEN** NKR lists no repository, so there is no NKR snapshot
- **WHEN** a reader opens the repository catalogue
- **THEN** the guide states that NKR lists no repository yet, with a link to NKR, and offers nothing to load

#### Scenario: NKR's facts take precedence

- **GIVEN** a curated repository entry with status pilot and a Czech name of its own, joined to an NKR record with status development and the name "CzBIRD"
- **WHEN** a reader opens the entry in either language
- **THEN** it is named CzBIRD and shown as in development, dated by the NKR snapshot, with NKR credited
- **AND** the curated functions, operator and abbreviation remain

#### Scenario: NKR leaves the address empty

- **GIVEN** a curated entry with a working address, joined through its reviewed NKR handle to an NKR record whose address is empty
- **WHEN** the catalogue is built
- **THEN** the entry keeps the curated address and still links to its NKR record

#### Scenario: NKR matches an address with a reviewed annotation

- **GIVEN** an NKR record at a raw source address whose re3data entry has a reviewed name and address override
- **WHEN** the catalogue is built and duplicate-checked
- **THEN** the NKR record joins once using its own address and supplies its own non-empty name and address without receiving the annotation's facts

#### Scenario: A record without an address and without a reviewed handle

- **GIVEN** an NKR record with an empty address that no entry names by its NKR handle
- **WHEN** the catalogue is built
- **THEN** the record does not join an entry with a similar name, and is listed as its own entry

#### Scenario: An abbreviation already in the name

- **GIVEN** an entry with the abbreviation "MBDB" whose NKR name is "Molecular Biophysics Database - MBDB"
- **WHEN** the entry's name is shown
- **THEN** the abbreviation is not added to it a second time

### Requirement: A repository not yet public is listed with its NKR record

An NKR repository with no address that joins no entry SHALL be listed with its status and its NKR record as its only
link, and SHALL say in both languages that it has no public address yet. Only a repository whose status is planned or
in development SHALL be listed without an address of its own.

#### Scenario: A repository in development

- **GIVEN** an NKR record with status development, an empty address and no matching entry
- **WHEN** a reader opens the repository catalogue
- **THEN** the repository is listed as in development, its name opens its entry, the entry links to the NKR record and states that the repository has no public address yet
- **AND** the data-repository chooser does not offer it

#### Scenario: An operational repository without an address

- **GIVEN** an NKR record with status production and an empty address that joins no entry
- **WHEN** the snapshot is refreshed
- **THEN** the refresh rejects the snapshot with a reason naming the record, and the previous snapshot stays unchanged

### Requirement: Links open their exact target

A shortcut or action that names a catalogue entry SHALL open that entry. A shortcut for a topic SHALL open the
catalogue filtered to that topic and the reader's lens, never the unfiltered catalogue. Page checks SHALL follow
every landing shortcut and station action and SHALL fail when one lands anywhere else.

#### Scenario: A shortcut names an entry

- **GIVEN** the data steward's shortcut for training the team
- **WHEN** it is chosen
- **THEN** the catalogue opens on the EOSC CZ training entry

#### Scenario: A shortcut names a topic

- **GIVEN** the community lens's shortcut for domain standards and vocabularies
- **WHEN** it is chosen
- **THEN** the catalogue opens with resources filtered to standards and vocabularies for the community lens

### Requirement: Controls act or say why not

A control that cannot act in the current state SHALL be inactive and SHALL state the reason in visible text beside
it, since an inactive control cannot take focus. It SHALL become active as soon as it can act. This SHALL hold for
pre-fill, test, clear, export, copy and share controls in the checks, the helpers and the catalogue.

#### Scenario: An empty repository maturity check

- **GIVEN** a repository maturity check with no identifier, no sample records and no answers
- **WHEN** it is shown
- **THEN** the re3data pre-fill, sample inspection and test controls are inactive with the reason that an identifier or records are needed, and the export, copy, link and clear controls are inactive until an answer exists

### Requirement: Landing shortcuts name the reader's situation

The landing's shortcuts for each lens SHALL be phrased as the reader's situation, such as having a grant that
requires a data management plan or wanting to share sensitive data, and SHALL lead to the step and action that
answer it. The guide SHALL NOT add a separate wizard.

#### Scenario: A researcher with a grant

- **GIVEN** a researcher on the landing
- **WHEN** they choose the shortcut for a grant that requires a data management plan
- **THEN** the planning step opens, and its next action leads to the data management plan tool

### Requirement: The reader marks the steps they have read

The rail and the life-cycle journey SHALL offer, on every step, a keyboard-operable control that sets and clears a read
mark for that step. No step SHALL carry a read mark until the reader sets one, and opening a step SHALL NOT mark it.
Every visible copy of a step's mark SHALL agree after the reader changes it. Deleting the guide's local data SHALL
remove every read mark. The self-check's own marks and the "last read" resume SHALL be unaffected.

#### Scenario: A reader sets and clears a mark

- **GIVEN** a reader on the licence step, with the planning step unmarked
- **WHEN** they set the read control beside the planning step and then clear it
- **THEN** the planning step first carries the read mark in text and visually and then carries none, no other step's mark changes, and no step is marked merely because it was opened

### Requirement: EOSC CZ Node membership is visible

An entry that belongs to the EOSC CZ Node SHALL carry a badge naming the node and the entry's state (a node
service, integration planned for a stated milestone, or an incubator service), with the date it was checked and a
link to its source. The catalogue SHALL offer a facet for node membership. The badge SHALL NOT claim more than
its source states.

#### Scenario: A repository with planned integration

- **GIVEN** the Czech Social Science Data Archive, listed in the node charter for integration by month 12
- **WHEN** it is shown in the repository catalogue
- **THEN** it carries the EOSC CZ Node badge with the planned integration and its milestone, the date checked and a link to the charter

### Requirement: Names appear in the reader's language with their abbreviations

Repository and research-infrastructure names SHALL appear in the reader's language with that language's
abbreviation where one exists; the other language's form SHALL remain available on the entry. Search SHALL match
every name and abbreviation in both languages.

#### Scenario: A Czech reader finds a repository by abbreviation

- **GIVEN** the Czech Social Science Data Archive
- **WHEN** a Czech reader opens the repository catalogue and searches for "CSDA"
- **THEN** the entry reads "Český sociálněvědní datový archiv (ČSDA)" and is found by "CSDA" and by "ČSDA"

### Requirement: Guide and FER catalogue read as one

The guide and the FIP Dashboard SHALL be usable as two facets of one service. Every FAIR-enabling resource the
guide mentions SHALL link to its dashboard record where one exists and show whether NRP or EOSC CZ has qualified
it. The principle explorer SHALL link each principle to the dashboard's resources for that principle, and the
community lens SHALL link to the dashboard's profiles and its convergence matrix. The guide SHALL NOT keep its own
copy of FER facts that the dashboard owns.

#### Scenario: Qualified and unqualified resources

- **GIVEN** a station that recommends two metadata standards, one verified by EOSC CZ in the dashboard and one only self-declared
- **WHEN** the user reads the station's resources
- **THEN** both link to their dashboard records, and only the first carries the qualification mark, stated in text

#### Scenario: From a principle to its resources

- **GIVEN** the principle F1 in the explorer
- **WHEN** the user follows the catalogue link
- **THEN** the FIP Dashboard opens with its resources filtered to F1

### Requirement: Testing-phase notice

Until the guide is finished and agreed by EOSC CZ, every view SHALL show a visible notice that the guide is in
testing and that its content may change. The notice SHALL be driven by the guide's release status in its content,
SHALL be readable by assistive technology, and SHALL be removed only by a release that records the agreement.

#### Scenario: Visitor during testing

- **GIVEN** the guide's release status is "testing"
- **WHEN** a user opens any view, including one embedded in an iframe
- **THEN** a notice at the top states in the current language that the guide is in testing and not yet agreed by EOSC CZ

### Requirement: Advisory tone and accurate claims

The guide SHALL NOT present a recommendation as an obligation. Where NRP conditions do require something, the
text SHALL say so and name the condition. DOI SHALL be presented as the recommended persistent identifier, and
other persistent, resolvable and managed identifiers (such as Handle, ARK or URN:NBN) as acceptable.

#### Scenario: Persistent identifier advice

- **GIVEN** the publication station in the researcher lens
- **WHEN** it explains persistent identifiers
- **THEN** it names DOI as recommended and states that other managed persistent identifiers are acceptable

### Requirement: Accessibility

The guide SHALL meet WCAG 2.2 level AA, which covers the EN 301 549 baseline that Czech law (zákon
č. 99/2019 Sb.) requires. Text SHALL have a contrast of at least 4.5:1, with brand colours used only for
accents and large text. No information SHALL depend on colour alone. Content SHALL carry correct language
attributes and SHALL reflow at 320 CSS pixels. Motion SHALL respect reduced-motion preferences. The guide SHALL
publish an accessibility statement.

#### Scenario: Status badge

- **GIVEN** a resource with the status "pilot"
- **WHEN** its badge is rendered
- **THEN** the status is conveyed by text and icon, not by colour alone

#### Scenario: Automated audit

- **GIVEN** any station in any lens and language
- **WHEN** the accessibility check runs
- **THEN** it reports no WCAG 2.2 A or AA violations

### Requirement: Accessibility exception for the API documentation

The interactive API documentation page, a third-party developer tool, is exempt from the accessibility
requirement by the maintainer's waiver. The accessibility statement SHALL name it, and the guide's own page for
machines SHALL list the same endpoints accessibly.

#### Scenario: API documentation page

- **GIVEN** the interactive API documentation page
- **WHEN** the accessibility check runs
- **THEN** that page is excluded, and the accessibility statement names it and points to the accessible endpoint list

### Requirement: Languages

The guide SHALL be available in Czech (default) and English, and the user SHALL be able to switch language
without losing their place.

#### Scenario: Language switch

- **GIVEN** a user on the licence station in Czech
- **WHEN** they switch to English
- **THEN** the licence station is shown in English in the same lens

### Requirement: Transparency, acknowledgement and identity

The guide SHALL state in its footer and on an "about" page which AI tools contributed to its content and that
humans reviewed it. It SHALL carry the mandatory NRP acknowledgement in Czech and English. It SHALL use the
official EOSC CZ logo packages and a light theme, and the EOSC CZ logo SHALL link to the EOSC CZ home page.

#### Scenario: About page

- **GIVEN** any user
- **WHEN** they open the about page
- **THEN** it names the AI tools used, the human review, and the NRP acknowledgement text with the project number

### Requirement: Legible, linked logos

The header logo and the funding logolink SHALL be shown at a size at which their text can be read, on a phone as
well as on a desktop. Each logo of the logolink SHALL link to its owner: the EU emblem to the Operational Programme
Johannes Amos Comenius, the ministry logo to the ministry, and the EOSC CZ logo to the EOSC CZ home page. The EU and
ministry pair SHALL stay whole; on a narrow screen the EOSC CZ logo MAY move below it.

#### Scenario: Footer on a phone

- **GIVEN** a user on a 390 pixel wide screen
- **WHEN** they reach the footer
- **THEN** the EU and ministry pair fills the width with its text legible, the EOSC CZ logo follows below at the same scale, and each logo is a link with an accessible name

### Requirement: Credit for content and compilation

Credit SHALL separate the content's basis from compilation. About SHALL contain both complete citations: the FAIR
analysis with its authors and the Guide as software with its compiler as editor. The footer SHALL link to About
without either citation. About SHALL retain analysis authors, compilation/development, editorial review, content
contributors, AI tools and funding. Each station SHALL keep its short sources/provenance line without person names,
linked to full detail.

#### Scenario: Who wrote the content

- **GIVEN** any view
- **WHEN** a user reads the footer
- **THEN** neither complete citation is repeated there, and a clear link opens About at the full credits and citations
- **AND** the footer retains its version/build identity, licence, funding and existing useful navigation

#### Scenario: Roles on the about page

- **GIVEN** a user who follows "Who contributed" in the footer
- **WHEN** the about page opens at its roles
- **THEN** a table names the authors of the analysis with their ORCID iDs, the editor, the editorial review,
  the content contributors with an ORCID link where one is recorded, the tools used and the funding
- **AND** the analysis and Guide are each cited in full once, with their distinct roles, in either language and print

#### Scenario: A content contributor is not a software author

- **GIVEN** a person credited as a content contributor
- **WHEN** a reader compares the about page with the guide's citation and with `CITATION.cff`
- **THEN** the person appears in the content-contributors row and not as the guide's editor or as a software author,
  and a contributor without an ORCID iD appears by name only

### Requirement: Shared callouts

The sensitive-data callout and the identifier-verification callout SHALL each be defined once and reused
wherever they apply, with the order of their items adapted to the lens. A callout SHALL show its question in a
frame that stands out and SHALL open on request.

#### Scenario: Sensitive-data callout in two lenses

- **GIVEN** the sensitive-data callout shown on the licence station
- **WHEN** the lens is researcher and then repository administrator
- **THEN** both lenses show the same callout text, but the repository administrator lens lists the access-infrastructure item first

#### Scenario: A callout on first view

- **GIVEN** a researcher who opens the licence station
- **WHEN** the station is first shown
- **THEN** the sensitive-data callout shows only its question in a framed box, and its advice appears when they open it

### Requirement: Accessible diagrams

Diagrams SHALL use pre-rendered Mermaid or explicitly approved source SVG adaptations. Each SHALL have
an accessible title, description and equivalent adjacent prose. Adapted manuscript figures SHALL preserve
their structure, terminology and scoped status/arrow meanings, with bilingual labels and full-size access.

#### Scenario: Reusing an approved manuscript figure

- **GIVEN** one of the three approved Layers-and-Seams figures
- **WHEN** it appears in the guide
- **THEN** its geometry and meanings remain consistent with the manuscript, diagrams retain their confirmed as-of month, and catalogue observations retain their documented source dates

#### Scenario: Diagram without prose

- **GIVEN** a station that embeds a diagram
- **WHEN** no adjacent prose restates its meaning
- **THEN** the content checks fail

### Requirement: Readable principle references

Wherever the guide names a FAIR principle, it SHALL show the principle's code together with its short title (for
example "R1.2 Provenance") and SHALL link it to the principle explorer. A bare code SHALL NOT appear on its own.

#### Scenario: Principle chips on a station

- **GIVEN** a station that covers R1.1 and R1.2
- **WHEN** its principles are shown
- **THEN** each appears as a code with its short title and links to that principle in the explorer

### Requirement: Visual anchors

The guide SHALL lead the reader with visual anchors: an icon for each station, lens and disclosure level; the
life-cycle journey on the path's start; the "what to do now" level as a prominent card; and principle tiles coloured
by F, A, I and R. Icons and colours SHALL always accompany text, never replace it.

#### Scenario: Station header

- **GIVEN** any station
- **WHEN** it is shown
- **THEN** its header carries the station's icon and name, and the "what to do now" card stands out from the levels below it

### Requirement: External links open in a new tab

Every link to an external URL SHALL open in a new tab and SHALL say so to assistive technology. Links within the
guide SHALL open in place.

#### Scenario: Header logo

- **GIVEN** any view
- **WHEN** the user follows the EOSC CZ logo in the header
- **THEN** eosc.cz opens in a new tab and the guide stays open

### Requirement: Shared icon and colour language

Icons SHALL come from Font Awesome Free, the set eosc.cz uses, vendored as individual SVG files with the
attribution its licence requires. The F/A/I/R colours SHALL follow the FIP Dashboard's scheme, darkened only where
contrast requires it.

#### Scenario: Principle tile next to the dashboard

- **GIVEN** a principle tile for an Interoperable principle in the guide
- **WHEN** it is compared with the same principle in the FIP Dashboard
- **THEN** both use the dashboard's I colour, unless the guide had to darken it to reach the contrast requirement

### Requirement: Self-check marks on the path are explained

When the path rail marks stations that hold open self-check items, the mark SHALL carry a visible explanation (a
label or legend) and SHALL link to the self-check that produced it.

#### Scenario: Mark on a station

- **GIVEN** a user with open self-check items addressed at the working station
- **WHEN** they view the path
- **THEN** the working station is marked, a visible label says that the mark means open self-check items, and the mark leads to that check

### Requirement: Catalogue of everything in the knowledge base

The guide SHALL offer one catalogue listing every kind of entity in its knowledge base: resources and cited sources
as one kind marked by how the guide uses them, repositories, requirements and findings, glossary terms, FIP
profiles, FAIR tests, check questions and content changes. Every requirement identifier the guide shows SHALL link
to its catalogue entry. The principle explorer SHALL stay a separate view. Every item SHALL link to its
machine-readable record in the guide's API.

#### Scenario: A resource that is also cited

- **GIVEN** a user in the catalogue
- **WHEN** they look up DMP.eosc.cz
- **THEN** it appears once, marked as recommended by the guide and as a basis of its content, with the stations that recommend it and the requirements that cite it

### Requirement: Catalogue facets and ordering

The catalogue SHALL be narrowed by facets with counts. Kind SHALL be a single choice showing every kind with its
count; search, station and principle SHALL apply across kinds and stay when the kind changes, and a facet that
belongs to one kind SHALL be labelled with it. The reader SHALL choose the ordering, groups SHALL follow it, and the whole state SHALL be part of
the address.

#### Scenario: Everything about one step

- **GIVEN** a user who chooses the station Licence while looking at resources
- **WHEN** they look at the kinds and then choose requirements
- **THEN** every kind shows how many of its entries concern Licence, kinds without stations show none with the reason, and the requirements open with Licence still chosen

#### Scenario: Following a requirement identifier

- **GIVEN** a researcher reading why a station's advice matters
- **WHEN** they follow the identifier A.F1.N1 under one of the requirements
- **THEN** the catalogue opens on that requirement, with its source, principles, audience and the stations and checks that use it

### Requirement: Catalogue search finds record identifiers

Search SHALL match displayed record identifiers, source identifiers and retained aliases across all catalogue
kinds, using the same case-insensitive matching as descriptive text.

#### Scenario: Looking up a record by its identifier

- **GIVEN** a reader with an identifier shown by any catalogue kind
- **WHEN** they search that kind for the identifier, including a different letter case
- **THEN** its record remains among the matching entries

### Requirement: The machine-readable side is visible

A page for machines SHALL teach machine-actionability by example, for data stewards first. It SHALL lead from a reader's task to the data (the whole knowledge base, one record, a query, an integration, discovery by harvesters, a saved check result). It SHALL show how the Guide applies its own advice, and explain and link the RO-Crate, RDF distribution and query recipes, API documentation and every endpoint, IRI pattern, profile and licence.

#### Scenario: A data steward wants one record

- **GIVEN** a data steward on the page for machines who wants the data about one principle
- **WHEN** they read what the page offers
- **THEN** they find the record's persistent IRI pattern and API address pattern, a working example, and how the guide itself uses the same means

#### Scenario: A data steward wants to ask a question of the whole graph

- **GIVEN** a data steward who wants the advice for one lens across all stations
- **WHEN** they read what the page offers for queries
- **THEN** they find the RDF distribution, the profile that defines what they may query and a recipe that answers that question

#### Scenario: A data steward needs a saved-result question definition

- **GIVEN** a saved result from revisions 1 to 3 that names a question-support document
- **WHEN** the reader compares the accessible endpoint table with the OpenAPI operations
- **THEN** `/api/tests/{id}.json` appears alongside the other operations as the displayed template, and its actual link
  opens a concrete retained question-support document without requiring URI-template substitution by the reader

### Requirement: The guide signposts itself

The Guide's HTML head SHALL carry FAIR Signposting links: the crate and RDF distribution (`describedby`), API description (`service-desc`), API documentation (`service-doc`), licence (`license`), presented type (`type`), editors (`author`), persistent identifier (`cite-as`) once available, and linkset (`linkset`). The linkset SHALL list the same links from the same source. Links SHALL be relative to the site so the Guide can move.

#### Scenario: Harvester discovers the API

- **GIVEN** a harvester that reads the guide's home page
- **WHEN** it inspects the typed links in the HTML head, or the linkset they point to
- **THEN** it finds the crate, the RDF distribution, the OpenAPI description, the API documentation and the licence

### Requirement: Export from every view

Every view SHALL offer printing or saving as PDF, and its content as data: a station, a principle and a check
their record in the API, a list its filtered content as CSV and as JSON in the API's list shape, with a link to each
entry's record. A station SHALL also export as Markdown. The whole knowledge base SHALL be downloadable as the crate
from the page for machines.

#### Scenario: A station as data

- **GIVEN** a user on a station
- **WHEN** they look for the station as data under the view
- **THEN** they find the station's record in the API

#### Scenario: Filtered resource list

- **GIVEN** a user who filtered the resources to the licence station
- **WHEN** they export the list as CSV
- **THEN** the file holds exactly the filtered resources with their links and statuses

### Requirement: Named resources link from text

A catalogue entry named in a text body SHALL be a link to its entry where one exists, styled so that reading is not
disturbed. Editors SHALL mark such references explicitly in the content, and the content checks SHALL reject a
reference to an unknown entry. The knowledge base SHALL keep the text clean, with the referenced entities recorded
as mentions. Addresses required by these synchronous references SHALL remain available without loading an unrelated
catalogue part.

#### Scenario: DataCite in a step

- **GIVEN** a step whose text names DataCite
- **WHEN** the step is shown
- **THEN** "DataCite" links to its resource entry, and the crate records the resource as mentioned by the step without markup in the text

#### Scenario: An infrastructure named before its graph part loads

- **GIVEN** a reader at a station whose advice names CSDA/ESS-CZ, LINDAT/CLARIAH-CZ or ELIXIR CZ while `fips` has not loaded
- **WHEN** the advice is shown
- **THEN** each name links to its infrastructure entry from the initially available issued address

### Requirement: Landing view

The guide's landing view SHALL be the path's start. Below one line on what the guide is and what it builds on, it
SHALL show a universal search box first, then the life-cycle journey, then three or four task shortcuts that change
with the lens, a resume line for a returning visitor, and routes to a data steward and to the FIP Dashboard.

#### Scenario: First visit

- **GIVEN** a first-time visitor in the researcher lens
- **WHEN** the landing view opens
- **THEN** they see the search box, the seven life-cycle stages with their steps, and shortcuts such as checking a dataset and choosing a repository

### Requirement: Life-cycle journey on the landing

The landing SHALL show the life cycle as a cycle: one graphic in which the seven stages form a closed ring in order,
each naming and linking the steps it holds with their icons; an equivalent text list SHALL accompany the graphic.
Choosing a stage SHALL open its first step. The stage of the step a returning visitor last read SHALL be marked in
text as well as visually; before any step was read, no stage SHALL be marked.

#### Scenario: Returning visitor sees where they were

- **GIVEN** a visitor who last read the licence step
- **WHEN** they open the path's start
- **THEN** the sharing stage is marked as last read in text and visually, and the other stages carry no mark

#### Scenario: Before any step is read

- **GIVEN** a visitor who has read no step
- **WHEN** they open the path's start
- **THEN** no stage is marked, and choosing the preservation stage opens the repository step

#### Scenario: The cycle closes

- **GIVEN** any lens and language
- **WHEN** the landing is shown
- **THEN** the seven stages form a ring in which reuse leads back to planning, and the text list names the same stages and steps in the same order

### Requirement: The Guide is named with a capital letter

Text SHALL name this guide with a capital letter wherever the word means it: Průvodce in Czech, the Guide in
English. A generic use, such as a licence selector or a guide to a topic, SHALL stay in lower case. A content check
SHALL flag a lower-case form that is not on a reviewed list of generic uses.

#### Scenario: A sentence about the guide

- **GIVEN** a Czech interface string that says the guide follows the life cycle
- **WHEN** the content checks run
- **THEN** a lower-case "průvodce" in it is reported, while "průvodce licencemi" on the reviewed list is not

### Requirement: Catalogue entries share one visual system

Every catalogue entry SHALL carry its kind's colour, one icon before its title and its fields as labelled rows with
icons in a fixed order. The icon SHALL be the entry's own favicon wherever one can be obtained, kept in the Guide with
its source, otherwise its kind's icon, which the kind facet shows too. The same badges SHALL mark tools in station resources and in the
self-check's evidence.

#### Scenario: Comparing two entries of different kinds

- **GIVEN** a reader looking at a repository and a life-cycle stage in the catalogue
- **WHEN** both entries are shown
- **THEN** each carries its kind's colour, their shared fields appear in the same order with the same icons, and the repository's service badge matches the one beside it in a station's resources

### Requirement: Search results while typing

Results from the guide's own content SHALL appear while the user types, from the second character on. The routes
for a recognised identifier SHALL appear only when the search is confirmed with Enter or the search button, because
they lead to outside services; while the identifier is being typed, a hint SHALL say that it was recognised and how
to continue.

#### Scenario: Typing a term

- **GIVEN** a user who types "licence" without pressing Enter
- **WHEN** they pause typing
- **THEN** the matching steps, principles, resources and terms are listed under the box

#### Scenario: Typing a DOI

- **GIVEN** a user who types a DOI
- **WHEN** they have not pressed Enter yet
- **THEN** a hint says a DOI was recognised and that Enter shows what can be done with it, and no route is offered yet

### Requirement: Universal search

Search SHALL match knowledge base text in both languages, ignoring diacritics, and link to the catalogue with the same query. Typing SHALL send nothing; identifier lookups SHALL require user choice, independently of text indexes. Text results SHALL wait for standards, questions, advice and fips in the selected language. Failed loads SHALL offer retry. Recovery SHALL respect current forms, pending queries, newer input and unrelated errors, retire obsolete search errors, and confirm results once.

#### Scenario: Searching a term

- **GIVEN** a user who types "licence"
- **WHEN** the results appear
- **THEN** they include the licence station, the principle R1.1 and licence resources and terms in both languages, and no request has left the browser

#### Scenario: Pasting a DOI

- **GIVEN** a user who pastes a DOI that the guide cannot place by its form
- **WHEN** they press Enter
- **THEN** the first result offers to find out what the DOI is, and nothing is sent until the user chooses it

#### Scenario: A text-search part fails

- **GIVEN** a text search whose required deferred part fails to load
- **WHEN** the reader confirms the search
- **THEN** a visible error offers retry and a later successful retry shows the results

#### Scenario: Only the FIP text-search part fails

- **GIVEN** a query matching a record supplied only by `fips`, with `standards`, `questions` and `advice` loaded
- **AND** loading `fips` fails
- **WHEN** the reader confirms the search
- **THEN** a visible error offers retry and neither partial nor empty results are confirmed as complete
- **AND** a successful retry includes the FIP-supplied match

#### Scenario: Navigation replaces a failed search form before retry

- **GIVEN** a failed text search whose original form has been replaced by lens navigation
- **WHEN** the reader retries without entering a newer query
- **THEN** the currently attached form shows recovered results for the pending query in the current route, not the detached predecessor
- **AND** completion of an older retry does not overwrite a query entered after navigation

#### Scenario: A replacement was deliberately cleared before retry completed

- **GIVEN** a failed search whose replacement form received a new query that the reader then cleared while retry was pending
- **WHEN** the older retry completes
- **THEN** the replacement stays empty and the older query and its results are not restored

#### Scenario: Retry completes during a deferred language render

- **GIVEN** a Czech text-search retry and a switch to English whose language scripts are still pending
- **WHEN** retry completes before the English form is ready and the scripts then finish
- **THEN** no recovered result is rendered into the outgoing Czech form and the current English form shows the pending query's recovered results

#### Scenario: Text changes to an identifier while its part fails

- **GIVEN** a text submission waiting for a required part whose input the reader replaces with a recognised identifier on the same form
- **WHEN** that text-only part fails
- **THEN** the current identifier's routes appear without another submission and the obsolete text-part failure does not suppress them

#### Scenario: An identifier search needs no text index

- **GIVEN** a recognised identifier while an unrelated text-index part cannot load
- **WHEN** the reader confirms the search
- **THEN** its routes still appear and the part failure is not treated as an identifier result

#### Scenario: Recovery finishes on a view without a search form

- **GIVEN** a failed text search whose retry is pending
- **WHEN** the reader opens a view without a search form, retry finishes there, and the reader then opens a different search-bearing route
- **THEN** the current form receives the pending query and its confirmed results
- **AND** a newer query or deliberate clear in that form is preserved, and a newer submission supersedes the older pending query

#### Scenario: A visible text-search failure is followed by a successful identifier

- **GIVEN** a visible search load error with a retry action after a text-search failure
- **WHEN** the reader confirms a recognised identifier successfully
- **THEN** its routes appear and the obsolete text-search error and retry action are removed
- **AND** a late completion of the older text operation cannot restore that error or replace the newer result

#### Scenario: The reader clears a failed search

- **GIVEN** a visible search load error and a pending query from that failed search
- **WHEN** the reader deliberately clears the current search field
- **THEN** the field and results stay empty, the obsolete search error and retry action are removed, and no older completion restores the query
- **AND** an unrelated load error is not dismissed

#### Scenario: Cold focus loading overlaps confirmation

- **GIVEN** a fresh search whose required local data is still loading after the field receives focus
- **WHEN** the reader confirms a text query before that loading finishes
- **THEN** completion shows one confirmed results update for the current query without an immediately preceding unconfirmed replacement
- **AND** repeating focus and confirmation with unchanged query, language, role and content leaves those results in place

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

### Requirement: Every page is reachable from the main menu

Every page SHALL sit under a main-menu item, and that item SHALL be marked current while the page is shown.
The "Nástroje a postupy" / "Tools and guidance" view SHALL list helpers, AI advice and research-practice
pages with descriptions and any relevant preparation status.

#### Scenario: Opening a helper from the menu

- **GIVEN** a data steward on any view
- **WHEN** they choose "Nástroje a postupy" in the main menu and open "Ověřit identifikátory"
- **THEN** the page opens and "Nástroje a postupy" stays marked as the current menu item

### Requirement: Research practice topics follow the reader's task

The guide SHALL offer bilingual pages for publishing research software, laboratory and field notebooks,
provenance with paradata, and FAIR Digital Objects, linked from the relevant existing stations. The pages
SHALL start with practical actions and explain infrastructure responsibilities. Recommendations SHALL
prioritise EOSC CZ, then European EOSC, then other initiatives, retaining original source ownership.

#### Scenario: Researcher records field observations

- **GIVEN** a researcher at the data collection step
- **WHEN** they follow notebook guidance
- **THEN** laboratory and field work are both addressed, national OSII plans and EOSC CZ training are visible, and an available tool is distinguished from a planned national integration

#### Scenario: Reader needs the reasoning behind a transformation

- **GIVEN** a reader at work or metadata
- **WHEN** they open provenance and paradata
- **THEN** an example connects inputs, tool and version with the reasons for a consequential decision and its uncertainty, with published sources and the guide's own evidence

### Requirement: Kind-specific facets remain inside their family

The repository function facet SHALL appear under the Repositories heading. Changing the selected family SHALL NOT
move the shared Kind facet.

#### Scenario: Reader switches catalogue families

- **GIVEN** a reader switching from resources to repositories
- **WHEN** the repository function choices appear
- **THEN** they appear inside that family section and the Kind facet retains its shared position

### Requirement: New advice fits the role and the complete station

Advice SHALL be edited in the context of the complete station and the responsibility of each affected
role. Additions that duplicate existing advice or supply no useful action for that role SHALL be omitted.
Practical steps SHALL appear in L1; L2 SHALL explain their basis and reasoning. Review SHALL cover the
complete station in every affected lens and both languages, preserving applicable maintainer corrections.

#### Scenario: Researcher creates a processing script

- **GIVEN** a researcher at the processing step
- **WHEN** software advice is added
- **THEN** it explains retaining the version, dependencies and a runnable example within the existing documentation steps, and is conditional on creating software

#### Scenario: A practical action is added to a station

- **GIVEN** a new action relevant to a particular role
- **WHEN** the full station is reviewed in that lens
- **THEN** the action fits the L1 sequence, while its explanatory basis is in L2 rather than another practical checklist

### Requirement: Software preservation guidance accepts appropriate alternatives

Named preservation services SHALL be examples unless a cited requirement prescribes them. The software
check SHALL accept preservation evidence from suitable repositories or other code archives without
requiring SWHID.

#### Scenario: Software is preserved outside Software Heritage

- **GIVEN** a specific source-code release preserved in a suitable repository
- **WHEN** the reader answers the preservation question
- **THEN** the repository evidence is accepted without an SWHID

### Requirement: Public pages explain stable practice and project contributions

Public pages SHALL exclude temporary implementation and prerelease-assessment commentary. OS II pages
and catalogue descriptions SHALL name the project and explain its contribution without administrative
section or deliverable numbers.

#### Scenario: Reader explores notebook support

- **GIVEN** a reader opening notebook guidance or the OS II catalogue entry
- **WHEN** they read about national support
- **THEN** OS II's notebook support, repository connections and provenance tracking are explained without study section numbers

### Requirement: Expanded sections retain content padding

Collapsed sections SHALL retain content padding when opened.

#### Scenario: Reader opens further guidance on a phone

- **GIVEN** a reader on a research-practice page at phone width
- **WHEN** they expand a section
- **THEN** the text and links retain readable spacing from its edges

### Requirement: Station references retain the reader context

Station references SHALL open the path station while retaining the selected language and role.

#### Scenario: Community reader follows a software page to licensing

- **GIVEN** a community reader on the software page in Czech
- **WHEN** they follow the Licence and access reference
- **THEN** the licensing station opens in Czech with the community lens, without routing through the resource catalogue

### Requirement: The whole question has a consistent readable format

Every check SHALL put the criterion and conditions needed to answer before its controls. Useful help,
responsibility, path links, source basis and evidence SHALL use a consistent labelled hierarchy with
details on demand. Original descriptions SHALL remain distinct from guide explanations. This format
SHALL apply to editable and provided questions in both languages with accessible answer-group semantics
and phone reflow.

#### Scenario: A researcher assesses software maintained by another team

- **GIVEN** a software criterion involving maintainer responsibilities
- **WHEN** the researcher reads the question
- **THEN** the criterion, useful evidence guidance and responsible actor are clear without implying that the reader must personally maintain the software

#### Scenario: An NRP-provided answer is displayed

- **GIVEN** a criterion provided by the selected NRP profile
- **WHEN** the question is displayed
- **THEN** its explanation and source remain accessible without an editable answer control

#### Scenario: A question changes state on a phone

- **GIVEN** a question moving between empty, pre-filled, edited, imported, running or failed states
- **WHEN** it is used at phone width in either language with the keyboard
- **THEN** the same hierarchy remains readable, answer controls retain their semantics and focus, and necessary conditions remain visible

### Requirement: Question evidence explains observations and coverage

Evidence SHALL lead with a verified human-readable observation, readable value and what it supports.
Source, date and inspected subject SHALL be accessible. Technical field paths, supporting values and
original probe explanations SHALL be available as details. The user's answer, an automated suggestion,
test outcome and the scope actually inspected SHALL be distinguishable. Unknown technical output SHALL
remain attributable original text without an invented explanation.

#### Scenario: A licence URI pre-fills a question

- **GIVEN** an observed URI for a recognised licence
- **WHEN** the pre-fill is shown beside the criterion
- **THEN** the reader sees the licence name, linked URI, source and supported conclusion, with the original field path available in details

#### Scenario: A passing test covers part of a criterion

- **GIVEN** a probe that verifies only one part of a compound criterion
- **WHEN** its result is displayed beside the question
- **THEN** the verified part and remaining uncertainty are clear and the pass is not presented as verification of the whole criterion

### Requirement: Software and FDO sections have meaningful icons

Software and FDO section groups SHALL use meaningful existing icons consistently in questions, the
running result and the full result, rather than relying on numeric fallback marks.

#### Scenario: A reader follows the PID section through an FDO check

- **GIVEN** an FDO check grouped by its sections
- **WHEN** the reader compares the questions, running result and full result
- **THEN** the PID section retains the same meaningful icon in each view

### Requirement: Assessment hierarchy supports scanning before technical detail

Questions/results SHALL lead with criterion/conditions, answer ownership and useful facts. Source/date/coverage
and next action SHALL precede native IDs, paths and logs. Original wording SHALL remain supplementary and quieter
than its reference. Labelled shared icons/colour SHALL distinguish answers, native verdicts and retrieval health.
Unavailable evidence SHALL NOT imply partial support without observations; necessary conditions SHALL stay visible.

#### Scenario: The citation probe was unavailable

- **GIVEN** a question with no supporting citation observation because its probe could not run
- **WHEN** the evidence panel is read
- **THEN** it explains unavailability and offers direct/manual continuation without claiming that part of the criterion was verified

### Requirement: Optional assessments expose all native results coherently

Provider overviews SHALL show target, date, versions, native result grouping and relevant question links.
Unmapped metrics and subtests SHALL remain inspectable, with their original meanings and source/invocation
links. No combined FAIR percentage or overall radar SHALL be introduced. The same readable hierarchy SHALL
work in both languages, phone widths, keyboard use, print and exported explanations.

#### Scenario: A metric has no Guide question mapping

- **GIVEN** a complete FAIR-Checker assessment containing an unmapped native metric
- **WHEN** the reader inspects the overview
- **THEN** that metric remains accessible with its criterion and native details without suggesting an unrelated Guide answer

### Requirement: Useful visuals are evaluated throughout the Guide

Visual planning SHALL cover the whole Guide beyond the three model figures. Accepted placements SHALL have
a reader question, route/lens, source, one maintained definition and accessible text. Existing navigation and
shared data SHALL be reused where useful; omissions SHALL have reasons. Technical architecture SHALL stay
in maintainer docs when it does not help a reader's task.

#### Scenario: Whole-Guide placement evaluation

- **GIVEN** the Guide's reader and contributor tasks
- **WHEN** diagram coverage is evaluated
- **THEN** it considers lifecycle orientation, object representations, publication/responsibility hand-overs, software release/preservation/citation, evidence-to-answer flow, gate/maturity scope and contributor architecture as well as the model figures

#### Scenario: The same metadata hand-over helps two views

- **GIVEN** two relevant role views using the same publication hand-over facts
- **WHEN** visuals are implemented
- **THEN** they reuse one maintained definition or shared data, preserve scoped meanings and provide suitable readable text in each context

#### Scenario: A historical architecture sketch contains private paths

- **GIVEN** a sketch of planning-hub and product filesystem locations
- **WHEN** public diagram coverage is evaluated
- **THEN** it is excluded from public delivery with its reason recorded, while useful build/contribution explanations use portable repository concepts

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

### Requirement: The glossary terms read as an index

The glossary terms sorted by name SHALL be grouped by initial letter in the language's alphabet, with a row of
letters that move to their groups, and each term SHALL lead to its definition at its source.

#### Scenario: Looking up a term

- **GIVEN** a reader on the glossary terms in Czech
- **WHEN** they choose the letter Č
- **THEN** the list moves to the terms starting with Č, after those starting with C

### Requirement: Glossary definitions are readable and searchable

The terms index SHALL include the Heslář definitions under CC BY 4.0, retaining their original Czech language,
source links and licence attribution. Definitions SHALL be rendered as safe text, searchable in the catalogue and
available in exports. A missing definition SHALL remain missing rather than being invented.

#### Scenario: Reader searches for an explanation

- **GIVEN** a phrase in a Heslář definition that does not appear in its label
- **WHEN** the reader searches the terms catalogue for that phrase
- **THEN** the matching term appears with its original definition, source link and CC BY 4.0 attribution

### Requirement: The path rail explains its marks

The rail SHALL mark a step with the self-check's own icons and colours for each open answer state, with how many
questions are put right there, and SHALL show a legend below it explaining the stage colours, the step being read and
the marks, whether or not any mark is shown.

#### Scenario: A step with missing and partly met answers

- **GIVEN** answers of No and Partly to questions put right at the licence step
- **WHEN** the rail is shown
- **THEN** the step carries one mark for each state with its count, in the self-check's icons, and the legend explains them

### Requirement: Path check badges can be hidden

The path menu SHALL offer a keyboard-operable control to hide self-check badges, shown by default. The choice SHALL
persist locally across navigation, language changes and reloads, without changing answers or step navigation, and
SHALL reset when the Guide's local data is cleared. Desktop and phone menus SHALL share the same choice.

#### Scenario: Reader hides check results to browse the path

- **GIVEN** saved answers that mark steps in the path menu
- **WHEN** the reader turns off check results and reloads the page
- **THEN** the badges remain hidden, the current step and links remain available, and turning results on restores the badges

### Requirement: Switching language or role keeps the reader's place

Switching the language SHALL keep the view, its entry and its part, and checks SHALL offer the role menu, each role
keeping the check's part.

#### Scenario: Switching language on a check's report

- **GIVEN** a reader on a dataset check's report in Czech
- **WHEN** they switch to English
- **THEN** the English report of the same check opens

### Requirement: The tools view separates tools from guidance

The tools view SHALL show interactive tools and guidance as separate groups, tools first, each with a sentence on
what its group holds.

#### Scenario: Opening the tools view

- **GIVEN** a reader on the tools view
- **WHEN** it is shown
- **THEN** the dataset check, the identifier check and the citation helper are listed under tools, and the how-to pages under guidance

### Requirement: Missing links are reported advisably

Checks SHALL offer deterministic ranked link suggestions using specific names, abbreviations and reviewed language variants. They SHALL prefer the longest relevant phrase, suppress generic, self and already-linked matches, and explain context/ambiguity. Each hint SHALL include location, language, excerpt, target, proposed reference and reason. Hints SHALL NOT rewrite prose, alter originals or fail a PR.

#### Scenario: An unlinked tool name

- **GIVEN** a body text that names a catalogue tool without marking a reference
- **WHEN** the advisory report runs
- **THEN** it lists the text and the tool as a possible missing link and the check still passes

#### Scenario: A generic word matches several catalogue labels

- **GIVEN** prose containing the word Data or Description without naming a specific entry
- **WHEN** the advisory report runs
- **THEN** the word does not generate blanket link suggestions to every matching label

### Requirement: The final candidate remains readable on phones

Mobile navigation SHALL show current page, role and testing status without delaying the task. Chips SHALL use compact IDs and titles SHALL name the view. Catalogues SHALL present every match without Show more, retain full source text in search/exports, and lay out all cards in print. Off-screen rendering MAY be deferred with keyboard and browser-search access preserved. Long definitions MAY use disclosures that retain wording, language and attribution.

#### Scenario: A reader opens the full glossary on a phone

- **GIVEN** glossary terms spanning many alphabetical groups
- **WHEN** the catalogue first renders
- **THEN** every matching term is present without another click, and opening a definition
  reveals its unchanged original with attribution

### Requirement: Evidence-source capability counts describe actual coverage

An evidence-source card SHALL derive its potential question coverage from the actual registered mappings/tests
for the selected check scope, including local software, CDIF and FDO tests. Potential coverage SHALL remain
distinct from observed results and SHALL NOT imply a complete answer where a test covers only part.

#### Scenario: The software lookup has registered local tests

- **GIVEN** an unanswered software check with local tests for some selected questions
- **WHEN** its evidence card is shown before any lookup
- **THEN** it states the potential coverage of those questions rather than zero observed results

### Requirement: The rail numbers its stages, not its steps

The path rail SHALL number the life-cycle stages only and SHALL NOT print a number for the steps under them, so the
reader sees one level of numbering. A step's position SHALL remain its ordering, not a printed number.

#### Scenario: Steps under a numbered stage

- **GIVEN** the rail showing the numbered life-cycle stages with the steps under them
- **WHEN** a reader opens the path
- **THEN** each stage shows its number and each step shows no number

### Requirement: Catalogue entries show everything their records carry

Every catalogue entry SHALL show each field its record carries, or the catalogue SHALL exclude that field with a
stated reason. A count SHALL NOT replace the items it counts, and a relation SHALL show on both of its ends. Each
entry SHALL lead to the dated content changes that produced or altered it, which the catalogue's list of changes
holds, so that no entry grows with each change.

#### Scenario: A content change names its people and tools

- **GIVEN** a reader opening a content change in the catalogue
- **WHEN** its entry is shown
- **THEN** it names the person responsible and each tool with its kind and version, an AI model appearing as a tool and never as an author
- **AND** it lists every requirement and source consulted and every item changed, grouped by kind, each linking to its entry, station or page

#### Scenario: A check question shows how it is answered

- **GIVEN** a reader opening a check question in the catalogue
- **WHEN** its entry is shown
- **THEN** it shows who puts it right, when it applies, whether "not applicable" is offered and which sources pre-fill it, with their limits

#### Scenario: A FIP profile shows its declarations

- **GIVEN** a reader opening a FIP profile in the catalogue
- **WHEN** its entry is shown
- **THEN** each declaration appears with its principle, its enabling resource and its status
- **AND** the table can be read across the entry's full width and on a page of its own
- **AND** that resource's entry lists the profile among those that declare it

#### Scenario: An entry leads to the changes that produced it

- **GIVEN** any catalogue entry covered by provenance
- **WHEN** its entry is shown
- **THEN** its corner counts the content changes that produced or altered it and leads to them in the catalogue, each
  dated and leading to the change's entry
- **AND** the entry itself does not list them

#### Scenario: A new field cannot hide

- **GIVEN** a record that gains a field its kind's entry neither shows nor excludes with a reason
- **WHEN** the checks run
- **THEN** they fail and name the kind and the field

### Requirement: Shared facts appear in the same place on every kind

Across kinds, an entry's byline SHALL name who made the work, and labelled rows SHALL name who operates, develops or
provides it. A work's own licence SHALL be a row; the licence of a quoted text SHALL sit beside the quote and be named
from the data. Dates SHALL sit in the details line, a status SHALL be one badge with icon, text and as-of date, and
qualified lists SHALL be rows. The catalogue's own labels SHALL NOT address the reader, since it is not read in a role.

#### Scenario: The same property in the same place

- **GIVEN** a reader comparing a large research infrastructure with a repository in the catalogue
- **WHEN** both entries are shown
- **THEN** each shows its host or operator as an Operated by row

#### Scenario: Two licences kept apart

- **GIVEN** a cited source with a licence and a glossary term that quotes a definition
- **WHEN** both entries are shown
- **THEN** the source shows a Licence row, and the term shows its definition's licence beside the definition, named as the data records it

#### Scenario: A question the self-check puts to the reader

- **GIVEN** a check question that the researcher puts right
- **WHEN** its catalogue entry is shown
- **THEN** who puts it right is named "researcher", the role, not "you"

#### Scenario: Status reads without colour

- **GIVEN** a test's health and a FIP declaration's status
- **WHEN** they are shown
- **THEN** each carries an icon, a text and, where recorded, an as-of date

### Requirement: Browser data belongs to one compatible build revision

The initial KB/UI pair, display-language payloads and deferred neutral/translated parts SHALL carry one build
revision matching the generated document's expectation. The loader SHALL reject missing or incompatible revisions
before merging data. A part and its selected
translation SHALL be accepted together and each contribution SHALL be merged at most once. Versioned local requests
SHALL preserve file, HTTP and iframe operation without external requests on load.

#### Scenario: A cached part comes from another build

- **GIVEN** a usable current view with saved answers and reader input
- **WHEN** a requested neutral or translated part has another or no revision
- **THEN** the graph, configuration, UI and answers retain their accepted state
- **AND** a neutral bilingual loading error offers recovery without asserting an empty source or a failed requirement

#### Scenario: Retry receives corrected matching data

- **WHEN** the rejected payload is corrected and the reader retries
- **THEN** it is fetched again, accepted data is reused and the requested view becomes usable without duplicate entities
- **AND** saved answers remain unchanged

#### Scenario: The initial files belong to different builds

- **WHEN** the Guide starts with an incompatible initial KB/UI pair
- **THEN** it stops normal rendering and provides a bilingual reload action
- **AND** reloading retains saved answers

#### Scenario: Both initial data files are equally stale

- **GIVEN** a document from the current build and matching KB/UI data from an older build
- **WHEN** startup checks the expected revision
- **THEN** no graph, UI or configuration is accepted
- **AND** a bilingual Reload action is offered without an ineffective startup Retry

#### Scenario: A nested consumer module changes

- **WHEN** only a nested assessment script under `assets/js/tests/` changes
- **THEN** the generated revision and versioned requests change

#### Scenario: A script path already contains a query and fragment

- **WHEN** any local script loader versions that path
- **THEN** it preserves the query values and fragment and sets exactly one current revision parameter
- **AND** all loaders use the same URL helper while keeping their established load/retry behavior

### Requirement: Entry actions wait for their deferred evidence

A maturity entry action SHALL retain its re3data target and wait for required questions data before interpreting
the snapshot. Failed loading SHALL use the existing neutral Retry flow and SHALL NOT claim that a record is absent.
Embedded-state checks SHALL exercise the embedded document's own state without requiring shared parent storage.

#### Scenario: A maturity action starts while questions data is delayed

- **GIVEN** a known re3data identifier selected from a cold landing search
- **WHEN** the required questions data is delayed or fails to load
- **THEN** the identifier and authored answers remain available and no missing-record conclusion is recorded
- **AND** successful loading permits pre-fill while failed loading offers the existing Retry behavior

### Requirement: Explain terms where they help the reader

The Guide SHALL link newly imported glossary terms from suitable existing bilingual guidance when a definition
helps the reader's current task. References SHALL preserve the advice's action, cited basis and normative strength.
Terms without a useful placement MAY remain available through the glossary rather than being forced into advice.

#### Scenario: A community records its implementation choices

- **GIVEN** guidance discussing a FAIR Implementation Profile and FAIR enabling resources
- **WHEN** a reader encounters those terms
- **THEN** contextual references open their glossary definitions in either language
- **AND** archival appraisal is not used as a synonym for FAIR assessment, nor succession for any preservation plan

### Requirement: Own-site favicons cover eligible resource kinds consistently

Services, tools, registries, standards, guides and documents SHALL use their own site's vendored favicon wherever
a usable one is obtained, consistently in catalogue entries and existing resource badges. A shared platform or
resolver mark SHALL NOT represent an item hosted there. Missing marks SHALL retain the established kind fallback;
infrastructures SHALL retain their separately reviewed marks. No external request SHALL start on page load.

#### Scenario: CoreTrustSeal has a usable favicon

- **GIVEN** the CoreTrustSeal standard has its own reviewed HTTPS site and a usable favicon
- **WHEN** favicon collection and catalogue rendering run
- **THEN** the normalized local icon appears beside the standard instead of the missing-icon fallback
- **AND** its source and observation date remain recorded without changing its kind, meaning or verification status

#### Scenario: A document is identified through a resolver or shared platform

- **GIVEN** a resource whose only address is a non-homepage item on a guarded resolver or shared platform
- **WHEN** the resource is rendered
- **THEN** it keeps its kind fallback rather than borrowing that platform's mark

#### Scenario: An eligible site has no usable mark

- **GIVEN** a completed acquisition observation finds no usable favicon for an eligible host
- **WHEN** the entry is rendered
- **THEN** it retains the same accessible fallback and remains usable in both languages and print

#### Scenario: NKR alone supplies a repository's site

- **GIVEN** an NKR-only repository with its own usable HTTPS site
- **WHEN** favicon targets are collected
- **THEN** that site's host is included even without a curated, KNAV, FIP Dashboard or re3data entry
- **AND** its NKR catalogue-record URL is not used as the repository's site

#### Scenario: A repository has only its NKR record address

- **GIVEN** a repository without a public site that is linked through its NKR record
- **WHEN** its badge is rendered
- **THEN** it keeps its repository-kind fallback rather than borrowing NKR's favicon
- **AND** the NKR catalogue's own entry may still use its own homepage mark

### Requirement: Registry detail loads when its reader task needs it

Detailed NKR and re3data pre-fill data and repository keyword detail SHALL load on demand through existing local data parts.
The first download in either language SHALL remain within 300 KB gzip with all four reconciled refreshes and
presentation changes. Repository controls and complete search SHALL wait for required data. Source fields,
dates, identities, answers and exports SHALL retain their meanings and values.

#### Scenario: First visit with populated NKR data

- **GIVEN** the reviewed NKR snapshot, the reconciled KNAV, FIP Dashboard and Heslář refreshes and the presentation changes
- **WHEN** a reader opens the landing in Czech or English
- **THEN** the actual initial scripts, styles and selected-language data total at most 307,200 gzip bytes
- **AND** detailed NKR/re3data pre-fill records and repository keywords are absent from that initial payload

#### Scenario: Direct repository check from a local file

- **GIVEN** a fresh local-file or iframe session in either language
- **WHEN** the reader opens the repository check directly
- **THEN** its existing data parts load before the NKR chooser renders
- **AND** every reviewed record retains its source identifier, fields and snapshot date without an empty-NKR notice

#### Scenario: Search needs a deferred keyword

- **GIVEN** a repository keyword not present in its label or other initial text
- **WHEN** a reader searches for that keyword from a cold session
- **THEN** the deferred data loads before complete results are presented
- **AND** the matching repository and its attribution remain available in both languages and exports

#### Scenario: The required local data fails to register

- **GIVEN** saved answers and an unavailable or unregistered required data part
- **WHEN** a reader opens the repository check or searches repository keywords
- **THEN** the existing retry flow preserves usable navigation and answers
- **AND** corrected registration restores the requested view without presenting missing data as an empty source

### Requirement: The bare Guide URL opens the path's start predictably

Opening `index.html` without a hash SHALL select the existing `#/<lang>/<lens>/path/start` lifecycle landing for every
reader, regardless of saved station history. The Path menu and resume action SHALL still use the last-read station.
Changing the default SHALL NOT alter an explicit route without a station or the crate preview's machines exception.

#### Scenario: A first visit opens the bare URL

- **GIVEN** a reader with no saved station history
- **WHEN** they open the Guide at `index.html` without a hash
- **THEN** they see the existing search-and-lifecycle landing selected by `#/<lang>/<lens>/path/start`

#### Scenario: A returning reader opens the bare URL

- **GIVEN** a reader whose saved last-read station is the licence step
- **WHEN** they open the same bare URL
- **THEN** they see that same lifecycle landing rather than automatically opening the licence station
- **AND** the Path menu and resume action still lead to the licence step

#### Scenario: The crate preview remains the exception

- **WHEN** a reader opens `ro-crate-preview.html` without a hash
- **THEN** the machines page appears instead of the lifecycle landing

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

Every address the build issues SHALL have a static bilingual landing page, `id/<address>.html`, readable without
JavaScript and marked with each language. Every issued direct or nested part and term-set member SHALL have one
anchored section, and the page SHALL link into the Guide through `#/id/<address>`. A request for an unknown address
SHALL return a bilingual not-found page that offers the catalogue search and resolves its styles at any depth.

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

#### Scenario: A nested part has one static target

- **GIVEN** a record whose API issues a nested action or a term-set member under a fragment
- **WHEN** a reader opens its landing page at that fragment
- **THEN** exactly one anchored section presents that part, including its nested action or term content

#### Scenario: A deeply nested missing address keeps its styling

- **GIVEN** a browser requesting `/id/resources/no-such-record`
- **WHEN** the server answers with the shared `404.html`
- **THEN** the response is not found, its text appears in both languages and both stylesheets resolve and load from the
  publication's actual root instead of below the missing record

### Requirement: Landing pages present statuses through one model

Every status property specialising `adms:status` SHALL use the landing page's Status field. An API record's actual
status date SHALL accompany the value where present, and no date SHALL be invented for an undated record. Each status
SHALL retain its date's role: ordinary statuses use `statusAsOf`, while `nodeState` prefers `nodeStateSince` when both
are present, so a later verification date cannot replace the Node's operational-state date.

#### Scenario: A registry-created infrastructure shows its ESFRI status

- **GIVEN** HL-LHC's API record naming `esfriStatus = landmark` without an observation date
- **WHEN** its landing page is read without JavaScript
- **THEN** landmark appears in the Status field rather than merely as a related-record link, and no date is fabricated

#### Scenario: A dated status keeps its date

- **GIVEN** an API record whose status includes `statusAsOf`, `nodeStateSince` or `reviewedDate`
- **WHEN** its landing page is shown
- **THEN** that actual date accompanies the value in the Status field

#### Scenario: The Node's state keeps its own date

- **GIVEN** the EOSC CZ Node API record with `nodeStateSince = 2026-10-08` and `statusAsOf = 2026-10-16`
- **WHEN** its landing page is read without JavaScript
- **THEN** the `nodeState` Status field shows the operational-state date, 2026-10-08, rather than the later check date

### Requirement: Landing pages signpost their record

A landing page's head SHALL carry FAIR Signposting links for its record: its persistent IRI (`cite-as`), its API
record (`describedby`), its type (`type`), its licence (`license`) and the Guide as its collection (`collection`).

#### Scenario: A harvester follows a record's typed links

- **GIVEN** a harvester that does not run JavaScript
- **WHEN** it reads the head of DMP.eosc.cz's landing page
- **THEN** it finds the record's persistent IRI as `cite-as` and its API record as `describedby`, without fetching the Guide page

#### Scenario: An action's type expands to its vocabulary

- **GIVEN** a provenance action whose API record carries `prov:Activity`
- **WHEN** a harvester reads the action page's `type` links
- **THEN** it finds `http://www.w3.org/ns/prov#Activity`, and every other compact class expands through its actual
  established-vocabulary mapping rather than a schema.org fallback
