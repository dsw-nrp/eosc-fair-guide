"""Vendor the Font Awesome Free icons that the guide names into assets/icons/.

Usage: python scripts/vendor_icons.py [--check]

Icon names come from `content/icons.toml` and from every `icon` field in the content files. Each named icon is
copied unchanged from `svgs/solid/` of the pinned `@fortawesome/fontawesome-free` package in `node_modules`, or from
`svgs/brands/` for a brand mark such as `github` (install it with `npm ci`), and icons that are no longer named are
removed. With `--check` the script changes
nothing and exits 1 when the vendored icons differ from what the content names. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = Path("node_modules") / "@fortawesome" / "fontawesome-free" / "svgs"
STYLES = ("solid", "brands")  # a name is looked up in this order
TARGET = Path("assets") / "icons"


def _icon_values(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "icon" and isinstance(item, str):
                yield item
            else:
                yield from _icon_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _icon_values(item)


def named_icons(root: Path = ROOT) -> set[str]:
    """Every icon name the content uses: the interface map and all `icon` fields."""
    names: set[str] = set()
    content = root / "content"
    for path in sorted(content.rglob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if path.name == "icons.toml":
            names.update(str(name) for name in data.get("ui", {}).values())
        names.update(_icon_values(data))
    return names


def plan(root: Path = ROOT) -> tuple[dict[str, bytes], list[str], list[str]]:
    """Return the icons to write (name → bytes), the stale icons to remove, and names missing from the package."""
    source = root / PACKAGE
    target = root / TARGET
    wanted = named_icons(root)
    write: dict[str, bytes] = {}
    missing = []
    for name in sorted(wanted):
        svg = next(
            (source / style / f"{name}.svg" for style in STYLES if (source / style / f"{name}.svg").is_file()), None
        )
        if svg is None:
            missing.append(name)
            continue
        data = svg.read_bytes()
        current = target / f"{name}.svg"
        if not current.is_file() or current.read_bytes() != data:
            write[name] = data
    stale = sorted(path.stem for path in target.glob("*.svg") if path.stem not in wanted) if target.is_dir() else []
    return write, stale, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report differences instead of writing; exit 1 on any")
    args = parser.parse_args(argv)
    if not (ROOT / PACKAGE).is_dir():
        print(f"vendor_icons: {PACKAGE.as_posix()} not found; run npm ci", file=sys.stderr)
        return 2
    write, stale, missing = plan()
    for name in missing:
        print(f"vendor_icons: '{name}' is not a Font Awesome Free solid or brand icon", file=sys.stderr)
    if args.check:
        for name in write:
            print(f"vendor_icons: assets/icons/{name}.svg is missing or differs from the package", file=sys.stderr)
        for name in stale:
            print(f"vendor_icons: assets/icons/{name}.svg is no longer named by the content", file=sys.stderr)
        return 1 if write or stale or missing else 0
    target = ROOT / TARGET
    target.mkdir(parents=True, exist_ok=True)
    for name, data in write.items():
        (target / f"{name}.svg").write_bytes(data)
    for name in stale:
        (target / f"{name}.svg").unlink()
    print(f"vendor_icons: {len(write)} written, {len(stale)} removed")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
