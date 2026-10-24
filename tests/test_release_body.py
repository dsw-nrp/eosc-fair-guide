"""Reviewed release notes replace the draft body's notes; the automation's verification record stays exact."""

import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import release_body  # noqa: E402

RECORD = (
    "<!-- guide-release:verification -->\nSite of commit `" + "a" * 40 + "`, version 1.0.0, checked on "
    "2026-10-24T00:00:00Z.\n\nThe attached `site.tar.gz` is the site that passed the checks and was deployed "
    "(SHA-256 `" + "b" * 64 + "`).\n\nRelease status: production (recorded by Tag release).\n"
    "<!-- /guide-release:verification -->"
)
DRAFT = "The merged pull requests and direct commits of v1.0.0 are listed in [CHANGELOG.md](link).\n\n" + RECORD
NOTES = """# Release notes — eosc-fair-guide (v1.0.0)

## Breaking changes

- Local duplicate repair needs a reviewed person ([#102](https://github.com/dsw-nrp/eosc-fair-guide/pull/102)).

## Features

_(none)_
"""


class FakeGitHub:
    """`gh release view/edit` against one release whose body and draft state the test controls."""

    def __init__(self, body=DRAFT, draft=True):
        self.body, self.draft, self.edits = body, draft, []

    def __call__(self, *args):
        if args[:2] == ("release", "view"):
            return json.dumps({"body": self.body, "isDraft": self.draft, "url": "https://example.test/release"})
        if args[:2] == ("release", "edit"):
            self.edits.append(args)
            self.body = Path(args[args.index("--notes-file") + 1]).read_text(encoding="utf-8")
            return ""
        raise AssertionError(args)


class ReleaseBodyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.notes = self.root / "eosc-fair-guide_v1.0.0.md"
        self.notes.write_text(NOTES, encoding="utf-8")
        self.addCleanup(self.temporary.cleanup)
        patcher = mock.patch.multiple(release_body, ROOT=self.root, REVIEWED=self.root / "reviewed")
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_body(self, github, *extra):
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.object(release_body, "gh", github), redirect_stdout(output), redirect_stderr(errors):
            status = release_body.main(["v1.0.0", "--notes", str(self.notes), *extra])
        return status, output.getvalue(), errors.getvalue()

    def test_the_markers_are_the_ones_the_release_workflow_writes(self):
        script = (Path(__file__).resolve().parent.parent / ".github/scripts/release-artifact.cjs").read_text("utf-8")
        found = re.search(r'VERIFICATION = \{ start: "([^"]+)", end: "([^"]+)" \}', script)
        self.assertEqual((found[1], found[2]), (release_body.START, release_body.END))

    def test_reviewed_notes_replace_the_default_and_keep_the_record_byte_for_byte(self):
        github = FakeGitHub()
        status, printed, _ = self.run_body(github)
        self.assertEqual(status, 0)
        self.assertEqual(github.edits, [], "a review run writes nothing to GitHub")
        reviewed = (self.root / "reviewed/v1.0.0.md").read_text(encoding="utf-8")
        self.assertTrue(reviewed.startswith("## Breaking changes\n"), "the report title gives way to the release name")
        self.assertTrue(reviewed.endswith("\n\n" + RECORD))
        self.assertNotIn("CHANGELOG.md](link)", reviewed)
        self.assertIn("python scripts/release_body.py v1.0.0 --apply", printed)

        status, printed, errors = self.run_body(github, "--apply")
        self.assertEqual(status, 0, errors)
        self.assertEqual(len(github.edits), 1)
        self.assertEqual(github.body, reviewed)
        self.assertIn("publish it in GitHub", printed)

    def test_apply_needs_the_same_reviewed_composition(self):
        github = FakeGitHub()
        self.assertEqual(self.run_body(github, "--apply")[0], 1, "nothing was reviewed yet")
        self.assertEqual(self.run_body(github)[0], 0)
        self.notes.write_text(NOTES + "\n- A late addition.\n", encoding="utf-8")
        status, _, errors = self.run_body(github, "--apply")
        self.assertEqual(status, 1)
        self.assertIn("changed since the reviewed composition", errors)
        self.assertEqual(github.edits, [])

    def test_a_published_release_is_never_changed(self):
        github = FakeGitHub(draft=False)
        self.assertEqual(self.run_body(github)[0], 0)
        status, _, errors = self.run_body(github, "--apply")
        self.assertEqual(status, 1)
        self.assertIn("is already published", errors)
        self.assertEqual(github.edits, [])

    def test_an_unconfirmed_update_fails(self):
        github = FakeGitHub()
        self.assertEqual(self.run_body(github)[0], 0)
        original = github.__call__

        def lossy(*args):
            result = original(*args)
            if args[:2] == ("release", "edit"):
                github.body = github.body.replace("production", "testing")
            return result

        errors = io.StringIO()
        with mock.patch.object(release_body, "gh", lossy), redirect_stdout(io.StringIO()), redirect_stderr(errors):
            status = release_body.main(["v1.0.0", "--notes", str(self.notes), "--apply"])
        self.assertEqual(status, 1)
        self.assertIn("differs from the reviewed one after the update", errors.getvalue())

    def test_working_notes_empty_notes_and_smuggled_markers_are_refused(self):
        working = self.root / "eosc-fair-guide_v1.0.0.working.md"
        working.write_text(NOTES, encoding="utf-8")
        with self.assertRaisesRegex(release_body.RefusedError, "never published"):
            release_body.notes_text(working)
        self.notes.write_text("# Release notes — eosc-fair-guide (v1.0.0)\n\n", encoding="utf-8")
        with self.assertRaisesRegex(release_body.RefusedError, "no notes below its title"):
            release_body.notes_text(self.notes)
        self.notes.write_text("## Other\n\n" + RECORD, encoding="utf-8")
        with self.assertRaisesRegex(release_body.RefusedError, "only the release workflow writes"):
            release_body.notes_text(self.notes)
        with self.assertRaisesRegex(release_body.RefusedError, "first"):
            release_body.notes_text(self.root / "missing.md")

    def test_a_body_without_one_marked_record_is_refused_with_the_fix(self):
        legacy = "Site of commit `" + "a" * 40 + "`, version 1.0.0.\nRelease status: testing (recorded by Tag release)."
        for body in (legacy, DRAFT + "\n" + RECORD, RECORD.replace(release_body.END, "")):
            with self.subTest(body=body[:30]), self.assertRaisesRegex(release_body.RefusedError, "GitHub editor"):
                release_body.verification(body)
        self.assertEqual(release_body.verification(DRAFT.replace("\n", "\r\n")), RECORD)

    def test_only_release_tags_are_accepted(self):
        for tag in ("1.0.0", "v1.0", "v01.0.0", "main"):
            with self.subTest(tag=tag), self.assertRaises(release_body.RefusedError):
                release_body.tag_version(tag)
        self.assertEqual(release_body.tag_version("v1.0.0-alpha.3"), "1.0.0-alpha.3")


if __name__ == "__main__":
    unittest.main()
