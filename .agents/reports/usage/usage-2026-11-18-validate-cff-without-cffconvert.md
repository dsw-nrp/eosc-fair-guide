# Validate CFF without cffconvert

- **When:** 2026-11-18
- **Agent / runtime:** Claude Code
- **Model / backend:** claude-opus-5-5
- **What:** Plan and implement the OpenSpec change `validate-cff-without-cffconvert`. `CITATION.cff` is validated
  with `jsonschema` against the CFF 1.2.0 schema, vendored unchanged from tag `1.2.0` of
  `citation-file-format/citation-file-format` (byte-identical to the copy `cffconvert` 2.0.0 bundled); YAML dates
  stay text, and another `cff-version` is refused. `cffconvert` leaves the requirements and `jsonschema` moves to
  4.26.0, superseding `dsw-nrp/eosc-fair-guide` PR 70 after merge.
- **Impacted:** `openspec/changes/validate-cff-without-cffconvert/`, `scripts/check_citation_metadata.py`,
  `scripts/schemas/cff-1.2.0.json` (new), `REUSE.toml`, `requirements-dev.txt`, `tests/test_citation_metadata.py`,
  `docs/how-to/build-and-check.md` and this usage entry.
- **Close-out:** Eight of nine tasks are done; 4.2 is the maintainer's review and the closing of PR 70 after merge.
  In a fresh environment from `requirements-dev.txt` (`jsonschema` 4.26.0, no `cffconvert`, `pip check` clean), the
  citation check and its 12 tests pass, and the invalid-value tests fail against an accept-everything schema.
  `npm run openspec:validate` passes 7 of 7, `reuse lint` passes, and all 36 repository checks pass in 250.3
  seconds under that environment; this entry was written afterwards and the documentation and agent-surface
  ownership checks were run again. The local `.venv` was left unchanged.

## Update 2026-11-20 — review follow-up on PR 189

- **When:** 2026-11-20
- **Agent / runtime:** Kilo
- **Model / backend:** e-infra-cz/deepseek-v4.1-flash-thinking
- **What:** Fixes observation O1 of the PR 189 review. A duplicate key inside one inline YAML merge source was
  flattened into the merging mapping unread, so its last value was kept silently. `TextDates` now scans every
  mapping node spliced in as a merge value before `SafeConstructor` flattens it; precedence across merge sources,
  and an explicit key overriding a merged one, stay as YAML defines them and are not refused.
- **Impacted:** `scripts/check_citation_metadata.py`, `tests/test_citation_metadata.py` and this entry.
- **Close-out:** `python -m unittest discover -s tests -p test_citation_metadata.py` passes 17 tests; the new
  inline-merge test is refused by the loader while the previous construct_mapping accepted it (`{'x': 2}` kept).
  `python -m unittest discover -s tests` passes 955 tests in 504 s, one skipped; its stdout also carries the
  `FAILED duplicates:`/`FAILED content:` lines of tests that assert a failing check.
