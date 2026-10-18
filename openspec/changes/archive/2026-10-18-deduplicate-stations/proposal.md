# Deduplicate stations and consolidate advice items

## Why

In several Guide stations (`content/stations/*.toml`), layering sources over time led to repetition of the same advice within the same station:
- Appended items at the end of stations (RDMkit and the licensing guide) repeat the main advice items without adding new operational requirements.
- Nearly identical AI prompts in Station 2 (`collect.20`) and Station 6 (`metadata.37`) both request tabular data dictionary creation, while `metadata.37` promises metadata abstract proposals and keywords.
- Introductory `kind = "key"` items and subsequent `level = "L0"` items repeat identical sentences in stations 2, 4, and 10.

Consolidating these duplicates improves reading flow, eliminates redundant advice, and properly retires obsolete identifiers without breaking stability contracts.

## What Changes

- Consolidate trailing duplicate advice items into primary station items across stations 1, 2, 6, 7, 8, and 10, retaining all external resource links (RDMkit, FAIR Cookbook, licensing guide).
- Formally retire superseded item identifiers in `content/identifiers.toml` under `[retired]`.
- Specialize `metadata.37` prompt for bilingual abstract, origin summary, and keyword extraction, differentiating it from `collect.20`.
- Differentiate introductory key insights from `L0` overview summaries in stations 2, 4, and 10, and streamline `analyse.11`.
- Record a valid provenance action with an up-to-date timestamp covering all modified and retired items.

## Capabilities

### Modified Capabilities

- `fair-guide/guide-knowledge-base`: station content is streamlined, duplicates removed, and retired item identifiers registered.

## Impact

Station guidance becomes more concise and non-repetitive for all four reader roles. Existing identifier lookups for retired items are handled cleanly via the `[retired]` registry. No external API changes, schema changes, or UI layout breakage.
