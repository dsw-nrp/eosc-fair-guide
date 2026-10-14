#!/usr/bin/env python3
"""Refresh dated snapshots of sources that a browser cannot query, or that the guide keeps as reviewed evidence.

Writes, each only after its response passes validation:

- ``content/glossary.toml`` from the Heslář Open Science API (labels, links and original Czech definitions under
  its reviewed CC BY 4.0 reuse terms);
- ``content/snapshots/re3data.toml`` with the Czech repositories registered in re3data;
- ``content/snapshots/fip-dashboard.toml`` with the FIP Dashboard's metadata, resources and profiles, which depend
  on each other and are replaced together in one file or not at all;
- ``content/snapshots/nkr.toml`` with the reviewed fields (``NKR_FIELDS``) of the repositories the National Repository
  Catalogue lists. Its repositories join the catalogue and the repository check's NKR pre-fill at build time; nothing
  is written while NKR lists no repository;
- ``content/snapshots/fairsharing.toml`` with the FAIRsharing record of each repository the catalogue lists, found
  through DataCite (FAIRsharing's own API needs a login): DataCite's metadata of each FAIRsharing record lists the
  described resource's addresses, including its re3data record;
- ``content/snapshots/datacite.toml`` with the DataCite repository of each repository whose re3data record DataCite
  names, so the catalogue offers DataCite's figures only where DataCite holds the repository;
- ``content/snapshots/knav-tools.toml`` with the tools of the KNAV Data Management Tools Catalogue, each with its
  life-cycle steps and discipline groups, at the catalogue's last commit. The catalogue's repository is licensed
  GPL-3.0, and so is the snapshot (``REUSE.toml``).

Usage::

    python scripts/refresh_snapshots.py [heslar] [re3data] [fip-dashboard] [nkr] [knav-tools] [fairsharing] [datacite]
                                        [--date YYYY-MM-DD] [--input DIR] [--report FILE] [--root DIR]

Without source names, all are refreshed. With ``--input``, responses are read from files in DIR instead of the
network (``heslar.json``, ``re3data-list.xml``, ``re3data-<id>.xml``, ``fip-dashboard-meta.json``,
``fip-dashboard-resource-types.json``, ``fip-dashboard-organizations.json``, ``fip-dashboard-resources.json``,
``fip-dashboard-fips.json``, ``nkr-<page>.json``, ``knav-tools.json``, ``knav-tools-commit.json``,
``fairsharing-<batch>.json``, ``datacite-<r3d id>.json``). FAIRsharing and DataCite read the repositories from the
checkout's content, the re3data snapshot included, so they follow a re3data refresh.

A refresh replaces a snapshot only when the response has the expected shape, every required collection is nonempty,
paginated sources were read completely within ``MAX_PAGES``, each response is at most ``MAX_RESPONSE_BYTES`` and no
collection loses more than ``MAX_REMOVED_SHARE`` of its existing records. Otherwise the snapshot stays as it was and
the source is reported as rejected. Replacement is atomic; a response that differs from the snapshot only in its
retrieval date changes nothing. ``--report`` writes each source's outcome (changed, unchanged, empty, rejected or
failed, with counts and the reason) as JSON, for the trusted publisher and the health report. Exits 1 when any
source was rejected or failed. Uses only the Python standard library; it never commits or opens pull requests.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import tomllib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HESLAR_API = "https://heslar.openscience.cz/api/v1/heslar/"
HESLAR_TERM = "https://heslar.openscience.cz/heslo.php?id={id}"
HESLAR_LICENSE = "https://creativecommons.org/licenses/by/4.0/"
RE3DATA_LIST = "https://www.re3data.org/api/beta/repositories?countries%5B%5D=CZE"
RE3DATA_REPOSITORY = "https://www.re3data.org/api/v1/repository/{id}"
DASHBOARD = "https://fip-dashboard.dmp.eosc.cz"
NKR = "https://repo.cz"
NKR_SEARCH = NKR + "/search?query=type:Repository&pageSize={size}&pageNum={page}"
RE3DATA_KIND = {"disciplinary": "domain", "institutional": "institutional", "other": "general"}
# The DOI re3data registers for each of its records, by which DataCite finds the repository it describes.
RE3DATA_DOI = re.compile(r"10\.17616/R3[0-9A-Z]{2,12}")
RE3DATA_RECORD = "https://www.re3data.org/repository/{id}"
DATACITE_API = "https://api.datacite.org"
# FAIRsharing registers a DataCite DOI for every record; a search names at most this many addresses at a time.
FAIRSHARING_PREFIX = "10.25504"
FAIRSHARING_DOI = re.compile(r"10\.25504/FAIRsharing\.[A-Za-z0-9]+", re.IGNORECASE)
FAIRSHARING_BATCH = 30
DATACITE_PAGE = 100
# A DataCite repository ID (a DataCite client): `<member>.<repository>` in lower case.
DATACITE_CLIENT = re.compile(r"[a-z0-9]+\.[a-z0-9][a-z0-9.-]*")
USER_AGENT = "eosc-fair-guide-snapshot/0.2 (+https://github.com/motyc/eosc-fair-guide)"

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_PAGES = 20
NKR_PAGE_SIZE = 100
# A reviewed limit: a refresh that would remove more than this share of a collection is treated as a broken
# response, not as the source shrinking; the maintainer reconciles a genuine large removal by hand.
MAX_REMOVED_SHARE = 0.25
# The NKR fields a snapshot keeps: what identifies a repository and what the guide's checks read (the `nkr` prefill
# paths in content/checks). Personal contact data are never copied; a contact is recorded only as present.
NKR_IDENTITY = ("repositoryName", "mainUrl", "type", "keywordCz", "keywordEn", "relatedRegistry")
NKR_PERSONAL = ("mainContact",)
KNAV_REPOSITORY = "Open-Science-Department-KNAV/Data-Management-Tools-Catalogue"
KNAV_TOOLS = f"https://raw.githubusercontent.com/{KNAV_REPOSITORY}/main/dmtools.json"
KNAV_COMMIT = f"https://api.github.com/repos/{KNAV_REPOSITORY}/commits?path=dmtools.json&per_page=1"
KNAV_PAGE = "https://openscience.lib.cas.cz/fair-data/katalog-nastroju-pro-spravu-dat/"
KNAV_LICENSE = "https://www.gnu.org/licenses/gpl-3.0.html"
MAX_KNAV_TOOLS = 1000
# The catalogue's discipline groups, by the icon that marks them in its filter (index.html of the catalogue).
KNAV_DISCIPLINES = {
    "infinity.svg": "all",
    "dna.svg": "biology-chemistry",
    "atom_structure.svg": "physics-materials",
    "monitor.svg": "computer-information",
    "telescope.svg": "astronomy",
    "user.svg": "social-sciences-humanities",
    "world.svg": "earth-sciences",
}


class RejectedError(Exception):
    """A response that cannot safely replace the snapshot; the snapshot stays unchanged."""


class Fetcher:
    """Read a bounded response from the network, or from a file when an input directory is given."""

    def __init__(self, input_dir: Path | None) -> None:
        self.input_dir = input_dir

    def get(self, url: str, file_name: str) -> bytes:
        if self.input_dir is not None:
            data = (self.input_dir / file_name).read_bytes()
        else:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise RejectedError(f"{file_name}: the response exceeds {MAX_RESPONSE_BYTES} bytes")
        return data

    def json(self, url: str, file_name: str) -> Any:
        try:
            return json.loads(self.get(url, file_name).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RejectedError(f"{file_name}: not JSON ({error})") from error


@dataclass
class Snapshot:
    """A validated replacement, not yet written: its file, text and the number of records in each collection."""

    path: str
    header: str
    blocks: list[str]
    counts: dict[str, int]
    required: tuple[str, ...] = ()
    retrieved: str = ""

    def text(self) -> str:
        return self.header + "\n" + "\n\n".join(self.blocks) + "\n"


@dataclass
class Outcome:
    source: str
    status: str
    path: str = ""
    counts: dict[str, int] = field(default_factory=dict)
    previous: dict[str, int] = field(default_factory=dict)
    reason: str = ""
    retrieved: str = ""


# ---------------------------------------------------------------------------
# TOML output


def q(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def text(value: dict[str, str] | None) -> str:
    value = value or {}
    return "{ cs = " + q((value.get("cs") or "").strip()) + ", en = " + q((value.get("en") or "").strip()) + " }"


def inline(table: dict[str, Any]) -> str:
    parts = []
    for key, value in table.items():
        if value is None or value == "":
            continue
        rendered = text(value) if isinstance(value, dict) else q(value)
        parts.append(f"{key} = {rendered}")
    return "{ " + ", ".join(parts) + " }"


def toml_value(value: Any) -> str:
    """Any JSON value as TOML: tables inline, keys quoted; null values are left out of tables and lists."""
    if isinstance(value, dict):
        items = [f"{q(str(key))} = {toml_value(item)}" for key, item in value.items() if item is not None]
        return "{ " + ", ".join(items) + " }" if items else "{}"
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value if item is not None) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    return q(str(value))


def require_list(value: Any, what: str) -> list[dict[str, Any]]:
    """A list of records, each an object with an ID; anything else is a changed or broken response."""
    if not isinstance(value, list) or not all(isinstance(item, dict) and item.get("id") for item in value):
        raise RejectedError(f"{what}: expected a list of records with IDs")
    return value


# ---------------------------------------------------------------------------
# Sources


class DefinitionText(HTMLParser):
    """Read the source's definition as text; markup and executable content never enter the snapshot."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1
        elif not self.hidden and tag in {"p", "div", "li", "br", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in {"p", "div", "li", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)

    def value(self) -> str:
        return "\n\n".join(line for part in "".join(self.parts).splitlines() if (line := " ".join(part.split())))


def heslar(fetch: Fetcher, today: str) -> Snapshot:
    data = fetch.json(HESLAR_API, "heslar.json")
    if not isinstance(data, dict):
        raise RejectedError("heslar.json: expected an object with a data list")
    terms = sorted(require_list(data.get("data"), "Heslář terms"), key=lambda term: str(term["id"]))
    seen: set[str] = set()
    blocks = [
        "[glossary]\n"
        f'source = "Heslář Open Science"\nurl = "https://heslar.openscience.cz/"\nretrieved = {today}\n'
        f"license = {q(HESLAR_LICENSE)}\n"
        "# Original Czech definitions, rendered as plain text; English labels are supplied by Heslář."
    ]
    for term in terms:
        label_cs = (term.get("termin_cs") or "").strip()
        label_en = (term.get("termin_en") or "").strip()
        if not label_cs or not label_en:
            continue
        # A term's ID is its ID in Heslář, adopted as published (docs/content-model.md, Identifiers).
        try:
            term_id = str(int(term["id"]))
        except (TypeError, ValueError) as error:
            raise RejectedError(f"Heslář term ID {term['id']!r} is not a number") from error
        if term_id in seen:
            continue
        seen.add(term_id)
        definition = DefinitionText()
        definition.feed(str(term.get("popis_cs") or ""))
        definition.close()
        body = definition.value()
        blocks.append(
            "[[term]]\n"
            f"id = {q(term_id)}\n"
            f"label = {text({'cs': label_cs, 'en': label_en})}\n"
            f"url = {q(HESLAR_TERM.format(id=term['id']))}"
            + (f'\ndefinition = {q(body)}\ndefinitionLanguage = "cs"' if body else "")
        )
    header = (
        "# Snapshot of Heslář Open Science (NTK). Generated by scripts/refresh_snapshots.py; do not edit by hand.\n"
    )
    return Snapshot("content/glossary.toml", header, blocks, {"term": len(seen)}, ("term",), today)


def parse_xml(data: bytes) -> ET.Element:
    """Parse downloaded XML, refusing any document that declares a DTD or entities."""
    head = data[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in data.lower():
        raise ValueError("refusing XML with a DTD or entity declarations")
    try:
        return ET.fromstring(data)
    except ET.ParseError as error:
        raise RejectedError(f"not XML ({error})") from error


def r3d(element: ET.Element, tag: str) -> list[str]:
    return [(child.text or "").strip() for child in element.iter() if child.tag.endswith("}" + tag) and child.text]


def r3d_names_in(record: ET.Element, language: str) -> list[str]:
    """The names a re3data record tags with one language (ISO 639-3), its repository name before its other names, in
    the record's order and each once. re3data tags names unevenly, so curated entries correct them (D-173)."""
    names: list[str] = []
    for tag in ("repositoryName", "additionalName"):
        for child in record.iter():
            value = (child.text or "").strip()
            if child.tag.endswith("}" + tag) and child.get("language") == language and value and value not in names:
                names.append(value)
    return names


def r3d_named(record: ET.Element, tag: str) -> list[str]:
    """The distinct named values of a re3data field, leaving out none, other and unknown."""
    return sorted({value for value in r3d(record, tag) if value.lower() not in ("none", "other", "unknown")})


def r3d_flag(record: ET.Element, tag: str) -> bool:
    return any(value.lower() == "yes" for value in r3d(record, tag))


INCLUSION_NOTE = "A reviewed inclusion (content/repositories.toml): hosted in the Czech Republic, not tagged with it."


def reviewed_inclusions(root: Path) -> set[str]:
    """Czech-hosted repositories that re3data lists without the Czech Republic, each kept with a reviewed reason in
    ``content/repositories.toml`` (``[[re3dataInclude]]``)."""
    path = root / "content" / "repositories.toml"
    entries = tomllib.loads(path.read_text(encoding="utf-8")).get("re3dataInclude", []) if path.is_file() else []
    ids = {str(entry.get("re3data", "")).strip() for entry in entries}
    if any(not re.fullmatch(r"r3d\d+", value) for value in ids):
        raise RejectedError("content/repositories.toml: a reviewed re3data inclusion is not an r3d identifier")
    return ids


def re3data(fetch: Fetcher, today: str, root: Path | None = None) -> Snapshot:
    listing = parse_xml(fetch.get(RE3DATA_LIST, "re3data-list.xml"))
    listed = {(repository.findtext("id") or "").strip() for repository in listing.iter("repository")} - {""}
    if any(not re.fullmatch(r"r3d\d+", value) for value in listed):
        raise RejectedError("re3data-list.xml: a listed repository ID is not an r3d identifier")
    dois = {
        (repository.findtext("id") or "").strip(): (repository.findtext("doi") or "")
        .strip()
        .removeprefix("https://doi.org/")
        for repository in listing.iter("repository")
        if (repository.findtext("doi") or "").strip()
    }
    if any(not RE3DATA_DOI.fullmatch(value) for value in dois.values()):
        raise RejectedError("re3data-list.xml: a record's DOI is not a re3data DOI")
    included = reviewed_inclusions(root or ROOT) - listed
    ids = sorted(listed | included)
    blocks = [
        "[snapshot]\n"
        f'source = "re3data"\nurl = "https://www.re3data.org/"\nretrieved = {today}\n'
        'license = "https://creativecommons.org/publicdomain/zero/1.0/"'
    ]
    for repository_id in ids:
        record = parse_xml(fetch.get(RE3DATA_REPOSITORY.format(id=repository_id), f"re3data-{repository_id}.xml"))
        names = r3d(record, "repositoryName")
        if not names:
            raise RejectedError(f"re3data-{repository_id}.xml: the record has no repository name")
        url = (r3d(record, "repositoryURL") or [""])[0]
        if not url.startswith("https://"):
            # The guide links only over HTTPS; the re3data record stands in for a plain-HTTP home page.
            url = f"https://www.re3data.org/repository/{repository_id}"
        kinds = [RE3DATA_KIND[value] for value in r3d(record, "type") if value in RE3DATA_KIND]
        subjects = sorted(
            {re.sub(r"^\d+\s+", "", value) for value in r3d(record, "subject") if re.match(r"^\d\s", value)}
        )
        pid_types = sorted({value for value in r3d(record, "pidSystem") if value.lower() not in ("none", "other")})
        languages = sorted(set(r3d(record, "repositoryLanguage")))
        apis = sorted(
            {child.get("apiType", "") for child in record.iter() if child.tag.endswith("}api")} - {"", "other"}
        )
        lines = ["[[repository]]", f"id = {q(repository_id.lower())}", f"name = {q(names[0])}", f"url = {q(url)}"]
        if czech := r3d_names_in(record, "ces"):
            lines.insert(3, f"namesCs = {q(czech)}")
        if repository_id in included:
            lines.insert(1, f"# {INCLUSION_NOTE}")
        if kinds:
            lines.append(f"kind = {q(kinds[0])}")
        lines.append(f"re3data = {q(repository_id)}")
        if dois.get(repository_id):
            lines.append(f"doi = {q(dois[repository_id])}")
        lines += [
            f"subjectsEn = {q(subjects)}",
            f"pidTypes = {q(pid_types)}",
            f"languages = {q(languages)}",
            f"apis = {q(apis)}",
            f"dataLicenses = {q(r3d_named(record, 'dataLicenseName'))}",
            f"certificates = {q(r3d_named(record, 'certificate'))}",
            f"metadataStandards = {q(r3d_named(record, 'metadataStandardName'))}",
            f"policies = {q(r3d_named(record, 'policyName'))}",
            f"versioning = {'true' if r3d_flag(record, 'versioning') else 'false'}",
            f"qualityManagement = {'true' if r3d_flag(record, 'qualityManagement') else 'false'}",
        ]
        blocks.append("\n".join(lines))
    header = (
        "# Snapshot of the Czech repositories in re3data. Generated by scripts/refresh_snapshots.py; do not edit by\n"
        "# hand. Repositories whose home page is not served over HTTPS link to their re3data record instead.\n"
    )
    return Snapshot("content/snapshots/re3data.toml", header, blocks, {"repository": len(ids)}, ("repository",), today)


def verification(items: list[dict[str, Any]]) -> str:
    rendered = [inline({key: item.get(key) for key in ("verifier", "level", "date", "url", "note")}) for item in items]
    return "[" + ", ".join(rendered) + "]"


def fip_dashboard(fetch: Fetcher, today: str) -> Snapshot:
    """The dashboard's collections refer to each other (resources to types and organisations, profiles to resources),
    so they are read and validated together and replace one file together."""
    meta = fetch.json(f"{DASHBOARD}/api/meta", "fip-dashboard-meta.json")
    if not isinstance(meta, dict):
        raise RejectedError("fip-dashboard-meta.json: expected an object")
    types = require_list(fetch.json(f"{DASHBOARD}/api/resource-types", "fip-dashboard-resource-types.json"), "types")
    organizations = require_list(
        fetch.json(f"{DASHBOARD}/api/organizations", "fip-dashboard-organizations.json"), "organisations"
    )
    resources = require_list(fetch.json(f"{DASHBOARD}/api/resources", "fip-dashboard-resources.json"), "resources")
    fips = require_list(fetch.json(f"{DASHBOARD}/api/fips", "fip-dashboard-fips.json"), "profiles")
    known = {item["id"] for item in resources}
    dangling = sorted(
        {d.get("resource") for item in fips for d in item.get("declarations", []) if d.get("resource")} - known
    )
    if dangling:
        raise RejectedError(f"FIP Dashboard profiles declare resources the response lacks: {', '.join(dangling[:5])}")
    head = [
        "[snapshot]",
        'source = "FIP Dashboard"',
        f'url = "{DASHBOARD}/"',
        f'api = "{DASHBOARD}/api"',
        f"retrieved = {today}",
        f"datasetName = {text(meta.get('name'))}",
        f"datasetVersion = {q(meta.get('version', ''))}",
        f"datasetUpdated = {q(meta.get('updated', ''))}",
    ]
    if meta.get("disclaimer"):
        head.append(f"disclaimer = {text(meta['disclaimer'])}")
    blocks = ["\n".join(head)]
    for item in sorted(types, key=lambda value: value["id"]):
        blocks.append(f"[[resourceType]]\nid = {q(item['id'])}\nlabel = {text(item.get('label'))}")
    for item in sorted(organizations, key=lambda value: value["id"]):
        lines = ["[[organization]]", f"id = {q(item['id'])}", f"name = {text(item.get('name'))}"]
        for key in ("acronym", "url", "ror", "scope"):
            if item.get(key):
                lines.append(f"{key} = {q(item[key])}")
        blocks.append("\n".join(lines))
    for item in sorted(resources, key=lambda value: value["id"]):
        lines = ["[[resource]]", f"id = {q(item['id'])}", f"name = {q(item.get('name', ''))}"]
        for key in ("acronym", "type", "scope", "url", "identifier", "provider"):
            if item.get(key):
                lines.append(f"{key} = {q(item[key])}")
        lines += [
            f"description = {text(item.get('description'))}",
            f"principles = {q(item.get('principles', []))}",
            f"verification = {verification(item.get('verification', []))}",
        ]
        blocks.append("\n".join(lines))
    for item in sorted(fips, key=lambda value: value["id"]):
        lines = ["[[fip]]", f"id = {q(item['id'])}", f"title = {text(item.get('title'))}"]
        for key in ("acronym", "community", "version", "updated", "status", "url"):
            if item.get(key):
                lines.append(f"{key} = {q(item[key])}")
        lines += [
            f"domain = {text(item.get('domain'))}",
            f"summary = {text(item.get('summary'))}",
            f"verification = {verification(item.get('verification', []))}",
        ]
        declarations = [
            inline({key: declaration.get(key) for key in ("principle", "resource", "status", "note")})
            for declaration in item.get("declarations", [])
        ]
        lines.append(
            "declarations = [\n  " + ",\n  ".join(declarations) + ",\n]" if declarations else "declarations = []"
        )
        blocks.append("\n".join(lines))
    header = "# Snapshot of the FIP Dashboard. Generated by scripts/refresh_snapshots.py; do not edit by hand.\n"
    counts = {
        "resourceType": len(types),
        "organization": len(organizations),
        "resource": len(resources),
        "fip": len(fips),
    }
    return Snapshot("content/snapshots/fip-dashboard.toml", header, blocks, counts, tuple(counts), today)


def nkr_fields(root: Path) -> tuple[str, ...]:
    """The reviewed NKR fields: identity fields and every top-level field a check pre-fills from NKR."""
    paths: set[str] = set()
    for check in sorted((root / "content" / "checks").glob("*.toml")):
        for item in tomllib.loads(check.read_text(encoding="utf-8")).get("item", []):
            for value in item.get("prefill", {}).get("nkr", []):
                if not value.startswith("@"):
                    paths.add(value.split(".", 1)[0])
    return tuple(dict.fromkeys([*NKR_IDENTITY, *sorted(paths - set(NKR_IDENTITY))]))


def nkr_pages(fetch: Fetcher) -> list[dict[str, Any]]:
    """Every repository NKR lists, read page by page until its reported total, within MAX_PAGES."""
    results: list[dict[str, Any]] = []
    total = None
    for page in range(MAX_PAGES):
        data = fetch.json(NKR_SEARCH.format(size=NKR_PAGE_SIZE, page=page), f"nkr-{page}.json")
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("results"), list)
            or not isinstance(data.get("size"), int)
        ):
            raise RejectedError(f"nkr-{page}.json: expected a Cordra search result with size and results")
        if total is None:
            total = data["size"]
            if total > MAX_PAGES * NKR_PAGE_SIZE:
                raise RejectedError(
                    f"NKR reports {total} repositories, more than {MAX_PAGES * NKR_PAGE_SIZE} can be read"
                )
        results += data["results"]
        if len(results) >= total:
            break
        if not data["results"]:
            break
    if total is None or len(results) != total:
        raise RejectedError(f"NKR pagination ended with {len(results)} of {total} repositories")
    return results


