"""Build once, execute disjoint CI lanes and reconcile complete, attributable check evidence.

The ordinary local entry remains check_all.py. This adapter shares its job inventory, execution,
health publication and final API validation. No lane publishes a complete site health result.
`quick` runs the cheap offline checks beside the build for early feedback; it is never the complete result.
`adopt` lets a staging deployment reuse a merge-queue run's verified result for the same commit and build inputs.
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
import check_duplicates

ROOT = check_all.ROOT
# Browser jobs by lane, as `ci_timings.py --from tests/fixtures/ci-timings/40022072478-1` packs that run's measured
# jobs into four lanes longest first. Every other job runs in the CPU lane. Change it only through review, from a
# newer run's suggestion; the workflow matrix names the same lanes.
BROWSER_LANES = {
    "browser-a": ("page", "model"),
    "browser-b": ("final-candidate", "runtime", "api", "diagrams", "discovery"),
    "browser-c": ("assessment",),
    "browser-d": ("helpers",),
}
# The unit shards get a runner of their own: beside the three validators on one 4-core runner, two shards made the
# CPU lane the critical path (run 40084136770).
UNIT_LANE = "unit"
LANES = ("cpu", UNIT_LANE, *BROWSER_LANES)
# Cheap offline checks that need no build. The CPU lane runs the same inventory jobs, so the required `checks`
# result reports every failure the quick result does.
QUICK = ("content", "duplicates", "changelog", "ruff", "format", "public-content", "openspec", "agent-generation")


def partition(available):
    """Every non-live job has exactly one owner; health-api belongs to final publication."""
    owners = {job: lane for lane, jobs in BROWSER_LANES.items() for job in jobs} | {"unit": UNIT_LANE}
    result = {lane: [] for lane in LANES}
    for job in available:
        if job.name in {"live", "health-api"}:
            continue
        if job.name in check_all.BROWSER_JOBS and job.name not in owners:
            raise ValueError(f"{job.name}: browser job without a lane in check_ci.BROWSER_LANES")
        result[owners.get(job.name, "cpu")].append(job)
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


def cache_status(env) -> dict:
    """The setup actions' `cache-hit` outputs; a lane without a cache for a tool records that it used none."""
    labels = {"true": "hit", "false": "miss"}
    return {tool: labels.get(env.get(f"CHECK_CACHE_{tool.upper()}", ""), "not used") for tool in ("pip", "npm")}


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
                "caches": cache_status(os.environ),
            },
        },
    )
    return 1 if any(not result.ok or result.partial for result in results) else 0


def quick_summary(results) -> str:
    failed = [result.job.name for result in results if not result.ok]
    lines = [
        "## Quick checks",
        "",
        "Cheap offline checks for early feedback. They do not replace the required `checks` result, which runs "
        "them again with every other check.",
        "",
        "| Check | Result | Seconds |",
        "| --- | --- | ---: |",
        *(
            f"| {result.job.name} | {'passed' if result.ok else 'failed'} | {result.seconds:.2f} |"
            for result in results
        ),
    ]
    for result in results:
        if not result.ok:
            lines += ["", f"### {result.job.name}", "", "```text", bounded_failure(result.output), "```"]
    if failed:
        command = "python scripts/check_all.py --only " + " ".join(failed)
        lines += [
            "",
            f"- **Next:** the pull request author fixes {', '.join(failed)} and reproduces it with `{command}`.",
            "- **If blocked:** the complete log is in this job's step output; the required `checks` result reports "
            "the same failures with the full health report.",
            f"- **Done when:** `{command}` passes locally and this job and `checks` pass on the next push.",
        ]
    else:
        lines += [
            "",
            "- **Next:** wait for the required `checks` result, which also runs the build, unit tests, validators "
            "and browser checks.",
            "- **If blocked:** `python scripts/check_all.py` reproduces the complete run locally.",
            "- **Done when:** `checks` passes.",
        ]
    return "\n".join(lines) + "\n"


def quick(args) -> int:
    selected = [job for job in check_all.jobs(args.base, False) if job.name in QUICK]
    results = check_all.run_all(selected, args.jobs, check_all.environment())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.md").write_text(quick_summary(results), encoding="utf-8", newline="\n")
    for result in results:
        if not result.ok:
            print(f"FAILED {result.job.name}:\n{bounded_failure(result.output)}")
    return 0 if all(result.ok for result in results) else 1


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


