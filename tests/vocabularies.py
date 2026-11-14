"""The vocabularies the Guide's graph refers to, read from their pinned copies, and the terms a graph uses from them.

Every class and property the Guide publishes from an established vocabulary must be a term that vocabulary defines,
at the IRI it defines it, so a consumer that loads the vocabulary finds the Guide's statements. The checks read the
copies in `tests/fixtures/vocabularies/` and never the network, so they give one answer on every machine;
`sources.toml` there records each copy's source, retrieval date and licence.

A graph uses a term where it names a property or a class: as a predicate, as a type, as an additional type, as the
class or property a vocabulary declaration names, or as a literal's datatype. A shape uses the terms it selects and
constrains by, and a JSON-LD context the terms it maps keys to. Any other value is a link and is checked only where
it falls in a pinned namespace, such as a FAIR principle a principle is the same as.
"""

from __future__ import annotations

import datetime
import functools
import json
import re
import sys
import tomllib
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import SH

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402

PINNED = ROOT / "tests" / "fixtures" / "vocabularies"
CONTEXT = ROOT / "tests" / "fixtures" / "ro-crate-1.2-context.json"
SCHEMA = "http://schema.org/"
# Where a graph names a class or a property rather than linking a value.
SCHEMA_POSITIONS = (RDFS.domain, RDFS.range, RDFS.subClassOf, RDFS.subPropertyOf)
SHAPE_POSITIONS = (SH["class"], SH.targetClass, SH.targetSubjectsOf, SH.targetObjectsOf, SH.datatype)
PATH_POSITIONS = (SH.inversePath, SH.alternativePath, SH.zeroOrMorePath, SH.oneOrMorePath, SH.zeroOrOnePath)


@dataclass(frozen=True)
class Vocabulary:
    """A vocabulary: its name, the namespaces it owns and the IRIs it defines in them."""

    name: str
    namespaces: tuple[str, ...]
    defined: frozenset[str]

    def owns(self, iri: str) -> str | None:
        """The longest of its namespaces that the IRI is in, if any."""
        return max((namespace for namespace in self.namespaces if iri.startswith(namespace)), key=len, default=None)


@dataclass(frozen=True)
class Use:
    """One use of an IRI: the IRI, what it is used as (property, class, datatype or value) and where."""

    iri: str
    position: str
    source: str


def manifest() -> list[dict[str, Any]]:
    return tomllib.loads((PINNED / "sources.toml").read_text(encoding="utf-8"))["vocabulary"]


def defined_in(graph: Graph, namespaces: Iterable[str]) -> frozenset[str]:
    """The IRIs in the namespaces that a vocabulary document states something about."""
    namespaces = tuple(namespaces)
    return frozenset(
        str(subject)
        for subject in graph.subjects()
        if isinstance(subject, URIRef) and str(subject).startswith(namespaces)
    )


@functools.cache
def copies() -> tuple[tuple[dict[str, Any], Graph | None], ...]:
    """Each manifest entry with its parsed copy, or None for a namespace that lists its terms instead."""
    return tuple(
        (entry, Graph().parse(PINNED / entry["file"], format=entry["format"]) if "file" in entry else None)
        for entry in manifest()
    )


@functools.cache
def pinned() -> tuple[Vocabulary, ...]:
    """Every pinned vocabulary, parsed from its copy, or from its listed terms where it has no document."""
    vocabularies = []
    for entry, graph in copies():
        namespaces = tuple(entry["namespaces"])
        if graph is not None:
            defined = defined_in(graph, namespaces)
        else:
            defined = frozenset(namespace + term for namespace in namespaces for term in entry["terms"])
        vocabularies.append(Vocabulary(entry["name"], namespaces, defined))
    return tuple(vocabularies)


@functools.cache
def pinned_graph() -> Graph:
    """Every pinned copy in one graph, for the class and property hierarchies they state."""
    union = Graph()
    for _, graph in copies():
        if graph is not None:
            union += graph
    return union


