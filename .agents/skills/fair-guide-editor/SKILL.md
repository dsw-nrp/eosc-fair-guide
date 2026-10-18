---
name: fair-guide-editor
description: Route edits to the EOSC CZ FAIR Guide through planning, native content rules, validation and release procedures.
---

# FAIR guide editor

1. Read `AGENTS.md`, `.agents/guide/rules/fair-guide-content.md` and
   `.agents/guide/rules/fair-guide-surfaces.md`. Use `docs/agent-tooling.md` to select the installed tool.
2. Classify the request. This skill MUST delegate every behaviour, data/API contract, stored-format, CI or
   governance change to the OpenSpec lifecycle through delivered `aiscr-planning-core` and `openspec-*` surfaces
   **before implementation**. Read relevant `openspec/specs/`, complete proposal/design/specs/tasks and obtain
   explicit approval under that lifecycle. Do not implement first or defer spec maintenance until afterward.
   Resume this native execution route only through approved OpenSpec apply. Ordinary typo/formatting corrections,
   behaviour-neutral dependency updates and routine source refreshes preserve the existing contract and use
   ordinary checks. Never classify a semantic change as wording.
3. Execute the approved scope using the content rule and `docs/content-model.md`; `docs/design.md` owns rationale.
   Content changes require bilingual text, reviewed sources and paradata. Edit authored sources, then regenerate.
4. Build and inspect affected views in both languages, phone width and print. Run `python scripts/check_all.py`
   with the installed prerequisites. Tooling edits also run native generation and both ownership/integrity checks.
5. Follow `CONTRIBUTING.md` for PR review and `docs/deployment.md` for separately authorized release operations.
   Update the rolling usage entry under `.agents/reports/usage/`; report check coverage and unresolved limits.
