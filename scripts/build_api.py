#!/usr/bin/env python3
"""Generate the FAIR guide's static read-only API from its knowledge base.

The API is a view over the crate that ``build_crate.py`` builds; ``build_crate.api_records`` decides what it
publishes. It is written into the site directory, which is not committed (``_site/`` by default):

- ``api/v1/<kind>.json`` and ``api/v1/<kind>/<id>.json``: kind lists and records, with nested scope paths where the
  identity has one, language maps and ``api/v1/context.jsonld``. Records link each other by relative paths, refer to
  terms in their set documents and name the entity's identifier in the crate or outside the guide in ``sameAs``;
- ``api/v1/index.json``: what API v1 offers and what it is built from;
- ``api/tests/<question>.json`` keeps describing its question for results saved by earlier releases, which name it;
- ``openapi.json``: the OpenAPI 3.1 description, with a server address relative to it;
- ``api/index.html``: the interactive documentation, the authored files in ``api/`` with the pinned Swagger UI
  package that ``npm ci`` installs.

Paths are derived from the Guide's kind, scope and identifier addresses. Every kind has one list and one record
operation in the OpenAPI description; vocabulary terms resolve through their set document.

    python scripts/build_api.py [--out DIR]

Uses only the Python standard library. Checked by ``tests/test_scripts.py`` and ``npm run check:api``.
"""

from __future__ import annotations

import argparse
import copy
import json
import posixpath
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

import build_crate as kb
import check_health
from landing_pages import pages as landing_pages

SITE = kb.ROOT / "_site"
OPENAPI_FILE = kb.API_FILES["description"]
CONTEXT_FILE = kb.API_FILES["context"]
META_FILE = kb.API_FILES["index"]
HEALTH_FILE = kb.API_FILES["health"]
DOCS_DIR = kb.ROOT / "api"
SWAGGER_DIR = kb.ROOT / "node_modules" / "swagger-ui-dist"
SWAGGER_FILES = ("swagger-ui-bundle.js", "swagger-ui.css", "LICENSE", "NOTICE")
SCHEMA_ORG = "http://schema.org/"
DQV = "http://www.w3.org/ns/dqv#"
DCAT = "http://www.w3.org/ns/dcat#"
SIO = kb.SIO

# Entities small enough to repeat in full inside the records that name them.
EMBEDDED_TYPES = {
    "DefinedTerm",
    "Audience",
    "Action",
    "EntryPoint",
    "Person",
    "Organization",
    "PropertyValue",
    "PrefillMapping",
}
TERMS: dict[str, Any] = {
    "@vocab": SCHEMA_ORG,
    "ftr": kb.FTR,
    "dqv": DQV,
    "dcat": DCAT,
    "foaf": kb.FOAF,
    "sio": SIO,
    "prov": kb.PROV,
    "Benchmark": "ftr:Benchmark",
    "Metric": "ftr:Metric",
    "Test": "ftr:Test",
    "hasBenchmark": {"@id": "ftr:hasBenchmark", "@type": "@id"},
    "inDimension": {"@id": "dqv:inDimension", "@type": "@id"},
    "isImplementationOf": {"@id": "sio:SIO_000233", "@type": "@id"},
    "hasImplementation": {"@id": "sio:SIO_000234", "@type": "@id"},
    "landingPage": {"@id": "dcat:landingPage", "@type": "@id"},
    # A principle's record lists what is about it, which the crate states from the other side.
    "clauses": {"@reverse": SCHEMA_ORG + "about", "@type": "@id"},
    "advice": {"@reverse": SCHEMA_ORG + "about", "@type": "@id"},
    "stations": {"@reverse": SCHEMA_ORG + "about", "@type": "@id"},
    # A check's record lists the questions that name it as their benchmark; registry records likewise name their thing.
    "questions": {"@reverse": kb.FTR + "hasBenchmark", "@type": "@id"},
    "records": {"@reverse": kb.FOAF + "primaryTopic", "@type": "@id"},
    "members": {"@reverse": SCHEMA_ORG + "inDefinedTermSet", "@type": "@id"},
    "address": kb.DCTERMS + "identifier",
    "iri": {"@type": "@id"},
    "label": SCHEMA_ORG + "name",
}


def is_language_list(value: Any) -> bool:
    values = kb.as_list(value)
    return bool(values) and all(isinstance(item, dict) and "@language" in item for item in values)


def language_map(value: Any) -> dict[str, Any]:
    """Language-tagged values as a JSON-LD language map: one string per language, a list where there are several."""
    grouped: dict[str, list[str]] = {}
    for item in kb.as_list(value):
        grouped.setdefault(item["@language"], []).append(item["@value"])
    return {language: texts[0] if len(texts) == 1 else texts for language, texts in grouped.items()}


def ids(value: Any) -> list[str]:
    return [item["@id"] for item in kb.as_list(value) if isinstance(item, dict) and "@id" in item]


