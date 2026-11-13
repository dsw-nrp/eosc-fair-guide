#!/usr/bin/env python3
"""Write the Guide's crate as N-Triples using only the standard library.

The context is the pinned local copy of the RO-Crate 1.2 terms used by the Guide. No remote resolver or RDF build
library is needed. The tests' rdflib parser reads the same context and acts as the independent interoperability
check; the build never performs a network request.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
CONTEXT_FILE = ROOT / "tests" / "fixtures" / "ro-crate-1.2-context.json"
NT_FILE = "knowledge-graph.nt"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XSD = "http://www.w3.org/2001/XMLSchema#"


def context(crate: dict[str, Any], context_file: Path = CONTEXT_FILE) -> dict[str, Any]:
    """The offline RO-Crate mappings, then the crate's own mappings, which take precedence."""
    local = json.loads(context_file.read_text(encoding="utf-8"))["@context"]
    return local | next((values for values in crate["@context"] if isinstance(values, dict)), {})


def iri_escape(value: str) -> str:
    """Escape everything N-Triples forbids in an absolute IRI, including all non-ASCII characters."""
    return "".join(
        char
        if 32 < ord(char) < 127 and char not in '<>"{}|^`\\'
        else f"\\u{ord(char):04X}"
        if ord(char) <= 0xFFFF
        else f"\\U{ord(char):08X}"
        for char in value
    )


def literal_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    )


def safe_iri(value: str) -> bool:
    """An IRI that can be an RDF resource, not a blank-node label."""
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value))


def n_triples(crate: dict[str, Any], base: str, *, context_file: Path = CONTEXT_FILE) -> str:
    """Return the graph's deterministic N-Triples; *base* is the crate's absolute publication address."""
    terms = context(crate, context_file)
    triples: list[str] = []
    blank = 0

    def absolute(value: str) -> str:
        return value if safe_iri(value) else urljoin(base, value)

    def expand(value: str) -> str:
        definition = terms.get(value)
        if isinstance(definition, dict):
            if definition.get("@id") is None:
                raise ValueError(f"a JSON-LD keyword cannot be used as a graph property: {value}")
            value = definition["@id"]
        elif isinstance(definition, str):
            value = definition
        prefix, separator, suffix = value.partition(":")
        if separator and prefix in terms:
            mapped = terms[prefix]
            if isinstance(mapped, dict):
                mapped = mapped.get("@id")
            if isinstance(mapped, str):
                return mapped + suffix
        if safe_iri(value):
            return value
        raise ValueError(f"no IRI for the JSON-LD term {value!r}")

    def resource(value: str) -> str:
        return f"<{iri_escape(absolute(value))}>"

    def fresh() -> str:
        nonlocal blank
        blank += 1
        return f"_:b{blank}"

    def datatype(value: str) -> str:
        return XSD + {"integer": "integer", "decimal": "decimal", "double": "double"}.get(value, value)

    def scalar(value: Any) -> str:
        if isinstance(value, bool):
            return f'"{"true" if value else "false"}"^^<{XSD}boolean>'
        if isinstance(value, int):
            return f'"{value}"^^<{XSD}integer>'
        if isinstance(value, float):
            return f'"{json.dumps(value)}"^^<{XSD}double>'
        if isinstance(value, Decimal):
            return f'"{value}"^^<{XSD}decimal>'
        if value is None:
            return '""'
        return f'"{literal_escape(str(value))}"'

    def emit(node: Any, identifier: str | None = None) -> str:
        if isinstance(node, list):
            # RDF collection: preserve the explicit JSON-LD list, stopping at rdf:nil where empty.
            items = node
            if not items:
                return resource(RDF + "nil")
            head = previous = None
            for item in items:
                cell = fresh()
                if previous is not None:
                    triples.append(f"{previous} <{RDF}rest> {cell} .")
                else:
                    head = cell
                triples.append(f"{cell} <{RDF}first> {walk(item)} .")
                previous = cell
            triples.append(f"{previous} <{RDF}rest> {resource(RDF + 'nil')} .")
            return head or fresh()
        if not isinstance(node, dict):
            return scalar(node)
        if set(node) == {"@id"}:
            value = node["@id"]
            return fresh() if str(value).startswith("_:") else resource(str(value))
        if "@value" in node or (set(node) == {"@list"}):
            return walk(node["@value"] if "@value" in node else node["@list"])
        subject = identifier or (
            fresh() if not node.get("@id") or str(node["@id"]).startswith("_:") else absolute(str(node["@id"]))
        )
        for raw_property in sorted(key for key in node if not key.startswith("@")):
            definition = terms.get(raw_property)
            predicate = expand(raw_property)
            coercion = definition.get("@type") if isinstance(definition, dict) else None
            value_type = definition.get("@language") if isinstance(definition, dict) else None
            for value in node[raw_property] if isinstance(node[raw_property], list) else [node[raw_property]]:
                if value is None:
                    continue
                if isinstance(value, str) and coercion in ("@id", "@vocab"):
                    obj = resource(expand(value) if coercion == "@vocab" else value)
                else:
                    obj = walk(value)
                    if isinstance(value, str) and value_type:
                        obj = obj[:-1] + "@" + value_type
                    elif isinstance(value, str) and coercion and coercion not in ("@json", "@literal"):
                        obj = obj[:-1] + "^^<" + iri_escape(datatype(expand(coercion))) + ">"
                triples.append(f"<{iri_escape(subject)}> <{iri_escape(predicate)}> {obj} .")
        for value_type in node.get("@type", []) if isinstance(node.get("@type"), list) else [node.get("@type")]:
            if value_type:
                triples.append(f"<{iri_escape(subject)}> <{RDF}type> {resource(expand(value_type))} .")
        return f"<{iri_escape(subject)}>"

    def walk(value: Any) -> str:
        if isinstance(value, dict):
            if "@value" in value:
                literal = scalar(value["@value"])
                if value.get("@language"):
                    return literal + "@" + value["@language"]
                if value.get("@type"):
                    return literal + "^^<" + iri_escape(datatype(expand(value["@type"]))) + ">"
                return literal
            if "@list" in value:
                return emit(value["@list"])
            if "@set" in value:
                raise ValueError("@set needs its owning property; use a JSON-LD array for the graph")
            return emit(value)
        return emit(value)

    for entity in crate["@graph"]:
        emit(entity)
    return "\n".join(sorted(triples)) + "\n"
