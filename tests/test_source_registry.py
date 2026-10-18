"""The refresh-source registry is authored once and read by Python, Node, the workflow and the maintained prose."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import refresh_snapshots  # noqa: E402


class SourceRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = refresh_snapshots.load_source_registry()

    def workflow_options(self) -> list[str]:
        workflow = yaml.load(
            (ROOT / ".github/workflows/source-refresh.yml").read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )
        return workflow["on"]["workflow_dispatch"]["inputs"]["source"]["options"]

    def assert_source_options(self, registry: dict[str, dict[str, object]], options: list[str]) -> None:
        self.assertEqual(options[0], "all")
        self.assertEqual(options[1:], list(registry))

    def assert_prose_names(self, registry: dict[str, dict[str, object]], texts: dict[str, str]) -> None:
        for label in (entry["label"] for entry in registry.values()):
            for name, text in texts.items():
                self.assertIn(label, text, f"{name} does not name {label}")

    def test_registry_owns_every_key_file_and_label(self) -> None:
        self.assertEqual(set(self.registry), set(refresh_snapshots.SOURCES))
        for key, entry in self.registry.items():
            self.assertTrue(entry["label"], key)
            self.assertTrue(entry["files"], key)
            self.assertTrue(all(isinstance(path, str) and path for path in entry["files"]), key)

    def test_workflow_choice_options_match_the_registry(self) -> None:
        options = self.workflow_options()
        self.assert_source_options(self.registry, options)
        with self.assertRaises(AssertionError):
            self.assert_source_options(self.registry, options[:-1])

    def test_maintained_prose_names_every_source(self) -> None:
        texts = {
            "AGENTS.md": (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "README_en.md": (ROOT / "README_en.md").read_text(encoding="utf-8"),
        }
        self.assert_prose_names(self.registry, texts)
        with self.assertRaises(AssertionError):
            self.assert_prose_names(self.registry, {"planted.md": "Heslář and re3data"})

    def test_node_publisher_reads_the_same_registry(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node is needed to load the trusted publisher")
        result = subprocess.run(
            [
                node,
                "-e",
                "const {SOURCES} = require('./.github/scripts/source-publisher.cjs');"
                "process.stdout.write(JSON.stringify(SOURCES));",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        )
        published = json.loads(result.stdout)
        self.assertEqual(set(published), set(self.registry))
        self.assertEqual(
            {key: published[key] for key in published},
            {key: list(entry["files"]) for key, entry in self.registry.items()},
        )

    def test_registry_refuses_a_planted_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".github").mkdir()
            data = json.loads((ROOT / ".github/source-registry.json").read_text(encoding="utf-8"))
            data["sources"].append({"key": "planted", "label": "Planted", "files": ["content/planted.toml"]})
            (root / ".github/source-registry.json").write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "keys do not match"):
                refresh_snapshots.load_source_registry(root)


if __name__ == "__main__":
    unittest.main()
