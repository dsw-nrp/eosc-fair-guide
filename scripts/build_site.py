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
import html
import os
import posixpath
import shutil
import sys
from pathlib import Path
from typing import Any

import build_api
import build_crate as kb
import check_health

SITE = kb.ROOT / "_site"
# Authored files the page loads as they are.
STATIC = ("assets/css", "assets/js", "assets/img")
LOCAL_TEST_DOC = "assets/js/tests/index.html"


def render_test_docs(template: str, content: dict[str, Any]) -> str:
    """Fill the two empty documentation blocks from the local-test registry; prose is authored only in TOML."""
    labels = {
        "cs": {"code": "Kód testu", "function": "Volaná funkce", "question": "Otázka", "record": "Test v katalogu"},
        "en": {
            "code": "Test code",
            "function": "Invoked function",
            "question": "Question",
            "record": "Test in catalogue",
        },
    }
    blocks = {}
    questions = {item["id"]: item for check in content["checks"] for item in check.get("item", [])}
    principle_labels = {entry["id"]: entry["label"] for entry in content["principles"]}
    for language in kb.LANGS:
        sections = []
        for test in content["live"].get("test", []):
            identifier = test["id"]
            anchor = identifier + ("-en" if language == "en" else "")
            source = posixpath.relpath(test["script"], posixpath.dirname(LOCAL_TEST_DOC))
            strings = labels[language]
            links = [
                (source, strings["code"]),
                (
                    f"../../../index.html#/{language}/K/catalogue/questions/{test['question']}",
                    strings["question"] + ": " + test["question"],
                ),
                (f"../../../index.html#/{language}/K/catalogue/tests/{identifier}", strings["record"]),
                (f"../../../api/tests/{identifier}.json", "JSON"),
            ]
            linked = " · ".join(
                f'<a href="{html.escape(target, quote=True)}">{html.escape(label)}</a>' for target, label in links
            )
            principle_links = " · ".join(
                f'<a href="../../../index.html#/{language}/K/catalogue/k!tests~p!{code}">'
                f"{code} · {html.escape(principle_labels[code][language])}</a>"
                for code in questions[test["question"]].get("principles", [])
            )
            sections.append(
                f'<section aria-labelledby="{html.escape(anchor, quote=True)}">\n'
                f'  <h3 id="{html.escape(anchor, quote=True)}"><code>{html.escape(identifier)}</code>'
                f" · {html.escape(test['label'][language])}</h3>\n"
                f"  <p>{html.escape(test['description'][language])}</p>\n"
                f'  <p class="test-principles">FAIR: {principle_links}</p>\n'
                f"  <p>{linked}</p>\n"
                f"  <p>{strings['function']}: <code>{html.escape(test['entryPoint'])}(observations)</code></p>\n"
                "</section>"
            )
        blocks["tests" + language] = "\n" + "\n".join(sections) + "\n"
    matches = list(kb.BLOCK.finditer(template))
    if {match.group("name") for match in matches} != set(blocks) or len(matches) != len(blocks):
        raise kb.ContentError(f"{LOCAL_TEST_DOC}: the two local-test documentation blocks are required")
    if any(match.group("body").strip() for match in matches):
        raise kb.ContentError(f"{LOCAL_TEST_DOC}: authored documentation blocks must stay empty")
    return kb.BLOCK.sub(lambda match: match.group(1) + blocks[match.group("name")] + match.group(4), template)


def build(out: Path = SITE, root: Path = kb.ROOT) -> dict[str, str]:
    """Replace the site directory with a fresh build; return the generated texts by path."""
    out = out.resolve()
    if out == root.resolve() or (out / ".git").exists() or not out.is_relative_to(root.resolve()):
        raise kb.ContentError(f"the site directory must be a directory of its own inside the repository, not {out}")
    generated = kb.outputs(root)
    content = kb.load_content(root / "content")
    documentation = root / LOCAL_TEST_DOC
    if documentation.is_file():
        generated[LOCAL_TEST_DOC] = render_test_docs(documentation.read_text(encoding="utf-8"), content)
    if out.exists():
        shutil.rmtree(out)
    for name in STATIC:
        shutil.copytree(root / name, out / name)
    for name, text in generated.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    api = build_api.Api(kb.build_crate(content), content)
    build_api.write_site(out, api.files())
    check_health.write_site_dashboard(api.health(), out)
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
    language_sizes = {lang: kb.page_payload(generated, lang=lang) for lang in kb.LANGS}
    largest_language = max(language_sizes, key=lambda lang: sum(language_sizes[lang].values()))
    sizes = language_sizes[largest_language]
    if args.sizes:
        print(f"Largest initial download ({largest_language}):")
        for name, size in sorted(sizes.items(), key=lambda item: -item[1]):
            print(f"{size / 1024:8.1f} KB  {name}")
        print(f"{sum(sizes.values()) / 1024:8.1f} KB  total compressed (budget {kb.PAGE_BUDGET_KB} KB)")
        for lang, measured in language_sizes.items():
            print(f"{sum(measured.values()) / 1024:8.1f} KB  initial download in {lang}")
    warning = kb.payload_warning(sizes, kb.PAGE_BUDGET_KB)
    if warning:
        print(f"warning: {warning}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::warning title=Page size::{warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
