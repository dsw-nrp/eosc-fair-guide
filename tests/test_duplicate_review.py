"""Regression cases for the duplicate-repair trust and failure boundaries in PR 102."""

import contextlib
import io
import itertools
import json
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import test_check_ci as ci_fixtures
import test_scripts as fixtures

check_duplicates = fixtures.check_duplicates
check_ci = ci_fixtures.check_ci
check_all = ci_fixtures.check_all
fix_duplicates = fixtures.fix_duplicates


def suggestion(**updates):
    return replace(
        check_duplicates.Suggestion(
            "resource:service",
            "re3data:r3d100000001",
            "link",
            True,
            "content/resources.toml",
            "resource.repository",
            "re3data",
            "r3d100000001",
            "shared address",
        ),
        **updates,
    )


def artifact_item(**updates):
    value = check_duplicates.report_payload(check_duplicates.DuplicateReport(suggestions=[suggestion()]))[
        "suggestions"
    ][0]
    return {**value, **updates}


class OwnershipTests(unittest.TestCase):
    def test_existing_owner_outside_the_duplicate_pair_blocks_the_suggestion(self):
        things = [
            check_duplicates.thing("resource:a", True, {"id": "a", "fipDashboard": "r1"}, fd="r1"),
            check_duplicates.thing("resource:b", True, {"id": "b"}, url="b.example"),
            check_duplicates.thing("fip-dashboard:r1", False, {"id": "r1"}, fd="r1", url="b.example"),
        ]
        with mock.patch.object(check_duplicates, "entries", return_value=things):
            report = check_duplicates.check({}, [])
        self.assertTrue(report.errors)
        self.assertEqual(report.suggestions, [])

    def test_competing_proposed_owners_are_not_safe(self):
        things = [
            check_duplicates.thing("resource:a", True, {"id": "a"}, url="a.example"),
            check_duplicates.thing("resource:b", True, {"id": "b"}, doi="10.1/b"),
            check_duplicates.thing("fip-dashboard:r1", False, {"id": "r1"}, fd="r1", url="a.example", doi="10.1/b"),
        ]
        with mock.patch.object(check_duplicates, "entries", return_value=things):
            self.assertEqual(check_duplicates.check({}, []).suggestions, [])

    def test_identical_suggestions_are_emitted_once(self):
        things = [
            check_duplicates.thing("resource:a", True, {"id": "a"}, url="a.example", doi="10.1/a"),
            check_duplicates.thing("fip-dashboard:r1", False, {"id": "r1"}, fd="r1", url="a.example", doi="10.1/a"),
        ]
        with mock.patch.object(check_duplicates, "entries", return_value=things):
            self.assertEqual(len(check_duplicates.check({}, []).suggestions), 1)

    def test_cross_registry_identity_cannot_acquire_competing_owners(self):
        things = [
            check_duplicates.thing("repository:a", True, {"id": "a"}, url="a.example"),
            check_duplicates.thing("resource:b", True, {"id": "b"}, url="b.example"),
            check_duplicates.thing("re3data:r3d1", False, {"id": "r3d1"}, r3d="r3d1", fd="r1", url="a.example"),
            check_duplicates.thing("fip-dashboard:r1", False, {"id": "r1"}, r3d="r3d1", fd="r1", url="b.example"),
        ]
        with mock.patch.object(check_duplicates, "entries", return_value=things):
            self.assertEqual(check_duplicates.check({}, []).suggestions, [])


