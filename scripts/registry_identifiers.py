"""The one owner of registry identifier shapes shared by snapshot refresh and content validation.

FAIRsharing answers in lower case while its published DOI uses `FAIRsharing`; recognition is
case-insensitive and the canonical form is restored where a value is written. A DataCite repository
ID is a lower-case DataCite client (`<member>.<repository>`).
"""

from __future__ import annotations

import re

FAIRSHARING_DOI = re.compile(r"10\.25504/FAIRsharing\.[A-Za-z0-9]+", re.IGNORECASE)
DATACITE_REPOSITORY = re.compile(r"[a-z0-9]+\.[a-z0-9][a-z0-9.-]*")


def canonical_fairsharing_doi(value: str) -> str:
    """Return the published case form for a FAIRsharing DOI."""
    return re.sub(r"(?i)^10\.25504/fairsharing\.", "10.25504/FAIRsharing.", str(value))
