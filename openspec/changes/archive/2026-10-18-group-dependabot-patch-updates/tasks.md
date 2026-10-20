# Tasks

## 1. Configure patch-only update groups

- [x] 1.1 Add a patch-only version-update group for all dependency names in each of the four ecosystem entries, preserving directories, weekly schedules and PR limits. Verify the parsed YAML contains the intended rules and `python -m unittest discover -s tests -p test_workflows.py` passes.
- [x] 1.2 Run `npm run openspec:validate` and the full `python scripts/check_all.py` suite, inspect the scoped diff and record actual coverage in the change's usage entry. Verify no commit, push or hosted Dependabot run was initiated.

## Workflow follow-up

- After reviewed delivery, inspect the next scheduled Dependabot run for grouped patch PRs per ecosystem.
- Commit, push and archive only under their separate authorizations; preserve the staged release change.