def nkr(fetch: Fetcher, today: str, root: Path | None = None) -> Snapshot:
    fields = nkr_fields(root or ROOT)
    blocks = [f'[snapshot]\nsource = "NKR"\nurl = "{NKR}/"\nretrieved = {today}\nfields = {q(list(fields))}']
    records = sorted(nkr_pages(fetch), key=lambda record: str(record.get("id", "")))
    for record in records:
        content = record.get("content") if isinstance(record, dict) else None
        if not isinstance(content, dict) or not record.get("id") or not content.get("repositoryName"):
            raise RejectedError("an NKR result has no ID or repository name")
        record_url = f"{NKR}/objects/{record['id']}"
        lines = ["[[record]]", f"id = {q(str(record['id']))}", f"url = {q(record_url)}"]
        for name in fields:
            if name in content and name not in NKR_PERSONAL:
                lines.append(f"{name} = {toml_value(content[name])}")
        for name in NKR_PERSONAL:
            if content.get(name):
                lines.append(f"{name}Present = true")
        blocks.append("\n".join(lines))
    header = (
        "# Snapshot of the repositories in the National Repository Catalogue (NKR): the reviewed fields only, no\n"
        "# personal contact data. Generated by scripts/refresh_snapshots.py; do not edit by hand.\n"
    )
    return Snapshot("content/snapshots/nkr.toml", header, blocks, {"record": len(records)}, (), today)


