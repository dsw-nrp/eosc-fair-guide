"""Check CFF, the Zenodo GitHub import profile and shared metadata without network or writes.

The profile follows Zenodo's importer at commit 1fab575d6b7eea09e5ebef5329ee366efbddc802,
site/zenodo_rdm/legacy/deserializers/metadata.py and github/schemas.py. The developer docs'
legacyrecord.json is older: it omits version and structured creator affiliations. This local
software profile explicitly accepts those fields, rejects unsupported/unknown input shapes,
and leaves remote vocabulary lookup and actual archival acceptance to Zenodo.

Usage: python scripts/check_citation_metadata.py [--root DIR]
Requires the repository's pinned requirements-dev.txt; does not modify either metadata file.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

import release_versions
import yaml
from cffconvert import Citation
from jsonschema import Draft7Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
TEXT = {"type": "string", "minLength": 1}
PERSON = {
    "type": "object",
    "required": ["name"],
    "additionalProperties": False,
    "properties": {
        "name": TEXT,
        "orcid": {"type": "string", "pattern": r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"},
        "gnd": TEXT,
        "affiliation": TEXT,
        "affiliations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "anyOf": [{"required": ["id"]}, {"required": ["name"]}],
                "properties": {"id": {"type": "string", "pattern": r"^0[0-9a-hj-km-np-tv-z]{6}\d{2}$"}, "name": TEXT},
            },
        },
    },
}
RELATIONS = [
    "isCitedBy",
    "cites",
    "isSupplementTo",
    "isSupplementedBy",
    "isContinuedBy",
    "continues",
    "isDescribedBy",
    "describes",
    "hasMetadata",
    "isMetadataFor",
    "isNewVersionOf",
    "isPreviousVersionOf",
    "isPartOf",
    "hasPart",
    "isReferencedBy",
    "references",
    "isDocumentedBy",
    "documents",
    "isCompiledBy",
    "compiles",
    "isVariantFormOf",
    "isOriginalFormOf",
    "isIdenticalTo",
    "isAlternateIdentifier",
    "isReviewedBy",
    "reviews",
    "isDerivedFrom",
    "isSourceOf",
    "requires",
    "isRequiredBy",
    "isObsoletedBy",
    "obsoletes",
    "isPublishedIn",
]
ROLES = [
    "ContactPerson",
    "DataCollector",
    "DataCurator",
    "DataManager",
    "Distributor",
    "Editor",
    "HostingInstitution",
    "Producer",
    "ProjectLeader",
    "ProjectManager",
    "ProjectMember",
    "RegistrationAgency",
    "RegistrationAuthority",
    "RelatedPerson",
    "Researcher",
    "ResearchGroup",
    "RightsHolder",
    "Supervisor",
    "Sponsor",
    "WorkPackageLeader",
    "Other",
]
PROFILE = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title",
        "upload_type",
        "description",
        "creators",
        "version",
        "publication_date",
        "access_right",
        "license",
    ],
    "properties": {
        **{
            key: TEXT
            for key in (
                "title",
                "description",
                "version",
                "license",
                "notes",
                "doi",
                "language",
                "method",
                "access_conditions",
                "imprint_publisher",
                "imprint_place",
                "imprint_isbn",
                "journal_title",
                "journal_volume",
                "journal_issue",
                "journal_pages",
                "conference_title",
                "conference_acronym",
                "conference_dates",
                "conference_place",
                "conference_url",
                "conference_session",
                "conference_session_part",
                "partof_title",
                "partof_pages",
                "thesis_university",
            )
        },
        "upload_type": {"const": "software"},
        "publication_date": {"type": "string", "format": "date"},
        "embargo_date": {"type": "string", "format": "date"},
        "access_right": {"enum": ["open", "embargoed", "restricted", "closed"]},
        "creators": {"type": "array", "minItems": 1, "items": PERSON},
        "contributors": {
            "type": "array",
            "items": {
                **PERSON,
                "required": ["name", "type"],
                "properties": {**PERSON["properties"], "type": {"enum": ROLES}},
            },
        },
        "keywords": {"type": "array", "uniqueItems": True, "items": TEXT},
        "references": {"type": "array", "items": TEXT},
        "related_identifiers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["identifier", "relation"],
                "additionalProperties": False,
                "properties": {
                    "identifier": TEXT,
                    "relation": {"enum": RELATIONS},
                    "scheme": TEXT,
                    "resource_type": TEXT,
                },
            },
        },
        "grants": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id"],
                "additionalProperties": False,
                "properties": {"id": TEXT},
            },
        },
        "communities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["identifier"],
                "additionalProperties": False,
                "properties": {"identifier": TEXT},
            },
        },
        "custom": {"type": "object"},
    },
}


def unique_object(pairs):
    """JSON must not hide a stale value behind a duplicate key."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f".zenodo.json duplicate key: {key}")
        result[key] = value
    return result


