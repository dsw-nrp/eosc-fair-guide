"""Release packaging carries only the exact site that passed the checks, reproducibly and labelled by commit."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402
import package_site  # noqa: E402

COMMIT = "f" * 40


class PackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "guide"
        shutil.copytree(ROOT / "tests/fixtures/minimal", self.root)
        self.site = self.root / "_site"
        build_crate.replace_site(self.site, self.root)
        (self.site / "api").mkdir()
        (self.site / "index.html").write_text("<!doctype html>", encoding="utf-8")
        self.built = {
            "version": "v0.0.1",
            "commit": COMMIT[:7],
            "date": "2026-10-17",
            "channel": "release",
            "dirty": False,
            "base": "v0.0.1",
            "status": "testing",
        }
        config = self.site / "assets/data/ui.js"
        config.parent.mkdir(parents=True)
        config.write_text("window.FairGuideData.ui = " + json.dumps({"config": {"build": self.built}}) + ";\n")
        self.health({"generated_at": "2026-10-12T00:00:00Z", "run": {"status": "passed"}, "revision": COMMIT})

    def tearDown(self) -> None:
        self.temp.cleanup()

    def health(self, report: dict) -> None:
        report = {"build": self.built, **report}
        (self.site / package_site.HEALTH).write_text(json.dumps(report), encoding="utf-8")

    def test_a_verified_site_becomes_one_labelled_reproducible_archive(self) -> None:
        output = Path(self.temp.name) / "release"
        manifest = package_site.package(self.site, COMMIT, output, self.root)
        self.assertEqual(manifest["name"], "eosc-fair-guide-site-0.0.1-ffffffffffff")
        archive = (output / manifest["archive"]).read_bytes()
        self.assertEqual(hashlib.sha256(archive).hexdigest(), manifest["sha256"])
        self.assertEqual((output / f"{manifest['archive']}.sha256").read_text().split()[0], manifest["sha256"])
        with tarfile.open(output / manifest["archive"]) as tar:
            names = tar.getnames()
            self.assertTrue(all(member.mtime == 0 and member.uid == 0 for member in tar.getmembers()))
        self.assertEqual(
            sorted(names),
            ["api/health.json", "assets/data/ui.js", "index.html"],
            "the site's own files, not the marker",
        )
        again = package_site.package(self.site, COMMIT, Path(self.temp.name) / "again", self.root)
        self.assertEqual(again["sha256"], manifest["sha256"], "the same site gives the same bytes")
        self.assertEqual(json.loads((output / "manifest.json").read_text())["health"]["run"], "passed")

    def test_unverified_or_foreign_sites_are_refused(self) -> None:
        output = Path(self.temp.name) / "release"
        for report, reason in (
            ({"generated_at": None, "run": {"status": "not_run"}}, "only the build's inventory"),
            ({"generated_at": "2026-10-12T00:00:00Z", "run": {"status": "failed"}}, "not passed"),
            ({"generated_at": "2026-10-12T00:00:00Z", "run": {"status": "partial"}}, "not passed"),
        ):
            self.health(report)
            with self.subTest(reason), self.assertRaisesRegex(package_site.PackageError, reason):
                package_site.package(self.site, COMMIT, output, self.root)
        foreign = Path(self.temp.name) / "foreign"
        (foreign / "api").mkdir(parents=True)
        (foreign / package_site.HEALTH).write_text(
            '{"generated_at": "x", "run": {"status": "passed"}}', encoding="utf-8"
        )
        with self.assertRaisesRegex(package_site.PackageError, "not a verified built site"):
            package_site.package(foreign, COMMIT, output, self.root)
        with self.assertRaisesRegex(package_site.PackageError, "full SHA"):
            package_site.package(self.site, "abc", output, self.root)
        self.assertFalse(output.exists(), "nothing is written for a refused site")


if __name__ == "__main__":
    unittest.main()
