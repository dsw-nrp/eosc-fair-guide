#!/usr/bin/env python3
"""Run the guide's checks with one command: build the site, then every check at once.

    python scripts/check_all.py [--base REF] [--live] [--jobs N] [--only NAME ...]

Builds the site into ``_site/``, then runs the content contract, the duplicates check, the unit tests, Ruff, the
icon and licence checks, the three crate validations and the page, API and diagram checks, each in its own process
and as many at a time as the computer has cores. Prints each check's result and time as it finishes, the output of
the checks that failed, and exits with 1 if any did. ``--live`` adds the live checks, which need the network;
``--only`` runs the named checks alone; ``--base`` passes a git reference to the content checks for paradata
freshness (``HEAD`` by default).

Run it with the interpreter of the environment that has ``requirements-dev.txt`` installed, after ``npm ci``. When
``PLAYWRIGHT_BROWSERS_PATH`` is not set and ``.cache/ms-playwright`` exists, the browser checks use it.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import build_api
import check_health

ROOT = Path(__file__).resolve().parent.parent
BROWSERS = ROOT / ".cache" / "ms-playwright"


@dataclass(frozen=True)
class Job:
    name: str
    command: list[str]


@dataclass(frozen=True)
class Result:
    job: Job
    returncode: int
    seconds: float
    output: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def tool(name: str) -> str:
    """A console script of the running interpreter's environment, or the one on the path."""
    here = Path(sys.executable).parent
    for candidate in (here / name, here / f"{name}.exe", here / "Scripts" / f"{name}.exe"):
        if candidate.exists():
            return str(candidate)
    return shutil.which(name) or name


def jobs(base: str | None, live: bool) -> list[Job]:
    python = sys.executable
    validator = tool("rocrate-validator")
    npm = shutil.which("npm") or "npm"
    crate = ["--skip-availability-check", "_site"]
    found = [
        Job("content", [python, "scripts/check_content.py", *(["--base", base] if base else [])]),
        Job("duplicates", [python, "scripts/check_duplicates.py"]),
        Job("health", [python, "scripts/check_health.py", "--output", ".cache/health-inventory"]),
        Job("unit", [python, "-m", "unittest", "discover", "-s", "tests", "-q"]),
        Job("ruff", [python, "-m", "ruff", "check", "scripts", "tests"]),
        Job("format", [python, "-m", "ruff", "format", "--check", "scripts", "tests"]),
        Job("icons", [python, "scripts/vendor_icons.py", "--check"]),
        Job("reuse", [python, "-m", "reuse", "lint"]),
        Job("crate", [validator, "validate", "-p", "ro-crate-1.2", *crate]),
        Job("process-run", [validator, "validate", "-p", "process-run-crate-0.5", "-nh", *crate]),
        Job(
            "profile",
            [validator, "validate", "--extra-profiles-path", "_site/profile", "-p", "fair-guide-0.1", "-nh", *crate],
        ),
        Job("page", [npm, "run", "-s", "check:page"]),
        Job("discovery", [npm, "run", "-s", "check:discovery"]),
        Job("assessment", [npm, "run", "-s", "check:assessment"]),
        Job("api", [npm, "run", "-s", "check:api"]),
        Job("diagrams", [npm, "run", "-s", "check:diagrams"]),
    ]
    if live:
        found.append(Job("live", [npm, "run", "-s", "check:live"]))
    return found


def environment() -> dict[str, str]:
    env = dict(os.environ)
    if "PLAYWRIGHT_BROWSERS_PATH" not in env and BROWSERS.is_dir():
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run(job: Job, env: dict[str, str]) -> Result:
    start = time.monotonic()
    try:
        done = subprocess.run(
            job.command,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        returncode, output = done.returncode, done.stdout + done.stderr
    except OSError as error:
        returncode, output = 127, f"could not start {job.command[0]}: {error}"
    return Result(job, returncode, time.monotonic() - start, output)


def run_all(selected: list[Job], workers: int, env: dict[str, str], report=print) -> list[Result]:
    """Run the jobs, at most `workers` at a time, reporting each as it finishes; results in the jobs' order."""
    results: dict[str, Result] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(run, job, env): job for job in selected}
        for future in as_completed(futures):
            result = future.result()
            results[result.job.name] = result
            report(f"{'ok  ' if result.ok else 'FAIL'} {result.seconds:6.1f}s  {result.job.name}")
    return [results[job.name] for job in selected]


def tail(text: str, lines: int = 40) -> str:
    return "\n".join(text.rstrip().splitlines()[-lines:])


