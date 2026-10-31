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
import urllib.parse
from datetime import UTC, date, datetime
from html.parser import HTMLParser
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
import fix_duplicates  # noqa: E402
import refresh_snapshots  # noqa: E402
import register_ids  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "minimal"
TODAY = date(2026, 3, 1)
# Two life-cycle models, the path's and another, with one published correspondence (docs/content-model.md,
# Life-cycle models); FixtureCase.add_lifecycles writes them into a fixture copy with covering provenance.
LIFECYCLES = {
    "lifecycle/1-path.toml": (
        '[lifecycle]\nid = "rdmkit"\nposition = 1\nsource = "report"\nname = { cs = "Cyklus", en = "Cycle" }\n\n'
        '[[stage]]\nid = "plan"\nname = { cs = "Plánování", en = "Plan" }\ndefinition = "Planning the data."\n'
        'translation = "Plánování dat."\nlocator = "p. 1"\n'
    ),
    "lifecycle/2-other.toml": (
        '[lifecycle]\nid = "other"\nposition = 2\nsource = "report"\nname = { cs = "Jiný", en = "Other" }\n\n'
        '[[stage]]\nid = "fund"\nname = { cs = "Financování", en = "Fund" }\ntranslated = "cs"\n'
        'definition = "Funding the work."\nlocator = "p. 2"\n'
    ),
    "lifecycle/crosswalk.toml": (
        '[[correspondence]]\nid = "rdmkit-plan-other-fund"\nguideRoute = "life/xw"\n'
        'stages = ["rdmkit.plan", "other.fund"]\nbasis = "published"\nsource = "report"\n'
        'locator = "Figure 1"\n'
    ),
}


class FixtureCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "guide"
        shutil.copytree(FIXTURE, self.root)
        (self.root / ".github").mkdir()
        shutil.copy(
            refresh_snapshots.ROOT / ".github/source-registry.json",
            self.root / ".github/source-registry.json",
        )

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

    def add_lifecycles(self) -> None:
        """LIFECYCLES in the fixture, covered by provenance, with the fixture's station in the path's stage."""
        (self.root / "content" / "lifecycle").mkdir()
        for relative, text in LIFECYCLES.items():
            (self.root / "content" / relative).write_text(text, encoding="utf-8")
        self.edit(
            "provenance.toml",
            '"test:test_one"]',
            '"test:test_one", "lifecycle:*", "rdmkit.*", "other.*", "crosswalk:*"]',
        )
        self.edit("stations/01-one.toml", "position = 1\n", 'position = 1\nlifecycleStage = "plan"\n')

    def errors(self) -> list[str]:
        content = build_crate.load_content(self.root / "content")
        return check_content.check(content, self.root, today=TODAY).errors

    def assertError(self, fragment: str) -> None:  # noqa: N802 - unittest naming
        errors = self.errors()
        self.assertTrue(any(fragment in error for error in errors), f"no error containing {fragment!r}: {errors}")


