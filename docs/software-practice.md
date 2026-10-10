# Software practice in this guide

The first official prerelease is the assessment baseline. The current development checkout prepares it.
This evidence map is a worked example, not a certificate or a claim that a public release already exists.
It follows [FAIR-IMPACT FRSM 1.0](https://fair-impact.eu/metrics-software), based on
[FAIR4RS](https://doi.org/10.1038/s41597-022-01710-x). The guide's software check uses these metric identifiers
separately from the data FAIR definitions.

| Criterion | Evidence available in development | First-prerelease follow-up |
| --- | --- | --- |
| FRSM-01, FRSM-03 | Version fields and the source repository identify the development project. | Publish the exact release, verify its archived code reference and record any release PID. |
| FRSM-02 | Source modules and files are identifiable within Git. | Use precise archival references where separately reused components need them. |
| FRSM-04, FRSM-05 | README pair and testing notice describe purpose and development status. | Keep the public metadata and release status consistent. |
| FRSM-06 | CITATION.cff and content/guide.toml name the responsible person and credit source authors separately. | Reconcile release contributors through the contributor workflow. |
| FRSM-07, FRSM-08 | The crate describes software and source separately from the content dataset. | Add the verified release identifier and publish persistent metadata. |
| FRSM-09 | Git repository and HTTPS address. | Make the released source publicly retrievable. |
| FRSM-10 | docs/content-model.md describes TOML inputs; the build emits RO-Crate JSON-LD and JSON API records. | Check example inputs and outputs in the built release. |
| FRSM-11 | Static API with OpenAPI description and contract checks. | Verify the published API paths. |
| FRSM-12 | Metadata links the content dataset and cited source objects; source and software entities are related. | Retain these links in the published crate. |
| FRSM-13 | pyproject.toml, package-lock.json, requirements-dev.txt and README_en.md describe build/runtime needs. | Reproduce the build in a fresh release checkout. |
| FRSM-14 | tests/ and scripts/check_all.py check content, exports, rendering, accessibility and formats. | Run the release checks and retain their results. |
| FRSM-15, FRSM-16 | REUSE layout, MIT code, CC BY 4.0 content and separate crate licences. | Pass REUSE on the release tree. |
| FRSM-17 | Git history, docs/design.md and content/provenance.toml retain changes, responsibility and reasoning. | Link release notes and dated verification evidence. |

[CODE](https://doi.org/10.1038/s41597-026-06705-6) supports gradual adoption: document a small example,
run it, and make collaboration practical. From a fresh checkout, `python scripts/build_site.py` creates
`_site/index.html`, the knowledge-base crate and static API. Opening that page should show the testing
notice and the lifecycle entry; `python scripts/check_content.py` should report no errors. Python 3.11 or
later suffices for this build. Install the pinned development dependencies to run the full test suite.

Choose preservation appropriate to the software: a disciplinary or institutional repository that accepts
code, a general repository such as Zenodo, or a code archive. The released code and its description should
remain identifiable as a specific version. Software Heritage is one code-archive example. If it is used,
verify an SWHID permalink to the release content. Keep credit and licensing discoverable through
CITATION.cff and REUSE. No archival identifier is claimed before verification. A release DOI and a code
SWHID have different roles; record their relationship if both exist. Public deposit or archival submission
is a separate release action.

[OpenSSF Best Practices](https://www.bestpractices.dev/en) is voluntary FLOSS self-certification. Before any
badge claim, assess the official criteria and link evidence for the public repository, contribution and
issue processes, release identification, change notes, vulnerability reporting and automated checks.
SECURITY.md, CONTRIBUTING.md and the local checks are preparation; the planned CI and public release remain
part of release readiness. No registration, badge or independent FAIR certification is claimed here.

The crate uses `#guide-software` for the application, `#guide-source` for source-code description and `./`
for the content dataset. Software uses MIT; the dataset uses CC BY 4.0. People remain responsible agents;
Claude and Codex appear as instruments in provenance, with available model information. This Process Run
Crate does not establish CPM, ISO 23494 or FDO conformance.
