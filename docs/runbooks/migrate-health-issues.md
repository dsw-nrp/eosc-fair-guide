<!-- type: how-to -->
# Migrate legacy health issues to the digest

A maintainer prepares this one-time migration after the digest workflow reaches the default branch, allowing about
an hour for review. The migration retains every observation and discussion before closing any old issue.

1. **Refresh the original threads.**
   - **Where:** GitHub issues #59–#65 and #85–#101, including their current comments and linked tasks.
   - **Do:** capture each issue's URL, state, complete body and human discussion in a local review package under
     `.cache/health-migration/`; also find any other open `guide-health` issue.
   - **Done when:** the package accounts for every original observation and discussion, with its source link.
   - **If it fails:** leave all issues open; an incomplete read cannot support migration approval.
2. **Prepare the exact mapping and first digest.**
   - **Where:** the authorising OpenSpec task, with local payloads in `.cache/health-migration/`.
   - **Do:** give each issue a disposition: absorbed finding, source update, candidate, retained task, or noise.
     Prepare the complete digest body and each closure comment linking its destination; preserve human discussion
     through source links and a faithful summary. Include expected issue states and any retained task number.
   - **Done when:** every issue has one disposition and the payloads are visible for review; nothing is posted.
   - **If it fails:** resolve conflicting or missing observations before continuing.
3. **Obtain approval.**
   - **Where:** the authorising task, after an independent documentation reader has cleared this runbook.
   - **Do:** show the maintainer the complete mapping, first digest and closure comments, then ask for approval
     of those exact payloads.
   - **Done when:** the maintainer approves them explicitly.
   - **If it fails:** revise the payloads and ask again; do not close an issue on an assumed approval.
4. **Publish, close and reread.**
   - **Where:** the approved digest and original GitHub issues.
   - **Do:** confirm the threads still match the review; publish the digest first, post the approved links and close
     absorbed issues as **Not planned**. Retained tasks keep their number and state. Reread each stored result.
   - **Done when:** every approved observation and discussion is reachable from the digest and all issue states
     match the mapping.
   - **If it fails:** stop at the first mismatch, keep remaining issues open and reconcile the stored partial result
     before resuming.
