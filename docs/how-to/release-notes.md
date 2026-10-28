<!-- type: how-to -->
# Prepare a draft release's notes


After the approved production publication, **Release** drafts the GitHub release. Its body links the release's section of
`CHANGELOG.md` and ends with a marked verification record: the commit, the archive digest, the container image and
the release status. Before publishing the draft, the maintainer replaces the link with reviewed notes.
The preferred route is [`/fair-guide-release-notes <tag>`](../../.agents/skills/fair-guide-release-notes/SKILL.md):
it runs steps 1 to 3 in one invocation, resolves the previous release tag including pre-releases, and asks once
before applying the exact body. It leaves publishing to the maintainer. For the equivalent manual route:

1. Run `/aiscr-write-release-notes` for the tag in English, from the previous release tag, and keep its default
   report-only mode. It reads the merged pull requests, the commit messages and the issue threads, groups them by
   the labels in `.github/release.yml` and writes the publishable report
   `.agents/reports/release-notes/eosc-fair-guide_<tag>.md`, beside a working companion that is never published.
2. `python scripts/release_body.py <tag>` composes the body for review: the publishable report without its title,
   followed by the verification record byte for byte. It prints the body and keeps it in `.cache/release-notes/`.
3. `python scripts/release_body.py <tag> --apply` writes exactly the reviewed body to the draft and reads it back.
   It refuses a published release, working notes, a body without one marked verification record or a composition
   that differs from the reviewed copy. Other release metadata and the replaced draft prefix are not bound by that comparison.
4. Publish the draft in GitHub. Zenodo takes the archived record's description from `.zenodo.json`.

The skill's own release-body update would replace the verification record, so leave it off. Without these steps
the published release keeps the changelog link and the verification record.

Return to [release](../runbooks/release.md) for the publication step.
