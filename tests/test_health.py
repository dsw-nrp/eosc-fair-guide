"""Health inventories expose omissions and broken records without claiming online availability."""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import date
from hashlib import sha256
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_api  # noqa: E402
import build_crate  # noqa: E402
import check_all  # noqa: E402
import check_health  # noqa: E402

TODAY = date(2026, 10, 11)


class HealthTests(unittest.TestCase):
    def test_link_decisions_expire_on_text_target_or_location_changes(self) -> None:
        candidates = check_health.missing_links(self.content)
        row = candidates[0]
        decision = {
            "path": row["path"],
            "address": row["address"],
            "sha256": sha256(row["text"].encode("utf-8")).hexdigest(),
            "reason": "This occurrence describes context rather than a navigation instruction.",
            "reviewed": "2026-10-16",
        }
        content = {"link_reviews": [decision]}
        reviewed = check_health.review_links(content, [row])
        self.assertFalse(reviewed["pending"])
        self.assertEqual(len(reviewed["reviewed"]), 1)
        self.assertFalse(reviewed["stale"])
        for field, replacement in [
            ("text", row["text"] + " Changed context."),
            ("address", "res/tool/github"),
            ("path", "pages[new].body.en"),
        ]:
            with self.subTest(field=field):
                changed = {**row, field: replacement}
                result = check_health.review_links(content, [changed])
                self.assertEqual(result["pending"], [changed])
                self.assertFalse(result["reviewed"])
                self.assertEqual(len(result["stale"]), 1)
        new = {**row, "path": "pages[new].body.en"}
        self.assertEqual(check_health.review_links(content, [row, new])["pending"], [new])

    def test_invalid_or_duplicate_link_decisions_fail_without_a_blanket_exemption(self) -> None:
        content = copy.deepcopy(self.content)
        row = check_health.missing_links(content)[0]
        decision = {
            "path": row["path"],
            "address": row["address"],
            "sha256": sha256(row["text"].encode("utf-8")).hexdigest(),
            "reason": "Reviewed context.",
            "reviewed": "2026-10-16",
        }
        for field, invalid in [
            ("path", "*"),
            ("address", "term/*"),
            ("reason", ""),
            ("sha256", ""),
            ("reviewed", "not a date"),
        ]:
            content["link_reviews"] = [{**decision, field: invalid}]
            report = self.report(content)
            group = next(group for group in report["integrity"] if group["type"] == "link review decisions")
            self.assertEqual(group["failed"], 1)
            self.assertIn(row, report["missing_links"])
        content["link_reviews"] = [decision, decision]
        self.assertTrue(check_health.review_links(content, [row])["issues"])

    def test_reviewed_links_remain_visible_with_reasons_in_dashboard_and_json(self) -> None:
        report = self.report()
        self.assertTrue(report["missing_link_review"]["reviewed"])
        page = check_health.dashboard(report)
        self.assertIn("Reviewed unlinked mentions:", page)
        self.assertIn("Stale link decisions requiring review:", page)
        self.assertIn("Reviewed unlinked mentions:", check_health.markdown(report))
        row = report["missing_link_review"]["reviewed"][0]
        row["review_reason"] = '<script>alert("review")</script>'
        page = check_health.dashboard(report)
        self.assertNotIn(row["review_reason"], page)
        self.assertIn("&lt;script&gt;", page)

    def test_advisory_does_not_treat_generic_metadata_as_names_or_relink_external_callouts(self) -> None:
        content = copy.deepcopy(self.content)
        page = next(row for row in content["pages"] if row["id"] == "software")
        section = next(row for row in page["section"] if row["id"] == "version")
        section["body"] = {
            "en": "Record the version, title, API and rights; NRP is not a named FIP here. Use Docker.",
            "cs": "Zapište verze, název a práva; NRP zde není název FIP. Použijte Docker.",
        }
        hints = check_health.missing_links(content)
        scoped = [row for row in hints if "[version]" in row["path"]]
        self.assertTrue(any(row["match"] == "Docker" for row in scoped))
        self.assertFalse(
            any(
                row["match"].casefold() in {"version", "title", "api", "rights", "nrp", "verze", "název", "práva"}
                for row in scoped
            )
        )
        self.assertFalse(any("callouts[sensitive-data].item[aai].text" in row["path"] for row in hints))

    def test_advisory_prefers_specific_reviewed_phrases_and_explains_ambiguity(self) -> None:
        content = copy.deepcopy(self.content)
        github = next(
            row
            for row in next(
                snapshot
                for snapshot in content["snapshots"]
                if snapshot["snapshot"]["source"] == "KNAV Data Management Tools Catalogue"
            )["tool"]
            if row["id"] == "github"
        )
        github["linkNames"] = {"en": ["Specific Research Hub", "Shared Portal"], "cs": ["GitHubu"]}
        gitlab = next(
            row
            for row in next(
                snapshot
                for snapshot in content["snapshots"]
                if snapshot["snapshot"]["source"] == "KNAV Data Management Tools Catalogue"
            )["tool"]
            if row["id"] == "gitlab"
        )
        gitlab["linkNames"] = {"en": ["Research Hub", "Shared Portal"]}
        page = next(row for row in content["pages"] if row["id"] == "software")
        section = next(row for row in page["section"] if row["id"] == "version")
        section["body"] = {
            "en": "Use Specific Research Hub and Shared Portal; data, metadata, repository and planning are generic.",
            "cs": "Použijte GitHubu.",
        }
        hints = [row for row in check_health.missing_links(content) if "[version]" in row["path"]]
        self.assertTrue(any(row["match"] == "Specific Research Hub" and row["confidence"] == "high" for row in hints))
        self.assertFalse(any(row["match"] == "Research Hub" for row in hints))
        ambiguous = next(row for row in hints if row["match"] == "Shared Portal")
        self.assertEqual(ambiguous["confidence"], "review")
        self.assertIn("ambiguous", ambiguous["reason"])
        self.assertTrue(any(row["match"] == "GitHubu" for row in hints))
        self.assertFalse(
            any(row["match"].casefold() in {"data", "metadata", "repository", "planning"} for row in hints)
        )
        self.assertTrue(all(row["excerpt"] and row["reference"].startswith("[[") and row["reason"] for row in hints))

    def test_missing_link_advisory_names_text_entry_and_language_without_failing(self) -> None:
        content = copy.deepcopy(self.content)
        page = next(page for page in content["pages"] if page["id"] == "software")
        section = next(section for section in page["section"] if section["id"] == "version")
        section["body"] = {"cs": "Použijte GitHub.", "en": "Use GitHub; GitHubby is another word."}
        unlinked = check_health.missing_links(content)
        matches = [
            item
            for item in unlinked
            if "[software]" in item["path"] and "[version]" in item["path"] and item["entry"] == "#knav-github"
        ]
        self.assertEqual({item["language"] for item in matches}, {"cs", "en"})
        self.assertTrue(all(item["address"] == "res/tool/github" for item in matches))
        section["body"] = {"cs": "Použijte [[res/tool/github|GitHub]].", "en": "Use [[res/tool/github|GitHub]]."}
        linked = check_health.missing_links(content)
        self.assertFalse(
            any(
                item["entry"] == "#knav-github" and "[software]" in item["path"] and "[version]" in item["path"]
                for item in linked
            )
        )
        section["body"] = {"cs": "GitHubby", "en": "GitHubby"}
        self.assertFalse(
            any(
                item["entry"] == "#knav-github" and "[version]" in item["path"]
                for item in check_health.missing_links(content)
            )
        )
        report = self.report(content)
        self.assertEqual(report["integrity_failed"], self.report(self.content)["integrity_failed"])
        self.assertIn("Possible missing links (advisory)", check_health.dashboard(report))
        self.assertIn("non-blocking", check_health.markdown(report))

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = build_crate.load_content(ROOT / "content")

    def report(self, content=None, **kwargs) -> dict:
        return check_health.make_report(content or self.content, today=TODAY, **kwargs)

    def test_summary_renders_every_failed_check_output(self) -> None:
        report = self.report()
        report["run"] = {
            "status": "failed",
            "reason": "",
            "jobs": [
                {"name": "content", "status": "failed", "seconds": 1, "output": "error: content failed"},
                {"name": "duplicates", "status": "failed", "seconds": 1, "output": "error: duplicates failed"},
                {"name": "crate", "status": "passed", "seconds": 1, "output": "ok"},
            ],
        }
        summary = check_health.markdown(report)
        self.assertIn("### Failed check output", summary)
        self.assertIn("#### content", summary)
        self.assertIn("#### duplicates", summary)
        self.assertIn("error: content failed", summary)
        self.assertNotIn("#### crate", summary)

    def test_checked_revision_can_differ_from_the_workflow_trigger(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_SHA": "a" * 40, "FAIR_GUIDE_CHECK_REVISION": "b" * 40}, clear=True):
            self.assertEqual(self.report()["revision"], "b" * 40)
        with mock.patch.dict(os.environ, {"GITHUB_SHA": "a" * 40}, clear=True):
            self.assertEqual(self.report()["revision"], "a" * 40)

    def test_inventory_covers_each_advice_question_and_clause(self) -> None:
        coverage = check_health.original_coverage(self.content)
        expected_advice = {item["id"] for parent in self.content["stations"] for item in parent["advice"]}
        expected_questions = {item["id"] for parent in self.content["checks"] for item in parent["item"]}
        self.assertEqual({item["id"] for item in coverage["advice"]}, expected_advice)
        self.assertEqual({item["id"] for item in coverage["questions"]}, expected_questions)
        self.assertEqual(len(coverage["clauses"]), len(self.content["ledger"]))
        self.assertEqual(
            coverage, check_health.original_coverage(self.content), "inventory order must be deterministic"
        )

    def test_question_omissions_are_reviewed_without_implicitly_excusing_advice(self) -> None:
        coverage = check_health.original_coverage(self.content)
        omissions = {item["id"]: item for item in coverage["questions"] if not item["originals"]}
        self.assertEqual(set(omissions), set(check_health.REVIEWED_SOURCE_LINK_BASIS))
        self.assertTrue(all(item["status"] == "reviewed_source_links" for item in omissions.values()))
        missing_advice = [item for item in coverage["advice"] if not item["originals"]]
        self.assertTrue(missing_advice)
        self.assertTrue(all(item["status"] == "no_original" and not item["reviewed_basis"] for item in missing_advice))

    def test_removing_an_original_exposes_exact_clause_and_affected_items(self) -> None:
        before = self.report()
        content = copy.deepcopy(self.content)
        clause = next(item for item in content["ledger"] if item["id"] == "OPENSSF.01")
        clause.pop("guidance")
        after = self.report(content, previous=before)
        record = next(item for item in after["original_coverage"]["clauses"] if item["id"] == "OPENSSF.01")
        self.assertFalse(record["has_original"])
        source = next(item for item in after["original_coverage"]["by_source"] if item["id"] == clause["source"])
        self.assertIn("software.20", source["questions_without_original"])
        self.assertEqual(after["trend"]["coverage"]["clauses"]["with_original_delta"], -1)
        self.assertIn("OPENSSF.01", after["trend"]["coverage"]["clauses"]["new_missing"])
        question = next(item for item in after["original_coverage"]["questions"] if item["id"] == "software.20")
        self.assertEqual(question["status"], "no_original")

    def test_partial_coverage_does_not_disappear_behind_one_original(self) -> None:
        coverage = check_health.original_coverage(self.content)
        advice = next(item for item in coverage["advice"] if item["id"] == "plan.01")
        self.assertEqual(advice["status"], "partial")
        self.assertIn("DSW-NRP.01", advice["missing_originals"])
        self.assertIn("A.K2.3.1", advice["originals"])
        source = next(item for item in coverage["by_source"] if item["id"] == "dsw-nrp")
        self.assertIn("plan.01", source["advice_with_other_original"])
        self.assertNotIn("plan.01", source["advice_without_original"])

    def test_clause_roles_versions_and_languages_remain_source_facts(self) -> None:
        coverage = check_health.original_coverage(self.content)
        clause = next(item for item in coverage["clauses"] if item["id"] == "FDO.FDO-GR9")
        self.assertEqual(clause["source_version"], "3.0")
        self.assertEqual(clause["original_language"], "en")
        self.assertTrue(clause["locator"])
        self.assertTrue(clause["kind"])
        self.assertTrue(clause["source_url"].startswith("https://"))

    def test_broken_reference_missing_translation_and_future_status_fail_by_type(self) -> None:
        content = copy.deepcopy(self.content)
        advice = content["stations"][0]["advice"][0]
        advice["sources"] = ["UNKNOWN.01"]
        resource = content["resources"][0]
        resource["description"].pop("en")
        resource["asOf"] = date(2099, 1, 1)
        report = self.report(content)
        groups = {group["type"]: group for group in report["integrity"]}
        finding = next(item for item in groups["station advice"]["items"] if item["id"] == advice["id"])
        self.assertIn("published-clause citations resolve", finding["issues"])
        finding = next(
            item for item in groups["resources: " + resource["type"]]["items"] if item["id"] == resource["id"]
        )
        self.assertIn("bilingual purpose", finding["issues"])
        self.assertIn("dated status is valid and not in the future", finding["issues"])

    def test_champion_invocation_endpoint_uses_the_provider_identifier(self) -> None:
        content = copy.deepcopy(self.content)
        champion = content["live"]["champion"]
        tests = {test["id"]: test for test in champion["test"]}
        expected = champion["endpoint"].rstrip("/") + "/fc_metadata_identifier_persistence"
        self.assertEqual(build_crate.champion_endpoint(champion, tests["fc-metadata-pid"]), expected)
        # Without a provider ID or an endpoint of its own, no invocation URL exists, so none is assumed.
        tests["fc-data-id-metadata"]["alternateIds"] = []
        groups = {group["type"]: group for group in check_health.integrity(content, ROOT, TODAY)}
        issues = {item["id"]: item["issues"] for item in groups["remote automated tests"]["items"]}
        self.assertIn("HTTPS invocation endpoint", issues["fc-data-id-metadata"])
        self.assertNotIn("HTTPS invocation endpoint", issues["fc-metadata-pid"])
        self.assertNotIn("HTTPS invocation endpoint", issues["community-data-citation"], "its own endpoint")

    def test_no_network_probe_or_current_status_is_inferred(self) -> None:
        report = self.report()
        self.assertEqual(report["live_availability"]["status"], "unchecked")
        connectors = next(group for group in report["integrity"] if group["type"] == "connectors")
        fip = next(item for item in connectors["items"] if item["id"] == "fip-dashboard")
        self.assertIn("Browser access is explicitly disabled.", fip["notes"])
        self.assertEqual(report["run"]["status"], "not_run")
        self.assertFalse(report["trend"]["available"])

    def test_custom_test_record_catches_missing_or_escaping_attachments(self) -> None:
        content = copy.deepcopy(self.content)
        content["live"]["test"] = [
            {
                "id": "guide-test",
                "question": "software.01",
                "label": {"cs": "Test", "en": "Test"},
                "description": {"cs": "Popis", "en": "Description"},
                "script": "../eosc-fair-guide/assets/js/assess.js",
                "documentation": "missing.html#test",
                "entryPoint": "",
            }
        ]
        groups = check_health.integrity(content, ROOT, TODAY)
        test = next(group for group in groups if group["type"] == "guide automated tests")["items"][0]
        # A normal file attachment is accepted; a nonexistent document and unnamed call are not.
        self.assertNotIn("JavaScript implementation attachment exists", test["issues"])
        self.assertIn("documentation attachment exists", test["issues"])
        self.assertIn("named invocation exists", test["issues"])
        self.assertFalse(check_health.local_file(ROOT, "../another-repository/AGENTS.md"))
        self.assertFalse(check_health.local_file(ROOT, "https://example.org/test.js"))

    def test_deleting_an_item_is_not_reported_as_fixing_its_missing_original(self) -> None:
        before = self.report()
        content = copy.deepcopy(self.content)
        parent = next(item for item in content["checks"] if item["check"]["id"] == "dataset")
        parent["item"] = [item for item in parent["item"] if item["id"] != "dataset.19"]
        after = self.report(content, previous=before)
        trend = after["trend"]["coverage"]["questions"]
        self.assertIn("dataset.19", trend["removed_items"])
        self.assertNotIn("dataset.19", trend["resolved_missing"])

    def test_report_artifacts_escape_external_text_and_keep_failures_readable(self) -> None:
        report = self.report()
        report["run"] = {
            "status": "failed",
            "jobs": [{"name": "broken", "status": "failed", "seconds": 1, "output": '<script>alert("x")</script>'}],
        }
        page = check_health.dashboard(report)
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("failure output", page)
        self.assertIn("dataset.19", page)
        self.assertIn("Not classified as a deliberate omission", page)
        self.assertEqual(check_health.anchor("javascript:alert(1)", "unsafe"), "unsafe")
        with tempfile.TemporaryDirectory() as temp:
            check_health.write_report(report, Path(temp))
            saved = json.loads((Path(temp) / "health.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["original_coverage"], report["original_coverage"])
            self.assertIn("failed", (Path(temp) / "summary.md").read_text(encoding="utf-8"))

    def test_unreadable_content_still_produces_a_dashboard(self) -> None:
        report = check_health.unreadable_report("invalid TOML", {"status": "failed", "jobs": []})
        self.assertIn("invalid TOML", check_health.dashboard(report))
        self.assertIn("failed", check_health.markdown(report))
        self.assertFalse(report["original_coverage"]["counts"])

    def test_report_records_partial_blocked_optional_and_failed_jobs(self) -> None:
        jobs = [check_all.Job("content", []), check_all.Job("unit", []), check_all.Job("live", [])]
        build = check_all.Result(check_all.Job("build", []), 0, 1, "")
        result = check_all.Result(jobs[0], 3, 0.5, "broken citation")
        with mock.patch.object(check_health, "write_report") as write:
            check_all.emit_report(build, [result], jobs, [jobs[0]], output=Path("unused"), previous=None)
            report = write.call_args.args[0]
        recorded = {item["name"]: item for item in report["run"]["jobs"]}
        self.assertEqual(report["run"]["status"], "failed")
        self.assertEqual(recorded["content"]["output"], "broken citation")
        self.assertEqual(recorded["unit"]["status"], "not_run")
        self.assertEqual(recorded["live"]["status"], "not_run")
        failed_build = check_all.Result(build.job, 1, 1, "build failed")
        with mock.patch.object(check_health, "write_report") as write:
            check_all.emit_report(failed_build, [], jobs, jobs[:2], output=Path("unused"), previous=None)
            recorded = {item["name"]: item for item in write.call_args.args[0]["run"]["jobs"]}
        self.assertEqual(recorded["content"]["status"], "blocked")
        self.assertEqual(recorded["live"]["status"], "not_run")

    def test_optional_unrun_live_job_does_not_mark_completed_offline_suite_partial(self) -> None:
        jobs = [check_all.Job("health", []), check_all.Job("live", [])]
        build = check_all.Result(check_all.Job("build", []), 0, 1, "")
        result = check_all.Result(jobs[0], 0, 0.5, "")
        with mock.patch.object(check_health, "write_report") as write:
            check_all.emit_report(build, [result], jobs, jobs[:1], output=Path("unused"), previous=None)
        self.assertEqual(write.call_args.args[0]["run"]["status"], "passed")

    def test_main_emits_diagnostics_before_returning_from_a_failed_build(self) -> None:
        failure = check_all.Result(check_all.Job("build", []), 1, 0.1, "broken build")
        with (
            mock.patch.object(check_all, "run", return_value=failure),
            mock.patch.object(check_all, "emit_report") as emit,
        ):
            self.assertEqual(check_all.main(["--only", "health"]), 1)
        self.assertEqual(emit.call_args.args[1], [])

    def test_missing_trend_baseline_does_not_erase_current_inventory(self) -> None:
        job = check_all.Job("health", [])
        build = check_all.Result(check_all.Job("build", []), 0, 0.1, "")
        result = check_all.Result(job, 0, 0.1, "")
        with (
            mock.patch.object(check_health, "read_previous", side_effect=OSError("missing baseline")),
            mock.patch.object(check_health, "write_report") as write,
        ):
            check_all.emit_report(build, [result], [job], [job], output=Path("unused"), previous=Path("missing"))
        report = write.call_args.args[0]
        self.assertTrue(report["original_coverage"]["counts"])
        self.assertIn("missing baseline", report["trend"]["reason"])
        self.assertFalse(report["trend"]["available"])

    def test_api_build_inventory_is_deterministic_without_a_completed_run_claim(self) -> None:
        api = build_api.Api(build_crate.build_crate(self.content), self.content)
        first = api.health()
        second = api.health()
        self.assertEqual(first, second)
        self.assertIsNone(first["generated_at"])
        self.assertEqual(first["run"]["status"], "not_run")
        self.assertEqual(first["run"]["jobs"], [])
        self.assertNotIn("@context", first)
        self.assertIn("health.json", api.meta()["hasPart"])
        description = json.loads(api.files()[build_api.OPENAPI_FILE])
        self.assertEqual(description["paths"]["/api/health.json"]["get"]["operationId"], "getHealth")
        self.assertEqual(
            description["components"]["schemas"]["HealthRun"]["properties"]["status"]["enum"],
            ["not_run", "passed", "partial", "failed"],
        )

    def test_api_health_links_questions_clauses_and_station_advice_without_mutating_report(self) -> None:
        report = self.report(run={"status": "passed", "jobs": []})
        original = copy.deepcopy(report)
        api = build_api.Api(build_crate.build_crate(self.content), self.content)
        linked = api.health(report)
        coverage = linked["original_coverage"]
        self.assertEqual(
            next(item for item in coverage["questions"] if item["id"] == "software.20")["api_record"],
            "q/software.20.json",
        )
        self.assertEqual(
            next(item for item in coverage["clauses"] if item["id"] == "OPENSSF.01")["api_record"],
            "cl/OPENSSF.01.json",
        )
        self.assertEqual(
            next(item for item in coverage["advice"] if item["id"] == "plan.01")["api_record"],
            "step/plan.json#advice-plan.01",
        )
        self.assertEqual(linked["generated_at"], report["generated_at"])
        self.assertEqual(report, original)

    def test_automated_api_test_embeds_documentation_with_site_relative_urls(self) -> None:
        api = build_api.Api(build_crate.build_crate(self.content), self.content)
        test = next(item for item in self.content["live"]["test"] if item["id"] == "guide-cdif-01")
        record = api.record("tests", test["id"], "#test-" + test["id"])
        self.assertEqual(record["url"], "../../../" + test["script"])
        self.assertIsInstance(record["subjectOf"], dict)
        self.assertEqual(record["subjectOf"]["url"], "../../../" + test["documentation"])
        self.assertEqual(record["subjectOf"]["isPartOf"], "../../../" + test["documentation"].split("#")[0])

    def test_failed_build_leaves_existing_site_health_bytes_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp) / "site"
            (site / "api").mkdir(parents=True)
            health = site / build_api.HEALTH_FILE
            health.write_text("old site health", encoding="utf-8")
            dashboard = site / "health" / "index.html"
            dashboard.parent.mkdir()
            dashboard.write_text("old site dashboard", encoding="utf-8")
            (site / build_api.OPENAPI_FILE).write_text("{}", encoding="utf-8")
            failed = check_all.Result(check_all.Job("build", []), 1, 0.1, "broken")
            with mock.patch("builtins.print"):
                check_all.emit_report(failed, [], [], [], output=Path(temp) / "report", previous=None, site=site)
            self.assertEqual(health.read_text(encoding="utf-8"), "old site health")
            self.assertEqual(dashboard.read_text(encoding="utf-8"), "old site dashboard")
            self.assertTrue((Path(temp) / "report" / "health.json").is_file())

    def test_successful_run_publication_replaces_build_snapshot_with_actual_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp) / "site"
            (site / "api").mkdir(parents=True)
            build_crate.mark_site(site)
            (site / build_api.HEALTH_FILE).write_text("{}", encoding="utf-8")
            (site / build_api.OPENAPI_FILE).write_text("{}", encoding="utf-8")
            job = check_all.Job("api", [])
            build = check_all.Result(check_all.Job("build", []), 0, 0.1, "")
            failure = check_all.Result(job, 1, 0.2, "bad schema")
            with mock.patch("builtins.print"):
                check_all.emit_report(
                    build, [failure], [job], [job], output=Path(temp) / "report", previous=None, site=site
                )
            published = json.loads((site / build_api.HEALTH_FILE).read_text(encoding="utf-8"))
            self.assertEqual(published["run"]["status"], "failed")
            self.assertTrue(published["generated_at"])
            self.assertEqual(published["run"]["jobs"][1]["output"], "bad schema")
            self.assertTrue(published["original_coverage"]["advice"][0].get("api_record"))
            dashboard = (site / "health" / "index.html").read_text(encoding="utf-8")
            self.assertIn(published["generated_at"], dashboard)
            self.assertIn("bad schema", dashboard)
            self.assertIn('href="../api/health.json"', dashboard)
            self.assertIn('href="../index.html"', dashboard)
            self.assertIn("failed", (site / "health" / "summary.md").read_text(encoding="utf-8"))

    def test_site_dashboard_for_a_plain_build_preserves_the_unchecked_state(self) -> None:
        api = build_api.Api(build_crate.build_crate(self.content), self.content)
        report = api.health()
        with tempfile.TemporaryDirectory() as temp:
            check_health.write_site_dashboard(report, Path(temp))
            dashboard = (Path(temp) / "health" / "index.html").read_text(encoding="utf-8")
            self.assertIn("No completed check run", dashboard)
            self.assertIn("not_run", dashboard)
            self.assertNotIn("Generated: None", dashboard)
            self.assertFalse((Path(temp) / "health" / "health.json").exists())

    def test_dashboard_and_summary_read_revision_scope_recorded_status_and_live_availability(self) -> None:
        report = check_health.make_report(self.content, today=date(2026, 10, 12))
        report["revision"] = "a" * 40
        report["run_url"] = "https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/7"
        page = check_health.dashboard(report)
        self.assertIn('href="https://github.com/dsw-nrp/eosc-fair-guide/commit/' + "a" * 40 + '"', page)
        self.assertIn("the scheduled live watch observes it separately", page)
        self.assertIn("Guide structure only; no live service is involved.", page)
        dated = next(
            item
            for group in report["integrity"]
            for item in group["items"]
            if item.get("recorded_status") and item.get("recorded_date")
        )
        self.assertIn(check_health.esc(f"{dated['recorded_status']} as of {dated['recorded_date']}"), page)
        summary = check_health.markdown(report)
        self.assertIn("Revision: `" + "a" * 12 + "`", summary)
        self.assertIn(f"Item groups without a live check: {check_health.unchecked_groups(report)}", summary)
        local = check_health.dashboard(report | {"revision": None, "run_url": None})
        self.assertIn("not recorded (a local build)", local)

    def test_api_publication_refuses_a_directory_without_a_built_api(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(build_crate.ContentError):
                build_api.publish_health(Path(temp), self.report(), self.content)
            self.assertFalse((Path(temp) / "api").exists())

    def test_api_publication_refuses_an_api_the_build_did_not_make(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp)
            (site / "api").mkdir()
            (site / build_api.HEALTH_FILE).write_text("authored", encoding="utf-8")
            (site / build_api.OPENAPI_FILE).write_text("{}", encoding="utf-8")
            with self.assertRaises(build_crate.UnsafeOutputError):
                build_api.publish_health(site, self.report(), self.content)
            self.assertEqual((site / build_api.HEALTH_FILE).read_text(encoding="utf-8"), "authored")
            self.assertFalse((site / "health").exists())

    def test_publication_reuses_one_content_and_crate_for_success_and_failure(self) -> None:
        for final_code in (0, 7):
            with self.subTest(final_code=final_code):
                job = check_all.health_api_job()
                build = check_all.Result(check_all.Job("build", []), 0, 0.1, "")
                candidate = check_all.Result(job, 0, 0.1, "")
                final = check_all.Result(job, final_code, 0.1, "final result")
                with (
                    mock.patch.object(build_crate, "load_content", wraps=build_crate.load_content) as parse,
                    mock.patch.object(build_crate, "build_crate", wraps=build_crate.build_crate) as construct,
                    mock.patch.object(check_health, "write_report") as write,
                    mock.patch.object(build_api, "publish_health") as publish,
                    mock.patch.object(check_all, "run", side_effect=[candidate, final]),
                    mock.patch("builtins.print"),
                ):
                    result = check_all.publish_results(
                        build, [], [job], [job], env={}, output=Path("unused"), previous=None, start=time.monotonic()
                    )
                self.assertEqual(result, int(bool(final_code)))
                self.assertEqual(parse.call_count, 1)
                self.assertEqual(construct.call_count, 1)
                reports = [call.args[0] for call in write.call_args_list]
                self.assertEqual(len(reports), 3 if final_code else 2)
                self.assertEqual(reports[0]["run"]["status"], "partial")
                self.assertEqual(reports[-1]["run"]["status"], "failed" if final_code else "passed")
                crates = [call.kwargs["crate"] for call in publish.call_args_list]
                self.assertTrue(all(crate is crates[0] for crate in crates))

    def test_final_api_validation_failure_is_retained_and_fails_the_runner(self) -> None:
        build = check_all.Result(check_all.Job("build", []), 0, 0.1, "")
        health = check_all.Result(check_all.Job("health", []), 0, 0.1, "")
        candidate = check_all.Result(check_all.Job("health-api", []), 0, 0.1, "")
        final = check_all.Result(candidate.job, 7, 0.2, "invalid final health")
        with (
            mock.patch.object(check_all, "run", side_effect=[build, candidate, final]),
            mock.patch.object(check_all, "run_all", return_value=[health]),
            mock.patch.object(check_all, "emit_report") as emit,
            mock.patch("builtins.print"),
        ):
            self.assertEqual(check_all.main(["--only", "health", "health-api"]), 1)
        failure = emit.call_args.args[1][-1]
        self.assertEqual(failure.returncode, 7)
        self.assertIn("invalid final health", failure.output)


if __name__ == "__main__":
    unittest.main()
