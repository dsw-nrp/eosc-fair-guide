# Informed consent, data appraisal, and team continuity design

## Context

The FAIR Data Guide aims to provide actionable, operational guidance rather than purely abstract FAIR principle restatements. Real-world institutional audits and data steward feedback show that data sharing most frequently fails due to:
- Overly restrictive informed consent signed at the project start.
- Lack of criteria for discarding recomputable pipeline files, leading to storage bloat or confusion.
- Departures of postdocs and PhD students leaving unannotated data on orphaned laptops.

## Decisions

- **Station 1 (Planning):**
  - Add advice `plan.31` for the Researcher lens (`lens = "V"`, `level = "L1"`): Citing `ETHICAL-SEVEN.01` and `RDMKIT.collect.02`, guide researchers to formulate informed consent allowing future reuse (anonymized or controlled access) and avoiding commitments to delete research data needlessly.
  - Add advice `plan.32` for the Researcher lens (`lens = "V"`, `level = "L1"`): Citing `POLICY-MANUAL.02`, `POLICY-MANUAL.04`, and `LAW-328-2025.83`, define clear criteria for long-term preservation (primary measurements, underlying data for publications, analysis scripts) versus recomputable intermediate files.
- **Station 2 (Collection & Processing):**
  - Add advice `collect.22` for the Researcher lens (`lens = "V"`, `level = "L1"`): Citing `EINFRA-DOCS.01`, `POLICY-MANUAL.06`, and `SURVEY-2025.01`, instruct researchers to use institutional/e-INFRA shared storage and execute a handover checklist before a team member leaves.
  - Add advice `collect.23` for the Data Steward lens (`lens = "DS"`, `level = "L1"`): Citing `POLICY-MANUAL.06` and `CESSDA-DMEG.01`, recommend data stewards provide concise offboarding checklists to departing personnel.
- **Identifiers & Provenance:**
  - Register new advice items in `content/identifiers.toml`.
  - Add action `2026-10-18-consent-appraisal` in `content/provenance.toml` with plain string `name` and `description` (conforming to RO-Crate 1.2 compaction requirements) and timestamp after the branch merge base.

## Validation

- `python scripts/register_ids.py` verifies all new IDs are tracked.
- `python scripts/check_content.py --base origin/main` verifies bilingual parity, schema validity, and fresh paradata.
- `python scripts/check_duplicates.py` ensures no duplicate advice texts or IDs.
- `python scripts/build_site.py` builds the site and crate without errors.
- `rocrate-validator validate -p ro-crate-1.2 --skip-availability-check _site` passes cleanly.
