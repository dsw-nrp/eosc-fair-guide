#!/usr/bin/env python3
"""Scheduled live monitoring: links, connector availability, the EOSC CZ pages the guide depends on and FAIR
Champion remeasurement, turned into a bounded plan of issues keyed for deduplication.

    python scripts/watch_sources.py --state STATE.json --output DIR [--champion PROBE.json] [--no-network]

It is separate from the deterministic pull-request checks: it makes network requests, its outcomes describe services
on the day of the run, and none of them is a failed FAIR requirement. It reads the previous run's state, so a failure
becomes an issue only after ``PERSISTENCE`` consecutive runs and a recovery closes it; an EOSC CZ page item that is
new or changed in the page's main content opens one issue per item (one per page above ``PAGE_ITEM_LIMIT``), and
the first run of a page only records a baseline. Writes ``observations.json`` (every observation, dated, with its
kind), ``issues.json`` (the plan for the trusted issue publisher), ``state.json`` (for the next run) and
``summary.md``. Uses only the Python standard library; it writes no repository file and opens no issue itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_crate  # noqa: E402
import check_content  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "eosc-fair-guide-watch/0.1 (+https://github.com/motyc/eosc-fair-guide)"
FORMAT_VERSION = 1
PERSISTENCE = 2  # consecutive failing runs before an issue opens
MAX_URLS = 600
WORKERS = 8
TIMEOUT = 20
MAX_PAGE_BYTES = 4 * 1024 * 1024
PAGE_ITEM_LIMIT = 10

# A fetch returns (HTTP status or None, body bytes or b"", error text).
Fetch = Callable[[str, bool], tuple[int | None, bytes, str]]


def fetch(url: str, body: bool) -> tuple[int | None, bytes, str]:
    """One bounded anonymous request: HEAD for a link (GET when HEAD is refused), GET for a page body."""
    for method in ("GET",) if body else ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.status, response.read(MAX_PAGE_BYTES) if body else b"", ""
        except urllib.error.HTTPError as error:
            if method == "HEAD" and error.code in (403, 405, 501):
                continue
            return error.code, b"", f"HTTP {error.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            return None, b"", str(getattr(error, "reason", error))
    return None, b"", "no response"


def classify(status: int | None) -> str:
    """A link's outcome: ok, broken (the address is gone or refused) or unavailable (the service did not answer)."""
    if status is not None and 200 <= status < 400:
        return "ok"
    if status in (404, 410) or (status is not None and 400 <= status < 500 and status != 429):
        return "broken"
    return "unavailable"


def content_links(content: dict[str, Any]) -> dict[str, list[str]]:
    """Every external address the guide links, with where it is used, up to MAX_URLS addresses."""
    found: dict[str, list[str]] = {}
    for name, data in content.items():
        if name in ("ui", "icons", "identifiers"):
            continue
        for path, key, value in check_content.walk(data, name):
            if key in ("url", "href") and isinstance(value, str) and value.startswith("https://"):
                found.setdefault(value, []).append(f"{path}.{key}")
    return dict(sorted(found.items())[:MAX_URLS])


class MainItems(HTMLParser):
    """Linked items and anchored sections in a page's <main>, leaving out its navigation, header and footer."""

    SKIPPED = {"nav", "header", "footer", "script", "style", "noscript"}

    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.depth = 0
        self.skipped = 0
        self.items: dict[str, str] = {}
        self._link: str | None = None
        self._anchor: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "main":
            self.depth += 1
        if not self.depth:
            return
        if tag in self.SKIPPED:
            self.skipped += 1
        if self.skipped:
            return
        href = values.get("href") or ""
        if tag == "a" and href and urlparse(urljoin(self.base, href)).scheme in ("http", "https"):
            self._link, self._text = urljoin(self.base, href), []
        elif values.get("id") and tag in ("h1", "h2", "h3", "h4", "section", "article", "div", "li"):
            self._anchor, self._text = "#" + values["id"], []

    def handle_endtag(self, tag: str) -> None:
        if not self.depth:
            return
        if tag in self.SKIPPED and self.skipped:
            self.skipped -= 1
            return
        if self.skipped:
            return
        if tag == "a" and self._link:
            self.items[self._link] = " ".join("".join(self._text).split())[:300]
            self._link = None
        elif self._anchor and tag in ("h1", "h2", "h3", "h4", "section", "article", "div", "li"):
            self.items.setdefault(self._anchor, " ".join("".join(self._text).split())[:300])
            self._anchor = None
        if tag == "main":
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth and not self.skipped and (self._link or self._anchor):
            self._text.append(data)


