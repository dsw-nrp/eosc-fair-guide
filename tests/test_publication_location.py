"""Semantic identities, actual-location portability and offline RDF/SHACL consumers."""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pyshacl import validate
from rdflib import Graph, URIRef

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_crate  # noqa: E402
import build_site  # noqa: E402
import check_ci  # noqa: E402
from publication_fixture import publication_files  # noqa: E402
from publication_location import base_url, preview_blocked, semantic_identity, site_identity, verify_declaration  # noqa: E402


class PublicationLocationTests(unittest.TestCase):
    def test_location_normalization_and_refusal(self):
        self.assertEqual(base_url(" https://actual.example/a/index.html?q=x#/view "), "https://actual.example/a/")
        for value in (
            "http://example.org/",
            "file:///private/x",
            "https://u:p@example.org/",
            "https://example.org:99999/",
            "https://example.org/with space/",
            "https://example.org/\\x",
            "",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                base_url(value)

    def test_legacy_identity_comes_from_the_actual_crate_not_current_configuration(self):
        files = publication_files("https://legacy.example/", semantic="https://legacy.example/")
        actual = verify_declaration(files, {})
        self.assertEqual(actual["vocabulary_base"], "https://legacy.example/terms#")
        self.assertEqual(actual["profile"], "https://legacy.example/profile/0.1")
        for key in ("scope",):
            crate = json.loads(files["ro-crate-metadata.json"])
            crate["@context"][1][key] = "https://other.example/terms#scope"
            with self.assertRaises(ValueError):
                semantic_identity(crate)
        missing = dict(files)
        missing.pop("ro-crate-metadata.json")
        with self.assertRaises(ValueError):
            site_identity(missing)

    def test_manifest_cannot_forge_or_normalize_the_namespace(self):
        files = publication_files()
        actual = site_identity(files)
        manifest = {
            "publication_url": actual["publication_url"],
            "semantic": {key: actual[key] for key in ("vocabulary_base", "profile")},
        }
        self.assertEqual(verify_declaration(files, manifest), actual)
        for key in ("vocabulary_base", "profile"):
            changed = copy.deepcopy(manifest)
            changed["semantic"][key] = changed["semantic"][key].replace("example.org", "other.org")
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_declaration(files, changed)
        changed = copy.deepcopy(manifest)
        changed["publication_url"] = "https://other.org/"
        with self.assertRaises(ValueError):
            verify_declaration(files, changed)

    def test_noindex_crawl_conflicts_and_valid_rules(self):
        for policy in (
            "User-agent: *\nDisallow: /next/",
            "User-agent: *\nDisallow: /",
            "User-agent: Googlebot\nDisallow: /*next/*",
        ):
            self.assertTrue(preview_blocked(policy, ["/next/", "/next/index.html"]))
        for policy in (
            "User-agent: *\nAllow: /",
            "User-agent: *\nDisallow: /private/",
            "User-agent: *\nDisallow: /\nAllow: /next/",
            "User-agent: *\nDisallow: /next/\nAllow: /next/",
        ):
            self.assertFalse(preview_blocked(policy, ["/next/", "/next/index.html"]))

    def test_two_origins_two_prefixes_with_real_expanded_graphs_and_profile_validation(self):
        """The location moves navigation only; the reviewed namespace alone moves the Guide's terms and profile."""
        original = build_crate.load_content()
        primary = json.loads((ROOT / "tests/fixtures/ro-crate-1.2-context.json").read_text())["@context"]
        external = None
        for origin in ("https://one.example", "https://two.example"):
            for prefix in ("/", "/a/guide/"):
                location = origin + prefix
                for semantic in ("https://namespace.example/", location):
                    with self.subTest(location=location, semantic=semantic):
                        content = copy.deepcopy(original)
                        content["guide"]["guide"]["namespace"] = semantic
                        with patch.dict(os.environ, {"FAIR_GUIDE_BASE_URL": location}):
                            build_crate.apply_base_url(content["guide"]["guide"])
                            crate = build_crate.build_crate(content)
                        identity = semantic_identity(crate)
                        self.assertEqual(identity["vocabulary_base"], semantic + "terms#")
                        self.assertEqual(content["guide"]["guide"]["pageUrl"], location)
                        iris = {item["@id"] for item in crate["@graph"]}
                        owned = {iri for iri in iris if iri.startswith(semantic)}
                        # Every Guide term plus the profile: the probe exercises the actual semantic IRIs, whatever
                        # their number in this content tree.
                        expected = {semantic + "terms#" + term for term in build_crate.GUIDE_TERMS}
                        self.assertEqual(owned, expected | {semantic + "profile/0.1"})
                        other = {iri for iri in iris if not iri.startswith(semantic)}
                        if external is None:
                            external = other
                        self.assertEqual(other, external, "logical and external identities stay unchanged")
                        crate["@context"][0] = primary
                        graph = Graph().parse(data=json.dumps(crate), format="json-ld", publicID=location)
                        shapes = Graph()
                        for text in build_crate.profile_shapes(ROOT, semantic).values():
                            shapes.parse(data=text, format="turtle")
                        conforms, _, report = validate(graph, shacl_graph=shapes, advanced=True)
                        self.assertTrue(conforms, str(report)[:1000])
                        broken = Graph()
                        for triple in graph:
                            broken.add(triple)
                        predicate = URIRef(semantic + "terms#modelKind")
                        target = next(broken.subjects(predicate=predicate))
                        # Removing required source evidence is caught at the selected namespace too.
                        broken.remove((target, URIRef("http://schema.org/citation"), None))
                        self.assertFalse(validate(broken, shacl_graph=shapes, advanced=True)[0])

    def test_the_namespace_comes_from_content_never_from_the_environment(self):
        content = build_crate.load_content()
        guide = content["guide"]["guide"]
        with patch.dict(os.environ, {"FAIR_GUIDE_BASE_URL": "https://moved.example/guide/"}):
            build_crate.apply_base_url(guide)
        self.assertEqual(guide["pageUrl"], "https://moved.example/guide/")
        self.assertEqual(guide["vocabularyBase"], base_url(guide["namespace"]) + "terms#", "a move renames no term")
        self.assertEqual(guide["profile"], f"{base_url(guide['namespace'])}profile/{guide['profileVersion']}")
        guide = {**content["guide"]["guide"], "namespace": "http://insecure.example/"}
        with self.assertRaisesRegex(build_crate.ContentError, "guide.namespace"):
            build_crate.apply_base_url(guide)
        # Content from before the setting named its terms under its own baseUrl, whatever the deployment location.
        older = {key: value for key, value in content["guide"]["guide"].items() if key != "namespace"}
        older["baseUrl"] = "https://fair.eosc.cz/"
        with patch.dict(os.environ, {"FAIR_GUIDE_BASE_URL": "https://moved.example/guide/"}):
            build_crate.apply_base_url(older)
        self.assertEqual(
            (older["pageUrl"], older["vocabularyBase"]), ("https://moved.example/guide/", "https://fair.eosc.cz/terms#")
        )

    def test_a_result_checked_for_another_namespace_is_never_reused(self):
        """Real builds of one commit at one location: only the reviewed namespace differs, and adoption refuses."""
        (ROOT / ".cache").mkdir(exist_ok=True)
        location = "https://actual.example/guide/"
        load = build_crate.load_content
        builds = []

        def with_namespace(namespace):
            def loaded(content_dir=build_crate.CONTENT):
                content = load(content_dir)
                content["guide"]["guide"]["namespace"] = namespace
                build_crate.apply_base_url(content["guide"]["guide"])
                return content

            return loaded

        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as temporary:
            for name, semantic in (("legacy", "https://legacy.example/"), ("current", location)):
                site = Path(temporary) / name
                with (
                    patch.dict(os.environ, {"FAIR_GUIDE_BASE_URL": location}),
                    patch.object(build_crate, "load_content", with_namespace(semantic)),
                ):
                    build_site.build(site)
                files = [path.relative_to(site).as_posix() for path in site.rglob("*") if path.is_file()]
                builds.append(check_ci.digest_files(site, files))
        legacy, current = builds
        changed = {path for path in legacy.keys() | current.keys() if legacy.get(path) != current.get(path)}
        self.assertLessEqual({"ro-crate-metadata.json", "assets/data/ui.js", "terms/fair-guide.ttl"}, changed)
        source = {"revision": "a" * 40, "files": {}}
        problems = check_ci.adoption_problems(
            {"source": source, "build": current},
            {"profile": "ci-partitioned", "source": source, "build_inputs": legacy},
            {},
        )
        self.assertIn("build inputs differ", " ".join(problems))
