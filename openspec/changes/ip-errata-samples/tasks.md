## 1. Content updates

- [x] 1.1 Update `metadata.05` in `content/stations/06-metadata.toml`.
- [x] 1.2 Add `licence.31` to `content/stations/07-licence.toml`.
- [x] 1.3 Update `publication.05` in `content/stations/08-publication.toml`.
- [x] 1.4 Register identifiers in `content/identifiers.toml`.
- [x] 1.5 Add provenance action `2026-10-18-ip-errata-samples` in `content/provenance.toml`.

## 2. Verification

- [x] 2.1 Run `python scripts/register_ids.py`.
- [x] 2.2 Run `python scripts/check_content.py --base origin/main`.
- [x] 2.3 Run `python scripts/check_duplicates.py`.
- [x] 2.4 Build site and validate with `rocrate-validator`.
