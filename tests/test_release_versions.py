"""Release metadata, real tag ancestry, provenance and refusal-before-write contracts."""

from __future__ import annotations

import io
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
import build_identity  # noqa: E402
import check_changelog  # noqa: E402
import release_versions as release  # noqa: E402


class ReleaseVersions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".github").mkdir()
        shutil.copyfile(ROOT / release.PATH_POLICY, self.root / release.PATH_POLICY)
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
        for name in ("package.json", "package-lock.json", ".zenodo.json"):
            path = self.root / name
            data = json.loads(path.read_text(encoding="utf-8"))
            data["version"] = "1.0.0-alpha.1"
            if name == "package-lock.json":
                data["packages"][""]["version"] = data["version"]
            if name == ".zenodo.json":
                data["publication_date"] = "2026-10-08"
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

    def test_shared_policy_rejects_missing_and_extra_prepared_files_before_writes(self) -> None:
        policy = json.loads((self.root / release.PATH_POLICY).read_text(encoding="utf-8"))
        for additional in (policy["additional"][:-1], [*policy["additional"], "SECURITY.md"]):
            with self.subTest(additional=additional):
                (self.root / release.PATH_POLICY).write_text(json.dumps({**policy, "additional": additional}))
                before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
                with (
                    patch.object(release, "history", return_value=(None, {"a", "b"})),
                    self.assertRaisesRegex(ValueError, "shared release path policy"),
                ):
                    release.prepare(self.root, "1.2.3", "2026-10-18", self.prs, "motyc")
                after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
                self.assertEqual(after, before)

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

    def test_the_dispatch_input_may_carry_the_tag_form(self) -> None:
        empty = self.root / "empty.json"
        empty.write_text("[]", encoding="utf-8")
        inputs = ["--prs", str(empty), "--associations", str(empty), "--actor", "motyc"]
        # prepare(root, version, ...) and check(root, site, version) receive the bare version either way.
        for command, position, result, extra in (("prepare", 1, {"files": []}, inputs), ("check", 2, [], [])):
            with self.subTest(command=command):
                passed: list[str] = []

                def record(*a, sink=passed, at=position, value=result, **_):
                    sink.append(a[at])
                    return value

                with patch.object(release, command, side_effect=record), patch("builtins.print"):
                    for value in ("v1.0.0-alpha.4", " 1.0.0-alpha.4\n"):
                        self.assertEqual(release.main([command, "--version", value, *extra]), 0)
                self.assertEqual(passed, ["1.0.0-alpha.4", "1.0.0-alpha.4"])
        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(release.main(["check", "--version", "vv1.0.0"]), 1)
        self.assertIn("1.0.0-alpha.4 or v1.0.0-alpha.4", stderr.getvalue())

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
        built = build_identity.identity(self.root)
        for node in nodes:
            node["creativeWorkStatus"] = built["status"]
        ui = site / release.BUILD_UI
        ui.parent.mkdir(parents=True)
        ui.write_text("window.FairGuideData.ui = " + json.dumps({"config": {"build": built}}) + ";\n")
        health = site / "api/health.json"
        health.parent.mkdir()
        health.write_text(json.dumps({"build": built}))
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

    def test_the_built_page_identity_is_checked_against_git(self) -> None:
        site = self.root / "_site"
        _, missing = release.built_identity(site, self.root)
        self.assertTrue(any("required page configuration" in error for error in missing))
        script = site / release.BUILD_UI
        script.parent.mkdir(parents=True, exist_ok=True)
        expected = build_identity.identity(self.root)
        script.write_text(
            'window.FairGuideData.ui = {"config":{"build":' + json.dumps(expected) + "}};\n", encoding="utf-8"
        )
        _, errors = release.built_identity(site, self.root)
        self.assertEqual(errors, [])

        wrong_commit = {**expected, "commit": "deadbee"}
        script.write_text(
            'window.FairGuideData.ui = {"config":{"build":' + json.dumps(wrong_commit) + "}};\n", encoding="utf-8"
        )
        _, errors = release.built_identity(site, self.root)
        self.assertTrue(any("build.commit" in error for error in errors))

        preview = {**expected, "channel": "next", "status": "production"}
        script.write_text(
            'window.FairGuideData.ui = {"config":{"build":' + json.dumps(preview) + "}};\n", encoding="utf-8"
        )
        _, errors = release.built_identity(site, self.root)
        self.assertTrue(any("must report the testing status" in error for error in errors))

    @patch.object(release, "history", return_value=("v0.9.0", {"a", "b"}))
    def test_prepare_synchronizes_files_and_preserves_bibliography(self, _history) -> None:
        citation_reference = (self.root / "CITATION.cff").read_text(encoding="utf-8").split("references:", 1)[1]
        stamp = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
        changed = release.prepare(self.root, "1.0.0-alpha.2", "2026-10-14", self.prs, "motyc", now=stamp)
        self.assertEqual(len(changed["files"]), len(release.FILES) + 3)
        self.assertIn(".zenodo.json", {item["path"] for item in changed["files"]})
        self.assertEqual(
            {item["path"] for item in changed["files"]},
            set(release.FILES) | {"CHANGELOG.md", "content/provenance.toml", "content/identifiers.toml"},
        )
        self.assertTrue(all(len(item["sha256"]) == 64 for item in changed["files"]))
        self.assertEqual(release.check(self.root), [])
        self.assertEqual(
            (self.root / "CITATION.cff").read_text(encoding="utf-8").split("references:", 1)[1], citation_reference
        )
        guide = tomllib.loads((self.root / release.FILES[0]).read_text(encoding="utf-8"))["guide"]
        self.assertNotIn("releaseStatus", guide)
        log = (self.root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("[#2]", log)
        self.assertIn("[#3]", log)
        self.assertNotIn("[#1]", log)
        self.assertNotIn("[#4]", log)
        # Previously accepted free-form notes move unchanged into the release, ahead of the generated lineage.
        self.assertIn("## [Unreleased]\n\n## [1.0.0-alpha.2] - 2026-10-14\n\nDraft notes.\n\nSince v0.9.0.", log)
        self.assertIn("Historical release text.", log)
        self.assertIn(r"One \[complete\]", log)
        original_zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
        prepared_zenodo = json.loads((self.root / ".zenodo.json").read_text(encoding="utf-8"))
        self.assertEqual(prepared_zenodo["version"], "1.0.0-alpha.2")
        self.assertEqual(prepared_zenodo["publication_date"], "2026-10-14")
        for field in set(original_zenodo) - {"version", "publication_date"}:
            self.assertEqual(prepared_zenodo[field], original_zenodo[field], field)
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

    def git_history(self, *, tagged=True, direct=True):
        def command(*args):
            return subprocess.run(
                ["git", *args], cwd=self.root, check=True, capture_output=True, encoding="utf-8"
            ).stdout.strip()

        command("init", "--initial-branch=main")
        command("config", "user.name", "Test")
        command("config", "user.email", "test@example.com")
        command("add", ".")
        command("commit", "-m", "Initial")
        if tagged:
            command("tag", "v0.9.0")
        if direct:
            (self.root / "direct").write_text("direct content", encoding="utf-8")
            command("add", "direct")
            command("commit", "-m", "Fix [direct] content")
        return release.history_export(self.root)

    def associations(self, local):
        return {
            "formatVersion": 1,
            "source": local["source"],
            "previousTag": local["previousTag"],
            "repository": "dsw-nrp/eosc-fair-guide",
            "base": "main",
            "associations": {entry["sha"]: [] for entry in local["firstParent"]},
        }

    def test_direct_only_release_uses_real_history_and_preserves_zenodo_fields(self):
        local = self.git_history()
        self.assertEqual(len(local["commits"]), 1)
        self.assertEqual(local["firstParent"][0]["sha"], local["source"])
        release.prepare(self.root, "1.0.0-alpha.2", "2026-10-14", [], "motyc", associations=self.associations(local))
        text = (self.root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("### Direct commits", text)
        self.assertIn(r"Fix \[direct\] content", text)
        self.assertIn("/commit/" + local["source"], text)
        self.assertNotIn("### Merged pull requests", text)
        self.assertEqual(release.check(self.root, requested="1.0.0-alpha.2"), [])

    def test_first_release_uses_all_history_without_a_pr(self):
        local = self.git_history(tagged=False, direct=False)
        self.assertIsNone(local["previousTag"])
        release.prepare(self.root, "1.0.0-alpha.2", "2026-10-14", [], "motyc", associations=self.associations(local))
        self.assertIn("the beginning of the repository", (self.root / "CHANGELOG.md").read_text())

    def commit(self, message: str, name: str | None = None) -> str:
        if name:
            (self.root / name).write_text(message, encoding="utf-8")
        for args in (["add", "-A"], ["commit", "-q", "-m", message]):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        return release.git(self.root, "rev-parse", "HEAD")

    def landed_after_preparation(self) -> tuple[list[dict], dict, dict[str, str]]:
        """A prepared 1.0.0-alpha.2 merged from its own branch, then a PR and a direct commit before any tag."""
        local = self.git_history()
        release.prepare(self.root, "1.0.0-alpha.2", "2026-10-14", [], "motyc", associations=self.associations(local))
        shas = {
            "release": self.commit("Prepare release 1.0.0-alpha.2"),
            "pull": self.commit("Later change", "later"),
            "direct": self.commit("Direct follow-up", "follow-up"),
        }
        repo = {"full_name": "dsw-nrp/eosc-fair-guide"}
        prs = [
            {
                **self.pr(5, shas["release"], "Prepare release 1.0.0-alpha.2"),
                "head": {"ref": "release/1.0.0-alpha.2", "repo": repo},
            },
            {**self.pr(6, shas["pull"], "Later change"), "head": {"ref": "feature/later", "repo": repo}},
        ]
        for pr in prs:
            pr["base"] = {"ref": "main", "repo": repo}
        associations = self.associations(release.history_export(self.root))
        associations["associations"] |= {shas["release"]: [5], shas["pull"]: [6]}
        return prs, associations, shas

    def test_tag_release_names_the_changes_a_prepared_release_misses(self):
        prs, associations, shas = self.landed_after_preparation()
        missing = release.missing_lineage(self.root, "1.0.0-alpha.2", prs, associations)
        self.assertEqual(missing["previous"], "v0.9.0")
        self.assertEqual(len(missing["pulls"]), 1)
        self.assertIn("[#6]", missing["pulls"][0])
        self.assertEqual(len(missing["direct"]), 1, "the earlier direct commit is listed; the release's own is not")
        self.assertIn(shas["direct"], missing["direct"][0])
        self.assertNotIn("#5", "".join(missing["pulls"] + missing["direct"]), "a release never lists itself")
        summary = self.root / "summary.md"
        (self.root / "prs.json").write_text(json.dumps(prs), encoding="utf-8")
        (self.root / "associations.json").write_text(json.dumps(associations), encoding="utf-8")
        argv = ["lineage", "--version", "v1.0.0-alpha.2", "--prs", str(self.root / "prs.json")]
        argv += ["--associations", str(self.root / "associations.json"), "--summary", str(summary)]
        with patch.object(release, "ROOT", self.root), patch("builtins.print"):
            self.assertEqual(release.main(argv), 3)
        report = summary.read_text(encoding="utf-8")
        self.assertIn("Not tagged: the `1.0.0-alpha.2` changelog misses 2 change(s) since v0.9.0", report)
        for marker in ("**Next:**", "**If blocked:**", "**Done when:** Tag release creates `v1.0.0-alpha.2`"):
            self.assertIn(marker, report)

    def test_completion_adds_only_the_missing_entries(self):
        prs, associations, shas = self.landed_after_preparation()
        before = self.snapshot()
        earlier = before["CHANGELOG.md"].decode("utf-8")
        manifest = release.complete(self.root, "1.0.0-alpha.2", prs, associations=associations)
        after = self.snapshot()
        self.assertEqual({path for path in after if after[path] != before.get(path)}, {"CHANGELOG.md"})
        self.assertEqual(manifest["mode"], "complete")
        self.assertEqual({item["path"] for item in manifest["files"]}, release.prepared_paths(self.root))
        text = after["CHANGELOG.md"].decode("utf-8")
        self.assertIn("[#6]", text)
        self.assertIn("/commit/" + shas["direct"], text)
        self.assertNotIn("[#5]", text)
        self.assertEqual(release.check(self.root, requested="1.0.0-alpha.2"), [])
        self.assertEqual(check_changelog.history_errors(earlier, text, "base", set()), [])
        self.assertEqual(release.missing_lineage(self.root, "1.0.0-alpha.2", prs, associations)["pulls"], [])
        with self.assertRaisesRegex(ValueError, "already lists every change"):
            release.complete(self.root, "1.0.0-alpha.2", prs, associations=associations)
        # Merged from the release branch like the preparation, the completed changelog lets Tag release proceed.
        completion = self.commit("Complete release 1.0.0-alpha.2")
        prs = [*prs, {**prs[0], **self.pr(7, completion, "Complete release 1.0.0-alpha.2")}]
        associations = self.associations(release.history_export(self.root))
        associations["associations"] |= {shas["release"]: [5], shas["pull"]: [6], completion: [7]}
        for name, data in (("prs.json", prs), ("associations.json", associations)):
            (self.root / ".git" / name).write_text(json.dumps(data), encoding="utf-8")
        argv = ["lineage", "--version", "1.0.0-alpha.2", "--prs", str(self.root / ".git/prs.json")]
        argv += ["--associations", str(self.root / ".git/associations.json")]
        with patch.object(release, "ROOT", self.root), patch("builtins.print") as printed:
            self.assertEqual(release.main(argv), 0)
        self.assertIn("lists every change since v0.9.0", printed.call_args.args[0])

    def test_preparing_a_version_the_default_branch_carries_completes_it(self):
        prs, associations, _ = self.landed_after_preparation()
        for name, data in (("prs.json", prs), ("associations.json", associations)):
            (self.root / name).write_text(json.dumps(data), encoding="utf-8")
        argv = ["prepare", "--version", "1.0.0-alpha.2", "--prs", str(self.root / "prs.json"), "--actor", "motyc"]
        argv += ["--associations", str(self.root / "associations.json"), "--manifest", str(self.root / "m.json")]
        with patch.object(release, "ROOT", self.root), patch("builtins.print"):
            self.assertEqual(release.main(argv), 0)
        self.assertEqual(json.loads((self.root / "m.json").read_text(encoding="utf-8"))["mode"], "complete")

    def test_a_missing_merged_list_is_added_before_the_direct_commits(self):
        section = "## [1.0.0] - 2026-10-14\n\nSince v0.9.0.\n\n### Direct commits\n\n- Fix ([aaaaaaa](https://x/commit/a))\n\n"
        text = "# Changelog\n\n## [Unreleased]\n\n" + section
        pull = "- Later ([#6](https://github.com/dsw-nrp/eosc-fair-guide/pull/6))"
        extended = release.extend_section(text, "1.0.0", {"pulls": [pull], "direct": []})
        self.assertIn(f"Since v0.9.0.\n\n### Merged pull requests\n\n{pull}\n\n### Direct commits\n", extended)

    def test_empty_history_and_stale_or_incomplete_associations_never_write(self):
        local = self.git_history(direct=False)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "no commits"):
            release.prepare(self.root, "1.2.3", "2026-10-14", [], "motyc", associations=self.associations(local))
        self.assertEqual(self.snapshot(), before)
        local = {**local, "firstParent": [{"sha": "a" * 40, "subject": "Changed"}], "commits": ["a" * 40]}
        for edit in ({"source": "b" * 40}, {"associations": {}}, {"associations": {"a" * 40: ["bad"]}}):
            with patch.object(release, "history_export", return_value=local), self.assertRaises(ValueError):
                release.release_changes(self.root, {**self.associations(local), **edit})
        self.assertEqual(self.snapshot(), before)

    def test_mixed_merge_squash_rebase_and_direct_commits_do_not_duplicate_pr_changes(self):
        shas = [character * 40 for character in "abcde"]
        changes = {
            "repository": "dsw-nrp/eosc-fair-guide",
            "base": "main",
            "firstParent": [{"sha": sha, "subject": "Same [title]"} for sha in shas],
            "associations": dict(zip(shas, [[1], [2], [3], [3], [99]], strict=True)),
        }
        prs = [
            {
                **self.pr(number, sha, "Same [title]"),
                "base": {"ref": "main", "repo": {"full_name": changes["repository"]}},
            }
            for number, sha in [(1, shas[0]), (2, shas[1]), (3, shas[3])]
        ]
        text = release.changelog(
            "## [Unreleased]\n\n## [0.9.0]\n\nOld.\n",
            "1.2.3",
            "2026-10-14",
            prs,
            set(shas),
            previous="v0.9.0",
            changes=changes,
        )
        for number in range(1, 4):
            self.assertEqual(text.count(f"[#{number}]"), 1)
        self.assertEqual(text.count("/commit/"), 1)
        self.assertIn("/commit/" + shas[-1], text)
        self.assertTrue(text.endswith("## [0.9.0]\n\nOld.\n"))
        bad_prs = [{**prs[0], "base": {"ref": "other", "repo": {"full_name": changes["repository"]}}}]
        with self.assertRaisesRegex(ValueError, "another repository or base"):
            release.changelog(
                "## [Unreleased]\n", "1.2.3", "2026-10-14", bad_prs, set(shas), previous=None, changes=changes
            )

    def test_curated_notes_survive_beside_the_pr_lineage(self):
        # G2: a curated note and an eligible merged PR must both reach the dated release section.
        text = release.changelog(
            "# Changelog\n\n## [Unreleased]\n\n### Fixed\n\n- Explain the duplicate repair.\n\n## [0.9.0]\n\nOld.\n",
            "1.0.0",
            "2026-10-14",
            [self.pr(2, "b", "Repair duplicates")],
            {"b"},
            previous="v0.9.0",
        )
        unreleased, rest = text.split("## [1.0.0] - 2026-10-14\n\n", 1)
        self.assertTrue(unreleased.endswith("## [Unreleased]\n\n"))
        notes, lineage = rest.split("Since v0.9.0.", 1)
        self.assertEqual(notes, "### Fixed\n\n- Explain the duplicate repair.\n\n")
        self.assertIn("[#2](https://github.com/dsw-nrp/eosc-fair-guide/pull/2)", lineage)
        self.assertTrue(text.endswith("## [0.9.0]\n\nOld.\n"))

    @patch.object(release, "history", return_value=("v0.9.0", {"a", "b"}))
    def test_reserved_or_malformed_notes_refuse_before_any_write(self, _history):
        for unreleased in ("### Merged pull requests\n\n- Hand-written list.\n", "### Added\n"):
            path = self.root / "CHANGELOG.md"
            path.write_text(f"# Changelog\n\n## [Unreleased]\n\n{unreleased}\n## [0.9.0]\n\nOld.\n", encoding="utf-8")
            before = self.snapshot()
            with self.subTest(unreleased=unreleased), self.assertRaisesRegex(ValueError, "CHANGELOG.md"):
                release.prepare(self.root, "1.0.0-alpha.2", "2026-10-14", self.prs, "motyc")
            self.assertEqual(self.snapshot(), before)

    def test_requested_release_requires_matching_nonempty_unique_dated_notes(self):
        target = "1.0.0-alpha.1"
        path = self.root / "CHANGELOG.md"
        for content in (
            "## [Unreleased]\n",
            f"## [{target}] - 2026-10-08\n\n### Notes\n",
            f"## [{target}] - 2000-01-01\n\nA fix.\n",
            f"## [{target}] - 2026-10-08\n\nA fix.\n## [{target}] - 2026-10-08\n\nAgain.\n",
        ):
            path.write_text(content, encoding="utf-8")
            self.assertTrue(release.check(self.root, requested=target), content)
        path.write_text(f"## [{target}] - 2026-10-08\n\n- A fix.\n", encoding="utf-8")
        self.assertEqual(release.check(self.root, requested=target), [])
        self.assertTrue(release.check(self.root, requested="2.0.0"))

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
        built = build_identity.identity(self.root)
        ui = site / release.BUILD_UI
        ui.parent.mkdir(parents=True)
        ui.write_text("window.FairGuideData.ui = " + json.dumps({"config": {"build": built}}) + ";\n")
        health = site / "api/health.json"
        health.parent.mkdir()
        health.write_text(json.dumps({"build": built}))
        self.assertEqual(release.check(self.root, site), [])


if __name__ == "__main__":
    unittest.main()