class Api:
    """The API's files, built from the crate."""

    def __init__(self, crate: dict[str, Any], content: dict[str, Any], *, graph: kb.Graph | None = None) -> None:
        self.graph = graph
        self.crate = crate
        self.content = content
        self.strings = content["ui"]["api"]
        self.entities = {entity["@id"]: entity for entity in crate["@graph"]}
        self.base = content["guide"]["guide"]["recordBase"]
        self.records = kb.api_records(self.entities, content)
        self.registry_records = kb.records_by_thing(self.entities)
        self.paths = {
            entity_id: kb.API_FILES["record"].format(record=kb.record_address(entity_id, self.base))
            for name, members in self.records.items()
            for record, entity_id in members
        }
        self.term_codes: dict[str, set[str]] = {}
        for term in self.entities.values():
            if "DefinedTerm" not in kb.as_list(term.get("@type")) or not term.get("termCode"):
                continue
            for set_id in ids(term.get("inDefinedTermSet")):
                address = kb.record_address(set_id, self.base)
                if address and address.startswith("vocabularies/"):
                    self.term_codes.setdefault(address.removeprefix("vocabularies/"), set()).add(term["termCode"])
        # The document each check question had as its test in earlier releases, which saved results still name.
        self.tests = {
            entity_id: kb.API_FILES["test"].format(id=record) for record, entity_id in self.records["questions"]
        }
        clash = {record for record, _ in self.records["tests"]} & {record for record, _ in self.records["questions"]}
        if clash:
            raise kb.ContentError(f"a check question and an automated test share the API record tests/{min(clash)}")
        # Entities without a record of their own in this API (advice and its steps, callouts, FIP declarations) live
        # in the record of what they are part of, under a fragment their address names.
        placed = True
        while placed:
            placed = False
            for entity_id, entity in self.entities.items():
                address = kb.guide_address(entity_id, self.base)
                if entity_id in self.paths or address is None:
                    continue
                # A part names the record it belongs to, or is a fragment under the record that names it.
                record = entity_id.split("#")[0]
                whole = next((whole for whole in ids(entity.get("isPartOf")) if whole in self.paths), None) or (
                    record if "#" in entity_id and record in self.paths else None
                )
                if whole:
                    # The actual part fragment (#knav, #step-2, #action), not a repeated full-path slug.
                    fragment = address.split("#", 1)[1] if "#" in address else address.rsplit("/", 1)[-1]
                    self.paths[entity_id] = self.paths[whole].split("#")[0] + "#" + fragment
                    placed = True
        self.language_keys: set[str] = set()
        self.reference_keys: set[str] = {"sameAs", "additionalType"}
        self.given: set[str] = set()  # the parts given in full in the record being built; later mentions link them

    # ------------------------------------------------------------------ identifiers and links

    @staticmethod
    def site_root(here: str) -> str:
        """The site's root as a path relative to a file of the API, so nothing names the address the site lives at."""
        return posixpath.relpath(".", posixpath.dirname(here)) + "/"

    def iri(self, entity_id: str, here: str) -> str:
        """An entity's identifier outside the API: an outside IRI as it is, the guide's own entities by their place in
        the crate, relative to the file that names them."""
        if "://" in entity_id:
            return entity_id
        if entity_id.startswith("#"):
            return self.site_root(here) + kb.CRATE_FILE + entity_id
        return self.site_root(here) + entity_id.removeprefix("./")

    @staticmethod
    def relative(here: str, target: str) -> str:
        path, _, fragment = target.partition("#")
        if path == here:
            return "#" + fragment if fragment else posixpath.basename(path)
        return posixpath.relpath(path, posixpath.dirname(here)) + ("#" + fragment if fragment else "")

    def reference(self, target: str, here: str, depth: int) -> Any:
        """A link to another record, a part of this record (in full where it is first named), a small term in full,
        or an identifier."""
        term = self.entities.get(target)
        if term and kb.kind_of(target, self.base) == "vocabularies" and "DefinedTerm" in kb.as_list(term.get("@type")):
            set_id = ids(term.get("inDefinedTermSet"))[0]
            set_path = self.paths.get(set_id)
            if set_path:
                # One set document per scheme, with a fragment per term: no repeated embedded term records.
                return {
                    "@id": self.relative(here, set_path) + "#" + term.get("termCode") or term["identifier"],
                    "termCode": term.get("termCode") or term["identifier"],
                }
        path = self.paths.get(target)
        if path and path.startswith(here + "#") and target not in self.given:
            self.given.add(target)
            return self.node(self.entities[target], here, depth)
        if path:
            return self.relative(here, path)
        entity = self.entities.get(target)
        local_document = (
            entity is not None
            and "CreativeWork" in kb.as_list(entity.get("@type"))
            and any(
                "File" in kb.as_list(self.entities.get(parent, {}).get("@type"))
                for parent in ids(entity.get("isPartOf"))
            )
        )
        if (
            entity is not None
            and depth == 0
            and (set(kb.as_list(entity.get("@type"))) & EMBEDDED_TYPES or local_document)
        ):
            return self.node(entity, here, 1)
        return self.iri(target, here)

    # ------------------------------------------------------------------ records

    def value(self, key: str, value: Any, here: str, depth: int) -> Any:
        if is_language_list(value):
            self.language_keys.add(key)
            return language_map(value)
        if isinstance(value, list):
            return [self.value(key, item, here, depth) for item in value]
        if isinstance(value, dict):
            if set(value) == {"@id"}:
                self.reference_keys.add(key)
                # An identifier in sameAs stays an identifier.
                return self.reference(value["@id"], here, 1 if key == "sameAs" else depth)
            if "@value" in value:
                return value["@value"]
            return {inner: self.value(inner, item, here, depth) for inner, item in value.items()}
        return value

    def node(self, entity: dict[str, Any], here: str, depth: int) -> dict[str, Any]:
        entity_id = entity["@id"]
        path = self.paths.get(entity_id)
        own = self.relative(here, path) if path else self.iri(entity_id, here)
        node: dict[str, Any] = {"@id": own, "@type": entity["@type"]}
        for key, value in entity.items():
            if key in ("@id", "@type"):
                continue
            name = key
            if (
                key == "url"
                and isinstance(value, str)
                and value.split("#", 1)[0] in self.entities
                and "://" not in value
            ):
                self.reference_keys.add(name)
                node[name] = self.site_root(here) + value.removeprefix("./")
            else:
                node[name] = self.value(name, value, here, depth)
        return node

    def record(self, collection: str, record: str, entity_id: str, here: str | None = None) -> dict[str, Any]:
        here = here or self.paths[entity_id]
        entity = self.entities[entity_id]
        self.given = set()
        node = self.node(entity, here, 0)
        types = kb.as_list(node["@type"])
        same = [self.iri(entity_id, here)] + [
            link for link in kb.as_list(node.get("sameAs")) if link != self.iri(entity_id, here)
        ]
        out = (
            {"@context": self.relative(here, CONTEXT_FILE)}
            | node
            | {
                "@type": types,
                "identifier": node.get("identifier", Path(record).name),
                "sameAs": same,
            }
        )
        # A record names its registry records in full under their fragments, from the record side's primaryTopic.
        registry = self.registry_records.get(entity_id, [])
        if registry:
            out["records"] = [self.node(self.entities[record_id], here, 0) for record_id in registry]
        if collection == "vocabularies":
            members = [member for member in self.entities.values() if entity_id in ids(member.get("inDefinedTermSet"))]
            out["members"] = []
            for member in members:
                doc = self.node(member, here, 0)
                doc["@id"] = "#" + (member.get("termCode") or member["identifier"])
                out["members"].append(doc)
        if collection == "principles":
            out |= self.about_principle(entity_id, here)
        if collection == "checks":
            questions = [
                question
                for _, question in self.records["questions"]
                if entity_id in ids(self.entities[question].get("hasBenchmark"))
            ]
            questions.sort(key=lambda question: self.entities[question].get("position", 0))
            out["questions"] = [self.relative(here, self.paths[question]) for question in questions]
        if collection == "questions":
            local = [
                test_id
                for _, test_id in self.records["tests"]
                if entity_id in ids(self.entities[test_id].get("isImplementationOf"))
            ]
            implementations = [self.relative(here, self.paths[test_id]) for test_id in local]
            if implementations:
                out["hasImplementation"] = implementations if len(implementations) > 1 else implementations[0]
        return out

    def about_principle(self, principle: str, here: str) -> dict[str, Any]:
        """What the crate says is about a principle: its requirements and findings, the advice that cites them (each
        with its lens), the stations that address it and the check questions that test it."""

        def members(collection: str) -> list[str]:
            return [entity_id for _, entity_id in self.records[collection]]

        def about(entity_id: str) -> bool:
            entity = self.entities[entity_id]
            return principle in ids(entity.get("about")) + ids(entity.get("inDimension"))

        clauses = [entity_id for entity_id in members("clauses") if about(entity_id)]
        cited = set(clauses)
        advice = [
            entity_id
            for entity_id, entity in self.entities.items()
            if kb.kind_of(entity_id, self.base) == "advice"
            and "#" not in entity_id
            and cited & set(ids(entity.get("citation")))
        ]
        return {
            "clauses": [self.relative(here, self.paths[entity_id]) for entity_id in clauses],
            "advice": [self.node(self.entities[entity_id], here, 0) for entity_id in advice],
            "stations": [
                self.relative(here, self.paths[entity_id]) for entity_id in members("stations") if about(entity_id)
            ],
            "questions": [
                self.relative(here, self.paths[entity_id]) for entity_id in members("questions") if about(entity_id)
            ],
        }

    def saved_result_reference(self, record: str, entity_id: str) -> dict[str, Any]:
        """The document a check question had as its test in earlier releases, which their saved results name. A
        person answering a question is no FTR test, so it is no test now: it describes the question and links it."""
        here = self.tests[entity_id]
        check = self.entities[ids(self.entities[entity_id].get("hasBenchmark"))[0]]
        lens = ids(check.get("audience"))[0].rsplit("/", 1)[-1]
        strings = self.strings["test"]
        context = self.entities[entity_id].get("assessmentContext", False)
        self.language_keys.update(("name", "description"))
        return {
            "@context": self.relative(here, CONTEXT_FILE),
            "@id": posixpath.basename(here),
            "@type": "CreativeWork",
            "identifier": record,
            "name": {language: text.format(id=record) for language, text in strings["name"].items()},
            "description": strings["contextDescription"] if context else strings["description"],
            **({"assessmentContext": True} if context else {}),
            "about": self.relative(here, self.paths[entity_id]),
            "landingPage": f"{self.site_root(here)}#/{kb.LANGS[0]}/{lens}/check/{check['identifier']}",
        }

    FILTER_FIELDS = {
        "advice": ("isPartOf", "audience", "disclosureLevel", "adviceKind", "about", "text"),
        "questions": ("hasBenchmark", "tier", "inDimension", "appliesTo", "fixAt", "fixedBy", "prefillMapping"),
        "resources": ("resourceType", "audience", "mentions", "serviceStatus", "statusAsOf", "repositoryFunction"),
        "repositories": ("repositoryKind", "serviceStatus", "acceptsDeposits", "identifier", "alternateIdentifier"),
        "clauses": ("isPartOf", "about", "clauseKind", "audience", "clauseStatus"),
        "tests": ("isImplementationOf", "about", "healthStatus"),
    }
    DEFAULT_FILTER_FIELDS = ("position", "termPosition")

    def filter_fields(self, collection: str) -> tuple[str, ...]:
        """Fields every summary in this list can actually be filtered on; an absent optional field is not a filter."""
        if collection in self.FILTER_FIELDS:
            return self.FILTER_FIELDS[collection]
        records = self.records[collection]
        return tuple(
            key
            for key in self.DEFAULT_FILTER_FIELDS
            if records and all(key in self.entities[entity_id] for _, entity_id in records)
        )

    def summary(self, entity_id: str, collection: str) -> dict[str, Any]:
        """A list entry with its ID, address, persistent IRI, label and the fields a client filters on."""
        entity = self.entities[entity_id]
        address = kb.record_address(entity_id, self.base)
        _, scope, identifier = kb.split_address(address)
        path = self.paths[entity_id]
        label = next((entity[key] for key in ("name", "headline", "text") if entity.get(key)), identifier)
        summary = {
            "@id": self.relative(f"api/v1/{collection}.json", path),
            "@type": entity["@type"],
            "identifier": identifier,
            "address": address,
            "iri": entity_id,
            "label": language_map(label) if is_language_list(label) else label,
        }
        if scope:
            summary["scope"] = scope
        for key in self.filter_fields(collection):
            if key in entity:
                summary[key] = self.value(key, entity[key], f"api/v1/{collection}.json", 0)
        return summary

    def collection(self, collection: str) -> dict[str, Any]:
        here = f"api/v1/{collection}.json"
        summaries = [self.summary(entity_id, collection) for _, entity_id in self.records[collection]]
        self.language_keys.update(("name", "description", "label"))
        strings = self.strings["collection"].get(collection, {})
        name = strings.get("name", {"cs": collection, "en": collection})
        description = strings.get("description", {"cs": name["cs"], "en": name["en"]})
        return {
            "@context": self.relative(here, CONTEXT_FILE),
            "@id": posixpath.basename(here),
            "@type": "ItemList",
            "name": name,
            "description": description,
            "filterFields": list(self.filter_fields(collection)),
            "numberOfItems": len(summaries),
            "itemListElement": summaries,
        }

    def index(self) -> dict[str, Any]:
        """What API v1 offers: every kind's list, the vocabulary records and the operations health snapshot."""
        root = self.entities["./"]
        self.reference_keys.update(("license", "isBasedOn", "hasPart"))
        return {
            "@context": self.relative(META_FILE, CONTEXT_FILE),
            "@id": posixpath.basename(META_FILE),
            "@type": "Dataset",
            "name": language_map(root["name"]),
            "description": language_map(root["description"]),
            "version": root["version"],
            "datePublished": root["datePublished"],
            "license": self.iri(ids(root["license"])[0], META_FILE),
            "url": self.site_root(META_FILE),
            "isBasedOn": self.site_root(META_FILE) + kb.CRATE_FILE,
            "hasPart": [f"{collection}.json" for collection in kb.API_COLLECTIONS]
            + [f"vocabularies/{record}.json" for record, _ in self.records["vocabularies"]]
            + [posixpath.basename(HEALTH_FILE)],
        }

    def health(self, report: dict[str, Any] | None = None) -> dict[str, Any]:
        """Ordinary JSON check evidence, enriched with relative links to the API's existing records.

        A plain build has no completed check timestamp. Its inventory is evaluated against the
        maintained content's latest recorded date so rebuilding the same sources is deterministic.
        ``check_all`` replaces it with the actual run report after the checks finish.
        """
        dates = [str(self.content["guide"]["guide"]["datePublished"])[:10]] + [
            str(action["endTime"])[:10] for action in self.content["provenance"] if action.get("endTime")
        ]
        as_of = max(date.fromisoformat(value) for value in dates)
        result = (
            copy.deepcopy(report)
            if report is not None
            else check_health.make_report(self.content, today=as_of, graph=self.graph)
        )
        result["content_as_of"] = as_of.isoformat()
        if report is None:
            result["generated_at"] = None
        record_paths = {
            name: {record: self.paths[entity_id] for record, entity_id in members}
            for name, members in self.records.items()
        }

        def link(item: dict[str, Any], collections: tuple[str, ...], prefix: str = "") -> None:
            target = self.paths.get(self.base + prefix + item["id"]) if prefix else None
            if not target:
                target = next(
                    (record_paths[name][item["id"]] for name in collections if item["id"] in record_paths[name]), None
                )
            if target:
                item["api_record"] = self.relative(HEALTH_FILE, target)

        groups = {
            "cited sources": ("resources",),
            "ledger clauses": ("clauses",),
            "stations": ("stations",),
            "questions and source context": ("questions",),
            "self-checks": ("checks",),
            "curated repositories": ("repositories", "resources"),
            "snapshot repositories": ("repositories", "resources"),
            "snapshot resources": ("resources",),
            "snapshot organisations": ("organizations",),
            "guide organisations": ("organizations",),
            "snapshot profiles": ("fips",),
            "glossary terms": ("glossary",),
            "FAIR principles": ("principles",),
            "remote automated tests": ("tests",),
            "guide automated tests": ("tests",),
            "implementation model": ("models", "layers", "seams", "model-examples"),
            "model associations": tuple(kb.API_COLLECTIONS),
        }
        model = ((self.content.get("model") or {}).get("model") or {}).get("id", "")
        for group in result["integrity"]:
            collections = ("resources",) if group["type"].startswith("resources:") else groups.get(group["type"], ())
            for item in group["items"]:
                if group["type"] == "implementation model" and item["id"].startswith(("layer.", "seam.", "example.")):
                    kind, identifier = item["id"].split(".", 1)
                    target = self.paths.get(f"{self.base}{MODEL_KINDS[kind]}/{identifier}")
                    if target:
                        item["api_record"] = self.relative(HEALTH_FILE, target)
                    continue
                if group["type"] == "implementation model" and item["id"].startswith("context:"):
                    _, station, lens = item["id"].split(":")
                    target = self.paths.get(f"{self.base}stations/{station}#context-{lens}")
                    if target:
                        item["api_record"] = self.relative(HEALTH_FILE, target)
                    continue
                if group["type"] == "implementation model" and item["id"] == "model:worked-example":
                    item["api_record"] = self.relative(
                        HEALTH_FILE, self.paths[f"{self.base}models/{model}#worked-example"]
                    )
                    continue
                if group["type"] == "model associations" and item["id"].startswith("test:"):
                    test = item["id"][5:]
                    target = next(
                        (
                            self.paths[f"{self.base}tests/{scope}/{test}"]
                            for scope in ("guide", kb.CHAMPION_SCOPE)
                            if f"{self.base}tests/{scope}/{test}" in self.paths
                        ),
                        HEALTH_FILE,
                    )
                    item["api_record"] = self.relative(HEALTH_FILE, target)
                    continue
                if group["type"] == "model associations" and f"{self.base}advice/{item['id']}" in self.paths:
                    link(item, (), "advice/")
                    continue
                link(item, collections, "advice/" if group["type"] == "station advice" else "")
        coverage = result["original_coverage"]
        for kind, collections, prefix in (
            ("clauses", ("clauses",), ""),
            ("questions", ("questions",), ""),
            ("advice", (), "advice/"),
            ("by_source", ("resources",), ""),
        ):
            for item in coverage[kind]:
                link(item, collections, prefix)
        return result

    def context(self) -> dict[str, Any]:
        """The JSON-LD context: schema.org by default, the guide's own terms, FTR and its neighbours, language maps
        and links for every property the records use."""
        guide_terms = self.crate["@context"][1]
        both = self.language_keys & self.reference_keys
        if both:
            raise kb.ContentError(f"the API property {min(both)} holds both text and links")
        terms = dict(TERMS)
        for key in sorted(self.language_keys | self.reference_keys):
            if key in TERMS:
                continue
            definition = {"@id": guide_terms.get(key, SCHEMA_ORG + key)}
            definition |= {"@container": "@language"} if key in self.language_keys else {"@type": "@id"}
            terms[key] = definition
        for key, iri in guide_terms.items():
            terms.setdefault(key, iri)
        return {"@context": terms}

    # ------------------------------------------------------------------ the site

    def files(self) -> dict[str, str]:
        """Every file of the API, by its path in the site."""
        docs: dict[str, dict[str, Any]] = {}
        for collection, members in self.records.items():
            for record, entity_id in members:
                docs[self.paths[entity_id]] = self.record(collection, record, entity_id)
        for record, entity_id in self.records["questions"]:
            docs[self.tests[entity_id]] = self.saved_result_reference(record, entity_id)
        for collection in kb.API_COLLECTIONS:
            docs[f"api/v1/{collection}.json"] = self.collection(collection)
        docs[META_FILE] = self.index()
        docs[HEALTH_FILE] = self.health()
        docs[CONTEXT_FILE] = self.context()  # after the records: it names every property they use
        docs[OPENAPI_FILE] = self.openapi(docs)
        # The records themselves also supply a static bilingual landing page at their issued address.
        return {
            path: json.dumps(doc, ensure_ascii=False, indent=2) + "\n" for path, doc in docs.items()
        } | landing_pages(self, docs)

    def openapi(self, docs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """OpenAPI 3.1: one list plus unscoped and scoped templates per kind, never one operation per record."""
        english = {
            key: value[kb.LANGS[1]]
            for key, value in self.strings.items()
            if isinstance(value, dict) and kb.LANGS[1] in value
        }
        paths: dict[str, Any] = {
            "/" + META_FILE: operation("getIndex", english["index"], "Index", "operations"),
            "/" + CONTEXT_FILE: operation(
                "getContext", english["context"], "Context", "operations", media="application/ld+json"
            ),
            "/" + HEALTH_FILE: operation("getHealth", english["health"], "Health", "operations"),
        }
        paths["/" + HEALTH_FILE]["get"]["description"] = english["healthDescription"]
        tags = [{"name": "operations", "description": english["metaTag"]}]
        for collection in kb.API_COLLECTIONS:
            strings = self.strings["collection"].get(collection, {})
            strings = {key: value[kb.LANGS[1]] for key, value in strings.items()}
            schema = SCHEMAS[collection]
            tags.append({"name": collection, "description": strings.get("description", collection)})
            paths[f"/api/v1/{collection}.json"] = operation(
                f"list{schema}s", strings.get("name", collection), f"{schema}List", collection
            )
            members = self.records[collection]
            for scoped in (False, True):
                records = [record for record, _ in members if ("/" in record) == scoped]
                if not records:
                    continue
                suffix = "/{scope}" if scoped else ""
                parameters = []
                if scoped:
                    parameters.append(
                        {
                            "name": "scope",
                            "in": "path",
                            "required": True,
                            "description": "The scope that is part of the record's identity.",
                            "schema": {"type": "string", "enum": sorted({record.split("/")[0] for record in records})},
                            "example": records[0].split("/")[0],
                        }
                    )
                parameters.append(
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "description": strings.get("parameter", "The record's identifier within its kind and scope."),
                        "schema": {"type": "string", "pattern": kb.API_ID.pattern},
                        "example": "R1.1" if "R1.1" in records else records[0].split("/")[-1],
                    }
                )
                path = f"/api/v1/{collection}{suffix}/{{id}}.json"
                paths[path] = operation(
                    f"get{schema}{'Scoped' if scoped else ''}",
                    strings.get("record", collection),
                    schema,
                    collection,
                )
                paths[path]["get"]["parameters"] = parameters
        paths["/api/tests/{id}.json"] = operation(
            "getSavedResultQuestion",
            self.strings["test"]["name"]["en"].format(id="{id}"),
            "SavedResultReference",
            "operations",
        )
        paths["/api/tests/{id}.json"]["get"]["parameters"] = [
            {
                "name": "id",
                "in": "path",
                "required": True,
                "description": "The check question addressed by a saved result of revision 1 to 3.",
                "schema": {"type": "string", "pattern": kb.API_ID.pattern},
                "example": self.records["questions"][0][0],
            }
        ]
        return {
            "openapi": "3.1.0",
            "info": {
                "title": english["title"],
                "version": self.entities["./"]["version"],
                "description": english["description"],
                "license": {"name": "CC BY 4.0", "identifier": "CC-BY-4.0"},
            },
            "externalDocs": {"description": english["guide"], "url": "./"},
            "servers": [{"url": ".", "description": english["server"]}],
            "tags": tags,
            "paths": paths,
            "components": {"schemas": typed_schemas(self, docs) | health_schemas()},
        }


