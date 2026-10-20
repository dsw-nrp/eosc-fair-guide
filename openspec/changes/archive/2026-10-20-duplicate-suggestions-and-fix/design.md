# Design

## Context

See `proposal.md` for the PR 82 failure and the requested outcome. The current duplicate check (`scripts/check_duplicates.py`) already computes the groups and a human-readable remedy, but it returns only a list of strings through the shared `Report` (`scripts/check_content.py:141-150`). The CI collector (`scripts/check_ci.py`) raises on the first failed lane result, and on that path it does not copy lane `logs/` or `details/` into the health artifact. The trusted comment publisher (`pr-summary.yml`, `.github/scripts/comment-summary.cjs`) reads only `summary.json` and has no suggestion data. The source refresh validates snapshot shape but not the Guide's cross-content identity rules.

## Goals / Non-Goals

**Goals:**

- Make the duplicate remedy exact and actionable without changing the duplicate rule.
- Let a maintainer apply an unambiguous link through an explicit command with provenance, while ordinary PR checks remain read-only.
- Make a failed aggregate self-explanatory from the job summary and its artifact.
- Prevent new snapshot rows from silently reusing identifiers owned by other content.

**Non-Goals:**

- No automatic curated-content edits on schedules, ordinary PRs, or untrusted forks.
- No automatic acceptance of lookalike records in `content/duplicates.toml`.
- No general-purpose auto-repair of names, types, provenance, citations or snapshot facts.
- No change to the duplicate check's identity keys or acceptance semantics.

## Decisions

### 1. A structured suggestion is a separate result, not a richer error string

`check_duplicates` keeps `Report.errors` for the existing human-readable failure and adds a suggestion collection with a stable shape:

```text
entry        resource:datarepo
record       re3data:r3d100014970
resolution   link
safe         true
file         content/resources.toml
table        resource.repository
field        re3data
value        r3d100014970
reason       shares address https://datarepo.eosc.cz
```

`check_duplicates` writes the collection to `duplicates.json` under `CHECK_REPORT_DIR` when that directory is set, and accepts `--report <path>` for local use. The current text output remains the default so existing humans and tests do not change.

Only link groups are eligible. `safe` is a rule-based boolean, not a confidence score. It is true only when all of these hold:

- exactly one curated entry and one registry record are in the group;
- they share an authoritative key (address, DOI or registry identifier), not only a name or text;
- the curated entry lacks the link field and has no conflicting value for it;
- the field placement is known (`[resource.repository]` for a resource, top level for `[[repository]]`);
- the group is not accepted in `duplicates.toml`;
- the registry record is present in the content used for the build.

The suggestion engine resolves the curated entry through the existing `Entry` records and a small kind-to-field map. It does not edit any file; `--fix` and the command are separate consumers.

Safety is checked across the complete suggestion set: different values for the same entry/table/field
make that target ambiguous. An existing key, including an empty value, is not a missing field. Consumers
inspect the whole target table and parse the proposed TOML before replacing the original file.

The registry-link owner index covers the full catalogue. A record already linked by another curated
entry cannot supply a safe suggestion; competing proposed owners are excluded even across joined
registries, and identical suggestions are deduplicated. One Python mapping owns exact entry-kind,
file, table and field combinations, shared by producer, collector and both apply consumers. The
independently trusted Node validator is checked against that domain, including invalid combinations.
Both handler paths reuse the checker's accepted-group loader.

Alternative considered: put the patch into the error string and parse it in CI. Rejected because it makes a display format a data contract and is unsafe to parse.

### 2. Suggestions are surfaced, not applied, by PR checks

The PR check workflow stays read-only. The lane artifact carries `duplicates.json`; the collector copies it into `.cache/pr-review/suggestions.json`, and the `guide-review-*` artifact includes it. The trusted comment publisher reads that file, validates the format and size, escapes the content, and appends a "Suggested fixes" section with a fenced diff and the reason. It skips a stale PR head exactly as it does for the changed-item summary.

The `checks` job summary renders the same suggestion text for a reader who does not open the artifact. The summary is bounded (at most a few suggestions and a short output tail per failed check) so a noisy failure cannot flood the run page.

The artifact's `head` is the PR source head supplied by the workflow, while `checkedRevision` retains the
merge commit used for the build. These identities remain separate; publisher freshness uses the source head.

