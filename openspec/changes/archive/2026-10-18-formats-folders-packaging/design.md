# Open formats, folder structure, and packaging design

## Context

Editorial review revealed that researchers often struggle with the jump from high-level principles (e.g. "use open formats", "organize data cleanly") to actual repository submission. Common pain points include unreadable Excel macros, unannotated multi-level directories, lack of sample data for sensitive cohorts, and failed bulk HTTP uploads of 50,000 micro-files.

## Decisions

- **Station 2 (Collection):**
  - Refine `collect.04` (`lens = "V"`, `level = "L1"`): augment with clear directory structure recommendation (`01_raw/`, `02_processed/`, `03_scripts/`, `04_outputs/`, `README.md`) and standardized date/version naming syntax (`2026-05-14_project_sample03_v01.csv`). Sources: `CESSDA-DMEG.01`, `CDSC-README.01`.
- **Station 3 (Processing):**
  - Refine `process.03` (`lens = "V"`, `level = "L1"`): add explicit format mappings across data types (CSV/UTF-8 or Parquet alongside `.xlsx`; plain text, Markdown, PDF/A alongside `.docx`; lossless TIFF/PNG, WAV/FLAC, GeoPackage/GeoTIFF). Sources: `A.I1.X1`, `MBDB-2026.01`, `LAW-328-2025.83.3`.
  - Refine `process.04` (`lens = "V"`, `level = "L1"`): recommend offering a small synthetic/aggregated dummy sample for restricted datasets so third parties can test scripts without privacy breach. Sources: `RDMKIT.process.02`, `A.A1.2.R2`.
- **Station 8 (Publication):**
  - Add advice `publication.30` (`lens = "V"`, `level = "L1"`): instruct packing collections of thousands of files into `.zip` or `.tar.gz` with an explicit manifest and verifying `SHA-256`/`MD5` checksums. Sources: `CDIF.REC5`, `CDIF.Manifest`, `A.F3.N2`.
- **Identifiers & Provenance:**
  - Register new advice items in `content/identifiers.toml`.
  - Add action `2026-10-18-formats-packaging` in `content/provenance.toml` with plain string name/description and timestamp after the branch merge base.

## Validation

- `python scripts/register_ids.py` verifies all new IDs are tracked.
- `python scripts/check_content.py --base origin/main` verifies bilingual parity, schema validity, and fresh paradata.
- `python scripts/check_duplicates.py` ensures no duplicate advice texts or IDs.
- `python scripts/build_site.py` builds the site and crate cleanly.
- `rocrate-validator validate -p ro-crate-1.2 --skip-availability-check _site` passes without errors.
