"""Run every published query recipe against the generated graph and its reviewed expected result."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

from rdflib import Graph, URIRef

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402
from knowledge_graph import NT_FILE  # noqa: E402

NAMESPACES = {
    "schema": "http://schema.org/",
    "guide": "https://w3id.org/eosc-cz/fair-guide/terms#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "sio": "http://semanticscience.org/resource/",
}


def rows(query: str, graph: Graph) -> dict[str, object]:
    """A deterministic ordinary-JSON result table, with no implicit graph or FAIR-score interpretation."""
    result = graph.query(query)
    columns = [str(variable) for variable in result.vars]
    values = sorted([str(row[column]) if row[column] is not None else None for column in columns] for row in result)
    return {"columns": columns, "rows": values}


def renamed_property(graph: Graph, query: str) -> Graph:
    """Rename the first relation predicate of a recipe in a graph copy, leaving the query unchanged."""
    predicates = re.findall(
        r"(?m)^\s*(schema|guide|foaf|sio):([A-Za-z][\w-]*)",
        "\n".join(line for line in query.splitlines() if not line.startswith("#")),
    )
    if not predicates:
        raise AssertionError("the recipe contains no relation predicate to rename")
    prefix, local = predicates[0]
    original, replacement = URIRef(NAMESPACES[prefix] + local), URIRef("urn:renamed:" + local)
    copy = Graph()
    for subject, predicate, obj in graph:
        copy.add((subject, replacement if predicate == original else predicate, obj))
    return copy


class RecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = build_crate.load_content()
        cls.guide = cls.content["guide"]["guide"]
        cls.generated = build_crate.outputs(content=cls.content)
        cls.graph = Graph().parse(data=cls.generated[NT_FILE], format="nt", publicID=cls.guide["pageUrl"])
        cls.source = ROOT / build_crate.PROFILE_DIR / "recipes"
        cls.published = "profile/" + cls.guide["profileVersion"] + "/recipes/"
        cls.recipes = sorted(cls.source.glob("*.rq"))

    def test_all_six_recipes_are_published_bilingually_and_match_their_fixtures(self) -> None:
        self.assertEqual(len(self.recipes), 6, "the six reviewed recipes")
        for path in self.recipes:
            with self.subTest(recipe=path.stem):
                query = self.generated[self.published + path.name]
                self.assertRegex(query, r"(?m)^# cs: \S")
                self.assertRegex(query, r"(?m)^# en: \S")
                result = rows(query, self.graph)
                self.assertTrue(result["rows"], "a useful example must return rows")
                fixture = ROOT / "tests" / "fixtures" / "recipes" / (path.stem + ".json")
                self.assertEqual(result, json.loads(fixture.read_text(encoding="utf-8")))
                self.assertTrue(build_crate.is_generated(self.published + path.name))

    def test_a_renamed_property_breaks_every_recipe(self) -> None:
        for path in self.recipes:
            with self.subTest(recipe=path.stem):
                copy = renamed_property(self.graph, self.generated[self.published + path.name])
                self.assertEqual(len(copy), len(self.graph), "renaming a property, not deleting a triple")
                self.assertEqual(rows(self.generated[self.published + path.name], copy)["rows"], [])


if __name__ == "__main__":
    unittest.main()
