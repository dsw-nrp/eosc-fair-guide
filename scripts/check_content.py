#!/usr/bin/env python3
"""Check the guide's content contract on the TOML sources.

Covers the rules the SHACL profile in ``profile/`` cannot express: unknown or inconsistent references, lossless
coverage of the FAIR analysis, one next action per station and lens, link and text safety, connector-only URLs
in the page scripts, and provenance coverage. With ``--base <git ref>``, every item changed since that revision
must be covered by a provenance action that ended after it.

Exit status: 0 when the contract holds, 1 when it does not, 2 when the content cannot be read. Uses only the
Python standard library. The rules are documented in ``docs/content-model.md``.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_crate import (  # noqa: E402
    BLOCK,
    PAGE_FILE,
    REFERENCE,
    ROOT,
    SOURCE_TYPES,
    ContentError,
    Graph,
    build_crate,
    is_generated,
    load_content,
)

LANGS = ("cs", "en")
LEVELS = ("L0", "L1", "L2")
CLAUSE_KINDS = ("requirement", "recommendation", "fulfilment", "statement")
CLAUSE_STATUSES = ("current", "refresh", "superseded")
HEALTH = ("available", "degraded", "unavailable")
PREFILL_SOURCES = ("datacite", "nkr", "champion", "fip", "resolver", "re3data")
ACTION_TYPES = ("create", "update")
RELEASE_STATUSES = ("testing", "released")
CHECK_PREFIXES = {
    "dataset": ("D", "P", "O"),
    "gate": ("G",),
    "maturity": ("S",),
    "fip": ("K",),
    "institution": ("I",),
    "coretrustseal": ("C",),
    "cdif": ("M",),
}
GATE_TIERS = ("required", "recommended")
MATURITY_TIERS = ("minimum", "recommended", "advanced")
# Checks built on a standard's requirements start with what the standard requires.
TIERS = {"gate": GATE_TIERS, "coretrustseal": ("standard",), "cdif": ("standard", "recommended", "advanced")}
FORBIDDEN_KEYS = ("score", "percentage", "points")
NOT_RENDERED = ("live.nanopub.query",)

# FAIR-enabling resource classes of the FIP ontology (https://w3id.org/fair/fip/terms/), as published.
FIP_CLASSES = (
    "Authentication-and-authorization-service",
    "Communication-protocol",
    "Crosswalk",
    "Data-usage-license",
    "Domain-Specific-Registry",
    "FAIR-Data-Policy",
    "FAIR-Data-Stewardship-Plan-Template",
    "FAIR-Assessment-Specification",
    "FAIR-Supporting-Software",
    "FAIR-Training-Material",
    "Generalist-Registry",
    "Identifier-service",
    "Knowledge-representation-language",
    "Metadata-data-linking-schema",
    "Metadata-preservation-policy",
    "Metadata-schema",
    "Persistency-Policy",
    "Provenance-Tracking-Service",
    "Provenance-model",
    "Registry",
    "Semantic-model",
    "Structured-vocabulary",
    "Validation-Service",
    "Web-API",
)
FIP_QUESTIONS = (
    "F1-D",
    "F1-MD",
    "F2",
    "F3",
    "F4-D",
    "F4-MD",
    "A1.1-D",
    "A1.1-MD",
    "A1.2-D",
    "A1.2-MD",
    "A2",
    "I1-D",
    "I1-MD",
    "I2-D",
    "I2-MD",
    "I3-D",
    "I3-MD",
    "R1.1-D",
    "R1.1-MD",
    "R1.2-D",
    "R1.2-MD",
)

PRINCIPLE = r"(?:F[1-4]|A1(?:\.[12])?|A2|I[1-3]|R1(?:\.[1-3])?)"
ANALYSIS_CLAUSE = re.compile(rf"^A\.(?P<principle>{PRINCIPLE})\.(?P<kind>[NRFX])(?P<number>\d+)$")
CLAUSE_ID = re.compile(
    r"^(A\.[A-Z0-9.]+|K\d[\w.]*|P\d+|S\.(?:MIN|REC)\d+|C\.[A-Z][\w.]*|CTS\.R\d+|CDIF\.[\w.-]+|DOC\.[\w.-]+|E\.[\w.-]+|G)$"
)
ADVICE_ID = re.compile(r"^(?P<station>[a-z0-9-]+)\.(?P<lens>[A-Z]+|all)\.(?P<level>L[0-2])(?:\.\d+)?$")
RAW_HTML = re.compile(r"<\s*[a-zA-Z/!]")
# Letters that mark a name as Czech; a plain name with one of them has no English form.
CZECH_LETTERS = re.compile(r"[ěščřžůťďňáéíóúý]", re.IGNORECASE)
URL_LITERAL = re.compile(r"https?://[^\s\"'`)<>\]]+")
LETTER_KIND = {"N": ("nrp", "requirement"), "R": ("repository", "requirement"), "F": ("fip", "requirement")}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    def warn(self, where: str, message: str) -> None:
        self.warnings.append(f"{where}: {message}")


# ---------------------------------------------------------------------------
# Helpers


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def walk(value: Any, path: str = "") -> Iterator[tuple[str, str, Any]]:
    """Yield (path, key, value) for every value in a nested structure."""
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            yield path, str(key), item
            yield from walk(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, f"{path}[{item_label(item, index)}]")


def item_label(item: Any, index: int) -> str:
    """Label a list item by its ID, so messages name the item rather than its position."""
    if isinstance(item, dict):
        if isinstance(item.get("id"), str):
            return item["id"]
        for value in item.values():
            if isinstance(value, dict) and isinstance(value.get("id"), str):
                return value["id"]
    return str(index)


def is_text(value: Any) -> bool:
    return isinstance(value, dict) and set(value) <= set(LANGS) and bool(value)


def require_text(report: Report, where: str, value: Any, field: str, proper_name_allowed: bool = False) -> None:
    if value is None:
        report.error(where, f"missing {field}")
    elif isinstance(value, str):
        if not proper_name_allowed:
            report.error(where, f"{field} must have Czech and English values")
    elif not is_text(value):
        report.error(where, f"{field} must be a table with 'cs' and 'en'")


def unique(report: Report, where: str, ids: list[str], what: str) -> None:
    seen: set[str] = set()
    for item_id in ids:
        if item_id in seen:
            report.error(where, f"duplicate {what} ID '{item_id}'")
        seen.add(item_id)


def to_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    return None


# ---------------------------------------------------------------------------
# Rules


def check_texts(report: Report, content: dict[str, Any]) -> None:
    """Every bilingual table has both languages; no raw HTML or script URLs anywhere."""
    for name, data in content.items():
        for path, key, value in walk(data, name):
            where = f"{path}.{key}" if path else key
            if isinstance(value, dict) and value and set(value) <= set(LANGS):
                for lang in LANGS:
                    if not str(value.get(lang, "")).strip():
                        report.error(where, f"missing {'Czech' if lang == 'cs' else 'English'} text")
            if isinstance(value, str):
                # The nanopublication query is sent to the query service and never shown; SPARQL writes IRIs in <>.
                if RAW_HTML.search(value) and where not in NOT_RENDERED:
                    report.error(where, "contains raw HTML; use plain text")
                if "javascript:" in value.lower():
                    report.error(where, "contains a javascript: URL")
            if key.lower() in FORBIDDEN_KEYS:
                report.error(where, "the guide shows no scores or percentages")


def check_links(report: Report, content: dict[str, Any], targets: set[str]) -> None:
    for name, data in content.items():
        for path, key, value in walk(data, name):
            where = f"{path}.{key}"
            if not isinstance(value, str):
                continue
            if key == "url" and not (value.startswith("https://") or value.startswith("mailto:")):
                report.error(where, f"link must use HTTPS: {value}")
            elif key == "href":
                if value.startswith("#"):
                    if value not in targets:
                        report.error(where, f"in-page target '{value}' does not exist")
                elif not value.startswith("https://"):
                    report.error(where, f"link must use HTTPS or an in-page target: {value}")
            elif key in ("origin", "endpoint") and not value.startswith("https://"):
                report.error(where, f"{key} must use HTTPS: {value}")
        for path, key, value in walk(data, name):
            if key == "sameAs":
                for iri in as_list(value):
                    if not re.match(r"^https?://", str(iri)):
                        report.error(f"{path}.sameAs", f"not an IRI: {iri}")


def check_ledger(report: Report, content: dict[str, Any], vocab: dict[str, set[str]]) -> set[str]:
    clauses = content["ledger"]
    ids = [clause.get("id", "") for clause in clauses]
    unique(report, "ledger", ids, "clause")
    source_ids = cited_ids(content)
    clause_ids = set(ids)
    for clause in clauses:
        where = f"ledger:{clause.get('id')}"
        if not CLAUSE_ID.match(clause.get("id", "")):
            report.error(where, "ID does not follow the ledger prefixes")
        if clause.get("source") not in source_ids:
            report.error(where, f"unknown source '{clause.get('source')}'")
        for principle in clause.get("principles", []):
            if principle not in vocab["principles"]:
                report.error(where, f"unknown principle '{principle}'")
        if clause.get("actor") not in vocab["clause_actors"]:
            report.error(where, f"unknown actor '{clause.get('actor')}'")
        if clause.get("kind") not in CLAUSE_KINDS:
            report.error(where, f"kind must be one of {', '.join(CLAUSE_KINDS)}")
        if clause.get("status", "current") not in CLAUSE_STATUSES:
            report.error(where, f"status must be one of {', '.join(CLAUSE_STATUSES)}")
        if clause.get("status") == "refresh" and not clause.get("note"):
            report.error(where, "a clause marked for refresh needs a note saying what changed")
        for note_source in clause.get("noteSources", []):
            if note_source not in clause_ids | source_ids:
                report.error(where, f"noteSources names an unknown clause or source '{note_source}'")
        superseded_by = clause.get("supersededBy")
        if superseded_by and superseded_by not in clause_ids | source_ids:
            report.error(where, f"supersededBy names an unknown clause or source '{superseded_by}'")
        require_text(report, where, clause.get("text"), "text")
        if "title" in clause:
            require_text(report, where, clause["title"], "title")
        if "guidance" in clause and not (isinstance(clause["guidance"], str) and clause["guidance"].strip()):
            report.error(where, "guidance is the source's own text, in English as published")
        match = ANALYSIS_CLAUSE.match(clause.get("id", ""))
        if match:
            # Lossless coverage: an analysis clause is reachable in the explorer under its own principle.
            if match["principle"] not in clause.get("principles", []):
                report.error(
                    where, f"not listed under its principle {match['principle']}, so the explorer would miss it"
                )
            letter = match["kind"]
            if letter in LETTER_KIND:
                actor, kind = LETTER_KIND[letter]
                if clause.get("actor") != actor or clause.get("kind") != kind:
                    report.error(where, f"'{letter}' clauses are {kind}s addressed to '{actor}'")
            elif clause.get("kind") not in ("fulfilment", "statement"):
                report.error(
                    where, "'X' clauses state fulfilment in NRP or a CoreTrustSeal/CDIF link, not a requirement"
                )
    return clause_ids


def cited_ids(content: dict[str, Any]) -> set[str]:
    """What a clause can cite: a source, or a resource that carries its citation."""
    return {source["id"] for source in content["sources"]} | {
        resource["id"] for resource in content["resources"] if resource.get("citation")
    }


def check_citation(report: Report, where: str, citation: dict[str, Any], own_url: bool) -> None:
    """How a cited work is cited: a title, a known type, an address or DOI, and a date."""
    if not citation.get("title"):
        report.error(where, "missing title")
    if citation.get("type") not in SOURCE_TYPES:
        report.error(where, f"type must be one of {', '.join(SOURCE_TYPES)}")
    if not (own_url or citation.get("url") or citation.get("doi")):
        report.error(where, "a source needs a URL or a DOI")
    if not (citation.get("datePublished") or citation.get("dateAccessed")):
        report.error(where, "a source needs datePublished or dateAccessed")


def check_sources(report: Report, content: dict[str, Any]) -> None:
    unique(report, "sources", [source.get("id", "") for source in content["sources"]], "source")
    for source in content["sources"]:
        check_citation(report, f"sources:{source.get('id')}", source, own_url=False)
        if "short" in source:
            require_text(report, f"sources:{source.get('id')}", source["short"], "short", proper_name_allowed=True)


def check_stations(report: Report, content: dict[str, Any], vocab: dict[str, set[str]], clause_ids: set[str]) -> None:
    stations = [data["station"] for data in content["stations"]]
    unique(report, "stations", [station["id"] for station in stations], "station")
    unique(report, "stations", [str(station["position"]) for station in stations], "station position")
    advice_ids: list[str] = []
    for data in content["stations"]:
        station = data["station"]
        where = f"station:{station['id']}"
        require_text(report, where, station.get("name"), "name")
        require_text(report, where, station.get("title"), "title")
        for principle in station.get("principles", []):
            if principle not in vocab["principles"]:
                report.error(where, f"unknown principle '{principle}'")
        for term in station.get("glossary", []):
            if term not in vocab["terms"]:
                report.error(where, f"unknown glossary term '{term}'")
        l0_by_lens: dict[str, int] = {lens: 0 for lens in vocab["lenses"]}
        for advice in data.get("advice", []):
            advice_id = advice.get("id", "")
            advice_ids.append(advice_id)
            item = f"advice:{advice_id}"
            match = ADVICE_ID.match(advice_id)
            lenses = sorted(vocab["lenses"]) if advice.get("lens") == "*" else as_list(advice.get("lens"))
            if not match:
                report.error(item, "ID must be <station>.<lens|all>.<level>[.<n>]")
            else:
                if match["station"] != station["id"]:
                    report.error(item, f"ID names station '{match['station']}' but the item is in '{station['id']}'")
                if match["level"] != advice.get("level"):
                    report.error(item, f"ID names level {match['level']} but the item has level {advice.get('level')}")
                expected_lens = "all" if len(lenses) != 1 else lenses[0]
                if match["lens"] != expected_lens:
                    report.error(item, f"ID names lens '{match['lens']}' but the item is for {', '.join(lenses)}")
            for lens in lenses:
                if lens not in vocab["lenses"]:
                    report.error(item, f"unknown lens '{lens}'")
            if advice.get("level") not in LEVELS:
                report.error(item, f"level must be one of {', '.join(LEVELS)}; L3 is generated")
            require_text(report, item, advice.get("text"), "text")
            if not advice.get("sources"):
                report.error(item, "cites no ledger clause")
            for source in advice.get("sources", []):
                if source not in clause_ids:
                    report.error(item, f"cites unknown clause '{source}'")
            if advice.get("kind") not in (None, "ai"):
                report.error(item, "kind must be 'ai' or omitted")
            if advice.get("kind") == "ai":
                # An AI tip says what to check afterwards and gives a prompt to copy.
                require_text(report, item, advice.get("check"), "check")
                require_text(report, item, advice.get("prompt"), "prompt")
            elif "check" in advice or "prompt" in advice:
                report.error(item, "only an AI item carries check and prompt")
            if advice.get("level") == "L0" and advice.get("kind") != "ai":
                if not advice.get("action"):
                    report.error(item, "an L0 item needs one concrete action")
                for lens in lenses:
                    if lens in l0_by_lens:
                        l0_by_lens[lens] += 1
            if advice.get("action") and advice.get("level") != "L0":
                report.error(item, "only L0 items carry an action")
            for step in advice.get("steps", []):
                require_text(report, item, step, "step")
        for lens, count in l0_by_lens.items():
            if count != 1:
                report.error(where, f"lens {lens} needs exactly one L0 item with its next action (found {count})")
    unique(report, "advice", advice_ids, "advice")


def check_checks(report: Report, content: dict[str, Any], vocab: dict[str, set[str]], clause_ids: set[str]) -> None:
    item_ids: list[str] = []
    check_ids = [data["check"]["id"] for data in content["checks"]]
    unique(report, "checks", check_ids, "check")
    for data in content["checks"]:
        check = data["check"]
        where = f"check:{check['id']}"
        if check["id"] not in CHECK_PREFIXES:
            report.error(where, f"check ID must be one of {', '.join(CHECK_PREFIXES)}")
            continue
        require_text(report, where, check.get("name"), "name")
        for lens in check.get("lenses", []):
            if lens not in vocab["lenses"]:
                report.error(where, f"unknown lens '{lens}'")
        profiles = {profile["id"] for profile in check.get("profile", [])}
        if check.get("defaultProfile") is not None and check["defaultProfile"] not in profiles:
            report.error(where, f"defaultProfile must be one of {', '.join(sorted(profiles)) or 'its profiles'}")
        modes = set(check.get("modes", []))
        tiers = TIERS.get(check["id"], MATURITY_TIERS)
        # A check either has no blocks, or every item belongs to one of its blocks.
        blocks = [block.get("id", "") for block in data.get("block", [])]
        unique(report, where, blocks, "block")
        for block in data.get("block", []):
            require_text(report, f"{where}.block:{block.get('id')}", block.get("name"), "name")
        for item in data.get("item", []):
            item_id = item.get("id", "")
            item_ids.append(item_id)
            here = f"item:{item_id}"
            if blocks and item.get("block") not in blocks:
                report.error(here, f"block must be one of {', '.join(blocks)}")
            if not blocks and item.get("block") is not None:
                report.error(here, "the check declares no blocks")
            if not item_id.startswith(CHECK_PREFIXES[check["id"]]):
                report.error(
                    here, f"items of the {check['id']} check start with {' or '.join(CHECK_PREFIXES[check['id']])}"
                )
            if item.get("prefillLevel") not in (None, "partly"):
                report.error(here, "prefillLevel can only be 'partly'")
            if item.get("tier") not in tiers:
                report.error(here, f"tier must be one of {', '.join(tiers)}")
            if "requirement" in item and item["requirement"] not in clause_ids:
                report.error(here, f"requirement names unknown clause '{item['requirement']}'")
            require_text(report, here, item.get("statement"), "statement")
            if item.get("help") is not None:
                require_text(report, here, item.get("help"), "help")
            for principle in item.get("principles", []):
                if principle not in vocab["principles"]:
                    report.error(here, f"unknown principle '{principle}'")
            if not item.get("sources"):
                report.error(here, "cites no ledger clause")
            for source in item.get("sources", []):
                if source not in clause_ids:
                    report.error(here, f"cites unknown clause '{source}'")
            if item.get("fixAt") and item["fixAt"] not in vocab["stations"]:
                report.error(here, f"fixAt names unknown station '{item['fixAt']}'")
            if not item.get("owner"):
                report.error(here, "names nobody who can fix a gap")
            for owner in item.get("owner", []):
                if owner not in vocab["owner_actors"]:
                    report.error(here, f"unknown owner '{owner}'")
            for profile in item.get("profiles", []) + item.get("providedByNrp", []):
                if profile not in profiles:
                    report.error(here, f"unknown profile '{profile}'")
            for mode in item.get("modes", []):
                if mode not in modes:
                    report.error(here, f"unknown mode '{mode}'")
            check_item_answers(report, here, item, content["live"].get("links", {}), vocab)
    unique(report, "checks", item_ids, "check item")


def check_item_answers(
    report: Report, here: str, item: dict[str, Any], links: dict[str, str], vocab: dict[str, set[str]]
) -> None:
    """Where an item's answer can come from: the pre-fill sources and the lookup link for a "don't know" task."""
    if item.get("lookup") is not None and item["lookup"] not in links:
        report.error(here, f"lookup names unknown link '{item['lookup']}'; add it to [links] in live.toml")
    for source, value in item.get("prefill", {}).items():
        if source not in PREFILL_SOURCES:
            report.error(here, f"unknown pre-fill source '{source}'")
        if source == "champion":
            for test in as_list(value):
                if test not in vocab["tests"]:
                    report.error(here, f"pre-fill names a test outside the curated set: '{test}'")
        if source == "fip":
            for question in as_list(value):
                if question not in FIP_QUESTIONS:
                    report.error(here, f"unknown FIP question '{question}'")


