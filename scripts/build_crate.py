#!/usr/bin/env python3
"""Generate the FAIR guide's knowledge base from the TOML sources.

Reads ``content/**/*.toml`` and writes:

- ``ro-crate-metadata.json``: the knowledge base as an RO-Crate 1.2 (Process Run Crate 0.5);
- ``assets/data/kb.js`` and ``assets/data/ui.js``: the crate and the interface strings and configuration as
  classic scripts, which load from a local file as well as from a web host;
- the generated blocks in ``index.html``: the Content Security Policy, a short schema.org description of the
  guide for search engines, the data scripts and the icon sprite;
- ``ro-crate-preview.html``: a copy of the page, which is the crate's HTML preview.

With ``--check`` nothing is written; the script exits with status 1 and shows a diff when the committed output
differs from the regenerated output. Either way it warns when what the page downloads, compressed, exceeds the page
budget; ``--sizes`` prints what the page downloads. Uses only the Python standard library. The content model is
documented in ``docs/content-model.md``.
"""

from __future__ import annotations

import argparse
import difflib
import gzip
import json
import os
import re
import sys
import tomllib
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
CRATE_FILE = "ro-crate-metadata.json"
PAGE_FILE = "index.html"
PREVIEW_FILE = "ro-crate-preview.html"
KB_SCRIPT = "assets/data/kb.js"
UI_SCRIPT = "assets/data/ui.js"
# What the page may download before any user action, gzip-compressed: the page, its scripts and its stylesheets.
# Above it the build warns, so that loading parts on demand is decided on a measurement.
PAGE_BUDGET_KB = 300
# A reference editors mark in a text: [[id|phrase]], where id names a resource or source, or term:<id> a glossary
# term, and phrase is the words in this language that name it.
REFERENCE = re.compile(r"\[\[(?P<id>[^\[\]|]+)\|(?P<phrase>[^\[\]|]+)\]\]")
PAGE_ASSET = re.compile(r'<script src="(?P<script>[^"]+)"|<link rel="stylesheet" href="(?P<style>[^"]+)"')

RO_CRATE = "https://w3id.org/ro/crate/1.2"
PROCESS_RUN_CRATE = "https://w3id.org/ro/wfrun/process/0.5"
FAIR_PRINCIPLES = "https://w3id.org/fair/principles/terms/"
FTR_TEST = "https://w3id.org/ftr#Test"
FIP_TERMS = "https://w3id.org/fair/fip/terms/"
FIP_DASHBOARD = "https://fip-dashboard.dmp.eosc.cz/resources/"
FTR = "https://w3id.org/ftr#"
PROV = "http://www.w3.org/ns/prov#"
LANGS = ("cs", "en")

LICENSES = {
    "CC-BY-4.0": (
        "https://spdx.org/licenses/CC-BY-4.0",
        "Creative Commons Attribution 4.0 International",
        "Licence of the guide's content: texts, data, documentation and diagrams.",
    ),
    "MIT": ("https://spdx.org/licenses/MIT", "MIT License", "Licence of the guide's code."),
}

# The guide's own vocabulary: term -> definition. Each term is defined in the graph as an rdf:Property.
TERMS = {
    "disclosureLevel": "Disclosure level (L0 to L3) at which an advice item is shown.",
    "adviceKind": "Kind of an advice item that is not ordinary advice, such as the AI-in-FAIRification overlay.",
    "block": "Block of a self-check that a question belongs to; a check's blocks are a defined term set in order.",
    "defaultProfile": "Profile a self-check starts with, such as no funding programme for the dataset check.",
    "startsAt": "Station at which the path opens for an answer to the entry question.",
    "tier": "Self-check tier of an item.",
    "fixAt": "Station where a gap found by a self-check item is addressed.",
    "fixedBy": "Actors who can fix a gap found by a self-check item.",
    "appliesTo": "Repository profiles or check modes that a self-check item applies to.",
    "providedByNrpFor": "Repository profiles for which NRP itself provides what a gate item asks for.",
    "allowsNotApplicable": "Whether 'not applicable' is an allowed answer to a self-check item.",
    "serviceStatus": "Status of a service or resource in the five-level vocabulary.",
    "statusAsOf": "Date on which a status was last verified.",
    "healthStatus": "Availability of a live test as last observed.",
    "resourceType": "Type of a resource, used to filter the resource finder.",
    "catalogueType": "Type of a FAIR-enabling resource in the FIP Dashboard.",
    "repositoryKind": "Kind of a repository: domain, institutional or general-purpose.",
    "clauseKind": "Kind of a ledger clause: requirement, fulfilment in NRP, or statement.",
    "supersededBy": "Clause or source that replaces a superseded clause.",
    "lensOrder": "Order of a callout's items for one lens, written as '<lens>: <item>, <item>, ...'.",
    "relatedTo": "CoreTrustSeal requirement or CDIF profile related to a FAIR principle.",
    "note": "Additional remark shown with a clause or a self-check item.",
    "disclaimer": "Disclaimer that a snapshot's source publishes about its data, shown while it is present.",
    "prefillLevel": "Highest answer that live evidence can pre-fill for a self-check item that it only partly proves.",
    "lookup": "Service where a user can find out the answer to a self-check item.",
}

# Sources are contextual entities. Cited datasets and software are typed through additionalType: as Dataset or
# SoftwareSourceCode entities, RO-Crate would treat them as data entities or scripts that belong inside the crate.
SOURCE_TYPES = {
    "report": "Report",
    "article": "ScholarlyArticle",
    "dataset": "CreativeWork",
    "webpage": "WebPage",
    "document": "DigitalDocument",
    "standard": "CreativeWork",
    "software": "CreativeWork",
    "presentation": "PresentationDigitalDocument",
}

SOURCE_ADDITIONAL_TYPES = {
    "dataset": "http://schema.org/Dataset",
    "software": "http://schema.org/SoftwareSourceCode",
}

RESOURCE_TYPES = {
    "service": ["CreativeWork", "Service"],
    "tool": "CreativeWork",
    "registry": "DataCatalog",
    "repository": "DataCatalog",
    "guide": "DigitalDocument",
    "document": "DigitalDocument",
    "standard": "CreativeWork",
    "vocabulary": "DefinedTermSet",
    "community": "WebPage",
    "project": ["CreativeWork", "Project"],
    "course": "Course",
}


class ContentError(Exception):
    """A content source cannot be turned into the crate."""


# ---------------------------------------------------------------------------
# Loading


def load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as error:
        raise ContentError(f"{path.relative_to(ROOT)}: {error}") from error


def load_content(content_dir: Path = CONTENT) -> dict[str, Any]:
    """Read every content file into one dictionary."""

    def optional(name: str) -> dict[str, Any]:
        path = content_dir / name
        return load_toml(path) if path.exists() else {}

    stations = [load_toml(path) for path in sorted((content_dir / "stations").glob("*.toml"))]
    stations.sort(key=lambda data: data["station"]["position"])
    checks = [load_toml(path) for path in sorted((content_dir / "checks").glob("*.toml"))]
    snapshots = [load_toml(path) for path in sorted((content_dir / "snapshots").glob("*.toml"))]
    return {
        "guide": load_toml(content_dir / "guide.toml"),
        "principles": optional("principles.toml").get("principle", []),
        "sources": optional("sources.toml").get("source", []),
        "ledger": optional("ledger.toml").get("clause", []),
        "stations": stations,
        "checks": checks,
        "resources": optional("resources.toml").get("resource", []),
        "repositories": optional("repositories.toml").get("repository", []),
        "snapshots": snapshots,
        "glossary": optional("glossary.toml"),
        "callouts": optional("callouts.toml").get("callout", []),
        "live": optional("live.toml"),
        "provenance": optional("provenance.toml").get("action", []),
        "pages": optional("pages.toml").get("page", []),
        "ui": optional("ui.toml"),
        "icons": optional("icons.toml"),
    }


# ---------------------------------------------------------------------------
# Value helpers


def text(value: Any) -> Any:
    """Turn bilingual tables into JSON-LD language-tagged values; leave plain strings as they are."""
    if isinstance(value, list):
        values: list[Any] = []
        for item in value:
            converted = text(item)
            values.extend(converted if isinstance(converted, list) else [converted])
        return values
    if isinstance(value, dict):
        return [{"@value": value[lang], "@language": lang} for lang in LANGS if value.get(lang)]
    return value


