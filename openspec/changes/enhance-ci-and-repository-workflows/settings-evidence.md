# Settings decisions and read-only evidence

## Tag protection, 26 October 2026 (task 13.4)

The maintainer explicitly selected **keep both deployment gates and checks**. A fresh read-only
`GET /repos/dsw-nrp/eosc-fair-guide/rulesets/25342318` reports active tag protection with no bypass actors,
required deployments `github-pages` and `staging`, and required status `checks` from integration `15368`
(GitHub Actions). Checks are enforced on creation; strict up-to-date policy is false.

The local declaration retains those exact gates and removes the obsolete pending replacement target. Only
the tag portion of the recorded API fixture was refreshed. All 39 audit tests pass natively, including planted
removal of either deployment, a changed check name and a wrong integration. The fresh read-only ruleset audit
reports no tag-protection difference. Its separately observed maximum merge batch of ten was explicitly retained
by the maintainer below; that was not a tag-protection failure.

No hosted setting was changed. Task 8.7 remains open: successful staging, API-created record acceptance and
required-check evidence before real tag creation still need their hosted exercise. This decision does not
waive those proofs or authorize tagging, publication or a settings write.

## Audit permission-input compatibility (task 13.2)

The pinned `actions/create-github-app-token` commit `64ab729a6294000f5aa4a4bc0b73d1f32bc45510` does not yet list
the two newer inputs in `action.yml`. Its actual
[generic parser](https://github.com/actions/create-github-app-token/blob/64ab729a6294000f5aa4a4bc0b73d1f32bc45510/lib/get-permissions-from-inputs.js)
forwards every `INPUT_PERMISSION-*` entry, lowercasing and replacing hyphens with underscores. Executing that
exact primary-source parser with the three explicit read inputs returns only `organization_projects: read`,
`issue_types: read` and `issue_fields: read`; its token-creation implementation forwards that object to installation
authentication. The [runner input handler](https://github.com/actions/runner/blob/main/src/Runner.Worker/Handlers/Handler.cs)
passes all supplied inputs to the environment; its
[action runner](https://github.com/actions/runner/blob/main/src/Runner.Worker/ActionRunner.cs)
warns about unlisted inputs rather than discarding them. A metadata warning may therefore appear with this pin.
No full-permission token or alternative authentication implementation is needed.

The workflow requests these reads only in the audit job. REST definition endpoints and Project GraphQL use that
credential, while repository reads and writes retain their original credential. The reviewed registration and
fixture record the advertised permissions, not installation acceptance. Actual token issuance, endpoint results
and the default-branch audit-only receipt remain task 13.3; local parser/routing fixtures do not establish them.

## Queue decision, 26 October 2026 (task 13.5)

A fresh read-only ruleset audit found one difference: live `max_entries_to_merge` was ten, while the declaration
still said three. The maintainer explicitly chose **keep the live batch of ten**. A direct read-back of ruleset
`24757722` confirms `ALLGREEN`, `SQUASH`, two builds, maximum ten/minimum one merges, zero batching wait and a
30-minute check timeout. Only the local declaration and corresponding recorded field are reconciled; no remote
setting is applied or restored.

The [GitHub controls](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
are independent. Build concurrency controls simultaneous merge-group CI. Merge limits control the batch of
verified entries that may merge; ten neither combines builds nor waits for ten entries when the minimum is one
and batching wait is zero. It is not a justification to skip any check.

Observed demand and waiting evidence:

- The existing four-attempt CI receipt measures six peak jobs per run, 21-31 seconds of queue time and 273-287
  seconds elapsed with full inventory coverage. Retaining two builds bounds queue build demand while PR runs
  share runner capacity; it is a conservative choice rather than proof of an optimal organization limit.
- The five most recent merge-group runs were all completed at read-back. Their elapsed ranges were 270-300
  seconds; run `40153182976` succeeded in 270 seconds, and `40151368869` failed the known provenance rule rather
  than a capacity limit. The two runs starting one second apart on 25 October are consistent with the two-build
  control. No new performance gain is claimed from changing the batch ceiling.
- All six currently open PRs are drafts (#116, #70, #39-#42), so this snapshot has no ready PR awaiting a larger
  merge batch. It does not establish high-backlog throughput. Keep the chosen ceiling and use `ci_timings.py`
  to revisit build concurrency when actual waiting/runner demand warrants it.

Recommendation accepted: retain the live ten-PR merge ceiling and two-build limit, with full checks and no
minimum batching delay. This corrects the unsupported implication that a three-PR ceiling was measured optimal.

# Technical-owner eligibility read, 26 October 2026

The read-only `GET /repos/dsw-nrp/eosc-fair-guide/collaborators/motyc/permission` request returns `admin`.
This confirms repository write access for the one technical owner declared by `CODEOWNERS`. It does not make
that owner eligible to approve their own pull request or replace an enforced independent-review requirement.
No collaborator, review rule or repository setting was changed by this read.

