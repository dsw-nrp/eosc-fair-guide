"""The settings audit reports every difference with where and how to fix it, and its fix only adds."""

import copy
import io
import json
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import audit_repository as audit  # noqa: E402

LIVE = json.loads((Path(__file__).resolve().parent / "fixtures" / "repository-audit.json").read_text(encoding="utf-8"))
REPO = "GET repos/dsw-nrp/eosc-fair-guide"


class Replay:
    """The recorded live state of 24 October 2026; writes are kept and applied to labels and Project items."""

    def __init__(self, responses=None):
        self.responses = copy.deepcopy(responses or LIVE)
        self.writes = []

    def get(self, path, *, pages=False):
        value = self.responses[f"GET {path}"]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)

    def graphql(self, query, variables):
        name = query.split("(")[0].split()[-1]
        if name == "AddItem":
            self.writes.append(("graphql", name, variables))
            number = next(
                issue["number"]
                for issue in self.responses[f"{REPO}/issues?state=open&per_page=100"]
                if issue["node_id"] == variables["content"]
            )
            items = self.responses["GRAPHQL ProjectItems"]["organization"]["projectV2"]["items"]["nodes"]
            items.append({"content": {"number": number, "repository": {"nameWithOwner": "dsw-nrp/eosc-fair-guide"}}})
            return {"addProjectV2ItemById": {"item": {"id": "new"}}}
        value = self.responses[f"GRAPHQL {name}"]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)

    def send(self, method, path, body):
        self.writes.append((method, path, body))
        labels = self.responses[f"{REPO}/labels?per_page=100"]
        if method == "POST":
            labels.append({"name": body["name"], "color": body["color"], "description": body["description"]})
        else:
            name = path.rsplit("/", 1)[-1].replace("%20", " ")
            next(label for label in labels if label["name"] == name).update(body)


def project(responses):
    return responses["GRAPHQL Project"]["organization"]["projectV2"]


