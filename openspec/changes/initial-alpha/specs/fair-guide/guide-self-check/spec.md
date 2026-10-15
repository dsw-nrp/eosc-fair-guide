## MODIFIED Requirements

### Requirement: Questions and unresolved findings expose relevant hand-overs

Question details SHALL show reviewed model connections beside actor/station information without changing
criterion meaning, source force or framework grouping. Unresolved findings SHALL offer a readable hand-over
using the actual target, criterion, observations, test references/invocations, date, source and relevant actor.
Nothing SHALL be dispatched automatically.

#### Scenario: Inspection is unavailable

- **GIVEN** a question associated with a repository connection whose evidence retrieval failed
- **WHEN** its result and hand-over are inspected
- **THEN** the unavailable inspection and its actual evidence remain explicit and no broken connection or failed requirement is inferred from that retrieval failure

### Requirement: Model associations travel with saved results

Markdown and structured result exports SHALL retain reviewed model associations alongside existing evidence.
Older saved results SHALL remain loadable without pretending that absent model or evidence fields were recorded.

#### Scenario: A result from before model integration is loaded

- **GIVEN** a valid saved result from before model associations were exported
- **WHEN** the current guide loads it
- **THEN** its answers and evidence are preserved and the absence of model fields does not make it invalid

### Requirement: Gate and maturity stay separate

The self-check SHALL keep two axes apart. The NRP onboarding gate answers whether a repository meets the NRP
conditions; FAIR maturity answers how well FAIR principles are met. The self-check SHALL NOT compute or show an
overall score or percentage.

#### Scenario: Repository administrator result

- **GIVEN** a repository administrator who completed both checks
- **WHEN** the result is shown
- **THEN** the gate list and the per-principle maturity view appear separately, and no combined score is shown

### Requirement: A check for each lens

The self-check SHALL offer:

- a dataset check for researchers and data stewards, with a before-publication and an after-publication mode;
- an NRP gate check and a repository maturity check for repository administrators;
- a FIP completeness check for communities.

An optional institution check MAY be offered. Every check item SHALL cite ledger sources.

#### Scenario: Researcher before publication

- **GIVEN** a researcher who has not published yet
- **WHEN** they start the dataset check in before-publication mode
- **THEN** they see planning items (data management plan, repository choice, licence, documentation, sensitive data) instead of items that need a published record

### Requirement: Gate items depend on the repository profile

The gate check SHALL first ask which profile applies: an instance of a core NRP system, an alternative system
on NRP infrastructure, or an independently operated repository. It SHALL show only the conditions that apply
to that profile, and SHALL mark conditions that NRP itself provides for core systems as provided by NRP.

#### Scenario: Core NRP system

- **GIVEN** a repository administrator who selects the core NRP system profile
- **WHEN** the gate list appears
- **THEN** security monitoring and central logging are shown as provided by NRP, not as items to answer

### Requirement: Answers include uncertainty

Each item SHALL accept the answers yes, partly, no and don't know, and "not applicable" where the item allows
it. A "don't know" answer SHALL become a follow-up task naming whom to ask.

#### Scenario: Don't know

- **GIVEN** a researcher unsure whether their repository is harvested by NMA
- **WHEN** they answer "don't know"
- **THEN** the result lists a task to check with the repository or their data steward, with a link to the NMA search

### Requirement: Tiers with a short first view

Items SHALL be tiered as Minimum (following the analysis' minimum for joining the national data
infrastructure), Recommended or Advanced; the gate uses Required and Recommended. The first view SHALL show the
Minimum (or Required) items only, and SHALL say in one sentence what that tier means and how many further items
exist; the other tiers SHALL open on request. A check without Minimum or Required items SHALL show all its items
at once.

#### Scenario: Extended check

- **GIVEN** a user who has answered the Minimum items
- **WHEN** they open the extended check
- **THEN** the Recommended and Advanced items appear without losing the answers already given

### Requirement: Pre-filled answers show their source

The self-check SHALL be able to pre-fill answers: from the repository's NKR record for repository checks, from
DataCite metadata for a dataset's DOI, from live test verdicts, and from the community's FIP for the FIP
completeness check. Each pre-filled answer SHALL show its source and retrieval date, SHALL remain editable, and
SHALL stay marked once the user changes it.

