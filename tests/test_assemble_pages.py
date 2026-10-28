"""Production stays byte-identical while every preview HTML page is visibly excluded from indexing."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import assemble_pages  # noqa: E402
import build_api  # noqa: E402
import build_crate  # noqa: E402
import build_site  # noqa: E402
import package_site  # noqa: E402
from publication_fixture import publication_files  # noqa: E402
from publication_location import site_identity  # noqa: E402

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
            **publication_files(),
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
            **publication_files(),
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

    def assemble(self) -> list[str]:
        return assemble_pages.assemble(
            self.stage,
            STAGING,
            self.out,
            production=self.release,
            production_tag="v1.2.3-alpha.1",
            production_commit=PRODUCTION,
            root=self.root,
        )

    def stamp_release(self, files: dict[str, bytes]) -> None:
        """A release packaged since publication stamps: its manifest names the root and namespace it was built for."""
        self.files.update(files)
        self.write_release(self.files)
        inputs = site_identity(self.files)
        self.manifest.update(
            publication_url=inputs["publication_url"],
            semantic={key: inputs[key] for key in ("vocabulary_base", "profile")},
        )
        self.save_manifest()

    def stage_files(self, files: dict[str, bytes]) -> None:
        for name, data in files.items():
            (self.stage / name).write_bytes(data)

    def test_a_preview_with_the_next_namespace_is_published_beside_production_with_a_notice(self):
        # The reviewed namespace changed after the release: production keeps its own, unchanged bytes until the next
        # release, and the summary says that the two channels differ (decision 28).
        self.stage_files(publication_files("https://actual.example/", semantic="https://actual.example/"))
        notices = self.assemble()
        self.assertEqual((self.out / "ro-crate-metadata.json").read_bytes(), self.files["ro-crate-metadata.json"])
        self.assertEqual(len(notices), 1)
        for value in ("https://actual.example/terms#", "https://example.org/guide/terms#", "next release"):
            self.assertIn(value, notices[0])
        # The publish workflow copies these lines into its run summary.
        notes = self.root / "notes.md"
        arguments = ["--staging", str(self.stage), "--staging-commit", STAGING, "--out", str(self.root / "cli")]
        arguments += ["--production", str(self.release), "--production-tag", "v1.2.3-alpha.1"]
        arguments += ["--production-commit", PRODUCTION, "--notes", str(notes)]
        assemble = assemble_pages.assemble
        with (
            patch.object(
                assemble_pages, "assemble", lambda *args, **options: assemble(*args, **options, root=self.root)
            ),
            patch("builtins.print"),
        ):
            self.assertEqual(assemble_pages.main(arguments), 0)
        self.assertEqual(notes.read_text(encoding="utf-8"), f"- {notices[0]}\n")

    def test_sites_built_for_different_publication_roots_are_refused(self):
        self.assemble()
        before = (self.out / "index.html").read_bytes()
        self.stamp_release(publication_files("https://actual.example/project/"))
        with self.assertRaisesRegex(assemble_pages.AssemblyError, "different publication roots"):
            self.assemble()
        self.assertEqual((self.out / "index.html").read_bytes(), before, "the existing output stays")

    def test_a_release_aligns_the_namespace_and_keeps_earlier_archives(self):
        old = dict(self.files)
        target = "https://actual.example/project/"
        self.stamp_release(publication_files(target))
        archive_before = (self.release / "site.tar.gz").read_bytes()
        self.stage_files(publication_files(target))
        self.assertEqual(self.assemble(), [], "aligned channels need no notice")
        self.assertEqual((self.release / "site.tar.gz").read_bytes(), archive_before)
        self.assertEqual((self.out / "ro-crate-metadata.json").read_bytes(), self.files["ro-crate-metadata.json"])
        self.assertNotEqual(old["ro-crate-metadata.json"], self.files["ro-crate-metadata.json"])

    def test_new_declarations_cannot_forge_the_content_or_change_publication_root(self):
        self.assemble()
        before = (self.out / "index.html").read_bytes()
        inputs = site_identity(self.files)
        self.manifest.update(
            publication_url=inputs["publication_url"],
            semantic={key: inputs[key] for key in ("vocabulary_base", "profile")},
        )
        self.manifest["semantic"]["profile"] = "https://other.example/profile/0.1"
        self.save_manifest()
        with self.assertRaisesRegex(assemble_pages.AssemblyError, "differs from its contents"):
            self.assemble()
        self.manifest["semantic"]["profile"] = inputs["profile"]
        self.save_manifest()
        self.stage_files(publication_files("https://other.example/", semantic="https://example.org/guide/"))
        with self.assertRaisesRegex(assemble_pages.AssemblyError, "different publication roots"):
            self.assemble()
        self.assertEqual((self.out / "index.html").read_bytes(), before)

    def test_a_preview_keeping_the_release_namespace_at_the_actual_pages_location_needs_no_notice(self):
        self.stage_files(publication_files("https://actual.example/", semantic="https://example.org/guide/"))
        # Unstamped historical production derives its semantics from its own crate.
        self.assertEqual(self.assemble(), [])
        self.assertEqual((self.out / "ro-crate-metadata.json").read_bytes(), self.files["ro-crate-metadata.json"])

    def test_a_root_crawl_block_cannot_hide_preview_noindex(self):
        self.files.update(publication_files("https://example.org/"))
        self.files["robots.txt"] = b"User-agent: *\nDisallow: /next/"
        self.write_release(self.files)
        for name, data in publication_files("https://example.org/").items():
            (self.stage / name).write_bytes(data)
        with self.assertRaisesRegex(assemble_pages.AssemblyError, "blocks reading preview noindex"):
            self.assemble()
        self.assertFalse(self.out.exists())

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

    def test_a_preview_built_from_the_release_commit_says_it_is_that_release(self) -> None:
        # Tag release tags a commit the preview already serves; the preview's own footer predates the tag.
        (self.stage / "api/health.json").write_text(json.dumps(self.health(PRODUCTION)), encoding="utf-8")
        assemble_pages.assemble(
            self.stage,
            PRODUCTION,
            self.out,
            production=self.release,
            production_tag="v1.2.3-alpha.1",
            production_commit=PRODUCTION,
            root=self.root,
        )
        for name, data in self.files.items():
            self.assertEqual((self.out / name).read_bytes(), data, name)
        pages = list((self.out / "next").rglob("*.html"))
        self.assertEqual(len(pages), 4)
        for path in pages:
            text = path.read_text(encoding="utf-8")
            self.assertIn('<span lang="cs">Tento náhled je totožný s vydáním v1.2.3-alpha.1 (commit aaaaaaa).', text)
            self.assertIn('<span lang="en">This preview is identical to release v1.2.3-alpha.1 (commit aaaaaaa).', text)
            self.assertNotIn("Preview of the next release", text)
            self.assertIn('content="noindex"', text)
            home = re.search(r'<a href="([^"]+)"><span lang="cs">Otevřít vydání', text)[1]
            self.assertEqual((path.parent / home).resolve(), (self.out / "index.html").resolve(), path)
        # Once the default branch moves on, the preview announces the next release again.
        (self.stage / "api/health.json").write_text(json.dumps(self.health(STAGING)), encoding="utf-8")
        self.assemble()
        text = (self.out / "next/index.html").read_text(encoding="utf-8")
        self.assertIn("Preview of the next release", text)
        self.assertNotIn("identical to release", text)

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


@unittest.skipUnless(
    (build_api.SWAGGER_DIR / build_api.SWAGGER_FILES[0]).is_file(), "needs the Node packages: run npm ci"
)
class CrawlerFileTests(unittest.TestCase):
    """Issue #83 on the real build: crawler files follow the configured base and assembly keeps the release's own."""

    def build(self, site: Path, sha: str, base: str | None) -> str:
        with patch.dict(os.environ):
            os.environ.pop(build_crate.BASE_URL_ENV, None)
            if base:
                os.environ[build_crate.BASE_URL_ENV] = base
            build_site.build(site)
        # The checks' passed run, which packaging and assembly require of a built site.
        health = json.loads((site / package_site.HEALTH).read_text(encoding="utf-8"))
        health |= {"generated_at": "2026-10-25T12:00:00Z", "run": {"status": "passed"}, "revision": sha}
        (site / package_site.HEALTH).write_text(json.dumps(health), encoding="utf-8")
        configured = build_crate.load_toml(ROOT / "content/guide.toml")["guide"]["baseUrl"]
        return (base or configured).rstrip("/") + "/"

    def test_production_keeps_its_crawler_files_and_the_preview_adds_none(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        for origin in ("https://one.example", "https://two.example"):
            for prefix in ("/", "/a/guide/"):
                base = origin + prefix
                with self.subTest(base=base), tempfile.TemporaryDirectory(dir=ROOT / ".cache") as temporary:
                    work = Path(temporary)
                    production, preview, release, out = (
                        work / name for name in ("production", "preview", "release", "pages")
                    )
                    for site, sha in ((production, PRODUCTION), (preview, STAGING)):
                        self.build(site, sha, base)
                        self.assertEqual(
                            (site / "robots.txt").exists(), prefix == "/", "only the origin root controls robots"
                        )
                        if prefix == "/":
                            self.assertEqual(
                                (site / "robots.txt").read_text(),
                                f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n",
                            )
                        sitemap = ElementTree.parse(site / "sitemap.xml")
                        locations = [
                            loc.text for loc in sitemap.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                        ]
                        self.assertEqual(locations, [base, base + "api/index.html"])
                        self.assertFalse(any(node.tag.endswith("lastmod") for node in sitemap.iter()))
                    release.mkdir()
                    data = package_site.archive(production)
                    digest = hashlib.sha256(data).hexdigest()
                    (release / "site.tar.gz").write_bytes(data)
                    (release / "site.tar.gz.sha256").write_text(digest)
                    manifest = {
                        "archive": "site.tar.gz",
                        "commit": PRODUCTION,
                        "version": "1.2.3",
                        "sha256": digest,
                        "health": {"generated_at": "2026-10-25T12:00:00Z", "run": "passed"},
                    }
                    (release / "manifest.json").write_text(json.dumps(manifest))
                    assemble_pages.assemble(
                        preview, STAGING, out, production=release, production_tag="v1.2.3", production_commit=PRODUCTION
                    )
                    for path in production.rglob("*"):
                        if path.is_file() and path.name != build_crate.SITE_MARKER:
                            self.assertEqual((out / path.relative_to(production)).read_bytes(), path.read_bytes())
                    for name in build_crate.CRAWLER_FILES:
                        self.assertFalse((out / "next" / name).exists())
                    self.assertNotIn("/next/", (out / "sitemap.xml").read_text())
                    for path in (out / "next").rglob("*.html"):
                        self.assertIn('content="noindex"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
