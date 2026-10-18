"""Verify delivered file bytes and mixed-reader sections against the read-only delivery receipt."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_surfaces import ROOT, delivery_findings, load


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        config, receipt = load(args.root.resolve())
        findings = delivery_findings(args.root.resolve(), config, receipt)
    except (OSError, ValueError, KeyError, TypeError) as error:
        findings = [str(error)]
    for finding in findings:
        print(finding)
    print(f"check_sibling_delivery: {len(findings)} finding(s)")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
