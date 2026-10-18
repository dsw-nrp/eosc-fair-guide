"""Snapshot replacement preserves locally owned identity and refuses ambiguous reassignment."""

import sys
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from catalogue_identity import identity_seed, preserve_snapshot, short_id, validate_identity  # noqa: E402


class SnapshotIdentityTests(unittest.TestCase):
    def test_initial_slug_uses_abbreviation_then_specific_url_words_without_particles(self):
        self.assertEqual(identity_seed({"acronym": "ORCID", "url": "https://example.org/other"}), "ORCID")
        self.assertEqual(
            identity_seed({"name": "A long name", "url": "https://example.org/bioimage-archive/submit/"}),
            "bioimage-archive",
        )
        self.assertEqual(
            identity_seed({"name": "Jupyter", "url": "https://example.org/pun/sys/jupyter/session_contexts/new"}),
            "jupyter",
        )
        self.assertEqual(
            short_id("The archive of data and software for research", set()), "archive-data-software-research"
        )
        self.assertEqual(short_id("2026-10-11-layers-and-seams", set()), "2026-10-11-layers-seams")

    OLD = (
        '[[tool]]\nid = "our-tool"\nalternateIds = [{ scheme = "knav", value = "external-1" }]\n'
        'guideRoute = "res/tool"\n'
        'name = "Old title"\nurl = "https://example.org/tool"\n'
    )

    def test_changed_external_id_and_title_join_by_authoritative_url(self):
        new = '[[tool]]\nid = "external-9"\nname = "New title"\nurl = "https://example.org/tool"\n'
        row = tomllib.loads(preserve_snapshot(new, self.OLD))["tool"][0]
        self.assertEqual(row["id"], "our-tool")
        self.assertEqual(row["guideRoute"], "res/tool")
        self.assertEqual(row["alternateIds"], [{"scheme": "knav", "value": "external-9"}])
        self.assertNotIn("guideId", row)

    def test_changed_url_keeps_identity_when_source_record_is_known(self):
        new = '[[tool]]\nid = "external-1"\nname = "Renamed tool"\nurl = "https://example.org/new"\n'
        self.assertEqual(tomllib.loads(preserve_snapshot(new, self.OLD))["tool"][0]["id"], "our-tool")

    def test_refresh_retains_reviewed_link_names_without_changing_source_text(self):
        old = self.OLD + 'linkNames = { cs = ["reviewed form"], en = ["Specific tool"] }\n'
        new = '[[tool]]\nid = "external-1"\nname = "Old title"\ndescription = "Exact source wording"\n'
        row = tomllib.loads(preserve_snapshot(new, old))["tool"][0]
        self.assertEqual(row["linkNames"], {"cs": ["reviewed form"], "en": ["Specific tool"]})
        self.assertEqual(row["description"], "Exact source wording")

    def test_name_alone_cannot_merge_changed_identity(self):
        new = '[[tool]]\nid = "unknown"\nname = "Old title"\nurl = "https://other.example/new"\n'
        with self.assertRaisesRegex(ValueError, "needs review"):
            preserve_snapshot(new, self.OLD)

    def test_split_source_cannot_reuse_one_guide_id(self):
        new = (
            '[[tool]]\nid = "a"\nurl = "https://example.org/tool"\n'
            '[[tool]]\nid = "b"\nurl = "https://example.org/tool"\n'
        )
        with self.assertRaisesRegex(ValueError, "duplicate Guide identity"):
            preserve_snapshot(new, self.OLD)

    def test_new_ids_are_short_and_do_not_reuse_removed_ids(self):
        new = '[[tool]]\nid = "new"\nname = "Our tool"\n'
        row = tomllib.loads(preserve_snapshot(new, self.OLD))["tool"][0]
        self.assertEqual(row["id"], "our-tool-2")
        self.assertLessEqual(len(short_id("A very long name " * 20, set())), 32)

    def test_new_dashboard_repository_uses_the_repository_family(self):
        incoming = '[[resource]]\nid = "external"\nname = "New Repository"\ntype = "repository"\n'
        row = tomllib.loads(preserve_snapshot(incoming, ""))["resource"][0]
        self.assertEqual(row["guideRoute"], "repo")

    def test_an_old_local_id_cannot_silently_become_a_source_identifier(self):
        malformed = '[[tool]]\nid = "forgotten-local-slug"\nurl = "https://example.org/tool"\n'
        with self.assertRaisesRegex(ValueError, "missing genuine knav"):
            preserve_snapshot(malformed, malformed)

    def test_removed_ids_stay_reserved_across_later_refreshes(self):
        second = preserve_snapshot('[[tool]]\nid = "second"\nname = "Second"\n', self.OLD)
        self.assertEqual(tomllib.loads(second)["identity"]["retiredIds"], ["our-tool"])
        third = preserve_snapshot(
            '[[tool]]\nid = "second"\nname = "Second"\n[[tool]]\nid = "new"\nname = "Our tool"\n', second
        )
        self.assertEqual([row["id"] for row in tomllib.loads(third)["tool"]], ["second", "our-tool-2"])

    def test_incomplete_untyped_duplicate_and_competing_identifiers_are_rejected(self):
        for fields in (
            {"alternateIds": ["old-local-id"]},
            {"alternateIds": [{"value": "old-local-id"}]},
            {"alternateIds": [{"scheme": "knav", "value": ""}]},
            {"guideId": "second-primary"},
            {"alternateIds": [{"scheme": "knav", "value": "one"}, {"scheme": "knav", "value": "two"}]},
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                validate_identity({"id": "owned", **fields}, "knav")

    def test_boundaries_keep_complete_words_when_reserving_a_collision_suffix(self):
        first = short_id("research metadata interoperability", set())
        self.assertEqual(first, "research-metadata")
        self.assertEqual(short_id("research metadata", {first}), "research-metadata-2")


if __name__ == "__main__":
    unittest.main()
