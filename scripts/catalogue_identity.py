"""Guide-owned record identity and compact route vocabulary.

Every normalized record owns id. Genuine source IDs are typed alternateIds, never a second primary field.
Only the locally owned ID and optional frozen route prefix are persisted, never a second table of full paths.
"""

from __future__ import annotations

import html
import json
import re
import tomllib
import unicodedata
from typing import Any
from urllib.parse import unquote, urlsplit


def bare_url(value: Any) -> str:
    """Match addresses by the shared normalization fixture, without discarding query or fragment identity."""
    address = re.sub(r"^https?://", "", str(value or "").strip().lower())
    return re.sub(r"^www\.", "", address).rstrip("/")


KIND_CODES = {
    "resources": "res",
    "repositories": "repo",
    "infrastructures": "ri",
    "principles": "pr",
    "stations": "step",
    "checks": "check",
    "questions": "q",
    "terms": "term",
    "tests": "test",
    "fips": "fip",
    "clauses": "cl",
    "model": "model",
    "lifecycle": "life",
    "actions": "act",
    "organizations": "org",
}
TYPE_CODES = {
    "service": "srv",
    "standard": "std",
    "registry": "reg",
    "general": "gen",
    "domain": "dom",
    "institutional": "inst",
    "fair-champion": "fc",
    "fair-checker": "fcx",
    "provenance-model": "prov",
    "vocabulary": "vocab",
    "infrastructure": "infra",
    "training": "train",
    "article": "art",
    "guidance": "guide",
    "policy": "pol",
    "social-sciences-humanities": "ssh",
    "environmental-sciences": "env",
    "physical-sciences": "phys",
    "biological-medical-sciences": "bio",
    "information-sciences": "info",
    "energy": "energy",
    "biological-and-medical-sciences": "bio",
    "physical-sciences-and-engineering": "phys",
    "social-sciences-and-humanities": "ssh",
    "e-infrastructures": "einfra",
    "community": "comm",
    "document": "doc",
    "publication": "pub",
    "project": "proj",
    "licence": "lic",
    "course": "course",
}
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
MAX_ID = 32
PARTICLES = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "for",
        "to",
        "in",
        "on",
        "at",
        "by",
        "with",
        "from",
        "into",
        "as",
        "via",
        "per",
        "over",
        "under",
        "between",
        "without",
        "within",
        "through",
        "about",
        "after",
        "before",
        "since",
        "until",
        "during",
        "but",
        "nor",
        "do",
        "na",
        "nad",
        "pod",
        "pro",
        "se",
        "ve",
        "v",
        "z",
        "ze",
        "k",
        "ke",
        "u",
    ]
)
RECORD_KINDS = {"term", "tool", "resource", "repository", "organization", "fip", "record"}
IDENTITY_FIELDS = ("url", "mainUrl", "identifier", "doi", "re3data", "ror")


def has_particles(identifier: str) -> bool:
    """SPDX BY means attribution, rather than the English preposition; keep official licence codes whole."""
    if re.fullmatch(r"cc-by(?:-(?:nc|nd|sa))*-\d[.-]\d", identifier, re.I):
        return False
    return bool(set(re.split(r"[-_]", identifier.casefold())) & PARTICLES)


