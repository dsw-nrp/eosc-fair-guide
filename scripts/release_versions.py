#!/usr/bin/env python3
"""Own release metadata and the merged-PR changelog; no third-party dependencies.

`check [--site DIR]` checks authored metadata, prose and an optional built crate.
`prepare --version VERSION --date YYYY-MM-DD --prs FILE --actor LOGIN` updates
metadata and the changelog from a complete GitHub closed-PR listing. It neither
commits nor tags. The dispatch supplies that listing and opens the release PR.
The crate derives its version and date from content/guide.toml at build time.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from datetime import UTC, date, datetime
from pathlib import Path

from register_ids import render

ROOT = Path(__file__).resolve().parent.parent
VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?")
FILES = ("content/guide.toml", "CITATION.cff", "package.json", "package-lock.json", "pyproject.toml")


def version(value: str) -> str:
    match = VERSION.fullmatch(value)
    if not match or any(
        not part or (part.isdigit() and len(part) > 1 and part[0] == "0")
        for part in (match[4] or "").split(".")
        if match[4] is not None
    ):
        raise ValueError("version must be a SemVer release or prerelease without a leading v or build suffix")
    return value


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, encoding="utf-8").stdout.strip()


def scalar(text: str, key: str, value: str, *, section: str | None = None) -> str:
    """Replace one declared scalar, preserving surrounding TOML or top-level CFF."""
    start, end = 0, len(text)
    if section:
        heading = re.search(r"(?m)^\[" + re.escape(section) + r"\]\s*$", text)
        if not heading:
            raise ValueError(f"missing [{section}]")
        start = heading.end()
        following = re.search(r"(?m)^\[", text[start:])
        end = start + following.start() if following else len(text)
    pattern = r"(?m)^" + re.escape(key) + (r"\s*=.*$" if section else r":.*$")
    replacement = key + (" = " if section else ": ") + value
    fragment, count = re.subn(pattern, lambda _: replacement, text[start:end])
    if count != 1:
        raise ValueError(f"expected exactly one {section or 'CFF root'}.{key}")
    return text[:start] + fragment + text[end:]


def citation(text: str, key: str) -> str | None:
    matches = re.findall(r"(?m)^" + re.escape(key) + r":\s*([^\r\n]+)$", text)
    if len(matches) > 1:
        raise ValueError(f"duplicate CFF root {key}")
    return matches[0].strip().strip("\"'") if matches else None


def metadata(root: Path) -> tuple[str, str, list[str]]:
    guide = tomllib.loads((root / FILES[0]).read_text(encoding="utf-8"))["guide"]
    expected = version(guide["version"])
    released = str(guide["datePublished"])
    date.fromisoformat(released)
    cff = (root / FILES[1]).read_text(encoding="utf-8")
    package = json.loads((root / FILES[2]).read_text(encoding="utf-8"))
    lock = json.loads((root / FILES[3]).read_text(encoding="utf-8"))
    project = tomllib.loads((root / FILES[4]).read_text(encoding="utf-8"))
    values = {
        "CITATION.cff version": citation(cff, "version"),
        "package.json": package["version"],
        "package-lock.json": lock["version"],
        "package-lock.json packages root": lock["packages"][""]["version"],
        "pyproject.toml": project["project"]["version"],
    }
    errors = [f"{name}: {actual!r}; expected {expected!r}" for name, actual in values.items() if actual != expected]
    if citation(cff, "date-released") != released:
        errors.append(f"CITATION.cff date-released must equal content/guide.toml datePublished ({released})")
    return expected, released, errors


def check(root: Path, site: Path | None = None) -> list[str]:
    expected, released, errors = metadata(root)
    # Historical versions belong only in the script-owned changelog. Source/runtime
    # versions are independent: this checks the Guide's literal version and explicit
    # Guide-version statements, not every dotted number in the documentation.
    explicit = re.compile(r"(?i)\b(?:guide(?:'s)?|průvodce)\s+(?:version|verze)\s+v?\d+\.\d+\.\d+")
    for directory in (root, root / "docs", root / ".agents/skills", root / ".claude/skills"):
        paths = directory.glob("*.md") if directory == root else directory.rglob("*.md")
        for path in paths:
            if path.name == "CHANGELOG.md":
                continue
            for line, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if expected in text or explicit.search(text):
                    errors.append(
                        f"{path.relative_to(root)}:{line}: read the Guide version from metadata; do not restate it"
                    )
    if site:
        crate = json.loads((site / "ro-crate-metadata.json").read_text(encoding="utf-8"))
        nodes = {node["@id"]: node for node in crate["@graph"]}
        for identifier in ("./", "#guide-source", "#guide-software"):
            if nodes.get(identifier, {}).get("version") != expected:
                errors.append(f"{site}/ro-crate-metadata.json {identifier}: version differs from {expected}")
        if nodes.get("./", {}).get("datePublished") != released:
            errors.append(f"{site}/ro-crate-metadata.json: datePublished differs from {released}")
    return errors


def history(root: Path) -> tuple[str | None, set[str]]:
    tags = git(root, "tag", "--merged", "HEAD").splitlines()
    valid = []
    for tag in tags:
        try:
            if tag.startswith("v"):
                version(tag[1:])
                valid.append(tag)
        except ValueError:
            continue
    previous = (
        git(root, "describe", "--tags", "--abbrev=0", *sum((["--match", tag] for tag in valid), []), "HEAD")
        if valid
        else None
    )
    return previous, set(git(root, "rev-list", f"{previous}..HEAD" if previous else "HEAD").splitlines())


def changelog(
    text: str, target: str, released: str, prs: list[dict], commits: set[str], *, previous: str | None
) -> str:
    if re.search(r"(?m)^## \[" + re.escape(target) + r"\]", text):
        raise ValueError("this version already has a changelog entry")
    selected = {}
    for pr in prs:
        if not pr.get("merged_at") or pr.get("merge_commit_sha") not in commits:
            continue
        number = pr.get("number")
        url = pr.get("html_url", "")
        if (
            not isinstance(number, int)
            or number < 1
            or not re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+/pull/" + str(number), url)
        ):
            raise ValueError("malformed merged pull request")
        title = " ".join(str(pr.get("title", "")).split())
        if not title:
            raise ValueError("merged pull request has no title")
        title = re.sub(r"([\\`*_{}\[\]<>()#!|])", r"\\\1", title)
        selected[number] = (str(pr["merged_at"]), f"- {title} ([#{number}]({url}))")
    if not selected:
        raise ValueError("no merged pull requests since the previous tag; refusing an empty release changelog")
    lines = ["### Merged pull requests", "", f"Since {previous or 'the beginning of the repository'}.", ""]
    lines.extend(value[1] for value in sorted(selected.values()))
    block = f"## [{target}] - {released}\n\n" + "\n".join(lines) + "\n\n"
    # Release preparation settles the Unreleased section as the complete PR list.
    # Earlier released sections and their original text remain byte-for-byte.
    unreleased = re.search(r"(?m)^## \[Unreleased\].*$", text)
    if not unreleased:
        raise ValueError("CHANGELOG.md needs an [Unreleased] section")
    following = re.search(r"(?m)^## ", text[unreleased.end() :])
    tail = text[unreleased.end() + following.start() :] if following else ""
    return text[: unreleased.start()] + "## [Unreleased]\n\n" + block + tail


def prepare(
    root: Path, target: str, released: str, prs: list[dict], actor: str, *, now: datetime | None = None
) -> list[str]:
    version(target)
    date.fromisoformat(released)
    _, _, errors = metadata(root)
    if errors:
        raise ValueError("\n".join(errors))
    previous, commits = history(root)
    if previous == "v" + target:
        raise ValueError("the requested version is already tagged")
    texts = {path: (root / path).read_text(encoding="utf-8") for path in FILES}
    people = tomllib.loads(texts[FILES[0]]).get("person", [])
    agents = [person["id"] for person in people if person.get("github", "").casefold() == actor.casefold()]
    if len(agents) != 1:
        raise ValueError("dispatch actor needs one reviewed person.github identity in content/guide.toml")
    texts[FILES[0]] = scalar(
        scalar(texts[FILES[0]], "version", json.dumps(target), section="guide"),
        "datePublished",
        released,
        section="guide",
    )
    texts[FILES[1]] = scalar(
        scalar(texts[FILES[1]], "version", json.dumps(target)), "date-released", json.dumps(released)
    )
    for path in (FILES[2], FILES[3]):
        data = json.loads(texts[path])
        data["version"] = target
        if path == FILES[3]:
            data["packages"][""]["version"] = target
        texts[path] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    texts[FILES[4]] = scalar(texts[FILES[4]], "version", json.dumps(target), section="project")
    texts["CHANGELOG.md"] = changelog(
        (root / "CHANGELOG.md").read_text(encoding="utf-8"), target, released, prs, commits, previous=previous
    )
    # Human-owned metadata gets a truthful action by the reviewed dispatcher.
    # This deterministic script is an instrument, not an invented AI identity.
    identifier = "release-" + target
    provenance = (root / "content/provenance.toml").read_text(encoding="utf-8")
    if any(action["id"] == identifier for action in tomllib.loads(provenance).get("action", [])):
        raise ValueError("release provenance already exists")
    timestamp = (now or datetime.now(UTC)).isoformat(timespec="seconds")
    texts["content/provenance.toml"] = (
        provenance.rstrip()
        + f"""

