"""Registry records are records about one thing: a `dcat:CatalogRecord` under the thing it
describes, with `foaf:primaryTopic` naming it, the registry's own values kept on the record and the winning values on
the thing; a thing only a registry knows is founded by its record."""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import build_crate as kb  # noqa: E402
from addresses import iri  # noqa: E402
from rdflib import RDF, URIRef  # noqa: E402
from test_nkr_integration import content_without_nkr, fixture_snapshot, reference_content  # noqa: E402
from vocabularies import crate_graph  # noqa: E402


def records_of(entities: dict, thing: str) -> dict:
    """The registry records about a thing, by their fragment."""
    return {
        entity_id.split("#", 1)[1]: entity
        for entity_id, entity in entities.items()
        if kb.CATALOG_RECORD in kb.as_list(entity.get("@type")) and entity.get("primaryTopic") == kb.ref(thing)
    }


def names(entity: dict) -> set[str]:
    return {item["@value"] if isinstance(item, dict) else str(item) for item in kb.as_list(entity.get("name"))}


class RegistryRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = content_without_nkr()
        cls.crate = kb.build_crate(cls.content)
        cls.entities = {entity["@id"]: entity for entity in cls.crate["@graph"]}
        cls.records = kb.records_by_thing(cls.entities)
        cls.re3data = next(item for item in cls.content["snapshots"] if item["snapshot"]["source"] == "re3data")

    def test_one_zenodo_node_holds_its_registry_records(self):
        zenodo = iri("repositories/zenodo")
        self.assertEqual(set(records_of(self.entities, zenodo)), {"knav", "fip-dashboard", "fairsharing"})
        # No second repository or resource node describes Zenodo; its registries' records hang under the one node.
        described = [
            entity_id
            for entity_id, entity in self.entities.items()
            if "#" not in entity_id
            and "Zenodo" in names(entity)
            and entity_id.startswith((iri("repositories/"), iri("resources/")))
        ]
        self.assertEqual(described, [zenodo])
        # A record is about its thing, not the same as it.
        self.assertNotIn(kb.ref(zenodo), kb.as_list(self.entities[zenodo + "#knav"].get("sameAs")))

    def test_registry_reclassification_retains_fip_classification_and_identity(self):
        for dashboard_type in ("repository", "registry"):
            content = copy.deepcopy(self.content)
            snapshot = next(row for row in content["snapshots"] if row["snapshot"]["source"] == "FIP Dashboard")
            if not any(row["id"] == "registry" for row in snapshot["resourceType"]):
                snapshot["resourceType"].append({"id": "registry", "label": {"cs": "Registry", "en": "Registry"}})
            for row in snapshot["resource"]:
                if kb.alternate_id(row, "fip-dashboard") in ("fairsharing", "nma"):
                    row["type"] = dashboard_type
            entities = {row["@id"]: row for row in kb.build_crate(content)["@graph"]}
            for identifier in ("fairsharing", "nma"):
                thing = iri("resources/" + identifier)
                with self.subTest(dashboard_type=dashboard_type, thing=thing):
                    record = records_of(entities, thing)["fip-dashboard"]
                    self.assertIn(kb.ref(kb.FIP_TERMS + "Registry"), kb.as_list(record["classification"]))
                    self.assertEqual(record["catalogueType"], kb.ref(iri("vocabularies/fd-types/" + dashboard_type)))
                    self.assertEqual(set(kb.as_list(record["@type"])), {"CreativeWork", kb.CATALOG_RECORD})
                    self.assertNotIn("acceptsDeposits", record)
                    baseline = records_of(self.entities, thing)["fip-dashboard"]
                    self.assertEqual(record.get("review"), baseline.get("review"))
                    for review in kb.ids_of(record.get("review")):
                        self.assertEqual(entities[review], self.entities[review])

    def test_one_knav_library_organisation_node(self):
        library = iri("organizations/knav")
        self.assertEqual(set(records_of(self.entities, library)), {"fip-dashboard-organization"})
        organisations = [
            entity_id
            for entity_id, entity in self.entities.items()
            if "#" not in entity_id and any(name.startswith("Knihovna A") for name in names(entity))
        ]
        self.assertEqual(organisations, [library])

    def test_a_thing_only_a_registry_knows_is_founded_by_its_record(self):
        tool = iri("resources/alphafold")  # only the KNAV catalogue lists AlphaFold
        thing, record = self.entities[tool], self.entities[tool + "#knav"]
        self.assertEqual(kb.founding_record(thing, self.records), tool + "#knav")
        self.assertNotIn("isBasedOn", thing)
        self.assertNotIn("description", thing)
        self.assertIn("description", record)
        self.assertIn("license", record)
        self.assertEqual(record["primaryTopic"], kb.ref(tool))
        # The catalogue's snapshot holds the record, not the thing.
        snapshot = self.entities["#snapshot-knav-data-management-tools-catalogue"]
        self.assertIn(kb.ref(tool + "#knav"), kb.as_list(snapshot["hasPart"]))
        self.assertNotIn(kb.ref(tool), kb.as_list(snapshot["hasPart"]))
        # The snapshot names its records; a record names the snapshot as what it rests on, never as its whole.
        self.assertNotIn("isPartOf", record)
        self.assertIn(kb.ref(snapshot["@id"]), kb.as_list(record["isBasedOn"]))

    def test_re3data_records_keep_re3data_values_beside_the_curated_ones(self):
        datarepo = iri("repositories/datarepo")
        record = records_of(self.entities, datarepo)["re3data"]
        row = next(item for item in self.re3data["repository"] if item["re3data"] == "r3d100014970")
        self.assertEqual(record["identifier"], "r3d100014970")
        self.assertEqual(names(record), {row["name"]})
        # The curated entry's name wins on the thing; the record keeps the registry's own.
        self.assertNotIn(row["name"], names(self.entities[datarepo]))
        self.assertIn(kb.ref(record["@id"]), kb.as_list(self.entities["#snapshot-re3data"]["hasPart"]))

    def test_a_repository_only_re3data_knows_is_founded_by_its_record(self):
        geomind = iri("repositories/geomind")
        thing = self.entities[geomind]
        self.assertEqual(self.records[geomind], [geomind + "#re3data"])
        self.assertEqual(kb.founding_record(thing, self.records), geomind + "#re3data")
        # A thing re3data founds keeps that, whatever other registries record it.
        lindat = self.entities[iri("repositories/lindat-clariah-cz")]
        self.assertEqual(kb.founding_record(lindat, self.records), lindat["@id"] + "#re3data")

    def test_fairsharing_and_datacite_record_the_repositories_they_annotate(self):
        zenodo = iri("repositories/zenodo")
        record = records_of(self.entities, zenodo)["fairsharing"]
        self.assertEqual(record["identifier"], "10.25504/FAIRsharing.wy4egf")
        self.assertIn(
            kb.ref("https://doi.org/10.25504/FAIRsharing.wy4egf"), kb.as_list(self.entities[zenodo]["sameAs"])
        )
        csda = iri("repositories/csda")
        self.assertEqual(records_of(self.entities, csda)["datacite"]["identifier"], "gesis.csda")

    def test_every_record_names_its_thing_and_no_thing_names_its_records(self):
        for entity_id, entity in self.entities.items():
            if kb.CATALOG_RECORD in kb.as_list(entity.get("@type")):
                thing = self.entities[entity["primaryTopic"]["@id"]]
                # The record names its thing; the thing does not name the record again.
                self.assertNotIn(kb.ref(entity_id), kb.as_list(thing.get("isBasedOn")), entity_id)
                snapshots = [item for item in kb.ids_of(entity.get("isBasedOn")) if item.startswith("#snapshot-")]
                self.assertEqual(len(snapshots), 1, entity_id)
                # A thing credits a registry through its record, never through the snapshot directly.
                self.assertNotIn(snapshots[0], kb.ids_of(thing.get("isBasedOn")), entity_id)

    def test_a_snapshot_holds_its_records_and_is_about_its_catalogue(self):
        self.assertNotIn("#knav-tools", self.entities)
        self.assertNotIn("#fers", self.entities)
        for entity_id, entity in self.entities.items():
            if kb.CATALOG_RECORD in kb.as_list(entity.get("@type")):
                snapshot = next(source for source in kb.ids_of(entity["isBasedOn"]) if source.startswith("#snapshot-"))
                self.assertIn(kb.ref(entity_id), kb.as_list(self.entities[snapshot]["hasPart"]), entity_id)
                self.assertNotIn("isPartOf", entity)
        for snapshot, catalogue in (
            ("#snapshot-knav-data-management-tools-catalogue", "resources/knav-dm-tools-catalogue"),
            ("#snapshot-fip-dashboard", "resources/fip-dashboard"),
            ("#snapshot-re3data", "resources/re3data"),
        ):
            self.assertEqual(self.entities[snapshot]["about"], kb.ref(iri(catalogue)), snapshot)

    def test_a_curated_thing_rests_on_the_guides_selection(self):
        for address in ("repositories/zenodo", "resources/argos", "organizations/cesnet"):
            thing = self.entities[iri(address)]
            source_property = "source" if address.startswith("organizations/") else "isBasedOn"
            self.assertIn(kb.ref(kb.GUIDE_SELECTION), kb.as_list(thing[source_property]), address)
            self.assertIsNone(kb.founding_record(thing, self.records), address)

    def test_node_onboarding_is_a_qualified_relation_from_the_service_platform(self):
        node = self.entities[iri("resources/eosc-cz-node")]
        self.assertEqual(node["@type"], ["Service", "Resource"])
        self.assertEqual(node["provider"], kb.ref(iri("infrastructures/e-infra-cz")))
        self.assertNotIn("member", node)
        relations = [self.entities[link["@id"]] for link in kb.as_list(node["qualifiedRelation"])]
        relation = next(item for item in relations if item["relation"] == kb.ref(iri("repositories/mbdb")))
        self.assertEqual(set(kb.as_list(relation["@type"])), {"dcat:Relationship", "CreativeWork"})
        self.assertEqual(relation["hadRole"], kb.ref(iri("vocabularies/node-roles/repository")))
        self.assertEqual(relation["nodeMilestone"], "M6")
        self.assertEqual(relation["statusAsOf"], "2026-10-16")
        self.assertEqual(relation["citation"], kb.ref(iri("resources/eosc-cz-node-charter")))
        self.assertNotIn("memberOf", relation)

    def test_foaf_names_the_topic_and_dcat_the_record_class(self):
        context = self.crate["@context"][1]
        self.assertEqual(context["primaryTopic"], kb.FOAF + "primaryTopic")
        self.assertEqual(context[kb.CATALOG_RECORD], kb.DCAT + "CatalogRecord")
        self.assertEqual(context["classification"], kb.DCTERMS + "type")

    def test_every_record_is_a_catalogue_record_and_a_creative_work_only(self):
        records = [entity for entity in self.entities.values() if kb.CATALOG_RECORD in kb.as_list(entity["@type"])]
        self.assertEqual(len({entity["@id"].rsplit("#", 1)[1] for entity in records}), 6, "every registry has records")
        for record in records:
            self.assertEqual(sorted(kb.as_list(record["@type"])), sorted(["CreativeWork", kb.CATALOG_RECORD]))
            # A class or kind the registry gives the thing is the record's classification, never its own type.
            self.assertNotIn("additionalType", record, record["@id"])
            self.assertNotIn("repositoryKind", record, record["@id"])

    def test_selecting_an_organisation_or_a_fip_class_finds_no_record(self):
        graph = crate_graph(self.crate, self.content["guide"]["guide"]["namespace"])
        records = set(graph.subjects(RDF.type, URIRef(kb.DCAT + "CatalogRecord")))
        organisations = set(graph.subjects(RDF.type, URIRef(kb.SCHEMA + "Organization")))
        self.assertTrue(organisations)
        self.assertEqual(organisations & records, set())
        fip_classed = {
            node
            for node, value in graph.subject_objects(URIRef(kb.SCHEMA + "additionalType"))
            if str(value).startswith(kb.FIP_TERMS)
        } | {node for node, cls in graph.subject_objects(RDF.type) if str(cls).startswith(kb.FIP_TERMS)}
        self.assertTrue(fip_classed)
        self.assertEqual(fip_classed & records, set())

    def test_a_registry_classifies_a_thing_on_its_record(self):
        # The FIP Dashboard classifies DataCite's metadata schema as a metadata schema; the Guide classifies it so too.
        schema = iri("resources/datacite-schema")
        metadata_schema = kb.FIP_TERMS + "Metadata-schema"
        record = records_of(self.entities, schema)["fip-dashboard"]
        self.assertEqual(record["classification"], kb.ref(metadata_schema))
        self.assertIn("fip:Metadata-schema", kb.as_list(self.entities[schema]["@type"]))
        repository = records_of(self.entities, iri("repositories/lindat-clariah-cz"))["re3data"]
        self.assertTrue(
            all(item["@id"].startswith(iri("vocabularies/")) for item in kb.as_list(repository["classification"]))
        )