Only the directory returned by successful reconciliation for the duplicate check's owning lane can
supply suggestions; arbitrary incoming directories cannot. Identity or required-evidence rejection
yields no suggestions. Required diagnostics are published before optional suggestion work, whose
bounded errors remain warnings without changing the gate. The collector invalidates previous output
and emits `suggestions_path` only after current-run generation and summary publication succeed; the
upload uses that step output. A stale file that cannot be removed is therefore excluded from review
artifacts. Reasons render as inert code text on both the bot comment and CI summary.

Alternative considered: a GitHub inline suggested change. Rejected because the repaired file is usually not in the pull request's diff, so no inline position exists. A normal PR comment with a diff is reliable.

### 3. Local `--fix` is a convenience for a person, not a CI action

`python scripts/check_duplicates.py --fix` applies only `safe` suggestions to the working tree, prints a unified diff, and exits non-zero if nothing was applicable. It does not add a provenance action and does not commit. The printed output names the provenance fields the person must complete, because the content rules require a person as the agent and a reviewable action for the changed entry.

Prepare and parse edits before replacement, write and close temporary siblings, then use `os.replace`
only if the target still has its inspected bytes. Preserve original bytes for affected targets and
register known replacement bytes in the rollback map immediately after the swap, before cleanup;
there is no post-write discovery read. Application, cleanup, content-loading or final duplicate-check
failure restores earlier changes and returns nonzero. Concurrent changes are refused and restoration
errors name the affected path. Print the exact unified diff, success message and complete provenance
reminder only after a passing recheck. This is atomic per file, not a crash-atomic multi-file transaction.

Alternative considered: `--fix` writes a provenance stub. Rejected because a stub would be a placeholder and the checker would either fail or accept an incomplete action.

### 4. `/fix-duplicates` is a separate trusted workflow

A new `.github/workflows/fix-duplicates.yml` listens for `issue_comment` on pull requests and accepts exactly `/fix-duplicates`. It is not triggered by schedules and does not run on forks. It uses trusted default-branch code and the existing repository-scoped App, with only the permissions needed for contents and pull-request comments. A separate workflow keeps source refresh's snapshot-only boundary intact and lets the command be enabled or disabled independently.

The handler:

1. Verifies the commenter currently has write access with the same permission check used by `/refresh`.
2. Verifies the pull request is open, belongs to the same repository, targets the default branch, and its head is not the default branch.
3. Extracts `content/` and its authored validation attachments (`assets/`, `profile/` and `index.html`)
   with `git archive` and records that exact commit SHA. The handler requires it to
   match the first validated PR head read before loading or changing content. The trusted validator reads
   attachment text and checks file existence; it does not execute PR code or scripts from the archive.
4. Runs the suggestion engine from default-branch code against that content.
5. Applies only `safe` suggestions. If none are available, it comments why and changes nothing.
6. Resolves the commenter to a reviewed `[[person]]` through the existing `github` identity. If there is no person entry, it refuses and asks for one; it never guesses a person.
7. Re-reads the head, checks that the target file still matches the content used for the suggestion, and aborts on a race.
8. Applies the link and one provenance action naming the commenter as agent, the command as instrument,
   the consulted record and the changed entry as objects/results, with an end time and offset. Registers
   that action ID before validating content and includes the register update in the same commit. Only the
   new action is registered; other missing IDs still fail validation, and existing/retired IDs are preserved.
9. Commits to the PR branch through the App without force-pushing, comments the applied diff and new head, and leaves the checks to rerun.
10. Never merges, never pushes to the default branch, and never edits `content/duplicates.toml`.

Repair diffs and PR-derived diagnostics use safely closed fences longer than any matching delimiter
run in retained text; truncation budgets the enclosure and keeps the commit reference. If the success
comment fails after committing, the workflow asks the maintainer to inspect the branch and run; it
does not imply the branch stayed unchanged or automatically undo the commit.

The command remains available on eligible `refresh/*` PRs. Source publication replaces an existing
branch only when the complete nonempty inventory belongs to the configured App and every message is
the expected `Refresh the <source> snapshot` message, allowing a terminal newline. The guard shares
that message construction with publication. Same-App repairs, people, other bots, unknown authors or
messages and missing/failed inventories protect the branch and explain manual reconciliation; no
tree, commit or ref update occurs. This preserves repairs instead of removing the refresh-PR use case.

Alternative considered: extend `source-refresh.yml`. Rejected because it would mix snapshot publication with curated-content edits and widen the command's trust surface.

