"""Check the human documentation's structure and facts offline; with --map, account for every former section.

    python scripts/check_docs.py
    python scripts/check_docs.py --map openspec/changes/<change>/section-map.md

Every human document (both READMEs, CONTRIBUTING and ``docs/**/*.md``) declares one type on its first line, for
example ``<!-- type: how-to -->``. A runbook in ``docs/runbooks/`` is a how-to guide that opens with at most two
sentences, then numbered steps, each with **Where**, **Do**, **Done when** and **If it fails**, within a word
budget. Every Mermaid block carries ``accTitle`` and ``accDescr`` (the diagram check also renders them). Every
repository path, workflow file and npm script a document names exists. ``--map`` reads the section map of a reshape
and fails on any heading of its base revision that the map does not account for. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES = ("landing", "how-to", "reference", "explanation", "tutorial")
DECLARATION = re.compile(r"<!-- type: ([a-z-]+) -->")
RUNBOOKS = "docs/runbooks"
FIELDS = ("Where", "Do", "Done when", "If it fails")
STEP_WORDS = 130
RUNBOOK_WORDS = 1300
# Build output, caches, environments and git-ignored reports a document may name but no checkout holds.
UNTRACKED = ("_site", ".cache", "node_modules", ".venv", ".agents/reports/release-notes", ".agents/local_scratch")
PLACEHOLDER = re.compile(r"[<>*{}$…]|X\.Y|\.\.\.")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
SPAN = re.compile(r"`([^`\n]+)`")
NPM = re.compile(r"\bnpm run(?: -s)? ([a-z0-9:_-]+)")
STEP = re.compile(r"^(\d+)\. (.*)")


def documents(root: Path) -> list[str]:
    found = [name for name in ("README.md", "README_en.md", "CONTRIBUTING.md") if (root / name).is_file()]
    return found + sorted(path.relative_to(root).as_posix() for path in (root / "docs").rglob("*.md"))


def prose(text: str) -> tuple[str, list[str]]:
    """The text outside fenced blocks, and the fenced blocks' contents."""
    outside, fenced, block = [], [], None
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            if block is None:
                block = [line.strip()[3:]]
            else:
                fenced.append("\n".join(block))
                block = None
            continue
        (outside if block is None else block).append(line)
    return "\n".join(outside), fenced


def structure(name: str, text: str) -> list[str]:
    first = text.split("\n", 1)[0].strip()
    declared = DECLARATION.fullmatch(first)
    found = []
    if not declared or declared.group(1) not in TYPES:
        found.append(f"{name}: declare one type on the first line, <!-- type: TYPE -->, TYPE one of {', '.join(TYPES)}")
    _, fenced = prose(text)
    for index, block in enumerate(fenced, 1):
        if block.startswith("mermaid") and not (
            re.search(r"^\s*accTitle\s*:", block, re.M) and re.search(r"^\s*accDescr\s*[:{]", block, re.M)
        ):
            found.append(f"{name}: Mermaid block {index} needs accTitle and accDescr")
    if name.startswith(RUNBOOKS + "/"):
        if declared and declared.group(1) != "how-to":
            found.append(f"{name}: a runbook is a how-to guide; declare <!-- type: how-to -->")
        found += runbook(name, text)
    return found


def runbook(name: str, text: str) -> list[str]:
    outside, _ = prose(text)
    lines = outside.splitlines()[1:]
    found = []
    title = next((index for index, line in enumerate(lines) if line.startswith("# ")), None)
    if title is None:
        return [f"{name}: a runbook starts with a `# ` title"]
    body = lines[title + 1 :]
    start = next((index for index, line in enumerate(body) if STEP.match(line) or line.startswith("#")), len(body))
    opening = " ".join(line.strip() for line in body[:start] if line.strip())
    sentences = [part for part in re.split(r"(?<=[.!?])\s+", opening) if part.strip()]
    if not sentences or len(sentences) > 2:
        found.append(f"{name}: open with one or two sentences on who acts, how long and why ({len(sentences)} now)")
    steps: list[tuple[str, list[str]]] = []
    for line in body:
        match = STEP.match(line)
        if match:
            steps.append((f"step {match.group(1)} ({match.group(2).strip('* ')[:40]})", [line]))
        elif line.startswith("#"):
            steps.append(("", []))  # a heading ends the step before it
        elif steps and steps[-1][0]:
            steps[-1][1].append(line)
    steps = [step for step in steps if step[0]]
    if not steps:
        found.append(f"{name}: give numbered steps, each with {', '.join(FIELDS)}")
    words = 0
    for label, step in steps:
        block = "\n".join(step)
        for field in FIELDS:
            marker = f"**{field}:**"
            if marker not in block:
                found.append(f"{name} {label}: add {marker}")
            else:
                value = block.split(marker, 1)[1]
                value = re.split(r"\n\s*- \*\*(?:Where|Do|Done when|If it fails):\*\*", value, maxsplit=1)[0]
                if not value.strip():
                    found.append(f"{name} {label}: give an action or evidence after {marker}")
        count = len(block.split())
        words += count
        if count > STEP_WORDS:
            found.append(f"{name} {label}: {count} words; keep a step within {STEP_WORDS} and link the reference")
    if words > RUNBOOK_WORDS:
        found.append(f"{name}: steps total {words} words; keep a runbook within {RUNBOOK_WORDS} and split it")
    return found