#### Scenario: Pre-fill from NKR

- **GIVEN** a repository administrator who enters their repository's NKR record
- **WHEN** the record lists DOI as a PID type
- **THEN** the persistent-identifier items are pre-answered "yes", labelled as taken from NKR with the date

### Requirement: Evidence beside each criterion

Next to each pre-filled criterion, the self-check SHALL show the evidence it found: the field or test, the actual
value and whether it meets the criterion. The same evidence SHALL appear in the Markdown summary and in the
exported result set, with a link to the record it was read from.

#### Scenario: Evidence beside the criterion

- **GIVEN** a dataset check pre-filled from DataCite
- **WHEN** the licence item is shown
- **THEN** it shows the licence URI found in the DataCite record and that it meets the criterion, and the exported result set records that value for the item

### Requirement: Clearing an identifier

Every identifier field SHALL have a visible control that clears the identifier together with the answers it
pre-filled, keeping the answers the user gave.

#### Scenario: Clearing an identifier

- **GIVEN** a dataset check pre-filled from a DOI, with two answers the user gave by hand
- **WHEN** the user clears the identifier field
- **THEN** the identifier and the answers it pre-filled are removed, and the two hand-given answers stay

### Requirement: FIP pre-fill sources and their mapping

The FIP completeness check SHALL take the community's profile from the FIP Dashboard first, and SHALL fall back to
a published FIP nanopublication for profiles the dashboard does not hold or cannot serve. A FIP declaration SHALL
pre-fill an answer as follows: "in use" gives yes; "planned" and "under consideration"
give partly, with the declaration's status as a note; "to be replaced" gives yes, with a note. A principle with no
declaration SHALL stay unanswered, with a note.

#### Scenario: Pre-fill from the FIP Dashboard

- **GIVEN** a community member who chooses their community's profile in the FIP Dashboard
- **WHEN** the profile declares DOI as "in use" for F1, a metadata profile as "planned" for F2, and nothing for R1.2
- **THEN** the F1 item is pre-answered "yes", the F2 item "partly" with the note "planned", and the R1.2 item stays unanswered with a note, each labelled as taken from the FIP Dashboard with the date

#### Scenario: Fallback to a published nanopublication

- **GIVEN** a community whose FIP is published as a nanopublication but is not in the FIP Dashboard
- **WHEN** the community member enters the FIP's nanopublication identifier
- **THEN** the items for principles with declared resources are pre-answered "yes" with the resources listed, labelled as taken from the nanopublication with the date

### Requirement: Results lead back to the path

The result SHALL show a per-principle view with text labels and a gap list ordered by tier. Each gap SHALL name
where it is addressed (a link to the station and lens) and who can fix it (the user, the curator, the
repository administrator or the community). The path SHALL highlight the stations that hold open gaps.

#### Scenario: Missing licence URI

- **GIVEN** a dataset check where the licence is not given as a URI
- **WHEN** the result is shown
- **THEN** the gap links to the licence station in the user's lens and names the user and the repository as able to fix it

### Requirement: Results export

Results SHALL export as a Markdown summary, as a printable view, and as JSON-LD expressed as an FTR test result
set in a small RO-Crate. Self-check answers and live test verdicts SHALL be part of the same result set.

#### Scenario: JSON-LD export

- **GIVEN** a completed dataset check with live test verdicts
- **WHEN** the user exports JSON-LD
- **THEN** the file contains one test result set that holds both the self-check answers and the live verdicts, with the dataset PID as the assessment target

### Requirement: Answers stay with the user

Answers SHALL be stored only in the user's browser. A shareable link that encodes answers SHALL be created
only when the user asks for it.

#### Scenario: No transmission of answers

- **GIVEN** a user filling in a check
- **WHEN** they answer items
- **THEN** no answer leaves the browser unless the user creates a shareable link or runs a live lookup

### Requirement: Check layout

