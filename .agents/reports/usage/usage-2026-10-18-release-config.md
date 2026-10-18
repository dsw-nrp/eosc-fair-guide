# Release-note configuration — 18 October 2026

- **When:** 2026-10-18
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** exact backend model id not exposed by the runtime
- **What:** Prepared the requested `.github/release.yml` and documented config-only and report-only validation.
- **Impacted:** Release configuration, deployment/tooling guidance and installed/portable delivery contracts.
- **Close-out:** Config-only validation, native generation, ownership/integrity and strict OpenSpec pass.
  Native full close-out passes 29/29 in 184.0 seconds, including 396 unit tests with one existing Windows
  symlink-privilege skip. The sandbox attempt failed on subprocess/temp permissions; its details are retained
  under `.cache/health-release-config-initial/`, with the settled receipt under `.cache/health-release-config-native/`.
  The maintainer approved and the engine applied the upstream correction for PR comment 4306460712.
  All 132 delivered hashes match; native Codex content is preserved. The delivered validator passes
  report-only execution and rejects an invalid title, with no target config required in the report checkout.
  Settled post-delivery close-out passes 29/29 in 216.7 seconds, with 67/67 planned browser/API cases
  executed and none skipped/pending. Final receipts are `.cache/release-config-check-all-final.log` and
  `.cache/health-release-config-final/`. Independent staging activity changed the index; the agent issued
  no staging commands. No commit, push, review posting, publication or archive was performed.
