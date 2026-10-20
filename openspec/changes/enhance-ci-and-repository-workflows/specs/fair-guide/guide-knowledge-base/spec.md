# Spec Delta

## MODIFIED Requirements

### Requirement: Statuses are dated

Every status of a service or resource SHALL use the five-level vocabulary (operational, pilot, in
development, planned, prospective) and SHALL carry an as-of date. A status older than the configured freshness
threshold SHALL be reported.

#### Scenario: Stale status

- **GIVEN** a resource whose status as-of date is older than the freshness threshold
- **WHEN** the scheduled health job runs
- **THEN** it records the resource and its last verified date in the current maintenance digest for maintainer triage

## ADDED Requirements

### Requirement: Safe duplicate repairs are prepared as complete bundles

A safe duplicate suggestion SHALL prepare its intended link edits, provenance inputs and identifier-registration intent together as a bounded, versioned repair bundle. The bundle SHALL identify its repository, source head, checked revision and input fingerprints. Draft responsibility, action identity and completion time SHALL remain explicitly unresolved until actual application; preparation SHALL change no authored content.

#### Scenario: CI detects the original registry duplicate
- **WHEN** a snapshot record unambiguously matches one curated entry
- **THEN** the prepared bundle identifies the link edit, affected result IDs, consulted registry evidence, repair instrument, provenance draft and registration intent without asserting that the repair occurred

#### Scenario: A suggestion remains ambiguous
- **WHEN** competing records, existing keys or accepted exceptions prevent a safe repair
- **THEN** no applicable bundle is offered for that group and the report retains the exact finding and human-review remedy

#### Scenario: A bundle is malformed or out of date
- **WHEN** a bundle has an unsupported version, exceeds bounds, changes an unapproved path or no longer matches its input identity
- **THEN** it cannot be applied and the diagnostic explains how to prepare current evidence

### Requirement: Duplicate repair application finalizes truthful provenance

Explicit local and trusted duplicate application SHALL use the same bundle semantics and finalize a reviewed responsible person, actual completion time and a nonconflicting action identity. It SHALL produce the required link, covering provenance and registration together. Unknown responsibility SHALL prevent writes and yield a concrete identity-resolution handoff. Existing unrelated provenance and issued or retired IDs SHALL be preserved.

#### Scenario: A local contributor requests a repair
- **WHEN** the contributor explicitly selects a reviewed responsible person and applies a safe repair
- **THEN** the complete proposed diff includes the link, truthful provenance and only the required action-registration change, without a separate manual provenance assembly step

#### Scenario: Local fix is invoked without a responsible person
- **WHEN** local fix is requested without a reviewed person identity
- **THEN** it returns nonzero, writes nothing and gives the exact complete-repair invocation and the procedure for obtaining a reviewed identity

#### Scenario: An existing PR action might be reused
- **WHEN** application considers extending existing provenance
- **THEN** it requires explicit action selection and verifies responsibility and coverage rather than attributing unrelated work to the caller; a separately attributable repair can retain its own scoped action

### Requirement: Complete repair validation precedes publication

A prepared duplicate repair SHALL be finalized and validated against the real content, identifier register and authored validation attachments before any local replacement or remote commit. Application SHALL recheck source identity and preserve unrelated edits. A validation error or precondition failure SHALL publish no repair and leave local authored files unchanged. CI drafts SHALL never be executed as trusted code.

#### Scenario: Provenance registration is omitted
- **WHEN** a proposed repair contains a new action but omits its required registration
- **THEN** the real content validation rejects the complete repair before any authored replacement or remote commit

#### Scenario: Validation attachments are missing
- **WHEN** the checked content references authored attachments absent from the validation input
- **THEN** application stops with the missing-input remedy and does not claim the bundle is valid

#### Scenario: A second contributor changes the input
- **WHEN** the PR head or a relevant local file changes while the complete repair is prepared
- **THEN** application refuses stale publication or replacement and explains how to refresh without overwriting the contributor's work

#### Scenario: Applying an already completed repair
- **WHEN** the intended links and matching provenance are already present
- **THEN** no duplicate action or registration is added and the handoff states whether work remains, preserving the documented nonzero local no-change exit
