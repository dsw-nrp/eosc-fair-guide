<!-- type: explanation -->
# About the Guide

## What the guide offers

- **A path along the research data life cycle:** the steps follow the seven stages of the RDMkit life cycle
  (planning, collecting, processing and analysing data, preserving, sharing and reuse) and end with a check. It
  starts where the user is now.
- **Four lenses on the same path:** researcher, data steward, repository administrator or curator,
  community and FIP.
- **Detail on demand:** one sentence and one concrete action first; steps, reasons and sources on request
  (levels L0–L3).
- **Principle explorer:** every requirement of the analysis under its FAIR principle.
- **Self-check:** the NRP conditions and FAIR maturity kept apart, with no overall score.
- **Evaluations the reader starts:** quick discovery from public records, the curated FAIR Champion tests,
  FAIR-Checker's metrics and a locally loaded F-UJI report, each with its scope, versions and coverage; a
  reader's own answers always stay theirs.
- **Resource and repository finder** with service status and an as-of date.
- **Layers and seams of FAIR implementation:** a model overview and catalogue associations connect guidance
  to responsibilities and information transfers, including hand-offs within a layer.

### The guide and the FIP Dashboard

The [FIP Dashboard](https://fip-dashboard.dmp.eosc.cz/) is the national catalogue of FAIR-enabling resources and
community profiles; it owns their records and answers "which resources and profiles". The guide answers "what to
do and why". The Guide owns its local record IDs and links source-issued Dashboard identifiers through typed
alternates; dated snapshots copy the selected source records while retaining their attribution. The Guide's FIP
completeness check is pre-filled from a dashboard profile, or from a published FIP nanopublication when a profile is
not in the dashboard.

The connector setting `browserAccess` controls whether the page can read the dashboard's API live. With browser
access disabled, the Guide reads a dated snapshot of profiles and resources and identifies it wherever it is used,
with the dashboard's own disclaimer. A scheduled job proposes snapshot updates by pull request. Enable live access
only after reviewing API access from the Guide's actual origin; the snapshot remains the fallback. See
[the catalogue and infrastructure design](design.md#catalogue-and-infrastructure) and
[snapshot refresh](design.md#snapshot-refresh-and-source-watch).


The [reader landing page](../README_en.md) links the published Guide; the [design](design.md) explains implementation decisions.
