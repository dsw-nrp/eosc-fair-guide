# Guide knowledge base

## ADDED Requirements

### Requirement: Practical guidance for physical sample links, patent/commercial exceptions, and immutable errata handling

The knowledge base SHALL provide actionable guidance on linking research datasets to physical sample and instrument identifiers, managing intellectual property and patent filings through embargos and statutory exceptions, and remediating post-publication errors without violating persistent identifier immutability.

#### Scenario: Linking physical specimens and equipment
- **GIVEN** research data gathered from geological, biological, or archaeological specimens
- **WHEN** composing metadata in Station 6 (Metadata)
- **THEN** the guide instructs researchers to link PIDs of physical samples (e.g. IGSN) and instruments alongside grant and article identifiers.

#### Scenario: Commercial research and patent applications
- **GIVEN** research data associated with potential patent filings or industrial commercialization
- **WHEN** consulting Station 7 (Licence)
- **THEN** the guide recommends consulting tech transfer offices, applying temporary embargos, and declaring statutory exemptions under Act No. 328/2025 Coll.

#### Scenario: Error remediation after data publication
- **GIVEN** an error discovered in published dataset files
- **WHEN** resolving the error in Station 8 (Publication)
- **THEN** the guide prohibits silent replacement or deletion, directing researchers to metadata correction, version incrementation with linked PIDs, or tombstone withdrawal as appropriate.
