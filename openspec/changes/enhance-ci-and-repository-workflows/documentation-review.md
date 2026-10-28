# Documentation review receipt

Date: 2026-10-25. Starting revision: `3b3267544b40c2c11bfe68600d9ddeb11de5f337`.
The [section map](section-map.md) accounts for 148 former sections. The structure, links, named-file and README
agreement checks pass for 37 current human documents. Agent instructions and delivered surfaces retain their owners.

## Independent audience readers

Three fresh `default` agents were started without the writing conversation. They read only human documentation,
its linked documentation and the section map; moved facts were sampled with `git show` against the starting revision.
They edited no files and performed no operational actions. Each reviewed the corrected documents again.

| Audience | Agent | Final result |
| --- | --- | --- |
| Guide readers | `docs_reader_review` | `NO_FINDINGS` |
| Contributors | `docs_contributor_review` | `NO_FINDINGS` |
| Maintainers | `docs_maintainer_review` | `NO_FINDINGS` |

## Findings and repairs

| Finding | Disposition |
| --- | --- |
| Reader explanation had no inbound route | Both READMEs link the FIP section of `docs/about.md`; repository layout is also reachable |
| Embedding required source inspection to find its configuration | Both Guide-side and host-side markup, `data-parent-origins` syntax, maintainer responsibility and the build route are documented |
| Advisory wording was lost from contributor guidance | The content reference states the named-NRP-only rule and suitable identifier alternatives; the content how-to links and states them |
| Advertised local duplicate repair lacked identity and recovery details | A linked local how-to restores `github`/`commitNames`, `--person`, complete checks, nonzero no-ops and rollback; the PR runbook covers a missing reply after a successful commit |
| Catalogue and deployment reference disagreed about retrying staging | The catalogue's authored TOML now distinguishes dispatching current staging from retrying a failed tag deployment, then was regenerated |
| Recorded acceptance could not meet the review step's completion condition | The runbook names both eligible-review and conditional explicit-acceptance completion, while preserving enforced GitHub requirements |
| Assembly procedure remained in reference | The procedure moved to `docs/how-to/verify-assembly.md`, linked from the deployment reference |
| Historical tag recovery remained in reference without operational steps | A linked runbook gives prerequisites, exact approval, commands, completion evidence and failure handling; the release runbook exposes the route |

No documentation finding is deferred.

The first integrated run additionally caught the standing introductory tooling-link contract and the complete
source-name inventory in both READMEs. Both were restored without weakening those tests; the reader reviewer
rechecked the final landing pages.

## Moved-fact samples

- Readers: life-cycle stages, role lenses and progressive detail; evaluator scope and retained reader answers;
  Dashboard ownership, browser restriction and prefill fallback; protocol fields, validation and size limits.
- Contributors: bilingual values, the five dated statuses, ORCID opt-out and reviewed identity, conditional
  independent review and explicit release acceptance.
- Maintainers: the timing receipt and artifact caveats, release-body byte preservation and refusals, local repair
  identity/no-op/reply recovery, and the review exception's original conditions.

This is local documentation acceptance. It does not establish that the new default-branch workflows have run,
that the digest has been published, that legacy issues have migrated, or that a release rehearsal has occurred.

## Focused review-procedure follow-up, 26 October 2026

Task 14.3 received a fresh independent integration/reader pass in `/root/review_runbook_reader`, with no writing
conversation inherited. The local documentation snapshot was based on HEAD `1a5287f`; the reader returned a
complete `NO_FINDINGS` with no referrals, unread ranges, refusals or missing evidence.

Scope: the complete new review runbook; the contribution reference's Review section; CODEOWNERS; merge step 2;
and the maintainer task table. The reader compared selectors, local scope behavior and posting/closing rules
against the delivered `aiscr-review-pr` workflow and Guide review facts. It confirmed separate exact review and
summary approvals, content-versus-technical responsibilities and the enforced-review limits of sole-maintainer
acceptance. No hosted behavior or human acceptance is inferred.

Subject SHA256s at that pass:

