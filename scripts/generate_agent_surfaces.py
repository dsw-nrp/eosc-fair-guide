"""Generate guide-owned vendor readers, skill copies and documentation inventory; --check writes nothing."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_surfaces import ROOT, load, path_at, replace_native, text_at

INVENTORY_BEGIN = "<!-- begin:guide:inventory -->"
INVENTORY_END = "<!-- end:guide:inventory -->"


def inventory(config: dict, receipt: dict) -> str:
    groups: dict[tuple[str, str], list[str]] = {}
    for relative, record in receipt["files"].items():
        groups.setdefault(("Delivered", record["asset"]), []).append(relative)
    for relative, entries in receipt["sections"].items():
        for name, record in entries.items():
            groups.setdefault(("Delivered section", record["asset"]), []).append(f"{relative}:{name}")
    for row in [*config["rules"], *config["skills"]]:
        groups[("Native generated", row["id"])] = [*row["outputs"]]
    lines = [INVENTORY_BEGIN, "", "| Ownership | Asset | Paths |", "| --- | --- | --- |"]
    for (owner, asset), paths in sorted(groups.items()):
        lines.append(f"| {owner} | `{asset}` | " + ", ".join(f"`{path}`" for path in sorted(paths)) + " |")
    lines += ["", "Templates are listed only when present in the delivery receipt.", "", INVENTORY_END]
    return "\n".join(lines)


def render(root: Path) -> dict[str, bytes]:
    config, receipt = load(root)
    outputs = {}
    native = ["<!-- begin:guide:native -->\n"]
    for row in config["rules"]:
        body = text_at(root, row["source"]).replace("\r\n", "\n").rstrip() + "\n"
        banner = f"<!-- Generated from {row['source']}; run scripts/generate_agent_surfaces.py. -->\n\n"
        for relative in row["outputs"]:
            header = ""
            if relative.endswith(".mdc"):
                header = f"---\ndescription: {row['description']}\nalwaysApply: true\n---\n\n"
            elif relative.endswith(".instructions.md"):
                header = '---\napplyTo: "**"\n---\n\n'
            outputs[relative] = (header + banner + body).encode("utf-8")
        native.append(f"<!-- begin:guide:{row['id']} -->\n{banner}{body}<!-- end:guide:{row['id']} -->\n")
    native.append("<!-- end:guide:native -->\n")
    outputs[config["mixed"]] = replace_native(text_at(root, config["mixed"]), "\n".join(native)).encode("utf-8")
    for row in config["skills"]:
        source = text_at(root, row["source"]).replace("\r\n", "\n").encode("utf-8")
        for relative in row["outputs"]:
            outputs[relative] = source
    document = text_at(root, config["inventory"])
    if document.count(INVENTORY_BEGIN) != 1 or document.count(INVENTORY_END) != 1:
        raise ValueError("documentation requires exactly one inventory region")
    before, rest = document.split(INVENTORY_BEGIN)
    _, after = rest.split(INVENTORY_END)
    outputs[config["inventory"]] = (before + inventory(config, receipt) + after).encode("utf-8")
    return outputs


def generate(root: Path, check: bool = False) -> list[str]:
    outputs = render(root)
    changed = []
    for relative, expected in outputs.items():
        path = path_at(root, relative)
        if not path.is_file() or path.read_bytes() != expected:
            changed.append(relative)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        changed = generate(args.root.resolve(), args.check)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"generate_agent_surfaces: {error}")
        return 1
    for relative in changed:
        print(f"{relative}: {'missing or drifted' if args.check else 'generated'}")
    if args.check and changed:
        config, _ = load(args.root.resolve())
        for row in config["skills"]:
            if set(changed).intersection(row["outputs"]):
                print(f"Skill source {row['source']}; identical mirrors: {', '.join(row['outputs'])}")
    print(f"generate_agent_surfaces: {len(changed)} {'difference(s)' if args.check else 'updated file(s)'}")
    return int(args.check and bool(changed))


if __name__ == "__main__":
    raise SystemExit(main())
