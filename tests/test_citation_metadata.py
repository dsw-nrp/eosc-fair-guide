"""CFF correctness and Zenodo consumer compatibility are independent release gates."""

import contextlib
import copy
import io
import json
import re
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

    def edit_cff(self, old, new):
        path = self.root / "CITATION.cff"
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_invalid_cff_is_not_hidden_by_matching_version_and_date(self):
        # Each value is invalid under the CFF 1.2.0 schema, and the report names the file and the field.
        for old, new, field in (
            ('date-released: "2026-', 'date-released: "1 November ', "CITATION.cff date-released:"),
            ("title: ", "titles: ", "CITATION.cff root: 'title' is a required property"),
            ("type: software", "type: poster", "CITATION.cff type:"),
        ):
            with self.subTest(field=field):
                self.setUp()
                self.edit_cff(old, new)
                self.assertIn(field, "\n".join(citation.check(self.root)))

    def test_unquoted_dates_are_validated_as_written(self):
        # YAML would read an unquoted date as a date object; the check keeps it as the text the schema expects.
        path = self.root / "CITATION.cff"
        text, count = re.subn(r'date-released: "(\d{4}-\d{2}-\d{2})"', r"date-released: \1", path.read_text("utf-8"))
        self.assertGreater(count, 0)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(citation.check(self.root), [])

    def test_another_cff_version_is_refused_rather_than_checked_against_the_wrong_schema(self):
        self.edit_cff("cff-version: 1.2.0", "cff-version: 1.3.0")
        self.assertEqual(
            citation.check(self.root),
            ["CITATION.cff cff-version must be 1.2.0, the version whose schema the check holds"],
        )

    def test_broken_yaml_is_reported_without_a_traceback(self):
        (self.root / "CITATION.cff").write_text("cff-version: 1.2.0\ntitle: [unclosed\n", encoding="utf-8")
        self.assertTrue(citation.check(self.root)[0].startswith("CITATION.cff is not valid YAML"))

    def test_a_duplicate_cff_key_is_reported_rather_than_hidden(self):
        # YAML keeps the last duplicate by default; the check must not let a stale value hide behind it.
        path = self.root / "CITATION.cff"
        path.write_text(path.read_text("utf-8") + '\ntitle: "Hidden second title"\n', encoding="utf-8")
        self.assertIn("duplicate key", "\n".join(citation.check(self.root)))

    def test_a_duplicate_key_inside_an_inline_merge_is_reported(self):
        # A merge value is flattened into the merging mapping rather than constructed on its own.
        path = self.root / "CITATION.cff"
        path.write_text(path.read_text("utf-8") + '\n<<: {title: "First", title: "Second"}\n', encoding="utf-8")
        self.assertIn("duplicate key", "\n".join(citation.check(self.root)))

    def test_a_key_merged_from_another_source_may_be_overridden(self):
        # An explicit key wins over a merged one on purpose; that is precedence, not a duplicate.
        path = self.root / "CITATION.cff"
        path.write_text('<<: {title: "Merged title"}\n' + path.read_text("utf-8"), encoding="utf-8")
        self.assertEqual(citation.check(self.root), [])

    def test_a_mapping_that_overrides_a_merged_key_may_be_merged_again(self):
        # Merging flattens the anchored mapping in place; checking it again afterwards would see its override as a
        # duplicate. The loader reads the chain as YAML does, and still refuses a duplicate in an anchored mapping.
        chained = "base: &b {x: 1}\nmid: &m {<<: *b, x: 2}\ntop: {<<: *m}\nlow: {<<: [*m, *b]}\n"
        self.assertEqual(citation.yaml.load(chained, Loader=citation.TextDates), citation.yaml.safe_load(chained))
        with self.assertRaisesRegex(citation.yaml.YAMLError, "duplicate key"):
            citation.yaml.load("base: &b {x: 1, x: 2}\ntop: {<<: *b}\n", Loader=citation.TextDates)

    def test_yaml11_boolean_spellings_stay_text(self):
        # PyYAML's YAML 1.1 resolver would read an unquoted `NO` as False; CFF's country is the string "NO".
        self.edit_cff(
            'orcid: "https://orcid.org/0000-0001-6592-6291"',
            'orcid: "https://orcid.org/0000-0001-6592-6291"\n    country: NO',
        )
        self.assertEqual(citation.check(self.root), [])

    def test_a_file_that_is_not_utf8_is_reported_rather_than_raising(self):
        # A Windows-1250 save is a decoding error, not an OSError; the check reports it like other read failures.
        path = self.root / "CITATION.cff"
        raw = path.read_bytes()
        self.assertIn(b"Nov\xc3\xa1k", raw)
        path.write_bytes(raw.replace(b"Nov\xc3\xa1k", b"Nov\xe1k", 1))
        errors = citation.check(self.root)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("CITATION.cff: "))
        self.assertIn("codec", errors[0])

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

    def test_contributors_mirror_the_guides_reviewed_list(self):
        contributor = {
            "name": "Karel Berka",
            "orcid": "0000-0001-9472-2589",
            "affiliations": [{"id": "04qxnmv42", "name": "Palacký University Olomouc"}],
            "type": "DataCurator",
        }
        self.assertEqual(self.zenodo.get("contributors"), [contributor])
        self.assertEqual(citation.check(self.root), [])
        self.assertNotIn("contributors:", (self.root / "CITATION.cff").read_text(encoding="utf-8"))
        for field, value, message in (
            ("name", "K. Berka", "name differs from the reviewed person"),
            ("orcid", "0000-0002-0000-0000", "ORCID iD differs"),
            ("type", "Editor", "type must be DataCurator"),
        ):
            with self.subTest(field=field):
                data = copy.deepcopy(self.zenodo)
                data["contributors"][0][field] = value
                self.write(data)
                self.assertIn(message, "\n".join(citation.check(self.root)))
        data = copy.deepcopy(self.zenodo)
        data["contributors"][0]["affiliations"][0]["id"] = "0287jta43"
        self.write(data)
        self.assertIn("affiliations must match", "\n".join(citation.check(self.root)))
        data = copy.deepcopy(self.zenodo)
        data["contributors"][0]["affiliation"] = "Would override the IDs"
        self.write(data)
        self.assertIn("overrides structured", "\n".join(citation.check(self.root)))
        data = copy.deepcopy(self.zenodo)
        data["contributors"] = []
        self.write(data)
        self.assertIn("missing contributor 'Karel Berka'", "\n".join(citation.check(self.root)))
        data = copy.deepcopy(self.zenodo)
        data["contributors"].append({"name": "Jane Doe", "type": "DataCurator"})
        self.write(data)
        self.assertIn("is not in content/guide.toml contributors", "\n".join(citation.check(self.root)))
        data = copy.deepcopy(self.zenodo)
        data["contributors"].append(copy.deepcopy(contributor))
        self.write(data)
        self.assertIn("duplicate contributor 'Karel Berka'", "\n".join(citation.check(self.root)))

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
