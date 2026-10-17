## ADDED Requirements

### Requirement: External calls only on user action

The page SHALL make no call to an external service on load. Every external call SHALL start from an explicit
user action. Calls SHALL go only to an allowlist of hosts, enforced by a Content Security Policy wherever the
hosting allows one.

#### Scenario: Page load

- **GIVEN** a user opening the guide
- **WHEN** the page finishes loading
- **THEN** no request has been sent to any external API

### Requirement: Two-stage live check

The dataset check SHALL first run a quick deterministic stage: resolve the identifier through the DOI or
Handle resolver and read DataCite metadata for DOIs. ORCID and ROR verification SHALL be available through
the linked identifier helper. The FAIR Champion deep check SHALL run only after a second, explicit user
action. The live-check page SHALL open the existing dataset check, sharing its answers and evidence.

#### Scenario: Quick check

- **GIVEN** a user who enters a DOI
- **WHEN** they start the check
- **THEN** the quick stage reports where the identifier resolves and which metadata are present, and the deep check waits for a separate request

### Requirement: Gentle and robust use of FAIR Champion

The deep check SHALL:

- use a curated set of core tests that excludes test families known to be unavailable or not applicable to
  repositories;
- run at most four tests at a time, each with a 60-second timeout;
- make no automatic retries, and offer a manual retry only for tests that returned no result;
- resolve the identifier first, and skip the deep check with an explanation when it does not resolve.

#### Scenario: Identifier does not resolve

- **GIVEN** a user who enters an identifier that the resolver cannot resolve
- **WHEN** they request the deep check
- **THEN** no FAIR Champion test is called, and the page explains that the identifier does not resolve

### Requirement: Outcomes and coverage are honest

Each test SHALL end in one of four states: pass, fail, indeterminate, or no result. A test that timed out or
returned an error SHALL be shown as "no result" and SHALL NOT count as a failed requirement. The result SHALL
always state its coverage: how many of the run tests returned a verdict.

#### Scenario: Service timeout

- **GIVEN** a deep check in which two of ten tests time out
- **WHEN** the results are shown
- **THEN** those two appear as "no result", no requirement is marked failed because of them, and the coverage reads 8 of 10

### Requirement: Test health is maintained as data

The curated test set and the health of each test SHALL be kept as dated data in the knowledge base. Tests that
fail persistently SHALL be hidden from the page. Changes to the set SHALL arrive as pull requests.

#### Scenario: Persistently failing test

- **GIVEN** a test that returned no result in every scheduled health run for the configured period
- **WHEN** the health job runs
- **THEN** it opens a pull request that marks the test unavailable, and the page stops calling it once merged

### Requirement: Narrow test observations suggest a partial answer

A question whose Champion tests inspect only part of its criterion, or whose sample left some records without a
verdict, SHALL receive a suggested answer from the part that was observed: Partly when that part is met, No when it
fails. A question with no verdict at all SHALL stay open. Original verdicts SHALL be retained, the help SHALL name
the limit of the evidence, and portable results SHALL record the partial basis.

#### Scenario: Metadata persistence assumed for a DOI

- **GIVEN** a question about metadata and tombstones after data withdrawal
- **WHEN** a Champion test passes by assuming metadata persistence for a DOI
- **THEN** the guide suggests Partly, the help states that the test did not inspect withdrawal, and the pass is retained as an observation

#### Scenario: A narrow test fails

- **GIVEN** a question whose Champion test inspects only the identifier part of its criterion
- **WHEN** that test fails for the dataset
- **THEN** the guide suggests No, with the failed observation and the scope of the test shown beside the question

#### Scenario: No verdict was obtained

- **GIVEN** a sample in which every record's test timed out
- **WHEN** the results are shown
- **THEN** the question stays open, its coverage reads none, and no answer is suggested

### Requirement: Identifier verification helper

The guide SHALL offer a helper that finds ORCID iDs, DOIs, Handles and ROR IDs in pasted text. It SHALL
validate ORCID and ROR checksums offline, resolve each identifier, and show the name or title it points to,
flagging identifiers that do not resolve. The identifier callout SHALL advise checking identifiers that an AI
produced by scripted resolution (the helper, or a script the AI writes and runs), rather than by distrust alone.