class GeneratorTests(FixtureCase):
    def test_original_term_definition_keeps_source_language_and_snapshot(self) -> None:
        (self.root / "content" / "glossary.toml").write_text(
            '[glossary]\nsource = "Glossary"\n\n[[term]]\n alternateIds = [{ scheme = "heslar", value = "1" }]\n'
            'id = "1"\nlabel = "Term"\n'
            'definition = "Snapshot definition."\ndefinitionLanguage = "en"\n',
            encoding="utf-8",
        )
        self.edit(
            "ledger.toml",
            'id = "A.F1.R1"\n',
            'id = "A.F1.R1"\nterms = ["1"]\nguidance = "Original source definition."\n'
            'guidanceLanguage = "cs"\nlocator = "p. 5"\n',
        )
        entities = {
            item["@id"]: item
            for item in build_crate.build_crate(build_crate.load_content(self.root / "content"))["@graph"]
        }
        self.assertEqual(entities["#term-1"]["description"], {"@value": "Snapshot definition.", "@language": "en"})
        self.assertEqual(entities["#term-1"]["subjectOf"], {"@id": "#clause-A.F1.R1"})
        self.assertEqual(
            entities["#clause-A.F1.R1"]["guidance"], {"@value": "Original source definition.", "@language": "cs"}
        )
        self.assertEqual(entities["#clause-A.F1.R1"]["sourceLocator"], "p. 5")
        self.edit("ledger.toml", 'terms = ["1"]', 'terms = ["missing"]')
        self.assertError("original definition names unknown term 'missing'")

    def test_rdmkit_enriches_one_tool_with_registry_links_and_training(self) -> None:
        self.append(
            "resources.toml",
            '\n[resource.rdmkit]\nid = "example-tool"\nbiotools = "example_tool"\n'
            'fairsharing = "NA"\ntess = "Example tool"\n',
        )
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"))
        tools = [item for item in crate["@graph"] if item.get("identifier") == "service"]
        self.assertEqual(len(tools), 1)
        self.assertEqual(
            tools[0]["rdmkitRecord"], "https://rdmkit.elixir-europe.org/all_tools_and_resources#example-tool"
        )
        self.assertEqual(tools[0]["sameAs"], {"@id": "https://bio.tools/example_tool"})
        self.assertEqual(tools[0]["trainingSearch"], "https://tess.elixir-europe.org/search?q=%22Example+tool%22")
        self.edit("resources.toml", 'id = "example-tool"', 'id = "invalid identifier"')
        self.assertError("rdmkit needs its source record ID")

    def add_infrastructures(
        self, member: str = 'resource = "service"\nrole = "service"\nlocator = "Section 3"\n'
    ) -> None:
        """An infrastructure that operates the fixture's service and a node whose member is that service, covered by
        provenance, with the vocabularies they use."""
        self.append(
            "guide.toml",
            '\n[[researchField]]\nid = "energy"\nname = { cs = "energetika", en = "energy" }\n'
            '\n[[infrastructurePhase]]\nid = "operational"\nname = { cs = "provoz", en = "operational" }\n'
            '\n[[infrastructureCharacter]]\nid = "virtual"\nname = { cs = "virtuální", en = "virtual" }\n'
            '\n[[esfriStatus]]\nid = "landmark"\nname = { cs = "ESFRI Landmark", en = "ESFRI Landmark" }\n'
            '\n[[nodeRole]]\nid = "service"\nname = { cs = "služba uzlu", en = "node service" }\n'
            '\n[[nodeRole]]\nid = "repository"\nname = { cs = "repozitář uzlu", en = "node repository" }\n',
        )
        (self.root / "content" / "infrastructures.toml").write_text(
            '[infrastructures]\nsource = "report"\nchecked = 2026-01-01\n\n'
            '[[infrastructure]]\nid = "ri"\nacronym = "RI-CZ"\n'
            'name = { cs = "Infrastruktura", en = "Infrastructure" }\n'
            'host = "A University"\nfield = "energy"\nphase = "operational"\ncharacter = "virtual"\nincluded = 2010\n'
            'esfri = ["landmark"]\nannex1 = "Annex 1, p. 1"\n\n'
            '[[infrastructure.nodeOf]]\nname = "EU-RI ERIC"\nesfri = "landmark"\n\n'
            '[[infrastructure.eric]]\nname = "EU-RI ERIC"\nentry = "2012"\n\n'
            '[[infrastructure.operates]]\nresource = "service"\nevidence = "https://ri.example.org/about"\n',
            encoding="utf-8",
        )
        (self.root / "content" / "eosc-node.toml").write_text(
            '[node]\nid = "eosc-cz-node"\nname = "EOSC CZ Node"\noperator = "ri"\nstate = "candidate"\n'
            'stateDate = 2026-01-01\nsources = ["report"]\nchecked = 2026-01-02\n\n[[member]]\n' + member,
            encoding="utf-8",
        )
        self.edit("provenance.toml", '"test:test_one"]', '"test:test_one", "infrastructure:*", "node:eosc-cz-node"]')

    def test_infrastructure_names_keep_their_own_sources(self) -> None:
        self.add_infrastructures()
        self.append(
            "sources.toml",
            '\n[[source]]\nid = "official-names"\ntype = "webpage"\nname = "Official names"\n'
            'title = "Official names"\nurl = "https://names.example.org/"\ninLanguage = "cs"\n',
        )
        self.edit("infrastructures.toml", 'id = "ri"\n', 'id = "ri"\nnamesSource = "official-names"\n')
        content = build_crate.load_content(self.root / "content")
        crate = build_crate.build_crate(content)
        entities = {item["@id"]: item for item in crate["@graph"]}
        expected = [{"@id": "#source-report"}, {"@id": "#source-official-names"}]
        self.assertEqual(entities["#infrastructure-ri"]["isBasedOn"], expected)
        self.assertEqual(entities["#infrastructures"]["isBasedOn"], expected)
        self.assertEqual(entities["#eric-eu-ri-eric"]["isBasedOn"], {"@id": "#source-report"})
        self.edit("infrastructures.toml", 'namesSource = "official-names"', 'namesSource = "missing-source"')
        self.assertError("unknown namesSource 'missing-source'")

    def test_infrastructure_official_site_and_reviewed_mark(self) -> None:
        self.add_infrastructures()
        self.edit(
            "infrastructures.toml", 'id = "ri"\n', 'id = "ri"\nwebsite = "https://ri.example.org/"\nlogo = false\n'
        )
        self.assertEqual(self.errors(), [])
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"))
        entity = next(item for item in crate["@graph"] if item["@id"] == "#infrastructure-ri")
        self.assertEqual(entity["sameAs"], {"@id": "https://ri.example.org/"})
        self.edit("infrastructures.toml", "logo = false", 'logo = "file:///private"')
        self.assertError("logo must be an HTTPS address")

    def test_infrastructures_and_the_node_keep_their_relations_apart(self) -> None:
        self.add_infrastructures()
        self.assertEqual(self.errors(), [])
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"))
        entities = {item["@id"]: item for item in crate["@graph"]}
        infrastructure = entities["#infrastructure-ri"]
        # The node of a European infrastructure, an ERIC membership and operating an entry stay three relations.
        self.assertEqual(infrastructure["nationalNodeOf"], {"@id": "#european-ri-eu-ri-eric"})
        self.assertEqual(infrastructure["memberOf"], {"@id": "#eric-eu-ri-eric"})
        self.assertEqual(entities["#eric-eu-ri-eric"]["czechMembershipSince"], "2012")
        self.assertEqual(infrastructure["operates"], {"@id": "#resource-service"})
        service = entities["#resource-service"]
        self.assertEqual(service["operatedBy"], {"@id": "#infrastructure-ri"})
        self.assertEqual(service["operatedBySource"], "https://ri.example.org/about")
        # The entry carries its membership: role, date checked and source; the node names its operator and state.
        membership = entities[service["nodeMembership"]["@id"]]
        self.assertEqual(membership["roleName"], {"@id": "#noderole-service"})
        self.assertEqual(membership["statusAsOf"], "2026-01-02")
        self.assertEqual(entities["#eosc-cz-node"]["operatedBy"], {"@id": "#infrastructure-ri"})
        self.assertEqual(entities["#eosc-cz-node"]["nodeState"], "candidate")
        records = build_crate.api_records(entities, build_crate.load_content(self.root / "content"))
        self.assertIn(("ri", "#infrastructure-ri"), records["infrastructures"])
        self.assertIn(("eosc-cz-node", "#eosc-cz-node"), records["organizations"])
        # The infrastructures load with the catalogue; the node and its memberships come with every view.
        core, parts = build_crate.split_crate(crate)
        self.assertIn("#infrastructure-ri", [item["@id"] for item in parts["fips"]["entities"]])
        self.assertIn("#eosc-cz-node", [item["@id"] for item in core["@graph"]])

    def test_infrastructure_and_node_records_are_checked(self) -> None:
        self.add_infrastructures('resource = "service"\nrole = "repository"\nlocator = "Appendix A"\n')
        self.assertError("a repository's planned integration names its milestone (M6, M12)")
        self.edit("infrastructures.toml", 'evidence = "https://ri.example.org/about"\n', "")
        self.assertError("an operator relation is recorded only with the source that states it")
        self.edit("infrastructures.toml", 'field = "energy"', 'field = "astrology"')
        self.assertError("unknown field 'astrology'")
        self.edit("eosc-node.toml", 'operator = "ri"', 'operator = "elsewhere"')
        self.assertError("the node's operator 'elsewhere' is not a listed infrastructure")

    def test_station_references_resolve_and_unknown_stations_fail(self) -> None:
        self.edit("stations/01-one.toml", "Take the first step.", "Read [[station:one|the station]].")
        graph = build_crate.Graph()
        build_crate.build_crate(build_crate.load_content(self.root / "content"), graph)
        self.assertTrue(any(link["ref"] == "#station-one" for links in graph.text_links.values() for link in links))
        self.edit("stations/01-one.toml", "station:one", "station:missing")
        self.assertError("unknown entry 'station:missing'")

    def test_embedded_json_escapes_only_the_unsafe_characters(self) -> None:
        # Markup and the two JavaScript line terminators are escaped; every other character, spaces included, stays.
        value = {"text": "a <b> & c d e"}
        serialised = build_crate.script_json(value)
        self.assertEqual(serialised, '{"text":"a \\u003cb\\u003e \\u0026 c\\u2028d\\u2029e"}')
        self.assertEqual(json.loads(serialised), value)

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

    def test_glossary_definition_language_license_and_deferred_text_are_lossless(self) -> None:
        definition = "Původní česká definice.\n\nDruhý odstavec."
        license_uri = "https://creativecommons.org/licenses/by/4.0/"
        graph = build_crate.Graph()
        build_crate.build_glossary(
            graph,
            {
                "glossary": {"source": "Heslář", "license": license_uri},
                "term": [
                    {
                        "id": 1,
                        "label": {"cs": "data", "en": "data"},
                        "definition": definition,
                        "definitionLanguage": "cs",
                        "url": "https://example.org/term/1",
                    },
                    {"id": 2, "label": {"cs": "pojem", "en": "term"}},
                ],
            },
        )
        entity = graph.entities["#term-1"]
        self.assertEqual(entity["description"], {"@value": definition, "@language": "cs"})
        self.assertEqual(entity["license"], license_uri)
        self.assertEqual(entity["url"], "https://example.org/term/1")
        self.assertNotIn("description", graph.entities["#term-2"])
        crate = {"@graph": list(graph.entities.values())}
        core, parts = build_crate.split_crate(crate)
        rebuilt = {entry["@id"]: dict(entry) for entry in core["@graph"]}
        self.assertNotIn("description", rebuilt["#term-1"])
        for part in parts.values():
            for entry in part["entities"]:
                rebuilt[entry["@id"]] = dict(entry)
            for identifier, properties in part["properties"].items():
                rebuilt[identifier].update(properties)
        self.assertEqual(rebuilt, graph.entities)

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
            '[[term]]\nalternateIds = [{ scheme = "heslar", value = "pid" }]\nid = "pid"\n'
            'label = { cs = "PID", en = "PID" }\n',
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
        merge = build_crate.apply_language_patch  # the documented semantics the page applies

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

    def test_the_reference_map_comes_from_the_catalogue_identity(self) -> None:
        """A reference may name any published catalogue entry by `collection:record`, so a repository and a
        catalogue tool are referenceable as a resource is; the guide's short forms stay."""
        content = build_crate.load_content()
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
        targets = build_crate.reference_targets(content, graph)
        self.assertIn("repo/gen/zenodo", targets)
        self.assertIn("res/tool/github", targets)
        self.assertNotIn("knav.github", targets)
        self.assertTrue(any(key.startswith("q/") for key in targets), "a question is nameable")
        self.assertIn("page:software", targets, "the short forms stay")

    def test_a_repository_reference_resolves_and_an_unknown_one_fails(self) -> None:
        self.edit("provenance.toml", '"test:test_one"]', '"test:test_one", "zenodo"]')
        (self.root / "content" / "repositories.toml").write_text(
            '[[repository]]\nid = "zenodo"\nname = "Zenodo"\nurl = "https://zenodo.org/"\nkind = "general"\n'
            'status = "pilot"\nasOf = 2026-01-01\n',
            encoding="utf-8",
        )
        self.edit(
            "stations/01-one.toml",
            'text = { cs = "Udělejte první krok.", en = "Take the first step." }',
            'text = { cs = "Uložte v [[repo/gen/zenodo|Zenodu]].", en = "Deposit in [[repo/gen/zenodo|Zenodo]]." }',
        )
        self.assertEqual(self.errors(), [])
        self.edit("stations/01-one.toml", "repo/gen/zenodo", "repo/gen/nope")
        self.assertError("refers to an unknown entry 'repo/gen/nope'")

    def test_missing_marker_is_reported(self) -> None:
        page = self.root / "index.html"
        page.write_text(page.read_text(encoding="utf-8").replace("<!-- generated:ui --><!-- /generated:ui -->", ""))
        with self.assertRaises(build_crate.ContentError):
            build_crate.outputs(self.root)

    def test_lifecycle_stages_crosswalk_and_path_link(self) -> None:
        self.add_lifecycles()
        content = build_crate.load_content(self.root / "content")
        crate = build_crate.build_crate(content)
        entities = {entity["@id"]: entity for entity in crate["@graph"]}
        plan = entities["#lifecycle-rdmkit.plan"]
        self.assertEqual(
            plan["description"],
            [{"@value": "Planning the data.", "@language": "en"}, {"@value": "Plánování dat.", "@language": "cs"}],
        )
        self.assertEqual(plan["descriptionTranslation"], "cs")
        self.assertEqual(plan["inDefinedTermSet"], {"@id": "#lifecycle-rdmkit"})
        self.assertEqual(entities["#lifecycle-other.fund"]["nameTranslation"], "cs")
        correspondence = entities["#crosswalk-rdmkit-plan-other-fund"]
        self.assertEqual(correspondence["mappingBasis"], "published")
        self.assertEqual(correspondence["about"], [{"@id": "#lifecycle-rdmkit.plan"}, {"@id": "#lifecycle-other.fund"}])
        self.assertEqual(correspondence["citation"], {"@id": "#source-report"})
        self.assertEqual(entities["#station-one"]["lifecycleStage"], {"@id": "#lifecycle-rdmkit.plan"})
        self.assertEqual(entities["#path"]["isBasedOn"], {"@id": "#lifecycle-rdmkit"})
        # The path's stages name the rail in the core; definitions and the other models load with the model part.
        core, parts = build_crate.split_crate(crate)
        core_ids = {entity["@id"]: entity for entity in core["@graph"]}
        self.assertNotIn("description", core_ids["#lifecycle-rdmkit.plan"])
        self.assertIn("description", parts["model"]["properties"]["#lifecycle-rdmkit.plan"])
        self.assertNotIn("#crosswalk-rdmkit-plan-other-fund", core_ids)
        records = build_crate.api_records(entities, content)["lifecycle"]
        self.assertEqual(
            {record for record, _ in records},
            {"rdmkit", "rdmkit.plan", "other", "other.fund", "crosswalk", "rdmkit-plan-other-fund"},
        )


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

    def test_a_quote_without_a_licence_stays_within_the_right_of_quotation(self) -> None:
        within = " ".join(["word"] * (check_content.QUOTE_LIMIT - 2))
        # List markers, bulleted or numbered, are not words, and a word hyphenated at a line break is one word.
        quote = f"- {within}\n1. hyphen-\nated\n2) word"
        self.edit("ledger.toml", "Guidance as the standard publishes it.\n\n- One item.", quote)
        self.assertEqual(self.errors(), [])
        self.edit("ledger.toml", "2) word", "2) word more")
        self.assertError(f"guidance quotes {check_content.QUOTE_LIMIT + 1} words from a source that records no licence")
        # The quote is attributed to its place in the source.
        self.edit("ledger.toml", 'locator = "R12"\n', "")
        self.assertError("guidance quoted from a source that records no licence needs a locator")
        # A licence the source records, or the Public Domain Mark of a source outside copyright, lifts both.
        public_domain = 'license = "https://creativecommons.org/publicdomain/mark/1.0/"\n'
        self.edit("sources.toml", 'title = "Test standard"\n', 'title = "Test standard"\n' + public_domain)
        self.assertEqual(self.errors(), [])

    def test_a_cited_work_records_one_citation_and_a_known_licence(self) -> None:
        # A resource's citation is a cited work too, and the licence it records is the one its quotes carry.
        licence = "https://creativecommons.org/licenses/by/4.0/"
        service = 'url = "https://example.org/service"\n'
        fields = f'type = "webpage", title = "Test service", dateAccessed = 2026-01-01, license = "{licence}"'
        self.edit("resources.toml", service, f"{service}citation = {{ {fields} }}\n")
        self.assertEqual(self.errors(), [])
        cited = check_content.cited_licences(build_crate.load_content(self.root / "content"))
        self.assertEqual(cited["service"], licence)
        # A second citation nested in the first is read by nothing, so it is rejected rather than ignored.
        nested = ', citation = { type = "webpage", title = "Other page" }'
        self.edit("resources.toml", f'"{licence}" }}', f'"{licence}"{nested} }}')
        self.assertError("a citation describes one work")
        self.edit("resources.toml", nested, "")
        # A licence is recorded as the whole canonical address of one known licence, so a free-text value, a
        # publisher's home page, another page on its site, an unreviewed licence or text after an address cannot lift
        # the bound unseen, and one licence never has two addresses.
        refused = (
            "All rights reserved",
            "https://creativecommons.org/",
            f"{licence} and more",
            "https://creativecommons.org/licenses/by/",
            "https://creativecommons.org/licenses/by/4.0",
            "https://creativecommons.org/licenses/by/4.0/deed.en",
            "https://creativecommons.org/licenses/by/4.0/legalcode",
            "https://creativecommons.org/licenses/by/4.0/legalcode.en",
            "https://creativecommons.org/licenses/nonexistent/9.9/",
            # Creative Commons published no version 9.9 and no unported 2.1, and 4.0 has no ports: such an address is
            # missing or lands on the deed.
            "https://creativecommons.org/licenses/by/9.9/",
            "https://creativecommons.org/licenses/by/2.1/",
            "https://creativecommons.org/licenses/by/4.0/xyz/",
            "https://creativecommons.org/licenses/by/4.0/cz/",
            # BY-NC-ND 1.0 is published as by-nd-nc, to which by-nc-nd/1.0/ redirects; later versions keep by-nc-nd.
            "https://creativecommons.org/licenses/by-nc-nd/1.0/",
            "https://creativecommons.org/licenses/by-nc-nd/1.0/fi/",
            "https://creativecommons.org/licenses/by-nd-nc/2.0/",
            "https://www.creativecommons.org/licenses/by/4.0/",
            "https://www.gnu.org/licenses/gpl-3.0",
            "https://www.gnu.org/licenses/gpl-3.0.en.html",
            "https://www.gnu.org/licenses/gpl-faq.html",
            "https://www.gnu.org/licenses/license-list.html",
            "https://gnu.org/licenses/gpl-3.0.html",
            # GNU keeps a superseded version under old-licenses/ and redirects its root address there; a version it
            # never published names no licence.
            "https://www.gnu.org/licenses/gpl-2.0.html",
            "https://www.gnu.org/licenses/old-licenses/gpl-3.0.html",
            "https://www.gnu.org/licenses/gpl-9.9.html",
            "https://opensource.org/licenses/MIT",
            "https://opensource.org/license/faq",
            # OSI serves a licence's page under its SPDX identifier too, but names the lowercase slug as canonical.
            "https://opensource.org/license/MIT",
            "https://opensource.org/license/Apache-2.0",
            # OSI publishes no page for an Open Data Commons licence; its SPDX entry is its address.
            "https://opensource.org/license/ODbL-1.0",
            "https://spdx.org/licenses/MIT.html",
            "https://spdx.org/licenses/MIT.HTML",
            # A Creative Commons licence is recorded at Creative Commons, not under its SPDX identifier.
            "https://spdx.org/licenses/CC-BY-4.0",
            # A licence the Guide has not reviewed is added to the list first.
            "https://spdx.org/licenses/ISC",
        )
        for value in refused:
            self.edit("resources.toml", f'license = "{licence}"', f'license = "{value}"')
            self.assertError("license is the canonical HTTPS address of a known licence or mark")
            self.edit("resources.toml", f'license = "{value}"', f'license = "{licence}"')
        accepted = (
            "https://creativecommons.org/licenses/by/3.0/cz/",
            "https://creativecommons.org/licenses/by/3.0/igo/",
            "https://creativecommons.org/licenses/by/2.5/scotland/",
            "https://creativecommons.org/licenses/by/2.1/jp/",
            "https://creativecommons.org/licenses/by/1.0/",
            "https://creativecommons.org/licenses/by-nd-nc/1.0/",
            "https://creativecommons.org/licenses/by-nd-nc/1.0/fi/",
            "https://creativecommons.org/licenses/by-nc-nd/2.0/",
            "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            "https://creativecommons.org/publicdomain/zero/1.0/",
            "https://www.gnu.org/licenses/gpl-3.0.html",
            "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
            "https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html",
            "https://www.gnu.org/licenses/fdl-1.3.html",
            "https://opensource.org/license/mit",
            "https://opensource.org/license/apache-2-0",
            "https://spdx.org/licenses/Apache-2.0",
            "https://spdx.org/licenses/ODbL-1.0",
        )
        for value in accepted:
            self.edit("resources.toml", f'license = "{licence}"', f'license = "{value}"')
            self.assertEqual(self.errors(), [], value)
            self.edit("resources.toml", f'license = "{value}"', f'license = "{licence}"')
        self.assertEqual(self.errors(), [])

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

    def test_topic_target_names_known_facets_and_values(self) -> None:
        self.edit(
            "stations/01-one.toml", 'href = "#check-gate"', 'href = "#resources?type=service,document&station=one"'
        )
        self.assertEqual(self.errors(), [])
        self.edit("stations/01-one.toml", "type=service,document&station=one", "type=service,ghost")
        self.assertError("unknown type value(s) ghost for #resources")
        self.edit("stations/01-one.toml", "#resources?type=service,ghost", "#resources?colour=red")
        self.assertError("unknown facet 'colour' for #resources")
        self.edit("stations/01-one.toml", "#resources?colour=red", "#tests?type=service")
        self.assertError("'#tests' takes no topic")
        self.edit("stations/01-one.toml", "#tests?type=service", "#repositories?function=")
        self.assertError("unknown function value(s) (none) for #repositories")

    def test_lifecycle_models_hold_together(self) -> None:
        self.add_lifecycles()
        self.assertEqual(self.errors(), [])

    def test_lifecycle_definition_is_quoted_never_translated(self) -> None:
        self.add_lifecycles()
        self.edit(
            "lifecycle/2-other.toml", '"Funding the work."', '{ cs = "Financování práce.", en = "Funding the work." }'
        )
        self.assertError("lifecycle:other.fund: definition is a text, as a string")

    def test_path_stage_definition_reads_the_same_in_both_languages(self) -> None:
        self.add_lifecycles()
        self.edit("lifecycle/1-path.toml", 'translation = "Plánování dat."', 'translation = "Plánování. Dat."')
        self.assertError("the translation does not render the definition sentence for sentence")
        self.edit("lifecycle/1-path.toml", 'translation = "Plánování. Dat."\n', "")
        self.assertError("a path stage carries the Průvodce's Czech translation of its definition")
        self.edit("lifecycle/2-other.toml", 'locator = "p. 2"', 'translation = "Financování práce."\nlocator = "p. 2"')
        self.assertError("only the path's stages are translated")

    def test_quoted_czech_definition_keeps_its_label(self) -> None:
        self.add_lifecycles()
        self.edit("lifecycle/1-path.toml", 'source = "report"\n', 'source = "report"\nczechSource = "report"\n')
        self.edit("lifecycle/1-path.toml", 'locator = "p. 1"', 'czechDefinition = "plánování dat."\nlocator = "p. 1"')
        self.assertError("the quoted Czech definition keeps its stage label ('Plánování: …')")
        self.edit("lifecycle/1-path.toml", '"plánování dat."', '"Plánování: plánování dat."')
        self.assertEqual(self.errors(), [])

    def test_lifecycle_czech_definition_comes_from_the_czech_source(self) -> None:
        self.add_lifecycles()
        self.edit(
            "lifecycle/2-other.toml", 'locator = "p. 2"', 'czechDefinition = "Financování práce."\nlocator = "p. 2"'
        )
        self.assertError("a Czech definition is quoted from the model's czechSource")

    def test_correspondence_links_the_path_to_another_model(self) -> None:
        self.add_lifecycles()
        self.edit("lifecycle/crosswalk.toml", '"other.fund"]', '"other.ghost"]')
        self.assertError("a correspondence names two known stages")
        self.edit("lifecycle/crosswalk.toml", '["rdmkit.plan", "other.ghost"]', '["other.fund", "other.fund"]')
        self.assertError("links a stage of 'rdmkit' to a stage of another model")

    def test_correspondence_states_its_basis(self) -> None:
        self.add_lifecycles()
        self.edit("lifecycle/crosswalk.toml", 'locator = "Figure 1"\n', "")
        self.assertError("a published correspondence cites its source and where it is published")
        self.edit("lifecycle/crosswalk.toml", 'basis = "published"', 'basis = "reviewed"')
        self.assertError("crosswalk:rdmkit-plan-other-fund: missing note")
        self.edit("lifecycle/crosswalk.toml", 'basis = "reviewed"', 'basis = "assumed"')
        self.assertError("basis must be one of published, reviewed, unconfirmed")

    def test_every_path_stage_corresponds_to_each_model(self) -> None:
        self.add_lifecycles()
        (self.root / "content" / "lifecycle" / "crosswalk.toml").write_text("", encoding="utf-8")
        self.assertError("lifecycle:rdmkit.plan: corresponds to no stage of other")

    def test_station_stage_is_a_path_stage(self) -> None:
        self.add_lifecycles()
        self.edit("stations/01-one.toml", 'lifecycleStage = "plan"', 'lifecycleStage = "fund"')
        self.assertError("station:one: lifecycleStage names no stage of 'rdmkit'")

    def test_every_path_stage_holds_a_step(self) -> None:
        self.add_lifecycles()
        self.edit("stations/01-one.toml", 'lifecycleStage = "plan"\n', "")
        self.assertError("lifecycle:rdmkit.plan: the stage holds no step of the path")

    def test_steps_follow_the_life_cycle(self) -> None:
        content = build_crate.load_content()
        stations = {data["station"]["id"]: data["station"] for data in content["stations"]}
        stations["collect"]["lifecycleStage"], stations["analyse"]["lifecycleStage"] = "analyse", "collect"
        del stations["process"]["lifecycleStage"]
        errors = check_content.check(content, build_crate.ROOT).errors
        self.assertTrue(any("station:analyse: the steps follow the order" in error for error in errors), errors)
        self.assertTrue(any("station:process: every step belongs to a stage" in error for error in errors))
        self.assertFalse(any("station:assessment" in error for error in errors))

    def test_lifecycle_change_needs_provenance(self) -> None:
        self.add_lifecycles()
        self.edit("provenance.toml", ', "crosswalk:*"]', "]")
        self.assertError("crosswalk:rdmkit-plan-other-fund: no provenance action covers this item")

    def test_the_guide_is_named_with_a_capital_letter(self) -> None:
        self.edit(
            "stations/01-one.toml",
            'text = { cs = "Postup.", en = "Steps." }',
            'text = { cs = "Postup průvodce.", en = "Steps of the guide." }',
        )
        self.assertError("name the Guide with a capital letter: 'průvodce'")
        self.assertError("name the Guide with a capital letter: 'the guide'")
        self.edit("stations/01-one.toml", '"Postup průvodce."', '"Vyberte s průvodcem licencemi."')
        self.edit("stations/01-one.toml", '"Steps of the guide."', '"Steps of the Guide."')
        self.assertError("name the Guide with a capital letter: 'průvodcem'")
        self.edit(
            "guide.toml",
            'version = "0.0.1"\n',
            'version = "0.0.1"\ngenericGuideUses = ["průvodcem licencemi"]\n',
        )
        self.assertFalse(any("D-177" in error for error in self.errors()))

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

    def test_provenance_can_name_glossary_terms(self) -> None:
        content = build_crate.load_content(self.root / "content")
        content["glossary"] = {"term": [{"id": "87"}]}
        self.assertEqual(check_content.content_index(content)["term:87"], "term")
        self.assertTrue(check_content.covered("term:*", "term:87"))

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
        # A tools page names its group, so the tools view can show tools and guidance apart (D-185).
        self.assertError("a tools page names its group")
        grouped = described + 'group = "guidance"\n'
        pages.write_text('[[page]]\nid = "tool"\nmenu = "tools"\n' + grouped + title, encoding="utf-8")
        self.edit("provenance.toml", '"test:test_one"]', '"test:test_one", "page:tool"]')
        self.assertFalse(any(error.startswith("page:") for error in self.errors()), self.errors())

    def test_base_url_must_use_https(self) -> None:
        self.edit("guide.toml", 'baseUrl = "https://example.org/guide/"', 'baseUrl = "http://example.org/guide/"')
        with self.assertRaisesRegex(build_crate.ContentError, "the guide's address must use HTTPS"):
            build_crate.load_content(self.root / "content")

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
alternateIds = [{ scheme = "fip-dashboard", value = "org1" }]
id = "org1"
name = { cs = "Organizace", en = "Organisation" }

