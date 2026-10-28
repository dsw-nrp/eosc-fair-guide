#!/usr/bin/env python3
"""Compare the repository's live GitHub settings with the reviewed expected state in `.github/repository.toml`.

    python scripts/audit_repository.py [--section NAME ...] [--json PATH] [--digest PATH] [--fix]
    python scripts/audit_repository.py --backfill MAPPING [--fix]
    python scripts/audit_repository.py --check-config

Reads, through the GitHub CLI (``gh``) and the caller's token, the repository's merge settings, rulesets,
environments and labels, Project #1 (fields, options, views, built-in automations and whether every open issue and
pull request is an item), the organization's issue types and issue fields, and the GitHub App's registered
permissions. Each difference names the setting, the expected and actual values, the UI path and an equivalent
command. A section the token cannot read is reported as unavailable, never as matching. An approved target recorded
under ``[[pending]]`` is reported as pending while the live value still equals its recorded current value.

Project items that need a person are reported as needing attention, each with its link: a Status that does not
match whether the item is open, an open issue without an Issue Type or whose body's ``Type`` row disagrees with it,
a Ready issue short of the definition of Ready (type, an ``area:*`` label, Priority, Effort and the planned-issue
shape), triage waiting over 14 days and Urgent work not started after three. ``--digest`` writes the public
"Project and settings" section of the maintenance digest, which counts the checks that read Project-only fields.

The audit writes nothing unless ``--fix`` is given, and ``--fix`` only creates or updates the declared labels and adds
missing open issues and pull requests to the Project; with ``--backfill`` it instead adds the reviewed mapping's area
labels and Issue Types to open issues. It never deletes a label, never changes a Project field value and never
changes a setting: people apply those, and the next audit confirms them. ``--check-config`` validates the file
offline. Exit status 1 means drift, an undeclared object, an item needing attention or a failed fix; unavailable and
pending sections are listed without failing.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import plan_issue_shape

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".github" / "repository.toml"
SECTIONS = ("settings", "rulesets", "environments", "labels", "project", "organization", "app")
ABSENT = "absent"
UNORDERED = {"include", "exclude", "bypass", "allowed_merge_methods", "reviewers", "branch_policies"}
UNORDERED |= {"required_status_checks"}

SETTING_KEYS = {
    "allow_squash_merge": bool,
    "allow_merge_commit": bool,
    "allow_rebase_merge": bool,
    "allow_auto_merge": bool,
    "allow_update_branch": bool,
    "delete_branch_on_merge": bool,
    "squash_merge_commit_title": ("PR_TITLE", "COMMIT_OR_PR_TITLE"),
    "squash_merge_commit_message": ("PR_BODY", "COMMIT_MESSAGES", "BLANK"),
    "merge_commit_title": ("PR_TITLE", "MERGE_MESSAGE"),
    "merge_commit_message": ("PR_BODY", "PR_TITLE", "BLANK"),
    "has_discussions": bool,
    "has_projects": bool,
    "has_wiki": bool,
}
RULE_TYPES = {
    "creation",
    "deletion",
    "update",
    "non_fast_forward",
    "required_linear_history",
    "required_signatures",
    "pull_request",
    "required_status_checks",
    "required_deployments",
    "merge_queue",
}
BYPASS = re.compile(r"^(RepositoryRole|Team|Integration|OrganizationAdmin|DeployKey) \d+ (always|pull_request)$")
POLICY = re.compile(r"^(branch|tag) \S+$")
SORT = re.compile(r"^.+ (asc|desc)$")
ACCESS = ("read", "write")
TOKEN_ACCESS = ("read", "write", "none")
UI = {
    "settings": "Settings → General → Pull Requests (merge options) and Features",
    "rulesets": "Settings → Rules → Rulesets → {name}",
    "environments": "Settings → Environments → {name}",
    "labels": "Issues → Labels",
    "project": "Project {title} → Settings, Workflows or the view's menu",
    "organization": "Organization settings → Planning → Issue types / Issue fields",
    "app": "The App owner's Settings → Developer settings → GitHub Apps → {slug} → Permissions & events",
}


class ConfigError(ValueError):
    """The expected-state file is malformed; the message lists every problem."""


class UnavailableError(Exception):
    """The token cannot read this part of the live state; the message names the access needed."""


# --- expected state ---------------------------------------------------------------------------------------------


def _keys(problems, where, table, allowed, required=()):
    """Record unknown and missing keys; true only when the table has every required key to check further."""
    if not isinstance(table, dict):
        problems.append(f"{where}: expected a table")
        return False
    missing = [key for key in required if key not in table]
    problems += [f"{where}: unknown key {key!r}" for key in table if key not in allowed]
    problems += [f"{where}: missing key {key!r}" for key in missing]
    return not missing


def _strings(problems, where, value, pattern=None):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        problems.append(f"{where}: expected a list of strings")
        return
    problems += [f"{where}: malformed value {item!r}" for item in value if pattern and not pattern.match(item)]


def _access(problems, where, value, allowed):
    if not isinstance(value, dict) or not all(isinstance(k, str) and v in allowed for k, v in value.items()):
        problems.append(f"{where}: expected permission = {' | '.join(allowed)} entries")


def validate(config: dict) -> list[str]:
    """Every problem in the expected state, with its location; an empty list means the file is usable."""
    problems: list[str] = []
    top = {"format", "repository", "settings", "ruleset", "environment", "label", "project"}
    top |= {"organization", "app", "token", "pending"}
    _keys(problems, "repository.toml", config, top, ("format", "repository"))
    if config.get("format") != 1:
        problems.append("format: expected 1")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", str(config.get("repository", ""))):
        problems.append("repository: expected OWNER/NAME")
    for key, value in config.get("settings", {}).items():
        kind = SETTING_KEYS.get(key)
        if kind is None:
            problems.append(f"settings: unknown key {key!r}")
        elif (kind is bool and not isinstance(value, bool)) or (isinstance(kind, tuple) and value not in kind):
            problems.append(f"settings.{key}: malformed value {value!r}")
    names = [ruleset.get("name") for ruleset in config.get("ruleset", []) if isinstance(ruleset, dict)]
    if len(names) != len(set(names)):
        problems.append("ruleset: duplicated name")
    for index, ruleset in enumerate(config.get("ruleset", [])):
        where = f"ruleset[{index}]"
        allowed = {"name", "target", "enforcement", "include", "exclude", "bypass", "rules"}
        if not _keys(problems, where, ruleset, allowed, tuple(allowed)):
            continue
        if ruleset["target"] not in ("branch", "tag"):
            problems.append(f"{where}.target: malformed value {ruleset['target']!r}")
        if ruleset["enforcement"] not in ("active", "evaluate", "disabled"):
            problems.append(f"{where}.enforcement: malformed value {ruleset['enforcement']!r}")
        for key in ("include", "exclude"):
            _strings(problems, f"{where}.{key}", ruleset[key])
        _strings(problems, f"{where}.bypass", ruleset["bypass"], BYPASS)
        for rule, parameters in ruleset["rules"].items() if isinstance(ruleset["rules"], dict) else ():
            if rule not in RULE_TYPES:
                problems.append(f"{where}.rules: unknown rule {rule!r}")
            elif not isinstance(parameters, dict):
                problems.append(f"{where}.rules.{rule}: expected a table")
    for name, environment in config.get("environment", {}).items():
        where = f"environment.{name}"
        allowed = {"reviewers", "prevent_self_review", "deployment", "branch_policies", "can_admins_bypass"}
        if not _keys(problems, where, environment, allowed, ("reviewers", "deployment", "can_admins_bypass")):
            continue
        _strings(problems, f"{where}.reviewers", environment["reviewers"])
        if environment["deployment"] not in ("all", "protected", "custom"):
            problems.append(f"{where}.deployment: malformed value {environment['deployment']!r}")
        if (environment["deployment"] == "custom") != ("branch_policies" in environment):
            problems.append(f"{where}: branch_policies belong to, and only to, a custom deployment")
        if "branch_policies" in environment:
            _strings(problems, f"{where}.branch_policies", environment["branch_policies"], POLICY)
        for key in ("prevent_self_review", "can_admins_bypass"):
            if key in environment and not isinstance(environment[key], bool):
                problems.append(f"{where}.{key}: malformed value {environment[key]!r}")
    labels = [label.get("name") for label in config.get("label", []) if isinstance(label, dict)]
    if len(labels) != len(set(labels)):
        problems.append("label: duplicated name")
    for index, label in enumerate(config.get("label", [])):
        where = f"label[{index}]"
        if not _keys(problems, where, label, {"name", "color", "description", "paths"}, ("name", "color")):
            continue
        if not re.fullmatch(r"[0-9a-f]{6}", str(label["color"])):
            problems.append(f"{where}.color: malformed value {label['color']!r}")
        if len(str(label.get("description", ""))) > 100:
            problems.append(f"{where}.description: longer than GitHub's 100 characters")
        if "paths" in label:
            _strings(problems, f"{where}.paths", label["paths"])
    project = config.get("project")
    if project is not None:
        allowed = {"owner", "number", "title", "public", "fields", "complete", "options", "view", "workflows"}
        if _keys(problems, "project", project, allowed, ("owner", "number")):
            if not isinstance(project["number"], int):
                problems.append("project.number: expected an integer")
            if not re.fullmatch(r"[A-Za-z0-9-]+", str(project["owner"])):
                problems.append("project.owner: expected an organization login")
            _strings(problems, "project.fields", project.get("fields", []))
            for name, options in project.get("options", {}).items():
                _strings(problems, f"project.options.{name}", options)
            for index, view in enumerate(project.get("view", [])):
                where = f"project.view[{index}]"
                allowed = {"name", "layout", "filter", "group_by", "sort_by"}
                if _keys(problems, where, view, allowed, tuple(allowed)):
                    if view["layout"] not in ("board", "table", "roadmap"):
                        problems.append(f"{where}.layout: malformed value {view['layout']!r}")
                    _strings(problems, f"{where}.group_by", view["group_by"])
                    _strings(problems, f"{where}.sort_by", view["sort_by"], SORT)
            if not all(isinstance(value, bool) for value in project.get("workflows", {}).values()):
                problems.append("project.workflows: expected name = true | false entries")
    organization = config.get("organization", {})
    if _keys(problems, "organization", organization, {"issue_types", "issue_fields"}):
        if not all(isinstance(value, bool) for value in organization.get("issue_types", {}).values()):
            problems.append("organization.issue_types: expected name = true | false entries")
        for name, options in organization.get("issue_fields", {}).items():
            _strings(problems, f"organization.issue_fields.{name}", options)
    if "app" in config and _keys(problems, "app", config["app"], {"slug", "permissions"}, ("slug", "permissions")):
        _access(problems, "app.permissions", config["app"]["permissions"], ACCESS)
    seen: set[tuple[str, str]] = set()
    for index, token in enumerate(config.get("token", [])):
        where = f"token[{index}]"
        if not _keys(problems, where, token, {"workflow", "jobs", "github", "app"}, ("workflow", "jobs", "github")):
            continue
        _strings(problems, f"{where}.jobs", token["jobs"])
        for job in token["jobs"] if isinstance(token["jobs"], list) else ():
            if (token["workflow"], job) in seen:
                problems.append(f"{where}: {token['workflow']} job {job!r} is listed twice")
            seen.add((token["workflow"], job))
        _access(problems, f"{where}.github", token["github"], TOKEN_ACCESS)
        if "app" in token:
            _access(problems, f"{where}.app", token["app"], ACCESS)
    for index, pending in enumerate(config.get("pending", [])):
        _keys(problems, f"pending[{index}]", pending, {"setting", "current", "task"}, ("setting", "current", "task"))
    return problems


def load(path: Path = CONFIG) -> dict:
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    if problems := validate(config):
        raise ConfigError("; ".join(problems))
    return config


# --- live state -------------------------------------------------------------------------------------------------


REFUSED = {
    "project": "the App token for the Project was not issued; check the App's installation and its Projects read "
    "permission",
    "organization": "the App token for organization issue types and fields was not issued; an organization owner "
    "may still need to accept those read permissions for the App's installation",
}


class GhCli:
    """Repository reads/writes use the caller's token. The audit's App tokens read only Project GraphQL and the
    organization's issue-type/field definitions over REST, each with its own token, so a token the workflow could not
    obtain (`refused`) hides only its own reads. A refusal becomes UnavailableError."""

    def __init__(self, project_token=None, organization_token=None, refused=()):
        self.project_token = project_token
        self.organization_token = organization_token
        self.refused = set(refused)

    def _run(self, arguments, payload=None, token=None):
        environment = {**os.environ, "GH_TOKEN": token} if token else None
        try:
            done = subprocess.run(
                ["gh", "api", *arguments],
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                env=environment,
            )
        except FileNotFoundError as error:
            raise UnavailableError("the GitHub CLI (gh) is not installed") from error
        except subprocess.CalledProcessError as error:
            lines = (error.stderr or error.stdout or "").strip().splitlines()
            raise UnavailableError(lines[-1] if lines else f"gh api exited with {error.returncode}") from error
        return json.loads(done.stdout) if done.stdout.strip() else None

    def get(self, path, *, pages=False):
        """One object, or every page of a list endpoint joined into one list."""
        organization_read = re.fullmatch(r"orgs/[^/?]+/(?:issue-types|issue-fields)(?:\?[^#]*)?", path)
        if organization_read and "organization" in self.refused:
            raise UnavailableError(REFUSED["organization"])
        token = self.organization_token if organization_read else None
        if not pages:
            return self._run([path], token=token)
        return [item for page in self._run(["--paginate", "--slurp", path], token=token) for item in page]

    def graphql(self, query, variables):
        arguments = ["graphql", "-f", f"query={query}"]
        for key, value in variables.items():
            if value is not None:
                arguments += ["-F" if isinstance(value, int) else "-f", f"{key}={value}"]
        read = re.match(r"\s*query\b", query)
        if read and "project" in self.refused:
            raise UnavailableError(REFUSED["project"])
        token = self.project_token if read else None
        return self._run(arguments, token=token)["data"]

    def send(self, method, path, body):
        return self._run(["-X", method, path, "--input", "-"], json.dumps(body))


PROJECT_QUERY = """query Project($owner: String!, $number: Int!) { organization(login: $owner) {
  projectV2(number: $number) { id title public
  fields(first: 100) { nodes { ... on ProjectV2FieldCommon { name }
    ... on ProjectV2SingleSelectField { options { name } } } }
  views(first: 100) { nodes { name layout filter
    groupByFields(first: 10) { nodes { ... on ProjectV2FieldCommon { name } } }
    sortByFields(first: 10) { nodes { direction field { ... on ProjectV2FieldCommon { name } } } } } } } } }"""
# Apart, because the weekly job's App token may read the Project but not its workflows (run 40190490225), and GitHub
# refuses a whole query over one field the token may not read.
WORKFLOWS_QUERY = """query ProjectWorkflows($owner: String!, $number: Int!) { organization(login: $owner) {
  projectV2(number: $number) { workflows(first: 100) { nodes { name enabled } } } } }"""
WORKFLOWS_NOTE = (
    "the App's Organization projects: read permission does not include the Project's workflows; a maintainer's "
    "local audit checks them"
)
ITEMS_QUERY = """query ProjectItems($owner: String!, $number: Int!, $after: String) { organization(login: $owner) {
  projectV2(number: $number) { items(first: 50, after: $after) { pageInfo { hasNextPage endCursor }
    nodes { type fieldValues(first: 30) { nodes { ... on ProjectV2ItemFieldSingleSelectValue { name updatedAt
        field { ... on ProjectV2FieldCommon { name } } } } }
      content { ... on Issue { __typename number state url body issueType { name } repository { nameWithOwner }
          labels(first: 50) { nodes { name } }
          issueFieldValues(first: 20) { nodes { ... on IssueFieldSingleSelectValue { name
            field { ... on IssueFieldSingleSelect { name } } } } } }
        ... on PullRequest { __typename number state url repository { nameWithOwner } } } } } } } }"""
ADD_ITEM = """mutation AddItem($project: ID!, $content: ID!) {
  addProjectV2ItemById(input: {projectId: $project, contentId: $content}) { item { id } } }"""


def _sorted(key, value):
    if key not in UNORDERED or not isinstance(value, list):
        return value
    return sorted(value, key=lambda item: json.dumps(item, sort_keys=True))


def read_settings(github, config):
    live = github.get(f"repos/{config['repository']}")
    return {key: live.get(key) for key in config["settings"]}


def read_rulesets(github, config):
    repo = config["repository"]
    found = {}
    for summary in github.get(f"repos/{repo}/rulesets", pages=True):
        ruleset = github.get(f"repos/{repo}/rulesets/{summary['id']}")
        rules = {}
        for rule in ruleset.get("rules", []):
            parameters = rule.get("parameters") or {}
            rules[rule["type"]] = {key: _sorted(key, value) for key, value in parameters.items()}
        names = ruleset.get("conditions", {}).get("ref_name", {})
        found[ruleset["name"]] = {
            "id": ruleset["id"],
            "target": ruleset["target"],
            "enforcement": ruleset["enforcement"],
            "include": sorted(names.get("include", [])),
            "exclude": sorted(names.get("exclude", [])),
            # GitHub returns bypass actors only to callers with write access to the ruleset.
            "bypass": sorted(
                f"{actor['actor_type']} {actor['actor_id']} {actor['bypass_mode']}"
                for actor in ruleset["bypass_actors"]
            )
            if "bypass_actors" in ruleset
            else None,
            "rules": rules,
        }
    return found


def read_environments(github, config):
    repo = config["repository"]
    found = {}
    for environment in github.get(f"repos/{repo}/environments").get("environments", []):
        name = environment["name"]
        reviewers, prevent = [], False
        for rule in environment.get("protection_rules", []):
            if rule["type"] == "required_reviewers":
                prevent = rule.get("prevent_self_review", False)
                for entry in rule.get("reviewers", []):
                    reviewer = entry["reviewer"]
                    reviewers.append(reviewer.get("login") or f"team:{reviewer.get('slug')}")
        policy = environment.get("deployment_branch_policy")
        deployment = "all" if not policy else "protected" if policy.get("protected_branches") else "custom"
        state = {
            "reviewers": sorted(reviewers),
            "prevent_self_review": prevent,
            "deployment": deployment,
            "can_admins_bypass": environment.get("can_admins_bypass"),
        }
        if deployment == "custom":
            policies = github.get(f"repos/{repo}/environments/{urllib.parse.quote(name)}/deployment-branch-policies")
            state["branch_policies"] = sorted(
                f"{entry.get('type', 'branch')} {entry['name']}" for entry in policies.get("branch_policies", [])
            )
        found[name] = state
    return found


def read_labels(github, config):
    repo = config["repository"]
    return {
        label["name"]: {"color": label["color"].lower(), "description": label.get("description") or ""}
        for label in github.get(f"repos/{repo}/labels?per_page=100", pages=True)
    }


def read_project(github, config):
    repo, project = config["repository"], config["project"]
    owner, number = project["owner"], project["number"]
    data = github.graphql(PROJECT_QUERY, {"owner": owner, "number": number})["organization"]["projectV2"]
    if data is None:
        raise UnavailableError(f"Project {owner}/{number} is not visible to this token (needs read:project)")
    fields = [node for node in data["fields"]["nodes"] if node.get("name")]
    state = {
        "id": data["id"],
        "title": data["title"],
        "public": data["public"],
        "fields": sorted(node["name"] for node in fields),
        "options": {
            node["name"]: [option["name"] for option in node["options"]] for node in fields if "options" in node
        },
        "view": {
            view["name"]: {
                "layout": view["layout"].removesuffix("_LAYOUT").lower(),
                "filter": view.get("filter") or "",
                "group_by": [node["name"] for node in view["groupByFields"]["nodes"] if node.get("name")],
                "sort_by": [
                    f"{node['field']['name']} {node['direction'].lower()}"
                    for node in view["sortByFields"]["nodes"]
                    if node.get("field", {}).get("name")
                ],
            }
            for view in data["views"]["nodes"]
        },
    }
    try:
        workflows = github.graphql(WORKFLOWS_QUERY, {"owner": owner, "number": number})["organization"]["projectV2"]
        state["workflows"] = {workflow["name"]: workflow["enabled"] for workflow in workflows["workflows"]["nodes"]}
    except UnavailableError as error:
        state["workflows"] = UnavailableError(f"{str(error).rstrip('.')}: {WORKFLOWS_NOTE}")
    state["entries"], state["hidden"] = read_items(github, owner, number, repo)
    state["items"] = set(state["entries"])
    if project.get("complete"):
        state["open"] = {
            issue["number"]: {"id": issue["node_id"], "url": issue["html_url"]}
            for issue in github.get(f"repos/{repo}/issues?state=open&per_page=100", pages=True)
        }
    return state


def read_items(github, owner, number, repo):
    """This repository's Project items by number (kind, state, Status and since when, type, body, labels and the
    Priority and Effort issue fields), and how many items' content the token may not see."""
    entries, hidden, after = {}, 0, None
    while True:
        page = github.graphql(ITEMS_QUERY, {"owner": owner, "number": number, "after": after})
        page = page["organization"]["projectV2"]["items"]
        for node in page["nodes"]:
            if node.get("type") == "REDACTED":
                hidden += 1
                continue
            content = node.get("content") or {}
            if content.get("repository", {}).get("nameWithOwner") != repo:
                continue
            selects = {
                value["field"]["name"]: value
                for value in node.get("fieldValues", {}).get("nodes", [])
                if value.get("field", {}).get("name")
            }
            fields = {
                value["field"]["name"]: value["name"]
                for value in (content.get("issueFieldValues") or {}).get("nodes", [])
                if value.get("field", {}).get("name")
            }
            entries[content["number"]] = {
                "kind": "pull request" if content.get("__typename") == "PullRequest" else "issue",
                "state": str(content.get("state", "")).lower(),
                "url": content.get("url", ""),
                "type": (content.get("issueType") or {}).get("name"),
                "body": content.get("body") or "",
                "labels": sorted(label["name"] for label in (content.get("labels") or {}).get("nodes", [])),
                "status": selects.get("Status", {}).get("name"),
                "since": selects.get("Status", {}).get("updatedAt"),
                "priority": fields.get("Priority"),
                "effort": fields.get("Effort"),
            }
        if not page["pageInfo"]["hasNextPage"]:
            return entries, hidden
        after = page["pageInfo"]["endCursor"]


