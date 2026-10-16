"""Keep PR execution read-only and the trusted comment job separate from untrusted code."""

from __future__ import annotations

import fnmatch
import json
import re
import subprocess
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
        self.assertEqual(tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"], expected)
        self.assertEqual(load("CITATION.cff")["date-released"], str(guide["datePublished"]))

    def test_release_dispatches_use_trusted_source_and_separate_app_delivery(self) -> None:
        for name in ("prepare-release", "tag-release"):
            workflow = load(f".github/workflows/{name}.yml")
            self.assertEqual(set(workflow["on"]), {"workflow_dispatch"})
            self.assertEqual(workflow["permissions"]["contents"], "read")
            job = next(iter(workflow["jobs"].values()))
            self.assertIn("github.event.repository.default_branch", job["if"])
            self.assertIn("github.ref", job["if"])
            steps = job["steps"]
            app = next(step for step in steps if step.get("id") == "app")
            self.assertEqual(app["with"]["permission-contents"], "write")
            self.assertIn("SOURCE_REFRESH_CLIENT_ID", app["with"]["client-id"])
            self.assertTrue(any("release_versions.py" in step.get("run", "") for step in steps))
            delivery = steps[-1]
            self.assertEqual(delivery["with"]["github-token"], "${{ steps.app.outputs.token }}")
            self.assertIn(".propose(" if name == "prepare-release" else ".tag(", delivery["with"]["script"])

    def test_the_editing_skills_are_identical_and_name_every_release_fact(self) -> None:
        shared = (ROOT / ".agents/skills/fair-guide-editor/SKILL.md").read_text(encoding="utf-8")
        claude = (ROOT / ".claude/skills/fair-guide-editor/SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(shared, claude, "the Claude Code copy mirrors the shared editing skill")
        release = shared.split("## 11. Release", 1)[1]
        for fact in (
            "content/guide.toml",
            "datePublished",
            "CITATION.cff",
            "date-released",
            "package.json",
            "package-lock.json",
            "CHANGELOG.md",
            "whole pull request",
            "vX.Y.Z",
            "same artifact",
        ):
            self.assertIn(fact, release, f"the release steps name {fact}")

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
        review = next(step for step in steps if step.get("with", {}).get("name", "").startswith("guide-review-"))
        # The bounded summary the comment reads travels with the complete list it points to.
        self.assertEqual(
            review["with"]["path"].split()[:2], [".cache/pr-review/summary.json", ".cache/pr-review/changes.json"]
        )
        # Contributor patches are exposed by the read-only checks, as an artifact and in the step summary.
        self.assertIn(".cache/pr-review/contributors.json", review["with"]["path"].split())
        self.assertTrue(any("scripts/contributors.py" in step.get("run", "") for step in steps))
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

    def test_source_refresh_runs_trusted_code_and_writes_only_through_the_scoped_app(self) -> None:
        text = (ROOT / ".github/workflows/source-refresh.yml").read_text(encoding="utf-8")
        workflow = load(".github/workflows/source-refresh.yml")
        self.assertEqual(set(workflow["on"]), {"schedule", "workflow_dispatch", "issue_comment"})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertNotIn("pull_request_target", text)
        for job in workflow["jobs"].values():
            self.assertNotIn("permissions", job, "no job widens the read-only token")
            for step in job["steps"]:
                if step.get("uses", "").startswith("actions/checkout@"):
                    self.assertEqual(step["with"]["ref"], "${{ github.event.repository.default_branch }}")
                    self.assertEqual(step["with"]["persist-credentials"], "false")
                # Comment text reaches trusted script only as data, never a shell command.
                self.assertNotIn("github.event.comment", step.get("run", ""))
        steps = workflow["jobs"]["refresh"]["steps"]
        app = next(step for step in steps if step.get("uses", "").startswith("actions/create-github-app-token@"))
        self.assertEqual(
            {key: value for key, value in app["with"].items() if key.startswith("permission-")},
            {"permission-contents": "write", "permission-pull-requests": "write"},
        )
        publish = next(step for step in steps if "publish(" in step.get("with", {}).get("script", ""))
        self.assertEqual(publish["with"]["github-token"], "${{ steps.app.outputs.token }}")
        self.assertNotIn("git push", text)
        self.assertNotIn("merge", text.lower().replace("never merges", ""))

    def test_live_watch_is_scheduled_trusted_and_writes_only_issues(self) -> None:
        text = (ROOT / ".github/workflows/health-watch.yml").read_text(encoding="utf-8")
        workflow = load(".github/workflows/health-watch.yml")
        self.assertEqual(set(workflow["on"]), {"schedule", "workflow_dispatch"})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        job = workflow["jobs"]["watch"]
        self.assertEqual(job["permissions"], {"contents": "read", "issues": "write"})
        checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
        self.assertEqual(checkout["with"]["ref"], "${{ github.event.repository.default_branch }}")
        self.assertEqual(checkout["with"]["persist-credentials"], "false")
        self.assertIn("scripts/watch_sources.py", text)
        self.assertIn("scripts/probe_champion.mjs --jobs 4", text)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("git push", text)
        # Live monitoring stays out of the deterministic pull-request checks.
        self.assertNotIn("watch_sources", (ROOT / ".github/workflows/checks.yml").read_text(encoding="utf-8"))

    def test_deployment_checks_once_and_ships_the_same_site_the_release_attaches(self) -> None:
        deploy = load(".github/workflows/deploy.yml")
        self.assertEqual(set(deploy["on"]), {"push", "workflow_dispatch"})
        self.assertEqual(deploy["permissions"], {"contents": "read"})
        self.assertEqual(deploy["jobs"]["sources"]["permissions"], {"contents": "read", "actions": "read"})
        self.assertEqual(deploy["on"]["push"], {"branches": ["main"], "tags": ["v*"]})
        verify = [step.get("run", "") + step.get("uses", "") for step in deploy["jobs"]["production"]["steps"]]
        order = [
            next(index for index, step in enumerate(verify) if marker in step)
            for marker in ("check_all.py", "package_site.py", "upload-artifact")
        ]
        self.assertEqual(order, sorted(order), "check, then package and hand over the same site")
        self.assertFalse(any("build_site.py" in step for step in verify), "nothing is rebuilt after the checks")
        for step in deploy["jobs"]["production"]["steps"]:
            if "check_all.py" in step.get("run", ""):
                self.assertEqual(step["if"], "needs.sources.outputs.build == 'true'", "only a tag rebuilds production")
        staging = deploy["jobs"]["staging"]
        self.assertIn("check_all.py", " ".join(step.get("run", "") for step in staging["steps"]))
        self.assertEqual(staging["env"]["FAIR_GUIDE_CHECK_REVISION"], "${{ needs.sources.outputs.staging }}")
        assemble = deploy["jobs"]["assemble"]
        self.assertIn("assemble_pages.py", " ".join(step.get("run", "") for step in assemble["steps"]))
        self.assertNotIn("check_all.py", " ".join(step.get("run", "") for step in assemble["steps"]))
        marker = next(step for step in staging["steps"] if step.get("with", {}).get("name") == "staging-site")
        self.assertEqual(marker["with"]["include-hidden-files"], "true", "the checked site marker travels with staging")
        self.assertEqual(deploy["jobs"]["deploy"]["permissions"], {"pages": "write", "id-token": "write"})
        release = load(".github/workflows/release.yml")
        self.assertEqual(
            release["on"], {"workflow_run": {"workflows": ["Deploy the verified site"], "types": ["completed"]}}
        )
        self.assertEqual(release["jobs"]["release"]["permissions"], {"contents": "write", "actions": "read"})
        text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertNotIn("build_site", text)
        self.assertNotIn("check_all", text)
        self.assertIn("guide-site-${{ steps.source.outputs.sha }}", text)
        self.assertIn("workflow_run.event == 'push'", release["jobs"]["release"]["if"])
        self.assertIn("workflow_run.head_repository.full_name == github.repository", release["jobs"]["release"]["if"])

    def test_code_owners_and_the_template_name_real_people_and_the_required_parts(self) -> None:
        owners = [
            line.split()
            for line in (ROOT / ".github/CODEOWNERS").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        self.assertTrue(owners)
        for rule in owners:
            for owner in rule[1:]:
                self.assertRegex(owner, r"^@[A-Za-z0-9-]+$", "a personal account, never an invented team")
        template = (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
        for part in ("## Sources and paradata", "## Checks", "## AI assistance", "## Related issues"):
            self.assertIn(part, template)
        guide = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        for fact in ("only collaborator", "eligible content reviewer", "ORCID iD listed", "package-lock.json"):
            self.assertIn(fact, guide)

    def test_every_generated_file_attribute_matches_a_committed_file(self) -> None:
        # Build output lives in the ignored _site/; an attribute for a path nothing commits can never apply.
        patterns = [
            line.split()[0]
            for line in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
            if "linguist-generated" in line and not line.lstrip().startswith("#")
        ]
        try:
            tracked = subprocess.run(
                ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
            ).stdout.decode("utf-8")
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git is not available")
        files = [name for name in tracked.split("\0") if name]
        for pattern in patterns:
            self.assertTrue(any(fnmatch.fnmatch(name, pattern) for name in files), f"{pattern} matches no file")

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
