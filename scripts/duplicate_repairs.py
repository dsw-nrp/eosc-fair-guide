"""Provenance and identifier registration for safe duplicate repairs, shared by the local and trusted routes.

Both `check_duplicates.py --fix` and the `/fix-duplicates` handler record one action naming a reviewed person,
the `duplicate-fix` instrument, the consulted registry source and the linked results, and register that action's
identifier. The functions here compute the new file text; each route writes it with its own safety rules.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import register_ids

if TYPE_CHECKING:
    from check_duplicates import Suggestion

INSTRUMENT = "duplicate-fix"
REGISTRY_OBJECTS = {"re3data": "re3data", "fip-dashboard": "fip-dashboard", "knav": "knav"}
IDENTITY_HELP = (
    "Run again with --person <id> naming a reviewed [[person]] in content/guide.toml, or add your reviewed "
    "github login and commitNames there through an ordinary content pull request (CONTRIBUTING.md, "
    "Credit and ORCID iDs)."
)


def person_for(content: dict[str, Any], login: str) -> str | None:
    """Resolve a GitHub login to a reviewed person; never guess or create one."""
    wanted = str(login or "").casefold()
    for person in content["guide"].get("person", []):
        if isinstance(person.get("github"), str) and person["github"].casefold() == wanted:
            return str(person["id"])
    return None


def local_person(content: dict[str, Any], *, chosen: str | None, git_name: str | None) -> tuple[str | None, str]:
    """The reviewed person a local repair records, and how they were found or why none could be."""
    people = content["guide"].get("person", [])
    if chosen:
        if any(person.get("id") == chosen for person in people):
            return chosen, f"recorded as {chosen} (named with --person)"
        return None, f"--person {chosen!r} is not a reviewed [[person]] id. {IDENTITY_HELP}"
    if not git_name:
        return None, f"git user.name is not set, so no reviewed person can be matched. {IDENTITY_HELP}"
    matches = sorted(
        {
            str(person["id"])
            for person in people
            if git_name in person.get("commitNames", [])
            or (isinstance(person.get("github"), str) and person["github"].casefold() == git_name.casefold())
        }
    )
    if len(matches) == 1:
        return matches[0], f"recorded as {matches[0]} (matched git user.name {git_name!r}; override with --person)"
    if matches:
        return None, f"git user.name {git_name!r} matches several people ({', '.join(matches)}). {IDENTITY_HELP}"
    return None, f"git user.name {git_name!r} matches no reviewed person. {IDENTITY_HELP}"


def git_user_name(root: Path) -> str | None:
    try:
        done = subprocess.run(
            ["git", "config", "user.name"], cwd=root, capture_output=True, encoding="utf-8", check=False
        )
    except OSError:
        return None
    return done.stdout.strip() or None


def instrument_available(content: dict[str, Any]) -> bool:
    return any(item.get("id") == INSTRUMENT for item in content["guide"].get("instrument", []))


def cited_source(content: dict[str, Any], record_name: str) -> str | None:
    """The consulted registry source, only when the content cites it."""
    kind = record_name.split(":", 1)[0]
    source_id = REGISTRY_OBJECTS.get(kind)
    if source_id is None:
        return None
    cited = {item["id"] for item in content["sources"]}
    cited |= {item["id"] for item in content["resources"] if item.get("citation")}
    return source_id if source_id in cited else None


def local_action_id(suggestions: list[Suggestion]) -> str:
    """A dated ID for a local repair, stable for the same set of links on the same day."""
    links = sorted(f"{item.entry}|{item.field_name}|{item.value}" for item in suggestions)
    digest = hashlib.sha256("\n".join(links).encode("utf-8")).hexdigest()[:7]
    return f"{datetime.now(UTC).date().isoformat()}-dupfix-local-{digest}"


def action_block(identifier: str, person: str, suggestions: list[Suggestion], content: dict[str, Any]) -> str:
    results = sorted({suggestion.entry.split(":", 1)[1] for suggestion in suggestions})
    sources = sorted(
        {source for suggestion in suggestions if (source := cited_source(content, suggestion.record)) is not None}
    )
    description = (
        f"Linked {', '.join(results)} to the registry record(s) the duplicate check named as a shared identity."
    )
    rows = [
        "[[action]]",
        f"id = {json.dumps(identifier)}",
        'type = "update"',
        'name = "Apply safe duplicate links"',
        f"description = {json.dumps(description)}",
        f"agent = {json.dumps(person)}",
        f"instruments = {json.dumps([INSTRUMENT])}",
    ]
    if sources:
        rows.append(f"objects = {json.dumps(sources)}")
    rows += [
        f"results = {json.dumps(results)}",
        f"endTime = {datetime.now(UTC).replace(microsecond=0).isoformat()}",
    ]
    return "\n".join(rows) + "\n"


def with_action(
    old: str, identifier: str, person: str, suggestions: list[Suggestion], content: dict[str, Any]
) -> str | None:
    """Provenance text with the repair action appended, or None when that action is already recorded."""
    if re.search(rf'(?m)^id\s*=\s*"{re.escape(identifier)}"\s*$', old):
        return None
    return old.rstrip() + "\n\n" + action_block(identifier, person, suggestions, content)


def with_registration(old: str, identifier: str) -> str | None:
    """Register text with only this action ID appended, or None when it is already issued."""
    expected = tomllib.loads(old)
    actions = expected["issued"]["actions"]
    if identifier in expected.get("retired", {}).get("actions", []):
        raise ValueError(f"action identifier {identifier!r} is retired")
    if identifier in actions:
        return None
    section = re.search(r"(?m)^\s*\[issued\][ \t]*(?:#[^\n]*)?$", old)
    if section is None:
        raise ValueError("identifier register has no supported [issued] table")
    following = re.search(r"(?m)^[ \t]*\[", old[section.end() :])
    stop = section.end() + following.start() if following else len(old)
    array = re.search(r"(?m)^[ \t]*actions[ \t]*=[ \t]*(\[[^\]]*\])", old[section.end() : stop])
    if array is None:
        raise ValueError("identifier register has no supported issued actions array")
    start, end = (section.end() + position for position in array.span(1))
    actions.append(identifier)
    new = old[:start] + register_ids.array(actions) + old[end:]
    if tomllib.loads(new) != expected:
        raise ValueError("registering the action would change unrelated identifier data")
    return new


def unified_diff(path: Path, old: str, new: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile=str(path), tofile=str(path)
        )
    )
