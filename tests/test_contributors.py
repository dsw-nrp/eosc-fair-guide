"""Contributor patches: reviewed identities only, AI as instruments, bots as automatic software, no guessed credit."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402
import check_content  # noqa: E402
import contributors  # noqa: E402


class ContributorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "guide"
        shutil.copytree(ROOT / "tests/fixtures/minimal", self.root)
        guide = self.root / "content/guide.toml"
        guide.write_text(
            guide.read_text(encoding="utf-8").replace(
                'name = "Test Person"', 'name = "Test Person"\ngithub = "tester-gh"\ncommitNames = ["Test Person"]'
            )
            + '\n[[person]]\nid = "opted"\nname = "Opted Out"\norcidOptOut = true\ngithub = "opted-gh"\n',
            encoding="utf-8",
        )
        (self.root / "CITATION.cff").write_text(
            "authors:\n  - family-names: Person\n    given-names: Test\n", encoding="utf-8"
        )
        self.git("init", "-q", "-b", "main")
        self.commit("Test Person", "someone@example.org", "base")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def status(self) -> str:
        result = subprocess.run(["git", "status", "--porcelain"], cwd=self.root, capture_output=True, check=True)
        return result.stdout.decode("utf-8")

    def commit(self, name: str, email: str, message: str) -> None:
        self.git("add", "-A")
        self.git("-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "-q", "--allow-empty", "-m", message)

    def touch(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(path.read_text(encoding="utf-8") + text if path.exists() else text, encoding="utf-8")

    def action(self, action_id: str, agent: str) -> str:
        return (
            f'\n[[action]]\nid = "{action_id}"\ntype = "update"\nname = "Edit"\nagent = "{agent}"\n'
            'instruments = ["model"]\nresults = ["one.03"]\nendTime = 2099-01-01T00:00:00+00:00\n'
        )

    def test_identities_roles_and_suggestions(self) -> None:
        self.git("checkout", "-q", "-b", "topic")
        self.touch("content/stations/01-one.toml", "\n# reviewed edit\n")
        self.touch("content/provenance.toml", self.action("by-tester", "tester"))
        self.commit(
            "Test Person",
            "1+tester-gh@users.noreply.github.com",
            "content: edit\n\nCo-authored-by: Claude <noreply@anthropic.com>",
        )
        self.touch("content/ledger.toml", "\n# unknown helper\n")
        self.commit("Jane Doe", "jane@example.org", "content: a stranger's edit")
        self.touch("content/snapshots/re3data.toml", "[snapshot]\n")
        self.commit("fair-guide-refresh[bot]", "9+fair-guide-refresh[bot]@users.noreply.github.com", "Refresh")
        self.touch("content/provenance.toml", self.action("by-opted", "opted"))
        self.commit("Test Person", "someone@example.org", "content: paradata for an opted-out person")
        data = contributors.report(self.root, "main")
        self.assertEqual(data["people"], {"tester": 2})
        self.assertEqual(data["instruments"], {"claude-opus-5-5": 1}, "an AI co-author is an instrument, not a person")
        persons = data["patches"]["persons"]
        self.assertEqual(
            [item["name"] for item in persons], ["Jane Doe"], "an unknown identity is reported, not guessed"
        )
        self.assertIn('name = "Jane Doe"', persons[0]["stub"])
        self.assertNotIn("orcid", persons[0]["stub"])
        self.assertEqual(
            data["patches"]["citation"], [{"name": "Opted Out"}], "opted out: no ORCID iD; listed people skipped"
        )
        self.assertEqual(data["patches"]["actions_without_their_agent"], [{"action": "by-opted", "agent": "opted"}])
        self.assertEqual(data["patches"]["people_without_an_action"], [])
        refresh = data["patches"]["automatic_refreshes"]
        self.assertEqual(len(refresh), 1)
        self.assertEqual(refresh[0]["software"], "fair-guide-refresh[bot]")
        self.assertIn("reviews and merges", refresh[0]["action"]["agent"], "no bot is credited as the agent")
        self.assertNotIn("fair-guide-refresh[bot]", json.dumps(data["patches"]["citation"]))
        summary = contributors.markdown(data)
        self.assertIn("suggestions to confirm, not changes", summary)
        self.assertIn("Jane Doe", summary)

    def test_the_run_writes_the_report_and_changes_nothing(self) -> None:
        before = self.status()
        output = Path(self.temp.name) / "contributors.json"
        with mock.patch.object(contributors, "ROOT", self.root), mock.patch("builtins.print"):
            self.assertEqual(contributors.main(["--base", "main", "--output", str(output)]), 0)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["commits"], 0)
        self.assertTrue(output.with_suffix(".md").is_file())
        self.assertEqual(before, self.status())

    def test_identity_fields_are_validated_and_opt_out_hides_the_orcid(self) -> None:
        guide = self.root / "content/guide.toml"
        guide.write_text(
            guide.read_text(encoding="utf-8").replace(
                "orcidOptOut = true", 'orcidOptOut = true\norcid = "https://orcid.org/0000-0002-1825-0097"'
            ),
            encoding="utf-8",
        )
        content = build_crate.load_content(self.root / "content")
        errors = check_content.check(content, self.root).errors
        self.assertTrue(any("opted out of listing an ORCID iD carries none" in error for error in errors), errors)
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
        self.assertIn("#person-opted", graph.entities)
        self.assertNotIn("https://orcid.org/0000-0002-1825-0097", graph.entities)
        guide.write_text(
            guide.read_text(encoding="utf-8").replace('github = "opted-gh"', 'github = "not a login"'), encoding="utf-8"
        )
        errors = check_content.check(build_crate.load_content(self.root / "content"), self.root).errors
        self.assertTrue(any("github must be a GitHub account name" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
