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
  `dcterms:identifier` and `termCode`. On 930 entities the `name` is the identifier itself. Some IDs end in a
  collision counter (`#fd-org-nrp-2`).
- The crate and the API are two models. The API renames properties, adds the FTR types and creates the 214 manual
  tests, none of which exist in the crate.
- Controlled vocabularies are modelled three ways, and statuses seven ways (strings and concepts). 55 check questions
  copy a ledger clause word for word, so the text is written out twice in the sources. The 16 CoreTrustSeal
  questions already take theirs from the clause.
- The graph says things its own data contradicts. The vocabulary the Guide publishes declares domains and ranges
  that make a reasoner, the RO-Crate validator among them, type membership roles as organisations and registry
  records as repositories. Classes such as the FTR test type are written as strings, a class query counts registry
  records as organisations, and some facts are stated in both directions.

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
  - Registry records (KNAV, FIP Dashboard, NKR, re3data, FAIRsharing, DataCite) become catalogue records about one
    thing. They keep their source's own wording, licence and retrieval date, and the thing rests on them.
  - A name in content, such as a publisher or an operator, resolves to the one thing the Guide describes under that
    name. A registry's organisation record attaches to a thing only by a reviewed key, never by its name.
  - Registries are resources; the catalogue's repository family holds repositories only.
  - Registry records are typed once, as catalogue records and creative works, never as the thing they describe.
  - The EOSC CZ Node is a platform the Guide lists as a resource, as the EOSC Federation Handbook 2.0 defines a Node:
    a collection of services and data sources that an organisation operates. The services and repositories it
    onboards are DCAT qualified relations carrying their role, milestone, date checked and source.
  - The duplicate check attaches every record to exactly one thing.
- **One model.**
  - Controlled vocabularies are modelled once, and every controlled value is a term, clause kinds and mapping
    coverage included.
  - Statuses become terms rather than strings.
  - Every kind is selected by its class or its term set; no class is written as a string.
  - Advice has a class of its own.
  - FTR benchmarks and metrics become part of the graph, and the tests that are services are FTR tests. A reader's
    self-check answer is a DQV quality measurement of its question.
  - Pre-fill mappings become typed statements.
  - The vocabulary's domains and ranges hold for the published graph, so a reasoner adds no class that a thing does
    not have.
  - Each fact is stated once, and schema.org properties are used within their domains and ranges.
  - Names that only repeat an identifier are dropped.
  - A question that repeats its clause takes the clause's text instead of copying it (55 questions).
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
  - Catalogue routes use addresses and keep the reader's lens (`#/<lang>/<lens>/catalogue/resources/dmp-eosc`).
  - Every record IRI opens a static landing page, `id/<address>.html`, readable without JavaScript and signposted,
    with a section for each part. Its link into the Guide, `#/id/<address>`, opens the entry in the reader's saved
    language and lens.
  - The production sitemap lists the landing pages, so search engines and harvesters reach every record.
  - Every catalogue entry shows its own persistent IRI among its identifiers. Identifier chips carry no labels, since
    each identifier is shown in full.
  - An entry credits every catalogue that supplied it.
  - Prose, and every field that can name records of several kinds, names a record by its address.
  - Every page section carries a reviewed `id` as its fragment, so reordering a page moves no IRI.
  - The machines page follows a reader's task: what it offers, what the reader is looking for, a worked example, how
    the Guide applies its own advice, and then the endpoints.
- **Saved results.** Format revision 4 records a reader's answer as a measurement of its question's persistent IRI,
  and automated evidence by its test's persistent IRI. Revisions 1–3 still load, and their
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
  - the EOSC CZ Node and the entries it onboards;
  - new requirements for IRI resolution, registry records, vocabulary and status modelling, the graph distribution
    and recipes, and derived question text;
  - new requirements that every kind is selected by its class, that the vocabulary's declarations hold for the
    graph, that each relation is stated once and that schema.org properties stay within their domains.
- `fair-guide/guide-experience`: the machine-readable page, signposting, identifier routing, identifier chips, the
  credited sources, the repository family and its facets, catalogue routes and record landing pages.
- `fair-guide/guide-delivery`: health snapshot publication, the production sitemap, namespace alignment between
  channels, and monitoring and maintaining the w3id redirect.
