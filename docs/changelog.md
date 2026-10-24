# Changelog policy

`CHANGELOG.md` explains each release to readers and maintainers. People write the explanations; release
preparation adds the complete list of merged pull requests and direct commits. This page says who writes what,
what the checks enforce and how a release consumes the notes.

## Writing an unpublished note

Add a note under `## [Unreleased]` when a pull request changes something a reader or maintainer would notice:
new or changed advice behaviour, a fixed defect, a new check, a changed workflow or a removed feature.

- Use the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) categories: `### Added`, `### Changed`,
  `### Deprecated`, `### Removed`, `### Fixed` and `### Security`.
- Describe the resulting behaviour in one or two sentences, not the implementation steps.
- Write for the settled scope of the pull request. When later commits refine the same work, edit the note
  instead of appending another one for each batch.
- Leave the section empty when nothing notable is pending; an empty section is valid.

A note is not needed for a typo or wording fix, a test-only change, or a routine dependency or source-refresh
pull request. Those still appear in the release's generated list of merged pull requests. The pull-request
review comment says whether a note was added. It is advice; the reviewer decides whether a change is notable.

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

**Prepare release** (`scripts/release_versions.py prepare`) moves the curated `[Unreleased]` notes unchanged into
the new dated section and leaves `[Unreleased]` empty. After the notes it adds `Since <previous tag>.` and the
generated `### Merged pull requests` and `### Direct commits` lists, each pull request once. Earlier releases keep
their bytes. Preparation refuses before writing any file when the notes are malformed or use a reserved heading,
so fix the notes and run it again. With no curated notes, the release contains only the generated lists.

Review the curated notes as a whole in the release pull request: merge related lines, check that each entry
describes released behaviour and correct wording there. The changelog check accepts this transition without a
further unpublished note.

## Findings after a release

Never edit a released section; its text is part of a published, archived release. Record a correction found
after a release under `[Unreleased]` for the next release, and name the affected version when that helps, for
example "Fixed: the API index link returned 404 (affected 1.2.0)". Name the affected version as it appears in its
release heading.

## Ownership

| Part | Owner |
| --- | --- |
| `[Unreleased]` notes | pull-request authors, reviewed with the pull request |
| Release lineage (`Since …`, merged pull requests, direct commits) | `scripts/release_versions.py` |
| Release dates and versions | `scripts/release_versions.py`; see [deployment](deployment.md) |
| GitHub-generated release-note categories | `.github/release.yml`; see [deployment](deployment.md) |
