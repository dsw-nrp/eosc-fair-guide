"""The unpublished changelog section, protected release history and complete release transitions."""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_changelog  # noqa: E402
import release_versions as release  # noqa: E402

HISTORY = "## [0.9.0] - 2026-10-01\n\n### Merged pull requests\n\n- Old ([#1](https://example.org/1))\n"
NOTES = "### Fixed\n\n- Keep curated notes through release preparation.\n"


def changelog(unreleased: str = "", history: str = HISTORY) -> str:
    return "# Changelog\n\nIntro.\n\n## [Unreleased]\n\n" + unreleased + ("\n" if unreleased else "") + history


class Structure(unittest.TestCase):
    def test_current_repository_changelog_is_valid(self) -> None:
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual(check_changelog.structure_errors(text), [])

    def test_empty_notes_and_legacy_prose_are_valid(self) -> None:
        for unreleased in ("", NOTES, "Draft notes in free prose.\n", "<!-- reminder -->\n"):
            with self.subTest(unreleased=unreleased):
                self.assertEqual(check_changelog.structure_errors(changelog(unreleased)), [])

    def test_missing_duplicate_and_misplaced_sections_name_their_fix(self) -> None:
        cases = {
            "no `## [Unreleased]`": "# Changelog\n\n" + HISTORY,
            "2 `## [Unreleased]` sections": changelog() + "\n## [Unreleased]\n",
            "must be the first section": "# Changelog\n\n" + HISTORY + "\n## [Unreleased]\n",
            "appears 2 times": changelog(history=HISTORY + "\n" + HISTORY),
        }
        for expected, text in cases.items():
            with self.subTest(expected=expected):
                self.assertIn(expected, "\n".join(check_changelog.structure_errors(text)))

    def test_placeholders_and_empty_categories_are_not_entries(self) -> None:
        placeholders = ("### Added\n", "### Added\n\n- \n", "### Fixed\n\n- TBD\n", "### Added\n\n### Fixed\n\n- A.\n")
        for unreleased in placeholders:
            with self.subTest(unreleased=unreleased):
                self.assertTrue(check_changelog.structure_errors(changelog(unreleased)))

    def test_reserved_lineage_headings_are_refused_in_curated_notes(self) -> None:
        errors = check_changelog.structure_errors(changelog("### Merged pull requests\n\n- Manual list.\n"))
        self.assertIn("Merged pull requests", "\n".join(errors))


class History(unittest.TestCase):
    def test_unchanged_history_with_new_notes_passes(self) -> None:
        self.assertEqual(check_changelog.history_errors(changelog(), changelog(NOTES), "base"), [])

    def test_editing_or_removing_a_release_is_refused(self) -> None:
        edited = changelog(history=HISTORY.replace("Old", "Rewritten"))
        self.assertIn("changed since base", "\n".join(check_changelog.history_errors(changelog(), edited, "base")))
        removed = changelog(history="")
        self.assertIn("was removed", "\n".join(check_changelog.history_errors(changelog(), removed, "base")))

    def test_accepted_historical_formats_pass_unconverted(self) -> None:
        legacy = "## [0.1.0]\n\nFree-form historical text without a date.\n"
        base = changelog(history=HISTORY + "\n" + legacy)
        self.assertEqual(check_changelog.history_errors(base, base, "base"), [])
        self.assertEqual(check_changelog.structure_errors(base), [])

    def test_complete_release_transition_is_accepted(self) -> None:
        base = changelog(NOTES)
        released = "## [1.0.0] - 2026-10-24\n\n" + NOTES.strip() + "\n\nSince v0.9.0.\n\n" + HISTORY.split("\n", 2)[2]
        transition = changelog(history=released + "\n" + HISTORY)
        self.assertEqual(check_changelog.history_errors(base, transition, "base"), [])
        self.assertEqual(check_changelog.structure_errors(transition), [])

    def test_incomplete_transitions_are_rejected(self) -> None:
        base = changelog(NOTES)
        lost = changelog(history="## [1.0.0] - 2026-10-24\n\nSince v0.9.0.\n\n" + HISTORY)
        kept_notes = changelog(NOTES, history="## [1.0.0] - 2026-10-24\n\n" + NOTES + "\n" + HISTORY)
        misplaced = changelog(history=HISTORY + "\n## [1.0.0] - 2026-10-24\n\n" + NOTES)
        two = changelog(history="## [1.1.0]\n\n" + NOTES + "\n## [1.0.0]\n\n" + NOTES + "\n" + HISTORY)
        for name, text in {"lost": lost, "kept": kept_notes, "misplaced": misplaced, "two": two}.items():
            with self.subTest(name=name):
                self.assertTrue(check_changelog.history_errors(base, text, "base"))

    def test_prepared_release_output_passes_the_check(self) -> None:
        base = changelog(NOTES)
        prepared = release.changelog(
            base,
            "1.0.0",
            "2026-10-24",
            [
                {
                    "number": 7,
                    "merge_commit_sha": "a" * 40,
                    "title": "Keep notes",
                    "merged_at": "2026-10-20T10:00:00Z",
                    "html_url": "https://github.com/dsw-nrp/eosc-fair-guide/pull/7",
                }
            ],
            {"a" * 40},
            previous="v0.9.0",
        )
        self.assertEqual(check_changelog.structure_errors(prepared), [])
        self.assertEqual(check_changelog.history_errors(base, prepared, "base"), [])


class CommandLine(unittest.TestCase):
    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        (self.root / "CHANGELOG.md").write_text(changelog(), encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "Initial")
        self.git("switch", "-c", "change")

    def test_history_is_compared_from_the_merge_base(self) -> None:
        (self.root / "CHANGELOG.md").write_text(changelog(NOTES), encoding="utf-8")
        errors, scope = check_changelog.check(self.root, "main")
        self.assertEqual((errors, scope[:13]), ([], "compared with"))
        (self.root / "CHANGELOG.md").write_text(changelog(history=HISTORY.replace("Old", "New")), encoding="utf-8")
        errors, _ = check_changelog.check(self.root, "main")
        self.assertIn("changed since", "\n".join(errors))

    def test_without_base_only_structure_is_checked(self) -> None:
        (self.root / "CHANGELOG.md").write_text(changelog(history=HISTORY.replace("Old", "New")), encoding="utf-8")
        errors, scope = check_changelog.check(self.root)
        self.assertEqual(errors, [])
        self.assertIn("no --base", scope)

    def test_the_command_fails_with_its_remedy(self) -> None:
        (self.root / "CHANGELOG.md").write_text("# Changelog\n\n" + HISTORY, encoding="utf-8")
        output = io.StringIO()
        with patch.object(check_changelog, "ROOT", self.root), redirect_stdout(output):
            status = check_changelog.main(["--base", "main"])
        self.assertEqual(status, 1)
        self.assertIn("add an empty one above the newest release", output.getvalue())
        self.assertIn("docs/changelog.md", output.getvalue())


if __name__ == "__main__":
    unittest.main()
