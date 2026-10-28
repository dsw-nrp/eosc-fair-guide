"""Public-source hygiene reports unsafe locations without exposing their contents."""

import subprocess
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

    def test_the_runtime_scratch_layout_is_allowed_but_machine_specific_paths_are_not(self):
        relative = "A hand-off lives under ." + "agents/local_scratch/<workflow>/<run>/.\n"
        self.assertEqual(public.violations(relative), [], "the repository-relative layout is not a local path")
        for machine in (
            "D:" + "\\work\\checkout\\.agents" + "\\local_scratch\\run\n",
            "/" + "srv/guide/.agents" + "/local_scratch/run\n",
        ):
            with self.subTest(machine=machine):
                self.assertEqual(
                    {rule for _, rule in public.violations(machine)},
                    {"local planning scratch"},
                    "an absolute path to the same layout is still machine-specific",
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

    def test_untracked_runtime_hand_offs_are_skipped_and_everything_else_is_checked(self):
        # Run hand-offs stay visible to Git by design (.agents/local_scratch/README.md) and point to machine-local
        # run locations; they are public source only once someone stages them.
        private = "C:" + "\\Users\\private-person\\run\n"
        hand_off, staged = ".agents/local_scratch/review/hand-off.md", ".agents/local_scratch/README.md"
        new = "docs/new.md"
        for repository in (True, False):
            with self.subTest(repository=repository), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                declaration = root / public.CONFIG
                declaration.parent.mkdir(parents=True)
                declaration.write_text('runtime = [".agents/local_scratch/**"]\n', encoding="utf-8")
                for rel in (hand_off, staged, new):
                    path = root / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(private, encoding="utf-8")
                if repository:
                    subprocess.run(["git", "init", "-q", str(root)], check=True)
                    subprocess.run(["git", "-C", str(root), "add", staged], check=True)
                checked = [staged, new] if repository else [hand_off, staged, new]
                self.assertEqual(
                    public.inspect(root),
                    sorted(f"{rel}:1: personal workstation path" for rel in checked),
                    "only an untracked hand-off in a Git work tree is skipped",
                )


if __name__ == "__main__":
    unittest.main()