def guide_vocabulary(guide: dict[str, Any], document: str | None = None) -> Vocabulary:
    """The Guide's own vocabulary, read from the document the build publishes at its namespace."""
    base = build_crate.vocabulary_base(guide)
    graph = Graph().parse(data=document or build_crate.vocabulary_document(guide), format="turtle")
    return Vocabulary("the Guide's vocabulary", (base,), defined_in(graph, (base,)))


def crate_graph(crate: dict[str, Any], base: str) -> Graph:
    """The crate's graph, expanded with the pinned RO-Crate context so that reading it makes no request."""
    crate = {**crate, "@context": [json.loads(CONTEXT.read_text("utf-8"))["@context"], *crate["@context"][1:]]}
    return Graph().parse(data=json.dumps(crate), format="json-ld", publicID=base)


def graph_uses(graph: Graph, source: str) -> Iterator[Use]:
    """The terms a data graph uses, and the IRIs it links to."""
    for _, predicate, value in graph:
        yield Use(str(predicate), "property", source)
        if predicate == RDF.type or predicate in SCHEMA_POSITIONS:
            if isinstance(value, URIRef):
                yield Use(str(value), "property" if predicate == RDFS.subPropertyOf else "class", source)
            continue
        if predicate == URIRef(SCHEMA + "additionalType") and str(value).startswith(("http://", "https://")):
            # RO-Crate's context reads an additional type as text; the class it names is still a term.
            yield Use(str(value), "class", source)
        elif isinstance(value, Literal) and value.datatype:
            yield Use(str(value.datatype), "datatype", source)
        elif isinstance(value, URIRef):
            yield Use(str(value), "value", source)


def path_terms(graph: Graph, path: Any) -> Iterator[str]:
    """The properties a SHACL path names: a property, a sequence, an alternative or an inverse of them."""
    if isinstance(path, URIRef):
        yield str(path)
    elif isinstance(path, BNode):
        if graph.value(path, RDF.first) is not None:
            for step in Collection(graph, path):
                yield from path_terms(graph, step)
        for position in PATH_POSITIONS:
            for step in graph.objects(path, position):
                yield from path_terms(graph, step)


def shape_uses(graph: Graph, source: str) -> Iterator[Use]:
    """The terms a shapes graph selects and constrains by. Its own SHACL properties are its language, not terms."""
    for path in graph.objects(None, SH.path):
        for term in path_terms(graph, path):
            yield Use(term, "property", source)
    for position in SHAPE_POSITIONS:
        for value in graph.objects(None, position):
            if isinstance(value, URIRef):
                kind = "datatype" if position == SH.datatype else "property" if "Of" in str(position) else "class"
                yield Use(str(value), kind, source)


def context_uses(context: dict[str, Any], source: str) -> Iterator[Use]:
    """The terms a JSON-LD context maps its keys to. A prefix or the default vocabulary is a namespace, not a term."""

    def expand(value: str) -> str:
        prefix, _, local = value.partition(":")
        target = context.get(prefix)
        if local and not local.startswith("//") and isinstance(target, str):
            return target + local
        return value

    for key, value in context.items():
        if key.startswith("@"):
            continue
        targets = [value] if isinstance(value, str) else [value.get("@id"), value.get("@reverse")]
        for target in targets:
            if not isinstance(target, str) or target.endswith(("#", "/")):
                continue
            local = key.rpartition(":")[2]
            yield Use(expand(target), "class" if local[:1].isupper() else "property", source)


def namespace_of(iri: str) -> str:
    """The namespace an IRI's term is in: everything up to its last '#' or '/'."""
    cut = max(iri.rfind("#"), iri.rfind("/"))
    return iri[: cut + 1]


def other_scheme(iri: str) -> str | None:
    if iri.startswith("https://"):
        return "http://" + iri.removeprefix("https://")
    if iri.startswith("http://"):
        return "https://" + iri.removeprefix("http://")
    return None


