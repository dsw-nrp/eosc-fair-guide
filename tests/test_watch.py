"""The scheduled live watch: outcome classes, fair selection under a budget and per-host cap, durable state with
migration and visible resets, page items without pagination, reviewed limitations, and one digest that comments only
on meaningful change and tracks maintainers' tasks."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import tomllib
import unittest
import urllib.error
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402
import watch_sources  # noqa: E402

TODAY = date(2026, 10, 12)
PAGE = """<html><body><header><a href="/menu">Menu</a></header><nav><a href="/other">Other</a></nav>
<main><h2 id="outputs">Outputs</h2><a href="/media/report.pdf">Report 2026</a>{extra}
<nav><a href="/inner-nav">Inner navigation</a></nav></main>
<footer><a href="/footer">Footer</a></footer></body></html>"""
PLAN = {"run_url": "https://github.com/o/r/actions/runs/7", "run_id": "7", "repository": "o/r", "notice": ""}


def content(**extra: object) -> dict:
    return {
        "guide": {"guide": {"freshnessDays": 180}, "person": [{"id": "david-novak"}]},
        "resources": [
            {"id": "a", "url": "https://a.example/ok", "asOf": date(2026, 10, 1)},
            {"id": "b", "url": "https://b.example/gone", "asOf": date(2025, 1, 1)},
            {"id": "c", "url": "http://plain.example/insecure"},
        ],
        "live": {
            "connector": [{"id": "svc", "origin": "https://svc.example"}],
            "watch": [{"id": "outputs", "url": "https://www.eosc.example/outputs"}],
            "champion": {"test": [curated("core_test")]},
            **extra,
        },
    }


def curated(guide_id: str, provider_id: str | None = None, health: str = "degraded") -> dict:
    """A curated Champion test as the build requires it: its own ID and the provider's as a typed alternate."""
    return {
        "id": guide_id,
        "alternateIds": [{"scheme": "fair-champion", "value": provider_id or guide_id}],
        "health": health,
        "asOf": date(2026, 10, 11),
    }


class Fetcher:
    def __init__(self, page: str = PAGE.format(extra=""), status: dict[str, int | None] | None = None):
        self.page, self.status, self.calls = page, status or {}, []

    def __call__(self, url: str, body: bool) -> tuple[int | None, bytes, str]:
        self.calls.append(url)
        for prefix, status in self.status.items():
            if url.startswith(prefix):
                return status, b"", "timed out" if status is None else f"HTTP {status}"
        return 200, self.page.encode() if body else b"", ""


class Run:
    """Successive watch runs over one content and one state, as the workflow chains them."""

    def __init__(self, data: dict | None = None, limitations: dict | None = None):
        self.content, self.limitations = data or content(), limitations or {}
        self.state, self.reported, self.day = watch_sources.empty_state(), {}, TODAY

    def __call__(self, fetcher: Fetcher, champion: dict | None = None, tasks: list | None = None, notice: str = ""):
        observations, self.state, coverage = watch_sources.observe(
            self.content, self.state, fetcher, champion, self.day, sleep=lambda _: None
        )
        found = watch_sources.findings(self.content, self.state, self.limitations, self.day)
        outcomes = {key: value.get("outcome") for key, value in self.state["targets"].items()}
        plan = {**PLAN, "notice": notice, "coverage": coverage, "findings": found, "outcomes": outcomes}
        body, comment, self.reported = watch_sources.render(plan, tasks or [], "", self.reported, self.day)
        self.state["reported"] = self.reported
        self.day += timedelta(days=7)
        return {item["key"]: item for item in found}, body, comment, observations, coverage


