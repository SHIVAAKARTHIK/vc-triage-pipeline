"""The eval stage: out/memos/*.md in, data/eval.json out.

A small LLM-as-judge pass over the pipeline's own final output, per the brief
("a small LLM-as-judge eval over your memos scoring traceability and
clarity — commit the results"). Deliberately narrow: it does not re-check
whether evidence ids resolve — `check_evidence_integrity` already guarantees
that structurally, before a memo can even be rendered (ADR 0006) — it checks
the one thing structural validation can't: whether the cited evidence
actually, plausibly supports the specific claim it's attached to, and whether
a partner could find the call inside 60 seconds. See ADR 0007.

Reuses the OpenAI plumbing from llm.py (same tool-forced pattern as
analyse.py) rather than inventing a second way to call the same API.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Template
from pydantic import BaseModel, Field, ValidationError

from triage.llm import LLMResponseError, extract_tool_arguments, function_tool_schema

logger = logging.getLogger(__name__)

DEFAULT_MEMOS_DIR = Path("out/memos")
DEFAULT_OUT_PATH = Path("data/eval.json")
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_COMPLETION_TOKENS = 500
TOOL_NAME = "submit_judgment"

_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "eval_judge.md"


class JudgeFailedError(RuntimeError):
    """A memo's judgment failed validation on every retry attempt."""


class RawJudgment(BaseModel):
    """What the judge model must produce — the pipeline fills in memo_slug,
    judged_at, and model_used itself."""

    traceability_score: int = Field(ge=1, le=5)
    traceability_notes: str = Field(min_length=1, max_length=400)
    clarity_score: int = Field(ge=1, le=5)
    clarity_notes: str = Field(min_length=1, max_length=400)


class JudgeResult(BaseModel):
    """One row of data/eval.json — a judged memo."""

    memo_slug: str
    traceability_score: int
    traceability_notes: str
    clarity_score: int
    clarity_notes: str
    judged_at: datetime
    model_used: str


def render_judge_prompt(memo_text: str) -> str:
    template = Template(_PROMPT_PATH.read_text(encoding="utf-8"))
    return template.render(memo_text=memo_text)


def judge_memo(
    send_message: Callable[..., Any],
    memo_slug: str,
    memo_text: str,
    *,
    model: str = DEFAULT_MODEL,
    max_attempts: int = 2,
) -> JudgeResult:
    """`send_message` is `openai.OpenAI(...).chat.completions.create` (or any
    object with that call signature) — injected exactly as in analyse.py, so
    tests never need a real key. Lighter retry budget than analyse_candidate's
    (2, not 3): a grading pass failing to parse is worth one retry, not a
    strong signal worth chasing further."""
    prompt = render_judge_prompt(memo_text)
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        response = send_message(
            model=model,
            max_completion_tokens=DEFAULT_MAX_COMPLETION_TOKENS,
            tools=[
                function_tool_schema(
                    TOOL_NAME, "Submit traceability and clarity scores for one memo.", RawJudgment
                )
            ],
            tool_choice={"type": "function", "function": {"name": TOOL_NAME}},
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            raw = RawJudgment(**extract_tool_arguments(response, TOOL_NAME))
        except (LLMResponseError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                "%s: judge attempt %d/%d failed to parse: %s", memo_slug, attempt, max_attempts, exc
            )
            continue

        return JudgeResult(
            memo_slug=memo_slug,
            traceability_score=raw.traceability_score,
            traceability_notes=raw.traceability_notes,
            clarity_score=raw.clarity_score,
            clarity_notes=raw.clarity_notes,
            judged_at=datetime.now(UTC),
            model_used=model,
        )

    raise JudgeFailedError(
        f"{memo_slug}: judging failed after {max_attempts} attempts, last error: {last_error}"
    ) from last_error


def run(
    memos_dir: Path = DEFAULT_MEMOS_DIR,
    out_path: Path = DEFAULT_OUT_PATH,
    model: str = DEFAULT_MODEL,
    max_attempts: int = 2,
    send_message: Callable[..., Any] | None = None,
) -> list[JudgeResult]:
    if send_message is None:
        from openai import OpenAI

        send_message = OpenAI().chat.completions.create

    results: list[JudgeResult] = []
    for memo_path in sorted(memos_dir.glob("*.md")):
        memo_text = memo_path.read_text(encoding="utf-8")
        try:
            result = judge_memo(
                send_message, memo_path.stem, memo_text, model=model, max_attempts=max_attempts
            )
        except JudgeFailedError as exc:
            logger.warning("skipping %s: %s", memo_path.stem, exc)
            continue
        results.append(result)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.model_dump(mode="json") for r in results]
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    total_memos = len(list(memos_dir.glob("*.md")))
    skipped = total_memos - len(results)
    logger.info("wrote %d judgments to %s (%d memo(s) skipped)", len(results), out_path, skipped)
    return results
