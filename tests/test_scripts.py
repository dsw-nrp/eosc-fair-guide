"""Tests for the crate generator, the content checks and the API build.

Run with ``python -m unittest discover -s tests``. Each test copies the minimal fixture into a temporary
directory, changes it, and asserts that the scripts accept or reject it.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_api  # noqa: E402
import build_crate  # noqa: E402
import check_content  # noqa: E402
import refresh_snapshots  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "minimal"
TODAY = date(2026, 3, 1)


class FixtureCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "guide"
        shutil.copytree(FIXTURE, self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def edit(self, relative: str, old: str, new: str) -> None:
        path = self.root / "content" / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"fixture text not found in {relative}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def append(self, relative: str, text: str) -> None:
        path = self.root / "content" / relative
        path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")

    def errors(self) -> list[str]:
        content = build_crate.load_content(self.root / "content")
        return check_content.check(content, self.root, today=TODAY).errors

    def assertError(self, fragment: str) -> None:  # noqa: N802 - unittest naming
        errors = self.errors()
        self.assertTrue(any(fragment in error for error in errors), f"no error containing {fragment!r}: {errors}")


class GeneratorTests(FixtureCase):
    def test_output_is_deterministic(self) -> None:
        first = build_crate.outputs(self.root)
        second = build_crate.outputs(self.root)
        self.assertEqual(first, second)

    def test_a_clause_can_be_superseded_by_a_later_one(self) -> None:
        self.edit(
            "ledger.toml",
            'actor = "repository"\n',
            'actor = "repository"\nstatus = "superseded"\nsupersededBy = "A.F1.X1"\n',
        )
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        graph = {entity["@id"]: entity for entity in crate["@graph"]}
        self.assertEqual(graph["#clause-A.F1.R1"]["supersededBy"], {"@id": "#clause-A.F1.X1"})

    def test_the_guide_signposts_itself(self) -> None:
        self.edit("guide.toml", 'profileVersion = "0.1"\n', 'profileVersion = "0.1"\ndoi = "10.1234/guide"\n')
        outputs = build_crate.outputs(self.root)
        links = json.loads(outputs[build_crate.LINKSET_FILE])["linkset"][0]
        self.assertEqual(links["anchor"], "./")
        self.assertEqual(links["describedby"][0]["href"], build_crate.CRATE_FILE)
        self.assertEqual(links["cite-as"], [{"href": "https://doi.org/10.1234/guide"}])
        self.assertNotIn("linkset", links, "the linkset does not list itself")
        head = outputs[build_crate.PAGE_FILE]
        for rel, targets in links.items():
            for target in targets if rel != "anchor" else []:
                self.assertRegex(head, f'<link rel="{rel}"[^>]* href="{re.escape(target["href"])}">')
        self.assertIn('<link rel="linkset" type="application/linkset+json" href="linkset.json">', head)

    def test_crate_structure(self) -> None:
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        graph = {entity["@id"]: entity for entity in crate["@graph"]}
        self.assertEqual(graph["ro-crate-metadata.json"]["conformsTo"], {"@id": build_crate.RO_CRATE})
        root = graph["./"]
        self.assertEqual(root["mainEntity"], {"@id": "#path"})
        self.assertIn({"@id": build_crate.PROCESS_RUN_CRATE}, root["conformsTo"])
        advice = graph["#advice-one.all.L0"]
        self.assertEqual(advice["citation"], {"@id": "#clause-A.F1.R1"})
        self.assertEqual(len(advice["audience"]), 2)
        action = graph["#action-create"]
        self.assertEqual(action["@type"], "CreateAction")
        self.assertIn({"@id": "#advice-one.V.L1.1"}, action["result"])
        resource = graph["#resource-service"]
        self.assertEqual(resource["additionalType"], "https://w3id.org/fair/fip/terms/Registry")

    def test_cited_datasets_and_software_stay_contextual(self) -> None:
        self.append(
            "sources.toml",
            '\n[[source]]\nid = "data"\ntype = "dataset"\ntitle = "Data"\ndoi = "10.1234/x"\n'
            "datePublished = 2026-01-01\n"
            '\n[[source]]\nid = "code"\ntype = "software"\ntitle = "Code"\nurl = "https://example.org/code"\n'
            "dateAccessed = 2026-01-01\n",
        )
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        graph = {entity["@id"]: entity for entity in crate["@graph"]}
        dataset = graph["https://doi.org/10.1234/x"]
        self.assertEqual(dataset["@type"], "CreativeWork")
        self.assertEqual(dataset["additionalType"], "http://schema.org/Dataset")
        self.assertEqual(graph["#source-code"]["@type"], "CreativeWork")
        self.assertEqual(graph["#source-code"]["additionalType"], "http://schema.org/SoftwareSourceCode")

    def test_station_links_accumulate(self) -> None:
        (self.root / "content" / "glossary.toml").write_text(
            '[glossary]\nsource = "Test glossary"\nretrieved = 2026-01-01\n\n'
            '[[term]]\nid = "pid"\nlabel = { cs = "PID", en = "PID" }\n',
            encoding="utf-8",
        )
        self.edit("stations/01-one.toml", "minutes = 5", 'minutes = 5\nglossary = ["pid"]')
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        station = next(entity for entity in crate["@graph"] if entity["@id"] == "#station-one")
        self.assertEqual(station["mentions"], [{"@id": "#term-pid"}, {"@id": "#resource-service"}])
        self.assertEqual(station["hasPart"], {"@id": "#callout-note"})
        self.assertEqual(self.errors(), [])

    def test_page_blocks_are_safe_and_preview_matches(self) -> None:
        self.edit("stations/01-one.toml", "Take the first step.", "Take the </script> step.")
        generated = build_crate.outputs(self.root)
        page = generated[build_crate.PAGE_FILE]
        self.assertEqual(page, generated[build_crate.PREVIEW_FILE])
        self.assertIn("connect-src https://api.example.org", page)
        kb = generated[build_crate.KB_SCRIPT]
        self.assertNotIn("</script>", kb)
        self.assertIn("Take the \\u003c/script\\u003e step.", kb)

    def test_data_leaves_the_page_for_scripts(self) -> None:
        generated = build_crate.outputs(self.root)
        page = generated[build_crate.PAGE_FILE]
        self.assertNotIn('"@graph"', page)
        self.assertIn(f'<script src="{build_crate.KB_SCRIPT}" defer></script>', page)
        self.assertIn(f'<script src="{build_crate.UI_SCRIPT}" defer></script>', page)
        summary = json.loads(page.split('<script type="application/ld+json">')[1].split("</script>")[0])
        self.assertEqual(summary["@type"], "Dataset")
        self.assertTrue(summary["distribution"]["contentUrl"].endswith(build_crate.CRATE_FILE))
        prefix = "window.FairGuideData.kb = "
        line = next(row for row in generated[build_crate.KB_SCRIPT].splitlines() if row.startswith(prefix))
        self.assertEqual(json.loads(line[len(prefix) : -1]), json.loads(generated[build_crate.CRATE_FILE]))

    def test_page_payload_follows_the_page_and_warns_over_budget(self) -> None:
        generated = build_crate.outputs(self.root)
        sizes = build_crate.page_payload(generated, self.root)
        self.assertIn(build_crate.KB_SCRIPT, sizes)
        self.assertIn(build_crate.UI_SCRIPT, sizes)
        self.assertIsNone(build_crate.payload_warning(sizes, budget_kb=10_000))
        warning = build_crate.payload_warning(sizes, budget_kb=0)
        self.assertIsNotNone(warning)
        self.assertIn("over its budget of 0 KB; largest: ", warning or "")

    def test_reference_in_text_becomes_a_mention(self) -> None:
        self.edit(
            "stations/01-one.toml",
            'text = { cs = "Udělejte první krok.", en = "Take the first step." }',
            'text = { cs = "Udělejte první krok v [[service|testovací službě]].", '
            'en = "Take the first step in the [[service|Test service]]." }',
        )
        graph = build_crate.Graph()
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"), graph)
        advice = next(entity for entity in crate["@graph"] if "Take the first step" in json.dumps(entity))
        self.assertNotIn("[[", json.dumps(advice, ensure_ascii=False))
        self.assertIn({"@value": "Take the first step in the Test service.", "@language": "en"}, advice["text"])
        self.assertIn({"@id": "#resource-service"}, build_crate.as_list(advice["mentions"]))
        self.assertEqual(
            graph.text_links[advice["@id"]],
            [{"ref": "#resource-service", "cs": "testovací službě", "en": "Test service"}],
        )
        self.assertEqual(self.errors(), [])

    def test_references_are_checked(self) -> None:
        old = 'text = { cs = "Udělejte první krok.", en = "Take the first step." }'
        self.edit(
            "stations/01-one.toml",
            old,
            'text = { cs = "Krok v [[nowhere|ničem]].", en = "A step in [[nowhere|nothing]]." }',
        )
        self.assertError("refers to an unknown entry 'nowhere'")
        self.edit(
            "stations/01-one.toml",
            'text = { cs = "Krok v [[nowhere|ničem]].", en = "A step in [[nowhere|nothing]]." }',
            'text = { cs = "Krok v [[service|službě]].", en = "A step in the service." }',
        )
        self.assertError("the Czech and English texts refer to different entries: service")
        self.edit(
            "stations/01-one.toml",
            'en = "A step in the service." }',
            'en = "A step in the [[service Test service]]." }',
        )
        self.assertError("a reference is not well formed; write [[id|phrase]]")

    def test_missing_marker_is_reported(self) -> None:
        page = self.root / "index.html"
        page.write_text(page.read_text(encoding="utf-8").replace("<!-- generated:ui --><!-- /generated:ui -->", ""))
        with self.assertRaises(build_crate.ContentError):
            build_crate.outputs(self.root)


class ContentCheckTests(FixtureCase):
    def test_fixture_passes(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_missing_translation(self) -> None:
        self.edit("stations/01-one.toml", ', en = "Steps."', "")
        self.assertError("one.V.L1.1")
        self.assertError("missing English text")

    def test_advice_without_source(self) -> None:
        self.edit("stations/01-one.toml", 'sources = ["A.F1.X1"]', "sources = []")
        self.assertError("cites no ledger clause")

    def test_unknown_clause(self) -> None:
        self.edit("stations/01-one.toml", 'sources = ["A.F1.X1"]', 'sources = ["A.F9.R9"]')
        self.assertError("cites unknown clause 'A.F9.R9'")

    def test_javascript_link(self) -> None:
        self.edit("resources.toml", 'url = "https://example.org/service"', 'url = "javascript:alert(1)"')
        self.assertError("javascript: URL")
        self.assertError("link must use HTTPS")

    def test_raw_html(self) -> None:
        self.edit("ledger.toml", "NRP zajišťuje DOI.", "NRP zajišťuje <b>DOI</b>.")
        self.assertError("raw HTML")

    def test_clause_missing_from_its_principle(self) -> None:
        self.edit(
            "ledger.toml",
            'id = "A.F1.R1"\nsource = "report"\nprinciples = ["F1"]',
            'id = "A.F1.R1"\nsource = "report"\nprinciples = []',
        )
        self.assertError("explorer would miss it")

    def test_station_without_next_action(self) -> None:
        self.edit(
            "stations/01-one.toml", 'action = { label = { cs = "Začít", en = "Start" }, href = "#check-gate" }\n', ""
        )
        self.assertError("needs one concrete action")

    def test_in_page_target_must_exist(self) -> None:
        self.edit("stations/01-one.toml", 'href = "#check-gate"', 'href = "#nowhere"')
        self.assertError("in-page target '#nowhere' does not exist")

    def test_item_without_provenance(self) -> None:
        self.edit("provenance.toml", '"G01", ', "")
        self.assertError("item:G01: no provenance action covers this item")

    def test_scores_are_forbidden(self) -> None:
        self.append("checks/gate.toml", "\n[check.score]\nmax = 10\n")
        self.assertError("no scores")

    def test_callout_order_lists_every_item(self) -> None:
        self.edit("callouts.toml", 'SR = ["b", "a"]', 'SR = ["b"]')
        self.assertError("must list every item exactly once")

    def test_champion_prefill_outside_curated_set(self) -> None:
        self.edit("checks/gate.toml", 'champion = ["test_one"]', 'champion = ["test_two"]')
        self.assertError("outside the curated set")

    def test_lookup_must_name_a_link(self) -> None:
        self.edit("checks/gate.toml", 'champion = ["test_one"] }', 'champion = ["test_one"] }\nlookup = "nowhere"')
        self.assertError("lookup names unknown link 'nowhere'")

    def test_lookup_enters_the_crate(self) -> None:
        self.edit("checks/gate.toml", 'champion = ["test_one"] }', 'champion = ["test_one"] }\nlookup = "search"')
        self.assertEqual(self.errors(), [])
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"))
        item = next(entity for entity in crate["@graph"] if entity["@id"] == "#item-G01")
        self.assertEqual(item["lookup"], {"@id": "https://example.org/search"})

    def test_nanopub_query_needs_the_fip_placeholder(self) -> None:
        nanopub = '\n[nanopub]\npath = "sparql"\nfipIri = ["https://example.org/np/{code}"]\n'
        nanopub += 'query = "SELECT * WHERE { ?s ?p ?o }"\n'
        self.append("live.toml", nanopub)
        self.assertError("the query must contain {fips}")

    def test_sparql_iris_are_not_raw_html(self) -> None:
        query = "PREFIX ex: <https://example.org/> SELECT * WHERE { VALUES ?fip { {fips} } ?fip ex:p ?o }"
        nanopub = f'\n[nanopub]\npath = "sparql"\nfipIri = ["https://example.org/np/{{code}}"]\nquery = "{query}"\n'
        self.append("live.toml", nanopub)
        self.assertEqual(self.errors(), [])

    def test_named_icon_must_be_vendored(self) -> None:
        self.append(
            "guide.toml",
            '\n[[task]]\nlens = "V"\nlabel = { cs = "Úkol", en = "Task" }\nhref = "#station-one"\nicon = "star"\n',
        )
        self.assertError("icon 'star' is not vendored")
        (self.root / "assets" / "icons").mkdir(parents=True)
        (self.root / "assets" / "icons" / "star.svg").write_text("<svg/>", encoding="utf-8")
        self.assertEqual(self.errors(), [])

    def test_task_needs_a_known_lens(self) -> None:
        self.append(
            "guide.toml", '\n[[task]]\nlens = "X"\nlabel = { cs = "Úkol", en = "Task" }\nhref = "#station-one"\n'
        )
        self.assertError("unknown lens 'X'")

    def test_guide_needs_an_editor(self) -> None:
        self.edit("guide.toml", 'editors = ["tester"]', "editors = []")
        self.assertError("the guide needs at least one editor")

    def test_source_author_id_must_be_a_person(self) -> None:
        self.edit("sources.toml", 'title = "Test report"', 'title = "Test report"\nauthors = ["nobody-known"]')
        self.assertError("unknown person 'nobody-known'")

    def test_credit_separates_basis_from_compilation(self) -> None:
        self.edit(
            "sources.toml", 'title = "Test report"', 'title = "Test report"\nauthors = ["tester", "Other Author"]'
        )
        self.edit("guide.toml", 'editors = ["tester"]', 'editors = ["tester"]\nisBasedOn = ["report"]')
        self.assertEqual(self.errors(), [])
        content = build_crate.load_content(self.root / "content")
        graph = {entity["@id"]: entity for entity in build_crate.build_crate(content)["@graph"]}
        root = graph["./"]
        self.assertNotIn("author", root)
        self.assertEqual(root["editor"], {"@id": "#person-tester"})
        report = next(entity for entity in graph.values() if entity.get("identifier") == "report")
        self.assertEqual(report["author"], {"@id": "#person-tester"})
        self.assertEqual(report["creditText"], "Test Person; Other Author")
        credits = build_crate.page_config(content)["config"]["credits"]
        self.assertEqual([credit["role"] for credit in credits], ["analysis", "editor", "tools"])
        self.edit("guide.toml", 'publisher = "org"', 'publisher = "org"\nfunder = "org"')
        funding = build_crate.page_config(build_crate.load_content(self.root / "content"))["config"]["credits"][-1]
        self.assertEqual(funding["role"], "funding")
        self.assertEqual(
            funding["people"][0]["name"],
            [{"@value": "Test Organisation", "@language": lang} for lang in build_crate.LANGS],
        )
        self.assertEqual(credits[0]["people"], [{"name": "Test Person", "url": None}, {"name": "Other Author"}])

    CITATION = '\n[resource.citation]\ntype = "webpage"\ntitle = "Test service page"\ndateAccessed = 2026-01-01\n'

    def test_cited_resource_is_one_entity(self) -> None:
        self.append("resources.toml", self.CITATION)
        self.edit("ledger.toml", 'source = "report"', 'source = "service"')
        self.assertEqual(self.errors(), [])
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        graph = {entity["@id"]: entity for entity in crate["@graph"]}
        self.assertIn({"@id": "#resource-service"}, build_crate.as_list(graph["#sources"]["hasPart"]))
        self.assertEqual(graph["#clause-A.F1.R1"]["isPartOf"], {"@id": "#resource-service"})
        self.assertEqual(graph["#resource-service"]["alternateName"], "Test service page")
        self.assertNotIn("#source-service", graph)

    def test_resource_cited_without_its_citation(self) -> None:
        self.edit("ledger.toml", 'source = "report"', 'source = "service"')
        self.assertError("unknown source 'service'")

    def test_same_address_in_two_entries(self) -> None:
        self.append(
            "sources.toml",
            '\n[[source]]\nid = "copy"\ntype = "webpage"\ntitle = "Copy"\n'
            'url = "http://www.example.org/service/"\ndateAccessed = 2026-01-01\n',
        )
        self.assertError("describes the same thing as resource:service (same address)")

    def test_one_identifier_names_one_entity(self) -> None:
        self.append(
            "sources.toml",
            '\n[[source]]\nid = "service"\ntype = "webpage"\ntitle = "Other"\n'
            'url = "https://example.org/other"\ndateAccessed = 2026-01-01\n',
        )
        self.assertError("id:service: names several entities")

    def test_snapshot_match_needs_a_link(self) -> None:
        snapshots = self.root / "content" / "snapshots"
        snapshots.mkdir(exist_ok=True)
        dashboard = DASHBOARD_SNAPSHOT.replace(
            'name = "Resource one"', 'name = "Resource one"\nurl = "https://example.org/service"'
        )
        (snapshots / "fip-dashboard.toml").write_text(dashboard, encoding="utf-8")
        self.assertError("matches FIP Dashboard resource 'r1'; link it with fipDashboard")
        self.edit("resources.toml", 'fipClass = ["Registry"]', 'fipClass = ["Registry"]\nfipDashboard = "r1"')
        self.assertFalse(any("matches FIP Dashboard" in error for error in self.errors()))

    def test_czech_name_needs_an_english_form(self) -> None:
        self.edit("guide.toml", 'name = "Test Organisation"', 'name = "Testovací organizace"')
        self.assertError("organization:org: 'Testovací organizace' is a Czech name with no English form")
        self.edit(
            "guide.toml", 'name = "Testovací organizace"', 'name = { cs = "Testovací organizace", en = "Test Org" }'
        )
        self.assertFalse(any("Czech name" in error for error in self.errors()))

    def test_publisher_that_is_an_organisation_is_cited_by_id(self) -> None:
        self.edit("sources.toml", 'title = "Test report"', 'title = "Test report"\npublisher = "Test Organisation"')
        self.assertError("sources:report: publisher 'Test Organisation' is the organisation 'org'; cite it by that ID")
        self.edit("sources.toml", 'publisher = "Test Organisation"', 'publisher = "org"')
        self.assertFalse(any("cite it by that ID" in error for error in self.errors()))
        self.edit("sources.toml", 'publisher = "org"', 'publisher = "Testovací vydavatel"')
        self.assertError("sources:report: publisher 'Testovací vydavatel' is a Czech name with no English form")

    def test_check_blocks_group_every_item(self) -> None:
        self.edit("checks/gate.toml", 'tier = "required"', 'block = "basics"\ntier = "required"')
        self.assertError("item:G01: the check declares no blocks")
        self.edit(
            "checks/gate.toml",
            "[[item]]",
            '[[block]]\nid = "other"\nname = { cs = "Ostatní", en = "Other" }\n\n[[item]]',
        )
        self.assertError("item:G01: block must be one of other")
        self.edit("checks/gate.toml", 'block = "basics"', 'block = "other"')
        self.assertFalse(any("block" in error for error in self.errors()))
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        item = next(entity for entity in crate["@graph"] if entity["@id"] == "#item-G01")
        self.assertEqual(item["block"], {"@id": "#block-gate-other"})

    def test_unused_resource_is_reported(self) -> None:
        self.edit("resources.toml", 'stations = ["one"]', "")
        content = build_crate.load_content(self.root / "content")
        warnings = check_content.check(content, self.root, today=TODAY).warnings
        self.assertIn(
            "resource:service: nothing uses this resource: no station recommends it and nothing cites it", warnings
        )

    def test_repository_resource_is_one_entity(self) -> None:
        self.append(
            "guide.toml",
            '\n[[repositoryKind]]\nid = "general"\nname = { cs = "obecný", en = "general" }\n'
            '\n[[resourceType]]\nid = "repository"\nname = { cs = "repozitář", en = "repository" }\n',
        )
        self.append(
            "resources.toml",
            '\n[[resource]]\nid = "repo"\nname = "Test repository"\nurl = "https://example.org/repo"\n'
            'type = "repository"\nstatus = "pilot"\nasOf = 2026-01-01\nstations = ["one"]\n'
            '\n[resource.repository]\nkind = "general"\n',
        )
        self.edit("provenance.toml", '"service", "A.*"', '"service", "repo", "A.*"')
        self.assertEqual(self.errors(), [])
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        graph = {entity["@id"]: entity for entity in crate["@graph"]}
        self.assertIn({"@id": "#resource-repo"}, build_crate.as_list(graph["#repositories"]["hasPart"]))
        self.assertEqual(graph["#resource-repo"]["repositoryKind"], {"@id": "#rkind-general"})
        self.assertNotIn("#repository-repo", graph)

    def test_every_page_sits_under_a_menu_item(self) -> None:
        pages = self.root / "content" / "pages.toml"
        title = 'title = { cs = "Stránka", en = "Page" }\n'
        pages.write_text('[[page]]\nid = "lost"\n' + title, encoding="utf-8")
        self.assertError("menu must be one of catalogue, tools, about")
        pages.write_text('[[page]]\nid = "tool"\nmenu = "tools"\n' + title, encoding="utf-8")
        self.assertError("missing description")
        described = 'description = { cs = "Co dělá.", en = "What it does." }\n'
        pages.write_text('[[page]]\nid = "tool"\nmenu = "tools"\n' + described + title, encoding="utf-8")
        self.assertFalse(any(error.startswith("page:") for error in self.errors()), self.errors())

    def test_base_url_must_use_https(self) -> None:
        self.edit("guide.toml", 'baseUrl = "https://example.org/guide/"', 'baseUrl = "http://example.org/guide/"')
        self.assertError("the guide's address must use HTTPS")

    def test_stale_status_is_a_warning(self) -> None:
        content = build_crate.load_content(self.root / "content")
        report = check_content.check(content, self.root, today=date(2027, 1, 1))
        self.assertEqual(report.errors, [])
        self.assertTrue(any("older than 180 days" in warning for warning in report.warnings))

    def test_script_urls_must_be_connectors(self) -> None:
        scripts = self.root / "assets" / "js"
        scripts.mkdir(parents=True)
        (scripts / "app.js").write_text('fetch("https://api.example.org/x");\nfetch("https://elsewhere.example/y");\n')
        self.assertError("URL outside the connector allowlist: https://elsewhere.example/y")
        self.assertFalse(any("api.example.org/x" in error for error in self.errors()))


DASHBOARD_SNAPSHOT = """[snapshot]
source = "FIP Dashboard"
url = "https://dashboard.example.org/"
retrieved = 2026-01-01
disclaimer = { cs = "Ukázková data.", en = "Sample data." }

