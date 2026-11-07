#!/usr/bin/env python3
"""One-time migration of the authored content to the kind vocabulary (unify-identity-model-and-api, decision 17).

Usage: python openspec/changes/unify-identity-model-and-api/migration/migrate.py [--dry-run] [--root DIR]

Rewrites the TOML files under content/. This folder alone knows the forms the content had before; the repository's
scripts and tests know only the current ones. A harvest proposed before the change and merged after it is migrated
with the same script. Steps:

- identifiers: the reviewed reassignments in ``ids.toml`` give generated snapshot rows identifiers without collision
  counters, each row found by its source's own identifier, and rename the entries that name those rows, because a
  reassignment is an editorial decision no refresh can make;
- snapshots: every generated snapshot is renormalised without a new observation: its rows, source passages and
  retrieval date stay, its identities are revalidated and its stored routes translated (``renormalise_snapshot``);
- page sections: a section without an ``id`` took its position as its fragment, which moved whenever its page was
  reordered; each takes its reviewed ``id`` from ``ids.toml``, found by its page, its position and its English
  heading, and a section that has an ``id`` keeps it;
- question statements: a question that copies its requirement clause in both languages drops its copy and takes the
  clause's text; one that copies a clause among its sources names it as its requirement first (``statements.toml``),
  and a clause takes the references the copy carried where that table says so;
- routes: stored ``guideRoute`` values, through the reviewed ``[routes]`` table in ``routes.toml``;
- references: every prose reference ``[[target|phrase]]`` to its one form, ``[[<kind>/<id>|phrase]]``. The word
  forms (``term:``, ``page:``, ``station:``, ``clause:``, ``infrastructure:``), the code addresses (``res/srv/``,
  ``term/``, ``step/`` and the rest) and bare resource or source IDs all name the same record by its address; a bare
  ID takes the kind its row's route freezes. A kind's list (``[[infrastructures|...]]``) keeps its name, and the
  Guide's profile (``[[profile|...]]``) is named by the section of the machines page that presents it;
- in-page links: an ``href`` that opened an entity by its build key (``#station-plan``) or a crate-local list
  (``#repositories?function=...``) names the record by its address (``stations/plan``) or the list by its kind;
- link reviews: each reviewed missing-link decision names its target by address, and a decision that was current
  before the migration stays current: its text hash follows the field, whose only change is the reference markup;
- the identifier register: every issued and retired identifier is keyed by the kind of its record, with its address
  without the kind as the value (``lenses = ["V"]`` becomes ``vocabularies = ["lenses/V", ...]``, a callout item
  ``callout.x.y`` ``callouts = ["x#y"]``, a station's model context ``stations = ["plan#context-V"]``, a local test
  ``tests = ["guide/guide-dataset-01"]``, and sources share ``resources``); no category keeps its old name;
- provenance results: each content ID or prefix pattern (``test:x``, ``provider:*``, ``plan.*``) becomes the addresses
  that name the same published records and parts (``tests/guide/x``, ``tests/f-uji/*``, ``advice/plan.*``), read from
  the build of the migrated copy; ``guide`` and ``*`` stay;
- fields that can name records of several kinds: provenance ``objects``, model association ``target`` and the worked
  example's ``steps`` name each record by its address (``A.F1.R1`` becomes ``clauses/A.F1.R1``,
  ``test:guide-dataset-01`` ``tests/guide/guide-dataset-01``), through the content check's own map of content IDs.

The steps run on a temporary copy of the content, so the whole result is checked before anything is written.
Idempotent: a second run changes nothing. ``--dry-run`` prints the unified diff and writes nothing. Uses only the
Python standard library and the repository's own scripts.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import register_ids  # noqa: E402
from build_crate import LANGS, Graph, build_crate, load_content, result_covers  # noqa: E402
from catalogue_identity import KINDS, RECORD_KINDS, parse_route, source_scheme, validate_identity  # noqa: E402
from check_content import content_addresses, copied_clause, walk  # noqa: E402

TABLES = tomllib.loads((HERE / "routes.toml").read_text(encoding="utf-8"))
ROUTES: dict[str, str] = TABLES["routes"]
# Every code prefix of a published address and the route it becomes.
PREFIXES: dict[str, str] = ROUTES | TABLES["prefixes"]
REFERENCE = re.compile(r"\[\[(?P<id>[^\[\]|]+)\|(?P<phrase>[^\[\]|]+)\]\]")
# The word forms of a reference and the kind each names.
WORD_KINDS = {
    "term": "glossary",
    "page": "pages",
    "station": "stations",
    "clause": "clauses",
    "infrastructure": "infrastructures",
}
# Non-record targets that keep their names: a kind's list.
KEPT = set(KINDS)
# Non-record targets that name a record's part instead: the Guide's profile, as the machines page presents it.
REPLACED = {"profile": "pages/machines#tasks"}
# The prose sections whose fields the missing-link review covers (scripts/check_health.py, missing_links).
REVIEWED_SECTIONS = ("pages", "stations", "checks", "callouts", "resources")


def generated_files(root: Path) -> set[Path]:
    """The snapshot files the source refresh owns; they are renormalised by their generator, not here. A content
    fixture without a source registry holds no generated snapshot."""
    path = root / ".github" / "source-registry.json"
    if not path.exists():
        return set()
    registry = json.loads(path.read_text(encoding="utf-8"))
    return {(root / item).resolve() for entry in registry["sources"] for item in entry["files"]}


def authored_files(root: Path) -> list[Path]:
    generated = generated_files(root)
    return [path for path in sorted((root / "content").rglob("*.toml")) if path.resolve() not in generated]


def address_of(target: str) -> str:
    """A code address (`res/srv/x`, `pr/F1`) as its address in the kind vocabulary; an address stays as it is."""
    head, identifier = target.rsplit("/", 1)
    if head.split("/")[0] in KINDS:
        return target
    if head not in PREFIXES:
        raise ValueError(f"unknown address form '{target}'")
    kind, scope = parse_route(PREFIXES[head])
    return "/".join(filter(None, (kind, scope, identifier)))


def bare_kinds(root: Path) -> dict[str, str]:
    """A bare reference names a resource or a source; its kind is the one its row's route freezes."""
    kinds: dict[str, str] = {}
    for name in ("resources.toml", "sources.toml"):
        path = root / "content" / name
        data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        for row in data.get("resource", []) + data.get("source", []):
            route = ROUTES.get(row.get("guideRoute", ""), row.get("guideRoute") or "resources")
            kinds[row["id"]] = parse_route(route)[0]
    return kinds