# The record kind of the implementation model's items, by the prefix their content IDs carry.
MODEL_KINDS = {"layer": "layers", "seam": "seams", "example": "model-examples"}
SCHEMA_NAMES = {
    "advice": "Advice",
    "checks": "Check",
    "clauses": "Clause",
    "fips": "Fip",
    "glossary": "Glossary",
    "lifecycles": "Lifecycle",
    "model-examples": "ModelExample",
    "models": "Model",
    "organizations": "Organization",
    "principles": "Principle",
    "questions": "Question",
    "repositories": "Repository",
    "resources": "Resource",
    "stations": "Station",
    "tests": "Test",
    "vocabularies": "Vocabulary",
}
SCHEMAS = {
    kind: SCHEMA_NAMES.get(kind, "".join(part.title() for part in kind.removesuffix("s").split("-")))
    for kind in kb.API_COLLECTIONS
}
KIND_REQUIRED = {
    "advice": ["text", "isPartOf", "audience", "disclosureLevel", "adviceKind"],
    "principles": ["name", "description", "termCode", "clauses", "advice", "stations", "questions"],
    "questions": ["text", "tier", "hasBenchmark", "citation"],
    "clauses": ["text", "isPartOf", "clauseKind"],
    "repositories": ["name", "repositoryKind"],
    "resources": ["name"],
    "tests": ["name"],
    "organizations": ["name"],
    "fips": ["name", "hasPart"],
    "actions": ["name"],
    "models": ["name"],
    "lifecycles": ["name"],
    # A name defines every infrastructure, including European records without the curated national-roadmap annex fields.
    "infrastructures": ["name"],
}


