#!/usr/bin/env python3
"""Check that no two entries of the guide describe one thing.

An entry is anything the guide lists or says: a curated resource, repository, source or organisation; a record of a
registry the guide mirrors (a FIP Dashboard resource, organisation or FIP, a re3data repository, a KNAV catalogue tool,
a Heslář term, a FAIR Champion test); and a piece of its own text (advice, a check question, a requirement). Two
entries of one kind describe one thing when they share an address, a DOI, a re3data, ROR, FIP Dashboard or KNAV ID, an
identifier, a name or the same words. A curated entry that links a registry record (``fipDashboard``, ``re3data``,
``knav``) is that record, not a second entry, and no two curated entries may link one record; a record annotation
(``[[record]]`` in ``content/repositories.toml``) joins the records of several registries it names. A group that looks
alike but is kept apart is accepted in ``content/duplicates.toml`` with its reason; any other group is an error, and
so is an accepted group that no longer occurs.

Exit status: 0 when the guide has no duplicate, 1 when it has, 2 when the content cannot be read. Uses only the Python
standard library. The rule is documented in ``docs/content-model.md`` (One entry per thing).
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import tempfile
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_content  # noqa: E402
import duplicate_repairs  # noqa: E402
from build_crate import ROOT, ContentError, load_content  # noqa: E402
from catalogue_identity import alternate_id, bare_url  # noqa: E402

ACCEPTED_FILE = "duplicates.toml"
# Exact reviewed placements, keyed by curated entry kind and registry link field.
PLACEMENTS = {
    ("resource", "re3data"): ("content/resources.toml", "resource.repository"),
    ("resource", "fipDashboard"): ("content/resources.toml", ""),
    ("resource", "knav"): ("content/resources.toml", ""),
    ("repository", "re3data"): ("content/repositories.toml", ""),
    ("repository", "fipDashboard"): ("content/repositories.toml", ""),
    ("repository", "knav"): ("content/repositories.toml", ""),
    ("source", "knav"): ("content/sources.toml", ""),
}


def valid_placement(entry: Any, file: Any, table: Any, field_name: Any) -> bool:
    if not all(isinstance(value, str) for value in (entry, file, table, field_name)):
        return False
    kind, separator, identifier = entry.partition(":")
    return bool(separator and identifier) and PLACEMENTS.get((kind, field_name)) == (file, table)


AUTHORITATIVE_KEYS = ("url", "doi", "r3d", "fd", "knav")
# Keys that state two entries are the same thing; every other key only suggests it.
LINK_KEYS = ("fd", "fdorg", "r3d", "knav")
KEY_NAMES = {
    "url": "address",
    "doi": "DOI",
    "r3d": "re3data ID",
    "ror": "ROR ID",
    "fd": "FIP Dashboard ID",
    "fdorg": "FIP Dashboard ID",
    "knav": "KNAV catalogue ID",
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
    record: dict[str, Any] | None = None  # the authored or snapshot row, for an exact suggestion


@dataclass(frozen=True)
class Suggestion:
    """A link the duplicate check can name without deciding that two records are one thing."""

    entry: str
    record: str
    resolution: str
    safe: bool
    file: str
    table: str
    field_name: str
    value: str
    reason: str


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


def thing(label: str, curated: bool, /, record: dict[str, Any] | None = None, **keys: Any) -> Entry:
    """A resource, repository, source or registry record, keyed by what identifies it."""
    entry = Entry(label, "things", curated, record=record)
    for kind, values in keys.items():
        for value in values if isinstance(values, list) else [values]:
            if value:
                entry.keys.add(f"{kind}:{value}")
    return entry


def entries(content: dict[str, Any]) -> list[Entry]:
    out: list[Entry] = []
    # A record annotation joins the records it names across registries: each of them carries the others' IDs.
    joined: dict[str, dict[str, Any]] = {}
    for item in content.get("repository_records", []):
        ids = {"r3d": item.get("re3data"), "fd": item.get("fipDashboard"), "knav": item.get("knav")}
        for kind, value in ids.items():
            if value:
                joined[f"{kind}:{value}"] = ids
    for resource in content["resources"]:
        citation = resource.get("citation", {})
        repository = resource.get("repository", {})
        out.append(
            thing(
                f"resource:{resource['id']}",
                True,
                record=resource,
                url=bare_url(resource.get("url")),
                doi=citation.get("doi", "").lower(),
                r3d=repository.get("re3data"),
                fd=resource.get("fipDashboard"),
                knav=resource.get("knav"),
                id=resource["id"],
                name=words(resource.get("name")),
            )
        )
    for repository in content["repositories"]:
        out.append(
            thing(
                f"repository:{repository['id']}",
                True,
                record=repository,
                url=bare_url(repository.get("url")),
                doi=(repository.get("fairsharing") or "").lower(),
                r3d=repository.get("re3data"),
                fd=repository.get("fipDashboard"),
                knav=repository.get("knav"),
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
                record=source,
                url=[bare_url(source.get("url")), bare_url("https://doi.org/" + doi) if doi else ""],
                doi=doi,
                knav=source.get("knav"),
                name=words(source.get("title")),
            )
        )
    for snapshot in content["snapshots"]:
        for record in snapshot.get("resource", []):
            out.append(
                thing(
                    f"fip-dashboard:{record['id']}",
                    False,
                    record=record,
                    url=bare_url(record.get("url")),
                    fd=alternate_id(record, "fip-dashboard"),
                    knav=joined.get("fd:" + str(alternate_id(record, "fip-dashboard")), {}).get("knav"),
                    id=record["id"],
                    name=words(record.get("name")),
                )
            )
        for record in snapshot.get("repository", []):
            out.append(
                thing(
                    f"re3data:{record['re3data']}",
                    False,
                    record=record,
                    url=bare_url(record.get("url")),
                    r3d=record["re3data"],
                    fd=joined.get(f"r3d:{record['re3data']}", {}).get("fd"),
                    knav=joined.get(f"r3d:{record['re3data']}", {}).get("knav"),
                    name=words(record.get("name")),
                )
            )
        for record in snapshot.get("tool", []):
            out.append(
                thing(
                    f"knav:{record['id']}",
                    False,
                    record=record,
                    url=bare_url(record.get("url") or record.get("httpUrl")),
                    knav=alternate_id(record, "knav"),
                    name=words(record.get("name")),
                )
            )
        for record in snapshot.get("organization", []):
            entry = thing(
                f"fip-dashboard-organisation:{record['id']}",
                False,
                record=record,
                url=bare_url(record.get("url")),
                ror=record.get("ror"),
                fdorg=alternate_id(record, "fip-dashboard"),
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
            record=organization,
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


@dataclass
class DuplicateReport:
    errors: list[str] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")


def entry_kind(entry: Entry) -> str:
    return entry.name.split(":", 1)[0]


def key_value(entry: Entry, prefix: str) -> str:
    """The record's own value for one identity key, as stored in the entry keys."""
    for key in entry.keys:
        if key.startswith(prefix + ":"):
            return key.split(":", 1)[1]
    return ""


