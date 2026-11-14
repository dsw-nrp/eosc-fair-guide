# Design

## Context

See `proposal.md` for the combined scope and issue/PR references. This replaces the unimplemented NKR loading
proposal; its earlier 35/36 local result is diagnostic evidence, not acceptance of the identity model.

The existing identity change forbids collision counters and scopes registry records under their described
thing. `reserved_identifiers()` still collects bare IDs across kinds and `short_id()` still allocates counters.
The prepared snapshots retain `git-2`, `provenance-2`, `re3data-2` and `datarepo-2`. Graph/API probes found no
second re3data or DataRepo thing, but KNAV exposes its counter ID and the joined NKR row's local ID can change
without changing the crate. Input identity ownership and published source observations need one coherent rule.

`DASHBOARD_FIP_CLASS` maps `repository` to FIP Registry but lacks the new `registry` key. FAIRsharing and NMA keep
their native `catalogueType`, while the reviewed FIP classification disappears. `views.js` renders the two
full citations in every footer; About already has the six-row roles table but no equivalent full citations.
`vendor_favicons.py` and `catalogue.js` each limit resource badge eligibility to services, tools and registries.
The favicon manifest records acquired assets only; failed fetches and completed negative observations collapse
to the same empty result. The collector also omits NKR-only repository sites; the prepared herbarium site is
absent from its target set, and `repo.cz` is not currently guarded as a shared catalogue host.

Before these further repairs, all four prepared snapshots total 310,237 gzip bytes in Czech and 307,858 in
English, against 307,200. `config.nkr` is initially embedded in `ui.js`; its five records are 3,972 JSON bytes
and 1,446 gzip bytes measured alone. Moving it alone is insufficient for the combined overrun.

## Goals / Non-Goals

**Goals:** make the four imports conform to the existing conceptual model, complete both selected presentation
issues, preserve source and credit meaning, keep the size limit, and verify the integrated result before delivery.

**Non-goals:** a new backend, dependency, public API or saved-answer format; source-text rewriting; merging things
by similar names/hosts; numeric-version bans; raising budgets; changing favicon dimensions/normalization/licensing;
reopening the existing identity change's release/namespace gates; automatic pushing, merging or issue closure.

## Decisions

### 1. Resolve the described thing before allocating an identity

Treat the canonical thing, the normalized source row and the source's observation as separate roles. A reviewed
join identifies the thing; its source observation is the existing `<thing>#<scheme>` catalogue record. It does
not require another numbered thing. Review the meaning of existing source handles before reusing them: a stored
link is a prior assertion, not evidence that a licence family is one licence or software is its deployed service.
Use exact NKR-address matching; retain the prohibition on implicit non-NKR name/host joins. The re3data KNAV join
remains explicit. Preserve existing specific snapshot keys; matching a canonical thing does not justify renaming
every established source row after that thing. Only the newly introduced counter assignments need reallocation.

Use issued `(kind, scope, id)` values when reserving current identities. A term can use `glossary/git` while
the software keeps `resources/git`; a page does not reserve its bare word against a term. After a known join,
allocate a new row against that canonical identity rather than preserving a temporary counter assignment.
The observation's own source identifier retains its issuing scheme; a row-local key must not act as an alias
for another described thing. Use the existing identity projection and typed identifier representation rather
than adding `guideId`, an alias table or another full-address register.

If an unjoined thing collides in its own kind/scope, reject with the conflicting identities and preserve the
old snapshot; a reviewed descriptive slug can resolve it. Existing released identities remain fixed. The four
new, unreleased counter assignments are corrected in place with their references. Preserve existing typed
retirement reservations; legacy unqualified retirements remain conservatively reserved until their owner is
known. Audit affected internal bare-ID lookups and use kind/role context rather than selecting the first hit.
Digits that express real source versions remain valid; test actual collision allocation instead of banning
every numeric suffix.

The maintainer's semantic correction requires a source-by-source review of the FIP joins, including versioned
licences versus their overview and publisher, repository software versus operated repositories, generic software
versus hosted instances, and identifier mechanisms versus their providers. Keep native source fields unchanged.
CLARIN's imported description and B-centre verification are instance-specific claims; neither can become the
Guide's own assertion that the software is a certified repository. Record the evidence and disposition of every
join in this change, and test semantic distinctions as well as address uniqueness. Existing descriptive FIP keys
such as `cc-by-4-0` and `clarin-dspace` are retained unless a separately justified unreleased identity correction
is needed. Do not hide a mistaken join by replacing its key with a broader canonical name.

Keeping automatic counters would contradict the active identity contract. Blindly deleting `-2` would instead
allow unrelated things to collide. The chosen order establishes identity before choosing the local spelling.

### 2. Preserve classifications on source records

