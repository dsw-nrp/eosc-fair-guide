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

    def test_one_zenodo_node_holds_its_knav_and_fip_dashboard_records(self):
        zenodo = iri("repositories/zenodo")
        self.assertEqual(set(records_of(self.entities, zenodo)), {"knav", "fip-dashboard"})
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
        # The catalogue's list of the KNAV records names the record, not the thing.
        self.assertIn(kb.ref(tool + "#knav"), kb.as_list(self.entities["#knav-tools"]["hasPart"]))

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
