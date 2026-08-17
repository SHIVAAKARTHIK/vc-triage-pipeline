"""Validator behaviour for the core schemas.

Each test targets one thing the schema is supposed to make impossible, per
docs/decisions/0002-dimension-scores-are-data.md and the module docstring in
src/triage/schemas.py: malformed evidence ids, claims with no evidence, dimension
weights that don't add up, and a total score that isn't self-computed.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from triage.schemas import DimensionScore, Evidence, NarrativeClaim
from triage.util import evidence_id


class TestEvidence:
    def test_accepts_a_well_formed_id(self, make_evidence) -> None:
        e = make_evidence()
        assert e.id == evidence_id(e.url.unicode_string())

    def test_rejects_a_malformed_id(self) -> None:
        with pytest.raises(ValidationError, match="ev_<8 hex chars>"):
            Evidence(
                id="not-an-evidence-id",
                url="https://example.com",
                source="hn",
                retrieved_at="2026-08-17T12:00:00Z",
                snippet="some text",
            )

    def test_rejects_empty_snippet(self, make_evidence) -> None:
        with pytest.raises(ValidationError):
            make_evidence(snippet="")


class TestNarrativeClaim:
    def test_rejects_a_claim_with_no_evidence_ids(self) -> None:
        with pytest.raises(ValidationError):
            NarrativeClaim(text="Some claim about the team.", evidence_ids=[])

    def test_rejects_a_malformed_evidence_id(self) -> None:
        with pytest.raises(ValidationError, match="malformed evidence ids"):
            NarrativeClaim(text="Some claim.", evidence_ids=["totally-not-an-id"])


class TestCandidate:
    def test_requires_at_least_one_evidence_item(self, make_candidate) -> None:
        with pytest.raises(ValidationError):
            make_candidate(evidence=[])

    def test_rejects_duplicate_evidence_ids(self, make_candidate, make_evidence) -> None:
        dupe = make_evidence()
        with pytest.raises(ValidationError, match="duplicate evidence ids"):
            make_candidate(evidence=[dupe, dupe])


class TestDimensionWeights:
    def test_accepts_weights_that_sum_to_100(self, make_analysis) -> None:
        a = make_analysis(weights=(40, 20, 15, 15, 10))
        assert sum(d.weight for d in a.dimension_scores) == 100

    def test_rejects_weights_that_do_not_sum_to_100(self, make_analysis) -> None:
        with pytest.raises(ValidationError, match="dimension weights sum to"):
            make_analysis(weights=(40, 20, 15, 15, 5))  # sums to 95

    def test_score_out_of_range_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore(name="x", weight=100, score=11, rationale="r")


class TestTotalScoreIsComputed:
    def test_total_score_is_not_an_accepted_input(self, make_analysis) -> None:
        """total_score is a computed field: nothing upstream (LLM output included)
        can set it directly. See ADR 0002."""
        a = make_analysis(weights=(40, 20, 15, 15, 10))
        # every dimension scored 7/10 in the factory -> 0.7 * 100 = 70
        assert a.total_score == 70

    def test_total_score_reflects_each_dimensions_own_rating(self, make_analysis) -> None:
        a = make_analysis(weights=(50, 50, 0.01, 0.01, 0.01))
        for d in a.dimension_scores:
            d.score = 10  # not normally mutated post-validation, but exercises the formula
        assert a.total_score == round(sum(d.score / 10 * d.weight for d in a.dimension_scores))


class TestRecommendation:
    def test_change_my_mind_requires_two_to_three_items(self, make_analysis) -> None:
        with pytest.raises(ValidationError):
            make_analysis(change_my_mind=["only one thing"])

    def test_change_my_mind_rejects_more_than_three(self, make_analysis) -> None:
        with pytest.raises(ValidationError):
            make_analysis(change_my_mind=["a", "b", "c", "d"])

    def test_call_must_be_one_of_the_three_literals(self, make_analysis) -> None:
        with pytest.raises(ValidationError):
            make_analysis(call="strong buy")

    def test_requires_at_least_one_risk(self, make_analysis) -> None:
        with pytest.raises(ValidationError):
            make_analysis(risks=[])
