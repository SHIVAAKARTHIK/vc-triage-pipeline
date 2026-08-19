"""Prompt rendering: does the system prompt actually carry the thesis, and does
the candidate prompt actually carry the evidence the model is required to cite?
"""

from __future__ import annotations

from triage import thesis
from triage.analyse import render_candidate_prompt, render_system_prompt


class TestSystemPrompt:
    def test_contains_every_dimension_name_and_weight(self) -> None:
        rendered = render_system_prompt()
        for d in thesis.DIMENSIONS:
            assert d.name in rendered
            assert f"{d.weight}%" in rendered

    def test_contains_the_anti_portfolio_from_the_real_document(self) -> None:
        """Dex is named in docs/thesis.md's anti-portfolio as the canonical
        no-named-workflow example -- if this is in the rendered prompt, the
        prose is genuinely coming from the document, not a hardcoded copy."""
        rendered = render_system_prompt()
        assert "Dex" in rendered

    def test_has_no_unrendered_jinja_tokens(self) -> None:
        rendered = render_system_prompt()
        assert "{{" not in rendered
        assert "{%" not in rendered

    def test_does_not_ask_the_model_to_choose_a_call(self) -> None:
        """The prompt should explicitly say the call is computed, not asked
        for -- regression guard against accidentally reintroducing that ask."""
        rendered = render_system_prompt()
        assert "you do not need to compute" in rendered.lower()


class TestCandidatePrompt:
    def test_contains_the_candidates_own_evidence_ids(self, make_candidate, make_evidence) -> None:
        ev = make_evidence(url="https://example.com/a", snippet="a distinctive snippet")
        candidate = make_candidate(evidence=[ev])

        rendered = render_candidate_prompt(candidate)

        assert ev.id in rendered
        assert "a distinctive snippet" in rendered
        assert candidate.name in rendered

    def test_has_no_unrendered_jinja_tokens(self, make_candidate) -> None:
        rendered = render_candidate_prompt(make_candidate())
        assert "{{" not in rendered
        assert "{%" not in rendered

    def test_handles_a_candidate_with_no_founders(self, make_candidate) -> None:
        candidate = make_candidate(founders=[])
        rendered = render_candidate_prompt(candidate)
        assert "(none found)" in rendered