def check_resources(report: Report, content: dict[str, Any], vocab: dict[str, set[str]], today: date) -> None:
    unique(report, "resources", [resource.get("id", "") for resource in content["resources"]], "resource")
    for resource in content["resources"]:
        where = f"resource:{resource.get('id')}"
        require_text(report, where, resource.get("name"), "name", proper_name_allowed=True)
        if resource.get("description") is not None:
            require_text(report, where, resource.get("description"), "description")
        if resource.get("type") not in vocab["resource_types"]:
            report.error(where, f"unknown type '{resource.get('type')}'")
        if not resource.get("url"):
            report.error(where, "missing url")
        check_status(report, where, resource, vocab, today)
        lenses = vocab["lenses"] if resource.get("lenses", "*") == "*" else set(as_list(resource.get("lenses")))
        for lens in lenses:
            if lens not in vocab["lenses"]:
                report.error(where, f"unknown lens '{lens}'")
        for station in resource.get("stations", []):
            if station not in vocab["stations"]:
                report.error(where, f"unknown station '{station}'")
        for fip_class in resource.get("fipClass", []):
            if fip_class not in FIP_CLASSES:
                report.error(where, f"unknown FIP class '{fip_class}'")
        dashboard_id = resource.get("fipDashboard")
        if dashboard_id is not None and not re.match(r"^[a-z0-9][a-z0-9-]*$", str(dashboard_id)):
            report.error(where, f"fipDashboard must be a FIP Dashboard resource ID: {dashboard_id}")
        if resource.get("citation") is not None:
            if "id" in resource["citation"] or "url" in resource["citation"]:
                report.error(f"{where}:citation", "a citation takes its ID and address from the resource")
            check_citation(report, f"{where}:citation", resource["citation"], own_url=True)
        if resource.get("repository") is not None:
            if resource.get("type") != "repository":
                report.error(f"{where}:repository", "only a resource of type 'repository' carries repository facts")
            if resource["repository"].get("kind") not in vocab["repository_kinds"]:
                report.error(f"{where}:repository", f"unknown kind '{resource['repository'].get('kind')}'")


