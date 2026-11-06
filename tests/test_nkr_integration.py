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
from unittest import mock

from pyshacl import validate
from rdflib import Graph, URIRef

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from datetime import date

import build_crate

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue_identity
import check_content
import check_duplicates
import check_health
import nkr_contract
import refresh_snapshots
from addresses import iri  # noqa: E402

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
        self.assertEqual((herbarium["id"], herbarium["guideRoute"]), ("herbarium", "repositories"))
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
        for value in (None, {}, {"properties": []}, {"properties": {"status": []}}):
            with self.subTest(schema=value):
                if value is not None:
                    schema.write_text(json.dumps(value), encoding="utf-8")
                outcome = self.refresh()
                self.assertEqual(outcome.status, "failed" if value is None else "rejected")
                self.assertIn("schema", outcome.reason)
                self.assertEqual(path.read_text(encoding="utf-8"), "previous snapshot\n")

    def test_schema_transport_failure_is_retryable_without_writing(self):
        self.assertEqual(self.refresh().status, "changed")
        path = self.root / "content/snapshots/nkr.toml"
        previous = path.read_bytes()
        with mock.patch.object(refresh_snapshots.Fetcher, "json", side_effect=OSError("schema connection timed out")):
            outcome = self.refresh()
        self.assertEqual(outcome.status, "failed", outcome.reason)
        self.assertEqual(path.read_bytes(), previous)

    def test_invalid_kept_values_reject_before_writing_with_record_and_field(self):
        self.assertEqual(self.refresh().status, "changed")
        path = self.root / "content/snapshots/nkr.toml"
        previous = path.read_bytes()
        page = self.inputs / "nkr-0.json"
        original = json.loads(page.read_text(encoding="utf-8"))
        for field, value in (
            ("status", "decommissioned"),
            ("status", None),
            ("mainUrl", "http://repo.example.org/"),
            ("mainUrl", "https:///missing-host"),
            ("mainUrl", " https://repo.example.org/"),
            ("mainUrl", " "),
            ("mainUrl", 42),
            ("additionalNames", ["not an object"]),
            ("additionalNames", [{"additionalName": []}]),
            ("additionalNames", [{"lang": "English"}]),
            ("keywordCz", "not an array"),
            ("keywordEn", [False]),
        ):
            with self.subTest(field=field, value=value):
                data = copy.deepcopy(original)
                row = data["results"][0]
                row["content"][field] = value
                page.write_text(json.dumps(data), encoding="utf-8")
                outcome = self.refresh()
                self.assertEqual(outcome.status, "rejected", outcome.reason)
                self.assertIn(row["id"], outcome.reason)
                self.assertIn(field, outcome.reason)
                self.assertEqual(path.read_bytes(), previous)

    def test_schema_status_enum_and_reviewed_mapping_are_both_required(self):
        self.assertEqual(self.refresh().status, "changed")
        path = self.root / "content/snapshots/nkr.toml"
        previous = path.read_bytes()
        schema_path = self.inputs / "nkr-schema.json"
        original = json.loads(schema_path.read_text(encoding="utf-8"))
        schema = copy.deepcopy(original)
        schema["properties"]["status"]["enum"].remove("production")
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        outcome = self.refresh()
        self.assertEqual(outcome.status, "rejected", outcome.reason)
        self.assertIn("status", outcome.reason)
        self.assertEqual(path.read_bytes(), previous)
        original["properties"]["status"]["enum"].append("decommissioned")
        schema_path.write_text(json.dumps(original), encoding="utf-8")
        page = self.inputs / "nkr-0.json"
        data = json.loads(page.read_text(encoding="utf-8"))
        row = data["results"][0]
        row["content"]["status"] = "decommissioned"
        page.write_text(json.dumps(data), encoding="utf-8")
        outcome = self.refresh()
        self.assertEqual(outcome.status, "rejected", outcome.reason)
        self.assertIn(row["id"], outcome.reason)
        self.assertIn("status", outcome.reason)
        self.assertEqual(path.read_bytes(), previous)

    def test_changed_schema_cannot_admit_shapes_the_guide_cannot_consume(self):
        self.assertEqual(self.refresh().status, "changed")
        path = self.root / "content/snapshots/nkr.toml"
        previous = path.read_bytes()
        schema_path = self.inputs / "nkr-schema.json"
        original_schema = json.loads(schema_path.read_text(encoding="utf-8"))
        page_path = self.inputs / "nkr-0.json"
        original_page = json.loads(page_path.read_text(encoding="utf-8"))
        for field, definition, value in (
            ("additionalNames", {"type": "string"}, "English name"),
            ("additionalNames", {"type": "array", "items": {"type": "string"}}, ["English name"]),
            (
                "additionalNames",
                {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"additionalName": {"type": "array", "items": {"type": "string"}}},
                    },
                },
                [{"additionalName": ["English name"], "lang": "English"}],
            ),
            ("keywordCz", {"type": "array", "items": {"type": "integer"}}, [42]),
            ("keywordEn", {"type": "string"}, "keyword"),
        ):
            with self.subTest(field=field, definition=definition):
                schema = copy.deepcopy(original_schema)
                schema["properties"][field] = definition
                schema_path.write_text(json.dumps(schema), encoding="utf-8")
                page = copy.deepcopy(original_page)
                for row in page["results"]:
                    row["content"][field] = value
                page_path.write_text(json.dumps(page), encoding="utf-8")
                outcome = self.refresh()
                self.assertEqual(outcome.status, "rejected", outcome.reason)
                self.assertTrue(any(row["id"] in outcome.reason for row in page["results"]), outcome.reason)
                self.assertIn(field, outcome.reason)
                self.assertEqual(path.read_bytes(), previous)

    def test_address_free_pilot_joins_reviewed_repository_or_resource_handle(self):
        page = self.inputs / "nkr-0.json"
        data = json.loads(page.read_text(encoding="utf-8"))
        row = next(row for row in data["results"] if row["content"]["repositoryName"] == "CzBIRD")
        row["content"]["status"] = "pilot - not accepting data"
        page.write_text(json.dumps(data), encoding="utf-8")
        for filename, header in (("repositories.toml", "[[repository]]"), ("resources.toml", "[[resource]]")):
            with self.subTest(placement=filename):
                target = self.root / "content" / filename
                original = target.read_text(encoding="utf-8") if target.exists() else ""
                nested = "\n[resource.repository]" if filename == "resources.toml" else ""
                target.write_text(
                    original
                    + f'\n{header}\nid = "bird"\nurl = "https://bird.example.org"'
                    + nested
                    + f'\nnkr = "{row["id"]}"\n',
                    encoding="utf-8",
                )
                self.assertEqual(self.refresh().status, "changed")
                target.write_text(original, encoding="utf-8")
                (self.root / "content/snapshots/nkr.toml").unlink()
        self.assertEqual(self.refresh().status, "rejected", "an unjoined pilot still needs its own address")

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

    def test_refresh_omits_relationships_absent_from_the_reviewed_schema(self):
        page = self.inputs / "nkr-0.json"
        data = json.loads(page.read_text(encoding="utf-8"))
        for row in data["results"]:
            row["content"]["relatedRegistry"] = [
                {"relatedRegistryUrl": "https://www.re3data.org/repository/r3d100013576"}
            ]
        page.write_text(json.dumps(data), encoding="utf-8")
        outcome = self.refresh()
        self.assertEqual(outcome.status, "changed", outcome.reason)
        snapshot = tomllib.loads((self.root / outcome.path).read_text(encoding="utf-8"))
        self.assertNotIn("relatedRegistry", snapshot["snapshot"]["fields"])
        self.assertTrue(all("relatedRegistry" not in row for row in snapshot["record"]))
        self.assertTrue(all("re3data" not in row for row in build_crate.nkr_repositories(snapshot)))

    def test_rejected_record_diagnostics_are_bounded_and_literal(self):
        self.assertEqual(self.refresh().status, "changed")
        path = self.root / "content/snapshots/nkr.toml"
        previous = path.read_bytes()
        page = self.inputs / "nkr-0.json"
        data = json.loads(page.read_text(encoding="utf-8"))
        hostile = "\n\x1b[31m<img src=x> [link](https://bad.example)\u0085\u2028\u2029"
        row = data["results"][0]
        row["id"] = hostile + "i" * 500
        row["content"].update(repositoryName=hostile + "n" * 500, mainUrl="http://bad.example/")
        page.write_text(json.dumps(data), encoding="utf-8")
        outcome = self.refresh()
        self.assertEqual(outcome.status, "rejected")
        self.assertNotRegex(outcome.reason, r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")
        self.assertNotIn("<img", outcome.reason)
        self.assertNotIn("[link](", outcome.reason)
        self.assertLess(len(outcome.reason), 900)
        self.assertEqual(path.read_bytes(), previous)


class NkrCatalogueTests(unittest.TestCase):
    def test_nkr_facts_bypass_annotations_and_join_through_the_original_address(self):
        for address, expected_id in (
            ("https://digiarchiv.aiscr.cz/", iri("repositories/amcr")),
            ("https://mbdb-data.org/", iri("repositories/mbdb")),
        ):
            with self.subTest(address=address):
                content = reference_content()
                snapshot = content["snapshots"][-1]
                snapshot["record"] = [row for row in snapshot["record"] if "mbdb" not in row.get("mainUrl", "")]
                record = copy.deepcopy(snapshot["record"][0])
                record.update(
                    id="original-nkr-facts",
                    repositoryName="Original NKR name",
                    additionalNames=[],
                    mainUrl=address,
                    alternateIds=[{"scheme": "nkr", "value": "20.500.14818/original-facts"}],
                    relatedRegistry=[{"relatedRegistryUrl": "https://www.re3data.org/repository/r3d100013576"}],
                )
                snapshot["record"].append(record)
                graph = build_crate.Graph()
                build_crate.build_crate(content, graph)
                entity = graph.entities[expected_id]
                self.assertEqual(
                    entity["name"], build_crate.text({"cs": "Original NKR name", "en": "Original NKR name"})
                )
                self.assertEqual(entity["url"], address)
                self.assertIn(
                    build_crate.ref(build_crate.NKR_OBJECTS + "20.500.14818/original-facts"),
                    build_crate.as_list(entity["sameAs"]),
                )
                self.assertEqual(
                    check_duplicates.check(content, check_duplicates._accepted(build_crate.ROOT)).errors, []
                )

    def test_curated_repository_and_resource_statuses_control_deposits(self):
        for status in ("planned", "in-development", "prospective", "pilot", "operational"):
            with self.subTest(status=status):
                content = build_crate.load_content()
                repository = next(row for row in content["repositories"] if row["id"] == "czech-bioimaging")
                resource = next(row for row in content["resources"] if row["id"] == "datarepo")
                for entry in (repository, resource):
                    entry.update(status=status, asOf="2026-11-05")
                graph = build_crate.Graph()
                build_crate.build_crate(content, graph)
                for entity_id in (iri("repositories/czech-bioimaging"), iri("repositories/datarepo")):
                    expected = False if status in ("planned", "in-development", "prospective") else None
                    self.assertIs(graph.entities[entity_id].get("acceptsDeposits"), expected)

    def test_raw_and_annotated_addresses_join_the_same_repository(self):
        for address in ("https://digiarchiv.aiscr.cz/", "https://amcr-info.aiscr.cz/"):
            with self.subTest(address=address):
                content = reference_content()
                record = copy.deepcopy(content["snapshots"][-1]["record"][0])
                record.update(
                    id="nkr-amcr-test",
                    mainUrl=address,
                    repositoryName="AMCR test",
                    additionalNames=[],
                    alternateIds=[{"scheme": "nkr", "value": "20.500.14818/amcr-test"}],
                )
                content["snapshots"][-1]["record"].append(record)
                graph = build_crate.Graph()
                build_crate.build_crate(content, graph)
                self.assertFalse(iri("repositories/nkr-amcr-test") in graph.entities)
                self.assertEqual(graph.entities[iri("repositories/amcr")]["url"], address)
                self.assertIn(
                    build_crate.ref(build_crate.NKR_OBJECTS + "20.500.14818/amcr-test"),
                    build_crate.as_list(graph.entities[iri("repositories/amcr")]["sameAs"]),
                )
                self.assertEqual(
                    check_duplicates.check(content, check_duplicates._accepted(build_crate.ROOT)).errors, []
                )

    def test_two_nkr_records_at_one_address_are_rejected_without_mixing_facts(self):
        for address in ("https://dual.example.org/", "https://archaeo-vault.cz"):
            with self.subTest(address=address):
                content = reference_content()
                # Keep the reference NKR record out of this component.
                content["snapshots"][-1]["record"] = []
                for slug, status in (("aaa-dual", "pilot - not accepting data"), ("zzz-dual", "production")):
                    content["snapshots"][-1]["record"].append(
                        {
                            "id": slug,
                            "alternateIds": [{"scheme": "nkr", "value": "20.500.14818/" + slug}],
                            "repositoryName": slug,
                            "mainUrl": address,
                            "status": status,
                            "type": "generic",
                        }
                    )
                with self.assertRaises(build_crate.ContentError) as raised:
                    build_crate.build_crate(content)
                self.assertIn("aaa-dual", str(raised.exception))
                self.assertIn("zzz-dual", str(raised.exception))
                errors = check_duplicates.check(content, check_duplicates._accepted(build_crate.ROOT)).errors
                self.assertTrue(any("aaa-dual" in error and "zzz-dual" in error for error in errors), errors)

    def test_curated_handles_are_validated_in_both_placements_when_snapshot_exists(self):
        for placement in ("repositories", "resources"):
            with self.subTest(placement=placement):
                content = reference_content()
                entry = content[placement][0]
                annotation = entry if placement == "repositories" else entry.setdefault("repository", {})
                annotation["nkr"] = "20.500.14818/srhtp4ek"
                report = check_content.Report()
                check_content.check_repositories(
                    report, content, check_content.vocabularies(content), date(2026, 11, 5)
                )
                self.assertFalse(any("NKR" in error for error in report.errors), report.errors)
                annotation["nkr"] = "20.500.14818/TYPO0000"
                report = check_content.Report()
                check_content.check_repositories(
                    report, content, check_content.vocabularies(content), date(2026, 11, 5)
                )
                self.assertTrue(
                    any(entry["id"] in error and annotation["nkr"] in error for error in report.errors), report.errors
                )

    def test_nkr_names_and_classification_override_but_empty_address_keeps_curated_facts(self):
        content = reference_content()
        curated = next(row for row in content["repositories"] if row["id"] == "czech-bioimaging")
        crate = build_crate.build_crate(content)
        entities = {row["@id"]: row for row in crate["@graph"]}
        bird = entities[iri("repositories/czech-bioimaging")]
        self.assertEqual(bird["name"], build_crate.text({"cs": "CzBIRD", "en": "CzBIRD"}))
        self.assertEqual(bird["url"], curated["url"])
        self.assertEqual(
            build_crate.as_list(bird["repositoryFunction"]),
            build_crate.refs([iri("vocabularies/repository-functions/") + value for value in curated["functions"]]),
        )
        self.assertEqual(bird["publisher"], build_crate.ref(iri("organizations/czech-bioimaging")))
        self.assertEqual(bird["serviceStatus"], build_crate.ref(iri("vocabularies/statuses/in-development")))
        self.assertEqual(bird["statusAsOf"], "2026-11-01")
        self.assertEqual(
            entities[iri("repositories/datarepo")]["name"],
            build_crate.text({"cs": "Datový catch-all repozitář", "en": "Data Catch-all Repository"}),
        )
        self.assertEqual(
            entities[iri("repositories/herbarium")]["name"],
            build_crate.text({"cs": "Repozitář herbářových sbírek", "en": "Herbarium Collections Repository"}),
        )

    def test_all_seven_statuses_are_dated_by_retrieval_and_retirement_is_reported(self):
        schema = json.loads((FIXTURE / "nkr-schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(schema["properties"]["status"]["enum"]), set(nkr_contract.NKR_STATUS))
        for native, expected in nkr_contract.NKR_STATUS.items():
            with self.subTest(status=native):
                content = reference_content()
                snapshot = content["snapshots"][-1]
                row = next(row for row in snapshot["record"] if row["repositoryName"] == "CzBIRD")
                row["status"] = native
                graph = build_crate.Graph()
                build_crate.build_crate(content, graph)
                bird = graph.entities[iri("repositories/czech-bioimaging")]
                if expected:
                    self.assertEqual(bird["serviceStatus"], build_crate.ref(iri("vocabularies/statuses/") + expected))
                    self.assertEqual(bird["statusAsOf"], "2026-11-01")
                    self.assertEqual(
                        bird.get("acceptsDeposits"),
                        False
                        if expected in build_crate.NON_DEPOSIT_STATUSES
                        or native == nkr_contract.NKR_PILOT_NOT_ACCEPTING
                        else None,
                    )
                else:
                    self.assertEqual(bird["serviceStatus"], build_crate.ref(iri("vocabularies/statuses/pilot")))
                    self.assertNotIn(build_crate.ref("#snapshot-nkr"), build_crate.as_list(bird["isBasedOn"]))
                    groups = check_health.integrity(content, build_crate.ROOT, date(2026, 11, 2), graph)
                    finding = next(group for group in groups if group["type"] == "NKR maintainer findings")["items"][0]
                    self.assertEqual(finding["id"], "20.500.14818/srhtp4ek")
                    self.assertIn(iri("repositories/czech-bioimaging"), " ".join(finding["notes"]))

    def test_retirement_filters_use_the_shared_mapping(self):
        content = reference_content()
        snapshot = content["snapshots"][-1]
        row = next(row for row in snapshot["record"] if row["repositoryName"] == "CzBIRD")
        row["status"] = "decommissioned"
        with mock.patch.dict(nkr_contract.NKR_STATUS, {"decommissioned": None}):
            graph = build_crate.Graph()
            build_crate.build_crate(content, graph)
            self.assertNotIn(
                build_crate.ref("#snapshot-nkr"),
                build_crate.as_list(graph.entities[iri("repositories/czech-bioimaging")]["isBasedOn"]),
            )
            self.assertFalse(any(entry.name.endswith("srhtp4ek") for entry in check_duplicates.entries(content)))
            self.assertFalse(
                any(record["sourceId"].endswith("srhtp4ek") for record in build_crate.nkr_config([snapshot])["records"])
            )
            groups = check_health.integrity(content, build_crate.ROOT, date(2026, 11, 5), graph)
            self.assertTrue(any(group["type"] == "NKR maintainer findings" for group in groups))

    def test_retirement_reports_raw_and_annotated_addresses_without_overriding_entries(self):
        for address in ("https://digiarchiv.aiscr.cz/", "https://amcr-info.aiscr.cz/"):
            with self.subTest(address=address):
                content = reference_content()
                before = build_crate.Graph()
                build_crate.build_crate(content, before)
                record = copy.deepcopy(content["snapshots"][-1]["record"][0])
                record.update(
                    id="amcr-retired",
                    repositoryName="Retired AMCR",
                    mainUrl=address,
                    status="decomissioned",
                    additionalNames=[],
                    alternateIds=[{"scheme": "nkr", "value": "20.500.14818/amcr-retired"}],
                )
                content["snapshots"][-1]["record"].append(record)
                graph = build_crate.Graph()
                build_crate.build_crate(content, graph)
                self.assertEqual(graph.entities[iri("repositories/amcr")], before.entities[iri("repositories/amcr")])
                self.assertFalse(iri("repositories/amcr-retired") in graph.entities)
                groups = check_health.integrity(content, build_crate.ROOT, date(2026, 11, 5), graph)
                finding = next(
                    item
                    for group in groups
                    if group["type"] == "NKR maintainer findings"
                    for item in group["items"]
                    if item["id"] == "20.500.14818/amcr-retired"
                )
                self.assertIn(iri("repositories/amcr"), " ".join(finding["notes"]))

    def test_retirement_reports_every_address_match(self):
        content = reference_content()
        record = copy.deepcopy(content["snapshots"][-1]["record"][0])
        record.update(
            id="retired-keys",
            repositoryName="Retired keys",
            status="decomissioned",
            additionalNames=[],
            mainUrl="https://digiarchiv.aiscr.cz/",
            alternateIds=[{"scheme": "nkr", "value": "20.500.14818/retired-keys"}],
        )
        content["repositories"].append(
            {"id": "other-amcr", "name": "Other AMCR", "url": record["mainUrl"], "re3data": "r3d999999999"}
        )
        content["snapshots"][-1]["record"].append(record)
        graph = build_crate.Graph()
        build_crate.build_crate(content, graph)
        groups = check_health.integrity(content, build_crate.ROOT, date(2026, 11, 5), graph)
        finding = next(
            item
            for group in groups
            if group["type"] == "NKR maintainer findings"
            for item in group["items"]
            if item["id"] == "20.500.14818/retired-keys"
        )
        for entity_id in (iri("repositories/amcr"), iri("repositories/other-amcr")):
            self.assertIn(entity_id, " ".join(finding["notes"]))

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
        node = URIRef(iri("repositories/czbird"))
        status = URIRef(base + "terms#serviceStatus")
        data.set((node, status, URIRef(iri("vocabularies/statuses/operational"))))
        conforms, _, report = validate(data, shacl_graph=shapes, advanced=True)
        self.assertFalse(conforms)
        self.assertIn("repositories/czbird", report)
        data.set((node, status, URIRef(iri("vocabularies/statuses/in-development"))))
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
        self.assertIn(iri("repositories/herbarium"), entities)
        # A curated repository NKR also lists rests on NKR's record, which rests on the snapshot.
        datarepo = iri("repositories/datarepo")
        self.assertIn(build_crate.ref(datarepo + "#nkr"), entities[datarepo]["isBasedOn"])
        self.assertIn(build_crate.ref("#snapshot-nkr"), build_crate.as_list(entities[datarepo + "#nkr"]["isBasedOn"]))

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
        original = copy.deepcopy(before.entities[iri("repositories/cesnet-invenio")])
        # The FIP Dashboard's own record of the repository it founds.
        dashboard = copy.deepcopy(before.entities[iri("repositories/cesnet-invenio#fip-dashboard")])
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
        self.assertNotIn(iri("repositories/nkr-cesnet"), graph.entities)
        entity = graph.entities[original["@id"]]
        for prop in ("identifier", "repositoryFunction"):
            self.assertEqual(entity[prop], original[prop], prop)
        # The dashboard's record keeps the dashboard's own values; NKR's win on the thing.
        kept = graph.entities[dashboard["@id"]]
        for prop in ("name", "provider", "review", "serviceStatus"):
            self.assertEqual(kept.get(prop), dashboard.get(prop), prop)
        self.assertEqual(kept["primaryTopic"], build_crate.ref(original["@id"]))
        self.assertIn(build_crate.ref("#snapshot-fip-dashboard"), build_crate.as_list(kept["isBasedOn"]))
        self.assertEqual(
            entity["name"], build_crate.text({"cs": record["repositoryName"], "en": record["repositoryName"]})
        )
        self.assertEqual(entity["repositoryKind"], build_crate.ref(iri("vocabularies/repository-kinds/general")))
        self.assertEqual(entity["serviceStatus"], build_crate.ref(iri("vocabularies/statuses/pilot")))
        self.assertEqual(entity["statusAsOf"], "2026-11-01")
        self.assertIs(entity["acceptsDeposits"], False)
        self.assertEqual(
            build_crate.as_list(entity["isBasedOn"]), build_crate.refs([dashboard["@id"], original["@id"] + "#nkr"])
        )
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
        entity = graph.entities[iri("repositories/nusl")]
        self.assertEqual(
            entity["repositoryFunction"],
            build_crate.refs([iri("vocabularies/repository-functions/deposit-publications")]),
        )
        self.assertIn(build_crate.ref(entity["@id"] + "#nkr"), build_crate.as_list(entity["isBasedOn"]))

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
        self.assertIn(iri("repositories/other-cesnet"), ids)
        self.assertIn(iri("repositories/cesnet-invenio"), ids)
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
