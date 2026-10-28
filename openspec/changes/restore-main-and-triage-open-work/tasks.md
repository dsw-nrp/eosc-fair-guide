# Tasks

Tasks marked **Human hand-off** or **Human decision** need the maintainer's approval, action or choice. Local checks
alone do not complete them.

- **Approval before any outside write.** Every commit, push, pull-request body and comment, and every write to GitHub,
  the Project or an upstream service, is shown to the maintainer and approved before it is made (design D4). This
  includes every issue body, field, parent link and closure in group 6.
- **Merge route.** The maintainer's own pull requests merge as design D2 describes.
- **Where ticks are recorded.** Ticks are recorded on the change branch. Work finished before PR C merges is ticked
  there; the rest is ticked in PR D.

## 1. Restore `main` (PR A)

- [x] 1.1 From the latest `main`, create `agents/claude/regenerate-agent-inventory` and run
      `python scripts/generate_agent_surfaces.py`.
      Verify:
      - `git diff --stat` lists only `docs/agent-tooling.md`;
      - the only changed row is `aiscr-plan-from-issue`, which gains `.agents/scripts/github/github_references.py`;
      - `python scripts/generate_agent_surfaces.py --check`, `python scripts/check_agent_surfaces.py` and
        `python scripts/check_sibling_delivery.py` each report no difference.
- [x] 1.2 Run `python scripts/check_all.py`, then commit, push and open PR A naming this change, after the maintainer
      approves the commit message and PR body. Verify that the PR's `checks` pass.
- [x] 1.3 **Human hand-off:** record acceptance on PR A and merge it through the administrator bypass (design D2).
      Verify that the **Deploy the verified site** run for the merge commit passes `agent-generation` and that
      `/next/` names the merge commit.

## 2. Bot pull requests

- [x] 2.1 **Human hand-off:** review and approve as code owner:
      - #138 and #139 as dependency updates;
      - #117 as content: the added DOI `10.17616/R31NJO1M` resolves to the Data Catch-all Repository's re3data record.

      Verify that each shows an approving code-owner review.
- [x] 2.2 Queue #138, #139 and #117 one at a time with **Merge when ready**. After each merge, wait for any Dependabot
      rebase and its checks. Verify that each shows as merged with a passing queue result.
- [x] 2.3 Verify on `main`:
      - no `setup-python` v7.0.0 pin remains under `.github/workflows/`;
      - `requirements-dev.txt` pins ruff 0.17.2;
      - `content/snapshots/re3data.toml` records `retrieved = 2026-10-26`.

## 3. Rebuilt content (PRs B1–B4)

- [x] 3.1 Build B1 for #35 from #39, on a branch from the latest `main` (design D3):
      - apply only #39's station changes, in commits that end with
        `Co-authored-by: Karel Berka <karel.berka@upol.cz>`;
      - add the `karel-berka` person record with `github = "KarelBerka"`, the `upol` organisation and the instrument
        records, with `antigravity` at `https://antigravity.google/`;
      - run `python scripts/register_ids.py`, and retire the merged IDs by hand;
      - add Karel Berka's provenance action with his draft's `endTime`;
      - list him under `[guide] contributors`;
      - make the watch coverage test independent of the link count.

      Verify:
      - `python scripts/check_all.py` passes;
      - `python scripts/contributors.py` reports no unresolved identity and no action whose agent made none of its
        commits;
      - the diff contains no file under `openspec/` or `.agents/reports/usage/`;
      - the changed stations read correctly in the built Guide, in Czech and English, at phone width and in print.
- [ ] 3.2 **Human hand-off:**
      - review B1's content against its cited clauses and the tone rules;
      - decide whether the review changed what the Guide says; if it did, add the reviewer's action covering exactly
        the changed items (design D3) and rerun `python scripts/check_all.py`;
      - approve its PR body, which carries `Closes dsw-nrp/eosc-fair-guide#35`;
      - record acceptance and merge it (design D2).

      Verify that #35 is closed, then close #39 with a link to B1.
- [ ] 3.3 Build B2 for #36 from #41 on the latest `main`, without the shared records. Verify as in 3.1, and that
      `plan.31`, `plan.32`, `collect.22` and `collect.23` are registered.
- [ ] 3.4 **Human hand-off:** review B2 as in 3.2, including the `plan.32` claim against `LAW-328-2025.83`, then
      merge it. Verify that #36 is closed, then close #41 with a link to B2.
- [ ] 3.5 Build B3 for #37 from #40 on the latest `main`. Verify as in 3.1, and that `publication.30` is registered.
- [ ] 3.6 **Human hand-off:** review B3 as in 3.2, including the claim citing `LAW-328-2025.83.3`, then merge it.
      Verify that #37 is closed, then close #40 with a link to B3.
