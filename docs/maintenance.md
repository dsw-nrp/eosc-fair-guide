# Maintenance

This page covers the recurring maintenance of the repository's settings. `CONTRIBUTING.md` covers contributions,
and [deployment](deployment.md) covers releases.

## Repository settings audit

[`.github/repository.toml`](../.github/repository.toml) is the reviewed expected state of the repository's merge
settings, rulesets (including the merge queue), environments and labels. It also covers Project #1 (fields, options,
views and built-in automations), the organization's issue types and issue fields, the GitHub App's registered
permissions and the token permissions each workflow job requests. Change it through review.

```bash
python scripts/audit_repository.py                    # read only: every section
python scripts/audit_repository.py --section labels   # one section
python scripts/audit_repository.py --json audit.json  # also the findings, with request bodies for the commands
python scripts/audit_repository.py --fix              # also create or update declared labels and add missing Project items
python scripts/audit_repository.py --check-config     # validate the file offline
```

Each finding names the setting, the expected and actual values, the UI path and an equivalent command:

| Status | Meaning | Next step |
| --- | --- | --- |
| drift | The live value differs from the reviewed one | Change the setting in the UI or with the command, or change the file through review |
| missing | A declared object does not exist | Create it; `--fix` creates declared labels and adds Project items |
| undeclared | A live object is not in the file | Declare it, or delete it in the UI; the audit never deletes anything |
| pending | An approved target that a person has not applied yet, still at its recorded current value | Apply it in its task, then audit again |
| done | A pending target now holds | Delete its `[[pending]]` entry |
| unavailable | The token cannot read this part | Run with a token from the table below; it is never counted as matching |

The audit exits with 1 for drift, missing or undeclared objects and for a failed fix. `--fix` never deletes a label,
never changes a Project field value and never changes a setting. `tests/test_workflows.py` compares every job's
`GITHUB_TOKEN` and App-token requests with the `[[token]]` entries offline, and fails on any extra permission.

### What each token can read

Only the maintainer-token column was verified by a read-only run on 24 October 2026 (`gh` with the `repo`, `read:org`
and `read:project` scopes). The other columns follow GitHub's permission reference for each endpoint.

| Section | Endpoint and permission | Maintainer token | `GITHUB_TOKEN` | App installation token |
| --- | --- | --- | --- | --- |
| Merge settings | `GET /repos/{repo}`: Metadata read | Read (verified) | Read | Read |
| Rulesets | `GET /repos/{repo}/rulesets`: Metadata read; bypass actors need write access to the ruleset | Read, with bypass actors (verified) | Rules; bypass actors unavailable | Rules; bypass actors unavailable |
| Environments | `GET /repos/{repo}/environments` and branch policies: Actions read | Read (verified) | Read when the job requests `actions: read` | Unavailable: no Actions permission is registered |
| Labels | `GET /repos/{repo}/labels`: Issues or Pull requests read | Read (verified) | Read with `issues: read` or `pull-requests: read` | Read (Pull requests) |
| Project #1 | GraphQL `organization.projectV2`: Organization Projects read | Read with `read:project` (verified) | Unavailable: no organization access | Read when the job requests it and the installation has accepted `organization_projects: read` (task 5.8) |
| Project completeness | `GET /repos/{repo}/issues`: Issues read | Read (verified) | Read with `issues: read` | Read when the job requests Issues read |
| Issue types | `GET /orgs/{org}/issue-types`: Organization Issue Types read | Read (verified) | Unavailable | Unavailable: not registered |
| Issue fields | `GET /orgs/{org}/issue-fields`: Organization Issue Fields read | Unconfirmed: an empty list, although Project #1 shows Priority and Effort | Unavailable | Unavailable: not registered |
| App registration | `GET /apps/{slug}`: public App, no permission | Read (verified) | Read | Read |

Issue-field values of one issue are read through `GET /repos/{repo}/issues/{number}/issue-field-values`, which needs
Issues read. A scheduled audit therefore combines a `GITHUB_TOKEN` with `actions: read` and `issues: read` for
the repository sections with an App token for Project #1. Issue types and issue fields stay unavailable there,
because the App's registration has no organization issue permissions.