class OutcomeTests(unittest.TestCase):
    def test_only_a_missing_address_is_broken(self) -> None:
        cases = {200: "ok", 301: "ok", 404: "broken", 410: "broken", 401: "denied", 403: "denied", 451: "denied"}
        cases |= {429: "rate-limited", 500: "unavailable", 503: "unavailable", 400: "unavailable", None: "unavailable"}
        for status, outcome in cases.items():
            with self.subTest(status=status):
                self.assertEqual(watch_sources.classify(status), outcome)

    def test_persistent_failures_enter_triage_and_recover_without_a_verdict(self) -> None:
        fresh = content()
        fresh["resources"][1]["asOf"] = date(2026, 10, 1)  # no stale status, so only the failures are findings
        run = Run(fresh)
        failing = Fetcher(status={"https://svc.example": None, "https://b.example/gone": 403})
        found, _, comment, _, _ = run(failing)
        self.assertNotIn("link:https://b.example/gone", found, "one failing check is transient")
        self.assertEqual(comment, "")
        found, body, comment, _, _ = run(failing)
        link = found["link:https://b.example/gone"]
        self.assertEqual((link["section"], link["outcome"]), ("triage", "denied"))
        self.assertIn("refused access (GET 403)", link["line"])
        self.assertNotIn("is gone", link["line"], "a denial never claims the page is gone")
        self.assertIn("never a failed requirement", found["connector:svc"]["line"])
        self.assertIn("**New** (2)", comment)
        self.assertIn("<!-- fair-guide-digest-run id=7 -->", comment)
        self.assertIn("## Needs triage (2)", body)
        found, body, comment, _, _ = run(Fetcher())
        self.assertNotIn("connector:svc", found)
        self.assertIn("**Recovered** (2)", comment)
        self.assertIn("## Needs triage (0)", body)


class FetchTests(unittest.TestCase):
    """A server that rejects HEAD is judged by its GET answer; a missing or throttled address is not asked twice. The
    requests are answered in process, so no test reaches the network."""

    @staticmethod
    def fetch(head: int, get: int) -> tuple[watch_sources.Answer, list[str]]:
        sent: list[str] = []
        raised: list[urllib.error.HTTPError] = []

        def urlopen(request, timeout):
            sent.append(request.get_method())
            status = head if request.get_method() == "HEAD" else get
            if status >= 400:
                raised.append(urllib.error.HTTPError(request.full_url, status, "refused", {}, None))
                raise raised[-1]
            response = mock.MagicMock(status=status)
            response.__enter__.return_value = response
            return response

        with mock.patch("urllib.request.urlopen", urlopen):
            answer = watch_sources.fetch("https://a.example/survey.pdf", False)
        for error in raised:
            error.close()
        return answer, sent

    def test_only_a_rejected_head_is_repeated_with_get(self) -> None:
        cases = {  # (HEAD, GET) answer: final status, outcome, methods sent
            (400, 200): (200, "ok", ["HEAD", "GET"]),
            (403, 403): (403, "denied", ["HEAD", "GET"]),
            (429, 200): (429, "rate-limited", ["HEAD"]),
            (404, 200): (404, "broken", ["HEAD"]),
        }
        for (head, get), (status, outcome, sent) in cases.items():
            with self.subTest(head=head, get=get):
                answer, requests = self.fetch(head, get)
                self.assertEqual((answer.status, watch_sources.classify(answer.status)), (status, outcome))
                self.assertEqual(requests, sent)
                self.assertEqual(answer.method, " then ".join(sent))