class LocalRepairTests(fixtures.FixtureCase):
    def setUp(self):
        super().setUp()
        fixtures.FixDuplicateCommandTests.prepare(self)
        self.path = self.root / "content/resources.toml"
        self.before = self.path.read_bytes()

    def run_local(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = check_duplicates.main(["--root", str(self.root), "--fix"])
        return status, output.getvalue()

    def test_apply_refuses_invalid_combinations_and_unsafe_suggestions(self):
        for item in (
            suggestion(table=""),
            suggestion(safe=False),
            suggestion(resolution="merge"),
            suggestion(file="content/sources.toml"),
            suggestion(field_name="knav"),
        ):
            with self.subTest(item=item):
                self.assertIsNone(check_duplicates.apply_suggestion(self.root, item))
                self.assertEqual(self.path.read_bytes(), self.before)

    def test_final_duplicate_failure_restores_exact_original_bytes(self):
        first = check_duplicates.check(fixtures.build_crate.load_content(self.root / "content"), [])
        rejected = check_duplicates.DuplicateReport(errors=["planted remaining duplicate"])
        with mock.patch.object(check_duplicates, "check", side_effect=[first, rejected]):
            status, output = self.run_local()
        self.assertNotEqual(status, 0)
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assertNotIn("applied safe link suggestions", output)

    def test_failed_content_reload_restores_original_bytes(self):
        content = fixtures.build_crate.load_content(self.root / "content")
        with mock.patch.object(
            check_duplicates, "load_content", side_effect=[content, ValueError("planted parse error")]
        ):
            status, output = self.run_local()
        self.assertNotEqual(status, 0)
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assertIn("planted parse error", output)

    def test_successful_replacement_needs_no_post_write_read(self):
        read = Path.read_bytes
        swap = check_duplicates.os.replace
        swapped = False

        def replace_file(source, target):
            nonlocal swapped
            result = swap(source, target)
            if Path(target) == self.path:
                swapped = True
            return result

        def reject_discovery_read(path):
            if path == self.path and swapped:
                raise OSError("planted post-replacement read failure")
            return read(path)

        with (
            mock.patch.object(check_duplicates.os, "replace", side_effect=replace_file),
            mock.patch.object(Path, "read_bytes", reject_discovery_read),
        ):
            status, output = self.run_local()
        self.assertEqual(status, 0, output)
        self.assertTrue(swapped)
        self.assertNotEqual(self.path.read_bytes(), self.before)
        self.assertIn(f"--- {self.path}\n+++ {self.path}\n@@ ", output)
        self.assertIn('\n+re3data = "r3d100000001"\n', output)
        self.assertIn("check_duplicates: applied safe link suggestions.", output)
        self.assertIn(
            "Add one provenance action naming the person, the consulted source/record and the changed result; "
            "this command does not write it.",
            output,
        )

    def test_post_swap_cleanup_failure_restores_the_replaced_file(self):
        swap = check_duplicates.os.replace
        unlink = Path.unlink
        swapped = False
        failed = False

        def replace_file(source, target):
            nonlocal swapped
            result = swap(source, target)
            swapped = swapped or Path(target) == self.path
            return result

        def fail_cleanup(path, *args, **kwargs):
            nonlocal failed
            if swapped and not failed and path.parent == self.path.parent and path.suffix == ".tmp":
                failed = True
                raise OSError("planted post-swap cleanup failure")
            return unlink(path, *args, **kwargs)

        with (
            mock.patch.object(check_duplicates.os, "replace", side_effect=replace_file),
            mock.patch.object(Path, "unlink", fail_cleanup),
        ):
            status, output = self.run_local()
        self.assertNotEqual(status, 0)
        self.assertTrue(failed)
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assertIn("planted post-swap cleanup failure", output)

    def test_later_apply_error_restores_earlier_file(self):
        source = self.root / "content/sources.toml"
        source_before = source.read_bytes()
        first = check_duplicates.DuplicateReport(
            suggestions=[
                suggestion(),
                suggestion(
                    entry="source:report",
                    record="knav:k1",
                    file="content/sources.toml",
                    table="",
                    field_name="knav",
                    value="k1",
                ),
            ]
        )
        apply = check_duplicates.apply_suggestion
        count = 0

        def failing(root, item, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("planted second write failure")
            return apply(root, item, **kwargs)

        with (
            mock.patch.object(check_duplicates, "check", return_value=first),
            mock.patch.object(check_duplicates, "apply_suggestion", side_effect=failing),
        ):
            status, output = self.run_local()
        self.assertNotEqual(status, 0)
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assertEqual(source.read_bytes(), source_before)
        self.assertNotIn("applied safe link suggestions", output)

    def test_replace_failure_preserves_bytes_and_cleans_temporary_file(self):
        before_files = set(self.path.parent.iterdir())
        with mock.patch.object(check_duplicates.os, "replace", side_effect=OSError("planted replace failure")):
            status, output = self.run_local()
        self.assertNotEqual(status, 0)
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assertEqual(set(self.path.parent.iterdir()), before_files)
        self.assertIn("planted replace failure", output)

    def test_temporary_write_failure_preserves_bytes(self):
        before_files = set(self.path.parent.iterdir())
        write_bytes = Path.write_bytes

        def fail_temporary(path, data):
            if path != self.path and path.parent == self.path.parent:
                raise OSError("planted temporary write failure")
            return write_bytes(path, data)

        with mock.patch.object(Path, "write_bytes", fail_temporary):
            status, output = self.run_local()
        self.assertNotEqual(status, 0)
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assertEqual(set(self.path.parent.iterdir()), before_files)
        self.assertIn("planted temporary write failure", output)

    def test_changed_target_is_not_overwritten(self):
        real_replace = check_duplicates.os.replace
        newer = self.before + b"\n# concurrent edit\n"

        def move_after_edit(source, target):
            self.path.write_bytes(newer)
            return real_replace(source, target)

        # Simulate the edit while the temporary sibling is being written, before the final byte guard.
        real_write = Path.write_bytes

        def write_after_edit(path, data):
            result = real_write(path, data)
            if path != self.path and path.parent == self.path.parent:
                self.path.write_bytes(newer)
            return result

        with (
            mock.patch.object(Path, "write_bytes", write_after_edit),
            mock.patch.object(check_duplicates.os, "replace", wraps=move_after_edit) as move,
        ):
            status, _ = self.run_local()
        self.assertNotEqual(status, 0)
        self.assertEqual(self.path.read_bytes(), newer)
        move.assert_not_called()

    def test_rollback_failure_is_reported_explicitly(self):
        actual = check_duplicates.os.replace
        calls = 0

        def fail_rollback(source, target):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise OSError("planted restoration failure")
            return actual(source, target)

        first = check_duplicates.check(fixtures.build_crate.load_content(self.root / "content"), [])
        with (
            mock.patch.object(
                check_duplicates, "check", side_effect=[first, check_duplicates.DuplicateReport(errors=["bad"])]
            ),
            mock.patch.object(check_duplicates.os, "replace", side_effect=fail_rollback),
        ):
            status, output = self.run_local()
        self.assertNotEqual(status, 0)
        self.assertIn("restore", output.lower())
        self.assertIn(str(self.path), output)

    def test_shared_accepted_loader_is_used_by_both_handler_paths(self):
        with mock.patch.object(check_duplicates, "_accepted", return_value=[]) as load:
            fix_duplicates.load_fix_context(self.root)
            fix_duplicates.content_errors(self.root)
        self.assertEqual(load.call_count, 2)

    def test_refresh_repair_commit_survives_a_failed_success_comment(self):
        command_fixtures = fixtures.FixDuplicateCommandTests
        fake = command_fixtures.FakeGitHub("dsw-nrp/eosc-fair-guide", "token")
        fake.pull_data = command_fixtures.github_pull(self)
        fake.pull_data["head"]["ref"] = "refresh/re3data"
        with (
            mock.patch.object(fix_duplicates, "GitHub", return_value=fake),
            mock.patch.object(fake, "comment", side_effect=RuntimeError("success comment unavailable")),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            status = fix_duplicates.main(
                [
                    "--root",
                    str(self.root),
                    "--pr",
                    "82",
                    "--commenter",
                    "tester",
                    "--repository",
                    fake.repository,
                    "--token",
                    "token",
                    "--expected-head",
                    "a" * 40,
                ]
            )
        self.assertEqual(status, 1)
        self.assertEqual(len(fake.commits), 1)
        self.assertEqual(fake.commits[0][0]["head"]["ref"], "refresh/re3data")
        self.assertIn("content/provenance.toml", fake.commits[0][1])
        workflow = (check_ci.ROOT / ".github/workflows/fix-duplicates.yml").read_text(encoding="utf-8")
        self.assertIn("Check the PR branch state; a commit may already exist", workflow)
        self.assertNotIn("No change is assumed", workflow)


class ArtifactTests(unittest.TestCase):
    def test_all_required_strings_reject_arrays_and_objects(self):
        for key, bad in itertools.product(("entry", "record", "file", "field", "table", "value", "reason"), ([], {})):
            with self.subTest(key=key, bad=bad), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                check_ci.write_json(
                    root / "cpu/details/duplicates.json",
                    {"formatVersion": 1, "suggestions": [artifact_item(**{key: bad})]},
                )
                self.assertEqual(check_ci.load_suggestions(root / "cpu", "head")["suggestions"], [])

    def test_invalid_placement_is_filtered(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            check_ci.write_json(
                root / "cpu/details/duplicates.json", {"formatVersion": 1, "suggestions": [artifact_item(table="")]}
            )
            self.assertEqual(check_ci.load_suggestions(root / "cpu", "head")["suggestions"], [])

    def test_python_node_placement_parity(self):
        cases = [
            artifact_item(entry=f"{kind}:id", file=file, table=table, field=field)
            for kind, file, table, field in itertools.product(
                ("resource", "repository", "source", "unknown"),
                ("content/resources.toml", "content/repositories.toml", "content/sources.toml", "outside.toml"),
                ("", "resource.repository", "other"),
                ("re3data", "fipDashboard", "knav", "other"),
            )
        ]
        expected = [check_duplicates.valid_placement(x["entry"], x["file"], x["table"], x["field"]) for x in cases]
        node = subprocess.run(
            [
                "node",
                "-e",
                "const {validSuggestion}=require('./.github/scripts/comment-summary.cjs');"
                "const x=JSON.parse(require('node:fs').readFileSync(0,'utf8'));"
                "process.stdout.write(JSON.stringify(x.map(validSuggestion)));",
            ],
            input=json.dumps(cases),
            text=True,
            capture_output=True,
            check=True,
            cwd=check_ci.ROOT,
        )
        self.assertEqual(json.loads(node.stdout), expected)
        self.assertEqual(sum(expected), 7)

    def test_summary_reason_is_inert_code_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "summary.md").write_text("# Check\n", encoding="utf-8")
            check_ci.append_suggestion_summary(
                root, {"suggestions": [artifact_item(reason="https://example.test @org/team `x`\n![image](evil)")]}
            )
            text = (root / "summary.md").read_text(encoding="utf-8")
            self.assertIn("(`https://example.test", text)
            self.assertNotIn("`x`", text)


class CollectorTests(unittest.TestCase):
    def setup_collector(self, root):
        manifest, jobs, groups = ci_fixtures.PartitionTests().fixture(root / "incoming")
        jobs.append(check_all.Job("duplicates", []))
        for path in (root / "incoming").glob("*/details/*/scripts.json"):
            scripts = check_ci.read_json(path)
            for script in scripts["scripts"]:
                script["seconds"] = 1
            check_ci.write_json(path, scripts)
        manifest.update(started=0, result={"returncode": 0, "seconds": 1, "output": "built"})
        path = root / "incoming/cpu/lane.json"
        data = check_ci.read_json(path)
        data["results"].append(
            {"name": "duplicates", "returncode": 1, "seconds": 1, "output": "duplicate failure", "partial": False}
        )
        check_ci.write_json(path, data)
        check_ci.write_json(
            root / "incoming/cpu/details/duplicates.json", {"formatVersion": 1, "suggestions": [artifact_item()]}
        )
        check_ci.write_json(root / "manifest.json", manifest)
        return (
            manifest,
            jobs,
            groups,
            SimpleNamespace(
                base=None, manifest=root / "manifest.json", incoming=root / "incoming", output=root / "health"
            ),
        )

    def run_collect(self, args, jobs, groups, **patches):
        actual = check_ci.read_json
        with (
            mock.patch.object(check_ci, "verify_build"),
            mock.patch.object(check_all, "jobs", return_value=jobs),
            mock.patch.object(check_ci, "read_json") as read,
        ):
            read.side_effect = lambda path: (
                groups if path == check_ci.ROOT / "scripts/check_groups.json" else actual(path)
            )
            with contextlib.ExitStack() as stack:
                for key, value in patches.items():
                    stack.enter_context(mock.patch.object(check_ci, key, **value))
                return check_ci.collect(args)

    def test_rejected_evidence_never_publishes_suggestions(self):
        for fault in ("revision", "build", "missing-lane", "duplicate-job", "missing-case"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _, jobs, groups, args = self.setup_collector(root)
                path = args.incoming / "cpu/lane.json"
                data = check_ci.read_json(path)
                if fault == "revision":
                    data["source"] = {"revision": "stale"}
                if fault == "build":
                    data["build"] = {"site": "wrong"}
                if fault == "duplicate-job":
                    data["results"].append(data["results"][0])
                check_ci.write_json(path, data)
                if fault == "missing-lane":
                    (args.incoming / "browser-b/lane.json").unlink()
                if fault == "missing-case":
                    (args.incoming / "browser-a/details/page/scripts.json").unlink()
                check_ci.write_suggestions(args.output, {"suggestions": [artifact_item()]})
                self.assertEqual(self.run_collect(args, jobs, groups), 1)
                self.assertEqual(check_ci.read_json(root / "pr-review/suggestions.json")["suggestions"], [])
                self.assertTrue((args.output / "summary.md").is_file())

    def test_only_validated_duplicate_lane_supplies_suggestions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, jobs, groups, args = self.setup_collector(root)
            check_ci.write_json(
                args.incoming / "untrusted/details/duplicates.json",
                {"formatVersion": 1, "suggestions": [artifact_item(value="evil")]},
            )
            self.assertEqual(self.run_collect(args, jobs, groups), 1)
            self.assertEqual(
                [x["value"] for x in check_ci.read_json(root / "pr-review/suggestions.json")["suggestions"]],
                ["r3d100000001"],
            )

    def test_required_report_precedes_optional_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, jobs, groups, args = self.setup_collector(root)

            def fail(*_):
                self.assertTrue((args.output / "summary.md").is_file())
                raise OSError("optional destination unavailable")

            self.assertEqual(self.run_collect(args, jobs, groups, write_suggestions={"side_effect": fail}), 1)
            self.assertIn("duplicate failure", (args.output / "summary.md").read_text(encoding="utf-8"))

    def test_only_successful_current_run_produces_an_upload_path(self):
        for rejected in (False, True):
            with self.subTest(rejected=rejected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _, jobs, groups, args = self.setup_collector(root)
                step_output = root / "step-output"
                step_output.write_text("", encoding="utf-8")
                stale = check_ci.write_suggestions(args.output, {"suggestions": [artifact_item(value="stale")]})
                if rejected:
                    lane_path = args.incoming / "cpu/lane.json"
                    lane = check_ci.read_json(lane_path)
                    lane["source"] = {"revision": "rejected"}
                    check_ci.write_json(lane_path, lane)
                unlink = Path.unlink

                def deny_stale_removal(path, *args, rejected=rejected, stale=stale, unlink=unlink, **kwargs):
                    if rejected and path == stale:
                        raise PermissionError("cannot invalidate prior suggestions")
                    return unlink(path, *args, **kwargs)

                with (
                    mock.patch.dict(check_ci.os.environ, {"GITHUB_OUTPUT": str(step_output)}),
                    mock.patch.object(Path, "unlink", deny_stale_removal),
                ):
                    self.assertEqual(self.run_collect(args, jobs, groups), 1)
                fields = dict(line.split("=", 1) for line in step_output.read_text(encoding="utf-8").splitlines())
                if rejected:
                    self.assertNotIn("suggestions_path", fields)
                    self.assertEqual(check_ci.read_json(stale)["suggestions"][0]["value"], "stale")
                else:
                    self.assertEqual(Path(fields["suggestions_path"]), stale)
                    self.assertEqual(check_ci.read_json(stale)["suggestions"][0]["value"], "r3d100000001")
                self.assertTrue((args.output / "summary.md").is_file())

    def test_optional_errors_preserve_passing_outcome_after_report_publication(self):
        for optional in ("write_suggestions", "append_suggestion_summary", "collect_suggestions"):
            with self.subTest(optional=optional), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _, jobs, groups, args = self.setup_collector(root)
                step_output = root / "step-output"
                step_output.write_text("", encoding="utf-8")
                path = args.incoming / "cpu/lane.json"
                lane = check_ci.read_json(path)
                for row in lane["results"]:
                    row.update(returncode=0, output="passed")
                check_ci.write_json(path, lane)
                for path in args.incoming.glob("*/lane.json"):
                    lane = check_ci.read_json(path)
                    lane.update(started=1, finished=2)
                    check_ci.write_json(path, lane)

                def publish(build, results, available, selected, **kwargs):
                    check_all.emit_report(build, results, available, selected, output=kwargs["output"], previous=None)
                    return 0

                with (
                    mock.patch.object(check_all, "publish_results", side_effect=publish),
                    mock.patch.dict(check_ci.os.environ, {"GITHUB_OUTPUT": str(step_output)}),
                ):
                    status = self.run_collect(
                        args, jobs, groups, **{optional: {"side_effect": OSError("optional failure")}}
                    )
                self.assertEqual(status, 0)
                self.assertTrue((args.output / "summary.md").is_file())
                self.assertNotIn("suggestions_path=", step_output.read_text(encoding="utf-8"))

    def test_partial_result_is_failed_in_aggregate_and_health(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, jobs, groups, args = self.setup_collector(root)
            path = args.incoming / "cpu/lane.json"
            data = check_ci.read_json(path)
            data["results"][0].update(
                returncode=0, partial=True, output="\n".join(f"pending case {index}" for index in range(60))
            )
            check_ci.write_json(path, data)
            self.assertEqual(self.run_collect(args, jobs, groups), 1)
            health = check_ci.read_json(args.output / "health.json")
            row = next(x for x in health["run"]["jobs"] if x["name"] == "content")
            self.assertEqual(row["status"], "failed")
            self.assertTrue(row["partial"])
            summary = (args.output / "summary.md").read_text(encoding="utf-8")
            self.assertIn("pending case 59", summary)
            self.assertIn("Incomplete required check coverage", summary)
            self.assertIn("Incomplete required check coverage", row["output"])


class BotOutputTests(unittest.TestCase):
    def test_hostile_diff_is_fenced_and_truncation_keeps_enclosure(self):
        for diff in ("+ https://evil.test @org/team\n```\n![image](evil)\n", "`" * 70000, "`" * 40000 + "~" * 40000):
            text = fix_duplicates.bounded_comment("Applied\n\n", diff, "\nCommit: `abc`.")
            opening = text.splitlines()[2]
            self.assertTrue(opening.endswith("diff"))
            fence = opening[:-4]
            self.assertGreaterEqual(len(fence), 3)
            self.assertEqual(text.splitlines()[-3], fence)
            self.assertLessEqual(len(text), fix_duplicates.COMMENT_LIMIT)
            self.assertTrue(text.endswith("Commit: `abc`."))


if __name__ == "__main__":
    unittest.main()
