## 1. Content updates

- [x] 1.1 Update `collect.04` in `content/stations/02-collect.toml`.
- [x] 1.2 Update `process.03` and `process.04` in `content/stations/03-process.toml`.
- [x] 1.3 Add `publication.30` to `content/stations/08-publication.toml`.
- [x] 1.4 Register identifiers in `content/identifiers.toml`.
- [x] 1.5 Add provenance action `2026-10-18-formats-packaging` in `content/provenance.toml`.

## 2. Verification

- [x] 2.1 Run `python scripts/register_ids.py`.
- [x] 2.2 Run `python scripts/check_content.py --base origin/main`.
- [x] 2.3 Run `python scripts/check_duplicates.py`.
- [x] 2.4 Build site and validate with `rocrate-validator`.
