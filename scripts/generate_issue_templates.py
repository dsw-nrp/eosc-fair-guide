"""Write the Czech and English Bug, Feature and Task issue templates from the delivered planned-issue shape.

    python scripts/generate_issue_templates.py          # write .github/ISSUE_TEMPLATE/
    python scripts/generate_issue_templates.py --check  # fail when a template differs from the declarations

Headings, metadata labels and the `Type` token come from the delivered `aiscr-plan-issue` declarations, so each
template carries the metadata table, `Problem`, its type block, `Scope`, `Acceptance criteria` and `Open questions` in
one language and sets the native issue type. The workflow-owned parts (marker, reporter context and disclosure) are
left out: `/aiscr-plan-issue` adds them when a maintainer shapes the issue before it becomes Ready.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from plan_issue_shape import ROOT, engine

DIRECTORY = ROOT / ".github" / "ISSUE_TEMPLATE"
REPOSITORY = "https://github.com/dsw-nrp/eosc-fair-guide"
LANGUAGES = ("en", "cs")  # the order of every delivered form tuple: the English form first, then the Czech one
NATIVE = {"bug": "Bug", "feature": "Feature", "task": "Task"}
SECTIONS = ("Problem", None, "Scope", "Acceptance criteria", "Open questions")  # None: the type block
METADATA = ("Type", "Affects", "Reported by", "Reproducibility")

TEXT = {
    "en": {
        "name": {"bug": "Bug (English)", "feature": "Feature (English)", "task": "Task (English)"},
        "about": {
            "bug": "Something in the Guide does not work as it should.",
            "feature": "Propose a new possibility or a change to the Guide.",
            "task": "Work that needs doing, such as maintenance or an update.",
        },
        "intro": (
            "Fill in the table and every section. Leave no section empty: if there is nothing to record, write "
            "“None.” The Type value stays `bug`, `feature` or `task`. Affects: the station, page, check or tool. "
            "Reported by: your name or account. Before an issue becomes Ready, maintainers shape it into the planned "
            "form with /aiscr-plan-issue."
        ),
        "reproducibility": "Reproducibility: always, sometimes or once.",
        "guide": {
            "Problem": "What you observed and why it matters.",
            "bug": "Numbered steps, the expected and the actual result, browser or version, and the exact error.",
            "feature": "Who is affected, what they do today, the alternatives considered and the cost of not acting.",
            "task": "What changes, why now, and the constraints and order of the work.",
            "Scope": "What belongs to the change, what explicitly does not, and the parts of the Guide affected.",
            "Acceptance criteria": "Checkable statements as task items: - [ ] …",
            "Open questions": "What must be decided, including your guesses at the cause. If nothing, write “None.”",
        },
    },
    "cs": {
        "name": {"bug": "Chyba (česky)", "feature": "Návrh (česky)", "task": "Úkol (česky)"},
        "about": {
            "bug": "Něco v Průvodci nefunguje, jak má.",
            "feature": "Navrhněte novou možnost nebo změnu Průvodce.",
            "task": "Práce, kterou je potřeba udělat, například údržba nebo aktualizace.",
        },
        "intro": (
            "Vyplňte tabulku a každou sekci. Žádnou sekci nenechávejte prázdnou: když není co uvést, napište "
            "„Žádné.“ Hodnota Typ zůstává `bug`, `feature` nebo `task`. Dotčená oblast: stanoviště, stránka, kontrola "
            "nebo nástroj. Nahlásil: vaše jméno nebo účet. Než správci zařadí podnět do stavu Ready, převedou jeho "
            "popis do plánované podoby pomocí /aiscr-plan-issue."
        ),
        "reproducibility": "Reprodukovatelnost: vždy, někdy nebo jednou.",
        "guide": {
            "Problem": "Co jste pozorovali a proč to vadí.",
            "bug": "Očíslované kroky, očekávaný a skutečný výsledek, prohlížeč nebo verze a přesný text chyby.",
            "feature": "Koho se to týká, co dělá dnes, zvažované alternativy a co stojí nic nedělat.",
            "task": "Co se změní, proč teď, omezení a pořadí kroků.",
            "Scope": "Co do změny patří, co výslovně ne a kterých částí Průvodce se týká.",
            "Acceptance criteria": "Ověřitelné výroky jako úkoly: - [ ] …",
            "Open questions": "Co je potřeba rozhodnout, včetně vašich domněnek o příčině. Když nic, napište „Žádné.“",
        },
    },
}


class ShapeError(ValueError):
    """The delivered declarations no longer have the shape this generator renders."""


def form(forms: tuple[str, ...], language: str) -> str:
    if len(forms) != len(LANGUAGES):
        raise ShapeError(f"the delivered shape declares {forms!r}; expected one form per language {LANGUAGES}")
    return forms[LANGUAGES.index(language)]


def template(kind: str, language: str) -> str:
    shape, text = engine(), TEXT[language]
    if tuple(shape.TYPE_BLOCK_FORMS) != tuple(NATIVE) or set(METADATA) != set(shape.METADATA_FORMS):
        raise ShapeError("the delivered issue types or metadata fields changed; review this generator")
    intro = text["intro"] + (" " + text["reproducibility"] if kind == "bug" else "")
    lines = ["---", f"name: {text['name'][kind]}", f"about: {text['about'][kind]}", f"type: {NATIVE[kind]}", "---", ""]
    lines += [f"<!-- {intro} -->", "", form(shape.TABLE_HEADER_FORMS, language), "| --- | --- |"]
    for field in METADATA:
        if field == shape.BUG_METADATA and kind != "bug":
            continue
        # Only the Type token is prefilled; an empty cell stays a missing row until the reporter fills it.
        lines.append(f"| {form(shape.METADATA_FORMS[field], language)} | {kind if field == 'Type' else ''} |")
    for section in SECTIONS:
        forms = shape.TYPE_BLOCK_FORMS[kind] if section is None else shape.SECTION_FORMS[section]
        lines += ["", f"## {form(forms, language)}", "", f"<!-- {text['guide'][section or kind]} -->"]
    return "\n".join(lines) + "\n"


def config() -> str:
    return "\n".join(
        [
            "blank_issues_enabled: true",
            "contact_links:",
            "  - name: Diskuse / Discussions",
            f"    url: {REPOSITORY}/discussions",
            "    about: Otázky a nápady, které ještě nejsou úkolem. Questions and ideas that are not yet a task.",
            "  - name: Jak přispět / Contributing",
            f"    url: {REPOSITORY}/blob/main/CONTRIBUTING.md",
            "    about: Jak se návrhy posuzují a přijímají. How proposals are reviewed and accepted.",
            "",
        ]
    )


def expected() -> dict[str, str]:
    files = {f"{kind}-{language}.md": template(kind, language) for kind in NATIVE for language in LANGUAGES}
    return files | {"config.yml": config()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare without writing; exit 1 on any difference")
    parser.add_argument("--directory", type=Path, default=DIRECTORY, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        files = expected()
    except ShapeError as error:
        print(f"generate_issue_templates: {error}", file=sys.stderr)
        return 1
    if args.check:
        present = {path.name for path in args.directory.iterdir()} if args.directory.is_dir() else set()
        stale = sorted(
            name
            for name, text in files.items()
            if not (args.directory / name).is_file() or (args.directory / name).read_text(encoding="utf-8") != text
        )
        for name in stale:
            print(f"generate_issue_templates: {name} differs from the delivered issue shape", file=sys.stderr)
        for name in sorted(present - set(files)):
            print(f"generate_issue_templates: {name} is not a generated template", file=sys.stderr)
        if stale or present - set(files):
            print("Regenerate with: python scripts/generate_issue_templates.py", file=sys.stderr)
            return 1
        print(f"generate_issue_templates: {len(files)} files match the delivered issue shape")
        return 0
    args.directory.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (args.directory / name).write_text(text, encoding="utf-8", newline="\n")
    print(f"generate_issue_templates: wrote {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
