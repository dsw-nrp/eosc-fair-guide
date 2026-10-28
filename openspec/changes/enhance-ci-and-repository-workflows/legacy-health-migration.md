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
   - **Where:** Actions → **Live health and source watch** → **Run workflow**, with parts `both`.
   - **Do:** run it, then open the digest it publishes.
   - **Done when:** every listed finding appears in the digest, possibly inside a host entry, or is noise such as
     #101.
   - **If it fails:** follow the digest runbook for the run's summary; close nothing.
3. **Approve the closing comment.**
   - **Where:** the authorising task.
   - **Do:** show the maintainer the one comment every absorbed issue receives, with the digest link, and a summary
     for each issue with human discussion.
   - **Done when:** the maintainer approves that text.
   - **If it fails:** revise it and ask again; close nothing on an assumed approval.
4. **Close and reread.**
   - **Where:** the listed issues.
   - **Do:** post the approved comment on each and close it as **Not planned**. An issue a maintainer keeps as a
     task stays open and is linked from the digest. Reread each issue.
   - **Done when:** every listed issue is closed or kept as recorded, and the digest covers its finding.
   - **If it fails:** stop at the first mismatch and keep the remaining issues open.

## Expected dispositions, read back on 28 October 2026

These are expectations, not a claim that any issue is migrated or closed. Step 1 adds any issue opened later.

| Issues | Expected treatment |
| --- | --- |
| #59–#65 | Champion candidates to review |
| #85–#99, #118–#135 | Link findings; the 17 `heslar.openscience.cz` timeouts (#119–#135) share one host entry |
| #100, #115 | Source updates to review |
| #101 | Noise after the pagination fix |

None of the 43 open issues had a human comment. Issue #137 tracks the possibly stale title of the source behind
issue #95, so closing that issue loses nothing. Actual publication, closure and read-back remain task 6.10.