FAILURE_TAIL_LINES = 40
FAILURE_TAIL_CHARS = 4000
SUGGESTION_LIMIT = 20


def bounded_failure(text: str) -> str:
    value = check_all.tail(text, FAILURE_TAIL_LINES)
    return value[-FAILURE_TAIL_CHARS:] if len(value) > FAILURE_TAIL_CHARS else value


def copy_lane_diagnostics(incoming: Path, output: Path) -> None:
    """Keep lane logs and details even when the aggregate rejects the run."""
    if not incoming.is_dir():
        return
    for directory in sorted(path for path in incoming.iterdir() if path.is_dir()):
        for child in ("details", "logs", "coverage"):
            if (directory / child).is_dir():
                shutil.copytree(directory / child, output / child, dirs_exist_ok=True)


def load_suggestions(incoming: Path | None, head: str, *, checked_revision: str = "") -> dict:
    """Read the bounded, validated suggestion artifact from the duplicate check."""
    suggestions = []
    for path in [incoming / "details/duplicates.json"] if incoming is not None else []:
        if not path.is_file():
            continue
        try:
            data = read_json(path)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or data.get("formatVersion") != 1:
            continue
        items = data.get("suggestions")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or item.get("safe") is not True:
                continue
            if item.get("resolution") not in (None, "link"):
                continue
            if not check_duplicates.valid_placement(
                item.get("entry"), item.get("file"), item.get("table"), item.get("field")
            ):
                continue
            required = ("entry", "record", "value", "reason")
            if not all(isinstance(item.get(key), str) and item.get(key) for key in required):
                continue
            if len(item["value"]) > 128 or len(item["reason"]) > 400:
                continue
            suggestions.append(
                {
                    "entry": item["entry"],
                    "record": item["record"],
                    "resolution": "link",
                    "safe": True,
                    "file": item["file"],
                    "table": item.get("table", ""),
                    "field": item["field"],
                    "value": item["value"],
                    "reason": item["reason"],
                }
            )
            if len(suggestions) >= SUGGESTION_LIMIT:
                break
    return {
        "formatVersion": 1,
        "head": head,
        "checkedRevision": checked_revision or head,
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "suggestions": suggestions,
    }


def collect_suggestions(incoming: Path | None, manifest: dict) -> dict:
    revision = str(manifest.get("source", {}).get("revision", ""))
    return load_suggestions(incoming, os.environ.get("PR_HEAD_SHA") or revision, checked_revision=revision)


def write_suggestions(output: Path, payload: dict) -> Path:
    target = output.parent / "pr-review" / "suggestions.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def summary_value(value: str) -> str:
    return value.replace("`", "'").replace("\n", " ")[:400]


def append_suggestion_summary(output: Path, payload: dict) -> None:
    summary = output / "summary.md"
    suggestions = payload.get("suggestions", [])
    if not summary.is_file() or not suggestions:
        return
    lines = ["", "### Suggested fixes", ""]
    for item in suggestions:
        table = f" [{summary_value(item['table'])}]" if item.get("table") else ""
        lines.append(
            f"- `{summary_value(item['entry'])}` ← `{summary_value(item['record'])}`: "
            f'add `{summary_value(item["field"])} = "{summary_value(item["value"])}"` to '
            f"`{summary_value(item['file'])}`{table} (`{summary_value(item['reason'])}`)"
        )
    summary.write_text(
        summary.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(lines).rstrip() + "\n", encoding="utf-8"
    )


class RejectedEvidenceError(ValueError):
    """Required evidence is missing or invalid; `results` keeps what the verified lanes reported."""

    def __init__(self, problems: list[str], results: list) -> None:
        super().__init__("; ".join(problems))
        self.results = results


def admitted_results(path: Path, manifest: dict, owners: dict, found: dict) -> tuple[str, dict, list]:
    """Read one lane, refusing it unless its identity and job inventory match; a refused lane yields nothing."""
    data = read_json(path)
    name = data["lane"]
    if name not in owners or name in found:
        raise ValueError("unknown or duplicated lane")
    if data["source"] != manifest["source"] or data["build"] != manifest["build"]:
        raise ValueError("lane has the wrong source revision or build identity")
    expected = {job.name: job for job in owners[name]}
    if Counter(row["name"] for row in data["results"]) != Counter(expected.keys()):
        raise ValueError(f"{name}: missing or duplicated jobs")
    results = []
    for row in data["results"]:
        job = expected[row["name"]]
        result = check_all.Result(job, row["returncode"], row["seconds"], row["output"], row["partial"])
        if result.partial:
            output = result.output
            if output and not output.endswith("\n"):
                output += "\n"
            result = check_all.Result(
                job,
                result.returncode or 1,
                result.seconds,
                output + "Incomplete required check coverage (partial result).",
                True,
            )
        results.append(result)
    return name, data, results