def short_id(value: str, used: set[str]) -> str:
    """Mint once locally, with a bounded readable seed; source changes never rerun this for existing rows."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    words = [word for word in re.findall(r"[a-z0-9]+", value) if word not in PARTICLES]
    selected = []
    for word in words:
        if len(word) > MAX_ID:
            continue
        if selected and len("-".join([*selected, word])) > MAX_ID:
            break
        selected.append(word)
    seed = "-".join(selected) or "entry"
    result, serial = seed, 2
    while result in used:
        suffix = f"-{serial}"
        root = seed
        while len(root + suffix) > MAX_ID:
            if "-" not in root:
                raise ValueError("Guide slug collision needs a shorter reviewed abbreviation")
            root = root.rsplit("-", 1)[0]
        result = root + suffix
        serial += 1
    used.add(result)
    return result


def record_name(row: dict[str, Any]) -> str:
    value = row.get("acronym") or row.get("name") or row.get("label") or row.get("title") or row.get("repositoryName")
    if isinstance(value, dict):
        value = value.get("en") or value.get("cs")
    return html.unescape(str(value or "entry")).split(" / ", 1)[0].split(";", 1)[0]


def identity_seed(row: dict[str, Any]) -> str:
    """Choose a readable initial seed, never an ongoing source-derived identity."""
    abbreviation = row.get("acronym") or row.get("abbreviation")
    if isinstance(abbreviation, dict):
        abbreviation = abbreviation.get("en") or abbreviation.get("cs")
    if abbreviation:
        return str(abbreviation)
    generic = {
        "www",
        "example",
        "org",
        "net",
        "com",
        "eu",
        "cz",
        "uk",
        "ac",
        "gov",
        "html",
        "php",
        "index",
        "home",
        "about",
        "us",
        "en",
        "cs",
        "submit",
        "search",
        "new",
        "tool",
        "repository",
        "resources",
        "api",
        "overview",
        "start",
        "dashboard",
        "session_contexts",
        "session-contexts",
        "batch_connect",
        "batch-connect",
        "sys",
        "pun",
        "services",
        "docs",
        "documentation",
        "display",
    }
    for field in ("url", "mainUrl"):
        value = row.get(field)
        if not isinstance(value, str):
            continue
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if host in {"www.re3data.org", "re3data.org", "heslar.openscience.cz", "doi.org", "purl.org", "w3id.org"}:
            continue  # A registry record or resolver URL does not name the described service.
        parts = [unquote(part).split(".")[0] for part in parsed.path.split("/") if part]
        specific = [part for part in parts if part.casefold() not in generic and len(part) >= 3 and not part.isdigit()]
        if specific:
            return specific[-1]
        labels = [part for part in host.split(".") if part not in generic and len(part) >= 3]
        if labels:
            return labels[0]
    return record_name(row)


def identity_values(row: dict[str, Any]) -> set[str]:
    return {str(row[field]).rstrip("/") for field in IDENTITY_FIELDS if isinstance(row.get(field), str) and row[field]}


def metadata_value(value: Any) -> str:
    """Render the small metadata values as TOML, including reviewed language maps."""
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{json.dumps(key)} = {metadata_value(item)}" for key, item in value.items()) + " }"
    if isinstance(value, list):
        return "[" + ", ".join(metadata_value(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def alternate_id(row: dict[str, Any], scheme: str) -> str | None:
    """Read a genuine typed source identifier; never reinterpret the primary ID as an external identifier."""
    values = {str(item["value"]) for item in row.get("alternateIds", []) if item.get("scheme") == scheme}
    if len(values) > 1:
        raise ValueError(f"{row.get('id')}: ambiguous {scheme} identifiers need review")
    return next(iter(values), None)


def validate_identity(row: dict[str, Any], scheme: str | None = None) -> None:
    """Reject competing primaries and untyped or missing source identifiers at normalization boundaries."""
    identifier = row.get("id")
    if not isinstance(identifier, str) or not SAFE_ID.fullmatch(identifier) or len(identifier) > MAX_ID:
        raise ValueError("record requires one safe primary id of at most 32 characters")
    if "guideId" in row:
        raise ValueError(f"{identifier}: obsolete guideId field; id is the one primary value")
    if has_particles(identifier):
        raise ValueError(f"{identifier}: primary slug contains a particle")
    alternates = row.get("alternateIds", [])
    if not isinstance(alternates, list):
        raise ValueError(f"{identifier}: alternateIds must be typed source identifiers")
    seen = set()
    for item in alternates:
        if (
            not isinstance(item, dict)
            or set(item) != {"scheme", "value"}
            or any(not isinstance(value, str) or not value.strip() for value in item.values())
        ):
            raise ValueError(f"{identifier}: every alternate needs a real source scheme and value")
        if item["scheme"] in seen:
            raise ValueError(f"{identifier}: ambiguous {item['scheme']} identifiers need review")
        seen.add(item["scheme"])
    if scheme and not alternate_id(row, scheme):
        raise ValueError(f"{identifier}: missing genuine {scheme} source identifier")


def source_scheme(data: dict[str, Any], kind: str) -> str:
    source = data.get("snapshot", {}).get("source", "")
    schemes = {
        "FIP Dashboard": "fip-dashboard",
        "KNAV Data Management Tools Catalogue": "knav",
        "re3data": "re3data",
        "NKR": "nkr",
    }
    if source in schemes:
        return schemes[source]
    return {"term": "heslar", "tool": "knav", "repository": "re3data", "record": "nkr"}.get(kind, "fip-dashboard")


def preserve_snapshot(
    new_text: str, old_text: str, reserved: set[str] | None = None, resource_types: dict[str, str] | None = None
) -> str:
    """Carry local IDs/prefixes across source refresh, refusing conflicting or ambiguous identity joins.

    A changed source ID may join through an exact authoritative URL/identifier. A name alone never merges rows.
    New fields are inserted into the generated TOML without rewriting source passages or their formatting.
    """
    incoming, existing = tomllib.loads(new_text), tomllib.loads(old_text) if old_text else {}
    for kind in RECORD_KINDS:
        for row in existing.get(kind, []):
            validate_identity(row, source_scheme(existing, kind))
    used = set(reserved or ())
    for key in RECORD_KINDS:
        used.update(str(row["id"]) for row in existing.get(key, []))
    used.update(existing.get("identity", {}).get("retiredIds", []))
    previous_ids = used - set(reserved or ())
    additions: dict[tuple[str, str], dict[str, Any]] = {}
    retained: set[str] = set()
    for kind in RECORD_KINDS:
        old = existing.get(kind, [])
        scheme = source_scheme(incoming, kind)
        claimed: set[str] = set()
        for row in incoming.get(kind, []):
            exact = [item for item in old if alternate_id(item, scheme) == str(row.get("id"))]
            matches = exact or [item for item in old if identity_values(item) & identity_values(row)]
            owners = {item["id"] for item in matches}
            if len(owners) > 1:
                raise ValueError(f"{kind}:{row.get('id')}: ambiguous Guide identity; review the source change")
            previous = next(iter(matches), None)
            if previous:
                identifier = previous["id"]
                if identifier in claimed:
                    raise ValueError(
                        f"{kind}:{row.get('id')}: source split would duplicate Guide identity {identifier}"
                    )
                fields = {key: previous[key] for key in ("id", "guideRoute", "linkNames") if previous.get(key)}
            else:
                if any(record_name(item).casefold() == record_name(row).casefold() for item in old):
                    raise ValueError(f"{kind}:{row.get('id')}: changed identity with the same name needs review")
                identifier = short_id(identity_seed(row), used)
                fields = {"id": identifier}
            fields["alternateIds"] = [
                item for item in (previous or {}).get("alternateIds", []) if item.get("scheme") != scheme
            ] + [{"scheme": scheme, "value": str(row["id"])}]
            if "guideRoute" not in fields:
                prefix = {"term": "term", "tool": "res/tool", "organization": "org", "fip": "fip"}.get(kind)
                if kind == "resource":
                    category = (resource_types or {}).get(str(row.get("type")), "tool")
                    prefix = "repo" if row.get("type") == "repository" else "res/" + TYPE_CODES.get(category, category)
                elif kind == "repository":
                    subtype = TYPE_CODES.get(str(row.get("kind")), str(row.get("kind") or ""))
                    prefix = "/".join(filter(None, ("repo", subtype)))
                elif kind == "record" and incoming.get("snapshot", {}).get("source") == "NKR":
                    prefix = "repo"
                if prefix:
                    fields["guideRoute"] = prefix
            claimed.add(identifier)
            retained.add(identifier)
            additions[(kind, str(row.get("id")))] = fields
    blocks = re.split(r"(?m)(?=^\[\[[A-Za-z][A-Za-z0-9_-]*\]\]\s*$)", new_text)
    for index, original_block in enumerate(blocks):
        block = original_block
        match = re.match(r"\[\[([A-Za-z][A-Za-z0-9_-]*)\]\]", block)
        identifier = re.search(r'^id\s*=\s*("(?:[^"\\]|\\.)*")\s*$', block, re.M)
        if not match or not identifier:
            continue
        fields = additions.get((match[1], str(json.loads(identifier[1]))))
        if fields:
            block = re.sub(r"(?m)^(?:id|alternateIds|guideRoute|linkNames)\s*=.*\n?", "", block)
            end = block.index("\n") + 1
            blocks[index] = (
                block[:end]
                + "".join(
                    f"{key} = {metadata_value(value)}\n"
                    for key, value in (
                        (key, fields[key]) for key in ("id", "alternateIds", "guideRoute", "linkNames") if key in fields
                    )
                )
                + block[end:]
            )
    result = "".join(blocks)
    retired = sorted(previous_ids - retained)
    if retired:
        result += "\n[identity]\nretiredIds = " + metadata_value(retired) + "\n"
    return result
