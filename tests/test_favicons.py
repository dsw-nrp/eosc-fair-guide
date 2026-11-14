"""Tests for scripts/vendor_favicons.py: which host stands for a tool, which icon is tried first, which bytes count
as an image, how a refresh updates what it obtains and keeps a favicon it cannot (prune being the only deletion), and
what the check refuses."""

from __future__ import annotations

import hashlib
import shutil
import struct
import sys
import tempfile
import unittest
import urllib.error
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402
import check_content  # noqa: E402
import vendor_favicons as vf  # noqa: E402


def png(size: int = vf.SIZE) -> bytes:
    """A blank PNG of the given side, enough for the header the check reads."""
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00" * size * 4 for _ in range(size))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


class HostTests(unittest.TestCase):
    def test_favicon_policy_rejects_non_boolean_values(self):
        content = build_crate.load_content()
        for value in ("true", 1, [], {}):
            content["guide"]["resourceType"][0]["favicon"] = value
            report = check_content.Report()
            check_content.check_type_crosswalk(report, content)
            self.assertTrue(any("favicon must be a boolean" in error for error in report.errors))

    def test_a_platform_stands_only_for_its_home_page(self) -> None:
        self.assertEqual(vf.stands_for("https://www.example.org/tool"), "example.org")
        self.assertEqual(vf.stands_for("https://github.com/"), "github.com")
        self.assertIsNone(vf.stands_for("https://github.com/someone/tool"))
        self.assertIsNone(vf.stands_for("https://repo.cz/objects/20.500/example"))
        self.assertEqual(vf.stands_for("https://repo.cz/"), "repo.cz")
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
            '[guide]\n\n[[resourceType]]\nid = "tool"\nfavicon = true\nfipDashboard = ["tool"]\n', encoding="utf-8"
        )
        (content / "resources.toml").write_text(
            '[[resource]]\nid = "alpha"\ntype = "tool"\nurl = "https://a.example.org/app"\n\n'
            '[[resource]]\nid = "bravo"\ntype = "tool"\nurl = "https://b.example.org/"\n\n'
            '[[resource]]\nid = "charlie"\ntype = "standard"\nurl = "https://c.example.org/"\n\n'
            '[[resource]]\nid = "delta"\ntype = "tool"\nurl = "https://github.com/someone/d"\n',
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

    def test_a_corrected_record_address_is_asked_for_its_favicon(self) -> None:
        (self.root / "content" / "repositories.toml").write_text(
            '[[repository]]\nid = "reviewed"\nname = "Reviewed repository"\nre3data = "r3d100013576"\nurl = "https://old.example.org/"\n'
            '[[record]]\nre3data = "r3d100013576"\nurl = "https://d.example.org/"\n'
            'evidence = ["https://d.example.org/"]\n',
            encoding="utf-8",
        )
        self.assertEqual(vf.service_urls(self.root)["d.example.org"], "https://d.example.org/")
        self.assertNotIn("old.example.org", vf.service_urls(self.root))

    def test_shared_policy_includes_standard_guide_document_and_nkr_only_sites(self):
        hosts = vf.service_urls(ROOT)
        self.assertIn("coretrustseal.org", hosts)
        guide = self.root / "content/guide.toml"
        guide.write_text(
            guide.read_text(encoding="utf-8") + '\n[[resourceType]]\nid="standard"\nfavicon=true\n', encoding="utf-8"
        )
        self.assertIn("c.example.org", vf.service_urls(self.root))
        for kind in ("guide", "document"):
            guide.write_text(
                guide.read_text(encoding="utf-8") + f'\n[[resourceType]]\nid="{kind}"\nfavicon=true\n', encoding="utf-8"
            )
            path = self.root / "content/resources.toml"
            path.write_text(
                path.read_text(encoding="utf-8")
                + f'\n[[resource]]\nid="{kind}-example"\ntype="{kind}"\nurl="https://{kind}.example.org/"\n',
                encoding="utf-8",
            )
            self.assertIn(kind + ".example.org", vf.service_urls(self.root))

    def test_collection_matches_the_full_published_catalogue_sites(self):
        content = build_crate.load_content()
        crate = build_crate.build_crate(content)
        base = content["guide"]["guide"]["recordBase"]
        expected = set()
        eligible = set(build_crate.favicon_types(content["guide"]))
        for row in crate["@graph"]:
            address = row["@id"].removeprefix(base)
            if "#" in address or not address.startswith(("resources/", "repositories/")):
                continue
            kind = row.get("resourceType", row.get("guideType", {})).get("@id", "").rsplit("/", 1)[-1]
            if (address.startswith("repositories/") or kind in eligible) and (
                host := vf.stands_for(row.get("url", ""))
            ):
                expected.add(host)
        self.assertEqual(set(vf.service_urls(ROOT)), expected)

    def test_a_cited_standard_with_a_doi_uses_its_own_site(self):
        guide = self.root / "content/guide.toml"
        guide.write_text(
            guide.read_text(encoding="utf-8")
            + '\n[[resourceType]]\nid="standard"\nfavicon=true\ncitation=["standard"]\n',
            encoding="utf-8",
        )
        (self.root / "content/sources.toml").write_text(
            '[[source]]\nid="cited-standard"\ntype="standard"\ndoi="10.1234/standard"\n'
            'title="A cited standard"\nurl="https://cited.example.org/"\n',
            encoding="utf-8",
        )
        self.assertIn("cited.example.org", vf.service_urls(self.root))

    def test_nkr_site_overrides_and_empty_site_fallback_use_reconciled_things(self):
        content = self.root / "content"
        (content / "repositories.toml").write_text(
            '[[repository]]\nid="local"\nname="Local"\nurl="https://old.example.org/"\nnkr="handle/1"\n',
            encoding="utf-8",
        )
        snapshots = content / "snapshots"
        snapshots.mkdir()
        target = snapshots / "nkr.toml"
        template = (
            '[snapshot]\nsource="NKR"\nretrieved=2026-11-14\n[[record]]\nid="local"\n'
            'alternateIds=[{scheme="nkr",value="handle/1"}]\nguideRoute="repositories"\n'
            'repositoryName="Local"\nstatus="intended"\nmainUrl="{site}"\n'
        )
        target.write_text(template.replace("{site}", "https://new.example.org/"), encoding="utf-8")
        with target.open("a", encoding="utf-8") as stream:
            stream.write(
                template.split("[[record]]", 1)[1]
                .replace('id="local"', 'id="herbarium"')
                .replace('value="handle/1"', 'value="handle/2"')
                .replace("{site}", "https://herbarium.biodiversity.cz/")
                .join(["\n[[record]]", ""])
            )
        self.assertIn("new.example.org", vf.service_urls(self.root))
        self.assertIn("herbarium.biodiversity.cz", vf.service_urls(self.root))
        self.assertNotIn("old.example.org", vf.service_urls(self.root))
        target.write_text(template.replace("{site}", ""), encoding="utf-8")
        self.assertIn("old.example.org", vf.service_urls(self.root))

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
        self.assertEqual(
            config, {"hosts": ["a.example.org", "github.com"], "homeOnly": ["github.com"], "marks": {}, "types": []}
        )

    def test_infrastructure_refresh_keeps_service_dates_and_shares_own_marks(self) -> None:
        vf.vendor(
            self.root,
            self.fetch,
            "2026-10-13",
            lambda originals, output: (output / "a.example.org~1.png").write_bytes(png()) and [],
        )
        (self.root / "content" / "infrastructures.toml").write_text(
            '[[infrastructure]]\nid="one"\nwebsite="https://b.example.org/"\nlogo="https://b.example.org/own.png"\n'
            '[[infrastructure]]\nid="two"\nwebsite="https://b.example.org/"\nlogo="https://b.example.org/own.png"\n'
            '[[infrastructure]]\nid="institution"\nwebsite="https://a.example.org/"\nlogo=false\n'
            '[[infrastructure]]\nid="unavailable"\nurl="https://www.vyzkumne-infrastruktury.cz/record/"\n',
            encoding="utf-8",
        )
        self.responses["https://b.example.org/own.png"] = png()
        asked = []

        def fetch(url: str, limit: int) -> tuple[str, bytes]:
            asked.append(url)
            return self.fetch(url, limit)

        def normalise(originals: Path, output: Path) -> list[str]:
            for path in originals.iterdir():
                (output / (path.stem + ".png")).write_bytes(png())
            return []

        before_observations = vf._toml(self.root / vf.MANIFEST)["observation"]
        count, missing = vf.vendor(self.root, fetch, "2026-10-14", normalise, infrastructures_only=True)
        self.assertEqual((count, missing), (3, ["infrastructure-institution", "infrastructure-unavailable"]))
        self.assertEqual(asked, ["https://b.example.org/own.png"] * 2)
        self.assertEqual(vf.check(self.root), [])
        records = vf._toml(self.root / vf.MANIFEST)["favicon"]
        after_observations = vf._toml(self.root / vf.MANIFEST)["observation"]
        self.assertEqual(before_observations, [row for row in after_observations if not row.get("key")])
        self.assertEqual(str(records[0]["retrieved"]), "2026-10-13")
        self.assertEqual({r["file"] for r in records}, {"a.example.org.png"}, "identical marks reuse the service file")
        fixture = self.root / "fixture"
        shutil.copytree(ROOT / "tests" / "fixtures" / "minimal", fixture)
        shutil.copytree(self.root / vf.TARGET, fixture / vf.TARGET)
        config = build_crate.page_config(build_crate.load_content(fixture / "content"))["config"]["favicons"]
        self.assertEqual(config["hosts"], ["a.example.org"])
        self.assertEqual(
            config["marks"], {"infrastructure-one": "a.example.org.png", "infrastructure-two": "a.example.org.png"}
        )

    def test_infrastructure_marks_refuse_unsafe_identity_and_logo_sources(self) -> None:
        path = self.root / "content" / "infrastructures.toml"
        path.write_text('[[infrastructure]]\nid="../escape"\nwebsite="https://a.example.org/"\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "lowercase slug"):
            vf.infrastructure_marks(self.root, self.fetch)
        path.write_text(
            '[[infrastructure]]\nid="one"\nwebsite="https://a.example.org/"\nlogo="file:///private"\n', encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            vf.infrastructure_marks(self.root, self.fetch)

    def test_a_refresh_keeps_a_favicon_it_cannot_obtain_again_and_prune_drops_it(self) -> None:
        vf.vendor(
            self.root,
            self.fetch,
            "2026-10-13",
            lambda originals, output: (output / "a.example.org~1.png").write_bytes(png()) and [],
        )

        def unreachable(url: str, limit: int) -> tuple[str, bytes]:
            raise OSError(url)

        # A second run that reaches no host keeps every recorded favicon, its file and its date untouched.
        count, missing = vf.vendor(self.root, unreachable, "2026-10-14", lambda originals, output: [])
        self.assertEqual((count, missing), (1, ["b.example.org"]))
        records = vf._toml(self.root / vf.MANIFEST)["favicon"]
        self.assertEqual(str(records[0]["retrieved"]), "2026-10-13", "an unrefreshed favicon keeps its date")
        observations = vf._toml(self.root / vf.MANIFEST)["observation"]
        self.assertTrue(all(row["outcome"] == "failed" and str(row["checked"]) == "2026-10-14" for row in observations))
        self.assertEqual(vf.check(self.root), [])
        # --prune is the explicit way to drop a favicon that was not obtained again.
        count, _ = vf.vendor(self.root, unreachable, "2026-10-14", lambda originals, output: [], prune=True)
        self.assertEqual(count, 0)
        self.assertEqual(vf.check(self.root), [])

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

    def test_observations_distinguish_missing_failed_unrenderable_and_acquired(self):
        for mode, outcome, reason in (
            ("missing", "unavailable", "no-usable-image"),
            ("timeout", "failed", "timeout"),
            ("rate-limit", "failed", "rate-limited"),
            ("invalid", "unavailable", "no-usable-image"),
            ("unrenderable", "unavailable", "not-renderable"),
            ("acquired", "available", "acquired"),
        ):

            def fetch(url, limit, mode=mode):
                if mode == "timeout":
                    raise TimeoutError("timed out")
                if mode in ("missing", "rate-limit"):
                    raise urllib.error.HTTPError(url, 404 if mode == "missing" else 429, "fixture", {}, None)
                return url, b"<html>no icon</html>" if mode == "invalid" else png()

            def normalise(originals, output, mode=mode):
                if mode == "acquired":
                    for path in originals.iterdir():
                        (output / (path.stem + ".png")).write_bytes(png())
                return []

            with self.subTest(mode=mode):
                vf.vendor(self.root, fetch, "2026-11-14", normalise)
                observations = vf._toml(self.root / vf.MANIFEST).get("observation", [])
                self.assertTrue(observations, "no acquisition observations recorded")
                self.assertEqual({(row["outcome"], row["reason"]) for row in observations}, {(outcome, reason)})
                self.assertEqual(vf.check(self.root), [])

    def test_observation_validation_and_unattempted_coverage_are_offline(self):
        path = self.root / vf.MANIFEST
        path.parent.mkdir(parents=True)
        for fields in (
            'checked=2026-11-14\noutcome="invented"\nreason="acquired"',
            'checked="2026-02-30"\noutcome="failed"\nreason="timeout"',
            'checked=2026-11-14\noutcome="failed"\nreason="arbitrary text"',
            'checked=2026-11-14\noutcome="available"\nreason="acquired"',
        ):
            path.write_text('[[observation]]\nhost="a.example.org"\n' + fields + "\n", encoding="utf-8")
            self.assertTrue(vf.check(self.root), fields)
        path.write_text(
            '[[observation]]\nhost="a.example.org"\nchecked=2026-11-14\noutcome="failed"\nreason="timeout"\n' * 2,
            encoding="utf-8",
        )
        self.assertTrue(any("duplicate" in problem for problem in vf.check(self.root)))
        path.write_text("", encoding="utf-8")
        self.assertEqual(vf.coverage(self.root)["unattempted"], ["a.example.org", "b.example.org"])

    def test_pruning_an_out_of_scope_icon_does_not_leave_a_false_available_observation(self):
        vf.vendor(
            self.root,
            self.fetch,
            "2026-10-13",
            lambda originals, output: (output / "a.example.org~1.png").write_bytes(png()) and [],
        )
        (self.root / "content/resources.toml").write_text("", encoding="utf-8")
        vf.vendor(self.root, self.fetch, "2026-10-14", lambda originals, output: [], prune=True)
        self.assertEqual(vf.check(self.root), [])
        self.assertFalse(vf._toml(self.root / vf.MANIFEST).get("favicon"))


if __name__ == "__main__":
    unittest.main()
