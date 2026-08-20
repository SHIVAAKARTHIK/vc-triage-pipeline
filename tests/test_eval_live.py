"""One real call against the real OpenAI API — not part of the default
suite, and skipped even under `-m live` unless OPENAI_API_KEY is actually set.

To run for real:  OPENAI_API_KEY=... uv run pytest -m live tests/test_eval_live.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"), reason="needs a real OPENAI_API_KEY"
    ),
]


def test_a_real_call_judges_one_real_memo() -> None:
    from openai import OpenAI

    from triage.eval import judge_memo

    memos_dir = Path("out/memos")
    memo_paths = sorted(memos_dir.glob("*.md")) if memos_dir.exists() else []
    if not memo_paths:
        pytest.skip("out/memos/*.md not present -- run `triage memo` first")

    memo_path = memo_paths[0]
    client = OpenAI()
    memo_text = memo_path.read_text(encoding="utf-8")
    result = judge_memo(client.chat.completions.create, memo_path.stem, memo_text)

    assert result.memo_slug == memo_path.stem
    assert 1 <= result.traceability_score <= 5
    assert 1 <= result.clarity_score <= 5
