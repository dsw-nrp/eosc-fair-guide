"""The one place the Python tests name the Guide's records (design.md, decision 3).

A record is named by its address, `<kind>/<id>` or `<kind>/<scope>/<id>`, and a part of it by the address and a
fragment. The helpers turn an address into what the build publishes for it: the record's IRI in the crate, its API
file and its page route. Tests name records only through these, never by the build's internal keys.
"""

from __future__ import annotations

from typing import Any

# The Guide's namespace, as content/guide.toml declares it; a content fixture declares its own.
GUIDE_NAMESPACE = "https://w3id.org/eosc-cz/fair-guide/"


def iri(address: str, namespace: str = GUIDE_NAMESPACE) -> str:
    """The published IRI of a record, or of a part of one (`<address>#<fragment>`)."""
    return f"{namespace}id/{address}"


def iri_in(content: dict[str, Any], address: str) -> str:
    """The IRI of a record in the namespace the loaded content declares, for content fixtures."""
    return content["guide"]["guide"]["recordBase"] + address


def address_of(identifier: str, namespace: str = GUIDE_NAMESPACE) -> str:
    """The address a published IRI names."""
    base = f"{namespace}id/"
    if not identifier.startswith(base):
        raise ValueError(f"{identifier} is not a record of {namespace}")
    return identifier[len(base) :]


def api_file(address: str) -> str:
    """The API file of a record."""
    return f"api/{address}.json"


def route(address: str, lang: str = "cs", lens: str = "V") -> str:
    """The page route of a record's catalogue entry."""
    return f"#/{lang}/{lens}/catalogue/{address}"