def page_items(url: str, body: bytes) -> dict[str, str]:
    parser = MainItems(url)
    parser.feed(body.decode("utf-8", errors="replace"))
    return parser.items


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def observe(
    content: dict[str, Any], state: dict[str, Any], fetcher: Fetch, champion: dict[str, Any] | None, today: date
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Today's observations and the next state; the state carries failure streaks and page items."""
    observations: list[dict[str, Any]] = []
    streaks: dict[str, int] = dict(state.get("streaks", {}))
    pages: dict[str, dict[str, str]] = {key: dict(value) for key, value in state.get("pages", {}).items()}

    def record(key: str, kind: str, status: str, **details: Any) -> None:
        failing = status not in ("ok", "available", "unchanged", "baseline", "changed", "matches")
        streaks[key] = streaks.get(key, 0) + 1 if failing else 0
        observations.append({"key": key, "kind": kind, "status": status, "streak": streaks[key], **details})

    links = content_links(content)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        answers = dict(zip(links, pool.map(lambda url: fetcher(url, False), links), strict=True))
    for url, used in links.items():
        status, _, error = answers[url]
        record(f"link:{url}", "link", classify(status), url=url, http=status, error=error, used=used[:5])
    for connector in content["live"].get("connector", []):
        status, _, error = fetcher(connector["origin"] + "/", False)
        outcome = "available" if status is not None and status < 500 and status != 429 else "unavailable"
        record(f"connector:{connector['id']}", "connector", outcome, url=connector["origin"], http=status, error=error)
    for page in content["live"].get("watch", []):
        status, body, error = fetcher(page["url"], True)
        key = f"watch:{page['id']}"
        if status is None or not 200 <= status < 300:
            record(key, "watch", "unavailable", url=page["url"], http=status, error=error)
            continue
        texts = page_items(page["url"], body)
        items = {href: digest(text) for href, text in texts.items()}
        before = pages.get(page["id"])
        if before is None:
            record(key, "watch", "baseline", url=page["url"], items=len(items))
        else:
            added = sorted(set(items) - set(before))
            changed = sorted(href for href in set(items) & set(before) if items[href] != before[href])
            record(
                key,
                "watch",
                "changed" if added or changed else "unchanged",
                url=page["url"],
                added=[{"item": href, "text": texts[href]} for href in added],
                updated=[{"item": href, "text": texts[href]} for href in changed],
            )
        pages[page["id"]] = items
    stale_after = int(content["guide"]["guide"].get("freshnessDays", 180))
    for name, data in content.items():
        for path, key, value in check_content.walk(data, name):
            if key == "asOf" and isinstance(value, date) and (today - value).days > stale_after:
                record(
                    f"stale:{path}.{key}",
                    "stale-status",
                    "stale",
                    item=f"{path}.{key}",
                    asOf=value.isoformat(),
                    days=(today - value).days,
                )
    if champion:
        core = {test["id"]: test for test in content["live"].get("champion", {}).get("test", [])}
        for summary in champion.get("summary", []):
            test = core.get(summary["id"])
            details = {
                "test": summary["id"],
                "measured": summary["health"],
                "attempted": summary["attempted"],
                "definitive": summary["definitive"],
                "indeterminate": summary["indeterminate"],
                "measuredAt": champion.get("generatedAt"),
            }
            if test is not None:
                same = test.get("health") == summary["health"]
                record(
                    f"champion:{summary['id']}",
                    "champion-core",
                    "matches" if same else "differs",
                    recorded=test.get("health"),
                    recordedAsOf=str(test.get("asOf", "")),
                    **details,
                )
            elif summary["health"] == "available":
                record(f"champion-candidate:{summary['id']}", "champion-candidate", "candidate", **details)
    return observations, {"format_version": FORMAT_VERSION, "streaks": streaks, "pages": pages}


def escape(value: Any) -> str:
    """External text as inert Markdown prose: no HTML, mentions, links or table breaks."""
    text = " ".join(str(value).split())[:300]
    for char, replacement in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ("@", "@\u200b"), ("|", "\\|")):
        text = text.replace(char, replacement)
    for char in "`*_[]()#!":
        text = text.replace(char, "\\" + char)
    return text