class CoverageTests(unittest.TestCase):
    def test_every_unchanged_link_is_attempted_within_two_runs(self) -> None:
        guide = build_crate.load_content()
        links, _ = watch_sources.content_links(guide)
        hosts = Counter(urlparse(url).hostname for url in links)
        over_cap = sum(max(0, count - watch_sources.PER_HOST) for count in hosts.values())
        self.assertGreater(over_cap, 0, "the Guide's own inventory exercises the per-host cap")
        run = Run(guide)
        first = run(Fetcher())[4]
        second = run(Fetcher())[4]
        for coverage in (first, second):
            self.assertEqual(coverage["eligible"], coverage["attempted"] + coverage["deferred"])
            self.assertLessEqual(coverage["attempted"], watch_sources.BUDGET)
        # The busiest host's cap, and the run budget once the inventory outgrows it, defer the rest to the second run.
        attempted = min(watch_sources.BUDGET, len(links) - over_cap)
        self.assertEqual((first["attempted"], first["deferred"]), (attempted, len(links) - attempted))
        never = [key for key, value in run.state["targets"].items() if value["kind"] == "link" and not value["checked"]]
        self.assertEqual(never, [], "every link was attempted within two runs")

    def test_a_deferred_failure_keeps_its_dated_observation(self) -> None:
        run = Run()
        failing = Fetcher(status={"https://b.example/gone": 404})
        run(failing)
        found, *_ = run(failing)
        checked = run.state["targets"]["link:https://b.example/gone"]["checked"]
        with mock.patch.object(watch_sources, "BUDGET", 1):  # only the least recently attempted link fits
            found, body, comment, observations, coverage = run(Fetcher())
        target = run.state["targets"]["link:https://b.example/gone"]
        self.assertEqual((target["streak"], target["checked"], target["outcome"]), (2, checked, "broken"))
        self.assertIn(f"not rechecked this run, last checked {checked}", found["link:https://b.example/gone"]["line"])
        self.assertNotIn("Recovered", comment, "a deferred target neither fails again nor recovers")
        self.assertEqual(coverage["deferred"], 2, "three links (the watched page too), one attempted")
        self.assertIn("2 deferred to a later run", body)

    def test_a_throttling_host_stops_and_other_hosts_are_still_attempted(self) -> None:
        urls = [f"https://slow.example/{n}" for n in range(5)] + [f"https://fast.example/{n}" for n in range(5)]
        waits = []

        def throttled(retry):
            def fetch(url, body):
                return (429, b"", "HTTP 429", "HEAD", retry) if url.startswith("https://slow") else (200, b"", "")

            return fetch

        answers = watch_sources.attempt(urls, throttled(None), waits.append)
        self.assertEqual(sorted(url for url in answers if "slow" in url), ["https://slow.example/0"])
        self.assertEqual(len([url for url in answers if "fast" in url]), 5)
        watch_sources.attempt(urls, throttled(5), waits.append)
        self.assertEqual(waits, [5], "a short Retry-After is honoured once")
        watch_sources.attempt(urls, throttled(600), waits.append)
        self.assertEqual(waits, [5], "a long Retry-After is not waited for")
        silent = watch_sources.attempt(
            urls, lambda url, body: (None, b"", "timed out") if "slow" in url else (200, b"", "")
        )
        self.assertEqual(len([url for url in silent if "slow" in url]), watch_sources.UNRESPONSIVE)

    def test_links_that_cannot_be_checked_are_counted_as_invalid(self) -> None:
        _, body, _, _, coverage = Run()(Fetcher())
        self.assertEqual(coverage["invalid"], 1)
        self.assertIn("Not checkable: `resources[c].url`", body)


