"""Refuse private planning/workstation details in public source; optionally inspect local commit messages.

Usage: python scripts/check_public_content.py [--root DIR] [--history]
Reports only relative file/line or commit IDs and the rule, never a sensitive matching value. Does not rewrite
files or history. Public author attribution and portable container/example paths are intentionally permitted.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tomllib
from pathlib import Path

from agent_surfaces import CONFIG, matches

ROOT = Path(__file__).resolve().parents[1]
AREAS = (
    "content",
    "docs",
    "assets",
    "scripts",
    "tests",
    "openspec",
    ".github",
    ".agents",
    ".claude",
    ".cursor",
    ".kilo",
    ".codex",
    ".gemini",
    ".devcontainer",
)
TEXT = {
    ".md",
    ".mdc",
    ".toml",
    ".py",
    ".js",
    ".mjs",
    ".css",
    ".html",
    ".svg",
    ".json",
    ".jsonc",
    ".rules",
    ".yaml",
    ".yml",
    ".cff",
    ".txt",
}
RULES = {
    "private planning repository": re.compile("aiscr-" + "management", re.I),
    "private planning extracts": re.compile(r"notes[/\\]" + "extracted", re.I),
    "local planning scratch": re.compile(
        r"(?:[A-Za-z]:[/\\]|(?<![\w.:/])/)[^\s\"'`<>]*" + r"\.agents[/\\]" + "local_scratch", re.I
    ),
    "personal workstation path": re.compile(r"(?:[A-Z]:[/\\](?:Users|David)[/\\]|/" + "Users" + r"/[^/]+/)", re.I),
}


def violations(text: str) -> list[tuple[int, str]]:
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        for name, pattern in RULES.items():
            candidate = re.sub(r"https?://[^\s\"']+", "", line) if name == "personal workstation path" else line
            if pattern.search(candidate):
                findings.append((number, name))
    return findings


def runtime_hand_offs(root: Path, paths: set[Path]) -> set[Path]:
    """Untracked files in the runtime paths that .agents/guide/surfaces.toml declares, such as the run hand-offs in
    .agents/local_scratch, which stay visible to Git by design and name machine-local locations. They are not public
    source until someone stages them; a tracked or staged file is always checked. Outside a Git work tree, or without
    the declaration, nothing is skipped."""
    try:
        patterns = tomllib.loads((root / CONFIG).read_text(encoding="utf-8"))["runtime"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return set()
    candidates = {path for path in paths if matches(path.relative_to(root).as_posix(), patterns)}
    if not candidates:
        return set()
    names = sorted(path.relative_to(root).as_posix() for path in candidates)
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", *names], cwd=root, capture_output=True, text=True, encoding="utf-8", check=False
    )
    if result.returncode != 0:
        return set()
    return candidates - {root / name for name in result.stdout.split("\0") if name}


def files(root: Path) -> list[Path]:
    found = {path for path in root.iterdir() if path.is_file() and path.suffix in TEXT}
    for area in AREAS:
        directory = root / area
        if directory.exists():
            found.update(
                path
                for path in directory.rglob("*")
                if path.is_file() and path.suffix in TEXT and "__pycache__" not in path.parts
            )
    return sorted(found - runtime_hand_offs(root, found))


def inspect(root: Path, history: bool = False) -> list[str]:
    findings = [
        f"{path.relative_to(root).as_posix()}:{line}: {rule}"
        for path in files(root)
        for line, rule in violations(path.read_text(encoding="utf-8"))
    ]
    if history:
        result = subprocess.run(
            ["git", "log", "--all", "--format=%H%x00%B%x00"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        parts = result.stdout.split("\0")
        for index in range(0, len(parts) - 1, 2):
            sha = parts[index].strip()
            findings.extend(f"commit {sha}: {rule}" for _, rule in violations(parts[index + 1]))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    findings = inspect(args.root.resolve(), args.history)
    for finding in findings:
        print(finding)
    print(f"check_public_content: {len(findings)} finding(s); history {'included' if args.history else 'not scanned'}")
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
