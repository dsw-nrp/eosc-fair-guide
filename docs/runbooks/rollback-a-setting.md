<!-- type: how-to -->
# Roll back one repository setting

A repository administrator undoes one applied setting in about ten minutes when it blocks merging, releasing or
publishing. Each setting has a reviewed rollback, so undoing one never disturbs the others.

1. **Find the setting and its rollback.**
   - **Where:** the [settings table](../deployment.md#settings-and-rollback).
   - **Do:** find the row of the setting that causes the problem and read its rollback.
   - **Done when:** you know the one change to make.
   - **If it fails:** a setting outside the table has no reviewed rollback; open an issue before changing it.
2. **See the current state.**
   - **Where:** your checkout, with a token that reads rulesets and environments.
   - **Do:** run `python scripts/audit_repository.py --section rulesets --section environments`.
   - **Done when:** its findings show the setting's expected and actual values.
   - **If it fails:** an "unavailable" finding needs a stronger token; see
     [what each token can read](../maintenance.md#what-each-token-can-read).
3. **Apply the rollback.**
   - **Where:** **Settings** → **Rules** or **Environments**, at the path the finding names.
   - **Do:** make the rollback change, and nothing else.
   - **Done when:** the setting shows its rollback value.
   - **If it fails:** only an administrator can change rules and environments; ask one.
4. **Record the new expected state.**
   - **Where:** `.github/repository.toml`, in a pull request.
   - **Do:** set the reviewed value to the rollback, or add a `[[pending]]` entry naming the task that applies it again.
   - **Done when:** `python scripts/audit_repository.py --section rulesets --section environments` reports no drift
     for the setting.
   - **If it fails:** a finding that remains names the next difference; fix it the same way.
