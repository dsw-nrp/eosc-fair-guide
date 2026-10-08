# Design

This document holds the design of the FAIR data guide: its goals, architecture, the decisions behind it with
the alternatives considered, and the dated decision log. The behaviour is specified in the OpenSpec change
`eosc-fair-guide`, which moves into this repository's `openspec/` tree at the first release; this document is the
guide's own, maintained account of the design. Content rules are in [content-model.md](content-model.md).

## Goals

- A self-explanatory Czech and English guide that leads each role from its current stage to the next concrete
  action.
- Current, sourced advice, with every statement traceable to a published source.
- A self-check that tells repositories what NRP requires and tells everyone where their FAIR gaps are.
- Live checks that help without overstating what automated tests can prove.
- A repository the team can maintain through reviewed pull requests.

## Non-goals

- Certifying FAIRness or NRP compliance: the guide advises, and NRP decides.
- A backend, proxy or user accounts.
- Replacing the FAIR analysis as the normative reference: the guide cites it.
- A national FIP authoring tool or FER catalogue: planned national services cover these.

## Architecture

Every diagram is paired with prose that states the same meaning; the prose is normative and the diagrams
support it.

### At a glance

- A **static page** (HTML, CSS, light vanilla JS, no backend) that can be embedded in eosc.cz, hosted on GitHub Pages, or opened as a file.
- Content is an **RO-Crate 1.2 knowledge base** with **paradata**; the page itself is the crate's HTML preview.
- The main view is a **path of nine stations** seen through **four role lenses**, with detail revealed on demand in levels L0–L3.
- A **self-check** keeps two axes apart, the NRP onboarding gate and FAIR maturity, and never shows an overall score.
- **Live checks** are two-stage: a quick deterministic check, then an opt-in FAIR Champion deep check with coverage shown.
- Every change arrives as a **pull request** through layered CI checks and a code-owner review; scheduled jobs refresh snapshots by PR.
- **OpenSpec-driven:** the guide is planned as an OpenSpec change, which moves into this repository at the first release.

### System context

People in four roles use one static page. The page calls a few open APIs, but only when the user clicks:
DataCite, the DOI and Handle resolvers, ORCID, ROR, the NKR catalogue, the nanopublication query service
(published FIPs), FAIR Champion and the DMP status feed. National services such as NMA, DMP.eosc.cz and identifikatory.cz are linked, not called. Sources
that a browser cannot reach (re3data, Heslář, FER nanopublications, NMA facets, test health) are captured as
snapshots by a scheduled CI job that opens a pull request.

```mermaid
flowchart LR
  accTitle: System context
  accDescr: Four kinds of users open the static guide page. The page calls a small set of open APIs only on click, links out to national services, and reads snapshots that a scheduled CI job refreshes.
  subgraph PEOPLE[People]
    direction TB
    V([Researcher])
    DS([Data steward])
    SR([Repository admin or curator])
    K([Community and FIP])
  end
  G["FAIR guide<br/>static page"]
  subgraph LIVE[Called live, on click]
    direction TB
    DC[DataCite REST]
    RES[doi.org and hdl.handle.net]
    OR[ORCID and ROR]
    NKR[NKR Cordra API]
    NPQ[Nanopub query, published FIPs]
    FC[FAIR Champion, opt-in]
    UP[DMP status feed]
  end
  subgraph LINK[Linked, not called]
    direction TB
    NMA[NMA search and RIV link]
    DMP[DMP.eosc.cz]
    PID[identifikatory.cz]
    MORE[FAIRsharing, FAIR-IMPACT,<br/>CERIT AI, NRP and e-INFRA docs]
  end
  subgraph SNAP[Snapshots by scheduled CI]
    direction TB
    R3[re3data]
    HES[Heslář]
    FER[FER nanopublications]
    NMAF[NMA facets]
    FCH[FAIR Champion test health]
  end
  PEOPLE --> G
  G -- fetch on click --> LIVE
  G -. link .-> LINK
  SNAP -- refresh by PR --> G
```

### Planning record

The guide is planned as an OpenSpec change: a proposal, five capability specs, a design and a task list, with
working notes (decision log, clause ledger, station drafts, self-check design and source inventory). During the
build-out the notes become this repository's content sources and design documents, and the open questions
become issues. At the first release the specs and the archived change move into `openspec/` here, so later
changes are planned in this repository.

```mermaid
flowchart LR
  accTitle: Planning record
  accDescr: The OpenSpec change and its working notes feed this repository. The notes become content sources and issues, and at the first release the specs and the archived change move into the openspec folder here.
  subgraph PLAN["OpenSpec change eosc-fair-guide"]
    direction TB
    CH["proposal, specs,<br/>design, tasks"]
    NOTES["working notes<br/>decisions, ledger, stations, F3, sources"]
    CH --- NOTES
  end
  subgraph TOOL["eosc-fair-guide repository"]
    direction TB
    SRC[content sources]
    PAGE[page and crate]
    ISS[issues]
    OS["openspec/<br/>specs and archive"]
  end
  CH -- implemented --> PAGE
  NOTES -- migrate --> SRC
  NOTES -- open questions --> ISS
  CH -- at first release --> OS
```

