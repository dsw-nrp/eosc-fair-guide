# Deduplicate stations design

## Context

The FAIR Data Guide structures recommendations into 11 life cycle stations across four role lenses (Researcher, Data Steward, Repository Manager, Community). Editorial analysis revealed duplicate items resulting from multiple ingestion rounds:
1. RDMkit links and license handbook links were appended at the end of files rather than integrated into early items.
2. AI prompts in station 2 and station 6 drifted into verbatim duplicates.
3. Overlaps between key overview items (`kind = "key"`) and basic level guidance (`level = "L0"`).

## Decisions

- **Incorporate, do not delete valuable links:** External links to RDMkit, the National Licensing Guide, and FAIR Cookbook present in appended items are moved into the relevant primary station advice items (`plan.03`, `plan.04`, `plan.10`, `collect.04`, `collect.05`, `metadata.06`, `licence.03`, `licence.09`, `licence.14`, `publication.03`, `citation.12`, `citation.20`).
- **Retire obsolete IDs:** Superseded items (`plan.28`, `plan.29`, `collect.21`, `metadata.41`, `licence.28`, `licence.29`, `licence.30`, `publication.29`, `citation.13`, `citation.23`) are registered as `[retired]` in `content/identifiers.toml` so link integrity and knowledge base validation hold.
- **Differentiate AI assistance:** In `06-metadata.toml`, `metadata.37` prompt is tailored to drafting bilingual abstracts, summarizing data provenance, and extracting candidate keywords/subject headings.
- **Fresh provenance timestamp:** The provenance action in `content/provenance.toml` is recorded with an `endTime` strictly newer than the PR merge-base on `main` to pass `check_content.py --base`.

## Validation

- Content contract: `python scripts/check_content.py` passes with zero errors and paradata freshness verified.
- Deduplication check: `python scripts/check_duplicates.py` passes with no shared addresses, IDs, or verbatim text.
- Full build and checks: `python scripts/check_all.py` passes without regressions.
