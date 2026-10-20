#!/usr/bin/env python3
"""Inventory content integrity, original-source coverage and a check run without network requests.

Writes ``health.json``, a self-contained ``index.html`` dashboard and ``summary.md`` suitable for a
GitHub Actions step summary. Originals are counted per clause and per cited item: an original on one
clause does not imply that all the item's citations have originals. Missing passages are review
information, not failed requirements or proof that a suitable original exists. Only explicitly
reviewed source-link-only questions are labelled as such. Live availability stays unchecked.

    python scripts/check_health.py [--output .cache/health] [--previous-report path/to/health.json]

Exit status 1 means an offline integrity check failed; coverage gaps alone do not fail the run.
FAIR_GUIDE_CHECK_REVISION identifies the source checked when it differs from a workflow's GITHUB_SHA,
as for a default-branch preview built during a release-tag deployment.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import build_crate
import check_content

ROOT = Path(__file__).resolve().parent.parent
FORMAT_VERSION = 1
# Reviewed during the question-source pass; these criteria are the guide's practical recommendations,
# rather than requirements imposed by the cited service or registry. No advice exception is inferred.
REVIEWED_SOURCE_LINK_BASIS = {
    "institution.24": "Institutional storage provision; the cited service does not impose this guide recommendation.",
    "maturity.18": "Registration in two independent registries; the cited schema does not impose this recommendation.",
}


def text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("en") or value.get("cs") or "")
    return str(value or "")


def bilingual(value: Any) -> bool:
    return isinstance(value, dict) and all(
        isinstance(value.get(lang), str) and value[lang].strip() for lang in ("cs", "en")
    )


def https(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password


def iso_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def source_entries(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = {item["id"]: dict(item) for item in content["sources"]}
    for item in content["resources"]:
        if item.get("citation"):
            entries[item["id"]] = {**item["citation"], "id": item["id"], "url": item["url"]}
    return entries


def missing_links(content: dict[str, Any], graph: build_crate.Graph | None = None) -> list[dict[str, str]]:
    """Rank useful editorial hints, retaining originals and never changing prose or integrity outcomes."""
    if graph is None:
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
    targets = build_crate.reference_targets(content, graph)
    addresses = {
        key: entity["catalogueAddress"] for key, entity in graph.entities.items() if entity.get("catalogueAddress")
    }
    generic = {
        "data",
        "metadata",
        "description",
        "popis",
        "repository",
        "repozitar",
        "repozitář",
        "access",
        "přístup",
        "licence",
        "license",
        "plan",
        "plán",
        "planning",
        "plánování",
        "check",
        "kontrola",
        "analysis",
        "analýza",
        "processing",
        "zpracování",
        "publication",
        "publikace",
        "sharing",
        "sdílení",
        "community",
        "komunita",
        "policy",
        "politika",
        "support",
        "podpora",
        "fair",
        "open",
        "guide",
        "průvodce",
        "service",
        "služba",
        "standard",
        "sources",
        "zdroje",
        "test",
        "research",
        "výzkum",
        "version",
        "verze",
        "title",
        "název",
        "rights",
        "práva",
        "security",
        "quality",
        "infrastructure",
        "infrastruktura",
        "provenance",
        "původ",
        "process",
        "publish",
        "preserve",
        "reuse",
        "share",
        "store",
        "core",
        "chat",
        "api",
    }
    names: dict[tuple[str, str, str], str] = {}

    def add(entity_id: str, label: str, language: str, basis: str) -> None:
        label = label.strip()
        if entity_id not in addresses or len(label) < 3 or label.casefold() in generic or "\n" in label:
            return
        if len(label.split()) == 1 and label.islower():
            return  # Common nouns need an explicit, specific phrase, not a blanket glossary link.
        # A criterion, model layer, stage or profile name often describes the subject of ordinary prose.
        # "NRP" does not by itself name the NRP FIP, nor "rich metadata" the F2 catalogue entry.
        if (
            addresses[entity_id].split("/")[0] in {"cl", "pr", "model", "life", "check", "fip", "test"}
            and len(label.split()) < 3
        ):
            return
        if basis == "form used in an authored reference" and not any(char.isupper() for char in label):
            return  # Linked common phrases are not aliases for the named tool or service everywhere else.
        names[(entity_id, label, language)] = basis

    rows = build_crate.catalogue_records(content)
    for entity_id in addresses:
        entity = graph.entities[entity_id]
        for field in ("name", "alternateName"):
            for value in build_crate.as_list(entity.get(field)):
                add(
                    entity_id,
                    value.get("@value", "") if isinstance(value, dict) else str(value),
                    value.get("@language", "und") if isinstance(value, dict) else "und",
                    "catalogue name",
                )
        for language, labels in rows.get(entity_id, {}).get("linkNames", {}).items():
            for label in labels:
                add(entity_id, label, language, "reviewed name variant")
    sections = ("pages", "stations", "checks", "callouts", "resources")
    prose_keys = {"text", "body", "intro", "description", "hint", "help", "note", "detail"}
    prose = []
    for section in sections:
        for path, key, value in check_content.walk(content.get(section, []), section):
            field = path.rsplit(".", 1)[-1] if key in ("cs", "en") else key
            if (
                field not in prose_keys
                or not isinstance(value, str)
                or any(part in path.lower() for part in ("original", "guidance", "quote", "definition"))
            ):
                continue
            # A callout item with a URL is already rendered as one complete external link.
            callout = re.match(r"callouts\[([^]]+)\]\.item\[([^]]+)\]", path)
            if callout and any(
                item.get("url")
                for group in content["callouts"]
                if group["id"] == callout[1]
                for item in group.get("item", [])
                if item["id"] == callout[2]
            ):
                continue
            language = key if key in ("cs", "en") else "und"
            prose.append((path, key, value, language))
            # Authored references provide reviewed inflected Czech and abbreviated forms without a stemmer.
            for match in build_crate.REFERENCE.finditer(value):
                add(targets.get(match["id"], ""), match["phrase"], language, "form used in an authored reference")
    patterns = [
        (
            entity_id,
            label,
            language,
            basis,
            re.compile(r"(?<!\w)" + re.escape(label) + r"(?!\w)", 0 if label.isupper() and len(label) <= 5 else re.I),
        )
        for (entity_id, label, language), basis in names.items()
    ]
    result = []
    for path, key, value, language in prose:
        linked = {targets.get(match["id"]) for match in build_crate.REFERENCE.finditer(value)}
        unlinked = build_crate.REFERENCE.sub(lambda match: " " * len(match[0]), value)
        unlinked = re.sub(r"https?://\S+|`[^`]*`", lambda match: " " * len(match[0]), unlinked)
        owners = [entity_id for token in re.findall(r"\[([^]]+)\]", path) for entity_id in graph.index.get(token, [])]
        related = {
            ref.get("@id")
            for owner in owners
            for values in graph.entities.get(owner, {}).values()
            for ref in build_crate.as_list(values)
            if isinstance(ref, dict) and "@id" in ref
        }
        candidates = []
        folded = unlinked.casefold()
        for entity_id, label, name_language, basis, pattern in patterns:
            if (
                name_language not in ("und", language)
                or entity_id in linked
                or entity_id in owners
                or label.casefold() not in folded
            ):
                continue
            native = graph.entities[entity_id].get("identifier")
            if isinstance(native, str) and f"[{native}]" in path:
                continue
            for match in pattern.finditer(unlinked):
                score = 85 if basis != "catalogue name" else 80
                if addresses[entity_id].startswith("term/"):
                    score -= 10
                if entity_id in related:
                    score += 15
                candidates.append((match.start(), match.end(), score, entity_id, label, basis))
        candidates.sort(key=lambda item: (-(item[1] - item[0]), -item[2], item[0], item[3]))
        covered: list[tuple[int, int]] = []
        emitted = set()
        for start, end, initial_score, entity_id, label, basis in candidates:
            score = initial_score
            if entity_id in emitted or any(start < last and end > first for first, last in covered):
                continue
            peers = {item[3] for item in candidates if item[0] == start and item[1] == end and item[2] == score}
            reason = basis + ("; associated with this record" if entity_id in related else "")
            if len(peers) > 1:
                score -= 25
                reason += "; ambiguous name: review " + ", ".join(sorted(addresses[peer] for peer in peers))
            covered.append((start, end))
            emitted.add(entity_id)
            phrase = value[start:end]
            result.append(
                {
                    "path": f"{path}.{key}",
                    "language": language,
                    "text": value,
                    "entry": entity_id,
                    "entry_name": label,
                    "address": addresses[entity_id],
                    "excerpt": ("…" if start > 65 else "")
                    + value[max(0, start - 65) : min(len(value), end + 95)]
                    + ("…" if end + 95 < len(value) else ""),
                    "match": phrase,
                    "reference": "[[" + addresses[entity_id] + "|" + phrase + "]]",
                    "confidence": "high" if score >= 80 else "review",
                    "score": str(score),
                    "reason": reason,
                }
            )
    return sorted(result, key=lambda item: (-int(item["score"]), item["path"], item["entry"]))


def cited_clauses(item: dict[str, Any]) -> list[str]:
    return list(dict.fromkeys(([item["requirement"]] if item.get("requirement") else []) + item.get("sources", [])))


def review_links(content: dict[str, Any], candidates: list[dict[str, str]]) -> dict[str, Any]:
    """Apply exact, dated editorial decisions; changed text or targets reopen the suggestion."""
    pending = {(row["path"], row["address"]): row for row in candidates}
    reviewed, stale, issues = [], [], []
    seen = set()
    for decision in content.get("link_reviews", []):
        key = (decision.get("path"), decision.get("address"))
        if (
            not all(isinstance(value, str) and value for value in key)
            or any("*" in value for value in key)
            or not isinstance(decision.get("reason"), str)
            or not decision["reason"].strip()
            or iso_date(decision.get("reviewed")) is None
            or not re.fullmatch(r"[0-9a-f]{64}", str(decision.get("sha256", "")))
            or key in seen
        ):
            issues.append(f"Invalid or duplicate link review: {key}")
            continue
        seen.add(key)
        candidate = pending.get(key)
        if candidate and sha256(candidate["text"].encode("utf-8")).hexdigest() == decision["sha256"]:
            reviewed.append({**candidate, "review_reason": decision["reason"], "reviewed": str(decision["reviewed"])})
            del pending[key]
        else:
            stale.append({**decision, "reviewed": str(decision["reviewed"])})
    return {"pending": list(pending.values()), "reviewed": reviewed, "stale": stale, "issues": issues}


def original_coverage(content: dict[str, Any]) -> dict[str, Any]:
    """Keep the complete missing-clause inventory and the exact citations behind every coverage count."""
    ledger = {item["id"]: item for item in content["ledger"]}
    sources = source_entries(content)
    clauses = []
    for identifier, clause in sorted(ledger.items()):
        source = sources.get(clause["source"], {})
        clauses.append(
            {
                "id": identifier,
                "source": clause["source"],
                "source_url": source.get("url", ""),
                "source_title": text(source.get("title")),
                "source_type": source.get("type", ""),
                "source_version": source.get("version"),
                "locator": clause.get("locator", ""),
                "guide_text": clause.get("text", {}),
                "kind": clause.get("kind", ""),
                "actor": clause.get("actor", ""),
                "status": clause.get("status", "current"),
                "has_original": bool(clause.get("guidance", "").strip()),
                "original_language": clause.get("guidanceLanguage", "en") if clause.get("guidance") else None,
            }
        )
    clause_index = {item["id"]: item for item in clauses}
    coverage: dict[str, list[dict[str, Any]]] = {"questions": [], "advice": []}
    for kind, parents, key in (("questions", content["checks"], "item"), ("advice", content["stations"], "advice")):
        for parent in parents:
            for item in parent.get(key, []):
                citations = cited_clauses(item)
                originals = [
                    identifier for identifier in citations if clause_index.get(identifier, {}).get("has_original")
                ]
                missing = [identifier for identifier in citations if identifier not in originals]
                reviewed = REVIEWED_SOURCE_LINK_BASIS.get(item["id"]) if kind == "questions" and not originals else None
                status = "complete" if originals and not missing else "partial" if originals else "no_original"
                if reviewed:
                    status = "reviewed_source_links"
                coverage[kind].append(
                    {
                        "id": item["id"],
                        "parent": parent["check" if key == "item" else "station"]["id"],
                        "guide_text": item.get("text")
                        or item.get("statement")
                        or ledger.get(item.get("requirement"), {}).get("text", {}),
                        "kind": item.get(
                            "kind", "context" if item.get("context") else "question" if key == "item" else "advice"
                        ),
                        "lens": item.get("lens"),
                        "level": item.get("level"),
                        "citations": citations,
                        "originals": originals,
                        "missing_originals": missing,
                        "missing_sources": sorted(
                            {ledger[identifier]["source"] for identifier in missing if identifier in ledger}
                        ),
                        "status": status,
                        "reviewed_basis": reviewed,
                    }
                )
        coverage[kind].sort(key=lambda item: item["id"])

    by_source = []
    for identifier, source in sorted(sources.items()):
        associated = [clause for clause in clauses if clause["source"] == identifier]
        if not associated:
            continue
        absent = {clause["id"] for clause in associated if not clause["has_original"]}
        row = {
            "id": identifier,
            "title": text(source.get("title")),
            "url": source.get("url", ""),
            "type": source.get("type", ""),
            "clauses": len(associated),
            "with_original": sum(clause["has_original"] for clause in associated),
            "missing_clauses": sorted(absent),
        }
        for kind, items in coverage.items():
            relevant = [item for item in items if absent.intersection(item["citations"])]
            row[kind + "_without_original"] = [item["id"] for item in relevant if not item["originals"]]
            row[kind + "_with_other_original"] = [item["id"] for item in relevant if item["originals"]]
        by_source.append(row)
    counts = {"clauses": {"total": len(clauses), "with_original": sum(item["has_original"] for item in clauses)}}
    for kind, items in coverage.items():
        counts[kind] = {
            "total": len(items),
            "with_original": sum(bool(item["originals"]) for item in items),
            **Counter(item["status"] for item in items),
        }
    return {"counts": counts, "clauses": clauses, **coverage, "by_source": by_source}


def integrity(content: dict[str, Any], root: Path, today: date) -> list[dict[str, Any]]:
    """Small named checks per item type, complementing the full content and duplicate validators."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ledger = {item["id"] for item in content["ledger"]}
    sources = source_entries(content)
    stations = {item["station"]["id"] for item in content["stations"]}

    def add(
        kind: str, item: dict[str, Any], conditions: list[tuple[str, bool]], notes: list[str] | None = None
    ) -> None:
        issues = [name for name, valid in conditions if not valid]
        groups[kind].append(
            {
                "id": str(item.get("id", "")),
                "name": text(item.get("name") or item.get("title") or item.get("label")),
                "status": "failed" if issues else "passed",
                "checks": [name for name, _ in conditions],
                "issues": issues,
                "notes": notes or [],
                "recorded_status": item.get("status") or item.get("health"),
                "recorded_date": str(item.get("asOf") or item.get("retrieved") or "") or None,
            }
        )

    def links(item: dict[str, Any]) -> tuple[str, bool]:
        citations = cited_clauses(item)
        return "published-clause citations resolve", bool(citations) and all(
            identifier in ledger for identifier in citations
        )

    def dated(item: dict[str, Any], key: str = "asOf") -> tuple[list[tuple[str, bool]], list[str]]:
        observed = iso_date(item.get(key))
        checks = [("dated status is valid and not in the future", observed is not None and observed <= today)]
        notes = [f"Recorded date: {observed.isoformat()} ({(today - observed).days} days old)."] if observed else []
        if observed and (today - observed).days > 90:
            notes.append("The recorded date is over 90 days old; review freshness. Availability was not tested.")
        return checks, notes

    for item in sources.values():
        preparation = item.get("id") == "layers-seams-manuscript" and item.get("preparationStatus") == "in-preparation"
        citation_check = check_content.Report()
        check_content.check_citation(citation_check, "source", item, own_url=False)
        add(
            "cited sources",
            item,
            [
                ("source title exists", bool(text(item.get("title")))),
                ("HTTPS source link or approved conceptual manuscript", preparation or https(item.get("url"))),
                ("source language is declared", item.get("inLanguage") in ("cs", "en")),
                ("source publication or preparation scope is valid", not citation_check.errors),
            ],
        )
    for item in content["ledger"]:
        checks = [
            (
                "published source resolves",
                item.get("source") in sources and not sources[item["source"]].get("preparationStatus"),
            ),
            ("bilingual guide wording", bilingual(item.get("text"))),
        ]
        if item.get("guidance"):
            checks += [
                ("original language is supported", item.get("guidanceLanguage", "en") in ("cs", "en")),
                ("original is non-empty", bool(item["guidance"].strip())),
            ]
        add("ledger clauses", item, checks)
    model = content.get("model", {})
    if model:
        validation = check_content.Report()
        check_content.check_model(validation, content, check_content.vocabularies(content), today)
        for identifier, item in check_content.model_items(content).items():
            if identifier == "model:layers-seams":
                related = validation.errors
            elif identifier == "model:worked-example":
                related = [error for error in validation.errors if error.startswith("model:worked-example:")]
            elif identifier.startswith("context:"):
                where = "model:" + identifier.replace(":", ".")
                related = [error for error in validation.errors if error.startswith(where + ":")]
            else:
                where = "model:" + identifier
                related = [error for error in validation.errors if error.startswith(where + ":")]
            add(
                "implementation model",
                item | {"id": item.get("id", identifier) if identifier.startswith("model:") else identifier},
                [("model scope, bilingual descriptions, references and dated evidence are valid", not related)],
                related,
            )
        for item in model.get("association", []):
            where = f"model:association.{item.get('target')}"
            related = [error for error in validation.errors if error.startswith(where + ":")]
            add(
                "model associations",
                {"id": item.get("target")},
                [("explicit target and model references resolve", not related)],
                related,
            )
    for parent in content["stations"]:
        item = parent["station"]
        add(
            "stations",
            item,
            [
                ("bilingual name and title", bilingual(item.get("name")) and bilingual(item.get("title"))),
                ("advice exists", bool(parent.get("advice"))),
            ],
        )
        for advice in parent.get("advice", []):
            add("station advice", advice, [("bilingual advice", bilingual(advice.get("text"))), links(advice)])
    for parent in content["checks"]:
        item = parent["check"]
        add(
            "self-checks",
            item,
            [
                ("bilingual name and scope", bilingual(item.get("name")) and bilingual(item.get("description"))),
                ("questions or source context exist", bool(parent.get("item"))),
            ],
        )
        for question in parent.get("item", []):
            requirement = next(
                (clause for clause in content["ledger"] if clause["id"] == question.get("requirement")), {}
            )
            wording = question.get("statement") or requirement.get("text")
            add(
                "questions and source context",
                question,
                [
                    ("bilingual question or inherited requirement", bilingual(wording)),
                    (
                        "FAIR links use existing principles",
                        all(
                            code in {entry["id"] for entry in content["principles"]}
                            for code in question.get("principles", [])
                        ),
                    ),
                    links(question),
                    (
                        "source context is not automatically answered",
                        not (question.get("context") and question.get("prefill")),
                    ),
                ],
            )
    for item in content["resources"]:
        checks, notes = dated(item)
        add(
            "resources: " + item["type"],
            item,
            [
                ("name exists", bool(text(item.get("name")))),
                ("bilingual purpose", bilingual(item.get("description"))),
                ("HTTPS resource link", https(item.get("url"))),
                ("station links resolve", all(identifier in stations for identifier in item.get("stations", []))),
                (
                    "service status uses the guide vocabulary",
                    item.get("status") in {entry["id"] for entry in content["guide"]["status"]},
                ),
                *checks,
            ],
            notes,
        )
    for item in content["repositories"]:
        checks, notes = dated(item)
        add(
            "curated repositories",
            item,
            [
                ("name exists", bool(text(item.get("name")))),
                ("HTTPS repository link", https(item.get("url"))),
                ("deposit/discovery purpose exists", bool(item.get("functions"))),
                *checks,
            ],
            notes,
        )
    for snapshot in content["snapshots"]:
        item = {"id": snapshot["snapshot"]["source"], **snapshot["snapshot"]}
        checks, notes = dated(item, "retrieved")
        add(
            "registry snapshots",
            item,
            [("HTTPS upstream link", https(item.get("url"))), *checks],
            notes + ["Snapshot content is offline evidence, not a current live-service result."],
        )
        for kind, field in (
            ("snapshot resources", "resource"),
            ("snapshot organisations", "organization"),
            ("snapshot profiles", "fip"),
            ("snapshot repositories", "repository"),
        ):
            for entity in snapshot.get(field, []):
                add(
                    kind,
                    entity,
                    [
                        ("identity exists", bool(entity.get("id"))),
                        ("name exists", bool(text(entity.get("name") or entity.get("label") or entity.get("title")))),
                    ],
                )
                if entity.get("url"):
                    groups[kind][-1]["checks"].append("HTTPS upstream item link")
                    if not https(entity["url"]):
                        groups[kind][-1]["issues"].append("HTTPS upstream item link")
                        groups[kind][-1]["status"] = "failed"
    for item in content["guide"].get("organization", []):
        add(
            "guide organisations",
            item,
            [("name exists", bool(text(item.get("name")))), ("HTTPS organisation link", https(item.get("url")))],
        )
    for item in content["glossary"].get("term", []):
        add(
            "glossary terms",
            item,
            [("bilingual label", bilingual(item.get("label"))), ("HTTPS term link", https(item.get("url")))],
        )
    for item in content["pages"]:
        add(
            "guide pages",
            item,
            [("bilingual title", bilingual(item.get("title"))), ("sections exist", bool(item.get("section")))],
        )
    for item in content["callouts"]:
        add(
            "callouts",
            item,
            [
                ("bilingual title and introduction", bilingual(item.get("title")) and bilingual(item.get("intro"))),
                ("station links resolve", all(identifier in stations for identifier in item.get("stations", []))),
            ],
        )
    for item in content["principles"]:
        add(
            "FAIR principles",
            item,
            [("bilingual label and statement", bilingual(item.get("label")) and bilingual(item.get("statement")))],
        )
    for item in content["live"].get("connector", []):
        notes = (
            ["Browser access is explicitly disabled."]
            if item.get("browserAccess") is False
            else ["Browser access and live availability were not probed in this inventory."]
        )
        add(
            "connectors",
            item,
            [
                ("name and purpose exist", bool(item.get("name")) and bool(item.get("purpose"))),
                ("HTTPS origin", https(item.get("origin"))),
            ],
            notes,
        )
    champion = content["live"].get("champion", {})
    for item in champion.get("test", []):
        checks, notes = dated(item)
        endpoint = item.get("endpoint") or (str(champion.get("endpoint", "")).rstrip("/") + "/" + item["id"])
        add(
            "remote automated tests",
            item,
            [
                ("bilingual name", bilingual(item.get("label"))),
                ("bilingual test purpose", bilingual(item.get("description"))),
                ("HTTPS invocation endpoint", https(endpoint)),
                ("HTTPS test documentation", https(champion.get("documentation"))),
                *checks,
            ],
            notes + ["Recorded service health is historical; this inventory did not invoke the test."],
        )
    questions = {item["id"] for parent in content["checks"] for item in parent.get("item", [])}
    for item in content["live"].get("test", []):
        script = item.get("script", "")
        documentation = str(item.get("documentation", "")).split("#", 1)[0]
        add(
            "guide automated tests",
            item,
            [
                ("bilingual name and purpose", bilingual(item.get("label")) and bilingual(item.get("description"))),
                ("question identity resolves", item.get("question") in questions),
                (
                    "JavaScript implementation attachment exists",
                    local_file(root, script) and Path(script).suffix == ".js",
                ),
                ("documentation attachment exists", local_file(root, documentation)),
                ("named invocation exists", bool(item.get("entryPoint"))),
            ],
            ["This checks the record and attachments; executing its logic is a separate assessment check."],
        )
    external_types = {
        "cited sources",
        "curated repositories",
        "registry snapshots",
        "snapshot resources",
        "snapshot organisations",
        "snapshot profiles",
        "snapshot repositories",
        "glossary terms",
        "guide organisations",
        "remote automated tests",
        "connectors",
    }
    return [
        {
            "type": kind,
            "scope": "Offline record integrity; live availability unchecked"
            if kind in external_types or kind.startswith("resources:")
            else "Offline guide structure and references",
            "live_availability": "unchecked"
            if kind in external_types or kind.startswith("resources:")
            else "not_applicable",
            "count": len(items),
            "passed": sum(item["status"] == "passed" for item in items),
            "failed": sum(item["status"] == "failed" for item in items),
            "items": sorted(items, key=lambda item: item["id"]),
        }
        for kind, items in sorted(groups.items())
    ]


