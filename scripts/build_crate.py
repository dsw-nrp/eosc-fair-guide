#!/usr/bin/env python3
"""Generate the FAIR guide's knowledge base from the TOML sources.

Reads ``content/**/*.toml`` and generates, for ``build_site.py`` to write into the site directory:

- ``ro-crate-metadata.json``: the knowledge base as an RO-Crate 1.2 (Process Run Crate 0.5);
- ``assets/data/kb.js`` and ``assets/data/ui.js``: the crate the page starts with and the interface strings and
  configuration as classic scripts, which load from a local file as well as from a web host; ``kb-<part>.js``: the
  parts of the crate that views load when they first need them (``PART_SCRIPTS``);
- the page with its generated blocks filled: the Content Security Policy, the guide's signposts, a short schema.org
  description of the guide for search engines, the data scripts and the icon sprite;
- ``ro-crate-preview.html``: a copy of the page, which is the crate's HTML preview;
- ``linkset.json`` and the profile's shapes at the guide's address.

None of it is committed: ``GENERATED`` names what the content checks refuse to find in the repository, and the
committed page keeps its generated blocks empty. Running this script builds the whole site (``build_site.py``).
Uses only the Python standard library. The content model is documented in ``docs/content-model.md``.
"""

from __future__ import annotations

import gzip
import html
import json
import os
import re
import shutil
import sys
import tomllib
import unicodedata
import urllib.parse
from datetime import date, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import build_identity
from catalogue_identity import (
    KIND_CODES,
    MAX_ID,
    SAFE_ID,
    TYPE_CODES,
    alternate_id,
    bare_url,
    has_particles,
    source_scheme,
    validate_identity,
)
from corrections import apply as apply_corrections
from publication_location import base_url as publication_base

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
# The record of the favicons the page shows for tools and services, relative to the checkout (D-183).
FAVICONS = Path("assets") / "favicons" / "sources.toml"

# The build's own git-derived identity, computed once per process (see build_identity).
_BUILD_IDENTITY: dict[str, Any] | None = None
_BUILD_ROOT = ROOT


def build_identity_facts() -> dict[str, Any]:
    """The version, commit, date, channel and resolved status of this build, memoized for the process."""
    global _BUILD_IDENTITY
    if _BUILD_IDENTITY is None:
        _BUILD_IDENTITY = build_identity.identity(_BUILD_ROOT)
    return _BUILD_IDENTITY


def reset_build_identity(root: Path = ROOT) -> None:
    """Drop the memoized identity when a new build selects its checkout and release tag."""
    global _BUILD_IDENTITY, _BUILD_ROOT
    _BUILD_IDENTITY = None
    _BUILD_ROOT = root


CRATE_FILE = "ro-crate-metadata.json"
PAGE_FILE = "index.html"
PREVIEW_FILE = "ro-crate-preview.html"
KB_SCRIPT = "assets/data/kb.js"
UI_SCRIPT = "assets/data/ui.js"
LANGUAGE_SCRIPTS = {lang: f"assets/data/kb-{lang}.js" for lang in ("cs", "en")}
# Parts of the knowledge base the page loads only when a view first needs them, so that what every view needs stays
# a small first download: the requirements of the standards the guide ingests (CoreTrustSeal, CDIF) with their
# guidance, the records of the FIP Dashboard and KNAV catalogue snapshots, and the text of the guide's pages. Each is
# a classic script like kb.js; kb.js and the parts together are the crate.
STANDARD_CLAUSES = ("#clause-CTS.", "#clause-CDIF.", "#clause-FDO.", "#clause-FRSM.")
PART_SCRIPTS = {
    "standards": "assets/data/kb-standards.js",
    "fips": "assets/data/kb-fips.js",
    "pages": "assets/data/kb-pages.js",
    "questions": "assets/data/kb-questions.js",
    "model": "assets/data/kb-model.js",
    "advice": "assets/data/kb-advice.js",
}
# View code the page loads when the view first opens, beside the shared code every view needs.
# Views whose code loads when they first open: the catalogue, and the self-check with its parts and report, which a
# path page also loads when saved answers mark gaps on its rail (D-182).
VIEW_SCRIPTS = {
    "catalogue": "assets/js/catalogue-view.js",
    "check": "assets/js/selfcheck.js",
    "selfcheck": "assets/js/selfcheck.js",
}
PART_LANGUAGE_SCRIPTS = {
    name: {lang: path.removesuffix(".js") + f"-{lang}.js" for lang in LANGUAGE_SCRIPTS}
    for name, path in PART_SCRIPTS.items()
}
PROFILE_DIR = "profile/fair-guide"
BASE_URL_ENV = "FAIR_GUIDE_BASE_URL"
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
NKR_OBJECTS = "https://repo.cz/objects/"
# NKR's repository types as the guide's repository kinds.
NKR_KIND = {"disciplinary": "domain", "institutional": "institutional", "generic": "general"}
RE3DATA_RECORD = re.compile(r"re3data\.org/repository/(r3d\d+)")
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
MODEL_TERMS = {
    "preparationStatus": "Preparation status of the approved conceptual-model manuscript, not a published requirement.",
    "modelKind": "Kind of a Layers-and-Seams model record: layer, seam, or implementation example.",
    "implementationLayers": (
        "Functional implementation layers explicitly addressed by an item; independent of FAIR principles and lenses."
    ),
    "implementationSeams": (
        "Information transfers across responsibility boundaries addressed by an item; association is not fulfilment."
    ),
    "introduction": "Introduction to the conceptual implementation model.",
    "ordering": "Functional rationale for the order of model layers, not a temporal sequence or maturity scale.",
    "feedback": "How planning, support and evaluation inform the implementation model throughout.",
    "transfer": "Information that crosses a responsibility boundary in a model seam.",
    "sender": "Actor or system supplying the information in a model seam.",
    "recipient": "Actor or system receiving and acting on the information in a model seam.",
    "carrier": "Standard, service or procedure carrying the information in a model seam.",
    "maintainers": "Actors implementing or maintaining a connection; not necessarily its formally assigned owner.",
    "scope": "Precisely scoped component or connection observed in an implementation example.",
}
TERMS = MODEL_TERMS | {
    "catalogueAddress": "The compact address of a Guide-owned catalogue record.",
    "disclosureLevel": "Disclosure level (L0 to L3) at which an advice item is shown.",
    "adviceKind": "Kind of an advice item that is not ordinary advice, such as the AI-in-FAIRification overlay.",
    "checkAfter": "What to check after following an AI tip, so that its output is verified before it is used.",
    "promptSample": "A short prompt to copy for an AI tip; the parts in brackets are filled in by the user.",
    "block": "Block of a self-check that a question belongs to; a check's blocks are a defined term set in order.",
    "defaultProfile": "Profile a self-check starts with, such as no funding programme for the dataset check.",
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
    "guideType": (
        "The guide's resource type of a cited source or a FIP Dashboard resource, from the crosswalk in "
        "content/guide.toml."
    ),
    "catalogueType": "Type of a FAIR-enabling resource in the FIP Dashboard.",
    "repositoryKind": "Kind of a repository: domain, institutional or general-purpose.",
    "repositoryFunction": "What a reader can use a repository or registry for.",
    "clauseKind": "Kind of a ledger clause: requirement, fulfilment in NRP, or statement.",
    "supersededBy": "Clause or source that replaces a superseded clause.",
    "lensOrder": "Order of a callout's items for one lens, written as '<lens>: <item>, <item>, ...'.",
    "relatedTo": "CoreTrustSeal requirement or CDIF profile related to a FAIR principle.",
    "note": "Additional remark shown with a clause or a self-check item.",
    "guidance": "Original description or guidance from the cited published source, in its original language.",
    "assessmentContext": "Source context that explains an assessment without creating a separate answerable criterion.",
    "disclaimer": "Disclaimer that a snapshot's source publishes about its data, shown while it is present.",
    "prefillLevel": "Highest answer that live evidence can pre-fill for a self-check item that it only partly proves.",
    "championEvidenceOnly": "Champion tests cover part of a question: Partly when that part is met, No when it fails.",
    "lookup": "Service where a user can find out the answer to a self-check item.",
    "guideState": "The reader's saved state for one check, carried in an exported result crate.",
    "guideSources": "The provenance of the evaluator sources an exported result retains, as JSON.",
    "mappingCoverage": (
        "Part of a self-check question that an external evaluator's native criterion supports: whole or partial. "
        "Only whole coverage may suggest an answer, and only from a native pass."
    ),
    "reviewedVersion": (
        "External evaluator version a criterion mapping was reviewed against; other versions keep their native "
        "results without answer suggestions."
    ),
    "lifecycleStage": "Stage of the RDMkit research data life cycle that a path step belongs to.",
    "dataciteRepository": "The repository's ID in DataCite (its DataCite client), as the maintainer reviewed it.",
    "abbreviation": "The abbreviation of a name in each language, such as ČSDA in Czech and CSDA in English (D-173).",
    "operatorSource": "The published page or document that states who operates a service or repository.",
    "operatedBy": "The large research infrastructure operating a catalogue entry, where a source says so (D-174).",
    "researchField": "The science-disciplinary domain of a large research infrastructure in the national roadmap.",
    "infrastructurePhase": "The life-cycle phase of a large research infrastructure in the national roadmap.",
    "infrastructureCharacter": "Whether an infrastructure is single-sited, multi-sited, distributed or virtual.",
    "roadmapSince": "The year a large research infrastructure was included in the national roadmap.",
    "esfriStatus": "The ESFRI Roadmap 2021 status: ESFRI Landmark or ESFRI Project.",
    "nationalNodeOf": "ESFRI research infrastructures that an infrastructure is the Czech node of.",
    "roadmapLocator": "Where in the national roadmap a large research infrastructure's facts are stated.",
    "czechMembershipSince": "The year the Czech Republic entered an ERIC; 'expected' while the ERIC is being set up.",
    "nodeMembership": "An entry's role in the EOSC CZ Node, with its milestone, date checked and source.",
    "nodeMilestone": "The month of the node's project by which a repository's integration is planned (M6, M12).",
    "nodeState": "The state of the EOSC CZ Node in the EOSC Federation, such as candidate.",
    "nodeStateSince": "The date the EOSC CZ Node reached its state, such as its approval as a candidate node.",
    "operatedBySource": "The published page or document that states which infrastructure operates an entry.",
    "operates": "Catalogue entries a large research infrastructure operates, where a source states it (D-174).",
    "developerSource": "The published page that states who developed a repository.",
    "mappingBasis": (
        "Basis of a correspondence between life-cycle stages: published by its source, reviewed by the guide, or "
        "unconfirmed."
    ),
    "nameTranslation": "Languages in which a stage's name is the guide's translation rather than its source's.",
    "descriptionTranslation": "Languages in which a stage's definition is the guide's translation of its source's.",
    "quotedDefinition": "A stage's definition quoted as a second source publishes it, with its stage label.",
    "discipline": "Discipline group of a tool in the KNAV Data Management Tools Catalogue.",
    "rdmkitRecord": "The pinned RDMkit tool record joined to this resource.",
    "trainingSearch": "Training materials about this tool, searched in ELIXIR TeSS.",
    "sourceLocator": "The section or page in the cited version supporting this clause or original definition.",
}

# Established vocabularies the guide reuses (design: *Established vocabularies, term mapping and the guide's
# address*). A property key listed here carries the established IRI in the emitted graph and defines no term of its
# own; the key stays the graph's storage name. docs/content-model.md records the classification an editor reads.
SCHEMA = "http://schema.org/"
DCTERMS = "http://purl.org/dc/terms/"
DCAT = "http://www.w3.org/ns/dcat#"
ADMS = "http://www.w3.org/ns/adms#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
XSD = "http://www.w3.org/2001/XMLSchema#"
RDF_LANG = "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"
ESTABLISHED_TERMS: dict[str, str] = {
    "identifier": SCHEMA + "identifier",
    "alternateIdentifier": SCHEMA + "identifier",
    "dataciteRepository": SCHEMA + "identifier",
    "catalogueAddress": DCTERMS + "identifier",
    "supersededBy": DCTERMS + "isReplacedBy",
    "relatedTo": DCTERMS + "relation",
    "operatorSource": DCTERMS + "source",
    "operatedBySource": DCTERMS + "source",
    "developerSource": DCTERMS + "source",
    "sourceLocator": DCTERMS + "references",
    "roadmapLocator": DCTERMS + "references",
    "abbreviation": SCHEMA + "alternateName",
}

