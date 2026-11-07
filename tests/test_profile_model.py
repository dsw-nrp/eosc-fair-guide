"""The profile's graph-model shapes: the real crate conforms, and each shape refuses a planted violation of the rule
it states, so no shape is trusted for merely existing."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, URIRef

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import build_crate  # noqa: E402
from addresses import iri  # noqa: E402

SCHEMA = "http://schema.org/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
FTR = "https://w3id.org/ftr#"
DQV = "http://www.w3.org/ns/dqv#"


class ProfileModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        content = build_crate.load_content()
        crate = build_crate.build_crate(content)
        context = json.loads((ROOT / "tests/fixtures/ro-crate-1.2-context.json").read_text("utf-8"))["@context"]
        crate["@context"][0] = context
        cls.base = content["guide"]["guide"]["namespace"]
        cls.terms = content["guide"]["guide"]["vocabularyBase"]
        cls.crate = Graph().parse(data=json.dumps(crate), format="json-ld", publicID=cls.base)
        cls.shapes = Graph()
        for path, shape in build_crate.profile_shapes(ROOT, cls.base).items():
            if path.endswith("2_model.ttl"):
                cls.shapes.parse(data=shape, format="turtle", publicID=cls.base)

    def conforms(self, graph: Graph) -> tuple[bool, str]:
        conforms, _, report = validate(graph, shacl_graph=self.shapes, advanced=True)
        return conforms, report

    def planted(self, *triples: tuple, removed: tuple = ()) -> str:
        graph = Graph()
        for triple in self.crate:
            graph.add(triple)
        for triple in removed:
            graph.remove(triple)
        for triple in triples:
            graph.add(triple)
        conforms, report = self.conforms(graph)
        self.assertFalse(conforms, f"the planted violation passed: {triples or removed}")
        return report

    def test_the_real_crate_conforms(self) -> None:
        conforms, report = self.conforms(self.crate)
        self.assertTrue(conforms, report)

    def test_a_term_in_two_sets_or_with_a_second_membership_is_refused(self) -> None:
        term = URIRef(iri("vocabularies/tiers/minimum"))
        report = self.planted((term, URIRef(SCHEMA + "inDefinedTermSet"), URIRef(iri("vocabularies/levels"))))
        self.assertIn("exactly one term set", report)
        report = self.planted((term, URIRef(SKOS + "inScheme"), URIRef(iri("vocabularies/tiers"))))
        self.assertIn("membership once", report)

    def test_an_unnamed_organisation_or_a_fip_without_its_status_is_refused(self) -> None:
        organisation = URIRef(iri("organizations/cuni"))
        name = URIRef(SCHEMA + "name")
        report = self.planted(
            removed=tuple((organisation, name, value) for value in self.crate.objects(organisation, name))
        )
        self.assertIn("organisation MUST have a name", report)
        fip = next(self.crate.subjects(URIRef(self.terms + "fipStatus"), None))
        status = URIRef(self.terms + "fipStatus")
        self.planted(removed=tuple((fip, status, value) for value in self.crate.objects(fip, status)))

    def test_a_status_string_is_refused(self) -> None:
        clause = URIRef(iri("clauses/A.F1.R1"))
        status = URIRef(self.terms + "clauseStatus")
        current = next(self.crate.objects(clause, status))
        self.planted((clause, status, Literal("current")), removed=((clause, status, current),))

    def test_a_question_that_repeats_its_ftr_relations_in_schema_org_is_refused(self) -> None:
        question = URIRef(iri("questions/dataset.01"))
        report = self.planted((question, URIRef(SCHEMA + "isPartOf"), URIRef(iri("checks/dataset"))))
        self.assertIn("as its benchmark", report)
        check = URIRef(iri("checks/dataset"))
        report = self.planted((check, URIRef(SCHEMA + "hasPart"), question))
        self.assertIn("does not list them", report)

    def test_a_check_without_metrics_or_a_criterion_without_its_principles_is_refused(self) -> None:
        check = URIRef(iri("checks/dataset"))
        benchmark = URIRef(FTR + "hasBenchmark")
        self.planted(removed=tuple((question, benchmark, check) for question in self.crate.subjects(benchmark, check)))
        # The check lists no question again.
        report = self.planted((check, URIRef(FTR + "hasAssociatedMetric"), URIRef(iri("questions/dataset.01"))))
        self.assertIn("does not list them", report)
        criterion = URIRef(iri("tests/fair-champion/fc-metadata-pid"))
        about = URIRef(SCHEMA + "about")
        report = self.planted(
            removed=tuple((criterion, about, value) for value in self.crate.objects(criterion, about))
        )
        self.assertIn("MUST name the principles it assesses", report)
        implements = URIRef("http://semanticscience.org/resource/SIO_000233")
        report = self.planted(
            (criterion, implements, URIRef("https://w3id.org/fair-metrics/general/FM_F3_M_DataIdent"))
        )
        self.assertIn("at most one metric", report)

    def test_a_record_about_two_things_or_a_mapping_without_coverage_is_refused(self) -> None:
        record = URIRef(iri("repositories/zenodo") + "#knav")
        topic = URIRef("http://xmlns.com/foaf/0.1/primaryTopic")
        report = self.planted((record, topic, URIRef(iri("resources/github"))))
        self.assertIn("exactly one thing", report)
        mapping = URIRef(iri("questions/dataset.01") + "#prefill-datacite")
        coverage = URIRef(self.terms + "prefillCoverage")
        stated = tuple((mapping, coverage, value) for value in self.crate.objects(mapping, coverage))
        report = self.planted(removed=stated)
        self.assertIn("how much of its question", report)


if __name__ == "__main__":
    unittest.main()