class StateTests(unittest.TestCase):
    def test_version_1_migrates_and_a_missing_or_malformed_state_is_a_visible_reset(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "format_version": 1,
                        "streaks": {"link:https://b.example/gone": 3, "stale:x": 1},
                        "pages": {"outputs": {"#outputs": "abc"}},
                    }
                ),  # fmt: skip
                encoding="utf-8",
            )
            state, notice = watch_sources.load_state(path)
            self.assertEqual(notice, "")
            self.assertEqual(state["targets"]["link:https://b.example/gone"]["streak"], 3)
            self.assertNotIn("stale:x", state["targets"])
            self.assertEqual(state["pages"], {"outputs": {"#outputs": "abc"}}, "baselines are kept")
            for text in ("{not json", json.dumps({"format_version": 9})):
                path.write_text(text, encoding="utf-8")
                self.assertIn("restarts every streak", watch_sources.load_state(path)[1])
            self.assertIn("No previous watch state", watch_sources.load_state(Path(temp) / "missing.json")[1])
        run = Run()
        _, body, comment, _, _ = run(Fetcher(status={"https://b.example/gone": 404}), notice="No previous state.")
        self.assertIn("> **State reset:** No previous state.", body)
        self.assertNotIn("Recovered", comment)

    def test_a_migrated_streak_continues(self) -> None:
        run = Run()
        run.state = watch_sources.migrate({"format_version": 1, "streaks": {"link:https://b.example/gone": 1}})
        found, *_ = run(Fetcher(status={"https://b.example/gone": 404}))
        self.assertEqual(found["link:https://b.example/gone"]["section"], "triage", "streak 1 + 1 reaches persistence")

    def test_targets_that_content_no_longer_names_leave_the_state(self) -> None:
        data = content()
        data["live"]["watch"] += [
            {"id": "events", "url": "https://events.example/list"},
            {"id": "kept", "url": "https://kept.example/news"},
        ]
        data["live"]["champion"]["test"].append(curated("gone_test"))
        measured = {"id": "core_test", "health": "available", "attempted": 3, "definitive": 3, "indeterminate": 0}
        champion = {"generatedAt": "2026-10-12T03:00:00Z", "summary": [measured, {**measured, "id": "gone_test"}]}
        failing = {"https://events.example": 503, "https://kept.example": 503}
        run = Run(data)
        run(Fetcher(status=failing), champion)
        found, *_ = run(Fetcher(page=PAGE.format(extra='<a href="/media/new.pdf">New</a>'), status=failing), champion)
        item = "page:outputs:https://www.eosc.example/media/new.pdf"
        listed = {"watch:events", "watch:kept", "champion:core_test", "champion:gone_test", item}
        self.assertLessEqual(listed, set(found))
        # The maintainers stop watching two pages and drop one core test; the next run does not remeasure Champion.
        data["live"]["watch"] = [page for page in data["live"]["watch"] if page["id"] == "kept"]
        tests = data["live"]["champion"]["test"]
        data["live"]["champion"]["test"] = [test for test in tests if test["id"] == "core_test"]
        found, body, *_ = run(Fetcher(status=failing))
        for key in ("watch:events", "watch:outputs", "champion:gone_test"):
            self.assertNotIn(key, run.state["targets"])
            self.assertNotIn(key, found)
        self.assertNotIn(item, run.state["sources"])
        self.assertNotIn(item, found)
        self.assertEqual(set(run.state["pages"]), set(), "no baseline is kept for a page no longer watched")
        self.assertNotIn("events.example", body)
        self.assertEqual(run.state["targets"]["watch:kept"]["streak"], 3, "a page still watched keeps its streak")
        self.assertEqual(found["champion:core_test"]["section"], "triage", "a test still listed stays")

    def test_curated_tests_are_matched_by_their_champion_identifier(self) -> None:
        # Five curated tests have their own ID, such as fc-metadata-pid; the probe names the provider's.
        provider = "fc_metadata_identifier_persistence"
        key = f"champion:{provider}"
        data = content()
        data["live"]["champion"]["test"].append(curated("fc-metadata-pid", provider, health="available"))

        def remeasured(health: str, definitive: int) -> dict:
            summary = {"id": provider, "health": health, "attempted": 3, "definitive": definitive, "indeterminate": 0}
            return {"generatedAt": "2026-10-12T03:00:00Z", "summary": [summary]}

        run = Run(data)
        # State left by a run that matched the Guide's own ID: the selected test was proposed as a candidate.
        run.state["targets"][f"champion-candidate:{provider}"] = {"kind": "champion-candidate", "outcome": "candidate"}
        found, *_ = run(Fetcher(), remeasured("available", 3))
        self.assertEqual(run.state["targets"][key]["outcome"], "matches")
        self.assertNotIn(f"champion-candidate:{provider}", run.state["targets"], "a selected test is no candidate")
        self.assertNotIn(f"champion-candidate:{provider}", found)
        run(Fetcher(), remeasured("degraded", 1))
        found, *_ = run(Fetcher(), remeasured("degraded", 1))
        self.assertEqual(found[key]["section"], "triage", "a measured health that differs from the record")
        self.assertIn(f"`{provider}` measured `degraded`, recorded `available`", found[key]["line"])
        # The maintainers drop it from the selection; the next run does not remeasure Champion.
        tests = data["live"]["champion"]["test"]
        data["live"]["champion"]["test"] = [test for test in tests if test["id"] != "fc-metadata-pid"]
        found, *_ = run(Fetcher())
        self.assertNotIn(key, run.state["targets"])
        self.assertNotIn(key, found)


class PageTests(unittest.TestCase):
    def test_pagination_and_navigation_are_not_new_items(self) -> None:
        # Issue #101: the training page's "Další" link to ?page=2 was reported as a new item.
        pager = (
            '<a href="/outputs?page=2">Další</a><a rel="next" href="/outputs/older">Older posts</a>'
            '<ul class="pagination"><li><a href="/outputs/p3">3</a></li></ul><a href="/outputs?page=4">4</a>'
            '<a href="/media/annual.pdf">2026</a>'
        )
        items = watch_sources.page_items("https://www.eosc.example/outputs", PAGE.format(extra=pager).encode())
        self.assertEqual(
            set(items),
            {"#outputs", "https://www.eosc.example/media/report.pdf", "https://www.eosc.example/media/annual.pdf"},
        )
        run = Run()
        run(Fetcher())
        found, _, comment, _, _ = run(Fetcher(page=PAGE.format(extra=pager)))
        sources = [item for item in found.values() if item["section"] == "source"]
        self.assertEqual([item["key"] for item in sources], ["page:outputs:https://www.eosc.example/media/annual.pdf"])
        self.assertIn("New item on `https://www.eosc.example/outputs` since 2026-10-19: 2026", sources[0]["line"])


