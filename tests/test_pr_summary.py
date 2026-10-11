"""Review artifacts retain both languages and distinguish added, removed and edited content."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_crate  # noqa: E402
import pr_summary  # noqa: E402


class ReviewSummaryTests(unittest.TestCase):
    def test_changed_and_removed_names_keep_their_language_and_identity(self) -> None:
        original = {"id": "dataset.01", "statement": {"cs": "Původní otázka", "en": "Original question"}}
        edited = original | {"statement": {"cs": "Upravená otázka", "en": "Edited question"}}

        def wrap(entry: dict) -> dict:
            return {"id": entry["id"], "kind": "question", "name": pr_summary.label(entry), "content": entry}

        before = {"question:dataset.01": wrap(original), "question:dataset.02": wrap(original | {"id": "dataset.02"})}
        after = {"question:dataset.01": wrap(edited), "question:dataset.03": wrap(original | {"id": "dataset.03"})}
        changed = pr_summary.compare(before, after)
        self.assertEqual([entry["change"] for entry in changed], ["updated", "removed", "added"])
        self.assertEqual(changed[0]["name"], edited["statement"])
        self.assertEqual(changed[1]["id"], "dataset.02")
        self.assertTrue(all("content" not in entry for entry in changed))

    def test_only_explicit_revision_inputs_are_accepted(self) -> None:
        for value in ("--help", "HEAD; command", "feature", "a" * 39):
            with self.assertRaises(ValueError):
                pr_summary.revision(value)
        self.assertEqual(pr_summary.revision("a" * 40), "a" * 40)

    def test_first_content_baseline_and_current_version_are_reported(self) -> None:
        content = build_crate.load_content(ROOT / "tests/fixtures/minimal/content")
        with (
            mock.patch.object(pr_summary.check_content, "git", return_value=""),
            mock.patch.object(pr_summary.build_crate, "load_content", return_value=content),
        ):
            report = pr_summary.report(ROOT, "a" * 40, "b" * 40)
        self.assertEqual(report["head"], "b" * 40)
        self.assertTrue(all(item["change"] == "added" for item in report["items"]))
        self.assertIn("guide", [item["id"] for item in report["items"]])


if __name__ == "__main__":
    unittest.main()