### Authoring and build

Editors change small content source files: stations, checks, resources, sources, glossary and callouts. A
generator that needs only the Python standard library turns them into the RO-Crate knowledge base and inlines
the same crate into the page. Mermaid sources render to SVG. CI regenerates both and fails if the committed
output differs, so the browser never needs a build step and pull-request diffs stay readable.

```mermaid
flowchart LR
  accTitle: Authoring and build
  accDescr: Content sources feed a standard-library generator that writes the RO-Crate and the page with the crate inlined. Mermaid sources render to SVG. The browser runs the committed output without a build.
  subgraph AUTH[Authoring time]
    direction TB
    C1["content/*.toml<br/>stations, checks, resources,<br/>sources, glossary, callouts"]
    C2["diagrams/*.mmd"]
    GEN["build_crate.py<br/>standard library only"]
    MMDC[mermaid-cli]
    C1 --> GEN
    C2 --> MMDC
  end
  subgraph OUT[Committed output]
    direction TB
    CRATE["ro-crate-metadata.json<br/>knowledge base and paradata"]
    HTML["index.html<br/>the crate's HTML preview,<br/>crate inlined"]
    SVG["assets/diagrams/*.svg"]
  end
  subgraph RUN[Browser]
    direction TB
    JS["app.js, live.js, i18n"]
    CSS["tokens.css, app.css"]
  end
  GEN --> CRATE
  GEN --> HTML
  MMDC --> SVG
  HTML --> RUN
```

### Content model

A station contains advice items; each item belongs to one lens and one disclosure level and cites
source clauses from the ledger. Clauses serve FAIR principles, identified by their published w3id IRIs.
Checks test a principle, derive from clauses and point to the station where a gap is fixed. Resources are
offered at stations for given lenses and carry a status, an as-of date and links to published FER or
FAIRsharing identifiers. Glossary terms come from Heslář. Paradata actions record who produced or verified
an item, with which tool and from which sources.

```mermaid
erDiagram
  STATION ||--o{ ADVICE : contains
  LENS ||--o{ ADVICE : "seen through"
  ADVICE }o--o{ CLAUSE : cites
  CLAUSE }o--o{ PRINCIPLE : serves
  CHECK }o--|| PRINCIPLE : tests
  CHECK }o--o{ CLAUSE : "derived from"
  CHECK }o--|| STATION : "fixed at"
  RESOURCE }o--o{ STATION : "offered at"
  RESOURCE }o--o{ LENS : "aimed at"
  GLOSSARY_TERM }o--o{ ADVICE : explains
  ACTION }o--o{ ADVICE : produced
  ACTION }o--o{ RESOURCE : verified
  ADVICE {
    string level "L0 to L3"
    string text "cs and en"
  }
  CLAUSE {
    string id "A, K, C, DOC or E"
  }
  PRINCIPLE {
    string iri "w3id FAIR principle"
  }
  CHECK {
    string id "D, P, G, S, K or I"
    string tier "Minimum, Doporučeno, Pokročilé"
  }
  RESOURCE {
    string status "five-level vocabulary"
    date asOf
    string sameAs "FER or FAIRsharing IRI"
  }
  ACTION {
    string agent "person, ORCID"
    string instrument "tool or AI model"
    date endTime
  }
```

### Runtime structure

The shell provides routing by language, lens and station, the language switch, the lens picker, the
disclosure levels and the theme. Six features sit inside it: the path, the principle explorer, the
self-check, the resource finder, the live check and the freshness badges. They share four services: an
index over the crate, connectors limited to an allowlist of hosts, a state store (local storage plus a
shareable link) and export. Self-check gaps link back into the path, and the live check pre-fills
self-check answers.

```mermaid
flowchart TB
  accTitle: Runtime structure of the page
  accDescr: A shell hosts six features that share four services. Self-check gaps link back to path stations, and the live check pre-fills the self-check.
  subgraph SHELL["F0 Shell"]
    direction LR
    ROUTER["router<br/>language, lens, station"]
    I18N["CZ and EN"]
    LENSSEL["lens picker"]
    DISC["L0 to L3 disclosure"]
  end
  subgraph FEAT[Features]
    direction LR
    F1["F1 Path<br/>stations by lens"]
    F2["F2 Principle explorer<br/>every clause"]
    F3["F3 Self-check<br/>gate and maturity"]
    F4["F4 Resource finder<br/>incl. repositories"]
    F5["F5 Live check<br/>two-stage"]
    F6["F6 Freshness<br/>status and as-of"]
  end
  subgraph SVC[Shared services]
    direction LR
    KB["KB index<br/>crate graph by id"]
    CONN["connectors<br/>allowlisted hosts"]
    STATE["state<br/>local storage and link"]
    EXP["export<br/>Markdown and FTR JSON-LD"]
  end
  SHELL --> FEAT
  FEAT --> SVC
  F3 -. gaps .-> F1
  F5 -. pre-fill .-> F3
```

### Two-stage live check

