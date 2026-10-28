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
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_crate import (  # noqa: E402
    BLOCK,
    LANGS,
    PAGE_FILE,
    PATH_LIFECYCLE,
    REFERENCE,
    RESOURCE_TYPES,
    ROOT,
    SOURCE_TYPES,
    ContentError,
    Graph,
    as_list,
    build_crate,
    is_generated,
    load_content,
    reference_targets,
    vocabulary_errors,
)
from catalogue_identity import alternate_id
from corrections import validate_fields
from registry_identifiers import DATACITE_REPOSITORY, FAIRSHARING_DOI, canonical_fairsharing_doi

LEVELS = ("L0", "L1", "L2")
CLAUSE_KINDS = ("requirement", "recommendation", "fulfilment", "statement")
CLAUSE_STATUSES = ("current", "refresh", "superseded")
HEALTH = ("available", "degraded", "unavailable")
PREFILL_SOURCES = ("datacite", "nkr", "champion", "fip", "resolver", "re3data")
ACTION_TYPES = ("create", "update")
LIFECYCLE_BASES = ("published", "reviewed", "unconfirmed")
# The checks the guide knows; a question's ID is its check's ID and a serial number (docs/content-model.md,
# Identifiers).
CHECKS = ("dataset", "gate", "maturity", "fip", "institution", "coretrustseal", "cdif", "software", "fdo")
QUESTION_NUMBER = re.compile(r"^\d{2}$")
GATE_TIERS = ("required", "recommended")
MATURITY_TIERS = ("minimum", "recommended", "advanced")
# Checks built on a standard's requirements start with what the standard requires.
TIERS = {
    "gate": GATE_TIERS,
    "coretrustseal": ("standard",),
    "cdif": ("standard", "recommended", "advanced"),
    "software": ("basic", "advanced"),
    "fdo": ("basic", "advanced"),
}
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
# A requirement's ID is its source's code and a local part: the source's own label where it labels its items
# consistently, a serial number otherwise.
CLAUSE_ID = re.compile(r"^(?P<code>[A-Z][A-Z0-9-]*)\.(?P<local>[A-Za-z0-9][A-Za-z0-9.-]*)$")
# An advice item's ID is its station's ID and a serial number; what it is for (audience, level) is in its fields.
ADVICE_ID = re.compile(r"^(?P<station>[a-z0-9-]+)\.(?P<number>\d{2})$")
# Stations, checks, pages, resources and sources carry lower-case kebab-case IDs.
SLUG = re.compile(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$")
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
    """Whether a value is a bilingual table: keys only from LANGS. Every rule that reads bilingual text uses this."""
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


# ---------------------------------------------------------------------------
# Rules


def check_texts(report: Report, content: dict[str, Any]) -> None:
    """Every bilingual table has both languages; no raw HTML or script URLs anywhere."""
    for name, data in content.items():
        for path, key, value in walk(data, name):
            where = f"{path}.{key}" if path else key
            if is_text(value):
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


def topic_target_error(value: str, topics: dict[str, dict[str, set[str]]]) -> str | None:
    """Why a topic target such as `#resources?type=standard,vocabulary` is invalid, or None when it is valid."""
    base, _, query = value.partition("?")
    facets = topics.get(base)
    if facets is None:
        return f"'{base}' takes no topic; use one of {', '.join(sorted(topics))}"
    if not query:
        return "a topic target needs at least one facet"
    for part in query.split("&"):
        key, _, values = part.partition("=")
        if key not in facets:
            return f"unknown facet '{key}' for {base}; use one of {', '.join(sorted(facets))}"
        unknown = [item for item in values.split(",") if item not in facets[key]]
        if not values or unknown:
            return f"unknown {key} value(s) {', '.join(unknown) or '(none)'} for {base}"
    return None


def check_links(
    report: Report, content: dict[str, Any], targets: set[str], topics: dict[str, dict[str, set[str]]] | None = None
) -> None:
    for name, data in content.items():
        for path, key, value in walk(data, name):
            where = f"{path}.{key}"
            if not isinstance(value, str):
                continue
            if key == "url" and not (value.startswith("https://") or value.startswith("mailto:")):
                report.error(where, f"link must use HTTPS: {value}")
            elif key == "href":
                if value.startswith("#") and "?" in value:
                    error = topic_target_error(value, topics or {})
                    if error:
                        report.error(where, f"topic target '{value}': {error}")
                elif value.startswith("#"):
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
    codes = source_codes(content)
    clause_ids = set(ids)
    for clause in clauses:
        where = f"ledger:{clause.get('id')}"
        for term in clause.get("terms", []):
            if term not in {str(item["id"]) for item in content.get("glossary", {}).get("term", [])}:
                report.error(where, f"original definition names unknown term '{term}'")
            if not clause.get("guidance"):
                report.error(where, "an original definition needs its source text in guidance")
        id_match = CLAUSE_ID.match(clause.get("id", ""))
        if not id_match:
            report.error(where, "ID must be <source code>.<local part>")
        elif clause.get("source") in codes and id_match["code"] != codes[clause["source"]]:
            report.error(where, f"ID must start with its source's code '{codes[clause['source']]}'")
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
            report.error(where, "guidance is the source's own text, in its original language as published")
        if "guidanceLanguage" in clause:
            if not clause.get("guidance"):
                report.error(where, "guidanceLanguage needs an original guidance passage")
            if clause["guidanceLanguage"] not in LANGS:
                report.error(where, "guidanceLanguage must be cs or en")
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


def source_code(source: dict[str, Any]) -> str:
    """A source's code: its declared `code`, or its ID in capitals without a version suffix."""
    return source.get("code") or re.sub(r"-\d+(?:\.\d+)+$", "", source["id"]).replace(".", "-").upper()


def source_codes(content: dict[str, Any]) -> dict[str, str]:
    """The code of every source and every cited resource, by ID."""
    return {source["id"]: source_code(source) for source in content["sources"]} | {
        resource["id"]: source_code(resource) for resource in content["resources"] if resource.get("citation")
    }


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
    if citation.get("preparationStatus") is not None:
        if citation.get("id") != "layers-seams-manuscript" or citation["preparationStatus"] != "in-preparation":
            report.error(where, "only the approved Layers-and-Seams manuscript may be cited as in preparation")
        if citation.get("type") != "article" or not citation.get("authors") or citation.get("inLanguage") != "en":
            report.error(
                where, "the in-preparation manuscript needs its authentic article title, authors and English language"
            )
        if any(citation.get(field) for field in ("doi", "datePublished", "publisher", "license", "journal", "year")):
            report.error(
                where,
                "an in-preparation manuscript cannot claim a DOI, publication date, "
                "publisher, journal, year or licence",
            )
        return
    if not (own_url or citation.get("url") or citation.get("doi")):
        report.error(where, "a source needs a URL or a DOI")
    if not (citation.get("datePublished") or citation.get("dateAccessed")):
        report.error(where, "a source needs datePublished or dateAccessed")


def check_type_crosswalk(report: Report, content: dict[str, Any]) -> None:
    """Every FIP Dashboard type and every citation form belongs to exactly one of the guide's resource types, and
    every guide type has a schema.org type."""
    types = content["guide"].get("resourceType", [])
    for prefix, key, known in (
        (
            "fd",
            "fipDashboard",
            {item["id"] for snapshot in content["snapshots"] for item in snapshot.get("resourceType", [])},
        ),
        ("form", "citation", set(SOURCE_TYPES)),
    ):
        claimed: dict[str, list[str]] = {}
        for item in types:
            for value in item.get(key, []):
                claimed.setdefault(value, []).append(item["id"])
        for value in sorted(known | set(claimed)):
            owners = claimed.get(value, [])
            if value not in known:
                # A snapshot need not hold every FIP Dashboard type at once; a citation form must exist.
                if prefix == "form":
                    report.error(f"guide:resourceType.{key}", f"'{value}' is not a known {key} type")
            elif len(owners) != 1:
                report.error(
                    f"guide:resourceType.{key}",
                    f"'{value}' belongs to {len(owners)} resource types; it must belong to one",
                )
    for item in types:
        if item["id"] not in RESOURCE_TYPES:
            report.error(f"guide:resourceType.{item['id']}", "no schema.org type for this resource type")


def check_sources(report: Report, content: dict[str, Any]) -> None:
    unique(report, "sources", [source.get("id", "") for source in content["sources"]], "source")
    for source in content["sources"]:
        check_citation(report, f"sources:{source.get('id')}", source, own_url=False)
        if "short" in source:
            require_text(report, f"sources:{source.get('id')}", source["short"], "short", proper_name_allowed=True)


def model_items(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Stable identifiers for the model definitions, observations and role-specific explanations."""
    data = content.get("model", {})
    result = {}
    if data.get("model"):
        result[f"model:{data['model']['id']}"] = data["model"]
        if data["model"].get("workedExample"):
            result["model:worked-example"] = data["model"]["workedExample"]
    for kind in ("layer", "seam", "example"):
        result |= {f"{kind}.{item['id']}": item for item in data.get(kind, [])}
    result |= {f"context:{item['station']}:{item['lens']}": item for item in data.get("context", [])}
    return result


def check_model(report: Report, content: dict[str, Any], vocab: dict[str, Any], today: date) -> None:
    """Keep conceptual definitions, explicit topic associations and scoped dated observations distinct."""
    data = content.get("model", {})
    manuscript = "layers-seams-manuscript"
    for clause in content["ledger"]:
        if clause.get("source") == manuscript:
            report.error(
                f"clause:{clause['id']}", "the in-preparation model manuscript cannot supply ledger requirements"
            )
    if not data:
        return
    model = data.get("model", {})
    if any(field in model for field in ("status", "asOf", "evidence", "owner")):
        report.error("model", "generic model definitions cannot carry implementation status or an assigned owner")
    if model.get("id") != "layers-seams":
        report.error("model", "model ID must be layers-seams")
    if model.get("source") != manuscript:
        report.error("model", "the conceptual model must cite the approved manuscript")
    source = next((item for item in content["sources"] if item["id"] == manuscript), {})
    if source.get("preparationStatus") != "in-preparation":
        report.error("model", "the approved manuscript source must be marked in-preparation")
    for field in ("name", "description", "introduction", "ordering", "feedback"):
        require_text(report, "model", model.get(field), field)
    if model.get("workedExample"):
        worked = model["workedExample"]
        for field in ("name", "description"):
            require_text(report, "model:worked-example", worked.get(field), field)
        if not worked.get("steps") or set(worked["steps"]) - set(content_index(content)):
            report.error("model:worked-example", "worked example must link existing content identities in order")
    for kind in ("layer", "seam", "example"):
        unique(report, f"model:{kind}", [item.get("id", "") for item in data.get(kind, [])], kind)
        for item in data.get(kind, []):
            where = f"model:{kind}.{item.get('id')}"
            if not SLUG.fullmatch(item.get("id", "")):
                report.error(where, "ID must be lower-case kebab-case")
            for field in ("name", "description"):
                require_text(report, where, item.get(field), field)
            if kind != "example" and any(field in item for field in ("status", "asOf", "evidence", "owner")):
                report.error(where, "generic model definitions cannot carry implementation status or an assigned owner")
    layers = {item["id"] for item in data.get("layer", [])}
    if layers != {"policy", "community", "infrastructure", "planning", "support", "evaluation"}:
        report.error("model:layers", "the model must retain its six functional layers")
    seams = {item["id"] for item in data.get("seam", [])}
    for item in data.get("seam", []):
        where = f"model:seam.{item['id']}"
        for field in ("transfer", "sender", "recipient", "carrier", "maintainers"):
            require_text(report, where, item.get(field), field)
        if not item.get("layers") or set(item["layers"]) - layers:
            report.error(where, "seam must reference known functional layers")
        if item.get("source", manuscript) != manuscript:
            report.error(where, "seam definition must retain its manuscript source")
    for item in data.get("example", []):
        where = f"model:example.{item['id']}"
        require_text(report, where, item.get("scope"), "scope")
        if item.get("seam") not in seams:
            report.error(where, "example names an unknown seam")
        if item.get("status") not in vocab["statuses"]:
            report.error(where, "example needs a known implementation status")
        observed = str(item.get("asOf", ""))
        try:
            parsed = date.fromisoformat(observed + "-01" if re.fullmatch(r"\d{4}-\d{2}", observed) else observed)
            if parsed > today:
                raise ValueError
        except ValueError:
            report.error(where, "example needs an actual YYYY-MM or ISO date observation, not in the future")
        if not item.get("evidence") or set(item["evidence"]) - cited_ids(content):
            report.error(where, "example must cite identifiable evidence for its scope, status and date")
    targets = content_index(content)
    seen = set()
    for item in data.get("association", []):
        where = f"model:association.{item.get('target')}"
        target = item.get("target")
        if target not in targets:
            report.error(where, "association names an unknown content target")
        if target in seen:
            report.error(where, "one explicit association per content target; merge its layer and seam references")
        seen.add(target)
        if not item.get("layers") and not item.get("seams"):
            report.error(where, "association must name at least one layer or seam")
        if set(item.get("layers", [])) - layers or set(item.get("seams", [])) - seams:
            report.error(where, "association references an unknown layer or seam")
    seen_contexts = set()
    for item in data.get("context", []):
        key = (item.get("station"), item.get("lens"))
        where = f"model:context.{key[0]}.{key[1]}"
        if key in seen_contexts:
            report.error(where, "one explanation per station and lens")
        seen_contexts.add(key)
        if key[0] not in vocab["stations"] or key[1] not in vocab["lenses"]:
            report.error(where, "context must address an existing station and reader lens")
        require_text(report, where, item.get("text"), "text")
        if not item.get("seams") or set(item["seams"]) - seams:
            report.error(where, "context must reference known seams")


ABBREVIATIONS = re.compile(r"\b(?:e\.g|i\.e|etc|např|tzv|tj|resp|apod)\.", re.IGNORECASE)


def sentences(value: str) -> int:
    """How many sentences a text has, not counting the full stops of common abbreviations."""
    return len([part for part in re.split(r"(?<=[.!?])\s+", ABBREVIATIONS.sub("", value.strip())) if part])


def lifecycle_items(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Stable identifiers for the life-cycle models (`lifecycle:<model>`), their stages (`<model>.<stage>`) and the
    crosswalk's correspondences (`crosswalk:<stage>_<stage>`)."""
    result: dict[str, dict[str, Any]] = {}
    for data in content.get("lifecycles", []):
        model = data["lifecycle"]
        result[f"lifecycle:{model['id']}"] = model
        result |= {f"{model['id']}.{stage['id']}": stage for stage in data.get("stage", [])}
    result |= {
        "crosswalk:" + item.get("id", "_".join(item.get("stages", []))): item for item in content.get("crosswalk", [])
    }
    return result


GUIDE_CZECH = re.compile(r"(?<![\w-])průvodc(?:e|i|em|ů|ům|ích)\b")
GUIDE_ENGLISH = re.compile(r"\b(?:the|this) guide\b")
# Text that is not the Guide's own wording: quoted originals, registry records and published titles.
GUIDE_NAME_SKIPPED = {"snapshots", "glossary", "identifiers"}


def check_guide_name(report: Report, content: dict[str, Any]) -> None:
    """The Guide is named with a capital letter wherever the word means it: Průvodce, the Guide (D-177). A
    lower-case form is accepted only inside a reviewed generic use (`genericGuideUses` in guide.toml), such as a
    licence selector."""
    generic = [phrase.lower() for phrase in content["guide"]["guide"].get("genericGuideUses", [])]

    def accepted(text: str, start: int, end: int) -> bool:
        lowered = text.lower()
        for phrase in generic:
            for found in re.finditer(re.escape(phrase), lowered):
                if found.start() <= start and end <= found.end():
                    return True
        return False

    for name, data in content.items():
        if name in GUIDE_NAME_SKIPPED:
            continue
        for path, key, value in walk(data, name):
            if not isinstance(value, str) or key in ("guidance", "genericGuideUses") or ".citation" in path:
                continue
            pattern = GUIDE_ENGLISH if key == "en" or (key != "cs" and not GUIDE_CZECH.search(value)) else GUIDE_CZECH
            for match in pattern.finditer(value):
                if not accepted(value, match.start(), match.end()):
                    report.error(f"{path}.{key}", f"name the Guide with a capital letter: '{match.group(0)}' (D-177)")


def check_lifecycles(report: Report, content: dict[str, Any]) -> None:
    """Each life-cycle model cites its source, and each stage keeps its published name and definition: a name the
    guide translated is marked, a definition is quoted, and a path stage adds the Průvodce's Czech translation of it
    (D-176). Each correspondence links a stage of the path's
    model to another model's stage and states its basis; a source's correspondence cites where it is published, the
    guide's own and an unconfirmed one say why. Every path stage corresponds to a stage of each other model, and a
    station's stage is one of the path's."""
    lifecycles = content.get("lifecycles", [])
    if not lifecycles:
        return
    sources = {source["id"] for source in content["sources"]}
    models = [data["lifecycle"] for data in lifecycles]
    unique(report, "lifecycle", [model.get("id", "") for model in models], "model")
    unique(report, "lifecycle", [str(model.get("position", "")) for model in models], "position")
    if PATH_LIFECYCLE not in {model.get("id") for model in models}:
        report.error("lifecycle", f"the path's life-cycle model '{PATH_LIFECYCLE}' is missing")
    stages: dict[str, str] = {}
    for data in lifecycles:
        model = data["lifecycle"]
        where = f"lifecycle:{model.get('id')}"
        if not SLUG.match(str(model.get("id", ""))):
            report.error(where, "the model ID must be lower-case kebab-case")
        require_text(report, where, model.get("name"), "name", proper_name_allowed=True)
        for field in ("source", "czechSource"):
            if field in model and model[field] not in sources:
                report.error(where, f"{field} names no source '{model[field]}'")
        if "source" not in model:
            report.error(where, "a life-cycle model cites its source")
        unique(report, where, [stage.get("id", "") for stage in data.get("stage", [])], "stage")
        if not data.get("stage"):
            report.error(where, "a life-cycle model lists its stages")
        for stage in data.get("stage", []):
            key = f"{model.get('id')}.{stage.get('id')}"
            stages[key] = model.get("id")
            here = f"lifecycle:{key}"
            if not SLUG.match(str(stage.get("id", ""))):
                report.error(here, "the stage ID must be lower-case kebab-case")
            require_text(report, here, stage.get("name"), "name", proper_name_allowed=True)
            if set(as_list(stage.get("translated"))) - set(LANGS):
                report.error(here, f"translated lists languages of the name: {', '.join(LANGS)}")
            # The source's definition is quoted in its language; a path stage adds the Průvodce's Czech translation,
            # sentence for sentence, and a Czech source's quote keeps its stage label so that it reads as a sentence.
            for field in ("definition", "translation", "czechDefinition", "note"):
                if field in stage and not (isinstance(stage[field], str) and stage[field].strip()):
                    report.error(here, f"{field} is a text, as a string")
            if not stage.get("definition"):
                report.error(here, "missing definition")
            if bool(stage.get("czechDefinition")) != bool(model.get("czechSource")):
                report.error(here, "a Czech definition is quoted from the model's czechSource, for every stage")
            label = stage["name"].get("cs", "") if isinstance(stage.get("name"), dict) else ""
            if stage.get("czechDefinition") and not str(stage["czechDefinition"]).startswith(f"{label}: "):
                report.error(here, f"the quoted Czech definition keeps its stage label ('{label}: …')")
            if model.get("id") == PATH_LIFECYCLE and not stage.get("translation"):
                report.error(here, "a path stage carries the Průvodce's Czech translation of its definition")
            if model.get("id") != PATH_LIFECYCLE and stage.get("translation"):
                report.error(here, "only the path's stages are translated; other definitions stay in their language")
            if stage.get("translation") and sentences(stage["translation"]) != sentences(stage.get("definition", "")):
                report.error(here, "the translation does not render the definition sentence for sentence")
            if not stage.get("locator"):
                report.error(here, "locator says where the source publishes the stage")
    pairs = set()
    linked: dict[str, set[str]] = {}
    for item in content.get("crosswalk", []):
        keys = as_list(item.get("stages"))
        where = "crosswalk:" + item.get("id", "_".join(str(key) for key in keys))
        if len(keys) != 2 or any(key not in stages for key in keys):
            report.error(where, "a correspondence names two known stages, as <model>.<stage>")
            continue
        if [stages[key] for key in keys].count(PATH_LIFECYCLE) != 1:
            report.error(where, f"a correspondence links a stage of '{PATH_LIFECYCLE}' to a stage of another model")
        if frozenset(keys) in pairs:
            report.error(where, "the correspondence is listed twice")
        pairs.add(frozenset(keys))
        basis = item.get("basis")
        if basis not in LIFECYCLE_BASES:
            report.error(where, f"basis must be one of {', '.join(LIFECYCLE_BASES)}")
        if basis in ("published", "unconfirmed") and (item.get("source") not in sources or not item.get("locator")):
            report.error(where, f"a {basis} correspondence cites its source and where it is published (locator)")
        if basis in ("reviewed", "unconfirmed"):
            require_text(report, where, item.get("note"), "note")
        path_stage, other = sorted(keys, key=lambda key: stages[key] != PATH_LIFECYCLE)
        linked.setdefault(path_stage, set()).add(stages[other])
    others = {model.get("id") for model in models} - {PATH_LIFECYCLE}
    for key, model in stages.items():
        if model == PATH_LIFECYCLE and others - linked.get(key, set()):
            report.error(
                f"lifecycle:{key}", "corresponds to no stage of " + ", ".join(sorted(others - linked.get(key, set())))
            )
    # The path follows the cycle: each stage holds its steps in the cycle's order, and no step stands outside it; the
    # assessment, a form of reuse, belongs to the reuse stage (D-175).
    path_stages = [
        stage["id"]
        for data in lifecycles
        if data["lifecycle"].get("id") == PATH_LIFECYCLE
        for stage in data.get("stage", [])
    ]
    ordered = sorted((data["station"] for data in content["stations"]), key=lambda station: station.get("position", 0))
    reached = -1
    for station in ordered:
        stage = station.get("lifecycleStage")
        where = f"station:{station['id']}"
        if stage is None:
            report.error(where, "every step belongs to a stage of the life cycle; name its lifecycleStage")
        elif stage not in path_stages:
            report.error(where, f"lifecycleStage names no stage of '{PATH_LIFECYCLE}'")
        elif path_stages.index(stage) < reached:
            report.error(where, "the steps follow the order of the life cycle's stages")
        else:
            reached = path_stages.index(stage)
    held = {station.get("lifecycleStage") for station in ordered}
    for stage in path_stages:
        if stage not in held:
            report.error(f"lifecycle:{PATH_LIFECYCLE}.{stage}", "the stage holds no step of the path")


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
        keys_by_lens: dict[str, int] = {lens: 0 for lens in vocab["lenses"]}
        for advice in data.get("advice", []):
            advice_id = advice.get("id", "")
            advice_ids.append(advice_id)
            item = f"advice:{advice_id}"
            match = ADVICE_ID.match(advice_id)
            lenses = sorted(vocab["lenses"]) if advice.get("lens") == "*" else as_list(advice.get("lens"))
            if not match:
                report.error(item, "ID must be <station>.<nn>")
            elif match["station"] != station["id"]:
                report.error(item, f"ID names station '{match['station']}' but the item is in '{station['id']}'")
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
            if advice.get("kind") not in (None, "ai", "key"):
                report.error(item, "kind must be 'ai', 'key' or omitted")
            if advice.get("kind") == "key":
                # The station's core idea, shown at the top of its how-to.
                if advice.get("level") != "L1" or advice.get("steps"):
                    report.error(item, "a key point is an L1 item without steps")
                for lens in lenses:
                    if lens in keys_by_lens:
                        keys_by_lens[lens] += 1
            if advice.get("kind") == "ai":
                # An AI tip says what to check afterwards and gives a prompt to copy.
                require_text(report, item, advice.get("check"), "check")
                require_text(report, item, advice.get("prompt"), "prompt")
            elif "check" in advice or "prompt" in advice:
                report.error(item, "only an AI item carries check and prompt")
            if advice.get("level") == "L0" and advice.get("kind") != "ai":
                # The next step, and at most one related tool beside it.
                actions = as_list(advice.get("action"))
                if not actions:
                    report.error(item, "an L0 item needs one concrete action")
                elif len(actions) > MAX_ACTIONS:
                    report.error(
                        item, f"an L0 item offers at most {MAX_ACTIONS} actions: the next step and one related tool"
                    )
                for action in actions:
                    require_text(report, f"{item}.action", action.get("label"), "label")
                    if not action.get("href"):
                        report.error(f"{item}.action", "an action needs an href")
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
        for lens, count in keys_by_lens.items():
            if count != 1:
                report.error(where, f"lens {lens} needs exactly one key point (found {count})")
    unique(report, "advice", advice_ids, "advice")


MAX_ACTIONS = 2


def check_checks(report: Report, content: dict[str, Any], vocab: dict[str, set[str]], clause_ids: set[str]) -> None:
    item_ids: list[str] = []
    check_ids = [data["check"]["id"] for data in content["checks"]]
    unique(report, "checks", check_ids, "check")
    for data in content["checks"]:
        check = data["check"]
        where = f"check:{check['id']}"
        if check["id"] not in CHECKS:
            report.error(where, f"check ID must be one of {', '.join(CHECKS)}")
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
            parent, _, number = item_id.rpartition(".")
            if parent != check["id"] or not QUESTION_NUMBER.match(number):
                report.error(here, f"a question of the {check['id']} check has the ID {check['id']}.<nn>")
            if item.get("prefillLevel") not in (None, "partly"):
                report.error(here, "prefillLevel can only be 'partly'")
            if "championEvidenceOnly" in item:
                if not isinstance(item["championEvidenceOnly"], bool):
                    report.error(here, "championEvidenceOnly must be a boolean")
                if not item.get("prefill", {}).get("champion"):
                    report.error(here, "championEvidenceOnly needs named Champion tests")
            if "context" in item and not isinstance(item["context"], bool):
                report.error(here, "context must be a boolean")
            if item.get("context") and item.get("prefill"):
                report.error(here, "source context cannot be automatically answered as a criterion")
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
    unique(
        report,
        "resources",
        [resource["rdmkit"].get("id", "") for resource in content["resources"] if resource.get("rdmkit")],
        "RDMkit tool record",
    )
    for resource in content["resources"]:
        where = f"resource:{resource.get('id')}"
        if resource.get("rdmkit"):
            record = resource["rdmkit"]
            if not SLUG.fullmatch(str(record.get("id", ""))):
                report.error(where, "rdmkit needs its source record ID")
            for key in ("biotools", "fairsharing", "tess"):
                if key in record and (not isinstance(record[key], str) or not record[key].strip()):
                    report.error(where, f"rdmkit {key} must be its non-empty source identifier")
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
            if resource.get("type") != "registry":
                report.error(
                    f"{where}:repository",
                    "only a resource of type 'registry' (repository or registry) carries repository facts",
                )
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
    for entry in content["repositories"] + content["resources"]:
        for value in entry.get("functions", []):
            if value not in vocab["repository_functions"]:
                report.error(entry["id"], f"unknown repository function '{value}'")
        if entry.get("functions") and entry in content["resources"] and entry.get("type") != "registry":
            report.error(entry["id"], "repository functions belong to repositories or registries")
    repositories = {item["re3data"] for snapshot in content["snapshots"] for item in snapshot.get("repository", [])}
    dashboard = {
        alternate_id(item, "fip-dashboard"): item
        for snapshot in content["snapshots"]
        for item in snapshot.get("resource", [])
    }
    tools = {alternate_id(item, "knav") for snapshot in content["snapshots"] for item in snapshot.get("tool", [])}
    annotations = content.get("repository_records", [])
    for key in ("re3data", "fipDashboard", "knav"):
        unique(report, f"repository records:{key}", [item[key] for item in annotations if item.get(key)], "record")
    for record in annotations:
        where = f"repository record:{record.get('re3data') or record.get('fipDashboard') or record.get('knav')}"
        if not any(record.get(key) for key in ("re3data", "fipDashboard", "knav")):
            report.error(where, "an annotation must identify an imported record")
        if record.get("re3data") and record["re3data"] not in repositories:
            report.error(where, "unknown re3data record")
        # Functions describe a repository; an annotation that only joins records may name any FIP Dashboard record.
        if record.get("fipDashboard") and (
            record["fipDashboard"] not in dashboard
            or (record.get("functions") and dashboard[record["fipDashboard"]].get("type") != "repository")
        ):
            report.error(where, "unknown FIP Dashboard repository or registry record")
        if record.get("knav") and record["knav"] not in tools:
            report.error(where, "unknown KNAV catalogue tool")
        if not record.get("evidence"):
            report.error(where, "reviewed record annotations need published evidence")
        for url in record.get("evidence", []):
            if not isinstance(url, str) or not url.startswith("https://"):
                report.error(where, "annotation evidence must be an HTTPS address")
        for value in record.get("functions", []):
            if value not in vocab["repository_functions"]:
                report.error(where, f"unknown repository function '{value}'")
    for entry in content["resources"] + content["repositories"] + content["sources"]:
        if entry.get("knav") and entry["knav"] not in tools:
            report.error(entry["id"], f"knav names no tool of the KNAV catalogue snapshot ('{entry['knav']}')")
    # A DataCite repository ID is the client's own ID, `<member>.<repository>` in lower case, and names one entry.
    datacite = [
        (entry["id"], entry.get("datacite") or entry.get("repository", {}).get("datacite"))
        for entry in content["repositories"] + content["resources"]
    ]
    datacite = [(entry_id, value) for entry_id, value in datacite if value]
    unique(report, "repositories:datacite", [value for _, value in datacite], "DataCite repository")
    for entry_id, value in datacite:
        if not isinstance(value, str) or not DATACITE_REPOSITORY.fullmatch(value):
            report.error(entry_id, f"datacite is not a DataCite repository ID ('{value}')")
    for snapshot in content["snapshots"]:
        info = snapshot.get("snapshot", {})
        where = f"snapshot:{info.get('source')}"
        for field in ("source", "url", "retrieved"):
            if not info.get(field):
                report.error(where, f"missing {field}")
        for repository in snapshot.get("repository", []):
            if repository.get("kind") and repository["kind"] not in vocab["repository_kinds"]:
                report.error(f"{where}:{repository.get('id')}", f"unknown kind '{repository['kind']}'")
        # An annotation joins one listed repository, named once, and adds a well-formed record to it.
        for number, row in enumerate(snapshot.get("annotation", []), start=1):
            here = f"{where}:annotation {number}"
            if bool(row.get("re3data")) == bool(row.get("url")):
                report.error(here, "an annotation names its repository by re3data or by url, one of them")
            if row.get("fairsharing"):
                value = str(row["fairsharing"])
                if not FAIRSHARING_DOI.fullmatch(value):
                    report.error(here, f"fairsharing is not a FAIRsharing DOI ('{value}')")
                elif value != canonical_fairsharing_doi(value):
                    report.error(here, f"fairsharing must use the published case ('{value}')")
            if row.get("datacite") and not DATACITE_REPOSITORY.fullmatch(str(row["datacite"])):
                report.error(here, f"datacite is not a DataCite repository ID ('{row['datacite']}')")
            if not row.get("fairsharing") and not row.get("datacite"):
                report.error(here, "an annotation adds a fairsharing record or a datacite repository")


VERIFICATION_LEVELS = ("verified", "self-declared", "under-review")
DECLARATION_STATUSES = ("in-use", "planned", "under-consideration", "to-be-replaced")


def check_fip_dashboard(report: Report, content: dict[str, Any], vocab: dict[str, Any]) -> None:
    """The dashboard snapshot is consistent, and every resource that names a dashboard record finds it."""
    snapshot = next((item for item in content["snapshots"] if item.get("fip") or item.get("resource")), None)
    if snapshot is None:
        return
    fers = {alternate_id(resource, "fip-dashboard") for resource in snapshot.get("resource", [])}
    organizations = {alternate_id(organization, "fip-dashboard") for organization in snapshot.get("organization", [])}
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
    for kind, plural in (("resource", "resources"), ("repository", "repositories")):
        for entry in content[plural]:
            if entry.get("fipDashboard") and entry["fipDashboard"] not in fers:
                report.error(f"{kind}:{entry['id']}", f"FIP Dashboard has no resource '{entry['fipDashboard']}'")


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
        if "definitionLanguage" in term and term["definitionLanguage"] not in LANGS:
            report.error(where, "definitionLanguage must name a supported source language")


def check_corrections(report: Report, content: dict[str, Any]) -> None:
    corrections = content.get("corrections", [])
    for error in validate_fields(corrections, content["glossary"]):
        report.error("corrections", error)
    terms = {term.get("id"): term for term in content["glossary"].get("term", [])}
    for correction in corrections:
        term = terms.get(correction.get("term"))
        if term is None:
            continue
        where = f"correction:{correction.get('id')}"
        text = term.get(correction.get("field"), "")
        if correction.get("replace") not in text:
            report.error(where, "the recorded replacement is absent")


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
        if test.get("endpoint"):
            endpoint_origin = re.match(r"^(https://[^/]+)", test["endpoint"])
            if not endpoint_origin or endpoint_origin.group(1) not in origins:
                report.error(where, "the endpoint's host is not a connector")
    local_tests = live.get("test", [])
    unique(report, "live", [test.get("id", "") for test in local_tests], "local test")
    questions = {item["id"]: item for check in content["checks"] for item in check.get("item", [])}
    assessment_scripts = live.get("discovery", {}).get("assessmentScripts", [])
    for test in local_tests:
        where = f"test:{test.get('id')}"
        question = test.get("question", "")
        if question not in questions:
            report.error(where, f"unknown question '{question}'")
        elif questions[question].get("context"):
            report.error(where, "source context cannot be automatically answered")
        if test.get("id") != "guide-" + question.replace(".", "-"):
            report.error(where, "local test ID must be guide-<question check>-<question number>")
        if test.get("family") not in ("object", "software"):
            report.error(where, "family must be object or software")
        for key in ("label", "description"):
            if not isinstance(test.get(key), dict) or any(not test[key].get(lang) for lang in LANGS):
                report.error(where, f"{key} needs Czech and English text")
        for key, extension in (("script", "js"), ("documentation", "html")):
            path = str(test.get(key, "")).split("#", 1)[0]
            if not re.fullmatch(r"assets/js/tests/[a-z][a-z0-9-]*\." + extension, path):
                report.error(where, f"{key} must name an attached {extension} file under assets/js/tests/")
            elif not (root / path).is_file():
                report.error(where, f"{key} attachment does not exist: {path}")
        if test.get("script") not in assessment_scripts:
            report.error(where, "the script is not in discovery.assessmentScripts")
        if test.get("entryPoint") != f'FairGuide.selfcheck.localTests["{test.get("id")}"]':
            report.error(where, "entryPoint must name this test's registered function")
    check_providers(report, content, vocab, root, origins=origins, questions=questions)
    for script in sorted((root / "assets" / "js").rglob("*.js")):
        for number, line in enumerate(script.read_text(encoding="utf-8").splitlines(), start=1):
            for url in URL_LITERAL.findall(line):
                origin = re.match(r"^(https?://[^/]+)", url)
                if not origin or origin.group(1) not in origins:
                    report.error(f"{script.relative_to(root)}:{number}", f"URL outside the connector allowlist: {url}")


PROVIDER_MODES = ("service", "import")
COVERAGE = ("whole", "partial")


def check_providers(
    report: Report,
    content: dict[str, Any],
    vocab: dict[str, set[str]],
    root: Path,
    *,
    origins: set[str],
    questions: dict[str, dict[str, Any]],
) -> None:
    """External evaluators: reviewed connectors and limits, native criteria with their own wording, and mappings that
    name a real question, a coverage and the versions they were reviewed against."""
    live = content["live"]
    providers = live.get("provider", [])
    if not providers:
        return
    settings = live.get("providers", {})
    script = str(settings.get("script", ""))
    if not re.fullmatch(r"assets/js/[a-z][a-z0-9-]*\.js", script) or not (root / script).is_file():
        report.error("providers", "script must name an existing file under assets/js/")
    if not isinstance(settings.get("maxImportBytes"), int) or not 0 < settings["maxImportBytes"] <= 4 * 1024 * 1024:
        report.error("providers", "maxImportBytes must be a whole number of bytes up to 4 MiB")
    connectors = {connector.get("id"): connector for connector in live.get("connector", [])}
    resources = {resource["id"] for resource in content["resources"]}
    unique(report, "providers", [provider.get("id", "") for provider in providers], "provider")
    for provider in providers:
        where = f"provider:{provider.get('id')}"
        if provider.get("resource") not in resources:
            report.error(where, f"unknown resource '{provider.get('resource')}'")
        if provider.get("mode") not in PROVIDER_MODES:
            report.error(where, f"mode must be one of {', '.join(PROVIDER_MODES)}")
        for key in ("form", "documentation", "code", "terms"):
            if key in provider and not str(provider[key]).startswith("https://"):
                report.error(where, f"{key} must be an https address")
        if not provider.get("form"):
            report.error(where, "a provider needs its public form or interface")
        if not isinstance(provider.get("observed"), date):
            report.error(where, "observed must be the date the provider was reviewed")
        reviewed = provider.get("reviewed")
        if not isinstance(reviewed, list) or not reviewed:
            report.error(where, "reviewed must list the provider versions the mappings were reviewed against")
        elif any(
            not isinstance(entry, dict) or not entry or not all(isinstance(v, str) and v for v in entry.values())
            for entry in reviewed
        ):
            report.error(where, "each reviewed version is a table of non-empty version strings")
        if provider.get("mode") == "service":
            connector = connectors.get(provider.get("connector"))
            if connector is None or connector.get("origin") not in origins:
                report.error(where, "a service provider needs a reviewed connector")
            path = str(provider.get("path", ""))
            if "{metric}" not in path or "{target}" not in path or path.startswith(("/", "http")):
                report.error(where, "path must be relative to the connector and name {metric} and {target}")
            for key, low, high in (("maxParallel", 1, 4), ("timeoutSeconds", 1, 60), ("maxBytes", 1, 1048576)):
                if not isinstance(provider.get(key), int) or not low <= provider[key] <= high:
                    report.error(where, f"{key} must be between {low} and {high}")
            if not isinstance(provider.get("scoreMax"), int) or provider["scoreMax"] < 1:
                report.error(where, "scoreMax must be the provider's highest native score")
        if "maturityMax" in provider and (not isinstance(provider["maturityMax"], int) or provider["maturityMax"] < 1):
            report.error(where, "maturityMax must be the provider's highest native maturity level")
        metrics = provider.get("metric", [])
        if not metrics:
            report.error(where, "a provider lists its native criteria")
        unique(report, where, [metric.get("id", "") for metric in metrics], "metric")
        for metric in metrics:
            here = f"{where}.{metric.get('id')}"
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", str(metric.get("id", ""))):
                report.error(here, "a metric ID is a Guide-owned primary identifier")
            if not isinstance(metric.get("name"), str) or not metric["name"].strip():
                report.error(here, "name is the provider's own wording of the criterion")
            if metric.get("principle") not in vocab["principles"]:
                report.error(here, f"unknown principle '{metric.get('principle')}'")
            if not isinstance(metric.get("label"), dict) or any(not metric["label"].get(lang) for lang in LANGS):
                report.error(here, "label needs Czech and English text")
        metric_ids = {alternate_id(metric, provider["id"]) for metric in metrics}
        pairs = [f"{mapping.get('metric')} {mapping.get('question')}" for mapping in provider.get("mapping", [])]
        unique(report, where, pairs, "mapping")
        for mapping in provider.get("mapping", []):
            here = f"{where}.{mapping.get('metric')}:{mapping.get('question')}"
            if mapping.get("metric") not in metric_ids:
                report.error(here, f"unknown metric '{mapping.get('metric')}'")
            question = questions.get(mapping.get("question"))
            if question is None:
                report.error(here, f"unknown question '{mapping.get('question')}'")
            elif question.get("context"):
                report.error(here, "source context cannot be automatically answered")
            if mapping.get("coverage") not in COVERAGE:
                report.error(here, f"coverage must be one of {', '.join(COVERAGE)}")
            if not isinstance(mapping.get("note"), dict) or any(not mapping["note"].get(lang) for lang in LANGS):
                report.error(here, "note needs Czech and English text stating what the criterion covers")


def content_index(content: dict[str, Any]) -> dict[str, str]:
    """Map content IDs that provenance actions can name to their kind."""
    index: dict[str, str] = {"guide": "guide"}
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
    for page in content["pages"]:
        index[f"page:{page['id']}"] = "page"
    for callout in content["callouts"]:
        index[f"callout:{callout['id']}"] = "callout"
        for item in callout.get("item", []):
            index[f"callout.{callout['id']}.{item['id']}"] = "callout item"
    for term in content["glossary"].get("term", []):
        index[f"term:{term['id']}"] = "term"
    for test in content["live"].get("test", []) + content["live"].get("champion", {}).get("test", []):
        index[f"test:{test['id']}"] = "test"
    for key in provider_criteria(content):
        index[key] = "criterion"
    for resource in content["resources"]:
        index.setdefault(resource["id"], "resource")
    for repository in content["repositories"]:
        index.setdefault(repository["id"], "repository")
    for organization in content["guide"].get("organization", []):
        index.setdefault("organization:" + organization["id"], "organization")
    for action in content["provenance"]:
        index.setdefault(f"action:{action['id']}", "action")
    for record in content.get("repository_records", []):
        for key, prefix in (("re3data", "re3data"), ("fipDashboard", "fip-dashboard")):
            if record.get(key):
                index.setdefault(f"{prefix}.{record[key]}", "repository record")
    index |= {key: "model" for key in model_items(content)}
    index |= {key: "lifecycle" for key in lifecycle_items(content)}
    index |= {
        f"infrastructure:{item['id']}": "infrastructure"
        for item in (content.get("infrastructures") or {}).get("infrastructure", [])
    }
    if (content.get("node") or {}).get("node"):
        index["node:eosc-cz-node"] = "node"
    for snapshot in content["snapshots"]:
        index |= {f"knav.{tool['id']}": "catalogue tool" for tool in snapshot.get("tool", [])}
    return index


def covered(pattern: str, item_id: str) -> bool:
    return item_id.startswith(pattern[:-1]) if pattern.endswith("*") else item_id == pattern


def issued_ids(content: dict[str, Any]) -> dict[str, list[str]]:
    """Every identifier the guide issues, by kind, in content order. Terms, FIPs, FIP Dashboard records and external
    tests carry their registries' identifiers. Local tests have guide-issued IDs (docs/content-model.md)."""
    return {
        "lenses": [lens["id"] for lens in content["guide"].get("lens", [])],
        "stations": [data["station"]["id"] for data in content["stations"]],
        "checks": [data["check"]["id"] for data in content["checks"]],
        # A check's modes and profiles are named within their check, and share links carry them.
        "modes": [
            f"{data['check']['id']}.{mode}" for data in content["checks"] for mode in data["check"].get("modes", [])
        ],
        "profiles": [
            f"{data['check']['id']}.{profile['id']}"
            for data in content["checks"]
            for profile in data["check"].get("profile", [])
        ],
        "pages": [page["id"] for page in content["pages"]],
        "callouts": [f"callout:{callout['id']}" for callout in content["callouts"]],
        "callout_items": [
            f"callout.{callout['id']}.{item['id']}"
            for callout in content["callouts"]
            for item in callout.get("item", [])
        ],
        "advice": [advice["id"] for data in content["stations"] for advice in data.get("advice", [])],
        "questions": [item["id"] for data in content["checks"] for item in data.get("item", [])],
        "tests": [test["id"] for test in content["live"].get("test", [])],
        "requirements": [clause["id"] for clause in content["ledger"]],
        "sources": [source["id"] for source in content["sources"]],
        "resources": [resource["id"] for resource in content["resources"]],
        "repositories": [repository["id"] for repository in content["repositories"]],
        "actions": [action["id"] for action in content["provenance"]],
        "model": list(model_items(content)),
        "lifecycle": list(lifecycle_items(content)),
    }


def check_identifiers(report: Report, content: dict[str, Any]) -> None:
    """A registered identifier names its entry for good: it is never renamed or reused, and an entry that goes away
    leaves its identifier retired. scripts/register_ids.py registers the identifiers of new entries."""
    register = content["identifiers"]
    if not register:
        return
    issued, retired = register.get("issued", {}), register.get("retired", {})
    current = issued_ids(content)
    for kind in sorted((set(issued) | set(retired)) - set(current)):
        report.error(f"identifiers:{kind}", f"unknown kind; the register knows {', '.join(current)}")
    for kind, ids in current.items():
        where = f"identifiers:{kind}"
        known, gone = set(issued.get(kind, [])), set(retired.get(kind, []))
        for value in ids:
            if value in gone:
                report.error(where, f"'{value}' is retired and cannot name another entry")
            elif value not in known:
                report.error(where, f"'{value}' is not registered (scripts/register_ids.py registers new entries)")
        for value in sorted(known - set(ids) - gone):
            report.error(where, f"'{value}' is registered but no entry has it: keep the identifier or retire it")
        for value in sorted(gone - known):
            report.error(where, f"'{value}' is retired but was never registered")


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
    # Every item whose change needs fresh paradata needs paradata at all: one list serves both rules.
    for item_id, (kind, _) in provenance_items(content).items():
        if not any(covered(p, item_id) for p in patterns):
            report.error(f"{kind}:{item_id}", "no provenance action covers this item")


def check_coherence(report: Report, content: dict[str, Any], graph: Graph, build_error: Exception | None) -> None:
    """The crate's identifiers hold together: one content ID names one entity (R1), references to snapshot records
    resolve (R4), and entries nothing uses are reported (R5). That no two entries describe one thing (R2, R3) is
    checked by scripts/check_duplicates.py."""
    # R1, read from the generator's own index of what each content ID names
    if build_error is not None:
        report.error("coherence", f"the crate could not be built to check identifiers: {build_error}")
        return
    for content_id, entity_ids in sorted(graph.index.items()):
        if len(set(entity_ids)) > 1:
            report.error(f"id:{content_id}", "names several entities: " + ", ".join(sorted(set(entity_ids))))

    # Every reference to one of the crate's own entities names an entity the crate has. A topic target
    # (`#resources?type=standard`) names its kind; check_links checks its facets and values.
    def targets(value: Any) -> Iterator[str]:
        if isinstance(value, list):
            for item in value:
                yield from targets(item)
        elif isinstance(value, dict):
            if set(value) == {"@id"}:
                yield str(value["@id"]).split("?")[0]
            else:
                for item in value.values():
                    yield from targets(item)

    for entity_id, entity in graph.entities.items():
        for key, value in entity.items():
            missing = sorted({target for target in targets(value) if target.startswith("#")} - graph.entities.keys())
            if key != "@id" and missing:
                report.error(f"crate:{entity_id}", f"{key} names {', '.join(missing)}, which the crate does not have")

    # R4, references to snapshot records resolve (one entry per thing is scripts/check_duplicates.py)
    dashboard = next((item for item in content["snapshots"] if item.get("fip") or item.get("resource")), {})
    org_ids = {alternate_id(org, "fip-dashboard") for org in dashboard.get("organization", [])}
    for organization in content["guide"].get("organization", []):
        if organization.get("fipDashboard") and organization["fipDashboard"] not in org_ids:
            report.error(
                f"organization:{organization['id']}",
                f"FIP Dashboard has no organisation '{organization['fipDashboard']}'",
            )

    # R5, entries nothing uses
    cited = {clause.get("source") for clause in content["ledger"]} | set(content["guide"]["guide"].get("isBasedOn", []))
    if content.get("model", {}).get("model"):
        cited.add(content["model"]["model"]["source"])
    cited |= {
        source for example in content.get("model", {}).get("example", []) for source in example.get("evidence", [])
    }
    cited |= {obj for action in content["provenance"] for obj in action.get("objects", [])}
    cited |= {
        source
        for item in [data["lifecycle"] for data in content.get("lifecycles", [])] + content.get("crosswalk", [])
        for source in (item.get("source"), item.get("czechSource"))
        if source
    }
    cited |= referenced(content)
    infrastructures = (content.get("infrastructures") or {}).get("infrastructures", {})
    cited |= {infrastructures.get("source"), infrastructures.get("namesSource")}
    cited |= {item.get("namesSource") for item in (content.get("infrastructures") or {}).get("infrastructure", [])}
    cited |= set(((content.get("node") or {}).get("node") or {}).get("sources", []))
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


def check_references(report: Report, content: dict[str, Any], targets: dict[str, str] | None) -> None:
    """A reference in text, [[id|phrase]], is well formed and names an entry the catalogue publishes, by a key
    scripts.build_crate.reference_targets derives from the catalogue identity, and a bilingual text refers to the
    same entries in both languages. When the crate could not be built, the entries cannot be resolved, so only the
    form and the language parity are checked."""
    known = set(targets) if targets is not None else None

    def entries(where: str, text: str) -> set[str]:
        if "[[" in REFERENCE.sub("", text) or "]]" in REFERENCE.sub("", text):
            report.error(where, "a reference is not well formed; write [[id|phrase]]")
        found = {match["id"] for match in REFERENCE.finditer(text)}
        if known is not None:
            for entry in sorted(found - known):
                report.error(where, f"refers to an unknown entry '{entry}'")
        return found

    for name, data in content.items():
        for path, key, value in walk(data, name):
            where = f"{path}.{key}" if path else key
            if is_text(value):
                found = {lang: entries(f"{where}.{lang}", str(value.get(lang, ""))) for lang in LANGS}
                if found["cs"] != found["en"]:
                    differ = sorted(found["cs"] ^ found["en"])
                    report.error(where, "the Czech and English texts refer to different entries: " + ", ".join(differ))
            elif isinstance(value, str) and key not in LANGS and ("[[" in value or "]]" in value):
                entries(where, value)


def check_infrastructures(report: Report, content: dict[str, Any]) -> None:
    """The large research infrastructures and the EOSC CZ Node (D-172, D-174): known vocabularies and sources, unique
    IDs, an operator relation only with its evidence and to a catalogue entry, and node members that name catalogue
    entries with a known role; a planned repository names its milestone."""
    guide = content["guide"]
    vocab = {
        kind: {item["id"] for item in guide.get(kind, [])}
        for kind in ("researchField", "infrastructurePhase", "infrastructureCharacter", "esfriStatus", "nodeRole")
    }
    sources = {source["id"] for source in content["sources"]}
    resources = {resource["id"] for resource in content["resources"]}
    repositories = {repository["id"] for repository in content["repositories"]}
    repositories |= {item["re3data"] for snapshot in content["snapshots"] for item in snapshot.get("repository", [])}
    fips = {
        alternate_id(item, "fip-dashboard") for snapshot in content["snapshots"] for item in snapshot.get("fip", [])
    }

    def names_entry(where: str, row: dict[str, Any]) -> None:
        if row.get("resource") and row["resource"] not in resources:
            report.error(where, f"unknown resource '{row['resource']}'")
        elif row.get("repository") and row["repository"] not in repositories:
            report.error(where, f"unknown repository '{row['repository']}' (a curated ID or a re3data record)")
        elif not row.get("resource") and not row.get("repository"):
            report.error(where, "names no catalogue entry (resource or repository)")

    data = content.get("infrastructures") or {}
    info = data.get("infrastructures", {})
    for key in ("source", "namesSource"):
        if info.get(key) and info[key] not in sources:
            report.error("infrastructures", f"unknown {key} '{info[key]}'")
    items = data.get("infrastructure", [])
    unique(report, "infrastructures", [item.get("id", "") for item in items], "infrastructure")
    for item in items:
        where = f"infrastructure:{item.get('id')}"
        for key in ("website", "logo"):
            value = item.get(key)
            if value is not None and not (key == "logo" and value is False) and not str(value).startswith("https://"):
                report.error(where, f"{key} must be an HTTPS address (or logo=false after reviewing available marks)")
        if item.get("namesSource") and item["namesSource"] not in sources:
            report.error(where, f"unknown namesSource '{item['namesSource']}'")
        for field, kind in (
            ("field", "researchField"),
            ("phase", "infrastructurePhase"),
            ("character", "infrastructureCharacter"),
        ):
            if item.get(field) not in vocab[kind]:
                report.error(where, f"unknown {field} '{item.get(field)}'")
        for status in item.get("esfri", []) + [row.get("esfri") for row in item.get("nodeOf", [])]:
            if status not in vocab["esfriStatus"]:
                report.error(where, f"unknown ESFRI status '{status}'")
        if item.get("fip") and item["fip"] not in fips:
            report.error(where, f"unknown FIP '{item['fip']}' in the FIP Dashboard snapshot")
        if not item.get("acronym") or not item.get("host"):
            report.error(where, "an infrastructure needs its acronym and its hosting institution from the roadmap")
        for row in item.get("operates", []):
            names_entry(where, row)
            if not str(row.get("evidence", "")).startswith("https://"):
                report.error(where, "an operator relation is recorded only with the source that states it (HTTPS)")
    ids = {item.get("id") for item in items}
    node = (content.get("node") or {}).get("node")
    if node:
        if node.get("operator") not in ids:
            report.error("node", f"the node's operator '{node.get('operator')}' is not a listed infrastructure")
        for source in node.get("sources", []):
            if source not in sources:
                report.error("node", f"unknown source '{source}'")
        members = (content.get("node") or {}).get("member", [])
        unique(report, "node", [str(row.get("resource") or row.get("repository")) for row in members], "member")
        for row in members:
            where = f"node member:{row.get('resource') or row.get('repository')}"
            names_entry(where, row)
            if row.get("role") not in vocab["nodeRole"]:
                report.error(where, f"unknown role '{row.get('role')}'")
            if row.get("role") == "repository" and not re.fullmatch(r"M\d{1,2}", str(row.get("milestone", ""))):
                report.error(where, "a repository's planned integration names its milestone (M6, M12)")
            if not row.get("locator"):
                report.error(where, "a member says where the charter lists it")


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
    records = content.get("repository_records", [])
    for record in records:
        if "name" in record:
            named.append((f"repository record:{record.get('re3data') or record.get('fipDashboard')}", record["name"]))

    # R6, Czech names have an English form
    for where, name in named:
        if isinstance(name, str) and CZECH_LETTERS.search(name):
            report.error(where, f"'{name}' is a Czech name with no English form; give it as a table with 'cs' and 'en'")

    # R6a, and where a Czech form exists, a curated name carries it: re3data tags a Czech name for the record, so the
    # entry or record annotation that names the repository gives its Czech name too (D-173).
    czech = {
        item["re3data"]: item["namesCs"]
        for snapshot in content["snapshots"]
        for item in snapshot.get("repository", [])
        if item.get("namesCs")
    }
    curated = [(f"repository:{item['id']}", item) for item in content["repositories"]]
    curated += [(f"repository record:{item.get('re3data')}", item) for item in records]
    for where, entry in curated:
        name = entry.get("name")
        if entry.get("re3data") in czech and name is not None and not (isinstance(name, dict) and name.get("cs")):
            report.error(
                where,
                f"re3data gives a Czech name ({czech[entry['re3data']][0]}); "
                "give the name as a table with its Czech form",
            )
        abbreviation = entry.get("abbreviation")
        if abbreviation is not None and not (
            isinstance(abbreviation, dict) and set(abbreviation) <= {"cs", "en"} and abbreviation
        ):
            report.error(where, "an abbreviation is a table of its forms by language ('cs', 'en')")
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
TOOL_GROUPS = ("tool", "guidance")  # the tools view's sections: interactive helpers, then guidance


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
            if page.get("group") not in TOOL_GROUPS:
                report.error(where, f"a tools page names its group, one of {', '.join(TOOL_GROUPS)}")
        for number, section in enumerate(page.get("section", []), start=1):
            require_text(report, f"{where}[{number}]", section.get("body"), "body")
            if not isinstance(section.get("details", False), bool):
                report.error(f"{where}[{number}]", "details must be true or false")
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
    # The build reads the Tag release decision from the release tag, not authored content.
    if guide.get("releaseStatus") is not None:
        report.error("guide", "releaseStatus is not authored in content; the build derives it from the release tag")
    require_text(report, "guide", guide.get("testingNotice"), "testingNotice")
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
    for field in ("publisher", "funder"):
        if guide.get(field) and guide[field] not in organization_ids:
            report.error("guide", f"unknown {field} organisation '{guide[field]}'")
    for person in guide_file.get("person", []):
        where = f"person:{person['id']}"
        for organization in person.get("affiliation", []):
            if organization not in organization_ids:
                report.error(where, f"unknown affiliation '{organization}'")
        # Reviewed identities for contributor matching (scripts/contributors.py); nothing is inferred from them.
        if "github" in person and not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", str(person["github"])):
            report.error(where, "github must be a GitHub account name")
        if not all(isinstance(name, str) and name.strip() for name in person.get("commitNames", [])):
            report.error(where, "commitNames must be the exact names the person commits under")
        if person.get("orcidOptOut") and person.get("orcid"):
            report.error(where, "a person who opted out of listing an ORCID iD carries none")
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
    # Every guide-specific term declares a broader established term or a recorded reason, and every published
    # guide term is defined in the vocabulary document served at the guide's address (design: group 21).
    for error in vocabulary_errors(guide):
        report.error("vocabulary", error)


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
        "repository_functions": {item["id"] for item in guide_file.get("repositoryFunction", [])},
        "stations": {data["station"]["id"] for data in content["stations"]},
        "terms": {term["id"] for term in content["glossary"].get("term", [])},
        "tests": {alternate_id(test, "fair-champion") for test in content["live"].get("champion", {}).get("test", [])},
        "people": {person["id"] for person in guide_file.get("person", [])},
        "instruments": {instrument["id"] for instrument in guide_file.get("instrument", [])},
        "freshness_days": int(guide_file["guide"].get("freshnessDays", 180)),
    }


def in_page_targets(content: dict[str, Any]) -> set[str]:
    targets = {"#path", "#ledger", "#repositories", "#resources", "#tests"}
    targets |= {f"#station-{data['station']['id']}" for data in content["stations"]}
    targets |= {f"#check-{data['check']['id']}" for data in content["checks"]}
    targets |= {f"#page-{page['id']}" for page in content["pages"]}
    targets |= {f"#resource-{resource['id']}" for resource in content["resources"]}
    return targets


def topic_targets(vocab: dict[str, Any]) -> dict[str, dict[str, set[str]]]:
    """The catalogue kinds a link may open narrowed to a topic, with the facets and values each accepts."""
    stations = set(vocab["stations"])
    return {
        "#resources": {"type": set(vocab["resource_types"]), "station": stations},
        "#repositories": {"function": set(vocab["repository_functions"]), "station": stations},
    }


def check(content: dict[str, Any], root: Path, today: date | None = None) -> Report:
    report = Report()
    vocab = vocabularies(content)
    # The crate is built once: coherence reads its identifier index, and the reference targets come from the same
    # catalogue identity, so a text reference and the build agree on what a reference may name.
    graph = Graph()
    build_error: Exception | None = None
    targets: dict[str, str] | None = None
    try:
        build_crate(content, graph)
        targets = reference_targets(content, graph)
    except (ContentError, KeyError, TypeError, ValueError) as error:
        build_error = error
    check_texts(report, content)
    check_links(report, content, in_page_targets(content), topic_targets(vocab))
    check_sources(report, content)
    check_model(report, content, vocab, today or date.today())
    check_lifecycles(report, content)
    check_guide_name(report, content)
    check_type_crosswalk(report, content)
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
    check_corrections(report, content)
    check_infrastructures(report, content)
    check_fip_dashboard(report, content, vocab)
    check_callouts(report, content, vocab)
    check_live(report, content, vocab, root)
    check_self_check_inputs(report, content)
    check_icons_and_tasks(report, content, root, vocab)
    check_provenance(report, content, vocab)
    check_identifiers(report, content)
    check_coherence(report, content, graph, build_error)
    check_names(report, content)
    check_references(report, content, targets)
    check_pages_and_ui(report, content)
    check_guide(report, content, vocab, root)
    check_no_build_output(report, root)
    return report


# ---------------------------------------------------------------------------
# Provenance freshness against a git revision


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, encoding="utf-8", check=True)
    return result.stdout


