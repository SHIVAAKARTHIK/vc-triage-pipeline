"""triage.analyse.run — data/candidates.json in, data/analyses/*.json out,
across more than one candidate, including one that never produces a valid
analysis.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from triage import thesis
from triage.analyse import run
from triage.util import evidence_id


def _candidate_dict(slug: str, name: str, url: str) -> dict:
    now = datetime.now(UTC).isoformat()
    ev_id = evidence_id(url)
    return {
        "slug": slug,
        "name": name,
        "website": "https://example.com",
        "one_liner": "A placeholder candidate for pipeline tests.",
        "founders": [],
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
    }


class TestRun:
    def test_writes_one_analysis_per_candidate_and_returns_them(
        self, tmp_path, scripted_sender, tool_response, valid_raw_input
    ) -> None:
        a = _candidate_dict("alpha", "Alpha", "https://alpha.example.com")
        b = _candidate_dict("beta", "Beta", "https://beta.example.com")
        candidates_path = tmp_path / "candidates.json"
        candidates_path.write_text(json.dumps([a, b]), encoding="utf-8")

        sender = scripted_sender(
            [
                tool_response(valid_raw_input(a["evidence"][0]["id"])),
                tool_response(valid_raw_input(b["evidence"][0]["id"])),
            ]
        )

        analyses = run(
            candidates_path=candidates_path, out_dir=tmp_path / "analyses", send_message=sender
        )

        assert {a.candidate_slug for a in analyses} == {"alpha", "beta"}
        written = sorted(p.name for p in (tmp_path / "analyses").glob("*.json"))
        assert written == ["alpha.json", "beta.json"]

    def test_skips_a_candidate_that_never_produces_a_valid_analysis(
        self, tmp_path, caplog, scripted_sender, tool_response, valid_raw_input
    ) -> None:
        a = _candidate_dict("alpha", "Alpha", "https://alpha.example.com")
        b = _candidate_dict("beta", "Beta", "https://beta.example.com")
        candidates_path = tmp_path / "candidates.json"
        candidates_path.write_text(json.dumps([a, b]), encoding="utf-8")

        # alpha: every attempt cites a fabricated id -> exhausts its 2 attempts.
        # beta: valid on the first try.
        sender = scripted_sender(
            [
                tool_response(valid_raw_input("ev_deadbeef")),
                tool_response(valid_raw_input("ev_deadbeef")),
                tool_response(valid_raw_input(b["evidence"][0]["id"])),
            ]
        )

        with caplog.at_level(logging.WARNING):
            analyses = run(
                candidates_path=candidates_path,
                out_dir=tmp_path / "analyses",
                send_message=sender,
                max_attempts=2,
            )

        assert [a.candidate_slug for a in analyses] == ["beta"]
        assert "skipping alpha" in caplog.text
        written = sorted(p.name for p in (tmp_path / "analyses").glob("*.json"))
        assert written == ["beta.json"]

    def test_written_analysis_round_trips_as_valid_json(
        self, tmp_path, scripted_sender, tool_response, valid_raw_input
    ) -> None:
        a = _candidate_dict("alpha", "Alpha", "https://alpha.example.com")
        candidates_path = tmp_path / "candidates.json"
        candidates_path.write_text(json.dumps([a]), encoding="utf-8")
        sender = scripted_sender([tool_response(valid_raw_input(a["evidence"][0]["id"]))])

        run(candidates_path=candidates_path, out_dir=tmp_path / "analyses", send_message=sender)

        written = json.loads((tmp_path / "analyses" / "alpha.json").read_text(encoding="utf-8"))
        assert written["candidate_slug"] == "alpha"
        assert written["thesis_version"] == thesis.thesis_version()
        assert 0 <= written["total_score"] <= 100

    def test_zero_candidates_produces_zero_analyses_without_error(
        self, tmp_path, scripted_sender
    ) -> None:
        """A source run that legitimately finds nothing relevant (an empty or
        very off-thesis batch) shouldn't crash the next stage."""
        candidates_path = tmp_path / "candidates.json"
        candidates_path.write_text(json.dumps([]), encoding="utf-8")
        sender = scripted_sender([])  # never called

        analyses = run(
            candidates_path=candidates_path, out_dir=tmp_path / "analyses", send_message=sender
        )

        assert analyses == []
        assert list((tmp_path / "analyses").glob("*.json")) == []