- `fair-guide/guide-self-check`: result format revision 4, which records answers as measurements of persistent
  question IRIs and automated evidence by persistent test IRIs.

## Impact

- **Build:** `scripts/build_crate.py`, `scripts/catalogue_identity.py`, `scripts/build_api.py` and
  `scripts/nkr_contract.py` (NKR's status mapping), plus a new RDF writer and a writer for the record landing
  pages and `404.html`. The sitemap in `build_crate.py` lists the landing pages.
- **Checks:** `scripts/check_content.py`, `scripts/check_duplicates.py`, `scripts/check_health.py`,
  `scripts/refresh_snapshots.py`, and `scripts/check_docs.py`, which refuses a citation of any change.
- **Release:** release assembly, image preparation and packaging stamps (`scripts/assemble_pages.py`,
  `scripts/image_release.py`, `scripts/package_site.py`), including reusable current and documented predecessor
  artifacts.
- **Page:** the scripts in `assets/js/` (213 fragment-prefix literals in 10 files), including the self-check's
  evidence export (`selfcheck.js`, `providers.js`) and the EOSC CZ Node badge and facet, and the API documentation
  page in `api/`.
- **Profile:** the shapes in `profile/fair-guide/must/`, which select every kind by its class.
- **Content:**
  - every content file with prose references;
  - `guideRoute` in the snapshots;
  - `content/identifiers.toml`;
  - provenance results and objects, model association targets and the worked example's steps;
  - agent names that need an address, and reviewed FIP Dashboard handles on curated rows;
  - the 55 merged question statements in `content/checks/`;
  - `content/pages.toml`: an `id` for every page section, and the machines page's order;
  - `content/eosc-node.toml` and the Node's entry, which moves to `resources/eosc-cz-node`, and
    `content/sources.toml`, which gains the EOSC Federation Handbook 2.0;
  - `content/guide.toml`: term sets for clause kinds, mapping bases, evaluator mapping coverage and model kinds;
  - `content/resources.toml`: the classification of the NRP Data Catch-all Repository, which says registry.
- **Tests:** Python, page and API tests, and fixtures.
- **Documentation and tooling:**
  - `docs/content-model.md`, `docs/design.md`, `docs/deployment.md` and `docs/ci-reference.md`;
  - the refresh and duplicate runbooks, and a new w3id runbook;
  - the native content rule in `.agents/guide/`, regenerated;
  - `docker/nginx.conf`;
  - the health-watch workflow;
  - comments that cite earlier changes, rewritten in their own words, in `scripts/`, `tests/`, `assets/`,
    `content/`, the `.github` workflows and scripts, and `.github/repository.toml`.
- **External:** a pull request to `perma-id/w3id.org` adding `ids/eosc-cz/fair-guide/`. EOSC CZ must agree to the
  `eosc-cz` folder first. The w3id maintainers decide when it merges.
- **Out of scope:**
  - the Guide's hosting address ([dsw-nrp/eosc-fair-guide#32](https://github.com/dsw-nrp/eosc-fair-guide/issues/32));
  - a Dataspecer view of the vocabulary
    ([dsw-nrp/eosc-fair-guide#33](https://github.com/dsw-nrp/eosc-fair-guide/issues/33));
  - a query service, precomputed query views, SQL or tabular distributions, and an in-browser query console;
  - content wording beyond the 55 merged question statements.
- **Delivery:** one pull request,
  [dsw-nrp/eosc-fair-guide#172](https://github.com/dsw-nrp/eosc-fair-guide/pull/172), carries the whole change. It
  merges when `python scripts/check_all.py` passes in full on it.
- **Validation:**
  - `npm run openspec:validate` and `python scripts/check_all.py`;
  - the new RDF, recipe and template-coverage checks;
  - the new checks that every kind has a selector, that the vocabulary's declarations hold, that no relation is
    stated both ways, that schema.org properties stay within their domains, and that every shape refuses a real node
    missing what it requires;
  - independent coverage from every issued address to its API record and landing page, plus generated-HTML rejection;
  - current and documented predecessor artifact assembly and image retries, and interrupted migration retries;
  - recursive fragment anchors and nested-404 stylesheet resolution;
  - byte-identical output after registry-index caching and schema-option deduplication;
  - the w3id probe once the redirect is live;
  - inspection of the catalogue, records, landing pages and machines page in both languages, at phone width and in
    print.
