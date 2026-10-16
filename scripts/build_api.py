#!/usr/bin/env python3
"""Generate the FAIR guide's static read-only API from its knowledge base.

The API is a view over the crate that ``build_crate.py`` builds; ``build_crate.api_records`` decides what it
publishes. It is written into the site directory, which is not committed (``_site/`` by default):

- ``api/<collection>.json`` and ``api/<kind>/<type>/<id>.json``: lists and canonical records, with language maps
  (``{"cs": …, "en": …}``) and the JSON-LD context ``api/context.jsonld``. Records link each other by relative
  paths, carry small terms (tiers, lenses, levels) in full, and name the entity's identifier in the crate or outside
  the guide in ``sameAs``;
- ``api/meta.json``: what the API is built from;
- the FTR definitions of the checks: each check is a benchmark (``api/check/``) and each question a metric
  (``api/q/``) with a manual test (``api/tests/``), which an exported result names as the test it comes from;
- ``openapi.json``: the OpenAPI 3.1 description, with a server address relative to it;
- ``api/index.html``: the interactive documentation, the authored files in ``api/`` with the pinned Swagger UI
  package that ``npm ci`` installs.

Paths follow the FIP Dashboard API's names where both describe the same thing (``/api/principles``,
``/api/resources``, ``/api/organizations``, ``/api/fips``, ``/api/meta``); a static site adds ``.json``.

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

SITE = kb.ROOT / "_site"
OPENAPI_FILE = kb.API_FILES["description"]
CONTEXT_FILE = kb.API_FILES["context"]
META_FILE = kb.API_FILES["meta"]
HEALTH_FILE = kb.API_FILES["health"]
DOCS_DIR = kb.ROOT / "api"
SWAGGER_DIR = kb.ROOT / "node_modules" / "swagger-ui-dist"
SWAGGER_FILES = ("swagger-ui-bundle.js", "swagger-ui.css", "LICENSE", "NOTICE")
SCHEMA_ORG = "http://schema.org/"
DQV = "http://www.w3.org/ns/dqv#"
DCAT = "http://www.w3.org/ns/dcat#"
SIO = "https://semanticscience.org/resource/"

# Entities small enough to repeat in full inside the records that name them.
EMBEDDED_TYPES = {"DefinedTerm", "Audience", "Action", "EntryPoint", "Person", "Organization", "PropertyValue"}
# What a record adds to its crate entity or names differently, per collection.
FTR_TYPES = {"checks": "Benchmark", "metrics": "Metric", "tests": "Test"}
RENAMED = {
    "checks": {"hasPart": "hasAssociatedMetric"},
    "metrics": {"about": "inDimension", "isPartOf": "hasBenchmark"},
}
DROPPED = {"metrics": {"additionalProperty", "name"}}  # the page's pre-fill settings; a name repeating the identifier
TERMS: dict[str, Any] = {
    "@vocab": SCHEMA_ORG,
    "ftr": kb.FTR,
    "dqv": DQV,
    "dcat": DCAT,
    "sio": SIO,
    "prov": kb.PROV,
    "Benchmark": "ftr:Benchmark",
    "Metric": "ftr:Metric",
    "Test": "ftr:Test",
    "hasAssociatedMetric": {"@id": "ftr:hasAssociatedMetric", "@type": "@id"},
    "hasBenchmark": {"@id": "ftr:hasBenchmark", "@type": "@id"},
    "inDimension": {"@id": "dqv:inDimension", "@type": "@id"},
    "isImplementationOf": {"@id": "sio:SIO_000233", "@type": "@id"},
    "hasImplementation": {"@id": "sio:SIO_000234", "@type": "@id"},
    "landingPage": {"@id": "dcat:landingPage", "@type": "@id"},
    # A principle's record lists what is about it, which the crate states from the other side.
    "clauses": {"@reverse": SCHEMA_ORG + "about", "@type": "@id"},
    "advice": {"@reverse": SCHEMA_ORG + "about"},
    "stations": {"@reverse": SCHEMA_ORG + "about", "@type": "@id"},
    "metrics": {"@reverse": DQV + "inDimension", "@type": "@id"},
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

    def __init__(self, crate: dict[str, Any], content: dict[str, Any]) -> None:
        self.crate = crate
        self.content = content
        self.strings = content["ui"]["api"]
        self.entities = {entity["@id"]: entity for entity in crate["@graph"]}
        self.records = kb.api_records(self.entities, content)
        self.paths = {
            entity_id: kb.API_FILES["record"].format(record=self.entities[entity_id]["catalogueAddress"])
            for name, members in self.records.items()
            for record, entity_id in members
        }
        # Each check question's manual test; the automated tests keep their own records beside them.
        self.tests = {
            entity_id: kb.API_FILES["test"].format(id=record) for record, entity_id in self.records["metrics"]
        }
        clash = {record for record, _ in self.records["tests"]} & {record for record, _ in self.records["metrics"]}
        if clash:
            raise kb.ContentError(f"a check question and an automated test share the API record tests/{min(clash)}")
        # Parts without a record of their own (advice and its steps, callouts, FIP declarations) live in the record
        # of what they are part of, under their own fragment.
        placed = True
        while placed:
            placed = False
            for entity_id, entity in self.entities.items():
                if entity_id in self.paths or not entity_id.startswith("#"):
                    continue
                whole = next((whole for whole in ids(entity.get("isPartOf")) if whole in self.paths), None)
                if whole:
                    self.paths[entity_id] = self.paths[whole].split("#")[0] + entity_id
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

    def node(self, entity: dict[str, Any], here: str, depth: int, collection: str = "") -> dict[str, Any]:
        entity_id = entity["@id"]
        path = self.paths.get(entity_id)
        own = self.relative(here, path) if path else self.iri(entity_id, here)
        renamed = RENAMED.get(collection, {})
        node: dict[str, Any] = {"@id": own, "@type": entity["@type"]}
        for key, value in entity.items():
            if key in ("@id", "@type") or key in DROPPED.get(collection, ()):
                continue
            name = renamed.get(key, key)
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
        node = self.node(entity, here, 0, collection)
        types = kb.as_list(node["@type"]) + ([FTR_TYPES[collection]] if collection in FTR_TYPES else [])
        same = [self.iri(entity_id, here)] + [
            link for link in kb.as_list(node.get("sameAs")) if link != self.iri(entity_id, here)
        ]
        out = {"@context": self.relative(here, CONTEXT_FILE)} | node | {"@type": types, "sameAs": same}
        if collection == "principles":
            out |= self.about_principle(entity_id, here)
        if collection == "metrics":
            local = [
                test_id
                for _, test_id in self.records["tests"]
                if entity_id in ids(self.entities[test_id].get("isImplementationOf"))
            ]
            implementations = [self.relative(here, self.tests[entity_id])] + [
                self.relative(here, self.paths[test_id]) for test_id in local
            ]
            out["hasImplementation"] = implementations if local else implementations[0]
        return out

    def about_principle(self, principle: str, here: str) -> dict[str, Any]:
        """What the crate says is about a principle: its requirements and findings, the advice that cites them (each
        with its lens), the stations that address it and the check questions that test it."""

        def members(collection: str) -> list[str]:
            return [entity_id for _, entity_id in self.records[collection]]

        def about(entity_id: str) -> bool:
            return principle in ids(self.entities[entity_id].get("about"))

        clauses = [entity_id for entity_id in members("clauses") if about(entity_id)]
        cited = set(clauses)
        advice = [
            entity_id
            for entity_id, entity in self.entities.items()
            if entity_id.startswith("#advice-") and cited & set(ids(entity.get("citation")))
        ]
        return {
            "clauses": [self.relative(here, self.paths[entity_id]) for entity_id in clauses],
            "advice": [self.node(self.entities[entity_id], here, 0) for entity_id in advice],
            "stations": [
                self.relative(here, self.paths[entity_id]) for entity_id in members("stations") if about(entity_id)
            ],
            "metrics": [
                self.relative(here, self.paths[entity_id]) for entity_id in members("metrics") if about(entity_id)
            ],
        }

    def manual_test(self, record: str, entity_id: str) -> dict[str, Any]:
        """The FTR test of a check question: a person answers it in the guide's self-check."""
        here = self.tests[entity_id]
        check = self.entities[ids(self.entities[entity_id].get("isPartOf"))[0]]
        lens = ids(check.get("audience"))[0].removeprefix("#lens-")
        strings = self.strings["test"]
        context = self.entities[entity_id].get("assessmentContext", False)
        self.language_keys.update(("name", "description"))
        return {
            "@context": self.relative(here, CONTEXT_FILE),
            "@id": posixpath.basename(here),
            "@type": ["Test"],
            "identifier": record,
            "name": {language: text.format(id=record) for language, text in strings["name"].items()},
            "description": strings["contextDescription"] if context else strings["description"],
            **({"assessmentContext": True} if context else {}),
            "isImplementationOf": self.relative(here, self.paths[entity_id]),
            "landingPage": f"{self.site_root(here)}#/{kb.LANGS[0]}/{lens}/check/{check['identifier']}",
        }

    def collection(self, collection: str, records: dict[str, dict[str, Any]]) -> dict[str, Any]:
        here = f"api/{collection}.json"
        paths = [self.paths[entity_id] for _, entity_id in self.records[collection]]
        if collection == "tests":
            paths += list(self.tests.values())
        summaries = []
        for path in paths:
            record = records[path]
            summary = {"@id": self.relative(here, path), "@type": record["@type"], "identifier": Path(path).stem}
            label = "name" if "name" in record else "text"
            summaries.append(summary | ({label: record[label]} if label in record else {}))
        self.language_keys.update(("name", "description"))
        return {
            "@context": self.relative(here, CONTEXT_FILE),
            "@id": posixpath.basename(here),
            "@type": "ItemList",
            "name": self.strings["collection"][collection]["name"],
            "description": self.strings["collection"][collection]["description"],
            "numberOfItems": len(summaries),
            "itemListElement": summaries,
        }

    def meta(self) -> dict[str, Any]:
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
            "hasPart": [f"{collection}.json" for collection in kb.API_COLLECTIONS] + [posixpath.basename(HEALTH_FILE)],
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
        result = copy.deepcopy(report) if report is not None else check_health.make_report(self.content, today=as_of)
        result["content_as_of"] = as_of.isoformat()
        if report is None:
            result["generated_at"] = None
        record_paths = {
            name: {record: self.paths[entity_id] for record, entity_id in members}
            for name, members in self.records.items()
        }

        def link(item: dict[str, Any], collections: tuple[str, ...], prefix: str = "") -> None:
            target = self.paths.get(prefix + item["id"]) if prefix else None
            if not target:
                target = next(
                    (record_paths[name][item["id"]] for name in collections if item["id"] in record_paths[name]), None
                )
            if target:
                item["api_record"] = self.relative(HEALTH_FILE, target)

        groups = {
            "cited sources": ("sources", "resources"),
            "ledger clauses": ("clauses",),
            "stations": ("stations",),
            "questions and source context": ("metrics",),
            "self-checks": ("checks",),
            "curated repositories": ("repositories", "resources"),
            "snapshot repositories": ("repositories", "resources"),
            "snapshot resources": ("resources",),
            "snapshot organisations": ("organizations",),
            "guide organisations": ("organizations",),
            "snapshot profiles": ("fips",),
            "glossary terms": ("terms",),
            "FAIR principles": ("principles",),
            "remote automated tests": ("tests",),
            "guide automated tests": ("tests",),
            "implementation model": ("model",),
            "model associations": tuple(kb.API_COLLECTIONS),
        }
        for group in result["integrity"]:
            collections = ("resources",) if group["type"].startswith("resources:") else groups.get(group["type"], ())
            for item in group["items"]:
                if group["type"] == "implementation model" and item["id"].startswith(("layer.", "seam.", "example.")):
                    kind, identifier = item["id"].split(".", 1)
                    prefix = "#model-example-" if kind == "example" else "#" + kind + "-"
                    target = self.paths.get(prefix + identifier)
                    if target:
                        item["api_record"] = self.relative(HEALTH_FILE, target)
                    continue
                if group["type"] == "implementation model" and item["id"].startswith("context:"):
                    context_id = "#model-context-" + item["id"].removeprefix("context:").replace(":", "-")
                    if self.paths.get(context_id):
                        item["api_record"] = self.relative(HEALTH_FILE, self.paths[context_id])
                    continue
                if group["type"] == "implementation model" and item["id"] == "model:worked-example":
                    item["api_record"] = self.relative(HEALTH_FILE, self.paths["#model-worked-example"])
                    continue
                if group["type"] == "model associations" and item["id"].startswith("test:"):
                    item["api_record"] = self.relative(
                        HEALTH_FILE, self.paths.get("#test-" + item["id"][5:], HEALTH_FILE)
                    )
                    continue
                if group["type"] == "model associations" and "#advice-" + item["id"] in self.paths:
                    link(item, (), "#advice-")
                    continue
                link(item, collections, "#advice-" if group["type"] == "station advice" else "")
        coverage = result["original_coverage"]
        for kind, collections, prefix in (
            ("clauses", ("clauses",), ""),
            ("questions", ("metrics",), ""),
            ("advice", (), "#advice-"),
            ("by_source", ("sources", "resources"), ""),
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
        for record, entity_id in self.records["metrics"]:
            docs[self.tests[entity_id]] = self.manual_test(record, entity_id)
        for collection in kb.API_COLLECTIONS:
            docs[f"api/{collection}.json"] = self.collection(collection, docs)
        docs[META_FILE] = self.meta()
        docs[HEALTH_FILE] = self.health()
        docs[CONTEXT_FILE] = self.context()  # after the records: it names every property they use
        docs[OPENAPI_FILE] = self.openapi(docs)
        return {path: json.dumps(doc, ensure_ascii=False, indent=2) + "\n" for path, doc in docs.items()}

    def openapi(self, docs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """The OpenAPI 3.1 description: one path per list and per record, each record's IDs as the parameter's
        values, and schemas that every file is validated against."""
        english = {
            key: value[kb.LANGS[1]]
            for key, value in self.strings.items()
            if isinstance(value, dict) and kb.LANGS[1] in value
        }
        paths: dict[str, Any] = {
            "/" + META_FILE: operation("getMeta", english["meta"], "Meta", "meta"),
            "/" + CONTEXT_FILE: operation(
                "getContext", english["context"], "Context", "meta", media="application/ld+json"
            ),
            "/" + HEALTH_FILE: operation("getHealth", english["health"], "Health", "meta"),
        }
        paths["/" + HEALTH_FILE]["get"]["description"] = english["healthDescription"]
        tags = [{"name": "meta", "description": english["metaTag"]}]
        for collection in kb.API_COLLECTIONS:
            strings = {key: value[kb.LANGS[1]] for key, value in self.strings["collection"][collection].items()}
            schema = SCHEMAS[collection]
            tags.append({"name": collection, "description": strings["description"]})
            paths[f"/api/{collection}.json"] = operation(f"list{schema}s", strings["name"], "List", collection)
            records = [
                Path(path).stem for path in docs if str(Path(path).parent).replace("\\", "/") == f"api/{collection}"
            ]
            if not records:
                continue  # An empty list is published as it is; there is no record path without a record to name.
            parameter = {
                "name": PARAMETERS[collection],
                "in": "path",
                "required": True,
                "description": strings["parameter"],
                "schema": {"type": "string", "enum": records},
                "example": "R1.1" if "R1.1" in records else records[0],
            }
            paths[f"/api/{collection}/{{{PARAMETERS[collection]}}}.json"] = operation(
                f"get{schema}", strings["record"], schema, collection, parameter=parameter
            )
        # The canonical addresses may have a subtype and share a family across API collection vocabularies.
        # Describe concrete paths so their schema always remains that of the record, including cited sources.
        for collection, members in self.records.items():
            for _, entity_id in members:
                path = self.paths[entity_id]
                if path != kb.API_FILES["record"].format(record=f"{collection}/{Path(path).stem}"):
                    paths["/" + path] = operation(
                        "catalogue" + re.sub(r"[^A-Za-z0-9]", "_", path),
                        "Catalogue record",
                        SCHEMAS[collection],
                        collection,
                    )
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
            "components": {"schemas": schemas(self.language_keys, self.reference_keys) | health_schemas()},
        }


# The path parameter of each collection, named like the FIP Dashboard's (`resource_id`, `fip_id`), and its schema.
PARAMETERS = {
    "principles": "principle_id",
    "stations": "station_id",
    "checks": "check_id",
    "metrics": "metric_id",
    "tests": "test_id",
    "resources": "resource_id",
    "sources": "source_id",
    "repositories": "repository_id",
    "clauses": "clause_id",
    "terms": "term_id",
    "organizations": "organization_id",
    "fips": "fip_id",
    "changes": "change_id",
    "model": "model_id",
    "lifecycle": "lifecycle_id",
    "infrastructures": "infrastructure_id",
}
SCHEMAS = {
    "principles": "Principle",
    "stations": "Station",
    "checks": "Check",
    "metrics": "Metric",
    "tests": "Test",
    "resources": "Resource",
    "sources": "Source",
    "repositories": "Repository",
    "clauses": "Clause",
    "terms": "Term",
    "organizations": "Organization",
    "fips": "Fip",
    "changes": "Change",
    "model": "Model",
    "lifecycle": "Lifecycle",
    "infrastructures": "Infrastructure",
}
# What every record of a collection carries; a record may carry more.
REQUIRED = {
    "Principle": ["termCode", "name", "description", "clauses", "advice", "stations", "metrics"],
    "Station": ["identifier", "name", "headline", "position", "about", "itemListElement"],
    "Check": ["identifier", "name", "description", "hasAssociatedMetric"],
    "Metric": ["identifier", "text", "tier", "hasBenchmark", "hasImplementation", "citation"],
    "Test": ["identifier", "name"],
    "Resource": ["identifier", "name"],
    "Source": ["identifier", "name"],
    "Repository": ["name", "url"],
    "Clause": ["identifier", "text", "isPartOf"],
    "Term": ["name"],
    "Organization": ["name"],
    "Fip": ["identifier", "name", "hasPart"],
    "Change": ["name"],
    "Model": ["identifier", "name", "citation"],
    "Lifecycle": ["identifier", "name"],
    "Infrastructure": ["identifier", "name", "abbreviation", "publisher", "roadmapLocator"],
    "Meta": ["name", "description", "version", "url", "isBasedOn", "hasPart"],
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


def schemas(language_keys: set[str], reference_keys: set[str]) -> dict[str, Any]:
    """The schemas of the records, a list and the context; `Text` and `Links` cover what every record may hold."""

    def property_schema(key: str) -> dict[str, Any]:
        if key == "championEvidenceOnly":
            return {"type": "boolean"}
        if key == "prefillLevel":
            return {"type": "string", "enum": ["partly"]}
        if key in language_keys:
            return ref("Text")
        if key in reference_keys or key in TERMS:
            return ref("Links")
        return {"type": "integer"} if key == "position" else {}

    out: dict[str, Any] = {
        "LocalizedText": {
            "description": "A language map: the text in Czech and English, a list where there are several.",
            "type": "object",
            "minProperties": 1,
            "propertyNames": {"enum": list(kb.LANGS)},
            "additionalProperties": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
        },
        "Text": {"oneOf": [{"type": "string"}, ref("LocalizedText")]},
        "Link": {
            "description": "A path to another record relative to this one, an identifier, or a small entity in full.",
            "oneOf": [
                {"type": "string"},
                {"type": "object", "required": ["@id"], "properties": {"@id": {"type": "string"}}},
            ],
        },
        "Links": {"oneOf": [ref("Link"), {"type": "array", "items": ref("Link")}]},
        "Types": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
        "Record": {
            "type": "object",
            "required": ["@context", "@id", "@type"],
            "properties": {
                "@context": {"type": "string"},
                "@id": {"type": "string"},
                "@type": ref("Types"),
                "sameAs": {"type": "array", "items": {"type": "string"}},
            },
        },
        "Summary": {
            "type": "object",
            "required": ["@id", "@type", "identifier"],
            "properties": {
                "@id": {"type": "string"},
                "@type": ref("Types"),
                "identifier": {"type": "string"},
                "name": ref("Text"),
                "text": ref("Text"),
            },
        },
        "List": {
            "allOf": [ref("Record")],
            "required": ["name", "description", "numberOfItems", "itemListElement"],
            "properties": {
                "name": ref("LocalizedText"),
                "description": ref("LocalizedText"),
                "numberOfItems": {"type": "integer"},
                "itemListElement": {"type": "array", "items": ref("Summary")},
            },
        },
        "Context": {"type": "object", "required": ["@context"], "properties": {"@context": {"type": "object"}}},
    }
    for schema, required in REQUIRED.items():
        out[schema] = {
            "allOf": [ref("Record")],
            "required": required,
            "properties": {key: property_schema(key) for key in required},
        }
    return out


def health_schemas() -> dict[str, Any]:
    """Typed ordinary-JSON evidence; outcome states are separate from recorded service statuses."""
    strings = {"type": "array", "items": {"type": "string"}}
    count = {"type": "integer", "minimum": 0}
    nullable_string = {"type": ["string", "null"]}
    record_link = {"type": "string", "minLength": 1, "description": "An API record path relative to api/health.json."}
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


def publish_health(out: Path, report: dict[str, Any], content: dict[str, Any] | None) -> None:
    """Replace only the health snapshot of an already built site; callers require a successful fresh build."""
    target = out / HEALTH_FILE
    if not target.is_file() or not (out / OPENAPI_FILE).is_file():
        raise kb.ContentError("health publication requires an existing built API")
    out = kb.require_site(out)
    document = Api(kb.build_crate(content), content).health(report) if content is not None else report
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