class LimitationTests(unittest.TestCase):
    ENTRY = {
        "key": "link:https://b.example/gone",
        "outcome": "denied",
        "reason": "The publisher blocks automated requests from data centres.",
        "evidence": "HEAD 403 then GET 403 from GitHub-hosted runners since 2026-09-01",
        "reviewer": "david-novak",
        "reviewed": date(2026, 10, 1),
        "reviewBy": date(2026, 10, 25),
    }

    def test_entries_name_one_target_with_a_basis(self) -> None:
        self.assertEqual(watch_sources.limitation_errors([self.ENTRY], {"david-novak"}), [])
        cases = {
            "without wildcards": {**self.ENTRY, "key": "link:https://b.example/*"},
            "evidence must state": {**self.ENTRY, "evidence": ""},
            "reviewer must be": {**self.ENTRY, "reviewer": "someone"},
            "reviewBy after reviewed": {**self.ENTRY, "reviewBy": date(2026, 9, 1)},
            "outcome must be one of": {**self.ENTRY, "outcome": "fine"},
        }
        for message, entry in cases.items():
            with self.subTest(message=message):
                self.assertIn(message, "\n".join(watch_sources.limitation_errors([entry], {"david-novak"})))
        conflict = watch_sources.limitation_errors([self.ENTRY, dict(self.ENTRY)], {"david-novak"})
        self.assertIn("conflicts with limitation[0]", "\n".join(conflict))

    def test_a_reviewed_denial_is_known_and_a_change_or_expiry_returns_it_to_triage(self) -> None:
        run = Run(limitations={self.ENTRY["key"]: self.ENTRY})
        denied = Fetcher(status={"https://b.example/gone": 403})
        run(denied)
        found, body, _, _, _ = run(denied)
        self.assertEqual(found[self.ENTRY["key"]]["section"], "limitation")
        self.assertIn("## Known limitations (1)", body)
        self.assertNotIn("Track as task](https://github.com/o/r/issues/new?title=Maintenance%3A+Link+https", body)
        found, _, comment, _, _ = run(denied)  # 2026-10-26: the review-by date has passed
        self.assertEqual(found[self.ENTRY["key"]]["section"], "triage")
        self.assertIn("review-by date 2026-10-25 passed", found[self.ENTRY["key"]]["line"])
        self.assertIn("**Expired** (1)", comment)
        self.assertEqual(run(denied)[2], "", "an expiry is announced once")
        run = Run(limitations={self.ENTRY["key"]: {**self.ENTRY, "reviewBy": date(2027, 1, 1)}})
        gone = Fetcher(status={"https://b.example/gone": 404})
        run(gone)
        self.assertIn("expects denied", run(gone)[0][self.ENTRY["key"]]["line"])

    def test_a_limitation_with_a_task_says_the_outcome_changed_only_when_it_did(self) -> None:
        run = Run(limitations={self.ENTRY["key"]: {**self.ENTRY, "reviewBy": date(2027, 1, 1)}})
        denied = Fetcher(status={"https://b.example/gone": 403})
        run(denied)
        task = {"key": self.ENTRY["key"], "outcome": "denied", "number": 14, "state": "open"}
        found, body, *_ = run(denied, tasks=[task])
        self.assertEqual(found[self.ENTRY["key"]]["section"], "limitation")
        known = body.split("## Known limitations (1)")[1]
        self.assertIn("Task #14 (open)", known)
        self.assertNotIn("The outcome changed", body)
        _, body, *_ = run(denied, tasks=[{**task, "outcome": "broken"}])
        self.assertIn("The outcome changed since task #14.", body.split("## Known limitations (1)")[1])

    def test_a_new_denial_offers_a_ready_to_paste_entry(self) -> None:
        run = Run()
        denied = Fetcher(status={"https://b.example/gone": 403})
        run(denied)
        found, body, _, _, _ = run(denied)
        entry = tomllib.loads(found["link:https://b.example/gone"]["suggestion"])["limitation"][0]
        self.assertEqual(
            (entry["key"], entry["outcome"], entry["reviewer"]), ("link:https://b.example/gone", "denied", "")
        )
        self.assertIn("```toml", body)

    def test_a_limitation_for_a_target_no_longer_checked_asks_for_removal(self) -> None:
        orphan = {**self.ENTRY, "key": "link:https://removed.example/"}
        found, *_ = Run(limitations={orphan["key"]: orphan})(Fetcher())
        self.assertIn("no longer checks", found["limitation:link:https://removed.example/"]["line"])

    def test_the_repository_file_is_valid(self) -> None:
        with mock.patch("builtins.print"):
            self.assertEqual(watch_sources.main(["check-config"]), 0)