The user enters a DOI, Handle or URL. The page resolves it and reads DataCite, ORCID and ROR, which takes
seconds and pre-fills answers. Only when the user asks for the deep check does the page call the curated
FAIR Champion core tests, a few at a time. A test that times out or errors is shown as "bez výsledku" and never
counts as a failure. Results come grouped by principle, with the coverage stated.

```mermaid
sequenceDiagram
  accTitle: Two-stage live check
  accDescr: A quick deterministic check resolves the identifier and reads DataCite, ORCID and ROR. An opt-in deep check calls curated FAIR Champion tests a few at a time and reports coverage, never counting a service failure as a failed requirement.
  actor U as User
  participant P as Guide page
  participant R as DOI and Handle resolvers
  participant D as DataCite, ORCID, ROR
  participant C as FAIR Champion
  U->>P: enter DOI, Handle or URL
  P->>R: resolve the identifier
  R-->>P: landing page URL
  P->>D: read metadata and identifiers
  D-->>P: licence, creators, relations
  P-->>U: quick check and pre-filled answers
  U->>P: run deep check
  loop curated core tests, three or four at a time
    P->>C: POST test with resource_identifier
    alt verdict returned
      C-->>P: pass, fail or indeterminate
    else timeout or service error
      P->>P: mark as bez výsledku
    end
  end
  P-->>U: results by principle with coverage
```

### Change delivery

Every change arrives as a pull request: text polishing by the team, edits by a maintainer working with the
editing skill, or a scheduled data refresh. Seven check layers run in parallel and feed one summary with
previews, and a code owner approves before merge and deployment. Scheduled health checks for links, statuses
and external services open issues instead of changing anything.

```mermaid
flowchart LR
  accTitle: Change delivery
  accDescr: Team edits, maintainer edits with the editing skill and scheduled refreshes all arrive as pull requests. Seven check layers run in parallel, feed a summary with previews, and a code owner approves before merge and deploy. Scheduled health checks open issues.
  T([Team: text polishing]) --> PR
  M([Maintainer with editing skill]) --> PR
  S([Scheduled data refresh]) --> PR
  PR[Pull request] --> CHK
  subgraph CHK[Checks in parallel]
    direction TB
    a[Structure: RO-Crate and SHACL]
    b[Content: CZ and EN, sources, paradata]
    c[Page: HTML, CSP, size budget]
    d[Accessibility: axe, contrast]
    e[Links]
    f[Diagrams re-render]
    g[Hygiene: REUSE, citation file, skill mirror]
  end
  CHK --> SUM[Summary and previews]
  SUM --> REV{Code-owner review}
  REV -->|approved| DEP[Merge and deploy]
  H([Scheduled health checks]) --> ISS[Issues]
```

### Traceability from source to screen

Published sources get ledger IDs: the report, the NRP conditions, the NRP documentation and published
papers. Advice items and checks cite those IDs, and the principle explorer shows every clause, so condensing
the path loses nothing. Each content change records a paradata action naming the person, the tool and the
sources, and the page shows it at level L3.

```mermaid
flowchart LR
  accTitle: Traceability from source to screen
  accDescr: Published sources receive ledger IDs. Advice items and checks cite them, and the principle explorer shows every clause. Content changes record paradata, which the page shows at disclosure level L3.
  SRC["Published sources<br/>report, NRP conditions,<br/>NRP docs, papers"] --> LED["Clause ledger<br/>A, K, C, DOC, E"]
  LED --> ADV["Advice items<br/>station, lens, level"]
  LED --> CHKS["Checks<br/>D, P, G, S, K, I"]
  LED --> F2X["F2 explorer<br/>every clause"]
  ADV --> ACT["Paradata<br/>agent, instrument, sources"]
  CHKS --> ACT
  ACT --> L3["Shown at L3<br/>Jak tento obsah vznikl"]
```

## Design decisions

1. **Static page, no backend.** It is portable to an eosc.cz page whose embedding rules are unknown, to GitHub
   Pages and to a local file, and nothing needs operating.
   *Alternatives:* a plugin for the eosc.cz CMS (MuniWeb; unknown and editor-dependent); a framework single-page
   app (a heavier build and harder for the team to maintain); a server application (needs an operator).
2. **The knowledge base is an RO-Crate 1.2, and the page is its HTML preview.** The content becomes a FAIR
   digital object itself, harvestable and standards-based, and provenance has a standard home.
   *Alternatives:* plain JSON (not linked data); a Markdown static-site generator (no machine-readable content
   model); a database (needs a backend).
3. **Content authored in TOML, crate generated by a standard-library script.** TOML is readable in
   pull-request diffs for the team's text work, is read by Python's standard library. CI regenerates the crate and compares.
   *Alternatives:* hand-editing the JSON-LD crate (unreadable diffs, easy to break); YAML (needs a third-party
   parser); Markdown with front matter (structured fields such as tiers and prefill mappings become awkward).
4. **The crate is delivered standalone and inlined.** The inlined copy keeps the page working from a file and
   in an iframe; the standalone file serves harvesters.
   *Alternatives:* fetch only (breaks `file://` and some embeddings); inline only (not harvestable).
