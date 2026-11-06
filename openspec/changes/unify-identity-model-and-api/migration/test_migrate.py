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
        provenance.write_text(text.replace(current, OLD_RESULTS), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def results(self) -> list[str]:
        data = tomllib.loads((self.root / "content" / "provenance.toml").read_text(encoding="utf-8"))
        return data["action"][0]["results"]

    def test_a_dry_run_prints_the_diff_and_writes_nothing(self) -> None:
        diff = migrate.migrate(self.root, dry_run=True)
        self.assertIn("+++ content/provenance.toml\n", diff)
        self.assertIn("organization:org", self.results())

    def test_results_name_the_same_items_by_address_and_a_second_run_changes_nothing(self) -> None:
        migrate.migrate(self.root, dry_run=False)
        self.assertEqual(self.results(), NEW_RESULTS)
        self.assertEqual(migrate.migrate(self.root, dry_run=False), [])

    def test_a_result_that_names_nothing_stops_the_migration(self) -> None:
        provenance = self.root / "content" / "provenance.toml"
        provenance.write_text(
            provenance.read_text(encoding="utf-8").replace('"guide", ', '"guide", "no-such-item", '), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "no-such-item"):
            migrate.migrate(self.root, dry_run=True)

    def test_the_register_kinds_take_the_kind_vocabulary(self) -> None:
        text = '[issued]\nrequirements = [\n  "A.F1.N1",\n]\nmodel = []\nlifecycle = []\nlenses = ["V"]\n'
        renamed = migrate.rename_register_kinds(text)
        self.assertEqual(
            renamed, '[issued]\nclauses = [\n  "A.F1.N1",\n]\nmodels = []\nlifecycles = []\nlenses = ["V"]\n'
        )
        self.assertEqual(migrate.rename_register_kinds(renamed), renamed)

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
