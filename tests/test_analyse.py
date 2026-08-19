"""analyse_candidate: the retry-on-invalid-output loop.

A fake `send_message` (matching `anthropic.Anthropic(...).messages.create`'s
call signature — see the `scripted_sender`/`tool_response` fixtures in
conftest.py) returns scripted responses in sequence, so these tests never touch
the network or need an API key -- see tests/test_analyse_live.py for the one
real call.
"""

from __future__ import annotations

import pytest

from triage import thesis
from triage.analyse import AnalysisFailedError, analyse_candidate


class TestHappyPath:
    def test_builds_a_valid_analysis_with_computed_call_and_total(
        self, make_candidate, make_evidence, scripted_sender, tool_response, valid_raw_input
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        sender = scripted_sender([tool_response(valid_raw_input(ev.id, score=8))])

        analysis = analyse_candidate(sender, candidate)

        assert len(sender.calls) == 1
        assert analysis.candidate_slug == candidate.slug
        # every dimension scored 8/10 -> 0.8 * 100 = 80 -> >= MEET_THRESHOLD (70)
        assert analysis.total_score == 80
        assert analysis.call == "meet"
        assert {d.name for d in analysis.dimension_scores} == set(thesis.dimension_names())
        first = analysis.dimension_scores[0]
        assert first.weight == thesis.weight_for(first.name)

    def test_low_scores_produce_a_pass(
        self, make_candidate, make_evidence, scripted_sender, tool_response, valid_raw_input
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        sender = scripted_sender([tool_response(valid_raw_input(ev.id, score=2))])

        analysis = analyse_candidate(sender, candidate)

        assert analysis.total_score == 20
        assert analysis.call == "pass"


class TestRetryOnDimensionNameMismatch:
    def test_retries_once_and_succeeds(
        self, make_candidate, make_evidence, scripted_sender, tool_response, valid_raw_input
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        bad = valid_raw_input(ev.id, dimension_names=("workflow_ownership", "technical_depth"))
        good = valid_raw_input(ev.id)
        sender = scripted_sender([tool_response(bad), tool_response(good)])

        analysis = analyse_candidate(sender, candidate, max_attempts=3)

        assert len(sender.calls) == 2
        assert analysis is not None
        second_call_content = sender.calls[1]["messages"][0]["content"]
        assert "team_domain_fit" in second_call_content
        assert "must use exactly" in second_call_content


class TestRetryOnDanglingEvidence:
    def test_retries_and_names_the_bad_id_in_the_correction(
        self, make_candidate, make_evidence, scripted_sender, tool_response, valid_raw_input
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        fabricated_id = "ev_deadbeef"
        bad = valid_raw_input(fabricated_id)
        good = valid_raw_input(ev.id)
        sender = scripted_sender([tool_response(bad), tool_response(good)])

        analysis = analyse_candidate(sender, candidate, max_attempts=3)

        assert len(sender.calls) == 2
        assert analysis.candidate_slug == candidate.slug
        second_call_content = sender.calls[1]["messages"][0]["content"]
        assert fabricated_id in second_call_content


class TestRetryOnMalformedResponse:
    def test_retries_when_a_required_field_is_missing(
        self, make_candidate, make_evidence, scripted_sender, tool_response, valid_raw_input
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        bad = valid_raw_input(ev.id)
        del bad["market"]
        good = valid_raw_input(ev.id)
        sender = scripted_sender([tool_response(bad), tool_response(good)])

        analysis = analyse_candidate(sender, candidate, max_attempts=3)
        assert len(sender.calls) == 2
        assert analysis is not None

    def test_retries_when_the_model_does_not_call_the_tool_at_all(
        self,
        make_candidate,
        make_evidence,
        scripted_sender,
        tool_response,
        text_response,
        valid_raw_input,
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        sender = scripted_sender([text_response(), tool_response(valid_raw_input(ev.id))])

        analysis = analyse_candidate(sender, candidate, max_attempts=3)
        assert len(sender.calls) == 2
        assert analysis is not None


class TestExhaustingAttempts:
    def test_raises_analysis_failed_error_after_max_attempts(
        self, make_candidate, make_evidence, scripted_sender, tool_response, valid_raw_input
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        always_bad = [tool_response(valid_raw_input("ev_deadbeef")) for _ in range(3)]
        sender = scripted_sender(always_bad)

        with pytest.raises(AnalysisFailedError, match=candidate.slug):
            analyse_candidate(sender, candidate, max_attempts=3)

        assert len(sender.calls) == 3
