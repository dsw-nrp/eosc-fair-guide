#!/usr/bin/env python3
"""Compare the repository's live GitHub settings with the reviewed expected state in `.github/repository.toml`.

    python scripts/audit_repository.py [--section NAME ...] [--json PATH] [--fix]
    python scripts/audit_repository.py --check-config

Reads, through the GitHub CLI (``gh``) and the caller's token, the repository's merge settings, rulesets,
environments and labels, Project #1 (fields, options, views, built-in automations and whether every open issue and
pull request is an item), the organization's issue types and issue fields, and the GitHub App's registered
permissions. Each difference names the setting, the expected and actual values, the UI path and an equivalent
command. A section the token cannot read is reported as unavailable, never as matching. An approved target recorded
under ``[[pending]]`` is reported as pending while the live value still equals its recorded current value.

The audit writes nothing unless ``--fix`` is given, and ``--fix`` only creates or updates the declared labels and adds
missing open issues and pull requests to the Project. It never deletes a label, never changes a Project field value
and never changes a setting: people apply those, and the next audit confirms them. ``--check-config`` validates the
file offline. Exit status 1 means drift, an undeclared object or a failed fix; unavailable and pending sections are
listed without failing.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shlex
import subprocess
import sys
import tomllib
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path

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
    if not isinstance(table, dict):
        problems.append(f"{where}: expected a table")
        return False
    problems += [f"{where}: unknown key {key!r}" for key in table if key not in allowed]
    problems += [f"{where}: missing key {key!r}" for key in required if key not in table]
    return True


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


class GhCli:
    """The live state through `gh api` with the caller's token; a refusal becomes UnavailableError."""

    def _run(self, arguments, payload=None):
        try:
            done = subprocess.run(
                ["gh", "api", *arguments], input=payload, capture_output=True, text=True, encoding="utf-8", check=True
            )
        except FileNotFoundError as error:
            raise UnavailableError("the GitHub CLI (gh) is not installed") from error
        except subprocess.CalledProcessError as error:
            lines = (error.stderr or error.stdout or "").strip().splitlines()
            raise UnavailableError(lines[-1] if lines else f"gh api exited with {error.returncode}") from error
        return json.loads(done.stdout) if done.stdout.strip() else None

    def get(self, path, *, pages=False):
        """One object, or every page of a list endpoint joined into one list."""
        if not pages:
            return self._run([path])
        return [item for page in self._run(["--paginate", "--slurp", path]) for item in page]

    def graphql(self, query, variables):
        arguments = ["graphql", "-f", f"query={query}"]
        for key, value in variables.items():
            if value is not None:
                arguments += ["-F" if isinstance(value, int) else "-f", f"{key}={value}"]
        return self._run(arguments)["data"]

    def send(self, method, path, body):
        return self._run(["-X", method, path, "--input", "-"], json.dumps(body))


PROJECT_QUERY = """query Project($owner: String!, $number: Int!) { organization(login: $owner) {
  projectV2(number: $number) { id title public
  fields(first: 100) { nodes { ... on ProjectV2FieldCommon { name }
    ... on ProjectV2SingleSelectField { options { name } } } }
  views(first: 100) { nodes { name layout filter
    groupByFields(first: 10) { nodes { ... on ProjectV2FieldCommon { name } } }
    sortByFields(first: 10) { nodes { direction field { ... on ProjectV2FieldCommon { name } } } } } }
  workflows(first: 100) { nodes { name enabled } } } } }"""
ITEMS_QUERY = """query ProjectItems($owner: String!, $number: Int!, $after: String) { organization(login: $owner) {
  projectV2(number: $number) { items(first: 100, after: $after) { pageInfo { hasNextPage endCursor }
    nodes { content { ... on Issue { number repository { nameWithOwner } }
      ... on PullRequest { number repository { nameWithOwner } } } } } } } }"""
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
        "workflows": {workflow["name"]: workflow["enabled"] for workflow in data["workflows"]["nodes"]},
    }
    if project.get("complete"):
        items, after = set(), None
        while True:
            page = github.graphql(ITEMS_QUERY, {"owner": owner, "number": number, "after": after})
            page = page["organization"]["projectV2"]["items"]
            items |= {
                node["content"]["number"]
                for node in page["nodes"]
                if node.get("content") and node["content"].get("repository", {}).get("nameWithOwner") == repo
            }
            if not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]
        state["open"] = {
            issue["number"]: {"id": issue["node_id"], "url": issue["html_url"]}
            for issue in github.get(f"repos/{repo}/issues?state=open&per_page=100", pages=True)
        }
        state["items"] = items
    return state


def read_organization(github, config):
    owner, expected = config["repository"].split("/")[0], config.get("organization", {})
    state = {}
    try:
        state["issue_types"] = {
            kind["name"]: kind["is_enabled"] for kind in github.get(f"orgs/{owner}/issue-types", pages=True)
        }
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
    status: str  # drift, missing, undeclared, pending, done, unavailable
    expected: object = None
    actual: object = None
    ui: str = ""
    command: str = ""
    note: str = ""
    fix: dict | None = field(default=None, repr=False)

    @property
    def fails(self) -> bool:
        return self.status in ("drift", "missing", "undeclared")