def knav_steps(root: Path) -> set[str]:
    """The catalogue's life-cycle steps, as the guide records them (content/lifecycle/3-knav-tools.toml)."""
    path = root / "content" / "lifecycle" / "3-knav-tools.toml"
    stages = tomllib.loads(path.read_text(encoding="utf-8")).get("stage", []) if path.is_file() else []
    return {str(stage.get("id")) for stage in stages}


def knav_tools(fetch: Fetcher, today: str, root: Path | None = None) -> Snapshot:
    """Every tool of the catalogue, or none: an unknown step or discipline group means the catalogue changed shape."""
    steps = knav_steps(root or ROOT)
    if not steps:
        raise RejectedError("content/lifecycle/3-knav-tools.toml names none of the catalogue's steps")
    commits = fetch.json(KNAV_COMMIT, "knav-tools-commit.json")
    head = commits[0] if isinstance(commits, list) and commits and isinstance(commits[0], dict) else {}
    sha = str(head.get("sha", ""))
    updated = str(((head.get("commit") or {}).get("committer") or {}).get("date", ""))[:10]
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated):
        raise RejectedError("knav-tools-commit.json: expected the catalogue's last commit with its SHA and date")
    tools = fetch.json(KNAV_TOOLS, "knav-tools.json")
    if not isinstance(tools, list) or not 0 < len(tools) <= MAX_KNAV_TOOLS:
        raise RejectedError(f"knav-tools.json: expected a list of 1 to {MAX_KNAV_TOOLS} tools")
    blocks = [
        "\n".join(
            [
                "[snapshot]",
                'source = "KNAV Data Management Tools Catalogue"',
                f'url = "{KNAV_PAGE}"',
                f'api = "https://github.com/{KNAV_REPOSITORY}"',
                f"retrieved = {today}",
                f'license = "{KNAV_LICENSE}"',
                f"datasetVersion = {q(sha)}",
                f"datasetUpdated = {q(updated)}",
            ]
        )
    ]
    seen: set[str] = set()
    for tool in sorted(tools, key=lambda item: str(item.get("id_name", "")) if isinstance(item, dict) else ""):
        if not isinstance(tool, dict) or not re.fullmatch(r"[a-z0-9_-]+", str(tool.get("id_name", ""))):
            raise RejectedError("knav-tools.json: a tool has no lower-case id_name")
        tool_id = tool["id_name"]
        tool_steps = [str(step).replace("_", "-") for step in tool.get("lifecycle_step", [])]
        icons = tool.get("icon", [])
        link = str(tool.get("link", ""))
        if tool_id in seen:
            raise RejectedError(f"knav-tools.json: two tools are named {tool_id}")
        seen.add(tool_id)
        if not str(tool.get("full_name", "")).strip() or not isinstance(tool.get("desc_short"), str):
            raise RejectedError(f"knav-tools.json: {tool_id} has no name or description")
        if not tool_steps or set(tool_steps) - steps:
            raise RejectedError(f"knav-tools.json: {tool_id} names unknown or no steps: {', '.join(tool_steps)}")
        if not isinstance(icons, list) or set(icons) - set(KNAV_DISCIPLINES):
            raise RejectedError(f"knav-tools.json: {tool_id} names an unknown discipline group")
        if not re.fullmatch(r"https?://\S+", link):
            raise RejectedError(f"knav-tools.json: {tool_id} has no web address")
        lines = ["[[tool]]", f"id = {q(tool_id)}", f"name = {q(tool['full_name'].strip())}"]
        # The guide links only over HTTPS; a plain-HTTP address is kept as data and the page links the catalogue.
        lines.append(f"url = {q(link)}" if link.startswith("https://") else f"httpUrl = {q(link)}")
        lines += [
            f"steps = {q(tool_steps)}",
            f"disciplines = {q([KNAV_DISCIPLINES[icon] for icon in icons])}",
            f"description = {q(tool['desc_short'].strip())}",
        ]
        blocks.append("\n".join(lines))
    header = (
        "# Snapshot of the KNAV Data Management Tools Catalogue (Open Science Department, Library of the Czech\n"
        "# Academy of Sciences): its tools with their life-cycle steps and discipline groups. Licensed GPL-3.0 like\n"
        "# the catalogue (REUSE.toml). Generated by scripts/refresh_snapshots.py; do not edit by hand.\n"
    )
    return Snapshot("content/snapshots/knav-tools.toml", header, blocks, {"tool": len(seen)}, ("tool",), today)