def problems(uses: Iterable[Use], vocabularies: Iterable[Vocabulary]) -> list[str]:
    """Each use of a term that no pinned vocabulary defines at that IRI, named with the vocabulary it belongs to.

    A term outside every pinned namespace fails for its namespace, unless the same term in the other scheme is in
    one: then it is that vocabulary's term written in the wrong scheme. A linked value fails only where it is in a
    pinned namespace and the vocabulary does not define it; a link elsewhere is not a term.
    """
    vocabularies = tuple(vocabularies)

    def owner(iri: str) -> tuple[Vocabulary, str] | None:
        owned = [(vocabulary, namespace) for vocabulary in vocabularies if (namespace := vocabulary.owns(iri))]
        return max(owned, key=lambda pair: len(pair[1]), default=None)

    found: set[str] = set()
    for use in uses:
        where = f"{use.iri} (a {use.position} in {use.source})"
        if found_owner := owner(use.iri):
            vocabulary, namespace = found_owner
            if use.iri != namespace and use.iri not in vocabulary.defined:
                found.add(f"{where}: {vocabulary.name} defines no such term")
            continue
        if use.position == "value":
            continue
        swapped = other_scheme(use.iri)
        if swapped and (found_owner := owner(swapped)):
            vocabulary = found_owner[0]
            defines = f"defines it as {swapped}" if swapped in vocabulary.defined else "defines neither form"
            found.add(f"{where}: written in the wrong scheme; {vocabulary.name} {defines}")
            continue
        found.add(f"{where}: its namespace {namespace_of(use.iri)} has no pinned copy")
    return sorted(found)


# ---------------------------------------------------------------------------
# Declarations that hold
#
# Every domain and range the Guide's vocabulary declares must hold for each use in the graph, including the domain
# and range of an established property a Guide term specialises, so that a reasoner adds no class a node does not
# have. A declaration that only the top class would satisfy says nothing and is left out, and a term nothing uses is
# not declared.

TOP_CLASSES = frozenset({RDFS.Resource, OWL.Thing, URIRef(SCHEMA + "Thing")})


class Hierarchy:
    """The RDFS view of some vocabularies: subclasses, subproperties, domains and ranges, read transitively."""

    def __init__(self, *graphs: Graph) -> None:
        self.parents: dict[URIRef, set[URIRef]] = defaultdict(set)
        self.domains: dict[URIRef, set[URIRef]] = defaultdict(set)
        self.ranges: dict[URIRef, set[URIRef]] = defaultdict(set)
        self.cache: dict[URIRef, frozenset[URIRef]] = {}
        for graph in graphs:
            for relation in (RDFS.subClassOf, RDFS.subPropertyOf):
                for child, parent in graph.subject_objects(relation):
                    if isinstance(child, URIRef) and isinstance(parent, URIRef):
                        self.parents[child].add(parent)
            for relation, target in ((RDFS.domain, self.domains), (RDFS.range, self.ranges)):
                for term, value in graph.subject_objects(relation):
                    if isinstance(term, URIRef) and isinstance(value, URIRef):
                        target[term].add(value)
        # A plain literal is a string and a tagged one a language string; every datatype is a kind of literal.
        for datatype in (XSD.string, RDF.langString, XSD.boolean, XSD.integer, XSD.date, XSD.gYear):
            self.parents[datatype].add(RDFS.Literal)

    def above(self, term: URIRef) -> frozenset[URIRef]:
        """The term and every class or property above it."""
        if term not in self.cache:
            seen, pending = {term}, [term]
            while pending:
                for parent in self.parents.get(pending.pop(), ()):
                    if parent not in seen:
                        seen.add(parent)
                        pending.append(parent)
            self.cache[term] = frozenset(seen)
        return self.cache[term]

    def declared(self, prop: URIRef) -> tuple[set[tuple[URIRef, URIRef]], set[tuple[URIRef, URIRef]]]:
        """The domains and ranges a property has, its own and those of the properties it specialises, each with the
        property that declares it."""
        domains = {(domain, owner) for owner in self.above(prop) for domain in self.domains.get(owner, ())}
        ranges = {(range_, owner) for owner in self.above(prop) for range_ in self.ranges.get(owner, ())}
        return domains, ranges


