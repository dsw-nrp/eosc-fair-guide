# Agent guide

This is the single guide for AI agents working in this repository. `CLAUDE.md` and
`.github/copilot-instructions.md` only point here. For any change to the guide's content, page or release,
use the editing skill `fair-guide-editor` (`.agents/skills/fair-guide-editor/SKILL.md`, mirrored in
`.claude/skills/`).

## Purpose

A static Czech and English FAIR data guide for EOSC CZ, an official output of NRP KA 5.1. It turns the FAIR
analysis for NRP/NDI (version 1.2, <https://doi.org/10.71495/5dv6-v116>) into a path of stations seen through
four role lenses, with a principle explorer, a self-check, live identifier checks and a resource finder. The
design and every settled decision are in [docs/design.md](docs/design.md); the content rules are in
[docs/content-model.md](docs/content-model.md).

## Invariants

Do not break these without an explicit decision recorded in `docs/design.md`.

1. **Static page, no backend.** HTML, CSS and light vanilla JavaScript. No framework, no build step for the
   browser, no server, no accounts. The page works from `file://`, in an iframe and on any static host.
2. **No external request on load.** External calls start only from a user action and go only to the connectors
   listed in `content/live.toml`; the Content Security Policy is generated from the same list, and the page
   scripts contain no URLs of their own.
3. **Sources, not output.** Content is authored in `content/*.toml`. The build (`scripts/build_site.py`) writes
   the crate, the page's data scripts and generated blocks, the preview, the linkset and the API into `_site/`, which
   is never committed; the committed `index.html` keeps its generated blocks empty. The content checks refuse a
   generated file in the repository.
4. **Published requirement sources.** Every advice item and check cites ledger clauses, and every clause points to a
   published source. The explicitly approved Layers-and-Seams manuscript may be cited as **in preparation**
   for the conceptual model and scoped implementation examples only. It supplies no ledger requirements;
   do not invent its DOI, publication date, publisher or licence. Other unpublished working material is not cited.
5. **Both languages.** Every user-facing string has Czech and English values.
6. **Paradata.** Every content change adds a provenance action (Process Run Crate): agent, instrument (name the
   AI model when one was used), sources consulted, items produced, end time.
7. **Advisory tone.** "Must" appears only where an NRP condition requires something, naming the condition. DOI
   is recommended; other persistent, resolvable, managed identifiers are acceptable.
8. **Honest self-check and live checks.** No overall score. The NRP conditions and FAIR maturity stay separate. A
   service failure is "no result", never a failed requirement, and coverage is always shown.
9. **Accessibility.** WCAG 2.2 AA. Text contrast at least 4.5:1: brand teal `#008691` and pink `#EB5D81` only
   for accents and large text, text tints `#00737D` and `#C2264F`. Nothing conveyed by colour alone. Native
   `details`/`summary` for disclosure. Correct `lang` attributes. Reflow at 320 px. Reduced motion respected.
10. **Safe rendering.** Render content and external responses through text nodes. No `innerHTML` with data, no
    inline scripts or event handlers, no `eval`. Only a small sanitised set of inline elements may come from
    formatted citations.
11. **Dated statuses.** Five-level vocabulary (operational, pilot, in development, planned, prospective) with an
    as-of date.
12. **Snapshots by pull request.** Sources a browser cannot reach enter as dated snapshots; scheduled jobs open
    pull requests or issues and never commit to `main`.
13. **Diagrams.** Mermaid sources in `diagrams/`, rendered to SVG in `assets/diagrams/`, or explicitly approved
    source SVG adaptations. Each has an accessible title and description and equivalent adjacent prose.
    The three approved manuscript figures retain their structure, terminology and scoped status/arrow meanings.

## Layout

| Path | Content |
| --- | --- |
| `content/` | TOML sources |
| `scripts/` | `build_site.py` (builds the site), `build_crate.py` (knowledge base, page and data scripts), `build_api.py` (API), `check_content.py` (content contract), `check_duplicates.py` (one entry per thing), `register_ids.py` (registers new entries' identifiers), `serve.py` (local server), `vendor_icons.py` (copies the named icons), `refresh_snapshots.py` (scheduled snapshots) |
| `tests/` | Tests of the scripts, with a minimal content fixture |
| `profile/` | SHACL profile for the crate |
| `index.html` | The page, with empty blocks the build fills (Content Security Policy, signposts, data scripts, icons) |
| `_site/` | The built site, not committed: the page and its copy as the crate's preview, `ro-crate-metadata.json`, the data scripts `assets/data/kb.js` (the crate) and `ui.js` (interface strings and configuration) that let the page work from a local file, `linkset.json`, the profile and the API |
| `assets/css/` | `tokens.css` (palette, type, spacing) and `app.css` (layout, components) |
| `assets/js/` | Classic scripts sharing one namespace, so the page also works from a local file: `core.js` (crate index, strings, safe DOM, storage, routing, exports), `views.js`, `live.js` (connectors), `selfcheck.js` (checks, pre-fill, results, exports), `search.js` (universal search), `app.js` (start-up) |
| `assets/img/` | Official EOSC CZ logos (own licence in `LICENSES/LicenseRef-EOSC-CZ-Logo.txt`) |
| `assets/icons/` | Vendored Font Awesome Free icons (CC BY 4.0); written by `scripts/vendor_icons.py`, never by hand |
| `assets/diagrams/` | Rendered SVG diagrams |
| `diagrams/` | Mermaid sources |
| `docs/` | `design.md`, `content-model.md` |
| `.github/` | Workflows, templates, `CODEOWNERS` |

## Commands

```bash
python scripts/check_all.py             # build, then every check below at once, each with its result and time (--live adds the network checks)
python scripts/build_site.py            # build the site into _site/ (after npm ci); open _site/index.html
python scripts/build_site.py --sizes    # also print what the page downloads, compressed; every build warns above the budget
python scripts/check_content.py         # content contract and no build output in the repository (--base <ref> also checks paradata freshness)
python scripts/check_duplicates.py      # one entry per thing: no two entries share an address, an identifier, a name or a text
python scripts/register_ids.py          # register the identifiers of new entries in content/identifiers.toml
python -m unittest discover -s tests    # tests of the generator, the checks and the snapshot script
python scripts/refresh_snapshots.py     # refresh the re3data, Heslář and FIP Dashboard snapshots (scheduled job)
python scripts/vendor_icons.py          # copy the icons the content names from node_modules (after npm ci); --check fails on drift
python scripts/serve.py --build         # build, then serve the site with its API at http://127.0.0.1:8000/ (this computer only)
```

Structure checks use `requirements-dev.txt` and validate the built crate, against the profile at the guide's address:

```bash
rocrate-validator validate -p ro-crate-1.2 --skip-availability-check _site
rocrate-validator validate -p process-run-crate-0.5 -nh --skip-availability-check _site
rocrate-validator validate --extra-profiles-path _site/profile -p fair-guide-0.1 -nh --skip-availability-check _site
```

Page checks need Node.js and Chromium (installed into the gitignored `.cache/`) and run on the built site; their
independent sections, and the sweep of every view in several pages, run at once:

```bash
npm ci
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright npm run browsers
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright npm run check:page   # rendering, axe (WCAG 2.2 A/AA), reflow, iframe, self-check
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright npm run check:api    # OpenAPI 3.1, every API file against its schema, links, the documentation page
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright npm run check:live   # real lookups (DataCite, resolvers, nanopublication); needs network
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright npm run check:diagrams   # every Mermaid diagram renders and has accTitle and accDescr
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright node tests/page/screenshots.mjs .cache/screenshots
```

## GUI and UX principles

Start from what the reader wants to do and what an entry means. Navigation, labels, grouping and defaults must
make sense without knowing the data files, registries or implementation. Source, recommendation and verification
are separate facts shown where they help a decision. Apply this lens to every view and review (D-137 in
`docs/design.md`).

Read the whole station through each affected role before adding advice. Integrate with existing steps,
use the responsibility of that role, and omit an addition when it offers no useful action there.
Named tools and services are examples unless a cited requirement actually prescribes them.
Public guide pages explain stable practices. Keep development plans, future assessment baselines and
temporary source-verification commentary in maintainer documentation.

Alignment, spacing and consistency are part of correctness here, not polish. The page checks enforce what can be
measured (`misalignedControls` and `collisions` in `tests/page/check_page.mjs`); the visual pass covers the rest.

- **Centre what belongs together.** Icon and label in a control sit on one middle line; when a label wraps, the icon
  sits on its first line or on the whole label, never in between, and an icon-only control centres its icon exactly.
  Space comes from the container's `gap` and the spacing tokens, never from a margin on an icon or a one-off value.
- **Nothing collides or touches unless decided.** Text, icons, fields and boxes keep apart, and boxes side by side or
  stacked keep at least the smallest spacing token between them. Where contact is the design (the funder's logo set),
  mark the container `data-joined` so the decision shows in the markup and in review. Something may lie over a form
  field only within its padding, as the clear button does.
- **Reflow and touch.** Nothing scrolls sideways at 320 px; a button is at least 2.75rem (44 px) high and every other
  target at least 24 px (WCAG 2.2, checked by axe); a long identifier or address never widens a column, so room
  reserved for a corner element must still fit a phone.
- **One look per role.** Actions in one row share one style (an export that is a link looks like the buttons beside
  it); a control marks the page it opens, not an unrelated menu item; links in running text stay quiet (a dotted
  underline), buttons do not.
- **Say it once.** A heading does not repeat what the navigation beside it already says; a separator stays with the
  word before it (a non-breaking space), never starting a line.
- **Plain words.** Spell out an abbreviation where a reader first meets it and link the entry that explains it; give
  an icon-only control an accessible name.
- **Enforce, then trust.** A fix that establishes a rule gets a page check, and a check is trusted only after it has
  reported a planted regression.

## Visual pass

Passing checks do not make a page finished. Before a page or view is reported done, drive it through its states
(empty, partly and fully answered, pre-filled, extended or collapsed, long and short content, Czech and English)
at desktop and phone widths, take viewport screenshots, and review them for misalignment, crowding, wrapping,
inconsistent spacing and unclear wording. Fix what you find, add a page check for any rule a fix establishes, and
repeat the pass on pages already closed when shared components change.

## Git

- Work on a branch named `agents/<agent>/<topic>` and open a pull request into `main`. Do not push to `main`.
- Keep commits focused, and mention AI assistance in the commit body.
- Write `CHANGELOG.md` from the complete, settled pull-request scope; do not append entries for intermediate batches.
- Scheduled jobs and agents never merge their own pull requests without a code owner's approval.

## Out of scope

- Certifying FAIRness or NRP compliance: the guide advises, NRP decides.
- A backend, proxy or analytics.
- Final text polishing, which the content team does through pull requests.
