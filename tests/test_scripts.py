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
import tomllib
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_api  # noqa: E402
import build_crate  # noqa: E402
import build_site  # noqa: E402
import check_all  # noqa: E402
import check_content  # noqa: E402
import check_duplicates  # noqa: E402
import refresh_snapshots  # noqa: E402
import register_ids  # noqa: E402

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
    def test_station_references_resolve_and_unknown_stations_fail(self) -> None:
        self.edit("stations/01-one.toml", "Take the first step.", "Read [[station:one|the station]].")
        graph = build_crate.Graph()
        build_crate.build_crate(build_crate.load_content(self.root / "content"), graph)
        self.assertTrue(any(link["ref"] == "#station-one" for links in graph.text_links.values() for link in links))
        self.edit("stations/01-one.toml", "station:one", "station:missing")
        self.assertError("unknown entry 'station:missing'")

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
        advice = graph["#advice-one.01"]
        self.assertEqual(advice["citation"], {"@id": "#clause-A.F1.R1"})
        self.assertEqual(len(advice["audience"]), 2)
        action = graph["#action-create"]
        self.assertEqual(action["@type"], "CreateAction")
        self.assertIn({"@id": "#advice-one.03"}, action["result"])
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
        kb = generated[build_crate.KB_SCRIPT] + generated[build_crate.LANGUAGE_SCRIPTS["en"]]
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
        core = json.loads(line[len(prefix) : -1])

        def merge(target, patch):
            for key, value in enumerate(patch) if isinstance(patch, list) else patch.items():
                if value is None:
                    continue
                if isinstance(value, (list, dict)):
                    merge(target[key], value)
                else:
                    target[key] = value

        for lang, path in build_crate.LANGUAGE_SCRIPTS.items():
            start = f"window.FairGuideData.languages[{json.dumps(lang)}] = "
            row = next(row for row in generated[path].splitlines() if row.startswith(start))
            merge(core, json.loads(row[len(start) : -1])["kb"])
        # The page starts with the core; the parts views load on demand are not in it, and core and parts together
        # are the crate.
        self.assertNotIn(f'src="{build_crate.PART_SCRIPTS["standards"]}"', page)
        self.assertFalse(any("guidance" in entity for entity in core["@graph"]))
        graph = {entity["@id"]: dict(entity) for entity in core["@graph"]}
        for name, path in build_crate.PART_SCRIPTS.items():
            start = f"window.FairGuideData.parts[{json.dumps(name)}] = "
            row = next(row for row in generated[path].splitlines() if row.startswith(start))
            part = json.loads(row[len(start) : -1])
            for lang, language_path in build_crate.PART_LANGUAGE_SCRIPTS[name].items():
                start = f"window.FairGuideData.partLanguages[{json.dumps(name)}][{json.dumps(lang)}] = "
                row = next(row for row in generated[language_path].splitlines() if row.startswith(start))
                merge(part, json.loads(row[len(start) : -1])["values"])
            for entity in part["entities"]:
                self.assertNotIn(entity["@id"], graph)
                graph[entity["@id"]] = entity
            for entity_id, properties in part["properties"].items():
                graph[entity_id] |= properties
        crate = json.loads(generated[build_crate.CRATE_FILE])
        self.assertEqual(graph, {entity["@id"]: entity for entity in crate["@graph"]})
        self.assertEqual(
            {key: value for key, value in core.items() if key != "@graph"},
            {key: value for key, value in crate.items() if key != "@graph"},
        )

    def test_page_payload_follows_the_page_and_warns_over_budget(self) -> None:
        generated = build_crate.outputs(self.root)
        sizes = build_crate.page_payload(generated, self.root)
        self.assertIn(build_crate.KB_SCRIPT, sizes)
        self.assertIn(build_crate.UI_SCRIPT, sizes)
        self.assertIsNone(build_crate.payload_warning(sizes, budget_kb=10_000))
        warning = build_crate.payload_warning(sizes, budget_kb=0)
        self.assertIsNotNone(warning)
        self.assertIn("over its budget of 0 KB; largest: ", warning or "")

    def test_helper_labels_are_deferred_with_complete_page_translations(self) -> None:
        self.append("ui.toml", '\n[helper.citation]\nlabel = { cs = "DOI pro citaci", en = "Citation DOI" }\n')
        generated = build_crate.outputs(self.root)
        self.assertNotIn('"helper"', generated[build_crate.UI_SCRIPT])
        for lang, label in [("cs", "DOI pro citaci"), ("en", "Citation DOI")]:
            self.assertNotIn(label, generated[build_crate.LANGUAGE_SCRIPTS[lang]])
            self.assertIn(label, generated[build_crate.PART_LANGUAGE_SCRIPTS["pages"][lang]])
        self.assertIn('"helper"', generated[build_crate.PART_SCRIPTS["pages"]])

    def test_provenance_details_load_with_catalogue_without_losing_dates(self) -> None:
        self.edit(
            "provenance.toml",
            'name = "Create the test content"',
            'name = "Create the test content"\ndescription = "Detailed provenance for the catalogue"',
        )
        generated = build_crate.outputs(self.root)
        self.assertNotIn("Detailed provenance for the catalogue", generated[build_crate.KB_SCRIPT])
        self.assertIn("2026-01-01T12:00:00+01:00", generated[build_crate.KB_SCRIPT])
        self.assertIn("Detailed provenance for the catalogue", generated[build_crate.PART_SCRIPTS["standards"]])
        self.assertIn("Detailed provenance for the catalogue", generated[build_crate.CRATE_FILE])

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
        self.assertError("one.03")
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

    def test_ai_item_says_what_to_check_and_gives_a_prompt(self) -> None:
        self.append(
            "stations/01-one.toml",
            '\n[[advice]]\nid = "one.04"\nlens = "V"\nlevel = "L1"\nkind = "ai"\n'
            'text = { cs = "Tip.", en = "Tip." }\nprompt = { cs = "Zadání.", en = "Prompt." }\nsources = ["A.F1.X1"]\n',
        )
        self.assertError("missing check")
        self.edit("stations/01-one.toml", 'kind = "ai"\n', "")
        self.assertError("only an AI item carries check and prompt")

    def test_a_clause_carries_its_title_and_guidance(self) -> None:
        self.assertEqual(self.errors(), [])
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        clause = next(entity for entity in crate["@graph"] if entity["@id"] == "#clause-CTS.R12")
        self.assertEqual(clause["guidance"]["@language"], "en")
        self.assertIn("- One item.", clause["guidance"]["@value"])
        self.assertIn({"@value": "Discovery and Identification", "@language": "en"}, clause["name"])
        principle = next(
            entity for entity in crate["@graph"] if entity.get("termCode") == "F1" and "relatedTo" in entity
        )
        self.assertIn({"@id": "#clause-CTS.R12"}, build_crate.as_list(principle["relatedTo"]))
        self.edit("ledger.toml", "guidance = '''", "guidance = 1\nnote = '''")
        self.assertError("guidance is the source's own text")

    def test_a_principle_links_only_existing_requirements(self) -> None:
        self.edit("principles.toml", 'cts = ["R12"]', 'cts = ["R99"]')
        self.assertError("cts names no CoreTrustSeal requirement clause 'CTS.R99'")

    def test_a_principle_links_cdif_profiles_and_items_take_its_principles(self) -> None:
        self.edit("principles.toml", 'cts = ["R12"]', 'cts = ["R12"]\ncdif = ["Core"]')
        self.assertError("cdif names no CDIF profile clause 'CDIF.Core'")
        self.append(
            "ledger.toml",
            '\n[[clause]]\nid = "CDIF.Core"\nsource = "report"\nprinciples = []\nactor = "repository"\n'
            'kind = "recommendation"\ntitle = { cs = "Core", en = "Core" }\n'
            'text = { cs = "Základní vlastnosti záznamu.", en = "Base properties of a record." }\n',
        )
        self.append(
            "checks/gate.toml",
            '\n[[item]]\nid = "gate.02"\nrequirement = "CDIF.Core"\ntier = "required"\nowner = ["repository-admin"]\n',
        )
        content = build_crate.load_content(self.root / "content")
        item = next(item for item in content["checks"][0]["item"] if item["id"] == "gate.02")
        self.assertEqual((item["sources"], item["principles"]), (["CDIF.Core"], ["F1"]))
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        principle = next(
            entity for entity in crate["@graph"] if entity.get("termCode") == "F1" and "relatedTo" in entity
        )
        self.assertIn({"@id": "#clause-CDIF.Core"}, build_crate.as_list(principle["relatedTo"]))

    def test_an_item_takes_its_question_from_the_requirement(self) -> None:
        self.append(
            "checks/gate.toml",
            '\n[[item]]\nid = "gate.02"\nrequirement = "CTS.R12"\ntier = "required"\nowner = ["repository-admin"]\n',
        )
        content = build_crate.load_content(self.root / "content")
        item = next(item for item in content["checks"][0]["item"] if item["id"] == "gate.02")
        self.assertEqual(item["statement"]["en"], "The repository enables discovery and citation.")
        self.assertEqual(item["sources"], ["CTS.R12"])
        self.assertEqual(item["principles"], ["F1"])
        self.edit("checks/gate.toml", 'requirement = "CTS.R12"', 'requirement = "CTS.R98"')
        self.assertError("requirement names unknown clause 'CTS.R98'")

    def test_text_may_refer_to_a_clause(self) -> None:
        self.edit(
            "ledger.toml",
            'text = { cs = "NRP zajišťuje DOI.", en = "NRP provides DOIs." }',
            'text = { cs = "NRP zajišťuje DOI podle [[clause:CTS.R12|R12]].", '
            'en = "NRP provides DOIs as [[clause:CTS.R12|R12]] asks." }',
        )
        self.assertEqual(self.errors(), [])
        self.edit("ledger.toml", "[[clause:CTS.R12|R12]].", "[[clause:CTS.R77|R12]].")
        self.assertError("refers to an unknown entry 'clause:CTS.R77'")

    def test_station_without_next_action(self) -> None:
        self.edit(
            "stations/01-one.toml", 'action = { label = { cs = "Začít", en = "Start" }, href = "#check-gate" }\n', ""
        )
        self.assertError("needs one concrete action")

    def test_station_offers_at_most_two_actions(self) -> None:
        one = 'action = { label = { cs = "Začít", en = "Start" }, href = "#check-gate" }'
        self.edit("stations/01-one.toml", one + "\n", "action = [" + ", ".join([one[len("action = ") :]] * 2) + "]\n")
        self.assertEqual(self.errors(), [])
        self.edit("stations/01-one.toml", "action = [", "action = [" + one[len("action = ") :] + ", ")
        self.assertError("at most 2 actions")

    def test_every_station_has_one_key_point_per_lens(self) -> None:
        self.edit("stations/01-one.toml", 'id = "one.02"\nlens = "*"', 'id = "one.02"\nlens = "V"')
        self.assertError("lens SR needs exactly one key point (found 0)")
        self.edit("stations/01-one.toml", 'id = "one.02"\nlens = "V"', 'id = "one.02"\nlens = "*"')
        self.edit("stations/01-one.toml", 'kind = "key"\n', 'kind = "key"\nsteps = [{ cs = "Krok.", en = "Step." }]\n')
        self.assertError("a key point is an L1 item without steps")

    def test_in_page_target_must_exist(self) -> None:
        self.edit("stations/01-one.toml", 'href = "#check-gate"', 'href = "#nowhere"')
        self.assertError("in-page target '#nowhere' does not exist")

    def test_item_without_provenance(self) -> None:
        self.edit("provenance.toml", '"gate.01", ', "")
        self.assertError("item:gate.01: no provenance action covers this item")

    def test_scores_are_forbidden(self) -> None:
        self.append("checks/gate.toml", "\n[check.score]\nmax = 10\n")
        self.assertError("no scores")

    def test_callout_order_lists_every_item(self) -> None:
        self.edit("callouts.toml", 'SR = ["b", "a"]', 'SR = ["b"]')
        self.assertError("must list every item exactly once")

    def test_champion_prefill_outside_curated_set(self) -> None:
        self.edit("checks/gate.toml", 'champion = ["test_one"]', 'champion = ["test_two"]')
        self.assertError("outside the curated set")

    def test_champion_selection_has_fresh_provenance(self) -> None:
        content = build_crate.load_content(self.root / "content")
        self.assertEqual(check_content.content_index(content)["test:test_one"], "test")
        self.assertIn("test:test_one", check_content.item_fingerprints(content))
        self.edit("provenance.toml", ', "test:test_one"', "")
        self.assertError("test:test_one: no provenance action covers this item")

    def test_guide_metadata_has_its_actual_crate_identity(self) -> None:
        content = build_crate.load_content(self.root / "content")
        self.assertIn("guide", check_content.item_fingerprints(content))
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
        self.assertEqual(graph.resolve(["guide"]), ["./"])

    def test_champion_evidence_only_contract(self) -> None:
        self.edit(
            "checks/gate.toml", 'champion = ["test_one"] }', 'champion = ["test_one"] }\nchampionEvidenceOnly = true'
        )
        self.assertEqual(self.errors(), [])
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"))
        item = next(entity for entity in crate["@graph"] if entity["@id"] == "#item-gate.01")
        self.assertTrue(item["championEvidenceOnly"])
        self.edit("checks/gate.toml", "championEvidenceOnly = true", 'championEvidenceOnly = "true"')
        self.assertError("championEvidenceOnly must be a boolean")

    def test_champion_evidence_only_needs_tests(self) -> None:
        self.edit("checks/gate.toml", ', champion = ["test_one"] }', "}\nchampionEvidenceOnly = true")
        self.assertError("championEvidenceOnly needs named Champion tests")

    def test_lookup_must_name_a_link(self) -> None:
        self.edit("checks/gate.toml", 'champion = ["test_one"] }', 'champion = ["test_one"] }\nlookup = "nowhere"')
        self.assertError("lookup names unknown link 'nowhere'")

    def test_lookup_enters_the_crate(self) -> None:
        self.edit("checks/gate.toml", 'champion = ["test_one"] }', 'champion = ["test_one"] }\nlookup = "search"')
        self.assertEqual(self.errors(), [])
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"))
        item = next(entity for entity in crate["@graph"] if entity["@id"] == "#item-gate.01")
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
        # The cited resource takes over the analysis's code with its requirements.
        self.edit("resources.toml", 'id = "service"\n', 'id = "service"\ncode = "A"\n')
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

    def test_one_identifier_names_one_entity(self) -> None:
        self.append(
            "sources.toml",
            '\n[[source]]\nid = "service"\ntype = "webpage"\ntitle = "Other"\n'
            'url = "https://example.org/other"\ndateAccessed = 2026-01-01\n',
        )
        self.assertError("id:service: names several entities")

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
        self.assertError("item:gate.01: the check declares no blocks")
        self.edit(
            "checks/gate.toml",
            "[[item]]",
            '[[block]]\nid = "other"\nname = { cs = "Ostatní", en = "Other" }\n\n[[item]]',
        )
        self.assertError("item:gate.01: block must be one of other")
        self.edit("checks/gate.toml", 'block = "basics"', 'block = "other"')
        self.assertFalse(any("block" in error for error in self.errors()))
        crate = json.loads(build_crate.outputs(self.root)[build_crate.CRATE_FILE])
        item = next(entity for entity in crate["@graph"] if entity["@id"] == "#item-gate.01")
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
            '\n[[resourceType]]\nid = "registry"\n'
            'name = { cs = "repozitář nebo registr", en = "repository or registry" }\n',
        )
        self.append(
            "resources.toml",
            '\n[[resource]]\nid = "repo"\nname = "Test repository"\nurl = "https://example.org/repo"\n'
            'type = "registry"\nstatus = "pilot"\nasOf = 2026-01-01\nstations = ["one"]\n'
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
        self.assertTrue(any("one.03" in error for error in report.errors), report.errors)

        self.append(
            "provenance.toml",
            '\n[[action]]\nid = "edit"\ntype = "update"\nname = "Edit"\nagent = "tester"\ninstruments = ["model"]\n'
            'results = ["one.03"]\nendTime = 2099-01-01T00:00:00+00:00\n',
        )
        content = build_crate.load_content(self.root / "content")
        report = check_content.Report()
        check_content.check_freshness(report, content, self.root, "HEAD")
        self.assertEqual(report.errors, [])


class IdentifierRegisterTests(FixtureCase):
    def register(self) -> list[str]:
        return register_ids.register(self.root / "content")

    def test_registered_identifiers_are_kept(self) -> None:
        added = self.register()
        self.assertIn("advice:one.03", added)
        self.assertIn("questions:gate.01", added)
        self.assertIn("profiles:gate.a", added)
        self.assertEqual(self.errors(), [])
        self.assertEqual(self.register(), [])
        # A renamed entry leaves its registered identifier without an entry, and its new one unregistered.
        self.edit("stations/01-one.toml", 'id = "one.03"', 'id = "one.04"')
        self.assertError("'one.03' is registered but no entry has it")
        self.assertError("'one.04' is not registered")
        # Registering the new identifier keeps the old one, which stays until it is retired.
        self.assertEqual(self.register(), ["advice:one.04"])
        self.assertError("'one.03' is registered but no entry has it")
        self.edit("identifiers.toml", "[retired]\n", '[retired]\nadvice = ["one.03"]\n')
        self.assertEqual(self.errors(), [])
        self.assertEqual(self.register(), [])
        self.assertIn('advice = [\n  "one.03",\n]', (self.root / "content" / "identifiers.toml").read_text("utf-8"))

    def test_retired_identifier_is_not_reused(self) -> None:
        self.register()
        self.edit("identifiers.toml", "[retired]\n", '[retired]\nadvice = ["one.03"]\n')
        self.assertError("'one.03' is retired and cannot name another entry")
        self.edit("identifiers.toml", '[retired]\nadvice = ["one.03"]\n', '[retired]\nadvice = ["one.99"]\n')
        self.assertError("'one.99' is retired but was never registered")
        self.edit("identifiers.toml", "[retired]\n", '[retired]\nterms = ["1"]\n')
        self.assertError("identifiers:terms: unknown kind")


class DuplicateTests(FixtureCase):
    ADVICE_COPY = (
        '\n[[advice]]\nid = "one.04"\nlens = "V"\nlevel = "L1"\ntext = { cs = "Postup.", en = "Steps." }\n'
        'sources = ["A.F1.X1"]\n'
    )

    def duplicates(self) -> list[str]:
        content = build_crate.load_content(self.root / "content")
        path = self.root / "content" / check_duplicates.ACCEPTED_FILE
        accepted = tomllib.loads(path.read_text(encoding="utf-8")).get("accepted", []) if path.exists() else []
        return check_duplicates.check(content, accepted).errors

    def assertDuplicate(self, fragment: str) -> None:  # noqa: N802 - unittest naming
        errors = self.duplicates()
        self.assertTrue(any(fragment in error for error in errors), errors)

    def dashboard(self, record: str = "") -> None:
        snapshots = self.root / "content" / "snapshots"
        snapshots.mkdir(exist_ok=True)
        text = DASHBOARD_SNAPSHOT.replace('name = "Resource one"', 'name = "Resource one"' + record)
        (snapshots / "fip-dashboard.toml").write_text(text, encoding="utf-8")

    def test_fixture_has_no_duplicates(self) -> None:
        self.assertEqual(self.duplicates(), [])

    def test_same_address_in_two_entries(self) -> None:
        self.append(
            "sources.toml",
            '\n[[source]]\nid = "copy"\ntype = "webpage"\ntitle = "Copy"\n'
            'url = "http://www.example.org/service/"\ndateAccessed = 2026-01-01\n',
        )
        self.assertDuplicate(
            "resource:service: describes one thing with source:copy (address 'example.org/service'); merge them"
        )

    def test_registry_record_needs_a_link(self) -> None:
        self.dashboard('\nurl = "https://example.org/service"')
        self.assertDuplicate(
            "fip-dashboard:r1: describes one thing with resource:service (address 'example.org/service'"
        )
        self.assertDuplicate("link the record with fipDashboard")
        self.edit("resources.toml", 'fipClass = ["Registry"]', 'fipClass = ["Registry"]\nfipDashboard = "r1"')
        self.assertEqual(self.duplicates(), [])

    def test_two_entries_cannot_link_one_record(self) -> None:
        self.dashboard()
        self.edit("resources.toml", 'fipClass = ["Registry"]', 'fipClass = ["Registry"]\nfipDashboard = "r1"')
        (self.root / "content" / "repositories.toml").write_text(
            '[[repository]]\nid = "repo"\nname = "Repo"\nurl = "https://repo.example.org/"\nkind = "general"\n'
            'fipDashboard = "r1"\n',
            encoding="utf-8",
        )
        self.assertDuplicate("repository:repo: links the same record as resource:service (FIP Dashboard ID 'r1')")

    def test_the_guide_says_each_thing_once(self) -> None:
        self.append("stations/01-one.toml", self.ADVICE_COPY)
        self.assertDuplicate(
            "advice:one.03: describes one thing with advice:one.04 (text 'postup'; text 'steps'); say it once"
        )
        self.append(
            "checks/gate.toml",
            '\n[[item]]\nid = "gate.02"\ntier = "required"\nprinciples = ["F1"]\n'
            'statement = { cs = "Repozitář přiděluje PID.", en = "The repository assigns PIDs." }\n'
            'sources = ["A.F1.R1"]\n',
        )
        self.assertDuplicate("item:gate.01: describes one thing with item:gate.02")

    def test_an_accepted_group_states_why_and_still_occurs(self) -> None:
        self.append("stations/01-one.toml", self.ADVICE_COPY)
        accepted = self.root / "content" / check_duplicates.ACCEPTED_FILE
        accepted.write_text(
            '[[accepted]]\nentries = ["advice:one.03", "advice:one.04"]\nreason = "Two audiences."\n', encoding="utf-8"
        )
        self.assertEqual(self.duplicates(), [])
        accepted.write_text(
            '[[accepted]]\nentries = ["advice:one.03", "advice:one.04"]\nreason = ""\n\n'
            '[[accepted]]\nentries = ["advice:one.01", "advice:one.99"]\nreason = "Gone."\n',
            encoding="utf-8",
        )
        self.assertDuplicate("duplicates:1: an accepted group states no reason")
        self.assertDuplicate("duplicates:2: names no entry: advice:one.99")
        self.assertDuplicate("duplicates:2: the accepted group no longer occurs; remove it")


class BuildOutputTests(FixtureCase):
    def test_the_repository_holds_no_build_output(self) -> None:
        def git(*args: str) -> None:
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

        git("init", "-q")
        (self.root / "ro-crate-metadata.json").write_text("{}", encoding="utf-8")
        (self.root / "api").mkdir()
        (self.root / "api" / "principles.json").write_text("{}", encoding="utf-8")
        (self.root / "api" / "index.html").write_text("<!doctype html>", encoding="utf-8")
        page = self.root / "index.html"
        page.write_text(
            page.read_text(encoding="utf-8").replace("<!-- /generated:ui -->", "x<!-- /generated:ui -->"),
            encoding="utf-8",
        )
        git("add", "-A")
        report = check_content.Report()
        check_content.check_no_build_output(report, self.root)
        named = " ".join(report.errors)
        for expected in ("ro-crate-metadata.json", "api/principles.json", "generated block 'ui'"):
            self.assertIn(expected, named)
        self.assertNotIn("api/index.html", named, "the API's authored page is not build output")


class SiteTests(unittest.TestCase):
    def test_repository_family_uses_meaning_and_reviewed_identity(self) -> None:
        content = build_crate.load_content()
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
        members = {item["@id"] for item in build_crate.as_list(graph.entities["#repositories"]["hasPart"])}
        self.assertTrue({"#resource-nma", "#resource-fairsharing", "#fer-nusl", "#fer-nrp-invenio"} <= members)
        self.assertNotIn("#fer-asep-arl", members)
        self.assertNotIn("#fer-clarin-dspace", members)
        self.assertNotIn("#fer-zenodo", members)
        self.assertEqual(graph.index["fip-dashboard.asep-arl"], graph.index["re3data.r3d100014032"])
        self.assertEqual(graph.index["fip-dashboard.clarin-dspace"], graph.index["re3data.r3d100010386"])
        nma = graph.entities["#resource-nma"]
        self.assertEqual(nma["serviceStatus"], {"@id": "#status-operational"})
        self.assertEqual(nma["repositoryFunction"], {"@id": "#rfunction-find-metadata"})
        self.assertEqual(
            build_crate.as_list(graph.entities["#fer-nusl"]["repositoryFunction"]),
            [{"@id": "#rfunction-deposit-publications"}],
        )
        as_ep = graph.entities[graph.index["re3data.r3d100014032"][0]]
        self.assertIn({"@id": "#rfunction-deposit-data"}, as_ep["repositoryFunction"])
        self.assertIn({"@id": "#rfunction-deposit-publications"}, as_ep["repositoryFunction"])
        self.assertIn({"@id": "#snapshot-fip-dashboard"}, as_ep["isBasedOn"])

    def test_record_annotations_are_validated_and_do_not_guess_identity(self) -> None:
        content = build_crate.load_content()
        report = check_content.Report()
        content["repository_records"][0]["fipDashboard"] = "nonexistent"
        content["repository_records"][0]["evidence"] = []
        content["repository_records"][0]["functions"] = ["not-a-function"]
        check_content.check_repositories(report, content, check_content.vocabularies(content), TODAY)
        self.assertTrue(any("unknown FIP Dashboard" in error for error in report.errors))
        self.assertTrue(any("need published evidence" in error for error in report.errors))
        self.assertTrue(any("unknown repository function" in error for error in report.errors))
        content = build_crate.load_content()
        content["repository_records"] = []
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
        members = {item["@id"] for item in build_crate.as_list(graph.entities["#repositories"]["hasPart"])}
        self.assertIn("#fer-asep-arl", members)
        self.assertIn("#fer-clarin-dspace", members)

    def test_duplicate_check_follows_reviewed_cross_registry_links(self) -> None:
        content = build_crate.load_content()
        entries = {item.name: item for item in check_duplicates.entries(content)}
        self.assertIn("fd:asep-arl", entries["re3data:r3d100014032"].keys)
        self.assertIn("fd:clarin-dspace", entries["re3data:r3d100010386"].keys)

    def test_one_command_builds_the_whole_site(self) -> None:
        out = build_crate.ROOT / ".cache" / "test-site"
        try:
            build_site.build(out)
            for path in (
                "index.html",
                "ro-crate-preview.html",
                "ro-crate-metadata.json",
                "linkset.json",
                "assets/data/kb.js",
                "assets/data/kb-standards.js",
                "assets/data/kb-fips.js",
                "assets/data/kb-pages.js",
                "assets/data/ui.js",
                "assets/css/app.css",
                "assets/js/app.js",
                "profile/fair-guide/profile.ttl",
                "openapi.json",
                "api/principles/R1.1.json",
                "api/index.html",
                "api/swagger-ui/swagger-ui-bundle.js",
                "profile/0.1/index.html",
            ):
                self.assertTrue((out / path).is_file(), path)
            # The profile's identifier resolves to a page whose links to its files lead somewhere.
            landing = out / "profile" / "0.1" / "index.html"
            for href in re.findall(r'href="(\.\./[^"]+)"', landing.read_text(encoding="utf-8")):
                target = (landing.parent / href).resolve()
                self.assertTrue(target.is_file() or (target / "index.html").is_file(), href)
            page = (out / "index.html").read_text(encoding="utf-8")
            self.assertTrue(
                all(match.group("body").strip() for match in build_crate.BLOCK.finditer(page)), "every block is filled"
            )
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_the_build_never_replaces_the_repository(self) -> None:
        with self.assertRaises(build_crate.ContentError):
            build_site.build(build_crate.ROOT)


class CheckAllTests(unittest.TestCase):
    def test_checks_run_at_once_and_a_failure_keeps_its_output(self) -> None:
        python = sys.executable
        jobs = [
            check_all.Job("passes", [python, "-c", "print('fine')"]),
            check_all.Job("fails", [python, "-c", "import sys; print('broken'); sys.exit(3)"]),
        ]
        lines: list[str] = []
        results = check_all.run_all(jobs, 2, dict(os.environ), report=lines.append)
        self.assertEqual([result.job.name for result in results], ["passes", "fails"])
        self.assertEqual([result.ok for result in results], [True, False])
        self.assertIn("broken", results[1].output)
        self.assertEqual(len(lines), 2)

    def test_a_missing_tool_fails_its_check_without_stopping_the_run(self) -> None:
        result = check_all.run(check_all.Job("missing", ["no-such-tool-for-the-guide"]), dict(os.environ))
        self.assertFalse(result.ok)
        self.assertIn("no-such-tool-for-the-guide", result.output)

    def test_live_checks_run_only_on_request(self) -> None:
        self.assertNotIn("live", [job.name for job in check_all.jobs("HEAD", live=False)])
        self.assertIn("live", [job.name for job in check_all.jobs("HEAD", live=True)])

    def test_an_unknown_check_is_refused(self) -> None:
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            check_all.main(["--only", "no-such-check"])


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
                implementations = [
                    self.target(metric_path, implementation)
                    for implementation in build_crate.as_list(metric["hasImplementation"])
                ]
                test_path = build_crate.API_FILES["test"].format(id=metric["identifier"])
                # The path an exported result names for the question's test.
                self.assertIn(test_path, implementations)
                test = self.docs[test_path]
                self.assertEqual(test["@type"], ["Test"])
                self.assertEqual(self.target(test_path, test["isImplementationOf"]), metric_path)
                for automatic_path in set(implementations) - {test_path}:
                    automatic = self.docs[automatic_path]
                    self.assertIn("Test", automatic["@type"])
                    self.assertEqual(self.target(automatic_path, automatic["isImplementationOf"]), metric_path)

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
