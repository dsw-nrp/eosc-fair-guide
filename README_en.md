# FAIR data guide (EOSC CZ)

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
- **Self-check:** the NRP onboarding gate and FAIR maturity kept apart, with no overall score.
- **Live identifier check:** a quick check, and an opt-in deep check with FAIR Champion.
- **Resource and repository finder** with service status and an as-of date.

## Running the guide

Open `index.html` in a browser. Nothing is installed, and the page works offline; only the live checks need
the internet. The page can be embedded in another site (iframe) or hosted on its own.

For a local server, which some browsers need for clipboard features:

```bash
python -m http.server 8000
```

## Repository layout

| Path | Content |
| --- | --- |
| `content/` | Content sources in TOML: stations, advice, checks, resources, ledger, glossary, callouts, provenance |
| `scripts/` | Crate generator and content checks (Python standard library only) |
| `profile/` | SHACL profile for the crate's structure |
| `index.html` | The guide page; also the crate's HTML preview, with the crate inlined |
| `ro-crate-metadata.json` | The knowledge base as an RO-Crate 1.2 (generated) |
| `assets/` | Styles, scripts, images and rendered diagrams |
| `diagrams/` | Mermaid diagram sources |
| `docs/` | Design and decisions (`design.md`), content model (`content-model.md`) |
| `.github/` | CI workflows, templates and code owners |

## Editing content

Content is authored in `content/*.toml`, never directly in `index.html` or `ro-crate-metadata.json`. The rules
are in [docs/content-model.md](docs/content-model.md); in short:

- every user-facing text exists in Czech and English;
- every advice item and check cites at least one clause of the ledger, and every ledger clause points to a
  published source;
- every content change adds a provenance action naming the person, the tool (including any AI model) and the
  sources;
- statuses use the five-level vocabulary and carry an as-of date.

After editing, regenerate and check:

```bash
python scripts/build_crate.py
python scripts/check_content.py
```

Agents and maintainers who edit with an AI assistant use the `fair-guide-editor` skill
(`.agents/skills/fair-guide-editor/SKILL.md`); the agent guide is [AGENTS.md](AGENTS.md).

## Contributing

Every change arrives as a pull request into `main`. CI checks structure, content, page integrity,
accessibility, links, diagrams and repository hygiene; a code owner reviews correctness and tone. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

Code is licensed under MIT and content under CC BY 4.0. Per-file licensing is declared in
[REUSE.toml](REUSE.toml); full texts are in [LICENSES/](LICENSES/).

## Authors and citation

The guide is implemented by David Novák (<https://orcid.org/0000-0001-6592-6291>). Its expert basis is the
analysis by Ilona Trtíková, Petra Bártková, Lada Biedermannová, Jindřich Fejfar, Robert Pergl, David Novák
and Tomáš Čížek. How to cite the guide: [CITATION.cff](CITATION.cff).

## Use of artificial intelligence

An AI assistant (Claude, Anthropic) contributed to the content and code. Every content change is recorded in
the knowledge base's paradata, including the tool used, and the guide shows it for each item. People review
the texts.

## Acknowledgement

This output was developed with financial contributions from the EOSC CZ initiative through the National
Repository Platform for Research Data project (CZ.02.01.01/00/23_014/0008787), funded by the Programme
Johannes Amos Comenius (P JAC) of the Ministry of Education, Youth and Sports of the Czech Republic (MEYS).
