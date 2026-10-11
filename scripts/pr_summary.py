#!/usr/bin/env python3
"""Describe changed authored content in both languages for a PR review artifact; never publish it.

    python scripts/pr_summary.py --base BASE_SHA --head HEAD_SHA --output .cache/pr-review/summary.json

Only TOML content from the base revision is read, using the current parser. No code from that revision
is checked out or executed. The report is data; the trusted comment workflow bounds and escapes it.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Any

import build_crate
import check_content

ROOT = Path(__file__).resolve().parent.parent


def revision(value: str) -> str:
    if value != "HEAD" and not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", value):
        raise ValueError("Use HEAD or a complete commit SHA")
    return value


def label(entry: dict[str, Any]) -> dict[str, str]:
    for key in ("statement", "name", "title", "label", "text"):
        value = entry.get(key)
        if isinstance(value, dict) and all(isinstance(value.get(lang), str) for lang in ("cs", "en")):
            return {lang: value[lang] for lang in ("cs", "en")}
    return {lang: str(entry.get("id", "")) for lang in ("cs", "en")}


def entries(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}

    def add(kind: str, entry: dict[str, Any]) -> None:
        if entry.get("id"):
            key = f"{kind}:{entry['id']}"
            found[key] = {"id": entry["id"], "kind": kind, "name": label(entry), "content": entry}

    for kind, part in (
        ("requirement", "ledger"),
        ("source", "sources"),
        ("resource", "resources"),
        ("repository", "repositories"),
        ("page", "pages"),
    ):
        for entry in content[part]:
            add(kind, entry)
    add("guide", {"id": "guide", **content["guide"]["guide"]})
    for data in content["stations"]:
        add("station", data["station"])
        for entry in data.get("advice", []):
            add("advice", entry)
    for data in content["checks"]:
        add("check", data["check"])
        for entry in data.get("item", []):
            add("question", entry)
    for entry in content["live"].get("test", []) + content["live"].get("champion", {}).get("test", []):
        add("test", entry)
    for part in ("layer", "seam", "example", "context"):
        for entry in content.get("model", {}).get(part, []):
            add("model", entry)
    return found


def compare(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    changes = []
    for key in sorted(before.keys() | after.keys()):
        if before.get(key) == after.get(key):
            continue
        entry = after.get(key) or before[key]
        changes.append(
            {key: value for key, value in entry.items() if key != "content"}
            | {"change": "added" if key not in before else "removed" if key not in after else "updated"}
        )
    return changes


def report(root: Path, base: str, head: str) -> dict[str, Any]:
    base, head = revision(base), revision(head)
    with tempfile.TemporaryDirectory() as temporary:
        previous = Path(temporary)
        for name in check_content.git(root, "ls-tree", "-r", "--name-only", base, "content/").splitlines():
            path = Path(name)
            if path.parts[0] != "content" or ".." in path.parts or path.suffix != ".toml":
                continue
            target = previous / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(check_content.git(root, "show", f"{base}:{name}"), encoding="utf-8")
        before = (
            entries(build_crate.load_content(previous / "content"))
            if (previous / "content/guide.toml").exists()
            else {}
        )
    changed = compare(before, entries(build_crate.load_content(root / "content")))
    return {"formatVersion": 1, "base": base, "head": head, "total": len(changed), "items": changed[:200]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/pr-review/summary.json")
    args = parser.parse_args(argv)
    result = report(ROOT, args.base, args.head)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"pr_summary: {result['total']} changed authored items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
