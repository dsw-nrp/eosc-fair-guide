"""Unit tests of the one-time content migration (unify-identity-model-and-api, decision 17).

Run with ``python -m unittest openspec/changes/unify-identity-model-and-api/migration/test_migrate.py``. Each test
works on a temporary copy of the minimal content fixture, put back into the forms the content had before the
migration, so the migration is checked against the input it was written for.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
import migrate  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "minimal"
# The fixture's provenance results as they were written before the migration, with the content IDs they used.
OLD_RESULTS = (
    'results = ["guide", "organization:org", "one.*", "gate.01", "service", "A.*", "CTS.*", "report", "cts-test", '
    '"callout:note", "callout.note.*", "test:test_one"]'
)
NEW_RESULTS = [
    "guide",
    "organizations/org",
    "advice/one.*",
    "questions/gate.01",
    "resources/service",
    "clauses/A.*",
    "clauses/CTS.*",
    "resources/report",
    "resources/cts-test",
    "callouts/note",
    "callouts/note#*",
    "tests/fair-champion/test_one",
]


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "guide"
        shutil.copytree(FIXTURE, self.root)
        provenance = self.root / "content" / "provenance.toml"
        text = provenance.read_text(encoding="utf-8")
        current = next(line for line in text.splitlines() if line.startswith("results = ["))
        text = text.replace(current, OLD_RESULTS).replace('objects = ["resources/report"]', 'objects = ["report"]')
        provenance.write_text(text, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def results(self, field: str = "results") -> list[str]:
        data = tomllib.loads((self.root / "content" / "provenance.toml").read_text(encoding="utf-8"))
        return data["action"][0][field]

    def test_a_dry_run_prints_the_diff_and_writes_nothing(self) -> None:
        diff = migrate.migrate(self.root, dry_run=True)
        self.assertIn("+++ content/provenance.toml\n", diff)
        self.assertIn("organization:org", self.results())

    def test_results_name_the_same_items_by_address_and_a_second_run_changes_nothing(self) -> None:
        migrate.migrate(self.root, dry_run=False)
        self.assertEqual(self.results(), NEW_RESULTS)
        self.assertEqual(self.results("objects"), ["resources/report"])
        self.assertEqual(migrate.migrate(self.root, dry_run=False), [])

    def test_a_result_that_names_nothing_stops_the_migration(self) -> None:
        provenance = self.root / "content" / "provenance.toml"
        provenance.write_text(
            provenance.read_text(encoding="utf-8").replace('"guide", ', '"guide", "no-such-item", '), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "no-such-item"):
            migrate.migrate(self.root, dry_run=True)

    def test_the_register_keys_each_identifier_by_its_records_kind(self) -> None:
        content = migrate.load_content(self.root / "content")
        text = (
            "[register]\nprepared = 2026-10-15\n\n[issued]\n"
            'lenses = ["V"]\nmodes = ["dataset.before"]\nprofiles = ["gate.core-system"]\n'
            'callouts = ["callout:note"]\ncallout_items = ["callout.note.one"]\nrequirements = ["A.F1.R1"]\n'
            'tests = ["guide-dataset-01"]\nsources = ["report"]\nadvice = ["one.01"]\n\n'
            '[retired]\nadvice = ["one.99"]\n'
        )
        rekeyed = tomllib.loads(migrate.rekey_register(text, content))
        self.assertEqual(
            rekeyed["issued"],
            {
                "vocabularies": ["lenses/V", "modes-dataset/before", "profiles-gate/core-system"],
                "callouts": ["note", "note#one"],
                "clauses": ["A.F1.R1"],
                "tests": ["guide/guide-dataset-01"],
                "resources": ["report"],
                "advice": ["one.01"],
            },
        )
        self.assertEqual(rekeyed["retired"], {"advice": ["one.99"]})
        again = migrate.rekey_register(migrate.rekey_register(text, content), content)
        self.assertEqual(again, migrate.rekey_register(text, content))

    def test_compression_keeps_the_prefix_then_falls_back_to_scopes_and_addresses(self) -> None:
        universe = [
            "tests/f-uji/A",
            "tests/f-uji/B",
            "tests/guide/one",
            "tests/fcx/C",
            "advice/x.01",
            "advice/x.01#step-1",
        ]
        self.assertEqual(
            migrate.compress("provider:*", {"tests/f-uji/A", "tests/f-uji/B", "tests/fcx/C"}, universe),
            ["tests/f-uji/*", "tests/fcx/*"],
        )
        self.assertEqual(migrate.compress("x.*", {"advice/x.01"}, universe), ["advice/x.*"])
        self.assertEqual(migrate.compress("guide-x", {"tests/guide/one"}, universe), ["tests/guide/one"])

    def test_fields_that_can_name_several_kinds_name_records_by_address(self) -> None:
        model = self.root / "content" / "model.toml"
        model.write_text(
            '[model]\nid = "m"\n\n[model.workedExample]\nsteps = ["A.F1.R1", "test:test_one", "questions/gate.01"]\n\n'
            '[[association]]\ntarget = "gate.01"\nseams = ["x"]\n',
            encoding="utf-8",
        )
        migrate.migrate_named_records(self.root)
        data = tomllib.loads(model.read_text(encoding="utf-8"))
        self.assertEqual(
            data["model"]["workedExample"]["steps"],
            ["clauses/A.F1.R1", "tests/fair-champion/test_one", "questions/gate.01"],
        )
        self.assertEqual(data["association"][0]["target"], "questions/gate.01")
        self.assertEqual(self.results("objects"), ["resources/report"])
        model.write_text('[[association]]\ntarget = "nothing"\nseams = ["x"]\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "'nothing' names no record"):
            migrate.migrate_named_records(self.root)

    def test_references_name_records_by_address(self) -> None:
        bare = {"service": "resources"}
        text = "Use [[service|the service]], [[term:data|data]] and [[res/tool/github|GitHub]]."
        self.assertEqual(
            migrate.migrate_references(text, bare),
            "Use [[resources/service|the service]], [[glossary/data|data]] and [[resources/github|GitHub]].",
        )
        with self.assertRaisesRegex(ValueError, "unknown reference target"):
            migrate.migrate_references("[[nothing|x]]", bare)


if __name__ == "__main__":
    unittest.main()
