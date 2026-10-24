#!/usr/bin/env python3
"""Run the complete unit suite in parallel shards with per-test timings and one merged slow-test report.

    python scripts/profile_checks.py [--shards N] [--shuffle SEED]

Test modules are packed into shards longest first from the measured module seconds in
``scripts/unit_shards.json``; a module without a measurement weighs one second. Each shard runs in its own process
with a private report directory, so no test writes into the report of the run that executes it. The merged
``unit-timings.json`` keeps every test's time, and the run fails when a test fails in any shard or when a
discovered test did not run exactly once. ``--shuffle`` reorders classes and their tests within each shard to expose
hidden shared state. The shard count comes from ``scripts/check_policy.json`` (``unit_shards``) unless given.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEIGHTS = ROOT / "scripts" / "unit_shards.json"
DEFAULT_WEIGHT = 1.0


class TimedResult(unittest.TextTestResult):
    """Keep individual durations without changing unittest's failure or skip semantics."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings: list[dict] = []
        self.started = 0.0

    def startTest(self, test):  # noqa: N802 - unittest API
        self.started = time.monotonic()
        super().startTest(test)

    def stopTest(self, test):  # noqa: N802 - unittest API
        self.timings.append({"test": test.id(), "seconds": time.monotonic() - self.started})
        super().stopTest(test)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def module_of(test) -> str:
    # A module that fails to import is still a module of the suite; its placeholder test names it.
    if isinstance(test, unittest.loader._FailedTest):  # noqa: SLF001 - the loader's import-failure record
        return test._testMethodName  # noqa: SLF001
    return test.id().split(".")[0]


def discover(start: Path) -> dict[str, list[str]]:
    """List the suite's test IDs by module; the shards import and run them, each in its own process."""
    imported, path = set(sys.modules), list(sys.path)
    modules: dict[str, list[str]] = {}
    try:
        for test in flatten(unittest.defaultTestLoader.discover(str(start), top_level_dir=str(start))):
            modules.setdefault(module_of(test), []).append(test.id())
    finally:
        for name in set(sys.modules) - imported:
            del sys.modules[name]
        sys.path[:] = path
    return modules


def assign(modules, weights: dict[str, float], count: int) -> list[list[str]]:
    """Deterministic longest-first packing; ties go to the lower shard, and empty shards are dropped."""
    shards: list[list[str]] = [[] for _ in range(max(1, count))]
    loads = [0.0] * len(shards)
    for module in sorted(modules, key=lambda name: (-weights.get(name, DEFAULT_WEIGHT), name)):
        target = min(range(len(shards)), key=lambda index: (loads[index], index))
        shards[target].append(module)
        loads[target] += weights.get(module, DEFAULT_WEIGHT)
    return [sorted(shard) for shard in shards if shard]


def shuffled(suite, seed: int) -> unittest.TestSuite:
    """Shuffle class order and each class's tests, keeping a class's tests together so its fixtures run once."""
    classes: dict[str, list] = {}
    for test in flatten(suite):
        classes.setdefault(f"{type(test).__module__}.{type(test).__qualname__}", []).append(test)
    order = random.Random(seed)
    groups = list(classes.values())
    order.shuffle(groups)
    for group in groups:
        order.shuffle(group)
    return unittest.TestSuite(test for group in groups for test in group)


def run_shard(start: Path, modules: list[str], report: Path, seed: int | None) -> int:
    sys.path.insert(0, str(start))
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    if seed is not None:
        suite = shuffled(suite, seed)
    result = unittest.TextTestRunner(verbosity=0, resultclass=TimedResult).run(suite)
    report.write_text(
        json.dumps(
            {"tests": result.timings, "successful": result.wasSuccessful(), "skipped": len(result.skipped)}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if result.wasSuccessful() else 1


def shard_count() -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_all  # noqa: PLC0415 - the budget owner is needed only when no count was given

    return check_all.execution_defaults(dict(os.environ), os.cpu_count() or 1)["unit_shards"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shards", type=int, help="parallel shard processes (default: the policy's unit_shards)")
    parser.add_argument("--shuffle", type=int, metavar="SEED", help="shuffle classes and tests within each shard")
    parser.add_argument("--start", type=Path, default=ROOT / "tests", help=argparse.SUPPRESS)
    parser.add_argument("--weights", type=Path, default=WEIGHTS, help=argparse.SUPPRESS)
    parser.add_argument("--run-shard", nargs="+", metavar="MODULE", help=argparse.SUPPRESS)
    parser.add_argument("--shard-report", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.run_shard:
        return run_shard(args.start, args.run_shard, args.shard_report, args.shuffle)
    count = args.shards or shard_count()
    if count < 1:
        parser.error("--shards must be positive")

    modules = discover(args.start)
    weights = json.loads(args.weights.read_text(encoding="utf-8"))["modules"] if args.weights.is_file() else {}
    shards = assign(modules, weights, count)
    directory = Path(os.environ.get("CHECK_REPORT_DIR", ROOT / ".cache" / "check-details"))
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="unit-shards-") as scratch:

        def launch(index: int):
            private = Path(scratch) / f"shard-{index}"
            (private / "details").mkdir(parents=True)
            command = [sys.executable, str(Path(__file__).resolve()), "--start", str(args.start)]
            command += ["--run-shard", *shards[index], "--shard-report", str(private / "report.json")]
            command += ["--shuffle", str(args.shuffle)] if args.shuffle is not None else []
            env = {**os.environ, "CHECK_REPORT_DIR": str(private / "details")}
            started = time.monotonic()
            # A failing shard is a result to merge, not an exception: its report and output still count.
            done = subprocess.run(
                command,
                check=False,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            report = private / "report.json"
            data = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else None
            return done.returncode, done.stdout + done.stderr, data, time.monotonic() - started

        with ThreadPoolExecutor(max_workers=len(shards)) as pool:
            outcomes = list(pool.map(launch, range(len(shards))))

    timings, problems, rows = [], [], []
    for index, (returncode, output, data, seconds) in enumerate(outcomes):
        executed = data["tests"] if data else []
        timings += executed
        rows.append({"modules": shards[index], "tests": len(executed), "seconds": seconds, "returncode": returncode})
        print(f"shard {index + 1}/{len(shards)}: {len(executed)} tests in {seconds:.1f}s, exit {returncode}")
        if returncode or data is None:
            print(output.rstrip())
        if data is None:
            problems.append(f"shard {index + 1} left no report (exit {returncode})")
    expected = Counter(test for tests in modules.values() for test in tests)
    seen = Counter(item["test"] for item in timings)
    if missing := sorted((expected - seen).elements()):
        problems.append(f"{len(missing)} discovered tests did not run, first: {missing[0]}")
    if extra := sorted((seen - expected).elements()):
        problems.append(f"{len(extra)} test runs were not discovered once, first: {extra[0]}")
    successful = not problems and all(returncode == 0 for returncode, *_ in outcomes)
    (directory / "unit-timings.json").write_text(
        json.dumps(
            {
                "tests": sorted(timings, key=lambda item: -item["seconds"]),
                "successful": successful,
                "skipped": sum(data["skipped"] for _, _, data, _ in outcomes if data),
                "shards": rows,
                "shuffle": args.shuffle,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    for problem in problems:
        print(f"FAILED: {problem}")
    for item in sorted(timings, key=lambda item: -item["seconds"])[:15]:
        print(f"{item['seconds']:7.2f}s {item['test']}")
    return 0 if successful else 1


if __name__ == "__main__":
    sys.exit(main())
