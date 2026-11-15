# Identity and glossary review

Review date: 2026-11-14. This supplements the design with the maintainer's semantic corrections. The earlier
mechanically passing delivery candidate was superseded; its renamed FIP keys are not accepted migrations.

## Source keys and described things

An established snapshot key is preserved independently of projection onto a curated thing. In particular,
`cc-by-4-0`, `clarin-dspace`, `dsw`, `doi`, `datacite-metadata-schema`, `e-infra-cz-aai`, `asep` and `zenodo`
retain their prior Guide metadata. The four newly imported counter assignments remain corrected: `glossary/git`,
`glossary/provenance`, KNAV `re3data`, and NKR `datarepo`. Native issuer/value pairs remain unchanged throughout.

| Dashboard handle | Reviewed disposition | Reason and scope |
| --- | --- | --- |
| `cc-by-40` | Remove join to `resources/creative-commons`; retain `resources/cc-by-4-0` | A specific, versioned licence is not an overview of licences. The overview links the specific entry. |
| organization `creative-commons` | Remove join to the licence overview; retain `organizations/cc` | The publisher is a separate organisation, not a licence or a list of licences. |
| `clarin-dspace` | Remove join to the LINDAT repository annotation; attach to reviewed `resources/clarin-dspace` software | The software and the repository using it are different things. The software links to the repository in its description, without asserting identity. |
| `dsw-tool` | Remove join to `resources/dmp-eosc`; retain `resources/dsw` | The global software platform is not the national deployment. KNAV's ELIXIR instance remains a third thing. The accepted shared-name group now records platform, instance and developer project explicitly. |
| `doi-datacite` | Remove join to the DataCite agency; retain `resources/doi` | The record describes DataCite DOI identifiers/registration, while the curated entry describes the provider. The existing key is retained; it does not assert that every DOI is a DataCite DOI. |
| organization `datacite` | Retain join to `resources/datacite` | Both describe the DataCite agency, with its ROR. The mechanism's provider resolves to this agency. |
| `datacite-schema` | Retain join to `resources/datacite-schema`; preserve row key `datacite-metadata-schema` | Both descriptions concern the schema series. The Guide's citation identifies documentation 4.7; the Dashboard's different DOI remains on its record. No equivalence of editions or version-specific DOIs is inferred. |
| `e-infra-aai` | Retain join to `resources/einfra-aai`; preserve row key `e-infra-cz-aai` | Both describe the national AAI service. The native Perun website does not make the record a description of every deployment of Perun software. |
| `fairsharing` | Retain `resources/fairsharing` | Same curated registry of standards, databases and policies; native reclassification to registry stays on its record. |
| organization `fairsharing-org` | Retain existing reviewed FAIRsharing project join | The source names the FAIRsharing project itself, without identifying a separate legal entity. This does not join FAIRsharing's hosts or the University of Oxford. |
| `orcid`, organization `orcid-org` | Retain existing reviewed `resources/orcid` join | The existing entry describes the ORCID initiative and identifier service. No individual ORCID iD, researcher, or host organisation is equated with it. |
| `ror` | Retain `resources/ror` | Same research-organisation identifier registry, not any organisation it identifies. |
| `handle` | Retain `resources/handle` | Same Handle System, not one Handle identifier or a hosted repository. |
| `signposting` | Retain `resources/fair-signposting` | Same FAIR Signposting profile; native access-protocol and Guide standard labels remain separate classifications. |
| `ro-crate` | Retain `resources/ro-crate` | Same packaging specification family; native generic description and the Guide's cited version remain distinguishable. |
| `oai-pmh` | Retain `resources/oai-pmh` | Same harvesting protocol, not a particular endpoint. |
| `nma` | Retain `resources/nma` | Same national metadata catalogue. Its demo source status is not promoted above the Guide's dated reviewed status. |
| `asep-arl` | Retain repository annotation join to `repositories/asep` | The national ASEP data-repository deployment, supported by the exact reviewed re3data annotation; not generic ARL software. |
| `zenodo` | Retain `repositories/zenodo` | Same operated repository. Preserve source row key/kind; projection supplies its canonical repository address. |
| `eduid-cz`, `nrp-invenio`, `nusl` | Retain their existing reviewed annotations | The records describe the named national service/deployments. Their annotations enrich KNAV/Guide classification without claiming that all Shibboleth or Invenio installations are those services. |