def operation(
    operation_id: str,
    summary: str,
    schema: str,
    tag: str,
    *,
    parameter: dict[str, Any] | None = None,
    media: str = "application/json",
) -> dict[str, Any]:
    return {
        "get": {
            "operationId": operation_id,
            "summary": summary,
            "tags": [tag],
            "parameters": [parameter] if parameter else [],
            "responses": {
                "200": {
                    "description": summary,
                    "content": {media: {"schema": {"$ref": f"#/components/schemas/{schema}"}}},
                },
                "404": {"description": "No such file"},
            },
        }
    }


def ref(name: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{name}"}


def combine_schemas(options: list[dict[str, Any]]) -> dict[str, Any]:
    # Cheap object-identity deduplication precedes structural serialization; all option objects stay alive in `options`.
    distinct = list({id(option): option for option in options}.values())
    unique = list({json.dumps(option, sort_keys=True): option for option in distinct}.values())
    if not unique:
        return {}
    if len(unique) == 1:
        return unique[0]
    if any(not option for option in unique):
        return {}
    return {"oneOf": unique}


def inferred_schema(api: Api, values: list[Any]) -> dict[str, Any]:
    """JSON types from the finite documents, keeping a vocabulary reference a distinct typed shape."""
    if not values:
        return {}
    objects = [value for value in values if isinstance(value, dict) and set(value) - {"@id", "termCode"}]
    object_properties = {
        key: inferred_schema(api, [item[key] for item in objects if key in item])
        for key in {key for item in objects for key in item}
    }
    object_shape = {"type": "object", "properties": object_properties} if objects else None
    options = (
        [
            {
                "type": "array",
                "items": inferred_schema(api, [item for value in values if isinstance(value, list) for item in value]),
            }
        ]
        if any(isinstance(value, list) for value in values)
        else []
    )
    for value in values:
        if isinstance(value, bool):
            options.append({"type": "boolean"})
        elif isinstance(value, int):
            options.append({"type": "integer"})
        elif isinstance(value, float):
            options.append({"type": "number"})
        elif isinstance(value, str):
            options.append({"type": "string"})
        elif isinstance(value, list):
            continue
        elif isinstance(value, dict):
            if set(value) <= set(kb.LANGS):
                options.append(ref("LocalizedText"))
            elif set(value) <= {"@id", "termCode"}:
                match = re.search(r"/vocabularies/([^/]+)[.]json#", value["@id"])
                codes = [value["termCode"]]
                if match:
                    codes = sorted(api.term_codes.get(match.group(1), set())) or codes
                options.append(
                    {
                        "type": "object",
                        "required": ["@id", "termCode"],
                        "properties": {"@id": {"type": "string"}, "termCode": {"enum": codes}},
                        "additionalProperties": False,
                        **({"x-term-set": match.group(1)} if match else {}),
                    }
                )
            else:
                options.append(object_shape)
        else:
            options.append({"type": "null"})
    return combine_schemas(options)


def typed_schemas(api: Api, docs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Response shapes share the graph's properties: only list identity/filter summaries are added."""
    out: dict[str, Any] = {
        "LocalizedText": {
            "type": "object",
            "minProperties": 1,
            "propertyNames": {"enum": list(kb.LANGS)},
            "additionalProperties": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
        },
        "Text": {"oneOf": [{"type": "string"}, ref("LocalizedText")]},
        "Types": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
        "Record": {
            "type": "object",
            "required": ["@context", "@id", "@type"],
            "properties": {"@context": {"type": "string"}, "@id": {"type": "string"}, "@type": ref("Types")},
        },
        "Summary": {
            "type": "object",
            "required": ["@id", "@type", "identifier", "address", "iri", "label"],
            "properties": {
                "@id": {"type": "string"},
                "@type": ref("Types"),
                "identifier": {"type": "string"},
                "address": {"type": "string"},
                "iri": {"type": "string"},
                "label": ref("Text"),
                "scope": {"type": "string"},
            },
        },
        "List": {
            "allOf": [ref("Record")],
            "required": ["name", "description", "filterFields", "numberOfItems", "itemListElement"],
            "properties": {
                "name": ref("LocalizedText"),
                "description": ref("LocalizedText"),
                "filterFields": {"type": "array", "items": {"type": "string"}},
                "numberOfItems": {"type": "integer", "minimum": 0},
                "itemListElement": {"type": "array", "items": ref("Summary")},
            },
        },
        "Context": {"type": "object", "required": ["@context"], "properties": {"@context": {"type": "object"}}},
        "SavedResultReference": {
            "allOf": [ref("Record")],
            "required": ["identifier", "name", "description", "about"],
            "properties": {
                "identifier": {"type": "string"},
                "name": ref("LocalizedText"),
                "description": ref("LocalizedText"),
                "about": {"type": "string"},
            },
        },
        "Index": {
            "allOf": [ref("Record")],
            "required": ["name", "description", "version", "url", "isBasedOn", "hasPart"],
            "properties": {"hasPart": {"type": "array", "items": {"type": "string"}}},
        },
    }
    for kind, schema in SCHEMAS.items():
        records = [docs[path] for path in (api.paths[entity_id] for _, entity_id in api.records[kind])]
        out[schema] = {
            "allOf": [ref("Record")],
            "required": ["identifier", *KIND_REQUIRED.get(kind, ["name"])],
            "properties": inferred_schema(api, records).get("properties", {}),
        }
        out[f"{schema}Summary"] = {
            "allOf": [ref("Summary")],
            "properties": {
                "scope": (
                    {"enum": sorted({record.split("/")[0] for record, _ in api.records[kind] if "/" in record})}
                    if any("/" in record for record, _ in api.records[kind])
                    else {"type": "string"}
                ),
                **inferred_schema(api, list(docs[f"api/v1/{kind}.json"]["itemListElement"])).get("properties", {}),
            },
        }
        out[f"{schema}List"] = copy.deepcopy(out["List"])
        out[f"{schema}List"]["properties"]["itemListElement"]["items"] = ref(f"{schema}Summary")
        fields = api.filter_fields(kind)
        out[f"{schema}List"]["properties"]["filterFields"]["items"] = (
            {"enum": sorted(fields)} if fields else {"type": "string"}
        )
    out["Model"]["anyOf"] = [{"required": ["source"]}, {"required": ["citation"]}]
    out["Repository"]["description"] = (
        "A repository requires an HTTPS address, except while planned or in development with an NKR record in "
        "sameAs, when it has no public address yet. Its status refers to the service-status term set."
    )
    out["Repository"]["properties"].update(
        {
            "url": {"type": "string", "pattern": "^https://"},
            "acceptsDeposits": {
                "type": "boolean",
                "enum": [False],
                "description": "False or absent; absence means unknown, never acceptance.",
            },
        }
    )
    out["Repository"]["if"] = {
        "not": {
            "required": ["serviceStatus", "sameAs"],
            "properties": {
                "serviceStatus": {
                    "type": "object",
                    "required": ["termCode"],
                    "properties": {"termCode": {"enum": ["planned", "in-development"]}},
                },
                "sameAs": {
                    "type": "array",
                    "contains": {"type": "string", "pattern": r"^https://repo[.]cz/objects/.+"},
                },
            },
        },
    }
    out["Repository"]["then"] = {"required": ["url"]}
    return out


def health_schemas() -> dict[str, Any]:
    """Typed ordinary-JSON evidence; outcome states are separate from recorded service statuses."""
    strings = {"type": "array", "items": {"type": "string"}}
    count = {"type": "integer", "minimum": 0}
    nullable_string = {"type": ["string", "null"]}
    record_link = {
        "type": "string",
        "minLength": 1,
        "description": "An API record path relative to api/v1/health.json.",
    }
    counts = {
        "type": "object",
        "required": ["total", "with_original"],
        "properties": {"total": count, "with_original": count},
        "additionalProperties": count,
    }
    return {
        "Health": {
            "type": "object",
            "description": (
                "A published offline check snapshot; recorded results describe content and checks, "
                "rather than runtime service liveness or a FAIR verdict."
            ),
            "required": [
                "format_version",
                "generated_at",
                "scope",
                "live_availability",
                "integrity",
                "integrity_failed",
                "original_coverage",
                "run",
                "trend",
            ],
            "not": {"required": ["@context"]},
            "properties": {
                "format_version": {"type": "integer", "const": check_health.FORMAT_VERSION},
                "generated_at": {
                    "type": ["string", "null"],
                    "description": "Actual report time; null for an unexecuted build inventory.",
                },
                "content_as_of": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                "scope": {"type": "string"},
                "revision": nullable_string,
                "run_url": nullable_string,
                "missing_links": {
                    "type": "array",
                    "description": "Advisory exact-name matches in authored prose; never integrity failures.",
                    "items": {
                        "type": "object",
                        "required": ["path", "language", "text", "entry", "entry_name", "address"],
                        "additionalProperties": {"type": "string"},
                    },
                },
                "live_availability": {
                    "type": "object",
                    "required": ["status", "reason"],
                    "properties": {"status": {"const": "unchecked"}, "reason": {"type": "string"}},
                },
                "integrity": {"type": "array", "items": ref("HealthGroup")},
                "integrity_failed": count,
                "original_coverage": ref("HealthCoverage"),
                "run": ref("HealthRun"),
                "trend": {
                    "type": "object",
                    "required": ["available"],
                    "properties": {
                        "available": {"type": "boolean"},
                        "reason": {"type": "string"},
                        "previous_generated_at": nullable_string,
                        "coverage": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "required": [
                                    "new_missing",
                                    "resolved_missing",
                                    "added_items",
                                    "removed_items",
                                    "with_original_delta",
                                ],
                                "properties": {
                                    "new_missing": strings,
                                    "resolved_missing": strings,
                                    "added_items": strings,
                                    "removed_items": strings,
                                    "with_original_delta": {"type": "integer"},
                                },
                            },
                        },
                        "job_changes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["name", "previous", "current"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "previous": {"type": "string"},
                                    "current": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        },
        "HealthRun": {
            "type": "object",
            "required": ["status", "jobs"],
            "properties": {
                "status": {"enum": ["not_run", "passed", "partial", "failed"]},
                "reason": {"type": "string"},
                "jobs": {"type": "array", "items": ref("HealthJob")},
            },
        },
        "HealthJob": {
            "type": "object",
            "required": ["name", "status"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "status": {"enum": ["passed", "failed", "blocked", "not_run"]},
                "seconds": {"type": ["number", "null"], "minimum": 0},
                "output": {"type": "string"},
                "partial": {"type": "boolean"},
                "scripts": {"type": "array", "items": ref("HealthScript")},
            },
        },
        "HealthScript": {
            "type": "object",
            "required": ["name", "status", "seconds", "planned", "executed", "skipped", "pending"],
            "properties": {
                "name": {"type": "string"},
                "status": {"enum": ["passed", "failed", "partial"]},
                "seconds": {"type": "number", "minimum": 0},
                "planned": count,
                "executed": {"type": "array", "items": ref("HealthCase")},
                "skipped": {"type": "array", "items": {"type": "string"}},
                "pending": {"type": "array", "items": {"type": "string"}},
            },
        },
        "HealthCase": {
            "type": "object",
            "required": ["name", "status"],
            "properties": {
                "name": {"type": "string"},
                "status": {"enum": ["passed", "failed"]},
                "seconds": {"type": "number", "minimum": 0},
                "aborted": {"type": "boolean"},
            },
        },
        "HealthGroup": {
            "type": "object",
            "required": ["type", "count", "passed", "failed", "items"],
            "properties": {
                "type": {"type": "string"},
                "scope": {"type": "string"},
                "live_availability": {"enum": ["unchecked", "not_applicable"]},
                "count": count,
                "passed": count,
                "failed": count,
                "items": {"type": "array", "items": ref("HealthItem")},
            },
        },
        "HealthItem": {
            "type": "object",
            "required": ["id", "name", "status", "checks", "issues", "notes"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "status": {"enum": ["passed", "failed"]},
                "checks": strings,
                "issues": strings,
                "notes": strings,
                "recorded_status": nullable_string,
                "recorded_date": nullable_string,
                "api_record": record_link,
            },
        },
        "HealthCoverage": {
            "type": "object",
            "required": ["counts", "clauses", "questions", "advice", "by_source"],
            "properties": {
                "counts": {
                    "type": "object",
                    "properties": {kind: counts for kind in ("clauses", "questions", "advice")},
                },
                "clauses": {"type": "array", "items": ref("HealthClause")},
                "questions": {"type": "array", "items": ref("HealthCitedItem")},
                "advice": {"type": "array", "items": ref("HealthCitedItem")},
                "by_source": {"type": "array", "items": ref("HealthSourceCoverage")},
            },
        },
        "HealthClause": {
            "type": "object",
            "required": ["id", "source", "has_original"],
            "properties": {
                "id": {"type": "string"},
                "source": {"type": "string"},
                "source_url": {"type": "string"},
                "source_title": {"type": "string"},
                "source_type": {"type": "string"},
                "source_version": nullable_string,
                "locator": {"type": "string"},
                "guide_text": ref("LocalizedText"),
                "kind": {"type": "string"},
                "actor": {"type": "string"},
                "status": {"type": "string"},
                "has_original": {"type": "boolean"},
                "original_language": nullable_string,
                "api_record": record_link,
            },
        },
        "HealthCitedItem": {
            "type": "object",
            "required": ["id", "parent", "citations", "originals", "missing_originals", "status"],
            "properties": {
                "id": {"type": "string"},
                "parent": {"type": "string"},
                "guide_text": ref("LocalizedText"),
                "kind": {"type": "string"},
                "lens": nullable_string,
                "level": nullable_string,
                "citations": strings,
                "originals": strings,
                "missing_originals": strings,
                "missing_sources": strings,
                "status": {"enum": ["complete", "partial", "no_original", "reviewed_source_links"]},
                "reviewed_basis": nullable_string,
                "api_record": record_link,
            },
        },
        "HealthSourceCoverage": {
            "type": "object",
            "required": ["id", "clauses", "with_original", "missing_clauses"],
            "properties": {
                "id": {"type": "string"},
                "title": {"type": "string"},
                "url": {"type": "string"},
                "type": {"type": "string"},
                "clauses": count,
                "with_original": count,
                "missing_clauses": strings,
                "questions_without_original": strings,
                "questions_with_other_original": strings,
                "advice_without_original": strings,
                "advice_with_other_original": strings,
                "api_record": record_link,
            },
        },
    }


def publish_health(
    out: Path, report: dict[str, Any], content: dict[str, Any] | None, crate: dict[str, Any] | None = None
) -> None:
    """Replace only the health snapshot of an already built site; callers require a successful fresh build."""
    target = out / HEALTH_FILE
    if not target.is_file() or not (out / OPENAPI_FILE).is_file():
        raise kb.ContentError("health publication requires an existing built API")
    out = kb.require_site(out)
    document = Api(crate or kb.build_crate(content), content).health(report) if content is not None else report
    (out / HEALTH_FILE).write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    check_health.write_site_dashboard(document, out)


def write_site(out: Path, files: dict[str, str]) -> None:
    """Replace the API in a site directory the build made: the generated files, the documentation page and Swagger UI.

    Refuses any other directory before removing anything, so the authored ``api/`` is never the target.
    """
    out = kb.require_site(out)
    api = out / "api"
    if api.exists():
        shutil.rmtree(api)
    for path, text in files.items():
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    for source in sorted(DOCS_DIR.iterdir()):
        if source.is_file():
            shutil.copyfile(source, api / source.name)
    swagger = api / "swagger-ui"
    swagger.mkdir()
    for name in SWAGGER_FILES:
        shutil.copyfile(SWAGGER_DIR / name, swagger / name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=SITE, help="the site directory (default: _site)")
    args = parser.parse_args(argv)
    try:
        kb.site_directory(args.out)
    except kb.UnsafeOutputError as error:
        print(f"build_api: {error}", file=sys.stderr)
        return 2
    if not (SWAGGER_DIR / SWAGGER_FILES[0]).exists():
        print("build_api: the Swagger UI package is missing; run npm ci", file=sys.stderr)
        return 2
    try:
        content = kb.load_content()
        files = Api(kb.build_crate(content), content).files()
        out = kb.claim_site(args.out)
    except (kb.ContentError, KeyError) as error:
        print(f"build_api: {error}", file=sys.stderr)
        return 2
    write_site(out, files)
    print(f"wrote {len(files)} API files and the API documentation into {args.out.name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
