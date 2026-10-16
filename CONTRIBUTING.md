# Contributing

Thank you for helping improve the FAIR Data Guide. This file describes how changes reach the guide. Content
rules are in [docs/content-model.md](docs/content-model.md); design decisions are in
[docs/design.md](docs/design.md).

## Branches and pull requests

- `main` supplies the `/next/` preview; production comes from checked release artifacts. Nobody pushes to `main`
  directly; every change arrives as a pull request.
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

Changes to behaviour, data/API contracts, stored formats, CI or governance need an OpenSpec change. Read the
relevant installed contracts in `openspec/specs/`, then use the repository's pinned CLI:

```bash
npm ci
npm run openspec:cli -- list --json
npm run openspec:cli -- new change <slug>
npm run openspec:cli -- instructions proposal --change <slug>
npm run openspec:validate
```

Complete proposal/design/specs/tasks and obtain explicit approval before implementation. Typos, wording,
formatting, behaviour-neutral dependency updates and routine source refreshes can use ordinary editing checks;
a semantic change is not a wording-only correction. Archive after delivery under fresh approval. The active
`initial-alpha` package and its [task list](openspec/changes/initial-alpha/tasks.md) state the remaining gates.

```bash
python scripts/build_site.py       # build the site into _site/: the crate, the page with its data, the API
python scripts/check_content.py    # content contract: languages, sources, paradata, links, statuses, identifiers
python scripts/check_duplicates.py # one entry per thing: nothing listed or said twice
python scripts/check_public_content.py --history # public-source and local commit-message hygiene
python scripts/register_ids.py     # after adding entries: register their identifiers
python scripts/check_all.py        # before a pull request: build, then every check at once (--live adds the network checks)
```

`check_all.py` needs `npm ci` and the tools from `requirements-dev.txt`, and reports each check's result and time.
Use `--jobs` for outer work and `--browser-workers` for the shared browser budget. Local and CI defaults live in
[`scripts/check_policy.json`](scripts/check_policy.json); `CI=true` selects the conservative CI profile.
Defaults are capped by the available CPU count. `--browser-workers` overrides `CHECK_BROWSER_WORKERS`, which
overrides the profile; npm and direct Node checks use the same policy. Browser groups
share atomic case slots across Node processes, so inner pools cannot multiply the global limit. `.cache/health/details/` and `logs/` retain timings, complete output,
case coverage and failure artifacts; `execution.json` records the actual profile, budgets, machine and built-input
hashes. The health report marks selected browser subsets as partial. Compare complete runs with identical
coverage and inputs when tuning budgets; a faster selected case does not establish a full-suite improvement.
Stop a benchmark after a failed run, retain its evidence and diagnose it before a corrected verification run.
`npm run check:runtime` checks the launcher, worker policy, partial reporting and actual browser failure artifacts.
Default traces retain actions; a failed case adds a PNG and an HTML snapshot. Set `CHECK_TRACE_SNAPSHOTS=1`
for full trace snapshots when investigating a difficult case.

PR CI runs one verified build through a CPU lane and two browser lanes, then the required `checks` collector.
`scripts/check_ci.py` owns that adapter; `check_all.py` owns the job inventory and `scripts/check_groups.json`
owns nested scripts. The collector verifies source/build identity, every required case and station/PDF coverage;
lane subsets cannot publish a complete pass. Inspect per-lane artifacts as well as the final health report.
Use `CHECK_AXE_MODE=compare` for a paired accessibility equivalence check, or `reference` for the established
adapter. Performance receipts distinguish elapsed time and runner minutes; more runners can increase total cost.
It includes strict OpenSpec validation and public-source hygiene. Install the pinned dependencies rather than
depending on a global OpenSpec command. Generated `_site/`, local caches and environments are never committed.

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

Page checks (rendering, accessibility, reflow, embedding) and diagram checks run in Chromium, which the checks read
from the repository's own cache (`.cache/ms-playwright`, a git-ignored directory). Install it there with
`npm run browsers`; `npm ci` alone installs the driver, not the browser.
The commands are listed in [AGENTS.md](AGENTS.md), and CI runs them on every pull request.

## Review

Checks protect the page and the data; people judge whether the advice is correct and the tone right. The
reviewers are the accounts in [.github/CODEOWNERS](.github/CODEOWNERS); it names only people who are actually
collaborators, never a team that does not exist.

The gates that can be enforced depend on who can review:

- **During the alpha, the code owners are the maintainer and a second owner.** `main` accepts changes only through
  pull requests, the required check "Guide checks and health report" must pass, and nothing is force-pushed or
  deleted. Code-owner approval is not required while the review rules await re-verification after the repository
  transfer, because GitHub does not let an author approve their own pull request; a release candidate instead needs
  the maintainer's explicit acceptance before it is tagged.
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

Use the **Prepare release** manual workflow on the default branch. `scripts/release_versions.py` sets the version
and release dates in `content/guide.toml`, `CITATION.cff`, `package.json`, `package-lock.json` and `pyproject.toml`,
records the reviewed dispatcher's provenance, and writes `CHANGELOG.md` from all pull requests merged since the
previous tag. The crate and API derive their metadata from the Guide. The release pull request runs ordinary
checks; review and merge it before using the separate **Tag release** dispatch on that merged commit.

`python scripts/release_versions.py check --site _site` refuses metadata/date disagreements and prose that
restates the Guide version. Tags use `vX.Y.Z` (or a SemVer prerelease suffix). The tag checks and packages the site;
production and the draft release receive those same verified bytes. See [deployment](docs/deployment.md) for
configuration, local fixtures and recovery. These workflows never merge a pull request or publish a release.

## Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
