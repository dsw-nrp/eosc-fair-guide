<!-- type: landing -->
# Maintainer tasks

Choose the task you need. Each runbook names the place, action, visible result and failure route; the
[CI reference](ci-reference.md) explains workflows, commands, artifacts and measured timings.

| Task | When | Runbook |
| --- | --- | --- |
| Review a change | A local diff or PR is ready for assessment | [Review](runbooks/review.md) |
| Merge a pull request | Checks and review are ready | [Merge](runbooks/merge.md) |
| Release a version | The intended changes have merged | [Release](runbooks/release.md) |
| Repair a broken queue or check | An administrator must unblock delivery | [Emergency merge](runbooks/emergency-merge.md) |
| Undo one setting | An applied setting blocks work | [Roll back a setting](runbooks/rollback-a-setting.md) |
| Refresh a source | A snapshot needs a new observation | [Refresh a source](runbooks/refresh-a-source.md) |
| Apply a safe duplicate link | A pull request has a reviewed suggestion | [Fix a duplicate](runbooks/fix-a-duplicate.md) |
| Triage maintenance | The weekly digest changes | [Handle the digest](runbooks/handle-the-digest.md) |
| Rerun a failed check | A failure needs diagnosis or a retry | [Rerun a check](runbooks/rerun-a-check.md) |
| Inspect or change settings | An audit reports drift | [Audit settings](runbooks/audit-settings.md) |

On an issue or pull request, `/help` lists commands and eligibility. `/fix-duplicates` and `/refresh <source>`
require write access; post a command as the whole comment. The [command reference](ci-reference.md#comment-commands)
defines their guards and outcomes. For local work, use [build and check](how-to/build-and-check.md).

The required status is `checks`, a job of **Guide checks and health report**. `quick` gives early feedback;
only the full result satisfies the gate. [Workflow catalogue](ci-reference.md#workflow-catalogue),
[timing receipt](ci-reference.md#timing-receipt), [deployment](deployment.md) and [maintenance](maintenance.md)
provide the details. [Contributing](../CONTRIBUTING.md) routes authoring work, and
[agent tooling](agent-tooling.md) identifies AI workflows and ownership.
