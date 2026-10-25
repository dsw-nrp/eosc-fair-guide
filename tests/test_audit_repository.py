"""The settings audit reports every difference with where and how to fix it, and its fix only adds."""

import copy
import io
import json
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import area_labels  # noqa: E402
import audit_repository as audit  # noqa: E402
import plan_issue_shape  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

LIVE = json.loads((Path(__file__).resolve().parent / "fixtures" / "repository-audit.json").read_text(encoding="utf-8"))
REPO = "GET repos/dsw-nrp/eosc-fair-guide"
OPEN = f"{REPO}/issues?state=open&per_page=100"
# When the Project items were recorded; the item checks measure waiting time from here.
RECORDED = datetime(2026, 10, 25, 12, tzinfo=UTC)
LABELS = f"{REPO}/labels?per_page=100"


def drop_labels(responses, *names):
    """The recorded state without some declared labels, as before `--fix` created them."""
    responses[LABELS] = [label for label in responses[LABELS] if label["name"] not in names]


class Replay:
    """The recorded live state: settings of 24 October 2026, and labels, Project items and open issues of 25 October
    after the labels were created and the backfill applied. Writes are kept and applied to labels, Project items and
    open issues."""

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
        if "/issues/" in path:
            number = int(path.split("/issues/")[1].split("/")[0])
            issue = next(issue for issue in self.responses[OPEN] if issue["number"] == number)
            if path.endswith("/labels"):
                issue["labels"] += [{"name": name} for name in body["labels"]]
            else:
                issue["type"] = {"name": body["type"]}
            return
        labels = self.responses[f"{REPO}/labels?per_page=100"]
        if method == "POST":
            labels.append({"name": body["name"], "color": body["color"], "description": body["description"]})
        else:
            name = path.rsplit("/", 1)[-1].replace("%20", " ")
            next(label for label in labels if label["name"] == name).update(body)


def project(responses):
    return responses["GRAPHQL Project"]["organization"]["projectV2"]


def project_items(responses):
    return responses["GRAPHQL ProjectItems"]["organization"]["projectV2"]["items"]["nodes"]


def project_workflows(responses):
    return responses["GRAPHQL ProjectWorkflows"]["organization"]["projectV2"]["workflows"]["nodes"]


def by_setting(findings):
    return {finding.setting: finding for finding in findings}


def baseline():
    """Every finding of the recorded live state, by setting."""
    return {finding.setting: finding.status for finding in audit.audit(audit.load(), Replay(), now=RECORDED)}


def beyond_baseline(findings):
    recorded = baseline()
    return {f.setting: f.status for f in findings if recorded.get(f.setting) != f.status}


QUEUE = "ruleset.Main branch protection.rules.merge_queue"
STAGING = "environment.staging"
TAG_DEPLOYMENT = "ruleset.Tag protection.rules.required_deployments.required_deployment_environments"
STRICT = "ruleset.Main branch protection.rules.required_status_checks.strict_required_status_checks_policy"


def pending_queue(config, live, *, applied=False):
    """The merge-queue steps as they waited on 24 October 2026: approved in the file, the queue absent live and the
    up-to-date requirement still on, unless `applied` keeps the live queue."""
    config.setdefault("pending", []).extend(
        [
            {"setting": QUEUE, "current": "absent", "task": "4.8, once 4.1 is on the default branch: enable the queue"},
            {"setting": STRICT, "current": True, "task": "4.8: switch off the up-to-date requirement"},
        ]
    )
    rules = live[f"{REPO}/rulesets/24757722"]["rules"]
    if not applied:
        rules[:] = [rule for rule in rules if rule["type"] != "merge_queue"]
        checks = next(rule for rule in rules if rule["type"] == "required_status_checks")
        checks["parameters"]["strict_required_status_checks_policy"] = True
    return rules