- [ ] 3.7 Build B4 for #38 from #42 on the latest `main`. Verify as in 3.1, and that `licence.31` is registered.
- [ ] 3.8 **Human hand-off:** review B4 as in 3.2, including the `licence.31` patent advice against
      `LAW-328-2025.83.5`, then merge it. Verify that #38 is closed, then close #42 with a link to B4.

## 4. Watch fallback, digest exemption and digest fixes (PR C, the change branch)

- [x] 4.1 On `agents/claude/restore-main-and-triage-open-work` from the latest `main`, add tests to
      `tests/test_watch.py` that patch `urllib.request.urlopen` (no network):
      - HEAD 400 followed by GET 200 gives 200 with the methods `HEAD then GET`;
      - HEAD 403 followed by GET 403 gives 403 with `HEAD then GET`;
      - HEAD 429 sends no GET;
      - HEAD 404 sends no GET.

      Verify with `python -m unittest discover -s tests -p test_watch.py` that the 400 test fails before 4.2 and the
      other tests pass.
- [x] 4.2 In `scripts/watch_sources.py`, add 400 to the HEAD statuses that `fetch` repeats with GET, and update the
      docstring of `fetch`. Verify that the tests from 4.1 and the rest of `tests/test_watch.py` pass.
- [x] 4.3 In `tests/test_audit_repository.py`, give the Project item fixture an author and add tests (design D7):
      - the digest (the `Bot` `github-actions`, a body starting with `<!-- fair-guide-digest -->`) waiting 40 days in
        Needs triage, and in Ready without the planned-issue shape, yields no `triage` or `ready` finding;
      - the digest without an Issue Type still yields a `type` finding;
      - an issue by a person that carries `guide-health` and starts with the marker, waiting 15 days, yields a `triage`
        finding.

      Verify with `python -m unittest discover -s tests -p test_audit_repository.py` that the tests of the first
      bullet fail before 4.4 and the others pass.
- [x] 4.4 In `scripts/audit_repository.py`, add the issue's author to the Project items query and skip the triage-age
      and Ready checks for the digest, identified as in design D7; update the module docstring. Verify that the tests
      from 4.3 and the rest of `tests/test_audit_repository.py` pass, and that a maintainer's
      `python scripts/audit_repository.py --section project` still runs without an error.
- [x] 4.5 **Human hand-off:** apply live, in the Project UI and the label settings, the Triage view filter
      `is:issue status:"Needs triage" -label:guide-health` and the `guide-health` description "The maintenance digest
      the watch publishes; reserved for it" (design D7). Then record them:
      - in `.github/repository.toml`, declare the filter and the description;
      - in `tests/fixtures/repository-audit.json`, record both live values;
      - in `docs/maintenance.md`, update the Triage view's row, list `guide-health` as reserved for the digest and
        state that the audit does not judge the digest's triage age or readiness.

      Verify that `python scripts/audit_repository.py --check-config`, `python scripts/check_docs.py` and
      `tests/test_audit_repository.py` pass, and that a maintainer's
      `python scripts/audit_repository.py --section project --section labels` reports no drift.
- [x] 4.6 In `content/resources.toml`, change the `ro-crate` resource address to
      `https://www.researchobject.org/ro-crate/specification/1.2/`. In `content/sources.toml`, move
      `sherpa-object-retrieval-api` to `https://openpolicyfinder.jisc.ac.uk/help/developers/api-types/object-retrieval-api`
      with that page's title, keeping its ID (#137, design D4). Keep `RO_CRATE` in `scripts/build_crate.py`, and add
      one provenance action covering both. Verify that `python scripts/build_site.py` succeeds and that the built
      resource and source link the new addresses.
- [x] 4.7 **Human decision:** write the `reason` for each of the seven limitations listed in design D4, and confirm
      the reviewer's person ID. Verify that every reason is recorded before 4.8 starts.
- [x] 4.8 Add the seven `[[limitation]]` entries to `.github/health-watch.toml`. Each takes the digest's key,
      outcome and evidence, the reason from 4.7, `reviewed` set to the review date and the offered `reviewBy`.
      Verify that `python scripts/watch_sources.py check-config` passes.
- [x] 4.9 Write one usage entry for this change under `.agents/reports/usage/`, named
      `usage-YYYY-MM-DD-restore-main-and-triage-open-work.md` with the date of its first `When`. It records the work
      done so far and the merge-route departure from design D2. Run `npm run openspec:validate`,
      `python scripts/check_usage.py` and `python scripts/check_all.py`. Once all three pass and the maintainer
      approves the PR body, which carries `Closes dsw-nrp/eosc-fair-guide#137`, open PR C.
