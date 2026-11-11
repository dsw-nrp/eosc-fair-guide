"""The image consumes verified release bytes and refuses mismatches before replacing any output."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import shutil
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import assemble_pages  # noqa: E402
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
        production = {"@id": "https://published.example/guide/id/vocabularies/release-statuses/production"}
        crate["@graph"][0]["releaseStatus"] = production
        files = {
            "index.html": "<!doctype html><title>Release fixture</title>",
            "assets/data/ui.js": self.config,
            "api/v1/health.json": json.dumps(self.health),
            "ro-crate-metadata.json": json.dumps(crate),
            "404.html": publication_files()["404.html"],
        }
        for name, text in files.items():
            path = self.site / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)
        self.artifact = self.root / "artifact"
        package_site.package(self.site, COMMIT, self.artifact, self.root)

    def rewrite_artifact(self, files: dict[str, bytes]) -> None:
        """Replace the packaged bytes and digest together, keeping the release's verified identity intact."""
        manifest_path = self.artifact / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as packed:
            for name, data in sorted(files.items()):
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                packed.addfile(entry, io.BytesIO(data))
        data = buffer.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        (self.artifact / manifest["archive"]).write_bytes(data)
        (self.artifact / (manifest["archive"] + ".sha256")).write_text(f"{digest}  {manifest['archive']}\n")
        manifest["sha256"] = digest
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def predecessor_files(self) -> dict[str, bytes]:
        """A real predecessor-shaped archive: old health and status, with no generated 404."""
        files = assemble_pages.production_files(self.artifact, TAG, COMMIT)
        files["api/health.json"] = files.pop(package_site.HEALTH)
        del files["404.html"]
        crate = json.loads(files[build_crate.CRATE_FILE])
        for node in crate["@graph"]:
            node.pop("releaseStatus", None)
            if node["@id"] in ("./", "#guide-software"):
                node["creativeWorkStatus"] = self.built["status"]
        files[build_crate.CRATE_FILE] = json.dumps(crate).encode()
        return files

    def status_files(self, layout: str, root_status: str, software_status: str, dual=False) -> dict[str, bytes]:
        files = (
            assemble_pages.production_files(self.artifact, TAG, COMMIT)
            if layout == "current"
            else self.predecessor_files()
        )
        crate = json.loads(files[build_crate.CRATE_FILE])
        nodes = {node["@id"]: node for node in crate["@graph"]}
        production = {"@id": "https://published.example/guide/id/vocabularies/release-statuses/production"}
        for key, prop in (("./", root_status), ("#guide-software", software_status)):
            nodes[key].pop("releaseStatus", None)
            nodes[key].pop("creativeWorkStatus", None)
            if prop is not None:
                nodes[key][prop] = production if prop == "releaseStatus" else self.built["status"]
            if dual:
                nodes[key]["creativeWorkStatus" if prop == "releaseStatus" else "releaseStatus"] = (
                    self.built["status"] if prop == "releaseStatus" else production
                )
        files[build_crate.CRATE_FILE] = json.dumps(crate).encode()
        return files

    def test_exact_verified_bytes_and_repeat_preparation(self) -> None:
        context = self.root / "image"
        for _ in range(2):
            self.assertEqual(image_release.prepare(self.artifact, context, TAG, COMMIT, self.root), self.built)
            for path in self.site.rglob("*"):
                if path.is_file() and path.name != build_crate.SITE_MARKER:
                    self.assertEqual((context / "site" / path.relative_to(self.site)).read_bytes(), path.read_bytes())
            self.assertFalse((context / "site" / build_crate.SITE_MARKER).exists())
            self.assertEqual((context / "publication-url.txt").read_text().strip(), self.publication_url)
            self.assertEqual((context / "health-path.txt").read_text(), "api/v1/health.json\n")
        image_release.verify(self.health, self.built, COMMIT, self.config)

    def test_status_layout_is_parsed_once_per_image_preparation(self) -> None:
        for layout in ("current", "predecessor"):
            with self.subTest(layout=layout):
                if layout == "predecessor":
                    self.rewrite_artifact(self.predecessor_files())
                with mock.patch.object(
                    assemble_pages, "release_statuses", wraps=assemble_pages.release_statuses
                ) as statuses:
                    image_release.prepare(self.artifact, self.root / ("image-" + layout), TAG, COMMIT, self.root)
                self.assertEqual(statuses.call_count, 1)

    def test_predecessor_schema_preparation_and_health_probe(self) -> None:
        files = self.predecessor_files()
        self.rewrite_artifact(files)
        context = self.root / "image"
        for _ in range(2):
            self.assertEqual(image_release.prepare(self.artifact, context, TAG, COMMIT, self.root), self.built)
            self.assertEqual((context / "health-path.txt").read_text(), "api/health.json\n")
            for name, data in files.items():
                self.assertEqual((context / "site" / name).read_bytes(), data, name)
            self.assertFalse((context / "site/404.html").exists())
        image_release.verify(self.health, self.built, COMMIT, self.config)

    def test_mixed_missing_and_split_status_layouts_are_refused_before_replacement(self) -> None:
        context = self.root / "image"
        image_release.prepare(self.artifact, context, TAG, COMMIT, self.root)
        before = {path.relative_to(context): path.read_bytes() for path in context.rglob("*") if path.is_file()}
        valid = assemble_pages.production_files(self.artifact, TAG, COMMIT)
        cases = (
            ("current", "creativeWorkStatus", "creativeWorkStatus", False),
            ("predecessor", "releaseStatus", "releaseStatus", False),
            ("current", "releaseStatus", "creativeWorkStatus", False),
            ("predecessor", "creativeWorkStatus", "releaseStatus", False),
            ("current", "releaseStatus", None, False),
            ("current", "releaseStatus", "releaseStatus", True),
        )
        for layout, root_status, software_status, dual in cases:
            with self.subTest(layout=layout, root=root_status, software=software_status, dual=dual):
                self.rewrite_artifact(self.status_files(layout, root_status, software_status, dual))
                with self.assertRaisesRegex(ValueError, "status layout"):
                    image_release.prepare(self.artifact, context, TAG, COMMIT, self.root)
                after = {path.relative_to(context): path.read_bytes() for path in context.rglob("*") if path.is_file()}
                self.assertEqual(after, before)
                self.rewrite_artifact(valid)

    def test_ambiguous_health_layout_is_refused(self) -> None:
        files = self.predecessor_files()
        files[package_site.HEALTH] = json.dumps(self.health).encode()
        self.rewrite_artifact(files)
        with self.assertRaisesRegex(ValueError, "exactly one recognized health result"):
            image_release.prepare(self.artifact, self.root / "image", TAG, COMMIT, self.root)

    def test_nginx_protects_every_supported_health_layout(self) -> None:
        config = (ROOT / "docker" / "nginx.conf").read_text(encoding="utf-8")
        self.assertEqual(config.count('add_header Cache-Control "no-store";'), 2)
        for path in ("/api/v1/health.json", "/api/health.json"):
            self.assertIn(f"location = {path} {{", config)

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