def pending_reviewer(config, live, reviewers=("motyc",)):
    """The `github-pages` reviewer removal as it waited on 24 October 2026: approved in the file, still live."""
    config.setdefault("pending", []).append(
        {"setting": "environment.github-pages.reviewers", "current": ["motyc"], "task": "4.8: remove the reviewer"}
    )
    pages = next(env for env in live[f"{REPO}/environments"]["environments"] if env["name"] == "github-pages")
    rule = {"id": 1, "type": "required_reviewers", "prevent_self_review": False, "reviewers": []}
    rule["reviewers"] = [{"type": "User", "reviewer": {"login": login}} for login in reviewers]
    pages["protection_rules"].append(rule)
    return pages, rule


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.config = audit.load()
        self.enterContext(unittest.mock.patch.object(audit, "clock", lambda: RECORDED))

    def test_the_committed_state_matches_the_recorded_live_state(self):
        # Recorded after `--fix` created the declared labels and the reviewed backfill typed and labelled every issue.
        # The maintainer created `staging` as declared on 25 October 2026; the tag ruleset's switch to it waits, still
        # at its recorded value, for the rest of the hand-off in task 8.7.
        statuses = {finding.setting: finding.status for finding in audit.audit(self.config, Replay())}
        self.assertEqual(statuses, {"organization.issue_fields": "unavailable", TAG_DEPLOYMENT: "pending"})
        issues = [node["content"] for node in project_items(LIVE) if node["content"]["__typename"] == "Issue"]
        self.assertGreater(len(issues), 50)
        self.assertTrue(all(issue["issueType"] for issue in issues if issue["state"] == "OPEN"))

    def test_project_workflows_the_token_may_not_read_leave_the_rest_audited(self):
        # Run 40190490225: the App token reads the Project, but GitHub refuses its workflows.
        live = copy.deepcopy(LIVE)
        live["GRAPHQL ProjectWorkflows"] = audit.UnavailableError("gh: You do not have permission to access workflows.")
        next(view for view in project(live)["views"]["nodes"] if view["name"] == "Triage")["filter"] = "is:issue"
        findings = audit.audit(self.config, Replay(live))
        found = by_setting(findings)
        self.assertEqual(found["project.workflows"].status, "unavailable")
        self.assertIn("does not include the Project's workflows", found["project.workflows"].note)
        self.assertEqual(found["project.view.Triage.filter"].status, "drift", "fields, views and items are audited")
        self.assertNotIn("project", found, "the Project itself is readable")
        section = audit.digest(findings)
        self.assertIn("`project.workflows`: gh: You do not have permission to access workflows:", section)
        self.assertNotIn(audit.OWNER_STEP, section, "no owner step for what no owner step fixes")

    def test_settings_the_token_cannot_see_are_unavailable_not_drift(self):
        # Run 40190490225: the weekly job's GITHUB_TOKEN receives the merge settings as null.
        live = copy.deepcopy(LIVE)
        settings = self.config["settings"]
        for key in settings:
            live[REPO][key] = None
        visible = next(key for key, value in settings.items() if isinstance(value, bool))
        live[REPO][visible] = not settings[visible]
        found = by_setting(audit.audit(self.config, Replay(live), sections=["settings"]))
        self.assertEqual(found["settings"].status, "unavailable")
        self.assertIn("as null to this token", found["settings"].note)
        self.assertNotIn(visible, found["settings"].note)
        self.assertEqual(found[f"settings.{visible}"].status, "drift", "a setting the token sees is still compared")
        hidden = [setting for setting in found if setting.startswith("settings.") and setting != f"settings.{visible}"]
        self.assertEqual(hidden, [], "an unseen setting is never reported as drift")

    def test_an_approved_target_waits_as_pending_with_its_task(self):
        live = copy.deepcopy(LIVE)
        pending_queue(self.config, live)
        findings = audit.audit(self.config, Replay(live))
        self.assertEqual(beyond_baseline(findings), {STRICT: "pending", QUEUE: "pending"})
        merge_queue = by_setting(findings)[QUEUE]
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
        next(flow for flow in project_workflows(live) if flow["name"] == "Auto-add to project")["enabled"] = False
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
        pending_reviewer(self.config, live)
        live["GRAPHQL Project"] = audit.UnavailableError("Resource not accessible by integration")
        live[f"{REPO}/environments"] = audit.UnavailableError("HTTP 403: Must have admin rights")
        drop_labels(live, "breaking-change")
        findings = by_setting(audit.audit(self.config, Replay(live)))
        self.assertEqual(findings["project"].status, "unavailable")
        self.assertIn("Resource not accessible", findings["project"].note)
        self.assertEqual(findings["environments"].status, "unavailable")
        self.assertEqual(findings["environments"].ui, "Settings → Environments", "a section path names no object")
        self.assertNotIn(
            "environment.github-pages.reviewers", findings, "a pending target in an unreadable section is not judged"
        )
        self.assertEqual(findings["label.breaking-change"].status, "missing", "the rest of the audit still runs")

    def test_an_empty_organization_list_is_unavailable_not_drift(self):
        live = copy.deepcopy(LIVE)
        live["GET orgs/dsw-nrp/issue-types"] = []
        findings = by_setting(audit.audit(self.config, Replay(live), sections=("organization",)))
        self.assertEqual(findings["organization.issue_types"].status, "unavailable")
        self.assertIn("an organization owner can confirm", findings["organization.issue_types"].note)
        self.assertFalse([setting for setting in findings if setting.startswith("organization.issue_types.")])

    def test_bypass_actors_hidden_from_a_read_only_token_are_unavailable_not_drift(self):
        live = copy.deepcopy(LIVE)
        del live[f"{REPO}/rulesets/24757722"]["bypass_actors"]
        findings = by_setting(audit.audit(self.config, Replay(live)))
        bypass = findings["ruleset.Main branch protection.bypass"]
        self.assertEqual(bypass.status, "unavailable")
        self.assertIn("write access to the ruleset", bypass.note)

    def test_a_reached_target_asks_for_its_pending_entry_to_be_removed(self):
        live = copy.deepcopy(LIVE)
        pending_queue(self.config, live, applied=True)
        findings = by_setting(audit.audit(self.config, Replay(live)))
        for setting in (QUEUE, STRICT):
            self.assertEqual(findings[setting].status, "done")
            self.assertIn("remove this pending entry", findings[setting].note)

    def test_a_pending_target_waits_and_one_that_moved_elsewhere_is_drift(self):
        live = copy.deepcopy(LIVE)
        _, rule = pending_reviewer(self.config, live)
        finding = by_setting(audit.audit(self.config, Replay(live)))["environment.github-pages.reviewers"]
        self.assertEqual(finding.status, "pending")
        rule["reviewers"].append({"type": "User", "reviewer": {"login": "someone-else"}})
        finding = by_setting(audit.audit(self.config, Replay(live)))["environment.github-pages.reviewers"]
        self.assertEqual(finding.status, "drift")

    def test_fix_only_creates_or_updates_declared_labels_and_adds_project_items(self):
        live = copy.deepcopy(LIVE)
        live[REPO]["allow_auto_merge"] = True
        drop_labels(live, "area:sources", "source-refresh")
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
        self.assertEqual(
            sorted(kinds), [("PATCH", "bug"), ("POST", "labels"), ("POST", "labels"), ("graphql", "AddItem")]
        )
        created = {write[2]["name"]: write[2]["color"] for write in replay.writes if write[0] == "POST"}
        self.assertEqual(set(created), {"area:sources", "source-refresh"}, "every missing declared label is created")
        self.assertEqual(created["area:sources"], "5319e7", "with its declared colour")
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
        live = copy.deepcopy(LIVE)
        pending_queue(self.config, live)
        with (
            tempfile.TemporaryDirectory() as temporary,
            redirect_stdout(io.StringIO()),
            unittest.mock.patch.object(audit, "load", return_value=self.config),
        ):
            path = Path(temporary) / "audit.json"
            audit.main(["--json", str(path)], github=Replay(live))
            report = json.loads(path.read_text(encoding="utf-8"))
        bodies = {item["setting"]: item["fix"]["body"] for item in report["findings"] if item["fix"]}
        queue = {rule["type"]: rule for rule in bodies[QUEUE]["rules"]}
        self.assertEqual(queue["merge_queue"]["parameters"]["merge_method"], "SQUASH")
        checks = queue["required_status_checks"]["parameters"]
        self.assertEqual(checks["required_status_checks"], [{"context": "checks", "integration_id": 15368}])
        self.assertIs(checks["strict_required_status_checks_policy"], True, "the other pending target stays live")
        pull = queue["pull_request"]["parameters"]
        self.assertIs(pull["require_extra_approval_for_unattributed_changes"], True, "no live parameter is dropped")
        self.assertNotIn("merge_queue", {rule["type"] for rule in bodies[STRICT]["rules"]})

    def test_a_command_for_another_difference_never_applies_a_pending_target(self):
        live = copy.deepcopy(LIVE)
        rules = pending_queue(self.config, live)
        next(rule for rule in rules if rule["type"] == "pull_request")["parameters"][
            "required_approving_review_count"
        ] = 0
        pages, _ = pending_reviewer(self.config, live)
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
        pending_queue(self.config, live)
        pending_reviewer(self.config, live)
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
        rules = pending_queue(self.config, live, applied=True)
        next(rule for rule in rules if rule["type"] == "merge_queue")["parameters"]["merge_method"] = "MERGE"
        findings = by_setting(audit.audit(self.config, Replay(live)))
        method = findings[f"{QUEUE}.merge_method"]
        self.assertEqual((method.status, method.expected, method.actual), ("drift", "SQUASH", "MERGE"))
        body = {rule["type"]: rule.get("parameters") for rule in method.fix["body"]["rules"]}
        self.assertEqual(body["merge_queue"]["merge_method"], "SQUASH", "applying the body fixes the finding")
        self.assertEqual(findings[QUEUE].status, "done")

    def test_a_kept_team_reviewer_stays_a_team(self):
        live = copy.deepcopy(LIVE)
        pages, rule = pending_reviewer(self.config, live)
        pages["can_admins_bypass"] = False
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
            # Appended after whatever targets the committed file has pending.
            f"pending[{len(self.config.get('pending', []))}]: missing key 'task'": lambda c: c.setdefault(
                "pending", []
            ).append({"setting": QUEUE, "current": 1}),
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

    def test_the_setting_steps_and_any_pending_entry_are_documented_in_order(self):
        text = (Path(__file__).resolve().parent.parent / "docs/deployment.md").read_text(encoding="utf-8")
        table = text[text.index("| Step | Precondition | Rollback |") :].split("\n\n")[0].splitlines()[2:]
        steps = {
            QUEUE: "Turn the merge queue on",
            STRICT: "require branches to be up to date",
            "environment.production": "Create `production`",
            "environment.github-pages.reviewers": "Remove the reviewer from `github-pages`",
            STAGING: "Create `staging`",
            TAG_DEPLOYMENT: "Require `staging` instead of `github-pages` for release tags",
        }
        rows = {setting: [index for index, row in enumerate(table) if step in row] for setting, step in steps.items()}
        self.assertEqual(list(rows.values()), [[0], [1], [2], [3], [4], [5]], "each step and its rollback, in order")
        pending = [entry["setting"] for entry in self.config.get("pending", [])]
        self.assertLessEqual(set(pending), set(steps), "an approved target waits for a documented step")
        self.assertEqual(pending, sorted(pending, key=list(steps).index), "pending steps follow the documented order")

    def test_an_invalid_file_stops_before_reading_anything(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "repository.toml"
            path.write_text('format = 1\nrepository = "a/b"\n[[label]]\nname = "x"\ncolor = "red"\n', encoding="utf-8")
            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), unittest.mock.patch("sys.stderr", errors):
                self.assertEqual(audit.main(["--config", str(path)], github=object()), 1)
        self.assertIn("label[0].color: malformed value 'red'", errors.getvalue())