class DigestTests(unittest.TestCase):
    def test_only_dates_and_counters_advancing_posts_no_comment(self) -> None:
        run = Run()
        failing = Fetcher(status={"https://b.example/gone": 404})
        run(failing)
        self.assertNotEqual(run(failing)[2], "")
        _, body, comment, _, _ = run(failing)
        self.assertEqual(comment, "", "the body is rebuilt, nothing is announced")
        self.assertIn(watch_sources.DIGEST_MARKER, body)
        self.assertIn("in 3 checks", body)

    def test_tasks_track_findings_keep_dispositions_and_a_changed_outcome_returns_to_triage(self) -> None:
        run = Run()
        failing = Fetcher(status={"https://b.example/gone": 404})
        run(failing)
        found, body, _, _, _ = run(failing)
        link = next(part for part in body.split("](") if part.startswith("https://github.com/o/r/issues/new?"))
        query = parse_qs(urlparse(link.split(")")[0]).query)
        self.assertEqual(query["labels"], ["area:maintenance"])
        self.assertIn(
            "<!-- fair-guide-finding key=link%3Ahttps%3A%2F%2Fb.example%2Fgone outcome=broken -->", query["body"][0]
        )
        task = {"key": "link:https://b.example/gone", "outcome": "broken", "number": 12, "state": "open"}
        _, body, comment, _, _ = run(failing, tasks=[task])
        self.assertIn("## Tracked (1)", body)
        self.assertIn("Task #12 (open)", body)
        self.assertIn("**Changed** (1)", comment, "moving into tracked is a change, announced once")
        closed = {**task, "state": "closed", "reason": "not_planned", "closed": "2026-11-01T10:00:00Z"}
        _, body, comment, _, _ = run(failing, tasks=[closed])
        self.assertIn("Task #12 (closed as not_planned on 2026-11-01)", body)
        self.assertEqual(comment, "", "a closed task keeps its disposition without reopening anything")
        _, body, comment, _, _ = run(Fetcher(status={"https://b.example/gone": 403}), tasks=[closed])
        run(Fetcher(status={"https://b.example/gone": 403}), tasks=[closed])
        self.assertIn(
            "The outcome changed since task #12.",
            run(Fetcher(status={"https://b.example/gone": 403}), tasks=[closed])[1],
        )

    def test_stale_statuses_and_champion_candidates_are_sections(self) -> None:
        champion = {
            "generatedAt": "2026-10-12T03:00:00Z",
            "summary": [
                {"id": "core_test", "health": "available", "attempted": 3, "definitive": 2, "indeterminate": 1},
                {"id": "candidate_test", "health": "available", "attempted": 3, "definitive": 3, "indeterminate": 0},
            ],
        }
        run = Run()
        found, body, *_ = run(Fetcher(), champion)
        self.assertEqual(found["stale:resources[b].asOf"]["section"], "stale")
        # The knowledge-base scenario: the digest names the resource and its last verified date for triage.
        self.assertIn("## Stale statuses (1)", body)
        self.assertIn("`resources[b].asOf` is dated 2025-01-01", body)
        self.assertEqual(found["champion-candidate:candidate_test"]["section"], "candidate")
        self.assertIn("not a selection", body)
        found, body, *_ = run(Fetcher())  # a weekly run without remeasurement keeps the candidate
        self.assertIn("champion-candidate:candidate_test", found)
        found, *_ = run(Fetcher(), champion)
        self.assertIn("indeterminate verdict is a result", found["champion:core_test"]["line"])

    def test_the_body_stays_within_the_issue_limit(self) -> None:
        many = {
            "live": {
                **content()["live"],
                "connector": [{"id": f"s{n}", "origin": f"https://s{n}.example"} for n in range(400)],
            }
        }
        run = Run({**content(), **many})
        down = Fetcher(status={"https://s": None})
        run(down)
        _, body, _, _, _ = run(down)
        self.assertLessEqual(len(body), watch_sources.BODY_LIMIT)
        self.assertIn("more in the run's observations artifact", body)

    def test_an_outage_of_one_host_is_one_entry_that_a_task_or_a_limitation_can_address(self) -> None:
        # 27 October 2026: 17 links on one unreachable host became 17 issues. In the digest they are one entry. (A host
        # that stops answering altogether is asked no further in a run, so its links surface over several runs; one
        # answering 503 for each fails them all at once.)
        links = [{"id": f"d{n}", "url": f"https://down.example/item/{n}"} for n in range(17)]
        data = {**content(), "resources": [*content()["resources"], *links]}
        failing = Fetcher(status={"https://down.example/": 503, "https://b.example/gone": 404})
        run = Run(data)
        run(failing)
        found, body, comment, _, _ = run(failing)
        self.assertIn("## Needs triage (2)", body, "the host's entry and the other broken link")
        self.assertIn("17 links on `down.example` did not answer", body)
        self.assertIn("<details><summary>The 17 links</summary>", body)
        for link in links:
            self.assertIn(link["url"], body, "every link stays visible in the issue")
        group = next(part for part in body.split("](") if "link-host%253Adown.example" in part)
        query = parse_qs(urlparse(group.split(")")[0]).query)
        self.assertIn("<!-- fair-guide-finding key=link-host%3Adown.example outcome=unavailable -->", query["body"][0])
        self.assertEqual(sum(key.startswith("link:https://down.example/") for key in run.reported), 17)
        self.assertIn("**New** (18)", comment, "each finding keeps its own key for change comments")
        task = {"key": "link-host:down.example", "outcome": "unavailable", "number": 30, "state": "open"}
        _, body, _, _, _ = run(failing, tasks=[task])
        self.assertIn("## Tracked (1)", body)
        self.assertIn("17 links on `down.example` did not answer. Task #30 (open)", body)
        self.assertIn("## Needs triage (1)", body)
        reviewed = {
            "link:https://down.example/item/3": {
                "outcome": "unavailable",
                "reviewer": "david-novak",
                "reviewed": TODAY,
                "reviewBy": TODAY + timedelta(days=90),
                "reason": "planned maintenance",
            }
        }
        run = Run(data, limitations=reviewed)
        run(failing)
        _, body, _, _, _ = run(failing)
        self.assertIn("16 links on `down.example` did not answer", body)
        self.assertIn("## Known limitations (1)", body, "a reviewed link stays a finding of its own")

    def test_a_long_section_continues_collapsed_in_the_body(self) -> None:
        links = [{"id": f"h{n}", "url": f"https://host{n}.example/page"} for n in range(30)]
        data = {**content(), "resources": [*content()["resources"], *links]}
        failing = Fetcher(status={"https://host": 404, "https://b.example/gone": 404})
        run = Run(data)
        run(failing)
        _, body, _, _, _ = run(failing)
        self.assertIn("## Needs triage (31)", body)
        self.assertIn("<details><summary>6 more</summary>", body)
        for link in links:
            self.assertIn(link["url"], body, "no finding is only in the artifact")
        self.assertNotIn("more in the run's observations artifact", body)
        self.assertLessEqual(len(body), watch_sources.BODY_LIMIT)

    def test_sources_the_latest_scheduled_refresh_did_not_refresh_are_listed_until_refreshed(self) -> None:
        # 26 October 2026: heslar and nkr were not refreshed, and only a red run said so. The digest lists them.
        url = "https://github.com/o/r/actions/runs/40313332538"
        coverage = {"eligible": 0, "attempted": 0, "deferred": 0, "invalid": 0}
        plan = {**PLAN, "coverage": coverage, "findings": [], "outcomes": {}}
        outcomes = [
            {"source": "heslar", "status": "failed", "reason": "timed out"},
            {"source": "nkr", "status": "rejected", "reason": "3 records [lack](https://evil.example) an ID"},
            {"source": "re3data", "status": "changed"},
            {"source": "datacite", "status": "unchanged"},
        ]
        refresh = {"run_url": url, "date": "2026-10-26", "outcomes": outcomes}
        body, comment, reported = watch_sources.render(plan, [], "", {}, TODAY, refresh=refresh)
        self.assertIn("## Sources not refreshed (2)", body)
        self.assertIn("Source `heslar` was not retrieved, so its snapshot was kept; the next scheduled refresh", body)
        self.assertIn(f"(timed out); [run]({url}) of 2026-10-26", body)
        self.assertIn("Source `nkr` was rejected by validation", body)
        self.assertNotIn("](https://evil.example)", body, "a reason is external text")
        self.assertNotIn("`re3data`", body)
        self.assertIn("Under Sources not refreshed, a rejected source needs a maintainer", body)
        self.assertIn("**New** (2)", comment)
        self.assertEqual({key for key in reported if key.startswith("refresh:")}, {"refresh:heslar", "refresh:nkr"})
        refreshed = {
            **refresh,
            "outcomes": [{"source": "heslar", "status": "changed"}, {"source": "nkr", "status": "unchanged"}],
        }
        body, comment, _ = watch_sources.render(plan, [], "", reported, TODAY, refresh=refreshed)
        self.assertIn("## Sources not refreshed (0)", body)
        self.assertIn("**No longer listed** (2)", comment)
        for value, text in (
            (
                {"run_url": url, "outcomes": None},
                f"The latest scheduled Source refresh ([run]({url})) left no readable report",
            ),
            ({"run_url": "", "outcomes": None}, "No scheduled Source refresh run was found"),
            ({"run_url": "https://evil.example/runs/1", "outcomes": None}, "Source refresh run was found"),
        ):
            with self.subTest(refresh=value):
                body, _, reported = watch_sources.render(plan, [], "", {}, TODAY, refresh=value)
                self.assertIn(text, body)
                self.assertIn("so whether the sources are current is unknown", body)
                self.assertNotIn("evil.example", body, "only a GitHub run address is linked")
                self.assertEqual(list(reported), ["refresh:report"])

    def test_external_text_stays_inert(self) -> None:
        text = watch_sources.escape("<img src=x onerror=alert(1)> [link](https://evil.example) @team | `code`")
        self.assertNotIn("<img", text)
        self.assertNotIn("](", text)
        self.assertIn("@\u200bteam", text)
        self.assertIn("\\|", text)


