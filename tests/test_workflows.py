"""Keep PR execution read-only and the trusted comment job separate from untrusted code."""

from __future__ import annotations

import json
import re
import tomllib
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load(path: str) -> dict:
    return yaml.load((ROOT / path).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


class WorkflowContracts(unittest.TestCase):
    def test_application_package_and_citation_versions_agree(self) -> None:
        guide = tomllib.loads((ROOT / "content/guide.toml").read_text(encoding="utf-8"))["guide"]
        expected = guide["version"]
        self.assertEqual(json.loads((ROOT / "package.json").read_text())["version"], expected)
        lock = json.loads((ROOT / "package-lock.json").read_text())
        self.assertEqual(lock["version"], expected)
        self.assertEqual(lock["packages"][""]["version"], expected)
        self.assertEqual(load("CITATION.cff")["version"], expected)

    def test_untrusted_pr_checks_have_no_write_permission_or_secrets(self) -> None:
        workflow = load(".github/workflows/checks.yml")
        self.assertEqual(set(workflow["on"]), {"pull_request"})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        job = workflow["jobs"]["checks"]
        self.assertNotIn("permissions", job)
        steps = job["steps"]
        self.assertTrue(
            any("scripts/check_all.py" in step.get("run", "") and '--base "$BASE_SHA"' in step["run"] for step in steps)
        )
        self.assertTrue(any(step.get("with", {}).get("name", "").startswith("guide-review-") for step in steps))
        self.assertNotIn("secrets.", (ROOT / ".github/workflows/checks.yml").read_text())

    def test_trusted_comment_never_checks_out_or_executes_pr_code(self) -> None:
        workflow = load(".github/workflows/pr-summary.yml")
        self.assertEqual(set(workflow["on"]), {"workflow_run"})
        self.assertEqual(workflow["permissions"], {"contents": "read", "actions": "read", "pull-requests": "write"})
        steps = workflow["jobs"]["comment"]["steps"]
        checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
        self.assertEqual(checkout["with"]["ref"], "${{ github.event.repository.default_branch }}")
        self.assertEqual(checkout["with"]["persist-credentials"], "false")
        self.assertFalse(any("run" in step for step in steps))
        scripts = [
            step["with"]["script"] for step in steps if step.get("uses", "").startswith("actions/github-script@")
        ]
        self.assertEqual(len(scripts), 1)
        self.assertIn("require('./.github/scripts/comment-summary.cjs')", scripts[0])
        self.assertNotIn("pr-review-incoming", scripts[0])

    def test_action_pins_and_dependency_updates_are_complete(self) -> None:
        for path in ROOT.glob(".github/workflows/*.yml"):
            workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
            for job in workflow["jobs"].values():
                for step in job.get("steps", []):
                    if "uses" in step:
                        self.assertRegex(step["uses"], re.compile(r"^[\w/-]+@[0-9a-f]{40}$"))
        updates = load(".github/dependabot.yml")["updates"]
        self.assertEqual({entry["package-ecosystem"] for entry in updates}, {"github-actions", "npm", "pip"})


if __name__ == "__main__":
    unittest.main()