#### Scenario: Valid ORCID of another person

- **GIVEN** pasted text that contains a well-formed ORCID iD
- **WHEN** the helper resolves it
- **THEN** it shows the person's name from the ORCID record, so the user can see whether it belongs to the intended person

### Requirement: Identifier resolution with incomplete title metadata

The helper SHALL render an external record's name or title as text, including titles received from
DataCite and Crossref. It SHALL preserve successful PID resolution when title metadata are unavailable.

#### Scenario: DOI metadata are unavailable

- **GIVEN** a DOI that resolves but whose title metadata cannot be read
- **WHEN** the helper finishes the lookup
- **THEN** it reports the resolved record, links to it and explains that its title is unavailable

### Requirement: Conservative Handle extraction

The identifier helper SHALL recognise Handles in pasted text only through a resolver link or an explicit
`hdl:` prefix. It SHALL explain this input convention and SHALL NOT guess that unlabelled fractions,
dates or numeric path fragments are Handles.

#### Scenario: Ordinary numeric values in pasted text

- **GIVEN** pasted prose containing a date, a fraction and an explicit `hdl:` identifier
- **WHEN** the user finds identifiers locally
- **THEN** only the explicit Handle is offered for resolution

### Requirement: Identifier helper reset

The textarea SHALL contain an accessible control that clears the pasted text, displayed results and
any identifier carried in its route. Discarded lookup responses SHALL NOT restore the cleared view.

#### Scenario: Clear input and its results

- **GIVEN** pasted text and existing or pending lookup results
- **WHEN** the user activates the textarea's clear control
- **THEN** the input and results are empty, the seeded identifier leaves the route, and focus returns to the textarea

### Requirement: DOI title attribution in the identifier helper

The helper SHALL retrieve public title metadata for DataCite and Crossref DOIs through anonymous
connectors and SHALL use a metadata title only when the record's DOI matches the requested DOI.

#### Scenario: Crossref DOI

- **GIVEN** a resolving Crossref DOI without a DataCite record
- **WHEN** the user requests its public record
- **THEN** the helper shows the title from the matching Crossref record

### Requirement: Safe rendering of external data

Responses from external services SHALL be rendered as text. The only markup allowed through is a small set of
inline elements (such as italics in formatted citations), and only after sanitisation. External content SHALL
never be evaluated as script.

#### Scenario: Markup in a response

- **GIVEN** a DataCite response that contains HTML markup in a title
- **WHEN** the page renders the title
- **THEN** the markup is shown as text or stripped, and no element from the response becomes active

### Requirement: Citation helper

On explicit request, the guide SHALL prepare APA and Czech ISO 690 author–date citations for a DataCite or
Crossref DOI through the reviewed DOI citation formatter, and copyable BibTeX and RIS from the registration
agency. It SHALL verify record identity and requested style availability, render responses as plain text,
and report each unavailable format without substituting another style.

#### Scenario: Citation from DOI

- **GIVEN** a user on the citation station
- **WHEN** they enter a DataCite or Crossref DOI and request a citation
- **THEN** the page shows an APA citation and a Czech ISO 690 citation and offers BibTeX and RIS as copyable text

#### Scenario: Missing style or failed service

- **WHEN** a requested style is absent or a representation cannot be read safely
- **THEN** that format is unavailable, other successful formats remain usable, and the page links to the source
- **AND** the guide advises checking authors, year, version and publisher against the record's page

### Requirement: NMA presence and the RIV link

To check whether a dataset is in the national metadata directory (NMA), the guide SHALL offer a link into the
NMA search pre-filled with the dataset's identifier. It SHALL explain how to obtain the link for RIV
reporting, and that this link SHALL NOT replace the persistent identifier in citations.

#### Scenario: Researcher checks NMA

- **GIVEN** a researcher who entered their dataset DOI
- **WHEN** they choose to check NMA
- **THEN** the NMA search opens with the DOI pre-filled, and the station explains the RIV link and its limits

### Requirement: FIP Dashboard with snapshot fallback