- `docs/runbooks/review.md`: `67464e3894fb3774dd77ab7ca57758e7acddc1612bf7478ce8fc50af75bd464b`
- `docs/contribution-reference.md`: `6ea884477bf61e3e6e21c37115f408d553c09f137799347bee97b6c0582fcf40`
- `.github/CODEOWNERS`: `c6f979fd886f92023ece173bbb9104738df37912550c875d3b9d3fc2c492d2ee`
- `docs/runbooks/merge.md`: `1181ab05912a35bd58c309894b6a860209e72a804b733552b5d157d1ee75a78c`
- `docs/ci.md`: `d5dc1e73fa07658783e1095feda9b7aeb4553361f56dbf7283760fd68867e840`

The documentation checker passed 38 documents; diagram checks rendered all 17 Mermaid diagrams and six SVG
adaptations. This bounded runbook receipt does not replace task 14.1's complete factual verification or 14.9's
final audience review after the behavior is settled. The earlier receipts above retain their historical scope.

## One-time migration relocation, 26 October 2026

Task 14.7 received a bounded independent reader pass in `/root/review_runbook_reader`, scope
`follow-up-14.7-relocation`, returning complete `NO_FINDINGS`. The reader compared the full relocated procedure
with the exact original procedure preserved as a regression fixture. Only the descriptive label changed from
"this runbook" to "this procedure"; all original steps, capture/approval/retention requirements and failure routes
remain. Proposed dispositions are explicitly unapproved and actual migration remains unchecked task 6.10.

The reader checked removal of the durable task route, retained recurring digest guidance and the new task link.
It did not fetch issue threads, judge hosted behavior, authorize a write or establish migration readiness.
The relocated record SHA256 was `879761595d2c4acf78f508fc49ffcbab2d2fae321a64ee3175b2295968e26c67`;
the original regression fixture was `4519fc19e7bf7d1cf04c3631ed891e777db5e6672e407dac5d53a62ae948b660`.

All 17 documentation tests pass, including reinserting the actual one-time procedure under another durable
runbook name (rejected) and generic setup/repeatable migration examples (accepted). The 37-document structure
and former-section map pass; native generation, ownership and delivered integrity pass.

## Namespace and durable-prose follow-up, 26 October 2026

Independent procedure/diagram scope `follow-up-14.8-diagrams`, run `/root/review_runbook_reader`, returned
`NO_FINDINGS`. The integration reader read the complete review, merge, refresh and digest runbooks and the
production/preview design section, compared all six named workflows and their actual handlers, and checked the
additional publication/tag-selection handlers where the workflows delegated behavior. The report establishes
local procedure semantics only; it establishes no hosted enforcement, rendering result or full long-document review.
Reviewed runbook SHA256s: review `63347288517f1f7e51b8793f9bb629b1f6d26e9d830dbec5a27ae18b4ba23fad`;
merge `93501bafb67c02599f307136056eeaab6b284403d079820b48ed3c84bc26c2d3`;
refresh `21d51b4c08ba72938681635a067deea642a09cc7738c5a14403fbd40f3a1a8e2`;
digest `f05f4f3b4b947a7caf2fa725f3f0dbdca87dfe4f2870cd44e8b32dd7fbe7fd20`.
The design section was reread after its binding-choice correction; its later quality-section heading rename
does not change that reviewed publication section. The native diagram run passes 20 Mermaid diagrams and six
approved SVG adaptations. Four planted publication shortcuts are rejected by the semantic check, and the
workflow tests verify the actual release job waits for image publication after successful Pages binding.

This bounded pass covers tasks 14.4-14.6 and the workflow diagrams in 14.8. It is not the complete
section/claim verification of 14.1 or the final audience acceptance of 14.9; publication-location claims still
depend on the namespace-transition decision recorded in `address-inventory.md`.

- The crate mapping qualifies every semantic type/property. The prefix table retains the actual external
  IRI schemes, including `http://schema.org/`. Serialized aliases are explained separately, without changing
  stored keys. The local criterion row includes `sio:SIO_000233`; test classes retain `ftr:Test`.