def check_status(report: Report, where: str, entry: dict[str, Any], vocab: dict[str, set[str]], today: date) -> None:
    status = entry.get("status")
    if status is None:
        report.error(where, "missing status")
        return
    if status not in vocab["statuses"]:
        report.error(where, f"unknown status '{status}'")
    as_of = entry.get("asOf")
    if not isinstance(as_of, date):
        report.error(where, "a status needs an as-of date (asOf = YYYY-MM-DD)")
    elif today - as_of > timedelta(days=vocab["freshness_days"]):
        report.warn(where, f"status last verified on {as_of.isoformat()}, older than {vocab['freshness_days']} days")


def check_repositories(report: Report, content: dict[str, Any], vocab: dict[str, set[str]], today: date) -> None:
    unique(report, "repositories", [repository.get("id", "") for repository in content["repositories"]], "repository")
    for repository in content["repositories"]:
        where = f"repository:{repository.get('id')}"
        if repository.get("kind") not in vocab["repository_kinds"]:
            report.error(where, f"unknown kind '{repository.get('kind')}'")
        check_status(report, where, repository, vocab, today)
    for snapshot in content["snapshots"]:
        info = snapshot.get("snapshot", {})
        where = f"snapshot:{info.get('source')}"
        for field in ("source", "url", "retrieved"):
            if not info.get(field):
                report.error(where, f"missing {field}")
        for repository in snapshot.get("repository", []):
            if repository.get("kind") and repository["kind"] not in vocab["repository_kinds"]:
                report.error(f"{where}:{repository.get('id')}", f"unknown kind '{repository['kind']}'")


