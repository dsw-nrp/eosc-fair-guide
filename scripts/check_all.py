#!/usr/bin/env python3
"""Run the guide's checks with one command: build the site, then every check at once.

    python scripts/check_all.py [--base REF] [--live] [--jobs N] [--only NAME ...]

Builds the site into ``_site/``, then runs the content contract, the duplicates check, the unit tests, Ruff, the
icon and licence checks, the three crate validations and the page, API and diagram checks, each in its own process
with separate bounded local and CI defaults. Prints each check's result and time as it finishes, the output of
the checks that failed, and exits with 1 if any did. ``--live`` adds the live checks, which need the network;
``--only`` runs the named checks alone after the build, which every check depends on, and reports the others as not
run; the published-health validation (``health-api``) runs in a full run or when named. ``--base`` passes a git
reference to the content checks for paradata freshness, compared from where this branch left it exactly as a pull
request is (the remote's default branch by default, so a local run reports what the pull request will).

Run it with the interpreter of the environment that has ``requirements-dev.txt`` installed, after ``npm ci``.
Browser checks default to ``.cache/ms-playwright`` and respect an explicit ``PLAYWRIGHT_BROWSERS_PATH``.
``--browser-workers`` bounds browser cases across processes through shared slots; nested work cannot multiply it.
Complete child logs, script/case timings and failure artifacts live under the report directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import build_api
import check_content
import check_health

ROOT = Path(__file__).resolve().parent.parent
BROWSERS = ROOT / ".cache" / "ms-playwright"
BROWSER_JOBS = {
    "page",
    "final-candidate",
    "discovery",
    "helpers",
    "assessment",
    "model",
    "api",
    "diagrams",
    "live",
    "runtime",
}


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
    partial: bool = False

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
        Job("versions", [python, "scripts/release_versions.py", "check", "--site", "_site"]),
        Job("openspec", [npm, "run", "-s", "openspec:validate"]),
        Job("public-content", [python, "scripts/check_public_content.py"]),
        Job("health", [python, "scripts/check_health.py", "--output", ".cache/health-inventory"]),
        Job("unit", [python, "scripts/profile_checks.py"]),
        Job("runtime", [shutil.which("node") or "node", "--test", "tests/runtime.test.mjs"]),
        Job("ruff", [python, "-m", "ruff", "check", "scripts", "tests"]),
        Job("format", [python, "-m", "ruff", "format", "--check", "scripts", "tests"]),
        Job("icons", [python, "scripts/vendor_icons.py", "--check"]),
        Job("favicons", [python, "scripts/vendor_favicons.py", "--check"]),
        Job("fonts", [python, "scripts/vendor_fonts.py", "--check"]),
        Job("reuse", [python, "-m", "reuse", "lint"]),
        Job("crate", [validator, "validate", "-p", "ro-crate-1.2", *crate]),
        Job("process-run", [validator, "validate", "-p", "process-run-crate-0.5", "-nh", *crate]),
        Job(
            "profile",
            [validator, "validate", "--extra-profiles-path", "_site/profile", "-p", "fair-guide-0.1", "-nh", *crate],
        ),
        Job("page", [npm, "run", "-s", "check:page"]),
        Job("final-candidate", [npm, "run", "-s", "check:final"]),
        Job("discovery", [npm, "run", "-s", "check:discovery"]),
        Job("helpers", [npm, "run", "-s", "check:helpers"]),
        Job("assessment", [npm, "run", "-s", "check:assessment"]),
        Job("model", [npm, "run", "-s", "check:model"]),
        Job("api", [npm, "run", "-s", "check:api"]),
        Job("diagrams", [npm, "run", "-s", "check:diagrams"]),
    ]
    if live:
        found.append(Job("live", [npm, "run", "-s", "check:live"]))
    return found


def environment() -> dict[str, str]:
    env = dict(os.environ)
    if "PLAYWRIGHT_BROWSERS_PATH" not in env:
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def execution_defaults(env: dict[str, str], cpus: int) -> dict:
    """Share the npm/direct-Node policy; explicit command-line budgets take precedence."""
    profile = "ci" if env.get("CI", "").lower() not in ("", "0", "false") else "local"
    policy = json.loads((ROOT / "scripts/check_policy.json").read_text(encoding="utf-8"))[profile]
    return {"profile": profile, **{key: min(value, max(1, cpus)) for key, value in policy.items()}}


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
    partial = False
    if job.name in BROWSER_JOBS and env.get("CHECK_REPORT_DIR"):
        group = "final" if job.name == "final-candidate" else job.name
        detail = Path(env["CHECK_REPORT_DIR"]) / group / "scripts.json"
        if detail.is_file():
            try:
                summary = json.loads(detail.read_text(encoding="utf-8"))
                partial = summary["status"] == "partial"
            except (OSError, ValueError, KeyError) as error:
                returncode = 1
                output += f"\nInvalid script timing report: {error}"
    return Result(job, returncode, time.monotonic() - start, output, partial)


def run_all(selected: list[Job], workers: int, env: dict[str, str], report=print) -> list[Result]:
    """Run the jobs, at most `workers` at a time, reporting each as it finishes; results in the jobs' order."""
    results: dict[str, Result] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(run, job, env): job for job in selected}
        for future in as_completed(futures):
            result = future.result()
            results[result.job.name] = result
            if env.get("CHECK_REPORT_DIR"):
                logs = Path(env["CHECK_REPORT_DIR"]).parent / "logs"
                logs.mkdir(parents=True, exist_ok=True)
                (logs / f"{result.job.name}.log").write_text(result.output, encoding="utf-8")
            report(f"{'ok  ' if result.ok else 'FAIL'} {result.seconds:6.1f}s  {result.job.name}")
    return [results[job.name] for job in selected]