- The effective emitted context is checked against the documented namespaces and aliases. A pinned subset of
  the published RO-Crate 1.2 context (source/blob and CC0 dedication recorded in its fixture) enables offline
  expansion of the real crate with RDFLib. Assertions cover Dublin Core publisher, PROV attribution, SIO
  implementation, FTR test classes and the Guide's actual namespace. Unknown/unqualified terms, a wrong
  vocabulary, a changed external scheme and a changed emitted alias are rejected by planted controls.
- All 37 durable human documents pass contextual stale-prose checks. The pass removes change-task dependencies,
  queue rollout narration, completed concept-DOI badge follow-up and deferred-work narration. The EOSC CZ FAIR
  Guide Project is named and linked at its organization Project URL. Dated CI measurements and hosted audit
  observations remain evidence, not current acceptance. Valid conditional recovery instructions, code examples,
  actual issue/PR references and deferred JavaScript loading remain accepted by negative controls.
- Czech and English READMEs, the root metadata and About page welcome assisted work under human oversight and
  responsibility, describe the repository's support and refer to paradata for actual tools/models/sources.
  Historical instruments and the new runtime record remain. Content/freshness checks pass; screen and print
  screenshots at 1280/390 px were inspected in both languages without overflow or external requests on load.

Historical material removed from durable prose is retained here with its original uncertainty:

- The old deployment text said the merge queue would activate in CI-change task 4.8. The current contract
  requires configured checks/reviews before queueing and checks the merged result; the completed rollout is
  not a continuing precondition for readers.
- The old deployment text described a rejected Zenodo archive with a CFF license list, the MIT string
  correction and an uninspected remote error payload. This was a local compatibility diagnosis, not proof of
  the remote cause or successful later archiving. The durable reference retains the actual CFF/import-subset
  distinction and regression command. The previously prospective concept-DOI badge instruction is superseded
  by maintaining the already recorded badge/record; no new archive or DOI claim is made by this edit.
- Batch FAIR-Checker/F-UJI evaluation of every repository sample was deferred separately. Current behavior
  remains one object at a time; no batch feature or acceptance is delivered here. Owner: repository maintainer;
  further implementation needs its own reviewed scope.
- The earlier model documentation called for a team audit of test gaps and validity after the first official
  prerelease. That human follow-up remains with the maintainer/content team; this change neither performs it
  nor treats it as an implementation promise. The durable text now describes the recurring review practice.
- The previous capability table linked organization-Project installation acceptance to task 5.8. Acceptance
  was confirmed earlier, while actual hosted endpoint proof remains the explicit hand-off in 13.3/5.8-5.9.
  The durable table describes the permission prerequisite instead of requiring a reader to find a change task.

## Complete claim review (tasks 14.1 and 14.9), 26-27 October 2026

This pass reads every line of the current human documents by audience and checks every factual claim against code,
content, the built `_site/` or the cited source, then judges whether the audience can follow each procedure. Each
audience reader is a fresh general-purpose agent started without the writing conversation. It edits nothing but its
receipt under the ignored `.cache/`, which records each document's SHA-256 and line count, per-section claims with
evidence, findings and counts. No reader performs an operational action. Findings were verified against their cited
lines before repair.

### Interrupted first pass

A Codex continuation started three readers (`/root/reader_claims`, `/root/contributor_claims` and
`/root/maintainer_claims`) and stopped mid-edit when its workspace ran out of credits. No contributor receipt was
written, and the other two passes were incomplete. The resumed apply (Claude Code) recovered their reported
findings from the session logs, verified each against the current tree and repaired it. Because none of those
passes completed, the final passes below replace them as acceptance.

