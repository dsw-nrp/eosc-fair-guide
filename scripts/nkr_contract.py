"""Reviewed NKR value shapes and status vocabulary for harvest, catalogue and content checks."""

# Shapes consumed by the Guide, independently of what a future upstream schema permits.
NKR_FIELD_SHAPES = {
    "repositoryName": {"type": "string"},
    "additionalNames": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["additionalName"],
            "properties": {"additionalName": {"type": "string"}, "lang": {"type": "string"}},
        },
    },
    "mainUrl": {"type": "string"},
    "type": {"type": "string"},
    "status": {"type": "string"},
    "keywordCz": {"type": "array", "items": {"type": "string"}},
    "keywordEn": {"type": "array", "items": {"type": "string"}},
}

NKR_PILOT_NOT_ACCEPTING = "pilot - not accepting data"
NKR_STATUS = {
    "intended": "planned",
    "development": "in-development",
    "test": "in-development",
    NKR_PILOT_NOT_ACCEPTING: "pilot",
    "pilot - accepting data": "pilot",
    "production": "operational",
    # This spelling is published by NKR's Repository schema.
    "decomissioned": None,
}


def nkr_status(value: str) -> str | None:
    """Unknown values need review; they must never silently become a missing Guide status."""
    if not isinstance(value, str) or value not in NKR_STATUS:
        raise ValueError(f"unreviewed NKR status: {value!r}")
    return NKR_STATUS[value]
