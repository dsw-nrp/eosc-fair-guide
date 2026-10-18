#!/usr/bin/env python3
"""The build's own identity, derived from the checked-out git state rather than an authored field.

    python scripts/build_identity.py [--root DIR]      # print this checkout's identity as JSON

`git describe --tags --match 'v*'` gives the version: an exact release tag, or the last tag with how far the build is
ahead of it. A build that is not exactly at a release tag is the unreleased `next` preview; a checkout without a
usable tag is `local`. Only a clean exact tag in production mode is a release. The Tag release dispatch records
its testing/production choice in the annotated tag; other contexts and unmarked tags stay testing. The date is the
release tag's date for a release and the build date otherwise. Uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path

from release_version import version as release_version

ROOT = Path(__file__).resolve().parent.parent
STATUSES = ("testing", "production")
STATUS_TRAILER = "Fair-Guide-Release-Status:"


def _git(root: Path, *args: str) -> str | None:
    """Run a read-only git command, or return None when git or the command is unavailable."""
    try:
        result = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, encoding="utf-8")
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def release_tag(value: str | None) -> bool:
    """Use the same version acceptance as release dispatch and metadata checks."""
    try:
        return bool(value and value.startswith("v") and release_version(value[1:]))
    except ValueError:
        return False


def config_identity(text: str) -> dict:
    """Read the required generated configuration; absent or malformed identity is an error."""
    match = re.search(r"^window\.FairGuideData\.ui = (.*);\r?$", text, re.MULTILINE)
    if not match:
        raise ValueError("the page configuration carries no build identity")
    data = json.loads(match[1])
    built = data.get("config", {}).get("build") if isinstance(data, dict) else None
    if not isinstance(built, dict) or not all(
        key in built for key in ("version", "commit", "channel", "status", "date", "dirty")
    ):
        raise ValueError("the page configuration carries no complete build identity")
    date.fromisoformat(built["date"])
    if built["channel"] not in ("release", "next", "local") or built["status"] not in STATUSES:
        raise ValueError("invalid build channel/status")
    if built["channel"] != "release" and built["status"] != "testing":
        raise ValueError("a build that is not a release must report the testing status")
    if built["channel"] == "release" and (built["dirty"] or not release_tag(built["version"])):
        raise ValueError("a release must have a clean valid release tag")
    if data["config"].get("releaseStatus", built["status"]) != built["status"]:
        raise ValueError("page status differs from its build identity")
    return built


def tag_status(root: Path, tag: str) -> str:
    """Read the immutable dispatch decision; unmarked tags default to testing, malformed markers fail."""
    kind = _git(root, "cat-file", "-t", f"refs/tags/{tag}")
    if kind == "commit":
        return "testing"  # A lightweight tag cannot inherit a marker from its commit message.
    if kind != "tag":
        raise ValueError("cannot read an annotated release tag")
    contents = _git(root, "for-each-ref", "--format=%(contents)", f"refs/tags/{tag}")
    if contents is None:
        raise ValueError("cannot read the release tag's status")
    values = [
        line.removeprefix(STATUS_TRAILER).strip() for line in contents.splitlines() if line.startswith(STATUS_TRAILER)
    ]
    if not values:
        return "testing"
    if len(values) != 1 or values[0] not in STATUSES:
        raise ValueError("release tag must carry one testing/production status marker")
    return values[0]


def identity(root: Path = ROOT, *, today: date | None = None, mode: str | None = None) -> dict[str, object]:
    """The build identity: version, commit, date, channel and resolved release status."""
    commit = _git(root, "rev-parse", "--short", "HEAD") or ""
    dirty = bool(_git(root, "status", "--porcelain"))
    mode = mode or os.environ.get("FAIR_GUIDE_BUILD_CHANNEL", "local")
    if mode not in ("local", "preview", "production"):
        raise ValueError("FAIR_GUIDE_BUILD_CHANNEL must be local, preview or production")
    exact = _git(root, "describe", "--tags", "--exact-match", "--match", "v*")
    requested = os.environ.get("FAIR_GUIDE_RELEASE_TAG") if mode == "production" else None
    if requested:
        target = _git(root, "rev-parse", f"refs/tags/{requested}^{{commit}}") if release_tag(requested) else None
        if not target or target != _git(root, "rev-parse", "HEAD"):
            raise ValueError("the selected production tag does not name this checkout")
        exact = requested
    if release_tag(exact) and not dirty and mode == "production":
        channel, version, base = "release", exact, exact
    else:
        nearest = exact if release_tag(exact) else _git(root, "describe", "--tags", "--abbrev=0", "--match", "v*")
        if release_tag(nearest):
            count = _git(root, "rev-list", "--count", f"{nearest}..HEAD")
            ahead = int(count) if count and count.isdigit() else 0
            channel, version, base = "next" if mode != "local" else "local", f"{nearest}+{ahead}", nearest
        else:
            channel, version, base = "local", commit or "unknown", None
    resolved = tag_status(root, exact) if channel == "release" else "testing"
    when = today or datetime.now(UTC).date()
    if channel == "release" and base:
        tagged = _git(root, "log", "-1", "--format=%cs", base)
        if tagged:
            when = date.fromisoformat(tagged)
    return {
        "version": version,
        "commit": commit,
        "dirty": dirty,
        "channel": channel,
        "base": base,
        "status": resolved,
        "date": when.isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="the checkout to describe (default: the repository)")
    args = parser.parse_args(argv)
    print(json.dumps(identity(args.root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