def ref(entity_id: str) -> dict[str, str]:
    return {"@id": entity_id}


def refs(entity_ids: list[str]) -> list[dict[str, str]]:
    return [ref(entity_id) for entity_id in entity_ids]


def iso(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def append_ref(entity: dict[str, Any], key: str, entity_id: str) -> None:
    """Add a reference to a property, keeping a single value single and several values in a list."""
    current = entity.get(key)
    if current is None:
        entity[key] = ref(entity_id)
    elif isinstance(current, list):
        current.append(ref(entity_id))
    else:
        entity[key] = [current, ref(entity_id)]


def principle_iri(principle: str) -> str:
    return FAIR_PRINCIPLES + principle


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def prune(entity: dict[str, Any]) -> dict[str, Any]:
    """Drop properties without a value, unwrap single-item lists, and give every entity a name."""
    pruned: dict[str, Any] = {}
    for key, value in entity.items():
        if value in (None, [], "", {}):
            continue
        unwrapped = value[0] if isinstance(value, list) and len(value) == 1 and key != "@type" else value
        pruned[key] = unwrapped
    if "name" not in pruned and "rdfs:label" not in pruned:
        fallback = pruned.get("identifier") or pruned.get("headline") or pruned.get("propertyID")
        if fallback is not None:
            pruned["name"] = fallback
    return pruned


# ---------------------------------------------------------------------------
# Graph


class Graph:
    """An ordered set of entities keyed by @id, plus an index from content IDs to entity IDs."""

    def __init__(self) -> None:
        self.entities: dict[str, dict[str, Any]] = {}
        self.index: dict[str, list[str]] = {}
        # Per entity whose text names others by reference: the phrase to link in each language.
        self.text_links: dict[str, list[dict[str, str]]] = {}

    def add(self, entity: dict[str, Any], content_id: str | None = None) -> str:
        entity = prune(entity)
        entity_id = entity["@id"]
        if entity_id in self.entities:
            if self.entities[entity_id] != entity:
                raise ContentError(f"two different entities share the @id {entity_id}")
        else:
            self.entities[entity_id] = entity
        if content_id is not None:
            targets = self.index.setdefault(content_id, [])
            if entity_id not in targets:
                targets.append(entity_id)
        return entity_id

    def resolve(self, content_ids: list[str]) -> list[str]:
        """Map content IDs to entity IDs; a trailing '*' matches every content ID with that prefix."""
        resolved: list[str] = []
        for content_id in content_ids:
            if content_id.endswith("*"):
                prefix = content_id[:-1]
                matches = [eid for cid, eids in self.index.items() if cid.startswith(prefix) for eid in eids]
            else:
                matches = self.index.get(content_id, [f"#unresolved-{content_id}"])
            for entity_id in matches:
                if entity_id not in resolved:
                    resolved.append(entity_id)
        return resolved


def reference_targets(content: dict[str, Any], graph: Graph) -> dict[str, str]:
    """What a reference in text may name: a resource or source by its ID, a glossary term as term:<id>."""
    targets = {
        item["id"]: graph.index[item["id"]][0]
        for item in content["resources"] + content["sources"]
        if graph.index.get(item["id"])
    }
    targets |= {
        "term:" + entity_id[len("#term-") :]: entity_id
        for entity_id in graph.entities
        if entity_id.startswith("#term-")
    }
    return targets


def link_texts(graph: Graph, targets: dict[str, str]) -> None:
    """Strip the references editors mark in text to their phrases, record each referenced entity as mentioned by the
    entity whose text names it, and keep per entity the phrase to link in each language for the page."""
    for entity_id, entity in graph.entities.items():
        found: dict[str, dict[str, str]] = {}

        def clean(
            value: Any, lang: str = "und", owner: str = entity_id, found: dict[str, dict[str, str]] = found
        ) -> Any:
            if isinstance(value, list):
                return [clean(item) for item in value]
            if isinstance(value, dict) and "@value" in value:
                return value | {"@value": clean(value["@value"], value.get("@language", "und"))}
            if not isinstance(value, str) or "[[" not in value:
                return value

            def phrase(match: re.Match[str]) -> str:
                target = targets.get(match["id"])
                if target is None:
                    raise ContentError(f"{owner}: the text refers to an unknown entry '{match['id']}'")
                found.setdefault(target, {"ref": target}).setdefault(lang, match["phrase"])
                return match["phrase"]

            return REFERENCE.sub(phrase, value)

        for key in [key for key in entity if not key.startswith("@")]:
            entity[key] = clean(entity[key])
        if found:
            mentioned = [item["@id"] for item in as_list(entity.get("mentions"))]
            entity["mentions"] = refs(mentioned + [target for target in found if target not in mentioned])
            graph.text_links[entity_id] = list(found.values())


def defined_terms(graph: Graph, set_id: str, set_name: str, prefix: str, items: list[dict[str, Any]]) -> list[str]:
    """Add a DefinedTermSet and its terms; return the term IDs."""
    term_ids = [f"#{prefix}-{item['id']}" for item in items]
    graph.add({"@id": f"#{set_id}", "@type": "DefinedTermSet", "name": set_name, "hasDefinedTerm": refs(term_ids)})
    for item, term_id in zip(items, term_ids, strict=True):
        graph.add(
            {
                "@id": term_id,
                "@type": "DefinedTerm",
                "termCode": item["id"],
                "name": text(item.get("name") or item.get("label")),
                "description": text(item.get("description")),
                "inDefinedTermSet": ref(f"#{set_id}"),
            }
        )
    return term_ids


# ---------------------------------------------------------------------------
# Builders


def build_people(graph: Graph, guide: dict[str, Any], organizations: dict[str, str]) -> dict[str, str]:
    people: dict[str, str] = {}
    for person in guide.get("person", []):
        entity_id = person.get("orcid") or f"#person-{person['id']}"
        people[person["id"]] = graph.add(
            {
                "@id": entity_id,
                "@type": "Person",
                "name": person["name"],
                "affiliation": refs(
                    [organizations[org] for org in person.get("affiliation", []) if org in organizations]
                ),
            },
            person["id"],
        )
    return people


def build_organizations(graph: Graph, guide: dict[str, Any]) -> dict[str, str]:
    organizations: dict[str, str] = {}
    for organization in guide.get("organization", []):
        entity_id = organization.get("ror") or f"#org-{organization['id']}"
        organizations[organization["id"]] = entity_id
    for organization in guide.get("organization", []):
        graph.add(
            {
                "@id": organizations[organization["id"]],
                "@type": "Organization",
                "name": text(organization["name"]),
                "url": organization.get("url"),
                "identifier": organization.get("identifier"),
                "sameAs": ref(f"#fd-org-{organization['fipDashboard']}") if organization.get("fipDashboard") else None,
                "funder": refs([organizations[funder] for funder in as_list(organization.get("funder"))]),
            },
            organization["id"],
        )
    return organizations


def organization_ref(graph: Graph, organizations: dict[str, str], name: str | None) -> dict[str, str] | None:
    """Reference a known organisation by ID, or add one by name."""
    if not name:
        return None
    if name in organizations:
        return ref(organizations[name])
    entity_id = f"#org-{slug(name)}"
    graph.add({"@id": entity_id, "@type": "Organization", "name": name})
    return ref(entity_id)


def build_instruments(graph: Graph, guide: dict[str, Any]) -> None:
    for instrument in guide.get("instrument", []):
        graph.add(
            {
                "@id": f"#instrument-{instrument['id']}",
                "@type": "SoftwareApplication",
                "name": instrument["name"],
                "version": instrument.get("version"),
                "url": instrument.get("url"),
                "applicationCategory": instrument.get("kind"),
            },
            instrument["id"],
        )


def build_vocabularies(graph: Graph, guide: dict[str, Any]) -> None:
    for lens in guide.get("lens", []):
        graph.add(
            {
                "@id": f"#lens-{lens['id']}",
                "@type": "Audience",
                "name": text(lens["name"]),
                "audienceType": lens["id"],
                "description": text(lens.get("description")),
            },
            f"lens:{lens['id']}",
        )
    defined_terms(graph, "levels", "Disclosure levels", "level", guide.get("level", []))
    defined_terms(graph, "tiers", "Self-check tiers", "tier", guide.get("tier", []))
    defined_terms(graph, "statuses", "Service statuses", "status", guide.get("status", []))
    defined_terms(graph, "actors", "Actors", "actor", guide.get("actor", []))
    defined_terms(graph, "resource-types", "Resource types", "rtype", guide.get("resourceType", []))
    defined_terms(graph, "repository-kinds", "Repository kinds", "rkind", guide.get("repositoryKind", []))
    stage_ids = defined_terms(graph, "stages", "Entry stages", "stage", guide.get("stage", []))
    for stage, stage_id in zip(guide.get("stage", []), stage_ids, strict=True):
        graph.entities[stage_id]["startsAt"] = ref(f"#station-{stage['station']}")
    for help_route in guide.get("help", []):
        graph.add(
            {
                "@id": f"#help-{help_route['id']}",
                "@type": "WebPage",
                "name": text(help_route["name"]),
                "url": help_route.get("url"),
                "audience": refs([f"#lens-{lens}" for lens in help_route.get("lenses", [])]),
            },
            f"help:{help_route['id']}",
        )


def build_terms(graph: Graph, vocabulary_base: str) -> None:
    for term, definition in TERMS.items():
        graph.add(
            {"@id": vocabulary_base + term, "@type": "rdf:Property", "rdfs:label": term, "rdfs:comment": definition}
        )


def build_principles(graph: Graph, principles: list[dict[str, Any]]) -> None:
    graph.add(
        {
            "@id": FAIR_PRINCIPLES,
            "@type": "DefinedTermSet",
            "name": "FAIR Guiding Principles",
            "url": "https://doi.org/10.1038/sdata.2016.18",
        }
    )
    for principle in principles:
        related = [f"#cts-{requirement}" for requirement in principle.get("cts", [])]
        related += [f"#cdif-{slug(profile)}" for profile in principle.get("cdif", [])]
        for requirement in principle.get("cts", []):
            graph.add(
                {
                    "@id": f"#cts-{requirement}",
                    "@type": "DefinedTerm",
                    "termCode": requirement,
                    "name": f"CoreTrustSeal {requirement}",
                    "inDefinedTermSet": ref("#coretrustseal"),
                }
            )
        for profile in principle.get("cdif", []):
            graph.add(
                {
                    "@id": f"#cdif-{slug(profile)}",
                    "@type": "DefinedTerm",
                    "termCode": profile,
                    "name": f"CDIF {profile}",
                    "inDefinedTermSet": ref("#cdif"),
                }
            )
        graph.add(
            {
                "@id": principle_iri(principle["id"]),
                "@type": "DefinedTerm",
                "termCode": principle["id"],
                "name": text(principle.get("label")),
                "description": text(principle.get("statement")),
                "inDefinedTermSet": ref(FAIR_PRINCIPLES),
                "relatedTo": refs(related),
            },
            principle["id"],
        )
    if any(principle.get("cts") for principle in principles):
        graph.add(
            {
                "@id": "#coretrustseal",
                "@type": "DefinedTermSet",
                "name": "CoreTrustSeal Requirements",
                "url": "https://www.coretrustseal.org/",
            }
        )
    if any(principle.get("cdif") for principle in principles):
        graph.add(
            {
                "@id": "#cdif",
                "@type": "DefinedTermSet",
                "name": "Cross-Domain Interoperability Framework (CDIF)",
                "url": "https://book.cdif.org/",
            }
        )


def build_sources(
    graph: Graph,
    sources: list[dict[str, Any]],
    organizations: dict[str, str],
    people: dict[str, str],
    names: dict[str, str],
) -> None:
    """Sources the guide cites but does not recommend as resources; returns their entity IDs."""
    source_ids = []
    for source in sources:
        entity_id = f"https://doi.org/{source['doi']}" if source.get("doi") else f"#source-{source['id']}"
        source_ids.append(entity_id)
        graph.add(
            {
                "@id": entity_id,
                "@type": SOURCE_TYPES[source["type"]],
                "additionalType": SOURCE_ADDITIONAL_TYPES.get(source["type"]),
                "identifier": source["id"],
                "name": text(source["title"]),
                "url": source.get("url"),
            }
            | citation_properties(graph, source, organizations, people, names),
            source["id"],
        )
    return source_ids


def citation_properties(
    graph: Graph, citation: dict[str, Any], organizations: dict[str, str], people: dict[str, str], names: dict[str, str]
) -> dict[str, Any]:
    """How a cited work is cited: publisher, authors, version, dates and licence. An author given as a person ID
    becomes a Person entity, any other author stays a name."""
    authors = citation.get("authors", [])
    return {
        "inLanguage": citation.get("inLanguage"),
        "publisher": organization_ref(graph, organizations, citation.get("publisher")),
        "version": citation.get("version"),
        "author": refs([people[author] for author in authors if author in people]),
        "creditText": "; ".join(names.get(author, author) for author in authors) or None,
        "datePublished": iso(citation["datePublished"]) if citation.get("datePublished") else None,
        "dateModified": iso(citation["dateModified"]) if citation.get("dateModified") else None,
        "sdDatePublished": iso(citation["dateAccessed"]) if citation.get("dateAccessed") else None,
        "license": citation.get("license"),
    }


def build_ledger(graph: Graph, clauses: list[dict[str, Any]]) -> None:
    clause_ids = [f"#clause-{clause['id']}" for clause in clauses]
    graph.add({"@id": "#ledger", "@type": "CreativeWork", "name": "Clause ledger", "hasPart": refs(clause_ids)})
    for clause in clauses:
        graph.add(
            {
                "@id": f"#clause-{clause['id']}",
                "@type": "CreativeWork",
                "identifier": clause["id"],
                "text": text(clause.get("text")),
                "about": refs([principle_iri(principle) for principle in clause.get("principles", [])]),
                "audience": refs([f"#actor-{clause['actor']}"] if clause.get("actor") else []),
                "isPartOf": refs(graph.resolve([clause["source"]])) if clause.get("source") else None,
                "clauseKind": clause.get("kind"),
                "creativeWorkStatus": clause.get("status", "current"),
                "note": text(clause.get("note")),
                "supersededBy": refs(graph.resolve([clause["supersededBy"]])) if clause.get("supersededBy") else None,
            },
            clause["id"],
        )
    for clause in clauses:
        # A note may cite clauses later in the ledger, so citations are added once every clause exists.
        if clause.get("noteSources"):
            entity = graph.entities[f"#clause-{clause['id']}"]
            entity["citation"] = refs(graph.resolve(clause["noteSources"]))
            if len(entity["citation"]) == 1:
                entity["citation"] = entity["citation"][0]


def lens_refs(lens: Any, all_lenses: list[str]) -> list[dict[str, str]]:
    lenses = all_lenses if lens == "*" else as_list(lens)
    return refs([f"#lens-{item}" for item in lenses])


def build_stations(graph: Graph, stations: list[dict[str, Any]], all_lenses: list[str]) -> list[str]:
    station_ids: list[str] = []
    for data in stations:
        station = data["station"]
        station_id = f"#station-{station['id']}"
        station_ids.append(station_id)
        advice_ids: list[str] = []
        for order, advice in enumerate(data.get("advice", []), start=1):
            advice_id = f"#advice-{advice['id']}"
            advice_ids.append(advice_id)
            level = advice["level"]
            is_tip = level == "L2" or advice.get("kind") == "ai"
            step_ids = [f"{advice_id}-step-{number}" for number in range(1, len(advice.get("steps", [])) + 1)]
            action_id = f"{advice_id}-action" if advice.get("action") else None
            graph.add(
                {
                    "@id": advice_id,
                    "@type": "HowToTip" if is_tip else "HowToDirection",
                    "identifier": advice["id"],
                    "text": text(advice["text"]),
                    "position": advice.get("position", order),
                    "audience": lens_refs(advice["lens"], all_lenses),
                    "disclosureLevel": ref(f"#level-{level}"),
                    "adviceKind": advice.get("kind"),
                    "citation": refs(graph.resolve(advice.get("sources", []))),
                    "isPartOf": ref(station_id),
                    "hasPart": refs(step_ids),
                    "potentialAction": ref(action_id) if action_id else None,
                },
                advice["id"],
            )
            for number, (step_id, step) in enumerate(zip(step_ids, advice.get("steps", []), strict=True), start=1):
                graph.add(
                    {
                        "@id": step_id,
                        "@type": "HowToDirection",
                        "text": text(step),
                        "position": number,
                        "isPartOf": ref(advice_id),
                    }
                )
            if action_id:
                action = advice["action"]
                graph.add(
                    {"@id": action_id, "@type": "Action", "name": text(action["label"]), "target": ref(action["href"])}
                )
        graph.add(
            {
                "@id": station_id,
                "@type": "HowToSection",
                "identifier": station["id"],
                "name": text(station["name"]),
                "headline": text(station.get("title")),
                "position": station["position"],
                "about": refs([principle_iri(principle) for principle in station.get("principles", [])]),
                "timeRequired": f"PT{station['minutes']}M" if station.get("minutes") else None,
                "itemListElement": refs(advice_ids),
                "mentions": refs([f"#term-{term}" for term in station.get("glossary", [])]),
            },
            station["id"],
        )
    graph.add({"@id": "#path", "@type": "HowTo", "name": "Path", "step": refs(station_ids)})
    return station_ids


def build_prefill(graph: Graph, item_id: str, prefill: dict[str, Any]) -> list[str]:
    """One property value per live source that can pre-fill an item, naming the fields, tests or FIP questions."""
    prefill_ids = []
    for source, value in prefill.items():
        prefill_id = f"{item_id}-prefill-{source}"
        prefill_ids.append(prefill_id)
        graph.add({"@id": prefill_id, "@type": "PropertyValue", "propertyID": f"prefill:{source}", "value": value})
    return prefill_ids


def build_checks(graph: Graph, checks: list[dict[str, Any]], links: dict[str, str]) -> list[str]:
    check_ids: list[str] = []
    for data in checks:
        check = data["check"]
        check_id = f"#check-{check['id']}"
        check_ids.append(check_id)
        profiles = check.get("profile", [])
        if profiles:
            defined_terms(graph, f"profiles-{check['id']}", f"Repository profiles ({check['id']})", "profile", profiles)
        modes = check.get("modes", [])
        if modes:
            defined_terms(
                graph,
                f"modes-{check['id']}",
                f"Check modes ({check['id']})",
                "mode",
                [{"id": mode, "name": mode} for mode in modes],
            )
        blocks = data.get("block", [])
        if blocks:
            defined_terms(
                graph,
                f"blocks-{check['id']}",
                f"Blocks of the {check['id']} check",
                "block",
                [
                    {
                        "id": f"{check['id']}-{block['id']}",
                        "name": block["name"],
                        "description": block.get("description"),
                    }
                    for block in blocks
                ],
            )
        item_ids: list[str] = []
        for order, item in enumerate(data.get("item", []), start=1):
            item_id = f"#item-{item['id']}"
            item_ids.append(item_id)
            prefill_ids = build_prefill(graph, item_id, item.get("prefill", {}))
            applies = [f"#profile-{profile}" for profile in item.get("profiles", [])]
            applies += [f"#mode-{mode}" for mode in item.get("modes", [])]
            graph.add(
                {
                    "@id": item_id,
                    "@type": "Question",
                    "identifier": item["id"],
                    "text": text(item["statement"]),
                    "description": text(item.get("help")),
                    "position": order,
                    "about": refs([principle_iri(principle) for principle in item.get("principles", [])]),
                    "citation": refs(graph.resolve(item.get("sources", []))),
                    "tier": ref(f"#tier-{item['tier']}"),
                    "block": ref(f"#block-{check['id']}-{item['block']}") if item.get("block") else None,
                    "fixAt": ref(f"#station-{item['fixAt']}") if item.get("fixAt") else None,
                    "fixedBy": refs([f"#actor-{owner}" for owner in item.get("owner", [])]),
                    "appliesTo": refs(applies),
                    "providedByNrpFor": refs([f"#profile-{profile}" for profile in item.get("providedByNrp", [])]),
                    "allowsNotApplicable": item.get("allowNotApplicable", False),
                    "note": text(item.get("note")),
                    "additionalProperty": refs(prefill_ids),
                    "prefillLevel": item.get("prefillLevel"),
                    "lookup": ref(links[item["lookup"]]) if item.get("lookup") else None,
                    "isPartOf": ref(check_id),
                },
                item["id"],
            )
        graph.add(
            {
                "@id": check_id,
                "@type": "Quiz",
                "identifier": check["id"],
                "name": text(check["name"]),
                "description": text(check.get("description")),
                "audience": refs([f"#lens-{lens}" for lens in check.get("lenses", [])]),
                "timeRequired": f"PT{check['minutes']}M" if check.get("minutes") else None,
                "defaultProfile": ref(f"#profile-{check['defaultProfile']}") if check.get("defaultProfile") else None,
                "hasPart": refs(item_ids),
            },
            f"check:{check['id']}",
        )
    return check_ids


def build_resources(
    graph: Graph,
    resources: list[dict[str, Any]],
    all_lenses: list[str],
    *,
    organizations: dict[str, str],
    people: dict[str, str],
    names: dict[str, str],
) -> list[str]:
    """One entity per resource; a resource the guide also cites carries its citation. Returns the cited ones."""
    cited: list[str] = []
    for resource in resources:
        resource_id = f"#resource-{resource['id']}"
        citation = resource.get("citation")
        entity = {
            "@id": resource_id,
            "@type": RESOURCE_TYPES[resource["type"]],
            "identifier": resource["id"],
            "name": text(resource["name"]),
            "description": text(resource.get("description")),
            "url": resource.get("url"),
            "audience": lens_refs(resource.get("lenses", "*"), all_lenses),
            "additionalType": (["http://schema.org/SoftwareApplication"] if resource["type"] == "tool" else [])
            + [FIP_TERMS + fip_class for fip_class in resource.get("fipClass", [])]
            + (
                [SOURCE_ADDITIONAL_TYPES[citation["type"]]]
                if citation and citation.get("type") in SOURCE_ADDITIONAL_TYPES
                else []
            ),
            "resourceType": ref(f"#rtype-{resource['type']}"),
            "serviceStatus": ref(f"#status-{resource['status']}") if resource.get("status") else None,
            "statusAsOf": iso(resource["asOf"]) if resource.get("asOf") else None,
            "sameAs": refs(
                resource.get("sameAs", [])
                + ([FIP_DASHBOARD + resource["fipDashboard"]] if resource.get("fipDashboard") else [])
                + ([f"https://doi.org/{citation['doi']}"] if citation and citation.get("doi") else [])
            ),
        }
        if citation:
            cited.append(resource_id)
            entity |= citation_properties(graph, citation, organizations, people, names)
            known = {item["@value"] if isinstance(item, dict) else item for item in as_list(entity["name"])}
            if citation.get("title") and citation["title"] not in known:
                entity["alternateName"] = citation["title"]
        # The guide's own list of a resource's languages wins over the cited work's language.
        entity["inLanguage"] = resource.get("languages") or entity.get("inLanguage")
        graph.add(entity, resource["id"])
    return cited


def link_resources(graph: Graph, resources: list[dict[str, Any]]) -> None:
    """Each station mentions the resources recommended at it."""
    for resource in resources:
        for station in resource.get("stations", []):
            station_entity = graph.entities.get(f"#station-{station}")
            if station_entity is not None:
                append_ref(station_entity, "mentions", f"#resource-{resource['id']}")


def repository_entity(repository: dict[str, Any], based_on: str) -> dict[str, Any]:
    identifiers = [value for value in (repository.get("re3data"), repository.get("nkr")) if value]
    same_as = []
    if repository.get("re3data"):
        same_as.append(f"https://www.re3data.org/repository/{repository['re3data']}")
    if repository.get("fairsharing"):
        same_as.append(f"https://doi.org/{repository['fairsharing']}")
    return {
        "@type": "DataCatalog",
        "name": text(repository["name"]),
        "url": repository.get("url"),
        "repositoryKind": ref(f"#rkind-{repository['kind']}") if repository.get("kind") else None,
        "keywords": text(repository.get("subjects"))
        or [{"@value": subject, "@language": "en"} for subject in repository.get("subjectsEn", [])],
        "identifier": identifiers,
        "inLanguage": repository.get("languages"),
        "sameAs": refs(same_as),
        "serviceStatus": ref(f"#status-{repository['status']}") if repository.get("status") else None,
        "statusAsOf": iso(repository["asOf"]) if repository.get("asOf") else None,
        "isBasedOn": [ref(based_on)],
    }


def repository_key(repository: dict[str, Any]) -> str:
    if repository.get("re3data"):
        return f"re3data:{repository['re3data']}"
    return "url:" + (repository.get("url") or repository["id"]).rstrip("/").lower()


def snapshot_id(snapshot: dict[str, Any]) -> str:
    return f"#snapshot-{slug(snapshot['snapshot']['source'])}"


def build_snapshots(graph: Graph, snapshots: list[dict[str, Any]]) -> list[str]:
    """Add one entity per snapshot, with its retrieval date and, for the FIP Dashboard, its disclaimer."""
    ids = []
    for snapshot in snapshots:
        info = snapshot["snapshot"]
        ids.append(
            graph.add(
                {
                    "@id": snapshot_id(snapshot),
                    "@type": "CreativeWork",
                    "name": f"Snapshot of {info['source']}",
                    "url": info.get("url"),
                    "dateCreated": iso(info["retrieved"]),
                    "license": info.get("license"),
                    "version": info.get("datasetVersion"),
                    "dateModified": info.get("datasetUpdated"),
                    "disclaimer": text(info.get("disclaimer")),
                },
                f"snapshot:{slug(info['source'])}",
            )
        )
    return ids


def build_repositories(
    graph: Graph, curated: list[dict[str, Any]], snapshots: list[dict[str, Any]], resources: list[dict[str, Any]]
) -> list[str]:
    """Merge the curated list, the repository-type resources and the snapshots: one entity per repository, crediting
    every source. A repository the guide recommends as a resource is that resource's entity."""
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    graph.add({"@id": "#repositories-curated", "@type": "CreativeWork", "name": "Curated repository list"})
    from_resources = [
        {key: resource[key] for key in ("id", "name", "url", "status", "asOf") if key in resource}
        | resource["repository"]
        | {"resource": f"#resource-{resource['id']}"}
        for resource in resources
        if resource.get("repository")
    ]
    sources = [("#repositories-curated", curated + from_resources)]
    for snapshot in snapshots:
        sources.append((snapshot_id(snapshot), snapshot.get("repository", [])))
    for based_on, repositories in sources:
        for repository in repositories:
            key = repository_key(repository)
            entity = repository_entity(repository, based_on)
            if key in merged:
                existing = merged[key]
                for prop, value in entity.items():
                    if prop == "isBasedOn":
                        existing["isBasedOn"] += [item for item in value if item not in existing["isBasedOn"]]
                    elif prop not in existing or existing[prop] in (None, [], ""):
                        existing[prop] = value
            else:
                entity["@id"] = repository.get("resource") or f"#repository-{repository['id']}"
                entity["_content_id"] = repository["id"]
                entity["_resource"] = bool(repository.get("resource"))
                merged[key] = entity
                order.append(key)
    repository_ids = []
    for key in order:
        entity = merged[key]
        content_id = entity.pop("_content_id")
        if entity.pop("_resource"):
            # The resource's entity takes the repository facts it does not state itself.
            resource = graph.entities[entity["@id"]]
            for prop in ("repositoryKind", "keywords", "isBasedOn"):
                if entity.get(prop) and not resource.get(prop):
                    resource[prop] = entity[prop]
            resource["sameAs"] = as_list(resource.get("sameAs")) + [
                item for item in as_list(entity.get("sameAs")) if item not in as_list(resource.get("sameAs"))
            ]
            if not resource["sameAs"]:
                del resource["sameAs"]
            repository_ids.append(entity["@id"])
            continue
        repository_ids.append(graph.add({"@id": entity.pop("@id"), **entity}, content_id))
    graph.add(
        {"@id": "#repositories", "@type": "CreativeWork", "name": "Repositories", "hasPart": refs(repository_ids)}
    )
    return repository_ids


DASHBOARD_FIP_CLASS = {
    "identifier-service": "Identifier-service",
    "metadata-schema": "Metadata-schema",
    "vocabulary": "Structured-vocabulary",
    "repository": "Registry",
    "access-protocol": "Communication-protocol",
    "authentication-service": "Authentication-and-authorization-service",
    "license": "Data-usage-license",
    "policy": "FAIR-Data-Policy",
    "provenance-model": "Provenance-model",
    "longevity-plan": "Metadata-preservation-policy",
    "tool": "FAIR-Supporting-Software",
}


def build_reviews(graph: Graph, item_id: str, verifications: list[dict[str, Any]]) -> list[str]:
    """Record catalogue verifications as schema.org reviews: verifier, level and date."""
    review_ids = []
    for number, verification in enumerate(verifications, start=1):
        review_id = f"{item_id}-verification-{number}"
        review_ids.append(review_id)
        graph.add(
            {
                "@id": review_id,
                "@type": "Review",
                "itemReviewed": ref(item_id),
                "author": ref(f"#fd-org-{verification['verifier']}"),
                "reviewAspect": verification.get("level"),
                "dateCreated": verification.get("date"),
                "url": verification.get("url"),
                "reviewBody": text(verification.get("note")),
            }
        )
    return review_ids


def build_fip_dashboard(graph: Graph, snapshots: list[dict[str, Any]]) -> list[str]:
    """Add the FIP Dashboard snapshot: organisations, FAIR-enabling resources with their verification, and FIPs."""
    snapshot = next((item for item in snapshots if item.get("fip") or item.get("resource")), None)
    if snapshot is None:
        return []
    based_on = ref(snapshot_id(snapshot))
    base = snapshot["snapshot"]["url"].rstrip("/")
    for organization in snapshot.get("organization", []):
        graph.add(
            {
                "@id": f"#fd-org-{organization['id']}",
                "@type": "Organization",
                "identifier": organization["id"],
                "name": text(organization["name"]),
                "alternateName": organization.get("acronym"),
                "url": organization.get("url"),
                "sameAs": refs([organization["ror"]] if organization.get("ror") else []),
            }
        )
    defined_terms(
        graph,
        "fd-types",
        "FIP Dashboard resource types",
        "fd-type",
        [{"id": item["id"], "name": item["label"]} for item in snapshot.get("resourceType", [])],
    )
    fer_ids = []
    for resource in snapshot.get("resource", []):
        fer_id = f"#fer-{resource['id']}"
        fer_ids.append(fer_id)
        fip_class = DASHBOARD_FIP_CLASS.get(resource.get("type", ""))
        review_ids = build_reviews(graph, fer_id, resource.get("verification", []))
        graph.add(
            {
                "@id": fer_id,
                "@type": "CreativeWork",
                "identifier": resource["id"],
                "name": resource["name"],
                "alternateName": resource.get("acronym"),
                "description": text(resource.get("description")),
                "url": resource.get("url"),
                "additionalType": FIP_TERMS + fip_class if fip_class else None,
                "catalogueType": ref(f"#fd-type-{resource['type']}") if resource.get("type") else None,
                "spatialCoverage": resource.get("scope"),
                "about": refs([principle_iri(principle) for principle in resource.get("principles", [])]),
                "provider": ref(f"#fd-org-{resource['provider']}") if resource.get("provider") else None,
                "sameAs": refs(
                    [f"{base}/resources/{resource['id']}"]
                    + ([resource["identifier"]] if resource.get("identifier") else [])
                ),
                "review": refs(review_ids),
                "isBasedOn": based_on,
            },
            f"fer:{resource['id']}",
        )
    fip_ids = []
    for fip in snapshot.get("fip", []):
        fip_id = f"#fip-{fip['id']}"
        fip_ids.append(fip_id)
        review_ids = build_reviews(graph, fip_id, fip.get("verification", []))
        declaration_ids = []
        for declaration in fip.get("declarations", []):
            declaration_id = f"{fip_id}-{declaration['principle']}-{declaration['resource']}"
            declaration_ids.append(declaration_id)
            graph.add(
                {
                    "@id": declaration_id,
                    "@type": "CreativeWork",
                    "additionalType": FIP_TERMS + "FIP-Declaration",
                    "about": ref(principle_iri(declaration["principle"])),
                    "mentions": ref(f"#fer-{declaration['resource']}"),
                    "creativeWorkStatus": declaration.get("status"),
                    "description": text(declaration.get("note")),
                    "isPartOf": ref(fip_id),
                }
            )
        graph.add(
            {
                "@id": fip_id,
                "@type": "CreativeWork",
                "additionalType": FIP_TERMS + "FAIR-Implementation-Profile",
                "identifier": fip["id"],
                "name": text(fip.get("title")),
                "alternateName": fip.get("acronym"),
                "abstract": text(fip.get("summary")),
                "keywords": text(fip.get("domain")),
                "version": fip.get("version"),
                "dateModified": fip.get("updated"),
                "creativeWorkStatus": fip.get("status"),
                "url": fip.get("url"),
                "author": ref(f"#fd-org-{fip['community']}") if fip.get("community") else None,
                "sameAs": ref(f"{base}/profiles/{fip['id']}"),
                "review": refs(review_ids),
                "hasPart": refs(declaration_ids),
                "isBasedOn": based_on,
            },
            f"fip:{fip['id']}",
        )
    graph.add(
        {
            "@id": "#fers",
            "@type": "CreativeWork",
            "name": "FAIR-enabling resources (FIP Dashboard)",
            "hasPart": refs(fer_ids),
        }
    )
    graph.add(
        {
            "@id": "#fips",
            "@type": "CreativeWork",
            "name": "FAIR Implementation Profiles (FIP Dashboard)",
            "hasPart": refs(fip_ids),
        }
    )
    return ["#fers", "#fips"]


def build_glossary(graph: Graph, glossary: dict[str, Any]) -> None:
    info = glossary.get("glossary")
    if not info:
        return
    term_ids = [f"#term-{term['id']}" for term in glossary.get("term", [])]
    graph.add(
        {
            "@id": "#glossary",
            "@type": "DefinedTermSet",
            "name": info["source"],
            "url": info.get("url"),
            "dateCreated": iso(info["retrieved"]) if info.get("retrieved") else None,
            "license": info.get("license"),
            "hasDefinedTerm": refs(term_ids),
        }
    )
    for term in glossary.get("term", []):
        graph.add(
            {
                "@id": f"#term-{term['id']}",
                "@type": "DefinedTerm",
                "termCode": str(term.get("heslarId", term["id"])),
                "name": text(term["label"]),
                "description": text(term.get("definition")),
                "url": term.get("url"),
                "inDefinedTermSet": ref("#glossary"),
            },
            f"term:{term['id']}",
        )


def build_callouts(graph: Graph, callouts: list[dict[str, Any]], all_lenses: list[str]) -> list[str]:
    callout_ids: list[str] = []
    for callout in callouts:
        callout_id = f"#callout-{callout['id']}"
        callout_ids.append(callout_id)
        item_ids = []
        for position, item in enumerate(callout.get("item", []), start=1):
            item_id = f"{callout_id}-{item['id']}"
            item_ids.append(item_id)
            graph.add(
                {
                    "@id": item_id,
                    "@type": "CreativeWork",
                    "identifier": item["id"],
                    "text": text(item["text"]),
                    "url": item.get("url"),
                    "position": position,
                    "audience": lens_refs(item.get("lenses", "*"), all_lenses),
                    "isPartOf": ref(callout_id),
                }
            )
        order = [f"{lens}: {', '.join(items)}" for lens, items in callout.get("order", {}).items()]
        graph.add(
            {
                "@id": callout_id,
                "@type": "CreativeWork",
                "identifier": callout["id"],
                "headline": text(callout["title"]),
                "text": text(callout.get("intro")),
                "hasPart": refs(item_ids),
                "lensOrder": order,
            },
            f"callout:{callout['id']}",
        )
        for station in callout.get("stations", []):
            station_entity = graph.entities.get(f"#station-{station}")
            if station_entity is not None:
                append_ref(station_entity, "hasPart", callout_id)
    return callout_ids


def build_tests(graph: Graph, live: dict[str, Any]) -> list[str]:
    champion = live.get("champion", {})
    test_ids = []
    for test in champion.get("test", []):
        test_id = f"#test-{test['id']}"
        test_ids.append(test_id)
        graph.add(
            {
                "@id": test_id,
                "@type": "CreativeWork",
                "additionalType": FTR_TEST,
                "identifier": test["id"],
                "name": text(test.get("label")) or test["id"],
                "url": champion["endpoint"].rstrip("/") + "/" + test["id"],
                "about": ref(principle_iri(test["principle"])) if test.get("principle") else None,
                "healthStatus": test.get("health"),
                "statusAsOf": iso(test["asOf"]) if test.get("asOf") else None,
            },
            f"test:{test['id']}",
        )
    return test_ids


WEB_APPLICATION = "https://schema.org/WebApplication"


def build_pages(graph: Graph, pages: list[dict[str, Any]]) -> list[str]:
    page_ids = []
    for page in pages:
        page_id = f"#page-{page['id']}"
        page_ids.append(page_id)
        section_ids = []
        for number, section in enumerate(page.get("section", []), start=1):
            section_id = f"{page_id}-{number}"
            section_ids.append(section_id)
            graph.add(
                {
                    "@id": section_id,
                    "@type": "CreativeWork",
                    "identifier": section.get("id"),
                    "headline": text(section.get("heading")),
                    "text": text(section["body"]),
                    "position": number,
                    "isPartOf": ref(page_id),
                }
            )
        graph.add(
            {
                "@id": page_id,
                "@type": "CreativeWork",
                "identifier": page["id"],
                "additionalType": WEB_APPLICATION if page.get("helper") else None,
                "headline": text(page["title"]),
                "description": text(page.get("description")),
                "hasPart": refs(section_ids),
            },
            f"page:{page['id']}",
        )
    return page_ids


def build_actions(graph: Graph, actions: list[dict[str, Any]], people: dict[str, str]) -> list[str]:
    action_ids = []
    for action in actions:
        action_id = f"#action-{action['id']}"
        action_ids.append(action_id)
        graph.add(
            {
                "@id": action_id,
                "@type": "UpdateAction" if action.get("type") == "update" else "CreateAction",
                "name": action["name"],
                "description": action.get("description"),
                "agent": ref(people.get(action["agent"], f"#person-{action['agent']}")),
                "instrument": refs([f"#instrument-{instrument}" for instrument in action.get("instruments", [])]),
                "object": refs(graph.resolve(action.get("objects", []))),
                "result": refs(graph.resolve(action.get("results", []))),
                "endTime": iso(action["endTime"]),
                "actionStatus": ref("http://schema.org/CompletedActionStatus"),
            },
            f"action:{action['id']}",
        )
    return action_ids


def build_crate(content: dict[str, Any], graph: Graph | None = None) -> dict[str, Any]:
    """The crate for the content; a caller that passes a graph can inspect it afterwards (the content checks read
    which entities each content ID names)."""
    guide_file = content["guide"]
    guide = guide_file["guide"]
    vocabulary_base = guide["vocabularyBase"]
    all_lenses = [lens["id"] for lens in guide_file.get("lens", [])]
    graph = graph if graph is not None else Graph()

    graph.add(
        {
            "@id": CRATE_FILE,
            "@type": "CreativeWork",
            "conformsTo": ref(RO_CRATE),
            "about": ref("./"),
        }
    )
    graph.add({"@id": "./", "@type": "Dataset"})  # completed below, after its parts exist
    graph.add(
        {"@id": PROCESS_RUN_CRATE, "@type": ["CreativeWork", "Profile"], "name": "Process Run Crate", "version": "0.5"}
    )
    graph.add(
        {
            "@id": guide["profile"],
            "@type": ["CreativeWork", "Profile"],
            "name": "EOSC CZ FAIR guide profile",
            "version": guide["profile"].rstrip("/").rsplit("/", 1)[-1],
            "url": guide["url"].rstrip("/") + "/tree/main/profile/fair-guide",
        }
    )

    organizations = build_organizations(graph, guide_file)
    people = build_people(graph, guide_file, organizations)
    build_instruments(graph, guide_file)
    build_terms(graph, vocabulary_base)
    build_principles(graph, content["principles"])
    names = {person["id"]: person["name"] for person in guide_file.get("person", [])}
    source_ids = build_sources(graph, content["sources"], organizations, people, names)
    build_vocabularies(graph, guide_file)
    build_glossary(graph, content["glossary"])
    # Resources exist before the ledger, because a clause may cite a resource; the stations they are recommended at
    # are linked once the stations exist.
    cited_resource_ids = build_resources(
        graph, content["resources"], all_lenses, organizations=organizations, people=people, names=names
    )
    graph.add(
        {
            "@id": "#sources",
            "@type": "CreativeWork",
            "name": "Cited sources",
            "hasPart": refs(source_ids + cited_resource_ids),
        }
    )
    build_ledger(graph, content["ledger"])
    build_stations(graph, content["stations"], all_lenses)
    link_resources(graph, content["resources"])
    check_ids = build_checks(graph, content["checks"], content["live"].get("links", {}))
    snapshot_ids = build_snapshots(graph, content["snapshots"])
    build_repositories(graph, content["repositories"], content["snapshots"], content["resources"])
    catalogue_ids = build_fip_dashboard(graph, content["snapshots"])
    callout_ids = build_callouts(graph, content["callouts"], all_lenses)
    test_ids = build_tests(graph, content["live"])
    page_ids = build_pages(graph, content["pages"])
    action_ids = build_actions(graph, content["provenance"], people)

    licenses = []
    for spdx in ("CC-BY-4.0", "MIT"):
        license_id, license_name, license_description = LICENSES[spdx]
        licenses.append(license_id)
        graph.add(
            {
                "@id": license_id,
                "@type": "CreativeWork",
                "name": license_name,
                "identifier": spdx,
                "description": license_description,
            }
        )
    graph.add(
        {
            "@id": PAGE_FILE,
            "@type": "File",
            "name": "FAIR guide page",
            "description": "The guide page, which is also the crate's HTML preview; it loads the crate from "
            + KB_SCRIPT
            + ".",
            "encodingFormat": "text/html",
            "license": refs(licenses),
        }
    )

    root = {
        "@id": "./",
        "@type": "Dataset",
        "name": text(guide["name"]),
        "description": text(guide["description"]),
        "version": guide["version"],
        "creativeWorkStatus": guide.get("releaseStatus"),
        "disambiguatingDescription": text(guide.get("testingNotice"))
        if guide.get("releaseStatus") == "testing"
        else None,
        "datePublished": iso(guide["datePublished"]),
        "inLanguage": list(LANGS),
        "url": guide.get("url"),
        "keywords": text(guide.get("keywords")),
        "license": ref(LICENSES["CC-BY-4.0"][0]),
        "editor": refs([people[person] for person in guide.get("editors", [])]),
        "contributor": refs([people[person] for person in guide.get("contributors", [])]),
        "publisher": ref(organizations[guide["publisher"]]) if guide.get("publisher") else None,
        "funder": ref(organizations[guide["funder"]]) if guide.get("funder") else None,
        "creditText": text(guide.get("acknowledgement")),
        "usageInfo": text(guide.get("aiStatement")),
        "isBasedOn": refs(graph.resolve(guide.get("isBasedOn", []))),
        "conformsTo": refs([PROCESS_RUN_CRATE, guide["profile"]]),
        "mainEntity": ref("#path"),
        "about": refs([principle_iri(principle["id"]) for principle in content["principles"]]),
        "hasPart": refs([PAGE_FILE]),
        "mentions": refs(
            action_ids
            + ["#ledger", "#sources", "#repositories"]
            + catalogue_ids
            + snapshot_ids
            + check_ids
            + callout_ids
            + test_ids
            + page_ids
        ),
    }
    graph.entities["./"] = prune(root)
    link_texts(graph, reference_targets(content, graph))

    context: dict[str, Any] = {term: vocabulary_base + term for term in TERMS}
    return {"@context": [f"{RO_CRATE}/context", context], "@graph": list(graph.entities.values())}


# ---------------------------------------------------------------------------
# Page blocks


def script_json(value: Any) -> str:
    """Serialise JSON safely for embedding in an HTML <script> element."""
    serialised = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    for char, escape in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), (" ", "\\u2028"), (" ", "\\u2029")):
        serialised = serialised.replace(char, escape)
    return serialised


