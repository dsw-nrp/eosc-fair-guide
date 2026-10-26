<!-- type: landing -->
# FAIR Data Guide (EOSC CZ)

[![DOI](https://zenodo.org/badge/1409358632.svg)](https://zenodo.org/badge/latestdoi/1409358632) [![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/dsw-nrp/eosc-fair-guide)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/dsw-nrp/eosc-fair-guide) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

An interactive guide for researchers, data stewards, repository administrators and research communities: from
planning data through choosing a repository, describing and licensing data, to publication, citation and checking.
It builds on the *Analysis and proposal of procedures for implementing the FAIR principles in NRP/NDI*
(version 1.2, NRP KA 5.1, <https://doi.org/10.71495/5dv6-v116>).

[Česky](README.md) · **[Open the Guide](https://fair.eosc.cz/)**

AI-assisted contributions start with [agent tooling](docs/agent-tooling.md); [AGENTS.md](AGENTS.md) is the
assistant's runtime entry.

## What the Guide offers

- A path through the seven RDMkit life-cycle stages and a final check, through four role lenses.
- One action first, with steps, reasons and sources on demand (L0–L3).
- A FAIR principle explorer, a dated resource and repository finder, and a layers-and-seams model.
- Separate NRP-condition and FAIR-maturity self-checks, without an overall score.
- Optional discovery, FAIR Champion, FAIR-Checker and local F-UJI reports, with versions, scope and coverage;
  your own answers stay yours.

The [FIP Dashboard](https://fip-dashboard.dmp.eosc.cz/) owns community profiles and enabling-resource records;
the Guide explains what to do and why. Browser access and dated snapshot use are described in
[About the Guide](docs/about.md#the-guide-and-the-fip-dashboard).

Weekly snapshot proposals cover Heslář, re3data, FIP Dashboard, NKR, KNAV, FAIRsharing and DataCite;
each changed source is reviewed through a pull request.

## Use or contribute

| Goal | Start here |
| --- | --- |
| Open a local copy or run checks | [Build and check](docs/how-to/build-and-check.md) |
| Put the Guide on another website | [Embed the Guide](docs/embedding.md) |
| Improve content or code | [Contributing](CONTRIBUTING.md) |
| Merge, release or maintain it | [Maintainer tasks](docs/ci.md) |
| Understand the data and application | [Content model](docs/content-model.md), [design](docs/design.md) and [repository layout](docs/repository-reference.md) |
| Examine the Guide's own practice | [Software evidence](docs/software-practice.md) and [model example](docs/model-practice.md) |

The built page works offline, from a local file, in an iframe or on a static host. Only user-started live checks
need the internet. Content sources are TOML; the build creates the crate, page and static API in `_site/`.
Production comes from verified releases; `/next/` is the checked default-branch preview.

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
