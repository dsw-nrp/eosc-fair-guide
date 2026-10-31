# Restore main and triage open work

## Claude Code session (explore, plan and apply groups 1–8 in part)

- **When:** 2026-10-28 – 2026-10-29
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **Subagents used:** aiscr-investigate
- **MCP servers used:** none
- **Workflow context used:** `openspec-explore` (the maintainer confirmed the capture of the planning artifacts and,
  later, of design D8; the maintainer asked for design D10), `openspec-apply-change`, `aiscr-plan-issue` through its delivered engine; delivered
  `aiscr-planning-core`, `aiscr-quality-first-execution`, `aiscr-usage-logging`, `aiscr-model-logging` and
  `aiscr-review-conduct` rules; the native `fair-guide-content` and `fair-guide-surfaces` rules; pinned
  `npx openspec` CLI; `gh` API and GraphQL queries; Playwright render checks of the built Guide; public pages read
  to verify the Antigravity, Gemini, ORCID, ROR, RO-Crate 1.2 and Open policy finder addresses; the TU Delft and
  Harvard offboarding pages, the Harvard checklist's Zenodo record, RDMkit's pinned source and the UK Data Service
  page read to trace B2's sources to their originals.
- **What:**
  - Extended the change `restore-main-and-triage-open-work` with the triage of every open issue and the digest's
    exemption from it, and drafted the triage ledger, which the maintainer approved.
  - PR A (#144) regenerated the agent inventory and restored `main`; the maintainer merged it and the bot pull
    requests #138, #139 and #117.
  - On the change branch: the watch repeats a HEAD 400 with GET; the audit leaves the published digest out of
    triage; the Triage view filter and the `guide-health` description were applied live by the maintainer and
    recorded; the RO-Crate resource and the Sherpa source (now Open policy finder, #137) link working pages; seven
    reviewed limitations.
  - At the maintainer's request, explored why the catalogue hides recorded fields and captured the remedy as design
    D8, two `guide-experience` requirements and task group 7 (PR E): complete cards per kind, six shared conventions,
    reverse relations and a completeness test.
  - B1 (#145, merged) rebuilt Karel Berka's draft #39 for #35; its review restored the NRP licence requirement in
    `licence.14` with a reviewer's action, and #39 was closed with a link. B2 (#147) rebuilt draft #41 for #36.
  - Shaped and posted #32 (which absorbed #15, closed as its duplicate) and #5–#14, and proposed their Priority,
    Effort and Ready; the maintainer confirmed and set them, since the organisation's issue fields are not visible
    to the API.
  - Addressed the review of PR C (#146), including its pre-existing observation: the digest now shows an issue's
    Type row as inert text. The maintainer merged PR C.
  - Addressed the review of B2 (#147) with a reviewer's action: `plan.32` is qualified by institutional and funder
    policy; the handover advice cites the Harvard Longwood Medical Area offboarding checklist, and the data
    dictionary the UK Data Service's guidance on data-level documentation.
  - At the maintainer's request, added the original-source rule (design D10, task group 8, PR F): the
    `guide-knowledge-base` delta, the native content rule with its generated copies, the content model and the
    content how-to. At the maintainer's request after the review of #147, PR F also bounds quotes from sources that
    record no licence by the right of quotation (200 words, enforced by the content check) and records the Act on
    research as outside copyright with the Public Domain Mark. Its review fixes require a locator for such a quote,
    accept a licence only as a known licence address, count numbered lists and line-break hyphenation correctly,
    record the Mark on the Open Science III call rules, and merge four resources' nested citations into one each.
    Its second review narrowed the licence check to the whole address of one licence, and at the maintainer's
    request the DataCite Metadata Schema now cites its version 4.7 documentation with its licence.
  - PR E (#149) built the complete catalogue of design D8: per-kind cards with the six conventions, reverse
    relations, a corner link from each entry to its changes, the FIP declarations across the card and on a page of
    their own, and `tests/page/check_catalogue.mjs`, which fails when a record field is neither shown nor excluded with
    a reason. Its review fixes label context questions in the self-check's words, link the Guide's pages a change
    altered by their headings, repair the page test's guard against addressing the reader, drop an unused row and map,
    and add a test that every interface key the page names has its strings.
- **Impacted:** `docs/agent-tooling.md` (#144); `scripts/watch_sources.py`, `scripts/audit_repository.py`, their
  tests and the audit fixture; `.github/repository.toml`, `.github/health-watch.toml`, `docs/maintenance.md`;
  `content/resources.toml`, `content/sources.toml`, `content/provenance.toml`, `content/identifiers.toml`; the
  change's artifacts, including the new `guide-experience` delta, and `triage.toml`; on B1's and B2's branches the
  station files, `content/guide.toml`, `content/provenance.toml`, `content/identifiers.toml` and
  `tests/test_watch.py`, and on B2's also `content/ledger.toml` and `content/sources.toml`; on PR F's branch
  `.agents/guide/rules/fair-guide-content.md`, its generated copies, the guide region of `CODEX.md`,
  `docs/content-model.md`, `docs/how-to/edit-content.md`, the new `guide-knowledge-base` delta,
  `scripts/check_content.py`, `tests/test_scripts.py`, the minimal fixture's ledger, `content/sources.toml`,
  `content/resources.toml`, `content/ledger.toml`, `content/provenance.toml` and `content/identifiers.toml`; on PR
  E's branch `assets/js/catalogue.js`, `assets/js/catalogue-view.js`,
  `assets/js/core.js`, `assets/js/views.js`, `assets/css/app.css`, `content/ui.toml`, `content/icons.toml`, ten
  vendored icons, `tests/page/check_catalogue.mjs`, `tests/page/check_page.mjs`, `tests/test_scripts.py`,
  `scripts/check_groups.json`,
  `docs/design.md`, `docs/content-model.md` and the `guide-experience` delta, D8 and tasks 7.3, 7.5 and 7.7; the bodies
  and provenance comments of the shaped issues; this usage entry.
- **Corrections:**
  - The maintainer put #70 out of scope, confirmed Karel Berka as the drafts' author with his GitHub account and
    address, defined the `Generic` milestone, and reported that the Sherpa API page refuses people as well, which
    turned a planned limitation into a source correction.
  - A `[[pending]]` entry only accepts documented deployment steps, so the two Project settings followed #141's
    route: applied live first, then declared and recorded.
  - `CITATION.cff` credits only software authors, so Karel Berka is credited through the Guide's `contributors`.
  - A watch test fixed the link count at 673; it now derives its expectations from the inventory.
  - The maintainer judged a catalogue fix limited to content changes insufficient and asked for complete cards per
    kind, consistent across kinds.
  - The review of PR C: a 403 does not establish bot protection, so the OpenAI limitation states only the refusal;
    the station rule stays in its existing requirement instead of a second ADDED one; #137's closure reason names
    its actual basis; a test ties the audit's digest identity to the publisher and renderer; and this entry was
    brought up to date. The maintainer asked for the review's pre-existing observation to be fixed as well (design D9).
  - Shaping found fixtures and tests for both whole evaluator mappings, so #14's effort fell from Medium to Low.
  - The maintainer asked #11 to help readers with licensing caveats across research outputs without naming a
    project, #12 to treat GA ČR, TA ČR, AZV ČR and Horizon Europe in one wave, and the agent to propose Priority,
    Effort and Ready for each shaped issue.
  - B2's handover advice first cited TU Delft's offboarding page. The maintainer asked for its original, the
    Harvard checklist, whose wording added who maintains the data next and introducing the checklist when people
    join; asked to keep the data dictionary with a reference of its own; and made citing the original a Guide rule
    (design D10).
  - The review of #147 called a 151-word quote from a page without a licence too long for "short passages". The
    maintainer asked to ease the rule rather than the quote: research quotes by right, laws and many other documents
    are outside copyright, and a length limit should keep the balance (D10).
  - On PR E the maintainer dropped the Made by row, which would repeat the byline; moved an entry's changes from a
    growing row to a corner link into the catalogue's list of changes; gave the FIP declarations the card's full width
    and a page of their own; and ruled out labels that address the reader, so the self-check's "you" is named as the
    researcher.
  - The review of PR F found that four resources kept their licence, authors or version DOI in a nested citation
    nothing read, that the locator and the counting were not enforced as written, and that any licence value lifted
    the bound. The maintainer chose to merge the nested citations and confirmed the Open Science III call rules as
    an administrative document outside copyright, so they record the Public Domain Mark instead of a narrower
    content model.
- **Merge route:** #144 and #146 were merged through the administrator bypass with green `checks`, departing from
  step 2 of `docs/runbooks/merge.md` as design D2 records.
- **Verification:**
  - the HEAD 400 test failed before the fix and passes after it, and the digest-exemption tests failed before the
    audit change; the digest identity test fails when the renderer's marker or the bot login drifts; the Type-row
    test failed while a backtick could end the code span; `tests/test_watch.py` and `tests/test_audit_repository.py`
    pass;
  - a maintainer's live audit of the Project and labels reports no drift and recognises only #140 as the digest;
  - B1's 16 changed items and B2's four new items render in Czech and English at phone width, and the built data
    holds no retired ID;
  - B2's review fix renders its changed items in Czech and English with no problem in eight item views;
  - PR F's rule appears in all five generated copies and only inside the guide region of `CODEX.md`;
    `python scripts/generate_agent_surfaces.py --check`, `python scripts/check_agent_surfaces.py`,
    `python scripts/check_sibling_delivery.py` and `python scripts/check_docs.py` pass;
  - the quotation test fails at 201 words and passes at 200 and with the Public Domain Mark; on 29 October, before
    #147 merged, its quote counted 145 words and the longest quote on `main` from a source without a licence 139 by
    the shipped counter (140 by a whitespace split, the figure first recorded here);
  - PR F's review tests fail with the former word count and with a check that accepts any licence, and pass with the
    fixes; on 29 October the content check reported no error, five bounded quotes remained, the longest 19 words, and every clause
    among them has a locator; FORCE11's licence and authors, the pilot's version DOI, date and licence in Zenodo and
    the CoreTrustSeal sentence were checked at their sources, while the CESSDA guide was offline for migration;
    the second review's test fails with the former prefix match, which accepted a home page and trailing text, and
    the DataCite schema's title, DOI, authors and CC BY 4.0 match its DataCite record and documentation;
  - PR E's catalogue test fails on cards that do not mark a field and passes on the final cards; the changed cards
    render in Czech and English, at phone width and in print, with no sideways scroll; its review's page assertions
    fail without the code fixes and pass with them, and the key test fails while `catalogue.assessmentContext` is
    undefined;
  - `python scripts/check_all.py` passes 36/36 for #144, for B1, for B2, for B2's review fix rebased onto `main`,
    for the change branch, for PR E and its review fix, and for PR F and both its review fixes; one full run of PR E's
    review fix failed the shared browser-slot timing test in `tests/runtime.test.mjs`, which passed alone twice and in
    the next full run; strict OpenSpec validation passes 6/6.
- **Close-out (29 October):** 22 of 57 tasks ticked. PR C's review and merge (4.11 and 4.12) are done and, as the tasks header
  says, are ticked in PR D. Open then: the review and merge of B2 (#147), PR E (#149) and PR F (#148), the rebuilds B3–B4,
  the digest actions outside the repository, the shaping of the remaining issues in the ledger, and the integration
  check after the next watch run.
- **Later in the session (29–30 October):** the maintainer merged B2 (#147). B3 was rebuilt from draft #40 for #37
  as `2ba195d`, and at the maintainer's request a second commit, `048a814`, added the Library of Congress site
  Sustainability of Digital Formats as a catalogue guide with the clause `LOC-DIGITAL-FORMATS.01`; the full suite
  passed 36/36 with both. B3's branch had been created from `origin/main` and kept it as its upstream, so a push
  from the editor sent `2ba195d` straight to `main` (design D11). The session found it, proposed the restoration and
  the prevention, and stopped at its usage limit before acting.

## Kilo session (restore `main` after the direct push)

- **When:** 2026-10-30 – 2026-10-31
- **Agent / runtime:** Kilo (VS Code extension)
- **Model / backend:** anthropic/claude-opus-5-5
- **Subagents used:** none
- **MCP servers used:** none
- **Workflow context used:** resumed from the Claude Code session's transcript; delivered `aiscr-planning-core`,
  `aiscr-quality-first-execution`, `aiscr-usage-logging` and `aiscr-model-logging` rules; the native
  `fair-guide-content` and `fair-guide-surfaces` rules; `aiscr-plan-issue` through its delivered engine; `gh` API
  queries; GitHub's documentation on ruleset bypass modes; a Playwright read of the live `/next/` catalogue; the
  DataCite records and the survey PDF read for the two versionless licences; for B4, RDMkit's *Data publication* page
  at its pinned revision and the Industrial Property Office's consolidated text of Act No. 527/1990 Coll.; live
  requests to OSI and Creative Commons licence addresses for the sixth review.
- **What:**
  - Restored `main` to `bed3284`: the maintainer ran the leased force push, because the Claude Code session's
    runtime had refused it and the agent did not repeat it by another route. The deployment and publication of
    `bed3284` passed, and the preview no longer carries B3.
  - Reopened #37 with the approved comment; opened B3 with the Library of Congress commit as #151, after the
    maintainer approved its body; closed draft #41 with a link to #147; pushed the approved review fix `d1e6c4c` to
    PR E (#149). Every push named its remote branch explicitly.
  - After the maintainer set the bypass of `Main branch protection` to **For pull requests only**, recorded it as
    design D11 and task group 9, declared it in `.github/repository.toml` and recorded it in the audit fixture.
  - Pruned stale remote-tracking refs and fast-forwarded local `main`; the maintainer deleted the four local branches
    whose work had merged, since the runtime refuses `git branch -D`.
  - Addressed the third review of PR F (task 8.8): a recorded licence must be the one canonical address of its
    licence, so its deed, legal-code and slash-less forms are refused and the message gives the canonical form; the
    native rule with its generated copies, the content model, the `guide-knowledge-base` delta and D10 say so; D10
    states the pre-change maximum as 139 words, the shipped counter's figure.
  - Addressed the fourth review of PR F (task 8.9): a recorded licence must name a known licence (Creative Commons
    names and tools, GNU families, or a reviewed list of SPDX identifiers), with the Creative Commons version
    required and any of its ports accepted; the survey and the policy manual record the CC BY 4.0 their sources
    state; D11's bypass has its row in the settings table of `docs/deployment.md`.
  - Verified task 7.10 on the live preview: a content change's card names its person with an ORCID link and its tools
    with their kinds, in Czech and English and at phone width; checked task 4.12: the Project and labels audits
    report no drift, and #137 is closed.
  - Shaped and posted #26, #28, #29 and #30 after the maintainer approved their archives and bodies; closed #27 as
    not planned at the maintainer's decision and recorded it in the triage ledger.
  - Posted the approved decision comment on #140 and reported the three dead tool addresses to the KNAV catalogue
    (Open-Science-Department-KNAV/Data-Management-Tools-Catalogue#1).
  - Answered B3's review (#151) with a reviewer's action `2026-10-30-formats-review` and four new clauses from general
    sources: `publication.30` starts from the repository's instructions, with packaging as an example
    (`RDMKIT.publication.01`, `RDMKIT.transfer.01`); `process.04` cites the Swedish National Data Service's guide on
    synthetic research data (`SND-SYNTHETIC.01`); `process.03` cites the Data Carpentry lesson on spreadsheets
    (`DC-SPREADSHEETS.01`). The maintainer corrected the Czech and merged #151, which closed #37.
  - Opened #152 for advice resting on a contributor's expert judgement, which the maintainer asked for during B3's
    review.
  - Shaped and posted #31, #33, #43, #80 (re-scoped to the OpenSSF Best Practices badge) and #136, and shaped #150 by
    direct edit at the maintainer's request.
  - Opened the digest's tracked tasks (task 5.1): #153 and #154 for the KNAV catalogue's dead addresses, #160 for the
    FIP Dashboard's unresolved repository address, which the Dashboard team tracks there; and #155–#159, one keyed
    task per FAIR Champion candidate, closed as not planned under the selection review's existing decision, since the
    digest reads one finding key per task. Commented on #140 that ELAN needs no task.
  - Addressed the fifth review of PR F (task 8.10): the reviewed licence lists are named on every surface, with
    separate lists of GNU paths, OSI pages and SPDX entries; the triage ledger reflects #27's closure.
  - Rebuilt B4 from Karel Berka's draft #42 for #38 (tasks 3.7–3.8) and, at the maintainer's request, settled the
    claims its clauses did not state before opening #161, with a reviewer's action `2026-10-31-ip-errata-review`:
    `metadata.05` names the funder and grant number (`CDIF.REC6`) instead of a RIV linkage; `licence.31` gives three
    steps resting on RDMkit's *Data publication* page (`RDMKIT.publication.02`) and on the novelty and priority
    sections of Act No. 527/1990 Coll. (`LAW-527-1990.5`, source `law-527-1990`); `publication.05` follows the NRP
    change policy and RDMkit on updating published entries (`RDMKIT.publication.03`). The maintainer corrected the
    Czech of `publication.05` and merged #161 as `1cdbd1d`, which closed #38.
  - Merged `main` with B4 into PR F and addressed its sixth review (task 8.11): OSI pages are named by OSI's
    canonical lowercase slugs, SPDX identifiers stay for SPDX entries, Creative Commons versions are the published
    ones with a port only before 4.0 and BY-NC-ND 1.0 under its published name `by-nd-nc`, D10 counts B3's seventh
    bounded quote, and the native rule names the three lists. The Patent Act records the Public Domain Mark, as the other laws do, extending the official-works action.
- **Impacted:** `main` on GitHub; issues #26–#31, #33, #37, #38, #43, #80, #136, #140, #150, #152–#160; pull
  requests #41, #42, #148, #149, #151 and #161; the issue report in the KNAV catalogue; the `Main branch protection`
  ruleset (applied by the maintainer); on B3's and B4's branches the station files, `content/ledger.toml`,
  `content/sources.toml`, `content/provenance.toml` and `content/identifiers.toml`; on PR F's branch
  `.github/repository.toml`, `tests/fixtures/repository-audit.json`, `scripts/check_content.py`,
  `tests/test_scripts.py`, `.agents/guide/rules/fair-guide-content.md` with its generated copies and the guide region
  of `CODEX.md`, `docs/content-model.md`, `docs/deployment.md`, `content/sources.toml`, `content/resources.toml`,
  `content/provenance.toml`, the change's `design.md`, `proposal.md`, `tasks.md`, `triage.toml` and
  `guide-knowledge-base` delta, and this usage entry.
- **Corrections:**
  - The maintainer stated that B3 should not have reached `main` without a pull request and asked for `main` to be
    moved back rather than reverted, and for the prevention to be logged in this change instead of a new one.
  - The maintainer asked for `main` to be fixed first and escalated when the agent could not act itself; the lease in
    the earlier proposed command named a wrong commit, which would have refused, and was corrected before it ran.
  - For the third review of PR F, the maintainer chose one canonical address per licence over accepting every
    published form; for the fourth, a reviewed list of SPDX identifiers over a vendored SPDX licence list.
  - The maintainer closed #27, since no national FAIR benchmark will exist, and held the FIP Dashboard report, which
    the Dashboard's own issue and its responsible person, Marek Suchánek, cover.
  - For B3's review, the maintainer rejected citing repository-specific instructions for general advice on packaging
    files and on spreadsheets, and asked for more generic sources or advice reworded so that an example does not carry
    the claim; the maintainer also corrected the Czech wording of `publication.30` and `process.03`.
  - The maintainer said that the FIP Dashboard team tracks the dead repository address directly on the Guide's task,
    not in an issue of its own, so #160 says so.
  - For B4, the maintainer asked for the claims the comparison had found unsupported to be solved before review
    rather than listed for review to restate, and changed the Czech "stahujte" to "znepřístupněte" in
    `publication.05`.
  - For the sixth review of PR F, the maintainer asked to fix BY-NC-ND 1.0's published name as well, which the agent
    had proposed to leave as a residual.
- **Verification:**
  - `git ls-remote` reports `main` at `bed3284`, and only B3's branch contains `2ba195d`; **Deploy the verified site**
    run 40982282070 passed its full checks and **Publish the verified site** run 40982793541 succeeded for
    `bed3284`; the crate at `/next/` lists no action of B3;
  - the ruleset reports the bypass `RepositoryRole 5 pull_request` and `current_user_can_bypass` as
    `pull_requests_only`; `python scripts/audit_repository.py --check-config` passes and a maintainer's
    `python scripts/audit_repository.py --section rulesets` reports no drift; `tests/test_audit_repository.py` fails
    with the fixture's former `always` and passes with `pull_request`;
  - #151 closes #37 at head `048a814`;
  - the licence boundary test fails with the former message and, once the message changed, with the former pattern,
    which accepted the legal-code form; it passes with the canonical pattern; `python scripts/check_content.py`
    reports no error, so every recorded licence is canonical; `LAW-328-2025.83.2` counts 139 words by
    `quote_words`;
  - the fourth review's boundary matrix fails against the former pattern and passes with the known-licence pattern;
    `python scripts/check_content.py` then reported only the two versionless records, and no error once they record
    CC BY 4.0; at this head six quotes are bounded, the longest `UKDS-DATA-LEVEL.01` at 145 words;
  - each shaped body passed `verify-composition` before posting; the `/next/` card was read in Czech and English at
    1280 px and in English at 360 px, with no sideways scroll;
  - B3's review fixes passed `python scripts/check_all.py` (35 of 36, REUSE on the untracked transcript), and the
    changed items render in Czech and English at 360 px; #151 merged as `93dd3f1`, whose deployment and publication
    passed;
  - every posted body (#26, #28–#31, #33, #43, #80, #136, #150, #152–#154, #160) passes the planned-issue readiness
    check, and a maintainer's `python scripts/audit_repository.py --section project` reports no drift and no
    attention finding;
  - the fifth review's boundary matrix fails against the former pattern and message and passes now; GNU, OSI and
    SPDX addresses were checked on 30 October 2026: OSI has no page for `ODbL-1.0` or `ODC-By-1.0`, and GNU
    redirects `gpl-2.0.html`, `lgpl-2.1.html` and `fdl-1.2.html` to `old-licenses/`; with B3 merged, seven quotes are
    bounded, `LOC-DIGITAL-FORMATS.01` adding one of 45 words, and the longest is still `UKDS-DATA-LEVEL.01` at 145;
  - B4's review fixes passed `python scripts/check_all.py` (35 of 36, REUSE on the untracked transcript), with
    `check_content.py --base origin/main` and `check_duplicates.py` reporting no error; the three items render in
    Czech and English at 360 and 1280 px with no sideways scroll, and their links open the glossary and catalogue
    entries; #161 merged as `1cdbd1d`;
  - the sixth review's boundary matrix fails against the former pattern on twelve addresses and passes now; on 31
    October OSI named `mit`, `apache-2-0`, `bsd-2-clause`, `bsd-3-clause`, `eupl-1-2` and `mpl-2-0` as its pages'
    canonical addresses, Creative Commons answered 404 for `by/9.9/`, `by/3.0/xyz/` and `by-nd-nc/2.0/` and 403 for
    an unported `by/2.1/`, redirected `by/4.0/xyz/` and `by/4.0/cz/` to the 4.0 deed, and redirected
    `by-nc-nd/1.0/` and its ports to `by-nd-nc/1.0/`; with B4 merged and the Patent Act
    marked, seven quotes remain bounded, the longest still `UKDS-DATA-LEVEL.01` at 145.
- **Close-out:** on 31 October, 22 of 65 tasks are ticked; PR D records the ticks of the work done since, including
  task groups 5, 6 and 9, B3 (3.5–3.6) and B4 (3.7–3.8). PR E (#149) merged as `45bf1eb`, B3 (#151) as `93dd3f1`
  and B4 (#161) as `1cdbd1d`. Open: PR F's review and merge (8.7), closing draft #42, and the integration check after
  the next watch run (group 10). For this round, `npm run openspec:validate`, `python scripts/check_usage.py` and
  `python scripts/check_all.py`: see the verification of its commit.
