#!/usr/bin/env python3
"""Report where a checks run spent its time and suggest balanced browser lanes from its own evidence.

    python scripts/ci_timings.py RUN_ID [--attempt N] [--repo OWNER/NAME] [--browser-lanes N ...] [--json PATH]
    python scripts/ci_timings.py --from DIRECTORY [--browser-lanes N ...] [--json PATH] [--unit-weights PATH]

RUN_ID reads one attempt of a "Guide checks and health report" run through the GitHub CLI (``gh``): its job and
step timings and its ``health-<run>-<attempt>`` artifact. Both are kept under ``.cache/ci-timings/<run>-<attempt>/``,
so ``--from`` repeats the report offline. A rerun removes the earlier attempts' artifacts, so read each attempt
before starting the next. Each job is split into queue (created to started), setup (job set-up,
checkout, toolchains, caches, installs and downloads), active check time and teardown (uploads and post steps).
The report names the critical path through the job graph, the elapsed and summed job time, the concurrent-job
peak, the time cases and scripts waited for a browser slot, the unit-test timings and the coverage the run proves.

The suggestion packs the measured browser jobs into lanes longest first. A lane is predicted as the longer of its
longest job and its browser work divided by its slots; the current assignment is predicted the same way beside its
measured time, so the model can be judged. The suggestion is advice: the assignment in ``check_ci.py`` changes only
through review, and a speed claim needs paired reruns at a fixed commit with unchanged coverage. In the same way,
``--unit-weights`` writes the measured unit-test module seconds for review into ``scripts/unit_shards.json``, from
which ``profile_checks.py`` packs its shards.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "ci-timings"
DEFAULT_REPO = "{owner}/{repo}"
SETUP = re.compile(
    r"^(Set up job$|Run actions/(checkout|setup-python|setup-node|cache|download-artifact)@|Run npm ci$|Install\b)"
)
TEARDOWN = re.compile(r"^(Post |Complete job$|Save\b|Share\b|Run actions/upload-artifact@)")
VALIDATORS = ("crate", "process-run", "profile")


def moment(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def span(start: str | None, end: str | None) -> float:
    return max(0.0, (moment(end) - moment(start)).total_seconds()) if start and end else 0.0


def phases(job: dict) -> dict:
    """Queue, setup, active and teardown seconds of one job, classified from its step names."""
    totals = {"setup": 0.0, "active": 0.0, "teardown": 0.0}
    for step in job.get("steps") or []:
        kind = "setup" if SETUP.match(step["name"]) else "teardown" if TEARDOWN.match(step["name"]) else "active"
        totals[kind] += span(step.get("started_at"), step.get("completed_at"))
    return {
        "name": job["name"],
        "conclusion": job.get("conclusion"),
        "created": job["created_at"],
        "started": job["started_at"],
        "completed": job["completed_at"],
        "queue": span(job["created_at"], job["started_at"]),
        "duration": span(job["started_at"], job["completed_at"]),
        **totals,
    }


def critical_path(jobs: list[dict]) -> list[dict]:
    """From the last job to finish, walk back through the job that finished last before each one was created."""
    path = [max(jobs, key=lambda job: moment(job["completed"]))]
    while True:
        created = moment(path[-1]["created"])
        before = [job for job in jobs if job not in path and moment(job["completed"]) <= created]
        if not before:
            return path[::-1]
        path.append(max(before, key=lambda job: moment(job["completed"])))


def concurrency_peak(jobs: list[dict]) -> int:
    # A job that ends at the second another starts did not overlap it.
    events = sorted([(moment(job["started"]), 1) for job in jobs] + [(moment(job["completed"]), -1) for job in jobs])
    active = peak = 0
    for _, delta in events:
        active += delta
        peak = max(peak, active)
    return peak


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def group_of(job: str) -> str:
    return "final" if job == "final-candidate" else job


def script_waits(script: dict) -> tuple[float, list[dict]]:
    """The script-level wait and each timed case's wait; earlier evidence without a field reads as no wait."""
    cases = script.get("cases") or {}
    timed = [case for case in cases.get("executed") or [] if "seconds" in case]
    return float((cases.get("script") or {}).get("queue_seconds", 0)), timed


def browser_estimate(name: str, seconds: float, scripts: list[dict] | None, workers: int) -> dict:
    """Uncontended time of one browser job: its scripts run in turn, and one script's cases share the lane's slots.

    `work` is the slot time the job needs. A job without script evidence (the Node runtime tests) holds no slot.
    """
    if scripts is None:
        return {"name": name, "estimate": seconds, "work": 0.0}
    estimate = work = 0.0
    for script in scripts:
        waited, timed = script_waits(script)
        if timed:
            active = [max(0.0, case["seconds"] - case.get("queue_seconds", 0)) for case in timed]
            estimate += max(*active, sum(active) / workers)
            work += sum(active)
        else:
            own = max(0.0, script["seconds"] - waited)
            estimate += own
            work += own
    return {"name": name, "estimate": estimate, "work": work}


