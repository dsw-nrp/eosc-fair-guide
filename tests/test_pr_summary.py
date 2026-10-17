"""Review artifacts retain both languages and distinguish added, removed and edited content."""

from __future__ import annotations

import json
import sys
import tempfile
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
        calls: list[tuple[str, ...]] = []

        def git(_root: Path, *args: str) -> str:
            calls.append(args)
            return "c" * 40 + "\n" if args[0] == "merge-base" else ""

        with (
            mock.patch.object(pr_summary.check_content, "git", side_effect=git),
            mock.patch.object(pr_summary.build_crate, "load_content", return_value=content),
        ):
            report = pr_summary.report(ROOT, "a" * 40, "b" * 40)
        self.assertEqual(report["head"], "b" * 40)
        self.assertTrue(all(item["change"] == "added" for item in report["items"]))
        self.assertIn("guide", [item["id"] for item in report["items"]])
        # The base content is read where the branch left the base, as the paradata check compares it.
        self.assertEqual(calls[0], ("merge-base", "a" * 40, "HEAD"))
        self.assertEqual(calls[1], ("ls-tree", "-r", "--name-only", "c" * 40, "content/"))

    def test_more_than_200_changes_keep_a_complete_list_beside_the_bounded_summary(self) -> None:
        items = [
            {"id": f"dataset.{n:03}", "kind": "question", "name": {"cs": "x", "en": "x"}, "change": "added"}
            for n in range(250)
        ]
        complete = {"formatVersion": 1, "base": "a" * 40, "head": "b" * 40, "total": 250, "items": items}
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(pr_summary, "report", return_value=complete):
            output = Path(temp) / "summary.json"
            with mock.patch("builtins.print"):
                self.assertEqual(pr_summary.main(["--output", str(output)]), 0)
            bounded = json.loads(output.read_text(encoding="utf-8"))
            listed = json.loads((Path(temp) / "changes.json").read_text(encoding="utf-8"))
        self.assertEqual((bounded["total"], len(bounded["items"]), bounded["truncated"]), (250, 200, True))
        self.assertEqual(bounded["complete"], "changes.json")
        self.assertEqual(listed["items"], items, "the complete list is not truncated")
        small = pr_summary.summary(complete | {"total": 3, "items": items[:3]})
        self.assertFalse(small["truncated"])


if __name__ == "__main__":
    unittest.main()