[[resourceType]]
id = "identifier-service"
label = { cs = "Služba identifikátorů", en = "Identifier service" }

[[organization]]
id = "org1"
name = { cs = "Organizace", en = "Organisation" }

[[resource]]
id = "r1"
name = "Resource one"
type = "identifier-service"
description = { cs = "Zdroj.", en = "Resource." }
principles = ["F1"]
verification = [{ verifier = "org1", level = "verified", date = "2026-01-01" }]

[[fip]]
id = "fip1"
title = { cs = "Profil", en = "Profile" }
community = "org1"
status = "published"
domain = { cs = "Obor", en = "Domain" }
summary = { cs = "Shrnutí.", en = "Summary." }
verification = []
declarations = [
  { principle = "F1", resource = "r1", status = "in-use" },
]
"""


class SnapshotTests(FixtureCase):
    def write_dashboard(self, text: str = DASHBOARD_SNAPSHOT) -> None:
        snapshots = self.root / "content" / "snapshots"
        snapshots.mkdir(exist_ok=True)
        (snapshots / "fip-dashboard.toml").write_text(text, encoding="utf-8")

    def test_dashboard_snapshot_passes_and_enters_the_crate(self) -> None:
        self.write_dashboard()
        self.edit("resources.toml", 'fipClass = ["Registry"]', 'fipClass = ["Registry"]\nfipDashboard = "r1"')
        self.assertEqual(self.errors(), [])
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        graph = {entity["@id"]: entity for entity in crate["@graph"]}
        self.assertEqual(graph["#fer-r1"]["review"], {"@id": "#fer-r1-verification-1"})
        self.assertEqual(graph["#fer-r1-verification-1"]["reviewAspect"], "verified")
        self.assertEqual(graph["#fip-fip1-F1-r1"]["creativeWorkStatus"], "in-use")
        self.assertIn({"@value": "Sample data.", "@language": "en"}, graph["#snapshot-fip-dashboard"]["disclaimer"])

    def test_a_reference_to_an_entity_the_crate_lacks_is_an_error(self) -> None:
        self.write_dashboard(
            DASHBOARD_SNAPSHOT.split("[[organization]]", 1)[0].split("[[resourceType]]", 1)[0]
            + "[[organization]]"
            + DASHBOARD_SNAPSHOT.split("[[organization]]", 1)[1]
        )
        self.edit("resources.toml", 'fipClass = ["Registry"]', 'fipClass = ["Registry"]\nfipDashboard = "r1"')
        self.assertError("catalogueType names #fd-type-identifier-service, which the crate does not have")

    def test_declaration_of_unknown_resource(self) -> None:
        self.write_dashboard(DASHBOARD_SNAPSHOT.replace('resource = "r1", status', 'resource = "r9", status'))
        self.assertError("declares unknown resource 'r9'")

    def test_resource_names_missing_dashboard_record(self) -> None:
        self.write_dashboard()
        self.edit("resources.toml", 'fipClass = ["Registry"]', 'fipClass = ["Registry"]\nfipDashboard = "nowhere"')
        self.assertError("FIP Dashboard has no resource 'nowhere'")

    def test_testing_notice_is_required(self) -> None:
        self.edit("guide.toml", 'testingNotice = { cs = "Testování.", en = "Testing." }\n', "")
        self.assertError("missing testingNotice")

    def test_unknown_affiliation(self) -> None:
        self.edit("guide.toml", 'name = "Test Person"', 'name = "Test Person"\naffiliation = ["nowhere"]')
        self.assertError("unknown affiliation 'nowhere'")

    def test_xml_with_a_dtd_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            refresh_snapshots.parse_xml(b'<!DOCTYPE x [<!ENTITY a "b">]><x>&a;</x>')

    def test_re3data_plain_http_home_page_links_to_the_record(self) -> None:
        inputs = Path(self.temp.name) / "inputs"
        inputs.mkdir()
        (inputs / "re3data-list.xml").write_text("<list><repository><id>r3d1</id></repository></list>")
        (inputs / "re3data-r3d1.xml").write_text(
            '<r3d:re3data xmlns:r3d="http://www.re3data.org/schema/2-2"><r3d:repository>'
            "<r3d:repositoryName>Old</r3d:repositoryName><r3d:repositoryURL>http://old.example.org/</r3d:repositoryURL>"
            "<r3d:type>disciplinary</r3d:type><r3d:pidSystem>DOI</r3d:pidSystem>"
            '<r3d:api apiType="OAI-PMH">https://old.example.org/oai</r3d:api><r3d:api apiType="other">x</r3d:api>'
            "<r3d:dataLicense><r3d:dataLicenseName>CC</r3d:dataLicenseName></r3d:dataLicense>"
            "<r3d:certificate>CoreTrustSeal</r3d:certificate><r3d:certificate>other</r3d:certificate>"
            "<r3d:versioning>yes</r3d:versioning></r3d:repository></r3d:re3data>"
        )
        original = refresh_snapshots.ROOT
        refresh_snapshots.ROOT = self.root
        try:
            refresh_snapshots.re3data(refresh_snapshots.Fetcher(inputs), "2026-01-01")
        finally:
            refresh_snapshots.ROOT = original
        self.append("guide.toml", '\n[[repositoryKind]]\nid = "domain"\nname = { cs = "oborový", en = "domain" }\n')
        snapshot = (self.root / "content" / "snapshots" / "re3data.toml").read_text(encoding="utf-8")
        self.assertIn('url = "https://www.re3data.org/repository/r3d1"', snapshot)
        self.assertIn('kind = "domain"', snapshot)
        self.assertIn('apis = ["OAI-PMH"]', snapshot)
        self.assertIn('certificates = ["CoreTrustSeal"]', snapshot)
        self.assertIn("versioning = true", snapshot)
        self.assertEqual(self.errors(), [])
        facts = build_crate.page_config(build_crate.load_content(self.root / "content"))["config"]["re3data"]["r3d1"]
        self.assertEqual(facts["name"], "Old")
        self.assertEqual(facts["dataLicenses"], ["CC"])
        self.assertEqual(facts["date"], "2026-01-01")


class FreshnessTests(FixtureCase):
    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def test_changed_item_needs_a_newer_action(self) -> None:
        self.git("init", "-q")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.org", "add", "-A")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.org", "commit", "-q", "-m", "base")
        self.edit("stations/01-one.toml", "Postup.", "Upravený postup.")
        content = build_crate.load_content(self.root / "content")
        report = check_content.Report()
        check_content.check_freshness(report, content, self.root, "HEAD")
        self.assertTrue(any("one.V.L1.1" in error for error in report.errors), report.errors)

        self.append(
            "provenance.toml",
            '\n[[action]]\nid = "edit"\ntype = "update"\nname = "Edit"\nagent = "tester"\ninstruments = ["model"]\n'
            'results = ["one.V.L1.1"]\nendTime = 2099-01-01T00:00:00+00:00\n',
        )
        content = build_crate.load_content(self.root / "content")
        report = check_content.Report()
        check_content.check_freshness(report, content, self.root, "HEAD")
        self.assertEqual(report.errors, [])


class ApiTests(unittest.TestCase):
    """The static API, built from the guide's own content, so the spec's scenarios hold on the real knowledge base."""

    @classmethod
    def setUpClass(cls) -> None:
        content = build_crate.load_content()
        cls.page_url = content["guide"]["guide"]["pageUrl"]
        cls.files = build_api.Api(build_crate.build_crate(content), content).files()
        cls.docs = {path: json.loads(text) for path, text in cls.files.items()}

    @staticmethod
    def target(here: str, link: str) -> str:
        return posixpath.normpath(posixpath.join(posixpath.dirname(here), link))

    def test_a_principle_carries_what_is_about_it(self) -> None:
        here = "api/principles/R1.1.json"
        principle = self.docs[here]
        self.assertEqual(principle["@context"], "../context.jsonld")
        self.assertEqual(set(principle["name"]), {"cs", "en"})
        self.assertTrue(principle["clauses"] and principle["stations"] and principle["metrics"])
        lenses = {
            audience["audienceType"]
            for advice in principle["advice"]
            for audience in build_crate.as_list(advice.get("audience"))
            if isinstance(audience, dict)
        }
        self.assertGreater(len(lenses), 1, "advice for more than one lens")
        metric = self.docs[self.target(here, principle["metrics"][0])]
        self.assertIn("../principles/R1.1.json", build_crate.as_list(metric["inDimension"]))

    def test_checks_are_benchmarks_whose_questions_have_manual_tests(self) -> None:
        checks = [path for path in self.docs if path.startswith("api/checks/")]
        self.assertTrue(checks)
        for path in checks:
            self.assertIn("Benchmark", self.docs[path]["@type"])
            for link in build_crate.as_list(self.docs[path]["hasAssociatedMetric"]):
                metric_path = self.target(path, link)
                metric = self.docs[metric_path]
                self.assertIn("Metric", metric["@type"])
                test_path = self.target(metric_path, metric["hasImplementation"])
                # The path an exported result names for the question's test.
                self.assertEqual(test_path, build_crate.API_FILES["test"].format(id=metric["identifier"]))
                test = self.docs[test_path]
                self.assertEqual(test["@type"], ["Test"])
                self.assertEqual(self.target(test_path, test["isImplementationOf"]), metric_path)

    def test_nothing_names_the_site_by_its_address(self) -> None:
        # The context's vocabulary terms are absolute by necessity; every link between files is relative.
        for path, text in self.files.items():
            if path != build_api.CONTEXT_FILE:
                self.assertNotIn(self.page_url, text, path)

    def test_the_description_documents_every_file(self) -> None:
        openapi = self.docs[build_api.OPENAPI_FILE]
        self.assertEqual(openapi["openapi"], "3.1.0")
        self.assertTrue(all("://" not in server["url"] for server in openapi["servers"]))

        def documented(path: str) -> bool:
            for template in openapi["paths"]:
                prefix, _, rest = template[1:].partition("{")
                suffix = rest.partition("}")[2]
                middle = path[len(prefix) : len(path) - len(suffix)]
                if path == template[1:] or (
                    rest and path.startswith(prefix) and path.endswith(suffix) and middle and "/" not in middle
                ):
                    return True
            return False

        for path in self.files:
            if path.startswith("api/"):
                self.assertTrue(documented(path), path)

    def test_record_ids_are_unique_and_safe_as_file_names(self) -> None:
        content: dict = {"guide": {}}
        with self.assertRaises(build_crate.ContentError):
            build_crate.api_records({"#clause-a": {"@id": "#clause-a", "identifier": "a b"}}, content)
        twice = {
            "#clause-a": {"@id": "#clause-a", "identifier": "x"},
            "#clause-b": {"@id": "#clause-b", "identifier": "x"},
        }
        with self.assertRaises(build_crate.ContentError):
            build_crate.api_records(twice, content)

    def test_output_is_deterministic(self) -> None:
        content = build_crate.load_content()
        self.assertEqual(build_api.Api(build_crate.build_crate(content), content).files(), self.files)

    def test_one_setting_moves_the_guide(self) -> None:
        # The guide's address is set once; a build at another address names the configured one nowhere.
        moved = "https://guide.example.org/fair/"
        with mock.patch.dict(os.environ, {build_crate.BASE_URL_ENV: moved}):
            outputs = build_crate.outputs()
            content = build_crate.load_content()
            api = build_api.Api(build_crate.build_crate(content), content).files()
        for path, text in {**outputs, **api}.items():
            self.assertNotIn(self.page_url, text, path)
        self.assertIn(moved + "terms#", outputs[build_crate.CRATE_FILE])
        self.assertIn(f"<{moved}profile/", outputs[build_crate.PROFILE_DIR + "/profile.ttl"])


if __name__ == "__main__":
    unittest.main()