| Finding | Resolution |
| --- | --- |
| C01 content model, evaluator suggestions | Reviewed whole coverage suggests Yes, Partly or No from the native result; partial coverage suggests Partly or No; other results suggest nothing |
| C02 model and manuscript IDs | `layers-seams-manuscript`, `layers-seams` and `model:layers-seams`; the prose title is not an identifier |
| C03 clause ID prefixes | The table uses the ledger's actual prefixes and source codes; no former alias is revived |
| C04 correspondence identity | A stored `id` and frozen `guideRoute`; `#crosswalk-<id>`, registered as `crosswalk:<id>` |
| C05 glossary identity | A Guide-owned `id`; the Heslář identifier is a typed alternate |
| C06 API addresses | Lists at `api/<collection>.json`, records at their catalogue address, manual tests at `api/tests/<question-id>.json`; the table gives real addresses for every collection |
| C07 portable results | Revision 3 with assessments, otherwise 2; earlier revisions load; 8 MiB import and 384 KiB budget stay distinct |
| C08 crate mapping | Root `schema:editor`, the actual `HowToTip` scope, and source types with `additionalType` |
| C09 external sources | OpenDOAR keys come through Open Policy Finder, paused for new keys on 26 October 2026; Infra Finder's publisher offers data and the Guide links it only |
| C10 advice lenses and actions | One station and level, one or more lenses; `action` is one action or at most two |
| C11 release-body refusals | The how-to and changelog policy state exactly what `release_body.py` refuses and that other metadata is not compared |
| C12 source-link-only questions | Two: `institution.24` and `maturity.18` |
| C13, reader-04 address model | `baseUrl` and the design separate the publication location from the semantic namespace (decision 28) |
| reader-01 Champion evidence | `championEvidenceOnly` partial-evidence suggestions are described; the reader's answer is kept |
| reader-02 FIP Dashboard records | Guide-owned IDs, typed Dashboard alternates and dated, attributed snapshots |
| reader-03 shared results | An explicitly shared result address carries its encoded data |
| M01 script dependencies | Generators use the standard library; the full suite also needs `requirements-dev.txt` |
| M02 quick fallback | The `checks.yml` fallback prints the three hand-off fields |
| M03 digest labels | The digest is created with `guide-health` and `area:maintenance`, pinned by its test |
| M04 Zenodo licence | The pinned importer accepts a string or dictionary but not a list; the repository checks a narrower SPDX-string profile |
| M05 refresh selection | A comment names exactly one source; `all` is offered only by manual dispatch |
| M06 workflow catalogue | Regenerated after workflow integration; `ci_catalogue.py --check` passes |

Owned deferral from C09: the source titled "Object Retrieval API - Sherpa Services" in `content/sources.toml` may be
stale. Retitling it is content work for the content team, with its own source check and paradata.

### Final audience passes

| Audience | Documents | Claims | Verified / finding / owned-deferred | Receipt |
| --- | --- | --- | --- | --- |
| Contributors | 12 (70 headings) | 300 | 275 / 14 / 11 | `.cache/docs-claims-contributor-final.json` |
| Guide readers | 9 (51 headings) | 287 | 249 / 7 / 31 | `.cache/docs-claims-reader-final.json` |
| Maintainers | 16 (56 headings) | 256 | 235 / 4 / 17 | `.cache/docs-claims-maintainer-final.json` |
| **All** | **37 (177 headings)** | **843** | **759 / 25 / 59** | |

Contributor findings, 12 in all (14 claims), were each confirmed against code or built output and repaired:

| Finding | Resolution |
| --- | --- |
| CF-01 content review roles | The content how-to says content collaborators review correctness and tone and a code owner checks technical integrity |
| CF-02 inline language marking | The content model states the actual `lang` behaviour (names with `inLanguage`, language fallback) and that no inline marker exists |
| CF-03 local assembly | The how-to records the checked commit with `FAIR_GUIDE_CHECK_REVISION` and says where the production directory comes from |
| CF-04 release procedure owner | Agent tooling points to the release runbook and deployment reference |
| CF-05 provenance identities | The content how-to requires a reviewed `[[person]]` and existing `[[instrument]]` entries first |
| CF-06 gate principles | `principles` is empty only for an item serving no single principle |
| CF-07 repository functions | `preserve-software` is listed |
| CF-08 file inventory | `model.toml` and `corrections.toml` rows and the corrections fields; `pages.toml` described generally |
| CF-09 Guide `url` | The source-code repository, as the crate's `codeRepository` |
| CF-10 register kinds and action IDs | The complete register kinds and the `release-<version>` action |
| CF-11 model identity and API | `identifier` and `termCode` as emitted; `api/model/{layer,seam,ex}/<id>.json` |
| CF-12 API parameters | Concrete catalogue addresses; only `{test_id}` and `{model_id}` are parameterised |

