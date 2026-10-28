#!/usr/bin/env python3
"""Own release metadata and the PR/direct-commit changelog; no third-party dependencies.

`check [--site DIR] [--version VERSION]` checks metadata and optional requested-release notes.
`history --output FILE` exports the exact local ancestry for read-only GitHub association collection.
`prepare --version VERSION --date YYYY-MM-DD --prs FILE --associations FILE --actor LOGIN [--manifest FILE]`
updates metadata and the changelog from a complete GitHub closed-PR listing and
reports the prepared paths and their digests. It neither commits nor tags. The
dispatch supplies that listing and opens the release PR. When the default branch already carries VERSION
untagged, it completes that release instead, adding only the changelog entries it lacks.
`lineage --version VERSION --prs FILE --associations FILE [--summary FILE]` exits 3 when the changelog of the
untagged VERSION misses a change since the previous tag, naming each; Tag release refuses to tag until then.
The crate derives its version and date from content/guide.toml at build time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from datetime import UTC, date, datetime
from pathlib import Path

import build_identity
import check_changelog
from handoff import handoff
from register_ids import render
from release_version import release_input, version

ROOT = Path(__file__).resolve().parent.parent
BUILD_UI = "assets/data/ui.js"
PATH_POLICY = ".github/release-prepared-files.json"
FILES = tuple(json.loads((ROOT / PATH_POLICY).read_text(encoding="utf-8"))["metadata"])


def prepared_paths(root: Path) -> set[str]:
    """Read the same permitted-set owner as the dispatcher, independently of a prepared manifest."""
    policy = json.loads((root / PATH_POLICY).read_text(encoding="utf-8"))
    if policy.get("formatVersion") != 1 or not all(
        isinstance(policy.get(key), list) for key in ("metadata", "additional")
    ):
        raise ValueError("invalid release path policy")
    paths = [*policy["metadata"], *policy["additional"]]
    if not all(isinstance(path, str) and path for path in paths) or len(paths) != len(set(paths)):
        raise ValueError("invalid release path policy")
    resolved = root.resolve()
    for path in paths:
        if "\\" in path or ":" in path or path.startswith("/") or any(p in ("", ".", "..") for p in path.split("/")):
            raise ValueError(f"unsafe release path: {path}")
        if (resolved / path).resolve() != resolved / path:
            raise ValueError(f"release path escapes or aliases another file: {path}")
    return set(paths)


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
    guide = tomllib.loads((root / "content/guide.toml").read_text(encoding="utf-8"))["guide"]
    expected = version(guide["version"])
    released = str(guide["datePublished"])
    date.fromisoformat(released)
    cff = (root / "CITATION.cff").read_text(encoding="utf-8")
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    zenodo = json.loads((root / ".zenodo.json").read_text(encoding="utf-8"))
    values = {
        "CITATION.cff version": citation(cff, "version"),
        "package.json": package["version"],
        "package-lock.json": lock["version"],
        "package-lock.json packages root": lock["packages"][""]["version"],
        "pyproject.toml": project["project"]["version"],
        ".zenodo.json version": zenodo.get("version"),
    }
    errors = [f"{name}: {actual!r}; expected {expected!r}" for name, actual in values.items() if actual != expected]
    if citation(cff, "date-released") != released:
        errors.append(f"CITATION.cff date-released must equal content/guide.toml datePublished ({released})")
    if zenodo.get("publication_date") != released:
        errors.append(f".zenodo.json publication_date must equal content/guide.toml datePublished ({released})")
    return expected, released, errors


def built_identity(site: Path, root: Path) -> tuple[dict, list[str]]:
    """The identity a build baked into the page configuration, checked against this checkout's git state."""
    try:
        text = (site / BUILD_UI).read_text(encoding="utf-8")
    except OSError as error:
        return {}, [f"{site}/{BUILD_UI}: required page configuration is unreadable ({error})"]
    try:
        built = build_identity.config_identity(text)
    except (ValueError, TypeError, KeyError) as error:
        return {}, [f"{site}/{BUILD_UI}: the page configuration is unreadable ({error})"]
    expected = build_identity.identity(root)
    errors = [
        f"{site}/{BUILD_UI}: build.{key} is {built.get(key)!r}; expected {expected[key]!r}"
        for key in ("version", "commit", "channel", "status", "date")
        if built.get(key) != expected[key]
    ]
    if built.get("channel") != "release" and built.get("status") != "testing":
        errors.append(f"{site}/{BUILD_UI}: a build that is not a release must report the testing status")
    return built, errors


