"""The settings audit reports every difference with where and how to fix it, and its fix only adds."""

import copy
import io
import json
import shlex
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
        self.assertEqual(findings["environments"].ui, "Settings → Environments", "a section path names no object")
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
        bodies = {item["setting"]: item["fix"]["body"] for item in report["findings"] if item["fix"]}
        queue = {rule["type"]: rule for rule in bodies["ruleset.Main branch protection.rules.merge_queue"]["rules"]}
        self.assertEqual(queue["merge_queue"]["parameters"]["merge_method"], "SQUASH")
        checks = queue["required_status_checks"]["parameters"]
        self.assertEqual(checks["required_status_checks"], [{"context": "checks", "integration_id": 15368}])
        self.assertIs(checks["strict_required_status_checks_policy"], True, "the other pending target stays live")
        pull = queue["pull_request"]["parameters"]
        self.assertIs(pull["require_extra_approval_for_unattributed_changes"], True, "no live parameter is dropped")
        strict = "ruleset.Main branch protection.rules.required_status_checks.strict_required_status_checks_policy"
        self.assertNotIn("merge_queue", {rule["type"] for rule in bodies[strict]["rules"]})

    def test_a_command_for_another_difference_never_applies_a_pending_target(self):
        live = copy.deepcopy(LIVE)
        main = live[f"{REPO}/rulesets/24757722"]
        next(rule for rule in main["rules"] if rule["type"] == "pull_request")["parameters"][
            "required_approving_review_count"
        ] = 0
        pages = next(env for env in live[f"{REPO}/environments"]["environments"] if env["name"] == "github-pages")
        pages["can_admins_bypass"] = False
        findings = by_setting(audit.audit(self.config, Replay(live)))
        ruleset = findings["ruleset.Main branch protection.rules.pull_request.required_approving_review_count"]
        rules = {rule["type"]: rule.get("parameters") for rule in ruleset.fix["body"]["rules"]}
        self.assertNotIn("merge_queue", rules, "fixing the review count does not switch the merge queue on")
        self.assertIs(rules["required_status_checks"]["strict_required_status_checks_policy"], True)
        self.assertEqual(rules["pull_request"]["required_approving_review_count"], 1)
        environment = findings["environment.github-pages.can_admins_bypass"].fix["body"]
        self.assertEqual(environment["reviewers"], [{"type": "User", "login": "motyc"}], "the reviewer stays")
        self.assertIs(environment["can_admins_bypass"], True)

    def test_a_missing_object_is_recreated_without_its_pending_targets(self):
        live = copy.deepcopy(LIVE)
        environments = live[f"{REPO}/environments"]["environments"]
        live[f"{REPO}/environments"]["environments"] = [env for env in environments if env["name"] != "github-pages"]
        live[f"{REPO}/rulesets"] = [entry for entry in live[f"{REPO}/rulesets"] if entry["id"] != 24757722]
        findings = by_setting(audit.audit(self.config, Replay(live)))
        pages = findings["environment.github-pages"]
        self.assertEqual(pages.status, "missing")
        self.assertEqual(pages.fix["body"]["reviewers"], [{"type": "User", "login": "motyc"}], "its current reviewer")
        main = findings["ruleset.Main branch protection"]
        rules = {rule["type"]: rule.get("parameters") for rule in main.fix["body"]["rules"]}
        self.assertNotIn("merge_queue", rules, "recreating the ruleset does not switch the merge queue on")
        self.assertIs(rules["required_status_checks"]["strict_required_status_checks_policy"], True)

    def test_a_finding_inside_a_reached_pending_target_applies_the_reviewed_value(self):
        live = copy.deepcopy(LIVE)
        queue = dict(self.config["ruleset"][0]["rules"]["merge_queue"], merge_method="MERGE")
        live[f"{REPO}/rulesets/24757722"]["rules"].append({"type": "merge_queue", "parameters": queue})
        findings = by_setting(audit.audit(self.config, Replay(live)))
        method = findings["ruleset.Main branch protection.rules.merge_queue.merge_method"]
        self.assertEqual((method.status, method.expected, method.actual), ("drift", "SQUASH", "MERGE"))
        rules = {rule["type"]: rule.get("parameters") for rule in method.fix["body"]["rules"]}
        self.assertEqual(rules["merge_queue"]["merge_method"], "SQUASH", "applying the body fixes the finding")
        self.assertEqual(findings["ruleset.Main branch protection.rules.merge_queue"].status, "done")

    def test_a_kept_team_reviewer_stays_a_team(self):
        live = copy.deepcopy(LIVE)
        pages = next(env for env in live[f"{REPO}/environments"]["environments"] if env["name"] == "github-pages")
        pages["can_admins_bypass"] = False
        rule = next(rule for rule in pages["protection_rules"] if rule["type"] == "required_reviewers")
        rule["reviewers"].append({"type": "Team", "reviewer": {"slug": "maintainers"}})
        findings = by_setting(audit.audit(self.config, Replay(live)))
        body = findings["environment.github-pages.can_admins_bypass"].fix["body"]
        self.assertIn({"type": "Team", "slug": "maintainers"}, body["reviewers"])
        self.assertNotIn({"type": "User", "login": "team:maintainers"}, body["reviewers"])

    def test_undeclared_rule_parameters_and_a_changed_check_source_are_drift(self):
        live = copy.deepcopy(LIVE)
        rules = {rule["type"]: rule for rule in live[f"{REPO}/rulesets/24757722"]["rules"]}
        rules["pull_request"]["parameters"]["automatic_copilot_code_review_enabled"] = True
        rules["required_status_checks"]["parameters"]["required_status_checks"][0]["integration_id"] = 1
        findings = by_setting(audit.audit(self.config, Replay(live)))
        added = findings["ruleset.Main branch protection.rules.pull_request.automatic_copilot_code_review_enabled"]
        self.assertEqual((added.status, added.expected, added.actual), ("drift", "absent", True))
        source = findings["ruleset.Main branch protection.rules.required_status_checks.required_status_checks"]
        self.assertEqual(source.status, "drift")
        self.assertEqual(source.actual, [{"context": "checks", "integration_id": 1}])

    def test_printed_commands_quote_every_value_for_the_shell(self):
        config = copy.deepcopy(self.config)
        label = {"name": "x $(touch pwned)", "color": "ffffff", "description": "a `tick` and 'quote' \\ $HOME"}
        config["label"].append(label)
        config["settings"]["squash_merge_commit_message"] = "PR_BODY"
        config["environment"]["stage $x"] = {"reviewers": [], "deployment": "all", "can_admins_bypass": True}
        findings = by_setting(audit.audit(config, Replay(), ("settings", "labels", "environments")))
        created = shlex.split(findings[f"label.{label['name']}"].command)
        self.assertEqual(created[3], label["name"])
        self.assertEqual(created[-1], label["description"])
        setting = shlex.split(findings["settings.squash_merge_commit_message"].command)
        self.assertEqual(setting[-2:], ["-f", "squash_merge_commit_message=PR_BODY"], "a string is sent as a string")
        self.assertIn("environments/stage%20%24x ", findings["environment.stage $x"].command)


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
            "project.owner: expected an organization login": lambda c: c["project"].update(owner="x;y"),
            "app.permissions: expected permission": lambda c: c["app"]["permissions"].update(contents="admin"),
            "is listed twice": lambda c: c["token"].append(dict(c["token"][0])),
            "pending[0]: missing key 'task'": lambda c: c["pending"][0].pop("task"),
            "format: expected 1": lambda c: c.update(format=2),
        }
        for message, change in cases.items():
            with self.subTest(message=message):
                self.assertIn(message, self.problems(change))

    def test_a_missing_required_key_is_listed_never_raised(self):
        tables = {
            "ruleset[0]": (lambda c: c["ruleset"][0], ("name", "target", "enforcement", "include", "bypass", "rules")),
            "environment.production": (lambda c: c["environment"]["production"], ("reviewers", "deployment")),
            "label[0]": (lambda c: c["label"][0], ("name", "color")),
            "project": (lambda c: c["project"], ("owner", "number")),
            "project.view[0]": (lambda c: c["project"]["view"][0], ("layout", "group_by", "sort_by")),
            "app": (lambda c: c["app"], ("slug", "permissions")),
            "token[0]": (lambda c: c["token"][0], ("workflow", "jobs", "github")),
        }
        for where, (table, keys) in tables.items():
            for key in keys:
                with self.subTest(where=where, key=key):
                    problems = self.problems(lambda c, table=table, key=key: table(c).pop(key))
                    self.assertIn(f"{where}: missing key {key!r}", problems)

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
