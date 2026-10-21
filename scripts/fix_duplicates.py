#!/usr/bin/env python3
"""Trusted maintainer command: apply safe duplicate link suggestions to a pull request.

The workflow checks out default-branch code, extracts the pull request's content as data, runs this handler,
and commits the changed files back to the pull request branch through the repository-scoped App. It never runs
pull-request code, never merges, and never edits the accepted-duplicates list.
"""

from __future__ import annotations

import argparse
import base64
import difflib
import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_crate  # noqa: E402
import check_content  # noqa: E402
import check_duplicates  # noqa: E402
import register_ids  # noqa: E402

COMMAND = "/fix-duplicates"
INSTRUMENT = "duplicate-fix"
COMMENT_LIMIT = 60000
REGISTRY_OBJECTS = {"re3data": "re3data", "fip-dashboard": "fip-dashboard", "knav": "knav"}
WRITERS = {"admin", "maintain", "write"}


def parse_command(body: str | None) -> bool:
    """Only the exact command is accepted; no arguments, URLs or shell text."""
    return str(body or "").strip() == COMMAND


def person_for(content: dict[str, Any], login: str) -> str | None:
    """Resolve the commenter to a reviewed person; never guess or create one."""
    wanted = str(login or "").casefold()
    for person in content["guide"].get("person", []):
        if isinstance(person.get("github"), str) and person["github"].casefold() == wanted:
            return str(person["id"])
    return None


def instrument_available(content: dict[str, Any]) -> bool:
    return any(item.get("id") == INSTRUMENT for item in content["guide"].get("instrument", []))


def cited_source(content: dict[str, Any], record_name: str) -> str | None:
    """The consulted registry source, only when the content cites it."""
    kind = record_name.split(":", 1)[0]
    source_id = REGISTRY_OBJECTS.get(kind)
    if source_id is None:
        return None
    cited = {item["id"] for item in content["sources"]}
    cited |= {item["id"] for item in content["resources"] if item.get("citation")}
    return source_id if source_id in cited else None


def action_id(pr: int, head: str) -> str:
    day = datetime.now(UTC).date().isoformat()
    return f"{day}-dupfix-{pr}-{head[:7]}"


def action_block(
    identifier: str, person: str, suggestions: list[check_duplicates.Suggestion], content: dict[str, Any]
) -> str:
    results = sorted({suggestion.entry.split(":", 1)[1] for suggestion in suggestions})
    sources = sorted(
        {source for suggestion in suggestions if (source := cited_source(content, suggestion.record)) is not None}
    )
    description = (
        f"Linked {', '.join(results)} to the registry record(s) the duplicate check named as a shared identity."
    )
    rows = [
        "[[action]]",
        f"id = {json.dumps(identifier)}",
        'type = "update"',
        'name = "Apply safe duplicate links"',
        f"description = {json.dumps(description)}",
        f"agent = {json.dumps(person)}",
        f"instruments = {json.dumps([INSTRUMENT])}",
    ]
    if sources:
        rows.append(f"objects = {json.dumps(sources)}")
    rows += [
        f"results = {json.dumps(results)}",
        f"endTime = {datetime.now(UTC).replace(microsecond=0).isoformat()}",
    ]
    return "\n".join(rows) + "\n"


def add_provenance(
    root: Path,
    pr: int,
    head: str,
    person: str,
    suggestions: list[check_duplicates.Suggestion],
    *,
    content: dict[str, Any],
) -> tuple[str | None, str]:
    path = root / "content" / "provenance.toml"
    old = path.read_text(encoding="utf-8")
    identifier = action_id(pr, head)
    if re.search(rf'(?m)^id\s*=\s*"{re.escape(identifier)}"\s*$', old):
        return None, identifier
    new = old.rstrip() + "\n\n" + action_block(identifier, person, suggestions, content)
    path.write_text(new, encoding="utf-8", newline="\n")
    diff = "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile=str(path), tofile=str(path)
        )
    )
    return diff, identifier


def register_action(root: Path, identifier: str) -> str | None:
    """Append only this action ID, preserving the rest of the reviewed register."""
    path = root / "content" / "identifiers.toml"
    old = path.read_text(encoding="utf-8")
    expected = tomllib.loads(old)
    actions = expected["issued"]["actions"]
    if identifier in expected.get("retired", {}).get("actions", []):
        raise ValueError(f"action identifier {identifier!r} is retired")
    if identifier in actions:
        return None
    section = re.search(r"(?m)^\s*\[issued\][ \t]*(?:#[^\n]*)?$", old)
    if section is None:
        raise ValueError("identifier register has no supported [issued] table")
    following = re.search(r"(?m)^[ \t]*\[", old[section.end() :])
    stop = section.end() + following.start() if following else len(old)
    array = re.search(r"(?m)^[ \t]*actions[ \t]*=[ \t]*(\[[^\]]*\])", old[section.end() : stop])
    if array is None:
        raise ValueError("identifier register has no supported issued actions array")
    start, end = (section.end() + position for position in array.span(1))
    actions.append(identifier)
    new = old[:start] + register_ids.array(actions) + old[end:]
    if tomllib.loads(new) != expected:
        raise ValueError("registering the action would change unrelated identifier data")
    path.write_text(new, encoding="utf-8", newline="\n")
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile=str(path), tofile=str(path)
        )
    )


