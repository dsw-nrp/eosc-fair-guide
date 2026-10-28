<!-- type: how-to -->
# Change the Guide's content

This guide changes a text, a source or a resource and gets it reviewed. The rules behind each step are in the
[content model](../content-model.md); the content is authored in `content/*.toml`, never in what the build makes.

New advice, questions and resources using the existing model need no OpenSpec change. If you need a new field or
change what an assessment means, follow [plan a change](plan-a-change.md) before implementation.

1. **Start a branch.** Name it `content/<topic>` (`agents/<agent>/<topic>` for AI-assisted work) and keep it to one purpose; the polishing of one station is a good
   size.
2. **Find the entry.** Search `content/` for its identifier, such as `repository.03`, or for a phrase from the page.
3. **Write both languages.** Czech is primary; the English text says the same, not more. Mark a resource, source or
   glossary term as `[[id|phrase]]` in both languages. Use [advisory wording](../content-model.md#advisory-wording):
   "must" only for a named NRP condition; DOI is recommended, with suitable alternatives accepted.
4. **Cite a published source.** An advice item or question cites at least one clause of `content/ledger.toml` in its
   `sources`. When the fact has no clause yet, add one first, pointing to a published source.
5. **Date a status.** A resource's `status` (operational, pilot, in development, planned or prospective) carries its
   `asOf` date.
6. **Record the paradata.** Add one provenance action for the pull request to `content/provenance.toml`, or extend
   the one it already has: the person responsible, the tools used (an AI model as an instrument, never an author),
   the sources consulted, the items changed and `endTime`, the time work finished. Extending an existing action
   records a later actual end time, not the comparison base's commit time. `agent` names a reviewed `[[person]]`
   and `instruments` existing `[[instrument]]` entries in `content/guide.toml`; on your first contribution, or with
   a new AI model, add them there first ([credit](../contribution-reference.md#credit-and-orcid-ids)). Run
   `python scripts/register_ids.py` to register new identifiers.
7. **Build and check.** Run `python scripts/build_site.py` and `python scripts/check_content.py`, look at the
   changed view in both languages, then run `python scripts/check_all.py`
   (see [build and check](build-and-check.md)).
8. **Open the pull request.** Fill in the template: what changed and why, the sources and the provenance action.
   Content collaborators review correctness and tone; a code owner checks technical integrity
   ([review](../contribution-reference.md#review)).
