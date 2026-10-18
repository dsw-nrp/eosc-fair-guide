"""Shared ownership, receipt and mixed-section primitives for repository-native agent tooling."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import tomllib
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ".agents/guide/surfaces.toml"
MARKER = re.compile(r"<!-- (begin|end):(generated|guide):([a-z0-9][a-z0-9-]*) -->")


def path_at(root: Path, relative: str) -> Path:
    """Refuse traversal and paths that escape through a symlink before any read or write."""
    posix, windows = PurePosixPath(relative), PureWindowsPath(relative)
    if (
        not relative
        or relative == "."
        or str(posix) != relative
        or "\\" in relative
        or ":" in relative
        or posix.is_absolute()
        or windows.drive
        or ".." in posix.parts
    ):
        raise ValueError(f"unsafe managed path: {relative}")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"managed path escapes root: {relative}")
    if path.resolve() != root.resolve() / relative:
        raise ValueError(f"managed path aliases another file: {relative}")
    return path


def text_at(root: Path, relative: str) -> str:
    return path_at(root, relative).read_bytes().decode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def matches(relative: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(relative, pattern) for pattern in patterns)


def blocks(text: str) -> list[tuple[str, str, int, int]]:
    """Return top-level byte-preserving text spans, rejecting ambiguous ownership markers."""
    stack: list[tuple[str, str, int]] = []
    seen: set[tuple[str, str]] = set()
    found = []
    offset = 0
    for line in text.splitlines(keepends=True):
        marker = MARKER.fullmatch(line.rstrip("\r\n"))
        if not marker:
            if re.match(r"<!-- (?:begin|end):(?:generated|guide):", line):
                raise ValueError("malformed ownership marker")
        else:
            action, kind, name = marker.groups()
            if action == "begin":
                if (kind, name) in seen or (stack and stack[-1][0] != kind):
                    raise ValueError(f"duplicate or crossing section: {kind}:{name}")
                seen.add((kind, name))
                stack.append((kind, name, offset))
            else:
                if not stack or stack[-1][:2] != (kind, name):
                    raise ValueError(f"unmatched section end: {kind}:{name}")
                _, _, start = stack.pop()
                if not stack:
                    found.append((kind, name, start, offset + len(line)))
        offset += len(line)
    if stack:
        raise ValueError(f"unclosed section: {stack[-1][0]}:{stack[-1][1]}")
    return found


def sections(text: str, kind: str) -> dict[str, str]:
    return {name: text[start:end] for owner, name, start, end in blocks(text) if owner == kind}


def replace_native(text: str, body: str) -> str:
    native = [(start, end) for kind, name, start, end in blocks(text) if kind == "guide" and name == "native"]
    if len(native) != 1 or set(sections(text, "guide")) != {"native"}:
        raise ValueError("mixed reader requires exactly one guide:native region")
    start, end = native[0]
    return text[:start] + body + text[end:]


def load(root: Path) -> tuple[dict, dict]:
    config = tomllib.loads(text_at(root, CONFIG))
    if config.get("format") != 1:
        raise ValueError("unsupported ownership-map format")
    for field in ("managed", "owned", "tool_generated", "runtime"):
        if not isinstance(config.get(field), list):
            raise ValueError(f"missing ownership-map field: {field}")
        for relative in config[field]:
            path_at(root, relative)
    for field in ("manifest", "mixed", "inventory"):
        path_at(root, config[field])
    outputs: set[str] = set()
    ids: set[str] = set()
    # Case-only aliases must be safe on every supported filesystem, including Windows.
    sources = {row["source"].casefold() for row in [*config["rules"], *config["skills"]]}
    protected = [pattern.casefold() for pattern in config["owned"] + config["tool_generated"] + config["runtime"]]
    for row in [*config["rules"], *config["skills"]]:
        if not re.fullmatch(r"fair-guide-[a-z0-9-]+", row["id"]) or row["id"] in ids:
            raise ValueError("duplicate or invalid native identity")
        ids.add(row["id"])
        path_at(root, row["source"])
        for relative in row["outputs"]:
            path_at(root, relative)
            key = relative.casefold()
            if key in {path.casefold() for path in (CONFIG, config["manifest"], config["mixed"], config["inventory"])}:
                raise ValueError(f"reserved output: {relative}")
            if key in sources or matches(key, protected):
                raise ValueError(f"conflicting generated ownership: {relative}")
            if key in {path.casefold() for path in outputs}:
                raise ValueError(f"duplicate output: {relative}")
            outputs.add(relative)
    receipt = json.loads(text_at(root, config["manifest"]))
    if receipt.get("format") != 1 or not isinstance(receipt.get("files"), dict):
        raise ValueError("unsupported delivery receipt")
    if set(receipt.get("sections", {})) != {config["mixed"]} or not receipt["sections"][config["mixed"]]:
        raise ValueError("receipt requires mixed reader sections")
    for relative, record in receipt["files"].items():
        path_at(root, relative)
        validate_record(record)
        if relative in outputs or matches(relative, config["owned"] + config["tool_generated"] + config["runtime"]):
            raise ValueError(f"conflicting delivered ownership: {relative}")
    if config["mixed"] in receipt["files"] or config["manifest"] in receipt["files"]:
        raise ValueError("receipt cannot hash itself or the whole mixed reader")
    for name, record in receipt["sections"][config["mixed"]].items():
        if not re.fullmatch(r"aiscr-[a-z0-9-]+", name):
            raise ValueError(f"invalid delivered section identity: {name}")
        validate_record(record)
    return config, receipt


def validate_record(record: dict) -> None:
    if not isinstance(record, dict) or not isinstance(record.get("asset"), str):
        raise ValueError("invalid delivery asset record")
    if not re.fullmatch(r"[a-f0-9]{64}", str(record.get("sha256", ""))):
        raise ValueError("invalid delivery SHA-256")


def classify(relative: str, config: dict, receipt: dict) -> str | None:
    if relative == config["mixed"]:
        return "mixed"
    if relative == config["manifest"] or relative in receipt["files"]:
        return "delivered"
    if any(relative in row["outputs"] for row in [*config["rules"], *config["skills"]]):
        return "generated"
    for field, owner in (("owned", "owned"), ("tool_generated", "tool-generated"), ("runtime", "runtime")):
        if matches(relative, config[field]):
            return owner
    return None


def managed_files(root: Path, config: dict) -> list[str]:
    found: set[str] = set()
    for relative in config["managed"]:
        path = path_at(root, relative)
        if path.is_file():
            found.add(relative)
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file():
                    name = child.relative_to(root).as_posix()
                    path_at(root, name)
                    found.add(name)
    return sorted(found)


def ownership_findings(root: Path, config: dict, receipt: dict) -> list[str]:
    return [
        f"{relative}: unclassified managed file"
        for relative in managed_files(root, config)
        if classify(relative, config, receipt) is None
    ]


def delivery_findings(root: Path, config: dict, receipt: dict) -> list[str]:
    findings = ownership_findings(root, config, receipt)
    for relative, record in receipt["files"].items():
        path = path_at(root, relative)
        if not path.is_file():
            findings.append(f"{relative}: missing delivered file")
        elif digest(path.read_bytes()) != record["sha256"]:
            findings.append(f"{relative}: modified delivered file")
    relative = config["mixed"]
    if not path_at(root, relative).is_file():
        return [*findings, f"{relative}: missing mixed reader"]
    text = text_at(root, relative)
    actual = sections(text, "generated")
    expected = receipt["sections"][relative]
    for name in sorted(set(actual) | set(expected)):
        if name not in actual:
            findings.append(f"{relative}:{name}: missing delivered section")
        elif name not in expected:
            findings.append(f"{relative}:{name}: extra delivered section")
        elif digest(actual[name].encode("utf-8")) != expected[name]["sha256"]:
            findings.append(f"{relative}:{name}: modified delivered section")
    cursor = 0
    for _, _, start, end in blocks(text):
        if text[cursor:start].strip():
            findings.append(f"{relative}: extra content outside owned sections")
        cursor = end
    if text[cursor:].strip():
        findings.append(f"{relative}: extra content outside owned sections")
    if set(sections(text, "guide")) != {"native"}:
        findings.append(f"{relative}: missing or extra native region")
    return findings