[[resource]]
alternateIds = [{ scheme = "fip-dashboard", value = "r1" }]
id = "r1"
name = "Resource one"
type = "identifier-service"
description = { cs = "Zdroj.", en = "Resource." }
principles = ["F1"]
verification = [{ verifier = "org1", level = "verified", date = "2026-01-01" }]

[[fip]]
alternateIds = [{ scheme = "fip-dashboard", value = "fip1" }]
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
        (inputs / "re3data-list.xml").write_text(
            "<list><repository><id>r3d1</id><doi>https://doi.org/10.17616/R3AB12</doi></repository></list>"
        )
        (inputs / "re3data-r3d1.xml").write_text(
            '<r3d:re3data xmlns:r3d="http://www.re3data.org/schema/2-2"><r3d:repository>'
            "<r3d:repositoryName>Old</r3d:repositoryName><r3d:repositoryURL>http://old.example.org/</r3d:repositoryURL>"
            "<r3d:type>disciplinary</r3d:type><r3d:pidSystem>DOI</r3d:pidSystem>"
            '<r3d:api apiType="OAI-PMH">https://old.example.org/oai</r3d:api><r3d:api apiType="other">x</r3d:api>'
            "<r3d:dataLicense><r3d:dataLicenseName>CC</r3d:dataLicenseName></r3d:dataLicense>"
            "<r3d:certificate>CoreTrustSeal</r3d:certificate><r3d:certificate>other</r3d:certificate>"
            "<r3d:versioning>yes</r3d:versioning></r3d:repository></r3d:re3data>"
        )
        outcome = refresh_snapshots.refresh("re3data", refresh_snapshots.Fetcher(inputs), "2026-01-01", self.root)
        self.assertEqual(outcome.status, "changed", outcome.reason)
        self.append("guide.toml", '\n[[repositoryKind]]\nid = "domain"\nname = { cs = "oborový", en = "domain" }\n')
        snapshot = (self.root / "content" / "snapshots" / "re3data.toml").read_text(encoding="utf-8")
        self.assertIn('url = "https://www.re3data.org/repository/r3d1"', snapshot)
        self.assertIn('kind = "domain"', snapshot)
        self.assertIn('apis = ["OAI-PMH"]', snapshot)
        self.assertIn('certificates = ["CoreTrustSeal"]', snapshot)
        self.assertIn("versioning = true", snapshot)
        self.assertIn('doi = "10.17616/R3AB12"', snapshot)
        self.assertEqual(self.errors(), [])
        facts = build_crate.page_config(build_crate.load_content(self.root / "content"))["config"]["re3data"]["r3d1"]
        self.assertEqual(facts["name"], "Old")
        self.assertEqual(facts["dataLicenses"], ["CC"])
        self.assertEqual(facts["date"], "2026-01-01")
        self.assertEqual(facts["doi"], "10.17616/R3AB12")
        # DataCite finds the repository by the record's DOI, which the crate keeps as the record's other identifier.
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"))
        entity = next(item for item in crate["@graph"] if item.get("catalogueAddress") == "repo/dom/old")
        self.assertIn({"@id": "https://doi.org/10.17616/R3AB12"}, entity["sameAs"])
        # A DOI that is not re3data's is refused, and the snapshot stays as it was.
        (inputs / "re3data-list.xml").write_text(
            "<list><repository><id>r3d1</id><doi>https://doi.org/10.1234/other</doi></repository></list>"
        )
        rejected = refresh_snapshots.refresh("re3data", refresh_snapshots.Fetcher(inputs), "2026-01-02", self.root)
        self.assertEqual(rejected.status, "rejected")
        self.assertIn("not a re3data DOI", rejected.reason)

    def test_re3data_keeps_the_names_it_tags_as_czech(self) -> None:
        inputs = Path(self.temp.name) / "inputs"
        inputs.mkdir()
        (inputs / "re3data-list.xml").write_text("<list><repository><id>r3d1</id></repository></list>")
        (inputs / "re3data-r3d1.xml").write_text(
            '<r3d:re3data xmlns:r3d="http://www.re3data.org/schema/2-2"><r3d:repository>'
            '<r3d:repositoryName language="eng">Czech National Corpus</r3d:repositoryName>'
            '<r3d:additionalName language="eng">CNC</r3d:additionalName>'
            '<r3d:additionalName language="ces">CNK</r3d:additionalName>'
            '<r3d:additionalName language="ces">Český národní korpus</r3d:additionalName>'
            '<r3d:additionalName language="ces">CNK</r3d:additionalName>'
            "<r3d:repositoryURL>https://korpus.example.org/</r3d:repositoryURL></r3d:repository></r3d:re3data>",
            encoding="utf-8",
        )
        outcome = refresh_snapshots.refresh("re3data", refresh_snapshots.Fetcher(inputs), "2026-01-01", self.root)
        self.assertEqual(outcome.status, "changed", outcome.reason)
        snapshot = (self.root / "content" / "snapshots" / "re3data.toml").read_text(encoding="utf-8")
        self.assertIn('name = "Czech National Corpus"', snapshot)
        self.assertIn('namesCs = ["CNK", "Český národní korpus"]', snapshot)

    def test_re3data_adds_reviewed_czech_hosted_repositories(self) -> None:
        inputs = Path(self.temp.name) / "inputs"
        inputs.mkdir()
        record = (
            '<r3d:re3data xmlns:r3d="http://www.re3data.org/schema/2-2"><r3d:repository>'
            "<r3d:repositoryName>{name}</r3d:repositoryName><r3d:repositoryURL>https://{name}.example.org/</r3d:repositoryURL>"
            "</r3d:repository></r3d:re3data>"
        )
        (inputs / "re3data-list.xml").write_text("<list><repository><id>r3d1</id></repository></list>")
        (inputs / "re3data-r3d1.xml").write_text(record.format(name="listed"))
        (inputs / "re3data-r3d2.xml").write_text(record.format(name="hosted"))
        repositories = self.root / "content" / "repositories.toml"
        repositories.write_text(
            '[[re3dataInclude]]\nre3data = "r3d2"\nreason = "Hosted in the Czech Republic."\n', encoding="utf-8"
        )
        outcome = refresh_snapshots.refresh("re3data", refresh_snapshots.Fetcher(inputs), "2026-01-01", self.root)
        self.assertEqual(outcome.status, "changed", outcome.reason)
        snapshot = (self.root / "content" / "snapshots" / "re3data.toml").read_text(encoding="utf-8")
        blocks = {
            tomllib.loads("[[repository]]" + block)["repository"][0]["alternateIds"][0]["value"]: block
            for block in snapshot.split("[[repository]]")[1:]
        }
        self.assertEqual(sorted(blocks), ["r3d1", "r3d2"])
        self.assertIn(refresh_snapshots.INCLUSION_NOTE, blocks["r3d2"])
        self.assertNotIn(refresh_snapshots.INCLUSION_NOTE, blocks["r3d1"])
        repositories.write_text(repositories.read_text(encoding="utf-8").replace('"r3d2"', '"ELI"'), encoding="utf-8")
        rejected = refresh_snapshots.refresh("re3data", refresh_snapshots.Fetcher(inputs), "2026-01-02", self.root)
        self.assertEqual(rejected.status, "rejected")
        self.assertIn("reviewed re3data inclusion", rejected.reason)


