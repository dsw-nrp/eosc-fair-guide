# Initial alpha candidate hand-off

Prepared 15 October 2026 for one maintainer acceptance of the complete local candidate. This document is an
operator checklist, not authorization to execute remote delivery, merge, change settings, tag or publish.
The current candidate remains on `agents/claude/guide-v0.1`; the final delivery must bind a reviewed commit SHA.

## Candidate and review coverage

The final pass covers architecture/data representation, bilingual text/source fidelity, UX/GUI/design and code
hygiene. The installed contracts are under `openspec/specs/fair-guide/`; the active portable planning package is
`openspec/changes/initial-alpha/`. Contributor instructions and both editing-skill copies describe the same flow.

| Lens | Result and review boundary |
| --- | --- |
| Architecture and data | One Guide-owned primary `id`, genuine typed `alternateIds` and stored route prefixes replace the parallel full-address register. One projection supplies API records, references, routes and chips. Refresh preserves owned identity and rejects ambiguous reassignment; external source IDs, IRIs and landing URLs retain distinct metadata roles. |
| Text | Reviewed all 11 steps in all four roles in Czech and English. Shortened authored immediate advice and removed selected repetition/superlatives. Original definitions, ledger quotations and evaluator/source labels retain their wording, language, attribution and qualifications. |
| UX and design | Compact phone navigation and role disclosures show current context; short chips retain complete links, entry titles identify the document, every matching catalogue card is present without another click, and original glossary definitions use attributed disclosures. Potential evidence coverage is derived from registered relations, separate from observed results. |
| Code hygiene | Removed unreleased route aliases and duplicate API documents, obsolete alias construction and redundant card comments. Centralized identity vocabulary, aligned docs and skill mirrors, and updated meaningful identity/refresh/advisory/browser regressions. No unrelated framework or storage migration. |

Every matching catalogue card is present without a Show more step, and print lays out every card. The terms
index moves directly to the selected letter.
Original source text remains searchable/exportable.
Saved assessment formats retain their separately required import support.

The final identity correction uses `id` consistently and removes `guideId`. All 458 imported source alternates
were compared with their recorded source IDs and full non-identity payload, with no differences; 756 source-text
and label fields also compare unchanged. Real grant, source vocabulary and ROR identifiers retain their metadata
roles. Source alternatives are flattened PropertyValue nodes in the crate and typed values in API records.

## Local verification receipt

Run from a clean dependency installation using the documented Python environment and `npm ci`:

```sh
python scripts/check_all.py --base origin/main --jobs 4 --report-dir .cache/health
npm run openspec:validate
python scripts/check_public_content.py --history
```

The machine receipt is `.cache/health/summary.md` and its dashboard; the built file preview is
`_site/index.html`, with screenshots under `.cache/screenshots/`. The full suite includes strict OpenSpec,
public-content scanning, unit tests, lint/format, content/provenance, API, profile validators and browser checks.
Before accepting, record the final run outcome and exact reviewed commit in the PR. A successful local run does
not establish remote workflow activation.

The 16 October 2026 reader-repair run passed all 25 checks in 205.1 seconds in the local Windows environment.
It includes all 264 path/role/language/width accessibility states, every matching catalogue card, the reported
desktop/phone defects and 40 Czech/English check/mode/scope PDFs with text on every page. The preview on port
8000 serves the repaired assets. This receipt does not replace the pending container or human acceptance.

The subsequent missing-link review passed 25/25 checks in 208.6 seconds. The dashboard/API now separate zero
unresolved suggestions, 79 individually reviewed unlinked mentions and zero stale decisions. Their reasons are
visible, and changed text or targets reopen review. All 18 edited content files preserve their original values
after stripping only reference markup. Initial downloads remain within the unchanged 300 KB budget.

The public-content audit scans maintained current text surfaces and local commit messages. It reports only
relative locations and rule names. It does not assert that every historical blob has been forensically audited.
No remote history rewrite is proposed or authorized. Public scholarly attribution and the explicitly approved
in-preparation model citation remain legitimate public content.

## Candidate exceptions requiring explicit disposition

- The prior candidate passed 25/25 checks inside the pinned Linux development container. The later uniform
  primary-ID correction requires a fresh container receipt before final candidate acceptance; the earlier
  daemon-unavailable note was a local sandbox limitation and is superseded.
- Live external services may be unavailable independently of the candidate. Keep the dated opt-in live receipt,
  distinguish unavailable/native missing results from failed FAIR criteria, and record the exact acceptance
  disposition. Do not substitute fabricated results or silently waive a failing acceptance probe.
  The 15 October retry returned all four citation formats for both DOI subjects, with distinct Czech ISO/APA.
  FAIR-Checker produced no attached native assessment within the 240-second browser wait; the live probe failed.
  The compact receipt is `.cache/live-release/receipt.json` (checked at 11:29:47 UTC). No successful twelve-metric
  live assessment is claimed; the deterministic evaluator fixtures remain independently checked.
- Questions requiring outside authority and approved future work are enumerated in
  [issue-handoff.md](issue-handoff.md), with owners, interim behaviour, acceptance and prepared issue bodies.
