# Spec Delta

## MODIFIED Requirements

### Requirement: Statuses are dated

Every status of a service or resource SHALL use the five-level vocabulary (operational, pilot, in
development, planned, prospective) and SHALL carry an as-of date. A status older than the configured freshness
threshold SHALL be reported.

#### Scenario: Stale status

- **GIVEN** a resource whose status as-of date is older than the freshness threshold
- **WHEN** the scheduled health job runs
- **THEN** the maintenance digest lists the resource and its last verified date for maintainer triage

### Requirement: Safe duplicate suggestions are applied only by explicit human action

Safe suggestions SHALL require explicit human action and provenance naming the requester; schedules and ordinary PR checks SHALL NOT apply them. Local repair SHALL validate TOML, replace each target atomically, restore original bytes on handled application or recheck failure, and after success report the exact diff including its provenance action and identifier registration. Failure or no-op SHALL return nonzero. The duplicate rule and accepted groups SHALL NOT change automatically.

#### Scenario: Scheduled refresh meets a duplicate

- **GIVEN** a scheduled source refresh adds a record that duplicates a curated entry
- **WHEN** the refresh completes
- **THEN** the snapshot proposal is unchanged by automation and the suggestion is reported for human action

#### Scenario: Authoritative matches compete for the same field

- **GIVEN** two registry records match one curated entry through different authoritative keys
- **WHEN** the duplicate check proposes links to the same target field
- **THEN** it marks neither competing value safe and no fix changes that field

#### Scenario: A target key already exists

- **GIVEN** a target table already contains the suggested field, even with an empty value
- **WHEN** a fix is considered
- **THEN** no duplicate key is inserted and the original file remains valid TOML

#### Scenario: No local safe change applies

- **GIVEN** content with no applicable safe suggestion
- **WHEN** the local fix command runs
- **THEN** it leaves the content unchanged and returns nonzero

#### Scenario: A maintainer applies the fix

- **GIVEN** a maintainer requests the fix on a same-repository pull request
- **WHEN** the safe suggestion is applied
- **THEN** the change is committed to that branch with a provenance action naming the maintainer, and the checks rerun

#### Scenario: A replacement fails

- **GIVEN** a safe link and a failure while writing its temporary replacement or replacing its target
- **WHEN** the local repair handles the error
- **THEN** the original target bytes are preserved, temporary files are cleaned up and the command reports failure

#### Scenario: Rechecking the completed repair fails

- **GIVEN** one or more files were changed by local duplicate repair
- **WHEN** content loading fails or duplicate errors remain during the final recheck
- **THEN** every changed target is restored to its original bytes and the command returns nonzero

#### Scenario: A later target fails after an earlier target changed

- **GIVEN** multiple safe links affect different files
- **WHEN** applying a later link raises an error
- **THEN** the earlier changes are also restored and no applied-success message is printed

#### Scenario: Cleanup fails after a target was replaced

- **GIVEN** a target was replaced successfully and the following temporary-file cleanup raises an error
- **WHEN** the local repair handles the error
- **THEN** the replaced target is already tracked for rollback and its original bytes are restored without a post-write discovery read

#### Scenario: A valid local repair completes

- **WHEN** all safe links are applied and the content and duplicate rechecks pass, including the identifier register
- **THEN** the command prints the applied working-tree diff, which contains the links, one provenance action naming the responsible person and that action's registration, and returns zero

### Requirement: Content changes record paradata

A pull request SHALL record one Process Run Crate provenance action by default: the person (ORCID where available), every instrument it used (including the AI tool/model), the consulted sources, the entities it produced or changed and the end time, with coverage naming every item it changed; a finer action per batch MAY replace it where a change genuinely needs its own. AI SHALL be an instrument. Provenance coverage SHALL include exactly the kinds compared against the PR merge base.

#### Scenario: Changed advice without a newer action

- **GIVEN** a pull request that changes an advice item's text
- **WHEN** no provenance action that is new since the comparison base, or whose end time moved later since that base, covers that item
- **THEN** the content checks fail and name the item

#### Scenario: A page changes without a newer action

- **GIVEN** a pull request that changes a page's text
- **WHEN** no provenance action that is new since the comparison base, or whose end time moved later since that base, covers that page
- **THEN** the content checks fail and name the page

#### Scenario: A pull request records one action

- **GIVEN** a pull request that changes several content items
- **WHEN** one provenance action covers every item the pull request changed
- **THEN** the content checks pass, and the action names every person and instrument the change used

#### Scenario: The default branch advances after the work ended

- **GIVEN** a pull request whose new action ended before an unrelated commit landed on the default branch
- **WHEN** the merge queue compares it with that newer base
- **THEN** the content checks pass, and the action's end time stays the time the work finished

#### Scenario: An earlier action is reused without new work

- **GIVEN** a pull request that adds a changed item to the coverage of an action already on the base without moving that action's end time
- **WHEN** the content checks run
- **THEN** they fail and name the item

#### Scenario: Initial public provenance is consolidated

- **GIVEN** unreleased preparation actions with the same responsible compiler and attributable instruments/sources
- **WHEN** the initial public state is recorded as one action
- **THEN** all produced-entity coverage and actual instruments/sources remain recorded, original-source authorship stays separate and references to the consolidated action resolve

