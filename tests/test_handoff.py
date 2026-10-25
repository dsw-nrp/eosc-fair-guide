"""Every automated output ends with who acts next, the way round a blocker and the evidence of completion."""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_all  # noqa: E402
import check_ci  # noqa: E402
import fix_duplicates  # noqa: E402
import release_versions  # noqa: E402
import watch_sources  # noqa: E402
from handoff import LABELS, handoff  # noqa: E402


def result(name: str, code: int) -> check_all.Result:
    return check_all.Result(check_all.Job(name, []), code, 1.0, "" if code == 0 else "boom")


class HandoffTests(unittest.TestCase):
    def ends_with_handoff(self, text: str) -> list[str]:
        tail = [line for line in text.strip().splitlines() if line.strip()][-3:]
        self.assertEqual([line.split(":**")[0] for line in tail], [f"- **{label}" for label in LABELS], text)
        for line in tail:
            self.assertTrue(line.split(":** ", 1)[1].strip(), line)
        return tail

    def test_a_missing_element_is_refused(self) -> None:
        for index, label in enumerate(LABELS):
            values = ["act", "work round", "evidence"]
            values[index] = " "
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, label):
                handoff(*values)

    def test_check_summaries_name_the_failure_and_its_local_command(self) -> None:
        failed = self.ends_with_handoff(check_ci.quick_summary([result("content", 1), result("ruff", 0)]))
        self.assertIn("`python scripts/check_all.py --only content`", failed[0])
        self.ends_with_handoff(check_ci.quick_summary([result("content", 0)]))
        collected = self.ends_with_handoff(check_ci.collected_handoff([result("page", 1), result("unit", 0)]))
        self.assertIn("fix page and reproduce them with `python scripts/check_all.py --only page`", collected[0])
        self.assertIn("the next run's `checks` passes", collected[2])
        # A success says what remains instead of claiming the work is done; a rejection is not a failed check.
        passed = self.ends_with_handoff(check_ci.collected_handoff([result("page", 0)]))
        self.assertIn("waits for review and the merge queue", passed[0])
        rejected = self.ends_with_handoff(check_ci.collected_handoff([], rejected="lane evidence missing"))
        self.assertIn("re-run the failed jobs", rejected[0])

    def test_the_digest_and_the_watch_summary_end_with_triage(self) -> None:
        coverage = {"eligible": 1, "attempted": 1, "deferred": 0, "invalid": 0}
        sections = {name: [] for name in watch_sources.SECTIONS} | {"triage": ["a link is gone"]}
        body = watch_sources.digest_body({"coverage": coverage}, sections, "", date(2026, 10, 25))
        self.assertIn("triages the 1 findings under Needs triage", self.ends_with_handoff(body)[0])
        self.ends_with_handoff(watch_sources.summary([], coverage, date(2026, 10, 25), ""))

    def test_release_and_repair_replies_end_with_their_next_step(self) -> None:
        missing = {"previous": "v0.9.0", "pulls": ["- Merge #12"], "direct": []}
        report = release_versions.lineage_report("1.0.0", missing)
        self.assertIn("Tag release creates `v1.0.0`", self.ends_with_handoff(report)[2])
        reply = fix_duplicates.unchanged("No file was changed.", "post `/fix-duplicates` again.")
        self.assertIn("python scripts/check_duplicates.py --fix", self.ends_with_handoff(reply)[1])


if __name__ == "__main__":
    unittest.main()
