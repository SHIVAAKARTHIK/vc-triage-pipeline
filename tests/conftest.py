"""Shared fixture factories, exposed as pytest fixtures.

Each fixture yields a *function* (not a built object) so a test can call e.g.
`make_candidate(evidence=[])` with just the override it cares about, rather than
constructing a full Candidate/Analysis by hand every time. Kept as fixtures rather
than a plain importable module so test files don't need `tests/` on sys.path or an
`__init__.py` to resolve `tests.conftest` — pytest discovers conftest.py on its own.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from triage.schemas import (
    Analysis,
    Candidate,
    DimensionScore,
    Evidence,
    NarrativeClaim,
    TractionSignal,
)
from triage.util import evidence_id

NOW = datetime(2026, 8, 17, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def make_evidence():
    def _make(url: str = "https://news.ycombinator.com/item?id=1", **overrides) -> Evidence:
        fields = {
            "id": evidence_id(url),
            "url": url,
            "source": "hn",
            "retrieved_at": NOW,
            "snippet": "Show HN: we automate SMB accounts-receivable follow-up with an agent.",
        }
        fields.update(overrides)
        return Evidence(**fields)

    return _make


@pytest.fixture
def make_candidate(make_evidence):
    def _make(
        slug: str = "ledgerly", evidence: list[Evidence] | None = None, **overrides
    ) -> Candidate:
        ev = evidence if evidence is not None else [make_evidence()]
        fields = {
            "slug": slug,
            "name": "Ledgerly",
            "website": "https://ledgerly.example.com",
            "one_liner": "AI agent that chases invoices so SMB finance teams don't have to.",
            "founders": ["Asha Rao"],
            "source_batch": "YC W25",
            "traction": TractionSignal(kind="hn_post", detail="142 points, 38 comments"),
            "evidence": ev,
            "sourced_at": NOW,
        }
        fields.update(overrides)
        return Candidate(**fields)

    return _make


@pytest.fixture
def make_dimension_scores():
    def _make(weights: tuple[float, ...] = (40, 20, 15, 15, 10)) -> list[DimensionScore]:
        names = [
            "workflow_ownership",
            "buyer_pain",
            "team_domain_fit",
            "wedge_defensibility",
            "traction",
        ]
        return [
            DimensionScore(name=n, weight=w, score=7, rationale=f"placeholder rationale for {n}")
            for n, w in zip(names, weights, strict=True)
        ]

    return _make


@pytest.fixture
def make_analysis(make_dimension_scores):
    def _make(
        candidate_slug: str = "ledgerly",
        evidence_ids: list[str] | None = None,
        weights: tuple[float, ...] = (40, 20, 15, 15, 10),
        **overrides,
    ) -> Analysis:
        ids = evidence_ids if evidence_ids is not None else [evidence_id("https://news.ycombinator.com/item?id=1")]
        claim = NarrativeClaim(text="Placeholder claim text.", evidence_ids=ids)
        fields = {
            "candidate_slug": candidate_slug,
            "thesis_version": "thesis@dev",
            "model_used": "claude-opus-5",
            "analyzed_at": NOW,
            "team": claim,
            "product": claim,
            "market": claim,
            "risks": [claim],
            "dimension_scores": make_dimension_scores(weights),
            "call": "watch",
            "call_rationale": "Placeholder rationale for the call.",
            "change_my_mind": ["Signed pilot with a paying SMB", "Second technical co-founder"],
        }
        fields.update(overrides)
        return Analysis(**fields)

    return _make
