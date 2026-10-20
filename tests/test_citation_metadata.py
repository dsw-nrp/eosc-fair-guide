"""CFF correctness and Zenodo consumer compatibility are independent release gates."""

import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_citation_metadata as citation  # noqa: E402
import release_versions  # noqa: E402


class CitationMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for path in release_versions.FILES:
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, destination)
        self.zenodo = json.loads((self.root / ".zenodo.json").read_text(encoding="utf-8"))

    def write(self, data):
        (self.root / ".zenodo.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_current_structured_affiliations_and_version_pass_without_network_or_writes(self):
        before = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with patch("requests.sessions.Session.request", side_effect=AssertionError("No network")):
            self.assertEqual(citation.check(self.root), [])
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()})

    def test_invalid_cff_is_not_hidden_by_matching_version_and_date(self):
        path = self.root / "CITATION.cff"
        path.write_text(
            path.read_text(encoding="utf-8").replace("cff-version: 1.2.0", "cff-version: 9.9.9"), encoding="utf-8"
        )
        self.assertIn("CITATION.cff schema", "\n".join(citation.check(self.root)))

    def test_import_profile_rejects_unsupported_shapes_and_unknown_keys(self):
        for edit in (
            {"license": ["MIT", "CC-BY-4.0"]},
            {"publication_date": "2026-99-99"},
            {"creators": []},
            {"upload_type": "poster"},
            {"typo_field": "lost"},
        ):
            with self.subTest(edit=edit):
                self.write({**self.zenodo, **edit})
                self.assertTrue(citation.check(self.root))

    def test_shared_software_fields_and_credit_must_agree(self):
        for edit in (
            {"version": "2.0.0"},
            {"publication_date": "2000-01-01"},
            {"title": "Different title"},
            {"description": "Unrelated abstract"},
            {"keywords": ["unrelated"]},
            {"license": "CC-BY-4.0"},
            {"creators": [{"name": "A report author", "orcid": "0000-0001-6491-2947"}]},
        ):
            self.write({**self.zenodo, **edit})
            self.assertTrue(citation.check(self.root), edit)

    def test_ror_ids_and_names_remain_reviewed_and_scalar_does_not_override_them(self):
        for field, value in [("id", "0287jta43"), ("name", "Unreviewed institution")]:
            data = copy.deepcopy(self.zenodo)
            data["creators"][0]["affiliations"][0][field] = value
            self.write(data)
            self.assertTrue(citation.check(self.root))
        data = copy.deepcopy(self.zenodo)
        data["creators"][0]["affiliation"] = "Would override the IDs"
        self.write(data)
        self.assertIn("overrides structured", "\n".join(citation.check(self.root)))

    def test_reference_link_and_curated_supported_fields_are_retained(self):
        self.write({**self.zenodo, "related_identifiers": []})
        self.assertIn("reference DOI", "\n".join(citation.check(self.root)))
        data = {
            **self.zenodo,
            "grants": [{"id": "reviewed-grant-id"}],
            "communities": [{"identifier": "reviewed-community"}],
            "custom": {"kept": "yes"},
        }
        self.write(data)
        self.assertEqual(citation.check(self.root), [])

    def test_duplicate_json_keys_and_broken_json_fail_actionably(self):
        path = self.root / ".zenodo.json"
        for value in ('{"title":"first","title":"hidden"}', '{"unfinished":'):
            path.write_text(value, encoding="utf-8")
            self.assertIn(".zenodo.json", "\n".join(citation.check(self.root)))

    def test_cli_is_read_only_and_reports_a_failed_gate(self):
        self.write({**self.zenodo, "version": "2.0.0"})
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(citation.main(["--root", str(self.root)]), 1)
        self.assertIn(".zenodo.json version", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