VERIFICATION_LEVELS = ("verified", "self-declared", "under-review")
DECLARATION_STATUSES = ("in-use", "planned", "under-consideration", "to-be-replaced")


def check_fip_dashboard(report: Report, content: dict[str, Any], vocab: dict[str, Any]) -> None:
    """The dashboard snapshot is consistent, and every resource that names a dashboard record finds it."""
    snapshot = next((item for item in content["snapshots"] if item.get("fip") or item.get("resource")), None)
    if snapshot is None:
        return
    fers = {resource["id"] for resource in snapshot.get("resource", [])}
    organizations = {organization["id"] for organization in snapshot.get("organization", [])}
    for resource in snapshot.get("resource", []):
        for verification in resource.get("verification", []):
            if verification.get("level") not in VERIFICATION_LEVELS:
                report.error(f"fer:{resource['id']}", f"unknown verification level '{verification.get('level')}'")
            if verification.get("verifier") not in organizations:
                report.error(f"fer:{resource['id']}", f"unknown verifier '{verification.get('verifier')}'")
    for fip in snapshot.get("fip", []):
        for declaration in fip.get("declarations", []):
            where = f"fip:{fip['id']}:{declaration.get('principle')}"
            if declaration.get("principle") not in vocab["principles"]:
                report.error(where, f"unknown principle '{declaration.get('principle')}'")
            if declaration.get("resource") not in fers:
                report.error(where, f"declares unknown resource '{declaration.get('resource')}'")
            if declaration.get("status") not in DECLARATION_STATUSES:
                report.error(where, f"unknown declaration status '{declaration.get('status')}'")
    for resource in content["resources"]:
        if resource.get("fipDashboard") and resource["fipDashboard"] not in fers:
            report.error(f"resource:{resource['id']}", f"FIP Dashboard has no resource '{resource['fipDashboard']}'")


def check_glossary(report: Report, content: dict[str, Any]) -> None:
    glossary = content["glossary"]
    terms = glossary.get("term", [])
    unique(report, "glossary", [term.get("id", "") for term in terms], "term")
    licensed = bool(glossary.get("glossary", {}).get("license"))
    for term in terms:
        where = f"term:{term.get('id')}"
        require_text(report, where, term.get("label"), "label")
        if term.get("definition") is not None and not licensed:
            report.error(where, "definitions may be copied only when the glossary's licence permits it")


def check_callouts(report: Report, content: dict[str, Any], vocab: dict[str, set[str]]) -> None:
    unique(report, "callouts", [callout.get("id", "") for callout in content["callouts"]], "callout")
    for callout in content["callouts"]:
        where = f"callout:{callout.get('id')}"
        require_text(report, where, callout.get("title"), "title")
        item_ids = [item.get("id", "") for item in callout.get("item", [])]
        unique(report, where, item_ids, "callout item")
        for item in callout.get("item", []):
            require_text(report, f"{where}.{item.get('id')}", item.get("text"), "text")
            for lens in as_list(item.get("lenses")):
                if lens not in vocab["lenses"]:
                    report.error(f"{where}.{item.get('id')}", f"unknown lens '{lens}'")
        for station in callout.get("stations", []):
            if station not in vocab["stations"]:
                report.error(where, f"unknown station '{station}'")
        for lens, order in callout.get("order", {}).items():
            if lens not in vocab["lenses"]:
                report.error(where, f"order given for unknown lens '{lens}'")
            if sorted(order) != sorted(item_ids):
                report.error(where, f"the order for lens {lens} must list every item exactly once")