def bare_url(url: str) -> str:
    """An address without its scheme, "www." and trailing slashes, as the page matches addresses."""
    value = re.sub(r"^https?://", "", url.strip().lower())
    return re.sub(r"^www\.", "", value).rstrip("/")


def catalogue_repositories(root: Path) -> list[dict[str, Any]]:
    """The repositories the catalogue lists from its own content: the curated list, repositories described as
    resources and the re3data snapshot, each once by its re3data record or else its address, with what identifies
    it (re3data ID, re3data DOI, address and a curated DataCite repository)."""
    content = root / "content"

    def read(path: Path) -> dict[str, Any]:
        return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    rows = list(read(content / "repositories.toml").get("repository", []))
    for resource in read(content / "resources.toml").get("resource", []):
        if isinstance(resource.get("repository"), dict):
            rows.append({key: resource[key] for key in ("id", "url") if key in resource} | resource["repository"])
    rows += read(content / "snapshots" / "re3data.toml").get("repository", [])
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = f"re3data:{row['re3data']}" if row.get("re3data") else "url:" + bare_url(str(row.get("url", "")))
        if key == "url:":
            continue
        entry = merged.setdefault(key, {})
        for name in ("re3data", "doi", "url", "datacite"):
            if row.get(name) and not entry.get(name):
                entry[name] = row[name]
    return [merged[key] for key in sorted(merged)]


