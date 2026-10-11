# Contributing

Thank you for helping improve the FAIR Data Guide. This file describes how changes reach the guide. Content
rules are in [docs/content-model.md](docs/content-model.md); design decisions are in
[docs/design.md](docs/design.md).

## Branches and pull requests

- `main` is the published state. Nobody pushes to it directly; every change arrives as a pull request.
- Name branches by purpose: `content/<topic>` for texts and data, `fix/<topic>` for defects,
  `feature/<topic>` for new behaviour, and `agents/<agent>/<topic>` for work done by an AI agent.
- Keep a pull request to one purpose. Text polishing of one station is a good size.
- Fill in the pull-request template: what changed, why, and which sources support it.

## What every content change needs

1. **Both languages.** Every user-facing text has a Czech and an English value.
2. **Published sources.** Every advice item and check cites at least one clause of the ledger
   (`content/ledger.toml`), and every clause points to a published source: the FAIR analysis, the NRP
   conditions, the NRP documentation, or a published paper, dataset or web page. The approved Layers-and-Seams
   manuscript may be cited as in preparation for the conceptual model and scoped examples only; it supplies
   no assessment requirements. Other unpublished working material is not cited.
3. **Paradata.** Add a provenance action that names who made the change, which tool was used (including any AI
   model), which sources were consulted and which items changed.
4. **Advisory tone.** Recommend; say "must" only where an NRP condition requires something, and name the
   condition. DOI is the recommended persistent identifier; other persistent, resolvable and managed
   identifiers are acceptable.
5. **Dated statuses.** Service statuses use the five-level vocabulary (operational, pilot, in development,
   planned, prospective) with an as-of date.
6. **Regenerated output.** Run the generator so the crate and the page match the sources.

## Checking locally

```bash
python scripts/build_site.py       # build the site into _site/: the crate, the page with its data, the API
python scripts/check_content.py    # content contract: languages, sources, paradata, links, statuses, identifiers
python scripts/check_duplicates.py # one entry per thing: nothing listed or said twice
python scripts/register_ids.py     # after adding entries: register their identifiers
python scripts/check_all.py        # before a pull request: build, then every check at once (--live adds the network checks)
```

`check_all.py` needs `npm ci` and the tools from `requirements-dev.txt`, and reports each check's result and time.

Repository hygiene needs two tools from `requirements-dev.txt`:

```bash
python -m pip install -r requirements-dev.txt
reuse lint                 # every file has a declared licence and copyright
cffconvert --validate      # CITATION.cff is valid
```

Page checks (rendering, accessibility, reflow, embedding) and diagram checks run in Chromium; the commands are listed in
[AGENTS.md](AGENTS.md), and CI runs them on every pull request.

## Review

CI must pass, and a code owner must approve. Checks protect the page and the data; people judge whether the
advice is correct and the tone right. Content code owners review texts; the maintainer reviews the design
documents, the content model and the CI configuration.

## Commit messages

Write a short imperative summary line (for example `content: clarify licence advice for data stewards`),
followed by a body when the reason is not obvious. Mention AI assistance in the body when it was used.

## Releases

A release updates the version and date in `CHANGELOG.md`, `CITATION.cff` and the crate together, and is
tagged `vX.Y.Z`.

## Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
