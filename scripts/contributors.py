#!/usr/bin/env python3
"""Suggest contributor and attribution patches for a branch, offline and without applying them.

    python scripts/contributors.py [--base REF] [--head REF] [--output FILE]

Reads the commits that changed ``content/`` or ``CITATION.cff`` since the branch left ``--base`` (the remote's
default branch by default) and the provenance actions the branch added. Identities are matched only through reviewed
facts in ``content/guide.toml``: a person's ``github`` login and exact ``commitNames``. AI assistants named as
co-authors are instruments, not people; a ``[bot]`` account is automatic software, whose snapshot refreshes are
reported with their run and source rather than credited to anyone. An identity that matches no person is reported
for confirmation with a stub, never guessed. Suggestions cover: person stubs for unresolved identities,
``CITATION.cff`` contributors for people who are agents of the branch's actions (with an ORCID iD only when known and
not opted out), actions whose agent made none of their commits, people who changed content without an action naming
them, and the shape of an action for an automatic refresh. The JSON report and a Markdown summary are written for the
read-only pull-request checks; nothing in the repository changes. Exits 0 unless git cannot be read.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_crate  # noqa: E402
import check_content  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# Assistants that sign commits as co-authors, by the address their tools use, and the instrument each one is.
AI_ADDRESSES = {
    "noreply@anthropic.com": "claude-opus-5-5",
    "noreply@openai.com": "openai-sol-6-1",
    "codex@openai.com": "openai-sol-6-1",
    "kilo@kilo.ai": "kilo-code",
}
SNAPSHOT_PATHS = ("content/snapshots/", "content/glossary.toml")
NOREPLY = re.compile(r"^(?:\d+\+)?(?P<login>[^@]+)@users\.noreply\.github\.com$", re.IGNORECASE)
TRAILER = re.compile(r"^Co-authored-by:\s*(?P<name>.+?)\s*<(?P<email>[^>]+)>\s*$", re.IGNORECASE | re.MULTILINE)


def commits(root: Path, base: str, head: str) -> list[dict[str, Any]]:
    """Content-changing commits with their author, co-authors and changed paths, oldest first."""
    log = check_content.git(
        root,
        "log",
        "--reverse",
        "--format=%H%x1f%an%x1f%ae%x1f%B%x1e",
        f"{base}..{head}",
        "--",
        "content/",
        "CITATION.cff",
    )
    found = []
    for record in filter(str.strip, log.split("\x1e")):
        sha, name, email, body = record.strip("\n").split("\x1f", 3)
        paths = check_content.git(root, "show", "--name-only", "--format=", sha).split()
        people = [(name, email)] + [(match["name"], match["email"]) for match in TRAILER.finditer(body)]
        found.append({"sha": sha, "identities": people, "paths": paths})
    return found


def classify(name: str, email: str, persons: list[dict[str, Any]]) -> tuple[str, str]:
    """('person', id), ('ai', instrument), ('bot', login) or ('unresolved', name), from reviewed facts only."""
    address = email.lower()
    if address in AI_ADDRESSES:
        return "ai", AI_ADDRESSES[address]
    match = NOREPLY.match(address)
    login = match["login"] if match else ""
    if name.endswith("[bot]") or login.endswith("[bot]"):
        return "bot", login or name
    for person in persons:
        if (login and login == str(person.get("github", "")).lower()) or name in person.get("commitNames", []):
            return "person", person["id"]
    return "unresolved", name


def person_entry(name: str, login: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "contributor"
    lines = ["[[person]]", f'id = "{slug}"', f"name = {json.dumps(name, ensure_ascii=False)}"]
    if login:
        lines.append(f'github = "{login}"')
    return "\n".join(lines)


def actions_at(root: Path, revision: str) -> dict[str, dict[str, Any]]:
    with tempfile.TemporaryDirectory() as temp:
        for path in check_content.git(root, "ls-tree", "-r", "--name-only", revision, "content/").split():
            target = Path(temp) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(check_content.git(root, "show", f"{revision}:{path}"), encoding="utf-8")
        if not (Path(temp) / "content" / "guide.toml").exists():
            return {}
        return {action["id"]: action for action in build_crate.load_content(Path(temp) / "content")["provenance"]}


def report(root: Path, base: str, head: str = "HEAD") -> dict[str, Any]:
    merge_base = check_content.merge_base(root, base)
    content = build_crate.load_content(root / "content")
    persons = content["guide"].get("person", [])
    by_id = {person["id"]: person for person in persons}
    history = commits(root, merge_base, head)
    before = actions_at(root, merge_base)
    added = {
        key: value
        for key, value in {action["id"]: action for action in content["provenance"]}.items()
        if key not in before
    }
    unresolved: dict[str, dict[str, Any]] = {}
    contributors: dict[str, list[str]] = {}
    instruments: dict[str, list[str]] = {}
    automatic = []
    for commit in history:
        for name, email in commit["identities"]:
            kind, value = classify(name, email, persons)
            if kind == "person":
                contributors.setdefault(value, []).append(commit["sha"])
            elif kind == "ai":
                instruments.setdefault(value, []).append(commit["sha"])
            elif kind == "unresolved":
                login = NOREPLY.match(email.lower())
                entry = unresolved.setdefault(
                    name, {"name": name, "github": login["login"] if login else None, "commits": []}
                )
                entry["commits"].append(commit["sha"])
            elif kind == "bot" and all(path.startswith(SNAPSHOT_PATHS) for path in commit["paths"]):
                automatic.append(
                    {
                        "commit": commit["sha"],
                        "software": value,
                        "paths": commit["paths"],
                        "action": {
                            "type": "update",
                            "agent": "the person who reviews and merges the refresh",
                            "instruments": ["the refresh workflow run that made the commit"],
                            "objects": ["the snapshot's source"],
                            "results": commit["paths"],
                        },
                    }
                )
    agents = {action.get("agent") for action in added.values()}
    cff = (root / "CITATION.cff").read_text(encoding="utf-8") if (root / "CITATION.cff").exists() else ""
    credited = cff.split("\nreferences:")[0]  # the software's own authors and contributors, not cited works
    citation = []
    for person_id in sorted(agents & set(by_id)):
        person = by_id[person_id]
        if (person.get("orcid") and person["orcid"] in credited) or all(
            part in credited for part in person["name"].split()
        ):
            continue
        entry = {"name": person["name"]}
        if person.get("orcid") and not person.get("orcidOptOut"):
            entry["orcid"] = person["orcid"]
        citation.append(entry)
    unmatched_actions = [
        {"action": key, "agent": action.get("agent")}
        for key, action in sorted(added.items())
        if contributors and action.get("agent") not in contributors
    ]
    uncredited = sorted(set(contributors) - agents) if added else sorted(contributors)
    return {
        "format_version": 1,
        "base": merge_base,
        "head": head,
        "commits": len(history),
        "added_actions": sorted(added),
        "people": {key: len(value) for key, value in sorted(contributors.items())},
        "instruments": {key: len(value) for key, value in sorted(instruments.items())},
        "patches": {
            "persons": [
                entry | {"stub": person_entry(entry["name"], entry["github"] or "")} for entry in unresolved.values()
            ],
            "citation": citation,
            "actions_without_their_agent": unmatched_actions,
            "people_without_an_action": uncredited,
            "automatic_refreshes": automatic,
        },
    }


def markdown(data: dict[str, Any]) -> str:
    patches = data["patches"]
    lines = [
        "## Contributor and attribution suggestions",
        "",
        f"{data['commits']} content commits since `{data['base'][:12]}`; "
        f"{len(data['added_actions'])} new provenance actions. These are suggestions to confirm, not changes.",
        "",
    ]
    for title, items in (
        (
            "Identities to confirm (no credit is assumed)",
            [
                f"{item['name']}" + (f" (GitHub {item['github']})" if item["github"] else "")
                for item in patches["persons"]
            ],
        ),
        (
            "Possible CITATION.cff contributors",
            [item["name"] + (" with ORCID iD" if item.get("orcid") else "") for item in patches["citation"]],
        ),
        (
            "Actions whose agent made none of the branch's content commits",
            [f"{item['action']} (agent {item['agent']})" for item in patches["actions_without_their_agent"]],
        ),
        ("People who changed content without an action naming them", patches["people_without_an_action"]),
        (
            "Automatic refreshes to record with their run and source",
            [item["commit"][:12] for item in patches["automatic_refreshes"]],
        ),
    ):
        lines.append(f"- {title}: " + (", ".join(items[:20]) + (" …" if len(items) > 20 else "") if items else "none"))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="the compared branch (default: the remote's default branch)")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/pr-review/contributors.json")
    args = parser.parse_args(argv)
    try:
        data = report(ROOT, args.base or check_content.default_base(ROOT), args.head)
    except (subprocess.CalledProcessError, check_content.ContentError) as error:
        print(f"contributors: {error}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(data), encoding="utf-8")
    print(markdown(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
