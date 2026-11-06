"""The duplicate check attaches every record to exactly one thing (design.md, decision 5). Shared keys still report a
duplicate, the authoritative ones with their safe link as the fix; a similar host or name only asks a person to look,
and accepted groups keep their reasons."""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_crate  # noqa: E402
import check_duplicates  # noqa: E402

OWNCLOUD = "knav:cesnet-owncloud may describe resource:cesnet-owncloud"


class DuplicateAttachmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = build_crate.load_content()
        cls.accepted = check_duplicates._accepted(build_crate.ROOT)

    def check(self, content):
        return check_duplicates.check(content, self.accepted)

    def test_the_linked_owncloud_record_needs_no_review(self):
        report = self.check(self.content)
        self.assertEqual(report.errors, [])
        self.assertFalse(any(review.startswith(OWNCLOUD) for review in report.reviews))

    def test_an_unlinked_owncloud_record_is_reported_for_review_and_never_fixed(self):
        content = copy.deepcopy(self.content)
        next(row for row in content["resources"] if row["id"] == "cesnet-owncloud").pop("knav")
        report = self.check(content)
        review = next(review for review in report.reviews if review.startswith(OWNCLOUD))
        self.assertIn("cesnet.cz", review)
        self.assertIn("owncloud", review)
        self.assertEqual(report.errors, [], "a similar host or name joins nothing and fails nothing")
        self.assertFalse(any(suggestion.entry == "resource:cesnet-owncloud" for suggestion in report.suggestions))

    def test_an_authoritative_shared_key_keeps_its_safe_fix(self):
        content = copy.deepcopy(self.content)
        resource = next(row for row in content["resources"] if row["id"] == "cesnet-owncloud")
        resource.pop("knav")
        resource["url"] = "https://owncloud.cesnet.cz/"
        report = self.check(content)
        self.assertTrue(any("describes one thing" in error for error in report.errors), report.errors)
        fix = next(suggestion for suggestion in report.suggestions if suggestion.entry == "resource:cesnet-owncloud")
        self.assertEqual((fix.field_name, fix.value, fix.safe), ("knav", "owncloud", True))

    def test_an_accepted_group_stays_accepted_and_is_not_reviewed(self):
        accepted = [group for group in self.accepted if "knav:jupyterhub" in group.get("entries", [])]
        self.assertTrue(accepted, "the accepted KNAV group is in content/duplicates.toml")
        report = self.check(self.content)
        self.assertFalse(any("accepted group" in error for error in report.errors))
        members = set(accepted[0]["entries"])
        self.assertFalse(
            any({part.split(" ")[0] for part in review.split(" may describe ")} <= members for review in report.reviews)
        )

    def test_the_report_names_the_reviews_apart_from_the_errors(self):
        payload = check_duplicates.report_payload(self.check(self.content))
        self.assertEqual(payload["errors"], [])
        self.assertIsInstance(payload["reviews"], list)


if __name__ == "__main__":
    unittest.main()
