"""Every authored page, repository, source and namespaced callout needs attributable coverage."""

import copy
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_crate  # noqa: E402
import check_content as cc  # noqa: E402


class ProvenanceScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = build_crate.load_content()

    def test_existing_content_has_coverage_for_all_new_kinds(self):
        content = copy.deepcopy(self.content)
        patterns = [p for action in content["provenance"] for p in action["results"]]
        items = cc.provenance_items(content)
        for key in (
            "page:software",
            "datahub-cuni",
            "genasis",
            "analyza-fair-1.2",
            "callout:sensitive-data",
            "callout.sensitive-data.rights",
        ):
            self.assertIn(key, items)
            self.assertTrue(any(cc.covered(p, key) for p in patterns), key)
        issued = cc.issued_ids(content)
        self.assertEqual(set(issued["callouts"]), set(content["identifiers"]["issued"]["callouts"]))
        self.assertEqual(set(issued["callout_items"]), set(content["identifiers"]["issued"]["callout_items"]))

    def test_page_repository_source_and_callout_changes_need_a_new_covering_action(self):
        before = copy.deepcopy(self.content)
        for key, mutate in (
            (
                "page:software",
                lambda c: c["pages"][next(i for i, p in enumerate(c["pages"]) if p["id"] == "software")].update(
                    description={"cs": "Jiný text", "en": "Changed text"}
                ),
            ),
            (
                "datahub-cuni",
                lambda c: next(r for r in c["repositories"] if r["id"] == "datahub-cuni").update(
                    name="Changed repository"
                ),
            ),
            (
                "analyza-fair-1.2",
                lambda c: next(s for s in c["sources"] if s["id"] == "analyza-fair-1.2").update(title="Changed source"),
            ),
            (
                "callout.sensitive-data.rights",
                lambda c: c["callouts"][0]["item"][-1].update(text={"cs": "Jiný text", "en": "Changed text"}),
            ),
        ):
            with self.subTest(key=key):
                content = copy.deepcopy(before)
                mutate(content)
                self.assertNotEqual(cc.item_fingerprints(before)[key], cc.item_fingerprints(content)[key])
                since = datetime(2026, 10, 16, tzinfo=UTC)
                with (
                    mock.patch.object(cc, "comparison_base", return_value=("base", since)),
                    mock.patch.object(
                        cc, "git", side_effect=lambda root, *args: "content/guide.toml" if args[0] == "ls-tree" else ""
                    ),
                    mock.patch.object(cc, "load_content", return_value=before),
                ):
                    report = cc.Report()
                    cc.check_freshness(report, content, build_crate.ROOT, "main")
                    self.assertTrue(any(error.startswith(key + ":") for error in report.errors), report.errors)
                    content["provenance"].append({"endTime": datetime(2026, 10, 17, tzinfo=UTC), "results": [key]})
                    report = cc.Report()
                    cc.check_freshness(report, content, build_crate.ROOT, "main")
                    self.assertFalse(any(error.startswith(key + ":") for error in report.errors), report.errors)


if __name__ == "__main__":
    unittest.main()
