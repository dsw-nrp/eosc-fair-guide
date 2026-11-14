"""The Guide's vocabulary declares only what holds: every domain and range is true of each use in the built graph,
including those of an established property a Guide term specialises, so a reasoner adds no class a node does not
have. Each branch of the check is proved by a planted declaration that must fail."""

from __future__ import annotations

import unittest

import test_nkr_integration
import vocabularies
from rdflib import RDF, RDFS, XSD, Graph, URIRef

build_crate = vocabularies.build_crate
SCHEMA = vocabularies.SCHEMA
ADMS_STATUS = URIRef("http://www.w3.org/ns/adms#status")
DCTERMS_DATE = URIRef("http://purl.org/dc/terms/date")


class VocabularyDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # The published graph, and the graph built with NKR's records, which are the only ones that carry some terms.
        cls.graphs = []
        for content in (build_crate.load_content(), test_nkr_integration.reference_content()):
            guide = content["guide"]["guide"]
            crate = build_crate.build_crate(content)
            cls.graphs.append(vocabularies.crate_graph(crate, guide["namespace"]))
        cls.guide = guide
        cls.base = guide["vocabularyBase"]
        cls.records = guide["recordBase"]
        cls.document = Graph().parse(data=build_crate.vocabulary_document(guide), format="turtle")

    def term(self, name: str) -> URIRef:
        return URIRef(self.base + name)

    def problems(self, vocabulary: Graph | None = None) -> list[str]:
        return vocabularies.declaration_problems(
            self.graphs, vocabulary or self.document, self.base, build_crate.EXPORT_GUIDE_TERMS
        )

    def planted(self, *added: tuple, removed: tuple = ()) -> list[str]:
        vocabulary = Graph()
        for triple in self.document:
            vocabulary.add(triple)
        for triple in removed:
            vocabulary.remove(triple)
        for triple in added:
            vocabulary.add(triple)
        found = self.problems(vocabulary)
        self.assertTrue(found, f"the planted declaration passed: {added or removed}")
        return found

    def test_every_declaration_holds_and_every_term_is_used(self) -> None:
        self.assertEqual(self.problems(), [])

    def test_a_wrong_domain_is_refused_naming_the_term_and_a_use(self) -> None:
        tier = self.term("tier")
        found = self.planted(
            (tier, RDFS.domain, URIRef(SCHEMA + "Organization")),
            removed=((tier, RDFS.domain, URIRef(SCHEMA + "Question")),),
        )
        self.assertEqual(len(found), 1, found)
        self.assertRegex(
            found[0], r"^guide:tier: its domain schema:Organization does not hold for \d+ use\(s\), such as <"
        )

    def test_a_wrong_range_is_refused(self) -> None:
        block = self.term("block")
        found = self.planted(
            (block, RDFS.range, URIRef(SCHEMA + "DefinedTermSet")),
            removed=((block, RDFS.range, URIRef(SCHEMA + "DefinedTerm")),),
        )
        self.assertTrue(any(item.startswith("guide:block: its range schema:DefinedTermSet") for item in found), found)

    def test_a_wrong_datatype_is_refused(self) -> None:
        flag = self.term("allowsNotApplicable")
        found = self.planted((flag, RDFS.range, XSD.string), removed=((flag, RDFS.range, XSD.boolean),))
        self.assertTrue(any("range xsd:string does not hold" in item and "(xsd:boolean)" in item for item in found))

    def test_the_range_of_a_specialised_property_must_hold(self) -> None:
        # A Guide term that specialises dcterms:date inherits its range, rdfs:Literal; a term whose values are nodes
        # does not satisfy it.
        tier = self.term("tier")
        found = self.planted((tier, RDFS.subPropertyOf, DCTERMS_DATE))
        self.assertTrue(
            any("guide:tier: its range rdfs:Literal, through dcterms:date" in item for item in found), found
        )

    def test_a_declaration_only_the_top_class_satisfies_is_refused(self) -> None:
        source = self.term("prefillSource")
        found = self.planted((source, RDFS.range, URIRef(SCHEMA + "Thing")))
        self.assertIn("guide:prefillSource: its rdfs:range schema:Thing says nothing", found)

    def test_a_declared_term_or_class_nothing_uses_is_refused(self) -> None:
        unused = self.term("neverUsed")
        found = self.planted((unused, RDF.type, RDF.Property))
        self.assertIn("guide:neverUsed: declared, but no graph uses it", found)
        found = self.planted((self.term("NeverUsed"), RDF.type, RDFS.Class))
        self.assertIn("guide:NeverUsed: declared, but no graph uses it", found)

    def test_terms_used_only_outside_the_content_graph_are_counted(self) -> None:
        exported = {"guideState", "guideSources"}
        self.assertTrue(exported <= set(build_crate.EXPORT_GUIDE_TERMS))
        found = vocabularies.declaration_problems(self.graphs, self.document, self.base, ())
        self.assertEqual(sorted(found), sorted(f"guide:{term}: declared, but no graph uses it" for term in exported))
        # Plant the absent use explicitly: a production NKR snapshot may already supply this property.
        without_deposits = Graph()
        for triple in self.graphs[0]:
            if triple[1] != self.term("acceptsDeposits"):
                without_deposits.add(triple)
        published = vocabularies.declaration_problems([without_deposits], self.document, self.base, exported)
        self.assertEqual(published, ["guide:acceptsDeposits: declared, but no graph uses it"])

    def test_an_rdfs_closure_adds_no_class_to_a_guide_node(self) -> None:
        # The crate publishes the vocabulary's declarations itself; read with them, the pinned vocabularies' class
        # hierarchies and the domains and ranges of the properties Guide terms specialise.
        for graph in self.graphs:
            hierarchy = vocabularies.Hierarchy(vocabularies.pinned_graph(), self.document, graph)
            guide_properties = {prop for prop in graph.predicates() if str(prop).startswith(self.base)}
            added = vocabularies.inferred_classes(graph, hierarchy, guide_properties)
            guide_nodes = {node: classes for node, classes in added.items() if str(node).startswith(self.records)}
            self.assertEqual(guide_nodes, {})

    def test_no_membership_service_or_registry_record_becomes_an_organisation_or_a_repository(self) -> None:
        organisation, repository = URIRef(SCHEMA + "Organization"), URIRef(SCHEMA + "DataCatalog")
        for graph in self.graphs:
            hierarchy = vocabularies.Hierarchy(vocabularies.pinned_graph(), self.document, graph)
            added = vocabularies.inferred_classes(graph, hierarchy, set(graph.predicates()) - {RDF.type})
            gained = {node for node, classes in added.items() if classes & {organisation, repository}}
            self.assertEqual(gained, set())

    def test_the_crate_and_the_vocabulary_document_declare_the_same(self) -> None:
        graph = self.graphs[0]
        for relation in (RDFS.domain, RDFS.range, RDFS.subPropertyOf, RDFS.subClassOf):
            with self.subTest(relation=relation):
                published = {(s, o) for s, o in graph.subject_objects(relation) if str(s).startswith(self.base)}
                document = {(s, o) for s, o in self.document.subject_objects(relation) if str(s).startswith(self.base)}
                self.assertEqual(published, document)

    def test_schema_org_uses_stay_within_their_domains_and_ranges(self) -> None:
        self.assertEqual(vocabularies.schema_problems(self.graphs, self.base), [])

    def test_each_relation_and_term_set_membership_is_stated_once(self) -> None:
        self.assertEqual(vocabularies.relation_problems(self.graphs, self.base), [])

    def test_the_corrected_declarations(self) -> None:
        # The findings of the graph-model review, each as the vocabulary now states it.
        def declared(name: str, relation: URIRef) -> set[str]:
            return {vocabularies.short(value, self.base) for value in self.document.objects(self.term(name), relation)}

        self.assertEqual(declared("assessmentContext", RDFS.subPropertyOf), set())
        self.assertEqual(declared("assessmentContext", RDFS.range), {"xsd:boolean"})
        self.assertEqual(declared("disclosureLevel", RDFS.subPropertyOf), set())
        self.assertEqual(declared("block", RDFS.range), {"schema:DefinedTerm"})
        self.assertEqual(declared("infrastructureCharacter", RDFS.range), {"schema:DefinedTerm"})
        self.assertEqual(declared("nodeMilestone", RDFS.domain), {"dcat:Relationship"})
        for name in ("nodeState", "nodeStateSince"):
            self.assertEqual(declared(name, RDFS.domain), {"schema:Service"})
        for name in ("statusAsOf", "operatedBy", "modelKind", "implementationLayers", "note"):
            self.assertEqual(declared(name, RDFS.domain), set(), name)
        for name in ("nameTranslation", "descriptionTranslation", "quotedDefinition"):
            self.assertEqual(declared(name, RDFS.domain), {"schema:DefinedTerm"}, name)
        for name in ("rdmkitRecord", "trainingSearch", "lookup"):
            self.assertEqual(declared(name, RDFS.range), set(), name)
        self.assertEqual(declared("serviceStatus", RDFS.subPropertyOf), {"adms:status"})


if __name__ == "__main__":
    unittest.main()
