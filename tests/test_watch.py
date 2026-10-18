"""The scheduled live watch: persistence before an issue, recovery closes it, page items by main content only,
Champion remeasurement as attributable health and proposals, and inert external text."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import watch_sources  # noqa: E402

TODAY = date(2026, 10, 12)
PAGE = """<html><body><header><a href="/menu">Menu</a></header><nav><a href="/other">Other</a></nav>
<main><h2 id="outputs">Outputs</h2><a href="/media/report.pdf">Report 2026</a>{extra}
<nav><a href="/inner-nav">Inner navigation</a></nav></main>
<footer><a href="/footer">Footer</a></footer></body></html>"""


def content(**extra: object) -> dict:
    return {
        "guide": {"guide": {"freshnessDays": 180}},
        "resources": [
            {"id": "a", "url": "https://a.example/ok", "asOf": date(2026, 10, 1)},
            {"id": "b", "url": "https://b.example/gone", "asOf": date(2025, 1, 1)},
        ],
        "live": {
            "connector": [{"id": "svc", "origin": "https://svc.example"}],
            "watch": [{"id": "outputs", "url": "https://www.eosc.example/outputs"}],
            "champion": {"test": [{"id": "core_test", "health": "degraded", "asOf": date(2026, 10, 11)}]},
            **extra,
        },
    }


class Fetcher:
    def __init__(self, page: str = PAGE.format(extra=""), down: set[str] | None = None, gone: set[str] | None = None):
        self.page, self.down, self.gone = page, down or set(), gone or set()

    def __call__(self, url: str, body: bool) -> tuple[int | None, bytes, str]:
        if any(url.startswith(prefix) for prefix in self.down):
            return None, b"", "timed out"
        if url in self.gone:
            return 404, b"", "HTTP 404"
        return 200, self.page.encode() if body else b"", ""


class WatchTests(unittest.TestCase):
    def run_once(self, state: dict, fetcher: Fetcher, champion: dict | None = None) -> tuple[list, dict, list]:
        observations, state = watch_sources.observe(content(), state, fetcher, champion, TODAY)
        return observations, state, watch_sources.plan(observations, "https://github.com/o/r/actions/runs/1", TODAY)

    @staticmethod
    def keyed(actions: list, kind: str) -> dict:
        return {action["key"]: action for action in actions if action["action"] == kind}

    def test_failures_become_issues_only_after_they_persist_and_close_on_recovery(self) -> None:
        failing = Fetcher(down={"https://svc.example"}, gone={"https://b.example/gone"})
        observations, state, actions = self.run_once({}, failing)
        statuses = {item["key"]: item["status"] for item in observations}
        self.assertEqual(statuses["link:https://b.example/gone"], "broken")
        self.assertEqual(statuses["connector:svc"], "unavailable")
        self.assertEqual(statuses["link:https://a.example/ok"], "ok")
        self.assertNotIn("link:https://b.example/gone", self.keyed(actions, "open"), "one failing run is transient")
        _, state, actions = self.run_once(state, failing)
        opened = self.keyed(actions, "open")
        self.assertIn("is broken", opened["link:https://b.example/gone"]["title"])
        self.assertIn("never a failed requirement", opened["connector:svc"]["body"])
        _, state, actions = self.run_once(state, Fetcher())
        self.assertIn("connector:svc", self.keyed(actions, "close"))
        self.assertEqual(state["streaks"]["connector:svc"], 0)

    def test_page_items_come_from_main_content_with_a_baseline_first(self) -> None:
        items = watch_sources.page_items("https://www.eosc.example/outputs", PAGE.format(extra="").encode())
        self.assertEqual(set(items), {"#outputs", "https://www.eosc.example/media/report.pdf"})
        observations, state, actions = self.run_once({}, Fetcher())
        self.assertEqual(next(item for item in observations if item["kind"] == "watch")["status"], "baseline")
        self.assertFalse([key for key in self.keyed(actions, "open") if key.startswith("watch:")])
        changed = PAGE.format(extra='<a href="/media/new.pdf">New guidance @team</a>').replace(
            "Report 2026", "Report 2026 v2"
        )
        observations, state, actions = self.run_once(state, Fetcher(page=changed))
        page_issues = [action for key, action in self.keyed(actions, "open").items() if key.startswith("watch:")]
        self.assertEqual(
            sorted(action["title"].split(":")[0] for action in page_issues),
            ["EOSC CZ new item", "EOSC CZ updated item"],
        )
        self.assertTrue(all("@\u200bteam" in action["body"] or "@" not in action["body"] for action in page_issues))
        observations, state, actions = self.run_once(state, Fetcher(page=changed))
        self.assertFalse([key for key in self.keyed(actions, "open") if key.startswith("watch:")], "no repeat")
        many = PAGE.format(
            extra="".join(f'<a href="/n{n}">Item {n}</a>' for n in range(watch_sources.PAGE_ITEM_LIMIT + 1))
        )
        _, _, actions = self.run_once(state, Fetcher(page=many))
        page_issues = [key for key in self.keyed(actions, "open") if key.startswith("watch:")]
        self.assertEqual(len(page_issues), 1, "a large change is one issue for the page")

    def test_champion_remeasurement_is_attributable_health_and_candidates_are_proposals(self) -> None:
        champion = {
            "generatedAt": "2026-10-12T03:00:00Z",
            "summary": [
                {"id": "core_test", "health": "available", "attempted": 3, "definitive": 2, "indeterminate": 1},
                {"id": "candidate_test", "health": "available", "attempted": 3, "definitive": 3, "indeterminate": 0},
                {"id": "weak_candidate", "health": "unavailable", "attempted": 3, "definitive": 0, "indeterminate": 0},
            ],
        }
        _, state, actions = self.run_once({}, Fetcher(), champion)
        self.assertNotIn("champion:core_test", self.keyed(actions, "open"))
        self.assertIn("champion-candidate:candidate_test", self.keyed(actions, "open"))
        self.assertNotIn("champion-candidate:weak_candidate", self.keyed(actions, "open"))
        _, state, actions = self.run_once(state, Fetcher(), champion)
        body = self.keyed(actions, "open")["champion:core_test"]["body"]
        self.assertIn("indeterminate verdict is a result, not a transport failure", body)
        self.assertIn("2026-10-12T03:00:00Z", body)
        champion["summary"][0]["health"] = "degraded"
        _, _, actions = self.run_once(state, Fetcher(), champion)
        self.assertIn("champion:core_test", self.keyed(actions, "close"))

    def test_stale_dated_statuses_are_one_issue(self) -> None:
        _, _, actions = self.run_once({}, Fetcher())
        stale = self.keyed(actions, "open")["stale-statuses"]
        self.assertIn("resources[b].asOf", stale["body"])
        self.assertNotIn("resources[a]", stale["body"])

    def test_external_text_stays_inert(self) -> None:
        text = watch_sources.escape("<img src=x onerror=alert(1)> [link](https://evil.example) @team | `code`")
        self.assertNotIn("<img", text)
        self.assertNotIn("](", text)
        self.assertIn("@\u200bteam", text)
        self.assertIn("\\|", text)

    def test_the_run_writes_observations_plan_state_and_summary_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp) / "guide"
            shutil.copytree(ROOT / "tests/fixtures/minimal", fixture)
            output = Path(temp) / "watch"
            with mock.patch.object(watch_sources, "ROOT", fixture), mock.patch("builtins.print"):
                code = watch_sources.main(
                    ["--state", str(Path(temp) / "missing.json"), "--output", str(output), "--no-network"]
                )
            self.assertEqual(code, 0)
            observations = json.loads((output / "observations.json").read_text(encoding="utf-8"))
            self.assertIn("not a FAIR verdict", observations["scope"])
            self.assertTrue(
                all(item["status"] != "ok" for item in observations["observations"] if item["kind"] == "link")
            )
            self.assertEqual(json.loads((output / "issues.json").read_text(encoding="utf-8"))["format_version"], 1)
            self.assertIn("streaks", json.loads((output / "state.json").read_text(encoding="utf-8")))
            self.assertIn("none is a failed FAIR requirement", (output / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