- The final production address, persistent namespace and eosc.cz embed origins require the service owner's
  decision. The current configured Pages testing address is not a claim of an agreed official production URL.

## Hand-off 1: accept the local candidate and remote payload

Review the preview, the four-lens results, verification receipt and exceptions once as a complete candidate.
Approve a specific remote payload: reviewed implementation PR, operator configuration below, issue replies and
follow-up bodies in [issue-handoff.md](issue-handoff.md). Record any accepted external-service exception explicitly.
No separate human approval is requested for each historical review checkpoint or lens.

Local changes include pre-existing staged work and the final unstaged corrections. Review the complete combined
diff before staging; do not accidentally omit either part. Deliver through a PR targeting `main` with the check
receipts, related issues, AI-involvement note and this hand-off linked. Human review/merge remains required.

Suggested PR title: **Complete the FAIR Guide initial alpha candidate**.

Suggested description: The Guide now provides the bilingual task path, conservative evidence-assisted
self-checks, sourced catalogue, software/model guidance and portable machine-readable exports. The final pass
gives catalogue records stable Guide-owned identities and compact routes, improves source-coverage hints and
phone navigation, and installs the contribution/release contracts. Validation and external exceptions are
recorded below; activation, human merges, issue posting and publication follow the explicit operator gates.
Related issues: #2, #3 and #4. AI assistance: implementation and review used AI agents; source attribution and
human acceptance remain explicit.

## Hand-off 2: operator activation and team readiness

The read-only GitHub inspection on 15 October found default branch
`01f20310966149b5bf1fb896047608f5fb8bac50`, no workflow directory on that branch, and Pages configured with
`build_type: workflow` at `https://motyc.github.io/eosc-fair-guide/`. Ruleset `24757722` exists and is active;
its only rules were deletion and non-fast-forward protection, so required reviews/checks must be configured and verified after delivery. Prepared files and a PR run
alone do not prove activation.

Complete these steps after local-candidate acceptance and remote-delivery authorization:

1. Deliver and review the implementation PR, including all eight prepared workflows and their pinned actions.
   Require the `checks` job from **Guide checks and health report**. Inspect the resulting check context as
   GitHub actually reports it before configuring the rule; do not guess a context name. Use available human
   reviewers, require PR delivery to `main`, and preserve deletion/non-fast-forward protection. Record the
   effective rules response and reviewed merge commit.
2. Install/confirm the repository-scoped App with Contents and Pull requests read/write, then configure repository
   variable `SOURCE_REFRESH_APP_ID` and secret `SOURCE_REFRESH_APP_PRIVATE_KEY`. Narrow per-job tokens are already
   declared. Keep App credentials out of PR execution and the repository; do not paste them into review receipts.
3. Verify Pages uses Actions and the `github-pages` environment admits the intended trusted deployment.
   Confirm the approved `baseUrl` and embed origins. Merge through human review, then verify `/next/` is built
   from the default branch with a testing banner, `noindex` on all HTML, and no sitemap/linkset discovery entries
   for staging. Before the first release, absence of production is expected; a default-branch push must not be
   described as an alpha production publication.
4. Verify trusted **Guide review comment**, **Source refresh**, **Live health and source watch**, and release
   workflows are present on the default branch. Under the approved remote scope, run bounded activation checks:
   summary publisher links the correct PR artifacts; source refresh creates/reuses a reviewed per-source PR;
   rejected data does not overwrite snapshots; health/watch state and keyed issue create/update/close behaviour
   correspond to that exact checked revision. Record run URLs and actual issue/PR outcomes, not just file presence.
5. Run the development-container smoke test. Post the three approved issue replies, create approved follow-ups,
   verify each resulting link, agree assignees and update the disposition ledger. Outside-owner requests remain
   proposals until those owners accept them.
6. Hand the team the verified `/next/` URL, PR/check/monitoring receipts, contributor and editing instructions,
   installed specs, issue links/owners and exceptions. Confirm ongoing work can use ordinary PRs. Complete this
   team hand-off before the alpha tag.
7. Run **Prepare release** (`prepare-release.yml`) on `main` with the version from `content/guide.toml`. Review its complete
   merged-PR changelog and aligned Guide/CFF/npm/lock/Python/crate versions and UTC release date. Human-merge the
   release PR; do not tag an implementation head or hand-edit generated output. See
   [deployment.md](deployment.md#release-preparation-and-tagging) for the owning protocol and failure rules.

## Hand-off 3: accept the deployed candidate, then authorize the tag

Accept the complete remotely prepared candidate with its checked merge SHA, deployment/monitoring evidence,
team readiness, linked dispositions and explicit exceptions. Obtain a direct order to run **Tag release** on the
current default-branch release merge with the version from `content/guide.toml`. The dispatch refuses unrelated later commits
or an existing tag; reconcile through review instead of moving a tag.

Verify that production, its downloaded artifact, draft release asset, health/API metadata, versions, date and
source commit agree, and that `/next/` still represents the default branch. Publishing the draft release remains
a maintainer action. Retain the testing notice until EOSC CZ agreement.

Archive the completed portable change only after implementation, remote delivery, issues, team hand-off and
publication gates are complete, under fresh archive approval. Installed specs must remain valid and consistent.