5. **The backbone is a stage-aware path with four role lenses and levels L0–L3; a principle explorer keeps
   every clause.** People think in their work stage, not in principles. Lenses let one path serve
   researchers, data stewards, repository administrators and communities. The explorer guarantees that
   condensing loses nothing.
   *Alternatives:* principle-first navigation (abstract for researchers); separate tools per role (duplicated
   content); a questionnaire first (no orientation before judgement).
6. **A clause ledger with a published-sources rule.** Every statement cites ledger IDs that point to published
   sources. Unpublished working material is never cited; its facts are traced to the published sources it relies on.
   *Alternatives:* free-form references (not checkable); citing unpublished working material.
7. **Paradata through Process Run Crate actions.** Who produced or verified content, with which tool
   (including AI), and from which sources is recorded per content batch and shown at level L3.
   *Alternatives:* git history only (not visible to readers and not linked to sources); a changelog (too coarse).
8. **The self-check keeps two axes (NRP gate, FAIR maturity) and shows no overall score.** The analysis warns
   that automated scores mainly reflect repository configuration and move a lot with small changes.
   *Alternatives:* one FAIR score or percentage (misleading); a maturity scale only (hides the binary NRP conditions).
9. **Live checks are two-stage, with FAIR Champion opt-in and governed by reliability rules.** The OSTrails CZ
   pilot (<https://doi.org/10.5281/zenodo.21726258>) found many calls without a verdict, a large share of
   indeterminate results and families that fail by construction. A quick deterministic stage gives instant
   value; the deep check reports coverage and never counts a service failure as a failed requirement.
   *Alternatives:* F-UJI (no browser access); always running the full Champion battery (slow, unreliable, heavy
   load); no live checks (loses a concrete, motivating feature).
10. **Sources a browser cannot reach enter as reviewed snapshots.** re3data, Heslář, FER lookups, NMA facets
    and test health refresh through scheduled pull requests.
    *Alternatives:* a proxy backend (contradicts decision 1); waiting for providers to enable CORS (tracked as
    issues, not relied on).
11. **The repository finder combines NKR live data, a re3data snapshot and a curated list; FERs come from the
    FIP Dashboard.** NKR is the national source but has no registered repositories yet; its published schema maps
    onto FAIR principles, which also lets the repository-administrator self-check be pre-filled from an NKR record.
    Standards, vocabularies and other FERs are shown from the dashboard snapshot with their NRP/EOSC CZ
    qualification and a link to the dashboard record.
    *Alternatives:* NKR only (currently empty); re3data only (misses NRP pilot repositories); a FER list maintained
    in the guide (a second copy of facts the dashboard owns).
12. **Diagrams are Mermaid sources pre-rendered to SVG,** following documentation
    visual conventions: approved diagram families, each diagram paired with prose.
    *Alternative:* the Mermaid runtime in the browser (heavy JavaScript, flash of code).
13. **Layered pull-request checks plus code-owner review; scheduled jobs never commit.** Checks make an edit
    safe for the page and the data; humans judge correctness and tone.
    *Alternative:* lint only (does not protect content integrity or accessibility).
14. **Licensing: MIT for code, CC BY 4.0 for content, REUSE layout.** This matches EOSC CZ outputs.
    *Alternatives:* a single licence (wrong fit for code or for content); EUPL-1.2 (considered; MIT chosen).
15. **Planning and later changes are OpenSpec-driven.** The guide was planned as an OpenSpec change. At the first
    release its specs become this repository's capability specs under `openspec/specs/`, and the change is archived
    under `openspec/changes/archive/`. OpenSpec is a pinned development dependency, so later changes to the guide
    are proposed, validated and archived here.
    *Alternatives:* planning outside the repository (future contributors cannot see why the guide is as it is); a
    design document only (no testable requirements).
16. **Visual identity: EOSC CZ, light theme, accessible tints.** Brand teal and pink are kept for accents and
    large text; darker tints carry body text to meet 4.5:1 contrast. The official logo packages are used.
    *Alternative:* raw brand colours for text (fails WCAG AA).
17. **AI tooling: `AGENTS.md` plus one editing skill mirrored for Claude Code.** It is enough for a future
    administrator to edit in line with the decisions.
    *Alternative:* generated configuration trees for many assistants (too much for this repository).
18. **The FIP completeness check is pre-filled from the community's profile in the FIP Dashboard, with a
    published nanopublication as the fallback.** The dashboard holds national FIPs with declarations per principle
    and a status for each (in use, planned, under consideration, to be replaced); it is read from the snapshot and,
    once its API admits the guide's origin, live. FIP Wizard publishes FIPs as nanopublications that the
    nanopublication query service serves to browsers; this adapter covers profiles outside the dashboard and keeps
    the pre-fill working if the dashboard is unavailable, in the pilot and in production. A principle with no
    declaration stays open with a note, because a missing declaration does not prove a gap.
    *Alternatives:* manual answers only (ignores published work); the dashboard only (no fallback); nanopublications
    only (misses the national catalogue).
19. **The guide and the FIP Dashboard are two facets of one service.** The dashboard (the national FER catalogue,
    into which NKR-qualified FERs move, open to resources from anywhere) answers "which resources and profiles";
    the guide answers "what to do and why". They share principle IDs, CZ/EN texts and the FIP vocabulary, link to
    each other's records, and go through the same review round. The dashboard owns FER facts; the guide refers to
    them by dashboard ID.
    *Alternatives:* a link to the dashboard only (users stitch the two together themselves); copying FERs into the
    guide (two owners of one fact).
20. **A testing-phase notice is driven by the release status.** Until EOSC CZ agrees the guide, `content/guide.toml`
    carries the status "testing" and every view shows a notice. The release that records the agreement changes the
    status, which removes the notice.
    *Alternative:* a hard-coded banner (easy to forget when releasing).

## Spikes and findings

### RO-Crate validation (2026-10-08)

rocrate-validator 0.12.2 supports RO-Crate 1.2, Process Run Crate 0.5 and user profiles loaded with
`--extra-profiles-path`. It builds a profile's identifier from `prof:hasToken` and the version that ends the
profile IRI, so the guide's profile in `profile/fair-guide/` is `fair-guide-0.1`. The checks run as three
passes:

- RO-Crate 1.2, with every requirement level;
- Process Run Crate 0.5 with profile inheritance disabled (`-nh`), because the validator declares that profile on
  top of RO-Crate 1.1 and would otherwise require a 1.1 metadata descriptor;
- the guide's profile, also with `-nh`.

Required checks must pass. Recommended findings that remain are accepted:

- the validator does no subclass inference, so it reports `HowToDirection`, `Question` and `DataCatalog` results
  of provenance actions as not being `CreativeWork`, although schema.org defines them as subclasses;
- it expects `actionStatus` as a string, while Process Run Crate examples use the IRI
  `http://schema.org/CompletedActionStatus`, which the crate keeps;
- the guide's own `rdf:Property` terms have no schema.org type.

Two validator findings changed the model: every `SoftwareApplication` needs a `version`, so FAIR Champion tests
are `CreativeWork` entities typed `ftr:Test` through `additionalType`; and in-page action targets are references to
crate entities (`#repositories`, `#check-gate`) rather than plain strings.

### Paradata granularity (2026-10-08)

Process Run Crate 0.5 admits `CreateAction`, `ActivateAction` and `UpdateAction`; an action needs an
`instrument` that is a `SoftwareApplication`, `SoftwareSourceCode` or workflow, and should name an agent, a
result and an end time. The guide records one action per content batch: `create` for new items and `update` for
changed ones. A result pattern with a trailing `*` covers a whole station or ledger section. The AI model and
the assistant runtime are named as instruments; the generator is not, because it transforms content rather than
authoring it. With `--base <ref>`, `check_content.py` requires an action newer than that revision for every item
whose source changed.

### FIP declarations from a nanopublication (2026-10-08)

The fallback source for the FIP pre-fill is the nanopublication query service. A SPARQL query over
`https://query.knowledgepixels.com/repo/full` follows a FIP to its declaration index, from the index to each
declaration nanopublication, and from each declaration to the FIP question it answers and the resource it declares.
The service sends `Access-Control-Allow-Origin: *`, so the page can call it directly; for a published FIP (the
ADVANCE project's profile) it returned 27 declarations in about half a second. Findings that shaped the adapter:

- a FIP is published under three IRI forms, `https://w3id.org/np/<code>#fip`, `https://w3id.org/np/<code>/fip`
  and `http://purl.org/np/<code>#fip` (165, 31 and 39 of the 235 FIPs the service listed), so the query lists all
  three and the export names the one that matched; the page accepts the trusty URI code on its own or inside an
  address;
- 232 of those 235 FIPs have a declaration index; the query found declarations for every FIP in a sample of eight
  once it listed all three forms;
- questions are IRIs of the form `https://w3id.org/fair/fip/terms/FIP-Question-<question>`, where the question is
  the code that `prefill.fip` uses (`F1-D`, `A1.1-MD`, …);
- the relation carries the status: `declares-current-use-of` is "in use", `declares-planned-use-of` is "planned"
  and `declares-planned-replacement-of` is "to be replaced";
- declared resources use `http://purl.org/np/…` IRIs, which purl.org also serves over HTTPS, and a resource can
  carry several labels, so the page links the HTTPS form and lists each resource once.

The query lives in `content/live.toml`, not in the scripts, so it can change with the service without a code
change. The FIP Dashboard API, the primary source, answered only its own development origin in a cross-origin
check on the same day, so the page uses the dashboard snapshot until `browserAccess` is switched on.

### FAIR Champion and the NMA search link (2026-10-08)

FAIR Champion tests are called with `POST <endpoint>/<test>` and the body `{"resource_identifier": …}`, as each
test's OpenAPI description at `https://tests.ostrails.eu/tests/<test>/api` states. The service sends
`Access-Control-Allow-Origin: *`, also on its pre-flight answer, and returns JSON-LD whose `ftr:TestResult` carries
`prov:value` (`pass`, `fail` or `indeterminate`) and `ftr:log`. A probe of the ten curated tests with a Zenodo DOI
and a LINDAT Handle confirmed the pilot's reliability findings: the DOI got HTTP 500 from eight tests within a
second, the Handle got verdicts from nine tests in 0 to 54 seconds, and the author-affiliation test gave no verdict
for either. That test is marked `degraded` in the health snapshot; the others are `available`.

NMA's search page is `https://nma.eosc.cz/datasets/?q=…` (`/search?q=` redirects there). A DOI in quotes finds the
record when NMA holds it and shows an empty result otherwise, while the direct record address
`/datasets/records/doi/<doi>` answers 404 for a dataset NMA does not hold. The guide therefore links the search
with the quoted identifier.

## Decision log

Source: **U** = decision of the maintainer, **S** = proposal from analysis, agreed by the maintainer.

| ID | Date | Decision | Src |
| --- | --- | --- | --- |
| D-01 | 2026-10-07 | Refresh *Analýza FAIR NRP/NDI v1.2* into an interactive, self-explanatory CZ+EN guide for an eosc.cz page. Live demo, then handover to the team for polishing. | U |
| D-02 | 2026-10-07 | Backbone is a **stage-aware lifecycle path**: PLÁN → PRÁCE → REPOZITÁŘ → POPIS → LICENCE A PŘÍSTUP → PUBLIKACE → DOHLEDATELNOST → CITACE A UZNÁNÍ → KONTROLA. A one-question stage entry opens the path; earlier stations are collapsed, not hidden. | U |
| D-03 | 2026-10-07 | **Four role lenses** on the same path: researcher, data steward, repository admin/curator, community/FIP. The path is the most desired feature; data stewards and repository admins are the most common users and translators. | U |
| D-04 | 2026-10-07 | "Rich, but on demand": disclosure levels L0 (what to do now), L1 (how), L2 (why: principles, CTS, CDIF 1.1, NRP rules), L3 (sources, FER IRIs, paradata). | U |
| D-05 | 2026-10-07 | Features: F0 shell · F1 path · F2 principle explorer · F3 self-check per role (incl. NRP onboarding gate) · F4 resource finder · F5 live check · F6 freshness. Discussed one feature at a time. | U |
| D-06 | 2026-10-07 | Stack: static HTML + CSS + light, safe vanilla JS. No backend, no build step for the page. Portable to an iframe, an inline block or a standalone page (target page unknown). | U |
| D-07 | 2026-10-07 | Knowledge base is an **RO-Crate 1.2** (`ro-crate-metadata.json`); `index.html` doubles as `ro-crate-preview.html`. **Paradata** follows Process Run Crate (CreateAction: agent, instrument, object, result, endTime). | U+S |
| D-08 | 2026-10-07 | Reuse standard IRIs: FAIR principles `w3id.org/fair/principles/terms/*`, published FER nanopub IRIs, FAIRsharing DOIs, FIP ontology classes, schema.org / DCAT / SKOS / dcterms. | U |
| D-09 | 2026-10-07 | Live calls only on user action, with graceful fallback. OK: DataCite REST (metadata, citation), FAIR Champion, nanopub query, Upptime JSON. Not usable from a browser: FAIRsharing API (login), Heslář API (no CORS), F-UJI (no CORS). | S |
| D-10 | 2026-10-07 | No built-in NRP FAIR check. Use external tools, with **FAIR Champion preferred**. Present scores as feedback on repository setup, not as a judgement of the author (report §5.2.1). | U |
| D-11 | 2026-10-07 | Tone is advisory and matches EOSC CZ materials; no enforcement wording beyond the actual NRP conditions (v3.4). | U |
| D-12 | 2026-10-07 | Sensitive data gets a short callout ("FAIR ≠ otevřená") with a combination of pointers; the user chooses the target. | U |
| D-13 | 2026-10-07 | Station "CITACE A UZNÁNÍ" leads with citation practice. RIV result type T is a factual note, never hype. Includes a citation helper from a PID. | U |
| D-14 | 2026-10-07 | PIDs: DOI is the recommended, most instructive option, **not the only valid one**. Handle, ARK, URN:NBN and others are acceptable if persistent, resolvable and managed. | U |
| D-15 | 2026-10-07 | CCMM wording: NMA works with **1.1.0**; "podpora 2.0.0 se připravuje (2027)" (likely a v2→v1 XSLT; meeting info, not guaranteed). Forward-looking advice may reference 2.0.0. | U |
| D-16 | 2026-10-07 | FIP/FER: no separate national FIP Wizard. The FER catalogue is a closed pilot, so keep a **placeholder** (user will supply a link). NKR will host approved qualified FERs; each repository is described by its FIP. | U |
| D-17 | 2026-10-07 | **No licence-selector placeholder**; the DSW plugin in dmp.eosc.cz is the deliverable. | U |
| D-18 | 2026-10-07 | DMP is a cornerstone: dmp.eosc.cz with funder templates (GA ČR, TA ČR, AZV ČR, MŠMT, Horizon Europe, Science Europe) and the CCMM export template. | U+S |
| D-19 | 2026-10-07 | AI transparency in a footer, an "O průvodci" page and per-item paradata. "AI ve FAIRifikaci" is an overlay per station plus an overview page linking CERIT AIaaS. Guardrails: keep unpublished data on-premise, verify every identifier, declare AI use. | U |
| D-20 | 2026-10-07 | Accessibility: EU Web Accessibility Directive (EN 301 549 / WCAG 2.1 AA; CZ zákon 99/2019 Sb.); target **WCAG 2.2 AA**; publish an accessibility statement. | U |
| D-21 | 2026-10-07 | UX is critical. Anti-dropout patterns: one-question entry, next best action, one concrete action per station, time estimates, glossary popovers, an escape hatch, remembered progress. Test with EOSC CZ personas. | U |
| D-22 | 2026-10-07 | Visual identity: brand teal #008691 and pink #EB5D81 only for accents and large text; text tints #00737D and #C2264F (both ≥ 5.6:1 on white). Muni font only inside eosc.cz pages; Arial/Helvetica fallback. | S |
| D-23 | 2026-10-07 | Diagrams in **Mermaid**, and they must look good. Follow documentation visual conventions: approved families only, every diagram paired with prose (which doubles as the text alternative). | U |
| D-24 | 2026-10-07 | Paradata agents: David Novák (ORCID 0000-0001-6592-6291) as implementing author, others as contributors; reviewed later. Text polishing goes to the team. | U |
| D-25 | 2026-10-07 | Repository `github.com/motyc/eosc-fair-guide`: private now, public later. Best-practice contents (README, licences, CITATION.cff, CONTRIBUTING, CHANGELOG…). Minimal AI tooling plus **one dedicated editing skill**; keep it light. | U |
| D-26 | 2026-10-07 | Not hosted on third-party AI artifact hosting (EOSC CZ branding). Preview locally until the repository is public, then use GitHub Pages or the target page. | S |
| D-27 | 2026-10-07 | Glossary source: **heslar.openscience.cz** (NTK), snapshotted at authoring time and linked back (licence to check). PID centre: **identifikatory.cz**. | U+S |
| D-28 | 2026-10-07 | Draft checklists and handbooks for repository administrators are supportive input only, not decisions. JSON-LD (schema.org) landing pages are desirable. | U |
| D-29 | 2026-10-08 | **CI must validate PR contents** so an edit is safe to accept once checks pass. Layers: structure, content contract, page integrity, accessibility, links, diagrams, repo hygiene, review aids. Hardened workflows. | U |
| D-30 | 2026-10-08 | Licences: **MIT** (code) + **CC BY 4.0** (content), REUSE layout. | U |
| D-31 | 2026-10-08 | README pair: Czech `README.md` and English operational `README_en.md`. | U |
| D-32 | 2026-10-08 | Light theme only for v1. | U |
| D-33 | 2026-10-08 | Sensitive-data callout uses **all five pointers** (data steward/DPO, Etické sedmero, Sensitive Cloud, sensitive-data AAI architecture, EOSC CZ WG), ordered as steps and filtered by lens, so it reads easily. | U |
| D-34 | 2026-10-08 | Repository discovery: **NKR connector** (Cordra REST at repo.cz, CORS ok, Repository schema published, no repositories registered yet) + **re3data** snapshot (no CORS; 14 CZ entries via `api/beta/repositories?countries[]=CZE`) + a curated layer (MBDB, datarepo…). Deduplicate via `relatedRegistry` and URL. | U+S |
| D-35 | 2026-10-08 | Branding from <https://www.eosc.cz/o-nas/sablony-eosc-cz> (logo zips, EU+MŠMT logolink; no design manual). Acknowledgement text from <https://www.eosc.cz/o-nas/acknowledgement> in the footer / about page. | U+S |
| D-36 | 2026-10-08 | Non-CORS sources (re3data, Heslář, FER lookups) and link health are refreshed by **scheduled CI jobs that open a PR** for human review, never by silently committing. | S |
| D-37 | 2026-10-08 | NKR Repository fields map onto FAIR principles, so the repository-admin lens can **pre-fill a self-check from the repository's NKR record** and show what is missing in that record. | S |
| D-38 | 2026-10-08 | The guide is an official **NRP KA 5.1** output, so the mandatory NRP acknowledgement (CZ/EN, CZ.02.01.01/00/23_014/0008787) goes in the footer and the "O průvodci" page. | U |
| D-39 | 2026-10-08 | Inventory method: a clause ledger (`content/ledger.toml`). The principle explorer (F2) is the lossless home for every report clause; path stations cite clause IDs; L2 is generated from the ledger. Report chapter IDs use a `K` prefix so they cannot be mistaken for principle names. | S |
| D-40 | 2026-10-08 | **Published sources only.** Unpublished working material is never cited or referenced; every fact taken from it is traced to the published source it relies on (ledger section `E.*`). | U |
| D-41 | 2026-10-08 | Outstanding open questions become **issues in this repository**, filed as one of the last steps, so they can be resolved there. | U |
| D-42 | 2026-10-08 | The AI warning is made helpful through a shared "Ověřte identifikátory" callout plus a light on-demand helper. The helper resolves ORCID, ROR, DOI and Handle in the browser and shows the name or title. Kept light; drop it if it grows. | U+S |
| D-43 | 2026-10-08 | NMA: the public REST API has no CORS, so "is my dataset in NMA?" is a pre-filled deep link into NMA search. The station explains the "Získat odkaz pro RIV" flow and states that **the RIV link never replaces the PID** (NRP docs). Anyone can create a manual NMA record. | U+S |
| D-44 | 2026-10-08 | The final text polishing is done by the team **via PRs on the live page**, after everything else is finished. | U |
| D-45 | 2026-10-08 | Live checks are **two-stage**. A deterministic quick check (DataCite, doi.org / hdl.handle.net, ORCID, ROR) comes first; FAIR Champion is an opt-in deep check limited to a curated core set, with gentle load, four outcome states and coverage always shown. A service failure never counts as a failed requirement. Grounded in the OSTrails CZ pilot (E.OSTRAILS-CZ). | U+S |
| D-46 | 2026-10-08 | F3 design: two axes (Brána NRP × Zralost FAIR), no overall score, gaps route back into path stations; pre-fill from NKR (repositories) and DataCite (datasets) with visible source chips; export as Markdown, print and an FTR `TestResultSet` in a small RO-Crate. | S |
| D-47 | 2026-10-08 | Gate profile (a), core NRP systems: G09 (security monitoring) and G10 (central logging) show as **„zajišťuje NRP“**. Confirmed by the user; the NRP repositories page states that NRP provides storage, repository software and the operating environment. | U |
| D-48 | 2026-10-08 | An optional **institution check** (data policy, DMP support, storage, OS III strategy) is included if it fits the scope; it is lower priority than the four lens checks. | U |
| D-49 | 2026-10-08 | **FIP pre-fill is in the first release:** the FIP completeness check (K) reads the community's published FIP nanopublication through the nanopub query service. Declared FERs pre-fill "ano"; questions with no declaration stay open with a note. | U |
| D-50 | 2026-10-08 | The repository is renamed to `motyc/eosc-fair-guide` so its name suits reuse; the vocabulary and profile IRIs follow the new name. | U |
| D-51 | 2026-10-08 | The FER catalogue is the **FIP Dashboard** (<https://fip-dashboard.dmp.eosc.cz>, API <https://fip-dashboard.dmp.eosc.cz/docs>). It will become the official national FER catalogue, into which NKR-qualified FERs move; it accepts resources from anywhere and marks some as NRP/EOSC CZ qualified. It goes through the same review round as the guide. | U |
| D-52 | 2026-10-08 | rocrate-validator 0.12.2 validates RO-Crate 1.2, Process Run Crate 0.5 (with inheritance disabled) and the guide's own profile; Process Run Crate admits `UpdateAction`, and paradata are recorded per content batch (see *Spikes and findings*). | S |
| D-53 | 2026-10-08 | The guide and the dashboard are **two facets of one service**; the dashboard owns FER facts and the guide links to its records with their qualification. Dashboard data (sample, v0.1.0) enter as a reviewed snapshot with the dashboard's own disclaimer shown while present; the API is used live once it admits the guide's origin. FIP pre-fill: dashboard profile first, published **nanopublication as the fallback** in the pilot and in production. | U+S |
| D-54 | 2026-10-08 | A visible **testing-phase notice** stays on every view until the guide is finished and agreed by EOSC CZ; it is driven by the release status in the content. | U |
| D-55 | 2026-10-08 | At the first release the OpenSpec change **moves into this repository** (specs to `openspec/specs/`, change to the archive); OpenSpec is a pinned development dependency, so later development is OpenSpec-driven. Nothing in this repository exposes local machine details or the planning environment's internals. | U |
| D-56 | 2026-10-08 | Self-check pre-fill uses **positive evidence only**: a field, declaration or resolution that is present answers yes (or partly when it proves the item only in part, `prefillLevel`); absence leaves the item open with a note, because a record that omits something does not prove it is missing. A pre-filled value never replaces an answer the user gave, each pre-fill shows its source and date, a changed answer stays marked, and choosing another dataset, repository or profile discards the previous one's evidence. The FIP nanopublication query is recorded in *Spikes and findings*. | S |
| D-57 | 2026-10-08 | Results export as Markdown, print and an FTR `TestResultSet` in a small RO-Crate (yes is `pass`, no is `fail`, partly and don't know are `indeterminate`; not applicable and items NRP provides are left out). The export is a valid RO-Crate 1.2; its licence is declared as not specified, because the person who saves the result decides on reuse. Exports and shared links name the published page (`pageUrl`), never a local file. A shared link carries only the mode, the profile and the answers, opens as a preview, and replaces the user's own answers only on request. "Don't know" names whom to ask and, where an item has one, a lookup link. | S |
| D-58 | 2026-10-08 | Live connectors: ORCID and ROR names, resolver titles, FAIR Champion tests (verdict and log; any failure to get a verdict is "no result") and the DMP.eosc.cz status page. The NMA deep link is the search page with the quoted identifier. Spikes in *Spikes and findings*. | S |