def check_live(report: Report, content: dict[str, Any], vocab: dict[str, set[str]], root: Path) -> None:
    live = content["live"]
    connectors = live.get("connector", [])
    unique(report, "live", [connector.get("id", "") for connector in connectors], "connector")
    origins = set()
    for connector in connectors:
        origin = connector.get("origin", "")
        if not re.match(r"^https://[a-z0-9.-]+(:\d+)?$", origin):
            report.error(f"connector:{connector.get('id')}", f"origin must be 'https://host' without a path: {origin}")
        origins.add(origin)
    champion = live.get("champion", {})
    if champion:
        endpoint_origin = re.match(r"^(https://[^/]+)", champion.get("endpoint", ""))
        if not endpoint_origin or endpoint_origin.group(1) not in origins:
            report.error("champion", "the endpoint's host is not a connector")
        if not 1 <= int(champion.get("maxParallel", 0)) <= 4:
            report.error("champion", "maxParallel must be between 1 and 4")
        if not 1 <= int(champion.get("timeoutSeconds", 0)) <= 60:
            report.error("champion", "timeoutSeconds must be between 1 and 60")
    for test in champion.get("test", []):
        where = f"test:{test.get('id')}"
        if test.get("principle") not in vocab["principles"]:
            report.error(where, f"unknown principle '{test.get('principle')}'")
        if test.get("health") is not None:
            if test["health"] not in HEALTH:
                report.error(where, f"health must be one of {', '.join(HEALTH)}")
            if not isinstance(test.get("asOf"), date):
                report.error(where, "health needs an as-of date")
    for script in sorted((root / "assets" / "js").glob("*.js")):
        for number, line in enumerate(script.read_text(encoding="utf-8").splitlines(), start=1):
            for url in URL_LITERAL.findall(line):
                origin = re.match(r"^(https?://[^/]+)", url)
                if not origin or origin.group(1) not in origins:
                    report.error(f"{script.relative_to(root)}:{number}", f"URL outside the connector allowlist: {url}")


def content_index(content: dict[str, Any]) -> dict[str, str]:
    """Map content IDs that provenance actions can name to their kind."""
    index: dict[str, str] = {}
    for clause in content["ledger"]:
        index[clause["id"]] = "clause"
    for source in content["sources"]:
        index.setdefault(source["id"], "source")
    for data in content["stations"]:
        index.setdefault(data["station"]["id"], "station")
        for advice in data.get("advice", []):
            index[advice["id"]] = "advice"
    for data in content["checks"]:
        for item in data.get("item", []):
            index[item["id"]] = "item"
    for resource in content["resources"]:
        index.setdefault(resource["id"], "resource")
    for repository in content["repositories"]:
        index.setdefault(repository["id"], "repository")
    return index


def covered(pattern: str, item_id: str) -> bool:
    return item_id.startswith(pattern[:-1]) if pattern.endswith("*") else item_id == pattern


def check_provenance(report: Report, content: dict[str, Any], vocab: dict[str, set[str]]) -> None:
    actions = content["provenance"]
    unique(report, "provenance", [action.get("id", "") for action in actions], "action")
    index = content_index(content)
    cited = cited_ids(content)
    for action in actions:
        where = f"action:{action.get('id')}"
        if action.get("type") not in ACTION_TYPES:
            report.error(where, f"type must be one of {', '.join(ACTION_TYPES)}")
        if action.get("agent") not in vocab["people"]:
            report.error(where, f"unknown agent '{action.get('agent')}'")
        if not action.get("instruments"):
            report.error(where, "names no instrument")
        for instrument in action.get("instruments", []):
            if instrument not in vocab["instruments"]:
                report.error(where, f"unknown instrument '{instrument}'")
        for obj in action.get("objects", []):
            if index.get(obj) != "clause" and obj not in cited:
                report.error(where, f"object '{obj}' is not a clause or source")
        for pattern in action.get("results", []):
            if not any(covered(pattern, item_id) for item_id in index):
                report.error(where, f"result '{pattern}' matches no item")
        end_time = action.get("endTime")
        if not isinstance(end_time, datetime) or end_time.tzinfo is None:
            report.error(where, "endTime must be a date-time with a time zone")
    patterns = [pattern for action in actions for pattern in action.get("results", [])]
    for item_id, kind in index.items():
        if kind in ("advice", "item", "resource", "clause") and not any(covered(p, item_id) for p in patterns):
            report.error(f"{kind}:{item_id}", "no provenance action covers this item")


def bare_url(url: Any) -> str:
    """An address without its scheme, "www." and trailing slashes, for telling whether two entries name one thing."""
    return re.sub(r"^https?://(www\.)?", "", str(url or "").strip().lower()).rstrip("/")


