"""The documentation checks: one declared type, runbook shape, accessible diagrams, existing facts, README agreement
and a section map that accounts for every former heading."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_docs import ROOT, anchor, problems, section_map  # noqa: E402

STEP = """{number}. **Approve the deployment.**
   - **Where:** the Deploy the verified site run.
   - **Do:** choose **Review deployments**, then **Approve**.
   - **Done when:** the run's production job is green.
   - **If it fails:** re-run the failed jobs.
"""
RUNBOOK = (
    "<!-- type: how-to -->\n# Release the Guide\n\nA maintainer releases in about an hour. "
    "Readers then get the reviewed Guide.\n\n" + STEP.format(number=1) + "\n" + STEP.format(number=2)
)
README = "<!-- type: landing -->\n# {title}\n\nIntro [tools](docs/agent-tooling.md).\n\n## Use\n\nText.\n"


class DocsTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.write("package.json", json.dumps({"scripts": {"check:docs": "x"}}))
        self.write("scripts/check_all.py", "")
        self.write(".github/workflows/deploy.yml", "")
        self.write("docs/agent-tooling.md", "<!-- type: reference -->\n# Tools\n")
        self.write("README.md", README.format(title="Průvodce"))
        self.write("README_en.md", README.format(title="Guide"))
        self.write("CONTRIBUTING.md", "<!-- type: landing -->\n# Contributing\n\nRun `python scripts/check_all.py`.\n")
        self.write("docs/runbooks/release.md", RUNBOOK)

    def write(self, name: str, text: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_the_repository_documentation_passes(self) -> None:
        self.assertEqual(problems(ROOT), [])

    def test_a_valid_set_passes(self) -> None:
        self.assertEqual(problems(self.root), [])

    def test_a_missing_or_unknown_type_names_the_accepted_types(self) -> None:
        self.write("docs/a.md", "# No declaration\n")
        self.write("docs/b.md", "<!-- type: guide -->\n# Unknown\n")
        found = problems(self.root)
        for name in ("docs/a.md", "docs/b.md"):
            self.assertIn(
                f"{name}: declare one type on the first line, <!-- type: TYPE -->, TYPE one of landing, "
                "how-to, reference, explanation, tutorial",
                found,
            )

    def test_a_renamed_script_is_caught_with_or_without_its_directory(self) -> None:
        self.write(
            "docs/scripts.md", "<!-- type: reference -->\n# Scripts\n\n`check_all.py` and `scripts/check_all.py`.\n"
        )
        self.assertEqual(problems(self.root), [])
        (self.root / "scripts/check_all.py").rename(self.root / "scripts/renamed.py")
        found = problems(self.root)
        self.assertIn("docs/scripts.md: names the script `check_all.py`, which does not exist", found)
        self.assertIn("docs/scripts.md: names `scripts/check_all.py`, which does not exist", found)

    def test_local_script_markup_is_checked(self) -> None:
        self.write(
            "docs/embed.md",
            '<!-- type: how-to -->\n# Embed\n\n```html\n<script src="assets/js/missing.js"></script>\n```\n',
        )
        (self.root / "assets/js").mkdir(parents=True)
        self.assertIn("docs/embed.md: names `assets/js/missing.js`, which does not exist", problems(self.root))

    def test_a_script_directory_typo_is_not_ignored(self) -> None:
        self.write("docs/typo.md", "<!-- type: reference -->\n# Typo\n\n`python script/check_all.py`.\n")
        self.assertIn("docs/typo.md: names `script/check_all.py`, which does not exist", problems(self.root))

    def test_a_runbook_step_without_its_failure_route_is_named(self) -> None:
        self.write(
            "docs/runbooks/release.md", RUNBOOK.replace("   - **If it fails:** re-run the failed jobs.\n", "", 1)
        )
        self.assertEqual(
            problems(self.root), ["docs/runbooks/release.md step 1 (Approve the deployment.): add **If it fails:**"]
        )

    def test_a_runbook_opens_briefly_and_stays_within_its_budget(self) -> None:
        self.write("docs/runbooks/release.md", RUNBOOK.replace("Guide.\n", "Guide. It is long. Really.\n", 1))
        self.assertIn(
            "docs/runbooks/release.md: open with one or two sentences on who acts, how long and why (4 now)",
            problems(self.root),
        )
        long = RUNBOOK.replace("re-run the failed jobs.", "re-run " + "the failed jobs " * 50, 1)
        self.write("docs/runbooks/release.md", long)
        self.assertTrue(any("words; keep a step within" in problem for problem in problems(self.root)))

    def test_a_diagram_without_accessible_names_is_named(self) -> None:
        self.write("docs/flow.md", "<!-- type: explanation -->\n# Flow\n\n```mermaid\nflowchart LR\n  a --> b\n```\n")
        self.assertEqual(problems(self.root), ["docs/flow.md: Mermaid block 1 needs accTitle and accDescr"])

    def test_missing_scripts_workflows_npm_scripts_and_links_are_named(self) -> None:
        self.write(
            "docs/ref.md",
            "<!-- type: reference -->\n# Ref\n\nRun `python scripts/check_al.py`, `npm run check:doc`, see "
            "`deploy.yml`, `publish.yml`, [the guide](missing.md) and the site's `/api/health.json`.\n",
        )
        self.assertEqual(
            problems(self.root),
            [
                "docs/ref.md: the link target missing.md does not exist",
                "docs/ref.md: names `scripts/check_al.py`, which does not exist",
                "docs/ref.md: names the workflow `publish.yml`, which does not exist",
                "docs/ref.md: names `npm run check:doc`, which package.json does not define",
            ],
        )

    def test_the_readmes_agree(self) -> None:
        self.write(
            "README_en.md",
            README.format(title="Guide") + "\n## Extra\n\nSee [the runbook](docs/runbooks/release.md).\n",
        )
        found = problems(self.root)
        self.assertIn("README.md and README_en.md: keep the same headings in the same order and levels", found)
        self.assertIn(
            "README.md and README_en.md: link the same documents in the same order; only one links "
            "docs/runbooks/release.md",
            found,
        )

    def test_local_and_moved_heading_links_are_verified(self) -> None:
        self.write(
            "docs/ref.md",
            "<!-- type: reference -->\n# Reference\n\n## Repeated\n\n## Repeated\n\n"
            "[first](#repeated) [second](#repeated-1) [missing](#absent) "
            "[moved](agent-tooling.md#gone)\n",
        )
        self.assertEqual(
            problems(self.root),
            [
                "docs/ref.md: the link #absent names a heading docs/ref.md does not have",
                "docs/ref.md: the link agent-tooling.md#gone names a heading agent-tooling.md does not have",
            ],
        )

    def test_the_section_map_accounts_for_every_former_heading(self) -> None:
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.org", "-c", "commit.gpgsign=false"]
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.write("docs/old.md", "# Old\n\n## Release preparation\n\n## Kept\n\n## Kept\n")
        subprocess.run([*git, "add", "docs/old.md"], cwd=self.root, check=True)
        subprocess.run([*git, "commit", "-qm", "base"], cwd=self.root, check=True)
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True, check=True
        ).stdout.strip()
        rows = [
            "| docs/old.md | Old | maintainers | reference | docs/runbooks/release.md |",
            "| docs/old.md | Release preparation | maintainers | how-to | docs/runbooks/release.md#release-the-guide |",
        ]
        table = "| Document | Heading | Audience | Type | Home |\n| --- | --- | --- | --- | --- |\n"
        path = self.root / "map.md"
        path.write_text(f"# Map\n\nBase: `{base}`\n\n" + table + "\n".join(rows) + "\n", encoding="utf-8")
        self.assertEqual(
            section_map(self.root, path),
            [f'{path}: add a row for docs/old.md "Kept" with its audience, type and home or removal reason'] * 2,
        )
        rows += [
            "| docs/old.md | Kept | maintainers | reference | docs/runbooks/release.md#no-such-step |",
            "| README.md | Use | readers | landing | removed: |",
        ]
        path.write_text(f"Base: `{base}`\n\n" + table + "\n".join(rows) + "\n", encoding="utf-8")
        found = section_map(self.root, path)
        self.assertIn(
            f'{path}: docs/old.md "Kept" moves to docs/runbooks/release.md#no-such-step, but '
            "docs/runbooks/release.md has no such heading",
            found,
        )
        self.assertIn(f'{path}: README.md "Use" needs a removal reason', found)
        self.assertIn(
            f'{path}: add a row for docs/old.md "Kept" with its audience, type and home or removal reason', found
        )

    def test_an_empty_runbook_field_does_not_count_as_a_step(self) -> None:
        self.write(
            "docs/runbooks/release.md", RUNBOOK.replace("choose **Review deployments**, then **Approve**.", "", 1)
        )
        self.assertIn(
            "docs/runbooks/release.md step 1 (Approve the deployment.): give an action or evidence after **Do:**",
            problems(self.root),
        )

    def test_anchors_follow_github(self) -> None:
        self.assertEqual(anchor("Release `v1.0` — tag & publish"), "release-v10--tag--publish")


if __name__ == "__main__":
    unittest.main()
