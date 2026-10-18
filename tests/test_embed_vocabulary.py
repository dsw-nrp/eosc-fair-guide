"""The dependency-free embed snippet accepts exactly the application's language, lens and view vocabulary."""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def vocabulary(embed_text: str) -> tuple[list[str], list[str], list[str]]:
    match = re.search(r"\(([^()]+)\)\\/\(([^()]+)\)\\/\(([^()]+)\)", embed_text)
    if match is None:
        raise AssertionError("embed validView does not expose its language/lens/view alternations")
    return tuple(part.split("|") for part in match.groups())  # type: ignore[return-value]


class EmbedVocabularyTests(unittest.TestCase):
    def core_vocabulary(self) -> tuple[list[str], list[str]]:
        core = (ROOT / "assets/js/core.js").read_text(encoding="utf-8")
        languages = re.search(r"const LANGS = \[([^\]]*)\];", core)
        views = re.search(r"const VIEWS = \[([^\]]*)\];", core)
        self.assertIsNotNone(languages)
        self.assertIsNotNone(views)
        return (
            re.findall(r'"([^"]+)"', languages.group(1)),
            re.findall(r'"([^"]+)"', views.group(1)),
        )

    def guide_lenses(self) -> list[str]:
        guide = tomllib.loads((ROOT / "content/guide.toml").read_text(encoding="utf-8"))
        return [lens["id"] for lens in guide["lens"]]

    def assert_vocabulary(self, embed_text: str, languages: list[str], lenses: list[str], views: list[str]) -> None:
        actual_languages, actual_lenses, actual_views = vocabulary(embed_text)
        self.assertEqual(actual_languages, languages)
        self.assertEqual(actual_lenses, lenses)
        self.assertEqual(actual_views, views)

    def test_embed_matches_the_application_vocabulary(self) -> None:
        languages, views = self.core_vocabulary()
        self.assert_vocabulary(
            (ROOT / "assets/js/embed.js").read_text(encoding="utf-8"),
            languages,
            self.guide_lenses(),
            views,
        )

    def test_entity_route_ids_are_not_views(self) -> None:
        _, _, views = vocabulary((ROOT / "assets/js/embed.js").read_text(encoding="utf-8"))
        self.assertNotIn("resources", views)
        self.assertNotIn("repositories", views)

    def test_a_planted_view_divergence_is_refused(self) -> None:
        languages, views = self.core_vocabulary()
        planted = (
            (ROOT / "assets/js/embed.js").read_text(encoding="utf-8").replace("(path|check|", "(resources|path|check|")
        )
        with self.assertRaises(AssertionError):
            self.assert_vocabulary(planted, languages, self.guide_lenses(), views)


if __name__ == "__main__":
    unittest.main()
