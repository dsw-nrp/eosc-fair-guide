"""Keep PR execution read-only and the trusted comment job separate from untrusted code."""

from __future__ import annotations

import fnmatch
import json
import re
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_ci  # noqa: E402


def load(path: str) -> dict:
    return yaml.load((ROOT / path).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def token_requests() -> dict[tuple[str, str], tuple[dict | None, dict]]:
    """Each workflow job's GITHUB_TOKEN permissions (its own block, else the workflow's) and App-token requests."""
    found = {}
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        workflow = load(path.relative_to(ROOT).as_posix())
        for name, job in workflow["jobs"].items():
            app = {}
            for step in job.get("steps", []):
                if step.get("uses", "").startswith("actions/create-github-app-token@"):
                    requested = step.get("with", {}).items()
                    app |= {
                        key.removeprefix("permission-"): value
                        for key, value in requested
                        if key.startswith("permission-")
                    }
            found[(path.name, name)] = (job.get("permissions", workflow.get("permissions")), app)
    return found


def reviewed_tokens() -> dict[tuple[str, str], tuple[dict, dict]]:
    config = tomllib.loads((ROOT / ".github/repository.toml").read_text(encoding="utf-8"))
    return {
        (entry["workflow"], job): (entry["github"], entry.get("app", {}))
        for entry in config["token"]
        for job in entry["jobs"]
    }


def token_differences(reviewed: dict, actual: dict) -> list[str]:
    """Every job whose token requests differ from its reviewed entry, naming the job and the permission."""
    problems = []
    for workflow, job in sorted(set(actual) | set(reviewed)):
        where = f"{workflow} job {job}"
        if (workflow, job) not in reviewed:
            problems.append(f"{where}: no reviewed token entry in .github/repository.toml")
            continue
        if (workflow, job) not in actual:
            problems.append(f"{where}: reviewed in .github/repository.toml, but no such job")
            continue
        if actual[(workflow, job)][0] is None:
            problems.append(f"{where}: no explicit permissions, so GITHUB_TOKEN gets the repository default")
            continue
        for index, token in enumerate(("GITHUB_TOKEN", "App token")):
            want, have = reviewed[(workflow, job)][index], actual[(workflow, job)][index]
            for permission in sorted(set(want) | set(have)):
                if want.get(permission, "none") != have.get(permission, "none"):
                    problems.append(
                        f"{where}: {token} requests {permission}: {have.get(permission, 'none')}, "
                        f"reviewed {want.get(permission, 'none')}"
                    )
    return problems


class WorkflowContracts(unittest.TestCase):
    def test_publication_follows_only_successful_deployments_where_no_cancellation_reaches(self) -> None:
        deploy = load(".github/workflows/deploy.yml")
        for job in deploy["jobs"].values():
            for step in job.get("steps", []):
                self.assertFalse(
                    step.get("uses", "").startswith(("actions/deploy-pages@", "actions/upload-pages-artifact@")),
                    "a cancelled deployment run never interrupts a Pages deployment",
                )
        workflow = load(".github/workflows/publish.yml")
        self.assertEqual(workflow["on"], {"workflow_run": {"workflows": [deploy["name"]], "types": ["completed"]}})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        resolve = workflow["jobs"]["resolve"]
        condition = " ".join(resolve["if"].split())
        # Deciding and deploying run together, one publication at a time. Only a run that will resolve enters the
        # shared group, so a run after a cancelled or failed deployment never replaces a waiting publication.
        idle = "format('pages-publish-idle-{0}', github.run_id)"
        self.assertEqual(
            {key: " ".join(value.split()) for key, value in workflow["concurrency"].items()},
            {"group": f"${{{{ {condition} && 'pages-publish' || {idle} }}}}", "cancel-in-progress": "false"},
        )
        for part in (
            "github.event.workflow_run.conclusion == 'success'",
            "github.event.workflow_run.head_repository.full_name == github.repository",
            "github.event.workflow_run.event == 'push' || github.event.workflow_run.event == 'workflow_dispatch'",
        ):
            self.assertIn(part, condition)
        self.assertNotIn("environment", resolve, "deciding leaves no github-pages deployment record")
        self.assertEqual(resolve["permissions"], {"actions": "read", "contents": "read"})
        self.assertEqual(resolve["steps"][0]["with"]["ref"], "${{ github.event.repository.default_branch }}")
        script = next(step for step in resolve["steps"] if step.get("id") == "resolve")["with"]["script"]
        self.assertIn("completedDeployment({ github, context })", script)
        self.assertIn("recorded: context.sha", script, "the Pages record names the staging published")
        publish = workflow["jobs"]["publish"]
        self.assertEqual(publish["needs"], "resolve")
        self.assertEqual(
            publish["if"], "needs.resolve.outputs.publish == 'true'", "only a real deployment enters github-pages"
        )
        self.assertEqual(publish["environment"]["name"], "github-pages")
        self.assertEqual(
            publish["permissions"], {"actions": "read", "contents": "read", "id-token": "write", "pages": "write"}
        )
        steps = publish["steps"]
        self.assertEqual(steps[0]["with"]["ref"], "${{ github.event.repository.default_branch }}", "trusted code")
        pages = next(step for step in steps if step.get("id") == "deployment")
        record = next(step for step in steps if step.get("with", {}).get("name") == "pages-identity")
        self.assertGreater(steps.index(record), steps.index(pages), "the record exists only after a Pages deployment")
        self.assertEqual(record["with"]["path"], ".cache/published/identity.json")
        writer = (ROOT / ".github/scripts/release-artifact.cjs").read_text(encoding="utf-8")
        self.assertIn('const PUBLISHED = ".cache/published/identity.json";', writer, "the reader names the same file")
        self.assertIn("assemble_pages.py", " ".join(step.get("run", "") for step in steps))
        self.assertNotIn("check_all.py", " ".join(step.get("run", "") for step in steps))

    def test_copilot_setup_uses_the_locked_workspace_cli(self) -> None:
        job = load(".github/workflows/copilot-setup-steps.yml")["jobs"]["copilot-setup-steps"]
        self.assertEqual(job["permissions"], {"contents": "read"})
        steps = job["steps"]
        self.assertEqual(steps[0]["with"]["persist-credentials"], "false")
        commands = [step.get("run", "") for step in steps]
        self.assertIn("npm ci", commands)
        self.assertIn("npm run openspec:cli -- --version", commands)
        self.assertFalse(any("npm install -g" in command for command in commands))

    def test_image_aliases_follow_every_required_audit_with_bounded_artifact_access(self) -> None:
        release = load(".github/workflows/release.yml")
        image = load(".github/workflows/publish-image.yml")
        for job in (release["jobs"]["publish"], image["jobs"]["image"]):
            self.assertEqual(job["permissions"].get("actions"), "read")
        self.assertEqual(release["concurrency"]["cancel-in-progress"], "false")
        steps = image["jobs"]["image"]["steps"]
        names = [step.get("name", "") for step in steps]
        promotion = names.index("Promote the audited digest")
        required = [
            "Run the candidate image and check its identity",
            "Sign the image",
            "Attest the build provenance",
            "Generate an SBOM",
            "Attest the SBOM",
            "Scan the image",
            "Recheck production eligibility before promotion",
        ]
        for name in required:
            index = names.index(name)
            self.assertLess(index, promotion)
            self.assertNotEqual(steps[index].get("continue-on-error"), "true", name)
        candidate = next(step for step in steps if step.get("id") == "tags")["run"]
        self.assertIn("candidate-", candidate)
        self.assertNotIn(":latest", candidate)
        self.assertNotIn(":stable", candidate)
        promotion_run = next(step for step in steps if step.get("name") == "Promote the audited digest")["run"]
        release_move = promotion_run.index('--tag "$IMAGE:$RELEASE_TAG"')
        release_assert = promotion_run.index('test "$(digest_of "$IMAGE:$RELEASE_TAG")"')
        latest_move = promotion_run.index('--tag "$IMAGE:latest"')
        self.assertLess(release_move, release_assert, "the release tag is promoted before it is verified")
        self.assertLess(release_assert, latest_move, "no moving alias is touched before the release digest is verified")
        self.assertIn("--raw", promotion_run)
        self.assertNotIn("--prefer-index=false", promotion_run)
        self.assertNotIn(".Manifest.Digest", promotion_run)
        self.assertIn(
            "steps.build.outputs.digest", next(step for step in steps if step.get("id") == "digest")["env"]["DIGEST"]
        )
        self.assertEqual(steps[0]["with"]["ref"], "${{ github.event.repository.default_branch }}")

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
        zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
        self.assertEqual(zenodo["version"], expected)
        self.assertEqual(zenodo["publication_date"], str(guide["datePublished"]))

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
            before_token = "\n".join(step.get("run", "") for step in steps[: steps.index(app)])
            self.assertIn("pip install -r requirements-dev.txt", before_token)
            self.assertIn("scripts/check_citation_metadata.py", before_token)
            if name == "prepare-release":
                self.assertIn("history --output .cache/release/history.json", before_token)
                self.assertIn("--associations .cache/release/associations.json", before_token)
            else:
                self.assertIn('check --version "$RELEASE_VERSION"', before_token)
                gate = next(step for step in steps if ".deployed(" in step.get("with", {}).get("script", ""))
                self.assertLess(steps.index(gate), steps.index(app), "the deployment check precedes the App token")
                self.assertNotIn("github-token", gate["with"], "it reads runs with the job's read-only token")
                self.assertEqual(job["permissions"], {"contents": "read", "actions": "read", "deployments": "read"})

    def test_release_status_is_a_tag_input_and_never_a_repository_variable(self) -> None:
        tag = load(".github/workflows/tag-release.yml")
        choice = tag["on"]["workflow_dispatch"]["inputs"]["release_status"]
        self.assertEqual(choice["type"], "choice")
        self.assertEqual(choice["options"], ["testing", "production"])
        self.assertEqual(choice["default"], "testing")
        self.assertEqual(choice["required"], "true")
        deploy = load(".github/workflows/deploy.yml")
        env = deploy["jobs"]["production"]["env"]
        self.assertNotIn("RELEASE_STATUS", env)
        self.assertEqual(env["FAIR_GUIDE_RELEASE_TAG"], "${{ needs.sources.outputs.tag }}")
        self.assertNotIn("vars.RELEASE_STATUS", (ROOT / ".github/workflows/deploy.yml").read_text())

    def test_identical_thin_skills_route_to_the_release_owners(self) -> None:
        shared = (ROOT / ".agents/skills/fair-guide-editor/SKILL.md").read_text(encoding="utf-8")
        claude = (ROOT / ".claude/skills/fair-guide-editor/SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(shared, claude, "the Claude Code copy mirrors the shared editing skill")
        self.assertIn("CONTRIBUTING.md", shared)
        self.assertIn("docs/deployment.md", shared)
        self.assertIn("before implementation", shared)
        release = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        release += (ROOT / "docs/deployment.md").read_text(encoding="utf-8")
        for fact in (
            "content/guide.toml",
            "datePublished",
            "CITATION.cff",
            "date-released",
            "package.json",
            "package-lock.json",
            "CHANGELOG.md",
            "vX.Y.Z",
            "same verified bytes",
        ):
            self.assertIn(fact, release, f"the release steps name {fact}")

    def test_untrusted_pr_checks_have_no_write_permission_or_secrets(self) -> None:
        workflow = load(".github/workflows/checks.yml")
        self.assertEqual(set(workflow["on"]), {"pull_request", "merge_group"})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        # The required context is named after this job; the work runs in the reusable workflow.
        gate = workflow["jobs"]["checks"]
        self.assertEqual(gate["needs"], "partitioned", "the quick result never gates or replaces `checks`")
        self.assertEqual(gate["if"], "always()")
        self.assertEqual(gate["steps"][0]["env"]["RESULT"], "${{ needs.partitioned.result }}")
        self.assertIn('[ "$RESULT" = success ]', gate["steps"][0]["run"])
        self.assertEqual(workflow["jobs"]["partitioned"]["uses"], "./.github/workflows/partitioned-checks.yml")
        partitioned = load(".github/workflows/partitioned-checks.yml")
        self.assertEqual(set(partitioned["on"]), {"workflow_call"})
        self.assertEqual(partitioned["permissions"], {"contents": "read"})
        steps = partitioned["jobs"]["collect"]["steps"]
        self.assertTrue(
            any(
                "scripts/check_ci.py collect" in step.get("run", "") and '--base "$BASE_SHA"' in step["run"]
                for step in steps
            )
        )
        self.assertEqual(partitioned["jobs"]["collect"]["needs"], ["build", "lanes"])
        # The collector still runs after a failed build or lane, but not in a cancelled run. The gate keeps
        # `always()`: a skipped required check counts as passing, so a cancelled merge group must fail it instead.
        self.assertEqual(partitioned["jobs"]["collect"]["if"], "${{ !cancelled() }}")
        self.assertEqual(gate["if"], "always()")
        lanes = partitioned["jobs"]["lanes"]
        self.assertEqual(lanes["strategy"]["fail-fast"], "false")
        self.assertEqual(lanes["strategy"]["matrix"]["lane"], list(check_ci.LANES))
        for job in [*workflow["jobs"].values(), *partitioned["jobs"].values()]:
            self.assertNotIn("permissions", job)
            for step in job.get("steps", []):
                if step.get("uses", "").startswith("actions/checkout@"):
                    self.assertEqual(step["with"]["persist-credentials"], "false")
        build_steps = partitioned["jobs"]["build"]["steps"]
        self.assertEqual(sum("scripts/check_ci.py build" in step.get("run", "") for step in build_steps), 1)
        review = next(step for step in steps if step.get("with", {}).get("name", "").startswith("guide-review-"))
        # The bounded summary the comment reads travels with the complete list it points to.
        self.assertEqual(
            review["with"]["path"].split()[:2], [".cache/pr-review/summary.json", ".cache/pr-review/changes.json"]
        )
        # Contributor patches are exposed by the read-only checks, as an artifact and in the step summary.
        self.assertIn(".cache/pr-review/contributors.json", review["with"]["path"].split())
        self.assertTrue(any("scripts/contributors.py" in step.get("run", "") for step in steps))
        for name in ("checks.yml", "partitioned-checks.yml"):
            self.assertNotIn("secrets.", (ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))

    def test_merge_groups_check_the_staging_bytes_without_review_data(self) -> None:
        workflow = load(".github/workflows/checks.yml")
        self.assertEqual(
            workflow["concurrency"]["group"], "guide-checks-${{ github.event.pull_request.number || github.ref }}"
        )
        called = workflow["jobs"]["partitioned"]["with"]
        self.assertEqual(
            called["base"], "${{ github.event.pull_request.base.sha || github.event.merge_group.base_sha }}"
        )
        self.assertEqual(
            called["head"], "${{ github.event.pull_request.head.sha || github.event.merge_group.head_sha }}"
        )
        self.assertEqual(called["channel"], "${{ github.event_name == 'merge_group' && 'preview' || 'local' }}")
        self.assertEqual(called["review"], "${{ github.event_name == 'pull_request' }}")
        self.assertEqual(workflow["jobs"]["quick"]["if"], "github.event_name == 'pull_request'")
        partitioned = load(".github/workflows/partitioned-checks.yml")
        self.assertEqual(partitioned["env"], {"FAIR_GUIDE_BUILD_CHANNEL": "${{ inputs.channel }}"})
        review_steps = [
            step
            for step in partitioned["jobs"]["collect"]["steps"]
            if "pr_summary.py" in step.get("run", "")
            or "contributors.py" in step.get("run", "")
            or step.get("with", {}).get("name", "").startswith("guide-review-")
        ]
        self.assertEqual(len(review_steps), 3)
        for step in review_steps:
            self.assertEqual(step["if"], "always() && inputs.review", "merge groups prepare no review data")
        # The trusted review comment answers pull-request runs only, never merge-group runs.
        comment = load(".github/workflows/pr-summary.yml")["jobs"]["comment"]
        self.assertEqual(comment["if"], "github.event.workflow_run.event == 'pull_request'")

    def test_pull_requests_merge_groups_and_the_deployment_fallback_share_one_partitioned_check(self) -> None:
        callers = {}
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            for name, job in load(path.relative_to(ROOT).as_posix())["jobs"].items():
                if job.get("uses") == "./.github/workflows/partitioned-checks.yml":
                    callers[(path.name, name)] = job.get("with", {})
                for step in job.get("steps", []):
                    if re.search(r"check_ci\.py (build|lane|collect)\b", step.get("run", "")):
                        self.assertIn(path.name, ("partitioned-checks.yml", "deploy.yml"), "one owner of the lanes")
        self.assertEqual(set(callers), {("checks.yml", "partitioned"), ("deploy.yml", "fallback-checks")})
        fallback = callers[("deploy.yml", "fallback-checks")]
        self.assertEqual(fallback, {"channel": "preview", "staging": "true"}, "a trusted run restores no cache")
        staging = next(
            step
            for step in load(".github/workflows/partitioned-checks.yml")["jobs"]["collect"]["steps"]
            if step.get("with", {}).get("name") == "staging-site"
        )
        self.assertEqual(staging["if"], "inputs.staging", "kept only after every step before it passed")
        self.assertEqual(staging["with"]["include-hidden-files"], "true", "the checked site marker travels with it")

    def test_quick_feedback_runs_beside_the_build_with_only_its_own_tools(self) -> None:
        quick = load(".github/workflows/checks.yml")["jobs"]["quick"]
        self.assertNotIn("needs", quick, "quick feedback does not wait for the build")
        runs = [step.get("run", "") for step in quick["steps"]]
        self.assertTrue(any('scripts/check_ci.py quick --base "$BASE_SHA"' in run for run in runs))
        install = next(run for run in runs if "pip install" in run)
        self.assertIn("grep -E '^ruff==' requirements-dev.txt", install, "Ruff keeps its single pinned version")
        self.assertNotIn("-r requirements-dev.txt", install)
        self.assertTrue(any("cat .cache/quick/summary.md" in run for run in runs))

    def test_dependency_caches_follow_the_lockfiles_and_stay_out_of_trusted_runs(self) -> None:
        checks = load(".github/workflows/partitioned-checks.yml")
        quick = load(".github/workflows/checks.yml")["jobs"]["quick"]
        node = next(step for step in quick["steps"] if step.get("uses", "").startswith("actions/setup-node@"))
        self.assertEqual((node["with"]["cache"], node["with"]["cache-dependency-path"]), ("npm", "package-lock.json"))
        self.assertEqual(load(".github/workflows/checks.yml")["jobs"]["partitioned"]["with"]["cache"], "true")
        self.assertEqual(checks["on"]["workflow_call"]["inputs"]["cache"]["default"], "false")
        for name, job in checks["jobs"].items():
            for step in job["steps"]:
                if step.get("uses", "").startswith("actions/setup-node@"):
                    self.assertEqual(step["with"]["cache"], "${{ inputs.cache && 'npm' || '' }}", name)
                    self.assertEqual(step["with"]["cache-dependency-path"], "package-lock.json", name)
                if step.get("uses", "").startswith("actions/setup-python@") and "cache" in step.get("with", {}):
                    # Only lanes installing the full requirements save under their key, so no partial install can.
                    self.assertEqual(name, "lanes")
                    self.assertEqual(
                        step["with"]["cache"],
                        "${{ inputs.cache && (matrix.lane == 'cpu' || matrix.lane == 'unit') && 'pip' || '' }}",
                    )
                    self.assertEqual(step["with"]["cache-dependency-path"], "requirements-dev.txt")
        lane_steps = checks["jobs"]["lanes"]["steps"]
        python_tools = next(step for step in lane_steps if "pip install -r requirements-dev.txt" in step.get("run", ""))
        self.assertEqual(
            python_tools["if"],
            "matrix.lane == 'cpu' || matrix.lane == 'unit'",
            "browser lanes need the standard library only",
        )
        browsers = next(step for step in lane_steps if "npm run browsers" in step.get("run", ""))
        self.assertEqual(browsers["if"], "startsWith(matrix.lane, 'browser-')")
        lane = next(step for step in lane_steps if "check_ci.py lane" in step.get("run", ""))
        self.assertEqual(lane["env"]["CHECK_CACHE_PIP"], "${{ steps.python.outputs.cache-hit }}")
        self.assertEqual(lane["env"]["CHECK_CACHE_NPM"], "${{ steps.node.outputs.cache-hit }}")
        self.assertNotIn("env", checks["jobs"]["collect"], "the collector launches no browser")
        # Pull-request caches are scoped to their ref; trusted workflows restore no dependency cache, so a pull
        # request's packages never reach them. The reusable checks cache only when their caller asks, and only
        # checks.yml asks. (The health watch keeps only its own run state in a cache.)
        dependencies = re.compile(r"\.npm|node_modules|pip|ms-playwright|site-packages")
        for path in ROOT.glob(".github/workflows/*.yml"):
            if path.name in ("checks.yml", "partitioned-checks.yml"):
                continue
            for job in load(path.relative_to(ROOT).as_posix())["jobs"].values():
                for step in job.get("steps", []):
                    self.assertNotIn("cache", step.get("with", {}), f"{path.name}: {step.get('uses')}")
                    if step.get("uses", "").startswith("actions/cache"):
                        self.assertNotRegex(step["with"]["path"], dependencies, path.name)

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
        self.assertEqual(len(scripts), 2)
        self.assertIn("require('./.github/scripts/comment-summary.cjs')", scripts[0])
        self.assertNotIn("pr-review-incoming", scripts[0])
        # Area labels come from the API's file list, never the artifact, even when the comment step fails.
        self.assertIn("require('./.github/scripts/labels.cjs')", scripts[1])
        labels = next(step for step in steps if "labels.cjs" in step.get("with", {}).get("script", ""))
        self.assertEqual(labels["if"], "${{ !cancelled() }}")
        source = (ROOT / ".github/scripts/labels.cjs").read_text(encoding="utf-8")
        self.assertIn("pulls.listFiles", source)
        self.assertNotIn("pr-review-incoming", source)
        self.assertNotIn("removeLabel", source, "automation only adds labels")

    def test_source_refresh_runs_trusted_code_and_writes_only_through_the_scoped_app(self) -> None:
        text = (ROOT / ".github/workflows/source-refresh.yml").read_text(encoding="utf-8")
        workflow = load(".github/workflows/source-refresh.yml")
        self.assertEqual(set(workflow["on"]), {"schedule", "workflow_dispatch", "workflow_call"})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        # Interdependent sources share one queue; waiting requests are kept rather than replaced.
        self.assertNotIn("concurrency", workflow)
        self.assertEqual(workflow["jobs"]["refresh"]["concurrency"], {"group": "source-refresh", "queue": "max"})
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
        answer = next(step for step in steps if step.get("name") == "Reply to the refresh command")
        self.assertIn("always()", answer["if"])
        self.assertIn("github.event_name == 'issue_comment'", answer["if"])
        self.assertEqual(answer["with"]["github-token"], "${{ steps.app.outputs.token }}")
        self.assertLess(
            steps.index(answer), steps.index(next(s for s in steps if s.get("name", "").startswith("Report")))
        )
        self.assertNotIn("git push", text)
        self.assertNotIn("merge", text.lower().replace("never merges", ""))

    def test_fix_duplicates_command_is_trusted_and_same_repo_only(self) -> None:
        text = (ROOT / ".github/workflows/fix-duplicates.yml").read_text(encoding="utf-8")
        workflow = load(".github/workflows/fix-duplicates.yml")
        self.assertEqual(set(workflow["on"]), {"workflow_call"})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertNotIn("pull_request_target", text)
        job = workflow["jobs"]["fix"]
        self.assertIn("github.event.issue.pull_request", job["if"])
        self.assertIn("/fix-duplicates", job["if"])
        self.assertEqual(
            job["concurrency"], {"group": "fix-duplicates-${{ github.event.issue.number }}", "queue": "max"}
        )
        steps = job["steps"]
        for step in steps:
            if step.get("uses", "").startswith("actions/checkout@"):
                self.assertEqual(step["with"]["ref"], "${{ github.event.repository.default_branch }}")
                self.assertEqual(step["with"]["persist-credentials"], "false")
        app = next(step for step in steps if step.get("uses", "").startswith("actions/create-github-app-token@"))
        self.assertEqual(
            {key: value for key, value in app["with"].items() if key.startswith("permission-")},
            {"permission-contents": "write", "permission-pull-requests": "write"},
        )
        self.assertIn("SOURCE_REFRESH_CLIENT_ID", app["with"]["client-id"])
        self.assertIn("SOURCE_REFRESH_APP_PRIVATE_KEY", app["with"]["private-key"])
        handler = next(step for step in steps if "scripts/fix_duplicates.py" in step.get("run", ""))
        self.assertNotIn("github.event.comment", handler["run"], "comment text never becomes shell text")
        self.assertIn("COMMENT_BODY", handler["env"])
        self.assertIn("CHECK_TOKEN", handler["env"])
        self.assertIn("--comment", handler["run"])
        self.assertIn("--check-token", handler["run"])
        self.assertIn("--expected-head", handler["run"])
        extract = next(step for step in steps if step.get("name") == "Extract the pull request content as data")
        self.assertIn('git archive "$archived_head"', extract["run"])
        self.assertIn('git archive "$archived_head" content assets profile index.html |', extract["run"])
        self.assertIn('"$archived_head" > .cache/fix-duplicates-head', extract["run"])
        self.assertNotIn("git push", text)
        self.assertNotIn("pulls.merge", text)
        self.assertNotIn("merge_pull", text)
        collect = load(".github/workflows/partitioned-checks.yml")["jobs"]["collect"]["steps"]
        review = next(step for step in collect if step.get("with", {}).get("name", "").startswith("guide-review-"))
        self.assertIn("${{ steps.collect.outputs.suggestions_path }}", review["with"]["path"])
        self.assertNotIn(".cache/pr-review/suggestions.json", review["with"]["path"].split())
        collector = next(step for step in collect if "check_ci.py collect" in step.get("run", ""))
        self.assertEqual(collector["env"]["PR_HEAD_SHA"], "${{ inputs.head }}")
        self.assertEqual(collector["id"], "collect")

    def test_comment_commands_filter_first_and_keep_every_accepted_request(self) -> None:
        text = (ROOT / ".github/workflows/commands.yml").read_text(encoding="utf-8")
        workflow = load(".github/workflows/commands.yml")
        self.assertEqual(workflow["on"], {"issue_comment": {"types": ["created"]}})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        # No workflow-level group: an ordinary comment cannot replace a command waiting for its resource.
        self.assertNotIn("concurrency", workflow)
        jobs = workflow["jobs"]
        self.assertEqual(jobs["parse"]["if"], "startsWith(github.event.comment.body, '/')")
        self.assertNotIn("permissions", jobs["parse"], "the filter runs with the read-only token")
        for name in ("help", "outcome"):
            self.assertEqual(
                jobs[name]["permissions"], {"contents": "read", "issues": "write", "pull-requests": "write"}
            )
        # Acknowledgement also reads run state, to name an earlier run that holds the same resource.
        self.assertEqual(
            jobs["acknowledge"]["permissions"],
            {"contents": "read", "actions": "read", "issues": "write", "pull-requests": "write"},
        )
        self.assertEqual(workflow["run-name"], "Comment on #${{ github.event.issue.number }}")
        for name, called in (("fix-duplicates", "fix-duplicates.yml"), ("refresh", "source-refresh.yml")):
            self.assertEqual(jobs[name]["uses"], f"./.github/workflows/{called}")
            self.assertEqual(jobs[name]["secrets"], "inherit")
            self.assertIn("needs.acknowledge.outputs.accepted == 'true'", jobs[name]["if"])
        self.assertEqual(jobs["outcome"]["needs"], ["parse", "acknowledge", "fix-duplicates", "refresh"])
        self.assertIn("always()", jobs["outcome"]["if"])
        for job in jobs.values():
            for step in job.get("steps", []):
                if step.get("uses", "").startswith("actions/checkout@"):
                    self.assertEqual(step["with"]["ref"], "${{ github.event.repository.default_branch }}")
                    self.assertEqual(step["with"]["persist-credentials"], "false")
                self.assertNotIn("github.event.comment", step.get("run", ""), "comment text never becomes shell text")
        self.assertNotIn("pull_request_target", text)
        self.assertNotIn("secrets.", text, "privileged credentials stay inside the called workflows")
        # Nothing else in the repository is started by comments.
        others = [
            path.name
            for path in (ROOT / ".github/workflows").glob("*.yml")
            if path.name != "commands.yml" and "issue_comment" in load(f".github/workflows/{path.name}").get("on", {})
        ]
        self.assertEqual(others, [])

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
        self.assertNotIn("secrets.", json.dumps(job), "the watch holds no credential")
        self.assertNotIn("git push", text)
        # Live monitoring stays out of the deterministic pull-request checks.
        self.assertNotIn("watch_sources", (ROOT / ".github/workflows/checks.yml").read_text(encoding="utf-8"))

    def test_adoption_steps_preserve_failure_before_writing_the_summary(self) -> None:
        # Check adoption itself: condition layout and shell selection cannot bypass this invariant.
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            for name, job in load(path.relative_to(ROOT).as_posix())["jobs"].items():
                for step in job.get("steps", []):
                    script = step.get("run", "")
                    adoption = script.find("scripts/check_ci.py adopt")
                    if adoption >= 0:
                        with self.subTest(workflow=path.name, job=name, step=step.get("name") or step.get("id")):
                            self.assertIn("set -o pipefail", script[:adoption])

    def test_the_weekly_audit_reads_the_project_alone_with_a_read_only_token(self) -> None:
        jobs = load(".github/workflows/health-watch.yml")["jobs"]
        audit = jobs["audit"]
        self.assertFalse("needs" in audit or "needs" in jobs["watch"], "neither job can stop the other")
        self.assertEqual(audit["permissions"], {"actions": "read", "contents": "read", "issues": "read"})
        checkout = next(step for step in audit["steps"] if step.get("uses", "").startswith("actions/checkout@"))
        self.assertEqual(checkout["with"]["ref"], "${{ github.event.repository.default_branch }}")
        self.assertEqual(checkout["with"]["persist-credentials"], "false")
        app = next(
            step for step in audit["steps"] if step.get("uses", "").startswith("actions/create-github-app-token@")
        )
        self.assertEqual(app["continue-on-error"], "true", "a token the App cannot issue is reported, not fatal")
        requested = {key: value for key, value in app["with"].items() if key.startswith("permission-")}
        self.assertEqual(requested, {"permission-organization-projects": "read"})
        self.assertEqual(app["with"]["owner"], "${{ github.repository_owner }}", "Projects belong to the organization")
        self.assertEqual(re.findall(r"secrets\.\w+", json.dumps(audit)), ["secrets.SOURCE_REFRESH_APP_PRIVATE_KEY"])
        run = next(step for step in audit["steps"] if "audit_repository.py" in step.get("run", ""))
        self.assertEqual(
            run["env"],
            {"GH_TOKEN": "${{ github.token }}", "GH_PROJECT_TOKEN": "${{ steps.app.outputs.token }}"},
            "the App token reads only the Project; everything else uses the job's token",
        )
        self.assertIn("--digest .cache/audit/project-and-settings.md > /dev/null", run["run"])
        self.assertNotIn("--fix", run["run"], "the weekly audit never writes")
        self.assertIn("test -s .cache/audit/project-and-settings.md", run["run"], "only a missing section fails")
        # The repository's logs and artifacts are public and the Project is not: only the redacted section leaves.
        self.assertNotIn("--json", run["run"])
        uploads = [step for step in audit["steps"] if step.get("uses", "").startswith("actions/upload-artifact@")]
        self.assertEqual(
            [(upload["if"], upload["with"]["path"]) for upload in uploads],
            [("always()", ".cache/audit/project-and-settings.md")],
        )

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
        stage = deploy["jobs"]["stage"]
        self.assertEqual(stage["if"], "needs.sources.outputs.kind == 'branch'", "a tag run prepares no staging site")
        self.assertEqual(stage["env"], {"FAIR_GUIDE_BUILD_CHANNEL": "preview"}, "the bytes the merge queue checks")
        runs = [step.get("run", "") for step in stage["steps"]]
        self.assertIn("python scripts/check_ci.py build", runs)
        self.assertFalse(any("check_all.py" in run for run in runs), "a reused result runs no check again")
        adopt = next(step for step in stage["steps"] if step.get("id") == "adopt")
        self.assertIn("scripts/check_ci.py adopt --incoming .cache/queue-result", adopt["run"])
        self.assertIn('echo "Full checks: $QUEUE_REASON."', adopt["run"], "the summary names the fallback reason")
        # The first hosted reuse (run 40147547699) took tee's status for the adoption's and uploaded an unchecked site.
        self.assertLess(adopt["run"].index("set -o pipefail"), adopt["run"].index("check_ci.py adopt"))
        queue = next(step for step in stage["steps"] if step.get("id") == "queue")
        self.assertIn("queueResult", queue["with"]["script"])
        kept = next(step for step in stage["steps"] if step.get("with", {}).get("name") == "staging-site")
        self.assertEqual(kept["if"], "steps.adopt.outputs.reused == 'true'")
        self.assertEqual(kept["with"]["include-hidden-files"], "true", "the checked site marker travels with staging")
        build = next(step for step in stage["steps"] if step.get("id") == "build")
        self.assertEqual(build["continue-on-error"], "true", "a failed staging build only means no reuse")
        self.assertEqual(queue["if"], "steps.build.outcome == 'success'")
        fallback = deploy["jobs"]["fallback-checks"]
        self.assertIn("needs.stage.outputs.reused != 'true'", fallback["if"])
        self.assertIn("!cancelled()", fallback["if"], "a failed reuse attempt still falls back to the full checks")
        publish = load(".github/workflows/publish.yml")["jobs"]["publish"]
        uploads = [
            step
            for step in deploy["jobs"]["production"]["steps"]
            if step.get("uses", "").startswith("actions/upload-artifact@")
        ]
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0]["with"].get("overwrite"), "true", "the release artifact is re-run safe")
        self.assertEqual(
            uploads[0]["with"]["name"],
            "guide-site-${{ needs.sources.outputs.production }}",
            "the cross-run release name stays stable",
        )
        downloads = {
            step["with"]["name"]: step["with"]["run-id"]
            for step in publish["steps"]
            if step.get("uses", "").startswith("actions/download-artifact@")
        }
        self.assertEqual(
            downloads,
            {
                "staging-site": "${{ needs.resolve.outputs.staging_run }}",
                "guide-site-${{ needs.resolve.outputs.production }}": "${{ steps.production.outputs.run }}",
            },
            "publication takes each channel from the run that checked or approved it",
        )
        # A release is drafted, and its image published, only after a publication deployed it to Pages.
        release = load(".github/workflows/release.yml")
        self.assertEqual(
            release["on"], {"workflow_run": {"workflows": ["Publish the verified site"], "types": ["completed"]}}
        )
        self.assertEqual(release["jobs"]["release"]["permissions"], {"contents": "write", "actions": "read"})
        self.assertEqual(release["jobs"]["publish"]["uses"], "./.github/workflows/publish-image.yml")
        self.assertEqual(release["jobs"]["publish"]["if"], "needs.bind.outputs.tag != ''")
        text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertNotIn("build_site", text)
        self.assertNotIn("check_all", text)
        self.assertIn("guide-site-${{ needs.bind.outputs.sha }}", text)
        image = (ROOT / ".github/workflows/publish-image.yml").read_text(encoding="utf-8")
        self.assertIn("guide-site-${{ inputs.commit }}", image)
        bind = release["jobs"]["bind"]
        self.assertIn("workflow_run.event == 'workflow_run'", bind["if"])
        self.assertIn("workflow_run.head_repository.full_name == github.repository", bind["if"])
        record = next(step for step in bind["steps"] if step.get("with", {}).get("name") == "pages-identity")
        self.assertEqual(record["with"]["run-id"], "${{ github.event.workflow_run.id }}")
        self.assertIn("publishedRelease({ github, context })", bind["steps"][-1]["with"]["script"])

    def test_only_new_production_bytes_wait_for_approval_and_preparation_is_cancelled_per_ref(self) -> None:
        deploy = load(".github/workflows/deploy.yml")
        self.assertEqual(
            deploy["concurrency"],
            {"group": "deploy-${{ github.ref }}", "cancel-in-progress": "${{ !startsWith(github.ref, 'refs/tags/') }}"},
            "a newer push cancels older preparation; nothing cancels a release tag",
        )
        approval = deploy["jobs"]["approve-production"]
        self.assertEqual(approval["environment"], {"name": "production"})
        self.assertEqual(approval["if"], "needs.sources.outputs.kind == 'tag' && needs.sources.outputs.build == 'true'")
        self.assertEqual(approval["permissions"], {})
        environments = {
            job.get("environment", {}).get("name") for job in deploy["jobs"].values() if "environment" in job
        }
        self.assertEqual(environments, {"production"}, "a tag never deploys to github-pages itself")
        superseded = deploy["jobs"]["superseded"]
        self.assertEqual(superseded["if"], "cancelled()")
        self.assertIn("superseded({ github, context })", superseded["steps"][-1]["with"]["script"])

    def test_release_helpers_never_spread_the_workflow_context(self) -> None:
        pattern = re.compile(r"\{\s*\.\.\.context\s*[,}]")
        for path in [*ROOT.glob(".github/workflows/*.yml"), *ROOT.glob(".github/scripts/*.cjs")]:
            self.assertNotRegex(
                path.read_text(encoding="utf-8"),
                pattern,
                f"{path.name} spreads the @actions/github context, which drops its repo getter",
            )
        for name, helper in (
            ("deploy.yml", "reuse"),
            ("release.yml", "draftRelease"),
            ("publish-image.yml", "assertPromotion"),
        ):
            text = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
            self.assertIn("refContext", text, f"{name} derives the {helper} context through refContext")

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
        for fact in (
            "independent eligible reviewer",
            "explicit acceptance before tagging",
            "ORCID iD listed",
            "package-lock.json",
        ):
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
        self.assertEqual(
            {entry["package-ecosystem"]: entry["directory"] for entry in updates},
            {"github-actions": "/", "npm": "/", "pip": "/", "docker": "/docker"},
        )
        for entry in updates:
            with self.subTest(ecosystem=entry["package-ecosystem"]):
                self.assertEqual(entry["schedule"], {"interval": "weekly"})
                self.assertEqual(entry["open-pull-requests-limit"], "30")
                # Patch and minor versions share one PR per ecosystem; a major update and security updates stay alone.
                self.assertEqual(
                    entry["groups"],
                    {
                        "minor-and-patch": {
                            "applies-to": "version-updates",
                            "patterns": ["*"],
                            "update-types": ["minor", "patch"],
                        }
                    },
                )


