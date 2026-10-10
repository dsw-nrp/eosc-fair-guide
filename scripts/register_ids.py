"""Register the identifiers of new entries in content/identifiers.toml.

Usage: python scripts/register_ids.py [--content DIR]

The register lists every identifier the guide has issued, by kind. The script adds the identifiers the content has
and the register lacks, after the ones already there; it never removes, reorders or renames one. An entry that goes
away keeps its identifier: add it under its kind in [retired] by hand, and it can never name another entry. The rules
are in docs/content-model.md, Identifiers. Uses only the standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_crate import CONTENT, load_content  # noqa: E402
from check_content import issued_ids  # noqa: E402

FILE = "identifiers.toml"
FROZEN = date(2026, 10, 10)
HEADER = """\
# The identifiers the guide has issued, by kind (docs/content-model.md, Identifiers). They were set on the date below
# and are kept from then on: an identifier names the same entry for good, and it is never renamed or reused. An
# entry that goes away leaves its identifier under [retired]. scripts/register_ids.py adds new entries' identifiers.
"""


def array(values: list[str]) -> str:
    if not values:
        return "[]"
    return "[\n" + "".join(f"  {json.dumps(value, ensure_ascii=False)},\n" for value in values) + "]"


def render(frozen: date, issued: dict[str, list[str]], retired: dict[str, list[str]]) -> str:
    lines = [HEADER, "[register]", f"frozen = {frozen.isoformat()}", "", "[issued]"]
    lines += [f"{kind} = {array(values)}" for kind, values in issued.items()]
    lines += ["", "[retired]"]
    lines += [f"{kind} = {array(values)}" for kind, values in retired.items() if values]
    return "\n".join(lines) + "\n"


def register(content_dir: Path) -> list[str]:
    """Add the content's unregistered identifiers to the register; return them as kind:identifier."""
    path = content_dir / FILE
    existing = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    frozen = existing.get("register", {}).get("frozen", FROZEN)
    issued = {kind: list(values) for kind, values in existing.get("issued", {}).items()}
    retired = {kind: list(values) for kind, values in existing.get("retired", {}).items()}
    added = []
    for kind, values in issued_ids(load_content(content_dir)).items():
        known = issued.setdefault(kind, [])
        for value in values:
            if value not in known and value not in retired.get(kind, []):
                known.append(value)
                added.append(f"{kind}:{value}")
    path.write_text(render(frozen, issued, retired), encoding="utf-8", newline="\n")
    return added


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--content", type=Path, default=CONTENT, help="content directory (default: content/)")
    args = parser.parse_args(argv)
    added = register(args.content)
    print(f"register_ids: {len(added)} new identifier(s)" + "".join(f"\n  {item}" for item in added))
    return 0


if __name__ == "__main__":
    sys.exit(main())
