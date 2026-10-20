# Local scratch — visible run hand-offs

Directory for **transient hand-offs**: artefacts a human must read, approve, or apply while a run is active — approval views and the exact bodies that will be posted, branch-audit reports, and operator-patch READMEs. Machine inputs, intermediates, payloads, and regenerable output belong under `.venv/.cache/`; committed retained output belongs under `.agents/reports/`. The classification is owned by the `workflow/artefact-placement` capability.

## Rules

- Directory contents are deliberately **not gitignored**: new and changed hand-offs remain visible in `git status` and diffs so reviewers can track them. Git visibility does not make a hand-off a durable report or authorize committing it.
- Layout is `<workflow>/<run>/`, keyed so a hand-off and its bulk run directory can be matched. Each hand-off carries the operator-facing payload and a pointer to the bulk location holding the machine artefacts; machine artefacts are not copied here.
- A hand-off is **read-only in practice**. Where an approval digest binds it, editing the file invalidates that digest: re-render the hand-off and approve it again rather than consuming it under the previous digest.
- **Retention follows consumption.** Remove a hand-off when its run reaches a terminal outcome; retain it while diagnosis or retry remains necessary. A hand-off with no posting or approval step — a branch-audit report, an operator-patch README — persists until local cleanup.
- Use UTF-8 for JSON and text outputs.
- When conclusions are final, move durable reports under `.agents/reports/` (or the appropriate subfolder) and delete the local hand-off.
