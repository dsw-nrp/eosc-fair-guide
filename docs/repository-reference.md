<!-- type: reference -->
# Repository reference

## Repository layout

| Path | Content |
| --- | --- |
| `content/` | Content sources in TOML: stations, advice, checks, resources, ledger, glossary, callouts, provenance |
| `scripts/` | Standard-library site/crate/API generators and checks; the full validation suite also uses the pinned development tools in `requirements-dev.txt` |
| `tests/` | Tests of the scripts, with a minimal content fixture |
| `profile/` | The guide's RO-Crate profile (SHACL) for the crate's structure |
| `index.html` | The guide page, with empty blocks the build fills |
| `_site/` | The built site, not committed: the page with its data scripts, the knowledge base as an RO-Crate 1.2 and its preview, and the API |
| `assets/` | Styles, scripts, images and rendered diagrams |
| `api/` | The API's documentation page; the build makes the API itself |
| `assets/diagrams/` | Bilingual adaptations of the approved manuscript figures |
| `docs/` | Design and decisions (`design.md`), content model (`content-model.md`) |
| `.github/` | CI workflows, templates and code owners |

The [software practice example](software-practice.md) maps the app's evidence and release verification
steps to its software guidance.

The [model practice example](model-practice.md) follows an actual requirement, question, test and
recorded revision. The conceptual model cites its manuscript as in preparation; assessment requirements
retain their published sources.


Build prerequisites and check commands are in [build and check](how-to/build-and-check.md).
