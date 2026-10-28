<!-- type: how-to -->
# Recover a removed historical release tag

A maintainer uses this exceptional recovery only for an unchanged historical release whose failed-deployment tag
was removed before an artifact was published. Allow about an hour, including approval and deployment.

1. **Confirm the original identity.**
   - **Where:** the original release pull request, failed deployment run and release issue.
   - **Do:** recover the exact original merge commit, tag and `Fair-Guide-Release-Status` annotation; confirm the tag
     is absent locally and remotely and no release artifact was ever published for it.
   - **Done when:** the task links evidence for every condition and every metadata file still describes that version.
   - **If it fails:** use the [normal release runbook](release.md) with a new version; corrected metadata cannot repair
     bytes frozen at an existing tag.
2. **Approve the recovery.**
   - **Where:** the release issue or OpenSpec task.
   - **Do:** obtain explicit maintainer approval for that exact tag, commit and status. A `production` status also
     needs the responsible maintainer's recorded approval for public use.
   - **Done when:** approval names all three values.
   - **If it fails:** create no tag.
3. **Recreate the annotated tag once.**
   - **Where:** a checkout with the original commit and permission to push release tags.
   - **Do:** use `git tag -a <tag> <original-commit> -m "Fair-Guide-Release-Status: testing"`, substituting the approved
     tag and commit and keeping the original status marker (`production` only if that was approved). Then use
     `git push origin refs/tags/<tag>`.
   - **Done when:** the remote tag resolves to the approved commit and its deployment run starts.
   - **If it fails:** inspect the tag and rejection before retrying. Never force, move an existing tag or bypass a
     protection rule; use a new normal release if the historical target is inadmissible.
4. **Complete the release.**
   - **Where:** the tag's **Deploy the verified site** run.
   - **Do:** resume the [release runbook at production approval](release.md#release-the-guide), then apply notes
     and publish after verifying the deployed identity.
   - **Done when:** the live site, verified artifact and published release name the approved tag and commit.
   - **If it fails:** rerun that tag deployment's failed jobs; do not recreate or move the tag.