def reconcile(manifest, incoming: Path, available, groups):
    """Validate evidence before publishing; do not infer completeness from equal totals.

    Lanes are judged one by one, so a missing or invalid lane cannot hide failures a verified lane reported.
    """
    owners = partition(available)
    found = {}
    results = []
    failures = []
    directories = {}
    problems = []
    for path in sorted(incoming.glob("*/lane.json")):
        try:
            name, data, lane_results = admitted_results(path, manifest, owners, found)
        except (OSError, ValueError, KeyError, TypeError) as error:
            problems.append(f"{path.parent.name}: {error}")
            continue
        found[name] = data
        directories[name] = path.parent
        for reported in lane_results:
            result = reported
            if reported.ok:
                try:
                    validate_scripts(reported.job, path.parent, groups, manifest)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    problems.append(f"{reported.job.name}: {error}")
                    result = check_all.Result(
                        reported.job, 1, reported.seconds, f"{reported.output}\nRejected evidence: {error}"
                    )
            results.append(result)
            if not result.ok:
                failures.append(result)
    if set(found) != set(LANES):
        problems.append("missing required lanes: " + ", ".join(sorted(set(LANES) - set(found))))
    if problems:
        raise RejectedEvidenceError(problems, results)
    if failures:
        # A failed lane may not have produced final coverage; the failure already prevents a complete pass.
        return results, found, directories, failures
    final_lane = next(name for name, jobs in owners.items() if any(job.name == "final-candidate" for job in jobs))
    try:
        for filename, key in (("station-coverage.json", "stations"), ("print-coverage.json", "pdfs")):
            coverage = read_json(directories[final_lane] / "coverage" / filename)
            if Counter(coverage["planned"]) != Counter(manifest["coverage"][key]) or coverage.get("skipped"):
                raise ValueError(f"{filename}: required inventory differs")
            complete_cases(manifest["coverage"][key], coverage["executed"], "key")
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RejectedEvidenceError([str(error)], results) from error
    return results, found, directories, []


def publish_suggestions(output: Path, manifest: dict, directories: dict, available) -> None:
    """Optional data never replaces a required report or rescues rejected evidence."""
    target = output.parent / "pr-review/suggestions.json"
    try:
        target.unlink(missing_ok=True)
        lane = next(
            (name for name, jobs in partition(available).items() if any(job.name == "duplicates" for job in jobs)), None
        )
        # Only the expected owner's directory, admitted by reconcile, may supply data.
        directory = directories.get(lane)
        payload = collect_suggestions(directory, manifest)
        write_suggestions(output, payload)
        append_suggestion_summary(output, payload)
        # A stale file can survive a failed invalidation. Upload only the path successfully
        # produced by this invocation, never an unconditional filename in the workflow.
        if step_output := os.environ.get("GITHUB_OUTPUT"):
            with Path(step_output).open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(f"suggestions_path={target.as_posix()}\n")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"WARNING: optional duplicate suggestions unavailable: {bounded_failure(str(error))}")