def literal_type(value: Literal) -> URIRef:
    return value.datatype or (RDF.langString if value.language else XSD.string)


def node_types(graph: Graph) -> dict[Any, set[URIRef]]:
    types: dict[Any, set[URIRef]] = defaultdict(set)
    for node, cls in graph.subject_objects(RDF.type):
        if isinstance(cls, URIRef):
            types[node].add(cls)
    return types


def admits(hierarchy: Hierarchy, types: dict[Any, set[URIRef]], value: Any, cls: URIRef) -> bool:
    """Whether a node or a literal already is of a class, by its asserted classes or its datatype."""
    if cls in TOP_CLASSES:
        return True
    if isinstance(value, Literal):
        return cls in hierarchy.above(literal_type(value))
    return any(cls in hierarchy.above(asserted) for asserted in types.get(value, ()))


PREFIXES = (
    ("schema:", SCHEMA),
    ("xsd:", str(XSD)),
    ("rdf:", str(RDF)),
    ("rdfs:", str(RDFS)),
    ("dcterms:", "http://purl.org/dc/terms/"),
    ("skos:", "http://www.w3.org/2004/02/skos/core#"),
    ("adms:", "http://www.w3.org/ns/adms#"),
    ("dcat:", "http://www.w3.org/ns/dcat#"),
)


def short(iri: Any, base: str) -> str:
    text = str(iri)
    for prefix, namespace in (("guide:", base), *PREFIXES):
        if text.startswith(namespace):
            return prefix + text[len(namespace) :]
    return text


def shown(node: Any, base: str) -> str:
    if isinstance(node, Literal):
        return f"{str(node)!r} ({short(literal_type(node), base)})"
    return f"<{node}>"


def declaration_problems(
    graphs: Iterable[Graph], vocabulary: Graph, base: str, used_elsewhere: Iterable[str] = ()
) -> list[str]:
    """Each declaration of the Guide's vocabulary that a use in one of the graphs does not satisfy, each one that only
    the top class would satisfy, and each declared term or class that no graph uses.

    `base` is the vocabulary's namespace; `used_elsewhere` names terms a graph outside these carries, such as the
    terms the page writes into exported results.
    """
    hierarchy = Hierarchy(pinned_graph(), vocabulary)
    properties = {term for term in vocabulary.subjects(RDF.type, RDF.Property) if str(term).startswith(base)}
    classes = {term for term in vocabulary.subjects(RDF.type, RDFS.Class) if str(term).startswith(base)}
    found: set[str] = set()
    for prop in properties:
        for relation in (RDFS.domain, RDFS.range):
            for value in vocabulary.objects(prop, relation):
                if value in TOP_CLASSES:
                    found.add(f"{short(prop, base)}: its {short(relation, base)} {short(value, base)} says nothing")
    used: set[URIRef] = {URIRef(base + term) for term in used_elsewhere}
    # One count per broken declaration over every graph: (term, domain or range, class, declaring term).
    misses: Counter[tuple[URIRef, str, URIRef, URIRef]] = Counter()
    example: dict[tuple[URIRef, str, URIRef, URIRef], str] = {}
    for graph in graphs:
        types = node_types(graph)
        used |= {cls for values in types.values() for cls in values}
        for prop in properties:
            domains, ranges = hierarchy.declared(prop)
            for subject, value in graph.subject_objects(prop):
                used.add(prop)
                checks = [("domain", subject, *pair) for pair in domains] + [("range", value, *pair) for pair in ranges]
                for side, node, cls, owner in checks:
                    if not admits(hierarchy, types, node, cls):
                        misses[(prop, side, cls, owner)] += 1
                        example.setdefault((prop, side, cls, owner), shown(node, base))
    for key, count in misses.items():
        prop, side, cls, owner = key
        through = "" if owner == prop else f", through {short(owner, base)}"
        found.add(
            f"{short(prop, base)}: its {side} {short(cls, base)}{through} does not hold for {count} use(s), "
            f"such as {example[key]}"
        )
    for term in sorted((properties | classes) - used):
        found.add(f"{short(term, base)}: declared, but no graph uses it")
    return sorted(found)