def annotation_key(repository: dict[str, Any]) -> str:
    """How an annotation names its repository: by re3data record where it has one, else by address."""
    return f"re3data = {q(repository['re3data'])}" if repository.get("re3data") else f"url = {q(repository['url'])}"


def fairsharing(fetch: Fetcher, today: str, root: Path | None = None) -> Snapshot:
    repositories = catalogue_repositories(root or ROOT)
    terms: set[str] = set()
    for repository in repositories:
        if repository.get("re3data"):
            terms.add(RE3DATA_RECORD.format(id=repository["re3data"]))
        url = str(repository.get("url", ""))
        if url.startswith(("https://", "http://")) and '"' not in url:
            terms |= {url.rstrip("/"), url.rstrip("/") + "/"}
    ordered = sorted(terms)
    records: dict[str, dict[str, Any]] = {}
    for start in range(0, len(ordered), FAIRSHARING_BATCH):
        batch = ordered[start : start + FAIRSHARING_BATCH]
        query = "relatedIdentifiers.relatedIdentifier:(" + " OR ".join(f'"{term}"' for term in batch) + ")"
        params = f"query={urllib.parse.quote(query)}&prefix={FAIRSHARING_PREFIX}&page[size]={DATACITE_PAGE}"
        url = f"{DATACITE_API}/dois?{params}"
        name = f"fairsharing-{start // FAIRSHARING_BATCH}.json"
        data = fetch.json(url, name)
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise RejectedError(f"{name}: expected a DataCite DOI search result")
        if len(data["data"]) >= DATACITE_PAGE:
            raise RejectedError(f"{name}: a search found {DATACITE_PAGE} records or more, more than one page")
        for entry in data["data"]:
            attributes = (entry or {}).get("attributes") or {}
            doi = str(attributes.get("doi") or (entry or {}).get("id") or "")
            if not FAIRSHARING_DOI.fullmatch(doi):
                raise RejectedError(f"{name}: {doi or 'a record'} is not a FAIRsharing DOI")
            title = next(
                (
                    item["title"]
                    for item in attributes.get("titles") or []
                    if isinstance(item, dict) and item.get("title")
                ),
                "",
            )
            related = [
                str(item.get("relatedIdentifier") or "")
                for item in attributes.get("relatedIdentifiers") or []
                if isinstance(item, dict)
            ]
            records[doi.lower()] = {
                # DataCite answers in lower case; FAIRsharing writes its records as "FAIRsharing.<code>".
                "doi": re.sub(r"(?i)^10\.25504/fairsharing\.", "10.25504/FAIRsharing.", doi),
                "name": re.sub(r"^FAIRsharing record for:\s*", "", str(title), flags=re.IGNORECASE),
                "re3data": {
                    match.group(1)
                    for value in related
                    if (match := re.search(r"re3data\.org/repository/(r3d\d+)", value))
                },
                "addresses": {bare_url(value) for value in related if value},
            }
    blocks = [
        "[snapshot]\n"
        f'source = "FAIRsharing"\nurl = "https://fairsharing.org/"\nretrieved = {today}\n'
        f'via = "{DATACITE_API}/"\nlicense = "https://creativecommons.org/publicdomain/zero/1.0/"'
    ]
    for repository in repositories:
        address = bare_url(str(repository.get("url", "")))
        found = sorted(
            (
                record
                for record in records.values()
                if (repository.get("re3data") and repository["re3data"] in record["re3data"])
                or (address and address in record["addresses"])
            ),
            # A record naming the repository's re3data record first, then by DOI, so the choice never varies.
            key=lambda record: (repository.get("re3data") not in record["re3data"], record["doi"].lower()),
        )
        if found:
            blocks.append(
                "\n".join(
                    [
                        "[[annotation]]",
                        annotation_key(repository),
                        f"fairsharing = {q(found[0]['doi'])}",
                        f"fairsharingName = {q(found[0]['name'])}",
                    ]
                )
            )
    header = (
        "# The FAIRsharing record of each repository the catalogue lists, found through the DataCite metadata of\n"
        "# FAIRsharing's records. Generated by scripts/refresh_snapshots.py; do not edit by hand.\n"
    )
    return Snapshot("content/snapshots/fairsharing.toml", header, blocks, {"annotation": len(blocks) - 1}, (), today)