def build_credits(content: dict[str, Any]) -> list[dict[str, Any]]:
    """The roles shown on the about page: who wrote the content basis, who compiled and reviewed the guide, the
    tools used and the funding."""
    guide_file = content["guide"]
    guide = guide_file["guide"]
    persons = {person["id"]: person for person in guide_file.get("person", [])}
    sources = {source["id"]: source for source in content["sources"]}
    organizations = {organization["id"]: organization for organization in guide_file.get("organization", [])}

    def person(entry: str) -> dict[str, Any]:
        found = persons.get(entry)
        return {"name": found["name"], "url": found.get("orcid")} if found else {"name": entry}

    credits: list[dict[str, Any]] = [
        {
            "role": "analysis",
            "work": text(sources[source]["title"]),
            "people": [person(a) for a in sources[source].get("authors", [])],
        }
        for source in guide.get("isBasedOn", [])
        if source in sources
    ]
    credits.append({"role": "editor", "people": [person(entry) for entry in guide.get("editors", [])]})
    credits.append({"role": "review", "people": [person(entry) for entry in guide.get("reviewers", [])]})
    used = {tool for action in content["provenance"] for tool in action.get("instruments", [])}
    tools = [tool for tool in guide_file.get("instrument", []) if tool["id"] in used]
    credits.append({"role": "tools", "people": [{"name": tool["name"], "url": tool.get("url")} for tool in tools]})
    funding = []
    project = organizations.get(guide.get("funder", ""))
    while project:
        name = project["name"]
        label = name if isinstance(name, dict) else dict.fromkeys(LANGS, name)
        if project.get("identifier"):
            label = {lang: f"{value} ({project['identifier']})" for lang, value in label.items()}
        funding.append({"name": text(label), "url": project.get("url")})
        project = organizations.get(project.get("funder", ""))
    credits.append({"role": "funding", "people": funding})
    return [credit for credit in credits if credit["people"]]


