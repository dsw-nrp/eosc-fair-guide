"""NKR's first public harvest exercises refresh, identity, catalogue and contracts."""

import copy
import json
import re
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, URIRef

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from datetime import date

import build_crate
import catalogue_identity
import check_duplicates
import check_health
import refresh_snapshots

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "nkr"


def fixture_snapshot():
    snapshot = refresh_snapshots.nkr(refresh_snapshots.Fetcher(FIXTURE), "2026-11-01")
    return tomllib.loads(catalogue_identity.preserve_snapshot(snapshot.text(), ""))


def reference_content():
    content = build_crate.load_content()
    content["snapshots"].append(fixture_snapshot())
    next(row for row in content["repositories"] if row["id"] == "czech-bioimaging")["nkr"] = "20.500.14818/srhtp4ek"
    return content


class NkrIdentityTests(unittest.TestCase):
    def test_real_records_receive_readable_kind_routes_without_contact_addresses(self):
        raw = json.loads((FIXTURE / "nkr-0.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["size"], 5)
        for path in FIXTURE.glob("*.json"):
            addresses = re.findall(r"[\w.+-]+@([\w.-]+\.[A-Za-z]{2,})", path.read_text(encoding="utf-8"))
            self.assertTrue(all(domain == "example.org" for domain in addresses))
        snapshot = refresh_snapshots.nkr(refresh_snapshots.Fetcher(FIXTURE), "2026-11-01")
        data = tomllib.loads(catalogue_identity.preserve_snapshot(snapshot.text(), ""))
        herbarium = next(row for row in data["record"] if "herbarium" in row.get("mainUrl", ""))
        self.assertEqual((herbarium["id"], herbarium["guideRoute"]), ("herbarium", "repo/dom"))
        for row in data["record"]:
            handle = catalogue_identity.alternate_id(row, "nkr")
            self.assertNotEqual(row["id"], handle.rsplit("/", 1)[-1])


class NkrRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(FIXTURE.parent / "minimal/content", self.root / "content")
        self.inputs = self.root / "inputs"
        shutil.copytree(FIXTURE, self.inputs)
        (self.root / "content/checks/gate.toml").write_text(
            '[[item]]\nid = "gate.13"\nprefill.nkr = ["mainContact", "pidType"]\n', encoding="utf-8"
        )

    def refresh(self):
        return refresh_snapshots.refresh("nkr", refresh_snapshots.Fetcher(self.inputs), "2026-11-01", self.root)

    def test_schema_selects_fields_and_reports_unavailable_prefill(self):
        outcome = self.refresh()
        self.assertEqual(outcome.status, "changed", outcome.reason)
        self.assertIn("pidType", outcome.reason)
        data = tomllib.loads((self.root / outcome.path).read_text(encoding="utf-8"))
        self.assertNotIn("pidType", data["snapshot"]["fields"])
        self.assertIn("status", data["snapshot"]["fields"])
        self.assertIn("additionalNames", data["snapshot"]["fields"])
        self.assertTrue(all(row["mainContactPresent"] for row in data["record"]))
        config = build_crate.nkr_config([data])
        self.assertTrue(all(row["content"]["mainContact"] is True for row in config["records"]))
        self.assertNotIn("@example.org", (self.root / outcome.path).read_text(encoding="utf-8"))
        self.assertIn("pidType", self.refresh().reason, "unchanged outcomes keep schema warnings")

    def test_unreadable_or_invalid_schema_preserves_previous_snapshot(self):
        path = self.root / "content/snapshots/nkr.toml"
        path.parent.mkdir(exist_ok=True)
        path.write_text("previous snapshot\n", encoding="utf-8")
        schema = self.inputs / "nkr-schema.json"
        schema.unlink()
        for value in (None, {}, {"properties": []}):
            with self.subTest(schema=value):
                if value is not None:
                    schema.write_text(json.dumps(value), encoding="utf-8")
                outcome = self.refresh()
                self.assertEqual(outcome.status, "rejected")
                self.assertIn("schema", outcome.reason)
                self.assertEqual(path.read_text(encoding="utf-8"), "previous snapshot\n")

    def test_operational_record_without_address_rejects_without_writing(self):
        self.assertEqual(self.refresh().status, "changed")
        path = self.root / "content/snapshots/nkr.toml"
        previous = path.read_bytes()
        page = self.inputs / "nkr-0.json"
        data = json.loads(page.read_text(encoding="utf-8"))
        row = data["results"][0]
        row["content"]["mainUrl"] = ""
        page.write_text(json.dumps(data), encoding="utf-8")
        outcome = self.refresh()
        self.assertEqual(outcome.status, "rejected")
        self.assertIn(row["id"], outcome.reason)
        self.assertIn(row["content"]["repositoryName"], outcome.reason)
        self.assertEqual(path.read_bytes(), previous)


class NkrCatalogueTests(unittest.TestCase):
    def test_nkr_names_and_classification_override_but_empty_address_keeps_curated_facts(self):
        content = reference_content()
        curated = next(row for row in content["repositories"] if row["id"] == "czech-bioimaging")
        crate = build_crate.build_crate(content)
        entities = {row["@id"]: row for row in crate["@graph"]}
        bird = entities["#repository-czech-bioimaging"]
        self.assertEqual(bird["name"], build_crate.text({"cs": "CzBIRD", "en": "CzBIRD"}))
        self.assertEqual(bird["url"], curated["url"])
        self.assertEqual(
            build_crate.as_list(bird["repositoryFunction"]),
            build_crate.refs(["#rfunction-" + value for value in curated["functions"]]),
        )
        self.assertEqual(bird["publisher"], build_crate.ref("#org-czech-bioimaging"))
        self.assertEqual(bird["serviceStatus"], build_crate.ref("#status-in-development"))
        self.assertEqual(bird["statusAsOf"], "2026-11-01")
        self.assertEqual(
            entities["#resource-datarepo"]["name"],
            build_crate.text({"cs": "Datový catch-all repozitář", "en": "Data Catch-all Repository"}),
        )
        self.assertEqual(
            entities["#repository-herbarium"]["name"],
            build_crate.text({"cs": "Repozitář herbářových sbírek", "en": "Herbarium Collections Repository"}),
        )

    def test_all_seven_statuses_are_dated_by_retrieval_and_retirement_is_reported(self):
        schema = json.loads((FIXTURE / "nkr-schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(schema["properties"]["status"]["enum"]), set(build_crate.NKR_STATUS))
        for native, expected in build_crate.NKR_STATUS.items():
            with self.subTest(status=native):
                content = reference_content()
                snapshot = content["snapshots"][-1]
                row = next(row for row in snapshot["record"] if row["repositoryName"] == "CzBIRD")
                row["status"] = native
                graph = build_crate.Graph()
                build_crate.build_crate(content, graph)
                bird = graph.entities["#repository-czech-bioimaging"]
                if expected:
                    self.assertEqual(bird["serviceStatus"], build_crate.ref("#status-" + expected))
                    self.assertEqual(bird["statusAsOf"], "2026-11-01")
                    self.assertEqual(
                        bird.get("acceptsDeposits"),
                        False
                        if expected in ("planned", "in-development") or native == "pilot - not accepting data"
                        else None,
                    )
                else:
                    self.assertEqual(bird["serviceStatus"], build_crate.ref("#status-pilot"))
                    self.assertNotIn(build_crate.ref("#snapshot-nkr"), build_crate.as_list(bird["isBasedOn"]))
                    groups = check_health.integrity(content, build_crate.ROOT, date(2026, 11, 2), graph)
                    finding = next(group for group in groups if group["type"] == "NKR maintainer findings")["items"][0]
                    self.assertEqual(finding["id"], "20.500.14818/srhtp4ek")
                    self.assertIn("#repository-czech-bioimaging", " ".join(finding["notes"]))

    def test_profile_accepts_only_not_yet_public_nkr_repositories_without_addresses(self):
        content = reference_content()
        next(row for row in content["repositories"] if row["id"] == "czech-bioimaging").pop("nkr")
        crate = build_crate.build_crate(content)
        crate["@context"][0] = json.loads((FIXTURE.parent / "ro-crate-1.2-context.json").read_text())["@context"]
        base = content["guide"]["guide"]["namespace"]
        data = Graph().parse(data=json.dumps(crate), format="json-ld", publicID=base)
        shapes = Graph()
        for shape in build_crate.profile_shapes(build_crate.ROOT, base).values():
            shapes.parse(data=shape, format="turtle", publicID=base)
        self.assertTrue(validate(data, shacl_graph=shapes, advanced=True)[0])
        node = URIRef(base + "#repository-czbird")
        status = URIRef(base + "terms#serviceStatus")
        data.set((node, status, URIRef(base + "#status-operational")))
        conforms, _, report = validate(data, shacl_graph=shapes, advanced=True)
        self.assertFalse(conforms)
        self.assertIn("repository-czbird", report)
        data.set((node, status, URIRef(base + "#status-in-development")))
        data.remove((node, URIRef("http://schema.org/sameAs"), None))
        self.assertFalse(validate(data, shacl_graph=shapes, advanced=True)[0])

    def test_reference_harvest_joins_four_entries_and_adds_one(self):
        original = build_crate.build_crate(build_crate.load_content())
        crate = build_crate.build_crate(reference_content())
        entities = {row["@id"]: row for row in crate["@graph"]}
        before = next(row for row in original["@graph"] if row["@id"] == "#repositories")["hasPart"]
        self.assertEqual(len(entities["#repositories"]["hasPart"]), len(before) + 1)
        joined = [
            row
            for row in entities.values()
            if any(
                link.get("@id", "").startswith(build_crate.NKR_OBJECTS)
                for link in build_crate.as_list(row.get("sameAs"))
            )
        ]
        self.assertEqual(len(joined), 5)
        self.assertIn("#repository-herbarium", entities)
        self.assertIn(build_crate.ref("#snapshot-nkr"), entities["#resource-datarepo"]["isBasedOn"])

    def test_an_nkr_address_reaching_two_components_is_refused(self):
        content = reference_content()
        row = {"id": "one-vault", "name": "One vault", "url": "https://archaeo-vault.cz", "re3data": "r3d999999998"}
        second = copy.deepcopy(row)
        second.update(id="other-vault", re3data="r3d999999999")
        content["repositories"].extend([row, second])
        with self.assertRaises(build_crate.ContentError) as raised:
            build_crate.build_crate(content)
        for value in ("20.500.14818/9lloktrg", row["id"], second["id"]):
            self.assertIn(value, str(raised.exception))
        duplicate_report = check_duplicates.check(content, check_duplicates._accepted(build_crate.ROOT))
        self.assertTrue(
            any(
                "keys reach different entries" in error and "one-vault" in error and "other-vault" in error
                for error in duplicate_report.errors
            )
        )

    def test_nkr_address_joins_dashboard_only_entry_preserving_identity_and_evidence(self):
        content = reference_content()
        before = build_crate.Graph()
        build_crate.build_crate(content, before)
        original = copy.deepcopy(before.entities["#fer-cesnet-invenio"])
        record = copy.deepcopy(content["snapshots"][-1]["record"][0])
        record.update(
            id="nkr-cesnet",
            alternateIds=[{"scheme": "nkr", "value": "20.500.14818/cesnet-test"}],
            repositoryName="NKR CESNET repository",
            additionalNames=[],
            mainUrl=original["url"].rstrip("/"),
            type="generic",
            status="pilot - not accepting data",
        )
        content["snapshots"][-1]["record"].append(record)
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
        matching = [
            link["@id"]
            for link in build_crate.as_list(graph.entities["#repositories"]["hasPart"])
            if build_crate.bare_url(graph.entities[link["@id"]].get("url")) == build_crate.bare_url(record["mainUrl"])
        ]
        self.assertEqual(matching, [original["@id"]])
        self.assertNotIn("#repository-nkr-cesnet", graph.entities)
        entity = graph.entities[original["@id"]]
        for prop in ("identifier", "catalogueAddress", "provider", "review", "repositoryFunction"):
            self.assertEqual(entity[prop], original[prop], prop)
        self.assertEqual(
            entity["name"], build_crate.text({"cs": record["repositoryName"], "en": record["repositoryName"]})
        )
        self.assertEqual(entity["repositoryKind"], build_crate.ref("#rkind-general"))
        self.assertEqual(entity["serviceStatus"], build_crate.ref("#status-pilot"))
        self.assertEqual(entity["statusAsOf"], "2026-11-01")
        self.assertIs(entity["acceptsDeposits"], False)
        for source in ("#snapshot-fip-dashboard", "#snapshot-nkr"):
            self.assertIn(build_crate.ref(source), build_crate.as_list(entity["isBasedOn"]))
        for source in (
            "https://fip-dashboard.dmp.eosc.cz/resources/nrp-invenio",
            "https://repo.cz/objects/20.500.14818/cesnet-test",
        ):
            self.assertIn(build_crate.ref(source), build_crate.as_list(entity["sameAs"]))
        self.assertEqual(graph.index["fip-dashboard.nrp-invenio"], [original["@id"]])
        self.assertEqual(check_duplicates.check(content, check_duplicates._accepted(build_crate.ROOT)).errors, [])

    def test_nkr_join_does_not_turn_a_dashboard_publication_repository_into_a_data_deposit(self):
        content = reference_content()
        record = content["snapshots"][-1]["record"][0]
        record["mainUrl"] = "https://nusl.cz/"
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
        entity = graph.entities["#fer-nusl"]
        self.assertEqual(entity["repositoryFunction"], build_crate.refs(["#rfunction-deposit-publications"]))
        self.assertIn(build_crate.ref("#snapshot-nkr"), build_crate.as_list(entity["isBasedOn"]))

    def test_nkr_handle_and_dashboard_address_reaching_different_entries_are_refused(self):
        content = reference_content()
        record = next(row for row in content["snapshots"][-1]["record"] if row["repositoryName"] == "CzBIRD")
        record["mainUrl"] = "https://nusl.cz/"
        with self.assertRaises(build_crate.ContentError) as raised:
            build_crate.build_crate(content)
        for value in ("20.500.14818/srhtp4ek", "czech-bioimaging", "nusl"):
            self.assertIn(value, str(raised.exception))
        errors = check_duplicates.check(content, check_duplicates._accepted(build_crate.ROOT)).errors
        self.assertTrue(
            any(
                all(value in error for value in ("keys reach different entries", "czech-bioimaging", "nusl"))
                for error in errors
            )
        )

    def test_dashboard_and_curated_addresses_stay_separate_until_an_nkr_join_is_ambiguous(self):
        content = reference_content()
        content["repositories"].append(
            {"id": "other-cesnet", "name": "Another CESNET entry", "url": "https://data.narodni-repozitar.cz/"}
        )
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
        ids = [link["@id"] for link in build_crate.as_list(graph.entities["#repositories"]["hasPart"])]
        self.assertIn("#repository-other-cesnet", ids)
        self.assertIn("#fer-cesnet-invenio", ids)
        record = content["snapshots"][-1]["record"][0]
        record["mainUrl"] = "https://data.narodni-repozitar.cz/"
        with self.assertRaises(build_crate.ContentError) as raised:
            build_crate.build_crate(content)
        for value in ("other-cesnet", "cesnet-invenio"):
            self.assertIn(value, str(raised.exception))

    def test_duplicate_check_joins_reference_harvest_but_refuses_two_curated_owners(self):
        content = reference_content()
        accepted = check_duplicates._accepted(build_crate.ROOT)
        self.assertEqual(check_duplicates.check(content, accepted).errors, [])
        first = next(row for row in content["repositories"] if row["id"] == "czech-bioimaging")
        second = copy.deepcopy(first)
        second.update(id="another-bird", name="Another bird", url="https://another.example.org")
        content["repositories"].append(second)
        errors = check_duplicates.check(content, accepted).errors
        self.assertTrue(
            any(
                all(value in error for value in ("czech-bioimaging", "another-bird", "20.500.14818/srhtp4ek"))
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