def inferred_classes(graph: Graph, hierarchy: Hierarchy, properties: Iterable[URIRef]) -> dict[Any, set[URIRef]]:
    """The classes an RDFS reasoner adds to each node from the domains and ranges of these properties and of the
    properties they specialise, beyond the superclasses of the classes the node asserts."""
    types = node_types(graph)
    added: dict[Any, set[URIRef]] = defaultdict(set)
    for prop in properties:
        domains, ranges = hierarchy.declared(prop)
        for subject, value in graph.subject_objects(prop):
            for cls, _ in domains:
                if not admits(hierarchy, types, subject, cls):
                    added[subject].add(cls)
            if not isinstance(value, Literal):
                for cls, _ in ranges:
                    if not admits(hierarchy, types, value, cls):
                        added[value].add(cls)
    return added


# ---------------------------------------------------------------------------
# schema.org's own declarations
#
# The pinned schema.org document states domainIncludes and rangeIncludes. Treat each include as a bound the Guide's
# published graph must meet, including declarations inherited from a property's parents. URL is schema.org's textual
# web-address datatype: it admits an IRI reference or an untagged string, while its other datatypes map to XSD.

SCHEMA_DOMAIN = URIRef(SCHEMA + "domainIncludes")
SCHEMA_RANGE = URIRef(SCHEMA + "rangeIncludes")
SCHEMA_URL = URIRef(SCHEMA + "URL")
SCHEMA_LITERAL_CLASSES = {
    XSD.string: frozenset({URIRef(SCHEMA + "Text")}),
    RDF.langString: frozenset({URIRef(SCHEMA + "Text")}),
    XSD.boolean: frozenset({URIRef(SCHEMA + "Boolean")}),
    XSD.integer: frozenset({URIRef(SCHEMA + "Integer"), URIRef(SCHEMA + "Number")}),
    XSD.decimal: frozenset({URIRef(SCHEMA + "Number")}),
    XSD.double: frozenset({URIRef(SCHEMA + "Number")}),
    XSD.float: frozenset({URIRef(SCHEMA + "Number")}),
    XSD.date: frozenset({URIRef(SCHEMA + "Date")}),
    XSD.dateTime: frozenset({URIRef(SCHEMA + "DateTime")}),
    XSD.time: frozenset({URIRef(SCHEMA + "Time")}),
}


def schema_lexical_classes(value: Literal) -> frozenset[URIRef]:
    """The schema.org datatypes a plain literal's own lexical form establishes, beyond its XSD datatype."""
    if literal_type(value) != XSD.string or value.language:
        return frozenset()
    text = str(value)
    found = set()
    for cls, pattern, parser in (
        (
            "Date",
            r"\d{4}(?:-\d{2})?(?:-\d{2})?",
            lambda value: datetime.date.fromisoformat(
                value + ("-01" if len(value) == 7 else "-01-01" if len(value) == 4 else "")
            ),
        ),
        ("DateTime", r".*T.*", lambda value: datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))),
        ("Time", r"\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?", datetime.time.fromisoformat),
    ):
        if re.fullmatch(pattern, text):
            try:
                parser(text)
            except ValueError:
                continue
            found.add(URIRef(SCHEMA + cls))
    duration = (
        r"P(?=\d|T\d)(?:\d+(?:[.,]\d+)?Y)?(?:\d+(?:[.,]\d+)?M)?(?:\d+(?:[.,]\d+)?W)?"
        r"(?:\d+(?:[.,]\d+)?D)?(?:T(?=\d)(?:\d+(?:[.,]\d+)?H)?(?:\d+(?:[.,]\d+)?M)?"
        r"(?:\d+(?:[.,]\d+)?S)?)?"
    )
    if re.fullmatch(duration, text):
        found.add(URIRef(SCHEMA + "Duration"))
    return frozenset(found)