Beside the questions, a running result SHALL stay in view while the reader scrolls; on narrow screens it SHALL
follow the questions. Items SHALL be grouped by FAIR principle by default, with a control that groups them by the
path step where each is addressed. Group headings SHALL NOT imitate the path's step numbering. The running result
SHALL be collapsible, and the choice SHALL be remembered in the browser.

#### Scenario: Answering on a wide screen

- **GIVEN** a user answering the dataset check on a desktop screen
- **WHEN** they mark the licence item "no"
- **THEN** the running result beside the questions shows R1.1 as a gap at once, without the user scrolling

### Requirement: A check reads as evidence, answers and report

A check SHALL read as three parts that it names and marks as the reader moves through them: evidence, answers and
report. The evidence part SHALL offer one card per evidence source, each stating what it sends to which service and
how long it may take.

#### Scenario: Choosing an evidence source

- **GIVEN** a repository administrator opening the repository maturity check
- **WHEN** the evidence part is shown
- **THEN** separate cards offer the re3data record, sample records with their supported discovery and FAIR Champion tests, and a saved result, each saying what is sent where and how long it may take, and the part is marked as the current one

#### Scenario: Single-object evaluators and repository samples

- **GIVEN** external evaluators that assess a single object and a repository sample containing several records
- **WHEN** the repository maturity check offers its evidence sources
- **THEN** it does not promise sample-wide FAIR-Checker or F-UJI evaluation; single-object assessment remains available in its supported checks, and batching those evaluators over every sample record is explicitly deferred follow-up work (tracked in the release hand-off)

### Requirement: Question cards are compact

Each question card SHALL show the criterion, its principles, answer controls whose states are distinguished by
colour as well as text, one consolidated evidence line, and one disclosure for tests, responsibility, the path step
and sources. Technical request details SHALL appear only inside that disclosure.

#### Scenario: A question with automated tests

- **GIVEN** a maturity question with two FAIR Champion tests
- **WHEN** the card is first shown
- **THEN** the criterion, principles, answer controls and one evidence line are visible, and the tests with their request addresses and documentation appear only when the details are opened

### Requirement: The report is a view of its own

The report SHALL have its own address and SHALL show per-principle distributions of answer states, the gaps grouped
by who fixes them, and the agreement between the reader's answers and the evaluators' observations. It SHALL NOT
show a combined score.

#### Scenario: Opening the report

- **GIVEN** a repository maturity check with answers and attached evaluator results
- **WHEN** the reader opens the report
- **THEN** a view with its own address shows the distribution of answer states per principle, the gaps grouped by who fixes them and where answers and evaluators agree or differ, with no overall score

### Requirement: Each answer can be withdrawn

Every question SHALL offer a control that withdraws its answer. Withdrawing SHALL restore the current suggestion
when one exists and otherwise leave the question unanswered, and SHALL leave other questions untouched.

#### Scenario: Withdrawing a manual answer

- **GIVEN** a question the reader answered Yes, for which re3data suggested Partly
- **WHEN** the reader withdraws the answer
- **THEN** the question shows the Partly suggestion attributed to re3data, and no other answer changes

### Requirement: The running result reaches every question

The running result SHALL list the questions, grouped as the answers part groups them, each with its answer state,
and SHALL move to a question when the reader chooses it; on wide screens it SHALL stay in view beside the questions.

#### Scenario: Jumping to an open question

- **GIVEN** a reader halfway through the maturity check on a wide screen
- **WHEN** they choose an unanswered question in the running result
- **THEN** the page moves to that question's card, and the running result stays in view with the question's state

### Requirement: Answer states have distinct colours

Each answer state SHALL have its own colour, solid in bars and distributions, and Yes and Don't know SHALL differ
clearly in hue. Colour SHALL never be the only carrier of a state.

#### Scenario: A distribution in the report

- **GIVEN** a report whose F principle has answers in every state
- **WHEN** its distribution bar is shown
- **THEN** each state is a solid segment in its own colour, Yes and Don't know are easily told apart, and each segment is also named in text

### Requirement: Test-run details are reachable

Wherever an evaluator's result appears, in a question's evidence line, the running result or the report, the reader
SHALL reach the run's details (request, response summary, log and documentation) in at most two actions.

#### Scenario: From the report to a run

