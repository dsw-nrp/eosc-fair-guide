#!/usr/bin/env python3
"""Run the complete unit suite with per-test timings and machine-readable slow-test evidence."""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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


def main() -> int:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=0, resultclass=TimedResult).run(suite)
    directory = Path(os.environ.get("CHECK_REPORT_DIR", ROOT / ".cache" / "check-details"))
    directory.mkdir(parents=True, exist_ok=True)
    timings = sorted(result.timings, key=lambda item: -item["seconds"])
    (directory / "unit-timings.json").write_text(
        json.dumps({"tests": timings, "successful": result.wasSuccessful(), "skipped": len(result.skipped)}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    for item in timings[:15]:
        print(f"{item['seconds']:7.2f}s {item['test']}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
