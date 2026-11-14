"""Unit tests of the one-time content migration (unify-identity-model-and-api, decision 17).

Run with ``python -m unittest openspec/changes/unify-identity-model-and-api/migration/test_migrate.py``. Each test
works on a temporary copy of the minimal content fixture, put back into the forms the content had before the
migration, so the migration is checked against the input it was written for.
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

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

    def test_dependent_renames_do_not_reapply_a_completed_transition(self) -> None:
        path = self.root / "content" / "duplicates.toml"
        before = '"term:research-infrastructure"\n"term:research-infrastructure-2"\n'
        after = '"term:large-research-infrastructure"\n"term:research-infrastructure"\n'
        path.write_text(before, encoding="utf-8")
        migrate.rename(self.root)
        self.assertEqual(path.read_text(encoding="utf-8"), after)
        # A mixed checkout may request this transition again; a completed result cannot be renamed again.
        migrate.rename(self.root)
        self.assertEqual(path.read_text(encoding="utf-8"), after)

    def test_every_interrupted_write_boundary_has_a_byte_identical_retry(self) -> None:
        source = Path(self.temporary.name) / "legacy"
        expected_root = Path(self.temporary.name) / "expected"
        shutil.copytree(self.root, source)
        shutil.copytree(source, expected_root)
        migrate.migrate(expected_root, dry_run=False)

        def state(root: Path) -> dict[str, bytes]:
            return {path.relative_to(root).as_posix(): path.read_bytes() for path in (root / "content").rglob("*.toml")}

        legacy, expected = state(source), state(expected_root)
        changed = [name for name in expected if expected[name] != legacy[name]]
        self.assertTrue(changed)
        actual_replace = migrate.os.replace
        for boundary in range(1, len(changed) + 1):
            with self.subTest(boundary=boundary, files=len(changed)):
                candidate = Path(self.temporary.name) / f"retry-{boundary}"
                shutil.copytree(source, candidate)
                calls = 0

                def interrupt(source_path, target_path, boundary=boundary):
                    nonlocal calls
                    calls += 1
                    if calls == boundary:
                        raise OSError(f"planted interruption at boundary {boundary}")
                    actual_replace(source_path, target_path)

                with (
                    mock.patch.object(migrate.os, "replace", side_effect=interrupt),
                    self.assertRaisesRegex(OSError, "planted interruption"),
                ):
                    migrate.migrate(candidate, dry_run=False)
                for name, data in state(candidate).items():
                    self.assertIn(data, (legacy[name], expected[name]), f"{name} was only partially written")
                migrate.migrate(candidate, dry_run=False)
                self.assertEqual(state(candidate), expected)
                self.assertEqual(migrate.migrate(candidate, dry_run=False), [])

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

    def test_a_page_section_takes_its_reviewed_id_once(self) -> None:
        pages = self.root / "content" / "pages.toml"
        pages.write_text(
            '[[page]]\nid = "p"\nmenu = "about"\ntitle = { cs = "Stránka", en = "Page" }\n\n'
            '[[page.section]]\nbody = { cs = "Úvod.", en = "Intro." }\n\n'
            '[[page.section]]\nid = "kept"\nheading = { cs = "Dál", en = "On" }\n'
            'body = { cs = "Text.", en = "Text." }\n',
            encoding="utf-8",
        )
        with mock.patch.dict(migrate.IDS, {"section": [{"page": "p", "position": 1, "id": "intro"}]}):
            migrate.name_sections(self.root)
            named = pages.read_text(encoding="utf-8")
            sections = tomllib.loads(named)["page"][0]["section"]
            self.assertEqual([section["id"] for section in sections], ["intro", "kept"])
            migrate.name_sections(self.root)
            self.assertEqual(pages.read_text(encoding="utf-8"), named)
        pages.write_text(named.replace('id = "intro"\n', ""), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "section 1 of 'p' has no id and no reviewed one"):
            migrate.name_sections(self.root)

    def test_a_question_that_copies_a_clause_takes_its_text_once(self) -> None:
        gate = self.root / "content" / "checks" / "gate.toml"
        text = gate.read_text(encoding="utf-8")
        own = next(line for line in text.splitlines() if line.startswith("statement = "))
        copy = (
            'statement = { cs = "Repozitář přiděluje [[resources/report|PID]]", en = "The repository assigns PIDs." }'
        )
        gate.write_text(text.replace(own, copy), encoding="utf-8")
        row = {"question": "gate.01", "clause": "A.F1.R1", "clauseText": {"cs": "Nový.", "en": "New."}}
        reviewed = {"requirement": [row]}
        with mock.patch.dict(migrate.STATEMENTS, reviewed):
            migrate.merge_statements(self.root)
            item = tomllib.loads(gate.read_text(encoding="utf-8"))["item"][0]
            self.assertEqual(item["requirement"], "A.F1.R1")
            self.assertNotIn("statement", item)
            ledger = tomllib.loads((self.root / "content" / "ledger.toml").read_text(encoding="utf-8"))
            self.assertEqual(ledger["clause"][0]["text"], {"cs": "Nový.", "en": "New."})
            once = gate.read_text(encoding="utf-8")
            migrate.merge_statements(self.root)
            self.assertEqual(gate.read_text(encoding="utf-8"), once)
        # Without a reviewed entry, a question drops only a copy of its own requirement in both languages; a copy in
        # one language stays, for the content check to report.
        shutil.copy2(FIXTURE / "content" / "ledger.toml", self.root / "content" / "ledger.toml")
        partial = 'statement = { cs = "Repozitář přiděluje PID.", en = "Records receive identifiers." }'
        with mock.patch.dict(migrate.STATEMENTS, {"requirement": []}):
            for statement, kept in ((partial, True), (copy, False)):
                gate.write_text(once.replace('requirement = "A.F1.R1"\n', f'requirement = "A.F1.R1"\n{statement}\n'))
                migrate.merge_statements(self.root)
                self.assertEqual(statement in gate.read_text(encoding="utf-8"), kept, statement)

    def test_references_name_records_by_address(self) -> None:
        bare = {"service": "resources"}
        text = "Use [[service|the service]], [[term:data|data]] and [[res/tool/github|GitHub]]."
        self.assertEqual(
            migrate.migrate_references(text, bare),
            "Use [[resources/service|the service]], [[glossary/data|data]] and [[resources/github|GitHub]].",
        )
        with self.assertRaisesRegex(ValueError, "unknown reference target"):
            migrate.migrate_references("[[nothing|x]]", bare)


class RenormaliseTests(unittest.TestCase):
    """A recorded snapshot moves to the current route format without a new observation."""

    SNAPSHOT = (
        '[snapshot]\nsource = "NKR"\nretrieved = 2026-11-01\n\n'
        '[[record]]\nid = "herbarium"\nalternateIds = [{ "scheme" = "nkr", "value" = "20.500.14818/jgu5fyqf" }]\n'
        'guideRoute = "repo/dom"\nrepositoryName = "Herbarium"\nmainUrl = "https://herbarium.biodiversity.cz"\n'
    )

    def test_an_nkr_route_is_rewritten_once_and_the_retrieval_date_stays(self):
        first = migrate.renormalise_snapshot(self.SNAPSHOT, {"repo/dom": "repositories"})
        self.assertEqual(tomllib.loads(first)["record"][0]["guideRoute"], "repositories")
        self.assertEqual(str(tomllib.loads(first)["snapshot"]["retrieved"]), "2026-11-01")
        self.assertEqual(first.replace('"repositories"', '"repo/dom"'), self.SNAPSHOT)
        self.assertEqual(migrate.renormalise_snapshot(first, {"repo/dom": "repositories"}), first)

    def test_an_untranslated_old_route_or_a_broken_identity_is_refused(self):
        with self.assertRaisesRegex(ValueError, "unknown record kind 'repo'"):
            migrate.renormalise_snapshot(self.SNAPSHOT)
        with self.assertRaisesRegex(ValueError, "missing genuine nkr"):
            migrate.renormalise_snapshot(self.SNAPSHOT.replace('"scheme" = "nkr"', '"scheme" = "knav"'))


class CurrentFormsTests(unittest.TestCase):
    """The repository's scripts, tests and page know only the current forms; the old ones live in this folder."""

    def test_no_durable_file_names_a_reference_word_form_or_a_code_address(self) -> None:
        # `check/<id>` is also the page's current view of a check, so that one head says nothing about an address.
        heads = sorted(set(migrate.PREFIXES) - {"check"}, key=len, reverse=True)
        code_address = re.compile(r"[\"'\[](?:" + "|".join(re.escape(head) for head in heads) + r")/[A-Za-z0-9]")
        word_form = re.compile(r"\[\[(?:" + "|".join(migrate.WORD_KINDS) + r"):")
        found = []
        for folder, patterns in (
            ("scripts", ("*.py",)),
            ("tests", ("*.py", "*.mjs", "*.toml")),
            ("assets/js", ("*.js",)),
        ):
            for pattern in patterns:
                for path in sorted((ROOT / folder).rglob(pattern)):
                    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                        if code_address.search(line) or word_form.search(line):
                            found.append(f"{path.relative_to(ROOT).as_posix()}:{number}: {line.strip()[:100]}")
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
