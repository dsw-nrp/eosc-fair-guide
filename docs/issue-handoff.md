# Issue dispositions and prepared replies

Prepared on 15 October 2026. These are drafts for maintainer review, not posted messages or assigned work.
The proposed owners below must agree to take responsibility. External questions retain the stated interim
behaviour; they do not prevent the Guide from representing the available evidence honestly.

## Standing questions

Each row gives the context, proposed owner, current behaviour and the evidence needed to close it.
Identifiers preserve continuity with the initial planning review without importing its private working material.

| ID | Context and disposition | Proposed owner | Interim behaviour | Acceptance |
| --- | --- | --- | --- | --- |
| Q-03 | NMA browser API access is externally blocked by CORS. | NMA API team | Link to NMA search. | Browser request from the approved Guide origins succeeds with documented access terms; errors remain distinct from absence. |
| Q-05 | Published OpenAIRE aggregation status needs dated confirmation and ongoing observation. | EOSC CZ content editor | State only the sourced status, without an expired relative promise; keep the source watch. | Record a public dated announcement and update the claim and its observation date together. |
| Q-10 | Official logo usage rules have no separate confirmed manual. | EOSC CZ communications | Use the official packages unchanged and retain attribution. | Record applicable published terms or written permission before any altered use. |
| Q-19 | A researcher-facing DSW export of the Czech Core Metadata Model is not confirmed. | DMP.eosc.cz team | Link the available template; do not promise an export. | Demonstrate the published export and its supported model version. |
| Q-20 | Status of the central recommended-licence catalogue under NRP KA 4.2 is unconfirmed. | NRP content owner | Use published NRP guidance and the attributed CC table. | Cite the public catalogue, version and scope; review changes before linking it as operational. |
| Q-23 | Czech NMA documentation addresses return no usable Czech page. | NRP documentation team | Identify English documentation honestly. | Working Czech counterpart reviewed for equivalent meaning and linked language navigation. |
| Q-25 | Resolved on 15 October: the public Czech KNAV page is available and covers type T and NMA. | KNAV content editor | Retain the published Czech source and its programme-specific qualifications. | Verified the page and its source links; no translation-address request remains. |
| Q-27 | Default compliance of Minimum pro RIV needs an authoritative decision. | NMA product owner and Guide maintainer | Keep the sourced checklist and avoid an unsupported compliance guarantee. | Written applicability decision with versioned requirements and affected question review. |
| Q-31 | Final public address needs an owner decision; the alpha is built at `https://fair.eosc.cz/` with its vocabulary and profile derived from it. Prepared issue below. | EOSC CZ service owner | Build from `content/guide.toml` `baseUrl` or `FAIR_GUIDE_BASE_URL`; record identity stays relative to that setting, so adopting another address or changing the value is a value change, not an identity migration; keep the testing notice and the `noindex` staging channel. | Approve the production URL and namespace policy, then verify redirects, metadata, embed origins and both deployment channels. |
| Q-32 | NMA CCMM 2.0.0 support in 2027 is a maintainer note, not a published commitment. | NMA team | Keep that attribution and qualification. | Replace it only with a dated public support statement specifying the model version. |
| Q-33 | FIP Dashboard CORS prevents direct reads from production origins. Prepared issue below. | FIP Dashboard team | Use the dated snapshot and existing nanopublication fallback. | Approved browser origins work; unavailable access remains distinguishable from an empty result. |
| Q-34 | Coverage of nanopublication-only FIPs in the Dashboard is unknown. | FIP Dashboard team | Retain the fallback and source distinctions. | Document inclusion policy and demonstrate a nanopublication-only example before narrowing the fallback. |
| Q-36 | New crate/profile versions require validator support and migration review. | Software maintainer | Keep the currently validated RO-Crate 1.2 and Process Run Crate 0.5 profiles. | Supported validator versions, reviewed semantic differences and successful fixture/full-crate validation. |
| Q-37 | FAIR analysis CoreTrustSeal numbering mixes editions. | Analysis authors | Link requirements by their stated meaning and identify the source edition. | Corrected published analysis or author-confirmed crosswalk; preserve quoted originals. |
| Q-38 | A future national benchmark may replace the Guide's reviewed Champion selection. | NRP assessment owner and Guide maintainer | Retain `champion/selection.md` and the current evidence-based selection. | Published benchmark with version, scope, criterion mappings and an explicit adoption decision. |
| Q-39 | Post-prerelease audit of test validity and gaps is explicitly future work. Prepared issue below. | Content lead and software maintainer | Retain current reviewed tests and their limitations. | Audit the first official prerelease, record evidence and file bounded follow-ups. |
| Q-40 | Deeper population of the conceptual model is explicitly future work. Prepared issue below. | Model maintainers and content lead | Retain reviewed existing associations; relevance does not prove implementation. | Approved useful coverage, source fidelity, ownership and maintenance plan before additional population. |
| Q-41 | Whole F-UJI mappings need maintainer confirmation. | Evaluator-mapping reviewer | Retain reviewed coverage distinctions; partial evidence suggests Partly or No. | Validate `FsF-F1-02MD` to `dataset.01` and `FsF-A1-01M` to `dataset.10`; record whole/partial rationale and version. |
| Q-42 | FAIR-Checker supplies API version 1.0 but no software version. | Evaluator-mapping reviewer | Display native evidence and reviewed identity limitations. | Decide whether that API identity is sufficient, with mapping fixtures and a documented re-review trigger. |
| Q-43 | Periodic evaluator-mapping review needs a named owner. | Maintainer and content lead | Preserve pinned reviewed sources and expose changed/unavailable evidence. | Named responsible reviewer, cadence, source-version triggers and a reviewed update procedure. |
| Q-44 | NRP organisation landing URL and Dashboard slug differ. | NRP communications and Dashboard team | Keep the landing URL and registry identifier in their separate roles. | Confirm canonical organisation URL and registry identity; no inferred equivalence from a redirect alone. |
| Q-45 | Alternative licensing of the KNAV catalogue needs permission. | KNAV Open Science Department and EOSC CZ legal reviewer | Preserve GPL-3.0 on the snapshot and its entities. | Record an authoritative licence grant and review its exact scope before changing attribution. |
| Q-46 | Shared DSW question UUIDs are not established. | DMP.eosc.cz team | Link the public model/tool; do not construct question deep links. | Verify the supported UUID mapping and stable public deep-link format. |
| Q-47 | RDMkit Czech national resources need an outward update after alpha. Prepared issue below. | Maintainer and ELIXIR CZ contributors | Keep current Guide guidance independently sourced. | Reviewed upstream contribution and recorded upstream disposition. |
| Q-49 | MaLDReTH Figure 2 repeats SHARE; the proposed Reuse to ACCESS correspondence needs confirmation. | MaLDReTH working group / PRISM | Mark the correspondence unconfirmed. | Published correction or author confirmation, then review the mapping without altering the original figure. |
| Q-51 | A public machine-readable EOSC CZ Node catalogue is not available to import. Prepared issue below. | e-INFRA CZ / EOSC CZ secretariat | Curate dated membership from the charter and observe the node page. | Published catalogue, licence, schema and membership semantics validated before snapshot adoption. |
| Q-52 | DataHub and re3data Map collection may describe one service. | Map and Data Centre, Charles University Faculty of Science | Keep separate records until the operator confirms their relation. | Confirm public address and identity/part-of relation, then review a merge or explicit relation with provenance. |
| Q-54 | Batched external single-object evaluation of repository samples is explicitly deferred. Prepared issue below. | Software maintainer and mapping reviewers | Keep sample discovery, Champion sample runs and single-object FAIR-Checker/F-UJI. | Bounded explicit runs with native per-record evidence, reviewed subject mappings and portable saved sample evidence. |
| Q-55 | Broader licence selection requires legal/content review. Prepared issue below. | Software maintainer and legal/content reviewers | Keep the flat attributed NRP CC matrix and software selector link. | Approved licence/version scope, sourced explanations, legal review and accessible bilingual interaction. |

