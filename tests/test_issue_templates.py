"""Issue templates follow the delivered planned-issue shape, one language each, and drift from it fails the check."""

import io
import re
import sys
import tempfile
import tomllib
import unittest
import unittest.mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_issue_templates as templates  # noqa: E402
from plan_issue_shape import body_type, engine  # noqa: E402


def fill(text):
    """A reporter's body from a template: front matter gone, every empty cell and section filled."""
    body = text.split("---\n", 2)[2]
    body = re.sub(r"^(\| [^|]+ \|)  \|$", r"\1 filled |", body, flags=re.MULTILINE)
    return re.sub(r"^(## .+)$", r"\1\n\nWritten by the reporter.", body, flags=re.MULTILINE)


class TemplateTests(unittest.TestCase):
    def test_the_committed_templates_match_the_delivered_shape(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(templates.main(["--check"]), 0)

    def test_each_template_carries_every_declared_section_in_one_language(self):
        shape = engine()
        for kind in templates.NATIVE:
            for language in templates.LANGUAGES:
                text = templates.template(kind, language)
                other = templates.LANGUAGES[1 - templates.LANGUAGES.index(language)]
                headings = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)
                expected = [templates.form(shape.SECTION_FORMS["Problem"], language)]
                expected.append(templates.form(shape.TYPE_BLOCK_FORMS[kind], language))
                expected += [templates.form(shape.SECTION_FORMS[name], language) for name in templates.SECTIONS[2:]]
                self.assertEqual(headings, expected, f"{kind}-{language}")
                self.assertIn(templates.form(shape.TABLE_HEADER_FORMS, language), text)
                foreign = {templates.form(forms, other) for forms in shape.SECTION_FORMS.values()}
                foreign |= {templates.form(forms, other) for forms in shape.METADATA_FORMS.values()}
                self.assertFalse(foreign & set(headings + re.findall(r"^\| (.+?) \|", text, re.MULTILINE)))
                self.assertIn(f"type: {templates.NATIVE[kind]}", text.split("---")[1])
                self.assertEqual(body_type(text), kind, "the Type row carries the machine token")
                for part in (shape.ISSUE_MARKER, shape.INTERACTIVE_DISCLOSURE, shape.REPORTER_CONTEXT_OPEN):
                    self.assertNotIn(part, text, "workflow-owned parts are left to /aiscr-plan-issue")

    def test_the_czech_bug_template_matches_the_specified_scenario(self):
        text = templates.template("bug", "cs")
        for heading in ("Problém", "Reprodukce", "Rozsah", "Akceptační kritéria", "Otevřené otázky"):
            self.assertIn(f"\n## {heading}\n", text)
        self.assertIn("| Pole | Hodnota |", text)
        self.assertIn("| Reprodukovatelnost |  |", text)
        self.assertIn("type: Bug", text)

    def test_a_filled_body_has_every_section_but_the_workflow_owned_reporter_context(self):
        for kind in templates.NATIVE:
            for language in templates.LANGUAGES:
                status = engine().section_status(fill(templates.template(kind, language)))
                self.assertEqual(status["missing"], ["Reporter context"], f"{kind}-{language}")
                self.assertEqual((status["empty"], status["missing_metadata"]), ([], []), f"{kind}-{language}")

    def test_an_unfilled_template_lists_its_missing_metadata(self):
        status = engine().section_status(templates.template("feature", "en"))
        self.assertEqual(status["missing_metadata"], ["Affects", "Reported by"])

    def test_the_native_types_are_the_organizations_declared_types(self):
        config = tomllib.loads((ROOT / ".github" / "repository.toml").read_text(encoding="utf-8"))
        self.assertLessEqual(set(templates.NATIVE.values()), set(config["organization"]["issue_types"]))

    def test_a_planted_heading_change_fails_the_check_with_the_regeneration_command(self):
        shape = engine()
        changed = dict(shape.SECTION_FORMS, Scope=("Scope", "Rozsah práce"))
        with tempfile.TemporaryDirectory() as directory:
            with redirect_stdout(io.StringIO()):
                templates.main(["--directory", directory])
            with unittest.mock.patch.object(shape, "SECTION_FORMS", changed):
                errors = io.StringIO()
                with redirect_stderr(errors):
                    self.assertEqual(templates.main(["--check", "--directory", directory]), 1)
            self.assertIn("bug-cs.md differs", errors.getvalue())
            self.assertNotIn("bug-en.md differs", errors.getvalue(), "only the changed language differs")
            self.assertIn("python scripts/generate_issue_templates.py", errors.getvalue())

    def test_an_unknown_file_or_a_reshaped_declaration_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            with redirect_stdout(io.StringIO()):
                templates.main(["--directory", directory])
            (Path(directory) / "question.md").write_text("---\nname: Question\n---\n", encoding="utf-8")
            with redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(templates.main(["--check", "--directory", directory]), 1)
            self.assertIn("question.md is not a generated template", errors.getvalue())
        shape = engine()
        with unittest.mock.patch.object(shape, "SECTION_FORMS", dict(shape.SECTION_FORMS, Scope=("Scope",))):
            with redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(templates.main(["--check"]), 1)
            self.assertIn("one form per language", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
