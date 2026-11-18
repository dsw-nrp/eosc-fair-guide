# Digitalia MUNI ARTS and the November EOSC CZ outputs

- **When:** 2026-11-18
- **Agent / runtime:** Claude Code
- **Model / backend:** claude-opus-5-5
- **What:** Act on the maintenance digest's source updates (`dsw-nrp/eosc-fair-guide` issue 140), as the maintainer
  decided. Add Digitalia MUNI ARTS, which the EOSC CZ catalogue of NDI repositories lists in production, as a curated
  repository, with its operator from its own pages and one provenance action. The NRP deposit-licence manual's
  clauses and advice were prepared on a separate local branch and held back: with them the initial Czech page
  download exceeds its 300 KB budget (471 bytes of headroom on `main`; they add about 690).
- **Impacted:** `content/repositories.toml`, `content/provenance.toml`, `content/identifiers.toml` and this usage
  entry.
- **Close-out:** `python scripts/check_content.py --base origin/main` and `python scripts/check_duplicates.py`
  pass with no new review notes. The initial Czech download keeps 222 bytes of headroom. All 36 repository checks
  pass in 232.0 seconds; this entry was written afterwards and the documentation and agent-surface ownership checks
  were run again.
