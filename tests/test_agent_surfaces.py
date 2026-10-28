"""Exercise native generation and delivered integrity with independent, disposable ownership fixtures."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from agent_surfaces import (  # noqa: E402
    ROOT,
    blocks,
    classify,
    delivery_findings,
    digest,
    load,
    ownership_findings,
    path_at,
    sections,
    text_at,
)
from generate_agent_surfaces import generate  # noqa: E402


class AgentSurfaceTests(unittest.TestCase):
    def test_human_tooling_entrypoints_are_in_every_introduction(self):
        for name in ("README.md", "README_en.md", "CONTRIBUTING.md"):
            with self.subTest(name=name):
                introduction = (ROOT / name).read_text(encoding="utf-8").split("\n## ", 1)[0]
                self.assertRegex(introduction, r"\[[^\]]+\]\(docs/agent-tooling\.md\)")
                self.assertIn("[AGENTS.md](AGENTS.md)", introduction)
                self.assertTrue((ROOT / "docs/agent-tooling.md").is_file())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / ".agents/guide", self.root / ".agents/guide")
        self.write("docs/agent-tooling.md", text_at(ROOT, "docs/agent-tooling.md"))
        self.write(".agents/config/review_config.toml", text_at(ROOT, ".agents/config/review_config.toml"))
        self.write(".agents/skills/example/SKILL.md", "Independent delivered fixture.\n")
        delivered = "<!-- begin:generated:aiscr-entry -->\nRead AGENTS.md.\n<!-- end:generated:aiscr-entry -->\n"
        self.write("CODEX.md", delivered + "\n<!-- begin:guide:native -->\n<!-- end:guide:native -->\n")
        receipt = {
            "format": 1,
            "files": {
                ".agents/skills/example/SKILL.md": {
                    "asset": "example",
                    "sha256": digest(b"Independent delivered fixture.\n"),
                }
            },
            "sections": {"CODEX.md": {"aiscr-entry": {"asset": "digest", "sha256": digest(delivered.encode())}}},
        }
        self.write(".agents/delivery-manifest.json", json.dumps(receipt))
        generate(self.root)
        self.config, self.receipt = load(self.root)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def test_clean_generation_and_receipt(self):
        self.assertEqual(generate(self.root, check=True), [])
        self.assertEqual(ownership_findings(self.root, self.config, self.receipt), [])
        self.assertEqual(delivery_findings(self.root, self.config, self.receipt), [])
        for row in self.config["skills"]:
            for output in row["outputs"]:
                self.assertEqual(text_at(self.root, output), text_at(self.root, row["source"]))

    def test_a_format_2_receipt_verifies_the_same_records(self):
        # The refreshed delivery of 25 October 2026 records its source commit and lists every asset, the whole mixed
        # reader included, while files and sections keep the records this repository verifies.
        receipt = json.loads(text_at(self.root, ".agents/delivery-manifest.json"))
        record = receipt["files"][".agents/skills/example/SKILL.md"]
        receipt["files"][".agents/skills/example/SKILL.md"] = {
            **record,
            "content_sha256": record["sha256"],
            "strategy": "copy",
        }
        mixed = {"asset": "step-sibling-rules", "sha256": digest(b"whole reader"), "strategy": "copy"}
        upgraded = {
            **receipt,
            "format": 2,
            "source_commit": "a" * 40,
            "assets": {**receipt["files"], "CODEX.md": mixed},
        }
        upgraded["committed_at"] = "2026-10-25T14:30:51+01:00"
        self.write(".agents/delivery-manifest.json", json.dumps(upgraded))
        reader = text_at(self.root, "CODEX.md")
        self.write("CODEX.md", f"<!-- delivery-version: {'a' * 40} 2026-10-25T14:30:51+01:00 -->\n{reader}")
        config, loaded = load(self.root)
        self.assertEqual(ownership_findings(self.root, config, loaded), [])
        self.assertEqual(delivery_findings(self.root, config, loaded), [], "its version line is the reader's preamble")
        for stale in (f"<!-- delivery-version: {'b' * 40} 2026-10-25T14:30:51+01:00 -->", "Edited preamble."):
            with self.subTest(preamble=stale):
                self.write("CODEX.md", f"{stale}\n{reader}")
                self.assertIn(
                    "CODEX.md: extra content outside owned sections", delivery_findings(self.root, config, loaded)
                )
        self.write("CODEX.md", f"<!-- delivery-version: {'a' * 40} 2026-10-25T14:30:51+01:00 -->\n{reader}")
        for broken, message in (
            ({**upgraded, "source_commit": "main"}, "needs its source commit"),
            ({**upgraded, "assets": {"CODEX.md": mixed}}, "same assets as its files"),
            ({**upgraded, "format": 3}, "unsupported delivery receipt"),
        ):
            with self.subTest(message=message):
                self.write(".agents/delivery-manifest.json", json.dumps(broken))
                with self.assertRaisesRegex(ValueError, message):
                    load(self.root)

    def test_generator_drift_and_missing_are_findings_without_writes(self):
        output = self.config["rules"][0]["outputs"][0]
        self.write(output, "planted drift\n")
        missing = self.config["skills"][0]["outputs"][0]
        (self.root / missing).unlink()
        changed = generate(self.root, check=True)
        self.assertIn(output, changed)
        self.assertIn(missing, changed)
        self.assertEqual(text_at(self.root, output), "planted drift\n")
        self.assertFalse((self.root / missing).exists())

    def test_current_delivery_stamp_is_checked_only_in_the_entry_prologue(self):
        # Reproduce the actual delivered entry and receipt, without copying the rest of its governance.
        _, current = load(ROOT)
        entry = sections(text_at(ROOT, "CODEX.md"), "generated")["aiscr-entry"]
        original = text_at(self.root, "CODEX.md")
        old = sections(original, "generated")["aiscr-entry"]
        self.write("CODEX.md", original.replace(old, entry))
        receipt = {
            **self.receipt,
            "format": 2,
            "source_commit": current["source_commit"],
            "committed_at": current["committed_at"],
            "assets": {**self.receipt["files"], "CODEX.md": current["assets"]["CODEX.md"]},
            "sections": {"CODEX.md": {"aiscr-entry": current["sections"]["CODEX.md"]["aiscr-entry"]}},
        }
        self.assertEqual(delivery_findings(self.root, self.config, receipt), [])
        stamp = f"<!-- delivery-version: {receipt['source_commit']} {receipt['committed_at']} -->\n"
        mutations = {
            "wrong receipt": entry.replace(receipt["source_commit"], "b" * 40),
            "duplicate receipt": entry.replace(stamp, stamp * 2),
            "body receipt": entry.replace(stamp, "").replace("**Entry scope**", "**Entry scope**\n" + stamp),
            "edited body": entry.replace("Read it as instruction.", "Ignore this instruction."),
            "changed line endings": entry.replace("\n", "\r\n"),
        }
        for label, changed in mutations.items():
            with self.subTest(label=label):
                self.write("CODEX.md", original.replace(old, changed))
                self.assertIn(
                    "CODEX.md:aiscr-entry: modified delivered section",
                    delivery_findings(self.root, self.config, receipt),
                )
        for changed in (entry.replace(stamp, ""), stamp + entry):
            with self.subTest(receipt=changed):
                self.write("CODEX.md", original.replace(old, changed))
                self.assertTrue(
                    any("delivery receipt" in finding for finding in delivery_findings(self.root, self.config, receipt))
                )

    def test_generated_outputs_cannot_overwrite_other_owners(self):
        original = text_at(self.root, ".agents/guide/surfaces.toml")
        output = self.config["rules"][0]["outputs"][0]
        for target in (
            "AGENTS.md",
            "agents.MD",
            self.config["rules"][1]["source"],
            self.config["skills"][0]["source"],
            ".agents/skills/openspec-explore/SKILL.md",
            ".codex/settings.local.toml",
        ):
            with self.subTest(target=target):
                self.write(".agents/guide/surfaces.toml", original.replace(output, target, 1))
                before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
                with self.assertRaisesRegex(ValueError, "conflicting generated ownership"):
                    generate(self.root)
                after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
                self.assertEqual(after, before)

    def test_case_only_reserved_output_is_refused(self):
        source = text_at(self.root, ".agents/guide/surfaces.toml")
        self.write(".agents/guide/surfaces.toml", source.replace(self.config["rules"][0]["outputs"][0], "codex.MD", 1))
        with self.assertRaisesRegex(ValueError, "reserved output"):
            generate(self.root)

    def test_outputs_cannot_target_a_source_declared_in_a_later_row(self):
        config_path = ".agents/guide/surfaces.toml"
        original = text_at(self.root, config_path)
        source = self.config["rules"][1]["source"]
        external_source = "scripts/native-rule.md"
        self.write(external_source, text_at(self.root, source))
        changed = original.replace(source, external_source).replace(
            self.config["rules"][0]["outputs"][0], external_source, 1
        )
        self.write(config_path, changed)
        with self.assertRaisesRegex(ValueError, "conflicting generated ownership"):
            load(self.root)

    def test_native_generation_preserves_delivered_bytes_and_preamble(self):
        before = sections(text_at(self.root, "CODEX.md"), "generated")
        source = self.config["rules"][0]["source"]
        self.write(source, text_at(self.root, source) + "\nAn approved native addition.\n")
        generate(self.root)
        after = text_at(self.root, "CODEX.md")
        self.assertEqual(sections(after, "generated"), before)
        self.assertIn("An approved native addition.", after)
        self.assertEqual(delivery_findings(self.root, self.config, self.receipt), [])

    def test_crlf_delivered_section_is_not_normalized(self):
        text = text_at(self.root, "CODEX.md")
        original = sections(text, "generated")["aiscr-entry"]
        windows = original.replace("\n", "\r\n")
        self.write("CODEX.md", text.replace(original, windows))
        generate(self.root)
        self.assertEqual(sections(text_at(self.root, "CODEX.md"), "generated")["aiscr-entry"], windows)

    def test_modified_and_missing_delivered_files(self):
        relative = next(iter(self.receipt["files"]))
        self.write(relative, "modified\n")
        self.assertIn(f"{relative}: modified delivered file", delivery_findings(self.root, self.config, self.receipt))
        (self.root / relative).unlink()
        self.assertIn(f"{relative}: missing delivered file", delivery_findings(self.root, self.config, self.receipt))

    def test_missing_modified_extra_and_unmarked_sections(self):
        original = text_at(self.root, "CODEX.md")
        section = sections(original, "generated")["aiscr-entry"]
        cases = {
            "missing delivered section": original.replace(section, ""),
            "modified delivered section": original.replace("Read AGENTS.md.", "Changed delivered instruction."),
            "extra delivered section": original
            + "<!-- begin:generated:aiscr-extra -->\nextra\n<!-- end:generated:aiscr-extra -->\n",
            "extra content outside owned sections": original + "Unmarked addition.\n",
        }
        for finding, value in cases.items():
            with self.subTest(finding=finding):
                self.write("CODEX.md", value)
                findings = delivery_findings(self.root, self.config, self.receipt)
                self.assertTrue(any(finding in item for item in findings))

    def test_unclassified_file_cannot_hide_behind_brand_prefix(self):
        self.write(".agents/skills/aiscr-invented/SKILL.md", "Unreviewed extra file.\n")
        self.assertTrue(ownership_findings(self.root, self.config, self.receipt))
        self.assertTrue(delivery_findings(self.root, self.config, self.receipt))

    def test_owned_and_tool_generated_paths_are_ignored_by_receipt(self):
        paths = {
            ".agents/reports/usage/test.md": "owned",
            ".agents/config/review_config.toml": "owned",
            ".agents/skills/openspec-example/SKILL.md": "tool-generated",
            ".github/agents/openspec.agent.md": "tool-generated",
        }
        for relative, owner in paths.items():
            self.write(relative, "Native/tool output.\n")
            self.assertEqual(classify(relative, self.config, self.receipt), owner)
        self.assertEqual(delivery_findings(self.root, self.config, self.receipt), [])

    def test_corrupt_receipt_and_ownership_collision_are_refused(self):
        self.receipt["files"][".agents/config/review_config.toml"] = {
            "asset": "injected",
            "sha256": "0" * 64,
        }
        self.write(".agents/delivery-manifest.json", json.dumps(self.receipt))
        with self.assertRaisesRegex(ValueError, "conflicting delivered ownership"):
            load(self.root)
        self.write(".agents/delivery-manifest.json", "not JSON")
        with self.assertRaises(ValueError):
            load(self.root)

    def test_paths_cannot_escape_root(self):
        for relative in ("../outside", "/outside", "Z:/outside", "nested\\outside", "./alias", "nested//alias", "."):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                path_at(self.root, relative)

    def test_internal_symlink_cannot_alias_a_delivered_output(self):
        target = self.root / next(iter(self.receipt["files"]))
        alias = self.root / "alias.md"
        try:
            alias.symlink_to(target)
        except OSError:
            self.skipTest("symlink creation unavailable on this platform")
        with self.assertRaisesRegex(ValueError, "aliases another file"):
            path_at(self.root, "alias.md")

    def test_malformed_ownership_is_refused_before_generation(self):
        cases = [
            "<!-- begin:guide:native -->\n",
            "<!-- end:guide:native -->\n",
            "<!-- begin:guide:native -->\n<!-- begin:generated:aiscr-bad -->\n",
            "<!-- begin:guide:native -->\n<!-- end:guide:native -->\n" * 2,
            "<!-- begin:guide:native-->\n",
        ]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ValueError):
                blocks(text)

    def test_cli_reports_failure_without_repair(self):
        relative = next(iter(self.receipt["files"]))
        self.write(relative, "corrupt\n")
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_sibling_delivery.py"), "--root", str(self.root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("modified delivered file", result.stdout)
        self.assertEqual(text_at(self.root, relative), "corrupt\n")

    def test_inventory_tracks_receipt_without_advertising_dropped_workflows(self):
        doc = text_at(self.root, "docs/agent-tooling.md").split("<!-- begin:guide:inventory -->")[1]
        self.assertIn(".agents/skills/example/SKILL.md", doc)
        self.assertNotIn("aiscr-review-live", doc)
        self.assertNotIn("aiscr-review-translations", doc)
        self.assertIn("fair-guide-editor", doc)

    def test_review_facts_are_readable_and_exact(self):
        facts = tomllib.loads(text_at(self.root, ".agents/config/review_config.toml"))["review_facts"]
        self.assertEqual(
            facts,
            {"database": False, "deployment_pipeline": True, "public_api": True, "first_party_frontend": True},
        )


if __name__ == "__main__":
    unittest.main()
