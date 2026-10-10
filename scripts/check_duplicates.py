#!/usr/bin/env python3
"""Check that no two entries of the guide describe one thing.

An entry is anything the guide lists or says: a curated resource, repository, source or organisation; a record of a
registry the guide mirrors (a FIP Dashboard resource, organisation or FIP, a re3data repository, a Heslář term, a FAIR
Champion test); and a piece of its own text (advice, a check question, a requirement). Two entries of one kind
describe one thing when they share an address, a DOI, a re3data, ROR or FIP Dashboard ID, an identifier, a name or the
same words. A curated entry that links a registry record (``fipDashboard``, ``re3data``) is that record, not a second
entry, and no two curated entries may link one record. A group that looks alike but is kept apart is accepted in
``content/duplicates.toml`` with its reason; any other group is an error, and so is an accepted group that no longer
occurs.

Exit status: 0 when the guide has no duplicate, 1 when it has, 2 when the content cannot be read. Uses only the Python
standard library. The rule is documented in ``docs/content-model.md`` (One entry per thing).
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_crate import ROOT, ContentError, load_content  # noqa: E402
from check_content import Report, bare_url  # noqa: E402

ACCEPTED_FILE = "duplicates.toml"
# Keys that state two entries are the same thing; every other key only suggests it.
LINK_KEYS = ("fd", "fdorg", "r3d")
KEY_NAMES = {
    "url": "address",
    "doi": "DOI",
    "r3d": "re3data ID",
    "ror": "ROR ID",
    "fd": "FIP Dashboard ID",
    "fdorg": "FIP Dashboard ID",
    "id": "identifier",
    "name": "name",
    "text": "text",
    "requirement": "requirement",
}


@dataclass
class Entry:
    name: str  # as the content checks name it: kind and content ID
    group: str  # entries are compared within their group only
    curated: bool  # the guide's own entry, as opposed to a registry's record or a piece of text
    keys: set[str] = field(default_factory=set)


def words(value: Any) -> list[str]:
    """Every form of a name or text, normalised: a string, or each language of a table (not its `inLanguage`)."""
    values = [item for key, item in value.items() if key != "inLanguage"] if isinstance(value, dict) else [value]
    out = []
    for item in values:
        if isinstance(item, str):
            normal = re.sub(r"\W+", " ", item.lower()).strip()
            if normal:
                out.append(normal)
    return out


def thing(label: str, curated: bool, /, **keys: Any) -> Entry:
    """A resource, repository, source or registry record, keyed by what identifies it."""
    entry = Entry(label, "things", curated)
    for kind, values in keys.items():
        for value in values if isinstance(values, list) else [values]:
            if value:
                entry.keys.add(f"{kind}:{value}")
    return entry


def entries(content: dict[str, Any]) -> list[Entry]:
    out: list[Entry] = []
    for resource in content["resources"]:
        citation = resource.get("citation", {})
        repository = resource.get("repository", {})
        out.append(
            thing(
                f"resource:{resource['id']}",
                True,
                url=bare_url(resource.get("url")),
                doi=citation.get("doi", "").lower(),
                r3d=repository.get("re3data"),
                fd=resource.get("fipDashboard"),
                id=resource["id"],
                name=words(resource.get("name")),
            )
        )
    for repository in content["repositories"]:
        out.append(
            thing(
                f"repository:{repository['id']}",
                True,
                url=bare_url(repository.get("url")),
                doi=(repository.get("fairsharing") or "").lower(),
                r3d=repository.get("re3data"),
                fd=repository.get("fipDashboard"),
                id=repository["id"],
                name=words(repository.get("name")),
            )
        )
    for source in content["sources"]:
        doi = (source.get("doi") or "").lower()
        out.append(
            thing(
                f"source:{source['id']}",
                True,
                url=[bare_url(source.get("url")), bare_url("https://doi.org/" + doi) if doi else ""],
                doi=doi,
                name=words(source.get("title")),
            )
        )
    for snapshot in content["snapshots"]:
        for record in snapshot.get("resource", []):
            out.append(
                thing(
                    f"fip-dashboard:{record['id']}",
                    False,
                    url=bare_url(record.get("url")),
                    fd=record["id"],
                    id=record["id"],
                    name=words(record.get("name")),
                )
            )
        for record in snapshot.get("repository", []):
            out.append(
                thing(
                    f"re3data:{record['re3data']}",
                    False,
                    url=bare_url(record.get("url")),
                    r3d=record["re3data"],
                    name=words(record.get("name")),
                )
            )
        for record in snapshot.get("organization", []):
            entry = thing(
                f"fip-dashboard-organisation:{record['id']}",
                False,
                url=bare_url(record.get("url")),
                ror=record.get("ror"),
                fdorg=record["id"],
                name=words(record.get("name")),
            )
            entry.group = "organisations"
            out.append(entry)
        for record in snapshot.get("fip", []):
            out.append(
                Entry(f"fip:{record['id']}", "fips", False, {f"name:{name}" for name in words(record.get("title"))})
            )
    for organization in content["guide"].get("organization", []):
        entry = thing(
            f"organization:{organization['id']}",
            True,
            url=bare_url(organization.get("url")),
            ror=organization.get("ror"),
            fdorg=organization.get("fipDashboard"),
            name=words(organization.get("name")),
        )
        entry.group = "organisations"
        out.append(entry)
    for term in content["glossary"].get("term", []):
        out.append(Entry(f"term:{term['id']}", "terms", False, {f"name:{name}" for name in words(term.get("label"))}))
    for test in content["live"].get("champion", {}).get("test", []):
        out.append(Entry(f"test:{test['id']}", "tests", False, {f"name:{name}" for name in words(test.get("label"))}))
    for data in content["stations"]:
        for advice in data.get("advice", []):
            out.append(
                Entry(f"advice:{advice['id']}", "advice", True, {f"text:{text}" for text in words(advice.get("text"))})
            )
    for data in content["checks"]:
        check_id = data["check"]["id"]
        for item in data.get("item", []):
            keys = {f"text:{text}" for text in words(item.get("statement"))}
            keys |= {f"requirement:{item['requirement']}"} if item.get("requirement") else set()
            out.append(Entry(f"item:{item['id']}", f"questions:{check_id}", True, keys))
    for clause in content["ledger"]:
        out.append(
            Entry(
                f"clause:{clause['id']}", "requirements", True, {f"text:{text}" for text in words(clause.get("text"))}
            )
        )
    return out


class Components:
    """Entries that one link joins into one thing."""

    def __init__(self, names: list[str]) -> None:
        self.parent = {name: name for name in names}

    def find(self, name: str) -> str:
        while self.parent[name] != name:
            self.parent[name] = self.parent[self.parent[name]]
            name = self.parent[name]
        return name

    def join(self, first: str, second: str) -> None:
        self.parent[self.find(first)] = self.find(second)


def remedy(group: list[Entry]) -> str:
    curated = [entry for entry in group if entry.curated]
    records = [entry for entry in group if not entry.curated]
    if group[0].group not in ("things", "organisations"):
        if records:
            return "the registry lists one thing twice; accept the pair in content/duplicates.toml with the reason"
        return "say it once"
    if len(curated) > 1:
        return "merge them into one entry"
    if curated and records:
        kinds = {record.name.split(":")[0] for record in records}
        if "re3data" in kinds:
            return "state the record's ID as re3data"
        return "link the record with fipDashboard"
    return (
        "the registries list one thing twice; curate one entry that links both, "
        "or accept the pair in content/duplicates.toml"
    )


def check(content: dict[str, Any], accepted: list[dict[str, Any]]) -> Report:
    report = Report()
    found = entries(content)
    by_name = {entry.name: entry for entry in found}
    components = Components(list(by_name))
    # A link joins a curated entry and the registry record it names into one thing.
    holders: dict[tuple[str, str], list[Entry]] = {}
    for entry in found:
        for key in entry.keys:
            holders.setdefault((entry.group, key), []).append(entry)
    for (_group, key), holding in holders.items():
        if key.split(":", 1)[0] in LINK_KEYS:
            for entry in holding[1:]:
                components.join(holding[0].name, entry.name)
            curated = sorted(entry.name for entry in holding if entry.curated)
            if len(curated) > 1:
                kind, value = key.split(":", 1)
                report.error(
                    curated[0],
                    f"links the same record as {', '.join(curated[1:])} ({KEY_NAMES[kind]} '{value}'); "
                    "merge them into one entry",
                )
    # Any key that two things share is a duplicate, unless it is accepted.
    groups: dict[frozenset[str], set[str]] = {}
    for (_group, key), holding in holders.items():
        things = {components.find(entry.name) for entry in holding}
        if len(things) > 1:
            groups.setdefault(frozenset(entry.name for entry in holding), set()).add(key)
    accepted_sets = [frozenset(item.get("entries", [])) for item in accepted]
    for index, item in enumerate(accepted):
        if not str(item.get("reason", "")).strip():
            report.error(f"duplicates:{index + 1}", "an accepted group states no reason")
        unknown = sorted(set(item.get("entries", [])) - by_name.keys())
        if unknown:
            report.error(f"duplicates:{index + 1}", f"names no entry: {', '.join(unknown)}")
    used: set[frozenset[str]] = set()
    for names, keys in sorted(groups.items(), key=lambda pair: sorted(pair[0])):
        match = next((accepted_set for accepted_set in accepted_sets if names <= accepted_set), None)
        if match is not None:
            used.add(match)
            continue
        ordered = sorted(names)
        shared = "; ".join(f"{KEY_NAMES[key.split(':', 1)[0]]} '{key.split(':', 1)[1]}'" for key in sorted(keys))
        report.error(
            ordered[0],
            f"describes one thing with {', '.join(ordered[1:])} ({shared}); "
            + remedy([by_name[name] for name in ordered]),
        )
    for index, accepted_set in enumerate(accepted_sets):
        if accepted_set and accepted_set not in used:
            report.error(f"duplicates:{index + 1}", "the accepted group no longer occurs; remove it")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this repository)")
    args = parser.parse_args(argv)
    try:
        content = load_content(args.root / "content")
        path = args.root / "content" / ACCEPTED_FILE
        accepted = tomllib.loads(path.read_text(encoding="utf-8")).get("accepted", []) if path.exists() else []
    except (ContentError, KeyError, tomllib.TOMLDecodeError) as error:
        print(f"check_duplicates: cannot read the content: {error}", file=sys.stderr)
        return 2
    report = check(content, accepted)
    for error in report.errors:
        print(f"error: {error}")
    print(f"check_duplicates: {len(report.errors)} errors")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
