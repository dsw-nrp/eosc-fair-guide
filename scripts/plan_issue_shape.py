"""The delivered planned-issue engine (`aiscr-plan-issue`), loaded read-only from `.agents/scripts/github/`.

The issue templates and the Project audit both use its shape declarations and checks, so a delivery update that
changes them reaches both through this one import. Nothing here changes the delivered file.
"""

from __future__ import annotations

import importlib.util
import sys
from functools import cache
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / ".agents" / "scripts" / "github" / "github_issues.py"


@cache
def engine() -> ModuleType:
    """The delivered module; its own `lib` and `github` imports resolve from `.agents/scripts`."""
    scripts = str(ENGINE.parent.parent)
    if scripts not in sys.path:
        sys.path.append(scripts)
    spec = importlib.util.spec_from_file_location("aiscr_github_issues", ENGINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def body_type(body: str) -> str | None:
    """The body's `Type`/`Typ` metadata value (`bug`, `feature`, `task` or anything written there), else None."""
    lines = (body or "").replace("\r\n", "\n").replace("\r", "\n").splitlines()
    try:
        # The engine's own row reader, so an accepted label form is never a second list here.
        rows = engine()._metadata_rows(lines)
    except Exception:  # noqa: BLE001 - a duplicated row is the engine's shape finding, not a type
        return None
    return rows["Type"][1].strip().strip("`") if "Type" in rows else None
