---
name: fair-guide-release-notes
description: Write and apply the reviewed notes of one Guide release draft in one invocation. Resolves the tag and the previous release tag, pre-releases included, runs aiscr-write-release-notes report-only in English, composes the body with release_body.py, asks once, applies and reads it back. Publishing stays a separate click.
argument-hint: <tag, for example v1.0.0-alpha.4>
disable-model-invocation: true
---

# FAIR Guide release notes

This skill writes to GitHub once, in step 5, after the user approves the exact body. It never tags, publishes,
edits `CHANGELOG.md` or changes a delivered `aiscr-*` file. `docs/changelog.md` owns the release-body policy.

1. **Resolve the release.** Take the tag from the argument and accept it with or without one leading `v`; the tag
   itself is `v<version>`. Run `gh release view <tag> --json isDraft,tagName,body`. Stop when the release is
   missing (Release drafts it after the production deployment) or already published (`isDraft` is false).
2. **Resolve the previous release tag.** Run `git fetch --tags`, then `git describe --tags --abbrev=0 <tag>^`. The
   Guide publishes pre-releases until 1.0.0, so a pre-release counts; the delivered workflow's default baseline, the
   last non-pre-release, would skip them. With no earlier tag the range starts at the repository's first commit.
   Tell the user the `prev..tag` range.
3. **Write the notes report-only.** Run `/aiscr-write-release-notes` with its Step 1 answers fixed: target
   `dsw-nrp/eosc-fair-guide`; single release `<tag>`; git range `prev..tag` from step 2; English; dependency
   coverage yes; release body update **No (A)**. It writes `.agents/reports/release-notes/eosc-fair-guide_<tag>.md`
   and a `.working.md` companion, which is never published.
4. **Compose for review.** Run `python scripts/release_body.py <tag>`. It prints the body, the publishable report
   without its title followed by the draft's verification record byte for byte, and keeps it in
   `.cache/release-notes/<tag>.md`. Show the user the `prev..tag` range, the composed body and the working notes'
   gap check, and ask once whether to apply exactly this body.
5. **Apply after approval.** Only on an explicit yes for that body, run
   `python scripts/release_body.py <tag> --apply`. It refuses when the notes or the release changed since the review,
   the release is published or the verification record is missing, and it reads the body back. Report what it read.
   Without approval, stop: the reviewed body stays in `.cache/release-notes/`.
6. **Hand over.** End with the next step: the maintainer publishes the draft in GitHub and Zenodo archives it.
   Release-notes reports stay git-ignored, so the release body is the durable record.