def record_link(entry: Entry) -> tuple[str, str, str] | None:
    """The link field a registry record can lend to a curated entry."""
    kind = entry_kind(entry)
    if kind == "re3data":
        value = key_value(entry, "r3d") or str((entry.record or {}).get("re3data", ""))
        return "r3d", "re3data", value
    if kind == "fip-dashboard":
        return "fd", "fipDashboard", key_value(entry, "fd")
    if kind == "knav":
        return "knav", "knav", key_value(entry, "knav")
    return None


def curated_target(entry: Entry, field_name: str) -> tuple[str, str] | None:
    """Where a curated entry stores one link field, or None when adding it needs review."""
    placement = PLACEMENTS.get((entry_kind(entry), field_name))
    if placement is None:
        return None
    record = entry.record or {}
    target = record.get("repository") if placement[1] else record
    return placement if isinstance(target, dict) and field_name not in target else None


def suggestion_for(group: list[Entry], owners: dict[str, set[str]]) -> Suggestion | None:  # noqa: PLR0911
    """A safe, exact link suggestion, or None when the group needs editorial judgement."""
    curated = [entry for entry in group if entry.curated]
    records = [entry for entry in group if not entry.curated]
    if len(curated) != 1 or len(records) != 1:
        return None
    curated_entry, record_entry = curated[0], records[0]
    if curated_entry.record is None or record_entry.record is None:
        return None
    link = record_link(record_entry)
    if link is None:
        return None
    _prefix, field_name, value = link
    if not value:
        return None
    if any(owners.get(key, set()) - {curated_entry.name} for key in record_entry.keys):
        return None
    shared = {key for key in curated_entry.keys & record_entry.keys if key.split(":", 1)[0] in AUTHORITATIVE_KEYS}
    if not shared:
        return None
    target = curated_target(curated_entry, field_name)
    if target is None:
        return None
    file, table = target
    order = {key: index for index, key in enumerate(AUTHORITATIVE_KEYS)}
    reason_key = min(shared, key=lambda key: (order[key.split(":", 1)[0]], key))
    reason_kind, reason_value = reason_key.split(":", 1)
    return Suggestion(
        entry=curated_entry.name,
        record=record_entry.name,
        resolution="link",
        safe=True,
        file=file,
        table=table,
        field_name=field_name,
        value=value,
        reason=f"shares {KEY_NAMES[reason_kind]} '{reason_value}'",
    )


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
        fields = {"fip-dashboard": "fipDashboard", "knav": "knav"}
        return "link the record with " + " and ".join(fields[kind] for kind in sorted(kinds) if kind in fields)
    return (
        "the registries list one thing twice; curate one entry that links both, "
        "or accept the pair in content/duplicates.toml"
    )