def apply_safe_suggestions(root: Path, suggestions: list[check_duplicates.Suggestion]) -> tuple[list[str], set[str]]:
    """Apply only suggestions the duplicate check marked safe and the command knows how to place."""
    diffs = []
    changed = set()
    for suggestion in suggestions:
        diff = check_duplicates.apply_suggestion(root, suggestion)
        if diff:
            diffs.append(diff)
            changed.add(suggestion.file)
    return diffs, changed


def load_fix_context(root: Path) -> tuple[dict[str, Any], list[check_duplicates.Suggestion]]:
    content = build_crate.load_content(root / "content")
    accepted = check_duplicates._accepted(root)
    suggestions = [item for item in check_duplicates.check(content, accepted).suggestions if item.safe]
    return content, suggestions


def content_errors(root: Path) -> list[str]:
    content = build_crate.load_content(root / "content")
    accepted = check_duplicates._accepted(root)
    errors = list(check_duplicates.check(content, accepted).errors)
    errors += list(check_content.check(content, root).errors)
    return errors


def apply_and_provenance(
    root: Path,
    pr: int,
    head: str,
    person: str,
    suggestions: list[check_duplicates.Suggestion],
    *,
    content: dict[str, Any],
) -> tuple[list[str], set[str]]:
    diffs, changed = apply_safe_suggestions(root, suggestions)
    if not diffs:
        return diffs, changed
    provenance_diff, identifier = add_provenance(root, pr, head, person, suggestions, content=content)
    if provenance_diff:
        diffs.append(provenance_diff)
        changed.add("content/provenance.toml")
    register_diff = register_action(root, identifier)
    if register_diff:
        diffs.append(register_diff)
        changed.add("content/identifiers.toml")
    return diffs, changed


class GitHub:
    def __init__(self, repository: str, token: str, api: str = "https://api.github.com") -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("invalid repository")
        self.repository = repository
        self.token = token
        self.api = api.rstrip("/")

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.api + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "fair-guide-fix-duplicates",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"GitHub API {method} {path} failed: {error.code} {detail}") from error

    def can_write(self, login: str) -> bool:
        if not login or not re.fullmatch(r"[A-Za-z0-9_.-]+", login):
            return False
        try:
            data = self.request("GET", f"/repos/{self.repository}/collaborators/{login}/permission")
        except RuntimeError:
            return False
        return data.get("permission") in WRITERS or data.get("role_name") in WRITERS

    def pull(self, pr: int) -> dict[str, Any]:
        return self.request("GET", f"/repos/{self.repository}/pulls/{pr}")

    def comment(self, pr: int, body: str) -> None:
        self.request("POST", f"/repos/{self.repository}/issues/{pr}/comments", {"body": body})

    def commit(self, pull: dict[str, Any], files: dict[str, str], message: str) -> str:
        head = pull["head"]["sha"]
        branch = pull["head"]["ref"]
        commit = self.request("GET", f"/repos/{self.repository}/git/commits/{head}")
        blobs = []
        for path, text in sorted(files.items()):
            blob = self.request(
                "POST",
                f"/repos/{self.repository}/git/blobs",
                {"content": base64.b64encode(text.encode("utf-8")).decode("ascii"), "encoding": "base64"},
            )
            blobs.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = self.request(
            "POST",
            f"/repos/{self.repository}/git/trees",
            {"base_tree": commit["tree"]["sha"], "tree": blobs},
        )
        created = self.request(
            "POST",
            f"/repos/{self.repository}/git/commits",
            {"message": message, "tree": tree["sha"], "parents": [head]},
        )
        ref = self.request(
            "PATCH",
            f"/repos/{self.repository}/git/refs/heads/{urllib.parse.quote(branch, safe='/')}",
            {"sha": created["sha"], "force": False},
        )
        return str(ref["object"]["sha"])


def bounded_comment(prefix: str, diff: str, suffix: str) -> str:
    """Keep a pull-request comment below GitHub's limit without losing the commit reference."""
    marker = "\n… diff truncated; the complete change is in the commit."
    budget = COMMENT_LIMIT - len(prefix) - len(suffix) - len(marker) - 14
    if budget < 0:
        raise ValueError("comment prefix and suffix exceed the size limit")
    retained = diff[:budget]
    while True:
        fences = [
            char * max(3, 1 + max((len(match[0]) for match in re.finditer(re.escape(char) + "+", retained)), default=0))
            for char in ("`", "~")
        ]
        fence = min(fences, key=len)
        content = retained + (marker if len(retained) < len(diff) else "")
        text = prefix + fence + "diff\n" + content.rstrip("\n") + "\n" + fence + "\n" + suffix
        if len(text) <= COMMENT_LIMIT:
            return text
        # Pathological runs of both delimiter characters can make the enclosure large.
        # Shrink the retained content and recompute the fence within the same total budget.
        retained = retained[: max(0, len(retained) - (len(text) - COMMENT_LIMIT))]


