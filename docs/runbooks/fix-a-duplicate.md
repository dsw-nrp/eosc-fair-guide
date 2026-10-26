<!-- type: how-to -->
# Fix a duplicate in a pull request

A maintainer with write access applies safe link suggestions to a pull request in a few minutes; local editors use
[the local procedure](../how-to/fix-duplicates-locally.md) for identity, `--person`, no-op results and rollback.
The repair records provenance so credit stays exact.

1. **Read the suggestion.**
   - **Where:** the pull request's **Guide review** comment, under **Suggested fixes**.
   - **Do:** check that each suggested link joins two entries for the same thing.
   - **Done when:** you agree with every suggested link.
   - **If it fails:** no **Suggested fixes** section means there is nothing safe to apply; resolve the duplicate by
     hand in the pull request.
2. **Check the prerequisites.**
   - **Where:** `content/guide.toml` on the pull request's branch.
   - **Do:** confirm that a reviewed `[[person]]` has your GitHub login as `github` and that the `duplicate-fix`
     instrument exists.
   - **Done when:** both are present.
   - **If it fails:** add your reviewed identity through an ordinary pull request first; rebase a branch that lacks
     the instrument.
3. **Apply the repair.**
   - **Where:** a comment on the pull request.
   - **Do:** post `/fix-duplicates` as the whole comment.
   - **Done when:** the reply names the repair commit.
   - **If it fails:** the reply names the reason. Check the branch and workflow run before retrying: the repair
     commit may exist even if its success comment failed. Use the [local route](../how-to/fix-duplicates-locally.md)
     when the command is unavailable.
4. **Review the repair.**
   - **Where:** the repair commit and the rerun checks.
   - **Do:** read the diff, including `content/provenance.toml` and `content/identifiers.toml`.
   - **Done when:** `checks` passes on the repair commit.
   - **If it fails:** revert the repair commit and ask a maintainer.
