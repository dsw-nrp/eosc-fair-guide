"""Print the area labels that a pull request's changed paths call for, by the rules in `.github/repository.toml`.

The trusted review publisher reads the changed paths from the GitHub API, passes them as a JSON list on standard
input and adds the labels printed here. It only ever adds labels. Standard library only, so it runs on a fresh
default-branch checkout without installing anything.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

from audit_repository import CONFIG, ConfigError, load

MAX_PATHS = 6000  # GitHub lists at most 3000 files per pull request, each with an optional previous name


def path_rules(config: dict) -> dict[str, list[str]]:
    """Each declared label with changed-path rules, and its patterns."""
    return {label["name"]: label["paths"] for label in config.get("label", []) if label.get("paths")}


def labels_for(paths: list[str], rules: dict[str, list[str]]) -> list[str]:
    """The labels whose patterns match any path. A pattern's `*` also crosses `/`, as in `fnmatch`."""
    return sorted(
        name
        for name, patterns in rules.items()
        if any(fnmatch.fnmatchcase(path, pattern) for path in paths for pattern in patterns)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=CONFIG, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        paths = json.load(sys.stdin)
        config = load(args.config)
    except (json.JSONDecodeError, ConfigError) as error:
        print(f"area_labels: {error}", file=sys.stderr)
        return 1
    if not isinstance(paths, list) or len(paths) > MAX_PATHS or not all(isinstance(path, str) for path in paths):
        print(f"area_labels: expected a JSON list of at most {MAX_PATHS} paths", file=sys.stderr)
        return 1
    print(json.dumps(labels_for(paths, path_rules(config))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