Other organisation joins remain on their exact reviewed handles/RORs: CESNET, CESSDA ERIC, CLARIN ERIC, CSDA,
e-INFRA CZ, ELIXIR CZ, EOSC CZ, KNAV, LINDAT/CLARIAH-CZ, NRP and NTK. These describe their named organisations or
infrastructures, not repositories they operate. Unjoined organisations and source-only resources remain unjoined;
neither a similar name nor a shared host creates a new identity assertion. Existing issued counter-looking IDs in
unrelated rows are not newly allocated or renamed by this refresh.

## CLARIN source ambiguity and verification

The maintainer identifies the Dashboard subject as repository software. The official
[CLARIN DSpace repository](https://github.com/ufal/clarin-dspace) confirms a software project based on DSpace.
The imported demo snapshot nevertheless describes an operated **instance**, points to a repository website, and
includes a CLARIN B-centre claim. Its dataset disclaimer also states that these are demonstration declarations.

Those native fields are preserved verbatim, not silently corrected into software claims. The reviewed software
entry has its own description, official software URL and tool classification. It does not enter the deposit
repository list. The Dashboard's conflicting type, description, verifier/date and B-centre note are grouped in an
attributed source disclosure; no such verification badge appears in the software's own status row. The LINDAT
repository keeps its re3data/KNAV records without this software identity join. This is a reviewed interpretation
with a visible source conflict, not independent evidence that the software is certified.

The [Creative Commons licence overview](https://creativecommons.org/licenses/) and
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) likewise identify different scopes. No other CC licence
will be attached to the specific BY 4.0 identity merely because the publisher or licence family is shared.

## Glossary placement review

The complete Plan and Publication stations were read across V, DS, SR and K, including shared advice, practical
steps, source context and AI tips, before editing. Changes retain the existing responsibilities, action controls,
cited ledger clauses and requirement strength; source passages and imported definitions are unchanged.

| Newly imported term | Placement or omission |
| --- | --- |
| `git` | AI page's commit/version-control practice links the definition; existing software entry and other action links remain available. |
| `authenticity` | No addition: present guidance discusses provenance/traceability and checksums, not a claim that an object is what it purports to be. A checksum alone is not authenticity evidence. |
| `succession-plan` | No addition: current passages discuss preservation and PID maintenance, not a hand-over of custody/control to a successor repository. |
| `appraisal` | Plan V, `plan.32`: selecting data for long-term retention, not assessing FAIRness or research performance. |
| `preferred-formats` | Publication V, `publication.30`: read the repository's accepted/recommended formats before deposit; retain the upload/checksum steps. |
| `fair-implementation-profile` | Plan K `plan.21`/`plan.22`, Publication K `publication.21`, the FIP check introduction, About's Dashboard explanation and the AI page's use overview. |
| `fair-enabling-resource` | Plan K `plan.22` and About's Dashboard explanation, on the choices recorded in a FIP. |
| `repository-policy` | Plan SR `plan.17`, on the existing NKR policy links. |
| `nanopublication` | FIP check introduction, on the published pre-fill input; the Dashboard action still opens the service. |
| `provenance` | Provenance page's opening explanation; retain its explicit distinction from paradata. |

Both languages name the same targets. Plain terms elsewhere are not replaced mechanically: for example a service
action still opens the service, and a generic preservation plan does not become a succession plan.

## Delivery dependency

Reader references require the new Heslář terms. The runtime prerequisite therefore carries neither the new
references nor the semantic content joins that depend on a prepared source. Original source PR repairs remain
separate. A final integration patch applies after the four refreshed sources and carries the reviewed joins,
glossary references and their paradata. Each projected stage must pass independently; the final combined tree
must reproduce the reviewed working files exactly.

The reader PR records its content work in `2026-11-14-identity-review`, separate from the runtime action
`2026-11-14-catalogue-repair`. Freshness is checked against the assembled source-cohort parent as well as the
original main branch, so the content remains covered after the prerequisite PRs merge.
