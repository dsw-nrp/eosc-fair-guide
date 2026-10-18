## 1. Content updates

- [ ] 1.1 Update `collect.04` in `content/stations/02-collect.toml`.
- [ ] 1.2 Update `process.03` and `process.04` in `content/stations/03-process.toml`.
- [ ] 1.3 Add `publication.30` to `content/stations/08-publication.toml`.
- [ ] 1.4 Register identifiers in `content/identifiers.toml`.
- [ ] 1.5 Add provenance action `2026-10-18-formats-packaging` in `content/provenance.toml`.

## 2. Verification

- [ ] 2.1 Run `python scripts/register_ids.py`.
- [ ] 2.2 Run `python scripts/check_content.py --base origin/main`.
- [ ] 2.3 Run `python scripts/check_duplicates.py`.
- [ ] 2.4 Build site and validate with `rocrate-validator`.