RE3DATA_FACTS = (
    "pidTypes",
    "apis",
    "dataLicenses",
    "certificates",
    "metadataStandards",
    "policies",
    "versioning",
    "qualityManagement",
)


def re3data_facts(content: dict[str, Any]) -> dict[str, Any]:
    """The re3data facts the self-check can pre-fill from, per r3d identifier, with the snapshot's date."""
    snapshot = next(
        (item for item in content["snapshots"] if item.get("snapshot", {}).get("source") == "re3data"), None
    )
    if not snapshot:
        return {}
    date = iso(snapshot["snapshot"]["retrieved"])
    return {
        str(repository["re3data"]).lower(): {"name": repository["name"], "date": date}
        | {key: repository[key] for key in RE3DATA_FACTS if key in repository}
        for repository in snapshot.get("repository", [])
        if repository.get("re3data")
    }


def page_config(content: dict[str, Any], text_links: dict[str, list[dict[str, str]]] | None = None) -> dict[str, Any]:
    guide = content["guide"]["guide"]
    live = content["live"]
    champion = {key: value for key, value in live.get("champion", {}).items() if key != "test"}
    return {
        "ui": content["ui"],
        "config": {
            "version": guide["version"],
            "releaseStatus": guide.get("releaseStatus"),
            "testingNotice": guide.get("testingNotice") if guide.get("releaseStatus") == "testing" else None,
            "datePublished": iso(guide["datePublished"]),
            "freshnessDays": guide.get("freshnessDays", 180),
            "pageUrl": guide.get("pageUrl"),
            "textLinks": text_links or {},
            "connectors": live.get("connector", []),
            "links": live.get("links", {}),
            "champion": champion,
            "nanopub": live.get("nanopub"),
            "dmpStatus": live.get("dmpStatus"),
            "fairsharing": live.get("fairsharing"),
            "vocab": {
                "roCrate": RO_CRATE,
                "ftr": FTR,
                "prov": PROV,
                "fipTerms": FIP_TERMS,
                "guide": guide["vocabularyBase"],
                "webApplication": WEB_APPLICATION,
            },
            "icons": {
                "ui": content.get("icons", {}).get("ui", {}),
                "stage": {
                    stage["id"]: stage["icon"] for stage in content["guide"].get("stage", []) if stage.get("icon")
                },
                "lens": {lens["id"]: lens["icon"] for lens in content["guide"].get("lens", []) if lens.get("icon")},
                "level": {
                    level["id"]: level["icon"] for level in content["guide"].get("level", []) if level.get("icon")
                },
                "station": {
                    data["station"]["id"]: data["station"]["icon"]
                    for data in content["stations"]
                    if data["station"].get("icon")
                },
                "block": {
                    f"{data['check']['id']}-{block['id']}": block["icon"]
                    for data in content["checks"]
                    for block in data.get("block", [])
                    if block.get("icon")
                },
                "check": {
                    data["check"]["id"]: data["check"]["icon"]
                    for data in content["checks"]
                    if data["check"].get("icon")
                },
                "page": {page["id"]: page["icon"] for page in content["pages"] if page.get("icon")},
            },
            "credits": build_credits(content),
            "pageMenu": {page["id"]: page["menu"] for page in content["pages"] if page.get("menu")},
            "re3data": re3data_facts(content),
            "tasks": [
                {key: task[key] for key in ("lens", "label", "href", "icon") if key in task}
                for task in content["guide"].get("task", [])
            ],
        },
    }