def provider_criteria(content: dict[str, Any]) -> dict[str, Any]:
    """External evaluators' criteria by content ID (`provider:<provider>.<metric>`), each with the provider's
    reviewed versions and its mappings, so a changed mapping or reviewed version needs that criterion's paradata."""
    criteria = {}
    for provider in content["live"].get("provider", []):
        for metric in provider.get("metric", []):
            mappings = [mapping for mapping in provider.get("mapping", []) if mapping.get("metric") == metric.get("id")]
            criteria[f"provider:{provider['id']}.{metric['id']}"] = {
                "metric": metric,
                "mappings": mappings,
                "reviewed": provider.get("reviewed", []),
            }
    return criteria


def provenance_items(content: dict[str, Any]) -> dict[str, tuple[str, Any]]:
    """Every item provenance must cover, with its kind and content: the guide's metadata, clauses, advice, questions,
    resources, sources, pages, curated repositories, callouts and their items, tests, external evaluators' criteria,
    organisations, infrastructures, the node, the model and the life-cycle models. Mandatory
    coverage and freshness both read this one list, so a kind whose changes are compared is never a kind no action has
    to cover."""
    items: dict[str, tuple[str, Any]] = {"guide": ("guide", content["guide"]["guide"])}
    for clause in content["ledger"]:
        items[clause["id"]] = ("clause", clause)
    for data in content["stations"]:
        for advice in data.get("advice", []):
            items[advice["id"]] = ("advice", advice)
    for data in content["checks"]:
        for item in data.get("item", []):
            items[item["id"]] = ("item", item)
    for resource in content["resources"]:
        items[resource["id"]] = ("resource", resource)
    for source in content["sources"]:
        items[source["id"]] = ("source", source)
    for page in content["pages"]:
        items[f"page:{page['id']}"] = ("page", page)
    for repository in content["repositories"]:
        items[repository["id"]] = ("repository", repository)
    for callout in content["callouts"]:
        items[f"callout:{callout['id']}"] = ("callout", callout)
        for item in callout.get("item", []):
            items[f"callout.{callout['id']}.{item['id']}"] = ("callout item", item)
    for test in content["live"].get("test", []) + content["live"].get("champion", {}).get("test", []):
        items[f"test:{test['id']}"] = ("test", test)
    items |= {key: ("criterion", value) for key, value in provider_criteria(content).items()}
    for organization in content["guide"].get("organization", []):
        items["organization:" + organization["id"]] = ("organization", organization)
    items |= {key: ("model", value) for key, value in model_items(content).items()}
    items |= {key: ("lifecycle", value) for key, value in lifecycle_items(content).items()}
    for item in (content.get("infrastructures") or {}).get("infrastructure", []):
        items[f"infrastructure:{item['id']}"] = ("infrastructure", item)
    if (content.get("node") or {}).get("node"):
        items["node:eosc-cz-node"] = ("node", content["node"])
    # Association changes alter the meaning of the mapped item and need that item's fresh paradata too.
    for association in content.get("model", {}).get("association", []):
        target = association["target"]
        kind, base = items.get(target, (None, None))
        if base is None:
            kind, base = "source", next((item for item in content["sources"] if item["id"] == target), None)
        items[target] = (kind, {"item": base, "modelAssociation": association})
    return items


