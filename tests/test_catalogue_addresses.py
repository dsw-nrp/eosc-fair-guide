"""Guide-issued addresses agree across the API, browser configuration and persistent record ownership."""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_api  # noqa: E402
import build_crate as kb  # noqa: E402


class CatalogueAddressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = kb.load_content()
        cls.crate = kb.build_crate(cls.content)
        cls.entities = {entry["@id"]: entry for entry in cls.crate["@graph"]}

    def test_registered_addresses_are_unique_safe_and_agree_with_api_records(self):
        addresses = kb.catalogue_addresses(self.entities, self.content)
        self.assertEqual(len(addresses), len(set(addresses.values())))
        api = build_api.Api(self.crate, self.content)
        for entity_id, address in addresses.items():
            self.assertLessEqual(len(address.rsplit("/", 1)[-1]), 32)
            self.assertEqual(api.paths[entity_id], f"api/{address}.json")
            self.assertEqual(self.entities[entity_id]["catalogueAddress"], address)
            self.assertTrue(all(kb.API_ID.fullmatch(part) for part in address.split("/")))
        self.assertEqual(addresses["#resource-datacite"], "res/srv/datacite")
        self.assertEqual(addresses["#repository-zenodo"], "repo/gen/zenodo")

    def test_source_id_changes_do_not_reissue_our_address(self):
        content = copy.deepcopy(self.content)
        tool = next(
            row for snapshot in content["snapshots"] for row in snapshot.get("tool", []) if row["id"] == "github"
        )
        tool["alternateIds"] = [{"scheme": "knav", "value": "changed-upstream-id"}]
        tool["name"] = "Changed title"
        entities = {entry["@id"]: entry for entry in kb.build_crate(content)["@graph"]}
        self.assertEqual(entities["#knav-github"]["catalogueAddress"], "res/tool/github")

    def test_reclassification_keeps_the_issued_address(self):
        content = copy.deepcopy(self.content)
        next(row for row in content["resources"] if row["id"] == "datacite")["type"] = "tool"
        entity = next(entry for entry in kb.build_crate(content)["@graph"] if entry["@id"] == "#resource-datacite")
        self.assertEqual(entity["catalogueAddress"], "res/srv/datacite")
        self.assertEqual(entity["resourceType"], kb.ref("#rtype-tool"))

    def test_authoritative_iri_changes_cannot_change_our_identity(self):
        content = copy.deepcopy(self.content)
        principle = next(row for row in content["principles"] if row["id"] == "F1")
        principle["iri"] = "https://vocabulary.example.org/F1"
        organization = content["guide"]["organization"][0]
        organization["ror"] = "https://ror.org/changed"
        entities = {entry["@id"]: entry for entry in kb.build_crate(content)["@graph"]}
        self.assertEqual(entities[kb.principle_iri("F1")]["catalogueAddress"], "pr/F1")
        self.assertEqual(entities[kb.principle_iri("F1")]["sameAs"], kb.ref(principle["iri"]))
        entity_id = "#org-" + organization["id"]
        self.assertEqual(entities[entity_id]["catalogueAddress"], self.entities[entity_id]["catalogueAddress"])
        self.assertEqual(entities[entity_id]["sameAs"], kb.ref(organization["ror"]))

    def test_all_source_alternates_are_typed_and_published_separately(self):
        for entity_id, row in kb.catalogue_records(self.content).items():
            self.assertNotIn("guideId", row)
            entity = self.entities.get(entity_id)
            if not entity:
                continue  # A curated record already represents this source record.
            self.assertEqual(entity["identifier"], row["id"])
            for alternate in row.get("alternateIds", []):
                self.assertEqual(set(alternate), {"scheme", "value"})
                self.assertIn(
                    (alternate["scheme"], alternate["value"]),
                    [
                        (self.entities[ref["@id"]]["propertyID"], self.entities[ref["@id"]]["value"])
                        for ref in kb.as_list(entity.get("alternateIdentifier"))
                    ],
                )

    def test_title_changes_do_not_reissue_addresses(self):
        entities = copy.deepcopy(self.entities)
        entities["#knav-github"]["name"] = "A different source label"
        self.assertEqual(
            kb.catalogue_addresses(entities, self.content), kb.catalogue_addresses(self.entities, self.content)
        )

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
        self.assertIn("api/res/tool/github.json", files)
        self.assertNotIn("api/resources/knav.github.json", files)
        self.assertNotIn("api/metrics/dataset.01.json", files)
        self.assertNotIn("catalogue", self.content["identifiers"])
        principle = api.record("principles", "F1", kb.principle_iri("F1"))
        self.assertIn(kb.FAIR_PRINCIPLES + "F1", principle["sameAs"])

    def test_canonical_api_record_publishes_the_issued_address(self):
        api = build_api.Api(self.crate, self.content)
        document = api.record("resources", "knav.github", "#knav-github")
        self.assertEqual(document["catalogueAddress"], self.entities["#knav-github"]["catalogueAddress"])
        self.assertEqual(document["@id"], "github.json")
        json.dumps(document)


if __name__ == "__main__":
    unittest.main()