### 5. The aggregate reports every failure and keeps the evidence

`check_ci.reconcile` collects every failed row instead of raising on the first, and returns a structured failure carrying each check name and a bounded output tail. `collect` emits those rows in the report, so `check_health.markdown` lists every failed check. Before emitting a failure report, the collector copies the incoming lane `logs/` and `details/` directories into the output, so the health artifact contains the same evidence the lane produced. The aggregate still exits non-zero and still cannot publish a complete pass. Required partial rows
become failed aggregate results even at native exit zero, with an incomplete-coverage explanation
and their partial flag retained. Original lane exit codes and evidence remain available; console
and health rendering consume the same normalized failure without changing the shared `Result.ok`
meaning or health schema.

The summary uses a fixed bound (for example, the last 40 lines or 4 KiB per failed check) and states that the full output is in the artifact. This avoids unbounded log volume while preserving the exact error text that PR 82 hid.

### 6. Reserved identifiers prevent a new snapshot from stealing an existing ID

`refresh_snapshots.commit` gathers the primary `id` values of all authored collections other than the snapshot being replaced, plus `retiredIds`, and passes them as `reserved` to `preserve_snapshot`. The existing identity join still decides whether a new row is the same thing as a curated entry; the reserved set only prevents a new local ID from colliding with an unrelated entry. A collision that cannot be resolved through the existing identity join is rejected with a reviewable reason rather than written.

The reserved set also includes every identifier under `[retired]` in `content/identifiers.toml`.

The PR 82 case is resolved by the link suggestion, not by changing the snapshot's generated ID: `build_crate.repository_key` merges the snapshot row and the curated resource by `re3data:<id>`. The reserved set is the general guard for the other case.

The delivered repair includes PR 82's dated snapshot together with
`resource:datarepo`'s `re3data = "r3d100014970"` link and a registered provenance action. The original
snapshot is preserved as reviewed source data; it and the curated resource build one repository entity.

### 7. Suggestion data is validated like any other artifact

The publisher treats `suggestions.json` as untrusted data even though it comes from the repository's own checks. It validates the format version, the PR head and repository, the number and size of suggestions, and the file/table/field names against the allowed map before rendering. Unknown or malformed suggestions are dropped with a count in the comment, not rendered as Markdown.
Require strings before membership or exact-placement lookup so arrays and objects cannot abort
failure diagnostics. Python consumers use the canonical mapping; Node keeps an independent mapping
whose accepted and rejected combinations are checked for parity.

## Risks / Trade-offs

- **False-positive safe suggestions** → The rules above are deliberately narrow; suggestions are never applied by CI; tests cover lookalike groups, multiple records, existing links and accepted exceptions.
- **A maintainer command edits curated content** → It requires current write access, a same-repository PR, a safe-only suggestion, an existing person mapping, a re-read before commit, and a provenance action; it cannot merge or target the default branch.
- **App token misuse** → The workflow uses trusted default-branch code, never executes PR code with the token, limits the token's permissions, and reuses the existing current-permission check.
- **Comment noise** → The suggestion section appears only when safe suggestions exist, in the existing single bot comment.
- **Artifact growth** → Output tails and suggestion counts are bounded; full evidence stays in the lane artifact.
- **Stale suggestions** → The handler re-reads the head and aborts if the target content changed; the comment publisher skips a stale head.
- **Missing person mapping** → The command refuses rather than inventing an agent; the local `--fix` path prints the fields for the human to complete.
- **Suggestion treated as a verdict** → `safe` is a boolean about mechanical applicability, not a claim that the two records are the same thing; the comment states the shared key and the remedy.

- **Repair atomicity** -> Per-file swaps and handled-error rollback do not promise recovery after
  process termination or total disk failure; restoration failures are explicit.
- **Protected refresh PRs** -> A person reconciles new source content once a repair is present,
  preserving its link, provenance and registered identifier.

## Migration Plan

- The local suggestion output and `--fix` are additive; existing duplicate failures keep their current text.
- The aggregate diagnostics change only the failure path; a passing run is unchanged.
- The reserved-ID guard applies on the next refresh; existing snapshots are not rewritten.
- The new workflow is inert until it reaches the default branch. If the App secrets are absent, the command is unavailable and reports that; local `--fix` remains.
- Rollback: remove or disable the new workflow and the comment section; suggestions and `--fix` can be reverted without touching content or snapshots.

## Open Questions

None.