def read_organization(github, config):
    owner, expected = config["repository"].split("/")[0], config.get("organization", {})
    state = {}
    try:
        types = github.get(f"orgs/{owner}/issue-types", pages=True)
        if not types:
            # As for issue fields: an empty list is also what a token that cannot see the types receives.
            raise UnavailableError(
                "the token lists no organization issue types; an organization owner can confirm them"
            )
        state["issue_types"] = {kind["name"]: kind["is_enabled"] for kind in types}
    except UnavailableError as error:
        state["issue_types"] = UnavailableError(str(error))
    if expected.get("issue_fields"):
        try:
            fields = github.get(f"orgs/{owner}/issue-fields", pages=True)
        except UnavailableError as error:
            fields = UnavailableError(str(error))
        if isinstance(fields, list) and not fields:
            # GitHub returns an empty list both for no fields and for fields this token cannot see.
            fields = UnavailableError(
                "the token lists no organization issue fields; an organization owner can confirm them"
            )
        state["issue_fields"] = (
            fields
            if isinstance(fields, UnavailableError)
            else {entry["name"]: [option["name"] for option in entry.get("options", [])] for entry in fields}
        )
    return state


def read_app(github, config):
    return {"permissions": github.get(f"apps/{config['app']['slug']}").get("permissions", {})}


