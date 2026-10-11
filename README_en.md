# FAIR Data Guide (EOSC CZ)

An interactive guide that takes researchers, data stewards, repository administrators and research
communities along the path to FAIR data: from the project plan through choosing a repository, describing and
licensing the data, to publication, citation and checking. It builds on the *Analysis and proposal of
procedures for implementing the FAIR principles in NRP/NDI* (version 1.2, NRP KA 5.1,
<https://doi.org/10.71495/5dv6-v116>) and brings it up to date with the current state of national services.

> **Status:** work in progress. Texts are drafts; the team edits them before the guide is announced.

This file is the operational README for maintainers and agents. The Czech [README.md](README.md) is the
human-facing overview.

## What the guide offers

- **A path of nine stations:** Plan → Work → Repository → Description → Licence and access → Publication →
  Findability → Citation and credit → Check. It starts where the user is now.
- **Four lenses on the same path:** researcher, data steward, repository administrator or curator,
  community and FIP.
- **Detail on demand:** one sentence and one concrete action first; steps, reasons and sources on request
  (levels L0–L3).
- **Principle explorer:** every requirement of the analysis under its FAIR principle.
- **Self-check:** the NRP conditions and FAIR maturity kept apart, with no overall score.
- **Live identifier check:** a quick check, and an opt-in deep check with FAIR Champion.
- **Resource and repository finder** with service status and an as-of date.
- **Layers and seams of FAIR implementation:** a model overview and catalogue associations connect guidance
  to responsibilities and information transfers, including hand-offs within a layer.

## Running the guide

On first use, install the pinned Node.js dependencies for the bundled API documentation.
Build with Python 3.11 or later, then open `_site/index.html`:

```bash
npm ci
python scripts/build_site.py
```

The generator uses the Python standard library; adapted SVG figures are local assets.
The built page works offline; only the live checks need the
internet. It can be embedded in another site (iframe) or hosted on its own.

For a local server, which some browsers need for clipboard features:

```bash
python scripts/serve.py --build
```

The guide documents its own research software practice. The first official prerelease will establish
the baseline; archiving the public code and any OpenSSF self-certification remain release steps.

## Repository layout

| Path | Content |
| --- | --- |
| `content/` | Content sources in TOML: stations, advice, checks, resources, ledger, glossary, callouts, provenance |
| `scripts/` | Crate generator, API build and content checks (Python standard library only) |
| `tests/` | Tests of the scripts, with a minimal content fixture |
| `profile/` | The guide's RO-Crate profile (SHACL) for the crate's structure |
| `index.html` | The guide page, with empty blocks the build fills |
| `_site/` | The built site, not committed: the page with its data scripts, the knowledge base as an RO-Crate 1.2 and its preview, and the API |
| `assets/` | Styles, scripts, images and rendered diagrams |
| `api/` | The API's documentation page; the build makes the API itself |
| `assets/diagrams/` | Bilingual adaptations of the approved manuscript figures |
| `docs/` | Design and decisions (`design.md`), content model (`content-model.md`) |
| `.github/` | CI workflows, templates and code owners |

The [software practice example](docs/software-practice.md) maps the app's evidence and remaining release
steps to its software guidance.

The [model practice example](docs/model-practice.md) follows an actual requirement, question, test and
recorded revision. The conceptual model cites its manuscript as in preparation; assessment requirements
retain their published sources.

## Editing content

Content is authored in `content/*.toml`, never in what the build makes. The rules
are in [docs/content-model.md](docs/content-model.md); in short:

- every user-facing text exists in Czech and English;
- every advice item and check cites at least one clause of the ledger, and every ledger clause points to a
  published source;
- every content change adds a provenance action naming the person, the tool (including any AI model) and the
  sources;
- statuses use the five-level vocabulary and carry an as-of date.

After editing, build the site and check it; then open `_site/index.html`:

```bash
python scripts/build_site.py
python scripts/check_content.py
```

To run every check at once, use `python scripts/check_all.py` (after `npm ci` and installing the tools
from `requirements-dev.txt`).
The run writes a health dashboard (`index.html`), JSON inventory and Markdown summary to
`.cache/health/`, including check outcomes and original-source coverage for questions, station advice
and clauses. CI publishes these as a run artifact and step summary. `--live` adds external service
checks; an offline run explicitly leaves live availability unchecked. To compare two saved reports,
use `--previous-report path/to/health.json`.
The built API also exposes the report at `api/health.json`, documented in `openapi.json`. A build alone
reports no completed check run; the check runner publishes its actual results at that endpoint.
The site also publishes the English dashboard at `health/index.html`, linked
from the footer and Data for machines. The JSON and dashboard receive the same check-run results.

To see the guide with its API as it will be published, serve it on your computer (the API documentation needs
`npm ci` once), then open <http://127.0.0.1:8000/> and <http://127.0.0.1:8000/api/>:

```bash
python scripts/serve.py --build
```

Agents and maintainers who edit with an AI assistant use the `fair-guide-editor` skill
(`.agents/skills/fair-guide-editor/SKILL.md`); the agent guide is [AGENTS.md](AGENTS.md).

## Contributing

Every change arrives as a pull request into `main`. CI checks structure, content, page integrity,
accessibility, links, diagrams and repository hygiene; a code owner reviews correctness and tone. See
[CONTRIBUTING.md](CONTRIBUTING.md).

The PR check workflow runs with read-only permissions. A separate trusted workflow posts the bilingual
review comment and links to its checks and preview artifacts. It reads only bounded review data from
the completed run, uses default-branch code and checks the current PR head before posting.

The [Champion selection record](docs/champion/selection.md) explains test scope and the dated health
measurement. To remeasure all reviewed candidates and the core after building the site, run
`node scripts/probe_champion.mjs --jobs 4 --output .cache/champion-health.json`. This does not edit the selection.

The first official prerelease tag is `v1.0.0-alpha.1`; application and citation metadata use `1.0.0-alpha.1`.

## Licence

Code is licensed under MIT and content under CC BY 4.0. Per-file licensing is declared in
[REUSE.toml](REUSE.toml); full texts are in [LICENSES/](LICENSES/).

## Authors and citation

The guide is implemented by David Novák (Library of the Czech Academy of Sciences and Institute of Archaeology of the Czech Academy of Sciences, Prague; <https://orcid.org/0000-0001-6592-6291>). Its expert basis is the
analysis by Ilona Trtíková, Petra Bártková, Lada Biedermannová, Jindřich Fejfar, Robert Pergl, David Novák
and Tomáš Čížek. How to cite the guide: [CITATION.cff](CITATION.cff).

## Use of artificial intelligence

AI assistants Claude (Anthropic) and Codex (OpenAI) contributed to the content and code.
Every content change is recorded in
the knowledge base's paradata, including the tool used, and the guide shows it for each item. People review
the texts.

## Acknowledgement

This output was developed with financial contributions from the EOSC CZ initiative through the National
Repository Platform for Research Data project (CZ.02.01.01/00/23_014/0008787), funded by the Programme
Johannes Amos Comenius (P JAC) of the Ministry of Education, Youth and Sports of the Czech Republic (MEYS).
