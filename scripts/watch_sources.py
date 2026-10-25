#!/usr/bin/env python3
"""Scheduled live monitoring: links, connector availability, the EOSC CZ pages the guide depends on, stale dated
statuses and FAIR Champion remeasurement, shown in one maintenance digest rebuilt from current state.

    python scripts/watch_sources.py observe --state STATE.json --output DIR [--champion PROBE.json] [--no-network]
    python scripts/watch_sources.py render --watch DIR --tasks TASKS.json [--audit SECTION.md] --output DIR
    python scripts/watch_sources.py check-config

It is separate from the deterministic pull-request checks: it makes network requests, its outcomes describe services
on the day of the run, and none of them is a failed FAIR requirement. ``observe`` reads the previous run's state
(version 1 is migrated; missing or malformed state is a visible reset that claims no streak or recovery), attempts the
least recently attempted links under a global budget and a per-host cap, classifies each answer and writes
``observations.json``, ``plan.json`` (the digest's findings and coverage), ``state.json`` and ``summary.md``.
``render`` joins that plan with the maintainers' tasks and the audit's "Project and settings" section into
``body.md``, ``comment.md`` (empty unless a finding appeared, changed, recovered or expired) and the ``state.json``
the next run reads. Reviewed limitations live in ``.github/health-watch.toml``; ``check-config`` validates them
offline. Uses only the Python standard library; it writes no repository file and opens no issue itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import tomllib
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_crate  # noqa: E402
import check_content  # noqa: E402
from handoff import handoff  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LIMITATIONS = ".github/health-watch.toml"
USER_AGENT = "eosc-fair-guide-watch/0.2 (+https://github.com/dsw-nrp/eosc-fair-guide)"
FORMAT_VERSION = 2
PERSISTENCE = 2  # consecutive failing observations before a finding is shown
BUDGET = 600  # link requests per run
PER_HOST = 120  # link requests per host per run; 199 of 673 links share one host, which two runs still cover
RETRY_AFTER_LIMIT = 30  # seconds one rate-limited host may be waited for, once
UNRESPONSIVE = 3  # consecutive unanswered requests that stop a host for the run
WORKERS = 8
TIMEOUT = 20
MAX_PAGE_BYTES = 4 * 1024 * 1024
SOURCE_DAYS = 28  # how long a changed EOSC CZ page item stays listed for review unless a task tracks it
SECTION_LIMIT = 25
BODY_LIMIT = 60000  # GitHub's issue body limit is 65,536 characters
FAILING = ("broken", "denied", "rate-limited", "unavailable")
GOOD = ("ok", "available", "matches")
DIGEST_MARKER = "<!-- fair-guide-digest -->"
SECTIONS = {
    "triage": "Needs triage",
    "tracked": "Tracked",
    "limitation": "Known limitations",
    "source": "Source updates to review",
    "candidate": "Candidates to review",
    "stale": "Stale statuses",
}
PAGINATION_WORDS = {
    "další",
    "předchozí",
    "následující",
    "next",
    "previous",
    "prev",
    "older",
    "newer",
    "more",
    "»",
    "«",
    "›",
    "‹",
    "…",
}
PAGINATION_KEYS = {"page", "p", "strana", "offset", "start", "pg"}


class Answer(tuple):
    """One request's outcome: HTTP status or None, body bytes, error text, the methods tried and any Retry-After."""

    def __new__(
        cls, status: int | None, body: bytes = b"", error: str = "", method: str = "GET", retry: int | None = None
    ):
        return super().__new__(cls, (status, body, error, method, retry))

    status = property(lambda self: self[0])
    body = property(lambda self: self[1])
    error = property(lambda self: self[2])
    method = property(lambda self: self[3])
    retry = property(lambda self: self[4])


# A fetch takes (url, body wanted) and returns an Answer, or (status, body, error) as before.
Fetch = Callable[[str, bool], tuple]


def answer(result: tuple) -> Answer:
    return result if isinstance(result, Answer) else Answer(*result)


def retry_after(value: str | None) -> int | None:
    return int(value) if value and value.strip().isdigit() else None


def fetch(url: str, body: bool) -> Answer:
    """One bounded anonymous request: HEAD for a link (GET when HEAD is refused), GET for a page body."""
    tried = []
    for method in ("GET",) if body else ("HEAD", "GET"):
        tried.append(method)
        request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return Answer(response.status, response.read(MAX_PAGE_BYTES) if body else b"", "", " then ".join(tried))
        except urllib.error.HTTPError as error:
            if method == "HEAD" and error.code in (403, 405, 501):
                continue
            wait = retry_after(error.headers.get("Retry-After")) if error.headers else None
            return Answer(error.code, b"", f"HTTP {error.code}", " then ".join(tried), wait)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            return Answer(None, b"", str(getattr(error, "reason", error)), " then ".join(tried))
    return Answer(None, b"", "no response", " then ".join(tried))


