<!-- type: how-to -->
# Audit and apply one repository setting

A maintainer checks settings in a few minutes; an administrator applies an approved difference when needed.
The audit compares live values with the reviewed declaration so an unrelated pending change stays untouched.

1. **Read the current differences.**
   - **Where:** a checkout of the default branch, authenticated with `gh auth login` as a repository maintainer. To see
     what the weekly job's App tokens can read, use Actions → **Live health and source watch** → **Run workflow** with
     parts `audit` instead.
   - **Do:** run `python scripts/audit_repository.py --section rulesets --section environments --json .cache/settings-audit.json`.
     Omit the section flags for the full read-only audit. A hosted audit changes no issue; read its run summary or its
     `settings-audit-<run>` artifact.
   - **Done when:** each difference names expected and actual values, its UI path and command.
   - **If it fails:** an unavailable part needs the permission in the [token table](../maintenance.md#what-each-token-can-read);
     exit 1 with findings means differences were found, rather than that the read failed.
2. **Approve one change.**
   - **Where:** the issue or OpenSpec task authorising the settings work.
   - **Do:** record the exact expected-versus-actual diff, its precondition and the
     [rollback](../deployment.md#settings-and-rollback); obtain the maintainer's approval.
   - **Done when:** approval names that one change and its precondition has evidence.
   - **If it fails:** leave the live setting as it is; a pending target is not permission to apply it.
3. **Apply the approved change.**
   - **Where:** the GitHub Settings path printed by the audit, as an administrator.
   - **Do:** set only the approved value. Alternatively use the audit's equivalent `gh api` command with the
     corresponding request body from `.cache/settings-audit.json`.
   - **Done when:** GitHub displays the new value.
   - **If it fails:** preserve the error and use the [rollback runbook](rollback-a-setting.md) if a partial change blocks work.
4. **Confirm and record it.**
   - **Where:** the checkout and the authorising task.
   - **Do:** rerun the same audit; record its result. Remove a completed `[[pending]]` entry from
     `.github/repository.toml` through a pull request once the audit reports `done`.
   - **Done when:** the approved difference is absent and unrelated pending values retain their previous state.
   - **If it fails:** compare the remaining finding before making any further change.
