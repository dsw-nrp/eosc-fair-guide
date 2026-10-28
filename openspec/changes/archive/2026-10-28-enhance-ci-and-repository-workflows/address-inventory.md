# Serving-location inventory and compatibility disposition

Task 12.1, recorded 26 October 2026 against checkpoint `1a5287f`, before changing address generation.
This is a change-owned implementation record, not a permanent hosting assumption.

## Verified baseline

The read-only Pages API reports `https://dsw-nrp.github.io/eosc-fair-guide/`, workflow deployment, HTTPS enabled
and no custom domain. `python scripts/build_site.py` succeeds, but its configured publication location remains
`https://fair.eosc.cz/`. `apply_base_url()` derives `pageUrl`, `vocabularyBase` and the profile IRI together.

The real crate contains 3,229 entities: 3,137 relative IDs, 24 external absolute IDs and 68 Guide-owned absolute
IRIs. The latter are the 67 `terms#` properties and `profile/0.1`. Its extension context uses those property IRIs;
the dataset's `conformsTo` names the profile. API records and the linkset use relative references, and OpenAPI's
server is `.`. These counts describe this input tree, not a permanent coverage floor.

Probes rebuilt the actual graph with `FAIR_GUIDE_BASE_URL=https://one.example/` and
`https://two.example/a/guide/`. In both, all 3,137 relative and 24 external IDs remained unchanged. Exactly 68
absolute publication IRIs relocated by replacing the old publication prefix; no other entity ID changed.
The existing builder's address substitution is broader than navigation and must be verified as such.

## Consumer inventory

| Consumer | Maintained source and mechanism | Required treatment |
| --- | --- | --- |
| Publication input | `content/guide.toml`, `build_crate.apply_base_url()`, `BASE_URL_ENV` | The configured location names the verified current Pages site; actual deployment input overrides it before validation. Separate selected semantic inputs under decision 28. No future-domain prediction or network discovery in an ordinary build |
| Browser page/export root | `assets/js/core.js`: `pageAddress()`, `siteAddress()` | HTTP(S) links use the Guide window's current URL/path. File use needs usable relative references and must not export a filesystem path as a public ID |
| Entry routing | `core.js`: `entryHref()` and its `pageUrl` fallback | Preserve logical record routes; distinguish semantic publication addresses from navigation |
| Catalogue exports | `catalogue-view.js`: CSV/JSON-LD entries, record links and export context | Resolve page/API links at the current channel; preserve exact external and logical identifiers |
| Self-check exports and shares | `selfcheck.js`: Markdown, result crates, test references and encoded state; `views.js` links | Current page/site roots for navigational references; explicit vocabulary terms retain the build's reviewed semantic context |
| Crate and extension context | `build_crate.build_terms()`, `build_crate()`, `page_config().config.vocab` | Ordinary previews retain published production's recorded semantic values; relocate the owned property IRIs/profile consistently for the next release and paired preview before verification, keeping stored keys and logical record IDs |
| Page metadata | `build_crate.page_summary()` and `render_page()` | Absolute metadata uses the actual publication input; browser navigation does not depend on this build-time value |
| Vocabulary publication | `vocabulary_base()`, `vocabulary_document()`, `vocabulary_page()` | Landing page, Turtle and graph term definitions agree with the same publication prefix |
| Profile publication | `profile_shapes()`, `profile_page()`, authored `profile/fair-guide/` templates | Generated profile declaration, shapes and landing page agree; authored template location does not force a deployed host |
| API and signposting | `build_api.py`, `signposts()`, `linkset()`, API schemas and OpenAPI | Retain relative entity/file references and the relative server; inspect contexts for the same semantic publication prefix |
| Sitemap and robots | `crawler_files()`, `CRAWLER_FILES`, assembly filtering and `CrawlerFileTests` | Actual production root/API URLs, effective host-root robots scope, crawlable preview `noindex`, no fabricated dates |
| Validation | `check_content.py` HTTPS/profile checks; crate/vocabulary/profile validators | Validate publication inputs coherently; exercise root/subpath origins and exact expanded vocabulary IRIs |
| Deployment checks | `checks.yml`, reusable `partitioned-checks.yml`, `deploy.yml`, `check_ci.py` build/adoption | Supply the same actual location and selected semantic namespace/profile before every compared build; bind them to input identity so reuse cannot cross incompatible values |
| Publication and artifacts | `package_site.py`, `assemble_pages.py`, `publish.yml`, release-artifact helpers | Package only validated bytes. Pair new production with a separately verified current-head preview using the same target namespace/profile; recheck identities/approval before a single Pages deployment. Never patch an existing release or preview |
| Other published metadata/examples | `docker/Dockerfile`, both READMEs, embedding examples, design/content references | Use the verified current address or explicitly supplied deployment input. Preserve historical evidence, issue snapshots and quoted sources |
| Citation/source identities | `CITATION.cff`, `.zenodo.json`, content source IDs and exact external vocabulary IRIs | Repository/DOI/source identities are not page-location aliases and are not rewritten by a hostname substitution |

