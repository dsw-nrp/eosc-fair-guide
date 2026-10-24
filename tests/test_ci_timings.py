"""Timing reports reproduce a recorded run and keep slot waits apart from the work they delay."""

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ci_timings  # noqa: E402

RUN = Path(__file__).resolve().parent / "fixtures" / "ci-timings" / "40022072478-1"


class RecordedRunTests(unittest.TestCase):
    def setUp(self):
        self.report = ci_timings.analyse(RUN, [3, 4])

    def job(self, name):
        return next(job for job in self.report["jobs"] if job["name"] == name)

    def test_the_reference_run_reproduces_its_measured_critical_path(self):
        self.assertEqual(self.report["critical_path"], ["build", "lanes (browser-b)", "checks"])
        self.assertEqual(self.report["critical_seconds"], 379)
        self.assertEqual(self.report["run"]["elapsed"], 379)
        lane = self.job("lanes (browser-b)")
        # Set-up, checkout, toolchains, both installs and the build download precede 226 s of checks.
        self.assertEqual((lane["queue"], lane["setup"], lane["active"], lane["teardown"]), (3, 71, 226, 7))
        self.assertEqual(self.job("build")["duration"], 20)
        self.assertEqual(self.report["concurrent_peak"], 3)
        self.assertEqual(self.report["queue_seconds"], 14)

    def test_slot_waits_lanes_units_and_coverage_come_from_the_health_artifact(self):
        lanes = self.report["lanes"]
        self.assertEqual(round(lanes["lanes"]["browser-b"]["seconds"]), 226)
        self.assertEqual(lanes["waits"][0]["name"], "en/320")
        self.assertEqual(lanes["waits"][0]["job"], "final-candidate")
        self.assertEqual(round(lanes["waits"][0]["seconds"]), 62)
        unit = self.report["unit"]
        self.assertEqual(unit["tests"], 470)
        self.assertEqual(unit["classes"][0]["name"], "test_health.HealthTests")
        coverage = self.report["coverage"]
        self.assertEqual(coverage["status"], "passed")
        self.assertEqual(coverage["not_passed"], [])
        self.assertEqual(set(coverage["validators"].values()), {"passed"})
        self.assertEqual(coverage["cases"]["passed"], coverage["cases"]["planned"])

    def test_every_suggestion_places_each_browser_job_once_and_is_deterministic(self):
        jobs = self.report["lanes"]["browser_jobs"]
        names = sorted(job["name"] for job in jobs)
        self.assertIn("runtime", names, "the Node runtime tests run in a browser lane without a slot")
        for count in range(1, 6):
            suggestion = ci_timings.suggest(jobs, count, 2)
            self.assertEqual(len(suggestion), count)
            self.assertEqual(sorted(name for lane in suggestion for name in lane["jobs"]), names)
            self.assertEqual(suggestion, ci_timings.suggest(list(reversed(jobs)), count, 2))
            for lane in suggestion:
                placed = [job for job in jobs if job["name"] in lane["jobs"]]
                self.assertEqual(lane["predicted"], ci_timings.predict(placed, 2))
        widest = ci_timings.suggest(jobs, 4, 2)
        self.assertLess(
            max(lane["predicted"] for lane in widest), self.report["lanes"]["lanes"]["browser-b"]["seconds"]
        )

    def test_the_text_report_names_the_path_waits_suggestions_and_coverage(self):
        text = ci_timings.render(self.report)
        self.assertIn("Critical path: build 23 s -> lanes (browser-b) 311 s -> checks 44 s (6 min 19 s).", text)
        self.assertIn("Longest slot waits: en/320 (final-candidate) 62 s", text)
        self.assertIn("Suggested 4 browser lanes:", text)
        self.assertIn("changes only through review", text)
        self.assertIn("validators: crate passed, process-run passed, profile passed", text)