class NkrRecordTests(unittest.TestCase):
    def build(self, content):
        return {entity["@id"]: entity for entity in kb.build_crate(content)["@graph"]}

    def test_reconciled_imports_keep_cross_kind_words_and_canonical_source_owners(self):
        content = content_without_nkr()
        content["snapshots"].append(fixture_snapshot())
        for identifier, native in (("git", "413"), ("provenance", "464")):
            if not any(row["id"] == identifier for row in content["glossary"]["term"]):
                content["glossary"]["term"].append(
                    {
                        "id": identifier,
                        "alternateIds": [{"scheme": "heslar", "value": native}],
                        "guideRoute": "glossary",
                        "label": {"cs": identifier, "en": identifier},
                        "url": "https://heslar.openscience.cz/heslo.php?id=" + native,
                    }
                )
        next(row for row in content["resources"] if row["id"] == "re3data")["knav"] = "re3data"
        knav = next(
            row for row in content["snapshots"] if row["snapshot"]["source"] == "KNAV Data Management Tools Catalogue"
        )
        if not any(kb.alternate_id(row, "knav") == "re3data" for row in knav["tool"]):
            knav["tool"].append(
                {
                    "id": "re3data",
                    "alternateIds": [{"scheme": "knav", "value": "re3data"}],
                    "guideRoute": "resources",
                    "name": "re3data",
                    "url": "https://www.re3data.org/",
                    "description": "Synthetic source description",
                    "steps": [],
                }
            )
        entities = self.build(content)
        for identifier in ("git", "provenance"):
            self.assertIn(iri("glossary/" + identifier), entities)
        self.assertIn(iri("resources/git"), entities)
        self.assertIn(iri("pages/provenance"), entities)
        for thing, scheme, native in (
            ("resources/re3data", "knav", "re3data"),
            ("repositories/datarepo", "nkr", "20.500.14818/sr3o5j0c"),
        ):
            record = records_of(entities, iri(thing))[scheme]
            row_kind = "tool" if scheme == "knav" else "record"
            row = next(
                row
                for snapshot in content["snapshots"]
                for row in snapshot.get(row_kind, [])
                if row["id"] == thing.split("/")[1]
            )
            self.assertEqual(row["guideRoute"], thing.split("/")[0])
            self.assertEqual(record["primaryTopic"], kb.ref(iri(thing)))
            self.assertEqual(kb.alternate_id(row, scheme), native)
            if scheme == "nkr":
                self.assertEqual(record["identifier"], native)
        for address in ("glossary/git-2", "glossary/provenance-2", "resources/re3data-2", "repositories/datarepo-2"):
            self.assertNotIn(iri(address), entities)
        api = kb.api_records(entities, content)
        self.assertIn(("git", iri("glossary/git")), api["glossary"])
        self.assertIn(("git", iri("resources/git")), api["resources"])

    def test_knav_reviewed_source_does_not_select_a_same_named_term(self):
        graph = kb.Graph()
        graph.add({"@id": "#term-git"}, "git")
        graph.add({"@id": "#source-git"}, "git")
        content = {
            "sources": [{"id": "git", "knav": "git"}],
            "resources": [],
            "repositories": [],
            "snapshots": [
                {
                    "snapshot": {"source": "KNAV Data Management Tools Catalogue"},
                    "tool": [
                        {
                            "id": "git",
                            "alternateIds": [{"scheme": "knav", "value": "git"}],
                            "name": "Git",
                            "description": "Source wording",
                            "steps": [],
                        }
                    ],
                }
            ],
        }
        kb.build_knav_tools(graph, content)
        self.assertEqual(graph.entities["#knav-git"]["sameAs"], kb.ref("#source-git"))

    def test_reviewed_knav_source_keeps_its_doi_build_key(self):
        graph = kb.Graph()
        graph.add({"@id": "https://doi.org/10.1234/source"}, "source")
        content = {
            "sources": [{"id": "source", "doi": "10.1234/source", "knav": "native"}],
            "resources": [],
            "repositories": [],
        }
        self.assertEqual(kb.knav_record_owners(graph, content), {"native": "https://doi.org/10.1234/source"})

    def test_nkr_wins_on_the_thing_and_keeps_its_own_values_on_its_record(self):
        content = reference_content()
        entities = self.build(content)
        bird = iri("repositories/czech-bioimaging")
        record = records_of(entities, bird)["nkr"]
        nkr = next(row for row in content["snapshots"][-1]["record"] if row["id"] == "czbird")
        for entity in (entities[bird], record):
            self.assertIn(str(nkr["repositoryName"]).strip(), names(entity))
            self.assertEqual(entity["serviceStatus"], entities[bird]["serviceStatus"])
        self.assertIn(kb.ref("#snapshot-nkr"), kb.as_list(record["isBasedOn"]))
        self.assertEqual(record["identifier"], "20.500.14818/srhtp4ek")
        # NKR's repository kind classifies the thing on its record; the thing's kind is the Guide's.
        self.assertTrue(record["classification"]["@id"].startswith(iri("vocabularies/repository-kinds/")))
        self.assertNotIn("repositoryKind", record)
        self.assertIn("repositoryKind", entities[bird])

    def test_the_herbarium_repository_is_founded_by_its_nkr_record(self):
        entities = self.build(reference_content())
        herbarium = iri("repositories/herbarium")
        self.assertIn("nkr", records_of(entities, herbarium))
        records = kb.records_by_thing(entities)
        self.assertEqual(kb.founding_record(entities[herbarium], records), herbarium + "#nkr")
        self.assertNotIn("isBasedOn", entities[herbarium])

    def test_an_address_free_record_founds_a_thing_in_development(self):
        content = reference_content()
        next(row for row in content["repositories"] if row["id"] == "czech-bioimaging").pop("nkr")
        entities = self.build(content)
        thing = iri("repositories/czbird")
        self.assertIn("nkr", records_of(entities, thing))
        self.assertNotIn("url", entities[thing])
        self.assertEqual(entities[thing]["serviceStatus"], kb.ref(iri("vocabularies/statuses/in-development")))
        self.assertIs(entities[thing]["acceptsDeposits"], False)


if __name__ == "__main__":
    unittest.main()