def content_security_policy(content: dict[str, Any]) -> str:
    origins = sorted({connector["origin"] for connector in content["live"].get("connector", [])})
    directives = [
        "default-src 'self'",
        # file: keeps the page working when it is opened from disk; it adds nothing on a web host.
        "script-src 'self' file:",
        "style-src 'self' file:",
        "img-src 'self' data: file:",
        "font-src 'self' file:",
        "connect-src " + " ".join(origins or ["'none'"]),
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'none'",
    ]
    return "; ".join(directives)


BLOCK = re.compile(r"(<!-- generated:(?P<name>[a-z]+) -->)(?P<body>.*?)(<!-- /generated:(?P=name) -->)", re.S)


def icon_sprite(icons_dir: Path) -> str:
    """Inline SVG sprite of the vendored icons, keeping the icons' licence notice once."""
    files = sorted(icons_dir.glob("*.svg")) if icons_dir.is_dir() else []
    if not files:
        return ""
    symbols = []
    notice = ""
    for path in files:
        svg = path.read_text(encoding="utf-8")
        notice = notice or (re.search(r"<!--!?(.*?)-->", svg, re.S) or [None, ""])[1].strip()
        view_box = re.search(r'viewBox="([^"]+)"', svg)
        paths = "".join(re.findall(r"<path[^>]*/>", svg))
        if view_box and paths:
            symbols.append(f'<symbol id="i-{path.stem}" viewBox="{view_box.group(1)}">{paths}</symbol>')
    comment = f"<!-- {notice} -->" if notice else ""
    return f'\n    {comment}<svg class="sprite" aria-hidden="true" focusable="false">{"".join(symbols)}</svg>\n    '


