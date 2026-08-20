"""The analyse stage: data/candidates.json in, data/analyses/<slug>.json out.

One tool-forced OpenAI chat-completions call per candidate, against a prompt
built entirely from docs/thesis.md (via triage.thesis) and the candidate's own
evidence — see Fig. 1/2 in the project overview, docs/decisions/0004, and
ADR 0005 (switched from Anthropic to OpenAI mid-build — API key available, not
a quality judgement).

The model is deliberately asked for less than the final `Analysis` needs:
`RawAnalysis` has no `total_score` (computed, ADR 0002) and no `call` (computed
from the total via `thesis.call_for_score`, ADR 0004) — only the qualitative
judgement (team/product/market/risks/dimension scores/rationale/change-my-mind)
that's actually the model's to make.

A response is rejected — and re-prompted with a corrective note naming exactly
what was wrong — if it doesn't parse, uses the wrong dimension names, or cites
an evidence id `check_evidence_integrity` can't resolve. `AnalysisFailedError`
after `max_attempts` is caught per-candidate by `run()`, which skips that
candidate and keeps going, the same graceful-degradation shape as source.py.
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

from triage import thesis
from triage.evidence import DanglingEvidenceError, check_evidence_integrity
from triage.schemas import Analysis, Candidate, DimensionScore, NarrativeClaim, weighted_total

logger = logging.getLogger(__name__)

DEFAULT_CANDIDATES_PATH = Path("data/candidates.json")
DEFAULT_ANALYSES_DIR = Path("data/analyses")
# Override with --model if this has aged out by the time you're reading it.
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_COMPLETION_TOKENS = 2000
TOOL_NAME = "submit_analysis"

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_SYSTEM_TEMPLATE_PATH = _PROMPTS_DIR / "analyse_system.md"
_CANDIDATE_TEMPLATE_PATH = _PROMPTS_DIR / "analyse_candidate.md"


class LLMResponseError(RuntimeError):
    """The model's response couldn't be turned into a usable RawAnalysis."""


class AnalysisFailedError(RuntimeError):
    """A candidate's analysis failed validation on every retry attempt."""


class RawDimensionScore(BaseModel):
    """What the model actually reports per dimension — no weight (that's
    thesis.weight_for, not the model's to state)."""

    name: str
    score: int = Field(ge=0, le=10)
    rationale: str = Field(min_length=1, max_length=400)


class RawAnalysis(BaseModel):
    """The tool-call shape the model must fill in. Deliberately missing
    `candidate_slug`, `thesis_version`, `model_used`, `analyzed_at` (the pipeline
    already knows these), `total_score` and `call` (both computed, never asked
    for). See module docstring."""

    team: NarrativeClaim
    product: NarrativeClaim
    market: NarrativeClaim
    risks: list[NarrativeClaim] = Field(min_length=1, max_length=5)
    dimension_scores: list[RawDimensionScore]
    call_rationale: str = Field(min_length=1, max_length=500)
    change_my_mind: list[str] = Field(min_length=2, max_length=3)


