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

### Development container

With Docker and the Dev Containers extension, open this checkout and choose **Reopen in Container**. The image
pins Python 3.12.15 and Node.js 22.23.3, installs the check tools and the lockfile's Playwright Chromium with its
system dependencies, and installs workspace Node packages automatically. Run `python scripts/check_all.py --jobs 4`
without any further setup, or `python scripts/serve.py --build` for the forwarded preview on port 8000. Rebuild
the container after changing the pinned runtimes, requirements or lockfile.

The same setup can be verified without an editor from the repository root:

```bash
docker build -f .devcontainer/Dockerfile -t fair-guide-dev .
docker run --rm --mount type=bind,source="$PWD",target=/workspaces/eosc-fair-guide --mount type=volume,target=/workspaces/eosc-fair-guide/node_modules fair-guide-dev sh -c 'npm ci && python scripts/check_all.py --jobs 4'
```

The bind mount keeps edited sources and generated preview/check reports in the checkout. A separate volume
holds container Node packages, preserving the host installation. The container uses its own `/opt/ms-playwright`
browser installation rather than a host browser cache.

Repository hygiene needs two tools from `requirements-dev.txt`:

```bash
python -m pip install -r requirements-dev.txt
reuse lint                 # every file has a declared licence and copyright
cffconvert --validate      # CITATION.cff is valid
```

Page checks (rendering, accessibility, reflow, embedding) and diagram checks run in Chromium; the commands are listed in
[AGENTS.md](AGENTS.md), and CI runs them on every pull request.

## Review

Checks protect the page and the data; people judge whether the advice is correct and the tone right. The
reviewers are the accounts in [.github/CODEOWNERS](.github/CODEOWNERS); it names only people who are actually
collaborators, never a team that does not exist.

The gates that can be enforced depend on who can review:

- **During the alpha, the maintainer is the only collaborator.** `main` accepts changes only through pull
  requests, the required check "Guide checks and health report" must pass, and nothing is force-pushed or deleted.
  Code-owner approval is not required, because GitHub does not let an author approve their own pull request; a
  release candidate instead needs the maintainer's explicit acceptance before it is tagged.
- **When an eligible content reviewer joins**, add them to `CODEOWNERS` for the content they review
  (`content/`, the stations and checks) and require one approving review from a code owner on `main`. From then
  on, nobody approves their own change.

Automated refreshes and agents never merge their own pull requests.

## Credit and ORCID iDs

Credit follows what people actually did. `CITATION.cff`, the crate and the provenance actions name a person
only with an identity they gave or that is reviewed (their name, their GitHub account and, if they want, their
ORCID iD). Anyone may ask not to have their ORCID iD listed; they are then credited by name only. No identity or
ORCID iD is guessed, and no team or bot is credited as an author.

## Commit messages

Write a short imperative summary line (for example `content: clarify licence advice for data stewards`),
followed by a body when the reason is not obvious. Mention AI assistance in the body when it was used.

## Releases

A release sets one version and the actual release date everywhere they appear: `content/guide.toml` (which the
crate carries), `CITATION.cff`, `package.json` and `package-lock.json` (both of its version fields), and the
`CHANGELOG.md` entry written for the complete pull request. `tests/test_workflows.py` checks that the versions
agree. After the maintainer accepts the candidate, the tag `vX.Y.Z` (or `vX.Y.Z-alpha.N`) on a deployed commit makes
the release workflow draft the release with that commit's verified site.

## Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