def check_coherence(report: Report, content: dict[str, Any]) -> None:
    """One curated entry per real-world thing: one content ID names one entity (R1), no two curated entries share an
    address or DOI (R2), a curated entry that matches a snapshot record links it (R3), references to snapshot records
    resolve (R4), and entries nothing uses are reported (R5)."""
    # R1, read from the generator's own index of what each content ID names
    graph = Graph()
    try:
        build_crate(content, graph)
    except (ContentError, KeyError, TypeError, ValueError) as error:
        report.error("coherence", f"the crate could not be built to check identifiers: {error}")
        return
    for content_id, entity_ids in sorted(graph.index.items()):
        if len(set(entity_ids)) > 1:
            report.error(f"id:{content_id}", "names several entities: " + ", ".join(sorted(set(entity_ids))))

    # Every reference to one of the crate's own entities names an entity the crate has.
    def targets(value: Any) -> Iterator[str]:
        if isinstance(value, list):
            for item in value:
                yield from targets(item)
        elif isinstance(value, dict):
            if set(value) == {"@id"}:
                yield value["@id"]
            else:
                for item in value.values():
                    yield from targets(item)

    for entity_id, entity in graph.entities.items():
        for key, value in entity.items():
            missing = sorted({target for target in targets(value) if target.startswith("#")} - graph.entities.keys())
            if key != "@id" and missing:
                report.error(f"crate:{entity_id}", f"{key} names {', '.join(missing)}, which the crate does not have")

    # R2, curated entries keyed by address and DOI
    entries: list[tuple[str, str, str]] = []
    for resource in content["resources"]:
        entries.append((f"resource:{resource['id']}", "url", bare_url(resource.get("url"))))
        if resource.get("citation", {}).get("doi"):
            entries.append((f"resource:{resource['id']}", "doi", resource["citation"]["doi"].lower()))
    for source in content["sources"]:
        entries.append((f"sources:{source['id']}", "url", bare_url(source.get("url"))))
        if source.get("doi"):
            entries.append((f"sources:{source['id']}", "doi", source["doi"].lower()))
            entries.append((f"sources:{source['id']}", "url", bare_url("https://doi.org/" + source["doi"])))
    for repository in content["repositories"]:
        entries.append((f"repository:{repository['id']}", "url", bare_url(repository.get("url"))))
    for organization in content["guide"].get("organization", []):
        entries.append((f"organization:{organization['id']}", "url", bare_url(organization.get("url"))))
    seen: dict[tuple[str, str], str] = {}
    for where, key, value in entries:
        if not value:
            continue
        other = seen.setdefault((key, value), where)
        if other != where:
            what = "address" if key == "url" else "DOI"
            report.error(where, f"describes the same thing as {other} (same {what}); merge them into one entry")

    # R3 and R4, curated entries against the snapshot records they match
    dashboard = next((item for item in content["snapshots"] if item.get("fip") or item.get("resource")), {})
    fers = {bare_url(fer.get("url")): fer["id"] for fer in dashboard.get("resource", []) if fer.get("url")}
    fer_ids = {fer["id"] for fer in dashboard.get("resource", [])}
    for resource in content["resources"]:
        # A record matches by its address, or by sharing the curated entry's ID, as the same name usually is.
        match = fers.get(bare_url(resource.get("url"))) or (resource["id"] if resource["id"] in fer_ids else None)
        if match and resource.get("fipDashboard") != match:
            report.error(
                f"resource:{resource['id']}", f"matches FIP Dashboard resource '{match}'; link it with fipDashboard"
            )
    organizations = dashboard.get("organization", [])
    org_by_url = {bare_url(org.get("url")): org["id"] for org in organizations if org.get("url")}
    org_by_ror = {org["ror"]: org["id"] for org in organizations if org.get("ror")}
    org_ids = {org["id"] for org in organizations}
    for organization in content["guide"].get("organization", []):
        where = f"organization:{organization['id']}"
        match = org_by_url.get(bare_url(organization.get("url"))) or org_by_ror.get(organization.get("ror"))
        if match and organization.get("fipDashboard") != match:
            report.error(where, f"matches FIP Dashboard organisation '{match}'; link it with fipDashboard")
        if organization.get("fipDashboard") and organization["fipDashboard"] not in org_ids:
            report.error(where, f"FIP Dashboard has no organisation '{organization['fipDashboard']}'")
    snapshot_repositories = [
        repository for snapshot in content["snapshots"] for repository in snapshot.get("repository", [])
    ]
    by_address = {
        bare_url(repository.get("url")): repository for repository in snapshot_repositories if repository.get("url")
    }
    curated = [(f"repository:{r['id']}", r) for r in content["repositories"]] + [
        (f"resource:{r['id']}", {"url": r.get("url"), **r["repository"]})
        for r in content["resources"]
        if r.get("repository")
    ]
    for where, repository in curated:
        match = by_address.get(bare_url(repository.get("url")))
        if match and match.get("re3data") and repository.get("re3data") != match["re3data"]:
            report.error(where, f"matches the re3data record {match['re3data']}; state it as re3data")

    # R5, entries nothing uses
    cited = {clause.get("source") for clause in content["ledger"]} | set(content["guide"]["guide"].get("isBasedOn", []))
    cited |= {obj for action in content["provenance"] for obj in action.get("objects", [])}
    cited |= referenced(content)
    for resource in content["resources"]:
        if not resource.get("stations") and resource["id"] not in cited and not resource.get("repository"):
            report.warn(
                f"resource:{resource['id']}",
                "nothing uses this resource: no station recommends it and nothing cites it",
            )
        if resource.get("citation") and resource["id"] not in cited:
            report.warn(f"resource:{resource['id']}", "carries a citation, but nothing cites it")
    for source in content["sources"]:
        if source["id"] not in cited:
            report.warn(f"sources:{source['id']}", "nothing cites this source")


def referenced(content: dict[str, Any]) -> set[str]:
    """Every entry a text refers to with [[id|phrase]]."""
    return {
        match["id"]
        for name, data in content.items()
        for _, _, value in walk(data, name)
        if isinstance(value, str)
        for match in REFERENCE.finditer(value)
    }


def check_references(report: Report, content: dict[str, Any]) -> None:
    """A reference in text, [[id|phrase]], is well formed and names a known resource, source, glossary term
    (term:<id>) or page of the guide (page:<id>), and a bilingual text refers to the same entries in both languages."""
    known = {item["id"] for item in content["resources"] + content["sources"]}
    known |= {"term:" + term["id"] for term in content["glossary"].get("term", [])}
    known |= {"page:" + page["id"] for page in content["pages"]}
    known |= {"clause:" + clause["id"] for clause in content["ledger"]}
    known.add("profile")

    def entries(where: str, text: str) -> set[str]:
        if "[[" in REFERENCE.sub("", text) or "]]" in REFERENCE.sub("", text):
            report.error(where, "a reference is not well formed; write [[id|phrase]]")
        found = {match["id"] for match in REFERENCE.finditer(text)}
        for entry in sorted(found - known):
            report.error(where, f"refers to an unknown entry '{entry}'")
        return found

    for name, data in content.items():
        for path, key, value in walk(data, name):
            where = f"{path}.{key}" if path else key
            if isinstance(value, dict) and value and set(value) <= set(LANGS):
                found = {lang: entries(f"{where}.{lang}", str(value.get(lang, ""))) for lang in LANGS}
                if found["cs"] != found["en"]:
                    differ = sorted(found["cs"] ^ found["en"])
                    report.error(where, "the Czech and English texts refer to different entries: " + ", ".join(differ))
            elif isinstance(value, str) and key not in LANGS and ("[[" in value or "]]" in value):
                entries(where, value)


