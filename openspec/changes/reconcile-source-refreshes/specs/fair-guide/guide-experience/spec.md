## ADDED Requirements

### Requirement: Browser data belongs to one compatible build revision

The initial KB/UI pair, display-language payloads and deferred neutral/translated parts SHALL carry one build
revision. The loader SHALL reject missing or incompatible revisions before merging data. A part and its selected
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

## MODIFIED Requirements

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

## ADDED Requirements

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
