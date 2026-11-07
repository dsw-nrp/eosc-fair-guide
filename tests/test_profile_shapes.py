"""Every shape of the profile selects real nodes by what they are and refuses one that loses what the shape requires.

A shape that selects its nodes by the property it requires cannot fail: a node that loses the property leaves the
shape. Each shape here selects by class, a target node or what the node is, and this test removes every required
property from a real node of every shape, in one mutated copy of the crate, and expects a violation for each."""

from __future__ import annotations

import unittest

import vocabularies
from addresses import iri
from pyshacl import validate
from rdflib import RDF, BNode, Graph, Literal, URIRef
from rdflib.namespace import SH

build_crate = vocabularies.build_crate
SCHEMA = vocabularies.SCHEMA


def focus_nodes(shapes: Graph, data: Graph, shape: URIRef) -> set:
    """The nodes a shape selects in the data, by each of its targets."""
    nodes: set = set()
    for cls in shapes.objects(shape, SH.targetClass):
        nodes |= set(data.subjects(RDF.type, cls))
    nodes |= set(shapes.objects(shape, SH.targetNode)) & set(data.subjects())
    for prop in shapes.objects(shape, SH.targetSubjectsOf):
        nodes |= set(data.subjects(prop, None))
    for prop in shapes.objects(shape, SH.targetObjectsOf):
        nodes |= {value for value in data.objects(None, prop) if not isinstance(value, Literal)}
    for target in shapes.objects(shape, SH.target):
        query = shapes.value(target, SH.select)
        if query is not None:
            nodes |= {row[0] for row in data.query(str(query))}
    return nodes


def required(shapes: Graph, shape: URIRef) -> list[URIRef]:
    """The properties a shape requires of its nodes directly: a property shape with a single property path and a
    minimum count, plain or qualified."""
    found = []
    for prop in shapes.objects(shape, SH.property):
        path = shapes.value(prop, SH.path)
        minimum = shapes.value(prop, SH.minCount) or shapes.value(prop, SH.qualifiedMinCount)
        if isinstance(path, URIRef) and minimum is not None and int(minimum) >= 1:
            found.append(path)
    return found


class ProfileShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        content = build_crate.load_content()
        namespace = content["guide"]["guide"]["namespace"]
        cls.terms = content["guide"]["guide"]["vocabularyBase"]
        cls.data = vocabularies.crate_graph(build_crate.build_crate(content), namespace)
        cls.shapes = Graph()
        for path, text in build_crate.profile_shapes(vocabularies.ROOT, namespace).items():
            if "/must/" in path:
                cls.shapes.parse(data=text, format="turtle")
        cls.node_shapes = sorted(
            shape for shape in cls.shapes.subjects(RDF.type, SH.NodeShape) if not isinstance(shape, BNode)
        )

    def results(self, graph: Graph) -> set[tuple]:
        """Each violation as (focus node, path or None, the shape that raised it)."""
        conforms, report, _ = validate(graph, shacl_graph=self.shapes, advanced=True)
        found = set()
        for result in report.subjects(RDF.type, SH.ValidationResult):
            found.add((report.value(result, SH.focusNode), report.value(result, SH.resultPath)))
        return found

    def mutated(self, removals: list[tuple]) -> Graph:
        graph = Graph()
        for triple in self.data:
            graph.add(triple)
        for node, path in removals:
            for value in list(graph.objects(node, path)):
                graph.remove((node, path, value))
        return graph

    def test_the_real_crate_conforms_to_every_shape(self) -> None:
        conforms, _, report = validate(self.data, shacl_graph=self.shapes, advanced=True)
        self.assertTrue(conforms, report)

    def test_every_shape_selects_real_nodes(self) -> None:
        for shape in self.node_shapes:
            with self.subTest(shape=str(shape)):
                self.assertTrue(focus_nodes(self.shapes, self.data, shape), f"{shape} selects no node of the crate")

    def test_every_required_property_of_every_shape_is_enforced(self) -> None:
        mutations: list[tuple] = []
        for shape in self.node_shapes:
            nodes = sorted(focus_nodes(self.shapes, self.data, shape), key=str)
            for path in required(self.shapes, shape):
                node = next((node for node in nodes if (node, path, None) in self.data), None)
                self.assertIsNotNone(node, f"{shape}: no node of the crate has {path}")
                mutations.append((shape, node, path))
        found = self.results(self.mutated([(node, path) for _, node, path in mutations]))
        missed = [(str(shape), str(node), str(path)) for shape, node, path in mutations if (node, path) not in found]
        self.assertEqual(missed, [])
        # The shapes the graph-model review found inert, and those a node could leave by losing its kind.
        covered = {
            (str(shape).rsplit("/", 1)[-1], str(path).rsplit("#", 1)[-1].rsplit("/", 1)[-1])
            for shape, _, path in mutations
        }
        for case in (
            ("ImplementationModelItem", "modelKind"),
            ("ImplementationSeam", "transfer"),
            ("ImplementationExample", "scope"),
            ("ApprovedModelManuscript", "preparationStatus"),
            ("Test", "about"),
            ("Clause", "clauseKind"),
            ("Repository", "repositoryKind"),
        ):
            self.assertIn(case, covered)

    def test_a_resource_without_its_type_is_refused(self) -> None:
        resource = URIRef(iri("resources/argos"))
        types = (URIRef(self.terms + "resourceType"), URIRef(self.terms + "guideType"))
        self.assertTrue(any((resource, prop, None) in self.data for prop in types))
        found = self.results(self.mutated([(resource, prop) for prop in types]))
        self.assertIn((resource, None), found)

    def test_a_repository_without_its_address_or_an_nkr_page_is_refused(self) -> None:
        repository = URIRef(iri("repositories/zenodo"))
        found = self.results(self.mutated([(repository, URIRef(SCHEMA + "url"))]))
        self.assertIn((repository, None), found)

    def test_a_repository_without_a_curated_source_or_registry_record_is_refused(self) -> None:
        repository = URIRef(iri("repositories/zenodo"))
        topic = URIRef("http://xmlns.com/foaf/0.1/primaryTopic")
        records = list(self.data.subjects(topic, repository))
        self.assertTrue(records)
        mutations = [(repository, URIRef(SCHEMA + "isBasedOn"))]
        mutations += [(record, topic) for record in records]
        found = self.results(self.mutated(mutations))
        self.assertIn((repository, None), found)


if __name__ == "__main__":
    unittest.main()