def reference_address(target: str, bare: dict[str, str]) -> str:
    """The one form of a reference target: `<kind>/<id>`, a part's `<kind>/<id>#<fragment>`, or a kind."""
    if target in KEPT:
        return target
    if target in REPLACED:
        return REPLACED[target]
    prefix, colon, rest = target.partition(":")
    if colon and prefix in WORD_KINDS:
        return f"{WORD_KINDS[prefix]}/{rest}"
    if "/" in target:
        return address_of(target)
    if target in bare:
        return f"{bare[target]}/{target}"
    raise ValueError(f"unknown reference target '{target}'")


def migrate_references(text: str, bare: dict[str, str]) -> str:
    return REFERENCE.sub(lambda match: f"[[{reference_address(match['id'], bare)}|{match['phrase']}]]", text)


HREF = re.compile(r'(href = )"#([^"?]*)(\?[^"]*)?"')
# The crate-local lists an in-page link opened and the kind whose list it is now.
LIST_KINDS = {
    "path": "stations",
    "ledger": "clauses",
    "repositories": "repositories",
    "resources": "resources",
    "tests": "tests",
}
TARGET_KINDS = {"station": "stations", "check": "checks", "page": "pages"}


def migrate_hrefs(text: str, bare: dict[str, str]) -> str:
    """An in-page link names a record by its address and a list by its kind, keeping any topic it narrows to."""

    def replace(match: re.Match[str]) -> str:
        target, query = match[2], match[3] or ""
        if target in LIST_KINDS:
            new = LIST_KINDS[target]
        else:
            prefix, _, identifier = target.partition("-")
            if prefix == "resource":
                new = f"{bare.get(identifier, 'resources')}/{identifier}"
            elif prefix in TARGET_KINDS:
                new = f"{TARGET_KINDS[prefix]}/{identifier}"
            else:
                raise ValueError(f"unknown in-page target '#{target}'")
        return f'{match[1]}"{new}{query}"'

    return HREF.sub(replace, text)