- [ ] 4.10 **Human hand-off:** review PR C, record acceptance and merge it (design D2). Verify that the deployment's
      full checks pass for the merge commit.
- [ ] 4.11 After PR C merges, verify that a maintainer's `python scripts/audit_repository.py --section project
      --section labels` reports no drift against `main`, that the digest no longer appears in the Triage view, and
      that #137 is closed.

## 5. Digest actions outside the repository

- [ ] 5.1 **Human hand-off:** from the digest's **Track as task** links, open tracked tasks for:
      - `data.narodni-repozitar.cz`;
      - the CESSDA DMEG address;
      - the LUMI address;
      - one review of the five FAIR Champion candidates.

      Triage each to Ready as 6.4 and 6.5 describe. Verify that each task exists, is Ready and passes the audit's
      Ready check.
- [ ] 5.2 **Human hand-off:** report the dead addresses upstream.
      - To the KNAV tools catalogue:
        - `data-management-expert-guide`: the root address `https://dmeg.cessda.eu/` answers;
        - `lumi`: the address is gone;
        - `elan`: it moved to `https://archive.mpi.nl/tla/elan`.
      - To the FIP Dashboard source: `cesnet-invenio`, whose domain no longer resolves.

      Verify that each report is linked from its task in 5.1, or for ELAN from a comment on #140.
- [ ] 5.3 **Human hand-off:** post one approved comment on #140 recording these decisions:
      - no action for the ÚFE job advert and the 11 November webinar;
      - heslar and nkr wait for the next scheduled refresh;
      - `asep.lib.cas.cz` and `data.eli-laser.eu` are decided after the next run;
      - the Issue Type lines for #115–#135 and the `PR - authored` sort clear on their own.

      Verify that the comment is posted.
- [x] 5.4 Run a maintainer's `python scripts/audit_repository.py --section project`. Verify that it reports no drift
      for the `PR - authored` view, whose expected sort #141 changed to the live `Status asc, Title asc`.

## 6. Issue triage

- [x] 6.1 Draft `openspec/changes/restore-main-and-triage-open-work/triage.toml` (design D6): one `[[issue]]` entry
      for every open issue except #140, with the fields D6 names, proposed values citing the thread or the files the
      issue names, and the known inputs D6 lists. #35–#38 are entered as closed by B1–B4 with `shape = "none"`.
      Verify that the file parses with `tomllib`, that its numbers equal the open issues from `gh issue list --state open`
      minus #140, and that every entry other than `keep` has a `reason`.
- [x] 6.2 **Human decision:** review the ledger and set the final decision, Priority, Effort, milestone and shaping
      route for each issue. Verify that the approved ledger is committed on the change branch.
- [ ] 6.3 **Human hand-off:** apply the ledger's closures, merges and parent changes. Each closure carries a comment
      with its reason and links its successor where one exists; a merged issue's content moves into the issue that
      absorbs it when that issue is shaped. Verify on GitHub that each entry's state and parent match the ledger.
- [ ] 6.4 **Human hand-off:** shape every issue whose route is `full` or `light` with `/aiscr-plan-issue`, in ledger
      order and in batches of about five. Each original is archived and each body posted only after the maintainer
      approves both digests; re-scoped issues take their new scope; a body keeps its language and replaces links to
      `motyc/eosc-fair-guide`. Verify that every shaped body passes the planned-issue readiness check the audit uses
      and that its provenance comment exists.
- [ ] 6.5 **Human hand-off:** for each shaped issue, set Priority, Effort and milestone from the ledger, then its
      Status to Ready. Verify that a maintainer's `python scripts/audit_repository.py --section project` reports no
      `ready` finding.
- [ ] 6.6 Verify the triage end state with a maintainer's `python scripts/audit_repository.py --section project`:
      - every ledger issue and every task from 5.1 is Ready or closed;
      - no ledger issue and not the digest has a `triage`, `ready` or `type` finding.

      Record in the usage entry any issue that a weekly run reported as overdue triage before it was Ready.

## 7. Complete catalogue (PR E)

- [ ] 7.1 After PR C merges, branch `agents/claude/complete-catalogue` from the latest `main`. Give each catalogue kind
      a declared list of the fields its entry shows, and add a test that reads the built crate and fails when a
      catalogue entity carries a property that its kind neither declares shown nor excludes with a reason (design D8).
      Verify that the test fails on the current cards and names the fields D8 lists as hidden, and that it passes for
      the kinds D8 leaves unchanged.
