"""Vendor the web fonts the guide uses into assets/fonts/.

Usage: python scripts/vendor_fonts.py [--check]

The life cycle's stage names on the landing are set in Plus Jakarta Sans (SIL Open Font License 1.1). The page loads
nothing from other sites, so the script copies the WOFF2 files of the weights it uses, in the Latin and Latin
Extended subsets that Czech and English need, unchanged from the pinned `@fontsource/plus-jakarta-sans` package in
`node_modules` (install it with `npm ci`); assets/css/app.css declares them with their unicode ranges. With `--check`
the script changes nothing and exits 1 when the vendored fonts differ from the package. Uses only the standard
library.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = Path("node_modules") / "@fontsource" / "plus-jakarta-sans" / "files"
TARGET = Path("assets") / "fonts"
FAMILY = "plus-jakarta-sans"
SUBSETS = ("latin", "latin-ext")
WEIGHTS = (700, 800)


def wanted() -> list[str]:
    return [f"{FAMILY}-{subset}-{weight}-normal.woff2" for subset in SUBSETS for weight in WEIGHTS]


def plan(root: Path = ROOT) -> tuple[dict[str, bytes], list[str], list[str]]:
    """The fonts to write (name → bytes), the stale fonts to remove and the names missing from the package."""
    source, target = root / PACKAGE, root / TARGET
    write, missing = {}, []
    for name in wanted():
        path = source / name
        if not path.is_file():
            missing.append(name)
            continue
        data = path.read_bytes()
        current = target / name
        if not current.is_file() or current.read_bytes() != data:
            write[name] = data
    stale = sorted(path.name for path in target.glob("*.woff2") if path.name not in wanted()) if target.is_dir() else []
    return write, stale, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report differences instead of writing; exit 1 on any")
    args = parser.parse_args(argv)
    if not (ROOT / PACKAGE).is_dir():
        print(f"vendor_fonts: {PACKAGE.as_posix()} not found; run npm ci", file=sys.stderr)
        return 1
    write, stale, missing = plan(ROOT)
    for name in missing:
        print(f"vendor_fonts: {name} is not in the package", file=sys.stderr)
    if args.check:
        for name in write:
            print(f"vendor_fonts: {name} differs from the package", file=sys.stderr)
        for name in stale:
            print(f"vendor_fonts: {name} is not used", file=sys.stderr)
        problems = len(write) + len(stale) + len(missing)
        print(f"vendor_fonts: {len(wanted())} fonts, {problems} problem(s)")
        return 1 if problems else 0
    target = ROOT / TARGET
    target.mkdir(parents=True, exist_ok=True)
    for name, data in write.items():
        (target / name).write_bytes(data)
    for name in stale:
        (target / name).unlink()
    print(f"vendor_fonts: {len(write)} written, {len(stale)} removed")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