def check_names(report: Report, content: dict[str, Any]) -> None:
    """Names readers see have an English form: a Czech name is a table with 'cs' and 'en', and a plain name is
    language-neutral (R6). A publisher that is a curated organisation is cited by the organisation's ID, which carries
    both names (R7)."""
    organizations = content["guide"].get("organization", [])
    ids = {organization["id"] for organization in organizations}
    named: list[tuple[str, Any]] = [(f"organization:{item['id']}", item.get("name")) for item in organizations]
    publishers: list[tuple[str, Any]] = []
    for source in content["sources"]:
        named.append((f"sources:{source['id']}", source.get("title")))
        publishers.append((f"sources:{source['id']}", source.get("publisher")))
    for resource in content["resources"]:
        named.append((f"resource:{resource['id']}", resource.get("name")))
        publishers.append((f"resource:{resource['id']}", (resource.get("citation") or {}).get("publisher")))
    for repository in content["repositories"]:
        named.append((f"repository:{repository['id']}", repository.get("name")))

    # R6, Czech names have an English form
    for where, name in named:
        if isinstance(name, str) and CZECH_LETTERS.search(name):
            report.error(where, f"'{name}' is a Czech name with no English form; give it as a table with 'cs' and 'en'")
    for where, name in publishers:
        if isinstance(name, str) and name not in ids and CZECH_LETTERS.search(name):
            report.error(
                where,
                f"publisher '{name}' is a Czech name with no English form; add the organisation with its Czech and "
                "English names and cite it by ID",
            )

    # R7, publishers that are curated organisations
    fold = lambda value: " ".join(str(value).casefold().split())  # noqa: E731 - a one-line normaliser
    known: dict[str, str] = {}
    for organization in organizations:
        name = organization.get("name")
        for value in name.values() if isinstance(name, dict) else [name]:
            if value:
                known[fold(value)] = known[fold(str(value).split(",", maxsplit=1)[0])] = organization["id"]
    for where, publisher in publishers:
        if isinstance(publisher, str) and publisher not in ids:
            match = known.get(fold(publisher)) or known.get(fold(publisher.split(",", maxsplit=1)[0]))
            if match:
                report.error(where, f"publisher '{publisher}' is the organisation '{match}'; cite it by that ID")


PAGE_MENUS = ("catalogue", "tools", "about", "header")  # header: a button beside the language


def check_pages_and_ui(report: Report, content: dict[str, Any]) -> None:
    unique(report, "pages", [page.get("id", "") for page in content["pages"]], "page")
    for page in content["pages"]:
        where = f"page:{page.get('id')}"
        require_text(report, where, page.get("title"), "title")
        if not isinstance(page.get("helper", False), bool):
            report.error(where, "helper must be true or false")
        if page.get("menu") not in PAGE_MENUS:
            menus = ", ".join(PAGE_MENUS)
            report.error(
                where, f"menu must be one of {menus}, so the page can be reached from the main menu or the header"
            )
        elif page["menu"] == "tools":
            require_text(report, where, page.get("description"), "description")
        for number, section in enumerate(page.get("section", []), start=1):
            require_text(report, f"{where}[{number}]", section.get("body"), "body")
            if "action" in section:
                require_text(report, f"{where}[{number}].action", section["action"].get("label"), "label")
                if not section["action"].get("href"):
                    report.error(f"{where}[{number}].action", "an action needs an href")

    def ui_strings(value: Any, path: str) -> None:
        if is_text(value):
            return
        if isinstance(value, dict):
            for key, item in value.items():
                ui_strings(item, f"{path}.{key}")
        else:
            report.error(path, "interface strings need Czech and English values")

    ui_strings(content["ui"], "ui")


def check_self_check_inputs(report: Report, content: dict[str, Any]) -> None:
    """Settings the self-check relies on: the nanopublication query, and the page URL that exports and links name."""
    nanopub = content["live"].get("nanopub")
    if nanopub:
        if "{fips}" not in nanopub.get("query", ""):
            report.error("nanopub", "the query must contain {fips}")
        if not nanopub.get("fipIri") or any("{code}" not in iri for iri in nanopub["fipIri"]):
            report.error("nanopub", "fipIri must list IRI forms that contain {code}")
    if not str(content["guide"]["guide"].get("pageUrl", "")).startswith("https://"):
        report.error("guide.baseUrl", "the guide's address must use HTTPS")


def check_icons_and_tasks(report: Report, content: dict[str, Any], root: Path, vocab: dict[str, set[str]]) -> None:
    """Every named icon is vendored, and every landing task belongs to a known lens."""
    icons_dir = root / "assets" / "icons"
    named: list[tuple[str, str]] = [
        (f"icons.ui.{key}", name) for key, name in content.get("icons", {}).get("ui", {}).items()
    ]
    for path, key, value in walk(content, ""):
        if key == "icon" and isinstance(value, str):
            named.append((path or "content", value))
    for where, name in named:
        if not (icons_dir / f"{name}.svg").is_file():
            report.error(where, f"icon '{name}' is not vendored; run scripts/vendor_icons.py")
    for task in content["guide"].get("task", []):
        if task.get("lens") not in vocab["lenses"]:
            report.error("guide.task", f"unknown lens '{task.get('lens')}'")
        if not task.get("href"):
            report.error("guide.task", "a task needs a link (href)")


def check_guide(report: Report, content: dict[str, Any], vocab: dict[str, set[str]], root: Path) -> None:
    guide_file = content["guide"]
    guide = guide_file["guide"]
    for field in ("name", "description", "acknowledgement", "aiStatement"):
        require_text(report, "guide", guide.get(field), field)
    if guide.get("releaseStatus") not in RELEASE_STATUSES:
        report.error("guide", f"releaseStatus must be one of {', '.join(RELEASE_STATUSES)}")
    if guide.get("releaseStatus") == "testing":
        require_text(report, "guide", guide.get("testingNotice"), "testingNotice")
    for stage in guide_file.get("stage", []):
        if stage.get("station") not in vocab["stations"]:
            report.error(f"stage:{stage.get('id')}", f"opens unknown station '{stage.get('station')}'")
    for help_route in guide_file.get("help", []):
        for lens in help_route.get("lenses", []):
            if lens not in vocab["lenses"]:
                report.error(f"help:{help_route.get('id')}", f"unknown lens '{lens}'")
    for person in guide.get("editors", []) + guide.get("reviewers", []) + guide.get("contributors", []):
        if person not in vocab["people"]:
            report.error("guide", f"unknown person '{person}'")
    if not guide.get("editors"):
        report.error("guide", "the guide needs at least one editor")
    for source in content["sources"]:
        for author in source.get("authors", []):
            if " " not in author and author not in vocab["people"]:
                report.error(f"source:{source.get('id')}", f"unknown person '{author}'")
    organization_ids = {organization["id"] for organization in guide_file.get("organization", [])}
    for person in guide_file.get("person", []):
        for organization in person.get("affiliation", []):
            if organization not in organization_ids:
                report.error(f"person:{person['id']}", f"unknown affiliation '{organization}'")
    shapes = root / "profile" / "fair-guide"
    if shapes.exists():
        profile = (shapes / "profile.ttl").read_text(encoding="utf-8")
        # The build writes the guide's address into the shapes; here the form is checked, whatever address they hold.
        version = f"profile/{guide.get('profileVersion', '')}>"
        if not re.search(r"<https://[^>]+/" + re.escape(version), profile):
            report.error("profile/fair-guide/profile.ttl", f"does not declare the profile IRI <…/{version}")
        for shape in sorted(shapes.rglob("*.ttl")):
            for prefix in re.findall(r"@prefix fg: <([^>]+)>", shape.read_text(encoding="utf-8")):
                if not prefix.endswith("/terms#"):
                    report.error(str(shape.relative_to(root)), f"fg: prefix {prefix} is not <address>terms#")


