#!/usr/bin/env python3
"""Check the changelog's unpublished section and protect published release history.

    python scripts/check_changelog.py [--base REF]

`CHANGELOG.md` keeps exactly one `## [Unreleased]` section above the releases. Its entries are curated by
people; an empty section is valid, but category headings without entries or placeholder text are not. With
`--base`, every released section must keep its bytes from where this branch left the base, as in a pull request.
The one accepted history change is a complete release transition: one new dated section, directly below an empty
`[Unreleased]`, that starts with the base's unpublished notes. Release preparation reuses this parser to keep
those notes. The check reads no pull-request text and never edits the changelog.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = "CHANGELOG.md"
UNRELEASED = "Unreleased"
# Release preparation generates these headings; curated notes use the semantic categories instead.
MERGED, DIRECT = "Merged pull requests", "Direct commits"
RESERVED = (MERGED, DIRECT)
HEADING = re.compile(r"(?m)^## (?P<title>[^\r\n]*)$")
CATEGORY = re.compile(r"^#{3,} +(?P<title>.+?)\s*#*\s*$")
COMMENT = re.compile(r"<!--.*?-->", re.S)
PLACEHOLDER = re.compile(r"(?i)^[-*+]?\s*(?:tbd|todo|tba|n/?a|none|\.\.\.|…)?\s*\.?$")


@dataclass(frozen=True)
class Section:
    title: str
    text: str  # the heading line through the end of the section, exactly as written
    body: str

    @property
    def key(self) -> str:
        """The bracketed version label, or the whole title for an unbracketed heading."""
        match = re.match(r"\[([^\]]+)\]", self.title)
        return match[1] if match else self.title.strip()

    @property
    def unreleased(self) -> bool:
        return self.key == UNRELEASED


def parse(text: str) -> tuple[str, list[Section]]:
    """Split a changelog into its preamble and level-two sections, keeping each section's exact text."""
    text = text.replace("\r\n", "\n")
    matches = list(HEADING.finditer(text))
    preamble = text[: matches[0].start()] if matches else text
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append(Section(match["title"], text[match.start() : end], text[match.end() : end]))
    return preamble, sections


def reserved_headings(body: str) -> list[str]:
    """Generated-lineage headings used inside curated notes."""
    found = []
    for line in COMMENT.sub("", body).splitlines():
        match = CATEGORY.match(line.strip())
        if match and match["title"].casefold() in {name.casefold() for name in RESERVED}:
            found.append(match["title"])
    return found


def entry_problems(body: str) -> list[str]:
    """Empty is valid; otherwise each category heading needs an entry and no line may be a bare placeholder."""
    lines = [line.strip() for line in COMMENT.sub("", body).splitlines()]
    if not any(lines):
        return []
    problems = []
    category, entries = None, 0
    meaningful = 0
    for line in [*lines, "### end"]:
        heading = CATEGORY.match(line)
        if heading:
            if category is not None and not entries:
                problems.append(f"category `{category}` has no entries")
            category, entries = heading["title"], 0
            continue
        if not line:
            continue
        if PLACEHOLDER.fullmatch(line):
            problems.append(f"placeholder `{line}` is not an entry")
            continue
        entries += 1
        meaningful += 1
    if not meaningful and not problems:
        problems.append("it has headings but no entries")
    return problems


def unreleased_section(sections: list[Section]) -> Section | None:
    found = [section for section in sections if section.unreleased]
    return found[0] if len(found) == 1 else None


def structure_errors(text: str) -> list[str]:
    """Problems a reader of this file alone can see, each with its fix."""
    _, sections = parse(text)
    errors = []
    unreleased = [index for index, section in enumerate(sections) if section.unreleased]
    if not unreleased:
        errors.append(f"{FILE} has no `## [{UNRELEASED}]` section; add an empty one above the newest release")
    elif len(unreleased) > 1:
        errors.append(f"{FILE} has {len(unreleased)} `## [{UNRELEASED}]` sections; merge them into one")
    elif unreleased[0] != 0:
        errors.append(f"`## [{UNRELEASED}]` must be the first section, above every release")
    if len(unreleased) == 1:
        body = sections[unreleased[0]].body
        for problem in entry_problems(body):
            errors.append(f"`[{UNRELEASED}]`: {problem}; write the change it describes or remove it")
        for heading in reserved_headings(body):
            errors.append(
                f"`[{UNRELEASED}]` uses `{heading}`, which release preparation generates; use a category such as "
                "Added, Changed or Fixed"
            )
    keys = [section.key for section in sections if not section.unreleased]
    for key in sorted({key for key in keys if keys.count(key) > 1}):
        errors.append(f"release `{key}` appears {keys.count(key)} times")
    return errors


def history_errors(previous: str, text: str, base_label: str) -> list[str]:
    """Released sections keep their bytes; a single complete release transition is the only addition."""
    _, base_sections = parse(previous)
    _, sections = parse(text)
    base_released = {section.key: section.text for section in base_sections if not section.unreleased}
    released = [section for section in sections if not section.unreleased]
    current = {section.key: section.text for section in released}
    errors = []
    for key, original in base_released.items():
        if key not in current:
            errors.append(f"release `{key}` was removed since {base_label}; published history is not rewritten")
        elif current[key] != original:
            errors.append(
                f"release `{key}` changed since {base_label}; record the correction in `[{UNRELEASED}]` for the "
                "next release instead"
            )
    added = [section for section in released if section.key not in base_released]
    if not added:
        return errors
    if len(added) > 1:
        return [*errors, "only one new release section may be added at a time, by release preparation"]
    new = added[0]
    if released[0] is not new:
        errors.append(f"new release `{new.key}` must directly follow `[{UNRELEASED}]`")
    head_unreleased = unreleased_section(sections)
    if head_unreleased is not None and head_unreleased.body.strip():
        errors.append(f"a release transition leaves `[{UNRELEASED}]` empty; `{new.key}` was added beside new notes")
    base_unreleased = unreleased_section(base_sections)
    notes = base_unreleased.body.strip() if base_unreleased else ""
    if notes and not new.body.strip().startswith(notes):
        errors.append(f"new release `{new.key}` does not start with the `[{UNRELEASED}]` notes of {base_label}")
    return errors


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, encoding="utf-8").stdout


def base_text(root: Path, ref: str) -> tuple[str | None, str]:
    """The changelog where this branch left `ref`, as a pull request compares it; None when it did not exist."""
    sha = git(root, "merge-base", ref, "HEAD").strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha):
        raise ValueError(f"no merge base with {ref}")
    try:
        return git(root, "show", f"{sha}:{FILE}"), sha[:7]
    except subprocess.CalledProcessError:
        return None, sha[:7]


def check(root: Path, base: str | None = None) -> tuple[list[str], str]:
    text = (root / FILE).read_text(encoding="utf-8")
    errors = structure_errors(text)
    if not base:
        return errors, "history not compared: no --base"
    previous, label = base_text(root, base)
    if previous is None:
        return errors, f"history not compared: {FILE} is new since {label}"
    return [*errors, *history_errors(previous, text, label)], f"compared with {label}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="git reference whose merge base keeps the published release history")
    args = parser.parse_args(argv)
    try:
        errors, scope = check(ROOT, args.base)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"check_changelog: {error}", file=sys.stderr)
        return 1
    for error in errors:
        print(f"{FILE}: {error}")
    if errors:
        print(f"check_changelog: {len(errors)} problem(s); see docs/changelog.md ({scope})")
        return 1
    print(f"check_changelog: [{UNRELEASED}] and released sections are consistent ({scope})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
