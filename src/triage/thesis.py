"""The structured runtime config the analyse stage actually loads.

`docs/thesis.md` is the human-readable source of truth (ADR 0002: dimensions are
data, not schema fields). This file is what code reads. The two are kept from
drifting apart in two different ways depending on what's being duplicated:

  * **Names and weights** are numbers a human could silently change in one place
    and forget the other — `tests/test_thesis_sync.py` parses docs/thesis.md's
    own markdown tables and asserts they match `DIMENSIONS`/`MEET_THRESHOLD`/
    `WATCH_THRESHOLD` here exactly. A drift fails the test suite, not a review.
  * **Prose** (the slice, why-now, anti-portfolio) is never duplicated at all —
    `section()` reads it straight out of docs/thesis.md at prompt-render time,
    so editing that document is the only edit needed to change what the model
    actually receives. See docs/decisions/0004.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

THESIS_PATH = Path("docs/thesis.md")


@dataclass(frozen=True)
class Dimension:
    name: str
    weight: float
    ten_looks_like: str
    zero_looks_like: str


DIMENSIONS: tuple[Dimension, ...] = (
    Dimension(
        name="workflow_ownership",
        weight=30,
        ten_looks_like=(
            "Agent executes the actual transaction end-to-end, no human step "
            "(e.g. filing/scrubbing insurance claims automatically)."
        ),
        zero_looks_like="Chat assistant that drafts something a human still reviews and sends.",
    ),
    Dimension(
        name="buyer_pain",
        weight=20,
        ten_looks_like=(
            "Buyer already has a named, quantifiable cost today -- a budget line, "
            "an FTE, hours/month spent on exactly this task."
        ),
        zero_looks_like="No evidence anyone currently pays for this work at all.",
    ),
    Dimension(
        name="team_domain_fit",
        weight=25,
        ten_looks_like=(
            "Founder has direct operating experience in the exact vertical and the "
            "technical depth to ship the agent."
        ),
        zero_looks_like="No visible domain background and no visible technical background.",
    ),
    Dimension(
        name="wedge_defensibility",
        weight=15,
        ten_looks_like=(
            "The agent accumulates workflow-specific data or integrations that "
            "compound the longer it runs."
        ),
        zero_looks_like="A thin prompt wrapper over a generic LLM call, replicable in a weekend.",
    ),
    Dimension(
        name="traction",
        weight=10,
        ten_looks_like=(
            "Real usage signal beyond batch admission -- a paying pilot, strong HN "
            "reception, or measurable outcomes."
        ),
        zero_looks_like="Idea-stage; no signal beyond being accepted into the batch.",
    ),
)

MEET_THRESHOLD = 70
WATCH_THRESHOLD = 40

_weight_sum = sum(d.weight for d in DIMENSIONS)
if abs(_weight_sum - 100) > 0.01:
    raise ValueError(f"DIMENSIONS weights sum to {_weight_sum}, expected 100 -- fix before import")


def dimension_names() -> tuple[str, ...]:
    return tuple(d.name for d in DIMENSIONS)


def weight_for(name: str) -> float:
    for d in DIMENSIONS:
        if d.name == name:
            return d.weight
    raise KeyError(f"unknown dimension {name!r}; expected one of {dimension_names()}")


def call_for_score(total_score: int) -> str:
    """The only place a categorical call is chosen — from the computed weighted
    total, never from the model. Mirrors ADR 0002's reasoning for total_score
    itself; see ADR 0004."""
    if total_score >= MEET_THRESHOLD:
        return "meet"
    if total_score >= WATCH_THRESHOLD:
        return "watch"
    return "pass"


def thesis_version() -> str:
    """A short hash of docs/thesis.md's current bytes, so every Analysis records
    exactly which thesis snapshot produced it (same construction as
    util.evidence_id: content-hashed, so identical content always yields the
    same tag)."""
    digest = hashlib.sha256(THESIS_PATH.read_bytes()).hexdigest()[:10]
    return f"thesis@{digest}"


def section(heading: str) -> str:
    """Extract one '## <heading>' section's body verbatim from docs/thesis.md,
    stopping at the next '## ' header. Used to build the analyse-stage prompt
    directly from the thesis document — see module docstring."""
    text = THESIS_PATH.read_text(encoding="utf-8")
    pattern = re.compile(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", re.DOTALL | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"section {heading!r} not found in {THESIS_PATH}")
    return match.group(1).strip()
