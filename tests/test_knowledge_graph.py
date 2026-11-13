"""The standard-library N-Triples distribution equals the crate and never resolves a remote context."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

from rdflib import Graph as RdfGraph
from rdflib.compare import isomorphic

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import build_crate  # noqa: E402
from knowledge_graph import NT_FILE, n_triples  # noqa: E402
from vocabularies import crate_graph  # noqa: E402


class KnowledgeGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.crate = build_crate.build_crate(build_crate.load_content())
        cls.base = "https://example.test/guide/"

    def test_full_crate_is_isomorphic_without_a_network(self) -> None:
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network access attempted")) as opener:
            text = n_triples(self.crate, self.base)
            self.assertEqual(text, n_triples(self.crate, self.base))
            expected = crate_graph(self.crate, self.base)
            actual = RdfGraph().parse(data=text, format="nt", publicID=self.base)
        opener.assert_not_called()
        self.assertGreater(len(actual), 0)
        self.assertEqual(
            len(actual),
            len(expected),
            f"N-Triples has {len(actual) - len(expected)} more triples than the crate",
        )
        self.assertTrue(isomorphic(actual, expected), "N-Triples differs from the crate's RDF graph")

    def test_output_uses_its_crate_base_and_escapes_literals(self) -> None:
        text = n_triples(
            {
                "@context": [{"example": "https://vocab.example/"}],
                "@graph": [
                    {
                        "@id": "./",
                        "@type": "CreativeWork",
                        "name": [{"@value": 'Czech "quote" and \n newline', "@language": "cs"}],
                        "example:local": {"@id": "ro-crate-metadata.json#record"},
                    }
                ],
            },
            self.base,
        )
        self.assertIn("<https://example.test/guide/>", text)
        self.assertIn("<https://example.test/guide/ro-crate-metadata.json#record>", text)
        self.assertIn('"Czech \\"quote\\" and \\n newline"@cs', text)
        self.assertNotIn("file://", text)

    def test_build_emits_the_distribution(self) -> None:
        outputs = build_crate.outputs(crate=self.crate)
        self.assertIn(NT_FILE, outputs)
        base = build_crate.page_config(build_crate.load_content())["config"]["pageUrl"]
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network access attempted")) as opener:
            graph = RdfGraph().parse(data=outputs[NT_FILE], format="nt", publicID=base)
        opener.assert_not_called()
        self.assertGreater(len(graph), 0)


if __name__ == "__main__":
    unittest.main()
