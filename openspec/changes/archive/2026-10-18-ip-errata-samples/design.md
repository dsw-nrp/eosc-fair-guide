# Physical sample metadata, IP exceptions, and errata design

## Context

Editorial analysis demonstrated confusion among researchers regarding:
- Linking datasets back to physical objects in museums, biobanks, or drill cores.
- Reconciling open data obligations with university commercialization pipelines and patent filings.
- How to remediate published data errors without breaking the integrity of persistent identifiers.

## Decisions

- **Station 6 (Metadata):**
  - Refine `metadata.05` (`lens = "V"`, `level = "L1"`): add explicit mentions of project/grant codes for RIV linkage, and physical sample PIDs (IGSN, collection/specimen numbers) and instrument IDs. Sources: `A.I3.R3`, `A.R1.2.N3`, `RDMKIT.collect.02`, `DDRAPP.01`, `CDIF.REC6`.
- **Station 7 (Licensing):**
  - Add advice `licence.31` (`lens = "V"`, `level = "L1"`): guide researchers preparing patent filings or working under industrial trade secrets to liaise with Technology Transfer Offices (TTO), utilize temporary embargos, and cite legal exceptions under Section 83(5) of Act No. 328/2025 Coll. Sources: `LAW-328-2025.83.5`, `POLICY-MANUAL.05`, `COPYRIGHT-LICENCES.04`.
- **Station 8 (Publication):**
  - Refine `publication.05` (`lens = "V"`, `level = "L1"`): prohibit silent file modification or deletion; define 3 clear escalation levels (metadata edits directly on record, versioned deposit with new PID and changelog or patch, tombstone withdrawal only for legal/ethical emergencies). Sources: `A.R1.R3`, `A.I3.R5`, `NRP.M1`, `NRP.M3`, `A.A2.R2`.
- **Identifiers & Provenance:**
  - Register new advice items in `content/identifiers.toml`.
  - Add action `2026-10-18-ip-errata-samples` in `content/provenance.toml` with plain string name/description and timestamp after the branch merge base.

## Validation

- `python scripts/register_ids.py` verifies all new IDs are tracked.
- `python scripts/check_content.py --base origin/main` verifies bilingual parity, schema validity, and fresh paradata.
- `python scripts/check_duplicates.py` ensures no duplicate advice texts or IDs.
- `python scripts/build_site.py` builds the site and crate cleanly.
- `rocrate-validator validate -p ro-crate-1.2 --skip-availability-check _site` passes without errors.
