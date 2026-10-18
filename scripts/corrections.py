"""Reviewed local corrections applied after a verbatim snapshot is loaded.

A correction never edits the snapshot. It records the source, the exact finding, the replacement, the
reason and the tracking issue, and is applied to the in-memory glossary the guide builds from.
"""

from __future__ import annotations

from typing import Any

CORRECTION_FIELDS = ("id", "source", "term", "field", "language", "find", "replace", "reason", "issue")
LANGUAGES = ("cs", "en")
TEXT_FIELDS = ("definition", "label")


def _terms(glossary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {term.get("id"): term for term in glossary.get("term", []) if isinstance(term, dict)}


def validate_fields(corrections: list[dict[str, Any]], glossary: dict[str, Any]) -> list[str]:
    """Required fields, a real target term and a URL-shaped source and issue link."""
    errors: list[str] = []
    terms = _terms(glossary)
    seen: set[str] = set()
    for correction in corrections:
        where = f"correction:{correction.get('id', '')}"
        for field in CORRECTION_FIELDS:
            value = correction.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{where}: missing {field}")
        if correction.get("field") not in TEXT_FIELDS:
            errors.append(f"{where}: field must be one of {', '.join(TEXT_FIELDS)}")
        if correction.get("language") not in LANGUAGES:
            errors.append(f"{where}: language must be one of {', '.join(LANGUAGES)}")
        if correction.get("id") in seen:
            errors.append(f"{where}: duplicate correction id")
        seen.add(correction.get("id"))
        term = terms.get(correction.get("term"))
        if term is None:
            errors.append(f"{where}: term '{correction.get('term')}' does not exist")
        elif not isinstance(term.get(correction.get("field")), str):
            errors.append(f"{where}: target field is not text")
        for field in ("source", "issue"):
            value = correction.get(field)
            if isinstance(value, str) and value and not value.startswith(("https://", "http://")):
                errors.append(f"{where}: {field} must be an address")
    return errors


def apply(corrections: list[dict[str, Any]], glossary: dict[str, Any]) -> None:
    """Apply each correction exactly once; an absent or ambiguous finding refuses the whole content load."""
    errors = validate_fields(corrections, glossary)
    if errors:
        raise ValueError("; ".join(errors))
    terms = _terms(glossary)
    for correction in corrections:
        term = terms[correction["term"]]
        field = correction["field"]
        text = term[field]
        if text.count(correction["find"]) != 1:
            raise ValueError(
                f"correction:{correction['id']}: '{correction['find']}' occurs {text.count(correction['find'])} times"
            )
        term[field] = text.replace(correction["find"], correction["replace"], 1)
