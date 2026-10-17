"""Resource scheduling and truthful reporting of nested check selections."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_all  # noqa: E402
from profile_checks import TimedResult  # noqa: E402


class CheckRunnerTests(unittest.TestCase):
    def test_profiles_match_the_node_policy_and_limit_defaults_on_small_machines(self):
        policy = json.loads((check_all.ROOT / "scripts/check_policy.json").read_text(encoding="utf-8"))
        for env, profile in (({}, "local"), ({"CI": "true"}, "ci"), ({"CI": "false"}, "local")):
            self.assertEqual(check_all.execution_defaults(env, 16), {"profile": profile, **policy[profile]})
        self.assertEqual(check_all.execution_defaults({}, 1), {"profile": "local", "jobs": 1, "browser_workers": 1})

    def test_every_child_receives_the_same_global_budget(self):
        jobs = [check_all.Job(name, []) for name in ["page", "model", "content"]]
        env = {"CHECK_BROWSER_WORKERS": "2", "CHECK_BROWSER_SLOT_DIR": "one-run-budget"}

        def run(job, received):
            self.assertEqual(received, env)
            return check_all.Result(job, 0, 0.01, "kept diagnostic")

        with mock.patch.object(check_all, "run", side_effect=run):
            results = check_all.run_all(jobs, 3, env, report=lambda _: None)
        self.assertEqual([result.job for result in results], jobs)

    def test_successful_selected_browser_cases_make_the_full_run_partial(self):
        job = check_all.Job("page", [])
        build = check_all.Result(check_all.Job("build", []), 0, 0.01, "build diagnostic")
        result = check_all.Result(job, 0, 0.01, "selected cases only", partial=True)
        with mock.patch.object(check_all.check_health, "write_report") as write:
            check_all.emit_report(build, [result], [job], [job], output=Path("unused"), previous=None)
        run = write.call_args.args[0]["run"]
        self.assertEqual(run["status"], "partial")
        self.assertEqual(run["jobs"][1]["output"], "selected cases only")
        self.assertTrue(run["jobs"][1]["partial"])

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
