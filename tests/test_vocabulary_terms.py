"""Every term the Guide publishes from an established vocabulary is a term that vocabulary defines, at the IRI it
defines it, read from the pinned copies only. Each branch of the check is proved by a planted use that must fail."""

from __future__ import annotations

import datetime
import unittest
from pathlib import Path

import vocabularies
from addresses import iri
from rdflib import RDF, Graph, Literal, URIRef
from vocabularies import Use

ROOT = Path(__file__).resolve().parents[1]
build_crate = vocabularies.build_crate
SIO_IMPLEMENTS = "http://semanticscience.org/resource/SIO_000233"


class VocabularyTermTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import build_api  # noqa: PLC0415 - the API's context is read only here

        content = build_crate.load_content()
        guide = content["guide"]["guide"]
        cls.crate = build_crate.build_crate(content)
        cls.graph = vocabularies.crate_graph(cls.crate, guide["namespace"])
        cls.base = guide["vocabularyBase"]
        cls.document = build_crate.vocabulary_document(guide)
        cls.vocabularies = (*vocabularies.pinned(), vocabularies.guide_vocabulary(guide, cls.document))
        cls.shapes = {
            path: Graph().parse(data=text, format="turtle")
            for path, text in build_crate.profile_shapes(ROOT, guide["namespace"]).items()
        }
        cls.api_context = build_api.TERMS
        cls.uses = [
            *vocabularies.graph_uses(cls.graph, "the crate"),
            *vocabularies.context_uses(cls.crate["@context"][1], "the crate's context"),
            *vocabularies.graph_uses(Graph().parse(data=cls.document, format="turtle"), "the vocabulary document"),
            *vocabularies.context_uses(cls.api_context, "the API's context"),
        ]
        for path, shapes in cls.shapes.items():
            uses = vocabularies.graph_uses if path.endswith("profile.ttl") else vocabularies.shape_uses
            cls.uses += uses(shapes, path)

    def problems(self, *planted: Use) -> list[str]:
        return vocabularies.problems([*self.uses, *planted], self.vocabularies)

    def test_every_term_is_defined_by_a_pinned_vocabulary(self) -> None:
        self.assertEqual(self.problems(), [])

    def test_the_check_covers_every_place_a_term_is_written(self) -> None:
        sources = {use.source for use in self.uses}
        self.assertTrue({"the crate", "the crate's context", "the vocabulary document", "the API's context"} <= sources)
        self.assertTrue(any(source.endswith("2_model.ttl") for source in sources))
        positions = {(use.source, use.position) for use in self.uses}
        for position in ("property", "class", "datatype", "value"):
            self.assertIn(("the crate", position), positions)

    def test_a_schema_org_class_in_https_is_refused_naming_schema_org(self) -> None:
        planted = Use("https://schema.org/WebApplication", "class", "the crate")
        found = self.problems(planted)
        self.assertEqual(len(found), 1, found)
        self.assertIn("https://schema.org/WebApplication", found[0])
        self.assertIn("schema.org defines it as http://schema.org/WebApplication", found[0])

    def test_a_planted_class_in_the_graph_is_found_and_refused(self) -> None:
        graph = Graph()
        graph.add((URIRef(iri("pages/machines")), RDF.type, URIRef("https://schema.org/WebApplication")))
        found = vocabularies.problems(vocabularies.graph_uses(graph, "a planted graph"), self.vocabularies)
        self.assertTrue(any("wrong scheme; schema.org" in item for item in found), found)

    def test_an_unpinned_namespace_is_refused_naming_it(self) -> None:
        planted = Use("http://purl.org/ontology/bibo/doi", "property", "the crate")
        found = self.problems(planted)
        self.assertEqual(
            found,
            [
                "http://purl.org/ontology/bibo/doi (a property in the crate): its namespace "
                "http://purl.org/ontology/bibo/ has no pinned copy"
            ],
        )

    def test_a_term_its_vocabulary_does_not_define_is_refused(self) -> None:
        for planted, vocabulary in (
            (Use("http://schema.org/isImplementationOf", "property", "the crate"), "schema.org"),
            (Use("http://www.w3.org/ns/dcat#Records", "class", "the crate"), "DCAT"),
            (
                Use(
                    vocabularies.build_crate.vocabulary_base({"namespace": "https://w3id.org/eosc-cz/fair-guide/"})
                    + "noSuchTerm",
                    "property",
                    "the crate",
                ),
                "the Guide's vocabulary",
            ),
        ):
            with self.subTest(planted.iri):
                found = self.problems(planted)
                self.assertEqual(len(found), 1, found)
                self.assertIn(f"{vocabulary} defines no such term", found[0])

    def test_a_link_outside_the_vocabularies_is_not_a_term(self) -> None:
        self.assertEqual(self.problems(Use("https://schema.org/Dataset", "value", "the crate")), [])
        found = self.problems(Use("https://w3id.org/fair/principles/terms/F9", "value", "the crate"))
        self.assertIn("FAIR Vocabulary defines no such term", found[0])

    def test_a_literal_datatype_is_a_term(self) -> None:
        graph = Graph()
        graph.add(
            (
                URIRef(iri("pages/machines")),
                URIRef("http://schema.org/name"),
                Literal("x", datatype=URIRef("http://www.w3.org/2001/XMLSchema#nosuchtype")),
            )
        )
        found = vocabularies.problems(vocabularies.graph_uses(graph, "a planted graph"), self.vocabularies)
        self.assertTrue(any("XML Schema datatypes defines no such term" in item for item in found), found)

    def test_every_implementation_link_is_sios_own_iri(self) -> None:
        links = list(self.graph.subject_objects(URIRef(SIO_IMPLEMENTS)))
        self.assertTrue(links)
        self.assertEqual(list(self.graph.subject_objects(URIRef("https://" + SIO_IMPLEMENTS[7:]))), [])
        written = [use for use in self.uses if "semanticscience.org" in use.iri]
        self.assertTrue({use.source for use in written} >= {"the crate", "the crate's context", "the API's context"})
        self.assertTrue(all(use.iri.startswith("http://semanticscience.org/resource/") for use in written), written)
        model = next(shapes for path, shapes in self.shapes.items() if path.endswith("2_model.ttl"))
        self.assertIn(URIRef(SIO_IMPLEMENTS), set(model.objects()))

    def test_a_schema_org_use_outside_its_domain_is_refused(self) -> None:
        graph = Graph()
        for triple in self.graph:
            graph.add(triple)
        term = URIRef(iri("vocabularies/tiers/minimum"))
        graph.add((term, URIRef("http://schema.org/position"), Literal(1)))
        found = vocabularies.schema_problems([graph], self.base)
        self.assertTrue(any(item.startswith("schema:position: its domain") for item in found), found)

    def test_a_schema_org_use_outside_its_range_is_refused(self) -> None:
        graph = Graph()
        for triple in self.graph:
            graph.add(triple)
        page = URIRef(iri("pages/machines"))
        resource = URIRef(iri("resources/argos"))
        graph.add((page, URIRef("http://schema.org/audience"), resource))
        found = vocabularies.schema_problems([graph], self.base)
        self.assertTrue(any(item.startswith("schema:audience: its range schema:Audience") for item in found), found)

    def test_an_inverse_pair_or_a_set_listing_its_terms_is_refused(self) -> None:
        graph = Graph()
        for triple in self.graph:
            graph.add(triple)
        whole = URIRef(iri("pages/machines"))
        has_part = URIRef("http://schema.org/hasPart")
        part = next(graph.objects(whole, has_part))
        graph.add((part, URIRef("http://schema.org/isPartOf"), whole))
        term_set = URIRef(iri("vocabularies/tiers"))
        graph.add((term_set, URIRef("http://schema.org/hasDefinedTerm"), URIRef(iri("vocabularies/tiers/minimum"))))
        found = vocabularies.relation_problems([graph], self.base)
        self.assertTrue(any("schema:hasPart and schema:isPartOf" in item for item in found), found)
        self.assertTrue(any("set lists its term again" in item for item in found), found)

    def test_schema_org_accepted_lexical_datetimes_and_durations(self) -> None:
        for text, expected in (("2026-05", "Date"), ("2026", "Date"), ("PT5M", "Duration")):
            with self.subTest(text=text):
                self.assertIn(
                    URIRef("http://schema.org/" + expected),
                    vocabularies.schema_lexical_classes(Literal(text)),
                )

    def test_each_copy_records_its_source_retrieval_date_and_licence(self) -> None:
        entries = vocabularies.manifest()
        listed = {entry["file"] for entry in entries if "file" in entry}
        on_disk = {path.name for path in vocabularies.PINNED.iterdir()} - {"sources.toml"}
        self.assertEqual(listed, on_disk, "every pinned copy is listed once, and every listed copy exists")
        for entry in entries:
            with self.subTest(entry["name"]):
                self.assertTrue(entry["source"].startswith(("http://", "https://")))
                self.assertIsInstance(entry["retrieved"], datetime.date)
                licences = entry["licence"] if isinstance(entry["licence"], list) else [entry["licence"]]
                self.assertTrue(licences and all(item.startswith("https://") for item in licences))
                self.assertTrue(entry["namespaces"])


if __name__ == "__main__":
    unittest.main()
