# Design

## Context

See [proposal.md](proposal.md) for the failed run and agreed scope. The existing owners are:

- `scripts/release_versions.py`: reachable-tag selection, release-history filtering, metadata, notes,
  provenance and the permitted-file digest manifest.
- `.github/scripts/prepare-release.cjs`: complete GitHub reads, branch freshness, release-PR delivery and tags.
- `prepare-release.yml` and `tag-release.yml`: separate manual, default-branch-only dispatches.
- `deploy.yml` and `release.yml`: checked tag artifacts, deployment, container publication and draft releases.
- `CITATION.cff` and the staged `.zenodo.json`: software citation and archive metadata; the latter currently
  has no release-preparation or cross-file validation coverage.

The present changelog refuses an empty selected PR list. Tagging requires a release PR whose merge SHA is
exactly the dispatch SHA. The delivery spec explicitly mandates that route; the delta changes that contract.
`CONTRIBUTING.md` also states an absolute PR-only contribution rule. Its release guidance and branch wording
must distinguish the default PR practice from explicitly authorized maintainer direct commits.

Two already published repairs form the existing baseline for this change:

| Existing commit | Behavior to preserve |
| --- | --- |
| [`6d15974`](https://github.com/dsw-nrp/eosc-fair-guide/commit/6d15974f1215103e5140c7957277e58ab60bbc50) | Preserve the repository getter when deriving GitHub workflow contexts; retain workflow callers, tests and recovery requirements. |
| [`ceb5f79`](https://github.com/dsw-nrp/eosc-fair-guide/commit/ceb5f79008a26a86dd1bc150d226b7b45bb91c2b) | Describe the software license as the MIT string in CFF. |

The staged CFF additions supply English affiliations and the guide URL; the staged Zenodo JSON adds structured
ROR affiliations, references, relations and funding/licensing notes. Preserve these reviewed additions.
Both the tag-time CFF license list and the current MIT-string document passed CFF 1.2.0 validation during
exploration. The maintainer reports that Zenodo rejected the previous release. The importer's string-valued
CFF license field supports the suspected cause, but the exact remote error payload has not been inspected.

## Goals / Non-Goals

**Goals:** retain one metadata owner and one manual tag path; make change selection truthful across direct,
merge, squash and rebase histories; validate committed release metadata independently of PR provenance;
maintain archive metadata and retain both existing repairs through normal PR delivery.

**Non-Goals:** a second metadata publisher, automatic commits to `main`, automatic version selection,
automatic changes to branch protection, moving existing tags, or changes to the static application's data and UI.
Accepting an existing direct commit does not grant an agent permission to push directly to `main`.

## Decisions

### Preserve PR delivery and separate tag initiation

Prepare release continues to propose `release/<version>` using the current permitted-file policy, digests,
actor identity and run-start timestamp. There is no direct-push mode in this change. A maintainer can instead
commit consistent release metadata through their separately authorized process and run Tag release.

This preserves the familiar review path without making the release commit's PR ancestry an eligibility rule.
An automatic tag after preparation or a release on every default-branch push would change release initiation
and is excluded. The existing App token remains the tag writer so the normal tag deployment is triggered.

### Retain the existing published history

The maintainer chose ordinary commit and PR delivery. The repository-context and MIT-license repairs remain
in their existing commits on main, together with the initial-alpha archive. This change builds on those repairs
and preserves the reviewed CFF/Zenodo additions. No replacement baseline or repair replay is needed.
Remove the abandoned local candidate branches, session-created recovery refs and candidate construction/export
files. Keep the current branch, active implementation, reviewed metadata, published refs and release tag intact.
The release-helper/workflow regression fixtures continue to cover the repository-getter repair.

### Use Git ancestry for scope and GitHub associations for PR grouping

Retain the nearest reachable valid release tag and full selected commit ancestry as the scope authority in
Python. Also emit ordered first-parent commit records for direct default-branch entries: full SHA and subject.
For the first release, walk from the beginning. Do not classify commits from dates or subject conventions.

Extend the Python CLI with a read-only history export consumed before the GitHub collection step; move Python
setup earlier in `prepare-release.yml`. The export binds its records to the selected dispatch SHA and tag.
The collector retains the complete paginated closed-PR listing and adds paginated PR associations for each
first-parent candidate, using GitHub's [commit-to-PR endpoint](https://docs.github.com/en/rest/commits/commits#list-pull-requests-associated-with-a-commit).
Use validated structured JSON for that additional data; preserve the existing `--prs` input rather than
silently changing a list into an incompatible object. Python checks SHAs and history membership on consumption.

Select PRs using merged state, target repository/default branch and merge-SHA membership in the full release
range. Remove first-parent commits associated with those selected PRs from the direct list. This groups
ordinary merge commits, squash commits and rebased PR commits under their PR while retaining genuine direct
commits. A matching subject or a merely open/unmerged PR is insufficient to suppress a direct entry. An API
failure or incomplete association record is a failed collection, not evidence that a commit had no PR.

First-parent traversal avoids listing side-branch internals twice; the existing full-ancestry scope keeps PR
selection compatible. See the [Git history documentation](https://git-scm.com/docs/git-log) for traversal semantics.
Fetch associations once per distinct candidate, with bounded concurrency and complete pagination. This costs
additional read calls proportional to release history, but avoids unreliable merge-message heuristics.

### Render complete, stable release notes

Keep the existing merged-PR section and add a direct-commits section only when needed. Sort PR entries by
merge time with PR number as a tie-breaker; keep commits in deterministic history order. Escape commit subjects
with the same plain-text Markdown policy as PR titles, and build links from the validated repository identity
and full SHA. The short SHA is a label, not the target identity. Do not collect commit e-mail addresses.

Reject preparation when the selected release history is empty, rather than when the PR list is empty.
Validate all collected data before the existing first metadata write. Preserve earlier released sections,
metadata references, prepared-file restrictions, provenance attribution and reviewed retry recovery.

### Validate release content before tagging

Replace the release-PR merge-SHA requirement with content validation shared by both routes. Keep the dispatch
on the current default branch and require the requested version to agree with every owning version, consistent
release dates, and exactly one nonempty changelog section for that version with the matching date. Reject a
duplicate version section. A generic metadata check used on ordinary development builds must not suddenly
require a newly prepared release section: add an explicit requested-release validation mode to the Python owner.

`tag-release.yml` passes the requested version to that mode before obtaining write credentials. The JS tag
writer retains its version/status checks and verifies the current default-branch SHA again immediately before
tag creation. It creates an annotated tag containing the selected status and never updates an existing tag.
Both PR and direct-commit releases use the same validation; there is no bypass flag or second tagging function.
If commits land after a release PR merge, the maintainer must reconcile notes and metadata for the selected
current commit before tagging; the presence of the old PR alone grants no exception to content checks.

Update the durable recovery requirement and its delta to distinguish the dispatch's current-head selection
from manually re-issuing an unchanged historical release at its original release merge commit. After a repair
advances the default branch, the dispatch can tag that repaired head if the committed metadata still validates;
it does not refuse merely because the head is no longer the release-PR merge. It cannot select the historical
merge commit. Manual recovery remains limited to that original commit, after its failed-deployment tag was
removed and before any released artifact was published, with the same status marker and no existing-tag move.
This change does not enlarge that recovery route to arbitrary historical targets. There is still no
atomic GitHub operation tying a branch-head check and a new tag ref together; keep the final check close to the
create operation and never claim stronger atomicity than the API provides.

### Maintain Zenodo metadata through the existing release owner

Add `.zenodo.json` to `.github/release-prepared-files.json` and the exact emitted-file/digest set. Extend
`release_versions.py` to update its `version` and `publication_date` alongside the Guide and CFF before
computing the manifest. Update positional metadata-file assumptions in the owner and tests, plus fixtures
that assume exactly five metadata files or eight prepared files. Preserve all unrelated Zenodo keys; do not
replace the file with a converter export.

The Guide remains the version/date authority. CFF remains the reviewed software-citation owner for names,
ORCIDs, title, abstract, keywords and software license. Keep the corresponding Zenodo values aligned, checking
semantic representations: bare versus URL ORCIDs, `MIT` versus `mit`, and the description's CFF abstract plus
its documented software/site links. Compare structured affiliations with reviewed person/organization metadata
by identity, rather than requiring CFF's combined affiliation string to equal the JSON representation.
Other shared-field changes require an accompanying Zenodo edit or an actionable check failure; release
preparation does not invent author credits from commit statistics.

Retain curated Zenodo notes, references, related identifiers, structured affiliations and funding
acknowledgements. The FAIR-analysis authors and its CC BY 4.0 license stay on that cited work. The root MIT
software license does not replace the file-level terms in `REUSE.toml`. Do not invent structured grant IDs,
community membership or archive identifiers while maintaining this metadata.

### Validate the actual metadata consumer, not only generic syntax

Introduce a read-only citation/Zenodo checker, with matching tests, and register it once in `check_all` so
the normal CPU lane and local close-out both execute it. Use the already pinned `cffconvert` and check-tool
dependencies in `requirements-dev.txt`. Prepare release and Tag release must install those tools and run the
same checker before metadata delivery or tag creation; keep workflow code and credentials on the trusted route.
Pin the checker's direct dependency to `jsonschema==3.2.0` in `requirements-dev.txt`, within
`cffconvert==2.0.0`'s `>=3.0,<4` constraint, rather than relying on its transitive installation.

The checker validates CFF against its declared schema, validates a documented offline Zenodo-import profile,
and checks shared values. The profile must explicitly support the current importer's `version` and structured
`affiliations` fields while continuing to reject unrelated invalid shapes. Pin and document its upstream
basis; normal checks must not download a changing schema or need a live Zenodo account.

Evidence reviewed during exploration:

- [Zenodo's software description rules](https://help.zenodo.org/docs/github/describe-software/) select
  `.zenodo.json` exclusively when both metadata files exist.
- [Zenodo's developer documentation](https://developers.zenodo.org/#github) links a legacy schema that
  rejects `version` and creator `affiliations` in the staged file.
- The [current GitHub release loader](https://github.com/zenodo/zenodo-rdm/blob/1fab575d6b7eea09e5ebef5329ee366efbddc802/site/zenodo_rdm/github/release.py)
  uses the legacy-to-RDM deserializer, whose [metadata schema](https://github.com/zenodo/zenodo-rdm/blob/1fab575d6b7eea09e5ebef5329ee366efbddc802/site/zenodo_rdm/legacy/deserializers/metadata.py)
  accepts both fields. The linked legacy JSON Schema alone is therefore not the compatibility gate.
- The [CFF import subset](https://github.com/zenodo/zenodo-rdm/blob/1fab575d6b7eea09e5ebef5329ee366efbddc802/site/zenodo_rdm/github/schemas.py)
  expects a string license. Generic CFF validity alone did not establish Zenodo importability for the old tag.

Preserve the staged ROR dictionaries instead of flattening them to pass the older schema. Fixtures must prove
that the supported structure passes, invalid licenses/fields and stale metadata fail, and unknown curated
fields are never silently discarded by preparation. Local checks prove the documented profile and agreement;
only a successful remote archive proves acceptance by the deployed Zenodo service.

### Add the issued concept DOI after successful archiving

Do not add a placeholder badge during implementation. After this PR lands and the corrected new release is
published and successfully archived, retrieve its actual concept DOI from Zenodo's Versions panel or record
metadata and add the same badge/link to `README.md` and `README_en.md` through the normal documentation route.
Verify the link identifies the release series and resolves to the latest published version. Preserve specific
version DOIs for reproducible citations; do not relabel them as the concept identifier.

[Zenodo's citation guidance](https://support.zenodo.org/help/en-gb/25-citations/234-how-to-share-or-cite-a-zenodo-record)
identifies the concept DOI as the all-versions link. Its [GitHub DOI guidance](https://support.zenodo.org/help/en-gb/24-github-integration/73-can-i-pre-reserved-a-doi-before-a-github-release)
does not support pre-reservation through the GitHub integration. This badge is an explicit post-release
follow-up; a failed archive keeps it pending. Confirm the integration is enabled before live acceptance.

## Risks / Trade-offs

- **Rebase/squash duplicates:** cover all merge styles with association fixtures and real Git-history tests;
  intersect associations with eligible merged PRs rather than trusting all returned PRs.
- **More API calls or missing pages:** bound concurrency, paginate every required endpoint and fail before
  preparation on incomplete results. Never publish truncated notes as a successful release.
- **Weaker validation after removing ancestry:** require explicit release-content checks for both routes,
  plus unchanged ref, version, status, digest and immutable-tag refusals.
- **Maintainer and agent guidance diverges:** update `CONTRIBUTING.md`, `docs/deployment.md` and the guide-owned
  surfaces rule together, then regenerate its vendor outputs. Delivered tooling remains read-only.
- **Scope expands into publication:** offline tests mock GitHub mutations. Remote release acceptance is an
  operator hand-off after approved delivery; this planning change creates no tag or release.
- **Legacy validation rejects supported metadata or overlooks consumer limits:** use a documented, pinned
  importer-compatible profile with positive and negative fixtures; retain actual Zenodo acceptance as a remote
  hand-off rather than treating generic CFF validity as proof.
- **The badge precedes DOI issuance:** keep it in the post-release follow-up and require the real concept DOI
  and a verified destination in both language versions.

## Migration Plan

Deliver the reviewed changes as a normal commit on the existing topic branch and through the usual PR workflow.
Keep the PR default and manual workflow inputs compatible, changing descriptions and labels that assume a merged
release PR. Include metadata, fixtures, contribution/deployment guidance and generated native guidance in the PR.
The existing main commits, deployment repairs, archived initial change and release tag remain unchanged.

Run strict OpenSpec validation, the focused Python and JS fixtures, Python lint, native generation/integrity
checks, CFF/Zenodo validation and the repository's full `check_all` before delivery. Record environmental limits
without treating partial coverage as full close-out. Committing and pushing require their own direct order.
Then prepare the next version containing the corrections, tag and publish it under their separate approvals,
verify actual Zenodo acceptance, and complete the README badge follow-up with the issued concept DOI.
Fixes on main do not change metadata frozen in the existing release; do not repair it by moving its tag.

Rollback uses a reviewed revert before another release dispatch. It never automatically moves or deletes a
release tag or rewrites a published Zenodo record.