def datacite(fetch: Fetcher, today: str, root: Path | None = None) -> Snapshot:
    blocks = [
        "[snapshot]\n"
        f'source = "DataCite"\nurl = "https://datacite.org/"\nretrieved = {today}\n'
        'license = "https://creativecommons.org/publicdomain/zero/1.0/"'
    ]
    for repository in catalogue_repositories(root or ROOT):
        if not repository.get("doi") or repository.get("datacite"):
            continue
        name = f"datacite-{repository['re3data']}.json"
        data = fetch.json(f"{DATACITE_API}/clients?re3data-id={urllib.parse.quote(repository['doi'])}", name)
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise RejectedError(f"{name}: expected a DataCite client search result")
        clients = [str((entry or {}).get("id") or "") for entry in data["data"]]
        # Only one repository naming the record identifies it; none or several leave the repository unannotated.
        if len(clients) == 1 and DATACITE_CLIENT.fullmatch(clients[0]):
            blocks.append("\n".join(["[[annotation]]", annotation_key(repository), f"datacite = {q(clients[0])}"]))
    header = (
        "# The DataCite repository of each repository whose re3data record DataCite names. Generated by\n"
        "# scripts/refresh_snapshots.py; do not edit by hand.\n"
    )
    return Snapshot("content/snapshots/datacite.toml", header, blocks, {"annotation": len(blocks) - 1}, (), today)