def classify(status: int | None) -> str:
    """An answer's outcome. Only a missing address is broken; refusals, throttling and silence say nothing about the
    page itself, and none of them is a FAIR verdict."""
    if status is not None and 200 <= status < 400:
        return "ok"
    if status in (404, 410):
        return "broken"
    if status in (401, 403, 451):
        return "denied"
    if status == 429:
        return "rate-limited"
    return "unavailable"


def content_links(content: dict[str, Any]) -> tuple[dict[str, list[str]], list[str]]:
    """Every external address the guide links, with where it is used, and the url or href values that are not a
    checkable HTTPS address."""
    found: dict[str, list[str]] = {}
    invalid: list[str] = []
    for name, data in content.items():
        if name in ("ui", "icons", "identifiers"):
            continue
        for path, key, value in check_content.walk(data, name):
            if key not in ("url", "href") or not isinstance(value, str):
                continue
            parsed = urlparse(value)
            if parsed.scheme == "https" and parsed.hostname:
                found.setdefault(value, []).append(f"{path}.{key}")
            elif parsed.scheme in ("http", "https"):
                invalid.append(f"{path}.{key}")
    return dict(sorted(found.items())), invalid


def select(
    urls: list[str], targets: dict[str, dict], budget: int | None = None, per_host: int | None = None
) -> list[str]:
    """The links to attempt: never attempted first, then the least recently attempted, at most `per_host` per host and
    `budget` in all (BUDGET and PER_HOST by default), so an unchanged inventory larger than the budget is covered in
    turn."""
    budget = BUDGET if budget is None else budget
    per_host = PER_HOST if per_host is None else per_host
    order = sorted(urls, key=lambda url: (targets.get(f"link:{url}", {}).get("checked") or "", url))
    chosen, hosts = [], Counter()
    for url in order:
        host = urlparse(url).hostname
        if len(chosen) < budget and hosts[host] < per_host:
            chosen.append(url)
            hosts[host] += 1
    return chosen


def attempt(urls: list[str], fetcher: Fetch, sleep: Callable[[float], None] = time.sleep) -> dict[str, Answer]:
    """Answers for `urls`, each host in turn and hosts in parallel. A host that rate-limits is waited for once when it
    asks for at most RETRY_AFTER_LIMIT seconds; a host that throttles again, asks for longer or stops answering is not
    asked further this run, and its remaining links are deferred."""
    hosts: dict[str, list[str]] = {}
    for url in urls:
        hosts.setdefault(urlparse(url).hostname or "", []).append(url)

    def run(queue: list[str]) -> dict[str, Answer]:
        answers, waited, silent = {}, False, 0
        for url in queue:
            result = answer(fetcher(url, False))
            if result.status == 429 and not waited and result.retry is not None and result.retry <= RETRY_AFTER_LIMIT:
                waited = True
                sleep(result.retry)
                result = answer(fetcher(url, False))
            answers[url] = result
            silent = silent + 1 if result.status is None else 0
            if result.status == 429 or silent >= UNRESPONSIVE:
                break
        return answers

    found: dict[str, Answer] = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for answers in pool.map(run, hosts.values()):
            found.update(answers)
    return found


class MainItems(HTMLParser):
    """Linked items and anchored sections in a page's <main>, leaving out its navigation, header, footer and
    pagination: a "next page" link (#101) is navigation, not a new item."""

    SKIPPED = {"nav", "header", "footer", "script", "style", "noscript"}
    PAGER = re.compile(r"pag(?:ination|er|ing)", re.IGNORECASE)

    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.depth = 0
        self.skipping: list[str] = []  # the open skipped elements, innermost last
        self.items: dict[str, str] = {}
        self._link: str | None = None
        self._rel = ""
        self._anchor: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "main":
            self.depth += 1
        if not self.depth:
            return
        pager = self.PAGER.search(values.get("class", "") + " " + values.get("aria-label", ""))
        nested = bool(self.skipping) and tag == self.skipping[-1]  # a same-named element inside a skipped one
        if tag in self.SKIPPED or (pager and tag not in ("a", "main")) or nested:
            self.skipping.append(tag)
        if self.skipping:
            return
        href = values.get("href") or ""
        if tag == "a" and href and urlparse(urljoin(self.base, href)).scheme in ("http", "https"):
            self._link, self._rel, self._text = urljoin(self.base, href), values.get("rel", ""), []
        elif values.get("id") and tag in ("h1", "h2", "h3", "h4", "section", "article", "div", "li"):
            self._anchor, self._text = "#" + values["id"], []

    def handle_endtag(self, tag: str) -> None:
        if not self.depth:
            return
        if self.skipping:
            if tag == self.skipping[-1]:
                self.skipping.pop()
            return
        if tag == "a" and self._link:
            text = " ".join("".join(self._text).split())[:300]
            if not self.paging(self._link, self._rel, text):
                self.items[self._link] = text
            self._link = None
        elif self._anchor and tag in ("h1", "h2", "h3", "h4", "section", "article", "div", "li"):
            self.items.setdefault(self._anchor, " ".join("".join(self._text).split())[:300])
            self._anchor = None
        if tag == "main":
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth and not self.skipping and (self._link or self._anchor):
            self._text.append(data)

    def paging(self, link: str, rel: str, text: str) -> bool:
        """A link to another page of this listing: rel next or prev, the same address with only a page parameter
        changed, or a bare page word or number."""
        if {"next", "prev", "previous"} & set(rel.lower().split()):
            return True
        here, there = urlparse(self.base), urlparse(link)
        if (there.netloc, there.path.rstrip("/")) == (here.netloc, here.path.rstrip("/")):
            changed = set(dict(parse_qsl(there.query))) ^ set(dict(parse_qsl(here.query))) | {
                key for key, value in parse_qsl(there.query) if dict(parse_qsl(here.query)).get(key) != value
            }
            if changed and changed <= PAGINATION_KEYS:
                return True
        word = text.strip().lower()
        return word in PAGINATION_WORDS or (word.isdigit() and len(word) <= 3)  # "2" is a page; "2026" may be a report