def item_fingerprints(content: dict[str, Any]) -> dict[str, str]:
    """Canonical JSON of every item that provenance must cover."""
    return {
        key: json.dumps(value, sort_keys=True, default=str) for key, (_, value) in provenance_items(content).items()
    }


def default_base(root: Path) -> str:
    """The branch a pull request is compared with: the remote's default branch."""
    try:
        return git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    except subprocess.CalledProcessError:
        return "origin/main"


def merge_base(root: Path, ref: str) -> str:
    """Where the checked-out branch left `ref`. A local run and a pull-request run judge the same changes because both
    compare with this point; git failing to find it is an error, never a quieter base."""
    sha = git(root, "merge-base", ref, "HEAD").strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha):
        raise ContentError(f"no merge base with {ref}")
    return sha


def fresh_actions(actions: list[dict[str, Any]], base_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The actions that can cover a change since the base: added since then, or extended with a later `endTime`.
    History decides, not the clock, so a base that moves on after the work ended leaves a correct action fresh."""
    before = {action["id"]: action for action in base_actions if action.get("id")}
    fresh = []
    for action in actions:
        end = action.get("endTime")
        if not isinstance(end, datetime):
            continue
        earlier = before.get(action["id"]) if action.get("id") else None
        if earlier is None or not isinstance(earlier.get("endTime"), datetime) or end > earlier["endTime"]:
            fresh.append(action)
    return fresh


def check_freshness(report: Report, content: dict[str, Any], root: Path, base: str) -> None:
    sha = merge_base(root, base)
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        for path in git(root, "ls-tree", "-r", "--name-only", sha, "content/").split():
            target = temp_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(git(root, "show", f"{sha}:{path}"), encoding="utf-8")
        earlier = load_content(temp_root / "content") if (temp_root / "content" / "guide.toml").exists() else None
    before = item_fingerprints(earlier) if earlier else {}
    fresh = fresh_actions(content["provenance"], earlier["provenance"] if earlier else [])
    after = item_fingerprints(content)
    since = base if sha.startswith(base) else f"{base} (merge base {sha[:12]})"
    for item_id, fingerprint in after.items():
        if before.get(item_id) == fingerprint:
            continue
        if not any(covered(pattern, item_id) for action in fresh for pattern in action.get("results", [])):
            report.error(
                f"{item_id}",
                f"changed since {since} but no provenance action added since then, or extended with a later "
                "endTime, covers it",
            )


# ---------------------------------------------------------------------------
# Entry point


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this repository)")
    parser.add_argument(
        "--base", help="git revision; items changed since then need a provenance action added or extended since then"
    )
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