def check(content: dict[str, Any], accepted: list[dict[str, Any]]) -> DuplicateReport:
    report = DuplicateReport()
    found = entries(content)
    by_name = {entry.name: entry for entry in found}
    components = Components(list(by_name))
    # A link joins a curated entry and the registry record it names into one thing.
    holders: dict[tuple[str, str], list[Entry]] = {}
    for entry in found:
        for key in entry.keys:
            holders.setdefault((entry.group, key), []).append(entry)
    owners = {
        key: {entry.name for entry in holding if entry.curated}
        for (_group, key), holding in holders.items()
        if key.split(":", 1)[0] in LINK_KEYS
    }
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
        suggestion = suggestion_for([by_name[name] for name in ordered], owners)
        if suggestion is not None:
            report.suggestions.append(suggestion)
    targets: dict[tuple[str, str, str, str], set[str]] = {}
    proposed_owners: dict[str, set[str]] = {}
    for suggestion in report.suggestions:
        target = (suggestion.file, suggestion.table, suggestion.entry, suggestion.field_name)
        targets.setdefault(target, set()).add(suggestion.value)
        proposed_owners.setdefault(components.find(suggestion.record), set()).add(suggestion.entry)
    unique: dict[tuple[str, str, str, str, str], Suggestion] = {}
    for suggestion in report.suggestions:
        unique.setdefault(
            (suggestion.entry, suggestion.file, suggestion.table, suggestion.field_name, suggestion.value), suggestion
        )
    report.suggestions = [
        suggestion
        for suggestion in unique.values()
        if len(targets[(suggestion.file, suggestion.table, suggestion.entry, suggestion.field_name)]) == 1
        and len(proposed_owners[components.find(suggestion.record)]) == 1
    ]
    for index, accepted_set in enumerate(accepted_sets):
        if accepted_set and accepted_set not in used:
            report.error(f"duplicates:{index + 1}", "the accepted group no longer occurs; remove it")
    return report


def report_payload(report: DuplicateReport) -> dict[str, Any]:
    return {
        "formatVersion": 1,
        "check": "duplicates",
        "errors": list(report.errors),
        "suggestions": [
            {
                "entry": suggestion.entry,
                "record": suggestion.record,
                "resolution": suggestion.resolution,
                "safe": suggestion.safe,
                "file": suggestion.file,
                "table": suggestion.table,
                "field": suggestion.field_name,
                "value": suggestion.value,
                "reason": suggestion.reason,
            }
            for suggestion in report.suggestions
        ],
    }