# --- comparison -------------------------------------------------------------------------------------------------


@dataclass
class Finding:
    section: str
    setting: str
    status: str  # drift, missing, undeclared, attention, pending, done, unavailable
    expected: object = None
    actual: object = None
    ui: str = ""
    command: str = ""
    note: str = ""
    fix: dict | None = field(default=None, repr=False)

    @property
    def fails(self) -> bool:
        return self.status in FAILING


FAILING = ("drift", "missing", "undeclared", "attention")
STATUSES = (*FAILING, "pending", "done", "unavailable")


def pending_kept(config, prefix, declared, live, setting):
    """What a command for `setting` applies: the declared state below `prefix`, except that each pending target the
    finding does not address keeps its live value, so fixing one difference never applies an approved target before
    its task. Where the live state lacks the target's containing table (the object or rule does not exist yet), the
    recorded current value is kept instead. A target at or above `setting` is addressed by the finding itself."""
    result = copy.deepcopy(declared)
    for entry in config.get("pending", []):
        target = entry["setting"]
        if not target.startswith(prefix) or target == setting or setting.startswith(target + "."):
            continue
        *parents, last = target.removeprefix(prefix).split(".")
        place, source = result, live
        for part in parents:
            place = place.get(part) if isinstance(place, dict) else None
            source = source.get(part) if isinstance(source, dict) else None
        if not isinstance(place, dict):
            continue
        value = source.get(last, ABSENT) if isinstance(source, dict) else entry["current"]
        if value == ABSENT:
            place.pop(last, None)
        else:
            place[last] = copy.deepcopy(value)
    return result


