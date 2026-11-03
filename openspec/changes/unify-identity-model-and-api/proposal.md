# Proposal

## Why

The Guide's static API does not work as an API. Its OpenAPI description lists 1,521 literal paths, only two of them
templated (published `1.0.0-alpha.5`, 990 KB). A list returns only names, so no question can be answered without
fetching every record. The 272 advice items, the Guide's main content, have no address. The cause is in the data
model behind it:

- Lists are named by role (`principles`, `sources`) and records by a kind/type code (`pr/F1`, `res/pub/...`). One
  code family holds several collections, so no path template can name one schema.
- One real-world thing is often several nodes. A registry record and the curated entry are peers joined by `sameAs`
  (17 pairs), or are not joined at all. Examples: `#org-knav` and `#fd-org-knav`; two addresses for the CESNET
  ownCloud service. Organisations sit in five entity families.
- An entity carries up to four identity forms: a fragment `@id` whose prefix encodes its type, `schema:identifier`,
  `dcterms:identifier` and `termCode`. On 925 entities the `name` is the identifier itself. Some IDs end in a
  collision counter (`#fd-org-nrp-2`).
- The crate and the API are two models. The API renames properties, adds the FTR types and creates the 214 manual
  tests, none of which exist in the crate.
- Controlled vocabularies are modelled three ways, and statuses seven ways (strings and concepts). 71 check questions
  repeat a ledger clause word for word, each written out twice in the sources.