def render_system_prompt() -> str:
    template = Template(_SYSTEM_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.render(
        slice=thesis.section("The slice"),
        why_now=thesis.section("Why now"),
        anti_portfolio=thesis.section("What I explicitly do not invest in"),
        dimensions=thesis.DIMENSIONS,
    )


def render_candidate_prompt(candidate: Candidate) -> str:
    template = Template(_CANDIDATE_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.render(candidate=candidate)


def _tool_schema() -> dict:
    return {
        "type": "function",
        "function": {
            "name": TOOL_NAME,
            "description": "Submit the structured analysis for one candidate.",
            "parameters": RawAnalysis.model_json_schema(),
        },
    }


def _extract_tool_input(response: Any) -> dict:
    """OpenAI returns arguments as a JSON *string*, not a dict — a malformed
    one is exactly as retry-able as a schema mismatch, so a bad JSON parse here
    raises the same LLMResponseError analyse_candidate already catches."""
    message = response.choices[0].message
    for tool_call in message.tool_calls or []:
        if tool_call.function.name == TOOL_NAME:
            try:
                return json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as exc:
                raise LLMResponseError(f"tool call arguments were not valid JSON: {exc}") from exc
    raise LLMResponseError(f"model response did not include a {TOOL_NAME!r} tool call")


def _build_analysis(candidate: Candidate, raw: RawAnalysis, *, model_used: str) -> Analysis:
    dimension_scores = [
        DimensionScore(
            name=d.name, weight=thesis.weight_for(d.name), score=d.score, rationale=d.rationale
        )
        for d in raw.dimension_scores
    ]
    total = weighted_total(dimension_scores)
    return Analysis(
        candidate_slug=candidate.slug,
        thesis_version=thesis.thesis_version(),
        model_used=model_used,
        analyzed_at=datetime.now(UTC),
        team=raw.team,
        product=raw.product,
        market=raw.market,
        risks=raw.risks,
        dimension_scores=dimension_scores,
        call=thesis.call_for_score(total),
        call_rationale=raw.call_rationale,
        change_my_mind=raw.change_my_mind,
    )


def analyse_candidate(
    send_message: Callable[..., Any],
    candidate: Candidate,
    *,
    model: str = DEFAULT_MODEL,
    max_attempts: int = 3,
) -> Analysis:
    """`send_message` is `openai.OpenAI(...).chat.completions.create` in real
    use (or any object with that call signature) — injected so tests never
    need a real API key or network access.

    Retries are stateless single-shot re-prompts with a corrective note, not a
    threaded tool-call conversation: simpler, and re-sending the full candidate
    context each attempt is cheap at this candidate count. See ADR 0004.
    """
    system_prompt = render_system_prompt()
    user_prompt = render_candidate_prompt(candidate)
    expected_names = set(thesis.dimension_names())
    known_evidence_ids = sorted(e.id for e in candidate.evidence)

    correction: str | None = None
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        user_content = (
            user_prompt
            if correction is None
            else f"{user_prompt}\n\n---\nYour previous attempt was invalid: {correction}\n"
            "Resubmit a complete, corrected analysis."
        )
        response = send_message(
            model=model,
            max_completion_tokens=DEFAULT_MAX_COMPLETION_TOKENS,
            tools=[_tool_schema()],
            tool_choice={"type": "function", "function": {"name": TOOL_NAME}},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )

        try:
            raw = RawAnalysis(**_extract_tool_input(response))
        except (LLMResponseError, ValidationError) as exc:
            last_error = exc
            correction = f"response did not parse: {exc}"
            logger.warning(
                "%s: attempt %d/%d failed to parse: %s", candidate.slug, attempt, max_attempts, exc
            )
            continue

        raw_names = {d.name for d in raw.dimension_scores}
        if raw_names != expected_names:
            last_error = ValueError(
                f"dimension names {sorted(raw_names)} != expected {sorted(expected_names)}"
            )
            correction = (
                f"you used dimension names {sorted(raw_names)}, but you must use exactly "
                f"{sorted(expected_names)} -- no more, no fewer, no renaming."
            )
            logger.warning(
                "%s: attempt %d/%d used wrong dimension names",
                candidate.slug, attempt, max_attempts,
            )
            continue

        analysis = _build_analysis(candidate, raw, model_used=model)

        try:
            check_evidence_integrity(candidate, analysis)
        except DanglingEvidenceError as exc:
            last_error = exc
            correction = f"{exc} Only cite ids from this list: {known_evidence_ids}."
            logger.warning(
                "%s: attempt %d/%d cited unknown evidence", candidate.slug, attempt, max_attempts
            )
            continue

        return analysis

    raise AnalysisFailedError(
        f"{candidate.slug}: failed after {max_attempts} attempts, last error: {last_error}"
    ) from last_error


def run(
    candidates_path: Path = DEFAULT_CANDIDATES_PATH,
    out_dir: Path = DEFAULT_ANALYSES_DIR,
    model: str = DEFAULT_MODEL,
    max_attempts: int = 3,
    send_message: Callable[..., Any] | None = None,
) -> list[Analysis]:
    if send_message is None:
        from openai import OpenAI

        send_message = OpenAI().chat.completions.create

    raw_candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidates = [Candidate(**c) for c in raw_candidates]

    out_dir.mkdir(parents=True, exist_ok=True)
    analyses: list[Analysis] = []
    for candidate in candidates:
        try:
            analysis = analyse_candidate(
                send_message, candidate, model=model, max_attempts=max_attempts
            )
        except AnalysisFailedError as exc:
            logger.warning("skipping %s: %s", candidate.slug, exc)
            continue

        path = out_dir / f"{candidate.slug}.json"
        body = json.dumps(analysis.model_dump(mode="json"), indent=2, ensure_ascii=False)
        path.write_text(body, encoding="utf-8")
        analyses.append(analysis)

    skipped = len(candidates) - len(analyses)
    logger.info(
        "wrote %d analyses to %s (%d candidate(s) skipped)", len(analyses), out_dir, skipped
    )
    return analyses
