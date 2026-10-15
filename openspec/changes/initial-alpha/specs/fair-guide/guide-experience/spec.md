## MODIFIED Requirements

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

The guide SHALL let users filter resources by station, lens, type, status and language. Repositories and registries
SHALL form one catalogue family regardless of whether their records come from the guide's selection, the FIP
Dashboard, re3data, NKR or FAIRsharing, without duplicates.

#### Scenario: Repository listed in two sources

- **GIVEN** a repository present in both NKR and the re3data snapshot
- **WHEN** the finder lists repositories
- **THEN** the repository appears once, with both sources credited, each as a link to its record

### Requirement: Repository and registry functions

A function facet SHALL distinguish data and publication deposit from finding metadata, standards, repositories
or support. An entry MAY have several functions. The data-repository chooser SHALL open data deposit, ordered by
domain, institutional and general-purpose repositories. Source, recommendation and verification SHALL remain
separate facts; inclusion SHALL NOT imply NRP or EOSC CZ qualification.

#### Scenario: Dashboard repository and registry

- **GIVEN** repositories and registries imported from the FIP Dashboard alongside other sources
- **WHEN** the user opens the repositories and registries family
- **THEN** every such thing is available there by meaning, with its functions and source records
- **AND** the data-deposit filter excludes metadata directories and standards registries that do not accept data deposits

#### Scenario: Reviewed cross-registry identity

- **GIVEN** reviewed evidence that differently named records in re3data and the FIP Dashboard describe one thing
- **WHEN** the catalogue lists that thing
- **THEN** one entry carries both records, each borrowed identifier still opens it, and source claims retain their provenance
- **AND** a similar name or hostname alone does not merge records

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

Users SHALL be able to sort resources by name, type, status or the date the status was checked, and repositories
by name, kind or source. Items SHALL carry orientation tags (principle tiles, lens icons), and every data source an
item names SHALL be a live link to the record it came from.

#### Scenario: Sorting by status date

- **GIVEN** a user in the resource finder
- **WHEN** they sort by the date the status was checked
- **THEN** the resources whose status was checked longest ago come first, each still showing its tags and source links

### Requirement: NKR records are shown as found

The scheduled source workflow SHALL bring NKR's repository records into a snapshot, and each SHALL join the matching
catalogue entry, or become an entry of its own when none matches. When NKR lists no repository, the finder and the
repository check SHALL say so with a link to NKR, and SHALL NOT show sample or simulated records.

#### Scenario: NKR lists no repository

- **GIVEN** NKR lists no repository, so there is no NKR snapshot
- **WHEN** a reader opens the repository catalogue
- **THEN** the guide states that NKR lists no repository yet, with a link to NKR, and offers nothing to load

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

Credit SHALL separate the content's basis from the guide's compilation. The footer SHALL credit the authors of the
FAIR analysis the content builds on and SHALL give the guide's own citation as software, naming its compiler in
an editor role. The about page SHALL
list the roles: authors of the analysis, compilation and development, editorial review, AI tools and funding.
Each station SHALL show its sources and provenance as one short line without person names, linking to the full
detail.

#### Scenario: Who wrote the content

- **GIVEN** any view
- **WHEN** a user reads the footer
- **THEN** it credits the authors of the FAIR analysis as the basis of the content and gives the guide's citation with its compiler as editor, so no single person appears as the author of everything

#### Scenario: Roles on the about page

- **GIVEN** a user who follows "Who contributed" in the footer
- **WHEN** the about page opens at its roles
- **THEN** a table names the authors of the analysis with their ORCID iDs, the editor, the editorial review, the tools used and the funding

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

A page for machines SHALL teach machine-actionability by example, for data stewards first. It SHALL start from
what a reader wants to do and lead to the matching data (the whole knowledge base, one record, an integration,
discovery by harvesters, a saved check result), SHALL show how the guide applies its own advice, and SHALL explain
and link the knowledge base (the RO-Crate), the API with its documentation and every endpoint, the guide's profile
and the licence.

#### Scenario: A data steward wants one record

