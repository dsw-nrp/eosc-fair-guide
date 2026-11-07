"""One identity projection: every Guide record has one address and one IRI, which the API, the page and the crate
share."""

import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import build_api  # noqa: E402
import build_crate as kb  # noqa: E402
from addresses import GUIDE_NAMESPACE, address_of, iri  # noqa: E402

# Families whose names the build used to fill with the identifier; none of them may repeat it any more.
GENERATED_NAMES = ("clauses", "advice", "questions", "pages", "callouts")
BASE = GUIDE_NAMESPACE + "id/"


class CatalogueAddressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = kb.load_content()
        cls.graph = kb.Graph()
        cls.crate = kb.build_crate(cls.content, cls.graph)
        cls.entities = {entry["@id"]: entry for entry in cls.crate["@graph"]}

    def addresses(self, entities=None):
        """Every published record's address, read from its IRI."""
        return {
            entity_id: kb.record_address(entity_id, BASE)
            for entity_id in (entities or self.entities)
            if kb.record_address(entity_id, BASE)
        }

    def test_every_guide_record_has_an_iri_in_the_namespace_and_parts_sit_under_it(self):
        records = self.addresses()
        self.assertEqual(records, self.graph.addresses)
        self.assertEqual(len(records), len(set(records.values())))
        for address in records.values():
            kind, _, identifier = kb.split_address(address)
            self.assertIn(kind, kb.KINDS)
            if kind != "vocabularies":  # a term's code is its vocabulary's own; minted IDs are bounded
                self.assertLessEqual(len(identifier), 32, address)
            self.assertTrue(all(kb.API_ID.fullmatch(part) for part in address.split("/")), address)
        for entity_id in self.entities:
            if "#" in entity_id and entity_id.startswith(BASE):
                self.assertIn(entity_id.split("#")[0], self.entities, f"{entity_id} is a part of no record")
        local = [entity_id for entity_id in self.entities if entity_id.startswith("#")]
        self.assertTrue(all(kb.CRATE_LOCAL.match(entity_id) for entity_id in local), local)
        self.assertNotIn("catalogueAddress", json.dumps(self.crate))

    def test_no_identifier_carries_a_collision_counter(self):
        records = set(self.addresses().values())
        for address in records:
            counted = re.fullmatch(r"(.+)-(\d+)", address)
            self.assertFalse(counted and counted[1] in records, f"{address} counts a collision")

    def test_no_name_only_repeats_the_identifier(self):
        self.assertNotIn("name", kb.prune({"@id": "#x", "identifier": "A.F1.N1"}))
        self.assertEqual(kb.prune({"@id": "#x", "identifier": "x", "headline": "H"})["name"], "H")
        for entity_id, entity in self.entities.items():
            address = kb.guide_address(entity_id, BASE) or ""
            if address.split("/")[0] in GENERATED_NAMES and entity.get("identifier"):
                names = [
                    item.get("@value") if isinstance(item, dict) else item for item in kb.as_list(entity.get("name"))
                ]
                self.assertNotIn(entity["identifier"], names, entity_id)

    def test_api_files_and_records_follow_the_address(self):
        api = build_api.Api(self.crate, self.content)
        for members in api.records.values():
            for _, entity_id in members:
                self.assertEqual(api.paths[entity_id], f"api/{address_of(entity_id)}.json")
        self.assertEqual(api.paths[iri("resources/datacite")], "api/resources/datacite.json")
        self.assertEqual(api.paths[iri("repositories/zenodo")], "api/repositories/zenodo.json")

    def test_source_id_changes_do_not_reissue_our_address(self):
        content = copy.deepcopy(self.content)
        tool = next(
            row for snapshot in content["snapshots"] for row in snapshot.get("tool", []) if row["id"] == "github"
        )
        tool["alternateIds"] = [{"scheme": "knav", "value": "changed-upstream-id"}]
        tool["name"] = "Changed title"
        entities = {entry["@id"] for entry in kb.build_crate(content)["@graph"]}
        self.assertIn(iri("resources/github"), entities)

    def test_reclassification_keeps_the_issued_address(self):
        content = copy.deepcopy(self.content)
        next(row for row in content["resources"] if row["id"] == "datacite")["type"] = "tool"
        entities = {entry["@id"]: entry for entry in kb.build_crate(content)["@graph"]}
        self.assertEqual(
            entities[iri("resources/datacite")]["resourceType"], kb.ref(iri("vocabularies/resource-types/tool"))
        )

    def test_authoritative_iri_changes_cannot_change_our_identity(self):
        content = copy.deepcopy(self.content)
        principle = next(row for row in content["principles"] if row["id"] == "F1")
        principle["iri"] = "https://vocabulary.example.org/F1"
        organization = content["guide"]["organization"][0]
        organization["ror"] = "https://ror.org/changed"
        entities = {entry["@id"]: entry for entry in kb.build_crate(content)["@graph"]}
        self.assertEqual(entities[iri("principles/F1")]["sameAs"], kb.ref(principle["iri"]))
        self.assertEqual(entities[iri("organizations/" + organization["id"])]["sameAs"], kb.ref(organization["ror"]))

    def test_all_source_alternates_are_typed_and_published_as_parts(self):
        for entity_id, entity in self.entities.items():
            for reference in kb.as_list(entity.get("alternateIdentifier")):
                alternate = self.entities[reference["@id"]]
                self.assertEqual(alternate["@type"], "PropertyValue")
                self.assertTrue(reference["@id"].startswith(entity_id.split("#")[0] + "#"), reference["@id"])
                self.assertTrue(alternate.get("propertyID") and alternate.get("value"))

    def test_title_changes_do_not_reissue_addresses(self):
        content = copy.deepcopy(self.content)
        # A tool no agent is named after: renaming GitHub would also change which thing its publishers name.
        tool = next(
            row for snapshot in content["snapshots"] for row in snapshot.get("tool", []) if row["id"] == "alphafold"
        )
        tool["name"] = "A different source label"
        entities = {entry["@id"]: entry for entry in kb.build_crate(content)["@graph"]}
        self.assertEqual(set(self.addresses(entities).values()), set(self.addresses().values()))

    def test_duplicate_unsafe_and_missing_owned_ids_are_refused(self):
        for value in ("../bad", "git", "the-data-tool", ""):
            content = copy.deepcopy(self.content)
            tool = next(
                row for snapshot in content["snapshots"] for row in snapshot.get("tool", []) if row["id"] == "github"
            )
            tool["id"] = value
            with self.assertRaises(kb.ContentError):
                kb.build_crate(content)

    def test_api_publishes_no_legacy_documents_and_retains_external_iris(self):
        api = build_api.Api(self.crate, self.content)
        files = api.files()
        self.assertIn("api/resources/github.json", files)
        self.assertNotIn("api/res/tool/github.json", files)
        self.assertNotIn("api/metrics/dataset.01.json", files)
        self.assertNotIn("catalogue", self.content["identifiers"])
        principle = api.record("principles", "F1", iri("principles/F1"))
        self.assertIn(kb.FAIR_PRINCIPLES + "F1", principle["sameAs"])

    def test_a_registry_record_sits_under_the_thing_it_describes(self):
        zenodo = iri("repositories/zenodo")
        self.assertIn(zenodo + "#knav", self.entities)
        self.assertNotIn(iri("resources/zenodo"), self.entities)
        self.assertIn(iri("organizations/cesnet") + "#fip-dashboard-organization", self.entities)


if __name__ == "__main__":
    unittest.main()
