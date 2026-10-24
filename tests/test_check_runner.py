"""Resource scheduling and truthful reporting of nested check selections."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_all  # noqa: E402
import check_ci  # noqa: E402
import profile_checks  # noqa: E402
from profile_checks import TimedResult  # noqa: E402


class CheckRunnerTests(unittest.TestCase):
    def test_profiles_match_the_node_policy_and_limit_defaults_on_small_machines(self):
        policy = json.loads((check_all.ROOT / "scripts/check_policy.json").read_text(encoding="utf-8"))
        for env, profile in (({}, "local"), ({"CI": "true"}, "ci"), ({"CI": "false"}, "local")):
            self.assertEqual(check_all.execution_defaults(env, 16), {"profile": profile, **policy[profile]})
        self.assertEqual(
            check_all.execution_defaults({}, 1), {"profile": "local", "jobs": 1, "browser_workers": 1, "unit_shards": 1}
        )

    def test_local_and_partitioned_runners_share_one_budget_owner(self):
        policy = json.loads((check_all.ROOT / "scripts/check_policy.json").read_text(encoding="utf-8"))

        def budgets(module, argv, env):
            parser = check_all.argparse.ArgumentParser()
            with (
                mock.patch.dict(check_all.os.environ, env, clear=True),
                mock.patch.object(check_all.os, "cpu_count", return_value=16),
            ):
                if module is check_all:
                    check_all.add_budget_arguments(parser)
                    args = parser.parse_args(argv)
                    return args.jobs, args.browser_workers
                captured = {}
                with mock.patch.object(check_ci, "collect", side_effect=lambda args: captured.update(vars(args)) or 0):
                    check_ci.main(["collect", "--base", "main", *argv])
                return captured["jobs"], captured["browser_workers"]

        ci = (policy["ci"]["jobs"], policy["ci"]["browser_workers"])
        for module in (check_all, check_ci):
            with self.subTest(module=module.__name__):
                self.assertEqual(budgets(module, [], {"CI": "true"}), ci, "the CI profile is the policy, not a copy")
                self.assertEqual(budgets(module, [], {}), (policy["local"]["jobs"], policy["local"]["browser_workers"]))
                self.assertEqual(budgets(module, [], {"CI": "true", "CHECK_BROWSER_WORKERS": "3"}), (ci[0], 3))
                self.assertEqual(
                    budgets(
                        module, ["--jobs", "2", "--browser-workers", "5"], {"CI": "true", "CHECK_BROWSER_WORKERS": "3"}
                    ),
                    (2, 5),
                    "explicit command-line budgets win",
                )

    def test_every_child_receives_the_same_global_budget(self):
        jobs = [check_all.Job(name, []) for name in ["page", "model", "content"]]
        env = {"CHECK_BROWSER_WORKERS": "2", "CHECK_BROWSER_SLOT_DIR": "one-run-budget"}

        def run(job, received):
            self.assertEqual(received, env)
            return check_all.Result(job, 0, 0.01, "kept diagnostic")

        with mock.patch.object(check_all, "run", side_effect=run):
            results = check_all.run_all(jobs, 3, env, report=lambda _: None)
        self.assertEqual([result.job for result in results], jobs)

    def test_a_partial_browser_result_fails_its_row_and_the_run(self):
        job = check_all.Job("page", [])
        build = check_all.Result(check_all.Job("build", []), 0, 0.01, "build diagnostic")
        result = check_all.Result(job, 0, 0.01, "selected cases only", partial=True)
        with mock.patch.object(check_all.check_health, "write_report") as write:
            check_all.emit_report(build, [result], [job], [job], output=Path("unused"), previous=None)
        run = write.call_args.args[0]["run"]
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["jobs"][1]["status"], "failed")
        self.assertEqual(run["jobs"][1]["output"], "selected cases only")
        self.assertTrue(run["jobs"][1]["partial"])
        with mock.patch("builtins.print") as printed:
            self.assertEqual(check_all.finish([result], 0.0), 1)
        self.assertIn("Incomplete required check coverage (partial result).", str(printed.call_args_list))

    def test_a_complete_explicit_subset_keeps_its_partial_report_and_passes(self):
        job = check_all.Job("content", [])
        unit = check_all.Job("unit", [])
        build = check_all.Result(check_all.Job("build", []), 0, 0.01, "")
        result = check_all.Result(job, 0, 0.01, "")
        with mock.patch.object(check_all.check_health, "write_report") as write:
            check_all.emit_report(build, [result], [job, unit], [job], output=Path("unused"), previous=None)
        run = write.call_args.args[0]["run"]
        self.assertEqual(run["status"], "partial")
        self.assertEqual({item["name"]: item["status"] for item in run["jobs"]}["unit"], "not_run")
        with mock.patch("builtins.print"):
            self.assertEqual(check_all.finish([result], 0.0), 0)

    def test_successful_output_is_retained_in_full_logs(self):
        job = check_all.Job("content", [])
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "details"
            with mock.patch.object(check_all, "run", return_value=check_all.Result(job, 0, 1, "success details")):
                check_all.run_all([job], 1, {"CHECK_REPORT_DIR": str(directory)}, report=lambda _: None)
            self.assertEqual((directory.parent / "logs/content.log").read_text(encoding="utf-8"), "success details")

    def test_unit_profiler_preserves_failures_and_skips(self):
        class Example(unittest.TestCase):
            def test_fail(self):
                self.fail("deliberate failure")

            @unittest.skip("deliberate skip")
            def test_skip(self):
                pass

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Example)
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=TimedResult).run(suite)
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(len(result.skipped), 1)
        self.assertEqual(len(result.timings), 2)

    def test_broken_nested_report_fails_even_when_the_child_exits_successfully(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "page").mkdir()
            (directory / "page/scripts.json").write_text("not JSON", encoding="utf-8")
            job = check_all.Job("page", [sys.executable, "-c", "print('child success')"])
            result = check_all.run(job, {"CHECK_REPORT_DIR": str(directory)})
        self.assertFalse(result.ok)
        self.assertIn("child success", result.output)
        self.assertIn("Invalid script timing report", result.output)


class UnitShardTests(unittest.TestCase):
    """Shards run every discovered test once, in private report directories, and fail on any shard's failure."""

    MODULE = """import os, unittest
from pathlib import Path

class {name}(unittest.TestCase):
{tests}
"""

    def suite(self, root: Path, modules: dict[str, list[str]]) -> Path:
        start = root / "tests"
        start.mkdir()
        for module, bodies in modules.items():
            tests = "\n".join(f"    def test_{index}(self):\n        {body}\n" for index, body in enumerate(bodies))
            (start / f"{module}.py").write_text(self.MODULE.format(name=module.title(), tests=tests), encoding="utf-8")
        return start

    def run_shards(self, start: Path, *extra: str) -> tuple[int, dict, str, Path]:
        report = start.parent / "report"
        printed = io.StringIO()
        with mock.patch.dict(profile_checks.os.environ, {"CHECK_REPORT_DIR": str(report)}), redirect_stdout(printed):
            status = profile_checks.main(["--start", str(start), "--weights", str(start / "none.json"), *extra])
        return (
            status,
            json.loads((report / "unit-timings.json").read_text(encoding="utf-8")),
            printed.getvalue(),
            report,
        )

    def test_every_discovered_test_runs_once_and_one_report_is_merged(self):
        with tempfile.TemporaryDirectory() as temporary:
            start = self.suite(Path(temporary), {f"test_m{index}": ["pass", "pass"] for index in range(5)})
            status, report, _, _ = self.run_shards(start, "--shards", "3")
        self.assertEqual(status, 0)
        self.assertTrue(report["successful"])
        self.assertEqual(len(report["tests"]), 10)
        self.assertEqual(len({item["test"] for item in report["tests"]}), 10)
        self.assertEqual(
            sorted(module for shard in report["shards"] for module in shard["modules"]),
            [f"test_m{index}" for index in range(5)],
        )

    def test_a_failure_in_any_shard_fails_the_check_and_names_the_test(self):
        for shards in ("1", "2", "4"):
            with self.subTest(shards=shards), tempfile.TemporaryDirectory() as temporary:
                modules = {f"test_m{index}": ["pass"] for index in range(4)}
                modules["test_m2"] = ["pass", "self.fail('planted shard failure')"]
                start = self.suite(Path(temporary), modules)
                status, report, printed, _ = self.run_shards(start, "--shards", shards)
                self.assertEqual(status, 1)
                self.assertFalse(report["successful"])
                self.assertEqual(len(report["tests"]), 5, "the merged timings keep every test")
                self.assertIn("test_m2.Test_M2.test_1", printed)
                self.assertIn("planted shard failure", printed)

    def test_a_shard_that_dies_reports_the_tests_it_did_not_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            start = self.suite(Path(temporary), {"test_alive": ["pass"], "test_dead": ["os._exit(3)"]})
            status, report, printed, _ = self.run_shards(start, "--shards", "2")
        self.assertEqual(status, 1)
        self.assertFalse(report["successful"])
        self.assertIn("left no report (exit 3)", printed)
        self.assertIn("1 discovered tests did not run, first: test_dead.Test_Dead.test_0", printed)

    def test_tests_cannot_write_into_the_report_of_the_run_that_executes_them(self):
        with tempfile.TemporaryDirectory() as temporary:
            write = "(Path(os.environ['CHECK_REPORT_DIR']) / 'duplicates.json').write_text('fixture')"
            start = self.suite(Path(temporary), {"test_writer": [write]})
            status, _, _, report = self.run_shards(start, "--shards", "1")
            self.assertEqual(status, 0)
            self.assertEqual(sorted(path.name for path in report.iterdir()), ["unit-timings.json"])

    def test_shuffled_shards_run_the_same_tests_in_another_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            start = self.suite(Path(temporary), {"test_many": ["pass"] * 12, "test_more": ["pass"] * 12})
            sys.path.insert(0, str(start))
            try:
                loaded = list(
                    profile_checks.flatten(unittest.defaultTestLoader.loadTestsFromNames(["test_many", "test_more"]))
                )
                ordered = [test.id() for test in profile_checks.flatten(profile_checks.shuffled(loaded, 1729))]
            finally:
                sys.path.remove(str(start))
                for name in ("test_many", "test_more"):
                    sys.modules.pop(name, None)
            status, report, _, _ = self.run_shards(start, "--shards", "2", "--shuffle", "1729")
        self.assertEqual(status, 0)
        self.assertEqual(sorted(ordered), sorted(test.id() for test in loaded))
        self.assertNotEqual(ordered, [test.id() for test in loaded])
        self.assertEqual(report["shuffle"], 1729)
        self.assertEqual(len(report["tests"]), 24)

    def test_shards_are_packed_longest_first_and_deterministically(self):
        weights = {"test_big": 30, "test_mid": 20, "test_small": 5}
        modules = ["test_small", "test_new", "test_mid", "test_big"]
        self.assertEqual(
            profile_checks.assign(modules, weights, 2), [["test_big"], ["test_mid", "test_new", "test_small"]]
        )
        self.assertEqual(
            profile_checks.assign(list(reversed(modules)), weights, 2), profile_checks.assign(modules, weights, 2)
        )
        self.assertEqual(
            profile_checks.assign(modules, weights, 9), [["test_big"], ["test_mid"], ["test_small"], ["test_new"]]
        )
        measured = json.loads(profile_checks.WEIGHTS.read_text(encoding="utf-8"))
        self.assertIn("run 40022072478", measured["source"], "the committed weights name their measured run")
