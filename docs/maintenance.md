# Maintenance

This page covers the recurring maintenance of the repository's settings and the triage of its issues in Project #1.
`CONTRIBUTING.md` covers contributions, and [deployment](deployment.md) covers releases.

## Triage

Every open issue and pull request is an item of Project #1. The Project's built-in automations are the only
automatic writers of its fields; people set everything else.

| Status | Meaning | Set by |
| --- | --- | --- |
| Needs triage | New, not yet triaged | The "Item added to project" automation, for issues and pull requests alike |
| Ready | Triaged: meets the definition of Ready below | A person |
| In progress | Someone is working on it | The "Pull request linked to issue" automation |
| Review | The linked pull request is ready for review | A person |
| Done | Closed or merged; archived after 14 days | The "Item closed" and "Pull request merged" automations |

**Definition of Ready.** An issue is Ready when it has an Issue Type (Bug, Feature or Task), at least one `area:*`
label, Priority (Urgent, High, Medium or Low) and Effort (High, Medium or Low), and a body in the planned-issue
shape. Priority and Effort are organization issue fields that exist only on typed issues, so the type comes first.
The planned-issue shape is what the delivered `/aiscr-plan-issue` workflow writes: it reworks a reporter's
description into that shape and posts it after the maintainer approves it. Triage an issue in this order: type, area
label, Priority and Effort, then shape it with `/aiscr-plan-issue`, then set Ready.

**Views.**

| View | Shows |
| --- | --- |
| Triage | Issues in Needs triage, oldest first |
| Board | Everything, grouped by Priority |
| My work | Your assigned items that are not Done |
| PR - authored | Pull requests people opened, whatever their Status |
| PR - automated | Dependabot and source-refresh pull requests, whatever their Status |
| Maintenance | Items labelled `area:maintenance`: the health digest and the tasks it spawns |
| Release | Everything, grouped by milestone |

**Area labels.** An area is a label because Project views can filter by labels but cannot group by them. The
trusted review publisher adds the area labels a pull request's changed files call for, by the path rules in
`.github/repository.toml`, after its checks have run. It never removes a label, and a label someone removed is not
added again. The source refresh adds `source-refresh` to its pull requests.

| Label | Covers |
| --- | --- |
| `area:content` | Advice, questions, glossary and model texts |
| `area:sources` | Snapshots, refresh, registry data and ledger sources |
| `area:interface` | Interface, accessibility, language and print |
| `area:evaluation` | Live checks, evaluators and the self-check |
| `area:delivery` | CI, release, deployment, tooling and dependencies |
| `area:maintenance` | The health digest and the tasks it spawns |
| `source-refresh` | Pull requests opened by the source refresh |

**Issue templates.** New issues start from the Czech or English Bug, Feature or Task template in
`.github/ISSUE_TEMPLATE/`, which sets the Issue Type. The templates carry the planned-issue metadata table and
sections, so shaping keeps what the reporter wrote. They are generated from the delivered `aiscr-plan-issue` shape:
after a delivery update changes it, the offline checks fail until you run `python scripts/generate_issue_templates.py`.
Blank issues stay possible, and Discussions take questions that are not yet a task.

**The weekly audit.** The "Live health and source watch" workflow runs the settings and Project audit every week in
a job of its own. Besides the settings below, the audit reports each item that needs a person, with its link:

- an open issue or pull request that is not in the Project;
- an open issue without an Issue Type, or whose body's `Type` row differs from it;
- a Ready issue short of the definition of Ready, with what it lacks;
- an issue in Needs triage for more than 14 days;
- an Urgent issue in Needs triage or Ready for more than three days;
- a closed item that is not Done, or an open one that is.

The job publishes only the "Project and settings" section of the public maintenance digest, in its step summary and
as the `settings-audit-<run>-<attempt>` artifact. It links issues and names Urgent work, but shows no other Project
field value: Ready, triage and Status findings appear there only as counts, and the Project's views show which items
they are. The repository's logs and artifacts are public and the Project is not, so the full report never leaves
the job; run `python scripts/audit_repository.py` with your own token for every finding.

## Repository settings audit

[`.github/repository.toml`](../.github/repository.toml) is the reviewed expected state of the repository's merge
settings, rulesets (including the merge queue), environments and labels. It also covers Project #1 (fields, options,
views and built-in automations), the organization's issue types and issue fields, the GitHub App's registered
permissions and the token permissions each workflow job requests. Change it through review.

```bash
python scripts/audit_repository.py                    # read only: every section
python scripts/audit_repository.py --section labels   # one section
python scripts/audit_repository.py --json audit.json  # also the findings, with request bodies for the commands
python scripts/audit_repository.py --digest digest.md # also the digest's "Project and settings" section
python scripts/audit_repository.py --fix              # also create or update declared labels and add missing Project items
python scripts/audit_repository.py --check-config     # validate the file offline
```

Each finding names the setting, the expected and actual values, the UI path and an equivalent command:

| Status | Meaning | Next step |
| --- | --- | --- |
| drift | The live value differs from the reviewed one | Change the setting in the UI or with the command, or change the file through review |
| missing | A declared object does not exist | Create it; `--fix` creates declared labels and adds Project items |
| undeclared | A live object is not in the file | Declare it, or delete it in the UI; the audit never deletes anything |
| attention | A Project item needs a person (see [Triage](#triage)) | Fix the item at its link, as the note says |
| pending | An approved target that a person has not applied yet, still at its recorded current value | Apply it in its task once the precondition the entry names holds, then audit again |
| done | A pending target now holds | Delete its `[[pending]]` entry |
| unavailable | The token cannot read this part | Run with a token from the table below; it is never counted as matching |

A live ruleset parameter that the file does not declare is drift too, so an applied body never silently drops it.
A body never applies a pending target that the finding does not address. Every other pending setting keeps its
live value, or its recorded current value when the ruleset, rule or environment does not exist yet. Fixing one
difference, or recreating a deleted object, therefore cannot switch the merge queue on before `checks.yml` reports
for merge groups, or remove the `github-pages` reviewer before the production job exists.

The audit exits with 1 for drift, missing or undeclared objects, items needing attention and a failed fix. `--fix`
never deletes a label, never changes a Project field value and never changes a setting. `tests/test_workflows.py`
compares every job's `GITHUB_TOKEN` and App-token requests with the `[[token]]` entries offline, and fails on any
extra permission.

**Backfill.** Once, a reviewed mapping gives every open issue its Issue Type and area label. Compare it first, then
apply it; the audit adds only the mapping's labels and types, and lists open issues the mapping does not cover:

```bash
python scripts/audit_repository.py --backfill openspec/changes/enhance-ci-and-repository-workflows/backfill.toml
python scripts/audit_repository.py --backfill openspec/changes/enhance-ci-and-repository-workflows/backfill.toml --fix
```

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
Issues read. The weekly audit job therefore combines a `GITHUB_TOKEN` with `actions: read` and `issues: read` for
the repository sections with an App token that may only read Projects, set as `GH_PROJECT_TOKEN` and used for
Project #1 alone. Issue types and issue fields stay unavailable there, because the App's registration has no
organization issue permissions. If that token cannot see the issues behind the Project's items, the audit reports
the items as unavailable instead of judging them; if the App cannot issue it, Project #1 is unavailable with the
step for the organization owner.