- **GIVEN** a report showing a FAIR Champion result on a question
- **WHEN** the reader opens the result's details
- **THEN** the run's request, response summary, log and documentation are shown without returning to the answers part

### Requirement: Repository samples can come from DataCite

Where a repository registers DOIs with DataCite, the maturity check SHALL offer to draw a random sample of its
records from the DataCite REST API. The sampled DOIs SHALL be shown before any probe runs, each replaceable, and
entering records by hand SHALL remain possible.

#### Scenario: Drawing a sample

- **GIVEN** a repository administrator who named a repository that registers DataCite DOIs
- **WHEN** they ask for a sample
- **THEN** a random set of its DOIs within the sample limit is listed with each record's title, nothing is probed yet, and any record can be replaced before the probes run

### Requirement: Evaluators are recognisable

Each external evaluator SHALL be marked by its own icon wherever its evidence, actions or results appear: its own
favicon wherever one can be obtained, otherwise its catalogue kind's icon. The icon SHALL always accompany the
evaluator's name.

#### Scenario: Evidence from two evaluators on one question

- **GIVEN** a question with observations from FAIR Champion and FAIR-Checker
- **WHEN** its evidence line is shown
- **THEN** each observation carries its evaluator's icon and name, distinguishable at a glance

### Requirement: Institution check

The basic institution check SHALL cover the research data strategy, with the minimum content the Open Science III
call requires before it accepts outputs, and the obligations of the research act. The extended check SHALL add the
action plan and the policy, with the minimum content the call sets when an institution prepares them, and the use of
the national data infrastructure with the people it needs (data steward roles, NMA, NRP, the DMP tool, training).

#### Scenario: Strategy without human resources

- **GIVEN** a data steward whose institution's strategy says nothing about data steward positions
- **WHEN** they answer the strategy block
- **THEN** the result names the gap in the strategy's human-resources area and cites the call's minimum content

### Requirement: Institution check sources

Policy items SHALL be detailed by the EOSC CZ manual for institutional data policies, and items that state a legal
obligation SHALL cite zákon č. 328/2025 Sb., § 83.

#### Scenario: Institution without a retention period

- **GIVEN** a data steward whose institution's policy sets no minimum retention period
- **WHEN** they answer the policy block of the extended check
- **THEN** the result names the gap, cites the call's policy minimum and the manual, and links to the step where retention is addressed

### Requirement: Funded-output profile

The dataset check SHALL offer a funded-output profile with a programme picker: the Open Science III FAIR dataset
output and the Open Science II minizáměr dataset output. Items both programmes require SHALL always show; items
only one programme requires SHALL show when that programme is picked.

#### Scenario: Picking the minizáměr programme

- **GIVEN** a researcher in the funded-output profile
- **WHEN** they pick the minizáměr programme
- **THEN** the shared items show (FAIR metadata, a persistent identifier, a complete NMA record), and the items only Open Science III requires do not

### Requirement: Funded-output gaps cite the programme

Each funded-output item SHALL cite the programme's published rules, and a gap SHALL state that the dataset would
not meet that programme's output requirement.

#### Scenario: Open Science III output without the data steward

- **GIVEN** a dataset check in the funded-output profile with Open Science III picked, pre-filled from a DOI whose metadata name no data steward
- **WHEN** the result is shown
- **THEN** it states that the dataset would not meet the Open Science III output requirement because the data steward is missing as creator or contributor, and cites the call's rules

### Requirement: Local data is explained and deletable

Each check and the self-check overview SHALL say in one short statement that answers stay in this browser and can
be moved as a file or a link, with a disclosure that explains what is stored, where, what is sent to services and
how to move or delete it. One control SHALL delete everything the guide stores in the browser, after a
confirmation.

#### Scenario: A user deletes their data

- **GIVEN** a user with answers in two checks
- **WHEN** they choose to delete all their data in the guide and confirm
- **THEN** both checks are empty, and nothing the guide stored remains in the browser

### Requirement: Results can be loaded back

