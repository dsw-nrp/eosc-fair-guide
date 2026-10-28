"""Release-version acceptance, checked against the Node predicate through shared fixtures."""

import re

VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?")


def version(value: str) -> str:
    """Accept a release or prerelease without leading v, build suffix or leading-zero numeric identifiers."""
    match = VERSION.fullmatch(value)
    if not match or any(re.fullmatch(r"0\d+", part) for part in (match[4] or "").split(".")):
        raise ValueError("version must be a SemVer release or prerelease without a leading v or build suffix")
    return value


ACCEPTED_FORM = "a SemVer release or prerelease such as 1.0.0-alpha.4 or v1.0.0-alpha.4"


def release_input(value: str) -> str:
    """A maintainer's dispatch input: surrounding whitespace and one leading v are dropped, then `version` decides.
    Tags, artifacts and images keep `version` alone."""
    bare = value.strip()
    bare = bare.removeprefix("v")
    try:
        return version(bare)
    except ValueError:
        raise ValueError(f"{value!r} is not {ACCEPTED_FORM}") from None
