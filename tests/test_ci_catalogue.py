"""The CI catalogue is rendered from the workflow files and fails on any undocumented workflow, artifact or write."""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ci_catalogue  # noqa: E402
from ci_catalogue import COMMAND, DOCUMENT, ENTRIES, ROOT, WORKFLOWS, main, problems, render  # noqa: E402

NEW_WORKFLOW = """name: Example
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo
"""


class CatalogueTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(ROOT / WORKFLOWS, self.root / WORKFLOWS)
        for name in (ENTRIES, DOCUMENT):
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / name, self.root / name)

    def check(self) -> tuple[int, str]:
        errors = io.StringIO()
        with redirect_stderr(errors), redirect_stdout(io.StringIO()):
            code = main(["--check", "--root", str(self.root)])
        return code, errors.getvalue()

    def edit(self, name: str, old: str, new: str) -> None:
        path = self.root / name
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_the_repository_catalogue_is_complete_and_current(self) -> None:
        self.assertEqual(problems(ROOT), [])
        self.assertIn(render(ROOT), (ROOT / DOCUMENT).read_text(encoding="utf-8"))
        self.assertEqual(self.check(), (0, ""))

    def test_the_generated_copilot_setup_is_covered(self) -> None:
        self.assertIn("### `copilot-setup-steps.yml`: Copilot Setup Steps", render(ROOT))

    def test_a_workflow_without_an_entry_is_named(self) -> None:
        (self.root / WORKFLOWS / "example.yml").write_text(NEW_WORKFLOW, encoding="utf-8")
        code, errors = self.check()
        self.assertEqual(code, 1)
        self.assertIn('add [workflow."example.yml"] with purpose, entry, next, rerun', errors)

    def test_an_artifact_without_an_entry_is_named(self) -> None:
        upload = (
            "      - uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2\n"
            "        with:\n          name: digest-draft-${{ github.run_id }}\n          path: .cache/x\n"
        )
        # Appended to the last step list, which is the publish job's.
        path = self.root / WORKFLOWS / "health-watch.yml"
        path.write_text(path.read_text(encoding="utf-8").rstrip("\n") + "\n" + upload, encoding="utf-8")
        code, errors = self.check()
        self.assertEqual(code, 1)
        self.assertIn('add [artifact."digest-draft-<run_id>"] with its purpose', errors)

    def test_a_new_write_permission_needs_its_reason(self) -> None:
        self.edit(f"{WORKFLOWS}/health-watch.yml", "      issues: read\n", "      issues: write\n")
        code, errors = self.check()
        self.assertEqual(code, 1)
        self.assertIn('workflow health-watch.yml needs writes."audit.issues": why the audit job may write', errors)

    def test_a_permission_change_without_regeneration_names_the_command(self) -> None:
        self.edit(
            f"{WORKFLOWS}/checks.yml",
            "permissions:\n  contents: read\n",
            "permissions:\n  contents: read\n  actions: read\n",
        )
        code, errors = self.check()
        self.assertEqual(code, 1)
        self.assertIn(f"{DOCUMENT}: the workflow catalogue is stale; run `{COMMAND}`", errors)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--root", str(self.root)]), 0)
        self.assertEqual(self.check(), (0, ""))

    def test_entries_nothing_uses_are_named(self) -> None:
        self.edit(
            ENTRIES,
            '[artifact."staging-site"]',
            '[artifact."retired-site"]\npurpose = "x"\n\n[artifact."staging-site"]',
        )
        self.assertIn(f'{ENTRIES}: remove [artifact."retired-site"]; no workflow uploads it', problems(self.root))

    def test_waiting_runs_are_described_as_github_keeps_them(self) -> None:
        # Without `queue: max`, GitHub keeps one waiting run per group and a newer one replaces it.
        self.assertEqual(
            ci_catalogue.concurrency({"group": "g", "cancel-in-progress": "false"}),
            "`g`, one run waits; a newer one replaces it",
        )
        self.assertEqual(ci_catalogue.concurrency({"group": "g"}), "`g`, one run waits; a newer one replaces it")
        self.assertEqual(
            ci_catalogue.concurrency({"group": "g", "queue": "max"}), "`g`, queued; every waiting run is kept"
        )
        self.assertEqual(
            ci_catalogue.concurrency({"group": "g", "cancel-in-progress": "true"}), "`g`, cancels the run in progress"
        )
        rendered = render(ROOT)
        self.assertIn("`refresh` `source-refresh`, queued; every waiting run is kept", rendered)
        self.assertIn("workflow `health-watch`, one run waits; a newer one replaces it", rendered)

    def test_expression_names_become_readable_patterns(self) -> None:
        self.assertEqual(
            ci_catalogue.placeholder("guide-site-${{ needs.sources.outputs.production }}-${{github.run_attempt}}"),
            "guide-site-<needs.sources.outputs.production>-<run_attempt>",
        )


if __name__ == "__main__":
    unittest.main()