def local_file(root: Path, value: Any) -> bool:
    if not isinstance(value, str) or not value or urlparse(value).scheme:
        return False
    path = (root / value).resolve()
    return path.is_relative_to(root.resolve()) and path.is_file()


def compare(report: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if not previous:
        return {"available": False, "reason": "No previous report supplied; this run establishes no coverage trend."}
    if previous.get("format_version") != FORMAT_VERSION:
        return {"available": False, "reason": "Previous report uses an incompatible format."}
    trend: dict[str, Any] = {"available": True, "previous_generated_at": previous.get("generated_at"), "coverage": {}}
    old = previous.get("original_coverage", {})
    current = report["original_coverage"]
    for kind in ("clauses", "questions", "advice"):
        key = "has_original" if kind == "clauses" else "originals"
        prior_ids = {item["id"] for item in old.get(kind, [])}
        current_ids = {item["id"] for item in current[kind]}
        before = {item["id"] for item in old.get(kind, []) if not item.get(key)}
        after = {item["id"] for item in current[kind] if not item.get(key)}
        trend["coverage"][kind] = {
            "new_missing": sorted(after - before),
            "resolved_missing": sorted((before - after) & current_ids),
            "added_items": sorted(current_ids - prior_ids),
            "removed_items": sorted(prior_ids - current_ids),
            "with_original_delta": current["counts"][kind]["with_original"]
            - old.get("counts", {}).get(kind, {}).get("with_original", 0),
        }
    prior_jobs = {item["name"]: item["status"] for item in previous.get("run", {}).get("jobs", [])}
    trend["job_changes"] = [
        {"name": item["name"], "previous": prior_jobs.get(item["name"], "not_recorded"), "current": item["status"]}
        for item in report.get("run", {}).get("jobs", [])
        if prior_jobs.get(item["name"], "not_recorded") != item["status"]
    ]
    return trend


def make_report(
    content: dict[str, Any],
    root: Path = ROOT,
    *,
    today: date | None = None,
    run: dict[str, Any] | None = None,
    previous: dict[str, Any] | None = None,
    graph: build_crate.Graph | None = None,
) -> dict[str, Any]:
    link_review = review_links(content, missing_links(content, graph))
    report = {
        "format_version": FORMAT_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": (
            "Offline authored-content integrity and original-passage inventory; "
            "no live requests or conformance verdict."
        ),
        "revision": os.environ.get("FAIR_GUIDE_CHECK_REVISION") or os.environ.get("GITHUB_SHA"),
        "build": build_crate.build_identity_facts(),
        "run_url": os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        + "/"
        + os.environ["GITHUB_REPOSITORY"]
        + "/actions/runs/"
        + os.environ["GITHUB_RUN_ID"]
        if all(os.environ.get(key) for key in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
        else None,
        "live_availability": {
            "status": "unchecked",
            "reason": "A dated resource or test status is not a current live availability probe; the scheduled live "
            "watch (scripts/watch_sources.py) observes services separately.",
        },
        "integrity": integrity(content, root, today or date.today()),
        "original_coverage": original_coverage(content),
        "missing_links": link_review.pop("pending"),
        "missing_link_review": link_review,
        "run": run or {"status": "not_run", "jobs": [], "reason": "Only the offline health inventory was requested."},
    }
    if link_review["issues"]:
        report["integrity"].append(
            {
                "type": "link review decisions",
                "count": 1,
                "passed": 0,
                "failed": 1,
                "items": [
                    {
                        "id": "link-reviews",
                        "name": "Link review decisions",
                        "status": "failed",
                        "checks": ["exact, dated, unique decisions with reasons"],
                        "issues": link_review["issues"],
                        "notes": [],
                    }
                ],
            }
        )
    report["integrity_failed"] = sum(group["failed"] for group in report["integrity"])
    report["trend"] = compare(report, previous)
    return report


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def unreadable_report(error: str, run: dict[str, Any]) -> dict[str, Any]:
    """A malformed content tree must still leave a diagnostic artifact after a failed build."""
    return {
        "format_version": FORMAT_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "build": build_crate.build_identity_facts(),
        "scope": "Content could not be inventoried; no content integrity or original-coverage claim is available.",
        "live_availability": {"status": "unchecked", "reason": "No live requests were made."},
        "integrity": [
            {
                "type": "content loading",
                "count": 1,
                "passed": 0,
                "failed": 1,
                "items": [
                    {
                        "id": "content",
                        "name": "Authored TOML",
                        "status": "failed",
                        "checks": ["readable content"],
                        "issues": [error],
                        "notes": [],
                    }
                ],
            }
        ],
        "integrity_failed": 1,
        "original_coverage": {"counts": {}, "clauses": [], "questions": [], "advice": [], "by_source": []},
        "run": run,
        "trend": {"available": False, "reason": "Content could not be loaded for a comparison."},
    }


def anchor(url: str, label: str) -> str:
    return f'<a href="{esc(url)}">{esc(label)}</a>' if https(url) else esc(label)


LIVE_LABELS = {
    "unchecked": "Live availability was not checked in this run; the scheduled live watch observes it separately.",
    "not_applicable": "Guide structure only; no live service is involved.",
}


def revision_text(report: dict[str, Any]) -> str:
    """The checked commit, linked where the run is known, or what the absence means."""
    revision = report.get("revision")
    if not revision:
        return "not recorded (a local build)"
    run_url = report.get("run_url") or ""
    commit = run_url.split("/actions/runs/")[0] + "/commit/" + revision if "/actions/runs/" in run_url else ""
    return anchor(commit, revision[:12]) if commit else esc(revision[:12])


def unchecked_groups(report: dict[str, Any]) -> int:
    return sum(group.get("live_availability") == "unchecked" for group in report["integrity"])


def recorded_text(item: dict[str, Any]) -> str:
    """An item's recorded status and its date, which describe the source on that date, not today."""
    status, when = item.get("recorded_status"), item.get("recorded_date")
    if not status and not when:
        return "—"
    return " ".join(part for part in (status or "dated", f"as of {when}" if when else "") if part)


def dashboard(report: dict[str, Any], *, site: bool = False) -> str:
    """Render the same report for the CI artifact or the published site, with usable relative links."""
    report_url = "../api/health.json" if site else "health.json"
    navigation = '<a href="../index.html">FAIR Data Guide</a> · ' if site else ""
    generated = report.get("generated_at") or "No completed check run"
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>FAIR guide check run</title><style>"
        "body{font:1rem/1.55 system-ui,sans-serif;margin:0 auto;padding:1.5rem;max-width:85rem;"
        "color:#24343a;background:#fff}h1,h2,h3{line-height:1.25}a{color:#005f67}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{text-align:left;vertical-align:top;"
        "border-bottom:1px solid #d1dcde;padding:.65rem;overflow-wrap:anywhere}"
        "details{margin:1rem 0;padding:.75rem;border:1px solid #d1dcde;border-radius:.3rem}"
        "summary{cursor:pointer;font-weight:600;min-height:1.5rem}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:24rem;overflow:auto;"
        "background:#f3f6f7;padding:1rem}code{overflow-wrap:anywhere}.quiet{color:#465b62}"
        "li{margin:.3rem 0}@media(max-width:40rem){body{padding:.75rem}th,td{padding:.4rem}}"
        ":focus-visible{outline:3px solid #005f67;outline-offset:3px}</style></head><body>"
        "<main><h1>FAIR guide check run</h1>",
        f'<p>{esc(report["scope"])}</p><p class="quiet">Generated: {esc(generated)}. '
        f"Revision: {revision_text(report)}. {anchor(report.get('run_url') or '', 'CI run')}</p>",
        f'<nav aria-label="Report links"><p>{navigation}<a href="{report_url}">Machine-readable report</a>'
        ' · <a href="summary.md">CI summary</a></p></nav>',
        "<h2>Run results</h2>",
        f"<p>Status: <strong>{esc(report['run']['status'])}</strong>. {esc(report['run'].get('reason', ''))}</p>",
    ]
    if report["run"].get("jobs"):
        parts.append("<table><thead><tr><th>Check</th><th>Result</th><th>Seconds</th></tr></thead><tbody>")
        for job in report["run"]["jobs"]:
            parts.append(
                f"<tr><td>{esc(job['name'])}</td><td>{esc(job['status'])}</td>"
                f"<td>{esc(job.get('seconds', ''))}</td></tr>"
            )
        parts.append("</tbody></table>")
        for job in report["run"]["jobs"]:
            if job.get("output"):
                parts.append(
                    f"<details{' open' if job.get('status') == 'failed' else ''}>"
                    f"<summary>{esc(job['name'])} "
                    f"{'failure' if job.get('status') == 'failed' else 'diagnostic'} output</summary>"
                    f"<pre>{esc(job.get('output', ''))}</pre></details>"
                )
            for script in job.get("scripts", []):
                parts.append(
                    f"<details><summary>{esc(script['name'])}: {esc(script['status'])}, "
                    f"{esc(script['seconds'])}s; {len(script['executed'])}/{script['planned']} cases executed</summary>"
                    f"<p>Skipped: {esc(', '.join(script['skipped']))}. "
                    f"Pending: {esc(', '.join(script['pending']))}.</p><ul>"
                )
                for case in script["executed"]:
                    parts.append(
                        f"<li>{esc(case['name'])}: {esc(case['status'])}, {esc(case.get('seconds', ''))}s"
                        f"{' (aborted)' if case.get('aborted') else ''}</li>"
                    )
                parts.append("</ul></details>")
    parts += [
        "<h2>Offline integrity by item type</h2>",
        "<p>These checks cover the recorded structure and references. "
        "They do not evaluate FAIR conformance or currently running services.</p>",
    ]
    for group in report["integrity"]:
        live = LIVE_LABELS.get(group.get("live_availability", ""), "")
        parts.append(
            f"<details><summary>{esc(group['type'])}: {group['passed']}/{group['count']} passed; "
            f"{group['failed']} failed</summary><p>{esc(group.get('scope', 'Offline record integrity'))}."
            f"{' ' + esc(live) if live else ''}</p>"
            "<table><thead><tr><th>Item</th><th>Result</th>"
            "<th>Checks / observations</th><th>Recorded status</th></tr></thead><tbody>"
        )
        for item in group["items"]:
            observations = item["issues"] or item["checks"]
            parts.append(
                f"<tr><td><code>{esc(item['id'])}</code><br>{esc(item['name'])}</td>"
                f"<td>{esc(item['status'])}</td><td>{esc('; '.join(observations))}<br>"
                f'<span class="quiet">{esc(" ".join(item["notes"]))}</span></td>'
                f"<td>{esc(recorded_text(item))}</td></tr>"
            )
        parts.append("</tbody></table></details>")
    coverage = report["original_coverage"]
    parts += [
        "<h2>Original-source coverage</h2>",
        "<p>A cited original is a passage retained in its source language, separate from the guide wording. "
        "Missing passages are an inventory for editorial review, not failed requirements. "
        "“With an original” means at least one cited clause has one; "
        "partial coverage still lists the other clauses.</p>",
        "<table><thead><tr><th>Item</th><th>With an original</th><th>Total</th></tr></thead><tbody>",
    ]
    for kind, count in coverage["counts"].items():
        parts.append(f"<tr><td>{esc(kind)}</td><td>{count['with_original']}</td><td>{count['total']}</td></tr>")
    parts += ["</tbody></table>", "<h3>By published source</h3>"]
    for source in coverage["by_source"]:
        if not source["missing_clauses"]:
            continue
        parts.append(
            f"<details><summary>{esc(source['id'])}: {source['with_original']}/{source['clauses']} "
            f"clauses with originals</summary><p>{anchor(source['url'], source['title'])} "
            f"({esc(source['type'])}).</p>"
        )
        for key, label in (
            ("missing_clauses", "Clauses without originals"),
            ("advice_without_original", "Advice without any cited original"),
            ("advice_with_other_original", "Advice with another cited original"),
            ("questions_without_original", "Questions without any cited original"),
            ("questions_with_other_original", "Questions with another cited original"),
        ):
            parts.append(f"<p><strong>{label}:</strong> {esc(', '.join(source[key]) or 'None')}</p>")
        parts.append(
            "<table><thead><tr><th>Missing clause</th><th>Guide wording</th><th>Source role</th></tr></thead><tbody>"
        )
        for clause in coverage["clauses"]:
            if clause["id"] in source["missing_clauses"]:
                parts.append(
                    f"<tr><td><code>{esc(clause['id'])}</code><br>{esc(clause['locator'])}</td>"
                    f"<td>{esc(text(clause['guide_text']))}</td>"
                    f"<td>{esc(clause['kind'])}; {esc(clause['actor'])}; {esc(clause['status'])}</td></tr>"
                )
        parts.append("</tbody></table>")
        parts.append("</details>")
    for kind in ("questions", "advice"):
        missing = [item for item in coverage[kind] if not item["originals"]]
        parts.append(
            f"<details><summary>{esc(kind)} without any original: {len(missing)}</summary>"
            "<table><thead><tr><th>Item</th><th>Guide wording / cited clauses</th>"
            "<th>Review status</th></tr></thead><tbody>"
        )
        for item in missing:
            basis = item["reviewed_basis"] or (
                "Not classified as a deliberate omission; review the suitability and reuse basis of a source passage."
            )
            parts.append(
                f"<tr><td><code>{esc(item['id'])}</code></td><td>{esc(text(item['guide_text']))}<br>"
                f"{esc(', '.join(item['citations']))}</td>"
                f"<td>{esc(basis)}</td></tr>"
            )
        parts.append("</tbody></table></details>")
    parts += ["<h2>Trend</h2>"]
    if report["trend"]["available"]:
        parts.append(
            f"<p>Compared with {esc(report['trend'].get('previous_generated_at'))}. "
            "Changed content counts are not a score.</p>"
        )
        for kind, delta in report["trend"]["coverage"].items():
            parts.append(
                f"<p><strong>{esc(kind)}:</strong> originals count change {delta['with_original_delta']:+d}; "
                f"newly missing: {esc(', '.join(delta['new_missing']) or 'None')}; "
                f"no longer missing: {esc(', '.join(delta['resolved_missing']) or 'None')}; "
                f"added items: {esc(', '.join(delta['added_items']) or 'None')}; "
                f"removed items: {esc(', '.join(delta['removed_items']) or 'None')}.</p>"
            )
        parts.append(f"<pre>{esc(json.dumps(report['trend']['job_changes'], indent=2))}</pre>")
    else:
        parts.append(f"<p>{esc(report['trend']['reason'])}</p>")
    advisories = report.get("missing_links", [])
    parts.append(
        f"<h2>Possible missing links (advisory): {len(advisories)}</h2>"
        "<p>Ranked catalogue-name suggestions with context and ambiguity notes; these do not fail checks.</p>"
    )
    parts.append(
        "<details><summary>Texts and matching entries</summary><table><thead>"
        "<tr><th>Text</th><th>Entry</th></tr></thead><tbody>"
    )
    for item in advisories:
        parts.append(
            f"<tr><td><code>{esc(item['path'])}</code><p>{esc(item['excerpt'])}</p></td>"
            f"<td>{esc(item['entry_name'])}<br><code>{esc(item['reference'])}</code>"
            f"<p>{esc(item['confidence'])}: {esc(item['reason'])}</p></td></tr>"
        )
    parts.append("</tbody></table></details>")
    review = report.get("missing_link_review", {})
    parts.append(
        f"<h3>Reviewed unlinked mentions: {len(review.get('reviewed', []))}</h3>"
        "<p>Decisions apply only to the exact field, target and text reviewed. Changed text reopens the suggestion.</p>"
        "<details><summary>Editorial decisions and reasons</summary><table><thead>"
        "<tr><th>Text and target</th><th>Decision</th></tr></thead><tbody>"
    )
    for item in review.get("reviewed", []):
        parts.append(
            f"<tr><td><code>{esc(item['path'])}</code><p>{esc(item['excerpt'])}</p>"
            f"<code>{esc(item['address'])}</code></td><td>{esc(item['review_reason'])}"
            f"<p>Reviewed {esc(item['reviewed'])}</p></td></tr>"
        )
    parts.append("</tbody></table></details>")
    parts.append(f"<h3>Stale link decisions requiring review: {len(review.get('stale', []))}</h3>")
    for item in review.get("stale", []):
        parts.append(
            f"<p><code>{esc(item['path'])}</code> → <code>{esc(item['address'])}</code>: {esc(item['reason'])}</p>"
        )
    parts += [
        "<h2>Live availability</h2>",
        f"<p><strong>{esc(report['live_availability']['status'])}</strong>: "
        f"{esc(report['live_availability']['reason'])}</p>",
        "</main></body></html>",
    ]
    return "\n".join(parts)


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "## FAIR guide check run",
        "",
        report["scope"],
        "",
        f"Run: **{report['run']['status']}**. Offline item integrity failures: **{report['integrity_failed']}**.",
        "",
        f"Revision: `{(report.get('revision') or 'not recorded')[:12]}`.",
        "",
        "| Item | With a cited original | Total |",
        "| --- | ---: | ---: |",
    ]
    for kind, counts in report["original_coverage"]["counts"].items():
        lines.append(f"| {kind} | {counts['with_original']} | {counts['total']} |")
    counts = report["original_coverage"]["counts"]
    if counts:
        lines += [
            "",
            f"Advice without any original: {counts['advice']['total'] - counts['advice']['with_original']}; "
            "Question omissions with reviewed source-link bases: "
            f"{counts['questions'].get('reviewed_source_links', 0)}. "
            "Missing originals are editorial review information, not failed requirements.",
        ]
    lines += ["", f"Possible missing links (advisory, non-blocking): **{len(report.get('missing_links', []))}**.", ""]
    review = report.get("missing_link_review", {})
    lines += [
        f"Reviewed unlinked mentions: **{len(review.get('reviewed', []))}**; "
        f"stale decisions requiring review: **{len(review.get('stale', []))}**.",
        "",
    ]
    lines += ["", "| Check | Result | Seconds |", "| --- | --- | ---: |"]
    for job in report["run"].get("jobs", []):
        lines.append(f"| {job['name']} | {job['status']} | {job.get('seconds', '')} |")
    nested = [script for job in report["run"].get("jobs", []) for script in job.get("scripts", [])]
    if nested:
        lines += [
            "",
            "| Script | Result | Seconds | Executed / planned cases | Skipped | Pending |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
        for script in nested:
            lines.append(
                f"| {script['name']} | {script['status']} | {script['seconds']} | "
                f"{len(script['executed'])} / {script['planned']} | "
                f"{len(script['skipped'])} | {len(script['pending'])} |"
            )
    failed = [
        job
        for job in report["run"].get("jobs", [])
        if job.get("status") == "failed" and str(job.get("output", "")).strip()
    ]
    if failed:
        lines += ["", "### Failed check output", "", "Full logs and details are in the uploaded health artifact.", ""]
        for job in failed:
            output = str(job["output"]).rstrip().replace("```", "'''")
            if len(output) > 4000:
                output = output[-4000:]
            lines += [f"#### {job['name']}", "", "```text", output, "```", ""]
    lines += [
        "",
        f"Live availability: **{report['live_availability']['status']}**. {report['live_availability']['reason']} "
        f"Item groups without a live check: {unchecked_groups(report)}. Dated service statuses are not current probes.",
        "",
        "The uploaded health artifact contains the dashboard, complete item inventory, "
        "missing-clause/source associations and failure output.",
    ]
    if not report["trend"]["available"]:
        lines += ["", report["trend"]["reason"]]
    else:
        lines += ["", "Coverage trend (original count change; new / resolved missing items):"]
        for kind, delta in report["trend"]["coverage"].items():
            lines.append(
                f"- {kind}: {delta['with_original_delta']:+d}; {len(delta['new_missing'])} new / "
                f"{len(delta['resolved_missing'])} resolved; {len(delta['removed_items'])} removed items."
            )
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "health.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    (output / "index.html").write_text(dashboard(report), encoding="utf-8")
    (output / "summary.md").write_text(markdown(report), encoding="utf-8")


def write_site_dashboard(report: dict[str, Any], site: Path) -> None:
    """Publish the report's human view beside the API, without a second JSON snapshot."""
    output = site / "health"
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(dashboard(report, site=True), encoding="utf-8", newline="\n")
    (output / "summary.md").write_text(markdown(report), encoding="utf-8", newline="\n")


def read_previous(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("previous report must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=ROOT / ".cache" / "health")
    parser.add_argument("--previous-report", type=Path)
    args = parser.parse_args(argv)
    try:
        report = make_report(build_crate.load_content(ROOT / "content"), previous=read_previous(args.previous_report))
        write_report(report, args.output)
    except (OSError, ValueError, build_crate.ContentError) as error:
        print(f"health report: {error}", file=sys.stderr)
        return 2
    print(
        f"Health inventory: {sum(group['count'] for group in report['integrity'])} items, "
        f"{report['integrity_failed']} integrity failures; {args.output}"
    )
    for kind, counts in report["original_coverage"]["counts"].items():
        print(f"Originals: {kind} {counts['with_original']}/{counts['total']}")
    return 1 if report["integrity_failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
