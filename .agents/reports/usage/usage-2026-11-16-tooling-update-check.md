# AISCR and OpenSpec tooling compatibility check

- **When:** 2026-11-16
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** GPT-6; exact backend model id not exposed by the runtime.
- **What:** Check the staged AISCR delivery and OpenSpec 2 workflow refresh against Guide-owned integration,
  documentation and ownership rules. Preserve the supplied staging and managed assets. Correct the obsolete
  Gemini/Copilot command descriptions in docs/agent-tooling.md and clarify the existing pinned-CLI route for the
  generic generated Copilot agent.
- **Impacted:** Guide tooling documentation and this usage entry. Delivered libraries, skills, rules and agent
  definitions remain read-only; product behavior, schemas, the completed archive and the active change are unchanged.
- **Close-out:** All 36 native repository checks pass in 251.8 seconds against origin/main, including the browser,
  unit, API, crate, ownership and delivery-integrity checks. OpenSpec 2 strict validation passes all six items;
  native generation reports no differences. The native issue-template adapter retains its consumed API, and all
  seven generated issue templates match. Updated AISCR CLI imports and the release configuration check pass.
  These results are separate from the earlier source-refresh acceptance. No commit, push, issue filing, PR write,
  spec sync or archival is performed by this check.