def check_no_build_output(report: Report, root: Path) -> None:
    """The repository holds authored files only: no generated file, no JSON file of the API, and the page with its
    generated blocks empty. Read from the files git tracks that are still on disk, so a removal already made counts."""
    try:
        listed = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return  # not a git working tree, such as a copied fixture
    tracked = (name for name in listed.stdout.decode("utf-8").split("\0") if name and (root / name).exists())
    for path in sorted(name for name in tracked if is_generated(name)):
        report.error(path, "is build output, which the repository does not hold; remove it, the build makes it")
    page = root / PAGE_FILE
    if page.exists():
        for match in BLOCK.finditer(page.read_text(encoding="utf-8")):
            if match.group("body").strip():
                report.error(PAGE_FILE, f"the generated block '{match.group('name')}' is filled; the build fills it")


def vocabularies(content: dict[str, Any]) -> dict[str, Any]:
    guide_file = content["guide"]
    return {
        "principles": {principle["id"] for principle in content["principles"]},
        "lenses": {lens["id"] for lens in guide_file.get("lens", [])},
        "clause_actors": {actor["id"] for actor in guide_file.get("actor", []) if actor.get("role") == "clause"},
        "owner_actors": {actor["id"] for actor in guide_file.get("actor", []) if actor.get("role") == "owner"},
        "statuses": {status["id"] for status in guide_file.get("status", [])},
        "resource_types": {item["id"] for item in guide_file.get("resourceType", [])},
        "repository_kinds": {item["id"] for item in guide_file.get("repositoryKind", [])},
        "stations": {data["station"]["id"] for data in content["stations"]},
        "terms": {term["id"] for term in content["glossary"].get("term", [])},
        "tests": {test["id"] for test in content["live"].get("champion", {}).get("test", [])},
        "people": {person["id"] for person in guide_file.get("person", [])},
        "instruments": {instrument["id"] for instrument in guide_file.get("instrument", [])},
        "freshness_days": int(guide_file["guide"].get("freshnessDays", 180)),
    }


def in_page_targets(content: dict[str, Any]) -> set[str]:
    targets = {"#path", "#ledger", "#repositories", "#resources"}
    targets |= {f"#station-{data['station']['id']}" for data in content["stations"]}
    targets |= {f"#check-{data['check']['id']}" for data in content["checks"]}
    targets |= {f"#page-{page['id']}" for page in content["pages"]}
    targets |= {f"#resource-{resource['id']}" for resource in content["resources"]}
    return targets


def check(content: dict[str, Any], root: Path, today: date | None = None) -> Report:
    report = Report()
    vocab = vocabularies(content)
    check_texts(report, content)
    check_links(report, content, in_page_targets(content))
    check_sources(report, content)
    clause_ids = check_ledger(report, content, vocab)
    for principle in content["principles"]:
        for code in principle.get("cts", []):
            if f"CTS.{code}" not in clause_ids:
                report.error(
                    f"principle:{principle['id']}", f"cts names no CoreTrustSeal requirement clause 'CTS.{code}'"
                )
        for profile in principle.get("cdif", []):
            if f"CDIF.{profile}" not in clause_ids:
                report.error(f"principle:{principle['id']}", f"cdif names no CDIF profile clause 'CDIF.{profile}'")
    check_stations(report, content, vocab, clause_ids)
    check_checks(report, content, vocab, clause_ids)
    check_resources(report, content, vocab, today or date.today())
    check_repositories(report, content, vocab, today or date.today())
    check_glossary(report, content)
    check_fip_dashboard(report, content, vocab)
    check_callouts(report, content, vocab)
    check_live(report, content, vocab, root)
    check_self_check_inputs(report, content)
    check_icons_and_tasks(report, content, root, vocab)
    check_provenance(report, content, vocab)
    check_coherence(report, content)
    check_names(report, content)
    check_references(report, content)
    check_pages_and_ui(report, content)
    check_guide(report, content, vocab, root)
    check_no_build_output(report, root)
    return report


# ---------------------------------------------------------------------------
# Provenance freshness against a git revision


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, encoding="utf-8", check=True)
    return result.stdout


def item_fingerprints(content: dict[str, Any]) -> dict[str, str]:
    """Canonical JSON of every item that provenance must cover."""
    items: dict[str, Any] = {}
    for clause in content["ledger"]:
        items[clause["id"]] = clause
    for data in content["stations"]:
        for advice in data.get("advice", []):
            items[advice["id"]] = advice
    for data in content["checks"]:
        for item in data.get("item", []):
            items[item["id"]] = item
    for resource in content["resources"]:
        items[resource["id"]] = resource
    return {key: json.dumps(value, sort_keys=True, default=str) for key, value in items.items()}


def check_freshness(report: Report, content: dict[str, Any], root: Path, base: str) -> None:
    base_time = datetime.fromisoformat(git(root, "show", "-s", "--format=%cI", base).strip())
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        for path in git(root, "ls-tree", "-r", "--name-only", base, "content/").split():
            target = temp_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(git(root, "show", f"{base}:{path}"), encoding="utf-8")
        before = (
            item_fingerprints(load_content(temp_root / "content"))
            if (temp_root / "content" / "guide.toml").exists()
            else {}
        )
    after = item_fingerprints(content)
    for item_id, fingerprint in after.items():
        if before.get(item_id) == fingerprint:
            continue
        fresh = [
            action
            for action in content["provenance"]
            if any(covered(pattern, item_id) for pattern in action.get("results", []))
            and isinstance(action.get("endTime"), datetime)
            and action["endTime"] > base_time
        ]
        if not fresh:
            report.error(f"{item_id}", f"changed since {base} but no provenance action newer than that covers it")


# ---------------------------------------------------------------------------
# Entry point


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this repository)")
    parser.add_argument("--base", help="git revision; items changed since then need a newer provenance action")
    parser.add_argument("--fail-stale", action="store_true", help="treat stale statuses as errors")
    args = parser.parse_args(argv)
    try:
        content = load_content(args.root / "content")
        report = check(content, args.root)
        if args.base:
            check_freshness(report, content, args.root, args.base)
    except (ContentError, KeyError, subprocess.CalledProcessError) as error:
        print(f"check_content: cannot read the content: {error}", file=sys.stderr)
        return 2
    for warning in report.warnings:
        print(f"warning: {warning}")
    for error in report.errors:
        print(f"error: {error}")
    failed = report.errors or (args.fail_stale and report.warnings)
    print(f"check_content: {len(report.errors)} errors, {len(report.warnings)} warnings")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
