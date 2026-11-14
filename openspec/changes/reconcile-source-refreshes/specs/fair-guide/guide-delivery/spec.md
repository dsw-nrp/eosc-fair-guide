## ADDED Requirements

### Requirement: Favicon publication preserves a recoverable verified set

The vendor SHALL stage and validate the complete manifest and images before replacing the active set. Failed
publication SHALL preserve or restore the previous verified set. An interrupted replacement SHALL have a recovery
path before the next integrity guard runs; ordinary failed acquisition SHALL retain prior verified assets.

#### Scenario: Publication stops between directory replacements

- **GIVEN** a verified current favicon set and a complete staged replacement
- **WHEN** publication is interrupted after preserving the old set but before installing the new one
- **THEN** the previous set remains recoverable and the next run restores it before ordinary validation
- **AND** no partial manifest/image set is accepted as a successful publication

#### Scenario: A hard stop leaves an abandoned stage

- **GIVEN** an abandoned staging directory directly under the owned assets directory
- **WHEN** the next single-process vendoring run recovers publication
- **THEN** it removes that generated directory after the ownership and link/reparse checks
- **AND** it preserves the installed verified set and unrelated files
- **AND** the ownership guard remains usable on the declared Python 3.11 minimum

### Requirement: Favicon acquisition has dated outcomes

Favicon collection SHALL record its latest completed attempt per host or reviewed infrastructure key in the
existing generated source manifest, with a checked date, outcome and reason. Outcomes SHALL distinguish a usable
acquisition, completed observation of no usable icon, and a failed attempt. A host without such an observation
SHALL remain unattempted; a timeout or service failure SHALL NOT establish unavailability.

#### Scenario: A host has no usable favicon

- **GIVEN** the host's permitted pages and candidates have been checked and no usable image is found
- **WHEN** collection completes for that host
- **THEN** the manifest records an `unavailable` observation with its checked date and reason
- **AND** the coverage report distinguishes it from a host never attempted

#### Scenario: A host cannot be reached

- **GIVEN** a transient network, rate-limit or service failure prevents a completed acquisition observation
- **WHEN** collection records its outcome
- **THEN** the outcome is `failed`, with its checked date and retry reason
- **AND** the host is not reported as confirmed to have no usable icon

#### Scenario: A usable image is acquired

- **GIVEN** a candidate passes the existing image, normalization and size checks
- **WHEN** collection writes the icon
- **THEN** it records an `available` observation and the existing asset metadata identifies the source, retrieval date,
  local file and hash

### Requirement: Failed favicon refresh preserves verified assets

A refresh that obtains no replacement SHALL retain each previously verified icon's bytes, source and retrieval
date. The latest failed or unavailable observation SHALL remain distinct from that retained asset. Partial
infrastructure refreshes SHALL retain unrelated observations and assets. Existing explicit pruning semantics
SHALL remain the only deliberate removal route.

#### Scenario: A previously available site times out

- **GIVEN** a recorded usable favicon from an earlier observation
- **WHEN** the next attempt fails before obtaining a replacement
- **THEN** the earlier icon remains usable with its original source, bytes and retrieval date
- **AND** a separately dated `failed` observation records the new attempt

#### Scenario: Only infrastructure marks are refreshed

- **GIVEN** recorded service icons and their acquisition observations
- **WHEN** the infrastructure-only refresh runs
- **THEN** service assets and observation dates remain unchanged

### Requirement: Favicon validation reports integrity and coverage honestly

The offline favicon check SHALL validate asset integrity and acquisition-observation identities, dates,
outcomes and reasons without fetching the network. Coverage SHALL distinguish available assets, confirmed
unavailable hosts, failed attempts, unattempted hosts and excluded platforms. Adding a new eligible host SHALL
NOT manufacture an observation or require a network request in offline checks.

#### Scenario: An observation is malformed

- **GIVEN** a duplicate identity, invalid date, unknown outcome or inconsistent acquisition record
- **WHEN** the offline check runs
- **THEN** it fails with the affected identity and invalid field

#### Scenario: Content adds a host that has never been collected

- **GIVEN** a new eligible host with no recorded acquisition observation
- **WHEN** offline checks and coverage reporting run
- **THEN** coverage lists it as unattempted, the page retains its fallback, and no availability verdict is invented

#### Scenario: Collection still has failed attempts

- **GIVEN** a refresh that obtained some icons but could not complete observations for other hosts
- **WHEN** its result is reviewed for completion
- **THEN** available, unavailable, failed and unattempted populations are reported separately
- **AND** the report does not claim the unresolved hosts were confirmed unavailable
