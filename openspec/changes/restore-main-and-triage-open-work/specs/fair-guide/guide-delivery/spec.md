# Spec Delta

## ADDED Requirements

### Requirement: A link check judges a rejected HEAD request by its GET answer

The health watch SHALL check a linked address with HEAD. It SHALL repeat the request with GET when HEAD is answered
with HTTP 400, 403, 405 or 501, and SHALL record the outcome of the GET answer together with both methods. A HEAD
answer of 404, 410 or 429, a success or a transport failure SHALL NOT be repeated with GET.

#### Scenario: A server rejects HEAD with HTTP 400

- **GIVEN** a linked address whose server answers HEAD with HTTP 400 and GET with HTTP 200
- **WHEN** the watch checks it
- **THEN** the link is recorded as answering, with the methods `HEAD then GET`
- **AND** an earlier triage finding for that link recovers instead of continuing

#### Scenario: Both methods are refused

- **GIVEN** a linked address answering HEAD and GET with HTTP 403
- **WHEN** the watch checks it
- **THEN** the outcome is access denied and the evidence names `HEAD then GET 403`

#### Scenario: A throttled HEAD request is not repeated

- **GIVEN** a linked address answering HEAD with HTTP 429
- **WHEN** the watch checks it
- **THEN** no GET request is sent and the outcome is rate limited

#### Scenario: A missing address is not repeated

- **GIVEN** a linked address answering HEAD with HTTP 404
- **WHEN** the watch checks it
- **THEN** no GET request is sent and the outcome is broken

## MODIFIED Requirements

### Requirement: Project consistency is audited with actionable fixes

A weekly read-only audit SHALL report open issues or PRs missing from Project #1, issues without a type, a body type
that differs from the native type, Ready issues lacking an area label, Priority, Effort or the planned-issue shape,
triage older than 14 days, Urgent issues without progress, state mismatches and automation or view drift, each with
a link or fix step. The digest that monitoring publishes SHALL be exempt from the triage-age and Ready checks only.
A value the digest takes from an issue body SHALL appear as inert text.

#### Scenario: An open issue is missing from the Project

- **WHEN** an open issue is not a Project item
- **THEN** the audit lists it with the fix command

#### Scenario: A Ready issue is incomplete

- **WHEN** an issue in Ready has no Effort or lacks a planned-issue section
- **THEN** the audit lists the missing parts and links the issue

#### Scenario: Urgent work has not started

- **WHEN** an Urgent issue has stayed in Needs triage or Ready for more than three days
- **THEN** the digest lists it

#### Scenario: A built-in automation is switched off

- **WHEN** a Project automation expected to be on is disabled
- **THEN** the audit names it and the affected items

#### Scenario: The published digest is not triaged

- **WHEN** the digest that monitoring published has stayed in Needs triage for more than 14 days, or is in Ready
  without the planned-issue shape
- **THEN** the audit reports neither
- **AND** it still reports the digest when it is missing from the Project or has no Issue Type

#### Scenario: A person's issue resembles the digest

- **WHEN** an issue opened by a person carries the digest's label or begins with its marker, and has stayed in Needs
  triage for more than 14 days
- **THEN** the audit reports its overdue triage

#### Scenario: A Type row carries Markdown

- **WHEN** an issue's Type row holds a backtick, a link and a mention, and differs from its Issue Type
- **THEN** the digest names the difference with that value as inert text: no link, formatting or notification
