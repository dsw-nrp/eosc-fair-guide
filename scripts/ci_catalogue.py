"""Render the workflow catalogue in docs/ci.md from the workflow files and their reviewed human entries.

    python scripts/ci_catalogue.py           # rewrite the catalogue region of docs/ci.md
    python scripts/ci_catalogue.py --check   # fail on a missing human entry or a stale catalogue; writes nothing

Triggers, permissions at each level, concurrency, uploaded artifacts and their retention come from
``.github/workflows/*.yml``; purpose, human entry point, next actor, rerun route, the reason for each write permission
and each artifact's purpose come from ``.github/ci-catalogue.toml``. Every workflow, uploaded artifact and write
permission needs its human entry, and an entry with nothing left to describe is an error too.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ".github/workflows"
ENTRIES = ".github/ci-catalogue.toml"
DOCUMENT = "docs/ci.md"
BEGIN, END = "<!-- begin:guide:ci-catalogue -->", "<!-- end:guide:ci-catalogue -->"
COMMAND = "python scripts/ci_catalogue.py"
WORKFLOW_FIELDS = ("purpose", "entry", "next", "rerun")
EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")


def load(path: Path) -> dict[str, Any]:
    """A workflow with every scalar as text, so `on` stays a key and versions keep their spelling."""
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def workflows(root: Path) -> dict[str, dict[str, Any]]:
    return {path.name: load(path) for path in sorted((root / WORKFLOWS).glob("*.yml"))}


def app_requests(job: dict[str, Any]) -> dict[str, str]:
    requested: dict[str, str] = {}
    for step in job.get("steps", []):
        if step.get("uses", "").startswith("actions/create-github-app-token@"):
            requested |= {
                key.removeprefix("permission-"): value
                for key, value in step.get("with", {}).items()
                if key.startswith("permission-")
            }
    return requested


def token_requests(root: Path = ROOT) -> dict[tuple[str, str], tuple[dict | None, dict]]:
    """Each workflow job's GITHUB_TOKEN permissions (its own block, else the workflow's) and App-token requests."""
    return {
        (name, job): (data.get("permissions", workflow.get("permissions")), app_requests(data))
        for name, workflow in workflows(root).items()
        for job, data in workflow["jobs"].items()
    }


def placeholder(text: str) -> str:
    """An expression-built name as a readable pattern: `${{ github.run_id }}` becomes `<run_id>`."""
    return EXPRESSION.sub(lambda match: "<" + re.sub(r"^github\.(event\.)?", "", match.group(1)) + ">", text)


def artifacts(workflow: dict[str, Any]) -> dict[str, str]:
    """Uploaded artifact names, as patterns, with their retention."""
    found = {}
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if step.get("uses", "").startswith("actions/upload-artifact@"):
                options = step.get("with", {})
                days = options.get("retention-days")
                found[placeholder(options["name"])] = f"{days} days" if days else "the repository's retention"
    return found


def writes(workflow: dict[str, Any]) -> list[str]:
    """`job.permission` for every write a job's GITHUB_TOKEN or App token may perform."""
    found = []
    for job, data in workflow["jobs"].items():
        github = data.get("permissions", workflow.get("permissions")) or {}
        if isinstance(github, str):
            github = {"all": github}
        for permission, level in sorted({**github, **app_requests(data)}.items()):
            if level == "write":
                found.append(f"{job}.{permission}")
    return found


def triggers(workflow: dict[str, Any]) -> str:
    events = workflow.get("on", {})
    if isinstance(events, str):
        events = {events: {}}
    if isinstance(events, list):
        events = dict.fromkeys(events, {})
    parts = []
    for event, declared in events.items():
        options = declared if isinstance(declared, dict) else {}
        details = []
        if event == "schedule":
            details = [f"`{entry['cron']}` UTC" for entry in declared]
        for key in ("branches", "tags", "paths", "types", "workflows"):
            if options.get(key):
                details.append(f"{key} " + ", ".join(f"`{value}`" for value in options[key]))
        if options.get("inputs"):
            details.append("inputs " + ", ".join(f"`{value}`" for value in options["inputs"]))
        parts.append(f"`{event}`" + (f" ({'; '.join(details)})" if details else ""))
    return "; ".join(parts)


def access(permissions: Any) -> str:
    if permissions is None:
        return "repository default"
    if isinstance(permissions, str):
        return f"`{permissions}`"
    if not permissions:
        return "none"
    return ", ".join(f"{key} {value}" for key, value in permissions.items())


def concurrency(value: Any) -> str:
    if isinstance(value, str):
        return f"`{value}`"
    cancels = value.get("cancel-in-progress", "false")
    return f"`{value['group']}`" + (
        ", cancels the run in progress"
        if cancels == "true"
        else f", cancel `{cancels}`"
        if cancels != "false"
        else ", queued"
    )


