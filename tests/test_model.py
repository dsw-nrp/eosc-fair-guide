"""The model preserves source scope, explicit associations and evidence precision."""

from __future__ import annotations

import copy
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_api  # noqa: E402
import build_crate  # noqa: E402
import check_content  # noqa: E402
import check_health  # noqa: E402


def bilingual(value: str) -> dict[str, str]:
    return {"cs": value, "en": value}


class ModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.content = build_crate.load_content(ROOT / "tests" / "fixtures" / "minimal" / "content")
        self.content["ui"] = build_crate.load_toml(ROOT / "content" / "ui.toml")
        self.content["sources"].append(
            {
                "id": "layers-seams-manuscript",
                "type": "article",
                "title": bilingual("Layers and seams of FAIR implementation"),
                "authors": ["Manuscript Author"],
                "inLanguage": "en",
                "preparationStatus": "in-preparation",
            }
        )
        self.content["model"] = {
            "model": {
                "id": "layers-seams",
                "source": "layers-seams-manuscript",
                **{key: bilingual(key) for key in ("name", "description", "introduction", "ordering", "feedback")},
            },
            "layer": [
                {"id": key, "name": bilingual(key), "description": bilingual(key)}
                for key in ("policy", "community", "infrastructure", "planning", "support", "evaluation")
            ],
            "seam": [
                {
                    "id": "repository-nma",
                    "layers": ["infrastructure"],
                    **{
                        key: bilingual(key)
                        for key in ("name", "description", "transfer", "sender", "recipient", "carrier", "maintainers")
                    },
                }
            ],
            "example": [
                {
                    "id": "pilot",
                    "seam": "repository-nma",
                    "name": bilingual("Pilot"),
                    "description": bilingual("A dated component observation"),
                    "scope": bilingual("Catalogue only"),
                    "status": "pilot",
                    "asOf": "2026-09",
                    "evidence": ["layers-seams-manuscript"],
                }
            ],
            "association": [{"target": "service", "layers": ["infrastructure"], "seams": ["repository-nma"]}],
            "context": [
                {
                    "station": "one",
                    "lens": "V",
                    "text": bilingual("A role-specific explanation"),
                    "seams": ["repository-nma"],
                }
            ],
        }
        self.content["ui"]["api"]["collection"]["model"] = {
            key: bilingual(key) for key in ("name", "description", "record", "parameter")
        }

    def errors(self) -> list[str]:
        report = check_content.Report()
        check_content.check_sources(report, self.content)
        check_content.check_model(report, self.content, check_content.vocabularies(self.content), date(2026, 10, 11))
        return report.errors

    def test_within_layer_connection_is_valid_and_does_not_claim_status(self) -> None:
        self.assertEqual(self.errors(), [])
        crate = build_crate.build_crate(self.content)
        graph = {item["@id"]: item for item in crate["@graph"]}
        seam = graph["#seam-repository-nma"]
        self.assertEqual(seam["implementationLayers"], {"@id": "#layer-infrastructure"})
        self.assertNotIn("serviceStatus", seam)
        self.assertEqual(graph["#model-example-pilot"]["statusAsOf"], "2026-09")
        self.assertEqual(graph["#resource-service"]["implementationSeams"], {"@id": "#seam-repository-nma"})
        self.assertNotIn("implementationSeams", graph["#item-gate.01"])

    def test_unknown_association_target_or_model_term_is_rejected(self) -> None:
        self.content["model"]["association"][0]["target"] = "missing"
        self.content["model"]["association"][0]["seams"] = ["made-up"]
        self.assertTrue(any("unknown content target" in error for error in self.errors()))
        self.assertTrue(any("unknown layer or seam" in error for error in self.errors()))
        with self.assertRaises(build_crate.ContentError):
            build_crate.build_crate(self.content)

    def test_in_preparation_exception_cannot_create_requirements_or_publication_facts(self) -> None:
        self.content["ledger"][0]["source"] = "layers-seams-manuscript"
        self.content["sources"][-1]["datePublished"] = date(2026, 9, 1)
        self.assertTrue(any("cannot supply ledger requirements" in error for error in self.errors()))
        self.assertTrue(any("cannot claim a DOI" in error for error in self.errors()))
        self.content["sources"][-1]["id"] = "another-draft"
        self.assertTrue(any("only the approved" in error for error in self.errors()))

    def test_generic_status_and_missing_or_imprecise_example_evidence_are_rejected(self) -> None:
        model = self.content["model"]
        model["seam"][0]["status"] = "operational"
        model["example"][0]["evidence"] = []
        model["example"][0]["asOf"] = "2026-13"
        errors = self.errors()
        for fragment in ("generic model definitions", "identifiable evidence", "YYYY-MM"):
            self.assertTrue(any(fragment in error for error in errors), errors)

    def test_deferred_model_reassembles_losslessly_without_expanding_initial_text(self) -> None:
        crate = build_crate.build_crate(self.content)
        core, parts = build_crate.split_crate(crate)
        restored = {item["@id"]: copy.deepcopy(item) for item in core["@graph"]}
        self.assertNotIn("#seam-repository-nma", restored)
        self.assertNotIn("#model-example-pilot", restored)
        deferred_ids = {item["@id"] for item in parts["model"]["entities"]}
        for term in build_crate.MODEL_TERMS:
            term_iri = crate["@context"][1][term]
            self.assertNotIn(term_iri, restored)
            self.assertIn(term_iri, deferred_ids)
            self.assertEqual(core["@context"][1][term], term_iri)
        for part in parts.values():
            restored.update({item["@id"]: item for item in part["entities"]})
            for entity_id, properties in part["properties"].items():
                restored[entity_id].update(properties)
        self.assertEqual(restored, {item["@id"]: item for item in crate["@graph"]})

    def test_api_and_health_expose_model_examples_and_actual_target_links(self) -> None:
        api = build_api.Api(build_crate.build_crate(self.content), self.content)
        docs = {
            api.paths[entity_id]: api.record(collection, record, entity_id)
            for collection, members in api.records.items()
            for record, entity_id in members
        }
        self.assertIn("api/model/repository-nma.json", docs)
        self.assertEqual(docs["api/model/pilot.json"]["statusAsOf"], "2026-09")
        self.assertEqual(build_api.PARAMETERS["model"], "model_id")
        record = docs["api/res/srv/service.json"]
        self.assertEqual(record["implementationSeams"], "../../model/repository-nma.json")
        health = api.health(check_health.make_report(self.content, today=date(2026, 10, 11)))
        model = next(group for group in health["integrity"] if group["type"] == "implementation model")
        self.assertEqual(model["failed"], 0)
        example = next(item for item in model["items"] if item["id"] == "example.pilot")
        self.assertEqual(example["api_record"], "model/pilot.json")
        self.content["model"]["example"][0]["evidence"] = ["missing"]
        broken = check_health.integrity(self.content, ROOT, date(2026, 10, 11))
        self.assertGreater(next(group for group in broken if group["type"] == "implementation model")["failed"], 0)

    def test_association_changes_enter_target_provenance_fingerprint(self) -> None:
        before = check_content.item_fingerprints(self.content)
        self.content["model"]["association"][0]["layers"] = ["community"]
        after = check_content.item_fingerprints(self.content)
        self.assertNotEqual(before["service"], after["service"])
        self.assertEqual(before["gate.01"], after["gate.01"])
        self.assertIn("context:one:V", after)
        self.assertIn("seam.repository-nma", check_content.issued_ids(self.content)["model"])

    def test_unknown_publisher_produces_a_clear_content_error(self) -> None:
        self.content["guide"]["guide"]["publisher"] = "missing-publisher"
        with self.assertRaisesRegex(build_crate.ContentError, "unknown publisher organisation 'missing-publisher'"):
            build_crate.build_crate(self.content)

    def test_worked_example_links_existing_revision_after_actions_are_built(self) -> None:
        action = self.content["provenance"][0]["id"]
        self.content["model"]["model"]["workedExample"] = {
            "name": bilingual("An inspectable revision"),
            "description": bilingual("Links actual content without claiming a live result"),
            "steps": ["A.F1.R1", "gate.01", f"action:{action}"],
        }
        self.assertEqual(self.errors(), [])
        crate = build_crate.build_crate(self.content)
        graph = {item["@id"]: item for item in crate["@graph"]}
        worked = graph["#model-worked-example"]
        self.assertEqual(
            worked["hasPart"], [{"@id": "#clause-A.F1.R1"}, {"@id": "#item-gate.01"}, {"@id": f"#action-{action}"}]
        )
        self.assertEqual(graph["#implementation-model"]["workExample"], {"@id": "#model-worked-example"})
        api = build_api.Api(crate, self.content)
        record = api.record("model", "layers-seams", "#implementation-model")
        self.assertTrue(
            any(
                isinstance(item, dict) and item.get("identifier") == "model-worked-example"
                for item in build_crate.as_list(record["hasPart"])
            )
        )

    def test_seam_association_reuses_endpoint_layers_without_citation_inheritance(self) -> None:
        self.content["model"]["association"][0].pop("layers")
        graph = {item["@id"]: item for item in build_crate.build_crate(self.content)["@graph"]}
        self.assertEqual(graph["#resource-service"]["implementationLayers"], {"@id": "#layer-infrastructure"})
        self.assertNotIn("implementationLayers", graph["#item-gate.01"])
        api = build_api.Api(build_crate.build_crate(self.content), self.content)
        station = api.record("stations", "one", "#station-one")
        contexts = build_crate.as_list(station["hasPart"])
        self.assertTrue(any(isinstance(item, dict) and item.get("identifier") == "context.one.V" for item in contexts))


if __name__ == "__main__":
    unittest.main()