The guide SHALL read FIP Dashboard data from the reviewed snapshot in the crate. Where the dashboard's API admits
the guide's origin, a user action MAY refresh a profile or resource from the API; the guide SHALL then show which
data are live and which come from the snapshot, with their dates. When the API is unreachable or refuses the
origin, the snapshot SHALL be used without an error for the user.

#### Scenario: API refuses the origin

- **GIVEN** the dashboard's API does not allow the guide's origin
- **WHEN** a community member starts the FIP pre-fill from a dashboard profile
- **THEN** the pre-fill uses the snapshot, labelled with the snapshot date, and no error is shown

### Requirement: Graceful degradation

When an external service is unreachable, the page SHALL say which service failed and link to it directly. All
other parts of the guide SHALL keep working.

#### Scenario: DataCite unreachable

- **GIVEN** DataCite does not respond
- **WHEN** a user runs the quick check
- **THEN** the page reports that DataCite is unavailable and links to the DOI landing page, and the self-check stays usable

### Requirement: FAIRsharing records through DataCite

The scheduled source workflow SHALL find FAIRsharing records of the listed repositories through their DataCite DOIs,
matched by the repository's re3data record or address, and keep them in a snapshot; each record SHALL join its
repository's identifiers. The maturity check SHALL answer whether a repository is registered in re3data and
FAIRsharing from the re3data and FAIRsharing snapshots, and SHALL leave the question open with a note without the
FAIRsharing snapshot.

#### Scenario: A repository with a FAIRsharing record

- **GIVEN** a repository administrator who fills in the maturity check from the re3data record of the Czech Social Science Data Archive
- **WHEN** the FAIRsharing snapshot holds its record, found through DataCite
- **THEN** the registration question is answered yes, with evidence linking to the FAIRsharing record

### Requirement: Shared PID discovery inspects supported landing representations

On a user action, shared object discovery SHALL inspect applicable resolver records, registry metadata
and readable landing HTML/JSON-LD, typed links, linksets and declared metadata representations on
reviewed origins. It SHALL validate subject identity and representation scope, preserve attributable
observations and use provider-independent discovery without guessed API paths or hostname-specific behaviour.

#### Scenario: A landing page blocks browser reads but its public API is supported

- **GIVEN** a resolved landing page whose HTML refuses cross-origin access and an observed metadata relation pointing to a readable representation on a reviewed origin
- **WHEN** the user requests object discovery
- **THEN** generic discovery follows that relation and retains attributable record evidence, unreadable representations remain unverified and no unsupported profile claim is inferred

#### Scenario: Linked metadata describes a different object

- **GIVEN** discovered metadata whose subject does not match the target
- **WHEN** pre-fill considers it
- **THEN** it is not used to answer target-object criteria and the mismatch remains explainable

### Requirement: Landing discovery respects browser access limits

Landing discovery SHALL use bounded anonymous requests through reviewed origins and corresponding
generated CSP. Unsupported origins, formats or CORS SHALL leave evidence unverified with a direct link
and a manual route. Discovery SHALL NOT use unrestricted crawling, an arbitrary proxy or opaque responses
to bypass browser access limits.

#### Scenario: A landing origin is unsupported

- **GIVEN** an object whose landing representation cannot be read through a reviewed connector
- **WHEN** the reader requests discovery
- **THEN** that representation remains unverified with a direct link and a manual route, without fetching it through an unrestricted proxy

### Requirement: Landing discovery serves existing object checks without starting deep tests

The dataset check and repository samples SHALL reuse supported object discovery where it supplies relevant
criterion evidence. Sample observations SHALL retain their individual object scope. Quick discovery SHALL
NOT initiate FAIR Champion tests; those SHALL retain their separate explicit user action.

#### Scenario: A repository administrator looks up sample objects

- **GIVEN** a repository sample containing several object PIDs
- **WHEN** the administrator requests quick discovery
- **THEN** relevant supported representations are inspected per object with sample limits stated, and FAIR Champion remains a separate action

### Requirement: Software connectors inspect anonymous public GitHub and GitLab repositories