def render(root: Path = ROOT) -> str:
    entries = tomllib.loads((root / ENTRIES).read_text(encoding="utf-8"))
    lines = [BEGIN, "", f"Generated by `{COMMAND}` from the workflow files and `{ENTRIES}`; do not edit by hand.", ""]
    for name, workflow in workflows(root).items():
        human = entries["workflow"][name]
        lines += [f"### `{name}`: {workflow.get('name', name)}", "", human["purpose"], ""]
        lines.append(f"- **Triggers:** {triggers(workflow)}")
        lines += [
            f"- **Entry point:** {human['entry']}",
            f"- **Next:** {human['next']}",
            f"- **Rerun:** {human['rerun']}",
        ]
        levels = [f"workflow {access(workflow.get('permissions'))}"]
        for job, data in workflow["jobs"].items():
            if "permissions" in data:
                levels.append(f"`{job}` {access(data['permissions'])}")
            if app_requests(data):
                levels.append(f"`{job}` App token {access(app_requests(data))}")
        lines.append(f"- **Permissions:** {'; '.join(levels)}")
        for write in writes(workflow):
            lines.append(f"  - `{write}`: {human['writes'][write]}")
        groups = ([f"workflow {concurrency(workflow['concurrency'])}"] if "concurrency" in workflow else []) + [
            f"`{job}` {concurrency(data['concurrency'])}"
            for job, data in workflow["jobs"].items()
            if "concurrency" in data
        ]
        lines.append(f"- **Concurrency:** {'; '.join(groups) if groups else 'none'}")
        called = sorted(
            {f"`{PurePosixPath(data['uses']).name}`" for data in workflow["jobs"].values() if "uses" in data}
        )
        if called:
            lines.append(f"- **Calls:** {', '.join(called)}, whose artifacts and writes are listed under it")
        uploaded = artifacts(workflow)
        lines.append("- **Artifacts:**" + ("" if uploaded else " none"))
        for artifact, retention in uploaded.items():
            lines.append(f"  - `{artifact}`, kept {retention}: {entries['artifact'][artifact]['purpose']}")
        lines.append("")
    return "\n".join([*lines, END])


def problems(root: Path = ROOT) -> list[str]:
    """Missing and orphaned human entries, each naming what to add or remove in the entries file."""
    entries = tomllib.loads((root / ENTRIES).read_text(encoding="utf-8"))
    declared = entries.get("workflow", {})
    found = []
    uploaded: set[str] = set()
    loaded = workflows(root)
    for name, workflow in loaded.items():
        human = declared.get(name)
        if human is None:
            found.append(f'{ENTRIES}: add [workflow."{name}"] with {", ".join(WORKFLOW_FIELDS)}')
            continue
        found += [f"{ENTRIES}: workflow {name} needs `{field}`" for field in WORKFLOW_FIELDS if not human.get(field)]
        needed = writes(workflow)
        found += [
            f'{ENTRIES}: workflow {name} needs writes."{write}": why the {write.split(".")[0]} job may write'
            for write in needed
            if not human.get("writes", {}).get(write)
        ]
        found += [
            f'{ENTRIES}: workflow {name} has writes."{write}", which no job requests; remove it'
            for write in human.get("writes", {})
            if write not in needed
        ]
        uploaded |= set(artifacts(workflow))
    found += [f'{ENTRIES}: remove [workflow."{name}"]; no such workflow' for name in declared if name not in loaded]
    described = entries.get("artifact", {})
    found += [
        f'{ENTRIES}: add [artifact."{name}"] with its purpose'
        for name in sorted(uploaded)
        if not described.get(name, {}).get("purpose")
    ]
    found += [
        f'{ENTRIES}: remove [artifact."{name}"]; no workflow uploads it' for name in described if name not in uploaded
    ]
    return found


def replace(document: str, block: str) -> str:
    if document.count(BEGIN) != 1 or document.count(END) != 1 or document.index(BEGIN) > document.index(END):
        raise ValueError(f"{DOCUMENT} needs exactly one {BEGIN} ... {END} region")
    start, end = document.index(BEGIN), document.index(END) + len(END)
    return document[:start] + block + document[end:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail on a missing entry or a stale catalogue")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    found = problems(args.root)
    for problem in found:
        print(problem, file=sys.stderr)
    if found:
        print(
            f"ci_catalogue: {len(found)} missing or orphaned entries; the catalogue was not rendered", file=sys.stderr
        )
        return 1
    path = args.root / DOCUMENT
    current = path.read_text(encoding="utf-8")
    updated = replace(current, render(args.root))
    if args.check:
        if updated != current:
            print(f"{DOCUMENT}: the workflow catalogue is stale; run `{COMMAND}`", file=sys.stderr)
            return 1
        print(f"ci_catalogue: {DOCUMENT} matches {len(list((args.root / WORKFLOWS).glob('*.yml')))} workflows")
        return 0
    if updated != current:
        path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"ci_catalogue: {DOCUMENT} {'updated' if updated != current else 'unchanged'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
