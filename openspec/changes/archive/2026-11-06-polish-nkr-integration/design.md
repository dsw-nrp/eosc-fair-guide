# Design

## Context

See `proposal.md` for the harvest that exposed these defects. The behaviour this change requires is in `specs/fair-guide/guide-experience/spec.md` and `specs/fair-guide/guide-knowledge-base/spec.md`.

Before this change:

- **One merge key.** `build_repositories` (`scripts/build_crate.py`) merges each repository record under a single key from `repository_key`: `re3data:<id>` when the record names one, otherwise `url:<address>`. Curated entries come first, and the first non-empty value of each property wins. A curated entry's `nkr` handle becomes a `sameAs` link but is not a merge key.
- **NKR records as repositories.** `nkr_repositories` turns NKR snapshot records into repository records and looks for a re3data ID in `relatedRegistry`, which the `Repository` record no longer carries.
- **Self-check pre-fill.** `nkr_config` feeds the self-check with each record's `fields`. `mainContact` is never present, because the refresh stores only `mainContactPresent`.
- **The refresh.** `refresh_snapshots.nkr` requests a fixed identity list plus every top-level `prefill.nkr` path. It does not check these against NKR's schema, and it drops `status` and `additionalNames`.
- **Identity.** `catalogue_identity.identity_seed` seeds a new ID from `url`, which for NKR is the record page on `repo.cz`. `preserve_snapshot` routes every new NKR record to `repo`.
- **Duplicate check.** `check_duplicates.entries` reads snapshot `resource`, `repository`, `tool`, `organization` and `fip` rows, but not `record` rows.
- **Contracts.** The profile shape `fair-guide:Repository` (`profile/fair-guide/must/1_content.ttl`) and the API schema (`build_api.py`, `"Repository": ["name", "url"]`) both require an address.

The five public NKR records as of 2026-11-01 are the reference fixture. They should give three automatic address joins (ArchaeoVault, the Data Catch-all Repository and MBDB), one reviewed join (CzBIRD to `czech-bioimaging`) and one new entry (the herbarium repository).

## Goals / Non-Goals

**Goals:**

- Joining stays deterministic and explainable: every join can be traced to a re3data ID, an NKR handle or an exact normalised address.
- NKR's precedence is per property and visible as provenance; no source value is lost from the record evidence.
- The refresh fails before writing when NKR sends something the Guide cannot represent, never after.

**Non-Goals:**

- Joining by address for sources other than NKR. re3data, FIP Dashboard and KNAV joins keep their reviewed links.
- Choosing between NKR and re3data facts other than those NKR states.
- Any change to how the self-check interprets a field it can read.

## Decisions

### D1. Identity is a union of keys; NKR addresses join only NKR records

**Decision.** Merging keeps the existing keys for every source: the re3data ID, otherwise the address. It adds the NKR handle as a key on every record that names one, curated entries included. An NKR record additionally looks up the normalised address (`bare_url`) of its `mainUrl` among the addresses of all entries built so far. Records that share any key fall into one component. An NKR record whose keys reach two components joins neither, and the content check reports it.

FIP Dashboard-only repositories enter that lookup as separate components before NKR is processed. An NKR join
retains the existing FIP entity's local identity, functions and verification evidence, and credits both source
records. FIP and curated entries do not join by address alone; an NKR record reaching both is ambiguous.

The address lookup indexes both the source record's address and its reviewed annotation address. The duplicate
check uses the same addresses. Two NKR records reaching one component are ambiguous too; neither record may
supply a mixture of identity and authoritative facts.

The reviewed Repository schema carries no `relatedRegistry`, so NKR records join only by their reviewed handle
or exact address. The dormant incoming re3data relationship parser is removed; existing curated/re3data joins
provide catalogue identity. An NKR row never receives another source's `[[record]]` annotation overlay,
and its original name and `mainUrl` supply its precedence values and match keys.

**Alternatives considered.**

- *Key every source by address.* Rejected: it would change re3data and FIP Dashboard joins that review currently governs. The spec limits the automatic address join to NKR (decision 1 of the exploration).
- *Prefer one key per record.* Rejected: a curated entry keyed by re3data and an NKR record keyed by address would never meet, which is exactly how the Data Catch-all Repository and ArchaeoVault were duplicated.

### D2. NKR wins per property, and only with a value

**Decision.** After the records are merged, a final pass applies NKR's values for the properties NKR owns: name, kind, status, the status date (`statusAsOf`), keywords and address. It applies them only where the NKR value is non-empty. Every other property keeps the existing first-value-wins rule.

The NKR name replaces the curated or registry name on the catalogue entity, including a resource's entity such as `datarepo`. Authored sentences keep their own link phrases. The curated abbreviation still applies.

