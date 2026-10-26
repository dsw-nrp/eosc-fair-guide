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
do and why" and refers to the dashboard's records by their dashboard IDs instead of copying them. The guide's FIP
completeness check is pre-filled from a dashboard profile, or from a published FIP nanopublication when a profile is
not in the dashboard.

The dashboard's API does not yet admit the guide's origin from a browser, so the guide reads a dated snapshot of its
profiles and resources and says so wherever they are used, with the dashboard's own disclaimer. A scheduled job
proposes a snapshot refresh by pull request when the dashboard's data change; once the API admits the guide's origin,
the connector setting `browserAccess` lets the page read it live and keep the snapshot as its fallback. See
[the catalogue and infrastructure design](design.md#catalogue-and-infrastructure) and
[snapshot refresh](design.md#snapshot-refresh-and-source-watch).


The [reader landing page](../README_en.md) links the published Guide; the [design](design.md) explains implementation decisions.
