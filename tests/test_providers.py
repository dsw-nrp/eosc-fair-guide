"""Tests for external evaluators: their content checks, crate criteria and mappings, page configuration and paradata.

Run with ``python -m unittest discover -s tests``. Each test copies the minimal fixture, adds one evaluator with two
native criteria and a reviewed mapping, and asserts what the scripts accept, reject and publish.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_crate  # noqa: E402
from test_scripts import FixtureCase  # noqa: E402

EVALUATOR = """
[[connector]]
id = "evaluator"
name = "Evaluator API"
origin = "https://evaluator.example.org"
purpose = "Testing an optional evaluator"

[providers]
script = "assets/js/providers.js"
maxImportBytes = 2097152

[[provider]]
id = "evaluator"
name = "Evaluator"
resource = "service"
mode = "service"
connector = "evaluator"
path = "api/metric_{metric}?url={target}"
form = "https://evaluator.example.org/check"
documentation = "https://evaluator.example.org/docs"
scoreMax = 2
maxParallel = 2
timeoutSeconds = 30
maxBytes = 1000
observed = 2026-02-01
reviewed = [{ api = "1.0" }]

[[provider.metric]]
id = "M1"
alternateIds = [{ scheme = "evaluator", value = "M1" }]
name = "The provider's own wording."
principle = "F1"
label = { cs = "Čtení Průvodce", en = "The Guide's reading" }

[[provider.metric]]
id = "M2"
alternateIds = [{ scheme = "evaluator", value = "M2" }]
name = "An unmapped criterion."
principle = "F1"
label = { cs = "Bez mapování", en = "Unmapped" }

[[provider.mapping]]
metric = "M1"
question = "gate.01"
coverage = "whole"
note = { cs = "Pokrývá celou otázku.", en = "Covers the whole question." }
"""


class ProviderCase(FixtureCase):
    def setUp(self) -> None:
        super().setUp()
        self.append("live.toml", EVALUATOR)
        self.edit("provenance.toml", '"test:test_one"]', '"test:test_one", "provider:*"]')
        script = self.root / "assets" / "js" / "providers.js"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("/* fixture */\n", encoding="utf-8")


class ProviderContentTests(ProviderCase):
    def test_a_reviewed_evaluator_is_accepted(self) -> None:
        self.assertEqual([error for error in self.errors() if "provider" in error or "evaluator" in error], [])

    def test_a_mapping_names_a_real_question_coverage_and_note(self) -> None:
        self.edit("live.toml", 'question = "gate.01"', 'question = "gate.99"')
        self.assertError("unknown question 'gate.99'")

    def test_coverage_is_whole_or_partial(self) -> None:
        self.edit("live.toml", 'coverage = "whole"', 'coverage = "most"')
        self.assertError("coverage must be one of whole, partial")

    def test_a_mapping_states_what_it_covers_in_both_languages(self) -> None:
        self.edit(
            "live.toml",
            'note = { cs = "Pokrývá celou otázku.", en = "Covers the whole question." }',
            'note = { cs = "Pokrývá." }',
        )
        self.assertError("note needs Czech and English text")

    def test_criteria_reuse_existing_principles(self) -> None:
        self.edit(
            "live.toml",
            'id = "M2"\nalternateIds = [{ scheme = "evaluator", value = "M2" }]\n'
            'name = "An unmapped criterion."\nprinciple = "F1"',
            'id = "M2"\nalternateIds = [{ scheme = "evaluator", value = "M2" }]\n'
            'name = "An unmapped criterion."\nprinciple = "F9"',
        )
        self.assertError("unknown principle 'F9'")

    def test_mappings_need_reviewed_versions(self) -> None:
        self.edit("live.toml", 'reviewed = [{ api = "1.0" }]', "reviewed = []")
        self.assertError("reviewed must list the provider versions")

    def test_a_service_needs_a_reviewed_connector_and_bounds(self) -> None:
        self.edit("live.toml", 'connector = "evaluator"\npath', 'connector = "elsewhere"\npath')
        self.assertError("a service provider needs a reviewed connector")
        self.edit("live.toml", "maxParallel = 2", "maxParallel = 9")
        self.assertError("maxParallel must be between 1 and 4")

    def test_a_criterion_keeps_a_native_name(self) -> None:
        self.edit("live.toml", 'name = "The provider\'s own wording."', 'name = ""')
        self.assertError("name is the provider's own wording")

    def test_every_criterion_needs_paradata(self) -> None:
        self.edit("provenance.toml", ', "provider:*"]', "]")
        self.assertError("criterion:provider:evaluator.M1: no provenance action covers this item")


class ProviderCrateTests(ProviderCase):
    def test_criteria_and_mappings_are_crate_entities_loaded_with_the_questions(self) -> None:
        outputs = build_crate.outputs(self.root)
        graph = {entity["@id"]: entity for entity in json.loads(outputs[build_crate.CRATE_FILE])["@graph"]}
        criterion = graph["#criterion-evaluator-M1"]
        self.assertEqual(criterion["identifier"], "M1")
        self.assertEqual(criterion["name"], {"@language": "en", "@value": "The provider's own wording."})
        self.assertEqual(criterion["about"], {"@id": build_crate.principle_iri("F1")})
        self.assertEqual(criterion["url"], "https://evaluator.example.org/api/metric_M1")
        mapping = graph["#mapping-evaluator-M1-gate.01"]
        self.assertEqual(mapping["about"], {"@id": "#item-gate.01"})
        self.assertEqual(mapping["mappingCoverage"], "whole")
        self.assertEqual(build_crate.as_list(mapping["reviewedVersion"]), ["api 1.0"])
        unmapped = graph["#criterion-evaluator-M2"]
        self.assertNotIn("hasPart", unmapped, "an unmapped criterion stays listed without an invented association")
        entity = '{"@id":"#criterion-evaluator-M1","@type"'
        self.assertIn(entity, outputs[build_crate.PART_SCRIPTS["questions"]])
        self.assertNotIn(entity, outputs[build_crate.KB_SCRIPT], "criteria stay off the initial download")

    def test_the_page_receives_limits_and_reviewed_versions_but_not_labels(self) -> None:
        content = build_crate.load_content(self.root / "content")
        config = build_crate.page_config(content)["config"]["providers"]
        provider = config["list"][0]
        self.assertEqual(provider["metrics"], ["M1", "M2"])
        self.assertEqual(provider["reviewed"], [{"api": "1.0"}])
        self.assertEqual(provider["maxParallel"], 2)
        self.assertNotIn("metric", provider)
        self.assertEqual(config["maxImportBytes"], 2097152)

    def test_the_connector_enters_the_content_security_policy(self) -> None:
        content = build_crate.load_content(self.root / "content")
        self.assertIn("https://evaluator.example.org", build_crate.content_security_policy(content))

    def test_without_evaluators_the_page_has_no_provider_configuration(self) -> None:
        content = build_crate.load_content(self.root / "content")
        content["live"].pop("provider")
        self.assertIsNone(build_crate.page_config(content)["config"]["providers"])


if __name__ == "__main__":
    unittest.main()