Both exports SHALL carry the whole state of a check (answers, mode or profile, target, the identifiers entered with
what they describe, and the evidence), the Markdown summary in a comment a reader does not see, so either file loads
back completely in another browser. A loaded file SHALL open as a preview and SHALL replace the user's answers
for that check only on request. A file the guide did not produce SHALL be refused with a message.

#### Scenario: Passing a check to a colleague

- **GIVEN** a data steward who exported a dataset check as JSON-LD and sent the file to a researcher
- **WHEN** the researcher loads the file into the guide in their own browser
- **THEN** they see the answers and evidence as a preview, and can adopt them, which replaces their own answers for that check only

#### Scenario: Starting a check from a saved result

- **GIVEN** a user who opens a check they have not started, before choosing its mode or profile
- **WHEN** they look for a way to start
- **THEN** loading a saved result is offered at the top of the check, beside any public records the check can be filled in from

#### Scenario: Loading back a Markdown summary

- **GIVEN** a user who pre-filled a check from a DOI and saved the Markdown summary
- **WHEN** they load the summary and adopt it
- **THEN** the DOI is back in its field, the line saying what it is shows, and the pre-filled answers keep their evidence

### Requirement: Resolved identifiers say what they are

When an identifier entered in a check resolves, the check SHALL show what it is: for a DOI its title, first author,
publisher, year and type, for a Handle the landing page's title, and for a repository or profile record its name.
The result SHALL name what was checked, and the exports SHALL carry the same description.

#### Scenario: A DOI is looked up

- **GIVEN** a user who enters a dataset DOI and runs the lookup
- **WHEN** DataCite returns the record
- **THEN** the dataset's title, first author, publisher, year and type appear under the field, and the result says it checks that dataset

### Requirement: Repository maturity from re3data

The repository maturity check SHALL accept a re3data DOI, an r3d identifier or a re3data record address, and SHALL
fill in the questions that the record's facts answer from the reviewed re3data snapshot, showing the snapshot's
date. A repository outside the snapshot SHALL be named and linked, with an explanation, and SHALL fill in nothing.

#### Scenario: A Czech repository in re3data

- **GIVEN** a repository administrator who enters the re3data record of a repository in the snapshot
- **WHEN** the check fills in from re3data
- **THEN** the questions on identifiers, the OAI-PMH interface, licences, versioning, certificates and policies are answered from the record, each showing re3data and the snapshot's date

### Requirement: Results carry their format and version

The JSON-LD export and the Markdown summary SHALL declare the result format and its version and the guide's version.
Loading SHALL tell apart a file the guide did not make, a damaged file, a file in a newer format and a file for an
unknown check, each with its own message. Questions the current guide does not know SHALL be skipped with a note.

#### Scenario: A file from an older guide

- **GIVEN** a saved result that includes a question the current guide no longer has
- **WHEN** a user loads it
- **THEN** the preview opens with the other answers and says how many questions were left out

### Requirement: Advisory software and FDO checks

The guide SHALL offer separate software and FDO readiness checks, with manual answers, evidence,
uncertainty, responsible actors, path links and the existing result/export/import behaviour. Neither check
SHALL award certification or a combined score; OpenSSF self-certification SHALL be described as voluntary
and distinct.

#### Scenario: Software release has no preservation reference

- **GIVEN** a researcher checking a script or computational notebook
- **WHEN** they answer that code preservation is unknown
- **THEN** the result gives a practical follow-up and a source, without claiming that a repository URL or development badge proves preservation or FAIR compliance

#### Scenario: DOI alone is supplied as FDO evidence

- **GIVEN** a repository administrator with an object DOI
- **WHEN** they inspect FDO readiness
- **THEN** profiled PID records, registered types and attributes, metadata and infrastructure responsibilities remain separate unanswered criteria until evidenced

### Requirement: Software and FDO questions retain their assessment scope

Software questions SHALL cover exact versions, preservation, licences, dependencies, execution examples,
tests and citation, citing software-specific sources. FDO questions SHALL distinguish object, PID and
infrastructure responsibilities and identify the versioned Proposed Recommendation.

#### Scenario: Researcher asks a provider about infrastructure

- **GIVEN** a researcher using the FDO readiness check
- **WHEN** a PID or infrastructure criterion is unanswered
- **THEN** its responsible actor and source are explicit and an uncertainty answer becomes a follow-up task

