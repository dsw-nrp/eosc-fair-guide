"""Release-version acceptance, checked against the Node predicate through shared fixtures."""

import re

VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?")


def version(value: str) -> str:
    """Accept a release or prerelease without leading v, build suffix or leading-zero numeric identifiers."""
    match = VERSION.fullmatch(value)
    if not match or any(re.fullmatch(r"0\d+", part) for part in (match[4] or "").split(".")):
        raise ValueError("version must be a SemVer release or prerelease without a leading v or build suffix")
    return value