class SnapshotRefreshTests(FixtureCase):
    """A refresh replaces a snapshot only with a complete, plausible response, atomically; otherwise it stays."""

    def setUp(self) -> None:
        super().setUp()
        self.inputs = Path(self.temp.name) / "inputs"
        self.inputs.mkdir()

    def put(self, name: str, value: object) -> None:
        text = value if isinstance(value, str) else json.dumps(value)
        (self.inputs / name).write_text(text, encoding="utf-8")

    def refresh(self, name: str, today: str = "2026-02-01") -> refresh_snapshots.Outcome:
        return refresh_snapshots.refresh(name, refresh_snapshots.Fetcher(self.inputs), today, self.root)

    def knav_inputs(self, **changes: object) -> None:
        """The catalogue's last commit and two tools, one with a plain-HTTP address; `changes` alter the first."""
        lifecycle = self.root / "content" / "lifecycle"
        lifecycle.mkdir(exist_ok=True)
        (lifecycle / "3-knav-tools.toml").write_text(
            '[lifecycle]\nid = "knav-tools"\n\n[[stage]]\nid = "planning"\n\n[[stage]]\nid = "storing-archiving"\n',
            encoding="utf-8",
        )
        self.put(
            "knav-tools-commit.json", [{"sha": "a" * 40, "commit": {"committer": {"date": "2026-03-28T19:46:46Z"}}}]
        )
        first = {"id_name": "dmp", "full_name": "A DMP tool", "lifecycle_step": ["planning"], "icon": ["user.svg"]}
        first |= {"desc_short": "Plans data.", "link": "https://dmp.example.org/"} | changes
        second = {"id_name": "archive", "full_name": "An archive", "lifecycle_step": ["storing_archiving"]}
        second |= {"icon": ["infinity.svg"], "desc_short": "Keeps data.", "link": "http://archive.example.org/"}
        self.put("knav-tools.json", [first, second])

    def listed_repositories(self) -> None:
        """Two listed repositories: a curated one with an address only, and one from the re3data snapshot with its
        re3data record and that record's DOI."""
        (self.root / "content" / "repositories.toml").write_text(
            '[[repository]]\nid = "local"\nname = "Local repository"\nurl = "https://data.example.org/"\n',
            encoding="utf-8",
        )
        (self.root / "content" / "snapshots").mkdir(exist_ok=True)
        (self.root / "content" / "snapshots" / "re3data.toml").write_text(
            '[snapshot]\nsource = "re3data"\nurl = "https://www.re3data.org/"\nretrieved = 2026-01-01\n\n'
            '[[repository]]\nalternateIds = [{ scheme = "re3data", value = "r3d100000002" }]\nid = "r3d100000002"\n'
            'name = "Registered repository"\nurl = "https://registered.example.org"\n'
            're3data = "r3d100000002"\ndoi = "10.17616/R3AB12"\n',
            encoding="utf-8",
        )

    def test_repository_names_keep_their_czech_form_and_abbreviations(self) -> None:
        (self.root / "content" / "snapshots").mkdir(exist_ok=True)
        (self.root / "content" / "snapshots" / "re3data.toml").write_text(
            '[snapshot]\nsource = "re3data"\nurl = "https://www.re3data.org/"\nretrieved = 2026-01-01\n\n'
            '[[repository]]\nalternateIds = [{ scheme = "re3data", value = "r3d100000002" }]\n'
            'id = "r3d100000002"\nname = "Czech Archive"\nnamesCs = ["Český archiv"]\n'
            'url = "https://archive.example.org"\nre3data = "r3d100000002"\n\n'
            '[[repository]]\nalternateIds = [{ scheme = "re3data", value = "r3d100000003" }]\n'
            'id = "r3d100000003"\nname = "Other Archive"\nnamesCs = ["Jiný archiv"]\n'
            'url = "https://other.example.org"\nre3data = "r3d100000003"\n',
            encoding="utf-8",
        )
        record = '[[record]]\nre3data = "r3d100000002"\n{fields}evidence = ["https://archive.example.org/about"]\n'
        path = self.root / "content" / "repositories.toml"
        path.write_text(record.format(fields='name = "Czech Archive"\n'), encoding="utf-8")
        self.assertError("re3data gives a Czech name (Český archiv); give the name as a table with its Czech form")
        path.write_text(
            record.format(fields='name = { cs = "Český archiv", en = "Czech Archive" }\nabbreviation = "ČA"\n'),
            encoding="utf-8",
        )
        self.assertError("an abbreviation is a table of its forms by language")
        path.write_text(
            record.format(
                fields='name = { cs = "Český archiv", en = "Czech Archive" }\nabbreviation = { cs = "ČA", en = "CA" }\n'
            ),
            encoding="utf-8",
        )
        self.assertEqual(self.errors(), [])
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"))
        entities = {item["@id"]: item for item in crate["@graph"]}
        corrected = entities["#repository-r3d100000002"]
        self.assertEqual(
            corrected["abbreviation"], [{"@value": "ČA", "@language": "cs"}, {"@value": "CA", "@language": "en"}]
        )
        self.assertIn({"@value": "Český archiv", "@language": "cs"}, corrected["name"])
        # Without a curated name, the name re3data tags as Czech serves Czech readers.
        self.assertEqual(
            entities["#repository-r3d100000003"]["name"],
            [{"@value": "Jiný archiv", "@language": "cs"}, {"@value": "Other Archive", "@language": "en"}],
        )

    @staticmethod
    def fairsharing_record(doi: str, *related: str) -> dict[str, object]:
        return {
            "id": doi.lower(),
            "attributes": {
                "doi": doi.lower(),
                "titles": [{"title": "FAIRsharing record for: A repository"}],
                "relatedIdentifiers": [{"relatedIdentifier": value} for value in related],
            },
        }

    def test_fairsharing_records_join_listed_repositories_by_re3data_record_or_address(self) -> None:
        self.listed_repositories()
        self.put(
            "fairsharing-0.json",
            {
                "data": [
                    self.fairsharing_record(
                        "10.25504/FAIRsharing.abc123", "https://www.re3data.org/repository/r3d100000002"
                    ),
                    self.fairsharing_record("10.25504/FAIRsharing.def456", "http://www.data.example.org"),
                ]
            },
        )
        outcome = self.refresh("fairsharing")
        self.assertEqual((outcome.status, outcome.counts), ("changed", {"annotation": 2}), outcome.reason)
        data = tomllib.loads((self.root / "content" / "snapshots" / "fairsharing.toml").read_text(encoding="utf-8"))
        rows = {row.get("re3data") or row.get("url"): row for row in data["annotation"]}
        # DataCite answers in lower case; the snapshot keeps FAIRsharing's own spelling and the record's name.
        self.assertEqual(rows["r3d100000002"]["fairsharing"], "10.25504/FAIRsharing.abc123")
        self.assertEqual(rows["https://data.example.org/"]["fairsharing"], "10.25504/FAIRsharing.def456")
        self.assertEqual(rows["r3d100000002"]["fairsharingName"], "A repository")

    def test_fairsharing_refuses_foreign_records_and_an_unread_second_page(self) -> None:
        self.listed_repositories()
        self.put(
            "fairsharing-0.json", {"data": [self.fairsharing_record("10.5281/zenodo.1", "https://data.example.org")]}
        )
        self.assertEqual(self.refresh("fairsharing").status, "rejected")
        record = self.fairsharing_record("10.25504/FAIRsharing.abc123", "https://data.example.org")
        self.put("fairsharing-0.json", {"data": [record] * refresh_snapshots.DATACITE_PAGE})
        self.assertEqual(self.refresh("fairsharing").status, "rejected")
        self.assertFalse((self.root / "content" / "snapshots" / "fairsharing.toml").exists())

    def test_datacite_names_a_repository_only_when_one_datacite_repository_claims_its_record(self) -> None:
        self.listed_repositories()
        self.put("datacite-r3d100000002.json", {"data": [{"id": "member.one"}, {"id": "member.two"}]})
        self.assertEqual(self.refresh("datacite").status, "empty")
        self.put("datacite-r3d100000002.json", {"data": [{"id": "member.repo"}]})
        outcome = self.refresh("datacite")
        self.assertEqual((outcome.status, outcome.counts), ("changed", {"annotation": 1}), outcome.reason)
        data = tomllib.loads((self.root / "content" / "snapshots" / "datacite.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["annotation"], [{"re3data": "r3d100000002", "datacite": "member.repo"}])

    def test_annotations_and_nkr_records_join_the_catalogue_at_build_time(self) -> None:
        self.listed_repositories()
        snapshots = self.root / "content" / "snapshots"
        (snapshots / "fairsharing.toml").write_text(
            '[snapshot]\nsource = "FAIRsharing"\nurl = "https://fairsharing.org/"\nretrieved = 2026-01-02\n\n'
            '[[annotation]]\nre3data = "r3d100000002"\n'
            'fairsharing = "10.25504/FAIRsharing.abc123"\nfairsharingName = "R"\n\n'
            '[[annotation]]\nurl = "https://unlisted.example.org/"\nfairsharing = "10.25504/FAIRsharing.zzz999"\n',
            encoding="utf-8",
        )
        (snapshots / "datacite.toml").write_text(
            '[snapshot]\nsource = "DataCite"\nurl = "https://datacite.org/"\nretrieved = 2026-01-02\n\n'
            '[[annotation]]\nurl = "https://data.example.org"\ndatacite = "member.repo"\n',
            encoding="utf-8",
        )
        (snapshots / "nkr.toml").write_text(
            '[snapshot]\nsource = "NKR"\nurl = "https://repo.cz/"\nretrieved = 2026-01-02\n'
            'fields = ["repositoryName", "mainUrl", "type"]\n\n'
            '[[record]]\nalternateIds = [{ scheme = "nkr", value = "21.T15999/abc" }]\n'
            'id = "national-repository"\nurl = "https://repo.cz/objects/21.T15999/abc"\n'
            'repositoryName = "National repository"\nmainUrl = "https://national.example.org/"\n'
            'type = "institutional"\n',
            encoding="utf-8",
        )
        content = build_crate.load_content(self.root / "content")
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
        repositories = {
            entity["@id"]: entity for entity in graph.entities.values() if entity.get("@type") == "DataCatalog"
        }

        def same_as(entity: dict[str, object]) -> list[str]:
            return [item["@id"] for item in build_crate.as_list(entity.get("sameAs"))]

        def sources(entity: dict[str, object]) -> list[str]:
            return [item["@id"] for item in build_crate.as_list(entity.get("isBasedOn"))]

        registered = repositories["#repository-r3d100000002"]
        self.assertIn("https://doi.org/10.25504/FAIRsharing.abc123", same_as(registered))
        self.assertIn("#snapshot-fairsharing", sources(registered))
        datacite_values = {
            entity["value"]
            for entity in graph.entities.values()
            if entity.get("@type") == "PropertyValue" and entity.get("propertyID") == "datacite"
        }
        self.assertIn("member.repo", datacite_values)
        self.assertNotIn("dataciteRepository", repositories["#repository-local"])
        self.assertIn("#snapshot-datacite", sources(repositories["#repository-local"]))
        # An annotation naming no listed repository adds none; an NKR record becomes a repository with NKR's address.
        self.assertFalse(any("zzz999" in value for entity in repositories.values() for value in same_as(entity)))
        national = next(
            entity for entity in repositories.values() if "https://repo.cz/objects/21.T15999/abc" in same_as(entity)
        )
        self.assertIn("#snapshot-nkr", sources(national))
        self.assertEqual(build_crate.nkr_config(content["snapshots"])["records"][0]["content"]["type"], "institutional")

    def test_knav_catalogue_becomes_a_snapshot_with_steps_and_disciplines(self) -> None:
        self.knav_inputs()
        outcome = self.refresh("knav-tools")
        self.assertEqual((outcome.status, outcome.counts), ("changed", {"tool": 2}), outcome.reason)
        data = tomllib.loads((self.root / "content" / "snapshots" / "knav-tools.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["snapshot"]["datasetVersion"], "a" * 40)
        self.assertEqual(data["snapshot"]["license"], refresh_snapshots.KNAV_LICENSE)
        tools = {tool["id"]: tool for tool in data["tool"]}
        self.assertEqual(tools["archive"]["steps"], ["storing-archiving"])
        self.assertEqual(tools["dmp"]["disciplines"], ["social-sciences-humanities"])
        # The guide links only over HTTPS: a plain-HTTP address is kept as data, never as the tool's URL.
        self.assertNotIn("url", tools["archive"])
        self.assertEqual(tools["archive"]["httpUrl"], "http://archive.example.org/")

    def test_knav_catalogue_that_changed_shape_is_rejected(self) -> None:
        for changes, reason in (
            ({"lifecycle_step": ["publishing"]}, "names unknown or no steps"),
            ({"icon": ["planet.svg"]}, "unknown discipline group"),
            ({"id_name": "Bad Id"}, "no lower-case id_name"),
            ({"id_name": "archive"}, "two tools are named archive"),
            ({"link": "ftp://dmp.example.org/"}, "no web address"),
        ):
            with self.subTest(reason):
                self.knav_inputs(**changes)
                outcome = self.refresh("knav-tools")
                self.assertEqual(outcome.status, "rejected")
                self.assertIn(reason, outcome.reason)
        self.assertFalse((self.root / "content" / "snapshots" / "knav-tools.toml").exists())

    def re3data_inputs(self, count: int) -> None:
        ids = [f"r3d1000000{n:02}" for n in range(count)]
        self.put(
            "re3data-list.xml", "<list>" + "".join(f"<repository><id>{i}</id></repository>" for i in ids) + "</list>"
        )
        for repository_id in ids:
            self.put(
                f"re3data-{repository_id}.xml",
                '<r3d:re3data xmlns:r3d="http://www.re3data.org/schema/2-2"><r3d:repository>'
                f"<r3d:repositoryName>Repository {repository_id}</r3d:repositoryName>"
                "<r3d:repositoryURL>https://repository.example.org/</r3d:repositoryURL></r3d:repository></r3d:re3data>",
            )

    def test_heslar_definitions_keep_their_language_and_licence_without_html(self) -> None:
        self.put(
            "heslar.json",
            {
                "data": [
                    {
                        "id": 1,
                        "termin_cs": "data",
                        "termin_en": "data",
                        "popis_cs": "<p>První <strong>odstavec</strong> &amp; text.</p>"
                        '<script>fetch("https://evil.example")</script>'
                        '<p>Druhý <a href="https://example.org">odstavec</a>.</p>',
                    }
                ]
            },
        )
        self.assertEqual(self.refresh("heslar").status, "changed")
        glossary = tomllib.loads((self.root / "content/glossary.toml").read_text(encoding="utf-8"))
        self.assertEqual(glossary["glossary"]["license"], refresh_snapshots.HESLAR_LICENSE)
        self.assertEqual(glossary["term"][0]["definition"], "První odstavec & text.\n\nDruhý odstavec.")
        self.assertEqual(glossary["term"][0]["definitionLanguage"], "cs")
        self.assertEqual(glossary["term"][0]["url"], "https://heslar.openscience.cz/heslo.php?id=1")

    def test_heslar_missing_definition_does_not_invent_one(self) -> None:
        self.put("heslar.json", {"data": [{"id": 1, "termin_cs": "data", "termin_en": "data"}]})
        self.assertEqual(self.refresh("heslar").status, "changed")
        glossary = tomllib.loads((self.root / "content/glossary.toml").read_text(encoding="utf-8"))
        self.assertNotIn("definition", glossary["term"][0])

    def test_an_empty_successful_response_keeps_the_snapshot(self) -> None:
        self.put("heslar.json", {"data": [{"id": 1, "termin_cs": "data", "termin_en": "data"}]})
        self.assertEqual(self.refresh("heslar").status, "changed")
        glossary = (self.root / "content/glossary.toml").read_bytes()
        self.put("heslar.json", {"data": []})
        outcome = self.refresh("heslar")
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("no term records", outcome.reason)
        self.assertEqual((self.root / "content/glossary.toml").read_bytes(), glossary)
        for broken in ("[]", '{"data": [{"termin_cs": "x"}]}', "not json"):
            self.put("heslar.json", broken)
            self.assertEqual(self.refresh("heslar").status, "rejected", broken)
        self.assertEqual((self.root / "content/glossary.toml").read_bytes(), glossary)

    def test_an_implausible_removal_is_rejected_and_a_reviewed_one_accepted(self) -> None:
        self.re3data_inputs(4)
        self.assertEqual(self.refresh("re3data").status, "changed")
        path = self.root / "content/snapshots/re3data.toml"
        before = path.read_bytes()
        self.re3data_inputs(2)
        outcome = self.refresh("re3data")
        self.assertEqual((outcome.status, outcome.previous), ("rejected", {}))
        self.assertIn("2 of 4 repository records would remain", outcome.reason)
        self.assertEqual(path.read_bytes(), before)
        (self.inputs / "re3data-list.xml").unlink()
        self.re3data_inputs(3)
        self.assertEqual(self.refresh("re3data").status, "changed", "a quarter may go")

    def test_reserved_identifier_prevents_a_new_snapshot_from_reusing_a_curated_id(self) -> None:
        self.put(
            "re3data-list.xml",
            "<list><repository><id>r3d100000099</id></repository></list>",
        )
        self.put(
            "re3data-r3d100000099.xml",
            '<r3d:re3data xmlns:r3d="http://www.re3data.org/schema/2-2"><r3d:repository>'
            "<r3d:repositoryName>Service repository</r3d:repositoryName>"
            "<r3d:repositoryURL>https://service.example.org/</r3d:repositoryURL></r3d:repository></r3d:re3data>",
        )
        outcome = self.refresh("re3data")
        self.assertEqual(outcome.status, "changed", outcome.reason)
        data = tomllib.loads((self.root / "content" / "snapshots" / "re3data.toml").read_text(encoding="utf-8"))
        self.assertIn("service-2", [row["id"] for row in data["repository"]])
        self.assertNotIn("service", [row["id"] for row in data["repository"]])

    def test_identity_collision_that_needs_review_is_rejected(self) -> None:
        self.re3data_inputs(1)
        self.assertEqual(self.refresh("re3data").status, "changed")
        target = self.root / "content" / "snapshots" / "re3data.toml"
        before = target.read_bytes()
        self.re3data_inputs(2)
        with mock.patch.object(
            refresh_snapshots, "preserve_snapshot", side_effect=ValueError("ambiguous Guide identity")
        ):
            outcome = self.refresh("re3data")
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("identity needs review", outcome.reason)
        self.assertEqual(target.read_bytes(), before)

    def test_refresh_reserves_central_and_snapshot_retired_identifiers(self) -> None:
        self.edit("resources.toml", 'id = "service"', 'id = "curated-service"')
        (self.root / "content" / "identifiers.toml").write_text(
            '[retired]\nresources = ["service"]\n', encoding="utf-8"
        )
        retired = self.root / "content" / "snapshots" / "retired.toml"
        retired.parent.mkdir(exist_ok=True)
        retired.write_text('[identity]\nretiredIds = ["service-2"]\n', encoding="utf-8")
        target = self.root / "content" / "snapshots" / "re3data.toml"
        reserved = refresh_snapshots.reserved_identifiers(self.root, target)
        self.assertTrue({"service", "service-2"} <= reserved)
        self.put("re3data-list.xml", "<list><repository><id>r3d100000099</id></repository></list>")
        self.put(
            "re3data-r3d100000099.xml",
            '<r3d:re3data xmlns:r3d="http://www.re3data.org/schema/2-2"><r3d:repository>'
            "<r3d:repositoryName>Service repository</r3d:repositoryName>"
            "<r3d:repositoryURL>https://service.example.org/</r3d:repositoryURL></r3d:repository></r3d:re3data>",
        )
        outcome = self.refresh("re3data")
        self.assertEqual(outcome.status, "changed", outcome.reason)
        rows = tomllib.loads(target.read_text(encoding="utf-8"))["repository"]
        self.assertEqual(rows[0]["id"], "service-3")

    def test_identical_data_changes_nothing_not_even_the_date(self) -> None:
        self.re3data_inputs(2)
        self.refresh("re3data", "2026-02-01")
        path = self.root / "content/snapshots/re3data.toml"
        before = path.read_bytes()
        outcome = self.refresh("re3data", "2026-03-01")
        self.assertEqual(outcome.status, "unchanged")
        self.assertEqual(path.read_bytes(), before)

    def test_a_failed_write_leaves_the_old_snapshot_and_no_partial_file(self) -> None:
        self.re3data_inputs(2)
        self.refresh("re3data", "2026-02-01")
        path = self.root / "content/snapshots/re3data.toml"
        before = path.read_bytes()
        self.re3data_inputs(3)
        (self.inputs / "re3data-r3d100000002.xml").write_text(
            '<r3d:re3data xmlns:r3d="http://www.re3data.org/schema/2-2"><r3d:repository>'
            "<r3d:repositoryName>Third repository</r3d:repositoryName>"
            "<r3d:repositoryURL>https://third.example.org/</r3d:repositoryURL></r3d:repository></r3d:re3data>",
            encoding="utf-8",
        )
        with mock.patch.object(refresh_snapshots.os, "replace", side_effect=OSError("disk full")):
            self.assertEqual(self.refresh("re3data").status, "failed")
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual([item.name for item in path.parent.iterdir()], ["re3data.toml"])

    def test_an_oversized_response_is_rejected(self) -> None:
        self.put("heslar.json", {"data": [{"id": n, "termin_cs": "x", "termin_en": "x"} for n in range(50)]})
        with mock.patch.object(refresh_snapshots, "MAX_RESPONSE_BYTES", 100):
            outcome = self.refresh("heslar")
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("exceeds 100 bytes", outcome.reason)
        self.assertFalse((self.root / "content/glossary.toml").exists())

    def test_dashboard_collections_are_replaced_together_or_not_at_all(self) -> None:
        self.put("fip-dashboard-meta.json", {"name": {"cs": "D", "en": "D"}, "version": "1"})
        self.put("fip-dashboard-resource-types.json", [{"id": "registry", "label": {"cs": "r", "en": "r"}}])
        self.put("fip-dashboard-organizations.json", [{"id": "org", "name": {"cs": "O", "en": "O"}}])
        self.put("fip-dashboard-resources.json", [{"id": "res", "name": "Res", "type": "registry"}])
        self.put(
            "fip-dashboard-fips.json", [{"id": "fip", "declarations": [{"resource": "missing", "principle": "F1"}]}]
        )
        outcome = self.refresh("fip-dashboard")
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("missing", outcome.reason)
        self.assertFalse((self.root / "content/snapshots/fip-dashboard.toml").exists())
        self.put("fip-dashboard-fips.json", [{"id": "fip", "declarations": [{"resource": "res", "principle": "F1"}]}])
        self.assertEqual(self.refresh("fip-dashboard").status, "changed")

    def nkr_page(self, page: int, size: int, ids: list[str]) -> None:
        results = [
            {
                "id": f"nkr/{i}",
                "content": {
                    "repositoryName": f"Repository {i}",
                    "mainUrl": "https://r.example.org/",
                    "pidType": ["DOI"],
                    "mainContact": {"email": "person@example.org"},
                    "unreviewed": "left out",
                },
            }
            for i in ids
        ]
        self.put(f"nkr-{page}.json", {"pageNum": page, "pageSize": 100, "size": size, "results": results})

    def test_nkr_pages_completely_and_keeps_only_reviewed_fields(self) -> None:
        self.nkr_page(0, 0, [])
        outcome = self.refresh("nkr")
        self.assertEqual(outcome.status, "empty", "NKR lists none: no header-only file")
        self.assertFalse((self.root / "content/snapshots/nkr.toml").exists())
        with mock.patch.object(refresh_snapshots, "NKR_PAGE_SIZE", 2):
            self.nkr_page(0, 3, ["a", "b"])
            self.nkr_page(1, 3, ["c"])
            self.assertEqual(self.refresh("nkr").status, "changed")
            snapshot = (self.root / "content/snapshots/nkr.toml").read_text(encoding="utf-8")
            self.assertEqual(snapshot.count("[[record]]"), 3)
            self.assertIn('pidType = ["DOI"]', snapshot)
            self.assertIn("mainContactPresent = true", snapshot)
            self.assertNotIn("person@example.org", snapshot)
            self.assertNotIn("unreviewed", snapshot)
            self.nkr_page(1, 3, [])
            outcome = self.refresh("nkr")
            self.assertEqual(outcome.status, "rejected")
            self.assertIn("2 of 3", outcome.reason)
        with (
            mock.patch.object(refresh_snapshots, "MAX_PAGES", 1),
            mock.patch.object(refresh_snapshots, "NKR_PAGE_SIZE", 1),
        ):
            self.nkr_page(0, 2, ["a"])
            self.assertIn("more than 1", self.refresh("nkr").reason)
        self.assertEqual(build_crate.load_content(self.root / "content")["snapshots"][0]["snapshot"]["source"], "NKR")
        self.assertTrue(build_crate.outputs(self.root), "a snapshot of NKR does not disturb the build")
        self.assertIn("pidType", refresh_snapshots.nkr_fields(build_crate.ROOT))
        self.assertNotIn(
            "mainContact", [line.split(" = ")[0] for line in snapshot.splitlines() if line.startswith("mainContact ")]
        )

    def test_the_run_reports_each_outcome_and_fails_on_a_rejection(self) -> None:
        self.put("heslar.json", {"data": []})
        report = Path(self.temp.name) / "report.json"
        with mock.patch.object(refresh_snapshots, "ROOT", self.root), mock.patch("builtins.print"):
            code = refresh_snapshots.main(["heslar", "--input", str(self.inputs), "--report", str(report)])
        self.assertEqual(code, 1)
        outcomes = json.loads(report.read_text(encoding="utf-8"))["outcomes"]
        self.assertEqual([(item["source"], item["status"]) for item in outcomes], [("heslar", "rejected")])
        self.assertFalse(hasattr(refresh_snapshots, "slug"), "the unused duplicate slug helper is gone")


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

    def commit(self, message: str) -> str:
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.org", "add", "-A")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.org", "commit", "-q", "-m", message)
        return check_content.git(self.root, "rev-parse", "HEAD").strip()

    def test_local_and_pull_request_runs_compare_from_where_the_branch_left_the_base(self) -> None:
        self.git("init", "-q", "-b", "main")
        fork = self.commit("base")
        self.git("checkout", "-q", "-b", "topic")
        self.edit("stations/01-one.toml", "Postup.", "Upravený postup.")
        self.commit("branch edit without paradata")
        self.git("checkout", "-q", "main")
        self.append("ledger.toml", "\n# a later change on the base branch\n")
        tip = self.commit("base moves on")
        self.git("checkout", "-q", "topic")
        content = build_crate.load_content(self.root / "content")
        for base in ("main", tip):
            self.assertEqual(check_content.merge_base(self.root, base), fork, base)
            report = check_content.Report()
            check_content.check_freshness(report, content, self.root, base)
            self.assertTrue(any(error.startswith("one.03:") for error in report.errors), (base, report.errors))
        # Comparing with the branch's own last commit, as the old local default did, hides the committed edit.
        report = check_content.Report()
        check_content.check_freshness(report, content, self.root, "HEAD")
        self.assertEqual(report.errors, [])

    ACTION = (
        '\n[[action]]\nid = "{id}"\ntype = "update"\nname = "Edit"\nagent = "tester"\ninstruments = ["model"]\n'
        "results = [{results}]\nendTime = {end}\n"
    )

    def merge(self, branch: str) -> None:
        self.git(
            "-c", "user.name=Test", "-c", "user.email=test@example.org", "merge", "-q", "--no-ff", branch, "-m", branch
        )

    def freshness_errors(self, base: str) -> list[str]:
        report = check_content.Report()
        check_content.check_freshness(report, build_crate.load_content(self.root / "content"), self.root, base)
        return report.errors

    def test_a_base_that_moves_on_after_the_work_ended_keeps_the_action_fresh(self) -> None:
        # Queue run 40151368869 rejected release PR #114 this way: its action ended before the base moved on.
        self.git("init", "-q", "-b", "main")
        self.commit("base")
        self.git("checkout", "-q", "-b", "topic")
        self.edit("stations/01-one.toml", "Postup.", "Upravený postup.")
        self.append("provenance.toml", self.ACTION.format(id="edit", results='"one.03"', end="2000-01-01T00:00:00Z"))
        self.commit("edit whose work ended long before the base moved on")
        self.git("checkout", "-q", "main")
        self.append("ledger.toml", "\n# a later change on the base branch\n")
        tip = self.commit("base moves on")
        self.merge("topic")  # the merge group: the entry on top of the newer base
        self.assertEqual(self.freshness_errors(tip), [])

    def test_an_extended_action_needs_a_later_end_time(self) -> None:
        self.git("init", "-q", "-b", "main")
        self.append("provenance.toml", self.ACTION.format(id="earlier", results='"one.01"', end="2026-02-01T12:00:00Z"))
        base = self.commit("base with an earlier action")
        self.edit("stations/01-one.toml", "Postup.", "Upravený postup.")
        self.edit("provenance.toml", 'results = ["one.01"]', 'results = ["one.01", "one.03"]')
        errors = self.freshness_errors(base)
        self.assertTrue(any(error.startswith("one.03:") and "later endTime" in error for error in errors), errors)
        self.edit("provenance.toml", "endTime = 2026-02-01T12:00:00Z", "endTime = 2026-02-02T12:00:00Z")
        self.assertEqual(self.freshness_errors(base), [])

    def test_a_merge_group_covers_each_entry_with_its_own_action(self) -> None:
        self.git("init", "-q", "-b", "main")
        base = self.commit("base")
        self.git("checkout", "-q", "-b", "first")
        self.edit("stations/01-one.toml", "Postup.", "Upravený postup.")
        self.append("provenance.toml", self.ACTION.format(id="first", results='"one.03"', end="2026-03-01T12:00:00Z"))
        self.commit("first entry with its action")
        self.git("checkout", "-q", "-b", "second", "main")
        self.edit("stations/01-one.toml", "Hlavní myšlenka.", "Upravená hlavní myšlenka.")
        self.commit("second entry without paradata")
        self.git("checkout", "-q", "-b", "group", "main")
        self.merge("first")
        self.merge("second")
        errors = self.freshness_errors(base)
        self.assertEqual([error.split(":", 1)[0] for error in errors], ["one.02"], errors)
        self.append("provenance.toml", self.ACTION.format(id="second", results='"one.02"', end="2026-03-01T12:00:00Z"))
        self.assertEqual(self.freshness_errors(base), [])

    def test_every_compared_kind_needs_an_action(self) -> None:
        content = build_crate.load_content(self.root / "content")
        compared = set(check_content.item_fingerprints(content))
        self.assertTrue({"guide", "organization:org", "test:test_one"} <= compared)
        content["provenance"][0]["results"] = []
        errors = check_content.check(content, self.root, today=TODAY).errors
        for item_id in compared:
            self.assertTrue(any(f":{item_id}: no provenance action covers" in f":{error}" for error in errors), item_id)

    def test_an_organisation_needs_paradata(self) -> None:
        self.append("guide.toml", '\n[[organization]]\nid = "new-org"\nname = "New Organisation"\n')
        self.assertError("organization:new-org: no provenance action covers this item")


class AlphaThreeQueueTests(unittest.TestCase):
    """Queue run 40151368869 rejected release PR #114: its release action ended at 01:28:10 UTC, and the new queue
    base 7b3fa74 was committed at 01:36:37 (task 8.1). History now decides, so the action prepared before the base
    moved still covers the Guide metadata it changed."""

    BASE = "7b3fa743f0afe526c9cd8067ec734702f432ea22"
    PREPARED = datetime(2026, 10, 25, 1, 28, 10, tzinfo=UTC)

    def setUp(self) -> None:
        try:
            check_content.git(build_crate.ROOT, "merge-base", "--is-ancestor", self.BASE, "HEAD")
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("the queue base is not an ancestor of this checkout")

    def test_the_release_action_prepared_before_the_base_moved_covers_the_guide(self) -> None:
        content = build_crate.load_content()
        action = next(action for action in content["provenance"] if action["id"] == "release-1.0.0-alpha.3")
        action["endTime"] = self.PREPARED
        committed = check_content.git(build_crate.ROOT, "show", "-s", "--format=%cI", self.BASE).strip()
        self.assertLess(self.PREPARED, datetime.fromisoformat(committed), "the clock comparison that failed the queue")
        report = check_content.Report()
        check_content.check_freshness(report, content, build_crate.ROOT, self.BASE)
        self.assertEqual([error for error in report.errors if error.startswith("guide:")], [], report.errors)


class ExactBaseTests(unittest.TestCase):
    """The first pull-request run failed for eight organisations against this exact base (review task 12.21)."""

    BASE = "01f20310966149b5bf1fb896047608f5fb8bac50"
    ORGANISATIONS = ("knav", "aru-praha", "cesnet", "msmt", "ntk", "csda", "cuni", "nrp")

    def setUp(self) -> None:
        try:
            check_content.git(build_crate.ROOT, "cat-file", "-e", self.BASE + "^{commit}")
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("the reported base commit is not in this clone")

    def errors(self, content: dict) -> list[str]:
        report = check_content.Report()
        check_content.check_freshness(report, content, build_crate.ROOT, self.BASE)
        return [
            error
            for error in report.errors
            if error.removeprefix("organization:").split(":", 1)[0] in self.ORGANISATIONS
        ]

    def test_the_eight_organisations_are_covered_against_the_reported_base(self) -> None:
        content = build_crate.load_content()
        self.assertEqual(self.errors(content), [])
        for action in content["provenance"]:
            action["results"] = [
                result
                for result in action.get("results", [])
                if result.removeprefix("organization:") not in self.ORGANISATIONS
            ]
        self.assertEqual(
            sorted(error.removeprefix("organization:").split(":", 1)[0] for error in self.errors(content)),
            sorted(self.ORGANISATIONS),
        )


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

    def report(self):
        content = build_crate.load_content(self.root / "content")
        path = self.root / "content" / check_duplicates.ACCEPTED_FILE
        accepted = tomllib.loads(path.read_text(encoding="utf-8")).get("accepted", []) if path.exists() else []
        return check_duplicates.check(content, accepted)

    def duplicates(self) -> list[str]:
        return self.report().errors

    def assertDuplicate(self, fragment: str) -> None:  # noqa: N802 - unittest naming
        errors = self.duplicates()
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_knav_tool_that_is_a_curated_entry_is_linked(self) -> None:
        snapshot = self.root / "content" / "snapshots" / "knav-tools.toml"
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_text(
            '[snapshot]\nsource = "KNAV"\nurl = "https://example.org/knav"\nretrieved = 2026-01-01\n\n'
            '[[tool]]\nalternateIds = [{ scheme = "knav", value = "svc" }]\nid = "svc"\nname = "Service tool"\n'
            'url = "https://example.org/service"\nsteps = ["planning"]\n'
            'disciplines = ["all"]\ndescription = "A service."\n',
            encoding="utf-8",
        )
        self.assertDuplicate("knav:svc: describes one thing with resource:service")
        self.assertDuplicate("link the record with knav")
        suggestion = self.report().suggestions[0]
        self.assertEqual(
            (suggestion.entry, suggestion.field_name, suggestion.file, suggestion.table, suggestion.value),
            ("resource:service", "knav", "content/resources.toml", "", "svc"),
        )
        self.edit("resources.toml", 'id = "service"\n', 'id = "service"\nknav = "svc"\n')
        self.assertEqual(self.duplicates(), [])
        # A curated entry names a tool the snapshot has.
        self.edit("resources.toml", 'knav = "svc"', 'knav = "ghost"')
        self.assertError("knav names no tool of the KNAV catalogue snapshot ('ghost')")

    def test_a_datacite_repository_id_is_well_formed_and_names_one_entry(self) -> None:
        self.edit("provenance.toml", '"test:test_one"]', '"test:test_one", "repo-first"]')
        repositories = self.root / "content" / "repositories.toml"
        entry = (
            '[[repository]]\nid = "{id}"\nname = "Repo"\nurl = "https://{id}.example.org/"\nkind = "general"\n'
            'status = "pilot"\nasOf = 2026-01-01\n'
        )
        repositories.write_text(entry.format(id="repo-first") + 'datacite = "member.repo"\n', encoding="utf-8")
        self.assertEqual(self.errors(), [])
        repositories.write_text(entry.format(id="repo-first") + 'datacite = "Member Repo"\n', encoding="utf-8")
        self.assertError("datacite is not a DataCite repository ID ('Member Repo')")
        repositories.write_text(
            entry.format(id="repo-first")
            + 'datacite = "member.repo"\n\n'
            + entry.format(id="repo-second")
            + 'datacite = "member.repo"\n',
            encoding="utf-8",
        )
        self.assertError("member.repo")

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
        self.assertEqual(self.report().suggestions, [], "a name/address lookalike is not a safe link suggestion")

    def test_re3data_record_suggests_the_curated_repository_link(self) -> None:
        self.append(
            "guide.toml",
            '\n[[resourceType]]\nid = "registry"\nname = { cs = "Registr", en = "Registry" }\n',
        )
        self.edit("resources.toml", 'type = "service"', 'type = "registry"')
        self.edit(
            "resources.toml", 'stations = ["one"]\n', 'stations = ["one"]\n\n[resource.repository]\nkind = "general"\n'
        )
        snapshot = self.root / "content" / "snapshots" / "re3data.toml"
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_text(
            '[snapshot]\nsource = "re3data"\nurl = "https://www.re3data.org/"\nretrieved = 2026-01-01\n\n'
            '[[repository]]\nalternateIds = [{ scheme = "re3data", value = "r3d100000001" }]\n'
            'id = "service"\nname = "Test repository"\nurl = "https://example.org/service"\n'
            're3data = "r3d100000001"\n',
            encoding="utf-8",
        )
        self.assertDuplicate("re3data:r3d100000001: describes one thing with resource:service")
        self.assertTrue(any("id:service: names several entities" in error for error in self.errors()))
        suggestion = self.report().suggestions[0]
        self.assertEqual(
            (suggestion.entry, suggestion.field_name, suggestion.file, suggestion.table, suggestion.value),
            ("resource:service", "re3data", "content/resources.toml", "resource.repository", "r3d100000001"),
        )
        report = self.root / ".cache" / "duplicates.json"
        self.assertEqual(check_duplicates.main(["--root", str(self.root), "--report", str(report)]), 1)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(data["formatVersion"], 1)
        self.assertEqual(data["suggestions"][0]["field"], "re3data")
        self.append(
            "guide.toml",
            '\n[[instrument]]\nid = "duplicate-fix"\nname = "Duplicate fix command"\nversion = "1"\n'
            'url = "https://example.org/fix"\nkind = "software"\n',
        )
        self.assertEqual(check_duplicates.main(["--root", str(self.root), "--fix", "--person", "tester"]), 0)
        self.assertEqual(self.duplicates(), [])
        self.assertEqual(self.errors(), [])
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"))
        graph = {entity["@id"]: entity for entity in crate["@graph"]}
        self.assertEqual(build_crate.as_list(graph["#repositories"]["hasPart"]), [{"@id": "#resource-service"}])
        self.assertNotIn("#repository-service", graph)
        self.assertIn(
            're3data = "r3d100000001"',
            (self.root / "content" / "resources.toml").read_text(encoding="utf-8"),
        )

    def test_fix_does_not_apply_an_ambiguous_group(self) -> None:
        self.append(
            "sources.toml",
            '\n[[source]]\nid = "copy"\ntype = "webpage"\ntitle = "Copy"\n'
            'url = "http://www.example.org/service/"\ndateAccessed = 2026-01-01\n',
        )
        before = (self.root / "content" / "resources.toml").read_text(encoding="utf-8")
        self.assertEqual(check_duplicates.main(["--root", str(self.root), "--fix"]), 1)
        self.assertEqual((self.root / "content" / "resources.toml").read_text(encoding="utf-8"), before)

    def test_clean_fix_returns_nonzero_without_writing(self) -> None:
        path = self.root / "content" / "resources.toml"
        before = path.read_bytes()
        self.assertNotEqual(check_duplicates.main(["--root", str(self.root), "--fix"]), 0)
        self.assertEqual(path.read_bytes(), before)

    def test_conflicting_authoritative_matches_are_not_safe(self) -> None:
        self.edit("sources.toml", 'id = "report"', 'id = "report"\ndoi = "10.1234/example"')
        snapshot = self.root / "content" / "snapshots" / "knav-tools.toml"
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_text(
            '[snapshot]\nsource = "KNAV"\nurl = "https://example.org/knav"\nretrieved = 2026-01-01\n'
            '\n[[tool]]\nid = "a"\nalternateIds = [{scheme = "knav", value = "a"}]\n'
            'name = "First tool"\nurl = "https://example.org/report"\n'
            '\n[[tool]]\nid = "b"\nalternateIds = [{scheme = "knav", value = "b"}]\n'
            'name = "Second tool"\nurl = "https://doi.org/10.1234/example"\n',
            encoding="utf-8",
        )
        path = self.root / "content" / "sources.toml"
        before = path.read_bytes()
        self.assertTrue(self.report().errors)
        self.assertEqual(self.report().suggestions, [])
        self.assertNotEqual(check_duplicates.main(["--root", str(self.root), "--fix"]), 0)
        self.assertEqual(path.read_bytes(), before)

    def test_existing_empty_link_and_repeated_insertion_preserve_bytes(self) -> None:
        self.dashboard('\nurl = "https://example.org/service"')
        suggestion = self.report().suggestions[0]
        path = self.root / "content" / "resources.toml"
        self.edit("resources.toml", 'fipClass = ["Registry"]', 'fipClass = ["Registry"]\nfipDashboard = ""')
        before = path.read_bytes()
        self.assertEqual(self.report().suggestions, [])
        self.assertIsNone(check_duplicates.apply_suggestion(self.root, suggestion))
        self.assertEqual(path.read_bytes(), before)
        self.edit("resources.toml", 'fipDashboard = ""\n', "")
        self.assertIsNotNone(check_duplicates.apply_suggestion(self.root, suggestion))
        linked = path.read_bytes()
        self.assertIsNone(check_duplicates.apply_suggestion(self.root, suggestion))
        self.assertEqual(path.read_bytes(), linked)
        tomllib.loads(path.read_text(encoding="utf-8"))

    def test_invalid_proposed_toml_is_not_written(self) -> None:
        path = self.root / "content" / "resources.toml"
        before = path.read_bytes()
        self.assertIsNone(
            check_duplicates.insert_field(path, "[[resource]]", "service", "", field_name="invalid key", value="record")
        )
        self.assertEqual(path.read_bytes(), before)

    def test_valid_toml_in_the_wrong_table_is_not_written(self) -> None:
        self.append(
            "resources.toml",
            '\n[resource.repository]\nkind = "general"\n[resource.citation] # source\ntype = "webpage"\n',
        )
        path = self.root / "content" / "resources.toml"
        before = path.read_bytes()
        self.assertIsNone(
            check_duplicates.insert_field(
                path, "[[resource]]", "service", "resource.repository", field_name="re3data", value="r3d1"
            )
        )
        self.assertEqual(path.read_bytes(), before)

    def test_duplicate_report_is_written_only_when_requested(self) -> None:
        report_dir = self.root / ".cache" / "report"
        with mock.patch.dict(os.environ, {"CHECK_REPORT_DIR": str(report_dir)}, clear=False):
            self.assertEqual(check_duplicates.main(["--root", str(self.root)]), 0)
        self.assertEqual(json.loads((report_dir / "duplicates.json").read_text(encoding="utf-8"))["formatVersion"], 1)
        self.assertFalse((self.root / "content" / "duplicates.json").exists())
        with mock.patch.dict(os.environ, {"CHECK_REPORT_DIR": ""}, clear=False):
            self.assertEqual(check_duplicates.main(["--root", str(self.root)]), 0)
        self.assertFalse((self.root / "content" / "duplicates.json").exists())

    def test_registry_record_needs_a_link(self) -> None:
        self.dashboard('\nurl = "https://example.org/service"')
        self.assertDuplicate(
            "fip-dashboard:r1: describes one thing with resource:service (address 'example.org/service'"
        )
        self.assertDuplicate("link the record with fipDashboard")
        suggestion = self.report().suggestions[0]
        self.assertEqual(
            (suggestion.entry, suggestion.field_name, suggestion.file, suggestion.table, suggestion.value),
            ("resource:service", "fipDashboard", "content/resources.toml", "", "r1"),
        )
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
        self.assertTrue({"#resource-nma", "#resource-fairsharing", "#fer-nusl", "#fer-cesnet-invenio"} <= members)
        self.assertNotIn("#fer-asep", members)
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
        self.assertIn("#fer-asep", members)
        self.assertIn("#fer-clarin-dspace", members)

    def test_duplicate_check_follows_reviewed_cross_registry_links(self) -> None:
        content = build_crate.load_content()
        entries = {item.name: item for item in check_duplicates.entries(content)}
        self.assertIn("fd:asep-arl", entries["re3data:r3d100014032"].keys)
        self.assertIn("fd:clarin-dspace", entries["re3data:r3d100010386"].keys)

    def test_missing_node_package_stops_the_build_before_output(self) -> None:
        out = build_crate.ROOT / ".cache" / "test-missing-prerequisite"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        (out / "previous.txt").write_text("previous build\n", encoding="utf-8")
        try:
            with mock.patch.object(build_api, "SWAGGER_DIR", out / "no-such-package"):
                with self.assertRaises(build_site.MissingPrerequisiteError) as raised:
                    build_site.build(out)
                self.assertIn("swagger-ui-dist", str(raised.exception))
                self.assertIn("npm ci", str(raised.exception))
                self.assertEqual(sorted(path.name for path in out.iterdir()), ["previous.txt"])
                with mock.patch("sys.stderr") as stderr:
                    self.assertEqual(build_site.main(["--out", str(out)]), 2)
                printed = "".join(call.args[0] for call in stderr.write.call_args_list)
                self.assertIn("swagger-ui-dist", printed)
                self.assertIn("npm ci", printed)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    @unittest.skipUnless(
        (build_api.SWAGGER_DIR / build_api.SWAGGER_FILES[0]).is_file(), "needs the Node packages: run npm ci"
    )
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
                "api/pr/R1.1.json",
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

    def test_every_tracked_top_level_directory_is_protected(self) -> None:
        try:
            listed = subprocess.run(
                ["git", "ls-files", "-z"], cwd=build_crate.ROOT, capture_output=True, check=True
            ).stdout.decode("utf-8")
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git is not available")
        tracked = {name.split("/", 1)[0] for name in listed.split("\0") if "/" in name}
        self.assertTrue(tracked)
        self.assertEqual(tracked - build_crate.PROTECTED_TREES, set())

    def test_every_interface_key_the_page_names_has_its_strings(self) -> None:
        # FG.t falls back to the key itself, so a key missing from content/ui.toml shows on the page as dotted text.
        strings = tomllib.loads((build_crate.ROOT / "content" / "ui.toml").read_text(encoding="utf-8"))

        def defined(key: str) -> bool:
            node: object = strings
            for part in key.split("."):
                node = node.get(part) if isinstance(node, dict) else None
            return isinstance(node, dict) and bool(node.get("cs") and node.get("en"))

        call = re.compile(r'\bFG\.t\(\s*"([A-Za-z]\w*(?:\.\w+)+)"\s*[,)]')
        named = [
            (path.name, key)
            for path in sorted((build_crate.ROOT / "assets" / "js").glob("*.js"))
            for key in call.findall(path.read_text(encoding="utf-8"))
        ]
        self.assertGreater(len(named), 400)
        self.assertEqual([f"{name}: {key}" for name, key in named if not defined(key)], [])


def make_link(test: unittest.TestCase, path: Path, target: Path) -> None:
    """A directory link, or a junction where Windows refuses links without privilege; skips when neither exists."""
    try:
        os.symlink(target, path, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            test.skipTest("directory links are not available")
        import _winapi  # noqa: PLC0415 - Windows only

        _winapi.CreateJunction(str(target), str(path))


class SiteOutputTests(FixtureCase):
    """The build replaces only a site directory it made; it refuses before anything is generated or removed."""

    def test_development_container_inputs_are_not_site_output(self) -> None:
        path = self.root / ".devcontainer" / "generated"
        with self.assertRaisesRegex(build_crate.UnsafeOutputError, "authored tree"):
            build_crate.site_directory(path, self.root)
        self.assertFalse(path.exists())

    def sentinel(self, relative: str, root: Path | None = None) -> Path:
        path = (root or self.root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("authored", encoding="utf-8")
        return path

    def assertRefused(self, out: Path, *sentinels: Path) -> None:  # noqa: N802 - unittest naming
        generated = mock.patch.object(build_crate, "outputs", side_effect=AssertionError("generated before the check"))
        with generated, self.assertRaises(build_crate.UnsafeOutputError):
            build_site.build(out, self.root)
        for path in sentinels:
            self.assertEqual(path.read_text(encoding="utf-8"), "authored", path)

    def test_the_repository_and_authored_trees_are_refused(self) -> None:
        guide = self.root / "content" / "guide.toml"
        original = guide.read_bytes()
        sentinels = (self.sentinel("api/index.html"), self.sentinel("assets/css/app.css"), self.sentinel("docs/a.md"))
        for out in (
            self.root,
            self.root / ".",
            self.root / "content",
            self.root / "api",
            self.root / "assets",
            self.root / "assets" / "css" / "site",
            self.root / "_site" / ".." / "content",
            self.root / "node_modules" / "site",
        ):
            with self.subTest(out=out):
                self.assertRefused(out, *sentinels)
        self.assertEqual(guide.read_bytes(), original)

    def test_directories_outside_the_repository_files_and_foreign_directories_are_refused(self) -> None:
        outside = self.sentinel("keep.txt", self.root.parent / "outside")
        readme = self.sentinel("README.md")
        foreign = self.sentinel("previews/keep.txt")
        checkout = self.sentinel("_site/.git/HEAD")
        for out in (outside.parent, readme, foreign.parent, checkout.parent.parent):
            with self.subTest(out=out):
                self.assertRefused(out, outside, readme, foreign, checkout)

    def test_links_and_junctions_to_other_directories_are_refused(self) -> None:
        guide = self.root / "content" / "guide.toml"
        original = guide.read_bytes()
        outside = self.sentinel("keep.txt", self.root.parent / "outside")
        make_link(self, self.root / "_site", self.root / "content")
        make_link(self, self.root / "elsewhere", outside.parent)
        (self.root / ".cache").mkdir()
        make_link(self, self.root / ".cache" / "assets", self.root / "content")
        for out in (self.root / "_site", self.root / "elsewhere", self.root / ".cache" / "assets" / "site"):
            with self.subTest(out=out):
                self.assertRefused(out, outside)
        self.assertEqual(guide.read_bytes(), original)
        self.assertFalse((self.root / "content" / "site").exists())

    def test_a_site_the_build_made_an_empty_or_the_default_directory_is_replaced_and_marked(self) -> None:
        made = self.root / ".cache" / "site"
        build_crate.replace_site(made, self.root)
        self.sentinel(".cache/site/stale.txt")
        empty = self.root / "empty"
        empty.mkdir()
        legacy = self.sentinel("_site/old.html").parent
        for out in (made, empty, legacy, self.root / "new" / "site"):
            with self.subTest(out=out):
                site = build_crate.replace_site(out, self.root)
                self.assertEqual([path.name for path in site.iterdir()], [build_crate.SITE_MARKER])

    def test_the_standalone_api_refuses_the_authored_api_before_removing_it(self) -> None:
        docs = self.sentinel("api/index.html")
        with self.assertRaises(build_crate.UnsafeOutputError):
            build_api.write_site(self.root, {})
        with self.assertRaises(build_crate.UnsafeOutputError):
            build_api.write_site(self.root / "api", {})
        failing = mock.Mock(side_effect=AssertionError("wrote the API"))
        with (
            mock.patch.object(build_crate, "ROOT", self.root),
            mock.patch.object(build_api, "write_site", failing),
            mock.patch("sys.stderr"),
        ):
            for out in (self.root, self.root / "api", self.root / "assets", self.root / "_site" / ".." / "api"):
                with self.subTest(out=out):
                    self.assertEqual(build_api.main(["--out", str(out)]), 2)
        failing.assert_not_called()
        self.assertEqual(docs.read_text(encoding="utf-8"), "authored")


class Elements(HTMLParser):
    """Start tags with their attributes and the text inside links, as a browser's parser reads them."""

    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.link_texts: list[str] = []
        self._in_link = False
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))
        if tag == "a":
            self._in_link = True
            self.link_texts.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._in_link = False

    def handle_data(self, data: str) -> None:
        if self._in_link:
            self.link_texts[-1] += data


class GeneratedMarkupTests(FixtureCase):
    """Empty collections, the profile's HTTPS rule and generated HTML hold for minimal content and hostile values."""

    def test_minimal_content_without_snapshots_publishes_a_valid_description(self) -> None:
        self.assertFalse((self.root / "content" / "snapshots").exists())
        content = build_crate.load_content(self.root / "content")
        # The fixture carries no interface strings of its own for the API; the guide's are used as they are.
        content["ui"]["api"] = tomllib.loads((build_crate.CONTENT / "ui.toml").read_text(encoding="utf-8"))["api"]
        api = build_api.Api(build_crate.build_crate(content), content)
        docs = {path: json.loads(text) for path, text in api.files().items()}
        openapi = docs[build_api.OPENAPI_FILE]
        empty = [name for name in build_crate.API_COLLECTIONS if not api.records[name]]
        self.assertIn("fips", empty, "the fixture exercises an empty snapshot collection")
        self.assertEqual(
            docs[build_api.META_FILE]["hasPart"],
            [f"{name}.json" for name in build_crate.API_COLLECTIONS] + ["health.json"],
        )
        for name in build_crate.API_COLLECTIONS:
            listed = docs[f"api/{name}.json"]
            self.assertEqual(listed["numberOfItems"], len(listed["itemListElement"]), name)
            self.assertIn(f"/api/{name}.json", openapi["paths"])
            record_path = f"/api/{name}/{{{build_api.PARAMETERS[name]}}}.json"
            if name in empty:
                self.assertEqual(listed["numberOfItems"], 0, name)
                self.assertNotIn(record_path, openapi["paths"])
                continue
            for _, entity_id in api.records[name]:
                self.assertIn("/" + api.paths[entity_id], openapi["paths"], name)

    def test_link_elements_escape_hostile_quoted_values(self) -> None:
        hostile = {"rel": 'x" onload="alert(1)', "type": "a&b<c>", "href": 'page"><script>alert(1)</script>'}
        parsed = Elements(build_crate.link_elements([hostile, {"rel": "license", "href": "https://example.org/l"}]))
        self.assertEqual([tag for tag, _ in parsed.tags], ["link", "link"])
        self.assertEqual(parsed.tags[0][1], hostile)
        self.assertEqual(parsed.tags[1][1], {"rel": "license", "href": "https://example.org/l"})

    def test_profile_page_escapes_file_links_and_names(self) -> None:
        shapes = self.root / build_crate.PROFILE_DIR
        names = ['x" onmouseover="alert(1)<b>.ttl', "a'b&c #1.ttl"]
        with mock.patch.object(Path, "rglob", return_value=[shapes / name for name in names]):
            page = build_crate.profile_page(self.root, {"profileVersion": "0.1"})["profile/0.1/index.html"]
        parsed = Elements(page)
        links = [
            attributes for tag, attributes in parsed.tags if tag == "a" and attributes.get("type") == "text/turtle"
        ]
        expected = sorted(f"{build_crate.PROFILE_DIR}/{name}" for name in names)
        hrefs = [link["href"] for link in links]
        for name in expected:
            self.assertIn("../../" + urllib.parse.quote(name), hrefs)
        self.assertTrue(all(set(link) == {"href", "type"} for link in links))
        self.assertNotIn("b", [tag for tag, _ in parsed.tags])
        self.assertTrue({name.removeprefix("profile/") for name in expected} <= set(parsed.link_texts))

    def test_every_profile_link_rule_requires_https(self) -> None:
        shapes = (build_crate.ROOT / build_crate.PROFILE_DIR / "must" / "1_content.ttl").read_text(encoding="utf-8")
        blocks = re.findall(r"sh:property \[(.*?)\]", shapes, flags=re.S)
        links = [block for block in blocks if "sh:path schema:url" in block]
        self.assertGreaterEqual(len(links), 2)
        for block in links:
            self.assertIn('sh:pattern "^https://"', block)


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

    def test_only_unit_fixtures_are_isolated_from_the_production_tag(self) -> None:
        producer = {"FAIR_GUIDE_BUILD_CHANNEL": "production", "FAIR_GUIDE_RELEASE_TAG": "v1.0.0"}
        completed = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(check_all.subprocess, "run", return_value=completed) as called:
            self.assertTrue(check_all.run(check_all.Job("unit", ["fixture"]), producer).ok)
            self.assertEqual(called.call_args.kwargs["env"]["FAIR_GUIDE_BUILD_CHANNEL"], "local")
            self.assertEqual(called.call_args.kwargs["env"]["FAIR_GUIDE_RELEASE_TAG"], "")
            self.assertTrue(check_all.run(check_all.Job("versions", ["fixture"]), producer).ok)
            self.assertEqual(called.call_args.kwargs["env"], producer)
        self.assertEqual(producer["FAIR_GUIDE_RELEASE_TAG"], "v1.0.0")

    def test_live_checks_run_only_on_request(self) -> None:
        self.assertNotIn("live", [job.name for job in check_all.jobs("HEAD", live=False)])
        self.assertIn("live", [job.name for job in check_all.jobs("HEAD", live=True)])

    def test_an_unknown_check_is_refused(self) -> None:
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            check_all.main(["--only", "no-such-check"])

    def test_only_runs_the_named_checks_and_their_documented_dependency(self) -> None:
        build = check_all.Result(check_all.Job("build", []), 0, 0.1, "")
        content = check_all.Result(check_all.Job("content", []), 0, 0.1, "")
        with (
            mock.patch.object(check_all, "run", return_value=build) as run,
            mock.patch.object(check_all, "run_all", return_value=[content]) as run_all,
            mock.patch.object(check_all, "emit_report") as emit,
            mock.patch.object(check_all.check_content, "default_base", return_value="origin/main"),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(check_all.main(["--only", "content"]), 0)
        self.assertEqual([call.args[0].name for call in run.call_args_list], ["build"], "no health-api or other job")
        self.assertEqual([job.name for job in run_all.call_args.args[0]], ["content"])
        emit.assert_called_once()
        self.assertEqual([job.name for job in emit.call_args.args[3]], ["content"])
        self.assertFalse(emit.call_args.kwargs.get("pending_api"))
        self.assertIn("health-api", [job.name for job in emit.call_args.args[2]])
        named = check_all.selected_jobs([check_all.Job("content", []), check_all.Job("health-api", [])], ["health-api"])
        self.assertEqual([job.name for job in named], ["health-api"])

    def test_unrun_jobs_are_reported_unrun_and_the_run_partial(self) -> None:
        jobs = [check_all.Job("content", []), check_all.Job("unit", []), check_all.Job("health-api", [])]
        build = check_all.Result(check_all.Job("build", []), 0, 0.1, "")
        with tempfile.TemporaryDirectory() as temp, mock.patch("builtins.print"):
            check_all.emit_report(
                build, [check_all.Result(jobs[0], 0, 0.1, "")], jobs, jobs[:1], output=Path(temp), previous=None
            )
            report = json.loads((Path(temp) / "health.json").read_text(encoding="utf-8"))
        statuses = {job["name"]: job["status"] for job in report["run"]["jobs"]}
        self.assertEqual(statuses, {"build": "passed", "content": "passed", "unit": "not_run", "health-api": "not_run"})
        self.assertEqual(report["run"]["status"], "partial")


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
        here = "api/pr/R1.1.json"
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
        self.assertIn("../pr/R1.1.json", build_crate.as_list(metric["inDimension"]))

    def test_checks_are_benchmarks_whose_questions_have_manual_tests(self) -> None:
        checks = [path for path in self.docs if path.startswith("api/check/")]
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

    def test_vocabulary_mapping_and_document_are_enforced(self) -> None:
        guide = build_crate.load_content()["guide"]["guide"]
        self.assertEqual([], build_crate.vocabulary_errors(guide))
        # Planted: a guide-specific term with no broader established term and no recorded reason is refused.
        with mock.patch.object(build_crate, "GUIDE_TERM_SHAPES", {}):
            errors = build_crate.vocabulary_errors(guide, terms={"orphanTerm": "A term with no parent."})
        self.assertTrue(any("no broader established term and no recorded reason" in error for error in errors), errors)
        # Planted: a published guide term absent from the vocabulary document is refused.
        errors = build_crate.vocabulary_errors(guide, document="<http://example.org/terms#other> a rdf:Property .")
        self.assertTrue(any("absent from the vocabulary document" in error for error in errors), errors)

    def test_one_setting_moves_the_guide_and_another_keeps_its_terms(self) -> None:
        # The guide's address is set once: a build at another address names the configured one only as the reviewed
        # namespace of its own terms and profile, which moving the site never renames (decision 28).
        moved = "https://guide.example.org/fair/"
        with mock.patch.dict(os.environ, {build_crate.BASE_URL_ENV: moved}):
            outputs = build_crate.outputs()
            content = build_crate.load_content()
            api = build_api.Api(build_crate.build_crate(content), content).files()
        namespace = content["guide"]["guide"]["vocabularyBase"].removesuffix("terms#")
        self.assertEqual(content["guide"]["guide"]["pageUrl"], moved)
        for path, text in {**outputs, **api}.items():
            rest = re.sub(re.escape(namespace) + r"(?:terms|profile/)", "", text)
            self.assertNotIn(self.page_url, rest, path)
        self.assertIn(namespace + "terms#", outputs[build_crate.CRATE_FILE])
        self.assertNotIn(moved + "terms#", outputs[build_crate.CRATE_FILE])
        self.assertIn(f"<{namespace}profile/", outputs[build_crate.PROFILE_DIR + "/profile.ttl"])


class FixDuplicateCommandTests(FixtureCase):
    def duplicates(self) -> list[str]:
        content = build_crate.load_content(self.root / "content")
        accepted = (
            tomllib.loads((self.root / "content" / check_duplicates.ACCEPTED_FILE).read_text(encoding="utf-8")).get(
                "accepted", []
            )
            if (self.root / "content" / check_duplicates.ACCEPTED_FILE).exists()
            else []
        )
        return check_duplicates.check(content, accepted).errors

    def prepare(self) -> None:
        self.edit("guide.toml", 'name = "Test Person"', 'name = "Test Person"\ngithub = "tester"')
        self.append(
            "guide.toml",
            '\n[[instrument]]\nid = "duplicate-fix"\nname = "Duplicate fix command"\nversion = "1"\n'
            'url = "https://example.org/fix"\nkind = "software"\n',
        )
        self.append(
            "guide.toml",
            '\n[[resourceType]]\nid = "registry"\nname = { cs = "Registr", en = "Registry" }\n',
        )
        self.edit("resources.toml", 'type = "service"', 'type = "registry"')
        self.edit(
            "resources.toml",
            'stations = ["one"]\n',
            'stations = ["one"]\n\n[resource.repository]\nkind = "general"\n',
        )
        snapshot = self.root / "content" / "snapshots" / "re3data.toml"
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_text(
            '[snapshot]\nsource = "re3data"\nurl = "https://www.re3data.org/"\nretrieved = 2026-01-01\n'
            'license = "https://creativecommons.org/publicdomain/zero/1.0/"\n\n'
            '[[repository]]\nalternateIds = [{ scheme = "re3data", value = "r3d100000001" }]\n'
            'id = "r3d100000001"\nname = "Test repository"\nurl = "https://example.org/service"\n'
            're3data = "r3d100000001"\n',
            encoding="utf-8",
        )

        register_ids.register(self.root / "content")

    def test_comment_body_is_bounded_and_keeps_the_commit(self) -> None:
        text = fix_duplicates.bounded_comment("prefix\n\n", "x" * 70000, "\nCommit: `abc`.")
        self.assertLessEqual(len(text), fix_duplicates.COMMENT_LIMIT)
        self.assertIn("diff truncated", text)
        self.assertTrue(text.endswith("Commit: `abc`."))

    def test_command_is_exact(self) -> None:
        self.assertTrue(fix_duplicates.parse_command("/fix-duplicates"))
        self.assertTrue(fix_duplicates.parse_command("  /fix-duplicates\n"))
        for body in ("/fix-duplicates now", "/refresh re3data", "please /fix-duplicates", ""):
            self.assertFalse(fix_duplicates.parse_command(body))

    def test_dry_run_applies_link_and_provenance(self) -> None:
        self.prepare()
        self.assertEqual(
            fix_duplicates.main(["--root", str(self.root), "--pr", "82", "--commenter", "tester", "--dry-run"]),
            0,
        )
        resources = (self.root / "content" / "resources.toml").read_text(encoding="utf-8")
        self.assertIn('re3data = "r3d100000001"', resources)
        provenance = (self.root / "content" / "provenance.toml").read_text(encoding="utf-8")
        self.assertIn('agent = "tester"', provenance)
        self.assertIn('instruments = ["duplicate-fix"]', provenance)
        self.assertIn('results = ["service"]', provenance)
        self.assertEqual(self.errors(), [])
        self.assertEqual(self.duplicates(), [])

    def test_unknown_commenter_is_refused_without_change(self) -> None:
        self.prepare()
        before = (self.root / "content" / "resources.toml").read_text(encoding="utf-8")
        self.assertEqual(
            fix_duplicates.main(["--root", str(self.root), "--pr", "82", "--commenter", "stranger", "--dry-run"]),
            1,
        )
        self.assertEqual((self.root / "content" / "resources.toml").read_text(encoding="utf-8"), before)

    class FakeGitHub:
        def __init__(self, repository, token):
            self.repository = repository
            self.writer = True
            self.pull_data = None
            self.pull_queue = []
            self.comments = []
            self.commits = []

        def can_write(self, login):
            return self.writer

        def pull(self, pr):
            if self.pull_queue:
                return self.pull_queue.pop(0)
            return self.pull_data

        def comment(self, pr, body):
            self.comments.append(body)

        def commit(self, pull, files, message):
            self.commits.append((pull, files, message))
            return "f" * 40

    def github_pull(self, head="a" * 40, repo="dsw-nrp/eosc-fair-guide", base="main"):
        return {
            "state": "open",
            "base": {"ref": base, "repo": {"default_branch": "main"}},
            "head": {"sha": head, "ref": "agents/tester/fix", "repo": {"full_name": repo}},
        }

    def test_github_refuses_unauthorised_or_foreign_pull_requests(self) -> None:
        self.prepare()
        default_head = self.github_pull()
        default_head["head"]["ref"] = "main"
        for writer, pull in (
            (False, self.github_pull()),
            (True, self.github_pull(repo="fork/guide")),
            (True, self.github_pull(base="release")),
            (True, default_head),
        ):
            fake = self.FakeGitHub("dsw-nrp/eosc-fair-guide", "token")
            fake.writer = writer
            fake.pull_data = pull
            before = (self.root / "content" / "resources.toml").read_text(encoding="utf-8")
            with mock.patch.object(fix_duplicates, "GitHub", lambda repo, token, fake=fake: fake):
                self.assertEqual(fix_duplicates.run_fix(self.root, 82, "tester", "dsw-nrp/eosc-fair-guide", "token"), 0)
            self.assertEqual(fake.commits, [])
            self.assertTrue(fake.comments)
            self.assertEqual((self.root / "content" / "resources.toml").read_text(encoding="utf-8"), before)

    def test_github_commits_only_after_the_head_is_rechecked(self) -> None:
        self.prepare()
        fake = self.FakeGitHub("dsw-nrp/eosc-fair-guide", "token")
        fake.pull_data = self.github_pull()
        fake.pull_queue = [self.github_pull(), self.github_pull(head="b" * 40)]
        with mock.patch.object(fix_duplicates, "GitHub", lambda repo, token: fake):
            self.assertEqual(
                fix_duplicates.run_fix(
                    self.root, 82, "tester", "dsw-nrp/eosc-fair-guide", "token", expected_head="a" * 40
                ),
                0,
            )
        self.assertEqual(fake.commits, [])
        self.assertIn("head moved", fake.comments[-1])

    def test_github_commits_the_link_and_provenance(self) -> None:
        self.prepare()
        register_path = self.root / "content" / "identifiers.toml"
        original = tomllib.loads(register_path.read_text(encoding="utf-8"))
        original["issued"]["actions"].append("retired-action")
        original["retired"]["actions"] = ["retired-action"]
        register_path.write_text(
            "# Preserve the reviewed register.\n"
            + register_ids.render(original["register"]["prepared"], original["issued"], original["retired"]),
            encoding="utf-8",
        )
        fake = self.FakeGitHub("dsw-nrp/eosc-fair-guide", "token")
        fake.pull_data = self.github_pull()
        with mock.patch.object(fix_duplicates, "GitHub", lambda repo, token: fake):
            self.assertEqual(
                fix_duplicates.run_fix(
                    self.root, 82, "tester", "dsw-nrp/eosc-fair-guide", "token", expected_head="a" * 40
                ),
                0,
            )
        self.assertEqual(len(fake.commits), 1)
        files = fake.commits[0][1]
        self.assertIn("content/resources.toml", files)
        self.assertIn("content/provenance.toml", files)
        self.assertIn("content/identifiers.toml", files)
        self.assertIn('re3data = "r3d100000001"', files["content/resources.toml"])
        self.assertIn('agent = "tester"', files["content/provenance.toml"])
        action = tomllib.loads(files["content/provenance.toml"])["action"][-1]["id"]
        original["issued"]["actions"].append(action)
        self.assertEqual(tomllib.loads(files["content/identifiers.toml"]), original)
        self.assertTrue(files["content/identifiers.toml"].startswith("# Preserve the reviewed register.\n"))
        self.assertEqual(self.errors(), [])
        self.assertIn("Applied the safe duplicate links", fake.comments[-1])

    def test_github_does_not_register_unrelated_missing_identifiers(self) -> None:
        self.prepare()
        path = self.root / "content" / "identifiers.toml"
        register = tomllib.loads(path.read_text(encoding="utf-8"))
        register["issued"]["resources"].remove("service")
        path.write_text(
            register_ids.render(register["register"]["prepared"], register["issued"], register["retired"]),
            encoding="utf-8",
        )
        fake = self.FakeGitHub("dsw-nrp/eosc-fair-guide", "token")
        fake.pull_data = self.github_pull()
        with mock.patch.object(fix_duplicates, "GitHub", lambda repo, token: fake):
            fix_duplicates.run_fix(self.root, 82, "tester", fake.repository, "token", expected_head="a" * 40)
        self.assertEqual(fake.commits, [])
        self.assertIn("'service' is not registered", fake.comments[-1])
        self.assertNotIn("service", tomllib.loads(path.read_text(encoding="utf-8"))["issued"]["resources"])

    def test_workflow_extraction_can_validate_and_fix_real_registered_content(self) -> None:
        repository = SCRIPTS.parent
        extracted = self.root / "extracted"
        shutil.copytree(repository / "content", extracted / "content")
        self.assertTrue(
            any("attachment does not exist" in error for error in fix_duplicates.content_errors(extracted)),
            "content-only extraction misses authored validation attachments",
        )
        workflow = (repository / ".github/workflows/fix-duplicates.yml").read_text(encoding="utf-8")
        archive = re.search(r'git archive "\$archived_head" ([^|\n]+)', workflow)
        self.assertIsNotNone(archive)
        for relative in archive.group(1).split():
            if relative == "content":
                continue
            source = repository / relative
            if source.is_dir():
                shutil.copytree(source, extracted / relative)
            else:
                shutil.copyfile(source, extracted / relative)
        resources = extracted / "content" / "resources.toml"
        original = resources.read_text(encoding="utf-8")
        self.assertIn('re3data = "r3d100014970"\n', original)
        resources.write_text(original.replace('re3data = "r3d100014970"\n', "", 1), encoding="utf-8")
        fake = self.FakeGitHub("dsw-nrp/eosc-fair-guide", "token")
        fake.pull_data = self.github_pull()
        with mock.patch.object(fix_duplicates, "GitHub", lambda repo, token: fake):
            fix_duplicates.run_fix(extracted, 82, "motyc", fake.repository, "token", expected_head="a" * 40)
        self.assertEqual(len(fake.commits), 1, fake.comments[-1])
        self.assertEqual(
            set(fake.commits[0][1]),
            {"content/resources.toml", "content/provenance.toml", "content/identifiers.toml"},
        )
        self.assertEqual(fix_duplicates.content_errors(extracted), [])

    def test_extracted_content_must_match_the_initial_head(self) -> None:
        self.prepare()
        fake = self.FakeGitHub("dsw-nrp/eosc-fair-guide", "token")
        fake.pull_data = self.github_pull(head="b" * 40)
        before = (self.root / "content" / "resources.toml").read_bytes()
        for expected in ("a" * 40, ""):
            with mock.patch.object(fix_duplicates, "GitHub", lambda repo, token: fake):
                fix_duplicates.run_fix(self.root, 82, "tester", fake.repository, "token", expected_head=expected)
            self.assertEqual(fake.commits, [])
            self.assertEqual((self.root / "content" / "resources.toml").read_bytes(), before)
        self.assertIn("head", fake.comments[-1])

    def test_apply_safe_suggestions_ignores_unsafe_or_unknown_placements(self) -> None:
        self.prepare()
        before = (self.root / "content" / "resources.toml").read_text(encoding="utf-8")
        suggestion = check_duplicates.Suggestion(
            entry="resource:service",
            record="re3data:r3d100000001",
            resolution="link",
            safe=False,
            file="content/resources.toml",
            table="resource.repository",
            field_name="re3data",
            value="r3d100000001",
            reason="unsafe",
        )
        self.assertEqual(fix_duplicates.apply_safe_suggestions(self.root, [suggestion]), ([], set()))
        self.assertEqual((self.root / "content" / "resources.toml").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