def ruleset_fix(config, ruleset, live, setting):
    name = ruleset["name"]
    rules = pending_kept(config, f"ruleset.{name}.rules.", ruleset["rules"], live and live["rules"], setting)
    actors = [entry.split() for entry in ruleset["bypass"]]
    body = {
        "name": name,
        "target": ruleset["target"],
        "enforcement": ruleset["enforcement"],
        "conditions": {"ref_name": {"include": ruleset["include"], "exclude": ruleset["exclude"]}},
        "bypass_actors": [
            {"actor_type": kind, "actor_id": int(ident), "bypass_mode": mode} for kind, ident, mode in actors
        ],
        "rules": [{"type": kind, **({"parameters": value} if value else {})} for kind, value in rules.items()],
    }
    return {"body": body}


def environment_fix(config, name, declared, live, setting):
    environment = pending_kept(config, f"environment.{name}.", declared, live, setting)
    deployment = environment["deployment"]
    reviewers = [
        {"type": "Team", "slug": reviewer.removeprefix("team:")}
        if reviewer.startswith("team:")
        else {"type": "User", "login": reviewer}
        for reviewer in environment["reviewers"]
    ]
    body = {
        "reviewers": reviewers,
        "prevent_self_review": environment.get("prevent_self_review", False),
        "can_admins_bypass": environment["can_admins_bypass"],
        "deployment_branch_policy": None
        if deployment == "all"
        else {"protected_branches": deployment == "protected", "custom_branch_policies": deployment == "custom"},
    }
    return {"body": body}


