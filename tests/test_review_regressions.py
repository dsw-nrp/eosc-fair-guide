"""Regression boundaries from the pre-release review: shared identities and one site-build graph."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402
import build_site  # noqa: E402
import catalogue_identity  # noqa: E402
import check_content  # noqa: E402
import check_duplicates  # noqa: E402
import refresh_snapshots  # noqa: E402
from release_version import version  # noqa: E402


def gnu_tar() -> str | None:
    """The GNU tar the pinned Pages upload action archives with, or None when only another tar is present.

    The action runs on the Ubuntu runner, where ``tar`` is GNU tar; a Windows host resolves ``tar`` to
    bsdtar, which rejects its ``--force-local``/``--exclude`` semantics. An explicit ``TAR`` wins, then the
    path, then the usual Git for Windows location.
    """
    git = Path(os.environ.get("PROGRAMFILES") or r"C:\Program Files") / "Git" / "usr" / "bin" / "tar.exe"
    candidates = [os.environ["TAR"]] if os.environ.get("TAR") else []
    candidates += [shutil.which("tar") or "", str(git)]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            probe = subprocess.run(
                [candidate, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        if "GNU tar" in probe.stdout:
            return candidate
    return None


class ReviewRegressions(unittest.TestCase):
    def test_upload_archive_excludes_marker_without_removing_the_repeat_build_guard(self) -> None:
        tar = gnu_tar()
        if tar is None:
            self.skipTest("GNU tar is required to replay the pinned Pages upload action's archive command")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for _ in range(2):
                site = build_crate.replace_site(root / "pages", root)
                (site / "index.html").write_text("<!doctype html>")
                archive = root / "artifact.tar"
                subprocess.run(
                    [
                        tar,
                        "--force-local",
                        "--directory",
                        str(site),
                        "--dereference",
                        "--hard-dereference",
                        "-cf",
                        str(archive),
                        "--exclude=.git",
                        "--exclude=.github",
                        "--exclude=.[^/]*",
                        ".",
                    ],
                    check=True,
                    capture_output=True,
                )
                with tarfile.open(archive) as packed:
                    self.assertEqual([member.name for member in packed if member.isfile()], ["./index.html"])
                self.assertTrue((site / build_crate.SITE_MARKER).is_file())

    def test_cross_runtime_normalization_and_version_fixture(self) -> None:
        fixture = json.loads((ROOT / "tests/fixtures/normalization.json").read_text(encoding="utf-8"))
        for value, expected in fixture["addresses"]:
            for owner in (catalogue_identity, build_crate, check_duplicates, refresh_snapshots):
                self.assertEqual(owner.bare_url(value), expected)
        self.assertIs(check_content.as_list, build_crate.as_list)
        self.assertIs(check_content.LANGS, build_crate.LANGS)
        for value in fixture["versions"]["valid"]:
            self.assertEqual(version(value), value)
        for value in fixture["versions"]["invalid"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                version(value)

    def test_site_consumers_share_one_content_parse_and_crate(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as temporary:
            out = Path(temporary) / "site"
            with (
                patch.object(build_crate, "load_content", wraps=build_crate.load_content) as content,
                patch.object(build_crate, "build_crate", wraps=build_crate.build_crate) as crate,
            ):
                generated = build_site.build(out)
                self.assertEqual(content.call_count, 1)
                self.assertEqual(crate.call_count, 1)
            self.assertEqual(
                (out / "ro-crate-metadata.json").read_text(encoding="utf-8"), generated[build_crate.CRATE_FILE]
            )
            self.assertEqual((out / "ro-crate-preview.html").read_bytes(), (out / "index.html").read_bytes())
            api = json.loads((out / "api/health.json").read_text(encoding="utf-8"))
            self.assertEqual(api["build"], build_crate.build_identity_facts())
