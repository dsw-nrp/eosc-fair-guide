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
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, NamedTuple
from xml.etree import ElementTree

import build_identity
from catalogue_identity import (
    KINDS,
    MAX_ID,
    NKR_KIND,
    address_hint,
    alternate_id,
    bare_url,
    has_particles,
    parse_route,
    short_id,
    source_scheme,
    split_address,
    validate_identity,
)
from catalogue_identity import address as issue_address
from corrections import apply as apply_corrections
from knowledge_graph import NT_FILE, n_triples
from nkr_contract import NKR_PILOT_NOT_ACCEPTING, nkr_status
from publication_location import base_url as publication_base

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
# The record of the favicons the page shows for tools and services, relative to the checkout.
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
STANDARD_CLAUSES = ("clauses/CTS.", "clauses/CDIF.", "clauses/FDO.", "clauses/FRSM.")
PART_SCRIPTS = {
    "standards": "assets/data/kb-standards.js",
    "fips": "assets/data/kb-fips.js",
    "pages": "assets/data/kb-pages.js",
    "questions": "assets/data/kb-questions.js",
    "model": "assets/data/kb-model.js",
    "advice": "assets/data/kb-advice.js",
    "api": "assets/data/kb-api.js",  # Descriptions of the API's kinds, used only by the machines view.
}
# View code the page loads when the view first opens, beside the shared code every view needs.
# Views whose code loads when they first open: the catalogue, and the self-check with its parts and report, which a
# path page also loads when saved answers mark gaps on its rail.
VIEW_SCRIPTS = {
    "catalogue": "assets/js/catalogue-view.js",
    "machines": "assets/js/machines.js",
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
# A reference editors mark in a text: [[<kind>/<id>|phrase]], where the address names a catalogue record (with its
# scope, `<kind>/<scope>/<id>`, where it has one), and phrase is the words in this language that name it. A kind's
# list (`[[infrastructures|...]]`) and the Guide's profile (`[[profile|...]]`) are the only targets named otherwise.
REFERENCE = re.compile(r"\[\[(?P<id>[^\[\]|]+)\|(?P<phrase>[^\[\]|]+)\]\]")
PAGE_ASSET = re.compile(r'<script src="(?P<script>[^"]+)"|<link rel="stylesheet" href="(?P<style>[^"]+)"')

RO_CRATE = "https://w3id.org/ro/crate/1.2"
PROCESS_RUN_CRATE = "https://w3id.org/ro/wfrun/process/0.5"
FAIR_PRINCIPLES = "https://w3id.org/fair/principles/terms/"
FTR_TEST = "https://w3id.org/ftr#Test"
FTR_METRIC = "https://w3id.org/ftr#Metric"
FIP_TERMS = "https://w3id.org/fair/fip/terms/"
FIP_DASHBOARD = "https://fip-dashboard.dmp.eosc.cz/resources/"
NKR_OBJECTS = "https://repo.cz/objects/"
NON_DEPOSIT_STATUSES = frozenset({"planned", "in-development", "prospective"})
RE3DATA_RECORD = re.compile(r"re3data\.org/repository/(r3d\d+)")
FTR = "https://w3id.org/ftr#"
PROV = "http://www.w3.org/ns/prov#"
# SIO defines its terms under http; "is implementation of" links a test to the metric it implements.
SIO = "http://semanticscience.org/resource/"
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
    "disclosureLevel": "Disclosure level (L0 to L3) at which an advice item is shown.",
    "adviceKind": "What an advice item is: a direction to act, a tip, a station's key point or an AI tip.",
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
    "clauseStatus": "Whether a requirement is current, due for an editorial update or superseded.",
    "fipStatus": "Whether a FAIR Implementation Profile is published or a draft, as the FIP Dashboard records it.",
    "declarationStatus": "The status of one declaration in a FAIR Implementation Profile, as the profile states it.",
    "releaseStatus": "Whether this build of the guide is a testing version or a production release.",
    "resourceType": "Type of a resource, used to filter the resource finder.",
    "guideType": (
        "The guide's resource type of a cited source or a FIP Dashboard resource, from the crosswalk in "
        "content/guide.toml."
    ),
    "catalogueType": "Type of a FAIR-enabling resource in the FIP Dashboard.",
    "repositoryKind": "Kind of a repository: domain, institutional or general-purpose.",
    "repositoryFunction": "What a reader can use a repository or registry for.",
    "acceptsDeposits": "Whether a repository currently accepts deposits; false when its dated status rules them out.",
    "clauseKind": "Kind of a ledger clause: requirement, fulfilment in NRP, or statement.",
    "supersededBy": "Clause or source that replaces a superseded clause.",
    "lensOrder": "Order of a callout's items for one lens, written as '<lens>: <item>, <item>, ...'.",
    "relatedTo": "CoreTrustSeal requirement or CDIF profile related to a FAIR principle.",
    "note": "Additional remark shown with a clause or a self-check item.",
    "guidance": "Original description or guidance from the cited published source, in its original language.",
    "assessmentContext": (
        "Whether a question is source context that explains an assessment rather than an answerable criterion."
    ),
    "disclaimer": "Disclaimer that a snapshot's source publishes about its data, shown while it is present.",
    "prefillMapping": "A live source that can suggest an answer to a check question, as a typed pre-fill mapping.",
    "prefillSource": "The source or service a pre-fill mapping reads, as the guide's catalogue describes it.",
    "prefillField": "A field of the source's record, or a test of the service, that a pre-fill mapping reads.",
    "prefillCoverage": "How much of its question a pre-fill mapping covers: the whole question, part of it, or "
    "FAIR Champion evidence only, which answers Partly when its part is met and No when it fails.",
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
    "abbreviation": "The abbreviation of a name in each language, such as ČSDA in Czech and CSDA in English.",
    "operatorSource": "The published page or document that states who operates a service or repository.",
    "operatedBy": "The large research infrastructure operating a catalogue entry, where a source says so.",
    "researchField": "The science-disciplinary domain of a large research infrastructure in the national roadmap.",
    "infrastructurePhase": "The life-cycle phase of a large research infrastructure in the national roadmap.",
    "infrastructureCharacter": "Whether an infrastructure is single-sited, multi-sited, distributed or virtual.",
    "roadmapSince": "The year a large research infrastructure was included in the national roadmap.",
    "esfriStatus": "The ESFRI Roadmap 2021 status: ESFRI Landmark or ESFRI Project.",
    "nationalNodeOf": "ESFRI research infrastructures that an infrastructure is the Czech node of.",
    "roadmapLocator": "Where in the national roadmap a large research infrastructure's facts are stated.",
    "czechMembershipSince": "The year the Czech Republic entered an ERIC; 'expected' while the ERIC is being set up.",
    "nodeMilestone": "The month of the node's project by which a repository's integration is planned (M6, M12).",
    "nodeState": "The state of the EOSC CZ Node in the EOSC Federation, such as candidate.",
    "nodeStateSince": "The date the EOSC CZ Node reached its state, such as its approval as a candidate node.",
    "operatedBySource": "The published page or document that states which infrastructure operates an entry.",
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
    "entryPoint": "The callable name that runs a local assessment criterion in the browser.",
    "termPosition": "The place of a term among its set's terms, for a set read in order, such as life-cycle stages.",
}

# Established vocabularies the guide reuses (design: *Established vocabularies, term mapping and the guide's
# address*). A property key listed here carries the established IRI in the emitted graph and defines no term of its
# own; the key stays the graph's storage name. docs/content-model.md records the classification an editor reads.
SCHEMA = "http://schema.org/"
DCTERMS = "http://purl.org/dc/terms/"
DCAT = "http://www.w3.org/ns/dcat#"
FOAF = "http://xmlns.com/foaf/0.1/"
# DCMI's genres of a resource; a cited work's class where schema.org's would make it a part of the crate.
DCMITYPE = "http://purl.org/dc/dcmitype/"
DQV = "http://www.w3.org/ns/dqv#"
# A registry's record about one thing.
CATALOG_RECORD = "dcat:CatalogRecord"
ADMS = "http://www.w3.org/ns/adms#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
XSD = "http://www.w3.org/2001/XMLSchema#"
RDF_LANG = "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"
# A Guide class in a declaration; the build writes it at the vocabulary's address (`term_shape`).
GUIDE = "guide:"
ESTABLISHED_TERMS: dict[str, str] = {
    "identifier": SCHEMA + "identifier",
    "alternateIdentifier": SCHEMA + "identifier",
    "dataciteRepository": SCHEMA + "identifier",
    "supersededBy": DCTERMS + "isReplacedBy",
    "relatedTo": DCTERMS + "relation",
    "source": DCTERMS + "source",
    "operatorSource": DCTERMS + "source",
    "operatedBySource": DCTERMS + "source",
    "developerSource": DCTERMS + "source",
    "definitionPart": DCTERMS + "hasPart",
    "dependencyManifest": DCTERMS + "references",
    "sourceLocator": DCTERMS + "references",
    "roadmapLocator": DCTERMS + "references",
    "abbreviation": SCHEMA + "alternateName",
    "primaryTopic": FOAF + "primaryTopic",
    # A registry's classification of the thing its record describes.
    "classification": DCTERMS + "type",
    "qualifiedRelation": DCAT + "qualifiedRelation",
    "relation": DCTERMS + "relation",
    "hadRole": DCAT + "hadRole",
    # Where a resource applies, such as a FIP Dashboard scope; schema.org's spatialCoverage expects a place.
    "coverage": DCTERMS + "coverage",
    # A check is an FTR benchmark, which each of its questions names; a question is an FTR metric of the principles it
    # measures.
    "hasBenchmark": FTR + "hasBenchmark",
    "inDimension": DQV + "inDimension",
}