def compare_settings(config, actual):
    repo = config["repository"]
    # GitHub returns these as null to a token that may not see them (the weekly job's GITHUB_TOKEN, run 40190490225):
    # unknown, so neither drift nor matching.
    hidden = [
        key for key, expected in config.get("settings", {}).items() if actual.get(key) is None and expected is not None
    ]
    if hidden:
        note = f"GitHub returns {', '.join(hidden)} as null to this token; a maintainer's local audit reads them"
        yield Finding("settings", "settings", "unavailable", ui=UI["settings"], note=note)
    for key, expected in config.get("settings", {}).items():
        if key not in hidden and actual.get(key) != expected:
            flag, value = ("-F", json.dumps(expected)) if isinstance(expected, bool) else ("-f", expected)
            yield Finding(
                "settings",
                f"settings.{key}",
                "drift",
                expected,
                actual.get(key),
                UI["settings"],
                shlex.join(["gh", "api", "-X", "PATCH", f"repos/{repo}", flag, f"{key}={value}"]),
            )


def compare_rulesets(config, actual):
    repo = config["repository"]
    expected_names = {ruleset["name"] for ruleset in config.get("ruleset", [])}
    for ruleset in config.get("ruleset", []):
        name, live = ruleset["name"], actual.get(ruleset["name"])
        ui = UI["rulesets"].format(name=name)
        if live is None:
            yield Finding(
                "rulesets",
                f"ruleset.{name}",
                "missing",
                "declared",
                ABSENT,
                ui,
                f"gh api -X POST repos/{repo}/rulesets --input <ruleset body in the JSON report>",
                fix=ruleset_fix(config, ruleset, None, f"ruleset.{name}"),
            )
            continue
        if live["bypass"] is None:
            note = "Bypass actors are shown only to a token with write access to the ruleset."
            yield Finding("rulesets", f"ruleset.{name}.bypass", "unavailable", ui=ui, note=note)
        differences = [
            (f"ruleset.{name}.{key}", ruleset[key], live[key])
            for key in ("target", "enforcement", "include", "exclude", "bypass")
            if live[key] is not None and _sorted(key, ruleset[key]) != live[key]
        ]
        for kind, parameters in ruleset["rules"].items():
            setting = f"ruleset.{name}.rules.{kind}"
            if kind not in live["rules"]:
                differences.append((setting, parameters or "present", ABSENT))
                continue
            # Parameters on either side: one that GitHub adds or a person sets in the UI is reported, never dropped.
            current = live["rules"][kind]
            differences += [
                (f"{setting}.{key}", parameters.get(key, ABSENT), current.get(key, ABSENT))
                for key in sorted(set(parameters) | set(current))
                if _sorted(key, parameters.get(key, ABSENT)) != current.get(key, ABSENT)
            ]
        differences += [
            (f"ruleset.{name}.rules.{kind}", ABSENT, "present")
            for kind in sorted(set(live["rules"]) - set(ruleset["rules"]))
        ]
        command = f"gh api -X PUT repos/{repo}/rulesets/{live['id']} --input <ruleset body in the JSON report>"
        for setting, expected, value in differences:
            fix = ruleset_fix(config, ruleset, live, setting)
            yield Finding("rulesets", setting, "drift", expected, value, ui, command, fix=fix)
    for name in sorted(set(actual) - expected_names):
        yield Finding(
            "rulesets",
            f"ruleset.{name}",
            "undeclared",
            ABSENT,
            "present",
            UI["rulesets"].format(name=name),
            "",
            "Declare the ruleset in .github/repository.toml or remove it in the UI.",
        )


def compare_environments(config, actual):
    repo = config["repository"]
    expected = config.get("environment", {})
    for name, environment in expected.items():
        ui = UI["environments"].format(name=name)
        path = f"repos/{repo}/environments/{urllib.parse.quote(name, safe='')}"
        command = (
            f"gh api -X PUT {shlex.quote(path)} --input <environment body in the JSON report>; "
            f"reviewers need their IDs (gh api users/LOGIN --jq .id, or orgs/ORG/teams/SLUG --jq .id for a team)"
        )
        policies = f"gh api -X POST {shlex.quote(path + '/deployment-branch-policies')} -f name=NAME -f type=TYPE"
        live = actual.get(name)
        if live is None:
            fix = environment_fix(config, name, environment, None, f"environment.{name}")
            yield Finding("environments", f"environment.{name}", "missing", "declared", ABSENT, ui, command, fix=fix)
            continue
        for key, value in environment.items():
            if _sorted(key, value) != live.get(key, ABSENT):
                setting = f"environment.{name}.{key}"
                yield Finding(
                    "environments",
                    setting,
                    "drift",
                    value,
                    live.get(key, ABSENT),
                    ui,
                    policies if key == "branch_policies" else command,
                    fix=environment_fix(config, name, environment, live, setting),
                )
    for name in sorted(set(actual) - set(expected)):
        yield Finding(
            "environments",
            f"environment.{name}",
            "undeclared",
            ABSENT,
            "present",
            UI["environments"].format(name=name),
            "",
            "Declare the environment in .github/repository.toml or delete it in the UI.",
        )


def compare_labels(config, actual):
    repo = config["repository"]
    for label in config.get("label", []):
        name, color, description = label["name"], label["color"], label.get("description", "")
        live = actual.get(name)
        create = {
            "method": "POST",
            "path": f"repos/{repo}/labels",
            "body": {"name": name, "color": color, "description": description},
        }
        if live is None:
            yield Finding(
                "labels",
                f"label.{name}",
                "missing",
                f"#{color} {description}",
                ABSENT,
                UI["labels"],
                shlex.join(["gh", "label", "create", name, "--color", color, "--description", description]),
                fix=create,
            )
            continue
        if live != {"color": color, "description": description}:
            update = {
                "method": "PATCH",
                "path": f"repos/{repo}/labels/{urllib.parse.quote(name)}",
                "body": {"color": color, "description": description},
            }
            yield Finding(
                "labels",
                f"label.{name}",
                "drift",
                f"#{color} {description}",
                f"#{live['color']} {live['description']}",
                UI["labels"],
                shlex.join(["gh", "label", "edit", name, "--color", color, "--description", description]),
                fix=update,
            )
    declared = {label["name"] for label in config.get("label", [])}
    for name in sorted(set(actual) - declared):
        yield Finding(
            "labels",
            f"label.{name}",
            "undeclared",
            ABSENT,
            "present",
            UI["labels"],
            "",
            "Declare the label in .github/repository.toml or delete it; the audit never deletes a label.",
        )


