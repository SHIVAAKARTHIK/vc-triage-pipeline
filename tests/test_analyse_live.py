"""One real call against the real OpenAI API — not part of the default
suite, and skipped even under `-m live` unless OPENAI_API_KEY is actually
set, so a contributor without a key still gets a clean run.

To run for real:  OPENAI_API_KEY=... uv run pytest -m live tests/test_analyse_live.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from triage.schemas import Candidate

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"), reason="needs a real OPENAI_API_KEY"
    ),
]


def test_a_real_call_produces_a_valid_analysis_for_one_real_candidate() -> None:
    from openai import OpenAI

    from triage.analyse import analyse_candidate

    candidates_path = Path("data/candidates.json")
    if not candidates_path.exists():
        pytest.skip("data/candidates.json not present -- run `triage source` first")

    raw = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidate = Candidate(**raw[0])

    client = OpenAI()
    analysis = analyse_candidate(client.chat.completions.create, candidate)

    assert analysis.candidate_slug == candidate.slug
    assert 0 <= analysis.total_score <= 100
    assert analysis.call in ("pass", "watch", "meet")
