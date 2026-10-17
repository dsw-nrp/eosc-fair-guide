# FAIR Champion selection and health measurement

The guide invokes a reviewed subset of public FAIR Champion tests after an explicit user action. A returned
verdict measures the published test's criterion. The question may require additional evidence, described in
its help. `championEvidenceOnly` keeps such observations without choosing an answer.

## Evidence collected on 11 October 2026

The [Champion registry](https://tools.ostrails.eu/champion/tests/) returned 210 records. All 48 invocation
endpoints on the enrolled `tests.ostrails.eu` origin were inspected, including their published OpenAPI
descriptions, and called once against each of the three public records in [reference-records.json](reference-records.json).
The other 162 records use origins that the guide has not enrolled; they were not invoked. The script contains
no repository-specific connector or exception.

[measurement.json](measurement.json) retains the 144 outcomes, dates, exact invocation addresses, original
test identities, declared metric and principle IRIs, HTTP errors, timings and response sizes. It is an
observation of these records on this date, not a general reliability rate: 10 tests returned a valid verdict
for all three, 37 for some records, and one returned no evaluative verdict. An `indeterminate` response
counts as a returned verdict but provides no positive or negative criterion evidence.

The [Czech pilot deposit](https://doi.org/10.5281/zenodo.21726258) also carries per-test results. A bounded
prefix of `results.json` (bytes 0–262143; HTTP 206) contained 81 complete rows with test identity, input,
timing, status, completion, verdict, description and log. This established the available evidence structure;
it was not a sample from which to infer aggregate reliability. Its July 2026 service versions differ from
the versions measured here. No pilot-wide statistic is claimed.

## Selection and question scope

| Test | Decision | Question and limits |
| --- | --- | --- |
| `fc_unique_identifier` | Add; three definitive verdicts | `dataset.01`, `maturity.01`: recognises identifier patterns; does not independently prove global uniqueness or repository-wide PID assignment. Evidence only. |
| `test_FM_F1_M_IdentPersistent` | Add; DOI passes, both Handles indeterminate | Same questions: likely persistence from scheme recognition, without predicting future access. Evidence only. |
| `community_data_cited_in_pub` | Add; three definitive verdicts | `dataset.13`: searches citation indexes. No match cannot establish that no citation exists. Logs reported OpenCitations HTTP 301, so index coverage was partial even when a verdict returned. Evidence only. |
| `fc_metadata_protocol` | Existing test; add question association | `maturity.05`: observes identifier resolution protocol, without checking OAI-PMH, metadata formats or NKR registration. Evidence only. |
| `fc_metadata_persistence` | Existing test; add question association; degraded | `maturity.11`: assumes persistence for DOIs; does not demonstrate tombstones or behaviour after withdrawal. Evidence only. |
| `fc_metadata_identifier_persistence` | Retain its identity in the catalogue; remove landing-page associations | Its scheme verdict cannot answer `dataset.02` or `maturity.02`. Both reference Handles failed this older version; the newer persistence test returned indeterminate. Actual landing observations continue through object discovery. |
| Other available tests | Do not add redundant or unrelated coverage | New protocol, authorisation and unique-identifier versions overlap existing metrics. Open-access-publication detection does not answer the guide's dataset-access question. |
| Other candidates | Do not add on this measurement | Partial service availability, indeterminate responses, domain-specific scope or harvest-only output provide insufficient grounds to widen the invoked set. |

All existing curated health values were refreshed from the same measurement. Availability describes the
service returning a verdict, independently of that verdict's meaning. Existing tests with degraded health
remain visible with their date and status; no-result responses are not failed questions. This selection is
bounded implementation work; the broader test-gap and validity audit remains a separate team review.

No inspected registry or API description claims to test FAIR Signposting, Link headers or linksets. Generic
object discovery can read these standard forms when exposed, but does not validate full Signposting
conformance. `maturity.07` therefore remains a manual assessment with its original sources.

## Re-measure without changing the selection

After building the site and installing Playwright's Chromium:

```sh
node scripts/probe_champion.mjs --jobs 4 --output .cache/champion-health.json
```

The default [candidate list](candidates.json) includes the core and all reviewed candidates. Optional
`--candidates` and `--records` arguments accept reviewed JSON inputs. The browser checks PID resolution
first, uses anonymous requests with no redirects, limits concurrency to four and calls to 60 seconds,
caps each response at 2 MiB, and records incomplete coverage. It writes progress after each call. The full
local report retains response logs; the committed measurement omits logs and preserves the measured
outcomes. The script never selects tests or edits authored content. Scheduled health reporting can use
the report; any selection or mapping change requires content review in a pull request.
