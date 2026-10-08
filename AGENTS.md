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
3. **Sources, not output.** Content is authored in `content/*.toml`. Never hand-edit `ro-crate-metadata.json`
   or the crate block inlined in `index.html`; run `scripts/build_crate.py`.
4. **Published sources only.** Every advice item and check cites ledger clauses, and every clause points to a
   published source. Unpublished working material is never cited or referenced.
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
13. **Diagrams.** Mermaid sources in `diagrams/`, rendered to SVG in `assets/diagrams/`, each with an accessible
    title and description and paired with prose that states the same meaning.

## Layout

| Path | Content |
| --- | --- |
| `content/` | TOML sources |
| `scripts/` | `build_crate.py` (generator), `check_content.py` (content contract), `vendor_icons.py` (copies the named icons), `refresh_snapshots.py` (scheduled snapshots) |
| `tests/` | Tests of the scripts, with a minimal content fixture |
| `profile/` | SHACL profile for the crate |
| `index.html` | The page and the crate's HTML preview, with the crate inlined |
| `ro-crate-metadata.json` | Generated RO-Crate 1.2 |
| `assets/css/` | `tokens.css` (palette, type, spacing) and `app.css` (layout, components) |
| `assets/js/` | Classic scripts sharing one namespace, so the page also works from a local file: `core.js` (crate index, strings, safe DOM, storage, routing), `views.js`, `live.js` (connectors), `selfcheck.js` (checks, pre-fill, results, exports), `search.js` (universal search), `app.js` (start-up) |
| `assets/img/` | Official EOSC CZ logos (own licence in `LICENSES/LicenseRef-EOSC-CZ-Logo.txt`) |
| `assets/icons/` | Vendored Font Awesome Free icons (CC BY 4.0); written by `scripts/vendor_icons.py`, never by hand |
| `assets/diagrams/` | Rendered SVG diagrams |
| `diagrams/` | Mermaid sources |
| `docs/` | `design.md`, `content-model.md` |
| `.github/` | Workflows, templates, `CODEOWNERS` |

## Commands

```bash
python scripts/build_crate.py           # regenerate the crate, the page blocks and the preview copy
python scripts/build_crate.py --check   # fail if committed output differs from regenerated output
python scripts/check_content.py         # content contract (--base <ref> also checks paradata freshness)
python -m unittest discover -s tests    # tests of the generator, the checks and the snapshot script
python scripts/refresh_snapshots.py     # refresh the re3data, Heslář and FIP Dashboard snapshots (scheduled job)
python scripts/vendor_icons.py          # copy the icons the content names from node_modules (after npm ci); --check fails on drift
```

Structure checks use `requirements-dev.txt`:

```bash
rocrate-validator validate -p ro-crate-1.2 --skip-availability-check .
rocrate-validator validate -p process-run-crate-0.5 -nh --skip-availability-check .
rocrate-validator validate --extra-profiles-path profile -p fair-guide-0.1 -nh --skip-availability-check .
```

Page checks need Node.js and Chromium (installed into the gitignored `.cache/`):

```bash
npm ci
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright npm run browsers
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright npm run check:page   # rendering, axe (WCAG 2.2 A/AA), reflow, iframe, self-check
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright npm run check:live   # real lookups (DataCite, resolvers, nanopublication); needs network
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright node tests/page/screenshots.mjs .cache/screenshots
```

## Visual pass

Passing checks do not make a page finished. Before a page or view is reported done, drive it through its states
(empty, partly and fully answered, pre-filled, extended or collapsed, long and short content, Czech and English)
at desktop and phone widths, take viewport screenshots, and review them for misalignment, crowding, wrapping,
inconsistent spacing and unclear wording. Fix what you find, add a page check for any rule a fix establishes, and
repeat the pass on pages already closed when shared components change.

## Git

- Work on a branch named `agents/<agent>/<topic>` and open a pull request into `main`. Do not push to `main`.
- Keep commits focused, and mention AI assistance in the commit body.
- Scheduled jobs and agents never merge their own pull requests without a code owner's approval.

## Out of scope

- Certifying FAIRness or NRP compliance: the guide advises, NRP decides.
- A backend, proxy or analytics.
- Final text polishing, which the content team does through pull requests.