SOURCES: dict[str, Callable[[Fetcher, str], Snapshot]] = {
    "heslar": heslar,
    "re3data": re3data,
    "fip-dashboard": fip_dashboard,
    "nkr": nkr,
    "knav-tools": knav_tools,
    "fairsharing": fairsharing,
    "datacite": datacite,
}


# ---------------------------------------------------------------------------
# Validation and replacement


def counts_in(path: Path, keys: list[str]) -> dict[str, int]:
    """Records per collection in an existing snapshot; an unreadable snapshot counts as none."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return {key: len(data.get(key, [])) for key in keys}


def without_date(value: str) -> str:
    return re.sub(r"(?m)^retrieved = .*$", "", value)


def commit(snapshot: Snapshot, root: Path) -> Outcome:
    """Validate a replacement against the existing snapshot and write it atomically, or explain why not."""
    target = root / snapshot.path
    previous = counts_in(target, list(snapshot.counts)) if target.exists() else {}
    outcome = Outcome("", "", snapshot.path, snapshot.counts, previous, retrieved=snapshot.retrieved)
    for key in snapshot.required:
        if snapshot.counts.get(key, 0) == 0:
            raise RejectedError(f"{snapshot.path}: the response holds no {key} records")
    for key, before in previous.items():
        after = snapshot.counts.get(key, 0)
        if before and after < before * (1 - MAX_REMOVED_SHARE):
            raise RejectedError(f"{snapshot.path}: {after} of {before} {key} records would remain")
    if not target.exists() and not any(snapshot.counts.values()):
        outcome.status, outcome.reason = "empty", "the source lists no records; nothing is written"
        return outcome
    new_text = snapshot.text()
    if target.exists() and without_date(target.read_text(encoding="utf-8")) == without_date(new_text):
        outcome.status, outcome.reason = "unchanged", "only the retrieval date would change"
        return outcome
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(new_text)
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    outcome.status = "changed"
    return outcome


def refresh(name: str, fetch: Fetcher, today: str, root: Path | None = None) -> Outcome:
    """Fetch, validate and, when safe, replace one source's snapshot. A failure never touches the snapshot."""
    root = root or ROOT
    try:
        snapshot = (
            SOURCES[name](fetch, today, root)
            if name in ("nkr", "re3data", "knav-tools", "fairsharing", "datacite")
            else SOURCES[name](fetch, today)
        )
        outcome = commit(snapshot, root)
    except RejectedError as error:
        return Outcome(name, "rejected", reason=str(error), retrieved=today)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return Outcome(name, "failed", reason=f"{type(error).__name__}: {error}", retrieved=today)
    outcome.source = name
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sources", nargs="*", help=f"sources to refresh: {', '.join(SOURCES)} (default: all)")
    parser.add_argument("--date", default=date.today().isoformat(), help="retrieval date to record (YYYY-MM-DD)")
    parser.add_argument("--input", type=Path, help="read responses from this directory instead of the network")
    parser.add_argument("--report", type=Path, help="write each source's outcome as JSON to this file")
    parser.add_argument("--root", type=Path, default=None, help="checkout whose content/ is refreshed (default: this)")
    args = parser.parse_args(argv)
    unknown = [name for name in args.sources if name not in SOURCES]
    if unknown:
        parser.error(f"unknown sources: {', '.join(unknown)}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        parser.error("--date must be YYYY-MM-DD")
    fetch = Fetcher(args.input)
    outcomes = [refresh(name, fetch, args.date, args.root) for name in args.sources or list(SOURCES)]
    for outcome in outcomes:
        counts = ", ".join(f"{key} {value}" for key, value in outcome.counts.items())
        print(
            f"{outcome.source}: {outcome.status}"
            + (f" ({counts})" if counts else "")
            + (f"; {outcome.reason}" if outcome.reason else "")
        )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps({"formatVersion": 1, "outcomes": [vars(outcome) for outcome in outcomes]}, indent=2) + "\n",
            encoding="utf-8",
        )
    return 1 if any(outcome.status in ("rejected", "failed") for outcome in outcomes) else 0


if __name__ == "__main__":
    sys.exit(main())