def check(root: Path, site: Path | None = None, requested: str | None = None) -> list[str]:
    expected, released, errors = metadata(root)
    if requested is not None:
        version(requested)
        if requested != expected:
            errors.append(f"requested version {requested} differs from committed metadata ({expected})")
        notes = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        sections = list(re.finditer(r"(?m)^## \[" + re.escape(requested) + r"\]([^\r\n]*)$", notes))
        if len(sections) != 1:
            errors.append("CHANGELOG.md needs exactly one section for the requested version")
        else:
            heading = sections[0]
            following = re.search(r"(?m)^## ", notes[heading.end() :])
            body = notes[heading.end() : heading.end() + following.start()] if following else notes[heading.end() :]
            if heading[1].strip() != "- " + released:
                errors.append("CHANGELOG.md requested version date differs from release metadata")
            if not any(line.strip() and not line.lstrip().startswith("#") for line in body.splitlines()):
                errors.append("CHANGELOG.md requested version section is empty")
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
        built, build_errors = built_identity(site, root)
        errors.extend(build_errors)
        if built:
            try:
                health = json.loads((site / "api/health.json").read_text(encoding="utf-8"))
                if health.get("build") != built:
                    errors.append(f"{site}/api/health.json: build identity differs from the page")
            except (OSError, ValueError) as error:
                errors.append(f"{site}/api/health.json: required health identity is unreadable ({error})")
        for identifier in ("./", "#guide-software") if built else ():
            status = nodes.get(identifier, {}).get("creativeWorkStatus")
            if status != built.get("status"):
                errors.append(
                    f"{site}/ro-crate-metadata.json {identifier}: status is {status!r}; "
                    f"expected {built.get('status')!r}"
                )
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


def history_export(root: Path) -> dict:
    """Bind ordered mainline subjects and full ancestry to one exact source and reachable tag."""
    source = git(root, "rev-parse", "HEAD")
    previous, commits = history(root)
    records = git(
        root, "log", "--first-parent", "--reverse", "--format=%H%x00%s", f"{previous}..HEAD" if previous else "HEAD"
    )
    first_parent = []
    for record in records.splitlines():
        sha, subject = record.split("\0", 1)
        first_parent.append({"sha": sha, "subject": subject})
    if git(root, "rev-parse", "HEAD") != source:
        raise ValueError("source moved while collecting release history")
    return {
        "formatVersion": 1,
        "source": source,
        "previousTag": previous,
        "commits": sorted(commits),
        "firstParent": first_parent,
    }


def release_changes(root: Path, data: dict) -> dict:
    """Reject incomplete/stale association data; local Git, never remote timestamps, owns scope."""
    local = history_export(root)
    if not isinstance(data, dict) or any(
        data.get(key) != local[key] for key in ("formatVersion", "source", "previousTag")
    ):
        raise ValueError("release associations name another source or previous tag")
    repository, base = data.get("repository", ""), data.get("base", "")
    if (
        not isinstance(repository, str)
        or not re.fullmatch(r"[\w.-]+/[\w.-]+", repository)
        or not isinstance(base, str)
        or not base
    ):
        raise ValueError("release associations need a repository and default branch")
    associations = data.get("associations")
    expected = {record["sha"] for record in local["firstParent"]}
    if not isinstance(associations, dict) or set(associations) != expected:
        raise ValueError("release associations are incomplete or contain unrelated commits")
    for numbers in associations.values():
        if not isinstance(numbers, list) or any(type(number) is not int or number < 1 for number in numbers):
            raise ValueError("malformed commit-to-PR associations")
    return {**local, "repository": repository, "base": base, "associations": associations}


