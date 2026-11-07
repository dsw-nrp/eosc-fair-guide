"""Every kind is selected by its class, a term set or a recorded reason, and every class is a type: a consumer selects
a kind's records exactly, without reading an identifier's form or a string. Each branch of the check is proved by a
planted selector that must fail."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import vocabularies
from addresses import iri
from rdflib import RDF, Literal, URIRef

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalogue_identity  # noqa: E402

build_crate = vocabularies.build_crate
SCHEMA = vocabularies.SCHEMA
DCTERMS = "http://purl.org/dc/terms/"


class KindSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        content = build_crate.load_content()
        guide = content["guide"]["guide"]
        cls.crate = build_crate.build_crate(content)
        cls.graph = vocabularies.crate_graph(cls.crate, guide["namespace"])
        cls.records = guide["recordBase"]
        cls.terms = guide["vocabularyBase"]

    def problems(self, selectors: dict | None = None) -> list[str]:
        return vocabularies.kind_problems(
            self.graph,
            build_crate.KIND_SELECTORS if selectors is None else selectors,
            catalogue_identity.KINDS,
            self.records,
            self.terms,
        )

    def test_every_kind_is_selected_exactly_or_records_why_not(self) -> None:
        self.assertEqual(self.problems(), [])
        self.assertEqual(set(build_crate.KIND_SELECTORS), set(catalogue_identity.KINDS))

    def test_a_kind_without_a_selector_is_refused_naming_it(self) -> None:
        selectors = {kind: selector for kind, selector in build_crate.KIND_SELECTORS.items() if kind != "clauses"}
        self.assertEqual(
            self.problems(selectors), ["clauses: no class, term set or recorded reason selects its records"]
        )

    def test_a_class_shared_with_another_kind_is_refused(self) -> None:
        found = self.problems(build_crate.KIND_SELECTORS | {"clauses": {"class": "CreativeWork"}})
        self.assertEqual(len(found), 1, found)
        self.assertRegex(found[0], r"^clauses: its selector also selects \d+ node\(s\), such as <")
        found = self.problems(build_crate.KIND_SELECTORS | {"organizations": {"class": "Organization"}})
        self.assertRegex(found[0], r"^organizations: its selector also selects \d+ node\(s\)")

    def test_a_selector_that_misses_records_is_refused(self) -> None:
        found = self.problems(build_crate.KIND_SELECTORS | {"vocabularies": {"class": "TermSet"}})
        self.assertTrue(found and found[0].startswith("vocabularies: its selector misses"), found)

    def test_only_the_guides_own_text_and_model_are_reached_by_iri(self) -> None:
        reasons = {kind for kind, selector in build_crate.KIND_SELECTORS.items() if "reason" in selector}
        self.assertEqual(reasons, {"callouts", "models", "pages"})

    def test_organisations_and_infrastructures_are_organisations_and_records_are_not(self) -> None:
        organisations = set(self.graph.subjects(RDF.type, URIRef(SCHEMA + "Organization")))
        own = {
            node
            for node in organisations
            if str(node).startswith((iri("organizations/"), iri("infrastructures/"))) and "#" not in str(node)
        }
        self.assertTrue(own <= organisations)
        # A described service can also be its author's or provider's organisation; a registry record is never one.
        self.assertTrue(
            all(str(node).startswith((iri("resources/"), iri("repositories/"))) for node in organisations - own)
        )
        self.assertFalse([node for node in organisations if "#" in str(node)])

    def test_every_class_is_a_type_and_no_class_is_a_string(self) -> None:
        self.assertFalse([entity["@id"] for entity in self.crate["@graph"] if "additionalType" in entity])
        self.assertFalse(list(self.graph.subject_objects(URIRef(SCHEMA + "additionalType"))))
        tests = set(self.graph.subjects(RDF.type, URIRef(build_crate.FTR + "Test")))
        self.assertTrue(tests)
        helpers = set(self.graph.subjects(RDF.type, URIRef(SCHEMA + "WebApplication")))
        self.assertEqual({str(node).removeprefix(iri("pages/")) for node in helpers}, {"identifiers", "citation"})
        schemas = set(self.graph.subjects(RDF.type, URIRef(build_crate.FIP_TERMS + "Metadata-schema")))
        self.assertIn(URIRef(iri("resources/datacite-schema")), schemas)

    def test_no_controlled_value_is_a_string(self) -> None:
        in_set = URIRef(SCHEMA + "inDefinedTermSet")
        for name, term_set in (
            ("clauseKind", "clause-kinds"),
            ("modelKind", "model-kinds"),
            ("mappingBasis", "correspondence-bases"),
            ("mappingCoverage", "evaluator-coverages"),
            ("discipline", "disciplines-knav"),
            ("coverage", "scopes-fip-dashboard"),
        ):
            with self.subTest(name):
                values = list(self.graph.objects(None, vocabularies.property_iri(name, self.terms)))
                self.assertTrue(values)
                self.assertFalse([value for value in values if isinstance(value, Literal)])
                sets = {self.graph.value(value, in_set) for value in values}
                self.assertEqual(sets, {URIRef(iri(f"vocabularies/{term_set}"))})

    def test_a_registrys_lists_are_its_schemes(self) -> None:
        based_on = URIRef(SCHEMA + "isBasedOn")
        for term_set, catalogue in (
            ("disciplines-knav", "knav-dm-tools-catalogue"),
            ("scopes-fip-dashboard", "fip-dashboard"),
        ):
            self.assertEqual(
                self.graph.value(URIRef(iri(f"vocabularies/{term_set}")), based_on),
                URIRef(iri(f"resources/{catalogue}")),
            )


if __name__ == "__main__":
    unittest.main()


class AssessmentCriterionTests(unittest.TestCase):
    """Every record of the tests kind is an assessment criterion, with its FTR type where FTR's definition holds: a
    test the Guide invokes through an API of its own implements a metric, a criterion an imported report states its
    results against is the provider's metric, and the Guide's browser-run local tests carry no FTR type."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = build_crate.load_content()
        crate = build_crate.build_crate(cls.content)
        cls.records = cls.content["guide"]["guide"]["recordBase"]
        cls.entities = {entity["@id"]: entity for entity in crate["@graph"]}

    def scope(self, scope: str) -> list[dict]:
        prefix = f"{self.records}tests/{scope}/"
        return [entity for key, entity in self.entities.items() if key.startswith(prefix) and "#" not in key]

    def test_no_manual_tests_remain(self) -> None:
        self.assertEqual(self.scope("self-check"), [])
        tests = [key for key in self.entities if key.startswith(self.records + "tests/") and "#" not in key]
        self.assertEqual(
            {key.removeprefix(self.records).split("/")[1] for key in tests},
            {"fair-champion", "fair-checker", "f-uji", "guide"},
        )

    def test_every_record_of_the_kind_is_an_assessment_criterion_with_its_ftr_type(self) -> None:
        expected = {
            "fair-champion": {"ftr:Test"},
            "fair-checker": {"ftr:Test"},
            "f-uji": {"ftr:Metric"},
            "guide": set(),
        }
        for scope, ftr in expected.items():
            records = self.scope(scope)
            self.assertTrue(records, scope)
            for entity in records:
                types = set(build_crate.as_list(entity["@type"]))
                self.assertIn("AssessmentCriterion", types, entity["@id"])
                self.assertEqual({name for name in types if name.startswith("ftr:")}, ftr, entity["@id"])

    def test_every_fair_champion_test_implements_the_metric_its_record_names(self) -> None:
        metrics = {test["id"]: test["metric"] for test in self.content["live"]["champion"]["test"]}
        tests = self.scope("fair-champion")
        self.assertEqual(len(tests), len(metrics))
        for entity in tests:
            self.assertEqual(entity["isImplementationOf"], {"@id": metrics[entity["identifier"]]})
            self.assertTrue(entity["isImplementationOf"]["@id"].startswith("https://w3id.org/fair-metrics/"))

    def test_a_local_test_implements_its_question_and_no_provider_criterion_claims_a_metric_it_lacks(self) -> None:
        for entity in self.scope("guide"):
            self.assertTrue(entity["isImplementationOf"]["@id"].startswith(self.records + "questions/"), entity["@id"])
        # FAIR-Checker publishes no metric IRIs, and F-UJI's criteria are metrics themselves.
        for scope in ("fair-checker", "f-uji"):
            self.assertFalse([entity["@id"] for entity in self.scope(scope) if "isImplementationOf" in entity])