def keep_live(declared, live, paths):
    """`declared` with each dotted path in `paths` at its value in `live`, or left out where `live` has none."""
    result = copy.deepcopy(declared)
    for path in paths:
        *parents, last = path.split(".")
        target, source = result, live
        for part in parents:
            target = target.get(part) if isinstance(target, dict) else None
            source = source.get(part) if isinstance(source, dict) else None
        if not isinstance(target, dict):
            continue
        if isinstance(source, dict) and last in source:
            target[last] = copy.deepcopy(source[last])
        else:
            target.pop(last, None)
    return result


def pending_kept(config, prefix, declared, live, setting):
    """What a command for `setting` applies: the declared state, but every other pending setting below `prefix` keeps
    its live value, so fixing one difference never applies an approved target before its task."""
    paths = {
        entry["setting"].removeprefix(prefix)
        for entry in config.get("pending", [])
        if entry["setting"].startswith(prefix) and entry["setting"] != setting
    }
    return keep_live(declared, live, paths)


def ruleset_fix(config, ruleset, live, setting):
    name = ruleset["name"]
    rules = pending_kept(config, f"ruleset.{name}.rules.", ruleset["rules"], live["rules"] if live else {}, setting)
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
    environment = pending_kept(config, f"environment.{name}.", declared, live or {}, setting)
    deployment = environment["deployment"]
    body = {
        "reviewers": [{"type": "User", "login": login} for login in environment["reviewers"]],
        "prevent_self_review": environment.get("prevent_self_review", False),
        "can_admins_bypass": environment["can_admins_bypass"],
        "deployment_branch_policy": None
        if deployment == "all"
        else {"protected_branches": deployment == "protected", "custom_branch_policies": deployment == "custom"},
    }
    return {"body": body}


def compare_settings(config, actual):
    repo = config["repository"]
    for key, expected in config.get("settings", {}).items():
        if actual.get(key) != expected:
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
            f"reviewers need their user IDs (gh api users/LOGIN --jq .id)"
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


def compare_project(config, actual):
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
            "project", f"project.workflows.{name}", "undeclared", ABSENT, actual["workflows"][name], ui, "", view_only
        )
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


def audit(config, github, sections=SECTIONS) -> list[Finding]:
    findings: list[Finding] = []
    audited = {section for section in sections if section not in ("project", "app") or config.get(section)}
    for section in [section for section in sections if section in audited]:
        try:
            actual = READ[section](github, config)
        except UnavailableError as error:
            findings.append(Finding(section, section, "unavailable", ui=where(section, config), note=str(error)))
            continue
        findings.extend(COMPARE[section](config, actual))
    return apply_pending(config, findings, audited)


def fix(findings, github) -> list[str]:
    """Create or update declared labels and add missing Project items; nothing else is ever written."""
    failures = []
    for finding in findings:
        if finding.status not in ("missing", "drift") or not finding.fix:
            continue
        try:
            if finding.section == "labels":
                github.send(finding.fix["method"], finding.fix["path"], finding.fix["body"])
            elif finding.section == "project" and "mutation" in finding.fix:
                github.graphql(finding.fix["mutation"], finding.fix["variables"])
        except UnavailableError as error:
            failures.append(f"{finding.setting}: {error}")
    return failures


# --- report -----------------------------------------------------------------------------------------------------


def render(findings, sections) -> str:
    counts = {
        status: sum(f.status == status for f in findings)
        for status in ("drift", "missing", "undeclared", "pending", "done", "unavailable")
    }
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
        "Next: a maintainer reviews each drift, undeclared object and missing item; `--fix` creates or updates the "
        "declared labels and adds missing Project items, and everything else is changed in the UI or with the command "
        "shown, then confirmed by a new audit."
        if failing
        else "Every readable section matches the reviewed state; unavailable sections need a token that can read them.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, github=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=CONFIG, help=argparse.SUPPRESS)
    parser.add_argument("--section", choices=SECTIONS, action="append", help="audit only these sections")
    parser.add_argument("--json", type=Path, help="also write the findings as JSON")
    parser.add_argument(
        "--fix", action="store_true", help="create or update declared labels; add missing Project items"
    )
    parser.add_argument("--check-config", action="store_true", help="validate the expected state offline and stop")
    args = parser.parse_args(argv)
    try:
        config = load(args.config)
    except ConfigError as error:
        print(f"audit_repository: {error}", file=sys.stderr)
        return 1
    if args.check_config:
        print(f"audit_repository: {args.config.name} is valid")
        return 0
    github = github or GhCli()
    sections = tuple(args.section or SECTIONS)
    findings = audit(config, github, sections)
    failures = []
    if args.fix:
        failures = fix(findings, github)
        findings = audit(config, github, sections)
    sys.stdout.write(render(findings, sections))
    for failure in failures:
        print(f"FIX FAILED: {failure}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {"findings": [{k: v for k, v in asdict(f).items()} for f in findings], "fix_failures": failures}
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + "\n", encoding="utf-8")
    return 1 if failures or any(finding.fails for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