- [ ] 7.2 Implement the six conventions in the shared card code: byline and rows for who made and who runs an entry; a
      Licence row and a quoted-text licence line named from the data; dates in the details line; one status badge
      helper with icon, text and as-of date; qualified lists as rows, grouped by kind, folded when long and built when
      first opened. Add every new label and icon to `content/ui.toml` in Czech and English. Verify that unit or page
      tests cover the badge helper and a folded list, which opens by keyboard and is built only when opened, and that
      `python scripts/check_content.py` passes.
- [ ] 7.3 Build the content-change entry: the agent's byline with an ORCID link unless the person opted out, Made by,
      Tools with each instrument's kind and recorded version, and Consulted and Changed grouped by kind with every item
      linked to its entry, station or page. Verify with page tests on `2026-10-16-initial-state` (143 consulted,
      1,374 changed) and `2026-10-18-station-dedup` that the names, tools, groups and counts show and every link
      resolves.
- [ ] 7.4 Build the check-question entry: the explanation, Who puts it right, Applies, Pre-filled from with its
      limits, Group, For NRP profile, Mentions, and the rare fields where present. Verify with a page test on
      `dataset.01` and on one CDIF question.
- [ ] 7.5 Build the FIP and enabling-resource entries: the authoring community's byline, status, version, date and
      keywords, the Declarations table, and Based on for FIP profiles; FAIR data type, coverage, Provided by and
      Declared in for enabling resources. Verify with a page test on the ČSDA profile (18 declarations: 17 in use, 1
      planned) and on one resource it declares.
- [ ] 7.6 Reshape the other cards to the conventions: the Licence row on resources and sources; the quoted-text licence
      line on KNAV tools, life-cycle stages, terms and requirement guidance; the infrastructure host as Operated by;
      the test health badge from the shared helper; the criterion's Covers row; the life-cycle stage's Corresponds to
      row. Verify with a page test per reshaped kind.
- [ ] 7.7 Add the reverse relations: Pre-fills on tests and criteria, Declared in on enabling resources, Replaced by and
      Replaces on requirements, and a Changes row on every entry covered by provenance. Verify with page tests for each
      pair, and that the completeness test from 7.1 now passes for every kind.
- [ ] 7.8 Reword the paradata decision in `docs/design.md`, and update any description of the catalogue's cards in
      `docs/content-model.md`. Verify that `python scripts/check_docs.py` passes and that the about page's statement
      (`content/pages.toml:179`) now matches the catalogue.
- [ ] 7.9 Run `python scripts/check_all.py`, and inspect every changed card in Czech and English, at phone width and in
      print. Commit, push and open PR E after the maintainer approves the commit messages and PR body. Verify that the
      PR's `checks` pass.
- [ ] 7.10 **Human hand-off:** review PR E, record acceptance and merge it (design D2). Verify that the deployment's
      full checks pass and that `/next/` shows a content change's person and tools in the catalogue.

## 8. Integration check and close-out (PR D)

- [ ] 8.1 **Human hand-off:** after groups 1–7 are done, start **Live health and source watch** with both the audit
      and the watch selected, or wait for the scheduled run. Verify in the rebuilt #140:
      - the seven limitations appear as known;
      - the survey PDF and the RO-Crate address are no longer under **Needs triage**;
      - the findings from 5.1 show as tracked;
      - **Project and settings** lists neither #115–#135, the view sort, the digest nor any ledger issue.
- [ ] 8.2 Using that run's results, decide on the two remaining hosts:
      - if `asep.lib.cas.cz` still fails, open one host task and triage it to Ready as 6.4 and 6.5 describe;
      - if `data.eli-laser.eu` still fails, add an `unavailable` limitation with the maintainer's reason in PR D.

      Verify that the next digest lists neither host under **Needs triage**.
- [ ] 8.3 Verify the end state:
      - #39–#42 are closed;
      - #117, #138 and #139 are merged, and so is PR E;
      - #35–#38 are closed;
      - the end state of 6.6 still holds;
      - the latest deployment of `main` passed.
- [ ] 8.4 On a branch from `main`:
      - tick this task list;
      - extend the usage entry with the work since PR C;
      - run `python scripts/check_all.py` and `npm run openspec:validate`.

      Verify that both pass, then open PR D once the maintainer approves its body.

## Workflow follow-up

- Archive the change in PR D with `/openspec-archive-change restore-main-and-triage-open-work` after explicit approval.
  The archive adds the `guide-delivery` link-check requirement and the modified Project audit requirement, and the two
  `guide-experience` catalogue requirements, to `openspec/specs/`.
- Merge PR D by the route in design D2, then verify the archived spec with `npm run openspec:validate`.