def field_texts(root: Path) -> dict[str, str]:
    """Every prose field the missing-link review hashes, by its review path."""
    content = load_content(root / "content")
    return {
        f"{path}.{key}": value
        for section in REVIEWED_SECTIONS
        for path, key, value in walk(content.get(section, []), section)
        if isinstance(value, str)
    }


def migrate_reviews(text: str, before: dict[str, str], after: dict[str, str]) -> str:
    """Name each reviewed target by address; a decision current before the migration follows its field's text."""
    blocks = re.split(r"(?m)(?=^\[\[review\]\]\s*$)", text)
    for index, block in enumerate(blocks):
        path = re.search(r'(?m)^path = ("(?:[^"\\]|\\.)*")$', block)
        if not path:
            continue
        field = json.loads(path[1])
        migrated = re.sub(
            r'(?m)^address = ("(?:[^"\\]|\\.)*")$',
            lambda match: f"address = {json.dumps(address_of(json.loads(match[1])))}",
            block,
        )
        digest = re.search(r'(?m)^sha256 = "([0-9a-f]{64})"$', migrated)
        old, new = before.get(field), after.get(field)
        current = digest and old is not None and hashlib.sha256(old.encode("utf-8")).hexdigest() == digest[1]
        if current and new is not None and old != new:
            migrated = migrated.replace(digest[1], hashlib.sha256(new.encode("utf-8")).hexdigest())
        blocks[index] = migrated
    return "".join(blocks)


IDS = tomllib.loads((HERE / "ids.toml").read_text(encoding="utf-8"))
ROW = re.compile(r"(?m)(?=^\[\[[A-Za-z][A-Za-z0-9_.-]*\]\]\s*$)")


def reassign(work: Path) -> bool:
    """Give each reviewed snapshot row its new identifier, found by the source's own identifier; True if any changed."""
    changed = False
    for row in IDS.get("reassign", []):
        path = work / row["file"]
        if not path.exists():
            continue  # a content fixture without that snapshot
        blocks = ROW.split(path.read_text(encoding="utf-8"))
        found = 0
        for index, block in enumerate(blocks):
            parsed = tomllib.loads(block) if block.startswith("[[") else {}
            rows = [item for value in parsed.values() if isinstance(value, list) for item in value]
            if not any(
                {"scheme": row["scheme"], "value": row["value"]} in item.get("alternateIds", []) for item in rows
            ):
                continue
            found += 1
            new = re.sub(r'(?m)^id = "[^"]*"$', f"id = {json.dumps(row['id'])}", block, count=1)
            changed |= new != block
            blocks[index] = new
        if found != 1:
            raise ValueError(f"{row['file']}: {found} rows carry {row['scheme']} {row['value']}; expected one")
        path.write_text("".join(blocks), encoding="utf-8", newline="\n")
    return changed


def rename(work: Path) -> None:
    """Rename the quoted entry names of reassigned records together, so names that swap are renamed once."""
    by_file: dict[str, dict[str, str]] = {}
    for row in IDS.get("rename", []):
        by_file.setdefault(row["file"], {})[json.dumps(row["old"])] = json.dumps(row["new"])
    for name, names in by_file.items():
        path = work / name
        pattern = re.compile("|".join(re.escape(old) for old in sorted(names, key=len, reverse=True)))
        path.write_text(
            pattern.sub(lambda match, names=names: names[match[0]], path.read_text(encoding="utf-8")), encoding="utf-8"
        )