def data_script(key: str, value: Any, about: str) -> str:
    """A classic script that hands generated data to the page. Unlike fetching a JSON file, it also works when the
    page is opened from disk."""
    return (
        f"/* {about} Generated by scripts/build_crate.py from content/; do not edit. */\n"
        "window.FairGuideData = window.FairGuideData || {};\n"
        f"window.FairGuideData.{key} = {script_json(value)};\n"
    )


SUMMARY_KEYS = ("name", "description", "version", "datePublished", "inLanguage", "keywords", "license")


def page_summary(crate: dict[str, Any], page_url: str | None) -> dict[str, Any]:
    """What search engines read in the page head: the guide as a schema.org dataset distributed as the crate."""
    root = next(entity for entity in crate["@graph"] if entity["@id"] == "./")
    summary: dict[str, Any] = {"@context": "https://schema.org", "@type": "Dataset"}
    if page_url:
        summary["url"] = page_url
    summary.update({key: root[key] for key in SUMMARY_KEYS if key in root})
    summary["distribution"] = {
        "@type": "DataDownload",
        "contentUrl": (page_url or "") + CRATE_FILE,
        "encodingFormat": "application/ld+json",
    }
    return summary


def render_page(page: str, content: dict[str, Any], crate: dict[str, Any], sprite: str = "") -> str:
    summary = script_json(page_summary(crate, page_config(content)["config"]["pageUrl"]))
    blocks = {
        "csp": f'\n    <meta http-equiv="Content-Security-Policy" content="{content_security_policy(content)}">\n    ',
        "kb": f'\n    <script type="application/ld+json">{summary}</script>'
        f'\n    <script src="{KB_SCRIPT}" defer></script>\n    ',
        "ui": f'\n    <script src="{UI_SCRIPT}" defer></script>\n    ',
        "icons": sprite,
    }
    required = {"csp", "kb", "ui"}
    found = {match.group("name") for match in BLOCK.finditer(page)}
    missing = sorted(required - found)
    if missing:
        raise ContentError(f"{PAGE_FILE}: missing generated block markers: {', '.join(missing)}")
    return BLOCK.sub(lambda match: match.group(1) + blocks[match.group("name")] + match.group(4), page)


