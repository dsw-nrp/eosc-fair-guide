"""Build once, execute disjoint CI lanes and reconcile complete, attributable check evidence.

The ordinary local entry remains check_all.py. This adapter shares its job inventory, execution,
health publication and final API validation. No lane publishes a complete site health result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

import check_all

ROOT = check_all.ROOT
LANES = ("cpu", "browser-a", "browser-b")
# The two substantial partitions balance the observed hosted groups, without duplicating command lists.
BROWSER_A = {"page", "assessment", "discovery"}


def partition(available):
    """Every non-live job has exactly one owner; health-api belongs to final publication."""
    result = {lane: [] for lane in LANES}
    for job in available:
        if job.name in {"live", "health-api"}:
            continue
        lane = "browser-a" if job.name in BROWSER_A else "browser-b" if job.name in check_all.BROWSER_JOBS else "cpu"
        result[lane].append(job)
    return result


def digest_files(root: Path, paths) -> dict:
    return {str(path): hashlib.sha256((root / path).read_bytes()).hexdigest() for path in sorted(paths)}


def source_identity(root: Path) -> dict:
    tracked = (
        subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root)
        .decode("utf-8")
        .split("\0")
    )
    return {
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "files": digest_files(root, {name for name in tracked if name and (root / name).is_file()}),
    }


def build_identity(root: Path) -> dict:
    site = root / "_site"
    return digest_files(site, [path.relative_to(site).as_posix() for path in site.rglob("*") if path.is_file()])


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def verify_build(manifest: dict, root: Path) -> None:
    if manifest["source"] != source_identity(root):
        raise ValueError("checked source revision/files differ from the verified build")
    if manifest["build"] != build_identity(root):
        raise ValueError("site files differ from the verified build")


def record(result) -> dict:
    return {
        "name": result.job.name,
        "returncode": result.returncode,
        "seconds": result.seconds,
        "output": result.output,
        "partial": result.partial,
    }


def coverage_inventory(root: Path) -> dict:
    script = """import {readFileSync} from 'node:fs';
