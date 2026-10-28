<!-- type: reference -->
# Maintenance

Use [handle the digest](runbooks/handle-the-digest.md) for weekly triage and [audit settings](runbooks/audit-settings.md)
for a settings difference. The [maintainer landing page](ci.md) lists all tasks. This reference covers the recurring maintenance of the repository's settings and the triage of its issues in the
[EOSC CZ FAIR Guide Project](https://github.com/orgs/dsw-nrp/projects/1).
`CONTRIBUTING.md` covers contributions, and [deployment](deployment.md) covers releases.

## Triage

Every open issue and pull request belongs in the EOSC CZ FAIR Guide Project. The Project's built-in automations are the only
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
description into that shape and posts it after the maintainer approves it. The [digest runbook](runbooks/handle-the-digest.md) gives the triage order and route to Ready.

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
settings, rulesets (including the merge queue), environments and labels. It also covers the EOSC CZ FAIR Guide Project (fields, options,
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
difference, or recreating a deleted object, therefore cannot activate an unrelated pending queue or environment
policy. Each pending entry retains its own precondition and approval scope.

The audit exits with 1 for drift, missing or undeclared objects, items needing attention and a failed fix. `--fix`
never deletes a label, never changes a Project field value and never changes a setting. `tests/test_workflows.py`
compares every job's `GITHUB_TOKEN` and App-token requests with the `[[token]]` entries offline, and fails on any
extra permission.

**Backfill input.** A separately reviewed mapping can assign Issue Types and area labels. Compare it first;
after approval, the audit applies only the mapping's labels and types and lists open issues it does not cover.
Replace `MAPPING` below with the path to that reviewed TOML file:

```bash
python scripts/audit_repository.py --backfill MAPPING
python scripts/audit_repository.py --backfill MAPPING --fix
```

### What each token can read

The maintainer-token column was verified by a read-only run on 24 October 2026 (`gh` with the `repo`, `read:org`
and `read:project` scopes). Entries marked "run 40190490225" come from the weekly job's first hosted run on
25 October 2026; the other columns follow GitHub's permission reference for each endpoint.

| Section | Endpoint and permission | Maintainer token | `GITHUB_TOKEN` | App installation token |
| --- | --- | --- | --- | --- |
| Merge settings | `GET /repos/{repo}`: the merge options are returned only to tokens that may see them | Read (verified) | Unavailable: returned as null (run 40190490225) | Not requested |
| Rulesets | `GET /repos/{repo}/rulesets`: Metadata read; bypass actors need write access to the ruleset | Read, with bypass actors (verified) | Rules; bypass actors unavailable | Rules; bypass actors unavailable |
| Environments | `GET /repos/{repo}/environments` and branch policies: Actions read | Read (verified) | Read when the job requests `actions: read` | Unavailable: no Actions permission is registered |
| Labels | `GET /repos/{repo}/labels`: Issues or Pull requests read | Read (verified) | Read with `issues: read` or `pull-requests: read` | Read (Pull requests) |
| EOSC CZ FAIR Guide Project | GraphQL `organization.projectV2` fields, views and items: Organization Projects read | Read with `read:project` (verified) | Unavailable: no organization access | Read when the job requests it; requires accepted `organization_projects: read` and an explicit audit-token request |
| Project workflows | GraphQL `organization.projectV2.workflows` | Read with `read:project` (verified) | Unavailable: no organization access | Unavailable: refused for Organization Projects read (run 40190490225) |
| Project completeness | `GET /repos/{repo}/issues`: Issues read | Read (verified) | Read with `issues: read` | Read when the job requests Issues read |
| Issue types | `GET /orgs/{org}/issue-types`: Organization Issue Types read | Read (verified) | Unavailable | Requires accepted Issue Types read and an explicit audit-token request |
| Issue fields | `GET /orgs/{org}/issue-fields`: Organization Issue Fields read | Unconfirmed: an empty list, although the Guide Project shows Priority and Effort | Unavailable | Requires accepted Issue Fields read and an explicit audit-token request; an empty result stays unavailable |
| App registration | `GET /apps/{slug}`: public App, no permission | Read (verified) | Read | Read |

Issue-field values of one issue are read through `GET /repos/{repo}/issues/{number}/issue-field-values`, which needs
Issues read. The weekly audit job therefore combines a `GITHUB_TOKEN` with `actions: read` and `issues: read` for
the repository sections with two audit App tokens: `GH_PROJECT_TOKEN` reads Project GraphQL, and
`GH_ORGANIZATION_TOKEN` reads only the organization issue-type/field definition endpoints over REST. They are
requested separately because GitHub refuses a token request as a whole when the installation has not accepted one
of its permissions. Repository issue-field values and other repository calls keep the repository credential;
writes never use an audit App credential. A token that was not issued, and refused or empty definitions, are
unavailable with their actual cause, without hiding readable Project/settings data or preventing unrelated digest
publication. Registration, installation acceptance, token issuance and successful
endpoint access are separate facts. Use the [audit runbook](runbooks/audit-settings.md) to verify the installed
capabilities; an audit-only run changes no issue or digest.

## Maintenance digest

The **Maintenance digest** is one open bot-authored issue labelled `guide-health` and `area:maintenance`.
The [digest runbook](runbooks/handle-the-digest.md) owns triage, task promotion, limitations and rotation.
The body is rebuilt from current observations. A comment records new, changed, recovered or expired findings;
unchanged runs add no comment. Pinning is best effort, so the label search also finds the digest.

| Section | Meaning |
| --- | --- |
| Needs triage | An untracked persistent finding, with response and provenance |
| Sources not refreshed | A source the latest scheduled refresh did not retrieve, found empty or rejected, with its reason and run, or a note that the refresh outcome is unknown |
| Known limitations | A reviewed explanation, evidence and review deadline, not a healthy result |
| Source updates to review | Changed watched pages or snapshot inputs |
| Candidates to review | Champion candidates; measurement approves no selection |
| Stale statuses | Resource statuses past their freshness threshold |
| Project and settings | Public-safe audit summary; private Project values stay out of the public artifact |

Outcome classes distinguish broken (404/410), denied (401/403/451), rate-limited (429) and unavailable responses.
A refusal proves no deletion or bot protection. A failed service is no result, never a failed FAIR requirement.
Findings from imported records name their upstream source and refresh route. Link coverage rotates by the least
recent attempt under the global and per-host budgets, respecting bounded `Retry-After` waits.

Unreviewed links that fail alike on one host form one triage entry that counts them and lists each link, collapsed.
Its **Track as task** covers that host and outcome; a reviewed limitation still applies to one link. A section
longer than its limit continues in a collapsed list in the body, so every finding stays in the issue; only a body
that would exceed GitHub's size limit counts the rest and points to the run's observations artifact.

Reviewed limitations live in `.github/health-watch.toml`, keyed to a target with an exact outcome, evidence,
reviewer and review deadline. Expired, mismatched and orphaned limitations return to triage. **Track as task**
prefills an issue with its stable finding marker. Tasks created by people with write access are adopted as
sub-issues; a matching tracked outcome suppresses repeated triage, and a changed outcome returns for attention.
A closed task keeps its disposition until the outcome changes.

Closing a digest requests rotation: the next run opens a successor, links both ways and moves the open sub-issues.
Two open bot digests refuse publication and name the conflict. The publisher resumes an interrupted rotation;
each run marker prevents duplicate comments on retry.

## Weekly jobs and stored state

The weekly order is source refresh, Dependabot, then health watch. The configured schedules allow a six-hour
start delay and full timeouts before Monday 06:00 UTC; this is a configured bound, not a GitHub scheduling guarantee.
The first weekly watch in a month also remeasures Champion. A manual **Live health and source watch** run selects
`audit`, `watch` or `both`; an audit-only run never changes an issue or digest.

The watch job reads sources and writes an observation artifact without issue-write permission. A separate publisher
combines it with the public-safe audit and updates the digest. Version-2 state is stored in a 90-day
`health-watch-state` artifact read only from default-branch runs of this workflow in this repository;
the legacy cache supplies a one-time migration fallback. Missing state starts a reported new baseline rather than
inventing continuity.
