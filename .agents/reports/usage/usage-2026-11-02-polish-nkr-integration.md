# Polish NKR integration

- **When:** 2026-11-02 (+01:00)
- **Agent / runtime:** Codex
- **Model / backend:** GPT-6; exact backend model id not exposed by the runtime
- **Subagents used:** none
- **MCP servers used:** GitHub
- **Workflow context used:** `openspec-apply-change polish-nkr-integration`,
  `openspec-verify-change polish-nkr-integration`, `fair-guide-editor`, delivered
  planning, execution, usage and model rules.
- **What:** Implement and verify the approved OpenSpec change `polish-nkr-integration`.
- **Impacted:** NKR fixtures, snapshot refresh, catalogue identity and rendering,
  duplicate checks, API/profile contracts, content provenance and maintainer documentation.
- **Verification:** `npm run openspec:validate` passed all six items. The first
  default aggregate (`.venv/Scripts/python.exe scripts/check_all.py`) passed 36/36
  checks in 195.6 seconds, including 723 unit tests. Fixture API/profile/page
  checks and the planted duplicate negative control passed as documented in
  `openspec/changes/polish-nkr-integration/handoff.md`. Visual artifacts are under
  `.cache/screenshots-nkr/`. The final default aggregate after the contact wording
  fix passed 36/36 checks in 165.2 seconds, including 723 unit tests; its JSON,
  HTML, execution details and logs are in `.cache/health/`.
- **Verification (OpenSpec, 2026-11-02):** Reviewed all 21 tracked tasks, ten delta
  requirements, 25 scenarios and nine design decisions. Fresh strict OpenSpec
  validation passed 6/6 items and the default aggregate passed 36/36 checks in
  194.6 seconds, including 723 unit tests. A refreshed five-record fixture with
  the reviewed handle deliberately omitted passed API validation and all 60
  required Guide profile checks; its address-free entry and private contact
  pre-fill passed browser probes in both languages at 1366 and 320 px. The
  additional browser probe initially needed process permission, then passed
  after escalation and correcting PowerShell's encoding of Czech assertions.
  Verification identified one Medium warning: NKR address matching omitted FIP Dashboard-only
  repositories because those entries are appended after the merge pass.
  An NKR record using CESNET Invenio's existing address produced two catalogue
  entries while the duplicate check reported no errors. A record combining
  CzBIRD's reviewed handle with the FIP-only NUSL address was accepted by the
  build although the duplicate check rejected its ambiguous keys. No
  implementation fixes were made during the verification pass itself.
- **Verification (authorized repair):** Task 3.1 was reopened and completed after
  the user requested the fix. Three new regressions failed before the repair,
  then passed after indexing FIP-only entries before the NKR merge. A fourth
  test preserves publication-deposit meaning. All 14 NKR tests and focused Ruff
  checks pass. A populated NKR/FIP build passes API validation and all 60 required
  Guide profile checks. Browser probes and viewport screenshots cover Czech and
  English at 1366 and 320 px, preserving the native route, both source links,
  verification evidence and deposit filtering. Artifacts are in
  `.cache/screenshots-nkr-fip/`. Strict OpenSpec validation passes all six items.
  The final default aggregate after the repair passed 36/36 checks in 186.8
  seconds, including 727 unit tests; its reports and logs are in `.cache/health/`.
- **Close-out:** All 21 tasks are complete and the NKR/FIP join warning is repaired;
  final local acceptance is green on `agents/codex/polish-nkr-integration`.
  The isolated baseline at
  `774b241890fdfb31be6ec111c0db9e415b998c5c` reproduced the eight NKR profile
  failures and identified one unrelated checkout-name assumption. No commit,
  push, PR creation, archive, source-refresh dispatch or hosted publication was performed.