class TriageGuideTests(unittest.TestCase):
    """The triage guide names only declared statuses, views, labels and automations, and only real commands."""

    def setUp(self):
        self.config = audit.load()
        self.text = (ROOT / "docs" / "maintenance.md").read_text(encoding="utf-8")
        self.triage = self.text.split("\n## Triage\n", 1)[1].split("\n## ", 1)[0]

    def column(self, header):
        rows = self.triage.split(header, 1)[1].split("\n\n", 1)[0].splitlines()[2:]
        return [row.split("|")[1].strip().strip("`") for row in rows]

    def test_statuses_views_labels_and_automations_are_the_declared_ones(self):
        project = self.config["project"]
        self.assertEqual(self.column("| Status | Meaning | Set by |"), project["options"]["Status"])
        self.assertEqual(sorted(self.column("| View | Shows |")), sorted(view["name"] for view in project["view"]))
        automatic = {label["name"] for label in self.config["label"] if label.get("paths")} | {"source-refresh"}
        self.assertEqual(set(self.column("| Label | Covers |")), automatic)
        rows = self.triage.split("| Status | Meaning | Set by |", 1)[1].split("\n\n", 1)[0].splitlines()[2:]
        automations = re.findall(r'"([^"]+)"', " ".join(row.split("|")[3] for row in rows))
        self.assertEqual(len(automations), 4)
        for name in automations:
            with self.subTest(automation=name):
                self.assertIs(project["workflows"].get(name), True, "an automation the guide relies on is on")
        for field, options in self.config["organization"]["issue_fields"].items():
            self.assertIn(f"{field} ({', '.join(options[:-1])} or {options[-1]})", self.triage)

    def test_every_command_flag_and_path_exists(self):
        commands = re.findall(r"python (scripts/\w+\.py)((?: --?[\w-]+(?: [^\s`#-][^\s`#]*)?)*)", self.text)
        self.assertGreater(len(commands), 8)
        for script, arguments in commands:
            with self.subTest(command=f"{script}{arguments}"):
                source = (ROOT / script).read_text(encoding="utf-8")
                for flag in re.findall(r"--[\w-]+", arguments):
                    self.assertIn(f'"{flag}"', source, f"{script} has no {flag}")
                for value in re.findall(r" ([\w./-]+\.toml)", arguments):
                    self.assertTrue((ROOT / value).is_file(), value)
        self.assertTrue((ROOT / ".agents/skills/aiscr-plan-issue/SKILL.md").is_file(), "/aiscr-plan-issue is delivered")