import {stationMatrix} from './tests/page/station_matrix.mjs';
import {printMatrix} from './tests/page/print_matrix.mjs';
import {browserSourceDigest} from './scripts/browser_env.mjs';
const graph=JSON.parse(readFileSync('_site/ro-crate-metadata.json','utf8'))['@graph'];
console.log(JSON.stringify({stations:stationMatrix(graph).map(x=>x.key),pdfs:printMatrix(graph).map(x=>x.key),browser_source_digest:browserSourceDigest()}));"""
    return json.loads(subprocess.check_output(["node", "--input-type=module", "-e", script], cwd=root, text=True))


def build(args) -> int:
    started = time.time()
    result = check_all.run(check_all.Job("build", [sys.executable, "scripts/build_site.py"]), check_all.environment())
    if not result.ok:
        check_all.emit_report(result, [], check_all.jobs(args.base, True), [], output=args.output, previous=None)
        print(result.output)
        return 1
    manifest = {
        "source": source_identity(ROOT),
        "build": build_identity(ROOT),
        "result": record(result),
        "coverage": coverage_inventory(ROOT),
        "started": started,
        "finished": time.time(),
    }
    write_json(args.manifest, manifest)
    print(f"Verified build: {manifest['source']['revision']}, {len(manifest['build'])} files")
    return 0


def lane(args) -> int:
    started = time.time()
    manifest = read_json(args.manifest)
    verify_build(manifest, ROOT)
    available = [*check_all.jobs(args.base, True), check_all.health_api_job()]
    selected = partition(available)[args.name]
    env = check_all.environment()
    env.update(
        CHECK_REPORT_DIR=str((args.output / "details").resolve()),
        CHECK_BROWSER_WORKERS=str(args.browser_workers),
        CHECK_BROWSER_SLOT_DIR=str((args.output / "details" / f"budget-{uuid.uuid4().hex}").resolve()),
    )
    results = check_all.run_all(selected, args.jobs, env)
    build_result = manifest["result"]
    initial = check_all.Result(
        check_all.Job("build", []), build_result["returncode"], build_result["seconds"], build_result["output"]
    )
    check_all.emit_report(initial, results, available, selected, output=args.output, previous=None)
    if any(job.name == "final-candidate" for job in selected):
        for name in ("station-coverage.json", "print-coverage.json"):
            path = ROOT / ".cache/screenshots/final" / name
            if path.is_file():
                target = args.output / "coverage" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    write_json(
        args.output / "lane.json",
        {
            "lane": args.name,
            "source": manifest["source"],
            "build": manifest["build"],
            "started": started,
            "finished": time.time(),
            "results": [record(result) for result in results],
            "execution": {
                "jobs": args.jobs,
                "browser_workers": args.browser_workers,
                "cpus": os.cpu_count(),
                "python": sys.version,
                "platform": sys.platform,
            },
        },
    )
    return 1 if any(not result.ok or result.partial for result in results) else 0


def complete_cases(planned, executed, key="name") -> None:
    wanted = Counter(planned)
    seen = Counter(item[key] for item in executed)
    if (
        any(count != 1 for count in wanted.values())
        or wanted != seen
        or any(item["status"] != "passed" for item in executed)
    ):
        raise ValueError("missing, duplicate, incomplete or failed case coverage")


def validate_scripts(job, directory: Path, groups: dict, manifest: dict) -> None:
    if job.name not in check_all.BROWSER_JOBS or job.name == "runtime":
        return
    group = "final" if job.name == "final-candidate" else job.name
    report = read_json(directory / "details" / group / "scripts.json")
    expected = [
        "tests/api/check_api.mjs" if name.startswith("../") else f"tests/page/check_{name}.mjs"
        for name in groups[group]
    ]
    scripts = report["scripts"]
    if report["status"] != "passed" or Counter(item["file"] for item in scripts) != Counter(expected):
        raise ValueError(f"{job.name}: script inventory is missing, duplicated or partial")
    for script in scripts:
        if script["status"] != "passed" or script["returncode"] != 0:
            raise ValueError(f"{job.name}: a script did not pass")
        cases = script.get("cases")
        if not cases or cases["status"] != "passed" or cases.get("skipped") or cases.get("pending"):
            raise ValueError(f"{script['file']}: missing or incomplete case report")
        if (
            cases["revision"] != manifest["source"]["revision"]
            or cases["source_digest"] != manifest["coverage"]["browser_source_digest"]
        ):
            raise ValueError(f"{script['file']}: case evidence has the wrong revision/source digest")
        complete_cases(cases["planned"], cases["executed"])


def reconcile(manifest, incoming: Path, available, groups):
    """Validate evidence before publishing; do not infer completeness from equal totals."""
    owners = partition(available)
    found = {}
    results = []
    directories = {}
    for path in sorted(incoming.glob("*/lane.json")):
        data = read_json(path)
        name = data["lane"]
        if name not in owners or name in found:
            raise ValueError("unknown or duplicated lane")
        if data["source"] != manifest["source"] or data["build"] != manifest["build"]:
            raise ValueError("lane has the wrong source revision or build identity")
        expected = {job.name: job for job in owners[name]}
        if Counter(row["name"] for row in data["results"]) != Counter(expected.keys()):
            raise ValueError(f"{name}: missing or duplicated jobs")
        for row in data["results"]:
            job = expected[row["name"]]
            if row["returncode"] != 0 or row["partial"]:
                raise ValueError(f"{job.name}: failed or partial result")
            validate_scripts(job, path.parent, groups, manifest)
            results.append(check_all.Result(job, row["returncode"], row["seconds"], row["output"], row["partial"]))
        found[name] = data
        directories[name] = path.parent
    if set(found) != set(LANES):
        raise ValueError("missing required lanes: " + ", ".join(sorted(set(LANES) - set(found))))
    final_lane = next(name for name, jobs in owners.items() if any(job.name == "final-candidate" for job in jobs))
    for filename, key in (("station-coverage.json", "stations"), ("print-coverage.json", "pdfs")):
        coverage = read_json(directories[final_lane] / "coverage" / filename)
        if Counter(coverage["planned"]) != Counter(manifest["coverage"][key]) or coverage.get("skipped"):
            raise ValueError(f"{filename}: required inventory differs")
        complete_cases(manifest["coverage"][key], coverage["executed"], "key")
    return results, found, directories


def collect(args) -> int:
    started = time.monotonic()
    available = [*check_all.jobs(args.base, True), check_all.health_api_job()]
    selected = [job for job in available if job.name != "live"]
    initial = check_all.Result(check_all.Job("build", []), 1, 0, "Build or lane evidence unavailable")
    try:
        manifest = read_json(args.manifest)
        verify_build(manifest, ROOT)
        row = manifest["result"]
        initial = check_all.Result(initial.job, row["returncode"], row["seconds"], row["output"])
        results, lanes, directories = reconcile(
            manifest, args.incoming, available, read_json(ROOT / "scripts/check_groups.json")
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        failed = check_all.Result(check_all.Job("aggregate", []), 1, 0, f"Aggregate rejected: {error}")
        check_all.emit_report(
            initial, [failed], [*available, failed.job], [*selected, failed.job], output=args.output, previous=None
        )
        print(failed.output)
        return 1
    for directory in directories.values():
        for child in ("details", "logs", "coverage"):
            if (directory / child).is_dir():
                shutil.copytree(directory / child, args.output / child, dirs_exist_ok=True)
    # The collector can run on another machine; map the build's UTC start onto this process's
    # monotonic clock so the shared summary reports the whole run, not just publication.
    suite_started = started - (time.time() - manifest["started"])
    metadata = {
        "profile": "ci-partitioned",
        "source": manifest["source"],
        "build_inputs": manifest["build"],
        "lanes": lanes,
        "elapsed_seconds": time.time() - manifest["started"],
        "lane_seconds": sum(data["finished"] - data["started"] for data in lanes.values()),
        "cost_scope": "Lane check time; hosted job setup/artifact minutes require Actions job timings.",
    }
    write_json(args.output / "execution.json", metadata)
    env = check_all.environment()
    env["CHECK_REPORT_DIR"] = str((args.output / "details").resolve())
    env["FAIR_GUIDE_CHECK_REVISION"] = manifest["source"]["revision"]
    # Health generation reads the checked revision from the process environment.
    os.environ["FAIR_GUIDE_CHECK_REVISION"] = manifest["source"]["revision"]
    status = check_all.publish_results(
        initial, results, available, selected, env=env, output=args.output, previous=None, start=suite_started
    )
    metadata["elapsed_seconds"] = time.time() - manifest["started"]
    write_json(args.output / "execution.json", metadata)
    return status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("build", "lane", "collect"))
    parser.add_argument("--name", choices=LANES)
    parser.add_argument("--base")
    parser.add_argument("--manifest", type=Path, default=ROOT / ".cache/ci-build/manifest.json")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/health")
    parser.add_argument("--incoming", type=Path, default=ROOT / ".cache/ci-results")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--browser-workers", type=int, default=2)
    args = parser.parse_args(argv)
    if args.jobs < 1 or args.browser_workers < 1 or (args.action == "lane" and not args.name):
        parser.error("positive budgets and --name for lane are required")
    args.base = args.base or check_all.check_content.default_base(ROOT)
    return {"build": build, "lane": lane, "collect": collect}[args.action](args)


if __name__ == "__main__":
    sys.exit(main())
