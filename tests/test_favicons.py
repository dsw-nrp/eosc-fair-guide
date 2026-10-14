"""Tests for scripts/vendor_favicons.py: which host stands for a tool, which icon is tried first, which bytes count
as an image, how a refresh replaces the folder without keeping originals, and what the check refuses."""

from __future__ import annotations

import hashlib
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402
import vendor_favicons as vf  # noqa: E402


def png(size: int = vf.SIZE) -> bytes:
    """A blank PNG of the given side, enough for the header the check reads."""
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00" * size * 4 for _ in range(size))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


class HostTests(unittest.TestCase):
    def test_a_platform_stands_only_for_its_home_page(self) -> None:
        self.assertEqual(vf.stands_for("https://www.example.org/tool"), "example.org")
        self.assertEqual(vf.stands_for("https://github.com/"), "github.com")
        self.assertIsNone(vf.stands_for("https://github.com/someone/tool"))
        self.assertIsNone(vf.stands_for("http://example.org/"), "an address that is not HTTPS has no favicon")


class CandidateTests(unittest.TestCase):
    def test_icons_are_tried_best_first_and_favicon_ico_last(self) -> None:
        html = """<head><link rel="apple-touch-icon" href="/touch.png">
        <link rel="icon" sizes="16x16" href="/16.png"><link rel="icon" sizes="64x64" href="/64.png">
        <link rel="icon" sizes="32x32" href="/32.png"><link rel="shortcut icon" href="/plain.ico">
        <link rel="icon" type="image/svg+xml" href="/logo.svg"><link rel="icon" href="http://example.org/x.png"></head>"""
        self.assertEqual(
            vf.candidates("https://example.org/page", html),
            [
                "https://example.org/logo.svg",
                "https://example.org/64.png",
                "https://example.org/32.png",
                "https://example.org/plain.ico",
                "https://example.org/touch.png",
                "https://example.org/16.png",
                "https://example.org/favicon.ico",
            ],
        )

    def test_only_plain_images_count(self) -> None:
        self.assertEqual(vf.image_kind(png()), "png")
        self.assertEqual(vf.image_kind(b"\x00\x00\x01\x00rest"), "ico")
        self.assertEqual(vf.image_kind(b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'), "svg")
        self.assertIsNone(vf.image_kind(b"<html><body>Not found</body></html>"))
        for hostile in (
            b"<svg><script>alert(1)</script></svg>",
            b'<svg><a href="javascript:alert(1)"><path/></a></svg>',
            b'<svg onload="alert(1)"><path/></svg>',
            b'<svg><image href="https://tracker.example/pixel.png"/></svg>',
            b"<svg><foreignObject><p>x</p></foreignObject></svg>",
        ):
            self.assertIsNone(vf.image_kind(hostile), hostile)


class VendorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        content = self.root / "content"
        content.mkdir()
        (content / "guide.toml").write_text(
            '[guide]\n\n[[resourceType]]\nid = "tool"\nfipDashboard = ["tool"]\n', encoding="utf-8"
        )
        (content / "resources.toml").write_text(
            '[[resource]]\nid = "a"\ntype = "tool"\nurl = "https://a.example.org/app"\n\n'
            '[[resource]]\nid = "b"\ntype = "tool"\nurl = "https://b.example.org/"\n\n'
            '[[resource]]\nid = "c"\ntype = "standard"\nurl = "https://c.example.org/"\n\n'
            '[[resource]]\nid = "d"\ntype = "tool"\nurl = "https://github.com/someone/d"\n',
            encoding="utf-8",
        )
        self.responses = {
            "https://a.example.org/": b'<link rel="icon" href="/a.svg"><link rel="icon" href="/a.png">',
            "https://a.example.org/a.svg": b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>',
            "https://a.example.org/a.png": png(16),
            "https://b.example.org/": b"<title>B</title>",
            "https://b.example.org/favicon.ico": b"<html>not found</html>",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fetch(self, url: str, limit: int) -> tuple[str, bytes]:
        if url not in self.responses:
            raise OSError(url)
        return url, self.responses[url][: limit + 1]

    def test_only_tools_and_services_are_asked_and_a_platform_tool_is_not(self) -> None:
        self.assertEqual(
            vf.service_urls(self.root),
            {"a.example.org": "https://a.example.org/app", "b.example.org": "https://b.example.org/"},
        )

    def test_the_first_icon_that_shows_is_kept_normalised_and_the_originals_are_not(self) -> None:
        seen: list[str] = []

        def normalise(originals: Path, output: Path) -> list[str]:
            seen.extend(sorted(path.name for path in originals.iterdir()))
            # The SVG draws nothing visible; the PNG is drawn into the normalised square.
            (output / "a.example.org~1.png").write_bytes(png())
            return ["a.example.org~0"]

        count, missing = vf.vendor(self.root, self.fetch, "2026-10-13", normalise)
        self.assertEqual(seen, ["a.example.org~0.svg", "a.example.org~1.png"], "every usable icon of a host is offered")
        self.assertEqual((count, missing), (1, ["b.example.org"]), "a site without an image keeps its monogram")
        folder = self.root / vf.TARGET
        self.assertEqual(sorted(path.name for path in folder.iterdir()), ["a.example.org.png", "sources.toml"])
        record = (folder / "sources.toml").read_text(encoding="utf-8")
        self.assertIn('source = "https://a.example.org/a.png"', record)
        self.assertIn("retrieved = 2026-10-13", record)
        self.assertFalse((self.root / vf.WORK).exists(), "the originals are removed")
        self.assertEqual(vf.check(self.root), [])

    def test_the_page_learns_which_hosts_have_a_favicon(self) -> None:
        fixture = self.root / "fixture"
        shutil.copytree(ROOT / "tests" / "fixtures" / "minimal", fixture)
        record = fixture / vf.MANIFEST
        record.parent.mkdir(parents=True)
        record.write_text(
            '[[favicon]]\nhost = "a.example.org"\nfile = "a.example.org.png"\n\n'
            '[[favicon]]\nhost = "github.com"\nfile = "github.com.png"\nhomeOnly = true\n',
            encoding="utf-8",
        )
        config = build_crate.page_config(build_crate.load_content(fixture / "content"))["config"]["favicons"]
        self.assertEqual(config, {"hosts": ["a.example.org", "github.com"], "homeOnly": ["github.com"]})

    def test_the_check_refuses_changed_unrecorded_and_wrongly_sized_files(self) -> None:
        vf.vendor(
            self.root,
            self.fetch,
            "2026-10-13",
            lambda originals, output: (output / "a.example.org~1.png").write_bytes(png()) and [],
        )
        folder = self.root / vf.TARGET
        (folder / "a.example.org.png").write_bytes(png(32))
        (folder / "stray.png").write_bytes(png())
        problems = vf.check(self.root)
        self.assertTrue(any("a.example.org.png: differs" in problem for problem in problems), problems)
        self.assertTrue(any(f"not a {vf.SIZE}-pixel PNG" in problem for problem in problems), problems)
        self.assertTrue(any("stray.png: not recorded" in problem for problem in problems), problems)
        self.assertEqual(hashlib.sha256(png()).hexdigest() != hashlib.sha256(png(32)).hexdigest(), True)


if __name__ == "__main__":
    unittest.main()