def page_items(url: str, body: bytes) -> dict[str, str]:
    parser = MainItems(url)
    parser.feed(body.decode("utf-8", errors="replace"))
    return parser.items


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# --- state ----------------------------------------------------------------------------------------------------------


def load_state(path: Path) -> tuple[dict[str, Any], str]:
    """The previous run's state in the current format, and a reset notice when there is none to continue from."""
    if not path.is_file():
        return (
            empty_state(),
            "No previous watch state was found, so this run restarts every streak and claims no recovery.",
        )
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return (
            empty_state(),
            f"The previous watch state was unreadable ({type(error).__name__}), so this run restarts every streak "
            "and claims no recovery.",
        )
    if isinstance(state, dict) and state.get("format_version") == 1 and isinstance(state.get("streaks"), dict):
        return migrate(state), ""
    if (
        isinstance(state, dict)
        and state.get("format_version") == FORMAT_VERSION
        and all(isinstance(state.get(key), dict) for key in ("targets", "pages", "sources", "reported"))
    ):
        return state, ""
    return (
        empty_state(),
        "The previous watch state had an unknown format, so this run restarts every streak and claims no recovery.",
    )


def empty_state() -> dict[str, Any]:
    return {"format_version": FORMAT_VERSION, "targets": {}, "pages": {}, "sources": {}, "reported": {}}


def migrate(state: dict[str, Any]) -> dict[str, Any]:
    """Version 1 kept failure streaks and page baselines; both continue, with outcomes learned at the next check."""
    kinds = {"link": "link", "connector": "connector", "watch": "watch", "champion": "champion-core"}
    targets = {}
    for key, streak in state["streaks"].items():
        kind = kinds.get(key.split(":", 1)[0])
        if kind and isinstance(streak, int) and streak > 0:
            targets[key] = {"kind": kind, "outcome": None, "streak": streak, "since": None, "checked": None}
    pages = {page: dict(items) for page, items in state.get("pages", {}).items() if isinstance(items, dict)}
    return {"format_version": FORMAT_VERSION, "targets": targets, "pages": pages, "sources": {}, "reported": {}}


def observed(previous: dict[str, Any] | None, outcome: str, today: date, **details: Any) -> dict[str, Any]:
    previous = previous or {}
    failing = outcome in FAILING or outcome == "differs"
    return {
        **details,
        "outcome": outcome,
        "streak": (previous.get("streak", 0) + 1) if failing else 0,
        "since": previous.get("since")
        if previous.get("outcome") == outcome and previous.get("since")
        else today.isoformat(),
        "checked": today.isoformat(),
    }


# --- limitations ------------------------------------------------------------------------------------------------------

LIMITATION_KEYS = {"key", "outcome", "reason", "evidence", "reviewer", "reviewed", "reviewBy"}


def limitation_errors(entries: Any, people: set[str]) -> list[str]:
    """Problems that make a limitation unusable, each naming its entry: a wildcard or unknown target, a missing basis,
    an unknown reviewer, impossible dates or two entries for one target."""
    if not isinstance(entries, list):
        return ["limitation: expected a list of [[limitation]] tables"]
    errors, seen = [], {}
    for index, entry in enumerate(entries):
        where = f"limitation[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: expected a table")
            continue
        where += f" ({entry.get('key', '?')})"
        errors += [f"{where}: unknown key {key!r}" for key in sorted(set(entry) - LIMITATION_KEYS)]
        errors += [f"{where}: missing {key!r}" for key in sorted(LIMITATION_KEYS - set(entry))]
        key = entry.get("key", "")
        if (
            not isinstance(key, str)
            or not re.fullmatch(r"(link|connector|watch):\S+", key)
            or any(c in key for c in "*?")
        ):
            errors.append(f"{where}: key must name one exact link, connector or watched page, without wildcards")
        if entry.get("outcome") not in FAILING:
            errors.append(f"{where}: outcome must be one of {', '.join(FAILING)}")
        for field in ("reason", "evidence"):
            if not isinstance(entry.get(field), str) or len(entry.get(field, "").strip()) < 10:
                errors.append(f"{where}: {field} must state the basis in words")
        if entry.get("reviewer") not in people:
            errors.append(f"{where}: reviewer must be a reviewed person ID from content/guide.toml")
        reviewed, due = entry.get("reviewed"), entry.get("reviewBy")
        if not isinstance(reviewed, date) or not isinstance(due, date) or due <= reviewed:
            errors.append(f"{where}: reviewed and reviewBy must be dates, reviewBy after reviewed")
        if isinstance(key, str) and key in seen:
            errors.append(f"{where}: conflicts with limitation[{seen[key]}] for the same target")
        seen.setdefault(key, index)
    return errors