def by_setting(findings):
    return {finding.setting: finding for finding in findings}


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.config = audit.load()

    def test_the_committed_state_matches_the_recorded_live_state_but_for_approved_steps(self):
        findings = audit.audit(self.config, Replay())
        statuses = {finding.setting: finding.status for finding in findings}
        strict = "ruleset.Main branch protection.rules.required_status_checks.strict_required_status_checks_policy"
        self.assertEqual(
            statuses,
            {
                strict: "pending",
                "ruleset.Main branch protection.rules.merge_queue": "pending",
                "environment.github-pages.reviewers": "pending",
                "environment.production": "pending",
                "app.permissions": "pending",
                "label.breaking-change": "missing",
                "organization.issue_fields": "unavailable",
            },
        )
        merge_queue = by_setting(findings)["ruleset.Main branch protection.rules.merge_queue"]
        self.assertEqual(
            merge_queue.expected["max_entries_to_merge"], 3, "a missing rule shows its declared parameters"
        )
        self.assertIn("task 4.8", merge_queue.note)

    def test_planted_drift_in_every_section_names_where_and_how(self):
        live = copy.deepcopy(LIVE)
        live[REPO]["allow_auto_merge"] = True
        main = live[f"{REPO}/rulesets/24757722"]
        next(rule for rule in main["rules"] if rule["type"] == "pull_request")["parameters"][
            "required_approving_review_count"
        ] = 0
        live[f"{REPO}/rulesets"].append({"id": 7, "name": "Stray rules"})
        live[f"{REPO}/rulesets/7"] = {**copy.deepcopy(main), "id": 7, "name": "Stray rules"}
        copilot = next(env for env in live[f"{REPO}/environments"]["environments"] if env["name"] == "copilot")
        copilot["can_admins_bypass"] = False
        bug = next(label for label in live[f"{REPO}/labels?per_page=100"] if label["name"] == "bug")
        bug["color"] = "000000"
        live[f"{REPO}/labels?per_page=100"].append({"name": "stray", "color": "ffffff", "description": None})
        board = next(view for view in project(live)["views"]["nodes"] if view["name"] == "Triage")
        board["filter"] = "is:issue"
        next(flow for flow in project(live)["workflows"]["nodes"] if flow["name"] == "Auto-add to project")[
            "enabled"
        ] = False
        status = next(node for node in project(live)["fields"]["nodes"] if node.get("name") == "Status")
        status["options"][0]["name"] = "Inbox"
        items = live["GRAPHQL ProjectItems"]["organization"]["projectV2"]["items"]["nodes"]
        removed = items.pop(0)["content"]["number"]
        open_numbers = {issue["number"] for issue in live[f"{REPO}/issues?state=open&per_page=100"]}
        live["GET orgs/dsw-nrp/issue-types"][0]["is_enabled"] = False
        live["GET apps/fair-guide-actions"]["permissions"]["administration"] = "write"

        findings = by_setting(audit.audit(self.config, Replay(live)))
        expected = {
            "settings.allow_auto_merge": ("drift", "gh api -X PATCH"),
            "ruleset.Main branch protection.rules.pull_request.required_approving_review_count": ("drift", "rulesets/"),
            "ruleset.Stray rules": ("undeclared", ""),
            "environment.copilot.can_admins_bypass": ("drift", "environments/copilot"),
            "label.bug": ("drift", "gh label edit"),
            "label.stray": ("undeclared", ""),
            "project.view.Triage.filter": ("drift", ""),
            "project.workflows.Auto-add to project": ("drift", ""),
            "project.options.Status": ("drift", ""),
            f"organization.issue_types.{LIVE['GET orgs/dsw-nrp/issue-types'][0]['name']}": ("drift", "issue-types"),
            "app.permissions": ("drift", ""),
        }
        if removed in open_numbers:
            expected[f"project.items.#{removed}"] = ("missing", "gh project item-add 1 --owner dsw-nrp")
        for setting, (status, command) in expected.items():
            with self.subTest(setting=setting):
                self.assertEqual(findings[setting].status, status)
                self.assertTrue(findings[setting].ui, "every finding names where to look")
                self.assertTrue(findings[setting].command or findings[setting].note, "and how to act")
                self.assertIn(command, findings[setting].command)
        self.assertEqual(findings["settings.allow_auto_merge"].actual, True)
        self.assertIn("Only the App's owner", findings["app.permissions"].note)

    def test_unreadable_sections_are_unavailable_never_matching(self):
        live = copy.deepcopy(LIVE)
        live["GRAPHQL Project"] = audit.UnavailableError("Resource not accessible by integration")
        live[f"{REPO}/environments"] = audit.UnavailableError("HTTP 403: Must have admin rights")
        findings = by_setting(audit.audit(self.config, Replay(live)))
        self.assertEqual(findings["project"].status, "unavailable")
        self.assertIn("Resource not accessible", findings["project"].note)
        self.assertEqual(findings["environments"].status, "unavailable")
        self.assertNotIn("environment.production", findings, "a pending target in an unreadable section is not judged")
        self.assertEqual(findings["label.breaking-change"].status, "missing", "the rest of the audit still runs")

    def test_bypass_actors_hidden_from_a_read_only_token_are_unavailable_not_drift(self):
        live = copy.deepcopy(LIVE)
        del live[f"{REPO}/rulesets/24757722"]["bypass_actors"]
        findings = by_setting(audit.audit(self.config, Replay(live)))
        bypass = findings["ruleset.Main branch protection.bypass"]
        self.assertEqual(bypass.status, "unavailable")
        self.assertIn("write access to the ruleset", bypass.note)

    def test_a_reached_target_asks_for_its_pending_entry_to_be_removed(self):
        live = copy.deepcopy(LIVE)
        checks = next(
            rule for rule in live[f"{REPO}/rulesets/24757722"]["rules"] if rule["type"] == "required_status_checks"
        )
        checks["parameters"]["strict_required_status_checks_policy"] = False
        setting = "ruleset.Main branch protection.rules.required_status_checks.strict_required_status_checks_policy"
        finding = by_setting(audit.audit(self.config, Replay(live)))[setting]
        self.assertEqual(finding.status, "done")
        self.assertIn("remove this pending entry", finding.note)

    def test_a_pending_target_that_moved_elsewhere_is_drift(self):
        live = copy.deepcopy(LIVE)
        pages = next(env for env in live[f"{REPO}/environments"]["environments"] if env["name"] == "github-pages")
        rule = next(rule for rule in pages["protection_rules"] if rule["type"] == "required_reviewers")
        rule["reviewers"].append({"type": "User", "reviewer": {"login": "someone-else"}})
        finding = by_setting(audit.audit(self.config, Replay(live)))["environment.github-pages.reviewers"]
        self.assertEqual(finding.status, "drift")

    def test_fix_only_creates_or_updates_declared_labels_and_adds_project_items(self):
        live = copy.deepcopy(LIVE)
        live[REPO]["allow_auto_merge"] = True
        next(label for label in live[f"{REPO}/labels?per_page=100"] if label["name"] == "bug")["color"] = "000000"
        live[f"{REPO}/labels?per_page=100"].append({"name": "stray", "color": "ffffff", "description": None})
        status = next(node for node in project(live)["fields"]["nodes"] if node.get("name") == "Status")
        status["options"][0]["name"] = "Inbox"
        items = live["GRAPHQL ProjectItems"]["organization"]["projectV2"]["items"]["nodes"]
        open_numbers = {issue["number"] for issue in live[f"{REPO}/issues?state=open&per_page=100"]}
        removed = next(item for item in items if item["content"]["number"] in open_numbers)
        items.remove(removed)
        replay = Replay(live)
        output = io.StringIO()
        with redirect_stdout(output):
            status_code = audit.main(["--fix"], github=replay)
        kinds = [(write[0], write[1].split("/")[-1] if write[0] != "graphql" else write[1]) for write in replay.writes]
        self.assertEqual(sorted(kinds), [("PATCH", "bug"), ("POST", "labels"), ("graphql", "AddItem")])
        self.assertEqual(
            replay.writes[0][2]["name"] if replay.writes[0][0] == "POST" else "breaking-change", "breaking-change"
        )
        self.assertFalse(
            any(write[0] in ("DELETE", "PUT") for write in replay.writes), "nothing is deleted or replaced"
        )
        after = by_setting(audit.audit(self.config, replay))
        self.assertEqual(after["label.stray"].status, "undeclared", "an undeclared label is never deleted")
        self.assertEqual(after["project.options.Status"].status, "drift", "field values and options are never changed")
        self.assertNotIn("label.bug", after)
        self.assertNotIn(f"project.items.#{removed['content']['number']}", after)
        self.assertEqual(status_code, 1, "the remaining drift still fails the audit")
        self.assertIn("[DRIFT] settings.allow_auto_merge", output.getvalue())

    def test_the_json_report_carries_the_bodies_for_the_commands(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            path = Path(temporary) / "audit.json"
            audit.main(["--json", str(path)], github=Replay())
            report = json.loads(path.read_text(encoding="utf-8"))
        queue = next(item for item in report["findings"] if item["setting"].endswith("rules.merge_queue"))
        rules = {rule["type"]: rule for rule in queue["fix"]["body"]["rules"]}
        self.assertEqual(rules["merge_queue"]["parameters"]["merge_method"], "SQUASH")
        self.assertEqual(
            rules["required_status_checks"]["parameters"]["required_status_checks"], [{"context": "checks"}]
        )


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = audit.load()

    def problems(self, change):
        config = copy.deepcopy(self.config)
        change(config)
        return " ".join(audit.validate(config))

    def test_the_committed_file_is_valid(self):
        self.assertEqual(audit.validate(self.config), [])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(["--check-config"]), 0)

    def test_unknown_sections_and_malformed_values_are_rejected_by_location(self):
        def ruleset(config):
            return config["ruleset"][0]

        cases = {
            "unknown key 'branches'": lambda c: c.update(branches={}),
            "settings: unknown key 'allow_force_push'": lambda c: c["settings"].update(allow_force_push=True),
            "settings.squash_merge_commit_message: malformed value": lambda c: c["settings"].update(
                squash_merge_commit_message="EVERYTHING"
            ),
            "ruleset[0].bypass: malformed value": lambda c: ruleset(c).update(bypass=["Admins always"]),
            "ruleset[0].rules: unknown rule 'protect_everything'": lambda c: ruleset(c)["rules"].update(
                protect_everything={}
            ),
            "branch_policies belong to, and only to, a custom deployment": lambda c: c["environment"]["production"].pop(
                "branch_policies"
            ),
            "color: malformed value": lambda c: c["label"][0].update(color="pink"),
            "label: duplicated name": lambda c: c["label"].append(dict(c["label"][0])),
            "description: longer than": lambda c: c["label"][0].update(description="x" * 101),
            "layout: malformed value": lambda c: c["project"]["view"][0].update(layout="kanban"),
            "sort_by: malformed value": lambda c: c["project"]["view"][0].update(sort_by=["Title upwards"]),
            "app.permissions: expected permission": lambda c: c["app"]["permissions"].update(contents="admin"),
            "is listed twice": lambda c: c["token"].append(dict(c["token"][0])),
            "pending[0]: missing key 'task'": lambda c: c["pending"][0].pop("task"),
            "format: expected 1": lambda c: c.update(format=2),
        }
        for message, change in cases.items():
            with self.subTest(message=message):
                self.assertIn(message, self.problems(change))

    def test_an_invalid_file_stops_before_reading_anything(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "repository.toml"
            path.write_text('format = 1\nrepository = "a/b"\n[[label]]\nname = "x"\ncolor = "red"\n', encoding="utf-8")
            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), unittest.mock.patch("sys.stderr", errors):
                self.assertEqual(audit.main(["--config", str(path)], github=object()), 1)
        self.assertIn("label[0].color: malformed value 'red'", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