The reader also noted stale pointers in user-facing messages. The comment-command replies linked a removed
`CONTRIBUTING.md` anchor, and two duplicate-repair messages named moved sections. All three now name the current
documents. `check_commands.mjs` now fails when a reply's link names a missing file or heading, demonstrated by
restoring the old anchor. Incomplete but accurate reference lists (`[[block]]` fields, topic link targets and the
changelog check's generated-lineage exception) were observed and not treated as findings.

CF-02 leaves a conflict for the maintainer: the native content rule asks editors to tag language changes inside a
text, but no such markup exists. Either an OpenSpec change adds the markup, or a governed rule edit removes the
requirement; this change does neither.

Owned deferrals carried by the contributor receipt: live GitHub settings (established by
`python scripts/audit_repository.py`), hosted publication and Zenodo import, client loading of generated mirrors,
browser clipboard behaviour, and external source facts dated in the text.

The first Guide-reader pass stopped at the runtime's session limit before writing a receipt and is not counted.
A fresh reader repeated the whole pass. Its five findings (seven claims) were each confirmed against the cited lines
and repaired:

| Finding | Resolution |
| --- | --- |
| RF-01 build prerequisites | Software practice says the build needs Python 3.11 or later and the pinned Node.js packages from `npm ci`, as `build_site.py` enforces; the crate's `runtimePlatform` says the same |
| RF-02 FRSM-13 evidence | The row cites the build how-to instead of the English README, which states no requirements |
| RF-03 citing the Guide | Both READMEs send readers to the footer's "How to cite the Guide" and say `CITATION.cff` credits the software, as that file states |
| RF-04 Czech titles | The Czech README uses the published title of the analysis and the Guide's name for the model, "model vrstev a návazností" |
| RF-05 App credentials | The design describes `SOURCE_REFRESH_CLIENT_ID` as a repository variable and only the private key as a secret; the same error in `docs/ci-reference.md` is corrected |

Owned deferrals carried by the reader receipt: the Zenodo and Software Heritage badge targets, hosted Pages and
`/next/` availability, observed weekly refresh proposals, published embedding headers, the pilot Champion byte
range and test logs, external evaluator and citation-formatter behaviour, behaviour established by the page and
unit suites, content review of organisation records, hosted release sequencing, and the maintainer's confirmation
of the national figures in the model example.

A fresh maintainer reader then covered all 16 maintainer documents. Its four findings were each confirmed against
the workflows and scripts and repaired:

| Finding | Resolution |
| --- | --- |
| MF-01 partitioned-checks callers | The catalogue entry adds the third caller: a release tag's deployment checks its paired current-head preview there |
| MF-02 waiting runs | The generator distinguishes `queue: max`, which keeps every waiting run, from a group without it, where one run waits and a newer one replaces it; a unit test pins both and the old wording fails it |
| MF-03 reuse hand-off | A reused merge-queue result now ends the deployment summary with **Next**, **If blocked** and **Done when**; the adoption test fails without it |
| MF-04 emergency issue label | The step tells the maintainer to add `area:delivery`, and a missing label is restored through the settings-audit runbook |

Owned deferrals carried by the maintainer receipt: live rulesets, environments, Project automation and token reads
(established by `python scripts/audit_repository.py`), hosted timing receipts for runs no fixture keeps, hosted
rerun artifact behaviour, the published Pages location, external Zenodo and GitHub documentation, merge-box button
labels, a historical-tag push under the tag ruleset, and image tags in the registry after the next release.

All 37 human documents are now read in full with every section accounted for, and no audience has an unread range.
These receipts replace the sampled usability readers of 25 October and the interrupted first pass as the complete
verification; those earlier records above are kept as history. Ordinary human content review is still required,
and the agreed deferral of a separate human documentation-wave review stands.