# The guide's own vocabulary: the terms the guide keeps in its namespace. Each declares the broader established
# term it specializes (empty where none exists, with the reason in GUIDE_TERM_REASONS), its domain and its range.
# The typing and status slots specialize their established parent rather than replacing it, because they are
# several distinct slots over one property that the profile targets individually.
GUIDE_TERMS: dict[str, str] = {term: definition for term, definition in TERMS.items() if term not in ESTABLISHED_TERMS}
# The guide's own classes, each with its definition, the established class it specializes and why that class is not
# used as it stands.
GUIDE_CLASSES: dict[str, tuple[str, str, str]] = {
    "AdviceItem": (
        "Advice the guide gives at a station, addressed to a reader's lens at a disclosure level.",
        SCHEMA + "CreativeWork",
        "schema.org's HowTo types describe the steps of one procedure, not advice addressed by lens and level.",
    ),
    "PrefillMapping": (
        "A live source that can suggest an answer to a check question: the source, the fields or tests it reads and "
        "how much of the question they cover.",
        SCHEMA + "Intangible",
        "schema:PropertyValue holds the value of an arbitrary property, not a source, what it reads and its coverage.",
    ),
    "Clause": (
        "A requirement, recommendation, fulfilment or finding the Guide cites from a published source, with its "
        "wording, conditions and normative strength.",
        SCHEMA + "CreativeWork",
        "No established class names a clause of a published source; schema.org and DCTERMS describe whole works.",
    ),
    "Resource": (
        "A service, tool, standard, document, course or other work the Guide's catalogue recommends or cites.",
        SCHEMA + "CreativeWork",
        "The catalogue lists services, tools, standards, documents and courses as one kind; no established class "
        "covers what the Guide recommends and cites.",
    ),
    "Repository": (
        "A data repository the Guide describes, where researchers deposit or find data.",
        SCHEMA + "DataCatalog",
        "schema:DataCatalog also types the registries the catalogue lists as resources.",
    ),
    "ResearchInfrastructure": (
        "A large research infrastructure of the national roadmap, an ERIC or another European research infrastructure.",
        SCHEMA + "Organization",
        "schema.org has no class for a research infrastructure, and not every organisation is one.",
    ),
    "LifecycleModel": (
        "A model of the research data life cycle: its stages in order, as its source publishes them.",
        SCHEMA + "DefinedTermSet",
        "schema:DefinedTermSet also types the Guide's vocabularies and its conceptual model.",
    ),
    "Crosswalk": (
        "A set of correspondences between the stages of two life-cycle models.",
        SCHEMA + "CreativeWork",
        "No established class names a crosswalk whose correspondences each carry their basis.",
    ),
    "StageCorrespondence": (
        "A correspondence between stages of two life-cycle models, with its basis and the source that states it.",
        SCHEMA + "CreativeWork",
        "SKOS mapping properties relate two concepts directly; a correspondence that carries its basis and its source "
        "needs a node, and no established class carries both.",
    ),
    "TermSet": (
        "A controlled vocabulary of the Guide, such as its tiers, levels, lenses or statuses.",
        SCHEMA + "DefinedTermSet",
        "schema:DefinedTermSet also types the life-cycle models, the conceptual model and the FAIR principles.",
    ),
    "AssessmentCriterion": (
        "A criterion an assessment applies to a self-check question: an evaluator's test or metric, or the Guide's "
        "own test.",
        SCHEMA + "CreativeWork",
        "FTR splits criteria into metrics and tests by how a provider exposes them; the Guide lists every provider's "
        "criterion as one kind.",
    ),
}
# The classes written on every record of a kind, beyond the established class its builder gives it: the Guide's
# class where kinds share one, and the class a kind's whole (a model, a crosswalk, a vocabulary) has where its
# members are selected by it (KIND_SELECTORS).
KIND_CLASSES: dict[str, tuple[str, ...]] = {
    "actions": ("prov:Activity",),
    "clauses": ("Clause",),
    "crosswalks": ("Crosswalk",),
    "infrastructures": ("ResearchInfrastructure",),
    "lifecycles": ("LifecycleModel",),
    "repositories": ("DataCatalog", "Repository"),
    "resources": ("Resource",),
    "tests": ("AssessmentCriterion",),
    "vocabularies": ("TermSet",),
}
# The class of a scoped record of a kind whose unscoped records are wholes: a crosswalk's correspondences.
SCOPED_KIND_CLASSES: dict[str, tuple[str, ...]] = {"crosswalks": ("StageCorrespondence",)}
# How a consumer selects each kind's records, which the checks hold to exactly its records: by a class (`class`), by
# the terms of a set or of every set of a class (`members`), by the term a property names (`term`), less what another
# selector selects (`except`); a list selects the union. A kind reached only by IRI records why (`reason`). A class
# is written as in the crate; a set or term by its address, or by its IRI where the Guide does not issue it.
KIND_SELECTORS: dict[str, Any] = {
    "actions": {"class": "prov:Activity"},
    "advice": {"class": "AdviceItem"},
    "callouts": {"reason": "The Guide's own text, which the stations and pages that show it reach by IRI."},
    "checks": {"class": "Quiz"},
    "clauses": {"class": "Clause"},
    "crosswalks": [{"class": "Crosswalk"}, {"class": "StageCorrespondence"}],
    "fips": {"class": "fip:FAIR-Implementation-Profile"},
    "glossary": {"members": "vocabularies/glossary"},
    "infrastructures": {"class": "ResearchInfrastructure"},
    "layers": {"term": ["modelKind", "vocabularies/model-kinds/layer"]},
    "lifecycles": [{"class": "LifecycleModel"}, {"members": {"class": "LifecycleModel"}}],
    "model-examples": {"term": ["modelKind", "vocabularies/model-kinds/example"]},
    "models": {
        "reason": "The Guide's one conceptual model, reached by IRI; its layers, seams and examples are selected by "
        "their model kind."
    },
    "organizations": {
        "class": "Organization",
        "except": [{"class": "ResearchInfrastructure"}, {"class": "Resource"}, {"class": "Repository"}],
    },
    "pages": {"reason": "The Guide's own text, reached by IRI from its navigation and its references."},
    "principles": {"members": FAIR_PRINCIPLES},
    "questions": {"class": "Question"},
    "repositories": {"class": "Repository"},
    "resources": {"class": "Resource"},
    "seams": {"term": ["modelKind", "vocabularies/model-kinds/seam"]},
    "stations": {"class": "HowToSection"},
    "tests": {"class": "AssessmentCriterion"},
    "vocabularies": [
        {"class": "TermSet"},
        {"members": {"class": "TermSet"}, "except": {"members": "vocabularies/glossary"}},
    ],
}
GUIDE_TERM_SHAPES: dict[str, tuple[str, str, str]] = {
    "preparationStatus": (ADMS + "status", SCHEMA + "ScholarlyArticle", SCHEMA + "DefinedTerm"),
    "modelKind": ("", "", SCHEMA + "DefinedTerm"),
    "implementationLayers": (DCTERMS + "subject", "", SCHEMA + "DefinedTerm"),
    "implementationSeams": (DCTERMS + "subject", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "introduction": ("", SCHEMA + "DefinedTermSet", RDF_LANG),
    "ordering": ("", SCHEMA + "DefinedTermSet", RDF_LANG),
    "feedback": ("", SCHEMA + "DefinedTermSet", RDF_LANG),
    "transfer": ("", SCHEMA + "DefinedTerm", RDF_LANG),
    "sender": ("", SCHEMA + "DefinedTerm", RDF_LANG),
    "recipient": ("", SCHEMA + "DefinedTerm", RDF_LANG),
    "carrier": ("", SCHEMA + "DefinedTerm", RDF_LANG),
    "maintainers": ("", SCHEMA + "DefinedTerm", RDF_LANG),
    "scope": ("", SCHEMA + "CreativeWork", RDF_LANG),
    "disclosureLevel": ("", GUIDE + "AdviceItem", SCHEMA + "DefinedTerm"),
    "adviceKind": ("", GUIDE + "AdviceItem", SCHEMA + "DefinedTerm"),
    "checkAfter": ("", GUIDE + "AdviceItem", RDF_LANG),
    "promptSample": ("", GUIDE + "AdviceItem", RDF_LANG),
    "block": ("", SCHEMA + "Question", SCHEMA + "DefinedTerm"),
    "defaultProfile": ("", SCHEMA + "Quiz", SCHEMA + "DefinedTerm"),
    "tier": ("", SCHEMA + "Question", SCHEMA + "DefinedTerm"),
    "fixAt": ("", SCHEMA + "Question", SCHEMA + "HowToSection"),
    "fixedBy": ("", SCHEMA + "Question", SCHEMA + "DefinedTerm"),
    "appliesTo": ("", SCHEMA + "Question", SCHEMA + "DefinedTerm"),
    "providedByNrpFor": ("", SCHEMA + "Question", SCHEMA + "DefinedTerm"),
    "allowsNotApplicable": ("", SCHEMA + "Question", XSD + "boolean"),
    "serviceStatus": (ADMS + "status", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "statusAsOf": (DCTERMS + "date", "", XSD + "string"),
    "healthStatus": (ADMS + "status", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "clauseStatus": (ADMS + "status", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "fipStatus": (ADMS + "status", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "declarationStatus": (ADMS + "status", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "releaseStatus": (ADMS + "status", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "resourceType": (DCTERMS + "type", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "guideType": (DCTERMS + "type", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "catalogueType": (DCTERMS + "type", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "repositoryKind": (DCTERMS + "type", SCHEMA + "DataCatalog", SCHEMA + "DefinedTerm"),
    "repositoryFunction": (DCTERMS + "subject", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "acceptsDeposits": ("", SCHEMA + "DataCatalog", XSD + "boolean"),
    "clauseKind": (DCTERMS + "type", GUIDE + "Clause", SCHEMA + "DefinedTerm"),
    "lensOrder": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "note": (SKOS + "note", "", RDF_LANG),
    "guidance": (DCTERMS + "description", SCHEMA + "CreativeWork", RDF_LANG),
    "assessmentContext": ("", SCHEMA + "Question", XSD + "boolean"),
    "disclaimer": (SKOS + "note", SCHEMA + "CreativeWork", RDF_LANG),
    "prefillMapping": ("", SCHEMA + "Question", GUIDE + "PrefillMapping"),
    "prefillSource": ("", GUIDE + "PrefillMapping", SCHEMA + "CreativeWork"),
    "prefillField": ("", GUIDE + "PrefillMapping", XSD + "string"),
    "prefillCoverage": ("", GUIDE + "PrefillMapping", SCHEMA + "DefinedTerm"),
    "lookup": ("", SCHEMA + "Question", ""),
    "guideState": ("", SCHEMA + "Dataset", XSD + "string"),
    "guideSources": ("", SCHEMA + "Dataset", XSD + "string"),
    "mappingCoverage": ("", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "reviewedVersion": ("", SCHEMA + "CreativeWork", XSD + "string"),
    "lifecycleStage": (DCAT + "theme", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "operatedBy": ("", "", SCHEMA + "Organization"),
    "researchField": (DCTERMS + "subject", SCHEMA + "Organization", SCHEMA + "DefinedTerm"),
    "infrastructurePhase": (ADMS + "status", SCHEMA + "Organization", SCHEMA + "DefinedTerm"),
    "infrastructureCharacter": ("", SCHEMA + "Organization", SCHEMA + "DefinedTerm"),
    "roadmapSince": ("", SCHEMA + "Organization", XSD + "string"),
    "esfriStatus": (ADMS + "status", SCHEMA + "Organization", SCHEMA + "DefinedTerm"),
    "nationalNodeOf": ("", SCHEMA + "Organization", SCHEMA + "Organization"),
    "czechMembershipSince": ("", SCHEMA + "Organization", XSD + "string"),
    "nodeMilestone": ("", DCAT + "Relationship", XSD + "string"),
    "nodeState": (ADMS + "status", SCHEMA + "Service", SCHEMA + "DefinedTerm"),
    "nodeStateSince": ("", SCHEMA + "Service", XSD + "string"),
    "mappingBasis": ("", GUIDE + "StageCorrespondence", SCHEMA + "DefinedTerm"),
    "nameTranslation": ("", SCHEMA + "DefinedTerm", XSD + "string"),
    "descriptionTranslation": ("", SCHEMA + "DefinedTerm", XSD + "string"),
    "quotedDefinition": ("", SCHEMA + "DefinedTerm", SCHEMA + "CreativeWork"),
    "discipline": (DCTERMS + "subject", SCHEMA + "CreativeWork", SCHEMA + "DefinedTerm"),
    "rdmkitRecord": ("", SCHEMA + "CreativeWork", ""),
    "trainingSearch": ("", SCHEMA + "CreativeWork", ""),
    "entryPoint": ("", GUIDE + "AssessmentCriterion", XSD + "string"),
    "termPosition": ("", SCHEMA + "DefinedTerm", XSD + "integer"),
}


def term_shape(term: str, base: str) -> tuple[str, str, str]:
    """A Guide term's broader term, domain and range, with a Guide class written at the vocabulary's address."""
    return tuple(  # type: ignore[return-value]
        base + value.removeprefix(GUIDE) if value.startswith(GUIDE) else value
        for value in GUIDE_TERM_SHAPES.get(term, ("", "", ""))
    )


GUIDE_TERM_REASONS: dict[str, str] = {
    term: reason
    for reason, terms in {
        "No established property expresses current availability for repository deposits.": ["acceptsDeposits"],
        "The guide's Layers-and-Seams conceptual model has no established equivalent.": [
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
            "assessmentContext",
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
            "prefillMapping",
            "prefillSource",
            "prefillField",
            "prefillCoverage",
            "lookup",
            "entryPoint",
        ],
        "The infrastructure that operates an entry is an entity reference; no single established property expresses "
        "the relation.": ["operatedBy"],
        "A national-roadmap or EOSC CZ Node fact the guide records; no established parent.": [
            "infrastructureCharacter",
            "roadmapSince",
            "nationalNodeOf",
            "czechMembershipSince",
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
        "schema:position's domain admits creative works and list items, not terms, and SKOS orders a scheme's "
        "members only through an ordered collection's list.": ["termPosition"],
        "A source's own remark, kept distinct from the guide's description.": ["disclaimer", "lensOrder"],
        "The exported result crate's own state and source provenance are the guide's.": ["guideState", "guideSources"],
    }.items()
    for term in terms
}

# The guide's own terms the exported result crate carries: the build owns their IRIs and the export reads them from
# the page configuration rather than declaring its own, so the page and its exports share one term context.
EXPORT_GUIDE_TERMS = ("guideState", "guideSources", "implementationLayers", "implementationSeams")

# Sources are contextual entities. A cited dataset is a dcat:Dataset and cited software a dcmitype:Software: RO-Crate
# reads schema.org's Dataset and SoftwareSourceCode as data entities and scripts that belong inside the crate.
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
    "dataset": DCAT + "Dataset",
    "software": DCMITYPE + "Software",
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

    def resolved(label: str, value: str | None) -> str:
        try:
            return publication_base(value or "")
        except ValueError as error:
            raise ContentError(f"{label}: {error}") from error

    namespace = resolved("guide.namespace", guide.get("namespace") or guide.get("baseUrl"))
    content_base = resolved("guide.baseUrl", guide.get("baseUrl"))
    environment_base = os.environ.get(BASE_URL_ENV)
    guide["pageUrl"] = resolved(BASE_URL_ENV, environment_base) if environment_base else content_base
    guide["vocabularyBase"] = namespace + "terms#"
    guide["recordBase"] = namespace + "id/"
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
            if "statement" not in item:
                # The content checks tell a question that takes its clause's text from one that copies it.
                item["statement"] = clause.get("text")
                item["statementFromRequirement"] = True
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
    """Drop properties without a value, unwrap single-item lists, and name an entity by its headline or, for a typed
    identifier, by its scheme. A name never only repeats the entity's identifier, which it carries once."""
    pruned: dict[str, Any] = {}
    for key, value in entity.items():
        if value in (None, [], "", {}):
            continue
        unwrapped = value[0] if isinstance(value, list) and len(value) == 1 and key != "@type" else value
        pruned[key] = unwrapped
    if "name" not in pruned and "rdfs:label" not in pruned:
        fallback = pruned.get("headline") or pruned.get("propertyID")
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
        # Build-only repository identity, shared with retirement reporting; never serialized.
        self.repository_keys: dict[str, set[str]] = {}
        # Each catalogue record's address, by its published identifier, once the identities are published, and each
        # build key's published identifier, for build-time readers of the content rows; neither is serialized.
        self.addresses: dict[str, str] = {}
        self.published: dict[str, str] = {}
        # Each provenance action's results as authored, by address, until the identities are published.
        self.results: dict[str, list[str]] = {}

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


# The kinds of record prose may reference. The rest of the catalogue (principles, questions' answers, provenance
# actions, vocabularies) is reached from the catalogue itself, not from prose.
REFERENCE_KINDS = frozenset(
    {
        "checks",
        "clauses",
        "crosswalks",
        "fips",
        "glossary",
        "infrastructures",
        "layers",
        "lifecycles",
        "model-examples",
        "models",
        "organizations",
        "pages",
        "questions",
        "repositories",
        "resources",
        "seams",
        "stations",
        "tests",
    }
)


def reference_targets(
    content: dict[str, Any], graph: Graph, placements: dict[str, Placement] | None = None
) -> dict[str, str]:
    """Every target a prose reference may name, as the entity it names: a record's address or a part's
    (`pages/machines#tasks`), from the one identity projection, and a kind word for that kind's list. During the
    build the entities are named by their build keys, afterwards by their published identifiers."""
    if placements is None and graph.addresses:
        base = content["guide"]["guide"]["recordBase"]
        records = {
            entity_id.removeprefix(base): entity_id for entity_id in graph.entities if entity_id.startswith(base)
        }
    else:
        placements = placements if placements is not None else identity_projection(graph, content)
        records = {placement.address: key for key, placement in placements.items() if placement.address}
        records |= {
            f"{placements[placement.owner].address}#{placement.fragment}": key
            for key, placement in placements.items()
            if placement.owner in placements and placements[placement.owner].address
        }
    targets = {address: entity_id for address, entity_id in records.items() if address.split("/")[0] in REFERENCE_KINDS}
    if (content.get("infrastructures") or {}).get("infrastructure"):
        targets["infrastructures"] = "#infrastructures"
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
                    raise ContentError(
                        f"{owner}: the text refers to an unknown entry '{match['id']}'"
                        + address_hint(match["id"], set(targets))
                    )
                found.setdefault(target, {"ref": target}).setdefault(lang, match["phrase"])
                return match["phrase"]

            return REFERENCE.sub(phrase, value)

        for key in [key for key in entity if not key.startswith("@")]:
            entity[key] = clean(entity[key])
        if found:
            # schema:mentions belongs to a CreativeWork; a term describes what its text names with schema:about.
            relation = "about" if {"DefinedTerm", "DefinedTermSet"} & set(as_list(entity.get("@type"))) else "mentions"
            mentioned = [item["@id"] for item in as_list(entity.get(relation))]
            entity[relation] = refs(mentioned + [target for target in found if target not in mentioned])
            graph.text_links[entity_id] = list(found.values())


# The statuses that are terms of their own schemes, by the property that names them, each specialising adms:status:
# the scheme's set, its name and its terms' build prefix. The terms are authored in guide.toml under the property.
STATUS_SCHEMES: dict[str, tuple[str, str, str]] = {
    "clauseStatus": ("requirement-statuses", "Requirement statuses", "requirement-status"),
    "fipStatus": ("fip-statuses", "FIP statuses", "fip-status"),
    "declarationStatus": ("declaration-statuses", "FIP declaration statuses", "declaration-status"),
    "healthStatus": ("health-statuses", "Test health", "health"),
    "preparationStatus": ("preparation-statuses", "Preparation statuses", "preparation"),
    "releaseStatus": ("release-statuses", "Release statuses", "release"),
    "nodeState": ("node-states", "EOSC CZ Node states", "node-state"),
}
# Every scheme whose terms a property names by code: the statuses, and what kind of advice an item is.
TERM_SCHEMES: dict[str, tuple[str, str, str]] = {
    **STATUS_SCHEMES,
    "adviceKind": ("advice-kinds", "Advice kinds", "advicekind"),
    "prefillCoverage": ("prefill-coverages", "Pre-fill coverage", "prefill-coverage"),
    "clauseKind": ("clause-kinds", "Clause kinds", "clausekind"),
    "modelKind": ("model-kinds", "Model kinds", "modelkind"),
    "mappingBasis": ("correspondence-bases", "Correspondence bases", "mappingbasis"),
    "mappingCoverage": ("evaluator-coverages", "Evaluator mapping coverage", "mappingcoverage"),
    "discipline": ("disciplines-knav", "KNAV catalogue discipline groups", "knavdiscipline"),
    "coverage": ("scopes-fip-dashboard", "FIP Dashboard scopes", "fdscope"),
}
# A scheme whose terms content/guide.toml lists under a name other than the property that names them.
TERM_LISTS = {"discipline": "knavDiscipline", "coverage": "fipDashboardScope"}
# A scheme a registry publishes, attributed to that registry's catalogue entry rather than to the Guide.
REGISTRY_SCHEMES = {"discipline": "knav-dm-tools-catalogue", "coverage": "fip-dashboard"}
# The term sets the page reads by code alone, with its own labels, never by a term's own name or description.
CODED_SETS = frozenset(set_id for set_id, _, _ in TERM_SCHEMES.values())


def status_term(graph: Graph, prop: str, code: Any) -> dict[str, str] | None:
    """A status, or another coded value, as the term of its scheme. A code the scheme lacks is refused, so no status
    stays a string."""
    if code in (None, ""):
        return None
    set_id, _, prefix = TERM_SCHEMES[prop]
    term_id = f"#{prefix}-{code}"
    if term_id not in graph.entities:
        raise ContentError(f"{prop}: '{code}' is no term of the {set_id} scheme in guide.toml")
    return ref(term_id)


def status_code(value: Any) -> str | None:
    """The code of a status term a published node names (`.../release-statuses/testing` gives `testing`)."""
    target = value.get("@id") if isinstance(value, dict) else None
    return str(target).rsplit("/", 1)[-1] if target else None


def defined_terms(graph: Graph, set_id: str, set_name: str, prefix: str, items: list[dict[str, Any]]) -> list[str]:
    """Add a named term set and its terms; return the term IDs. Every term is a DefinedTerm in exactly one
    DefinedTermSet, which it names with `inDefinedTermSet`; the set lists its terms in order. Their SKOS reading is
    stated once, in the vocabulary document, so no instance carries a second type or membership."""
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
                # An organisation has no CreativeWork domain; dcterms:source names its published selection.
                "source": ref(GUIDE_SELECTION),
            },
            "organization:" + organization["id"],
        )
    return organizations


# What a thing the Guide's own content describes rests on, beside any registry's record about it. A thing that rests
# on nothing but registry records is one only registries know.
GUIDE_SELECTION = "#guide-selection"

# The crate-local lists that hold the records of a kind, so a link to a kind's list names the list.
KIND_LISTS = {
    "stations": "#path",
    "clauses": "#ledger",
    "repositories": "#repositories",
    "resources": "#resources",
    "tests": "#tests",
}


def action_target(href: str) -> dict[str, str]:
    """What an action opens: an outside page, a kind's list (with the topic it narrows to), or a record by its
    address, which names the record's own IRI once identities are published."""
    target, mark, query = href.partition("?")
    if "://" in href or target not in KIND_LISTS:
        return ref(href)
    return ref(KIND_LISTS[target] + mark + query)


def name_text(value: Any) -> str | None:
    """A literal name from the content or the graph, whether it is a plain string or a language-tagged value."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return name_text(value.get("@value"))
    if isinstance(value, list):
        return next((name_text(item) for item in value if name_text(item)), None)
    return None


# The build keys of the things a named agent can be: an organisation, an infrastructure, a repository or a resource
# the Guide describes. A FIP Dashboard organisation record no curated thing names is such an organisation too.
AGENT_THINGS = ("#org-", "#infrastructure-", "#european-ri-", "#repository-", "#resource-", "#eosc-cz-node")


def folded_names(entity: dict[str, Any]) -> set[str]:
    """An entity's names in every language, its alternate names and its acronym, as an exact name comparison reads
    them."""
    values = [value for key in ("name", "alternateName", "abbreviation") for value in name_values(entity.get(key))]
    return {unicodedata.normalize("NFKC", value).casefold() for value in values}


def agent_things(graph: Graph, founded: set[str]) -> dict[str, str]:
    """Every entity a named agent's name can match, with the thing it stands for: a thing the Guide describes stands
    for itself, a KNAV or FIP Dashboard record for the curated thing it is linked to, and a record no curated thing
    stands for founds a thing of its own. `founded` holds the FIP Dashboard organisation records that found
    organisations of their own."""
    dashboard_pages = {
        target: entity_id
        for entity_id, entity in graph.entities.items()
        if entity_id.startswith(AGENT_THINGS)
        for target in ids_of(entity.get("sameAs"))
        if target.startswith(FIP_DASHBOARD)
    }
    things = {entity_id: entity_id for entity_id in graph.entities if entity_id.startswith(AGENT_THINGS)}
    things |= {key: key for key in founded}
    for entity_id, entity in graph.entities.items():
        if entity_id.startswith("#fer-"):
            pages = [target for target in ids_of(entity.get("sameAs")) if target in dashboard_pages]
            things[entity_id] = dashboard_pages[pages[0]] if pages else entity_id
    for entity_id, entity in graph.entities.items():
        if entity_id.startswith("#knav-"):
            standing = next((target for target in ids_of(entity.get("sameAs")) if target in graph.entities), None)
            things[entity_id] = things.get(standing, standing) if standing else entity_id
    return things


def agent_ref(graph: Graph, name: str, things: dict[str, str]) -> str:
    """The entity for a named agent (a publisher, an operating, hosting or developing organisation): the one thing the
    Guide describes under exactly that name, in any language and of any kind (agent_things), or the record an address
    names. A name two things share is refused, and the content names the agent by address instead; only a name no
    thing has adds an organisation, which a later agent of that name finds."""
    if "/" in name and name.split("/", 1)[0] in KINDS:
        return name  # an address, which becomes the record's IRI once identities are published
    folded = unicodedata.normalize("NFKC", name).casefold()
    matches = sorted(
        {thing for entity_id, thing in things.items() if folded in folded_names(graph.entities[entity_id])}
    )
    if len(matches) > 1:
        raise ContentError(f"the agent '{name}' names several things ({', '.join(matches)}); name it by its address")
    if matches:
        return matches[0]
    # A new organisation is named like any minted record: by the name's words, without particles, within 32
    # characters.
    entity_id = f"#org-{short_id(name, set())}"
    graph.add({"@id": entity_id, "@type": "Organization", "name": name})
    things[entity_id] = entity_id
    return entity_id


def organization_record_owners(graph: Graph, content: dict[str, Any]) -> dict[str, str]:
    """Each FIP Dashboard organisation record's thing, by build key: the curated thing whose row names the record's
    handle (an organisation's or an infrastructure's `fipDashboard`, a European infrastructure's in its `nodeOf` or
    `eric` entry, a resource's `fipDashboardOrganization`), or that carries the record's ROR. A name never attaches a
    record; one no thing names founds an organisation of its own."""
    handles: dict[str, str] = {}
    for row in content["guide"].get("organization", []):
        if isinstance(row.get("fipDashboard"), str):
            handles[row["fipDashboard"]] = f"#org-{row['id']}"
    for item in (content.get("infrastructures") or {}).get("infrastructure", []):
        if item.get("fipDashboard"):
            handles[item["fipDashboard"]] = f"#infrastructure-{item['id']}"
        for entry in item.get("nodeOf", []) + item.get("eric", []):
            if entry.get("fipDashboard"):
                handles[entry["fipDashboard"]] = f"#european-ri-{slug(entry['name'])}"
    for resource in content["resources"]:
        if resource.get("fipDashboardOrganization"):
            handles[resource["fipDashboardOrganization"]] = f"#resource-{resource['id']}"
    rors = {
        target: entity_id
        for entity_id, entity in graph.entities.items()
        if entity_id.startswith(AGENT_THINGS)
        for target in ids_of(entity.get("sameAs"))
        if target.startswith("https://ror.org/")
    }
    owners = {}
    for snapshot in content["snapshots"]:
        for row in snapshot.get("organization", []):
            owner = handles.get(alternate_id(row, "fip-dashboard")) or rors.get(row.get("ror", ""))
            if owner in graph.entities:
                owners[f"#fd-org-{row['id']}"] = owner
    return owners


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
    # A lens is a term of the lens set like any other controlled term, and also an Audience, which `audience` needs.
    lenses = guide.get("lens", [])
    graph.add(
        {
            "@id": "#lenses",
            "@type": "DefinedTermSet",
            "name": "Reader lenses",
            "hasDefinedTerm": refs([f"#lens-{lens['id']}" for lens in lenses]),
        }
    )
    for lens in lenses:
        graph.add(
            {
                "@id": f"#lens-{lens['id']}",
                "@type": ["DefinedTerm", "Audience"],
                "termCode": lens["id"],
                "name": text(lens["name"]),
                "audienceType": lens["id"],
                "description": text(lens.get("description")),
                "inDefinedTermSet": ref("#lenses"),
            },
            f"lens:{lens['id']}",
        )
    defined_terms(graph, "levels", "Disclosure levels", "level", guide.get("level", []))
    defined_terms(graph, "tiers", "Self-check tiers", "tier", guide.get("tier", []))
    defined_terms(graph, "statuses", "Service statuses", "status", guide.get("status", []))
    defined_terms(graph, "actors", "Actors", "actor", guide.get("actor", []))
    for actor in guide.get("actor", []):
        # A clause's actor is an Audience as `schema:audience` requires, beside its controlled-term type.
        graph.entities[f"#actor-{actor['id']}"]["@type"] = ["DefinedTerm", "Audience"]
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
    for role in guide.get("nodeRole", []):
        graph.entities[f"#noderole-{role['id']}"]["@type"] = ["DefinedTerm", "dcat:Role"]
    for prop, (set_id, set_name, prefix) in TERM_SCHEMES.items():
        defined_terms(graph, set_id, set_name, prefix, guide.get(TERM_LISTS.get(prop, prop), []))
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
    specializes where one exists, its domain and its range, and one rdfs:Class per class with the class it
    specializes."""
    for term, definition in GUIDE_TERMS.items():
        broader, domain, range_ = term_shape(term, vocabulary_base)
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
    for name, (definition, broader, _) in GUIDE_CLASSES.items():
        graph.add(
            {
                "@id": vocabulary_base + name,
                "@type": "rdfs:Class",
                "rdfs:label": name,
                "rdfs:comment": definition,
                "rdfs:subClassOf": {"@id": broader},
            }
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
                "isBasedOn": ref(GUIDE_SELECTION),
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
        "publisher": ref(organizations[citation["publisher"]]) if citation.get("publisher") in organizations else None,
        "publisherName": citation.get("publisher") if citation.get("publisher") not in organizations else None,
        "version": citation.get("version"),
        "author": refs([people[author] for author in authors if author in people]),
        "creditText": "; ".join(names.get(author, author) for author in authors) or None,
        "datePublished": iso(citation["datePublished"]) if citation.get("datePublished") else None,
        "dateModified": iso(citation["dateModified"]) if citation.get("dateModified") else None,
        "sdDatePublished": iso(citation["dateAccessed"]) if citation.get("dateAccessed") else None,
        "license": citation.get("license"),
        "preparationStatus": status_term(graph, "preparationStatus", citation.get("preparationStatus")),
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
                "clauseKind": status_term(graph, "clauseKind", clause.get("kind")),
                "sourceLocator": clause.get("locator"),
                "clauseStatus": status_term(graph, "clauseStatus", clause.get("status", "current")),
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
            # What the item is: an AI tip or a station's key point as the content says, a tip at the Why level, and
            # otherwise a direction to act.
            kind = advice.get("kind") or ("tip" if level == "L2" else "direction")
            step_ids = [f"{advice_id}-step-{number}" for number in range(1, len(advice.get("steps", [])) + 1)]
            # The next step first, then at most one related tool.
            actions = as_list(advice.get("action"))
            action_ids = [
                f"{advice_id}-action" + (f"-{number}" if number > 1 else "") for number in range(1, len(actions) + 1)
            ]
            graph.add(
                {
                    "@id": advice_id,
                    "@type": "AdviceItem",
                    "identifier": advice["id"],
                    "text": text(advice["text"]),
                    "position": advice.get("position", order),
                    "audience": lens_refs(advice["lens"], all_lenses),
                    "disclosureLevel": ref(f"#level-{level}"),
                    "adviceKind": status_term(graph, "adviceKind", kind),
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
                    {
                        "@id": action_id,
                        "@type": "Action",
                        "name": text(action["label"]),
                        "target": action_target(action["href"]),
                    }
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


# The catalogue entry of each live source a question's pre-fill names; the DOI or Handle resolver is the Guide's own
# lookup through either system, which no single entry describes.
PREFILL_SOURCES = {
    "datacite": "datacite",
    "champion": "fair-champion",
    "fip": "fip-dashboard",
    "nkr": "nkr",
    "re3data": "re3data",
    "resolver": None,
}


def build_prefill(graph: Graph, item_id: str, item: dict[str, Any]) -> list[str]:
    """One typed mapping per live source that can suggest the item's answer: the source, the fields, tests or FIP
    questions it reads, and how much of the question it covers. The item's `prefillLevel` and
    `championEvidenceOnly` are read into that coverage."""
    prefill_ids = []
    for source, value in item.get("prefill", {}).items():
        if source not in PREFILL_SOURCES:
            raise ContentError(f"{item_id}: unknown pre-fill source '{source}'")
        if source == "champion" and item.get("championEvidenceOnly"):
            coverage = "champion-evidence-only"
        else:
            coverage = "partly" if item.get("prefillLevel") == "partly" else "whole"
        entry = next((key for key in graph.resolve([PREFILL_SOURCES[source] or ""]) if key in graph.entities), None)
        prefill_id = f"{item_id}-prefill-{source}"
        prefill_ids.append(prefill_id)
        graph.add(
            {
                "@id": prefill_id,
                "@type": "PrefillMapping",
                "identifier": source,
                "prefillSource": ref(entry) if entry else None,
                "prefillField": [str(field) for field in as_list(value)] if value is not True else None,
                "prefillCoverage": status_term(graph, "prefillCoverage", coverage),
            }
        )
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
            prefill_ids = build_prefill(graph, item_id, item)
            applies = [f"#profile-{profile}" for profile in item.get("profiles", [])]
            applies += [f"#mode-{mode}" for mode in item.get("modes", [])]
            graph.add(
                {
                    "@id": item_id,
                    # A question is the FTR metric its manual test and any automated tests implement.
                    "@type": ["Question", "ftr:Metric"],
                    "identifier": item["id"],
                    "text": text(item["statement"]),
                    "description": text(item.get("help")),
                    "position": order,
                    "inDimension": refs([principle_iri(principle) for principle in item.get("principles", [])]),
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
                    "prefillMapping": refs(prefill_ids),
                    "lookup": ref(links[item["lookup"]]) if item.get("lookup") else None,
                    "hasBenchmark": ref(check_id),
                },
                item["id"],
            )
        graph.add(
            {
                "@id": check_id,
                # A check is the FTR benchmark its questions are the metrics of.
                "@type": ["Quiz", "ftr:Benchmark"],
                "identifier": check["id"],
                "name": text(check["name"]),
                "description": text(check.get("description")),
                "audience": refs([f"#lens-{lens}" for lens in check.get("lenses", [])]),
                "timeRequired": f"PT{check['minutes']}M" if check.get("minutes") else None,
                "defaultProfile": ref(f"#profile-{check['defaultProfile']}") if check.get("defaultProfile") else None,
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
            "additionalType": ([DCMITYPE + "Software"] if resource["type"] == "tool" else [])
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
            "operatorSource": ref((resource.get("operator") or {}).get("source"))
            if (resource.get("operator") or {}).get("source")
            else None,
            "rdmkitRecord": (
                ref("https://rdmkit.elixir-europe.org/all_tools_and_resources#" + rdmkit["id"])
                if rdmkit.get("id")
                else None
            ),
            "trainingSearch": (
                ref(
                    "https://tess.elixir-europe.org/search?" + urllib.parse.urlencode({"q": '"' + rdmkit["tess"] + '"'})
                )
                if rdmkit.get("tess")
                else None
            ),
            "sameAs": refs(
                resource.get("sameAs", [])
                + registry_links
                + ([FIP_DASHBOARD + resource["fipDashboard"]] if resource.get("fipDashboard") else [])
                + ([f"https://doi.org/{citation['doi']}"] if citation and citation.get("doi") else [])
            ),
            "isBasedOn": [ref(GUIDE_SELECTION)],
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


def registry_record_key(scheme: str, value: str) -> str:
    """The build key of a registry's record about a thing, which the identity projection places under the thing."""
    return f"#{scheme}-record-{slug(str(value))}"


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
    # (a table, from the entry or its record annotation) corrects both.
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
        "operatorSource": ref((repository.get("operator") or {}).get("source"))
        if (repository.get("operator") or {}).get("source")
        else None,
        "developerName": text((repository.get("developer") or {}).get("name")),
        "developerSource": ref((repository.get("developer") or {}).get("source"))
        if (repository.get("developer") or {}).get("source")
        else None,
        "isBasedOn": [ref(based_on)],
    }


def repository_key(repository: dict[str, Any]) -> str:
    if repository.get("re3data"):
        return f"re3data:{repository['re3data']}"
    return "url:" + (repository.get("url") or repository["id"]).rstrip("/").lower()


def snapshot_id(snapshot: dict[str, Any]) -> str:
    return f"#snapshot-{slug(snapshot['snapshot']['source'])}"


def nkr_match_keys(repository: dict[str, Any]) -> set[str]:
    """The reviewed Repository schema supports an NKR handle and its exact address as join keys."""
    keys = {"nkr:" + repository["nkr"]} if repository.get("nkr") else set()
    if address := bare_url(repository.get("url")):
        keys.add("url:" + address)
    return keys


def nkr_repositories(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """The repositories of an NKR snapshot as repository records: NKR's name, address, kind and keywords, its record
    ID and source status. Nothing else of the record is read here."""
    if snapshot.get("snapshot", {}).get("source") != "NKR":
        return []
    repositories = []
    for record in snapshot.get("record", []):
        status = nkr_status(record.get("status"))
        if status is None:
            continue
        repositories.append(
            {
                "id": record["id"],
                "name": {
                    "cs": str(record["repositoryName"]).strip(),
                    "en": next(
                        (
                            str(item["additionalName"]).strip()
                            for item in record.get("additionalNames", [])
                            if item.get("lang") == "English" and item.get("additionalName", "").strip()
                        ),
                        str(record["repositoryName"]).strip(),
                    ),
                },
                "url": record.get("mainUrl"),
                "nkr": alternate_id(record, "nkr"),
                "kind": NKR_KIND.get(str(record.get("type", ""))),
                "status": status,
                "asOf": snapshot["snapshot"]["retrieved"],
                "nkrStatus": record["status"],
                "subjects": {
                    "cs": ", ".join(map(str, as_list(record.get("keywordCz")))),
                    "en": ", ".join(map(str, as_list(record.get("keywordEn")))),
                },
            }
        )
    return repositories


# The catalogue entry of a source whose snapshot names it otherwise than by the entry's ID.
SNAPSHOT_CATALOGUES = {"KNAV Data Management Tools Catalogue": "knav-dm-tools-catalogue"}


def build_snapshots(graph: Graph, snapshots: list[dict[str, Any]]) -> list[str]:
    """Add one entity per snapshot, with its retrieval date, the catalogue entry of its source where the guide has
    one and, for the FIP Dashboard, its disclaimer. A snapshot holds the records it supplies (attach_records)."""
    ids = []
    for snapshot in snapshots:
        info = snapshot["snapshot"]
        catalogue = SNAPSHOT_CATALOGUES.get(info["source"], slug(info["source"]))
        source = next(iter(graph.index.get(catalogue, [])), "")
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
    # A list a registry publishes rests on that registry's catalogue entry.
    for prop, catalogue in REGISTRY_SCHEMES.items():
        source = next(iter(graph.index.get(catalogue, [])), "")
        if source in graph.entities:
            graph.entities["#" + TERM_SCHEMES[prop][0]]["isBasedOn"] = ref(source)
    return ids


ANNOTATION_SCHEMES = {"FAIRsharing": "fairsharing", "DataCite": "datacite"}


def annotate_repositories(graph: Graph, repository_ids: list[str], snapshots: list[dict[str, Any]]) -> None:
    """Join each snapshot annotation (FAIRsharing, DataCite) to the repository it names, by re3data record or else
    by address, as that registry's record about the repository: a FAIRsharing record with its DOI and name, a
    DataCite record with its repository ID. The repository keeps the FAIRsharing DOI among its identifiers and the
    DataCite repository where the Guide names none, and rests on the record. An annotation adds no repository of its
    own; one that names no listed repository is left out."""
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
        scheme = ANNOTATION_SCHEMES.get(snapshot["snapshot"]["source"])
        for row in snapshot.get("annotation", []):
            entity = (
                by_re3data.get(row["re3data"]) if row.get("re3data") else by_address.get(bare_url(row.get("url", "")))
            )
            if entity is None or scheme is None or not row.get(scheme):
                continue
            record = {
                "@id": registry_record_key(scheme, row[scheme]),
                "@type": CATALOG_RECORD,
                "identifier": row[scheme],
                "isPartOf": ref(snapshot_id(snapshot)),
                "isBasedOn": ref(snapshot_id(snapshot)),
                "primaryTopic": ref(entity["@id"]),
            }
            if scheme == "fairsharing":
                doi = f"https://doi.org/{row['fairsharing']}"
                record |= {"name": row.get("fairsharingName"), "sameAs": ref(doi)}
                if doi not in ids_of(entity.get("sameAs")):
                    entity["sameAs"] = as_list(entity.get("sameAs")) + [ref(doi)]
            elif not entity.get("dataciteRepository"):
                entity["dataciteRepository"] = row["datacite"]
            graph.add(record)
            if record["@id"] not in ids_of(entity.get("isBasedOn")):
                append_ref(entity, "isBasedOn", record["@id"])


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
                "content": {name: record[name] for name in fields if name in record and name != "mainContact"}
                | ({"mainContact": True} if record.get("mainContactPresent") else {}),
            }
            for record in snapshot.get("record", [])
            if nkr_status(record.get("status")) is not None
        ],
    }


def build_repositories(
    graph: Graph,
    curated: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    resources: list[dict[str, Any]],
    records: list[dict[str, Any]] | None = None,
) -> list[str]:
    """List repositories by meaning, regardless of source; a registry is a resource, listed with the resources, whose
    identities are indexed beside the repositories'. Reviewed record annotations join
    registry identities without changing a snapshot's facts or inferring identity from a similar host or name.
    Each registry's row stays that registry's record about the thing, and the catalogue lists the thing once, with
    the winning values: what the curated entry states, then NKR's name, kind, dated status, keywords and address,
    then the first registry that states a fact, in the order of RECORD_SCHEMES."""
    records = records or []
    annotations = {item["re3data"]: item for item in records if item.get("re3data")}
    merged: dict[str, dict[str, Any]] = {}
    keys: dict[str, str] = {}
    addresses: dict[str, set[str]] = {}
    order: list[str] = []
    nkr_owners: dict[str, str] = {}
    nkr_statuses: dict[str, str] = {}

    def merge_into(existing: dict[str, Any], entity: dict[str, Any]) -> None:
        for prop, value in entity.items():
            if prop in ("isBasedOn", "sameAs", "alternateIdentifier"):
                existing[prop] = as_list(existing.get(prop)) + [
                    item for item in as_list(value) if item not in as_list(existing.get(prop))
                ]
            elif prop not in existing or existing[prop] in (None, [], ""):
                existing[prop] = value

    registry_rows: list[tuple[str, dict[str, Any]]] = []
    from_resources = [
        {key: resource[key] for key in ("id", "name", "url", "status", "asOf") if key in resource}
        | resource["repository"]
        | {"resource": f"#resource-{resource['id']}"}
        for resource in resources
        if resource.get("repository")
    ]
    sources = [(GUIDE_SELECTION, curated + from_resources)]
    for snapshot in snapshots:
        sources.append((snapshot_id(snapshot), snapshot.get("repository", [])))

    def merge_source(based_on: str, repositories: list[dict[str, Any]]) -> None:
        nonlocal keys, addresses
        for source_record in repositories:
            is_nkr = based_on == "#snapshot-nkr"
            if is_nkr:
                record_key = registry_record_key("nkr", source_record["nkr"])
            elif based_on == "#snapshot-re3data":
                # The row is re3data's record; the thing rests on it, and the record keeps re3data's own values.
                record_key = registry_record_key("re3data", source_record["re3data"])
                registry_rows.append((record_key, source_record))
            else:
                record_key = based_on
            repository = source_record if is_nkr else source_record | annotations.get(source_record.get("re3data"), {})
            record_keys = {repository_key(repository)}
            if repository.get("nkr"):
                record_keys.add("nkr:" + repository["nkr"])
            address = bare_url(repository.get("url"))
            if is_nkr:
                record_keys = nkr_match_keys(repository)
            matching = {keys[key] for key in record_keys if key in keys}
            if is_nkr and address:
                matching.update(addresses.get(address, set()))
            if is_nkr and len(matching) > 1:
                names = ", ".join(sorted(str(merged[key]["_content_id"]) for key in matching))
                raise ContentError(f"NKR {repository['nkr']} ({repository['name']}) reaches different entries: {names}")
            key = next((key for key in order if key in matching), repository_key(repository))
            if is_nkr:
                if key in nkr_owners:
                    raise ContentError(
                        f"NKR records {nkr_owners[key]} and {repository['nkr']} reach the same entry: "
                        f"{merged[key]['_content_id']}"
                    )
                nkr_owners[key] = repository["nkr"]
                nkr_statuses[key] = repository["nkrStatus"]
            # A non-NKR record may connect existing keys; preserve the earliest component's facts.
            for other in [value for value in order if value in matching and value != key]:
                merge_into(merged[key], merged.pop(other))
                order.remove(other)
                keys = {name: key if value == other else value for name, value in keys.items()}
                addresses = {
                    name: {key if value == other else value for value in values} for name, values in addresses.items()
                }
            entity = repository_entity(repository, record_key)
            if key in merged:
                merge_into(merged[key], entity)
            else:
                entity["@id"] = repository.get("resource") or f"#repository-{repository['id']}"
                entity["_content_id"] = repository["id"]
                entity["_resource"] = bool(repository.get("resource"))
                merged[key] = entity
                order.append(key)
            keys.update({name: key for name in record_keys})
            for source_address in {address, bare_url(source_record.get("url"))} - {""}:
                addresses.setdefault(source_address, set()).add(key)
            if is_nkr:
                merged[key]["_nkr"] = {
                    prop: value
                    for prop, value in entity.items()
                    if prop in ("name", "repositoryKind", "serviceStatus", "statusAsOf", "keywords", "url")
                    and value not in (None, [], "")
                }

    for based_on, repositories in sources:
        merge_source(based_on, repositories)

    # FIP-only entries already exist in the graph. Index them as separate components
    # before NKR looks up addresses, preserving other sources' reviewed joins.
    existing = list(merged.values()) + [
        graph.entities[f"#resource-{resource['id']}"]
        for resource in resources
        if resource.get("repository") or resource.get("type") == "registry"
    ]
    linked = {
        item["@id"].removeprefix(FIP_DASHBOARD)
        for entity in existing
        for item in as_list(entity.get("sameAs"))
        if isinstance(item, dict) and item.get("@id", "").startswith(FIP_DASHBOARD)
    }
    dashboard_ids = []
    dashboard_annotations = {item["fipDashboard"]: item for item in records if item.get("fipDashboard")}
    for snapshot in snapshots:
        for record in snapshot.get("resource", []):
            handle = alternate_id(record, "fip-dashboard")
            if record.get("type") != "repository" or handle in linked:
                continue
            entity_id = f"#fer-{record['id']}"
            entity = graph.entities[entity_id]
            functions = dashboard_annotations.get(handle, {}).get("functions", [])
            if functions:
                entity["repositoryFunction"] = refs([f"#rfunction-{value}" for value in functions])
            # A reviewed kind is the Guide's classification of the thing the record founds, not the Dashboard's.
            kind = dashboard_annotations.get(handle, {}).get("kind")
            if kind:
                entity.setdefault(PRECEDENCE, {})["repositoryKind"] = ref(f"#rkind-{kind}")
            key = "fip-dashboard:" + str(handle)
            merged[key] = entity | {"_content_id": record["id"], "_resource": True}
            keys[key] = key
            address = bare_url(entity.get("url"))
            if address:
                addresses.setdefault(address, set()).add(key)
            order.append(key)
            dashboard_ids.append(entity_id)

    for snapshot in snapshots:
        merge_source(snapshot_id(snapshot), nkr_repositories(snapshot))

    component_ids = {key: entity["@id"] for key, entity in merged.items()}
    native_statuses = {component_ids[key]: status for key, status in nkr_statuses.items()}
    # NKR's own values, which its record keeps while the thing takes the winning ones.
    nkr_values = {component_ids[key]: dict(merged[key].get("_nkr", {})) for key in nkr_owners}
    graph.repository_keys = {name: {component_ids[key]} for name, key in keys.items() if name.startswith("nkr:")}
    graph.repository_keys.update(
        {"url:" + address: {component_ids[key] for key in components} for address, components in addresses.items()}
    )
    repository_ids = []
    for key in order:
        entity = merged[key]
        overrides = entity.pop("_nkr", {})
        entity.update(overrides)
        content_id = entity.pop("_content_id")
        if entity.pop("_resource"):
            is_dashboard = entity["@id"] in dashboard_ids
            if is_dashboard and not overrides:
                continue
            # The resource's entity takes the repository facts it does not state itself. A repository only the FIP
            # Dashboard knows takes them, NKR's precedence among them, on the thing its record founds
            # (attach_records), so the dashboard's record keeps its own values.
            resource = graph.entities[entity["@id"]]
            target = resource.setdefault(PRECEDENCE, {}) if is_dashboard else resource
            target.update(overrides)
            for prop in ("repositoryKind", "repositoryFunction", "keywords", "isBasedOn", "dataciteRepository"):
                if entity.get(prop) and not resource.get(prop) and not target.get(prop):
                    target[prop] = entity[prop]
            for source in as_list(entity.get("isBasedOn")):
                if source not in as_list(resource.get("isBasedOn")) + as_list(target.get("isBasedOn")):
                    append_ref(target, "isBasedOn", source["@id"])
            added = [item for item in as_list(entity.get("sameAs")) if item not in as_list(resource.get("sameAs"))]
            if is_dashboard:
                if added:
                    target["sameAs"] = as_list(target.get("sameAs")) + added
            else:
                resource["sameAs"] = as_list(resource.get("sameAs")) + added
                if not resource["sameAs"]:
                    del resource["sameAs"]
            if not is_dashboard:
                repository_ids.append(entity["@id"])
            continue
        repository_ids.append(graph.add({"@id": entity.pop("@id"), **entity}, content_id))

    annotate_repositories(graph, repository_ids, snapshots)
    for entity_id, values in nkr_values.items():
        handle = next(owner for key, owner in nkr_owners.items() if component_ids[key] == entity_id)
        graph.add(
            {
                "@id": registry_record_key("nkr", handle),
                "@type": CATALOG_RECORD,
                "identifier": handle,
                **values,
                "isPartOf": ref("#snapshot-nkr"),
                "isBasedOn": ref("#snapshot-nkr"),
                "primaryTopic": ref(entity_id),
            }
        )

    # A registry is a resource the catalogue lists with the resources; its identities are indexed here too, so a
    # registry's own records join it as they join a repository.
    registries = [
        f"#resource-{resource['id']}"
        for resource in resources
        if resource.get("type") == "registry" and f"#resource-{resource['id']}" not in repository_ids
    ]
    repository_ids.extend(dashboard_ids)

    # re3data's record of each repository it lists, about the thing that rests on it, with re3data's own values.
    topics = {
        source: entity_id
        for entity_id in repository_ids
        for holder in (graph.entities[entity_id], graph.entities[entity_id].get(PRECEDENCE, {}))
        for source in ids_of(holder.get("isBasedOn"))
    }
    for record_key, row in registry_rows:
        own = repository_entity(row, "#snapshot-re3data")
        graph.add(
            {
                "@id": record_key,
                "@type": CATALOG_RECORD,
                "identifier": row["re3data"],
                "name": text(row["name"]),
                "url": row.get("url"),
                "repositoryKind": own["repositoryKind"],
                "keywords": own["keywords"],
                "inLanguage": own["inLanguage"],
                "sameAs": own["sameAs"],
                "isPartOf": ref("#snapshot-re3data"),
                "isBasedOn": ref("#snapshot-re3data"),
                "primaryTopic": ref(topics[record_key]),
            }
        )
    for entity_id in repository_ids + registries:
        entity = graph.entities[entity_id]
        holder = entity.get(PRECEDENCE, entity)
        if (
            holder.get("serviceStatus", entity.get("serviceStatus"))
            in [ref("#status-" + value) for value in NON_DEPOSIT_STATUSES]
            or native_statuses.get(entity_id) == NKR_PILOT_NOT_ACCEPTING
        ):
            holder["acceptsDeposits"] = False
        else:
            holder.pop("acceptsDeposits", None)
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
            "name": "Repositories",
            "hasPart": refs(repository_ids),
        }
    )
    return repository_ids


KNAV_REGISTRY = "knav-tools"  # the life-cycle model of the KNAV catalogue's steps (content/lifecycle/)


def build_knav_tools(graph: Graph, content: dict[str, Any]) -> None:
    """The tools of the KNAV Data Management Tools Catalogue snapshot, each with its life-cycle steps, discipline
    groups and the catalogue's licence. A tool that a curated entry (`knav`) or a record annotation names is that
    entry: its record says so in `sameAs` and the catalogue lists the entry once."""
    snapshot = next((item for item in content["snapshots"] if item.get("tool")), None)
    if snapshot is None:
        return
    info = snapshot["snapshot"]
    standing: dict[str, str] = {}
    for entry in content["resources"] + content["repositories"] + content["sources"]:
        if entry.get("knav") and graph.index.get(entry["id"]):
            standing[entry["knav"]] = graph.index[entry["id"]][0]
    for item in (content.get("infrastructures") or {}).get("infrastructure", []):
        if item.get("knav"):
            standing[item["knav"]] = f"#infrastructure-{item['id']}"
        for entry in item.get("nodeOf", []) + item.get("eric", []):
            if entry.get("knav"):
                standing[entry["knav"]] = f"#european-ri-{slug(entry['name'])}"
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
    for tool in snapshot["tool"]:
        graph.add(
            {
                "@id": f"#knav-{tool['id']}",
                "@type": "CreativeWork",
                "identifier": tool["id"],
                "name": tool["name"],
                "description": {"@value": tool["description"], "@language": "en"},
                "url": tool.get("url"),
                "lifecycleStage": refs([lifecycle_stage_id(KNAV_REGISTRY, step) for step in tool["steps"]]),
                "discipline": [status_term(graph, "discipline", group) for group in tool.get("disciplines", [])],
                "license": info.get("license"),
                "isBasedOn": ref(snapshot_id(snapshot)),
                "sameAs": ref(standing[alternate_id(tool, "knav")]) if alternate_id(tool, "knav") in standing else None,
                # The catalogue lists tools: a thing only it knows is a tool by the Guide's own types, while the
                # record keeps KNAV's values.
                PRECEDENCE: {"guideType": ref("#rtype-tool")},
            },
            f"knav.{alternate_id(tool, 'knav')}",
        )


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
    """The large research infrastructures of the national roadmap: each with its names, hosting institution,
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

    def european_ri(name: str) -> dict[str, Any]:
        """A European research infrastructure, by its name in the roadmap. A node of it and an ERIC of the same name
        are one infrastructure, so both relations point to one entity with both facts."""
        entity_id = f"#european-ri-{slug(name)}"
        if entity_id not in graph.entities:
            graph.add({"@id": entity_id, "@type": "Organization", "name": name})
        # The roadmap names it, so the Guide describes it whatever registry also records it.
        if based_on:
            graph.entities[entity_id].setdefault("source", ref(based_on[0]))
        return graph.entities[entity_id]

    def node_of(name: str, status: str) -> str:
        entity = european_ri(name)
        entity.setdefault("esfriStatus", ref(f"#esfri-{status}"))
        return entity["@id"]

    def eric(name: str, since: str) -> str:
        entity = european_ri(name)
        entity.setdefault("czechMembershipSince", since)
        return entity["@id"]

    for item in items:
        entity_id = f"#infrastructure-{item['id']}"
        item_sources = graph.resolve(
            [source for source in (info.get("source"), item.get("namesSource", info.get("namesSource"))) if source]
        )
        collection_sources.extend(source for source in item_sources if source not in collection_sources)
        for row in item.get("operates", []):
            target = catalogue_entry(graph, row)
            if target is None:
                raise ContentError(f"infrastructure {item['id']}: operates an unknown catalogue entry {row}")
            graph.entities[target]["operatedBy"] = ref(entity_id)
            graph.entities[target]["operatedBySource"] = ref(row["evidence"]) if row.get("evidence") else None
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
                    "nationalNodeOf": refs([node_of(row["name"], row["esfri"]) for row in item.get("nodeOf", [])]),
                    "memberOf": refs([eric(row["name"], row["entry"]) for row in item.get("eric", [])]),
                    # The FIP of the infrastructure's community in the FIP Dashboard snapshot, where it has one.
                    "subjectOf": ref(graph.index["fip:" + item["fip"]][0]) if item.get("fip") else None,
                    "roadmapLocator": item.get("annex1"),
                    "source": refs(item_sources),
                },
                f"infrastructure:{item['id']}",
            )
        )
    graph.add(
        {
            "@id": "#infrastructures",
            "@type": "CreativeWork",
            "name": "Large research infrastructures",
            # The roadmap's list names organisations, which are no part of a creative work: it is about them.
            "about": refs(ids),
            "isBasedOn": refs(collection_sources),
            "dateModified": iso(info["checked"]) if info.get("checked") else None,
        }
    )
    return ["#infrastructures", *ids]


def build_node(graph: Graph, data: dict[str, Any]) -> list[str]:
    """The EOSC CZ Node as a service platform, with one DCAT qualified relation per onboarded entry. Each
    relationship is also a CreativeWork: it is the dated evidence statement whose charter its citation names."""
    node = data.get("node")
    if not node:
        return []
    sources = graph.resolve(node.get("sources", []))
    operator = f"#infrastructure-{node['operator']}"
    memberships = []
    for member in data.get("member", []):
        target = catalogue_entry(graph, member)
        if target is None:
            raise ContentError(f"node member {member}: an unknown catalogue entry")
        relation_id = f"#node-membership-{target.removeprefix('#')}"
        graph.add(
            {
                "@id": relation_id,
                "@type": ["dcat:Relationship", "CreativeWork"],
                "relation": ref(target),
                "hadRole": ref(f"#noderole-{member['role']}"),
                "nodeMilestone": member.get("milestone"),
                "statusAsOf": iso(node["checked"]),
                "citation": refs(sources[:1]),
                "description": member.get("locator"),
            }
        )
        memberships.append(relation_id)
    graph.add(
        {
            "@id": "#eosc-cz-node",
            "@type": "Service",
            "identifier": node["id"],
            "resourceType": ref("#rtype-service"),
            "name": node["name"],
            "url": node.get("url"),
            "provider": ref(operator) if operator in graph.entities else None,
            "nodeState": status_term(graph, "nodeState", node.get("state")),
            "statusAsOf": iso(node["checked"]),
            "nodeStateSince": iso(node["stateDate"]) if node.get("stateDate") else None,
            "source": refs(sources),
            "qualifiedRelation": refs(memberships),
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
                "isBasedOn": based_on,
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
                "coverage": status_term(graph, "coverage", resource.get("scope")),
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
                    "declarationStatus": status_term(graph, "declarationStatus", declaration.get("status")),
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
                "fipStatus": status_term(graph, "fipStatus", fip.get("status")),
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
            "@id": "#fips",
            "@type": "CreativeWork",
            "name": "FAIR Implementation Profiles (FIP Dashboard)",
            "hasPart": refs(fip_ids),
        }
    )
    return ["#fips"]


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
        term_id = f"#term-{term['id']}"
        definition_id = term_id + "#definition"
        if term.get("definition"):
            # A quoted definition is a work of its own, under the term's IRI: its text, licence and source belong to
            # that work, not to the DefinedTerm, whose domain schema.org does not admit for licence or citation.
            graph.add(
                {
                    "@id": definition_id,
                    "@type": "CreativeWork",
                    "description": text({term.get("definitionLanguage", "cs"): term["definition"]})
                    if isinstance(term.get("definition"), str)
                    else text(term.get("definition")),
                    "license": ref(info["license"]) if info.get("license") else None,
                    # schema:citation also admits text, so the source page is cited by its address, not as a work
                    # whose own class is unknown.
                    "citation": term.get("url"),
                }
            )
        graph.add(
            {
                "@id": term_id,
                "@type": "DefinedTerm",
                "identifier": term["id"],
                "termCode": alternate_id(term, "heslar"),
                "subjectOf": refs(
                    [f"#clause-{item['id']}" for item in clauses or [] if str(term["id"]) in item.get("terms", [])]
                ),
                "name": text(term["label"]),
                "definitionPart": ref(definition_id) if term.get("definition") else None,
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
                "citation": (
                    [test.get("record") or champion["testRecord"].format(id=native), champion["documentation"]]
                    if champion.get("testRecord") and champion.get("documentation")
                    else []
                ),
                "about": ref(principle_iri(test["principle"])) if test.get("principle") else None,
                # The metric the test implements, as its own FTR record at FAIR Champion names it.
                "isImplementationOf": ref(test["metric"]) if test.get("metric") else None,
                "healthStatus": status_term(graph, "healthStatus", test.get("health")),
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
        test_id = "#test-" + test["id"]
        test_ids.append(test_id)
        graph.add(
            {
                "@id": test_id,
                "@type": "CreativeWork",
                "identifier": test["id"],
                "name": text(test["label"]),
                "description": text(test["description"]),
                "url": test["script"],
                "isImplementationOf": ref(question_id),
                # A local test is about the principles its question measures.
                "about": question.get("inDimension"),
                "citation": question.get("citation"),
                "hasPart": refs(files),
                "subjectOf": ref(doc_id),
                "entryPoint": test["entryPoint"],
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
                        "mappingCoverage": status_term(graph, "mappingCoverage", mapping["coverage"]),
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
                    # A criterion the Guide invokes through the provider's API is an FTR test; one an imported
                    # report states its results against is the provider's FTR metric.
                    "additionalType": FTR_TEST if provider.get("mode") == "service" else FTR_METRIC,
                    "identifier": metric["id"],
                    "name": {"@language": "en", "@value": metric["name"]},
                    "alternateName": text(metric.get("label")),
                    "about": ref(principle_iri(metric["principle"])),
                    "isPartOf": ref(f"#resource-{provider['resource']}"),
                    "url": invocation or provider.get("form"),
                    "citation": documentation,
                    "reviewedVersion": reviewed,
                    "hasPart": refs(mapping_ids),
                },
                f"provider:{provider['id']}.{metric['id']}",
            )
    return criteria


WEB_APPLICATION = SCHEMA + "WebApplication"


def build_pages(graph: Graph, pages: list[dict[str, Any]]) -> list[str]:
    page_ids = []
    for page in pages:
        page_id = f"#page-{page['id']}"
        page_ids.append(page_id)
        section_ids = []
        for number, section in enumerate(page.get("section", []), start=1):
            # A section's own id is its fragment, so reordering a page moves no IRI; its place is only its position.
            if not section.get("id"):
                raise ContentError(f"page '{page['id']}': section {number} has no id")
            section_id = f"{page_id}-{section['id']}"
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
                    {
                        "@id": action_id,
                        "@type": "Action",
                        "name": text(action["label"]),
                        "target": action_target(action["href"]),
                    }
                )
        graph.add(
            {
                "@id": page_id,
                "@type": "CreativeWork",
                "identifier": page["id"],
                "additionalType": WEB_APPLICATION if page.get("helper") else None,  # a type (type_records)
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
                # A clause or a cited work, by its address, which becomes its IRI once identities are published.
                "object": refs(action.get("objects", [])),
                "endTime": iso(action["endTime"]),
                "actionStatus": ref("http://schema.org/CompletedActionStatus"),
            },
            f"action:{action['id']}",
        )
        graph.results[action_id] = list(action.get("results", []))
    return action_ids


# The registries whose records describe things, by the fragment a record takes under its thing, in the order a thing
# lists its records: the first registry that records a thing the Guide does not describe founds it, and a fact
# neither the curated entry nor NKR states comes from the first registry that states it.
RECORD_SCHEMES = ("re3data", "fip-dashboard", "fip-dashboard-organization", "knav", "nkr", "fairsharing", "datacite")
# A registry's record about a thing, by the family of its build key, and the fragment it takes under the thing.
REGISTRY_RECORDS = (
    ("#knav-", "knav"),
    ("#fer-", "fip-dashboard"),
    ("#fd-org-", "fip-dashboard-organization"),
    *((registry_record_key(scheme, ""), scheme) for scheme in ("nkr", "re3data", "fairsharing", "datacite")),
)
# The facts other registries win for a thing a registry record founds, held on that record until it founds the thing.
PRECEDENCE = "_precedence"
# What a thing only a registry knows carries itself: its identity, name, address and the facts lists filter on.
FOUNDED_FACTS = (
    "@type",
    "additionalType",
    "identifier",
    "name",
    "alternateName",
    "url",
    "resourceType",
    "guideType",
    "repositoryKind",
    "repositoryFunction",
    "serviceStatus",
    "statusAsOf",
    "acceptsDeposits",
    "lifecycleStage",
    "discipline",
    "sameAs",
)


def attach_records(graph: Graph, base: str) -> None:
    """Make each registry record a `dcat:CatalogRecord` about the one thing it describes. A record of a thing the
    Guide describes already sits under it (`<thing>#knav`); a thing only a registry knows is founded by its record:
    the thing keeps its identity, name, address and filter facts, and the registry's own record, with its text and
    attribution, moves under it. Each record names its thing and rests on the snapshot that supplied it, which lists
    the record; the thing does not name its records again."""
    for key, published in list(graph.published.items()):
        scheme = next((name for prefix, name in REGISTRY_RECORDS if key.startswith(prefix)), None)
        if scheme is None or not published.startswith(base) or published not in graph.entities:
            continue
        if published.partition("#")[2] not in ("", scheme):
            continue  # a part of a record, such as a FIP Dashboard verification, is not itself a record
        thing = published.split("#")[0]
        if "#" in published:
            record = graph.entities[published]
            record.pop(PRECEDENCE, None)
        else:
            record = graph.entities.pop(published)
            founded = {"@id": published} | {
                prop: record[prop] for prop in FOUNDED_FACTS if prop in record and prop != "@id"
            }
            for prop, value in record.pop(PRECEDENCE, {}).items():
                if prop in ("isBasedOn", "sameAs"):
                    founded[prop] = as_list(founded.get(prop)) + [
                        item for item in as_list(value) if item not in as_list(founded.get(prop))
                    ]
                else:
                    founded[prop] = value
            record = record | {"@id": f"{published}#{scheme}"}
            # The build key keeps naming the thing, which its content row describes; the record moves under it.
            graph.entities[published] = founded
            graph.entities[record["@id"]] = record
        # A record is a catalogue record and a creative work whatever its registry describes, never of its thing's
        # class, so selecting a class finds things and not records. How the registry classifies the thing, such as a
        # FIP Dashboard resource's FIP class or a repository kind, is the record's own classification.
        record["@type"] = ["CreativeWork", CATALOG_RECORD]
        classification = [
            *(ref(value) for value in as_list(record.pop("additionalType", None)) if isinstance(value, str)),
            *as_list(record.pop("repositoryKind", None)),
        ]
        if classification:
            record["classification"] = classification if len(classification) > 1 else classification[0]
        # A record is about its thing, not the same as it: primaryTopic replaces an earlier sameAs to the thing.
        same = [
            item for item in as_list(record.get("sameAs")) if not (isinstance(item, dict) and item.get("@id") == thing)
        ]
        if same:
            record["sameAs"] = same if len(same) > 1 else same[0]
        else:
            record.pop("sameAs", None)
        record["primaryTopic"] = ref(thing)
    # A record names its thing and rests on its snapshot, which holds it; the thing does not name its records again
    # and rests only on what is not one of them, such as the Guide's selection.
    for record_id, record in list(graph.entities.items()):
        thing = graph.entities.get(next(iter(ids_of(record.get("primaryTopic"))), ""))
        if thing is None or CATALOG_RECORD not in as_list(record.get("@type")):
            continue
        snapshot = next(source for source in ids_of(record.get("isBasedOn")) if source.startswith("#snapshot-"))
        append_ref(graph.entities[snapshot], "hasPart", record_id)
        others = [source for source in ids_of(thing.get("isBasedOn")) if not source.startswith(thing["@id"] + "#")]
        if others:
            thing["isBasedOn"] = refs(list(dict.fromkeys(others)))
        else:
            thing.pop("isBasedOn", None)
    # An author, provider or publisher is the thing, never the registry's record about it. Snapshot builders use
    # record IRIs before the one-thing join runs, so resolve every such agent after all primaryTopic statements exist.
    for entity in graph.entities.values():
        for prop in ("author", "provider", "publisher"):
            resolved = []
            for target in ids_of(entity.get(prop)):
                record = graph.entities.get(target, {})
                resolved.append(next(iter(ids_of(record.get("primaryTopic"))), target))
            if resolved != ids_of(entity.get(prop)):
                entity[prop] = refs(resolved) if len(resolved) > 1 else ref(resolved[0])
            for target in resolved:
                # One real-world thing can be both a described service and the organisation that provides or authors
                # a work. State that role explicitly; catalogue kind selection still keeps it out of organisations.
                thing_entity = graph.entities.get(target)
                if thing_entity is not None and not {"Organization", "Person"} & set(
                    as_list(thing_entity.get("@type"))
                ):
                    thing_entity["@type"] = [*as_list(thing_entity.get("@type")), "Organization"]


# Established classes written in their compact form, as the crate's context names them.
CLASS_PREFIXES = (
    (SCHEMA, ""),
    (FTR, "ftr:"),
    (FIP_TERMS, "fip:"),
    (PROV, "prov:"),
    (DCAT, "dcat:"),
    (DCMITYPE, "dcmitype:"),
)


def compact_class(iri: str) -> str:
    return next((prefix + iri.removeprefix(base) for base, prefix in CLASS_PREFIXES if iri.startswith(base)), iri)


def has_type(entity: dict[str, Any], name: str) -> bool:
    return name in as_list(entity.get("@type"))


def parts_stated_once(graph: Graph) -> None:
    """State each part-whole relation in one direction. A whole names its parts, the fragments under its own IRI, with
    hasPart, as a snapshot names its records and the crate's root its files; a record names the record it belongs to
    with isPartOf, as an advice item its station and a correspondence its crosswalk."""
    for whole_id, whole in graph.entities.items():
        kept = []
        for part_id in ids_of(whole.get("hasPart")):
            part = graph.entities.get(part_id)
            if part is None or whole_id not in ids_of(part.get("isPartOf")):
                kept.append(part_id)
                continue
            if part_id.startswith(whole_id + "#") or whole_id.startswith("#snapshot-") or whole_id == "./":
                rest = [item for item in ids_of(part.get("isPartOf")) if item != whole_id]
                if rest:
                    part["isPartOf"] = refs(rest) if len(rest) > 1 else ref(rest[0])
                else:
                    part.pop("isPartOf")
                kept.append(part_id)
        if "hasPart" in whole and len(kept) < len(ids_of(whole["hasPart"])):
            if kept:
                whole["hasPart"] = refs(kept) if len(kept) > 1 else ref(kept[0])
            else:
                whole.pop("hasPart")


def terms_name_their_sets(graph: Graph) -> None:
    """State a term's membership once, by the term: a set does not list its terms, and its order is each term's
    position among them, taken from the set's list or the term's own position."""
    for entity in graph.entities.values():
        for position, term_id in enumerate(ids_of(entity.pop("hasDefinedTerm", None)), 1):
            term = graph.entities.get(term_id)
            if term is not None and "termPosition" not in term:
                term["termPosition"] = term.pop("position", position)
    for entity in graph.entities.values():
        if "DefinedTerm" in as_list(entity.get("@type")) and "position" in entity:
            entity["termPosition"] = entity.pop("position")


def type_records(graph: Graph, base: str) -> set[str]:
    """Write every class a node has as its type: a class its builder named as an additional type, and the class that
    selects its kind (KIND_CLASSES), so a consumer selects a kind by class and never reads a type from a string.
    Return the schema.org classes written by name, which the crate's context declares, since RO-Crate's context names
    only some of them."""
    named: set[str] = set()
    for entity_id, entity in graph.entities.items():
        classes = [compact_class(value) for value in as_list(entity.pop("additionalType", None))]
        named |= {name for name in classes if ":" not in name and not name.startswith("http")}
        if entity_id.startswith(base) and "#" not in entity_id:
            kind, *rest = entity_id.removeprefix(base).split("/")
            whole = len(rest) == 1 or kind == "tests"
            classes += KIND_CLASSES.get(kind, ()) if whole else SCOPED_KIND_CLASSES.get(kind, ())
        if classes:
            types = list(dict.fromkeys(as_list(entity.get("@type")) + classes))
            entity["@type"] = types[0] if len(types) == 1 else types
    return named


def records_by_thing(entities: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Each thing's registry records, which name it with primaryTopic."""
    found: dict[str, list[str]] = {}
    for record_id, record in entities.items():
        if CATALOG_RECORD in as_list(record.get("@type")):
            for thing in ids_of(record.get("primaryTopic")):
                found.setdefault(thing, []).append(record_id)
    return found


def founding_record(thing: dict[str, Any], records: dict[str, list[str]]) -> str | None:
    """The registry record that founds a thing only registries know: the first of its records, in the order of
    RECORD_SCHEMES, when the thing rests on nothing else. None for a thing the Guide's own content describes.
    `records` is records_by_thing of the graph."""
    own = records.get(thing["@id"], [])
    if not own or thing.get("isBasedOn") or thing.get("source"):
        return None
    return min(own, key=lambda source: RECORD_SCHEMES.index(source.rsplit("#", 1)[1]))


def attach_results(graph: Graph, base: str) -> None:
    """Each provenance action's results, which name items by address (`stations/plan`, `advice/plan.*`,
    `callouts/sensitive-data#steward`), as the published records and parts they match. `guide` names the Guide's
    metadata, and `*` a change of the Guide as a whole, such as a structural migration: both record the Guide itself,
    so a record's list of changes holds only the changes made to it."""
    addresses = {entity_id: entity_id.removeprefix(base) for entity_id in graph.entities if entity_id.startswith(base)}
    for action_key, patterns in graph.results.items():
        matched: list[str] = []
        for pattern in patterns:
            if pattern in ("guide", "*"):
                matched.append("./")
            else:
                matched += [entity_id for entity_id, address in addresses.items() if result_covers(pattern, address)]
        action = graph.entities[graph.published.get(action_key, action_key)]
        if matched:
            action["result"] = refs(list(dict.fromkeys(matched)))


def result_covers(pattern: str, address: str) -> bool:
    """Whether a provenance result names an address: exactly, or as a prefix with a trailing `*`, which matches
    records (`advice/plan.*`) and matches parts only where the pattern names a part (`callouts/sensitive-data#*`).
    `*` alone names the Guide as a whole, and so covers every item."""
    if pattern == "*":
        return True
    if not pattern.endswith("*"):
        return address == pattern
    prefix = pattern[:-1]
    return address.startswith(prefix) and ("#" in prefix or "#" not in address)


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
                "modelKind": status_term(graph, "modelKind", kind),
                "position": position,
                "name": text(item["name"]),
                "description": text(item["description"]),
                "inDefinedTermSet": ref(model_id),
                "source": refs(graph.resolve([item.get("source", model["source"])])),
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
                "modelKind": status_term(graph, "modelKind", "example"),
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
            # Layers and seams belong to the set, not to a CreativeWork; only the model's works are its parts.
            "hasPart": refs(parts[len(terms) :]),
            "hasDefinedTerm": refs(terms),
            "workExample": ref("#model-worked-example") if model.get("workedExample") else None,
        },
        f"model:{model['id']}",
    )
    return [model_id]


def attach_associations(graph: Graph, data: dict[str, Any], base: str) -> None:
    """Each explicitly authored association, on the record its target names by address once identities are
    published: the layers it names and those of the seams it names, and the seams."""
    seam_layers = {item["id"]: item["layers"] for item in data.get("seam", [])}
    for association in data.get("association", []):
        entity = graph.entities.get(base + association["target"])
        if entity is None:
            raise ContentError(f"model association names no record: '{association['target']}'")
        seams = association.get("seams", [])
        layers = dict.fromkeys(association.get("layers", []) + [layer for seam in seams for layer in seam_layers[seam]])
        for key in layers:
            append_ref(entity, "implementationLayers", graph.published[f"#layer-{key}"])
        for key in seams:
            append_ref(entity, "implementationSeams", graph.published[f"#seam-{key}"])


# The life-cycle model whose stages the path follows: a station's `lifecycleStage` names one of its stages.
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
            stage_id = lifecycle_stage_id(model["id"], stage["id"])
            definition_id = stage_id + "#definition"
            graph.add(
                {
                    "@id": definition_id,
                    "@type": "CreativeWork",
                    "description": definition,
                    "citation": refs(graph.resolve([model["source"]])),
                    "license": refs([licences[model["source"]]] if licences.get(model["source"]) else []),
                }
            )
            czech_definition_id = None
            if stage.get("czechDefinition"):
                czech_definition_id = stage_id + "#czech-definition"
                czech_source = model.get("czechSource")
                graph.add(
                    {
                        "@id": czech_definition_id,
                        "@type": "CreativeWork",
                        "description": {"@value": stage["czechDefinition"], "@language": "cs"},
                        "citation": refs(graph.resolve([czech_source])) if czech_source else None,
                        "license": refs([licences[czech_source]] if licences.get(czech_source) else []),
                    }
                )
            stage_ids.append(
                graph.add(
                    {
                        "@id": stage_id,
                        "@type": "DefinedTerm",
                        "identifier": stage["id"],
                        "termCode": stage["id"],
                        "position": position,
                        "name": text(stage["name"]),
                        "definitionPart": ref(definition_id),
                        "nameTranslation": as_list(stage.get("translated")),
                        "descriptionTranslation": ["cs"] if stage.get("translation") else None,
                        "quotedDefinition": ref(czech_definition_id) if czech_definition_id else None,
                        "note": {"@value": stage["note"], "@language": language} if stage.get("note") else None,
                        "inDefinedTermSet": ref(set_id),
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
                    "mappingBasis": status_term(graph, "mappingBasis", item["basis"]),
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
    graph.add({"@id": GUIDE_SELECTION, "@type": "CreativeWork", "name": "The Guide's selection"})
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
    # The vocabularies come first: every status names a term of its scheme, a source's included.
    build_vocabularies(graph, guide_file)
    source_ids = build_sources(graph, content["sources"], organizations, people, names, crosswalk=crosswalk)
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
    if node_ids:
        append_ref(graph.entities["#resources"], "hasPart", node_ids[0])
    build_knav_tools(graph, content)
    callout_ids = build_callouts(graph, content["callouts"], all_lenses)
    test_ids = build_tests(graph, content["live"])
    build_providers(graph, content["live"])
    page_ids = build_pages(graph, content["pages"])
    model_ids = build_model(graph, content.get("model", {}))
    action_ids = build_actions(graph, content["provenance"], people)
    if content.get("model", {}).get("model", {}).get("workedExample"):
        worked = content["model"]["model"]["workedExample"]
        steps = worked["steps"]
        actions = [entity_id for entity_id in steps if entity_id.startswith("actions/")]
        works = [entity_id for entity_id in steps if entity_id not in actions]
        example = graph.entities["#model-worked-example"]
        example["hasPart"] = refs(works)
        # An action is no CreativeWork: the example offers its final revision as an action, after its work steps.
        example["potentialAction"] = refs(actions)

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
            "additionalType": DCMITYPE + "Software",
            "name": "FAIR Data Guide source code",
            # DCM's software class fits a cited work, without pretending the work has schema.org's software-specific
            # properties: the address and manifests are links, and its languages are discovery keywords.
            "url": guide.get("url"),
            "version": guide["version"],
            "keywords": ["JavaScript", "Python", "HTML", "CSS"],
            "dependencyManifest": refs(
                [
                    guide.get("url", "").rstrip("/") + "/blob/HEAD/pyproject.toml",
                    guide.get("url", "").rstrip("/") + "/blob/HEAD/package-lock.json",
                    guide.get("url", "").rstrip("/") + "/blob/HEAD/requirements-dev.txt",
                ]
            ),
            "citation": guide.get("url", "").rstrip("/") + "/blob/HEAD/CITATION.cff",
            "license": ref(LICENSES["MIT"][0]),
            "author": refs([people[person] for person in guide.get("editors", [])]),
            "isPartOf": ref(software_id),
        }
    )
    graph.add(
        {
            "@id": "#guide-help",
            "@type": "WebPage",
            "name": "FAIR Data Guide README",
            "url": guide.get("url", "").rstrip("/") + "/blob/HEAD/README_en.md",
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
            "releaseStatus": status_term(graph, "releaseStatus", build_identity_facts()["status"]),
            "url": guide.get("url"),
            "license": ref(LICENSES["MIT"][0]),
            "author": refs([people[person] for person in guide.get("editors", [])]),
            "runtimePlatform": (
                "Web browser; Python 3.11 or later and the pinned Node.js packages for the build; "
                "Node.js for development checks"
            ),
            "softwareHelp": ref("#guide-help"),
            "hasPart": refs(["#guide-source", "./"]),
            "subjectOf": ref("./"),
        }
    )
    for field in ("publisher", "funder"):
        if guide.get(field) and guide[field] not in organizations:
            raise ContentError(f"guide: unknown {field} organisation '{guide[field]}'")
    graph.add({"@id": "#ai-statement", "@type": "CreativeWork", "text": text(guide.get("aiStatement"))})
    root = {
        "@id": "./",
        "@type": "Dataset",
        "name": text(guide["name"]),
        "description": text(guide["description"]),
        "version": guide["version"],
        "releaseStatus": status_term(graph, "releaseStatus", build_identity_facts()["status"]),
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
        "usageInfo": ref("#ai-statement") if guide.get("aiStatement") else None,
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
    # An agent (a publisher, an operating, hosting or developing organisation) is named by reference to an entity,
    # not by a literal name, once every thing it can be exists.
    founded = {key for key in graph.entities if key.startswith("#fd-org-")} - set(
        organization_record_owners(graph, content)
    )
    things = agent_things(graph, founded)
    agents: list[str] = []
    for entity in list(graph.entities.values()):
        for name_key, agent_key in (
            ("publisherName", "publisher"),
            ("operatorName", "publisher"),
            ("developerName", "attributedTo"),
            ("hostingInstitution", "publisher"),
        ):
            name = name_text(entity.get(name_key))
            if name:
                agents.append(agent_ref(graph, name, things))
                append_ref(entity, agent_key, agents[-1])
            entity.pop(name_key, None)
    placements = identity_projection(graph, content)
    issued = {placement.address for placement in placements.values() if placement.address}
    unknown = sorted({agent for agent in agents if "/" in agent and agent not in issued})
    if unknown:
        raise ContentError("an agent names no record: " + ", ".join(unknown))
    link_texts(graph, reference_targets(content, graph, placements))
    publish_identities(graph, placements, guide["recordBase"])
    attach_associations(graph, content.get("model", {}), guide["recordBase"])
    attach_records(graph, guide["recordBase"])
    attach_results(graph, guide["recordBase"])
    terms_name_their_sets(graph)
    parts_stated_once(graph)
    named_classes = type_records(graph, guide["recordBase"])

    context: dict[str, Any] = {
        term: ESTABLISHED_TERMS.get(term, vocabulary_base + term) for term in [*ESTABLISHED_TERMS, *GUIDE_TERMS]
    }
    context.update((name, vocabulary_base + name) for name in GUIDE_CLASSES)
    context["ftr"] = FTR
    context["fip"] = FIP_TERMS
    context["dcat"] = DCAT
    context["dcmitype"] = DCMITYPE
    context.update((name, SCHEMA + name) for name in sorted(named_classes))
    context["isImplementationOf"] = SIO + "SIO_000233"
    context[CATALOG_RECORD] = DCAT + "CatalogRecord"
    context["publisher"] = DCTERMS + "publisher"
    context["attributedTo"] = PROV + "wasAttributedTo"
    return {"@context": [f"{RO_CRATE}/context", context], "@graph": list(graph.entities.values())}


# ---------------------------------------------------------------------------
# Page blocks


API_COLLECTIONS = tuple(sorted(KINDS))
# Stored-record groups used only by catalogue_addresses to recover an owned record's identity and kind. These are
# not published API paths: cataloguing still distinguishes cited works and organisations before the one projection.
CATALOGUE_RECORD_GROUPS = (
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
# Where API v1's files sit in the site; records are `api/v1/<kind>/<id>.json`, or scoped under that kind.
API_FILES = {
    "health": "api/v1/health.json",
    "description": "openapi.json",
    "docs": "api/",
    "context": "api/v1/context.jsonld",
    "index": "api/v1/index.json",
    "record": "api/v1/{record}.json",
}
# Saved-result revisions 1 to 3 retain this support path; it describes a question and is not an FTR test.
API_FILES["test"] = "api/tests/{id}.json"
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


def catalogue_record_keys(
    entities: dict[str, dict[str, Any]], content: dict[str, Any]
) -> dict[str, list[tuple[str, str]]]:
    """The catalogue records among the built entities, by their build keys, before their identities are published:
    per collection, each record's ID and the entity it describes, in the crate's order. A record ID names a file, so
    it is unique within its collection and safe as a path segment. A FIP Dashboard resource that a curated resource
    stands for is published as that resource; the manual tests of the check questions are added by the API build."""

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
    fers = {
        "#fer-" + row["id"]
        for snapshot in content.get("snapshots", [])
        for row in snapshot.get("resource", [])
        if not (alternate_id(row, "fip-dashboard") and FIP_DASHBOARD + alternate_id(row, "fip-dashboard") in described)
    }
    sources = part_ids("#sources")
    records: dict[str, list[tuple[str, str]]] = {name: [] for name in CATALOGUE_RECORD_GROUPS}
    for entity_id, entity in entities.items():
        if "#" in entity_id[1:]:
            continue  # a part of a record, placed under its whole; never a standalone collection record
        collection = next((name for prefix, name in API_PREFIXES.items() if entity_id.startswith(prefix)), None)
        record = entity.get("identifier")
        if collection == "repositories" and entity.get("@type") != "DataCatalog":
            continue  # the repository kinds, a term set
        if entity_id.removeprefix("#") in CODED_SETS:
            continue  # a coded term set, such as the clause kinds, is a vocabulary whatever its name begins with
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
        elif entity_id.startswith("#item-") and "Question" in as_list(entity.get("@type")):
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
        elif entity_id.startswith("#knav-") and not entity.get("sameAs"):
            # A catalogue tool no entry of the guide stands for, under the catalogue's identifier for it.
            collection, record = "resources", f"knav.{entity['identifier']}"
        if entity_id == "#implementation-model":
            collection, record = "model", entity["identifier"]
        if entity_id == "#eosc-cz-node":
            # The EOSC CZ Node is a service platform the Guide lists as a resource.
            collection, record = "resources", entity["identifier"]
        if collection is None:
            continue
        if not isinstance(record, str) or not API_ID.match(record):
            raise ContentError(f"{entity_id}: no record ID the API can publish under {collection}/ ({record!r})")
        if any(existing == record for existing, _ in records[collection]):
            raise ContentError(f"{entity_id}: two entities share the API record {collection}/{record}")
        records[collection].append((record, entity_id))
    return records


# Every address kind publishes a list under that same kind; sources are resources, and scoped identities stay nested.
API_KIND_COLLECTIONS = {kind: kind for kind in API_COLLECTIONS}


def guide_address(entity_id: str, base: str) -> str | None:
    """The address a published identifier names, `<address>` for a record or `<address>#<fragment>` for its part;
    None for a file, an outside IRI or a crate-local node."""
    return entity_id[len(base) :] if entity_id.startswith(base) else None


def record_address(entity_id: str, base: str) -> str | None:
    """A record's address from its published identifier; None for a part or anything that is not a record."""
    address = guide_address(entity_id, base)
    return address if address and "#" not in address else None


def kind_of(entity_id: str, base: str) -> str | None:
    """The kind of the record an identifier names, or of the record its part belongs to."""
    address = guide_address(entity_id, base)
    return address.split("/", 1)[0] if address else None


def api_records(entities: dict[str, dict[str, Any]], content: dict[str, Any]) -> dict[str, list[tuple[str, str]]]:
    """What the static API publishes, from the published identities: per collection, each record's ID and the entity
    it describes, in the crate's order. A record's collection follows from its kind; a record ID names a file, so it
    is unique within its collection and safe as a path segment. The manual tests of the check questions are added by
    the API build."""
    base = content["guide"]["guide"]["recordBase"]
    records: dict[str, list[tuple[str, str]]] = {name: [] for name in API_COLLECTIONS}
    for entity_id, entity in entities.items():
        address = record_address(entity_id, base)
        if address is None:
            continue
        try:
            kind, scope, identifier = split_address(address)
        except ValueError as error:
            raise ContentError(f"{entity_id}: {error}") from error
        collection = API_KIND_COLLECTIONS.get(kind)
        if collection is None or (kind == "vocabularies" and "DefinedTermSet" not in as_list(entity.get("@type"))):
            continue
        record = "/".join(address.split("/")[1:])
        if not all(API_ID.fullmatch(part) for part in record.split("/")):
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


# The crosswalk between the life-cycle models' stages; its mappings are scoped by it.
CROSSWALK_ID = "lifecycle-stages"
# The scope of the FAIR Champion tests the Guide curates, beside the external evaluators' own resource IDs.
CHAMPION_SCOPE = "fair-champion"
# A published API collection's record kind, where the collection is named by a role rather than by its kind.
COLLECTION_KINDS = {"sources": "resources", "metrics": "questions", "changes": "actions", "terms": "glossary"}


# The kind and scope of the members of the model and life-cycle collections, by the build key's prefix; the rest of
# those collections are the model itself and the life-cycle models and stages.
MEMBER_ROUTES = (
    ("#layer-", "layers", None),
    ("#seam-", "seams", None),
    ("#model-example-", "model-examples", None),
    ("#crosswalk-", "crosswalks", CROSSWALK_ID),
    ("#lifecycle-crosswalk", "crosswalks", None),
)


def record_route(
    entity_id: str, entity: dict[str, Any], collection: str, repositories: set[str]
) -> tuple[str, str | None]:
    """The kind and scope a published record is issued under, from what it is rather than how it is classified."""
    if entity_id in repositories:
        # A registry describes other resources; it is a resource, not a repository, whatever list holds it.
        return ("resources" if entity.get("resourceType") == ref("#rtype-registry") else "repositories"), None
    if collection == "tests":
        if entity_id.startswith("#criterion-"):
            return "tests", as_list(entity.get("isPartOf"))[0]["@id"].removeprefix("#resource-")
        return "tests", "guide" if entity_id.startswith("#test-guide-") else CHAMPION_SCOPE
    if collection in ("model", "lifecycle"):
        route = next(((kind, scope) for prefix, kind, scope in MEMBER_ROUTES if entity_id.startswith(prefix)), None)
        if route is None and collection == "lifecycle":
            model = entity_id.removeprefix("#lifecycle-")
            route = "lifecycles", model.split(".", 1)[0] if "." in model else None
        return route or ("models", None)
    return COLLECTION_KINDS.get(collection, collection), None


def catalogue_addresses(entities: dict[str, dict[str, Any]], content: dict[str, Any]) -> dict[str, str]:
    """Project stored Guide IDs and frozen kinds once; external identities never issue a published address."""
    records = catalogue_records(content)
    repositories = {item["@id"] for item in as_list(entities.get("#repositories", {}).get("hasPart"))}
    result: dict[str, str] = {}
    for entity_id, old in api_paths(catalogue_record_keys(entities, content)).items():
        entity = entities[entity_id]
        collection, identifier = old.split("/", 1)
        kind, scope = record_route(entity_id, entity, collection, repositories)
        if entity_id.startswith("#criterion-"):
            identifier = str(entity["identifier"])
        elif kind == "lifecycles" and scope:
            identifier = identifier.split(".", 1)[1]
        elif entity_id == "#lifecycle-crosswalk":
            identifier = CROSSWALK_ID
        row = records.get(entity_id, {})
        if "guideId" in row:
            raise ContentError(f"{entity_id}: obsolete guideId field; id is the one primary value")
        identifier = str(row.get("id") or identifier)
        if has_particles(identifier):
            raise ContentError(
                f"{entity_id}: Guide slug contains a particle; use an official abbreviation or source URL words"
            )
        try:
            if row.get("guideRoute"):
                kind, scope = parse_route(row["guideRoute"])
            address = issue_address(kind, identifier, scope)
        except ValueError as error:
            raise ContentError(f"{entity_id}: {error}") from error
        if len(identifier) > MAX_ID:
            raise ContentError(f"{entity_id}: overlong Guide identifier {identifier}; assign a short primary id")
        holder = next((other for other, issued in result.items() if issued == address), None)
        if holder is not None:
            raise ContentError(
                f"two entries share Guide address {address}: {holder}, {entity_id}; review their identities"
            )
        result[entity_id] = address
    return result


# ---------------------------------------------------------------------------
# One identity projection

# Nodes that organise the crate itself keep their crate-local identifiers: the lists the catalogue groups, the
# source snapshots, the Guide's own software, and the instruments, people without an ORCID iD and help routes its
# provenance and pages name.
# They are not catalogue records, so they have no address. Any other node without an address is refused.
CRATE_LOCAL = re.compile(
    r"#(?:repositories|sources|resources|ledger|path|fips|infrastructures|tests"
    r"|guide-selection|guide-source|guide-software|guide-help|ai-statement|(?:snapshot|instrument|help|person)-[A-Za-z0-9._-]+)\Z"
)
# The properties by which a record holds a part that has no address of its own.
PART_PROPERTIES = (
    "hasPart",
    "potentialAction",
    "alternateIdentifier",
    "definitionPart",
    "quotedDefinition",
    "prefillMapping",
    "qualifiedRelation",
    "review",
)


class Placement(NamedTuple):
    """Where an entity is published: a record at its address, a part of another entity under a fragment, or an
    identifier kept as it is (a file of the crate, an outside IRI or a crate-local node)."""

    address: str | None = None
    owner: str | None = None
    fragment: str | None = None
    kept: str | None = None


def identity_projection(graph: Graph, content: dict[str, Any]) -> dict[str, Placement]:
    """Place every entity of the built graph, by its build key: each catalogue record at one address, each part under
    the record it belongs to, a registry's record under the thing it describes, and files, outside IRIs and
    crate-local nodes as they are. An entity that fits none of these, or two that would share a place, is refused."""
    entities = graph.entities
    rows = catalogue_records(content)
    placed: dict[str, Placement] = {
        key: Placement(address=address) for key, address in catalogue_addresses(entities, content).items()
    }

    def thing(key: str, kind: str, identifier: str, scope: str | None = None) -> None:
        if key in entities and key not in placed:
            try:
                placed[key] = Placement(address=issue_address(kind, identifier, scope))
            except ValueError as error:
                raise ContentError(f"{key}: {error}") from error

    def part(key: str, owner: str, fragment: str) -> None:
        if key in entities and key not in placed:
            placed[key] = Placement(owner=owner, fragment=fragment)

    # Records the API publishes from API v1 on: advice, pages and callouts.
    for data in content["stations"]:
        for advice in data.get("advice", []):
            thing(f"#advice-{advice['id']}", "advice", advice["id"])
    for page in content["pages"]:
        thing(f"#page-{page['id']}", "pages", page["id"])
    for callout in content["callouts"]:
        thing(f"#callout-{callout['id']}", "callouts", callout["id"])

    # The European research infrastructures, which a registry's record may be about.
    for key in entities:
        if key.startswith("#european-ri-"):
            thing(key, "infrastructures", key.removeprefix("#european-ri-"))

    # A registry's record about a thing the Guide describes sits under that thing.
    topic_records = {
        registry_record_key(scheme, ""): scheme for scheme in ("nkr", "re3data", "fairsharing", "datacite")
    }
    for key, entity in entities.items():
        scheme = next((name for prefix, name in topic_records.items() if key.startswith(prefix)), None)
        if scheme and key not in placed:
            topic = next(iter(ids_of(entity.get("primaryTopic"))), None)
            if topic in placed:
                part(key, topic, scheme)
        if key.startswith("#knav-") and key not in placed:
            same = [target for target in ids_of(entity.get("sameAs")) if target in placed and target != key]
            if len(same) == 1:
                part(key, same[0], "knav")
    dashboard_things = {
        target.removeprefix(FIP_DASHBOARD): key
        for key, entity in entities.items()
        if key in placed
        for target in ids_of(entity.get("sameAs"))
        if target.startswith(FIP_DASHBOARD)
    }
    owners = organization_record_owners(graph, content)
    for key in list(entities):
        row = rows.get(key, {})
        handle = alternate_id(row, "fip-dashboard") if row else None
        if key.startswith("#fer-") and handle in dashboard_things:
            part(key, dashboard_things[handle], "fip-dashboard")
        elif key.startswith("#fd-org-"):
            if key in owners:
                part(key, owners[key], "fip-dashboard-organization")
            else:
                thing(key, "organizations", str(row.get("id") or key.removeprefix("#fd-org-")))

    # The remaining organisations, the European research infrastructures and the controlled vocabularies.
    for key, entity in entities.items():
        if key.startswith("#org-"):
            thing(key, "organizations", key.removeprefix("#org-"))
        elif key.startswith("#lens-"):
            thing(key, "vocabularies", key.removeprefix("#lens-"), "lenses")
        elif "DefinedTermSet" in as_list(entity.get("@type")) and key.startswith("#"):
            thing(key, "vocabularies", key.removeprefix("#"))
    for key, entity in entities.items():
        term_set = next(iter(ids_of(entity.get("inDefinedTermSet"))), None)
        if term_set in placed and placed[term_set].address and placed[term_set].address.startswith("vocabularies/"):
            code = str(entity.get("termCode") or entity.get("identifier") or "")
            check = term_set.removeprefix("#blocks-")
            if term_set.startswith("#blocks-"):
                code = code.removeprefix(check + "-")
            thing(key, "vocabularies", code, placed[term_set].address.split("/", 1)[1])

    # Parts: what a record holds under its own fragment, placed once its whole is placed.
    holders: dict[str, list[str]] = {}
    for key, entity in entities.items():
        for prop in PART_PROPERTIES:
            for target in ids_of(entity.get(prop)):
                holders.setdefault(target, []).append(key)
    progress = True
    while progress:
        progress = False
        for key, entity in entities.items():
            if key in placed or not key.startswith("#") or CRATE_LOCAL.match(key):
                continue
            # The whole a part names itself comes first; otherwise the one record that holds it.
            wholes = [whole for whole in ids_of(entity.get("isPartOf")) if whole in placed] or list(
                dict.fromkeys(whole for whole in holders.get(key, []) if whole in placed)
            )
            if len(wholes) == 1:
                part(key, wholes[0], part_fragment(key, entity, wholes[0]))
                progress = True
    for key, entity in entities.items():
        if key in placed:
            continue
        if CRATE_LOCAL.match(key) or not key.startswith("#"):
            placed[key] = Placement(kept=key)
        elif key.startswith("#local-test-documentation-") and isinstance(entity.get("url"), str):
            placed[key] = Placement(kept=entity["url"])  # a section of a file of the crate
    unplaced = sorted(set(entities) - set(placed))
    if unplaced:
        raise ContentError("entities with no address or whole to belong to: " + ", ".join(unplaced[:12]))
    return placed


def ids_of(value: Any) -> list[str]:
    return [item["@id"] for item in as_list(value) if isinstance(item, dict) and isinstance(item.get("@id"), str)]


def name_values(value: Any) -> list[str]:
    return [item.get("@value", "") if isinstance(item, dict) else str(item) for item in as_list(value) if item]


def part_fragment(key: str, entity: dict[str, Any], whole: str) -> str:
    """A part's fragment under its whole: a name for what it is to the whole, or the rest of its build key after the
    whole's, which for a page section is its own id."""
    named = {
        "#mapping-": lambda: "mapping-" + key.removeprefix("#mapping-" + whole.removeprefix("#criterion-") + "-"),
        "#node-membership-": lambda: "membership-" + key.removeprefix("#node-membership-"),
        "#model-context-": lambda: "context-" + str(entity.get("identifier", "")).rsplit(".", 1)[-1],
    }
    fragment = next((rule() for prefix, rule in named.items() if key.startswith(prefix)), None)
    if entity.get("@type") == "PropertyValue" and entity.get("propertyID") and key.startswith("#alternate-"):
        fragment = "id-" + slug(str(entity["propertyID"]))
    elif fragment is None and whole == "#implementation-model" and key.startswith("#model-"):
        fragment = key.removeprefix("#model-")
    elif fragment is None and key.startswith((whole + "#", whole + "-")):
        fragment = key[len(whole) + 1 :]
    if fragment is None:
        raise ContentError(f"{key}: no fragment for a part of {whole}")
    return fragment


def published_ids(placements: dict[str, Placement], base: str) -> dict[str, str]:
    """Each build key's published identifier: `<base><address>` for a record, the record's identifier and a fragment
    for a part (a part of a part joins both fragments), and the kept identifier otherwise."""
    result: dict[str, str] = {}

    def resolve(key: str, seen: tuple[str, ...] = ()) -> str:
        if key in result:
            return result[key]
        placement = placements[key]
        if placement.address:
            value = base + placement.address
        elif placement.kept:
            value = placement.kept
        else:
            if key in seen:
                raise ContentError(f"{key}: a part cannot contain itself")
            whole = resolve(placement.owner, (*seen, key))
            value = whole + ("-" if "#" in whole else "#") + str(placement.fragment)
        result[key] = value
        return value

    for key in placements:
        resolve(key)
    clashes = {value for value, count in Counter(result.values()).items() if count > 1}
    if clashes:
        raise ContentError("two entities share a published identifier: " + ", ".join(sorted(clashes)[:6]))
    return result


def publish_identities(graph: Graph, placements: dict[str, Placement], base: str) -> dict[str, str]:
    """Re-key the built graph to the published identifiers: every entity, every reference and the build's indexes.
    A record whose build key was an outside IRI (a DOI) keeps it in sameAs. Returns the addresses of the records."""
    mapping = published_ids(placements, base)

    # A reference may name a record by its address, as an action's target does; it becomes the record's IRI.
    by_address = {placement.address: mapping[key] for key, placement in placements.items() if placement.address}

    def rewrite(value: Any) -> Any:
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, dict):
            return {
                name: mapping.get(item) or by_address.get(item, item)
                if name == "@id" and isinstance(item, str)
                else rewrite(item)
                for name, item in value.items()
            }
        return value

    graph.entities = {mapping[key]: rewrite(entity) for key, entity in graph.entities.items()}
    for key, placement in placements.items():
        if placement.address and "://" in key:
            append_ref(graph.entities[mapping[key]], "sameAs", key)  # an outside identity, such as a DOI
    graph.index = {content_id: [mapping.get(key, key) for key in keys] for content_id, keys in graph.index.items()}
    graph.text_links = {
        mapping.get(key, key): [link | {"ref": mapping.get(link["ref"], link["ref"])} for link in links]
        for key, links in graph.text_links.items()
    }
    graph.repository_keys = {
        name: {mapping.get(key, key) for key in keys} for name, keys in graph.repository_keys.items()
    }
    graph.addresses = {mapping[key]: placement.address for key, placement in placements.items() if placement.address}
    graph.published = mapping
    return graph.addresses


def record_base_of(crate: dict[str, Any]) -> str:
    """The record base of a published crate: the namespace its profile names, followed by `id/`; for a crate without
    the Guide's profile, the base its records share, or none."""
    root = next((entity for entity in crate["@graph"] if entity["@id"] == "./"), {})
    profiles = [
        reference
        for reference in ids_of(root.get("conformsTo"))
        if "/profile/" in reference and "w3id.org/ro/" not in reference
    ]
    if profiles:
        return profiles[0].split("profile/", 1)[0] + "id/"
    records = [entity["@id"] for entity in crate["@graph"] if "/id/" in entity["@id"] and "://" in entity["@id"]]
    return records[0].split("/id/", 1)[0] + "/id/" if records else "urn:fair-guide:no-records/"


def relative_ids(value: Any, base: str) -> Any:
    """The page's view of published identifiers: a record, or a part of one, by its address relative to the Guide's
    namespace; files, outside IRIs and crate-local nodes as they are."""
    if isinstance(value, list):
        return [relative_ids(item, base) for item in value]
    if isinstance(value, dict):
        return {
            name: item.removeprefix(base) if name == "@id" and isinstance(item, str) else relative_ids(item, base)
            for name, item in value.items()
        }
    return value


LINKSET_FILE = "linkset.json"
# What the build generates and the repository must not hold; the API's records and its description as well.
GENERATED = (
    CRATE_FILE,
    NT_FILE,
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
        or path == "404.html"
        or (path.startswith("id/") and path.endswith(".html"))
        or (path.startswith("api/") and path.endswith((".json", ".jsonld")))
        or bool(PROFILE_PAGE.match(path))
        or (not path.startswith(PROFILE_DIR + "/") and bool(re.fullmatch(r"profile/[^/]+/recipes/.+\.rq", path)))
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
        {"rel": "describedby", "href": NT_FILE, "type": "application/n-triples"},
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
    """The roles shown on the about page: who wrote the content basis, who compiled and reviewed the guide, who
    contributed content, the tools used and the funding."""
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
    credits.append({"role": "contributors", "people": [person(entry) for entry in guide.get("contributors", [])]})
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
            # Records are named by address relative to `<namespace>id/`; the kinds are the address's first segment.
            "namespace": guide["recordBase"].removesuffix("id/"),
            "kinds": sorted(KINDS),
            # The registries whose records describe things, in the order a thing lists them (founding first).
            "recordSchemes": list(RECORD_SCHEMES),
            "textLinks": text_links or {},
            "foldedSections": [
                f"pages/{page['id']}#{section['id']}"
                for page in content["pages"]
                for section in page.get("section", [])
                if section.get("details")
            ],
            "api": {
                "files": API_FILES,
                "records": api or {},
                "fipCollections": content["ui"]["api"].get("fipCollections", []),
                "recipes": {
                    "root": f"profile/{guide.get('profileVersion', '')}/recipes/",
                    "items": list(content["ui"]["api"].get("recipes", {}).get("labels", {})),
                },
            },
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
                "dqv": DQV,
                "fipTerms": FIP_TERMS,
                "guide": guide["vocabularyBase"],
                "guideTerms": {term: guide["vocabularyBase"] + term for term in EXPORT_GUIDE_TERMS},
                # The landing page of the Guide's profile, at its version's address.
                "profilePage": f"profile/{guide.get('profileVersion', '')}/index.html",
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


def split_crate(crate: dict[str, Any], base: str | None = None) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """The crate as the page loads it: the core every view needs, and the parts (PART_SCRIPTS) that views load when
    they first need them. A part holds whole entities, or properties of core entities (original passages and source
    bylines); the core and the parts together are the crate. What goes where follows each entity's address under the
    record base (`base`, inferred from the crate when omitted) and the registries' records."""
    graph = crate["@graph"]
    base = base or record_base_of(crate)

    def address(entity: dict[str, Any]) -> str:
        return guide_address(entity["@id"], base) or ""

    def kind(entity: dict[str, Any]) -> str:
        return address(entity).split("/", 1)[0]

    def fragment(entity: dict[str, Any]) -> str:
        return address(entity).partition("#")[2]

    def scope(entity: dict[str, Any]) -> str:
        parts = address(entity).split("#")[0].split("/")
        return parts[1] if len(parts) == 3 else ""

    # The FIP Dashboard's and the KNAV catalogue's records of resources and repositories.
    registry = {
        entity["@id"]
        for entity in graph
        if CATALOG_RECORD in as_list(entity.get("@type"))
        and kind(entity) in ("resources", "repositories")
        and fragment(entity) in ("fip-dashboard", "knav")
    }

    records = records_by_thing({entity["@id"]: entity for entity in graph})

    def from_registry(entity: dict[str, Any]) -> bool:
        """A record a registry published, or a part of one: the FIP Dashboard's and the KNAV catalogue's."""
        return (
            entity["@id"] in registry
            or entity["@id"].split("#")[0] in registry
            or (kind(entity) in ("resources", "repositories") and fragment(entity).startswith(RECORD_SCHEMES))
            # A thing only a registry knows loads with the record that founds it.
            or founding_record(entity, records) in registry
        )

    guidance_sources = {
        reference["@id"] for entity in graph if entity.get("guidance") for reference in as_list(entity.get("isPartOf"))
    }
    initial_sources = {
        reference["@id"] for entity in graph if entity["@id"] == "./" for reference in as_list(entity.get("isBasedOn"))
    }
    guidance_sources -= initial_sources
    pages = [
        entity for entity in graph if kind(entity) == "pages" and not fragment(entity) and "isPartOf" not in entity
    ]
    sections = {ref["@id"] for page in pages for ref in as_list(page.get("hasPart"))}
    sections |= {
        ref["@id"] for entity in graph if entity["@id"] in sections for ref in as_list(entity.get("potentialAction"))
    }
    parts: dict[str, dict[str, Any]] = {name: {"entities": [], "properties": {}} for name in PART_SCRIPTS}
    core = []
    path_model = f"lifecycles/{PATH_LIFECYCLE}"
    for entity in graph:
        if kind(entity) in ("models", "layers", "seams", "model-examples") or (
            kind(entity) == "stations" and fragment(entity).startswith("context-")
        ):
            parts["model"]["entities"].append(entity)
        elif address(entity).startswith(path_model + "/"):
            # The path's stages name the rail on every view; their definitions load with the other life-cycle models.
            detail = {
                key: entity[key]
                for key in ("definitionPart", "descriptionTranslation", "quotedDefinition")
                if key in entity
            }
            parts["model"]["properties"][entity["@id"]] = detail
            core.append({key: value for key, value in entity.items() if key not in detail})
        elif address(entity) == path_model:
            # The path's model names its stages' source on the landing, with a link to the page that publishes it.
            detail = {key: entity[key] for key in ("citation",) if key in entity}
            parts["model"]["properties"][entity["@id"]] = detail
            core.append({key: value for key, value in entity.items() if key not in detail})
        elif kind(entity) in ("lifecycles", "crosswalks"):
            parts["model"]["entities"].append(entity)
        elif entity.get("@type") == "rdf:Property" and entity.get("rdfs:label") in MODEL_TERMS:
            # Full definitions are needed only with the model; its property IRIs remain in the core context.
            parts["model"]["entities"].append(entity)
        elif entity.get("@type") in ("rdf:Property", "rdfs:Class"):
            # Vocabulary definitions serve source detail and machine readers, rather than initial navigation.
            # Keep their full definitions with the standards part, which the machine-data page also loads.
            parts["standards"]["entities"].append(entity)
        elif entity["@id"].startswith("#instrument-"):
            # Instrument detail is provenance metadata and loads with the actions that name it.
            parts["standards"]["entities"].append(entity)
        elif kind(entity) == "vocabularies" and address(entity).split("/")[1] in CODED_SETS:
            # Statuses, advice kinds and pre-fill coverage are read by their codes, which their references carry;
            # the terms themselves serve detail and machine readers.
            parts["standards"]["entities"].append(entity)
        elif kind(entity) == "glossary" and fragment(entity).startswith("id-"):
            # Imported glossary IDs are detail metadata; catalogue/search load them with the definitions.
            parts["standards"]["entities"].append(entity)
        # The FIP Dashboard snapshot (the profiles and the resource records they declare) and the KNAV catalogue's.
        elif kind(entity) == "questions" or (
            kind(entity) == "tests" and scope(entity) not in ("guide", CHAMPION_SCOPE)
        ):
            # External evaluators' criteria and their reviewed mappings load with the questions they relate to.
            parts["questions"]["entities"].append(entity)
        elif kind(entity) in ("fips", "infrastructures") or from_registry(entity):
            # The large research infrastructures load with the catalogue, as the registries' records do.
            parts["fips"]["entities"].append(entity)
        elif address(entity).startswith(STANDARD_CLAUSES):
            parts["standards"]["entities"].append(entity)
        elif (has_type(entity, "CreateAction") or has_type(entity, "UpdateAction")) and (
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
        elif status_code(entity.get("adviceKind")) == "ai" and ("promptSample" in entity or "checkAfter" in entity):
            # An AI tip's prompt and what to check afterwards show on its station and the AI page, which load this.
            detail = {key: entity[key] for key in ("promptSample", "checkAfter") if key in entity}
            parts["standards"]["properties"][entity["@id"]] = detail
            core.append({key: value for key, value in entity.items() if key not in detail})
        elif entity["@id"] in sections:
            parts["pages"]["entities"].append(entity)
        elif kind(entity) == "glossary" and fragment(entity) in ("definition", "czech-definition"):
            # Original definitions are works of their own, loaded with sourced detail and search.
            parts["standards"]["entities"].append(entity)
        elif kind(entity) == "glossary" and not fragment(entity) and entity.get("definitionPart"):
            # The definition's link loads with it; the first download needs only each term's label.
            parts["standards"]["properties"][entity["@id"]] = {"definitionPart": entity["definitionPart"]}
            core.append({key: value for key, value in entity.items() if key != "definitionPart"})
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
        level = guide_address(entity.get("disclosureLevel", {}).get("@id", ""), base)
        if level in ("vocabularies/levels/L1", "vocabularies/levels/L2", "vocabularies/levels/L3"):
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
            glossary = str(node.get("@id", "")).startswith("glossary/") and node.get("termCode")
            # A repository's or an infrastructure's entry keeps its name in the other language too.
            named = has_type(node, "DataCatalog") or "abbreviation" in node
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


def crawler_files(base: str, landing_pages: tuple[str, ...] = ()) -> dict[str, str]:
    """Discovery at the actual publication root. A subpath cannot publish the origin's robots policy.

    Preview HTML remains crawlable so its noindex can be read. Only root hosting emits robots.txt; either hosting
    mode emits the production sitemap, without fragments, preview URLs or invented modification dates.
    """
    base = publication_base(base)
    urlset = ElementTree.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    preview = urllib.parse.urlsplit(base).path.rstrip("/").endswith("/next")
    for path in SITEMAP_PATHS + (() if preview else landing_pages):
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
    initial_ui = dict(content["ui"])
    api_strings = content["ui"]["api"]
    # Keep only the shared JSON-link labels initially; the other API documentation belongs to the machines part.
    initial_ui["api"] = {key: api_strings[key] for key in ("record", "recordTitle")}
    links = signposts(content, crate)
    page = render_page(
        (root / PAGE_FILE).read_text(encoding="utf-8"),
        content | {"ui": initial_ui},
        crate,
        icon_sprite(root / "assets" / "icons"),
    )
    core, parts = split_crate(crate, content["guide"]["guide"]["recordBase"])
    parts["api"]["ui"] = {"api": api_strings}
    # The page names a record by its address and a part by the address and a fragment, relative to the namespace.
    base = content["guide"]["guide"]["recordBase"]
    core = relative_ids(core, base)
    parts = {
        name: relative_ids(part, base)
        | {
            "properties": {
                key.removeprefix(base): relative_ids(value, base) for key, value in part["properties"].items()
            }
        }
        for name, part in parts.items()
    }
    entities = {entity["@id"]: entity for entity in crate["@graph"]}
    # Keep the namespace in config, not in every key: lookup normalizes full IRIs back to this same local address.
    records = {
        record_address(entity_id, base): record_address(entity_id, base)
        for members in api_records(entities, content).values()
        for _, entity_id in members
    }
    text_links = {
        key.removeprefix(base): [link | {"ref": link["ref"].removeprefix(base)} for link in found]
        for key, found in graph.text_links.items()
    }
    # Synchronous references need their target address before the infrastructure graph arrives. Keep only those
    # addresses initially visible; the remaining infrastructure records still load with fips or the machines page.
    referenced = {link["ref"] for found in text_links.values() for link in found}
    infrastructure_records = {
        address: path
        for address, path in records.items()
        if address.startswith("infrastructures/") and address not in referenced
    }
    records = {address: path for address, path in records.items() if address not in infrastructure_records}
    ui = page_config(content | {"ui": initial_ui}, text_links, records, links)
    ui["config"]["parts"] = dict(PART_SCRIPTS)
    ui["config"]["languages"] = dict(LANGUAGE_SCRIPTS)
    ui["config"]["partLanguages"] = dict(PART_LANGUAGE_SCRIPTS)
    parts["fips"]["config"] = {"api": {"records": infrastructure_records}}
    parts["api"]["config"] = {"api": {"records": infrastructure_records}}
    parts["pages"]["config"] = {"signposts": ui["config"].pop("signposts")}
    api_metadata = ui["config"]["api"]
    parts["api"]["config"]["api"] |= {
        key: api_metadata.pop(key) for key in ("recipes", "fipCollections") if key in api_metadata
    }
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
    # Production discovery follows the same per-record projection as API v1 and the landing pages.
    record_paths = api_paths(api_records({entity["@id"]: entity for entity in crate["@graph"]}, content))
    landing_paths = tuple(sorted("id/" + path.removesuffix(".json") + ".html" for path in record_paths.values()))
    return (
        {
            CRATE_FILE: json.dumps(crate, ensure_ascii=False, indent=2) + "\n",
            NT_FILE: n_triples(crate, page_config(content)["config"]["pageUrl"]),
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
        | profile_recipes(root, content["guide"]["guide"])
        | profile_page(root, content["guide"]["guide"])
        | vocabulary_page(root, content["guide"]["guide"])
        | crawler_files(content["guide"]["guide"]["pageUrl"], landing_paths)
    )


PROFILE_PAGE = re.compile(r"^profile/[^/]+/index\.html$")
VOCABULARY_FILE = "terms/fair-guide.ttl"
# How the Guide's controlled vocabularies read in SKOS, stated once for every term and set rather than on each
# instance. These are subclass and subproperty axioms in the Guide's own document, never equivalences.
SKOS_ALIGNMENT = (
    "# Every controlled term of the Guide is a schema:DefinedTerm in one schema:DefinedTermSet. These axioms let a",
    "# SKOS consumer read them as concepts in schemes; they state no equivalence between the two vocabularies.",
    "schema:DefinedTerm rdfs:subClassOf skos:Concept .",
    "schema:DefinedTermSet rdfs:subClassOf skos:ConceptScheme .",
    "schema:inDefinedTermSet rdfs:subPropertyOf skos:inScheme .",
)


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
        f"@prefix schema: <{SCHEMA}> .",
        f"@prefix skos: <{SKOS}> .",
        "",
        f"<{base.rstrip('#')}> a owl:Ontology ;",
        '    rdfs:label "EOSC CZ FAIR guide vocabulary"@en ;',
        '    rdfs:comment "The guide\'s own terms, with the established term each specializes."@en .',
        "",
        *SKOS_ALIGNMENT,
        "",
    ]
    for name, (definition, broader, _) in GUIDE_CLASSES.items():
        lines.append(f"<{base}{name}> a rdfs:Class ;")
        lines.append(f'    rdfs:label "{name}"@en ;')
        lines.append(f'    rdfs:comment "{turtle_text(definition)}"@en ;')
        lines.append(f"    rdfs:subClassOf <{broader}> .")
        lines.append("")
    for term, definition in GUIDE_TERMS.items():
        broader, domain, range_ = term_shape(term, base)
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
            "acceptsDeposits",
            "repositoryFunction",
            "clauseKind",
            "discipline",
            "researchField",
            "lifecycleStage",
            "serviceStatus",
            "healthStatus",
            "clauseStatus",
            "fipStatus",
            "declarationStatus",
            "releaseStatus",
            "infrastructurePhase",
            "esfriStatus",
            "nodeState",
        ],
    ),
    ("Descriptions and notes", ["guidance", "assessmentContext", "note", "disclaimer"]),
    (
        "Dated and reviewed status",
        ["statusAsOf", "reviewedVersion", "mappingCoverage", "mappingBasis"],
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
            "prefillMapping",
            "prefillSource",
            "prefillField",
            "prefillCoverage",
            "adviceKind",
            "checkAfter",
            "promptSample",
            "guideState",
            "guideSources",
            "entryPoint",
        ],
    ),
    ("Roles and relations", ["operatedBy"]),
    ("Term order", ["termPosition"]),
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

    classes = [
        f'\n      <article class="detail-entry" id="{escape(name, quote=True)}">'
        f'<h3><a href="#{escape(name, quote=True)}"><code>{escape(name)}</code></a></h3>'
        f"<p>{escape(definition)}</p>"
        f'<p class="detail-meta">specializes {link(broader)}: {escape(reason)}</p></article>'
        for name, (definition, broader, reason) in GUIDE_CLASSES.items()
    ]
    sections = [f'\n    <section class="detail-group">\n      <h2>Classes</h2>{"".join(classes)}\n    </section>']
    for heading, terms in GUIDE_TERM_GROUPS:
        blocks = []
        for term in terms:
            if term not in GUIDE_TERMS:
                continue
            broader, domain, range_ = term_shape(term, vocabulary_base(guide))
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
      <a href="{VOCABULARY_FILE}" type="text/turtle">Turtle document</a>. Every controlled term the guide publishes
      is a <code>schema:DefinedTerm</code> in one <code>schema:DefinedTermSet</code>; the Turtle document also states,
      once, how they read as SKOS concepts in schemes.</p>{"".join(sections)}
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
    for name in GUIDE_CLASSES:
        if f"<{base}{name}> a rdfs:Class" not in document:
            errors.append(f"guide class '{name}' is absent from the vocabulary document")
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


def profile_recipes(root: Path, guide: dict[str, Any]) -> dict[str, str]:
    """Publish each authored SPARQL recipe at the active profile version, with its bilingual description."""
    recipe_source = root / PROFILE_DIR / "recipes"
    published: dict[str, str] = {}
    for path in sorted(recipe_source.glob("*.rq")):
        text = path.read_text(encoding="utf-8")
        for language in LANGS:
            if not re.search(rf"^# {language}: \S", text, re.M):
                raise ContentError(f"{path.relative_to(root)}: recipe lacks its {language} description")
        written = re.search(r"^PREFIX guide: <([^>]*)>", text, re.M)
        if written:
            text = text.replace(written.group(1), guide["vocabularyBase"])
        published[f"profile/{guide.get('profileVersion', '')}/recipes/{path.name}"] = text
    return published


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