### Requirement: Criteria retain the meaning and force of their sources

Questions and answer guidance SHALL preserve the cited source's assessed subject, scope, conditions and
normative strength. Examples, alternatives and context SHALL NOT become extra obligations, and
simplification SHALL NOT lose necessary parts. Not applicable SHALL respect the criterion's conditions.
Automated suggestions SHALL identify whether they support the whole criterion or only part of it.

#### Scenario: An FDO requirement permits several type choices

- **GIVEN** FDO-FDOR8 permits an existing, derived or new type
- **WHEN** its guide question and answer guidance are reviewed
- **THEN** all permitted choices remain valid and documenting the choice is not introduced as another source obligation

#### Scenario: A metadata description lists possible content

- **GIVEN** a published FDO description lists possible metadata categories
- **WHEN** it appears in the readiness check
- **THEN** the description retains that contextual meaning without requiring every category to be present

### Requirement: Pre-fill retains attributable observations and user answers

Pre-fill SHALL retain bounded observations from multiple sources with their subject, date, provenance
and supported scope. Disagreements SHALL remain visible rather than being silently overwritten or merged
into an unsupported conclusion. User-edited answers SHALL survive later lookup and saved-result loading,
remaining distinguishable from automated suggestions. Missing evidence from one source SHALL NOT alone
establish failure of a criterion.

#### Scenario: Registry and landing metadata disagree

- **GIVEN** two sources provide conflicting evidence about the same object
- **WHEN** both are inspected during pre-fill
- **THEN** both observations remain attributable, the disagreement is visible and a manual answer is preserved

### Requirement: Probe explanations and bounded evidence survive export and import

Checks SHALL retain bounded supporting values and per-record probe logs or failure context, shortening
display rather than stored evidence. Readable results and Markdown SHALL explain supported conclusions
and scope; structured exports SHALL retain observations, provenance and original probe text.
Export/import SHALL preserve this evidence within size limits and retain loading of older results.

#### Scenario: A repository sample has one unavailable probe

- **GIVEN** a sample with successful probe logs and one request failure
- **WHEN** the reader inspects, exports and reloads its result
- **THEN** per-record observations and available explanations remain accessible, and the unavailable probe does not count as a failed requirement or a completed test; its diagnostic remains separate from supported FTR verdict values

#### Scenario: A result from before the evidence extension is loaded

- **GIVEN** a valid older result with manual answers, a target identifier and earlier evidence
- **WHEN** the current guide loads it
- **THEN** those values are restored without pretending that the older file contains observations or logs it never retained

### Requirement: CDIF and FDO accept object PIDs with bounded assessment scope

CDIF and FDO SHALL accept an object PID and pre-fill safely supported items from resolver, registry and
supported landing-page evidence. Results SHALL name the object and representation inspected. Unsupported
automatic discovery of another managed PID SHALL leave manual assessment available. Unobserved
infrastructure guarantees SHALL remain unanswered by automation.

#### Scenario: DataCite metadata is available but no CDIF representation is validated

- **GIVEN** a DOI resolving to DataCite metadata and a landing page
- **WHEN** CDIF pre-fill inspects the supported representations
- **THEN** observed metadata is attributed to those representations while profile conformance and unverified required content remain open

#### Scenario: A PID resolves but persistence guarantees are not evidenced

- **GIVEN** an object PID that currently resolves
- **WHEN** FDO pre-fill completes
- **THEN** resolution evidence is shown without answering provider persistence, tombstone or security requirements from that observation alone

### Requirement: Profile and type claims require matching evidence

A registry schema, generic JSON-LD or a declared profile SHALL NOT alone establish CDIF profile conformance
or completeness. A MIME type or free-text type name SHALL NOT alone establish a registered FDO type.
Evidence for these claims SHALL match the inspected subject and representation; observations from
different representations SHALL NOT be merged into unsupported conformance.

#### Scenario: A declared profile has not been validated

- **GIVEN** a landing representation declaring a CDIF profile
- **WHEN** the guide can read the declaration but cannot validate the required content
- **THEN** the declaration is retained as evidence while conformance and completeness remain unverified