The page does not append an abbreviation already present as a complete token anywhere in the name, including
a suffix after a space, hyphen or dash. The match is case-sensitive and respects Unicode letters and numbers.
This rule lives in the one place that composes the displayed name.

**Alternatives considered.**

- *Order NKR first in the source list.* Rejected: NKR would then also own the entity ID and every first-filled property, including a curated description and operator.
- *Override with empty values as well.* Rejected by the maintainer: a known working instance address stays.

### D3. NKR statuses are mapped at build time, dated by retrieval

**Decision.** The snapshot keeps NKR's own `status` string, so the snapshot remains the source's text. The build maps it to the five-level vocabulary as the spec gives. Its as-of date is the snapshot's `retrieved` date, because that is when the status was observed. NKR's `releaseDate` is ignored: every record carries the placeholder `2028-01-01`.

A decommissioned record contributes no entity and does not join one. The build reports it, together with any entry its keys reach, in the health inventory's maintainer findings.

The graph retains the build's repository key-to-entity lookup as runtime metadata, including raw and annotated
addresses. Retirement reporting uses that lookup and the same NKR match-key derivation as the build; it reports
all reached entries without merging the retired record or changing an entry's facts. The lookup is not published.

**Alternatives considered.**

- *Map in the refresh.* Rejected: it would rewrite the source's value in the snapshot.
- *Use the record's `metadata.modifiedOn` as the date.* Rejected: it records editing, not verification, and the snapshot does not keep it.

### D4. Deposit availability is derived, not a new authored field

**Decision.** The build marks a repository entity as not accepting data in two cases: its five-level status is planned, in development or prospective, or its NKR status is `pilot - not accepting data`. This is a Guide vocabulary property, `acceptsDeposits` set to false, which is omitted when unknown.

The data-deposit facet value is not indexed for such an entity, so the data-repository chooser, which is that facet, leaves it out. The card still shows the entry's functions.

Only the final entity loop derives `acceptsDeposits`, after applying NKR's status overrides. One shared set
owns the Guide statuses that prohibit deposit; the NKR pilot refusal remains source record data until that
final derivation. Curated and NKR status cases both exercise this rule.

**Alternatives considered.**

- *Remove `deposit-data` from the entry's functions.* Rejected: the function describes what the repository is for, and it would return silently when the status changes.
- *Ask readers to add a status filter.* Rejected under the reader-first principle.

### D5. A repository that is not public yet has no address and says so

**Decision.** An NKR record that joins nothing and has an empty address becomes an entity without `url`, carrying the NKR `sameAs` link and its status. This is allowed only when its mapped status is planned or in development. Otherwise the refresh rejects the snapshot (see D6).

The catalogue card shows a bilingual line stating that the repository has no public address yet. Its title opens the entry, as for any entry, and the NKR record is its external link.

- **Profile.** The `fair-guide:Repository` link property becomes an `sh:or` of two alternatives: an HTTPS `schema:url`, or a status in {planned, in development} together with a `sameAs` under `https://repo.cz/objects/`.
- **API.** The `Repository` schema drops `url` from `required` and adds an OpenAPI 3.1 `if`/`then`: unless the status is one of those two, `url` is required. The description states the exception.

**Alternatives considered.**

- *Omit such records (option a).* Rejected by the maintainer.
- *Use the NKR record page as the `url`.* Rejected: `url` would then misname the repository's address, the same confusion that produced the opaque IDs.

### D6. The refresh reads NKR's schema and validates before writing

**Decision.** The NKR refresh first fetches `https://repo.cz/schemas/Repository` (fixture `nkr-schema.json`). The kept fields are the identity fields (`repositoryName`, `additionalNames`, `mainUrl`, `type`, `status`, `keywordCz`, `keywordEn`) plus the top-level `prefill.nkr` paths, intersected with the schema's `properties`. The `prefill.nkr` paths the schema lacks go into the outcome report and the pull-request body, not the request.

`mainContact` is kept only as `mainContactPresent`. `nkr_config` turns that into a present value for the `mainContact` path, so the self-check answers gate.13 from it and shows "present" with no address.

The refresh checks the shape and enum values of every kept field against the fetched schema, including nested
array elements. A non-empty `mainUrl` must be an absolute HTTPS address. Every status must occur in the schema's
enum and in the shared reviewed status mapping used by refresh, build, duplicate and health checks. A curated
`nkr` handle is checked against the snapshot when one exists, on both repositories and resource repositories.

Kept identity values also satisfy the Guide's consumed shapes: alternative names are objects in an array,
their names and language labels are strings, and keywords are arrays of strings. These expectations live with
the reviewed NKR contract; upstream schema changes cannot make an incompatible value safe to write. Field
selection remains the schema-defined intersection, with dynamic pre-fill roots unchanged.

