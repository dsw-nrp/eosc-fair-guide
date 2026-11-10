"""Static HTML landing pages are complete, bilingual and projected only from the corresponding API records."""

from __future__ import annotations

import json
import os
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_api  # noqa: E402
import build_crate  # noqa: E402
import landing_pages  # noqa: E402


class Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags = []
        self.links = []
        self.languages = []
        self.ids = []
        self.fields = {}
        self.stack = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        self.tags.append(tag)
        if "lang" in attributes:
            self.languages.append(attributes["lang"])
        self.stack.append(tag)
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag in ("a", "link"):
            self.links.append(attributes)
        if "data-field" in attributes:
            self.fields[attributes["data-field"]] = [attributes["data-field"], ""]

    def handle_endtag(self, tag: str) -> None:
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        for key in self.fields:
            self.fields[key][1] += data


class LandingPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = build_crate.load_content()
        cls.api = build_api.Api(build_crate.build_crate(cls.content), cls.content)
        cls.files = cls.api.files()
        cls.paths = [path for path in cls.files if path.startswith("id/") and path.endswith(".html")]
        cls.documents = {path: json.loads(text) for path, text in cls.files.items() if path.endswith(".json")}

    def document(self, path: str) -> Document:
        document = Document()
        document.feed(self.files[path])
        return document

    def name(self, value: object, language: str) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return self.name(value.get(language, value.get("en", value.get("cs"))), language)
        return ""

    def test_a_page_per_address_and_no_javascript(self) -> None:
        expected = {
            "id/" + self.api.paths[entity_id].removeprefix("api/v1/").removesuffix(".json") + ".html"
            for _, members in self.api.records.items()
            for _, entity_id in members
        }
        self.assertEqual(set(self.paths), expected)
        self.assertEqual(self.files, build_api.Api(build_crate.build_crate(self.content), self.content).files())
        for path in self.paths:
            document = self.document(path)
            self.assertNotIn("script", document.tags, path)
            self.assertIn("cs", document.languages, path)
            self.assertIn("en", document.languages, path)
            self.assertIn("style-src 'self'", self.files[path])
            self.assertIn("script-src 'none'", self.files[path])

    def test_stations_are_bilingual_and_link_their_relations(self) -> None:
        path = "id/stations/plan.html"
        api_path = "api/v1/stations/plan.json"
        record = self.documents[api_path]
        for language in ("cs", "en"):
            input_doc = self.document(path)
            self.assertIn(f'<section class="landing-record" lang="{language}" id="{language}">', self.files[path])
            self.assertIn(self.name(record["name"], language), self.files[path])
            self.assertIn(self.name(record["headline"], language).split(" ", 1)[0], self.files[path])
            self.assertTrue(
                any(
                    link.get("rel") == "cite-as" and link.get("href") == self.api.base + "stations/plan"
                    for link in input_doc.links
                ),
                repr(input_doc.links[:5]),
            )
            self.assertTrue(
                any(
                    link.get("rel") == "describedby"
                    and link.get("href") == "../../api/v1/stations/plan.json"
                    and link.get("type") == "application/ld+json"
                    for link in input_doc.links
                )
            )
            self.assertIn(self.api.base + "stations/plan", self.files[path])
        self.assertIn("../../index.html#/id/stations/plan", self.files[path])
        self.assertTrue(
            any(
                link.get("href", "").endswith("vocabularies/lenses.html#V") and link.get("type") == "text/html"
                for link in input_doc.links
            )
        )
        self.assertTrue(
            any(
                link.get("href", "").endswith("lifecycles/rdmkit/plan.html") and link.get("type") == "text/html"
                for link in input_doc.links
            )
        )
        self.assertIn("context-V", input_doc.ids)

    def test_repository_has_external_ids_registry_parts_and_source_licences(self) -> None:
        path = "id/repositories/zenodo.html"
        content = self.files[path]
        document = self.document(path)
        self.assertIn("zenodo.org", content)
        self.assertIn("doi.org", content)
        self.assertIn("knav", document.ids)
        record = self.documents["api/v1/repositories/zenodo.json"]
        part = next(part for part in record["records"] if part["@id"].endswith("#knav"))
        for key in ("license", "citation", "isBasedOn"):
            if key in part:
                self.assertIn(str(part[key] if isinstance(part[key], str) else part[key]["@id"]), content)
        self.assertIn("operational", content)
        self.assertIn('data-field="serviceStatus"', content)
        self.assertTrue(
            any(
                link.get("rel") == "describedby"
                and link.get("href") == "../../api/v1/repositories/zenodo.json"
                and link.get("type") == "application/ld+json"
                for link in document.links
            )
        )
        self.assertIn("knav", document.ids)

    def test_status_fields_follow_shared_declarations_and_real_dates(self) -> None:
        expected = {
            prop for prop, shape in build_crate.GUIDE_TERM_SHAPES.items() if shape[0] == build_crate.ADMS + "status"
        }
        self.assertEqual(set(landing_pages.STATUS_PROPERTIES), expected)
        content = self.files["id/infrastructures/hl-lhc.html"]
        self.assertIn('<dd data-field="esfriStatus">ESFRI Landmark</dd>', content)
        self.assertNotIn('<dd data-field="esfriStatus">ESFRI Landmark (', content)
        record = self.documents["api/v1/repositories/zenodo.json"]
        dated = self.files["id/repositories/zenodo.html"]
        self.assertIn(f'<dd data-field="serviceStatus">operational (as of {record["statusAsOf"]})</dd>', dated)

    def test_a_resource_page_keeps_types_languages_parts_and_no_site_address(self) -> None:
        path = "id/resources/rdmkit.html"
        content = self.files[path]
        self.assertIn("RDMkit", content)
        self.assertIn('<section class="landing-record" lang="cs" id="cs">', content)
        self.assertIn('<section class="landing-record" lang="en" id="en">', content)
        self.assertNotIn("<script", content)
        self.assertNotIn(self.content["guide"]["guide"]["pageUrl"], content)
        self.assertIn("../../api/v1/resources/rdmkit.json", content)
        self.assertIn("../../index.html#/id/resources/rdmkit", content)
        document = self.document(path)
        self.assertGreater(len(document.ids), 2)

    def test_every_api_fragment_has_one_static_target(self) -> None:
        for path in self.paths:
            document = self.document(path)
            self.assertEqual(len(document.ids), len(set(document.ids)), f"duplicate id in {path}: {document.ids}")
            api_path = "api/v1" + path.removeprefix("id").removesuffix(".html") + ".json"
            expected = set()

            def collect(value, expected=expected):
                if isinstance(value, dict):
                    if isinstance(value.get("@id"), str) and value["@id"].startswith("#"):
                        expected.add(value["@id"][1:])
                    for child in value.values():
                        collect(child)
                elif isinstance(value, list):
                    for child in value:
                        collect(child)

            collect(self.documents[api_path])
            self.assertFalse(expected - set(document.ids), f"missing anchors in {path}: {expected - set(document.ids)}")

    def test_compact_action_types_expand_to_prov(self) -> None:
        path = next(path for path in self.paths if "/actions/" in path)
        self.assertIn("/actions/", path)
        document = self.document(path)
        types = {link.get("href") for link in document.links if link.get("rel") == "type"}
        self.assertIn("http://www.w3.org/ns/prov#Activity", types)
        self.assertFalse(any(value and value.startswith("http://schema.org/prov:") for value in types))

    def test_nginx_uses_the_bilingual_not_found_page(self) -> None:
        config = (ROOT / "docker" / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn("error_page 404 /404.html;", config)

    def test_not_found_page_is_bilingual_and_has_absolute_catalogue_search(self) -> None:
        document = self.document("404.html")
        self.assertEqual(document.languages, ["cs", "cs", "en"])
        self.assertIn("Zadaná adresa", self.files["404.html"])
        self.assertIn("does not identify an entry", self.files["404.html"])
        self.assertIn("/index.html#/cs/V/catalogue", self.files["404.html"])
        self.assertIn("Nenalezeno / Not found", self.files["404.html"])
        self.assertIn('href="/eosc-fair-guide/assets/css/tokens.css"', self.files["404.html"])
        self.assertIn('href="/eosc-fair-guide/assets/css/app.css"', self.files["404.html"])

    def test_production_sitemap_lists_every_landing_page_but_not_preview(self) -> None:
        expected = sorted(self.paths)
        with mock.patch.dict(os.environ, {build_crate.BASE_URL_ENV: "https://example.org/guide/"}):
            generated = build_crate.outputs(crate=self.api.crate)
        urls = [
            element.text
            for element in ElementTree.fromstring(generated["sitemap.xml"]).iter(
                "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
            )
        ]
        self.assertEqual(sorted(urls[2:]), ["https://example.org/guide/" + path for path in expected])
        with mock.patch.dict(os.environ, {build_crate.BASE_URL_ENV: "https://example.org/next/"}):
            preview = build_crate.outputs(crate=self.api.crate)
        preview_urls = [
            element.text
            for element in ElementTree.fromstring(preview["sitemap.xml"]).iter(
                "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
            )
        ]
        self.assertFalse(any("/id/" in url for url in preview_urls), "preview sitemap names record landing pages")


if __name__ == "__main__":
    unittest.main()
