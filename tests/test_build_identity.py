"""The build identity derived from git: release, next, local, and the release-status rule."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_identity  # noqa: E402

TODAY = date(2026, 1, 2)


class IdentityTests(unittest.TestCase):
    def identity(self, responses, status=None, mode="production"):
        def fake(_root, *args):
            if args[:2] == ("cat-file", "-t"):
                return "tag"
            if args[:2] == ("for-each-ref", "--format=%(contents)"):
                return "" if status is None else f"Fair-Guide-Release-Status: {status}\n"
            return responses.get(args)

        with patch.object(build_identity, "_git", fake), patch.dict(os.environ, FAIR_GUIDE_RELEASE_TAG=""):
            return build_identity.identity(today=TODAY, mode=mode)

    def test_dirty_local_and_preview_tag_builds_never_claim_a_released_site(self) -> None:
        clean = {
            ("rev-parse", "--short", "HEAD"): "abc1234",
            ("status", "--porcelain"): "",
            ("describe", "--tags", "--exact-match", "--match", "v*"): "v1.0.0",
        }
        for mode in ("local", "preview"):
            built = self.identity(clean, status="production", mode=mode)
            self.assertNotEqual(built["channel"], "release")
            self.assertEqual(built["status"], "testing")
        built = self.identity({**clean, ("status", "--porcelain"): " M content/guide.toml"}, status="production")
        self.assertNotEqual(built["channel"], "release")
        self.assertEqual(built["status"], "testing")

    def test_an_exact_tag_is_a_release_and_reads_its_annotation(self) -> None:
        responses = {
            ("rev-parse", "--short", "HEAD"): "abc1234",
            ("status", "--porcelain"): "",
            ("describe", "--tags", "--exact-match", "--match", "v*"): "v1.0.0",
            ("log", "-1", "--format=%cs", "v1.0.0"): "2026-01-01",
        }
        identity = self.identity(responses, status="production")
        self.assertEqual(identity["channel"], "release")
        self.assertEqual(identity["version"], "v1.0.0")
        self.assertEqual(identity["status"], "production")
        self.assertEqual(identity["date"], "2026-01-01")

    def test_ahead_of_the_last_tag_is_next_and_always_testing(self) -> None:
        responses = {
            ("rev-parse", "--short", "HEAD"): "def5678",
            ("status", "--porcelain"): "",
            ("describe", "--tags", "--exact-match", "--match", "v*"): None,
            ("describe", "--tags", "--abbrev=0", "--match", "v*"): "v1.0.0",
            ("rev-list", "--count", "v1.0.0..HEAD"): "7",
        }
        identity = self.identity(responses, status="production")
        self.assertEqual(identity["channel"], "next")
        self.assertEqual(identity["version"], "v1.0.0+7")
        self.assertEqual(identity["base"], "v1.0.0")
        self.assertEqual(identity["status"], "testing")
        self.assertEqual(identity["date"], "2026-01-02")

    def test_no_usable_tag_is_a_local_build(self) -> None:
        responses = {
            ("rev-parse", "--short", "HEAD"): "c0ffee0",
            ("status", "--porcelain"): " M content/guide.toml",
            ("describe", "--tags", "--exact-match", "--match", "v*"): None,
            ("describe", "--tags", "--abbrev=0", "--match", "v*"): None,
        }
        identity = self.identity(responses)
        self.assertEqual(identity["channel"], "local")
        self.assertEqual(identity["version"], "c0ffee0")
        self.assertTrue(identity["dirty"])
        self.assertEqual(identity["status"], "testing")

    def test_status_defaults_to_testing_and_an_unknown_value_is_refused(self) -> None:
        responses = {
            ("rev-parse", "--short", "HEAD"): "abc1234",
            ("status", "--porcelain"): "",
            ("describe", "--tags", "--exact-match", "--match", "v*"): "v1.0.0",
            ("log", "-1", "--format=%cs", "v1.0.0"): "2026-01-01",
        }
        with self.assertRaisesRegex(ValueError, "status marker"):
            self.identity(responses, status="bogus")
        self.assertEqual(self.identity(responses, status=None)["status"], "testing")

    def test_repository_variable_cannot_override_the_tag_decision(self) -> None:
        responses = {
            ("rev-parse", "--short", "HEAD"): "abc1234",
            ("status", "--porcelain"): "",
            ("describe", "--tags", "--exact-match", "--match", "v*"): "v1.0.0",
        }
        for configured in ("", "testing", "production", "released", "Production"):
            with self.subTest(configured=configured), patch.dict(os.environ, RELEASE_STATUS=configured):
                self.assertEqual(self.identity(responses, status="production")["status"], "production")
                self.assertEqual(self.identity(responses)["status"], "testing")

    def test_malformed_or_unreadable_tag_status_is_refused(self) -> None:
        for contents in (
            None,
            "Fair-Guide-Release-Status: released",
            "Fair-Guide-Release-Status: Production",
            "Fair-Guide-Release-Status: testing\nFair-Guide-Release-Status: production",
        ):

            def fake(_root, *args, marker=contents):
                return "tag" if args[0] == "cat-file" else marker

            with (
                self.subTest(contents=contents),
                patch.object(build_identity, "_git", side_effect=fake),
                self.assertRaises(ValueError),
            ):
                build_identity.tag_status(ROOT, "v1.0.0")

    def test_real_tags_bind_the_choice_and_selected_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                return subprocess.check_output(
                    ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args],
                    cwd=root,
                    text=True,
                ).strip()

            git("init", "-q")
            git("commit", "--allow-empty", "-qm", "Fixture\n\nFair-Guide-Release-Status: production")
            git("tag", "-a", "v1.0.0", "-m", "Release v1.0.0\n\nFair-Guide-Release-Status: production")
            git("tag", "v1.0.1")
            with patch.dict(os.environ, FAIR_GUIDE_RELEASE_TAG="v1.0.0", RELEASE_STATUS="testing"):
                built = build_identity.identity(root, mode="production")
                self.assertEqual((built["version"], built["status"]), ("v1.0.0", "production"))
                self.assertEqual(build_identity.identity(root, mode="preview")["status"], "testing")
            with patch.dict(os.environ, FAIR_GUIDE_RELEASE_TAG="v1.0.1"):
                self.assertEqual(build_identity.identity(root, mode="production")["status"], "testing")
            git("commit", "--allow-empty", "-qm", "Later")
            with (
                patch.dict(os.environ, FAIR_GUIDE_RELEASE_TAG="v1.0.0"),
                self.assertRaisesRegex(ValueError, "does not name this checkout"),
            ):
                build_identity.identity(root, mode="production")

    def test_without_git_the_build_is_local(self) -> None:
        identity = self.identity({})
        self.assertEqual(identity["channel"], "local")
        self.assertEqual(identity["version"], "unknown")


if __name__ == "__main__":
    unittest.main()