The refresh rejects the replacement, leaving the existing snapshot, in these cases:

- the schema is malformed or lacks `properties` or its status enum;
- a kept value has an invalid shape, status, or address;
- a record is not decommissioned, has an empty `mainUrl`, joins no addressed entry through a reviewed `nkr`
  handle, and its status maps to neither planned nor in development.

Schema retrieval failures retain the retryable `failed` outcome; malformed schema content is `rejected`.

Record names and IDs are bounded, flattened and stripped of terminal/control characters before entering
diagnostics. Source text is escaped for Markdown/HTML, and the publisher independently applies that treatment
to reasons in summaries and pull-request bodies. Snapshot source values are not rewritten by this formatting.

**Alternatives considered.**

- *A hand-maintained allow-list.* Rejected: it drifted silently, which is how 16 unreachable fields stayed listed.
- *Fail when a check names an unavailable field.* Rejected: that would block every refresh until the separate `RepositoryPlus` work lands.

### D7. NKR record pages never seed identity; routes follow NKR type

**Decision.** `identity_seed` treats NKR's host as a registry host, like re3data's, so for NKR rows it falls through to `mainUrl` and then to the name. `preserve_snapshot` routes a new NKR record by its type to `repo/dom`, `repo/inst` or `repo/gen`. The type mapping (`disciplinary`, `institutional`, `generic`) moves from `build_crate.py` into `catalogue_identity.py`, so build and refresh share one copy.

Existing IDs are unaffected: no NKR snapshot has merged.

**Alternatives considered.**

- *A special NKR branch in `identity_seed`.* Rejected: the registry-host list is the existing mechanism, and the spec already forbids registry paths as seeds.

### D8. The duplicate check models NKR records as linked records

**Decision.** `check_duplicates.entries` adds NKR records as registry things with an `nkr` key (the handle) and an address key. `nkr` becomes both an authoritative key and a link key. An NKR record's address joins the component it reaches, as a link does, so the reference harvest reports nothing. Two curated entries naming one handle, or an NKR address reaching two components, are reported with both names. The safe-suggestion machinery gains the `nkr` placement on `[[repository]]` and `[resource.repository]`, so the Node-validator parity check covers it.

### D9. Page checks test the empty state by injection

**Decision.** The two assertions that assume NKR is empty (`tests/page/check_page.mjs`, the finder and the maturity check) set `FairGuide.config.nkr` to null in the page and re-render before asserting. They restore the configuration afterwards, as the gate pre-fill test already does with a record. A new assertion covers the populated state: with the built snapshot, `#nkr-status` is absent and an NKR-credited repository is listed once.

## Risks / Trade-offs

- **[Risk]** NKR text overrides better curated wording: MBDB's name suffix, 25 MBDB keywords, the typo "BioImaing" in CzBIRD's English keywords. **Mitigation:** the abbreviation display rule (D2); a typo is fixed through the existing reviewed local correction, with a tracking issue to NKR, never by editing the snapshot.
- **[Risk]** An exact address shared by two different services, such as an institution's portal, joins them. **Mitigation:** the match is exact after normalisation, not by host; reaching two components is an error (D1, D8).
- **[Risk]** NKR changes its schema again. **Mitigation:** the refresh reads the schema and rejects what it cannot represent before writing (D6); [dsw-nrp/eosc-fair-guide#169](https://github.com/dsw-nrp/eosc-fair-guide/issues/169) covers the expected `RepositoryPlus` change.
- **[Trade-off]** A curated status date older than the snapshot gives way to NKR's. This is accepted under NKR authority: the snapshot date is when the status was last observed.
- **[Trade-off]** Relaxing `url` in the API is a contract change for consumers. This is accepted before the first release and is stated in the schema description.

## Migration Plan

1. Implement and merge this change through a reviewed pull request. No NKR snapshot exists on `main`, so the build is unchanged until one does.
2. Close [dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168) unmerged, with a comment pointing to this change.
3. A maintainer dispatches `source-refresh.yml` for `nkr`, or waits for the schedule. The new pull request carries readable, kind-routed IDs; the maintainer registers them (`scripts/register_ids.py`) and reviews the joins in the preview before merging.
4. Rollback: without a merged NKR snapshot, revert this change. If a snapshot has merged, revert or remove the
   NKR snapshot first, then revert this change, or revert both together in one pull request. Validate the proposed
   revert against a tree containing the merged snapshot so no intermediate tree fails the repository link checks.

## Open Questions

- How to report "BioImaing" to NKR, and whether a local correction is wanted meanwhile, can be decided during review of the refresh pull request without changing this design.
