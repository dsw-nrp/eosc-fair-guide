<!-- type: how-to -->
# Review the evaluator mappings

The mapping owner, the technical owner in [`CODEOWNERS`](../../.github/CODEOWNERS), reviews the external-evaluator
mappings every six months and whenever a provider changes; a review takes about an hour. The mappings decide which
answers the Guide suggests.

1. **Decide whether a review is due.**
   - **Where:** the date in this step, F-UJI's [releases](https://github.com/pangaea-data-publisher/fuji/releases)
     and FAIR-Checker's [API description](https://fair-checker.france-bioinformatique.fr/swagger.json).
   - **Do:** review by 26 April 2027 at the latest. Review sooner after a new F-UJI metric, software version or
     metric version, or a changed FAIR-Checker metric list, metric wording or API version.
   - **Done when:** you know which provider and which versions to check.
   - **If it fails:** a provider page that does not answer is tried again later; the reviewed versions stay as they
     are.
2. **Compare each provider with its reviewed record.**
   - **Where:** the `[[provider]]` records in `content/live.toml`: `reviewed` and each `[[provider.metric]]`.
   - **Do:** for F-UJI, assess a public dataset at its [form](https://www.f-uji.net/?action=test) and read the
     report's `software_version`, `metric_version` and `metric_specification`. For FAIR-Checker, read `info.version`
     in the API description, then compare its twelve metrics and their wording with the recorded `name` values: the
     API version can stay the same while a metric changes.
   - **Done when:** every difference is listed, or there is none.
   - **If it fails:** without a current report or description, stop here and leave the record unchanged.
3. **Check each mapping against its fixtures.**
   - **Where:** `tests/fixtures/providers/` and `tests/page/check_providers.mjs`.
   - **Do:** confirm for each `[[provider.mapping]]` that `whole` holds only where a native pass establishes
     everything the question asks; a narrower criterion is `partial`. Remove a mapping whose `metric` is unlisted.
     Promote nothing to `whole` here: a new whole mapping needs its own validation. For a new version, add a
     synthetic fixture with the public report's structure and no real subject metadata, test both whole mappings
     against it, then list the version in `reviewed`. Run `npm run check:providers`.
   - **Done when:** the check passes and every reviewed F-UJI version has a fixture that exercises both whole
     mappings.
   - **If it fails:** leave the version out of `reviewed`. Its reports keep their native results and suggest no
     answer.
4. **Record the review.**
   - **Where:** a pull request.
   - **Do:** apply step 2's differences to the metric records (`name`, `label`, a new or retired metric), set the
     provider's `observed` date, move the step 1 date six months on and add the pull request's provenance action. No
     difference still moves both dates.
   - **Done when:** the pull request merges through the [merge runbook](merge.md).
   - **If it fails:** follow [rerun a check](rerun-a-check.md) for a failed check.

A changed mapping changes only what the Guide suggests: stored assessments keep every native result, and an answer
a reader gave stays theirs. Unreviewed versions suggest nothing; same-version changes are caught only here.
FAIR-Checker's reviewed identity is its API version, the only version it publishes;
[the design](../design.md#optional-evaluators) explains how each provider's results are read.
