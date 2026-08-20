"""triage.memo — rendering, the Sources footer, and the pipe-escaping guard.

Reuses the make_candidate/make_evidence/make_analysis factories from
conftest.py so a memo is built from the same shapes the rest of the suite
already exercises.
"""

from __future__ import annotations

import pytest

from triage.evidence import DanglingEvidenceError
from triage.memo import CALL_LABELS, cited_evidence, render_memo
from triage.schemas import NarrativeClaim


class TestCitedEvidence:
    def test_returns_only_evidence_actually_cited(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        cited = make_evidence(url="https://example.com/cited")
        uncited = make_evidence(url="https://example.com/uncited")
        candidate = make_candidate(evidence=[cited, uncited])
        analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[cited.id])

        result = cited_evidence(candidate, analysis)

        assert [e.id for e in result] == [cited.id]

    def test_dedupes_evidence_cited_in_more_than_one_section(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        claim = NarrativeClaim(text="Cited twice.", evidence_ids=[ev.id])
        analysis = make_analysis(
            candidate_slug=candidate.slug,
            evidence_ids=[ev.id],
            team=claim,
            product=claim,  # same evidence cited again
        )

        result = cited_evidence(candidate, analysis)
        assert len(result) == 1

    def test_preserves_first_citation_order(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        first = make_evidence(url="https://example.com/first")
        second = make_evidence(url="https://example.com/second")
        candidate = make_candidate(evidence=[second, first])  # stored out of citation order
        analysis = make_analysis(
            candidate_slug=candidate.slug,
            evidence_ids=[first.id],
            team=NarrativeClaim(text="cites first", evidence_ids=[first.id]),
            product=NarrativeClaim(text="cites second", evidence_ids=[second.id]),
        )

        result = cited_evidence(candidate, analysis)
        assert [e.id for e in result] == [first.id, second.id]


class TestRenderMemo:
    def test_the_call_appears_before_the_scores_table(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[ev.id], call="meet")

        rendered = render_memo(candidate, analysis)

        call_index = rendered.index(CALL_LABELS["meet"])
        scores_index = rendered.index("## Scores")
        assert call_index < scores_index

    def test_includes_every_dimension_score(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[ev.id])

        rendered = render_memo(candidate, analysis)
        for d in analysis.dimension_scores:
            assert d.name in rendered
            assert f"{d.score}/10" in rendered

    def test_includes_every_change_my_mind_item(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[ev.id])

        rendered = render_memo(candidate, analysis)
        for item in analysis.change_my_mind:
            assert item in rendered

    def test_sources_section_includes_the_evidence_url(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        ev = make_evidence(url="https://example.com/a-real-source")
        candidate = make_candidate(evidence=[ev])
        analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[ev.id])

        rendered = render_memo(candidate, analysis)
        assert "https://example.com/a-real-source" in rendered
        assert ev.id in rendered

    def test_scores_table_has_no_blank_lines_between_rows(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        """A blank line inside a GFM table terminates it -- regression guard
        for the Jinja for-loop-newline bug found rendering the real committed
        analyses (fixed by trim_blocks/lstrip_blocks on the Environment)."""
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[ev.id])

        rendered = render_memo(candidate, analysis)
        lines = rendered.splitlines()
        header_index = lines.index("## Scores")
        table_lines = [
            line for line in lines[header_index:header_index + 20] if line.startswith("|")
        ]
        # the header row, the separator row, and one row per dimension score
        assert len(table_lines) == 2 + len(analysis.dimension_scores)
        # and they must be contiguous in the rendered output -- no blank line
        # sitting between any two of them
        start = lines.index(table_lines[0], header_index)
        block = lines[start : start + len(table_lines)]
        assert block == table_lines

    def test_founder_bios_with_embedded_newlines_render_as_one_tight_bullet(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(
            evidence=[ev], founders=["Jane Doe — line one\n\nline two, still her bio"]
        )
        analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[ev.id])

        rendered = render_memo(candidate, analysis)
        assert "- Jane Doe — line one line two, still her bio" in rendered

    def test_renders_cleanly_when_the_candidate_has_no_founders(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        """founders=[] is a real, common case (docs/decisions/0003: 'founder
        signal where findable', not required) -- the memo must still render a
        complete, well-formed Team section, not an empty gap or a stray
        template artifact from the {% if candidate.founders %} guard."""
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev], founders=[])
        analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[ev.id])

        rendered = render_memo(candidate, analysis)

        assert "## Team" in rendered
        assert "{% if" not in rendered
        assert "{%endif%}" not in rendered
        # the narrative team text still appears even with no founder bullets
        assert analysis.team.text in rendered

    def test_pipe_characters_in_a_rationale_do_not_break_the_table(
        self, make_candidate, make_evidence, make_analysis, make_dimension_scores
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        scores = make_dimension_scores()
        scores[0].rationale = "Strong fit | but limited traction"
        analysis = make_analysis(
            candidate_slug=candidate.slug, evidence_ids=[ev.id], dimension_scores=scores
        )

        rendered = render_memo(candidate, analysis)
        assert "Strong fit \\| but limited traction" in rendered
        # every dimension row (starts "| `name`") must still have exactly 5
        # real column-delimiter pipes once the escaped one is discounted
        table_rows = [line for line in rendered.splitlines() if line.startswith("| `")]
        assert table_rows
        for row in table_rows:
            unescaped_pipes = row.replace("\\|", "").count("|")
            assert unescaped_pipes == 5  # | name | weight | score | why |

    def test_has_no_unrendered_jinja_tokens(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[ev.id])

        rendered = render_memo(candidate, analysis)
        assert "{{" not in rendered
        assert "{%" not in rendered

    def test_raises_on_dangling_evidence_instead_of_rendering_a_broken_memo(
        self, make_candidate, make_evidence, make_analysis
    ) -> None:
        ev = make_evidence(url="https://example.com/a")
        candidate = make_candidate(evidence=[ev])
        analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=["ev_deadbeef"])

        with pytest.raises(DanglingEvidenceError):
            render_memo(candidate, analysis)