def compare_project(config, actual, now=None):
    project = config["project"]
    ui = UI["project"].format(title=project.get("title", project["number"]))
    owner, number = project["owner"], project["number"]
    view_only = "The API cannot change Project settings, views or workflows; change them in the UI."
    for key in ("title", "public"):
        if key in project and project[key] != actual[key]:
            yield Finding("project", f"project.{key}", "drift", project[key], actual[key], ui, "", view_only)
    if "fields" in project and sorted(project["fields"]) != actual["fields"]:
        yield Finding(
            "project", "project.fields", "drift", sorted(project["fields"]), actual["fields"], ui, "", view_only
        )
    for name, options in project.get("options", {}).items():
        if options != actual["options"].get(name, ABSENT):
            yield Finding(
                "project",
                f"project.options.{name}",
                "drift",
                options,
                actual["options"].get(name, ABSENT),
                ui,
                "",
                view_only,
            )
    views = {view["name"]: view for view in project.get("view", [])}
    for name, view in views.items():
        live = actual["view"].get(name)
        if live is None:
            yield Finding("project", f"project.view.{name}", "missing", "declared", ABSENT, ui, "", view_only)
            continue
        for key in ("layout", "filter", "group_by", "sort_by"):
            if view[key] != live[key]:
                yield Finding("project", f"project.view.{name}.{key}", "drift", view[key], live[key], ui, "", view_only)
    for name in sorted(set(actual["view"]) - set(views)):
        yield Finding("project", f"project.view.{name}", "undeclared", ABSENT, "present", ui, "", view_only)
    if isinstance(actual["workflows"], UnavailableError):
        # Only the workflows are unknown; the fields, views and items above and below are still audited.
        yield Finding("project", "project.workflows", "unavailable", ui=ui, note=str(actual["workflows"]))
    else:
        for name, enabled in project.get("workflows", {}).items():
            if actual["workflows"].get(name, ABSENT) != enabled:
                yield Finding(
                    "project",
                    f"project.workflows.{name}",
                    "drift",
                    enabled,
                    actual["workflows"].get(name, ABSENT),
                    ui,
                    "",
                    view_only,
                )
        for name in sorted(set(actual["workflows"]) - set(project.get("workflows", {}))):
            yield Finding(
                "project",
                f"project.workflows.{name}",
                "undeclared",
                ABSENT,
                actual["workflows"][name],
                ui,
                "",
                view_only,
            )
    if actual["hidden"]:
        # An item the token cannot see is neither missing nor in order, so nothing is judged from the items.
        note = f"{actual['hidden']} items' issues and pull requests are hidden from this token; it needs Issues read."
        yield Finding("project", "project.items", "unavailable", ui=ui, note=note)
        return
    if project.get("complete"):
        for number_, issue in sorted(actual["open"].items()):
            if number_ not in actual["items"]:
                yield Finding(
                    "project",
                    f"project.items.#{number_}",
                    "missing",
                    "an item",
                    ABSENT,
                    ui,
                    shlex.join(["gh", "project", "item-add", str(number), "--owner", owner, "--url", issue["url"]]),
                    fix={"mutation": ADD_ITEM, "variables": {"project": actual["id"], "content": issue["id"]}},
                )
    yield from item_findings(config, actual["entries"], now or clock())


def clock():
    return datetime.now(UTC)


# The Project's Status options the checks read, and how long an item may wait in them.
TRIAGE, READY, DONE = "Needs triage", "Ready", "Done"
TRIAGE_DAYS, URGENT_DAYS = 14, 3


def unready(item):
    """What a Ready issue lacks from the definition of Ready; empty when it meets it."""
    lacking = [] if item["type"] else ["Issue Type"]
    if not any(label.startswith("area:") for label in item["labels"]):
        lacking.append("an area:* label")
    lacking += [name for name in ("Priority", "Effort") if not item[name.lower()]]
    shape = plan_issue_shape.engine().readiness(item["body"])
    if not shape["ready"]:
        parts = [f"no {name}" for name in shape["missing"] + shape["missing_metadata"]]
        parts += [f"empty {name}" for name in shape["empty"]]
        lacking.append(f"the planned-issue shape ({'; '.join(parts) or shape['shape_findings'][0]['detail']})")
    return lacking


def attention(number, item, check, expected, actual, *, command="", note=""):
    """A Project item that needs a person, linked from the finding."""
    setting = f"project.item.#{number}.{check}"
    return Finding("project", setting, "attention", expected, actual, item["url"], command, note)


def item_findings(config, entries, now):
    """Items that need a person: wrong state, missing or contradicting type, incomplete Ready, overdue triage and
    stalled Urgent work. Each links the item and says how to fix it."""
    repo = config["repository"]
    for number, item in sorted(entries.items()):
        closed = item["state"] in ("closed", "merged")
        if item["status"] and closed != (item["status"] == DONE):
            note = "The Project's Item closed and Item reopened automations keep this; set the Status by hand."
            yield attention(number, item, "status", DONE if closed else f"not {DONE}", item["status"], note=note)
        if item["kind"] != "issue" or closed:
            continue
        if not item["type"]:
            command = shlex.join(["gh", "api", "-X", "PATCH", f"repos/{repo}/issues/{number}", "-f", "type=TYPE"])
            note = "Set the Issue Type in the issue's sidebar."
            yield attention(number, item, "type", "Bug, Feature or Task", ABSENT, command=command, note=note)
        written = plan_issue_shape.body_type(item["body"])
        if item["type"] and written and written != item["type"].lower():
            note = "The body's Type row and the Issue Type disagree; correct whichever is wrong."
            yield attention(number, item, "body-type", item["type"].lower(), written, note=note)
        days = (now - datetime.fromisoformat(item["since"])).days if item["since"] else 0
        if item["status"] == TRIAGE and days > TRIAGE_DAYS:
            note = "Triage it in the Project's Triage view: set the type, an area label, Priority and Effort."
            yield attention(
                number, item, "triage", f"triaged within {TRIAGE_DAYS} days", f"waiting {days} days", note=note
            )
        if item["priority"] == "Urgent" and item["status"] in (TRIAGE, READY) and days > URGENT_DAYS:
            note = "Urgent work starts within three days: assign it or lower its Priority."
            yield attention(
                number, item, "urgent", f"started within {URGENT_DAYS} days", f"not started for {days} days", note=note
            )
        if item["status"] == READY and (lacking := unready(item)):
            note = "Complete it (shape the body with /aiscr-plan-issue) or move it back to Needs triage."
            yield attention(number, item, "ready", "the definition of Ready", lacking, note=note)


def compare_organization(config, actual):
    expected = config.get("organization", {})
    owner = config["repository"].split("/")[0]
    ui = UI["organization"]
    for part, command in (
        ("issue_types", f"gh api orgs/{owner}/issue-types"),
        ("issue_fields", f"gh api orgs/{owner}/issue-fields"),
    ):
        if part not in expected:
            continue
        live = actual.get(part)
        if isinstance(live, UnavailableError):
            yield Finding("organization", f"organization.{part}", "unavailable", None, None, ui, command, str(live))
            continue
        for name, value in expected[part].items():
            if live.get(name, ABSENT) != value:
                yield Finding(
                    "organization", f"organization.{part}.{name}", "drift", value, live.get(name, ABSENT), ui, command
                )
        for name in sorted(set(live) - set(expected[part])):
            yield Finding("organization", f"organization.{part}.{name}", "undeclared", ABSENT, live[name], ui, command)


