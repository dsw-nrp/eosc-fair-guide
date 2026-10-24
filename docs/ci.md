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
