"""judge_memo: the retry-on-invalid-output loop for the eval stage.

Same fake-sender approach as test_analyse.py (see conftest.py's
scripted_sender/tool_response fixtures) — no network, no key needed.
"""

from __future__ import annotations

import pytest

from triage.eval import TOOL_NAME, JudgeFailedError, judge_memo, render_judge_prompt


def _valid_judgment(traceability: int = 4, clarity: int = 5) -> dict:
    return {
        "traceability_score": traceability,
        "traceability_notes": "The revenue claim matches the cited homepage snippet.",
        "clarity_score": clarity,
        "clarity_notes": "The call and its main driver are in the first three lines.",
    }


class TestRenderJudgePrompt:
    def test_includes_the_memo_text_verbatim(self) -> None:
        rendered = render_judge_prompt("# Egress Health — Take a meeting\n\nSome memo body.")
        assert "# Egress Health — Take a meeting" in rendered
        assert "Some memo body." in rendered

    def test_has_no_unrendered_jinja_tokens(self) -> None:
        rendered = render_judge_prompt("a memo")
        assert "{{" not in rendered
        assert "{%" not in rendered


class TestJudgeMemo:
    def test_happy_path_returns_a_valid_judge_result(
        self, scripted_sender, tool_response
    ) -> None:
        judgment = _valid_judgment(traceability=4, clarity=5)
        sender = scripted_sender([tool_response(judgment, tool_name=TOOL_NAME)])

        result = judge_memo(sender, "egress-health", "a memo body", max_attempts=2)

        assert len(sender.calls) == 1
        assert result.memo_slug == "egress-health"
        assert result.traceability_score == 4
        assert result.clarity_score == 5
        assert result.model_used

    def test_retries_once_on_a_malformed_response_then_succeeds(
        self, scripted_sender, tool_response
    ) -> None:
        bad = {"traceability_score": 4}  # missing required fields
        good = _valid_judgment()
        sender = scripted_sender(
            [tool_response(bad, tool_name=TOOL_NAME), tool_response(good, tool_name=TOOL_NAME)]
        )

        result = judge_memo(sender, "mesh", "a memo body", max_attempts=2)

        assert len(sender.calls) == 2
        assert result.memo_slug == "mesh"

    def test_raises_after_max_attempts_are_exhausted(
        self, scripted_sender, tool_response
    ) -> None:
        bad = {"traceability_score": 4}
        always_bad = [tool_response(bad, tool_name=TOOL_NAME) for _ in range(2)]
        sender = scripted_sender(always_bad)

        with pytest.raises(JudgeFailedError, match="dex"):
            judge_memo(sender, "dex", "a memo body", max_attempts=2)

        assert len(sender.calls) == 2

    def test_score_out_of_range_is_rejected_and_retried(
        self, scripted_sender, tool_response
    ) -> None:
        out_of_range = _valid_judgment()
        out_of_range["traceability_score"] = 9  # only 1-5 is valid
        good = _valid_judgment()
        sender = scripted_sender(
            [
                tool_response(out_of_range, tool_name=TOOL_NAME),
                tool_response(good, tool_name=TOOL_NAME),
            ]
        )

        result = judge_memo(sender, "toothy-ai", "a memo body", max_attempts=2)

        assert len(sender.calls) == 2
        assert 1 <= result.traceability_score <= 5

    def test_uses_the_tool_name_the_prompt_asks_for(self, scripted_sender, tool_response) -> None:
        sender = scripted_sender([tool_response(_valid_judgment(), tool_name=TOOL_NAME)])
        judge_memo(sender, "cardamon", "a memo body", max_attempts=2)

        called_tools = sender.calls[0]["tools"]
        assert called_tools[0]["function"]["name"] == TOOL_NAME