def predict(estimates: list[dict], workers: int) -> float:
    if not estimates:
        return 0.0
    return max(*(item["estimate"] for item in estimates), sum(item["work"] for item in estimates) / workers)


def suggest(estimates: list[dict], count: int, workers: int) -> list[dict]:
    """Longest-first packing into the lane whose predicted time grows least; ties keep the earlier lane."""
    lanes: list[list[dict]] = [[] for _ in range(count)]
    for item in sorted(estimates, key=lambda item: (-item["estimate"], item["name"])):
        target = min(range(count), key=lambda index: (predict([*lanes[index], item], workers), index))
        lanes[target].append(item)
    return [{"jobs": [item["name"] for item in lane], "predicted": predict(lane, workers)} for lane in lanes]


def evidence(directory: Path) -> dict:
    """Lanes, browser scripts, unit timings and coverage from the run's health artifact, as far as it exists."""
    health = directory / "health"
    execution = read_json(health / "execution.json") or {}
    lanes = execution.get("lanes") or {}
    scripts = {
        path.parent.name: (read_json(path) or {}).get("scripts") or []
        for path in sorted((health / "details").glob("*/scripts.json"))
    }
    unit = read_json(health / "details" / "unit-timings.json")
    report = read_json(health / "health.json") or {}
    return {"lanes": lanes, "scripts": scripts, "unit": unit, "run": report.get("run")}


def lane_report(found: dict, browser_lanes: list[int]) -> dict:
    lanes, scripts = found["lanes"], found["scripts"]
    if not lanes:
        return {"available": False, "reason": "the health artifact has no lane record (the collector rejected it)"}
    measured, waits, browser = {}, [], []
    for name, data in sorted(lanes.items()):
        workers = int(data["execution"]["browser_workers"])
        jobs = [row["name"] for row in data["results"]]
        estimates = []
        for row in data["results"]:
            group = group_of(row["name"])
            if group in scripts:
                for script in scripts[group]:
                    waited, timed = script_waits(script)
                    if waited:
                        waits.append({"lane": name, "job": row["name"], "name": script["file"], "seconds": waited})
                    waits.extend(
                        {"lane": name, "job": row["name"], "name": case["name"], "seconds": case["queue_seconds"]}
                        for case in timed
                        if case.get("queue_seconds")
                    )
            if group in scripts or row["name"] == "runtime":
                estimates.append(browser_estimate(row["name"], row["seconds"], scripts.get(group), workers))
        browser.extend(estimates)
        measured[name] = {
            "seconds": data["finished"] - data["started"],
            "jobs": jobs,
            "browser_workers": workers,
            "predicted": predict(estimates, workers) if estimates else None,
            "slot_waits": sum(item["seconds"] for item in waits if item["lane"] == name),
            # Lanes record their dependency-cache hits from the setup actions; older evidence has none.
            "caches": data["execution"].get("caches"),
        }
    workers = max((lane["browser_workers"] for lane in measured.values()), default=1)
    return {
        "available": True,
        "lanes": measured,
        "waits": sorted(waits, key=lambda item: (-item["seconds"], item["name"])),
        "browser_jobs": sorted(browser, key=lambda item: (-item["estimate"], item["name"])),
        "suggestions": {str(count): suggest(browser, count, workers) for count in browser_lanes},
    }


def unit_report(unit: dict | None) -> dict:
    if not unit:
        return {"available": False}
    tests = unit["tests"]
    classes: dict[str, float] = {}
    modules: dict[str, float] = {}
    for test in tests:
        module, name = test["test"].split(".")[:2]
        classes[f"{module}.{name}"] = classes.get(f"{module}.{name}", 0.0) + test["seconds"]
        modules[module] = modules.get(module, 0.0) + test["seconds"]
    return {
        "available": True,
        "tests": len(tests),
        "seconds": sum(test["seconds"] for test in tests),
        "successful": unit.get("successful"),
        "slowest": sorted(tests, key=lambda test: -test["seconds"])[:5],
        "classes": sorted(({"name": k, "seconds": v} for k, v in classes.items()), key=lambda c: -c["seconds"])[:5],
        "modules": dict(sorted(modules.items())),
    }


