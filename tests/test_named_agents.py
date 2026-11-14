"""Named agents resolve to reviewed things, not merely similar names. A reviewed project/service can hold both source
records; a provider is not thereby its identifier mechanism, software or hosted deployment. Shared names need review."""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import build_crate as kb  # noqa: E402
import check_duplicates  # noqa: E402
from addresses import iri  # noqa: E402


def agents(entity: dict, key: str = "publisher") -> list[str]:
    return [item["@id"] for item in kb.as_list(entity.get(key))]


class NamedAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = kb.load_content()
        cls.entities = {entity["@id"]: entity for entity in kb.build_crate(cls.content)["@graph"]}

    def build(self, content: dict) -> dict:
        return {entity["@id"]: entity for entity in kb.build_crate(content)["@graph"]}

    def test_an_organisation_named_in_its_other_language_is_that_organisation(self):
        # The roadmap names the host "Charles University"; the Guide's organisation is "Univerzita Karlova" in Czech.
        self.assertEqual(agents(self.entities[iri("infrastructures/cnc")]), [iri("organizations/cuni")])
        self.assertNotIn(iri("organizations/charles-university"), self.entities)

    def test_a_publisher_that_is_a_described_service_is_that_service(self):
        self.assertIn(iri("repositories/zenodo"), agents(self.entities[iri("resources/snd-synthetic-data")]))
        self.assertNotIn(iri("organizations/zenodo"), self.entities)
        # A thing only a registry knows is a publisher too: GitHub is the thing the KNAV catalogue's record founds.
        self.assertEqual(agents(self.entities[iri("resources/ostrails-cli")]), [iri("resources/github")])
        self.assertNotIn(iri("organizations/github"), self.entities)

    def test_a_reviewed_project_and_service_hold_both_dashboard_records(self):
        orcid = iri("resources/orcid")
        for fragment in ("#fip-dashboard", "#fip-dashboard-organization"):
            record = self.entities[orcid + fragment]
            self.assertEqual(record["primaryTopic"], kb.ref(orcid), fragment)
            self.assertNotIn(kb.ref(orcid + fragment), kb.as_list(self.entities[orcid].get("isBasedOn")))
        self.assertNotIn(iri("organizations/orcid-2"), self.entities)

    def test_no_two_described_things_share_a_name_outside_a_reviewed_group(self):
        errors, _ = check_duplicates.shared_names(self.content, check_duplicates._distinct(ROOT))
        self.assertEqual(errors, [])

    def test_a_shared_name_is_reported_unless_a_reviewed_group_explains_it(self):
        distinct = [
            group for group in check_duplicates._distinct(ROOT) if "infrastructures/cnc" not in group["addresses"]
        ]
        errors, _ = check_duplicates.shared_names(self.content, distinct)
        self.assertTrue(any("infrastructures/cnc, repositories/czech-national-corpus" in error for error in errors))

    def test_an_organisation_record_named_like_a_thing_is_listed_for_review(self):
        content = copy.deepcopy(self.content)
        resource = next(row for row in content["resources"] if row["id"] == "creative-commons")
        resource.pop("fipDashboardOrganization", None)
        resource["name"] = "Creative Commons"
        entities = self.build(content)
        # Without its reviewed handle the record founds an organisation of its own; its name joins nothing.
        self.assertIn(iri("organizations/cc"), entities)
        errors, reviews = check_duplicates.shared_names(content, check_duplicates._distinct(ROOT))
        self.assertEqual(errors, [])
        self.assertTrue(any("organizations/cc, resources/creative-commons" in review for review in reviews), reviews)

    def test_an_agent_named_by_address_or_by_a_shared_name(self):
        content = copy.deepcopy(self.content)
        resource = next(row for row in content["resources"] if row.get("operator"))
        resource["operator"]["name"] = "repositories/zenodo"
        self.assertIn(iri("repositories/zenodo"), agents(self.build(content)[iri(f"resources/{resource['id']}")]))
        resource["operator"]["name"] = "Czech National Corpus"
        with self.assertRaisesRegex(kb.ContentError, "the agent 'Czech National Corpus' names several things"):
            kb.build_crate(content)
        resource["operator"]["name"] = "resources/no-such-thing"
        with self.assertRaisesRegex(kb.ContentError, "an agent names no record: resources/no-such-thing"):
            kb.build_crate(content)


if __name__ == "__main__":
    unittest.main()
