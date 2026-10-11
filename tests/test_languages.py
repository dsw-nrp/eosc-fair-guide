"""Language downloads retain exact sources and reconstruct complete bilingual records."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402


def assignment(script: str, prefix: str):
    line = next(line for line in script.splitlines() if line.startswith(prefix))
    return json.loads(line[len(prefix) : -1])


def merge_patch(target, patch):
    """Apply generated patch semantics, keeping objects and array positions unchanged."""
    for key, value in enumerate(patch) if isinstance(patch, list) else patch.items():
        if value is None:
            continue
        if isinstance(target, list):
            while len(target) <= key:
                target.append(None)
        if isinstance(value, (dict, list)):
            existing = target[key] if isinstance(target, list) else target.get(key)
            if not isinstance(existing, (dict, list)):
                target[key] = [] if isinstance(value, list) else {}
            merge_patch(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


class LanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generated = build_crate.outputs()

    def test_originals_and_bilingual_vocabulary_stay_faithful(self) -> None:
        value = {
            "@graph": [
                {
                    "@id": "#source",
                    "inLanguage": "en",
                    "name": build_crate.text({"cs": "Původní dílo", "en": "Original work"}),
                    "description": build_crate.text({"cs": "Překlad popisu", "en": "Translated description"}),
                    "guidance": {"@language": "en", "@value": "An exact original, with its condition."},
                },
                {"@id": "#term-1", "termCode": "1", "name": build_crate.text({"cs": "data", "en": "data"})},
            ]
        }
        common, languages, search = build_crate.split_languages(value)
        source = common["@graph"][0]
        self.assertEqual(source["name"][1]["@value"], "Original work")
        self.assertNotIn("@value", source["name"][0])
        self.assertEqual(source["guidance"], value["@graph"][0]["guidance"])
        self.assertEqual(common["@graph"][1], value["@graph"][1])
        self.assertIn("translated", search[1]["words"]["cs"])
        self.assertIn("preklad", search[1]["words"]["en"])
        for lang in ("en", "cs"):
            merge_patch(common, languages[lang])
        self.assertEqual(common, value)

    def test_language_values_are_absent_until_selected(self) -> None:
        core = assignment(self.generated[build_crate.KB_SCRIPT], "window.FairGuideData.kb = ")
        by_id = {entity["@id"]: entity for entity in core["@graph"]}
        name = by_id["#station-plan"]["name"]
        self.assertTrue(all("@value" not in value for value in name))
        language = assignment(
            self.generated[build_crate.LANGUAGE_SCRIPTS["en"]], 'window.FairGuideData.languages["en"] = '
        )
        merge_patch(core, language["kb"])
        self.assertNotIn("@value", name[0])
        self.assertTrue(name[1]["@value"])
        self.assertEqual(name[1]["@language"], "en")

    def test_language_file_manifest_is_available_before_any_language_load(self) -> None:
        ui = assignment(self.generated[build_crate.UI_SCRIPT], "window.FairGuideData.ui = ")
        self.assertEqual(ui["config"]["languages"], build_crate.LANGUAGE_SCRIPTS)
        self.assertEqual(ui["config"]["partLanguages"], build_crate.PART_LANGUAGE_SCRIPTS)

    def test_generated_languages_and_parts_reconstruct_full_crate(self) -> None:
        for order in (("cs", "en"), ("en", "cs")):
            core = assignment(self.generated[build_crate.KB_SCRIPT], "window.FairGuideData.kb = ")
            ui = assignment(self.generated[build_crate.UI_SCRIPT], "window.FairGuideData.ui = ")
            for lang in order:
                language = assignment(
                    self.generated[build_crate.LANGUAGE_SCRIPTS[lang]],
                    f"window.FairGuideData.languages[{json.dumps(lang)}] = ",
                )
                merge_patch(core, language["kb"])
                merge_patch(ui, language["ui"])
            graph = {entity["@id"]: entity for entity in core["@graph"]}
            for name, path in build_crate.PART_SCRIPTS.items():
                part = assignment(self.generated[path], f"window.FairGuideData.parts[{json.dumps(name)}] = ")
                for lang in order:
                    language = assignment(
                        self.generated[build_crate.PART_LANGUAGE_SCRIPTS[name][lang]],
                        f"window.FairGuideData.partLanguages[{json.dumps(name)}][{json.dumps(lang)}] = ",
                    )
                    merge_patch(part, language["values"])
                graph.update({entity["@id"]: entity for entity in part["entities"]})
                for entity_id, properties in part["properties"].items():
                    graph[entity_id].update(properties)
            crate = json.loads(self.generated[build_crate.CRATE_FILE])
            self.assertEqual(graph, {entity["@id"]: entity for entity in crate["@graph"]})
            self.assertTrue(ui["ui"]["app"]["title"]["cs"])
            self.assertTrue(ui["ui"]["app"]["title"]["en"])

    def test_every_generated_language_script_is_rejected_as_authored_content(self) -> None:
        for path in [
            *build_crate.LANGUAGE_SCRIPTS.values(),
            *(path for values in build_crate.PART_LANGUAGE_SCRIPTS.values() for path in values.values()),
        ]:
            self.assertTrue(build_crate.is_generated(path), path)
            self.assertIn(path, self.generated)

    def test_both_initial_languages_are_counted_and_within_budget(self) -> None:
        for lang in build_crate.LANGS:
            sizes = build_crate.page_payload(self.generated, lang=lang)
            self.assertIn(build_crate.LANGUAGE_SCRIPTS[lang], sizes)
            self.assertNotIn(build_crate.LANGUAGE_SCRIPTS["en" if lang == "cs" else "cs"], sizes)
            self.assertIsNone(build_crate.payload_warning(sizes, build_crate.PAGE_BUDGET_KB))


if __name__ == "__main__":
    unittest.main()
