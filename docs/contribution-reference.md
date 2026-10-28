<!-- type: reference -->
# Contribution reference

The [contributor landing page](../CONTRIBUTING.md) links the procedures for editing, building and planning.
This reference records branch conventions, review criteria, credit and commit policy.

## Branches and delivery

`main` supplies the `/next/` preview; production uses verified release artifacts. Pull requests are the default
delivery path. An explicitly authorised maintainer direct commit remains releasable after the same checks;
this does not authorise agents to push to `main` or bypass protection. Branch names identify their purpose:
`content/<topic>`, `fix/<topic>`, `feature/<topic>`, or `agents/<agent>/<topic>` for AI-assisted work.
A pull request has one purpose and uses the template to explain the change, reason and supporting sources.

## Review

Checks protect the page and data; human reviewers judge correctness and tone. The appropriate content team or
collaborators listed in the repository's **Collaborators and teams** review content meaning, source interpretation
and wording. [.github/CODEOWNERS](../.github/CODEOWNERS) names technical owners: they check that a change preserves
integrity and compatibility and fits the Guide. It is not the content-review roster, and a technical approval
does not establish content expertise. Only actual eligible technical owners are listed.

The [review runbook](runbooks/review.md) owns scope selection, AI-assisted analysis, finding disposition,
posting approval and re-review. Human content and technical acceptance remain separate from those automated outputs.

The gates that can be enforced depend on who can review:

- Pull requests into `main` require the `checks` result of "Guide checks and health report" to pass. Explicitly
  authorized maintainer direct commits remain subject to configured branch protection; nothing is force-pushed or
  deleted.
- Choose **Merge when ready** after approval. The queue checks the merged result again
  and merges only when it passes, so a pull request no longer has to be up to date with `main`. Human, Dependabot
  and refresh pull requests take the same path. An administrator's direct merge is the break-glass route; its
  deployment runs the full checks (see [deployment](deployment.md#merge-queue-staging-and-production)).
- Keep `CODEOWNERS` aligned with eligible technical reviewers for the owned files. Require one
  approving code-owner review when an independent eligible reviewer is available. GitHub does not let an
  author approve their own pull request; without an eligible independent reviewer, a release candidate needs
  the maintainer's explicit acceptance before tagging. Track changes to reviewer coverage and branch settings
  in an issue or OpenSpec change.

Automated refreshes and agents never merge their own pull requests.

## Credit and ORCID iDs

Credit follows what people actually did. `CITATION.cff`, the crate and the provenance actions name a person
only with an identity they gave or that is reviewed (their name, their GitHub account and, if they want, their
ORCID iD). Anyone may ask not to have their ORCID iD listed; they are then credited by name only. No identity or
ORCID iD is guessed, and no team or bot is credited as an author.

## Commit messages

Write a short imperative summary line (for example `content: clarify licence advice for data stewards`),
followed by a body when the reason is not obvious. Mention AI assistance in the body when it was used.
Commit messages are the durable record from which release notes are written: squash merges keep every branch
commit's message, while pull-request descriptions may change later. Say in the body what changed for readers or
maintainers and why, and name the issues involved as `#N`. A breaking change, a step people have to take or a
security fix also gets one line under `[Unreleased]` in `CHANGELOG.md` (see the [changelog policy](changelog.md)).

## Repository settings

`.github/repository.toml` is the reviewed expected state for settings, the
[EOSC CZ FAIR Guide Project](https://github.com/orgs/dsw-nrp/projects/1) and token permissions.
Changes to workflow token permissions include their `[[token]]` entry. The read-only audit and its limits are
in the [maintenance reference](maintenance.md#repository-settings-audit); settings changes need approval of
their exact diff. [Rollback](runbooks/rollback-a-setting.md) changes one setting at a time.

## Content and check requirements

The [content model](content-model.md) defines bilingual values, published sources, advisory wording, dated
statuses and provenance. The [content how-to](how-to/edit-content.md) applies those requirements to an edit.
The [build how-to](how-to/build-and-check.md) covers setup and local checks; the [CI reference](ci-reference.md)
defines lanes, evidence, budgets, failure artifacts and the complete-coverage rule.

## Release responsibilities

The [release runbook](runbooks/release.md) owns preparation, queueing, tagging, production approval, notes and
publication. The [deployment reference](deployment.md) defines immutable bytes, release status, citation metadata,
image identity and recovery. Automation drafts releases; a maintainer publishes them.

## Conduct

Everyone taking part follows the [Code of Conduct](../CODE_OF_CONDUCT.md).
