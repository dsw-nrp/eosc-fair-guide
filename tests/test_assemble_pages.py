"""Production stays byte-identical while every preview HTML page is visibly excluded from indexing."""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import assemble_pages  # noqa: E402
import build_crate  # noqa: E402

PRODUCTION = "a" * 40
STAGING = "b" * 40
HTML = (
    '<!doctype html><html><head><meta name="robots" content="index,follow">'
    "<title>Guide</title></head><body>Content</body></html>"
)


class AssemblyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = build_crate.claim_site(self.root / "stage", self.root)
        self.out = self.root / "pages"
        self.release = self.root / "release"
        self.release.mkdir()
        self.files = {
            "index.html": HTML.encode(),
            "api/health.json": json.dumps(self.health(PRODUCTION)).encode(),
            "linkset.json": b'{"anchor":"https://example.org/guide/"}',
            "sitemap.xml": b"<urlset><loc>https://example.org/guide/</loc></urlset>",
            "assets/js/app.js": b"window.example = true;",
        }
        self.write_release(self.files)
        for name, data in {
            "index.html": HTML.encode(),
            "api/index.html": HTML.encode(),
            "profile/0.1/index.html": HTML.encode(),
            "assets/js/tests/index.html": HTML.encode(),
            "assets/css/staging.css": (ROOT / "assets/css/staging.css").read_bytes(),
            "api/health.json": json.dumps(self.health(STAGING)).encode(),
            "openapi.json": b'{"servers":[{"url":"https://example.org/guide/"}],"paths":{}}',
            "linkset.json": self.files["linkset.json"],
        }.items():
            path = self.stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    @staticmethod
    def health(sha: str) -> dict:
        return {"generated_at": "2026-10-14T12:00:00Z", "run": {"status": "passed"}, "revision": sha}

    def write_release(self, files: dict[str, bytes], extra: tarfile.TarInfo | None = None) -> None:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as packed:
            for name, data in files.items():
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                packed.addfile(entry, io.BytesIO(data))
            if extra:
                packed.addfile(extra)
        data = buffer.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        (self.release / "site.tar.gz").write_bytes(data)
        (self.release / "site.tar.gz.sha256").write_text(digest, encoding="utf-8")
        self.manifest = {
            "archive": "site.tar.gz",
            "commit": PRODUCTION,
            "version": "1.2.3-alpha.1",
            "sha256": digest,
            "health": {"generated_at": "2026-10-14T12:00:00Z", "run": "passed"},
        }
        self.save_manifest()

    def save_manifest(self) -> None:
        (self.release / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def assemble(self) -> None:
        assemble_pages.assemble(
            self.stage,
            STAGING,
            self.out,
            production=self.release,
            production_tag="v1.2.3-alpha.1",
            production_commit=PRODUCTION,
            root=self.root,
        )

    def test_both_trees_are_combined_without_changing_a_production_byte(self) -> None:
        self.assemble()
        for name, data in self.files.items():
            self.assertEqual((self.out / name).read_bytes(), data, name)
        pages = list((self.out / "next").rglob("*.html"))
        self.assertEqual(len(pages), 4)
        for path in pages:
            text = path.read_text(encoding="utf-8")
            self.assertIn('content="noindex"', text)
            self.assertNotIn('content="index,follow"', text)
            self.assertIn('class="staging-notice"', text)
            self.assertIn('lang="cs"', text)
            self.assertIn('lang="en"', text)
            for marker in text.split('href="')[1:]:
                href = marker.split('"')[0]
                self.assertTrue((path.parent / href).resolve().is_file(), href)
        self.assertNotIn(b"/next/", (self.out / "linkset.json").read_bytes())
        self.assertNotIn(b"/next/", (self.out / "sitemap.xml").read_bytes())
        self.assertEqual((self.out / "next/linkset.json").read_bytes(), self.files["linkset.json"])
        self.assertFalse((self.out / "next" / build_crate.SITE_MARKER).exists())
        preview_api = json.loads((self.out / "next/openapi.json").read_text(encoding="utf-8"))
        self.assertEqual(preview_api["servers"][0]["url"], ".", "preview API requests stay on the preview")
        (self.stage / "index.html").write_text(HTML.replace("Content", "New preview"), encoding="utf-8")
        self.assemble()
        self.assertEqual((self.out / "index.html").read_bytes(), self.files["index.html"])
        self.assertIn("New preview", (self.out / "next/index.html").read_text(encoding="utf-8"))

    def test_no_tag_yet_publishes_only_an_explained_preview(self) -> None:
        assemble_pages.assemble(self.stage, STAGING, self.out, root=self.root)
        self.assertIn("no published release", (self.out / "index.html").read_text(encoding="utf-8"))
        self.assertIn('content="noindex"', (self.out / "next/index.html").read_text(encoding="utf-8"))
        self.assertFalse((self.out / "api").exists())

    def test_invalid_artifacts_preserve_an_existing_output(self) -> None:
        self.assemble()
        original = (self.out / "index.html").read_bytes()
        for key, value in (
            ("commit", STAGING),
            ("version", "9.9.9"),
            ("sha256", "f" * 64),
            ("archive", "../site.tar.gz"),
        ):
            saved = self.manifest[key]
            self.manifest[key] = value
            self.save_manifest()
            with self.subTest(key), self.assertRaises(assemble_pages.AssemblyError):
                self.assemble()
            self.assertEqual((self.out / "index.html").read_bytes(), original)
            self.manifest[key] = saved
        self.save_manifest()
        self.files["api/health.json"] = json.dumps(self.health(STAGING)).encode()
        self.write_release(self.files)
        with self.assertRaisesRegex(assemble_pages.AssemblyError, "checked commit"):
            self.assemble()
        self.assertEqual((self.out / "index.html").read_bytes(), original)

    def test_unsafe_archive_members_are_refused_before_writing(self) -> None:
        for name in ("../escaped.txt", "/absolute.txt", "assets/../../escaped.txt", "next/index.html"):
            with self.subTest(name):
                self.write_release({**self.files, name: b"unsafe"})
                with self.assertRaises(assemble_pages.AssemblyError):
                    self.assemble()
                self.assertFalse(self.out.exists())
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            entry = tarfile.TarInfo("link")
            entry.type, entry.linkname = kind, "index.html"
            self.write_release(self.files, entry)
            with self.assertRaises(assemble_pages.AssemblyError):
                self.assemble()
            self.assertFalse(self.out.exists())

    def test_output_overlap_authored_trees_and_unverified_staging_are_refused(self) -> None:
        for out in (self.stage, self.stage / "nested", self.root, self.root / "assets"):
            with self.subTest(out), self.assertRaises((assemble_pages.AssemblyError, build_crate.ContentError)):
                assemble_pages.assemble(self.stage, STAGING, out, root=self.root)
        report = self.stage / "api/health.json"
        report.write_text(json.dumps(self.health(PRODUCTION)), encoding="utf-8")
        with self.assertRaisesRegex(assemble_pages.AssemblyError, "staging health"):
            assemble_pages.assemble(self.stage, STAGING, self.out, root=self.root)
        self.assertFalse(self.out.exists())

    def test_markup_in_scripts_and_old_robots_tags_do_not_confuse_the_transform(self) -> None:
        text = (
            '<html><HEAD><META NAME="ROBOTS" CONTENT="index">'
            '<script>const example = "<body>";</script></HEAD><BODY>text</BODY></html>'
        )
        result = assemble_pages.preview_html(text.encode(), "api/index.html").decode()
        self.assertEqual(result.count('name="robots"'), 1)
        self.assertIn('href="../assets/css/staging.css"', result)
        self.assertIn('const example = "<body>";', result)
        self.assertTrue(result.index("<BODY>") < result.index('class="staging-notice"'))

    def test_cross_platform_path_collisions_are_rejected_before_replacement(self) -> None:
        for name in ("INDEX.html", "assets", "NUL", "trailing."):
            with self.subTest(name):
                self.write_release({**self.files, name: b"collision"})
                with self.assertRaises(assemble_pages.AssemblyError):
                    self.assemble()
                self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
