<!-- type: how-to -->
# Build and check the Guide locally

This guide sets up a checkout, builds the site and runs the same checks as the pull-request run. You need
Python 3.11 or later and Node.js; the [development container](#use-the-development-container) has everything.

## Set up once

Install the pinned Node.js packages, the Chromium the page checks use and the Python check tools:

```bash
npm ci
npm run browsers
python -m pip install -r requirements-dev.txt
```

The browser goes into the repository's own cache, `.cache/ms-playwright`, on Windows and Unix. Set
`PLAYWRIGHT_BROWSERS_PATH` only to use another installation; `npm ci` alone installs the driver, not the browser.

## Build and look at the site

```bash
python scripts/build_site.py
```

Open `_site/index.html`. The built page works offline; only the live checks need the internet. Some browsers need a
local server for clipboard features, and the API documentation needs one too:

```bash
python scripts/serve.py --build
```

Then open <http://127.0.0.1:8000/> and <http://127.0.0.1:8000/api/>.

## Run the checks

Before a pull request, run every check at once:

```bash
python scripts/check_all.py
```

It builds the site first and reports each check's result and time. `--only content page` runs named checks, `--jobs 4`
sets the parallel work and `--live` adds the checks that need the network. The run writes a health dashboard
(`index.html`), `health.json` and a Markdown summary to `.cache/health/`; `--previous-report path/to/health.json`
compares two runs. The [CI reference](../ci-reference.md#local-reproduction) explains the profiles and budgets.

Single checks while you work:

```bash
python scripts/check_content.py    # languages, sources, paradata, links, statuses, identifiers
python scripts/check_duplicates.py # one entry per thing
python scripts/check_docs.py       # documentation types, runbook steps and named files
python scripts/register_ids.py     # after adding entries: register their identifiers
reuse lint                         # every file has a declared licence and copyright
cffconvert --validate              # CITATION.cff is valid
```

## Use the development container

With Docker and the Dev Containers extension, open the checkout and choose **Reopen in Container**. It pins Python
and Node.js, installs the check tools and Chromium, and installs the Node packages. Run
`python scripts/check_all.py --jobs 4` without further setup, or `python scripts/serve.py --build` for the preview
on port 8000. Rebuild the container after the pinned runtimes, requirements or lockfile change.

Without an editor, the same setup runs from the repository root:

```bash
docker build -f .devcontainer/Dockerfile -t fair-guide-dev .
docker run --rm --mount type=bind,source="$PWD",target=/workspaces/eosc-fair-guide --mount type=volume,target=/workspaces/eosc-fair-guide/node_modules fair-guide-dev sh -c 'npm ci && python scripts/check_all.py --jobs 4'
```

The bind mount keeps your edits and reports in the checkout; a separate volume holds the container's Node packages,
and the container uses its own browser installation.
