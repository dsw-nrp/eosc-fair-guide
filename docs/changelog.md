<!-- type: reference -->
# Changelog policy

`CHANGELOG.md` is the permanent record of what each release contains. Release preparation generates it from
durable history: the merged pull requests and the direct commits since the previous release. People add a single
line only for what that list cannot carry. The reader-facing account of a release belongs in its GitHub release
body, written at release time from the same history. This page says who writes what, what the checks enforce and
how a release consumes it.

## Write the detail in commit messages

Commit messages are the durable source. Pull-request descriptions change after merge and differ in shape; commit
messages do not. A squash merge into `main` takes the pull-request title (or the single commit's summary) and keeps
the messages of every branch commit in its body, so a commit message written for a later reader reaches the default
branch unchanged. Write a short imperative summary line and a body that says what changed for readers or
maintainers and why, naming the issues involved as `#N` (see [commit messages](contribution-reference.md#commit-messages)).

## When to add an unpublished note

Add a line under `## [Unreleased]` only for what a reader must not miss in a list of titles:

- a breaking change: something that worked before now behaves differently or is refused; also give the pull
  request the `breaking-change` label;
- a step people have to take, such as a migration, a changed command or a newly required setting;
- a security fix.

Write one line per change that describes the resulting behaviour, under a
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) category such as `### Changed`, `### Removed` or
`### Security`. New features, fixes, checks, refactoring and dependency or source refreshes need no note: the
generated list covers them. Leave the section empty when nothing qualifies; an empty section is valid.

## What the check enforces

`python scripts/check_changelog.py --base origin/main` runs in `check_all.py` and in the CPU lane of the pull-request
checks. It reads only `CHANGELOG.md` and Git history, never pull-request text, and it never edits the file.

| Rule | Failure message names |
| --- | --- |
| Exactly one `## [Unreleased]` section, above every release | the missing, duplicated or misplaced section |
| A category heading has at least one entry; bare placeholders such as `- TBD` are not entries | the empty category or placeholder |
| `### Merged pull requests` and `### Direct commits` are reserved for release preparation | the reserved heading |
| Every released section keeps its bytes from where the branch left the base | the changed or removed release |
| A new release section is added only by a complete release transition | what the transition lost or misplaced |

Without `--base`, only the structure of the file is checked. Older release sections keep their accepted
formats and are never converted.

## How a release consumes the notes

**Prepare release** (`scripts/release_versions.py prepare`) moves the `[Unreleased]` lines unchanged into the new
dated section and leaves `[Unreleased]` empty. After them it adds `Since <previous tag>.` and the generated
`### Merged pull requests` and `### Direct commits` lists, each pull request once. Earlier releases keep their
bytes. Preparation refuses before writing any file when the lines are malformed or use a reserved heading, so fix
them and run it again. With no lines, the release contains only the generated lists. The changelog check accepts
this transition without a further unpublished note.

## Write the release body

The [release-notes how-to](how-to/release-notes.md) owns the one-invocation skill and manual fallback.
The draft body combines the publishable notes with one byte-preserved verification record; working notes,
published releases and changed inputs are refused by `scripts/release_body.py`.


## Findings after a release

Never edit a released section; its text is part of a published, archived release. Record a correction found
after a release under `[Unreleased]` for the next release when it is a breaking change, a required step or a
security fix, and name the affected version when that helps, for example "Security: the health report no longer
shows local paths (affected 1.2.0)". Name the affected version as it appears in its release heading. Other
corrections reach the next release through their commits.

## Ownership

| Part | Owner |
| --- | --- |
| Commit messages | commit authors; squash merges keep them in the default branch |
| `[Unreleased]` lines | pull-request authors, reviewed with the pull request |
| Release lineage (`Since …`, merged pull requests, direct commits) | `scripts/release_versions.py` |
| Release dates and versions | `scripts/release_versions.py`; see [deployment](deployment.md) |
| Release-note categories | `.github/release.yml`, read by GitHub and by `/aiscr-write-release-notes` |
| Release-body notes | the maintainer, with `/aiscr-write-release-notes` and `scripts/release_body.py` |
| Release-body verification record | the release workflow (`.github/scripts/release-artifact.cjs`) |
