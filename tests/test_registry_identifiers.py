"""FAIRsharing and DataCite shapes have one owner and one shared valid/invalid fixture."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_content  # noqa: E402
import refresh_snapshots  # noqa: E402
import registry_identifiers  # noqa: E402


class RegistryIdentifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = json.loads((ROOT / "tests/fixtures/registry_identifiers.json").read_text(encoding="utf-8"))

    def test_refresh_and_content_validation_share_the_owner(self) -> None:
        self.assertIs(refresh_snapshots.FAIRSHARING_DOI, registry_identifiers.FAIRSHARING_DOI)
        self.assertIs(check_content.FAIRSHARING_DOI, registry_identifiers.FAIRSHARING_DOI)
        self.assertIs(refresh_snapshots.DATACITE_REPOSITORY, registry_identifiers.DATACITE_REPOSITORY)
        self.assertIs(check_content.DATACITE_REPOSITORY, registry_identifiers.DATACITE_REPOSITORY)
        self.assertTrue(registry_identifiers.FAIRSHARING_DOI.flags & re.IGNORECASE)

    def test_shared_fixture_accepts_and_rejects_the_expected_forms(self) -> None:
        for value in self.fixture["fairsharing"]["valid"]:
            self.assertIsNotNone(registry_identifiers.FAIRSHARING_DOI.fullmatch(value), value)
        for value in self.fixture["fairsharing"]["invalid"]:
            self.assertIsNone(registry_identifiers.FAIRSHARING_DOI.fullmatch(value), value)
        for value in self.fixture["datacite"]["valid"]:
            self.assertIsNotNone(registry_identifiers.DATACITE_REPOSITORY.fullmatch(value), value)
        for value in self.fixture["datacite"]["invalid"]:
            self.assertIsNone(registry_identifiers.DATACITE_REPOSITORY.fullmatch(value), value)

    def test_fairsharing_output_keeps_its_published_case(self) -> None:
        self.assertEqual(
            registry_identifiers.canonical_fairsharing_doi("10.25504/fairsharing.ABC123"),
            "10.25504/FAIRsharing.ABC123",
        )
        self.assertEqual(
            registry_identifiers.canonical_fairsharing_doi("10.25504/FAIRsharing.abc123"),
            "10.25504/FAIRsharing.abc123",
        )


if __name__ == "__main__":
    unittest.main()
