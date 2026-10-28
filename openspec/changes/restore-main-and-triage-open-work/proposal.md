# Proposal

## Why

`main` has failed its deployment checks since b3474e5 (28 October 2026). The redelivery of the AIS CR tools added
`.agents/scripts/github/github_references.py` to the `aiscr-plan-from-issue` receipt, but nobody regenerated the
inventory in `docs/agent-tooling.md`, so `agent-generation` fails. The commit reached `main` without a pull request.
The merge queue checks `main` together with each pull request, so every queued pull request now fails as well.

Behind that block, a maintainer faces seven open pull requests, 33 issues that were never triaged and a maintenance
digest with 16 findings (#140):

- Three bot pull requests are green and wait only for review.
- Four drafts by Karel Berka, written with Antigravity (#39–#42), conflict with `main`. They were checked by the CI
  that #116 replaced, and they carry OpenSpec archives and per-item requirements that the content rule does not ask
  for.
- One digest finding is the watch's own error: it reads a server's rejected HEAD request as an unavailable page.
- Every open issue has a type and an area label, but none has Priority, Effort or a planned-issue body, so none can
  be Ready. Some are stale: #15 and #32 still describe `https://fair.eosc.cz/` as the Guide's address and namespace,
  which #116 changed and #136 now covers. The audit starts reporting them after 6 November, when 31 of them pass
  14 days in Needs triage.
- The digest can never be triaged. Its body is rebuilt on every run, so it cannot take the planned-issue shape that
  Ready requires, and the audit reports it 14 days after it opens, as it will every successor.
- The catalogue hides part of what the knowledge base records. The Guide tells readers that every content change is
  recorded with its author, its tools including any AI model and its sources, and that they find it in the catalogue
  (`content/pages.toml:179`). The catalogue's change entries show none of these: only a count of changed items and the
  cited sources among the objects consulted. Questions hide who puts them right, when they apply and which sources
  pre-fill them; FIP profiles show a count of declarations instead of the declarations; enabling resources, licences
  and superseded requirements lose fields too. Stations stay quiet by design; the catalogue is where they send readers
  for the detail.

## What Changes

1. **Restore `main`.** A quick-fix pull request regenerates the inventory with
   `python scripts/generate_agent_surfaces.py`. Nothing else changes.
2. **Land the bot pull requests** once `main` is green:
   - #138: ruff 0.17.2.
   - #139: the last `setup-python` 7.0.0 pin and a new `docker/login-action` v4 commit.
   - #117: the re3data snapshot with one added DataCite DOI.
3. **Rebuild the drafts, one pull request per issue.**
   - **Mapping:** #39 → #35, #41 → #36, #40 → #37 and #42 → #38, merged in that order. Each new pull request
     starts from current `main`.
   - **Kept:** the station text, identifier registration, and the author's credit in git, provenance and the
     Guide's contributors.
   - **Dropped:** the archived OpenSpec changes, the per-item knowledge-base requirements and the drafts' usage logs.
   - **Shared records:** the person, organisation and instrument records that all four drafts add land once, in the
     first rebuilt pull request, with the Antigravity record pointing to its product page.
   - **Closure:** each draft is closed with a link to its replacement.
4. **Triage digest #140** following `docs/runbooks/handle-the-digest.md`:
   - reviewed limitations for the seven denials and rate limits;
   - a reader-link fix for the RO-Crate 1.2 resource;
   - the Sherpa API source record moved to Open policy finder, since its page refuses people as well (#137);
   - upstream reports and tracked tasks for dead addresses in imported snapshots;
   - a decision after the next run for `asep.lib.cas.cz` and `data.eli-laser.eu`;
   - a tracked task for the FAIR Champion candidate review;
   - a decision comment for the two source updates;
   - a check that the Project view sort finding has cleared, since #141 recorded the live sort as expected.
5. **Retry a HEAD 400 with GET.** The watch already repeats a HEAD request with GET after 403, 405 or 501. Adding 400
   means a server that rejects HEAD is judged by its GET answer. The events.eosc.cz survey PDF is the current case.
6. **Triage every open issue** to the definition of Ready in `docs/maintenance.md`, or close it:
   - one reviewed ledger decides, for each issue, whether it is kept, re-scoped, merged or closed, with its Priority,
     Effort, milestone and shaping route;
   - closures and re-scopes come first, because they remove work from the shaping;
   - the remaining bodies are shaped with `/aiscr-plan-issue`, then Priority, Effort and Ready are set;
   - the tracked tasks this change opens are triaged the same way.
7. **Exempt the digest from triage.** The audit stops reporting the published digest's time in Needs triage and its
   Ready completeness, and the Project's Triage view leaves it out. Every other issue, including one a person labels
   `guide-health`, keeps every check.
8. **Show every recorded field in the catalogue.** Stations stay quiet; the catalogue hides nothing:
   - complete cards for content changes, check questions, FIP profiles, FAIR-enabling resources, resources and sources
     (their licence) and superseded requirements;
   - six conventions applied to every kind, which also reshape the infrastructure, test, criterion, life-cycle and
     term cards;
   - relations shown in both directions, including a **Changes** row on every entry;
   - a test that fails when a recorded field is neither shown nor excluded with a reason.

### Exclusions

- A procedure or check that regenerates native surfaces after each redelivery.
- Reviewer configuration for the single code owner.
- The FAIR Champion selection review itself; this change only opens its task.
- Edits to imported snapshot records, which their upstream sources correct.
- PR #70 (jsonschema 4), which cannot be applied for compatibility reasons.
- The work the triaged issues describe. Triage decides and shapes each issue; it does not carry it out.
- Changes to the definition of Ready, and an extension of `audit_repository.py --backfill` to Priority, Effort or
  Status.
- Changes to the stations' quiet source and date line, and to the About page's credits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-delivery`:
  - the live health watch states when a link check repeats a rejected HEAD request with GET, and adds HTTP 400 to
    those statuses;
  - the Project audit exempts the published digest from its triage-age and Ready checks.
- `fair-guide/guide-experience`:
  - the catalogue shows every field its records carry, or excludes it with a reason, and shows relations in both
    directions;
  - catalogue entries follow shared conventions for who made or runs an entry, licences, dates, status and qualified
    lists.

## Impact

- **Generated documentation:** `docs/agent-tooling.md` (one inventory row).
- **Bot pull requests:** `.github/workflows/health-watch.yml`, `.github/workflows/publish-image.yml`,
  `requirements-dev.txt` and `content/snapshots/re3data.toml`.
- **Rebuilt content:** `content/stations/*.toml`, `content/identifiers.toml`, `content/provenance.toml` and
  `content/guide.toml`, with `tests/test_watch.py` made independent of the link count.
- **Digest fixes:** `content/resources.toml` (`ro-crate` address), `content/sources.toml`
  (`sherpa-object-retrieval-api`) and `.github/health-watch.toml` (limitations).
- **Watch behaviour:** `scripts/watch_sources.py` and `tests/test_watch.py`.
- **Audit behaviour:** `scripts/audit_repository.py`, `tests/test_audit_repository.py`,
  `tests/fixtures/repository-audit.json`, `.github/repository.toml` (the Triage view filter and the `guide-health`
  description) and `docs/maintenance.md`.
- **Catalogue:** `assets/js/catalogue.js`, `assets/js/catalogue-view.js`, the shared badge helper in `assets/js/`,
  the labels and icons in `content/ui.toml`, the page tests under `tests/page/`, a completeness test, and the decision
  on paradata detail in `docs/design.md`.
- **Specs:** `openspec/specs/fair-guide/guide-delivery/spec.md` and `openspec/specs/fair-guide/guide-experience/spec.md`
  on archive.
- **Records:** one usage entry under `.agents/reports/usage/` for this change, and the triage ledger
  `openspec/changes/restore-main-and-triage-open-work/triage.toml`.
- **GitHub:**
  - pull requests #39–#42, #117, #138 and #139;
  - issues #35–#38 and #140, plus new tracked tasks;
  - issues #5–#33, #43, #80, #136 and #137: bodies, titles, parents, Priority, Effort, milestones, Status and
    closures;
  - the Project's Triage view and the `guide-health` label's description.
- **Upstream:** the KNAV tools catalogue records and the FIP Dashboard record that carry dead addresses.

### Validation

- `npm run openspec:validate`.
- `python scripts/check_all.py` on every pull request.
- `python scripts/watch_sources.py check-config` for the limitations.
- `python scripts/audit_repository.py --check-config` for the Triage view filter.
- `checks` and the deployment run for each merge.
- The next **Live health and source watch** run lists each addressed digest finding as known, tracked or no longer
  present.
- A maintainer's `python scripts/audit_repository.py --section project` reports no attention finding for any issue
  in the ledger, and every ledger issue is Ready or closed.
- The catalogue completeness test passes for every kind, and the changed cards are inspected in both languages, at
  phone width and in print.