[[action]]
id = {json.dumps(identifier)}
type = "update"
name = "Prepare release metadata"
description = "Release metadata and merged-pull-request changelog prepared for human review."
agent = {json.dumps(agents[0])}
instruments = ["release-automation"]
objects = []
results = ["guide"]
endTime = {timestamp}
"""
    )
    # Append the newly issued action without changing any existing identity.
    registry = tomllib.loads((root / "content/identifiers.toml").read_text(encoding="utf-8"))
    issued = registry["issued"]
    if identifier in issued.get("actions", []) or identifier in registry.get("retired", {}).get("actions", []):
        raise ValueError("release action identifier has already been issued")
    issued.setdefault("actions", []).append(identifier)
    texts["content/identifiers.toml"] = render(registry["register"]["frozen"], issued, registry.get("retired", {}))
    # All parsing and refusals above happen before the first write. The generated
    # crate is rebuilt, never patched; its consistency is checked with --site.
    for path, text in texts.items():
        (root / path).write_text(text, encoding="utf-8", newline="\n")
    return list(texts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    checking = commands.add_parser("check")
    checking.add_argument("--site", type=Path)
    preparing = commands.add_parser("prepare")
    preparing.add_argument("--version", required=True)
    preparing.add_argument("--date", default=date.today().isoformat())
    preparing.add_argument("--prs", required=True, type=Path)
    preparing.add_argument("--actor", required=True)
    preparing.add_argument("--timestamp", type=datetime.fromisoformat)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            errors = check(ROOT, args.site)
            if errors:
                raise ValueError("\n".join(errors))
            print("release_versions: metadata, dates and prose agree")
        else:
            paths = prepare(
                ROOT,
                args.version,
                args.date,
                json.loads(args.prs.read_text(encoding="utf-8")),
                args.actor,
                now=args.timestamp,
            )
            print("Prepared for review: " + ", ".join(paths))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"release_versions: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