class EstimateTests(unittest.TestCase):
    def test_a_script_wait_is_not_counted_as_its_work(self):
        script = {"file": "check_waiting.mjs", "seconds": 50, "cases": {"script": {"queue_seconds": 40}}}
        self.assertEqual(
            ci_timings.browser_estimate("helpers", 50, [script], 2),
            {"name": "helpers", "estimate": 10, "work": 10},
        )

    def test_cases_share_the_slots_and_scripts_follow_each_other(self):
        cases = [{"name": "one", "seconds": 60, "queue_seconds": 20}, {"name": "two", "seconds": 30}]
        scripts = [{"file": "a.mjs", "seconds": 70, "cases": {"executed": cases}}, {"file": "b.mjs", "seconds": 5}]
        estimate = ci_timings.browser_estimate("page", 75, scripts, 2)
        self.assertEqual(estimate, {"name": "page", "estimate": 45, "work": 75})
        self.assertEqual(
            ci_timings.browser_estimate("runtime", 38, None, 2), {"name": "runtime", "estimate": 38, "work": 0}
        )

    def test_steps_are_classified_by_name(self):
        def step(name, start, end):
            return {
                "name": name,
                "started_at": f"2026-10-23T20:00:{start:02}Z",
                "completed_at": f"2026-10-23T20:00:{end:02}Z",
            }

        job = {
            "name": "quick",
            "conclusion": "success",
            "created_at": "2026-10-23T19:59:58Z",
            "started_at": "2026-10-23T20:00:00Z",
            "completed_at": "2026-10-23T20:00:40Z",
            "steps": [
                step("Set up job", 0, 2),
                step("Run actions/checkout@0123", 2, 4),
                step("Run actions/setup-python@0123", 4, 6),
                step("Install the quick-check tools", 6, 10),
                step("Run the quick checks", 10, 30),
                step("Save the quick result", 30, 35),
                step("Post Run actions/checkout@0123", 35, 36),
                step("Complete job", 36, 37),
                {"name": "Skipped step", "started_at": None, "completed_at": None},
            ],
        }
        self.assertEqual(
            {key: ci_timings.phases(job)[key] for key in ("queue", "setup", "active", "teardown", "duration")},
            {"queue": 2, "setup": 10, "active": 20, "teardown": 7, "duration": 40},
        )


class SourceTests(unittest.TestCase):
    def test_a_run_without_its_health_artifact_still_reports_timings(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name in ("run.json", "jobs.json"):
                shutil.copyfile(RUN / name, directory / name)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(ci_timings.main(["--from", str(directory), "--json", str(directory / "out.json")]), 0)
            self.assertIn("Lane evidence unavailable", output.getvalue())
            self.assertIn("Coverage unavailable: the run has no health report", output.getvalue())
            written = json.loads((directory / "out.json").read_text(encoding="utf-8"))
            self.assertEqual(written["critical_path"], ["build", "lanes (browser-b)", "checks"])

    def test_fetch_reads_one_attempt_and_its_own_health_artifact(self):
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            if command[:2] == ["gh", "api"]:
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"run_attempt": 2}), stderr="")
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="no artifact")

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(ci_timings, "CACHE", Path(temporary)):
            with mock.patch.object(ci_timings.subprocess, "run", side_effect=run), redirect_stdout(io.StringIO()):
                directory = ci_timings.fetch(123, None, "owner/name")
            self.assertEqual(directory, Path(temporary) / "123-2")
        self.assertEqual(calls[0], ["gh", "api", "repos/owner/name/actions/runs/123"])
        self.assertEqual(calls[1][-1], "repos/owner/name/actions/runs/123/attempts/2")
        self.assertEqual(calls[2][-1], "repos/owner/name/actions/runs/123/attempts/2/jobs?per_page=100")
        download = calls[3]
        self.assertEqual(download[:4], ["gh", "run", "download", "123"])
        self.assertEqual(download[download.index("-n") + 1], "health-123-2")
        self.assertEqual(download[download.index("-R") + 1], "owner/name")


if __name__ == "__main__":
    unittest.main()
