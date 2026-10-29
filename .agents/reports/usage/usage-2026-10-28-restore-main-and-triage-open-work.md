# Restore main and triage open work

## Claude Code session (explore, plan and apply groups 1–6 in part)

- **When:** 2026-10-28 – 2026-10-29
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** aiscr-investigate
- **MCP servers used:** none
- **Workflow context used:** `openspec-explore` (the maintainer confirmed the capture of the planning artifacts and,
  later, of design D8), `openspec-apply-change`, `aiscr-plan-issue` through its delivered engine; delivered
  `aiscr-planning-core`, `aiscr-quality-first-execution`, `aiscr-usage-logging`, `aiscr-model-logging` and
  `aiscr-review-conduct` rules; the native `fair-guide-content` and `fair-guide-surfaces` rules; pinned
  `npx openspec` CLI; `gh` API and GraphQL queries; Playwright render checks of the built Guide; public pages read
  to verify the Antigravity, Gemini, ORCID, ROR, RO-Crate 1.2 and Open policy finder addresses.
- **What:**
  - Extended the change `restore-main-and-triage-open-work` with the triage of every open issue and the digest's
    exemption from it, and drafted the triage ledger, which the maintainer approved.
  - PR A (#144) regenerated the agent inventory and restored `main`; the maintainer merged it and the bot pull
    requests #138, #139 and #117.
  - On the change branch: the watch repeats a HEAD 400 with GET; the audit leaves the published digest out of
    triage; the Triage view filter and the `guide-health` description were applied live by the maintainer and
    recorded; the RO-Crate resource and the Sherpa source (now Open policy finder, #137) link working pages; seven
    reviewed limitations.
  - At the maintainer's request, explored why the catalogue hides recorded fields and captured the remedy as design
    D8, two `guide-experience` requirements and task group 7 (PR E): complete cards per kind, six shared conventions,
    reverse relations and a completeness test.
  - B1 (#145, merged) rebuilt Karel Berka's draft #39 for #35; its review restored the NRP licence requirement in
    `licence.14` with a reviewer's action, and #39 was closed with a link. B2 (#147) rebuilt draft #41 for #36.
  - Shaped and posted #32 (which absorbed #15, closed as its duplicate) and #5–#9; grounded #10–#14.
  - Addressed the review of PR C (#146).
- **Impacted:** `docs/agent-tooling.md` (#144); `scripts/watch_sources.py`, `scripts/audit_repository.py`, their
  tests and the audit fixture; `.github/repository.toml`, `.github/health-watch.toml`, `docs/maintenance.md`;
  `content/resources.toml`, `content/sources.toml`, `content/provenance.toml`, `content/identifiers.toml`; the
  change's artifacts, including the new `guide-experience` delta, and `triage.toml`; on B1's and B2's branches the
  station files, `content/guide.toml`, `content/provenance.toml`, `content/identifiers.toml` and
  `tests/test_watch.py`; the bodies and provenance comments of the shaped issues; this usage entry.
- **Corrections:**
  - The maintainer put #70 out of scope, confirmed Karel Berka as the drafts' author with his GitHub account and
    address, defined the `Generic` milestone, and reported that the Sherpa API page refuses people as well, which
    turned a planned limitation into a source correction.
  - A `[[pending]]` entry only accepts documented deployment steps, so the two Project settings followed #141's
    route: applied live first, then declared and recorded.
  - `CITATION.cff` credits only software authors, so Karel Berka is credited through the Guide's `contributors`.
  - A watch test fixed the link count at 673; it now derives its expectations from the inventory.
  - The maintainer judged a catalogue fix limited to content changes insufficient and asked for complete cards per
    kind, consistent across kinds.
  - The review of PR C: a 403 does not establish bot protection, so the OpenAI limitation states only the refusal;
    the station rule stays in its existing requirement instead of a second ADDED one; #137's closure reason names
    its actual basis; a test ties the audit's digest identity to the publisher and renderer; and this entry was
    brought up to date.
  - Shaping found fixtures and tests for both whole evaluator mappings, so #14's effort fell from Medium to Low.
- **Merge route:** #144 was merged through the administrator bypass with green `checks`, departing from step 2 of
  `docs/runbooks/merge.md` as design D2 records.
- **Verification:**
  - the HEAD 400 test failed before the fix and passes after it, and the digest-exemption tests failed before the
    audit change; the digest identity test fails when the renderer's marker, the audit's marker or the bot login
    drifts; `tests/test_watch.py` and `tests/test_audit_repository.py` pass;
  - a maintainer's live audit of the Project and labels reports no drift and recognises only #140 as the digest;
  - B1's 16 changed items and B2's four new items render in Czech and English at phone width, and the built data
    holds no retired ID;
  - `python scripts/check_all.py` passes 36/36 for #144, for B1, for B2 and for the change branch; strict OpenSpec
    validation passes 6/6.
- **Close-out:** 21 of 49 tasks done. Open: the review and merge of B2 (#147) and the rebuilds B3–B4, PR C's review
  and merge, the digest actions outside the repository, the shaping of the remaining issues in the ledger, PR E,
  and the integration check after the next watch run.