def compare_app(config, actual):
    app = config["app"]
    if actual["permissions"] != app["permissions"]:
        yield Finding(
            "app",
            "app.permissions",
            "drift",
            app["permissions"],
            actual["permissions"],
            UI["app"].format(slug=app["slug"]),
            "",
            "Only the App's owner can change its registered permissions; installations then accept them.",
        )


SECTION_OF = {
    "settings": "settings",
    "ruleset": "rulesets",
    "environment": "environments",
    "label": "labels",
    "project": "project",
    "organization": "organization",
    "app": "app",
}
COMPARE = {
    "settings": compare_settings,
    "rulesets": compare_rulesets,
    "environments": compare_environments,
    "labels": compare_labels,
    "project": compare_project,
    "organization": compare_organization,
    "app": compare_app,
}


def apply_pending(config, findings, audited):
    """Approved targets still at their recorded current value are pending; reached targets are done."""
    pending = {entry["setting"]: entry for entry in config.get("pending", [])}
    for finding in findings:
        entry = pending.get(finding.setting)
        if entry and finding.actual == _sorted(finding.setting.rsplit(".", 1)[-1], entry["current"]):
            finding.status, finding.note = "pending", f"Approved target, not yet applied: task {entry['task']}"
    unavailable = {finding.section for finding in findings if finding.status == "unavailable"}
    differing = {finding.setting for finding in findings}
    for setting, entry in pending.items():
        section = SECTION_OF[setting.split(".")[0]]
        if setting not in differing and section in audited and section not in unavailable:
            note = f"The target holds: remove this pending entry ({entry['task']})."
            findings.append(Finding(section, setting, "done", note=note))
    return findings


def where(section, config):
    """The UI path of a whole section: an object's path stops before the object's name."""
    project, app = config.get("project", {}), config.get("app", {})
    return UI[section].removesuffix(" → {name}").format(title=project.get("title", ""), slug=app.get("slug", ""))


READ = {
    "settings": read_settings,
    "rulesets": read_rulesets,
    "environments": read_environments,
    "labels": read_labels,
    "project": read_project,
    "organization": read_organization,
    "app": read_app,
}


def audit(config, github, sections=SECTIONS, now=None, backfill=None) -> list[Finding]:
    findings: list[Finding] = []
    if backfill is not None:
        try:
            findings.extend(compare_backfill(config, read_backfill(github, config), backfill))
        except UnavailableError as error:
            findings.append(Finding("backfill", "backfill", "unavailable", note=str(error)))
    audited = {section for section in sections if section not in ("project", "app") or config.get(section)}
    for section in [section for section in sections if section in audited]:
        try:
            actual = READ[section](github, config)
        except UnavailableError as error:
            findings.append(Finding(section, section, "unavailable", ui=where(section, config), note=str(error)))
            continue
        timing = {"now": now} if section == "project" else {}
        findings.extend(COMPARE[section](config, actual, **timing))
    return apply_pending(config, findings, audited)


def fix(findings, github) -> list[str]:
    """Create or update declared labels, add missing Project items and, from a reviewed backfill mapping, add its
    labels and Issue Types to open issues; nothing else is ever written."""
    failures = []
    for finding in findings:
        if finding.status not in ("missing", "drift") or not finding.fix:
            continue
        try:
            if finding.section in ("labels", "backfill"):
                github.send(finding.fix["method"], finding.fix["path"], finding.fix["body"])
            elif finding.section == "project" and "mutation" in finding.fix:
                github.graphql(finding.fix["mutation"], finding.fix["variables"])
        except UnavailableError as error:
            failures.append(f"{finding.setting}: {error}")
    return failures


# --- backfill ---------------------------------------------------------------------------------------------------


def load_backfill(path: Path, config: dict) -> list[dict]:
    """The reviewed mapping (`[[issue]]` with `number`, `type` and `area`), checked against the declared state."""
    try:
        entries = tomllib.loads(path.read_text(encoding="utf-8")).get("issue", [])
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    types = set(config.get("organization", {}).get("issue_types", {}))
    areas = {label["name"] for label in config.get("label", []) if label["name"].startswith("area:")}
    problems, numbers = [], set()
    for index, entry in enumerate(entries):
        where = f"{path.name}: issue[{index}]"
        if not _keys(problems, where, entry, {"number", "type", "area"}, ("number", "type", "area")):
            continue
        if not isinstance(entry["number"], int) or entry["number"] in numbers:
            problems.append(f"{where}.number: expected a unique issue number")
        numbers.add(entry["number"])
        if entry["type"] not in types:
            problems.append(f"{where}.type: {entry['type']!r} is not a declared issue type")
        if not isinstance(entry["area"], list) or not entry["area"] or not set(entry["area"]) <= areas:
            problems.append(f"{where}.area: expected one or more declared area:* labels")
    if problems:
        raise ConfigError("; ".join(problems))
    return entries


def read_backfill(github, config):
    issues = github.get(f"repos/{config['repository']}/issues?state=open&per_page=100", pages=True)
    return {
        "issues": {issue["number"]: issue for issue in issues if "pull_request" not in issue},
        "labels": set(read_labels(github, config)),
    }


def compare_backfill(config, actual, mapping):
    """Each mapped issue's missing Issue Type or area labels as a fix; an unmapped open issue is listed for triage.
    GitHub creates a label it does not know when one is added to an issue, so labels wait until all exist."""
    repo = config["repository"]
    absent = sorted({name for entry in mapping for name in entry["area"]} - actual["labels"])
    if absent:
        note = "Create the declared labels first (`--section labels --fix`); until then no area label is added."
        yield Finding("backfill", "backfill.labels", "missing", absent, ABSENT, UI["labels"], "", note)
    for entry in mapping:
        number, issue = entry["number"], actual["issues"].get(entry["number"])
        if issue is None:
            note = "Not an open issue any more; it needs no backfill."
            yield Finding("backfill", f"backfill.#{number}", "done", note=note)
            continue
        current = (issue.get("type") or {}).get("name")
        path = f"repos/{repo}/issues/{number}"
        if current != entry["type"]:
            command = shlex.join(["gh", "api", "-X", "PATCH", path, "-f", f"type={entry['type']}"])
            fix = {"method": "PATCH", "path": path, "body": {"type": entry["type"]}}
            setting = f"backfill.#{number}.type"
            url = issue["html_url"]
            yield Finding("backfill", setting, "missing", entry["type"], current or ABSENT, url, command, fix=fix)
        present = {label["name"] for label in issue.get("labels", [])}
        if not absent and (missing := [name for name in entry["area"] if name not in present]):
            command = shlex.join(["gh", "issue", "edit", str(number), "--add-label", ",".join(missing)])
            fix = {"method": "POST", "path": f"{path}/labels", "body": {"labels": missing}}
            setting, url = f"backfill.#{number}.labels", issue["html_url"]
            yield Finding("backfill", setting, "missing", entry["area"], sorted(present), url, command, fix=fix)
    mapped = {entry["number"] for entry in mapping}
    for number, issue in sorted(actual["issues"].items()):
        if number not in mapped:
            note = "Opened after the mapping was reviewed: triage it in the Project's Triage view."
            yield Finding("backfill", f"backfill.#{number}", "undeclared", ABSENT, "open", issue["html_url"], "", note)