STATEMENTS = tomllib.loads((HERE / "statements.toml").read_text(encoding="utf-8"))
ITEM = re.compile(r"(?m)(?=^\[\[item\]\]\s*$)")
STATEMENT_LINE = re.compile(r"(?m)^statement = \{[^\n]*\}\n")


def inline_text(value: dict[str, str]) -> str:
    """A bilingual text as the content writes it, on one line."""
    return "{ " + ", ".join(f"{lang} = {json.dumps(value[lang], ensure_ascii=False)}" for lang in ("cs", "en")) + " }"


def merge_statements(work: Path) -> None:
    """A question that copies a clause it cites takes that clause's text instead: one that copies its requirement
    drops its copy, and one that copies a clause among its sources (``statements.toml``) names it as its requirement
    first. A clause takes the references a question's copy carried where the table says so."""
    reviewed = {row["question"]: row for row in STATEMENTS.get("requirement", [])}
    ledger_path = work / "content" / "ledger.toml"
    if not ledger_path.exists():
        return
    ledger = ledger_path.read_text(encoding="utf-8")
    for row in reviewed.values():
        if "clauseText" not in row:
            continue
        blocks = ROW.split(ledger)
        for index, block in enumerate(blocks):
            if block.startswith("[[clause]]") and tomllib.loads(block)["clause"][0]["id"] == row["clause"]:
                blocks[index] = re.sub(
                    r"(?m)^text = \{[^\n]*\}$",
                    lambda _match, row=row: "text = " + inline_text(row["clauseText"]),
                    block,
                    count=1,
                )
        ledger = "".join(blocks)
    tomllib.loads(ledger)
    ledger_path.write_text(ledger, encoding="utf-8", newline="\n")
    clauses = {clause["id"]: clause for clause in tomllib.loads(ledger).get("clause", [])}
    for path in sorted((work / "content" / "checks").glob("*.toml")):
        blocks = ITEM.split(path.read_text(encoding="utf-8"))
        for index, original in enumerate(blocks):
            if not original.startswith("[[item]]"):
                continue
            block = original
            item = tomllib.loads(block)["item"][0]
            # A reviewed entry applies where its clause exists; a content fixture may hold neither.
            row = reviewed.get(item.get("id")) if reviewed.get(item.get("id"), {}).get("clause") in clauses else None
            if row and "requirement" not in item:
                anchor = re.search(r"(?m)^principles = [^\n]*\n", block) or re.search(r"(?m)^id = [^\n]*\n", block)
                block = block[: anchor.end()] + f"requirement = {json.dumps(row['clause'])}\n" + block[anchor.end() :]
                item["requirement"] = row["clause"]
            if item.get("statement") and item.get("requirement"):
                copied = copied_clause(dict(item, sources=[]), clauses)
                if row or (copied and copied[1] == list(LANGS)):
                    block = STATEMENT_LINE.sub("", block, count=1)
            blocks[index] = block
        text = "".join(blocks)
        tomllib.loads(text)  # the result stays valid TOML
        path.write_text(text, encoding="utf-8", newline="\n")


PAGE = re.compile(r"(?m)(?=^\[\[page\]\]\s*$)")
SECTION = re.compile(r"(?m)(?=^\[\[page\.section\]\]\s*$)")


def name_sections(work: Path) -> None:
    """Give each page section without an id its reviewed one (``[[section]]`` in ``ids.toml``), found by its page, its
    position and its English heading (none for a section without a heading); a section that has an id keeps it."""
    path = work / "content" / "pages.toml"
    if not path.exists():
        return
    reviewed = {(row["page"], row["position"]): row for row in IDS.get("section", [])}
    pages = PAGE.split(path.read_text(encoding="utf-8"))
    for index, page in enumerate(pages):
        if not page.startswith("[[page]]"):
            continue
        parts = SECTION.split(page)
        page_id = tomllib.loads(parts[0])["page"][0]["id"]
        for position, block in enumerate(parts[1:], start=1):
            section = tomllib.loads(block)["page"]["section"][0]
            if "id" in section:
                continue
            row = reviewed.get((page_id, position))
            if row is None or row.get("heading", "") != (section.get("heading") or {}).get("en", ""):
                raise ValueError(f"pages.toml: section {position} of '{page_id}' has no id and no reviewed one")
            named = f"[[page.section]]\nid = {json.dumps(row['id'])}\n"
            parts[position] = block.replace("[[page.section]]\n", named, 1)
        pages[index] = "".join(parts)
    text = "".join(pages)
    tomllib.loads(text)  # the result stays valid TOML
    path.write_text(text, encoding="utf-8", newline="\n")


