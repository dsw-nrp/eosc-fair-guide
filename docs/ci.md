# Continuous integration

This page records how the pull-request checks are measured. `CONTRIBUTING.md` describes how to run them.

## Timing receipt

A speed claim compares reruns of one fixed commit before and after a change, with unchanged coverage, as reported by
`python scripts/ci_timings.py <run-id> --attempt <n>`. Hosted runners vary widely between attempts with identical
inputs, so read the median and the range, never a single run. A rerun removes the earlier attempts' artifacts, so
read each attempt's report before starting the next.

### Baseline

Run 40022072478 of PR #103 at commit `40d0386`, with the CPU lane and two browser lanes. Attempt 1 is the original
run; attempts 2–4 are the three reruns of 24 October 2026. Every attempt succeeded, so its collector accepted
complete check, case and validator coverage.

| Attempt | Elapsed | Critical lane | Queue | Setup (summed) | Summed job time | Peak jobs |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 379 s | browser-b | 14 s | 178 s | 759 s | 3 |
| 2 | 346 s | browser-a | 14 s | 159 s | 852 s | 3 |
| 3 | 347 s | browser-a | 15 s | 174 s | 775 s | 3 |
| 4 | 262 s | browser-b | 14 s | 130 s | 569 s | 3 |

The three reruns give a median of 346 s (range 262–347 s). The CPU lane's check time alone ranged from 114 s to
225 s between attempts. Attempts 1 and 4 keep their lane evidence: 67 of 67 browser cases passed, and every
validator profile passed (`tests/fixtures/ci-timings/40022072478-1` holds attempt 1). The reruns removed the
artifacts of attempts 2 and 3, so only their job and step timings remain.

### Candidate

Run 40085436997 of PR #107 at commit `ae2e813`: the quick job, a CPU lane, a unit-test lane and four browser lanes,
unit shards and dependency caches. Attempt 1 is the original run; attempts 2–4 are the three reruns of 24 October
2026. Every attempt passed 33 checks, 68 of 68 browser cases and all three validator profiles. The changelog check
and the command-workflow case are new since the baseline. The validators' output matches the baseline's apart
from timings.

| Attempt | Elapsed | Critical lane | Queue | Setup (summed) | Summed job time | Peak jobs | Quick result |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 287 s | browser-a | 21 s | 223 s | 929 s | 6 | 19 s |
| 2 | 274 s | browser-a | 29 s | 231 s | 953 s | 6 | 27 s |
| 3 | 273 s | browser-a | 31 s | 241 s | 915 s | 6 | 22 s |
| 4 | 280 s | browser-b | 27 s | 202 s | 880 s | 6 | 23 s |

### Result

- **Elapsed.** The reruns' median fell from 346 s to 274 s, and their range narrowed from 262–347 s to 273–280 s.
  One baseline rerun (262 s) was faster than every candidate attempt, so the gain lies in the typical and slow runs.
- **Quick feedback.** Cheap offline failures are reported after 19–27 s.
- **Cost.** The reruns' median summed job time rose from 775 s to 915 s and queue time from 14 s to about 29 s,
  with six concurrent jobs instead of three. Public-repository minutes are free; the organisation's
  concurrent-job limit is the constraint to watch.
- **Caches.** The branch's first run (40084136770) missed the pip cache, and its CPU lane spent 38 s on setup. Every
  candidate attempt hit both the pip and the npm cache, with identical check inventories.
- **Unit lane.** In run 40084136770 two unit shards beside the three validators made the CPU lane the critical path
  (261 s). With a runner of their own, the unit lane took 95–110 s and the CPU lane 110–179 s, never critical.
- **Collector artifacts.** The health, preview and review artifacts keep their names and file inventories. The
  only differences are group 1's new checks and two logs that unit tests had leaked into the baseline's report.
