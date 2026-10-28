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
from publication_fixture import publication_files  # noqa: E402

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
        self.publication_url = "https://published.example/guide/"
        evidence = publication_files(self.publication_url, built=self.built, version=TAG[1:])
        self.config = evidence["assets/data/ui.js"].decode("utf-8")
        crate = json.loads(evidence["ro-crate-metadata.json"])
        crate["@graph"][0]["creativeWorkStatus"] = "production"
        crate["@graph"].append({"@id": "#guide-software", "creativeWorkStatus": "production"})
        files = {
            "index.html": "<!doctype html><title>Release fixture</title>",
            "assets/data/ui.js": self.config,
            "api/health.json": json.dumps(self.health),
            "ro-crate-metadata.json": json.dumps(crate),
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
            self.assertEqual((context / "publication-url.txt").read_text().strip(), self.publication_url)
        image_release.verify(self.health, self.built, COMMIT, self.config)

    def test_publication_url_is_verified_and_legacy_archives_are_not_rewritten(self) -> None:
        path = self.artifact / "manifest.json"
        manifest = json.loads(path.read_text())
        self.assertEqual(manifest["publication_url"], self.publication_url)
        manifest["publication_url"] = "https://unrelated.example/"
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "publication/semantic declaration differs"):
            image_release.prepare(self.artifact, self.root / "image", TAG, COMMIT, self.root)
        manifest.pop("publication_url")
        manifest.pop("semantic")
        path.write_text(json.dumps(manifest))
        original = {p: p.read_bytes() for p in self.artifact.iterdir()}
        image_release.prepare(self.artifact, self.root / "image", TAG, COMMIT, self.root)
        self.assertEqual({p: p.read_bytes() for p in self.artifact.iterdir()}, original)
        self.assertEqual((self.root / "image/publication-url.txt").read_text().strip(), self.publication_url)

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
