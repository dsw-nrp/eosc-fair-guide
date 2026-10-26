---
applyTo: "**"
---

<!-- Generated from .agents/guide/rules/fair-guide-content.md; run scripts/generate_agent_surfaces.py. -->

# FAIR guide content and editorial rules

Read these constraints before editing content, the page or an evaluator. Start at `AGENTS.md` and use
`fair-guide-editor` to route the change. The OpenSpec boundary, tooling ownership and execution procedures
are in `.agents/guide/rules/fair-guide-surfaces.md` and `docs/agent-tooling.md`.

## 1. Find what to change

Every normalized catalogue record has one Guide-owned primary `id`. Imported source IDs belong in typed
`alternateIds = [{ scheme = "knav", value = "github" }]`, using the actual source issuer and value. Never put an
obsolete own ID there. Do not add `guideId`, old-route aliases or another full-address mapping. Source joins use
explicit alternates; titles, external IDs/IRIs, URLs and classifications cannot silently change the local ID.

- Texts and data live in `content/*.toml`. Each authored entry has a locally owned identifier: a station
  `repository`, an advice item `repository.03`, a check `dataset`, a question `dataset.04`, a clause `A.F1.R2`,
  a local test `guide-dataset-01`, an evaluator criterion `provider:f-uji.FsF-F1-02MD`. Identifiers become
  issued at the first official release; before that they may change in place. Issued IDs are never renamed or
  reused; `scripts/register_ids.py` registers new ones and a retired one stays under `[retired]`.
- Search by identifier or by a phrase from the page. Never edit what the build makes: everything in `_site/`
  (the crate, the data scripts, the API, the health report) and the generated blocks of `index.html`, which stay
  empty in the repository.
- Page behaviour lives in `assets/js/`: `core.js` (index, strings, storage, routing), `app.js` (rendering),
  `views.js`, `catalogue.js`, `search.js`, `selfcheck.js`, the deferred `inspection.js` and `providers.js`, and
  `live.js` with the deferred `discovery.js` (connectors).

## 2. Change content

A new advice item, question or resource using the existing fields, lenses and levels is a content instance:
use its published sources, bilingual text, paradata and ordinary checks. A new field, changed assessment meaning,
runtime behaviour, stored format, CI or governance rule needs an approved OpenSpec change before implementation.

For an **advice item**:

1. Set the station, lens (`V`, `DS`, `SR`, `K`) and level (`L0`–`L3`). L0 is one sentence and one concrete
   action; practical steps belong in L1 and their basis in L2. L2 also shows the cited clauses; L3 is generated
   from sources and paradata.
2. Write both `cs` and `en` text. Czech is the primary language; English says the same, not more. Where the
   text names a resource, source or glossary term, mark it as `[[id|phrase]]` (`term:<id>` for a term), in both
   languages with the words each sentence uses; the content checks reject unknown IDs and uneven languages.
3. Cite at least one ledger clause in `sources`. If the fact has no clause yet, add one to the ledger first
   (section 3).

For a **question** (`[[item]]` in `content/checks/<check>.toml`): set `tier`, `principles`, the `statement` in
both languages, `sources`, `fixAt`, `owner`, the `modes` or `profiles` it applies to, and `prefill` where a live
source can answer it, with `prefillLevel` or `championEvidenceOnly` where that source covers only part of it.
Never add a score.

For a **resource**: set type, `status` (operational, pilot, in development, planned, prospective) with `asOf`,
lenses, stations, and `sameAs` for its published FER nanopublication or FAIRsharing DOI where one exists. Links
use HTTPS.

## 3. Sources and the ledger

- Every clause in the ledger points to a published source: the FAIR analysis, the NRP conditions and
  documentation, or a published paper, dataset, standard or page. Keep original wording, conditions and
  normative strength; an original passage stays supplementary and quieter than the Guide's own text.
- The approved Layers-and-Seams manuscript is the sole exception: cite it as **in preparation** only for the
  conceptual model and scoped implementation examples in `content/model.toml`. It cannot supply ledger
  requirements, and no DOI, publication date, publisher or licence may be invented. For other unpublished
  working material, find the published source it relies on and cite that.
- Clause IDs are stable. Do not renumber; retire a clause by marking it superseded.

For **model associations**, reference the shared layer and seam IDs in `content/model.toml` for each reviewed
target. Associate what a question or test actually addresses; do not infer links from all its citations. Generic
layer and seam definitions carry no implementation status. A separate example names its precise scope, evidence
and observation date. Context explanations address an existing station and lens and belong in **Proč**.

## 4. Evaluators, tests and evidence

- **Tests.** A local test (`[[test]]` in `content/live.toml`) inspects part of one question; its function and
  documentation are attached files. FAIR Champion tests keep their curated selection and dated health
  (`docs/champion/selection.md`).