def scripts(root: Path) -> set[str]:
    try:
        return set(json.loads((root / "package.json").read_text(encoding="utf-8")).get("scripts", {}))
    except (OSError, ValueError):
        return set()


def facts(root: Path, name: str, text: str, npm: set[str]) -> list[str]:
    """Repository paths, workflow files and npm scripts the document names that do not exist."""
    found = []
    where = (root / name).parent
    outside, fenced = prose(text)
    for target in LINK.findall(outside):
        if re.match(r"[a-z][a-z0-9+.-]*:", target):
            continue
        path, _, fragment = target.partition("#")
        linked_path = where / path if path else root / name
        if path and not (where / path).exists():
            found.append(f"{name}: the link target {target} does not exist")
        elif linked_path.suffix == ".md" and fragment and not re.fullmatch(r"L\d+(?:-L\d+)?", fragment):
            linked = linked_path.read_text(encoding="utf-8")
            if fragment not in anchors(linked):
                found.append(f"{name}: the link {target} names a heading {path or name} does not have")
    tokens = [token for span in SPAN.findall(outside) for token in span.split()]
    tokens += [token for block in fenced for token in block.split()]
    tokens += re.findall(r"(?:src|href)=[\"']([^\"'<>]+)[\"']", text)
    tops = {path.name for path in root.iterdir()}
    script_names = {
        path.name
        for folder in ("scripts", ".github/scripts", "assets/js", "tests")
        for path in (root / folder).rglob("*")
        if path.is_file()
    }
    for raw in tokens:
        token = raw.strip("\"'()[],;:").removesuffix(".")
        if not token or PLACEHOLDER.search(token) or "://" in token or token.startswith(("-", "/")):
            continue
        token = re.sub(r":\d+$|#.*$", "", token)
        script_path = re.fullmatch(r"[\w./-]+\.(?:py|mjs|cjs|js)", token)
        if "/" in token and (token.split("/")[0] in tops or script_path):
            ignored = any(token == folder or token.startswith(folder + "/") for folder in UNTRACKED)
            if not ignored and not (root / token).exists():
                found.append(f"{name}: names `{token}`, which does not exist")
        elif re.fullmatch(r"[A-Za-z0-9_.-]+\.ya?ml", token) and not any(
            (root / folder / token).exists() for folder in (".github/workflows", ".github", "")
        ):
            found.append(f"{name}: names the workflow `{token}`, which does not exist")
        elif re.fullmatch(r"[A-Za-z0-9_-]+\.(?:py|mjs|cjs|js)", token) and token not in script_names:
            found.append(f"{name}: names the script `{token}`, which does not exist")
    for script in NPM.findall(outside + "\n" + "\n".join(fenced)):
        if script not in npm:
            found.append(f"{name}: names `npm run {script}`, which package.json does not define")
    return found


def headings(text: str) -> list[str]:
    outside, _ = prose(text)
    return [line.lstrip("#").strip() for line in outside.splitlines() if re.match(r"#{1,6} ", line)]


def former(root: Path, base: str) -> dict[tuple[str, str], int]:
    """Every heading of the human documents at the base revision."""
    listed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", base], cwd=root, capture_output=True, text=True, check=True
    ).stdout.split()
    names = [name for name in listed if name in ("README.md", "README_en.md", "CONTRIBUTING.md")]
    names += [name for name in listed if name.startswith("docs/") and name.endswith(".md")]
    found: dict[tuple[str, str], int] = {}
    for name in names:
        text = subprocess.run(
            ["git", "show", f"{base}:{name}"], cwd=root, capture_output=True, text=True, encoding="utf-8", check=True
        ).stdout
        for heading in headings(text):
            found[(name, heading)] = found.get((name, heading), 0) + 1
    return found