#### Scenario: Dataset is only a free-text type label

- **GIVEN** object metadata whose type field contains Dataset without a verified registered-type reference
- **WHEN** FDO pre-fill inspects the type
- **THEN** the label is retained without answering the registered FDO type criterion Yes

### Requirement: Software repository pre-fill reflects only safely derived facts

Software pre-fill SHALL identify the public repository, immutable commit and whether it is development
state or a selected release. Yes SHALL require evidence for the whole criterion; partial observations
SHALL remain partial and unsupported items open. File or badge presence SHALL NOT prove execution,
contributor roles, certification, bundled rights or preservation. Source paths, date, scope and incomplete
inspection SHALL travel with the result.

#### Scenario: A dependency manifest is present

- **GIVEN** a public software repository with a dependency manifest
- **WHEN** pre-fill evaluates the machine-actionable dependencies, build and configuration criterion
- **THEN** the manifest supplies attributed partial evidence unless the whole criterion is safely established

#### Scenario: A citation DOI identifies a paper

- **GIVEN** repository citation metadata whose preferred citation is an article DOI
- **WHEN** pre-fill evaluates software identification and preservation
- **THEN** the article is distinguished from the software version and is not treated as its archival identifier

#### Scenario: A repository contains a root licence and test definitions

- **GIVEN** a root licence file, a tests directory and workflow definitions
- **WHEN** pre-fill evaluates licensing and execution
- **THEN** their presence is attributed without claiming that all bundled third-party rights are settled or that tests have run successfully

### Requirement: Native F-UJI report import has a local preview

F-UJI JSON reports SHALL load through bounded local import without requests/credentials. Preview SHALL
show target, date, software/metric versions and provenance before explicit attachment. Mismatched targets
SHALL NOT silently prefill. Duplicate/historical reports SHALL be distinguishable. Recognized unmapped
versions SHALL retain native evidence without suggestions; malformed/foreign reports SHALL have specific errors.

#### Scenario: An older assessment uses an unmapped version

- **GIVEN** a recognized report for the target whose metric version has no reviewed mapping
- **WHEN** the reader attaches it after preview
- **THEN** its complete native results remain inspectable and existing answers are unchanged

### Requirement: Evaluator results are read as their providers present them

Native statuses, scores, maturity, subtests and diagnostics SHALL remain recorded independently. Each result SHALL
be read as its provider's own interface presents it: F-UJI by its FAIR level (met at the top level, partly met below
it, not established at level 0) and FAIR-Checker by its score (2, 1 and 0 as met, partly met and not met). Where the
report's own status differs from that reading, the Guide SHALL show it.

#### Scenario: F-UJI's unknown at level 0

- **GIVEN** a F-UJI metric at maturity 0
- **WHEN** its result is shown
- **THEN** it is shown as not established at FAIR level 0 of 3, as F-UJI shows it, never as a failure

### Requirement: Native verdicts and reviewed answer suggestions remain separate

A reviewed versioned mapping MAY suggest an answer only from the provider's reading: whole coverage as the
reading, partial coverage Partly when its part is met and No when it fails. No reading SHALL form an overall FAIR
score. A reading that is not established, an unavailable result or an unreviewed version SHALL NOT suggest an
answer, and disagreements SHALL be attributable.

#### Scenario: A F-UJI metric the report marks fail at the top level

- **GIVEN** a F-UJI metric with test status fail, full earned score, maturity 3 and failed unscored subtests
- **WHEN** its result is presented or considered for a question with a reviewed whole mapping
- **THEN** it shows as passed at FAIR level 3 of 3 with the report's status noted, and the question is suggested Yes

#### Scenario: FAIR-Checker's scores through partial mappings

- **GIVEN** a reviewed FAIR-Checker assessment whose partially mapped metrics scored 2, 1 and 0
- **WHEN** its evidence is applied to the questions
- **THEN** the first two suggest Partly and the last No, each beside the reader's own answer without replacing it

#### Scenario: Harvested licence statements have different scopes

