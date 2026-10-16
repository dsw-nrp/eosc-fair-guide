"""Release metadata, real tag ancestry, provenance and refusal-before-write contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate  # noqa: E402
import release_versions as release  # noqa: E402


class ReleaseVersions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in (*release.FILES, "CHANGELOG.md", "content/provenance.toml", "content/identifiers.toml"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        # Release PRs change the repository's own version/date and add actions.
        # Keep this fixture independent of whichever release is being checked.
        for name, section in ((release.FILES[0], "guide"), (release.FILES[4], "project")):
            path = self.root / name
            text = release.scalar(path.read_text(encoding="utf-8"), "version", '"1.0.0-alpha.1"', section=section)
            if section == "guide":
                text = release.scalar(text, "datePublished", "2026-10-08", section=section)
            path.write_text(text, encoding="utf-8")
        path = self.root / "CITATION.cff"
        text = release.scalar(path.read_text(encoding="utf-8"), "version", '"1.0.0-alpha.1"')
        path.write_text(release.scalar(text, "date-released", '"2026-10-08"'), encoding="utf-8")
        for name in ("package.json", "package-lock.json"):
            path = self.root / name
            data = json.loads(path.read_text(encoding="utf-8"))
            data["version"] = "1.0.0-alpha.1"
            if name == "package-lock.json":
                data["packages"][""]["version"] = data["version"]
            path.write_text(json.dumps(data), encoding="utf-8")
        (self.root / "content/provenance.toml").write_text("", encoding="utf-8")
        (self.root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [Unreleased]\n\nDraft notes.\n\n## [0.9.0]\n\nHistorical release text.\n",
            encoding="utf-8",
        )
        registry = tomllib.loads((self.root / "content/identifiers.toml").read_text(encoding="utf-8"))
        (self.root / "content/identifiers.toml").write_text(
            release.render(registry["register"]["prepared"], {"actions": []}, {}), encoding="utf-8"
        )
        self.prs = [
            self.pr(3, "a", "One [complete] change"),
            self.pr(2, "b", "Second change"),
            self.pr(1, "old", "Before the tag"),
            {**self.pr(4, "a", "Closed only"), "merged_at": None},
        ]

    @staticmethod
    def pr(number: int, sha: str, title: str) -> dict:
        return {
            "number": number,
            "merge_commit_sha": sha,
            "title": title,
            "merged_at": f"2026-10-{number:02}T10:00:00Z",
            "html_url": f"https://github.com/dsw-nrp/eosc-fair-guide/pull/{number}",
        }

    def snapshot(self) -> dict:
        return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}

    def test_semver_refuses_injection_ambiguous_numbers_and_build_suffix(self) -> None:
        for value in ("1.2.3", "1.2.3-alpha.1", "1.2.3-rc-1", "0.0.0"):
            self.assertEqual(release.version(value), value)
        for value in ("v1.2.3", "01.2.3", "1.2.3-alpha.01", "1.2.3-a..b", "1.2.3+build", "1.2.3\n", "$(id)"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.version(value)

    def test_each_authored_version_and_date_is_checked(self) -> None:
        self.assertEqual(release.check(self.root), [])
        for name in release.FILES[1:]:
            path = self.root / name
            original = path.read_text(encoding="utf-8")
            path.write_text(original.replace("1.0.0-alpha.1", "2.0.0"), encoding="utf-8")
            self.assertTrue(any(name in error for error in release.check(self.root)), name)
            path.write_text(original, encoding="utf-8")
        path = self.root / "CITATION.cff"
        path.write_text(
            path.read_text(encoding="utf-8").replace('date-released: "2026-10-08"', 'date-released: "2026-10-09"'),
            encoding="utf-8",
        )
        self.assertIn("date-released", "\n".join(release.check(self.root)))

    def test_crate_date_and_every_guide_version_are_checked(self) -> None:
        site = self.root / "site"
        site.mkdir()
        expected, released, _ = release.metadata(self.root)
        nodes = [{"@id": name, "version": expected} for name in ("./", "#guide-source", "#guide-software")]
        nodes[0]["datePublished"] = released
        path = site / "ro-crate-metadata.json"
        path.write_text(json.dumps({"@graph": nodes}))
        self.assertEqual(release.check(self.root, site), [])
        for node in nodes:
            original = node["version"]
            node["version"] = "0.0.0"
            path.write_text(json.dumps({"@graph": nodes}))
            self.assertIn(node["@id"], "\n".join(release.check(self.root, site)))
            node["version"] = original
        nodes[0]["datePublished"] = "2000-01-01"
        path.write_text(json.dumps({"@graph": nodes}))
        self.assertIn("datePublished", "\n".join(release.check(self.root, site)))

    def test_prose_version_refused_but_source_versions_and_changelog_preserved(self) -> None:
        docs = self.root / "docs"
        docs.mkdir()
        path = docs / "guide.md"
        path.write_text("Based on FAIR analysis version 1.2 and Python 3.12.15.\n")
        self.assertEqual(release.check(self.root), [])
        path.write_text(path.read_text() + "The Guide version 2.3.4 is current.\n")
        self.assertIn("docs", "\n".join(release.check(self.root)))
        path.write_text("Use v1.0.0-alpha.1.\n")
        self.assertIn("guide.md:1", "\n".join(release.check(self.root)))

    @patch.object(release, "history", return_value=("v0.9.0", {"a", "b"}))
    def test_prepare_synchronizes_files_and_preserves_bibliography(self, _history) -> None:
        citation_reference = (self.root / "CITATION.cff").read_text(encoding="utf-8").split("references:", 1)[1]
        stamp = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
        changed = release.prepare(self.root, "1.0.0-alpha.2", "2026-10-14", self.prs, "motyc", now=stamp)
        self.assertEqual(len(changed), 8)
        self.assertEqual(release.check(self.root), [])
        self.assertEqual(
            (self.root / "CITATION.cff").read_text(encoding="utf-8").split("references:", 1)[1], citation_reference
        )
        guide = tomllib.loads((self.root / release.FILES[0]).read_text(encoding="utf-8"))["guide"]
        self.assertEqual(guide["releaseStatus"], "testing")
        log = (self.root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("[#2]", log)
        self.assertIn("[#3]", log)
        self.assertNotIn("[#1]", log)
        self.assertNotIn("[#4]", log)
        self.assertNotIn("Draft notes.", log)
        self.assertIn("Historical release text.", log)
        self.assertIn(r"One \[complete\]", log)
        actions = tomllib.loads((self.root / "content/provenance.toml").read_text(encoding="utf-8"))["action"]
        self.assertEqual(actions[-1]["agent"], "david-novak")
        self.assertEqual(actions[-1]["endTime"], stamp)
        register = tomllib.loads((self.root / "content/identifiers.toml").read_text(encoding="utf-8"))
        self.assertEqual(register["issued"]["actions"][-1], "release-1.0.0-alpha.2")

    @patch.object(release, "history", return_value=(None, {"a", "b"}))
    def test_bad_actor_empty_log_and_bad_input_never_write(self, _history) -> None:
        before = self.snapshot()
        for target, released, prs, actor in (
            ("1.2.3", "2026-10-14", self.prs, "unreviewed"),
            ("1.2.3", "2026-10-14", [], "motyc"),
            ("1.2.3", "2026-02-30", self.prs, "motyc"),
            ("1.2.3", "2026-10-14", [{**self.prs[0], "html_url": "javascript:bad"}], "motyc"),
        ):
            with self.assertRaises(ValueError):
                release.prepare(self.root, target, released, prs, actor)
            self.assertEqual(self.snapshot(), before)

    def test_real_ancestry_excludes_previous_tag_and_non_ancestor_pr(self) -> None:
        def command(*args):
            return subprocess.run(
                ["git", *args], cwd=self.root, check=True, capture_output=True, text=True
            ).stdout.strip()

        command("init", "--initial-branch=main")
        command("config", "user.name", "Test")
        command("config", "user.email", "test@example.com")
        command("add", ".")
        command("commit", "-m", "Initial")
        initial = command("rev-parse", "HEAD")
        command("tag", "v0.9.0")
        (self.root / "changed").write_text("new")
        command("add", ".")
        command("commit", "-m", "Merged change")
        newest = command("rev-parse", "HEAD")
        previous, commits = release.history(self.root)
        self.assertEqual(previous, "v0.9.0")
        self.assertEqual(commits, {newest})
        log = release.changelog(
            "# Changelog\n\n## [Unreleased]\n\n## [0.9.0]\n\nOld text.\n",
            "1.0.0",
            "2026-10-14",
            [self.pr(1, initial, "Old"), self.pr(2, newest, "Merged"), self.pr(3, "other", "Other branch")],
            commits,
            previous=previous,
        )
        self.assertIn("[#2]", log)
        self.assertNotIn("[#1]", log)
        self.assertNotIn("[#3]", log)
        self.assertTrue(log.endswith("## [0.9.0]\n\nOld text.\n"))

    @patch.object(release, "history", return_value=(None, {"a", "b"}))
    def test_prepared_metadata_generates_the_same_crate_versions_and_date(self, _history) -> None:
        shutil.copytree(ROOT / "content", self.root / "content", dirs_exist_ok=True)
        for name in release.FILES[1:]:
            shutil.copyfile(ROOT / name, self.root / name)
        issued = tomllib.loads((self.root / "content/identifiers.toml").read_text(encoding="utf-8"))["issued"][
            "actions"
        ]
        suffix = 1
        while f"release-999999.0.0-fixture.{suffix}" in issued:
            suffix += 1
        release.prepare(self.root, f"999999.0.0-fixture.{suffix}", "2026-10-14", self.prs, "motyc")
        crate = build_crate.build_crate(build_crate.load_content(self.root / "content"))
        site = self.root / "site"
        site.mkdir()
        (site / "ro-crate-metadata.json").write_text(json.dumps(crate, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(release.check(self.root, site), [])


if __name__ == "__main__":
    unittest.main()