- **GIVEN** a data steward on the page for machines who wants the data about one principle
- **WHEN** they read what the page offers
- **THEN** they find the API record's address pattern, a working example, and how the guide itself uses the same means

### Requirement: The guide signposts itself

The guide's HTML head SHALL carry FAIR Signposting links: the crate (`describedby`), the API description
(`service-desc`), the API documentation (`service-doc`), the licence (`license`), the type of what the page
presents (`type`), the editors (`author`), the guide's persistent identifier (`cite-as`) once it has one, and a
linkset (`linkset`) that lists the same links from the same source. Every link SHALL be relative to the site, so
the guide can move.

#### Scenario: Harvester discovers the API

- **GIVEN** a harvester that reads the guide's home page
- **WHEN** it inspects the typed links in the HTML head, or the linkset they point to
- **THEN** it finds the crate, the OpenAPI description, the API documentation and the licence

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

A catalogue entry named in a text body SHALL be a link to its entry where one exists, styled so that reading is
not disturbed. Editors SHALL mark such references explicitly in the content, and the content checks SHALL reject a
reference to an unknown entry. The knowledge base SHALL keep the text clean, with the referenced entities recorded
as mentions.

#### Scenario: DataCite in a step

- **GIVEN** a step whose text names DataCite
- **WHEN** the step is shown
- **THEN** "DataCite" links to its resource entry, and the crate records the resource as mentioned by the step without markup in the text

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

The landing's search box SHALL search text locally over the knowledge base and route identifiers by what they
denote. Text results SHALL end with a link that opens the catalogue with the same query, which is the full results
page. Matching SHALL ignore diacritics and cover both languages. Typing SHALL send nothing to any service; a service
is called only after the user picks an identifier result.

#### Scenario: Searching a term

- **GIVEN** a user who types "licence"
- **WHEN** the results appear
- **THEN** they include the licence station, the principle R1.1 and licence resources and terms in both languages, and no request has left the browser

#### Scenario: Pasting a DOI

- **GIVEN** a user who pastes a DOI that the guide cannot place by its form
- **WHEN** they press Enter
- **THEN** the first result offers to find out what the DOI is, and nothing is sent until the user chooses it

### Requirement: Identifiers are routed by what they denote

An identifier SHALL be placed without any request where its form or the knowledge base tells what it denotes: a
re3data record or NKR record leads to the repository maturity check, a nanopublication or FIP profile to the FIP
check, a ROR ID to the institution check, an ORCID iD to the identifier helper, and an entry of the guide to its
catalogue entry. A generic DOI or Handle SHALL offer one lookup that says what it is before the fitting check.

#### Scenario: A repository's DOI

- **GIVEN** a user who pastes the DOI of a re3data record
- **WHEN** they press Enter
- **THEN** the first result offers the repository maturity check filled in from re3data, not the dataset check

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

The repository function facet SHALL appear under the Repositories and registries heading. Changing the
selected family SHALL NOT move the shared Kind facet.

#### Scenario: Reader switches catalogue families

- **GIVEN** a reader switching from resources to repositories and registries
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
test ID, it SHALL show it as a chip rather than a bare link. A persistent identifier SHALL keep its scheme and be shown
in full; a chip for an entry of the catalogue SHALL lead to it.

#### Scenario: A repository with records in several registries

- **GIVEN** a repository with a re3data record, a FAIRsharing record and a FIP Dashboard record
- **WHEN** its catalogue entry is shown
- **THEN** each record is a chip naming its scheme, and its sources lead to those registries' catalogue entries

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

Mobile navigation SHALL show current page/role and testing status without delaying the task. Chips SHALL use compact IDs; document titles SHALL identify the current view. Catalogue lists SHALL apply a global initial limit across alphabetical groups, keep every match reachable and retain complete source text in search/exports. Long definitions MAY use disclosures while preserving original wording, language and attribution.

#### Scenario: A reader opens the full glossary on a phone

- **GIVEN** glossary terms spanning many alphabetical groups
- **WHEN** the catalogue first renders
- **THEN** a global initial limit bounds the rendered cards, every term remains reachable, and opening a definition
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
