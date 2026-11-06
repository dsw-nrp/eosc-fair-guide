"""The page names records by their addresses and reads a kind from the address (design.md, decision 15). No page
script may still test an entity by one of the build's former fragment prefixes (`"#station-"`), which name no
published record any more. The crate's own nodes (`#repositories`, `#snapshot-datacite`) keep their names, and a part
is its record's address with its own fragment (`#fip-dashboard`, `#step-1`)."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_crate as kb  # noqa: E402

# A string literal that starts with a fragment and a family word: `"#station-`, `'#lens-V'`.
LITERAL = re.compile(r"""["'`](#([a-z][a-z0-9]*)-[^"'`\s]*)""")


def retired_literals(text: str, retired: set[str], kept: set[str], fragments: set[str]) -> list[tuple[int, str]]:
    """Each literal of a retired family, by line, that is neither one of the crate's own nodes nor a part's whole
    fragment (a page section may be called `#station-tips`, so a prefix alone never passes)."""
    return [
        (number, match[1])
        for number, line in enumerate(text.splitlines(), start=1)
        for match in LITERAL.finditer(line)
        if match[2] in retired and match[1] not in kept and match[1] not in fragments
    ]


class PageIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content = kb.load_content()
        graph = kb.Graph()
        kb.build_crate(content, graph)
        base = content["guide"]["guide"]["recordBase"]
        # The families whose fragment keys the build now publishes as records or parts, and the nodes it keeps.
        cls.retired = {
            re.match(r"#([a-z][a-z0-9]*)", key)[1]
            for key, published in graph.published.items()
            if key.startswith("#") and published.startswith(base)
        }
        cls.kept = {key for key, published in graph.published.items() if key == published}
        cls.fragments = {
            "#" + published.split("#", 1)[1]
            for published in graph.published.values()
            if published.startswith(base) and "#" in published
        }

    def test_the_families_are_the_ones_the_projection_retired(self):
        self.assertTrue({"station", "check", "item", "resource", "lens", "rtype", "knav"} <= self.retired)
        self.assertIn("#snapshot-knav-data-management-tools-catalogue", self.kept)

    def test_the_guard_finds_a_fragment_prefix_test(self):
        found = retired_literals(
            'if (id.startsWith("#station-")) return FG.get(`#lens-${x}`);', self.retired, self.kept, self.fragments
        )
        self.assertEqual(found, [(1, "#station-"), (1, "#lens-${x}")])
        current = 'FG.get("#guide-selection"); FG.get("#snapshot-nkr"); FG.get(record + "#fip-dashboard")'
        self.assertEqual(retired_literals(current, self.retired, self.kept, self.fragments), [])

    def test_no_page_script_tests_a_retired_fragment_prefix(self):
        found = [
            f"{path.relative_to(ROOT).as_posix()}:{number}: {literal}"
            for path in sorted((ROOT / "assets" / "js").rglob("*.js"))
            for number, literal in retired_literals(
                path.read_text(encoding="utf-8"), self.retired, self.kept, self.fragments
            )
        ]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