class TokenPermissions(unittest.TestCase):
    """Each job requests exactly the reviewed token permissions in .github/repository.toml."""

    def test_every_job_requests_exactly_its_reviewed_permissions(self) -> None:
        self.assertEqual(token_differences(reviewed_tokens(), token_requests()), [])

    def test_a_planted_extra_permission_fails_and_names_the_job(self) -> None:
        actual = token_requests()
        github, app = actual[("partitioned-checks.yml", "build")]
        actual[("partitioned-checks.yml", "build")] = ({**github, "issues": "write"}, app)
        github, app = actual[("tag-release.yml", "tag")]
        actual[("tag-release.yml", "tag")] = (github, {**app, "pull-requests": "write"})
        actual[("checks.yml", "unlisted")] = ({"contents": "read"}, {})
        self.assertEqual(
            token_differences(reviewed_tokens(), actual),
            [
                "checks.yml job unlisted: no reviewed token entry in .github/repository.toml",
                "partitioned-checks.yml job build: GITHUB_TOKEN requests issues: write, reviewed none",
                "tag-release.yml job tag: App token requests pull-requests: write, reviewed none",
            ],
        )

    def test_a_job_without_explicit_permissions_is_refused(self) -> None:
        actual = token_requests()
        actual[("partitioned-checks.yml", "build")] = (None, {})
        self.assertIn(
            "partitioned-checks.yml job build: no explicit permissions, so GITHUB_TOKEN gets the repository default",
            token_differences(reviewed_tokens(), actual),
        )

    def test_app_token_requests_stay_within_the_reviewed_registration(self) -> None:
        config = tomllib.loads((ROOT / ".github/repository.toml").read_text(encoding="utf-8"))
        registered = config["app"]["permissions"]
        rank = {"read": 1, "write": 2}
        for (workflow, job), (_, app) in token_requests().items():
            for permission, access in app.items():
                name = permission.replace("-", "_")
                with self.subTest(workflow=workflow, job=job, permission=permission):
                    self.assertGreaterEqual(rank.get(registered.get(name), 0), rank[access])


if __name__ == "__main__":
    unittest.main()