# ---------------------------------------------------------------------------
# Entry point


def outputs(root: Path = ROOT) -> dict[str, str]:
    content = load_content(root / "content")
    graph = Graph()
    crate = build_crate(content, graph)
    page = render_page(
        (root / PAGE_FILE).read_text(encoding="utf-8"), content, crate, icon_sprite(root / "assets" / "icons")
    )
    return {
        CRATE_FILE: json.dumps(crate, ensure_ascii=False, indent=2) + "\n",
        KB_SCRIPT: data_script("kb", crate, "The knowledge base, the same RO-Crate as ro-crate-metadata.json."),
        UI_SCRIPT: data_script("ui", page_config(content, graph.text_links), "Interface strings and configuration."),
        PAGE_FILE: page,
        PREVIEW_FILE: page,
    }


def page_payload(generated: dict[str, str], root: Path = ROOT) -> dict[str, int]:
    """Compressed bytes of each file the page loads, read from the page's own script and stylesheet tags; a file the
    build generates is measured as generated."""
    page = generated[PAGE_FILE]
    files = [PAGE_FILE] + [match.group("script") or match.group("style") for match in PAGE_ASSET.finditer(page)]
    sizes = {}
    for name in files:
        text = generated[name] if name in generated else (root / name).read_text(encoding="utf-8")
        sizes[name] = len(gzip.compress(text.encode("utf-8"), compresslevel=9, mtime=0))
    return sizes


