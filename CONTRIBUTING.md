# Contributing

Thank you for helping improve the FAIR Data Guide. This file describes how changes reach the guide. Content
rules are in [docs/content-model.md](docs/content-model.md); design decisions are in
[docs/design.md](docs/design.md).

**Using an AI assistant:** Start with the [agent tooling guide](docs/agent-tooling.md) to choose a tool and
workflow. [AGENTS.md](AGENTS.md) supplies the runtime instructions the assistant must read.

## Branches and pull requests

- `main` supplies the `/next/` preview; production comes from checked release artifacts. Pull requests are the
  default delivery path. Explicitly authorized maintainer direct commits remain releasable after the same
  metadata and release checks; this grants agents no permission to push directly or bypass branch protection.
- Name branches by purpose: `content/<topic>` for texts and data, `fix/<topic>` for defects,
  `feature/<topic>` for new behaviour, and `agents/<agent>/<topic>` for work done by an AI agent.
- Keep a pull request to one purpose. Text polishing of one station is a good size.
- Fill in the pull-request template: what changed, why, and which sources support it.
- Describe a notable change for readers or maintainers under `## [Unreleased]` in `CHANGELOG.md`; the
  [changelog policy](docs/changelog.md) says what is notable and what the check enforces.

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
a semantic change is not a wording-only correction. Archive after delivery under fresh approval. Keep temporary
implementation status, remaining work and release-specific decisions in issues and the relevant OpenSpec change.

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

### Fixing a duplicate from a pull request

Comment `/help` on any pull request to see the commands that apply there and whether you may use them. Post a
command as the whole comment. An accepted command gets an 👀 reaction at once and ends with a 🚀 reaction or a
reply that names its workflow run; a command that cannot run is answered with the reason and an alternative.
Commands for the same pull request (or, for `/refresh <source>`, all refreshes) wait their turn instead of
replacing each other.

When the duplicate check names a safe link, a maintainer with current write access can comment
`/fix-duplicates` on an open same-repository pull request that targets the default branch. The trusted workflow
reads that pull request's content and validation attachments as data, applies only safe link suggestions,
adds a provenance action naming the commenter, registers its identifier, and commits the repair through the
same repository-scoped App used by source refresh. It requires a
reviewed `[[person]]` whose `github` is the commenter's login and the `duplicate-fix` instrument; it never
merges, never pushes the default branch, never runs on schedules or forks and never edits
`content/duplicates.toml`. A stale head makes it change nothing. The App secrets are
`SOURCE_REFRESH_CLIENT_ID` and `SOURCE_REFRESH_APP_PRIVATE_KEY`; without them the command is unavailable. Roll
back by reverting its commit or removing the workflow.

For a local edit, run `python scripts/check_duplicates.py --fix`. It applies the safe links, adds one provenance
action naming you and registers its identifier, which is the same complete repair as the command. You are found
through your reviewed `commitNames` or `github` entry matching `git config user.name`; name yourself explicitly with
`--person <your-person-id>` when that does not match or matches several people. With no reviewed identity, nothing
is written: add your reviewed identity first (see [Credit and ORCID iDs](#credit-and-orcid-ids)). Inspect the
printed diff, including `content/provenance.toml` and `content/identifiers.toml`, before committing, then run
`python scripts/check_all.py`. Undo an uncommitted repair with `git restore content/`. Local repairs use atomic file
replacement and restore original bytes on a handled application or recheck failure, including a repair that would
add a content error; restoration errors are reported explicitly. There is no multi-file crash-transaction guarantee.
Running it again after a complete repair changes nothing and, like any clean no-op, returns nonzero.

The command also works on eligible `refresh/<source>` pull requests. Once a repair or other unrecognized
commit is present, source refresh leaves that branch intact and asks for manual reconciliation. Automatic
replacement is allowed only for a nonempty, verified list of commits authored by the refresh App with that
source's expected snapshot message. Reconcile a protected PR by hand or close it so the next refresh can start
from the default branch. If the command reports an unexpected failure, check the branch and workflow run:
the repair commit may already exist even if its success comment failed.

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

- Pull requests into `main` require the check "Guide checks and health report" to pass. Explicitly authorized
  maintainer direct commits remain subject to configured branch protection; nothing is force-pushed or deleted.
- Keep `CODEOWNERS` aligned with eligible reviewers for `content/`, the stations and checks. Require one
  approving code-owner review when an independent eligible reviewer is available. GitHub does not let an
  author approve their own pull request; without an eligible independent reviewer, a release candidate needs
  the maintainer's explicit acceptance before tagging. Track changes to reviewer coverage and branch settings
  in an issue or OpenSpec change.

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
and release dates in `content/guide.toml`, `CITATION.cff`, `.zenodo.json`, `package.json`, `package-lock.json` and
`pyproject.toml`, records the reviewed dispatcher's provenance, and moves the curated `[Unreleased]` notes of
`CHANGELOG.md` into the new release, followed by the merged PRs and direct default-branch commits since the
previous reachable tag, without duplicate PR entries (see the [changelog policy](docs/changelog.md)). The crate and API
derive their metadata from the Guide. The default release PR runs ordinary checks; review and merge it before
using the separate **Tag release** dispatch. Valid metadata committed directly through an authorized maintainer
process is also accepted: tagging checks the current default-branch source, every version/date and nonempty
dated release notes, without requiring a release PR. Preparation and ordinary pushes never create a release tag.

`python scripts/release_versions.py check --site _site` refuses metadata/date disagreements and prose that
restates the Guide version. Tags use `vX.Y.Z` (or a SemVer prerelease suffix). The tag checks and packages the site;
production and the draft release receive those same verified bytes. See [deployment](docs/deployment.md) for
configuration, local fixtures and recovery. These workflows never merge a pull request or publish a release.

`python scripts/check_citation_metadata.py` validates CFF, supported Zenodo import fields and shared software
credit. Keep curated Zenodo references, notes and ROR affiliations; see [metadata ownership](docs/deployment.md#citation-and-zenodo-metadata).
After a corrected new release is successfully archived in Zenodo, add its actual concept-DOI badge to both
README languages and verify the all-versions destination. This is a post-release follow-up; no DOI is invented
or prefilled while archiving is pending.

The footer shows the build's own identity, derived from git rather than an authored field: the version from the
release tag (an untagged build shows the last tag plus its distance and commit, and is marked as the unreleased
`next` preview), the short commit and a date. A machine-readable copy travels in the health result and the release
manifest. The **Tag release** input `release_status` selects `testing` (the default) or `production` (approved
public use). The [deployment status contract](docs/deployment.md#release-status) defines the recorded decision.
Only the clean tagged production job may use that status; local,
dirty and `/next/` builds stay `testing`, even at a release tag. Image metadata comes from the verified artifact,
not from a later checkout or workflow input.

### Release container image

Every tagged release also publishes a container image to the GitHub container registry, assembled from that
release's verified site artifact — never rebuilt from source — so a reader can run the published page locally with
`docker run --rm -p 8080:8080 ghcr.io/dsw-nrp/eosc-fair-guide:latest`. It carries the release tag, a moving
`latest` on every release and a moving `stable` on every non-prerelease. It is signed (cosign, keyless) and attested
against its digest and scanned with Trivy; a failed scan operation blocks publication, while vulnerability
findings are advisory. The release notes record that digest. Its `nginx-unprivileged` base is digest-pinned and
the `docker` Dependabot entry keeps it current.

## Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
