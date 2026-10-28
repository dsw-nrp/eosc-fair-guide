"""The block that ends every automated output: who acts next, the way round a blocker, and the evidence of completion.

Python renderers (check summaries, the collector, the maintenance digest, repair replies) use ``handoff``; the trusted
JavaScript publishers use its twin in ``.github/scripts/handoff.cjs``. A missing element is a programming error, so
an output can never end without saying what happens next.
"""

from __future__ import annotations

LABELS = ("Next", "If blocked", "Done when")


def handoff(next_step: str, blocked: str, done: str) -> list[str]:
    """The three Markdown list items, in order; each must say something."""
    values = (next_step, blocked, done)
    for label, value in zip(LABELS, values, strict=True):
        if not str(value).strip():
            raise ValueError(f"a handoff needs its {label!r} element")
    return [f"- **{label}:** {value}" for label, value in zip(LABELS, values, strict=True)]