def schema_admits(hierarchy: Hierarchy, types: dict[Any, set[URIRef]], value: Any, cls: URIRef) -> bool:
    """Whether a value has a class schema.org's declaration admits, or its corresponding schema.org datatype."""
    if cls == SCHEMA_URL:
        if isinstance(value, URIRef):
            return True
        if isinstance(value, Literal) and not value.language and literal_type(value) in (XSD.string, XSD.anyURI):
            return True
    if isinstance(value, Literal) and cls in SCHEMA_LITERAL_CLASSES.get(literal_type(value), ()):
        return True
    if isinstance(value, Literal) and cls in schema_lexical_classes(value):
        return True
    return admits(hierarchy, types, value, cls)


def schema_problems(graphs: Iterable[Graph], base: str) -> list[str]:
    """Every schema.org property use none of its pinned domain or range alternatives admits."""
    graphs = tuple(graphs)
    pinned = pinned_graph()
    hierarchy = Hierarchy(pinned, *graphs)
    for relation, target in ((SCHEMA_DOMAIN, hierarchy.domains), (SCHEMA_RANGE, hierarchy.ranges)):
        for prop, cls in pinned.subject_objects(relation):
            if isinstance(prop, URIRef) and isinstance(cls, URIRef):
                target[prop].add(cls)
    pinned_types = node_types(pinned)
    misses: Counter[tuple[URIRef, str]] = Counter()
    example: dict[tuple[URIRef, str], str] = {}
    alternatives: dict[tuple[URIRef, str], set[URIRef]] = {}
    for graph in graphs:
        types = defaultdict(set, {node: set(classes) for node, classes in pinned_types.items()})
        for node, classes in node_types(graph).items():
            types[node] |= classes
        for prop in {predicate for predicate in graph.predicates() if str(predicate).startswith(SCHEMA)}:
            domains, ranges = hierarchy.declared(prop)
            for subject, value in graph.subject_objects(prop):
                for side, node, declared in (("domain", subject, domains), ("range", value, ranges)):
                    if not declared:
                        continue
                    classes = {cls for cls, _ in declared}
                    key = (prop, side)
                    alternatives[key] = classes
                    if not any(schema_admits(hierarchy, types, node, cls) for cls in classes):
                        misses[key] += 1
                        example.setdefault(key, shown(node, base))
    return sorted(
        f"{short(prop, base)}: its {side} "
        + " or ".join(short(cls, base) for cls in sorted(alternatives[(prop, side)], key=str))
        + f" does not hold for {count} use(s), such as {example[(prop, side)]}"
        for (prop, side), count in misses.items()
    )


# ---------------------------------------------------------------------------
# Relations stated once
#
# schema.org and OWL declare inverse pairs; the Guide declares its one operating pair in its own vocabulary. A pair
# must be stated in one direction only. A term names its set, so the set must not list it again.