def write_report(path: Path, report: DuplicateReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report_payload(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _is_table_header(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("[") and stripped.endswith("]")


def atomic_replace(
    path: Path, data: bytes, *, expected: bytes, on_replaced: Callable[[Path, bytes], None] | None = None
) -> None:
    """Prepare a sibling, then swap only if the target still has the inspected bytes."""
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    os.close(descriptor)
    try:
        temporary.write_bytes(data)
        temporary.chmod(path.stat().st_mode)
        if path.read_bytes() != expected:
            raise OSError(f"target changed while preparing the repair: {path}")
        os.replace(temporary, path)
        if on_replaced is not None:
            on_replaced(path, data)
    finally:
        temporary.unlink(missing_ok=True)


def field_table(parsed: dict[str, Any], entry_header: str, entry_id: str, table: str) -> dict[str, Any] | None:
    """Find the actual target table, including unusually formatted existing keys."""
    row = next((item for item in parsed.get(entry_header.strip("[]"), []) if item.get("id") == entry_id), None)
    if row is None:
        return None
    target = row
    for part in table.split(".")[1:] if table else []:
        target = target.get(part)
        if not isinstance(target, dict):
            return None
    return target


def insert_field(
    path: Path,
    entry_header: str,
    entry_id: str,
    table: str,
    *,
    field_name: str,
    value: str,
    on_replaced: Callable[[Path, bytes], None] | None = None,
) -> str | None:
    """Insert one link into the exact entry and table, returning its unified diff."""
    original = path.read_bytes()
    old = original.decode("utf-8")
    parsed = tomllib.loads(old)
    target = field_table(parsed, entry_header, entry_id, table)
    if target is None or field_name in target:
        return None
    lines = old.splitlines(keepends=True)
    start = None
    block_end = None
    id_line = None
    id_pattern = re.compile(rf'^\s*id\s*=\s*"{re.escape(entry_id)}"\s*$')
    for index, line in enumerate(lines):
        if line.strip() != entry_header:
            continue
        end = next((item for item in range(index + 1, len(lines)) if lines[item].lstrip().startswith("[[")), len(lines))
        found = next((item for item in range(index, end) if id_pattern.match(lines[item])), None)
        if found is not None:
            start, block_end, id_line = index, end, found
            break
    if start is None or block_end is None or id_line is None:
        return None
    if table:
        header = f"[{table}]"
        header_line = next((item for item in range(start, block_end) if lines[item].strip() == header), None)
        if header_line is None:
            return None
        insert_at = header_line + 1
        while insert_at < block_end and not _is_table_header(lines[insert_at]):
            insert_at += 1
    else:
        insert_at = id_line + 1
    if insert_at > 0 and not lines[insert_at - 1].endswith(("\n", "\r")):
        lines[insert_at - 1] += "\n"
    lines.insert(insert_at, f"{field_name} = {json.dumps(value, ensure_ascii=False)}\n")
    new = "".join(lines)
    target[field_name] = value
    try:
        if tomllib.loads(new) != parsed:
            return None
    except tomllib.TOMLDecodeError:
        return None
    diff = "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )
    atomic_replace(path, new.encode("utf-8"), expected=original, on_replaced=on_replaced)
    return diff


def apply_suggestion(
    root: Path, suggestion: Suggestion, *, on_replaced: Callable[[Path, bytes], None] | None = None
) -> str | None:
    if (
        suggestion.safe is not True
        or suggestion.resolution != "link"
        or not valid_placement(suggestion.entry, suggestion.file, suggestion.table, suggestion.field_name)
    ):
        return None
    kind = suggestion.entry.split(":", 1)[0]
    header = {"resource": "[[resource]]", "repository": "[[repository]]", "source": "[[source]]"}.get(kind)
    if header is None or ":" not in suggestion.entry:
        return None
    entry_id = suggestion.entry.split(":", 1)[1]
    return insert_field(
        root / suggestion.file,
        header,
        entry_id,
        suggestion.table,
        field_name=suggestion.field_name,
        value=suggestion.value,
        on_replaced=on_replaced,
    )


def _accepted(root: Path) -> list[dict[str, Any]]:
    path = root / "content" / ACCEPTED_FILE
    return tomllib.loads(path.read_text(encoding="utf-8")).get("accepted", []) if path.exists() else []


def apply_local(
    root: Path, report: DuplicateReport, *, person: str, content: dict[str, Any]
) -> tuple[DuplicateReport, bool]:
    """Apply the complete repair (links, provenance action, its registration) with byte-preserving rollback."""
    originals: dict[Path, bytes] = {}
    written: dict[Path, bytes] = {}
    diffs = []
    applied = []

    def restore() -> None:
        for path, expected in written.items():
            try:
                atomic_replace(path, originals[path], expected=expected)
            except OSError as error:
                print(f"check_duplicates: cannot restore {path}: {error}", file=sys.stderr)

    def write_text(relative: str, new: str | None) -> None:
        if new is None:
            return
        path = root / relative
        old = originals.setdefault(path, path.read_bytes())
        diffs.append(duplicate_repairs.unified_diff(path, old.decode("utf-8"), new))
        atomic_replace(path, new.encode("utf-8"), expected=old, on_replaced=written.__setitem__)

    # Errors that predate the repair stay the contributor's own work; only errors the repair adds reject it.
    existing = set(check_content.check(content, root).errors)
    try:
        for suggestion in report.suggestions:
            if not valid_placement(suggestion.entry, suggestion.file, suggestion.table, suggestion.field_name):
                continue
            path = root / suggestion.file
            if path not in originals:
                originals[path] = path.read_bytes()
            diff = apply_suggestion(root, suggestion, on_replaced=written.__setitem__)
            if diff:
                diffs.append(diff)
                applied.append(suggestion)
        if not diffs:
            print("check_duplicates: no safe suggestion could be applied")
            return report, False
        identifier = duplicate_repairs.local_action_id(applied)
        provenance = (root / "content/provenance.toml").read_text(encoding="utf-8")
        write_text(
            "content/provenance.toml", duplicate_repairs.with_action(provenance, identifier, person, applied, content)
        )
        register = root / "content/identifiers.toml"
        if register.is_file():
            write_text(
                "content/identifiers.toml",
                duplicate_repairs.with_registration(register.read_text(encoding="utf-8"), identifier),
            )
        updated = load_content(root / "content")
        checked = check(updated, _accepted(root))
        added = [error for error in check_content.check(updated, root).errors if error not in existing]
        if checked.errors or added:
            restore()
            print("check_duplicates: repair rejected; original files restored where possible")
            return DuplicateReport(errors=[*checked.errors, *added], suggestions=checked.suggestions), False
    except (OSError, ValueError, ContentError, KeyError):
        restore()
        raise
    print("".join(diffs), end="")
    print(f"check_duplicates: applied the safe links with provenance action {identifier} and its registration.")
    return checked, True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this repository)")
    parser.add_argument("--report", type=Path, help="write the suggestion collection to this JSON file")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="apply the safe link suggestions to the working tree with their provenance action and registration",
    )
    parser.add_argument(
        "--person",
        help="reviewed [[person]] id responsible for --fix (default: matched from git user.name)",
    )
    args = parser.parse_args(argv)
    try:
        content = load_content(args.root / "content")
        accepted = _accepted(args.root)
    except (OSError, ContentError, KeyError, ValueError) as error:
        print(f"check_duplicates: cannot read the content: {error}", file=sys.stderr)
        return 2
    report = check(content, accepted)
    for error in report.errors:
        print(f"error: {error}")
    for suggestion in report.suggestions:
        table = f" [{suggestion.table}]" if suggestion.table else ""
        print(
            f'fix: {suggestion.entry}: add {suggestion.field_name} = "{suggestion.value}" '
            f"to {suggestion.file}{table} ({suggestion.reason})"
        )
    applied = False
    if args.fix:
        if not report.suggestions:
            if report.errors:
                print("check_duplicates: no safe suggestion applies; review the errors above")
            else:
                print("check_duplicates: nothing to fix")
        else:
            # Responsibility and the instrument are settled before anything is written.
            person, resolution = duplicate_repairs.local_person(
                content, chosen=args.person, git_name=duplicate_repairs.git_user_name(args.root)
            )
            if person is None:
                print(f"check_duplicates: no file was changed; {resolution}", file=sys.stderr)
                return 2
            if not duplicate_repairs.instrument_available(content):
                print(
                    f"check_duplicates: no file was changed; the {duplicate_repairs.INSTRUMENT!r} instrument is "
                    "missing from content/guide.toml. Update the branch from the default branch first.",
                    file=sys.stderr,
                )
                return 2
            print(f"check_duplicates: {resolution}")
            try:
                report, applied = apply_local(args.root, report, person=person, content=content)
            except (OSError, ContentError, KeyError, ValueError) as error:
                print(f"check_duplicates: cannot apply the repair: {error}", file=sys.stderr)
                return 2
            for error in report.errors:
                print(f"error: {error}")
    report_path = args.report
    if report_path is None and os.environ.get("CHECK_REPORT_DIR"):
        report_path = Path(os.environ["CHECK_REPORT_DIR"]) / "duplicates.json"
    if report_path is not None:
        write_report(report_path, report)
    print(f"check_duplicates: {len(report.errors)} errors")
    return 1 if report.errors or (args.fix and not applied) else 0


if __name__ == "__main__":
    sys.exit(main())