- **GIVEN** a report containing a licence URI, another licence name and access-right statements from several sources
- **WHEN** evidence is considered
- **THEN** each statement keeps its source and scope, with no invented effective licence or automatic whole-criterion suggestion from aggregation alone

### Requirement: Answer ownership survives provider state changes

Manual answers SHALL keep reader attribution through provider completion, retry, attachment and source removal.
Observations/proposals SHALL stay inspectable across sources; arrival order SHALL NOT hide relevant facts.
Reset/removal SHALL explain scope and preserve unrelated work. Late results for changed targets/checks SHALL
be discarded. Suggestions from partial evidence SHALL follow the partial-evidence rule and SHALL NOT replace an
answer the reader gave.

#### Scenario: A passing native result follows a manual No

- **GIVEN** a reader's No answer and later supporting DataCite and Champion observations
- **WHEN** the result is shown
- **THEN** No remains attributed to the reader, with the observations and proposals labelled separately rather than credited as the answer's source

### Requirement: Complete accepted evidence has a lossless export route

Accepted assessments SHALL be retained once with question references and complete native fields/source text.
Size limits SHALL be checked before attachment. Compact summaries MAY omit originals only with clear scope
and a complete source download. Accepted reports SHALL NOT be silently truncated for portable budgets.
Export/import SHALL preserve attribution and support existing saved Guide result versions.

#### Scenario: A report fits the import limit but exceeds the compact sharing budget

- **GIVEN** a valid accepted report larger than the compact answer-link budget
- **WHEN** the reader exports or shares the result
- **THEN** a compact summary explains its scope and a separate complete evidence download retains the original native assessment without silent data loss

### Requirement: Follow-up summaries reflect selected question scope

Results SHALL distinguish answered questions from satisfied criteria and unresolved actions. Don't know
SHALL remain a valid answer with follow-up. Summary wording SHALL refer to the selected questions and actual
evidence rather than full FAIR conformance. Introductions SHALL describe the check's actual use of answers
and observations; NRP admission decisions SHALL appear only in their applicable context.

#### Scenario: Every question has an answer but one is unknown

- **GIVEN** a check with thirteen Yes answers and one Don't know
- **WHEN** the summary is shown
- **THEN** it leads with the remaining action and does not claim that nothing is missing merely because all questions are answered

### Requirement: Runs report beside the control that started them

A run's status, its progress and the record a lookup found SHALL be shown in the evidence card whose control
started the run or the lookup, so a reader sees them without leaving the control.

#### Scenario: FAIR Champion tests on a dataset

- **GIVEN** a dataset check whose identifier card offers the FAIR Champion tests
- **WHEN** the reader starts them
- **THEN** the progress bar and the status appear in that card, beside the control

### Requirement: The report's state follows the check's categories

A check organised in blocks SHALL report its state by block first, counting every question once in its block. The
state by FAIR principle SHALL count a question under every group of principles it addresses and SHALL say how many
questions have no FAIR principle.

#### Scenario: A CoreTrustSeal readiness report

- **GIVEN** answers to CoreTrustSeal questions, some of which address several FAIR principles and some none
- **WHEN** the report is shown
- **THEN** its state by block covers every answered question, and each FAIR group counts every question that addresses it

### Requirement: The report says who puts each gap right

The gaps SHALL be grouped by the owners each question names, the rule SHALL be stated above them, and the chosen
role SHALL only put its own group first. The report's evaluator table SHALL name each question and lead from each
response to that question's row in the list of all answers.

#### Scenario: A repository administrator reads the gaps

- **GIVEN** gaps owned by the repository administrator and others
- **WHEN** a reader in the repository administrator's role opens the report
- **THEN** the rule is stated, the repository administrator's group comes first and is marked as their role, and the other groups follow unchanged

### Requirement: The extended switch sets the check's scope

The extended switch SHALL set which questions the check covers for its list, its running result, its report and
the path's marks alike. Answers to questions outside the scope SHALL be kept and counted aside, with a way to switch
the extended check on.

#### Scenario: Switching the extended check off after answering further questions

- **GIVEN** a dataset check with answers to Recommended questions
- **WHEN** the reader switches the extended check off
- **THEN** the list, the running result and the progress show the first tier only, and a note counts the saved answers left out
