<!-- type: reference -->
# Software practice in this guide

This evidence map is a worked example of software assessment. Evaluate the files and published artifacts of
the specific release being assessed; a source checkout alone does not prove publication or preservation.
It follows [FAIR-IMPACT FRSM 1.0](https://fair-impact.eu/metrics-software), based on
[FAIR4RS](https://doi.org/10.1038/s41597-022-01710-x). The guide's software check uses these metric identifiers
separately from the data FAIR definitions.

| Criterion | Evidence to verify for the assessed release |
| --- | --- |
| FRSM-01, FRSM-03 | Version fields, the source repository and immutable release references identify the software. |
| FRSM-02 | Source modules and files are identifiable within Git. |
| FRSM-04, FRSM-05 | README pair and resolved release status describe purpose and intended use. |
| FRSM-06 | CITATION.cff and content/guide.toml name the responsible person and credit source authors separately. |
| FRSM-07, FRSM-08 | The crate describes software and source separately from the content dataset. |
| FRSM-09 | Git repository and HTTPS address. |
| FRSM-10 | docs/content-model.md describes TOML inputs; the build emits RO-Crate JSON-LD and JSON API records. |
| FRSM-11 | Static API with OpenAPI description and contract checks. |
| FRSM-12 | Metadata links the content dataset and cited source objects; source and software entities are related. |
| FRSM-13 | pyproject.toml, package-lock.json, requirements-dev.txt and docs/how-to/build-and-check.md describe build/runtime needs. |
| FRSM-14 | tests/ and scripts/check_all.py check content, exports, rendering, accessibility and formats. |
| FRSM-15, FRSM-16 | REUSE layout, MIT code, CC BY 4.0 content and separate crate licences. |
| FRSM-17 | Git history, docs/design.md and content/provenance.toml retain changes, responsibility and reasoning. |

[CODE](https://doi.org/10.1038/s41597-026-06705-6) supports gradual adoption: document a small example,
run it, and make collaboration practical. The [build how-to](how-to/build-and-check.md) sets up the checkout. `python scripts/build_site.py` creates
`_site/index.html`, the knowledge-base crate and static API. Opening that page should show the testing
notice and the lifecycle entry; `python scripts/check_content.py` should report no errors. The build needs
Python 3.11 or later and the pinned Node.js packages that `npm ci` installs. The full test suite also needs
`requirements-dev.txt`.

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
Use SECURITY.md, CONTRIBUTING.md, workflow results and the published release as evidence. Record each
assessment, missing evidence and follow-up work in its issue or OpenSpec change. No registration, badge or
independent FAIR certification is claimed by this example.

The crate uses `#guide-software` for the application, `#guide-source` for source-code description and `./`
for the content dataset. Software uses MIT; the dataset uses CC BY 4.0. People remain responsible agents;
AI assistants appear as instruments in provenance, with actual available model information. This Process Run
Crate does not establish CPM, ISO 23494 or FDO conformance.
