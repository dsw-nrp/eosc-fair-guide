"""Snapshot replacement preserves locally owned identity and refuses ambiguous reassignment."""

import sys
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from catalogue_identity import (  # noqa: E402
    KINDS,
    SCOPED_KINDS,
    address,
    identity_seed,
    parse_route,
    preserve_snapshot,
    short_id,
    split_address,
    validate_identity,
)


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
        'guideRoute = "resources"\n'
        'name = "Old title"\nurl = "https://example.org/tool"\n'
    )

    def test_changed_external_id_and_title_join_by_authoritative_url(self):
        new = '[[tool]]\nid = "external-9"\nname = "New title"\nurl = "https://example.org/tool"\n'
        row = tomllib.loads(preserve_snapshot(new, self.OLD))["tool"][0]
        self.assertEqual(row["id"], "our-tool")
        self.assertEqual(row["guideRoute"], "resources")
        self.assertEqual(row["alternateIds"], [{"scheme": "knav", "value": "external-9"}])
        self.assertNotIn("guideId", row)

    def test_changed_url_keeps_identity_when_source_record_is_known(self):
        new = '[[tool]]\nid = "external-1"\nname = "Renamed tool"\nurl = "https://example.org/new"\n'
        self.assertEqual(tomllib.loads(preserve_snapshot(new, self.OLD))["tool"][0]["id"], "our-tool")

    def test_existing_precise_source_key_survives_a_curated_join(self):
        old = (
            '[[resource]]\nid="cc-by-4-0"\n'
            'alternateIds=[{scheme="fip-dashboard", value="cc-by-40"}]\n'
            'guideRoute="resources"\nname="Creative Commons Attribution 4.0"\n'
        )
        incoming = '[[resource]]\nid="cc-by-40"\nname="Creative Commons Attribution 4.0"\n'
        row = tomllib.loads(
            preserve_snapshot(incoming, old, joins={("fip-dashboard", "cc-by-40"): {"resources/specific-licence"}})
        )["resource"][0]
        self.assertEqual(row["id"], "cc-by-4-0")
        self.assertEqual(row["guideRoute"], "resources")

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

    def test_known_source_identity_can_move_to_a_shared_site_without_merging_things(self):
        old = self.OLD + self.OLD.replace("our-tool", "second").replace("external-1", "external-2").replace(
            "example.org/tool", "example.org/second"
        )
        incoming = '[[tool]]\nid = "external-1"\nurl = "https://example.org/second"\n'
        row = tomllib.loads(preserve_snapshot(incoming, old))["tool"][0]
        self.assertEqual(row["id"], "our-tool")

    def test_unknown_source_identity_with_two_address_owners_is_rejected(self):
        old = self.OLD + self.OLD.replace("our-tool", "second").replace("external-1", "external-2")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            preserve_snapshot('[[tool]]\nid="unknown"\nurl="https://example.org/tool"\n', old)

    def test_split_source_cannot_reuse_one_guide_id(self):
        new = (
            '[[tool]]\nid = "a"\nurl = "https://example.org/tool"\n'
            '[[tool]]\nid = "b"\nurl = "https://example.org/tool"\n'
        )
        with self.assertRaisesRegex(ValueError, "duplicate Guide identity"):
            preserve_snapshot(new, self.OLD)

    def test_new_ids_are_short_and_do_not_reuse_removed_ids(self):
        new = '[[tool]]\nid = "new"\nname = "Our tool"\n'
        with self.assertRaisesRegex(ValueError, "our-tool.*review"):
            preserve_snapshot(new, self.OLD)
        self.assertLessEqual(len(short_id("A very long name " * 20, set())), 32)

    def test_new_dashboard_repository_uses_the_repository_family(self):
        incoming = '[[resource]]\nid = "external"\nname = "New Repository"\ntype = "repository"\n'
        row = tomllib.loads(preserve_snapshot(incoming, ""))["resource"][0]
        self.assertEqual(row["guideRoute"], "repositories")

    def test_legacy_repository_without_route_keeps_its_kind_without_spurious_retirement(self):
        old = (
            '[[resource]]\nid="archive"\n'
            'alternateIds=[{scheme="fip-dashboard",value="external-archive"}]\n'
            'type="repository"\nname="Archive"\n'
        )
        for native_type in ("repository", "registry"):
            incoming = f'[[resource]]\nid="external-archive"\ntype="{native_type}"\nname="Archive"\n'
            result = tomllib.loads(preserve_snapshot(incoming, old))
            self.assertEqual(result["resource"][0]["guideRoute"], "repositories")
            self.assertNotIn("identity", result)

    def test_an_old_local_id_cannot_silently_become_a_source_identifier(self):
        malformed = '[[tool]]\nid = "forgotten-local-slug"\nurl = "https://example.org/tool"\n'
        with self.assertRaisesRegex(ValueError, "missing genuine knav"):
            preserve_snapshot(malformed, malformed)

    def test_removed_ids_stay_reserved_across_later_refreshes(self):
        second = preserve_snapshot('[[tool]]\nid = "second"\nname = "Second"\n', self.OLD)
        self.assertEqual(tomllib.loads(second)["identity"]["retiredIds"], ["resources/our-tool"])
        with self.assertRaisesRegex(ValueError, "our-tool.*review"):
            preserve_snapshot(
                '[[tool]]\nid = "second"\nname = "Second"\n[[tool]]\nid = "new"\nname = "Our tool"\n', second
            )

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
        with self.assertRaisesRegex(ValueError, "research-metadata.*review"):
            short_id("research metadata", {first})

    def test_reservations_use_kind_and_scope_not_bare_words(self):
        reserved = {"resources/git", "pages/provenance", "tests/f-uji/version-2"}
        incoming = '[[term]]\nid = "501"\nname = "Git"\n[[term]]\nid = "502"\nname = "Provenance"\n'
        rows = tomllib.loads(preserve_snapshot(incoming, "", reserved))["term"]
        self.assertEqual([row["id"] for row in rows], ["git", "provenance"])
        self.assertEqual(short_id("version-2", set()), "version-2")
        with self.assertRaisesRegex(ValueError, "glossary/git.*review"):
            preserve_snapshot(incoming, "", {"glossary/git"})

    def test_legacy_retirement_remains_conservatively_reserved(self):
        with self.assertRaisesRegex(ValueError, "git.*review"):
            preserve_snapshot('[[term]]\nid = "501"\nname = "Git"\n', "", {"git"})

    def test_reviewed_join_precedes_allocation_and_rejects_ambiguous_owners(self):
        incoming = '[[tool]]\nid = "re3data"\nname = "re3data"\n'
        joins = {("knav", "re3data"): {"resources/re3data"}}
        row = tomllib.loads(preserve_snapshot(incoming, "", {"resources/re3data"}, joins=joins))["tool"][0]
        self.assertEqual((row["id"], row["guideRoute"]), ("re3data", "resources"))
        self.assertEqual(row["alternateIds"], [{"scheme": "knav", "value": "re3data"}])
        joins[("knav", "re3data")].add("resources/another")
        with self.assertRaisesRegex(ValueError, "ambiguous.*resources/another.*resources/re3data"):
            preserve_snapshot(incoming, "", joins=joins)


