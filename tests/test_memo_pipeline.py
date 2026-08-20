"""triage.memo.run — data/candidates.json + data/analyses/*.json in,
out/memos/*.md out.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from triage.memo import run
from triage.util import evidence_id


def _write_analysis(analyses_dir: Path, slug: str, ev_id: str, **overrides) -> None:
    (analyses_dir / f"{slug}.json").write_text(
        json.dumps(_analysis_dict(slug, ev_id, **overrides)), encoding="utf-8"
    )


def _candidate_dict(slug: str, name: str, url: str) -> dict:
    now = datetime.now(UTC).isoformat()
    ev_id = evidence_id(url)
    return {
        "slug": slug,
        "name": name,
        "website": "https://example.com",
        "one_liner": "A placeholder candidate for memo pipeline tests.",
        "founders": ["A Founder"],
        "source_batch": "Winter 2025",
        "traction": {"kind": "yc_batch", "detail": "Winter 2025 admission", "url": url},
        "evidence": [
            {
                "id": ev_id,
                "url": url,
                "source": "yc",
                "retrieved_at": now,
                "snippet": "Placeholder snippet.",
            }
        ],
        "sourced_at": now,
    }, ev_id


def _analysis_dict(slug: str, ev_id: str, call: str = "watch") -> dict:
    now = datetime.now(UTC).isoformat()
    claim = {"text": "Placeholder claim.", "evidence_ids": [ev_id]}
    return {
        "candidate_slug": slug,
        "thesis_version": "thesis@dev",
        "model_used": "gpt-4o-mini",
        "analyzed_at": now,
        "team": claim,
        "product": claim,
        "market": claim,
        "risks": [claim],
        "dimension_scores": [
            {"name": "workflow_ownership", "weight": 30, "score": 5, "rationale": "r"},
            {"name": "buyer_pain", "weight": 20, "score": 5, "rationale": "r"},
            {"name": "team_domain_fit", "weight": 25, "score": 5, "rationale": "r"},
            {"name": "wedge_defensibility", "weight": 15, "score": 5, "rationale": "r"},
            {"name": "traction", "weight": 10, "score": 5, "rationale": "r"},
        ],
        "call": call,
        "call_rationale": "Placeholder rationale.",
        "change_my_mind": ["thing one", "thing two"],
    }


class TestRun:
    def test_writes_one_memo_per_analysis_and_returns_paths(self, tmp_path) -> None:
        a, a_ev = _candidate_dict("alpha", "Alpha", "https://alpha.example.com")
        b, b_ev = _candidate_dict("beta", "Beta", "https://beta.example.com")
        candidates_path = tmp_path / "candidates.json"
        candidates_path.write_text(json.dumps([a, b]), encoding="utf-8")

        analyses_dir = tmp_path / "analyses"
        analyses_dir.mkdir()
        _write_analysis(analyses_dir, "alpha", a_ev)
        _write_analysis(analyses_dir, "beta", b_ev)

        out_dir = tmp_path / "memos"
        written = run(
            candidates_path=candidates_path, analyses_dir=analyses_dir, out_dir=out_dir
        )

        assert sorted(p.name for p in written) == ["alpha.md", "beta.md"]
        assert (out_dir / "alpha.md").exists()
        assert (out_dir / "alpha.md").read_text(encoding="utf-8").startswith("# Alpha")

    def test_skips_an_analysis_with_no_matching_candidate(self, tmp_path, caplog) -> None:
        a, a_ev = _candidate_dict("alpha", "Alpha", "https://alpha.example.com")
        candidates_path = tmp_path / "candidates.json"
        candidates_path.write_text(json.dumps([a]), encoding="utf-8")

        analyses_dir = tmp_path / "analyses"
        analyses_dir.mkdir()
        _write_analysis(analyses_dir, "alpha", a_ev)
        # an analysis for a candidate that was never sourced (or was later removed)
        _write_analysis(analyses_dir, "ghost", a_ev)

        out_dir = tmp_path / "memos"
        with caplog.at_level(logging.WARNING):
            written = run(
                candidates_path=candidates_path, analyses_dir=analyses_dir, out_dir=out_dir
            )

        assert [p.name for p in written] == ["alpha.md"]
        assert "ghost" in caplog.text

    def test_memo_call_matches_the_analysis_call(self, tmp_path) -> None:
        a, a_ev = _candidate_dict("alpha", "Alpha", "https://alpha.example.com")
        candidates_path = tmp_path / "candidates.json"
        candidates_path.write_text(json.dumps([a]), encoding="utf-8")

        analyses_dir = tmp_path / "analyses"
        analyses_dir.mkdir()
        _write_analysis(analyses_dir, "alpha", a_ev, call="meet")

        out_dir = tmp_path / "memos"
        run(candidates_path=candidates_path, analyses_dir=analyses_dir, out_dir=out_dir)

        text = (out_dir / "alpha.md").read_text(encoding="utf-8")
        assert "Take a meeting" in text

    def test_zero_analyses_produces_zero_memos_without_error(self, tmp_path) -> None:
        candidates_path = tmp_path / "candidates.json"
        candidates_path.write_text(json.dumps([]), encoding="utf-8")
        analyses_dir = tmp_path / "analyses"
        analyses_dir.mkdir()

        written = run(
            candidates_path=candidates_path, analyses_dir=analyses_dir, out_dir=tmp_path / "memos"
        )

        assert written == []
