# Guide knowledge base

## ADDED Requirements

### Requirement: Actionable conventions for file organisation, open formats, synthetic samples, and archive packaging

The knowledge base SHALL provide concrete recommendations specifying directory conventions, non-proprietary format alternatives across standard research modalities, synthetic dataset creation for restricted data, and archive packaging guidelines for large file collections.

#### Scenario: File and folder organisation
- **GIVEN** a researcher setting up a project workspace
- **WHEN** consulting Station 2 (Collect)
- **THEN** the guide presents concrete examples of clean directory separation (raw vs. processed vs. scripts vs. outputs) and consistent date-stamped file naming.

#### Scenario: Format conversion and open alternatives
- **GIVEN** data stored in proprietary formats (such as Excel workbooks or Word documents)
- **WHEN** preparing data for preservation and sharing in Station 3 (Process)
- **THEN** the guide enumerates open format equivalents across tabular, textual, audiovisual, and geospatial domains.

#### Scenario: Synthetic sample for restricted data
- **GIVEN** sensitive or restricted research data that cannot be made public
- **WHEN** publishing the metadata and access terms
- **THEN** the guide recommends providing an open synthetic dummy or aggregated sample with matching schema to enable script verification.

#### Scenario: Packaging large file collections
- **GIVEN** a dataset comprising thousands of individual files
- **WHEN** publishing to a repository in Station 8
- **THEN** the guide recommends bundling the files into an archive with an explicit manifest and verifying checksums.
