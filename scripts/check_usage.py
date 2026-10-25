"""Check the Guide's usage entries: dated filenames and the delivered canonical field labels.

Each entry in ``.agents/reports/usage/`` is named ``usage-YYYY-MM-DD-<topic>.md`` with a real date equal to the
entry's first ``When``, and carries every mandatory label of the delivered usage-logging rule. A later session of a
rolling entry keeps the original filename. Each violation names the file and the exact rename or missing label.

Usage: python scripts/check_usage.py [--root DIR]
Uses only the Python standard library and writes nothing.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ".agents/reports/usage"
NAME = re.compile(r"usage-(\d{4}-\d{2}-\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md")
WHEN = re.compile(r"^- \*\*When:\*\* *(\d{4}-\d{2}-\d{2})", re.MULTILINE)
# The mandatory field set of the delivered aiscr-usage-logging rule, in its exact label form.
LABELS = ("When", "Agent / runtime", "Model / backend", "What", "Impacted", "Close-out")


def real(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def topic(stem: str) -> str:
    """The topic a misnamed entry already carries, without any date it was given."""
    rest = re.sub(r"^\d{4}-\d{2}-\d{2}-?", "", stem.removeprefix("usage-"))
    return re.sub(r"[^a-z0-9]+", "-", rest.lower()).strip("-") or "<topic>"


def errors(root: Path) -> list[str]:
    found = []
    folder = root / FOLDER
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        name = f"{FOLDER}/{path.name}"
        text = path.read_text(encoding="utf-8")
        first = WHEN.search(text)
        started = real(first.group(1)) if first else None
        match = NAME.fullmatch(path.name)
        if not started:
            found.append(f"{name}: no `- **When:** YYYY-MM-DD` line dates the entry's first session")
        elif not match or real(match.group(1)) != started:
            expected = f"{FOLDER}/usage-{started.isoformat()}-{match.group(2) if match else topic(path.stem)}.md"
            found.append(
                f"{name}: rename it to {expected} (git mv '{name}' '{expected}'); an entry is named "
                "usage-YYYY-MM-DD-<topic>.md after its first `When` date and keeps that name for later sessions"
            )
        for label in LABELS:
            if f"**{label}:**" not in text:
                found.append(f"{name}: add the `**{label}:**` field, the exact label of the delivered usage rule")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    found = errors(args.root)
    for error in found:
        print(error, file=sys.stderr)
    entries = len(list((args.root / FOLDER).glob("*.md")))
    outcome = f"{len(found)} problems in {entries} usage entries" if found else f"all {entries} usage entries pass"
    print(f"check_usage: {outcome}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