The Guide's own term and profile IRIs name a hosting address (`content/guide.toml:26`), and record IRIs depend on
where the crate was read. The first official release fixes identifiers for good
(*The first release establishes the route baseline*). This is the last point at which identity, model and API can
change together without a deprecation path. The change absorbs
[dsw-nrp/eosc-fair-guide#136](https://github.com/dsw-nrp/eosc-fair-guide/issues/136) in full, including the w3id
submission.

## What Changes

- **BREAKING. Persistent identity.**
  - The namespace becomes `https://w3id.org/eosc-cz/fair-guide/`, registered with w3id and maintained by `motyc`
    and `MarekSuchanek`. It names the Guide's terms (`terms#`), its profile (`profile/<version>`) and its records
    (`id/<address>`).
  - An address is `<kind>/<id>`, with a plural English word as the kind (`resources/dmp-eosc`, `stations/licence`).
    A scope segment appears only where it is part of the identity (`tests/f-uji/<id>`, `lifecycles/rdmkit/plan`).
  - Classifications (resource type, repository kind, research domain) move out of addresses into properties.
  - One identity projection serves IRIs, API paths, page routes, prose references, the page's data keys and exports.
    Collision counters disappear.
- **One node per real-world thing.**
  - Registry records (KNAV, FIP Dashboard, re3data, NKR) become catalogue records about one thing. They keep their
    source's own wording, licence and retrieval date.
  - The duplicate check attaches every record to exactly one thing.
- **One model.**
  - Controlled vocabularies are modelled once.
  - Statuses become terms rather than strings.
  - Advice has a class of its own.
  - FTR benchmarks, metrics and manual tests become part of the graph.
  - Pre-fill mappings become typed statements.
  - Names that only repeat an identifier are dropped.
  - A question that repeats its clause takes the clause's text instead of copying it (71 questions).
- **BREAKING. API v1** under `/api/v1/`:
  - `<kind>.json` lists whose entries carry the fields a client filters on;
  - `<kind>/<id>.json` records, with vocabularies published once and referenced from records;
  - advice as its own collection;
  - typed schemas and a templated OpenAPI description;
  - the health snapshot under its own tag and path.
- **Interoperability by identity.** The requirement to follow the FIP Dashboard's path names is replaced. Records name
  their Dashboard counterparts in `sameAs`, and the API documentation maps Guide kinds to Dashboard collections.
- **Graph access.**
  - An N-Triples distribution that needs no remote context.
  - A versioned query contract: the RO-Crate profile and its SHACL shapes, profile `0.2`.
  - Documented SPARQL recipes, each run in CI as a contract test.
- **Page.**
  - Catalogue routes use addresses (`#/<lang>/catalogue/resources/dmp-eosc`).
  - A permanent route, `#/id/<address>`, opens the catalogue entry an IRI names.
  - Every record shows its own persistent IRI as a labelled chip.
  - Prose uses one reference syntax.
- **Saved results.** Format revision 4 names persistent test IRIs. Revisions 1–3 still load, and their
  `api/tests/<question>.json` references keep resolving.
- **Contract stability.** Nothing published is permanent before Guide `1.0.0`. A deprecation rule takes effect from
  `1.0.0`. The follow-up issue
  [dsw-nrp/eosc-fair-guide#171](https://github.com/dsw-nrp/eosc-fair-guide/issues/171), in the `v1.0.0` milestone,
  moves the profile, API and contract versions to their production values.

## Capabilities

### New Capabilities

None. The changed behaviour belongs to the existing capabilities below.

### Modified Capabilities

- `fair-guide/guide-knowledge-base`:
  - the static API, addressing and FTR publication;
  - the one-entry rule, prose references and catalogue addresses;
  - the namespace and the route baseline;
  - new requirements for IRI resolution, registry records, vocabulary and status modelling, the graph distribution
    and recipes, and derived question text.
- `fair-guide/guide-experience`: the machine-readable page, signposting, identifier routing, identifier chips and
  catalogue routes.
- `fair-guide/guide-delivery`: health snapshot publication, namespace alignment between channels, and monitoring and
  maintaining the w3id redirect.
- `fair-guide/guide-self-check`: result format revision 4 and its persistent test references.

## Impact

- **Build:** `scripts/build_crate.py`, `scripts/catalogue_identity.py` and `scripts/build_api.py`, plus a new RDF
  writer.
- **Checks:** `scripts/check_content.py`, `scripts/check_duplicates.py`, `scripts/check_health.py` and
  `scripts/refresh_snapshots.py`.
- **Release:** release assembly and packaging stamps (`scripts/assemble_pages.py`, `scripts/package_site.py`).
- **Page:** the scripts in `assets/js/` (213 fragment-prefix literals in 10 files) and the API documentation page in
  `api/`.
- **Content:**
  - every content file with prose references;
  - `guideRoute` in the snapshots;
  - `content/identifiers.toml`;
  - provenance result IDs;
  - the 71 merged question statements in `content/checks/`.
- **Tests:** Python, page and API tests, and fixtures.
- **Documentation and tooling:**
  - `docs/content-model.md`, `docs/design.md`, `docs/deployment.md` and `docs/ci-reference.md`;
  - the refresh and duplicate runbooks, and a new w3id runbook;
  - the native content rule in `.agents/guide/`, regenerated;
  - `docker/nginx.conf`;
  - the health-watch workflow.
- **External:** a pull request to `perma-id/w3id.org` adding `ids/eosc-cz/fair-guide/`. EOSC CZ must agree to the
  `eosc-cz` folder first. The w3id maintainers decide when it merges.
- **Out of scope:**
  - the Guide's hosting address ([dsw-nrp/eosc-fair-guide#32](https://github.com/dsw-nrp/eosc-fair-guide/issues/32));
  - a Dataspecer view of the vocabulary
    ([dsw-nrp/eosc-fair-guide#33](https://github.com/dsw-nrp/eosc-fair-guide/issues/33));
  - a query service, precomputed query views, SQL or tabular distributions, and an in-browser query console;
  - content wording beyond the 71 merged question statements.
- **Validation:**
  - `npm run openspec:validate` and `python scripts/check_all.py`;
  - the new RDF, recipe and template-coverage checks;
  - the w3id probe once the redirect is live;
  - inspection of the catalogue, records and machines page in both languages, at phone width and in print.