- **External evaluators** (`[[provider]]`): keep each metric's `id` and `name` exactly as the provider publishes
  them, give an existing FAIR `principle` and a bilingual `label`, and list in `reviewed` the version
  combinations you checked (`{ api = "1.0" }`, or a F-UJI metric version with its specification DOI). A
  `[[provider.mapping]]` says whether the criterion covers a whole question or part of it, with a bilingual note
  on what it covers. Map `whole` only when a native pass establishes everything the question asks; a narrower
  criterion is `partial`, and an unrelated one stays unmapped. A new provider version needs its own review
  before it is listed.
- **What the runtime does with them.** Read each result as the provider presents it: FAIR-Checker scores 2, 1
  and 0 mean met, partly met and not met; an all-zero assessment establishes nothing. F-UJI's maximum maturity
  level is met, intermediate levels partly met, and level 0 not established; retain its native status
  separately. For a reviewed version, whole coverage suggests Yes, Partly or No from that reading; partial
  coverage suggests Partly when its part is met (even partly), or No when it fails. Unavailable, unestablished
  and unreviewed results suggest nothing. Whole-question evidence outranks partial evidence; disagreements stay
  for the reader to settle. A reader's answer is never replaced. Late results for another target are discarded.
  Provider scores stay native and are never combined into a FAIR score.
- **Retention.** One record per accepted assessment; questions refer to it. Original reports are kept once per
  digest and leave the browser only in the complete evidence download. A result with assessments is format
  revision 3; keep revisions 1 and 2 loadable.
- **Fixtures.** Provider tests use the synthetic reports in `tests/fixtures/providers/`; never commit a real
  report's subject metadata.

## 5. Tone

- Advisory: recommend and explain why. Use "musí" / "must" only for NRP conditions, and name the condition
  ("Podmínky NRP vyžadují…"). Name NRP admission only where a check is about it.
- DOI is the recommended persistent identifier; Handle, ARK, URN:NBN and other persistent, resolvable, managed
  identifiers are acceptable.
- Automated FAIR results reflect repository configuration more than the author's work; never present them as a
  verdict on people, and say what a result does not establish.
- Short sentences, one idea each. Explain a term on first use or link it to the glossary.
- Where the text means this Guide, write Průvodce / the Guide with a capital letter. A generic use (a licence
  selector, another organisation's guide) stays in lower case; add a new one to `genericGuideUses` in
  `content/guide.toml`.

## 6. Accessibility and visuals

- Status and results are conveyed by text and icon, never by colour alone. Answer states, provider verdicts and
  retrieval health keep separate, labelled marks.
- Body text uses the text tints (`#00737D`, `#C2264F`), not the raw brand colours.
- New controls are native elements, reachable and operable by keyboard, with a visible focus.
- A reader visual is a labelled ordered list from one maintained definition: `visual.<name>` in
  `content/ui.toml`, or the model's seam records for hand-overs. It needs a title, adjacent prose with the same
  meaning and no drawing runtime. The approved manuscript figures are copied exactly; keep their geometry,
  terminology and scoped status/arrow meanings in both languages.
- Maintainer diagrams are Mermaid in Markdown with `accTitle` and `accDescr`. The content model's
  entity-relationship diagram is defined once, in `docs/content-model.md`.
- Mark language changes inside a text with a language tag in the content (see the content model).

## 7. Paradata and credit

Add one provenance action per pull request by default to `content/provenance.toml` and register it. Extend that
action as the pull request changes; use finer actions only for separately attributable work. The initial public
state consolidates unreleased preparation actions without changing source attribution:

- `agent`: the person responsible, from `[[person]]` in `content/guide.toml`;
- `instruments`: the tools used, naming the AI model as an instrument when one was used (never as an author);
- `objects`: the ledger clauses and sources consulted;
- `results`: the IDs of the items created or changed (a trailing `*` matches a prefix, such as `provider:*`);
- `endTime`: when the change was finished, with its offset.

Every compared kind needs paradata: Guide metadata, clauses, advice, questions, resources, tests, evaluator
criteria (with their mappings and reviewed versions), organisations, pages, curated repositories/sources,
callouts and the model. The content check compares the content with the merge base of the default branch
(`--base`, which `check_all.py` sets to the remote's default branch): an item that changed since then needs an
action added since then, or an existing one extended with a later `endTime`, that covers it. Never move an
`endTime` only to pass the check. Snapshot refreshes are recorded with the run and source by automation;
a person reviews them. `scripts/contributors.py` suggests credit from reviewed identities (`github`,
`commitNames`); it never guesses a person, and an opted-out ORCID stays hidden.
