"""Data contracts shared by every pipeline stage.

These are the nouns the pipeline passes between stages as files (see Fig. 1 in the
project overview and docs/decisions/0001-stack-and-scope.md):

    seed input -> [source]  -> Candidate(s)  -> data/candidates.json
    candidates -> [analyse] -> Analysis       -> data/analyses/<slug>.json
    analysis   -> [memo]    -> out/memos/<slug>.md   (rendered, not modelled)

The one guarantee the brief calls out by name — "claims in memos with no traceable
source" is an anti-pattern — is enforced here structurally, not by prompting:

  * every fact worth stating is captured as `Evidence` first (source URL, snippet,
    retrieval time) *during sourcing*, before any LLM sees the candidate;
  * every judgement the analysis stage makes (`NarrativeClaim`) must cite at least
    one evidence id;
  * `evidence.check_evidence_integrity` then checks those ids actually resolve
    against the candidate's evidence set before an `Analysis` is allowed to reach
    the memo stage. See tests/test_evidence.py.

Scores are similarly kept honest: dimensions are data (name/weight/score), not
hardcoded fields per thesis dimension, and `Analysis.total_score` is a *computed*
property — Python sums the weighted dimension scores itself, so there is no field
the model can fill in with arithmetic that doesn't match its own ratings.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, computed_field, field_validator, model_validator

_EVIDENCE_ID_RE = re.compile(r"^ev_[0-9a-f]{8}$")

Call = Literal["pass", "watch", "meet"]


class Evidence(BaseModel):
    """One fetched, timestamped fact a claim can point to."""

    id: str = Field(description="Stable id from util.evidence_id(url); ev_ + 8 hex chars.")
    url: HttpUrl
    source: Literal["yc", "hn", "homepage", "other"]
    retrieved_at: datetime
    snippet: str = Field(
        min_length=1,
        max_length=500,
        description="The actual text this evidence supports — not just a page title.",
    )

    @field_validator("id")
    @classmethod
    def _id_is_well_formed(cls, v: str) -> str:
        if not _EVIDENCE_ID_RE.match(v):
            raise ValueError(
                f"evidence id {v!r} must match ev_<8 hex chars>; use util.evidence_id()"
            )
        return v


class TractionSignal(BaseModel):
    """The freshness/traction signal the brief requires per candidate."""

    kind: Literal["hn_post", "yc_batch", "github_activity", "funding", "other"]
    detail: str = Field(min_length=1, max_length=200, description='e.g. "142 points, 38 comments"')
    url: HttpUrl | None = None


class Candidate(BaseModel):
    """One sourced startup — the output of the source stage."""

    slug: str
    name: str = Field(min_length=1)
    website: HttpUrl
    one_liner: str = Field(min_length=1, max_length=280)
    founders: list[str] = Field(default_factory=list, description="Best-effort; may be empty.")
    source_batch: str | None = Field(default=None, description='e.g. "YC W25"')
    traction: TractionSignal
    evidence: list[Evidence] = Field(min_length=1)
    sourced_at: datetime

    @model_validator(mode="after")
    def _evidence_ids_unique(self) -> Candidate:
        ids = [e.id for e in self.evidence]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(
                f"{self.slug}: duplicate evidence ids {sorted(dupes)} (same URL fetched twice?)"
            )
        return self


class NarrativeClaim(BaseModel):
    """A single judgement in an analysis — Team / Product / Market / one risk.

    `evidence_ids` is mandatory and non-empty by construction: a claim with no
    evidence cannot even be built, let alone reach a memo.
    """

    text: str = Field(min_length=1, max_length=1200)
    evidence_ids: list[str] = Field(min_length=1)

    @field_validator("evidence_ids")
    @classmethod
    def _ids_well_formed(cls, ids: list[str]) -> list[str]:
        bad = [i for i in ids if not _EVIDENCE_ID_RE.match(i)]
        if bad:
            raise ValueError(f"malformed evidence ids: {bad}")
        return ids


class DimensionScore(BaseModel):
    """One line of the thesis's scoring table (docs/thesis.md), applied to one candidate.

    Dimensions are data, not hardcoded schema fields, so a wording change in the
    thesis doesn't require a schema/migration change — only the config the analyse
    stage loads. See docs/decisions/0002-dimension-scores-are-data.md.
    """

    name: str = Field(min_length=1, description="Must match a dimension name in docs/thesis.md.")
    weight: float = Field(gt=0, le=100)
    score: int = Field(
        ge=0, le=10, description="Model's rating out of 10; Python applies the weight."
    )
    rationale: str = Field(min_length=1, max_length=400)


class Analysis(BaseModel):
    """The output of the analyse stage — one file per candidate at data/analyses/<slug>.json.

    Covers stage 2 (Team/Product/Market/Risks/Score) and stage 3 (the call, its
    rationale, and what would change it) from the brief in one artefact, because
    the recommendation is part of forming the judgement, not a separate pass over
    it. The memo stage only renders this to Markdown — it makes no judgement calls.
    """

    candidate_slug: str
    thesis_version: str = Field(
        description="Hash/tag of the thesis.md snapshot this was scored against."
    )
    model_used: str
    analyzed_at: datetime

    team: NarrativeClaim
    product: NarrativeClaim
    market: NarrativeClaim
    risks: list[NarrativeClaim] = Field(min_length=1, max_length=5)

    dimension_scores: list[DimensionScore] = Field(min_length=1)

    call: Call
    call_rationale: str = Field(min_length=1, max_length=500)
    change_my_mind: list[str] = Field(
        min_length=2,
        max_length=3,
        description="The 2-3 things that would change the call, required by the brief verbatim.",
    )

    @model_validator(mode="after")
    def _weights_sum_to_100(self) -> Analysis:
        total = sum(d.weight for d in self.dimension_scores)
        if abs(total - 100.0) > 0.5:
            raise ValueError(
                f"{self.candidate_slug}: dimension weights sum to {total:.1f}, expected 100 "
                "(check docs/thesis.md against the config the analyse stage loaded)"
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_score(self) -> int:
        """0-100, computed here — never accepted as LLM output. See module docstring."""
        return weighted_total(self.dimension_scores)


def weighted_total(dimension_scores: list[DimensionScore]) -> int:
    """0-100 weighted score from per-dimension ratings — the one formula both
    `Analysis.total_score` and `analyse.py` use.

    A standalone function, not just a method, because analyse.py needs this
    number *before* an Analysis can be constructed: `call` is chosen from the
    weighted total (docs/decisions/0004), and `call` is a required constructor
    argument. Calling this function first and Analysis.total_score afterwards
    are the same formula applied to the same list, so the two can't drift apart.
    """
    return round(sum(d.score / 10 * d.weight for d in dimension_scores))
