## 1. Content consolidation and identifier management

- [x] 1.1 Apply station text consolidations and link preservation to `01-plan.toml`, `02-collect.toml`, `04-analyse.toml`, `06-metadata.toml`, `07-licence.toml`, `08-publication.toml`, and `10-citation.toml`.
- [x] 1.2 Update prompt in `metadata.37` to focus on bilingual abstracts, provenance summary, and keyword extraction.
- [x] 1.3 Move superseded identifiers to `[retired]` in `content/identifiers.toml` and verify with `scripts/register_ids.py`.
- [x] 1.4 Add paradata entry to `content/provenance.toml` with current timestamp and AI assistance disclosure.

## 2. Verification

- [x] 2.1 Verify content hygiene and paradata freshness via `python scripts/check_content.py`.
- [x] 2.2 Verify duplicate check via `python scripts/check_duplicates.py`.
- [x] 2.3 Run full test and build suite via `python scripts/check_all.py`.
