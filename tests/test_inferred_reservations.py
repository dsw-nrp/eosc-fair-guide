"""The identity-only refresh view reserves the organisations the full build infers."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_crate as kb  # noqa: E402
import refresh_snapshots as refresh  # noqa: E402
from catalogue_identity import preserve_snapshot  # noqa: E402


class InferredReservationsTests(unittest.TestCase):
    def test_every_built_organisation_is_reserved_before_a_dashboard_refresh(self):
        content = kb.load_content()
        crate = kb.build_crate(content)
        base = kb.record_base_of(crate)
        expected = {
            entity["@id"].removeprefix(base)
            for entity in crate["@graph"]
            if entity["@id"].startswith(base + "organizations/") and "#" not in entity["@id"]
        }
        self.assertIn("organizations/carpentries", expected)
        target = ROOT / "content/snapshots/fip-dashboard.toml"
        reserved = refresh.reserved_identifiers(ROOT, target)
        _, projected = kb.catalogue_identity_graph(refresh.identity_content(ROOT))
        self.assertEqual(expected, {value for value in projected.values() if value.startswith("organizations/")})
        self.assertLessEqual(expected, reserved)

    def test_a_new_source_cannot_reuse_an_inferred_agent_address(self):
        target = ROOT / "content/snapshots/fip-dashboard.toml"
        incoming = '[snapshot]\nsource="FIP Dashboard"\n[[organization]]\nid="new-observation"\nname="Carpentries"\n'
        with self.assertRaisesRegex(ValueError, "organizations/carpentries.*review"):
            preserve_snapshot(incoming, target.read_text(encoding="utf-8"), refresh.reserved_identifiers(ROOT, target))

    def test_inference_needs_no_page_or_check_content_and_reuses_known_agents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / "content"
            content.mkdir()
            (content / "guide.toml").write_text(
                '[guide]\n[[organization]]\nid="known"\nname="Known Institute"\n', encoding="utf-8"
            )
            (content / "resources.toml").write_text(
                '[[resource]]\nid="tool"\ntype="tool"\nname="A tool"\n'
                'operator={name="Known Institute"}\ncitation={publisher="Publisher Institute"}\n',
                encoding="utf-8",
            )
            (content / "repositories.toml").write_text(
                '[[repository]]\nid="archive"\nname="An archive"\nurl="https://archive.example.org/"\n'
                'operator={name="Operator Institute"}\ndeveloper={name="Developer Institute"}\n',
                encoding="utf-8",
            )
            reserved = refresh.reserved_identifiers(root, content / "snapshots/fip-dashboard.toml")
            self.assertLessEqual(
                {
                    "organizations/known",
                    "organizations/publisher-institute",
                    "organizations/operator-institute",
                    "organizations/developer-institute",
                },
                reserved,
            )
            self.assertNotIn("organizations/known-institute", reserved)


if __name__ == "__main__":
    unittest.main()
