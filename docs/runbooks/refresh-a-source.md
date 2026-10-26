<!-- type: how-to -->
# Refresh a source snapshot

A maintainer refreshes a source when its data changed and the weekly refresh should not wait; starting it takes a
minute and reviewing its pull request a few more. Every refresh is validated and proposed as a pull request, so
nothing reaches the Guide unreviewed.

1. **Start the refresh.**
   - **Where:** Actions → **Source refresh** → **Run workflow**, or a comment `/refresh <source>` on a pull request.
   - **Do:** choose the source (`heslar`, `re3data`, `fip-dashboard`, `nkr`, `knav-tools`, `fairsharing`,
     `datacite`) or `all`.
   - **Done when:** the run summary, or the reply to your comment, lists each source's result.
   - **If it fails:** a rejected or failed source keeps its snapshot; the run's refresh report artifact gives the
     reason.
2. **Review the refresh pull request.**
   - **Where:** the pull request "Refresh the `<source>` snapshot", labelled `source-refresh`.
   - **Do:** read the snapshot change as content and confirm that `checks` passed.
   - **Done when:** you approve it, or close it as wrong.
   - **If it fails:** a closed proposal is not offered again with identical content; the next real change is.
3. **Merge it.**
   - **Where:** the pull request's merge box.
   - **Do:** choose **Merge when ready**, as in the [merge runbook](merge.md).
   - **Done when:** the pull request shows as merged.
   - **If it fails:** a branch with someone else's commits is left for reconciliation by hand; close it so the
     next refresh starts from `main`.
