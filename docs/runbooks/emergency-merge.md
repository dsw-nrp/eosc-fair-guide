<!-- type: how-to -->
# Merge in an emergency

A repository administrator merges directly, bypassing the queue, only when the queue or the required check itself
is broken; it takes minutes. The deployment then runs the full checks, because the commit has no queue result.

1. **Confirm the emergency.**
   - **Where:** the pull request and its failing queue or `checks` run.
   - **Do:** confirm that the failure is in the checking machinery, not in the change.
   - **Done when:** you can name the broken workflow, rule or service.
   - **If it fails:** the change itself fails, so use the [merge runbook](merge.md) instead.
2. **Say why.**
   - **Where:** a comment on the pull request.
   - **Do:** name the broken mechanism and why the merge cannot wait.
   - **Done when:** the comment is posted.
   - **If it fails:** nothing else depends on it; post it before merging.
3. **Merge with the bypass.**
   - **Where:** the pull request's merge box.
   - **Do:** choose **Merge without waiting for requirements to be met**.
   - **Done when:** the pull request shows as merged.
   - **If it fails:** only an administrator can bypass; ask one.
4. **Follow the full checks.**
   - **Where:** Actions → **Deploy the verified site** for the merge commit.
   - **Do:** confirm that its summary says full checks ran and that they passed.
   - **Done when:** **Publish the verified site** records `staging` for the merge commit.
   - **If it fails:** revert the merge through a new pull request, or fix forward through the queue.
5. **Repair the mechanism.**
   - **Where:** a new issue.
   - **Do:** describe the broken mechanism, link the pull request and add the `area:delivery` label.
   - **Done when:** the issue is open with the `area:delivery` label.
   - **If it fails:** when the label does not exist, the `labels` section of the [settings audit](audit-settings.md)
     reports it missing; restore it through that runbook, then add it.
