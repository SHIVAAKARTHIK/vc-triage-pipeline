"""The traceability gate: does every claim in an Analysis resolve to real evidence?

This is Fig. 2 in the project overview made literal. `Evidence` lives once, on the
`Candidate` that was fetched during sourcing — `Analysis` only ever references it by
id, so this module is the single place that checks the references are real before
an `Analysis` is allowed to reach the memo stage.

Deliberately a plain function over two already-validated Pydantic models, not a
method on either: it needs both objects, and keeping it out-of-band means it can sit
directly in the pipeline's control flow —

    analysis = call_llm(candidate, thesis)
    check_evidence_integrity(candidate, analysis)   # raises before any file is written
    write_analysis(analysis)

— rather than firing implicitly inside a constructor where a caller could miss it.
"""

from __future__ import annotations

from triage.schemas import Analysis, Candidate


class DanglingEvidenceError(ValueError):
    """Raised when an Analysis cites an evidence id its Candidate never collected."""


def check_evidence_integrity(candidate: Candidate, analysis: Analysis) -> None:
    """Raise DanglingEvidenceError unless every cited evidence id was actually fetched.

    Checks Team, Product, Market, and every risk — every `NarrativeClaim` on the
    analysis. Dimension scores are deliberately not checked here: their rationale is
    expected to restate a claim made (and already cited) elsewhere on the analysis,
    not to introduce a new fact of its own.
    """
    if candidate.slug != analysis.candidate_slug:
        raise DanglingEvidenceError(
            f"candidate/analysis mismatch: {candidate.slug!r} vs {analysis.candidate_slug!r}"
        )

    known_ids = {e.id for e in candidate.evidence}

    cited_ids: set[str] = set()
    for claim in (analysis.team, analysis.product, analysis.market, *analysis.risks):
        cited_ids |= set(claim.evidence_ids)

    dangling = sorted(cited_ids - known_ids)
    if dangling:
        raise DanglingEvidenceError(
            f"{analysis.candidate_slug}: analysis cites evidence id(s) {dangling} "
            f"not present in candidate.evidence ({sorted(known_ids)})"
        )