def normalized(value: str) -> str:
    return " ".join(value.split())


def orcid(value: str) -> str:
    return value.removeprefix("https://orcid.org/").rstrip("/")


def credits(cff: dict, zenodo: dict, guide: dict) -> list[str]:
    """CFF owns software authorship; reviewed Guide identities own structured affiliation IDs."""
    errors = []
    expected = []
    for author in cff["authors"]:
        name = author.get("name") or ", ".join(filter(None, [author.get("family-names"), author.get("given-names")]))
        expected.append((normalized(name), orcid(author.get("orcid", ""))))
    actual = [(normalized(person["name"]), orcid(person.get("orcid", ""))) for person in zenodo["creators"]]
    if actual != expected:
        errors.append(".zenodo.json creators must match CITATION.cff software authors and ORCIDs in order")
    organizations = {item["id"]: item for item in guide.get("organization", [])}
    people = {orcid(item["orcid"]): item for item in guide.get("person", []) if item.get("orcid")}
    for index, creator in enumerate(zenodo["creators"]):
        if "affiliation" in creator and "affiliations" in creator:
            errors.append(
                f".zenodo.json creators/{index}: use one affiliation form; the scalar overrides structured IDs"
            )
        affiliations = creator.get("affiliations")
        if affiliations is None:
            continue
        person = people.get(orcid(creator.get("orcid", "")))
        if not person:
            errors.append(f".zenodo.json creators/{index}: structured affiliations need a reviewed Guide person/ORCID")
            continue
        reviewed = [organizations[key] for key in person.get("affiliation", [])]
        expected_ids = {item["ror"].rsplit("/", 1)[-1] for item in reviewed if item.get("ror")}
        actual_ids = {item.get("id") for item in affiliations}
        if actual_ids != expected_ids or len(actual_ids) != len(affiliations):
            errors.append(f".zenodo.json creators/{index}: affiliations must match the reviewed organization ROR IDs")
        by_ror = {item["ror"].rsplit("/", 1)[-1]: item for item in reviewed if item.get("ror")}
        for item in affiliations:
            organization = by_ror.get(item.get("id"))
            if organization and item.get("name") and item["name"] != organization["name"]["en"]:
                errors.append(f".zenodo.json creators/{index}: affiliation name differs from the reviewed English name")
    return errors


def check(root: Path) -> list[str]:
    """Return actionable diagnostics; no network or file writes, even on malformed input."""
    try:
        raw = (root / "CITATION.cff").read_text(encoding="utf-8")
        Citation(raw).validate()
        cff = yaml.safe_load(raw)
    except Exception as error:  # cffconvert uses several schema/YAML exception types
        return [f"CITATION.cff schema validation failed: {error}"]
    try:
        zenodo = json.loads((root / ".zenodo.json").read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    except (OSError, ValueError) as error:
        return [f".zenodo.json: {error}"]
    errors = [
        f".zenodo.json {'/'.join(map(str, error.path)) or 'root'}: {error.message}"
        for error in Draft7Validator(PROFILE, format_checker=FormatChecker()).iter_errors(zenodo)
    ]
    if errors:
        return errors
    try:
        guide = tomllib.loads((root / "content/guide.toml").read_text(encoding="utf-8"))
        errors.extend(release_versions.metadata(root)[2])
        errors.extend(credits(cff, zenodo, guide))
        for key in ("title", "keywords"):
            if zenodo.get(key) != cff.get(key):
                errors.append(f".zenodo.json {key} differs from CITATION.cff")
        abstract = normalized(cff.get("abstract", ""))
        links = f"Online guide: {cff.get('url', '')}\nSource code: {cff.get('repository-code', '')}"
        if normalized(zenodo["description"]) not in {abstract, normalized(abstract + "\n\n" + links)}:
            errors.append(
                ".zenodo.json description must match the CFF abstract, optionally followed by its guide/source links"
            )
        license_value = cff.get("license")
        if not isinstance(license_value, str) or zenodo["license"].casefold() != license_value.casefold():
            errors.append(".zenodo.json license must match the single CITATION.cff software license")
        cited = {
            item["identifier"].removeprefix("https://doi.org/")
            for item in zenodo.get("related_identifiers", [])
            if item["relation"] == "cites"
        }
        for reference in cff.get("references", []):
            if reference.get("doi") and reference["doi"] not in cited:
                errors.append(".zenodo.json related_identifiers must retain the CFF reference DOI with relation cites")
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append(f"citation metadata: {error}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    errors = check(args.root)
    for error in errors:
        print(f"citation_metadata: {error}", file=sys.stderr)
    if not errors:
        print("citation_metadata: CFF schema, Zenodo import profile and shared fields agree (offline)")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