def code(value: Any) -> str:
    """External text for a code span, where Markdown and mentions are inert: one line, no backticks."""
    return " ".join(str(value).split())[:300].replace("`", "'")


def plain(value: Any, limit: int = 100) -> str:
    """External text for an issue title, which GitHub shows as plain text: one line, no mention."""
    return " ".join(str(value).split())[:limit].replace("@", "@\u200b")


def plan(observations: list[dict[str, Any]], run_url: str | None, today: date) -> list[dict[str, Any]]:
    """Issue actions keyed for deduplication: open or update after PERSISTENCE failing runs, close on recovery."""
    actions: list[dict[str, Any]] = []
    source = f" ([run]({run_url}))" if run_url else ""
    for item in observations:
        key, kind, status = item["key"], item["kind"], item["status"]
        if kind in ("link", "connector") and status in ("ok", "available"):
            actions.append({"key": key, "action": "close", "comment": f"Recovered on {today.isoformat()}{source}."})
        elif kind == "link" and item["streak"] >= PERSISTENCE:
            what = "is broken" if status == "broken" else "did not answer"
            actions.append(
                {
                    "key": key,
                    "action": "open",
                    "title": f"Link {what}: {plain(item['url'], 120)}",
                    "body": f"`{code(item['url'])}` {what} in {item['streak']} consecutive runs "
                    f"(HTTP {item['http'] or 'none'}; {escape(item['error'])}).\n\nUsed at: "
                    + ", ".join(f"`{code(place)}`" for place in item["used"])
                    + f"\n\nLast checked {today}{source}.",
                }
            )
        elif kind == "connector" and item["streak"] >= PERSISTENCE:
            actions.append(
                {
                    "key": key,
                    "action": "open",
                    "title": f"Service unavailable: {plain(key.split(':', 1)[1])}",
                    "body": f"`{code(item['url'])}` did not answer in {item['streak']} consecutive runs. "
                    "The guide keeps working; lookups through this service show no result, never a failed "
                    f"requirement.\n\nLast checked {today}{source}.",
                }
            )
        elif kind == "watch" and status == "changed":
            changes = [("New", entry) for entry in item["added"]] + [("Updated", entry) for entry in item["updated"]]
            if len(changes) > PAGE_ITEM_LIMIT:
                listed = "\n".join(
                    f"- {label}: {escape(entry['text'])} (`{code(entry['item'])}`)"
                    for label, entry in changes[:PAGE_ITEM_LIMIT]
                )
                actions.append(
                    {
                        "key": f"{key}:{today.isoformat()}",
                        "action": "open",
                        "title": f"EOSC CZ page changed: {plain(key.split(':', 1)[1])} ({len(changes)} items)",
                        "body": f"{len(changes)} items changed in the main content of `{code(item['url'])}` "
                        f"on {today}; the first {PAGE_ITEM_LIMIT}:\n\n{listed}\n\nReview what the guide cites{source}.",
                    }
                )
            else:
                for label, entry in changes:
                    actions.append(
                        {
                            "key": f"{key}:{entry['item']}:{digest(entry['text'])}",
                            "action": "open",
                            "title": f"EOSC CZ {label.lower()} item: {plain(entry['text'] or entry['item'])}",
                            "body": f"{label} item in the main content of `{code(item['url'])}` on {today}: "
                            f"{escape(entry['text'])} (`{code(entry['item'])}`). Check whether the guide's "
                            f"advice or sources should follow{source}.",
                        }
                    )
        elif kind == "champion-core" and status == "differs" and item["streak"] >= PERSISTENCE:
            actions.append(
                {
                    "key": key,
                    "action": "open",
                    "title": f"FAIR Champion test health changed: {plain(item['test'])}",
                    "body": f"Recorded `{code(item['recorded'])}` (as of {escape(item['recordedAsOf'])}); measured "
                    f"`{code(item['measured'])}` in {item['streak']} consecutive remeasurements "
                    f"({item['definitive']} definitive and {item['indeterminate']} indeterminate verdicts of "
                    f"{item['attempted']} calls, {escape(item['measuredAt'])}). An indeterminate verdict is a "
                    "result, not a transport failure. Update the dated health in `content/live.toml` with "
                    f"fresh provenance if the change holds{source}.",
                }
            )
        elif kind == "champion-core" and status == "matches":
            actions.append(
                {"key": key, "action": "close", "comment": f"Measured health matches the record on {today}{source}."}
            )
        elif kind == "champion-candidate":
            actions.append(
                {
                    "key": key,
                    "action": "open",
                    "title": f"FAIR Champion candidate available: {plain(item['test'])}",
                    "body": f"The reviewed candidate `{code(item['test'])}` returned verdicts for every reference "
                    f"record ({item['definitive']} definitive, {item['indeterminate']} indeterminate). This "
                    "is a proposal for the documented selection review (docs/champion/selection.md), not a "
                    f"selection{source}.",
                }
            )
    stale = [item for item in observations if item["kind"] == "stale-status"]
    if stale:
        listed = "\n".join(f"- `{code(item['item'])}`: {item['asOf']} ({item['days']} days)" for item in stale[:40])
        actions.append(
            {
                "key": "stale-statuses",
                "action": "open",
                "title": f"{len(stale)} dated statuses need review",
                "body": f"These recorded statuses are older than the guide's freshness period:\n\n{listed}{source}",
            }
        )
    else:
        actions.append({"key": "stale-statuses", "action": "close", "comment": f"No stale dated status on {today}."})
    return actions