def load_limitations(root: Path, content: dict[str, Any]) -> tuple[dict[str, dict], list[str]]:
    path = root / LIMITATIONS
    entries = tomllib.loads(path.read_text(encoding="utf-8")).get("limitation", []) if path.is_file() else []
    people = {person["id"] for person in content["guide"].get("person", [])}
    errors = limitation_errors(entries, people)
    return ({} if errors else {entry["key"]: entry for entry in entries}), errors


# --- text -------------------------------------------------------------------------------------------------------------


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


OUTCOME_TEXT = {
    "broken": "is gone",
    "denied": "refused access",
    "rate-limited": "rate-limited the watch",
    "unavailable": "did not answer",
}


# --- observe ----------------------------------------------------------------------------------------------------------


def observe(
    content: dict[str, Any],
    state: dict[str, Any],
    fetcher: Fetch,
    champion: dict[str, Any] | None,
    today: date,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Today's observations, the next state and the coverage counts."""
    targets: dict[str, dict] = {key: dict(value) for key, value in state["targets"].items()}
    pages = {key: dict(value) for key, value in state["pages"].items()}
    sources = {key: dict(value) for key, value in state["sources"].items()}
    observations: list[dict[str, Any]] = []

    def record(key: str, kind: str, outcome: str, **details: Any) -> None:
        targets[key] = observed(targets.get(key), outcome, today, kind=kind, **details)
        observations.append({"key": key, "kind": kind, "status": outcome, "streak": targets[key]["streak"], **details})

    links, invalid = content_links(content)
    chosen = select(list(links), targets)
    answers = attempt(chosen, fetcher, sleep)
    for url, used in links.items():
        key = f"link:{url}"
        if url in answers:
            result = answers[url]
            evidence = f"{result.method} {result.status if result.status is not None else 'no answer'}"
            evidence += f": {result.error}" if result.error and result.status is None else ""
            record(
                key,
                "link",
                classify(result.status),
                url=url,
                http=result.status,
                method=result.method,
                evidence=evidence,
                used=used[:5],
            )
        else:
            # Deferred: the dated observation stays as it was, without a new failure or a recovery.
            targets.setdefault(key, {"kind": "link", "outcome": None, "streak": 0, "since": None, "checked": None})
            targets[key]["url"], targets[key]["used"] = url, used[:5]
            observations.append({"key": key, "kind": "link", "status": "deferred", "checked": targets[key]["checked"]})
    for key in [key for key, value in targets.items() if value.get("kind") == "link" and key[5:] not in links]:
        del targets[key]  # no longer linked
    for connector in content["live"].get("connector", []):
        result = answer(fetcher(connector["origin"] + "/", False))
        # A service that answers, even 404 at its root, is available; only throttling and silence are not.
        answered = result.status is not None and result.status < 500 and result.status != 429
        outcome = "available" if answered else classify(result.status)
        record(
            f"connector:{connector['id']}",
            "connector",
            outcome,
            url=connector["origin"],
            http=result.status,
            method=result.method,
            evidence=f"{result.method} {result.status if result.status is not None else 'no answer'}",
        )
    connectors = {f"connector:{item['id']}" for item in content["live"].get("connector", [])}
    for key in [key for key, value in targets.items() if value.get("kind") == "connector" and key not in connectors]:
        del targets[key]
    for page in content["live"].get("watch", []):
        result = answer(fetcher(page["url"], True))
        key = f"watch:{page['id']}"
        if result.status is None or not 200 <= result.status < 300:
            outcome = classify(result.status)
            record(
                key,
                "watch",
                "unavailable" if outcome == "ok" else outcome,
                url=page["url"],
                http=result.status,
                method=result.method,
                evidence=f"{result.method} {result.status or 'no answer'}",
            )
            continue
        texts = page_items(page["url"], result.body)
        items = {href: digest(text) for href, text in texts.items()}
        before = pages.get(page["id"])
        if before is None:
            record(key, "watch", "baseline", url=page["url"], items=len(items))
        else:
            for href in sorted(set(items) - set(before)) + sorted(
                h for h in set(items) & set(before) if items[h] != before[h]
            ):
                label = "New" if href not in before else "Updated"
                sources[f"page:{page['id']}:{href}"] = {
                    "page": page["id"],
                    "url": page["url"],
                    "item": href,
                    "text": texts[href],
                    "label": label,
                    "first": today.isoformat(),
                }
            record(key, "watch", "ok", url=page["url"], items=len(items))
        pages[page["id"]] = items
    for key, item in list(sources.items()):
        if item["first"] < (today - timedelta(days=365)).isoformat():
            del sources[key]  # long past review, tracked or not
        elif item["first"] < (today - timedelta(days=SOURCE_DAYS)).isoformat():
            item["aged"] = True
    if champion:
        core = {test["id"]: test for test in content["live"].get("champion", {}).get("test", [])}
        measured = set()
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
                measured.add(f"champion-candidate:{summary['id']}")
                record(f"champion-candidate:{summary['id']}", "champion-candidate", "candidate", **details)
        for key in [k for k, v in targets.items() if v.get("kind") == "champion-candidate" and k not in measured]:
            del targets[key]  # no longer available, or adopted into the core selection
    coverage = {
        "eligible": len(links),
        "attempted": len(answers),
        "deferred": len(links) - len(answers),
        "invalid": len(invalid),
        "invalidAt": invalid[:SECTION_LIMIT],
    }
    next_state = {
        **empty_state(),
        "targets": targets,
        "pages": pages,
        "sources": sources,
        "reported": state["reported"],
    }
    return observations, next_state, coverage


def findings(content: dict[str, Any], state: dict[str, Any], limitations: dict[str, dict], today: date) -> list[dict]:
    """What the digest shows, before tasks: persistent failures (in triage or as a known limitation), page items to
    review, Champion candidates and stale statuses. Every finding has a stable key and a fingerprint of what matters."""
    found = []
    for key, target in sorted(state["targets"].items()):
        kind, outcome = target.get("kind"), target.get("outcome")
        failing = outcome in FAILING or outcome == "differs"
        if failing and target.get("streak", 0) >= PERSISTENCE:
            stale = target.get("checked") != today.isoformat()
            when = f"since {target.get('since')}" + (
                f"; not rechecked this run, last checked {target.get('checked')}" if stale else ""
            )
            if kind in ("link", "connector", "watch"):
                what = {"link": "Link", "connector": "Service", "watch": "Watched page"}[kind]
                line = (
                    f"{what} `{code(target.get('url', key))}` {OUTCOME_TEXT.get(outcome, outcome)} "
                    f"({code(target.get('evidence', ''))}) in {target['streak']} checks, {when}"
                )
                if kind == "link" and target.get("used"):
                    line += "; used at " + ", ".join(f"`{code(place)}`" for place in target["used"][:3])
                if kind == "connector":
                    line += ". The Guide keeps working; its lookups show no result, never a failed requirement"
            else:  # a Champion core test whose measured health differs from the record
                line = (
                    f"FAIR Champion test `{code(target.get('test'))}` measured `{code(target.get('measured'))}`, "
                    f"recorded `{code(target.get('recorded'))}` (as of {escape(target.get('recordedAsOf'))}) in "
                    f"{target['streak']} remeasurements; {target.get('definitive')} definitive and "
                    f"{target.get('indeterminate')} indeterminate verdicts of {target.get('attempted')} calls. An "
                    "indeterminate verdict is a result, not a transport failure"
                )
            entry = {"key": key, "kind": kind, "outcome": outcome, "line": line, "section": "triage"}
            limitation = limitations.get(key)
            if limitation and limitation["outcome"] == outcome and today <= limitation["reviewBy"]:
                entry["section"] = "limitation"
                entry["line"] += (
                    f". Reviewed by {limitation['reviewer']} on {limitation['reviewed']}: "
                    f"{escape(limitation['reason'])}; review by {limitation['reviewBy']}"
                )
            elif limitation:
                why = (
                    f"its review-by date {limitation['reviewBy']} passed"
                    if today > limitation["reviewBy"]
                    else (f"the reviewed limitation expects {limitation['outcome']}")
                )
                entry["line"] += f". Back in triage: {why}"
                entry["expired"] = today > limitation["reviewBy"]
            elif kind == "link" and outcome in ("denied", "rate-limited"):
                entry["suggestion"] = suggestion(key, outcome, target, today)
            found.append(entry)
        elif kind == "champion-candidate":
            line = (
                f"FAIR Champion candidate `{code(target.get('test'))}` returned verdicts for every reference record "
                f"({target.get('definitive')} definitive, {target.get('indeterminate')} indeterminate; measured "
                f"{escape(target.get('measuredAt'))}). A proposal for the documented selection review "
                "(docs/champion/selection.md), not a selection"
            )
            found.append({"key": key, "kind": kind, "outcome": "candidate", "line": line, "section": "candidate"})
    for key, item in sorted(state["sources"].items()):
        line = (
            f"{item['label']} item on `{code(item['url'])}` since {item['first']}: "
            f"{escape(item['text'] or item['item'])} (`{code(item['item'])}`). Check whether the Guide's advice or "
            "sources should follow"
        )
        found.append(
            {
                "key": key,
                "kind": "source",
                "outcome": digest(item["text"]),
                "line": line,
                "section": "source",
                "aged": bool(item.get("aged")),
            }
        )
    stale_after = int(content["guide"]["guide"].get("freshnessDays", 180))
    for name, data in content.items():
        for path, key, value in check_content.walk(data, name):
            if key == "asOf" and isinstance(value, date) and (today - value).days > stale_after:
                line = f"`{code(f'{path}.{key}')}` is dated {value.isoformat()} ({(today - value).days} days ago)"
                found.append(
                    {
                        "key": f"stale:{path}.{key}",
                        "kind": "stale-status",
                        "outcome": value.isoformat(),
                        "line": line,
                        "section": "stale",
                    }
                )
    linked = {key for key, value in state["targets"].items() if value.get("kind") in ("link", "connector", "watch")}
    for key in sorted(limitations):
        if key not in linked:
            line = (
                f"The reviewed limitation for `{code(key)}` names a target the Guide no longer checks; "
                f"remove it from `{LIMITATIONS}`"
            )
            found.append(
                {
                    "key": f"limitation:{key}",
                    "kind": "limitation",
                    "outcome": "orphaned",
                    "line": line,
                    "section": "triage",
                }
            )
    return found


def suggestion(key: str, outcome: str, target: dict[str, Any], today: date) -> str:
    """A ready-to-paste limitation for a new denial or rate limit; the maintainer completes reason and reviewer."""
    return "\n".join(
        [
            "[[limitation]]",
            f"key = {json.dumps(key)}",
            f'outcome = "{outcome}"',
            'reason = ""  # why this is acceptable, in words',
            "evidence = "
            + json.dumps(f"{target.get('evidence', '')} from GitHub-hosted runners since {target.get('since')}"),
            'reviewer = ""  # your person ID in content/guide.toml',
            f"reviewed = {today.isoformat()}",
            f"reviewBy = {(today + timedelta(days=180)).isoformat()}",
        ]
    )


def summary(observations: list[dict[str, Any]], coverage: dict[str, Any], today: date, notice: str) -> str:
    counts: dict[str, dict[str, int]] = {}
    for item in observations:
        counts.setdefault(item["kind"], {}).setdefault(item["status"], 0)
        counts[item["kind"]][item["status"]] += 1
    lines = [
        "## Live watch",
        "",
        f"Run on {today}. Live outcomes describe services today; none is a failed FAIR requirement.",
    ]
    if notice:
        lines += ["", f"**State reset:** {notice}"]
    lines += ["", "| Kind | Outcomes |", "| --- | --- |"]
    for kind, statuses in sorted(counts.items()):
        lines.append(
            f"| {kind} | " + ", ".join(f"{status} {count}" for status, count in sorted(statuses.items())) + " |"
        )
    lines += [
        "",
        "Links: {eligible} eligible, {attempted} attempted, {deferred} deferred, {invalid} invalid.".format(**coverage),
        "",
        *handoff(
            "the publish job rebuilds the maintenance digest from these observations.",
            "if it does not run, the observations artifact of this run keeps them, and the next run continues from "
            "the last saved state.",
            "the publish job's summary names the digest issue.",
        ),
    ]
    return "\n".join(lines) + "\n"


# --- render -----------------------------------------------------------------------------------------------------------

FINDING_MARKER = re.compile(r"<!-- fair-guide-finding key=(\S+) outcome=(\S+) -->")


def finding_marker(key: str, outcome: str) -> str:
    return f"<!-- fair-guide-finding key={quote(key, safe='')} outcome={quote(str(outcome), safe='')} -->"


def task_link(repository: str, finding: dict[str, Any]) -> str:
    """A new-issue address prefilled with the Task shape, the finding and its key, labelled for maintenance."""
    body = "\n".join(
        [
            "| Field | Value |",
            "| --- | --- |",
            "| Type | task |",
            "| Affects | The maintenance digest |",
            "| Reported by | Live health and source watch |",
            "",
            "## Problem",
            "",
            finding["line"] + ".",
            "",
            "## Work outline",
            "",
            "Decide what the Guide should do about this observation.",
            "",
            "## Scope",
            "",
            "This finding only.",
            "",
            "## Acceptance criteria",
            "",
            "- [ ] The Guide is corrected, the observation is recorded as a reviewed limitation, or the task is "
            "closed as not planned.",
            "",
            "## Open questions",
            "",
            "None.",
            "",
            finding_marker(finding["key"], finding["outcome"]),
        ]
    )
    title = f"Maintenance: {plain(re.sub(r'[`*_]', '', finding['line']), 90)}"
    query = urlencode({"title": title, "labels": "area:maintenance", "body": body})
    return f"https://github.com/{repository}/issues/new?{query}"


def render(
    plan: dict[str, Any], tasks: list[dict[str, Any]], audit: str, previous: dict[str, str], today: date
) -> tuple[str, str, dict[str, str]]:
    """The digest body, the comment for meaningful change (empty when there is none) and what this run reported.
    A finding with a maintainer's task is tracked while its outcome is the one the task was created for."""
    by_key: dict[str, list[dict]] = {}
    for task in tasks:
        by_key.setdefault(task["key"], []).append(task)
    sections: dict[str, list[str]] = {name: [] for name in SECTIONS}
    reported: dict[str, str] = {}
    expired = set()
    trackable = ("triage", "source", "candidate", "stale")
    for finding in plan["findings"]:
        section = finding["section"]
        linked = sorted(by_key.get(finding["key"], []), key=lambda task: task["number"])
        current = [task for task in linked if task["outcome"] == str(finding["outcome"])]
        if finding.get("aged") and not linked:
            continue  # an unreviewed page item drops off after SOURCE_DAYS; the comment says so once
        line = finding["line"] + "."
        if current and section in trackable:
            section = "tracked"
            task = current[-1]
            line += f" Task #{task['number']}" + (
                f" (closed as {task['reason'] or 'completed'} on {task['closed'][:10]})"
                if task["state"] == "closed"
                else " (open)"
            )
        elif linked:
            line += f" The outcome changed since task #{linked[-1]['number']}."
        if section in trackable:
            line += f" [Track as task]({task_link(plan['repository'], finding)})"
        if finding.get("suggestion") and section == "triage":
            line += "\n\n  ```toml\n" + "\n".join("  " + row for row in finding["suggestion"].splitlines()) + "\n  ```"
        sections[section].append(line)
        reported[finding["key"]] = f"{section}|{finding['outcome']}"
        if finding.get("expired"):
            expired.add(finding["key"])
    body = digest_body(plan, sections, audit, today)
    limit = SECTION_LIMIT
    while len(body) > BODY_LIMIT and limit > 3:
        limit //= 2
        body = digest_body(plan, sections, audit, today, limit)
    comment = change_comment(plan, previous, reported, expired)
    return body, comment, reported


def digest_body(plan: dict, sections: dict[str, list[str]], audit: str, today: date, limit: int = SECTION_LIMIT) -> str:
    run = f"[run]({plan['run_url']})" if plan.get("run_url") else "the latest run"
    lines = [
        DIGEST_MARKER,
        "This body is rebuilt by the Live health and source watch on every run, so edits here are replaced; discuss "
        f"in comments. Last rebuilt on {today} by {run}. Live outcomes describe services on that day; none is a "
        "failed FAIR requirement.",
    ]
    if plan.get("predecessor"):
        lines += ["", f"Continues #{plan['predecessor']}."]
    if plan.get("notice"):
        lines += ["", f"> **State reset:** {plan['notice']}"]
    for name, title in SECTIONS.items():
        entries = sections[name]
        lines += ["", f"## {title} ({len(entries)})", ""]
        lines += [f"- {entry}" for entry in entries[:limit]] or ["None."]
        if len(entries) > limit:
            lines.append(f"- … and {len(entries) - limit} more in the run's observations artifact.")
    coverage = plan["coverage"]
    lines += [
        "",
        "## Coverage",
        "",
        "Links: {eligible} eligible, {attempted} attempted, {deferred} deferred to a later run, {invalid} not a "
        "checkable HTTPS address. A deferred link keeps its last dated observation.".format(**coverage),
    ]
    lines += [f"- Not checkable: `{code(place)}`" for place in coverage.get("invalidAt", [])[:limit]]
    lines += ["", audit.strip() if audit.strip() else "## Project and settings\n\nThe audit did not run this time."]
    triage = len(sections["triage"])
    lines += ["", "## Next", ""]
    lines += handoff(
        f"a maintainer triages the {triage} findings under Needs triage: fix the source, use **Track as task**, or "
        f"add the suggested reviewed limitation to `{LIMITATIONS}`."
        if triage
        else "nothing needs triage; review the source updates and candidates when any are listed.",
        "discuss a finding in a comment here; the run's observations artifact holds every outcome and its evidence.",
        "a run's digest lists nothing under Needs triage.",
    )
    return "\n".join(lines) + "\n"


def change_comment(plan: dict, previous: dict[str, str], reported: dict[str, str], expired: set[str]) -> str:
    """One comment per meaningful change, carrying the run marker that lets a retry find it. A finding counts once,
    when it appears, changes section or outcome, recovers, expires or stops being listed; dates never count."""
    new = sorted(set(reported) - set(previous))
    moved = {key for key in set(reported) & set(previous) if reported[key] != previous[key]}
    changed = sorted(moved - expired)
    gone = sorted(set(previous) - set(reported))
    recovered = [key for key in gone if plan["outcomes"].get(key) in GOOD]
    dropped = [key for key in gone if key not in recovered]
    parts = [
        ("New", new),
        ("Changed", changed),
        ("Expired", sorted(moved & expired)),
        ("Recovered", recovered),
        ("No longer listed", dropped),
    ]
    if not any(keys for _, keys in parts):
        return ""
    lines = [f"<!-- fair-guide-digest-run id={plan.get('run_id') or 'local'} -->"]
    for label, keys in parts:
        if keys:
            lines += ["", f"**{label}** ({len(keys)}): " + ", ".join(f"`{code(key)}`" for key in keys[:SECTION_LIMIT])]
            if len(keys) > SECTION_LIMIT:
                lines[-1] += f", … and {len(keys) - SECTION_LIMIT} more"
    if plan.get("run_url"):
        lines += ["", f"From [this run]({plan['run_url']}); the body above shows the current state."]
    return "\n".join(lines) + "\n"


# --- command line -----------------------------------------------------------------------------------------------------


def offline(url: str, body: bool) -> Answer:
    return Answer(None, b"", "network disabled")


def run_context() -> tuple[str | None, str | None, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", "dsw-nrp/eosc-fair-guide")
    run_id = os.environ.get("GITHUB_RUN_ID")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    return (
        (f"{server}/{repository}/actions/runs/{run_id}" if run_id and os.environ.get("GITHUB_REPOSITORY") else None),
        run_id,
        repository,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    observing = commands.add_parser("observe")
    observing.add_argument("--state", type=Path, required=True, help="previous run's state.json (missing: a reset)")
    observing.add_argument("--output", type=Path, required=True, help="directory for observations, plan and state")
    observing.add_argument("--champion", type=Path, help="output of scripts/probe_champion.mjs for this run")
    observing.add_argument("--no-network", action="store_true", help="record every request as unanswered (tests)")
    rendering = commands.add_parser("render")
    rendering.add_argument("--watch", type=Path, required=True, help="the observe output directory")
    rendering.add_argument("--tasks", type=Path, required=True, help="maintainers' keyed tasks, from the publisher")
    rendering.add_argument("--audit", type=Path, help="the audit's Project and settings section")
    rendering.add_argument("--predecessor", type=int, help="the closed digest a new one continues")
    rendering.add_argument("--output", type=Path, required=True)
    commands.add_parser("check-config")
    args = parser.parse_args(argv)
    content = build_crate.load_content(ROOT / "content")
    limitations, errors = load_limitations(ROOT, content)
    if args.command == "check-config":
        for error in errors:
            print(f"{LIMITATIONS}: {error}", file=sys.stderr)
        print(
            f"watch_sources: {LIMITATIONS} "
            + ("has errors" if errors else f"is valid ({len(limitations)} limitations)")
        )
        return 1 if errors else 0
    today = datetime.now(UTC).date()
    run_url, run_id, repository = run_context()
    if args.command == "observe":
        state, notice = load_state(args.state)
        champion = (
            json.loads(args.champion.read_text(encoding="utf-8")) if args.champion and args.champion.is_file() else None
        )
        observations, next_state, coverage = observe(
            content, state, offline if args.no_network else fetch, champion, today
        )
        found = findings(content, next_state, limitations, today)
        if errors:
            notice = (
                (notice + " " if notice else "")
                + f"{LIMITATIONS} is invalid, so no limitation applies: "
                + "; ".join(errors[:3])
            )
        outcomes = {key: value.get("outcome") for key, value in next_state["targets"].items()}
        plan = {
            "format_version": FORMAT_VERSION,
            "run_url": run_url,
            "run_id": run_id,
            "repository": repository,
            "notice": notice,
            "coverage": coverage,
            "findings": found,
            "outcomes": outcomes,
        }
        args.output.mkdir(parents=True, exist_ok=True)
        meta = {
            "format_version": FORMAT_VERSION,
            "observed_at": datetime.now(UTC).isoformat(),
            "revision": os.environ.get("GITHUB_SHA"),
            "run_url": run_url,
            "scope": "Live services, links and watched pages on the day of the run; not a FAIR verdict.",
        }
        text = summary(observations, coverage, today, notice)
        for name, data in (
            ("observations.json", meta | {"observations": observations}),
            ("plan.json", plan),
            ("state.json", next_state),
        ):
            (args.output / name).write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
        (args.output / "summary.md").write_text(text, encoding="utf-8")
        print(text)
        return 0
    plan = json.loads((args.watch / "plan.json").read_text(encoding="utf-8"))
    state = json.loads((args.watch / "state.json").read_text(encoding="utf-8"))
    plan["predecessor"] = args.predecessor
    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))
    audit = args.audit.read_text(encoding="utf-8") if args.audit and args.audit.is_file() else ""
    body, comment, reported = render(plan, tasks, audit, state.get("reported", {}), today)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "body.md").write_text(body, encoding="utf-8")
    (args.output / "comment.md").write_text(comment, encoding="utf-8")
    (args.output / "state.json").write_text(
        json.dumps({**state, "reported": reported}, indent=2) + "\n", encoding="utf-8"
    )
    print(f"watch_sources: digest body {len(body)} characters; comment {'planned' if comment else 'not needed'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