Add the reviewed `registry` to FIP Registry correspondence while preserving its native Dashboard type and the
existing local resource-type mapping. Keep ontology classification on the source record and Guide classification
on the thing. Control probes must compare both FAIRsharing and NMA before/after the source reclassification,
including unchanged thing addresses, catalogue-record typing and deposit/verification semantics.

### 3. Move detailed data into existing deferred parts

Move `config.nkr` and `config.re3data` into the `questions` part before language splitting. The maintainer approved
including re3data after the original two moves left Czech 556 bytes over the threshold; its pre-fill consumers
already wait for `questions`. Verify both configurations restore exactly, including language and Retry behavior.
Move primary repository keywords into
property patches in `fips`; keep primary labels, IDs and navigation data initially available. Catalogue and
check routes already wait for both parts, and text search waits for `fips`. Verify every `nkrRecords()` and
`nkrNote()` consumer, cold keyword search, both language load orders and exact reconstruction. Add an existing
part dependency only if a reproducer identifies a missed consumer.

Reuse the established local classic-script loader, merge semantics and registration/Retry path. A load failure
must not appear to mean an empty NKR. Retain the warning-only build behavior and the existing 300 KB acceptance
test. Final measurements include all source, citation and favicon-configuration changes, not isolated estimates.

### 4. Put complete citations on About

Reuse the existing citation renderers and graph metadata to render the analysis and software citations once
within About's credits section, beside the existing roles table. The footer keeps a quiet, keyboard-accessible
credits/About link. Preserve analysis authors, the Guide's editor role, contributor attribution, ORCID choices,
version/DOI data, citation metadata files, licence, funding and build identity. Bilingual/print checks must prove
both presence on About and absence from every footer. This changes the previous footer-location requirement,
not who receives credit.

### 5. Define favicon eligibility once

Declare favicon eligibility on the existing Guide resource-type definitions with a validated optional `favicon`
boolean. Enable it for the six agreed types: service, tool, registry, standard, guide and document. Collection
and generated page configuration derive the eligible type set from that declaration; badge rendering consumes
the generated set. Keep the existing repository, imported-record and evaluator coverage. This native UI policy
does not change an entry's semantic type or imply qualification.

Reuse the current own-host resolution, guarded platform list, local normalized assets and kind fallback.
CoreTrustSeal is an explicit regression case. Platforms and DOI resolvers represent their own home page only;
their mark cannot stand for a hosted paper or tool. Infrastructure-specific reviewed marks keep their existing
separate lookup and refresh path. A shared collection predicate avoids fixing the collector while leaving the
catalogue's display gate unchanged.

Derive collection targets from the reconciled canonical resource/repository things and their winning website
values, reusing the build's identity resolution rather than maintaining another source join. This includes
NKR-only repositories and NKR overrides while respecting an existing curated site when NKR leaves it empty.
Guard NKR catalogue-record addresses as shared-host records, as re3data's already are; a repository without
its own site retains its kind icon. Source observations themselves are not extra favicon targets.

NKR/re3data repository identifier detail and API lookup entries that no authored reference needs initially follow
the same deferred registry detail,
as unreferenced infrastructure entries already do. Catalogue/search load `fips`, repository checks load `questions`,
and machine documentation loads `api`; each receives the complete lookup map. Authored-reference targets stay
initially available so a station link never depends on a later catalogue visit.

### 6. Record acquisition observations beside existing asset provenance

Extend `assets/favicons/sources.toml` with generated `[[observation]]` entries: `host`, `checked` (date),
`outcome` (`available`, `unavailable`, `failed`), a bounded documented `reason`, and optional infrastructure `key`.
Identity is `key` when present, otherwise host. Keep one latest observation per identity. Existing `[[favicon]]`
records retain their file, source, hash, retrieval date and platform restriction. The attempt date must never
rewrite the acquisition date of a retained asset.

Record `unavailable` only after the permitted pages/candidates yield a completed negative observation: missing
icons or unsuitable images after the existing checks. Distinguish definitive missing responses from timeouts,
rate limits, transient server failures and refused redirects. If such a failure prevents a conclusion and no
usable replacement is acquired, record `failed`. Keep valid prior image bytes and dates for both outcomes;
only the existing explicit prune mode may remove them. Partial infrastructure refreshes preserve unrelated
observations and assets.

Validate observation identities, real dates, allowed outcomes/reasons and consistency with asset records in
the offline `--check` path. Keep attempted/available/unavailable/failed/unattempted/excluded coverage in the
vendoring report; do not publish maintenance diagnostics or observation arrays in the initial browser payload.
New eligible hosts remain unattempted until fetched, so ordinary source PRs do not acquire a network-dependent
offline gate. A live refresh must review remaining failures before claiming complete coverage.
Report retained-asset availability and latest-attempt outcomes as separate axes: a usable old icon can coexist
with a newer failed observation, so those counts must not be presented as disjoint populations.

