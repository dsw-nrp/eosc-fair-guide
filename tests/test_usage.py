"""Usage entries are named after their first session and carry the delivered labels."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_usage import FOLDER, ROOT, errors  # noqa: E402

FIELDS = "".join(
    f"- **{label}:** x\n" for label in ("Agent / runtime", "Model / backend", "What", "Impacted", "Close-out")
)


def session(when: str) -> str:
    return f"## Session\n\n- **When:** {when}\n{FIELDS}"


class UsageEntryTests(unittest.TestCase):
    def check(self, files: dict[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / FOLDER).mkdir(parents=True)
            for name, text in files.items():
                (root / FOLDER / name).write_text(text, encoding="utf-8")
            return errors(root)

    def test_the_repository_entries_pass(self) -> None:
        self.assertEqual(errors(ROOT), [])

    def test_a_rolling_entry_keeps_its_name_for_later_sessions(self) -> None:
        text = session("2026-10-20") + "\n" + session("2026-10-24")
        self.assertEqual(self.check({"usage-2026-10-20-ci-workflows.md": text}), [])

    def test_an_undated_entry_names_its_rename(self) -> None:
        found = self.check({"usage-ci-workflows.md": session("2026-10-24")})
        expected = f"{FOLDER}/usage-2026-10-24-ci-workflows.md"
        self.assertEqual(len(found), 1)
        self.assertIn(f"rename it to {expected} (git mv '{FOLDER}/usage-ci-workflows.md' '{expected}')", found[0])

    def test_a_date_other_than_the_first_session_names_the_expected_file(self) -> None:
        text = session("2026-10-20") + session("2026-10-24")
        found = self.check(
            {"usage-2026-10-24-ci-workflows.md": text, "usage-2026-02-30-other.md": session("2026-02-28")}
        )
        self.assertEqual(
            [line.split(" (git mv")[0] for line in found],
            [
                f"{FOLDER}/usage-2026-02-30-other.md: rename it to {FOLDER}/usage-2026-02-28-other.md",
                f"{FOLDER}/usage-2026-10-24-ci-workflows.md: rename it to {FOLDER}/usage-2026-10-20-ci-workflows.md",
            ],
        )

    def test_a_missing_or_near_miss_label_is_named(self) -> None:
        text = session("2026-10-20").replace("**Close-out:**", "**Closeout:**")
        found = self.check({"usage-2026-10-20-topic.md": text, "usage-2026-10-21-none.md": FIELDS})
        self.assertIn(f"{FOLDER}/usage-2026-10-20-topic.md: add the `**Close-out:**` field", found[0])
        self.assertIn(f"{FOLDER}/usage-2026-10-21-none.md: no `- **When:** YYYY-MM-DD` line", found[1])


if __name__ == "__main__":
    unittest.main()