class KindVocabularyTests(unittest.TestCase):
    """An address is `<kind>/<id>` or `<kind>/<scope>/<id>`, with a plural kind word and no classification."""

    def test_every_kind_and_scope_forms_one_address(self):
        for kind in sorted(KINDS):
            with self.subTest(kind=kind):
                if kind == "tests":
                    self.assertEqual(address(kind, "x", "f-uji"), "tests/f-uji/x")
                    with self.assertRaisesRegex(ValueError, "needs a scope"):
                        address(kind, "x")
                    continue
                self.assertEqual(address(kind, "x"), f"{kind}/x")
                self.assertEqual(split_address(f"{kind}/x"), (kind, None, "x"))
                if kind in SCOPED_KINDS:
                    self.assertEqual(split_address(address(kind, "plan", "rdmkit")), (kind, "rdmkit", "plan"))
                else:
                    with self.assertRaisesRegex(ValueError, "takes no scope"):
                        address(kind, "x", "scope")
        self.assertEqual(split_address("lifecycles/rdmkit/plan"), ("lifecycles", "rdmkit", "plan"))

    def test_a_classification_segment_or_an_unknown_kind_is_refused(self):
        for value in ("resources/service/datacite", "repositories/domain/csda", "resource/x", "tools/x"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                split_address(value)
        for value in ("repositories/domain", "resources/service", "tools", "resources/a/b"):
            with self.subTest(route=value), self.assertRaises(ValueError):
                parse_route(value)
        self.assertEqual(parse_route("tests/fair-champion"), ("tests", "fair-champion"))

    def test_a_refresh_refuses_a_stored_route_with_a_classification(self):
        old = SnapshotIdentityTests.OLD.replace('guideRoute = "resources"', 'guideRoute = "resources/tool"')
        with self.assertRaisesRegex(ValueError, "'resources' takes no scope 'tool'"):
            preserve_snapshot('[[tool]]\nid = "external-1"\nname = "Old title"\n', old)

    def test_a_new_disciplinary_nkr_record_is_a_repository(self):
        incoming = (
            '[snapshot]\nsource = "NKR"\n\n'
            '[[record]]\nid = "20.500.14818/jgu5fyqf"\nrepositoryName = "Herbarium"\n'
            'mainUrl = "https://herbarium.biodiversity.cz"\ntype = "disciplinary"\n'
        )
        row = tomllib.loads(preserve_snapshot(incoming, ""))["record"][0]
        self.assertEqual((row["id"], row["guideRoute"]), ("herbarium", "repositories"))


if __name__ == "__main__":
    unittest.main()
