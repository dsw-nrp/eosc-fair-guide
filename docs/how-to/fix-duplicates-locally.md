<!-- type: how-to -->
# Apply safe duplicate links locally

Use this procedure in a checkout when the pull-request command is unavailable or you are editing locally.
Set up the [build and checks](build-and-check.md) first, then keep the repair separate from other content edits.

1. **Review the suggestions.** Run `python scripts/check_duplicates.py` on your branch. Check that every safe link
   really joins entries for the same thing. The tool adds links; it does not merge records or change accepted
   duplicate groups in `content/duplicates.toml`.
2. **Resolve your identity.** A reviewed `[[person]]` in `content/guide.toml` supplies its `id`, `github` and
   `commitNames`. Without an explicit choice, the repair matches `git config user.name` to exactly one reviewed
   `github` or `commitNames` value. Review of a new identity is an ordinary content pull request; see
   [credit and ORCID](../contribution-reference.md#credit-and-orcid-ids). No identity or ORCID is guessed.
3. **Apply the safe links.** Run `python scripts/check_duplicates.py --fix`. If your Git name is unknown or
   ambiguous, it writes nothing and exits nonzero; rerun with `--person <your-person-id>` after confirming the
   reviewed entry. For example: `python scripts/check_duplicates.py --fix --person <your-person-id>`.
4. **Inspect and check the complete repair.** The printed diff includes the links, one provenance action in
   `content/provenance.toml` and its registration in `content/identifiers.toml`. Run `python scripts/check_all.py`;
   commit and push the focused repair on your branch once it passes. A second run after a complete repair is a
   clean no-op and returns nonzero without changing anything; read the diagnostic before treating an exit as failure.

Each file is replaced atomically. A handled application or final recheck failure restores the original bytes of
every changed file and reports any restoration error; a crash across multiple files has no transaction guarantee.
To undo an uncommitted repair deliberately, use `git restore -p -- content/` and select only its hunks. To undo a
committed repair, revert its commit. The [pull-request runbook](../runbooks/fix-a-duplicate.md) covers the bot route.
