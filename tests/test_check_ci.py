"""Partition evidence must fail closed when a lane, job, script, case or build is missing/wrong."""

import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_all  # noqa: E402
import check_ci  # noqa: E402


class PartitionTests(unittest.TestCase):
    def test_citation_metadata_checker_has_one_cpu_owner(self):
        inventory = check_all.jobs(None, False)
        found = [job for job in inventory if job.name == "citation-metadata"]
        self.assertEqual(len(found), 1)
        owners = [lane for lane, jobs in check_ci.partition(inventory).items() if found[0] in jobs]
        self.assertEqual(owners, ["cpu"])
        self.assertIn("scripts/check_citation_metadata.py", found[0].command)

    def fixture(self, root):
        manifest = {
            "source": {"revision": "checked", "files": {"input": "sha"}},
            "build": {"site": "sha"},
            "coverage": {
                "stations": ["station-1", "station-2"],
                "pdfs": ["pdf-1", "pdf-2"],
                "browser_source_digest": "browser-sha",
            },
        }
        jobs = [check_all.Job(name, []) for name in ("content", "page", "final-candidate")]
        groups = {"page": ["page"], "final": ["final_candidate"]}
        for lane, owned in check_ci.partition(jobs).items():
            directory = root / lane
            rows = [
                {"name": job.name, "returncode": 0, "seconds": 1, "output": "retained", "partial": False}
                for job in owned
            ]
            check_ci.write_json(
                directory / "lane.json",
                {"lane": lane, "source": manifest["source"], "build": manifest["build"], "results": rows},
            )
            for job in owned:
                if job.name == "content":
                    continue
                group = "final" if job.name == "final-candidate" else job.name
                name = groups[group][0]
                check_ci.write_json(
                    directory / "details" / group / "scripts.json",
                    {
                        "status": "passed",
                        "scripts": [
                            {
                                "file": f"tests/page/check_{name}.mjs",
                                "status": "passed",
                                "returncode": 0,
                                "cases": {
                                    "status": "passed",
                                    "revision": "checked",
                                    "source_digest": "browser-sha",
                                    "planned": ["case"],
                                    "executed": [{"name": "case", "status": "passed"}],
                                    "skipped": [],
                                    "pending": [],
                                },
                            }
                        ],
                    },
                )
        for filename, key in (("station-coverage.json", "stations"), ("print-coverage.json", "pdfs")):
            check_ci.write_json(
                root / "browser-b/coverage" / filename,
                {
                    "planned": manifest["coverage"][key],
                    "executed": [{"key": key, "status": "passed"} for key in manifest["coverage"][key]],
                    "skipped": [],
                },
            )
        return manifest, jobs, groups

    def test_real_inventory_has_exactly_one_owner_and_retains_all_profiles(self):
        available = check_all.jobs(None, True)
        lanes = check_ci.partition(available)
        names = [job.name for jobs in lanes.values() for job in jobs]
        self.assertEqual(sorted(names), sorted(job.name for job in available if job.name != "live"))
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue({"crate", "process-run", "profile"} <= {job.name for job in lanes["cpu"]})
        self.assertEqual([job.name for job in lanes[check_ci.UNIT_LANE]], ["unit"], "the shards get their own runner")
        self.assertTrue(all(lanes[lane] for lane in check_ci.LANES))

    def test_every_browser_job_has_exactly_one_reviewed_lane(self):
        owned = [job for jobs in check_ci.BROWSER_LANES.values() for job in jobs]
        self.assertEqual(len(owned), len(set(owned)))
        self.assertEqual(set(owned), check_all.BROWSER_JOBS - {"live"})
        self.assertEqual(check_ci.LANES, ("cpu", check_ci.UNIT_LANE, *check_ci.BROWSER_LANES))
        with (
            mock.patch.object(check_all, "BROWSER_JOBS", check_all.BROWSER_JOBS | {"unassigned"}),
            self.assertRaisesRegex(ValueError, "unassigned: browser job without a lane"),
        ):
            check_ci.partition([check_all.Job("unassigned", [])])

    def test_complete_evidence_is_accepted_without_losing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest, jobs, groups = self.fixture(root)
            results, lanes, _, failures = check_ci.reconcile(manifest, root, jobs, groups)
            self.assertEqual(len(results), 3)
            self.assertTrue(all(result.ok and result.output == "retained" for result in results))
            self.assertEqual(failures, [])
            self.assertEqual(set(lanes), set(check_ci.LANES))

    def test_incomplete_or_wrong_evidence_never_becomes_a_complete_pass(self):
        faults = (
            "missing-lane",
            "duplicate-lane",
            "wrong-revision",
            "wrong-build",
            "missing-job",
            "duplicate-job",
            "missing-script",
            "duplicate-script",
            "missing-case-report",
            "wrong-case-revision",
            "wrong-case-source",
            "missing-case",
            "duplicate-case",
            "failed-case",
            "pending-case",
            "missing-station",
            "duplicate-pdf",
            "wrong-inventory",
        )
        for fault in faults:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                manifest, jobs, groups = self.fixture(root)
                lane_path = root / "browser-a/lane.json"
                script_path = root / "browser-a/details/page/scripts.json"
                data = check_ci.read_json(lane_path)
                scripts = check_ci.read_json(script_path)
                case = scripts["scripts"][0]["cases"]
                if fault == "missing-lane":
                    lane_path.unlink()
                elif fault == "duplicate-lane":
                    check_ci.write_json(root / "duplicate/lane.json", data)
                elif fault == "wrong-revision":
                    data["source"]["revision"] = "other"
                elif fault == "wrong-build":
                    data["build"]["site"] = "different"
                elif fault == "missing-job":
                    data["results"] = []
                elif fault == "duplicate-job":
                    data["results"] *= 2
                elif fault == "missing-script":
                    scripts["scripts"] = []
                elif fault == "duplicate-script":
                    scripts["scripts"] *= 2
                elif fault == "missing-case-report":
                    scripts["scripts"][0]["cases"] = None
                elif fault == "wrong-case-revision":
                    case["revision"] = "other"
                elif fault == "wrong-case-source":
                    case["source_digest"] = "other"
                elif fault == "missing-case":
                    case["executed"] = []
                elif fault == "duplicate-case":
                    case["executed"] *= 2
                elif fault == "failed-case":
                    case["executed"][0]["status"] = "failed"
                elif fault == "pending-case":
                    case["pending"] = ["another"]
                else:
                    path = (
                        root
                        / "browser-b/coverage"
                        / ("print-coverage.json" if fault == "duplicate-pdf" else "station-coverage.json")
                    )
                    evidence = check_ci.read_json(path)
                    if fault == "missing-station":
                        evidence["executed"].pop()
                    elif fault == "duplicate-pdf":
                        evidence["executed"].append(copy.deepcopy(evidence["executed"][0]))
                    else:
                        evidence["planned"][0] = "unexpected"
                    check_ci.write_json(path, evidence)
                if fault != "missing-lane":
                    check_ci.write_json(lane_path, data)
                check_ci.write_json(script_path, scripts)
                with self.assertRaises((ValueError, OSError)):
                    check_ci.reconcile(manifest, root, jobs, groups)

    def test_failed_checks_are_returned_together(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest, jobs, groups = self.fixture(root)
            for lane, name in (("cpu", "content"), ("browser-b", "final-candidate")):
                path = root / lane / "lane.json"
                data = check_ci.read_json(path)
                for row in data["results"]:
                    if row["name"] == name:
                        row["returncode"] = 1
                        row["output"] = f"{name} failed"
                check_ci.write_json(path, data)
            results, _, _, failures = check_ci.reconcile(manifest, root, jobs, groups)
            self.assertEqual({result.job.name for result in failures}, {"content", "final-candidate"})
            self.assertEqual(len(results), 3)
            self.assertEqual(sorted(result.job.name for result in failures), ["content", "final-candidate"])

    def fail_content(self, root: Path) -> None:
        path = root / "cpu/lane.json"
        data = check_ci.read_json(path)
        for row in data["results"]:
            if row["name"] == "content":
                row.update(returncode=1, output="content failed: resource `x` lacks a source")
        check_ci.write_json(path, data)

    def test_known_failures_survive_missing_or_rejected_lane_evidence(self) -> None:
        # G4: a failed CPU content check must stay visible when another lane's evidence is unusable.
        for fault in ("missing", "wrong-identity"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                manifest, jobs, groups = self.fixture(root)
                self.fail_content(root)
                lane = root / "browser-a/lane.json"
                if fault == "missing":
                    lane.unlink()
                else:
                    data = check_ci.read_json(lane)
                    data["results"][0]["output"] = "must not be admitted"
                    data["build"] = {"site": "other"}
                    check_ci.write_json(lane, data)
                with self.assertRaises(check_ci.RejectedEvidenceError) as caught:
                    check_ci.reconcile(manifest, root, jobs, groups)
                names = {result.job.name: result for result in caught.exception.results}
                self.assertFalse(names["content"].ok)
                self.assertNotIn("page", names, "a rejected lane contributes no results")
                self.assertIn("browser-a", str(caught.exception))

    def test_collector_reports_the_known_failure_with_the_missing_lane(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incoming = root / "incoming"
            manifest, jobs, groups = self.fixture(incoming)
            manifest["result"] = {"returncode": 0, "seconds": 1, "output": "built"}
            self.fail_content(incoming)
            (incoming / "browser-a/lane.json").unlink()
            check_ci.write_json(root / "manifest.json", manifest)
            real_read = check_ci.read_json
            args = SimpleNamespace(base=None, manifest=root / "manifest.json", incoming=incoming, output=root / "out")
            output = io.StringIO()
            with (
                mock.patch.object(check_ci, "verify_build"),
                mock.patch.object(check_ci.check_all, "jobs", return_value=jobs),
                mock.patch.object(
                    check_ci,
                    "read_json",
                    side_effect=lambda p: groups if p.name == "check_groups.json" else real_read(p),
                ),
                mock.patch.object(check_all, "emit_report") as emit,
                redirect_stdout(output),
            ):
                self.assertEqual(check_ci.collect(args), 1)
            _, results, _, _ = emit.call_args.args
            by_name = {result.job.name: result for result in results}
            self.assertFalse(by_name["content"].ok)
            self.assertIn("lacks a source", by_name["content"].output)
            self.assertIn("missing required lanes: browser-a", by_name["aggregate"].output)
            self.assertFalse(by_name["aggregate"].ok)
            printed = output.getvalue()
            self.assertIn("FAILED content", printed)
            self.assertIn("missing required lanes: browser-a", printed)
            self.assertEqual(check_ci.read_json(root / "pr-review/suggestions.json")["suggestions"], [])

    def test_failed_lane_diagnostics_are_copied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incoming = root / "incoming"
            output = root / "output"
            (incoming / "cpu/logs").mkdir(parents=True)
            (incoming / "cpu/details").mkdir()
            (incoming / "cpu/logs/content.log").write_text("exact failure", encoding="utf-8")
            (incoming / "cpu/details/duplicates.json").write_text("{}", encoding="utf-8")
            check_ci.copy_lane_diagnostics(incoming, output)
            self.assertEqual((output / "logs/content.log").read_text(encoding="utf-8"), "exact failure")
            self.assertEqual((output / "details/duplicates.json").read_text(encoding="utf-8"), "{}")

    def test_suggestions_are_bounded_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "cpu/details").mkdir(parents=True)
            check_ci.write_json(
                root / "cpu/details/duplicates.json",
                {
                    "formatVersion": 1,
                    "suggestions": [
                        {
                            "entry": "resource:service",
                            "record": "re3data:r3d1",
                            "resolution": "link",
                            "safe": True,
                            "file": "content/resources.toml",
                            "table": "resource.repository",
                            "field": "re3data",
                            "value": "r3d1",
                            "reason": "shares address 'example.org/service'",
                        },
                        {
                            "entry": "resource:other",
                            "record": "re3data:r3d2",
                            "safe": True,
                            "file": "outside.toml",
                            "table": "",
                            "field": "re3data",
                            "value": "r3d2",
                            "reason": "unsafe file",
                        },
                    ],
                },
            )
            with mock.patch.dict(check_ci.os.environ, {"GITHUB_REPOSITORY": "dsw-nrp/eosc-fair-guide"}):
                payload = check_ci.load_suggestions(root / "cpu", "a" * 40)
            self.assertEqual(payload["head"], "a" * 40)
            self.assertEqual(payload["repository"], "dsw-nrp/eosc-fair-guide")
            self.assertEqual([item["value"] for item in payload["suggestions"]], ["r3d1"])

    def test_suggestion_summary_is_appended(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "summary.md").write_text("# Summary\n", encoding="utf-8")
            check_ci.append_suggestion_summary(
                output,
                {
                    "suggestions": [
                        {
                            "entry": "resource:service",
                            "record": "re3data:r3d1",
                            "file": "content/resources.toml",
                            "table": "resource.repository",
                            "field": "re3data",
                            "value": "r3d1",
                            "reason": "shares address 'example.org/service'",
                        }
                    ]
                },
            )
            summary = (output / "summary.md").read_text(encoding="utf-8")
            self.assertIn("### Suggested fixes", summary)
            self.assertIn('re3data = "r3d1"', summary)

    def test_collected_suggestions_publish_with_distinct_merge_and_head_shas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            incoming = Path(temporary)
            check_ci.write_json(
                incoming / "cpu/details/duplicates.json",
                {
                    "formatVersion": 1,
                    "suggestions": [
                        {
                            "entry": "resource:service",
                            "record": "re3data:r3d1",
                            "resolution": "link",
                            "safe": True,
                            "file": "content/resources.toml",
                            "table": "resource.repository",
                            "field": "re3data",
                            "value": "r3d1",
                            "reason": "shared URL",
                        }
                    ],
                },
            )
            with mock.patch.dict(
                check_ci.os.environ, {"PR_HEAD_SHA": "a" * 40, "GITHUB_REPOSITORY": "dsw-nrp/eosc-fair-guide"}
            ):
                payload = check_ci.collect_suggestions(incoming / "cpu", {"source": {"revision": "b" * 40}})
            self.assertEqual(payload["head"], "a" * 40)
            self.assertEqual(payload["checkedRevision"], "b" * 40)
            published = subprocess.run(
                [
                    "node",
                    "-e",
                    "const {body}=require('./.github/scripts/comment-summary.cjs');"
                    "const data=JSON.parse(require('node:fs').readFileSync(0,'utf8'));"
                    "process.stdout.write(body({id:1,head_sha:'a'.repeat(40),conclusion:'failure'},"
                    "{formatVersion:1,head:'a'.repeat(40),total:0,items:[]},data.repository,data));",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True,
                cwd=check_ci.ROOT,
            )
            self.assertIn("### Suggested fixes", published.stdout)
            self.assertIn('re3data = "r3d1"', published.stdout)

    def test_site_modification_is_rejected_before_lane_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "_site").mkdir()
            page = root / "_site/index.html"
            page.write_text("checked", encoding="utf-8")
            manifest = {"source": {}, "build": check_ci.build_identity(root)}
            with mock.patch.object(check_ci, "source_identity", return_value={}):
                check_ci.verify_build(manifest, root)
                page.write_text("changed", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "site files"):
                    check_ci.verify_build(manifest, root)

    def test_setup_failure_emits_failed_aggregate_and_blocked_jobs(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = SimpleNamespace(
                base=None, manifest=Path(temporary) / "missing.json", incoming=Path(temporary), output=Path(temporary)
            )
            with mock.patch.object(check_all, "emit_report") as emit:
                self.assertEqual(check_ci.collect(args), 1)
            initial, results, _, _ = emit.call_args.args
            self.assertFalse(initial.ok)
            self.assertFalse(results[0].ok)
            self.assertEqual(results[0].job.name, "aggregate")

    def test_source_identity_covers_working_files_as_well_as_revision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "input").write_text("before", encoding="utf-8")
            with mock.patch.object(
                check_ci.subprocess, "check_output", side_effect=[b"input\0", "head", b"input\0", "head"]
            ):
                before = check_ci.source_identity(root)
                (root / "input").write_text("after", encoding="utf-8")
                after = check_ci.source_identity(root)
            self.assertEqual(before["revision"], after["revision"])
            self.assertNotEqual(before["files"], after["files"])

    def test_collection_reports_build_through_publication_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest, jobs, groups = self.fixture(root)
            manifest.update(started=100, result={"returncode": 0, "seconds": 2, "output": "built"})
            results, lanes, directories, failures = check_ci.reconcile(manifest, root, jobs, groups)
            self.assertEqual(failures, [])
            for lane in lanes.values():
                lane.update(started=110, finished=140)
            args = SimpleNamespace(base=None, manifest=root / "manifest.json", incoming=root, output=root / "out")
            with (
                mock.patch.object(check_ci, "read_json", side_effect=[manifest, groups]),
                mock.patch.object(check_ci, "verify_build"),
                mock.patch.object(check_ci, "reconcile", return_value=(results, lanes, directories, [])),
                mock.patch.object(check_ci.time, "monotonic", return_value=900),
                mock.patch.object(check_ci.time, "time", side_effect=[150, 150, 170]),
                mock.patch.object(check_all, "publish_results", return_value=0) as publish,
                mock.patch.dict(check_ci.os.environ),
            ):
                self.assertEqual(check_ci.collect(args), 0)
            self.assertEqual(publish.call_args.kwargs["start"], 850, "include build/lane time before collection")
            metadata = check_ci.read_json(root / "out/execution.json")
            self.assertEqual(metadata["elapsed_seconds"], 70, "include final health publication")
            self.assertEqual(
                metadata["lane_seconds"], 30 * len(check_ci.LANES), "lane effort remains separate from elapsed time"
            )


class AdoptTests(unittest.TestCase):
    """A staging deployment reuses a merge-queue result only for the same commit, files and build inputs."""

    IDENTITY = {
        "version": "v1.0.0+3",
        "commit": "aaaaaaa",
        "channel": "next",
        "status": "testing",
        "date": "2026-10-24",
    }

    def setUp(self):
        self.manifest = {
            "source": {"revision": "a" * 40, "files": {"content/guide.toml": "1"}},
            "build": {"index.html": "2"},
        }
        self.execution = {
            "profile": "ci-partitioned",
            "source": copy.deepcopy(self.manifest["source"]),
            "build_inputs": dict(self.manifest["build"]),
        }
        self.report = {
            "format_version": check_all.check_health.FORMAT_VERSION,
            "generated_at": "2026-10-24T10:00:00+00:00",
            "revision": "a" * 40,
            "build": dict(self.IDENTITY),
            "run": {"status": "passed", "jobs": []},
        }
        facts = mock.patch.object(
            check_all.check_health.build_crate, "build_identity_facts", return_value=dict(self.IDENTITY)
        )
        facts.start()
        self.addCleanup(facts.stop)

    def test_only_the_same_commit_files_and_build_inputs_are_reused(self):
        self.assertEqual(check_ci.adoption_problems(self.manifest, self.execution, self.report), [])
        cases = {
            "not a partitioned check result": lambda execution, report: execution.update(profile="ci-local"),
            "source revision or files differ": lambda execution, report: execution["source"].update(revision="b"),
            "build inputs differ": lambda execution, report: execution["build_inputs"].update({"index.html": "3"}),
            "has format": lambda execution, report: report.update(format_version=0),
            "did not pass": lambda execution, report: report["run"].update(status="failed"),
            "names another commit": lambda execution, report: report.update(revision="b" * 40),
            "another build identity": lambda execution, report: report["build"].update(date="2026-10-25"),
        }
        for reason, change in cases.items():
            with self.subTest(reason=reason):
                execution, report = copy.deepcopy(self.execution), copy.deepcopy(self.report)
                change(execution, report)
                self.assertIn(reason, " ".join(check_ci.adoption_problems(self.manifest, execution, report)))
        undated = {**self.report, "generated_at": None}
        self.assertIn("its check run did not pass", check_ci.adoption_problems(self.manifest, self.execution, undated))

    def adopt(self, root, *, evidence=True, api_ok=True):
        incoming = root / "incoming"
        if evidence:
            check_ci.write_json(incoming / "execution.json", self.execution)
            check_ci.write_json(incoming / "health.json", self.report)
        check_ci.write_json(root / "manifest.json", self.manifest)
        args = SimpleNamespace(
            manifest=root / "manifest.json", incoming=incoming, source="https://example.test/runs/40"
        )
        validation = check_all.Result(check_all.health_api_job(), 0 if api_ok else 1, 1.0, "health API output")
        printed = io.StringIO()
        with (
            mock.patch.object(check_ci, "verify_build"),
            mock.patch.object(
                check_all.PublicationContext, "load", return_value=check_all.PublicationContext({}, {}, None)
            ),
            mock.patch.object(check_all.build_api, "publish_health") as publish,
            mock.patch.object(check_all, "run", return_value=validation),
            redirect_stdout(printed),
        ):
            status = check_ci.adopt(args)
        return status, printed.getvalue(), publish

    def test_a_matching_result_is_published_into_the_fresh_build_and_validated(self):
        with tempfile.TemporaryDirectory() as temporary:
            status, printed, publish = self.adopt(Path(temporary))
        self.assertEqual(status, 0)
        self.assertIn("Reused https://example.test/runs/40", printed)
        site, report = publish.call_args.args[:2]
        self.assertEqual((site, report), (check_ci.ROOT / "_site", self.report))

    def test_a_missing_mismatched_or_invalid_result_falls_back_and_says_why(self):
        with tempfile.TemporaryDirectory() as temporary:
            status, printed, publish = self.adopt(Path(temporary), evidence=False)
        self.assertEqual(status, 1)
        self.assertIn("Full checks: https://example.test/runs/40 cannot be reused", printed)
        self.assertIn("unavailable or unreadable", printed)
        publish.assert_not_called()
        self.report["revision"] = "b" * 40
        with tempfile.TemporaryDirectory() as temporary:
            status, printed, publish = self.adopt(Path(temporary))
        self.assertEqual(status, 1)
        self.assertIn("names another commit", printed)
        publish.assert_not_called()
        self.report["revision"] = "a" * 40
        with tempfile.TemporaryDirectory() as temporary:
            status, printed, _ = self.adopt(Path(temporary), api_ok=False)
        self.assertEqual(status, 1)
        self.assertIn("fails the health API", printed)


class QuickTests(unittest.TestCase):
    def test_quick_checks_are_the_cpu_lanes_own_jobs_and_need_no_build(self):
        inventory = check_all.jobs("base", False)
        cpu = check_ci.partition(inventory)["cpu"]
        quick = [job for job in inventory if job.name in check_ci.QUICK]
        self.assertEqual(sorted(job.name for job in quick), sorted(check_ci.QUICK))
        for job in quick:
            self.assertIn(job, cpu, f"{job.name}: the required result runs the identical command")
            self.assertFalse(any("_site" in part for part in job.command), f"{job.name} needs no build")

    def run_quick(self, failing: str | None):
        def run(job, env):
            failed = job.name == failing
            return check_all.Result(job, int(failed), 0.5, "advice.fixture cites an unknown clause" if failed else "")

        with tempfile.TemporaryDirectory() as temporary:
            printed = io.StringIO()
            with mock.patch.object(check_all, "run", side_effect=run), redirect_stdout(printed):
                status = check_ci.main(["quick", "--base", "main", "--output", temporary])
            return status, (Path(temporary) / "summary.md").read_text(encoding="utf-8"), printed.getvalue()

    def test_a_quick_failure_names_the_check_its_reproduction_and_the_required_result(self):
        status, summary, printed = self.run_quick("content")
        self.assertEqual(status, 1)
        self.assertIn("| content | failed |", summary)
        self.assertIn("advice.fixture cites an unknown clause", summary)
        self.assertIn("`python scripts/check_all.py --only content`", summary)
        self.assertIn("required `checks` result reports the same failures", summary)
        self.assertIn("FAILED content", printed)

    def test_a_passing_quick_result_points_to_the_required_result(self):
        status, summary, _ = self.run_quick(None)
        self.assertEqual(status, 0)
        self.assertEqual(summary.count("| passed |"), len(check_ci.QUICK))
        self.assertIn("They do not replace the required `checks` result", summary)
        self.assertIn("- **Done when:** `checks` passes.", summary)

    def test_lanes_record_their_dependency_cache_hits(self):
        self.assertEqual(
            check_ci.cache_status({"CHECK_CACHE_PIP": "true", "CHECK_CACHE_NPM": "false"}),
            {"pip": "hit", "npm": "miss"},
        )
        self.assertEqual(
            check_ci.cache_status({"CHECK_CACHE_PIP": "", "CHECK_CACHE_NPM": "true"}), {"pip": "not used", "npm": "hit"}
        )