RESULTS = re.compile(r"(?ms)^results = \[(?P<body>[^\]]*)\]$")
# The family words of the content IDs that provenance results used, before an item's own ID.
FAMILIES = (
    "callout:",
    "callout.",
    "test:",
    "provider:",
    "organization:",
    "model:",
    "layer.",
    "seam.",
    "example.",
    "context:",
    "lifecycle:",
    "crosswalk:",
    "infrastructure:",
    "node:",
    "page:",
    "term:",
    "action:",
    "knav.",
)


# The register's old categories whose values are content IDs, which the content's own map names by address; an
# earlier run of this step named the first three by their kind word already.
CONTENT_ID_CATEGORIES = {
    "requirements",
    "clauses",
    "model",
    "models",
    "lifecycle",
    "lifecycles",
    "sources",
    "resources",
}


def within_check(prefix: str):
    """A check's mode or profile (`dataset.before`) as the term of that check's vocabulary (`modes-dataset/before`)."""
    return lambda value: ("vocabularies", "{}-{}/{}".format(prefix, *value.split(".", 1)))


# The register's other old categories, each with the kind and the address without the kind its entries take.
REGISTER_RULES = {
    "lenses": lambda value: ("vocabularies", f"lenses/{value}"),
    "modes": within_check("modes"),
    "profiles": within_check("profiles"),
    "callouts": lambda value: ("callouts", value.removeprefix("callout:")),
    "callout_items": lambda value: ("callouts", "{}#{}".format(*value.removeprefix("callout.").split(".", 1))),
    "tests": lambda value: ("tests", value if "/" in value else f"guide/{value}"),
    "requirements": lambda value: ("clauses", value),
}


def register_entry(category: str, value: str, addresses: dict[str, str]) -> tuple[str, str]:
    """An old register entry as the kind of its record and its address without the kind. An entry this step keyed
    already, and a kind of the vocabulary whose entries need no change (stations, advice, actions), stay as they are."""
    if category in KINDS and f"{category}/{value}" in addresses.values():
        return category, value
    if category in CONTENT_ID_CATEGORIES and value in addresses:
        kind, identifier = addresses[value].split("/", 1)
        return kind, identifier
    if category in CONTENT_ID_CATEGORIES - {"requirements", "clauses"}:
        raise ValueError(f"register entry {category}:{value} names no record")
    rule = REGISTER_RULES.get(category)
    return rule(value) if rule else (category, value)


def rekey_register(text: str, content: dict) -> str:
    """Key every issued and retired identifier by the kind of its record, with its address without the kind as the
    value, keeping the register's order within each kind."""
    data = tomllib.loads(text)
    addresses = content_addresses(content)
    sections: dict[str, dict[str, list[str]]] = {}
    for section in ("issued", "retired"):
        rekeyed: dict[str, list[str]] = {}
        for category, values in data.get(section, {}).items():
            for value in values:
                kind, identifier = register_entry(category, value, addresses)
                if identifier not in rekeyed.setdefault(kind, []):
                    rekeyed[kind].append(identifier)
        sections[section] = rekeyed
    return register_ids.render(data["register"]["prepared"], sections["issued"], sections["retired"])


def is_address(pattern: str) -> bool:
    """A result that already names an address or an address prefix (`stations/plan`, `advice/plan.*`)."""
    return "/" in pattern and pattern.split("/", maxsplit=1)[0] in KINDS