class CommandTests(unittest.TestCase):
    def test_observe_and_render_write_their_outputs_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp) / "guide"
            shutil.copytree(ROOT / "tests/fixtures/minimal", fixture)
            watch, digest = Path(temp) / "watch", Path(temp) / "digest"
            (Path(temp) / "tasks.json").write_text("[]", encoding="utf-8")
            with mock.patch.object(watch_sources, "ROOT", fixture), mock.patch("builtins.print"):
                argv = ["observe", "--state", str(Path(temp) / "missing.json"), "--output", str(watch), "--no-network"]
                self.assertEqual(watch_sources.main(argv), 0)
                argv = [
                    "render",
                    "--watch",
                    str(watch),
                    "--tasks",
                    str(Path(temp) / "tasks.json"),
                    "--output",
                    str(digest),
                ]
                self.assertEqual(watch_sources.main([*argv, "--predecessor", "41"]), 0)
            observations = json.loads((watch / "observations.json").read_text(encoding="utf-8"))
            self.assertIn("not a FAIR verdict", observations["scope"])
            plan = json.loads((watch / "plan.json").read_text(encoding="utf-8"))
            self.assertIn("No previous watch state", plan["notice"])
            self.assertEqual(json.loads((watch / "state.json").read_text(encoding="utf-8"))["format_version"], 2)
            body = (digest / "body.md").read_text(encoding="utf-8")
            self.assertIn("Continues #41.", body)
            self.assertIn("The audit did not run this time.", body)
            self.assertIn("## Sources not refreshed (0)", body, "without a refresh lookup nothing is claimed")
            self.assertIn("reported", json.loads((digest / "state.json").read_text(encoding="utf-8")))
            # The publisher passes the latest scheduled refresh run, and its report when it could be downloaded.
            report = Path(temp) / "report.json"
            report.write_text(json.dumps({"formatVersion": 1, "outcomes": [{"source": "heslar", "status": "failed"}]}))
            run = ["--refresh-run", "https://github.com/o/r/actions/runs/9", "--refresh-date", "2026-10-26"]
            for extra, expected in (
                (["--refresh", str(report)], "Source `heslar` was not retrieved"),
                (["--refresh", str(Path(temp) / "absent.json")], "left no readable report"),
                ([], "left no readable report"),
            ):
                with (
                    self.subTest(extra=extra),
                    mock.patch.object(watch_sources, "ROOT", fixture),
                    mock.patch("builtins.print"),
                ):
                    self.assertEqual(watch_sources.main([*argv, *run, *extra]), 0)
                    self.assertIn(expected, (digest / "body.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