Resolved questions remain resolved: the official logos are used unchanged; the approved glossary reuse retains
source attribution and original Czech definitions; DMP.eosc.cz is identified as the Node's DSW. No new licence
request for the approved glossary reuse is part of this hand-off.

Dated source check for Q-25: [KNAV's Czech type-T and NMA article](https://openscience.lib.cas.cz/funders/novy-vyzkumny-vysledek-typu-t-a-narodni-metadatovy-adresar/),
updated 23 February 2026, was read on 15 October. Q-05 remains externally unconfirmed: the checked
[Node announcement](https://www.eosc.cz/en/news-and-events/news/eosc-cz-node-joins-the-eosc-federation) establishes
candidate/onboarding context, but does not establish that OpenAIRE aggregation is operational. This is a limit
of the checked evidence, not proof that no later announcement exists; the source watch remains required.

## Draft reply to issue 2

První dva body jsou zapracovány v upravené podobě:

1. Úvod nabízí vyhledávání a konkrétní situace podle role; odkazy vedou přímo k příslušnému kroku a akci.
   Povinný tříkrokový průchod jsme nezavedli, aby se čtenář mohl vracet přímo ke svému úkolu.
2. Přehled ukazuje sedm fází životního cyklu a všech jedenáct kroků Průvodce. Čtenář sám označuje a odznačuje
   přečtené kroky; otevření kroku značku nenastaví. Značky se ukládají místně a neznamenají splnění požadavků
   ani výsledek sebehodnocení.
3. Generování FAIR prohlášení pro poskytovatele financování zůstává samostatným navazujícím úkolem.
   Připravený návrh níže vyžaduje ověřené a verzované požadavky GAČR, TAČR a Horizon Europe.

Implementace je připravena k přijetí kandidáta. Aktivace na výchozí větvi a zveřejnění následují až po schválení
v rámci [předání](release-handoff.md). Odkaz na navazující issue doplníme po jeho schváleném založení.

## Draft reply to issue 3

1. Lokální workflow jsou připravena: výchozí větev sestavuje `/next/`, produkce vychází z vydání.
   Aktivaci po sloučení, Pages a povinné kontroly musí ještě ověřit správce.
2. Vývojový kontejner má připnuté prostředí a kontrolní příkaz. V tomto prostředí nebyl dostupný Docker daemon;
   spuštění kontejneru je výslovný bod předání, nikoli vykázaný úspěšný test.
3. Chybějící balíček pro Swagger nyní zastaví sestavení ještě před zápisem výstupu a uvede `npm ci`.
   Chování ověřují testy včetně zachování původního výstupu.
4. Instalovatelná offline aplikace je samostatný budoucí úkol. Současný Průvodce funguje z lokálního souboru;
   instalace, service worker a správa aktualizací vyžadují vlastní návrh a ověření.

Podrobný stav a připravený navazující úkol jsou v předání. Odkaz na nové issue doplníme po schváleném založení.

## Draft reply to issue 4

1. Připraven je vložitelný rámec s ukázkou hostitelské stránky. Protokol ověřuje přesný původ zpráv,
   přenáší výšku a aktuální pohled; odpovědi sebehodnocení neposílá. Integraci ověřují lokální testy.
2. Katalog obsahuje 44 výzkumných infrastruktur se zdroji a oddělenými vztahy k provozovatelům, ERIC a národním
   uzlům. Samotná souvislost s infrastrukturou neznamená ověřenou kvalifikaci služby ani splnění FAIR.
3. Doplněna je stránka pro software, příslušné otázky a rady k prostředím, kontejnerům, workflow, WorkflowHubu
   a Workflow RO-Crate. Odkazy na Git, GitHub a GitLab vedou přes vlastní katalogové záznamy Průvodce.

Body jsou implementovány lokálně. Nasazení a přijetí skutečné integrace na eosc.cz zůstávají součástí
schváleného operátorského předání.

## Prepared follow-up issues

Each subsection is a ready-to-review issue body. Post only after remote delivery is authorized, replace its
proposed owner with an agreed assignee, and record the resulting URL in the standing-question table or a linked
tracking issue. Do not close issues 2–4 before the outstanding follow-ups and activation evidence are linked.

### Allow FIP Dashboard reads from the Guide's approved origins (Q-33)

Context: the browser connector cannot read the live Dashboard from the deployment origins under current CORS
configuration. Proposed owner: FIP Dashboard team. Interim: dated snapshot and nanopublication fallback.
Request: agree the final production/staging origins; enable only those supported origins; document access policy.
Acceptance: a real browser can read the supported API from each agreed origin; unsupported origins follow the
agreed policy; unavailable access and no record have different states; credentials are not embedded in the Guide.

### Audit test validity and gaps against the first official prerelease (Q-39)

Context: this review deliberately follows the first official prerelease. Proposed owners: content lead and
software maintainer. Interim: current tests and caveats. Review criterion coverage, source fidelity,
evidence-to-answer logic, false positives/negatives, partial/unavailable evidence and FAIR mappings.
Acceptance: name the exact release baseline, retain reproducible positive/negative examples, disposition every
finding and link bounded implementation issues. No audit is claimed by the present implementation.

### Review deeper population and contextual reuse of the conceptual model (Q-40)

Context: broader population is outside the initial implementation. Proposed owners: model maintainers and
content lead. Review useful links and missing associations across resources, requirements, advice, questions
and tests. Interim: existing reviewed mappings. Acceptance: an approved scope with evidence and review/maintenance
owners; useful reader tasks; unchanged source meaning and FAIR categories; relevance kept distinct from proof
of implementation. Implement subsequent population only through a separately approved change.

### Update RDMkit's Czech national resources after alpha (Q-47)

Context: the page contains the former National Repository pilot and a non-Czech funding line, and omits NRP,
NKR and EOSC CZ. Proposed owners: maintainer and the page's ELIXIR CZ contributors. Interim: independently sourced
Guide advice. Acceptance: check the live upstream page after alpha, prepare a sourced update with the current
services and funding context, obtain contributor review and record the upstream PR and disposition.

### Adopt the public EOSC CZ Node service catalogue when available (Q-51)

Context: the charter envisages a national service catalogue, but no adopted machine-readable membership source
is available. Proposed owners: e-INFRA CZ / EOSC CZ secretariat and snapshot maintainer. Interim: dated curated
charter membership and source watch. Acceptance: public endpoint, reuse terms, schema, identifiers and membership
roles/statuses; reviewed joins to Guide-owned IDs; safe refresh/removal handling; no implication of certification.

### Run external evaluators over a bounded repository sample (Q-54)

Context: FAIR-Checker and F-UJI currently assess one object; repository sample discovery and Champion runs remain
available. Proposed owners: software maintainer and evaluator-mapping reviewers. Acceptance: explicit user
action; bounded count/concurrency; reviewed subject-aware mappings; native per-record evidence, dates and
coverage; no result distinguished from service failure; manual answers preserved; complete sample evidence
export/import. Document public metadata sent and cancellation/retry behaviour before implementation.

### Design a broader, source-reviewed licence selector (Q-55)

Context: the current CC matrix is a flat attributed NRP table, and software links to the NRP License Selector.
Proposed owners: software maintainer and legal/content reviewers. Establish useful licence families and reader
tasks; assess SPDX as an identifier catalogue, not a compatibility authority. Source and version every rule;
separate adaptation/combination, output licence choice and unchanged redistribution. Acceptance: approved scope
and sources, licence/version-aware explanations, Czech legal qualifications, legal review and accessible
bilingual controls justified by the larger scope; retain direct access to the simple CC table.

### Prepare sourced FAIR data statements for funders (issue 2.3)

Context: readers need reusable statements for GAČR, TAČR and Horizon Europe. Proposed owners: funding support
specialist and content editor. Interim: existing DMP/action guidance. Acceptance: dated official requirements
for each programme/call, explicit applicability and source versions, editable statements with assumptions and
missing evidence visible, accessible bilingual export, and no invented compliance certification. Review the
draft with funding specialists before implementing a generator.

### Design an installable offline version with safe updates (issue 3.4)

Context: local-file use already works, but installability and an update lifecycle are separate capabilities.
Proposed owner: software maintainer. Interim: downloadable file-mode Guide. Acceptance: agreed offline scope,
versioned cache/update/rollback rules, visible stale-source state, preserved local answers, explicit online
external probes, no background assessment, accessible install/update behaviour and browser coverage. Document
hosting and service-worker scope before implementation.

### Assign and validate external-evaluator mapping maintenance (Q-41–Q-43)

Context: whole versus partial F-UJI coverage and FAIR-Checker's version identity require a reviewer decision.
Proposed owner: evaluator-mapping reviewer, agreed with the content lead. Interim: current reviewed mappings and
visible limitations. Acceptance: evidence and fixtures for the two named whole mappings; decision on API-version
identity; named owner, review cadence and metric/version change triggers; preserve native evidence and manual
answers when mappings change. Further whole mappings need focused validation, not a blanket promotion.

### Confirm and adopt the Guide's canonical address (Q-31)

Context: the guide's page, the vocabulary of its own terms (`https://fair.eosc.cz/terms#`) and its RO-Crate
profile all derive from one setting, `baseUrl` in `content/guide.toml` or `FAIR_GUIDE_BASE_URL` at build time.
The alpha is built with `https://fair.eosc.cz/` so that the published IRIs are canonical from the first release,
but that address is not yet agreed with its owner. Record identity and record addresses are relative to the
setting, so adopting another address later, or changing this value, is a value change and not an identity
migration. Proposed owner: EOSC CZ service owner. Interim: build from the setting, keep the testing notice and
the `noindex` staging channel. Request: confirm `fair.eosc.cz` as the guide's official address, or name the
address to use, and state the hosting and redirect arrangement (DNS, GitHub Pages or eosc.cz, embed origins).
Acceptance: the agreed address resolves to the guide; the vocabulary and profile IRIs resolve at it; the embed
origins are agreed for it; both deployment channels are verified there; and the setting, the profile IRI, the
shapes' prefix and the embed examples agree. Switching the value is a bounded, checked change — four files, and
`check_content` refuses a half-switched base.
