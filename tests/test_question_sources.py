"""Source language, normative context and lazy reconstruction contracts for assessment questions."""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_api  # noqa: E402
import build_crate  # noqa: E402
import check_content  # noqa: E402


class QuestionSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = build_crate.load_content(ROOT / "content")
        cls.crate = build_crate.build_crate(cls.content)
        cls.entities = {entity["@id"]: entity for entity in cls.crate["@graph"]}

    def test_original_language_is_preserved_and_separate_from_guide_translation(self) -> None:
        for clause_id, language in (("A.F1.R1", "cs"), ("FDO.FDO-GR9", "en"), ("CDIF.REQ1", "en")):
            entity = self.entities["#clause-" + clause_id]
            self.assertEqual(entity["guidance"]["@language"], language)
            self.assertNotEqual(entity["guidance"], entity["text"])
            self.assertTrue(entity["isPartOf"])
        core, parts = build_crate.split_crate(self.crate)
        self.assertFalse(any("guidance" in entity for entity in core["@graph"]))
        originals = {entity["@id"]: entity["guidance"] for entity in self.crate["@graph"] if "guidance" in entity}
        deferred = {
            entity["@id"]: entity["guidance"] for entity in parts["standards"]["entities"] if "guidance" in entity
        }
        deferred.update(
            {
                key: properties["guidance"]
                for key, properties in parts["standards"]["properties"].items()
                if "guidance" in properties
            }
        )
        self.assertEqual(originals, deferred)

    def test_context_keeps_identity_without_becoming_an_extra_requirement(self) -> None:
        contexts = {entity["identifier"] for entity in self.crate["@graph"] if entity.get("assessmentContext")}
        self.assertEqual(contexts, {"fdo.09", "fdo.29", "fdo.32"})
        for item_id in contexts:
            entity = self.entities["#item-" + item_id]
            self.assertTrue(entity["citation"])
            self.assertTrue(entity["description"])
        self.assertIn("can be of different types", self.entities["#clause-FDO.FDO-GR9"]["guidance"]["@value"])
        self.assertIn("strongly recommended", self.entities["#clause-FDO.FDO-GR6"]["guidance"]["@value"])

    def test_lazy_parts_reconstruct_full_source_attribution(self) -> None:
        core, parts = build_crate.split_crate(self.crate)
        rebuilt = {entity["@id"]: copy.deepcopy(entity) for entity in core["@graph"]}
        # The homepage and About citation keep their byline before deferred parts arrive.
        analysis = self.entities["./"]["isBasedOn"]["@id"]
        self.assertEqual(rebuilt[analysis]["creditText"], self.entities[analysis]["creditText"])
        for part in parts.values():
            for entity in part["entities"]:
                rebuilt[entity["@id"]] = copy.deepcopy(entity)
            for identifier, properties in part["properties"].items():
                rebuilt[identifier].update(properties)
        self.assertEqual(rebuilt, self.entities)

    def test_source_context_cannot_be_prefilled_and_language_cannot_be_invented(self) -> None:
        content = copy.deepcopy(self.content)
        fdo = next(check for check in content["checks"] if check["check"]["id"] == "fdo")
        next(item for item in fdo["item"] if item.get("context"))["prefill"] = {"resolver": True}
        clause = next(clause for clause in content["ledger"] if clause.get("guidance"))
        clause["guidanceLanguage"] = "xx"
        errors = check_content.check(content, ROOT).errors
        self.assertTrue(any("source context cannot be automatically answered" in error for error in errors))
        self.assertTrue(any("guidanceLanguage must be cs or en" in error for error in errors))

    def test_historical_api_test_discloses_source_context_instead_of_an_assessment(self) -> None:
        api = build_api.Api(self.crate, self.content)
        record = api.manual_test("fdo.09", "#item-fdo.09")
        self.assertTrue(record["assessmentContext"])
        self.assertIn("does not represent", record["description"]["en"])
        self.assertNotIn("assessmentContext", api.manual_test("fdo.01", "#item-fdo.01"))

    def test_report_version_and_metric_set_version_are_distinct(self) -> None:
        clause = self.entities["#clause-FRSM.FRSM-11"]
        self.assertEqual(clause["isPartOf"], {"@id": "https://doi.org/10.5281/zenodo.15535629"})
        self.assertIn("Only applicable if APIs are implemented", clause["guidance"]["@value"])
        self.assertEqual(self.entities[clause["isPartOf"]["@id"]]["version"], "1.1")
        fdo_source = self.entities["#clause-FDO.FDO-GR9"]["isPartOf"]["@id"]
        self.assertEqual(self.entities[fdo_source]["version"], "3.0")

    def test_each_question_has_originals_or_a_reviewed_source_link_basis(self) -> None:
        # These practical guide questions have no single published requirement to quote.
        # Their cited services/registries do not impose the guide's own recommendation.
        source_link_basis = {
            "institution.24": "institutional storage provision",
            "maturity.18": "registration in two independent registries",
        }
        missing = set()
        for check in self.content["checks"]:
            for item in check["item"]:
                value = self.entities["#item-" + item["id"]].get("citation", [])
                references = value if isinstance(value, list) else [value]
                self.assertTrue(references, item["id"])
                if not any("guidance" in self.entities.get(ref["@id"], {}) for ref in references):
                    missing.add(item["id"])
        self.assertEqual(
            missing, set(source_link_basis), "Review every missing original; one per check is insufficient"
        )

    def test_originals_keep_legally_and_operationally_important_conditions(self) -> None:
        law = self.entities["#clause-LAW-328-2025.83.2"]["guidance"]["@value"]
        self.assertIn("zvláštním právem pořizovatele databáze", law)
        self.assertIn("(4)", law)
        dataset = self.entities["#clause-OS3-RULES.24"]["guidance"]["@value"]
        self.assertIn("nezáleží na konkrétní roli", dataset)
        self.assertIn("pracovní smlouva", dataset)
        openssf = self.entities["#clause-OPENSSF.01"]
        self.assertIn("voluntarily self-certify", openssf["guidance"]["@value"])
        source = self.entities[openssf["isPartOf"]["@id"]]
        self.assertEqual(source["version"], "2024-08-16")
        self.assertEqual(source["license"], "https://creativecommons.org/licenses/by/3.0/")


if __name__ == "__main__":
    unittest.main()
