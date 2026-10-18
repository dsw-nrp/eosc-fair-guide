## 1. Content additions

- [x] 1.1 Add `plan.31` and `plan.32` to `content/stations/01-plan.toml`.
- [x] 1.2 Add `collect.22` and `collect.23` to `content/stations/02-collect.toml`.
- [x] 1.3 Register identifiers in `content/identifiers.toml`.
- [x] 1.4 Add provenance action `2026-10-18-consent-appraisal` in `content/provenance.toml`.

## 2. Verification

- [x] 2.1 Run `python scripts/register_ids.py`.
- [x] 2.2 Run `python scripts/check_content.py --base origin/main`.
- [x] 2.3 Run `python scripts/check_duplicates.py`.
- [x] 2.4 Build site with `python scripts/build_site.py`.
- [x] 2.5 Validate RO-Crate via `rocrate-validator`.
