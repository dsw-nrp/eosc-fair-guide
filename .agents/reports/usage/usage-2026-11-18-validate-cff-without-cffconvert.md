# Validate CFF without cffconvert

- **When:** 2026-11-18
- **Agent / runtime:** Claude Code
- **Model / backend:** claude-opus-5-5
- **What:** Plan the OpenSpec change `validate-cff-without-cffconvert`: validate `CITATION.cff` against a vendored
  CFF 1.2.0 schema with `jsonschema`, so `cffconvert` 2.0.0 no longer pins `jsonschema` below 4 and
  `dsw-nrp/eosc-fair-guide` PR 70 can be superseded. Planning artifacts only; implementation awaits approval.
- **Impacted:** `openspec/changes/validate-cff-without-cffconvert/` (proposal, design, tasks, `skip_specs`) and
  this usage entry.
- **Close-out:** `npm run openspec:validate` passes 7 of 7 items, with this change accepted under `skip_specs`;
  the agent-surface ownership check reports no findings. A read-only probe found no schema errors for the current
  `CITATION.cff` and rejected a non-ISO `date-released`.
