"""Contracts for software/FDO assessment and the guide's worked software example."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402


class ResearchPracticeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = build_crate.load_content(ROOT / "content")
        cls.crate = build_crate.build_crate(cls.content)
        cls.entities = {entity["@id"]: entity for entity in cls.crate["@graph"]}

    def test_software_and_content_have_separate_licences_and_identity(self) -> None:
        software = self.entities["#guide-software"]
        source = self.entities["#guide-source"]
        dataset = self.entities["./"]
        self.assertEqual(software["@type"], "SoftwareApplication")
        self.assertEqual(dataset["@type"], "Dataset")
        self.assertEqual(software["license"], source["license"])
        self.assertNotEqual(software["license"], dataset["license"])
        self.assertEqual(software["softwareVersion"], dataset["version"])
        self.assertEqual(dataset["isPartOf"], {"@id": "#guide-software"})
        self.assertEqual(software["subjectOf"], {"@id": "./"})
        self.assertEqual(source["codeRepository"], self.content["guide"]["guide"]["url"])

    def test_source_metrics_are_complete_and_distinct_from_data_principles(self) -> None:
        checks = {data["check"]["id"]: data for data in self.content["checks"]}
        software = checks["software"]["item"]
        fdo = checks["fdo"]["item"]
        self.assertEqual(len(software), 20)
        self.assertEqual({item["requirement"] for item in software[:17]}, {f"FRSM.FRSM-{n:02}" for n in range(1, 18)})
        labels = [f"FDOR-GR{n}" if n < 4 else f"FDO-GR{n}" for n in range(1, 16)]
        labels += [f"FDO-PIDR{n}" for n in range(1, 7)]
        labels += [f"FDO-FDOR{n}" if n < 9 else f"FDO-FDO{n}" for n in range(1, 12)]
        labels += ["FDO-RESR1", "FDO-RESR2"]
        self.assertEqual(len(fdo), 34)
        self.assertEqual({item["requirement"] for item in fdo}, {"FDO." + label for label in labels})
        for items, count in ((software, 8), (fdo, 6)):
            self.assertEqual(sum(item["tier"] == "basic" for item in items), count)
            existing = {principle["id"] for principle in self.content["principles"]}
            self.assertTrue(all(set(item.get("principles", [])) <= existing for item in items))
            self.assertTrue(all(item.get("owner") and item.get("fixAt") for item in items))

    def test_lazy_questions_preserve_complete_crate_and_path_metadata(self) -> None:
        core, parts = build_crate.split_crate(self.crate)
        self.assertFalse(any(entity["@type"] == "Question" for entity in core["@graph"]))
        questions = {entity["@id"]: entity for entity in parts["questions"]["entities"]}
        for item_id in ("#item-software.01", "#item-fdo.01", "#item-dataset.01"):
            self.assertEqual(questions[item_id], self.entities[item_id])
        rebuilt = {entity["@id"]: dict(entity) for entity in core["@graph"]}
        for part in parts.values():
            for entity in part["entities"]:
                self.assertNotIn(entity["@id"], rebuilt)
                rebuilt[entity["@id"]] = entity
            for entity_id, properties in part["properties"].items():
                rebuilt[entity_id].update(properties)
        self.assertEqual(rebuilt, self.entities)


if __name__ == "__main__":
    unittest.main()