def escaped(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>()#!|])", r"\\\1", " ".join(text.split()))


def lineage(
    prs: list[dict], commits: set[str], changes: dict | None, *, exclude: str | None = None
) -> tuple[dict[int, tuple[str, int, str]], list[tuple[str, str]]]:
    """The deduplicated release history: merged PRs by number as (merge time, number, entry), and the direct
    first-parent commits no PR represents as (sha, entry). PRs from `exclude`, the release's own proposal branch, are
    left out with their commits: a release never lists its own preparation."""
    selected: dict[int, tuple[str, int, str]] = {}
    represented, own = set(), set()
    for pr in prs:
        if not pr.get("merged_at") or pr.get("merge_commit_sha") not in commits:
            continue
        head = pr.get("head") or {}
        if (
            exclude
            and head.get("ref") == exclude
            and (not changes or (head.get("repo") or {}).get("full_name") == changes["repository"])
        ):
            own.add(pr.get("number"))
            represented.add(pr["merge_commit_sha"])
            continue
        if changes and (
            pr.get("base", {}).get("ref") != changes["base"]
            or pr.get("base", {}).get("repo", {}).get("full_name") != changes["repository"]
        ):
            raise ValueError("merged pull request names another repository or base branch")
        number = pr.get("number")
        url = pr.get("html_url", "")
        if (
            not isinstance(number, int)
            or number < 1
            or not re.fullmatch(
                r"https://github\.com/"
                + (re.escape(changes["repository"]) if changes else r"[\w.-]+/[\w.-]+")
                + r"/pull/"
                + str(number),
                url,
            )
        ):
            raise ValueError("malformed merged pull request")
        title = " ".join(str(pr.get("title", "")).split())
        if not title:
            raise ValueError("merged pull request has no title")
        selected[number] = (str(pr["merged_at"]), number, f"- {escaped(title)} ([#{number}]({url}))")
        represented.add(pr["merge_commit_sha"])
    direct = []
    if changes:
        for record in changes["firstParent"]:
            linked = set(changes["associations"][record["sha"]])
            if record["sha"] not in represented and not linked & (selected.keys() | own):
                sha, subject = record["sha"], escaped(record["subject"])
                if not subject:
                    raise ValueError("direct commit has no subject")
                entry = f"- {subject} ([{sha[:7]}](https://github.com/{changes['repository']}/commit/{sha}))"
                direct.append((sha, entry))
    return selected, direct


def changelog(
    text: str,
    target: str,
    released: str,
    prs: list[dict],
    commits: set[str],
    *,
    previous: str | None,
    changes: dict | None = None,
) -> str:
    if re.search(r"(?m)^## \[" + re.escape(target) + r"\]", text):
        raise ValueError("this version already has a changelog entry")
    # The shared parser refuses malformed sections and reserved lineage headings before anything is composed.
    problems = check_changelog.structure_errors(text)
    if problems:
        raise ValueError("CHANGELOG.md: " + "; ".join(problems))
    preamble, sections = check_changelog.parse(text)
    if not commits:
        raise ValueError("no commits since the previous tag; refusing an empty release changelog")
    selected, entries = lineage(prs, commits, changes, exclude=f"release/{target}")
    direct = [entry for _, entry in entries]
    if not selected and not direct:
        raise ValueError("no merged pull requests since the previous tag; refusing an empty release changelog")
    lines = [f"Since {previous or 'the beginning of the repository'}.", ""]
    if selected:
        lines.extend([f"### {check_changelog.MERGED}", "", *(value[2] for value in sorted(selected.values())), ""])
    if direct:
        lines.extend([f"### {check_changelog.DIRECT}", "", *direct])
    # The curated notes lead the release unchanged; the generated lineage follows them, never replaces them.
    notes = sections[0].body.strip()
    block = f"## [{target}] - {released}\n\n" + (notes + "\n\n" if notes else "") + "\n".join(lines) + "\n\n"
    # Earlier released sections and their original text remain byte-for-byte.
    released_text = "".join(section.text for section in sections[1:])
    return preamble + f"## [{check_changelog.UNRELEASED}]\n\n" + block + released_text


def prepare(
    root: Path,
    target: str,
    released: str,
    prs: list[dict],
    actor: str,
    *,
    now: datetime | None = None,
    associations: dict | None = None,
) -> dict[str, object]:
    permitted = prepared_paths(root)
    version(target)
    date.fromisoformat(released)
    _, _, errors = metadata(root)
    if errors:
        raise ValueError("\n".join(errors))
    previous, commits = history(root)
    changes = release_changes(root, associations) if associations is not None else None
    if previous == "v" + target:
        raise ValueError("the requested version is already tagged")
    texts = {path: (root / path).read_text(encoding="utf-8") for path in FILES}
    people = tomllib.loads(texts["content/guide.toml"]).get("person", [])
    agents = [person["id"] for person in people if person.get("github", "").casefold() == actor.casefold()]
    if len(agents) != 1:
        raise ValueError("dispatch actor needs one reviewed person.github identity in content/guide.toml")
    texts["content/guide.toml"] = scalar(
        scalar(texts["content/guide.toml"], "version", json.dumps(target), section="guide"),
        "datePublished",
        released,
        section="guide",
    )
    texts["CITATION.cff"] = scalar(
        scalar(texts["CITATION.cff"], "version", json.dumps(target)), "date-released", json.dumps(released)
    )
    for path in ("package.json", "package-lock.json", ".zenodo.json"):
        data = json.loads(texts[path])
        data["version"] = target
        if path == "package-lock.json":
            data["packages"][""]["version"] = target
        if path == ".zenodo.json":
            data["publication_date"] = released
        texts[path] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    texts["pyproject.toml"] = scalar(texts["pyproject.toml"], "version", json.dumps(target), section="project")
    texts["CHANGELOG.md"] = changelog(
        (root / "CHANGELOG.md").read_text(encoding="utf-8"),
        target,
        released,
        prs,
        commits,
        previous=previous,
        changes=changes,
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
description = "Release metadata and complete PR/direct-commit changelog prepared for human review."
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
    texts["content/identifiers.toml"] = render(registry["register"]["prepared"], issued, registry.get("retired", {}))
    # All parsing and refusals above happen before the first write. The generated
    # crate is rebuilt, never patched; its consistency is checked with --site.
    if set(texts) != permitted:
        raise ValueError("prepared files differ from the shared release path policy")
    for path, text in texts.items():
        (root / path).write_text(text, encoding="utf-8", newline="\n")
    return {
        "formatVersion": 1,
        "version": target,
        "mode": "prepare",
        "files": [
            {"path": path, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()} for path, text in texts.items()
        ],
    }


PR_LINK = re.compile(r"\[#(\d+)\]\(https://github\.com/[\w.-]+/[\w.-]+/pull/\1\)")
COMMIT_LINK = re.compile(r"\]\(https://github\.com/[\w.-]+/[\w.-]+/commit/([0-9a-f]{40})\)")


def release_section(root: Path, target: str) -> check_changelog.Section:
    _, sections = check_changelog.parse((root / "CHANGELOG.md").read_text(encoding="utf-8"))
    found = [section for section in sections if section.key == target]
    if len(found) != 1:
        raise ValueError(f"CHANGELOG.md needs exactly one section for {target}")
    return found[0]


def missing_lineage(root: Path, target: str, prs: list[dict], associations: dict) -> dict:
    """The changes from the previous release tag to HEAD that the prepared, untagged section of `target` does not
    list yet, as changelog entries in release order. Tag release refuses while any are missing."""
    version(target)
    previous, commits = history(root)
    if previous == "v" + target:
        raise ValueError("the requested version is already tagged")
    selected, direct = lineage(prs, commits, release_changes(root, associations), exclude=f"release/{target}")
    body = release_section(root, target).body
    listed_prs = {int(number) for number in PR_LINK.findall(body)}
    listed_commits = set(COMMIT_LINK.findall(body))
    return {
        "previous": previous,
        "pulls": [entry for _, number, entry in sorted(selected.values()) if number not in listed_prs],
        "direct": [entry for sha, entry in direct if sha not in listed_commits],
    }


def list_end(lines: list[str], marker: str, since: int) -> int:
    """The line after the last entry of the generated list under `marker`, which preparation writes as the heading,
    one blank line and the entries."""
    start = lines.index(marker, since)
    if start + 1 >= len(lines) or lines[start + 1]:
        raise ValueError(f"the `{marker}` list is not as release preparation writes it; reconcile it by hand")
    end = start + 2
    while end < len(lines) and lines[end].startswith("- "):
        end += 1
    return end


def extend_section(text: str, target: str, missing: dict) -> str:
    """Append the missing entries to the generated lists of `target`'s section; every existing line stays in place."""
    preamble, sections = check_changelog.parse(text)
    merged, direct = f"### {check_changelog.MERGED}", f"### {check_changelog.DIRECT}"
    parts = []
    for section in sections:
        if section.key != target:
            parts.append(section.text)
            continue
        lines = section.text.split("\n")
        since = next((index for index, line in enumerate(lines) if line.startswith("Since ")), None)
        if since is None:
            raise ValueError(f"the {target} section has no generated lineage to complete; reconcile it by hand")
        for marker, entries in ((merged, missing["pulls"]), (direct, missing["direct"])):
            if not entries:
                continue
            if marker in lines[since:]:
                end = list_end(lines, marker, since)
                lines[end:end] = entries
            elif marker == merged and direct in lines[since:]:
                start = lines.index(direct, since)
                lines[start:start] = [marker, "", *entries, ""]
            else:
                end = list_end(lines, merged, since) if merged in lines[since:] else since + 1
                lines[end:end] = ["", marker, "", *entries]
        parts.append("\n".join(lines))
    return preamble + "".join(parts)


def complete(root: Path, target: str, prs: list[dict], *, associations: dict) -> dict[str, object]:
    """Complete a prepared, untagged release on the default branch: add only the changes its changelog does not list
    yet. Version, dates, curated notes, earlier entries and provenance stay as they are."""
    permitted = prepared_paths(root)
    expected, _, errors = metadata(root)
    if errors:
        raise ValueError("\n".join(errors))
    if expected != target:
        raise ValueError(f"the default branch carries {expected}; prepare {target} as a new release instead")
    missing = missing_lineage(root, target, prs, associations)
    if not missing["pulls"] and not missing["direct"]:
        raise ValueError(f"the {target} changelog already lists every change since the previous tag; run Tag release")
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    extended = extend_section(text, target, missing)
    problems = check_changelog.structure_errors(extended) + check_changelog.history_errors(
        text, extended, "HEAD", set()
    )
    if problems:
        raise ValueError("CHANGELOG.md: " + "; ".join(problems))
    (root / "CHANGELOG.md").write_text(extended, encoding="utf-8", newline="\n")
    return {
        "formatVersion": 1,
        "version": target,
        "mode": "complete",
        "added": [*missing["pulls"], *missing["direct"]],
        "files": [
            {"path": path, "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest()}
            for path in sorted(permitted)
        ],
    }


def lineage_report(target: str, missing: dict) -> str:
    """The Tag release summary: either complete, or what is missing and what happens next."""
    since = missing["previous"] or "the beginning of the repository"
    entries = [*missing["pulls"], *missing["direct"]]
    if not entries:
        return f"The `{target}` changelog lists every change since {since}.\n"
    return "\n".join(
        [
            f"### Not tagged: the `{target}` changelog misses {len(entries)} change(s) since {since}",
            "",
            *entries,
            "",
            *handoff(
                f"Tag release starts Prepare release for `{target}`, which opens a pull request adding exactly these "
                "entries. Review and merge it with **Merge when ready**, then run Tag release again.",
                f"when no completion pull request appears, run Prepare release for `{target}` yourself.",
                f"Tag release creates `v{target}`.",
            ),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    checking = commands.add_parser("check")
    checking.add_argument("--site", type=Path)
    checking.add_argument("--version")
    exporting = commands.add_parser("history")
    exporting.add_argument("--output", required=True, type=Path)
    preparing = commands.add_parser("prepare")
    preparing.add_argument("--version", required=True)
    preparing.add_argument("--date", default=date.today().isoformat())
    preparing.add_argument("--prs", required=True, type=Path)
    preparing.add_argument("--associations", required=True, type=Path)
    preparing.add_argument("--actor", required=True)
    preparing.add_argument("--timestamp", type=datetime.fromisoformat)
    preparing.add_argument("--manifest", type=Path)
    comparing = commands.add_parser("lineage")
    comparing.add_argument("--version", required=True)
    comparing.add_argument("--prs", required=True, type=Path)
    comparing.add_argument("--associations", required=True, type=Path)
    comparing.add_argument("--summary", type=Path, help="also append the report to this Markdown file")
    args = parser.parse_args(argv)
    try:
        if getattr(args, "version", None) is not None:
            args.version = release_input(args.version)  # the dispatch input, as the maintainer typed it
        if args.command == "check":
            errors = check(ROOT, args.site, args.version)
            if errors:
                raise ValueError("\n".join(errors))
            print("release_versions: metadata, dates and prose agree")
        elif args.command == "history":
            output = history_export(ROOT)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
            )
        elif args.command == "lineage":
            missing = missing_lineage(
                ROOT,
                args.version,
                json.loads(args.prs.read_text(encoding="utf-8")),
                json.loads(args.associations.read_text(encoding="utf-8")),
            )
            report = lineage_report(args.version, missing)
            print(report, end="")
            if args.summary:
                with args.summary.open("a", encoding="utf-8") as summary:
                    summary.write(report)
            return 3 if missing["pulls"] or missing["direct"] else 0
        else:
            prs = json.loads(args.prs.read_text(encoding="utf-8"))
            associations = json.loads(args.associations.read_text(encoding="utf-8"))
            # The default branch already carries the version: complete that untagged release instead.
            if metadata(ROOT)[0] == args.version:
                manifest = complete(ROOT, args.version, prs, associations=associations)
            else:
                manifest = prepare(
                    ROOT, args.version, args.date, prs, args.actor, now=args.timestamp, associations=associations
                )
            if args.manifest:
                args.manifest.parent.mkdir(parents=True, exist_ok=True)
                args.manifest.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
                )
            if manifest.get("mode") == "complete":
                print(f"Completion of {args.version} prepared for review: " + "; ".join(manifest["added"]))
            else:
                print("Prepared for review: " + ", ".join(item["path"] for item in manifest["files"]))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"release_versions: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