## Address model and compatibility

1. Navigation and API/file references follow the serving document and its channel path. An iframe uses its own
   document location. Relative offline links avoid a guessed public host and do not expose filesystem paths as
   public identifiers. Static absolute metadata uses the actual publication input before checks/package.
2. Default publication input is the verified current Pages address. A different host supplies its own actual
   URL; it does not require changing browser code. The preview uses its own navigation/API path. Before cutover,
   ordinary previews retain the verified published production vocabulary/profile namespace. New production and
   a checked current-head preview switch to the same actual-root namespace together at the next approved release.
3. The 67 absolute property IRIs and one profile IRI are a deliberate relocation of publication addresses.
   Their absolute RDF names do change; this is not claimed to preserve those absolute names. Their symbols,
   meaning and stored aliases stay the same. All logical content record IDs and exact external IRIs stay fixed.
   Tests compare the expanded context, graph and shapes, not merely visible links. The planned relocation occurs
   only for the coordinated release pair; changing the navigation/publication input alone cannot migrate an
   ordinary preview's semantic identity ahead of production.
4. Existing alpha archives and release assets retain their original namespace and bytes. They are not patched,
   silently reinterpreted, or given fabricated `sameAs` declarations. Historical consumers retain each artifact's
   context; new consumers use the current artifact's published context/profile. No redirect at `fair.eosc.cz` is
   promised: that hostname's adoption/DNS remains outside this change.
5. Root/API discovery is the agreed initial scope. Hash views and languages do not become separately indexable
   documents. A project-subpath robots file does not control its origin, and crawler access must allow reading
   preview `noindex`. Search-engine uptake remains separate from correct generated and hosted output.

The alternate-origin graph probes establish this inventory and compatibility boundary only. Runtime file/iframe,
expanded profile, crawler, artifact-byte and hosted discovery acceptance remain tasks 12.2-12.6.

## Live transition finding: acceptance reopened

After implementing the input plumbing, a fresh read of the actual production crate and vocabulary confirmed:

- Production's `scope` mapping is `https://fair.eosc.cz/terms#scope`, and its profile is
  `https://fair.eosc.cz/profile/0.1`.
- The production `terms/fair-guide.ttl` defines the legacy namespace, not
  `https://dsw-nrp.github.io/eosc-fair-guide/terms#scope`.
- A newly built preview using the Pages namespace would dereference production documents that still define the
  legacy namespace. Logical record IDs surviving the graph probe does not resolve this operational transition.

This finding reopened task 12.1: the graph/consumer inventory was complete, but the migration direction was not
settled. Updating production files outside a new verified release would violate artifact immutability, while
changing preview alone would not meet the shared semantic-identity requirement. The subsequent maintainer
decision below resolves that question; it does not retrospectively accept the draft implementation.

## Selected transition: coordinated next-release cutover

The maintainer selected: **"Plan a coordinated production/preview namespace cutover at the next release."**
This is planning scope, not approval to tag, promote, publish or modify existing release artifacts.

Decision 28 and the two revised capability deltas define the explicit compatibility disposition:

1. Ordinary pre-cutover previews use the verified published production namespace/profile as a separate semantic
   build input. Navigation/discovery follows the actual Pages location without causing an early namespace switch.
2. The next release's production artifact and a current-default-head preview are verified against the same new
   namespace/profile at the actual publication root. Their evidence binds semantic and publication inputs;
   historical unstamped values come from the verified crate, never the current source default.