class AreaLabelTests(unittest.TestCase):
    """The reviewed path rules give each area label real files, and the helper prints only what they match."""

    def setUp(self):
        self.rules = area_labels.path_rules(audit.load())

    def test_every_area_label_has_rules_matching_tracked_files(self):
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True
        ).stdout.splitlines()
        areas = {label["name"] for label in audit.load()["label"] if label["name"].startswith("area:")}
        self.assertEqual(set(self.rules), areas, "each area label, and only those, has path rules")
        for name in areas:
            with self.subTest(label=name):
                self.assertTrue(area_labels.labels_for(tracked, {name: self.rules[name]}))

    def test_planning_and_usage_logs_alone_label_nothing(self):
        paths = [".agents/reports/usage/usage-2026-10-25-x.md", "openspec/changes/x/design.md", "tests/test_x.py"]
        self.assertEqual(area_labels.labels_for(paths, self.rules), [])
        self.assertEqual(
            area_labels.labels_for(["content/checks/dataset.toml", "content/live.toml"], self.rules),
            ["area:content", "area:evaluation"],
        )

    def test_the_helper_refuses_anything_but_a_bounded_list_of_paths(self):
        for text in ('{"path": "x"}', '["x", 1]', json.dumps(["x"] * (area_labels.MAX_PATHS + 1)), "not json"):
            with (
                self.subTest(text=text[:20]),
                unittest.mock.patch("sys.stdin", io.StringIO(text)),
                redirect_stdout(io.StringIO()),
                unittest.mock.patch("sys.stderr", io.StringIO()),
            ):
                self.assertEqual(area_labels.main([]), 1)
        with (
            unittest.mock.patch("sys.stdin", io.StringIO('["docker/Dockerfile"]')),
            redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(area_labels.main([]), 0)
        self.assertEqual(json.loads(output.getvalue()), ["area:delivery"])


def shaped(kind="task"):
    """A body the delivered `readiness()` accepts: marker, title, metadata, every section and the disclosure."""
    engine = plan_issue_shape.engine()
    block = engine.TYPE_BLOCK_FORMS[kind][0]
    return "\n".join(
        [engine.ISSUE_MARKER, "", "# Something to do", "", "| Field | Value |", "| --- | --- |", f"| Type | {kind} |"]
        + ["| Affects | the Guide |", "| Reported by | maintainer |"]
        + [
            line
            for section in ("Problem", block, "Scope", "Open questions")
            for line in ("", f"## {section}", "", "Text.")
        ]
        + ["", "## Acceptance criteria", "", "- [ ] Text.", "", "## Reporter context", "", engine.REPORTER_CONTEXT_OPEN]
        + ["None.", engine.REPORTER_CONTEXT_CLOSE, "", engine.INTERACTIVE_DISCLOSURE]
    ).replace(
        "## Open questions\n\nText.\n\n## Acceptance criteria\n\n- [ ] Text.",
        "## Acceptance criteria\n\n- [ ] Text.\n\n## Open questions\n\nText.",
    )


def node(
    number, *, kind="Issue", state="OPEN", status="Needs triage", days=1, issue_type=None, labels=(), body="", **fields
):
    """A Project item as the GraphQL query returns it, its Status set `days` before the recording."""
    since = (RECORDED - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    content = {
        "__typename": kind,
        "number": number,
        "state": state,
        "url": f"https://github.com/dsw-nrp/eosc-fair-guide/{'issues' if kind == 'Issue' else 'pull'}/{number}",
        "repository": {"nameWithOwner": "dsw-nrp/eosc-fair-guide"},
    }
    if kind == "Issue":
        values = [{"name": value, "field": {"name": name.title()}} for name, value in fields.items()]
        content |= {
            "body": body,
            "issueType": {"name": issue_type} if issue_type else None,
            "labels": {"nodes": [{"name": name} for name in labels]},
            "issueFieldValues": {"nodes": values},
        }
    status_value = [{"name": status, "updatedAt": since, "field": {"name": "Status"}}] if status else []
    return {"fieldValues": {"nodes": [{}, *status_value]}, "content": content}


class ProjectItemTests(unittest.TestCase):
    """Items needing a person are named with their link and how to fix them; settled items say nothing."""

    def setUp(self):
        self.config = audit.load()

    def findings(self, nodes):
        live = copy.deepcopy(LIVE)
        project_items(live)[:] = nodes
        live[OPEN] = []
        return by_setting(audit.audit(self.config, Replay(live), sections=("project",), now=RECORDED))

    def test_each_rule_of_the_definition_and_the_waiting_times(self):
        complete = {"issue_type": "Task", "labels": ["area:content"], "priority": "Medium", "effort": "Low"}
        findings = self.findings(
            [
                node(1, state="CLOSED", status="In progress"),
                node(2, status="Done", **complete),
                node(3),
                node(4, issue_type="Feature", body=shaped("bug")),
                node(5, days=15, **complete),
                node(6, status="Ready", days=4, **(complete | {"priority": "Urgent"}), body=shaped()),
                node(7, status="Ready", issue_type="Bug", labels=["bug"], priority="High", body=shaped("bug")[:-200]),
                node(8, status="Ready", body=shaped(), **complete),
                node(9, kind="PullRequest", status="Needs triage", days=40),
                node(10, kind="PullRequest", state="MERGED", status="Done"),
                node(11, days=14, **complete),
                node(12, status="Ready", days=3, **(complete | {"priority": "Urgent"}), body=shaped()),
            ]
        )
        self.assertEqual(
            {setting: finding.status for setting, finding in findings.items()},
            dict.fromkeys(
                [
                    "project.item.#1.status",
                    "project.item.#2.status",
                    "project.item.#3.type",
                    "project.item.#4.body-type",
                    "project.item.#5.triage",
                    "project.item.#6.urgent",
                    "project.item.#7.ready",
                ],
                "attention",
            ),
            "the met definition (#8), pull requests (#9, #10) and the exact limits (#11, #12) need nothing",
        )
        self.assertEqual(
            (findings["project.item.#1.status"].expected, findings["project.item.#1.status"].actual),
            ("Done", "In progress"),
        )
        self.assertEqual(findings["project.item.#2.status"].expected, "not Done")
        self.assertIn("type=TYPE", findings["project.item.#3.type"].command)
        self.assertEqual(findings["project.item.#3.type"].ui, "https://github.com/dsw-nrp/eosc-fair-guide/issues/3")
        self.assertEqual(
            (findings["project.item.#4.body-type"].expected, findings["project.item.#4.body-type"].actual),
            ("feature", "bug"),
        )
        self.assertEqual(findings["project.item.#5.triage"].actual, "waiting 15 days")
        self.assertEqual(findings["project.item.#6.urgent"].actual, "not started for 4 days")
        lacking = findings["project.item.#7.ready"].actual
        self.assertEqual(lacking[:2], ["an area:* label", "Effort"])
        self.assertTrue(lacking[2].startswith("the planned-issue shape ("), "the shape names what is missing")
        for finding in findings.values():
            with self.subTest(setting=finding.setting):
                self.assertTrue(finding.ui.startswith("https://github.com/dsw-nrp/eosc-fair-guide/"))
                self.assertTrue(finding.command or finding.note, "and how to act")
                self.assertTrue(finding.fails)

    def test_issue_fields_and_status_dates_are_read_from_the_project(self):
        page = {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [node(6, status="Ready", days=4, issue_type="Bug", priority="Urgent", effort="Low")],
        }
        replay = Replay({"GRAPHQL ProjectItems": {"organization": {"projectV2": {"items": page}}}})
        entries, hidden = audit.read_items(replay, "dsw-nrp", 1, "dsw-nrp/eosc-fair-guide")
        self.assertEqual(hidden, 0)
        self.assertEqual(
            {key: entries[6][key] for key in ("kind", "state", "type", "status", "priority", "effort")},
            {"kind": "issue", "state": "open", "type": "Bug", "status": "Ready", "priority": "Urgent", "effort": "Low"},
        )
        self.assertEqual(entries[6]["since"], "2026-10-21T12:00:00Z")

    def test_items_hidden_from_the_token_are_unavailable_never_missing(self):
        live = copy.deepcopy(LIVE)
        project_items(live).append({"type": "REDACTED", "fieldValues": {"nodes": []}, "content": None})
        next(view for view in project(live)["views"]["nodes"] if view["name"] == "Triage")["filter"] = "is:issue"
        findings = by_setting(audit.audit(self.config, Replay(live), sections=("project",), now=RECORDED))
        self.assertEqual(findings["project.items"].status, "unavailable")
        self.assertIn("1 items' issues and pull requests are hidden", findings["project.items"].note)
        self.assertEqual([setting for setting in findings if setting.startswith("project.item")], ["project.items"])
        self.assertEqual(findings["project.view.Triage.filter"].status, "drift", "the Project's settings still count")

    def test_only_graphql_uses_the_project_token(self):
        calls = []

        def run(arguments, **options):
            calls.append((arguments[2], (options.get("env") or {}).get("GH_TOKEN")))
            return unittest.mock.Mock(stdout='{"data": {}}' if arguments[2] == "graphql" else "[]")

        with unittest.mock.patch.object(audit.subprocess, "run", run):
            github = audit.GhCli("app-token")
            github.get("repos/dsw-nrp/eosc-fair-guide/labels")
            github.graphql(audit.PROJECT_QUERY, {"owner": "dsw-nrp", "number": 1})
            audit.GhCli().graphql(audit.PROJECT_QUERY, {"owner": "dsw-nrp", "number": 1})
        self.assertEqual(
            calls, [("repos/dsw-nrp/eosc-fair-guide/labels", None), ("graphql", "app-token"), ("graphql", None)]
        )


class DigestTests(unittest.TestCase):
    """The digest's section is public: it links issues and Urgent work but counts what reads Project-only fields."""

    def setUp(self):
        self.config = audit.load()

    def test_public_lines_counted_project_fields_and_a_bound(self):
        live = copy.deepcopy(LIVE)
        complete = {"issue_type": "Task", "labels": ["area:content"], "priority": "Medium", "effort": "Low"}
        project_items(live)[:] = [node(number) for number in range(100, 140)] + [
            node(5, days=15, **complete),
            node(6, status="Ready", days=4, **(complete | {"priority": "Urgent"}), body=shaped()),
            node(7, status="Ready", **(complete | {"priority": "High"})),
        ]
        live[OPEN] = []
        drop_labels(live, "area:sources")
        text = audit.digest(audit.audit(self.config, Replay(live), now=RECORDED))
        self.assertTrue(text.startswith("## Project and settings\n"))
        self.assertIn("- #6 is Urgent and has not started (not started for 4 days).", text)
        self.assertIn("- 1 Ready issue(s) do not meet the definition of Ready; see the Project's views.", text)
        self.assertIn("- 1 issue(s) have waited over 14 days for triage; see the Project's views.", text)
        self.assertNotIn("#7", text, "a Ready issue is counted, not named")
        self.assertNotIn("#5 ", text)
        for value in ("High", "Medium", "Low", "In progress"):
            self.assertNotIn(value, text, "no Project field value other than Urgent is shown")
        self.assertIn("- `label.area:sources`: expected", text, "settings drift is listed")
        public = 40 + 1 + 1  # the untyped issues, the Urgent one and the missing label
        overflow = f"- … and {public - audit.DIGEST_ITEMS} more; `python scripts/audit_repository.py` lists them all."
        self.assertIn(overflow, text, "only those")
        listed = text.split("Unavailable")[0].count("\n- ")
        self.assertEqual(listed, audit.DIGEST_ITEMS + 1 + 2, "the bound, its overflow line and the two counts")

    def test_a_denied_token_is_unavailable_with_the_owners_step_and_the_rest_intact(self):
        live = copy.deepcopy(LIVE)
        live["GRAPHQL Project"] = audit.UnavailableError("Resource not accessible by integration")
        drop_labels(live, "breaking-change")
        findings = audit.audit(self.config, Replay(live), now=RECORDED)
        text = audit.digest(findings)
        self.assertIn("- `project`: Resource not accessible by integration. An organization owner accepts", text)
        self.assertIn("- `label.breaking-change`: expected", text, "the settings part still publishes")
        self.assertNotIn("has no Issue Type", text, "nothing is claimed about an unread Project")

    def test_a_clean_state_says_so(self):
        text = audit.digest([audit.Finding("settings", "settings", "done")])
        self.assertIn("Every readable setting and Project item matches the reviewed state.", text)


class BackfillTests(unittest.TestCase):
    """The reviewed mapping is compared first and applied only with `--fix`: Issue Types and area labels only."""

    def setUp(self):
        self.config = audit.load()
        self.live = copy.deepcopy(LIVE)

        def issue(number, **extra):
            return {"number": number, "html_url": f"https://github.com/x/{number}", "node_id": f"I_{number}"} | {
                "labels": [],
                "type": None,
                **extra,
            }

        self.live[OPEN] = [
            issue(13),
            issue(83, labels=[{"name": "area:sources"}], type={"name": "Feature"}),
            issue(99),
            issue(110, pull_request={"url": "x"}),
        ]
        self.directory = self.enterContext(tempfile.TemporaryDirectory())

    def mapping(self, text):
        path = Path(self.directory) / "backfill.toml"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_a_dry_run_lists_the_changes_and_fix_applies_only_them(self):
        path = self.mapping(
            '[[issue]]\nnumber = 13\ntype = "Feature"\narea = ["area:interface"]\n\n'
            '[[issue]]\nnumber = 83\ntype = "Feature"\narea = ["area:sources"]\n\n'
            '[[issue]]\nnumber = 7\ntype = "Bug"\narea = ["area:content"]\n'
        )
        replay = Replay(self.live)
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(audit.main(["--backfill", path], github=replay), 1)
        self.assertEqual(replay.writes, [], "the dry run writes nothing")
        report = output.getvalue()
        self.assertIn("Sections: backfill.", report)
        self.assertIn("[MISSING] backfill.#13.type", report)
        self.assertIn("command:  gh api -X PATCH repos/dsw-nrp/eosc-fair-guide/issues/13 -f type=Feature", report)
        self.assertIn("[MISSING] backfill.#13.labels", report)
        self.assertIn("[UNDECLARED] backfill.#99", report, "an unmapped open issue goes to triage")
        self.assertIn("[DONE] backfill.#7", report, "a closed issue needs nothing")
        self.assertNotIn("#83.", report, "an issue already matching its mapping needs nothing")
        self.assertNotIn("#110", report, "pull requests are not mapped")
        with redirect_stdout(io.StringIO()):
            audit.main(["--backfill", path, "--fix"], github=replay)
        issue = "repos/dsw-nrp/eosc-fair-guide/issues/13"
        self.assertEqual(
            replay.writes,
            [("PATCH", issue, {"type": "Feature"}), ("POST", f"{issue}/labels", {"labels": ["area:interface"]})],
        )

    def test_labels_wait_until_the_declared_labels_exist(self):
        path = self.mapping('[[issue]]\nnumber = 13\ntype = "Feature"\narea = ["area:interface"]\n')
        drop_labels(self.live, *(label["name"] for label in self.config["label"] if label["name"].startswith("area:")))
        replay = Replay(self.live)
        with redirect_stdout(io.StringIO()) as output:
            audit.main(["--backfill", path, "--fix"], github=replay)
        self.assertEqual([write[0] for write in replay.writes], ["PATCH"], "only the type; GitHub would invent labels")
        self.assertIn("[MISSING] backfill.labels", output.getvalue())
        self.assertIn("--section labels --fix", output.getvalue())

    def test_a_mapping_outside_the_declared_types_and_areas_is_refused(self):
        path = self.mapping(
            '[[issue]]\nnumber = 13\ntype = "Epic"\narea = ["bug"]\n\n'
            '[[issue]]\nnumber = 13\ntype = "Task"\narea = []\n'
        )
        errors = io.StringIO()
        with unittest.mock.patch("sys.stderr", errors):
            self.assertEqual(audit.main(["--backfill", path], github=Replay(self.live)), 1)
        for problem in (
            "'Epic' is not a declared issue type",
            "expected one or more declared area:* labels",
            "expected a unique issue number",
        ):
            self.assertIn(problem, errors.getvalue())


if __name__ == "__main__":
    unittest.main()