### Requirement: Provenance coverage agrees with changed-item fingerprints

Every authored entity kind included in freshness comparison SHALL have truthful provenance coverage,
including organizations. Local, exact-base PR and merge-queue comparison SHALL enforce the same coverage contract.
Automatic source retrieval SHALL record source/time/software/run separately from human editorial review.
Human authorship and citation entries SHALL NOT be inferred from an automation account or indiscriminately
assigned to every action in a pull request.

#### Scenario: An organization changes without covering provenance

- **GIVEN** a changed organization included in the base-comparison fingerprints
- **WHEN** content validation runs locally, on the pull request or in the merge queue
- **THEN** it requires a truthful covering action in all three contexts and does not silently exempt the kind

#### Scenario: A merge group holds two content changes

- **GIVEN** two queued pull requests in one merge group, each covering its own changed items with its own new action
- **WHEN** the merge group is checked against its base
- **THEN** each item is covered by its own pull request's action, and neither pull request needs a new end time

### Requirement: Content addressed relative to the site

The API's files SHALL name the guide's own entities and each other by references relative to the file that names
them, never by the site's address, so the guide works unchanged when it moves to another address. Links that leave
the page, such as the test references in an exported result, SHALL take the address the page is served from.
Runtime links SHALL use the Guide window's location, including its channel path, rather than an iframe parent's
location. Offline use SHALL retain usable relative/local references without inventing a public host or exposing
filesystem paths as public identifiers.

#### Scenario: The guide moves

- **GIVEN** the guide published at a new address
- **WHEN** a consumer follows a link in an API record, or the test reference in a result exported there
- **THEN** it reaches the record at the new address, without the guide being rebuilt for it

#### Scenario: The Guide is embedded at a repository subpath

- **GIVEN** the Guide runs in an iframe under a different origin or path from its parent
- **WHEN** a reader opens an API reference, share link or exported test reference
- **THEN** the link follows the Guide's current origin and channel path, not the parent or a predicted public hostname

#### Scenario: The Guide is opened from a local file

- **WHEN** a reader navigates or exports references from `file://`
- **THEN** local/relative behavior remains usable, no filesystem path is represented as a public identifier, and no external request is made on load

## ADDED Requirements

### Requirement: Local duplicate repair resolves a reviewed responsible person

Local repair SHALL record as responsible the reviewed person given with `--person` or, without it, the single
reviewed person whose GitHub account or commit name matches the local Git identity. An unknown or ambiguous identity
SHALL write nothing, return nonzero and name both the `--person` option and the identity-review procedure. Repair
SHALL never invent a person.

#### Scenario: The local Git identity is reviewed

- **GIVEN** a local Git user name listed in one person's reviewed `commitNames`
- **WHEN** the contributor runs the local fix without `--person`
- **THEN** the provenance action names that person and the output says how the person was resolved

#### Scenario: A person is named explicitly

- **WHEN** the contributor runs the local fix with `--person` and a reviewed person ID
- **THEN** that person is recorded regardless of the local Git identity

#### Scenario: The identity is unknown or ambiguous

- **WHEN** the local Git identity matches no reviewed person or more than one
- **THEN** the command writes nothing, returns nonzero and names the `--person` option and the procedure for adding a reviewed identity

### Requirement: Guide semantic publication addresses use the actual location

Guide-owned vocabulary, profile and other absolute publication addresses SHALL derive from the actual deployment
location before verification. Changing the serving address SHALL NOT silently change logical entity IDs or external
vocabulary/source IRIs. Existing absolute Guide IRIs SHALL have an explicit compatibility disposition before
implementation; preview and production SHALL retain the reviewed shared content identities.

#### Scenario: A different origin or repository prefix is deployed

- **WHEN** the build receives the actual publication location
- **THEN** expanded JSON-LD and profile references resolve there, logical content IDs and exact external IRIs retain their identity, and any existing absolute Guide IRI has its reviewed compatibility treatment

#### Scenario: Publication combines production and preview

- **WHEN** verified production content is assembled beside a preview
- **THEN** channel links remain distinct without silently rewriting shared content identity or already verified production metadata

### Requirement: Documentation qualifies reused concepts by namespace

Technical mappings SHALL identify reused concepts by their actual namespace/prefix and resolvable IRI, including
every crate-mapping row. Documentation SHALL distinguish serialized aliases from expanded terms and identify
Guide-owned terms consistently. Namespace explanations SHALL match emitted JSON-LD without renaming stored keys
or normalizing the spelling or scheme of external IRIs.

#### Scenario: A serialized key is an alias for another vocabulary

- **WHEN** documentation explains `publisher`, `attributedTo`, test types or Guide terms
- **THEN** their mappings agree with the emitted context, including `dcterms:publisher`, `prov:wasAttributedTo`, `ftr:Test` and the applicable `sio:`/Guide terms

#### Scenario: A mapping uses an unknown prefix or the wrong vocabulary

- **WHEN** documentation verification compares a planted mapping with expanded generated JSON-LD
- **THEN** it rejects the mismatch and preserves the actual external term IRI exactly