A separate manually maintained unavailable list would duplicate provenance and invite stale negative claims.
The existing generated manifest is the chosen home for both positive assets and acquisition observations.

## Risks / Trade-offs

- A bare-ID helper conflates a term and software after kind-scoped allocation: exercise graph, API, prose links,
  search and all affected role-specific lookups with the real Git/provenance cases.
- A source observation is lost while duplicate things disappear: assert its wording, identifiers, licence,
  classification, date and `primaryTopic`, not merely the count of catalogue entries.
- New favicon eligibility increases metadata or visual ambiguity: derive the type set once, retain platform
  exclusions, inspect actual images and measure the complete initial payload again.
- An external failure is mistaken for a negative fact: keep failure and unavailability distinct, preserve old
  assets, and report unverified hosts without claiming that the issue's coverage is complete.
- A required part arrives late or without registration: prove cold direct navigation, saved-answer retention,
  complete search, retry and both language orders before the broader visual pass.

## Migration Plan

The approved planning replacement removes only the unimplemented `defer-nkr-prefill-data` artifacts after this
plan validates. Implementation requires a fresh apply instruction. Preserve the existing local source/fixture
repairs as input evidence, then regenerate corrected Guide metadata without refetching source passages or
changing their retrieval dates. Extend ordinary content provenance and consolidate the existing rolling usage
record under this change's slug during apply.

Integrate the ten newly imported glossary terms into existing bilingual reader prose where the concept is useful.
Read each affected station through its affected roles; retain existing actions, requirement strength and original
source passages. Prefer links on an already meaningful mention. Do not link general scientific assessment to
archival appraisal, or a general preservation plan to succession, merely because their words resemble the labels.
Record a useful placement or an explicit omission reason for every new term, with ordinary content paradata.

When a curated resource's type conflicts with the Dashboard's mapped type, keep the native description, type and
verification together in an attributed source disclosure. Do not repeat those verification badges in the resource's
own status row. This makes CLARIN's instance-specific B-centre claim inspectable without certifying the software.

Implement identity/classification first, then footer and favicon coverage, then settle deferred payloads against
the final data. Run the complete checks and inspect affected/shared views. Prepare source-PR repairs and the
shared implementation as separately reviewable patches with explicit dependencies; do not silently replace
the original PR histories or close them. Concrete branch updates require their own approval and fresh head
checks, followed by hosted evidence. Release and archive retain their existing approval boundaries.

Rollback of an uncommitted repair restores only its owned hunks; a committed repair is reverted. Keep source
attribution and previously verified favicon bytes throughout. No saved-answer migration or released-IRI alias
layer is introduced.

The maintainer authorized commit and PR preparation on 2026-11-14. Publish a runtime prerequisite draft and a
dependent reader-integration draft, preserving the four existing source PRs. For preparation, the source branches
may merge the committed runtime prerequisite before it reaches `main`; their original commits remain ancestors.
The reader branch assembles those prepared heads and applies the reviewed integration. All PRs target `main`;
their cumulative diffs narrow as prerequisites merge. The merge order and human/technical gates remain unchanged.

## Runtime review remediation

Address the six blocking findings and bounded identity/comment cleanups from the review of the runtime PR before
completing delivery. A file iframe owns its storage independently of its parent, so the cold-load fixture seeds
and verifies state inside that document. A re3data entry action retains its target before navigation, waits for
the questions data before interpreting a snapshot, and leaves load failures to the existing neutral Retry flow.

Favicon publication prepares and validates a complete sibling staging directory, then replaces the current
directory with a verified backup available for rollback/restart recovery. Startup recovery precedes the existing
integrity guard. The manifest schema and acquisition meanings stay unchanged; all string fields use TOML-safe
serialization. The temporary/backup paths are generated maintenance state, never authored assets.

Use one snapshot route/address helper for legacy rows with no explicit route; a repository-shaped Dashboard row
uses the repository kind consistently in reservation, allocation and retirement. Test deferred API lookups against
the complete published API projection and require both referenced and deferred cases to be nonempty. Update the
citation carriers and the counter-refusal release note/label under existing repository policy.

The cross-version protocol, network policy and inferred-agent reservations were initially recorded as advisory
follow-ups. The maintainer subsequently authorized fixing all of them in this active change; the consolidated
decisions below supersede those deferrals. Intentional search-focus preloading remains unchanged. The bounded
manifest escaping observation is already handled with the publication repair. No new GitHub issue is implied.

### Second runtime review: cleanup and Python compatibility

