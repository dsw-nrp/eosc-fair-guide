"""Reviewed corrections apply to the built glossary while the snapshot stays verbatim."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402
import corrections  # noqa: E402


class GlossaryCorrectionTests(unittest.TestCase):
    def correction(self, **changes: object) -> dict[str, object]:
        value: dict[str, object] = {
            "id": "test-correction",
            "source": "https://example.org/source",
            "term": "term",
            "field": "definition",
            "language": "cs",
            "find": "typo",
            "replace": "correct",
            "reason": "The source has a typo.",
            "issue": "https://example.org/issues/1",
        }
        value.update(changes)
        return value

    def glossary(self) -> dict[str, object]:
        return {"term": [{"id": "term", "definition": "A typo in the source."}]}

    def test_a_correction_replaces_exactly_one_finding(self) -> None:
        glossary = self.glossary()
        corrections.apply([self.correction()], glossary)
        self.assertEqual(glossary["term"][0]["definition"], "A correct in the source.")

    def test_a_missing_or_ambiguous_finding_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "occurs 0 times"):
            corrections.apply([self.correction(find="absent")], self.glossary())
        glossary = {"term": [{"id": "term", "definition": "typo typo"}]}
        with self.assertRaisesRegex(ValueError, "occurs 2 times"):
            corrections.apply([self.correction()], glossary)

    def test_fields_and_links_are_validated(self) -> None:
        for changes in (
            {"field": "name"},
            {"language": "de"},
            {"term": "missing"},
            {"issue": "not-an-address"},
            {"source": "not-an-address"},
        ):
            errors = corrections.validate_fields([self.correction(**changes)], self.glossary())
            self.assertTrue(errors, changes)

    def test_the_real_overlay_corrects_the_built_glossary(self) -> None:
        content = build_crate.load_content()
        term = next(item for item in content["glossary"]["term"] if item["id"] == "overlay-journal")
        self.assertNotIn("Ovarlay Journal", term["definition"])
        self.assertIn("Overlay Journal", term["definition"])
        self.assertTrue(content["corrections"])


if __name__ == "__main__":
    unittest.main()