def emit_report(
    build: Result,
    results: list[Result],
    available: list[Job],
    selected: list[Job],
    *,
    output: Path,
    previous: Path | None,
    site: Path | None = None,
    pending_api: bool = False,
) -> None:
    """Retain failures and unrun jobs; a partial run never reports the whole suite as passed."""
    completed = {result.job.name: result for result in [build, *results]}
    selected_names = {job.name for job in selected}
    run_jobs = []
    for job in [build.job, *available]:
        result = completed.get(job.name)
        status = (
            "passed"
            if result and result.ok
            else "failed"
            if result
            else "not_run"
            if pending_api and job.name == "health-api"
            else "blocked"
            if job.name in selected_names
            else "not_run"
        )
        run_jobs.append(
            {
                "name": job.name,
                "status": status,
                "seconds": round(result.seconds, 2) if result else None,
                "output": tail(result.output) if result and not result.ok else "",
            }
        )
    failed = any(not result.ok for result in completed.values())
    partial = bool({job.name for job in available if job.name != "live"} - selected_names)
    run = {
        "status": "failed" if failed else "partial" if partial or pending_api else "passed",
        "reason": (
            "Jobs marked not_run were not selected, including optional live checks. "
            "Jobs marked blocked could not run after a failed build."
        ),
        "jobs": run_jobs,
    }
    if pending_api:
        run["reason"] += " Final health API validation is pending."
    content = None
    try:
        content = check_health.build_crate.load_content(ROOT / "content")
    except (OSError, ValueError, check_health.build_crate.ContentError) as error:
        report = check_health.unreadable_report(str(error), run)
    else:
        previous_error = None
        try:
            baseline = check_health.read_previous(previous)
        except (OSError, ValueError) as error:
            baseline = None
            previous_error = str(error)
        report = check_health.make_report(content, ROOT, run=run, previous=baseline)
        if previous_error:
            report["trend"] = {"available": False, "reason": f"Previous report could not be read: {previous_error}"}
    check_health.write_report(report, output)
    if site is not None and build.ok:
        build_api.publish_health(site, report, content)
    print(f"Health dashboard: {output / 'index.html'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="HEAD", help="git reference for paradata freshness (default HEAD)")
    parser.add_argument("--live", action="store_true", help="also run the live checks, which need the network")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4, help="checks run at a time")
    parser.add_argument("--only", nargs="+", metavar="NAME", help="run only these checks")
    parser.add_argument(
        "--report-dir", type=Path, default=ROOT / ".cache" / "health", help="JSON, HTML and CI-summary output directory"
    )
    parser.add_argument(
        "--previous-report", type=Path, help="previous health.json for coverage and check-result trends"
    )
    args = parser.parse_args(argv)

    selected = jobs(args.base, args.live)
    if args.only:
        unknown = sorted(set(args.only) - {job.name for job in selected})
        if unknown:
            parser.error(f"unknown check: {', '.join(unknown)}; known: {', '.join(job.name for job in selected)}")
        selected = [job for job in selected if job.name in args.only]

    env = environment()
    health_api = Job("health-api", [shutil.which("node") or "node", "tests/api/check_api.mjs", "--health-only"])
    available = [*jobs(args.base, live=True), health_api]
    selected.append(health_api)
    start = time.monotonic()
    build = run(Job("build", [sys.executable, "scripts/build_site.py"]), env)
    print(f"{'ok  ' if build.ok else 'FAIL'} {build.seconds:6.1f}s  build")
    if not build.ok:
        print(tail(build.output))
        emit_report(build, [], available, selected, output=args.report_dir, previous=args.previous_report)
        return 1
    results = run_all([job for job in selected if job != health_api], args.jobs, env)
    emit_report(
        build,
        results,
        available,
        selected,
        output=args.report_dir,
        previous=args.previous_report,
        site=ROOT / "_site",
        pending_api=True,
    )
    candidate_api = run(health_api, env)
    print(f"{'ok  ' if candidate_api.ok else 'FAIL'} {candidate_api.seconds:6.1f}s  health-api (publication)")
    results.append(candidate_api)
    emit_report(
        build, results, available, selected, output=args.report_dir, previous=args.previous_report, site=ROOT / "_site"
    )
    final_api = run(health_api, env)
    print(f"{'ok  ' if final_api.ok else 'FAIL'} {final_api.seconds:6.1f}s  health-api (final snapshot)")
    if not final_api.ok:
        results[-1] = Result(
            health_api, final_api.returncode, candidate_api.seconds + final_api.seconds, final_api.output
        )
        emit_report(
            build,
            results,
            available,
            selected,
            output=args.report_dir,
            previous=args.previous_report,
            site=ROOT / "_site",
        )
    failed = [result for result in results if not result.ok]
    for result in failed:
        print(f"\n--- {result.job.name} ({' '.join(result.job.command[1:])})\n{tail(result.output)}")
    total = time.monotonic() - start
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed in {total:.1f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
