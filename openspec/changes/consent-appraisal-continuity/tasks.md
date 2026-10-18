## 1. Content additions

- [ ] 1.1 Add `plan.31` and `plan.32` to `content/stations/01-plan.toml`.
- [ ] 1.2 Add `collect.22` and `collect.23` to `content/stations/02-collect.toml`.
- [ ] 1.3 Register identifiers in `content/identifiers.toml`.
- [ ] 1.4 Add provenance action `2026-10-18-consent-appraisal` in `content/provenance.toml`.

## 2. Verification

- [ ] 2.1 Run `python scripts/register_ids.py`.
- [ ] 2.2 Run `python scripts/check_content.py --base origin/main`.
- [ ] 2.3 Run `python scripts/check_duplicates.py`.
- [ ] 2.4 Build site with `python scripts/build_site.py`.
- [ ] 2.5 Validate RO-Crate via `rocrate-validator`.
