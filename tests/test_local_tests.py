"""Identity, executable attachments and API coverage of local advisory tests."""

import copy
import html
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_api  # noqa: E402
import build_crate  # noqa: E402
import build_site  # noqa: E402
import check_content  # noqa: E402


class LocalTestRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = build_crate.load_content(ROOT / "content")
        cls.crate = build_crate.build_crate(cls.content)
        cls.entities = {entity["@id"]: entity for entity in cls.crate["@graph"]}
        cls.api = build_api.Api(cls.crate, cls.content)
        cls.files = cls.api.files()

    def test_local_tests_have_individual_identity_and_executable_attachments(self) -> None:
        tests = self.content["live"]["test"]
        self.assertEqual(len(tests), 42)
        self.assertEqual(len({test["id"] for test in tests}), len(tests))
        crate_parts = {part["@id"] for part in self.entities["./"]["hasPart"]}
        for test in tests:
            with self.subTest(test=test["id"]):
                entity = self.entities["#test-" + test["id"]]
                question_id = "#item-" + test["question"]
                self.assertIn(question_id, self.entities)
                self.assertFalse(self.entities[question_id].get("assessmentContext"))
                self.assertEqual(entity["isImplementationOf"], {"@id": question_id})
                self.assertEqual({value["@language"] for value in entity["description"]}, {"cs", "en"})
                self.assertEqual({value["@language"] for value in entity["name"]}, {"cs", "en"})
                self.assertIn(test["id"], test["entryPoint"])
                entry = next(
                    self.entities[part["@id"]]
                    for part in build_crate.as_list(entity["additionalProperty"])
                    if self.entities[part["@id"]].get("propertyID") == "entryPoint"
                )
                self.assertEqual(entry["propertyID"], "entryPoint")
                self.assertEqual(entry["value"], test["entryPoint"])
                for part in entity["hasPart"]:
                    path = part["@id"]
                    self.assertTrue((ROOT / path).is_file(), path)
                    self.assertIn("SoftwareSourceCode", self.entities[path]["@type"])
                    self.assertIn(path, crate_parts)
                doc = self.entities[entity["subjectOf"]["@id"]]
                self.assertEqual(doc["url"], test["documentation"])
                self.assertIn(doc["isPartOf"]["@id"], crate_parts)
                self.assertTrue((ROOT / doc["isPartOf"]["@id"]).is_file())

    def test_api_describes_automatic_and_manual_implementations_separately(self) -> None:
        for test in self.content["live"]["test"]:
            with self.subTest(test=test["id"]):
                record = json.loads(self.files[f"api/test/guide/{test['id']}.json"])
                self.assertEqual(record["isImplementationOf"], f"../../q/{test['question']}.json")
                self.assertTrue(record["description"]["cs"])
                self.assertTrue(record["description"]["en"])
                metric = json.loads(self.files[f"api/q/{test['question']}.json"])
                self.assertEqual(
                    metric["hasImplementation"],
                    [f"../tests/{test['question']}.json", f"../test/guide/{test['id']}.json"],
                )
        # Manual question tests, curated Champion tests, local tests and external evaluators' criteria.
        criteria = sum(len(provider["metric"]) for provider in self.content["live"].get("provider", []))
        self.assertEqual(criteria, 29)
        self.assertEqual(json.loads(self.files["api/tests.json"])["numberOfItems"], 214 + 13 + 42 + criteria)

    def test_external_tests_link_documentation_and_execution_separately(self) -> None:
        for test in self.content["live"]["champion"]["test"]:
            record = self.entities["#test-" + test["id"]]
            links = {entry["@id"] for entry in record["subjectOf"]}
            self.assertIn(
                test.get("record")
                or self.content["live"]["champion"]["testRecord"].format(
                    id=next(item["value"] for item in test["alternateIds"] if item["scheme"] == "fair-champion")
                ),
                links,
            )
            self.assertIn(self.content["live"]["champion"]["documentation"], links)
            self.assertNotIn(record["url"], links)

    def test_existing_fair_principles_are_shared_by_questions_tests_and_api(self) -> None:
        questions = {item["id"]: item for check in self.content["checks"] for item in check["item"]}
        known = {entry["id"] for entry in self.content["principles"]}
        self.assertEqual(len(known), 15, "the established FAIR vocabulary is unchanged")
        for test in self.content["live"]["test"]:
            with self.subTest(test=test["id"]):
                question = questions[test["question"]]
                codes = question.get("principles", [])
                self.assertTrue(codes, "current local tests have applicable existing principle links")
                self.assertTrue(set(codes) <= known)
                entity = self.entities["#test-" + test["id"]]
                self.assertEqual(entity.get("about"), self.entities["#item-" + test["question"]].get("about"))
                record = json.loads(self.files[f"api/test/guide/{test['id']}.json"])
                self.assertEqual(
                    build_crate.as_list(record["about"]),
                    [f"../../pr/{code}.json" for code in codes],
                )
        self.assertEqual(questions["software.14"]["principles"], ["R1"])
        self.assertEqual(questions["software.20"].get("principles", []), [])
        self.assertEqual(questions["cdif.04"]["principles"], ["A1.2", "R1.1"])
        self.assertEqual(questions["fdo.21"].get("principles", []), [])
        self.assertEqual(
            questions["cdif.27"]["principles"], ["F2"], "existing source-linked profile mapping is preserved"
        )
        self.assertEqual(questions["software.03"]["requirement"], "FRSM.FRSM-03")
        self.assertFalse(any(entry.get("propertyID") == "fairArea" for entry in self.crate["@graph"]))

    def test_unknown_principles_are_rejected_without_forcing_a_mapping_for_every_question(self) -> None:
        content = copy.deepcopy(self.content)
        item = next(parent for parent in content["checks"] if parent["check"]["id"] == "software")["item"][0]
        item["principles"] = ["F1", "quality"]
        self.assertTrue(any("unknown principle" in error for error in check_content.check(content, ROOT).errors))
        item["principles"] = []
        self.assertFalse(any("unknown principle" in error for error in check_content.check(content, ROOT).errors))

    def test_registration_and_unsafe_or_mismatched_attachments_are_rejected(self) -> None:
        content = copy.deepcopy(self.content)
        test = content["live"]["test"][0]
        identifier = test["id"]
        content["identifiers"]["issued"]["tests"].remove(identifier)
        test["script"] = "assets/js/tests/../../outside.js"
        test["entryPoint"] = 'FairGuide.selfcheck.localTests["another-test"]'
        test["question"] = "fdo.09"
        errors = check_content.check(content, ROOT).errors
        self.assertTrue(any(identifier in error and "not registered" in error for error in errors))
        self.assertTrue(any("script must name an attached js file" in error for error in errors))
        self.assertTrue(any("entryPoint must name this test" in error for error in errors))
        self.assertTrue(any("source context cannot be automatically answered" in error for error in errors))

    def test_individual_documentation_is_generated_from_the_registry_in_both_languages(self) -> None:
        template = (ROOT / build_site.LOCAL_TEST_DOC).read_text(encoding="utf-8")
        self.assertTrue(all(not match.group("body").strip() for match in build_crate.BLOCK.finditer(template)))
        document = build_site.render_test_docs(template, self.content)
        for test in self.content["live"]["test"]:
            self.assertEqual(test["documentation"], f"assets/js/tests/index.html#{test['id']}")
            for language in build_crate.LANGS:
                anchor = test["id"] + ("-en" if language == "en" else "")
                self.assertIn(f'<h3 id="{anchor}"><code>{test["id"]}</code>', document)
                self.assertIn(html.escape(test["label"][language]), document)
                self.assertIn(html.escape(test["description"][language]), document)
                self.assertIn(f'href="../../../index.html#/{language}/K/catalogue/q/{test["question"]}"', document)
                self.assertIn(f'href="../../../api/test/guide/{test["id"]}.json"', document)
        changed = copy.deepcopy(self.content)
        changed["live"]["test"][0]["description"]["cs"] = '<img src="unsafe">Updated description from TOML'
        regenerated = build_site.render_test_docs(template, changed)
        self.assertIn("&lt;img src=&quot;unsafe&quot;&gt;Updated description from TOML", regenerated)
        self.assertNotIn('<img src="unsafe">', regenerated)
        self.assertNotIn("Updated description from TOML", template)

    def test_documentation_template_refuses_missing_and_committed_generated_blocks(self) -> None:
        template = (ROOT / build_site.LOCAL_TEST_DOC).read_text(encoding="utf-8")
        with self.assertRaisesRegex(build_crate.ContentError, "blocks are required"):
            build_site.render_test_docs(template.replace("<!-- generated:testsen -->", ""), self.content)
        with self.assertRaisesRegex(build_crate.ContentError, "must stay empty"):
            build_site.render_test_docs(
                template.replace("<!-- generated:testsen -->", "<!-- generated:testsen -->x"), self.content
            )


if __name__ == "__main__":
    unittest.main()
