## ADDED Requirements

### Requirement: Station advice is non-repetitive and concise

Advice items within a life cycle station SHALL present distinct recommendations without redundant duplication. Guidance covering tools, checklists, or licensing handbooks SHALL be integrated into the primary recommendation items rather than appended as redundant trailing items. Obsolete or superseded advice identifiers SHALL be recorded as retired in the identifier registry.

#### Scenario: Trailing duplicate advice item removed
- **GIVEN** an advice item that repeats an earlier recommendation in the same station
- **WHEN** the knowledge base is compiled
- **THEN** the recommendation is consolidated into the primary advice item, retaining external links, and the superseded identifier is listed under retired identifiers in the knowledge base.

#### Scenario: AI prompt specialization
- **GIVEN** AI assistance advice items across different stations
- **WHEN** prompts are provided for different life cycle tasks (such as data collection vs. metadata creation)
- **THEN** the prompts SHALL differ materially in objective, instructions, and target output.