3. Trusted publication checks current head, artifact contents, shared inputs and production approval, then deploys
   the compatible pair together. A mismatch, stale head, failed check or missing approval publishes neither
   candidate channel. The prior deployment stays intact; a retry requires a newly compatible verified pair.
4. Old archives keep their original bytes and contexts. Logical IDs and exact external IRIs stay fixed. No
   aliases, redirects, custom-domain/DNS changes or profile-version bump are inferred.

Tasks 12.3, 12.6 and new 12.7 cover this transition. Task 12.1 remains for apply to verify the revised inventory
and compatibility model; no implementation task is completed by this planning revision. The migration-direction
question is settled, and the updated plan is the next apply scope. No release version or execution is selected.

## Local acceptance matrix (task 12.6), 26 October 2026

Recorded in the resumed apply after an interrupted session. The review of that session's draft found and repaired
three defects before acceptance. The pre-deployment recheck failed every ordinary publication that a push
overtook; it now requires a current head only for a paired release. Fixtures replaced the live-production selection
with the newest approved release, so they asserted that branch publications promote releases, which the code does
not do; they now model the live release. The paired preview used the head read before approval, which can be hours
old; `pair-head` now reads it after approval. Each row names actual producers and consumers; GitHub/HTTP transport is
the only substituted part.

| Required case | Evidence (actual producer → consumer) |
| --- | --- |
| Two origins × two prefixes, expanded JSON-LD and SHACL profile | `test_publication_location` builds the real graph for `one.`/`two.example`, `/` and `/a/guide/`, legacy and actual namespaces; every Guide term and the profile move, all other IDs stay; pySHACL validates and rejects a planted gap |
| Runtime navigation, API records, exports, iframe, `index.html`, `file://`, no load-time request | `check_embed.mjs` consumes real exports and API records at two origins and prefixes through an iframe and a local file; filesystem paths are never published |
| Pre-cutover ordinary preview | `check_publication.mjs` protocol: the live legacy crate, verified against the real packaged release assets, selects legacy semantics for `buildLocation` and an ordinary publication; `test_assemble_pages` assembles a legacy preview at the actual Pages location |
| Paired cutover and later previews | Protocol: a tag publication takes its paired preview; after cutover the live new release gives previews its namespace. `test_assemble_pages` accepts the matching pair and refuses a mixed one |
| Stale head, missing paired preview, moved Pages root | Protocol and `assertPublication` cases: nothing published or deployment refused, with the rerun route |
| Namespace/profile/root mismatch, forged or legacy artifact | `test_publication_location` and `test_assemble_pages`: stamps that differ from contents, another root or profile, contradictory terms; unstamped archives read from their crate |
| Failed check, missing approval | `pair-head` requires approval (or approved reuse); `test_workflows` pins it, and publication follows only a successful deployment; `check_docs` rejects a diagram path past withheld approval |
| Cross-namespace reuse | `test_a_result_checked_for_another_namespace_is_never_reused`: two real builds of one commit and location differ in crate, page configuration and vocabulary, and `check_ci.adoption_problems` refuses |
| Unchanged historical bytes | Cutover assembly keeps the archive bytes; `test_image_release` refuses rewriting legacy archives; crawler assembly keeps every production byte |
| Sitemap and robots, root and subpath, planted `noindex` conflict | `CrawlerFileTests` on the real builder and assembly; `preview_blocked` cases and a planted root disallow refused by assembly |

Local fixtures do not establish hosted discovery, actual Pages API behaviour, real tag-run timing or search-engine
uptake. Those stay with the separately approved rehearsal (11.3); indexing uptake is not a release criterion.

## Revision, 28 October 2026: a reviewed namespace setting

The maintainer replaced the coordinated pair with a reviewed namespace setting (decision 28, revised). The
inventory, the 68 relocated Guide IRIs and the historical-artifact disposition above still hold. What changes is how
the namespace is chosen: from `content/guide.toml`, not from published production. The rows above for the paired
cutover, the stale head and the missing paired preview describe the implementation that task 16.2 removes. Its
verification replaces them with a mixed-namespace pair that assembles with a notice and a refusal for different
publication roots. A persistent `w3id.org` namespace is tracked as #136.