def compress(pattern: str, targets: set[str], universe: list[str]) -> list[str]:
    """The fewest address patterns that name exactly `targets` among the published addresses: the old prefix within
    each kind, then a whole kind, then a record's scope or parts, then the addresses themselves."""
    if not pattern.endswith("*"):
        return sorted(targets)
    remaining, chosen = set(targets), []

    def take(candidate: str) -> None:
        members = {address for address in universe if result_covers(candidate, address)}
        # A part of a record the result names, such as an advice item's step, changes with it.
        extra = {address for address in members - targets if address.split("#")[0] not in targets}
        if members and not extra and members & remaining:
            chosen.append(candidate)
            remaining.difference_update(members)

    stem = pattern[:-1]
    for family in FAMILIES:
        stem = stem.removeprefix(family)
    for kind in sorted({address.split("/")[0] for address in targets}):
        take(f"{kind}/{stem}*")
    for kind in sorted({address.split("/")[0] for address in remaining}):
        take(f"{kind}/*")
    for parent in sorted({a.split("#")[0] + "#" if "#" in a else a.rsplit("/", 1)[0] + "/" for a in remaining}):
        take(parent + "*")
    return chosen + sorted(remaining)


def migrate_results(work: Path) -> None:
    """Name every provenance result by address, matching the same published records and parts as before."""
    path = work / "content" / "provenance.toml"
    content = load_content(work / "content")
    graph = Graph()
    build_crate(content, graph)
    base = content["guide"]["guide"]["recordBase"]
    # Once the identities are published, the build's index names each content ID's entities by their IRIs.
    universe = sorted({key.removeprefix(base) for key in graph.entities if key.startswith(base)})

    def translate(pattern: str) -> list[str]:
        if pattern in ("guide", "*") or is_address(pattern):
            return [pattern]
        keys = [key for key in graph.resolve([pattern]) if not key.startswith("#unresolved-")]
        if not keys or any(not key.startswith(base) and key != "./" for key in keys):
            raise ValueError(f"provenance result '{pattern}' names no published item")
        targets = {key.removeprefix(base) for key in keys if key != "./"}
        return (["guide"] if "./" in keys else []) + compress(pattern, targets, universe)

    def replace(match: re.Match[str]) -> str:
        values = json.loads("[" + match["body"].strip().rstrip(",") + "]")
        new = list(dict.fromkeys(value for pattern in values for value in translate(pattern)))
        if "\n" not in match["body"]:
            return f"results = {json.dumps(new, ensure_ascii=False)}"
        return "results = [\n" + "".join(f"  {json.dumps(value, ensure_ascii=False)},\n" for value in new) + "]"

    text = RESULTS.sub(replace, path.read_text(encoding="utf-8"))
    tomllib.loads(text)
    path.write_text(text, encoding="utf-8", newline="\n")


OBJECTS = re.compile(r"(?ms)^objects = \[(?P<body>[^\]]*)\]$")
STEPS = re.compile(r"(?m)^steps = \[(?P<body>[^\]\n]*)\]$")
TARGET = re.compile(r'(?m)^target = (?P<value>"[^"\n]*")$')


def migrate_named_records(work: Path) -> None:
    """Name the records of the fields that can name several kinds by address; an address stays as it is."""
    content = load_content(work / "content")
    addresses = content_addresses(content)

    def address(value: str) -> str:
        if is_address(value):
            return value
        if value not in addresses:
            raise ValueError(f"'{value}' names no record")
        return addresses[value]

    def array(match: re.Match[str], key: str) -> str:
        values = [address(value) for value in json.loads("[" + match["body"].strip().rstrip(",") + "]")]
        if "\n" not in match["body"]:
            return f"{key} = {json.dumps(values, ensure_ascii=False)}"
        return f"{key} = [\n" + "".join(f"  {json.dumps(value, ensure_ascii=False)},\n" for value in values) + "]"

    for name, rewrites in (
        ("provenance.toml", ((OBJECTS, lambda match: array(match, "objects")),)),
        (
            "model.toml",
            (
                (STEPS, lambda match: array(match, "steps")),
                (TARGET, lambda match: f"target = {json.dumps(address(json.loads(match['value'])))}"),
            ),
        ),
    ):
        path = work / "content" / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, replace in rewrites:
            text = pattern.sub(replace, text)
        tomllib.loads(text)
        path.write_text(text, encoding="utf-8", newline="\n")


