#!/usr/bin/env python3
"""Build the FAIR guide's site from its sources with one command.

    python scripts/build_site.py [--out DIR] [--sizes]

Writes into the site directory (``_site/`` by default, never committed): the page with its generated blocks and its
copy as the crate's preview, the page's data scripts, the crate, the linkset, the profile at the guide's address, the
page's styles, scripts and images, and the API with its documentation (``build_api.py``). The directory is replaced
as a whole, so nothing stale stays in it. Every build warns when what the page downloads, compressed, exceeds the
page budget; ``--sizes`` prints what it downloads.

Then open ``_site/index.html``, or serve the site with ``python scripts/serve.py`` to use the API locally. Uses only
the Python standard library; the API documentation needs the Swagger UI package (``npm ci``).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

import build_api
import build_crate as kb

SITE = kb.ROOT / "_site"
# Authored files the page loads as they are.
STATIC = ("assets/css", "assets/js", "assets/img")


def build(out: Path = SITE, root: Path = kb.ROOT) -> dict[str, str]:
    """Replace the site directory with a fresh build; return the generated texts by path."""
    out = out.resolve()
    if out == root.resolve() or (out / ".git").exists() or not out.is_relative_to(root.resolve()):
        raise kb.ContentError(f"the site directory must be a directory of its own inside the repository, not {out}")
    generated = kb.outputs(root)
    if out.exists():
        shutil.rmtree(out)
    for name in STATIC:
        shutil.copytree(root / name, out / name)
    for name, text in generated.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    content = kb.load_content(root / "content")
    build_api.write_site(out, build_api.Api(kb.build_crate(content), content).files())
    return generated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=SITE, help="the site directory (default: _site)")
    parser.add_argument("--sizes", action="store_true", help="print what the page downloads, compressed")
    args = parser.parse_args(argv)
    if not (build_api.SWAGGER_DIR / build_api.SWAGGER_FILES[0]).exists():
        print("build_site: the Swagger UI package is missing; run npm ci", file=sys.stderr)
        return 2
    try:
        generated = build(args.out)
    except (kb.ContentError, KeyError) as error:
        print(f"build_site: {error}", file=sys.stderr)
        return 2
    print(f"build_site: built the site into {args.out.name}/")
    sizes = kb.page_payload(generated)
    if args.sizes:
        for name, size in sorted(sizes.items(), key=lambda item: -item[1]):
            print(f"{size / 1024:8.1f} KB  {name}")
        print(f"{sum(sizes.values()) / 1024:8.1f} KB  total compressed (budget {kb.PAGE_BUDGET_KB} KB)")
    warning = kb.payload_warning(sizes, kb.PAGE_BUDGET_KB)
    if warning:
        print(f"warning: {warning}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::warning title=Page size::{warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