def tail(text: str, lines: int = 40) -> str:
    return "\n".join(
        line if len(line) <= 2000 else line[:2000] + " ... [full line retained in the check log]"
        for line in text.rstrip().splitlines()[-lines:]
    )


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
        script_details = []
        group = "final" if job.name == "final-candidate" else job.name
        details_path = output / "details" / group / "scripts.json"
        if result and details_path.is_file():
            try:
                details = json.loads(details_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                details = {"scripts": []}  # run() already records the invalid report as a failed job.
            for item in details["scripts"]:
                cases = item.get("cases") or {}
                script_details.append(
                    {
                        "name": item["file"],
                        "seconds": round(item["seconds"], 2),
                        "status": item["status"],
                        "planned": len(cases.get("planned", [])),
                        "executed": [
                            {key: case[key] for key in ("name", "status", "seconds", "aborted") if key in case}
                            for case in cases.get("executed", [])
                        ],
                        "skipped": cases.get("skipped", []),
                        "pending": cases.get("pending", []),
                    }
                )
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
                "output": tail(result.output) if result else "",
                "partial": result.partial if result else False,
                "scripts": script_details,
            }
        )
    failed = any(not result.ok for result in completed.values())
    partial = bool({job.name for job in available if job.name != "live"} - selected_names) or any(
        result.partial for result in results
    )
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
    parser.add_argument(
        "--base",
        help="git reference for paradata freshness, compared from where this branch left it, as in a pull request "
        "(default: the remote's default branch)",
    )
    parser.add_argument("--live", action="store_true", help="also run the live checks, which need the network")
    defaults = execution_defaults(dict(os.environ), os.cpu_count() or 1)
    parser.add_argument("--jobs", type=int, default=defaults["jobs"], help="checks run at a time (profile default)")
    parser.add_argument(
        "--browser-workers",
        type=int,
        default=os.environ.get("CHECK_BROWSER_WORKERS", defaults["browser_workers"]),
        help="browser work at a time, shared across groups (CLI > CHECK_BROWSER_WORKERS > profile)",
    )
    parser.add_argument("--only", nargs="+", metavar="NAME", help="run only these checks")
    parser.add_argument(
        "--report-dir", type=Path, default=ROOT / ".cache" / "health", help="JSON, HTML and CI-summary output directory"
    )
    parser.add_argument(
        "--previous-report", type=Path, help="previous health.json for coverage and check-result trends"
    )
    args = parser.parse_args(argv)
    if args.browser_workers < 1 or args.jobs < 1:
        parser.error("--jobs and --browser-workers must be positive")
    args.base = args.base or check_content.default_base(ROOT)

    health_api = Job("health-api", [shutil.which("node") or "node", "tests/api/check_api.mjs", "--health-only"])
    selected = jobs(args.base, args.live)
    known = [job.name for job in selected] + [health_api.name]
    if args.only:
        unknown = sorted(set(args.only) - set(known))
        if unknown:
            parser.error(f"unknown check: {', '.join(unknown)}; known: {', '.join(known)}")
    selected = selected_jobs([*selected, health_api], args.only)

    env = environment()
    env["CHECK_BROWSER_WORKERS"] = str(args.browser_workers)
    env["CHECK_REPORT_DIR"] = str((args.report_dir / "details").resolve())
    env["CHECK_BROWSER_SLOT_DIR"] = str((args.report_dir / "details" / f"budget-{uuid.uuid4().hex}").resolve())
    available = [*jobs(args.base, live=True), health_api]
    start = time.monotonic()
    build = run(Job("build", [sys.executable, "scripts/build_site.py"]), env)
    print(f"{'ok  ' if build.ok else 'FAIL'} {build.seconds:6.1f}s  build")
    if not build.ok:
        print(tail(build.output))
        emit_report(build, [], available, selected, output=args.report_dir, previous=args.previous_report)
        return 1
    args.report_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "profile": defaults["profile"],
        "jobs": args.jobs,
        "browser_workers": args.browser_workers,
        "logical_cpus": os.cpu_count(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "ci": bool(os.environ.get("CI")),
        "build_inputs": {
            name: hashlib.sha256((ROOT / "_site" / name).read_bytes()).hexdigest()
            for name in ("index.html", "assets/data/kb.js", "assets/data/ui.js", "ro-crate-metadata.json")
        },
    }
    (args.report_dir / "execution.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Execution: {defaults['profile']}, {args.jobs} outer jobs, {args.browser_workers} shared browser slots")
    results = run_all([job for job in selected if job != health_api], args.jobs, env)
    if health_api not in selected:
        # The published-health validation was not asked for: the report says so instead of running it anyway.
        emit_report(
            build,
            results,
            available,
            selected,
            output=args.report_dir,
            previous=args.previous_report,
            site=ROOT / "_site",
        )
        return finish(results, start)
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
    return finish(results, start)


def selected_jobs(available: list[Job], only: list[str] | None) -> list[Job]:
    """The jobs a run executes. Every job depends on the build, which always runs first; the published-health
    validation (health-api) also depends on the run's own report, so it runs in a full run or when named."""
    return list(available) if not only else [job for job in available if job.name in only]


def finish(results: list[Result], start: float) -> int:
    failed = [result for result in results if not result.ok]
    for result in failed:
        print(f"\n--- {result.job.name} ({' '.join(result.job.command[1:])})\n{tail(result.output)}")
    total = time.monotonic() - start
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed in {total:.1f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