ROUTE_LINE = re.compile(r'(?m)^guideRoute = ("(?:[^"\\]|\\.)*")$')


def translate_routes(text: str, routes: dict[str, str]) -> str:
    """Rewrite the stored guideRoute values of a TOML text through a reviewed translation, leaving every other byte;
    every resulting route must be a kind of the vocabulary, with its scope where it has one."""

    def replace(match: re.Match[str]) -> str:
        value = json.loads(match[1])
        new = routes.get(value, value)
        parse_route(new)
        return f"guideRoute = {json.dumps(new, ensure_ascii=False)}"

    return ROUTE_LINE.sub(replace, text)


def renormalise_snapshot(text: str, routes: dict[str, str] | None = None) -> str:
    """A recorded snapshot in the current identity format, without a new observation: its rows, source passages and
    retrieval date stay; their identities are revalidated and their stored routes translated and checked."""
    data = tomllib.loads(text)
    for kind in RECORD_KINDS:
        for row in data.get(kind, []):
            validate_identity(row, source_scheme(data, kind))
    return translate_routes(text, routes or {})


def renormalise_snapshots(work: Path) -> None:
    """Renormalise every generated snapshot: its stored routes take the kind vocabulary, and nothing else changes."""
    for path in sorted(generated_files(work)):
        if path.exists():
            text = path.read_text(encoding="utf-8")
            path.write_text(renormalise_snapshot(text, ROUTES), encoding="utf-8", newline="\n")


def run(work: Path) -> None:
    """Apply every step to the content copy under `work`."""
    if reassign(work):
        rename(work)
    renormalise_snapshots(work)
    name_sections(work)
    merge_statements(work)
    before = field_texts(work)
    bare = bare_kinds(work)
    for path in authored_files(work):
        text = path.read_text(encoding="utf-8")
        text = migrate_hrefs(migrate_references(translate_routes(text, ROUTES), bare), bare)
        tomllib.loads(text)  # every result stays valid TOML
        path.write_text(text, encoding="utf-8", newline="\n")
    reviews = work / "content" / "link-reviews.toml"
    if reviews.exists():
        text = migrate_reviews(reviews.read_text(encoding="utf-8"), before, field_texts(work))
        tomllib.loads(text)
        reviews.write_text(text, encoding="utf-8", newline="\n")
    register = work / "content" / "identifiers.toml"
    if register.exists():
        text = rekey_register(register.read_text(encoding="utf-8"), load_content(work / "content"))
        register.write_text(text, encoding="utf-8", newline="\n")
    # Names first: the build that the results step reads resolves those fields by address.
    migrate_named_records(work)
    migrate_results(work)


def copy_checkout(root: Path, work: Path) -> None:
    shutil.copytree(root / "content", work / "content")
    registry = root / ".github" / "source-registry.json"
    if registry.exists():
        (work / ".github").mkdir()
        shutil.copy2(registry, work / ".github" / "source-registry.json")


def migrate(root: Path, dry_run: bool) -> list[str]:
    """Migrate a copy, then write back what changed; return the unified diff."""
    diff: list[str] = []
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        copy_checkout(root, work)
        run(work)
        for path in sorted((root / "content").rglob("*.toml")):
            relative = path.relative_to(root)
            before, after = path.read_text(encoding="utf-8"), (work / relative).read_text(encoding="utf-8")
            if before == after:
                continue
            name = relative.as_posix()
            diff.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True), name, name))
            if not dry_run:
                path.write_text(after, encoding="utf-8", newline="\n")
    return diff


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print the diff and write nothing")
    parser.add_argument("--root", type=Path, default=ROOT, help="checkout to migrate (default: this one)")
    args = parser.parse_args(argv)
    diff = migrate(args.root.resolve(), args.dry_run)
    if args.dry_run:
        sys.stdout.writelines(diff)
    files = sum(line.startswith("+++ ") for line in diff)
    print(f"migrate: {files} file(s) {'would change' if args.dry_run else 'changed'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