def collect(args) -> int:
    started = time.monotonic()
    available = [*check_all.jobs(args.base, True), check_all.health_api_job()]
    selected = [job for job in available if job.name != "live"]
    initial = check_all.Result(check_all.Job("build", []), 1, 0, "Build or lane evidence unavailable")
    manifest = {}
    try:
        manifest = read_json(args.manifest)
        verify_build(manifest, ROOT)
        row = manifest["result"]
        initial = check_all.Result(initial.job, row["returncode"], row["seconds"], row["output"])
        results, lanes, directories, failures = reconcile(
            manifest, args.incoming, available, read_json(ROOT / "scripts/check_groups.json")
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        copy_lane_diagnostics(args.incoming, args.output)
        # Results of verified lanes stay attributable beside the evidence problem; neither makes a pass.
        known = error.results if isinstance(error, RejectedEvidenceError) else []
        failed = check_all.Result(check_all.Job("aggregate", []), 1, 0, f"Aggregate rejected: {error}")
        check_all.emit_report(
            initial,
            [*known, failed],
            [*available, failed.job],
            [*selected, failed.job],
            output=args.output,
            previous=None,
        )
        publish_suggestions(args.output, manifest, {}, available)
        for result in known:
            if not result.ok:
                print(f"FAILED {result.job.name}:\n{bounded_failure(result.output)}")
        print(failed.output)
        return 1
    copy_lane_diagnostics(args.incoming, args.output)
    if failures:
        check_all.emit_report(initial, results, available, selected, output=args.output, previous=None)
        publish_suggestions(args.output, manifest, directories, available)
        for result in failures:
            print(f"FAILED {result.job.name}:\n{bounded_failure(result.output)}")
        return 1
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
    publish_suggestions(args.output, manifest, directories, available)
    metadata["elapsed_seconds"] = time.time() - manifest["started"]
    write_json(args.output / "execution.json", metadata)
    return status


def adoption_problems(manifest: dict, execution: dict, report: dict) -> list[str]:
    """Why a merge-queue result cannot stand for this checkout's fresh build; empty when it can."""
    problems = []
    if execution.get("profile") != "ci-partitioned":
        problems.append("it is not a partitioned check result")
    if execution.get("source") != manifest["source"]:
        problems.append("its source revision or files differ from this commit")
    if execution.get("build_inputs") != manifest["build"]:
        problems.append("its build inputs differ from this build, for example because it was built on another day")
    if report.get("format_version") != check_all.check_health.FORMAT_VERSION:
        problems.append(f"its health snapshot has format {report.get('format_version')!r}")
    if report.get("run", {}).get("status") != "passed" or not report.get("generated_at"):
        problems.append("its check run did not pass")
    if report.get("revision") != manifest["source"]["revision"]:
        problems.append("its health snapshot names another commit")
    if report.get("build") != check_all.check_health.build_crate.build_identity_facts():
        problems.append("its health snapshot names another build identity")
    return problems


def adopt(args) -> int:
    """Publish a passing merge-queue result's health snapshot into this checkout's fresh build, or say why the full
    checks run instead. Exits 1 whenever the result is not reused."""
    source = args.source or "the merge-queue result"
    try:
        manifest = read_json(args.manifest)
        verify_build(manifest, ROOT)
        execution = read_json(args.incoming / "execution.json")
        report = read_json(args.incoming / "health.json")
        problems = adoption_problems(manifest, execution, report)
    except (OSError, ValueError, KeyError, TypeError) as error:
        problems = [f"its evidence is unavailable or unreadable ({bounded_failure(str(error))})"]
    if problems:
        print(f"Full checks: {source} cannot be reused, because " + "; ".join(problems) + ".")
        return 1
    context = check_all.PublicationContext.load()
    if context.error is not None:
        print(f"Full checks: the content could not be read to publish {source}: {context.error}")
        return 1
    check_all.build_api.publish_health(ROOT / "_site", report, context.content, crate=context.crate)
    validation = check_all.run(check_all.health_api_job(), check_all.environment())
    if not validation.ok:
        failure = bounded_failure(validation.output)
        print(f"Full checks: the health snapshot of {source} fails the health API:\n{failure}")
        return 1
    print(
        f"Reused {source}: the same commit, source files and build inputs passed every check there, and its health "
        "snapshot is published in this staging site."
    )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("build", "lane", "collect", "quick", "adopt"))
    parser.add_argument("--name", choices=LANES)
    parser.add_argument("--base")
    parser.add_argument("--manifest", type=Path, default=ROOT / ".cache/ci-build/manifest.json")
    parser.add_argument("--output", type=Path, help="report directory (default: .cache/health; quick: .cache/quick)")
    parser.add_argument("--incoming", type=Path, default=ROOT / ".cache/ci-results")
    parser.add_argument("--source", help="adopt: the merge-queue run whose result is offered, named in the output")
    # Lanes use the same budget owner as local runs, scripts/check_policy.json; CI=true selects its CI profile.
    check_all.add_budget_arguments(parser)
    args = parser.parse_args(argv)
    if args.jobs < 1 or args.browser_workers < 1 or (args.action == "lane" and not args.name):
        parser.error("positive budgets and --name for lane are required")
    args.base = args.base or check_all.check_content.default_base(ROOT)
    args.output = args.output or ROOT / (".cache/quick" if args.action == "quick" else ".cache/health")
    return {"build": build, "lane": lane, "collect": collect, "quick": quick, "adopt": adopt}[args.action](args)


if __name__ == "__main__":
    sys.exit(main())
