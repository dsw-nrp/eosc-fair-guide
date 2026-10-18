"""The image consumes verified release bytes and refuses mismatches before replacing any output."""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402
import image_release  # noqa: E402
import package_site  # noqa: E402

COMMIT = "f" * 40
TAG = "v0.0.1"


class ImageReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(ROOT / "tests/fixtures/minimal/content", self.root / "content")
        shutil.copytree(ROOT / "docker", self.root / "docker")
        self.site = build_crate.replace_site(self.root / "site", self.root)
        self.built = {
            "version": TAG,
            "commit": COMMIT[:7],
            "date": "2026-10-17",
            "channel": "release",
            "dirty": False,
            "base": TAG,
            "status": "production",
        }
        self.health = {
            "build": self.built,
            "revision": COMMIT,
            "generated_at": "2026-10-17T00:00:00Z",
            "run": {"status": "passed"},
        }
        self.config = "window.FairGuideData.ui = " + json.dumps({"config": {"build": self.built}}) + ";\n"
        files = {
            "index.html": "<!doctype html><title>Release fixture</title>",
            "assets/data/ui.js": self.config,
            "api/health.json": json.dumps(self.health),
            "ro-crate-metadata.json": json.dumps(
                {"@graph": [{"@id": key, "creativeWorkStatus": "production"} for key in ("./", "#guide-software")]}
            ),
        }
        for name, text in files.items():
            path = self.site / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.artifact = self.root / "artifact"
        package_site.package(self.site, COMMIT, self.artifact, self.root)

    def test_exact_verified_bytes_and_repeat_preparation(self) -> None:
        context = self.root / "image"
        for _ in range(2):
            self.assertEqual(image_release.prepare(self.artifact, context, TAG, COMMIT, self.root), self.built)
            for path in self.site.rglob("*"):
                if path.is_file() and path.name != build_crate.SITE_MARKER:
                    self.assertEqual((context / "site" / path.relative_to(self.site)).read_bytes(), path.read_bytes())
            self.assertFalse((context / "site" / build_crate.SITE_MARKER).exists())
        image_release.verify(self.health, self.built, COMMIT, self.config)

    def test_manifest_or_served_identity_mismatch_is_refused(self) -> None:
        path = self.artifact / "manifest.json"
        original = json.loads(path.read_text())
        output = self.root / "image"
        image_release.prepare(self.artifact, output, TAG, COMMIT, self.root)
        for field in ("commit", "version", "date", "status"):
            bad = copy.deepcopy(original)
            bad["build"][field] = "planted mismatch"
            path.write_text(json.dumps(bad))
            with self.subTest(field=field), self.assertRaises(ValueError):
                image_release.prepare(self.artifact, output, TAG, COMMIT, self.root)
            self.assertEqual((output / "site/assets/data/ui.js").read_text(), self.config)
        path.write_text(json.dumps(original))
        for health, commit, config in (
            ({**self.health, "revision": "a" * 40}, COMMIT, self.config),
            (self.health, "a" * 40, self.config),
            (self.health, COMMIT, self.config.replace("production", "testing")),
        ):
            with self.assertRaises(ValueError):
                image_release.verify(health, self.built, commit, config)