def unit_weights(report: dict) -> dict:
    """Measured module seconds for scripts/unit_shards.json, which profile_checks.py packs shards from."""
    run = report["run"]
    measured = f"run {run['id']} attempt {run['attempt']} ({str(run['head'])[:7]})"
    return {
        "source": f"ci_timings.py: {measured}, unit-timings.json",
        "modules": {name: round(seconds, 1) for name, seconds in report["unit"]["modules"].items()},
    }


def coverage_report(run: dict | None, scripts: dict) -> dict:
    if not run:
        return {"available": False}
    statuses = {job["name"]: job["status"] for job in run["jobs"]}
    executed = planned = 0
    for group in scripts.values():
        for script in group:
            cases = script.get("cases") or {}
            planned += len(cases.get("planned") or [])
            executed += sum(case.get("status") == "passed" for case in cases.get("executed") or [])
    return {
        "available": True,
        "status": run["status"],
        "checks": len(statuses),
        "not_passed": sorted(name for name, status in statuses.items() if status != "passed" and name != "live"),
        "validators": {name: statuses.get(name, "missing") for name in VALIDATORS},
        "cases": {"planned": planned, "passed": executed},
    }


def analyse(directory: Path, browser_lanes: list[int]) -> dict:
    run = read_json(directory / "run.json")
    jobs = [phases(job) for job in read_json(directory / "jobs.json")["jobs"]]
    if run is None or not jobs:
        raise ValueError(f"{directory}: run.json and jobs.json with at least one job are required")
    path = critical_path(jobs)
    found = evidence(directory)
    return {
        "run": {
            "id": run["id"],
            "attempt": run.get("run_attempt", 1),
            "event": run.get("event"),
            "head": run.get("head_sha"),
            "conclusion": run.get("conclusion"),
            "elapsed": span(run.get("run_started_at") or run["created_at"], max(job["completed"] for job in jobs)),
        },
        "jobs": jobs,
        "critical_path": [job["name"] for job in path],
        "critical_seconds": span(path[0]["created"], path[-1]["completed"]),
        "summed_job_seconds": sum(job["duration"] for job in jobs),
        "queue_seconds": sum(job["queue"] for job in jobs),
        "setup_seconds": sum(job["setup"] for job in jobs),
        "concurrent_peak": concurrency_peak(jobs),
        "lanes": lane_report(found, browser_lanes),
        "unit": unit_report(found["unit"]),
        "coverage": coverage_report(found["run"], found["scripts"]),
    }


def seconds_text(value: float) -> str:
    whole = round(value)
    return f"{whole // 60} min {whole % 60} s" if whole >= 60 else f"{value:.0f} s"


def render(report: dict) -> str:
    run = report["run"]
    lines = [
        f"Run {run['id']} attempt {run['attempt']} ({run['event']}, {str(run['head'])[:7]}, {run['conclusion']}): "
        f"{seconds_text(run['elapsed'])} from start to the last job.",
        "Critical path: "
        + " -> ".join(
            f"{job['name']} {job['queue'] + job['duration']:.0f} s"
            for name in report["critical_path"]
            for job in report["jobs"]
            if job["name"] == name
        )
        + f" ({seconds_text(report['critical_seconds'])}).",
        "",
        f"{'Job':<22}{'queue':>7}{'setup':>7}{'active':>8}{'teardown':>10}{'total':>7}",
    ]
    for job in report["jobs"]:
        lines.append(
            f"{job['name']:<22}{job['queue']:>7.0f}{job['setup']:>7.0f}{job['active']:>8.0f}"
            f"{job['teardown']:>10.0f}{job['queue'] + job['duration']:>7.0f}"
        )
    lines += [
        "",
        f"Summed job time {report['summed_job_seconds']:.0f} s, of which setup {report['setup_seconds']:.0f} s; "
        f"queue {report['queue_seconds']:.0f} s; peak of {report['concurrent_peak']} concurrent jobs.",
    ]
    lanes = report["lanes"]
    if not lanes["available"]:
        lines += ["", f"Lane evidence unavailable: {lanes['reason']}."]
    else:
        lines += ["", "Lanes (measured check time, predicted from the uncontended estimates, slot waits):"]
        for name, lane in lanes["lanes"].items():
            predicted = f"{lane['predicted']:.0f} s" if lane["predicted"] is not None else "-"
            lines.append(
                f"  {name:<10} {lane['seconds']:6.0f} s  predicted {predicted:>6}  waits {lane['slot_waits']:5.0f} s"
                f"  {', '.join(lane['jobs']) if len(lane['jobs']) <= 6 else str(len(lane['jobs'])) + ' checks'}"
                + (
                    "  (caches: " + ", ".join(f"{tool} {state}" for tool, state in lane["caches"].items()) + ")"
                    if lane["caches"]
                    else ""
                )
            )
        if lanes["waits"]:
            lines.append(
                "Longest slot waits: "
                + "; ".join(f"{item['name']} ({item['job']}) {item['seconds']:.0f} s" for item in lanes["waits"][:5])
            )
        lines.append(
            "Browser jobs (uncontended estimate / slot work): "
            + ", ".join(f"{item['name']} {item['estimate']:.0f}/{item['work']:.0f} s" for item in lanes["browser_jobs"])
        )
        for count, suggestion in lanes["suggestions"].items():
            lines.append(
                f"Suggested {count} browser lanes: "
                + " | ".join(f"{', '.join(lane['jobs'])} ({lane['predicted']:.0f} s)" for lane in suggestion)
            )
        lines.append("The suggestion is advice; the assignment in scripts/check_ci.py changes only through review.")
    unit = report["unit"]
    if unit["available"]:
        lines += [
            "",
            f"Unit tests: {unit['tests']} in {unit['seconds']:.0f} s; slowest classes: "
            + ", ".join(f"{item['name']} {item['seconds']:.1f} s" for item in unit["classes"]),
        ]
    coverage = report["coverage"]
    if coverage["available"]:
        validators = ", ".join(f"{name} {status}" for name, status in coverage["validators"].items())
        not_passed = ", ".join(coverage["not_passed"]) or "none"
        lines += [
            "",
            f"Coverage: run {coverage['status']}; {coverage['checks']} checks, not passed: {not_passed}; "
            f"validators: {validators}; browser cases passed {coverage['cases']['passed']} of "
            f"{coverage['cases']['planned']} planned.",
        ]
    else:
        lines += ["", "Coverage unavailable: the run has no health report, so it proves no complete check."]
    return "\n".join(lines) + "\n"