# --- digest -----------------------------------------------------------------------------------------------------

DIGEST_ITEMS = 25
OWNER_STEP = (
    "An organization owner accepts the fair-guide-actions App's request to read Projects (Organization settings → "
    "GitHub Apps → fair-guide-actions), and the next weekly run reads Project #1 again."
)
# The digest is public. These checks read the Project's own Status, so the digest shows only how many items they
# found; the Project's views show which.
COUNTED = {
    "ready": "Ready issue(s) do not meet the definition of Ready",
    "triage": f"issue(s) have waited over {TRIAGE_DAYS} days for triage",
    "status": "item(s) have a Status that does not match whether they are open",
}


def digest_line(finding):
    """One public line for a finding, or None when the finding is only counted."""
    check = finding.setting.rsplit(".", 1)[-1]
    if finding.setting.startswith("project.item."):
        number = finding.setting.split(".")[2]
        return {
            "type": f"{number} has no Issue Type.",
            "body-type": f"{number}: the body says `{finding.actual}`, the Issue Type `{finding.expected}`.",
            "urgent": f"{number} is Urgent and has not started ({finding.actual}).",
        }.get(check)
    if finding.setting.startswith("project.items."):
        return f"{finding.setting.removeprefix('project.items.')} is not in Project #1."
    return f"`{finding.setting}`: expected {json.dumps(finding.expected, ensure_ascii=False)}, found " + json.dumps(
        finding.actual, ensure_ascii=False
    )


def digest(findings) -> str:
    """The digest's "Project and settings" section in Markdown, bounded to a few dozen lines. It is the only output
    the weekly job publishes: the full report names Project-only values, and a public repository's logs and
    artifacts are public."""
    failing = [finding for finding in findings if finding.fails]
    lines = ["## Project and settings", ""]
    listed = [line for line in map(digest_line, failing) if line]
    counted = {check: 0 for check in COUNTED}
    for finding in failing:
        if (check := finding.setting.rsplit(".", 1)[-1]) in counted and finding.setting.startswith("project.item."):
            counted[check] += 1
    if not failing:
        lines.append("Every readable setting and Project item matches the reviewed state.")
    lines += [f"- {line}" for line in listed[:DIGEST_ITEMS]]
    if len(listed) > DIGEST_ITEMS:
        lines.append(f"- … and {len(listed) - DIGEST_ITEMS} more; `python scripts/audit_repository.py` lists them all.")
    lines += [f"- {count} {COUNTED[check]}; see the Project's views." for check, count in counted.items() if count]
    unavailable = [finding for finding in findings if finding.status == "unavailable"]
    if unavailable:
        lines += ["", "Unavailable to the audit's token:"]
        for finding in unavailable:
            step = f" {OWNER_STEP}" if finding.setting == "project" else ""
            lines.append(f"- `{finding.setting}`: {finding.note}.{step}")
    return "\n".join(lines) + "\n"


# --- report -----------------------------------------------------------------------------------------------------


def render(findings, sections) -> str:
    counts = {status: sum(f.status == status for f in findings) for status in STATUSES}
    lines = [
        "Repository settings audit against .github/repository.toml",
        "Sections: " + ", ".join(sections) + ".",
        "",
    ]
    for finding in findings:
        lines.append(f"[{finding.status.upper()}] {finding.setting}")
        if finding.status not in ("unavailable", "done"):
            lines.append(f"    expected: {json.dumps(finding.expected, ensure_ascii=False)}")
            lines.append(f"    actual:   {json.dumps(finding.actual, ensure_ascii=False)}")
        if finding.ui:
            lines.append(f"    where:    {finding.ui}")
        if finding.command:
            lines.append(f"    command:  {finding.command}")
        if finding.note:
            lines.append(f"    note:     {finding.note}")
    failing = [f for f in findings if f.fails]
    lines += [
        "",
        ", ".join(f"{count} {status}" for status, count in counts.items()) + ".",
        "Next: a maintainer reviews each drift, undeclared object and missing item, and fixes each item that needs "
        "attention at its link; `--fix` creates or updates the declared labels and adds missing Project items, and "
        "everything else is changed in the UI or with the command shown, then confirmed by a new audit."
        if failing
        else "Every readable section matches the reviewed state; unavailable sections need a token that can read them.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, github=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=CONFIG, help=argparse.SUPPRESS)
    parser.add_argument("--section", choices=SECTIONS, action="append", help="audit only these sections")
    parser.add_argument("--json", type=Path, help="also write the findings as JSON")
    parser.add_argument("--digest", type=Path, help="also write the digest's Project and settings section (Markdown)")
    parser.add_argument(
        "--backfill",
        type=Path,
        help="compare open issues with a reviewed mapping of Issue Types and area labels, instead of the sections",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="create or update declared labels; add missing Project items; apply a --backfill mapping",
    )
    parser.add_argument("--check-config", action="store_true", help="validate the expected state offline and stop")
    args = parser.parse_args(argv)
    try:
        config = load(args.config)
        backfill = load_backfill(args.backfill, config) if args.backfill else None
    except ConfigError as error:
        print(f"audit_repository: {error}", file=sys.stderr)
        return 1
    if args.check_config:
        print(f"audit_repository: {args.config.name} is valid")
        return 0
    # The workflow passes each App-token step's outcome; "failure" means that token could not be issued.
    refused = [part for part in REFUSED if os.environ.get(f"GH_{part.upper()}_TOKEN_OUTCOME") == "failure"]
    github = github or GhCli(
        os.environ.get("GH_PROJECT_TOKEN") or None, os.environ.get("GH_ORGANIZATION_TOKEN") or None, refused
    )
    sections = tuple(args.section or (() if backfill is not None else SECTIONS))
    findings = audit(config, github, sections, backfill=backfill)
    failures = []
    if args.fix:
        failures = fix(findings, github)
        findings = audit(config, github, sections, backfill=backfill)
    sys.stdout.write(render(findings, sections + (("backfill",) if backfill is not None else ())))
    if args.digest:
        args.digest.parent.mkdir(parents=True, exist_ok=True)
        args.digest.write_text(digest(findings), encoding="utf-8")
    for failure in failures:
        print(f"FIX FAILED: {failure}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {"findings": [{k: v for k, v in asdict(f).items()} for f in findings], "fix_failures": failures}
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + "\n", encoding="utf-8")
    return 1 if failures or any(finding.fails for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
