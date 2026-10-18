# Open formats, folder structure, synthetic samples, and packaging

## Why

Practical gaps were identified in Stations 2 (Collect), 3 (Process), and 8 (Publication):
1. **Folder organisation and naming:** General advice needs concrete directory convention examples (`01_raw/`, `02_processed/`, `03_scripts/`, `04_outputs/`, `README.md`) and ISO date-based file naming (`collect.04`).
2. **Open non-proprietary formats:** General advice needs concrete open format recommendations across data types (CSV/Parquet vs. Excel; plain text/Markdown/PDF-A vs. Word; TIFF/PNG, WAV/FLAC, GeoPackage/GeoTIFF) in `process.03`.
3. **Synthetic/dummy data for restricted sets:** For sensitive data under controlled access, providing a small dummy/synthetic dataset with identical schemas allows external researchers to test processing scripts (`process.04`).
4. **Packaging massive file collections:** Repositories struggle with tens of thousands of tiny individual files; packaging them into archives (`.zip`, `.tar.gz`) with manifests and cryptographic checksums (`SHA-256`, `MD5`) prevents upload failure and metadata corruption (`publication.30`).

## What Changes

- Update `collect.04` in `02-collect.toml` with concrete subfolder conventions and ISO date file naming steps.
- Update `process.03` in `03-process.toml` with concrete open formats for tabular, text, image, audio, and geospatial data.
- Update `process.04` in `03-process.toml` with guidance on providing synthetic/dummy samples when data remain restricted.
- Add `publication.30` in `08-publication.toml` for packaging thousands of small files into archives with manifests and checksums.
- Register new identifiers in `content/identifiers.toml`.
- Add an updated provenance action in `content/provenance.toml` with string literal name/description and timestamp strictly greater than base commit.

## Capabilities

### Modified Capabilities

- `fair-guide/guide-knowledge-base`: extended with concrete folder patterns, open format mappings, synthetic sample guidance, and archive packaging instructions.

## Impact

Enhances day-to-day usability for researchers and stewards preparing datasets for deposit. Fully adheres to repository invariants, dual-language parity, WCAG contrast, and RO-Crate 1.2 rules.