def relation_problems(graphs: Iterable[Graph], base: str) -> list[str]:
    """Every inverse pair stated in both directions, and every term set that lists its terms."""
    declared = set()
    for predicate in (URIRef(SCHEMA + "inverseOf"), OWL.inverseOf):
        for first, second in pinned_graph().subject_objects(predicate):
            if isinstance(first, URIRef) and isinstance(second, URIRef):
                declared.add((first, second))
    declared = {tuple(sorted(pair, key=str)) for pair in declared}
    found = set()
    for graph in graphs:
        for first, second in declared:
            if first not in set(graph.predicates()) or second not in set(graph.predicates()):
                continue
            for subject, value in graph.subject_objects(first):
                if (value, second, subject) in graph:
                    pair = sorted((short(first, base), short(second, base)))
                    found.add(f"{' and '.join(pair)} stated both ways, such as <{subject}> and <{value}>")
        has_defined_term = URIRef(SCHEMA + "hasDefinedTerm")
        for term_set, term in graph.subject_objects(has_defined_term):
            found.add(f"a set lists its term again with schema:hasDefinedTerm, such as <{term_set}> and <{term}>")
    return sorted(found)


# ---------------------------------------------------------------------------
# Kinds selected by class
#
# Every kind has a class or a term set that selects exactly its records, or a recorded reason why it is reached only
# by IRI (build_crate.KIND_SELECTORS), so a consumer selects a kind without reading an identifier's form.

PREFIXED = {
    "prov": "http://www.w3.org/ns/prov#",
    "fip": build_crate.FIP_TERMS,
    "ftr": build_crate.FTR,
    "dcat": build_crate.DCAT,
    "dcmitype": build_crate.DCMITYPE,
}
IN_SET = URIRef(SCHEMA + "inDefinedTermSet")


def class_iri(name: str, terms: str) -> URIRef:
    prefix, _, local = name.rpartition(":")
    if prefix:
        return URIRef(PREFIXED[prefix] + local)
    return URIRef((terms if name in build_crate.GUIDE_CLASSES else SCHEMA) + name)


def property_iri(name: str, terms: str) -> URIRef:
    return URIRef(
        build_crate.ESTABLISHED_TERMS.get(name, terms + name if name in build_crate.GUIDE_TERMS else SCHEMA + name)
    )


def select(graph: Graph, selector: Any, records: str, terms: str) -> set[Any]:
    """The nodes a kind selector selects in a graph."""
    if isinstance(selector, list):
        return set().union(*(select(graph, item, records, terms) for item in selector))

    def node(value: str) -> URIRef:
        return URIRef(value if "://" in value else records + value)

    if "class" in selector:
        found = set(graph.subjects(RDF.type, class_iri(selector["class"], terms)))
    elif "members" in selector:
        target = selector["members"]
        sets = select(graph, target, records, terms) if isinstance(target, dict) else {node(target)}
        found = {member for term_set in sets for member in graph.subjects(IN_SET, term_set)}
    elif "term" in selector:
        name, term = selector["term"]
        found = set(graph.subjects(property_iri(name, terms), node(term)))
    else:
        found = set()
    if "except" in selector:
        found -= select(graph, selector["except"], records, terms)
    return found


def kind_problems(graph: Graph, selectors: dict[str, Any], kinds: Iterable[str], records: str, terms: str) -> list[str]:
    """Each kind with neither a selector nor a reason, and each selector that does not select exactly its kind's
    records, with how many it misses or adds and one of each."""
    found = []
    subjects = {str(subject) for subject in graph.subjects() if isinstance(subject, URIRef)}
    for kind in sorted(kinds):
        selector = selectors.get(kind)
        if not selector:
            found.append(f"{kind}: no class, term set or recorded reason selects its records")
            continue
        if isinstance(selector, dict) and "reason" in selector:
            if not str(selector["reason"]).strip():
                found.append(f"{kind}: its recorded reason is empty")
            continue
        own = {URIRef(iri) for iri in subjects if iri.startswith(f"{records}{kind}/") and "#" not in iri}
        selected = select(graph, selector, records, terms)
        for label, nodes in (("misses", own - selected), ("also selects", selected - own)):
            if nodes:
                found.append(f"{kind}: its selector {label} {len(nodes)} node(s), such as <{min(map(str, nodes))}>")
    return found
