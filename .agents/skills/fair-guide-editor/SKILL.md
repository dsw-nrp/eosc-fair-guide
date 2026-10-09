---
name: fair-guide-editor
description: Edit the EOSC CZ FAIR guide safely. Use for any change to its content (advice, checks, resources, ledger clauses, callouts, glossary, statuses), to the page, or for a release. Covers the content model, tone, accessibility, paradata, regeneration, checks and release steps.
---

# FAIR guide editor

Use this skill for every change to the guide. Read [AGENTS.md](../../../AGENTS.md) first: its invariants
apply to everything below. Field-level rules are in [docs/content-model.md](../../../docs/content-model.md).

## 1. Find what to change

- Texts and data live in `content/*.toml`. Each entity has a stable `id` (for example a station `repozitar`,
  an advice item `repozitar.SR.L1.2`, a check `S04`, a clause `A.F1.R2`).
- Search by `id` or by a phrase from the page. Never edit what the build makes: the crate, the data scripts and
  the API in `_site/`, and the generated blocks of `index.html`, which stay empty in the repository.
- Page behaviour lives in `assets/js/app.js` (rendering, routing, state) and `assets/js/live.js` (connectors).

## 2. Change content

For an **advice item**:

1. Set the station, lens (`V`, `DS`, `SR`, `K`) and level (`L0`–`L3`). L0 is one sentence and one concrete
   action. L1 is steps. L2 is generated from the cited clauses. L3 is generated from sources and paradata.
2. Write both `cs` and `en` text. Czech is the primary language; English says the same, not more. Where the
   text names a resource, source or glossary term, mark it as `[[id|phrase]]` (`term:<id>` for a term), in both
   languages with the words each sentence uses; the content checks reject unknown IDs and uneven languages.
3. Cite at least one ledger clause in `sources`. If the fact has no clause yet, add one to the ledger first
   (step 3).

For a **check**: set `check`, `tier`, `principle` (w3id IRI), the statement in both languages, `sources`,
`fixAt` (station and lens), `owner`, and `prefill` where a live source can answer it. Never add a score.

For a **resource**: set type, `status` (operational, pilot, in development, planned, prospective) with
`asOf`, lenses, stations, and `sameAs` for its published FER nanopublication or FAIRsharing DOI where one
exists. Links use HTTPS.

## 3. Sources and the ledger

- Every clause in the ledger points to a published source: the FAIR analysis (`A.*`, `K*`), the NRP
  conditions (`C.*`), the NRP documentation (`DOC.*`) or a published paper, dataset or page (`E.*`).
- Unpublished working material is never cited. When a fact comes from such material, find the published
  source it relies on and cite that.
- Clause IDs are stable. Do not renumber; retire a clause by marking it superseded.

## 4. Tone

- Advisory: recommend and explain why. Use "musí" / "must" only for NRP conditions, and name the condition
  ("Podmínky NRP vyžadují…").
- DOI is the recommended persistent identifier; Handle, ARK, URN:NBN and other persistent, resolvable,
  managed identifiers are acceptable.
- Automated FAIR results reflect repository configuration more than the author's work; never present them as
  a verdict on people.
- Short sentences, one idea each. Explain a term on first use or link it to the glossary.

## 5. Accessibility

- Status and results are conveyed by text and icon, never by colour alone.
- Body text uses the text tints (`#00737D`, `#C2264F`), not the raw brand colours.
- New controls are native elements, reachable and operable by keyboard, with a visible focus.
- Every diagram has an accessible title and description and adjacent prose with the same meaning.
- Mark language changes inside a text with a language tag in the content (see the content model).

## 6. Paradata

Add one provenance action per change batch to `content/provenance.toml`:

- `agent`: the person responsible, with ORCID where available;
- `instrument`: the tools used, naming the AI model when one was used;
- `object`: the ledger clauses and sources consulted;
- `result`: the IDs of the items created or changed;
- `endTime`: when the change was finished.

The content check fails when a changed item has no action newer than the last release.

## 7. Build and check

```bash
python scripts/build_site.py
python scripts/check_content.py
```

Then open `_site/index.html` (or `python scripts/serve.py` to use the API) and look at the changed station in each affected lens and in both languages. Before
the pull request, run every check at once with `python scripts/check_all.py` (after `npm ci` and installing
`requirements-dev.txt`).

## 8. Pull request

Work on `agents/<agent>/<topic>` (or `content/<topic>` for people), open a pull request into `main`, fill in
the template, and wait for CI and a code owner. Do not merge your own pull request.

## 9. Release

1. Move the `Unreleased` entries in `CHANGELOG.md` under the new version and date.
2. Set the same version and date in `CITATION.cff` and in the crate's publication metadata
   (`content/guide.toml`), then build.
3. Open the release pull request; after merge, tag `vX.Y.Z` and publish the release notes.
