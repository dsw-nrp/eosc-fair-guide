<!-- type: how-to -->
# Migrate legacy health issues to the digest

A maintainer migrates the per-finding health issues once, right after the digest workflow reaches the default
branch, in about half an hour. Every open legacy issue is covered by the digest before it is closed.

1. **List the issues to migrate.**
   - **Where:** GitHub issues with the `guide-health` label.
   - **Do:** list every open issue that carries the legacy `fair-guide-health key=` marker, whatever its number,
     and note any comment by a person.
   - **Done when:** the list is complete and each issue with human discussion is marked.
   - **If it fails:** leave all issues open; an incomplete list cannot support closure.
2. **Publish the first digest.**
   - **Where:** Actions → **Live health and source watch** → **Run workflow**, with parts `both` and **Also
     remeasure FAIR Champion tests** ticked.
   - **Do:** run it, then open the digest it publishes. Champion candidates appear only in a run that remeasures
     Champion. A link appears only after it fails again on top of its migrated streak, and a run tries at most 600
     links, so run the workflow again without Champion when a listed link finding is missing.
   - **Done when:** each listed finding appears in the digest, possibly inside a host entry, no longer holds (the
     link answers, or the candidate is no longer available), or is noise such as #101; source updates follow step 3.
   - **If it fails:** follow the digest runbook for the run's summary; close nothing.
3. **Approve the closing comment.**
   - **Where:** the authorising task.
   - **Do:** show the maintainer the one comment every absorbed issue receives, with the digest link, and a summary
     for each issue with human discussion. If the digest does not list #100 or #115 because the migrated page
     baseline already holds their items, put the maintainer's review of each in its closing comment, saying whether
     the Guide's advice or sources should follow.
   - **Done when:** the maintainer approves that text.
   - **If it fails:** revise it and ask again; close nothing on an assumed approval.
4. **Close and reread.**
   - **Where:** the listed issues.
   - **Do:** post the approved comment on each and close it as **Not planned**. To keep a finding as work, create
     its task with **Track as task** in the digest; a legacy issue cannot be adopted. Reread each issue.
   - **Done when:** every listed issue is closed or kept as recorded, and the digest covers its finding.
   - **If it fails:** stop at the first mismatch and keep the remaining issues open.

## Expected dispositions, read back on 28 October 2026

These are expectations, not a claim that any issue is migrated or closed. Step 1 adds any issue opened later.

| Issues | Expected treatment |
| --- | --- |
| #59–#65 | Champion candidates to review (step 2's Champion run) |
| #85–#99, #118–#135 | Link findings; the 17 `heslar.openscience.cz` timeouts (#119–#135) share one host entry |
| #100, #115 | Source updates; reviewed at closure if the digest does not list them |
| #101 | Noise after the pagination fix |

None of the 43 open issues had a human comment. Issue #137 tracks the possibly stale title of the source behind
issue #95, so closing that issue loses nothing. Actual publication, closure and read-back remain task 6.10.