# The guide's own vocabulary: the terms the guide keeps in its namespace. Each declares the broader established
# term it specializes (empty where none exists, with the reason in GUIDE_TERM_REASONS), its domain and its range.
# The typing and status slots specialize their established parent rather than replacing it, because they are
# several distinct slots over one property that the profile targets individually (design: group 21).
GUIDE_TERMS: dict[str, str] = {term: definition for term, definition in TERMS.items() if term not in ESTABLISHED_TERMS}
GUIDE_TERM_SHAPES: dict[str, tuple[str, str, str]] = {
    "preparationStatus": ("", SCHEMA + "ScholarlyArticle", XSD + "string"),
    "modelKind": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "implementationLayers": (DCTERMS + "subject", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "implementationSeams": (DCTERMS + "subject", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "introduction": ("", SCHEMA + "CreativeWork", RDF_LANG),
    "ordering": ("", SCHEMA + "CreativeWork", RDF_LANG),
    "feedback": ("", SCHEMA + "CreativeWork", RDF_LANG),
    "transfer": ("", SCHEMA + "DefinedTerm", RDF_LANG),
    "sender": ("", SCHEMA + "DefinedTerm", RDF_LANG),
    "recipient": ("", SCHEMA + "DefinedTerm", RDF_LANG),
    "carrier": ("", SCHEMA + "DefinedTerm", RDF_LANG),
    "maintainers": ("", SCHEMA + "DefinedTerm", RDF_LANG),
    "scope": ("", SCHEMA + "CreativeWork", RDF_LANG),
    "disclosureLevel": (SCHEMA + "position", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "adviceKind": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "checkAfter": ("", SCHEMA + "CreativeWork", RDF_LANG),
    "promptSample": ("", SCHEMA + "CreativeWork", RDF_LANG),
    "block": ("", SCHEMA + "Question", SCHEMA + "DefinedTermSet"),
    "defaultProfile": ("", SCHEMA + "Quiz", SCHEMA + "DefinedTerm"),
    "tier": ("", SCHEMA + "Question", SCHEMA + "DefinedTerm"),
    "fixAt": ("", SCHEMA + "Question", SCHEMA + "HowToSection"),
    "fixedBy": ("", SCHEMA + "Question", SCHEMA + "DefinedTerm"),
    "appliesTo": ("", SCHEMA + "Question", SCHEMA + "DefinedTerm"),
    "providedByNrpFor": ("", SCHEMA + "Question", SCHEMA + "DefinedTerm"),
    "allowsNotApplicable": ("", SCHEMA + "Question", XSD + "boolean"),
    "serviceStatus": (ADMS + "status", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "statusAsOf": (DCTERMS + "date", SCHEMA + "CreativeWork", XSD + "date"),
    "healthStatus": (ADMS + "status", SCHEMA + "CreativeWork", XSD + "string"),
    "resourceType": (DCTERMS + "type", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "guideType": (DCTERMS + "type", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "catalogueType": (DCTERMS + "type", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "repositoryKind": (DCTERMS + "type", SCHEMA + "DataCatalog", SCHEMA + "DefinedTerm"),
    "repositoryFunction": (DCTERMS + "subject", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "clauseKind": (DCTERMS + "type", SCHEMA + "CreativeWork", XSD + "string"),
    "lensOrder": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "note": (SKOS + "note", SCHEMA + "CreativeWork", RDF_LANG),
    "guidance": (DCTERMS + "description", SCHEMA + "CreativeWork", RDF_LANG),
    "assessmentContext": (DCTERMS + "description", SCHEMA + "CreativeWork", RDF_LANG),
    "disclaimer": (SKOS + "note", SCHEMA + "CreativeWork", RDF_LANG),
    "prefillLevel": ("", SCHEMA + "Question", SCHEMA + "DefinedTerm"),
    "championEvidenceOnly": ("", SCHEMA + "Question", XSD + "boolean"),
    "lookup": ("", SCHEMA + "Question", SCHEMA + "CreativeWork"),
    "guideState": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "guideSources": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "mappingCoverage": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "reviewedVersion": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "lifecycleStage": (DCAT + "theme", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "operatedBy": ("", SCHEMA + "CreativeWork", SCHEMA + "Organization"),
    "researchField": (DCTERMS + "subject", SCHEMA + "Organization", SCHEMA + "DefinedTerm"),
    "infrastructurePhase": (ADMS + "status", SCHEMA + "Organization", SCHEMA + "DefinedTerm"),
    "infrastructureCharacter": ("", SCHEMA + "Organization", XSD + "string"),
    "roadmapSince": ("", SCHEMA + "Organization", XSD + "gYear"),
    "esfriStatus": (ADMS + "status", SCHEMA + "Organization", SCHEMA + "DefinedTerm"),
    "nationalNodeOf": ("", SCHEMA + "Organization", SCHEMA + "Organization"),
    "czechMembershipSince": ("", SCHEMA + "Organization", XSD + "string"),
    "nodeMembership": ("", SCHEMA + "Organization", RDF_LANG),
    "nodeMilestone": ("", SCHEMA + "Organization", XSD + "string"),
    "nodeState": (ADMS + "status", SCHEMA + "Organization", XSD + "string"),
    "nodeStateSince": ("", SCHEMA + "Organization", XSD + "date"),
    "operates": ("", SCHEMA + "Organization", SCHEMA + "CreativeWork"),
    "mappingBasis": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "nameTranslation": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "descriptionTranslation": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "quotedDefinition": ("", SCHEMA + "CreativeWork", RDF_LANG),
    "discipline": (DCTERMS + "subject", SCHEMA + "CreativeWork", XSD + "string"),
    "rdmkitRecord": ("", SCHEMA + "CreativeWork", SCHEMA + "CreativeWork"),
    "trainingSearch": ("", SCHEMA + "CreativeWork", SCHEMA + "CreativeWork"),
}
GUIDE_TERM_REASONS: dict[str, str] = {
    term: reason
    for reason, terms in {
        "The guide's Layers-and-Seams conceptual model has no established equivalent.": [
            "preparationStatus",
            "modelKind",
            "introduction",
            "ordering",
            "feedback",
            "transfer",
            "sender",
            "recipient",
            "carrier",
            "maintainers",
            "scope",
        ],
        "The guide's self-check machinery is its own; no established property expresses it.": [
            "disclosureLevel",
            "adviceKind",
            "checkAfter",
            "promptSample",
            "block",
            "defaultProfile",
            "tier",
            "fixAt",
            "fixedBy",
            "appliesTo",
            "providedByNrpFor",
            "allowsNotApplicable",
            "prefillLevel",
            "championEvidenceOnly",
            "lookup",
        ],
        "The infrastructure that operates an entry, and the entries it operates, are entity references; no single "
        "established property expresses the relation (D-174).": [
            "operatedBy",
            "operates",
        ],
        "A national-roadmap or EOSC CZ Node fact the guide records; no established parent.": [
            "infrastructureCharacter",
            "roadmapSince",
            "nationalNodeOf",
            "czechMembershipSince",
            "nodeMembership",
            "nodeMilestone",
            "nodeStateSince",
        ],
        "Reviewed mapping lineage the guide records over native results; no established parent.": [
            "mappingCoverage",
            "reviewedVersion",
            "mappingBasis",
        ],
        "The guide's translation or quotation provenance.": [
            "nameTranslation",
            "descriptionTranslation",
            "quotedDefinition",
        ],
        "A join to a source's own record and search.": ["rdmkitRecord", "trainingSearch"],
        "A source's own remark, kept distinct from the guide's description.": ["disclaimer", "lensOrder"],
        "The exported result crate's own state and source provenance are the guide's.": ["guideState", "guideSources"],
    }.items()
    for term in terms
}

# The guide's own terms the exported result crate carries: the build owns their IRIs and the export reads them from
# the page configuration rather than declaring its own (design: one shared term context, group 21).
EXPORT_GUIDE_TERMS = ("guideState", "guideSources", "implementationLayers", "implementationSeams")

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
    "guide": "DigitalDocument",
    "document": "DigitalDocument",
    "publication": "CreativeWork",
    "standard": "CreativeWork",
    "vocabulary": "DefinedTermSet",
    "licence": "CreativeWork",
    "policy": "DigitalDocument",
    "data": "CreativeWork",
    "community": "WebPage",
    "project": ["CreativeWork", "Project"],
    "course": "Course",
}


def type_crosswalk(guide: dict[str, Any]) -> dict[str, str]:
    """The guide's resource type of each FIP Dashboard type ('fd:<type>') and citation form ('form:<type>'), so the
    catalogue lists resources, cited sources and FIP Dashboard records by one vocabulary."""
    crosswalk: dict[str, str] = {}
    for item in guide.get("resourceType", []):
        for fd_type in item.get("fipDashboard", []):
            crosswalk[f"fd:{fd_type}"] = item["id"]
        for form in item.get("citation", []):
            crosswalk[f"form:{form}"] = item["id"]
    return crosswalk


def guide_type(crosswalk: dict[str, str], prefix: str, value: str | None) -> dict[str, str] | None:
    """The guide's resource type of a FIP Dashboard type ('fd') or citation form ('form'), as a reference."""
    key = f"{prefix}:{value}"
    return ref(f"#rtype-{crosswalk[key]}") if key in crosswalk else None


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


def apply_base_url(guide: dict[str, Any]) -> None:
    """Derive the page's address from where the guide is published, and its vocabulary and profile from its reviewed
    `namespace`, so that moving the site never renames a term. `FAIR_GUIDE_BASE_URL` gives a build its actual
    publication location instead of the content's `baseUrl`; nothing overrides the namespace. Content from before the
    setting existed named its terms under its own `baseUrl`, so that value, never the environment, is its namespace."""

    def resolved(key: str, value: str | None) -> str:
        try:
            return publication_base(value or "")
        except ValueError as error:
            raise ContentError(f"guide.{key}: {error}") from error

    namespace = resolved("namespace", guide.get("namespace") or guide.get("baseUrl"))
    guide["pageUrl"] = resolved("baseUrl", os.environ.get(BASE_URL_ENV) or guide.get("baseUrl"))
    guide["vocabularyBase"] = namespace + "terms#"
    guide["profile"] = f"{namespace}profile/{guide.get('profileVersion', '')}"


def load_content(content_dir: Path = CONTENT) -> dict[str, Any]:
    """Read every content file into one dictionary."""

    def optional(name: str) -> dict[str, Any]:
        path = content_dir / name
        return load_toml(path) if path.exists() else {}

    stations = [load_toml(path) for path in sorted((content_dir / "stations").glob("*.toml"))]
    stations.sort(key=lambda data: data["station"]["position"])
    checks = [load_toml(path) for path in sorted((content_dir / "checks").glob("*.toml"))]
    snapshots = [load_toml(path) for path in sorted((content_dir / "snapshots").glob("*.toml"))]
    lifecycle_dir = content_dir / "lifecycle"
    lifecycles = [load_toml(path) for path in sorted(lifecycle_dir.glob("*.toml")) if path.name != "crosswalk.toml"]
    lifecycles.sort(key=lambda data: data["lifecycle"]["position"])
    guide = load_toml(content_dir / "guide.toml")
    apply_base_url(guide["guide"])
    content = {
        "guide": guide,
        "principles": optional("principles.toml").get("principle", []),
        "sources": optional("sources.toml").get("source", []),
        "ledger": optional("ledger.toml").get("clause", []),
        "stations": stations,
        "checks": checks,
        "resources": optional("resources.toml").get("resource", []),
        "repositories": optional("repositories.toml").get("repository", []),
        "repository_records": optional("repositories.toml").get("record", []),
        "infrastructures": optional("infrastructures.toml"),
        "node": optional("eosc-node.toml"),
        "snapshots": snapshots,
        "glossary": optional("glossary.toml"),
        "corrections": optional("corrections.toml").get("correction", []),
        "callouts": optional("callouts.toml").get("callout", []),
        "live": optional("live.toml"),
        "provenance": optional("provenance.toml").get("action", []),
        "pages": optional("pages.toml").get("page", []),
        "ui": optional("ui.toml"),
        "icons": optional("icons.toml"),
        "identifiers": optional("identifiers.toml"),
        "link_reviews": optional("link-reviews.toml").get("review", []),
        "model": optional("model.toml"),
        "lifecycles": lifecycles,
        "crosswalk": optional("lifecycle/crosswalk.toml").get("correspondence", []),
        # The normalised favicons kept with the page (scripts/vendor_favicons.py), beside the content they serve.
        "favicons": load_toml(path).get("favicon", []) if (path := content_dir.parent / FAVICONS).is_file() else [],
    }
    try:
        apply_corrections(content["corrections"], content["glossary"])
    except ValueError as error:
        raise ContentError(str(error)) from error
    resolve_requirements(content)
    return content


def resolve_requirements(content: dict[str, Any]) -> None:
    """A check item that names the requirement it asks about (`requirement = "<clause ID>"`) takes from it what it
    does not state itself: its question (the clause's text), its first source (the clause) and its FAIR principles
    (those that link the requirement). A requirement that names no clause is left for the content checks to report."""
    clauses = {clause.get("id"): clause for clause in content["ledger"]}
    linked: dict[str, list[str]] = {}
    for principle in content["principles"]:
        for code in principle.get("cts", []):
            linked.setdefault(f"CTS.{code}", []).append(principle["id"])
        for profile in principle.get("cdif", []):
            linked.setdefault(f"CDIF.{profile}", []).append(principle["id"])
    for data in content["checks"]:
        for item in data.get("item", []):
            clause = clauses.get(item.get("requirement"))
            if clause is None:
                continue
            item.setdefault("statement", clause.get("text"))
            item["sources"] = [clause["id"]] + [source for source in item.get("sources", []) if source != clause["id"]]
            item.setdefault("principles", linked.get(clause["id"], []))


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
    return "#principle-" + principle


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


# The catalogue collections whose emitted compact addresses prose may reference. The rest of the catalogue
# (principles, checks, provenance actions) is reached from the catalogue itself, not from prose.
REFERENCE_COLLECTIONS = (
    "resources",
    "sources",
    "repositories",
    "terms",
    "stations",
    "checks",
    "clauses",
    "tests",
    "metrics",
    "organizations",
    "fips",
    "model",
    "lifecycle",
    "infrastructures",
)


def reference_targets(content: dict[str, Any], graph: Graph) -> dict[str, str]:
    """Canonical compact catalogue addresses plus current authored short forms for Guide content and pages."""
    records = api_records(graph.entities, content)
    allowed = {
        entity_id
        for collection, members in records.items()
        if collection in REFERENCE_COLLECTIONS
        for _, entity_id in members
    }
    targets = {
        address: entity_id
        for entity_id, address in catalogue_addresses(graph.entities, content).items()
        if entity_id in allowed
    }
    targets |= {
        item["id"]: graph.index[item["id"]][0]
        for item in content["resources"] + content["sources"]
        if graph.index.get(item["id"])
    }
    targets |= {
        "term:" + entity_id[len("#term-") :]: entity_id
        for entity_id in graph.entities
        if entity_id.startswith("#term-")
    }
    targets |= {"page:" + page["id"]: f"#page-{page['id']}" for page in content["pages"]}
    targets |= {"station:" + data["station"]["id"]: f"#station-{data['station']['id']}" for data in content["stations"]}
    targets |= {"clause:" + clause["id"]: f"#clause-{clause['id']}" for clause in content["ledger"]}
    infrastructures = (content.get("infrastructures") or {}).get("infrastructure", [])
    targets |= {"infrastructure:" + item["id"]: f"#infrastructure-{item['id']}" for item in infrastructures}
    if infrastructures:
        targets["infrastructures"] = "#infrastructures"
    targets["profile"] = content["guide"]["guide"]["profile"]
    targets |= {
        key: entity_ids[0]
        for key, entity_ids in graph.index.items()
        if key.startswith(("model:", "layer.", "seam.", "example."))
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
    """Add a named term set and its terms; return the term IDs. A set names its scheme both as a schema.org
    DefinedTermSet and as a SKOS ConceptScheme, and each term is a DefinedTerm and a SKOS Concept, so the typing
    sets are one vocabulary over named schemes (design: group 21)."""
    term_ids = [f"#{prefix}-{item['id']}" for item in items]
    graph.add(
        {
            "@id": f"#{set_id}",
            "@type": ["DefinedTermSet", "skos:ConceptScheme"],
            "name": set_name,
            "hasDefinedTerm": refs(term_ids),
        }
    )
    for item, term_id in zip(items, term_ids, strict=True):
        graph.add(
            {
                "@id": term_id,
                "@type": ["DefinedTerm", "skos:Concept"],
                "termCode": item["id"],
                "name": text(item.get("name") or item.get("label")),
                "description": text(item.get("description")),
                "inDefinedTermSet": ref(f"#{set_id}"),
                "skos:inScheme": ref(f"#{set_id}"),
            }
        )
    return term_ids


# ---------------------------------------------------------------------------
# Builders


def build_people(graph: Graph, guide: dict[str, Any], organizations: dict[str, str]) -> dict[str, str]:
    people: dict[str, str] = {}
    for person in guide.get("person", []):
        # A person who opted out of listing their ORCID iD is identified by the guide alone.
        orcid = None if person.get("orcidOptOut") else person.get("orcid")
        entity_id = orcid or f"#person-{person['id']}"
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
        entity_id = f"#org-{organization['id']}"
        organizations[organization["id"]] = entity_id
    for organization in guide.get("organization", []):
        graph.add(
            {
                "@id": organizations[organization["id"]],
                "@type": "Organization",
                "name": text(organization["name"]),
                "url": organization.get("url"),
                "identifier": organization.get("identifier"),
                "sameAs": ref(organization["ror"]) if organization.get("ror") else None,
                "funder": refs([organizations[funder] for funder in as_list(organization.get("funder"))]),
            },
            "organization:" + organization["id"],
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


def name_text(value: Any) -> str | None:
    """A literal name from the content or the graph, whether it is a plain string or a language-tagged value."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return name_text(value.get("@value"))
    if isinstance(value, list):
        return next((name_text(item) for item in value if name_text(item)), None)
    return None


def agent_ref(graph: Graph, name: str) -> str:
    """The entity for a named agent (an operating, hosting or developing organisation): an existing organisation
    with the same name where there is one, a new one otherwise. An agent is named by reference, not by a literal."""
    folded = unicodedata.normalize("NFKD", name).casefold()
    for entity_id, entity in graph.entities.items():
        if entity_id.startswith("#org-") and "Organization" in as_list(entity.get("@type")):
            existing = name_text(entity.get("name"))
            if existing and unicodedata.normalize("NFKD", existing).casefold() == folded:
                return entity_id
    entity_id = f"#org-{slug(name)}"
    if entity_id in graph.entities:
        return entity_id
    graph.add({"@id": entity_id, "@type": "Organization", "name": name})
    return entity_id


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
    defined_terms(
        graph,
        "repository-functions",
        "Repository and registry functions",
        "rfunction",
        guide.get("repositoryFunction", []),
    )
    defined_terms(graph, "research-fields", "Research fields", "rifield", guide.get("researchField", []))
    defined_terms(
        graph, "ri-phases", "Infrastructure life-cycle phases", "riphase", guide.get("infrastructurePhase", [])
    )
    defined_terms(
        graph, "ri-characters", "Infrastructure characters", "richaracter", guide.get("infrastructureCharacter", [])
    )
    defined_terms(graph, "esfri-statuses", "ESFRI statuses", "esfri", guide.get("esfriStatus", []))
    defined_terms(graph, "node-roles", "EOSC CZ Node roles", "noderole", guide.get("nodeRole", []))
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
    """The guide's own vocabulary: one rdf:Property per term, each declaring the broader established term it
    specializes where one exists, its domain and its range."""
    for term, definition in GUIDE_TERMS.items():
        broader, domain, range_ = GUIDE_TERM_SHAPES.get(term, ("", "", ""))
        entity: dict[str, Any] = {
            "@id": vocabulary_base + term,
            "@type": "rdf:Property",
            "rdfs:label": term,
            "rdfs:comment": definition,
        }
        if broader:
            entity["rdfs:subPropertyOf"] = {"@id": broader}
        if domain:
            entity["rdfs:domain"] = {"@id": domain}
        if range_:
            entity["rdfs:range"] = {"@id": range_}
        graph.add(entity)


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
        # CoreTrustSeal requirements are ledger clauses (CTS.R01 ...), with their statement and guidance.
        related = [f"#clause-CTS.{requirement}" for requirement in principle.get("cts", [])]
        related += [f"#clause-CDIF.{profile}" for profile in principle.get("cdif", [])]
        graph.add(
            {
                "@id": principle_iri(principle["id"]),
                "sameAs": ref(principle["iri"]) if principle.get("iri") else None,
                "@type": "DefinedTerm",
                "termCode": principle["id"],
                "name": text(principle.get("label")),
                "description": text(principle.get("statement")),
                "inDefinedTermSet": ref(FAIR_PRINCIPLES),
                "relatedTo": refs(related),
            },
            principle["id"],
        )


def build_sources(
    graph: Graph,
    sources: list[dict[str, Any]],
    organizations: dict[str, str],
    people: dict[str, str],
    names: dict[str, str],
    *,
    crosswalk: dict[str, str],
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
                # The short name shown where the source is named often, as next to each requirement it holds.
                "alternateName": text(source.get("short")),
                "guideType": guide_type(crosswalk, "form", source.get("type")),
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
        "preparationStatus": citation.get("preparationStatus"),
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
                "name": text(clause.get("title")),
                "text": text(clause.get("text")),
                "guidance": {
                    "@value": clause["guidance"].strip(),
                    "@language": clause.get("guidanceLanguage", "en"),
                }
                if isinstance(clause.get("guidance"), str)
                else None,
                "about": refs([principle_iri(principle) for principle in clause.get("principles", [])]),
                "audience": refs([f"#actor-{clause['actor']}"] if clause.get("actor") else []),
                "isPartOf": refs(graph.resolve([clause["source"]])) if clause.get("source") else None,
                "clauseKind": clause.get("kind"),
                "sourceLocator": clause.get("locator"),
                "creativeWorkStatus": clause.get("status", "current"),
                "note": text(clause.get("note")),
            },
            clause["id"],
        )
    for clause in clauses:
        # A clause may name clauses later in the ledger (its replacement, its note's sources), so those links are
        # added once every clause exists.
        if clause.get("supersededBy"):
            entity = graph.entities[f"#clause-{clause['id']}"]
            entity["supersededBy"] = ref(graph.resolve([clause["supersededBy"]])[0])
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
            is_tip = level == "L2" or advice.get("kind") in ("ai", "key")
            step_ids = [f"{advice_id}-step-{number}" for number in range(1, len(advice.get("steps", [])) + 1)]
            # The next step first, then at most one related tool.
            actions = as_list(advice.get("action"))
            action_ids = [
                f"{advice_id}-action" + (f"-{number}" if number > 1 else "") for number in range(1, len(actions) + 1)
            ]
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
                    "checkAfter": text(advice.get("check")),
                    "promptSample": text(advice.get("prompt")),
                    "citation": refs(graph.resolve(advice.get("sources", []))),
                    "isPartOf": ref(station_id),
                    "hasPart": refs(step_ids),
                    "potentialAction": refs(action_ids),
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
            for action_id, action in zip(action_ids, actions, strict=True):
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
                "lifecycleStage": ref(lifecycle_stage_id(PATH_LIFECYCLE, station["lifecycleStage"]))
                if station.get("lifecycleStage")
                else None,
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
                    "assessmentContext": True if item.get("context") else None,
                    "note": text(item.get("note")),
                    "additionalProperty": refs(prefill_ids),
                    "prefillLevel": item.get("prefillLevel"),
                    "championEvidenceOnly": True if item.get("championEvidenceOnly") else None,
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
        rdmkit = resource.get("rdmkit", {})
        registry_links = [
            base + urllib.parse.quote(rdmkit[key], safe="")
            for key, base in (
                ("biotools", "https://bio.tools/"),
                ("fairsharing", "https://fairsharing.org/FAIRsharing."),
            )
            if rdmkit.get(key) and rdmkit[key] != "NA"
        ]
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
            "repositoryFunction": refs([f"#rfunction-{value}" for value in resource.get("functions", [])]),
            "serviceStatus": ref(f"#status-{resource['status']}") if resource.get("status") else None,
            "statusAsOf": iso(resource["asOf"]) if resource.get("asOf") else None,
            "operatorName": text((resource.get("operator") or {}).get("name")),
            "operatorSource": (resource.get("operator") or {}).get("source"),
            "rdmkitRecord": (
                "https://rdmkit.elixir-europe.org/all_tools_and_resources#" + rdmkit["id"] if rdmkit.get("id") else None
            ),
            "trainingSearch": (
                "https://tess.elixir-europe.org/search?" + urllib.parse.urlencode({"q": '"' + rdmkit["tess"] + '"'})
                if rdmkit.get("tess")
                else None
            ),
            "sameAs": refs(
                resource.get("sameAs", [])
                + registry_links
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
    # The guide's list of resources, which advice can point to as a whole.
    graph.add(
        {
            "@id": "#resources",
            "@type": "CreativeWork",
            "name": "Resources",
            "hasPart": refs([f"#resource-{resource['id']}" for resource in resources]),
        }
    )
    return cited


def link_resources(graph: Graph, resources: list[dict[str, Any]]) -> None:
    """Each station mentions the resources recommended at it."""
    for resource in resources:
        for station in resource.get("stations", []):
            station_entity = graph.entities.get(f"#station-{station}")
            if station_entity is not None:
                append_ref(station_entity, "mentions", f"#resource-{resource['id']}")


def repository_entity(repository: dict[str, Any], based_on: str) -> dict[str, Any]:
    same_as = []
    if repository.get("re3data"):
        same_as.append(f"https://www.re3data.org/repository/{repository['re3data']}")
    if repository.get("doi"):
        # The DOI of the same re3data record, by which DataCite finds the repository.
        same_as.append(f"https://doi.org/{repository['doi']}")
    if repository.get("fairsharing"):
        same_as.append(f"https://doi.org/{repository['fairsharing']}")
    if repository.get("nkr"):
        same_as.append(f"{NKR_OBJECTS}{repository['nkr']}")
    if repository.get("fipDashboard"):
        same_as.append(FIP_DASHBOARD + repository["fipDashboard"])
    # A name re3data gives only in English takes the first name it tags as Czech for Czech readers; a curated name
    # (a table, from the entry or its record annotation) corrects both (D-173).
    name = repository["name"]
    czech = repository.get("namesCs") or []
    if isinstance(name, str) and czech and czech[0] != name:
        name = {"cs": czech[0], "en": name}
    return {
        "@type": "DataCatalog",
        "name": text(name),
        "abbreviation": text(repository.get("abbreviation")),
        "url": repository.get("url"),
        "repositoryKind": ref(f"#rkind-{repository['kind']}") if repository.get("kind") else None,
        "repositoryFunction": refs([f"#rfunction-{value}" for value in repository.get("functions", ["deposit-data"])]),
        "keywords": text(repository.get("subjects"))
        or [{"@value": subject, "@language": "en"} for subject in repository.get("subjectsEn", [])],
        "identifier": repository["id"],
        "inLanguage": repository.get("languages"),
        "sameAs": refs(same_as),
        "dataciteRepository": repository.get("datacite"),
        "serviceStatus": ref(f"#status-{repository['status']}") if repository.get("status") else None,
        "statusAsOf": iso(repository["asOf"]) if repository.get("asOf") else None,
        "operatorName": text((repository.get("operator") or {}).get("name")),
        "operatorSource": (repository.get("operator") or {}).get("source"),
        "developerName": text((repository.get("developer") or {}).get("name")),
        "developerSource": (repository.get("developer") or {}).get("source"),
        "isBasedOn": [ref(based_on)],
    }


def repository_key(repository: dict[str, Any]) -> str:
    if repository.get("re3data"):
        return f"re3data:{repository['re3data']}"
    return "url:" + (repository.get("url") or repository["id"]).rstrip("/").lower()


def snapshot_id(snapshot: dict[str, Any]) -> str:
    return f"#snapshot-{slug(snapshot['snapshot']['source'])}"


def nkr_repositories(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """The repositories of an NKR snapshot as repository records: NKR's name, address, kind and keywords, its record
    ID and the re3data record it names. Nothing else of the record is read here."""
    if snapshot.get("snapshot", {}).get("source") != "NKR":
        return []
    repositories = []
    for record in snapshot.get("record", []):
        registries = [
            str(item.get("relatedRegistryUrl", ""))
            for item in as_list(record.get("relatedRegistry"))
            if isinstance(item, dict)
        ]
        r3d = next((found.group(1) for url in registries if (found := RE3DATA_RECORD.search(url))), None)
        repositories.append(
            {
                "id": record["id"],
                "name": str(record["repositoryName"]),
                "url": record.get("mainUrl"),
                "nkr": alternate_id(record, "nkr"),
                "re3data": r3d,
                "kind": NKR_KIND.get(str(record.get("type", ""))),
                "subjects": {
                    "cs": ", ".join(map(str, as_list(record.get("keywordCz")))),
                    "en": ", ".join(map(str, as_list(record.get("keywordEn")))),
                },
            }
        )
    return repositories


def build_snapshots(graph: Graph, snapshots: list[dict[str, Any]]) -> list[str]:
    """Add one entity per snapshot, with its retrieval date, the catalogue entry of its source where the guide has
    one and, for the FIP Dashboard, its disclaimer."""
    ids = []
    for snapshot in snapshots:
        info = snapshot["snapshot"]
        source = f"#resource-{slug(info['source'])}"
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
                    "about": ref(source) if source in graph.entities else None,
                },
                f"snapshot:{slug(info['source'])}",
            )
        )
    return ids


def annotate_repositories(graph: Graph, repository_ids: list[str], snapshots: list[dict[str, Any]]) -> None:
    """Join each snapshot annotation (FAIRsharing, DataCite) to the repository it names, by re3data record or else
    by address: its FAIRsharing record becomes one of the repository's identifiers, its DataCite repository is
    recorded where the guide names none, and the snapshot becomes one of its sources. An annotation adds no
    repository of its own; one that names no listed repository is left out."""
    by_re3data: dict[str, dict[str, Any]] = {}
    by_address: dict[str, dict[str, Any]] = {}
    for entity_id in repository_ids:
        entity = graph.entities[entity_id]
        values = [str(item) for item in as_list(entity.get("identifier"))]
        values += [str(item.get("@id", "")) for item in as_list(entity.get("sameAs")) if isinstance(item, dict)]
        for value in values:
            found = RE3DATA_RECORD.search(value) or re.fullmatch(r"(r3d\d+)", value)
            if found:
                by_re3data.setdefault(found.group(1), entity)
        if entity.get("url"):
            by_address.setdefault(bare_url(entity["url"]), entity)
    for snapshot in snapshots:
        for row in snapshot.get("annotation", []):
            entity = (
                by_re3data.get(row["re3data"]) if row.get("re3data") else by_address.get(bare_url(row.get("url", "")))
            )
            if entity is None:
                continue
            if row.get("fairsharing"):
                same_as = as_list(entity.get("sameAs"))
                record = f"https://doi.org/{row['fairsharing']}"
                if record not in [item.get("@id") for item in same_as if isinstance(item, dict)]:
                    entity["sameAs"] = same_as + [ref(record)]
            if row.get("datacite") and not entity.get("dataciteRepository"):
                entity["dataciteRepository"] = row["datacite"]
            if snapshot_id(snapshot) not in [item.get("@id") for item in as_list(entity.get("isBasedOn"))]:
                append_ref(entity, "isBasedOn", snapshot_id(snapshot))


def nkr_config(snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    """What the repository check pre-fills from NKR: each listed repository's record with its reviewed fields, and
    the date of the snapshot; none before NKR lists a repository."""
    snapshot = next((item for item in snapshots if item.get("snapshot", {}).get("source") == "NKR"), None)
    if not snapshot:
        return None
    fields = snapshot["snapshot"].get("fields", [])
    return {
        "retrieved": iso(snapshot["snapshot"]["retrieved"]),
        "records": [
            {
                "id": record["id"],
                "sourceId": alternate_id(record, "nkr"),
                "content": {name: record[name] for name in fields if name in record},
            }
            for record in snapshot.get("record", [])
        ],
    }


def build_repositories(
    graph: Graph,
    curated: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    resources: list[dict[str, Any]],
    records: list[dict[str, Any]] | None = None,
) -> list[str]:
    """List repositories and registries by meaning, regardless of source. Reviewed record annotations join
    registry identities without changing a snapshot's facts or inferring identity from a similar host or name.
    Source records remain available as evidence; the catalogue lists the described thing once."""
    records = records or []
    annotations = {item["re3data"]: item for item in records if item.get("re3data")}
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
        sources.append((snapshot_id(snapshot), snapshot.get("repository", []) + nkr_repositories(snapshot)))
    for based_on, repositories in sources:
        for source_record in repositories:
            repository = source_record | annotations.get(source_record.get("re3data"), {})
            key = repository_key(repository)
            entity = repository_entity(repository, based_on)
            if repository.get("fipDashboard"):
                entity["isBasedOn"].append(ref("#snapshot-fip-dashboard"))
            if key in merged:
                existing = merged[key]
                for prop, value in entity.items():
                    if prop == "isBasedOn":
                        existing["isBasedOn"] += [item for item in value if item not in existing["isBasedOn"]]
                    elif prop in ("sameAs", "alternateIdentifier"):
                        existing[prop] = as_list(existing.get(prop)) + [
                            item for item in as_list(value) if item not in as_list(existing.get(prop))
                        ]
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
            for prop in ("repositoryKind", "repositoryFunction", "keywords", "isBasedOn", "dataciteRepository"):
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

    annotate_repositories(graph, repository_ids, snapshots)

    # Registry resources belong here too, even when the guide recommends or cites them elsewhere.
    for resource in resources:
        if resource.get("type") == "registry":
            entity_id = f"#resource-{resource['id']}"
            entity = graph.entities[entity_id]
            append_ref(entity, "isBasedOn", "#repositories-curated")
            if resource.get("fipDashboard"):
                append_ref(entity, "isBasedOn", "#snapshot-fip-dashboard")
            if entity_id not in repository_ids:
                repository_ids.append(entity_id)
    linked = {
        item["@id"].removeprefix(FIP_DASHBOARD)
        for entity_id in repository_ids
        for item in as_list(graph.entities[entity_id].get("sameAs"))
        if isinstance(item, dict) and item.get("@id", "").startswith(FIP_DASHBOARD)
    }
    dashboard_annotations = {item["fipDashboard"]: item for item in records if item.get("fipDashboard")}
    for snapshot in snapshots:
        for record in snapshot.get("resource", []):
            if record.get("type") != "repository" or alternate_id(record, "fip-dashboard") in linked:
                continue
            entity_id = f"#fer-{record['id']}"
            entity = graph.entities[entity_id]
            functions = dashboard_annotations.get(alternate_id(record, "fip-dashboard"), {}).get("functions", [])
            if functions:
                entity["repositoryFunction"] = refs([f"#rfunction-{value}" for value in functions])
            repository_ids.append(entity_id)
    for entity_id in repository_ids:
        entity = graph.entities[entity_id]
        for record in as_list(entity.get("sameAs")):
            url = record.get("@id", "") if isinstance(record, dict) else str(record)
            if url.startswith(FIP_DASHBOARD):
                graph.index["fip-dashboard." + url.removeprefix(FIP_DASHBOARD)] = [entity_id]
            elif url.startswith("https://www.re3data.org/repository/"):
                graph.index["re3data." + url.rsplit("/", 1)[-1]] = [entity_id]
    graph.add(
        {
            "@id": "#repositories",
            "@type": "CreativeWork",
            "name": "Repositories and registries",
            "hasPart": refs(repository_ids),
        }
    )
    return repository_ids


KNAV_REGISTRY = "knav-tools"  # the life-cycle model of the KNAV catalogue's steps (content/lifecycle/)


def build_knav_tools(graph: Graph, content: dict[str, Any]) -> list[str]:
    """The tools of the KNAV Data Management Tools Catalogue snapshot, each with its life-cycle steps, discipline
    groups and the catalogue's licence. A tool that a curated entry (`knav`) or a record annotation names is that
    entry: its record says so in `sameAs` and the catalogue lists the entry once."""
    snapshot = next((item for item in content["snapshots"] if item.get("tool")), None)
    if snapshot is None:
        return []
    info = snapshot["snapshot"]
    standing: dict[str, str] = {}
    for entry in content["resources"] + content["repositories"] + content["sources"]:
        if entry.get("knav") and graph.index.get(entry["id"]):
            standing[entry["knav"]] = graph.index[entry["id"]][0]
    # A FIP Dashboard record a curated entry links is listed as that entry, so a tool joined to it is too.
    curated_records = {
        entry["fipDashboard"]: graph.index[entry["id"]][0]
        for entry in content["resources"] + content["repositories"]
        if entry.get("fipDashboard") and graph.index.get(entry["id"])
    }
    for record in content.get("repository_records", []):
        if record.get("knav"):
            if record.get("re3data"):
                target = graph.index[f"re3data.{record['re3data']}"][0]
            else:
                dashboard = record["fipDashboard"]
                target = (
                    curated_records.get(dashboard)
                    or graph.index.get(f"fip-dashboard.{dashboard}", [f"#fer-{dashboard}"])[0]
                )
            standing[record["knav"]] = target
    tool_ids = []
    for tool in snapshot["tool"]:
        tool_ids.append(
            graph.add(
                {
                    "@id": f"#knav-{tool['id']}",
                    "@type": "CreativeWork",
                    "identifier": tool["id"],
                    "name": tool["name"],
                    "description": {"@value": tool["description"], "@language": "en"},
                    "url": tool.get("url"),
                    "lifecycleStage": refs([lifecycle_stage_id(KNAV_REGISTRY, step) for step in tool["steps"]]),
                    "discipline": tool.get("disciplines", []),
                    "license": info.get("license"),
                    "isBasedOn": ref(snapshot_id(snapshot)),
                    "sameAs": ref(standing[alternate_id(tool, "knav")])
                    if alternate_id(tool, "knav") in standing
                    else None,
                },
                f"knav.{alternate_id(tool, 'knav')}",
            )
        )
    graph.add(
        {
            "@id": "#knav-tools",
            "@type": "CreativeWork",
            "name": "KNAV Data Management Tools Catalogue",
            "url": info.get("url"),
            "isBasedOn": ref(snapshot_id(snapshot)),
            "hasPart": refs(tool_ids),
        }
    )
    return ["#knav-tools"]


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


def build_reviews(
    graph: Graph, item_id: str, verifications: list[dict[str, Any]], organizations: dict[str, str]
) -> list[str]:
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
                "author": ref("#fd-org-" + organizations[verification["verifier"]]),
                "reviewAspect": verification.get("level"),
                "dateCreated": verification.get("date"),
                "url": verification.get("url"),
                "reviewBody": text(verification.get("note")),
            }
        )
    return review_ids


def catalogue_entry(graph: Graph, row: dict[str, Any]) -> str | None:
    """The catalogue entry a node member or an operator relation names: a resource by its ID, a repository by its
    curated ID or by its re3data record (a repository listed from re3data has no ID of the guide's own)."""
    if row.get("resource"):
        entity_id = f"#resource-{row['resource']}"
        return entity_id if entity_id in graph.entities else None
    value = str(row.get("repository", ""))
    for entity_id in (f"#repository-{value}", f"#resource-{value}"):
        if entity_id in graph.entities:
            return entity_id
    for entity_id, entity in graph.entities.items():
        if entity.get("@type") != "DataCatalog":
            continue
        external = [str(item.get("@id", "")) for item in as_list(entity.get("sameAs")) if isinstance(item, dict)]
        if f"https://www.re3data.org/repository/{value}" in external:
            return entity_id
    return None


def build_infrastructures(graph: Graph, data: dict[str, Any]) -> list[str]:
    """The large research infrastructures of the national roadmap (D-174): each with its names, hosting institution,
    field, phase, character, year of inclusion and ESFRI status (Annex 1), the European research infrastructures it is
    the Czech node of (Annex 7), the ERICs it belongs to through the Czech Republic's membership (Annex 6), and the
    catalogue entries it operates where a source states it. Three relations stay distinct: node, ERIC membership and
    operating an entry; EOSC CZ Node membership is the entry's own (build_node)."""
    info = data.get("infrastructures", {})
    items = data.get("infrastructure", [])
    if not items:
        return []
    based_on = graph.resolve([info[key] for key in ("source", "namesSource") if info.get(key)])
    collection_sources = list(based_on)
    ids = []

    def european_ri(name: str, status: str) -> str:
        entity_id = f"#european-ri-{slug(name)}"
        if entity_id not in graph.entities:
            graph.add({"@id": entity_id, "@type": "Organization", "name": name, "esfriStatus": ref(f"#esfri-{status}")})
        return entity_id

    def eric(name: str, since: str) -> str:
        entity_id = f"#eric-{slug(name)}"
        if entity_id not in graph.entities:
            graph.add(
                {
                    "@id": entity_id,
                    "@type": "Organization",
                    "name": name,
                    "czechMembershipSince": since,
                    "isBasedOn": refs(based_on[:1]),
                }
            )
        return entity_id

    for item in items:
        entity_id = f"#infrastructure-{item['id']}"
        item_sources = graph.resolve(
            [source for source in (info.get("source"), item.get("namesSource", info.get("namesSource"))) if source]
        )
        collection_sources.extend(source for source in item_sources if source not in collection_sources)
        operated = []
        for row in item.get("operates", []):
            target = catalogue_entry(graph, row)
            if target is None:
                raise ContentError(f"infrastructure {item['id']}: operates an unknown catalogue entry {row}")
            graph.entities[target]["operatedBy"] = ref(entity_id)
            graph.entities[target]["operatedBySource"] = row.get("evidence")
            operated.append(target)
        ids.append(
            graph.add(
                {
                    "@id": entity_id,
                    "@type": "Organization",
                    "identifier": item["id"],
                    "name": text(item["name"]),
                    "abbreviation": item["acronym"],
                    "url": item.get("url"),
                    "sameAs": ref(item["website"]) if item.get("website") else None,
                    "hostingInstitution": item.get("host"),
                    "researchField": ref(f"#rifield-{item['field']}") if item.get("field") else None,
                    "infrastructurePhase": ref(f"#riphase-{item['phase']}"),
                    "infrastructureCharacter": ref(f"#richaracter-{item['character']}"),
                    "roadmapSince": str(item["included"]),
                    "esfriStatus": refs([f"#esfri-{status}" for status in item.get("esfri", [])]),
                    "nationalNodeOf": refs([european_ri(row["name"], row["esfri"]) for row in item.get("nodeOf", [])]),
                    "memberOf": refs([eric(row["name"], row["entry"]) for row in item.get("eric", [])]),
                    "operates": refs(operated),
                    # The FIP of the infrastructure's community in the FIP Dashboard snapshot, where it has one.
                    "subjectOf": ref(graph.index["fip:" + item["fip"]][0]) if item.get("fip") else None,
                    "roadmapLocator": item.get("annex1"),
                    "isBasedOn": refs(item_sources),
                },
                f"infrastructure:{item['id']}",
            )
        )
    graph.add(
        {
            "@id": "#infrastructures",
            "@type": "CreativeWork",
            "name": "Large research infrastructures",
            "hasPart": refs(ids),
            "isBasedOn": refs(collection_sources),
            "dateModified": iso(info["checked"]) if info.get("checked") else None,
        }
    )
    return ["#infrastructures", *ids]


def build_node(graph: Graph, data: dict[str, Any]) -> list[str]:
    """The EOSC CZ Node (D-172): its operator, its state and its members. Each member entry carries its membership:
    the role, any planned milestone, the date checked and the source, so a badge says no more than the charter does."""
    node = data.get("node")
    if not node:
        return []
    sources = graph.resolve(node.get("sources", []))
    operator = f"#infrastructure-{node['operator']}"
    memberships = []
    for member in data.get("member", []):
        target = catalogue_entry(graph, member)
        if target is None:
            raise ContentError(f"EOSC CZ Node: member {member} names no catalogue entry")
        membership_id = f"#node-membership-{slug(target.lstrip('#'))}"
        graph.add(
            {
                "@id": membership_id,
                "@type": "OrganizationRole",
                "roleName": ref(f"#noderole-{member['role']}"),
                "nodeMilestone": member.get("milestone"),
                "statusAsOf": iso(node["checked"]),
                "citation": refs(sources[:1]),
                "description": member.get("locator"),
                "member": ref(target),
                "memberOf": ref("#eosc-cz-node"),
            }
        )
        graph.entities[target]["nodeMembership"] = ref(membership_id)
        memberships.append(membership_id)
    graph.add(
        {
            "@id": "#eosc-cz-node",
            "@type": "Organization",
            "identifier": node["id"],
            "name": node["name"],
            "url": node.get("url"),
            "nodeState": node.get("state"),
            "statusAsOf": iso(node["checked"]),
            "nodeStateSince": iso(node["stateDate"]) if node.get("stateDate") else None,
            "operatedBy": ref(operator) if operator in graph.entities else None,
            "isBasedOn": refs(sources),
            "member": refs(memberships),
        },
        "node:eosc-cz-node",
    )
    return ["#eosc-cz-node", *memberships]


def build_fip_dashboard(graph: Graph, snapshots: list[dict[str, Any]], crosswalk: dict[str, str]) -> list[str]:
    """Add the FIP Dashboard snapshot: organisations, FAIR-enabling resources with their verification, and FIPs."""
    snapshot = next((item for item in snapshots if item.get("fip") or item.get("resource")), None)
    if snapshot is None:
        return []
    based_on = ref(snapshot_id(snapshot))
    base = snapshot["snapshot"]["url"].rstrip("/")
    organizations = {alternate_id(row, "fip-dashboard"): row["id"] for row in snapshot.get("organization", [])}
    resources = {alternate_id(row, "fip-dashboard"): row["id"] for row in snapshot.get("resource", [])}

    def organization_ref(value):
        return ref("#fd-org-" + organizations[value]) if value in organizations else None

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
        review_ids = build_reviews(graph, fer_id, resource.get("verification", []), organizations)
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
                "guideType": guide_type(crosswalk, "fd", resource.get("type")),
                "spatialCoverage": resource.get("scope"),
                "about": refs([principle_iri(principle) for principle in resource.get("principles", [])]),
                "provider": organization_ref(resource.get("provider")),
                "sameAs": refs(
                    (
                        [f"{base}/resources/{alternate_id(resource, 'fip-dashboard')}"]
                        if alternate_id(resource, "fip-dashboard")
                        else []
                    )
                    + ([resource["identifier"]] if resource.get("identifier") else [])
                ),
                "review": refs(review_ids),
                "isBasedOn": based_on,
            },
            f"fer:{alternate_id(resource, 'fip-dashboard')}",
        )
    fip_ids = []
    for fip in snapshot.get("fip", []):
        fip_id = f"#fip-{fip['id']}"
        fip_ids.append(fip_id)
        review_ids = build_reviews(graph, fip_id, fip.get("verification", []), organizations)
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
                    "mentions": ref("#fer-" + resources[declaration["resource"]]),
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
                "author": organization_ref(fip.get("community")),
                "sameAs": ref(f"{base}/profiles/{alternate_id(fip, 'fip-dashboard')}")
                if alternate_id(fip, "fip-dashboard")
                else None,
                "review": refs(review_ids),
                "hasPart": refs(declaration_ids),
                "isBasedOn": based_on,
            },
            f"fip:{alternate_id(fip, 'fip-dashboard')}",
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


def build_glossary(graph: Graph, glossary: dict[str, Any], clauses: list[dict[str, Any]] | None = None) -> None:
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
                "identifier": term["id"],
                "termCode": alternate_id(term, "heslar"),
                "subjectOf": refs(
                    [f"#clause-{item['id']}" for item in clauses or [] if str(term["id"]) in item.get("terms", [])]
                ),
                "name": text(term["label"]),
                "description": text({term.get("definitionLanguage", "cs"): term["definition"]})
                if isinstance(term.get("definition"), str)
                else text(term.get("definition")),
                "url": term.get("url"),
                "license": info.get("license") if term.get("definition") else None,
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
                },
                f"callout.{callout['id']}.{item['id']}",
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


def champion_endpoint(champion: dict[str, Any], test: dict[str, Any]) -> str | None:
    """A curated test's invocation URL: its own endpoint, or the service endpoint with the provider's test ID."""
    native, base = alternate_id(test, "fair-champion"), champion.get("endpoint")
    return test.get("endpoint") or (base.rstrip("/") + "/" + native if base and native else None)


def build_tests(graph: Graph, live: dict[str, Any]) -> list[str]:
    champion = live.get("champion", {})
    test_ids = []
    for test in champion.get("test", []):
        native = alternate_id(test, "fair-champion")
        test_id = f"#test-{test['id']}"
        test_ids.append(test_id)
        graph.add(
            {
                "@id": test_id,
                "@type": "CreativeWork",
                "additionalType": FTR_TEST,
                "identifier": test["id"],
                "name": text(test.get("label")) or test["id"],
                "url": champion_endpoint(champion, test),
                "description": text(test.get("description")),
                "subjectOf": refs(
                    [test.get("record") or champion["testRecord"].format(id=native), champion["documentation"]]
                    if champion.get("testRecord") and champion.get("documentation")
                    else []
                ),
                "about": ref(principle_iri(test["principle"])) if test.get("principle") else None,
                "healthStatus": test.get("health"),
                "statusAsOf": iso(test["asOf"]) if test.get("asOf") else None,
            },
            f"test:{test['id']}",
        )
    # Executable local definitions are real crate files, shared by related criteria. A criterion has its own
    # named function and record; attaching the shared source keeps the algorithm inspectable without copying it.
    attached: set[str] = set()
    for test in live.get("test", []):
        question_id = "#item-" + test["question"]
        question = graph.entities.get(question_id)
        if question is None:
            raise ContentError(f"test:{test['id']}: unknown question {test['question']}")
        files = ["assets/js/assess.js", test["script"]]
        doc_path, _, fragment = test["documentation"].partition("#")
        for path in files + [doc_path]:
            if path in attached:
                continue
            attached.add(path)
            code = path.endswith(".js")
            graph.add(
                {
                    "@id": path,
                    "@type": ["File", "SoftwareSourceCode"] if code else ["File", "DigitalDocument"],
                    "name": Path(path).name,
                    "encodingFormat": "application/javascript" if code else "text/html",
                    "programmingLanguage": "JavaScript" if code else None,
                    "license": ref(LICENSES["MIT" if code else "CC-BY-4.0"][0]),
                    "isPartOf": ref("./"),
                }
            )
        doc_id = "#local-test-documentation-" + test["id"]
        if doc_id not in graph.entities:
            graph.add(
                {
                    "@id": doc_id,
                    "@type": "CreativeWork",
                    "name": text(test["label"]),
                    "url": doc_path + ("#" + fragment if fragment else ""),
                    "isPartOf": ref(doc_path),
                    "license": ref(LICENSES["CC-BY-4.0"][0]),
                }
            )
        entry_id = "#entry-localtest-" + test["id"]
        graph.add({"@id": entry_id, "@type": "PropertyValue", "propertyID": "entryPoint", "value": test["entryPoint"]})
        test_id = "#test-" + test["id"]
        test_ids.append(test_id)
        graph.add(
            {
                "@id": test_id,
                "@type": "CreativeWork",
                "additionalType": FTR_TEST,
                "identifier": test["id"],
                "name": text(test["label"]),
                "description": text(test["description"]),
                "url": test["script"],
                "isImplementationOf": ref(question_id),
                "about": question.get("about"),
                "citation": question.get("citation"),
                "hasPart": refs(files),
                "subjectOf": ref(doc_id),
                "additionalProperty": refs([entry_id]),
            },
            f"test:{test['id']}",
        )
    # The curated tests as a whole, which a station's action can point to.
    graph.add(
        {
            "@id": "#tests",
            "@type": "CreativeWork",
            "name": text({"cs": "Automatizované testy", "en": "Automated tests"}),
            "hasPart": refs(test_ids),
        }
    )
    return test_ids


def criterion_id(provider: str, metric: str) -> str:
    """The crate entity of an external evaluator's native criterion; the native ID is kept verbatim."""
    return f"#criterion-{provider}-{metric}"


def build_providers(graph: Graph, live: dict[str, Any]) -> list[str]:
    """External evaluators' native criteria and the reviewed associations of each with guide questions.

    A criterion keeps the provider's own name and identifier and adds the guide's reading as `alternateName`. A
    mapping records the coverage it was reviewed for and the provider versions it was reviewed against; it is a
    statement about the criterion, never a criterion the guide invents. Unmapped criteria stay listed."""
    criteria = []
    for provider in live.get("provider", []):
        reviewed = [
            ", ".join(f"{key} {value}" for key, value in entry.items()) for entry in provider.get("reviewed", [])
        ]
        documentation = [provider[key] for key in ("documentation", "terms") if provider.get(key)]
        for metric in provider.get("metric", []):
            native = alternate_id(metric, provider["id"])
            entity_id = criterion_id(provider["id"], metric["id"])
            mappings = [mapping for mapping in provider.get("mapping", []) if mapping["metric"] == native]
            mapping_ids = []
            for mapping in mappings:
                mapping_id = f"#mapping-{provider['id']}-{metric['id']}-{mapping['question']}"
                mapping_ids.append(mapping_id)
                graph.add(
                    {
                        "@id": mapping_id,
                        "@type": "CreativeWork",
                        "name": f"{provider['name']} {metric['id']} → {mapping['question']}",
                        "about": ref("#item-" + mapping["question"]),
                        "isBasedOn": ref(entity_id),
                        "mappingCoverage": mapping["coverage"],
                        "reviewedVersion": reviewed,
                        "description": text(mapping.get("note")),
                        "dateModified": iso(provider["observed"]) if provider.get("observed") else None,
                    }
                )
            invocation = None
            if provider.get("connector") and provider.get("path"):
                connector = next((c for c in live.get("connector", []) if c["id"] == provider["connector"]), None)
                if connector is None:
                    raise ContentError(f"provider:{provider['id']}: unknown connector {provider['connector']}")
                invocation = connector["origin"] + "/" + provider["path"].split("?", 1)[0].replace("{metric}", native)
            criteria.append(entity_id)
            graph.add(
                {
                    "@id": entity_id,
                    "@type": "CreativeWork",
                    "additionalType": FTR_TEST,
                    "identifier": metric["id"],
                    "name": {"@language": "en", "@value": metric["name"]},
                    "alternateName": text(metric.get("label")),
                    "about": ref(principle_iri(metric["principle"])),
                    "isPartOf": ref(f"#resource-{provider['resource']}"),
                    "url": invocation or provider.get("form"),
                    "subjectOf": refs(documentation),
                    "reviewedVersion": reviewed,
                    "hasPart": refs(mapping_ids),
                },
                f"provider:{provider['id']}.{metric['id']}",
            )
    return criteria


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
            action_id = f"{section_id}-action" if section.get("action") else None
            graph.add(
                {
                    "@id": section_id,
                    "@type": "CreativeWork",
                    "identifier": section.get("id"),
                    "headline": text(section.get("heading")),
                    "text": text(section["body"]),
                    "position": number,
                    "isPartOf": ref(page_id),
                    "potentialAction": ref(action_id) if action_id else None,
                }
            )
            if action_id:
                action = section["action"]
                graph.add(
                    {"@id": action_id, "@type": "Action", "name": text(action["label"]), "target": ref(action["href"])}
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


def build_model(graph: Graph, data: dict[str, Any]) -> list[str]:
    """Build the shared conceptual model and only the explicitly authored associations.

    Definitions never carry implementation status. Dated observations are separate example records, so a
    connection tag cannot silently turn a manuscript observation into a current service claim.
    """
    if not data:
        return []
    model = data["model"]
    seam_layers = {item["id"]: item["layers"] for item in data.get("seam", [])}
    model_id = "#implementation-model"
    source = refs(graph.resolve([model["source"]]))
    parts = []
    for kind in ("layer", "seam"):
        for position, item in enumerate(data.get(kind, []), 1):
            entity_id = f"#{kind}-{item['id']}"
            parts.append(entity_id)
            entity = {
                "@id": entity_id,
                "@type": "DefinedTerm",
                "identifier": f"{kind}.{item['id']}",
                "termCode": f"{kind}.{item['id']}",
                "modelKind": kind,
                "position": position,
                "name": text(item["name"]),
                "description": text(item["description"]),
                "inDefinedTermSet": ref(model_id),
                "citation": refs(graph.resolve([item.get("source", model["source"])])),
            }
            if kind == "seam":
                entity |= {
                    key: text(item[key]) for key in ("transfer", "sender", "recipient", "carrier", "maintainers")
                }
                entity["implementationLayers"] = refs([f"#layer-{key}" for key in item["layers"]])
            graph.add(entity, f"{kind}.{item['id']}")
    terms = list(parts)
    for item in data.get("example", []):
        entity_id = f"#model-example-{item['id']}"
        parts.append(entity_id)
        seam_id = f"#seam-{item['seam']}"
        graph.add(
            {
                "@id": entity_id,
                "@type": "CreativeWork",
                "identifier": f"example.{item['id']}",
                "modelKind": "example",
                "name": text(item["name"]),
                "description": text(item["description"]),
                "scope": text(item["scope"]),
                "isPartOf": ref(seam_id),
                "implementationSeams": ref(seam_id),
                "serviceStatus": ref(f"#status-{item['status']}"),
                "statusAsOf": iso(item["asOf"]),
                "citation": refs(graph.resolve(item["evidence"])),
            },
            f"example.{item['id']}",
        )
        append_ref(graph.entities[seam_id], "hasPart", entity_id)
    for item in data.get("context", []):
        entity_id = f"#model-context-{item['station']}-{item['lens']}"
        parts.append(entity_id)
        graph.add(
            {
                "@id": entity_id,
                "@type": "CreativeWork",
                "identifier": f"context.{item['station']}.{item['lens']}",
                "text": text(item["text"]),
                "isPartOf": ref(f"#station-{item['station']}"),
                "audience": ref(f"#lens-{item['lens']}"),
                "implementationSeams": refs([f"#seam-{key}" for key in item["seams"]]),
                "implementationLayers": refs(
                    [
                        f"#layer-{key}"
                        for key in dict.fromkeys(layer for seam in item["seams"] for layer in seam_layers[seam])
                    ]
                ),
                "citation": source,
            },
            f"context:{item['station']}:{item['lens']}",
        )
        append_ref(graph.entities[f"#station-{item['station']}"], "hasPart", entity_id)
    if model.get("workedExample"):
        worked = model["workedExample"]
        parts.append("#model-worked-example")
        graph.add(
            {
                "@id": "#model-worked-example",
                "@type": "CreativeWork",
                "identifier": "model-worked-example",
                "name": text(worked["name"]),
                "description": text(worked["description"]),
                # Finalised after provenance actions exist: the last step may be a recorded revision.
                "isPartOf": ref(model_id),
                "exampleOfWork": ref(model_id),
            },
            "model:worked-example",
        )
    graph.add(
        {
            "@id": model_id,
            "@type": "DefinedTermSet",
            "identifier": model["id"],
            "name": text(model["name"]),
            "description": text(model["description"]),
            **{key: text(model[key]) for key in ("introduction", "ordering", "feedback")},
            "citation": source,
            "hasPart": refs(parts),
            "hasDefinedTerm": refs(terms),
            "workExample": ref("#model-worked-example") if model.get("workedExample") else None,
        },
        f"model:{model['id']}",
    )
    for association in data.get("association", []):
        target = association["target"]
        entity_ids = graph.index.get(target)
        if not entity_ids:
            raise ContentError(f"model association names an unknown content ID '{target}'")
        for entity_id in entity_ids:
            for field, prefix, output in (
                ("layers", "layer", "implementationLayers"),
                ("seams", "seam", "implementationSeams"),
            ):
                keys = association.get(field, [])
                if field == "layers":
                    keys = list(
                        dict.fromkeys(
                            keys + [layer for seam in association.get("seams", []) for layer in seam_layers[seam]]
                        )
                    )
                for key in keys:
                    append_ref(graph.entities[entity_id], output, f"#{prefix}-{key}")
    return [model_id]


# The life-cycle model whose stages the path follows (D-162): a station's `lifecycleStage` names one of its stages.
PATH_LIFECYCLE = "rdmkit"


def lifecycle_stage_id(model: str, stage: str) -> str:
    return f"#lifecycle-{model}.{stage}"


def build_lifecycles(
    graph: Graph, lifecycles: list[dict[str, Any]], crosswalk: list[dict[str, Any]], sources: list[dict[str, Any]]
) -> list[str]:
    """The research data life-cycle models as term sets of their stages, each stage with its name and definition as
    published, its sources and their licences; and the crosswalk, one record per correspondence between two stages
    with its basis: published by a source, reviewed by the guide, or unconfirmed."""
    licences = {source["id"]: source.get("license") for source in sources}
    languages = {source["id"]: source.get("inLanguage", "en") for source in sources}
    names: dict[str, dict[str, str]] = {}
    ids = []
    for data in lifecycles:
        model = data["lifecycle"]
        set_id = f"#lifecycle-{model['id']}"
        cited = [model["source"]] + as_list(model.get("czechSource"))
        language = languages.get(model["source"], "en")
        stage_ids = []
        for position, stage in enumerate(data.get("stage", []), 1):
            key = f"{model['id']}.{stage['id']}"
            names[key] = stage["name"]
            # The definition is quoted in its source's language; a path stage adds the Průvodce's Czech translation,
            # marked, so that both languages say the same, and the Czech source's own definition as a quotation.
            definition = [{"@value": stage["definition"], "@language": language}]
            if stage.get("translation"):
                definition.append({"@value": stage["translation"], "@language": "cs"})
            stage_ids.append(
                graph.add(
                    {
                        "@id": lifecycle_stage_id(model["id"], stage["id"]),
                        "@type": "DefinedTerm",
                        "identifier": stage["id"],
                        "termCode": stage["id"],
                        "position": position,
                        "name": text(stage["name"]),
                        "description": definition,
                        "nameTranslation": as_list(stage.get("translated")),
                        "descriptionTranslation": ["cs"] if stage.get("translation") else None,
                        "quotedDefinition": {"@value": stage["czechDefinition"], "@language": "cs"}
                        if stage.get("czechDefinition")
                        else None,
                        "note": {"@value": stage["note"], "@language": language} if stage.get("note") else None,
                        "inDefinedTermSet": ref(set_id),
                        "citation": refs(graph.resolve(cited)),
                        "license": list(dict.fromkeys(licences[source] for source in cited if licences.get(source))),
                    },
                    key,
                )
            )
        ids.append(
            graph.add(
                {
                    "@id": set_id,
                    "@type": "DefinedTermSet",
                    "identifier": model["id"],
                    "name": text(model["name"]),
                    "url": model.get("url"),
                    "position": model["position"],
                    "citation": refs(graph.resolve(cited)),
                    "hasDefinedTerm": refs(stage_ids),
                },
                f"lifecycle:{model['id']}",
            )
        )
    correspondence_ids = []
    for item in crosswalk:
        keys = item["stages"]
        if any(key not in names for key in keys):
            raise ContentError(f"a crosswalk correspondence names an unknown stage: {', '.join(keys)}")
        key = item["id"]
        correspondence_ids.append(
            graph.add(
                {
                    "@id": f"#crosswalk-{key}",
                    "@type": "CreativeWork",
                    "identifier": key,
                    "name": text({lang: " ↔ ".join(names[stage][lang] for stage in keys) for lang in LANGS}),
                    "about": refs([lifecycle_stage_id(*stage.split(".", 1)) for stage in keys]),
                    "mappingBasis": item["basis"],
                    "citation": refs(graph.resolve([item["source"]])) if item.get("source") else None,
                    "description": text(item.get("note")),
                    "isPartOf": ref("#lifecycle-crosswalk"),
                },
                f"crosswalk:{key}",
            )
        )
    if correspondence_ids:
        ids.append(
            graph.add(
                {
                    "@id": "#lifecycle-crosswalk",
                    "@type": "CreativeWork",
                    "identifier": "crosswalk",
                    "name": "Crosswalk between research data life-cycle models",
                    "hasPart": refs(correspondence_ids),
                },
                "lifecycle:crosswalk",
            )
        )
    return ids


def build_crate(content: dict[str, Any], graph: Graph | None = None) -> dict[str, Any]:
    """The crate for the content; a caller that passes a graph can inspect it afterwards (the content checks read
    which entities each content ID names)."""
    try:
        for row in catalogue_records(content).values():
            validate_identity(row)
        for snapshot in content["snapshots"]:
            for kind in ("tool", "resource", "repository", "organization", "fip", "record"):
                if kind == "record" and snapshot.get("snapshot", {}).get("source") != "NKR":
                    continue
                for row in snapshot.get(kind, []):
                    validate_identity(row, source_scheme(snapshot, kind))
        for row in content.get("glossary", {}).get("term", []):
            validate_identity(row, "heslar")
        for row in content.get("live", {}).get("champion", {}).get("test", []):
            validate_identity(row, "fair-champion")
        for provider in content.get("live", {}).get("provider", []):
            for row in provider.get("metric", []):
                validate_identity(row, provider["id"])
    except ValueError as error:
        raise ContentError(str(error)) from error
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
    graph.add({"@id": "./", "@type": "Dataset"}, "guide")  # completed below, after its parts exist
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
    crosswalk = type_crosswalk(guide_file)
    source_ids = build_sources(graph, content["sources"], organizations, people, names, crosswalk=crosswalk)
    build_vocabularies(graph, guide_file)
    build_glossary(graph, content["glossary"], content["ledger"])
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
    lifecycle_ids = build_lifecycles(
        graph, content.get("lifecycles", []), content.get("crosswalk", []), content["sources"]
    )
    build_stations(graph, content["stations"], all_lenses)
    if f"#lifecycle-{PATH_LIFECYCLE}" in graph.entities:
        graph.entities["#path"]["isBasedOn"] = ref(f"#lifecycle-{PATH_LIFECYCLE}")
    link_resources(graph, content["resources"])
    check_ids = build_checks(graph, content["checks"], content["live"].get("links", {}))
    snapshot_ids = build_snapshots(graph, content["snapshots"])
    catalogue_ids = build_fip_dashboard(graph, content["snapshots"], crosswalk)
    build_repositories(
        graph, content["repositories"], content["snapshots"], content["resources"], content.get("repository_records")
    )
    infrastructure_ids = build_infrastructures(graph, content.get("infrastructures") or {})
    node_ids = build_node(graph, content.get("node") or {})
    knav_ids = build_knav_tools(graph, content)
    callout_ids = build_callouts(graph, content["callouts"], all_lenses)
    test_ids = build_tests(graph, content["live"])
    build_providers(graph, content["live"])
    page_ids = build_pages(graph, content["pages"])
    model_ids = build_model(graph, content.get("model", {}))
    action_ids = build_actions(graph, content["provenance"], people)
    if content.get("model", {}).get("model", {}).get("workedExample"):
        worked = content["model"]["model"]["workedExample"]
        graph.entities["#model-worked-example"]["hasPart"] = refs(graph.resolve(worked["steps"]))

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

    software_id = "#guide-software"
    graph.add(
        {
            "@id": "#guide-source",
            "@type": "CreativeWork",
            "additionalType": "http://schema.org/SoftwareSourceCode",
            "name": "FAIR Data Guide source code",
            "codeRepository": guide.get("url"),
            "version": guide["version"],
            "programmingLanguage": ["JavaScript", "Python", "HTML", "CSS"],
            "softwareRequirements": [
                guide.get("url", "").rstrip("/") + "/blob/HEAD/pyproject.toml",
                guide.get("url", "").rstrip("/") + "/blob/HEAD/package-lock.json",
                guide.get("url", "").rstrip("/") + "/blob/HEAD/requirements-dev.txt",
            ],
            "citation": guide.get("url", "").rstrip("/") + "/blob/HEAD/CITATION.cff",
            "license": ref(LICENSES["MIT"][0]),
            "author": refs([people[person] for person in guide.get("editors", [])]),
            "isPartOf": ref(software_id),
        }
    )
    graph.add(
        {
            "@id": software_id,
            "@type": "SoftwareApplication",
            "name": text(guide["name"]),
            "description": "The guide software; its content knowledge base is a separately described dataset.",
            "softwareVersion": guide["version"],
            "version": guide["version"],
            "creativeWorkStatus": build_identity_facts()["status"],
            "url": guide.get("url"),
            "license": ref(LICENSES["MIT"][0]),
            "author": refs([people[person] for person in guide.get("editors", [])]),
            "runtimePlatform": (
                "Web browser; Python 3.11 or later and the pinned Node.js packages for the build; "
                "Node.js for development checks"
            ),
            "softwareHelp": guide.get("url", "").rstrip("/") + "/blob/HEAD/README_en.md",
            "hasPart": refs(["#guide-source", "./"]),
            "subjectOf": ref("./"),
        }
    )
    for field in ("publisher", "funder"):
        if guide.get(field) and guide[field] not in organizations:
            raise ContentError(f"guide: unknown {field} organisation '{guide[field]}'")
    root = {
        "@id": "./",
        "@type": "Dataset",
        "name": text(guide["name"]),
        "description": text(guide["description"]),
        "version": guide["version"],
        "creativeWorkStatus": build_identity_facts()["status"],
        "disambiguatingDescription": text(guide.get("testingNotice"))
        if build_identity_facts()["status"] == "testing"
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
        "isPartOf": ref(software_id),
        "about": refs([principle_iri(principle["id"]) for principle in content["principles"]]),
        "hasPart": refs(
            [entity_id for entity_id, entity in graph.entities.items() if "File" in as_list(entity.get("@type"))]
        ),
        "mentions": refs(
            action_ids
            + ["#ledger", "#sources", "#resources", "#repositories"]
            + catalogue_ids
            + knav_ids
            + snapshot_ids
            + check_ids
            + callout_ids
            + test_ids
            + page_ids
            + model_ids
            + lifecycle_ids
            + infrastructure_ids[:1]
            + node_ids[:1]
        ),
    }
    graph.entities["./"] = prune(root)
    for entity_id, row in catalogue_records(content).items():
        if not isinstance(row.get("id"), str) or not row["id"]:
            raise ContentError(f"{entity_id}: record requires one non-empty primary id")
        if entity_id not in graph.entities:
            continue
        entity = graph.entities[entity_id]
        if row.get("id"):
            entity["identifier"] = row["id"]
        if row.get("alternateIds"):
            identifiers = []
            for item in row["alternateIds"]:
                alternate_entity = "#alternate-" + entity_id.lstrip("#") + "-" + slug(item["scheme"])
                identifiers.append(
                    graph.add(
                        {
                            "@id": alternate_entity,
                            "@type": "PropertyValue",
                            "propertyID": item["scheme"],
                            "value": item["value"],
                        }
                    )
                )
            entity["alternateIdentifier"] = refs(identifiers)
        # A DataCite repository ID is one genuine source identifier like any other: it becomes a typed value under
        # the one identifier property rather than a separate field (design: *one identifier property, typed by its
        # scheme*). The scheme keeps it distinct from the record's other source identifiers.
        if isinstance(entity.get("dataciteRepository"), str) and entity["dataciteRepository"]:
            if "datacite" not in {item["scheme"] for item in row.get("alternateIds", [])}:
                datacite_entity = "#alternate-" + entity_id.lstrip("#") + "-datacite"
                graph.add(
                    {
                        "@id": datacite_entity,
                        "@type": "PropertyValue",
                        "propertyID": "datacite",
                        "value": entity["dataciteRepository"],
                    }
                )
                append_ref(entity, "alternateIdentifier", datacite_entity)
            entity.pop("dataciteRepository", None)
    # An agent (an operating, hosting or developing organisation) is named by reference to an entity, not by a
    # literal name: one way to name an agent and its source (design: group 21).
    for entity in list(graph.entities.values()):
        for name_key, agent_key in (
            ("operatorName", "publisher"),
            ("developerName", "attributedTo"),
            ("hostingInstitution", "publisher"),
        ):
            name = name_text(entity.get(name_key))
            if name:
                append_ref(entity, agent_key, agent_ref(graph, name))
            entity.pop(name_key, None)
    link_texts(graph, reference_targets(content, graph))
    for entity_id, address in catalogue_addresses(graph.entities, content).items():
        graph.entities[entity_id]["catalogueAddress"] = address

    context: dict[str, Any] = {
        term: ESTABLISHED_TERMS.get(term, vocabulary_base + term) for term in [*ESTABLISHED_TERMS, *GUIDE_TERMS]
    }
    context["isImplementationOf"] = "https://semanticscience.org/resource/SIO_000233"
    context["skos:Concept"] = SKOS + "Concept"
    context["skos:ConceptScheme"] = SKOS + "ConceptScheme"
    context["skos:inScheme"] = {"@id": SKOS + "inScheme", "@type": "@id"}
    context["publisher"] = DCTERMS + "publisher"
    context["attributedTo"] = PROV + "wasAttributedTo"
    return {"@context": [f"{RO_CRATE}/context", context], "@graph": list(graph.entities.values())}


# ---------------------------------------------------------------------------
# Page blocks


API_COLLECTIONS = (
    "principles",
    "stations",
    "checks",
    "metrics",
    "tests",
    "resources",
    "sources",
    "repositories",
    "clauses",
    "terms",
    "organizations",
    "fips",
    "changes",
    "model",
    "lifecycle",
    "infrastructures",
)
API_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# Where the API's own files sit in the site; records are `api/<collection>/<record ID>.json`.
API_FILES = {
    "health": "api/health.json",
    "description": "openapi.json",
    "docs": "api/",
    "context": "api/context.jsonld",
    "meta": "api/meta.json",
    "record": "api/{record}.json",  # a list (`principles`) or a canonical record (`pr/R1.1`)
}
API_FILES["test"] = API_FILES["record"].replace(
    "{record}", "tests/{id}"
)  # a question's manual test, which results name
API_PREFIXES = {
    "#station-": "stations",
    "#check-": "checks",
    "#test-": "tests",
    "#criterion-": "tests",
    "#repository-": "repositories",
    "#clause-": "clauses",
    "#action-": "changes",
    "#layer-": "model",
    "#seam-": "model",
    "#model-example-": "model",
    "#lifecycle-": "lifecycle",
    "#crosswalk-": "lifecycle",
    "#infrastructure-": "infrastructures",
}


def api_records(entities: dict[str, dict[str, Any]], content: dict[str, Any]) -> dict[str, list[tuple[str, str]]]:
    """What the static API publishes: per collection, each record's ID and the entity it describes, in the crate's
    order. A record ID names a file, so it is unique within its collection and safe as a path segment. A FIP
    Dashboard resource that a curated resource stands for is published as that resource; the manual tests of the
    check questions are added by the API build."""

    def part_ids(whole: str) -> set[str]:
        return {part["@id"] for part in as_list(entities.get(whole, {}).get("hasPart"))}

    organizations = {
        f"#org-{organization['id']}": organization["id"] for organization in content["guide"].get("organization", [])
    }
    described = {
        target["@id"]
        for entity_id, entity in entities.items()
        if entity_id.startswith(("#resource-", "#repository-"))
        for target in as_list(entity.get("sameAs"))
        if isinstance(target, dict)
    }
    linked_fers = {
        "#fer-" + row["id"]
        for snapshot in content.get("snapshots", [])
        for row in snapshot.get("resource", [])
        if alternate_id(row, "fip-dashboard") and FIP_DASHBOARD + alternate_id(row, "fip-dashboard") in described
    }
    fers = part_ids("#fers") - linked_fers
    sources = part_ids("#sources")
    records: dict[str, list[tuple[str, str]]] = {name: [] for name in API_COLLECTIONS}
    for entity_id, entity in entities.items():
        collection = next((name for prefix, name in API_PREFIXES.items() if entity_id.startswith(prefix)), None)
        record = entity.get("identifier")
        if collection == "repositories" and entity.get("@type") != "DataCatalog":
            continue  # the repository kinds, a term set
        if collection in ("repositories", "changes"):
            record = entity_id.split("-", 1)[1]
        elif collection == "lifecycle":
            record = entity_id.removeprefix("#lifecycle-").removeprefix("#crosswalk-")
        elif entity_id.startswith("#criterion-"):
            # An external criterion is published under its provider's resource ID and its own native identifier.
            resource = as_list(entity.get("isPartOf"))[0]["@id"].removeprefix("#resource-")
            record = f"{resource}.{entity.get('identifier')}"
        elif collection is not None:
            pass
        elif entity_id.startswith("#principle-") and entity.get("termCode"):
            collection, record = "principles", entity["termCode"]
        elif entity_id.startswith("#item-") and entity.get("@type") == "Question":
            collection = "metrics"
        elif (entity_id.startswith("#resource-") and entity.get("resourceType")) or entity_id in fers:
            collection = "resources"
        elif entity_id in sources:
            collection = "sources"
        elif entity_id.startswith("#term-") and entity.get("inDefinedTermSet") == ref("#glossary"):
            collection, record = "terms", entity_id.removeprefix("#term-")
        elif entity_id in organizations:
            collection, record = "organizations", organizations[entity_id]
        elif FIP_TERMS + "FAIR-Implementation-Profile" in as_list(entity.get("additionalType")):
            collection = "fips"
        elif entity_id.startswith("#knav-") and entity_id != "#knav-tools" and not entity.get("sameAs"):
            # A catalogue tool no entry of the guide stands for, under the catalogue's identifier for it.
            collection, record = "resources", f"knav.{entity['identifier']}"
        if entity_id == "#implementation-model":
            collection, record = "model", entity["identifier"]
        if entity_id == "#eosc-cz-node":
            # The EOSC CZ Node is an organisation of its own, beside the curated ones (D-172).
            collection, record = "organizations", entity["identifier"]
        if collection is None:
            continue
        if not isinstance(record, str) or not API_ID.match(record):
            raise ContentError(f"{entity_id}: no record ID the API can publish under {collection}/ ({record!r})")
        if any(existing == record for existing, _ in records[collection]):
            raise ContentError(f"{entity_id}: two entities share the API record {collection}/{record}")
        records[collection].append((record, entity_id))
    return records


def api_paths(records: dict[str, list[tuple[str, str]]]) -> dict[str, str]:
    """Each published entity's record, as `<collection>/<record ID>` under the API's directory."""
    return {entity_id: f"{name}/{record}" for name, members in records.items() for record, entity_id in members}


def catalogue_records(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The owning source row for a published entity; id is primary and alternateIds identify real source records."""
    result = {}
    if content.get("model", {}).get("model"):
        result["#implementation-model"] = content["model"]["model"]
    for kind in ("layer", "seam", "example"):
        prefix = "#model-example-" if kind == "example" else "#" + kind + "-"
        result.update((prefix + row["id"], row) for row in content.get("model", {}).get(kind, []))
    for data in content.get("lifecycles", []):
        result["#lifecycle-" + data["lifecycle"]["id"]] = data["lifecycle"]
        for row in data.get("stage", []):
            result[lifecycle_stage_id(data["lifecycle"]["id"], row["id"])] = row
    for row in content.get("crosswalk", []):
        result["#crosswalk-" + row["id"]] = row
    for section, prefix in (
        ("resources", "#resource-"),
        ("sources", "#source-"),
        ("repositories", "#repository-"),
        ("principles", "#principle-"),
        ("ledger", "#clause-"),
        ("provenance", "#action-"),
    ):
        result.update((prefix + row["id"], row) for row in content.get(section, []))
    for parent in content["stations"]:
        row = parent["station"]
        result["#station-" + row["id"]] = row
    for parent in content["checks"]:
        row = parent["check"]
        result["#check-" + row["id"]] = row
        result.update(("#item-" + row["id"], row) for row in parent.get("item", []))
    for row in content["guide"].get("organization", []):
        result["#org-" + row["id"]] = row
    for row in content.get("infrastructures", {}).get("infrastructure", []):
        result["#infrastructure-" + row["id"]] = row
    for row in content.get("live", {}).get("test", []):
        result["#test-" + row["id"]] = row
    for row in content.get("live", {}).get("champion", {}).get("test", []):
        result["#test-" + row["id"]] = row
    for provider in content.get("live", {}).get("provider", []):
        for row in provider.get("metric", []):
            result[criterion_id(provider["id"], row["id"])] = row
    for row in content.get("glossary", {}).get("term", []):
        result["#term-" + str(row["id"])] = row
    for snapshot in content["snapshots"]:
        for key, prefix in (
            ("repository", "#repository-"),
            ("tool", "#knav-"),
            ("resource", "#fer-"),
            ("organization", "#fd-org-"),
            ("fip", "#fip-"),
        ):
            result.update((prefix + str(row["id"]), row) for row in snapshot.get(key, []))
        if snapshot.get("snapshot", {}).get("source") == "NKR":
            result.update(("#repository-" + str(row["id"]), row) for row in snapshot.get("record", []))
    return result


def catalogue_addresses(entities: dict[str, dict[str, Any]], content: dict[str, Any]) -> dict[str, str]:
    """Project stored Guide IDs and frozen prefixes once; external identities never issue a published address."""
    records = catalogue_records(content)
    repositories = {item["@id"] for item in as_list(entities.get("#repositories", {}).get("hasPart"))}
    result: dict[str, str] = {}
    for entity_id, old in api_paths(api_records(entities, content)).items():
        entity = entities[entity_id]
        collection, identifier = old.split("/", 1)
        kind = {"sources": "resources", "metrics": "questions", "changes": "actions"}.get(collection, collection)
        subtype = ""
        if entity_id in repositories:
            kind = "repositories"
            subtype = (entity.get("repositoryKind") or {}).get("@id", "").removeprefix("#rkind-")
            if not subtype and entity.get("resourceType") == ref("#rtype-registry"):
                subtype = "registry"
        elif kind == "resources":
            subtype = (
                (entity.get("resourceType") or entity.get("guideType") or {})
                .get("@id", "#rtype-tool")
                .removeprefix("#rtype-")
            )
        elif kind == "infrastructures":
            subtype = (entity.get("researchField") or {}).get("@id", "").removeprefix("#rifield-")
        elif kind == "tests":
            subtype = "guide" if entity_id.startswith("#test-guide-") else "fair-champion"
            if entity_id.startswith("#criterion-"):
                subtype = as_list(entity.get("isPartOf"))[0]["@id"].removeprefix("#resource-")
                identifier = str(entity["identifier"])
        row = records.get(entity_id, {})
        if "guideId" in row:
            raise ContentError(f"{entity_id}: obsolete guideId field; id is the one primary value")
        identifier = str(row.get("id") or identifier)
        if has_particles(identifier):
            raise ContentError(
                f"{entity_id}: Guide slug contains a particle; use an official abbreviation or source URL words"
            )
        prefix = row.get("guideRoute") or "/".join(filter(None, (KIND_CODES[kind], TYPE_CODES.get(subtype, subtype))))
        if prefix.split("/")[0] not in KIND_CODES.values() or len(prefix.split("/")) > 2:
            raise ContentError(f"{entity_id}: invalid Guide route prefix {prefix}")
        address = prefix + "/" + identifier
        if not all(SAFE_ID.fullmatch(part) for part in address.split("/")) or len(identifier) > MAX_ID:
            raise ContentError(
                f"{entity_id}: invalid or overlong Guide identifier {identifier}; assign a short primary id"
            )
        if address in result.values():
            raise ContentError(f"{entity_id}: two entries share Guide address {address}; review their identities")
        result[entity_id] = address
    return result


LINKSET_FILE = "linkset.json"
# What the build generates and the repository must not hold; the API's records and its description as well.
GENERATED = (
    CRATE_FILE,
    PREVIEW_FILE,
    KB_SCRIPT,
    UI_SCRIPT,
    *PART_SCRIPTS.values(),
    *LANGUAGE_SCRIPTS.values(),
    *(path for paths in PART_LANGUAGE_SCRIPTS.values() for path in paths.values()),
    LINKSET_FILE,
    API_FILES["description"],
)


def is_generated(path: str) -> bool:
    """Whether a repository path is build output: a generated file, or a JSON file of the API."""
    return (
        path in GENERATED
        or (path.startswith("api/") and path.endswith((".json", ".jsonld")))
        or bool(PROFILE_PAGE.match(path))
    )


# ---------------------------------------------------------------------------
# Where the build writes

DEFAULT_SITE = "_site"
# The file a build leaves in the site directory, so that only a directory the build made is ever replaced.
SITE_MARKER = ".fair-guide-site"
# Top-level trees the repository authors, the build reads or the environment keeps; a site directory never lies in
# one of them. tests/test_scripts.py requires every tracked top-level directory to be named here.
PROTECTED_TREES = frozenset(
    {
        ".agents",
        ".claude",
        ".codex",
        ".cursor",
        ".devcontainer",
        ".gemini",
        ".git",
        ".github",
        ".kilo",
        ".venv",
        "LICENSES",
        "api",
        "assets",
        "content",
        "diagrams",
        "docker",
        "docs",
        "node_modules",
        "openspec",
        "profile",
        "scripts",
        "tests",
    }
)


class UnsafeOutputError(ContentError):
    """A requested output directory could replace or change files the build did not write."""


def site_directory(out: Path, root: Path | None = None) -> Path:
    """The resolved site directory the build may replace; refuses before anything is changed.

    The directory lies inside the repository and is not the repository, reaches it through no link or junction, does
    not lie in a protected tree, and, when it exists, is a directory the build made (it holds ``SITE_MARKER``), an
    empty directory or the repository's default ``_site/``, never one holding a checkout.
    """
    root = ROOT if root is None else root
    lexical_root = Path(os.path.abspath(root))
    lexical = Path(os.path.abspath(out))
    try:
        relative = lexical.relative_to(lexical_root)
    except ValueError:
        raise UnsafeOutputError(f"the site directory must lie inside the repository, not {lexical}") from None
    if not relative.parts:
        raise UnsafeOutputError(f"the site directory must be a directory of its own, not the repository {lexical}")
    real_root = os.path.normcase(os.path.realpath(lexical_root))
    real = Path(os.path.realpath(lexical))
    if os.path.normcase(real) != os.path.normcase(os.path.join(real_root, *relative.parts)):
        raise UnsafeOutputError(f"the site directory {relative.as_posix()} passes through a link or junction to {real}")
    protected = {os.path.normcase(name) for name in PROTECTED_TREES}
    if os.path.normcase(relative.parts[0]) in protected:
        raise UnsafeOutputError(
            f"the site directory {relative.as_posix()} lies in the authored tree {relative.parts[0]}/"
        )
    if real.exists():
        if not real.is_dir():
            raise UnsafeOutputError(f"the site directory {relative.as_posix()} exists and is not a directory")
        if (real / ".git").exists():
            raise UnsafeOutputError(f"the site directory {relative.as_posix()} holds a checkout")
        legacy = relative.parts == (DEFAULT_SITE,)
        if not ((real / SITE_MARKER).is_file() or legacy or not any(real.iterdir())):
            raise UnsafeOutputError(
                f"the site directory {relative.as_posix()} holds files the build did not write; remove them first"
            )
    return real


def mark_site(site: Path) -> None:
    """Record that the build made this directory."""
    (site / SITE_MARKER).write_text(
        "Written by the FAIR guide's build, which replaces this directory as a whole.\n", encoding="utf-8", newline="\n"
    )


def replace_site(out: Path, root: Path | None = None) -> Path:
    """Empty a checked site directory for a fresh build and mark it; return its resolved path."""
    site = site_directory(out, root)
    if site.exists():
        shutil.rmtree(site)
    site.mkdir(parents=True)
    mark_site(site)
    return site


def claim_site(out: Path, root: Path | None = None) -> Path:
    """Create or adopt a checked site directory without emptying it, for a build of one of its parts."""
    site = site_directory(out, root)
    site.mkdir(parents=True, exist_ok=True)
    if not (site / SITE_MARKER).is_file():
        mark_site(site)
    return site


def require_site(site: Path) -> Path:
    """A directory the build made, before a part of it is replaced or changed; refuses any other directory."""
    resolved = Path(os.path.realpath(site))
    if site.is_symlink() or not (resolved / SITE_MARKER).is_file():
        raise UnsafeOutputError(f"{site} is not a site directory the build made")
    return resolved


SCHEMA_ORG_TYPES = ("https://schema.org/AboutPage", "https://schema.org/Dataset")


def signposts(content: dict[str, Any], crate: dict[str, Any]) -> list[dict[str, str]]:
    """The guide's FAIR Signposting links: what the page head carries and the linkset lists, each relative to the
    site except identifiers outside it. The page presents the knowledge base, a dataset, and is its landing page."""
    guide = content["guide"]["guide"]
    root = next(entity for entity in crate["@graph"] if entity["@id"] == "./")
    links = [
        {"rel": "describedby", "href": CRATE_FILE, "type": "application/ld+json", "profile": RO_CRATE},
        {
            "rel": "service-desc",
            "href": API_FILES["description"],
            "type": "application/vnd.oai.openapi+json;version=3.1",
        },
        {"rel": "service-doc", "href": API_FILES["docs"], "type": "text/html"},
        {"rel": "license", "href": root["license"]["@id"]},
        *({"rel": "type", "href": iri} for iri in SCHEMA_ORG_TYPES),
        *({"rel": "author", "href": editor["@id"]} for editor in as_list(root.get("editor")) if "://" in editor["@id"]),
    ]
    if guide.get("doi"):
        links.append({"rel": "cite-as", "href": f"https://doi.org/{guide['doi']}"})
    return links + [{"rel": "linkset", "href": LINKSET_FILE, "type": "application/linkset+json"}]


def linkset(links: list[dict[str, str]]) -> dict[str, Any]:
    """The signposts as a linkset (RFC 9264) anchored at the site, which it names relatively, so the guide can move."""
    targets: dict[str, list[dict[str, str]]] = {}
    for link in links:
        if link["rel"] != "linkset":
            targets.setdefault(link["rel"], []).append({key: value for key, value in link.items() if key != "rel"})
    return {"linkset": [{"anchor": "./", **targets}]}


def link_elements(links: list[dict[str, str]]) -> str:
    """The signposts as link elements for the page head; HTML has no profile attribute, the linkset carries it."""

    def element(link: dict[str, str]) -> str:
        attributes = " ".join(
            f'{key}="{html.escape(str(link[key]), quote=True)}"' for key in ("rel", "type", "href") if key in link
        )
        return f"\n    <link {attributes}>"

    return "".join(element(link) for link in links) + "\n    "


def script_json(value: Any) -> str:
    """Serialise JSON safely for embedding in an HTML <script> element."""
    serialised = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    for char, escape in (
        ("<", "\\u003c"),
        (">", "\\u003e"),
        ("&", "\\u0026"),
        ("\u2028", "\\u2028"),
        ("\u2029", "\\u2029"),
    ):
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
    "doi",  # the record's DOI, by which the maturity check finds the repository in DataCite
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


def provider_config(live: dict[str, Any]) -> dict[str, Any] | None:
    """What the page needs to run or import an external evaluator: limits, links and reviewed versions. Names,
    labels and mappings are crate data (`#criterion-*`), loaded with the questions."""
    if not live.get("provider"):
        return None
    keep = ("id", "name", "mode", "connector", "path", "versionPath", "form", "documentation", "code", "terms")
    limits = ("scoreMax", "maturityMax", "maxParallel", "timeoutSeconds", "maxBytes")
    return live.get("providers", {}) | {
        "list": [
            {key: provider[key] for key in keep + limits if key in provider}
            | {
                "reviewed": provider.get("reviewed", []),
                "metrics": [alternate_id(metric, provider["id"]) for metric in provider["metric"]],
            }
            for provider in live["provider"]
        ]
    }


def page_config(
    content: dict[str, Any],
    text_links: dict[str, list[dict[str, str]]] | None = None,
    api: dict[str, str] | None = None,
    links: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    guide = content["guide"]["guide"]
    live = content["live"]
    status = build_identity_facts()["status"]
    champion = {key: value for key, value in live.get("champion", {}).items() if key != "test"}
    return {
        "ui": content["ui"],
        "config": {
            "version": guide["version"],
            "build": build_identity_facts(),
            "releaseStatus": status,
            "testingNotice": guide.get("testingNotice") if status == "testing" else None,
            "datePublished": iso(guide["datePublished"]),
            "freshnessDays": guide.get("freshnessDays", 180),
            "pageUrl": guide.get("pageUrl"),
            "textLinks": text_links or {},
            "foldedSections": [
                f"#page-{page['id']}-{number}"
                for page in content["pages"]
                for number, section in enumerate(page.get("section", []), start=1)
                if section.get("details")
            ],
            "api": {"files": API_FILES, "collections": list(API_COLLECTIONS), "records": api or {}},
            "signposts": links or [],
            "connectors": live.get("connector", []),
            "links": live.get("links", {}),
            "champion": champion,
            "nanopub": live.get("nanopub"),
            "dmpStatus": live.get("dmpStatus"),
            "nkr": nkr_config(content["snapshots"]),
            "discovery": live.get("discovery"),
            "helpers": live.get("helpers"),
            "views": VIEW_SCRIPTS,
            "software": live.get("software"),
            "providers": provider_config(live),
            "vocab": {
                "roCrate": RO_CRATE,
                "ftr": FTR,
                "prov": PROV,
                "fipTerms": FIP_TERMS,
                "guide": guide["vocabularyBase"],
                "guideTerms": {term: guide["vocabularyBase"] + term for term in EXPORT_GUIDE_TERMS},
                "webApplication": WEB_APPLICATION,
            },
            "favicons": {
                "hosts": sorted(entry["host"] for entry in content.get("favicons", []) if not entry.get("key")),
                "homeOnly": sorted(entry["host"] for entry in content.get("favicons", []) if entry.get("homeOnly")),
                "marks": {entry["key"]: entry["file"] for entry in content.get("favicons", []) if entry.get("key")},
            },
            "icons": {
                "ui": content.get("icons", {}).get("ui", {}),
                "kind": content.get("icons", {}).get("kind", {}),
                "relation": content.get("icons", {}).get("relation", {}),
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
            "toolGroup": {page["id"]: page["group"] for page in content["pages"] if page.get("menu") == "tools"},
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


def split_crate(crate: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """The crate as the page loads it: the core every view needs, and the parts (PART_SCRIPTS) that views load when
    they first need them. A part holds whole entities, or properties of core entities (original passages and source
    bylines); the core and the parts together are the crate."""
    graph = crate["@graph"]
    guidance_sources = {
        reference["@id"] for entity in graph if entity.get("guidance") for reference in as_list(entity.get("isPartOf"))
    }
    initial_sources = {
        reference["@id"] for entity in graph if entity["@id"] == "./" for reference in as_list(entity.get("isBasedOn"))
    }
    guidance_sources -= initial_sources
    pages = [entity for entity in graph if str(entity["@id"]).startswith("#page-") and "isPartOf" not in entity]
    sections = {ref["@id"] for page in pages for ref in as_list(page.get("hasPart"))}
    sections |= {
        ref["@id"] for entity in graph if entity["@id"] in sections for ref in as_list(entity.get("potentialAction"))
    }
    parts: dict[str, dict[str, Any]] = {name: {"entities": [], "properties": {}} for name in PART_SCRIPTS}
    core = []
    path_stages = f"#lifecycle-{PATH_LIFECYCLE}."
    for entity in graph:
        if entity["@id"] == "#implementation-model" or str(entity["@id"]).startswith(
            ("#layer-", "#seam-", "#model-context-", "#model-example-", "#model-worked-")
        ):
            parts["model"]["entities"].append(entity)
        elif str(entity["@id"]).startswith(path_stages):
            # The path's stages name the rail on every view; their definitions load with the other life-cycle models.
            detail = {
                key: entity[key]
                for key in ("description", "descriptionTranslation", "quotedDefinition", "citation", "license")
                if key in entity
            }
            parts["model"]["properties"][entity["@id"]] = detail
            core.append({key: value for key, value in entity.items() if key not in detail})
        elif entity["@id"] == f"#lifecycle-{PATH_LIFECYCLE}":
            # The path's model names its stages' source on the landing, with a link to the page that publishes it.
            detail = {key: entity[key] for key in ("citation", "hasDefinedTerm") if key in entity}
            parts["model"]["properties"][entity["@id"]] = detail
            core.append({key: value for key, value in entity.items() if key not in detail})
        elif str(entity["@id"]).startswith(("#lifecycle-", "#crosswalk-")):
            parts["model"]["entities"].append(entity)
        elif entity.get("@type") == "rdf:Property" and entity.get("rdfs:label") in MODEL_TERMS:
            # Full definitions are needed only with the model; its property IRIs remain in the core context.
            parts["model"]["entities"].append(entity)
        elif entity.get("@type") == "rdf:Property":
            # Vocabulary definitions serve source detail and machine readers, rather than initial navigation.
            # Keep their full definitions with the standards part, which the machine-data page also loads.
            parts["standards"]["entities"].append(entity)
        elif str(entity["@id"]).startswith("#alternate-term-"):
            # Imported glossary IDs are detail metadata; catalogue/search load them with the definitions.
            parts["standards"]["entities"].append(entity)
        # The FIP Dashboard snapshot (the profiles and the resource records they declare) and the KNAV catalogue's.
        elif str(entity["@id"]).startswith(("#item-", "#criterion-", "#mapping-")):
            # External evaluators' criteria and their reviewed mappings load with the questions they relate to.
            parts["questions"]["entities"].append(entity)
        elif str(entity["@id"]).startswith(("#fip-", "#fer-", "#knav-", "#infrastructure", "#european-ri-", "#eric-")):
            # The large research infrastructures load with the catalogue, as the registries' records do.
            parts["fips"]["entities"].append(entity)
        elif str(entity["@id"]).startswith(STANDARD_CLAUSES):
            parts["standards"]["entities"].append(entity)
        elif entity.get("@type") in ("CreateAction", "UpdateAction") and (
            entity.get("description") or entity.get("result")
        ):
            # The catalogue uses detailed provenance and a station's sources what changed it, both after this part
            # loads; navigation and credits need only names and dates.
            detail = {
                key: entity[key]
                for key in ("description", "result", "object", "agent", "instrument", "actionStatus")
                if key in entity
            }
            parts["standards"]["properties"][entity["@id"]] = detail
            core.append({key: value for key, value in entity.items() if key not in detail})
        elif entity.get("adviceKind") == "ai" and ("promptSample" in entity or "checkAfter" in entity):
            # An AI tip's prompt and what to check afterwards show on its station and the AI page, which load this.
            detail = {key: entity[key] for key in ("promptSample", "checkAfter") if key in entity}
            parts["standards"]["properties"][entity["@id"]] = detail
            core.append({key: value for key, value in entity.items() if key not in detail})
        elif entity["@id"] in sections:
            parts["pages"]["entities"].append(entity)
        elif str(entity["@id"]).startswith("#term-") and entity.get("description"):
            # Glossary labels serve navigation immediately; original definitions load with sourced detail/search.
            parts["standards"]["properties"][entity["@id"]] = {"description": entity["description"]}
            core.append({key: value for key, value in entity.items() if key != "description"})
        elif "guidance" in entity:
            parts["standards"]["properties"][entity["@id"]] = {"guidance": entity["guidance"]}
            core.append({key: value for key, value in entity.items() if key != "guidance"})
        elif entity["@id"] in guidance_sources and entity.get("creditText"):
            # Originals and their bylines load together; the homepage's foundation citation stays complete.
            parts["standards"]["properties"][entity["@id"]] = {"creditText": entity["creditText"]}
            core.append({key: value for key, value in entity.items() if key != "creditText"})
        else:
            core.append(entity)
    # Only core targets become property patches. Questions and standards keep their explicit associations
    # with their own deferred entities, so concurrent part loading cannot drop a patch for a missing target.
    for index, original in enumerate(core):
        entity = original
        if entity.get("disclosureLevel", {}).get("@id") in ("#level-L1", "#level-L2", "#level-L3"):
            detail = {key: value for key, value in entity.items() if key in ("text", "description")}
            if detail:
                parts["advice"]["properties"][entity["@id"]] = detail
                entity = {key: value for key, value in entity.items() if key not in detail}
                core[index] = entity
        deferred = {
            key: value for key, value in entity.items() if key in ("implementationLayers", "implementationSeams")
        }
        if deferred:
            parts["model"]["properties"].setdefault(entity["@id"], {}).update(deferred)
            core[index] = {key: value for key, value in entity.items() if key not in deferred}
    return crate | {"@graph": core}, parts


def part_script(name: str, part: dict[str, Any]) -> str:
    """A part of the knowledge base as a classic script the page loads when a view first needs it."""
    return (
        f"/* Part '{name}' of the knowledge base, loaded when a view needs it; with kb.js and the other parts it is "
        "the crate. Generated by scripts/build_crate.py from content/; do not edit. */\n"
        "window.FairGuideData = window.FairGuideData || {};\n"
        "window.FairGuideData.parts = window.FairGuideData.parts || {};\n"
        f"window.FairGuideData.parts[{json.dumps(name)}] = {script_json(part)};\n"
    )


def apply_language_patch(target: Any, patch: Any) -> None:
    """Apply a language patch from `split_languages` in place, as the page's `mergeData` (assets/js/core.js) does.

    The patch follows the target's tree. A null value, at an object key or an array position, changes nothing; an
    object or array replaces a missing or scalar value with an empty container of its kind and is merged into it; an
    array position past the end extends the array; any other value is set. Keys that would reach a prototype in the
    page (`__proto__`, `constructor`, `prototype`) are skipped here as there. tests/fixtures/language-patch.json holds
    the expected results both implementations are checked against.
    """
    entries = enumerate(patch) if isinstance(patch, list) else patch.items()
    for key, value in entries:
        if value is None or key in ("__proto__", "constructor", "prototype"):
            continue
        if isinstance(target, list):
            target.extend([None] * (key + 1 - len(target)))
        if isinstance(value, (dict, list)):
            existing = target[key] if isinstance(target, list) else target.get(key)
            if not isinstance(existing, (dict, list)):
                target[key] = [] if isinstance(value, list) else {}
            apply_language_patch(target[key], value)
        else:
            target[key] = value


def split_languages(value: Any) -> tuple[Any, dict[str, Any], list[dict[str, Any]]]:
    """Separate bilingual display values from neutral data without changing the complete crate.

    Patches follow the original tree; null array positions mean no change. Language tags and other structure stay
    in the common tree, so applying both patches reproduces every value in its original order. Original source
    passages are monolingual and stay together. A cited work also keeps its original title for translated citations.
    Compact folded word indexes preserve search in both languages without loading the other display translation.
    """
    search = []

    def visit(node: Any, path: list[str | int], original: str | None = None):
        if path in (["config", "languages"], ["config", "partLanguages"]):
            # These language keys select local file paths; they are bootstrap configuration, not display text.
            return node, {}
        if isinstance(node, list):
            languages = {item.get("@language") for item in node if isinstance(item, dict)}
            if set(LANGS) <= languages:
                common, patches = [], {lang: [] for lang in LANGS}
                for item in node:
                    language = item.get("@language") if isinstance(item, dict) else None
                    localized = language in LANGS and language != original and "@value" in item
                    common.append({key: value for key, value in item.items() if key != "@value"} if localized else item)
                    for lang in LANGS:
                        patches[lang].append({"@value": item["@value"]} if localized and language == lang else None)
                if path and path[-1] in {"name", "headline", "text", "description", "abstract", "keywords"}:
                    words = {}
                    for lang in LANGS:
                        other = " ".join(
                            str(item.get("@value", "")) if isinstance(item, dict) else str(item)
                            for item in node
                            if not isinstance(item, dict) or item.get("@language") != lang
                        )
                        folded = unicodedata.normalize("NFD", other)
                        folded = "".join(char for char in folded if not unicodedata.combining(char)).lower()
                        words[lang] = " ".join(dict.fromkeys(re.findall(r"[\w-]+", folded)))
                    search.append({"path": path, "words": words})
                return common, {lang: patch for lang, patch in patches.items() if any(patch)}
            common, patches = [], {lang: [] for lang in LANGS}
            for index, item in enumerate(node):
                shared, localized = visit(item, path + [index])
                common.append(shared)
                for lang in LANGS:
                    patches[lang].append(localized.get(lang))
            return common, {lang: patch for lang, patch in patches.items() if any(item is not None for item in patch)}
        if isinstance(node, dict):
            common, patches = {}, {lang: {} for lang in LANGS}
            # A translated text holds one value per language; a table keyed by language codes whose values are
            # themselves tables (the language facet's labels) is structure, and both languages keep all of it.
            bilingual = all(lang in node for lang in LANGS) and not any(isinstance(node[lang], dict) for lang in LANGS)
            source_language = node.get("inLanguage") if not node.get("resourceType") else None
            glossary = str(node.get("@id", "")).startswith("#term-") and node.get("termCode")
            # A repository's or an infrastructure's entry keeps its name in the other language too (D-173).
            named = node.get("@type") == "DataCatalog" or "abbreviation" in node
            for key, item in node.items():
                if bilingual and key in LANGS:
                    common[key] = ""
                    patches[key][key] = item
                    continue
                if (glossary and key == "name") or (named and key in ("name", "abbreviation")):
                    # The published vocabulary is deliberately shown as Czech/English pairs in its catalogue.
                    common[key] = item
                    continue
                shared, localized = visit(item, path + [key], source_language if key == "name" else None)
                common[key] = shared
                for lang, patch in localized.items():
                    patches[lang][key] = patch
            return common, {lang: patch for lang, patch in patches.items() if patch}
        return node, {}

    common, patches = visit(value, [])
    return common, {lang: patches.get(lang, {}) for lang in LANGS}, search


def language_script(lang: str, value: dict[str, Any], part: str | None = None) -> str:
    """A local classic script with one language's values; loaded on selection, including from file://."""
    assignment = (
        "window.FairGuideData.partLanguages = window.FairGuideData.partLanguages || {};\n"
        f"window.FairGuideData.partLanguages[{json.dumps(part)}] = "
        f"window.FairGuideData.partLanguages[{json.dumps(part)}] || {{}};\n"
        f"window.FairGuideData.partLanguages[{json.dumps(part)}][{json.dumps(lang)}]"
        if part
        else "window.FairGuideData.languages = window.FairGuideData.languages || {};\n"
        f"window.FairGuideData.languages[{json.dumps(lang)}]"
    )
    return (
        f"/* {lang} display values, loaded on language selection. "
        "Generated by scripts/build_crate.py; do not edit. */\n"
        "window.FairGuideData = window.FairGuideData || {};\n"
        f"{assignment} = {script_json(value)};\n"
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
        # FAIR Signposting: where harvesters find the knowledge base, the API, the licence and the linkset.
        "links": link_elements(signposts(content, crate)),
    }
    required = {"csp", "kb", "ui", "links"}
    found = {match.group("name") for match in BLOCK.finditer(page)}
    missing = sorted(required - found)
    if missing:
        raise ContentError(f"{PAGE_FILE}: missing generated block markers: {', '.join(missing)}")
    return BLOCK.sub(lambda match: match.group(1) + blocks[match.group("name")] + match.group(4), page)


# ---------------------------------------------------------------------------
# Entry point


# The Guide root and its API documentation: every view of the Guide is a fragment of the root, so it has no other page.
SITEMAP_PATHS = ("", "api/index.html")
# Assembly publishes the default-branch preview under this path, beside the release.
PREVIEW_PATH = "next/"
CRAWLER_FILES = ("robots.txt", "sitemap.xml")


def crawler_files(base: str) -> dict[str, str]:
    """Discovery at the actual publication root. A subpath cannot publish the origin's robots policy.

    Preview HTML remains crawlable so its noindex can be read. Only root hosting emits robots.txt; either hosting
    mode emits the production sitemap, without fragments, preview URLs or invented modification dates.
    """
    base = publication_base(base)
    urlset = ElementTree.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in SITEMAP_PATHS:
        ElementTree.SubElement(ElementTree.SubElement(urlset, "url"), "loc").text = base + path
    ElementTree.indent(urlset)
    sitemap = ElementTree.tostring(urlset, encoding="unicode", xml_declaration=True) + "\n"
    files = {"sitemap.xml": sitemap}
    if urllib.parse.urlsplit(base).path == "/":
        files["robots.txt"] = f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n"
    return files


def outputs(
    root: Path = ROOT,
    *,
    content: dict[str, Any] | None = None,
    graph: Graph | None = None,
    crate: dict[str, Any] | None = None,
) -> dict[str, str]:
    content = load_content(root / "content") if content is None else content
    graph = Graph() if graph is None else graph
    crate = build_crate(content, graph) if crate is None else crate
    links = signposts(content, crate)
    page = render_page(
        (root / PAGE_FILE).read_text(encoding="utf-8"), content, crate, icon_sprite(root / "assets" / "icons")
    )
    core, parts = split_crate(crate)
    ui = page_config(
        content,
        graph.text_links,
        {key: entity["catalogueAddress"] for key, entity in graph.entities.items() if entity.get("catalogueAddress")},
        links,
    )
    ui["config"]["catalogueKinds"] = {code: kind for kind, code in KIND_CODES.items()}
    # The page uses config.api.records; the complete graph field returns with its deferred data part.
    for index, entity in enumerate(core["@graph"]):
        if entity.get("catalogueAddress"):
            parts["fips"]["properties"].setdefault(entity["@id"], {})["catalogueAddress"] = entity["catalogueAddress"]
            core["@graph"][index] = {key: value for key, value in entity.items() if key != "catalogueAddress"}
    ui["config"]["parts"] = dict(PART_SCRIPTS)
    ui["config"]["languages"] = dict(LANGUAGE_SCRIPTS)
    ui["config"]["partLanguages"] = dict(PART_LANGUAGE_SCRIPTS)
    # Helper labels belong with the pages that use them, not the initial download.
    # Helper and machine-data labels belong with the pages that use them: they load with the pages part rather
    # than the initial download, which stays within its budget.
    page_labels = {key: ui["ui"][key] for key in ("helper", "machines") if key in ui["ui"]}
    if page_labels:
        parts["pages"]["ui"] = page_labels
        ui["ui"] = {key: value for key, value in ui["ui"].items() if key not in page_labels}
    # The self-check's own label groups (answers, evidence, results, evaluators) load with the questions, which every
    # view showing them needs; its top-level strings, which the path's rail also uses, stay in the initial download.
    selfcheck = ui["ui"].get("selfcheck", {})
    grouped = {
        key: value for key, value in selfcheck.items() if isinstance(value, dict) and not set(value) <= set(LANGS)
    }
    if grouped:
        parts["questions"]["ui"] = {"selfcheck": grouped}
        ui["ui"] = ui["ui"] | {"selfcheck": {key: value for key, value in selfcheck.items() if key not in grouped}}
    localized_core, core_languages, core_search = split_languages(core)
    localized_ui, ui_languages, _ = split_languages(ui)
    localized_parts = {name: split_languages(part) for name, part in parts.items()}
    return (
        {
            CRATE_FILE: json.dumps(crate, ensure_ascii=False, indent=2) + "\n",
            KB_SCRIPT: data_script(
                "kb",
                localized_core,
                "Neutral knowledge-base structure; with selected language values and deferred parts it is the crate.",
            ),
            UI_SCRIPT: data_script("ui", localized_ui, "Interface structure and configuration."),
            PAGE_FILE: page,
            PREVIEW_FILE: page,
            LINKSET_FILE: json.dumps(linkset(links), ensure_ascii=False, indent=2) + "\n",
        }
        | {path: part_script(name, localized_parts[name][0]) for name, path in PART_SCRIPTS.items()}
        | {
            path: language_script(
                lang,
                {
                    "kb": core_languages[lang],
                    "ui": ui_languages[lang],
                    "search": [{"path": entry["path"], "words": entry["words"][lang]} for entry in core_search],
                },
            )
            for lang, path in LANGUAGE_SCRIPTS.items()
        }
        | {
            path: language_script(
                lang,
                {
                    "values": localized_parts[name][1][lang],
                    "search": [
                        {"path": entry["path"], "words": entry["words"][lang]} for entry in localized_parts[name][2]
                    ],
                },
                name,
            )
            for name, paths in PART_LANGUAGE_SCRIPTS.items()
            for lang, path in paths.items()
        }
        | profile_shapes(root, vocabulary_base(content["guide"]["guide"]).removesuffix("terms#"))
        | profile_page(root, content["guide"]["guide"])
        | vocabulary_page(root, content["guide"]["guide"])
        | crawler_files(content["guide"]["guide"]["pageUrl"])
    )


PROFILE_PAGE = re.compile(r"^profile/[^/]+/index\.html$")
VOCABULARY_FILE = "terms/fair-guide.ttl"


def turtle_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def vocabulary_base(guide: dict[str, Any]) -> str:
    """The vocabulary IRI base, from the derived value or, for a caller that has not applied the addresses, the
    content's own `namespace`, so the check reads the same address the build writes."""
    if guide.get("vocabularyBase"):
        return str(guide["vocabularyBase"])
    value = guide.get("namespace") or guide.get("baseUrl")
    base = publication_base(value) if value else "/"
    return base + "terms#"


def vocabulary_document(guide: dict[str, Any]) -> str:
    """The guide's vocabulary in Turtle, served at the guide's address (`<address>terms`), so a consumer
    dereferencing a guide term IRI receives its definition. Derived from the one declaration `GUIDE_TERMS`."""
    base = vocabulary_base(guide)
    lines = [
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "",
        f"<{base.rstrip('#')}> a owl:Ontology ;",
        '    rdfs:label "EOSC CZ FAIR guide vocabulary"@en ;',
        '    rdfs:comment "The guide\'s own terms, with the established term each specializes."@en .',
        "",
    ]
    for term, definition in GUIDE_TERMS.items():
        broader, domain, range_ = GUIDE_TERM_SHAPES.get(term, ("", "", ""))
        lines.append(f"<{base}{term}> a rdf:Property ;")
        lines.append(f'    rdfs:label "{term}"@en ;')
        lines.append(f'    rdfs:comment "{turtle_text(definition)}"@en ;')
        if broader:
            lines.append(f"    rdfs:subPropertyOf <{broader}> ;")
        if domain:
            lines.append(f"    rdfs:domain <{domain}> ;")
        if range_:
            lines.append(f"    rdfs:range <{range_}> ;")
        lines[-1] = lines[-1].rstrip(" ;") + " ."
        lines.append("")
    return "\n".join(lines) + "\n"


# The vocabulary page groups the terms by what they are for, in this order, so it reads as a reference rather
# than a list. Every guide term appears in exactly one group; vocabulary_errors refuses one that does not.
GUIDE_TERM_GROUPS: list[tuple[str, list[str]]] = [
    (
        "Catalogue typing and status",
        [
            "resourceType",
            "guideType",
            "catalogueType",
            "repositoryKind",
            "repositoryFunction",
            "clauseKind",
            "discipline",
            "researchField",
            "lifecycleStage",
            "serviceStatus",
            "healthStatus",
            "infrastructurePhase",
            "esfriStatus",
            "nodeState",
        ],
    ),
    ("Descriptions and notes", ["guidance", "assessmentContext", "note", "disclaimer"]),
    (
        "Dated and reviewed status",
        ["statusAsOf", "reviewedVersion", "mappingCoverage", "mappingBasis", "championEvidenceOnly", "prefillLevel"],
    ),
    (
        "Self-check machinery",
        [
            "block",
            "disclosureLevel",
            "defaultProfile",
            "tier",
            "fixAt",
            "fixedBy",
            "appliesTo",
            "providedByNrpFor",
            "allowsNotApplicable",
            "lookup",
            "adviceKind",
            "checkAfter",
            "promptSample",
            "guideState",
            "guideSources",
        ],
    ),
    ("Roles and relations", ["operatedBy", "operates"]),
    (
        "Layers-and-Seams model",
        [
            "preparationStatus",
            "modelKind",
            "implementationLayers",
            "implementationSeams",
            "introduction",
            "ordering",
            "feedback",
            "transfer",
            "sender",
            "recipient",
            "carrier",
            "maintainers",
            "scope",
        ],
    ),
    (
        "National infrastructures and the EOSC CZ Node",
        [
            "infrastructureCharacter",
            "roadmapSince",
            "nationalNodeOf",
            "czechMembershipSince",
            "nodeMembership",
            "nodeMilestone",
            "nodeStateSince",
            "lensOrder",
        ],
    ),
    (
        "Translation, quotation and source joins",
        ["nameTranslation", "descriptionTranslation", "quotedDefinition", "rdmkitRecord", "trainingSearch"],
    ),
]


def vocabulary_page(root: Path, guide: dict[str, Any]) -> dict[str, str]:
    """The vocabulary document and its landing page at the guide's address: the terms the guide introduces, grouped
    by what they are for, each anchored at `<address>terms#<term>` so a term IRI opens its entry, with the broader
    established term it specializes (or the reason none exists), its domain and its range."""
    escape = html.escape

    def link(iri: str) -> str:
        return f'<a href="{escape(iri, quote=True)}"><code>{escape(iri)}</code></a>' if iri else ""

    sections = []
    for heading, terms in GUIDE_TERM_GROUPS:
        blocks = []
        for term in terms:
            if term not in GUIDE_TERMS:
                continue
            broader, domain, range_ = GUIDE_TERM_SHAPES.get(term, ("", "", ""))
            relation = f"specializes {link(broader)}" if broader else escape(GUIDE_TERM_REASONS.get(term, ""))
            blocks.append(
                f'\n      <article class="detail-entry" id="{escape(term, quote=True)}">'
                f'<h3><a href="#{escape(term, quote=True)}"><code>{escape(term)}</code></a></h3>'
                f"<p>{escape(GUIDE_TERMS[term])}</p>"
                f'<p class="detail-meta">{relation}</p>'
                f'<p class="detail-meta">Domain {link(domain)} · Range {link(range_)}</p></article>'
            )
        sections.append(
            f'\n    <section class="detail-group">\n      <h2>{escape(heading)}</h2>{"".join(blocks)}\n    </section>'
        )
    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; img-src 'self'">
    <title>EOSC CZ FAIR guide vocabulary</title>
    <link rel="alternate" type="text/turtle" href="{VOCABULARY_FILE}">
    <link rel="stylesheet" href="../assets/css/tokens.css">
    <link rel="stylesheet" href="../assets/css/app.css">
  </head>
  <body>
    <main class="wrap profile-page">
      <h1>EOSC CZ FAIR guide vocabulary</h1>
      <p class="detail-intro">The guide reuses an established vocabulary wherever one expresses a fact, so the
      terms below are the ones it introduces itself. Each has its own address here —
      <code>&lt;address&gt;terms#&lt;term&gt;</code> — which opens its entry, and declares the broader established
      term it specializes (or why none exists), the domain it is used on and its range. Machine readers use the
      <a href="{VOCABULARY_FILE}" type="text/turtle">Turtle document</a>.</p>{"".join(sections)}
      <p><a href="../">The FAIR Data Guide</a></p>
    </main>
  </body>
</html>
"""
    return {"terms/index.html": page, VOCABULARY_FILE: vocabulary_document(guide)}


def vocabulary_errors(
    guide: dict[str, Any],
    terms: dict[str, str] | None = None,
    reasons: dict[str, str] | None = None,
    document: str | None = None,
) -> list[str]:
    """Refuse a guide-specific term with no declared broader term and no recorded reason, and a published guide
    term absent from the vocabulary document. `terms`/`reasons`/`document` allow a planted regression."""
    terms = GUIDE_TERMS if terms is None else terms
    reasons = GUIDE_TERM_REASONS if reasons is None else reasons
    document = vocabulary_document(guide) if document is None else document
    base = vocabulary_base(guide)
    grouped = {term for _, group in GUIDE_TERM_GROUPS for term in group}
    errors = []
    for term in terms:
        broader = GUIDE_TERM_SHAPES.get(term, ("", "", ""))[0]
        if not broader and term not in reasons:
            errors.append(f"guide term '{term}' declares no broader established term and no recorded reason")
        if term not in grouped:
            errors.append(f"guide term '{term}' is not in a vocabulary-page group")
        if f"<{base}{term}>" not in document:
            errors.append(f"published guide term '{term}' is absent from the vocabulary document")
    return errors


def profile_page(root: Path, guide: dict[str, Any]) -> dict[str, str]:
    """The landing page of the guide's profile at the profile's own IRI (`<address>profile/<version>/`), so the
    identifier resolves: what the profile is, read from its description, and links to its description, its shapes,
    its specification and the guide. In English, like the profile."""
    shapes = root / PROFILE_DIR
    description = (shapes / "profile.ttl").read_text(encoding="utf-8") if (shapes / "profile.ttl").exists() else ""
    label = (re.search(r'rdfs:label "([^"]+)"', description) or [None, "EOSC CZ FAIR guide profile"])[1]
    comment = (re.search(r'rdfs:comment "([^"]+)"', description) or [None, ""])[1]
    specification = (re.search(r"prof:hasArtifact <([^>]+)>", description) or [None, ""])[1]
    publisher = (re.search(r"dct:publisher <([^>]+)>", description) or [None, ""])[1]
    token = (re.search(r'prof:hasToken "([^"]+)"', description) or [None, ""])[1]
    up = "../../"
    escape = html.escape

    def link(iri: str, text: str | None = None) -> str:
        return f'<a href="{escape(iri, quote=True)}">{escape(text or iri)}</a>' if iri else ""

    def entry(heading: str, body: str) -> str:
        return f'\n      <article class="detail-entry"><h3>{heading}</h3><p>{body}</p></article>'

    profile_iri = guide.get("profile")
    facts = [
        entry("Profile of", f"{link(RO_CRATE, 'RO-Crate 1.2')} and its transitive profile"),
    ]
    if profile_iri:
        identifier = f'<a href="{escape(profile_iri, quote=True)}"><code>{escape(profile_iri)}</code></a>'
        facts.insert(0, entry("Identifier", identifier))
    if publisher:
        facts.append(entry("Publisher", link(publisher)))
    if token:
        facts.append(entry("Token", f"<code>{escape(token)}</code>"))
    if specification:
        facts.append(entry("Specification", link(specification, "The guide's content model")))
    files = sorted(path.relative_to(root).as_posix() for path in shapes.rglob("*.ttl"))
    items = "".join(
        f'\n        <li><a href="{escape(up + urllib.parse.quote(name), quote=True)}" type="text/turtle">'
        f"{escape(name.removeprefix('profile/'))}</a></li>"
        for name in files
    )
    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; img-src 'self'">
    <title>{escape(label)}</title>
    <link rel="describedby" type="text/turtle" href="{up}{PROFILE_DIR}/profile.ttl">
    <link rel="stylesheet" href="{up}assets/css/tokens.css">
    <link rel="stylesheet" href="{up}assets/css/app.css">
  </head>
  <body>
    <main class="wrap profile-page">
      <h1>{escape(label)}</h1>
      <p class="detail-intro">{escape(comment)} The knowledge base is validated against it at every change, and the
      rules its shapes cannot express are checked by the guide's content checks. Machine readers use the
      <a href="{up}{PROFILE_DIR}/profile.ttl" type="text/turtle">Turtle document</a>.</p>
      <section class="detail-group">
        <h2>Profile</h2>{"".join(facts)}
      </section>
      <section class="detail-group">
        <h2>Files</h2>
        <ul class="detail-files">{items}
        </ul>
      </section>
      <p><a href="{up}">The FAIR Data Guide</a></p>
    </main>
  </body>
</html>
"""
    return {f"profile/{guide.get('profileVersion', '')}/index.html": page}


def profile_shapes(root: Path, base: str) -> dict[str, str]:
    """The profile's shapes at the guide's address: the address they were written with, read from their `fg:`
    prefix, is replaced by the configured one, so the address is set in one place."""
    shapes = {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((root / PROFILE_DIR).rglob("*.ttl"))
    }
    written = next(
        (match.group(1) for text in shapes.values() for match in re.finditer(r"@prefix fg: <([^>]*)terms#>", text)),
        None,
    )
    return {path: text.replace(written, base) if written else text for path, text in shapes.items()}


def page_payload(generated: dict[str, str], root: Path = ROOT, lang: str = "cs") -> dict[str, int]:
    """Compressed bytes of each file the page loads, read from the page's own script and stylesheet tags; a file the
    build generates is measured as generated."""
    page = generated[PAGE_FILE]
    files = [PAGE_FILE] + [match.group("script") or match.group("style") for match in PAGE_ASSET.finditer(page)]
    files.append(LANGUAGE_SCRIPTS[lang])
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


if __name__ == "__main__":
    import build_site

    sys.exit(build_site.main())
