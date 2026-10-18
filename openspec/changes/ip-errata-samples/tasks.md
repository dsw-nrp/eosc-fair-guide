## 1. Content updates

- [ ] 1.1 Update `metadata.05` in `content/stations/06-metadata.toml`.
- [ ] 1.2 Add `licence.31` to `content/stations/07-licence.toml`.
- [ ] 1.3 Update `publication.05` in `content/stations/08-publication.toml`.
- [ ] 1.4 Register identifiers in `content/identifiers.toml`.
- [ ] 1.5 Add provenance action `2026-10-18-ip-errata-samples` in `content/provenance.toml`.

## 2. Verification

- [ ] 2.1 Run `python scripts/register_ids.py`.
- [ ] 2.2 Run `python scripts/check_content.py --base origin/main`.
- [ ] 2.3 Run `python scripts/check_duplicates.py`.
- [ ] 2.4 Build site and validate with `rocrate-validator`.
