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


@pytest.fixture
def scripted_sender():
    """A fake `openai.OpenAI(...).chat.completions.create` — returns canned
    responses in sequence and records every call's kwargs, so tests can assert
    on retry counts and on what a corrective re-prompt actually said."""

    class ScriptedSender:
        def __init__(self, responses: list) -> None:
            self.responses = list(responses)
            self.calls: list[dict] = []

        def __call__(self, **kwargs):
            self.calls.append(kwargs)
            return self.responses.pop(0)

    return ScriptedSender


@pytest.fixture
def tool_response():
    """Builds a fake OpenAI ChatCompletion whose message carries a single
    matching tool_call — matches just enough of the real response shape
    (choices[0].message.tool_calls[0].function.{name,arguments}) for
    llm.extract_tool_arguments to work, nothing more. `arguments` is a JSON
    *string*, same as the real API, not a dict.

    Defaults to analyse.py's tool name (the fixture's original, still most
    common use); pass `tool_name=` explicitly for any other stage (eval.py)."""
    import json
    from types import SimpleNamespace

    from triage.analyse import TOOL_NAME as ANALYSE_TOOL_NAME

    def _make(tool_input: dict, tool_name: str = ANALYSE_TOOL_NAME) -> SimpleNamespace:
        function = SimpleNamespace(name=tool_name, arguments=json.dumps(tool_input))
        tool_call = SimpleNamespace(function=function)
        message = SimpleNamespace(tool_calls=[tool_call], content=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    return _make


@pytest.fixture
def text_response():
    """A fake ChatCompletion with no tool_calls — the 'model refused the tool
    call' case analyse.py has to retry past."""
    from types import SimpleNamespace

    def _make(text: str = "I'd rather not.") -> SimpleNamespace:
        message = SimpleNamespace(tool_calls=None, content=text)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    return _make


@pytest.fixture
def valid_raw_input():
    """A RawAnalysis-shaped dict (analyse.py's tool-call payload), citing a
    given evidence id and using real thesis dimension names unless overridden —
    the happy-path payload every retry test starts from and mutates."""

    def _make(
        evidence_id: str, dimension_names: tuple[str, ...] | None = None, score: int = 7
    ) -> dict:
        from triage import thesis

        names = dimension_names or thesis.dimension_names()
        claim = {"text": "Placeholder claim.", "evidence_ids": [evidence_id]}
        return {
            "team": claim,
            "product": claim,
            "market": claim,
            "risks": [claim],
            "dimension_scores": [
                {"name": n, "score": score, "rationale": f"rationale for {n}"} for n in names
            ],
            "call_rationale": "Placeholder rationale.",
            "change_my_mind": ["Signed pilot with a paying SMB", "Second technical co-founder"],
        }

    return _make