def payload_warning(sizes: dict[str, int], budget_kb: int) -> str | None:
    """The warning for a page over its budget, naming the largest parts; None within the budget."""
    total = sum(sizes.values())
    if total <= budget_kb * 1024:
        return None
    largest = sorted(sizes.items(), key=lambda item: -item[1])[:3]
    parts = ", ".join(f"{name} {size / 1024:.0f} KB" for name, size in largest)
    return f"the page downloads {total / 1024:.0f} KB compressed, over its budget of {budget_kb} KB; largest: {parts}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare instead of writing; exit 1 on differences")
    parser.add_argument("--sizes", action="store_true", help="print what the page downloads, compressed")
    args = parser.parse_args(argv)
    try:
        generated = outputs()
    except (ContentError, KeyError) as error:
        print(f"build_crate: {error}", file=sys.stderr)
        return 2

    stale = []
    for name, value in generated.items():
        path = ROOT / name
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current == value:
            continue
        if args.check:
            stale.append(name)
            diff = difflib.unified_diff(
                current.splitlines(),
                value.splitlines(),
                f"{name} (committed)",
                f"{name} (regenerated)",
                lineterm="",
                n=1,
            )
            print("\n".join(list(diff)[:60]))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8", newline="\n")
            print(f"wrote {name}")
    sizes = page_payload(generated)
    if args.sizes:
        for name, size in sorted(sizes.items(), key=lambda item: -item[1]):
            print(f"{size / 1024:8.1f} KB  {name}")
        print(f"{sum(sizes.values()) / 1024:8.1f} KB  total compressed (budget {PAGE_BUDGET_KB} KB)")
    warning = payload_warning(sizes, PAGE_BUDGET_KB)
    if warning:
        print(f"warning: {warning}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::warning title=Page size::{warning}")
    if stale:
        print(f"build_crate: out of date: {', '.join(stale)}; run python scripts/build_crate.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