def gh(*args: str) -> str:
    try:
        return subprocess.run(["gh", *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout
    except FileNotFoundError as error:
        raise SystemExit(
            "ci_timings.py needs the GitHub CLI (gh) to read a run; use --from DIRECTORY offline"
        ) from error
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"gh {' '.join(args)} failed: {error.stderr.strip()}") from error


def fetch(run_id: int, attempt: int | None, repo: str) -> Path:
    """Keep the attempt's run, jobs and health artifact in the cache; an expired or replaced artifact leaves timings."""
    base = f"repos/{repo}/actions/runs/{run_id}"
    attempt = attempt or json.loads(gh("api", base))["run_attempt"]
    directory = CACHE / f"{run_id}-{attempt}"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "run.json").write_text(gh("api", f"{base}/attempts/{attempt}"), encoding="utf-8")
    (directory / "jobs.json").write_text(gh("api", f"{base}/attempts/{attempt}/jobs?per_page=100"), encoding="utf-8")
    if not (directory / "health").is_dir():
        # gh resolves {owner}/{repo} in API paths, but `run download` takes the checkout's repository by default.
        target = [] if repo == DEFAULT_REPO else ["-R", repo]
        name = f"health-{run_id}-{attempt}"
        result = subprocess.run(
            ["gh", "run", "download", str(run_id), *target, "-n", name, "-D", str(directory / "health")],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            print(
                f"WARNING: {name} unavailable ({result.stderr.strip()}); timings only. Artifacts expire, and a rerun "
                "removes those of earlier attempts."
            )
    return directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("run", nargs="?", type=int, help="the checks run ID")
    source.add_argument("--from", dest="directory", type=Path, help="a kept run directory, read offline")
    parser.add_argument("--attempt", type=int, help="the run attempt (default: the latest)")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="OWNER/NAME (default: this checkout's repository)")
    parser.add_argument("--browser-lanes", type=int, nargs="+", default=[3, 4], help="lane counts to suggest")
    parser.add_argument("--json", type=Path, help="also write the complete report as JSON")
    parser.add_argument("--unit-weights", type=Path, help="write the measured unit-test module seconds (for review)")
    args = parser.parse_args(argv)
    if any(count < 1 for count in args.browser_lanes):
        parser.error("--browser-lanes must be positive")
    directory = args.directory or fetch(args.run, args.attempt, args.repo)
    try:
        report = analyse(directory, args.browser_lanes)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Cannot read the run timings: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(render(report))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.unit_weights:
        if not report["unit"]["available"]:
            print("Cannot write unit weights: the run has no unit-test timings.", file=sys.stderr)
            return 1
        args.unit_weights.write_text(json.dumps(unit_weights(report), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
