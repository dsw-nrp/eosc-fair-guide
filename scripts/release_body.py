#!/usr/bin/env python3
"""Compose a draft release's body from reviewed release notes and the automation's verification record.

    python scripts/release_body.py TAG [--notes PATH] [--repo OWNER/NAME] [--apply]

The notes are the publishable report that ``/aiscr-write-release-notes`` writes to
``.agents/reports/release-notes/eosc-fair-guide_<TAG>.md``; its ``.working.md`` companion is refused. The release
workflow ends each draft body with a marked verification record (commit, archive digest, container image and release
status). That block stays byte for byte; the reviewed notes replace everything before it, without the report's own
title, because the release has a name. Without ``--apply`` the composed body is written to
``.cache/release-notes/<TAG>.md`` and printed for review. ``--apply`` composes again from the current notes and
release, refuses unless the result equals that reviewed file and the release is still an unpublished draft, updates
the body through the GitHub CLI (``gh``) and reads it back. Publishing the draft stays a separate maintainer act.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import release_version

ROOT = Path(__file__).resolve().parent.parent
NAME = "eosc-fair-guide"
NOTES = ROOT / ".agents" / "reports" / "release-notes"
REVIEWED = ROOT / ".cache" / "release-notes"
DEFAULT_REPO = "{owner}/{repo}"
# Written by .github/scripts/release-artifact.cjs (VERIFICATION); a test keeps the two in agreement.
START, END = "<!-- guide-release:verification -->", "<!-- /guide-release:verification -->"


class RefusedError(ValueError):
    """The body cannot be composed or applied safely; the message names the fix."""


def tag_version(tag: str) -> str:
    if not tag.startswith("v"):
        raise RefusedError(f"{tag}: a release tag is v<version>")
    try:
        return release_version.version(tag[1:])
    except ValueError as error:
        raise RefusedError(f"{tag}: {error}") from error


def notes_text(path: Path) -> str:
    """The publishable notes without their title line; working notes and verification markers are refused."""
    if path.name.endswith(".working.md"):
        raise RefusedError(f"{path.name} holds working notes, which are never published; use the publishable report")
    try:
        lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    except OSError as error:
        raise RefusedError(f"{path}: {error.strerror}; run /aiscr-write-release-notes for this tag first") from error
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].startswith("# "):
        lines.pop(0)
    text = "\n".join(lines).strip()
    if not text:
        raise RefusedError(f"{path.name} has no notes below its title")
    if START in text or END in text:
        raise RefusedError(f"{path.name} contains the verification markers, which only the release workflow writes")
    return text


def verification(body: str) -> str:
    """The one marked verification record of a release body."""
    body = body.replace("\r\n", "\n")
    if body.count(START) != 1 or body.count(END) != 1 or body.index(START) > body.index(END):
        raise RefusedError(
            "the release body has no single marked verification record; it was drafted before the record was marked, "
            f"so place {START} and {END} around its automated lines in the GitHub editor and run again"
        )
    return body[body.index(START) : body.index(END) + len(END)]


def compose(notes: str, body: str) -> str:
    return f"{notes}\n\n{verification(body)}"


def gh(*args: str) -> str:
    try:
        done = subprocess.run(["gh", *args], check=True, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError as error:
        raise RefusedError("the GitHub CLI (gh) is needed to read and update the release") from error
    except subprocess.CalledProcessError as error:
        raise RefusedError(f"gh {' '.join(args[:3])} failed: {error.stderr.strip()}") from error
    return done.stdout


def release(tag: str, repo: str) -> dict:
    target = [] if repo == DEFAULT_REPO else ["-R", repo]
    return json.loads(gh("release", "view", tag, *target, "--json", "body,isDraft,url"))


def apply(tag: str, repo: str, composed: str) -> None:
    target = [] if repo == DEFAULT_REPO else ["-R", repo]
    with tempfile.TemporaryDirectory(prefix="release-body-") as scratch:
        path = Path(scratch) / "body.md"
        path.write_text(composed, encoding="utf-8", newline="\n")
        gh("release", "edit", tag, *target, "--notes-file", str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", help="the release tag, for example v1.0.0")
    parser.add_argument(
        "--notes", type=Path, help="the publishable report (default: its /aiscr-write-release-notes path)"
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="OWNER/NAME (default: this checkout's repository)")
    parser.add_argument("--apply", action="store_true", help="update the draft release with the reviewed body")
    args = parser.parse_args(argv)
    reviewed = REVIEWED / f"{args.tag}.md"
    try:
        tag_version(args.tag)
        current = release(args.tag, args.repo)
        composed = compose(notes_text(args.notes or NOTES / f"{NAME}_{args.tag}.md"), current["body"] or "")
        if not args.apply:
            reviewed.parent.mkdir(parents=True, exist_ok=True)
            reviewed.write_text(composed, encoding="utf-8", newline="\n")
            print(composed)
            print(f"\nNext: review the body above, kept in {reviewed.relative_to(ROOT).as_posix()}, then run")
            print(f"  python scripts/release_body.py {args.tag} --apply")
            return 0
        if not current["isDraft"]:
            raise RefusedError(f"{args.tag} is already published; edit a published release only deliberately in GitHub")
        if not reviewed.is_file() or reviewed.read_text(encoding="utf-8") != composed:
            raise RefusedError("the notes or the release changed since the reviewed composition; run without --apply")
        apply(args.tag, args.repo, composed)
        after = release(args.tag, args.repo)
        if (after["body"] or "").replace("\r\n", "\n").strip() != composed.strip():
            raise RefusedError(
                f"the release body differs from the reviewed one after the update; inspect {after['url']}"
            )
    except RefusedError as error:
        print(f"release_body: {error}", file=sys.stderr)
        return 1
    print(f"Updated the draft {args.tag}: {after['url']}")
    print("Next: open the draft, check the notes and the verification record, then publish it in GitHub.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
