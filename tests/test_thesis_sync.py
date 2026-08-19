"""Guards the promise in ADR 0002/0004: docs/thesis.md is what a human reads,
src/triage/thesis.py is what the code loads, and this test is what stops them
silently drifting apart. Parses docs/thesis.md's own markdown tables directly —
no synthetic fixture — so a drift shows up here, not in a reviewer's read-through.
"""

from __future__ import annotations

import re
from pathlib import Path

from triage import thesis

THESIS_TEXT = Path("docs/thesis.md").read_text(encoding="utf-8")

_DIMENSION_ROW_RE = re.compile(r"^\|\s*`([a-z_]+)`\s*\|\s*([\d.]+)\s*\|", re.MULTILINE)
_THRESHOLD_ROW_RE = re.compile(
    r"^\|\s*(\d+)[–-]\d+\s*\|\s*(Take a meeting|Watch|Pass)\s*\|", re.MULTILINE
)


def test_dimension_names_and_weights_match_the_documents_table() -> None:
    rows = _DIMENSION_ROW_RE.findall(THESIS_TEXT)
    doc_dimensions = {name: float(weight) for name, weight in rows}
    assert doc_dimensions, "no dimension rows parsed out of docs/thesis.md -- table format changed?"

    config_dimensions = {d.name: d.weight for d in thesis.DIMENSIONS}
    assert doc_dimensions == config_dimensions


def test_call_thresholds_match_the_documents_table() -> None:
    rows = _THRESHOLD_ROW_RE.findall(THESIS_TEXT)
    lower_bounds = {label: int(bound) for bound, label in rows}
    assert lower_bounds, "no call-threshold rows parsed -- table format changed?"
    assert lower_bounds.get("Take a meeting") == thesis.MEET_THRESHOLD
    assert lower_bounds.get("Watch") == thesis.WATCH_THRESHOLD


def test_document_no_longer_carries_the_unreviewed_draft_note() -> None:
    """A soft reminder, not a hard gate on shipping: the thesis started life as
    an AI draft (see AI_USE.md) explicitly flagged as pending review. This just
    keeps that flag visible in the test output rather than silently forgotten."""
    if "pending Karthik's review" in THESIS_TEXT or "not yet been" in THESIS_TEXT:
        import warnings

        warnings.warn(
            "docs/thesis.md still carries its AI-draft/pending-review note -- "
            "make sure it's actually been read and owned before this ships.",
            stacklevel=1,
        )