Software pre-fill SHALL support public GitHub.com and GitLab.com repositories without credentials.
Institutional GitLab hosts SHALL be outside the feature's scope. Requested refs SHALL resolve to an
immutable commit before bounded metadata and selected-file inspection. The connectors SHALL NOT clone,
build or execute repository code or fetch arbitrary linked resources. Rate limiting, pagination,
truncation and unavailable access SHALL be distinguishable from verified absence.

#### Scenario: The default branch changes during assessment

- **GIVEN** a public repository whose default branch can advance
- **WHEN** the user starts software pre-fill
- **THEN** inspected files and evidence refer to the resolved immutable commit rather than mixed branch states

#### Scenario: A public API rate limit prevents inspection

- **GIVEN** a supported repository whose API refuses further reads
- **WHEN** software pre-fill reaches the limit
- **THEN** available observations retain their scope and remaining items stay unverified, without requesting credentials or reporting missing requirements

### Requirement: Standard landing evidence keeps its subject boundaries

Discovery SHALL read supported embedded JSON-LD, Schema.org microdata and declared JSON or text
linksets using generic format handling. Microdata nested items, itemref and machine-readable values
SHALL retain their subject boundaries. Unsupported formats and unreadable browser access SHALL be
disclosed with manual source links; a network/CORS/redirect error SHALL NOT establish absent metadata.
Discovery SHALL NOT guess provider API paths.

#### Scenario: Nested metadata identifies another object

- **GIVEN** a landing page with nested microdata items describing different subjects
- **WHEN** discovery extracts supporting values
- **THEN** properties remain with their declared item and only identity-matched evidence can prefill the inspected object's questions

#### Scenario: Landing HTML is not readable from the guide

- **GIVEN** a readable registry record and a browser failure reading the resolved landing page
- **WHEN** lookup scope is displayed
- **THEN** the registry remains usable, the page is linked for direct inspection and the error explains that the browser cannot establish the presence or absence of page metadata

### Requirement: Evaluation choices are explicit and credential free

The Guide SHALL retain quick discovery/Champion and offer FAIR-Checker/F-UJI with readable scope and target
sharing. External hand-off SHALL use public forms and a copyable identifier unless safe prefill is verified.
No evaluator SHALL run on entry, typing, quick lookup, import preview or incidental navigation. The Guide
SHALL NOT require credentials, an unrestricted proxy or browser access to F-UJI's authenticated API.

#### Scenario: A reader opens the alternate evaluation choices

- **GIVEN** a target PID entered in a self-check
- **WHEN** the reader views the evaluation options
- **THEN** all choices explain scope and target disclosure, and no assessment starts before explicit selection

### Requirement: FAIR-Checker retains the complete native assessment

Optional FAIR-Checker runs SHALL request all twelve native metrics via reviewed anonymous REST connectors/CSP
with bounded concurrency, time and size. They SHALL retain native IDs, criteria, verdicts, scores, timing,
recommendations and diagnostics, including unmapped results. Known API/software/metric versions SHALL stay
distinct. Unavailable/indeterminate results SHALL NOT fail Guide criteria.

#### Scenario: Target changes during an assessment

- **GIVEN** unfinished metrics for an earlier target
- **WHEN** the reader changes the target
- **THEN** late results do not attach to the new target and any retry is bounded to unresolved work for the selected assessment

#### Scenario: Some metrics return no usable result

- **GIVEN** a twelve-metric assessment with successful results and unavailable metrics
- **WHEN** it completes and the reader requests retry
- **THEN** successful native results remain inspectable, only unresolved work is retried within limits and no unavailable metric answers a question No

### Requirement: Provider discovery and mappings preserve subject scope

Evaluator evidence SHALL retain target, subject/representation, source URLs and date. Provider harvest
SHALL be attributed to the provider, not browser retrieval. Evidence SHALL NOT cross from a metadata object,
paper or parent collection to a dataset/software release without a reviewed supporting relation.
Generic RDF or an empty graph SHALL NOT establish profile conformance or metadata absence.

#### Scenario: A provider harvested a browser-inaccessible landing page

- **GIVEN** a F-UJI report with attributed landing-page evidence and a Guide browser fetch blocked by CORS
- **WHEN** that report is attached
- **THEN** the evidence is identified as harvested through F-UJI at its assessment date, while the browser-access limit remains explicit