def anchor(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped, spaces as hyphens."""
    text = re.sub(r"[^\w\- ]", "", heading.lower().replace("`", ""))
    return text.replace(" ", "-")


def anchors(text: str) -> set[str]:
    """Include GitHub's numeric suffixes for repeated headings."""
    seen: Counter[str] = Counter()
    result = set()
    for heading in headings(text):
        slug = anchor(heading)
        result.add(slug if not seen[slug] else f"{slug}-{seen[slug]}")
        seen[slug] += 1
    return result


def section_map(root: Path, path: Path) -> list[str]:
    """Former headings the map does not account for, and homes that do not exist.

    The map is a Markdown table, `| Document | Heading | Audience | Type | Home |`, after a `Base:` line naming the
    full commit the reshape started from. A home is `path#anchor`, or `removed: <reason>`.
    """
    text = path.read_text(encoding="utf-8")
    base = re.search(r"^Base: `?([0-9a-f]{40})`?", text, re.M)
    if not base:
        return [f"{path}: name the full commit the reshape started from on a `Base:` line"]
    entries = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 5 and cells[0] not in ("Document", "---"):
            entries.append(dict(zip(("document", "heading", "audience", "type", "home"), cells, strict=True)))
    accounted = Counter((entry["document"], entry["heading"]) for entry in entries)
    found = [
        f'{path}: add a row for {document} "{heading}" with its audience, type and home or removal reason'
        for (document, heading), count in sorted(former(root, base.group(1)).items())
        for _ in range(max(0, count - accounted[(document, heading)]))
    ]
    for entry in entries:
        label = f'{entry["document"]} "{entry["heading"]}"'
        if entry["type"] not in TYPES or not entry["audience"] or not entry["home"]:
            found.append(f"{path}: {label} needs an audience, a type ({', '.join(TYPES)}) and a home or removal")
            continue
        if entry["home"].startswith("removed:"):
            if not entry["home"].removeprefix("removed:").strip():
                found.append(f"{path}: {label} needs a removal reason")
            continue
        target, _, fragment = entry["home"].partition("#")
        if not (root / target).is_file():
            found.append(f"{path}: {label} moves to {target}, which does not exist")
        elif fragment and fragment not in anchors((root / target).read_text("utf-8")):
            found.append(f"{path}: {label} moves to {entry['home']}, but {target} has no such heading")
    return found


def agreement(root: Path) -> list[str]:
    """The two READMEs are one landing page in two languages: the same outline and the same links."""
    texts = {name: (root / name).read_text(encoding="utf-8") for name in ("README.md", "README_en.md")}

    def outline(text: str) -> list[int]:
        outside, _ = prose(text)
        return [len(line) - len(line.lstrip("#")) for line in outside.splitlines() if re.match(r"#{1,6} ", line)]

    def links(text: str) -> list[str]:
        outside, _ = prose(text)
        return [target for target in LINK.findall(outside) if not target.startswith(("README", "http", "#"))]

    cs, en = texts["README.md"], texts["README_en.md"]
    found = []
    if outline(cs) != outline(en):
        found.append("README.md and README_en.md: keep the same headings in the same order and levels")
    if links(cs) != links(en):
        missing = sorted(set(links(cs)) ^ set(links(en)))
        found.append(
            "README.md and README_en.md: link the same documents in the same order"
            + (f"; only one links {', '.join(missing)}" if missing else "")
        )
    return found


def problems(root: Path = ROOT) -> list[str]:
    npm = scripts(root)
    found = []
    for name in documents(root):
        text = (root / name).read_text(encoding="utf-8")
        found += structure(name, text) + facts(root, name, text, npm)
    if (root / "README.md").is_file() and (root / "README_en.md").is_file():
        found += agreement(root)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--map", type=Path, help="a section map whose former headings must all be accounted for")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    found = problems(args.root)
    if args.map:
        found += section_map(args.root, args.map if args.map.is_absolute() else args.root / args.map)
    for problem in found:
        print(problem, file=sys.stderr)
    count = len(documents(args.root))
    print(f"check_docs: {len(found)} problems in {count} documents" if found else f"check_docs: {count} documents pass")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
