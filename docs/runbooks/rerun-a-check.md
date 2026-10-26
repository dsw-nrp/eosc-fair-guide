<!-- type: how-to -->
# Rerun a failed check

The author of a pull request, or a maintainer, handles a failed check in minutes. Reproducing it locally tells a
real failure from a passing hiccup, so the fix goes where the problem is.

1. **Find the failure.**
   - **Where:** the pull request's checks → the `partitioned / collect` job's summary.
   - **Do:** read the failed check and the local command its **Next** line gives.
   - **Done when:** you know which check failed and its command.
   - **If it fails:** a summary that says setup did not reach the check runner points to the failed job step.
2. **Reproduce it locally.**
   - **Where:** your checkout, set up as in [build and check](../how-to/build-and-check.md).
   - **Do:** run the command, for example `python scripts/check_all.py --only content page`.
   - **Done when:** it fails the same way, or passes.
   - **If it fails:** a check that needs the network runs only with `--live`.
3. **Fix or rerun.**
   - **Where:** your branch, or the run page.
   - **Do:** push a fix for a failure you reproduced; choose **Re-run failed jobs** when it passed locally.
   - **Done when:** `checks` passes.
   - **If it fails:** when a rerun fails again without a change, ask a maintainer, who reads the lane evidence with
     `python scripts/ci_timings.py <run-id>`.
