"""Registry records are records about one thing (design.md, decision 4): a `dcat:CatalogRecord` under the thing it
describes, with `foaf:primaryTopic` naming it, the registry's own values kept on the record and the winning values on
the thing; a thing only a registry knows is founded by its record."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import build_crate as kb  # noqa: E402
from addresses import iri  # noqa: E402
from test_nkr_integration import reference_content  # noqa: E402


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
        cls.content = kb.load_content()
        cls.crate = kb.build_crate(cls.content)
        cls.entities = {entity["@id"]: entity for entity in cls.crate["@graph"]}
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

    def test_one_knav_library_organisation_node(self):
        library = iri("organizations/knav")
        self.assertEqual(set(records_of(self.entities, library)), {"fip-dashboard"})
        organisations = [
            entity_id
            for entity_id, entity in self.entities.items()
            if "#" not in entity_id and any(name.startswith("Knihovna A") for name in names(entity))
        ]
        self.assertEqual(organisations, [library])

    def test_a_thing_only_a_registry_knows_is_founded_by_its_record(self):
        tool = iri("resources/alphafold")  # only the KNAV catalogue lists AlphaFold
        thing, record = self.entities[tool], self.entities[tool + "#knav"]
        self.assertEqual(kb.as_list(thing["isBasedOn"])[0], kb.ref(tool + "#knav"))
        self.assertNotIn("description", thing)
        self.assertIn("description", record)
        self.assertIn("license", record)
        self.assertEqual(record["primaryTopic"], kb.ref(tool))
        # The catalogue's snapshot holds the record, not the thing.
        snapshot = self.entities["#snapshot-knav-data-management-tools-catalogue"]
        self.assertIn(kb.ref(tool + "#knav"), kb.as_list(snapshot["hasPart"]))
        self.assertNotIn(kb.ref(tool), kb.as_list(snapshot["hasPart"]))
        self.assertEqual(record["isPartOf"], kb.ref(snapshot["@id"]))

    def test_re3data_records_keep_re3data_values_beside_the_curated_ones(self):
        datarepo = iri("repositories/datarepo")
        record = records_of(self.entities, datarepo)["re3data"]
        row = next(item for item in self.re3data["repository"] if item["re3data"] == "r3d100014970")
        self.assertEqual(record["identifier"], "r3d100014970")
        self.assertEqual(names(record), {row["name"]})
        # The curated entry's name wins on the thing; the record keeps the registry's own.
        self.assertNotIn(row["name"], names(self.entities[datarepo]))
        self.assertEqual(kb.as_list(record["isPartOf"]), [kb.ref("#snapshot-re3data")])

    def test_a_repository_only_re3data_knows_is_founded_by_its_record(self):
        geomind = iri("repositories/geomind")
        thing = self.entities[geomind]
        self.assertEqual(kb.as_list(thing["isBasedOn"]), [kb.ref(geomind + "#re3data")])
        self.assertEqual(kb.founding_record(thing), geomind + "#re3data")
        # A thing re3data founds keeps that, whatever other registries record it.
        lindat = self.entities[iri("repositories/lindat-clariah-cz")]
        self.assertEqual(kb.founding_record(lindat), lindat["@id"] + "#re3data")

    def test_fairsharing_and_datacite_record_the_repositories_they_annotate(self):
        zenodo = iri("repositories/zenodo")
        record = records_of(self.entities, zenodo)["fairsharing"]
        self.assertEqual(record["identifier"], "10.25504/FAIRsharing.wy4egf")
        self.assertIn(
            kb.ref("https://doi.org/10.25504/FAIRsharing.wy4egf"), kb.as_list(self.entities[zenodo]["sameAs"])
        )
        csda = iri("repositories/csda")
        self.assertEqual(records_of(self.entities, csda)["datacite"]["identifier"], "gesis.csda")

    def test_every_thing_rests_on_each_of_its_records(self):
        for entity_id, entity in self.entities.items():
            if kb.CATALOG_RECORD in kb.as_list(entity.get("@type")):
                thing = self.entities[entity["primaryTopic"]["@id"]]
                self.assertIn(kb.ref(entity_id), kb.as_list(thing.get("isBasedOn")), entity_id)
                snapshots = [item for item in kb.ids_of(entity.get("isBasedOn")) if item.startswith("#snapshot-")]
                self.assertEqual(len(snapshots), 1, entity_id)
                # A thing credits a registry through its record, never through the snapshot directly.
                self.assertNotIn(snapshots[0], kb.ids_of(thing.get("isBasedOn")), entity_id)

    def test_a_snapshot_holds_its_records_and_is_about_its_catalogue(self):
        self.assertNotIn("#knav-tools", self.entities)
        self.assertNotIn("#fers", self.entities)
        for entity_id, entity in self.entities.items():
            if kb.CATALOG_RECORD in kb.as_list(entity.get("@type")):
                snapshot = self.entities[entity["isPartOf"]["@id"]]
                self.assertIn(kb.ref(entity_id), kb.as_list(snapshot["hasPart"]), entity_id)
        for snapshot, catalogue in (
            ("#snapshot-knav-data-management-tools-catalogue", "resources/knav-dm-tools-catalogue"),
            ("#snapshot-fip-dashboard", "resources/fip-dashboard"),
            ("#snapshot-re3data", "resources/re3data"),
        ):
            self.assertEqual(self.entities[snapshot]["about"], kb.ref(iri(catalogue)), snapshot)

    def test_a_curated_thing_rests_on_the_guides_selection(self):
        for address in ("repositories/zenodo", "resources/argos", "organizations/cesnet"):
            thing = self.entities[iri(address)]
            self.assertIn(kb.ref(kb.GUIDE_SELECTION), kb.as_list(thing["isBasedOn"]), address)
            self.assertIsNone(kb.founding_record(thing), address)

    def test_foaf_names_the_topic_and_dcat_the_record_class(self):
        context = self.crate["@context"][1]
        self.assertEqual(context["primaryTopic"], kb.FOAF + "primaryTopic")
        self.assertEqual(context[kb.CATALOG_RECORD], kb.DCAT + "CatalogRecord")


class NkrRecordTests(unittest.TestCase):
    def build(self, content):
        return {entity["@id"]: entity for entity in kb.build_crate(content)["@graph"]}

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

    def test_the_herbarium_repository_is_founded_by_its_nkr_record(self):
        entities = self.build(reference_content())
        herbarium = iri("repositories/herbarium")
        self.assertIn("nkr", records_of(entities, herbarium))
        self.assertEqual(kb.as_list(entities[herbarium]["isBasedOn"])[0], kb.ref(herbarium + "#nkr"))

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