def summary(observations: list[dict[str, Any]], actions: list[dict[str, Any]], today: date) -> str:
    counts: dict[str, dict[str, int]] = {}
    for item in observations:
        counts.setdefault(item["kind"], {}).setdefault(item["status"], 0)
        counts[item["kind"]][item["status"]] += 1
    lines = [
        "## Live watch",
        "",
        f"Run on {today}. Live outcomes describe services today; none is a failed FAIR requirement.",
        "",
        "| Kind | Outcomes |",
        "| --- | --- |",
    ]
    for kind, statuses in sorted(counts.items()):
        lines.append(
            f"| {kind} | " + ", ".join(f"{status} {count}" for status, count in sorted(statuses.items())) + " |"
        )
    opened = sum(action["action"] == "open" for action in actions)
    lines += ["", f"Planned issue actions: {opened} to open or update; persistence threshold {PERSISTENCE} runs."]
    return "\n".join(lines) + "\n"


def offline(url: str, body: bool) -> tuple[int | None, bytes, str]:
    return None, b"", "network disabled"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--state", type=Path, required=True, help="previous run's state.json (missing: first run)")
    parser.add_argument("--output", type=Path, required=True, help="directory for observations, issues and state")
    parser.add_argument("--champion", type=Path, help="output of scripts/probe_champion.mjs for this run")
    parser.add_argument("--no-network", action="store_true", help="record every request as unanswered (tests)")
    args = parser.parse_args(argv)
    content = build_crate.load_content(ROOT / "content")
    state = json.loads(args.state.read_text(encoding="utf-8")) if args.state.is_file() else {}
    if state and state.get("format_version") != FORMAT_VERSION:
        state = {}
    champion = (
        json.loads(args.champion.read_text(encoding="utf-8")) if args.champion and args.champion.is_file() else None
    )
    today = datetime.now(UTC).date()
    observations, next_state = observe(content, state, offline if args.no_network else fetch, champion, today)
    run_url = (
        f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
        if os.environ.get("GITHUB_REPOSITORY") and os.environ.get("GITHUB_RUN_ID")
        else None
    )
    actions = plan(observations, run_url, today)
    args.output.mkdir(parents=True, exist_ok=True)
    meta = {
        "format_version": FORMAT_VERSION,
        "observed_at": datetime.now(UTC).isoformat(),
        "revision": os.environ.get("GITHUB_SHA"),
        "run_url": run_url,
        "scope": "Live services, links and watched pages on the day of the run; not a FAIR verdict.",
    }
    (args.output / "observations.json").write_text(
        json.dumps(meta | {"observations": observations}, indent=2, default=str) + "\n", encoding="utf-8"
    )
    (args.output / "issues.json").write_text(
        json.dumps({"format_version": FORMAT_VERSION, "actions": actions}, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "state.json").write_text(json.dumps(next_state, indent=2) + "\n", encoding="utf-8")
    (args.output / "summary.md").write_text(summary(observations, actions, today), encoding="utf-8")
    print(summary(observations, actions, today))
    return 0


if __name__ == "__main__":
    sys.exit(main())
