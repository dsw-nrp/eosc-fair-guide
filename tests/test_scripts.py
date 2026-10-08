"""Tests for the crate generator and the content checks.

Run with ``python -m unittest discover -s tests``. Each test copies the minimal fixture into a temporary
directory, changes it, and asserts that the scripts accept or reject it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_crate  # noqa: E402
import check_content  # noqa: E402

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
        self.assertEqual(page.count("</script>"), 2)
        self.assertIn("connect-src https://api.example.org", page)

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


if __name__ == "__main__":
    unittest.main()
