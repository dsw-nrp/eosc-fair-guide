# Group Dependabot patch updates

- **When:** 2026-10-18
- **Agent / runtime:** OpenAI Codex
- **Model / backend:** exact backend model id not exposed by the runtime
- **What:** Apply the maintainer's requested patch-only grouping policy through `group-dependabot-patch-updates`; explain the missing `-r` in the reported pip invocation.
- **Impacted:** `.github/dependabot.yml` and this change's OpenSpec artifacts. Preserve the maintainer's weekly schedules, directory paths, limit of 30 and staged release work.
- **Close-out:** Both tasks are complete. Parsed YAML confirms patch-only groups for all dependency names in all four ecosystems, with directories, weekly schedules and limits preserved. The 16 workflow tests and strict OpenSpec (7/7) pass; full native close-out passes 30/30 in 172.8 seconds, including 412 Python tests (one existing skip). Receipts are in `.cache/health-dependabot-patch-groups/`. A no-network pip dry-run with `-r requirements-dev.txt` succeeds with the pinned dependencies already installed; its three temporary directories were cleaned after checking their exact repository-local paths. Implementation close-out performed no commit, push, hosted update run or archive. Actual grouped PR creation remains a post-delivery observation.
- **Archive:** Under the maintainer's explicit bulk-archive instruction, used `openspec-bulk-archive-change` and inline `openspec-sync-specs` to sync the patch-grouping requirement and all three scenarios after the release delta, verify the main spec and archive the complete change at `openspec/changes/archive/2026-10-18-group-dependabot-patch-updates/`. No active changes remain. Hosted grouping is still a post-delivery observation; no commit, push or hosted update run was performed.
