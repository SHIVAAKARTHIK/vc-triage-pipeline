"""The traceability gate itself — Fig. 2 in the project overview, as code.

check_evidence_integrity is the last thing that runs before an Analysis is allowed
to be written to data/analyses/ and, downstream, rendered into a memo. These tests
are the ones that matter most for the brief's "claims with no traceable source"
anti-pattern: if this file passes, that anti-pattern is structurally impossible,
not just avoided by convention.
"""

from __future__ import annotations

import pytest

from triage.evidence import DanglingEvidenceError, check_evidence_integrity
from triage.schemas import NarrativeClaim
from triage.util import evidence_id


def test_passes_when_every_cited_id_resolves(make_evidence, make_candidate, make_analysis) -> None:
    ev = make_evidence(url="https://ycombinator.com/companies/ledgerly")
    candidate = make_candidate(evidence=[ev])
    analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[ev.id])

    check_evidence_integrity(candidate, analysis)  # should not raise


def test_raises_when_a_claim_cites_an_id_the_candidate_never_collected(
    make_evidence, make_candidate, make_analysis
) -> None:
    real_ev = make_evidence(url="https://ycombinator.com/companies/ledgerly")
    candidate = make_candidate(evidence=[real_ev])

    fabricated_id = evidence_id("https://twitter.com/some/thread/nobody/fetched")
    analysis = make_analysis(candidate_slug=candidate.slug, evidence_ids=[fabricated_id])

    with pytest.raises(DanglingEvidenceError, match=fabricated_id):
        check_evidence_integrity(candidate, analysis)


def test_raises_when_only_one_of_several_cited_ids_is_dangling(
    make_evidence, make_candidate, make_analysis
) -> None:
    """A claim can legitimately cite more than one piece of evidence; every one
    of them has to resolve, not just the first."""
    real_ev = make_evidence(url="https://ycombinator.com/companies/ledgerly")
    candidate = make_candidate(evidence=[real_ev])

    fabricated_id = evidence_id("https://example.com/never-fetched")
    analysis = make_analysis(
        candidate_slug=candidate.slug, evidence_ids=[real_ev.id, fabricated_id]
    )

    with pytest.raises(DanglingEvidenceError, match=fabricated_id):
        check_evidence_integrity(candidate, analysis)


def test_checks_every_narrative_section_not_just_team(
    make_evidence, make_candidate, make_analysis
) -> None:
    """Regression guard: it's easy to write this check against team/product/market
    and forget risks (a list, plumbed differently) — assert risks are covered too."""
    real_ev = make_evidence(url="https://ycombinator.com/companies/ledgerly")
    candidate = make_candidate(evidence=[real_ev])

    fabricated_id = evidence_id("https://example.com/dangling-risk-source")
    analysis = make_analysis(
        candidate_slug=candidate.slug,
        evidence_ids=[real_ev.id],
        risks=[NarrativeClaim(text="A risk with a bad source.", evidence_ids=[fabricated_id])],
    )

    with pytest.raises(DanglingEvidenceError, match=fabricated_id):
        check_evidence_integrity(candidate, analysis)


def test_raises_on_candidate_analysis_slug_mismatch(make_candidate, make_analysis) -> None:
    candidate = make_candidate(slug="ledgerly")
    analysis = make_analysis(candidate_slug="a-totally-different-company")

    with pytest.raises(DanglingEvidenceError, match="mismatch"):
        check_evidence_integrity(candidate, analysis)
