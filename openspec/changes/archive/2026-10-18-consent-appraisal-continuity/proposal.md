# Informed consent, data appraisal, and team continuity

## Why

Practical gaps were identified in Station 1 (Planning) and Station 2 (Collection & Processing):
1. **Informed Consent (Human Subjects):** Researchers frequently promise ethics boards or participants that data will be destroyed after project end or never shared outside the team, inadvertently precluding lawful Open/FAIR archiving. Guidance is needed to craft consent forms that anticipate anonymized archiving or controlled access under "The Ethical Seven".
2. **Data Selection & Appraisal:** Researchers struggle to decide what to preserve long-term versus ephemeral scratch/intermediate results. Guidance is needed to distinguish irreplaceable raw measurements and underlying published data from recomputable intermediate data.
3. **Team Continuity & Handover:** Turnover of doctoral students or research staff often causes data loss ("data stuck on personal laptops"). Explicit handover checklists and shared repository practices are needed for both researchers and data stewards.

## What Changes

- Add `plan.31` in `01-plan.toml` (Researcher lens): guidance on informed consent formulation before human data collection.
- Add `plan.32` in `01-plan.toml` (Researcher lens): guidance on appraisal and selection of data for long-term preservation vs. reproducible intermediate computations.
- Add `collect.22` in `02-collect.toml` (Researcher lens): guidance on storing data in institutional/e-INFRA storage and conducting handover before personnel departure.
- Add `collect.23` in `02-collect.toml` (Data Steward lens): practical handover checklist recommendation for data stewards assisting departing staff.
- Register new identifiers in `content/identifiers.toml`.
- Record an updated provenance action in `content/provenance.toml` with string literal name/description and timestamp strictly greater than base commit.

## Capabilities

### Modified Capabilities

- `fair-guide/guide-knowledge-base`: extended with practical guidance on consent wording, data appraisal, and research team continuity.

## Impact

Strengthens practical execution for human research data, curation efficiency, and research group institutional memory. Fully conforms to WCAG 2.2 contrast, dual-language parity (CS/EN), and RO-Crate 1.2 provenance standards.
