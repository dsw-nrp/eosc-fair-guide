"""Public-source hygiene reports unsafe locations without exposing their contents."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_public_content as public  # noqa: E402


class PublicContentTests(unittest.TestCase):
    def test_public_attribution_and_portable_paths_are_permitted(self):
        self.assertEqual(
            public.violations(
                "An author credited at https://orcid.org/example\n/workspaces/guide\n"
                "https://example.org/users/researchers/\n"
            ),
            [],
        )

    def test_private_path_and_planning_extracts_are_detected(self):
        value = "D:" + "\\David\\private\\plan\n" + "notes/" + "extracted/report.txt"
        self.assertEqual(
            {rule for _, rule in public.violations(value)}, {"personal workstation path", "private planning extracts"}
        )

    def test_delivered_tooling_is_scanned_and_private_references_are_refused(self):
        paths = (
            ".agents/skills/example/SKILL.md",
            ".agents/scripts/example.py",
            ".agents/canonical_configs/templates/example.md",
            ".claude/skills/example/SKILL.md",
            ".claude/rules/example.md",
            ".claude/agents/example.md",
            ".cursor/rules/example.mdc",
            ".kilo/rules/example.md",
            ".kilo/kilo.jsonc",
            ".codex/agents/example.toml",
            ".codex/rules/example.rules",
            ".gemini/agents/example.md",
            ".gemini/context/example.md",
            ".gemini/commands/example.toml",
            ".github/instructions/example.instructions.md",
            "CODEX.md",
        )
        portable = "AIS CR attribution <https://ror.org/01a7rqj69>; aiscr-example tooling.\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for rel in paths:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(portable, encoding="utf-8")
            self.assertEqual(public.inspect(root), [])
            for rel in paths:
                with self.subTest(path=rel):
                    path = root / rel
                    path.write_text("aiscr-" + "management\n", encoding="utf-8")
                    self.assertEqual(public.inspect(root), [f"{rel}:1: private planning repository"])
                    path.write_text(portable, encoding="utf-8")

    def test_ignored_generated_tree_is_not_scanned_and_report_is_redacted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs").mkdir()
            (root / "_site").mkdir()
            private = "C:" + "\\Users\\private-person\\secret.txt"
            (root / "docs" / "example.md").write_text(private, encoding="utf-8")
            (root / "_site" / "ignored.md").write_text(private, encoding="utf-8")
            findings = public.inspect(root)
            self.assertEqual(findings, ["docs/example.md:1: personal workstation path"])
            self.assertNotIn("private-person", "\n".join(findings))


if __name__ == "__main__":
    unittest.main()
