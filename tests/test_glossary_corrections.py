"""Reviewed corrections apply to the built glossary while the snapshot stays verbatim."""

from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_api  # noqa: E402
import build_crate  # noqa: E402
import build_site  # noqa: E402
import check_content  # noqa: E402
import check_duplicates  # noqa: E402
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

    def test_replacement_may_contain_the_original_finding(self) -> None:
        glossary = {"term": [{"id": "term", "definition": "archiv"}]}
        correction = self.correction(find="archiv", replace="archivace")
        corrections.apply([correction], glossary)
        report = check_content.Report()
        check_content.check_corrections(report, {"glossary": glossary, "corrections": [correction]})
        self.assertEqual(report.errors, [])
        self.assertEqual(glossary["term"][0]["definition"], "archivace")

    def test_loader_translates_invalid_absent_and_ambiguous_corrections_for_every_entrypoint(self) -> None:
        for correction in (self.correction(field="wrong"), self.correction(find="absent"), self.correction()):
            for module in (check_content, check_duplicates, build_api, build_site):
                with self.subTest(correction=correction, entrypoint=module.__name__):
                    invalid = {"term": [{"id": "term", "definition": "typo typo"}]}

                    def fail_load(*_args, selected=correction, glossary=invalid):
                        corrections.apply([selected], glossary)

                    with mock.patch.object(build_crate, "apply_corrections", side_effect=fail_load):
                        with self.assertRaises(build_crate.ContentError):
                            build_crate.load_content()
                        error = StringIO()
                        with redirect_stderr(error):
                            self.assertEqual(module.main([]), 2)
                        self.assertIn(module.__name__, error.getvalue())
                        self.assertNotIn("Traceback", error.getvalue())

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