Preserve the declared Python 3.11 minimum. Directory-link inspection uses `lstat` mode and Windows reparse
attributes available at that floor; unsupported newer `Path` methods must not be required, and an inspection
error fails closed. This retains the ownership boundary rather than weakening it for older interpreters.

After recovering any backup, the next vendoring run removes abandoned direct-child `.favicons-stage-*`
directories through that same ownership guard. Reject links/reparse points and paths outside the literal
assets directory before recursive removal; leave unrelated entries and the installed verified bytes intact.
Vendoring remains a single maintenance process, as its shared work directory already requires. Never infer a
complete published asset set from an abandoned stage.

Empty/missing-set checking and work-filename validation were initially advisory observations. They are promoted
into the consolidated remediation below by the maintainer's explicit instruction to fix all remaining items.

## Consolidated remediation of remaining observations

The maintainer's instruction to fix all remaining items and fold them into this change authorizes this planning
extension and its implementation through apply. Preserve the existing PR stack and approval boundaries for merge,
issue closure, spec sync, archive and release. The scope comprises all six outstanding defects/policies; intentional
search-focus preloading remains a reviewed choice rather than a defect.

### Complete organisation reservations

Share named-agent resolution between the full build and its identity-only projection. Include organisations
inferred from publishers, operators, developers and infrastructure hosts when reserving existing addresses.
Keep this projection independent of complete page/check/lifecycle content. Compare it against the complete
catalogue and reproduce the Carpentries collision. An incoming unjoined organisation that collides is refused
for review before snapshot replacement; this adds neither counters nor automatic source joins by name.

### Explicit favicon integrity and contained working files

The read-only check requires an existing directory and a readable manifest with valid set metadata. An explicitly
recorded empty set is valid. Vendoring may bootstrap an absent set as an explicit acquisition operation, after
backup recovery; an existing directory with no valid manifest is not a verified empty set. Preserve prune and
partial-refresh meanings and previously verified bytes/dates.

Validate each host/key-derived working identity and verify its resolved file path is inside the owned work
directory before the first image write. Apply the same rules to offline fixtures and network acquisitions;
reject Windows separators, drive/absolute paths and traversal without normalising them into a different identity.

### Public-only HTTPS acquisition

Favicon acquisition uses direct HTTPS with normal certificate and hostname verification. Reject credentials,
invalid ports/hosts and non-HTTPS URLs; reject non-public, loopback, private, link-local, multicast, reserved,
unspecified and site-local destinations, including mapped-address forms. Resolve all candidate addresses before
connecting and refuse a mixed public/private answer set. Connect to a validated numeric address without a second
DNS lookup, verify the connected peer, and preserve the original TLS hostname. Repeat the policy at every redirect
hop, refusing a downgrade before any HTTP request. Cross-host HTTPS image CDNs remain possible under this policy.

Ambient proxies are deliberately excluded from this acquisition path: delegating resolution to a proxy would
bypass the validated/pinned destination. Document that maintainer-facing change and the offline `--input`
alternative; do not change the Guide's browser connectors or unrelated refresh clients. Offline fixtures make
no DNS or network requests and still obey filename containment. Policy refusals produce a bounded failed
acquisition reason and retain prior icons, never a false unavailable observation. Test DNS answers, rebinding,
connected peers, TLS context/hostname, redirects and proxy exclusion with controlled fixtures; never probe a real
private service. Preserve Python 3.11 and use only the standard library.

### Revision-compatible data loading

Generate one deterministic content/runtime revision for each build. Stamp the initial KB/UI pair, display-language
payloads and every neutral/translated deferred part. Version local script requests with that revision to separate
ordinary HTTP caches while retaining classic scripts and file/iframe operation. A missing or mismatched revision
is rejected before it can be merged. Initial KB/UI mismatches stop normal rendering with a bilingual recovery action.

Stage a neutral part and its selected translation until both are accepted, then merge each accepted contribution
once. A failed or obsolete payload cannot mutate the graph, UI, configuration or answer state. Keep single-flight
loads, accepted payload reuse, language switching and existing Retry semantics. Retry refetches failed registrations;
an outdated initial build can offer an explicit Reload action that retains saved answers. Until that action,
preserve the current view and input and report only a neutral loading failure, never an empty registry or failed
FAIR requirement. Saved-result and public crate/API formats remain unchanged.

Exercise absent/stale registrations, mixed neutral/translated revisions, both language orders, concurrent loads,
Retry after correction and an outdated initial pair on HTTP, file and iframe routes. Inspect the bilingual recovery
states at desktop/320 px and print. Keep the 307,200-byte limit. If revision handling consumes the narrow remaining
margin, move assessment-only configuration to the existing questions part and verify every consumer; do not trim
source passages or raise the budget.
