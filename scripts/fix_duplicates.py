#!/usr/bin/env python3
"""Trusted maintainer command: apply safe duplicate link suggestions to a pull request.

The workflow checks out default-branch code, extracts the pull request's content as data, runs this handler,
and commits the changed files back to the pull request branch through the repository-scoped App. It never runs
pull-request code, never merges, and never edits the accepted-duplicates list.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
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
import duplicate_repairs  # noqa: E402
from duplicate_repairs import INSTRUMENT, instrument_available, person_for  # noqa: E402
from handoff import handoff  # noqa: E402

COMMAND = "/fix-duplicates"
COMMENT_LIMIT = 60000
WRITERS = {"admin", "maintain", "write"}


def parse_command(body: str | None) -> bool:
    """Only the exact command is accepted; no arguments, URLs or shell text."""
    return str(body or "").strip() == COMMAND


def action_id(pr: int, head: str) -> str:
    day = datetime.now(UTC).date().isoformat()
    return f"{day}-dupfix-{pr}-{head[:7]}"


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
    new = duplicate_repairs.with_action(old, identifier, person, suggestions, content)
    if new is None:
        return None, identifier
    path.write_text(new, encoding="utf-8", newline="\n")
    return duplicate_repairs.unified_diff(path, old, new), identifier


def register_action(root: Path, identifier: str) -> str | None:
    """Append only this action ID, preserving the rest of the reviewed register."""
    path = root / "content" / "identifiers.toml"
    old = path.read_text(encoding="utf-8")
    new = duplicate_repairs.with_registration(old, identifier)
    if new is None:
        return None
    path.write_text(new, encoding="utf-8", newline="\n")
    return duplicate_repairs.unified_diff(path, old, new)


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
        # Every reply names the run that produced it, so the result can be traced and retried from there.
        run = os.environ.get("GITHUB_RUN_ID", "")
        if re.fullmatch(r"[0-9]+", run):
            server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
            body += f"\n\n[Run]({server}/{self.repository}/actions/runs/{run})"
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


LOCAL_FIX = (
    "run `python scripts/check_duplicates.py --fix` locally and push the result, as `CONTRIBUTING.md` describes."
)


def unchanged(text: str, next_step: str) -> str:
    """A reply for a run that changed nothing: what to do instead, and how a repair shows."""
    return (
        text + "\n\n" + "\n".join(handoff(next_step, LOCAL_FIX, "a `/fix-duplicates` reply names the repair commit."))
    )


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


def admitted(pull: dict[str, Any], repository: str) -> bool:
    """Whether `/fix-duplicates` may change this pull request: open, from this repository, into the default branch from
    another branch. `eligibility()` in `.github/scripts/commands.cjs` decides the same for `/help` and the command gate,
    and a parity test runs both on one case table."""
    default = pull.get("base", {}).get("repo", {}).get("default_branch")
    return (
        pull.get("state") == "open"
        and pull.get("head", {}).get("repo", {}).get("full_name") == repository
        and pull.get("base", {}).get("ref") == default
        and pull.get("head", {}).get("ref") != default
    )


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
        gh.comment(
            pr,
            unchanged(
                f"@{commenter}, `/fix-duplicates` needs current write access. No file was changed.",
                "a maintainer with write access posts `/fix-duplicates`.",
            ),
        )
        return 0
    pull = gh.pull(pr)
    if not admitted(pull, repository):
        gh.comment(
            pr,
            unchanged(
                "`/fix-duplicates` only runs on an open same-repository pull request targeting the default branch.",
                "fix the duplicates on the branch by hand.",
            ),
        )
        return 0
    head = pull["head"]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        return refusal("invalid pull request head")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head) or head != expected_head:
        gh.comment(
            pr,
            unchanged(
                "The extracted content does not match the current pull request head; no file was changed.",
                "post `/fix-duplicates` again to extract the current head.",
            ),
        )
        return 0
    content, suggestions = load_fix_context(root)
    if not suggestions:
        gh.comment(
            pr,
            unchanged(
                "No safe duplicate suggestion applies; no file was changed.",
                "nothing for this command: the review comment lists no safe duplicate link.",
            ),
        )
        return 0
    person = person_for(content, commenter)
    if person is None:
        gh.comment(
            pr,
            unchanged(
                f"No reviewed `[[person]]` has `github = {commenter}`; no fix was applied.",
                f'add a reviewed `[[person]]` with `github = "{commenter}"` to `content/guide.toml`, then post the '
                "command again.",
            ),
        )
        return 0
    if not instrument_available(content):
        gh.comment(
            pr,
            unchanged(
                "The `duplicate-fix` instrument is missing from this branch; no file was changed.",
                "rebase the branch on the default branch, then post the command again.",
            ),
        )
        return 0
    diffs, changed = apply_and_provenance(root, pr, head, person, suggestions, content=content)
    if not diffs:
        gh.comment(
            pr,
            unchanged(
                "No safe duplicate suggestion could be applied; no file was changed.",
                "compare the review comment's suggestions with the branch and fix the duplicates by hand.",
            ),
        )
        return 0
    errors = content_errors(root)
    if errors:
        bounded = "\n".join(errors[:20])[:4000]
        gh.comment(
            pr,
            bounded_comment(
                "The fix would leave content errors; no file was changed:\n\n",
                bounded,
                unchanged("", "fix the listed content errors on the branch, then post the command again."),
            ),
        )
        return 0
    current = gh.pull(pr)
    if current.get("head", {}).get("sha") != head:
        gh.comment(
            pr,
            unchanged(
                "The pull request head moved while the fix was prepared; no file was changed.",
                "post `/fix-duplicates` again.",
            ),
        )
        return 0
    files = {path: (root / path).read_text(encoding="utf-8") for path in changed}
    commit = gh.commit(current, files, f"Apply safe duplicate link from /fix-duplicates (PR #{pr})")
    gh.comment(
        pr,
        bounded_comment(
            "Applied the safe duplicate links and their provenance action. The checks will rerun.\n\n",
            "".join(diffs),
            f"\nCommit: `{commit}`.\n\n"
            + "\n".join(
                handoff(
                    f"the checks rerun on `{commit[:12]}`, and the pull request's author reviews the repair.",
                    "if a check fails on the repair, revert the commit and ask a maintainer.",
                    "the checks pass and a reviewer approves the pull request.",
                )
            ),
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
