# Polish NKR integration

- **When:** 2026-11-02 through 2026-11-05 (+01:00)
- **Agent / runtime:** Codex
- **Model / backend:** GPT-6; exact backend model id not exposed by the runtime
- **Subagents used:** none
- **MCP servers used:** GitHub
- **Workflow context used:** `openspec-apply-change polish-nkr-integration`,
  `openspec-verify-change polish-nkr-integration`, `fair-guide-editor`, delivered
  planning, execution, usage and model rules.
- **What:** Implement and verify the approved OpenSpec change `polish-nkr-integration`,
  including the nine review repairs requested for dsw-nrp/eosc-fair-guide#170.
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
- **Verification (review repairs, 2026-11-05):** All nine findings are repaired with
  regression coverage, reconciled OpenSpec artifacts and corrected rollback order.
  The NKR module passes 22 tests. The full native default aggregate passes 36/36
  checks in 189.7 seconds, including 735 unit tests; strict OpenSpec validation
  passes 6/6 items. The five-record fixture adds one repository and passes API
  validation (1,736 files), all 60 required Guide profile checks and the focused
  NKR browser section. Czech/English desktop, 320 px and print screenshots are
  local under `.cache/screenshots-nkr-review/` and
  `.cache/screenshots-nkr-review-fixture/`. A sandboxed unit rerun hit temporary
  directory permissions; the native run passed and its empty scratch was removed.
- **Verification (OpenSpec after review repairs, 2026-11-05):** The explicitly
  requested `openspec-verify-change` pass examined 26/26 tracked tasks, 12 delta
  requirements, 30 scenarios and nine design decisions. Fresh native acceptance
  passed 36/36 checks in 206.2 seconds, including 735 unit tests and strict
  OpenSpec validation 6/6. Isolated probes found two warnings: a changed schema
  may admit an `additionalNames` type the build cannot consume after replacing
  the snapshot, and retirement reporting misses AMCR when reached through its
  raw snapshot address. The report and recommendations are in
  `openspec/changes/polish-nkr-integration/verification.md`; probe evidence is in
  `.cache/nkr-verification-probes.json`. No implementation or task state changed.
- **Verification (authorized warning repairs, 2026-11-05):** The explicit "fix
  both" request authorized tasks 10.1-10.3. Identity values now satisfy the
  Guide's consumed shapes as well as the upstream schema before writing, and
  retirement reporting uses the build's identity lookup for raw/annotated
  addresses and reviewed keys. Three new NKR tests reproduce and cover the
  failures; all 25 NKR tests pass. Both original isolated probes now pass.
  Final native acceptance passes 36/36 checks in 172.9 seconds, including
  738 unit tests; strict OpenSpec validation passes 6/6. The verification report
  records both warnings as resolved. Existing staged content was preserved.
- **Verification (second PR review repairs, 2026-11-05):** The user requested
  repair of the new review at `f898fde`. All five new Low findings are addressed
  by tasks 11.1-11.5: NKR annotation isolation, removal of its unsupported
  incoming re3data path and claims, expanded contact-evidence assertions,
  literal diagnostics at both producers/sinks, and one final availability
  derivation. Four new NKR tests and publisher/browser adversarial cases pass;
  the NKR module has 29 tests. Planted localization and availability regressions
  were detected and removed. Expanded evidence screenshots were inspected in
  both languages at 1366 and 320 px. The first aggregate had one formatting
  failure; after correction, final native acceptance passes 36/36 checks in
  170.5 seconds, including 742 unit tests. Strict OpenSpec passes 6/6. The
  security fix has a changelog note. Evidence and dispositions are in the
  change's verification report and hand-off. The review's two older non-verdict
  observations remain advisory. No subagents were used; GitHub was read only.
- **Close-out:** All 34 tasks are complete and local acceptance is green on
  `agents/codex/polish-nkr-integration`; all five new findings are repaired.
  The user explicitly requested a local commit of the second-review repairs.
  The isolated baseline at
  `774b241890fdfb31be6ec111c0db9e415b998c5c` reproduced the eight NKR profile
  failures and identified one unrelated checkout-name assumption. The user
  explicitly requested a local commit of the review and verification repairs.
  No push, PR creation, archive, source-refresh dispatch or hosted publication
  was performed.