def refusal(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def run_fix(  # noqa: PLR0911
    root: Path,
    pr: int,
    commenter: str,
    repository: str,
    token: str,
    *,
    check_token: str = "",
    expected_head: str = "",
    dry_run: bool = False,
) -> int:
    if dry_run:
        content, suggestions = load_fix_context(root)
        if not suggestions:
            print("No safe duplicate suggestion applies; no file was changed.")
            return 0
        person = person_for(content, commenter)
        if person is None:
            return refusal(f"No reviewed [[person]] has github = {commenter!r}; no fix was applied.")
        if not instrument_available(content):
            return refusal(f"Instrument {INSTRUMENT!r} is missing from the PR content; rebase before fixing.")
        diffs, changed = apply_and_provenance(root, pr, "dry-run", person, suggestions, content=content)
        if not diffs:
            print("No safe duplicate suggestion could be applied; no file was changed.")
            return 1
        errors = content_errors(root)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print("".join(diffs), end="")
        return 0

    gh = GitHub(repository, token)
    checker = GitHub(repository, check_token) if check_token else gh
    if not checker.can_write(commenter):
        gh.comment(pr, f"@{commenter}, `/fix-duplicates` needs current write access. No file was changed.")
        return 0
    pull = gh.pull(pr)
    default = pull.get("base", {}).get("repo", {}).get("default_branch")
    if (
        pull.get("state") != "open"
        or pull.get("head", {}).get("repo", {}).get("full_name") != repository
        or pull.get("base", {}).get("ref") != default
        or pull.get("head", {}).get("ref") == default
    ):
        gh.comment(
            pr, "`/fix-duplicates` only runs on an open same-repository pull request targeting the default branch."
        )
        return 0
    head = pull["head"]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        return refusal("invalid pull request head")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head) or head != expected_head:
        gh.comment(
            pr,
            "The extracted content does not match the current pull request head; no file was changed. "
            "Rerun the command to extract the current head.",
        )
        return 0
    content, suggestions = load_fix_context(root)
    if not suggestions:
        gh.comment(pr, "No safe duplicate suggestion applies; no file was changed.")
        return 0
    person = person_for(content, commenter)
    if person is None:
        gh.comment(pr, f"No reviewed `[[person]]` has `github = {commenter}`; no fix was applied.")
        return 0
    if not instrument_available(content):
        gh.comment(pr, "The `duplicate-fix` instrument is missing from this branch; rebase before fixing.")
        return 0
    diffs, changed = apply_and_provenance(root, pr, head, person, suggestions, content=content)
    if not diffs:
        gh.comment(pr, "No safe duplicate suggestion could be applied; no file was changed.")
        return 0
    errors = content_errors(root)
    if errors:
        bounded = "\n".join(errors[:20])[:4000]
        gh.comment(pr, bounded_comment("The fix would leave content errors; no file was changed:\n\n", bounded, ""))
        return 0
    current = gh.pull(pr)
    if current.get("head", {}).get("sha") != head:
        gh.comment(
            pr, "The pull request head moved while the fix was prepared; no file was changed. Rerun the command."
        )
        return 0
    files = {path: (root / path).read_text(encoding="utf-8") for path in changed}
    commit = gh.commit(current, files, f"Apply safe duplicate link from /fix-duplicates (PR #{pr})")
    gh.comment(
        pr,
        bounded_comment(
            "Applied the safe duplicate links and their provenance action. The checks will rerun.\n\n",
            "".join(diffs),
            f"\nCommit: `{commit}`.",
        ),
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, required=True, help="root containing the extracted content/ directory")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--commenter", required=True)
    parser.add_argument("--comment", default=COMMAND, help="the exact command body, checked before any action")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.environ.get("GH_TOKEN", ""))
    parser.add_argument("--check-token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--expected-head", default="", help="exact SHA archived by the trusted workflow")
    parser.add_argument("--dry-run", action="store_true", help="apply to the extracted content without calling GitHub")
    args = parser.parse_args(argv)
    if not parse_command(args.comment):
        print("fix_duplicates: only the exact /fix-duplicates command is accepted", file=sys.stderr)
        return 0
    if not args.dry_run and (not args.repository or not args.token):
        parser.error("--repository and --token (or GITHUB_REPOSITORY/GH_TOKEN) are required")
    if not args.dry_run and not re.fullmatch(r"[0-9a-f]{40}", args.expected_head):
        parser.error("--expected-head must name the exact archived commit SHA")
    try:
        return run_fix(
            args.root,
            args.pr,
            args.commenter,
            args.repository,
            args.token,
            check_token=args.check_token,
            expected_head=args.expected_head,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"fix_duplicates: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
